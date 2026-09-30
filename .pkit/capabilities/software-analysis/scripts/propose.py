#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — propose: what a flagged artefact's evidence decides (DEC-001).

For one artefact the friction checks flag, reads the evidence of its change —
`pkit friction explain`, which names the files each anchor stands on, the
commits behind each finding with the paths behind them, and the artefact's
body; what the artefact quotes from those files at its revalidation point and
at HEAD; and where lost code went (`_lib/reading.py`) — and says what it comes
to (`_lib/resolve.py` states the rules):

- a **proposal** — `holds` (the code moved), `analysis-stale` or
  `code-regressed`, with the rule and the evidence that decided it, for the
  resolving agent to confirm by reading;
- **read** — nothing mechanical decides; the agent reads the change, and the
  evidence may lean to an outcome (`hint`);
- **ambiguous** — the artefact and the code disagree and nothing says whether
  the change was meant: stale or regressed is a person's to decide, and the
  question to ask them;
- **none** — nothing to resolve.

For a verdict that comes to an outcome it gives the answer (`_lib/answers.py`):
what the person does first, and the writer commands that record the outcome,
word for word, with a placeholder where the words are the agent's to draft or
the person's to supply. It runs none of them.

What the agent read goes in as quotes, each with where it was read:
`--contradicted` (the change contradicts what the artefact says),
`--intended` (the change's context says the change was meant), `--unintended`
(it says it was not: a failing result on the artefact, a report of the
defect), each followed by its `--…-from`: a commit, a URL, or a person. A quote
from a commit is checked against that commit's message — `git log --format=%B`,
whitespace runs read as one space — when it is one of the commits behind the
changed anchors; any other source cannot be checked here, and is shown as
unverified. The check is shown, never enforced: the person decides.

It writes nothing: a query — bounded, deterministic for the same repository
state, read-only, needing no network. It reads HEAD, as the explanation does.

Usage:
  pkit analysis propose <artefact>
      [--contradicted <quote> --contradicted-from <source>]
      [--intended <quote> --intended-from <source>]
      [--unintended <quote> --unintended-from <source>] [--json]

Exit codes:
  0  answered, whatever the verdict
  1  the artefact cannot be explained — not committed, not found, or its
     revalidation point is beyond a shallow clone — said on standard error
  2  a usage error, a quote without its source among them
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import answers, backbone, reading, resolve  # noqa: E402
from _lib.model import Unreadable  # noqa: E402

#: The version of the `--json` document.
SCHEMA_VERSION = 1

#: What the agent read, each a quote with its source, as the flags name them.
READINGS = ("contradicted", "intended", "unintended")

#: A source that names a commit: an abbreviated or full object name.
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pkit analysis propose",
        description="Say which revalidation outcome a flagged artefact's evidence decides — or "
        "that stale versus regressed is a person's to decide (software-analysis DEC-001 point "
        "5). Read-only.",
    )
    parser.add_argument("artefact", help="The artefact: its id, or its location.")
    helps = {
        "contradicted": "What in the change contradicts what the artefact says, quoted.",
        "intended": "Where the change's context says the change was meant, quoted.",
        "unintended": "Where it says it was not — a failing result, a report of the defect — "
        "quoted.",
    }
    for name in READINGS:
        parser.add_argument(f"--{name}", metavar="QUOTE", help=helps[name])
        parser.add_argument(
            f"--{name}-from",
            metavar="SOURCE",
            help=f"Where the --{name} quote was read: a commit, a URL, or a person.",
        )
    parser.add_argument("--json", action="store_true", help="Print the verdict document.")
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    for name in READINGS:
        quote, source = getattr(args, name), getattr(args, f"{name}_from")
        if (quote is None) != (source is None):
            parser.error(
                f"--{name} and --{name}-from go together: the quote, and where it was read"
            )
    root = backbone.project_root()
    try:
        evidence = reading.read(root, args.artefact)
    except Unreadable as exc:
        print(f"cannot propose: {exc}", file=sys.stderr)
        return 1
    behind = {c.commit for a in evidence.anchors if a.changed for c in a.commits}
    quotes = {
        name: _quote(root, getattr(args, name), getattr(args, f"{name}_from"), behind)
        for name in READINGS
    }
    intent = resolve.Intent(**quotes)
    verdict = resolve.propose(evidence.artefact, evidence.state, evidence.anchors, intent)
    answer = answers.answer(evidence.location, verdict, evidence.anchors)
    if args.json:
        document = _document(evidence, intent, verdict, answer)
        print(json.dumps(document, indent=2, ensure_ascii=False))
    else:
        print("\n".join(_lines(evidence, intent, verdict, answer)))
    return 0


