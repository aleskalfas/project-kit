"""`pkit friction resolve`: a merge's conflicting revalidation, resolved as text (COR-050 point 3).

When two lines of work revalidate the same artefact, its `revalidated` block
conflicts on merge, and the person resolving the conflict revalidates the
combined state; nothing merges two revalidations automatically, since that
would claim a revalidation nobody made (point 3). This command does the
mechanical half of that and none of the answer:

- **Only during a merge.** The base side is the one being merged in —
  `MERGE_HEAD` — and this branch is `HEAD`. Outside a merge there is nothing
  to resolve.
- **Only git's own conflict, untouched.** A conflicted file's three versions
  are git's index stages, read byte for byte. `git merge-file` merges them
  again — in the conflict style the file shows, with the histogram diff git's
  merge uses where this git offers it (2.44 on) — and the result must be the
  working file, conflict-marker labels and line endings aside. A file that
  differs, because the person already resolved or edited part of it, or
  because git merged it in a way this cannot reproduce, is refused and never
  overwritten.
- **Only conflicts inside `revalidated` blocks.** The same merge, with every
  conflict taken from this branch and again from the base side, gives git's
  merge of everything else; a block whose text differs between the two is
  one git conflicted on, and only those are decided. Each is replaced, in
  both, by its decision — and the two must then be equal, which holds only
  when every conflict region lies inside a replaced block. A conflict
  anywhere else — the body, another field, the anchors, a line beside a
  block — leaves the file as git left it, and says where. A block git merged
  cleanly keeps git's merge, byte for byte.
- **A decision merges the answer and the deferrals apart (points 3 and 4).**
  The answer — `at`, `outcome`, `unchanged-because` — comes from the side that
  changed it. Deferrals merge three ways by anchor, so parallel deferrals are
  kept; one anchor's deferral changed differently on both sides is left to
  the person. Where both sides revalidated — both changed `at` — the base
  side's answer is taken, and only when `MERGE_HEAD` is the change check's
  base (`resolve_base`): otherwise its answer would read in this branch's
  change check as a revalidation made here, which nobody made, so the block
  is left in conflict. A block one side removed and the other changed is left
  too, and said.
- **It writes no answer.** Each artefact both sides revalidated now carries
  the base side's answer as written, and owes a revalidation of the combined
  state once the merge is committed. The command names it with the outcome
  its content bears out against the base side's — `updated` when it differs,
  `unchanged` when it does not — as the change check judges it. The check
  requires that revalidation only where an anchor of the artefact changed on
  this branch; elsewhere it is point 3's rule for people, and the command's
  advice.
- **Staging is the person's.** The resolved file is written in the working
  file's own line endings; `git add` runs only with consent — `--yes`, or a
  terminal's confirmation — and `git checkout -m -- <path>` brings the
  conflict back, staged or not.
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

import click

from project_kit import cli_render
from project_kit.backbone_schemas import CONTAINER_KEY
from project_kit.friction_check import (
    SHORT,
    FrictionCheckError,
    commit_of,
    content,
    parsed_at,
    resolve_base,
    run_git,
)
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
from project_kit.friction_report import BECAUSE
from project_kit.friction_write import (
    DEFERRED,
    OUTCOMES,
    REVALIDATED,
    UNCHANGED,
    FileNotReplaced,
    carrier_keys,
    command_line,
    key_span,
    replace_file,
    written_key,
)
from project_kit.working_tree import nul_separated

UPDATED = OUTCOMES[0]

# The index's stages of a path in conflict (`git ls-files -u`).
_ANCESTOR, _THIS, _BASE = 1, 2, 3

# What a stage's mode is for a file whose text can be merged; a link or a
# submodule is not one.
_FILE_MODES = frozenset({"100644", "100755"})

# A line opening a conflict region, and one opening its common ancestor's part
# (the `diff3` and `zdiff3` styles), as git writes them into the working tree.
_CONFLICT_MARKER = re.compile(r"^<{7}(?: |\r?$)", re.MULTILINE)
_ANCESTOR_MARKER = re.compile(r"^\|{7}(?: |\r?$)", re.MULTILINE)

# A marker line with its label, which names the sides and differs between git's
# merge and `git merge-file`; it is compared without one.
_MARKER_LABEL = re.compile(r"^([<|>])\1{6}(?: [^\n]*)?$", re.MULTILINE)

# `git merge-file` exits with how many conflicts it left, at most 127; 129
# is a usage error — an option this git does not know.
_CONFLICTS = tuple(range(128))
_USAGE = 129
_HISTOGRAM = "--diff-algorithm=histogram"

# An artefact across the versions: a file's one document, or an entry by id.
_Key = tuple[ArtefactKind, str | None]

# A block absent from a version, so that it compares unequal to one written empty.
_ABSENT = object()

#: The version of the document `render_json` returns, under the rule every reading
#: document of the `friction` group follows: raised when a key a reader relies on
#: changes its meaning or goes, never for a key added.
RESOLVE_SCHEMA_VERSION = 1


class FileStatus(Enum):
    """What the command did with a file. The values are the `status` field of the JSON output."""

    RESOLVED = "resolved"  # every conflict lay inside `revalidated` blocks: written
    LEFT = "left"  # a conflict it does not settle: the file left in conflict, untouched
    SKIPPED = "skipped"  # not in conflict any more, or not an artefact's file


@dataclass(frozen=True)
class Owed:
    """An artefact both sides revalidated: it now carries the base side's answer, and owes
    a revalidation of the combined state once the merge is committed (COR-050 point 3)."""

    artefact: str  # its id
    location: str
    answer: Any  # the base side's answer as written: `at`, `outcome`, `unchanged-because`
    outcome: str  # what its content bears out against the base side's: updated or unchanged
    why: str
    command: str  # the revalidation, with a placeholder where a person's words go


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
        """1 when an artefact's file is left in conflict; else 0, a skipped file included."""
        return 1 if self.left else 0


