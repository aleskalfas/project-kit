"""The answer reader: where an artefact's answers are, and the point each value keeps
(COR-062; ADR-068; ADR-057 point 2).

A change writes its answers to friction in answer files of its own, in one folder
the backbone fixes (COR-062 points 1 and 2). This module is the one home of
everything about them:

- **The folder** (`FOLDER`, `is_answer_file`, `in_folder`). It alone holds the
  path, `.pkit/project/friction/answers/`, the same in every project (ADR-068
  point 1). An answer file is a YAML file directly in it. Discovery reads no file
  in the folder as an artefact, a path anchor and an anchor of a registered kind
  stand on no answer file, and the measures and the declared surface leave them
  out: each asks here (COR-062 point 2).
- **One file** (`read_answer_file`): one mapping with an `answers` list, each
  entry one artefact's answers — its location (`artefact`), the other answer
  files it read (`read`), a revalidation and its deferrals (`revalidated`), and
  revisit entries (`revisited`), with the keys COR-050 names (ADR-068 point 2).
  Read forgivingly: what the reading cannot use is left out, and the schema
  (`friction-answers`, bound by its location, ADR-056 point 2) says why, through
  validation.
- **A state's files** (`working_tree_files`, `commit_files`): the answer files of
  the working tree's one listing, or of a commit's tree.
- **Names history agrees with** (`HistoryNames`, `WorkingNames`; COR-062 point 5).
  A name in `read` is honoured only where the named file was added in a commit
  that first carried the name, or in an ancestor of one; one first carried on two
  lines of work needs this of one of them. An uncommitted entry honours a name of
  a file HEAD holds. Any other name is void, and what it named stays live.
- **Which answers are live** (`liveness`; COR-062 points 4, 5 and 7). Two answers
  that each name the other's file have read neither; a name of a file the state
  does not hold names nothing. Replacing an answer takes naming its file by an
  honoured name: a revalidation replaces the revalidations it read and each
  deferral it read that it does not re-state; a deferral only the deferral of its
  own anchor it read; a revisit entry only the entry for its own target it read.
  An answer stays replaced while one that read it is present, live or not. An
  answer on what is gone — an anchor the artefact no longer declares, a target no
  link takes — answers nothing and is not live; nor is an entry whose location,
  followed through the renames of its file, holds no artefact. A revalidation
  reaches a deferral only where it keeps it in its own entry or read its file
  (`Liveness.kept`). Two live revalidations of one artefact were made apart
  (`Liveness.apart`).
- **The reading of a state** (`StateAnswers.answers`). Until every answer has
  moved out of the blocks, an artefact whose block holds an answer is read wholly
  from its block, as before; one whose block holds none is read wholly from the
  answer files. A whole artefact is read from one home, never kinds mixed across
  homes. This is the one transitional rule: the move removes it.
- **Points across homes** (`AnswerHistory`; COR-062 point 6). A value's point is
  the commit where the artefact's answers — its block in history, and every answer
  file naming it — first carried it; a version carrying it in one home where a
  parent carried it in the other is no write. A deferral that replaces one it read
  keeps that one's point; one put back, or moved out of a block, keeps its point
  by anchor and reason. The walk back stops where the artefact was last added,
  never where an answer file was added. `friction_history` supplies the walk.
- **The first commit holding two answers made apart** (`AnswerHistory.
  first_holding`), where their debt originates (COR-050 point 9, COR-062 point 7).
- **What a prune would remove** (`StateAnswers.prunable`): each answer file in
  which no answer is live (COR-062 point 8; ADR-068 point 4).

Where no answer file exists, every artefact reads as it read before, and nothing
here reads history (`AnswerHistory.dormant`).
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit.backbone_schemas import (
    ANSWER_FILE_SCHEMA_KIND,
    BackboneSchemaInvalid,
    BackboneSchemaMissing,
    as_written,
    load_backbone_schema,
    schema_findings,
)
from project_kit.friction_discovery import (
    REVISITED_KEY,
    Anchor,
    Artefact,
    ArtefactKind,
    Discovery,
    entry_reason,
    link_targets,
    parse_at,
    parsed_at,
)
from project_kit.friction_git import (
    LINK_MODE,
    BlobReader,
    CommitTree,
    FrictionCheckError,
    TreeEntry,
    TreeReader,
    parse_name_status,
    run_git,
)
from project_kit.friction_history import (
    BLOCK,
    Carried,
    Deferred,
    History,
    Points,
    Walker,
    carrier,
)
from project_kit.working_tree import working_tree

#: The answer folder, relative to the repository root: the same in every project, moved
#: by no setting (COR-062 point 2; ADR-068 point 1). No other module holds it.
FOLDER = ".pkit/project/friction/answers"

#: An answer file's suffix: a YAML file directly in the folder (ADR-056 point 2).
SUFFIX = ".yaml"

#: The kind of the answer files' backbone file schema (`backbone_schemas`).
SCHEMA_KIND = ANSWER_FILE_SCHEMA_KIND

ANSWERS_KEY = "answers"
ARTEFACT_KEY = "artefact"
READ_KEY = "read"
REVALIDATED_KEY = "revalidated"
DEFERRED_KEY = "deferred"

#: Where an artefact's answers were read from at a state (`Answers.home`).
BLOCK_HOME = "block"
FILES_HOME = "files"

_yaml: Any = YAML(typ="safe")


# --- the folder ---------------------------------------------------------------------


def is_answer_file(rel: str) -> bool:
    """Whether the repository-relative `rel` is an answer file: a YAML file directly in the
    answer folder (COR-062 point 1)."""
    path = PurePosixPath(rel)
    return path.parent.as_posix() == FOLDER and path.suffix == SUFFIX


def in_folder(rel: str) -> bool:
    """Whether `rel` lies in the answer folder, at any depth: never a place's file
    (COR-062 point 2)."""
    return rel.startswith(f"{FOLDER}/")


def path_of(name: str) -> str:
    """The repository-relative path of the answer file named `name` in the folder."""
    return f"{FOLDER}/{name}"


def name_of(rel: str) -> str:
    """The name in the folder of the answer file at `rel`."""
    return PurePosixPath(rel).name


def location_of(artefact: Artefact, name: str | None = None) -> str:
    """How an answer names `artefact` (COR-062 point 1): its file's path — `name`, where
    given, for an earlier name of the file — and, for a collection entry, `#` and its id."""
    path = artefact.path if name is None else name
    return path if artefact.kind is ArtefactKind.DOCUMENT else f"{path}#{artefact.id}"


# --- one file -----------------------------------------------------------------------


@dataclass(frozen=True)
class Revalidation:
    """A revalidation in an answer file (COR-050 point 3): `at` parsed (`parse_at`), and
    as written; the outcome, and `unchanged-because` whitespace folded."""

    at: Any
    written: Any
    outcome: str | None
    because: str | None


@dataclass(frozen=True)
class Deferment:
    """A deferral in an answer file (COR-050 point 4): its anchor and its reason,
    whitespace folded (`None` where it gives no text)."""

    anchor: Anchor
    reason: str | None
    index: int = 0  # its position in `deferred` as written


@dataclass(frozen=True)
class RevisitAnswer:
    """A revisit entry in an answer file (COR-050 point 16)."""

    anchor: Anchor
    outcome: str | None
    reason: str | None
    index: int = 0  # its position in `revisited` as written


@dataclass(frozen=True)
class Entry:
    """One artefact's answers in one answer file: an entry of its `answers` list.

    `file` is the file's name in the folder, `index` the entry's position;
    `location` the artefact as the answer named it; `read` the other answer files
    it names, in written order.
    """

    file: str
    index: int
    location: str
    read: tuple[str, ...]
    revalidation: Revalidation | None
    deferrals: tuple[Deferment, ...]
    revisits: tuple[RevisitAnswer, ...]

    @property
    def deferred_anchors(self) -> frozenset[Anchor]:
        return frozenset(d.anchor for d in self.deferrals)

    @property
    def revisited_anchors(self) -> frozenset[Anchor]:
        return frozenset(r.anchor for r in self.revisits)


@dataclass(frozen=True)
class AnswerFile:
    """One answer file as read: its name, the document as written (`None` where it does
    not read), its entries, and why it cannot be read, when it cannot."""

    name: str
    document: Any
    entries: tuple[Entry, ...]
    problem: str | None = None


def read_answer_file(name: str, raw: bytes | None) -> AnswerFile:
    """The answer file `name` from its bytes, read forgivingly: an entry without a text
    location is left out, as is a deferral or revisit entry whose anchor is not written
    as texts. Whether the file holds the schema's shape is validation's to say."""
    if raw is None:
        return AnswerFile(name, None, (), "cannot be read")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return AnswerFile(name, None, (), "is not UTF-8 text")
    try:
        loaded = _yaml.load(text)
    except YAMLError as exc:
        reason = " ".join(str(getattr(exc, "problem", None) or exc).split())
        return AnswerFile(name, None, (), f"does not parse as YAML ({reason})")
    document = as_written(loaded)
    if not isinstance(document, Mapping):
        return AnswerFile(name, document, (), "is no mapping")
    listed = cast(Mapping[str, Any], document).get(ANSWERS_KEY)
    if not isinstance(listed, list):
        return AnswerFile(name, document, (), f"holds no `{ANSWERS_KEY}` list")
    entries: list[Entry] = []
    for index, item in enumerate(cast(list[Any], listed)):
        entry = _entry(name, index, item)
        if entry is not None:
            entries.append(entry)
    return AnswerFile(name, document, tuple(entries))


def _entry(name: str, index: int, item: Any) -> Entry | None:
    if not isinstance(item, Mapping):
        return None
    fields = cast(Mapping[str, Any], item)
    location = fields.get(ARTEFACT_KEY)
    if not isinstance(location, str) or not location.strip():
        return None
    read_value = fields.get(READ_KEY)
    read = (
        tuple(dict.fromkeys(r for r in cast(list[Any], read_value) if isinstance(r, str)))
        if isinstance(read_value, list)
        else ()
    )
    revalidated = fields.get(REVALIDATED_KEY)
    revalidation: Revalidation | None = None
    deferrals: list[Deferment] = []
    if isinstance(revalidated, Mapping):
        block = cast(Mapping[str, Any], revalidated)
        if "at" in block:
            outcome = block.get("outcome")
            because = block.get("unchanged-because")
            revalidation = Revalidation(
                at=parse_at(block.get("at")),
                written=block.get("at"),
                outcome=outcome if isinstance(outcome, str) else None,
                because=_folded(because),
            )
        written = block.get(DEFERRED_KEY)
        listed_deferrals = cast(list[Any], written) if isinstance(written, list) else []
        for position, deferral in enumerate(listed_deferrals):
            anchor = _anchor(deferral)
            if anchor is not None:
                reason = cast(Mapping[str, Any], deferral).get("reason")
                deferrals.append(Deferment(anchor, _folded(reason), position))
    revisits: list[RevisitAnswer] = []
    written_revisits = fields.get(REVISITED_KEY)
    listed_revisits = (
        cast(list[Any], written_revisits) if isinstance(written_revisits, list) else []
    )
    for position, revisit in enumerate(listed_revisits):
        anchor = _anchor(revisit)
        if anchor is not None:
            entry = cast(Mapping[str, Any], revisit)
            outcome = entry.get("outcome")
            revisits.append(
                RevisitAnswer(
                    anchor,
                    outcome if isinstance(outcome, str) else None,
                    _folded(entry.get("reason")),
                    position,
                )
            )
    return Entry(
        name, index, location.strip(), read, revalidation, tuple(deferrals), tuple(revisits)
    )


def _anchor(item: Any) -> Anchor | None:
    if not isinstance(item, Mapping):
        return None
    anchor = cast(Mapping[str, Any], item).get("anchor")
    if not isinstance(anchor, Mapping):
        return None
    named = cast(Mapping[str, Any], anchor)
    kind, value = named.get("kind"), named.get("value")
    if isinstance(kind, str) and isinstance(value, str):
        return Anchor(kind, value)
    return None


def _folded(value: Any) -> str | None:
    return " ".join(value.split()) if isinstance(value, str) else None


def load_schema(target_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    """The tree's answer-file schema, or why it cannot be read: the tree's copy, never the
    binary's (ADR-056 point 1)."""
    try:
        return load_backbone_schema(target_root, SCHEMA_KIND), None
    except BackboneSchemaMissing as exc:
        return None, f"no answer-file schema at {exc}; the shape check is skipped (run `pkit sync`)"
    except BackboneSchemaInvalid as exc:
        return None, f"{exc}; the shape check is skipped (`pkit schemas validate` reports it)"


