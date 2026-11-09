"""Scratchpad-note authoring and state transitions (per COR-012 + COR-043).

The deterministic part of `pkit new scratchpad` and `pkit scratchpad
<done|drop|reported|list>`: file stamping, state-folder transitions,
frontmatter updates, and the `reported` side-state of active (COR-043) —
stamp on send, freeze-by-convention with drift *detection*, live pull-only
upstream read-back. The conversational layer (slug judgement, topic
boundary, body-drafting opening) is the `scratchpad-author` skill's job
per COR-005's "Skill / command pairing".

It also holds the `scratchpad` member of `pkit validate` (`outcome`): a note
lies in one state folder, the folder being its state (COR-012).
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import hashlib
import io
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import click
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, ScalarNode

from project_kit.validators import Finding, Outcome

RetiredState = Literal["done", "dropped"]

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

#: All state folders, most-specific-first for slug resolution. `reported/` is
#: the optional side-state of active (COR-043): lazily created, removed when
#: it empties.
_ALL_STATES = ("active", "reported", "done", "dropped")

#: The fields a note's first stamp writes in its front matter, as
#: `_insert_reported_frontmatter` lays them out (COR-043 point 3). `project`
#: and `workstream` join them where the report names them.
_STAMP_FIELDS = ("reported", "reported_to", "reported_hash")

_ISSUE_REF_RE = re.compile(r"^[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*#\d+$")
_ISSUE_URL_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s]+)/issues/(\d+)/?(?:[?#].*)?$")


ACTIVE_TEMPLATE = """\
---
authors:
  - {author}
started: {today}
---

