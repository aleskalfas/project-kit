"""The fixers' proposals brought to the person, and what the person decides (DEC-056 point 6).

The drift command gathers each fixer's proposals into the queue (`drift_queue`),
and the landing command counts what waits. This module is how they come back
to the person, and how the person's decision is kept or applied. The project
manager reaches the queue only through the commands built on it, never with
file tools:

- `show-proposals` brings the batch: each proposal with its evidence, its diff
  and its writer's command word for word, and each question a fixer held.
- `apply-proposals` applies what the person accepted to the working tree of
  the change's branch, upstream first: each diff, then each writer.
- `refuse-proposals` remembers a refusal against the artefact's friction.
- `answer-question` records the person's answer to a held question, for the
  artefact's next brief.

What waits is checked again before it is shown and before it is applied
(`recheck`). A proposal whose artefact is no longer stale at the default
branch, whose friction there differs from what it was judged against, which was
judged under another version of the run's contract, or whose files no longer
read is set aside (`set_aside`), so the next run dispatches it again. It is
never shown or applied. A diff that no longer applies is set aside too.

Each writer's command is built from the answer's fields as a list of
arguments (`writer_argv`). No string a fixer wrote is run as a command: its
words reach the writer only as the value of an option, after the person read
them. A run's folder is removed once none of its proposals waits (`prune`).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from _lib import default_branch, drift, drift_queue, fixer_contract
from _lib.membership import CAPABILITY_NAME, resolve_capability_root

#: The commands of the batch, as `pkit pm <verb>`.
SHOW = "show-proposals"
APPLY = "apply-proposals"
REFUSE = "refuse-proposals"
ANSWER = "answer-question"

#: The states of what waits on the person: a proposal, and a question a fixer held.
PROPOSED = "proposed"
HELD = "held"

#: The file a fixer writes beside its answer, for the person to read first.
EVIDENCE = "evidence.md"

#: A placeholder a fixer's draft leaves for the person to fill, such as
#: `<the defect reference>` (`schemas/fixer-answer.schema.json`, `justification`).
_PLACEHOLDER = re.compile(r"<[^<>\s][^<>]*>")

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Refused(Exception):
    """The command cannot go on, and nothing was written: the message says why."""


# --- starting a command ----------------------------------------------------------------------


@dataclass(frozen=True)
class Started:
    """Where a command of the batch works: the checkout, and the queue in the main
    working tree's agent workspace."""

    capability_root: Path
    repo_root: Path
    queue: Path


def start(verb: str, capability_root: Path | None) -> Started:
    """The checkout and the queue for `verb`. Raises Refused inside an agent run
    (a fixer applies nothing, DEC-056 point 5), where the capability is not
    found, and where the repository keeps no queue. Each command calls the
    bootstrap gate and, before it writes, the session guard itself."""
    if drift.RUN_MARKER in os.environ:
        raise Refused(
            f"refusing to run `pkit pm {verb}` inside an agent run ({drift.RUN_MARKER} is set): "
            "a fixer only proposes (DEC-056 point 5)"
        )
    root = resolve_capability_root(capability_root)
    if root is None:
        raise Refused(f"{CAPABILITY_NAME} capability not found")
    repo_root = root.parents[2]
    queue = drift_queue.folder(repo_root)
    if isinstance(queue, str):
        raise Refused(queue)
    return Started(root, repo_root, queue)


# --- what waits ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Waiting:
    """An artefact that waits on the person: a proposal, with its answer read
    again by the run's contract, or a question a fixer held."""

    name: str
    entry: Mapping[str, Any]
    files: Path | None  # the fixer's files of its run: <queue>/runs/<run>/<fixer>
    answer: fixer_contract.Answer | None = None
    unread: str = ""  # why its files no longer read

    @property
    def state(self) -> str:
        return str(self.entry.get("state"))

    @property
    def answered(self) -> bool:
        """A held question the person has answered: it waits for the next run."""
        return self.state == HELD and bool(self.entry.get("answer"))

    @property
    def evidence(self) -> str | None:
        """The evidence the fixer wrote for the person, or None where there is none."""
        if self.files is None:
            return None
        parts = _parts(self.name)
        return None if parts is None else read_plain(self.files, [*parts, EVIDENCE])


def _parts(relative: str) -> list[str] | None:
    """`relative` split at each `/`, or None where it is no plain relative path."""
    if not relative or relative.startswith("/") or "\\" in relative or "\0" in relative:
        return None
    parts = relative.split("/")
    return None if any(part in ("", ".", "..") for part in parts) else parts


