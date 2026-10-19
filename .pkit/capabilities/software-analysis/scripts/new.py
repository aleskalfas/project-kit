#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — new: stamp an artefact or a revalidation record.

Writes one artefact under the analysis location — the `analysis` sub-path of
the internal documentation root, recorded the first time an artefact is placed
there (COR-049 point 5). Its front matter comes from its kind's template, and
its body is rendered from its kind's declared structure, each part holding its
hint until a person writes it (DEC-001 point 1):

- a use case, `use-case-model/use-cases/[<area>/]UC-NNN-<slug>.md`, with its
  actor, its other actors and the requirements it must meet, and an anchor to
  each;
- a journey, `use-case-model/journeys/JRN-NNN-<slug>.md`, with its steps, the
  use cases outside it that a step relies on and the requirements that bind its
  whole path, an anchor to its actor and to each requirement and, from the two
  lists of use cases, its use-case anchors;
- an actor, `use-case-model/actors/ACT-<slug>.md`, headed by its id and name,
  with its needs in its front matter;
- a term, the entry `TERM-<slug>` of `glossary.md`;
- a requirement of each of the three kinds (DEC-002),
  `requirements/<quality|functional|constraints>/[<area>/]REQ-NNN-<slug>.md`,
  headed by its id, its kind and its title, with its actors and the
  requirements it refines, and an anchor to each.

A use case, a journey or a requirement takes the next free number on the
default branch — a requirement's across its three kinds' places — every
number its history ever gave a file included, but an id the project's
numbering setting frees (`_lib/numbering.py`) — on a base named with `--base`,
and in the working tree; `$PKIT_CHECK_BASE`, a pipeline's base for its checks,
never moves where it numbers from (COR-054 point 3). `pkit analysis
check-numbers` reports a number another branch took first. `_lib/stamp.py`
states the rules.

It also writes a revalidation record, `revalidations/<date>-<slug>.md`, and only
one with something to say — a planned revalidation, one that found a
regression or a gap (point 6), or one where a person decided an artefact was
stale (point 5); `_lib/revalidation.py` states the rules. A planned record names
each source of the design it reviewed, one `--reviewed-against` each, and the
stamp warns of a commit the default branch does not hold. Each gap names the
artefacts it affects.

Usage:
  pkit analysis new use-case <slug> --actor <ACT-id> [--other-actor <ACT-id>]...
      [--requirement <REQ-id>]... [--area <area>] [--title <text>]
  pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id>...
      [--relies-on <UC-id>]... [--requirement <REQ-id>]... [--title <text>]
  pkit analysis new actor <slug> [--name <text>] [--unanchored-because <text>]
  pkit analysis new term <slug> [--name <text>] [--unanchored-because <text>]
  pkit analysis new <quality-requirement|functional-requirement|constraint> <slug>
      [--actor <ACT-id>]... [--refines <REQ-id>]... [--area <area>]
      [--title <text>] [--unanchored-because <text>]
  each also: [--path <glob>]... [--record <id>]... [--base <ref>]
      [--analysis <component>]

  pkit analysis new revalidation <slug> --change <ref> --trigger <trigger>
      --outcome <id>=<outcome>... --because <id>=<text>...
      [--reviewed-against "<title> @ <version> [@ <link>]"]...
      [--gap "<ids>: <gap> => <resolution>"]... [--by <who> | --by-agent <name>]
      [--confirmed-by <who>] [--title <text>] [--analysis <component>]

Where the project lists several analyses in its configuration, one per component
(DEC-001 point 2), `--analysis` names the one to write in, and what is written
lies in that analysis's folder; it may be left out where the list holds one. An
actor of an analysis it builds on is named with that analysis, such as
`--actor core:ACT-developer`, and resolves against the actors its glossary's head
lists from it; nothing anchors it, so `--record` names the records behind it.

Exit codes:
  0  stamped, with any warning on standard error
  1  refused — the message says why
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, revalidation, schemas, stamp
from _lib.model import ACTOR, CONSTRAINT, FUNCTIONAL, JOURNEY, KINDS, QUALITY, TERM, USE_CASE
from _lib.placeholder import unfilled

