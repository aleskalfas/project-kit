---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-28
---

# Review output + merge-gate decisions (settled design → realization)

**Anchor task:** Feature #795 ("Review output + merge-gate model") under EPIC #725
(code-review discipline). Sibling of Feature #757 (comment house-style + render
seam, under EPIC #756). Split from #757 so it can be worked in parallel.

**Relationship to #757 (the one shared contract):** this feature *consumes* #757's
render seam through the **`format(data) → string`** interface. Per the
`review-output-architecture` note, review ships its **own temporary formatter**
behind that seam so it is **not blocked** on #757; the durable shared contracts are
the **`format(data) → string` interface + the review data schema**. Neither feature
depends on the other's delivery — only on those contracts — so A and B proceed in
parallel.

Design source: the `code-review-*` notes (rendered surface), `review-output-
architecture` (the data model, from a parallel instance — reconciled below), and
this note (the settled decisions).

---

## 1 · Review-as-data (the central shift)

Move the source of truth for a review from the posted comment to **structured
data**. The comment becomes a *rendering* of the data; the gate reads the data.

- **Review data schema** (the load-bearing contract): a single reviewer entry
  (reviewer name, verdict, findings with severity/remit/location, advisory-vs-
  blocking) + the combined review (per-sub-reviewer entries + an overall verdict).
- **Shared reviewer prompt template** — one template describing the common review
  process; "fill the template" == "emit data conforming to the schema"; per-reviewer
  specialisation stays in each agent's `.md` body. Replaces the ad-hoc prompt in
  `review-pr._invoke_agent` (scan-anywhere parse, fail-closed on unparseable).

## 2 · Actor / aggregation model

- **Actors:** the local agent panel (ONE actor), each human (an actor), each
  remote/independent reviewer (an actor).
- **Level 1 — within the local pass:** the panel's sub-reviewers (code / security /
  docs / pm) combine into **one aggregate review → one comment per round**.
  *Resolves the fork:* `review-output-architecture` argued for one combined comment;
  the older `code-review-surface-template` rendered one native review per perspective.
  **Decision: combined** (one review per round), superseding the per-perspective
  rendering.
- **Level 2 — across actors:** the combined agent review + human native reviews +
  remote reviews **mix** into the review the gate judges.

## 3 · Machine record = read the human header, anchored on the verdict WORD

(Chosen over a hidden data block, on the no-divergence / WYSIWYG argument.) The
per-agent verdict line is a **schema-owned, drift-guarded contract**; the parser
keys on the stable token (`APPROVED` / `CHANGES_REQUESTED`) and **ignores the
decoration** (emoji, backticks) — restyle freely as long as the word stays. A
**round-trip test (`parse(render(x)) == x`)** guarantees renderer↔parser agree.
This is the gate-read side of the seam contract #757 emits.

## 4 · Merge-gate model

- **G1 · Authority mode = hybrid.** Auto-detect (branch-protection / self-authored)
  + explicit `review_authority: pkit-verdict | github-native` override. Solo → pkit
  comment verdict is authority; team → GitHub native review state is authority
  (pkit's own review is pre-flight/advisory there).
- **G2 · Staleness SHA source = hybrid.** Native reviews use GitHub's `commit_id`;
  comment verdicts **embed the HEAD SHA** (a fact, not a verdict — no divergence).
- **G3 · Staleness strictness = strict + per-reviewer audited override.** Any new
  commit invalidates all applicable approvals (matches GitHub dismiss-stale;
  composes with one-review-per-round anchored to a commit); override keeps a
  specific reviewer's approval with an audited reason.
- **G4 · Mixed reviewers = authority-wins.** The mode's authority gates; the
  non-authority kind is advisory. No per-reviewer promotions.
- **G5 · Override / bypass = audited override of pkit's OWN verdict.** Native
  branch-protection override stays GitHub's `--admin` (pkit surfaces, doesn't own).
- **G6 · Reviewer applicability** (already built: DEC-032 + `review-contributions.yaml`).
  Predicates: `floor` (diff-property) + `match` (classification). Shipped panel:
  code + security ride `touches-code`; docs rides `touches-code` (the code→docs
  obligation) + `match: type:*`. **NEW: add a `touches-docs` floor** so a docs
  change fires doc review from the diff alone (closes the unclassified-docs-only
  gap). security fires on all code (via `touches-code`).

## 5 · Tamper-evidence

Moves from the verdict comment's marker (DEC-047 / ADR-042) to the **data
artifact** — a human still cannot forge a gate-counted approval. Open question: where
the combined data lives (marked/fenced payload vs committed file vs PR artifact) and
how it stays tamper-evident there.

## 6 · Supersession — AUTHORISED (was A6)

The aggregate one-review-per-round model + reading verdicts this way **supersedes
part of DEC-028** (one-comment-one-verdict) **and ADR-042** (first-line gate
selector). *User signed off.* Must be **explicit**: a DEC-028 amendment + an ADR-042
companion. **Coupled:** the DEC-047 freeform spoof guard reads the same grammar, so
any grammar change ships **in the same change-set** as the guard (else `comment-pr`
becomes a verdict-forgery vector). Blast radius = the merge gate, which **fails
closed**.

---

## Artifacts to produce (realization)

1. **pm DEC** — the review-data / gate-read model + the actor/aggregation model;
   carries the **DEC-028 amendment** (aggregate unit) + **DEC-032** (read source) +
   **DEC-050** (override composes with the combined pass).
2. **project-kit ADR** — the **ADR-042 companion** (gate selector moves off
   first-line-per-comment; tamper-evidence on the data artifact) + the
   `parse(render(x)) == x` invariant on the gate-read side.
3. **software-engineering DEC-002 amendment** — panel: three independent verdicts →
   one aggregate round; reviewers emit findings/data, not comment bytes.

Acceptance gate applies before any implementation cites these. The `touches-docs`
floor (G6) is a small, self-contained early slice.

## Open questions

1. The review data schema's exact attributes (single entry + combined + overall).
2. Where the combined data lives + how tamper-evidence re-homes there (§5).
3. Cross-actor gate composition (agent-pass read-from-data + human/remote paths).
4. Migration / back-compat: N-comments → one-combined changes what `done-work` reads
   and what `show-pr --field review` displays; dual-read during transition?
   (Grammar compatibility window — accept both grammars for one minor cycle.)

## References

- Issues: #795 (anchor) · #725 (EPIC) · #757 / #756 (sibling: house-style + seam) ·
  #670 (native review) · #690 (audit feedback).
- Decisions: DEC-028 (verdict) · DEC-032 (reviewer resolution / contributions) ·
  DEC-050 (per-reviewer override) · DEC-002 (se panel) · DEC-047 (freeform / spoof
  guard) · DEC-049 (audit/journal). ADRs: ADR-042 (first-line gate selector) ·
  ADR-037 (provenance write-path) · ADR-026 / ADR-031 (seam family).
- Design scratchpads (this branch): `code-review-surface-template`,
  `code-review-agent-block-styles`, `code-review-round-{1,2,3}`,
  `review-output-architecture`.
- Sibling decisions note (#757): `2026-08-27-comment-render-seam-decisions.md`.
