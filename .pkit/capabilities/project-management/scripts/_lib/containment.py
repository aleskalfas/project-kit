"""The sole constructor of the native sub-issue (containment) link write, AND
the one read seam that resolves a parent's children.

DEC-005 makes **GitHub's native sub-issues field** the canonical structural
mechanism for the hierarchy parent ↔ child edge: every parent-link mutation must
set the native link *in addition to* the textual first-line parent-ref. Until
now the codebase wrote only the textual child-side ref; this module supplies the
missing native write.

The read counterpart (the second half of this module)
--------------------------------------------------------
DEC-005's "native wins" rule is a *read*-time resolution as much as a write-time
one. Where this module's write half is the sole constructor of the native link,
its read half (:func:`resolve_children`) is the sole resolver of "what are this
parent's children?" — the union of its native sub-issues and the issues whose
child-side first line names it, **native-wins on conflict**. Both `show-tree` and the
DEC-034 closure-fold child-walk resolve through it, so no consumer re-derives
containment by parsing body parent-refs directly (ADR-026's one-read-seam
discipline, mirrored here for the containment axis: a second consumer must not
re-derive what one seam already resolves). Its upward counterpart,
:func:`resolve_parent`, answers "what is this issue's parent?" from one read of
the issue's record — the native parent it carries, held to the first line — for
the forward cascade, the closure cascade and the fold's membership step, and
through its pure half (:func:`compare_parents`) for `show-tree`. Both directions
read a first line through `body_parent_ref`, so the issue a line names is the
same either way. The formal contract for both halves
is ADR-035, the containment resolution contract (under
``tech-docs/architecture/decisions/``); this module's docstrings carry the
semantics it pins.

A *containment link* is a third non-label substrate, distinct from the two
``_lib/substrate_writes`` covers (the Projects-v2 field-value and the milestone
assignment): it establishes the native parent ↔ child edge that surfaces a child
in the parent's sub-issues panel and feeds the Projects-v2 "Sub-issues progress"
field (DEC-005). Because it is a different operation (``gh api
repos/.../sub_issues`` rather than ``gh project item-edit`` / ``gh issue
…--milestone``), it lives in its own module with its own sole-constructor guard
(``tests/test_pm_containment_write_seam.py``) — the same discipline as ADR-031's
substrate-write seam, not a widening of that seam's covered set.

Sole-constructor discipline (ADR-031, applied to containment)
-------------------------------------------------------------
Every script that links a child under a parent obtains the ``gh`` write **only
by asking this module** — it never string-builds the ``gh api …/sub_issues``
argv itself. That makes "no script string-builds the sub-issue write inline" a
structural property the guard enforces, the direct analogue of the field-value /
milestone seam. ``create-issue`` and ``link-parent`` link through
:func:`link_sub_issue`; ``set-field --parent`` re-parents through
:func:`move_sub_issue`. Any further parent-link mutation (promote, …) reuses the
same construction point.

The API mechanism
-----------------
GitHub's REST endpoint ``POST /repos/{owner}/{repo}/issues/{parent}/sub_issues``
with body ``{"sub_issue_id": <child database id>}`` is the canonical add. The
``sub_issue_id`` is the child's **integer database id** (``gh api
repos/.../issues/<n> --jq .id``), NOT the issue number and NOT the GraphQL
node id (``gh issue view --json id`` returns the node id, which this endpoint
rejects). REST is chosen over the GraphQL ``addSubIssue`` mutation because it
needs only the integer id the same ``gh api`` round-trip already yields, with no
node-id resolution or query crafting. A move is the same add with
``replace_parent=true``: GitHub takes the child from its old parent and gives it
to the new one in one write, so there is no moment at which it has neither.

Idempotency (DEC-026, value-equality)
-------------------------------------
Linking an already-linked child is a no-op. Before adding, the linker reads the
child's own record — the read that resolves its database id also carries its
current native parent — and, when that names no parent, lists the parent's
current sub-issues (``GET …/sub_issues``); either showing the child already there
skips the write. A caller linking many children holds a :class:`SubIssueReads`
for the run, so each parent's list is read once however many of its children are
linked.

One native parent (#1040)
-------------------------
An issue has at most one native parent. A child already under a *different*
parent is a **conflict**: :func:`link_sub_issue` reports it
(:attr:`LinkOutcome.CONFLICT`, naming the parent the child has) and does not
post. It is reported on evidence of exactly that and nothing else — before the
add, the child's record naming another parent; after it, GitHub's refusal
stating the one-parent rule, or, on a plain link GitHub refused for a reason pm
does not recognise, a re-read of the child's record naming another parent. On a
move (:func:`move_sub_issue`) the child's existing parent is the precondition,
not a finding, so a move refused for any reason but the one-parent rule is a
failure rather than a conflict with a remedy the refusal never asked for.

A 422 is never read as an absent feature (#808, ADR-035)
--------------------------------------------------------
HTTP 422 is GitHub refusing a request it could not process, and the sub-issues
endpoint answers it on instances where sub-issues work: for a child that
already has a parent (above), or for a malformed ``sub_issue_id``. So a 422 is
never ``unsupported`` — not on its status, and not on any wording. GitHub's
message is read only to tell one refusal from another (the one-parent rule is
the conflict it states, a duplicate is a link already in place, a rejected id
is a defect in pm's request), and it reaches the operator as written
(:attr:`LinkResult.said`). Any other 422 is a **failure** carrying those words.
An adopter whose GitHub offers no sub-issues, where the seam cannot establish
that by attribution (below), declares it with the ``containment: textual``
write selector; it is never inferred from a message.

Graceful degradation (the textual ref is the fallback)
------------------------------------------------------
Where the instance does not support sub-issues — an older GHES, the feature
turned off — and the seam establishes it (a 410, or a 404 the parent-issue
probe attributes to the endpoint: :func:`_classify_native_failure`), the native
write degrades to a **no-op**: the link result reports ``unsupported`` and the
caller carries on. The textual first-line parent-ref (written unchanged by
``create-issue``) carries the relationship in that case. A native write never
fails the create.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from _lib import body_parent_ref

# Sibling module — the gh shell-out helper that pins the adopter's host/owner
# (DEC-023). Imported the same way `_lib.substrate_writes` does, with a defensive
# fallback for unusual import contexts (tests that load a module by file path may
# not have _lib on sys.path).
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]


class LinkOutcome(Enum):
    """The outcome class of one native sub-issue link attempt.

    LINKED       — the native link was created this call.
    MOVED        — the child was a native sub-issue of another parent and was
                   moved under this one this call (:func:`move_sub_issue` only).
    ALREADY       — the child was already a sub-issue of the parent (idempotent
                    no-op, value-equality per DEC-026).
    CONFLICT     — the child is a native sub-issue of a DIFFERENT parent, as its
                   record or GitHub's one-parent refusal says. An issue has one
                   native parent, so the link was not made; the result names the
                   parent the child has where that could be established. Not
                   "unsupported": the instance has sub-issues, this child is
                   spoken for.
    UNSUPPORTED  — the instance does not support sub-issues, established by a
                   410 or by a 404 attributed to the endpoint rather than to an
                   unseeable repository (`_classify_native_failure`) — never by a
                   422, whatever it says. The textual ref is the fallback. NOT a
                   failure.
    FAILED       — the write was attempted and failed for a reason that is NOT
                    "unsupported" (auth, network, missing `gh`, or a 422 that is
                    neither a link already in place nor a conflict — a malformed
                    request, or a refusal pm does not recognise). A genuine
                    problem to report rather than silently swallow; a refusal's
                    own words ride in `LinkResult.said`.
    """

    LINKED = "linked"
    MOVED = "moved"
    ALREADY = "already"
    CONFLICT = "conflict"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


@dataclass(frozen=True)
class NativeParent:
    """The issue a child is natively a sub-issue of, as the child's record says.

    ``repository`` is ``owner/repo`` when the parent lives in another repository
    (native sub-issues may cross repositories) and ``None`` when it is this one,
    so a parent elsewhere is never mistaken for the same-numbered issue here.
    """

    number: int
    repository: str | None = None

    @property
    def ref(self) -> str:
        """How a report names the parent: ``#979``, or ``owner/repo#979``."""
        return f"{self.repository}#{self.number}" if self.repository else f"#{self.number}"

    def is_issue(self, number: int | str) -> bool:
        """True when this parent is issue ``number`` of this repository."""
        return self.repository is None and self.number == int(number)


# An owner and a repository name as the hosting service spells them: ASCII
# letters, digits, `-`, `_` and `.`. A name is read into a request's path, where
# any other text could address something else — a space, a `#`, a `/`, or `..`,
# a step out of the path — so text outside this alphabet names no repository,
# and what carries it is unreadable (`is_repository_name`).
_NAME = r"[A-Za-z0-9_.-]+"
_REPOSITORY_NAME = re.compile(rf"{_NAME}/{_NAME}")
_FOREIGN_REF = re.compile(rf"(?P<repo>{_NAME}/{_NAME})#(?P<number>[0-9]+)")


def is_repository_name(text: str) -> bool:
    """Whether ``text`` is ``owner/repo`` in the hosting service's alphabet,
    neither name made of dots alone nor carrying ``..``."""
    if _REPOSITORY_NAME.fullmatch(text) is None:
        return False
    return all(name.strip(".") and ".." not in name for name in text.split("/"))


@dataclass(frozen=True, order=True)
class ForeignIssue:
    """An issue in another repository: ``owner/repo`` and its number there.

    A native sub-issue may live in another repository. It is identified by
    both, so it is never taken for this repository's issue of the same number.
    """

    repository: str
    number: int

    @property
    def ref(self) -> str:
        """How it is named: ``owner/repo#42``."""
        return f"{self.repository}#{self.number}"

    @classmethod
    def parse(cls, text: str) -> ForeignIssue | None:
        """The issue ``owner/repo#42`` names, or ``None`` for any other text —
        the inverse of :attr:`ref`. A repository name outside the hosting
        service's alphabet (:func:`is_repository_name`) names none."""
        m = _FOREIGN_REF.fullmatch(text.strip())
        if m is None or not is_repository_name(m.group("repo")):
            return None
        return cls(m.group("repo"), int(m.group("number")))


@dataclass(frozen=True)
class IssueLinkState:
    """What linking a child needs to know about it, from one read of its record.

    ``database_id`` is the id the sub-issues endpoint takes; ``parent`` is the
    child's current native parent, ``None`` when it has none (or when the
    instance's issue record does not carry the field).
    """

    database_id: int
    parent: NativeParent | None


# Who a refusal's words belong to. GitHub's error body is GitHub's sentence;
# when the body carries none, the words are gh's own summary line — which may
# relay GitHub's message, but is gh's line, and is attributed as such.
SPEAKER_GITHUB = "GitHub"
SPEAKER_GH = "gh"


@dataclass(frozen=True)
class Said:
    """What a refused sub-issues call said, and who said it.

    Quoted to the operator as written (whitespace folded onto one line), never
    reworded and never read into a verdict about the instance: a refusal's words
    may tell one refusal from another, but they do not grant ``unsupported``
    (ADR-035). ``speaker`` is :data:`SPEAKER_GITHUB` for GitHub's error body and
    :data:`SPEAKER_GH` for gh's stderr when the body carried no words.
    """

    words: str
    speaker: str = SPEAKER_GITHUB

    def quoted(self) -> str:
        """``GitHub said: "…"`` — or ``gh said: "…"`` for gh's own line."""
        return f'{self.speaker} said: "{self.words}"'