def shape_findings(answer_file: AnswerFile, schema: Mapping[str, Any]) -> list[tuple[str, str]]:
    """`(JSON Pointer, message)` per way the file departs from the answer files' schema
    (`backbone_schemas.schema_findings`); one finding, at the file, where it does not read."""
    if answer_file.document is None:
        return [("", answer_file.problem or "cannot be read")]
    return schema_findings(answer_file.document, schema)


# --- a state's files ----------------------------------------------------------------


def working_tree_files(target_root: Path) -> dict[str, AnswerFile]:
    """The answer files of the working tree's one listing (`working_tree`), by name."""
    found: dict[str, AnswerFile] = {}
    for rel in working_tree(target_root).files():
        if not is_answer_file(rel):
            continue
        path = target_root / rel
        if path.is_symlink():
            found[name_of(rel)] = AnswerFile(name_of(rel), None, (), "is a link")
            continue
        try:
            raw: bytes | None = path.read_bytes()
        except OSError:
            raw = None
        found[name_of(rel)] = read_answer_file(name_of(rel), raw)
    return found


def commit_files(tree: CommitTree) -> dict[str, AnswerFile]:
    """The answer files a commit's tree holds, by name, read from git objects."""
    rels = [rel for rel in tree.files() if is_answer_file(rel)]
    if not rels:
        return {}
    read = tree.read_bytes(rels)
    found: dict[str, AnswerFile] = {}
    for rel in rels:
        entry = tree.entry(rel)
        if entry is not None and entry[0] == LINK_MODE:
            found[name_of(rel)] = AnswerFile(name_of(rel), None, (), "is a link")
        else:
            found[name_of(rel)] = read_answer_file(name_of(rel), read.get(rel))
    return found