class FrictionResolveError(click.ClickException):
    """Writing or staging stopped partway; the message says what was done before it."""


# --- the plan ------------------------------------------------------------------------


@dataclass(frozen=True)
class _Context:
    """What every file of one run is judged against."""

    root: Path
    merge_head: str
    base_ref: str | None  # the change check's base, as resolved; `None` when it does not
    base_tip: str | None
    base_problem: str | None  # why the base does not resolve
    histogram: bool  # `git merge-file` takes the histogram diff (git 2.44 on)
    nonce: str

    def base_side_refusal(self, location: str) -> str | None:
        """Why the base side's answer cannot be taken for an artefact both sides revalidated,
        or `None` when it can: `MERGE_HEAD` is the change check's base tip."""
        if self.base_tip is not None and self.base_tip == self.merge_head:
            return None
        if self.base_tip is None:
            which = f"the change check's base does not resolve here ({self.base_problem})"
        else:
            which = (
                f"MERGE_HEAD {self.merge_head[:SHORT]} is not the change check's base "
                f"({self.base_ref} at {self.base_tip[:SHORT]})"
            )
        return (
            f"both sides revalidated {location}, and {which}: taken, the base side's answer "
            f"would read in this branch's change check as a revalidation made here, which "
            f"nobody made — resolve its `revalidated` block by hand and revalidate the "
            f"combined state once the merge is committed"
        )


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
    context = _context(target_root, merge_head)
    files = tuple(
        _file(context, rel, unmerged.get(rel), discovery, walked.get(rel))
        for rel in dict.fromkeys(wanted)
    )
    return Resolution(merge_head, files)


def _context(root: Path, merge_head: str) -> _Context:
    try:
        base = resolve_base(root)
    except FrictionCheckError as exc:
        ref, tip, problem = None, None, exc.message
    else:
        ref, tip, problem = base.ref, base.tip, None
    return _Context(
        root=root,
        merge_head=merge_head,
        base_ref=ref,
        base_tip=tip,
        base_problem=problem,
        histogram=_takes_histogram(root),
        nonce=secrets.token_hex(8),
    )


def _takes_histogram(root: Path) -> bool:
    """Whether this git's `merge-file` takes the histogram diff git's own merge uses."""
    with tempfile.TemporaryDirectory(prefix="pkit-friction-resolve-") as folder:
        empty = Path(folder) / "empty"
        empty.write_bytes(b"")
        files = [str(empty)] * 3
        completed = run_git(root, "merge-file", "-p", _HISTOGRAM, *files, accept=(0, _USAGE))
    return completed.returncode == 0


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
    context: _Context,
    rel: str,
    stages: Mapping[int, _Stage] | None,
    discovery: Discovery,
    found: DiscoveredFile | None,
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
    return _resolve(context, rel, stages, found)


