"""The answers a release owes for its own version edits (PRJ-014).

A release rewrites version lines (`release.version_writes`), and every artefact
anchored on a file it rewrites then owes the change check an answer (COR-050
point 5). After `pkit release apply` writes, `write_release_answers` runs the
change check over the release's writes, against the commit the release started
from, and writes an `unchanged` revalidation (COR-050 point 3) for each artefact
it can answer (PRJ-014 point 1):

- **Only version lines.** Each finding on the artefact that fails is friction on
  a path anchor, and each file of the release's diff that the anchor matches is a
  version file whose changed lines are all version lines (`VersionFile`).
- **No version the lines held.** The artefact's content — its body and its own
  fields, derived links whole — states none of the versions those lines held and
  no longer hold, as a whole version number (`stated`).
- **No deferral, no answers made apart.** In the writer's reading of the answer
  files, the artefact carries no live deferral and at most one live revalidation.

Its reason names each file, each rewritten line before and after, and the
versions the artefact does not state (PRJ-014 point 2). Every other artefact the
check asks about is left to a person, with why (point 3). The answers go in one
answer file the release adds, through the friction writer (COR-062 point 1).
Before it ends, the step runs the check again and takes back any answer of its
own that the check does not accept, or flags as replacing answers made apart
(point 4): it removes its answer file and writes the rest again.

Nothing here runs where the friction functionality holds no artefact: the check
is dormant, and no answer file is written.
"""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from project_kit import answer_files as af
from project_kit import friction_check as fc
from project_kit import friction_write as fw
from project_kit.friction_discovery import (
    NOTHING_SET_ASIDE,
    Artefact,
    Discovery,
    content,
    discover_artefacts,
    pattern_matches,
)
from project_kit.friction_git import CommitTree
from project_kit.release import ReleaseWrite, version_writes

#: A version number as a release writes one, a pre-release's suffix included.
VERSION_NUMBER = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?")

#: The record the release's answers rest on, which their reasons name.
RECORD = "PRJ-014"

# Why an artefact whose answers were made apart is left (COR-062 point 7).
_APART = "its answers were made apart, and their combined state needs judging"


@dataclass(frozen=True)
class LineEdit:
    """One line of a version file the release rewrote: as it stood and as it was
    written, each as the file holds it; `None` for a line the release added, or
    removed."""

    before: str | None
    after: str | None

    def described(self) -> str:
        """The edit in words, each line shown without its indent."""
        if self.before is None:
            return f"`{_shown(self.after)}` was added"
        if self.after is None:
            return f"`{self.before.strip()}` was removed"
        return f"`{self.before.strip()}` became `{_shown(self.after)}`"


@dataclass(frozen=True)
class VersionFile:
    """A file the release rewrote only in its version lines (`release.version_writes`),
    with each line it rewrote."""

    path: str
    edits: tuple[LineEdit, ...]

    @property
    def held(self) -> tuple[str, ...]:
        """The versions the rewritten lines held that the lines as written no longer hold,
        in the order they stood: what a document stating them would now say wrongly."""
        before = [v for e in self.edits if e.before for v in VERSION_NUMBER.findall(e.before)]
        after = {v for e in self.edits if e.after for v in VERSION_NUMBER.findall(e.after)}
        return tuple(dict.fromkeys(v for v in before if v not in after))

    def described(self) -> str:
        return f"In {self.path}, {_joined([e.described() for e in self.edits])}."


@dataclass(frozen=True)
class Left:
    """An artefact the check asks about that the release leaves to a person, and why."""

    location: str
    why: str


@dataclass(frozen=True)
class ReleaseAnswers:
    """What the answer step did: the artefacts it answered, in the check's order, the
    answer file it wrote them in, and the artefacts it left to a person."""

    answered: tuple[str, ...] = ()
    file: str | None = None
    left: tuple[Left, ...] = ()


def write_release_answers(source_kit: Path, *, now: datetime | None = None) -> ReleaseAnswers:
    """Write the answers the release's version edits owe, in the working tree of
    `source_kit`'s repository, against HEAD, the commit the release started from
    (PRJ-014). Raises `FrictionCheckError` where the check cannot run."""
    root = source_kit.parent
    result = fc.run_change_check(root, "HEAD")
    if result.dormant or result.base is None:
        return ReleaseAnswers()
    base = result.base.commit
    files = version_files(source_kit, base)
    changed = fc.read_diff(root, base).paths
    discovery = discover_artefacts(root)
    by_location = {a.location: a for a in discovery.artefacts}
    judged = _Judged(root, discovery)
    reasons: dict[str, str] = {}
    left: list[Left] = []
    for location, findings in _asked(result).items():
        artefact = by_location.get(location)
        answer = (
            _judge(artefact, findings, files, changed, judged)
            if artefact is not None
            else Left(location, "it is not where the check found it")
        )
        if isinstance(answer, Left):
            left.append(answer)
        else:
            reasons[location] = answer
    if not reasons:
        return ReleaseAnswers(left=tuple(left))
    written = _write(root, reasons, now)
    taken_back = _not_standing(fc.run_change_check(root, "HEAD"), written)
    if taken_back:
        (root / written).unlink()
        kept = {loc: why for loc, why in reasons.items() if loc not in taken_back}
        written = _write(root, kept, now) if kept else None
        left.extend(Left(loc, why) for loc, why in taken_back.items())
        reasons = kept
    return ReleaseAnswers(tuple(reasons), written, tuple(left))


