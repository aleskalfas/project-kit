---
authors:
  - Ales Kalfas <kalfas.ales@gmail.com>
started: 2026-05-29
---

# Capability harness config — propagating configured gh host + recommended permissions into the harness

## The question

When an adopter installs a capability that drives an AI harness (the project-management capability driving Claude Code), how does the capability contribute *harness-level* configuration — permission allowlists and environment variables — to the adopter, **including values derived from the adopter's own capability config** rather than shipped as literals?

Concretely, two pieces surfaced together:

1. **Recommended permission allowlist** (static, generic) — the broad-but-guarded set (`Bash(gh:*)`, `Bash(git:*)`, `Bash(pkit:*)`, plus `deny` guardrails for force-push / `rm -rf` / `sudo`) that lets an operator drive the pm workflow without a prompt per command.
2. **gh host → harness env** (derived, adopter-specific) — the configured `gh.host` from the pm capability's `project/config.yaml` needs to reach the harness so raw `gh` calls hit the right host without an `export GH_HOST=… &&` prefix on every command.

## What prompted this

Session 2026-05-29: every `gh` / `pkit` command the agent ran prompted for permission, despite the project's `.claude/settings.json` already carrying broad `Bash(gh:*)` / `Bash(git:*)` / `Bash(pkit:*)` allow rules. Root cause: the agent prefixed commands with `export GH_HOST=github.com && …`. Claude Code splits compound commands on `&&`/`;`/`|` and requires *every* segment to match an allow rule; the `export GH_HOST=…` segment matched nothing → prompt. The allowlist was wide enough; the **command construction** defeated it, and the construction existed only because the host wasn't in the harness env.

So the friction is a symptom of config not propagating from the capability to the harness. Fixing propagation removes the need for the prefix, which removes the prompts.

## Forces

