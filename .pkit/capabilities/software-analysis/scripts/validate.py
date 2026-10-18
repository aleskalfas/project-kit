#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — validate: the analysis artefacts (DEC-001).

Checks each artefact's shape and own fields against its companion schema, a
use case's or journey's heading against its id and title, an actor's against
its id and name and a requirement's against its id, its kind and its title
(DEC-002 point 2), an actor's file named after its id and a requirement's
carrying its number, ids two artefacts share, an actor, other actor, step or
use case relied on that the stamp would refuse, a use case's other actors
naming its own actor and a journey's `relies-on` naming a step, a use case not
anchored to each actor it involves or a journey not anchored to its actor, a
journey whose use-case anchors do not match its steps and its `relies-on`, a
requirement's `actors` and `refines` against the analysis and its anchors
within it (DEC-002 points 6 and 7), and the revalidation
records' front matter, the artefacts they cite and the evidence
they copy. Where it reads the evidence point, it warns on an entry whose `id`
is not its own `<artefact>@<commit>#<check>`, and on a capability's entry whose
check opens with another name than the capability's. It reports an open
regression — a record's `code-regressed` artefact not revalidated since — and
never fails on it. `unanchored-because`
beside anchors is the core's finding, in the friction block the key belongs
to (COR-050 point 12). `_lib/check.py` states every check and the record point
it applies.

Each body is checked against its kind's declared structure too — a part
missing, out of order or empty, `None.` where a part may not read it, and a
part or a front-matter field that breaks the form its structure gives it
(`_lib/forms.py`). A revalidation record's always: it is a held document,
which no rule binds on, so the capability holds it itself (DEC-001 point 1).
An artefact's, and a glossary's head, only where the format rule,
RS-SAN-001, binds, as `pkit rule-sets reach` reads it, and at its status:
accepted, as errors; under any other status, not at all. `SAN` binds only
through a set of the project's own that inherits it, so the summary counts the
artefacts no rule of `SAN` binds on, and where it binds on none of the
analysis, the check reports it while no rule of `SAN` is accepted and warns
once one is. `--preview` previews a proposed rule as if it were accepted,
where `pkit rule-sets reach --preview` says it would bind: each departure is
a report whose message opens `preview:`, so the exit is the normal check's.
The backbone runs the normal check, with no preview. The structure is the
kind's as the project's own `project/structures.yaml` relabels it, tightened by
each group of the project's whose rule binds on the body, as `pkit rule-sets
reach` reads where a rule binds (`_lib/project_structure.py`). A preview reads
`pkit rule-sets reach --preview` too, so a group whose rule, or a rule it
fills, is proposed is previewed where the rule would bind.

The backbone runs it as this capability's validator, the
`software-analysis:artefacts` member of `pkit validate` (ADR-058): from the
project root, with `--json` alone and the offline marker set, reading one
findings document from standard output. It is a query — bounded,
deterministic, read-only, needing no network — and `pkit init` and `pkit sync`
provision its dependencies in uv's cache. It reads the analysis in the working
tree, through the backbone's discovery, `pkit friction artefacts`, and — when a
record copies evidence — the evidence point, through `pkit connections
resolve`, so the same tree gets the same answer as long as the evidence
fillers read the tree alone; a number another branch took first, and a use
case's step or variant renumbered or removed, read a base, and are `pkit
analysis check-numbers`' to report.

Usage:
  pkit analysis validate             the summary and the findings
  pkit analysis validate --json      the findings document {summary, findings}
  pkit analysis validate --preview   a proposed rule's findings too, as reports

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
from _lib import backbone, check


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis validate",
        description=(
            "Check the analysis artefacts (software-analysis DEC-001): shape and required "
            "parts, headings, duplicate ids, what an artefact names, actor and journey "
            "anchors, revalidation records and the evidence they copy, each record's body "
            "against its structure, and each artefact's body against its kind's structure "
            "where the format rule, RS-SAN-001, is accepted and binds. Read-only and offline; "
            "the working tree, and the evidence point when a record copies evidence."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the findings document {summary, findings}, as `pkit validate` reads it.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help=(
            "Preview each proposed rule as if it were accepted, the format rule, RS-SAN-001, "
            "and a project rule that tightens a kind's structure, where `pkit rule-sets reach "
            "--preview` says it would bind: what each body would break of its kind's "
            "structure, as reports opening `preview:`, which never change the exit status."
        ),
    )
    args = parser.parse_args()

    outcome = check.check(backbone.project_root(), preview=args.preview)
    if args.json:
        print(json.dumps(outcome.document(), indent=2, ensure_ascii=False))
        return 0
    print("\n".join(outcome.lines()))
    return 1 if outcome.errors else 0


if __name__ == "__main__":
    sys.exit(main())
