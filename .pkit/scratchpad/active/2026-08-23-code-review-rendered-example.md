---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-23
---

# Code review rendered example — index

The rendered review for PR #758 is split **one file per round** (a round = one `review-pr` run against the current HEAD → **one aggregated review** carrying every perspective + all inline findings; overall verdict = all-must-approve across perspectives):

- `2026-08-24-code-review-round-1.md` — HEAD `a1b2c3d`: aggregate `CHANGES_REQUESTED · code ✗ · security ✗ · docs ✗` (2+2+1 findings, inline).
- `2026-08-24-code-review-round-2.md` — HEAD `e4f5g6h` (author's fix): aggregate `CHANGES_REQUESTED · code ✓ · security ✗ · docs ✓` (one partial-fix item remains).
- `2026-08-24-code-review-round-3.md` — resolution + merge, two endings: **A** security ✓ → clean gate summary; **B** operator overrides → override audit → `security ⤼ overridden`.

Design commentary + the model live in the companions: `2026-08-23-code-review-surface-template.md` and `2026-08-18-pkit-comment-house-style.md`.
