#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — history (read-only, per DEC-049).

Renders an issue's engine journal — the substrate-neutral, canonical audit
trail of pkit-governed lifecycle moves — so the state log is discoverable
without reading the GitHub timeline by hand (the #672 "looked unlogged" gap).

    pkit project-management history <N>
    pkit project-management history <N> --check-drift

`--check-drift` surfaces the **governance boundary** (DEC-049): it diffs the
engine journal (what pkit governed) against the GitHub timeline's `state:*`
label events (what actually happened) and flags state changes with no matching
journal entry — an out-of-band mutation made without pkit's control.

Read-only. Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/history.py 42
Or via the dispatcher:
  pkit project-management history 42

Exit codes:
  0  rendered (and, with --check-drift, no drift)
  2  usage error (gh / engine failure)
  3  drift detected (--check-drift only)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.membership import resolve_capability_root  # noqa: E402

_PROCESS_ADDRESS = "project-management:issue-lifecycle"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render an issue's engine journal (the canonical pkit-governed audit "
            "trail); --check-drift flags ungoverned state changes. Per DEC-049."
        ),
    )
    parser.add_argument("issue_number", type=int)
    parser.add_argument(
        "--check-drift", action="store_true",
        help="Diff the journal against the GitHub timeline's state-label events "
        "and flag state changes pkit did not author (governance boundary).",
    )
    parser.add_argument("--capability-root", type=Path, default=None)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print("error: project-management capability not found.", file=sys.stderr)
        return 2
    config = load_adopter_config(capability_root)

    journal = _read_journal(args.issue_number)
    if journal is None:
        print(
            f"error: could not read the engine journal for #{args.issue_number} "
            "(is the process engine available?).",
            file=sys.stderr,
        )
        return 2

    print(f"history: #{args.issue_number} — engine journal ({len(journal)} entry(ies))")
    if not journal:
        print("  (no journal entries — no pkit-governed moves recorded yet.)")
    for entry in journal:
        print("  " + _render_entry(entry))

    if args.check_drift:
        return _report_drift(args.issue_number, journal, config)
    return 0


def _read_journal(issue_number: int) -> list[dict] | None:
    """Read the subject's journal via `pkit process status … --json` (the read
    seam homed in the binary, ADR-020). None on any failure."""
    try:
        proc = subprocess.run(
            [
                "pkit", "process", "status", _PROCESS_ADDRESS,
                "--subject", str(issue_number), "--json",
            ],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    journal = data.get("journal")
    return journal if isinstance(journal, list) else []


def _render_entry(entry: dict) -> str:
    """One-line render of a journal entry — the useful fields, generically."""
    when = entry.get("ts") or entry.get("at") or entry.get("timestamp") or "?"
    actor = entry.get("actor") or "?"
    to_state = entry.get("to") or entry.get("state") or "?"
    frm = entry.get("from")
    move = f"{frm} → {to_state}" if frm else str(to_state)
    trigger = entry.get("trigger")
    trigger_str = f" ({trigger})" if trigger else ""
    # `version` is added by the reliable-journal slice (#697); render when present.
    version = entry.get("version") or entry.get("pkit_version")
    tail = f"  [pkit {version}]" if version else ""
    reason = entry.get("reason") or (entry.get("detail") or {}).get("reason")
    reason_str = f" — {reason}" if reason else ""
    return f"{when}  {actor}  {move}{trigger_str}{reason_str}{tail}"


def _report_drift(issue_number: int, journal: list[dict], config: dict) -> int:
    """Governance boundary (DEC-049): flag GitHub `state:*` label changes that have
    no matching journal entry — state moved without pkit's control."""
    timeline_states = _timeline_state_adds(issue_number, config)
    if timeline_states is None:
        print(
            "  [drift] could not read the GitHub timeline; drift not checked.",
            file=sys.stderr,
        )
        return 2

    governed = len([e for e in journal if (e.get("to") or e.get("state"))])
    observed = len(timeline_states)
    print(f"\ndrift check: {governed} governed move(s) journaled · "
          f"{observed} `state:*` change(s) on the GitHub timeline")

    if observed <= governed:
        print("  ✓ no ungoverned state changes detected.")
        return 0

    unmatched = observed - governed
    print(f"  ⚠ {unmatched} `state:*` change(s) on the timeline have no journal "
          "entry — either an **ungoverned** change (a manual label edit / raw `gh`),")
    print("    or a governed move the journal didn't record (until the journal is "
          "fully reliable — #697). The state-label events on the timeline:")
    for ev in timeline_states:
        print(f"      {ev.get('created_at', '?')}  {ev.get('actor', '?')}  "
              f"+{ev.get('label', '?')}")
    return 3


def _timeline_state_adds(issue_number: int, config: dict) -> list[dict] | None:
    """GitHub timeline `labeled` events for `state:*` labels — the observed state
    changes. None on gh failure. Each item: {created_at, actor, label}."""
    proc = gh_run(
        [
            "gh", "api", "--paginate",
            f"repos/{{owner}}/{{repo}}/issues/{issue_number}/timeline",
        ],
        config, check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        events = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    out: list[dict] = []
    for ev in events if isinstance(events, list) else []:
        if not isinstance(ev, dict) or ev.get("event") != "labeled":
            continue
        label = (ev.get("label") or {}).get("name", "")
        if not label.startswith("state:"):
            continue
        out.append({
            "created_at": ev.get("created_at", "?"),
            "actor": (ev.get("actor") or {}).get("login", "?"),
            "label": label,
        })
    return out


if __name__ == "__main__":
    sys.exit(main())
