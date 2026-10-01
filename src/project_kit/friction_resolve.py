"""`pkit friction resolve`: a merge's conflicting revalidation, resolved as text (COR-050 point 3).

When two lines of work revalidate the same artefact, its `revalidated` block
conflicts on merge, and the person resolving the conflict revalidates the
combined state; nothing merges the two automatically, since that would claim
a revalidation nobody made (point 3). This command does the mechanical half
of that and none of the answer:

- **Only during a merge.** The base side is the one being merged in —
  `MERGE_HEAD`, as when the default branch is merged into a branch — and this
  branch is `HEAD`. Outside a merge there is nothing to resolve.
- **Read from the index, never from the markers.** A conflicted file's three
  versions are git's stages — the common ancestor, this branch's, the base
  side's — read byte for byte (`git cat-file blob`, the exact form of `git
  show :<n>:<path>`) and parsed as discovery parses a file, so line endings
  and front matter in flow style need nothing of their own.
- **The blocks aside, the rest is git's merge.** In each version every
  artefact's `revalidated` block — its key through the end of its value — is
  replaced by one token, the same in all three, and the versions are merged
  again (`git merge-file`, with the histogram diff git's own merge uses where
  this git offers it). A clean merge means every conflict lay inside those
  blocks; each token is then replaced by the block a three-way merge of the
  parsed blocks gives — the side that changed it, or the base side's where
  both did — the result is read back, and the file is written and staged.
  A conflict anywhere else — the body, another field, the anchors — leaves
  the file as git left it, and says where.
- **It writes no answer.** `at`, `outcome` and `unchanged-because` are the
  base side's as written. Each artefact both sides revalidated owes a
  revalidation of the combined state, and the command names it with the
  outcome its content bears out against the base side's — `updated` when it
  differs, `unchanged` when it does not — as the change check will judge it
  once the merge is committed.
"""

from __future__ import annotations

import difflib
import json
import re
import secrets
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, cast

from project_kit import cli_render
from project_kit.backbone_schemas import CONTAINER_KEY
from project_kit.friction_check import SHORT, commit_of, content, run_git
from project_kit.friction_discovery import (
    FRICTION_KEY,
    Anchor,
    Artefact,
    ArtefactKind,
    DiscoveredFile,
    Discovery,
    discover_artefacts,
    held_message,
    line_break,
    parse_artefacts,
    split_front_matter,
    universal_newlines,
)
from project_kit.friction_report import BECAUSE, REASON
from project_kit.friction_write import (
    OUTCOMES,
    REVALIDATED,
    UNCHANGED,
    carrier_keys,
    command_line,
    key_span,
    replace_file,
)
from project_kit.working_tree import nul_separated

UPDATED = OUTCOMES[0]

# The index's stages of a path in conflict (`git ls-files -u`).
_ANCESTOR, _THIS, _BASE = 1, 2, 3

# What a stage's mode is for a file whose text can be merged; a link or a
# submodule is not one.
_FILE_MODES = frozenset({"100644", "100755"})

# A line opening a conflict region, as git writes one into the working tree.
_CONFLICT_MARKER = re.compile(r"^<{7}(?: |\r?$)", re.MULTILINE)

# `git merge-file` exits with how many conflicts it left, at most 127; 129
# is a usage error — an option this git does not know.
_CONFLICTS = tuple(range(128))
_USAGE = 129
_HISTOGRAM = "--diff-algorithm=histogram"

# An artefact across the three versions: a file's one document, or an entry by id.
_Key = tuple[ArtefactKind, str | None]

#: The version of the document `render_json` returns, under the rule every reading
#: document of the `friction` group follows: raised when a key a reader relies on
#: changes its meaning or goes, never for a key added.
RESOLVE_SCHEMA_VERSION = 1


class FileStatus(Enum):
    """What the command did with a file. The values are the `status` field of the JSON output."""

    RESOLVED = "resolved"  # every conflict lay inside `revalidated` blocks: written and staged
    LEFT = "left"  # a conflict lies elsewhere: left as git left it
    SKIPPED = "skipped"  # not in conflict, or not an artefact's file