# {title}
"""


def stamp_new_scratchpad(target_root: Path, slug: str, dry_run: bool = False) -> Path:
    """Stamp a new active-state scratchpad note.

    Path: `.pkit/scratchpad/active/<YYYY-MM-DD>-<slug>.md`. Frontmatter
    is seeded with `authors` (from git config) and `started` (today).
    Body opens with a level-1 heading derived from the slug — the author
    edits it on first pass.
    """
    _validate_slug(slug)
    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    active_dir = scratchpad_dir / "active"
    if not active_dir.is_dir():
        raise click.ClickException(
            f"{active_dir.relative_to(target_root)} does not exist. "
            f"Run 'pkit init' from this project's root first."
        )

    today = _today()
    target = active_dir / f"{today}-{slug}.md"
    if target.exists():
        raise click.ClickException(
            f"a scratchpad note already exists at {target.relative_to(target_root)}."
        )
    # Slugs are unique across the area, not just per state — refuse if
    # the same slug already lives in done/ or dropped/.
    existing = _find_in_any_state(scratchpad_dir, slug)
    if existing is not None:
        raise click.ClickException(
            f"slug {slug!r} already used by {existing.relative_to(target_root)}."
        )

    title = _slug_to_title(slug)
    content = ACTIVE_TEMPLATE.format(author=_resolve_author(), today=today, title=title)
    if not dry_run:
        target.write_text(content, encoding="utf-8")
    return target


def transition_to_done(
    target_root: Path,
    slug: str,
    produced: tuple[str, ...] = (),
    dry_run: bool = False,
) -> tuple[Path, Path]:
    """Move a note from active/ (or reported/) to done/, appending retired/produced frontmatter."""
    return _transition(target_root, slug, "done", produced=produced, dry_run=dry_run)


def transition_to_dropped(target_root: Path, slug: str, dry_run: bool = False) -> tuple[Path, Path]:
    """Move a note from active/ (or reported/) to dropped/, appending retired frontmatter."""
    return _transition(target_root, slug, "dropped", produced=(), dry_run=dry_run)


def _transition(
    target_root: Path,
    slug: str,
    to_state: RetiredState,
    *,
    produced: tuple[str, ...],
    dry_run: bool,
) -> tuple[Path, Path]:
    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    active_dir = scratchpad_dir / "active"
    if not active_dir.is_dir():
        raise click.ClickException(f"{active_dir.relative_to(target_root)} does not exist.")

    # Retirement proceeds from active/ or from its reported side-state
    # (`reported/ → done|dropped` by the same gesture, COR-043).
    src = _resolve_in_state(active_dir, slug)
    if src is None:
        reported_dir = scratchpad_dir / "reported"
        if reported_dir.is_dir():
            src = _resolve_in_state(reported_dir, slug)
    if src is None:
        raise click.ClickException(
            f"no active or reported scratchpad note matches {slug!r} in "
            f"{scratchpad_dir.relative_to(target_root)}."
        )

    dst_dir = scratchpad_dir / to_state
    dst = dst_dir / src.name
    if dst.exists():
        raise click.ClickException(f"target already exists at {dst.relative_to(target_root)}.")

    new_content = _add_retirement_frontmatter(src.read_text(encoding="utf-8"), produced=produced)
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst.write_text(new_content, encoding="utf-8")
        src.unlink()
        _remove_reported_dir_if_empty(src.parent)
    return src, dst


def _remove_reported_dir_if_empty(directory: Path) -> None:
    """Drop a now-empty `reported/` — the directory is lazy (COR-043): created
    when the first note enters, removed when it empties. Best-effort (a stray
    non-note file simply keeps the directory)."""
    if directory.name != "reported":
        return
    with contextlib.suppress(OSError):
        directory.rmdir()


def _add_retirement_frontmatter(content: str, *, produced: tuple[str, ...]) -> str:
    """Parse YAML frontmatter, append `retired` (and optionally `produced`), re-serialise."""
    yaml = YAML()
    yaml.preserve_quotes = True
    # Match the indentation style of the stamped active-state notes:
    #   authors:
    #     - Name <email>
    yaml.indent(mapping=2, sequence=4, offset=2)

    fm_yaml, body = _split_frontmatter(content)
    _refuse_keys_held_twice(_frontmatter_keys(content))
    try:
        data = yaml.load(io.StringIO(fm_yaml)) or {}
    except YAMLError as exc:
        problem = getattr(exc, "problem", None) or exc
        raise click.ClickException(
            f"scratchpad note's frontmatter does not read as YAML: {problem}."
        ) from None
    if not isinstance(data, dict):
        raise click.ClickException("scratchpad note has malformed frontmatter (not a mapping).")

    # Use a date object (not a string) so ruamel.yaml serialises bare
    # (`retired: 2026-05-12`), not quoted (`retired: '2026-05-12'`).
    data["retired"] = _today_date()
    if produced:
        data["produced"] = list(produced)

    out = io.StringIO()
    yaml.dump(data, out)
    return f"---\n{out.getvalue()}---\n\n{body}"


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split a markdown file into (frontmatter_yaml, body). Both strings."""
    if not content.startswith("---"):
        raise click.ClickException("scratchpad note has no frontmatter block.")
    after_open = content[len("---") :].lstrip("\n")
    end_match = re.search(r"^---\s*$", after_open, re.MULTILINE)
    if not end_match:
        raise click.ClickException("scratchpad note has no closing frontmatter delimiter.")
    fm_yaml = after_open[: end_match.start()]
    body = after_open[end_match.end() :].lstrip("\n")
    return fm_yaml, body


def _notes_found_by(state_dir: Path, slug: str) -> list[Path]:
    """The notes of `state_dir` that `slug` finds: the note whose whole file name
    it is, or each note whose file name after the date is that whole slug
    (`note_slug`). A slug never finds a note whose slug merely ends in it."""
    if slug.endswith(".md"):
        candidate = state_dir / slug
        return [candidate] if Path(slug).name == slug and candidate.is_file() else []
    return sorted(
        path for path in state_dir.glob("*.md") if path.is_file() and note_slug(path.name) == slug
    )


