"""The answers a change wrote, read from the change check (DEC-055, DEC-065).

An agent building a change may give the answers its own change owes — the
revalidations and deferrals the change check asks of it — without asking
first. A reviewer other than that agent checks them, from the change check's
own list, and the person who authorises the merge is told what changed in
each updated document and which are left out of date, as information
(COR-050 point 3). No command writes the list into the pull request's
description: each reader derives the answers from the change check at the
pull request's head (DEC-065 points 1 and 2). This module derives them and
says what a reader takes from them:

- `derive(head, base)` runs the change check at the pull request's head
  (`pkit friction check --json --base <base> --head <oid>`) against the pull
  request's base — always named, so `$PKIT_CHECK_BASE` in the environment never
  changes it — after fetching that base, and reads what the check is asked
  about — its places and the files `friction.exclude` leaves out — at both ends
  of the change, through the backbone's discovery (`settings_change`). It
  returns the check's document and the friction settings the change alters —
  or why they could not be read, which is never a pass. `checked(head, base)`
  is the same run of the change check without the settings, for a reader that
  needs only the answers. Given the pull request's `Source`, either first
  fetches a head this clone lacks (`fetch_head`), from its branch, or for a
  pull request from a fork from the ref its base repository keeps for it, on
  the base's remote (`base_remote`). With `from_checkout=False`, either keeps the
  backbone's refusal to run an anchor's resolver away from the head, and starts
  no program the head holds (`Derivation.needs_checkout`).
- `written(base)` runs the same check as the project's gate runs it, from the
  working directory with no `--head` and nothing fetched: the answers the
  documentation check reads, where a page's answer meets its obligation
  (DEC-053 point 2).
- `told(document, settings, sentences, also)` is what the person who authorises
  the merge is told, as information, as a terminal shows it (DEC-065 point 4):
  what changed in each `updated` document, in its author's sentence; what is
  left out of date (`left_out`); each answer the change check did not ask for,
  with its words; the friction settings changed; how many files the check could
  not read; each revalidation the merge would leave answered apart (`apart`);
  and what the caller adds. The landing command and `show-pr --field answers`
  both print it from `_lib.answers_told.at_head`, the one place that feeds it, so
  the two cannot differ. `counted_told` counts it. Each answer reads in the words
  of the change check's own list (`LABELS`).
- `sentences(body)` reads the author's sentences where the change's author
  keeps them: the description's own `## What changed in each updated document`
  section (`SENTENCES_HEADING`), one list item per document, the document in
  a code span as the change check names it. `unread` names each list item
  there that gives no sentence — one in another form, such as the document in
  bold — by its line, and `unread_warning` is what a command says of it, with
  the form a sentence takes (`SENTENCE_FORM`). `updated_in` is the documents
  the change check marks `updated`, `unsaid` each of those with no sentence,
  and `unsaid_message` is what a command says of one: the move to review when
  it refuses, the opening of the pull request when it warns (DEC-065 point 3).
  `unlisted` names each sentence on a document the change check does not mark
  `updated`, which no reviewer checks, and `unlisted_warning` is what a
  command says of it. `closing_references` names each sentence that reads as a
  closing reference, which the host's own parser would close an issue with at
  merge, and `closing_message` is what a command says of one when it refuses
  (DEC-065 point 5).
- `listed_paths(document)` names the files the answers' words are on, from the
  file the change check gives each answer, an answer file or the artefact's own
  (COR-062 point 1): the landing stops, and nothing overrides it, on a base
  that changed one (DEC-065 point 5), and names the merge of the base
  ([project-management:DEC-064-base-merge-named] point 1).
  `apart(document)` is each revalidation on the base's tip that a merge would
  leave answered apart from the change's own (`answered_apart_at_tip`, COR-062
  point 7), a line each, told after the rest.
- `answers_folder(root)` is where the backbone keeps the friction answers, as
  its whole-repository check gives it, read once for a run: no path in it
  counts as code for a floor (DEC-032 D1).
- `covers(since, head, base)` asks the backbone whether every change from one
  head of a pull request to a later one lies inside answer files the change
  adds, a clean merge of the base counting as none (`pkit friction since`, its
  document's version 2): where it does, an authorisation for the earlier head
  covers the later one (DEC-055 point 3). An answer that cannot be read is
  never a pass.
- `merged(head, base)` runs the change check on the merge of a pull request's
  head with its base as the base stands, fetched first: the merge built as a
  commit on no branch, checked from a temporary checkout of it against the
  base's tip, the head named as the change's own head, as the checks on a pull
  request run it (DEC-055 point 6). `Merged.refused` gives the findings the
  check fails on there, each naming its document. The whole-repository check
  is not run at the merge: what a change leaves unanswered is what that check
  reports once the change merges, save the cases COR-050 names where the two
  checks part, and a page the base had already left stale is not the change's.
- `strip` and `has_list` find and remove the region an earlier run of these
  commands wrote into a description: both its markers, what lies between them,
  and the heading directly above it (`HEADING`, or `FORMER_HEADING`, a still
  earlier run's). No command writes one (DEC-065 point 1): the landing command
  removes one an earlier run left, the commands that open and edit the pull
  request drop one from the body they write, and every other reader strips it
  before it reads. Nothing else is removed. `orphaned` says a start marker has
  no end marker after it, and `ORPHAN_WARNING` is what a command says of it,
  leaving the text as it is.

Which backbone derives the answers: each run of the change check — from the
working directory, or, unless the caller gave it up (`from_checkout`), from a
temporary checkout of the head when the first meets the backbone's refusal to
run an anchor's resolver away from the head — runs the `pkit` first on PATH with
routing off (`PKIT_NO_ROUTE=1`). That is the backbone serving the command that
runs this module: a source checkout's own environment (`uv run` puts its `pkit`
first), a project's pinned version (the pin's run puts its `pkit` first), else
the installed tool. Never routed again from the directory a run starts in, a
temporary checkout's own source or pin cannot give the same head other answers.

The markers are locked to `body-format.yaml`'s `friction_answers_marker` by
`tests/test_pm_friction_answers.py`.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple

# Sibling _lib imports, dual-form so the module loads both as part of the `_lib`
# package (scripts/ on sys.path) and standalone-by-path (scripts/_lib/ on
# sys.path) — as `pr_validation` does, which imports this module.
try:
    import default_branch  # type: ignore[import-not-found]
    import provenance  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from _lib import default_branch, provenance  # type: ignore[no-redef]
# The one start of a `pkit` call, the package's first, so every module a run loads
# shares it, whichever form loaded them.
try:
    from _lib import backbone
except ImportError:  # pragma: no cover
    import backbone  # type: ignore[no-redef]

#: The heading directly above the region an earlier run of these commands wrote into
#: a description: no command writes it (DEC-065 point 1), and each finds and strips it.
HEADING = "## Documentation this change affects"
#: The heading a still earlier run wrote above the region, stripped with it as well.
FORMER_HEADING = "## Friction answers"
#: Sentinels — MUST match body-format.yaml `friction_answers_marker`. The start
#: marker an earlier run wrote carries the head the list was for and the merge-base
#: it was taken against.
MARKER_START = "<!-- pkit-friction-answers:start"
MARKER_END = "<!-- pkit-friction-answers:end -->"
_START_LINE = re.compile(r"^<!-- pkit-friction-answers:start(?:\s[^\n]*)?-->$")


def _heading_line(*headings: str) -> re.Pattern[str]:
    """Any of `headings` as a line of its own, however a hand spaced or cased it."""
    words = "|".join(
        r"[ \t]+".join(re.escape(word) for word in heading.removeprefix("## ").split())
        for heading in headings
    )
    return re.compile(rf"^ {{0,3}}##[ \t]+(?:{words})[ \t]*#*[ \t]*$", re.IGNORECASE)


#: The region's heading as a line — its own, or the one a still earlier run wrote.
_HEADING_LINE = _heading_line(HEADING, FORMER_HEADING)
#: A heading that ends a section: an ATX heading of level one or two.
_SECTION_END = re.compile(r"^ {0,3}#{1,2}(?:[ \t]|$)")
#: A fenced code block's opening line; a heading inside one is no heading.
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")

#: The version of `pkit friction check --json` this module reads; a document of
#: another is unreadable here, never misread.
SCHEMA_VERSION = 1
#: How long the change check may run before its answer is given up on.
TIMEOUT = 600
#: The backbone's command, as a capability's script runs it, and the
#: environment both runs of the check add: routing off (the module docstring).
PKIT = ("pkit",)
UNROUTED = {"PKIT_NO_ROUTE": "1"}
SHORT = 7
#: The backbone's refusal to run an anchor's resolver from a working tree that
#: is not the commit `--head` names: the one failure a temporary checkout of
#: the head answers. The backbone owns the sentence — its change check's
#: `--head` refusal (the CLI README, "Friction checks", `--head`) — and this is
#: the part of it that says where to run from.
RESOLVER_REFUSAL = "Run from a checkout at"

#: What the change check is asked about, read at one commit through the
#: backbone's discovery (`pkit friction artefacts --json --at <rev>`): the one
#: reading of the friction settings a capability's script makes, which never
#: re-reads the configuration itself (the CLI README, "friction artefacts").
ARTEFACTS = ("friction", "artefacts", "--json", "--at")
#: Whether what changed between two heads lies inside answer files the change adds, a
#: clean merge of the base counting as none, as the backbone answers it (`pkit friction
#: since`, the CLI README, "friction since"): this capability never reads an answer itself.
SINCE = ("friction", "since")
#: The version of `pkit friction since --json` this module reads, versioned apart from
#: the change check's document; a document of another is no answer, never misread.
#: Version 2 counts answer files the change adds, where version 1 counted the
#: artefacts' blocks (ADR-068 point 5).
SINCE_SCHEMA_VERSION = 2
#: Where a friction setting's change is said to be, in a refusal.
SETTINGS_WHERE = "the friction settings"


# --- the friction settings ----------------------------------------------------


@dataclass(frozen=True)
class Setting:
    """One change to what the change check is asked about: what changed, and its
    value where the head left its base and at the head, each a list of texts.
    The friction settings decide what the check asks — a change that empties the
    places leaves it dormant, one that excludes an artefact's file leaves the
    artefact out — so a change to them is told with the answers (DEC-065
    point 4)."""

    key: str
    before: tuple[str, ...]
    after: tuple[str, ...]


#: The two settings a change can alter, as the person is told them: the places the
#: change check reads, and — of the files whose standing changed — those
#: `friction.exclude` leaves out.
PLACES = "Checked locations"
EXCLUDED = "Documents excluded from checking"


def settings_change(merge_base: str, head: str) -> tuple[Setting, ...] | str:
    """How what the change check is asked about differs between `merge_base` and
    `head` — the places it reads, the project's and every capability's, and the
    files `friction.exclude` leaves out of those both commits hold — or why it
    could not be read. Read through the backbone at each commit, from git
    objects, as the change check reads each side's own settings."""
    if not merge_base:
        return "the change check named no commit the head left its base at"
    before = _discovery_at(merge_base)
    if isinstance(before, str):
        return before
    after = _discovery_at(head)
    if isinstance(after, str):
        return after
    found: list[Setting] = []
    places = (_places(before), _places(after))
    if places[0] != places[1]:
        found.append(Setting(PLACES, *places))
    standing = (_standing(before), _standing(after))
    changed = {
        path
        for path in standing[0].keys() & standing[1].keys()
        if standing[0][path] != standing[1][path]
    }
    if changed:
        found.append(
            Setting(
                EXCLUDED,
                tuple(sorted(path for path in changed if standing[0][path])),
                tuple(sorted(path for path in changed if standing[1][path])),
            )
        )
    return tuple(found)


