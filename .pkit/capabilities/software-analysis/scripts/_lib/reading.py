"""Reading a flagged artefact's change, as `_lib/resolve.py` classifies it.

The evidence is the backbone's explanation, `pkit friction explain <artefact>
--json` (COR-050 point 13), which carries what a reader would otherwise
compute again (ADR-057 point 2): the artefact's state, its revalidation point
and its body (for a collection entry, the section headed by its id); each
anchor with its state and, for a path anchor, the files it stands on at the
point and at HEAD, and the files its glob covers that `friction.exclude` leaves
out; and each finding with the commits behind it, each with the paths behind
the finding it touched — for a dead path anchor, where its files went. Nothing
here matches an anchor, lists the commits that touched one, or slices a body.

Git adds what the explanation does not carry: the text of those files. For each
changed path anchor, which pieces of code the artefact quotes (what it writes
in backticks) the files it stood on at the point held, and which of those the
files it stands on at HEAD no longer hold. A file `friction.exclude` leaves out
is none of them, so a quote surviving only in such a file is gone.

And one thing only this reading derives: **where lost code went**. The quoted
code an anchor no longer holds moved when one file outside it, of a kind (by
its extension) the anchor's files are, now holds every piece of it and held
none of it at the point — a file renamed, or the code carried into another
file. An anchor the artefact quotes nothing from, gone because its files are,
moved where git's rename detection says the files it stood on at the point
went. Anything else is not a move: more than one such file, a quote found only
in a file of another kind, a quote the file already held — and never a file
the anchor's glob covers that `friction.exclude` leaves out, where the anchor
re-pointed would stand on nothing.

Both read HEAD, as the explanation does: uncommitted work is not read.

An artefact the checks did not judge is refused, never read: `unreachable` (a
point beyond a shallow clone), `unresolved` (an anchor of it cannot be
resolved, so whether what it denotes changed cannot be told), and any state
this reading does not know, which a later backbone may add — read as not
judged, never as current (the CLI README, "Friction checks"). An anchor in a state
this reading does not know is kept with that state, which the classification reads
as not judged (`_lib/resolve.py`). The explanation is read by its keys (ADR-097
point 3): a key the reading needs that is missing, null where the CLI reference
prints no null, or of another type is a document it cannot read, never a default.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import backbone
from _lib import document_keys as keys
from _lib.model import Unreadable
from _lib.resolve import DEAD, Anchor, Commit

#: A piece of code quoted in Markdown, and a template placeholder that is none.
_QUOTE = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER = re.compile(r"^<[^>]*>$")

#: The artefact states this reading reads: judged, or with nothing to judge.
_READ_STATES = frozenset({"current", "stale", "deferred", "unanchored", "excluded"})


@dataclass(frozen=True)
class Reading:
    """What the evidence says of one artefact: its id and location, its state, HEAD
    and its revalidation point, and each of its anchors."""

    artefact: str
    location: str
    state: str
    head: str | None
    point: str | None
    anchors: tuple[Anchor, ...]


@dataclass(frozen=True)
class _Files:
    """What a path anchor stands on, as the explanation names it (`files`): the files
    at the revalidation point and at HEAD, and those its glob covers at HEAD that
    `friction.exclude` leaves out."""

    point: tuple[str, ...]
    head: tuple[str, ...]
    excluded: frozenset[str]


def read(root: Path, artefact: str) -> Reading:
    """The evidence on `artefact`. Raises Unreadable when the backbone cannot explain it."""
    return reading_of(
        backbone.explain(root, artefact),
        artefact,
        lambda *path: _read_path(root, *path),
    )


#: How a changed path anchor is read against the files it stood on (`_read_path`, less
#: the root): a test stands it in.
PathReader = Callable[[Anchor, "_Files", tuple[str, ...], str, str], Anchor]


def reading_of(document: Mapping[str, Any], artefact: str, read_path: PathReader) -> Reading:
    """The explanation of `artefact`, `pkit friction explain --json`, as its evidence,
    each changed path anchor read through `read_path`. Raises Unreadable for an
    artefact the checks did not judge, and for a key the reading needs that the
    document gives missing, null or of another type."""
    try:
        return _reading(document, artefact, read_path)
    except keys.Untold as exc:
        raise Unreadable(
            f"`pkit friction explain {artefact} --json` answered a document this capability "
            f"cannot read: {exc}"
        ) from exc


def _reading(document: Mapping[str, Any], artefact: str, read_path: PathReader) -> Reading:
    state = keys.text(document, "state", "")
    if state == "unreachable":
        raise Unreadable(
            f"{artefact}'s revalidation point lies beyond this shallow clone's history: "
            f"`git fetch --unshallow`, then ask again"
        )
    if state == "unresolved":
        raise Unreadable(
            f"{artefact} is not judged: an anchor of it cannot be resolved, so whether what it "
            f"denotes changed cannot be told — `pkit friction explain {artefact}` says which, "
            f"and what clears it"
        )
    if state not in _READ_STATES:
        raise Unreadable(
            f"`pkit friction explain` gives {artefact} the state {state!r}, which this "
            f"capability does not read: it is not judged, never current — `pkit friction "
            f"explain {artefact}` says why"
        )
    location = keys.text(document, "location", "") or artefact
    point = _commit(document, "revalidation_point")
    head = _commit(document, "head")
    commits = _commits_by_anchor(document)
    quotes = _quotes(keys.text(document, "body", ""))
    anchors: list[Anchor] = []
    for where, entry in keys.objects(document, "anchors", ""):
        kind, value = keys.text(entry, "kind", where), keys.text(entry, "value", where)
        anchor = Anchor(
            kind=kind,
            value=value,
            state=keys.text(entry, "state", where),
            commits=commits.get((kind, value), ()),
        )
        files = _files(keys.mapping_or_null(entry, "files", where), f"{where}.files")
        if anchor.changed and kind == "path" and files is not None and point is not None:
            anchor = read_path(anchor, files, quotes, point, head or "HEAD")
        anchors.append(anchor)
    return Reading(
        artefact=keys.text(document, "artefact", "") or artefact,
        location=location,
        state=state,
        head=head,
        point=point,
        anchors=tuple(anchors),
    )


def _commit(document: Mapping[str, Any], key: str) -> str | None:
    """The commit of the object at `key`, `None` where the document prints it null."""
    found = keys.mapping_or_null(document, key, "")
    return None if found is None else _text(keys.text(found, "commit", key))


def _read_path(
    root: Path, anchor: Anchor, files: _Files, quotes: tuple[str, ...], point: str, head: str
) -> Anchor:
    """A changed path anchor with what the artefact quotes from the files it stood on
    at `point`, what of that the files it stands on at `head` no longer hold, and —
    where it resolves to nothing, or lost quoted code — where that went."""
    held = {q: backbone.files_holding(root, point, q, files.point) for q in quotes}
    quoted = tuple(q for q in quotes if held[q])
    gone = tuple(q for q in quoted if not backbone.files_holding(root, head, q, files.head))
    lost = anchor.state == DEAD or bool(gone)
    moved_to = _moved_to(root, point, head, files, {q: held[q] for q in gone}) if lost else ()
    return Anchor(anchor.kind, anchor.value, anchor.state, anchor.commits, quoted, gone, moved_to)


def _moved_to(
    root: Path, point: str, head: str, files: _Files, gone: Mapping[str, set[str]]
) -> tuple[str, ...]:
    """Where the code a path anchor lost since `point` went, or `()` when the reading
    cannot name one place: the one file outside the anchor, of a kind its files are,
    that holds every piece of `gone` at `head` and held none of it at `point` — or,
    with nothing quoted from it, where git says the files it stood on at `point` were
    renamed to. `gone` maps each lost quote to the anchor's files that held it at
    `point`. A file the anchor's glob covers that `friction.exclude` leaves out is
    never where code went."""
    if not gone:
        renamed = backbone.renamed(root, point, head, files.point)
        return tuple(path for path in renamed if path not in files.excluded)
    kinds = {_kind(path) for holding in gone.values() for path in holding}
    arrived: set[str] | None = None
    for quote in gone:
        fresh = backbone.files_holding(root, head, quote) - backbone.files_holding(
            root, point, quote
        )
        fresh -= files.excluded
        arrived = fresh if arrived is None else arrived & fresh
        if not arrived:
            return ()
    found = sorted(path for path in arrived or () if _kind(path) in kinds)
    return tuple(found) if len(found) == 1 else ()


def _kind(path: str) -> str:
    """A file's kind, as far as a move goes: its extension."""
    return Path(path).suffix