def read_plain(root: Path, parts: Sequence[str]) -> str | None:
    """The text of `root/parts…`, or None unless it is a plain file reached
    through plain folders: no part may be a link, so nothing reads outside the
    queue."""
    at = root
    for index, part in enumerate(parts):
        at = at / part
        try:
            mode = os.lstat(at).st_mode
        except OSError:
            return None
        last = index == len(parts) - 1
        if stat.S_ISLNK(mode) or (not last and not stat.S_ISDIR(mode)):
            return None
        if last and not stat.S_ISREG(mode):
            return None
    try:
        return at.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _files(queue: Path, entry: Mapping[str, Any]) -> Path | None:
    """The fixer's files of the entry's run, or None where its run or fixer is no
    single plain name."""
    run, fixer = str(entry.get("run") or ""), str(entry.get("fixer") or "")
    if any(_parts(name) is None or "/" in name for name in (run, fixer)):
        return None
    return queue / drift_queue.RUNS / run / fixer


def _position(index: Mapping[str, Any], name: str, entry: Mapping[str, Any]) -> tuple[str, int]:
    """Where an artefact stands in the queue: its run, then its place in the brief,
    which names the artefacts upstream first."""
    run = str(entry.get("run") or "")
    runs = index.get("runs") or {}
    listed = ((runs.get(run) or {}).get("fixers") or {}).get(str(entry.get("fixer") or "")) or {}
    names = listed.get("artefacts") or []
    return run, names.index(name) if name in names else len(names)


def waiting(
    index: Mapping[str, Any], queue: Path, contract: fixer_contract.Contract
) -> list[Waiting]:
    """Each artefact that waits on the person, in the queue's order, upstream
    first: each proposal with its answer read again, and each held question."""
    found: list[tuple[tuple[str, int], Waiting]] = []
    for name, entry in (index.get("artefacts") or {}).items():
        state = entry.get("state")
        if state not in (PROPOSED, HELD):
            continue
        files = _files(queue, entry)
        answer: fixer_contract.Answer | None = None
        unread = ""
        if state == PROPOSED:
            if files is None:
                unread = "its run or fixer is no plain name"
            else:
                read = fixer_contract.read_answer(files, name, contract=contract)
                if isinstance(read, fixer_contract.Unread):
                    unread = read.why
                else:
                    answer = read
        found.append((_position(index, name, entry), Waiting(name, entry, files, answer, unread)))
    found.sort(key=lambda pair: pair[0])
    return [item for _, item in found]


# --- checked again ---------------------------------------------------------------------------


def recheck(item: Waiting, explained: Mapping[str, Any], contract_version: int) -> str | None:
    """Why `item` no longer stands at the current default branch, or None. A
    proposal set aside for any of these is dispatched again (DEC-056 point 6).
    `explained` is `pkit friction explain <artefact> --json` at the default
    branch's commit."""
    judged = item.entry.get("contract_version")
    if judged != contract_version:
        return (
            f"it was judged under version {judged} of the run's contract, and this reads "
            f"version {contract_version}"
        )
    if item.unread:
        return f"its proposal no longer reads: {item.unread}"
    state = explained.get("state")
    if state != "stale":
        return f"it is no longer stale at the default branch: it is {state}"
    if drift.friction_fingerprint(explained) != item.entry.get("friction"):
        return "its friction at the default branch differs from the friction it was judged against"
    return None


# --- the queue's index, changed --------------------------------------------------------------


def set_aside(index: Mapping[str, Any], name: str, why: str) -> dict[str, Any]:
    """`index` with the artefact set aside, so the next run dispatches it again."""
    entries = dict(index.get("artefacts") or {})
    entry = dict(entries[name])
    entry.update(state=fixer_contract.SET_ASIDE, words=why, proposal=None, evidence=None, diff=None)
    entries[name] = entry
    return {**index, "artefacts": entries}


def refuse(index: Mapping[str, Any], name: str, *, at: str) -> dict[str, Any]:
    """`index` with the person's refusal remembered against the artefact's friction,
    and the artefact no longer waiting. The drift command dispatches it again only
    once its friction changes (DEC-056 point 6)."""
    entries = dict(index.get("artefacts") or {})
    entry = entries.pop(name)
    refusals = dict(index.get("refusals") or {})
    refusals[name] = {
        "friction": entry.get("friction"),
        "type": entry.get("type"),
        "fixer": entry.get("fixer"),
        "run": entry.get("run"),
        "commit": entry.get("commit"),
        "at": at,
    }
    return {**index, "artefacts": entries, "refusals": refusals}