def version_files(source_kit: Path, base: str) -> dict[str, VersionFile]:
    """Each version file the working tree changed since `base` only in its version
    lines, by its repository-relative path. A version file whose changed lines are not
    all version lines is left out, so an anchor on it is left to a person."""
    root = source_kit.parent
    writes = version_writes(source_kit)
    committed = CommitTree(root, base).read_bytes([w.path for w in writes])
    found: dict[str, VersionFile] = {}
    for write in writes:
        path = root / write.path
        before = (committed.get(write.path) or b"").decode("utf-8", "replace")
        after = path.read_text(encoding="utf-8") if path.is_file() else ""
        edits = _edits(before, after)
        if edits and _only_version_lines(edits, write):
            found[write.path] = VersionFile(write.path, edits)
    return found


def stated(versions: Sequence[str], artefact: Artefact) -> tuple[str, ...]:
    """Those of `versions` the artefact's content states as a whole version number: its
    body and its own fields, derived links whole (COR-050 point 5)."""
    body, fields = content(artefact, NOTHING_SET_ASIDE)
    text = f"{body}\n{json.dumps(fields, ensure_ascii=False, default=str)}"
    return tuple(v for v in versions if _stands_in(v, text))


def render(answers: ReleaseAnswers) -> list[str]:
    """What `pkit release apply` says of its answers, one line each."""
    lines: list[str] = []
    if answers.answered:
        lines.append(
            f"Answered {len(answers.answered)} artefact(s) the release's version edits ask "
            f"about, in {answers.file} ({RECORD}):"
        )
        lines.extend(f"  {location}" for location in answers.answered)
    if answers.left:
        lines.append(
            f"Left {len(answers.left)} artefact(s) for a person to answer on the release "
            f"branch before it merges (`pkit friction check` lists them):"
        )
        lines.extend(f"  {left.location}: {left.why}" for left in answers.left)
    return lines


# --- judging one artefact -----------------------------------------------------------


def _asked(result: fc.ChangeCheck) -> dict[str, list[fc.Finding]]:
    """By location, in the check's order, the failing findings of each artefact the check
    asks for an answer: one with friction among them."""
    failing: dict[str, list[fc.Finding]] = {}
    for finding in result.failing:
        if finding.location is not None and finding.artefact is not None:
            failing.setdefault(finding.location, []).append(finding)
    return {
        location: found
        for location, found in failing.items()
        if any(f.kind is fc.FindingKind.FRICTION for f in found)
    }


def _judge(
    artefact: Artefact,
    findings: Sequence[fc.Finding],
    files: Mapping[str, VersionFile],
    changed: Collection[str],
    judged: _Judged,
) -> str | Left:
    """The reason the release answers the artefact with, or why it leaves it."""
    location = artefact.location
    anchored: dict[str, VersionFile] = {}
    for finding in findings:
        anchor = finding.anchor
        if finding.kind is not fc.FindingKind.FRICTION:
            return Left(location, f"the check finds more of it to fail ({finding.kind.value})")
        if anchor is None or anchor.kind != "path":
            what = "its anchor list or its place" if anchor is None else f"its {anchor.kind} anchor"
            return Left(location, f"the check asks about {what}, not a version line")
        matched = sorted(
            p for p in changed if pattern_matches(anchor.value, p) and not af.is_answer_file(p)
        )
        if not matched:
            return Left(location, f"the check asks about its anchor {anchor.value} for no file")
        others = [p for p in matched if p not in files]
        if others:
            return Left(
                location,
                f"its anchor {anchor.value} stands on {_joined(others)}, which the release "
                f"changed in more than version lines",
            )
        anchored.update((p, files[p]) for p in matched)
    held = tuple(dict.fromkeys(v for f in anchored.values() for v in f.held))
    found = stated(held, artefact)
    if found:
        return Left(location, f"it states {_joined(found)}, which a line the release rewrote held")
    why = judged.why_not(artefact)
    if why is not None:
        return Left(location, why)
    return _reason(list(anchored.values()), held)