#: The kind a revalidation record is stamped as.
REVALIDATION = "revalidation"

#: What parts a gap from what resolved it, in `--gap "<ids>: <gap> => <resolution>"`,
#: and the ids of the artefacts it affects from the gap.
GAP_SEPARATOR = " => "
IDS_SEPARATOR = ":"


def _pair(value: str) -> tuple[str, str]:
    """`<id>=<text>`, as `--outcome` and `--because` take it."""
    artefact_id, sep, text = value.partition("=")
    if not sep or not artefact_id.strip() or not text.strip():
        raise argparse.ArgumentTypeError(f"{value!r} is not <id>=<text>")
    return artefact_id.strip(), text.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pkit analysis new",
        description="Stamp an analysis artefact or a revalidation record under the analysis "
        "location (software-analysis DEC-001 and DEC-002).",
    )
    kinds = parser.add_subparsers(dest="kind", required=True, metavar="KIND")

    def kind(name: str, help_text: str, title: str) -> argparse.ArgumentParser:
        sub = kinds.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("slug", help="A word naming it: lowercase letters, digits and hyphens.")
        sub.add_argument(
            f"--{title}", dest="title", metavar="TEXT", help=f"Its {title} (default: the slug)."
        )
        sub.add_argument(
            "--path",
            dest="paths",
            action="append",
            default=[],
            metavar="GLOB",
            help="A path anchor: code that makes it true (repeatable).",
        )
        sub.add_argument(
            "--record",
            dest="records",
            action="append",
            default=[],
            metavar="ID",
            help="A record anchor: a decision it relies on (repeatable).",
        )
        sub.add_argument(
            "--base",
            metavar="REF",
            default=None,
            help="A branch whose ids count as taken beside the default branch's, which always "
            "do; $PKIT_CHECK_BASE never does.",
        )
        _analysis_argument(sub)
        return sub

    use_case = kind(USE_CASE, "A use case: one actor's goal and how it is fulfilled.", "title")
    use_case.add_argument("--actor", required=True, metavar="ACT-ID", help="Whose goal it is.")
    use_case.add_argument(
        "--other-actor",
        dest="other_actors",
        action="append",
        default=[],
        metavar="ACT-ID",
        help="Another actor who takes part, written in `other-actors` and anchored (repeatable).",
    )
    use_case.add_argument(
        "--requirement",
        dest="requirements",
        action="append",
        default=[],
        metavar="REQ-ID",
        help="A requirement it must meet, of any of the three kinds, written in `requirements` "
        "and anchored (repeatable).",
    )
    use_case.add_argument(
        "--area", metavar="WORD", help="The functional area's folder to put it in."
    )
    journey = kind(JOURNEY, "A journey: one actor's path across several use cases.", "title")
    journey.add_argument("--actor", required=True, metavar="ACT-ID", help="Who takes it.")
    journey.add_argument(
        "--step",
        dest="steps",
        action="append",
        default=[],
        metavar="UC-ID",
        help="A use case it passes through, in order (at least two).",
    )
    journey.add_argument(
        "--relies-on",
        dest="relies_on",
        action="append",
        default=[],
        metavar="UC-ID",
        help="A use case outside the journey that a step relies on, written in `relies-on` "
        "and anchored (repeatable).",
    )
    journey.add_argument(
        "--requirement",
        dest="requirements",
        action="append",
        default=[],
        metavar="REQ-ID",
        help="A requirement that binds the journey's whole path, of any of the three kinds, "
        "written in `requirements` and anchored (repeatable). One that binds a single step is "
        "that step's use case's to list.",
    )
    entries = (
        kind(ACTOR, "An actor: a named role that uses the system, and its needs.", "name"),
        kind(TERM, "A glossary term: a domain word and what it means.", "name"),
    )
    for entry in entries:
        entry.add_argument(
            "--unanchored-because",
            metavar="TEXT",
            help=(
                "Why nothing embodies it, so it has no anchors (instead of --path/--record): "
                "written as `unanchored-because` in its friction block."
            ),
        )
    requirements = (
        kind(
            QUALITY,
            "A quality requirement: how well the system must behave, such as how fast, how "
            "reliably or how safely.",
            "title",
        ),
        kind(
            FUNCTIONAL,
            "A functional requirement: behaviour that holds across use cases, such as a "
            "business rule. Behaviour that serves one actor's goal is a use case instead.",
            "title",
        ),
        kind(
            CONSTRAINT,
            "A constraint: a limit on the solution, which the design takes as given.",
            "title",
        ),
    )
    for requirement in requirements:
        requirement.add_argument(
            "--actor",
            dest="actors",
            action="append",
            default=[],
            metavar="ACT-ID",
            help="An actor whose need it meets, written in `actors` and anchored (repeatable).",
        )
        requirement.add_argument(
            "--refines",
            action="append",
            default=[],
            metavar="REQ-ID",
            help="A requirement it refines, of any of the three kinds, written in `refines` and "
            "anchored (repeatable).",
        )
        requirement.add_argument(
            "--area", metavar="WORD", help="The functional area's folder to put it in."
        )
        requirement.add_argument(
            "--unanchored-because",
            metavar="TEXT",
            help=(
                "Why nothing embodies it, so it has no anchors (instead of --path, --record, "
                "--actor and --refines): written as `unanchored-because` in its friction block."
            ),
        )
    help_text = (
        "A revalidation record, kept only when there is something to say: a planned "
        "revalidation, one that found a regression or a gap, or one where a person decided "
        "an artefact was stale. A planned record names each source of the design it "
        "reviewed with --reviewed-against."
    )
    _revalidation_arguments(kinds.add_parser(REVALIDATION, help=help_text, description=help_text))
    return parser


