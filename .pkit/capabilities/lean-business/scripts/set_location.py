#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — set-location: record the folder that holds the project's ideas
(lean-business DEC-002 point 1).

Run before the first idea, where the default, `lean-business/` at the repository's top, is
not where the ideas should live. Running it is the consent (COR-048 point 5): it records
`location: <path>` in the capability's configuration, every other line of the file kept.
The path is relative to the repository's top, and the rules the check reads a location by
refuse it where it is the top itself, lies outside the repository, under `.pkit/` or a
hidden folder, is reached through a link, or is a file.

Moving the ideas is the person's own act: where the location in use already holds an
idea, move its folder first, then run the command. Naming the location in use, the default
while none is recorded, records it as it stands.

Usage:
  pkit lean set-location <path>

Exit codes:
  0  recorded, or already recorded
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

from _lib import acting, layout, listing, writes
from _lib import location as locations
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean set-location",
        description="Record the folder that holds the project's ideas, relative to the "
        "repository's top. Running it is the consent.",
    )
    made.add_argument("path", help="The folder, such as `ideas` or `docs/ideas`.")
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    path = str(args.path).rstrip("/") if str(args.path) not in ("", "/") else str(args.path)
    found = locations.problem(ctx.root, path)
    if found is not None:
        raise Refused(f"`{path}` cannot hold the ideas: it {found}")
    try:
        recorded = locations.configured(ctx.root)
    except locations.LocationRefused as exc:
        raise Refused(str(exc)) from exc
    if recorded == path:
        ctx.say(f"`{path}/` is recorded already as where the ideas live; nothing changed.")
        return
    in_use = recorded if recorded is not None else locations.DEFAULT
    held = _ideas_in(ctx, in_use) if path != in_use else []
    if held:
        raise Refused(
            f"the ideas live in `{in_use}/`, which holds {', '.join(f'`{i}`' for i in held)}: "
            f"move the folder to `{path}/` first, then record it"
        )
    files = writes.Files(ctx.root, writes.Target(path, record=True))
    acting.content(ctx, files, f"The ideas live in `{path}/` from now on.")


def _ideas_in(ctx: Context, folder: str) -> list[str]:
    if locations.problem(ctx.root, folder) is not None or not (ctx.root / folder).is_dir():
        return []
    try:
        return sorted(layout.read(ctx.root, folder).ideas)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"`{folder}/` cannot be read: {exc}") from exc


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
