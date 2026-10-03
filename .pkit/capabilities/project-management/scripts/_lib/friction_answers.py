"""The answers a change wrote, listed in its pull request's description (DEC-055).

An agent building a change may give the answers its own change owes — the
revalidations and deferrals the change check asks of it — without asking
first; they become a person's decision when the person who authorises the
merge is shown every one of them, word for word, from the change check's own
list (COR-050 point 3). This module puts that list in the description:

- `derive(head, base)` runs the change check at the pull request's head
  (`pkit friction check --json --head <oid>`) against where that head left its
  base, after fetching the base, and returns its document — or why it could
  not be read, which is never a pass.
- `render(document, head)` is the `## Friction answers` section, between its
  markers; `lines(document)` the same list for a terminal.
- `closing_reference(document)` names a word that reads as a closing
  reference: the host's own parser would close an issue with it at merge, and
  nothing here can make that parser skip a section, so such a list is never
  written.
- `stamp`, `strip`, `find` and `current` place, remove, find and compare the
  section — strip-then-place-exactly-one, as `provenance.stamp` keeps the
  footer. The section sits last, before the provenance footer.

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
import subprocess
import tempfile
from collections.abc import Iterator, Mapping, Sequence
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

#: The version of `pkit friction check --json` this module reads; a document of
#: another is unreadable here, never misread.
SCHEMA_VERSION = 1
#: The longest description the host keeps, in characters (GitHub's limit on a
#: pull request's body).
BODY_LIMIT = 65536
#: How long the change check may run before its answer is given up on.
TIMEOUT = 600
#: The backbone's command, as a capability's script runs it.
PKIT = ("pkit",)
SHORT = 7

#: A closing reference in the host's grammar: one of its nine keywords, an
#: optional colon, then `#N`, `owner/repo#N` or an issue's URL, in any case.
#: Over-matching only refuses a list; under-matching closes an issue at merge.
CLOSING_REFERENCE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*"
    r"(?:#\d+|[\w.-]+/[\w.-]+#\d+|https?://\S+?/issues/\d+)",
    re.IGNORECASE,
)


# --- deriving ----------------------------------------------------------------


@dataclass(frozen=True)
class Derivation:
    """The change check's document at one head, or why it could not be read."""

    head: str
    document: Mapping[str, Any] | None = None
    problem: str | None = None
    answers: tuple[Mapping[str, Any], ...] = field(default=())

    @property
    def unreadable(self) -> tuple[str, ...]:
        """The head's files whose front matter does not parse: not read for answers."""
        found = (self.document or {}).get("unreadable")
        return tuple(str(path) for path in found) if isinstance(found, list) else ()

    @property
    def merge_base(self) -> str:
        return str(_mapping((self.document or {}).get("base")).get("commit") or "")

    @property
    def outdated(self) -> bool:
        """The base moved on after the head left it (the check's `base.outdated`)."""
        return bool(_mapping((self.document or {}).get("base")).get("outdated"))


def check_base_for(base: str, config: Mapping[str, Any]) -> str | None:
    """What the change check is told to compare with for a pull request against
    `base`: nothing for the default branch — the check's own base is that branch —
    else `base`, which the check resolves as it resolves every branch named as a
    base (COR-054 point 2). Where the backbone cannot say which the default branch
    is, `base` is named."""
    try:
        return None if base == default_branch.name(config) else base
    except default_branch.Unanswered:
        return base


def derive(head: str, base: str | None) -> Derivation:
    """The change check's document for commit `head` against `base` (`None`: the
    check's own base), the base fetched first where it is a remote's.

    Run from the working directory with `--head`, which reads the commit from git
    objects. A resolver of a registered anchor kind runs only from a checkout at
    the commit, so where the run gives no document and the working directory is not
    a clean checkout at `head`, the check runs again from a temporary checkout of
    `head`, removed afterwards. Never a pass on a guess: a base that could not be
    fetched, no document, a document of another version or without `answers` all
    make the derivation unreadable, with why."""
    problem = _refresh_base(base)
    if problem is not None:
        return Derivation(head, problem=problem)
    found = _run_check(head, base, cwd=None)
    if isinstance(found, str) and not _clean_at(head):
        with _checkout(head) as (path, why_not):
            if path is None:
                found = f"{found}; a checkout at {head[:SHORT]} to run it from failed: {why_not}"
            else:
                found = _run_check(head, base, cwd=path, env={"PKIT_NO_ROUTE": "1"})
    if isinstance(found, str):
        return Derivation(head, problem=found)
    return Derivation(head, document=found, answers=tuple(_entries(found)))


def _refresh_base(base: str | None) -> str | None:
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


def _run_check(
    head: str, base: str | None, *, cwd: Path | None, env: Mapping[str, str] | None = None
) -> Mapping[str, Any] | str:
    """The check's document, or why there is none. Enforcing mode exits 1 on
    friction and still prints its document, so exit 0 and 1 both carry one."""
    argv = [*PKIT, "friction", "check", "--json", *(["--base", base] if base else [])]
    argv += ["--head", head]
    command = f"`pkit friction check --json{' --base ' + base if base else ''} --head {head}`"
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=None if env is None else {**os.environ, **env},
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
    why = f"it exited {proc.returncode}" + (f": {said[-1]}" if said else "")
    if proc.returncode not in (0, 1):
        return f"{command}: {why}"
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        return f"{command}: {why}, with no JSON document"
    if not isinstance(document, dict):
        return f"{command}: its answer is not a document"
    version = document.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        return f"{command}: it answered schema_version {version!r}; this reads {SCHEMA_VERSION}"
    if not isinstance(document.get("answers"), list):
        return f"{command}: its document lists no answers — the backbone predates the list"
    return document