def _discovery_at(commit: str) -> Mapping[str, Any] | str:
    """The backbone's discovery at `commit`, run as the change check is (unrouted),
    or why it could not be read."""
    command = f"`pkit friction artefacts --json --at {commit}`"
    try:
        proc = backbone.run(
            [*PKIT, *ARTEFACTS, commit],
            env={**os.environ, **UNROUTED},
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT,
        )
    except FileNotFoundError as exc:
        return f"{command}: `pkit` is not on PATH ({exc})"
    except subprocess.TimeoutExpired:
        return f"{command}: it did not answer within {TIMEOUT}s"
    except OSError as exc:
        return f"{command}: it could not be run ({exc})"
    said = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()]
    if proc.returncode != 0:
        return f"{command}: it exited {proc.returncode}" + (f": {said[-1]}" if said else "")
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        return f"{command}: its answer is not JSON"
    if not isinstance(document, dict) or document.get("schema_version", 1) != SCHEMA_VERSION:
        return f"{command}: its answer is not a document of version {SCHEMA_VERSION}"
    return document


def _places(document: Mapping[str, Any]) -> tuple[str, ...]:
    """Every place discovery reads, in walk order: its path, and who declares it
    where that is not the project, or why it is skipped."""
    out: list[str] = []
    for place in document.get("places") or []:
        place = _mapping(place)
        text = str(place.get("path") or place.get("written") or "?")
        source = str(place.get("source") or "")
        notes = [source] if source and source != "project" else []
        skipped = _mapping(place.get("skipped")).get("reason")
        notes += [f"skipped: {skipped}"] if skipped else []
        out.append(text + (f" ({', '.join(notes)})" if notes else ""))
    return tuple(out)


def _standing(document: Mapping[str, Any]) -> dict[str, bool]:
    """Each file discovery read, and whether `friction.exclude` leaves it out."""
    return {
        str(_mapping(item).get("path")): bool(_mapping(item).get("excluded"))
        for item in document.get("files") or []
        if _mapping(item).get("path")
    }


# --- deriving ----------------------------------------------------------------


@dataclass(frozen=True)
class Derivation:
    """The change check's document at one head and the friction settings the
    change alters, or why they could not be read. `needs_checkout` says `problem`
    is the backbone's refusal to run an anchor's resolver away from the head, kept
    because the caller asked for no temporary checkout (`from_checkout=False`)."""

    head: str
    document: Mapping[str, Any] | None = None
    problem: str | None = None
    answers: tuple[Mapping[str, Any], ...] = field(default=())
    settings: tuple[Setting, ...] = field(default=())
    needs_checkout: bool = False

    @property
    def listed(self) -> bool:
        """Whether the change check lists anything for the change: answers it
        wrote, or friction settings it alters."""
        return bool(self.answers or self.settings)

    @property
    def unreadable(self) -> tuple[str, ...]:
        """The head's files whose front matter does not parse: not read for answers."""
        found = (self.document or {}).get("unreadable")
        return tuple(str(path) for path in found) if isinstance(found, list) else ()

    @property
    def merge_base(self) -> str:
        """The commit the head left its base at (the check's `base.commit`)."""
        return str(_mapping((self.document or {}).get("base")).get("commit") or "")

    @property
    def tip(self) -> str:
        """The base's commit the check read (`base.tip`)."""
        return str(_mapping((self.document or {}).get("base")).get("tip") or "")

    @property
    def outdated(self) -> bool:
        """The base moved on after the head left it (the check's `base.outdated`)."""
        return bool(_mapping((self.document or {}).get("base")).get("outdated"))


@dataclass(frozen=True)
class Source:
    """Where a pull request's head is fetched from, where this clone lacks it: a
    remote, and a ref in the repository it names. For a pull request from the base's
    own repository, the remote its branch is pushed to and the branch. For one from a
    fork, the base's remote, as `_refresh_base` resolves it, and the ref the base
    repository keeps for the pull request: the fork is a repository this clone may
    name no remote for."""

    remote: str
    ref: str


def pull_request_source(
    branch: str, number: int, *, cross_repository: bool, base: str, remote: str | None = None
) -> Source:
    """The `Source` of pull request `number`, opened from `branch` into the branch
    `base`. From a fork: the base's remote (`base_remote`) and `refs/pull/<number>/head`.
    Otherwise: `remote`, else the remote the branch is pushed to (`branch_remote`), and
    the branch."""
    if cross_repository:
        return Source(base_remote(base), f"refs/pull/{number}/head")
    return Source(remote or branch_remote(branch), f"refs/heads/{branch}")


