#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — new: stamp an artefact or a revalidation record (DEC-001).

Writes one artefact from its kind's template under the analysis location — the
`analysis` sub-path of the internal documentation root, recorded the first
time an artefact is placed there (COR-049 point 5):

- a use case, `use-case-model/use-cases/[<area>/]UC-NNN-<slug>.md`, with its
  actor and the actor anchor;
- a journey, `use-case-model/journeys/JRN-NNN-<slug>.md`, with its steps and,
  from them, its use-case anchors;
- an actor, the entry `ACT-<slug>` of `use-case-model/actors.md`;
- a term, the entry `TERM-<slug>` of `glossary.md`.

A use case or journey takes the next free number on the default branch — every
number its history ever gave a file included, but an id the project's
numbering setting frees (`_lib/numbering.py`) — on a base named with `--base`,
and in the working tree; `$PKIT_CHECK_BASE`, a pipeline's base for its checks,
never moves where it numbers from (COR-054 point 3). `pkit analysis
check-numbers` reports a number another branch took first. `_lib/stamp.py`
states the rules.

It also writes a revalidation record, `revalidations/<date>-<slug>.md`, and only
one with something to say — a planned revalidation, one that found a
regression or a gap (point 6), or one where a person decided an artefact was
stale (point 5); `_lib/revalidation.py` states the rules.

Usage:
  pkit analysis new use-case <slug> --actor <ACT-id> [--area <area>] [--title <text>]
  pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id>... [--title <text>]
  pkit analysis new actor <slug> [--name <text>] [--unanchored-because <text>]
  pkit analysis new term <slug> [--name <text>] [--unanchored-because <text>]
  each also: [--path <glob>]... [--record <id>]... [--base <ref>]

  pkit analysis new revalidation <slug> --change <ref> --trigger <trigger>
      --outcome <id>=<outcome>... --because <id>=<text>...
      [--gap "<gap> => <resolution>"]... [--by <who> | --by-agent <name>]
      [--confirmed-by <who>] [--title <text>]

Exit codes:
  0  stamped
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
from _lib.model import ACTOR, JOURNEY, TERM, USE_CASE

#: The kind a revalidation record is stamped as.
REVALIDATION = "revalidation"

#: What parts a gap from what resolved it, in `--gap "<gap> => <resolution>"`.
GAP_SEPARATOR = " => "


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
        "location (software-analysis DEC-001).",
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
        return sub

    use_case = kind(USE_CASE, "A use case: one actor's goal and how it is fulfilled.", "title")
    use_case.add_argument("--actor", required=True, metavar="ACT-ID", help="Whose goal it is.")
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
    help_text = (
        "A revalidation record, kept only when there is something to say: a planned "
        "revalidation, one that found a regression or a gap, or one where a person decided "
        "an artefact was stale."
    )
    _revalidation_arguments(kinds.add_parser(REVALIDATION, help=help_text, description=help_text))
    return parser


def _revalidation_arguments(record: argparse.ArgumentParser) -> None:
    record.add_argument("slug", help="A word naming its subject: the record is <date>-<slug>.md.")
    record.add_argument("--title", metavar="TEXT", help="Its subject (default: the slug).")
    record.add_argument(
        "--change",
        required=True,
        metavar="REF",
        help="The change that carried it: a work item, a pull request or a range of commits.",
    )
    record.add_argument(
        "--trigger", required=True, choices=schemas.record_triggers(), help="What triggered it."
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
        metavar="GAP => RESOLUTION",
        help="A gap found — behaviour nothing describes, or a description with no behaviour — "
        "and what resolved it — the defect reported, the artefact written (repeatable).",
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


def _gap(value: str) -> tuple[str, str]:
    """`<gap> => <resolution>`: a gap and what resolved it, given as one pair so
    neither can be matched with another's."""
    gap, sep, resolved = value.partition(GAP_SEPARATOR)
    if not sep or not gap.strip() or not resolved.strip():
        raise stamp.Refused(
            f'--gap {value!r} is not "<gap> => <resolution>": the gap found, then what '
            f"resolved it — the defect reported, or the artefact written"
        )
    return gap.strip(), resolved.strip()


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
    )
    return revalidation.stamp_record(backbone.project_root(), request)


def _stamp_artefact(args: argparse.Namespace) -> stamp.Stamped:
    request = stamp.Request(
        kind=args.kind,
        slug=args.slug,
        title=args.title,
        actor=getattr(args, "actor", None),
        steps=tuple(getattr(args, "steps", ())),
        area=getattr(args, "area", None),
        paths=tuple(args.paths),
        records=tuple(args.records),
        unanchored_because=getattr(args, "unanchored_because", None),
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
    print(f"stamped {stamped.id} at {stamped.location}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
