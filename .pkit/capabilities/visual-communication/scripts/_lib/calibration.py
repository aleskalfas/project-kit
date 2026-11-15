"""The accepted calibration's data, and whether the verdict ends the designer's loop
(visual-communication DEC-042 points 9 and 10).

- **The data.** A refinement of DEC-042 writes it when whoever maintains the capability
  accepts a calibration's report: `calibration.yaml` in the capability's folder, bound to
  `visual-communication:calibration`. Nothing else writes it, and this module only reads
  it. Absent, no report is accepted. It holds each rule with evidence of its own in the
  accepted report, with its set's major and a digest of its text; a digest of the
  reviewer's definition and one of the design knowledge; and the model the review ran on,
  with its effort where the harness has one.
- **The reading** is the same values as they stand now: each rule the bar covers, with its
  set's major and a digest of its text; the two digests; and the model the round's report
  names. It has the data's shape, so the change that writes the data can take it from the
  reading of the state the calibration ran on.
- **The hold is on** where a report is accepted, the bar covers only rules with evidence of
  their own in it (point 10), and nothing has lapsed (point 9): no covered set's major, no
  covered rule's text, neither definition, nor the model or its effort differs from the
  data. Otherwise each reason it is off is said. A lapse only withdraws the hold: nothing
  here starts a calibration.
- **Each digest** is SHA-256, written `sha256:<hex>`, as a deploy's mark writes the digest of
  an agent's definition:
  - a rule's text, its section in the body of its set's file (`bar.rule_text`), as UTF-8;
  - the reviewer's definition: the bytes of the capability's own
    `agents/graphic-design-reviewer.md`, as the deploy digests the file it writes from;
  - the design knowledge: the canonical text (RFC 8785) of the SHA-256 of each file in the
    capability's `design-knowledge/`, by its path within that folder.
- **Another definition of the reviewer.** The deploy runs the definition of a name that
  wins among the places that ship one, and the project's place wins over every other
  (COR-013 point 8). A capability cannot ask the picker that decides it (ADR-057 point 1),
  so the reading names each definition of the reviewer's name in the project's place, or in
  another capability's, and the hold lapses while one stands: the command cannot tell that
  the calibrated reviewer ran.

Reads only, and needs no network.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import files
from _lib.bar import Covered, rule_text
from _lib.reading import ReadError, canonical_bytes, sha256
from _lib.root import CAPABILITIES_DIR, SHIPPED

#: The accepted calibration's data, in the capability's folder, and its kind of file.
DATA = SHIPPED / "calibration.yaml"
KIND = "calibration"

#: The reviewer, by its name, and its definition in the capability's folder.
REVIEWER = "graphic-design-reviewer"
DEFINITION = SHIPPED / "agents" / f"{REVIEWER}.md"

#: The design knowledge's folder (DEC-030 point 8).
DESIGN_KNOWLEDGE = SHIPPED / "design-knowledge"

#: The project's place of agents' definitions, relative to the project root.
PROJECT_AGENTS = ".pkit/agents/project"

#: How a digest is written: the algorithm's name, a colon, the hex digest.
ALGORITHM = "sha256"

#: The record's points, as the reasons cite them.
LAPSES = "DEC-042 point 9"
REACHES = "DEC-042 point 10"


class Unreadable(Exception):
    """The accepted calibration's data cannot be read; the message says why."""


@dataclass(frozen=True)
class Reading:
    """The values the hold is compared on, as they stand now, in the data's shape: each
    rule covered with its set's major and the digest of its text, the digest of the
    reviewer's definition, or None where the capability ships none, the digest of the
    design knowledge, and the model. `others` are the other definitions of the reviewer's
    name in the project, each by its path."""

    rules: Mapping[str, Mapping[str, Any]]
    reviewer: str | None
    design_knowledge: str
    model: Mapping[str, Any]
    others: tuple[str, ...]

    def as_data(self) -> dict[str, Any]:
        """The reading in the shape of the accepted calibration's data, without its
        binding."""
        return {
            "rules": {rule: dict(values) for rule, values in self.rules.items()},
            "reviewer": self.reviewer,
            "design-knowledge": self.design_knowledge,
            "model": dict(self.model),
        }


def digest(data: bytes) -> str:
    """The digest of `data`, written as a deploy's mark writes it."""
    return f"{ALGORITHM}:{sha256(data)}"


def read(root: Path, covered: Sequence[Covered], model: Mapping[str, Any]) -> Reading:
    """The reading of the project at `root`, for the rules a bar covers and the model a
    round's report names."""
    return Reading(
        rules={
            each.rule: {
                "major": each.held_by.major,
                "text": digest(rule_text(each.held_by.path, each.rule).encode("utf-8")),
            }
            for each in covered
        },
        reviewer=digest(DEFINITION.read_bytes()) if DEFINITION.is_file() else None,
        design_knowledge=folder_digest(DESIGN_KNOWLEDGE),
        model={key: model[key] for key in ("name", "effort") if key in model},
        others=tuple(_other_definitions(root)),
    )