def base_remote(base: str) -> str:
    """The remote the branch `base` is fetched from, as `_refresh_base` resolves it,
    and `origin` where it resolves to no remote's branch, as `branch_remote` falls
    back."""
    try:
        found = default_branch.check_base(base)
    except default_branch.Unanswered:
        return "origin"
    remote = _remote_branch(found)
    return remote[0] if remote is not None else "origin"


def _remote_branch(found: default_branch.Base) -> tuple[str, str] | None:
    """The remote and the branch of a base the backbone resolved to a remote-tracking
    reference, or None for any other base."""
    if found.resolved != "remote":
        return None
    remote, slash, branch = found.ref.partition("/")
    return (remote, branch) if slash and remote and branch else None


def branch_remote(branch: str) -> str:
    """The remote `branch` is pushed to — its push remote, else the remote it
    tracks — and `origin` when it names none, as start-work resolves a branch
    (COR-054 point 2)."""
    for atom in ("push:remotename", "upstream:remotename"):
        remote = _git("for-each-ref", f"--format=%({atom})", f"refs/heads/{branch}").stdout
        if remote.strip() and remote.strip() != ".":
            return remote.strip()
    return "origin"


def has_commit(oid: str) -> bool:
    """Whether this clone holds commit `oid`."""
    return _git("cat-file", "-e", f"{oid}^{{commit}}").returncode == 0


def fetch_head(head: str, source: Source) -> str | None:
    """Fetch commit `head` from `source` where this clone lacks it: why it is still
    missing, or None."""
    if has_commit(head):
        return None
    proc = _git("fetch", "--quiet", source.remote, source.ref)
    if has_commit(head):
        return None
    said = (proc.stderr or "").strip().splitlines()
    return f"the head {head[:SHORT]} is not in this clone, and fetching {source.ref} from " + (
        f"{source.remote} failed: {said[-1]}" if said else f"{source.remote} did not bring it"
    )


def derive(
    head: str, base: str, *, source: Source | None = None, from_checkout: bool = True
) -> Derivation:
    """The change check's document for commit `head` against the branch `base` —
    the pull request's, named always — as `checked` gives it, and the friction
    settings the change alters.

    Never a pass on a guess: what makes `checked` unreadable, and settings that
    cannot be read, make the derivation unreadable, with why."""
    found = checked(head, base, source=source, from_checkout=from_checkout)
    if found.document is None:
        return found
    settings = settings_change(found.merge_base, head)
    if isinstance(settings, str):
        return Derivation(head, problem=settings)
    return replace(found, settings=settings)


def checked(
    head: str, base: str, *, source: Source | None = None, from_checkout: bool = True
) -> Derivation:
    """The change check's document for commit `head` against the branch `base`, the
    base fetched first where it is a remote's, and `head` from `source` where this
    clone lacks it. It reads no friction settings, for a reader that needs only the
    answers.

    Run from the working directory with `--head`, which reads the commit from git
    objects. A resolver of a registered anchor kind runs only from a checkout at
    the commit, and the check refuses so elsewhere: on that refusal alone the
    check runs again from a temporary checkout of `head`, removed afterwards; any
    other failure is kept as it is. Never a pass on a guess: a base or a head that
    could not be fetched, no document, and a document of another version or
    without `answers` all make the derivation unreadable, with why.

    That second run starts the resolvers `head` holds, under this account, so it is
    code from the pull request's head. A reader anyone may run on a head they have
    not read passes `from_checkout=False`: the refusal is then kept, and the
    derivation says so (`needs_checkout`)."""
    problem = _refresh_base(base)
    if problem is None and source is not None:
        problem = fetch_head(head, source)
    if problem is not None:
        return Derivation(head, problem=problem)
    found = _run_check(head, base, cwd=None)
    if isinstance(found, _NoDocument) and found.elsewhere:
        if not from_checkout:
            return Derivation(head, problem=found.why, needs_checkout=True)
        with _checkout(head) as (path, why_not):
            if path is None:
                found = _NoDocument(
                    f"{found.why}; a checkout at {head[:SHORT]} to run it from failed: {why_not}"
                )
            else:
                found = _run_check(head, base, cwd=path)
    if isinstance(found, _NoDocument):
        return Derivation(head, problem=found.why)
    return Derivation(head, document=found, answers=tuple(_entries(found)))


def refresh_base(base: str) -> str | None:
    """Fetch `base` where it is a remote's, as `derive` does before the change check
    reads it: why not, or None. Another reader of the change against that base, such
    as the accepted records it alters (`accepted_records`), fetches it the same way."""
    return _refresh_base(base)


def _refresh_base(base: str) -> str | None:
    """Fetch the base the check will read where it is a remote's; why not, or None."""
    try:
        found = default_branch.check_base(base)
    except default_branch.Unanswered as exc:
        return str(exc)
    if found.resolved != "remote":
        return None
    named = _remote_branch(found)
    if named is None:
        return f"the base {found.ref} names no remote's branch to fetch"
    remote, branch = named
    proc = _git("fetch", "--quiet", remote, branch)
    if proc.returncode != 0:
        said = (proc.stderr or "").strip().splitlines()
        return f"the base {found.ref} could not be fetched" + (f": {said[-1]}" if said else "")
    return None


@dataclass(frozen=True)
class _NoDocument:
    """Why the check gave no document; `elsewhere` when it refused only because
    the working directory is not a checkout at the head (`RESOLVER_REFUSAL`)."""

    why: str
    elsewhere: bool = False


def written(base: str) -> Derivation:
    """The change check's document for the change from the branch `base` to the head,
    as the project's gate runs the check: from the working directory, with no
    `--head`, so the backbone reads HEAD and `$PKIT_CHECK_HEAD` as that line does
    (ADR-068 point 6). Nothing is fetched: the base is read as it stands. A failure
    is kept as it is, never a pass; the head is named `HEAD`. Unlike `derive`, it
    makes no second run from a temporary checkout: run at the head, the check has no
    cause to refuse an anchor's resolver away from it, and a refusal is a failure."""
    found = _run_check(None, base, cwd=None)
    if isinstance(found, _NoDocument):
        return Derivation("HEAD", problem=found.why)
    return Derivation("HEAD", document=found, answers=tuple(_entries(found)))


def _run_check(
    head: str | None, base: str, *, cwd: Path | None, own_head: str | None = None
) -> Mapping[str, Any] | _NoDocument:
    """The check's document at `head` — the working directory's, where None — or why
    there is none. Enforcing mode exits 1 on friction and still prints its document,
    so exit 0 and 1 both carry one. `own_head`, where given, is the change's own head
    the check judges what each answer read against (`PKIT_CHECK_HEAD`): a parent of
    the commit the working directory is at, such as a pull request's head under a
    merge."""
    named = [] if head is None else ["--head", head]
    argv = [*PKIT, "friction", "check", "--json", "--base", base, *named]
    command = f"`{' '.join(argv)}`"
    own = {} if own_head is None else {OWN_HEAD: own_head}
    try:
        proc = backbone.run(
            argv,
            cwd=cwd,
            env={**os.environ, **UNROUTED, **own},
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT,
        )
    except FileNotFoundError as exc:
        return _NoDocument(f"{command}: `pkit` is not on PATH ({exc})")
    except subprocess.TimeoutExpired:
        return _NoDocument(f"{command}: it did not answer within {TIMEOUT}s")
    except OSError as exc:
        return _NoDocument(f"{command}: it could not be run ({exc})")
    said = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()]
    why = f"it exited {proc.returncode}" + (f": {said[-1]}" if said else "")
    if proc.returncode not in (0, 1):
        return _NoDocument(f"{command}: {why}")
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        elsewhere = RESOLVER_REFUSAL in " ".join((proc.stderr or "").split())
        return _NoDocument(f"{command}: {why}, with no JSON document", elsewhere=elsewhere)
    if not isinstance(document, dict):
        return _NoDocument(f"{command}: its answer is not a document")
    version = document.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        return _NoDocument(
            f"{command}: it answered schema_version {version!r}; this reads {SCHEMA_VERSION}"
        )
    if not isinstance(document.get("answers"), list):
        return _NoDocument(
            f"{command}: its document lists no answers — the backbone predates the list"
        )
    return document


