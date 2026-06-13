---
authors:
  - Ales Kalfas <kalfas.ales@gmail.com>
started: 2026-06-01
---

# CLI design conventions

## The question

How should a `pkit` CLI command be *designed* — its grammar, naming, arguments,
safety, idempotency, errors, exit codes, output, discoverability — so every new
command is consistent and an author isn't re-deciding the shape each time?
COR-004 owns *which* commands exist and why; this note is the layer below: the
*house conventions* a command follows once it's decided to exist. Output is one
slice (the sibling `cli-output-conventions` note); this note is the whole.

## Forces

- **Consistency over cleverness.** A user who learns one `pkit` command should
  predict the next. Same verb vocabulary, same flag names, same safety gestures.
- **Least-surprise + least-harm.** Mutating/destructive commands must be
  predictable and recoverable; read-only must be obviously safe.
- **Self-sufficiency.** A command shouldn't depend on the user having run a
  separate command first (validate-before-assume; resolve your own context).
- **Thin CLI, logic in modules.** The CLI layer is a shim; behavior is testable
  without Click. (Mirrors how `permissions.py`/`cli.py` already split.)
- **Don't rot.** Conventions describe *shapes and rules*, not a command
  inventory (COR-004 owns the inventory; principles-not-inventory).

## What's known (grounded in the current CLI)

- **Grammar = noun-group + verb.** `pkit <area/noun> <verb> [args]` — groups are
  nouns/areas (`permissions`, `schemas`, `new`, `install`), verbs are actions
  (`explain`, `grant`, `validate`, `apply`). Installed capabilities surface
  their verbs lazily via the `CapabilityDispatchGroup` (COR-021).
- **Verb reuse.** The surface already reuses a small verb set: `validate`,
  `show`, `list`, `new`, `explain`, `diff`, `apply`, `enable`/`disable`. New
  commands should reach for an existing verb before inventing one.
- **The README table already encodes two per-command axes:** *writes?* and
  *idempotent?* — every command declares both. That table is the contract.
