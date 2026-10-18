"""The answers a change wrote, listed in its pull request's description (DEC-055).

An agent building a change may give the answers its own change owes — the
revalidations and deferrals the change check asks of it — without asking
first. A reviewer other than that agent checks them, from the change check's
own list, and the person who authorises the merge is told what changed in
each updated document and which are left out of date, as information
(COR-050 point 3). This module puts that list in the description, with each
updated document's sentence from the change's author:

- `derive(head, base)` runs the change check at the pull request's head
  (`pkit friction check --json --base <base> --head <oid>`) against the pull
  request's base — always named, so `$PKIT_CHECK_BASE` in the environment never
  changes it — after fetching that base, and reads what the check is asked
  about — its places and the files `friction.exclude` leaves out — at both ends
  of the change, through the backbone's discovery (`settings_change`). It
  returns the check's document and the friction settings the change alters —
  or why they could not be read, which is never a pass.
- `render(document, head, settings)` is the `## Documentation this change
  affects` section, between its markers; `lines(document, settings)` the same
  list for a terminal. Both speak to a reader who does not know the
  methodology, in the words of the change check's own list: the question once
  (`QUESTION`), then each document, the anchors the change modified that it
  relies on, and whether it is still true, each answer and flag in plain words
  (`LABELS`, `FLAGS`). The change check's own terms stay in its
  machine-readable list (`--json`), which this module reads. Each `updated`
  document also gives its sentence on what changed, or says its author gave
  none.
- `sentences(body)` reads those sentences where the change's author keeps
  them: the description's own `## What changed in each updated document`
  section (`SENTENCES_HEADING`), one list item per document, the document in
  a code span as the list names it. `unread` names each list item there that
  gives no sentence — one in another form, such as the document in bold — by
  its line, and `unread_warning` is what a command says of it, with the form
  a sentence takes (`SENTENCE_FORM`). `given` is the ones the list shows, and
  `with_sentences` puts them into a list already written, for an edit that
  derives nothing. `told` is what the person who authorises the merge is
  told, as information: those sentences, the documents left out of date, and
  the friction settings changed.
- `closing_reference` and `comment_delimiter` name a word of the list that
  must not be written: one that reads as a closing reference — the host's own
  parser would close an issue with it at merge, and nothing here can make that
  parser skip a section — and one holding an HTML comment's delimiter, which
  could open or close a comment around the section's markers.
  `sentence_closing_reference` and `sentence_comment_delimiter` name the same
  in an author's sentence.
- `covers(since, head, base)` asks the backbone whether every change from one
  head of a pull request to a later one lies inside `revalidated` blocks, a
  clean merge of the base counting as none (`pkit friction since`): where it does, an
  authorisation for the earlier head covers the later one (DEC-055 point 3).
  An answer that cannot be read is never a pass.
- `stamp`, `strip`, `find` and `current` place, remove, find and compare the
  section — strip-then-place-exactly-one, as `provenance.stamp` keeps the
  footer. The section sits last, before the provenance footer. A section
  under its heading no command wrote — a list typed by hand, with no markers —
  is stripped with everything under it (`hand_written`). `FORMER_HEADING`, the
  heading an earlier run of these commands wrote the section under, is read as
  the section's heading too, so a list it left is replaced whole.

Which backbone derives the list: both runs of the change check — from the
working directory, and from a temporary checkout of the head when the first
meets the backbone's refusal to run an anchor's resolver away from the head —
run the `pkit` first on PATH with routing off (`PKIT_NO_ROUTE=1`). That is the
backbone serving the command that runs this module: a source checkout's own
environment (`uv run` puts its `pkit` first), a project's pinned version (the
pin's run puts its `pkit` first), else the installed tool. Never routed again
from the directory a run starts in, a temporary checkout's own source or pin
cannot give the same head another list.

Every reader of a description strips the section before it reads (DEC-055
point 4): the list is the artefacts' words, never input. The markers are
locked to `body-format.yaml`'s `friction_answers_marker` by
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Sibling _lib imports, dual-form so the module loads both as part of the `_lib`
# package (scripts/ on sys.path) and standalone-by-path (scripts/_lib/ on
# sys.path) — as `pr_validation` does, which imports this module.
try:
    import default_branch  # type: ignore[import-not-found]
    import provenance  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from _lib import default_branch, provenance  # type: ignore[no-redef]

HEADING = "## Documentation this change affects"
#: The heading an earlier run of these commands wrote the section under: read as
#: the section's heading, so a section it left is found, stripped and replaced.
FORMER_HEADING = "## Friction answers"
#: Sentinels — MUST match body-format.yaml `friction_answers_marker`. The start
#: marker carries the head the list is for and the merge-base it was taken against.
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


#: The section's heading as a line — its own, or the one an earlier run wrote.
_HEADING_LINE = _heading_line(HEADING, FORMER_HEADING)
#: A heading that ends a section: an ATX heading of level one or two.
_SECTION_END = re.compile(r"^ {0,3}#{1,2}(?:[ \t]|$)")
#: A fenced code block's opening line; a heading inside one is no heading.
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")

#: The version of `pkit friction check --json` this module reads; a document of
#: another is unreadable here, never misread.
SCHEMA_VERSION = 1
#: The longest description the host keeps, in characters (GitHub's limit on a
#: pull request's body).
BODY_LIMIT = 65536
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
#: Whether what changed between two heads lies inside `revalidated` blocks, a clean
#: merge of the base counting as none, as the backbone answers it (`pkit friction since`, the CLI
#: README, "friction since"): the one reading of the blocks this capability makes.
SINCE = ("friction", "since")
#: The version of `pkit friction since --json` this module reads, versioned apart from
#: the change check's document; a document of another is no answer, never misread.
SINCE_SCHEMA_VERSION = 1
#: Where a friction setting's change is said to be, in a refusal.
SETTINGS_WHERE = "the friction settings"

#: A closing reference in the host's grammar: one of its nine keywords, an
#: optional colon, then `#N`, `owner/repo#N` or an issue's URL, in any case.
#: Over-matching only refuses a list; under-matching closes an issue at merge.
CLOSING_REFERENCE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*"
    r"(?:#\d+|[\w.-]+/[\w.-]+#\d+|https?://\S+?/issues/\d+)",
    re.IGNORECASE,
)
#: An HTML comment's delimiters: a word holding one could open or close a
#: comment around the section's markers, or hide the list from the page.
COMMENT_DELIMITER = re.compile(r"<!--|-->")


# --- the friction settings ----------------------------------------------------


@dataclass(frozen=True)
class Setting:
    """One change to what the change check is asked about: what changed, and its
    value where the head left its base and at the head, each a list of texts.
    The friction settings decide what the check asks — a change that empties the
    places leaves it dormant, one that excludes an artefact's file leaves the
    artefact out — so a change to them is shown with the answers (DEC-055
    point 1)."""

    key: str
    before: tuple[str, ...]
    after: tuple[str, ...]


#: The two settings a list can show, as it names them: the places the change
#: check reads, and — of the files whose standing changed — those
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
        proc = subprocess.run(
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
    change alters, or why they could not be read."""

    head: str
    document: Mapping[str, Any] | None = None
    problem: str | None = None
    answers: tuple[Mapping[str, Any], ...] = field(default=())
    settings: tuple[Setting, ...] = field(default=())

    @property
    def listed(self) -> bool:
        """Whether there is a list to show: answers the change wrote, or friction
        settings it alters."""
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