# --- a later head an authorisation covers ------------------------------------------


@dataclass(frozen=True)
class Coverage:
    """The backbone's answer for two heads of a pull request: whether every change from
    `since` to `head` lies inside answer files the change adds, a clean merge of the
    base counting as none (DEC-055 point 3). `outside` names each change that does not,
    a line each, and `problem` why the answer could not be read, which is never a pass."""

    since: str = ""
    head: str = ""
    covered: bool = False
    #: How many answer files the change adds changed.
    inside: int = 0
    outside: tuple[str, ...] = ()
    problem: str | None = None


def covers(since: str, head: str, base: str) -> Coverage:
    """Whether the changes from commit `since` to commit `head` lie only inside answer
    files the change adds, a clean merge of the branch `base` counting as none, as the
    backbone answers it (`pkit friction since <since> --head <head> --base <base>
    --json`, run unrouted as the change check is). The base is fetched first where it
    is a remote's, so a merge of it is told from the author's own commits. This
    capability never reads an answer itself (DEC-055 point 3)."""
    problem = _refresh_base(base)
    if problem is not None:
        return Coverage(problem=problem)
    command = f"`pkit friction since {since} --head {head} --base {base} --json`"
    try:
        proc = backbone.run(
            [*PKIT, *SINCE, since, "--head", head, "--base", base, "--json"],
            env={**os.environ, **UNROUTED},
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT,
        )
    except FileNotFoundError as exc:
        return Coverage(problem=f"{command}: `pkit` is not on PATH ({exc})")
    except subprocess.TimeoutExpired:
        return Coverage(problem=f"{command}: it did not answer within {TIMEOUT}s")
    except OSError as exc:
        return Coverage(problem=f"{command}: it could not be run ({exc})")
    said = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()]
    if proc.returncode != 0:
        return Coverage(
            # The backbone's message can quote a path the author chose: escaped.
            problem=f"{command}: it exited {proc.returncode}"
            + (f": {shown(said[-1])}" if said else "")
        )
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        return Coverage(problem=f"{command}: its answer is not JSON")
    if not isinstance(document, dict) or document.get("schema_version") != SINCE_SCHEMA_VERSION:
        return Coverage(
            problem=f"{command}: its answer is not a document of version {SINCE_SCHEMA_VERSION}"
        )
    return _coverage(document, command)


def _coverage(document: Mapping[str, Any], command: str) -> Coverage:
    """The backbone's document read, every field it rests on checked: a document missing
    one is no answer."""
    since, head = document.get("since"), document.get("head")
    covered, inside, outside = (document.get(k) for k in ("all_inside", "inside", "outside"))
    if not (
        isinstance(since, str)
        and isinstance(head, str)
        and isinstance(covered, bool)
        and isinstance(inside, list)
        and isinstance(outside, list)
    ):
        return Coverage(problem=f"{command}: its document lacks what an answer needs")
    lines = [
        f"{shown(str(_mapping(o).get('path') or 'the merge'))} "
        f"({str(_mapping(o).get('commit'))[:SHORT]}: {shown(str(_mapping(o).get('why')))})"
        for o in outside
    ]
    reason = document.get("reason")
    if isinstance(reason, str) and reason:
        lines.insert(0, shown(reason))
    if covered != (not lines and reason is None):
        return Coverage(
            problem=f"{command}: its answer and the changes it names disagree, so it is no answer"
        )
    return Coverage(since, head, covered, len(inside), tuple(lines))


# --- the merge as it would land ------------------------------------------------------

#: The variable that names the change's own head to the change check, where the working
#: tree is a merge of it (the CLI README, "Friction checks", `PKIT_CHECK_HEAD`).
OWN_HEAD = "PKIT_CHECK_HEAD"
#: The finding kinds the change check fails on in enforcing mode (the CLI README,
#: "Friction checks", "Modes"): the ones a refused merge names. A kind the check fails
#: on that is missing here still refuses the merge, through the document's `failed`.
FAILING = frozenset(
    {
        "friction",
        "bump",
        "dead-anchor",
        "unresolved-kind",
        "no-answer",
        "unrevisited",
        "answer-file-rewritten",
        "prune-mixed",
        "read-incomplete",
        "answers-nothing",
    }
)
#: Who the merge is made by: it reaches no branch, so it names no person, and git needs
#: no identity configured to build it.
_MERGE_IDENTITY = {
    "GIT_AUTHOR_NAME": "pkit land-work",
    "GIT_AUTHOR_EMAIL": "land-work@pkit.invalid",
    "GIT_COMMITTER_NAME": "pkit land-work",
    "GIT_COMMITTER_EMAIL": "land-work@pkit.invalid",
}


@dataclass(frozen=True)
class Merged:
    """The change check on the merge of a pull request's head with its base's tip, as
    the base stands once fetched (DEC-055 point 6), or why it was not run. `merge` is
    the commit the check ran at — the head itself where the head holds the tip and its
    own check read that tip — and `conflicts` the files a merge conflicts in, which
    leave nothing to check."""

    head: str
    tip: str = ""
    merge: str = ""
    document: Mapping[str, Any] | None = None
    conflicts: tuple[str, ...] = ()
    problem: str | None = None

    @property
    def failed(self) -> bool:
        """Whether the check fails at the merge, in the mode the project sets."""
        return bool((self.document or {}).get("failed"))

    @property
    def failing(self) -> tuple[Mapping[str, Any], ...]:
        """The findings at the merge of a kind the check fails on in enforcing mode, in
        its order, whatever the project's mode: in warning mode, what is reported there
        for information."""
        findings = (self.document or {}).get("findings")
        return tuple(
            f
            for f in (findings if isinstance(findings, list) else [])
            if isinstance(f, Mapping) and f.get("kind") in FAILING
        )

    @property
    def refused(self) -> tuple[Mapping[str, Any], ...]:
        """The findings the check fails on at the merge, in its order; none where it
        does not fail."""
        return self.failing if self.failed else ()


def merged(head: str, base: str, *, checked: Mapping[str, Any] | None = None) -> Merged:
    """The change check on the merge of commit `head` with the branch `base` as it
    stands: the base fetched first where it is a remote's, its tip read again through
    the backbone (COR-054 point 5), the merge built as git merges the two, and the
    check run on it against the tip, as the checks on a pull request run it — from a
    checkout of the merge, the head named as the change's own head (COR-062 point 4,
    `PKIT_CHECK_HEAD`). DEC-055 point 6.

    Nothing the person works on is touched: the merge is a commit object of its own,
    on no branch (`git merge-tree --write-tree`, `git commit-tree`), never signed —
    `git commit-tree` signs only when asked to — and the checkout is a temporary one,
    removed afterwards. `checked`, the change check's document at the head, serves
    where the head holds the tip it read and that tip is the one the fetch finds: the
    merge is then the head, and its check is the head's. A merge that conflicts names
    its files and runs no check. Never a pass on a guess: a base that cannot be
    fetched or read, a merge git cannot build, and a check that gives no document all
    give the problem."""
    problem = _refresh_base(base)
    if problem is not None:
        return Merged(head, problem=problem)
    try:
        tip = default_branch.branch(base).tip
    except default_branch.Unanswered as exc:
        return Merged(head, problem=str(exc))
    if not tip:
        return Merged(head, problem=f"the base {base} names no commit")
    read = _mapping(_mapping(checked).get("base"))
    if checked is not None and read.get("tip") == tip and read.get("outdated") is False:
        return Merged(head, tip=tip, merge=head, document=checked)
    built = _build_merge(head, tip)
    if built.problem is not None or built.conflicts:
        return Merged(head, tip=tip, conflicts=built.conflicts, problem=built.problem)
    with _checkout(built.merge) as (path, why_not):
        if path is None:
            why = f"a checkout of the merge {built.merge[:SHORT]} failed: {why_not}"
            return Merged(head, tip=tip, merge=built.merge, problem=why)
        found = _run_check(None, tip, cwd=path, own_head=head)
    if isinstance(found, _NoDocument):
        return Merged(head, tip=tip, merge=built.merge, problem=found.why)
    return Merged(head, tip=tip, merge=built.merge, document=found)


