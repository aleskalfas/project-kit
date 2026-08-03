#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — validate-pr (verb-subject per DEC-020).

Validates an existing GitHub PR against the methodology's PR-side rules. The
rules themselves live in the shared `_lib/pr_validation` module (so `open-pr`
and `review-work` validate at the ready transition through the *same* validator,
not just here at the standalone command). This script is the CLI wrapper: fetch
the PR, gather the closing issue's type labels, run the validator, print/emit.

Findings tagged by severity per validation-severity.yaml.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/validate-pr.py 99

Or via the dispatcher (per COR-021):
  pkit project-management validate-pr 99

Exit codes:
  0  every check passed or only warning-level findings
  1  one or more hard-reject / bypassable findings
  2  usage error (PR not found)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.placeholder_detection import PHASE_CREATE, PHASE_TRANSITION  # noqa: E402
from _lib.pr_validation import (  # noqa: E402
    SEVERITY_BYPASSABLE,
    SEVERITY_HARD_REJECT,
    SEVERITY_WARNING,
    Finding,
    _expected_conv_types,  # noqa: F401  (re-exported for tests)
)
from _lib.pr_validation import extract_closing_issues as _extract_closing_issues  # noqa: E402
from _lib.pr_validation import validate_pr as _validate_pr  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a GitHub PR against the methodology's title + body "
            "rules. Findings by severity; exit code is the contract."
        ),
    )
    parser.add_argument("pr_number", type=int, help="GitHub PR number.")
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    parser.add_argument(
        "--phase",
        choices=(PHASE_CREATE, PHASE_TRANSITION),
        default=PHASE_CREATE,
        help=(
            "Validation phase. 'create' (default) — PR body was just opened; "
            "empty-checkbox-section in ## Test plan is a warning. "
            "'transition' — merge gate; empty-checkbox-section is a hard-reject "
            "per DEC-031."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    titles = _read_yaml(capability_root / "schemas" / "titles.yaml", yaml_loader)
    classification = _read_yaml(
        capability_root / "schemas" / "classification.yaml", yaml_loader
    )
    git_conv = _read_yaml(
        capability_root / "schemas" / "git-conventions.yaml", yaml_loader
    )

    pr = _gh_get_pr(args.pr_number, config)
    if pr is None:
        return 2

    pr_title = str(pr.get("title", ""))
    pr_body = str(pr.get("body") or "")

    closing_issues = _extract_closing_issues(pr_body)
    closing_type_labels = _gather_closing_type_labels(closing_issues, config)

    findings = _validate_pr(
        pr_title=pr_title,
        pr_body=pr_body,
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=closing_type_labels,
        capability_root=capability_root,
        phase=args.phase,
    )

    if args.json:
        out = {
            "pr_number": args.pr_number,
            "pr_title": pr_title,
            "findings": [
                {"severity": f.severity, "label": f.label, "detail": f.detail}
                for f in findings
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        _print_findings(args.pr_number, pr_title, findings)

    blocking = any(
        f.severity in (SEVERITY_HARD_REJECT, SEVERITY_BYPASSABLE) for f in findings
    )
    return 1 if blocking else 0


def _gather_closing_type_labels(closing_issues: list[int], config: dict) -> list[str]:
    out: list[str] = []
    for n in closing_issues:
        issue = _gh_get_issue(n, config)
        if issue is None:
            continue
        for lbl in issue.get("labels") or []:
            name = lbl.get("name") if isinstance(lbl, dict) else str(lbl)
            if isinstance(name, str) and axis_labels.is_axis_label(name, "type"):
                out.append(name)
    return out


def _print_findings(pr_number: int, pr_title: str, findings: list[Finding]) -> None:
    print(f"validating PR #{pr_number}: {pr_title}")
    print()
    if not findings:
        print("[ok] no findings.")
        return
    by_severity: dict[str, list[Finding]] = {}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)
    for sev in (SEVERITY_HARD_REJECT, SEVERITY_BYPASSABLE, SEVERITY_WARNING):
        group = by_severity.get(sev, [])
        if not group:
            continue
        print(f"[{sev}]")
        for f in group:
            print(f"  - {f.label}: {f.detail}")
        print()
    n_block = len(by_severity.get(SEVERITY_HARD_REJECT, [])) + len(
        by_severity.get(SEVERITY_BYPASSABLE, [])
    )
    n_warn = len(by_severity.get(SEVERITY_WARNING, []))
    print(f"summary: {n_block} blocking, {n_warn} warning(s).")


# ---- gh wrappers ----------------------------------------------------


def _gh_get_pr(pr_number: int, config: dict) -> dict | None:
    try:
        proc = gh_run(
            ["gh", "pr", "view", str(pr_number), "--json", "title,body,state,url"],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh pr view {pr_number} failed.\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="labels")


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


if __name__ == "__main__":
    sys.exit(main())
