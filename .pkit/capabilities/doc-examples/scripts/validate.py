#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""doc-examples capability — validate: the run's configuration and the form of each
console fence ([doc-examples:DEC-001-console-examples-as-tests] point 11).

What would stop the run, or fail a fence before its first command, is an error:

- a selection the run cannot read: no types named and no living-docs page type, or a
  type no installed component declares and no project place gives
- a project's placeholder whose name is not in upper case
- two placeholders of the project's form with one name, a variable that takes the
  caller's value among them
- a fence that cannot be read: a line before its first command, or no command

A fence under another name for a shell session, such as `shell-session`, is a
warning, which fails nothing. A configuration of another shape is an error too.

The backbone runs it as this capability's validator, the `doc-examples:examples`
member of `pkit validate` (COR-055 point 3): from the project root, with `--json`
alone and the offline marker set, reading one findings document from standard
output. A query: read-only, offline, bounded. It runs nothing of the project's.

Usage:
  pkit doc-examples validate          the summary and the findings
  pkit doc-examples validate --json   the findings document {summary, findings}

Exit codes:
  0  answered; without --json, also: no error found
  1  without --json: an error found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import selection


def check(root: Path) -> tuple[list[str], list[selection.Problem]]:
    """The summary lines and the findings for the project at `root`."""
    config, problems = selection.read_config(root)
    if not config.read:
        return ["The configuration cannot be read, so no page is checked."], problems
    try:
        pages = selection.select(config, selection.read_artefacts(root))
    except selection.Unreadable as exc:
        problems.append(selection.Problem(selection.ERROR, "pkit friction artefacts", str(exc)))
        return ["The selection cannot be read, so no page is checked."], problems
    problems.extend(pages.problems)
    if pages.problems:
        return ["The selection cannot be read, so no page is checked."], problems
    runner = selection.runner_module()
    fences = 0
    for path in pages.paths:
        try:
            text = runner.read_page(root / path)
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(selection.Problem(selection.ERROR, path, f"cannot be read: {exc}"))
            continue
        for fence in runner.console_fences(text.split("\n"), path):
            where = f"{path}:{fence.line}"
            if fence.language != runner.LANGUAGE:
                problems.append(
                    selection.Problem(
                        selection.WARNING,
                        where,
                        f"a `{fence.language}` fence is a shell session no run checks: name "
                        f"it `{runner.LANGUAGE}` to run it, or give it its shell's language",
                    )
                )
                continue
            fences += 1
            if fence.problem is not None:
                problems.append(selection.Problem(selection.ERROR, where, fence.problem))
    summary = [
        f"{fences} console fence(s) in {len(pages.paths)} page(s), the documents of "
        f"{', '.join(pages.types)}."
    ]
    return summary, problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the run's configuration and the form of each console fence "
            "(doc-examples DEC-001 point 11). Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the findings document {summary, findings}, as `pkit validate` reads it.",
    )
    args = parser.parse_args()

    summary, problems = check(selection.project_root())
    if args.json:
        document = {"summary": summary, "findings": [p.as_json() for p in problems]}
        print(json.dumps(document, indent=2, ensure_ascii=False))
        return 0
    for line in summary:
        print(line)
    for problem in problems:
        print(f"  {problem.severity:<8}{problem.location}")
        print(f"    → {problem.message}")
    return 1 if selection.errors(problems) else 0


if __name__ == "__main__":
    sys.exit(main())