# --- names history agrees with ------------------------------------------------------


class HistoryNames:
    """Whether a name in `read` is one history agrees with (COR-062 point 5), from a
    history read from the state's commit: the named file was added in a commit that
    first carried the name, or in an ancestor of one."""

    def __init__(self, history: History, blobs: BlobReader) -> None:
        self.history = history
        self._blobs = blobs
        self._reads: dict[str, frozenset[str]] = {}
        self._adds: dict[str, tuple[int, ...]] = {}
        self._carried: dict[tuple[str, str], tuple[int, ...]] = {}

    def honoured(self, reader: str, named: str) -> bool:
        """Whether the name of `named` in the answer file `reader` is honoured."""
        adds = self.adds(named)
        return any(
            add in self.history.ancestors(first)
            for first in self.first_carried(reader, named)
            for add in adds
        )

    def adds(self, name: str) -> tuple[int, ...]:
        """The commits that added the answer file `name`, newest first: no parent held
        it. A file git paired with a removed one as a rename is added there too."""
        found = self._adds.get(name)
        if found is None:
            path = path_of(name)
            found = tuple(
                index
                for index in self.history.touched(path)
                if (entry := self.history.entry(index, path)) is not None
                and (entry.status == "A" or (entry.status == "R" and entry.path == path))
            )
            self._adds[name] = found
        return found

    def first_carried(self, reader: str, named: str) -> tuple[int, ...]:
        """The commits where the answer file `reader` first carried the name `named` in
        `read`: carrying it where no parent did, and no other such commit an ancestor."""
        key = (reader, named)
        found = self._carried.get(key)
        if found is None:
            path = path_of(reader)
            writes: list[int] = []
            for index in self.history.touched(path):
                entry = self.history.entry(index, path)
                if entry is None or entry.status == "D" or entry.after is None:
                    continue
                if named not in self.reads(entry.after):
                    continue
                added = entry.status == "A" or entry.status == "R"
                parents = () if added else entry.before
                if not any(state is not None and named in self.reads(state) for state in parents):
                    writes.append(index)
            found = tuple(
                w
                for w in writes
                if not any(o != w and o in self.history.ancestors(w) for o in writes)
            )
            self._carried[key] = found
        return found

    def reads(self, state: TreeEntry) -> frozenset[str]:
        """Every name the version `state` of an answer file reads, any entry's."""
        found = self._reads.get(state[1])
        if found is None:
            raw = None if state[0] == LINK_MODE else self._blobs.read_object(state[1])
            parsed = read_answer_file("", raw)
            found = frozenset(name for entry in parsed.entries for name in entry.read)
            self._reads[state[1]] = found
        return found


class WorkingNames:
    """Whether a name in `read` is honoured in the working tree: a name an uncommitted
    entry carries is honoured where HEAD holds the named file (COR-062 point 5); one the
    file carried at HEAD already, by the history (`HistoryNames`)."""

    def __init__(
        self,
        head: Mapping[str, AnswerFile],
        history: HistoryNames | None,
    ) -> None:
        self._head = head
        self._history = history

    def honoured(self, reader: str, named: str) -> bool:
        at_head = self._head.get(reader)
        carried = at_head is not None and any(named in e.read for e in at_head.entries)
        if carried and self._history is not None:
            return self._history.honoured(reader, named)
        return named in self._head