@dataclass(frozen=True)
class Owed:
    """An artefact both sides revalidated: it now carries the base side's answer, and owes
    a revalidation of the combined state once the merge is committed (COR-050 point 3)."""

    artefact: str  # its id
    location: str
    answer: Any  # the base side's `revalidated` block, as written
    outcome: str  # what its content bears out against the base side's: updated or unchanged
    why: str
    command: str  # the revalidation, with a placeholder where a person's words go
    dropped: tuple[Anchor, ...] = ()  # this branch's deferrals the base side's block lacks


@dataclass(frozen=True)
class FileResult:
    """One file the command looked at. `before` and `after` are a resolved file's text as
    the working tree holds it and as it is written."""

    path: str
    status: FileStatus
    reason: str | None = None
    owed: tuple[Owed, ...] = ()
    before: str = ""
    after: str = ""


@dataclass(frozen=True)
class Resolution:
    """What `pkit friction resolve` found: the merge, if one is in progress, and each file.
    `note` says why there is nothing to resolve, when there is not."""

    merge_head: str | None
    files: tuple[FileResult, ...]
    note: str | None = None

    @property
    def resolved(self) -> tuple[FileResult, ...]:
        return tuple(f for f in self.files if f.status is FileStatus.RESOLVED)

    @property
    def left(self) -> tuple[FileResult, ...]:
        return tuple(f for f in self.files if f.status is FileStatus.LEFT)

    @property
    def exit_code(self) -> int:
        """1 while an artefact's file it was asked about stays in conflict; else 0."""
        return 1 if self.left else 0


# --- the plan ------------------------------------------------------------------------


def plan_resolve(target_root: Path, paths: Sequence[str] = ()) -> Resolution:
    """What resolving the merge in progress would do, to `paths` — repository-relative —
    or, with none named, to every file in conflict. Reads; writes nothing."""
    merge_head = commit_of(target_root, "MERGE_HEAD")
    unmerged = _unmerged(target_root)
    if merge_head is None:
        note = "no merge is in progress: nothing to resolve"
        if unmerged:
            note += (
                " — the files in conflict come from a rebase, a cherry-pick or another "
                "operation, whose sides are not a merge's; resolve them by hand"
            )
        return Resolution(merge_head=None, files=(), note=note + ".")
    wanted = [_repository_path(p) for p in paths] or sorted(unmerged)
    if not wanted:
        return Resolution(merge_head, (), note="no file is in conflict: nothing to resolve.")
    discovery = discover_artefacts(target_root)
    walked = {f.path: f for f in discovery.files}
    nonce = secrets.token_hex(8)
    files = tuple(
        _file(target_root, rel, unmerged.get(rel), discovery, walked.get(rel), nonce)
        for rel in dict.fromkeys(wanted)
    )
    return Resolution(merge_head, files)


def _repository_path(given: str) -> str:
    """A path as the other friction commands name a file: relative to the project root."""
    return PurePosixPath(given).as_posix()


@dataclass(frozen=True)
class _Stage:
    mode: str
    blob: str


def _unmerged(root: Path) -> dict[str, dict[int, _Stage]]:
    """Every path in conflict, with the stages the index holds for it: 1 the common
    ancestor, 2 this branch's (`HEAD`), 3 the base side's (`MERGE_HEAD`)."""
    stages: dict[str, dict[int, _Stage]] = {}
    for record in nul_separated(run_git(root, "ls-files", "-u", "-z").stdout):
        meta, _, rel = record.partition("\t")
        mode, blob, stage = meta.split(" ")
        stages.setdefault(rel, {})[int(stage)] = _Stage(mode, blob)
    return stages


