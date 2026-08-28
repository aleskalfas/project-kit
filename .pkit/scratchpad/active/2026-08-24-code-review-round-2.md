---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-24
---

# Code review round 2

*PR #758 · HEAD `e4f5g6h` (author pushed a fix) · fresh `review-pr` run re-reviews on the new HEAD (round-1 now stale). **One aggregated review.** Still blocked on one security item.*

---

## 🧰 pkit review — ⛔️ CHANGES_REQUESTED · code ✓ · security ✗ · docs ✓

### 🤖 `code-reviewer` → ✅ APPROVED
Both blocks resolved (400 on bad JSON; dedup lock-guarded). Round-1 advisories stand, non-blocking.

### 🤖 `security-reviewer` → ⛔️ CHANGES_REQUESTED
- *Blocking:*
  - `compare_digest` fixed ✓, but the secret is **still logged** — the `log.debug` moved to `config.py:12` rather than being removed

### 🤖 `docs-reviewer` → ✅ APPROVED
`docs/webhooks.md` added; endpoint + `WEBHOOK_SECRET` documented, matches behaviour.

<sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

**Inline comments:**
↳ `config.py` L12 — security: same secret-leak, relocated. Drop the debug line entirely.