def _resolve_in_state(state_dir: Path, slug: str) -> Path | None:
    """Find a scratchpad note by its whole slug or its whole file name."""
    matches = _notes_found_by(state_dir, slug)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        raise click.ClickException(
            f"slug {slug!r} matches multiple notes: {names}. "
            f"Pass the full filename to disambiguate."
        )
    return None


def _find_in_any_state(scratchpad_dir: Path, slug: str) -> Path | None:
    """The first note, searching every state folder (incl. the reported
    side-state), that holds this whole slug."""
    for state in _ALL_STATES:
        state_dir = scratchpad_dir / state
        if not state_dir.is_dir():
            continue
        matches = _notes_found_by(state_dir, slug)
        if matches:
            return matches[0]
    return None


# --- reported side-state (COR-043) ----------------------------------


@dataclass(frozen=True)
class ReportedStamp:
    """Outcome of a reported-stamp gesture. `src == dst` when the note was
    already reported (append case)."""

    src: Path
    dst: Path
    added: tuple[str, ...]
    duplicate: tuple[str, ...]


@dataclass(frozen=True)
class ReportedRefState:
    """One reported ref resolved live (#678, mirroring report.py's
    `TrackedFix` shape): its upstream state plus — when the read succeeded —
    the issue's title and URL, so a listing can say WHAT was reported, not
    just its number. Offline/unresolved: state "unknown", title/url empty
    (the render degrades to ref + state)."""

    ref: str  # normalized `owner/repo#N`
    state: str  # "open" | "closed" | "unknown" (offline / unresolvable)
    title: str = ""
    url: str = ""


@dataclass(frozen=True)
class NoteEntry:
    """One note in a `list_notes` listing."""

    name: str
    folder: str  # "active" | "reported" | "done" | "dropped"
    refs: tuple[ReportedRefState, ...] = ()
    drifted: bool = False


def normalize_issue_ref(ref: str) -> str:
    """Normalize an issue reference to `owner/repo#N`. Accepts that form
    directly or a full GitHub issue URL; raises on anything else."""
    if _ISSUE_REF_RE.match(ref):
        return ref
    m = _ISSUE_URL_RE.match(ref)
    if m:
        return f"{m.group(1)}/{m.group(2)}#{m.group(3)}"
    raise click.ClickException(
        f"invalid issue ref {ref!r} — expected owner/repo#N or a GitHub issue URL."
    )


def content_hash(content: str) -> str:
    """`sha256:<hex>` over `content` — the COR-043 drift-detection anchor."""
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def note_slug(name: str) -> str:
    """The slug portion of a note filename (`<YYYY-MM-DD>-<slug>.md`)."""
    stem = name[: -len(".md")] if name.endswith(".md") else name
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)


def resolve_note(
    target_root: Path, note: str, states: tuple[str, ...] = ("active", "reported")
) -> Path:
    """Resolve a note reference — a slug, a full filename, or a path — to an
    existing file. Slug/filename resolution searches `states` in order."""
    candidate = Path(note)
    path = candidate if candidate.is_absolute() else target_root / candidate
    if path.is_file():
        return path
    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    for state in states:
        state_dir = scratchpad_dir / state
        if state_dir.is_dir():
            match = _resolve_in_state(state_dir, note)
            if match is not None:
                return match
    raise click.ClickException(
        f"no scratchpad note matches {note!r} in {' or '.join(states)} "
        f"under {scratchpad_dir.relative_to(target_root)}."
    )