def _file(
    root: Path,
    rel: str,
    stages: Mapping[int, _Stage] | None,
    discovery: Discovery,
    found: DiscoveredFile | None,
    nonce: str,
) -> FileResult:
    if stages is None:
        return FileResult(rel, FileStatus.SKIPPED, "not in conflict: nothing to resolve")
    held = discovery.holding(rel)
    if held is not None:
        return FileResult(rel, FileStatus.SKIPPED, held_message(held))
    if found is None:
        return FileResult(
            rel,
            FileStatus.SKIPPED,
            "no declared place holds it, so it is no artefact's file; resolve it as any other",
        )
    return _resolve(root, rel, stages, found, nonce)


# --- one file ------------------------------------------------------------------------


@dataclass(frozen=True)
class _Stamp:
    """One artefact's `revalidated` block as one version writes it: its value as written,
    and its text — the key through the end of its value — at `start` in that version."""

    value: Any
    start: int
    written: str

    @property
    def end(self) -> int:
        return self.start + len(self.written)


@dataclass(frozen=True)
class _Version:
    """One of the three versions of a file, read with `\\n` line breaks."""

    text: str
    artefacts: Mapping[_Key, Artefact]
    stamps: Mapping[_Key, _Stamp]


_NO_VERSION = _Version("", {}, {})


def _left(rel: str, reason: str) -> FileResult:
    return FileResult(rel, FileStatus.LEFT, reason)


def _resolve(
    root: Path, rel: str, stages: Mapping[int, _Stage], found: DiscoveredFile, nonce: str
) -> FileResult:
    if _THIS not in stages or _BASE not in stages:
        gone = "this branch" if _THIS not in stages else "the base side"
        return _left(rel, f"removed on {gone} and changed on the other: keep it or remove it")
    if any(stage.mode not in _FILE_MODES for stage in stages.values()):
        return _left(rel, "not a regular file on every side")
    try:
        before = (root / rel).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _left(rel, f"cannot read it: {exc}")
    if not _CONFLICT_MARKER.search(before):
        return FileResult(
            rel,
            FileStatus.SKIPPED,
            "it holds no conflict marker any more — resolved by hand already, so it is left "
            "as it is; `git add` it when it is done",
        )
    written: dict[int, str] = {}
    for number, stage in stages.items():
        try:
            written[number] = run_git(root, "cat-file", "blob", stage.blob).stdout.decode("utf-8")
        except UnicodeDecodeError:
            return _left(rel, "a side is not UTF-8 text")
    newlines = {line_break(text) for text in written.values()}
    newline = newlines.pop() if len(newlines) == 1 else None
    if newline is None:
        return _left(
            rel,
            "its sides are written with different line endings, or one mixes them, so no "
            "one line ending would keep the merge's other bytes",
        )

    versions: dict[int, _Version] = {}
    for number, text in written.items():
        version = _read_version(rel, found, universal_newlines(text))
        if isinstance(version, str):
            if number == _ANCESTOR:
                version = _Version(universal_newlines(text), {}, {})
            else:
                side = "this branch" if number == _THIS else "the base side"
                return _left(rel, f"on {side}, {version}")
        versions[number] = version
    ancestor = versions.get(_ANCESTOR, _NO_VERSION)
    this, base = versions[_THIS], versions[_BASE]

    keys = sorted(
        {*ancestor.stamps, *this.stamps, *base.stamps}, key=lambda k: (k[0].value, k[1] or "")
    )
    tokens = {key: f"@pkit-friction-resolve-{nonce}-{n}@" for n, key in enumerate(keys)}
    decided = {
        key: _decide(ancestor.stamps.get(key), this.stamps.get(key), base.stamps.get(key))
        for key in keys
    }
    both = [key for key, (_stamp, owed) in decided.items() if owed]
    tokened = {n: _tokened(version, tokens) for n, version in versions.items()}
    merged = _merged(root, tokened[_THIS], tokened.get(_ANCESTOR, ""), tokened[_BASE])
    if merged is None:
        reason = _where(root, tokened)
        if both:
            named = ", ".join(base.artefacts[key].location for key in both)
            reason += (
                f"; the `revalidated` block of {named} conflicts too — take the base side's, "
                f"and revalidate the combined state once the merge is committed"
            )
        return _left(rel, reason)

    resolved = _read_back(rel, found, merged, tokens, {k: s for k, (s, _o) in decided.items()})
    if resolved is None:
        return _left(
            rel,
            "the merge would drop, repeat or misplace a `revalidated` block, so it cannot be "
            "resolved as text",
        )
    text, artefacts = resolved
    owed = tuple(
        _owed(artefacts[key], base.artefacts[key], this.artefacts.get(key), ancestor, key)
        for key in both
    )
    after = text if newline == "\n" else text.replace("\n", newline)
    return FileResult(rel, FileStatus.RESOLVED, owed=owed, before=before, after=after)


