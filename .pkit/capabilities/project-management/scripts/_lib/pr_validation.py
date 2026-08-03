"""The single PR-body/title validator (DEC-013 / DEC-031), shared across the
PR lifecycle so a skeleton body is caught at the *ready* transition, not late
at the merge gate.

`validate-pr` (the standalone command), `open-pr` (non-draft), and `review-work`
(open-ready / flip draft→ready) all resolve through :func:`validate_pr` — one
place the PR rules live, so the "empty `## Summary` / bare `- [ ]` Test plan /
empty `## Doc impact`" skeleton can't sail past open + review and only fail at
merge (the fail-late trap this module exists to close). Merge stays the backstop;
drafts stay exempt (validation runs only when a PR goes ready-for-review).

The checks:
  * title matches `titles.yaml`'s `pr` Conventional-Commits regex, and its
    `<type>` matches the closing issue's `type:*` mapping (when supplied);
  * body carries a `Closes/Fixes/Resolves #N` keyword (git-conventions.yaml);
  * body carries a `## Doc impact` section (git-conventions.yaml / DEC-015);
  * body is authored — residual-placeholder detection per DEC-031 (an empty
    `## Test plan` checkbox is a warning at `create`, a hard-reject at
    `transition` — the phase the ready gate and the merge gate both pass).

Phase controls the Test-plan strictness: the ready transition passes
``PHASE_TRANSITION`` so it catches exactly what merge will reject.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Sibling _lib imports, dual-form so the module loads both as part of the `_lib`
# package (scripts/ on sys.path) and standalone-by-path (scripts/_lib/ on
# sys.path) — mirrors `_lib/substrate_writes.py`'s idiom.
try:
    import axis_labels  # type: ignore[import-not-found]
    from placeholder_detection import (  # type: ignore[import-not-found]
        PHASE_CREATE,
        detect_placeholder_residuals,
    )
except ImportError:  # pragma: no cover
    from _lib import axis_labels  # type: ignore[no-redef]
    from _lib.placeholder_detection import (  # type: ignore[no-redef]
        PHASE_CREATE,
        detect_placeholder_residuals,
    )


SEVERITY_HARD_REJECT = "hard-reject"
SEVERITY_BYPASSABLE = "bypassable-with-audit"
SEVERITY_WARNING = "warning"

#: The severities that block a gate (as opposed to advisory warnings).
BLOCKING_SEVERITIES = (SEVERITY_HARD_REJECT, SEVERITY_BYPASSABLE)

CLOSING_KEYWORD_RE = re.compile(r"\b(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    severity: str
    label: str
    detail: str


def has_blocking(findings: list[Finding]) -> bool:
    """True when any finding is hard-reject or bypassable-with-audit."""
    return any(f.severity in BLOCKING_SEVERITIES for f in findings)


def validate_pr(
    *,
    pr_title: str,
    pr_body: str,
    titles: dict,
    classification: dict,
    git_conv: dict,
    closing_type_labels: list[str],
    capability_root: Path | None = None,
    phase: str = PHASE_CREATE,
) -> list[Finding]:
    """Validate a PR title + body against the methodology's PR rules.

    Pure over its inputs (no `gh` reads) so callers can validate a *composed*
    body before opening a PR, or a fetched body before flipping it ready.
    ``closing_type_labels`` is the closing issue's ``type:*`` labels for the
    title-type cross-check; pass ``[]`` to skip that cross-check (a caller that
    already derived the correct title from the issue, e.g. ``open-pr``).
    """
    findings: list[Finding] = []

    # Title regex + type cross-check.
    pattern = _pr_title_pattern(titles)
    if pattern:
        m = re.match(pattern, pr_title)
        if not m:
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "title.pattern",
                    f"PR title does not match Conventional Commits pattern: {pattern!r}",
                )
            )
        else:
            conv_type = m.group(1)
            expected_types = _expected_conv_types(closing_type_labels, classification)
            if expected_types and conv_type not in expected_types:
                if len(closing_type_labels) > 1:
                    findings.append(
                        Finding(
                            SEVERITY_WARNING,
                            "title.type-mismatch",
                            f"PR <type>={conv_type!r} differs from closing-issue type "
                            f"labels' mapping {expected_types!r}; multi-issue PR with "
                            "mixed types — warning per git-conventions.yaml.",
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            SEVERITY_HARD_REJECT,
                            "title.type-mismatch",
                            f"PR <type>={conv_type!r} does not match the closing issue's "
                            f"type:* label mapping {expected_types!r}.",
                        )
                    )

    # Body: closing keyword required.
    if not CLOSING_KEYWORD_RE.search(pr_body):
        findings.append(
            Finding(
                SEVERITY_HARD_REJECT,
                "body.closes",
                "PR body has no `Closes #N` / `Fixes #N` / `Resolves #N` reference "
                "(required by git-conventions.yaml).",
            )
        )

    # Body: Doc impact required.
    if "## Doc impact" not in pr_body:
        findings.append(
            Finding(
                SEVERITY_HARD_REJECT,
                "body.doc-impact",
                "PR body is missing the `## Doc impact` section "
                "(required by git-conventions.yaml).",
            )
        )

    # Residual-placeholder detection per DEC-031 (empty checkboxes / surviving
    # PR.md placeholder prose). Needs capability_root to read the live template.
    if capability_root is not None:
        for sev, label, detail in detect_placeholder_residuals(
            body=pr_body,
            structural_type="pr",
            body_format=pr_body_format(),
            capability_root=capability_root,
            phase=phase,
        ):
            findings.append(Finding(sev, label, detail))

    return findings


# PR-body format descriptor for the placeholder-detection helper. Mirrors the
# body-format.yaml structure the issue side uses. `## Test plan` is the only
# required checkbox section in PR.md; `## Doc impact` / `## Summary` are prose,
# covered by the helper's prose-fingerprint signal.
_PR_BODY_FORMAT: dict = {
    "bodies": {
        "pr": {
            "required_sections": [
                {
                    "heading": "## Test plan",
                    "has_checkboxes": True,
                    "severity": "[validation-severity:hard-reject]",
                    "purpose": (
                        "Checkboxes describing the testing strategy. Omit the "
                        "section entirely for trivial changes; when present, at "
                        "least one authored item is required."
                    ),
                },
            ],
        },
    },
}


def pr_body_format() -> dict:
    """The body-format descriptor for the PR placeholder check."""
    return _PR_BODY_FORMAT


def _pr_title_pattern(titles: dict) -> str | None:
    formats = titles.get("formats") or {}
    entry = formats.get("pr")
    if isinstance(entry, dict):
        p = entry.get("pattern")
        if isinstance(p, str):
            return p
    return None


def extract_closing_issues(pr_body: str) -> list[int]:
    """The issue numbers a PR body closes (Closes/Fixes/Resolves #N), de-duped."""
    out: list[int] = []
    for m in CLOSING_KEYWORD_RE.finditer(pr_body or ""):
        n = int(m.group(1))
        if n not in out:
            out.append(n)
    return out


def _expected_conv_types(type_labels: list[str], classification: dict) -> list[str]:
    """Map each `type:*` label to its expected pr_conv_type (+ alternates)."""
    mapping = classification.get("pr_type_mapping") or []
    out: list[str] = []
    for label in type_labels:
        value = axis_labels.read("type", [label])
        for entry in mapping:
            if not isinstance(entry, dict):
                continue
            if entry.get("issue_label_value") == value:
                t = entry.get("pr_conv_type")
                if isinstance(t, str) and t not in out:
                    out.append(t)
                for alt in entry.get("alternates") or []:
                    if isinstance(alt, str) and alt not in out:
                        out.append(alt)
                break
    return out