# --- which answers are live ---------------------------------------------------------


@dataclass(frozen=True)
class Liveness:
    """One artefact's answers in the answer files of one state, judged (COR-062 points 4,
    5 and 7).

    - `entries`: every entry naming the artefact, by file name then position.
    - `reads`: by entry, the files it read — named, present in the state, not the
      entry's own, honoured, and not naming it back.
    - `revalidations`, `deferrals`, `revisits`: the live answers.
    - `kept`: the live deferrals a live revalidation reaches — in its own entry, or in
      a file it read.
    - `apart`: each pair of live revalidations, neither of which read the other.
    """

    entries: tuple[Entry, ...]
    reads: Mapping[Entry, frozenset[str]]
    revalidations: tuple[Entry, ...]
    deferrals: tuple[tuple[Entry, Deferment], ...]
    revisits: tuple[tuple[Entry, RevisitAnswer], ...]
    kept: frozenset[tuple[Entry, Deferment]]
    apart: tuple[tuple[Entry, Entry], ...]

    def replacers(self, entry: Entry, *, deferral: Deferment | None = None) -> tuple[Entry, ...]:
        """The present entries that replace an answer of `entry`: its revalidation, or with
        `deferral`, that deferral (COR-062 point 5)."""
        found: list[Entry] = []
        for other in self.entries:
            if other.file == entry.file or entry.file not in self.reads[other]:
                continue
            # A revalidation replaces the revalidations and the deferrals it read; a
            # deferral only the deferral of its own anchor.
            if other.revalidation is not None or (
                deferral is not None and deferral.anchor in other.deferred_anchors
            ):
                found.append(other)
        return tuple(found)

    def inherited(self, entry: Entry, deferral: Deferment) -> tuple[tuple[Entry, Deferment], ...]:
        """The deferrals of `deferral`'s anchor whose point it keeps (COR-062 point 6): those
        in a file its entry read that it replaces, and that no other answer replaced
        before it — every other replacer read its file too."""
        found: list[tuple[Entry, Deferment]] = []
        for other in self.entries:
            if other.file == entry.file or other.file not in self.reads[entry]:
                continue
            for earlier in other.deferrals:
                if earlier.anchor != deferral.anchor:
                    continue
                others = [
                    r for r in self.replacers(other, deferral=earlier) if r.file != entry.file
                ]
                if all(entry.file in self.reads[r] for r in others):
                    found.append((other, earlier))
        return tuple(found)


def liveness(
    entries: Sequence[Entry],
    present: Collection[str],
    honoured: Callable[[str, str], bool],
    *,
    declared: Collection[Anchor] | None = None,
    targets: Collection[Anchor] | None = None,
) -> Liveness:
    """Judge one artefact's `entries` — every entry naming it in the state's answer files,
    whose names are `present` — by COR-062 points 4, 5 and 7.

    `honoured(reader, named)` says whether history agrees with a name. `declared`, where
    given, are the anchors the artefact declares: a deferral of another answers nothing.
    `targets`, where given, are the targets its links take: a revisit entry for another
    answers nothing.
    """
    ordered = tuple(sorted(entries, key=lambda e: (e.file, e.index)))
    raw = {e: frozenset(e.read) - {e.file} for e in ordered}
    by_file: dict[str, list[Entry]] = {}
    for entry in ordered:
        by_file.setdefault(entry.file, []).append(entry)

    def names_back(entry: Entry, named: str) -> bool:
        return any(entry.file in raw[other] for other in by_file.get(named, ()))

    reads = {
        e: frozenset(
            named
            for named in raw[e]
            if named in present and not names_back(e, named) and honoured(e.file, named)
        )
        for e in ordered
    }
    holder = Liveness(ordered, reads, (), (), (), frozenset(), ())
    revalidations = tuple(
        e for e in ordered if e.revalidation is not None and not holder.replacers(e)
    )
    deferrals = tuple(
        (e, d)
        for e in ordered
        for d in e.deferrals
        if (declared is None or d.anchor in declared) and not holder.replacers(e, deferral=d)
    )
    revisits = tuple(
        (e, r)
        for e in ordered
        for r in e.revisits
        if (targets is None or r.anchor in targets)
        and not any(
            other.file != e.file and e.file in reads[other] and r.anchor in other.revisited_anchors
            for other in ordered
        )
    )
    live_files = {e.file for e in revalidations}
    kept = frozenset(
        (e, d)
        for e, d in deferrals
        if e.file in live_files or any(e.file in reads[r] for r in revalidations)
    )
    apart = tuple(
        (first, second)
        for position, first in enumerate(revalidations)
        for second in revalidations[position + 1 :]
        if first.file != second.file
    )
    return Liveness(ordered, reads, revalidations, deferrals, revisits, kept, apart)


# --- the reading of a state ---------------------------------------------------------


def block_holds_answers(artefact: Artefact) -> bool:
    """Whether the artefact's own block holds an answer: a `revalidated` block or a
    `revisited` list, whatever it holds. Until the move, such an artefact is read wholly
    from its block (`StateAnswers.answers`)."""
    block = artefact.friction
    return isinstance(block, Mapping) and (
        REVALIDATED_KEY in block or REVISITED_KEY in cast(Mapping[str, Any], block)
    )


@dataclass(frozen=True)
class LiveRevalidation:
    """A live revalidation: the answer file it is in (`None` in the block), `at` parsed
    and as written, its outcome and its `unchanged-because`."""

    file: str | None
    at: Any
    written: Any
    outcome: str | None
    because: str | None