# --- one file ------------------------------------------------------------------------


@dataclass(frozen=True)
class _Stamp:
    """One artefact's `revalidated` block as one version writes it: its value as written,
    its text — the key through the end of its value — at `start` in that version, the
    column its key starts at, and whether it sits in a mapping written in flow style."""

    value: Any
    start: int
    written: str
    column: int
    flow: bool

    @property
    def end(self) -> int:
        return self.start + len(self.written)


@dataclass(frozen=True)
class _Version:
    """One version of a file, read with `\\n` line breaks."""

    text: str
    artefacts: Mapping[_Key, Artefact]
    stamps: Mapping[_Key, _Stamp]


_NO_VERSION = _Version("", {}, {})


@dataclass(frozen=True)
class _Decision:
    """A conflicted block decided: its value, its text when one side wrote exactly that
    (`None` when it is written anew), and whether a revalidation is owed."""

    value: Any
    text: str | None
    owed: bool


def _left(rel: str, reason: str) -> FileResult:
    return FileResult(rel, FileStatus.LEFT, reason)


def _resolve(
    context: _Context, rel: str, stages: Mapping[int, _Stage], found: DiscoveredFile
) -> FileResult:
    if _THIS not in stages or _BASE not in stages:
        gone = "this branch" if _THIS not in stages else "the base side"
        return _left(rel, f"removed on {gone} and changed on the other: keep it or remove it")
    if any(stage.mode not in _FILE_MODES for stage in stages.values()):
        return _left(rel, "not a regular file on every side")
    try:
        before = (context.root / rel).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _left(rel, f"cannot read it: {exc}")
    if not _CONFLICT_MARKER.search(before):
        return FileResult(
            rel,
            FileStatus.SKIPPED,
            "it holds no conflict marker any more — resolved already, so it is left as it "
            "is; `git add` it when it is done",
        )
    newline = line_break(before)
    if newline is None:
        return _left(
            rel,
            "its working file mixes line endings, so no one line ending would keep its other bytes",
        )

    blobs = {n: run_git(context.root, "cat-file", "blob", s.blob).stdout for n, s in stages.items()}
    versions: dict[int, _Version] = {}
    for number, blob in blobs.items():
        try:
            text = universal_newlines(blob.decode("utf-8"))
        except UnicodeDecodeError:
            return _left(rel, "a side is not UTF-8 text")
        version = _read_version(rel, found, text)
        if isinstance(version, str):
            if number != _ANCESTOR:
                side = "this branch" if number == _THIS else "the base side"
                return _left(rel, f"on {side}, {version}")
            version = _Version(text, {}, {})
        versions[number] = version

    sides = _merge(context, blobs, before)
    if isinstance(sides, str):
        return _left(rel, sides)
    ours, theirs = (_read_version(rel, found, side) for side in sides)
    if isinstance(ours, str) or isinstance(theirs, str):
        reason = ours if isinstance(ours, str) else theirs
        return _left(rel, f"with each conflict taken from one side, {reason}")

    conflicted = sorted(
        (key for key in {*ours.stamps, *theirs.stamps} if _text(ours, key) != _text(theirs, key)),
        key=lambda k: (k[0].value, k[1] or ""),
    )
    ancestor = versions.get(_ANCESTOR, _NO_VERSION)
    this, base = versions[_THIS], versions[_BASE]
    decided: dict[_Key, _Decision | str] = {}
    texts: dict[_Key, str] = {}
    lopsided = False  # a conflicted block stands on one side of its conflict only
    for n, key in enumerate(conflicted):
        location = _location(key, base, this, ancestor, ours, theirs)
        decision = _decide(context, key, location, ancestor, this, base)
        if key not in ours.stamps or key not in theirs.stamps:
            lopsided = True
            if isinstance(decision, _Decision):
                decision = (
                    f"the `revalidated` block of {location} stands on one side of a conflict "
                    f"only: resolve it by hand"
                )
        decided[key] = decision
        if isinstance(decision, str):
            texts[key] = f"@pkit-friction-resolve-{context.nonce}-{n}@"
        else:
            target = ours.stamps[key]
            texts[key] = decision.text or written_key(
                REVALIDATED, decision.value, column=target.column, flow=target.flow
            )

    one, other = _spliced(ours, texts), _spliced(theirs, texts)
    refused = [d for d in decided.values() if isinstance(d, str)]
    where = None if one == other else _where(one, other, front_matter=not lopsided)
    if where is not None:
        notes = [
            decision if isinstance(decision, str) else _advice(key, decision, ours)
            for key, decision in decided.items()
        ]
        return _left(rel, "; ".join([where, *notes]))
    if refused:
        return _left(rel, "; ".join(refused))

    chosen = {k: d.value for k, d in decided.items() if isinstance(d, _Decision)}
    artefacts = _read_back(rel, found, one, chosen)
    if artefacts is None:
        return _left(
            rel,
            "its `revalidated` blocks would not read back as decided, so it cannot be "
            "resolved as text",
        )
    owed = tuple(
        _owed(artefacts[key], base.artefacts[key])
        for key, decision in decided.items()
        if isinstance(decision, _Decision) and decision.owed
    )
    after = one if newline == "\n" else one.replace("\n", newline)
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
        start = offset + span.start
        column = start - (text.rfind("\n", 0, start) + 1)
        written = front_matter[span.start : span.end]
        stamps[_key(artefact)] = _Stamp(value, start, written, column, span.flow)
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