def derive(head: str, base: str) -> Derivation:
    """The change check's document for commit `head` against the branch `base` —
    the pull request's, named always — the base fetched first where it is a
    remote's, and the friction settings the change alters.

    Run from the working directory with `--head`, which reads the commit from git
    objects. A resolver of a registered anchor kind runs only from a checkout at
    the commit, and the check refuses so elsewhere: on that refusal alone the
    check runs again from a temporary checkout of `head`, removed afterwards; any
    other failure is kept as it is. Never a pass on a guess: a base that could
    not be fetched, no document, a document of another version or without
    `answers`, and settings that cannot be read all make the derivation
    unreadable, with why."""
    problem = _refresh_base(base)
    if problem is not None:
        return Derivation(head, problem=problem)
    found = _run_check(head, base, cwd=None)
    if isinstance(found, _NoDocument) and found.elsewhere:
        with _checkout(head) as (path, why_not):
            if path is None:
                found = _NoDocument(
                    f"{found.why}; a checkout at {head[:SHORT]} to run it from failed: {why_not}"
                )
            else:
                found = _run_check(head, base, cwd=path)
    if isinstance(found, _NoDocument):
        return Derivation(head, problem=found.why)
    merge_base = str(_mapping(found.get("base")).get("commit") or "")
    settings = settings_change(merge_base, head)
    if isinstance(settings, str):
        return Derivation(head, problem=settings)
    return Derivation(head, document=found, answers=tuple(_entries(found)), settings=settings)


def _refresh_base(base: str) -> str | None:
    """Fetch the base the check will read where it is a remote's; why not, or None."""
    try:
        found = default_branch.check_base(base)
    except default_branch.Unanswered as exc:
        return str(exc)
    if found.resolved != "remote":
        return None
    remote, slash, branch = found.ref.partition("/")
    if not slash or not branch:
        return f"the base {found.ref} names no remote's branch to fetch"
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


