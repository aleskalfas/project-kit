# Permissions — decision core

Propagated, harness-neutral code home for the permission **decision core** (per [COR-028](../decisions/core/COR-028-permission-model-realization.md) and [ADR-003](../../docs/architecture/decisions/ADR-003-permission-core-code-home.md)).

This is **not** a COR-011 area — it has no content layout of its own. It is a propagated code directory (synced into adopters via `PROPAGATED_AREAS`, like `adapters/`), holding the logic that both consumers import so they decide identically (ADR-002's same-code invariant):

- the `pkit permissions` CLI (`explain` / `diff`), running in the global runtime, and
- the claude-code PreToolUse hook, running in the adopter tree at decision time (where the global `pkit` is not importable).

**Dependency direction (ADR-003):** the CLI and the hook import this; this imports neither `src/project_kit` nor any adapter. Recognizers arrive as catalog *data* (`../schemas/privilege-catalog.yaml`), never as adapter code.

- `decide.py` — `decide(model, catalog, request, posture) → allow|deny|abstain` + the recognizer matcher + `hook_decide()` (fail-open) + the **single model loader** `load_catalog()` / `load_model()` (both the hook and the CLI build the model through these, so they decide identically) + `guardrail_denies()` (synthesizes the baseline `all`/`deny` grants from the privileges the catalog flags `guardrail: true` — the model half of ADR-002's double-lock). Also contains `_stdlib_load_yaml()` — a stdlib-only YAML-subset fallback invoked by `load_yaml()` when `ruamel.yaml` is not importable (e.g. inside macOS Seatbelt where `uv` panics, per ADR-014). **The fallback lives here, in the shared loader, not in the hook** — so the hook and CLI parse via the same code path (ADR-002/ADR-003 same-code invariant). Conformance fixtures live at `tests/test_permission_decide.py` (including parse-equality tests between ruamel and the stdlib fallback on all shipped files); the hook's end-to-end tests at `tests/test_permission_hook.py`.
