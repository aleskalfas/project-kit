---
variant: specialized
---

# Command-line interface

project-kit ships a CLI that adopting projects use to install the methodology, pull updates, manage capabilities, and check state. The binary's name is **`pkit`** (per PRJ-001). The CLI is the surface through which project-kit's mechanisms (propagation, extension, suspension) and delivery operations (seed, merge) are exercised against your project — see `.pkit/decisions/README.md` and the COR records in `.pkit/decisions/core/` for the underlying contracts.

The design rules governing the CLI's shape — why these commands exist and not others, why some verbs stay separate — are recorded in `.pkit/decisions/core/COR-004-cli-surface.md`. This document is the spec: what each command does, which flags it accepts, what guarantees it provides.

## Implementation status

The CLI is implemented in Python (per PRJ-003), with `.pkit/cli/pkit` as a thin proxy that exec's the Python runtime via `uv` and bypasses to the adapter's shell scripts for `deploy-skills` / `merge-settings` (which are shell to the bone — primitives the adapter ships, not surface commands).

The full COR-004 surface is implemented: `init`, `sync`, `merge`, `upgrade`, `capabilities install / register / uninstall / upgrade / list` (per COR-017 + COR-031), `status`, `validate`, `version`, `version bump`, `release plan / apply / merge / publish-notes / check / lint / check-shareable` (per PRJ-002 + COR-041), `new decision`, the authoring commands (`area`, `adapter`, `capability`, `agent`, `storyboard`, `schema`, `migration`), and the scratchpad commands (`new scratchpad`, `scratchpad done`, `scratchpad drop`, `scratchpad reported`, `scratchpad list`) per COR-012 + COR-043. Each authoring command ships paired with its skill under `.pkit/skills/core/<name>-author/` per COR-005's "Skill / command pairing". (The `bundle` command family was retired in COR-027 — capabilities subsumed the bundle role.)

## Installing pkit on PATH

**Recommended (per PRJ-004):** install pkit globally via `uv tool install`:

```
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git
```

After this, `pkit` is on PATH; the binary works against any project-kit-adopting project — the runtime resolves the current project's root from CWD at invocation time (via `git rev-parse --show-toplevel`, with a structurally-validated CWD-walk fallback that skips a broken/vestigial `.git`). Re-installing the kit into more adopter projects does **not** require additional installs of pkit. The methodology content `init` / `sync` / `upgrade` propagate is **bundled in the wheel** (version-locked to the binary), so these commands work from the installed binary without a source checkout (per [ADR-033](../../docs/architecture/decisions/ADR-033-official-install-bundles-content.md)); a checkout, when present, takes precedence so contributors' source edits stay live.

**One install for everyone — no separate router.** The installed binary is CWD- and pin-aware (per [ADR-039](../../docs/architecture/decisions/ADR-039-pkit-entry-point-router.md)): on every invocation it cheaply picks a route *before* loading the CLI. Inside a project-kit source checkout it runs that checkout's working tree; in an adopter that pins a version (`.pkit/version-pin`, per [ADR-049](../../docs/architecture/decisions/ADR-049-per-project-version-pin.md)) different from the running binary it runs that pinned version under `uvx …@<pin>` (an unresolvable pin degrades loudly to running self, never a hard fail); otherwise it runs in-process. Adopters and contributors therefore share this **single** install — there is no separate shim to put on PATH. Escape hatches: `PKIT_NO_ROUTE=1` forces in-process execution; `PKIT_ROUTED=1` is the internal loop guard the re-exec'd process inherits. On the source-checkout route the router also sets `PKIT_CLI_VERSION` to the checkout's `.pkit/VERSION` so version-provenance reports `cli == tree` (in a checkout the running code *is* the tree, but package metadata can lag a `.pkit/VERSION`-only bump); an explicit `PKIT_CLI_VERSION` in the environment wins, and the other routes leave it unset so a genuine installed-CLI-vs-tree drift still shows.

Pin to a specific kit version:

```
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git@v0.10.0
```

**Alternative (project-kit contributor convenience):** symlink the source-tree dispatcher onto PATH so changes you make to the kit's source are picked up without re-installing:

```
ln -s /path/to/project-kit/.pkit/cli/pkit ~/.local/bin/pkit
```

This is useful while developing the kit itself. The symlink target is the thin proxy; it routes to Python via `uv run --project /path/to/project-kit` so the source tree's `pyproject.toml` resolves the package version.

**Requirements either way:** Python 3.11+ and `uv` (per PRJ-003). Install `uv`:

```
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
```

## Surface

