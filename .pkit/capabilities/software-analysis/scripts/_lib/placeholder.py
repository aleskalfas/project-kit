"""A placeholder a person fills: words in angle brackets.

Two readings, each where it is safe:

- **By shape**, for a text a person gives a writer. A command shown for a
  person to run writes what only they can supply in angle brackets — `<the
  defect reference>`, `<your name>`. Run as shown, it would write the
  placeholder as though it were their words. The backbone's friction writers
  refuse a justification or a reason still holding one; the record stamp
  refuses its texts by the same shape (`unfilled`), so a command run as shown
  writes nothing until its placeholders are filled. A bracket with no space
  inside, or opening in capitals, is code (`Vec<u8>`, `Map<String, int>`), not
  a placeholder.
- **By the texts shipped**, for an artefact. What the stamp leaves for a person
  to write is a template's placeholder, and what a person passes the artefact
  stamp comes from the skill's commands, so an artefact — its own fields, its
  body — and the artefact stamp's texts are matched against exactly those
  (`left_in`): the capitalised ones a shape would take for code (`<Title>`,
  `<Term>`) are caught, and words of the artefact's own in angle brackets
  (`maps <user id> to a session`, code a body quotes) never are. The lists are
  append-only: a template reworded keeps its old placeholder here, so what was
  stamped before still fails until it is filled. A test holds them to the
  templates and the skill.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

#: The shape both the backbone's writers and the record stamp refuse.
PLACEHOLDER = re.compile(r"<[a-z][^<>\n]*\s[^<>\n]*>")

#: Every placeholder the artefact templates (`templates/actors.md`, `glossary.md`,
#: `use-case.md`, `journey.md`) ever shipped in a front matter's value or a body.
#: Append-only.
IN_TEMPLATES = (
    "<Display name>",
    "<what this actor needs from the system, in one sentence>",
    "<code that embodies it>",
    "<decision that names it>",
    "<Who this is, when they come to the system, and what they bring with them.>",
    "<Term>",
    "<what the term means, in one sentence>",
    "<decision that defines it>",
    "<More on the term when one sentence is not enough: where it applies, what it is not, "
    "an example.>",
    "<Title>",
    "<code it exercises>",
    "<decision it relies on>",
    "<what the actor wants to achieve, in one sentence>",
    "<what triggers it>",
    "<what the actor or the system does>",
    "<…>",
    "<the condition at step 1, what happens instead, and where the path rejoins or ends>",
    "<the state that shows the goal is met>",
    "<code at a seam between two steps>",
    "<where the actor begins, and what they want by the end>",
    "<what the actor achieves in this use case>",
    "<what carries over, and how it could break>",
    "<the state that shows the whole path succeeded>",
)

#: Every placeholder the `analysis-author` skill's commands ever showed for a text the
#: artefact stamp writes — its `--title`, `--name` or `--unanchored-because` — that
#: the templates do not ship. Append-only.
IN_COMMANDS = (
    "<why nothing embodies it>",
    "<why>",
)

#: What an artefact's own fields, and the artefact stamp's texts, are matched against.
SHIPPED = IN_TEMPLATES + IN_COMMANDS


def unfilled(text: str) -> str | None:
    """The first placeholder `text` still holds by shape, or `None`."""
    found = PLACEHOLDER.search(text)
    return None if found is None else found.group(0)


def left_in(text: str, shipped: Sequence[str] = SHIPPED) -> list[str]:
    """Each placeholder of `shipped` that `text` still holds, matched exactly, in the
    order they stand."""
    return [p for _at, p in sorted((text.find(p), p) for p in set(shipped) if p in text)]