def _analysis_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--analysis",
        metavar="COMPONENT",
        default=None,
        help="The analysis to write in, by its component, where the project lists several in "
        "its configuration (DEC-001 point 2): its folder takes what is written. Needed where "
        "it lists more than one.",
    )


def _revalidation_arguments(record: argparse.ArgumentParser) -> None:
    record.add_argument("slug", help="A word naming its subject: the record is <date>-<slug>.md.")
    _analysis_argument(record)
    record.add_argument("--title", metavar="TEXT", help="Its subject (default: the slug).")
    record.add_argument(
        "--change",
        required=True,
        metavar="REF",
        help="The change that carried it: a work item, a pull request, or a range of commits "
        "on the default branch.",
    )
    record.add_argument(
        "--trigger", required=True, choices=schemas.record_triggers(), help="What triggered it."
    )
    record.add_argument(
        "--reviewed-against",
        dest="reviewed_against",
        action="append",
        default=[],
        metavar="TITLE @ VERSION [@ LINK]",
        help="A source of the design a planned revalidation reviewed, once for each, and "
        "only on a planned record: its title, then its version, then its link where it lies "
        "outside this repository. A version in this repository is a commit's full id on the "
        "default branch, or `this change` when the design lands with the record. Outside it, "
        "it is the time the text was read, such as 2026-01-05T10:00:00Z, or a commit's full "
        "id.",
    )
    record.add_argument(
        "--outcome",
        dest="outcomes",
        action="append",
        default=[],
        type=_pair,
        metavar="ID=OUTCOME",
        help=f"An artefact covered and its outcome, one of {', '.join(schemas.record_outcomes())} "
        f"(repeatable, at least one).",
    )
    record.add_argument(
        "--because",
        action="append",
        default=[],
        type=_pair,
        metavar="ID=TEXT",
        help="Why an artefact's outcome is what it is (repeatable; one per --outcome).",
    )
    record.add_argument(
        "--gap",
        dest="gaps",
        action="append",
        default=[],
        metavar="IDS: GAP => RESOLUTION",
        help="A gap found, after the ids of the artefacts it affects, separated by commas, "
        "each one an --outcome gives: behaviour nothing describes, or a description with no "
        "behaviour. Then what resolved it: the defect reported, or the artefact written. "
        "Repeatable. Each regression and each gap found is named among a gap's ids.",
    )
    who = record.add_mutually_exclusive_group()
    who.add_argument(
        "--by", metavar="WHO", help="The person who performed it (default: git's user.name)."
    )
    who.add_argument(
        "--by-agent",
        metavar="NAME",
        help="The agent that performed it; --confirmed-by then names the person who confirmed it.",
    )
    record.add_argument(
        "--confirmed-by",
        metavar="WHO",
        help="The person who confirmed an agent's outcomes, or decided an artefact was stale.",
    )


