---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-23
---

# Code review surface template

A rendered mock-up of the **ideal** code-review surface on a PR, so we can eyeball it before crystallizing. Companion to `2026-08-18-pkit-comment-house-style.md` (the house style) and the code-review panel (`software-engineering:DEC-002`, per-reviewer override `DEC-050`). Everything here is illustrative markdown — how the comments would *render* on GitHub.

## Model being rendered

A **panel** — `code-reviewer` (generalist) · `security-reviewer` · `docs-reviewer` — each producing **one native GitHub review** carrying: an event (APPROVE / REQUEST_CHANGES), a **house-styled summary body**, and **inline line-anchored comments** for specific findings. Plus a per-reviewer **override audit** and a **gate summary** on merge. All in the one `🧰` house style; every comment/body ends with the universal `<sub>` provenance footer.

Design points shown:
- The house-styled header line **is** the gate-parsed verdict line (unified grammar — the parser changes to match).
- **Blocking vs advisory** are visually separated (DEC-002: block only on objective failures).
- **Inline** findings live on the diff (native reviews API — extends #672's body-only delivery).
- The **override** audit is prose + verdict-grammar-distinct (never mistaken for a verdict).

---

## Scenario

PR **#742** — `feat: add tag-fetch + deploy step`. `code-reviewer` passes with one advisory; `security-reviewer` blocks on a real injection; `docs-reviewer` passes. Two variants of resolution shown: **(X)** author fixes → clean merge; **(Y)** operator overrides the security block.

---

## 1 · Per-reviewer verdicts (each = one native GitHub review)

### `code-reviewer` — native review, event: **APPROVE**
> **Summary body (renders under the review):**
>
> 🧰 pkit review · code-reviewer — APPROVED
>
> No blocking issues.
>
> *Advisory (non-blocking):*
> - `fetch_tag()` swallows the subprocess error — consider surfacing stderr.
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

### `security-reviewer` — native review, event: **REQUEST_CHANGES**
> **Summary body:**
>
> 🧰 pkit review · security-reviewer — CHANGES_REQUESTED
>
> **Blocking (1):**
> - Command injection — a remote-fetched tag is interpolated into a `shell=True` command. See inline on `deploy.py:42`.
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>
>
> **Inline comment, anchored to `deploy.py` line 42:**
> > 🧰 security-reviewer — **Command injection.** `subprocess.run(f"git checkout {tag}", shell=True)` interpolates a remote-fetched tag. Pass an argv list and drop `shell=True`.

### `docs-reviewer` — native review, event: **APPROVE**
> 🧰 pkit review · docs-reviewer — APPROVED
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

---

## 2 · Resolution variant X — author fixes, re-review, clean merge

`security-reviewer` re-runs on the new commit → native review, event **APPROVE**:
> 🧰 pkit review · security-reviewer — APPROVED
>
> Prior block resolved (argv list, no shell). ✓
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

**Gate summary on `done-work` (merged):**
> 🧰 pkit gate — merged #742 · code ✓ · security ✓ · docs ✓ · CI green
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

---

## 3 · Resolution variant Y — operator overrides the security block

**Per-reviewer override audit** (`done-work --bypass-reviewer security-reviewer --bypass-reason "…"`) — prose, verdict-grammar-distinct:
> 🧰 pkit override · security-reviewer — false positive: the tag is validated against a semver allowlist upstream (#740); the `shell=True` path is unreachable.
>
> Reviewer state at override: **CHANGES_REQUESTED** (block: [comment](#)). 
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

**Gate summary on `done-work` (merged):**
> 🧰 pkit gate — merged #742 · code ✓ · security ⤼ overridden · docs ✓ · CI green
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

---

## What this mock-up commits us to (for discussion)

- **Header = parsed line.** `🧰 pkit review · <perspective> — APPROVED|CHANGES_REQUESTED` is both the house style *and* the gate-parsed grammar → the `done-work` parser + `stamp_verdict` change in lockstep (DEC-028 amendment).
- **Native review is the vehicle**, carrying event + summary body + **inline comments**. Extends #672 (body-only today) to the reviews API with `comments:[{path,line,body}]`. **This is the biggest net-new piece.**
- **Override audit** never carries a `pkit review · … — VERDICT` line → the gate reader can't mistake it (DEC-050 satisfied, house-styled).
- **Gate summary** is a first-class house-styled comment: `code ✓ · security ⤼ overridden · docs ✗ missing` — the honest at-a-glance roll-up (DEC-002 companion c).
- **Footer** on every body/comment (universal provenance).

## Complex worked example — the whole thread

**PR #758 — `feat: webhook receiver for deploy events`.** Touches `webhook.py`, `verify.py`, `config.py`, `tests/test_webhook.py`; `docs/` untouched. Reviewed across three rounds. This is the full PR conversation, top to bottom, as it would render.

### Round 1 — initial panel review (HEAD `a1b2c3d`)

**`code-reviewer` — native review · REQUEST_CHANGES**
> 🧰 pkit review · code-reviewer — CHANGES_REQUESTED
>
> **Blocking (2):**
> - Unhandled `json.JSONDecodeError` on a malformed body → uncaught 500 (`webhook.py:31`).
> - Dedup set mutated without a lock — concurrent deliveries can double-process (`webhook.py:58`).
>
> *Advisory (3):*
> - `TIMEOUT = 30` — magic constant; name it.
> - `handle()` is 90 lines; extract signature-verify + dispatch.
> - `tests/test_webhook.py` has no malformed-body case.
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>
>
> ↳ inline `webhook.py:31` — 🧰 code-reviewer: wrap `json.loads(body)` — a malformed payload crashes the worker. Return 400.
> ↳ inline `webhook.py:58` — 🧰 code-reviewer: `self._seen.add(id)` races under concurrent deliveries; guard with the lock or use an atomic store.

**`security-reviewer` — native review · REQUEST_CHANGES**
> 🧰 pkit review · security-reviewer — CHANGES_REQUESTED
>
> **Blocking (2):**
> - Signature compared with `==` — timing-attack vector; use `hmac.compare_digest` (`verify.py:19`).
> - Webhook secret written to the debug log (`verify.py:24`).
>
> *Advisory (1):*
> - No rate-limit / replay window on the endpoint — consider a nonce + timestamp.
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>
>
> ↳ inline `verify.py:19` — 🧰 security-reviewer: **timing attack.** `sig == expected` short-circuits; use `hmac.compare_digest(sig, expected)`.
> ↳ inline `verify.py:24` — 🧰 security-reviewer: **secret leak.** `log.debug(f"secret={secret}")` writes the shared secret to logs. Remove.

**`docs-reviewer` — native review · REQUEST_CHANGES**
> 🧰 pkit review · docs-reviewer — CHANGES_REQUESTED
>
> **Blocking (1):**
> - New public endpoint `/webhooks/deploy` and config key `WEBHOOK_SECRET` are undocumented (DEC-015 doc obligation for `webhook.py` → `docs/webhooks.md`).
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

*Gate after round 1: `code ✗ · security ✗ · docs ✗` — blocked.*

### Round 2 — author pushes a fix (HEAD `e4f5g6h`)

Verdicts re-run on the new HEAD (stale round-1 approvals wouldn't count anyway — freshness):

**`code-reviewer` · APPROVED**
> 🧰 pkit review · code-reviewer — APPROVED
>
> Both blocks resolved (400 on bad JSON; dedup now lock-guarded). ✓ The 3 advisories remain, non-blocking.
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

**`security-reviewer` · REQUEST_CHANGES** (partial fix — one block remains)
> 🧰 pkit review · security-reviewer — CHANGES_REQUESTED
>
> **Blocking (1):**
> - `compare_digest` — fixed ✓. But the secret is **still logged** — the `log.debug` moved to `config.py:12` rather than being removed (`config.py:12`).
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>
>
> ↳ inline `config.py:12` — 🧰 security-reviewer: same secret-leak, relocated. Drop the debug line entirely.

**`docs-reviewer` · APPROVED**
> 🧰 pkit review · docs-reviewer — APPROVED
>
> `docs/webhooks.md` added; endpoint + `WEBHOOK_SECRET` documented, matches behaviour. ✓
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

*Gate after round 2: `code ✓ · security ✗ · docs ✓` — still blocked on security.*

### Round 3 — resolution (two variants)

**Variant X — author removes the log (HEAD `i7j8k9l`):**
> 🧰 pkit review · security-reviewer — APPROVED
>
> Secret log removed. ✓ Advisory (rate-limit) stands.
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

`done-work` → **gate summary:**
> 🧰 pkit gate — merged #758 · code ✓ · security ✓ · docs ✓ · CI green
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

**Variant Y — operator judges the log finding a false alarm and overrides** (`done-work --bypass-reviewer security-reviewer --bypass-reason "…"`):
> 🧰 pkit override · security-reviewer — the `log.debug` is gated behind `if DEV and not PROD`; never runs in a deploy. Tracked to remove in #761.
>
> Reviewer state at override: **CHANGES_REQUESTED** (block: [comment](#)).
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

`done-work` → **gate summary:**
> 🧰 pkit gate — merged #758 · code ✓ · security ⤼ overridden · docs ✓ · CI green
>
> <sub>🧰 pkit · tree `1.149.0` · pm `0.54.0` · cli `1.149.0`</sub>

### What the complex case shows

- **Iteration reads cleanly** — each round is a fresh set of native reviews on the new HEAD; the thread tells the story (blocked → partial → resolved) at a glance.
- **Partial fixes are honest** — security stays `CHANGES_REQUESTED` with the *one* remaining block, not a fresh full list.
- **Blocking vs advisory holds up under volume** — 2 blocks + 3 advisories in one verdict stays scannable (blocking bulleted first, advisory italic below; blocks also inline on the line).
- **The gate summary is the payoff** — one line tells you exactly which perspectives passed, which was overridden, CI state — the honest at-a-glance verdict on a busy PR.
- **Volume check** — a 3-reviewer × 3-round PR = up to 9 verdict bodies + inline comments. GitHub collapses superseded reviews, and each body is compact (blocking list + footer), so the thread stays readable — but it argues for the **preview (#673)** on a colleague's PR and for keeping advisories terse.

## Open questions the mock surfaces

1. **Advisory findings** — inline (line-anchored) or in the summary body's *Advisory* section, or both? (Shown: blocking → inline + summary; advisory → summary section. Line-level advisories could also be inline.)
2. **Self-authored PRs** — the local path can't post native reviews on your own PR (self-approval block, #672) → degrade to comments. Does the panel then post 3 comment-verdicts + inline-as-comments? (Ties to the preview #673.)
3. **One review per perspective** vs a single combined review — shown as one-per-perspective (each is a distinct GitHub review object). Confirm.