@dataclass(frozen=True)
class LinkResult:
    """Outcome of one native sub-issue link attempt — a neutral carrier.

    Failure-posture-neutral in the same spirit as
    ``substrate_writes.SubstrateWriteResult`` (ADR-031 point 6): it records what
    happened; the caller decides what to do. ``create-issue`` treats every
    outcome as non-fatal (the textual ref is the spine) but reports a one-line
    note keyed on ``outcome``.

    Fields:
      outcome        — the :class:`LinkOutcome`.
      detail         — a one-line human-readable summary for the caller to print.
      current_parent — for CONFLICT, the parent the child is natively under
                       (``None`` when GitHub refused on the one-parent rule but
                       the child's record could not name the parent); for MOVED,
                       the parent it was moved from. ``None`` otherwise.
      said           — what GitHub's refusal of the add said (:class:`Said`),
                       when the outcome came from a refused 422: the error body's
                       messages, or ``gh``'s stderr when the body carried none.
                       ``detail`` already quotes it; a caller that writes its own
                       report line appends it (:meth:`quoting_refusal`), so the
                       operator reads what was said and not only pm's reading of
                       it. ``None`` when there was no such refusal.

    The seam reports only what it did to the native link. What became of the
    textual first line is the caller's to say — ``create-issue`` wrote it,
    ``link-parent`` found it, ``set-field`` rewrites it only once this allows.
    """

    outcome: LinkOutcome
    detail: str = ""
    current_parent: NativeParent | None = None
    said: Said | None = None

    @property
    def ok(self) -> bool:
        """True when the relationship is in place after this call (linked,
        moved, or already-linked). CONFLICT, UNSUPPORTED and FAILED are not
        ``ok`` — the native link to this parent is absent — but only FAILED is a
        genuine error (UNSUPPORTED is expected on instances without the feature;
        CONFLICT is a disagreement for the caller to report)."""
        return self.outcome in (LinkOutcome.LINKED, LinkOutcome.MOVED, LinkOutcome.ALREADY)

    @property
    def refused(self) -> bool:
        """True when GitHub refused the add (a 422) and the refusal was neither a
        link already in place nor a conflict: FAILED, with the refusal's words
        in ``said``. The one case a write caller follows with the textual-mode way
        out (``axis_labels.TEXTUAL_CONTAINMENT_WAY_OUT``) — the seam never reads
        a refusal as an instance without sub-issues, so the operator who knows
        theirs has none is told how to say so."""
        return self.outcome is LinkOutcome.FAILED and self.said is not None

    def quoting_refusal(self, sentence: str) -> str:
        """``sentence`` followed by what the refusal said, when it said anything
        — for a caller that reports the outcome in its own sentence instead of
        ``detail``, so the refusal's words still reach the operator."""
        return _quoting(sentence, self.said)


# HTTP statuses that mean "this instance does not support sub-issues" by status
# alone — degrade to a no-op rather than a failure. Only 410: an invisible
# repository never produces it, so it needs no probe (ADR-035; what a 410
# establishes on a write is tracked in #1247). No other status does the same, and 422 in
# particular is never here — GitHub answers it for a request it refused on an
# instance where sub-issues work (#808), so it says nothing about the substrate,
# on its status or in its words (ADR-035).
_UNSUPPORTED_STATUSES = (410,)

# The 422 refusal status, read off the error body's `status` or gh's stderr. It
# says only that GitHub refused the request — which refusal is in its words —
# and is never evidence about the instance.
_UNPROCESSABLE_STATUS = 422

# 404 is the ambiguous one, and no amount of stderr parsing resolves it: GitHub
# answers 404 both for "this endpoint does not exist here" and for "you may not
# know this repository exists". Same status, same message, opposite meanings for
# a close gate. `_classify_native_failure` settles it by probing instead.
_AMBIGUOUS_STATUS = 404


def add_sub_issue_args(
    *,
    parent_number: int | str,
    child_database_id: int | str,
    replace_parent: bool = False,
) -> list[str]:
    """Construct the ``gh api …/sub_issues`` add argv.

    The sole constructor of the native sub-issue link write. Callers obtain this
    argv only here; they never string-build ``gh api repos/.../sub_issues``
    themselves (the containment-seam guard enforces it).

    ``child_database_id`` is the child's **integer database id** (not its number,
    not its node id). ``-X POST -F sub_issue_id=<id>`` posts the documented body.
    The ``-F`` (typed field) form is REQUIRED, not ``-f``: the endpoint validates
    ``sub_issue_id`` as a JSON *integer* and rejects the string ``-f`` would send
    with ``HTTP 422 … is not of type integer``. The ``{owner}/{repo}``
    placeholders are resolved by ``gh`` against the current repo (host/owner
    pinned via the gh helper per DEC-023).

    ``replace_parent`` adds ``-F replace_parent=true`` (a typed boolean), which
    makes the add a MOVE: GitHub takes the child from its current parent in the
    same write. Only :func:`move_sub_issue` asks for it — a plain link never
    takes a child from another parent.
    """
    args = [
        "gh",
        "api",
        "-X",
        "POST",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/sub_issues",
        "-F",
        f"sub_issue_id={child_database_id}",
    ]
    if replace_parent:
        args += ["-F", "replace_parent=true"]
    return args


def list_sub_issues_args(*, parent_number: int | str) -> list[str]:
    """Construct the ``gh api …/sub_issues`` list (GET) argv.

    Used for the value-equality idempotency read before an add — list the
    parent's current sub-issues and skip the add when the child is already among
    them. Paginated so a parent with many children is read in full.
    """
    return [
        "gh",
        "api",
        "--paginate",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/sub_issues",
    ]


# The child's record answers both questions linking asks of it: its database id
# and its current native parent. GitHub's REST issue carries the parent as
# `parent_issue_url` and omits it when there is none; `repository_url` is read
# beside it so a parent in another repository is told apart from the
# same-numbered issue here. One value per line, the id first.
_LINK_STATE_JQ = '.id, (.parent_issue_url // ""), .repository_url'
_ISSUE_URL = re.compile(r"/repos/(?P<repo>[^/]+/[^/]+)/issues/(?P<number>\d+)/?$")
_REPOSITORY_URL = re.compile(rf"/repos/(?P<repo>{_NAME}/{_NAME})/?\Z")


def _url_repository(url: str) -> str | None:
    """The ``owner/repo`` a ``repository_url`` names, or ``None`` where it names
    none the hosting service could have spelled (:func:`is_repository_name`)."""
    m = _REPOSITORY_URL.search(url)
    return m.group("repo") if m is not None and is_repository_name(m.group("repo")) else None


def read_link_state(config: dict[str, Any], *, issue_number: int | str) -> IssueLinkState | None:
    """Read a child's database id and its current native parent in one call.

    The sub-issues endpoint keys on the integer DATABASE id, not the number and
    not the GraphQL node id (``gh issue view --json id`` returns the node id,
    which the endpoint rejects). ``gh api repos/{owner}/{repo}/issues/<n>`` —
    the read that resolves that id — also carries the child's native parent, so
    knowing the parent before an add costs no extra call. ``None`` on any
    failure (missing ``gh``, non-zero exit, non-integer id); callers degrade.

    An instance whose issue record lacks the parent field reads as "no parent".
    That never produces a wrong link: the add is then refused on the one-parent
    rule, and :func:`link_sub_issue` reads the refusal (see the module
    docstring).
    """
    try:
        proc = _gh_call(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/issues/{issue_number}",
                "--jq",
                _LINK_STATE_JQ,
            ],
            config,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    lines = (proc.stdout or "").split("\n")
    try:
        database_id = int(lines[0].strip())
    except (TypeError, ValueError):
        return None
    parent_url = lines[1].strip() if len(lines) > 1 else ""
    repository_url = lines[2].strip() if len(lines) > 2 else ""
    return IssueLinkState(
        database_id=database_id,
        parent=_parse_native_parent(parent_url, repository_url),
    )


@dataclass(frozen=True)
class IssueRecord:
    """An issue and its native parent, from one read of its record.

    ``issue`` holds the fields the pm scripts read off ``gh issue view --json``,
    in that shape: ``title``, ``body``, ``labels`` (``{"name": …}`` objects),
    ``state`` (``OPEN`` / ``CLOSED``) and ``milestone``. ``parent`` is the issue's
    native parent, ``None`` when it has none (or when the instance's issue record
    does not carry the field); its ``repository`` is relative to the issue's own.
    """

    issue: dict[str, Any]
    parent: NativeParent | None


@dataclass(frozen=True)
class UnreadIssue:
    """Why an issue's record could not be read.

    ``why`` is pm's reading of the failure; ``said`` is what ``gh`` printed for
    it (:class:`Said` — GitHub's error body, else gh's own stderr), quoted as
    written, ``None`` when it printed nothing.
    """

    why: str
    said: Said | None = None

    @property
    def detail(self) -> str:
        """``why``, followed by what was said, when anything was."""
        return _quoting(self.why, self.said)


def read_issue_record(
    config: dict[str, Any], *, issue_number: int | str, repository: str | None = None
) -> IssueRecord | UnreadIssue:
    """Read an issue and its native parent in one call.

    ``gh api repos/{owner}/{repo}/issues/<n>`` — the record
    :func:`read_link_state` reads a child's database id from — carries the
    issue's title, body, labels, state and milestone beside its
    ``parent_issue_url``. A walk up the hierarchy that compares an issue's
    textual parent with its native one therefore costs no second call per issue.

    ``repository`` (``owner/repo``) reads an issue in another repository — a
    native sub-issue that lives there (:class:`ForeignIssue`) — instead of this
    one. It is a read: nothing in this module writes to another repository.

    :class:`UnreadIssue` on any failure — missing ``gh``, a non-zero exit (with
    what gh said), output that is not an issue's record — for a pull request,
    which the endpoint also answers for, and for a record numbered other than
    ``issue_number``: GitHub redirects the read of an issue transferred to
    another repository, and gh follows the redirect to an issue that is not the
    one asked for. A ``repository`` outside the hosting service's alphabet
    (:func:`is_repository_name`) is unread, and no request is made for it.
    """
    if repository is not None and not is_repository_name(repository):
        return UnreadIssue(f"{repository!r} is not a repository name")
    name = f"{repository}#{issue_number}" if repository else f"#{issue_number}"
    where = repository or "{owner}/{repo}"
    try:
        proc = _gh_call(["gh", "api", f"repos/{where}/issues/{issue_number}"], config)
    except FileNotFoundError:
        return UnreadIssue("`gh` is not on PATH")
    if proc.returncode != 0:
        said = _Refusal.read(proc.stdout or "", proc.stderr or "").said
        return UnreadIssue(f"gh exited {proc.returncode}", said)
    try:
        record = json.loads(proc.stdout or "")
    except (json.JSONDecodeError, ValueError):
        return UnreadIssue("gh's answer was not JSON")
    if not isinstance(record, dict):
        return UnreadIssue("gh's answer was not an issue's record")
    if "pull_request" in record:
        return UnreadIssue(f"{name} is a pull request")
    number = record.get("number")
    if not isinstance(number, int) or isinstance(number, bool):
        return UnreadIssue("gh's answer was not an issue's record")
    if number != int(issue_number):
        return UnreadIssue(
            f"the record gh returned is #{number}'s, not {name}'s "
            "(an issue transferred elsewhere, whose read was redirected)"
        )
    labels = [
        {"name": str(label.get("name", "")) if isinstance(label, dict) else str(label)}
        for label in record.get("labels") or []
    ]
    issue = {
        "title": str(record.get("title") or ""),
        "body": str(record.get("body") or ""),
        "labels": labels,
        "state": str(record.get("state") or "").upper(),
        "milestone": record.get("milestone"),
    }
    parent = _parse_native_parent(
        str(record.get("parent_issue_url") or ""), str(record.get("repository_url") or "")
    )
    return IssueRecord(issue=issue, parent=parent)


