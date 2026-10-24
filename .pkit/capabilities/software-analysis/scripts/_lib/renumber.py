"""Renumbering a new artefact before its change reaches the default branch (DEC-001 point 3).

When two lines of work number a new use case, journey or requirement the same,
the first to reach the default branch keeps the number, and the other
renumbers before merging. `pkit analysis check-numbers` reports the collision
(`_lib/numbers.py`); this gives this branch's artefact another number, with
every reference to it in the repository's analyses:

- **its file** is renamed, the number its name opens with replaced, and its
  `id` and its heading are rewritten with every other mention in it;
- **each mention elsewhere** is rewritten, in every file of the analyses'
  places, every revalidation record and every other file of the analysis
  location: another artefact's front matter — `after`, `steps`, `relies-on`,
  `requirements`, `refines` — and its anchors and deferrals, prose, a link to
  the file and to its heading, a record's outcomes, gaps and evidence, and a
  mention written with another analysis's qualifier, such as `core:UC-021`.
  A mention is the id whole, in any spelling of its number (`UC-21`, `UC-021`),
  and no letter, digit or underscore runs into it; a heading's anchor is its
  id in lower case after `#`. Ids are unique across a repository's analyses,
  so a mention names one artefact wherever it stands (point 3);
- **each overview** that names it is written anew once the files are, as
  `pkit analysis overview` writes it (DEC-003 point 8): an overview carries a
  fingerprint of what it draws, so it is drawn, never rewritten as text.

What it refuses, writing nothing:

- **an artefact the default branch holds.** Once settled, an id names one
  artefact for good (point 3). So the artefact renumbered is one this branch
  numbered: a file of the working tree holding the id at a path where this
  branch left the default branch held none. An id the default branch held there
  at a path this branch no longer holds it at is its artefact, moved, and
  refused; so is one whose file the default branch holds in a version this
  branch's history wrote since — its own work, landed by a squash merge, which
  merging the default branch in settles. One the default branch holds in a file
  of the same name and other bytes may be the same, edited since: that is said,
  and only the person knows;
- **a number already given, or not past the default branch's.** A new number
  is given past what the default branch holds, and past the base `--base`
  names, as the stamp gives one (`_lib/stamp.py`): past every number their
  tips hold and their history ever gave a file of its place, the project's
  numbering setting read as the stamp reads it (`_lib/numbering.py`). No file
  of the working tree holds it either. Without `--to`, it is the next free
  number, one past those and the working tree's;
- **a mention it cannot tell apart.** A file that mentioned the id already
  where this branch left the default branch holds the default branch's own
  artefact's mentions, merged in since. It is left as it is where this branch
  has not changed it, and refused where it has, since the two artefacts'
  mentions then mix in one file.

What is settled, and where this branch left it, the backbone names (`pkit
repository base --json`, COR-054 point 5): the default branch, and the base
`--base` names. `$PKIT_CHECK_BASE`, a pipeline's base for its checks, never
moves where a number is given from (point 3). The analysis is read through
the backbone's discovery (`pkit friction artefacts`), at the working tree and
at those commits, never by walking its folders.

It writes each file whole, to a temporary file beside it then moved over it,
the renamed one before its old file is removed. A failure partway leaves what
was written, and says which (COR-004: failure is forward-only).
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from _lib import analyses, backbone, diagrams, history, numbering, overview, stamp, structure
from _lib.model import (
    JOURNEY,
    NUMBERED,
    PREFIX,
    QUALITY,
    USE_CASE,
    Analysis,
    Unreadable,
    id_in_name,
    identity,
    noun_numbered,
    number_in,
    number_of,
)

#: The kind whose numbering a prefix names: a requirement's number is one across its
#: three kinds (DEC-002 point 2), so any of the three stands for them.
KIND_OF_PREFIX = {PREFIX[USE_CASE]: USE_CASE, PREFIX[JOURNEY]: JOURNEY, PREFIX[QUALITY]: QUALITY}

#: The command, as a refusal names it.
COMMAND = "pkit analysis renumber"


class Refused(Exception):
    """The renumbering cannot be made; the message says why and what to do."""


class Failed(Exception):
    """A write failed partway; the message says what was written before it."""


@dataclass(frozen=True)
class Settled:
    """One branch a number is given past: its reference, its tip, and where this branch
    left it (`fork`)."""

    ref: str
    tip: str
    fork: str


@dataclass(frozen=True)
class Change:
    """One file the renumbering rewrites: its path, the path it is renamed to — `None`
    where it keeps its name — how many mentions of the id it rewrites, and its text."""

    path: str
    renamed: str | None
    mentions: int
    text: str


@dataclass(frozen=True)
class Plan:
    """What renumbering `old` as `new` writes: each file it changes, the folder of each
    analysis whose overview is drawn anew, and what it has to say."""

    old: str
    new: str
    changes: tuple[Change, ...]
    overviews: tuple[str | None, ...]
    overview_paths: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def lines(self) -> list[str]:
        """The plan, one line for each file it changes."""
        out = [f"renumber {self.old} as {self.new} (DEC-001 point 3):"]
        for change in self.changes:
            said = f"{change.mentions} mention{'' if change.mentions == 1 else 's'}"
            if change.renamed is not None:
                out.append(f"  rename    {change.path} → {change.renamed}, {said}")
            else:
                out.append(f"  rewrite   {change.path}, {said}")
        out += [f"  overview  {path}, drawn anew" for path in self.overview_paths]
        return out


@dataclass
class Written:
    """What applying a plan wrote: each file, and each warning about an overview."""

    paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def plan(root: Path, old_id: str, to: str | None = None, base: str | None = None) -> Plan:
    """What renumbering `old_id` in the working tree at `root` writes: as `to`, or as the
    next free number, given past the default branch and, when one is named, the base
    `base`. Raises Refused when it cannot be made."""
    old = number_in(old_id)
    if old is None:
        raise Refused(
            f"{old_id!r} is no use case's, journey's or requirement's id: only a numbered "
            f"artefact is renumbered (DEC-001 point 3)"
        )
    prefix = old.split("-", 1)[0]
    if to is not None:
        _check_spelling(to, prefix, old)
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        raise Refused(f"the analysis could not be read: {exc}") from exc
    here = analysis.numbers().get(old)
    if not here:
        raise Refused(
            f"no {noun_numbered(old)} of the working tree holds {old}, by its front matter or "
            f"by its file's name"
        )

    branch, branches = _settled(root, base)
    reading = _Readings(root)
    path = _ours(old, here, branches, reading)
    notes: list[str] = []
    notes += _landed(root, analysis, old, path, branches, reading)
    top = _settled_top(root, analysis, prefix, branch, branches, reading, notes)
    new = _new(analysis, prefix, old, to, top, branches)

    renamed = _renamed(root, path, old, new)
    changes = _changes(root, analysis, old, new, path, renamed, branches)
    listing = analyses.read(root)
    kept = listing.kept() if listing.keeps_overview else []
    overviews = [
        folder for folder in kept if _mentions(root, overview.path_of(analysis, folder), old)
    ]
    return Plan(
        old=old,
        new=new,
        changes=tuple(changes),
        overviews=tuple(overviews),
        overview_paths=tuple(overview.path_of(analysis, folder) for folder in overviews),
        notes=tuple(notes),
    )


def apply(root: Path, planned: Plan) -> Written:
    """Write `planned`: each file whole, the renamed one before its old file is removed,
    then each overview that names the id drawn anew. Raises Failed, naming what was
    written, when a write fails partway. An overview that cannot be drawn is a warning
    naming `pkit analysis overview`, as the stamp's is."""
    written = Written()
    for change in planned.changes:
        target = change.renamed or change.path
        try:
            stamp.write_whole(root / target, change.text.encode("utf-8"))
            written.paths.append(target)
            if change.renamed is not None:
                (root / change.path).unlink()
        except OSError as exc:
            done = ", ".join(written.paths) or "nothing"
            raise Failed(
                f"{target} could not be written: {exc}; written before it: {done}. Run "
                f"`pkit analysis validate` and finish by hand"
            ) from exc
    if not planned.overviews:
        return written
    try:
        listing = analyses.read(root)
        analysis = backbone.read_analysis(root)
        shown_as = overview.shown_as()
    except (Unreadable, structure.Unreadable) as exc:
        written.warnings.append(_not_drawn(exc))
        return written
    for folder in planned.overviews:
        try:
            drawn = overview.write(root, analysis, listing, folder, shown_as)
        except (diagrams.NoAnswer, stamp.Refused) as exc:
            written.warnings.append(_not_drawn(exc))
            continue
        if drawn.changed:
            written.paths.append(drawn.path)
    return written


