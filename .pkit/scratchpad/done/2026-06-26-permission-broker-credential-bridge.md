---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-26
retired: 2026-06-27
produced:
  - '#340'
  - '#312'
---

# Permission broker — credential bridge for the OS sandbox

Design exploration. Retires by producing an ADR (project-kit's own architecture) + an EPIC. Not built yet.

## Problem

On macOS the OS sandbox (Claude Code Seatbelt) and the kit's GitHub access conflict. We want **both**: the sandbox on (OS confinement) **and** a working `gh`/git toolchain — without handing the GitHub token to the sandboxed agent.

What we proved empirically this session (CC 2.1.193):

- **`uv`/`pkit` run fine inside the sandbox now** — the old SCDynamicStore brick is gone (`pkit schemas validate` passes sandboxed).
- **`gh` is the sole blocker** — it fails on `~/.config/gh: operation not permitted` (the `denyRead` floor).
- **The token is in the macOS Keychain, not in `~/.config/gh`** (`gh auth status` → `(keyring)`; `hosts.yml` has no token). So the `denyRead` of that dir protects nothing secret while breaking `gh`.
- **The harness's native "controlled hole" (`excludedCommands`) is non-functional** in this CC — it honors `sandbox.enabled` from `settings.local.json` but ignores `excludedCommands` from the same file.
- Operator preference: **move off the Keychain to 1Password** for the GitHub credential.

So the native door (`excludedCommands`) is dead, and we want a *narrow, controlled* hole rather than removing the sandbox.

## Decision direction (operator-chosen)

A **credential broker**: a process **outside** the sandbox that holds the GitHub token (from 1Password) and serves vetted gh work to the sandboxed agent over a **single Unix socket** allowed through the sandbox. The agent never sees the token and can only reach that one socket.

### Why a broker over the alternatives

- `excludedCommands` — the intended mechanism; non-functional here.
- `GH_TOKEN` in the session env (from `op` at launch) — works everywhere, but the token is **readable by the sandboxed agent** (env vars). Rejected: defeats the "agent never sees the token" goal.
- Un-`denyRead` `~/.config/gh` + Keychain — the token's not in that dir, but it stays in the Keychain (operator wants off the Keychain), and Keychain access under Seatbelt is unverified.
- **Broker** — the only option that is *both* 1Password-sourced *and* keeps the token unreachable by the agent.

## The clean enabler

All pkit gh calls already funnel through **one seam: `_lib/gh.gh_run`**. So the in-sandbox client side is a single routing point — "if a broker socket is configured, send the call there; else run `gh` directly." No scattered changes.

## The shaping fork — thin vs fat broker

- **Thin broker (v1, chosen).** The broker forwards gh calls and holds the token. It delivers **credential isolation** (token never in the sandbox). **Operation-narrowing** (agent can't run *arbitrary* gh) is left to the **existing permission layer** (the raw-gh deny + read-redirect, `issue-tracker-write` / `issue-tracker-read-raw`). Clean separation: *broker isolates the credential, the permission layer narrows the operations.*
- **Fat broker (future hardening).** The broker re-validates each operation itself, so it holds even if the permission layer is bypassed (`bash -c`). Belt-and-suspenders, but duplicates the permission layer; deferred.

## Open design questions (for `critic` / `architect`)

- **Placement.** The broker is a *credential-bridge for OS confinement* — a permissions/backbone concern, not project-management (the same kind of home question COR-026 raised for the analyst agent). Where does it live: backbone permissions surface? A new component? It must be harness-neutral in concept, with only the socket-allow config being Claude-Code-specific.
- **Lifecycle / startup.** Who starts it, and when? It needs `op` (1Password) at startup to fetch the token — interactive (biometric) or a service-account token. Candidates: a `pkit` command (`pkit permissions gh-broker start`), a launchd/login agent, or an `op run`-wrapped launcher. Must be up before the sandboxed agent needs gh, and recover across restarts.
- **Protocol.** Thin = "forward this gh argv + return stdout/stderr/exit". Keep it minimal and framed so it can't become an arbitrary-exec channel beyond what gh itself already is. Define the request/response shape and error/timeout semantics.
- **Socket security.** Path + perms (0600, user-only); the single `allowUnixSockets` entry; what stops another local process from using it (single-user assumption stated).
- **Token sourcing from 1Password.** `op read`/`op run` at broker startup; refresh on rotation; never written to disk.
- **Degradation.** When no broker socket is configured (the common, non-sandboxed case), `_lib/gh.gh_run` runs `gh` directly — unchanged behavior. The broker is opt-in for the sandbox-on posture.
- **`setup autonomy` interplay.** Once the broker exists, `setup autonomy` on macOS could enable the sandbox *and* point at the broker — turning #336 from "warn/skip" into "wire the broker". Until then, #336's warn/skip stands.

## Relationship to existing issues

- **#312** (macOS exclusion bricks pkit) — reframe: the premise ("exclude pkit/uv via `excludedCommands`") is disproven (excludedCommands non-functional; uv no longer bricks). The real resolution is this broker. This note + the EPIC supersede that framing.
- **#336** (`setup autonomy` must not enable a macOS-incompatible sandbox) — the broker is the eventual "make it compatible" answer; #336's warn/skip is the interim.
- **#335** (EPIC #315 before/after proof) — independent; runs sandbox-off until the broker lands.

## Not now

Fat broker; any non-gh credential bridging. Note: git-over-HTTPS push also needs the token — with the broker, HTTPS push via gh-credential-helper would also route through the broker, OR switch the remote to SSH so the 1Password SSH agent handles push (already sandbox-allowed).

## Verdict (2026-06-27): REJECTED on review — do not build

`critic` + `architect` both rejected the broker; this note retires here.

**Decisive finding (critic): the thin broker is net-negative.** The socket is allowlisted → prompt-free (no hook fires on socket traffic); the thin broker forwards *arbitrary* `gh` argv; the permission layer is a speed-bump (porous to `bash -c`). Compose those and a compromised agent gets a **prompt-free, permission-layer-bypassing, arbitrary-`gh` channel with the live token behind it** — it can run `gh auth token` (print the token, defeating the entire goal) or `gh api -X DELETE …`. Hiding the token's *value* is pointless when its *power* is reachable; for an autonomous agent the power IS the asset. So v1 is *weaker* than today (where raw `gh` is denied). Only a *fat* re-validating broker would be defensible — and that is re-implementing the permission layer as a real fail-closed boundary, a different and larger decision.

**Architect:** the broker would *supersede* ADR-030 (foundational, accepted 2026-06-24; needs operator sign-off), and its genuine win would be credential *provenance*, **not** egress confinement (which the thin broker does not deliver).

**Redirect.** The real defense is **least-privilege power-scoping, not credential-hiding** → EPIC **#340** (scoped GitHub token from 1Password). The macOS sandbox blockers (`excludedCommands` non-functional; `gh` `denyRead`) are tracked in the reframed EPIC **#312**. Interim posture: **sandbox OFF on macOS**.

Retired as *done* — produced: #340 + the #312 reframe.