def _read_version(rel: str, found: DiscoveredFile, text: str) -> _Version | str:
    """One version's artefacts and where each `revalidated` block is written in it, or
    why it cannot be read."""
    artefacts, reason = parse_artefacts(rel, found.places[0], text, rule_set=found.rule_set)
    if reason is not None:
        return f"its front matter does not parse ({reason})"
    front_matter, _body = split_front_matter(text)
    offset = text.find("\n") + 1  # the front matter starts after its opening line
    stamps: dict[_Key, _Stamp] = {}
    for artefact in artefacts:
        present, value = _written_block(artefact)
        if not present or front_matter is None:
            continue
        keys = (*carrier_keys(artefact), CONTAINER_KEY, FRICTION_KEY, REVALIDATED)
        span = key_span(front_matter, keys)
        if span is None:
            return (
                f"the `revalidated` block of {artefact.location} is not written directly "
                f"(a YAML alias or merge key)"
            )
        start, end = span
        stamps[_key(artefact)] = _Stamp(value, offset + start, front_matter[start:end])
    return _Version(text, {_key(a): a for a in artefacts}, stamps)


def _key(artefact: Artefact) -> _Key:
    return (artefact.kind, None if artefact.kind is ArtefactKind.DOCUMENT else artefact.id)


def _written_block(artefact: Artefact) -> tuple[bool, Any]:
    """Whether the artefact's friction block writes `revalidated`, and its value as written."""
    block = artefact.friction
    if not isinstance(block, Mapping):
        return False, None
    mapping = cast("Mapping[str, Any]", block)
    return REVALIDATED in mapping, mapping.get(REVALIDATED)


def _decide(
    ancestor: _Stamp | None, this: _Stamp | None, base: _Stamp | None
) -> tuple[_Stamp | None, bool]:
    """The block a three-way merge of the parsed blocks gives — the side that changed it, or
    the base side's where both did — and whether a revalidation is owed: both changed it,
    and the base side's still has one."""
    if _same(this, base) or _same(this, ancestor):
        return base, False
    if _same(base, ancestor):
        return this, False
    return base, base is not None


def _same(one: _Stamp | None, other: _Stamp | None) -> bool:
    if one is None or other is None:
        return one is other
    return one.value == other.value


def _tokened(version: _Version, tokens: Mapping[_Key, str]) -> str:
    """The version with each `revalidated` block replaced by its artefact's token."""
    text = version.text
    for key, stamp in sorted(version.stamps.items(), key=lambda item: -item[1].start):
        text = text[: stamp.start] + tokens[key] + text[stamp.end :]
    return text


def _read_back(
    rel: str,
    found: DiscoveredFile,
    merged: str,
    tokens: Mapping[_Key, str],
    chosen: Mapping[_Key, _Stamp | None],
) -> tuple[str, Mapping[_Key, Artefact]] | None:
    """The merge with each token replaced by the block chosen for it, and its artefacts —
    `None` unless every token stands once where a block is chosen, and the result reads
    back with exactly those blocks."""
    text = merged
    for key, token in tokens.items():
        stamp, count = chosen[key], merged.count(token)
        if stamp is None and count == 0:
            continue
        if stamp is None or count != 1:
            return None
        text = text.replace(token, stamp.written)
    artefacts, reason = parse_artefacts(rel, found.places[0], text, rule_set=found.rule_set)
    if reason is not None:
        return None
    by_key = {_key(a): a for a in artefacts}
    for key, stamp in chosen.items():
        artefact = by_key.get(key)
        if stamp is not None and (
            artefact is None or _written_block(artefact) != (True, stamp.value)
        ):
            return None
    return text, by_key


