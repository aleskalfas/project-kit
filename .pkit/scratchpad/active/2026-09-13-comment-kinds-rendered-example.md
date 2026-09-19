---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-13
---

# Comment kinds rendered example

Companion to **DEC-052** (`comment-house-style`) — every pkit comment kind rendered as it
would appear on GitHub, so the content + style model can be eyeballed before the DEC is
accepted and before the render-seam ADR pins the exact bytes.

Example versions throughout: `tree 1.150.0 · pm 0.55.0 · cli 1.150.0`. The invisible
`<!-- pkit-<kind> -->` marker is noted under each block. Exact byte-ordering of marker vs
footer, and the footer sentinels, are the **render-seam ADR's** job.

> **Converged — readability pass 2** (the `readability-reviewer` loop; no blocking issues
> remain). Conventions:

## Converging conventions

- **No `🧰 pkit` prefix** — the footer `<sub>🧰 pkit · tree · pm · cli</sub>` is the single
  pkit mark.
- **Per-kind icon** (authored kinds only): `🎫` filing · `⚖️` override · `🚦` move · verdict
  is agent-led (`🤖 <agent>`). Pass-through kinds (freeform, hook) have **no** kind line —
  just the user's words + footer.
- **One separator grammar:** `·` separates peer header tokens · `→` is reserved for a
  transition or outcome (state→state, verdict→outcome) · `—` introduces a one-line gloss ·
  **rationale/detail drops to its own prose line** (never appended with `;`).
- **Header-then-detail:** a header line carries only scannable tokens (kind · disposition ·
  transition); reasoning goes in a **separate paragraph below** — a blank line *must*
  separate them, since a bare newline collapses into the header in rendered markdown
  (the run-on you'd otherwise still see) — or as a `-` list when multi-point.
- **Override header grammar:** `⚖️ override · [<what> →] <disposition> [· authorised by <name>]`
  — `<what> →` (what was overridden, e.g. a reviewer's finding) appears *only* for a
  per-finding override; `<disposition>` is the small tag (`false positive` / `accepted
  risk` / …); `· authorised by <name>` *only* when the poster ≠ authoriser. The **reason
  drops to its own line** — a clean sentence, or a `-` list when genuinely multi-point,
  never a `;`-run-on. Lifting *what* into the header is what kills the run-on (the reason
  then has one job — justify), and `<what> → <disposition>` reuses verdict's
  `subject → outcome` model, so a reader who learned verdict gets override for free.
- **Verdict keeps no kind-icon:** `🤖 <agent> → <outcome>`, where `⛔️` / `✅` *is* the
  verdict's identity in the icon column. A second leading glyph would break the
  one-glyph-per-kind rule.
- **Filing carries no footer** (open question resolved → option a): the birth-stamp *is*
  the provenance and can't drift, so the footer would be pure duplication.

---

## Full issue in context — where each provenance element sits

The only provenance in the **body/description** is the footer; the filing record is a
separate **thread comment**.

**▸ Description (the issue body):**

> Feature: #720
>
> ## What
> A `/webhooks/deploy` endpoint that receives deploy events and updates the release board.
>
> ## Acceptance criteria
> - [ ] Endpoint verifies the HMAC signature before processing.
> - [ ] Malformed payloads return 400, never crash the worker.
> - [ ] `docs/webhooks.md` documents the endpoint + `WEBHOOK_SECRET`.
>
> ## Doc impact
> New public endpoint + config key — `docs/webhooks.md`.
>
> ---
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

**▸ Comment thread, first comment (posted by pkit at creation):**

> 🎫 filed · tree `1.150.0` · pm `0.55.0` · cli `1.150.0` · 2026-09-13

`<!-- pkit-provenance:filing -->` — the birth-stamp *is* the provenance (immutable, can't
drift), so **no footer** here.

---

## filing — a birth-stamp, one line

> 🎫 filed · tree `1.150.0` · pm `0.55.0` · cli `1.150.0` · 2026-09-13

`<!-- pkit-provenance:filing -->`

## override — standalone, self-posted (disposition only; no `<what>`, no authoriser)

> ⚖️ override · false positive
>
> Tag is validated against a semver allowlist upstream, so the `shell=True` path is unreachable (#740).
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-override -->`

## override — per-finding, bot-posted (the four-field form: `<what> → <disposition> · authoriser`)

> ⚖️ override · security-reviewer's `shell=True` finding → false positive · authorised by Aleš Kalfas
>
> Dev-gated log line, never runs in deploy (#761).
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-override -->` — the two header slots are **independent**: `<what> →` marks a
per-finding override (whoever posts); `· authorised by <name>` appears **only** when a
bot posted it. **Run under your own account, the authoriser drops** (GitHub shows you as
the comment-author): `⚖️ override · security-reviewer's `shell=True` finding → false positive`.

## override — multi-point reason (a `-` list, never a `;`-run-on)

> ⚖️ override · accepted risk
>
> - No replay window yet — tracked for next milestone (#802).
> - Endpoint stays internal-only until then; unreachable from the public gateway.
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-override -->`

## move — `<from> → <to>`, causation in words

> 🚦 move · `todo → in-progress` — cascade from #613
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-move -->`

## overridden move — ONE comment: move header + a stacked override sub-block

> 🚦 move · `in-review → done` — merged #718
>
> ⚖️ override · security-reviewer's `shell=True` finding → false positive · authorised by Aleš Kalfas
>
> Dev-gated log line, never runs in deploy (#761).
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-move -->` — one comment, one marker; the override reads exactly like a
freestanding override sub-block (the consistency win).

## verdict — a reviewer's verdict (agent-led; `🤖` identity is off-surface)

> 🤖 `security-reviewer` → ⛔️ CHANGES_REQUESTED
>
> **Blocking**
> - Command injection — a remote-fetched tag is interpolated into a `shell=True` command (`deploy.py:42`).
>
> *Advisory*
> - No rate-limit / replay window on the endpoint.
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-verdict -->` — single-reviewer content model; the one-review-per-round
**aggregate layout** is Feature #795's grammar, not DEC-052. *(Resolved: no dedicated
verdict kind-icon — the `⛔️` / `✅` outcome glyph is the verdict's identity in the icon
column; a second leading glyph would break the one-glyph-per-kind rule.)*

## freeform — pass-through (no kind line; frame around the user's words)

> Can we confirm the webhook secret rotation is scheduled before this ships? cc @alice
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-freeform -->`

## hook — pass-through (adopter's configured message, framed)

> 🚀 Deployed to staging: https://staging.example.com/builds/718
>
> <sub>🧰 pkit · tree `1.150.0` · pm `0.55.0` · cli `1.150.0`</sub>

`<!-- pkit-hook: deploy-notify -->` — *accepted tradeoff: the adopter's leading `🚀` sits in
the kind-icon column and could momentarily read as a pkit kind. It's the adopter's text,
not pkit's to change.*

---

## Retirement

Illustrative companion to DEC-052; retire with the DEC (or drop) once the render-seam ADR
lands the concrete renderer and the readability loop has converged the final format.
