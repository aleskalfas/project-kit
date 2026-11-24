"""What a scene check states of itself in its code (visual-communication DEC-063 point 1,
DEC-062 points 1 and 2).

A *scene check* is a check whose findings come from computing a scene, whatever they point
at. Each meets two duties, whether or not it states a reach:

- **It gives its findings scene by scene** (`Found`), each tagged with its scene's language
  and key over the size axes, and with its page where its place lies on one. A finding that
  holds alike in every language, or at every key, says so in place of naming one. A check of
  colour names, beside its scene, the combinations each finding holds for. Any merging of
  findings across scenes, pages or languages is the render's own code's
  (`checks.scene_findings`), in one place for every check.
- **It states the axes it compares scenes across** (`SceneCheck.compares`): the sizes, the
  languages, both, or none. A check compares scenes where its finding in one scene depends
  on another. One that reads several scenes only to give a finding once compares none. So
  whatever runs the check knows which scenes to compute, and a reader knows which scenes a
  silence rests on.

**Its reach** (`Reach`), where a reader leans on its silence: the kinds of place it measures
and those it leaves out, in the words of its entry in the capability's list of checks
(`checks.md`), beside an id of the check's own that stays as the check changes. A test holds
the two texts equal, joined on the id. A check that states no reach counts as having measured
no place, whatever it found: its findings still reach every reader, and only its silence
counts for nothing. A check with a reach that could measure nothing at a place of a kind it
measures states so in the piece, as a fact, under a label its reach names (`statements`).

Knows nothing of files, scenes or the check's run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from _lib.findings import Finding

#: The axes a check may compare scenes across (DEC-063 point 1).
SIZES = "sizes"
LANGUAGES = "languages"


@dataclass(frozen=True)
class Reach:
    """The kinds of place a scene check measures and those it leaves out, each a clause in
    the words of its entry, and what it states as a fact where it could measure nothing:
    each such statement in words (`states`), and the label of each (`statements`)."""

    measures: tuple[str, ...]
    leaves_out: tuple[str, ...]
    states: tuple[str, ...] = ()
    statements: tuple[str, ...] = ()

    def said(self, id_: str) -> str:
        """The reach in the words of its entry in the list of checks, which shows `id_`."""
        text = (
            f"**Its reach**, `{id_}`. It measures: {'; '.join(self.measures)}. "
            f"It leaves out: {'; '.join(self.leaves_out)}."
        )
        if self.states:
            text += f" Where it could measure nothing, it states so: {'; '.join(self.states)}."
        return text


@dataclass(frozen=True)
class SceneCheck:
    """A scene check as its code states it: what it is, in a few words, for whoever reads the
    code; the axes it compares scenes across; whether it measures a scene in each combination
    of modes it serves, a check of colour; and, where a reader leans on its silence, its id
    and its reach, with the labels its findings carry."""

    about: str
    compares: frozenset[str] = frozenset()
    colour: bool = False
    id: str = ""
    labels: tuple[str, ...] = ()
    reach: Reach | None = None

    def __post_init__(self) -> None:
        if (self.reach is None) != (not self.id):
            raise ValueError(f"a check states its reach beside its id: {self.about}")
        if not self.compares <= {SIZES, LANGUAGES}:
            raise ValueError(f"a check compares only sizes and languages: {self.about}")

    def reach_said(self) -> dict[str, Any]:
        """Its reach as the viewing step's report carries it, by the code that ran."""
        assert self.reach is not None
        return {
            "labels": list(self.labels),
            "compares": sorted(self.compares),
            "colour": self.colour,
            "measures": list(self.reach.measures),
            "leaves-out": list(self.reach.leaves_out),
            "states": list(self.reach.states),
            "statements": list(self.reach.statements),
        }


@dataclass(frozen=True)
class Found:
    """A finding as its check gives it in one scene, before the render's code merges it.

    - `language`: the scene's language; None where the check gives it for every language.
    - `size`: the scene's key over the size axes; None where it gives it for every key.
    - `combinations`: for a finding of a check of colour, each whole key it holds for; none
      where it names none, and for every other finding, which holds alike in every
      combination its scene serves.
    - `page`: the trace id of the page its place lies on; None where its place lies on no
      page, such as content a size hides.
    """

    finding: Finding
    check: SceneCheck
    language: str | None
    size: str | None
    combinations: tuple[str, ...] = ()
    page: str | None = None
