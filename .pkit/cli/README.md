---
variant: specialized
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/cli/**
        - src/project_kit/cli.py
        - src/project_kit/__main__.py
        - src/project_kit/dispatcher.py
        - src/project_kit/router.py
        - src/project_kit/cli_render.py
        - src/project_kit/install.py
        - src/project_kit/sync.py
        - src/project_kit/upgrade.py
        - src/project_kit/merge.py
        - src/project_kit/workspace.py
        - src/project_kit/visibility.py
        - src/project_kit/versioning.py
        - src/project_kit/status.py
        - src/project_kit/validate.py
        - src/project_kit/validators.py
        - src/project_kit/scaffolds.py
        - src/project_kit/decisions.py
        - src/project_kit/scratchpads.py
        - src/project_kit/permissions.py
        - src/project_kit/project_config.py
        - src/project_kit/config_validate.py
        - src/project_kit/docs_roots.py
        - src/project_kit/friction_check.py
        - src/project_kit/friction_repository.py
        - src/project_kit/friction_report.py
        - src/project_kit/friction_write.py
        - src/project_kit/connections_config.py
        - src/project_kit/wiring_graph.py
        - src/project_kit/report.py
        - src/project_kit/report_context.py
        - src/project_kit/environment.py
      record: [COR-004, COR-012, COR-043, COR-048, COR-049, COR-050, PRJ-001, PRJ-003, PRJ-004, ADR-033, ADR-039, ADR-049, ADR-058, ADR-059]
    revalidated:
      at: 2026-09-29T15:15:31Z
      outcome: updated
---

# Command-line interface

project-kit ships a CLI that adopting projects use to install the methodology, pull updates, manage capabilities, and check state. The binary's name is **`pkit`** (per PRJ-001). The CLI is the surface through which project-kit's mechanisms (propagation, extension, suspension) and delivery operations (seed, merge) are exercised against your project — see `.pkit/decisions/README.md` and the COR records in `.pkit/decisions/core/` for the underlying contracts.

The design rules governing the CLI's shape — why these commands exist and not others, why some verbs stay separate — are recorded in `.pkit/decisions/core/COR-004-cli-surface.md`. This document is the spec: what each command does, which flags it accepts, what guarantees it provides.

## Implementation status

The CLI is implemented in Python (per PRJ-003), with `.pkit/cli/pkit` as a thin proxy that exec's the Python runtime via `uv` and bypasses to the adapter's shell scripts for `deploy-skills` / `merge-settings` (which are shell to the bone — primitives the adapter ships, not surface commands).

The full COR-004 surface is implemented: `init`, `sync`, `merge`, `upgrade`, `capabilities install / register / uninstall / upgrade / list / show` (per COR-017 + COR-031; `show` and the install and uninstall plans per COR-053 point 8), `status`, `validate`, `version`, `version bump`, `release plan / apply / merge / publish-notes / check / lint / check-shareable` (per PRJ-002 + COR-041), `new decision`, the authoring commands (`area`, `adapter`, `capability`, `agent`, `storyboard`, `schema`, `migration`), and the scratchpad commands (`new scratchpad`, `scratchpad done`, `scratchpad drop`, `scratchpad reported`, `scratchpad list`) per COR-012 + COR-043. Each authoring command ships paired with its skill under `.pkit/skills/core/` per COR-005's "Skill / command pairing". (The `bundle` command family was retired in COR-027 — capabilities subsumed the bundle role.)

## Installing pkit on PATH

**Recommended (per PRJ-004):** install pkit globally via `uv tool install`:

```
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git
```

After this, `pkit` is on PATH; the binary works against any project-kit-adopting project — the runtime resolves the current project's root from CWD at invocation time (via `git rev-parse --show-toplevel`, with a structurally-validated CWD-walk fallback that skips a broken/vestigial `.git`). Re-installing the kit into more adopter projects does **not** require additional installs of pkit. The kit-owned methodology content is **bundled in the wheel** (version-locked to the binary), so these commands work from the installed binary without a source checkout (per [ADR-033](../../tech-docs/architecture/decisions/ADR-033-official-install-bundles-content.md)). The bundle is defined by *tier ownership*, not by the propagation surface: it carries what the kit owns and withholds the *contents* of the source project's own `project/` tier, so no adopter receives another project's config, activation switches or audit journals. (The few tiers the installer gates its scaffolding on ship as empty directory markers — layout, not data.) The bundle is a *superset* of what sync propagates: it additionally carries capability source, which ships as a distribution medium and is never propagated. The one path on which the two disagreed was a bug in the sync predicate, fixed in #823. A checkout, when present, takes precedence over the bundle, so contributors' source edits stay live.

**One install for everyone — no separate router.** The installed binary is CWD- and pin-aware (per [ADR-039](../../tech-docs/architecture/decisions/ADR-039-pkit-entry-point-router.md)): on every invocation it cheaply picks a route *before* loading the CLI. Inside a project-kit source checkout it runs that checkout's working tree; in an adopter that pins a version (`.pkit/version-pin`, per [ADR-049](../../tech-docs/architecture/decisions/ADR-049-per-project-version-pin.md)) different from the running binary it runs that pinned version under `uvx …@<pin>` (an unresolvable pin degrades loudly to running self, never a hard fail); otherwise it runs in-process. Adopters and contributors therefore share this **single** install — there is no separate shim to put on PATH. Escape hatches: `PKIT_NO_ROUTE=1` forces in-process execution; `PKIT_ROUTED=1` is the internal loop guard the re-exec'd process inherits. On the source-checkout route the router also sets `PKIT_CLI_VERSION` to the checkout's `.pkit/VERSION` so version-provenance reports `cli == tree` (in a checkout the running code *is* the tree, but package metadata can lag a `.pkit/VERSION`-only bump); an explicit `PKIT_CLI_VERSION` in the environment wins, and the other routes leave it unset so a genuine installed-CLI-vs-tree drift still shows.

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
| `capabilities install <name>` | install a *kit-shipped* capability: copy the capability's **kit-owned** subtree from kit source into the adopter, register it, deploy (per COR-017). `--plan [--json]` shows instead what the install would change in the wiring — the connections it would make and break, the role conflicts it would open and how to resolve each, what the capability needs — and writes nothing (see "Discovery" below) | yes (`--plan`: no) | already-installed reports, no re-run |
| `capabilities register <name>` | register + activate an *in-repo (incubated)* capability authored at `.pkit/capabilities/<name>/` — registers in place (no copy), records origin `incubated-in-repo`, then runs the same deploy primitives + dependency gating as install (per COR-031). Skips the "exists in kit source" pre-flight; keeps backbone-version + collision + dependency pre-flights. Idempotent on an already-registered capability: a clean no-op when it is already `incubated-in-repo`, or an *adopt-in-place* origin upgrade (set origin to `incubated-in-repo` on the existing entry, no re-copy/re-deploy) when it was registered `kit-shipped` — including the origin-unset default a manual registration leaves | yes | no-op when already incubated; adopts a kit-shipped/origin-unset entry in place |
| `capabilities uninstall <name>` | remove an installed capability. `--plan [--json]` shows instead what the removal would change in the wiring — fillers lost, processes and other counterparts left without a provider, artefacts whose role blocks would be orphaned, selections left naming it — and writes nothing (see "Discovery" below) | yes (`--plan`: no) | yes |
| `capabilities list` | list capabilities known to this project — kit-source-available plus anything installed — with an `origin` column marking each installed one `kit-shipped` or `incubated` (per COR-031) | no | yes (read-only) |
| `capabilities show <name> [--json]` | a capability's connections, installed or not, from its package metadata alone: the roles it provides, the points it accepts and offers, its extensions, and what would connect here against the live wiring (per COR-053 point 8; see "Discovery" below) | no | yes (read-only) |
| `capabilities refresh <name> [--dry-run]` | regenerate the capability's generated package metadata — `connections.extensions.depends-on` from its process definitions' `depends_on`, marked `generated: true` — leaving the rest of `package.yaml` as written (per COR-053 point 4; see "Regenerating a capability's `depends-on` list" below). Authoring-time; refuses a kit-shipped capability installed in an adopting project | yes | yes — rewrites only a stale list |
| `new area <name>` | scaffold a new area (per COR-011) | yes | no — refuses if area already exists |
| `new adapter <name>` | scaffold a new adapter (per COR-005) | yes | no — refuses if adapter already exists |
| `new capability <name>` | scaffold a new capability (per COR-017); refuses the reserved name `core`, which names the core schemas area (`install` and `register` refuse it too) | yes | no — refuses if capability already exists |
| `new migration [...]` | scaffold a migration script in the right `<major>.<minor>.0/` directory | yes | no — emits a fresh, numbered file each call |
| `new decision <namespace> <slug>` | scaffold a new decision record stub (frontmatter + four sections + next number in namespace) | yes | no — refuses if a record with that slug already exists |
| `new agent <namespace> <name> [--with-storyboard]` | stamp an agent stub in `core`, `project` or a capability's `agents/` folder (per COR-013 + COR-015; see "Authoring commands") | yes | no — refuses a name already taken in core, project or any capability |
| `new storyboard agent <name> [--namespace <ns>] [--scenario <slug>]` | stamp a storyboard beside an agent, wherever it lives (per COR-016; see "Authoring commands") | yes | no — refuses if the storyboard already exists |
| `new scratchpad <slug>` | stamp a new active-state scratchpad note (per COR-012) | yes | no — refuses if the slug is already in use across any state |
| `scratchpad done <slug> [--produced <ref>...]` | move a note from `active/` (or `reported/`, removing that lazy directory when it empties) to `done/`, append `retired`/`produced` to frontmatter | yes | no — refuses if no active or reported note matches |
| `scratchpad drop <slug>` | move a note from `active/` (or `reported/`) to `dropped/`, append `retired` to frontmatter | yes | no — refuses if no active or reported note matches |
| `scratchpad reported <slug> <ref>...` | manually stamp an active note as sent through the report channel: move to lazily-created `reported/`, append `reported`/`reported_to`/`reported_hash` frontmatter (per COR-043; the automatic stamp happens on a successful `report` post — this gesture covers URL-first posts and retroactive marking). Refs are `owner/repo#N` or GitHub issue URLs (normalised) | yes | yes — appends refs to an already-reported note; duplicate refs are a no-op |
| `scratchpad list` | list notes by state; reported notes resolve their refs' upstream state **live** via `gh` (pull-only, never stored; offline degrades to `state unknown`), flag divergence from the stamped hash (`modified since reported`), and print a retire prompt when every ref is closed — never auto-retiring (per COR-043) | no | yes (read-only) |
| `status` | show how project-kit is wired in this project (paths, installed backbone version vs source, adapter, deployed skills, capabilities, rule-set pins behind their inherited set, the resolved connections per role and per point, data points, decision counts) | no | yes (read-only) |
| `validate [--only <name>]... [--skip <name>]...` | run every registered validator — the backbone's twelve members and each installed component's — grouped by functionality through one renderer; exit non-zero on errors only (ADR-058) | no | yes (read-only) |
| `schemas validate [<path>]` | validate the schema YAMLs in the core schemas area (`.pkit/schemas/`) and every installed capability's `schemas/` against their JSON Schema companions + cross-file refs | no | yes (read-only) |
| `decisions validate` | detect duplicate decision ids within an id-space (core / project / ADR / per-capability DEC) + id-vs-filename mismatches, and a rule id (`RS-<SET>-NNN`, COR-051) claimed twice across the rule sets; exit non-zero on any | no | yes (read-only) |
| `data validate <path>` | validate adopter data files against their bound capability schemas (per COR-023); resolves binding field-first via `pkit_schema:`, then via per-schema `binds_to:` fallback | no | yes (read-only) |
| `friction check [--base <ref>] [--json]` | the friction change check (COR-050): every artefact whose anchor changed — working tree against the merge-base of `<ref>`, default `origin/main` or `$PKIT_CHECK_BASE` — carries an answer (updated, unchanged, deferred); reports friction, bumps with nothing behind them, dead anchors of the change and an outdated base, upstream first; `--json` for other components; exits 1 only in enforcing mode. See "Friction checks" | no | yes (read-only) |
| `friction check --all [--json]` | the whole-repository friction check (COR-050 point 6): every artefact at HEAD against the current history, each anchor judged from the artefact's revalidation point — derived from git, renames followed — and each deferral from its deferral point; reports stale and deferred debt with their origins, every dead anchor, over-broad anchors, unanchored artefacts and uncovered surface, upstream first; needs the full history and says so in a shallow clone; exits 0 in either mode. See "Friction checks" | no | yes (read-only) |
| `friction debt [--json]` | the friction debt listing (COR-050 point 9): exactly the stale and deferred findings of the whole-repository check, oldest first by the author date of their origin, each with its kind, artefact, anchor, origin commit, author, date and change, and a deferral's reason; artefacts a shallow clone cannot judge are named apart; exits 0. See "Friction checks" | no | yes (read-only) |
| `friction explain <artefact> [--json]` | explain one artefact's friction (COR-050 point 13): its anchors, its revalidation and deferral points, what changed since each — every changed anchor with the commits behind it — and, for each finding the whole-repository check reports on it, what clears it: the writer command giving the answer (`revalidate … --outcome …`, `defer … --anchor … --reason …`) or the edit it needs. See "Friction checks" | no | yes (read-only) |
| `friction artefacts [--json]` | the places and the artefacts artefact discovery finds (COR-050 point 1), from the one discovery `pkit validate` reads: each declared place — the project's and each capability's, with its location and root — the files it matches and the skips validation applies (a synced copy, a place outside the repository, a malformed declaration), every file read with its front matter's own fields, and every artefact; `--json` is the stable document a capability's own script reads instead of walking the places. Exit 1 when the configuration cannot be read. See "Friction checks" | no | yes (read-only) |
| `friction revalidate <artefact> --outcome <updated\|unchanged> [--because <text>] [--keep <anchor>]... [--yes\|--dry-run]` | write an artefact's revalidation (COR-050 point 3): a fresh `at`, the outcome, and for `unchanged` an `unchanged-because` that must differ from the one written; re-states the deferrals kept (each named with `--keep` or confirmed at the prompt) and removes the rest. Rewrites the `revalidated` block and nothing else in the file; writes only with consent. See "Friction checks" | yes | no — `at` moves on every run |
| `friction defer <artefact> --anchor <anchor> --reason <text> [--yes\|--dry-run]` | defer one anchor the artefact carries (COR-050 point 4): add its entry to `deferred`, kept sorted, or reword the reason of the entry already there; never touches `at`. Writes only with consent. See "Friction checks" | yes | yes — the same reason is a no-op |
| `friction record-status <artefact> [--yes\|--dry-run]` | record the whole-repository check's state of the artefact at HEAD in its tool-written `last-check` (COR-050 point 10), only when the state changes; the command an after-merge job would run (the job is not shipped). Writes only with consent. See "Friction checks" | yes | yes — no-op while the state holds |
| `agents` | report which kit-shipped agents will deploy vs. be skipped — and why, per COR-013. An agent is skipped only when it references an overlay category `.pkit/agents/project/overlay.yaml` doesn't define through a **hard** channel (`owns`/`needs`/`answers`/`reads.paths`/`reads.records`); a category referenced *only* via `reads.patterns` is an **optional** read (ADR-052) whose absence never skips — the agent deploys without it, and the undefined optional categories are surfaced in their own footer state (`Optional \| N categor(ies) undefined \| agents deploy without them`) rather than as a skip cause. Each row also shows the agent's **effective model and effort** (`model inherit`, `effort high (overlay)`) — the overlay's `overrides.<agent>` value, else the front matter's, else `inherit`; a value the harness does not accept is shown refused (the deploy drops it and the agent inherits). Deployment itself happens in `sync`; this is the diagnostic | no | yes (read-only) |
| `agents reconcile [--write]` | surface referenced-but-undefined overlay categories into `overlay.yaml` as commented stubs (explicit; `sync` never mutates the seeded overlay). Dry-run by default | yes (with `--write`) | yes — idempotent (skips already-present categories) |
| `config set <key> <value> [--yes]` | set one backbone-owned key of `.pkit/project/config.yaml` (dotted, e.g. `docs.internal`) through the consent-gated writer (COR-048 point 5): the key must exist in the configuration schema and hold a single value, the result is validated before anything is written, the reserved `project` block is refused. Asks once on a terminal; `--yes` consents non-interactively; without either it refuses and names the command to run. See "Configuration file" | yes | yes — same value, same file |
| `permissions explain [<agent>]` | render the per-agent permission mental model — grants, scopes, effects (per COR-028) | no | yes (read-only) |
| `permissions diff [<agent>]` | reconcile the model against live `.claude/settings.json`: flag live rules no granted privilege justifies + dimensions the harness can't natively enforce | no | yes (read-only) |
| `permissions catalog` | list the privilege catalog (baseline + extensions); a path-scoped allow (the agent workspace) shows the folder it is recognized inside | no | yes (read-only) |
| `permissions overview` | role-grouped catalog view — guardrails vs enablers, provenance, granted-to, live-enforcement status; a path-scoped allow is marked `[inside <folder>/]` | no | yes (read-only) |
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
| `permissions diagnose report` | print the classified, frequency-ranked, **recommend-only** report over the captured log: groups by command shape (interpreter / shell-shape / egress / allowlist-gap — taxonomy in code, not the record), ranks by frequency within action bands (recommend / judgement / document), and emits a recommended remediation per group. A file-tool deferral whose target is the agent workspace goes first, in a `workspace` group under its own **DEFECTS** band: every agent is granted the workspace for the file tools, so a prompt there is a defect to report, never an allowlist gap (permissions README, "A prompt for the agent workspace is a defect"). Applies **nothing** (auto-fix is deferred; a new catalog privilege is never auto-fixable). The captured signal is a SUPERSET of real prompts (the hook sees its own deferral, not whether the harness prompted), so counts are stated as **coverage**, not a predicted prompt decrement | no | yes (read-only) |
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
| `release merge <pr> [--dry-run]` | merge a release PR (the sanctioned path for a `chore(release):` PR that closes no issue) — guarded to `release/*` heads, merges only an open/mergeable/green PR as one squash commit whose subject is the PR title, head branch deleted on merge; does not tag (`release-tag.yml` tags post-merge); see `.pkit/release/README.md` | yes | no — merges a PR |
| `release publish-notes <version> [--dry-run]` | publish a **notes-only** GitHub Release for tag `v<version>` (body = that version's `CHANGELOG.md` section) so the release page shows what changed — idempotent (updates if it exists), **no artifact** (a notes overlay on the tag install path, PRJ-004), repo from the ambient `gh` context; `--dry-run` prints the notes without calling `gh`; see `.pkit/release/README.md` | no (publishes a Release) | no — calls `gh` |
| `release check --base <ref>` | CI guard: fail a PR whose surface change ships no changeset (escape hatch: `none` changeset / `skip-changeset` label) | no | yes (read-only) |
| `release lint` | format lint of the OBJECTIVE changeset + `CHANGELOG.md` subset (category enum, body shape, changelog heading structure); a reminder not a proof (escape hatch: `--skip` / `PKIT_CHANGELOG_LINT_SKIP`) | no | yes (read-only) |
| `release check-shareable <component>` | pre-sharing lint: is a capability ready to be consumed externally-sourced (COR-041)? Checks it declares a `version`, a well-formed `package.yaml` manifest, and a bounded `requires_backbone` range; warns on cheaply-detectable local-only assumptions. Reports pass / the specific gaps; project-neutral (any component by name). Like the rest of the `release` group, inspects the component in the working-directory project, not the checkout that owns the `pkit` binary; see `.pkit/release/README.md` | no | yes (read-only) |
| `process health [--process <addr>] [--interpretation-only] [--json]` | walk every opt-in hand-off contract (COR-042) and report missed hand-offs; report-only, takes no subject; exits non-zero on any miss or indeterminate. A `--process` scope that matches nothing walked is itself indeterminate (never a clean empty run); a bare run over zero declared contracts stays clean. `--interpretation-only` re-renders the same walk as the COR-044 authoring check: indeterminates only, misses not counted, exit non-zero on any indeterminate | no | yes (read-only) |
| `process new <capability>:<process-id> [...] [--dry-run]` | scaffold a lint-clean process definition into its NAMED owning capability + a fail-closed predicate stub per declared evaluable, registered in the capability's package.yaml (COR-044); errors cleanly with no owning capability, or one the project does not register as a component (`pkit capabilities register <name>`) | yes | no — one-shot, refuses an existing id |
| `process couple <addr> --state <s> --upstream <addr> --relation <r> --mode <m> --why <prose> [--version <n>] [--mandatory <reason>] [--dry-run]` | append a `depends_on` entry (COR-038) to the invoker-named definition; the upstream by implementation or by role (COR-053), with the targeted interface version and the mandatory mark when given; relation/mode validated against the closed vocabularies read from the shape contract; definition `version` NOT bumped; names `pkit capabilities refresh <capability>` when the generated `depends-on` list is left stale, never writing package metadata | yes | yes — identical entry is a clean no-op; the same `(upstream, relation, mode)` with a different `why`, version or mark refuses |
| `process hand-off <addr> --upstream <addr> --trigger <state> --candidates <cmd> --resolve <cmd> [--state <s>] [--dry-run]` | add a COR-042 hand-off contract to an existing coupling; validates the trigger against the upstream where resolvable; scaffolds + registers the seam stubs when new; `version` NOT bumped | yes | yes — identical contract is a clean no-op; a different contract refuses |
| `process graph [filters and presets] [--flow \| --mermaid \| --json] [--verbose]` | render the configured process topology (COR-038): the one wiring graph filtered to its process edges — derived, annotated, and the resolved `offers` edges — narrowed by atomic filters and presets. See "Connections commands", the graph relation | no | yes (read-only) |
| `connections graph [--kind <kind>]... [--flow \| --mermaid \| --json] [--verbose]` | render the one wiring graph (COR-053 point 7): the process definitions' derived and annotated edges with the wiring resolver's data, event and offered-process edges, in the process graph's format; `--kind` narrows to `data`, `process` or `event`. See "Connections commands" | no | yes (read-only) |
| `connections providers set <role> <capability> [--yes \| --dry-run]` | select the provider of a role: write `connections.providers.<role>` through the consent-gated writer, after checking the capability is installed and declares the role; the diff first, `--dry-run` stops there. The fix a role conflict names. See "Connections commands" | yes | yes — the same selection writes nothing |
| `connections resolve <address> [--json]` | resolve one data point (COR-052) and print it: its value — a `single` point's answer, or the entries of a `union` or `additive` point with their origins — how it resolved or why not, and every filler considered; `--json` is the stable document a capability's own script reads. Exit 1 when the point does not resolve or nothing defines it. See "Connections commands" | no | yes (read-only) |

## Lifecycle commands

### `init`

Runs first install in this order:

1. **Propagation** — every path in the synced manifest is written into the project's `.pkit/` tree.
2. **Seed** — every path in the seed manifest is written once with its template content.
3. **Merge** — every declared merge target is merged with its core baseline (per COR-002's two-tier contract).
4. **Agent workspace** — creates `.agent-workspace/` at the project root and adds the line `/.agent-workspace/` to the repository's local exclude file, `<git common dir>/info/exclude`, so the intermediate files agents keep there never reach a commit (the workspace rule in `rules/core.md`; the permission model grants the folder to every agent — see `.pkit/permissions/README.md`, "The agent workspace"). The exclude file belongs to the clone and is never committed, so it is not one of the merged fixed-path files of COR-002: the entry is appended directly, no other line is touched, and a line already naming the folder (with or without the leading `/` or trailing `/`) counts as present. Because the entry goes in the *common* git directory, one line covers every worktree of the clone, each at its own root. Outside a git repository the folder is created and the exclusion skipped with a note. A symlink where the folder belongs is refused, never adopted: the permission grant would follow it to wherever it points. The local exclude covers this clone only. The project's committed `.gitignore` is the adopter's file, which pkit never writes (ADR-009; `rules/core.md`, the rule that fixed-path config files change only through the merge primitive), so `init`'s closing next steps recommend adding `/.agent-workspace/` there — the line that covers every clone, including one that never runs `init` or `sync`; skip it when keeping pkit private (`pkit visibility private`).
5. **Query-command environments** — for every command a registered component declares with `query-contract: true` whose script carries inline script metadata, resolves the script's environment once, online, into uv's cache (`uv sync --script`, which never runs the script), so the command answers when `pkit validate` runs it offline. One line per command: `provisioned`, `unchanged … already provisioned`, `skipped … nothing to provision`, or `warning … not provisioned` with uv's reason — a warning, never a failure, so `init` and `sync` work offline. The lifecycle README's "How dependencies are provisioned before an offline run" is the reference.

**Announce-and-confirm gate (issue #780).** `init` does not install silently at whatever the resolver picks — the target can be a git root or install-marked ancestor well above where you are standing. Before installing it:

- **Announces on every run** — including the happy path — the resolved install target, *why* it was chosen, and any real project-kit install (a `looks_like_pkit_install` match, not a bare `.pkit/`) found between your current directory and the target or at it. The reason is one of: your current directory **is** the git root (install here); a git root **above you** (that root is the target; `--here` is refused); a structurally-real repository git **could not verify** — dubious ownership / `safe.directory` (init refuses and guides you to `git config --global --add safe.directory …` or an explicit target — or, when that repository is already a project-kit project, to the `safe.directory` fix and then `pkit sync`); a structurally-real repository git **cannot open** for any other reason — a corrupt `HEAD`, a dangling worktree pointer (init refuses, reports it as broken rather than as an ownership problem, and points you at `git -C <path> status`, repairing or removing that `.git`, or an explicit target — or, when that repository is already a project-kit project, at repairing the `.git` and then `pkit sync`); an **already-adopted** project-kit install above you (init refuses and redirects to `pkit sync` — never an install target); or a fresh **non-git folder** (install here). A vestigial `.git` — an empty directory, or one missing `objects/` or `refs/` — is skipped by the validated walk, never offered as a root.
- **Confirms before installing anywhere other than your current directory**, and before creating a standalone install in a fresh non-git folder. On an interactive terminal it prompts; on a **non-interactive / piped stdin it refuses** rather than auto-confirming (a piped `yes |` no longer silently installs somewhere you did not expect). An absent or closed stdin counts as non-interactive. **Declining the prompt exits non-zero** (`Aborted!`, exit 1), so a chained `pkit init && …` stops rather than running on as if the install had happened. For an **off-CWD** target (a git root above you) the non-interactive remedies are `pkit init --root <that root>`, or running `pkit init` from the root — a bare `--yes` will not install there, and `--here` is refused in a subfolder. For a target that **is** your current directory (a fresh non-git folder), `--yes` accepts the offer, and `--here` installs in the current directory.
- **Refuses an off-target split-brain**: if an install sits between your current directory and the resolved target but the target itself has none, installing there would leave two installs straddling your current directory. `init` refuses and names the existing install. That install is shadowed — every command resolves to the git root, so neither `pkit sync` nor `pkit init` reaches it — and the refusal names `pkit init --root <target>` to install at that target anyway.
- **Refuses to re-run when the target is already a project-kit project** — `init` is one-shot, not idempotent (COR-004): it exits non-zero, names the project, and points you at `pkit sync` to refresh kit-owned content. The refusal fires before any confirm, so you are never prompted for an install that could not proceed anyway.
- **Refuses a `.pkit` at the target that is not a project-kit install** — a leftover or partial `.pkit/` with neither `manifest.yaml` nor `decisions/`, or a file at that path. `init` never installs over it and `pkit sync` cannot adopt it, so the refusal says what is wrong and tells you to move it aside (or delete it), then re-run the same command. Like the already-adopted refusal, it fires before any confirm.

Every refusal's suggested remedy is one the same invocation accepts: where a refusal names a command, running it from where you stand gets past that refusal. `pkit sync` has no `--root` — it refreshes whichever project it resolves from the current directory — so a redirect to it is phrased for where you ran `init`: a bare `pkit sync` when you are inside that project, and `cd <project> && pkit sync` when you are not (typically after `--root` named a project elsewhere).

Flags:

- **`--here`** installs into the current directory instead of a resolved parent. **Honored** when the current directory is a git root or a non-git folder (no git-root-wins precedence overrides your current directory, so a `.pkit/` here is reachable). It is stopped by three guards: **refused when the current directory is a subfolder of a git worktree** — every command there resolves to the git root, so a subfolder `.pkit/` would be unreachable, and `init` points you at the git root instead (or at `pkit sync`, when that root is already a project-kit project); **refused when the current directory is inside an existing project-kit project** — a second, nested install is not supported, and `init` names the enclosing project and points you at `pkit sync`; and it **does not override the dubious-ownership or broken-repository guards** — if the current directory is a real git repository git declines to vouch for (`safe.directory` / dubious ownership) or cannot open, `init` refuses and guides you to fix the tree first, `--here` included. Mutually exclusive with `--root`.
- **`--yes`** accepts the confirm only when the resolved target **is your current directory** (a fresh non-git folder). It never installs at an off-CWD target — a bare `--yes` from a subfolder refuses and points you at `--root`, so a non-interactive run can never install somewhere you are not standing.
- **`--root <path>`** installs at an explicit, existing path — the sanctioned way to install at a resolved parent (e.g. a git repository root) non-interactively in CI, where a bare `--yes` is refused. Mutually exclusive with `--here`; a nonexistent path is refused at the CLI boundary rather than silently materialised. Because you named the target explicitly, it **skips the confirm and the between-you-and-the-target split-brain scan** the other paths apply — but not the checks on the target itself. It refuses a target that is already a project-kit project (redirects to `pkit sync`), and it refuses a **shadowed** target: a subfolder of a git worktree (the nested `.pkit/` would be unreachable — every command resolves to the git root; the refusal names `--root <git root>`, or `pkit sync` when that root is already adopted) or a path inside an existing project-kit project (a second, nested install). When the target is itself a repository git **refuses to verify** (dubious ownership) or **cannot open**, `--root` is the escape the guided refusal names, so it installs — but warns first, naming the problem (and, for dubious ownership, the `safe.directory` remedy).
- **`--dry-run`** previews what would be installed without writing any files or prompting (per COR-004). It skips only the confirm prompt and the non-interactive-stdin refusal that stands in for it; **every other refusal fires ahead of `--dry-run`**, so those combinations report the refusal rather than a preview: `--here` together with `--root`; the dubious-ownership and broken-repository refusals; a nested or shadowed target (`--here` in a git subfolder or inside an existing project, `--root` at a subfolder or inside an existing project); an already-adopted target, or a `.pkit` there that is not an install; the off-target split-brain; a bare `--yes` at an off-CWD target; and the install's own source checks (no usable methodology source, or a target that is the source itself).

If you arrive at a partial or broken state, run `validate` to see what is and isn't consistent, then use targeted `sync` / `merge` to recover.

### `sync`

Re-runs propagation only. Pulls current canonical core content into your project's `.pkit/` tree. Does **not** invoke seed (one-shot only — see COR-001) or merge (separate consent profile — see COR-002 and COR-004). Idempotent: re-running with no changes pending reports "current" and exits cleanly.

**Agent workspace.** Sync runs the same workspace step as `init` (step 4 above) — self-host included — so a project installed before the workspace existed, or one whose folder or exclude entry has gone missing, gets them back. It creates only what is missing and reports each part `unchanged` otherwise.

**Query-command environments.** Sync runs the same provisioning step as `init` (step 5 above) — self-host included, after the capability refresh — so a fresh clone, a CI runner, or a project whose capability just gained a query command is ready for an offline `pkit validate`. A command that already resolves offline is reported `unchanged … already provisioned` and nothing is fetched; one that cannot be provisioned is a warning and the sync still completes. Run `pkit sync` on checkout in a pipeline, before its gate.

**Capability downgrade guard (`--force`).** When sync reconciles an installed kit-shipped capability against its kit source (auto-upgrade per COR-017), it compares the source version to the installed version of record (the per-component `manifest.yaml`, falling back to the installed `package.yaml`). If the source is **older** than what's installed — the sign of a stale or mis-pinned source — sync **refuses** that capability's refresh, printing a `refused` line naming both versions, and leaves the installed tree untouched rather than silently downgrading it. Pass **`--force`** to override: the downgrade then proceeds, but a loud `downgrade` line records the deliberate overwrite. A source version equal to or newer than installed refreshes normally, unaffected by the guard. (This is the fix for issue #524, where a stale source silently overwrote a newer committed capability tree.)

On **self-host** (project-kit itself, where the source *is* the installed `.pkit/`), propagation would copy files onto themselves — so `sync` skips propagation and runs only the adapter deploy primitives instead, re-wiring the harness (`.claude/` agents, skills, settings, CLAUDE.md) from the source you just edited. This is the self-host way to apply source edits to the harness; you don't (and can't) `sync`/`upgrade` project-kit onto itself otherwise. (The downgrade guard reconciles capabilities, which self-host skips, so it never fires there.)

**Refused in the methodology's source repository when the running code is not its own** ([ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md)). Self-host is recognised by sync's test: the project is the parent of the methodology tree the running code resolves. The entry-point router makes that the normal case, because in a source checkout it runs that checkout's own dispatcher. A run that misses the router's source-checkout route reaches the checkout with other code — an installed release, or another checkout's — and sync's test then says no while the checkout's marker (the package source beside its `.pkit/`) still says source. Propagating would copy that code's tree over the source it is built from, so `sync` refuses: it exits non-zero, writes nothing, names both tests, and says how the run got there — routing bypassed with `PKIT_NO_ROUTE=1` (by hand, or by a `pin` to a newer release or a pinned `upgrade`, which run that release's `upgrade` this way), routing suppressed by an inherited `PKIT_ROUTED=1`, a dispatcher that is present but not executable, a dispatcher that has been deleted, or a start that never went through the router. The dispatcher is not a marker, so a checkout that has lost it is still the source — the router's warning says the checkout "carries the methodology's package source but no dispatcher" and names `git checkout -- .pkit/cli/pkit` — never an adopter to propagate over. **Nothing overrides the refusal** — not `--force` (which overrides only the capability downgrade guard), not `--dry-run`, not the bypass, which is itself a way in: the situation is a defect to repair, not a choice. The remedy is to run the checkout's own code, `.pkit/cli/pkit sync` from its root, after restoring the dispatcher's executable bit or the dispatcher itself if that was the cause.

### `merge [<target>...]`

Re-runs merge against one or more declared merge targets, or against all targets if no argument is given. Honours the two-tier (auto-add / prompt-once) contract from COR-002. Idempotent.

Use this when you want to pull baseline updates for a single fixed-path config file (e.g., `.claude/settings.json`, `.gitignore`) without invoking other operations.

### `upgrade`

Compares the version of the core layer recorded in your project against the version this CLI was built from. Runs any pending migrations in order, then runs `sync`. Refuses to proceed if your project's recorded version is ahead of the CLI's (and tells you so).

It also **updates the pkit tool itself** when it is stale (per [ADR-044](../../tech-docs/architecture/decisions/ADR-044-upgrade-self-update-detect-instruct.md), amended): it queries the release source for the latest tag and, when the installed `pkit` is behind, runs **`uv tool install --force …@v<latest>`** and **re-runs the upgrade under the new version** — one seamless command, no manual step. It **degrades to just printing the command** (the old behaviour) when the session is non-interactive (no TTY, so a network install is never forced under automation), when `--no-self-update` is passed, or if the install fails/is declined (the sandbox gates a global-binary mutation) — it never bricks. Run **outside any project**, `pkit upgrade` performs this tool update alone instead of erroring on a missing project — and "outside" is judged honestly: a `.pkit/` ancestor counts as a project root only when it looks like a real install (`manifest.yaml`, or `decisions/` for pre-manifest installs), so a stray junk `~/.pkit/` never makes upgrade resolve your home directory as the project. This is safe because pin-by-default insulates projects from the global tool — updating it never disturbs a pinned project (which runs its own version via the router's `uvx` re-exec). When the tool is current it says so; any lookup failure (offline, timeout) warns and continues; it never runs in a source checkout (the next paragraph).

On **self-host**, there is no backbone to upgrade (the source is the installed state), so `upgrade` short-circuits to the self-host `sync` above — re-running the deploy primitives — rather than attempting a version transition. In a source checkout run by code that is not its own, `upgrade` **refuses** exactly as `sync` does (see [`sync`](#sync)), and does so right after that self-host check — before the pinned-project branch, the tool update, and the bypass that skips the tool update — so a release's `upgrade` bootstrapped by `pin` or a pinned `upgrade` refuses too. No flag overrides it.

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

Per [ADR-049](../../tech-docs/architecture/decisions/ADR-049-per-project-version-pin.md), a project opts into running a fixed pkit version by committing a **`.pkit/version-pin`** directive — a plain one-line text file holding a version number. It is **project-owned and never kit-synced**: `init`, `sync`, and `upgrade`'s content pass never write or clobber it; only the gestures below do. Its *presence* is the opt-in signal — the router reads it and re-execs `uvx project-kit@<pin>` so the pinned version serves every command, and a global-tool upgrade no longer moves this project. Absent the file, nothing changes: the router runs the installed binary as-is. This is the lockfile model (`.python-version`-style): you *write* a pin, then separately *raise* or *remove* it.

- **`pin [<version>]`** — write the directive. VERSION is a **version number only** — `1.145.0`, or `v1.145.0` (a single leading `v` is stripped). Branch, commit-sha, and pre-release / build-metadata pins are **refused** (the command exits non-zero and writes nothing): the router can only route a bare `v<semver>` tag, so those are deferred to a later router change. Both forms **require `.pkit/manifest.yaml`** (the project's recorded content version); run `pkit sync` first if it is absent.
  With **no argument** it freezes the project at its current *content* version (`.pkit/manifest.yaml`'s `backbone_version`) — the common case: lock this project where its content is (so no-arg `pin` == `pin <current-content-version>`). Freezing at the content version, not the installed binary's version, avoids baking in a code-vs-content mismatch when the tool is ahead of synced content. With a **`<version>`** token it dispatches on how that version orders against the content version:
  - **equal** → freeze in place (write the pin, no content sync);
  - **newer** → reconcile content forward to the target *under that version's own code* (`uvx project-kit@v<version>`, run under the `PKIT_NO_ROUTE=1` bypass so it doesn't route-loop) — this syncs content + runs the forward migrations — then flips the pin **last**, so a failed reconcile never advances the pin past content that isn't in place. This ordering keeps the pin from ever getting ahead of content; it is not one atomic transaction — an interrupted raise is recovered by re-running (idempotent);
  - **older** → **refused**. pkit migrations are forward-only (COR-010), so there is no safe content-sync back to an earlier version; the command exits non-zero, writes nothing, and touches no content. To roll a project back, `git checkout` the `.pkit/` tree at a commit that carried the earlier version (`git checkout <ref> -- .pkit/`) — git restores kit-owned *and* project-owned state together, atomically (this also reverts `.pkit/version-pin` itself, and only restores a state that exists in history), which a forward-only content sync cannot. There is deliberately no `--force` override.
- **`upgrade`** — raise an existing pin forward to the latest release, automatically and with no `uv` step (see the pinned-project note under [`upgrade`](#upgrade) above).
- **`unpin`** — remove the directive; the project reverts to floating on the installed binary. Idempotent — fine to run when no pin is present.

**`pin` is refused in the methodology's source repository** ([ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md)), both forms, before anything is read or written: a pin is meaningless in the methodology's source, because the router's source-checkout route runs the checkout's own code before any pin is read — and, when it cannot exec the dispatcher, falls back to the running binary, never to a pin. `pin` normally runs under that route, so sync's test recognises the source; the refusal also fires where only the checkout's markers do, since a `pin <newer>` there would run a release's `upgrade` over the checkout. To move a source checkout to another release, update it with git — its `.pkit/` moves with its code.

### Capabilities — two ways in

A capability enters a project through one of two verbs, distinguished by where the capability was authored (its *origin*, per COR-031):

- **`capabilities install <name>`** — for a **kit-shipped** capability. The capability ships in the kit source; install copies its **kit-owned** subtree into the adopter's `.pkit/capabilities/<name>/` — the adopter-owned `project/` tree arrives empty, since the source's own `project/` content is that project's state rather than a template — registers it (origin `kit-shipped`), and deploys its skills/agents. `sync` thereafter reconciles it against the kit source (auto-upgrade per COR-017).

- **`capabilities register <name>`** — for an **in-repo (incubated)** capability the adopter authored in *its own* repo at `.pkit/capabilities/<name>/`. Because the working tree *is* the source, register performs **no copy**: it records the capability in install-state with origin `incubated-in-repo`, then runs the *same* deploy primitives and dependency gating an install runs, so the capability's skills/agents land in the harness exactly as a kit-shipped one's would. `sync` thereafter **skips source-reconciliation** for it — there is no kit source to reconcile against, and the files are adopter-owned (the no-shared-files invariant) — so a home-grown capability survives `sync` untouched instead of being flagged "no longer shipped" or refreshed from an empty source.

**The in-repo activation flow.** Scaffold a capability with `pkit new capability <name>` (or hand-author the subtree), build it out under `.pkit/capabilities/<name>/`, then run `pkit capabilities register <name>`. Register applies every pre-flight an install does *except* "exists in kit source" (the in-repo tree is the source): it checks backbone-version satisfaction, runs the COR-030 dependency gate, and refuses on a naming collision against *other* installed content (the capability's own artifacts are not collisions against themselves). Origin is the only thing that differs between the two paths — participation, deploy, and dependency edges are identical (COR-031 D1). `capabilities list` and `pkit status` mark each installed capability's origin so an incubated one is visibly distinct from a kit-shipped one.

**Adopting an already-registered capability.** `register` is idempotent, branching on the recorded origin (COR-031 D2). If the capability is already registered as `incubated-in-repo`, register reports a clean no-op and returns. If it is registered `kit-shipped` — including the origin-unset default that the old manual-registration workaround leaves behind (an absent origin reads back as `kit-shipped`) — register *adopts it in place*: it re-runs the applicable pre-flights (self-consistency, backbone-version, dependency), sets `origin: incubated-in-repo` on the existing registry entry, and reports the change. It does **not** re-copy the subtree (already in place) or re-deploy — this is an origin-state upgrade, not a fresh install — so it is the supported path to protect a manually-registered home-grown capability from `sync` reconciliation. `--dry-run` shows the adoption without writing. (`upgrade` cannot do this: it refreshes deploy but never changes origin.)

**When the same name also ships from kit source (collision — graduation arriving unbidden).** If a capability you register (or adopt) at `.pkit/capabilities/<name>/` *also* exists in the kit source, `register` keeps/adopts the **in-repo (incubated)** copy and **surfaces a note** that a kit-shipped version is available — it never silently shadows either tree. This is the operational precedence for COR-031's collision boundary: the adopter's local copy is the one installed, and `sync` leaves it untouched (D1) — it is the only copy of the adopter's work — while the kit-shipped version is neither installed nor reconciled against; its existence is surfaced so you *know* it is there (COR-031 reserves incubated→kit-shipped **graduation** for a later decision). If instead you want the *kit-shipped* copy of a colliding capability — e.g. your local one was an abandoned experiment — that reverse preference is a known limitation; for now, remove the in-repo copy and run `pkit capabilities install <name>` to take the kit version.

If a same-named capability later begins shipping from kit source (graduation, before graduation is specified), `register` surfaces the overlap as a note and registers the in-repo copy; `sync` surfaces the same collision rather than silently shadowing either tree (COR-031 boundary case).

**Refused in the methodology's source repository when the running code is not its own** ([ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md)). `capabilities install`, `capabilities upgrade` (which refreshes an installed capability from source) and `capabilities register` copy or register a capability with the running code's tree. In a source checkout reached by other code they refuse exactly as [`sync`](#sync) does, with the same message — both tests, how the run got there, `Nothing was written, and no flag overrides this refusal` — before any other pre-flight, `--plan` and `--dry-run` included. The remedy names the command as it would be re-run under the checkout's own dispatcher, `.pkit/cli/pkit capabilities install <name>` and so on.

**Query-command environments.** `capabilities install`, `capabilities register` and `capabilities upgrade` end, after deploying the capability, with the provisioning step `init` and `sync` run (see [`sync`](#sync)), scoped to that capability: each query command it registers is resolved once, online, and reported with the line `sync` prints — `provisioned`, `unchanged … already provisioned`, `skipped`, or a `warning` that never fails the command. An offline `pkit validate` then answers for it without a `pkit sync` first. Other components' commands are left to `sync`, and `--dry-run` provisions nothing.

### Mandatory process connections: refused, or warned and forced

A process definition's `depends_on` entry may be marked mandatory, with a reason ([COR-053](../decisions/core/COR-053-connection-points.md) point 6; the process area README, "depends_on"). The lifecycle commands read the mark from the capability's generated `depends-on` list and judge it through the wiring resolver, with COR-030's direction split (the lifecycle README, "Mandatory process connections"):

- **`install`, `register`, `upgrade` refuse the capability carrying an unmet mark** — an upstream whose capability is not installed, whose role no installed capability provides, that is neither offered nor defined, or that is offered at another interface version. One line per mark: `- '<upstream>': <why it is not met> (mandatory: <reason>)`, then `Install or upgrade the upstream first, then retry`. `--force` does not override it.
- **`upgrade` and `uninstall` warn when they would leave another capability's mark unmet**: `Warning: uninstalling '<name>' would leave N mandatory process connection(s) unmet:`, one line per counterpart — `- '<capability>' depends on '<upstream>': <why> (mandatory: <reason>)` — and refuse, pointing at `--force`. Under `--force` the warning is printed (`Warning (--force): … leaves …`) and the operation proceeds.

### Regenerating a capability's `depends-on` list

**`capabilities refresh <name> [--dry-run]`** rewrites `connections.extensions.depends-on` in `.pkit/capabilities/<name>/package.yaml` from the `depends_on` entries the capability's process definitions declare ([COR-053](../decisions/core/COR-053-connection-points.md) point 4): one entry per distinct upstream and targeted interface version, sorted, marked `generated: true`. Comments, key order and quoting elsewhere in the file are kept; with nothing to generate the list is removed. It prints the entries it wrote, or that the list is fresh and nothing was written; `--dry-run` prints the same and writes nothing. Run it where the capability is authored, whenever a definition's `depends_on` changes (after `pkit process couple`, say) — `pkit validate` fails a stale list and names this command. The capability must be authored in the repository (`.pkit/capabilities/<name>/package.yaml`); registered or not. A **kit-shipped** capability installed in an adopting project is refused: its package file is core-owned and `sync` overwrites it, so a stale list there is reported to the capability's author.

### Discovery: `show`, the plans and suggestions

What a capability connects to is readable before it is installed, and what an install or an uninstall would change in the wiring is shown before it happens ([COR-053](../decisions/core/COR-053-connection-points.md) point 8). All three read the one wiring resolver; none resolves anything of its own, and none writes. The lifecycle README's "Discovery: what a capability would connect to" carries the full contract.

**`capabilities show <name> [--json]`.** Found in the *local catalogue* only: the capabilities registered in this project (their installed tree), capability subtrees authored in this repository and not registered, and the capabilities that ship with the running pkit — in that order when a name is in more than one. Read from its package metadata alone, it lists the roles it provides with who answers each, the points it accepts (data) and offers (processes, events) with their version, policy, mandatory mark and description, its extensions (`contributes`, `subscribes`, `depends-on`), and what would connect here: for an installed capability the live wiring's bindings to and from it, for one not installed the bindings of the wiring this project would have with it installed. A name the catalogue does not hold is refused, pointing at `pkit capabilities list`.

**`capabilities install <name> --plan [--json]`.** The difference between the live wiring and the wiring the resolver computes with the capability added — so the plan is exact: the install then changes the wiring by exactly that difference. It lists the connections the install would make; the connections it would break (installing a second provider of a role breaks every connection to the role until one provider is selected); each role conflict it would open, with the command that resolves it — `pkit connections providers set <role> <capability>`, one per provider; what the capability needs that this project does not give it — the errors the install would put on the capability itself: an unmet mandatory mark, a mandatory cycle, a `requires_backbone` or `requires_capabilities` range the project does not meet; the role blocks in artefacts whose meaning changes (an orphaned block the new provider adopts, a bare key a second active role would make ambiguous); then the roles, points and findings that change. The plan runs before the install's backbone and dependency gates, so a capability they would refuse still gets its plan, the reason among what it needs; an installed capability has none.

**`capabilities uninstall <name> --plan [--json]`.** The same difference with the capability removed, run before the refusal checks. It lists the fillers lost — the capability's own contributions, and the project filler files answering a point it defines that no provider would define after it (kept on disk, inert); the processes left without a provider (`depends-on` entries it answered) and the other counterparts left without one (contributions to its points, subscriptions to its events); the artefacts whose role blocks would be orphaned — preserved and reported, never an error, until a provider of the role is active again; the selections in the configuration left naming it; then the roles, points and findings that change.

`--json` prints the machine form of `show` and of either plan (keys sorted, stable); on `install` or `uninstall` it goes with `--plan`, and alone it is refused. `--plan` writes nothing and runs no other step of the operation.

**Suggestions.** Where the live wiring has an unmet need — a data point filled by nothing but its default, a role an installed counterpart targets and nobody provides, an implementation-addressed upstream not installed — `pkit status` suggests, under Capabilities, each capability of the local catalogue not installed that would answer it: one contributing to the point at its version, one providing the role, the upstream named. Suggestions read only the local catalogue — package metadata already on disk; nothing is fetched to make one. **A suggestion is never an action**: it names the capability and `pkit capabilities show <name>`, and installs nothing. They are computed in one place (`capability_plans.suggestions`), which any other view of the wiring reads rather than suggesting on its own.

## Configuration file

A project keeps its declarations to the backbone in **one project-owned file**: `.pkit/project/config.yaml` ([COR-048](../decisions/core/COR-048-backbone-configuration.md) point 1). It sits in the project namespace — `sync`, `upgrade` and every uninstall leave it alone — and it is the file `pkit report` already reads the project's `name` from. An absent file, an empty file or a missing key means the owning record's default applies; that is never an error (point 3).

**Every key is owned by a core record** (point 2), which defines its meaning, default and writers. A capability never adds a key here; its settings live in its own subtree. Project records may own keys only under the reserved `project` block.

| Key | Meaning | Default | Owning record |
|---|---|---|---|
| `name` | The project's declared name, rendered wherever the backbone names the project (never derived from a folder or remote name). | none — readers fall back to the git remote's repository name | COR-048 point 2 (writer: the `pkit report` prompt-once write-back, ADR-050) |
| `docs.user` | The **user root**: the directory, relative to the repository root, where user-facing documentation lives. | `docs/` | [COR-049](../decisions/core/COR-049-documentation-roots.md) point 1 |
| `docs.internal` | The **internal root**: where technical documentation for maintainers and agents (decisions, architecture, guides, analysis) lives; components that choose a documentation location derive it from this root plus their conventional sub-path. | `docs/` | COR-049 points 1 and 4 |
| `friction.mode` | How the friction change check treats what it finds: `warning` reports and passes; `enforcing` fails on friction, dead anchors and a bump with nothing behind it. | `warning` | [COR-050](../decisions/core/COR-050-anchors-and-friction.md) points 12 and 14 |
| `friction.status-job` | When the job that writes the tool-written `last-check` status runs: `never`, or `after-merge`. | `never` | COR-050 points 10 and 14 |
| `friction.places` | The project's own anchored places: paths or globs, relative to the repository root, where the friction check looks for artefacts carrying the methodology's container. `**` spans folders. | none | COR-050 points 1 and 14 |
| `friction.surface` | The project's declared surface: paths or globs that artefacts are expected to anchor to; the check reports the uncovered part. | none | COR-050 point 14 |
| `friction.exclude` | Paths or globs the friction checks leave out. | none | COR-050 point 14 |
| `connections.providers` | The **provider-selection key**: `<publisher>::<role>` → the installed capability that answers the role. | empty | [COR-053](../decisions/core/COR-053-connection-points.md) point 7 (writer: `pkit connections providers set`, "Connections commands") |
| `connections.selections` | The **contributor-selection key**: `<publisher>::<role>:<point>` → the installed capability whose contribution wins a `single` data point. | empty | [COR-052](../decisions/core/COR-052-slots.md) point 4, COR-053 point 7 |
| `project` | Reserved for keys the project's own decision records own. Checked only for being a mapping; never inspected. | empty | COR-048 point 2 |

```yaml
# yaml-language-server: $schema=../schemas/backbone/config.schema.json
name: example
docs: { user: docs/, internal: docs/ }
friction:
  mode: warning
  places: [docs/**/*.md]