def _run_check(head: str, base: str, *, cwd: Path | None) -> Mapping[str, Any] | _NoDocument:
    """The check's document, or why there is none. Enforcing mode exits 1 on
    friction and still prints its document, so exit 0 and 1 both carry one."""
    argv = [*PKIT, "friction", "check", "--json", "--base", base, "--head", head]
    command = f"`pkit friction check --json --base {base} --head {head}`"
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env={**os.environ, **UNROUTED},
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
    `since` to `head` lies inside `revalidated` blocks, a clean merge of the base
    counting as none (DEC-055 point 3). `outside` names each change that does not, a line each, and
    `problem` why the answer could not be read, which is never a pass."""

    since: str = ""
    head: str = ""
    covered: bool = False
    #: How many files changed only inside `revalidated` blocks.
    inside: int = 0
    outside: tuple[str, ...] = ()
    problem: str | None = None


def covers(since: str, head: str, base: str) -> Coverage:
    """Whether the changes from commit `since` to commit `head` lie only inside
    `revalidated` blocks, a clean merge of the branch `base` counting as none, as the
    backbone answers it (`pkit friction since <since> --head <head> --base <base>
    --json`, run unrouted as the change check is). The base is fetched first where it
    is a remote's, so a merge of it is told from the author's own commits. This
    capability never reads a friction block itself (DEC-055 point 3)."""
    problem = _refresh_base(base)
    if problem is not None:
        return Coverage(problem=problem)
    command = f"`pkit friction since {since} --head {head} --base {base} --json`"
    try:
        proc = subprocess.run(
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
            problem=f"{command}: it exited {proc.returncode}" + (f": {said[-1]}" if said else "")
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
    if not covered and not lines:
        return Coverage(problem=f"{command}: it answers not covered and names no change")
    return Coverage(since, head, covered, len(inside), tuple(lines))


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
    """The files the list's words are on: each answer's artefact file, which holds
    the deferrals a revalidation kept too."""
    return {str(e.get("location") or "").split("#", 1)[0] for e in _entries(document)} - {""}


def documents(answers: Iterable[Mapping[str, Any]]) -> int:
    """How many documents `answers` are on — each answer's artefact counted once:
    a page that defers two anchors is one document the change affects."""
    return len({str(answer.get("location") or answer.get("artefact") or "?") for answer in answers})


#: How a command's output names the list, in the section's plain words.
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


# --- rendering ---------------------------------------------------------------


def shown(text: str) -> str:
    """`text` with each character that is not printable — a control character, a
    newline, a bidirectional override, a zero-width character — written as its
    escape (`\\x1b`, `\\u202e`), as the change check's human view shows it."""
    if text.isprintable():
        return text
    return "".join(ch if ch.isprintable() else ascii(ch)[1:-1] for ch in text)