| Command | Operation | Mutates? | Idempotent? |
|---|---|---|---|
| `init` | first install: announce target + confirm off-CWD, then propagation + seed + merge (`--here` / `--yes` / `--root <path>` / `--dry-run`) | yes | no — refuses re-run (points you to `pkit sync`) |
| `sync` | re-run propagation | yes | yes |
| `merge [<target>...]` | re-run merge for one or all targets | yes | yes |
| `upgrade` | version-aware migrations + sync; **pins the project by default** at the version it upgrades to (ADR-049) — `--no-pin` opts out (keep following the installed global tool). In an already-pinned project it auto-advances the `.pkit/version-pin` directive to the latest release (reconcile forward via `uvx`, flip the pin last; no `uv tool install`); offline-safe; self-host is never pinned | yes | yes |
| `pin [<version>]` | write the `.pkit/version-pin` directive (per ADR-049): no argument freezes at the current content version (`backbone_version`); `<version>` (a version number only, leading `v` stripped) freezes (equal), reconciles content forward then flips the pin last (newer), or refuses (older — forward-only migrations). Requires the manifest; refuses branch/sha/pre-release pins. Project-owned; never kit-synced | yes | no — overwrites an existing pin |
| `unpin` | remove the `.pkit/version-pin` directive (per ADR-049); the project reverts to floating on the installed binary | yes | yes — no-op when absent |
| `visibility` | control pkit's git footprint (per ADR-009). No subcommand = status | no | yes (read-only) |
| `visibility shared` / `visibility private` | `private` hides the whole footprint via the per-clone `.git/info/exclude` (no committed `.gitignore` is ever written) + a confirm-gated untrack; `shared` (default) keeps pkit committed. `--dry-run` previews | yes | yes — idempotent |
| `visibility untrack [--dry-run]` | remove already-tracked pkit footprint files from the git index (`git rm --cached`, working copies preserved). Footprint-only, confirm-gated; refuses mid-merge/rebase or on staged footprint changes. Its own subcommand so the git-index-mutating gesture stays explicit (per ADR-009) | yes | yes — no-op when nothing tracked |
| `capabilities install <name>` | install a *kit-shipped* capability: copy the subtree from kit source into the adopter, register it, deploy (per COR-017) | yes | already-installed reports, no re-run |
| `capabilities register <name>` | register + activate an *in-repo (incubated)* capability authored at `.pkit/capabilities/<name>/` — registers in place (no copy), records origin `incubated-in-repo`, then runs the same deploy primitives + dependency gating as install (per COR-031). Skips the "exists in kit source" pre-flight; keeps backbone-version + collision + dependency pre-flights. Idempotent on an already-registered capability: a clean no-op when it is already `incubated-in-repo`, or an *adopt-in-place* origin upgrade (set origin to `incubated-in-repo` on the existing entry, no re-copy/re-deploy) when it was registered `kit-shipped` — including the origin-unset default a manual registration leaves | yes | no-op when already incubated; adopts a kit-shipped/origin-unset entry in place |
| `capabilities uninstall <name>` | remove an installed capability | yes | yes |
| `capabilities list` | list capabilities known to this project — kit-source-available plus anything installed — with an `origin` column marking each installed one `kit-shipped` or `incubated` (per COR-031) | no | yes (read-only) |
| `new area <name>` | scaffold a new area (per COR-011) | yes | no — refuses if area already exists |
| `new adapter <name>` | scaffold a new adapter (per COR-005) | yes | no — refuses if adapter already exists |
| `new capability <name>` | scaffold a new capability (per COR-017) | yes | no — refuses if capability already exists |
| `new migration [...]` | scaffold a migration script in the right `<major>.<minor>.0/` directory | yes | no — emits a fresh, numbered file each call |
| `new decision <namespace> <slug>` | scaffold a new decision record stub (frontmatter + four sections + next number in namespace) | yes | no — refuses if a record with that slug already exists |
| `new scratchpad <slug>` | stamp a new active-state scratchpad note (per COR-012) | yes | no — refuses if the slug is already in use across any state |
| `scratchpad done <slug> [--produced <ref>...]` | move a note from `active/` (or `reported/`, removing that lazy directory when it empties) to `done/`, append `retired`/`produced` to frontmatter | yes | no — refuses if no active or reported note matches |
| `scratchpad drop <slug>` | move a note from `active/` (or `reported/`) to `dropped/`, append `retired` to frontmatter | yes | no — refuses if no active or reported note matches |
| `scratchpad reported <slug> <ref>...` | manually stamp an active note as sent through the report channel: move to lazily-created `reported/`, append `reported`/`reported_to`/`reported_hash` frontmatter (per COR-043; the automatic stamp happens on a successful `report` post — this gesture covers URL-first posts and retroactive marking). Refs are `owner/repo#N` or GitHub issue URLs (normalised) | yes | yes — appends refs to an already-reported note; duplicate refs are a no-op |
| `scratchpad list` | list notes by state; reported notes resolve their refs' upstream state **live** via `gh` (pull-only, never stored; offline degrades to `state unknown`), flag divergence from the stamped hash (`modified since reported`), and print a retire prompt when every ref is closed — never auto-retiring (per COR-043) | no | yes (read-only) |
| `status` | show how project-kit is wired in this project (paths, installed backbone version vs source, adapter, deployed skills, capabilities, decision counts) | no | yes (read-only) |
| `validate` | check project state against invariants | no | yes (read-only) |
| `schemas validate [<path>]` | validate capability schema YAMLs against their JSON Schema companions + cross-file refs | no | yes (read-only) |
| `decisions validate` | detect duplicate decision ids within an id-space (core / project / ADR / per-capability DEC) + id-vs-filename mismatches; exit non-zero on any | no | yes (read-only) |
| `data validate <path>` | validate adopter data files against their bound capability schemas (per COR-023); resolves binding field-first via `pkit_schema:`, then via per-schema `binds_to:` fallback | no | yes (read-only) |
| `agents` | report which kit-shipped agents will deploy vs. be skipped — and why, per COR-013. An agent is skipped only when it references an overlay category `.pkit/agents/project/overlay.yaml` doesn't define through a **hard** channel (`owns`/`needs`/`answers`/`reads.paths`/`reads.records`); a category referenced *only* via `reads.patterns` is an **optional** read (ADR-052) whose absence never skips — the agent deploys without it, and the undefined optional categories are surfaced in their own footer state (`Optional \| N categor(ies) undefined \| agents deploy without them`) rather than as a skip cause. Deployment itself happens in `sync`; this is the diagnostic | no | yes (read-only) |
| `agents reconcile [--write]` | surface referenced-but-undefined overlay categories into `overlay.yaml` as commented stubs (explicit; `sync` never mutates the seeded overlay). Dry-run by default | yes (with `--write`) | yes — idempotent (skips already-present categories) |
| `permissions explain [<agent>]` | render the per-agent permission mental model — grants, scopes, effects (per COR-028) | no | yes (read-only) |
| `permissions diff [<agent>]` | reconcile the model against live `.claude/settings.json`: flag live rules no granted privilege justifies + dimensions the harness can't natively enforce | no | yes (read-only) |
| `permissions catalog` | list the privilege catalog (baseline + extensions) | no | yes (read-only) |
| `permissions overview` | role-grouped catalog view — guardrails vs enablers, provenance, granted-to, live-enforcement status | no | yes (read-only) |
| `permissions grant <subject> <privilege> [--scope <glob>...] [--deny]` | add/update a grant in the project model, validated against the catalog | yes | no — idempotent (updates a matching grant) |
| `permissions scaffold <cap>` | stamp a capability's `permissions/` fragment skeleton — `privilege-catalog.yaml` (definition, ADR-021) + `grants.yaml` (deny policy, ADR-016) — with correct shapes + inline footgun guidance (fragment keys are BARE; a grant references a fragment privilege with the SCOPED `[privilege-catalog:<cap>:<name>]` token; `guardrail: true` forbidden). Standalone (serves existing capabilities, not a `new capability` flag). Refuses an unknown capability; refuses to clobber an existing fragment file | yes | no — no-clobber (leaves an authored fragment untouched) |
| `permissions revoke <subject> <privilege>` | remove a grant from the project model | yes | no — no-ops when absent |
| `permissions mode [additive\|managed]` | show (no arg) or set the ownership mode | yes (on set) | no |
| `permissions enable` | turn on live enforcement: register the PreToolUse hook (opt-in) + ensure native guardrail denies (the double-lock) | yes | no — idempotent |
| `permissions disable` | turn off live enforcement: strip the PreToolUse hook registration (guardrail denies stay) | yes | no — idempotent |
| `permissions apply` | additively realize the model into `.claude/settings.json` — union the projected session-wide allow rules + ensure guardrail denies — and print the out-of-harness gap report. Additive only (managed-mode wholesale regeneration is separate) | yes | no — additive, idempotent (set-union) |
| `permissions setup` | list the permissions domain's setup goals (per ADR-007) | no | yes (read-only) |
| `permissions setup autonomy [--profile <name>] [--remove-overrides]` | goal-oriented setup (first ADR-007 instance): stand up autonomous agents by composing `profile activate` + `enable` + `sandbox enable --strict` (strict is the autonomy posture's default per ADR-028 — it seals the unsandboxed escape by writing `allowUnsandboxedCommands: false`, so the per-command `dangerouslyDisableSandbox` flag is inert and an agent can't silently disable the box; reversible by `sandbox enable` without `--strict` or `setup autonomy down`), auto-resolving the SSH-agent socket (`$SSH_AUTH_SOCK`, per ADR-010), stop honestly at the session-restart boundary, and on re-run verify via the probe suite — the goal is declared reached only when the proof passes (decision layer + credential floor). **Detects per-machine overlay attributes that override the intended posture** (#399): on each run it reads the gitignored `.claude/settings.local.json` (never the committed baseline) for sandbox keys that defeat the **platform-correct** intended posture — `enabled` conflicting with the intended state (on macOS the intended posture is sandbox-OFF per #336, so `enabled: false` is *not* flagged there but `enabled: true` is; on a viable platform `enabled: false` *is* an override), a local `allowUnsandboxedCommands: true` un-sealing the strict seal, and inert **cruft** (a leftover `excludedCommands` list while the box is off — harmless, surfaced as tidy-up). It **warns loudly** (names each attribute, current-vs-intended, and how it defeats the posture — distinguishing genuine OVERRIDE "remove to restore autonomy" from inert CRUFT "remove to tidy"), then **offers to remove**, **consent-gated**: removal happens only on an interactive confirmation or with `--remove-overrides`, and is **never** covered by a blanket `--yes` (the trust-gesture exemption — removing the operator's local config is destructive). Removal drops the **whole `settings.local.json`** when it holds only overriding attributes, else strips **only** those attributes leaving other local config byte-faithful; it edits ONLY the gitignored per-machine file and reports what it removed. (This is distinct from #313's *auto-enforced* `autoAllowBashIfSandboxed`/seal, which the confinement step re-asserts loudly and which therefore reconciles before removal runs — the two compose.) **Auto-applies the one platform-mandatory, necessity-verified required exclusion** (per ADR-027): on macOS with a uv repo marker and an installed `uv` below the known-fixed release (the SystemConfiguration Seatbelt panic, ADR-014, is present in every release until a fix ships — so while no fixed release is known, every readable `uv` version qualifies; the gate is the fixed release, never a known-bad ceiling), it excludes the command `uv` through the real `sandbox exclude` primitive under a distinct `_required` provenance tag — loud (the UNCONFINED banner), in its own setup block, reported by `sandbox status` as auto-applied, written only to the per-machine live settings file (`.claude/settings.json`); in a conventional adopter layout that file is per-machine, but in a repo that tracks it the operator must keep the auto-applied exclusion uncommitted. (Excluding the command `uv` covers `pkit` only via `uv run pkit` — head token `uv`; a directly-installed `pkit` console-script entry point — head token `pkit` — is not covered.) A fixed `uv` self-disables it. Optional widenings stay in the **NEXT** block of explicit gestures it detects but won't run for you — `gh` exclusion (widening) and commit-signing socket (`accommodate --socket`). **Self-heals**: a later run removes a previously auto-applied `_required` exclusion once the version floor shows it's no longer required (uv upgraded past a fix / on Linux), never touching an operator's `_manual` carve-out. Stepwise, resumable; no dangerous-flag pass-through | yes | no — resumable + idempotent (live system is the checkpoint) |
| `permissions setup autonomy down` | tear the goal's live switches down (hook + sandbox), **reverse the auto-applied `_required` exclusion** (setup applied it, so teardown removes it and reports it — operator `_manual` carve-outs are left as reported residual), and loudly report residual state (profile still active in the model, unenforced; operator sandbox keys left) | yes | no — idempotent |
| `permissions probe [--subject <s>] [--live]` | probe-by-probe proof that the current model rejects/allows what it declares: drives the live hook's entry point (`hook_decide`) over curated concrete requests and checks each verdict against the declared contract (REJECTED / ALLOWED / NOT COVERED → ✓ works / ✗ BROKEN); checks the native double-lock denies; `--live` adds honest reachability probes of the sandbox credential denyRead floor (never certifies a pass it can't prove). Non-zero exit on any broken probe (CI-able) | no | yes (read-only; `--live` performs open-attempts, reads no content) |
| `permissions diagnose` | the permission-prompt diagnostic loop (per PRJ-006), opt-in + **recommend-only**: capture deferred (prompted) decisions, classify + rank them, and report remediations it RECOMMENDS (it applies nothing). No subcommand = `status` | no | yes (read-only) |
| `permissions diagnose on [--ttl <s>] [--no-redact]` | arm a bounded diagnostic session: write a TTL armed marker so it auto-expires (can't stay silently on). While armed, the PreToolUse hook appends each **deferred** decision to a local, git-ignored, size-capped (drop-oldest) log; the command tail is redacted by default (`--no-redact` logs full commands). Capture lives in the claude-code adapter hook, runs *after* the decision and only on the deferred verdict, and is fail-safe-wrapped — it can never change a decision or break fail-open | yes (writes the local marker) | yes — idempotent (re-arm refreshes the window) |
| `permissions diagnose off` | disarm: remove the armed marker (the hook stops capturing). The captured log is left in place | yes | yes — idempotent |
| `permissions diagnose status` | show armed / expired / off state + captured-log size | no | yes (read-only) |
| `permissions diagnose report` | print the classified, frequency-ranked, **recommend-only** report over the captured log: groups by command shape (interpreter / shell-shape / egress / allowlist-gap — taxonomy in code, not the record), ranks by frequency within action bands (recommend / judgement / document), and emits a recommended remediation per group. Applies **nothing** (auto-fix is deferred; a new catalog privilege is never auto-fixable). The captured signal is a SUPERSET of real prompts (the hook sees its own deferral, not whether the harness prompted), so counts are stated as **coverage**, not a predicted prompt decrement | no | yes (read-only) |
| `permissions sandbox` | status of the OS-sandbox confinement (per ADR-004): enabled, auto-allow, fail mode, fail-over, credential denyRead floor | no | yes (read-only) |
| `permissions sandbox enable [--strict] [--dangerously-allow-unconfined]` | turn on the OS sandbox (Seatbelt / bubblewrap) with prompt-free sandboxed Bash, always fail-closed (`failIfUnavailable: true`) + a credential `denyRead` floor; additive over operator sandbox keys. **On macOS the OS-confinement half is platform-gated OFF** (#336/#430): the Seatbelt box is incompatible with the autonomy toolchain — `excludedCommands` is non-functional in this Claude Code, and the credential `denyRead ~/.config/gh` floor collides with `gh`'s own config read, so an enabled box silently breaks `gh`/`pkit`/`git push` (ADR-014). Rather than enabling, it writes `sandbox.enabled: false` to `settings.local.json` (correcting a non-functional stale `enabled: true`) and prints a loud message naming both blockers; the intent-layer autonomy posture still applies. Also auto-applies the **narrowing** allowances of any detected toolkit (only its narrowing entries — a toolkit may be mixed, e.g. the `uv` toolkit carries both its `~/.cache/uv` narrowing cache and a macOS `exclude-command` widening; the widening half is never written here) — specifically the `uv` toolkit's `~/.cache/uv` write allowance when `uv.lock` or `pyproject.toml` is present, so the confined `pkit`/`uv` CLI can reach its package cache on Linux/bubblewrap without a manual `sandbox accommodate uv` step; inert on macOS where the uv CLI is excluded from the box (ADR-014/ADR-027). Written via the single provenance writer (ADR-008 rule 2); idempotent. `--strict` also locks the unsandboxed fail-over escape hatch (`allowUnsandboxedCommands: false` — the seal `setup autonomy` defaults to per ADR-028); re-running **without** `--strict` clears a previously-set seal (the reversibility lever — restores the harness-default fail-over and the operator's `dangerouslyDisableSandbox` stopgap). The dangerous flag (operator-only, per-invocation, never a committable default) is the sole way to write fail-open | yes | no — additive, idempotent |
| `permissions sandbox disable` | turn the OS sandbox off (`enabled: false`); operator sandbox keys (excludedCommands, denyRead, …) survive | yes | no — idempotent |
| `permissions sandbox toolkit list` | list confinement toolkits (per ADR-008) — per-tool sandbox allowances, each marked **narrowing** (makes the box usable) or **widening** (carves a tool out of the box) + which are accommodated | no | yes (read-only) |
| `permissions sandbox toolkit show <name>` | show a toolkit's exact allowances, each classified by boundary effect, with honesty glosses on widening entries | no | yes (read-only) |
| `permissions sandbox accommodate <tool>… [--detect] [--remove]` | apply a toolkit's **narrowing** allowances (build caches, sockets) so legit tooling works inside the box; records the choice in `permission-config` (committable, narrowing-only); `--detect` scans lockfiles/manifests; `--remove` drops only pkit-authored entries (operator entries untouched, via provenance). Never applies widening | yes | no — additive, idempotent |
| `permissions sandbox accommodate --socket <path> [--name <id>] [--remove]` | a one-off **narrowing** unix-socket allowance (e.g. `--socket "$SSH_AUTH_SOCK"` for the SSH agent / signing socket) — per-machine, `_manual`-provenance, **never committed** (per ADR-010); `--name` keys it for recompute-replace. `setup autonomy` reuses this writer to auto-resolve `$SSH_AUTH_SOCK` | yes | no — recompute-replace, idempotent |
| `permissions sandbox exclude <cmd> [--weaker-tls] [--remove]` | the **widening** gesture: carve a command out of the box so it runs UNCONFINED. Loud, per-invocation, **never** written to committed config, never proposed by detect; reported by `sandbox status` (attributed *operator-set*) + `probe`. Never applied by setup — **except** the one necessity-verified, platform-mandatory required exclusion `setup autonomy` auto-applies under the `_required` tag (ADR-027); that one carve-out of ADR-008 rule 4 is the only setup-applied widening | yes | no — additive, idempotent |
| `permissions profile list` | list available autonomy profiles (shipped + project), marking the active one (per ADR-005) | no | yes (read-only) |
| `permissions profile show <name>` | show a profile's posture + layered grants | no | yes (read-only) |
| `permissions profile activate <name> [--no-apply]` | activate a profile: set posture + layer its grants under your own (never overwriting manual grants), then `apply` unless `--no-apply`. Does not enable the hook | yes | no — idempotent (overwrite + swap) |
| `version` | show CLI version + project's recorded core-layer version | no | yes (read-only) |
| `version bump <segment>` | bump `.pkit/VERSION` (`segment` = `patch` / `minor` / `major`); see PRJ-002 | yes | no — each call increments |
| `release plan [--json]` | preview the release computed from pending changesets (PRJ-002); `--json` emits a machine-readable summary for the release-PR automation; see `.pkit/release/README.md` | no | yes (read-only) |
| `release apply [--no-broaden]` | consume changesets → write versions + broaden `requires_backbone` + changelog (the sole main-only writer, PRJ-002 D3); tagging is a separate step (`version tag`). Broaden has two shapes: a backbone release widens every component to the new backbone minor (PRJ-002 D4); a component release widens the released component's own bound to cover the current backbone (#494 / COR-041 — the author-side claim). Both widen-only; `--no-broaden` skips it. See `.pkit/release/README.md` | yes | no — writes a release |
| `release merge <pr> [--dry-run]` | merge a release PR (the sanctioned path for a `chore(release):` PR that closes no issue) — guarded to `release/*` heads, merges only an open/mergeable/green PR by squash + delete-branch; does not tag (`release-tag.yml` tags post-merge); see `.pkit/release/README.md` | yes | no — merges a PR |
| `release publish-notes <version> [--dry-run]` | publish a **notes-only** GitHub Release for tag `v<version>` (body = that version's `CHANGELOG.md` section) so the release page shows what changed — idempotent (updates if it exists), **no artifact** (a notes overlay on the tag install path, PRJ-004), repo from the ambient `gh` context; `--dry-run` prints the notes without calling `gh`; see `.pkit/release/README.md` | no (publishes a Release) | no — calls `gh` |
| `release check --base <ref>` | CI guard: fail a PR whose surface change ships no changeset (escape hatch: `none` changeset / `skip-changeset` label) | no | yes (read-only) |
| `release lint` | format lint of the OBJECTIVE changeset + `CHANGELOG.md` subset (category enum, body shape, changelog heading structure); a reminder not a proof (escape hatch: `--skip` / `PKIT_CHANGELOG_LINT_SKIP`) | no | yes (read-only) |
| `release check-shareable <component>` | pre-sharing lint: is a capability ready to be consumed externally-sourced (COR-041)? Checks it declares a `version`, a well-formed `package.yaml` manifest, and a bounded `requires_backbone` range; warns on cheaply-detectable local-only assumptions. Reports pass / the specific gaps; project-neutral (any component by name); see `.pkit/release/README.md` | no | yes (read-only) |
| `process health [--process <addr>] [--interpretation-only] [--json]` | walk every opt-in hand-off contract (COR-042) and report missed hand-offs; report-only, takes no subject; exits non-zero on any miss or indeterminate. A `--process` scope that matches nothing walked is itself indeterminate (never a clean empty run); a bare run over zero declared contracts stays clean. `--interpretation-only` re-renders the same walk as the COR-044 authoring check: indeterminates only, misses not counted, exit non-zero on any indeterminate | no | yes (read-only) |
| `process new <capability>:<process-id> [...] [--dry-run]` | scaffold a lint-clean process definition into its NAMED owning capability + a fail-closed predicate stub per declared evaluable, registered in the capability's package.yaml (COR-044); errors cleanly with no owning capability, or one the project does not register as a component (`pkit capabilities register <name>`) | yes | no — one-shot, refuses an existing id |
| `process couple <addr> --state <s> --upstream <addr> --relation <r> --mode <m> --why <prose> [--dry-run]` | append a `depends_on` entry (COR-038) to the invoker-named definition; relation/mode validated against the closed vocabularies read from the shape contract; definition `version` NOT bumped | yes | yes — identical entry is a clean no-op; the same `(upstream, relation, mode)` with a different `why` refuses |
| `process hand-off <addr> --upstream <addr> --trigger <state> --candidates <cmd> --resolve <cmd> [--state <s>] [--dry-run]` | add a COR-042 hand-off contract to an existing coupling; validates the trigger against the upstream where resolvable; scaffolds + registers the seam stubs when new; `version` NOT bumped | yes | yes — identical contract is a clean no-op; a different contract refuses |

## Lifecycle commands

### `init`

Runs first install in this order:

1. **Propagation** — every path in the synced manifest is written into the project's `.pkit/` tree.
2. **Seed** — every path in the seed manifest is written once with its template content.
3. **Merge** — every declared merge target is merged with its core baseline (per COR-002's two-tier contract).

**Announce-and-confirm gate (issue #780).** `init` does not install silently at whatever the resolver picks — the target can be a git root or install-marked ancestor well above where you are standing. Before installing it:

- **Announces on every run** — including the happy path — the resolved install target, *why* it was chosen, and any real project-kit install (a `looks_like_pkit_install` match, not a bare `.pkit/`) found between your current directory and the target or at it. The reason is one of: your current directory **is** the git root (install here); a git root **above you** (that root is the target; `--here` is refused); a structurally-real repository git **could not verify** — dubious ownership / `safe.directory` (init refuses and guides you to `git config --global --add safe.directory …` or an explicit target); an **already-adopted** project-kit install above you (init refuses and redirects to `pkit sync` — never an install target); or a fresh **non-git folder** (install here). A broken or vestigial `.git` is skipped by the validated walk, never offered as a root.
- **Confirms before installing anywhere other than your current directory**, and before creating a standalone install in a fresh non-git folder. On an interactive terminal it prompts; on a **non-interactive / piped stdin it refuses** rather than auto-confirming (a piped `yes |` no longer silently installs somewhere you did not expect). For an **off-CWD** target (a git root above you) the sanctioned non-interactive escape is `--root <path>` — a bare `--yes` will not install there. For a target that **is** your current directory (a fresh non-git folder), `--yes` accepts the offer, and `--here` installs in the current directory.
- **Refuses an off-target split-brain**: if an install sits between your current directory and the resolved target but the target itself has none, installing there would leave two installs straddling your current directory. `init` refuses and names the existing install; pass `--root <path>` to install at that target anyway.
- **Refuses to re-run when the target is already a project-kit project** — `init` is one-shot, not idempotent (COR-004): it exits non-zero, names the project, and points you at `pkit sync` to refresh kit-owned content. The refusal fires before any confirm, so you are never prompted for an install that could not proceed anyway.

Flags:

- **`--here`** installs into the current directory instead of a resolved parent. **Honored** when the current directory is a git root or a non-git folder (no git-root-wins precedence overrides your current directory, so a `.pkit/` here is reachable). **Refused only when the current directory is a subfolder of a git worktree** — every command there resolves to the git root, so a `.pkit/` in the subfolder would be unreachable; `init` points you at the git root instead. Mutually exclusive with `--root`.
- **`--yes`** accepts the confirm only when the resolved target **is your current directory** (a fresh non-git folder). It never installs at an off-CWD target — a bare `--yes` from a subfolder refuses and points you at `--root`, so a non-interactive run can never install somewhere you are not standing.
- **`--root <path>`** installs at an explicit, existing path — the sanctioned way to install at a resolved parent (e.g. a git repository root) non-interactively in CI, where a bare `--yes` is refused. Mutually exclusive with `--here`; a nonexistent path is refused at the CLI boundary rather than silently materialised. Still honours the already-adopted-install refusal (redirects to `pkit sync` rather than re-installing), and warns loudly when the path is a subfolder of a git worktree — the nested `.pkit/` would be unreachable until monorepo support lands, but the explicit `--root` is your consent, so it proceeds.
- **`--dry-run`** previews what would be installed without writing any files or prompting (per COR-004).

If you arrive at a partial or broken state, run `validate` to see what is and isn't consistent, then use targeted `sync` / `merge` to recover.

### `sync`

Re-runs propagation only. Pulls current canonical core content into your project's `.pkit/` tree. Does **not** invoke seed (one-shot only — see COR-001) or merge (separate consent profile — see COR-002 and COR-004). Idempotent: re-running with no changes pending reports "current" and exits cleanly.

**Capability downgrade guard (`--force`).** When sync reconciles an installed kit-shipped capability against its kit source (auto-upgrade per COR-017), it compares the source version to the installed version of record (the per-component `manifest.yaml`, falling back to the installed `package.yaml`). If the source is **older** than what's installed — the sign of a stale or mis-pinned source — sync **refuses** that capability's refresh, printing a `refused` line naming both versions, and leaves the installed tree untouched rather than silently downgrading it. Pass **`--force`** to override: the downgrade then proceeds, but a loud `downgrade` line records the deliberate overwrite. A source version equal to or newer than installed refreshes normally, unaffected by the guard. (This is the fix for issue #524, where a stale source silently overwrote a newer committed capability tree.)

On **self-host** (project-kit itself, where the source *is* the installed `.pkit/`), propagation would copy files onto themselves — so `sync` skips propagation and runs only the adapter deploy primitives instead, re-wiring the harness (`.claude/` agents, skills, settings, CLAUDE.md) from the source you just edited. This is the self-host way to apply source edits to the harness; you don't (and can't) `sync`/`upgrade` project-kit onto itself otherwise. (The downgrade guard reconciles capabilities, which self-host skips, so it never fires there.)

### `merge [<target>...]`

Re-runs merge against one or more declared merge targets, or against all targets if no argument is given. Honours the two-tier (auto-add / prompt-once) contract from COR-002. Idempotent.

Use this when you want to pull baseline updates for a single fixed-path config file (e.g., `.claude/settings.json`, `.gitignore`) without invoking other operations.

### `upgrade`

Compares the version of the core layer recorded in your project against the version this CLI was built from. Runs any pending migrations in order, then runs `sync`. Refuses to proceed if your project's recorded version is ahead of the CLI's (and tells you so).

It also **updates the pkit tool itself** when it is stale (per [ADR-044](../../docs/architecture/decisions/ADR-044-upgrade-self-update-detect-instruct.md), amended): it queries the release source for the latest tag and, when the installed `pkit` is behind, runs **`uv tool install --force …@v<latest>`** and **re-runs the upgrade under the new version** — one seamless command, no manual step. It **degrades to just printing the command** (the old behaviour) when the session is non-interactive (no TTY, so a network install is never forced under automation), when `--no-self-update` is passed, or if the install fails/is declined (the sandbox gates a global-binary mutation) — it never bricks. Run **outside any project**, `pkit upgrade` performs this tool update alone instead of erroring on a missing project — and "outside" is judged honestly: a `.pkit/` ancestor counts as a project root only when it looks like a real install (`manifest.yaml`, or `decisions/` for pre-manifest installs), so a stray junk `~/.pkit/` never makes upgrade resolve your home directory as the project. This is safe because pin-by-default insulates projects from the global tool — updating it never disturbs a pinned project (which runs its own version via the router's `uvx` re-exec). When the tool is current it says so; any lookup failure (offline, timeout) warns and continues; it is suppressed on a source checkout / self-host.

On **self-host**, there is no backbone to upgrade (the source is the installed state), so `upgrade` short-circuits to the self-host `sync` above — re-running the deploy primitives — rather than attempting a version transition.

**In a pinned project** (one that has a `.pkit/version-pin` directive — see [`pin` / `unpin`](#pin--unpin-per-project-version-pin) below), `upgrade` *auto-advances the pin to the latest release* rather than floating on the installed tool — with **no `uv tool install` and no manual step at all**. The framing is: `upgrade` advances a project **as far as it safely can without mutating the shared global tool**. An un-pinned project cannot go past the installed bundle without a global `uv tool install` (a shared-binary mutation with cross-project blast radius), so it only *instructs* (the staleness check above); a pinned project can advance with **zero global mutation** — the router's bypass + ephemeral `uvx` fetch the target's own code per-project — so it *acts*.

**Pinning is the default (`--no-pin` to opt out).** An un-pinned project is **pinned by default** after `upgrade`, at the version it just upgraded to — so pinning is the norm and a project stays code⟺content-coherent with no remembered gesture. It pins at the *local* synced version (offline-safe — no `git ls-remote` latest lookup), writes the pin **last** (after content + migrations, so a failed sync never leaves a pin ahead of content), and is a **no-op on an already-pinned project** (the auto-advance above already maintains the pin). Pass **`--no-pin`** to keep the project un-pinned — it then keeps following the installed global tool, running in-process (`pkit unpin` removes an existing pin). Note the default therefore moves a project into the pinned (uvx-re-exec) execution model on its next upgrade; the router degrades an unresolvable pin to running self, so a pinned project never bricks offline. Self-host (project-kit's own checkout) is never pinned.

Concretely, when `upgrade` detects it is running as the pinned child (the router re-exec'd it into the pinned version, which cannot mutate the global tool from inside), it resolves the latest released version via the same `git ls-remote` check, then:

- **latest is newer than the pin** → it reconciles content forward to latest *under the target's own code* (bootstrapped through the `PKIT_NO_ROUTE=1` router bypass) and, **last of all, flips the pin forward** — so a failed reconcile never advances the pin *past* content that isn't in place. This ordering guarantees the pin is never ahead of content; it is not a single atomic transaction. If a raise is interrupted mid-migration, content can be advanced with the pin not yet flipped — a benign, self-correcting state: just **re-run** the upgrade, which is idempotent (sync re-applies content, migrations no-op on already-applied state, the pin flip no-ops once it matches).
- **latest equals the pin** → a clear "already at the latest release" no-op; the pin is untouched.
- **latest is older than the pin** (the project is pinned ahead of the newest release) → it says so and leaves the pin; pkit never downgrades a pin (migrations are forward-only, COR-010).
- **the release source is unreachable** (offline, no credentials, timeout) → it degrades loudly to a warning and leaves the pin unchanged; it never bricks the command.

An **un-pinned** project's `upgrade` is unchanged: plain content-sync from the tool's bundle, no pin file written.

> **Rollout note.** The auto-advance logic lives in the *pinned wheel's* own `upgrade` code, run under the target version. A project pinned *below* the ship that introduced this behaviour keeps the old print-only escape until it is first raised past that ship — the old code is what runs while the pin sits below it. There is no bootstrap gap: `pkit pin <newer>` already self-bootstraps with no `uv` step, so an operator can always move such a project forward with `pkit pin <version>`, after which `pkit upgrade`'s auto-advance is live.

### `pin` / `unpin` — per-project version pin

Per [ADR-049](../../docs/architecture/decisions/ADR-049-per-project-version-pin.md), a project opts into running a fixed pkit version by committing a **`.pkit/version-pin`** directive — a plain one-line text file holding a version number. It is **project-owned and never kit-synced**: `init`, `sync`, and `upgrade`'s content pass never write or clobber it; only the gestures below do. Its *presence* is the opt-in signal — the router reads it and re-execs `uvx project-kit@<pin>` so the pinned version serves every command, and a global-tool upgrade no longer moves this project. Absent the file, nothing changes: the router runs the installed binary as-is. This is the lockfile model (`.python-version`-style): you *write* a pin, then separately *raise* or *remove* it.

- **`pin [<version>]`** — write the directive. VERSION is a **version number only** — `1.145.0`, or `v1.145.0` (a single leading `v` is stripped). Branch, commit-sha, and pre-release / build-metadata pins are **refused** (the command exits non-zero and writes nothing): the router can only route a bare `v<semver>` tag, so those are deferred to a later router change. Both forms **require `.pkit/manifest.yaml`** (the project's recorded content version); run `pkit sync` first if it is absent.
  With **no argument** it freezes the project at its current *content* version (`.pkit/manifest.yaml`'s `backbone_version`) — the common case: lock this project where its content is (so no-arg `pin` == `pin <current-content-version>`). Freezing at the content version, not the installed binary's version, avoids baking in a code-vs-content mismatch when the tool is ahead of synced content. With a **`<version>`** token it dispatches on how that version orders against the content version:
  - **equal** → freeze in place (write the pin, no content sync);
  - **newer** → reconcile content forward to the target *under that version's own code* (`uvx project-kit@v<version>`, run under the `PKIT_NO_ROUTE=1` bypass so it doesn't route-loop) — this syncs content + runs the forward migrations — then flips the pin **last**, so a failed reconcile never advances the pin past content that isn't in place. This ordering keeps the pin from ever getting ahead of content; it is not one atomic transaction — an interrupted raise is recovered by re-running (idempotent);
  - **older** → **refused**. pkit migrations are forward-only (COR-010), so there is no safe content-sync back to an earlier version; the command exits non-zero, writes nothing, and touches no content. To roll a project back, `git checkout` the `.pkit/` tree at a commit that carried the earlier version (`git checkout <ref> -- .pkit/`) — git restores kit-owned *and* project-owned state together, atomically (this also reverts `.pkit/version-pin` itself, and only restores a state that exists in history), which a forward-only content sync cannot. There is deliberately no `--force` override.
- **`upgrade`** — raise an existing pin forward to the latest release, automatically and with no `uv` step (see the pinned-project note under [`upgrade`](#upgrade) above).
- **`unpin`** — remove the directive; the project reverts to floating on the installed binary. Idempotent — fine to run when no pin is present.

### Capabilities — two ways in

A capability enters a project through one of two verbs, distinguished by where the capability was authored (its *origin*, per COR-031):

- **`capabilities install <name>`** — for a **kit-shipped** capability. The capability ships in the kit source; install copies its subtree into the adopter's `.pkit/capabilities/<name>/`, registers it (origin `kit-shipped`), and deploys its skills/agents. `sync` thereafter reconciles it against the kit source (auto-upgrade per COR-017).

- **`capabilities register <name>`** — for an **in-repo (incubated)** capability the adopter authored in *its own* repo at `.pkit/capabilities/<name>/`. Because the working tree *is* the source, register performs **no copy**: it records the capability in install-state with origin `incubated-in-repo`, then runs the *same* deploy primitives and dependency gating an install runs, so the capability's skills/agents land in the harness exactly as a kit-shipped one's would. `sync` thereafter **skips source-reconciliation** for it — there is no kit source to reconcile against, and the files are adopter-owned (the no-shared-files invariant) — so a home-grown capability survives `sync` untouched instead of being flagged "no longer shipped" or refreshed from an empty source.

**The in-repo activation flow.** Scaffold a capability with `pkit new capability <name>` (or hand-author the subtree), build it out under `.pkit/capabilities/<name>/`, then run `pkit capabilities register <name>`. Register applies every pre-flight an install does *except* "exists in kit source" (the in-repo tree is the source): it checks backbone-version satisfaction, runs the COR-030 dependency gate, and refuses on a naming collision against *other* installed content (the capability's own artifacts are not collisions against themselves). Origin is the only thing that differs between the two paths — participation, deploy, and dependency edges are identical (COR-031 D1). `capabilities list` and `pkit status` mark each installed capability's origin so an incubated one is visibly distinct from a kit-shipped one.

**Adopting an already-registered capability.** `register` is idempotent, branching on the recorded origin (COR-031 D2). If the capability is already registered as `incubated-in-repo`, register reports a clean no-op and returns. If it is registered `kit-shipped` — including the origin-unset default that the old manual-registration workaround leaves behind (an absent origin reads back as `kit-shipped`) — register *adopts it in place*: it re-runs the applicable pre-flights (self-consistency, backbone-version, dependency), sets `origin: incubated-in-repo` on the existing registry entry, and reports the change. It does **not** re-copy the subtree (already in place) or re-deploy — this is an origin-state upgrade, not a fresh install — so it is the supported path to protect a manually-registered home-grown capability from `sync` reconciliation. `--dry-run` shows the adoption without writing. (`upgrade` cannot do this: it refreshes deploy but never changes origin.)

**When the same name also ships from kit source (collision — graduation arriving unbidden).** If a capability you register (or adopt) at `.pkit/capabilities/<name>/` *also* exists in the kit source, `register` keeps/adopts the **in-repo (incubated)** copy and **surfaces a note** that a kit-shipped version is available — it never silently shadows either tree. This is the operational precedence for COR-031's collision boundary: the adopter's local copy is the one installed, and `sync` leaves it untouched (D1) — it is the only copy of the adopter's work — while the kit-shipped version is neither installed nor reconciled against; its existence is surfaced so you *know* it is there (COR-031 reserves incubated→kit-shipped **graduation** for a later decision). If instead you want the *kit-shipped* copy of a colliding capability — e.g. your local one was an abandoned experiment — that reverse preference is a known limitation; for now, remove the in-repo copy and run `pkit capabilities install <name>` to take the kit version.

If a same-named capability later begins shipping from kit source (graduation, before graduation is specified), `register` surfaces the overlap as a note and registers the in-repo copy; `sync` surfaces the same collision rather than silently shadowing either tree (COR-031 boundary case).

## Authoring commands

The `new` family scaffolds first-class methodology elements — areas, adapters, capabilities, migrations — by stamping the contract their owning record fixes (COR-005 for adapters, COR-010 for the manifest layer and migrations, COR-011 for areas, COR-017 for capabilities). Every `new` command is a one-shot generator: it refuses to overwrite existing targets, and the output is a directory or file the rest of the CLI surface (`status`, `sync`, `upgrade`, etc.) recognises immediately. No manual manifest edits are needed after a scaffold call.

Templates live where the contract they instantiate lives — `.pkit/lifecycle/templates/` for migration scripts and per-component manifest skeletons; `.pkit/cli/scaffolds/` for area, adapter, and capability directory shapes — so a kit upgrade that changes a contract also updates what gets stamped.

### `new area <name> [--variant <variant>]`

Scaffolds an adopter-owned area at `.pkit/<name>/` with the README skeleton appropriate to the chosen variant (per COR-011). The variant is one of:

- **`universal`** — gives the area the `core/` + `project/` layout (per COR-003).
- **`adapter-umbrella`** — top-level harness translations, like `.pkit/adapters/` itself.
- **`specialized`** — minimal layout (just a README); the area's content shape is documented in the README directly.

Default variant is `specialized` if `--variant` is omitted. Refuses if `<name>` is a kit-shipped area name (no-shared-files invariant) or if `.pkit/<name>/` already exists. (The `bundle-based` variant was retired in COR-027 — alternative implementations live as capability-internal data per COR-018, not as filesystem-level bundles.)

### `new adapter <name>`

Scaffolds a top-level adapter at `.pkit/adapters/<name>/` (per COR-005). Stamps:

- `package.yaml` — versioned `0.1.0`, `requires_backbone` pinned to a range matching the project's current backbone (per COR-010's compatibility model).
- `README.md` — skeleton.
- `settings/core/settings.json` — empty baseline.
- `deploy-skills.sh`, `merge-settings.sh` — primitive stubs.
- `migrations/` — empty directory.

### `new migration --tier <tier> [--component <name>] --version <X.Y.0> [--scope <scope>] --slug <kebab>`

Drops a numbered, executable script into the right `<major>.<minor>.0/` directory under the relevant tier's migrations tree (per COR-010 and `.pkit/lifecycle/README.md`).

- **`--tier`** is one of `backbone`, `adapter`, `capability`. Determines the tree the migration lands in.
- **`--component <name>`** is required when `--tier` is `adapter` or `capability`; identifies the component the migration belongs to.
- **`--version <X.Y.0>`** is the target minor version. The patch segment is always `.0` (per the lifecycle spec — patches have no migrations).
- **`--scope <scope>`** is one of `manifest-schema`, `structural`, `resource` (default). Scope determines the script's boilerplate header and the ordering convention within its directory.
- **`--slug <kebab>`** is a kebab-case description used for the file name.

The output filename is `<NNN>-<slug>.sh`, where `NNN` is the next zero-padded index in the directory. The stamped script includes the contract boilerplate from `.pkit/lifecycle/README.md` ("Migration framework" → "Script contract"): `set -euo pipefail`, `ROOT` env consumption, and an idempotence-pattern comment.

### `new decision <namespace> <slug>`

Scaffolds a new decision-record stub per the schema in `.pkit/decisions/README.md`. The command is the deterministic part of authoring a record: pick the next number in the namespace, stamp the frontmatter and the four required section headers, leave the body empty for the author to fill.

- **`<namespace>`** is one of:

  | Namespace | Prefix | Location | Per COR |
  |---|---|---|---|
  | `core` | `COR-NNN` | `.pkit/decisions/core/` | (the methodology) |
  | `project` | `PRJ-NNN` | `.pkit/decisions/project/` | (the methodology) |
  | `adr` | `ADR-NNN` | overlay-resolved (see below) | COR-025 |
  | *a capability name* | `DEC-NNN` | `.pkit/capabilities/<capability>/decisions/` | (per-capability) |

  Numbering is independent per id-space. A `<namespace>` that is not `core`, `project`, or `adr` is interpreted as a capability name: the record stamps under that capability's `decisions/` directory with the `DEC` prefix, numbered independently within that capability (two different capabilities may both hold a `DEC-001`). The command refuses if no capability of that name exists under `.pkit/capabilities/`; the `decisions/` subdirectory is created on first use.

- **`<slug>`** is a kebab-case shorthand of the decision's title — short enough to keep listings self-documenting (e.g., `merge-delivery`, `pattern-extraction`).

For `core` and `project` namespaces, the target directory is fixed at `.pkit/decisions/<namespace>/`. For the `adr` namespace, the target directory is read from the agents overlay at `.pkit/agents/project/overlay.yaml` — specifically the first entry of the top-level `adr-records:` list (per COR-024's `<adr-records>` placeholder + COR-025's ADR decision space). The command refuses with a helpful message if:

- the overlay file is missing,
- the `adr-records:` key is missing or empty,
- the resolved path is inside `.pkit/` (ADRs describe the adopter's project, not the methodology installed in it — per COR-025),
- the resolved directory doesn't exist on disk (suggests `mkdir -p <path>` first, so typos don't silently become directories).

Per-agent overrides of `adr-records` (under `overrides.<agent>:`) are *not* consulted by the stamping command — the top-level key is the canonical write target. If an adopter sets a per-agent override that diverges, that's a configuration error to reconcile by hand.

The stamped file includes:

- Frontmatter — `id` (auto-numbered), `title` (placeholder), `status: proposed`, `date` (today's date), `author` (read from `git config user.name` and `git config user.email`).
- The four required section headers — `## Context`, `## Decision`, `## Rationale`, `## Implications` — empty.

Refuses if a record with the same slug already exists in the id-space, or if the namespace is invalid — for a capability namespace, "invalid" means no capability of that name exists under `.pkit/capabilities/`.

**Coordination with the `decision-author` skill.** Per COR-006's discriminator: a command stamps deterministically, a skill drafts content conversationally. The `decision-author` skill (`.pkit/skills/core/decision-author/`) calls `pkit new decision <namespace> <slug>` for the stub, then walks the author through filling the body — content drafting, discipline self-checks, and approval. Authors who don't need the conversational help can call the command directly.

### `new scratchpad <slug>`

Stamps a new active-state scratchpad note at `.pkit/scratchpad/active/<YYYY-MM-DD>-<slug>.md` per the convention in COR-012 and the spec in `.pkit/scratchpad/README.md`. The command is the deterministic part of starting a note: pick today's date, validate the slug, seed the frontmatter, write an H1 derived from the slug.

- **`<slug>`** is a kebab-case shorthand of the question the note explores (e.g. `agent-architecture`, `versioning-policy`). Slugs are unique across the entire scratchpad area — the command refuses if any state folder already contains a note with this slug.

The stamped file includes:

- Frontmatter — `authors` (a list seeded from `git config user.name` / `user.email`) and `started` (today's date).
- A level-1 heading derived from the slug as a starting title (the author edits it on first pass).

Supports `--dry-run`.

**Coordination with the `scratchpad-author` skill.** The paired skill (`.pkit/skills/core/scratchpad-author/`) carries the slug-choice judgement, the topic-boundary discipline, and the body-drafting opening prompt. Authors who don't need the conversational help can call the command directly.

## Scratchpad commands

Scratchpad notes (per COR-012) move between three state folders — `active/`, `done/`, `dropped/` — plus the optional `reported/` side-state of active (per COR-043: lazily created when the first note enters it, removed when it empties). The retire-direction commands wrap the `git mv` + frontmatter update; the convention's full spec lives in `.pkit/scratchpad/README.md`.

### `scratchpad done <slug> [--produced <ref>...]`

Moves a note from `active/` — or from `reported/`, retirement proceeds from the side-state by the same gesture — to `done/` and appends `retired` (today) and `produced` (the list of `--produced` refs) to its frontmatter. Use when the note's content has been incorporated into other artifacts (records, docs, skills, agents). A reported note's `produced` refs naturally include the upstream issue(s) it became.

- **`<slug>`** matches either the slug portion of the filename or the full filename. Use the full filename to disambiguate when multiple notes share a slug (rare; the `new scratchpad` command refuses duplicates within the area).
- **`--produced <ref>`** is repeatable. Each value is a record ID (`COR-013`), file path (`.pkit/agents/README.md`), or URL. May be omitted; the `produced:` field is then not added (the author can edit it later by hand).

Supports `--dry-run`. Refuses if no active or reported note matches the slug, or if the destination filename already exists in `done/`. When the move empties `reported/`, the directory is removed (it is lazy — COR-043).

### `scratchpad drop <slug>`

Moves a note from `active/` (or `reported/`) to `dropped/` and appends `retired` (today) to its frontmatter. Use when the line of thought did not pan out.

Before dropping, the convention asks the author to append a closing paragraph to the body explaining *why* the line was abandoned, so future readers do not re-tread the path silently.

Supports `--dry-run`. Refuses if no active or reported note matches the slug, or if the destination filename already exists in `dropped/`.

### `scratchpad reported <slug> <ref>...`

The **manual stamp gesture** (per COR-043): mark a note as sent through the report channel when the post happened outside the tooling — the URL path (the browser filed it; the compose flow ends by printing this exact command as the required follow-up, #664) or retroactive marking of a note hand-carried upstream before the mechanism existed. The automatic equivalent runs on a successful `pkit report` API post (direct or via `report submit`).

Moves the note from `active/` to the lazily-created `reported/` and appends to its frontmatter: `reported` (today), `reported_to` (the refs), and `reported_hash` (SHA-256 of the full file as it was at stamp time — the drift-detection anchor). On a note already in `reported/`, appends the refs not yet recorded and re-anchors the hash (a new send); duplicate refs are an idempotent no-op.

- **`<ref>`** is `owner/repo#N` or a full GitHub issue URL (normalised to `owner/repo#N`). Repeatable — one note may become several issues.

Supports `--dry-run`.

### `scratchpad list`

Lists every note grouped by state folder. For `reported/` notes it additionally (per COR-043):

- **Resolves each ref's upstream state live** via `gh` — pull-only at the moment of asking, nothing stored or synced; offline or unresolvable degrades to `state unknown`, never blocking.
- **Flags drift** — `[modified since reported]` when the current content diverges from the stamped hash. A warning, never a gate: reported notes are frozen by convention, and follow-up thinking belongs in a new note.
- **Prompts retirement** when *all* of a note's refs are closed, printing the exact `pkit scratchpad done <slug> --produced <ref>...` command. It never auto-retires — retirement carries `produced` refs only a human can complete.

## Diagnostic commands

### `status`

Read-only inventory of how project-kit is wired in this project — useful as a one-shot answer to "is this set up correctly?" Reports:

- **Project root** and the resolved **source pkit binary** (the `pkit` you ran from).
- **Whether `.pkit/` is installed** at the project root (and a hint to run `pkit init` if not).
- **Adapter status** (Claude Code today): whether `.claude/settings.json` is merged, whether a `.pre-pkit` backup exists, and a list of deployed skills split into kit-managed (symlinks into `.pkit/skills/`) vs user-managed (anything else under `.claude/skills/`).
- **Capabilities** — which are available in `.pkit/capabilities/` and which are installed (per COR-017).
- **Counts** for decisions (COR / PRJ records) and skills (core / project).

Output is human-readable with tagged status lines. Makes no changes.

### `validate`

Read-only state check. Verifies:

- The no-shared-files invariant — no project edits to core-owned paths.
- The manifest — every declared path is present and well-formed.
- Per-area schema rules — decision-record schema, link validity, naming conventions, and any rules each area documents in its own README.

Reports issues with their locations and a brief diagnosis. Makes no changes.

`status` answers "what's installed?"; `validate` answers "is it consistent?". Different questions, different commands.

### `schemas validate [<path>]`

Read-only check on the **capability-side schemas mechanism**: every YAML schema under `.pkit/capabilities/<cap>/schemas/` is validated against its JSON Schema companion (shape pass) and every typed-token cross-schema reference is resolved against the target namespace's id collection (resolver pass).

A YAML declaring an external `$schema` (a `# yaml-language-server:` directive or a top-level `$schema:` key naming a schema other than its own companion) is an **instance**, not a definition: it is exempt from the companion requirement and validated against the schema its pointer names, resolved relative to the YAML's own directory. Findings report against the instance's path with a JSON pointer into the offending position; a pointer whose target is missing or is not a valid Draft 2020-12 schema is itself a finding. See `.pkit/schemas/README.md` ("The pointer is validated, not just classifying") for the full contract.

With `<path>`, runs the same passes scoped to the given file or directory — useful for adopters whose data follows the same conventions outside the capabilities tree.

`--shape-only` skips the resolver pass (useful mid-refactor when a referenced target schema doesn't exist yet). It does not affect instance validation, which is shape-only by construction.

The no-PATH gate also runs a **fragment-token-resolution lint** (ADR-021): for every installed capability's `permissions/grants.yaml`, each grant's privilege token must resolve to a privilege in the *merged* catalog, or the deny silently does not bind (the bare-vs-scoped fail-open hazard). The lint reuses the decision core's merge (`load_catalog`) and token normaliser (`_privilege_ids`) so it agrees with the runtime exactly; it covers hand-authored fragments, not just those `permissions scaffold` / `permissions grant` produce. An unresolved token fails the gate with a clear message naming the file, the offending token, and the likely fix (usually the missing `<cap>:` scope). This pass is project-scoped (it needs the manifest + merged catalog), so it runs only in `schemas validate` with no `<path>`, not in the path-scoped form.

### `data validate <path>`

Read-only check on **adopter-side data files** against capability schemas (per COR-023, superseding COR-022). Resolves each file's binding in two steps:

1. **Field-first.** A top-level `pkit_schema: <capability>:<schema>` field is authoritative.
2. **Capability fallback.** Otherwise, the resolver walks every installed capability's `schemas/*.yaml`, collects each schema's `binds_to:` glob entries, and uses the first matching glob.

When neither resolves, the file is reported as unresolved. Schema-version mismatches refuse with a structured migration hint (auto-migration is out of scope in v1).

`<path>` is a file or directory; directories walk recursively for `*.yaml` (`.pkit/` subtrees are excluded — those are kit-managed, not adopter data).

`pkit data validate` is distinct from `pkit schemas validate`: the latter validates the *spec* (capability YAML + companion); the former validates *instance data* (adopter file + its bound schema).

### `version`

Prints the CLI's version and your project's recorded core-layer version side by side. Useful for confirming whether `upgrade` has work to do.

### `version bump <segment>`

Bumps `.pkit/VERSION` per the policy in PRJ-002. `<segment>` is `patch`, `minor`, or `major`:

- **`patch`** — backward-compatible bug fix to existing surface.
- **`minor`** — new surface added (new command, new principle, new area). Pre-1.0, this is the typical bump and may carry breaking changes per semver convention for `0.x` releases.
- **`major`** — reserved for `1.0.0` and post-1.0 spec breakage. Pre-1.0 the command refuses major bumps.

The command parses the current version, validates it as semver, computes the new version, writes it back, and prints `Bumped backbone: <old> -> <new>`.

After writing the new backbone version, the command **auto-broadens** the `requires_backbone` upper bound on every kit-shipped `package.yaml` under `$SOURCE_KIT` whose existing range no longer includes the new backbone version. The new upper bound is `<NEW_MAJOR.(NEW_MINOR+1).0`. Components whose range still covers the new version are untouched (so patch bumps that stay within the current minor line are no-ops on `requires_backbone`). Component authors who deliberately want a tighter range narrow it manually after the bump.

Under the current PRJ-002 policy, feature branches **declare** version intent via a changeset rather than bumping in-branch; `version bump` remains fully functional during cutover (introduce → migrate → retire) and is what the release step's writes are equivalent to. Recommended commit message when it is used: `chore(versioning): bump backbone <old> -> <new>`.

### `release plan` / `release apply` / `release merge` / `release publish-notes` / `release check` / `release lint`

The declared, release-driven version path (PRJ-002 D1–D4). Feature branches drop a **changeset** file under `.changes/unreleased/`; the release step on `main` is the sole writer of version state. `release plan` previews the computed release; `release apply` consumes the changesets, computes each tier's new version from current `main`, broadens `requires_backbone` (the broaden moves here, PRJ-002 D4), updates `CHANGELOG.md`, and deletes the consumed changesets. Tagging stays a separate anchored step (`pkit version tag --push` on `main` after the release commit lands), matching the bump/tag split. `release merge <pr>` is the **sanctioned merge path** for a release PR — one that closes no issue, which the project-management issue-PR merge gate legitimately refuses; it is guarded to `release/*` heads, merges only an open, mergeable, green PR (squash + delete-branch), and does not tag (`release-tag.yml` tags on the push to `main`). `release publish-notes <version>` publishes a **notes-only** GitHub Release for tag `v<version>` (body = that version's `CHANGELOG.md` section) so the release page shows what changed — it is **idempotent** (creates the Release, then edits its notes on re-run), attaches **no artifact** (a notes overlay on the git-tag install path, PRJ-004 — never a file/wheel channel), and derives the repo from the ambient `gh` context; `--dry-run` prints the notes without calling `gh`, and `release-tag.yml` runs it automatically right after it cuts a tag. `release check --base <ref>` is the CI surface-without-changeset guard, with a `none`-changeset / `skip-changeset`-label escape hatch. `release lint` is a sibling *format* check — it validates only the mechanically-checkable subset (a changeset's category is a Keep-a-Changelog group and its body is a well-formed sentence; `CHANGELOG.md` headings parse) and leaves plain-language judgment to the guide and review; it reads committed files only (no PR context), so it rides in the shared check aggregator (`scripts/check.sh`). The full mechanics — changeset format, contributor workflow, and both checks' honest limits — live in the release-flow spec (`.pkit/release/README.md`).

## Process commands

The process-substrate engine's surface (`pkit process status / can-move / move / validate / cascade / graph / health`) is specified operation-by-operation in the process area (`.pkit/process/README.md`, "The engine") — the engine's contracts live there with the shape reference, per COR-033. This section specs the commands whose contracts are CLI-owned rather than engine-owned: the health check and the three authoring stamps.

**Why the authoring stamps are `process new` and not `new process`.** Every other authoring stamp is a sub-verb of the `new` family (`new decision`, `new area`, `new capability` — see "Authoring commands"). The three process stamps are **deliberately** sub-verbs of `process` instead, because they are a family in their own right: `new`, `couple`, and `hand-off` all take the same `<capability>:<process-id>` address argument and all read the same shape contract, and two of the three mutate an *existing* definition, which the one-shot `new` family does not do. Grouping them under the address they share keeps that family visible; grouping them under `new` would split it across two namespaces and leave `couple` / `hand-off` homeless. The divergence is recorded here rather than left to be noticed: moving these verbs later is a CLI signature change, and would owe a migration (COR-010).

**All three stamps require a *registered* owning capability.** The gate, its three distinct refusals, and the no-manifest fallback it preserves are specified once under `process new` below; `couple` and `hand-off` apply the same check on the definition they are asked to mutate.

**Correcting a declared coupling or contract.** `couple` and `hand-off` refuse to overwrite a declaration that differs from what you asked for — deliberately, since a declared edge is a decision, not a draft. There is as yet **no stamp that edits one back**: repair rides with `amend`, the named-deferred operation for definition evolution (COR-044's deferred family). Until it ships, the interim route is to edit the `depends_on` entry in your own definition by hand and re-run `pkit process validate` — the one place where hand-editing a definition is the sanctioned path rather than a violation of it (core rule 3 governs *stamping* an artifact; there is no stamp to invoke here yet).

### `process health [--process <addr>] [--interpretation-only] [--json]`

Walk every declared **hand-off contract** — the opt-in `handoff` sub-block on a `depends_on` entry (per [COR-042](../decisions/core/COR-042-process-health.md)) — and report every **missed hand-off**: an upstream subject currently at its trigger state with no downstream subject picking it up.

Takes **no subject** (unlike `validate`): it walks contracts across the configured wiring. For each contract it resolves the upstream definition, runs the binding-supplied `candidates` source, confirms each candidate **one subject at a time** through the engine's own per-subject position resolution, and asks the binding's `resolve` predicate for the downstream counterpart (the two-predicate seam, per [ADR-048](../../docs/architecture/decisions/ADR-048-handoff-resolve-seam.md)). Entries without a contract are never evaluated.

- **Report-only.** No move is blocked, nothing is journaled or remediated; the check reads live positions and is safe precisely because nothing rides on the read. The at-trigger snapshot is live per run (a red produced by a race is an honest answer about the instant evaluated).
- **Fail-closed indeterminacy, distinct from a miss.** An uninterpretable contract (unresolvable upstream address, phantom trigger state, malformed block), an erroring/unavailable candidate source, an unreadable upstream position, or an erroring `resolve` reports **indeterminate** — never "nothing missed". A candidate source that evaluates cleanly to zero subjects is a determinate, clean answer. A process definition that cannot be loaded at all is surfaced and counted indeterminate (its contract set is unknown).
- **Exit code:** `0` only when misses **and** indeterminates are both zero; `1` on any miss or indeterminate (one non-zero code — miss-vs-indeterminate is distinguished in the report, not the exit code).
- **Deterministic report.** Couplings render flow-direction (`upstream → downstream   @trigger`, grouped per contract, one line per missed/indeterminate upstream subject — a satisfied subject produces no line) and order **topologically over the contract wiring**: upstream-most process groups first, name tie-breaks, deterministic name-order fallback on declared cycles; subjects name-sorted. No time/age-based ordering. Summary line: `N missed, M indeterminate`.
- **`--process <addr>`** keeps only contracts touching that `<capability>:<process-id>` as either endpoint. **`--json`** emits the byte-stable machine form: per-contract objects (`upstream`, `downstream`, `trigger`, `state`, `misses[]`, `indeterminate[]`, `counts`) plus `skipped[]` (unloadable definitions), `unresolved_scope` (below — `null` on any run that resolved its scope) and `totals`.
- **A scoped run that resolves to nothing is indeterminate, not clean.** Naming an address is a *claim*, and a claim can fail: when `--process <addr>` matches neither a walked definition nor any declared contract's endpoint, the run checked nothing, so it reports `unresolved_scope` — one indeterminate, exit `1` — and names the likely cause with its remedy (an on-disk-but-unregistered capability → `pkit capabilities register <name>`; no such capability; a registered capability with no such process id; a malformed address). Two neighbouring cases stay **determinate-empty and clean**: a **bare** run over a project that genuinely declares zero contracts (it makes no scope claim), and a **scoped** run against a definition that *was* walked and simply declares no contract touching it (the definition was read; "none declared" is a real answer). The line is between "read it, found nothing declared" and "never found it at all".

Offline and read-only apart from running the registered predicate scripts (which must themselves be read-only, per the engine contract). The contract's field shape and the seam payloads (`{candidates: [...]}` / `{downstream: [...]}`) are specified in the process area's `depends_on` section.

- **`--interpretation-only`** — the authoring-completion variant (per [COR-044](../decisions/core/COR-044-process-authoring-layer.md)): the same walk, re-rendered to answer only the interpretability question — does every contract resolve (upstream address, real trigger state) and do its seams execute? It reports **indeterminates only**; misses are **not counted, not rendered, and do not affect the exit code** (a fresh, correct contract routinely reports real misses — upstream work waiting is the very situation that motivates declaring it — so miss-count is never the authoring done-signal). Exit `0` iff zero indeterminates. Implemented as a **consumer of the health walker** (COR-042 point 5's design-once rule — never a parallel contract-walker); the default run's exit contract is unchanged. `--json` emits the machine form minus every miss surface (no `misses` arrays, no at-trigger/satisfied counts they could be derived from): per-contract `{upstream, downstream, trigger, state, indeterminate[], counts}` plus `skipped[]` and `totals.indeterminate`.
  - **Both seams are checked statically**, on top of whatever the walk exercised: each declared seam command must be registered in the declaring capability's `package.yaml`, its script must be on disk, and it must no longer carry the scaffold's stub marker. Without that, a contract whose candidate set is momentarily empty would never run `resolve` and would report interpretable with an unwritten seam — a done-signal that depends on who happens to be at the trigger. A statically-broken seam the walk *also* exercised is reported from both lenses; that is deliberate, not double-counting noise. The static findings belong to this view only — the default run's misses-plus-runtime-indeterminates contract is untouched.
  - **A report that finds nothing is not a pass — and the scoped form enforces that.** Contract discovery walks the process definitions of capabilities **registered as components** with the project. A scoped run against an address outside that set (a typo, or a definition in an unregistered capability) reports `unresolved_scope` and exits `1` rather than reading green — see the bullet above; the authoring stamps close the other half by refusing an unregistered capability outright. Read the summary line all the same: a green is only a pass if the report *names your contract*.
  - **Scope it to your own process.** The done-signal after authoring is `pkit process health --interpretation-only --process <your-address>`, **not** the bare form: bare walks every contract in the project, so another owner's unimplemented seam holds your signal red — against COR-044's owner-scoping posture. `--process <addr>` keeps every contract touching that address as **either endpoint** (your definition's contracts on its upstreams, and other definitions' contracts on yours).

### `process new <capability>:<process-id> [flags]`

The deterministic stamp under the process-authoring skill's `new` operation (per [COR-044](../decisions/core/COR-044-process-authoring-layer.md); the COR-005 skill/command pairing). Scaffolds a **lint-clean** process definition at `.pkit/capabilities/<capability>/schemas/<process-id>.yaml` — validated against the shape contract (`.pkit/schemas/_defs/process.schema.json`) **before** writing — plus a **predicate stub for every evaluable the declared shape demands**, each registered in the owning capability's `package.yaml` commands tree.

- **The owning capability is required, and must be registered.** A definition is a capability-instance artifact, so all three stamps refuse three distinct ways: an address with no `<capability>:` half, a capability with no directory on disk, and — the one that matters most — **a directory the project does not register as a component**, refused with `pkit capabilities register <name>` as the named remedy. That third gate exists because contract discovery walks only registered capabilities: a definition stamped into an unregistered one would be real, correct, and watched by nothing, with `process health` reporting no contracts and exiting `0` over it (#713). The gate shares discovery's own capability lookup, **fallback included** — with no backbone manifest, or one listing no capabilities, the installed set is the filesystem scan, so a pre-manifest install stays authorable. The command never routes a capability-less adopter through capability authoring or registration — that walkthrough is the skill's judgment (#685), not the stamp's.
- **Shape flags.** `--cardinality <v>` (+ `--key <slug>` for keyed, COR-032); `--domain-ref <pointer>`; repeatable `--state "<id>=<meaning>"` (declaration order kept — it can be load-bearing for detection precedence); `--entry <id>` / `--guarded-entry <id>` / `--terminal <id>` marks; repeatable `--transition "<from>:<to>:<trigger>[:<authorisation>]"` (authorisation defaults to `user`, the safe floor); `--gate "<from>:<to>:<trigger>[:<kind>]"` on a declared transition (kind defaults `deterministic`; `authorisation-artifact` is the other stubbed kind — the engine-computed kinds ride the deferred subprocess/cascade block surface); repeatable `--invariant "<id>=<why>"` (COR-035); `--blocked <reason>` (COR-034). Every enum-valued flag is validated against the shape contract's vocabulary **read as data**.
- **`--domain-ref <pointer>` records where the subject's *domain* data lives** — deliberately distinct from its process position, since the substrate tracks a position and not the thing itself. Optional on either cardinality: the shape requires only `cardinality`, and omitting the flag leaves the key out entirely, so a definition stamped without one is as valid and lint-clean as one with. **Free-form, and checked only for being non-empty** — the engine never interprets it and the contract fixes no form (a repo path, a tracker address, a URL are all admissible), so a stamp enforcing one shape would refuse pointers the contract accepts.
- **A transition is addressed by its full key `(from, to, trigger)`** — by the gate flag and by the derived gate-stub command name alike. Two transitions between the same state pair are shape-legal when their triggers differ (an `approve` beside a `force-approve`), so a pair-keyed address would leave the second permanently ungateable and make two gate flags on that pair silently last-wins. Consequences: the stamp requires a **kebab-case trigger** (it is an id the command name is built from, and the colon-separated flag grammar cannot carry a colon anyway), refuses a duplicate `(from, to, trigger)`, and refuses a second `--gate` on an already-gated transition.
- **Stubs per the predicate-runner contract:** detection always (one per state); an entry-guard, gate, `resume_when` (for `awaiting-condition`), or invariant-check stub when declared. Each stub is read-only, takes the subject argv + `--json`, and **fails closed** (exits non-zero) until implemented — an unwritten predicate can never read as green. Each also carries a **stub marker** the author deletes on implementing it, which is what `health --interpretation-only` reads statically. Implementing them is the `process-author` agent's territory.
- One-shot: refuses when the target file exists or any schema already claims the process id; refuses command-name collisions against the capability's registered commands, **and script-path collisions** — a hand-written `scripts/<name>.py` the capability has not registered is never overwritten by a stub.

### `process couple <addr> --state <s> --upstream <addr> --relation <r> --mode <m> --why <prose>`

The stamp under the skill's `couple` operation: append a `depends_on` entry ([COR-038](../decisions/core/COR-038-process-connections.md)) to the **invoker-named** definition's hosting state — coupling lives in the subscriber; the upstream is never touched (the owner-scoping COR-044 fixes by construction).

- `--relation` / `--mode` are validated against the **closed vocabularies read from the shape contract as data** — a new relation kind is an enum value the command picks up, never a code change. `--why` is required (COR-038).
- **No version bump:** the entry is additive, inert metadata (COR-044's version semantics — state/transition evolution is the deferred `amend` operation, which does bump).
- An upstream that does not resolve locally is declarable (warned, not refused — the entry is inert; a later hand-off contract on it would report indeterminate). Round-trip edit (comments and layout preserved); the result is re-linted and the prior file restored on any failure.
- **An entry is identified by `(upstream, relation, mode)`.** The shape places no uniqueness constraint on `depends_on`, so one state may legally depend on the same upstream in two different ways (an `informational` pull beside a `triggered-by` push) — a second entry with a different relation or mode is appended, not refused. The identical entry (that key plus the same `why`) is a clean no-op; the same key with a **different `why`** is a genuine divergence and refuses. See "Correcting a declared coupling or contract" above for the repair route.

### `process hand-off <addr> --upstream <addr> --trigger <state> --candidates <cmd> --resolve <cmd> [--state <s>]`

The stamp under the skill's `hand-off` operation: add a [COR-042](../decisions/core/COR-042-process-health.md) hand-off contract — the `handoff` sub-block (trigger + the two seam predicate refs) — to an **existing** coupling on the invoker-named definition. Refuses when no `depends_on` entry for the upstream exists (`process couple` first); `--state` disambiguates when the same upstream is coupled on several states.

- **Trigger validated where resolvable:** when the upstream definition loads, a trigger that is not one of its states is refused (a phantom trigger would report indeterminate forever); an unresolvable upstream degrades to a warning — health reports the contract indeterminate until it resolves, never silently green. Declare a **stable** trigger state (the ephemeral-trigger authoring smell, COR-042).
- `--candidates` / `--resolve` name commands of the **declaring** capability: unregistered names are scaffolded as fail-closed seam stubs (ADR-048 payload shapes — `{candidates: [...]}` / `{downstream: [...]}`) and registered in `package.yaml`; already-registered names are reused untouched. A name whose derived script path is already taken by an unregistered file refuses rather than overwriting it, with the definition left unedited.
- **No version bump** (additive, report-only edit). Idempotent on the identical contract; refuses to overwrite a different one (repair route above). The authoring done-signal afterwards is `pkit process health --interpretation-only --process <addr>` reporting **no indeterminates** — never a zero miss-count, and scoped to your own address rather than the whole project.

## Report commands

The built-in adopter→upstream feedback channel (per [pkit:PRJ-008]; cross-repo
realization [pkit:ADR-047]). A `report` files an issue to the **configured report
target** — the upstream repo the distribution sets in project config (for every real
adopter that is project-kit's own repo), *not* the adopter's own tracker. The environment block (pkit + capability versions, adapter, OS) is attached
automatically and **redacted by construction** (`$HOME`/paths stripped, kit-shipped
capabilities only unless `--include-private`).

**Run report verbs from your project root.** Everything the channel does is
anchored on the resolved project root: the environment block is collected from
it, and the draft store (`report submit`) lives *inside* it. Composing from a
scratch directory — the natural move when you draft a long body in a temp file —
resolves no project, and the flow says so rather than degrading silently (#693):
the compose **warns loudly** (naming the directory and this expectation) and the
environment block renders its project half as `NOT COLLECTED — composed outside
a pkit project`, never as `backbone: unknown` / `adapter: none` /
`capabilities: (none installed)` — values a maintainer reads as facts about
*your* install. The compose still proceeds (a report from outside beats no
report) and the unresolved marker stays **path-free**, like the rest of the
block; the directory is named only on your terminal. The environment block is
baked at compose time, so a report composed outside a project is re-composed
from the root, not relocated.

### `report bug` / `report feedback` / `report change-request`

Compose and file a **bug** (structured), **feedback** (freeform), or
**change-request** (structured-ish) report, agent-assisted (the `report-author`
skill). `change-request` is a **third sibling verb rather than a `--kind` flag on
`feedback`** because it follows PRJ-008's structured-vs-freeform verb split: a CR
carries its own compose template (motivation / desired behaviour / current
workaround), which a flag on the freeform verb would blur.

**Kind visibility (#663).** Every filed report carries its kind three ways: a
**title prefix** (`[Bug]` / `[CR]` / `[Feedback]`, prepended at compose before
the project parenthetical), a **namespaced GitHub label** (`report:bug` /
`report:change-request` / `report:feedback` — namespaced so the channel's
vocabulary never collides with the target repo's own labels), and the **body
kind-marker** (`<!-- pkit-report: kind=… -->`, stamped on every kind — the
machine-authoritative signal). An API post **creates the label on the target if
missing** (fixed color per kind, description "pkit report kind"); a label
create/apply failure **degrades to posting without the label** — a warning,
never a blocked send, because the prefix + marker still carry the kind. URL
prefills keep the label parameter (harmless where GitHub drops it — URL-filed
issues from non-collaborators lose labels); there the prefix + marker are the
reliable signals. The read side (`inbox` / `show` / `list`) classifies label →
marker → prefix, recognizing both the namespaced and the legacy bare-kind
labels; an issue the classifier cannot place renders as `unclassified`.

**The send path (#662): API-post primary.** With `gh` authenticated, the composed
payload (body + any overflow comment) is shown **once**, the confirm names the
target **and the posting identity** ("posts a PUBLIC issue to `<owner/repo>` as
`@<gh login>`"), and an explicit yes posts via `gh` — the note travels as the
issue **body**, never URL-embedded, so a real scratchpad-backed report files with
no copy-paste. The **prefilled-URL form survives only where it is honest**: no
`gh` auth, or an explicit `--url` — and only within the ~6000-char URL budget
(GitHub's edge rejects longer request lines with HTTP 414, so an oversized
prefill *hard-fails* on open; over budget the flow refuses the URL form and names
the API / stage alternatives instead). Whenever the URL form is used, the flow
warns that **the browser's logged-in account authors the submit** — it can
silently differ from the CLI identity (the misattribution that hit #659).
`--open` opens a within-budget prefilled form in the browser instead of forcing
copy-paste (degrades to the printed URL). `--yes` / autonomy **stages the
composed payload and prints three short lines — the submit command
(`staged: pkit report submit <id>`), the resolved project root (or
`no project — <cwd>`), and the draft store it wrote to — it never posts** (the
deliberate `--yes` asymmetry, per ADR-047: **`--yes` stages, never posts**).
Naming the root and the store is what makes a draft staged in the wrong place
visible at the moment it happens (#693). `--file` is kept as an explicit gesture; the API post is the
default whenever `gh` is authenticated. `--on-behalf-of @login` files under the
invoker's identity with a "Reported for @login" attribution so the beneficiary
still tracks it.

**Project + workstream context** (per [pkit:ADR-050]) rides every composed
report, drafts included: a human context line right under the title
(`Project: <name> · Workstream: <ws>`, missing halves omitted), `project=` /
`workstream=` keys on the body marker, and a ` (<project>)` title
parenthetical when the project is known. Sourcing is **names, never paths**
(the redaction discipline extended — no value is ever derived from a
filesystem path segment, directory basenames included): the project name
comes from the declared `name` key in the adopter-owned
`.pkit/project/config.yaml`; when that key is absent, an **interactive**
`--file` compose prompts once (defaulting to the git remote's repo name
**without** the owner/org — a private org name is itself potentially
sensitive) and offers to write the answer back so future reports skip the
prompt, while draft / `--yes` / no-auth paths use config-then-remote-fallback
silently. No name resolvable ⇒ the body states `(project: not declared)`
instead. The workstream is **asked of the project-management capability** —
its `context-workstream` read verb (current branch → issue → workstream),
invoked by subprocess through the capability dispatcher, so the backbone
never reads pm's `workstreams.yaml` or labels itself; `--workstream <name>`
overrides, and pm-absent / underivable simply omits the half. A successful
post stamps the same pair into the reported scratchpad note's
frontmatter. This context block is the designated extension point for
version provenance (EPIC #411): future provenance fields join the same
line/marker rather than adding a second block.

**`--scratchpad <slug>`** (per COR-043) inlines a scratchpad note — resolved by
slug, filename, or path in `active/` (or `reported/` for a re-send) — into the
composed report as a collapsed `<details>` section titled with the note's filename
+ "(as sent)". The attached content passes a **compose-time redaction lint** on
*every* path, drafts and URL-first included ($HOME, `/Users/…`, `/home/…`, `~/`
home paths — redaction is a property of the payload, not the channel):
interactively a finding prompts **edit-or-send-anyway**; on draft paths findings
ride as warnings with the draft. An **oversized** note (composed body over the
issue-body budget) is sent as an excerpted body **plus ONE overflow comment**
carrying the full as-sent text — one logical send, body and comment shown and
confirmed as a **single gesture** before any post (ADR-047 refinement). If the
issue posts but the overflow comment fails, the send did not complete as
confirmed: **nothing is stamped**, the created issue is named with the
remediation, and the `gh` error is surfaced verbatim. On a **fully-successful
post** the note is stamped `reported` (moved to the lazily-created `reported/`
with refs/date/hash frontmatter) — whether the post came from a direct compose
or from `report submit`; staged and URL paths send nothing and stamp nothing at
compose time. **Tracking fires on every path** (#664, from #660 §C.7): the
staged path stamps at `report submit` exactly as a direct post, and any
scratchpad-backed flow that ends at a URL instead of a post — `--url`,
`--open`, the no-auth fallback, or an API post that degraded to the URL —
**ends with the required follow-up as its last line** (`after filing in the
browser, run: pkit scratchpad reported <slug> <issue-ref>`): the browser
cannot stamp the note, so the exact one-command gesture is handed over
loudly, never left as a hidden step. Every
report verb also prints a one-line warning (never a gate) when a `reported/`
note has been modified since its stamp.

### `report submit [<id>]`

The human half of the agent-stage + human-submit split (#662). A `--yes`
compose stages its full payload — with the compose-time redaction findings as
header warnings — under `.pkit/scratchpad/.report-drafts/` (project-local,
kept out of git by a `.gitignore` the stager drops inside the directory, so no
repo-root ignore edit is needed). The store is **per-project**: a draft is
visible only to a `submit` run under the same root, so every message names the
store path it read (#693) — the listing header, the empty state, and the
not-found error, which adds the resolved root and points at running submit from
the root the draft was staged under (a draft staged elsewhere is invisible here,
not lost). Bare, `report submit` lists the staged
drafts. With an id it loads the staged payload, re-surfaces the redaction
warnings, shows the whole payload (body + any overflow comment), names the
posting identity and target, and posts via `gh` only on an explicit confirm —
then stamps/tracks exactly as a direct post (COR-043) and removes the stage
file. **Interactive-only**: `--yes` is refused, so ADR-047's gate survives the
realization — autonomy stages, only a human posts. A failed post keeps the
draft for retry; an issue created whose overflow comment failed keeps the
draft **only** as the source of the full text and says not to resubmit (the
issue already exists — retry the comment instead).

### `report` (= `report list`) / `report show <N>`

`report` lists the invoker's reports (authored by *or* attributed to them) + states,
one line each — **flat by default**, each row tagged with its project marker
(`[<project>]`, per [pkit:ADR-050]) when the report carries one; `--tree`
expands each feedback with its
`## Tracked by` fixes and their states inline. **Membership requires positive
report provenance** (#681): an issue is listed only when it carries the
`pkit-report` body marker, a `report:*` label, or the on-behalf-of
attribution line — **unioned** with any issue a local `reported/` note
references (how a raw-`gh`-filed report without a marker stays listed).
Title prefixes (`[Bug]`/`[CR]`/`[Feedback]`) and legacy bare kind labels only
classify a member's *kind* — they never make an ordinary tracker issue a
report (that was #681's over-sweep). `report show <N>` adds the maintainer
comments and the `## Tracked by` rollup. **Rollups render title + URL** (#664):
each tracked fix shows its number + state **plus its title and URL** — bare
numbers force a browser round-trip to learn what is fixing you — degrading to
number + state when a ref can't be resolved (offline). Read-only; requires `gh` auth (a
no-auth user tracks via GitHub's own notifications).

**One tracking truth (#664).** `pkit report` (list) and `pkit scratchpad list`
answer different questions and both are honest: `report list` is the
**upstream view** (my reports on the target, recognized by the provenance
rule above), `scratchpad list` is the **note view** (my local notes' reported
state). The declared source-of-truth rule: the **issue** (upstream) is the
truth for *state*; the **note's frontmatter** is the truth for *what was
sent*. They reconcile by derivation, never by a sync mechanism
(derive-don't-store): `report list` tags a row `[note: <slug>]` when a local
`reported/` note references that issue, and `scratchpad list` resolves its
refs' upstream state live — nothing is copied or stored on either side.

### `report inbox` / `report link` / `report unlink` (maintainers)

Enabled **only when the current repo is the configured report target** (the
structural "developers of the target repo" gate; inert elsewhere). `report inbox` lists all incoming feedback for
triage — the same positive-provenance membership rule as the reporter list
(#681; a raw-filed report with neither marker nor `report:*` label is not
inbox-discoverable, since the maintainer has no local notes for foreign
reporters) — each row tagged with its workstream marker (`[<workstream>]`, per
[pkit:ADR-050]) when present; `--kind <bug|feedback|change-request>` narrows to one kind, and
`--group-by project` groups rows by the body marker's `project=` key (reports
without one group under
`(no project)`). `report inbox --resolved` lists open feedbacks/change-requests
whose `## Tracked by` issues are **all closed**, and — **interactively only** —
prompts per report to post a closing comment + close; `--yes` / non-interactive
**lists without closing** (the same never-autonomous asymmetry as the reporter
side's `--yes`), and a close is never automatic. `report link` / `unlink
<feedback-N> <fix-N>` add/remove a `#fix-N` reference
in feedback #N's `## Tracked by` list. These are same-repo edits (no cross-repo gate).
`report link` is the **one** Tracked-by editor: the project-management
capability's `create-issue --from-report <N>` invokes this same verb after
filing a fix (per [project-management:DEC-048-from-report-auto-link]), so the
manual `report link` remains the universal fallback, never a parallel
implementation.

## Standard flags

- **`--help`** on every command, including the root.
- **`--version`** on the root, equivalent to running the `version` subcommand.
- **`--dry-run`** on every mutating command (`init`, `sync`, `merge`, `upgrade`, `capabilities install`, `capabilities register`, `capabilities uninstall`, `capabilities upgrade`, `process new`, `process couple`, `process hand-off`). Shows the plan without applying any changes. On the process stamps it runs every check a real run runs, including the shape lint of the would-be definition, and reports the stubs it would scaffold.
- **`--color {auto,always,never}`** on the root (default `auto`). Colourizes human output via the semantic styling layer (per ADR-011); resolved once at the command boundary. Honours `NO_COLOR`; styling is never load-bearing (plain text carries all structure), so this never changes machine output or piped/redirected output.

## Command output conventions

Human-readable command output (the default read-for-understanding view) follows one shape so every command is consistent and self-explanatory without each author re-inventing layout. Machine output (`--json`, exit codes) is a separate concern. The exemplars are `pkit permissions overview` / `explain` / `profile list`; the shared renderer is `cli_render` (per ADR-006) — read-views should render through it rather than hand-building strings.

**The skeleton** (read-views):

```
<Title — what this is>   (pointer to the sibling view)

  <status banner: current state + glossed config>     # only if there's live state

SECTION — <what it is>
  <aligned rows, widths computed across all rows>

Legend
  <token>   <one-line meaning>                         # only tokens actually shown

Commands
  pkit … <args>   <3–5 word next step>
```

**Rules** (apply to *all* human output, including procedural/step logs like `setup autonomy`, even where `cli_render` doesn't fit):

- **Three zones, marked by typography + whitespace — never horizontal rules.** A view has a Header zone (title + status), a Body zone (sections + rows), and a Reference zone (Legend + Commands / next-steps). Mark boundaries with **header case** + one blank line, not drawn lines: data sections are **ALL-CAPS** with an em-dash gloss (`GUARDRAILS — …`); Reference/advisory zones use **Title-case** labels (`Legend`, `Commands`, `Next — …`, `One-time tip — …`). **No `────`/`====`/`----` rules** — width-ambiguous, alignment-fragile, and louder than the whitespace+typography scheme the field standardises on (gh / kubectl / docker / cargo use no rules).
- **One line per idea.** No multi-sentence headers or footer paragraphs; if a thing needs a sentence it's a Legend entry, not a paragraph. Empty/edge states get one line.
- **Label ↔ gloss is inline-parenthetical.** Put the secondary gloss in parentheses after the value (`Active profile: none   (only your manual grants apply)`); the em-dash carries a count/qualifier (`— 3 available`). Table rows keep the gloss as a *column* (stacking per row breaks alignment). Don't stack a plain indented sub-line as a subtitle — without a styling layer it's indistinguishable from a soft-wrap.
- **Compute column widths** across all rows; never hardcode (fixed widths go ragged on the longest entry). Sections share the width basis so they align.
- **Symbols sparingly:** `—` for glosses, `·` as a separator, `[…]` for tags. Avoid box-drawing and emoji (alignment-fragile, inconsistent across terminals). A command offered as a next step goes on its own indented line so it's copy-paste-obvious.
- **Cross-reference sibling views by name** so the surface is discoverable.
- **Styling is never load-bearing.** Structure must read with zero styling — header case + whitespace + indentation carry all meaning, exactly the plain output. Emphasis (bold/dim, later colour) only *amplifies* what the plain text already says; it never encodes information the plain text lacks. This holds for hand-authored output too, not just `cli_render`: if a reader piping to a file or using a screen-reader loses the meaning, the structure was wrong. The styling layer enforces it mechanically (`strip_ansi(styled) == plain`); hand-authored output owes the same discipline.
- **Author-supplied prose fields wrap through `cli_render.wrap()`.** Hanging-indent of author newlines is unconditional; hard-wrap to terminal width is TTY-only and resolved once at the command boundary (piped is always no-wrap, regardless of `COLUMNS`); long tokens overflow rather than breaking mid-token. The human narrative is porcelain and is **never** a parsed surface — a script reads the `--json` sibling, which never wraps and is byte-stable across TTY / `COLUMNS` / piped. (Per ADR-024.)

A stronger visible break is a *dim* header from the TTY-aware styling layer (per ADR-011): authors tag a semantic role (`heading` / `strong` / `muted`), one gate maps it to bold/dim on a TTY, degrading to plain whitespace when piped / `NO_COLOR` / `--color never` — not a drawn rule.

## Failure mode

The CLI runs forward-only — no transactional rollback across the manifest (see COR-004). If a command fails partway:

1. The project is left at a known partial state.
2. The error message identifies what went wrong and where.
3. Run `validate` to see the full picture.
4. Address the underlying issue and re-run the failing command, or revert the partial mutations through git.

Idempotent commands (`sync`, `merge`, `upgrade`, `validate`, `version`) are safe to re-run. `init` is not — recover via `validate` and targeted commands instead.