connections:
  providers: { pkit::work-tracking: project-management }
project:
  anything-the-project-decides: true
```

**Schema.** The file is validated as a whole against `.pkit/schemas/backbone/config.schema.json`, a backbone file schema shipped in the tree and bound to this file by its fixed path ([ADR-056](../../tech-docs/architecture/decisions/ADR-056-backbone-file-schemas-home.md); the schemas README's "Backbone file schemas" section). The file carries **no version key** — the backbone owns its shape and migrates it (COR-010). The first line above is the editor directive the backbone stamps into a file it creates; an editor that reads it validates and completes as you type.

**Strict when checked, forgiving when read** (COR-048 point 4). `pkit validate` runs the configuration pass and reports under a `configuration` heading; commands that merely read a key never fail because of it and use the default (COR-048 point 4); today's only reader, `pkit report`, falls back silently. The findings, each with a JSON Pointer into the file and a severity:

| Severity | Finding |
|---|---|
| error | An unknown key at any backbone-owned level, reported with the nearest known key (`unknown key 'doc'; did you mean 'docs'?`). A key of `connections.providers` / `connections.selections` that is not an address of the right form. |
| error | A wrong type, an invalid `mode` / `status-job` value, an absolute path, a duplicate pattern. A file that does not parse, or is not a mapping. |
| error | A documentation root that resolves (after following links) outside the repository or inside `.pkit/` (COR-049 point 1). |
| warning | A documentation root that does not exist yet, or exists but is not a directory (COR-049 point 7). |
| error | A friction pattern that leaves the repository — absolute, climbing above the root, or resolving outside it through a link (its nearest existing ancestor is followed, so `docs/linked/sub/**` with `docs/linked` a link out is caught before `sub` exists) (COR-050 point 14). A bare `.` means the whole repository and is accepted. This pass is the one owner of the finding; the friction pass never walks such a pattern. |
| warning | A friction pattern that matches nothing: a dead pattern keeps silence looking like health (COR-050 point 12). The patterns are judged as friction discovery reads them, and a pattern matches something only when it covers a file of the working tree's listing — the files git sees — by the reading the friction checks apply: a glob reaching only folders, or files git ignores, covers nothing the checks ever see. |
| error | A connection entry naming a capability that is not installed, with the fix (`pkit capabilities install <name>`, or remove the entry). |
| error | A `connections.providers` entry naming an installed capability that does not provide the role — the message lists the roles it does provide and the installed providers to choose from (COR-053 point 7). |
| error | A `connections.selections` entry naming no data point the active provider of its role defines (a point only an unselected provider declares is not defined in the project), a point that is not `single`, or a capability that declares no contribution to it — the message lists the point's installed contributors (COR-052 point 4). The point is read from the resolved wiring; while its role has no active provider, the role conflict or the provider selection is the finding and the contributor selection is not judged. |

Only errors fail the command. The same repository state always yields the same findings in the same order: schema findings by position, then the repository checks in a fixed order — docs, friction, connections — each entry in written order. A tree recorded before the schema landed has no `config.schema.json`; the pass reports "no config schema present in this tree; skipped." rather than validating against a shape that tree never shipped (ADR-056 point 1).

**The `docs` key — documentation roots** ([COR-049](../decisions/core/COR-049-documentation-roots.md)). Two roots, one per audience, both defaulting to `docs/`; the two may be the same folder or one nested in the other. They describe *layout* only — whether a project separates its audiences is a documentation discipline's rule, not the backbone's.

- **Derivation** (points 3 and 4). Whatever in the methodology has to *choose* a documentation location derives it from the right root plus a conventional sub-path: the commands that fill missing overlay categories (`pkit agents reconcile` / `adopt`), commands that stamp documents, and capabilities that keep documents of their own. The backbone owns one list of sub-paths for the overlay categories that locate a *folder* of documents — `architecture-docs` → `<internal>/architecture`, `adr-records` → `<internal>/architecture/decisions` (`src/project_kit/docs_roots.py`, `CONVENTIONAL_SUBPATHS`); a category listing individual *files* (the project-root documents) does not derive. A capability declares the sub-paths of its own documents in its package metadata (`docs.locations`). **Agent deployment derives nothing**: placeholders resolve only from what the overlay explicitly contains.
- **Precedence**: **explicit > derived from the root > conventional default.** An explicit location — a value already in the overlay, or recorded in a capability's configuration — always wins; a root is consulted only where no explicit value exists.
- **Record on first use** (point 5). A location derived from a root is recorded as an explicit value the first time a document is placed there: an overlay category is written uncommented (annotated `recorded by \`pkit agents adopt\``); a capability's location goes into `.pkit/capabilities/<name>/project/docs-locations.yaml`, a backbone-owned file kept apart from the capability's own `config.yaml` so a strict capability schema is never broken by a key it did not declare. Recording happens only where a location is chosen — never on read — and an already-recorded value is never overwritten.
- **A later root change moves nothing** (point 6). Because every chosen location is recorded, changing a root afterwards affects only locations chosen from then on. There is **no migration**: an absent key means the defaults, and every location that resolved before the roots existed is an explicit overlay value, so introducing them changed nothing.
- **Status lines** (points 6 and 7). `pkit status` gains a `Documentation` section: one line per root with its source (`user root  docs/  (default)`, `internal root  tech-docs/  (explicit)`), then every recorded location — those lying inside the internal root under `inside root`, then those outside it under `outside root`, one line each, capability locations tagged `(<capability>)`, in a fixed order — so a project sees where its recorded locations sit and what a relocation would involve. Moving documents is always an explicit, reviewable operation.
- **Reading is forgiving.** A root that is absent, not a relative path, or unreadable resolves to the default for every reader; `pkit validate` reports the file's problems.

**Writing — the consent rule** (COR-048 point 5). Every writer of this file — `pkit config set`, the `name` write-back of `pkit report`, and any capability that offers to record a value — goes through one primitive (`project_kit.project_config.write_config`): it re-reads the file, applies the change, validates the result against the schema (an invalid result is refused and nothing is written), asks for consent **once**, then writes atomically, keeping the file's header and comments. Consent takes exactly three forms: an interactive confirmation; an explicit `--yes`; or an upgrade migration the owning record specifies. A **non-interactive run without `--yes` refuses** — exit non-zero, naming the exact command to run — rather than writing silently. Editing the file by hand is the project's own edit, always allowed.

### `config set <key> <value> [--yes]`

Set one backbone-owned key. `<key>` is dotted (`docs.internal`, `friction.mode`, `connections.providers.pkit::work-tracking`); the command walks it through the configuration schema and refuses an unknown key (naming the nearest known one), any key under the reserved `project` block (the project's own records own it; the backbone never writes it), and a key that holds a mapping or a list (`friction.places` — edit the file). `<value>` is coerced to the key's declared type, and the whole file is validated before the write: `pkit config set friction.mode loud --yes` is refused with the schema's message and writes nothing. On success it prints `set docs.internal = tech-docs  (.pkit/project/config.yaml)`; a file it creates opens with the editor directive. Runs under the `kit` privilege like every other `pkit` command — no separate grant. A provider selection has its own command, `pkit connections providers set <role> <capability>`, which also checks that the capability declares the role and shows the diff first ("Connections commands").

## Authoring commands

The `new` family scaffolds first-class methodology elements — areas, adapters, capabilities, migrations — by stamping the contract their owning record fixes (COR-005 for adapters, COR-010 for the manifest layer and migrations, COR-011 for areas, COR-017 for capabilities). Every `new` command is a one-shot generator: it refuses to overwrite existing targets, and the output is a directory or file the rest of the CLI surface (`status`, `sync`, `upgrade`, etc.) recognises immediately. No manual manifest edits are needed after a scaffold call.

The shapes are stamped by the CLI's own scaffolding code (`src/project_kit/scaffolds.py`), which ships with the binary, so a kit upgrade that changes a contract also updates what gets stamped.

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

**Coordination with the `decision-author` skill.** Per COR-006's discriminator: a command stamps deterministically, a skill drafts content conversationally. The `decision-author` skill (`.pkit/skills/core/decision-author.md`) calls `pkit new decision <namespace> <slug>` for the stub, then walks the author through filling the body — content drafting, discipline self-checks, and approval. Authors who don't need the conversational help can call the command directly.

### `new agent <namespace> <name> [--with-storyboard] [--dry-run]`

Stamps an agent stub — the unified front matter (COR-013) and the canonical body sections — flat as `<name>.md` (COR-015). The spec for what goes in it is `.pkit/agents/README.md`.

- **`<namespace>`** is one of:

  | Namespace | Location |
  |---|---|
  | `core` | `.pkit/agents/core/` |
  | `project` | `.pkit/agents/project/` |
  | *a capability name* | `.pkit/capabilities/<capability>/agents/` (COR-017, COR-026) |

  A `<namespace>` that is not `core` or `project` is interpreted as a capability name, as for `new decision`: the command refuses if no capability of that name exists under `.pkit/capabilities/`, naming the ones that do, and creates the capability's `agents/` folder on first use.

- **`<name>`** is kebab-case, naming the role. The command refuses a name already taken in core, project or any capability, in either layout — the deploy resolves one agent per name, so a second one would mask the first.

- **`--with-storyboard`** stamps folder form (`<name>/<name>.md`) with a sibling `storyboard.md` scaffold (COR-016) whose `consumers:` names the agent, its `namespace` being the capability's name for a capability's agent.

**Coordination with the `agent-author` skill.** The skill carries the namespace choice (universal role, adopter role, or a capability's discipline), the name, and the body drafting; the command is the stamp underneath.

### `new storyboard agent <name> [--namespace <ns>] [--scenario <slug>] [--dry-run]`

Stamps a storyboard (COR-016) beside an existing agent: `storyboard.md`, or `<slug>.storyboard.md` with `--scenario`, carrying the three-layer scaffold and a `consumers:` entry naming the agent. A flat agent migrates to folder form first (COR-015, an agent gaining its first helper).

- **`agent`** is the only artifact kind handled today.
- **`<name>`** is the agent's name. Without `--namespace`, the command looks wherever agents ship from, in the deploy's order — project, core, then capabilities by name — and stamps beside the first agent of that name, the one that deploys.
- **`--namespace <ns>`** pins the lookup to one location: `core`, `project` or a capability name (an unknown capability gets the `new agent` refusal).

Refuses if the storyboard already exists or no agent of that name is found. **Coordination with the `storyboard-author` skill**: the skill walks the framing, tone and scenario drafting after the stamp.

### `new scratchpad <slug>`

Stamps a new active-state scratchpad note at `.pkit/scratchpad/active/<YYYY-MM-DD>-<slug>.md` per the convention in COR-012 and the spec in `.pkit/scratchpad/README.md`. The command is the deterministic part of starting a note: pick today's date, validate the slug, seed the frontmatter, write an H1 derived from the slug.

- **`<slug>`** is a kebab-case shorthand of the question the note explores (e.g. `agent-architecture`, `versioning-policy`). Slugs are unique across the entire scratchpad area — the command refuses if any state folder already contains a note with this slug.

The stamped file includes:

- Frontmatter — `authors` (a list seeded from `git config user.name` / `user.email`) and `started` (today's date).
- A level-1 heading derived from the slug as a starting title (the author edits it on first pass).

Supports `--dry-run`.

**Coordination with the `scratchpad-author` skill.** The paired skill (`.pkit/skills/core/scratchpad-author.md`) carries the slug-choice judgement, the topic-boundary discipline, and the body-drafting opening prompt. Authors who don't need the conversational help can call the command directly.

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
- **Agent workspace** — whether `.agent-workspace/` exists and whether git ignores it (`excluded from git`, `NOT excluded from git`, or not a git repository), asked of git itself so an exclusion by any rule counts; when the folder is missing or not excluded, the line names `pkit sync` as the remedy. A symlink where the folder belongs is reported as never the workspace.
- **Adapter status** (Claude Code today): whether `.claude/settings.json` is merged, whether a `.pre-pkit` backup exists, and a list of deployed skills split into kit-managed (symlinks into `.pkit/skills/`) vs user-managed (anything else under `.claude/skills/`).
- **Capabilities** — which are available in `.pkit/capabilities/` and which are installed (per COR-017); then, when the wiring has an unmet need, the capabilities of the local catalogue that would answer it — suggestions only, from package metadata on disk, never fetched and never installed (COR-053 point 8; see "Discovery"). The report is one run: every section that reads the wiring reads the same resolution of it.
- **Documentation** — the two documentation roots with their source (`explicit` / `default`), and every recorded documentation location, those inside the internal root and then those outside it, one line each (COR-049 points 6 and 7; see "Configuration file", the `docs` key).
- **Friction** — the friction mode with its source, and each declared place, surface entry and excluded path: the project's in written order, then each capability's, tagged `(<capability>)` — a capability place inside its documentation location (the recorded one when recorded), its surface repository-relative (COR-050 point 14). With no place declared it says so. Rule-set folders, places by the location rule rather than by declaration, are not listed.
- **Rule sets** — how many rule sets and rules were found, and how many inheritance pins were checked; each pin whose inherited set has moved to another major is listed — the inheriting set, the pin, the version the inherited set is at — with its fix, the edit to `inherits` that re-pins it once the change is reviewed (COR-051 point 7). The same pins fail `pkit validate` under `versions`; see the schemas README, "Rule-set files".
- **Connections** — the resolved wiring (COR-053 point 7). First each role anything names: its provider (`<role> → <capability>`, `selected` when the configuration selects it, the providers not selected named); a role in **conflict** — several installed providers, none selected — or a selection naming no provider, followed by one `fix:` line per provider giving the exact command that resolves it (`pkit connections providers set <role> <capability>`); or **orphaned** — no installed capability provides it. Then each point an active provider defines: its kind, version and provider, `mandatory` when marked, and whether it is filled (a data point) or how many counterparts are bound (a process or event point); under it the project filler and every counterpart reaching it — `bound`, or `inert` with why (another version; an unselected provider's, not delivered) — and each mandatory mark the wiring leaves **unmet**, the point's own included. Last, the counterparts that reach no point (`unreached`: a role nobody answers, a point its role does not define, an upstream not installed). What a data point resolves to is the next section's, not repeated here. The wiring is `pkit validate`'s own, resolved once for this section and the next, so the two never disagree; see "Connections commands".
- **Data points** — where project filler files live (`<internal-root>/pkit/fillers/`) and how many there are, how many data points are defined and resolved; then per point its policy, inert policy and default participation, whether it resolved or why not, its value (a `single` point's answer and the filler that gave it; each entry of a `union` or `additive` point with its origin and what it replaced), each removal override with its reason, and every filler considered — taken, inert or passed over, with the reason — a command filler saying whether its command declares the query contract, which is trusted, not enforced (COR-052 point 7). The resolution is `pkit validate`'s own, command fillers included, which run as they do there; see the lifecycle README, "How a data point resolves".
- **Counts** for decisions (COR / PRJ records) and skills (core / project).

Output is human-readable with tagged status lines. Makes no changes.

### `validate`

The one umbrella over every deterministic check of the tree's **state** (COR-004; the registry's shape is ADR-058). Each functionality registers a *validator* — a name, an order and a callable that reads the project and answers with summary lines and findings, each finding with a severity. The backbone registers its members in `project_kit.validators`; an installed capability registers its own in its package metadata (`validators:`, the lifecycle README's package-metadata reference). One renderer prints every member under its own heading — the summary lines, then each finding as `<severity>  <location>` over `→ <message>`, an unknown key always phrased by the shared renderer with the nearest known key — and one summary closes the report. **Only `error` fails**; `warning`, `info` and `report` print. Makes no changes.

The backbone's members, in the order they run (what a later member reads, an earlier one checked):

| Member | What it checks | Focused surface |
|---|---|---|
| `manifests` | the backbone manifest is present, parseable and at schema_version 1; each registered component's per-component manifest, where one exists at the declared path, parses and carries its required fields and a matching name and kind; a missing one is skipped (adapters and capabilities propagate through sync and do not stamp one) | — |
| `schemas` | every schema pair (YAML against its JSON Schema companion, cross-file references resolved), every pointered instance, the backbone file schemas load, the capability grants' privilege tokens resolve | `schemas validate` |
| `configuration` | `.pkit/project/config.yaml` against `config.schema.json`, then the repository checks its records ask for (documentation roots, friction patterns, connection selections) — see "Configuration file" | — |
| `packages` | every registered component's `package.yaml` against `package.schema.json`, then the repository checks (name matches directory, versions and ranges parse, command scripts exist, each validator and each command filler names a `commands:` leaf that declares `query-contract: true`, connection points under a provided role with their schemas and commands, a contribution naming `command` or `value` but not both, document locations and friction places relative); an unknown key is an error naming the nearest known key — see the lifecycle README, "Validation: the package schema" and "Strict on unknown keys" | — |
| `connections` | the wiring the installed packages and the configuration's selections resolve to — the active provider of each role, each active role's points, every counterpart against its point; fails on a role provided twice with no selection (naming `pkit connections providers set <role> <capability>` for each provider), an unmet mandatory mark, a mandatory cycle, disagreeing companion schemas, a `single` point with several contributors and no selection; warns on an unselected provider, an inert counterpart, a counterpart naming a point its role does not define — see the lifecycle README, "How the wiring is resolved". Then how each data point resolves from its project filler, contributions and default by its policy, running each command filler once, offline-marked and bounded: fails on a project filler file that does not parse, is malformed, or holds a value its point refuses, on colliding entries, and on an inert filler of a `fail` point; warns on an inert filler of a `fallback` point and on a file under the fillers prefix that names no point; reports a filler whose point no active provider defines — see the lifecycle README, "How a data point resolves" | — |
| `versions` | every version relation, each finding labelled with its relation: `requires_backbone` against the installed backbone, `requires_capabilities` ranges against installed versions, contributions and subscriptions against point versions, `depends-on` entries against the offered interface's version, a project filler's envelope against its point's version, rule-set inheritance pins against the inherited set's major | — |
| `friction` | artefacts in the declared places (COR-050 point 12): front matter that does not parse, a malformed `friction` block, a dangling deferral, a cycle between artefacts fail; an orphaned role block or an inert point block is a report. A capability place the walk does not follow — not in the package schema's shape `{path, location?}`, or leaving the repository — fails too, dormant or not. Dormant — a count line, plus any place the walk cannot follow — until a place is declared and an artefact carries the container. Reference: `.pkit/schemas/README.md`, "The friction block" | — |
| `rule-sets` | every rule-set file the location rule finds against `rule-set.schema.json`, then the join between data and prose, ids, the container inside each rule, origins, successors and inheritance (COR-051); an unresolved source kind and an orphaned fill are reports. Reference: `.pkit/schemas/README.md`, "Rule-set files" | — |
| `decisions` | each core and project record's front matter (id, title, status, date, author), and the id spaces across every record family: no id claimed twice within a space, the front-matter id matching the filename, no rule id claimed twice across the rule sets | `decisions validate` (the id spaces) |
| `refs` | the reference graph across agents, skills and hooks (COR-013): **drift** between an artifact's front matter and its body — a declared reference the body never cites, a body citation not declared — is a *warning*, since the artifact deploys and resolves regardless and the body parser is a heuristic; a path owned twice or by nobody, a hook no provider answers, colliding providers, a missing storyboard, a citation that does not resolve, a sub-procedure that does not exist, an agent `model:` / `effort:` (front matter or overlay override) the harness does not accept are *errors* | `refs validate` — fails on any finding, drift included |
| `process` | every process definition the installed capabilities declare resolves to exactly one file whose `process.id` matches. A subject's invariants need a subject and its predicates and are not run here | `process validate <address>` (the invariants) |
| `data` | every data file in the repository that a `pkit_schema:` field or an installed capability's `binds_to:` glob claims — outside `.pkit/` and any dot-directory, plus every project-owned `project/` folder under `.pkit/` (`.pkit/project/`, `.pkit/capabilities/<name>/project/`), among the files git sees (the working tree's one listing, which the `friction` member reads too) — against its bound schema and with cross-file references resolved over every bound file (COR-023, COR-029); a file nothing claims is not adopter data and is skipped, an unreadable one included | `data validate <path>` — a named file nothing binds, or that does not parse, is a finding there |

Each installed component's validators follow (a capability's or an adapter's — every installed package is read), addressed `<component>:<name>`, sorted by their `order` (1000 by default, after every backbone member), then component, then name. An entry under `validators:` in the component's package metadata names a leaf of its `commands:` tree by `command`, so the same script is a focused surface (`pkit <capability> <command>`) and a member here; the leaf's `help` is the validator's (the lifecycle README, "Package metadata").

**The query contract expected of a validator command** ([ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 3; ADR-058). The leaf declares it with `query-contract: true` — bounded, deterministic, read-only, needing no network — and the umbrella runs the script from the project root with the one argument `--json`, the offline marker in its environment (`PKIT_OFFLINE=1`, and `UV_OFFLINE=1` so a `uv run --script` shebang resolves its dependencies from uv's cache and never fetches), in its own process group, bounded by the backbone's one command bound of thirty seconds (the lifecycle README, "How a registered command is run" — the runner it shares with the process engine's predicates), and reads one JSON document — and nothing else — from its standard output: `{"summary": ["..."], "findings": [{"severity": "error"|"warning"|"info"|"report", "location": "...", "message": "..."}]}`, a finding optionally carrying a `label`; diagnostics go to standard error. **No answer is an error finding, never a clean pass:** a leaf without the declaration (the `packages` member reports it, the runner refuses it), an abnormal exit, a timeout (the whole process group is killed, the grandchild a `uv run --script` shebang starts included), or an answer that is not exactly that document — a missing or non-list `summary` or `findings`, a malformed finding. An exit that is uv's report of a dependency missing from its cache gets its own message, **"environment not provisioned — run `pkit sync`"**: `pkit init` and `pkit sync` provision every query command's environment (step 5 of `init`). **Residual gap:** as for a resolver (the resolver-limits paragraph under "Friction checks"), the declaration is trusted, not enforced — nothing here confines the process it starts, and the marker only tells a well-behaved command. The living-docs capability registers the first, `living-docs:spaces` (its README, "Validation").

`--only <name>` (repeatable) runs the named members alone; `--skip <name>` (repeatable) drops them; `--no-refs` is `--skip refs`, kept for scripts that pass it. A name the registry does not know is refused, naming the registered members.

**What is not a validator.** The checks that read a base ref and answer about a *change* — `friction check`, `migrations check-diff`, `release lint` — are diff-scoped, not state checks; they are their own lines of the check aggregator (`scripts/check.sh`), which calls `pkit validate` once beside them.

`status` answers "what's installed?"; `validate` answers "is it consistent?". Different questions, different commands.

### `schemas validate [<path>]`

Read-only check on the **kit-side schemas mechanism**: every YAML schema in the core schemas area (`.pkit/schemas/`, where `pkit new schema core` stamps) and under `.pkit/capabilities/<cap>/schemas/` is validated against its JSON Schema companion (shape pass) and every typed-token cross-schema reference is resolved against the target namespace's id collection (resolver pass).

A YAML declaring an external `$schema` (a `# yaml-language-server:` directive or a top-level `$schema:` key naming a schema other than its own companion) is an **instance**, not a definition: it is exempt from the companion requirement and validated against the schema its pointer names, resolved relative to the YAML's own directory. Findings report against the instance's path with a JSON pointer into the offending position; a pointer whose target is missing or is not a valid Draft 2020-12 schema is itself a finding. See `.pkit/schemas/README.md` ("The pointer is validated, not just classifying") for the full contract.

With `<path>`, runs the same passes scoped to the given file or directory — useful for adopters whose data follows the same conventions outside the capabilities tree.

`--shape-only` skips the resolver pass (useful mid-refactor when a referenced target schema doesn't exist yet). It does not affect instance validation, which is shape-only by construction.

The no-PATH gate also runs a **fragment-token-resolution lint** (ADR-021): for every installed capability's `permissions/grants.yaml`, each grant's privilege token must resolve to a privilege in the *merged* catalog, or the deny silently does not bind (the bare-vs-scoped fail-open hazard). The lint reuses the decision core's merge (`load_catalog`) and token normaliser (`_privilege_ids`) so it agrees with the runtime exactly; it covers hand-authored fragments, not just those `permissions scaffold` / `permissions grant` produce. An unresolved token fails the gate with a clear message naming the file, the offending token, and the likely fix (usually the missing `<cap>:` scope). This pass is project-scoped (it needs the manifest + merged catalog), so it runs only in `schemas validate` with no `<path>`, not in the path-scoped form.

The no-PATH gate also **load-checks the backbone file schemas** — every `*.schema.json` under `.pkit/schemas/backbone/` (the methodology's front-matter container today; see the schemas README's "Backbone file schemas" section) must parse as a valid Draft 2020-12 schema. They are not enumerated as pairs. A malformed file fails the gate naming the file and the reason, and the summary line reports how many were checked.

### `data validate <path>`

Read-only check on **adopter-side data files** against capability schemas (per COR-023, superseding COR-022). Resolves each file's binding in two steps:

1. **Field-first.** A top-level `pkit_schema: <capability>:<schema>` field is authoritative.
2. **Capability fallback.** Otherwise, the resolver walks every installed capability's `schemas/*.yaml`, collects each schema's `binds_to:` glob entries, and uses the first matching glob.

When neither resolves, the file is reported as unresolved. Schema-version mismatches refuse with a structured migration hint (auto-migration is out of scope in v1).

`<path>` is a file or directory; directories walk recursively for `*.yaml` (`.pkit/` subtrees are excluded — those are kit-managed, not adopter data).

`pkit data validate` is distinct from `pkit schemas validate`: the latter validates the *spec* (capability YAML + companion); the former validates *instance data* (adopter file + its bound schema).

### `version`

Prints the CLI's own version (`pkit <version>`) — the version of the checkout or wheel that owns the binary, not of the project at the working directory; `pkit status` shows the project's recorded core-layer version for comparing against it.

### `version bump <segment>`

Bumps `.pkit/VERSION` per the policy in PRJ-002. `<segment>` is `patch`, `minor`, or `major`:

- **`patch`** — backward-compatible bug fix to existing surface.
- **`minor`** — new surface added (new command, new principle, new area). Pre-1.0, this is the typical bump and may carry breaking changes per semver convention for `0.x` releases.
- **`major`** — reserved for `1.0.0` and post-1.0 spec breakage. Pre-1.0 the command refuses major bumps.

The command parses the current version, validates it as semver, computes the new version, writes it back, and prints `Bumped backbone: <old> -> <new>`.

After writing the new backbone version, the command **auto-broadens** the `requires_backbone` upper bound on every kit-shipped `package.yaml` under the working-directory project's `.pkit/` (the project the command operates on) whose existing range no longer includes the new backbone version. The new upper bound is `<NEW_MAJOR.(NEW_MINOR+1).0`. Components whose range still covers the new version are untouched (so patch bumps that stay within the current minor line are no-ops on `requires_backbone`). Component authors who deliberately want a tighter range narrow it manually after the bump.

Under the current PRJ-002 policy, feature branches **declare** version intent via a changeset rather than bumping in-branch; `version bump` remains fully functional during cutover (introduce → migrate → retire) and is what the release step's writes are equivalent to. Recommended commit message when it is used: `chore(versioning): bump backbone <old> -> <new>`.

### `release plan` / `release apply` / `release merge` / `release publish-notes` / `release check` / `release lint`

The declared, release-driven version path (PRJ-002 D1–D4). Feature branches drop a **changeset** file under `.changes/unreleased/`; the release step on `main` is the sole writer of version state. `release plan` previews the computed release; `release apply` consumes the changesets, computes each tier's new version from current `main`, broadens `requires_backbone` (the broaden moves here, PRJ-002 D4), updates `CHANGELOG.md`, and deletes the consumed changesets. Tagging stays a separate anchored step (`pkit version tag --push` on `main` after the release commit lands), matching the bump/tag split. `release merge <pr>` is the **sanctioned merge path** for a release PR — one that closes no issue, which the project-management issue-PR merge gate legitimately refuses; it is guarded to `release/*` heads, merges only an open, mergeable, green PR (one squash commit whose subject is the PR title, head branch deleted on merge), and does not tag (`release-tag.yml` tags on the push to `main`). `release publish-notes <version>` publishes a **notes-only** GitHub Release for tag `v<version>` (body = that version's `CHANGELOG.md` section) so the release page shows what changed — it is **idempotent** (creates the Release, then edits its notes on re-run), attaches **no artifact** (a notes overlay on the git-tag install path, PRJ-004 — never a file/wheel channel), and derives the repo from the ambient `gh` context; `--dry-run` prints the notes without calling `gh`, and `release-tag.yml` runs it automatically right after it cuts a tag. `release check --base <ref>` is the CI surface-without-changeset guard, with a `none`-changeset / `skip-changeset`-label escape hatch. `release lint` is a sibling *format* check — it validates only the mechanically-checkable subset (a changeset's category is a Keep-a-Changelog group and its body is a well-formed sentence; `CHANGELOG.md` headings parse) and leaves plain-language judgment to the guide and review; it reads committed files only (no PR context), so it rides in the shared check aggregator (`scripts/check.sh`). Every `version` subcommand and every `release` command operates on the project at the working directory — the same CWD root resolution as every other command — not on the checkout that owns the `pkit` binary (bare `pkit version`, which prints the CLI's own version, is the one exception); when the two differ (a git worktree run through the main checkout's virtualenv, say) the command prints a one-line notice on stderr naming both paths and proceeds. The full mechanics — changeset format, contributor workflow, and both checks' honest limits — live in the release-flow spec (`.pkit/release/README.md`).

## Friction checks

The `friction` command group is everything the anchors-and-friction functionality does ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 13), named like the block an artefact carries and the configuration key. Its reading commands never write: the change check (`check`), the whole-repository check (`check --all`), the debt listing (`debt`), one artefact's explanation (`explain`) — the last two views of the whole-repository check, never a second computation of it — and the places and artefacts discovery finds (`artefacts`), below. Writing is always one of three separate commands — `revalidate`, `defer`, `record-status`, after the reading commands below — and no reading command ever writes. The block itself, where artefacts are looked for and what validation fails on are in the schemas README, "The friction block".

**What every writer does** (point 13):

- **Names what it writes, and writes only that.** Each command rewrites one key of the artefact's `friction` block — `revalidated`, the `deferred` list inside it, or `last-check` — and prints the key, the file and the lines it occupies. Every other byte of the file stays as it was: the lines from that key through the end of its value are replaced, or, in a block written in flow style (`pkit: { friction: { … } }`), that key's characters inside the braces. Entries are kept in one order — deferrals by anchor kind, then value; keys in the schema's order — so the same input writes the same bytes, and parallel branches deferring different anchors touch different lines.
- **Writes only what validation accepts.** Before anything is written the result is read back: the front matter must hold exactly what it held with that one key replaced, and the artefact must pass validation's own judgments of a block (the shape, dangling deferrals). A block that would not validate — a typo elsewhere in it, say — is refused, and nothing is written; fix it first (`pkit validate`).
- **Writes only with consent** — the consent rule of the configuration writer (COR-048 point 5), applied to the project's artefacts: `--yes` consents non-interactively; on a terminal without it the command shows the diff and asks; `--dry-run` shows the diff and writes nothing; a non-interactive run with neither refuses, writes nothing, and names the command to run with `--dry-run` and with `--yes`. `--yes` and `--dry-run` together are refused. A command with nothing to write says why and exits `0`.
- **Naming the artefact and an anchor.** `<artefact>` is its location — `path` for a document, `path#id` for a collection entry — or its id (a document's path works too); a name that fits more than one artefact is refused with the candidates. An anchor is `kind:value` (`path:src/cli/**`, `record:software-analysis:DEC-001`) or a bare value, when only one anchor of the artefact has it. An artefact with no `friction` block is refused: declare its anchors first. Files with carriage-return line endings are refused rather than rewritten.

### `friction check [--base <ref>] [--json]`

The **change check** (COR-050 point 6): every artefact with an anchor that changed in the change being made carries an answer in the same change. It reads the artefacts, never a pull-request description, so it runs the same in CI, for a pull request from any tool, and locally before a commit.

- **What it compares — git alone, nothing checked out.** *Head* is the working tree as git sees it: tracked files plus untracked ones git does not ignore — the same listing `pkit validate` reads, so the two find the same artefacts (a link is listed but never read as a document) — so uncommitted work counts and the header says how much (`Head: <commit> + working tree, 2 uncommitted paths`, or `(working tree clean)`). *The base* is the merge-base of `<ref>` and HEAD, read from git objects; `<ref>` defaults to `origin/main`, `PKIT_CHECK_BASE` overrides the default, and `--base` overrides both. *The diff* is `git diff -M --name-status <merge-base>` plus untracked files. Each side is discovered in its own declared places, so declaring a place makes the artefacts in it new, and dropping one removes them. Every run prints the base commit it compared against.
- **When an anchor changed** (point 5). A `path` anchor, when a changed path matches it — `**` spans folders, a path naming a directory covers every file beneath it, and excluded paths (`friction.exclude`) and the artefact's own file are ignored. A `record` anchor (`COR-050`, `PRJ-002`, `ADR-019`, or a capability decision `<capability>:DEC-NNN`), when the record's file changed; a pure rename keeps its content. An `artefact` anchor, when the target's **content** changed: its body compared as text, its own fields compared parsed, never anything inside the `pkit` container. The cascade follows from that: an artefact whose target changed must answer, and its own dependants are asked only when that answer changed its content (`updated`), never after `unchanged`.
- **The three answers**, read from the artefact's block before and after. **Updated**: the content changed and the parsed `at` changed, with `outcome: updated`. **Unchanged**: only `at` changed, with `outcome: unchanged` and an `unchanged-because` that changed too. **Deferred**: a deferral naming that anchor, by kind and value, was introduced in the change — one that was already there covers only earlier changes. An artefact new in the change counts as revalidated. A change to the artefact's own anchor list, or a move (its file renamed, or an entry moved to another collection file), needs a revalidation in the same change. Writing the same `at` differently — quoted, say — is not a revalidation.
- **Findings**, grouped by artefact, upstream first along artefact anchors (point 11):

| Kind | Meaning | Fails in enforcing mode |
|---|---|---|
| `friction` | An anchor changed — or the anchor list, or the artefact's place — and no answer stands. | yes |
| `bump` | `at` changed with nothing behind it: `unchanged` with the same justification, `updated` without a content change, `unchanged` although the content changed, or no outcome. | yes |
| `dead-anchor` | At head the anchor resolves to nothing, and the change is why: the anchor was added, or its target was removed or moved. An anchor that was already dead is the whole-repository check's. | yes |
| `unresolved-kind` | An anchor of a kind no installed component resolves, added in the change — reported apart from an identifier that does not resolve. | yes |
| `answered` | A change the artefact answers: `updated`, `unchanged` with its justification, `deferred` with its reason, or `new`. | no |
| `revalidated` | A revalidation in the change with no changed anchor behind it. | no |
| `outdated-base` | The tip of `<ref>` is not an ancestor of HEAD: results hold only against an up-to-date base — merge or rebase, and run again. | never |
| `unreadable` | Front matter in a place that does not parse; `pkit validate` fails on it. | no |

- **Modes** (point 12), from `friction.mode` in the configuration file. `warning`, the default, reports and exits `0`; `enforcing` exits `1` on friction, a bump, a dead anchor or an unresolved kind, and never on an outdated base. A malformed block, a dangling deferral or a cycle is validation's finding and fails `pkit validate` in either mode. A value that is not a mode reads as `warning` with a warning line, and `pkit validate` fails on it, so enforcement is never switched off silently. **Dormant** — the counts only, exit `0`, no repository demanded — while no place is declared or nothing in the places carries the container (point 15). The check binds only where the project makes it a required status of its continuous integration ([ADR-019](../../tech-docs/architecture/decisions/ADR-019-enforcement-gate-mechanism-vs-boundary.md) for the mechanism-versus-boundary split).
- **`--json`** emits one stable document, keys sorted, identical for the same repository state: `check` (`change`), `mode`, `dormant`, `failed`, `base` (`ref`, `tip`, `commit` — the merge-base compared against — and `outdated`), `head` (`commit`, `uncommitted_paths`), `counts` (places, artefacts, those carrying the container, one count per finding kind) and `findings` in report order, each with `artefact` (its id), `location` (`path`, or `path#id` for a collection entry), `kind`, `anchor` (`{kind, value}` or `null`), `answer` (`updated`, `unchanged`, `deferred`, `new` or `null`) and `message`. Other components — a work-tracking capability rendering a pull request's documentation impact, say — read this, never the human view.
- **Resolver limits** (point 2; [ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md)). The backbone resolves `path`, `record` and `artefact` itself. A kind a capability registers is resolved by a command the capability declares, and before such a command could run the check refuses one that does not declare the query contract — bounded, deterministic, read-only, needing no network. No capability registers a kind yet, so every other kind is an unresolved kind; running registered resolvers — with their time bound and fail-closed reading — arrives with the kind registry. **Residual gap:** the declaration is trusted, not enforced, and no layer of this distribution holds a single command to "no network": where the operating-system sandbox is on it admits every host the session allowed and is not a security boundary; on macOS the `pkit`/`uv` process tree — and so every command the check starts — runs outside it; in a pipeline or a plain terminal nothing restricts its network access.
- **Limits of the reading.** The check follows git's rename detection: a document moved and rewritten beyond recognition, with no `id` field of its own, reads as removed and new. Reading through git never follows a link — a linked Markdown file in a place is matched as a path but not read as a document — and ignored files belong to neither side.

### `friction check --all [--json]`

The **whole-repository check** (COR-050 point 6): every artefact in the declared places at HEAD, checked against the current history with the rule of point 5 — an anchor has changed when a commit reachable from HEAD and not from the artefact's revalidation point touched it. It reports and never fails (point 12): exit `0` in either mode, `--base` not read. project-kit runs it on every push to `main` with the full history ([ADR-055](../../tech-docs/architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 5): the `friction-report` job of `.github/workflows/checks.yml`, whose log and step summary carry the report.

- **The points, from git** (points 3, 4 and 9). The *revalidation point* is the last commit, following renames, in which the parsed value of `at` changed; for an artefact without `at`, the commit that introduced its block. A *deferral point* is the commit that first introduced the deferral entry, by anchor kind and value — rewording the reason does not move it — and a deferral covers its anchor up to that point only: a later change to the anchor is new friction, and an entry kept through a revalidation covers nothing after it. Both are derived by walking the artefact's file back from HEAD, no further than the oldest point in question: one `git log --name-status -M` from HEAD serves the whole check, matched in memory (which commits a point reaches, each file's names over time, which commits touched a path), and a file's earlier versions are read newest first through one `git cat-file --batch`, each judged against the file's state at its commit's own first parent — what `git log` diffed it against — so a commit on a merged branch is compared with its own ancestor, never with whatever the log lists next. A collection entry has its own points, read from its file's history under its id. An artefact **moved after its revalidation point** with no revalidation since is reported stale at the rename, since rename detection can hide earlier changes (point 3).
- **What it reads.** HEAD and its history, never the working tree: uncommitted work is counted in the header and left out. It needs the **full history**: in a shallow clone, an artefact whose revalidation point or deferral point lies beyond the cut is reported `unreachable` and not judged (`git fetch --unshallow`), and the header says the clone is shallow. Before the first commit the check refuses.
- **When an anchor changed** — the change check's rules, applied to every commit after the point rather than to one diff: a `path` anchor when such a commit touched a matching path (either side of a rename; excluded paths and the artefact's own file, under any of its names, ignored); a `record` anchor when one touched the record's file beyond a pure rename; an `artefact` anchor when the target's **content** at HEAD differs from its content as the point saw it — never anything inside the container, so an `unchanged` revalidation of the target stops the cascade. The **origin** of stale debt is the first commit after the point that changed the anchor (author, date, change); of deferred debt, the deferral point.
- **Findings**, grouped by artefact, upstream first along artefact anchors (point 11), each artefact's line naming its revalidation point:

| Kind | Meaning |
|---|---|
| `stale` | An anchor changed after the revalidation point beyond what a deferral covers, or the artefact moved after it with no revalidation. Carries its origin. |
| `deferred` | A deferral, with its point as origin; the human view adds its age. For the artefact's state, stale wins over deferred (point 10). |
| `dead-anchor` | At HEAD the anchor resolves to nothing — every one, not only a change's (point 7). |
| `unresolved-kind` | An anchor of a kind no installed component resolves. |
| `over-broad` | A path anchor matching more than half of the tracked files, excluded paths left out: *most* changes would be a revalidation, which teaches people to bump the marker blindly (point 7). The threshold is `OVER_BROAD_SHARE`, one half — the literal reading of "most" — judged on files because the share of files is what HEAD alone answers deterministically, without guessing at what will change next. |
| `unreachable` | A point beyond a shallow clone's history; the artefact is not judged. |
| `unreadable` | Front matter in a place that does not parse; `pkit validate` fails on it. |

- **The two measures** (point 8), after the findings, never failed: **unanchored artefacts** — every artefact in the places with no anchors, whether or not it carries the container; **uncovered surface** — the paths of the declared surface (`friction.surface` of the project and of each installed capability, excluded paths left out) that no artefact anchors to, where a path is anchored when a path anchor matches it, a record anchor names it, or an artefact anchor names the artefact it holds. Both are listed in full: the measure is the distance to a described surface, and the list is where to start.
- **Dormant** — exit `0`, no repository demanded — while no place is declared. With places declared and nothing anchored yet, the check runs and the measures show what remains (point 8): the state every project starts in.
- **`--json`** emits one stable document, keys sorted, identical for the same repository state (ages are the human view's, computed at the run): `check` (`repository`), `mode`, `dormant`, `failed` (always `false`), `head` (`commit`, `uncommitted_paths`), `history` (`shallow`), `counts` (places, artefacts, those carrying the container, `checked` — the artefacts with anchors or deferrals that were judged — `surface`, and one count per finding kind), `states` (artefacts by `current`, `stale`, `deferred`, `unreachable`), `artefacts` — one entry per checked artefact in report order: `artefact`, `location`, `state`, `revalidation_point` (`commit`, `author`, `date`, `change`; `null` when unreachable) and `deferral_points` (`anchor`, `point`) — `findings` in report order, each with `artefact`, `location`, `kind`, `anchor`, `origin` (the same four fields, or `null`) and `message`, and `measures` (`unanchored` locations, `uncovered_surface` paths). Against the change check's document: `check` differs, `origin` stands where `answer` stood, there is no `base`, and `history`, `states`, `artefacts` and `measures` are new.
- **Limits of the reading.** Renames are followed as git's rename detection pairs them commit by commit (`-M`), so a file rewritten beyond recognition in the same commit as its move reads as new there. A merge commit lists no paths, as `git log` prints none for it: the commits it merges carry the changes, and a change made only while resolving a merge is not seen — a marker or a deferral first set that way has its point at the commit that added the file. A record's file moved after the point is followed the same way as an artefact's.

### `friction debt [--json]`

The **debt listing** (COR-050 point 9): the debt derived from git, never kept in a ledger — every stale and deferred finding of the whole-repository check, oldest first.

- **Exactly what `check --all` reports**, from one run of the same check — never a second reading of the history: its `stale` and `deferred` findings, each with its kind, the artefact (id and location), the anchor (`—` for a move) and its **origin** — the commit, its author, its author date and its change (the commit's subject). Stale debt originates in the first commit after the point that changed the anchor, or in the rename that moved the artefact; deferred debt at its deferral point, and its reason is shown with it.
- **Oldest first**, by the author date of the origin; debts of the same date keep the check's order, upstream first. The human view adds each one's age.
- **What it reads** — HEAD and its history, like `check --all`: uncommitted work is counted in the header and left out. In a shallow clone an artefact whose points lie beyond the cut is named apart as not judged (`git fetch --unshallow`): its debt cannot be told. Dormant while no place is declared. It never fails: exit `0`.
- **`--json`** emits one stable document, keys sorted, no ages: `report` (`debt`), `dormant`, `head` (`commit`, `uncommitted_paths`), `history` (`shallow`), `counts` (`stale`, `deferred`, `unreachable`), `debt` — oldest first, each the `check --all --json` finding (`kind`, `artefact`, `location`, `anchor`, `origin`, `message`) with `reason` added (a deferral's; `null` for stale debt) — and `unreachable` (`artefact` and `location` of each artefact not judged).

### `friction explain <artefact> [--json]`

**One artefact's friction, explained** (COR-050 point 13): what makes it true, where its answers stand, what changed since, and what would clear each finding. `<artefact>` is named as the writers name one — its location (`path`, or `path#id` for a collection entry) or an id — and looked up at HEAD; a name that fits none, or more than one, is refused with what it could have meant.

- **Its findings are the whole-repository check's** for that artefact, in the same order: the same code judges it on the same history.
- **Points** — the revalidation point and each deferral point, commit and date, derived from git as `check --all` derives them.
- **Anchors** — each anchor HEAD declares, with what the check found: `stale` (with how many commits changed it since its point), `deferred`, `current`, `dead-anchor`, `unresolved-kind`, or `unreachable` while a shallow clone keeps the artefact from being judged; an over-broad one is marked.
- **What changed since each point** — every finding with the commits behind it, oldest first. A stale anchor: every commit after what covers it (the revalidation point, and a deferral up to its point) that changed it, its origin among them — for a `path` anchor the commits that touched a matching path, for a `record` anchor those that changed the record's file, for an `artefact` anchor those at which the target's content differs from its content at their first parent. A move: the rename. A deferral: the changes it postpones, after the revalidation point and up to the deferral point.
- **What clears each finding**, as the writer command that gives the answer, with a placeholder for the words only a person supplies. A stale anchor: `pkit friction revalidate <location> --outcome updated` (with the content change), `… --outcome unchanged --because '<why the content still holds>'`, or `pkit friction defer <location> --anchor '<kind:value>' --reason '<why it can wait>'`. A move: a revalidation only. A deferral: a revalidation that does not `--keep` it. Where no writer answers the finding, the edit it needs: a dead or over-broad anchor is corrected in the block and the artefact revalidated (a changed anchor list needs one); an unresolved kind needs its component installed, or the anchor removed; an unreachable point needs the full history. A revalidation answers every stale anchor at once and re-states the deferrals, so the human view names the ones to `--keep`.
- **What it reads** — HEAD and its history, like `check --all`: an artefact not committed yet is refused (commit first). An artefact with no anchors and no deferrals is `unanchored` — nothing to judge — and exits `0`; no place declared, or no commit yet, is refused.
- **`--json`** emits one stable document, keys sorted, no ages: `report` (`explain`), `head`, `history`, `artefact`, `location`, `state` (`current`, `stale`, `deferred`, `unreachable` or `unanchored`), `revalidation_point` and `deferral_points` (as in `check --all --json`), `anchors` (`kind`, `value`, `state`, `changes`, `over_broad`), and `findings` in the check's order, each with `kind`, `anchor`, `origin`, `message`, `commits` (oldest first, each `commit`, `author`, `date`, `change`), `clears` (how, in one line) and `answers` (each `answer` — `updated`, `unchanged` or `deferred` — and its `command`).

### `friction artefacts [--json]`

**Where the artefacts are**, as artefact discovery finds them (COR-050 point 1): the one computation of the places and what they hold, which `pkit validate`, the checks and the writers read too ([ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 2; `src/project_kit/friction_discovery.py`). It reads the working tree — the files git sees — and writes nothing. It is the seam through which a capability's own script reads the places: a script runs in its own environment and does not import the backbone, and it never re-reads the declarations or walks the places itself — what it decides over the answer, such as which of two matching places wins, is its own.

- Without `--json`, one line per place — its path, who declares it and in which location, how many files it matches, the synced copies it matches and why it is skipped — then the counts of files and artefacts.
- With `--json`, one stable document, keys sorted, the same bytes for the same state:
  - `schema_version` — `1`; raised when a key a reader relies on changes its meaning or goes, never for a key added.
  - `roots` — the documentation roots, `{user, internal}`, repository-relative ([COR-049](../decisions/core/COR-049-documentation-roots.md) point 1).
  - `places` — every declared place in walk order: the project's `friction.places` as written, then each installed capability's by name, a malformed declaration where it was written; then each rule-set folder the location rule names that no declaration already is ([COR-051](../decisions/core/COR-051-rule-sets.md) point 2). Each carries `source` (`project`, `capability:<name>`, or `backbone` for the backbone's rule-set folder), `declared` (false for a rule-set folder), `file` and `pointer` (where it is declared; a rule-set folder names itself), `written` (the path as written), `location` (for a capability place inside one of its documentation locations: `{name, path, root}` — the location's name, where it lies, the root its declaration names), `path` (the repository-relative path or glob the walk follows), `rule_sets` (`null`, or `{component}` when the place holds rule sets — the component whose method rule sets they are, `null` for the project's own), `encloses` (the roots, by audience, it reaches whole: it matches a document directly in the root and one three folders beneath), `files` (every Markdown file it matches, whichever place a file is read under), `synced` (the synced copies it matches, never walked — COR-050 point 14), and `skipped` (`null`, or `{reason, detail}` with `reason` `malformed` — a capability place not in the package schema's shape, which has no `path` — or `outside-repository`).
  - `files` — every Markdown file the walk read, by path: `places` (the indices of the places matching it; the first is the one it was read under), `rule_set` (the index of the rule-set place claiming it, or `null`), `excluded` (whether `friction.exclude` leaves it out), `fields` (its front matter as written, less the `pkit` container; `null` without a front-matter mapping), and `unreadable` (why the file or its front matter could not be read, or `null`). A link is never read, so never a file here.
  - `artefacts` — every artefact in walk order: `path`, `id`, `kind` (`document` or `entry`), `location` (`path`, or `path#id` for an entry), `place` and `rule_set` (indices), `container` and `friction` (whether it carries the container and a `friction` block), and `fields` (its own fields — the front matter or the entry, as written, less the container).
- Exit `0` when answered — no place declared is an answer, with no places; `1` when the configuration file exists but cannot be read (it does not parse, or is not a mapping), or outside a project, and nothing is printed on standard output; `2` on a usage error.

### `friction revalidate <artefact> --outcome <updated|unchanged> [--because <text>] [--keep <anchor>]... [--yes | --dry-run]`

Writes the artefact's **revalidation** (COR-050 point 3): the `revalidated` block, rewritten whole.

- **`at`** is the current UTC time, to the second — a second later if that equals the `at` already written, since `at` changes on every revalidation. Its commit becomes the revalidation point once committed.
- **`--outcome updated`**: the content changed with this revalidation; it carries no justification, and `--because` is refused. **`--outcome unchanged`**: the content did not need to change; `--because` is required and is written as `unchanged-because`, and it must differ from the justification already written (compared with whitespace folded, as the change check compares it) — the one piece of judgment the tool cannot supply, so a repeated one is refused.
- **Kept deferrals are re-stated deliberately** (point 4). A deferral is kept only when `--keep <anchor>` names it, or — on a terminal — when you confirm it at the prompt, one question per deferral, removing by default; every other entry is removed, and the output names each deferral it keeps or removes. A kept entry keeps its reason and its deferral point. Keeping a deferral the artefact does not have, or one whose anchor it no longer declares (it would dangle), is refused; an entry whose anchor is gone is always removed.
- It writes the marker; whether the diff bears the outcome out — `updated` with a content change, `unchanged` without one — is the change check's to judge (a `bump` otherwise).

### `friction defer <artefact> --anchor <anchor> --reason <text> [--yes | --dry-run]`

Writes one **deferral** (COR-050 point 4): the anchor's entry in `deferred`, inside `revalidated`.

- The anchor must be one the artefact carries; any other, and an empty `--anchor` or `--reason`, is refused. A new entry is added in its sorted place; an entry already deferring that anchor has its reason reworded, which keeps its deferral point — the commit that first introduced the entry — and the same reason again is a no-op.
- **`at` is never touched**, nor `outcome` or `unchanged-because` — their lines stay byte for byte: a deferral is not a revalidation. An artefact never revalidated gets a `revalidated` block holding `deferred` alone.
- The entry answers the anchor's change in the change check, and covers the anchor's changes up to the commit that introduces it; a later change is new friction.

### `friction record-status <artefact> [--yes | --dry-run]`

Writes the tool-written **status** (COR-050 point 10): `last-check`, from the whole-repository check at HEAD.

- `state` is the artefact's state there — `current`, `stale` or `deferred`, stale winning — `as-of` is HEAD, and `since`, when stale, is the oldest commit the staleness comes from (the origin of its earliest stale finding, by author date).
- **Written only when the status changes**: when `last-check` already records the same `state` and `since`, nothing is written and the command exits `0`, whatever its `as-of` — so a status that holds is never rewritten merge after merge. `last-check` sits inside the container, so writing it is no change to the artefact's content: it wakes no dependant and asks the change check nothing.
- It reads HEAD, never the working tree, like `check --all`, and says how many uncommitted paths it left out. Refused: an artefact with no anchors and no deferrals (it has no state), one not in HEAD yet, and one whose points lie beyond a shallow clone's history (`git fetch --unshallow`).
- It is the command a project's after-merge job would run (the `friction.status-job` setting of the configuration file); that job is not shipped yet, and the setting's default is `never`.

## Connections commands

The connection points of [COR-053](../decisions/core/COR-053-connection-points.md) — the roles a capability provides, the points their providers define, and the counterparts that plug into them — are declared in package metadata (the lifecycle README, "The connection, documentation and friction blocks") and resolved by the one wiring resolver ("How the wiring is resolved" there). `pkit validate` reports the resolution under `connections` and `versions`, and `pkit status` shows it under "Connections"; this group draws it, writes the one selection a person makes, and reads one data point as it resolves.

### `connections graph [--kind <kind>]... [--flow | --mermaid | --json] [--verbose]`

Renders the **one wiring graph** (COR-053 point 7), read-only: the process graph's topology with the wiring resolver's edges added — the wiring graph subsumes the process graph rather than sitting beside it. It is built from the two computations that already exist, the process definitions and the resolver's wiring, never a third ([ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 2; `src/project_kit/wiring_graph.py`). Every edge carries a `source`, and each kind of edge has exactly one:

| Source | Relation | Edge | Kind |
|---|---|---|---|
| `derived` | `composed-subprocess`, `aggregates` | a definition's `subprocess` / `cascade` block → the process it embeds or folds ([COR-038](../decisions/core/COR-038-process-connections.md)) | process |
| `annotated` | `informational`, `gates-on-readiness`, `triggered-by`, `constrained-with` | a definition's state → the upstream of its `depends_on` entry, in either address form: `<capability>:<process-id>`, or a role-addressed `<publisher>::<role>:<point>` | process |
| `resolved` | `offers` | the offered process definition `<provider>:<process-id>` → its process point — how a role-addressed `depends_on` reaches the process that answers it | process |
| `resolved` | `accepts` | a data point's provider → the point | data |
| `resolved` | `contributes` | a contributing capability → the data point it names | data |
| `resolved` | `fills` | the project's filler file → its data point | data |
| `resolved` | `emits` | an event's provider → the event | event |
| `resolved` | `subscribes` | a subscribing capability → the event it names | event |

- **The generated `depends-on` list is not drawn.** It is a machine-written copy of the definitions' `depends_on` (COR-053 point 4), whose edges the `annotated` rows already draw; drawing the copy too would draw one fact twice. Whether an entry binds — the version it targets, its upstream installed — is reported by `pkit validate` and shown by `pkit status`.
- **A resolved edge says how it stands**, in the `mode` field a process edge uses for `pull` / `push`: a definer's edge is `active` (its provider answers the role), `not selected` (another is selected) or `conflict` (several provide it and none is selected); a counterpart's is its binding — `bound`, `inert (version)`, `inert (provider)` (its capability provides a role and is not the selected provider), `no active provider`, `no such point`; a project filler's is `bound` or `inert (version)`. Every installed provider's points are drawn, active or not, and a counterpart whose target resolves nowhere is drawn to the address it names, so a dangling reference is visible. A project filler whose point no active provider defines is not drawn; `pkit validate` reports it.
- **The process graph's formats.** The adjacency view (the default) lists each node's out- and in-edges with a glyph and a `[relation · mode]` label: a definer's edge is marked `◇` (`◇ accepts` / `◇ accepted by`, `◇ emits` / `◇ emitted by`, `◇ offers` / `◇ offered by`), a counterpart's is an arrow (`→ contributes to` / `← contributed by`, `→ fills` / `← filled by`, `→ subscribes to` / `← subscribed by`). `--flow` and `--mermaid` as for the process graph, a resolved edge ending in a circle (`--o`) in mermaid. `--json` is the same byte-stable `{nodes, edges, skipped}`: each edge's `from`, `from_state`, `to`, `relation`, `mode`, `source` and `why` — for a resolved edge, the declaration's description, which people read in the graph (COR-053 point 3); `--verbose` shows it in the text views.
- **`--kind <data|process|event>`**, repeatable, keeps the edges of those kinds. A view shows the nodes its edges touch, as the process graph's filters do.
- **Deterministic, declarations only.** The same repository state renders the same bytes, in the process graph's total order. No filler command runs and no process position is resolved.

**The graph relation: `process graph` is this graph filtered to its process edges.** `pkit process graph` renders the process kind of the wiring graph — the derived and annotated edges it always drew, and the `offers` edges — and applies its atomic filters and presets to that view (its `--source` takes `resolved` too). Nothing it drew before is removed, and with no filter `pkit process graph --json` and `pkit connections graph --kind process --json` are the same bytes: one graph computation, which a test holds.

### `connections providers set <role> <capability> [--yes | --dry-run]`

Selects `<capability>` as the provider of the qualified role `<role>` (`<publisher>::<role>`): writes the **provider-selection key** of the configuration file, `connections.providers.<role>: <capability>` (COR-053 point 7; "Configuration file" above).

- **Checked first.** `<capability>` must be installed and declare `<role>` among the roles of its package metadata, read as the wiring resolver reads them — the reading the configuration pass checks an existing entry against, so a selection this command writes is one `pkit validate` accepts. Otherwise it refuses and writes nothing, naming the roles the capability does provide and, for each installed provider of the role, the command that selects it.
- **Written through the consent-gated writer** (COR-048 point 5). The diff of `.pkit/project/config.yaml` is shown first, computed by the writer's own path, so it is exactly what the write makes; `--dry-run` stops there and writes nothing; `--yes` writes; without either, a terminal is asked after the diff, and a non-interactive run refuses, naming the command with `--yes`. The rest of the file — other keys, comments, its header — is kept; a file it creates opens with the editor directive. The same selection again writes nothing. `--yes` and `--dry-run` exclude each other.
- **The fix a role conflict names.** When several installed capabilities provide one role and none is selected, `pkit validate` fails under `connections` naming this command once per provider, and `pkit status` lists a `fix:` line per provider under the role.

The contributor-selection key, `connections.selections`, has no command of its own; `pkit config set connections.selections.<address> <capability>` writes it.

### `connections resolve <address> [--json]`

Resolves the data point `<address>` (`<publisher>::<role>:<point>`) exactly as `pkit validate` reports it and `pkit status` shows it — its fillers combined by its policy ([COR-052](../decisions/core/COR-052-slots.md); the lifecycle README, "How a data point resolves") — and prints it. Read-only: it writes nothing, and command fillers run as they do there, under the query policy (`--json` alone, offline-marked, bounded). It is the seam through which a capability's own script reads a point it defines — a script runs in its own environment and does not import the backbone — and then applies the value itself, since a data point is a value and takes no parameter (COR-052 point 6).

- Without `--json`, the point's lines of the status report's "Data points" section.
- With `--json`, one stable document: `address`; `defined`; `provider`; `policy` and `inert_policy`; `participation` (the default's, or null); `resolved`, and `why` when not; `value` — null when the point does not resolve, never a partial value; `origin` (a `single` point's answering filler); `entries` (a `union` or `additive` point's, each `{id, origin, replaces, value}`, `origin` being a capability, `project filler` or `the default`); `removals` (each `{id, reason, removed_from}`); `fillers` (each `{source, name, supplies, state, reason, query_contract}`, `state` one of `taken`, `inert`, `passed over`). An address no active provider defines as a data point prints `{address, defined: false, resolved: false, value: null, why}`.
- Exit `0` when the point resolves; `1` when it does not, or nothing defines it; `2` when `<address>` is not a point address.

## Process commands

The process-substrate engine's surface (`pkit process status / can-move / move / validate / cascade / graph / health`) is specified operation-by-operation in the process area (`.pkit/process/README.md`, "The engine") — the engine's contracts live there with the shape reference, per COR-033. This section specs the commands whose contracts are CLI-owned rather than engine-owned: the health check and the three authoring stamps. `process graph` is the process view of the one wiring graph: its edges and formats are specified under "Connections commands" above, the graph relation.

**Why the authoring stamps are `process new` and not `new process`.** Every other authoring stamp is a sub-verb of the `new` family (`new decision`, `new area`, `new capability` — see "Authoring commands"). The three process stamps are **deliberately** sub-verbs of `process` instead, because they are a family in their own right: `new`, `couple`, and `hand-off` all take the same `<capability>:<process-id>` address argument and all read the same shape contract, and two of the three mutate an *existing* definition, which the one-shot `new` family does not do. Grouping them under the address they share keeps that family visible; grouping them under `new` would split it across two namespaces and leave `couple` / `hand-off` homeless. The divergence is recorded here rather than left to be noticed: moving these verbs later is a CLI signature change, and would owe a migration (COR-010).

**All three stamps require a *registered* owning capability.** The gate, its three distinct refusals, and the no-manifest fallback it preserves are specified once under `process new` below; `couple` and `hand-off` apply the same check on the definition they are asked to mutate.

**Correcting a declared coupling or contract.** `couple` and `hand-off` refuse to overwrite a declaration that differs from what you asked for — deliberately, since a declared edge is a decision, not a draft. There is as yet **no stamp that edits one back**: repair rides with `amend`, the named-deferred operation for definition evolution (COR-044's deferred family). Until it ships, the interim route is to edit the `depends_on` entry in your own definition by hand and re-run `pkit process validate` — the one place where hand-editing a definition is the sanctioned path rather than a violation of it (core rule 3 governs *stamping* an artifact; there is no stamp to invoke here yet).

### `process health [--process <addr>] [--interpretation-only] [--json]`

Walk every declared **hand-off contract** — the opt-in `handoff` sub-block on a `depends_on` entry (per [COR-042](../decisions/core/COR-042-process-health.md)) — and report every **missed hand-off**: an upstream subject currently at its trigger state with no downstream subject picking it up.

Takes **no subject** (unlike `validate`): it walks contracts across the configured wiring. For each contract it resolves the upstream definition, runs the binding-supplied `candidates` source, confirms each candidate **one subject at a time** through the engine's own per-subject position resolution, and asks the binding's `resolve` predicate for the downstream counterpart (the two-predicate seam, per [ADR-048](../../tech-docs/architecture/decisions/ADR-048-handoff-resolve-seam.md)). Entries without a contract are never evaluated.

- **A role-addressed upstream** (`<publisher>::<role>:<point>`, per [COR-053](../decisions/core/COR-053-connection-points.md) point 2) is the process the role's **active provider** offers at that address, read from the wiring resolver — resolved once per run, and only when some contract names its upstream by role. No installed provider, providers in conflict with none selected, or no process offered at the address makes the contract **indeterminate**, the reason named. The report shows the address as declared, and the `candidates` seam receives it as declared.

- **Report-only.** No move is blocked, nothing is journaled or remediated; the check reads live positions and is safe precisely because nothing rides on the read. The at-trigger snapshot is live per run (a red produced by a race is an honest answer about the instant evaluated).
- **Fail-closed indeterminacy, distinct from a miss.** An uninterpretable contract (unresolvable upstream address, phantom trigger state, malformed block), an erroring/unavailable candidate source, an unreadable upstream position, or an erroring `resolve` reports **indeterminate** — never "nothing missed". A candidate source that evaluates cleanly to zero subjects is a determinate, clean answer. A process definition that cannot be loaded at all is surfaced and counted indeterminate (its contract set is unknown).
- **Exit code:** `0` only when misses **and** indeterminates are both zero; `1` on any miss or indeterminate (one non-zero code — miss-vs-indeterminate is distinguished in the report, not the exit code).
- **Deterministic report.** Couplings render flow-direction (`upstream → downstream   @trigger`, grouped per contract, one line per missed/indeterminate upstream subject — a satisfied subject produces no line) and order **topologically over the contract wiring**: upstream-most process groups first, name tie-breaks, deterministic name-order fallback on declared cycles; subjects name-sorted. No time/age-based ordering. Summary line: `N missed, M indeterminate`.
- **`--process <addr>`** keeps only contracts touching that `<capability>:<process-id>` as either endpoint — a role-addressed upstream counts as both its declared address and the implementation it resolves to. **`--json`** emits the byte-stable machine form: per-contract objects (`upstream`, `downstream`, `trigger`, `state`, `misses[]`, `indeterminate[]`, `counts`) plus `skipped[]` (unloadable definitions), `unresolved_scope` (below — `null` on any run that resolved its scope) and `totals`.
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

### `process couple <addr> --state <s> --upstream <addr> --relation <r> --mode <m> --why <prose> [--version <n>] [--mandatory <reason>]`

The stamp under the skill's `couple` operation: append a `depends_on` entry ([COR-038](../decisions/core/COR-038-process-connections.md)) to the **invoker-named** definition's hosting state — coupling lives in the subscriber; the upstream is never touched (the owner-scoping COR-044 fixes by construction).

- `--upstream` takes either form the shape contract's address grammar admits: the implementation form `<capability>:<process-id>`, or the role form `<publisher>::<role>:<point>` — the process offered at that point by the role's active provider ([COR-053](../decisions/core/COR-053-connection-points.md) point 2). An address outside the grammar refuses.
- `--relation` / `--mode` are validated against the **closed vocabularies read from the shape contract as data** — a new relation kind is an enum value the command picks up, never a code change. `--why` is required (COR-038).
- `--version <n>` (an integer, at least 1) writes the entry's `version`: the upstream interface version it targets, connecting only to an offered process at an equal one (COR-053 point 5). `--mandatory <reason>` writes the mark `mandatory: { reason: <reason> }` (point 6); a blank reason refuses. Each key is written only when its flag is given, after `why`.
- **No version bump:** the entry is additive, inert metadata (COR-044's version semantics — state/transition evolution is the deferred `amend` operation, which does bump).
- An upstream that does not resolve locally is declarable (warned, not refused — the entry is inert; a later hand-off contract on it would report indeterminate). A role address is resolved through the wiring resolver, as `health` resolves it, and the warning says why it reaches no process. Round-trip edit (comments and layout preserved); the result is re-linted and the prior file restored on any failure.
- **An entry is identified by `(upstream, relation, mode)`.** The shape places no uniqueness constraint on `depends_on`, so one state may legally depend on the same upstream in two different ways (an `informational` pull beside a `triggered-by` push) — a second entry with a different relation or mode is appended, not refused. The identical entry (that key plus the same `why`, `version` and mark) is a clean no-op; the same key with a **different `why`, `version` or mark** is a genuine divergence and refuses, naming what the declared entry says. See "Correcting a declared coupling or contract" above for the repair route.
- **The refresh step.** The stamp writes the definition and never package metadata. When the capability's generated `depends-on` list ([COR-053](../decisions/core/COR-053-connection-points.md) point 4) is stale afterwards — whether this run made it so or it already was — the output ends with a `Next:` line naming `pkit capabilities refresh <capability>`; run it, or `pkit validate` fails. Under `--dry-run` the same line appears when the previewed entry would leave the list stale. A coupling that generates nothing new — another way of depending on an upstream already listed, at the same version and mark — names nothing.

### `process hand-off <addr> --upstream <addr> --trigger <state> --candidates <cmd> --resolve <cmd> [--state <s>]`

The stamp under the skill's `hand-off` operation: add a [COR-042](../decisions/core/COR-042-process-health.md) hand-off contract — the `handoff` sub-block (trigger + the two seam predicate refs) — to an **existing** coupling on the invoker-named definition. Refuses when no `depends_on` entry for the upstream exists (`process couple` first); `--state` disambiguates when the same upstream is coupled on several states.

- **Trigger validated where resolvable:** when the upstream definition loads, a trigger that is not one of its states is refused (a phantom trigger would report indeterminate forever); an unresolvable upstream degrades to a warning — health reports the contract indeterminate until it resolves, never silently green. A role-addressed upstream (`<publisher>::<role>:<point>`) is resolved through the wiring resolver, as `health` and `couple` resolve it: the trigger is checked against the process the role's active provider offers there, and a role that reaches no offered process is warned about with the resolver's reason. Declare a **stable** trigger state (the ephemeral-trigger authoring smell, COR-042).
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
resolved through the capability dispatcher and run under the backbone's
thirty-second command bound (the lifecycle README, "How a registered command
is run"), so the backbone never reads pm's `workstreams.yaml` or labels
itself; `--workstream <name>` overrides, and pm-absent / underivable simply
omits the half — a verb that overruns the bound is stopped, and the report
warns and goes on without it. A successful
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
- **`--dry-run`** on every mutating command (`init`, `sync`, `merge`, `upgrade`, `capabilities install`, `capabilities register`, `capabilities uninstall`, `capabilities upgrade`, `capabilities refresh`, `process new`, `process couple`, `process hand-off`, `friction revalidate`, `friction defer`, `friction record-status`). Shows the plan without applying any changes. On the process stamps it runs every check a real run runs, including the shape lint of the would-be definition, and reports the stubs it would scaffold.
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
