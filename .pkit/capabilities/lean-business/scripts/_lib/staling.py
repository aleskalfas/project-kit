"""What a write leaves stale: each judgement whose fingerprint matched the files before the
write and no longer does after it (lean-business DEC-002 point 13; DEC-003 point 2).

A change to a canvas's content, or to the idea's goal, may change what a standing verdict
or a shortlisting judged. It is never refused, since content is no judgement and stays
editable, but the command names each judgement it leaves stale, so the person knows to
judge again. A shortlisting left stale is said louder where a cycle not yet reviewed
explores its variant: no experiment is declared on that variant until the person judges it
and shortlists it again (DEC-003 point 7).

A judgement already stale before the write, or one the write itself takes again or
clears, is not named: the write did not make it stale. Nor is a verdict of a variant
shelved or split, whose content stays editable: those outcomes are final, so nothing rests
on its verdicts any more, and no verdict of it is judged again (DEC-002 point 13).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from _lib import fingerprint, gates, layout
from _lib.reading import ReadError, load_yaml
from _lib.writes import Files


@dataclass(frozen=True)
class Stale:
    """A judgement a write leaves stale, in words, and whether to say it louder."""

    line: str
    loud: bool = False


#: The outcomes that are final, on whose variant's verdicts nothing rests any more.
FINAL = ("shelved", "split")

#: The label of the check's findings on a judgement that is stale, which a command names in
#: its own words rather than again as the check's.
LABEL = "stale"


def stale(files: Files) -> list[Stale]:
    """What the write `files` leaves stale, one for each judgement."""
    lines: list[Stale] = []
    for idea in _ideas(files):
        lines.extend(_idea(files, idea))
    return lines


def _ideas(files: Files) -> list[str]:
    """Each idea whose folder the write changes a file in."""
    found: list[str] = []
    prefix = PurePosixPath(files.location)
    for rel in files.texts:
        path = PurePosixPath(rel)
        if not path.is_relative_to(prefix) or len(path.relative_to(prefix).parts) < 2:
            continue
        idea = path.relative_to(prefix).parts[0]
        if idea not in found:
            found.append(idea)
    return found


def _idea(files: Files, idea: str) -> list[Stale]:
    folder = f"{files.location}/{idea}"
    goal_rel = f"{folder}/{layout.GOAL}"
    goal_before, goal_after = _before(files, goal_rel), _after(files, goal_rel)
    cycles = _cycles(files, folder)
    lines: list[Stale] = []
    for rel in _canvases(files, folder):
        stood, becomes = _before(files, rel), _after(files, rel)
        if not isinstance(stood, Mapping) or not isinstance(becomes, Mapping):
            continue
        if _kind(becomes) in FINAL:
            continue
        variant = becomes.get("id")
        for step in fingerprint.STEPS:
            if _verdict(stood, step) is None or _verdict(stood, step) != _verdict(becomes, step):
                continue
            if (
                fingerprint.check_verdict(step, stood, goal_before).fresh
                and fingerprint.check_verdict(step, becomes, goal_after).stale
            ):
                lines.append(
                    Stale(
                        f"the verdict on {step} of `{variant}` is stale after this change: what "
                        f"it judged changed, so judge the step again, `pkit lean judge "
                        f"{variant} {step}`"
                    )
                )
        outcome = _outcome(becomes)
        if outcome is None or outcome != _outcome(stood) or outcome.get("kind") != "shortlisted":
            continue
        if not (
            fingerprint.check_shortlisting(stood, goal_before).fresh
            and fingerprint.check_shortlisting(becomes, goal_after).stale
        ):
            continue
        exploring = [c for c in cycles if variant in gates.explored(c)]
        if exploring:
            named = ", ".join(f"`{c.get('id')}`" for c in exploring)
            lines.append(
                Stale(
                    f"the shortlisting of `{variant}` is stale after this change, and {named}, "
                    f"not yet reviewed, explores it: no experiment is declared on it until you "
                    f"judge it and shortlist it again",
                    loud=True,
                )
            )
        else:
            lines.append(
                Stale(
                    f"the shortlisting of `{variant}` is stale after this change: judge it and "
                    f"shortlist it again before an experiment rests on it"
                )
            )
    return lines


def _verdict(canvas: Mapping[str, Any], step: str) -> object:
    verdicts = canvas.get("verdicts")
    return verdicts.get(step) if isinstance(verdicts, Mapping) else None


def _outcome(canvas: Mapping[str, Any]) -> Mapping[str, Any] | None:
    outcome = canvas.get("outcome")
    return outcome if isinstance(outcome, Mapping) else None


def _kind(canvas: Mapping[str, Any]) -> object:
    outcome = _outcome(canvas)
    return outcome.get("kind") if outcome is not None else None


def _canvases(files: Files, folder: str) -> list[str]:
    """Each canvas of the idea whose folder is `folder`, as the files stand or the write
    leaves them, by its path."""
    variants = files.root / folder / layout.VARIANTS
    found = {
        f"{folder}/{layout.VARIANTS}/{held.name}/{layout.CANVAS}"
        for held in (variants.iterdir() if variants.is_dir() else [])
        if (held / layout.CANVAS).is_file()
    }
    found.update(
        rel
        for rel in files.texts
        if rel.startswith(f"{folder}/{layout.VARIANTS}/") and rel.endswith(f"/{layout.CANVAS}")
    )
    return sorted(found)


def _cycles(files: Files, folder: str) -> list[Mapping[str, Any]]:
    """Each cycle of the idea not yet reviewed, as the write leaves it."""
    held = files.root / folder / layout.CYCLES
    rels = {
        f"{folder}/{layout.CYCLES}/{path.name}"
        for path in (held.iterdir() if held.is_dir() else [])
        if path.name.endswith(layout.SUFFIX)
    }
    rels.update(rel for rel in files.texts if rel.startswith(f"{folder}/{layout.CYCLES}/"))
    found: list[Mapping[str, Any]] = []
    for rel in sorted(rels):
        data = _after(files, rel)
        if isinstance(data, Mapping) and not isinstance(data.get("review"), Mapping):
            found.append(data)
    return found


def _before(files: Files, rel: str) -> Any:
    path = files.root / rel
    if not path.is_file():
        return None
    try:
        return load_yaml(path.read_bytes().decode("utf-8"), rel)
    except (OSError, UnicodeDecodeError, ReadError):
        return None


def _after(files: Files, rel: str) -> Any:
    if rel not in files.texts:
        return _before(files, rel)
    text = files.texts[rel]
    if text is None:
        return None
    try:
        return load_yaml(text, rel)
    except ReadError:
        return None
