---
id: ADR-042
title: Shared verdict selector — permissive read primitive, strict gate wrapper
status: accepted
date: 2026-07-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

When one parser/selector feeds **both** a security-relevant gate and a read surface, the shared primitive is **permissive** (the safe default for the read surface), and the **gate reaches it only through a required-argument strict wrapper** — so the fail-open default is *structurally unreachable* from the gate path. The realized instance is the DEC-028 reviewer-verdict selector, now shared by the merge gate (`done-work`) and the governed read surface (`show-pr --field review`, from #544): both must agree on *which comment is a reviewer's current verdict*, but only the gate may apply the freshness / membership / author-exclusion filters that make it safe. This ADR pins the discipline that keeps the gate un-foot-gunnable; it realizes DEC-028, it does not change it.

## Context

[project-management:DEC-028-agent-as-approver-paths] fixes the reviewer-verdict grammar, the latest-verdict-per-reviewer selection (robust to comment order), and the gate-checker's freshness / membership / author-exclusion rules; [project-management:DEC-032-conditional-reviewer-requirements] resolves the required-reviewer set per PR. That selection logic lived **inline** in `done-work.py` (the merge gate). Issue #544 needed the *same* verdict — token + reasons — readable through the governed pm surface (`show-pr`), because an operator/agent could see the verdict label but had no allowed path to the reasons (raw `gh pr view --comments` is correctly denied). Two consumers now need the one selection; hand-rolling it twice would let the two drift on the invariant that must not — "which comment is a reviewer's current verdict" ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)).

The two consumers differ on **filtering**, not on selection: the gate must drop stale, non-required, and self-authored verdicts; the read surface legitimately wants *all* posted verdicts (latest per reviewer) so an operator sees the full picture. Extracting the shared selection into `_lib/agent_verdicts.py` raised the design question this ADR answers: how to share the selection without letting the read surface's permissiveness leak into the gate.

## Decision

**One shared selector; the gate reaches it only through a strict, required-argument wrapper.** Five points.

- **D1 — Permissive primitive, strict gate wrapper.** `latest_verdicts_per_reviewer(...)` is the shared, *permissive* selection primitive (no freshness / membership / author-exclusion filter). The gate does **not** call it directly; it calls `gate_verdicts(comments, *, min_timestamp, local_reviewer_ok, remote_reviewer_ok)` whose three security-relevant filters are **required, non-defaulted** keyword arguments — omitting any is a call-site error, not a silent fail-open. The permissive default is therefore structurally unreachable from the gate path. The burden of explicitness sits on the security-relevant path, not the read path.

- **D2 — The read surface is a superset, and says so.** `show-pr --field review` calls the permissive primitive directly and shows a **superset** of the gate's subset — including stale and non-required verdicts. It **annotates staleness** (a verdict predating the latest commit is marked as one the merge gate will not count), so an operator or agent is never misled that a stale `APPROVED` is mergeable.

- **D3 — Fail-closed stays with the caller.** The gate owns fail-closed: `done-work` computes the freshness anchor (the latest-commit timestamp) and **refuses before calling the module** when it cannot be established. The module is a pure selector that trusts the anchor it is handed; it never decides fail-open-vs-closed.

- **D4 — Scope: posted-comment parsing only.** This module parses the **first line of a posted comment**. It is **not** the raw-output "scan for the first grammar-matching line anywhere" extractor that `review-pr` owns (DEC-028's separate consumer-scan contract, which must tolerate agent preamble). Raw-output extraction must not be routed through this module.

- **D5 — One instance, not yet a promoted pattern.** This records *this* decision; it deliberately does **not** promote the strict/permissive split to a core (COR-level) pattern. Per COR-007, a second independent split earns the promotion; one instance is a recorded decision. The module lives in the pm capability's `_lib/` — all consumers are pm surfaces, so no backbone promotion (the same placement call [ADR-038](ADR-038-contribution-collector.md) made).

## Rationale

**Why permissive-primitive + strict-wrapper rather than a safe-by-default single function.** The alternative — one function with the filters defaulted to safe values — was rejected: it makes the *read* surface the awkward caller (it must opt *out* of filters it never wants) and, worse, still leaves the gate one forgotten keyword-argument away from silent weakening (a caller who omits `min_timestamp` gets a plausible-looking but fail-open result). Inverting it puts the explicitness where the risk is: the read path gets the natural, permissive primitive, and the gate cannot be constructed without naming every safety filter. A missing filter on the gate path is a loud `TypeError` at construction, not a quiet hole discovered in production.

**Why share the selection at all (not just the grammar).** The invariant most likely to drift between two hand-rolled implementations is not the line grammar (a regex) but *latest-per-reviewer-by-timestamp* — the subtle, order-independent selection DEC-028 step 5 specifies. Sharing only the grammar would leave that subtlety duplicated; sharing the selection is the COR-007-correct cut. The critic + architect review confirmed the moved grammar is byte-identical to the deleted inline code and the gate's five DEC-028 filters are all preserved.

**Why this is ADR-worthy though it is one refactor.** The strict/permissive split is a non-obvious *safety* choice a reader cannot reconstruct from DEC-028 alone — DEC-028 says *what* the gate filters, not *why the shared selector is built so the gate cannot forget to filter*. Recording it is documentation-of-a-decision (the posture [ADR-038](ADR-038-contribution-collector.md) took for its family's rule), not premature generalisation — D5 explicitly withholds promotion.

### Alternatives considered

- **Single function, filters safe-by-default.** Rejected (see Rationale) — awkward for the read surface, still fail-openable by omission on the gate.
- **Share only the grammar; leave selection per-consumer.** Rejected — re-opens the latest-per-reviewer drift COR-007 is invoked to close.
- **Promote the split to a COR-level pattern now.** Rejected — one instance; COR-007 says wait for the second (D5).
- **Put the selector in the backbone.** Rejected — no non-pm consumer; speculative generality (ADR-038 rule 1).

## Implications

- **`_lib/agent_verdicts.py`** is the single source of truth for parsing + selecting *posted-comment* DEC-028 verdicts: `parse_verdict_line`, the permissive `latest_verdicts_per_reviewer`, and the strict `gate_verdicts` wrapper.
- **`done-work`** calls `gate_verdicts` (required filters) and retains fail-closed freshness ownership; its gate behaviour is unchanged (verified: identical grammar, 63 gate tests green).
- **`show-pr --field review`** calls the permissive primitive, marks stale verdicts, and documents the superset relationship.
- **A future gate-consuming caller** must go through `gate_verdicts` (or an equally strict wrapper); calling the permissive primitive from a gate path is the anti-pattern this ADR names.
- **`review-pr`** keeps its own raw-output scan-anywhere extractor (D4) — it must not be routed through this module.
- **Surface/bump:** the new `show-pr --field review` is a surface change → pm capability `package.yaml` minor bump; the extraction itself is behaviour-preserving. Migration-free (additive; no rename/removal, no `schema_version` change).
- **Stands on** DEC-028, DEC-032, COR-007, and ADR-038 (the shape-sibling) — all accepted.
