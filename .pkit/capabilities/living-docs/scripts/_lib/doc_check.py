"""This capability's contribution to the documentation-check point (DEC-001 point 7).

`pkit::work-tracking:doc-check` is the data point the provider of the
`pkit::work-tracking` role defines: the documentation obligations a pull
request may owe (project-management DEC-053). This capability contributes the
two kinds a documentation capability owes it (DEC-053 point 4), read from the
backbone's whole-repository friction check, `pkit friction check --all --json`,
which judges HEAD against its history (COR-050). The check is asked to judge the
pages alone (`Pages`): the obligations read no other artefact's judgement, and
its measures stay the whole repository's.

- **`page-stale`** — one per page of the spaces the check reports `stale`. Its
  `document` is the page, whose answer in the diff — updated, unchanged with
  its justification, or deferred with its reason — meets it. A page the check
  reports `deferred` gives none: its deferral is the answer (project-management
  DEC-053 point 4), and `pkit friction debt` reports it as debt — the check
  would otherwise refuse every later pull request that leaves the page alone.
  A page anchored on one part — a record's point, a page's section or its lead
  — is stale only when what that part stands on changed, as the check reads it
  (COR-050 point 5), and the obligation names the anchor as the check gives it.
- **`code-undocumented`** — one per path of the declared surface that nothing
  anchors (COR-050 point 8). Its `path` is the code, and it names no
  `document`: no page's change answers it, only a page anchoring the path.
  The obligation leaves the point once one does, since the check reads HEAD:
  that is how it is met (DEC-053 point 2).

Every obligation's source is `friction` — the signal, never the capability that
reads it, so another provider of the documentation role contributes under the
same enforcement setting — and its id is `friction:<reason>:<page or path>`,
so no two collide in the point's `additive` merge.

**Fail closed.** A check that gives no document, or one of a `schema_version`
this reading does not understand (a document without the key comes from a
backbone that predates it, and reads as version 1), or one it cannot tell
anything from at a key it reads — the key missing, null where the CLI reference
does not print it null, or of another type (ADR-097 point 3) — or a page the
check could not judge because it did not do its work, is no answer — raised,
never an empty list: the point is `fail`, and a gate never passes on fewer
obligations than it should. A page is judged when its state is `current`,
`stale` or `deferred`. `unreachable` (its friction lies beyond a shallow clone's
history), `unresolved` with an anchor whose resolver gave no answer
(`no-answer`), a state this reading does not know, and a finding of a kind it
does not know on the page are no judgment (the CLI reference, "Every reading
document carries its version"). A page `unresolved` only because nothing
installed resolves one of its anchors' kinds (`unresolved-kind`) owes what its
other anchors owe: that anchor is a declaration for the project to mend, which
the change check fails where a change is why and validation reports (COR-050
point 12), never a reason to fail every later check. A repository with no commit
owes nothing: there is no HEAD to judge.
These are the two cases a filler that reads history tells apart (COR-052 point
6): history that does not exist yet holds nothing, and the answer is `[]`;
history that exists and cannot be read is no answer. Whether HEAD names a
commit is the backbone's to say — `head` in `pkit repository base --json`, which
tells a HEAD with no commit yet from one git cannot read here — so this module
asks git nothing. A history a shallow clone cut short is the other way it cannot
be read: only the filler knows how far back it reads, so detecting it is this
module's.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from _lib import backbone
from _lib import document_keys as keys

POINT = "pkit::work-tracking:doc-check"
POINT_VERSION = 1

#: The obligations' source, and their two reasons (the point's companion schema).
SOURCE = "friction"
PAGE_STALE = "page-stale"
CODE_UNDOCUMENTED = "code-undocumented"

#: The artefact states and finding kinds the whole-repository check reports that
#: matter here: only `stale` is owed — a `deferred` page carries its answer.
STALE = "stale"
UNREACHABLE = "unreachable"
UNRESOLVED = "unresolved"

#: The two finding kinds that leave a page `unresolved`: an anchor of a kind nothing
#: installed resolves — a declaration for the project to mend — and an anchor whose
#: resolver gave no answer — a check that did not do its work.
UNRESOLVED_KIND = "unresolved-kind"
NO_ANSWER = "no-answer"

#: The states in which the check judged a page. Any other — `unreachable`,
#: `unresolved`, one this reading does not know — is no judgment, so no answer,
#: unless the page is `unresolved` only by `UNRESOLVED_KIND` (`_only_by_kind`).
JUDGED = frozenset({"current", STALE, "deferred"})

#: Every finding kind the whole-repository check reports (the CLI reference, `friction
#: check --all`). A page with a finding of another kind is not judged: the kind may
#: mean anything, so the page may owe what this reading cannot see.
FINDING_KINDS = frozenset(
    {
        STALE,
        "deferred",
        "left-out",
        "dead-anchor",
        "unresolved-kind",
        "no-answer",
        "over-broad",
        "shared-id",
        "whole-and-parts",
        "unreachable",
        "unreadable",
        "answered-apart",
    }
)

#: The backbone's readings this contribution reads: the whole-repository check, and
#: settled state for whether HEAD names a commit (`head`).
CHECK_ARGV = ("pkit", "friction", "check", "--all", "--json")
BASE_ARGV = ("pkit", "repository", "base", "--json")

#: What has the check judge only the artefacts listed on its standard input: the pages.
SELECTION_ARGV = ("--artefacts-from", "-")

#: The version of each reading this capability understands. A check's document
#: without `schema_version` comes from a backbone that predates the key: version 1.
#: `pkit repository base` has printed the key from the first.
READING_VERSION = 1

Runner = Callable[..., subprocess.CompletedProcess[str]]


class NoAnswer(Exception):
    """The friction on the pages cannot be read in full: the filler gives no answer."""


@dataclass(frozen=True)
class _Finding:
    """One finding of the check: where it lies, `None` for one on no artefact, its kind,
    and the anchor it names as `(kind, value)`, `None` for none."""

    location: str | None
    kind: str
    anchor: tuple[str, str] | None


@dataclass(frozen=True)
class _Friction:
    """The check's document, as this reading reads it: whether the check is dormant,
    each artefact's location and state, the findings, and the uncovered surface."""

    dormant: bool
    states: tuple[tuple[str, str], ...]
    findings: tuple[_Finding, ...]
    uncovered: tuple[str, ...]