def stamp_reported(
    target_root: Path,
    note: str,
    refs: tuple[str, ...],
    *,
    project: str | None = None,
    workstream: str | None = None,
    dry_run: bool = False,
) -> ReportedStamp:
    """Stamp a note as sent through the report channel (COR-043).

    From `active/`: move to the lazily-created `reported/`, appending
    `reported` (today), `reported_to` (normalized refs), `reported_hash`
    (SHA-256 of the full file as it was at send time), and optionally
    `project`/`workstream`. On an already-reported note: append the refs not
    yet recorded and recompute the hash (a new send re-anchors drift);
    duplicate refs are an idempotent no-op.

    The frontmatter edit is a textual insertion (no YAML round-trip) so the
    pre-stamp bytes stay recoverable — `content_hash` of the stamped file with
    the reported block stripped equals the stamped hash. The block is only the
    fields this stamp wrote, so a field of the note's own, such as its own
    `project` where the stamp writes none, stays in what the hash covers.

    A stamp that would leave a key twice in the front matter is refused,
    naming the key, and writes nothing (`_refuse_unrecordable`, #2923).
    """
    normalized: list[str] = []
    for ref in refs:
        norm = normalize_issue_ref(ref)
        if norm not in normalized:
            normalized.append(norm)
    if not normalized:
        raise click.ClickException("at least one issue ref is required.")

    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    src = resolve_note(target_root, note, states=("active", "reported"))
    content = src.read_text(encoding="utf-8")

    if src.parent == scratchpad_dir / "reported":
        _refuse_unrecordable(content, first=False)
        existing = read_reported_refs(content)
        added = tuple(r for r in normalized if r not in existing)
        duplicate = tuple(r for r in normalized if r in existing)
        if not added:
            return ReportedStamp(src, src, (), duplicate)
        new_hash = content_hash(_strip_reported_frontmatter(content))
        new_content = _append_reported_refs(content, added, new_hash)
        if not dry_run:
            src.write_text(new_content, encoding="utf-8")
        return ReportedStamp(src, src, added, duplicate)

    if src.parent != scratchpad_dir / "active":
        raise click.ClickException(
            f"{src} is outside .pkit/scratchpad/active/ — only active (or "
            "already-reported) notes can be stamped reported."
        )

    dst = scratchpad_dir / "reported" / src.name
    if dst.exists():
        raise click.ClickException(f"target already exists at {dst.relative_to(target_root)}.")
    _refuse_unrecordable(content, first=True, project=project, workstream=workstream)
    new_content = _insert_reported_frontmatter(
        content,
        tuple(normalized),
        hash_value=content_hash(content),
        date=_today(),
        project=project,
        workstream=workstream,
    )
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(new_content, encoding="utf-8")
        src.unlink()
    return ReportedStamp(src, dst, tuple(normalized), ())


def refuse_unrecordable_send(
    target_root: Path,
    note: Path,
    content: str,
    *,
    project: str | None = None,
    workstream: str | None = None,
) -> None:
    """Refuse, before a report sends `note`, a send that its stamp would refuse
    to record (`_refuse_unrecordable`), so nothing is posted that the note
    cannot record (#2923). `project` and `workstream` are what the stamp would
    write. A note outside `active/` and `reported/` is never stamped, and is
    never refused here."""
    area = target_root / ".pkit" / "scratchpad"
    if note.parent == area / "active":
        _refuse_unrecordable(content, first=True, project=project, workstream=workstream)
    elif note.parent == area / "reported":
        _refuse_unrecordable(content, first=False)


def note_is_drifted(content: str) -> bool:
    """True iff a reported note's current content diverges from its stamped
    hash (post-send edit — surfaced as a warning, never a gate; COR-043).

    The hash is read from the reported block's own line (`_reported_block`),
    so a frontmatter holding a key twice, the note's and the stamp's, is still
    checked. A hash the frontmatter records outside such a block is compared
    with the whole file, and reads as drift: the stamp's fields were edited."""
    lines = content.split("\n")
    try:
        block = _reported_block(lines, _frontmatter_close(lines))
    except click.ClickException:
        return False
    if block is None:
        stored = _read_frontmatter_data(content).get("reported_hash")
    else:
        stored = lines[block[1]].removeprefix("reported_hash:").strip()
    if not isinstance(stored, str) or not stored:
        return False
    return content_hash(_strip_reported_frontmatter(content)) != stored