def _clean_at(head: str) -> bool:
    """The working directory is a checkout at `head` with nothing uncommitted."""
    at = _git("rev-parse", "--verify", "--quiet", "HEAD").stdout.strip()
    if at != head:
        return False
    status = _git("status", "--porcelain", "--untracked-files=normal")
    return status.returncode == 0 and not status.stdout.strip()


@contextlib.contextmanager
def _checkout(head: str) -> Iterator[tuple[Path | None, str]]:
    """A temporary detached checkout of `head` (a linked worktree), removed on exit."""
    scratch = Path(tempfile.mkdtemp(prefix="pkit-friction-answers-"))
    path = scratch / "checkout"
    added = _git("worktree", "add", "--detach", "--quiet", str(path), head)
    try:
        if added.returncode != 0:
            said = (added.stderr or "").strip().splitlines()
            yield None, said[-1] if said else f"git worktree add exited {added.returncode}"
        else:
            yield path, ""
    finally:
        if added.returncode == 0:
            _git("worktree", "remove", "--force", str(path))
        shutil.rmtree(scratch, ignore_errors=True)
        _git("worktree", "prune")


def _git(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], capture_output=True, text=True, check=False)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _entries(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    found = document.get("answers")
    return [entry for entry in found if isinstance(entry, Mapping)] if found else []


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


def _counted(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def render(document: Mapping[str, Any], head: str) -> str | None:
    """The `## Friction answers` section for `document`, derived at commit `head`;
    None when the change wrote no answers. Every text is the check's, shown with
    any non-printable character escaped and set in a code span, so no word of an
    artefact is read as Markdown."""
    entries = [_read_entry(entry) for entry in _entries(document)]
    if not entries:
        return None
    merge_base = str(_mapping(document.get("base")).get("commit") or "")
    count = _counted(len(entries), "answer", "answers")
    first = (
        f"{count} written by this change, as of `{head[:SHORT]}` — the change check's list "
        "(`pkit friction check`). Each is on its artefact."
    )
    unreadable = document.get("unreadable")
    if isinstance(unreadable, list) and unreadable:
        files = len(unreadable)
        first += (
            f" {_counted(files, 'file', 'files')} the check could not read "
            f"{'is' if files == 1 else 'are'} not listed."
        )
    out = [HEADING, "", f"{MARKER_START} head={head} base={merge_base} -->", first, ""]
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
    out.append(MARKER_END)
    return "\n".join(out)


def lines(document: Mapping[str, Any]) -> list[str]:
    """The list as a terminal shows it: one line per answer, its words in full."""
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
    return out


def closing_reference(document: Mapping[str, Any]) -> tuple[str, str] | None:
    """The first text of the list that reads as a closing reference, as
    (location, the words that read so); None when none does. Every text the
    section would show is read, as it would show it."""
    for entry in (_read_entry(e) for e in _entries(document)):
        texts = [entry.location, entry.anchor, entry.reason]
        for anchor, words in entry.kept:
            texts += [anchor, words]
        for text in texts:
            match = CLOSING_REFERENCE.search(text or "")
            if match is not None:
                return entry.location, match.group(0)
    return None


# --- the section in a description ------------------------------------------


def _is_start(line: str) -> bool:
    return bool(_START_LINE.match(line.strip()))


def _is_end(line: str) -> bool:
    return line.strip() == MARKER_END


def _region(lines_: Sequence[str]) -> tuple[int, int] | None:
    """The first complete region: the start marker's line and the end marker's."""
    for start, line in enumerate(lines_):
        if _is_start(line):
            for end in range(start + 1, len(lines_)):
                if _is_end(lines_[end]):
                    return start, end
            return None
    return None


def find(body: str) -> str | None:
    """The region `body` carries — its start marker's line through its end
    marker's — or None when it carries no complete one."""
    lines_ = body.replace("\r\n", "\n").split("\n")
    found = _region(lines_)
    if found is None:
        return None
    start, end = found
    return "\n".join(lines_[start : end + 1])


def strip(body: str) -> str:
    """`body` without the section: every region, any marker line on its own, and
    the heading directly above a region (blank lines between). Text outside it is
    left as it is."""
    lines_ = body.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    index = 0
    cut = False
    while index < len(lines_):
        line = lines_[index]
        if _is_start(line) or _is_end(line):
            _drop_heading(out)
            end = index
            if _is_start(line):
                found = _region(lines_[index:])
                end = index + found[1] if found is not None else index
            index = end + 1
            cut = True
            continue
        if cut and not line.strip() and (not out or not out[-1].strip()):
            index += 1  # no second blank line where the section was
            continue
        cut = False
        out.append(line)
        index += 1
    return "\n".join(out)


def _drop_heading(out: list[str]) -> None:
    """Drop the section's heading from the end of `out`, and the blank lines with it."""
    end = len(out)
    while end and not out[end - 1].strip():
        end -= 1
    if end and out[end - 1].strip() == HEADING:
        end -= 1
        while end and not out[end - 1].strip():
            end -= 1
        del out[end:]
        if out:
            out.append("")


def _footer_start(lines_: Sequence[str]) -> int | None:
    """Where the provenance footer starts, as `provenance.strip_footer` finds it."""
    for index, line in enumerate(lines_):
        if provenance.MARKER_START in line or provenance.MARKER_END in line:
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
    """Whether `body` carries `block`'s region, read as a host may have changed its
    whitespace; with `block` None, whether it carries none."""
    if block is None:
        return find(body) is None and MARKER_START not in body
    return find(body) is not None and _normal(find(body)) == _normal(find(block))


def fits(body: str) -> bool:
    """Whether the host keeps `body` whole."""
    return len(body) <= BODY_LIMIT