def has_commit(root: str, run: Runner = backbone.run) -> bool:
    """Whether HEAD names a commit — the history the friction check reads — as the
    backbone reads HEAD, `head` in `pkit repository base --json`: False only when
    there is none yet. Raises NoAnswer when the reading gives no answer, or says
    git cannot read HEAD here: history that exists and was not read is never
    history that does not exist."""
    return commit_named(_document(BASE_ARGV, root, run))


def commit_named(document: Mapping[str, Any]) -> bool:
    """Whether the `pkit repository base --json` document says HEAD names a commit, as
    `has_commit` reads it."""
    _versioned(BASE_ARGV, document, "head", absent=None)
    try:
        head = keys.mapping(document, "head", "")
        commit = keys.text_or_null(head, "commit", "head")
        unborn = keys.flag(head, "unborn", "head")
        problem = keys.text_or_null(head, "problem", "head")
    except keys.Untold as exc:
        raise _unreadable(BASE_ARGV, exc) from exc
    if commit:
        return True
    if unborn:
        return False
    raise NoAnswer(
        problem.rstrip(".")
        if problem
        else "HEAD names no commit this clone can read, and the backbone does not say why"
    )


class Pages:
    """The pages, handed to a check started before they are known: the check reads them
    from its standard input (`SELECTION_ARGV`), as late as just before it judges any
    artefact, so telling the pages adds little to its time or none.

    `give` writes them, one a line, and ends the list: given none, the check judges
    none. `close` lets go of both ends, so a `give` still writing to a check that has
    ended stops rather than waits on a reader that is gone."""

    def __init__(self) -> None:
        read, write = os.pipe()
        self.reader = os.fdopen(read, "r", encoding="utf-8")
        self._writer = os.fdopen(write, "w", encoding="utf-8")

    def give(self, pages: Iterable[str]) -> None:
        try:
            self._writer.writelines(f"{page}\n" for page in pages)
        except (BrokenPipeError, ValueError):
            pass  # the check has ended and been let go of: it reads no more
        finally:
            _quietly_closed(self._writer)

    def close(self) -> None:
        _quietly_closed(self.reader)
        _quietly_closed(self._writer)


def _quietly_closed(end: Any) -> None:
    """Close one end of the pipe; a write the close flushes that finds no reader is owed
    nothing."""
    with contextlib.suppress(OSError):
        end.close()


def read_friction(
    root: str, run: Runner = backbone.run, *, pages: Pages | None = None
) -> Mapping[str, Any]:
    """The whole-repository check's machine-readable document, through `pkit`: with
    `pages`, judging the pages alone, each as the whole check judges it, the measures
    still the whole repository's. The obligations read no other artefact's judgement,
    so the check does not pay for every one. Raises NoAnswer when it gives none, or one
    of a version this reading does not understand."""
    if pages is None:
        return friction_of(_document(CHECK_ARGV, root, run))
    called = (*CHECK_ARGV, *SELECTION_ARGV)
    return friction_of(_document(CHECK_ARGV, root, run, called, stdin=pages.reader))