def _parse_native_parent(parent_url: str, repository_url: str) -> NativeParent | None:
    """The parent a ``parent_issue_url`` names, relative to the child's repository.

    A parent URL whose repository cannot be compared with the child's (no
    ``repository_url``) is kept as foreign: calling it "this repository's #N"
    on no evidence could turn a conflict into a false "already linked".
    """
    m = _ISSUE_URL.search(parent_url)
    if not m:
        return None
    here = _url_repository(repository_url)
    same = here is not None and here.lower() == m.group("repo").lower()
    return NativeParent(
        number=int(m.group("number")),
        repository=None if same else m.group("repo"),
    )


def link_sub_issue(
    config: dict[str, Any],
    *,
    parent_number: int | str,
    child_number: int | str,
    sub_issues: SubIssueReads | None = None,
) -> LinkResult:
    """Link the child issue under the parent via GitHub's native sub-issues API.

    The one place the native containment link is established (ADR-031
    sole-constructor discipline applied to containment). Composes these steps,
    all through the gh helper (DEC-023 host/owner pinning):

      1. read the child's record — its integer database id (the id the endpoint
         needs) and its current native parent (:func:`read_link_state`);
      2. a child already under this parent is :attr:`LinkOutcome.ALREADY`; one
         under a DIFFERENT parent is :attr:`LinkOutcome.CONFLICT`, and nothing
         is posted — an issue has one native parent;
      3. otherwise read the parent's current sub-issues and short-circuit to
         ALREADY when the child is among them (value-equality idempotency per
         DEC-026). ``sub_issues`` is the caller's per-run snapshot when it links
         many children; without one the parent is read fresh;
      4. POST the add; on a refusal, read what GitHub's error body says about
         the child's parent, then ask the one classification point
         (:func:`_classify_native_failure`) whether the instance lacks the
         feature.

    Never raises and never returns a fatal posture for an *unsupported* instance:
    a 410, or a 404 attributed to the endpoint, yields
    :attr:`LinkOutcome.UNSUPPORTED` so the caller carries the textual ref as the
    fallback. A 422 is never that, whatever it says: one stating the one-parent
    rule is the CONFLICT it states, as is any other 422 after which the child's
    record names another parent; one refusing a duplicate is ALREADY. A genuine
    error (auth / network / missing ``gh``, an unresolvable child id, a
    malformed request, or a 422 pm does not recognise) yields
    :attr:`LinkOutcome.FAILED` for the caller to report — still non-fatal to
    the create, which already wrote the textual ref. A refused 422's own words
    ride in :attr:`LinkResult.said`.
    """
    return _attach(
        config,
        parent_number=parent_number,
        child_number=child_number,
        move=False,
        sub_issues=sub_issues,
    )


def move_sub_issue(
    config: dict[str, Any],
    *,
    parent_number: int | str,
    child_number: int | str,
) -> LinkResult:
    """Put the child natively under the parent, moving it from any other parent.

    The re-parenting counterpart of :func:`link_sub_issue`, for a caller that
    has just been told which parent is meant (``set-field --parent``). Where the
    child is under another parent the add is posted with ``replace_parent``, so
    GitHub moves it in one write — :attr:`LinkOutcome.MOVED`, with the old parent
    in ``current_parent``. Otherwise it behaves as :func:`link_sub_issue`. A
    move GitHub refuses on the one-parent rule is :attr:`LinkOutcome.CONFLICT`,
    naming the parent the child stays under; a move refused for any other reason
    is :attr:`LinkOutcome.FAILED` with GitHub's words — the parent the child has
    is the precondition of a move, not a finding about it, so it is no evidence
    of a conflict.
    """
    return _attach(
        config,
        parent_number=parent_number,
        child_number=child_number,
        move=True,
        sub_issues=None,
    )


def _attach(
    config: dict[str, Any],
    *,
    parent_number: int | str,
    child_number: int | str,
    move: bool,
    sub_issues: SubIssueReads | None,
) -> LinkResult:
    """The shared body of :func:`link_sub_issue` and :func:`move_sub_issue`."""
    state = read_link_state(config, issue_number=child_number)
    if state is None:
        return LinkResult(
            LinkOutcome.FAILED,
            detail=(
                f"could not resolve issue #{child_number}'s database id for the "
                "native sub-issue link"
            ),
        )
    holder = state.parent
    if holder is not None and holder.is_issue(parent_number):
        return _already_linked(child_number, parent_number)
    if holder is not None and not move:
        return _conflict(child_number, parent_number, holder, move=False)

    if holder is None:
        # Idempotency read: already a sub-issue of this parent? value-equality skip.
        existing = (
            sub_issues.read(parent_number)
            if sub_issues is not None
            else read_native_children(config, parent_number=parent_number)
        )
        if existing.outcome is NativeReadOutcome.READ and int(child_number) in existing.numbers:
            return _already_linked(child_number, parent_number)

    # A move only when the child has a parent to be taken from; otherwise even a
    # move_sub_issue posts a plain add and is read as one.
    replacing = holder is not None
    args = add_sub_issue_args(
        parent_number=parent_number,
        child_database_id=state.database_id,
        replace_parent=replacing,
    )
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return LinkResult(
            LinkOutcome.FAILED,
            detail="`gh` not on PATH; native sub-issue link skipped",
        )
    if proc.returncode == 0:
        if replacing:
            return LinkResult(
                LinkOutcome.MOVED,
                detail=(
                    f"moved #{child_number} from {holder.ref} to #{parent_number} "
                    "as a native sub-issue"
                ),
                current_parent=holder,
            )
        return LinkResult(
            LinkOutcome.LINKED,
            detail=f"linked #{child_number} as a native sub-issue of #{parent_number}",
        )

    refusal = _Refusal.read(proc.stdout or "", proc.stderr or "")
    settled = _read_refusal(
        config,
        refusal,
        parent_number=parent_number,
        child_number=child_number,
        move=replacing,
    )
    if settled is not None:
        return settled
    stderr = (proc.stderr or "").strip()
    # The one definition of "unsupported" (ADR-035 point 3): a 410, or a 404 the
    # probe attributes to the endpoint. A 422 never reaches it, whatever it says.
    if (
        _classify_native_failure(
            config, parent_number=parent_number, stderr=stderr, stdout=proc.stdout or ""
        )
        is NativeReadOutcome.UNSUPPORTED
    ):
        return LinkResult(
            LinkOutcome.UNSUPPORTED,
            detail="native sub-issues unsupported on this instance",
        )
    if refusal.unprocessable:
        return _refused(
            refusal, child_number=child_number, parent_number=parent_number, move=replacing
        )
    return LinkResult(
        LinkOutcome.FAILED,
        detail=(
            f"native sub-issue link failed (gh exit {proc.returncode}). "
            f"stderr: {stderr or 'no stderr'}"
        ),
    )


def _already_linked(child_number: int | str, parent_number: int | str) -> LinkResult:
    return LinkResult(
        LinkOutcome.ALREADY,
        detail=f"#{child_number} is already a native sub-issue of #{parent_number} (no-op)",
    )


def _conflict(
    child_number: int | str,
    parent_number: int | str,
    holder: NativeParent | None,
    *,
    move: bool,
    said: Said | None = None,
) -> LinkResult:
    """The CONFLICT result, naming the child, the parent it has and the one asked
    for, and what has to happen first: the link the child has must go. ``said``
    is what GitHub's refusal said, when GitHub refused, quoted after pm's own
    sentence."""
    held = holder.ref if holder is not None else "another parent (its record does not say which)"
    link = f"its native link to {holder.ref}" if holder is not None else "its existing native link"
    if move:
        detail = (
            f"#{child_number} could not be moved to #{parent_number}: it stays a "
            f"native sub-issue of {held}; {link} must be removed first"
        )
    else:
        detail = (
            f"#{child_number} is already a native sub-issue of {held}, not "
            f"#{parent_number}; an issue has one native parent, so it was not linked "
            f"— {link} must be removed first"
        )
    return LinkResult(
        LinkOutcome.CONFLICT,
        detail=_quoting(detail, said),
        current_parent=holder,
        said=said,
    )


def _refused(
    refusal: _Refusal,
    *,
    child_number: int | str,
    parent_number: int | str,
    move: bool,
) -> LinkResult:
    """The FAILED result for a 422 that is neither a link already in place nor a
    conflict: pm's sentence for the cause it recognises, then the refusal's own
    words. It claims nothing about the instance — a 422 is never evidence that
    sub-issues are absent (ADR-035) — and nothing about the textual first line,
    which is the caller's to report."""
    if refusal.says(_MALFORMED_ID):
        cause = (
            f"GitHub rejected the sub_issue_id pm sent for #{child_number} as "
            "malformed: a defect in pm's request — report it against pm"
        )
    else:
        attempt = (
            f"move #{child_number} to #{parent_number}"
            if move
            else f"link #{child_number} under #{parent_number}"
        )
        cause = f"GitHub refused to {attempt} (HTTP 422) for a reason pm does not recognise"
    return LinkResult(
        LinkOutcome.FAILED,
        detail=_quoting(cause, refusal.said),
        said=refusal.said,
    )


def _quoting(detail: str, said: Said | None) -> str:
    """``detail`` followed by the refusal's own words, when it said any."""
    return f"{detail}. {said.quoted()}" if said is not None else detail


# What GitHub's refusal of an add says, read from the error body `gh api` prints
# on stdout — its stderr carries only a summary line, which names the first
# error's message OR the status, not reliably both. Each pattern is matched on
# the rule a message states rather than on the exact sentence:
#
# * an issue has one native parent: adding a child that has another is refused
#   with a 422 stating that rule ("Sub issue may only have one parent");
# * adding a child this parent already holds is refused as a duplicate;
# * the endpoint types `sub_issue_id` as a JSON integer and refuses anything
#   else with a 422 saying so ("… is not of type integer") — see
#   `add_sub_issue_args`.
#
# These tell one refusal from another and nothing more. No pattern here — or
# anywhere — reads a message as "this instance has no sub-issues": that verdict
# is the seam's one fail-open answer, and it is established by attribution
# (`_classify_native_failure`), never matched out of a guess at GitHub's
# phrasing (ADR-035, #808). Whatever a refusal says, its words reach the
# operator as written.
_ONE_PARENT = re.compile(r"\bone parent\b", re.IGNORECASE)
_DUPLICATE = re.compile(r"\bduplicate sub-?issues?\b", re.IGNORECASE)
_MALFORMED_ID = re.compile(r"\bnot\s+(?:of\s+type\s+[\"']?|an?\s+)integer\b", re.IGNORECASE)