def _quote(
    root: Path, text: str | None, source: str | None, behind: set[str]
) -> resolve.Quote | None:
    """A quote with its source, checked where the source is a commit behind the change."""
    if text is None or source is None:
        return None
    if not _COMMIT.match(source):
        return resolve.Quote(text, source)
    commit = backbone.commit_of(root, source)
    said = backbone.message(root, commit) if commit in behind and commit else None
    return resolve.Quote(text, source, said is not None and _fold(text) in _fold(said))


def _fold(text: str) -> str:
    return " ".join(text.split())


def _source_kind(quote: resolve.Quote) -> str:
    return "commit" if _COMMIT.match(quote.source) else "other"


def _name(verdict: resolve.Verdict) -> str:
    if isinstance(verdict, resolve.Proposal):
        return verdict.outcome
    if isinstance(verdict, resolve.Ambiguous):
        return "ambiguous"
    if isinstance(verdict, resolve.Read):
        return "read"
    return "none"


def _document(
    evidence: reading.Reading,
    intent: resolve.Intent,
    verdict: resolve.Verdict,
    answer: answers.Answer | None,
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
        "hint": verdict.hint if isinstance(verdict, resolve.Read) else None,
        "question": verdict.question if isinstance(verdict, resolve.Ambiguous) else None,
        "anchors": [
            {
                "kind": a.kind,
                "value": a.value,
                "state": a.state,
                "shape": a.shape,
                "commits": [
                    {"commit": c.commit, "change": c.change, "paths": list(c.paths)}
                    for c in a.commits
                ],
                "quoted": list(a.quoted),
                "gone": list(a.gone),
                "moved_to": list(a.moved_to),
            }
            for a in evidence.anchors
            if a.changed
        ],
        "read": {name: _quote_json(getattr(intent, name)) for name in READINGS},
        "answer": None
        if answer is None
        else {
            "outcome": answer.outcome,
            "first": list(answer.first),
            "commands": list(answer.commands),
        },
    }


def _quote_json(quote: resolve.Quote | None) -> dict[str, Any] | None:
    if quote is None:
        return None
    return {
        "quote": quote.text,
        "source": quote.source,
        "source_kind": _source_kind(quote),
        "verified": quote.verified,
    }


def _lines(
    evidence: reading.Reading,
    intent: resolve.Intent,
    verdict: resolve.Verdict,
    answer: answers.Answer | None,
) -> list[str]:
    lines = [f"{evidence.artefact}  {evidence.location} — {evidence.state}"]
    for anchor in (a for a in evidence.anchors if a.changed):
        lines.append(f"  {anchor.label} ({anchor.state}, {anchor.shape})")
        lines += [f"    {c.commit[:12]} {c.change}{_paths(c.paths)}" for c in anchor.commits]
        if anchor.quoted:
            gone = f"; gone at HEAD: {_quoted(anchor.gone)}" if anchor.gone else ""
            lines.append(f"    quotes {_quoted(anchor.quoted)}{gone}")
        if anchor.moved_to:
            lines.append(f"    moved to {', '.join(anchor.moved_to)}")
    for name in READINGS:
        quote = getattr(intent, name)
        if quote is not None:
            lines.append(f"  {name}: {quote.text!r} — {quote.source}, {_checked(quote)}")
    leans = verdict.hint if isinstance(verdict, resolve.Read) else None
    hint = f", leaning to {leans}" if leans else ""
    lines.append(f"{_name(verdict)} ({verdict.rule}{hint}): {verdict.reason}")
    if isinstance(verdict, resolve.Ambiguous):
        lines.append(f"  ask a person: {verdict.question}")
    if answer is not None:
        lines.append(f"Commands for the person ({answer.outcome}):")
        lines += [f"  first: {step}" for step in answer.first]
        lines += [f"  {command}" for command in answer.commands]
    lines.append("Read-only: nothing was written.")
    return lines


def _checked(quote: resolve.Quote) -> str:
    if quote.verified is None:
        return "unverified"
    return "verified in its message" if quote.verified else "NOT found in its message"


def _quoted(quotes: tuple[str, ...]) -> str:
    return ", ".join(f"`{q}`" for q in quotes)


def _paths(paths: tuple[str, ...]) -> str:
    """The paths behind a commit, as a human line closes with them: `git show <commit>
    -- <paths>` is what changed under the anchor."""
    return f" — {', '.join(paths)}" if paths else ""


if __name__ == "__main__":
    sys.exit(main())