def _text(version: _Version, key: _Key) -> str | None:
    stamp = version.stamps.get(key)
    return None if stamp is None else stamp.written


def _location(key: _Key, *versions: _Version) -> str:
    """Where the artefact is, as the friction commands name it: from the first version
    that holds it."""
    for version in versions:
        if key in version.artefacts:
            return version.artefacts[key].location
    return str(key[1])  # pragma: no cover — a key comes from a version's artefacts


# --- the decision --------------------------------------------------------------------


def _decide(
    context: _Context,
    key: _Key,
    location: str,
    ancestor: _Version,
    this: _Version,
    base: _Version,
) -> _Decision | str:
    """The block a conflicted artefact gets, or why it is left to the person (COR-050
    points 3 and 4).

    A block only one side changed is that side's. Where both did, the answer — every key
    but `deferred` — and the deferrals merge apart: the answer is the side's that changed
    it, and the base side's where both revalidated (`at` changed on both), which owes a
    revalidation; the deferrals merge three ways, by anchor.
    """
    a, t, b = (version.stamps.get(key) for version in (ancestor, this, base))
    av, tv, bv = (_ABSENT if s is None else s.value for s in (a, t, b))
    if tv in (bv, av) or bv == av:
        stamp, side = (t, "this branch") if bv == av and tv != bv else (b, "the base side")
        if stamp is None:
            return (
                f"{side} removed the `revalidated` block of {location} beside a change of "
                f"the other side's: resolve it by hand"
            )
        return _Decision(stamp.value, stamp.written, owed=False)
    if t is None or b is None:
        removed, changed = ("this branch", "the base side")
        if b is None:
            removed, changed = changed, removed
        return (
            f"{removed} removed the `revalidated` block of {location} and {changed} changed "
            f"it: keep it or remove it by hand"
        )
    if not all(isinstance(s.value, Mapping) for s in (a, t, b) if s is not None):
        return (
            f"the `revalidated` block of {location} is not a mapping on every side: resolve "
            f"it by hand"
        )
    try:
        chosen, owed = _answer(context, key, location, ancestor, this, base)
        deferrals = _deferrals(key, location, ancestor, this, base)
    except _Unsettled as exc:
        return exc.reason
    value: dict[str, Any] = dict(chosen)
    if deferrals is not _ABSENT:
        value[DEFERRED] = deferrals
    text = t.written if value == t.value else b.written if value == b.value else None
    return _Decision(value, text, owed)