@dataclass(frozen=True)
class _Refusal:
    """What ``gh api`` printed for a refused sub-issues call, read once.

    ``gh api`` prints GitHub's JSON error body on stdout and a one-line summary
    of its own on stderr. The body may be absent or not JSON, and its text may
    sit in ``message``, in ``errors[]`` (an object's ``message``, its ``field``
    and ``code`` alone, or a bare string), or in both — so every field is read
    defensively.

    Fields:
      messages      — every message the refusal carries: the body's
                      ``message``, each ``errors`` entry, then gh's stderr
                      lines. The patterns above are matched against these.
      said          — the words for the operator (:class:`Said`): GitHub's
                      body messages, or — attributed to gh — gh's stderr when
                      the body carried none; whitespace is folded so the words
                      fit a one-line report, never reworded. ``None`` when there
                      were no words at all.
      unprocessable — the refusal was a 422, by the body's ``status`` or gh's
                      stderr.
      stderr        — gh's stderr as printed, for the status checks.
    """

    messages: tuple[str, ...]
    said: Said | None
    unprocessable: bool
    stderr: str

    @classmethod
    def read(cls, stdout: str, stderr: str) -> _Refusal:
        body = _error_body(stdout)
        from_body: list[str] = []
        if body is not None:
            if isinstance(body.get("message"), str):
                from_body.append(body["message"])
            errors = body.get("errors")
            for error in errors if isinstance(errors, list) else []:
                entry = _error_entry_words(error)
                if entry is not None:
                    from_body.append(entry)
        from_body = [message for message in from_body if message.strip()]
        from_stderr = [line for line in stderr.splitlines() if line.strip()]
        speaker = SPEAKER_GITHUB if from_body else SPEAKER_GH
        words = "; ".join(" ".join(word.split()) for word in from_body or from_stderr)
        status = str(body.get("status", "")) if body is not None else ""
        return cls(
            messages=tuple(from_body + from_stderr),
            said=Said(words, speaker) if words else None,
            unprocessable=(
                status == str(_UNPROCESSABLE_STATUS)
                or _mentions_status(stderr, _UNPROCESSABLE_STATUS)
            ),
            stderr=stderr,
        )

    def says(self, pattern: re.Pattern[str]) -> bool:
        """True when any of the refusal's messages states what ``pattern`` matches."""
        return any(pattern.search(message) for message in self.messages)


def _error_entry_words(error: object) -> str | None:
    """One ``errors[]`` entry of GitHub's error body, as words.

    Its ``message``, or a bare string; an entry that carries only GitHub's
    validation ``code`` is rendered ``field: code`` (``code`` alone when it names
    no field), so a "Validation Failed" never reaches the operator stripped of
    the one entry that says what failed. ``None`` for an entry with no words.
    """
    if isinstance(error, str):
        return error
    if not isinstance(error, dict):
        return None
    message = error.get("message")
    if isinstance(message, str) and message.strip():
        return message
    code = error.get("code")
    if not isinstance(code, str) or not code.strip():
        return None
    field = error.get("field")
    return f"{field}: {code}" if isinstance(field, str) and field.strip() else code


def _read_refusal(
    config: dict[str, Any],
    refusal: _Refusal,
    *,
    parent_number: int | str,
    child_number: int | str,
    move: bool,
) -> LinkResult | None:
    """What a refused add says about the child's parent — ``None`` when nothing.

    A duplicate means the child is already here (ALREADY). The one-parent rule
    sends the seam back to the child's record, on a link or a move: a child now
    under this parent is ALREADY (someone linked it meanwhile), one under
    another parent is a CONFLICT naming that parent, and a one-parent refusal
    whose parent the record cannot name is still a CONFLICT — GitHub stated it.

    A 422 whose words pm does not recognise earns that second look only on a
    plain link (``move`` False): there, a child the re-read finds under another
    parent is the conflict, established by its record rather than by wording.
    On a move the child having another parent is the precondition, not a
    finding, so an unrecognised refusal is no evidence of a conflict. A 422 that
    names its own cause (a malformed id) says nothing about the parent. Each of
    those is left, like anything else, to :func:`_attach`, which reports it as
    the failure it is, with GitHub's words.
    """
    if refusal.says(_DUPLICATE):
        return _already_linked(child_number, parent_number)
    one_parent = refusal.says(_ONE_PARENT)
    if not one_parent and (move or not refusal.unprocessable or refusal.says(_MALFORMED_ID)):
        return None
    now = read_link_state(config, issue_number=child_number)
    holder = now.parent if now is not None else None
    if holder is not None and holder.is_issue(parent_number):
        return _already_linked(child_number, parent_number)
    if holder is not None or one_parent:
        return _conflict(child_number, parent_number, holder, move=move, said=refusal.said)
    return None


def _error_body(stdout: str) -> dict[str, Any] | None:
    """The JSON error body ``gh api`` prints on stdout for a refused request."""
    try:
        body = json.loads(stdout)
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _mentions_status(stderr: str, status: int) -> bool:
    """True when gh's stderr carries ``status`` in either of its phrasings."""
    lowered = stderr.lower()
    return f"http {status}" in lowered or f"({status})" in lowered


def _is_unsupported(stderr: str) -> bool:
    """True when ``gh``'s stderr carries the one status that settles absence alone.

    Only a **410** does: an invisible repository never produces it, so the
    unseeable repository is already ruled out (ADR-035). **404 is
    deliberately excluded**: GitHub returns it both for a missing endpoint and
    for a repository the caller may not see, so reading it as "unsupported"
    hands a close gate a determinate answer on no evidence whenever a token
    lacks scope (#869). **422 is never here, and no message is read**: GitHub
    answers 422 for a request it refused on an instance where sub-issues work,
    so neither its status nor its words say the substrate is absent (#808,
    ADR-035). Use :func:`_classify_native_failure`, which probes rather than
    guesses; this predicate answers only the part the status can decide.
    """
    return any(_mentions_status(stderr, status) for status in _UNSUPPORTED_STATUSES)


def _mentions_ambiguous_status(stderr: str) -> bool:
    """True when stderr carries a 404, or gh's bare code-less phrasing of one."""
    if _mentions_status(stderr, _AMBIGUOUS_STATUS):
        return True
    # `gh` sometimes phrases a missing endpoint as "Not Found" without the code.
    return "not found" in stderr.lower()


def _classify_native_failure(
    config: dict[str, Any], *, parent_number: int | str, stderr: str, stdout: str = ""
) -> NativeReadOutcome:
    """Why a native sub-issues call failed — asked of the API, not of the text.

    The one call both the read and the write path route through, so they cannot
    drift into different notions of "unsupported" — ADR-026's one-reader
    discipline applied to failure attribution, and ADR-035 §3 on why the two
    directions must not each hold their own definition of the same fact.

    UNSUPPORTED is reached two ways and no other: a 410 (:func:`_is_unsupported`),
    or a 404 the probe below attributes to the endpoint. A **422** is always
    UNREADABLE, whatever its message says: GitHub refused a request, on an
    instance where sub-issues may well work, and its words are not evidence
    about the substrate (#808, ADR-035). Nor is it probed — a visible parent
    would change nothing about a refusal. ``stdout`` is the error body ``gh
    api`` printed, read here only so a 422 named by the body alone is still
    recognised as one.

    A 404 on `…/sub_issues` is genuinely ambiguous, so it is settled by probing
    the parent issue itself — the same `gh api repos/{owner}/{repo}/issues/<n>`
    endpoint :func:`read_link_state` reads a child from:

    * the probe succeeds — repository, credentials and parent are all visible, so
      a 404 on the *sub-resource* really is an absent endpoint -> UNSUPPORTED
    * the probe fails — a repository, credential or visibility fault, and a
      native child set may exist unseen -> UNREADABLE
    * the probe cannot run at all -> UNREADABLE, the fail-closed default

    One extra call, only on the failure path, once per parent resolved. That is
    negligible against a gate that would otherwise answer confidently on no
    evidence — and the cost is paid only when something is already wrong.
    """
    if _is_unsupported(stderr):
        return NativeReadOutcome.UNSUPPORTED
    if _Refusal.read(stdout, stderr).unprocessable or not _mentions_ambiguous_status(stderr):
        return NativeReadOutcome.UNREADABLE
    try:
        probe = _gh_call(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/issues/{parent_number}",
                "--jq",
                ".number",
            ],
            config,
        )
    except FileNotFoundError:
        return NativeReadOutcome.UNREADABLE
    if probe.returncode != 0:
        return NativeReadOutcome.UNREADABLE
    return NativeReadOutcome.UNSUPPORTED


def _parse_concatenated_arrays(text: str) -> list | None:
    """Parse ``gh --paginate`` output, which may concatenate JSON arrays.

    Mirrors ``_lib.milestone._parse_concatenated_arrays``. Returns the merged
    list, or ``None`` when nothing parses (so the caller can distinguish an empty
    list — a parent with no sub-issues — from an unreadable payload). An empty
    input is an empty list (a successful read of an empty page).
    """
    if not text:
        return []
    decoder = json.JSONDecoder()
    out: list = []
    idx = 0
    parsed_any = False
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except ValueError:
            break
        parsed_any = True
        if isinstance(obj, list):
            out.extend(obj)
        idx = end
    return out if parsed_any else None


def _gh_call(args: list[str], config: dict[str, Any]) -> subprocess.CompletedProcess:
    """Call ``gh`` through the helper. Direct subprocess fallback if helper missing.

    Mirrors ``_lib.substrate_writes._gh_call`` so the containment write keeps the
    same execution path (adopter host/owner pinned per DEC-023) as the other
    non-label substrate writes.
    """
    if gh_run is not None:
        return gh_run(args, config, check=False)
    return subprocess.run(args, capture_output=True, text=True, check=False)


# =========================================================================
# Read seam — resolve a parent's children (native and first-line children
# together, native-wins). The counterpart to the write half above.
# =========================================================================


class ChildSubstrate(Enum):
    """Which substrate a resolved child came from (DEC-005's two mechanisms).

    NATIVE   — a GitHub native sub-issue of the parent (the canonical mechanism).
    TEXTUAL  — discovered only via the child's body first-line parent-ref (the
               projection); present in the corpus but NOT a native sub-issue.

    On conflict (a child present BOTH natively and textually) the child resolves
    to NATIVE — "native wins" (DEC-005). The substrate is surfaced so a consumer
    can render or reason about provenance; the child set itself is the union with
    native-wins dedup.
    """

    NATIVE = "native"
    TEXTUAL = "textual"


