# Permissions — decision core

Propagated, harness-neutral code home for the permission **decision core** (per [COR-028](../decisions/core/COR-028-permission-model-realization.md) and [ADR-003](../../docs/architecture/decisions/ADR-003-permission-core-code-home.md)).

This is **not** a COR-011 area — it has no content layout of its own. It is a propagated code directory (synced into adopters via `PROPAGATED_AREAS`, like `adapters/`), holding the logic that both consumers import so they decide identically (ADR-002's same-code invariant):

- the `pkit permissions` CLI (`explain` / `diff`), running in the global runtime, and
- the claude-code PreToolUse hook, running in the adopter tree at decision time (where the global `pkit` is not importable).

**Dependency direction (ADR-003):** the CLI and the hook import this; this imports neither `src/project_kit` nor any adapter. Recognizers arrive as catalog *data* (`../schemas/privilege-catalog.yaml`), never as adapter code.

- `decide.py` — `decide(model, catalog, request, posture) → allow|deny|abstain` + the recognizer matcher + `hook_decide()` (fail-open) + the **single model loader** `load_catalog()` / `load_model()` (both the hook and the CLI build the model through these, so they decide identically; `load_catalog()` also merges installed capabilities' privilege-catalog fragments per ADR-021 — additive-only, collision-rejecting, guardrail-forbidding) + `guardrail_denies()` (synthesizes the baseline `all`/`deny` grants from the privileges the catalog flags `guardrail: true` — the model half of ADR-002's double-lock). Also contains `_stdlib_load_yaml()` — a stdlib-only YAML-subset fallback invoked by `load_yaml()` when `ruamel.yaml` is not importable (e.g. inside macOS Seatbelt where `uv` panics, per ADR-014). **The fallback lives here, in the shared loader, not in the hook** — so the hook and CLI parse via the same code path (ADR-002/ADR-003 same-code invariant). Conformance fixtures live at `tests/test_permission_decide.py` (including parse-equality tests between ruamel and the stdlib fallback on all shipped files); the hook's end-to-end tests at `tests/test_permission_hook.py`.

- `diagnose_capture.py` — the harness-side **capture** half of the permission-prompt diagnostic loop (per [PRJ-006](../decisions/project/PRJ-006-permission-prompt-diagnostics.md)). Propagated beside `decide.py` and imported by the PreToolUse hook *after* the decision is computed. It is deliberately **separate from `decide.py`** so the decision core stays pure: `capture()` is a side-effect (a "prompt" is a harness behaviour), gated on the deferred (`abstain`) verdict, active only while a TTL-bounded session is armed, and **inert on any failure** — its own internal `try` (plus the hook's outer `try`) guarantees a capture fault can never change a decision or break fail-open. Stdlib-only, same bare-`python3` runtime constraint as `decide.py` (ADR-014). End-to-end tests at `tests/test_permission_hook.py`; unit + redaction/size-cap/inert tests at `tests/test_permission_diagnose.py`.

## The permission-prompt diagnostic loop (PRJ-006)

An opt-in, **recommend-only** loop that turns confirmation-prompt friction into a measurable, closable feedback loop. Two halves, split along the [ADR-002](../../docs/architecture/decisions/ADR-002-permission-realizer-ownership.md) same-code / harness-boundary seam:

- **Capture** (harness side, `diagnose_capture.py`, above): while *off* (the default), the hook does one cheap marker read and logs nothing; while *armed*, it appends each deferred decision to a local log. Because the hook observes only its own deferral — not whether the harness ultimately prompted — the captured signal is a **superset** of real prompts; the report states **coverage**, never a predicted prompt-count decrement.
- **Arm / disarm / classify / report** (CLI side, `src/project_kit/permissions.py`, the `diagnose_*` functions): `pkit permissions diagnose on | off | status | report`. The armed marker (`project/diagnose.yaml`) carries a **TTL** so a session auto-expires and can't stay silently on; the log (`project/diagnose-log.jsonl`) is size-capped (drop-oldest), command-tail-redacted by default, and **git-ignored** (both files, via the project `.gitignore`). The classifier groups raw command text into a taxonomy that lives **in code, not in the record** (it churns as it meets real data) and is **advisory for ranking only** — it orders + explains the report but never authorizes a change. The MVP **applies nothing**: auto-fix is deferred, and authoring a new catalog privilege is never auto-fixable.

## Scope enforcement

Grant scope globs constrain the reach of an allow grant. The dimension matched depends on the privilege's `scope_type` in `privilege-catalog.yaml`:

- **`directory` scope** (e.g. `docker`): grant scope globs are matched against the request's `cwd` via `fnmatch`. A request outside the listed paths is denied. This is enforced by the hook at decision time; it is not an OS-level confinement boundary (see ADR-004 for why shell confinement via cwd checking is not a security boundary).

- **`domain` scope** (e.g. `web-fetch`): grant scope globs are matched against the **hostname** of the request URL via `fnmatch` — **positive allow-list semantics**. The grant permits only URLs whose host matches at least one glob. A request with a non-matching host, or a request missing a parseable URL, is denied.

  Example grant (in `project/grants.yaml`):

  ```yaml
  - subject: agent:researcher
    privilege: "[privilege-catalog:web-fetch]"
    scope: ["docs.python.org", "*.github.com"]
    effect: allow
  ```

  This allows `researcher` to fetch from `docs.python.org` or any subdomain of `github.com`, and blocks all other hosts.

- **No scope** (absent): the grant is unconstrained — any cwd / any host.

## Default-agent subject resolution

The hook resolves the subject for every PreToolUse call.  Subject resolution
order (per issue #57):

1. **`agent_type` present in the payload** → `agent:<agent_type>`.  Claude Code
   sets this for spawned Task-subagents; the result is unchanged.

2. **`agent_type` absent + `.claude/settings.json` has `agent: X`** →
   `agent:X`.  The main session runs *as* that agent — all per-agent grants
   (allow and deny) apply.  `settings.json` is read with stdlib `json`; a
   missing, unreadable, or malformed file silently falls back to rule 3.

3. **`agent_type` absent + no `agent` key in `settings.json`** → `operator`.

**Implication:** in a session with a configured default agent, a human's
`!`-typed command is also bound to that agent's grants — consistent, because the
session runs *as* the agent.

Without this resolution (the pre-#57 behaviour), the main session always resolved
to `operator` even when `settings.json` set `agent: project-manager`, making
every per-agent grant inert for the primary execution context.

## Surgical deny: blocking raw gh mutations for project-manager

The `issue-tracker-write` privilege (in `privilege-catalog.yaml`) recognizes
the three raw `gh` mutations that bypass the project-management capability's
validating scripts:

- `gh issue edit`
- `gh issue comment`
- `gh pr edit`

It does **not** match `gh issue view`, `gh pr view`, `gh api`, or any other `gh`
subcommand — only mutations.

### Where the deny lives (ADR-016)

The deny is a **capability-contributed grant** shipped by the project-management
capability at `.pkit/capabilities/project-management/permissions/grants.yaml`.
It is **not** a manual grant in `project/grants.yaml` (which stays empty for this
policy). `load_model` discovers it by walking the manifest `components:` list;
a capability directory not registered in the manifest contributes nothing
(install-state-as-gate). Run `pkit permissions overview` to see it listed under
"CAPABILITY-CONTRIBUTED DENIES".

When project-manager calls `gh issue edit`, the request matches **two** privileges:

- `issue-tracker` (the broad `cmd: gh` recognizer) — **allowed** (once
  `issue-tracker` is granted to the agent via the active profile)
- `issue-tracker-write` (the mutation pattern) — **denied** by the capability fragment

`decide()` provides order-independent deny-wins semantics: it continues
iterating all effective grants after setting `matched_allow = True` for an
allow grant, and short-circuits immediately on any deny-overlap hit — so the
explicit deny wins regardless of grant ordering, even when the `autonomous`
profile grants `issue-tracker` to all.  No change to `decide.py` was required;
the existing loop already guarantees this property.

The capability scripts' internal `gh` calls are **unaffected**: they run inside
the `pkit` subprocess, below the PreToolUse hook layer — they are not Claude
Code tool calls and are therefore not subject to hook-based enforcement.

## Capability-contributed privilege *definitions* (ADR-021)

ADR-016 (above) lets a capability ship its own deny *policy*, but the privilege
the deny references still had to be *defined* in the backbone catalog. ADR-021
closes that gap: an installed capability may also ship a **privilege-catalog
fragment** at `.pkit/capabilities/<cap>/permissions/privilege-catalog.yaml`,
which `load_catalog` merges into the central catalog. A capability now ships a
privilege **definition and** its deny together, self-contained, with no
core-catalog edit (which `pkit sync` would overwrite anyway).

The fragment reuses the existing `privilege-catalog.yaml` document shape — **no
new schema**. Discovery is install-gated like the grants walk: only
manifest-registered capabilities contribute (an orphan directory contributes
nothing). The merge rule — **additive-only, collision-rejecting,
guardrail-forbidding**, with each fragment id rewritten to a capability-scoped
`<cap>:<name>` key — is ADR-021's; read it for the full semantics and the safety
rationale. In short: a fragment can extend the recognised *vocabulary* in its own
namespace but can never overwrite a backbone or peer privilege, and can never
install a deny on every adopter (a `guardrail: true` fragment entry is rejected).
A grant references a scoped privilege with the COR-019 token whose id half carries
the scope (`[privilege-catalog:<cap>:<name>]`, per COR-019's id-scope
clarification).

`pkit permissions overview` attributes each merged privilege to its contributing
capability and surfaces any rejected fragment. A fragment privilege is **inert**
until a grant references it; the narrowing is the deny grant the capability also
ships (ADR-016's channel, unchanged), and a tool-call deny is a behaviour-shaping
speed-bump, **not** a security boundary (ADR-004).

### Deny/negation scopes are intentionally unsupported

Negation globs (`!*.ru`) in a domain-scoped grant are **explicitly rejected** with an error rather than silently accepted or partially enforced. Rationale (ADR-004 §61): a tool-layer denylist is a false boundary — an agent's raw `bash curl` bypasses it at the sandbox layer, which is agent-blind. Advertising negation enforcement would overstate fidelity and violate COR-028's honesty discipline. Only positive allow-lists are supported; if you need to block a host, remove it from the allow-list rather than adding a negation glob.