def answer(index: Mapping[str, Any], name: str, *, words: str, by: str) -> dict[str, Any]:
    """`index` with the person's answer to a held question, and who gave it. The
    question then waits for the next run, whose brief quotes both (DEC-056 point 3)."""
    entries = dict(index.get("artefacts") or {})
    entry = dict(entries[name])
    entry.update(answer=words, answered_by=by)
    entries[name] = entry
    return {**index, "artefacts": entries}


def consume(index: Mapping[str, Any], name: str) -> dict[str, Any]:
    """`index` without the artefact whose proposal was applied."""
    entries = dict(index.get("artefacts") or {})
    entries.pop(name, None)
    return {**index, "artefacts": entries}


def prune(queue: Path, index: Mapping[str, Any]) -> list[str]:
    """Remove each run's folder that no waiting artefact needs, once each of its
    proposals was accepted or refused (DEC-056 point 6). The runs removed."""
    needed = {
        str(entry.get("run"))
        for entry in (index.get("artefacts") or {}).values()
        if entry.get("state") in (PROPOSED, HELD)
    }
    runs = queue / drift_queue.RUNS
    removed: list[str] = []
    if not runs.is_dir() or runs.is_symlink():
        return removed
    for child in sorted(runs.iterdir()):
        if child.name in needed:
            continue
        if child.is_symlink() or not child.is_dir():
            child.unlink()
        else:
            shutil.rmtree(child)
        removed.append(child.name)
    return removed


# --- the writer's command --------------------------------------------------------------------


def writer_argv(name: str, fields: Mapping[str, Any], because: str | None = None) -> list[str]:
    """The writer that records the answer, built from its fields: `pkit friction
    revalidate`, with the outcome, the justification of an `unchanged` answer (the
    person's words where given), each deferral it keeps, and `--yes`, since the
    person accepted it word for word. The artefact comes after `--`, so no name is
    read as an option."""
    argv = ["pkit", "friction", "revalidate", "--outcome", str(fields["outcome"])]
    if fields["outcome"] == "unchanged":
        argv += ["--because", because if because is not None else str(fields["justification"])]
    for anchor in fields.get("keep") or []:
        argv += ["--keep", str(anchor)]
    return [*argv, "--yes", "--", name]


def shown(argv: Sequence[str]) -> str:
    """A command as a person reads it and a shell would take it, word for word."""
    return shlex.join(argv)


def placeholder(text: str | None) -> str | None:
    """The first placeholder a draft leaves for the person to fill, or None."""
    found = _PLACEHOLDER.search(text or "")
    return found.group(0) if found else None


@cache
def _line_schema() -> Mapping[str, Any]:
    document = json.loads(fixer_contract.ANSWER_SCHEMA.read_text(encoding="utf-8"))
    return document["$defs"]["line"]


def line_problem(text: str) -> str | None:
    """Why the person's words cannot stand in an answer, or None: they are held to
    the line an answer's own words are, one line with no control or hiding
    character (`schemas/fixer-answer.schema.json`, `line`)."""
    import jsonschema

    if jsonschema.Draft202012Validator(_line_schema()).is_valid(text):
        return None
    return "they must be one line that is not blank, with no control, separator or hiding character"


# --- the default branch, and the checkout the change is made in ------------------------------


def pin(repo_root: Path, run: Runner = subprocess.run) -> tuple[str, str]:
    """The default branch's name and commit, as the backbone resolves them."""
    try:
        branch = default_branch.read(cwd=repo_root, run=run).default_branch
    except default_branch.Unanswered as exc:
        raise Refused(str(exc)) from exc
    commit = branch.commit
    if commit is None or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise Refused(
            "the default branch's commit cannot be resolved"
            + (f": {branch.problem}" if branch.problem else "")
            + " (`pkit repository base` says why)"
        )
    return branch.name, commit


def _git(root: Path, run: Runner, *argv: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *argv], cwd=str(root), capture_output=True, text=True, check=False)


def _last(proc: subprocess.CompletedProcess[str]) -> str:
    said = (proc.stderr or proc.stdout or "").strip().splitlines()
    return said[-1] if said else f"git exited {proc.returncode}"


def branch_problem(root: Path, default: str, run: Runner = subprocess.run) -> str | None:
    """Why the checkout is no branch an ordinary change is made on, or None: the
    change goes through a pull request, so not the default branch, and not a
    detached head."""
    proc = _git(root, run, "symbolic-ref", "--quiet", "--short", "HEAD")
    if proc.returncode != 0:
        return "the checkout is on no branch: switch to the change's branch first"
    current = (proc.stdout or "").strip()
    if current == default:
        return (
            f"the checkout is on the default branch, {default}: what you accept is applied "
            "through an ordinary pull request, so switch to the change's branch first"
        )
    return None