def _not_drawn(exc: Exception) -> str:
    return (
        f"an overview was not drawn anew: {exc}. Once that is mended, run `{overview.COMMAND}` "
        f"(DEC-003 point 8)"
    )


# --- what is settled -------------------------------------------------------------------------


def _check_spelling(to: str, prefix: str, old: str) -> None:
    """Refuse a `--to` that is no number of `old`'s kind, in its one spelling."""
    spelt = number_in(to)
    if spelt is None or spelt.split("-", 1)[0] != prefix:
        raise Refused(
            f"--to {to!r} is no {noun_numbered(old)}'s id: {old} is renumbered as "
            f"{prefix}-NNN, since a number never changes its kind's numbering (DEC-001 point 3)"
        )
    if spelt != to:
        raise Refused(
            f"--to {to!r} spells {spelt} with other zeros: a number has one spelling, three "
            f"digits below 1000 — write {spelt}"
        )
    if spelt == old:
        raise Refused(f"{old} is its number already; name another with --to")


def _settled(root: Path, base: str | None) -> tuple[backbone.Branch, list[Settled]]:
    """The default branch, and each branch a number is given past: the default branch,
    and the base `base` names when one is — each with its tip and where this branch left
    it, as the backbone resolves them (COR-054 point 5). Never `$PKIT_CHECK_BASE`, which
    only a comparison reads (point 3). Refused, with the backbone's reason and fix, where
    one resolves nowhere or shares no history with HEAD."""
    try:
        reading = backbone.settled(root, base)
    except Unreadable as exc:
        raise Refused(f"what the default branch holds could not be read: {exc}") from exc
    branch = reading.default_branch
    if branch.ref is None or branch.commit is None:
        raise Refused(branch.problem or f"the default branch {branch.name!r} resolves nowhere")
    own = reading.base
    if base is not None or own.ref != branch.ref:
        try:
            own = backbone.settled(root, branch.ref).base
        except Unreadable as exc:
            raise Refused(f"what the default branch holds could not be read: {exc}") from exc
    branches = [_branch(own)]
    if base is not None and reading.base.tip != branch.commit:
        branches.append(_branch(reading.base))
    return branch, branches