@dataclass(frozen=True)
class ResolvedChild:
    """One child of a parent, with the substrate it was resolved from.

    ``number`` is the child issue number (the methodology's stable key, shared by
    both substrates — the native sub-issues payload carries ``number`` and the
    textual parent-ref names ``#<number>``). Dedup across the two substrates is by
    ``number`` within this repository; ``substrate`` records who won (NATIVE on
    conflict per DEC-005).

    ``repository`` is ``owner/repo`` for a native sub-issue that lives in another
    repository, ``None`` for a child in this one. A child elsewhere is NATIVE (no
    first line here can name it) and is a different issue from this repository's
    issue of the same number: :attr:`ref` names it with its repository.
    """

    number: int
    substrate: ChildSubstrate
    repository: str | None = None

    @property
    def ref(self) -> str:
        """How a report names the child: ``#11``, or ``owner/repo#42``."""
        return f"{self.repository}#{self.number}" if self.repository else f"#{self.number}"


@dataclass(frozen=True)
class ChildResolution:
    """The resolved child set for one parent, plus how it was resolved.

    Fields:
      children          — the resolved children, deduped across substrates with
                          native-wins: this repository's sorted by number, then
                          native sub-issues in other repositories, sorted by
                          repository and number.
      native_supported  — False only when the seam established that the
                          instance has **no native substrate** (a 410, or an
                          attributed 404 — never a 422); the result is then
                          textual-only, and that is a COMPLETE answer. True
                          otherwise — including when the read failed, which is
                          reported through ``complete`` rather than by
                          pretending the substrate is absent.
      complete          — False when the seam cannot vouch for the child set: an
                          unreadable native read, or a corpus that was not
                          enumerated to exhaustion (or supplied without a
                          completeness claim). A gating consumer must check this:
                          an incomplete answer is not a smaller child set, it is
                          no answer.
      incomplete_reason — why, in operator-facing words, with what the failed
                          native read said quoted after it; None when complete.

    Convenience accessors keep call sites terse and stop each consumer from
    re-deriving the same projections off ``children``.
    """

    children: tuple[ResolvedChild, ...]
    native_supported: bool
    complete: bool = True
    incomplete_reason: str | None = None

    @property
    def numbers(self) -> list[int]:
        """The numbers of the children in this repository (union, native-wins
        dedup), sorted — never a child in another repository (:attr:`foreign`)."""
        return [c.number for c in self.children if c.repository is None]

    @property
    def native_numbers(self) -> list[int]:
        """This repository's child numbers that resolved from the NATIVE
        substrate, sorted."""
        return sorted(
            c.number
            for c in self.children
            if c.substrate is ChildSubstrate.NATIVE and c.repository is None
        )

    @property
    def textual_numbers(self) -> list[int]:
        """Child numbers that resolved from the TEXTUAL substrate only, sorted."""
        return sorted(c.number for c in self.children if c.substrate is ChildSubstrate.TEXTUAL)

    @property
    def foreign(self) -> tuple[ResolvedChild, ...]:
        """The native sub-issues that live in another repository."""
        return tuple(c for c in self.children if c.repository is not None)


class NativeReadOutcome(Enum):
    """How the native sub-issues read went — three outcomes, not two.

    ``UNSUPPORTED`` and ``UNREADABLE`` both yield no child set, but they mean
    opposite things for completeness and must not be collapsed (ADR-035 §5):

    * ``READ`` — the endpoint answered. The set is authoritative, empty included.
    * ``UNSUPPORTED`` — this instance has no native substrate at all, so the
      textual projection genuinely IS the whole answer, and degrading to it is a
      *determinate* result. Reached two ways and no other: a 410, or a 404 the
      probe attributes to the endpoint. No other status reaches it and no
      wording does — a 422 is UNREADABLE whatever it says (#808). It is the
      seam's only fail-open surface, so it has to be earned rather than
      inferred (#869).
    * ``UNREADABLE`` — auth, network, a transient 5xx, a 422 GitHub answered
      with, an unparseable payload, or no ``gh`` on PATH: a native child set may
      exist and was not seen. Absence of the tool is not evidence about the
      instance. Degrading here would silently drop natively-linked children
      whose bodies carry no parent-ref line, which on a close gate is a
      fail-open.
    """

    READ = "read"
    UNSUPPORTED = "unsupported"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class NativeRead:
    """A native read's children plus how the read went.

    ``numbers`` are the children in this repository; ``foreign`` the sub-issues
    that live in another repository, each with its repository, so none is taken
    for this repository's issue of the same number.

    ``said`` is what the failed call said (:class:`Said` — GitHub's error body,
    or gh's own line), carried so a consumer reporting an unreadable read can
    quote it rather than guess at the cause. ``None`` for a read that answered,
    or a failure with no words. ``why`` is pm's own reading of an answer it
    could not use — a listed sub-issue it could not place in a repository —
    ``None`` otherwise.
    """

    numbers: set[int]
    outcome: NativeReadOutcome
    said: Said | None = None
    foreign: frozenset[ForeignIssue] = frozenset()
    why: str | None = None

    @property
    def supported(self) -> bool:
        return self.outcome is not NativeReadOutcome.UNSUPPORTED


def read_native_children(config: dict[str, Any], *, parent_number: int | str) -> NativeRead:
    """The native child set, with the outcome that produced it.

    Each sub-issue is placed in its repository by comparing the repository its
    entry names (``repository_url``) with this repository's own name: the same
    name is this repository's, whatever else the entry lacks, and goes to
    ``numbers``; another name goes to ``foreign``; an entry naming none is this
    repository's, the number-only shape. This repository's name is taken from
    the answer itself where it can be — an entry's ``parent_issue_url`` names
    the parent asked about, which is this repository's issue, and the hosting
    service puts it on every entry — so placing costs no call. Only where an
    entry names a repository and none carries that anchor is it read from the
    parent's own record (:func:`_this_repository`), once per read; a parent
    record that cannot be read leaves the read unreadable, since no entry can
    then be placed.

    What this read cannot see. The set is what the hosting service lists to
    this reader, and it may leave out a sub-issue in a repository the reader
    cannot see; nothing in the answer marks the omission. So a child this list
    names holds a gate whether or not its own record can then be read — one
    that cannot leaves the fold indeterminate — but a child the list leaves out
    is not in the set at all, and a gate over it opens.

    Prefer this over :func:`read_native_child_numbers`, which cannot distinguish
    "no native substrate here" from "I could not reach it".
    """
    args = list_sub_issues_args(parent_number=parent_number)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        # No `gh` at all. This says nothing about the INSTANCE — a native child
        # set may well exist and we simply cannot look. Calling it unsupported
        # would license a determinate textual-only answer on no evidence, so it
        # is the unreadable case (ADR-035 §2).
        return NativeRead(numbers=set(), outcome=NativeReadOutcome.UNREADABLE)
    if proc.returncode != 0:
        outcome = _classify_native_failure(
            config,
            parent_number=parent_number,
            stderr=proc.stderr or "",
            stdout=proc.stdout or "",
        )
        said = _Refusal.read(proc.stdout or "", proc.stderr or "").said
        return NativeRead(numbers=set(), outcome=outcome, said=said)
    payload = _parse_concatenated_arrays((proc.stdout or "").strip())
    if payload is None:
        # The endpoint answered and we could not read it: a child set may exist.
        return NativeRead(numbers=set(), outcome=NativeReadOutcome.UNREADABLE)
    listed: list[tuple[dict[str, Any], str | None]] = []
    for entry in payload:
        if not isinstance(entry, dict) or not isinstance(entry.get("number"), int):
            continue
        named = str(entry.get("repository_url") or "")
        repository = _url_repository(named) if named else None
        if named and repository is None:
            # A listed child no repository could hold: unplaced, a child set may
            # hold it, so the read is not a child set.
            return NativeRead(
                numbers=set(),
                outcome=NativeReadOutcome.UNREADABLE,
                why=(
                    f"a sub-issue of #{parent_number} names a repository the hosting "
                    f"service could not have spelled ({named!r}), so it cannot be placed"
                ),
            )
        listed.append((entry, repository))
    here: str | None = None
    if any(repository is not None for _entry, repository in listed):
        here = _anchored_repository(payload, parent_number) or _this_repository(
            config, parent_number
        )
        if here is None:
            return NativeRead(
                numbers=set(),
                outcome=NativeReadOutcome.UNREADABLE,
                why=(
                    f"#{parent_number}'s sub-issues name their repositories, and this "
                    f"repository's own name could not be read from #{parent_number}'s "
                    "record, so none of them can be placed"
                ),
            )
    numbers: set[int] = set()
    foreign: set[ForeignIssue] = set()
    for entry, repository in listed:
        if repository is None or here is None or repository.lower() == here.lower():
            numbers.add(entry["number"])
        else:
            foreign.add(ForeignIssue(repository, entry["number"]))
    return NativeRead(numbers=numbers, outcome=NativeReadOutcome.READ, foreign=frozenset(foreign))


def _anchored_repository(payload: list, parent_number: int | str) -> str | None:
    """This repository's name as the sub-issues answer states it: the repository
    of the parent an entry's ``parent_issue_url`` names, where that is the parent
    asked about — an issue of this repository. ``None`` when no entry says so."""
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        m = _ISSUE_URL.search(str(entry.get("parent_issue_url") or ""))
        if m is not None and int(m.group("number")) == int(parent_number):
            if is_repository_name(m.group("repo")):
                return m.group("repo")
    return None


def _this_repository(config: dict[str, Any], parent_number: int | str) -> str | None:
    """This repository's name as the parent's own record states it — the
    repository the seam's requests are addressed to — or ``None`` when the
    record cannot be read or names none. One call, made only where a sub-issues
    answer names repositories and carries no ``parent_issue_url`` to anchor them
    (:func:`read_native_children`)."""
    try:
        proc = _gh_call(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/issues/{parent_number}",
                "--jq",
                ".repository_url",
            ],
            config,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return _url_repository((proc.stdout or "").strip())


class SubIssueReads:
    """A run's reads of parents' native sub-issues — each parent read at most once.

    A verb that links many children under a few parents holds one of these for
    the run and hands it to :func:`link_sub_issue`, so a parent's list is read
    once however many of its children the run touches (#1040: one Feature was
    read nine times, once per child). Keyed by parent number; every read goes
    through :func:`read_native_children`, so a cached answer carries the same
    three-valued outcome a fresh one would.

    The reads are a snapshot taken when first asked. The linker still reads each
    child's own record fresh before it posts, so a link someone else made after
    the snapshot is reported as already linked, never posted twice.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._reads: dict[int, NativeRead] = {}

    def read(self, parent_number: int | str) -> NativeRead:
        """The parent's native sub-issues — read on first ask, then remembered."""
        key = int(parent_number)
        if key not in self._reads:
            self._reads[key] = read_native_children(self._config, parent_number=key)
        return self._reads[key]


def read_native_child_numbers(
    config: dict[str, Any], *, parent_number: int | str
) -> set[int] | None:
    """Return the issue NUMBERS of the parent's native sub-issues in this
    repository (a sub-issue in another repository is not among them).

    Reads ``GET /repos/{owner}/{repo}/issues/{parent}/sub_issues`` (paginated)
    through the gh helper (DEC-023 host/owner pinning), the same endpoint the
    write half's idempotency read uses — but keyed on the child ``number`` (the
    methodology's stable id) rather than the database ``id`` the *write* needs.

    Returns ``None`` when the native read did not succeed, for any reason —
    an absent endpoint, a missing ``gh``, a non-zero exit, or an unparseable
    payload. An empty set is a *successful* read of a parent with no native
    sub-issues, distinct from ``None``.

    Retained for callers that only need the numbers. :func:`resolve_children` no
    longer uses it: collapsing "no native substrate here" with "could not reach
    it" loses the distinction a gate depends on, so the resolver calls
    :func:`read_native_children` instead. Prefer that one in new code.
    """
    read = read_native_children(config, parent_number=parent_number)
    return read.numbers if read.outcome is NativeReadOutcome.READ else None


