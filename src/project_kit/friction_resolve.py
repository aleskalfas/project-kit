"""`pkit friction resolve`: a merge's conflicting answers, resolved as text (COR-050 points 3, 16).

When two lines of work revalidate the same artefact, its `revalidated` block
conflicts on merge, and the person resolving the conflict revalidates the
combined state; nothing merges two revalidations automatically, since that
would claim a revalidation nobody made (point 3). So it is with the
`revisited` entry two lines of work each wrote for one target: whoever
resolves the conflict writes it again (point 16). This command does the
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
- **Only conflicts inside `revalidated` blocks and `revisited` lists.** The
  same merge, with every conflict taken from this branch and again from the
  base side, gives git's merge of everything else; a block or list whose text
  differs between the two is one git conflicted on, and only those are
  decided. Each is replaced, in both, by its decision — and the two must then
  be equal, which holds only when every conflict region lies inside a
  replaced block or list. A conflict anywhere else — the body, another field,
  the anchors, a line beside a block — leaves the file as git left it, and
  says where. A block or list git merged cleanly keeps git's merge, byte for
  byte.
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
- **A `revisited` list merges by target (point 16).** Its entries merge three
  ways by anchor, as deferrals do: an entry only one side changed is that
  side's, so entries both sides wrote for different targets are kept, sorted
  as the writer sorts them. Where both sides wrote the entry of one target
  differently, the base side's is taken, under the rule for an answer both
  sides revalidated: only when `MERGE_HEAD` is the change check's base. An
  entry one side removed and the other changed, a list that is not one
  well-formed entry per target on every side, and a merge that leaves no
  entry, are left to the person.
- **It writes no answer.** Each artefact both sides revalidated now carries
  the base side's answer as written, and owes a revalidation of the combined
  state once the merge is committed. The command names it with the outcome
  its content bears out against the base side's — `updated` when it differs,
  `unchanged` when it does not — as the change check judges it. The check
  requires that revalidation only where an anchor of the artefact changed on
  this branch; elsewhere it is point 3's rule for people, and the command's
  advice. Each target both sides wrote an entry for now carries the base
  side's entry, and owes its entry written again for the combined state: the
  command names the `pkit friction revisit` that writes it. The base side's
  reason is no new reason, so the check asks for that entry where this
  branch changed a trigger field of a link listing the target and left the
  target as it was; elsewhere it is point 16's rule for people, and the
  command's advice.
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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, cast

import click

from project_kit import cli_render
from project_kit.backbone_schemas import CONTAINER_KEY
from project_kit.document_parts import colliding_keys, split_front_matter
from project_kit.friction_check import (
    SHORT,
    FrictionCheckError,
    commit_of,
    content_differs,
    parsed_at,
    printable,
    resolve_base,
    run_git,
)
from project_kit.friction_discovery import (
    FRICTION_KEY,
    REVISITED_KEY,
    Anchor,
    Artefact,
    ArtefactKind,
    DiscoveredFile,
    Discovery,
    discover_artefacts,
    held_message,
    line_break,
    parse_artefacts,
)
from project_kit.friction_report import BECAUSE
from project_kit.friction_write import (
    DEFERRED,
    OUTCOMES,
    REVALIDATED,
    REVISIT_OUTCOMES,
    UNCHANGED,
    FileNotReplaced,
    carrier_keys,
    command_line,
    key_span,
    replace_file,
    written_key,
)
from project_kit.line_breaks import universal_newlines
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

# One answer of an artefact a conflict can lie in: its `revalidated` block, or its
# `revisited` list, by the key that writes it.
_Part = tuple[str, _Key]

# What a person writes in place of a revisit entry's reason (`pkit friction revisit`).
REVISIT_REASON = "<why the target still stands, or the follow-up that revisits it>"

# A block absent from a version, so that it compares unequal to one written empty.
_ABSENT = object()

#: The version of the document `render_json` returns, under the rule every reading
#: document of the `friction` group follows: raised when a key a reader relies on
#: changes its meaning or goes, never for a key added.
RESOLVE_SCHEMA_VERSION = 1


class FileStatus(Enum):
    """What the command did with a file. The values are the `status` field of the JSON output."""

    RESOLVED = "resolved"  # every conflict lay inside `revalidated` blocks or `revisited` lists
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
class OwedRevisit:
    """A target both sides wrote a `revisited` entry for: the source now carries the base
    side's entry, and owes the entry written again for the combined state once the merge is
    committed (COR-050 point 16)."""

    artefact: str  # the source's id
    location: str
    target: Anchor
    entry: Any  # the base side's entry as written: `outcome`, `reason`
    command: str  # the entry written again, with a placeholder where a person's words go


@dataclass(frozen=True)
class FileResult:
    """One file the command looked at. `before` and `after` are a resolved file's text as
    the working tree holds it and as it is written."""

    path: str
    status: FileStatus
    reason: str | None = None
    owed: tuple[Owed, ...] = ()
    owed_revisits: tuple[OwedRevisit, ...] = ()
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

    def base_side_refusal(self, location: str, target: Anchor | None = None) -> str | None:
        """Why the base side's answer cannot be taken for an artefact both sides revalidated
        — or, given `target`, the base side's entry for a target both sides wrote one for —
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
        if target is not None:
            return (
                f"both sides wrote the `revisited` entry of {target.kind}:{target.value} in "
                f"{location}, and {which}: taken, the base side's entry would read in this "
                f"branch's change check as an entry written here, which nobody wrote — resolve "
                f"its `revisited` list by hand and write the entry again for the combined state "
                f"once the merge is committed"
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
class Stamp:
    """One artefact's `revalidated` block, or its `revisited` list, as one version writes
    it: its value as written, its text — the key through the end of its value — at `start`
    in that version, the column its key starts at, and whether it sits in a mapping
    written in flow style."""

    value: Any
    start: int
    written: str
    column: int
    flow: bool

    @property
    def end(self) -> int:
        return self.start + len(self.written)


@dataclass(frozen=True)
class Version:
    """One version of a file, read with `\\n` line breaks: its artefacts, where each
    `revalidated` block is written in it (`stamps`), and where each `revisited` list is
    (`revisits`). `pkit friction since` reads both through it too (`friction_since`)."""

    text: str
    artefacts: Mapping[_Key, Artefact]
    stamps: Mapping[_Key, Stamp]
    revisits: Mapping[_Key, Stamp] = field(default_factory=dict[_Key, Stamp])

    def spans(self, which: str) -> Mapping[_Key, Stamp]:
        """Where each artefact's answer of one kind is written: its `revalidated` block,
        or its `revisited` list, by the key that writes it."""
        return self.revisits if which == REVISITED_KEY else self.stamps


_NO_VERSION = Version("", {}, {})


@dataclass(frozen=True)
class _Decision:
    """A conflicted block or list decided: its value, its text when one side wrote exactly
    that (`None` when it is written anew), whether a revalidation is owed, and, for a
    `revisited` list, each target whose entry is owed written again."""

    value: Any
    text: str | None
    owed: bool
    targets: tuple[Anchor, ...] = ()


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
    versions: dict[int, Version] = {}
    for number, blob in blobs.items():
        try:
            text = universal_newlines(blob.decode("utf-8"))
        except UnicodeDecodeError:
            return _left(rel, "a side is not UTF-8 text")
        version = read_version(rel, found, text)
        if isinstance(version, str):
            if number != _ANCESTOR:
                side = "this branch" if number == _THIS else "the base side"
                return _left(rel, f"on {side}, {version}")
            version = Version(text, {}, {})
        versions[number] = version

    sides = _merge(context, blobs, before)
    if isinstance(sides, str):
        return _left(rel, sides)
    ours, theirs = (read_version(rel, found, side) for side in sides)
    if isinstance(ours, str) or isinstance(theirs, str):
        reason = ours if isinstance(ours, str) else theirs
        return _left(rel, f"with each conflict taken from one side, {reason}")

    conflicted: list[_Part] = [
        (which, key)
        for which in (REVALIDATED, REVISITED_KEY)
        for key in sorted(
            (
                key
                for key in {*ours.spans(which), *theirs.spans(which)}
                if _text(ours, which, key) != _text(theirs, which, key)
            ),
            key=lambda k: (k[0].value, k[1] or ""),
        )
    ]
    ancestor = versions.get(_ANCESTOR, _NO_VERSION)
    this, base = versions[_THIS], versions[_BASE]
    decided: dict[_Part, _Decision | str] = {}
    texts: dict[_Part, str] = {}
    lopsided = False  # a conflicted block or list stands on one side of its conflict only
    for n, part in enumerate(conflicted):
        which, key = part
        location = _location(key, base, this, ancestor, ours, theirs)
        decide = _decide_revisits if which == REVISITED_KEY else _decide
        decision = decide(context, key, location, ancestor, this, base)
        if key not in ours.spans(which) or key not in theirs.spans(which):
            lopsided = True
            if isinstance(decision, _Decision):
                decision = (
                    f"the {_named(which, location)} stands on one side of a conflict only: "
                    f"resolve it by hand"
                )
        decided[part] = decision
        if isinstance(decision, str):
            texts[part] = f"@pkit-friction-resolve-{context.nonce}-{n}@"
        else:
            target = ours.spans(which)[key]
            texts[part] = decision.text or written_key(
                which, decision.value, column=target.column, flow=target.flow
            )

    one, other = _spliced(ours, texts), _spliced(theirs, texts)
    refused = [d for d in decided.values() if isinstance(d, str)]
    where = None if one == other else _where(one, other, front_matter=not lopsided)
    if where is not None:
        notes = [
            decision if isinstance(decision, str) else _advice(part, decision, ours)
            for part, decision in decided.items()
        ]
        return _left(rel, "; ".join([where, *notes]))
    if refused:
        return _left(rel, "; ".join(refused))

    chosen = {p: d.value for p, d in decided.items() if isinstance(d, _Decision)}
    artefacts = _read_back(rel, found, one, chosen)
    if artefacts is None:
        return _left(
            rel,
            "its `revalidated` blocks and `revisited` lists would not read back as decided, "
            "so it cannot be resolved as text",
        )
    owed = tuple(
        _owed(artefacts[key], base.artefacts[key])
        for (which, key), decision in decided.items()
        if which == REVALIDATED and isinstance(decision, _Decision) and decision.owed
    )
    owed_revisits = tuple(
        _owed_revisit(artefacts[key], base, key, target)
        for (which, key), decision in decided.items()
        if which == REVISITED_KEY and isinstance(decision, _Decision)
        for target in decision.targets
    )
    after = one if newline == "\n" else one.replace("\n", newline)
    return FileResult(
        rel,
        FileStatus.RESOLVED,
        owed=owed,
        owed_revisits=owed_revisits,
        before=before,
        after=after,
    )


def read_version(rel: str, found: DiscoveredFile, text: str) -> Version | str:
    """One version's artefacts and where each `revalidated` block and each `revisited`
    list is written in it, or why it cannot be read.

    A block or a list is found by the written text of the keys that lead to it
    (`key_span`), and discovery reads each key rendered as text. Where two keys on that
    path are read alike, as `1` and `"1"` are, discovery reads one entry and the text
    found may be the other's, so the version cannot be read (`colliding_keys`)."""
    artefacts, reason = parse_artefacts(rel, found.places[0], text, rule_set=found.rule_set)
    if reason is not None:
        return f"its front matter does not parse ({reason})"
    front_matter, _body = split_front_matter(text)
    spans: dict[str, dict[_Key, Stamp]] = {REVALIDATED: {}, REVISITED_KEY: {}}
    written: list[tuple[Artefact, str, Any, tuple[str, ...]]] = []
    for artefact in artefacts:
        for which in spans:
            present, value = _written(artefact, which)
            if present:
                keys = (*carrier_keys(artefact), CONTAINER_KEY, FRICTION_KEY, which)
                written.append((artefact, which, value, keys))
    if front_matter is not None and written:
        alike = colliding_keys(front_matter, [keys for *_, keys in written])
        offset = text.find("\n") + 1  # the front matter starts after its opening line
        for artefact, which, value, keys in written:
            if keys in alike:
                return (
                    f"two keys on the path to the {_named(which, artefact.location)} are "
                    f"read as `{alike[keys]}` once rendered, so which one holds it cannot "
                    f"be told"
                )
            span = key_span(front_matter, keys)
            if span is None:
                return (
                    f"the {_named(which, artefact.location)} is not written directly "
                    f"(a YAML alias or merge key)"
                )
            start = offset + span.start
            column = start - (text.rfind("\n", 0, start) + 1)
            text_of = front_matter[span.start : span.end]
            spans[which][_key(artefact)] = Stamp(value, start, text_of, column, span.flow)
    return Version(text, {_key(a): a for a in artefacts}, spans[REVALIDATED], spans[REVISITED_KEY])


def _key(artefact: Artefact) -> _Key:
    return (artefact.kind, None if artefact.kind is ArtefactKind.DOCUMENT else artefact.id)


def _named(which: str, location: str) -> str:
    """An artefact's answer of one kind as a message names it."""
    if which == REVISITED_KEY:
        return f"`{REVISITED_KEY}` list of {location}"
    return f"`{REVALIDATED}` block of {location}"


def _written(artefact: Artefact, which: str = REVALIDATED) -> tuple[bool, Any]:
    """Whether the artefact's friction block writes `which` — `revalidated`, or
    `revisited` — and its value as written."""
    block = artefact.friction
    if not isinstance(block, Mapping):
        return False, None
    mapping = cast("Mapping[str, Any]", block)
    return which in mapping, mapping.get(which)


def _text(version: Version, which: str, key: _Key) -> str | None:
    stamp = version.spans(which).get(key)
    return None if stamp is None else stamp.written


def _location(key: _Key, *versions: Version) -> str:
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
    ancestor: Version,
    this: Version,
    base: Version,
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


def _block(version: Version, key: _Key) -> Mapping[str, Any]:
    stamp = version.stamps.get(key)
    return {} if stamp is None else cast("Mapping[str, Any]", stamp.value)


def _answer(
    context: _Context,
    key: _Key,
    location: str,
    ancestor: Version,
    this: Version,
    base: Version,
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


def _deferrals(key: _Key, location: str, ancestor: Version, this: Version, base: Version) -> Any:
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


def _entries(version: Version, key: _Key) -> dict[Anchor, Any] | None:
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


def _decide_revisits(
    context: _Context,
    key: _Key,
    location: str,
    ancestor: Version,
    this: Version,
    base: Version,
) -> _Decision | str:
    """The `revisited` list a conflicted source gets, or why it is left to the person
    (COR-050 point 16).

    A list only one side changed is that side's. Where both did, the entries merge
    three ways by target, sorted as the writer sorts them: an entry only one side
    changed is that side's. Where both sides wrote one target's entry differently, the
    base side's is taken, under the rule for an answer both sides revalidated
    (`base_side_refusal`), and the entry is owed written again for the combined state.
    """
    a, t, b = (version.revisits.get(key) for version in (ancestor, this, base))
    av, tv, bv = (_ABSENT if s is None else s.value for s in (a, t, b))
    if tv in (bv, av) or bv == av:
        stamp, side = (t, "this branch") if bv == av and tv != bv else (b, "the base side")
        if stamp is None:
            return (
                f"{side} removed the `{REVISITED_KEY}` list of {location} beside a change of "
                f"the other side's: resolve it by hand"
            )
        return _Decision(stamp.value, stamp.written, owed=False)
    if t is None or b is None:
        removed, changed = ("this branch", "the base side")
        if b is None:
            removed, changed = changed, removed
        return (
            f"{removed} removed the `{REVISITED_KEY}` list of {location} and {changed} changed "
            f"it: keep it or remove it by hand"
        )
    sides = [_revisit_entries(version, key) for version in (ancestor, this, base)]
    if any(side is None for side in sides):
        return (
            f"both sides changed the `{REVISITED_KEY}` list of {location}, and a side's list is "
            f"not one well-formed entry per target: resolve it by hand"
        )
    a_side, t_side, b_side = cast("list[dict[Anchor, Any]]", sides)
    merged: list[Any] = []
    owed: list[Anchor] = []
    for target in sorted({*a_side, *t_side, *b_side}, key=lambda x: (x.kind, x.value)):
        ae, te, be = a_side.get(target), t_side.get(target), b_side.get(target)
        if te in (be, ae):
            entry = be
        elif be == ae:
            entry = te
        elif te is None or be is None:
            removed = "this branch" if te is None else "the base side"
            return (
                f"{removed} removed the `{REVISITED_KEY}` entry of {target.kind}:{target.value} "
                f"in {location} and the other side changed it: keep it or remove it by hand"
            )
        else:
            refusal = context.base_side_refusal(location, target)
            if refusal is not None:
                return refusal
            entry = be
            owed.append(target)
        if entry is not None:
            merged.append(entry)
    if not merged:
        return (
            f"both sides removed entries of the `{REVISITED_KEY}` list of {location}, which "
            f"leaves none: resolve it by hand"
        )
    text = t.written if merged == t.value else b.written if merged == b.value else None
    return _Decision(merged, text, owed=bool(owed), targets=tuple(owed))


def _revisit_entries(version: Version, key: _Key) -> dict[Anchor, Any] | None:
    """A version's `revisited` entries of the artefact by target; `None` unless the list
    is a list whose every entry is well-formed and names a target no other entry does."""
    stamp = version.revisits.get(key)
    raw = None if stamp is None else stamp.value
    if raw is None:
        return {}
    artefact = version.artefacts.get(key)
    if not isinstance(raw, list) or artefact is None:
        return None
    entries = cast("list[Any]", raw)
    by_target = {r.anchor: entries[r.index] for r in artefact.revisits}
    return by_target if len(by_target) == len(entries) else None


def _spliced(version: Version, texts: Mapping[_Part, str]) -> str:
    """The version with each block and list `texts` names replaced by its text."""
    text = version.text
    stamps = [
        (version.spans(which)[key], new)
        for (which, key), new in texts.items()
        if key in version.spans(which)
    ]
    for stamp, new in sorted(stamps, key=lambda item: -item[0].start):
        text = text[: stamp.start] + new + text[stamp.end :]
    return text


def _advice(part: _Part, decision: _Decision, ours: Version) -> str:
    """What to take for a decided block or list, in a file left for another conflict."""
    which, key = part
    named = _named(which, ours.artefacts[key].location)
    if which == REVISITED_KEY and decision.owed:
        targets = ", ".join(f"{t.kind}:{t.value}" for t in decision.targets)
        return (
            f"the {named} conflicts too: both sides wrote the entry of {targets} — take the "
            f"base side's entry, keep each side's other entries, and write the entry again "
            f"for the combined state once the merge is committed"
        )
    if decision.owed:
        return (
            f"the {named} conflicts too: both sides revalidated it — take the base side's "
            f"answer, keep both sides' changes to `deferred`, and revalidate the combined "
            f"state once the merge is committed"
        )
    return f"the {named} conflicts too: keep what each side changed in it"


#: Where a decided conflict may lie, as a refusal names what lies outside it.
_ANSWERS = "the `revalidated` blocks and `revisited` lists"


def _where(one: str, other: str, *, front_matter: bool) -> str | None:
    """Where a file still conflicts once its decided blocks and lists are put in: its
    front matter, its body, or — when neither alone does — the file as a whole. Without
    `front_matter` — a block or list left to the person stands on one side only, so the
    front matters differ there anyway — only the body is told, and `None` when it does
    not conflict."""
    (fm_one, body_one), (fm_other, body_other) = split_front_matter(one), split_front_matter(other)
    found: list[str] = []
    if fm_one is not None and fm_other is not None:
        if front_matter and fm_one != fm_other:
            found.append(f"the front matter, outside {_ANSWERS}")
        if body_one != body_other:
            found.append("the body")
    if found:
        return "it conflicts in " + " and in ".join(found)
    return f"it conflicts outside {_ANSWERS}" if front_matter else None


def _read_back(
    rel: str, found: DiscoveredFile, text: str, chosen: Mapping[_Part, Any]
) -> Mapping[_Key, Artefact] | None:
    """The resolution's artefacts — `None` unless it parses and every decided block and
    list reads back as decided."""
    artefacts, reason = parse_artefacts(rel, found.places[0], text, rule_set=found.rule_set)
    if reason is not None:
        return None
    by_key = {_key(a): a for a in artefacts}
    for (which, key), value in chosen.items():
        artefact = by_key.get(key)
        if artefact is None or _written(artefact, which) != (True, value):
            return None
    return by_key


def _owed(resolved: Artefact, base: Artefact) -> Owed:
    """What an artefact both sides revalidated owes, with the outcome its content bears
    out against the base side's, as the change check will compare them (COR-050 point 5)."""
    if content_differs(resolved, base):
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
    block = _written(resolved)[1]
    answer = {k: v for k, v in cast("Mapping[str, Any]", block).items() if k != DEFERRED}
    return Owed(
        artefact=resolved.id,
        location=resolved.location,
        answer=answer,
        outcome=outcome,
        why=why,
        command=command_line("pkit", "friction", "revalidate", resolved.location, *words),
    )


def _owed_revisit(resolved: Artefact, base: Version, key: _Key, target: Anchor) -> OwedRevisit:
    """What a target both sides wrote a `revisited` entry for owes: its entry written again
    for the combined state (COR-050 point 16), the base side's outcome named, since only
    the person can say whether the target still stands."""
    entries = _revisit_entries(base, key) or {}  # well-formed: the decision merged them
    entry = cast("Mapping[str, Any]", entries.get(target, {}))
    words = {k: v for k, v in entry.items() if k != "anchor"}
    outcome = words.get("outcome")
    command = command_line(
        "pkit",
        "friction",
        "revisit",
        resolved.location,
        "--target",
        f"{target.kind}:{target.value}",
        "--outcome",
        outcome if outcome in REVISIT_OUTCOMES else UNCHANGED,
        "--reason",
        REVISIT_REASON,
    )
    return OwedRevisit(
        artefact=resolved.id,
        location=resolved.location,
        target=target,
        entry=words,
        command=command,
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
    if any(result.owed_revisits for result in resolution.resolved):
        lines += [
            "",
            "The person resolving the conflict writes each `revisited` entry both sides wrote",
            "again for the combined state (COR-050 point 16): commit the merge, then run each",
            "`pkit friction revisit` above with the outcome that holds and your words in place",
            "of the placeholder. The base side's reason is no new reason, so the change check",
            "asks for the entry where this branch changed a trigger field of a link listing the",
            "target and left the target as it was; `pkit friction check` names those.",
        ]
    if resolution.left:
        lines += ["", "Resolve the files left by hand and `git add` them before committing."]
    if dry_run and resolution.resolved:
        lines += ["", cli_render.style("strong", "Dry run: nothing written.")]
    return "\n".join(lines) + "\n"


def _file_lines(result: FileResult, dry_run: bool) -> list[str]:
    """What the command says of one file, and, in a dry run, its diff. A path, a reason
    and an artefact's words are the author's, so what it says is printed escaped, as the
    change check's human view prints them (`printable`): they cannot move the cursor or
    hide the command printed beside them."""
    said = [printable(line) for line in _said(result, dry_run)]
    if dry_run and result.status is FileStatus.RESOLVED:
        said.extend("    " + line for line in _diff(result))
    return said


def _said(result: FileResult, dry_run: bool) -> list[str]:
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
    for revisit in result.owed_revisits:
        target = f"{revisit.target.kind}:{revisit.target.value}"
        lines.append(
            f"    {revisit.location} now carries the base side's `{REVISITED_KEY}` entry of "
            f"{target}: {_entry_line(revisit)}"
        )
        lines.append(
            "      once the merge is committed, write it again for the combined state — "
            "`unchanged` if the target still stands, `deferred` with the follow-up that "
            "revisits it:"
        )
        lines.append(f"        {revisit.command}")
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
        return f"Staged {', '.join(staged)} (`git diff --cached` shows what is staged). {back}\n"
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


def _entry_line(owed: OwedRevisit) -> str:
    """The base side's revisit entry in one line: its outcome and its reason."""
    entry: Any = owed.entry
    words: Mapping[str, Any] = (
        cast("Mapping[str, Any]", entry) if isinstance(entry, Mapping) else {}
    )
    outcome, reason = words.get("outcome"), words.get("reason")
    return f"{outcome} — {reason}" if isinstance(reason, str) else str(outcome)


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
                "owed_revisits": [
                    {
                        "artefact": owed.artefact,
                        "location": owed.location,
                        "target": {"kind": owed.target.kind, "value": owed.target.value},
                        "base_entry": owed.entry,
                        "command": owed.command,
                    }
                    for owed in result.owed_revisits
                ],
            }
            for result in resolution.files
        ],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


__all__ = [
    "RESOLVE_SCHEMA_VERSION",
    "REVISIT_REASON",
    "FileResult",
    "FileStatus",
    "FrictionResolveError",
    "Owed",
    "OwedRevisit",
    "Resolution",
    "Stamp",
    "Version",
    "plan_resolve",
    "read_version",
    "render_diffs",
    "render_human",
    "render_json",
    "render_staging",
    "stage",
    "write",
]
