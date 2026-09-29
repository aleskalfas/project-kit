#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "pathspec>=0.12",
# ]
# ///
"""Project-management capability — check-doc-mapping (verb-subject per DEC-020).

Check a pull request's documentation obligations (DEC-015 + DEC-053 +
ADR-019). The obligations are the resolved `pkit::work-tracking:doc-check` data
point, read through the backbone (`pkit connections resolve <point> --json`),
and this check applies them to the diff:

- **The code->doc mapping** is the point's always-included default filler
  (`fill-doc-check`, one obligation per rule). A mapping obligation is met
  exactly as it always was: when the diff touches the rule's code, at least one
  mapped doc is in the diff too — or a line in the PR's `## Doc impact`
  section names the code path or the rule's glob.
- **A contributed obligation** — from a documentation capability, or the
  project's own filler file — is met only by the page's answer in the diff:
  a changed file matches its `document`. A `## Doc impact` line meets nothing;
  the form of the answer is the core change check's to verify (`pkit friction
  check`).
- **Unresolved means fail.** The point's inert policy is `fail`: when a filler
  cannot answer, the point does not resolve and the check exits 1, naming the
  filler and the fix, rather than pass on fewer obligations than it should.

With no documentation capability installed the point holds the mapping's
obligations alone, and the check prints and exits exactly as it did before the
point existed.

ADR-019 framing: this script is the capability-owned *mechanism* — a read-only
check that exits non-zero on an unsatisfied mapping. The real *boundary* is the
adopter wiring it as a required CI status check behind branch protection
(`gh api` / `bash -c` evade any tool-layer check, per ADR-004). At the merge-pr
layer it is only a warning (a speed-bump). The capability ships the mechanism;
the adopter wires the boundary; the residual gap is declared, not hidden.

Configuration in `project/config.yaml` (opt-in, default off — ADR-019 Case A):
  code_path_to_doc_mapping:
    enforce: true            # default false -> advisory: report would-fire, exit 0
    rules:
      - code: "packages/cli/src/commands/registry.ts"   # gitignore-style glob
        docs: ["packages/cli/README.md"]
  doc_check:                 # DEC-053: each contributed source's own setting
    sources:
      friction: enforcing    # default advisory; the mapping keeps `enforce` above

Use SURGICAL 1:1 couplings (a narrow surface file -> its reference doc). A broad
`tree/** -> README` rule false-positives on most PRs (see the dry-run audit);
keep those advisory (enforce: false) or don't map them. The mandatory
`## Doc impact` section remains the universal hard gate; this adds targeted
enforcement on couplings that genuinely move together.

Diff source: `--base <ref>` (default origin/main). Changed files come from
`git diff --name-only --diff-filter=ACMRT <base>...HEAD` — added/copied/
modified/renamed/type-changed; a *deletion* of a code file does not demand a
doc.

Override (bypassable-with-audit): a line in the PR body's `## Doc impact`
section that names the triggering code path (or the rule's code glob) marks that
mapping rule satisfied — a human-visible, reviewed reason, not a silent skip.
It overrides mapping rules only. PR body from `--pr-body-file <path>` or,
failing that, `gh pr view` resolved from the current branch. The project may
also remove an obligation from the point with a reason (the removal override of
its filler file); the check prints each one removed.

Exit codes:
  0  every enforced obligation met (or enforcement off / nothing to check)
  1  an enforced obligation unmet (the mapping with enforce on; a contributed
     source set enforcing), or the doc-check point does not resolve
  2  usage error (bad config, git failure, the point unreadable)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pathspec
from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, doc_check  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    resolve_capability_root,
)


def _changed_files(base: str) -> list[str] | None:
    """Non-deleted files changed between merge-base(base, HEAD) and HEAD."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", f"{base}...HEAD"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        print("error: git not found.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: git diff against {base!r} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _doc_impact_section(body: str) -> str:
    """Return the text of the PR body's `## Doc impact` section (lowercased)."""
    if not body:
        return ""
    lines = body.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("## "):
            if capture:
                break  # next section ends Doc impact
            capture = stripped.lower().startswith("## doc impact")
            continue
        if capture:
            out.append(line)
    return "\n".join(out).lower()


def _pr_body(args: argparse.Namespace, config: dict) -> str:
    if args.pr_body_file:
        try:
            return Path(args.pr_body_file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"warn: could not read --pr-body-file: {exc}", file=sys.stderr)
            return ""
    # Resolve the PR body from the current branch (CI / local). Best-effort:
    # if there is no PR, overrides simply aren't available.
    proc = gh_run(
        ["gh", "pr", "view", "--json", "body", "-q", ".body"], config, check=False
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout or ""


def _matches(glob: str, path: str) -> bool:
    """gitignore-style match of a single glob against a single path."""
    spec = pathspec.PathSpec.from_lines("gitignore", [glob])
    return spec.match_file(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check the code->doc mapping (DEC-015 + ADR-019). Read-only. "
            "Exits non-zero on an unsatisfied enforced mapping; the real "
            "boundary is wiring this as a required CI status check."
        ),
    )
    parser.add_argument(
        "--base", default="origin/main",
        help="Base ref to diff HEAD against (default: origin/main).",
    )
    parser.add_argument(
        "--pr-body-file", default=None,
        help="File containing the PR body (override source). Default: gh pr view.",
    )
    parser.add_argument(
        "--capability-root", type=Path, default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("check-doc-mapping", capability_root=capability_root):
        return 2

    config = load_adopter_config(capability_root)
    mapping = config.get("code_path_to_doc_mapping") or {}
    if not isinstance(mapping, dict):
        print(
            "error: code_path_to_doc_mapping must be a mapping with "
            "`enforce:` and `rules:` (per ADR-019).",
            file=sys.stderr,
        )
        return 2
    enforce = bool(mapping.get("enforce", False))
    rules = mapping.get("rules") or []
    settings, settings_problem = doc_check.source_settings(config)
    if settings_problem is not None:
        print(f"error: {settings_problem}", file=sys.stderr)
        return 2

    # The obligations: the resolved doc-check point (DEC-053) — the mapping's,
    # as the default filler printed them, and whatever else fills the point.
    try:
        point = doc_check.read_point()
    except doc_check.PointUnreadable as exc:
        print(f"error: could not read the {doc_check.POINT} point: {exc}.", file=sys.stderr)
        return 2
    obligations = doc_check.split(point, CAPABILITY_NAME)
    if not point.resolved or obligations.problems:
        _report_unresolved(point, obligations.problems)
        return 1
    contributed = obligations.contributed
    if not rules and not obligations.mapping and not contributed:
        print("check-doc-mapping: no rules configured; skipped.")
        return 0

    changed = _changed_files(args.base)
    if changed is None:
        return 2
    changed_set = set(changed)

    section = _doc_impact_section(_pr_body(args, config))

    mode = "enforce" if enforce else "advisory"
    print(f"check-doc-mapping: {len(rules)} rule(s), {len(changed)} changed file(s), mode={mode}")
    if contributed:
        print(
            f"check-doc-mapping: {len(contributed)} contributed obligation(s) from "
            f"{', '.join(doc_check.sources_of(contributed))}"
        )

    unsatisfied: list[str] = []
    for obligation in obligations.mapping:
        code_glob = str(obligation["code"])
        docs = obligation["documents"]
        triggered = sorted(f for f in changed if _matches(code_glob, f))
        if not triggered:
            continue  # this rule's code surface wasn't touched
        doc_touched = any(
            any(_matches(str(d), f) for f in changed_set) for d in docs
        )
        if doc_touched:
            print(f"  ✓ {code_glob} → doc updated")
            continue
        # Override: the Doc-impact section names the glob or a triggering file.
        overridden = bool(section) and (
            code_glob.lower() in section
            or any(t.lower() in section for t in triggered)
        )
        if overridden:
            print(f"  ⊘ {code_glob} → overridden via `## Doc impact` (audited)")
            continue
        docs_str = ", ".join(str(d) for d in docs)
        print(f"  ✗ {code_glob} → {docs_str} (not updated; e.g. {triggered[0]})")
        unsatisfied.append(code_glob)

    # Contributed obligations: met only by the page's answer in the diff — the
    # page changed. The `## Doc impact` section is not read for them.
    unanswered: dict[str, int] = {}
    for obligation in contributed:
        source = str(obligation["source"])
        page = str(obligation["document"])
        if any(_matches(page, f) for f in changed_set):
            print(f"  ✓ [{source}] {page} → answered in the diff")
            continue
        print(f"  ✗ [{source}] {page} → no answer in the diff ({obligation['reason']})")
        unanswered[source] = unanswered.get(source, 0) + 1

    for obligation_id, reason in doc_check.removed(point):
        print(f"  − {obligation_id} → removed by the project filler: {reason}")

    if not unsatisfied and not unanswered:
        print(
            "check-doc-mapping: all touched mappings satisfied."
            if not contributed
            else "check-doc-mapping: every obligation met."
        )
        return 0

    failed = False
    if unsatisfied and enforce:
        print(
            f"\n[refused] {len(unsatisfied)} mapping(s) unsatisfied — update the "
            "mapped doc(s), or add a `## Doc impact` line naming the code path.",
            file=sys.stderr,
        )
        failed = True
    elif unsatisfied:
        print(
            f"\n[advisory] {len(unsatisfied)} mapping(s) would fire under enforce: true. "
            "Set code_path_to_doc_mapping.enforce: true (with surgical rules) to block.",
            file=sys.stderr,
        )
    for source, count in sorted(unanswered.items()):
        if doc_check.setting_of(settings, source) == doc_check.ENFORCING:
            print(
                f"\n[refused] {count} {source} obligation(s) unanswered — answer each on "
                "its page in this diff; a `## Doc impact` line does not meet them.",
                file=sys.stderr,
            )
            failed = True
        else:
            print(
                f"\n[advisory] {count} {source} obligation(s) unanswered. Set "
                f"doc_check.sources.{source}: enforcing to block.",
                file=sys.stderr,
            )
    return 1 if failed else 0


def _report_unresolved(point: doc_check.ResolvedPoint, problems: list[str]) -> None:
    """The point does not resolve, or an entry breaks the source rule: the check
    cannot see every obligation it should, so it fails rather than pass on fewer
    (DEC-053, the `fail` inert policy). Names each inert filler and its fix."""
    what = (
        f"does not resolve: {point.why}"
        if not point.resolved
        else f"carries what the check refuses: {'; '.join(problems)}"
    )
    print(
        f"[unresolved] the {doc_check.POINT} point {what}. The check cannot see every "
        "obligation it should, so it fails rather than pass on fewer (DEC-053).",
        file=sys.stderr,
    )
    for filler in point.inert:
        name = str(filler.get("name", ""))
        print(
            f"  inert: {name} ({filler.get('supplies', '')}): {filler.get('reason', '')}",
            file=sys.stderr,
        )
        if name == CAPABILITY_NAME:
            print(
                f"  fix: run `pkit pm {doc_check.FILLER_VERB}` to see why it gives no "
                "answer; run once online, it also provisions its dependency for the "
                "offline run.",
                file=sys.stderr,
            )
        else:
            print(f"  fix: update {name}, pin it, or uninstall it.", file=sys.stderr)
    if not point.inert:
        print(
            "  fix: `pkit validate` names the finding (its `connections` member).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
