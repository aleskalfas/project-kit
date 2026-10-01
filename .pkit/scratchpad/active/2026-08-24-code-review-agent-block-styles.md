---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-24
---

# Code review — per-agent block style (chosen)

The per-agent block inside the aggregated review. One block per perspective; the aggregate header (`## 🧰 pkit review — <emoji> VERDICT · code … · security … · docs …`) + the `<sub>` footer wrap the set. Rendered examples live in the per-round files (`2026-08-24-code-review-round-{1,2,3}.md`).

**Legend:** ⛔️ CHANGES_REQUESTED · ✅ APPROVED. **`🧰`** = the pkit tool (frame); **`🤖`** = an agent within it.

## Template

```
### 🤖 `{{agent}}` → {{⛔️|✅}} {{VERDICT}}
- *Blocking:*
  - {{finding}} (`{{file}}:{{line}}`)
- *Advisory:*
  - {{finding}}
```

- Agent name is **inline code**, prefixed with **🤖** (variant A — the icon signals "agent"; compact across stacked blocks).
- Verdict is `→ <emoji> VERDICT`.
- `*Blocking:*` / `*Advisory:*` are nested list groups; each finding a sub-bullet with its `file:line`.
- Omit a group that's empty. An **APPROVED with no findings** collapses to just the headline.

## Rendered — CHANGES_REQUESTED

### 🤖 `code-reviewer` → ⛔️ CHANGES_REQUESTED
- *Blocking:*
  - Unhandled `json.JSONDecodeError` on a malformed body → uncaught 500 (`webhook.py:31`)
  - Dedup set mutated without a lock — concurrent deliveries can double-process (`webhook.py:58`)
- *Advisory:*
  - `TIMEOUT = 30` — magic constant; name it
  - `handle()` is 90 lines — extract verify + dispatch
  - no malformed-body test case

## Rendered — APPROVED (advisory only)

### 🤖 `code-reviewer` → ✅ APPROVED
- *Advisory:*
  - `TIMEOUT = 30` — magic constant; name it

## Rendered — APPROVED (clean, no findings)

### 🤖 `docs-reviewer` → ✅ APPROVED