@dataclass(frozen=True)
class LiveDeferral:
    """A live deferral: its file (`None` in the block), anchor and reason, and whether a
    live revalidation reaches it (`kept`; COR-062 point 5)."""

    file: str | None
    anchor: Anchor
    reason: str | None
    kept: bool = False


@dataclass(frozen=True)
class LiveRevisit:
    """A live revisit entry: its file (`None` in the block), target, outcome and reason."""

    file: str | None
    anchor: Anchor
    outcome: str | None
    reason: str | None


@dataclass(frozen=True)
class Answers:
    """An artefact's answers at a state, read wholly from one home (`home`): its block, or
    the answer files. `apart` holds, for answers read from answer files, each pair of
    files whose revalidations were made apart (COR-062 point 7). `liveness` is the
    judgment of its answer files where they were read."""

    home: str
    revalidations: tuple[LiveRevalidation, ...] = ()
    deferrals: tuple[LiveDeferral, ...] = ()
    revisits: tuple[LiveRevisit, ...] = ()
    apart: tuple[tuple[str, str], ...] = ()
    liveness: Liveness | None = field(default=None, compare=False)

    @property
    def from_files(self) -> bool:
        return self.home == FILES_HOME

    def as_json(self) -> dict[str, Any]:
        return {
            "home": self.home,
            "revalidations": [
                {
                    "file": r.file,
                    "at": r.written if isinstance(r.written, str) else None,
                    "outcome": r.outcome,
                    "unchanged_because": r.because,
                }
                for r in self.revalidations
            ],
            "deferrals": [
                {
                    "file": d.file,
                    "anchor": {"kind": d.anchor.kind, "value": d.anchor.value},
                    "reason": d.reason,
                    "kept": d.kept,
                }
                for d in self.deferrals
            ],
            "revisits": [
                {
                    "file": r.file,
                    "anchor": {"kind": r.anchor.kind, "value": r.anchor.value},
                    "outcome": r.outcome,
                    "reason": r.reason,
                }
                for r in self.revisits
            ],
            "answered_apart": [list(pair) for pair in self.apart],
        }


def block_answers(artefact: Artefact) -> Answers:
    """The answers the artefact's own block holds, as `Answers`."""
    revalidations: tuple[LiveRevalidation, ...] = ()
    revalidated = artefact.revalidated
    if isinstance(revalidated, Mapping) and "at" in revalidated:
        outcome = revalidated.get("outcome")
        revalidations = (
            LiveRevalidation(
                None,
                parsed_at(artefact),
                revalidated.get("at"),
                outcome if isinstance(outcome, str) else None,
                _folded(revalidated.get("unchanged-because")),
            ),
        )
    deferrals = tuple(
        LiveDeferral(None, d.anchor, entry_reason(artefact, d)) for d in artefact.deferrals
    )
    revisits = tuple(LiveRevisit(None, r.anchor, r.outcome, r.reason) for r in artefact.revisits)
    return Answers(BLOCK_HOME, revalidations, deferrals, revisits)


class StateAnswers:
    """The answer files of one state, and each artefact's answers there.

    `files` are the state's answer files by name; `honoured` says whether history
    agrees with a name (`HistoryNames`, `WorkingNames`); `locations(artefact)` gives
    every location an answer may name the artefact by — its location under each
    name its file had, so an answer follows the renames of its file (COR-062 point
    10). An entry moved between collection files starts again where it lands, so its
    old location is none of these.
    """

    def __init__(
        self,
        files: Mapping[str, AnswerFile],
        honoured: Callable[[str, str], bool],
        locations: Callable[[Artefact], Collection[str]],
    ) -> None:
        self.files = dict(files)
        self._honoured = honoured
        self._locations = locations
        self._by_location: dict[str, list[Entry]] = {}
        for answer_file in self.files.values():
            for entry in answer_file.entries:
                self._by_location.setdefault(entry.location, []).append(entry)
        self._liveness: dict[tuple[str, str], Liveness] = {}

    @property
    def dormant(self) -> bool:
        """No answer file in the state."""
        return not self.files

    def entries(self, artefact: Artefact) -> tuple[Entry, ...]:
        """Every entry of the state's answer files naming `artefact`."""
        found: list[Entry] = []
        for location in dict.fromkeys(self._locations(artefact)):
            found.extend(self._by_location.get(location, ()))
        return tuple(found)

    def liveness(self, artefact: Artefact, discovery: Discovery | None = None) -> Liveness:
        """The artefact's answers in the answer files, judged (`liveness`): with
        `discovery`, a deferral of an anchor it no longer declares and a revisit entry
        for a target no link takes answer nothing."""
        key = (artefact.location, artefact.path)
        found = self._liveness.get(key)
        if found is None:
            declared = frozenset(
                Anchor(kind, value) for kind, values in artefact.anchors.items() for value in values
            )
            targets: frozenset[Anchor] | None = None
            if discovery is not None:
                targets = frozenset(
                    anchor
                    for link in discovery.links(artefact)
                    for anchor in link_targets(artefact, link)
                )
            found = liveness(
                self.entries(artefact),
                self.files,
                self._honoured,
                declared=declared,
                targets=targets,
            )
            self._liveness[key] = found
        return found

    def answers(self, artefact: Artefact, discovery: Discovery | None = None) -> Answers:
        """The artefact's answers at this state, read wholly from one home: its block,
        where the block holds an answer, else the answer files (the transitional rule,
        until the move)."""
        if block_holds_answers(artefact):
            return block_answers(artefact)
        judged = self.liveness(artefact, discovery)
        return Answers(
            FILES_HOME,
            tuple(
                LiveRevalidation(
                    e.file,
                    e.revalidation.at,
                    e.revalidation.written,
                    e.revalidation.outcome,
                    e.revalidation.because,
                )
                for e in judged.revalidations
                if e.revalidation is not None
            ),
            tuple(
                LiveDeferral(e.file, d.anchor, d.reason, (e, d) in judged.kept)
                for e, d in judged.deferrals
            ),
            tuple(LiveRevisit(e.file, r.anchor, r.outcome, r.reason) for e, r in judged.revisits),
            tuple((a.file, b.file) for a, b in judged.apart),
            judged,
        )

    def prunable(self, discovery: Discovery) -> tuple[str, ...]:
        """The answer files in which no answer is live at this state, sorted: what a prune
        would remove (COR-062 point 8; ADR-068 point 4). An entry whose location holds no
        artefact answers nothing."""
        live: set[str] = set()
        for artefact in discovery.artefacts:
            judged = self.liveness(artefact, discovery)
            live.update(e.file for e in judged.revalidations)
            live.update(e.file for e, _d in judged.deferrals)
            live.update(e.file for e, _r in judged.revisits)
        return tuple(sorted(name for name in self.files if name not in live))

    def gone(self, discovery: Discovery) -> tuple[Entry, ...]:
        """The entries whose location, followed through renames, holds no artefact."""
        named: set[Entry] = set()
        for artefact in discovery.artefacts:
            named.update(self.entries(artefact))
        return tuple(
            entry
            for answer_file in self.files.values()
            for entry in answer_file.entries
            if entry not in named
        )


