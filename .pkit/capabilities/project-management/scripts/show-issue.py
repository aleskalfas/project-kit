#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — show-issue (verb-subject per DEC-020).

Read-only diagnostic for an existing GitHub issue. Surfaces the
methodology-relevant view: title, type (inferred from prefix),
classification labels, assignees, state, parent-ref (first body line),
required-section presence summary, milestone.

Membership gate per DEC-021.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/show-issue.py 42

Or via the dispatcher (per COR-021):
  pkit project-management show-issue 42

Exit codes:
  0  shown
  1  membership refusal
  2  usage error (issue not found; gh failure)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib import provenance  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Show the methodology-relevant view of a GitHub issue: type, "
            "classification, assignees, state, parent-ref, milestone, "
            "and required-section presence summary."
        ),
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number to inspect.",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text.",
    )
    output.add_argument(
        "--field",
        metavar="NAME",
        default=None,
        help=(
            "Print only the value of a single field, with no surrounding "
            "chrome (scalars bare, lists one per line, sections one "
            "present/absent line each). Mutually exclusive with --json. "
            "Valid fields: " + ", ".join(ISSUE_FIELD_NAMES) + "."
        ),
    )
    args = parser.parse_args()

    if args.field is not None and args.field not in ISSUE_FIELD_NAMES:
        print(
            f"error: unknown field '{args.field}'.\n"
            f"valid fields: {', '.join(ISSUE_FIELD_NAMES)}",
            file=sys.stderr,
        )
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            f"error: {CAPABILITY_NAME} capability not found.",
            file=sys.stderr,
        )
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    body_format = _read_yaml(capability_root / "schemas" / "body-format.yaml", yaml_loader)

    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    summary = _summarise(issue, issue_types, body_format)

    if args.field is not None:
        for line in _field_lines_for(summary)[args.field]:
            print(line)
    elif args.json:
        print(json.dumps(summary, indent=2))
    else:
        _print_summary(args.issue_number, summary)
    return 0


def _summarise(issue: dict, issue_types: dict, body_format: dict) -> dict:
    title = str(issue.get("title", ""))
    # Read-side strip (ADR-037): the agent composes edits against
    # footer-free text, so it never sees or mishandles the footer bytes.
    body = provenance.strip_footer(str(issue.get("body") or ""))
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    assignees = [
        a.get("login", "") if isinstance(a, dict) else str(a)
        for a in (issue.get("assignees") or [])
    ]
    state = str(issue.get("state", "")).lower()
    milestone = issue.get("milestone") or {}
    milestone_title = (
        milestone.get("title") if isinstance(milestone, dict) else None
    )

    structural_type = _infer_structural_type(title, issue_types)
    parent_ref = _first_body_line(body)
    required_sections = _required_section_status(structural_type, body, body_format)
    criteria = _extract_criteria(body)

    type_labels = [lbl for lbl in labels if axis_labels.is_axis_label(lbl, "type")]
    priority_labels = [lbl for lbl in labels if axis_labels.is_axis_label(lbl, "priority")]
    workstream_labels = [lbl for lbl in labels if axis_labels.is_axis_label(lbl, "workstream")]
    other_labels = [
        lbl
        for lbl in labels
        if not any(
            axis_labels.is_axis_label(lbl, ax)
            for ax in ("type", "priority", "workstream")
        )
    ]

    return {
        "title": title,
        "structural_type": structural_type,
        "state": state,
        "assignees": assignees,
        "milestone": milestone_title,
        "parent_ref": parent_ref,
        "classification": {
            "type": type_labels,
            "priority": priority_labels,
            "workstream": workstream_labels,
        },
        "other_labels": other_labels,
        "required_sections": required_sections,
        "criteria": criteria,
        "body": body,
        "url": issue.get("url"),
    }


# The addressable field vocabulary for `--field`. Order is the documented
# order (and is asserted to match `_field_lines_for`'s keys in the tests).
ISSUE_FIELD_NAMES = (
    "title",
    "type",
    "state",
    "assignees",
    "milestone",
    "parent",
    "priority",
    "workstream",
    "labels",
    "criteria",
    "sections",
    "body",
    "url",
)


def _scalar(value: object) -> list[str]:
    """Render a scalar field as zero or one output line.

    `None` and the empty string render as no output (a bare command for an
    absent field yields nothing, not a blank line).
    """
    if value is None:
        return []
    text = str(value)
    return [text] if text != "" else []