def drifted_reported_notes(target_root: Path) -> list[str]:
    """Names of `reported/` notes whose content has drifted from the stamped
    hash. Empty when the directory is absent (the lazy-dir normal state)."""
    reported_dir = target_root / ".pkit" / "scratchpad" / "reported"
    if not reported_dir.is_dir():
        return []
    return [
        path.name
        for path in sorted(reported_dir.glob("*.md"))
        if note_is_drifted(path.read_text(encoding="utf-8"))
    ]


def read_reported_refs(content: str) -> tuple[str, ...]:
    """The `reported_to` refs recorded in a note's frontmatter."""
    data = _read_frontmatter_data(content)
    raw = data.get("reported_to")
    if not isinstance(raw, list):
        return ()
    return tuple(str(item) for item in raw if item)


def list_notes(target_root: Path) -> list[NoteEntry]:
    """Every scratchpad note, grouped by state folder. Reported notes carry
    their refs resolved **live** via `resolve_ref` (pull-only, nothing
    stored — COR-043; offline degrades to "unknown") and a drift flag."""
    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    entries: list[NoteEntry] = []
    for state in _ALL_STATES:
        state_dir = scratchpad_dir / state
        if not state_dir.is_dir():
            continue
        for path in sorted(state_dir.glob("*.md")):
            if state != "reported":
                entries.append(NoteEntry(path.name, state))
                continue
            content = path.read_text(encoding="utf-8")
            refs = tuple(resolve_ref(ref) for ref in read_reported_refs(content))
            entries.append(NoteEntry(path.name, state, refs=refs, drifted=note_is_drifted(content)))
    return entries


def outcome(target_root: Path) -> Outcome:
    """The `scratchpad` member of `pkit validate`: each note lies in one state
    folder, which is its state (COR-012). A slug whose notes lie in more than
    one state folder is an error, one for each such slug, naming each of its
    files. Two notes of one slug in one folder are not this member's concern.
    Only `.md` files are notes."""
    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    by_slug: dict[str, list[Path]] = {}
    for state in _ALL_STATES:
        state_dir = scratchpad_dir / state
        if not state_dir.is_dir():
            continue
        for path in sorted(state_dir.glob("*.md")):
            if path.is_file():
                by_slug.setdefault(note_slug(path.name), []).append(path)
    findings: list[Finding] = []
    for slug, paths in sorted(by_slug.items()):
        states = len({path.parent.name for path in paths})
        if states > 1:
            files = ", ".join(path.relative_to(target_root).as_posix() for path in paths)
            findings.append(
                Finding(
                    f".pkit/scratchpad :: {slug}",
                    f"slug {slug!r} is in {states} state folders: {files}. A note lies in one "
                    "state folder, which is its state (COR-012). Keep the note in the folder "
                    "of its state, and remove or rename each other file.",
                )
            )
    notes = sum(len(paths) for paths in by_slug.values())
    return Outcome(
        (f"{notes} scratchpad note(s) checked; {len(findings)} error(s).",),
        tuple(findings),
    )


def resolve_ref(ref: str) -> ReportedRefState:
    """Live upstream view of `owner/repo#N` via ONE `gh` read: its state
    ("open" / "closed") plus title + url (#678 — the same single read that
    used to fetch state alone), degrading to state "unknown" with empty
    title/url offline or on any failure (COR-043: never blocking, never
    guessing). Cross-repo *read* — unrestricted per COR-039."""
    owner_repo, _, number = ref.partition("#")
    data = _gh_json(
        ["gh", "issue", "view", number, "--repo", owner_repo, "--json", "state,title,url"]
    )
    if isinstance(data, dict) and isinstance(data.get("state"), str):
        state = data["state"].lower()
        if state in ("open", "closed"):
            return ReportedRefState(
                ref,
                state,
                title=str(data.get("title", "")),
                url=str(data.get("url", "")),
            )
    return ReportedRefState(ref, "unknown")