def file_problem(root: Path, commit: str, path: str, run: Runner = subprocess.run) -> str | None:
    """Why the checkout's file is not the default branch's, or None. A proposal was
    checked against the default branch, so its diff applies to that file only."""
    proc = _git(root, run, "diff", "--quiet", commit, "--", path)
    if proc.returncode == 0:
        return None
    if proc.returncode == 1:
        return (
            f"the checkout's {path} differs from the default branch's at {commit[:12]}: "
            "make the change's branch from the default branch, with nothing else on that file"
        )
    return f"the checkout's {path} cannot be compared with the default branch's: {_last(proc)}"


# --- applying ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Outcome:
    """What applying one accepted proposal did."""

    name: str
    applied: bool
    why: str = ""
    set_aside: bool = False  # dispatched again at the next run
    argv: tuple[str, ...] = ()
    sentence: str | None = None  # an `updated` answer's sentence, for the pull request


def upstream_first(names: Sequence[str], upstreams: Mapping[str, Sequence[str]]) -> list[str]:
    """`names` with each after the upstreams it names among them, otherwise in the
    order given. A cycle keeps the order given."""
    chosen = set(names)
    out: list[str] = []
    done: set[str] = set()

    def visit(name: str, path: set[str]) -> None:
        if name in done or name in path:
            return
        path.add(name)
        for upstream in upstreams.get(name, ()):
            if upstream in chosen and upstream != name:
                visit(upstream, path)
        path.discard(name)
        done.add(name)
        out.append(name)

    for name in names:
        visit(name, set())
    return out


def apply_one(
    item: Waiting,
    *,
    root: Path,
    because: str | None,
    sentence: str | None,
    run: Runner = subprocess.run,
    write: Runner = subprocess.run,
    dry_run: bool = False,
) -> Outcome:
    """Apply one accepted proposal to the checkout at `root`: its diff, where it
    has one, then its writer. A diff that no longer applies sets the proposal
    aside. A writer that fails leaves the file as it was, and the proposal waits.
    A dry run checks the diff and writes nothing."""
    assert item.answer is not None
    fields = item.answer.fields
    argv = tuple(writer_argv(item.name, fields, because))
    said = sentence if sentence is not None else fields.get("sentence")
    own = root / fixer_contract.own_file(item.name)
    try:
        before = own.read_bytes() if not own.is_symlink() else None
    except OSError as exc:
        return Outcome(item.name, False, f"its file cannot be read: {exc}")
    if before is None:
        return Outcome(item.name, False, f"its file, {own.relative_to(root)}, is a link")
    diff = item.answer.diff
    if diff is not None:
        checked = _git(root, run, "apply", "--check", str(diff))
        if checked.returncode != 0:
            why = f"its diff no longer applies: {_last(checked)}"
            return Outcome(item.name, False, why, set_aside=True, argv=argv)
    if dry_run:
        return Outcome(item.name, True, argv=argv, sentence=said)
    if diff is not None:
        applied = _git(root, run, "apply", str(diff))
        if applied.returncode != 0:
            own.write_bytes(before)
            why = f"its diff no longer applies: {_last(applied)}"
            return Outcome(item.name, False, why, set_aside=True, argv=argv)
    try:
        wrote = write(list(argv), cwd=str(root), capture_output=True, text=True, check=False)
    except OSError as exc:
        own.write_bytes(before)
        return Outcome(item.name, False, f"its writer could not start: {exc}", argv=argv)
    if wrote.returncode != 0:
        own.write_bytes(before)
        why = f"its writer exited {wrote.returncode}: {_last(wrote)}; its file is as it was"
        return Outcome(item.name, False, why, argv=argv)
    return Outcome(item.name, True, argv=argv, sentence=said)


# --- printing --------------------------------------------------------------------------------


def say(line: str = "") -> None:
    """Print one line whose words may be a fixer's, each control or formatting
    character shown as its escape, so no word rewrites the terminal."""
    print(drift.plain(line))


def say_block(text: str, indent: str = "    | ") -> None:
    """Print a fixer's file, line by line, each through `say`."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for line in lines or [""]:
        say(f"{indent}{line}")


def error(message: str) -> None:
    print(f"error: {drift.plain(message)}", file=sys.stderr)
