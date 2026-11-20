#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — remove-side: take a side out of a multisided or marketplace
variant (lean-business DEC-002 point 6).

Content, so it asks nothing and records no who or when. Refused while anything still names
the side, since it would then name a side the canvas does not name: an entry of the canvas,
the estimate's inputs given for it, or an assumption that comes from such an input. Each is
changed or removed first.

A side is part of the model every verdict and each shortlisting cover, so the removal is
warned of, never refused, naming each judgement it leaves stale.

Usage:
  pkit lean remove-side <variant> <name>

Exit codes:
  0  written
  1  refused: nothing was written
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, readings, writes
from _lib.acting import Context
from _lib.fingerprint import BOXES
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean remove-side",
        description="Take a side out of a multisided or marketplace variant.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("name", help="The side's name, such as `cooks`.")
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, str(args.variant))
    name = str(args.name)
    if name not in canvas.sides():
        named = ", ".join(f"`{s}`" for s in canvas.sides()) or "none"
        raise Refused(f"`{canvas.id}` names no side `{name}` (it names {named})")
    still = [*_naming_in_canvas(canvas.plain(), name), *_assumptions_naming(files, canvas, name)]
    if still:
        raise Refused(
            f"the side `{name}` is still named by {_listed(still)}: change or remove each "
            f"first, with `edit-entry --side` or `--clear side`, `set-inputs --side {name} "
            f"--clear <input>`, or `edit-assumption --side`"
        )
    held = canvas.data["sides"]
    held.remove(name)
    if not held:
        del canvas.data["sides"]
    files.put(canvas.rel, canvas.doc)
    acting.content(ctx, files, f"`{canvas.id}` no longer serves the side `{name}`.")


def _listed(named: list[str]) -> str:
    return named[0] if len(named) == 1 else f"{', '.join(named[:-1])} and {named[-1]}"


def _naming_in_canvas(canvas: Mapping[str, object], side: str) -> list[str]:
    """Each entry of the canvas, and each set of its inputs, given for `side`."""
    found = [
        f"the entry `{entry.get('id')}`"
        for box in BOXES
        for entry in readings.entries(canvas, box)
        if entry.get("side") == side
    ]
    held = canvas.get("viability")
    for inputs in held if isinstance(held, list) else []:
        if isinstance(inputs, Mapping) and inputs.get("side") == side:
            found.append("the estimate's inputs for it")
    return found


def _assumptions_naming(files: writes.Files, canvas: canvases.Canvas, side: str) -> list[str]:
    """Each assumption of the variant that comes from an input given for `side`."""
    doc = files.read(files.path("assumptions", canvas.id))
    listed = doc.plain().get("assumptions") if doc is not None else None
    found: list[str] = []
    for assumption in listed if isinstance(listed, list) else []:
        source = assumption.get("source") if isinstance(assumption, Mapping) else None
        if isinstance(source, Mapping) and source.get("side") == side:
            found.append(f"the assumption `{assumption.get('id')}`")
    return found


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