def renames(target_root: Path) -> Mapping[str, str]:
    """Each path HEAD's history renamed a file away from, with the name the file took
    there, from git's own rename detection: what a location written before a move is
    followed through (COR-062 point 10). One `git log`, newest first; a path renamed away
    twice keeps its newest move."""
    try:
        listed = run_git(
            target_root,
            "log",
            "-z",
            "--no-color",
            "--format=",
            "--name-status",
            "-M",
            "--diff-filter=R",
            "HEAD",
            "--",
            accept=(0, 128),
        )
    except FrictionCheckError:
        return {}
    if listed.returncode != 0:
        return {}
    moved: dict[str, str] = {}
    tokens = listed.stdout.decode("utf-8", "surrogateescape").split("\0")
    for entry in parse_name_status([t.lstrip("\n") for t in tokens if t.strip()]):
        if entry.old_path is not None:
            moved.setdefault(entry.old_path, entry.path)
    return moved


def follow(path: str, moved: Mapping[str, str]) -> str:
    """Where the file once at `path` is now, following `moved` (`renames`) to its end."""
    seen = {path}
    while path in moved and moved[path] not in seen:
        path = moved[path]
        seen.add(path)
    return path


def working_locator(discovery: Discovery, target_root: Path) -> Callable[[str], Artefact | None]:
    """The artefact of the working tree's discovery an entry's location names: its own
    location, else its file followed through HEAD's renames (`renames`). An entry moved
    between collection files is not followed: its old location names nothing."""
    by_location = {artefact.location: artefact for artefact in discovery.artefacts}
    moved: Mapping[str, str] | None = None

    def locate(location: str) -> Artefact | None:
        nonlocal moved
        found = by_location.get(location)
        if found is not None:
            return found
        if moved is None:
            moved = renames(target_root)
        for artefact in discovery.artefacts:
            name = location if artefact.kind is ArtefactKind.DOCUMENT else None
            if name is None:
                path, _, entry_id = location.rpartition("#")
                if entry_id != artefact.id:
                    continue
                name = path
            if name != artefact.path and follow(name, moved) == artefact.path:
                return artefact
        return None

    return locate


def head_locations(history: History | None) -> Callable[[Artefact], tuple[str, ...]]:
    """`StateAnswers.locations` for a state read with `history`: the artefact's location
    under every name its file had (`History.names`), its own first; without a history,
    its own alone."""

    def locations(artefact: Artefact) -> tuple[str, ...]:
        names = (artefact.path,) if history is None else history.names(artefact.path)
        return tuple(location_of(artefact, name) for name in names)

    return locations


# --- points across homes ------------------------------------------------------------


@dataclass(frozen=True)
class AnswerPoints:
    """What the walk across homes found for an artefact's answers: `points`, as the checks
    read them, and per live deferral, in `Answers.deferrals` order, the points it keeps."""

    points: Points
    deferrals: tuple[tuple[int, ...], ...] = ()
    # Per live revalidation, in `Answers.revalidations` order, the points of its value.
    revalidations: tuple[tuple[int, ...], ...] = ()