def _reason(files: Sequence[VersionFile], held: Sequence[str]) -> str:
    """The `unchanged-because` of a release's answer (PRJ-014 point 2)."""
    lines = [
        "The release rewrote only version lines in the files this artefact anchors.",
        *(f.described() for f in files),
    ]
    if held:
        lines.append(
            f"The artefact states none of the versions those lines held, {_joined(held)}, "
            f"so what it says still holds."
        )
    else:
        lines.append("No line held a version it no longer holds, so what the artefact says holds.")
    lines.append(f"The release step wrote this answer ({RECORD}).")
    return " ".join(lines)


class _Judged:
    """The artefacts' answers as the friction writer reads the working tree's answer
    files (`friction_write`): names a committed entry carries honoured, every location a
    file had followed (COR-062 points 4, 5 and 10)."""

    def __init__(self, root: Path, discovery: Discovery) -> None:
        present = af.working_tree_files(root)
        at_head = af.head_names(root)
        locations = af.working_locations(root) if present else None
        self.discovery = discovery
        self.state = af.StateAnswers(
            present,
            lambda _reader, named: named in at_head,
            locations if locations is not None else lambda a: (a.location,),
        )

    def why_not(self, artefact: Artefact) -> str | None:
        """Why a revalidation of the artefact would claim a judgement the release step
        cannot make, or `None` (PRJ-014 point 3)."""
        judged = self.state.liveness(artefact, self.discovery)
        if judged.deferrals:
            anchors = [f"{d.anchor.kind}:{d.anchor.value}" for _e, d in judged.deferrals]
            return f"it carries a live deferral of {_joined(anchors)}"
        if len(judged.revalidations) > 1:
            return _APART
        return None


# --- writing and taking back --------------------------------------------------------


def _write(root: Path, reasons: Mapping[str, str], now: datetime | None) -> str:
    """Write each reason as the artefact's `unchanged` revalidation, through the friction
    writer, into the one answer file of the release's own; returns that file."""
    written: str | None = None
    for location, because in reasons.items():
        plan = fw.plan_revalidate(root, location, outcome=fw.UNCHANGED, because=because, now=now)
        fw.write(plan)
        written = plan.rel
    assert written is not None  # `reasons` is never empty here
    return written


def _not_standing(result: fc.ChangeCheck, written: str) -> dict[str, str]:
    """By location, each answer of the release's that the check does not accept, or flags
    as replacing answers made apart, and why it is taken back (PRJ-014 point 4)."""
    taken: dict[str, str] = {}
    for answer in result.answers:
        if answer.file != written or answer.location in taken:
            continue
        if answer.status is not fc.AnswerStatus.STANDS:
            taken[answer.location] = (
                f"the check does not accept the release's answer on it ({answer.status.value})"
            )
        elif answer.replaces_apart:
            taken[answer.location] = _APART
    return taken


# --- reading the edits --------------------------------------------------------------


def _edits(before: str, after: str) -> tuple[LineEdit, ...]:
    """The lines `after` changed of `before`, each paired with the line it replaced
    where the two stand in one block of equal length. A blank line added or removed is
    no edit, as the changeset guard tolerates one (`release.is_release_diff`)."""
    old, new = before.splitlines(), after.splitlines()
    edits: list[LineEdit] = []
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        removed, added = old[i1:i2], new[j1:j2]
        if tag == "replace" and len(removed) == len(added):
            edits.extend(LineEdit(b, a) for b, a in zip(removed, added, strict=True))
            continue
        edits.extend(LineEdit(b, None) for b in removed if b.strip())
        edits.extend(LineEdit(None, a) for a in added if a.strip())
    return tuple(edits)


def _only_version_lines(edits: Sequence[LineEdit], write: ReleaseWrite) -> bool:
    """Whether every line the edits touch is one `write` rewrites: any line of a file
    written whole, such as the backbone's version file, else one its patterns match,
    read as the changeset guard reads a changed line (`release.is_release_diff`)."""
    if not write.lines:
        return True
    touched = [line for e in edits for line in (e.before, e.after) if line and line.strip()]
    return all(any(p.match(line) for p in write.lines) for line in touched)


def _stands_in(version: str, text: str) -> bool:
    """Whether `version` stands in `text` as a whole version number: no digit or dot-led
    number runs on either side of it."""
    pattern = rf"(?<![0-9.]){re.escape(version)}(?![0-9]|\.[0-9])"
    return re.search(pattern, text) is not None


def _shown(line: str | None) -> str:
    return (line or "").strip()


def _joined(items: Sequence[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"