def _field_lines_for(s: dict) -> dict[str, list[str]]:
    """Project the summary into the addressable `--field` vocabulary.

    Each value is the list of output lines for that field: scalars are zero or
    one line, lists are one item per line, `sections` is one present/absent
    line per required section. Derived from the same summary the `--json` path
    serialises — no second fetch.
    """
    classification = s.get("classification") or {}
    all_labels = (
        list(classification.get("type") or [])
        + list(classification.get("priority") or [])
        + list(classification.get("workstream") or [])
        + list(s.get("other_labels") or [])
    )
    sections = [
        f"{'present' if sec.get('present') else 'absent'} {sec.get('heading')}"
        for sec in (s.get("required_sections") or [])
    ]
    return {
        "title": _scalar(s.get("title")),
        "type": _scalar(s.get("structural_type")),
        "state": _scalar(s.get("state")),
        "assignees": list(s.get("assignees") or []),
        "milestone": _scalar(s.get("milestone")),
        "parent": _scalar(s.get("parent_ref")),
        "priority": list(classification.get("priority") or []),
        "workstream": list(classification.get("workstream") or []),
        "labels": all_labels,
        "criteria": list(s.get("criteria") or []),
        "sections": sections,
        "body": _scalar(s.get("body")),
        "url": _scalar(s.get("url")),
    }


def _print_summary(issue_number: int, s: dict) -> None:
    title = s.get("title") or ""
    print(f"issue #{issue_number}: {title}")
    print(f"  type:         {s.get('structural_type') or '<unrecognised prefix>'}")
    print(f"  state:        {s.get('state') or '<unknown>'}")
    print(f"  assignees:    {', '.join(s.get('assignees') or []) or '<none>'}")
    if s.get("milestone"):
        print(f"  milestone:    {s['milestone']}")
    parent_ref = s.get("parent_ref") or ""
    if parent_ref:
        print(f"  parent ref:   {parent_ref}")
    classification = s.get("classification") or {}
    type_lbls = classification.get("type") or []
    pri_lbls = classification.get("priority") or []
    ws_lbls = classification.get("workstream") or []
    print(f"  type label:   {', '.join(type_lbls) or '<missing>'}")
    print(f"  priority:     {', '.join(pri_lbls) or '<unset / on board>'}")
    print(f"  workstream:   {', '.join(ws_lbls) or '<unset / on board>'}")
    other = s.get("other_labels") or []
    if other:
        print(f"  other labels: {', '.join(other)}")
    sections = s.get("required_sections") or []
    if sections:
        present = sum(1 for sec in sections if sec.get("present"))
        print(f"  body sections: {present}/{len(sections)} required present")
        for sec in sections:
            marker = "✓" if sec.get("present") else "✗"
            print(f"    {marker} {sec.get('heading')}")
    url = s.get("url")
    if url:
        print(f"  url:          {url}")


def _infer_structural_type(title: str, issue_types: dict) -> str | None:
    types = issue_types.get("types") or {}
    for type_name, entry in types.items():
        if not isinstance(entry, dict):
            continue
        prefix = entry.get("title_prefix", "")
        case = entry.get("title_case", "title")
        rendered = str(prefix)
        if case == "upper":
            rendered = rendered.upper()
        if title.startswith(f"[{rendered}] "):
            return str(type_name)
    return None


def _first_body_line(body: str) -> str:
    return body.lstrip().split("\n", 1)[0] if body.strip() else ""


def _extract_criteria(body: str) -> list[str]:
    """Pull the authored items under the '## Acceptance criteria' section.

    Returns each item's text with the leading bullet and any checkbox marker
    stripped. Collection starts at the acceptance-criteria heading and stops
    at the next level-2 heading. A bare skeleton item (`- [ ]` with nothing
    after it) is excluded — it carries no authored content.
    """
    items: list[str] = []
    in_section = False
    for raw in body.splitlines():
        stripped = raw.strip()
        if stripped.startswith("## "):
            in_section = "acceptance criteria" in stripped.lower()
            continue
        if not in_section:
            continue
        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if not bullet:
            continue
        text = bullet.group(1)
        checkbox = re.match(r"^\[[ xX]\]\s*(.*)$", text)
        if checkbox:
            text = checkbox.group(1)
        text = text.strip()
        if text:
            items.append(text)
    return items


def _required_section_status(
    structural_type: str | None, body: str, body_format: dict
) -> list[dict]:
    if not structural_type:
        return []
    bodies = body_format.get("bodies") or {}
    type_body = bodies.get(structural_type) or {}
    sections = type_body.get("required_sections") or []
    out: list[dict] = []
    for s in sections:
        if not isinstance(s, dict):
            continue
        heading = str(s.get("heading", ""))
        if not heading:
            continue
        out.append({"heading": heading, "present": heading in body})
    return out


def _read_yaml(path: Path, yaml_loader: YAML) -> dict:
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    data = _read_yaml(capability_root / "project" / "members.yaml", yaml_loader)
    members = data.get("members") or []
    return members if isinstance(members, list) else []


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(
        issue_number, config,
        fields="title,body,labels,assignees,state,milestone,url",
    )


if __name__ == "__main__":
    sys.exit(main())