# The seam's own corpus acquisition. Set far above any plausible tracker: this is
# not a view control, it is the point past which the seam refuses to pretend it
# saw everything. Struck => the answer is incomplete, never a short answer served
# as a whole one. `gh issue list` paginates internally up to --limit, so one call
# fetches to exhaustion below the ceiling.
CORPUS_CEILING = 5000

_CORPUS_FIELDS = "number,body,state,labels,milestone"


@dataclass(frozen=True)
class IssueCorpus:
    """Every issue the seam could see, and whether that is all of them.

    ``complete`` is the honest signal the consumers lacked: each of them fetched
    its own corpus with a different ceiling and only one noticed when it struck
    one, so the same seam answered with four different notions of completeness.
    """

    rows: tuple[dict[str, Any], ...]
    complete: bool

    @property
    def bodies(self) -> dict[int, str]:
        out: dict[int, str] = {}
        for row in self.rows:
            number = row.get("number")
            if isinstance(number, int):
                out[number] = str(row.get("body") or "")
        return out

    @property
    def titles(self) -> dict[int, str]:
        """Issue titles, for renderers. Requires ``title`` in the fetch's
        ``fields`` — the default set omits it, and without it every value is the
        empty string with nothing to say why."""
        out: dict[int, str] = {}
        for row in self.rows:
            number = row.get("number")
            if isinstance(number, int):
                out[number] = str(row.get("title") or "")
        return out

    @property
    def states(self) -> dict[int, str]:
        out: dict[int, str] = {}
        for row in self.rows:
            number = row.get("number")
            if isinstance(number, int):
                out[number] = str(row.get("state", "")).lower()
        return out


def fetch_issue_corpus(
    config: dict[str, Any],
    *,
    fields: str = _CORPUS_FIELDS,
    state: str = "all",
    limit: int = CORPUS_CEILING,
) -> IssueCorpus | None:
    """Fetch the issue corpus, reporting whether the fetch was exhaustive.

    Returns ``None`` when the query itself failed — distinct from a complete
    fetch of an empty tracker, and distinct from a truncated one.

    ``limit`` defaults to the seam's ceiling, which is not a view control: a gate
    wants every row or an honest refusal. A *renderer* may lower it deliberately
    (``show-tree --limit``), and then `complete` is what lets it label the view as
    partial instead of presenting a short answer as the whole one. ``state``
    likewise exists for renderers; a gate must not filter, since a closed child
    still counts.
    """
    args = [
        "gh",
        "issue",
        "list",
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        fields,
    ]
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        parsed = json.loads(proc.stdout or "[]")
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, list):
        return None
    rows = tuple(row for row in parsed if isinstance(row, dict))
    # Measure the ceiling against what `gh` RETURNED, not against what survived
    # filtering: a dropped non-dict row would otherwise make a struck ceiling
    # read as complete. Measured against the limit actually requested, so a
    # renderer's lowered limit is judged against its own ask.
    return IssueCorpus(rows=rows, complete=len(parsed) < limit)


def resolve_children(
    config: dict[str, Any],
    *,
    parent_number: int,
    corpus: dict[int, str] | None = None,
    corpus_complete: bool | None = None,
) -> ChildResolution:
    """Resolve a parent's children — its native sub-issues together with every
    issue whose first line names it, native-wins on conflict (DEC-005).

    The sole read-seam for "what are this parent's children?" ``show-tree``, the
    DEC-034 closure fold and ``close-issue``'s open-children walk all resolve
    through it, so none re-derives containment (the ADR-026 one-read-seam
    discipline applied to the containment axis).

    Args:
      parent_number   — the parent whose children to resolve.
      corpus          — optional ``{number: body}``. Omit it and the seam
                        acquires the corpus itself via :func:`fetch_issue_corpus`,
                        which is the path every gate should take. Supply one only
                        when you already hold it (``show-tree`` renders from a
                        corpus it fetched for other reasons).
      corpus_complete — required *with* ``corpus``: your claim about whether that
                        map is the whole tracker. Omit the claim and the seam
                        treats the answer as **not vouched for**
                        (``complete=False``) rather than assuming — assuming is
                        how four consumers ended up with four ceilings (#846).

    Returns a :class:`ChildResolution` carrying the child set, each child's
    substrate, ``native_supported``, and a **completeness verdict**
    (``complete`` + ``incomplete_reason``). A consumer gating on the child set
    must check ``complete``: an incomplete answer is not a smaller child set, it
    is *no answer*, and holding fail-closed is the only correct response.

    Resolution:
      1. Native side — one ``GET …/sub_issues`` call for THIS parent
         (:func:`read_native_children`, three-valued). ``UNSUPPORTED`` → the
         instance has no native substrate, so textual-only is the *complete*
         answer (``native_supported=False``). ``UNREADABLE`` → a native child set
         may exist unseen, so the resolution is **incomplete** while
         ``native_supported`` stays True: the endpoint is not absent, it was not
         reachable.
      2. Textual side — every corpus issue whose body first-line parent-ref names
         ``parent_number`` (``_body_names_parent``), excluding the parent itself.
      3. Union with **native-wins dedup**: a child present both ways is NATIVE; a
         child present only textually is TEXTUAL; a native child not in the
         corpus is still NATIVE (mixed-mode — the native panel is authoritative
         even for a child the textual scan missed). A native sub-issue in another
         repository is a child with its repository (:attr:`ResolvedChild.repository`),
         never this repository's issue of the same number.
      4. Determinacy — an incomplete corpus or an unreadable native read makes
         the whole resolution incomplete. A non-empty native panel does **not**
         rescue a truncated textual scan: the rows never fetched are exactly
         where a textual-only child would be.

    API cost — two shapes, and the difference matters before you drop ``corpus=``:

    * **Corpus supplied** — the textual side is free (you already paid for the
      fetch); the native side is one ``…/sub_issues`` call per parent resolved.
    * **Corpus omitted** (the seam acquires) — the textual side costs one FULL
      enumeration per call, plus the same one native call per parent.

    The native side is per *parent resolved*, never per corpus issue, so it
    scales with parents queried. The textual side does not: a caller that
    resolves many parents in a loop and omits ``corpus`` pays a whole-tracker
    enumeration on every iteration. ``show-tree`` is exactly that shape — it
    walks candidate parents — which is why it supplies its own corpus and must
    keep doing so. A gate resolving a single container should omit it and let
    the seam vouch for completeness.

    Three consumers today: ``show-tree`` (supplies), the DEC-034 closure fold's
    ``cascade_members`` (omits), and ``close-issue._find_open_children``
    (supplies, with a completeness claim). A whole-tree ``show-tree`` pays one
    native call per node that has children — bounded by the tree's internal-node
    count, well under the corpus size, and the price of honouring "native wins"
    without a private GraphQL batch (a batched ``subIssues`` GraphQL pass is a
    later optimisation, not pinned here — COR-007 speculative-generality
    restraint).
    """
    native = read_native_children(config, parent_number=parent_number)
    native_supported = native.supported
    native_set = native.numbers
    fetch_failed = False

    if corpus is None:
        fetched = fetch_issue_corpus(config)
        if fetched is None:
            corpus = {}
            corpus_complete = False
            fetch_failed = True
        else:
            corpus = fetched.bodies
            corpus_complete = fetched.complete
    elif corpus_complete is None:
        # A caller that supplies a corpus must claim its completeness. Absent a
        # claim the seam cannot vouch for it, so it says so rather than assuming.
        corpus_complete = False

    textual_set = {
        number
        for number, body in corpus.items()
        if number != parent_number and _body_names_parent(body, parent_number)
    }

    # Determinacy, per ADR-035 §5. A non-empty native panel does NOT rescue a
    # truncated textual scan: the rows never fetched are exactly where a
    # textual-only child would be.
    incomplete_reason: str | None = None
    if fetch_failed:
        incomplete_reason = "the issue list could not be read at all (gh failure)"
    elif native.outcome is NativeReadOutcome.UNREADABLE:
        incomplete_reason = native.why or _quoting(
            "the native sub-issues read failed and the failure could not be "
            "attributed to an absent endpoint, so a native child set may exist and "
            "was not seen",
            native.said,
        )
    elif not corpus_complete:
        incomplete_reason = (
            "the issue corpus was not enumerated to exhaustion, so a textual-only "
            "child may sit in the rows that were never fetched"
        )

    resolved: list[ResolvedChild] = []
    for number in native_set:
        resolved.append(ResolvedChild(number=number, substrate=ChildSubstrate.NATIVE))
    for number in textual_set - native_set:  # native-wins: skip textual dupes
        resolved.append(ResolvedChild(number=number, substrate=ChildSubstrate.TEXTUAL))
    resolved.sort(key=lambda c: c.number)
    # A sub-issue in another repository is another issue than this repository's
    # of the same number: it is neither deduped against one nor read as one.
    resolved.extend(
        ResolvedChild(
            number=child.number, substrate=ChildSubstrate.NATIVE, repository=child.repository
        )
        for child in sorted(native.foreign)
    )
    return ChildResolution(
        children=tuple(resolved),
        native_supported=native_supported,
        complete=incomplete_reason is None,
        incomplete_reason=incomplete_reason,
    )


def _body_names_parent(body: str, parent_number: int) -> bool:
    """True when a child body's first line names issue ``parent_number`` as its
    parent, in any form (``body_parent_ref.named_issue``).

    The textual side of the child set reads the line the way every other reader
    of an issue's parent does, so the issue a line names here is the issue
    :func:`resolve_parent` resolves the same line to. A first line naming its
    parent in a form the child's type does not allow (``Epic: #5``) still counts
    the child: it is reported as non-conforming, never dropped from a gate.
    """
    return body_parent_ref.named_issue(body) == parent_number


# =========================================================================
# Read seam, upward — resolve an issue's parent. The counterpart to
# `resolve_children`: one record read, the native parent held to the first line.
# =========================================================================


class ParentKind(Enum):
    """How an issue's two records of its parent stand (:func:`resolve_parent`).

    AGREED        — the native parent is the issue the first line names.
    NATIVE_ONLY   — a native parent, and a first line that names no issue (none
                    at all, or a milestone).
    TEXTUAL_ONLY  — a first line naming a parent, and no native parent — the
                    tracker reports none, or the instance has no sub-issues.
    DISAGREE      — a native parent other than the issue the first line names
                    (a native parent in another repository always is).
    NONE          — neither record names a parent.
    UNREAD        — the issue's record could not be read, so its native parent
                    is not known; the first line is read from the body the
                    caller holds.
    """

    AGREED = "agreed"
    NATIVE_ONLY = "native-only"
    TEXTUAL_ONLY = "textual-only"
    DISAGREE = "disagree"
    NONE = "none"
    UNREAD = "unread"