class _Unsettled(Exception):
    """A part of a conflicted block this command does not settle: left to the person."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _block(version: _Version, key: _Key) -> Mapping[str, Any]:
    stamp = version.stamps.get(key)
    return {} if stamp is None else cast("Mapping[str, Any]", stamp.value)


def _answer(
    context: _Context,
    key: _Key,
    location: str,
    ancestor: _Version,
    this: _Version,
    base: _Version,
) -> tuple[Mapping[str, Any], bool]:
    """The answer the block keeps and whether a revalidation is owed for it; `_Unsettled`
    when it is left to the person."""
    aa, ta, ba = (
        {k: v for k, v in _block(version, key).items() if k != DEFERRED}
        for version in (ancestor, this, base)
    )
    if ta in (ba, aa):
        return ba, False
    if ba == aa:
        return ta, False
    before = ancestor.artefacts.get(key)
    was = parsed_at(before) if before is not None else None
    if parsed_at(this.artefacts[key]) == was or parsed_at(base.artefacts[key]) == was:
        raise _Unsettled(
            f"both sides changed the answer in the `revalidated` block of {location}, but "
            f"only one changed `at`: no two revalidations to settle — resolve it by hand"
        )
    refusal = context.base_side_refusal(location)
    if refusal is not None:
        raise _Unsettled(refusal)
    return ba, True


def _deferrals(key: _Key, location: str, ancestor: _Version, this: _Version, base: _Version) -> Any:
    """The `deferred` the block keeps — `_ABSENT` when none is written: as the side that
    changed it writes it, or, where both did, a three-way merge by anchor, sorted as the
    writers sort it (COR-050 point 4); `_Unsettled` when it is left to the person."""
    ad, td, bd = (_block(version, key).get(DEFERRED, _ABSENT) for version in (ancestor, this, base))
    if td in (bd, ad):
        return bd
    if bd == ad:
        return td
    sides = [_entries(version, key) for version in (ancestor, this, base)]
    if any(side is None for side in sides):
        raise _Unsettled(
            f"both sides changed the deferrals of {location}, and a side's `deferred` is not "
            f"one well-formed entry per anchor: resolve it by hand"
        )
    a_side, t_side, b_side = cast("list[dict[Anchor, Any]]", sides)
    merged: list[Any] = []
    for anchor in sorted({*a_side, *t_side, *b_side}, key=lambda x: (x.kind, x.value)):
        ae, te, be = a_side.get(anchor), t_side.get(anchor), b_side.get(anchor)
        if te in (be, ae):
            entry = be
        elif be == ae:
            entry = te
        else:
            raise _Unsettled(
                f"both sides changed the deferral of {anchor.kind}:{anchor.value} in "
                f"{location}, differently: resolve it by hand"
            )
        if entry is not None:
            merged.append(entry)
    return merged or _ABSENT


def _entries(version: _Version, key: _Key) -> dict[Anchor, Any] | None:
    """A version's deferrals of the artefact by anchor; `None` unless each entry is
    well-formed and names an anchor no other entry does."""
    raw = _block(version, key).get(DEFERRED)
    if raw is None:
        return {}
    artefact = version.artefacts.get(key)
    if not isinstance(raw, list) or artefact is None:
        return None
    entries = cast("list[Any]", raw)
    by_anchor = {d.anchor: entries[d.index] for d in artefact.deferrals}
    return by_anchor if len(by_anchor) == len(entries) else None


def _spliced(version: _Version, texts: Mapping[_Key, str]) -> str:
    """The version with each block `texts` names replaced by its text."""
    text = version.text
    stamps = [(version.stamps[key], new) for key, new in texts.items() if key in version.stamps]
    for stamp, new in sorted(stamps, key=lambda item: -item[0].start):
        text = text[: stamp.start] + new + text[stamp.end :]
    return text


def _advice(key: _Key, decision: _Decision, ours: _Version) -> str:
    """What to take for a decided block, in a file left for another conflict."""
    location = ours.artefacts[key].location
    if decision.owed:
        return (
            f"the `revalidated` block of {location} conflicts too: both sides revalidated "
            f"it — take the base side's answer, keep both sides' changes to `deferred`, and "
            f"revalidate the combined state once the merge is committed"
        )
    return f"the `revalidated` block of {location} conflicts too: keep what each side changed in it"


def _where(one: str, other: str, *, front_matter: bool) -> str | None:
    """Where a file still conflicts once its decided blocks are put in: its front matter,
    its body, or — when neither alone does — the file as a whole. Without `front_matter`
    — a block left to the person stands on one side only, so the front matters differ
    there anyway — only the body is told, and `None` when it does not conflict."""
    (fm_one, body_one), (fm_other, body_other) = split_front_matter(one), split_front_matter(other)
    found: list[str] = []
    if fm_one is not None and fm_other is not None:
        if front_matter and fm_one != fm_other:
            found.append("the front matter, outside the `revalidated` blocks")
        if body_one != body_other:
            found.append("the body")
    if found:
        return "it conflicts in " + " and in ".join(found)
    return "it conflicts outside the `revalidated` blocks" if front_matter else None


def _read_back(
    rel: str, found: DiscoveredFile, text: str, chosen: Mapping[_Key, Any]
) -> Mapping[_Key, Artefact] | None:
    """The resolution's artefacts — `None` unless it parses and every decided block reads
    back as decided."""
    artefacts, reason = parse_artefacts(rel, found.places[0], text, rule_set=found.rule_set)
    if reason is not None:
        return None
    by_key = {_key(a): a for a in artefacts}
    for key, value in chosen.items():
        artefact = by_key.get(key)
        if artefact is None or _written_block(artefact) != (True, value):
            return None
    return by_key


def _owed(resolved: Artefact, base: Artefact) -> Owed:
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
    block = _written_block(resolved)[1]
    answer = {k: v for k, v in cast("Mapping[str, Any]", block).items() if k != DEFERRED}
    return Owed(
        artefact=resolved.id,
        location=resolved.location,
        answer=answer,
        outcome=outcome,
        why=why,
        command=command_line("pkit", "friction", "revalidate", resolved.location, *words),
    )


# --- git's merge, reproduced ---------------------------------------------------------


def _merge(context: _Context, blobs: Mapping[int, bytes], working: str) -> tuple[str, str] | str:
    """Git's merge of the three stages with every conflict taken from this branch, and
    again from the base side, read with `\\n` line breaks — once `git merge-file` is seen
    to give the conflict `working` holds; else why the file is left."""
    algorithm = (_HISTOGRAM,) if context.histogram else ()
    styles: tuple[tuple[str, ...], ...] = (
        (("--diff3",), ("--zdiff3",)) if _ANCESTOR_MARKER.search(working) else ((),)
    )
    wanted = _unlabelled(working)
    with tempfile.TemporaryDirectory(prefix="pkit-friction-resolve-") as folder:
        files: list[str] = []
        for name, number in (("this", _THIS), ("ancestor", _ANCESTOR), ("base", _BASE)):
            path = Path(folder) / name
            path.write_bytes(blobs.get(number, b""))
            files.append(str(path))

        def merge_file(*flags: str) -> str:
            completed = run_git(
                context.root,
                "merge-file",
                "-p",
                "-q",
                *algorithm,
                *flags,
                *files,
                accept=_CONFLICTS,
            )
            return completed.stdout.decode("utf-8")

        style = next((s for s in styles if _unlabelled(merge_file(*s)) == wanted), None)
        if style is None:
            older = (
                ""
                if context.histogram
                else " (this git, before 2.44, lacks the histogram diff git's merge uses)"
            )
            return (
                f"it is not the conflict git left: part of it was resolved or edited by hand, "
                f"or git merged it in a way `git merge-file` does not reproduce here{older} — "
                f"so it is not overwritten; resolve it by hand"
            )
        ours = merge_file("--ours", *style)
        theirs = merge_file("--theirs", *style)
    return universal_newlines(ours), universal_newlines(theirs)


def _unlabelled(text: str) -> str:
    """A conflicted text with `\\n` line breaks and its conflict markers without labels."""
    return _MARKER_LABEL.sub(lambda m: m.group(1) * 7, universal_newlines(text))


# --- the write -----------------------------------------------------------------------


def write(target_root: Path, resolution: Resolution) -> tuple[str, ...]:
    """Write each resolved file — refused, for a file, if it changed since it was read — and
    return the paths written. A failure partway says which were written before it."""
    written: list[str] = []
    paths = [result.path for result in resolution.resolved]
    for result in resolution.resolved:
        try:
            replace_file(target_root / result.path, result.path, result.before, result.after)
        except (FileNotReplaced, OSError) as exc:
            why = exc.reason if isinstance(exc, FileNotReplaced) else f"{exc}."
            raise FrictionResolveError(
                f"{result.path} was not written: {why} "
                + _done(written, ())
                + f" Not written: {', '.join(paths[len(written) :])}."
            ) from exc
        written.append(result.path)
    return tuple(written)


def stage(target_root: Path, written: Sequence[str]) -> tuple[str, ...]:
    """`git add` each written file, one at a time, and return the paths staged. A failure
    partway says which were staged before it."""
    staged: list[str] = []
    for path in written:
        try:
            run_git(target_root, "add", "--", f":(literal){path}")
        except FrictionCheckError as exc:
            rest = list(written[len(staged) :])
            raise FrictionResolveError(
                f"staging {path} failed: {exc.message.rstrip('.')}. "
                + _done(written, staged)
                + f" Not staged: {', '.join(rest)} — `{command_line('git', 'add', '--', *rest)}` "
                f"stages them once the cause is fixed."
            ) from exc
        staged.append(path)
    return tuple(staged)


def _done(written: Sequence[str], staged: Sequence[str]) -> str:
    """What a run had done before a failure: the files written, and those staged."""
    if not written:
        return "This run wrote nothing before it."
    done = f"This run wrote {', '.join(written)}"
    done += f" and staged {', '.join(staged)}" if staged else ", staging none"
    return done + "; `git checkout -m -- <path>` brings a file's conflict back."


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
            "placeholder. The change check requires it where an anchor of the artefact changed",
            "on this branch; `pkit friction check` names those, and anything else it owes.",
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
        return [f"  {result.path} — left in conflict: {result.reason}"]
    done = "would be resolved" if dry_run else "resolved and written"
    lines = [f"  {result.path} — {done}"]
    for owed in result.owed:
        lines.append(
            f"    {owed.location} now carries the base side's answer: {_answer_line(owed)}"
        )
        lines.append(f"      once the merge is committed, answer `{owed.outcome}` — {owed.why}:")
        lines.append(f"        {owed.command}")
    if dry_run:
        lines.extend("    " + line for line in _diff(result))
    return lines


def _diff(result: FileResult) -> list[str]:
    """A resolved file's change from its conflicted state, one line each."""
    diff = difflib.unified_diff(
        result.before.splitlines(keepends=True),
        result.after.splitlines(keepends=True),
        fromfile=f"a/{result.path}",
        tofile=f"b/{result.path}",
    )
    return [line.rstrip("\r\n") for line in diff]


