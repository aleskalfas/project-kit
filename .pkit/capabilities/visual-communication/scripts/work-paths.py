#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""visual-communication capability — work-paths: the paths the graphic-designer's grant
takes by default, the location of the visual work (DEC-030 point 5, COR-073 point 3).

The capability declares the overlay category `visual-communication.work`, which the agent
`graphic-designer` owns, and names this command as its default's query. Installing the
capability, and `pkit agents reconcile --write`, ask it and write its answer into the agents
overlay, where the project set no value of its own.

It answers the location the configuration records. Where none is recorded, it answers
`visual/`, where that folder is absent, holds no file, or holds the capability's work, as a
command that writes there would take it (DEC-002 point 1). A `visual/` that holds files of
another kind, or that cannot be the location, is never granted: it answers no path, and says
why in its note.

It only reads, and needs no network: a query, which `pkit sync` provisions. It takes no
subject.

Usage:
  pkit visual work-paths          each path, one to a line, and why where it answers none
  pkit visual work-paths --json   one document, {"paths": [...]}, with a "note" where it
                                  answers no path

Exit codes:
  0  answered, with a path or with none
  1  no answer: the configuration cannot be read, records a location that is refused, or
     git cannot list the default's files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import location as loc
from _lib.root import CONFIG, project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual work-paths",
        description="Answer the paths the graphic-designer's grant takes by default.",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    args = parser.parse_args()
    try:
        answer = answered(project_root())
    except (loc.LocationRefused, loc.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(answer, ensure_ascii=False))
        return 0
    for path in answer["paths"]:
        print(path)
    if "note" in answer:
        print(f"no path: {answer['note']}")
    return 0


def answered(root: Path) -> dict[str, Any]:
    """The default's answer: the recorded location, else `visual/` where a writing command
    would take it, else no path with the reason. Raises LocationRefused where the
    configuration cannot be read or records a location that is refused, and GitFailed."""
    recorded = loc.configured(root)
    if recorded is not None:
        found = loc.problem(root, recorded)
        if found is not None:
            raise loc.LocationRefused(
                f"{CONFIG} records the location `{recorded}`, which {found}: change the "
                f"`{loc.KEY}:` line to where the work lies"
            )
        return {"paths": [f"{recorded}/"]}
    found = loc.problem(root, loc.DEFAULT)
    if found is not None:
        return {"paths": [], "note": f"the default location `{loc.DEFAULT}` {found}"}
    if (
        not (root / loc.DEFAULT).exists()
        or not loc.files(root, loc.DEFAULT)
        or loc.holds_marker(root, loc.DEFAULT)
    ):
        return {"paths": [f"{loc.DEFAULT}/"]}
    return {
        "paths": [],
        "note": (
            f"`{loc.DEFAULT}/` holds files that are not the visual work, and {CONFIG} records "
            "no location"
        ),
    }


if __name__ == "__main__":
    sys.exit(main())