def judged_as_handed(report: Mapping[str, Any], pages: Iterable[str]) -> None:
    """Raise NoAnswer unless the check judged the pages it was handed, as its `selection`
    names them: a list cut short on its way reads like a whole one, and a page the check
    was never handed would owe nothing, unread. A dormant check judges nothing, so it
    names none."""
    try:
        if keys.flag(report, "dormant", ""):
            return
        selection = keys.mapping_or_null(report, "selection", "")
        named = None if selection is None else keys.texts(selection, "named", "selection")
    except keys.Untold as exc:
        raise _unreadable(CHECK_ARGV, exc) from exc
    handed = sorted(set(pages))
    if named is None or sorted(set(named)) != handed:
        judged = "every artefact" if named is None else f"{len(set(named))} artefact(s)"
        raise NoAnswer(
            f"`{' '.join(CHECK_ARGV)}` judged {judged}, not the {len(handed)} page(s) handed to it"
        )


def friction_of(document: Mapping[str, Any]) -> Mapping[str, Any]:
    """The whole-repository check's document, at the version this reading reads.
    Raises NoAnswer as `read_friction` does."""
    return _versioned(CHECK_ARGV, document, "artefacts", absent=READING_VERSION)


def _document(
    argv: Sequence[str],
    root: str,
    run: Runner,
    called: Sequence[str] | None = None,
    **options: Any,
) -> Mapping[str, Any]:
    """The document a backbone reading prints: `argv` names the reading, and `called`,
    where given, is the argument list it runs with, what it is asked of added, with
    `subprocess.run`'s `options`. Raises NoAnswer when it gives none."""
    try:
        proc = run(
            list(called or argv), cwd=root, capture_output=True, text=True, check=False, **options
        )
    except OSError as exc:
        raise NoAnswer(f"`pkit` could not be run ({exc})") from exc
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if proc.returncode != 0 or not isinstance(document, Mapping):
        detail = (proc.stderr or "").strip().splitlines()
        raise NoAnswer(
            f"`{' '.join(argv)}` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else "")
        )
    return document


def _versioned(
    argv: Sequence[str], document: Mapping[str, Any], key: str, *, absent: int | None
) -> Mapping[str, Any]:
    """`document`, one that carries `key`, at the version this capability reads; a
    document without `schema_version` reads as `absent`, and as no version where that
    is `None`. Raises NoAnswer otherwise."""
    if key not in document:
        raise NoAnswer(f"`{' '.join(argv)}` answered without `{key}`, so without its document")
    version = document.get("schema_version", absent)
    if type(version) is not int or version != READING_VERSION:
        raise NoAnswer(
            f"`{' '.join(argv)}` answered schema_version {version!r}; "
            f"this capability reads {READING_VERSION}"
        )
    return document


def _unreadable(argv: Sequence[str], exc: keys.Untold) -> NoAnswer:
    return NoAnswer(f"`{' '.join(argv)}` answered a document this capability cannot read: {exc}")


def _friction(report: Mapping[str, Any]) -> _Friction:
    """The check's document as this reading reads it. Raises NoAnswer at a key it
    cannot tell anything from (ADR-097 point 3)."""
    try:
        dormant = keys.flag(report, "dormant", "")
        states = tuple(
            (keys.text(entry, "location", where), keys.text(entry, "state", where))
            for where, entry in keys.objects(report, "artefacts", "")
        )
        findings = tuple(
            _finding(where, entry) for where, entry in keys.objects(report, "findings", "")
        )
        measures = keys.mapping(report, "measures", "")
        uncovered = keys.texts(measures, "uncovered_surface", "measures")
    except keys.Untold as exc:
        raise _unreadable(CHECK_ARGV, exc) from exc
    return _Friction(dormant, states, findings, uncovered)


def _finding(where: str, entry: Mapping[str, Any]) -> _Finding:
    anchor = keys.mapping_or_null(entry, "anchor", where)
    inner = keys.at(where, "anchor")
    return _Finding(
        location=keys.text_or_null(entry, "location", where),
        kind=keys.text(entry, "kind", where),
        anchor=(
            None
            if anchor is None
            else (keys.text(anchor, "kind", inner), keys.text(anchor, "value", inner))
        ),
    )