class AnswerHistory:
    """The answer files through one history, beside each artefact's block (COR-062
    point 6): every version of every answer file read once, by its object.

    `dormant` — no answer file in the history — leaves every reading to the
    artefact's block, exactly as before.
    """

    def __init__(self, history: History, walker: Walker, blobs: BlobReader) -> None:
        self.history = history
        self.walker = walker
        self.blobs = blobs
        self.trees = TreeReader(blobs)
        self.names = HistoryNames(history, blobs)
        self.paths = tuple(p for p in history.paths if is_answer_file(p))
        self._parsed: dict[str, AnswerFile] = {}
        self._naming: dict[str, bool] = {}
        self._at: dict[str, Mapping[str, TreeEntry]] = {}
        self._locations: dict[str, frozenset[str]] = {}

    @property
    def dormant(self) -> bool:
        return not self.paths

    # --- reading -------------------------------------------------------------------

    def parsed(self, state: TreeEntry, name: str) -> AnswerFile:
        found = self._parsed.get(state[1])
        if found is None:
            raw = None if state[0] == LINK_MODE else self.blobs.read_object(state[1])
            found = self._parsed[state[1]] = read_answer_file(name, raw)
        return found if found.name == name else _renamed(found, name)

    def versions(self, path: str) -> list[tuple[int, TreeEntry]]:
        """Each commit that left the answer file at `path` with content, and that content."""
        found: list[tuple[int, TreeEntry]] = []
        for index in self.history.touched(path):
            entry = self.history.entry(index, path)
            if entry is not None and entry.status != "D" and entry.after is not None:
                found.append((index, entry.after))
        return found

    def files_at(self, sha: str) -> Mapping[str, TreeEntry]:
        """The answer files a commit holds, by name."""
        found = self._at.get(sha)
        if found is None:
            listed = self.trees.listing(sha, FOLDER)
            found = self._at[sha] = {
                name: entry
                for name, entry in listed.items()
                if name.endswith(SUFFIX) and entry[0] != "040000"
            }
        return found

    def state(self, files: Mapping[str, AnswerFile]) -> StateAnswers:
        """The state whose answer files are `files`, read with this history."""
        return StateAnswers(files, self.names.honoured, head_locations(self.history))

    def head(self, head_sha: str) -> StateAnswers:
        """HEAD's answer files, judged with this history."""
        files = {name: self.parsed(entry, name) for name, entry in self.files_at(head_sha).items()}
        return self.state(files)

    # --- whether a commit's answers carry something --------------------------------

    def _names_artefact(self, like: Artefact) -> frozenset[str]:
        """Every location an answer may name `like` by (`head_locations`), read once."""
        found = self._locations.get(like.location)
        if found is None:
            found = self._locations[like.location] = frozenset(head_locations(self.history)(like))
        return found

    def ever_named(self, like: Artefact) -> bool:
        """Whether any answer file in the history names `like`."""
        found = self._naming.get(like.location)
        if found is None:
            locations = self._names_artefact(like)
            found = any(
                entry.location in locations
                for path in self.paths
                for _index, state in self.versions(path)
                for entry in self.parsed(state, name_of(path)).entries
            )
            self._naming[like.location] = found
        return found

    def _block_at(self, like: Artefact, sha: str) -> Artefact | None:
        for name in self.history.names(like.path):
            entry = self.trees.entry(sha, name)
            if entry is not None:
                return self.walker.artefact_in(entry, name, like)
        return None

    def _entries_at(self, like: Artefact, sha: str) -> list[Entry]:
        locations = self._names_artefact(like)
        return [
            entry
            for name, state in self.files_at(sha).items()
            for entry in self.parsed(state, name).entries
            if entry.location in locations
        ]

    def _carries(
        self,
        like: Artefact,
        sha: str,
        in_block: Callable[[Artefact | None], bool],
        in_entry: Callable[[Entry], bool],
    ) -> bool:
        if in_block(self._block_at(like, sha)):
            return True
        return any(in_entry(entry) for entry in self._entries_at(like, sha))

    def _writes(
        self,
        like: Artefact,
        candidates: Iterable[int],
        in_block: Callable[[Artefact | None], bool],
        in_entry: Callable[[Entry], bool],
    ) -> tuple[list[int], bool]:
        """Of `candidates`, the commits where the artefact's answers, in either home, carry
        what the two tests look for where no parent's did — within the artefact's own
        history (`_since_added`). Also whether one lies where a shallow clone is cut,
        carrying it there: then where it was first carried cannot be told."""
        since = self._since_added(like)
        writes: list[int] = []
        for index in sorted(set(candidates)):
            if since is not None and index not in since:
                continue
            commit = self.history.commits[index]
            if not self._carries(like, commit.sha, in_block, in_entry):
                continue
            if self.history.is_cut(index):
                return [], True
            if not any(
                self._carries(like, parent, in_block, in_entry) for parent in commit.parents
            ):
                writes.append(index)
        return writes, False

    def _since_added(self, like: Artefact) -> frozenset[int] | None:
        versions = list(self.history.versions(like.path))
        if not versions:
            return None
        return self.history.descendants(versions[-1].index)

    def _file_candidates(self, like: Artefact, in_entry: Callable[[Entry], bool]) -> set[int]:
        locations = self._names_artefact(like)
        return {
            index
            for path in self.paths
            for index, state in self.versions(path)
            if any(
                entry.location in locations and in_entry(entry)
                for entry in self.parsed(state, name_of(path)).entries
            )
        }

    # --- a revalidation's value ----------------------------------------------------

    def carried(self, like: Artefact, value: Any) -> Carried:
        """Where the artefact's answers, in either home, first carried `value` — a parsed
        `at` (COR-062 point 6). Without `at` (`BLOCK`), or where no answer file ever
        named the artefact, its block's own walk (`Walker.carried`)."""
        if value is BLOCK or self.dormant or not self.ever_named(like):
            return self.walker.carried(like, value)
        block = self.walker.block_writes(like, value)
        if block.unreachable:
            return block
        in_block = carrier(value)

        def in_entry(entry: Entry) -> bool:
            return entry.revalidation is not None and entry.revalidation.at == value

        candidates = set(block.points) | self._file_candidates(like, in_entry)
        writes, unreachable = self._writes(like, candidates, in_block, in_entry)
        if unreachable:
            return Carried((), unreachable=True, cut=True)
        return self.walker.first_carried(like, writes, cut=block.cut)

    # --- a deferral's point --------------------------------------------------------

    def deferral_points(
        self,
        like: Artefact,
        liveness: Liveness,
        entry: Entry,
        deferral: Deferment,
        seen: frozenset[tuple[str, Anchor]] = frozenset(),
    ) -> tuple[tuple[int, ...], bool]:
        """The points a deferral in an answer file keeps, and whether one lies beyond a
        shallow clone (COR-062 point 6). One that replaces deferrals of its anchor it read
        keeps theirs; any other starts a point of its own, unless it puts back a deferral
        with its anchor and reason, or moves one out of the block: then it keeps that
        one's point."""
        key = (entry.file, deferral.anchor)
        inherited = [
            found
            for found in liveness.inherited(entry, deferral)
            if (found[0].file, found[1].anchor) not in seen
        ]
        if inherited:
            points: set[int] = set()
            unreachable = False
            for other, earlier in inherited:
                found, beyond = self.deferral_points(like, liveness, other, earlier, seen | {key})
                points.update(found)
                unreachable = unreachable or beyond
            return tuple(sorted(points)), unreachable
        return self._deferral_carried(like, deferral.anchor, deferral.reason)

    def _deferral_carried(
        self, like: Artefact, anchor: Anchor, reason: str | None
    ) -> tuple[tuple[int, ...], bool]:
        def in_block(found: Artefact | None) -> bool:
            return found is not None and any(
                d.anchor == anchor and entry_reason(found, d) == reason for d in found.deferrals
            )

        def in_entry(entry: Entry) -> bool:
            return any(d.anchor == anchor and d.reason == reason for d in entry.deferrals)

        if reason is None:  # no text to tell a deferral put back by: one of its own
            block = Deferred(None)
        else:
            block = self.walker.deferral_point(like, anchor, reason)
        if block.unreachable:
            return (), True
        writes, unreachable = self._writes(
            like, self._file_candidates(like, in_entry), in_block, in_entry
        )
        if unreachable:
            return (), True
        candidates = [*writes, *(() if block.point is None else (block.point,))]
        return tuple(self.walker.first(candidates)), False

    # --- one artefact --------------------------------------------------------------

    def points(self, like: Artefact, answers: Answers) -> AnswerPoints:
        """The points of an artefact's answers (COR-050 points 3 and 4, COR-062 point 6):
        read from its block, its block's walk, each value found across homes; read from
        answer files, every live revalidation's points — the block's own where none is
        live — and every live deferral's, with whether a revalidation reaches it."""
        if not answers.from_files:
            points = self.walker.points(like, self.carried)
            return AnswerPoints(
                points,
                tuple(() if p is None else (p,) for _a, p in points.deferrals),
                tuple(points.revalidations for _ in answers.revalidations),
            )
        versions = list(self.history.versions(like.path))
        if not versions:
            unwalked = self.walker.unwalked(
                like, tuple((d.anchor, None) for d in answers.deferrals)
            )
            return AnswerPoints(
                Points(
                    unwalked.revalidations,
                    unwalked.deferrals,
                    unwalked.moves,
                    unwalked.own_paths,
                    unwalked.unreachable,
                    kept=tuple(d.kept for d in answers.deferrals),
                ),
                tuple(() for _ in answers.deferrals),
            )
        unreachable: str | None = None
        cut = False
        revalidations: set[int] = set()
        per_revalidation: list[tuple[int, ...]] = []
        for value in [r.at for r in answers.revalidations] or [BLOCK]:
            found = self.carried(like, value)
            if found.unreachable:
                unreachable = "its revalidation point"
            revalidations.update(found.points)
            per_revalidation.append(found.points)
            cut = cut or found.cut
        if not revalidations and unreachable is None:
            revalidations.add(versions[-1].index)
        per_deferral: list[tuple[int, ...]] = []
        flat: list[tuple[Anchor, int | None]] = []
        kept: list[bool] = []
        judged = answers.liveness
        live = list(judged.deferrals) if judged is not None else []
        for deferral, (entry, written) in zip(answers.deferrals, live, strict=True):
            assert judged is not None
            found_points, beyond = self.deferral_points(like, judged, entry, written)
            if beyond:
                anchor = deferral.anchor
                unreachable = unreachable or f"the deferral point of {anchor.kind} {anchor.value}"
            if not found_points and not beyond:
                found_points = (versions[-1].index,)
            per_deferral.append(found_points)
            for point in found_points or (None,):
                flat.append((deferral.anchor, point))
                kept.append(deferral.kept)
        points = self.walker.walked(
            like,
            tuple(sorted(revalidations)),
            tuple(flat),
            unreachable=unreachable,
            cut=cut and unreachable is None,
            kept=tuple(kept),
        )
        return AnswerPoints(
            points,
            tuple(per_deferral),
            tuple(per_revalidation) if answers.revalidations else (),
        )

    # --- answers made apart --------------------------------------------------------

    def first_holding(self, first: str, second: str) -> int | None:
        """The first commit holding both answer files, where two revalidations made apart
        originate as debt (COR-062 point 7): of the commits that descend from where each
        was last added, the oldest none of whose parents does. `None` where either was
        never added in this history."""
        adds_first, adds_second = self.names.adds(first), self.names.adds(second)
        if not adds_first or not adds_second:
            return None
        both = self.history.descendants(adds_first[0]) & self.history.descendants(adds_second[0])
        firsts = [
            index
            for index in both
            if not any(
                parent is not None and parent in both
                for parent in self.history.parent_positions[index]
            )
        ]
        return max(firsts) if firsts else None


def _renamed(found: AnswerFile, name: str) -> AnswerFile:
    """A file read once under another name — the same bytes in two files — under `name`."""
    entries = tuple(
        Entry(name, e.index, e.location, e.read, e.revalidation, e.deferrals, e.revisits)
        for e in found.entries
    )
    return AnswerFile(name, found.document, entries, found.problem)


__all__ = [
    "ANSWERS_KEY",
    "ARTEFACT_KEY",
    "BLOCK_HOME",
    "FILES_HOME",
    "FOLDER",
    "READ_KEY",
    "SCHEMA_KIND",
    "SUFFIX",
    "AnswerFile",
    "AnswerHistory",
    "AnswerPoints",
    "Answers",
    "Deferment",
    "Entry",
    "HistoryNames",
    "LiveDeferral",
    "LiveRevalidation",
    "LiveRevisit",
    "Liveness",
    "Revalidation",
    "RevisitAnswer",
    "StateAnswers",
    "WorkingNames",
    "block_answers",
    "block_holds_answers",
    "commit_files",
    "head_locations",
    "in_folder",
    "is_answer_file",
    "liveness",
    "location_of",
    "name_of",
    "path_of",
    "read_answer_file",
    "working_tree_files",
]