def render_diffs(resolution: Resolution) -> str:
    """Each resolved file's change from its conflicted state: what staging would take."""
    lines = [line for result in resolution.resolved for line in _diff(result)]
    return "\n".join(lines) + "\n" if lines else ""


def render_staging(written: Sequence[str], staged: Sequence[str]) -> str:
    """What became of the files written: staged, or the `git add` still to run — and how
    to bring a file's conflict back."""
    back = "To bring a file's conflict back: git checkout -m -- <path>"
    if staged:
        return f"Staged {', '.join(staged)} (`git diff --cached` shows it). {back}\n"
    return (
        "Not staged. Check each file — `git diff -- <path>` shows it against both sides — "
        f"then stage it:\n  {command_line('git', 'add', '--', *written)}\n{back}\n"
    )


def _answer_line(owed: Owed) -> str:
    """The base side's answer in one line: `at`, the outcome, and its justification."""
    answer: Any = owed.answer
    block: Mapping[str, Any] = (
        cast("Mapping[str, Any]", answer) if isinstance(answer, Mapping) else {}
    )
    at, outcome, because = block.get("at"), block.get("outcome"), block.get("unchanged-because")
    shown = f"at {at}, {outcome}"
    return f"{shown} — {because}" if isinstance(because, str) else shown


def render_json(resolution: Resolution, *, dry_run: bool, staged: Sequence[str] = ()) -> str:
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
                "staged": result.path in staged,
                "reason": result.reason,
                "owed": [
                    {
                        "artefact": owed.artefact,
                        "location": owed.location,
                        "base_answer": owed.answer,
                        "outcome": owed.outcome,
                        "why": owed.why,
                        "command": owed.command,
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
    "FrictionResolveError",
    "Owed",
    "Resolution",
    "plan_resolve",
    "render_diffs",
    "render_human",
    "render_json",
    "render_staging",
    "stage",
    "write",
]
