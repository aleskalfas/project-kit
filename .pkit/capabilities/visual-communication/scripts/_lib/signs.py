"""The concepts a piece's scenes show with a sign, and what the checks of signs find in them
(visual-communication DEC-036 point 8).

`shown` reads, once a scene's instances are placed, each concept with a sign that an
instance or a run names, and whether only its colour tells it apart there:

- **An instance** that names a concept leaves it to its colour where a part of it, or of what
  it holds, paints from that concept's colour family, and no sign part of it or of what it
  holds draws the concept's sign. What it holds takes the concept where it takes its family
  from the instance (DEC-010 point 6, DEC-036 point 2). A state that gives an instance a
  family paints it from no concept.
- **A run** that names a concept leaves it to its colour where its text part paints it from
  that concept's family, its fill or its ground, and chooses no sign for its style (DEC-036
  point 3).

A concept with no sign is its notation's to mend (`notations`), so neither reads it.

What the checks of signs find, each in the scenes it reads (`LEFT_TO_COLOUR`, `ONE_SIGN`,
DEC-063 point 1):

- **A concept left to its colour** asks for attention, naming the owner of the component, or
  of the brand's drawing, that draws it so: `sign-missing` for an instance, `run-sign-missing`
  for a run. It lies in the component's file. `left_to_colour` gives one in each scene for
  each instance or run found so, naming it, and compares no scenes. The render gives it once
  for each version of what draws it, naming the first found so (`once_for_each_version`).
- **Two concepts of one sign**, two whose signs are one outline (`Outline.form`), ask the
  piece's author for attention once in each language whose content names both:
  `sign-shared`, naming each concept and its notation. It lies in that language's content
  file, where the second of them is first named. `one_sign` reads every scene of a language
  at once, so it compares sizes, and gives its finding for every key of that language. No
  finding judges two concepts that share a family.

`findings` gives both as the render keeps them, over every scene of a piece.

Knows nothing of files, the lock or the check's run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from _lib.findings import ATTENTION, AUTHOR, Finding
from _lib.layout import CONTENT, PAINTS, Instance, TextRun
from _lib.outlines import Outline
from _lib.scene_checks import SIZES, SceneCheck

#: The calls for attention on a concept left to its colour: by an instance, and by a run.
SIGN_MISSING = "sign-missing"
RUN_SIGN_MISSING = "run-sign-missing"

#: The call for attention on two concepts of one piece whose signs are one outline.
SIGN_SHARED = "sign-shared"

#: The check of a concept left to its colour, which gives each place it found in each scene,
#: and the check of two concepts of one sign, which reads every scene of a language at once
#: (DEC-036 point 8, DEC-063 point 1).
LEFT_TO_COLOUR = SceneCheck("a concept told apart by its colour alone")
ONE_SIGN = SceneCheck("concepts of one language whose signs are one outline", frozenset({SIZES}))


@dataclass(frozen=True)
class Shown:
    """A concept with a sign that an instance or a run names, as one scene shows it.

    - `concept`, `<notation>/<concept>`; `notation`, its notation's `<name>@<version>`; and
      `outline`, its sign.
    - `named`: the key path in the content file that names it; "" where no content does, as
      where a component's part gives it.
    - `component`: the component that draws the instance or the run; `library`, the
      `<library>@<version>` it lies in, "" for the piece's own.
    - `trace`: the instance's trace id, or the run's text's.
    - `alone`: only its colour tells it apart there.
    - `part`, `run` and `style`: for a run, its text part, its place and its word; "" for an
      instance.
    """

    concept: str
    notation: str
    outline: Outline
    named: str
    component: str
    library: str
    trace: str
    alone: bool
    part: str = ""
    run: str = ""
    style: str = ""


def shown(top: Instance) -> list[Shown]:
    """Each concept with a sign that an instance or a run names in the scene placed from
    `top`: each run's as the walk meets it, then each instance's."""
    found: list[Shown] = []
    named: list[Instance] = []
    coloured: set[int] = set()  # the instances whose concept's family a part paints
    signed: set[int] = set()  # the instances whose concept's sign a part draws
    for instance in (top, *top.below()):
        if instance.named_by is instance:
            named.append(instance)
        for name, node in instance.nodes.items():
            if not node.present:
                continue
            kind = node.part.kind
            if kind == "sign":
                if instance.named_by is not None:
                    signed.add(id(instance.named_by))
                continue
            for run in node.runs if kind == "text" else ():
                painted = any(instance.from_family(name, prop, run) for prop in ("fill", "ground"))
                if run.outline is not None:
                    alone = run.own_family and painted and instance.run_sign(name, run) is None
                    found.append(_run(instance, name, run, run.outline, alone))
                if not run.own_family and painted and instance.coloured_by is not None:
                    coloured.add(id(instance.coloured_by))
            if kind != "text" and any(instance.from_family(name, prop) for prop in PAINTS):
                if instance.coloured_by is not None:
                    coloured.add(id(instance.coloured_by))
    for instance in named:
        concept = str(instance.concept)
        outline = instance.ctx.sign(concept)
        if outline is None:
            continue
        source = instance.concept_source
        found.append(
            Shown(
                concept,
                instance.ctx.library(concept),
                outline,
                source[len(CONTENT) :] if source.startswith(CONTENT) else "",
                instance.component.use,
                instance.library,
                instance.trace,
                id(instance) in coloured and id(instance) not in signed,
            )
        )
    return found


def _run(instance: Instance, name: str, run: TextRun, outline: Outline, alone: bool) -> Shown:
    """A run's concept, as its text part `name` of `instance` shows it."""
    concept = str(run.concept)
    return Shown(
        concept,
        instance.ctx.library(concept),
        outline,
        run.place if run.source.startswith(CONTENT) else "",
        instance.component.use,
        instance.library,
        f"{instance.trace}/{name}",
        alone,
        part=name,
        run=run.place,
        style=run.word or "",
    )