def _code(text: str, *, least: int = 1) -> str:
    """`text` as a Markdown code span: its delimiter is longer than any run of
    backticks inside, and a space pads a text that starts or ends with one."""
    runs = [len(run) for run in re.findall(r"`+", text)]
    fence = "`" * max(least, max(runs, default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


#: Each answer of the change check (`--json`'s `answer`) as the list says it:
#: whether the document is still true. An answer it does not name here is shown
#: as the check gives it. The change check's own list says the same words.
LABELS = {
    "updated": "updated in this change",
    "unchanged": "still accurate",
    "deferred": "out of date, fixed later",
    "unanchored": "not tied to anything",
}
#: The answers whose words the list tells the person who authorises the merge
#: (DEC-055 point 3): an update's sentence, and a deferral's reason.
UPDATED, DEFERRED = "updated", "deferred"
#: How the list gives an `updated` document's sentence: the author's words.
SAID = "what changed, in the words of the pull request's author"
#: What it says where the author wrote no sentence for that document.
UNSAID = "what changed: the pull request's author has not said"
#: A revalidation whose outcome is neither `updated` nor `unchanged` (`answer` null).
NO_OUTCOME = "no decision recorded"
#: Each flag the change check puts on an answer, as the list names it.
FLAGS = {
    "new": "new document",
    "not asked": "not asked for by this change",
    "bump": "re-check date changed with nothing behind it",
    "edited": "edited without a new re-check",
    "written back": "re-check date set back to one it had before, which answers nothing",
    "entry written back": "an entry it had before, which covers only what that one did",
    "put back": "an entry it had before, covering the anchor as it stood then",
}
#: What an anchor of a core kind is named; an anchor of another kind is named as
#: the check names it, `kind:value`.
_ANCHOR_NOUNS = {"path": "", "record": "decision record ", "artefact": "document "}


@dataclass(frozen=True)
class _Anchor:
    """An anchor, its kind and value each shown as the list shows it."""

    kind: str
    value: str

    @property
    def named(self) -> str:
        """The anchor as the change check names it."""
        return f"{self.kind}:{self.value}"

    def said(self, *, markdown: bool) -> str:
        """The anchor in plain words: "`src/cli/**`", "decision record `COR-050`". The
        anchor's own text is set in a code span in Markdown."""
        noun = _ANCHOR_NOUNS.get(self.kind)
        text = self.value if noun is not None else self.named
        return f"{noun or ''}{_code(text) if markdown else text}"


def _read_anchor(value: Any) -> _Anchor | None:
    anchor = _mapping(value)
    if not anchor:
        return None
    return _Anchor(shown(str(anchor.get("kind"))), shown(str(anchor.get("value"))))


@dataclass(frozen=True)
class _Entry:
    """One answer, every text in it shown as the list shows it. `changed`: the
    anchors the change modified that the answer is about (the check's `changed`;
    none from a backbone that predates it). `updated`: the answer is `updated`,
    so the list gives the author's `sentence` on what changed, or says there is
    none."""

    location: str
    label: str
    anchor: _Anchor | None
    flags: tuple[str, ...]
    reason: str | None
    kept: tuple[tuple[_Anchor, str | None], ...]
    changed: tuple[_Anchor, ...] = ()
    updated: bool = False
    sentence: str | None = None


def _flags(entry: Mapping[str, Any]) -> list[str]:
    """Every flag the change check puts on an answer, in the list's words."""
    status = entry.get("status")
    flags: list[str] = []
    if entry.get("new"):
        flags.append(FLAGS["new"])
    if not entry.get("asked"):
        flags.append(FLAGS["not asked"])
    if status == "bump":
        flags.append(FLAGS["bump"])
    if status == "edited":
        flags.append(FLAGS["edited"])
    if status == "written-back":
        flags.append(FLAGS["written back" if entry.get("anchor") is None else "entry written back"])
    elif entry.get("put_back"):
        flags.append(FLAGS["put back"])
    return flags


def _read_entry(entry: Mapping[str, Any], sentences: Mapping[str, str] | None = None) -> _Entry:
    answer, reason = entry.get("answer"), entry.get("reason")
    kept: list[tuple[_Anchor, str | None]] = []
    for item in entry.get("kept") or []:
        words = _mapping(item).get("reason")
        held = _read_anchor(_mapping(item).get("anchor")) or _Anchor("None", "None")
        kept.append((held, shown(str(words)) if words is not None else None))
    changed = entry.get("changed")
    relied = [_read_anchor(item) for item in changed] if isinstance(changed, list) else []
    location = shown(str(entry.get("location") or entry.get("artefact") or "?"))
    updated = answer == UPDATED
    sentence = (sentences or {}).get(location) if updated else None
    return _Entry(
        location=location,
        label=LABELS.get(str(answer), shown(str(answer))) if answer else NO_OUTCOME,
        anchor=_read_anchor(entry.get("anchor")),
        flags=tuple(_flags(entry)),
        reason=shown(str(reason)) if reason is not None else None,
        kept=tuple(kept),
        changed=tuple(anchor for anchor in relied if anchor is not None),
        updated=updated,
        sentence=shown(sentence) if sentence is not None else None,
    )


def _side(values: Sequence[str], *, code: bool) -> str:
    """One side of a setting's change: each text, or "none"."""
    if not values:
        return "none"
    return ", ".join(_code(shown(v)) if code else shown(v) for v in values)


def _counted(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


#: The question the list answers, stated once above it, as the change check's
#: own list states it.
QUESTION = (
    "These documents rely on something this change modifies, and each answer says whether "
    "the document is still true."
)
#: What the section says first, to a reader who does not know the methodology.
OPENING = QUESTION
#: What it says first where the change decided nothing about any document but
#: changes which documents are checked.
SETTINGS_OPENING = (
    "This change decided nothing about any document, but it changes which documents are checked."
)
#: What the list says above those changes, after the documents.
SETTINGS_LEAD = "It also changes which documents are checked:"


def _and(items: Sequence[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _described(entry: _Entry, number: int, *, markdown: bool) -> list[str]:
    """One answer as the list shows it — the document, the anchors the change
    modified that it relies on, whether it is still true, its flags and its words —
    then, for an `updated` document, the author's sentence on what changed (`SAID`)
    or that there is none (`UNSAID`), then each deferral it kept, as the change
    check's own list says them. In Markdown the outcome is bold and every text of
    the artefact's, and the author's sentence, is set in a code span."""

    def text(words: str, least: int = 1) -> str:
        return _code(words, least=least) if markdown else words

    def bold(words: str) -> str:
        return f"**{words}**" if markdown else words

    sentence = bold(entry.label[:1].upper() + entry.label[1:])
    where = text(entry.location)
    if entry.changed:
        relied = _and([anchor.said(markdown=markdown) for anchor in entry.changed])
        line = f"{number}. {where} relies on {relied}, which this change modifies. {sentence}"
    elif entry.anchor is not None:
        line = f"{number}. {where} relies on {entry.anchor.said(markdown=markdown)}. {sentence}"
    else:
        line = f"{number}. {where} — {bold(entry.label)}"
    line += "".join(f" ({flag})" for flag in entry.flags)
    if entry.reason is not None:
        line += f': "{text(entry.reason, least=2)}"'
    out = [line]
    if entry.updated:
        said = UNSAID if entry.sentence is None else f'{SAID}: "{text(entry.sentence, least=2)}"'
        out.append(f"   - ({said})" if markdown else f"   ({said})")
    for anchor, words in entry.kept:
        kept = f"still out of date for changes to {anchor.said(markdown=markdown)}, fixed later"
        kept += f': "{text(words, least=2)}"' if words is not None else ""
        out.append(f"   - ({kept})" if markdown else f"   ({kept})")
    return out


def render(
    document: Mapping[str, Any],
    head: str,
    settings: Sequence[Setting] = (),
    sentences: Mapping[str, str] | None = None,
) -> str | None:
    """The `## Documentation this change affects` section for `document`, derived
    at commit `head`, with the friction `settings` the change alters and, beside
    each `updated` document, its author's sentence from `sentences` (`sentences`
    reads them); None when the change wrote no answers and alters no setting. It
    opens in plain words for a reader who does not know the methodology
    (`OPENING`); every text of the check's or the backbone discovery's, and every
    sentence, is shown with any non-printable character escaped and set in a code
    span, so no word of an artefact is read as Markdown."""
    entries = [_read_entry(entry, sentences) for entry in _entries(document)]
    if not entries and not settings:
        return None
    merge_base = str(_mapping(document.get("base")).get("commit") or "")
    dormant = not entries and bool(document.get("dormant"))
    as_of = f"As of commit `{head[:SHORT]}`" + (", no document is checked." if dormant else ".")
    unreadable = document.get("unreadable")
    if isinstance(unreadable, list) and unreadable:
        as_of += f" {_counted(len(unreadable), 'document', 'documents')} could not be read."
    out = [HEADING, "", f"{MARKER_START} head={head} base={merge_base} -->"]
    out += [OPENING if entries else SETTINGS_OPENING, "", as_of, ""]
    for number, entry in enumerate(entries, start=1):
        out += _described(entry, number, markdown=True)
    if settings:
        out += ["", SETTINGS_LEAD, ""] if entries else []
        for setting in settings:
            before, after = _side(setting.before, code=True), _side(setting.after, code=True)
            out.append(f"- {setting.key}: {before} → {after}")
    out.append(MARKER_END)
    return "\n".join(out)


def lines(
    document: Mapping[str, Any],
    settings: Sequence[Setting] = (),
    sentences: Mapping[str, str] | None = None,
) -> list[str]:
    """The list as a terminal shows it, in the section's words: the question once
    (`QUESTION`), one line per answer, its words in full, with each `updated`
    document's sentence on a line of its own, then one per friction setting the
    change alters."""
    entries = [_read_entry(e, sentences) for e in _entries(document)]
    out: list[str] = [QUESTION] if entries else []
    for number, entry in enumerate(entries, start=1):
        out += _described(entry, number, markdown=False)
    for setting in settings:
        before, after = _side(setting.before, code=False), _side(setting.after, code=False)
        out.append(f"{setting.key}: {before} → {after}")
    return out


def told(
    document: Mapping[str, Any],
    settings: Sequence[Setting] = (),
    sentences: Mapping[str, str] | None = None,
) -> list[str]:
    """What the person who authorises the merge is told, as information, not a
    gate (DEC-055 point 3), as a terminal shows it: what changed in each `updated`
    document, in its author's sentence or that there is none; each document left
    out of date, with the anchor and the words of each deferral the change wrote
    or a revalidation kept, which name its follow-up; then each friction setting
    the change alters."""
    out: list[str] = []
    entries = [_read_entry(e, sentences) for e in _entries(document)]
    for entry in entries:
        if entry.updated:
            said = "the pull request's author has not said"
            if entry.sentence is not None:
                said = f'"{entry.sentence}"'
            out.append(f"What changed in {entry.location}: {said}")
    for entry in entries:
        late = [(entry.anchor, entry.reason)] if entry.label == LABELS[DEFERRED] else []
        for anchor, words in [*late, *entry.kept]:
            where = f", for changes to {anchor.said(markdown=False)}" if anchor else ""
            out.append(
                f"Left out of date: {entry.location}{where}"
                + (f': "{words}"' if words is not None else "")
            )
    for setting in settings:
        before, after = _side(setting.before, code=False), _side(setting.after, code=False)
        out.append(f"{setting.key}: {before} → {after}")
    return out


def counted_told(document: Mapping[str, Any]) -> tuple[int, int]:
    """How many documents the change updated, and how many it leaves out of date
    — a deferral it wrote or a revalidation kept — each document counted once."""
    entries = _entries(document)
    updated = {str(e.get("location") or "") for e in entries if e.get("answer") == UPDATED}
    late = {
        str(e.get("location") or "")
        for e in entries
        if e.get("answer") == DEFERRED or e.get("kept")
    }
    return len(updated), len(late)


# --- the author's sentences ---------------------------------------------------

#: The heading of the description's section where the change's author says what
#: changed in each document the change revalidated as `updated`, one sentence
#: each (DEC-055 point 1). It is the author's own text, kept in the description
#: between writes; the commands read it and give each sentence beside its
#: document in the list. MUST match body-format.yaml `friction_answers_marker`'s
#: `sentences_heading`.
SENTENCES_HEADING = "## What changed in each updated document"
_SENTENCES_LINE = _heading_line(SENTENCES_HEADING)
#: A sentence: a top-level list item, bulleted or numbered and starting in the
#: line's first column, that names the document in a code span, as the list names
#: it, then a colon or a dash, then the sentence.
_SENTENCE_ITEM = re.compile(
    r"^(?:[-*+]|\d{1,9}[.)])[ \t]+(`+)(.+?)\1(?!`)[ \t]*(?:[:—–-][ \t]*)?(.*)$"
)
#: The form a sentence takes, as a warning names it.
SENTENCE_FORM = "- `path`: sentence"
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


def _read_sentences(body: str) -> tuple[dict[str, str], list[Unread]]:
    """The sentences the author wrote under `SENTENCES_HEADING`, and each list item
    there that gives none (`sentences`, `unread`). One reading for both, so a
    warning names exactly the items the reading leaves out. The list a command
    wrote reads as a blank line, so its lines keep their numbers. An item is at
    the list's top level unless it is indented as far as the content of the
    top-level item above it, in the same list. A heading, an HTML comment, a
    thematic break, a fence, or a paragraph after a blank line, indented less
    than that content, ends the list."""
    lines_ = _split(provenance.strip_footer(body))
    listed = {index for span in _spans(lines_) for index in range(span.first, span.last + 1)}
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
    document each names — its location, as the list names it. Read from `body`
    without the list, its provenance footer, fenced code blocks and HTML comments.
    An item runs on over the lines under it up to a blank line, another list item,
    a heading, an HTML comment, a thematic break or a fence, its whitespace
    folded. Of two items for one document, the first."""
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
        f'a sentence: "{item.text}" — write it as "{SENTENCE_FORM}", starting in the '
        "line's first column, the document in a code span as the list names it"
    )


def given(document: Mapping[str, Any], sentences_: Mapping[str, str]) -> dict[str, str]:
    """The sentences the list gives: each `updated` document's, by its location."""
    updated = {_read_entry(e).location for e in _entries(document) if e.get("answer") == UPDATED}
    return {key: words for key, words in sentences_.items() if key in updated}


def unsaid(document: Mapping[str, Any], sentences_: Mapping[str, str]) -> list[str]:
    """Each `updated` document the author wrote no sentence for, in the list's order."""
    entries = [_read_entry(e, sentences_) for e in _entries(document)]
    return list(dict.fromkeys(e.location for e in entries if e.updated and e.sentence is None))


def sentence_closing_reference(sentences_: Mapping[str, str]) -> tuple[str, str] | None:
    """The first of `sentences_` that reads as a closing reference, as (the
    document it is for, the words that read so); None when none does."""
    return _first(CLOSING_REFERENCE, ((key, shown(words)) for key, words in sentences_.items()))


def sentence_comment_delimiter(sentences_: Mapping[str, str]) -> tuple[str, str] | None:
    """The first of `sentences_` holding an HTML comment's delimiter, as (the
    document it is for, the delimiter); None when none does."""
    return _first(COMMENT_DELIMITER, ((key, shown(words)) for key, words in sentences_.items()))


#: An entry's line in a list a command wrote: its number, then the document in a
#: code span.
_ENTRY_LINE = re.compile(r"^\d+\. (`+)(.+?)\1(?!`)")
#: How an `updated` entry's outcome reads in the Markdown list, in either case.
_UPDATED_MARK = f"**{LABELS[UPDATED]}**".lower()
#: A code span, as `_code` writes every text of an artefact's.
_CODE_SPAN = re.compile(r"(`+).+?\1(?!`)")


def _marked_updated(line: str) -> bool:
    """Whether an entry's line gives the outcome `updated`: the bold label outside
    every code span, so an artefact's words that quote it mark nothing."""
    return _UPDATED_MARK in _CODE_SPAN.sub("", line).lower()


#: How a line giving an author's sentence, or saying there is none, begins.
_SAID_LINE = re.compile(rf"^   - \((?:{re.escape(SAID)}|{re.escape(UNSAID)})")


def _region_updated(block: str) -> list[str]:
    """The documents a list a command wrote marks `updated`, as it names them."""
    out: list[str] = []
    for line in _split(block):
        entry = _ENTRY_LINE.match(line)
        if entry is not None and _marked_updated(line):
            out.append(_unpadded(entry.group(2)))
    return out


def given_in(block: str, sentences_: Mapping[str, str]) -> dict[str, str]:
    """The sentences a list a command wrote gives: each `updated` document's."""
    updated = set(_region_updated(block))
    return {key: words for key, words in sentences_.items() if key in updated}


def _unpadded(text: str) -> str:
    """A code span's text as `_code` wrote it: one space each side dropped when
    both are there."""
    return text[1:-1] if len(text) > 1 and text.startswith(" ") and text.endswith(" ") else text


def with_sentences(block: str, sentences_: Mapping[str, str]) -> str:
    """A list a command wrote — a region `find` gave — with each `updated`
    document's sentence from `sentences_`, or the line saying there is none, in
    place of the one it had; every other line as it was, the check's words and
    the markers included. For an edit that derives nothing: the list stays the
    check's for the head it names, and gives the author's sentences as they now
    stand."""
    out: list[str] = []
    for line in _split(block):
        if _SAID_LINE.match(line):
            continue
        out.append(line)
        entry = _ENTRY_LINE.match(line)
        if entry is None or not _marked_updated(line):
            continue
        sentence = sentences_.get(_unpadded(entry.group(2)))
        said = UNSAID if sentence is None else f'{SAID}: "{_code(shown(sentence), least=2)}"'
        out.append(f"   - ({said})")
    return "\n".join(out)


def _texts(document: Mapping[str, Any], settings: Sequence[Setting]) -> Iterator[tuple[str, str]]:
    """Every text the section would show, as it would show it, with where it is:
    (an answer's location, or `SETTINGS_WHERE`) and the text. An anchor is read as
    the change check names it, `kind:value`."""
    for entry in (_read_entry(e) for e in _entries(document)):
        named = entry.anchor.named if entry.anchor is not None else None
        texts: list[str | None] = [entry.location, entry.label, named, entry.reason]
        texts += [anchor.named for anchor in entry.changed]
        for anchor, words in entry.kept:
            texts += [anchor.named, words]
        for text in texts:
            if text:
                yield entry.location, text
    for setting in settings:
        for value in (setting.key, *setting.before, *setting.after):
            yield SETTINGS_WHERE, shown(value)


def _first(pattern: re.Pattern[str], found: Iterable[tuple[str, str]]) -> tuple[str, str] | None:
    for where, text in found:
        match = pattern.search(text)
        if match is not None:
            return where, match.group(0)
    return None


def closing_reference(
    document: Mapping[str, Any], settings: Sequence[Setting] = ()
) -> tuple[str, str] | None:
    """The first text of the list that reads as a closing reference, as
    (location, the words that read so); None when none does. Every text the
    section would show is read, as it would show it."""
    return _first(CLOSING_REFERENCE, _texts(document, settings))


def comment_delimiter(
    document: Mapping[str, Any], settings: Sequence[Setting] = ()
) -> tuple[str, str] | None:
    """The first text of the list holding an HTML comment's delimiter (`<!--` or
    `-->`), as (location, the delimiter); None when none does."""
    return _first(COMMENT_DELIMITER, _texts(document, settings))


# --- the section in a description ------------------------------------------


def _is_start(line: str) -> bool:
    return bool(_START_LINE.match(line.strip()))


def _is_end(line: str) -> bool:
    return line.strip() == MARKER_END


def _is_marker(line: str) -> bool:
    return _is_start(line) or _is_end(line)


@dataclass(frozen=True)
class _Span:
    """Lines of a body that are the section, or a piece of one: `first` through
    `last`. `kind` is `region` (a start marker's line through its end marker's,
    `start` and `end`), `marker` (a marker with no partner, and for a start
    marker everything after it up to the provenance footer), or `hand` (the
    section's heading — or `FORMER_HEADING` — with no marker following, and
    everything under it)."""

    first: int
    last: int
    kind: str
    start: int = -1
    end: int = -1


def _spans(lines_: Sequence[str]) -> list[_Span]:
    """Every piece of the section `lines_` carries, in order. The heading directly
    above a region or a marker — blank lines between — goes with it. Markers are
    whole lines wherever they stand, a fenced code block included, so a region is
    never hidden by a fence left open above it; a heading is read only outside a
    fenced code block."""
    footer = _footer_start(lines_)
    spans: list[_Span] = []
    fence: str | None = None
    index = 0
    while index < len(lines_):
        line = lines_[index]
        if _is_marker(line):
            spans.append(_marked(lines_, index, footer, heading=None))
            index = spans[-1].last + 1
            continue
        if fence is not None:
            fence = None if _closes(line, fence) else fence
            index += 1
            continue
        opened = _FENCE.match(line)
        if opened is not None:
            fence = opened.group(1)
            index += 1
            continue
        if _HEADING_LINE.match(line):
            below = index + 1
            while below < len(lines_) and not lines_[below].strip():
                below += 1
            if below < len(lines_) and _is_marker(lines_[below]):
                spans.append(_marked(lines_, below, footer, heading=index))
            else:
                spans.append(_hand(lines_, index, footer))
            index = spans[-1].last + 1
            continue
        index += 1
    return spans


def _closes(line: str, fence: str) -> bool:
    """Whether `line` closes a fenced block opened with `fence`: that character, at
    least as many times, and nothing else."""
    text = line.strip()
    return text.startswith(fence) and not text.strip(fence[0])


def _marked(lines_: Sequence[str], at: int, footer: int | None, *, heading: int | None) -> _Span:
    """The span of the marker line at `at`: its region, when a start marker's end
    follows; else the marker alone — or, for a start marker, everything from it to
    the provenance footer or the end of the body, where its list would be."""
    first = at if heading is None else heading
    if _is_start(lines_[at]):
        for end in range(at + 1, len(lines_)):
            if _is_end(lines_[end]):
                return _Span(first, end, "region", start=at, end=end)
            if _is_start(lines_[end]):
                break
        stop = footer if footer is not None and footer > at else len(lines_)
        return _Span(first, stop - 1, "marker")
    return _Span(first, at, "marker")


def _hand(lines_: Sequence[str], heading: int, footer: int | None) -> _Span:
    """The span of a section under the section's heading that no command wrote: its
    heading through the line before the provenance footer, a marker, the next heading of
    level one or two outside a fenced block, or the end of the body."""
    fence: str | None = None
    for index in range(heading + 1, len(lines_)):
        line = lines_[index]
        if index == footer or _is_marker(line):
            return _Span(heading, index - 1, "hand")
        if fence is not None:
            fence = None if _closes(line, fence) else fence
            continue
        opened = _FENCE.match(line)
        if opened is not None:
            fence = opened.group(1)
            continue
        if _SECTION_END.match(line):
            return _Span(heading, index - 1, "hand")
    return _Span(heading, len(lines_) - 1, "hand")


def _split(body: str) -> list[str]:
    return body.replace("\r\n", "\n").split("\n")


def find(body: str) -> str | None:
    """The region `body` carries — its start marker's line through its end
    marker's — or None when it carries no complete one. Of several, the last:
    every write places its region last, so that is the latest."""
    lines_ = _split(body)
    regions = [span for span in _spans(lines_) if span.kind == "region"]
    if not regions:
        return None
    return "\n".join(lines_[regions[-1].start : regions[-1].end + 1])


def hand_written(body: str) -> bool:
    """Whether `body` carries a section no command wrote: the section's heading —
    or `FORMER_HEADING` — with no marker under it."""
    return any(span.kind == "hand" for span in _spans(_split(body)))


def has_list(body: str) -> bool:
    """Whether `body` carries the section a command wrote, or a marker of one."""
    return any(span.kind != "hand" for span in _spans(_split(body)))


def strip(body: str) -> str:
    """`body` without the section: every region and the heading directly above it,
    every marker with no partner — a start marker with everything after it up to
    the provenance footer — and every section under the section's heading, or
    `FORMER_HEADING`, that no command wrote, with everything under it. Text
    outside them is left as it is."""
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


def _footer_start(lines_: Sequence[str]) -> int | None:
    """Where the provenance footer starts, as `provenance.strip_footer` finds it:
    the first line that is one of its markers, whole."""
    markers = (provenance.MARKER_START, provenance.MARKER_END)
    for index, line in enumerate(lines_):
        if line.strip() in markers:
            return index
    return None


def stamp(body: str, block: str | None) -> str:
    """`body` with exactly one section, `block` — the section `render` gives, or a
    region `find` gave — placed last before the provenance footer; with `block`
    None, `body` without one."""
    rest = strip(body).split("\n")
    if block is None:
        return "\n".join(rest)
    section = block if block.lstrip().startswith(HEADING) else f"{HEADING}\n\n{block.strip()}"
    footer_at = _footer_start(rest)
    before = "\n".join(rest if footer_at is None else rest[:footer_at]).rstrip()
    footer = "" if footer_at is None else "\n".join(rest[footer_at:]).strip()
    out = f"{before}\n\n{section.strip()}" if before else section.strip()
    return f"{out}\n\n{footer}\n" if footer else f"{out}\n"


def _normal(text: str | None) -> str:
    """Line endings as `\\n`, trailing whitespace dropped, outer blank lines trimmed."""
    if text is None:
        return ""
    lines_ = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines_).strip("\n")


def current(body: str, block: str | None) -> bool:
    """Whether `body` carries `block`'s region and nothing else of the section,
    read as a host may have changed its whitespace; with `block` None, whether it
    carries nothing of the section — no region, no marker line, no section a
    hand wrote under its heading. Markers count only as whole lines."""
    lines_ = _split(body)
    spans = _spans(lines_)
    if block is None:
        return not spans
    if len(spans) != 1 or spans[0].kind != "region":
        return False
    region = "\n".join(lines_[spans[0].start : spans[0].end + 1])
    return _normal(region) == _normal(find(block))


def fits(body: str) -> bool:
    """Whether the host keeps `body` whole."""
    return len(body) <= BODY_LIMIT
