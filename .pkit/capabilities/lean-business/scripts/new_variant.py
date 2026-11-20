#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — new-variant: start a variant of an idea, its canvas and its
empty list of assumptions (lean-business DEC-002 points 4 and 7).

Content, so it asks nothing and records no who or when. It creates the idea's folder where
none is, since a first sketch may come before the goal. The variant's authors default to
git's `user.name`. A variant that takes up the story of a shelved one, or comes from a
split, names it with `--comes-from`.

The variant's id is the one given, `<idea>--<variant>`. It is refused where the variant
exists, or where a reference still names it, since an id named is never given again.

Usage:
  pkit lean new-variant <idea>--<variant> --archetype direct|multisided|marketplace
                        [--author <name>]... [--comes-from <variant>]

Exit codes:
  0  written
  1  refused: nothing was written
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, editing, ids, layout, naming, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean new-variant",
        description="Start a variant of an idea: its canvas and its empty list of assumptions.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("--archetype", required=True, choices=canvases.ARCHETYPES)
    made.add_argument(
        "--author",
        action="append",
        dest="authors",
        help="Who writes it; repeat it for each. Git's user.name where none is given.",
    )
    made.add_argument(
        "--comes-from",
        help="The variant it comes from: one it was split from, or a shelved one whose story "
        "it takes up.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    variant = canvases.variant_id(str(args.variant))
    idea = ids.idea_of(variant)
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas_rel = files.path("canvas", variant)
    assumptions_rel = files.path("assumptions", variant)
    if files.exists(canvas_rel):
        raise Refused(f"the variant `{variant}` exists already, at `{canvas_rel}`")
    naming.given(
        idea,
        typed=ids.own(variant),
        text="",
        fallback="variant",
        taken=naming.in_use(files, idea),
    )
    authors = [a.strip() for a in args.authors or [] if a.strip()] or [ctx.who]
    body = editing.mapping(
        [
            ("id", variant),
            ("archetype", args.archetype),
            ("authors", editing.seq(authors)),
            ("comes-from", _comes_from(idea, args.comes_from)),
        ]
    )
    files.put(canvas_rel, editing.new(layout.SCHEMA["canvas"], body))
    if not files.exists(assumptions_rel):
        files.put(
            assumptions_rel,
            editing.new(layout.SCHEMA["assumptions"], {"assumptions": editing.seq()}),
        )
    acting.content(ctx, files, f"Created the variant `{variant}`: `{canvas_rel}`.")


def _comes_from(idea: str, given: str | None) -> str | None:
    if given is None:
        return None
    named = given if ids.is_idea_qualified(given) else ids.qualify(idea, given)
    if not ids.is_idea_qualified(named) or ids.idea_of(named) != idea:
        raise Refused(f"`{given}` names no variant of `{idea}`")
    return ids.ref(ids.CANVAS, named)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