@dataclass(frozen=True)
class _Built:
    """The merge `_build_merge` built, the files it conflicts in, or why git could not
    build it."""

    merge: str = ""
    conflicts: tuple[str, ...] = ()
    problem: str | None = None


def _build_merge(head: str, tip: str) -> _Built:
    """The merge of `head` with `tip`, as git merges two commits, recorded as a commit
    on no branch whose parents are the tip and the head."""
    tree = _git("merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", tip, head)
    fields = [field for field in tree.stdout.split("\0") if field]
    if tree.returncode == 1 and len(fields) > 1:
        return _Built(conflicts=tuple(dict.fromkeys(fields[1:])))
    if tree.returncode != 0 or not fields:
        said = (tree.stderr or "").strip().splitlines()
        why = f"git could not merge {head[:SHORT]} with {tip[:SHORT]}"
        return _Built(problem=why + (f": {said[-1]}" if said else ""))
    made = subprocess.run(
        [
            "git",
            "commit-tree",
            fields[0],
            "-p",
            tip,
            "-p",
            head,
            "-m",
            "The merge land-work checks",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **_MERGE_IDENTITY},
    )
    merge = made.stdout.strip()
    if made.returncode != 0 or not merge:
        said = (made.stderr or "").strip().splitlines()
        why = f"git could not record the merge of {head[:SHORT]} with {tip[:SHORT]}"
        return _Built(problem=why + (f": {said[-1]}" if said else ""))
    return _Built(merge=merge)


@contextlib.contextmanager
def _checkout(head: str) -> Iterator[tuple[Path | None, str]]:
    """A temporary detached checkout of `head` (a linked worktree), removed on exit
    — a termination signal included. Only the worktree this run added is removed,
    with the directory it sits in; nothing else of the repository's is touched."""
    scratch = Path(tempfile.mkdtemp(prefix="pkit-friction-answers-"))
    path = scratch / "checkout"
    with _terminating_unwinds():
        added = _git("worktree", "add", "--detach", "--quiet", str(path), head)
        admin = _admin_dir(path) if added.returncode == 0 else None
        try:
            if added.returncode != 0:
                said = (added.stderr or "").strip().splitlines()
                yield None, said[-1] if said else f"git worktree add exited {added.returncode}"
            else:
                yield path, ""
        finally:
            if added.returncode == 0:
                removed = _git("worktree", "remove", "--force", str(path))
                if removed.returncode != 0 and admin is not None:
                    shutil.rmtree(admin, ignore_errors=True)
            shutil.rmtree(scratch, ignore_errors=True)


def _admin_dir(path: Path) -> Path | None:
    """The repository's record of the linked worktree at `path` (`.git/worktrees/<name>`),
    as the worktree's `.git` file names it."""
    try:
        pointer = (path / ".git").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    gitdir = pointer.removeprefix("gitdir:").strip()
    if not pointer.startswith("gitdir:") or not gitdir:
        return None
    return Path(gitdir) if Path(gitdir).is_absolute() else path / gitdir


@contextlib.contextmanager
def _terminating_unwinds() -> Iterator[None]:
    """While inside, a termination signal (SIGTERM) raises `SystemExit`, so the
    `finally` that removes a temporary checkout runs; the handler before is put
    back on the way out. Off the main thread no handler can be set."""

    def unwind(signum: int, _frame: Any) -> None:
        raise SystemExit(128 + signum)

    try:
        before = signal.signal(signal.SIGTERM, unwind)
    except ValueError:  # not the main thread
        yield
        return
    try:
        yield
    finally:
        # None: the handler before was not set from Python — the default's.
        signal.signal(signal.SIGTERM, signal.SIG_DFL if before is None else before)


