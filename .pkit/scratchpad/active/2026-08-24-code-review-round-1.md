---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-24
---

# Code review round 1

*PR #758 `feat: webhook receiver` · HEAD `a1b2c3d` · one `review-pr` run → **one aggregated review**. Legend: ⛔️ CHANGES_REQUESTED · ✅ APPROVED. `↳` = inline comment on a diff line.*

---

## 🧰 pkit review — ⛔️ CHANGES_REQUESTED · code ✗ · security ✗ · docs ✗

### 🤖 `code-reviewer` → ⛔️ CHANGES_REQUESTED
- *Blocking:*
  - Unhandled `json.JSONDecodeError` on a malformed body → uncaught 500 (`webhook.py:31`)
  - Dedup set mutated without a lock — concurrent deliveries can double-process (`webhook.py:58`)
- *Advisory:*
  - `TIMEOUT = 30` — magic constant; name it
  - `handle()` is 90 lines — extract verify + dispatch
  - no malformed-body test case

### 🤖 `security-reviewer` → ⛔️ CHANGES_REQUESTED
- *Blocking:*
  - Signature compared with `==` — timing-attack vector; use `hmac.compare_digest` (`verify.py:19`)
  - Webhook secret written to the debug log (`verify.py:24`)
- *Advisory:*
  - no replay window — consider a nonce + timestamp

### 🤖 `docs-reviewer` → ⛔️ CHANGES_REQUESTED
- *Blocking:*
  - New endpoint `/webhooks/deploy` + config key `WEBHOOK_SECRET` undocumented (DEC-015 doc obligation: `webhook.py` → `docs/webhooks.md`)

<sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

**Inline comments** (part of the same review):
↳ `webhook.py` L31 — code: wrap `json.loads(body)` — a malformed payload crashes the worker; return 400.
↳ `webhook.py` L58 — code: `self._seen.add(id)` races under concurrent deliveries; guard with the lock.
↳ `verify.py` L19 — security: **timing attack.** `sig == expected` short-circuits; use `hmac.compare_digest(sig, expected)`.
↳ `verify.py` L24 — security: **secret leak.** `log.debug(f"secret={secret}")` writes the shared secret to logs. Remove.