- **Adopter-neutrality (COR-014).** `github.com` is this operator's host. Nothing shipped may hardcode it. A `github.com` adopter must get correct behaviour with zero host config (gh's default already works) — ideally *nothing* injected for them.
- **No-shared-files invariant (COR-013 / COR-017).** The capability cannot edit the adopter's `settings.json` directly; the claude-code adapter owns that file via its merge primitive. Capability contributions flow through the adapter's overlay/merge path.
- **Single source of truth.** `gh.host` already lives in the pm capability's `project/config.yaml` (validated by `pre-check`). The pkit scripts already consume it correctly: `gh_run` (#209) injects `--hostname` from config on every script-mediated `gh` call. The gap is only the *raw* `gh` the agent/session runs outside pkit.
- **Existing carrier exists.** DEC-030 (#191) gave the pm capability a way to contribute top-level `settings.json` keys through the claude-code adapter (`merge-settings.sh`, broadened in #190/#205 to preserve top-level keys — that's how `"agent": "project-manager"` lands). But DEC-030 overlays are **static file merges** — they have no notion of a value computed from adopter config.

## What is already known / accepted

- COR-013 / COR-017 — no-shared-files; capability contribution boundaries.
- COR-026 + DEC-029 — pm agent placement and shape (the agent is the primary consumer of the harness config).
- DEC-030 — capability-contributed adapter overlays + the enable/disable-default-agent toggle. The precedent and likely carrier.
- #209 — `gh_run` injects `--hostname` from config; pkit-mediated gh access is already host-correct.
- #190 / #205 — `merge-settings.sh` preserves top-level keys (so an `env` block or a `permissions` block can be merged in).

## Candidate alternatives

### A — Extend overlays to support derived values
Teach the DEC-030 overlay mechanism to template a value from capability config at enable/sync time. Overlay declares something like "set `env.GH_HOST` from `gh.host`, omit if unset/default"; the adapter resolves it during merge.
- **Pro:** one mechanism handles both static (permissions) and derived (host) contributions; conceptually clean.
- **Con:** introduces templating/derivation into what was a static-merge contract — a real surface increase on the overlay mechanism. Needs a DEC.

### B — Keep overlays static; add a "sync env from gh config" deploy step
Leave overlays static for the permissions block. Add a small, dedicated adapter step that reads `gh.host` and writes `env.GH_HOST` into the merged settings (only when non-default).
- **Pro:** overlays stay simple; the derivation is one narrow, testable step.
- **Con:** two mechanisms doing similar-looking things (static overlay + bespoke env-sync); risk of drift; the env-sync step is single-purpose and may not generalise to the next derived value.

### C — Sidestep env entirely with a `pkit gh` passthrough
Add a thin `pkit gh …` command that forwards to `gh` with `--hostname` injected from config (reusing `gh_run`). Train the agent to prefer `pkit gh` over raw `gh`. Then no env var, no overlay derivation — the host always comes from config at the one chokepoint.
- **Pro:** single source of truth enforced structurally; no harness-env coupling; reuses `gh_run`; works for every harness, not just Claude Code.
- **Con:** new CLI surface; requires retraining the agent (and humans) to avoid raw `gh`; the recommended-permission allowlist would then target `pkit gh:*` (already covered by `pkit:*`) — but humans still type raw `gh` by habit, so the env problem doesn't fully disappear for interactive use.

### Hybrid worth considering
C (for the agent's structural correctness — everything through pkit) **plus** A or B (so interactive raw `gh` by a human also gets the host). C alone fixes the agent; it doesn't fix a human typing `gh issue view` in the same shell. The env propagation is what covers the human case.

## Open questions

- Does the recommended-permission allowlist belong to the **capability** (pm knows what verbs it needs) or the **adapter** (Claude Code knows the permission syntax)? Likely a capability-authored overlay *expressed in* the adapter's permission vocabulary — which is exactly what DEC-030 overlays are. Confirm the overlay can carry a `permissions` block as cleanly as it carries `agent`.
- Should injected env be **opt-in** (like the default-agent toggle) or automatic on install? The default-agent precedent (DEC-030) is opt-in for sovereignty reasons. Host propagation is lower-stakes (it only sets a host the adopter already configured) — automatic-when-configured may be fine.
- Is `GH_HOST` the right lever, or `gh`'s own per-repo host resolution (git remote)? On enterprise, the git remote *is* the enterprise host, yet raw `gh api` still defaulted to github.com this session — so the git-remote path is not reliable for `gh api`. `GH_HOST` (or `--hostname`) is needed.
- How does this generalise beyond gh host? If other capabilities will want to propagate config-derived harness env, alternative A's generality starts to pay off.

## Decant target (provisional)

Likely **one DEC** in the project-management (or a cross-cutting core) namespace that picks A/B/C (or the hybrid) and defines how capability config propagates to harness config, **plus** an implementation arc filed under Milestone #7. The static recommended-permissions overlay (piece 1) is low-risk and largely independent — being filed as its own Task now, ahead of resolving the derived-host design here.

## Third input — agent-driven permission needs (`pkit agents` management)

A second framing arrived the same session: should each kit agent carry its own "narrow but wide enough" permission overlay, managed by a `pkit agents` command surface (apply / validate / list installed agents), with general + per-folder scoping? Reviewed by `critic` + `architect`. Synthesis (both converged):

**This is the same seam, third entry point.** Capability-driven (the recommended allowlist above) and agent-driven (an agent's declared needs) both terminate at `settings.json.permissions` through the adapter. **One mechanism, one DEC — not parallel.** Fold here.

**Hard substrate limit (reframes the whole idea).** Claude Code scopes permissions per-agent only at the *tool* level (frontmatter `tools`/`disallowedTools`/`permissionMode`). Command-pattern rules (`Bash(gh:*)`) are *session-wide* — never per-agent. Consequences:

- Split the abstraction: *tool needs* → frontmatter (native per-agent, already COR-013 §2); *command needs* → `settings.json` (session-wide, a **project-level union** across installed agents). Do **not** fuse them into one "per-agent permission profile" — that implies an agent-granularity the harness can't honour.
- Per-agent command-level "least privilege" is unachievable in-session: multi-agent → union; single-agent → the agent's needs *are* the session's, so the profile buys nothing. The real session-wide lever is the **deny baseline** (already shipped in `core/settings.json`).
- `validate` is a **project-level** invariant ("union of installed agents' declared needs ⊆ allow; no allow entry no agent declared"), not per-agent. And it must **not** be naive set-containment: the prompts this session came from command *construction* (`export … && …` splitting on `&&`), not missing allows — a subset check would give false "won't-prompt" assurance (the exact failure mode that started this). The collision-free, unambiguously-useful validate piece is **JSON-schema-validating settings.json** against Claude Code's published schema.
- Per-folder = native per-project `.claude/settings.json`. Multi-root *single-session differential* trust is **not expressible** (`--add-dir` grants file access, not config; rules are session-global). True per-agent/per-dir runtime filtering only via **PreToolUse hooks** (frontmatter-declarable) — the spine if hard enforcement is the actual goal.

**Collision with accepted DEC-030.** DEC-030 reserves the `permissions` key against overlay contribution and names "a future DEC" to relax it. Writing permissions from agent/capability declarations IS that future DEC; it **must explicitly amend DEC-030**'s reserved-key rule *and* its `disable` strip-logic (line 74 carve-out breaks once overlays may carry permissions). This is the one accepted record the eventual DEC modifies — surface at decant.

**Placement (both reviewers agree):** mechanism (declaration vocabulary + adapter translation + `pkit agents` verbs) → **core** (generalises COR-013's tool-translation to command-needs; note: COR-013 §6 commits the `refs`/`hooks` CLI families — only `pkit agents matrix` exists, as a *future* area-README command, not a committed `pkit agents` verb group). Content (`gh`/`git` grants) → capability/project, never core (COR-014).

**Two open forks blocking decant:**
1. **New field vs derive.** Express command-needs as a new harness-neutral frontmatter field, or *derive* them from the `needs:`/`provides:` hook metadata agents already declare (avoids a new field + keeps the reference graph single-source). New field = COR-013 amendment; derivation = none. Resolve before the DEC.
2. **DEC-030 amendment precedence.** Does a capability/agent-contributed allow-set merge before or after `merge-settings.sh` step 1's skill-grant computation, and how does `disable` strip permission keys it now legitimately contributed?

**Smallest-version option (critic's CA-1/CA-3):** ship the static recommended allowlist (already filed as #226) + document the native tool-level gating + the schema-validate check; drop the per-agent command-profile abstraction and the `apply`-writes-permissions machinery entirely. Delivers ~80% (it's mostly docs + the existing baseline) with no DEC-030 collision. Weigh this against the full mechanism before committing.

## Related

- Sibling deferred scratchpads `2026-05-22-modular-install-surface.md` and `2026-05-26-parallelization-primitive.md` (parked).
- Session handoff `2026-05-28-session-handoff-cli-gap-follow-up.md` (the CLI-gap arc; this note is a new thread off the same dogfood session).