def obligations(report: Mapping[str, Any], pages: Iterable[str]) -> list[dict[str, Any]]:
    """The obligations `report` gives rise to: the stale pages, then the uncovered
    surface, each sorted. A page left unjudged only by an anchor of a kind nothing
    installed resolves owes what its other anchors owe (`_only_by_kind`). Raises
    NoAnswer when the check did not do its work on a page: its points lie beyond
    this clone's history, an anchor's resolver gave no answer, its state is one
    this reading does not know, or a finding on it is of a kind this reading does
    not know; and when the report cannot be read."""
    friction = _friction(report)
    if friction.dormant:
        return []
    page_set = set(pages)
    reports = [(page, state) for page, state in friction.states if page in page_set]
    kinds = _kinds_by_location(friction.findings)
    unreachable = sorted(page for page, state in reports if state == UNREACHABLE)
    if unreachable:
        raise NoAnswer(
            f"friction on {', '.join(unreachable)} cannot be judged: a point lies beyond this "
            f"shallow clone's history — fetch the full history (`git fetch --unshallow`)"
        )
    unjudged = sorted(
        (page, state)
        for page, state in reports
        if state not in JUDGED and not _only_by_kind(page, state, kinds)
    )
    if unjudged:
        named = ", ".join(f"{page} ({state})" for page, state in unjudged)
        raise NoAnswer(
            f"friction on {named} was not judged: an anchor's resolver gave no answer — run "
            f"again, then `pkit sync`, or mend the resolver — or the state is one this "
            f"capability does not know; `pkit friction explain <page>` says which"
        )
    unknown = sorted(
        {
            (finding.location, finding.kind)
            for finding in friction.findings
            if finding.location in page_set and finding.kind not in FINDING_KINDS
        }
    )
    if unknown:
        named = ", ".join(f"{page} ({kind})" for page, kind in unknown)
        raise NoAnswer(
            f"friction on {named} was not judged: the check reports a finding of a kind this "
            f"capability does not know, which may be owed; `pkit friction explain <page>` "
            f"says what it is"
        )
    stale = sorted(
        page
        for page, state in reports
        if state == STALE or (_only_by_kind(page, state, kinds) and STALE in kinds.get(page, set()))
    )
    return [
        *(_page_stale(page, friction.findings) for page in stale),
        *(_code_undocumented(path) for path in sorted(friction.uncovered)),
    ]


def unresolved_kinds(report: Mapping[str, Any], pages: Iterable[str]) -> list[tuple[str, str, str]]:
    """The anchors of a kind nothing installed resolves on the pages the check left
    unjudged only by them (`_only_by_kind`), as (page, kind, value), sorted: for the
    human view, which names each as a declaration to mend, not owed here."""
    friction = _friction(report)
    if friction.dormant:
        return []
    kinds = _kinds_by_location(friction.findings)
    page_set = set(pages)
    held = {
        page
        for page, state in friction.states
        if page in page_set and _only_by_kind(page, state, kinds)
    }
    return sorted(
        (finding.location, *finding.anchor)
        for finding in friction.findings
        if finding.kind == UNRESOLVED_KIND
        and finding.location in held
        and finding.anchor is not None
    )


def envelope(value: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The filler envelope the command prints (COR-052 point 6)."""
    return {"schema_version": POINT_VERSION, "value": list(value)}


def _kinds_by_location(findings: Iterable[_Finding]) -> dict[str | None, set[str]]:
    """The finding kinds the check reports at each location."""
    kinds: dict[str | None, set[str]] = {}
    for finding in findings:
        kinds.setdefault(finding.location, set()).add(finding.kind)
    return kinds


def _only_by_kind(page: str, state: str, kinds: Mapping[str | None, set[str]]) -> bool:
    """Whether the check left the page unjudged only because nothing installed
    resolves one of its anchors' kinds — a declaration for the project to mend —
    and not because an anchor's resolver gave no answer."""
    at = kinds.get(page, set())
    return state == UNRESOLVED and UNRESOLVED_KIND in at and NO_ANSWER not in at


def _page_stale(page: str, findings: Sequence[_Finding]) -> dict[str, Any]:
    details = [_detail(f) for f in findings if f.location == page]
    what = ", ".join(d for d in details if d)
    return {
        "id": f"{SOURCE}:{PAGE_STALE}:{page}",
        "source": SOURCE,
        "reason": PAGE_STALE,
        "document": page,
        "description": f"{STALE}{': ' + what if what else ''} — pkit friction explain {page}",
    }


def _detail(finding: _Finding) -> str:
    """One stale finding, as a few words: which anchor changed. A page's deferred
    findings are answered, so they are not what it owes."""
    if finding.kind != STALE:
        return ""
    if finding.anchor is None:
        return "moved with no revalidation"
    kind, value = finding.anchor
    return f"{kind} {value} changed"


def _code_undocumented(path: str) -> dict[str, Any]:
    return {
        "id": f"{SOURCE}:{CODE_UNDOCUMENTED}:{path}",
        "source": SOURCE,
        "reason": CODE_UNDOCUMENTED,
        "path": path,
        "description": f"{path} is in the declared surface and nothing anchors it — "
        f"anchor it from a page",
    }