def _gap(value: str) -> revalidation.Gap:
    """`<ids>: <gap> => <resolution>`: the ids of the artefacts a gap affects, the gap, and
    what resolved it, given as one so none can be matched with another's. What comes
    before the first colon is ids alone, so a gap written without them, whose own text
    holds a colon, is refused for its form, naming what is no id."""
    gap, sep, resolved = value.partition(GAP_SEPARATOR)
    labelled, colon, found = gap.partition(IDS_SEPARATOR)
    ids = tuple(i.strip() for i in labelled.split(","))
    # A gap still holding a placeholder is the placeholder refusal's, which says to fill it.
    named_ids = colon and unfilled(value) is None
    no_id = [i for i in ids if i and not _artefact_id(i)] if named_ids else []
    if not (sep and colon and all(ids) and not no_id and found.strip() and resolved.strip()):
        named = ""
        if no_id:
            are = "is no artefact's id" if len(no_id) == 1 else "are no artefacts' ids"
            named = f" ({', '.join(map(repr, no_id))} {are})"
        raise stamp.Refused(
            f'--gap {value!r} is not "<ids>: <gap> => <resolution>"{named}: the ids of the '
            f"artefacts it affects, separated by commas, then the gap found, then what "
            f"resolved it — the defect reported, or the artefact written (DEC-001 point 6)"
        )
    return revalidation.Gap(ids, found.strip(), resolved.strip())


def _artefact_id(text: str) -> bool:
    """Whether `text` has the shape of an artefact's id, of any kind, a requirement's
    included (DEC-002, Implications)."""
    return any(schemas.id_pattern(kind).match(text) for kind in KINDS)


def _stamp_record(args: argparse.Namespace) -> stamp.Stamped:
    request = revalidation.RecordRequest(
        slug=args.slug,
        change=args.change,
        trigger=args.trigger,
        outcomes=tuple(args.outcomes),
        by=args.by,
        by_agent=args.by_agent,
        confirmed_by=args.confirmed_by,
        title=args.title,
        because=tuple(args.because),
        gaps=tuple(_gap(value) for value in args.gaps),
        reviewed_against=tuple(args.reviewed_against),
        analysis=args.analysis,
    )
    return revalidation.stamp_record(backbone.project_root(), request)


def _stamp_artefact(args: argparse.Namespace) -> stamp.Stamped:
    request = stamp.Request(
        kind=args.kind,
        slug=args.slug,
        title=args.title,
        actor=getattr(args, "actor", None),
        other_actors=tuple(getattr(args, "other_actors", ())),
        steps=tuple(getattr(args, "steps", ())),
        relies_on=tuple(getattr(args, "relies_on", ())),
        area=getattr(args, "area", None),
        paths=tuple(args.paths),
        records=tuple(args.records),
        unanchored_because=getattr(args, "unanchored_because", None),
        actors=tuple(getattr(args, "actors", ())),
        refines=tuple(getattr(args, "refines", ())),
        requirements=tuple(getattr(args, "requirements", ())),
        analysis=args.analysis,
    )
    return stamp.stamp(backbone.project_root(), request, args.base)


def main() -> int:
    args = _parser().parse_args()
    try:
        stamped = _stamp_record(args) if args.kind == REVALIDATION else _stamp_artefact(args)
    except stamp.Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for note in stamped.notes:
        print(note)
    for warning in stamped.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"stamped {stamped.id} at {stamped.location}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
