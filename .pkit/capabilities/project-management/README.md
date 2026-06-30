# project-management capability

A project-management discipline an adopter installs to get a team-wide rulebook for filing, validating, and transitioning work — encoded as data the engine reads at runtime. Issue hierarchy, state machine, body shape, title format, branch and PR conventions, validation severity, and time containers are all schemas; the skills and agent are methodology-agnostic and act on whatever the schemas say.

Install this capability when:

- Your team wants a single rulebook for project-management work across multiple projects, not folklore re-invented per project.
- You want AI agents to file, validate, transition, and close issues *mechanically* — the methodology in data, not in agent prompts.
- You're on GitHub (Issues, sub-issues, Milestones, Projects v2). The methodology binds to GitHub primitives directly; it does not transfer to Linear/Jira without rewriting.

Skip it for solo projects with no shared methodology, for teams whose tracker is not GitHub, or for projects where ad-hoc issue management is sufficient.

## Relationship to the pm-workflow spec

This capability is the **operational realization** of the [pm-workflow](https://github.com/aleskalfas/pm-workflow) methodology. pm-workflow is the *spec* — the team's authoring workspace where the methodology is iterated, debated, and ratified (its `MET-NNN` decisions, its narrative `METHODOLOGY.md`, its review-agent ceremony). This capability *distills* that spec into a form `pkit` can install: per-decision DECs that cite their `source: MET-NNN` upstream, schemas that encode the operationally-material rules, and an engine that consumes them.

The authority signal for distillation is pm-workflow's `main` branch. Capability DECs carry the upstream commit SHA in their `source:` frontmatter; readers can always walk back to the MET they came from. See `decisions/DEC-001-distillation-lineage.md` for the contract.

## What this capability ships

`pkit capabilities install project-management` copies the following into the adopter's `.pkit/capabilities/project-management/`:

- `decisions/DEC-NNN-*.md` — principles distilled from pm-workflow's METs (1:1). Some are schema-backed; others ship as policy prose adopters read.
- `schemas/<name>.yaml` + `<name>.schema.json` — the operationally-material rules in data form: issue hierarchy, workflow state machine, body shape, title regexes, label classification, git conventions, validation severity, time containers.
- `skills/pm/` — the composite engine skill (`pm.md` dispatcher + `create-issue.md` + `validate-body.md` + `transition-state.md` sub-procedures, per COR-020). Methodology-agnostic; reads schemas at runtime.
- `agents/project-manager.md` — orchestrates the three skills, enforces methodology gates.
- `templates/{EPIC,Feature,Umbrella,Task,PR}.md` — body shapes adopters fill in.
- `scripts/pre-check.py` — read-only diagnostic verifying every methodology prerequisite is in place (DEC-017). Hard-gate on every pm operation.
- `scripts/bootstrap.py` — first-time setup. Creates the required initial GitHub state (labels per classification axes; optionally a starter EPIC). Additive idempotent.
- `scripts/migrate.py` — adopter-state reconciliation after capability upgrades. Reads `migrations/<version>.yaml` manifests; per-change confirmation gates on every destructive step.
- `migrations/` — versioned manifests of adopter-state changes the capability has shipped. Empty in v0.2.0; populated on subsequent surface changes.

The engine is **methodology-agnostic by design**: when the methodology evolves upstream, schemas change; the engine picks up the new rules automatically without skill-code edits. Adding a state, a new issue type, or a new title regex becomes a schema edit.

## Adopter setup

> **Short form**: every `pkit project-management <subcommand>` shown below also works as `pkit pm <subcommand>` — the capability registers `pm` as an alias via `aliases:` in its `package.yaml`. Both resolve to the same dispatch group; pick whichever reads better.

Four phases, in order:

### 1. Install

```
pkit capabilities install project-management
```

Copies the capability subtree into the adopter and registers it in the backbone manifest.

### 2. Author the project-side config

Create `.pkit/capabilities/project-management/project/config.yaml` declaring the adopter's specifics:

```yaml
schema_version: 1
default_branch: main                  # the repo's default branch
has_projects_v2_board: false          # set true + projects_v2_board_id when a board is configured
workstreams:                          # one entry per allowed workstream value
  - capabilities
  - schemas
  - cli
# Optional:
# projects_v2_board_id: 12
# code_path_to_doc_mapping: { src/foo/**: [docs/foo.md] }
# pre_close_triage_lead_days: 3
# gh:                                 # per DEC-023 — both fields optional
#   host: github.com              #   target a non-`github.com` host
#   default_owner: ai-platform-incubation   # spliced as `--owner` on cross-owner ops
```

This config is adopter-owned. The capability's schemas are immutable kit-shipped content per the no-shared-files invariant; the config is the seam where adopter-specific values plug in.

#### The `gh:` block (per [project-management:DEC-023-gh-host-and-owner])

Adopters whose GitHub host is not `github.com` (Enterprise GHE deployments such as `github.com`), or whose Projects v2 board lives in a different owner from the repo, declare this in the `gh:` block:

- **`host:`** — the GitHub host every `gh` shell-out should target. When set, the kit threads `GH_HOST=<host>` into every `gh` invocation and pre-check verifies `gh auth status -h <host>` succeeds. Single-org `github.com` adopters omit the field.
- **`default_owner:`** — the owner spliced as `--owner` on cross-owner operations (board / org / cross-owner labels). Single-owner adopters whose board lives in the repo's owner omit the field.

Both fields are optional and additive — an existing config without a `gh:` block continues to validate. **Config wins over ambient** per DEC-023: if both `GH_HOST` is set in the shell and `gh.host` is configured, the config value reaches `gh`. This makes the methodology reproducible from `config.yaml` alone.

> At v0.5.0+ workstreams move from `config.yaml`'s bare list into a dedicated `.pkit/capabilities/project-management/project/workstreams.yaml` file with full attributes (status, deprecation reason, etc.) per [project-management:DEC-018-workstream-taxonomy-and-lifecycle]. The `config.yaml` form keeps working as a fallback during transition; the v0.5.0 PR ships a migration that bridges installed adopters.

### 3. Bootstrap

```
pkit project-management bootstrap
```

(Or the direct-path equivalent `.pkit/capabilities/project-management/scripts/bootstrap.py` — both forms work per the capability-command-dispatch convention from COR-021.)

Reads the config and the capability's schemas; creates the methodology's required GitHub labels. Additive idempotent — re-running on a fully-bootstrapped repo creates nothing.

**Labels created by bootstrap:**

- `type:*` (always) — one label per type value in `classification.yaml`.
- `priority:*` (label-fallback mode) — one label per priority value.
- `workstream:*` (label-fallback mode, per declared workstreams).
- `state:*` (label-fallback mode) — one label per lifecycle state in `workflow.yaml` (`state:todo`, `state:backlog`, `state:in-progress`, `state:review`, `state:done`). These are the substrate for `move-issue`'s state machine on label-fallback adopters.

Board adopters (`has_projects_v2_board: true`) skip `priority:*`, `workstream:*`, and `state:*` labels; those axes live as Projects v2 fields instead.

Optionally, file a starter EPIC so subsequent Task filings have a default parent:

```
pkit project-management bootstrap --with-starter-epic
```

EPICs are PM-authority filing per [project-management:DEC-008-pm-and-implementer-roles]; the flag is the PM's explicit authorisation gesture.

### 4. Verify with pre-check

```
pkit project-management pre-check
```

Read-only diagnostic. Walks every prerequisite the methodology depends on (gh auth, repo accessible, required labels present, default branch matches, config parses). Exit zero when every check passes; non-zero with remediation hints when something is missing.

Pre-check is the **hard gate** on every pm operation per [project-management:DEC-017-prerequisites-bootstrap-migrate-discipline]. The project-manager invokes it as Step 0 of every action; CI workflows wire it in as a PR check.

**What pre-check covers at v0.17.0+:**

| Check | Label |
|---|---|
| `git`, `gh` on PATH | tooling |
| `gh auth` active (ambient) | auth |
| Adopter config present + parses | config |
| `gh:` block valid; host-pinned auth works | config / DEC-023 |
| Repo accessible | connectivity |
| Projects v2 board resolves (board mode) | substrate |
| `type:*` labels present | labels |
| `priority:*` / `workstream:*` labels present (label-fallback) | labels |
| `state:*` labels present (label-fallback) | labels — new in v0.17.0 |
| Default branch matches config | config |
| `workstreams.yaml` parses cleanly | config / DEC-018 |
| `mandatory-issue-state.yaml` present + valid | schema / DEC-019 |
| Mesh config URIs valid | config / DEC-022 |
| `hooks.yaml` shape + per-kind validation | hooks / DEC-024 |
| `review:` block valid | config / DEC-027 + DEC-028 |
| Title-prefix alignment (sample of open issues) | data quality — new in v0.17.0 |

### 4b. (Optional) Smoke-test the installation

```
pkit project-management self-test
```

Creates a throwaway issue, advances it through the full state machine (create → backlog → in-progress → backlog → close), then cleans up. Catches transition / identity-resolution / label-routing bugs before adopters hit them in real work.

Use `--dry-run` to preview the plan without mutating. Use `--skip-cleanup` to leave the issue/milestone open after a failed run for debugging.

Each step prints `[ok]` or `[fail] <reason>`. Final summary line: `self-test: N passed, M failed`. Exit non-zero on any failure.

### Then use

```
claude --agent project-manager "File an EPIC for <outcome>"
```

The project-manager walks the methodology end-to-end: picks a title matching the EPIC pattern, fills the body against the template, validates against the body-format and validation-severity schemas, creates the GitHub issue, runs the cascade check.

#### Issue body — parent-ref first line

Every non-EPIC body opens with a parent-ref on the first line. The ref form depends on the parent type:

- **Issue parent** (EPIC, Feature, Umbrella): plain `<Label>: #<N>` — e.g. `EPIC: #42`. GitHub auto-links `#42` correctly to that issue.
- **Milestone parent**: `Milestone: [#<N>](../milestone/<N>)` — e.g. `Milestone: [#6](../milestone/6)`. The explicit markdown link is required because GitHub auto-links bare `#N` to an *issue*, not a milestone. `create-issue --milestone <N>` emits this form automatically.

EPIC bodies may omit the parent-ref line entirely (EPICs are not always scheduled under a milestone when filed).

`validate-issue` enforces these forms. The old plain `Milestone: #<N>` form is accepted with a deprecation warning during the grace period; update existing bodies to the link form.

For an **issue parent**, `create-issue --parent <N>` also sets GitHub's **native sub-issue link** between the new child and the parent, *in addition to* the textual first-line ref (per [project-management:DEC-005-linking-and-containment]: native sub-issues are the canonical containment mechanism; the textual ref is the universal spine). The native link is what surfaces the child in the parent's sub-issues panel and feeds the Projects v2 "Sub-issues progress" field. It is idempotent (re-linking an already-linked child is a no-op) and degrades to a no-op where the instance does not support sub-issues (e.g. an older GHES / the feature off) — the textual ref carries the relationship in that case, and a native-link failure never fails the create. A milestone parent (`--milestone`) is not a sub-issue relationship and carries its own native Milestone field, so no sub-issue link is set for it. The native write goes through `scripts/_lib/containment.py` as a single construction point (the ADR-031 sole-constructor discipline applied to the containment substrate), reusable by any future parent-link mutation.

The **containment substrate is selectable** (per [project-management:DEC-039-containment-substrate-selection], contract ADR-035) via a top-level `containment: native | textual` key in the optional brownfield `substrate-map.yaml` (`schemas/substrate-map.yaml` documents the axes; the selector is a manual operator key beside `hierarchy:`, not a per-axis binding). `native` (the default, and the greenfield behaviour when no map is present, or when the key is absent from a present map) sets the native sub-issue link as described above. `textual` — for a tracker that does not support native sub-issues, or an operator who prefers the textual representation — makes `create-issue --parent` record *only* the textual child-side parent-ref and **skip the native link entirely**. The textual ref is the universal spine, written in **both** modes (so it is the containment record in `textual` mode). The selector intent lives in the committed map; no resolved value is written back (one-consumer contract). The mode resolves through the same substrate-map read seam (`scripts/_lib/axis_labels.containment_mode`) the other axes use.

In `textual` mode a parent has no native sub-issues panel, so its **parent-side children view is render-on-demand** (per DEC-039 D4 / ADR-035 section 4): a generated **do-not-edit children comment** on the parent, written by **full overwrite** through one construction point (`scripts/_lib/containment.refresh_children_comment`) and refreshed by the read path. The comment is a *derived, regenerable view* — the child-side ref + the `resolve_children` read-seam remain the source of truth; it is **never an append** (there is exactly one marked comment per parent, found by its `<!-- pkit:children-view do-not-edit -->` marker and updated in place). It carries a visible "do not edit — auto-generated" notice so a human knows not to hand-edit it, and lists each child as a `#<n>` link (a textual-only child is marked `(textual)`). The refresh is **idempotent** — re-rendering the same child set is a no-op (no comment-edit churn) — and **failure-posture-neutral**: a failed refresh is reported as a one-line note and never fails the create (the textual ref is the spine). It is a **no-op in `native` mode** (the native panel already gives parent-side visibility). Refresh triggers: automatically on **child-create** (`create-issue --parent` in textual mode, after the textual ref is written), and explicitly via **`show-tree --refresh-children-views`** (textual mode only; a write, so it is gated by the foreign-repo session guard). Like the native link, the comment write goes through `scripts/_lib/containment.py` as a single construction point under the same grep/AST sole-constructor guard (`tests/test_pm_containment_write_seam.py`).

#### Issue body validation — residual placeholder detection (per [project-management:DEC-031-reject-unauthored-placeholder-bodies])

`validate-issue` detects bodies that still carry the stamped template skeleton the author was supposed to fill. Two signals, both derived structurally from the live template at runtime:

- **Empty required checkbox section** — a required checkbox section (per [project-management:DEC-010-issue-body-minimum-structure]) with **zero authored items** is the primary "unauthored" signal. An *authored item* is a checkbox line with non-whitespace content after the `]`, regardless of checked state — `- [ ] Real criterion` and `- [x] Real criterion` are both authored; a bare `- [ ]` (nothing after) is a skeleton item. Severity: `warning` at `create-issue` (the issue is filed, but the warning is visible); `hard-reject` from the **first lifecycle transition** (Todo → Backlog) onward. Lenient: a trailing bare `- [ ]` alongside real authored items is fine — only a section with *no authored items at all* triggers.
- **Surviving template placeholder prose** — if the body still contains placeholder text from the template (e.g. "The thesis or outcome being de-risked…"), `validate-issue` emits a `warning` at every validation call. Detection is runtime-derived from the matching `templates/<Type>.md`, so it stays in sync automatically when a template is edited.

The asymmetry is deliberate: `create-issue` keeps stamping the template skeleton for the author to fill (stamp-then-fill workflow is preserved), and a just-filed Todo that cannot advance is harmless. The **block** lives at the first transition — that is where the harm of an unauthored body advancing through its whole lifecycle is closed.

`create-issue` always emits the warning when filing an unauthored body; it never silently admits one.

#### PR body validation — residual placeholder detection (per [project-management:DEC-031-reject-unauthored-placeholder-bodies])

`validate-pr` applies the same two-signal rule to PR bodies, derived structurally from `templates/PR.md` at runtime:

- **Empty required checkbox section** — same authored-item definition as the issue side. Severity: `warning` when the PR is opened (`create-draft` / `review-work`); `hard-reject` at the merge gate — `done-work` refuses to squash-merge a PR whose body still carries the raw `## Summary` skeleton with no authored checkbox items.
- **Surviving template placeholder prose** — if the body still contains placeholder text from `templates/PR.md`, `validate-pr` emits a `warning` at every validation call. Detection is runtime-derived from the live template, so it stays in sync automatically when the template is edited.

The trigger asymmetry mirrors the issue side: a PR opened with an unauthored body is visible (warning surfaced immediately) but not blocked; the **hard-reject** fires at `done-work`, where merging an unauthored PR body causes the actual harm. `done-work` always runs `validate-pr` before entering the approval gate; a placeholder-body failure is reported and the merge is refused.

#### The seven workflow wrappers (per [project-management:DEC-026-work-ownership-lifecycle])

For the standard development flow, seven verb-subject commands compose over `move-issue` and own the side-effects (branch, PR, merge, audit comments) at each step. They replace ad-hoc combinations of `move-issue` + `gh` calls that adopters previously had to wire by hand.

| Command | Issue transition | Side-effects |
|---|---|---|
| `promote-issue <N> [--milestone "<M>"] --reason "<R>"` | Todo → Backlog | Audit comment; milestone attach only when `--milestone` is given (omit to promote on `--reason` alone — per DEC-026 #61 amendment) |
| `start-work <N>` | Backlog → In Progress | Branch `<type>/<N>-<slug>` + assignee |
| `create-draft <N>` | (none — issue stays In Progress) | Opens draft PR via `gh pr create --draft` |
| `review-work <N> [--reviewer @<u>]` | In Progress → Review | Opens ready PR or flips draft→ready; assigns reviewers |
| `back-to-draft <N>` | (none — issue stays in Review) | Flips PR to draft; dismisses prior APPROVED reviews |
| `done-work <N> [--bypass "<R>"]` | Review → Done | Squash-merge via three-way approval gate (APPROVED review / `Approved`-prefix comment / `--bypass`); pulls main |
| `handoff-issue <N> --to @<u> --reason "<R>"` | (none — no state change) | Audit comment + reassign |

All seven are idempotent at the level of observable state — re-running after a partial failure recovers cleanly. Audit comments use DEC-024's template-stamp markers (`<!-- pkit-hook: <name> -->`) so re-posts detect existing entries and skip.

#### Batch substrate primitives — `check-criterion` / `uncheck-criterion` / `set-field` (per [project-management:DEC-038-criterion-addressing])

Three narrow, batch-capable verbs replace the whole-body fetch-edit-resend that `edit-issue` forces for a single checkbox flip or field change. Each takes narrow input, validates the **whole batch up front**, refuses before any mutation on a hard inconsistency, and applies **idempotently** so a half-applied batch recovers by re-running. Output is a single clean line per result — nothing to pipe through `grep`.

| Command | What it does |
|---|---|
| `check-criterion <issue> <index> [text] [<index> [text]] ...` | Tick one or more acceptance-criterion checkboxes, addressed by **1-based index** (matching `show-issue --field criteria`'s numbering) with an optional **expected-text guard**. |
| `uncheck-criterion <issue> <index> [text] ...` | Untick — the symmetric counterpart; identical addressing and failure model. |
| `set-field <issue> [--priority X] [--workstream Y] [--parent N]` | Declaratively set classification field(s) in one call. Priority/workstream resolve through the same seam `create-issue` uses (substrate-map-aware); `--parent` rewrites the body's first parent-ref line. Under a Projects-v2 board, priority/workstream live on board fields — `set-field` reports a degrade note and does not touch a label. |

**Addressing a criterion** (`check`/`uncheck`): the **index** is the primary address; the optional **expected-text** is both a wording-based double-check and a guard that the box has not moved between read and write. The guard rule is **equality on the trimmed, checkbox-marker-stripped text** — copy it verbatim from `show-issue --field criteria` output. Each guard follows the index it guards (`check-criterion 239 1 "docs updated" 3`).

**Failure + recovery** (DEC-038 D4) for all three:

- **Index out of range** → refuse the whole batch; report the criterion count. Never create a checkbox.
- **Expected-text mismatch** (criteria reordered between read and write) → refuse; report the actual line so the caller re-reads. Never tick blind.
- **Ambiguous guard** (text matches more than one criterion) → refuse and list the matches; ambiguity never silently resolves.
- **Unknown field value** (`set-field`) → refuse before any mutation, listing the adopter's declared values.
- **Already in the requested state** → no-op success. Ticking a ticked box, or setting a field to its current value, is not an error.
- **Half-batch faults mid-apply** → re-run is safe: applied targets no-op, the rest complete.

```
pkit pm check-criterion 239 1 3 5            # tick criteria 1, 3, 5 in one call
pkit pm check-criterion 239 2 "docs updated" # tick #2 only if it still reads "docs updated"
pkit pm uncheck-criterion 239 2              # untick #2 (idempotent)
pkit pm set-field 239 --priority High --workstream cli   # set both, idempotently
pkit pm set-field 239 --parent 42            # rewrite the parent-ref line to Feature: #42
```

All three accept `--dry-run` (validate + show the plan, write nothing) and `--yes` (skip the confirmation prompt), and run the DEC-021 membership gate at startup.

**`close-issue`** is *not* in the seven-command palette — it handles closure outside forward-progress flow: won't-do / abandonment (`--mode=wont-do`), the post-PR-merge cascade hook (`--mode=pr-merge`), and **cascade-eligibility closure** of a container (epic/feature/umbrella) once all its children are closed and its own checkboxes are ticked (`--mode=cascade-eligibility-close`, a non-skippable DEC-007 gate).

**Review-mode resolution** is settled in [project-management:DEC-027-review-modes] (mode lookup) and [project-management:DEC-028-agent-as-approver-paths] (agent gate).

#### Read-only diagnostics — `show-issue` / `show-pr`

Both surface the methodology-relevant view of an existing issue / PR. Three output modes:

- **Default** — a terse, human-readable summary with banner and labels.
- **`--json`** — the full summary structure as machine-readable JSON.
- **`--field <name>`** — print just one field's value with **no surrounding chrome** (no banner, no label, no heading), so an agent can capture a single value as a *bare* command instead of piping the full view through `grep`/`tail`. Scalars print bare; lists print one item per line; `sections` prints one `present`/`absent` line per required section; `body` prints verbatim. An absent field (e.g. a missing milestone) prints nothing and still exits 0.

`--field` and `--json` are mutually exclusive — passing both is a usage error (non-zero exit). An unknown field name fails to stderr listing the valid field set (non-zero exit); the same set is shown in `--help`.

Addressable fields:

- **`show-issue`**: `title`, `type`, `state`, `assignees`, `milestone`, `parent`, `priority`, `workstream`, `labels`, `criteria`, `sections`, `body`, `url`.
- **`show-pr`**: `title`, `state`, `draft`, `base`, `head`, `merged-at`, `cc-type`, `cc-summary`, `closes`, `reviewers`, `doc-impact`, `body`, `url`.

```
pkit pm show-issue 318 --field state          # -> in progress's state, e.g. `open`
pkit pm show-issue 318 --field criteria       # -> one acceptance-criterion per line
pkit pm show-pr 320 --field cc-type            # -> e.g. `feat(pm)`
```

Configure the review mode in `project/config.yaml`:

```yaml
review:
  mode: agent                             # agent (default) | human
  human_review:
    reviewer_role: Implementer            # role to auto-assign as reviewer (when mode=human)
  agents:
    remote_registered:                    # bot identity for the autonomous path
      - github_login: claude-bot
    local_registered:                     # local Claude Code agents the developer invokes
      - name: reviewer                    # kit-shipped default (this capability's `agents/reviewer.md`)
```

Both `remote_registered:` and `local_registered:` are optional lists, capped at one entry each at v1 (per DEC-028). Each entry contributes a path to the agent gate's OR composition.

The capability ships a default **`reviewer`** agent for the local path (per COR-026 — discipline-implying agents live in the capability that ships the discipline). It applies the conventions defined by this capability's schemas and DECs (Conventional Commits PR titles, branch/type alignment per DEC-013, classification axes complete per DEC-012, surface-change/migration discipline per COR-010, no-shared-files per COR-001) and emits the [project-management:DEC-028]-format verdict comment that `done-work`'s gate-checker consumes. Adopters who want the default register it as above; adopters with project-specific review needs author their own agent under `.claude/agents/` and register that name instead (subject to v1's singleton-per-path constraint). Note: the kit's universal `critic` agent (per COR-024) is **not** suitable for this slot — its role is adversarial review of *unbaked* proposals, not gating *shipped* PR diffs.

Mode is resolved per-PR by three layers (highest wins):

1. Project default (`review.mode:`).
2. Per-issue label (`review:human` or `review:agent`).
3. Per-invocation `review-work --require-human` flag.

`done-work`'s gate evaluates the resolved mode:
- **human mode** — three-way OR (APPROVED review / `Approved`-prefix comment from non-author / `--bypass`).
- **agent mode** — DEC-028's gate-checker: at least one configured path (remote-bot OR local-agent) has a fresh APPROVED verdict post-dating the latest commit, plus `--bypass`.

For the local-agent path, run `pkit project-management review-pr <N>` after `review-work` to invoke every registered local agent against the PR diff. Each agent posts a `Reviewer agent (local, <name>): APPROVED|CHANGES_REQUESTED` comment. Re-running re-invokes and posts a fresh verdict (post-date-latest-commit handles staleness).

### 5. (Optional) Declare lifecycle hooks

Per [project-management:DEC-024-lifecycle-hooks], adopters can declare **post-action steps** the engine fires after each pm lifecycle event — set a board field after `create-issue`, post a templated comment after `close-issue`, assign a default milestone, or run a custom script. Hooks live in `project/hooks.yaml`:

```yaml
schema_version: 1
hooks:
  after_create_issue:
    - kind: set-board-field
      field_id: PVTSSF_lAHO...
      single_select_option_id: f78a3c2e
  after_close_issue:
    - kind: post-comment
      template_path: project/hook-templates/close-thanks.md
```

**Lifecycle events at v1**: `after_create_issue`, `after_close_issue`, `after_open_pr`, `after_merge_pr`, `after_move_issue`. Each event's value is an ordered list; hooks fire serially in declared order after the primary operation succeeds.

**Hook kinds at v1**:

- **`set-board-field`** — set a Projects v2 single-select or text field on the just-created/moved item.
- **`post-comment`** — post a comment from a template file under `project/hook-templates/`. The template renders `{{ issue.number }}`, `{{ issue.title }}`, `{{ repo }}` placeholders. Idempotent — the engine writes a `<!-- pkit-hook: <stamp> -->` marker and skips when a marker comment already exists.
- **`assign-milestone`** — set the issue's milestone by title. Idempotent.
- **`custom-script`** — escape hatch. Runs an adopter-supplied script at the declared path with a fixed env-var envelope: `PKIT_HOOK_EVENT`, `PKIT_ISSUE_NUMBER` (or `PKIT_PR_NUMBER`), `PKIT_REPO`, `PKIT_HOOK_REPLAY`, `PKIT_DRY_RUN`. Idempotency is the script's responsibility — short-circuit when `PKIT_HOOK_REPLAY=true`.

**Failure semantics**: report-and-continue. A hook failure does **not** propagate to the primary script's exit code — the primary operation already succeeded on GitHub; deleting the issue because a follow-up comment failed produces worse partial states. Hook failures are reported to stderr with `[failed] #<index> <kind>: <error>` lines; the script exits 0.

**Distinction from GitHub Actions**: hooks fire **synchronously** within the CLI invocation, atomic with the primary command. GitHub Actions react asynchronously to GitHub-side events. Use a hook for "after I file this, the board's Workstream field should be set"; use an Action for "every external-contributor PR gets labeled."

The file is optional — absence means zero declared hooks. The schema for each kind lives at `.pkit/capabilities/project-management/schemas/hook-kinds/<kind>.schema.json`; pre-check validates the file's shape and per-kind required fields.

### 6. (Optional) Enable project-manager as the default Claude Code agent

Per [project-management:DEC-030-capability-contributed-adapter-overlays], this capability ships an opt-in **adapter overlay** that makes the `project-manager` agent the default for `claude` sessions in the adopter project. Off by default — installation alone has no effect on `.claude/settings.json`. Adopters who want PM-as-default flip it on:

```
pkit project-management enable-default-agent
```

This copies the capability's overlay template (`adapters/claude-code/overlay.template.json`) to the adopter-owned activation file (`project/adapter-overlays/claude-code.json`), then re-runs the claude-code adapter's `merge-settings.sh`. The resulting `.claude/settings.json` includes `"agent": "project-manager"`; running plain `claude` from that point boots as `project-manager`.

Reverse with:

```
pkit project-management disable-default-agent
```

Disable strips the `agent` key from `.claude/settings.json`, removes the live overlay file, and re-runs the merge. Both subcommands are idempotent.

Preconditions: the claude-code adapter must be installed in the project (`enable` refuses with a clear message if not). The overlay does not interact with permissions or skill grants — it only sets the top-level `agent` key.

Rationale for the opt-in default: PM-as-default is a substantial behavioural shift (every `claude` session starts as the project-manager agent, not the general-purpose assistant). Adopters should opt in deliberately once they've decided the trade-off works for their workflow.

## Permissions

The project-management capability ships a **capability-contributed permission grant** (per ADR-016) at `.pkit/capabilities/project-management/permissions/grants.yaml`. This fragment is automatically composed into the effective permission model whenever this capability is a registered component — no manual copy required.

### What it enforces

```yaml
- subject: agent:project-manager
  privilege: '[privilege-catalog:issue-tracker-write]'
  effect: deny
- subject: agent:project-manager
  privilege: '[privilege-catalog:issue-tracker-read-raw]'
  effect: deny
```

The **first** deny blocks the `project-manager` agent from invoking the mutating `gh` subcommands directly — `gh issue create|edit|comment|close|reopen` and `gh pr create|edit|merge|close|reopen`. The agent reaches the issue tracker exclusively through the capability's validated scripts (`create-issue.py`, `close-issue.py`, `merge-pr.py`, etc.), which enforce the methodology's preconditions and gates (validation, the checkbox close-gate, the approval gate). Note this is a **speed-bump, not a security boundary** — per ADR-004 a tool-call denylist is porous (a `bash -c '…'` wrapper or `gh api -X PATCH … state=closed` evades it); the genuine gate enforcement lives inside the scripts, so the deny only removes the reflexive direct-typed bypass.

The **second** deny (`issue-tracker-read-raw`) is a **read-redirect**: it blocks the three raw read views the clean-output verbs replace — `gh issue view`, `gh pr view`, `gh pr diff` — and routes the agent to `pkit project-management show-issue` / `show-pr` (and their `--field <name>` for a single value, [described above](#read-only-diagnostics--show-issue--show-pr)). Those verbs emit clean output an agent can capture as a *bare* command instead of piping a full `gh` view through `grep`/`tail`. The recognizer is deliberately narrow — **only** those three views; `gh pr checks`, `gh run`, `gh api`, `gh issue list`, and `gh pr list` stay available, as do `git` and `pkit`. Like the mutation deny it is a speed-bump (a deny is auto-rejected by the harness with no operator prompt, so the agent simply adapts to the clean verb).

### Adopter inheritance — how you get the deny

Unlike a hand-authored grant in your project's `grants.yaml`, this deny is **capability-owned** and ships automatically:

1. `pkit capabilities install project-management` registers the capability in `.pkit/manifest.yaml`.
2. The permission model loader (`load_model` in `.pkit/permissions/decide.py`) discovers the manifest-registered capability and loads its fragment — install-state-as-gate.
3. A one-time `pkit permissions setup autonomy` activates the enforcement hook and profiles; the capability's deny is already in the model before that step.

On upgrade: `pkit upgrade` (or `pkit capabilities upgrade project-management`) propagates any changes to the fragment; the model loader picks them up on the next invocation. No manual grant is ever needed.

### Deny-wins under any profile

The `autonomous` profile grants `issue-tracker` to all agents (broad `gh` reads and writes). The capability deny on `issue-tracker-write` still holds because `decide()` is **deny-wins and order-independent**: a capability deny wins over a profile allow regardless of layer ordering. Run `pkit permissions probe --agent project-manager` to verify the deny is active.

### Visibility

Run `pkit permissions overview` to see the capability-contributed deny listed under "CAPABILITY-CONTRIBUTED DENIES" with its source (`contributed by capability: project-management`). Run `pkit permissions explain project-manager` to see the per-agent view with the same attribution.

To deliberately override the deny (not recommended — it removes the methodology enforcement gate): `pkit permissions grant agent:project-manager issue-tracker-write` in your project's `grants.yaml`. The override is auditable and explicit; it does not touch the capability's fragment.

## Upgrading

When `pkit capabilities upgrade project-management` lands a new version that ships a migration manifest under `migrations/`, the adopter's GitHub state may need reconciliation. The upgrade itself is **not** auto-chained with migration — explicit invocation, so the adopter reads the migration plan before authorising:

```
pkit project-management migrate
```

The migrate script:

- Refuses to run if pre-check fails (drift in basic state breaks migration plan computation).
- Reads pending migration manifests (versions present in `migrations/` but not yet in the adopter's `project/migrations-applied.yaml`).
- Presents the change plan and prompts for **per-change confirmation** — no batch `--yes` flag by default.
- Executes confirmed changes via `gh` mutations.
- Records the applied migration in the adopter's state file (idempotent: re-runs are no-ops).

The discipline that pins this lifecycle — including the same-PR-as-surface-change rule for migration manifests — is [project-management:DEC-017-prerequisites-bootstrap-migrate-discipline].

## Roadmap

The capability evolves on a versioned rollout pinned by [project-management:DEC-020-methodology-as-executable-commands]. Each version is a coherent unit of behaviour change rather than a single big switch:

| Version | What ships |
|---|---|
| **v0.3.0** | DEC-020 — methodology rules move from skill prose into deterministic **verb-subject scripts** under `scripts/` (`create-issue.py`, `validate-issue.py`, …); the `pm` composite skill's sub-procedures thin to intent-to-command routers. Plus DEC-021 — team membership gate; `add-member.py` / `remove-member.py` / `show-members.py` |
| **v0.4.0** | Remaining issue + PR commands; `show-tree.py` diagnostic |
| **v0.5.0** | Workstream lifecycle (per [project-management:DEC-018-workstream-taxonomy-and-lifecycle]) — `add` / `rename` / `edit` / `merge` / `split` / `remove` / `show` / `list` workstream scripts; `workstreams.yaml` becomes the source of truth; `schemas/workstreams.schema.json` ships |
| **v0.6.0** | Mandatory-issue-state enforcement (per [project-management:DEC-019-mandatory-issue-state]) — `schemas/mandatory-issue-state.yaml`; `create-issue.py` auto-adds to the configured board; default-to-filer assignment; `assign-issue.py` reassignment script; `validate-issue.py` checks; `templates/.github/workflows/pm-issue-check.yml` post-check workflow template |
| **v0.7.0+** | Methodology-mesh (per [project-management:DEC-022-methodology-mesh]) — cross-repo state coordination via per-repo `mesh_peers:` (with optional `mesh_source:` governance-repo pointer); `check-mesh.py` diagnostic; `templates/.github/workflows/pm-mesh-check.yml` scheduled workflow; drift surfaces as warnings, not enforced |

At v1 (v0.3.0+), invocation is **direct-path** — `.pkit/capabilities/project-management/scripts/<verb>-<subject>.py`. When the kit's capability-command CLI dispatch lands (kit issue [#112](https://github.com/aleskalfas/project-kit/issues/112)), the same scripts surface via `pkit pm <verb> <subject>` with no script changes.

## Authority — membership lifecycle (v0.3.0+)

Once v0.3.0 lands, every mutating verb-subject script checks a project-side **`members.yaml`** before proceeding, per [project-management:DEC-021-team-membership-gate]. Two modes:

- **Open mode** — `members.yaml` is absent or has an empty list. Any invoker with repo access passes the gate. This is the install default.
- **Closed mode** — `members.yaml` lists ≥1 member. Only listed members pass; non-members get a structured refusal with a remediation hint pointing at `add-member.py`.

Bootstrap is **self-add by the first member while open mode applies**. From the moment the first entry lands on main, the repo is closed; subsequent additions require an existing member's PR review.

This refines [project-management:DEC-008-pm-and-implementer-roles] — the PM / Implementer role distinction continues to apply *within* the membership; the gate is what restricts entry.

## Citing this capability's decisions

Inside this capability's own content (and from any other kit-shipped or adopter content referencing the discipline), cite decisions by their filename stem: `[project-management:DEC-001-distillation-lineage]`. The validator (`pkit refs validate`) walks capability subtrees and resolves these citations.

Schemas distilled from upstream METs carry a structured `source:` block (per the schemas-area envelope convention) naming the upstream project, commit SHA, and MET IDs they distill from. This makes the lineage machine-checkable.

## Dependencies

- **GitHub** as the work-tracker. The methodology names GitHub primitives directly (per MET-002 / DEC-002): Issues, native sub-issues, Milestones, Projects v2 boards and fields, labels, branch protection, GraphQL.
- **`gh` CLI** authenticated for the target organization, or equivalent GitHub access for whatever tooling the project-manager invokes.
- **No other capabilities required.** This capability is self-contained.

## Feedback to the spec

Operational findings — distillation gaps, schema shapes that didn't survive contact with reality, adopter friction — flow back to pm-workflow as scratchpad notes under `pm-workflow/.pkit/scratchpad/active/`. pm-workflow's existing scratchpad → decision review machinery consumes them. The channel is manual for v0.1.0; tooling lands if volume justifies it (per COR-007).
