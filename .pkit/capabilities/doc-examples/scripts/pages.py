#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""doc-examples capability — pages: the pages the run reads, and its configuration
([doc-examples:DEC-001-console-examples-as-tests] points 3 and 11).

The pages are the documents of the types the project names in
`.pkit/capabilities/doc-examples/project/config.yaml`, or of living-docs' page type
when it names none, read from the backbone's one answer (`pkit friction artefacts
--json`). The run, `scripts/run-examples.py`, reads them through this command, with
the configuration it needs: the setup step, the folders before `PATH`, the variables
and the project's placeholders.

A query: read-only, offline, bounded. It runs nothing of the project's.

Usage:
  pkit doc-examples pages          the types and the pages, one per line
  pkit doc-examples pages --json   the pages document the run reads

Exit codes:
  0  answered
  1  the configuration or the selection cannot be read; each problem names its fix
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import selection


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "List the pages whose console examples the run reads (doc-examples DEC-001 "
            "point 3), with the run's configuration. Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the pages document the run reads."
    )
    args = parser.parse_args()

    root = selection.project_root()
    config, problems = selection.read_config(root)
    pages = selection.Pages()
    if not selection.errors(problems):
        try:
            pages = selection.select(config, selection.read_artefacts(root))
        except selection.Unreadable as exc:
            problems.append(selection.Problem(selection.ERROR, "pkit friction artefacts", str(exc)))
        problems.extend(pages.problems)
    failed = selection.errors(problems)
    if failed:
        for problem in failed:
            print(f"error: {problem.location}: {problem.message}", file=sys.stderr)
        print("`pkit doc-examples validate` reports the same problems.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(selection.document(root, config, pages), indent=2, ensure_ascii=False))
        return 0
    print(f"{len(pages.paths)} page(s), the documents of {', '.join(pages.types)}:")
    for path in pages.paths:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
