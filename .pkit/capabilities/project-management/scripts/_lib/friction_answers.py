"""The answers a change wrote, listed in its pull request's description (DEC-055).

An agent building a change may give the answers its own change owes — the
revalidations and deferrals the change check asks of it — without asking
first; they become a person's decision when the person who authorises the
merge is shown every one of them, word for word, from the change check's own
list (COR-050 point 3). This module puts that list in the description:

- `derive(head, base)` runs the change check at the pull request's head
  (`pkit friction check --json --base <base> --head <oid>`) against the pull
  request's base — always named, so `$PKIT_CHECK_BASE` in the environment never
  changes it — after fetching that base, and reads what the check is asked
  about — its places and the files `friction.exclude` leaves out — at both ends
  of the change, through the backbone's discovery (`settings_change`). It
  returns the check's document and the friction settings the change alters —
  or why they could not be read, which is never a pass.
- `render(document, head, settings)` is the `## Friction answers` section,
  between its markers; `lines(document, settings)` the same list for a
  terminal.
- `closing_reference` and `comment_delimiter` name a word of the list that
  must not be written: one that reads as a closing reference — the host's own
  parser would close an issue with it at merge, and nothing here can make that
  parser skip a section — and one holding an HTML comment's delimiter, which
  could open or close a comment around the section's markers.
- `stamp`, `strip`, `find` and `current` place, remove, find and compare the
  section — strip-then-place-exactly-one, as `provenance.stamp` keeps the
  footer. The section sits last, before the provenance footer. A
  `## Friction answers` section no command wrote — a list typed by hand, with
  no markers — is stripped with everything under it (`hand_written`).

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

HEADING = "## Friction answers"
#: Sentinels — MUST match body-format.yaml `friction_answers_marker`. The start
#: marker carries the head the list is for and the merge-base it was taken against.
MARKER_START = "<!-- pkit-friction-answers:start"
MARKER_END = "<!-- pkit-friction-answers:end -->"
_START_LINE = re.compile(r"^<!-- pkit-friction-answers:start(?:\s[^\n]*)?-->$")
#: The section's heading as a line, however a hand spaced or cased it.
_HEADING_LINE = re.compile(r"^ {0,3}##[ \t]+friction answers[ \t]*#*[ \t]*$", re.IGNORECASE)
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


#: The two settings a list can show.
PLACES = "the places the change check reads"
EXCLUDED = "of the files whose standing changed, those `friction.exclude` leaves out"


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


@dataclass(frozen=True)
class _Entry:
    """One answer, every text in it shown as the list shows it."""

    location: str
    answer: str
    anchor: str | None
    marks: tuple[str, ...]
    reason: str | None
    kept: tuple[tuple[str, str | None], ...]


def _read_entry(entry: Mapping[str, Any]) -> _Entry:
    anchor = _mapping(entry.get("anchor"))
    reason = entry.get("reason")
    marks: list[str] = []
    if entry.get("new"):
        marks.append("a new artefact")
    if not entry.get("asked"):
        marks.append("not asked for by the change check")
    if entry.get("status") == "bump":
        marks.append("the diff does not bear it out")
    if entry.get("status") == "edited":
        marks.append("edited without a revalidation")
    kept: list[tuple[str, str | None]] = []
    for item in entry.get("kept") or []:
        held = _mapping(_mapping(item).get("anchor"))
        words = _mapping(item).get("reason")
        kept.append(
            (
                shown(f"{held.get('kind')}:{held.get('value')}"),
                shown(str(words)) if words is not None else None,
            )
        )
    return _Entry(
        location=shown(str(entry.get("location") or entry.get("artefact") or "?")),
        answer=shown(str(entry.get("answer") or "no outcome")),
        anchor=shown(f"{anchor.get('kind')}:{anchor.get('value')}") if anchor else None,
        marks=tuple(marks),
        reason=shown(str(reason)) if reason is not None else None,
        kept=tuple(kept),
    )


def _side(values: Sequence[str], *, code: bool) -> str:
    """One side of a setting's change: each text, or "none"."""
    if not values:
        return "none"
    return ", ".join(_code(shown(v)) if code else shown(v) for v in values)