@dataclass(frozen=True)
class ParentResolution:
    """An issue's parent, with how its native link and its first line stand.

    ``parent`` is the parent the issue has: the native one wherever one was read
    (DEC-005: native wins), else the issue the first line names, else ``None``.
    ``native`` is the native parent as read; ``line`` the first line, classified
    (``body_parent_ref.read_first_line``), whose ``issue`` is :attr:`named`.

    A first line naming the issue itself names no parent: no child set holds an
    issue under itself (ADR-035). It is classified as naming none — ``line``'s
    form is ``NONE`` — ``names_itself`` says it did, and :attr:`self_note` says
    so in one sentence, so every property here agrees that the line names no
    parent.

    A consumer that **writes** on the parent acts only where :attr:`walks` — the
    two records agree, or a first line in an allowed form is the only record —
    and otherwise stops, saying :attr:`fact` and :meth:`remedy`. A consumer that
    only **reads** follows the native parent, counts the first line's parent as
    well (:attr:`local_parents`), and labels the disagreement. Each says its own
    consequence after the seam's words; none compares the two records itself.
    """

    issue: int
    kind: ParentKind
    line: body_parent_ref.FirstLine
    native: NativeParent | None = None
    unread: UnreadIssue | None = None
    names_itself: bool = False

    @property
    def named(self) -> int | None:
        """The issue the first line names as the parent, in any form — never
        the issue itself."""
        return self.line.issue

    @property
    def parent(self) -> NativeParent | None:
        """The parent the issue has: native wherever one was read, else the
        first line's."""
        if self.native is not None:
            return self.native
        return NativeParent(self.named) if self.named is not None else None

    @property
    def walks(self) -> bool:
        """Whether a consumer that writes on the parent may act on it: the two
        records agree, or a conforming first line is the only record."""
        conforming = self.line.form is body_parent_ref.LineForm.CONFORMING
        return self.kind is ParentKind.AGREED or (
            self.kind is ParentKind.TEXTUAL_ONLY and conforming
        )

    @property
    def local_parents(self) -> tuple[int, ...]:
        """Every parent in this repository the issue is a child of — its native
        parent and the issue its first line names, one or both, native first —
        the parents whose child sets (:func:`resolve_children`) hold it."""
        out: list[int] = []
        if self.native is not None and self.native.repository is None:
            out.append(self.native.number)
        if self.named is not None and self.named not in out:
            out.append(self.named)
        return tuple(out)

    @property
    def self_note(self) -> str | None:
        """What to say of a first line naming the issue itself, after which a
        consumer says its own consequence, or ``None``."""
        if not self.names_itself:
            return None
        n = self.issue
        return f"#{n}'s first line `{self.line.line}` names #{n} itself, which is no parent"

    @property
    def fact(self) -> str | None:
        """What keeps the two records from agreeing, in the seam's words, or
        ``None`` where nothing does: ``#12's first line names #5, its native
        parent is #7``. A non-conforming first line is said by
        :attr:`form_note`, not here."""
        n = self.issue
        if self.kind is ParentKind.UNREAD:
            detail = self.unread.detail if self.unread is not None else ""
            if self.named is None:
                return (
                    f"#{n}'s record could not be read, so its native parent is not known ({detail})"
                )
            return (
                f"#{n}'s record could not be read to hold its native parent to "
                f"#{self.named}, the parent its first line names ({detail})"
            )
        if self.native is None or self.kind not in (ParentKind.NATIVE_ONLY, ParentKind.DISAGREE):
            return None
        if self.named is None:
            return (
                f"#{n}'s first line names no parent issue, its native parent is {self.native.ref}"
            )
        return f"#{n}'s first line names #{self.named}, its native parent is {self.native.ref}"

    @property
    def form_note(self) -> str | None:
        """What to say of a first line naming its parent in a form the issue's
        type does not allow, after the issue's number, or ``None``."""
        note = self.line.note
        return f"#{self.issue}'s {note}" if note is not None else None

    def remedy(self, *, abroad: str = "") -> str | None:
        """How the two records are brought into agreement, or ``None`` where
        they agree or no native parent was read: the native parent wins and the
        first line is rewritten to name it ([project-management:DEC-005-linking-and-containment]).
        No first-line form can name a native parent in another repository; the
        line then says so — with ``abroad``, what the caller does not do there —
        and how the native link is moved under the first line's parent instead.

        Neither applies to an issue whose type has no first-line form naming an
        issue (an EPIC): its container is a milestone, so no rewrite of its first
        line names an issue parent, and the line says that instead."""
        native, n = self.native, self.issue
        if native is None or self.kind not in (ParentKind.NATIVE_ONLY, ParentKind.DISAGREE):
            return None
        if not self.line.issue_form:
            elsewhere = (
                f"; {native.ref} is in another repository, which {abroad}"
                if native.repository is not None and abroad
                else ""
            )
            return (
                f"→ #{n}'s container is a milestone: no first-line form its type may have "
                f"names an issue, so no rewrite of its first line names {native.ref}"
                f"{elsewhere}."
            )
        if native.repository is None:
            return (
                f"→ the native parent wins (DEC-005): `set-field {n} --parent {native.number}` "
                f"rewrites #{n}'s first line to name it."
            )
        also = f" and {abroad}" if abroad else ""
        move_link = (
            f"; if #{self.named} is its parent, `set-field {n} --parent {self.named}` moves the "
            "native link under it"
            if self.named is not None
            else ""
        )
        return (
            f"→ {native.ref} is in another repository, which no first-line form can name"
            f"{also}{move_link}."
        )


def compare_parents(
    issue_number: int, line: body_parent_ref.FirstLine, native: NativeParent | None
) -> ParentResolution:
    """Hold an issue's native parent to its first line — the pure comparison
    :func:`resolve_parent` makes after its read, for a caller that derived the
    native parent itself (``show-tree``, from the native child sets it resolved).
    ``native`` is ``None`` where the issue has none. A first line naming the
    issue itself is classified here as naming no parent (:func:`_self_named`)."""
    line, names_itself = _self_named(issue_number, line)
    named = line.issue
    if native is None:
        kind = ParentKind.TEXTUAL_ONLY if named is not None else ParentKind.NONE
    elif named is None:
        kind = ParentKind.NATIVE_ONLY
    elif native.is_issue(named):
        kind = ParentKind.AGREED
    else:
        kind = ParentKind.DISAGREE
    return ParentResolution(
        issue=issue_number, kind=kind, line=line, native=native, names_itself=names_itself
    )


def _self_named(
    issue_number: int, line: body_parent_ref.FirstLine
) -> tuple[body_parent_ref.FirstLine, bool]:
    """``line`` as the seam reads it for issue ``issue_number``, and whether it
    named the issue itself. Such a line names no parent — no child set holds an
    issue under itself — so it is read as naming none, its form ``NONE`` and no
    form note (a line naming no parent is in no form to correct); the line as
    written is kept for the seam's sentence."""
    if line.issue is None or line.issue != issue_number:
        return line, False
    return replace(line, form=body_parent_ref.LineForm.NONE, number=None, note=None), True


def resolve_parent(
    config: dict[str, Any],
    *,
    issue_number: int,
    structural_type: str | None,
    issue_types: dict,
    record: IssueRecord | UnreadIssue | None = None,
    body: str | None = None,
) -> ParentResolution:
    """Resolve an issue's parent — its native parent held to its first line.

    The sole read seam for "what is this issue's parent?", the upward
    counterpart of :func:`resolve_children`: the forward cascade, the closure
    cascade's eligibility report and the closure fold's membership step resolve
    a parent through it, and ``show-tree`` through its pure half
    (:func:`compare_parents`). None compares a first line with a native parent
    itself, and the first line is read by ``body_parent_ref`` — the reader the
    textual side of a child set uses — so the issue a line names is the same
    for every consumer.

    Args:
      issue_number    — the issue whose parent to resolve.
      structural_type — its type, which says which first-line forms conform;
                        ``None`` for an untyped issue, whose any
                        ``<Label>: #<N>`` line conforms.
      record          — the issue's record (:func:`read_issue_record`), or why
                        it could not be read, when the caller already holds it;
                        omit it and the seam reads it. A ``gh issue view``
                        payload is not a record: it cannot carry the native
                        parent.
      body            — the issue's body as the caller holds it, read for the
                        first line only where the record cannot be read.

    Cost: one REST read of the issue when ``record`` is omitted, none when it is
    supplied (the shape mirrors :func:`resolve_children`'s corpus-supplied /
    omitted split).
    """
    if record is None:
        record = read_issue_record(config, issue_number=issue_number)
    if isinstance(record, UnreadIssue):
        line, names_itself = _self_named(
            issue_number, body_parent_ref.read_first_line(body or "", structural_type, issue_types)
        )
        return ParentResolution(
            issue=issue_number,
            kind=ParentKind.UNREAD,
            line=line,
            unread=record,
            names_itself=names_itself,
        )
    line = body_parent_ref.read_first_line(
        str(record.issue.get("body") or ""), structural_type, issue_types
    )
    return compare_parents(issue_number, line, record.parent)


# =========================================================================
# Render-on-demand textual children view (DEC-039 D4 / ADR-035 section 4).
#
# Where the tracker has no native sub-issues panel (`containment: textual`), a
# parent has no parent-side children view at all — only the child-side textual
# refs + `show-tree` on demand. This half supplies that view as a **generated
# do-not-edit comment on the parent**, written by **FULL OVERWRITE** through one
# construction point and refreshed by the read path. It is a derived, regenerable
# view: the child-side ref + the read seam (`resolve_children`) remain the source
# of truth. **Never an append** — there is exactly one marked comment per parent,
# found by its marker and updated in place (DEC-039 D4: a stored body block would
# be a drift-prone second source of truth; an append would churn comments on every
# child-create).
#
# Mode gate: the writer is a **no-op in native mode** (the native sub-issues panel
# already gives parent-side visibility). The single mode gate is
# `refresh_children_comment`, which consults the caller-supplied containment mode
# once and returns a no-op outcome for `native`.
# =========================================================================


# The do-not-edit marker that identifies the generated children comment. An HTML
# comment so it is INVISIBLE in rendered markdown, yet a stable string the
# find-existing scan keys on (a human reading the source sees the do-not-edit
# notice; a human reading the rendered comment sees only the children list under
# the visible heading). This is the one place the marker text lives — both the
# renderer (emits it) and the find-existing scan (matches it) reference it, so
# they cannot drift.
CHILDREN_VIEW_MARKER = "<!-- pkit:children-view do-not-edit -->"

# The containment-mode value that ENABLES the textual children view. Mirrors
# ``axis_labels.CONTAINMENT_TEXTUAL`` — duplicated here (a bare string) so this
# module's writer needs no import of the selector seam (it takes the mode as a
# plain ``str`` argument; the caller resolves the mode through
# ``axis_labels.containment_mode`` and passes the value). Any non-``textual``
# value (``native``, the greenfield default, or anything unrecognised) is a no-op.
CONTAINMENT_TEXTUAL = "textual"

# The visible heading + do-not-edit notice the rendered comment carries, so a
# human reading the COMMENT (not the source) also knows not to hand-edit it.
_CHILDREN_VIEW_HEADING = "### Children (auto-generated — do not edit)"
_CHILDREN_VIEW_NOTICE = (
    "_This comment is a regenerable view of this issue's children, refreshed by "
    "project-kit. Edits are overwritten. The source of truth is each child's "
    "first-line parent-ref._"
)