def findings(scenes: Sequence[tuple[str, Sequence[Shown]]]) -> list[Finding]:
    """What the checks of signs find in a piece's scenes, as the render keeps them, each
    scene given as its language's content file with what it shows: each concept left to its
    colour, once for each version of what draws it, and each set of concepts of one sign,
    once in each language."""
    alone = once_for_each_version(
        [finding for _, shown in scenes for finding in left_to_colour(shown)]
    )
    return [*alone, *(finding for _, finding in one_sign(scenes))]


def left_to_colour(shown: Sequence[Shown]) -> list[Finding]:
    """Each concept that one scene, `shown`, leaves to its colour, one finding for each
    instance or run found so, naming it, and holding its trace id as its place."""
    return [_alone(one) for one in shown if one.alone]


def once_for_each_version(found: Sequence[Finding]) -> list[Finding]:
    """The render's merge of `left_to_colour`'s findings, over every scene: once for each
    version of the component, or of the brand's drawing, that leaves a concept to its colour,
    the first found so."""
    kept: dict[tuple[str, str, str], Finding] = {}
    for finding in found:
        component = str(finding.extra["component"])
        kept.setdefault((finding.code, finding.library, component), finding)
    return list(kept.values())


def one_sign(scenes: Sequence[tuple[str, Sequence[Shown]]]) -> list[tuple[str, Finding]]:
    """Each set of concepts of one sign that a language's content names, read over every
    scene of that language, each scene given as its language's content file with what it
    shows: the content file, with its finding."""
    forms: dict[str, dict[str, dict[str, Shown]]] = {}
    for content, each in scenes:
        by_form = forms.setdefault(content, {})
        for one in each:
            if one.named:
                by_form.setdefault(one.outline.form(), {}).setdefault(one.concept, one)
    return [
        (content, _shared(content, list(concepts.values())))
        for content, by_form in forms.items()
        for concepts in by_form.values()
        if len(concepts) > 1
    ]


def _alone(one: Shown) -> Finding:
    """The call for attention on a concept left to its colour, in the component that draws
    it so, naming its owner."""
    use = one.component
    if one.part:
        code, where = RUN_SIGN_MISSING, f"parts.{one.part}.text"
        message = (
            f"{one.trace}: the run {one.run} names the concept `{one.concept}`, and the text "
            f"`{one.part}` paints it from that concept's colour family in the style "
            f"`{one.style}`, for which it chooses no sign, so its colour alone tells the "
            "concept apart"
        )
        fix = f"have the text `{one.part}` of `{use}` choose a sign for the style `{one.style}`"
    else:
        code, where = SIGN_MISSING, "parts"
        message = (
            f"{one.trace} names the concept `{one.concept}`: a part of it, or of what it holds, "
            "paints from that concept's colour family, and none draws its sign, so its colour "
            "alone tells the concept apart"
        )
        fix = f"give `{use}` a sign part, which draws the sign of its instance's concept"
    if one.library:
        fix = f"{fix}, in a version of its own"
    who = f"the owner of `{one.library.partition('@')[0]}`" if one.library else AUTHOR
    return Finding(
        code,
        ATTENTION,
        message,
        where=where,
        fix=fix,
        library=one.library,
        who=who,
        extra={"component": use, "place": one.trace},
    )


def _shared(content: str, concepts: Sequence[Shown]) -> Finding:
    """The call for attention on concepts of one piece whose signs are one outline, in its
    content file of one language, where the second of them is first named."""
    each = [f"`{one.concept}`, of the notation {one.notation}" for one in concepts]
    listed = ", ".join(each[:-1]) + f" and {each[-1]}"
    return Finding(
        SIGN_SHARED,
        ATTENTION,
        f"the concepts {listed} have one sign, so their signs do not tell them apart",
        file=content,
        where=concepts[1].named,
        fix="map one of them to another icon or shape in its notation, or ask the notation's "
        "owner to; or name only one of them in this piece",
        who=AUTHOR,
    )