def _branch(named: backbone.Base) -> Settled:
    if named.problem is not None or named.tip is None or named.fork is None:
        raise Refused(named.problem or f"the base {named.ref!r} cannot be compared")
    return Settled(ref=named.ref, tip=named.tip, fork=named.fork)


class _Readings:
    """The analysis at a commit, read once for each."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._at: dict[str, Analysis] = {}

    def at(self, commit: str, ref: str) -> Analysis:
        if commit not in self._at:
            try:
                self._at[commit] = backbone.read_analysis(self._root, at=commit)
            except Unreadable as exc:
                raise Refused(f"{ref} could not be read: {exc}") from exc
        return self._at[commit]


def _ours(old: str, here: set[str], branches: list[Settled], reading: _Readings) -> str:
    """The file of this branch's artefact numbered `old`: the one file of the working tree
    holding it at a path where no branch held it where this branch left it. Refused where
    that artefact is the default branch's, or where two files of this branch's hold it."""
    for settled in branches:
        held = reading.at(settled.fork, settled.ref).numbers().get(old, set())
        if held and not held & here:
            raise Refused(
                f"{old} is {settled.ref}'s: it held {old} at {_listed(held)} when this branch "
                f"left it, and this branch holds it at {_listed(here)}. Once settled, a number "
                f"names one artefact for good, so it is never renumbered (DEC-001 point 3)"
            )
        here = here - held
        if not here:
            raise Refused(
                f"{old} is {settled.ref}'s, at {_listed(held)}: once settled, a number names "
                f"one artefact for good, so it is never renumbered (DEC-001 point 3)"
            )
    if len(here) > 1:
        raise Refused(
            f"{old} is held by {len(here)} files of this branch's, {_listed(here)}: keep one, "
            f"or renumber all but one by hand, then run this again for the one you keep"
        )
    return next(iter(here))


def _landed(
    root: Path,
    analysis: Analysis,
    old: str,
    path: str,
    branches: list[Settled],
    reading: _Readings,
) -> list[str]:
    """Refuse where a branch holds this branch's own artefact numbered `old`, landed: its
    tip holds the id, where this branch left it held none, in a file whose bytes are a
    version this branch's history wrote — a parent branch squash-merged, say. A file of
    the name this branch gives it, in other bytes, may be that work edited since, and only
    the person knows: a note says so."""
    notes: list[str] = []
    for settled in branches:
        on_tip = reading.at(settled.tip, settled.ref)
        at_fork = reading.at(settled.fork, settled.ref)
        theirs = on_tip.numbers().get(old, set()) - at_fork.numbers().get(old, set())
        if not theirs:
            continue
        folders = analysis.place_folders(NUMBERED) | on_tip.place_folders(NUMBERED)
        written = backbone.blobs_written(root, settled.fork, folders)
        for their in sorted(theirs):
            if backbone.blob_of(root, settled.tip, their) in written:
                raise Refused(
                    f"{settled.ref} holds {old} at {their} in a version this branch wrote: "
                    f"it is this branch's own work, landed, so the number is settled — merge "
                    f"{settled.ref} and keep one file (DEC-001 point 3)"
                )
            if posixpath.basename(their) == posixpath.basename(path):
                notes.append(
                    f"{settled.ref} holds {old} at {their}, the name this branch gives it, in "
                    f"other bytes: if that is this branch's own work, landed and edited since, "
                    f"do not renumber it — merge {settled.ref} and keep one file"
                )
    return notes


def _settled_top(
    root: Path,
    analysis: Analysis,
    prefix: str,
    branch: backbone.Branch,
    branches: list[Settled],
    reading: _Readings,
    notes: list[str],
) -> int:
    """The highest number of `prefix` the branches hold at their tips, or their history
    ever gave a file of its place that counts, as the stamp counts it (`_lib/history.py`):
    the project's numbering setting frees what it names, and refuses where it cannot be
    honoured (`_lib/numbering.py`)."""
    kind = KIND_OF_PREFIX[prefix]
    tips = [reading.at(settled.tip, settled.ref) for settled in branches]
    top = max(
        (number_of(i) for tip in tips for i in tip.held() if _of_prefix(i, prefix)),
        default=0,
    )
    setting = numbering.resolve(root, numbering.read(root), branch)
    freeing = numbering.freeing(root, setting, branch.commit, analysis.place_folders(NUMBERED))
    problems = (*setting.problems, *freeing.problems)
    if problems:
        raise Refused(f"{numbering.NAME}, {problems[0].location}: {problems[0].message}")
    notes += [f"{numbering.NAME}, {said.location}: {said.message}" for said in freeing.reports]
    named = " and ".join(settled.ref for settled in branches)
    if backbone.is_shallow(root):
        notes.append(
            f"history: shallow clone — {named}'s history was read back to where the clone "
            f"stops, so a number a file was given before it is not counted; fetch the full "
            f"history (`git fetch --unshallow`) to count every one"
        )
    sharing = [k for k in NUMBERED if PREFIX[k] == prefix]
    readings = [analysis, *tips]
    folders = {folder for state in readings for folder in state.place_folders(sharing)}
    judge = history.Judge(root, readings, freeing.files)
    given = [n for settled in branches for n in history.given(root, settled.tip, folders)]
    past = history.highest(judge, given, kind, above=top)
    return top if past is None else number_of(past.id)


def _new(
    analysis: Analysis,
    prefix: str,
    old: str,
    to: str | None,
    top: int,
    branches: list[Settled],
) -> str:
    """The new id: `to`, where it is past `top` and no file of the working tree holds it,
    else refused, naming the next free number; without `to`, that next free number."""
    held = analysis.held()
    mine = max((number_of(i) for i in held if _of_prefix(i, prefix)), default=0)
    following = identity(f"{prefix}-{max(top, mine) + 1}")
    if to is None:
        return following
    named = " and ".join(settled.ref for settled in branches)
    if to in held:
        raise Refused(
            f"{to} is held in the working tree already: an id names one artefact — "
            f"{following} is the next free number"
        )
    if number_of(to) <= top:
        raise Refused(
            f"{to} is not past what {named} holds or its history gave, {prefix}-{top:03d} the "
            f"highest: a new number is given past it, and never used again (DEC-001 point 3) "
            f"— {following} is the next free number"
        )
    return to


def _of_prefix(artefact_id: str, prefix: str) -> bool:
    return number_in(artefact_id) == artefact_id and artefact_id.startswith(f"{prefix}-")


# --- what it writes --------------------------------------------------------------------------


def _renamed(root: Path, path: str, old: str, new: str) -> str | None:
    """The path the file at `path` takes: its name's number replaced, where its name opens
    with `old`'s number; `None` where it does not. Refused where a file lies there already,
    or where it is reached through a link (`stamp.refuse_links`)."""
    name = posixpath.basename(path)
    if id_in_name(name) != old:
        return None
    target = posixpath.join(posixpath.dirname(path), _NAME_NUMBER.sub(new, name, count=1))
    if (root / target).exists():
        raise Refused(f"{target} exists already: move it, or name another number with --to")
    try:
        stamp.refuse_links(root, root / target, target)
    except stamp.Refused as exc:
        raise Refused(str(exc)) from exc
    return target


#: The number a file's name opens with, as the stamp names one (`id_in_name`).
_NAME_NUMBER = re.compile(r"^[A-Z]+-[0-9]+")


def _changes(
    root: Path,
    analysis: Analysis,
    old: str,
    new: str,
    path: str,
    renamed: str | None,
    branches: list[Settled],
) -> list[Change]:
    """Each file of the analysis location that mentions `old`, with its mentions written
    as `new`: the artefact's own file, renamed, first. A file that mentioned `old` where
    this branch left a branch is that branch's, kept as it is where this branch has not
    changed it, and refused where it has."""
    rewrite = _rewriter(old, new)
    forks = list(dict.fromkeys(settled.fork for settled in branches))
    changes: list[Change] = []
    mixed: list[str] = []
    for rel in _files(analysis):
        text = _text(root, rel)
        if text is None:
            continue
        changed, mentions = rewrite(text)
        if not mentions:
            continue
        before = [t for fork in forks if (t := _text_at(root, fork, rel)) is not None]
        if any(rewrite(t)[1] for t in before):
            if all(t == text for t in before if rewrite(t)[1]):
                continue  # the default branch's own mentions, merged in, untouched since
            mixed.append(rel)
            continue
        change = Change(rel, renamed if rel == path else None, mentions, changed)
        changes.append(change)
    if mixed:
        raise Refused(
            f"{_listed(mixed)} mentioned {old} where this branch left the default branch, "
            f"for its own artefact, and this branch changed them too: the two artefacts' "
            f"mentions cannot be told apart, so rewrite this branch's by hand"
        )
    if not any(change.path == path for change in changes):
        text = _text(root, path)
        if text is None:
            raise Refused(f"{path} cannot be read as text, so it cannot be renamed here")
        changes.append(Change(path, renamed, 0, text))
    return sorted(changes, key=lambda change: (change.path != path, change.path))


def _files(analysis: Analysis) -> list[str]:
    """Every file of the analysis location the backbone's reading lists, but the
    overviews: each file of a place, each revalidation record, and each other file of
    the location — none `friction.exclude` leaves out."""
    return sorted({*analysis.files, *analysis.records, *(analysis.unplaced or ())})


def _rewriter(old: str, new: str) -> Callable[[str], tuple[str, int]]:
    """A text with each mention of `old` written as `new`, and how many there were: the
    id whole, in any spelling of its number, with no letter, digit or underscore running
    into it, and a heading's anchor, the id in lower case after `#`."""
    prefix, number = old.split("-", 1)
    spelt = rf"{prefix}-0*{int(number)}(?![0-9])"
    mention = re.compile(rf"(?<![A-Za-z0-9_]){spelt}")
    anchor = re.compile(rf"(?<=#){spelt.lower()}")

    def rewrite(text: str) -> tuple[str, int]:
        text, mentions = mention.subn(new, text)
        text, anchors = anchor.subn(new.lower(), text)
        return text, mentions + anchors

    return rewrite


def _mentions(root: Path, rel: str, old: str) -> bool:
    text = _text(root, rel)
    return text is not None and _rewriter(old, old)(text)[1] > 0


def _text(root: Path, rel: str) -> str | None:
    """The file's text, its line endings kept; `None` where it is no UTF-8 text."""
    try:
        return (root / rel).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _text_at(root: Path, commit: str, rel: str) -> str | None:
    """The file's text at `commit`; `None` where the commit holds no such file."""
    try:
        return backbone.text_at(root, commit, rel)
    except backbone.GitFailed:
        return None


def _listed(paths: Iterable[str]) -> str:
    return ", ".join(sorted(paths))