- **Established safety gestures:** block-unless-`--force` (uninstall refuses on
  references), `--dry-run` (install/uninstall/merge preview), confirm-before-
  destructive (rules/core.md #8), `--yes` to skip a confirm.
- **Error handling:** user errors raise `ClickException` (clean message, exit 1);
  domain errors (`PermissionsError`) are caught at the CLI shim and re-raised as
  `ClickException`. Messages say *what's wrong + how to fix* ("run `pkit
  permissions catalog`").
- **Context resolution:** commands resolve the target root themselves
  (`find_target_root`) and fail clearly if not in a project tree; don't infer
  state from prior runs (`pkit status` is the truth — rules/core.md #11).
- **Authoring commands pair with a skill** (COR-005); the script is the
  deterministic stamp, the skill carries the disciplines.

## Draft conventions (what to reuse)

### Grammar & naming
- `pkit <noun-group> <verb> [<positional>] [--options]`. Group = area/noun; verb
  = action. Prefer an existing verb (`list`/`show`/`validate`/`new`/`explain`/
  `diff`/`apply`/`enable`/`disable`/`grant`/`revoke`) over a synonym.
- Lowercase, single-word verbs where possible; kebab-case multi-word
  (`check-diff`). Flags are `--kebab-case`, repeatable where natural (`--scope`).
- Positional args for the *essential nouns* (subject, privilege); options for
  *modifiers* (`--deny`, `--scope`). Sensible defaults; no required option if a
  default is reasonable.
- **Verb and persisted-state vocabulary must agree (bidirectional).** The word
  the user *types* and the word the system *shows back for the same fact* should
  match. Two ways to satisfy it — rename the verb to the state, or rename the
  state to the verb; neither is privileged. Verbs that produce no state-noun
  (`grant`/`revoke` → an entry's presence/absence, `apply` → a realized file,
  `sync`/`bump`) have nothing to disagree with, so the rule is vacuous for them —
  it bites *only* where a verb and a named lifecycle state describe one fact in
  two roots. The one place that bites today: `permissions profile use` types
  "use" but the model persists `active_profile` and the output says "active".
  - *Trade to weigh, not pre-decide:* `use` is a strong activation idiom
    (`kubectl … use-context`, `nvm use`, `pyenv`, `tfenv use`) — renaming to
    `activate` optimises internal verb↔field agreement at the cost of external
    idiom agreement. Resolve it cleanly in *one* direction: either keep `use` and
    teach the link in the Legend (`use` ⇒ active), **or** rename hard to
    `activate` (pre-1.0; one command + its tests; ships a version bump — no data
    migration, since no adopter on-disk state is keyed to the verb, only to the
    profile name in `active_profile`).
    A *hidden alias* is the worst option — it keeps `use` in muscle memory while
    showing `activate`, replacing a 2-token gap with a 3-token one.
- **Provenance is a separate naming facet from lifecycle state.** Where a thing
  came from (`shipped` vs `project`) and what state it's in (`active`/inactive)
  are different questions; don't let one *word* try to answer both. (This is a
  vocabulary rule. The *rendering* fix for the `[shipped]` confusion — it lacked a
  Legend entry — lives in the sibling output note's legend discipline, not here.)

### Read-only vs mutating (declare it)
- Every command is one or the other. Read-only commands **never** mutate and are
  safe to run anytime. Mutating commands declare their *idempotency* and whether
  they're additive.
- A read-only sibling and a mutating sibling are a good pair (`explain`↔`grant`,
  `diff`↔`apply`) — and should **share the same core function** so they can't
  disagree (the same-code discipline, e.g. `project()` for diff+apply).

### Safety
- **Idempotent by default** — re-running a mutation converges (a fixed point),
  doesn't duplicate. Say so in `--help` / the README table.
- **Destructive or override ⇒ block-unless-`--force`**, with the refusal listing
  *what* it would break. Confirm interactively for irreversible ops; `--yes` to
  skip in automation.
- **`--dry-run`** for any non-trivial mutation: print the plan, change nothing.
- Never silently widen trust or delete adopter content; additive is the safe
  default, wholesale ownership is opt-in (cf. ADR-002).

### Errors & exit codes
- `0` success; non-zero failure. Reserve distinct codes only when a caller
  branches on them (e.g. membership-refusal vs usage error, as the capability
  scripts do) — otherwise `ClickException` (exit 1) with a clear message.
- Error messages: *what failed* + *how to fix* + the command that helps. No
  stack traces for user errors.

### Output (→ see `cli-output-conventions`)
- Human-readable, scannable default: title + (status banner) + sectioned body +
  Legend + Commands footer; computed-width columns; one line per idea. The
  detailed spec is the sibling note.
- Deterministic ordering (sort), so output is diffable and testable.

### Tables
- **Primary identifier is the leftmost column;** lifecycle state and metadata
  follow it (`NAME` then `STATE` then `SOURCE` then `DESCRIPTION`). Matches
  `kubectl get` (NAME first) and `gh issue list` (number/title first).
- **One deterministic default order** — ascending by the primary identifier.
  Stable, no flag required to get a sensible result.
- **Render a metadata column only when it carries information.** A column whose
  value is constant across every row is noise — suppress it. Worked example:
  `profile list` hides the SOURCE column when every profile is `shipped`, and
  surfaces it only once a project defines or overrides one (then `shipped` vs
  `project` actually distinguishes rows). The facet still exists; it's shown when
  it discriminates.
- **A list command follows the same skeleton as the other views** — title +
  rows + a self-status line + `Legend` + `Commands` (the output note's spec), not
  an ad-hoc `key: value` trailer. The self-status is a full sentence, not a bare
  token dump.
- **Header banner vs footer summary — by what the line *is*.** A *framing
  precondition* the reader needs before the rows make sense (is enforcement even
  on? — `overview`/`explain`) leads as a header banner. A *summary of the listed
  set* (which item is active) reads as a footer after the rows — the rows are the
  primary content; the active-state is a conclusion about them. Don't put a
  conclusion-about-the-set above the set.
- **No speculative `--sort`/`--filter` flags.** Small tables (3 profiles, a
  handful of privileges) don't need them, and adding them ahead of a consumer
  contradicts the build-with-the-consumer discipline (the same reasoning that
  deferred the managed-apply / import / capability-privilege tails). The escape
  hatch for power use is structured output (`--json` ↓) piped to `jq`/`sort`, not
  a flag matrix. Add a bespoke `--sort`/`--filter`/`--state` flag to a *specific*
  command only on demonstrated recurrence (COR-007) — the kubectl/docker heavy
  end, justified only when a table is large and queried constantly.

### Machine output (`--json`) — porcelain vs plumbing
The field converges (gh, kubectl, docker, aws) on: a sensible human default
**plus** a machine-readable mode as the universal filter/sort escape hatch.
- **Porcelain vs plumbing is per *invocation*, not per command** (git's framing).
  A command's *default* is human-readable unless it has no human audience at all
  (the `permission-hook.py` emits `permissionDecision` JSON by default — pure
  plumbing). The same porcelain command can be run headless: `diff` is read by a
  human at the prompt *and* by a CI gate — CI just passes `--json` like any other
  caller, and relies on the **exit code**, not on the default format flipping.
  **Never auto-switch format on TTY detection** — surprising a piped consumer with
  a format change is worse than requiring the flag.
- **Offer `--json` when a consumer appears, not speculatively.** Same COR-007 bar
  as the table-flags rule above — don't blanket-ship `--json` across every
  list/show/overview/explain command ahead of need. The one command with a named
  consumer today is **`diff`** (a sync-check CI gate) → ship `diff --json` + a
  meaningful exit code now; add `--json` elsewhere as real consumers show up.
  Never offer it for one-line mutation confirmations or free-form prose.
- **Data on stdout, chatter on stderr.** For `--json` to be pipeable at all, the
  machine payload goes to stdout and every human/progress line to stderr.
- **Define the `--json` failure shape, not just success.** A consumer keyed on
  exit code still needs to parse failures: on error, emit a JSON envelope
  (`{"error": "...", ...}`) to stdout with a nonzero exit — don't let success be
  JSON and failure be a bare stderr line, or the parser breaks on the path it
  cares about.
- **`--json` output is its own versioned surface (PRJ-002)** — once shipped, a
  field rename breaks consumers, so it rides the normal version policy. It is
  *not* required to mirror an on-disk YAML schema: the CLI's output contract and
  the storage schema have different consumers and change pressures (a storage
  refactor shouldn't force an output break). Define the `--json` shape
  *explicitly* and reuse schema field names only where a 1:1 record
  correspondence genuinely exists (`catalog`, `profile list`); analytical
  commands (`diff`, `overview`) define their own report shape.

### Structure & placement
- **Thin CLI shim, logic in a module.** `cli.py` resolves context, calls a
  module function, translates domain errors to `ClickException`. The module is
  unit-testable without Click. (ADR-003-style tiering for propagated logic.)
- Help strings: one line, action-first, name the sibling view. The group's
  docstring says what the noun is.

## Open questions

- ~~**Machine output (`--json`).**~~ *Resolved* — see "Machine output" above:
  offer on data/inspection commands, default only for plumbing, schema-shaped so
  it's a versioned surface. `diff --json` + exit code is the first consumer.
- ~~**Table sort/filter flags.**~~ *Resolved* — see "Tables": deterministic
  default order, no speculative flags, `--json` is the escape hatch; bespoke
  flags only on demonstrated recurrence.
- **Colour / `NO_COLOR` / non-TTY rendering.** The output note leans on aligned
  columns and glyphs; pin what happens when piped or `NO_COLOR` is set (drop
  colour, keep alignment). Adjacent to the no-TTY-format-switch rule above.
- **Pagination / large human tables.** The tables rule defers power-slicing to
  `--json | jq`, but `--json` isn't offered everywhere — so what does a large
  *human* table do (page? truncate with a count? nothing)? Open.
- **Where the provenance-vs-state rule lives on crystallisation.** It's split
  across this note (naming) and the output note (legend rendering) with one
  shared worked example — COR-007's recurrence test says pick one home before
  crystallising, don't duplicate.
- **Confirmation UX.** Standardize the prompt/`--yes`/`--force` trichotomy: when
  is each required? (force = override a safety refusal; yes = skip a routine
  confirm; dry-run = preview.) Pin the semantics so they're not conflated.
- **Quiet/verbose.** A `-q`/`-v` convention, or per-command? Probably defer.
- **Global flags.** `--help`/`--version` exist; any others worth standardizing
  (`--project-root` override for tests)?
- **Where does the crystallised convention live?** Lean: a "Command design
  conventions" section in `.pkit/cli/README.md` (author guidance), with COR-004
  remaining the *surface/inventory* owner. A PRJ record only if it must bind.

## Retires into

A "Command design conventions" section of `.pkit/cli/README.md` (sibling to
COR-004's surface spec), absorbing `cli-output-conventions` as its Output
subsection — once validated against the next new command. A PRJ record if it
should be a binding project rule. Until then this note is the reference.

## Related

- COR-004 (CLI command surface — *which* commands + why), COR-005 (skill/command
  pairing), COR-021 (capability command dispatch), COR-007 (the recurrence that
  justifies this note), COR-012 (this area).
- `.pkit/scratchpad/active/2026-05-31-cli-output-conventions.md` — the output
  slice; folds in here on crystallisation.
- `.pkit/cli/README.md` — the crystallisation home; rules/core.md #8/#11 (safety
  + validate-before-assume).