def _counted(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


#: What the list says above the friction settings the change alters.
SETTINGS_LEAD = (
    "The change alters what the change check is asked about — the friction settings "
    "(`pkit friction artefacts`):"
)


def render(document: Mapping[str, Any], head: str, settings: Sequence[Setting] = ()) -> str | None:
    """The `## Friction answers` section for `document`, derived at commit `head`,
    with the friction `settings` the change alters; None when the change wrote no
    answers and alters no setting. Every text is the check's or the backbone
    discovery's, shown with any non-printable character escaped and set in a
    code span, so no word of an artefact is read as Markdown."""
    entries = [_read_entry(entry) for entry in _entries(document)]
    if not entries and not settings:
        return None
    merge_base = str(_mapping(document.get("base")).get("commit") or "")
    if entries:
        first = (
            f"{_counted(len(entries), 'answer', 'answers')} written by this change, as of "
            f"`{head[:SHORT]}` — the change check's list (`pkit friction check`). Each is on "
            "its artefact."
        )
    else:
        dormant = "; it is dormant at that head" if document.get("dormant") else ""
        first = (
            f"No answer written by this change, as of `{head[:SHORT]}`, in the change check's "
            f"list (`pkit friction check`){dormant}."
        )
    unreadable = document.get("unreadable")
    if isinstance(unreadable, list) and unreadable:
        files = len(unreadable)
        first += (
            f" {_counted(files, 'file', 'files')} the check could not read "
            f"{'is' if files == 1 else 'are'} not listed."
        )
    out = [HEADING, "", f"{MARKER_START} head={head} base={merge_base} -->", first]
    if entries:
        out.append("")
    for number, entry in enumerate(entries, start=1):
        line = f"{number}. {_code(entry.location)} — **{entry.answer}**"
        if entry.anchor is not None:
            line += f" {_code(entry.anchor)}"
        if entry.marks:
            line += f" — {'; '.join(entry.marks)}"
        if entry.reason is not None:
            line += f": {_code(entry.reason, least=2)}"
        out.append(line)
        for anchor, words in entry.kept:
            kept = f"   - keeps the deferral of {_code(anchor)}"
            out.append(kept + (f": {_code(words, least=2)}" if words is not None else ""))
    if settings:
        out += ["", SETTINGS_LEAD, ""]
        for setting in settings:
            before, after = _side(setting.before, code=True), _side(setting.after, code=True)
            out.append(f"- {setting.key}: {before} → {after}")
    out.append(MARKER_END)
    return "\n".join(out)


def lines(document: Mapping[str, Any], settings: Sequence[Setting] = ()) -> list[str]:
    """The list as a terminal shows it: one line per answer, its words in full,
    then one per friction setting the change alters."""
    out: list[str] = []
    for number, entry in enumerate((_read_entry(e) for e in _entries(document)), start=1):
        line = f"{number}. {entry.location} — {entry.answer}"
        if entry.anchor is not None:
            line += f" {entry.anchor}"
        if entry.marks:
            line += f" — {'; '.join(entry.marks)}"
        if entry.reason is not None:
            line += f": {entry.reason}"
        out.append(line)
        for anchor, words in entry.kept:
            out.append(
                f"   keeps the deferral of {anchor}" + (f": {words}" if words is not None else "")
            )
    for setting in settings:
        before, after = _side(setting.before, code=False), _side(setting.after, code=False)
        out.append(f"{setting.key}: {before} → {after}")
    return out


def _texts(document: Mapping[str, Any], settings: Sequence[Setting]) -> Iterator[tuple[str, str]]:
    """Every text the section would show, as it would show it, with where it is:
    (an answer's location, or `SETTINGS_WHERE`) and the text."""
    for entry in (_read_entry(e) for e in _entries(document)):
        texts: list[str | None] = [entry.location, entry.anchor, entry.reason]
        for anchor, words in entry.kept:
            texts += [anchor, words]
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
    marker everything after it up to the provenance footer), or `hand` (a
    `## Friction answers` heading no marker follows, with everything under it)."""

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
    """The span of a `## Friction answers` section no command wrote: its heading
    through the line before the provenance footer, a marker, the next heading of
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
    """Whether `body` carries a `## Friction answers` section no command wrote: the
    heading with no marker under it."""
    return any(span.kind == "hand" for span in _spans(_split(body)))


def has_list(body: str) -> bool:
    """Whether `body` carries the section a command wrote, or a marker of one."""
    return any(span.kind != "hand" for span in _spans(_split(body)))


def strip(body: str) -> str:
    """`body` without the section: every region and the heading directly above it,
    every marker with no partner — a start marker with everything after it up to
    the provenance footer — and every `## Friction answers` section no command
    wrote, with everything under it. Text outside them is left as it is."""
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
    carries nothing of the section — no region, no marker line, no
    `## Friction answers` section a hand wrote. Markers count only as whole lines."""
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