def accepted() -> dict[str, Any] | None:
    """The accepted calibration's data, or None where the capability ships none. Raises
    Unreadable where it cannot be read, or its schema refuses it."""
    if not DATA.exists():
        return None
    try:
        data = files.read_bound(DATA, KIND)
    except (files.FileError, ReadError) as exc:
        raise Unreadable(str(exc)) from exc
    problems = files.shape_problems(data, KIND)
    if problems:
        raise Unreadable(f"{DATA.name}: its schema refuses it: {'; '.join(problems)}")
    return data


def off(reading: Reading, data: Mapping[str, Any] | None) -> list[str]:
    """Each reason the hold is off, for `reading` against the accepted `data`; none where it
    is on."""
    if data is None:
        return [
            f"no calibration's report is accepted: the capability ships no `{DATA.name}`, the "
            f"data a refinement of DEC-042 writes when its maintainer accepts one ({LAPSES})"
        ]
    calibrated: Mapping[str, Mapping[str, Any]] = data["rules"]
    reasons = []
    past = [rule for rule in reading.rules if rule not in calibrated]
    if past:
        reasons.append(
            f"the bar reaches past the accepted calibration, whose report gives no evidence of "
            f"its own for {_named(past)} ({REACHES})"
        )
    for rule, now in reading.rules.items():
        then = calibrated.get(rule)
        if then is None:
            continue
        if now["major"] != then["major"]:
            reasons.append(
                f"the set of `{rule}` is at major {now['major']}, and the calibration read major "
                f"{then['major']} ({LAPSES})"
            )
        elif now["text"] != then["text"]:
            reasons.append(
                f"the text of `{rule}` differs from the text the calibration read ({LAPSES})"
            )
    reasons.extend(_definitions_off(reading, data))
    reasons.extend(_model_off(reading.model, data["model"]))
    return reasons


def folder_digest(folder: Path) -> str:
    """The digest of the files in `folder`, at any depth: the canonical text of each one's
    SHA-256, by its path within the folder."""
    found = (
        {
            path.relative_to(folder).as_posix(): sha256(path.read_bytes())
            for path in sorted(folder.rglob("*"))
            if path.is_file()
        }
        if folder.is_dir()
        else {}
    )
    return digest(canonical_bytes(found))


def _definitions_off(reading: Reading, data: Mapping[str, Any]) -> list[str]:
    reasons = []
    if reading.others:
        reasons.append(
            f"another definition of `{REVIEWER}` stands in the project, in "
            f"{_named(reading.others)}: the command reads only the capability's own, so it "
            f"cannot tell that the calibrated reviewer ran ({LAPSES})"
        )
    if reading.reviewer is None:
        reasons.append(f"the capability ships no definition of `{REVIEWER}` ({LAPSES})")
    elif reading.reviewer != data["reviewer"]:
        reasons.append(
            f"the reviewer's definition differs from the one the calibration read ({LAPSES})"
        )
    if reading.design_knowledge != data["design-knowledge"]:
        reasons.append(f"the design knowledge differs from the one the calibration read ({LAPSES})")
    return reasons


def _model_off(now: Mapping[str, Any], then: Mapping[str, Any]) -> list[str]:
    reasons = []
    if now.get("name") != then.get("name"):
        reasons.append(
            f"the review ran on the model `{now.get('name')}`, and the calibration on "
            f"`{then.get('name')}` ({LAPSES})"
        )
    if now.get("effort") != then.get("effort"):
        reasons.append(
            f"the review ran {_effort(now)}, and the calibration {_effort(then)} ({LAPSES})"
        )
    return reasons


def _effort(model: Mapping[str, Any]) -> str:
    effort = model.get("effort")
    return f"at the effort `{effort}`" if effort is not None else "with no effort named"


def _other_definitions(root: Path) -> Iterable[str]:
    """Each definition of the reviewer's name in the project's place, or in a capability's
    place other than this one's file, by its path relative to `root`, in name order."""
    own = DEFINITION.resolve()
    places = [root / PROJECT_AGENTS]
    capabilities = root / CAPABILITIES_DIR
    if capabilities.is_dir():
        places += [folder / "agents" for folder in sorted(capabilities.iterdir())]
    for place in places:
        for path in (place / f"{REVIEWER}.md", place / REVIEWER / f"{REVIEWER}.md"):
            if path.is_file() and path.resolve() != own:
                yield path.relative_to(root).as_posix()


def _named(items: Sequence[str]) -> str:
    return ", ".join(f"`{each}`" for each in items)