def _quotes(body: str) -> tuple[str, ...]:
    """What the artefact quotes: the backticked code of its body, as the explanation
    gives it — for a collection entry, the section headed by its id — placeholders
    left out."""
    return tuple(
        dict.fromkeys(
            quote.strip()
            for quote in _QUOTE.findall(body)
            if quote.strip() and not _PLACEHOLDER.match(quote.strip())
        )
    )


def _files(files: Mapping[str, Any] | None, where: str) -> _Files | None:
    """A path anchor's `files`, or `None` for another kind, or when there is no
    revalidation point to read them at."""
    if files is None or keys.value(files, "point", where) is None:
        return None
    return _Files(
        point=_paths(keys.texts(files, "point", where)),
        head=_paths(keys.texts(files, "head", where)),
        excluded=frozenset(_paths(keys.texts(files, "excluded", where))),
    )


def _commits_by_anchor(document: Mapping[str, Any]) -> dict[tuple[str, str], tuple[Commit, ...]]:
    """The commits behind each anchor's findings, each once, in the order the findings
    give them — each finding's oldest first — with every path behind them it touched."""
    found: dict[tuple[str, str], dict[str, Commit]] = {}
    for where, finding in keys.objects(document, "findings", ""):
        anchor = keys.mapping_or_null(finding, "anchor", where)
        if anchor is None:
            continue
        on = f"{where}.anchor"
        seen = found.setdefault((keys.text(anchor, "kind", on), keys.text(anchor, "value", on)), {})
        for inner, commit in keys.objects(finding, "commits", where):
            sha = keys.text(commit, "commit", inner)
            paths = _paths(keys.texts(commit, "paths", inner))
            earlier = seen.get(sha)
            if earlier is not None:
                paths = tuple(sorted({*earlier.paths, *paths}))
            seen[sha] = Commit(sha, keys.text(commit, "change", inner), paths)
    return {key: tuple(commits.values()) for key, commits in found.items()}


def _paths(value: Sequence[str]) -> tuple[str, ...]:
    return tuple(item for item in value if item)


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