def _git(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], capture_output=True, text=True, check=False)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _entries(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    found = document.get("answers")
    return [entry for entry in found if isinstance(entry, Mapping)] if found else []


def listed_paths(document: Mapping[str, Any]) -> set[str]:
    """The files the answers' words are on: the file the change check names for each
    answer (`file`), which holds the deferrals a revalidation kept too. That is an
    answer file the change adds, or the artefact's own file for an answer in its
    block (COR-062 point 1). An answer it names no file for, such as a target
    revisited by changing it, counts its artefact's file."""
    found: set[str] = set()
    for entry in _entries(document):
        file = entry.get("file")
        if isinstance(file, str) and file:
            found.add(file)
        else:
            found.add(str(entry.get("location") or "").split("#", 1)[0])
    return found - {""}


# --- where the backbone keeps the answers -------------------------------------------

#: The backbone's whole-repository check, whose document gives the folder of friction
#: answers (`answers.folder`, the CLI README, "Friction checks"): the reading that
#: gives it for no one artefact.
WHOLE = ("friction", "check", "--all", "--json")

#: The folder each repository root's backbone gave, read once for a run.
_FOLDERS: dict[str, str | None] = {}


def answers_folder(root: Path, run: Any = backbone.run) -> str | None:
    """The folder the backbone keeps the friction answers in, repository-relative, as
    it gives it (`answers.folder` in `pkit friction check --all --json`, COR-062 point
    2), read at `root` once for a run, unrouted as the change check is. This capability
    never names the folder itself. None where the backbone gives none, for any reason:
    a reader then sets no path apart, which errs toward more review, never less
    (DEC-032 D5)."""
    key = str(root)
    if key not in _FOLDERS:
        _FOLDERS[key] = _folder_at(root, run)
    return _FOLDERS[key]


def _folder_at(root: Path, run: Any) -> str | None:
    try:
        proc = run(
            [*PKIT, *WHOLE],
            cwd=root,
            env={**os.environ, **UNROUTED},
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
    except ValueError:
        return None
    if not isinstance(document, Mapping) or document.get("schema_version", 1) != SCHEMA_VERSION:
        return None
    folder = _mapping(document.get("answers")).get("folder")
    if not isinstance(folder, str) or not folder.strip("/") or folder.startswith("/"):
        return None
    return folder.strip("/")


def documents(answers: Iterable[Mapping[str, Any]]) -> int:
    """How many documents `answers` are on — each answer's artefact counted once:
    a page that defers two anchors is one document the change affects."""
    return len({str(answer.get("location") or answer.get("artefact") or "?") for answer in answers})


#: How a command's output names the answers: the documents they are on.
NAME = "documents this change affects"
#: What that output calls a change to the friction settings.
CHECKED = "a change to which documents are checked"


def affected(count: int, *, settings: bool) -> str:
    """How many documents the change affects — `count`, as `documents` counts
    them — and whether it changes which are checked, as a command's line says
    it after `NAME`."""
    if not count:
        return f"none, but {CHECKED}" if settings else "none"
    return f"{count}, plus {CHECKED}" if settings else str(count)


# --- what the person is told --------------------------------------------------


def shown(text: str) -> str:
    """`text` with each character that is not printable — a control character, a
    newline, a bidirectional override, a zero-width character — written as its
    escape (`\\x1b`, `\\u202e`), as the change check's human view shows it."""
    if text.isprintable():
        return text
    return "".join(ch if ch.isprintable() else ascii(ch)[1:-1] for ch in text)


#: Each answer of the change check (`--json`'s `answer`) in plain words: whether
#: the document is still true. An answer it does not name here is shown as the
#: check gives it. The change check's own list says the same words.
LABELS = {
    "updated": "updated in this change",
    "unchanged": "still accurate",
    "deferred": "out of date, fixed later",
    "unanchored": "not tied to anything",
}
#: The answers whose words the person who authorises the merge is told (DEC-065
#: point 4): an update's sentence, and a deferral's reason.
UPDATED, DEFERRED = "updated", "deferred"
#: A reason for having no anchors (`unanchored-because`): a person's to decide,
#: since no change owes it (COR-050 point 3).
UNANCHORED = "unanchored"
#: The `answer` of a revisit entry (COR-050 point 16): a source's answer for one
#: target of its links. Its `outcome` — `updated` where the target changed in the
#: change, else `unchanged` or `deferred` — reads as `LABELS` says it, and a
#: `deferred` one leaves the target out of date until the follow-up its reason
#: names.
REVISITED = "revisited"
#: A revalidation whose outcome is neither `updated` nor `unchanged` (`answer` null).
NO_OUTCOME = "no decision recorded"
#: How a line names an answer the change check did not ask for, which a person or
#: the delegate they named decided before it was written (COR-064).
NOT_ASKED = "Not asked for by this change"
#: How a line names a document or a target left out of date (COR-050 point 3).
LEFT = "Left out of date"
#: How a line counts the files the change check could not read for answers.
UNREAD = "Files the change check could not read"
#: What an anchor of a core kind is named; an anchor of another kind is named as
#: the check names it, `kind:value`.
_ANCHOR_NOUNS = {"path": "", "record": "decision record ", "artefact": "document "}


@dataclass(frozen=True)
class _Anchor:
    """An anchor, its kind and value each shown escaped."""

    kind: str
    value: str

    @property
    def named(self) -> str:
        """The anchor as the change check names it."""
        return f"{self.kind}:{self.value}"

    def said(self) -> str:
        """The anchor in plain words: "src/cli/**", "decision record COR-050"."""
        noun = _ANCHOR_NOUNS.get(self.kind)
        return f"{noun}{self.value}" if noun is not None else self.named


def _read_anchor(value: Any) -> _Anchor | None:
    anchor = _mapping(value)
    if not anchor:
        return None
    return _Anchor(shown(str(anchor.get("kind"))), shown(str(anchor.get("value"))))


@dataclass(frozen=True)
class _Entry:
    """One answer, every text in it shown escaped. `updated`: the answer is
    `updated`, so the person is told the author's `sentence` on what changed, or
    that there is none. `asked`: the change check asked for it.

    A revisit entry (`revisit`, COR-050 point 16) is the source's answer for one
    target: `location` is the source, `label` its outcome, `target` the anchor it
    names, `links` the fields that list the target, and `deferred` whether it
    leaves the target out of date. It is never `updated`: a target revisited by
    changing it carries no author's sentence, since it is no revalidation."""

    location: str
    label: str
    anchor: _Anchor | None
    reason: str | None
    kept: tuple[tuple[_Anchor, str | None], ...]
    updated: bool = False
    sentence: str | None = None
    asked: bool = True
    revisit: bool = False
    target: _Anchor | None = None
    links: tuple[str, ...] = ()
    deferred: bool = False


def _read_entry(entry: Mapping[str, Any], sentences: Mapping[str, str] | None = None) -> _Entry:
    answer, reason = entry.get("answer"), entry.get("reason")
    kept: list[tuple[_Anchor, str | None]] = []
    for item in entry.get("kept") or []:
        words = _mapping(item).get("reason")
        held = _read_anchor(_mapping(item).get("anchor")) or _Anchor("None", "None")
        kept.append((held, shown(str(words)) if words is not None else None))
    location = shown(str(entry.get("location") or entry.get("artefact") or "?"))
    updated = answer == UPDATED
    sentence = (sentences or {}).get(location) if updated else None
    revisit = answer == REVISITED
    # A revisit's outcome is what the person is told of it, as an answer's is.
    said = entry.get("outcome") if revisit else answer
    return _Entry(
        location=location,
        label=LABELS.get(str(said), shown(str(said))) if said else NO_OUTCOME,
        anchor=_read_anchor(entry.get("anchor")),
        reason=shown(str(reason)) if reason is not None else None,
        kept=tuple(kept),
        updated=updated,
        sentence=shown(sentence) if sentence is not None else None,
        asked=entry.get("asked") is True and answer != UNANCHORED,
        revisit=revisit,
        target=_read_anchor(entry.get("target")) if revisit else None,
        links=_texts_of(entry.get("links")) if revisit else (),
        deferred=revisit and said == DEFERRED,
    )


def _texts_of(value: Any) -> tuple[str, ...]:
    """Each text of a list of the check's, shown escaped; none where it is no list."""
    return tuple(shown(str(item)) for item in value) if isinstance(value, list) else ()


def _side(values: Sequence[str]) -> str:
    """One side of a setting's change: each text, or "none"."""
    return ", ".join(shown(v) for v in values) if values else "none"


def _and(items: Sequence[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def told(
    document: Mapping[str, Any],
    settings: Sequence[Setting] = (),
    sentences: Mapping[str, str] | None = None,
    also: Sequence[str] = (),
) -> list[str]:
    """What the person who authorises the merge is told, as information, not a
    gate (DEC-065 point 4), as a terminal shows it: what changed in each `updated`
    document, in its author's sentence or that there is none; what is left out of
    date (`left_out`); each answer the change check did not ask for, and each
    reason for having no anchors, with its outcome and words, which a person or
    their delegate decided (COR-064); each friction setting the change alters; how
    many files the check could not read; each revalidation the merge would leave
    answered apart (`apart`); then `also`, what the caller adds, such as a change
    to the fixers' grant list. No other answer is told, such as a document still
    accurate."""
    out: list[str] = []
    entries = [_read_entry(e, sentences) for e in _entries(document)]
    for entry in entries:
        if entry.updated:
            said = "the pull request's author has not said"
            if entry.sentence is not None:
                said = f'"{entry.sentence}"'
            out.append(f"What changed in {entry.location}: {said}")
    out += left_out(document)
    for entry in entries:
        if not entry.asked:
            where = _late_target(entry) if entry.revisit else entry.location + _for(entry.anchor)
            out.append(f"{NOT_ASKED}: {where}, {entry.label}{_quoted(entry.reason)}")
    for setting in settings:
        out.append(f"{setting.key}: {_side(setting.before)} → {_side(setting.after)}")
    unread_files = _texts_of(document.get("unreadable"))
    if unread_files:
        out.append(f"{UNREAD}: {len(unread_files)}")
    return [*out, *apart(document), *also]


def left_out(document: Mapping[str, Any]) -> list[str]:
    """What the change leaves out of date, a line each, as `told` gives it: each
    document, with the anchor and the words of each deferral the change wrote or a
    revalidation kept, and each target of a link a `deferred` revisit entry leaves
    out of date, with the source that names it and the entry's words. The words
    name its follow-up (COR-050 points 3 and 16)."""
    out: list[str] = []
    for entry in (_read_entry(e) for e in _entries(document)):
        if entry.revisit:
            if entry.deferred:
                out.append(f"{LEFT}: {_late_target(entry)}{_quoted(entry.reason)}")
            continue
        late = [(entry.anchor, entry.reason)] if entry.label == LABELS[DEFERRED] else []
        for anchor, words in [*late, *entry.kept]:
            out.append(f"{LEFT}: {entry.location}{_for(anchor)}{_quoted(words)}")
    return out


def _for(anchor: _Anchor | None) -> str:
    """`, for changes to <anchor>`, or nothing where there is no anchor."""
    return f", for changes to {anchor.said()}" if anchor is not None else ""


def _quoted(words: str | None) -> str:
    """`: "<words>"`, or nothing where there are none."""
    return f': "{words}"' if words is not None else ""


#: What a revisit entry says where the check names no target.
A_TARGET = "a target"


def _late_target(entry: _Entry) -> str:
    """The target a revisit entry answers for, as `told` names it: `<target>, which
    <source> names through <links>`."""
    target = entry.target.said() if entry.target is not None else A_TARGET
    through = f" through {_and(list(entry.links))}" if entry.links else ""
    return f"{target}, which {entry.location} names{through}"


#: How a line names a revalidation on the base's tip that a merge would leave
#: answered apart from the change's own (COR-062 point 7).
APART = "Answered apart once merged"


def apart(document: Mapping[str, Any]) -> list[str]:
    """Each live revalidation on the base's tip that the change's answer on its
    document did not read, a line each, as the change check reports it
    (`answered_apart_at_tip`). Merged, the two are answered apart, which the
    whole-repository check reports as debt until a revalidation reads both (COR-062
    point 7). Told after the rest (`told`), as information that stops nothing
    (DEC-055 point 3). Every text is shown escaped."""
    out: list[str] = []
    found = document.get("answered_apart_at_tip")
    for item in found if isinstance(found, list) else []:
        location = shown(str(_mapping(item).get("location") or "?"))
        revalidations = _mapping(item).get("revalidations")
        for revalidation in revalidations if isinstance(revalidations, list) else []:
            said = _mapping(revalidation)
            file, at = said.get("file"), said.get("at")
            where = f" in {shown(str(file))}" if file else ""
            when = f" of {shown(str(at))}" if at else ""
            outcome = said.get("outcome")
            label = LABELS.get(str(outcome), shown(str(outcome))) if outcome else NO_OUTCOME
            words = said.get("unchanged_because")
            out.append(
                f"{APART}: {location} — the base's revalidation{where}{when}, which this "
                f"change's answer did not read. {label[:1].upper()}{label[1:]}"
                f"{_quoted(shown(str(words)) if words is not None else None)}"
            )
    return out


class Counted(NamedTuple):
    """What `told` tells, counted: the documents the change updated, the documents
    it leaves out of date — a deferral it wrote or a revalidation kept — and the
    targets of a link it leaves out of date — a `deferred` revisit entry — each
    counted once, and the answers the change check did not ask for."""

    updated: int
    left: int
    targets: int
    unasked: int = 0


def counted_told(document: Mapping[str, Any]) -> Counted:
    """How many documents the change updated, how many it leaves out of date, how
    many targets of a link it leaves out of date, and how many answers the change
    check did not ask for (`Counted`): a document by its location, a target by its
    anchor, whatever sources name it. An entry the check names no target for
    counts as one of its own, as `told` gives it a line."""
    entries = _entries(document)
    updated = {str(e.get("location") or "") for e in entries if e.get("answer") == UPDATED}
    late = {
        str(e.get("location") or "")
        for e in entries
        if e.get("answer") == DEFERRED or e.get("kept")
    }
    targets: set[tuple[str, ...]] = set()
    for index, e in enumerate(entries):
        if e.get("answer") != REVISITED or e.get("outcome") != DEFERRED:
            continue
        target = _mapping(e.get("target"))
        named = (str(target.get("kind")), str(target.get("value")))
        targets.add(named if target else ("", str(index)))
    unasked = sum(1 for e in entries if not _read_entry(e).asked)
    return Counted(len(updated), len(late), len(targets), unasked)


# --- the author's sentences ---------------------------------------------------

#: The heading of the description's section where the change's author says what
#: changed in each document the change revalidated as `updated`, one sentence
#: each (COR-050 point 3, DEC-065 point 1). It is the author's own text, kept in
#: the description; the commands read each sentence from it. MUST match
#: body-format.yaml `friction_answers_marker`'s `sentences_heading`.
SENTENCES_HEADING = "## What changed in each updated document"
_SENTENCES_LINE = _heading_line(SENTENCES_HEADING)
#: A sentence: a top-level list item, bulleted or numbered and starting in the
#: line's first column, that names the document in a code span, as the change check
#: names it, then a colon or a dash, then the sentence.
_SENTENCE_ITEM = re.compile(
    r"^(?:[-*+]|\d{1,9}[.)])[ \t]+(`+)(.+?)\1(?!`)[ \t]*(?:[:—–-][ \t]*)?(.*)$"
)
#: The form a sentence takes, as a warning names it.
SENTENCE_FORM = "- `path`: sentence"
#: The form, as a command's warning or refusal tells the author to write it.
_FORM_SAID = (
    f'"{SENTENCE_FORM}", starting in the line\'s first column, the document in a code span '
    "as the change check names it"
)
#: A closing reference in the host's grammar: one of its nine keywords, an optional
#: colon, then `#N`, `owner/repo#N` or an issue's URL, in any case. It reads wider
#: than the closing references this capability reads, since the host closes what it
#: reads: over-matching only refuses a sentence, and under-matching closes an issue
#: at merge past the checkbox gate and the cascade (DEC-065 point 5).
CLOSING_REFERENCE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*"
    r"(?:#\d+|[\w.-]+/[\w.-]+#\d+|https?://\S+?/issues/\d+)",
    re.IGNORECASE,
)
#: A thematic break: three or more of one of `-`, `*`, `_`, spaces between.
_BREAK = r" {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$"
#: A line that ends the item above it: a list item of its own, at any depth, a
#: heading, an HTML comment's opening, or a thematic break.
_ITEM_END = re.compile(
    r"^[ \t]*(?:[-*+]|\d{1,9}[.)])(?:[ \t]|$)"
    r"| {0,3}#{1,6}(?:[ \t]|$)"
    r"|[ \t]*<!--"
    rf"|{_BREAK}"
)
#: A list item that opens at a list's top level, indented by at most three
#: spaces: the indent, the bullet or number, and the whitespace after it.
_ITEM_OPENING = re.compile(r"^( {0,3})([-*+]|\d{1,9}[.)])([ \t]+|$)")
_THEMATIC_BREAK = re.compile(_BREAK)
#: An ATX heading, of any level, indented by at most three spaces.
_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
#: An HTML comment's opening at the start of a line: the lines up to its
#: closing do not render, so nothing in them is read.
_COMMENT_OPENING = re.compile(r"^[ \t]*<!--")


@dataclass(frozen=True)
class Unread:
    """A list item under `SENTENCES_HEADING` that gives no sentence: the number of
    its line in the description, and the line, shown as a terminal shows it."""

    line: int
    text: str


def _nest(opening: re.Match[str]) -> int:
    """The column an item's content starts in: an item indented that far, or
    further, is nested under it."""
    indent, marker, space = opening.groups()
    return len(indent) + len(marker) + (min(len(space), 4) if space else 1)


def _closes(line: str, fence: str) -> bool:
    """Whether `line` closes a fenced block opened with `fence`: that character, at
    least as many times, and nothing else."""
    text = line.strip()
    return text.startswith(fence) and not text.strip(fence[0])


def _read_sentences(body: str) -> tuple[dict[str, str], list[Unread]]:
    """The sentences the author wrote under `SENTENCES_HEADING`, and each list item
    there that gives none (`sentences`, `unread`). One reading for both, so a
    warning names exactly the items the reading leaves out. A list an earlier run
    wrote reads as a blank line, so its lines keep their numbers. An item is at
    the list's top level unless it is indented as far as the content of the
    top-level item above it, in the same list. A heading, an HTML comment, a
    thematic break, a fence, or a paragraph after a blank line, indented less
    than that content, ends the list."""
    lines_ = _split(provenance.strip_footer(body))
    listed = _covered(_spans(lines_))
    found: dict[str, str] = {}
    unread_: list[Unread] = []
    inside = comment = blank = False
    fence: str | None = None
    current: list[str] | None = None
    key, at = "", 0
    nest: int | None = None

    def close() -> None:
        nonlocal current
        if current is None:
            return
        words = " ".join(" ".join(current).split())
        if not key or not words:
            unread_.append(Unread(at, shown(lines_[at - 1])))
        elif key not in found:
            found[key] = words
        current = None

    for number, raw in enumerate(lines_, start=1):
        line = "" if number - 1 in listed else raw
        if fence is not None:
            fence = None if _closes(line, fence) else fence
            continue
        if comment:
            comment = "-->" not in line
            continue
        # A line indented less than the content of the top-level item above it,
        # that is no item of the list, ends the list.
        outdented = nest is not None and len(line) - len(line.lstrip()) < nest
        opened = _FENCE.match(line)
        if opened is not None or _COMMENT_OPENING.match(line):
            close()
            nest = None if outdented else nest
            if opened is not None:
                fence = opened.group(1)
            else:
                comment = "-->" not in line.split("<!--", 1)[1]
            continue
        if _SENTENCES_LINE.match(line):
            close()
            inside, nest = True, None
            continue
        if _SECTION_END.match(line):
            close()
            inside = False
            continue
        if not inside:
            continue
        item = _SENTENCE_ITEM.match(line)
        opening = None if _THEMATIC_BREAK.match(line) else _ITEM_OPENING.match(line)
        if opening is not None and opening.group(1) and nest is not None:
            nested = len(opening.group(1)) >= nest
        else:
            nested = False
        if item is not None:
            close()
            key, at, current = item.group(2).strip(), number, [item.group(3)]
        elif opening is not None and not nested:
            close()
            unread_.append(Unread(number, shown(line)))
        elif not line.strip() or _ITEM_END.match(line):
            close()
            if outdented and (_HEADING.match(line) or _THEMATIC_BREAK.match(line)):
                nest = None
        elif current is not None:
            current.append(line.strip())
        elif blank and outdented:
            nest = None  # a paragraph of its own
        if opening is not None and not nested:
            nest = _nest(opening)
        blank = not line.strip()
    close()
    return found, unread_


def sentences(body: str) -> dict[str, str]:
    """The sentences the change's author wrote under `SENTENCES_HEADING`, by the
    document each names — its location, as the change check names it. Read from
    `body` without a list an earlier run wrote, its provenance footer, fenced code
    blocks and HTML comments. An item runs on over the lines under it up to a blank
    line, another list item, a heading, an HTML comment, a thematic break or a
    fence, its whitespace folded. Of two items for one document, the first."""
    return _read_sentences(body)[0]


def unread(body: str) -> list[Unread]:
    """Each list item under `SENTENCES_HEADING` in `body` that `sentences` reads no
    sentence from, in order: a top-level item that does not start in the line's
    first column with its document in a code span — one naming it in bold, or with
    no code span, or one in a list indented whole — and one that names a document
    but gives no words. An item nested under another is not one, nor is anything
    inside an HTML comment."""
    return _read_sentences(body)[1]


def unread_warning(item: Unread) -> str:
    """What a command says of `item`: the line it is on, and the form a sentence
    takes."""
    return (
        f"line {item.line} of the description, under `{SENTENCES_HEADING}`, is not read as "
        f'a sentence: "{item.text}" — write it as {_FORM_SAID}'
    )


def unsaid_message(location: str) -> str:
    """What a command that refuses or warns says of `location`, a document the change
    check marks `updated` at the pull request's head with no sentence in the
    description: the document, and the form a sentence takes."""
    return (
        f"{location} is updated in this change, and the description gives no sentence on "
        f"what changed in it — under `{SENTENCES_HEADING}`, write one on a line of its own "
        f"as {_FORM_SAID}"
    )


def updated_in(document: Mapping[str, Any]) -> list[str]:
    """Each document the change check's `document` marks `updated`, as the check
    names it and in its order. A target revisited by changing it is none: no
    revalidation carries a sentence there."""
    entries = (e for e in _entries(document) if e.get("answer") == UPDATED)
    return list(dict.fromkeys(_read_entry(e).location for e in entries))


def unlisted(document: Mapping[str, Any], sentences_: Mapping[str, str]) -> list[str]:
    """Each document `sentences_` gives a sentence for that `document` does not mark
    `updated`, in the sentences' order: no reviewer checks such a sentence, so the
    author removes it (DEC-055 point 3, DEC-065 point 3)."""
    updated = set(updated_in(document))
    return [key for key in sentences_ if key not in updated]


def unlisted_warning(location: str, head: str, pr_number: int | None = None) -> str:
    """What a command that derives the answers at `head` says of `location`, a document
    the author gives a sentence for that the change check does not mark `updated`:
    no reviewer checks the sentence, and the edit that removes it."""
    edit = "`edit-pr`" if pr_number is None else f"`edit-pr {pr_number} --body-file <file>`"
    return (
        f"{location} has a sentence under `{SENTENCES_HEADING}`, and the change check at "
        f"{head[:SHORT]} does not mark it updated, so no reviewer checks the sentence — "
        f"remove it from the description with {edit}"
    )


def unsaid(document: Mapping[str, Any], sentences_: Mapping[str, str]) -> list[str]:
    """Each `updated` document the author wrote no sentence for, in the change check's
    order."""
    entries = [_read_entry(e, sentences_) for e in _entries(document)]
    return list(dict.fromkeys(e.location for e in entries if e.updated and e.sentence is None))


def closing_references(sentences_: Mapping[str, str]) -> list[tuple[str, str]]:
    """Each of `sentences_` that reads as a closing reference, in order, as (the
    document it is for, the words that read so). A sentence stays in the description
    and the squash commit, where the host's parser reads it, and nothing here can
    make that parser skip a section (DEC-065 point 5)."""
    found = ((key, CLOSING_REFERENCE.search(shown(words))) for key, words in sentences_.items())
    return [(key, match.group(0)) for key, match in found if match is not None]


def closing_message(location: str, words: str) -> str:
    """What a command that refuses says of the sentence on `location`, whose `words`
    read as a closing reference."""
    return (
        f"the sentence on what changed in {location}, under `{SENTENCES_HEADING}`, reads as "
        f"a closing reference ({words}): the host would close an issue with it at merge — "
        "reword it"
    )


# --- the region in a description --------------------------------------------

#: What a command says of a start marker with no end marker after it: what follows
#: may be the author's, so nothing is removed (DEC-065 point 1).
ORPHAN_WARNING = (
    f"the description holds a line `{MARKER_START} …` with no end marker after it, so it "
    "is left as it is: if it is what remains of a list an earlier run wrote, remove it "
    "with `edit-pr`"
)


def _is_start(line: str) -> bool:
    return bool(_START_LINE.match(line.strip()))


def _is_end(line: str) -> bool:
    return line.strip() == MARKER_END


@dataclass(frozen=True)
class _Span:
    """The lines of a body a command wrote: `first`, the heading directly above the
    start marker or the marker itself, through `last`, the end marker."""

    first: int
    last: int


def _spans(lines_: Sequence[str]) -> list[_Span]:
    """Every region a command wrote that `lines_` carries, in order: a start marker
    through the first end marker after it with no start marker between, and the
    heading directly above it, blank lines between. Markers are whole lines wherever
    they stand, a fenced code block included, so a region is never hidden by a fence
    left open above it. A marker with no partner makes no region."""
    spans: list[_Span] = []
    start: int | None = None
    for index, line in enumerate(lines_):
        if _is_start(line):
            start = index
        elif _is_end(line) and start is not None:
            spans.append(_Span(_opening(lines_, start), index))
            start = None
    return spans


def _opening(lines_: Sequence[str], start: int) -> int:
    """The line a region whose start marker is at `start` opens on: the heading
    directly above it, blank lines between, or the marker."""
    above = start - 1
    while above >= 0 and not lines_[above].strip():
        above -= 1
    return above if above >= 0 and _HEADING_LINE.match(lines_[above]) else start


def _covered(spans: Iterable[_Span]) -> set[int]:
    """The numbers of the lines `spans` cover."""
    return {index for span in spans for index in range(span.first, span.last + 1)}


def _split(body: str) -> list[str]:
    return body.replace("\r\n", "\n").split("\n")


def has_list(body: str) -> bool:
    """Whether `body` carries a region a command wrote."""
    return bool(_spans(_split(body)))


def orphaned(body: str) -> bool:
    """Whether `body` holds a start marker that makes no region: its end marker was
    lost, or it is quoted. What follows it may be the author's, so nothing removes
    it (DEC-065 point 1)."""
    lines_ = _split(body)
    covered = _covered(_spans(lines_))
    return any(_is_start(line) for at, line in enumerate(lines_) if at not in covered)


def strip(body: str) -> str:
    """`body` without each region a command wrote and the heading directly above it.
    Text outside them is left as it is, a marker with no partner and a section under
    either heading with no markers included (DEC-065 point 1)."""
    lines_ = _split(body)
    spans = _spans(lines_)
    if not spans:
        return body.replace("\r\n", "\n")
    out: list[str] = []
    index = 0
    cut = False
    for span in spans:
        for line in lines_[index : span.first]:
            if cut and not line.strip() and (not out or not out[-1].strip()):
                continue  # no second blank line where the section was
            cut = False
            out.append(line)
        while out and not out[-1].strip():
            out.pop()
        if out:
            out.append("")
        index = span.last + 1
        cut = True
    for line in lines_[index:]:
        if cut and not line.strip() and (not out or not out[-1].strip()):
            continue
        cut = False
        out.append(line)
    return "\n".join(out)