def _owed(
    resolved: Artefact, base: Artefact, this: Artefact | None, ancestor: _Version, key: _Key
) -> Owed:
    """What an artefact both sides revalidated owes, with the outcome its content bears
    out against the base side's, as the change check will compare them (COR-050 point 5)."""
    if content(resolved) != content(base):
        outcome = UPDATED
        why = (
            "its content differs from the base side's (this branch changed its body or its "
            "own fields), and an `updated` revalidation takes no `--because`"
        )
        words = ("--outcome", UPDATED)
    else:
        outcome = UNCHANGED
        why = (
            "its content is the base side's (this branch changed nothing in it but its "
            "block): say why it still holds against this branch's change"
        )
        words = ("--outcome", UNCHANGED, "--because", BECAUSE)
    dropped = tuple(
        sorted(
            _deferred(this) - _deferred(base) - _deferred(ancestor.artefacts.get(key)),
            key=lambda anchor: (anchor.kind, anchor.value),
        )
    )
    return Owed(
        artefact=resolved.id,
        location=resolved.location,
        answer=_written_block(resolved)[1],
        outcome=outcome,
        why=why,
        command=command_line("pkit", "friction", "revalidate", resolved.location, *words),
        dropped=dropped,
    )


def _deferred(artefact: Artefact | None) -> set[Anchor]:
    """The anchors an artefact's block defers."""
    return set() if artefact is None else {d.anchor for d in artefact.deferrals}


def _where(root: Path, tokened: Mapping[int, str]) -> str:
    """Where a file conflicts once its `revalidated` blocks are set aside: its front matter,
    its body, or — when neither alone does — the file as a whole."""
    parts = {number: split_front_matter(text) for number, text in tokened.items()}
    found: list[str] = []
    if parts[_THIS][0] is not None and parts[_BASE][0] is not None:
        names = ("the front matter, outside the `revalidated` blocks", "the body")
        for index, name in enumerate(names):
            texts = [
                (parts[n][index] or "") if n in parts else "" for n in (_THIS, _ANCESTOR, _BASE)
            ]
            if _merged(root, *texts) is None:
                found.append(name)
    if not found:
        return "it conflicts outside the `revalidated` blocks"
    return "it conflicts in " + " and in ".join(found)


def _merged(root: Path, this: str, ancestor: str, base: str) -> str | None:
    """The three-way merge of the texts, or `None` where it conflicts: `git merge-file`, with
    the histogram diff git's own merge uses where this git offers it (git 2.44 on)."""
    with tempfile.TemporaryDirectory(prefix="pkit-friction-resolve-") as folder:
        files: list[str] = []
        for name, text in (("this", this), ("ancestor", ancestor), ("base", base)):
            path = Path(folder) / name
            path.write_bytes(text.encode("utf-8"))
            files.append(str(path))
        completed = run_git(
            root, "merge-file", "-p", "-q", _HISTOGRAM, *files, accept=(*_CONFLICTS, _USAGE)
        )
        if completed.returncode == _USAGE:  # a git before 2.44: its default diff
            completed = run_git(root, "merge-file", "-p", "-q", *files, accept=_CONFLICTS)
    return completed.stdout.decode("utf-8") if completed.returncode == 0 else None


# --- the write -----------------------------------------------------------------------


def apply(target_root: Path, resolution: Resolution) -> None:
    """Write each resolved file — refused, for a file, if it changed since it was read — and
    stage it."""
    for result in resolution.resolved:
        replace_file(target_root / result.path, result.path, result.before, result.after)
        run_git(target_root, "add", "--", f":(literal){result.path}")


# --- rendering -----------------------------------------------------------------------