class RefreshOutcome(Enum):
    """The outcome class of one children-comment refresh attempt.

    CREATED    — no marked comment existed; one was posted this call.
    UPDATED    — the marked comment existed and its body changed; PATCHed.
    UNCHANGED  — the marked comment existed and the freshly-rendered body equals
                 its current body (value-equality idempotency) → NO write.
    SKIPPED    — native mode (the native panel suffices) → the writer is a no-op.
    FAILED     — a gh read/write failed (auth/network/missing `gh`). Non-fatal to
                 the caller — the child-side textual ref is the spine.
    """

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class RefreshResult:
    """Outcome of one children-comment refresh — a neutral carrier.

    Failure-posture-neutral in the same spirit as :class:`LinkResult` (ADR-035
    section 3, ADR-031 point 6): it records what happened; the caller decides what
    it means. ``create-issue`` treats every outcome as non-fatal — the textual ref
    is the spine — and reports a one-line note keyed on ``outcome``.
    """

    outcome: RefreshOutcome
    detail: str = ""

    @property
    def ok(self) -> bool:
        """True when the view is in the desired state after this call (created,
        updated, already-current, or a deliberate native-mode no-op). Only FAILED
        is a genuine problem."""
        return self.outcome is not RefreshOutcome.FAILED


def render_children_comment_body(
    *,
    parent_number: int,
    resolution: ChildResolution,
    titles: dict[int, str] | None = None,
) -> str:
    """Render the parent's children-comment body from a :class:`ChildResolution`.

    The rendered view is DERIVED from the read seam's output (DEC-039 D4: the
    comment is a regenerable view, not a source of truth). The body carries:

      1. the :data:`CHILDREN_VIEW_MARKER` (the find-existing key, invisible in
         rendered markdown);
      2. a visible heading + do-not-edit notice so a human reading the rendered
         comment also knows not to hand-edit it;
      3. one bullet per resolved child — ``- #<n>``, or ``- owner/repo#<n>`` for
         a sub-issue in another repository (GitHub auto-links either reference),
         with a child's title appended when ``titles`` carries it (``titles`` is
         this repository's, so a child elsewhere is listed without one), and a
         ``(textual)`` provenance marker on a textual-only child (native is the
         default and unmarked, matching ``show-tree``).

    Children are listed in the resolution's order (sorted by number — the seam
    already sorts). An empty child set renders an explicit "no children" line so a
    parent whose last child was removed gets an honest, current view rather than a
    stale list. The output is deterministic for a given ``(resolution, titles)`` so
    the idempotency value-equality check (re-render of the same child set → no
    write) holds.
    """
    titles = titles or {}
    lines = [
        CHILDREN_VIEW_MARKER,
        _CHILDREN_VIEW_HEADING,
        "",
        _CHILDREN_VIEW_NOTICE,
        "",
    ]
    if not resolution.children:
        lines.append("_No children._")
    else:
        for child in resolution.children:
            title = titles.get(child.number) if child.repository is None else None
            label = child.ref + (f" — {title}" if title else "")
            marker = "  _(textual)_" if child.substrate is ChildSubstrate.TEXTUAL else ""
            lines.append(f"- {label}{marker}")
    return "\n".join(lines) + "\n"


def list_issue_comments_args(*, parent_number: int | str) -> list[str]:
    """Construct the ``gh api …/comments`` list (GET) argv.

    Reads ``GET /repos/{owner}/{repo}/issues/{parent}/comments`` (paginated) to
    find the existing marked children comment by its marker — and crucially to get
    each comment's REST ``id`` (``gh issue view --json comments`` does NOT carry
    the REST comment id the PATCH needs). The find-existing scan keys on
    :data:`CHILDREN_VIEW_MARKER` in the comment body.
    """
    return [
        "gh",
        "api",
        "--paginate",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/comments",
    ]


def create_comment_args(*, parent_number: int | str, body: str) -> list[str]:
    """Construct the ``gh api …/comments`` create (POST) argv.

    Posts ``POST /repos/{owner}/{repo}/issues/{parent}/comments`` with the
    rendered body. ``-f body=<text>`` sends the body as a string field (the
    comment body is markdown text, not a typed value — ``-f``, not ``-F``). Used
    only when no marked comment yet exists; an existing one is UPDATED in place
    (never a second comment — DEC-039 D4's overwrite-not-append invariant).
    """
    return [
        "gh",
        "api",
        "-X",
        "POST",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/comments",
        "-f",
        f"body={body}",
    ]


def update_comment_args(*, comment_id: int | str, body: str) -> list[str]:
    """Construct the ``gh api …/comments/<id>`` update (PATCH) argv.

    PATCHes ``/repos/{owner}/{repo}/issues/comments/{comment_id}`` with the
    freshly-rendered body — the **full overwrite** that makes the children view a
    single source (DEC-039 D4 / ADR-035 section 4). The comment id is the REST id
    read from :func:`list_issue_comments_args`. ``-f body=<text>`` overwrites the
    whole body (markdown string field). This is the overwrite that replaces the
    append a naive children view would do.
    """
    return [
        "gh",
        "api",
        "-X",
        "PATCH",
        f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}",
        "-f",
        f"body={body}",
    ]


# Sentinel distinguishing "the comment list could not be READ" from "read OK,
# no marked comment present". The distinction is load-bearing: a failed read must
# be reported FAILED (never treated as absent, which would duplicate-post — the
# very append/churn DEC-039 D4 forbids), while a clean read with no marked comment
# is the CREATE path. A distinct singleton (not ``None``) so the two cannot be
# conflated at the call site.
class _CommentReadFailed:
    _instance: _CommentReadFailed | None = None

    def __new__(cls) -> _CommentReadFailed:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


COMMENT_READ_FAILED: _CommentReadFailed = _CommentReadFailed()


def find_children_comment(
    config: dict[str, Any], *, parent_number: int | str
) -> tuple[int, str] | None | _CommentReadFailed:
    """Find the parent's existing marked children comment.

    Lists the parent's comments and returns one of three signals — the
    three-way distinction overwrite-not-append depends on:

      * ``(comment_id, body)`` — the FIRST comment whose body carries
        :data:`CHILDREN_VIEW_MARKER`. The refresh OVERWRITES this one in place
        (PATCH), never posting a second comment.
      * ``None`` — the list was read cleanly and NO marked comment exists. The
        refresh CREATES one (the first POST).
      * :data:`COMMENT_READ_FAILED` — the list could NOT be read (missing ``gh``,
        non-zero exit, unparseable payload). The refresh reports FAILED and writes
        NOTHING — a failed read is never treated as "absent" (which would
        duplicate-post, the churn DEC-039 D4 forbids).
    """
    args = list_issue_comments_args(parent_number=parent_number)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return COMMENT_READ_FAILED
    if proc.returncode != 0:
        return COMMENT_READ_FAILED
    payload = _parse_concatenated_arrays((proc.stdout or "").strip())
    if payload is None:
        return COMMENT_READ_FAILED
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        body = entry.get("body")
        if isinstance(body, str) and CHILDREN_VIEW_MARKER in body:
            cid = entry.get("id")
            if isinstance(cid, int):
                return cid, body
    return None


def refresh_children_comment(
    config: dict[str, Any],
    *,
    parent_number: int,
    corpus: dict[int, str],
    containment_mode: str,
    titles: dict[int, str] | None = None,
) -> RefreshResult:
    """Refresh the parent's render-on-demand children comment (the ONE writer).

    The single construction point for the textual children view (ADR-035 section
    3/4): every refresh of the view routes through here; no script string-builds a
    children-comment write inline. Composes the render + find-existing + overwrite:

      1. **Mode gate (the one point).** In ``native`` mode the native sub-issues
         panel already gives parent-side visibility, so this is a **no-op**
         (:attr:`RefreshOutcome.SKIPPED`). Only ``textual`` mode renders + writes.
      2. **Render** the body from the read seam's resolution
         (:func:`resolve_children` → :func:`render_children_comment_body`) — the
         comment is a derived view, the seam stays the source of truth.
      3. **Find** the existing marked comment (:func:`find_children_comment`). A
         failed READ is :attr:`RefreshOutcome.FAILED` (never treated as "absent",
         which would duplicate-post).
      4. **Idempotency.** If a marked comment exists and its body equals the
         freshly-rendered body, **skip the write** (:attr:`RefreshOutcome.UNCHANGED`)
         — no comment-edit churn on a re-render of the same child set.
      5. **Write by overwrite** — PATCH the existing comment in place
         (:attr:`RefreshOutcome.UPDATED`), or POST a new one when none exists
         (:attr:`RefreshOutcome.CREATED`). **Never a second comment** — overwrite,
         never append (DEC-039 D4).

    Failure-posture-neutral (ADR-035 section 3): never raises; a failed read/write
    yields :attr:`RefreshOutcome.FAILED` for the caller to report as a one-line
    note — the child-side textual ref is the spine, so a failed refresh never fails
    the caller's operation.
    """
    if containment_mode != CONTAINMENT_TEXTUAL:
        return RefreshResult(
            RefreshOutcome.SKIPPED,
            detail=(
                f"containment is {containment_mode!r}; children comment is a no-op "
                "(the native sub-issues panel gives parent-side visibility)"
            ),
        )

    resolution = resolve_children(config, parent_number=parent_number, corpus=corpus)
    body = render_children_comment_body(
        parent_number=parent_number, resolution=resolution, titles=titles
    )

    existing = find_children_comment(config, parent_number=parent_number)
    if existing is COMMENT_READ_FAILED:
        # A failed READ is never treated as "absent" (which would duplicate-post);
        # write nothing and report FAILED (non-fatal — the textual ref is the spine).
        return RefreshResult(
            RefreshOutcome.FAILED,
            detail=(
                f"could not read #{parent_number}'s comments to find the children "
                "view; no write attempted (avoiding a duplicate post)"
            ),
        )
    if existing is not None:
        comment_id, current_body = existing  # type: ignore[misc]
        if current_body == body:
            return RefreshResult(
                RefreshOutcome.UNCHANGED,
                detail=(
                    f"children comment on #{parent_number} already current "
                    f"({len(resolution.children)} child(ren)); no write"
                ),
            )
        args = update_comment_args(comment_id=comment_id, body=body)
        outcome, verb = RefreshOutcome.UPDATED, "updated"
    else:
        args = create_comment_args(parent_number=parent_number, body=body)
        outcome, verb = RefreshOutcome.CREATED, "created"

    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return RefreshResult(
            RefreshOutcome.FAILED,
            detail="`gh` not on PATH; children comment refresh skipped",
        )
    if proc.returncode == 0:
        return RefreshResult(
            outcome,
            detail=(
                f"{verb} children comment on #{parent_number} "
                f"({len(resolution.children)} child(ren))"
            ),
        )
    stderr = (proc.stderr or "").strip()
    return RefreshResult(
        RefreshOutcome.FAILED,
        detail=(
            f"children comment refresh on #{parent_number} failed "
            f"(gh exit {proc.returncode}). stderr: {stderr or 'no stderr'}"
        ),
    )
