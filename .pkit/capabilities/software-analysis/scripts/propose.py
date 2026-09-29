#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — propose: what a flagged artefact's evidence decides (DEC-001).

For one artefact the friction checks flag, reads the evidence of its change —
`pkit friction explain`, and what the artefact quotes from its anchored code at
its revalidation point and at HEAD (`_lib/reading.py`) — and says which of the
four outcomes it decides (`_lib/resolve.py` states the rules):

- a **proposal** — `holds`, `analysis-stale` or `code-regressed`, with the rule
  and the evidence that decided it, for the resolving agent to confirm;
- **read** — nothing mechanical decides; the agent reads the change;
- **ambiguous** — the artefact and the code disagree and nothing says whether
  the change was meant: stale or regressed is a person's to decide, and the
  question to ask them;
- **none** — nothing to resolve.

What the agent read goes in as quotes of where it read it: `--contradicted`
(the change contradicts what the artefact says), `--intended` (the change's
context says the change was meant), `--unintended` (it says it was not: a
failing result on the artefact, a report of the defect).

It writes nothing: a query — bounded, deterministic for the same repository
state, read-only, needing no network. It reads HEAD, as the explanation does.

Usage:
  pkit analysis propose <artefact> [--contradicted <quote>] [--intended <quote>]
      [--unintended <quote>] [--json]

Exit codes:
  0  answered, whatever the verdict
  1  the artefact cannot be explained — not committed, not found, or its
     revalidation point is beyond a shallow clone — said on standard error
  2  a usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, reading, resolve  # noqa: E402
from _lib.model import Unreadable  # noqa: E402

#: The version of the `--json` document.
SCHEMA_VERSION = 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pkit analysis propose",
        description="Say which revalidation outcome a flagged artefact's evidence decides — or "
        "that stale versus regressed is a person's to decide (software-analysis DEC-001 point "
        "5). Read-only.",
    )
    parser.add_argument("artefact", help="The artefact: its id, or its location.")
    parser.add_argument(
        "--contradicted",
        metavar="QUOTE",
        help="Your reading: what in the change contradicts what the artefact says.",
    )
    parser.add_argument(
        "--intended",
        metavar="QUOTE",
        help="Where the change's context says the change was meant: a commit, a pull request, "
        "a work item — quoted.",
    )
    parser.add_argument(
        "--unintended",
        metavar="QUOTE",
        help="Where it says it was not: a failing result on the artefact, a report of the "
        "defect — quoted.",
    )
    parser.add_argument("--json", action="store_true", help="Print the verdict document.")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        evidence = reading.read(backbone.project_root(), args.artefact)
    except Unreadable as exc:
        print(f"cannot propose: {exc}", file=sys.stderr)
        return 1
    intent = resolve.Intent(
        contradicted=args.contradicted, intended=args.intended, unintended=args.unintended
    )
    verdict = resolve.propose(evidence.artefact, evidence.state, evidence.anchors, intent)
    if args.json:
        print(json.dumps(_document(evidence, intent, verdict), indent=2, ensure_ascii=False))
    else:
        print("\n".join(_lines(evidence, verdict)))
    return 0


def _name(verdict: resolve.Verdict) -> str:
    if isinstance(verdict, resolve.Proposal):
        return verdict.outcome
    if isinstance(verdict, resolve.Ambiguous):
        return "ambiguous"
    if isinstance(verdict, resolve.Read):
        return "read"
    return "none"


def _document(
    evidence: reading.Reading, intent: resolve.Intent, verdict: resolve.Verdict
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artefact": evidence.artefact,
        "location": evidence.location,
        "state": evidence.state,
        "head": evidence.head,
        "revalidation_point": evidence.point,
        "verdict": _name(verdict),
        "rule": verdict.rule,
        "reason": verdict.reason,
        "question": verdict.question if isinstance(verdict, resolve.Ambiguous) else None,
        "anchors": [
            {
                "kind": a.kind,
                "value": a.value,
                "state": a.state,
                "shape": a.shape,
                "commits": [{"commit": c.commit, "change": c.change} for c in a.commits],
                "quoted": list(a.quoted),
                "gone": list(a.gone),
            }
            for a in evidence.anchors
            if a.changed
        ],
        "read": {
            "contradicted": intent.contradicted,
            "intended": intent.intended,
            "unintended": intent.unintended,
        },
    }


def _lines(evidence: reading.Reading, verdict: resolve.Verdict) -> list[str]:
    lines = [f"{evidence.artefact}  {evidence.location} — {evidence.state}"]
    for anchor in (a for a in evidence.anchors if a.changed):
        lines.append(f"  {anchor.label} ({anchor.state}, {anchor.shape})")
        lines += [f"    {c.commit[:12]} {c.change}" for c in anchor.commits]
        if anchor.quoted:
            gone = f"; gone at HEAD: {_quoted(anchor.gone)}" if anchor.gone else ""
            lines.append(f"    quotes {_quoted(anchor.quoted)}{gone}")
    lines.append(f"{_name(verdict)} ({verdict.rule}): {verdict.reason}")
    if isinstance(verdict, resolve.Ambiguous):
        lines.append(f"  ask a person: {verdict.question}")
    lines.append("Read-only: nothing was written.")
    return lines


def _quoted(quotes: tuple[str, ...]) -> str:
    return ", ".join(f"`{q}`" for q in quotes)


if __name__ == "__main__":
    sys.exit(main())