def render_human(resolution: Resolution, *, dry_run: bool) -> str:
    """What was resolved, what was left and why, and the answer each artefact owes."""
    title = cli_render.style("title", "Friction resolve")
    if resolution.merge_head is None:
        return f"{title} — {resolution.note}\n"
    head = resolution.merge_head[:SHORT]
    lines = [f"{title} — the merge of {head} (MERGE_HEAD, the base side) into this branch", ""]
    if resolution.note:
        lines.append(f"  {resolution.note}")
    for result in resolution.files:
        lines.extend(_file_lines(result, dry_run))
    if any(result.owed for result in resolution.resolved):
        lines += [
            "",
            "The person resolving the conflict revalidates the combined state (COR-050 point 3):",
            "commit the merge, then run each command above with your words in place of the",
            "placeholder; `pkit friction check` names anything else this branch owes.",
        ]
    if resolution.left:
        lines += ["", "Resolve the files left by hand and `git add` them before committing."]
    if dry_run and resolution.resolved:
        lines += ["", cli_render.style("strong", "Dry run: nothing written.")]
    return "\n".join(lines) + "\n"


def _file_lines(result: FileResult, dry_run: bool) -> list[str]:
    if result.status is FileStatus.SKIPPED:
        return [f"  {result.path} — skipped: {result.reason}"]
    if result.status is FileStatus.LEFT:
        return [f"  {result.path} — left as git left it: {result.reason}"]
    done = "would be resolved and staged" if dry_run else "resolved and staged"
    lines = [f"  {result.path} — {done}"]
    for owed in result.owed:
        lines.append(f"    {owed.location} now carries the base side's answer: {_answer(owed)}")
        lines.append(f"      once the merge is committed, answer `{owed.outcome}` — {owed.why}:")
        lines.append(f"        {owed.command}")
        for anchor in owed.dropped:
            label = f"{anchor.kind}:{anchor.value}"
            defer = command_line(
                "pkit", "friction", "defer", owed.location, "--anchor", label, "--reason", REASON
            )
            lines.append(
                f"      this branch's deferral of {label} is not in the base side's block; "
                f"after revalidating, defer it again if it still stands:"
            )
            lines.append(f"        {defer}")
    if dry_run:
        diff = difflib.unified_diff(
            result.before.splitlines(keepends=True),
            result.after.splitlines(keepends=True),
            fromfile=f"a/{result.path}",
            tofile=f"b/{result.path}",
        )
        lines.extend("    " + line.rstrip("\r\n") for line in diff)
    return lines


def _answer(owed: Owed) -> str:
    """The base side's answer in one line: `at`, the outcome, and its justification."""
    answer: Any = owed.answer
    block: Mapping[str, Any] = (
        cast("Mapping[str, Any]", answer) if isinstance(answer, Mapping) else {}
    )
    at, outcome, because = block.get("at"), block.get("outcome"), block.get("unchanged-because")
    shown = f"at {at}, {outcome}"
    return f"{shown} — {because}" if isinstance(because, str) else shown


def render_json(resolution: Resolution, *, dry_run: bool) -> str:
    """The stable machine-readable resolution: keys sorted, the same bytes for the same state."""
    document = {
        "schema_version": RESOLVE_SCHEMA_VERSION,
        "report": "resolve",
        "dry_run": dry_run,
        "merging": resolution.merge_head is not None,
        "merge_head": resolution.merge_head,
        "note": resolution.note,
        "files": [
            {
                "path": result.path,
                "status": result.status.value,
                "staged": result.status is FileStatus.RESOLVED and not dry_run,
                "reason": result.reason,
                "owed": [
                    {
                        "artefact": owed.artefact,
                        "location": owed.location,
                        "base_answer": owed.answer,
                        "outcome": owed.outcome,
                        "why": owed.why,
                        "command": owed.command,
                        "dropped_deferrals": [
                            {"kind": anchor.kind, "value": anchor.value} for anchor in owed.dropped
                        ],
                    }
                    for owed in result.owed
                ],
            }
            for result in resolution.files
        ],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


__all__ = [
    "RESOLVE_SCHEMA_VERSION",
    "FileResult",
    "FileStatus",
    "Owed",
    "Resolution",
    "apply",
    "plan_resolve",
    "render_human",
    "render_json",
]