def _gh_json(args: list[str]) -> object | None:
    """Run a `gh … --json …` read and parse its JSON; None on any failure."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None


def _frontmatter_close(lines: list[str]) -> int:
    """Index of the closing `---` line of the frontmatter block; raises when
    the note has no well-formed frontmatter."""
    if not lines or lines[0].strip() != "---":
        raise click.ClickException("scratchpad note has no frontmatter block.")
    for i in range(1, len(lines)):
        if re.match(r"^---\s*$", lines[i]):
            return i
    raise click.ClickException("scratchpad note has no closing frontmatter delimiter.")


def _insert_reported_frontmatter(
    content: str,
    refs: tuple[str, ...],
    *,
    hash_value: str,
    date: str,
    project: str | None,
    workstream: str | None,
) -> str:
    """Insert the reported block before the closing frontmatter delimiter,
    leaving every existing byte untouched (drift-hash fidelity)."""
    lines = content.split("\n")
    close = _frontmatter_close(lines)
    block = [f"reported: {date}", "reported_to:"]
    block.extend(f"  - {ref}" for ref in refs)
    block.append(f"reported_hash: {hash_value}")
    if project:
        block.append(f"project: {project}")
    if workstream:
        block.append(f"workstream: {workstream}")
    return "\n".join(lines[:close] + block + lines[close:])


def _append_reported_refs(content: str, refs: tuple[str, ...], hash_value: str) -> str:
    """Append refs to an existing `reported_to` list and refresh the hash line."""
    lines = content.split("\n")
    close = _frontmatter_close(lines)
    try:
        head = next(i for i in range(1, close) if lines[i].startswith("reported_to:"))
    except StopIteration:
        raise click.ClickException("reported note has no reported_to frontmatter list.") from None
    end = head + 1
    while end < close and (lines[end].startswith(" ") or lines[end].startswith("\t")):
        end += 1
    new_lines = lines[:end] + [f"  - {ref}" for ref in refs] + lines[end:]
    return "\n".join(
        f"reported_hash: {hash_value}" if line.startswith("reported_hash:") else line
        for line in new_lines
    )


def _refuse_unrecordable(
    content: str,
    *,
    first: bool,
    project: str | None = None,
    workstream: str | None = None,
) -> None:
    """Refuse a stamp that would leave a key twice in the note's front matter
    (#2923), naming each key and its lines. A key the front matter holds twice
    already refuses any stamp. A first send also refuses each field it writes
    that the front matter holds: `reported`, `reported_to`, `reported_hash`,
    and `project` or `workstream` where it writes them. A later send writes
    into the stamp's own block only, and adds no key."""
    keys = _frontmatter_keys(content)
    _refuse_keys_held_twice(keys)
    if not first:
        return
    written: set[str] = set(_STAMP_FIELDS)
    if project:
        written.add("project")
    if workstream:
        written.add("workstream")
    held = [f"{key!r} on line {line}" for key, line in keys if key in written]
    if held:
        raise click.ClickException(
            "the note's front matter holds a field that recording the send writes as "
            f"well, so it would hold the key twice: {'; '.join(held)}. Rename the note's "
            "own field, then run the command again."
        )


def _refuse_keys_held_twice(keys: list[tuple[str, int]]) -> None:
    """Refuse a note whose front matter holds a key twice, which no YAML read
    of it accepts, naming each such key and its lines."""
    lines_by_key: dict[str, list[int]] = {}
    for key, line in keys:
        lines_by_key.setdefault(key, []).append(line)
    twice = [
        f"{key!r} on lines {_joined([str(line) for line in lines])}"
        for key, lines in lines_by_key.items()
        if len(lines) > 1
    ]
    if twice:
        raise click.ClickException(
            f"the note's front matter holds a key twice, so it does not read: "
            f"{'; '.join(twice)}. Keep one of each, then run the command again."
        )


def _frontmatter_keys(content: str) -> list[tuple[str, int]]:
    """Each top-level key of a note's front matter with its line number in the
    file, in order. A key held twice is listed twice: the composed nodes hold
    every key, where a YAML load refuses the second. Empty where the note has
    no front matter, or front matter that does not parse as a mapping."""
    lines = content.split("\n")
    composer: Any = YAML()  # ruamel's composer and nodes are untyped
    try:
        close = _frontmatter_close(lines)
        root: Any = composer.compose(io.StringIO("\n".join(lines[1:close])))
    except (click.ClickException, YAMLError):
        return []
    if not isinstance(root, MappingNode):
        return []
    held: Any = getattr(root, "value", ())
    keys: list[tuple[str, int]] = []
    for key_node, _value_node in held:
        if isinstance(key_node, ScalarNode):
            mark: Any = getattr(key_node, "start_mark", None)
            keys.append((str(getattr(key_node, "value", "")), int(mark.line) + 2))
    return keys


def _joined(items: list[str]) -> str:
    """`a`, `a and b`, or `a, b and c`."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _reported_block(lines: list[str], close: int) -> tuple[int, int, int] | None:
    """The reported block in a note's frontmatter, as `(start, hash_line, end)`
    line indices: the fields the stamp wrote, laid out as
    `_insert_reported_frontmatter` writes them and `_append_reported_refs`
    keeps them. That is `reported`, `reported_to` and its items,
    `reported_hash`, then `project` and `workstream` where the stamp wrote
    them. The last such run before the closing delimiter, since the stamp
    inserts its block last; None where the frontmatter holds none. A field
    the note held before the stamp lies above the block, whatever its name."""
    found = None
    for start in range(1, close - 1):
        if not (
            lines[start].startswith("reported:") and lines[start + 1].startswith("reported_to:")
        ):
            continue
        hash_line = start + 2
        while hash_line < close and lines[hash_line].startswith((" ", "\t")):
            hash_line += 1
        if hash_line == close or not lines[hash_line].startswith("reported_hash:"):
            continue
        end = hash_line + 1
        for key in ("project:", "workstream:"):
            if end < close and lines[end].startswith(key):
                end += 1
        found = (start, hash_line, end)
    return found


def _strip_reported_frontmatter(content: str) -> str:
    """The note as it was at send time: current content minus the reported
    block (`_reported_block`), so only the fields the stamp wrote. The
    drift-hash view, and the text the first stamp hashed (#2918). Content
    with no such block is returned whole."""
    lines = content.split("\n")
    try:
        block = _reported_block(lines, _frontmatter_close(lines))
    except click.ClickException:
        return content
    if block is None:
        return content
    start, _hash_line, end = block
    return "\n".join(lines[:start] + lines[end:])


def _read_frontmatter_data(content: str) -> dict:
    """Parse a note's frontmatter into a plain mapping; {} on any malformation."""
    try:
        fm_yaml, _body = _split_frontmatter(content)
    except click.ClickException:
        return {}
    try:
        data = YAML().load(io.StringIO(fm_yaml)) or {}
    except Exception:  # ruamel raises library-specific errors on bad YAML
        return {}
    return data if isinstance(data, dict) else {}


def _slug_to_title(slug: str) -> str:
    """Convert kebab-case slug to a Title Case starting point for the H1.

    The author edits the H1 to whatever reads best; this is just a seed.
    """
    return slug.replace("-", " ").capitalize()


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise click.ClickException(
            "slug must be kebab-case (lowercase letters, digits, single hyphens)."
        )


def _today() -> str:
    """Today's date as ISO 8601 (`YYYY-MM-DD`). Indirected for test pinning."""
    return _today_date().isoformat()


def _today_date() -> _dt.date:
    """Today as a `datetime.date`. Indirected for test pinning; used directly
    when handing the value to a YAML serialiser that distinguishes date
    objects from strings (bare vs quoted scalar)."""
    return _dt.date.today()


def _resolve_author() -> str:
    """Read git config user.name / user.email; format as `Name <email>`."""
    name = _git_config("user.name")
    email = _git_config("user.email")
    if name and email:
        return f"{name} <{email}>"
    if name:
        return name
    return "<unknown>"


def _git_config(key: str) -> str:
    try:
        result = subprocess.run(["git", "config", key], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
