# Contributing to project-kit

This document is for people working on **project-kit itself** — adding or amending the methodology, evolving the kit's structure, contributing code. It is not synced into adopting projects; it lives only in project-kit's own repo.

If you have a project that has *adopted* project-kit and you want to record decisions in that project, see [`.pkit/decisions/README.md`](.pkit/decisions/README.md) instead. That file is the adopter-facing spec; this one covers the kit-maintainer responsibilities the adopter README deliberately doesn't.

---

## Running checks

There is one source of truth for "what must pass before this lands": **`scripts/check.sh`** — the check aggregator. It runs the test suite, `pkit schemas validate`, and `pkit migrations check-diff`. Run it any time:

```
./scripts/check.sh
```

The same aggregator runs in two places, so the gate can't drift:

- **Pre-push hook** (`.githooks/pre-push`) — runs it before every push for fast local feedback. Opt in once per clone: `git config core.hooksPath .githooks` (bypass in a pinch with `git push --no-verify`).
- **CI** (`.github/workflows/checks.yml`) — runs the same aggregator on a clean Linux runner for every PR and push to `main`: the unbypassable backstop plus the platform / clean-install / post-merge coverage a local hook can't give. **Not active yet:** GitHub Actions is not enabled on this GHE instance (the Actions API 404s — no runners), so this workflow does not run today. It's staged and correct; it lights up automatically once a GHE site admin enables Actions + provisions runners. **Until then the pre-push hook is the only gate that actually runs** — don't assume CI is gating PRs.

Add a check by editing `scripts/check.sh` once; both the hook and CI pick it up. (`ruff` and `pyright` are configured in `pyproject.toml` but the tree doesn't yet pass them, so they're **not** gated — adopting them is a separate cleanup.)

**Optional task runner.** A [`mise.toml`](mise.toml) provides convenience aliases over the underlying `uv run ...` commands — `mise tasks` lists them, `mise run check` runs the lint/format/typecheck/test bundle. After cloning, run `mise trust` once to enable the task runner: mise gates untrusted config by design, so a fresh clone prints a "not trusted" error on every shell until you do. Not using mise? Run the `uv run ...` commands (or `./scripts/check.sh`) directly — mise is sugar, not a requirement.

**Switching the global `pkit` (dev vs pinned).** There's one `pkit` on PATH; "switching versions" means controlling what it points at. The `mise.toml` wraps the incantations so you don't have to remember them:

- `mise run pkit:dev` — point the global `pkit` at **this checkout** (editable; source edits go live via the PRJ-001 dispatcher).
- `mise run pkit:pin` — switch back to the **pinned release** (the PRJ-004 git install).
- `mise run pkit:which` — show which one is currently active.

`pkit:dev` makes *one* checkout globally active, so across multiple clones you re-run it (or just use `uv run pkit` in-tree, which always binds to the current checkout and touches no global state). Both tasks mutate `~/.local/bin/pkit` (or `$UV_TOOL_BIN_DIR`); `pkit:pin` only ever removes a *symlink*, never a real binary.

---

## How the methodology is structured

project-kit's methodology is captured in two layers.

**The math — `.pkit/decisions/README.md`.** The spec of the decision-record system: schema, statuses, namespaces, the no-shared-files invariant, what's structural and what's contractual. The spec describes the framework, not any particular decision in it. This file is synced into every adopter, including project-kit's own tree (project-kit self-hosts), so it speaks in adopter voice.

**The physics — `.pkit/decisions/core/COR-NNN-*.md`.** The kit's actual architectural decisions. Each record is a substantive choice the kit has made among viable alternatives, about how it works.

The spec lives in the README rather than as a record because a record about how records work would be self-referential. The same applies to the **no-shared-files invariant**: it is foundational, not a peer choice among alternatives — without it the system is a different system. Foundational rules belong in the README; viable choices belong in records.

---

## Adding a core record (COR)

Core records are kit-owned. They sync into every adopting project. Adding one means committing project-kit and every adopter to a methodology choice.

1. **Pick the next COR number** in `.pkit/decisions/core/`. Numbering is independent of `project/`.
2. **Create `COR-NNN-slug.md`** with the schema and four sections described in `.pkit/decisions/README.md`.
3. **Open as `proposed`** if discussion is still open; promote to `accepted` once agreed.
4. **Respect the discipline below** — both axiom and project-neutrality.

### Axiom discipline

The `core/` corpus is treated as an axiom system. A record may use only:

- terms defined in an earlier record in the same corpus, or
- generic English / filesystem / Markdown vocabulary, or
- references to external tools or specifications named explicitly (e.g. Claude Code, Yeoman).

It must not lean on tooling, commands, or conventions that the kit itself has not yet recorded a decision about. Concretely: do not use `pk sync`, `pk init`, `pk` or any other kit-internal command name inside core records until that name is decided in its own record. Use generic phrasing instead — "the kit's sync operation", "first-time install", "the kit's CLI" — or defer the discussion to a future record.

When a record needs to reach for something not yet defined, the right move is either to introduce that concept in its own earlier record or to defer the topic to a future one. Forward-pointer "see also" references are fine for navigation, but no record should *depend* on a later one.

This keeps the corpus self-supporting: any reader can start at COR-001 and follow forward without needing to know what the kit's CLI eventually looks like, what its sync mechanism is named, or what its distribution channel will be.

### Project-neutrality

A core record must be **project-neutral**: written from the perspective of any project that adopts the kit. It describes rules, contracts, and conventions that every adopter follows.

Project-kit-specific decisions — how project-kit-the-project itself is built, the fact that it self-hosts, the choice of CLI binary name `pk`, the choice of templating engine, the distribution channel — belong in `.pkit/decisions/project/` as PRJ records (project-kit's own project-side decisions), not in `core/`.

The test: would this record make sense, and feel applicable, when read in an arbitrary adopting project's repo? If yes → COR. If it leaks project-kit's internals → PRJ.

The same test applies to every artifact kind that has a core / project split, not just decision records. **Rules** in `.pkit/rules/{core,project}.md`, **skills** in `.pkit/skills/{core,project}/`, **agents** in `.pkit/agents/{core,project}/`, **hook providers** (with the `project > bundle > adapter > core` precedence in COR-013) — for all of them, an artifact ships in the core layer if and only if it would be useful to an arbitrary adopter. If it relies on a specific project's tooling, structure, or conventions, it lives in the project namespace instead. Bundle-specific content moves to that bundle's documentation; harness-specific content goes to the adapter's. When extending the methodology with a new artifact kind, apply the same question. (Codified as COR-014; see that record for the principle named explicitly.)

Adopter-relevance heuristic for the open questions:

- **Templating engine choice** — PRJ (internal; adopters get stamped files, they don't write templates).
- **Customisation tracking** — the *rule* (don't edit kit-owned files) lives in the README invariant; the *internal mechanism* is PRJ.
- **Distribution channel** — PRJ (mostly).
- **Minimal init params** — COR (adopters have to provide these).
- **Agent variance** — COR (adopters need to know how to add their own agents).
- **CLI command surface (the public interface)** — COR (adopters use it).
- **Self-hosting** — PRJ (project-kit-specific).

### Principles, not inventory

A COR captures **durable principles** — rules among viable alternatives, with the rationale that distinguishes them. It does not enumerate operational state: path mappings, command lists, file lists, the current set of bundles, the current set of artifact types.

Operational state belongs in reference docs: per-area READMEs (`.pkit/cli/README.md`, `.pkit/workflow/README.md`, …), the install/sync manifest, area-specific spec files. The COR cross-references the reference doc; the doc owns the listing.

Inventory pinned inside a COR has two costs:

- **Brittleness** — every content addition forces a COR edit. The record turns into a tracking doc rather than a decision.
- **Conflation** — the decision (the rule that governs membership) gets mixed with its application (the current members). Future readers can't tell which sentences are load-bearing rules and which are just state.

Examples in the corpus to read for shape:

- **COR-003** — captures the *principles* for assigning a mechanism + delivery to any artifact type. It does not list which paths use which mechanism. The actual path-to-mechanism map lives in each area's README plus the install/sync manifest.
- **COR-004** — captures the *design rules* for the CLI command surface (one operation per command, sync/merge stay separate, init is one-shot, etc.). It does not list the current commands. The command list lives in `.pkit/cli/README.md`.

**Pre-draft check.** Before writing a COR, list every piece of content that might land in it and tag each as either a *rule among alternatives* (decision-worthy, with rationale) or *current state* (inventory, will change as content lands). Inventory gets one cross-reference line in the COR, not enumeration. If an item sits ambiguously between the two, default to inventory unless the *why* is non-obvious and contested.

When the boundary blurs and a single area's specifics outgrow a general COR, that area earns its own focused record — not by stuffing more state into the existing one. Workflow bundles is the most likely first such split.

### Lead with meaning

A record earns its keep only if a reader can grasp what it decides. Correctness is necessary but not sufficient — a record that is accurate yet unreadable has failed, because the reader can't extract the decision without reverse-engineering it.

So every record **leads with meaning**:

- **A short, declarative title.** State the decision, not a clause-stacked description of its mechanism. "Capabilities contribute permission grants through a model-composed fragment" — not a twenty-five-word run-on naming every layer.
- **A plain-language summary first.** Open with what the record decides and why it matters, in prose a reader grasps in under a minute, *before* the rigor. The detailed decision, the layering, the citations, and the rejected alternatives come **after** the summary — not instead of it.
- **Cross-references serve the sentence.** Cite what a point actually needs — roughly one reference per point. A sentence carrying five bracketed citations buries its own meaning; the reader chases links instead of learning the substance. Reference by meaning first, then the identifier (the authoring twin of `.pkit/rules/core.md`'s reference-by-meaning rule).

This is a principle, not a style sheet: don't pad records with mandated boilerplate, and don't strip the rigor — keep the depth, but put a readable on-ramp in front of it. The failure mode it guards against is the wall-of-jargon record whose decision is unrecoverable on a first read.

---

## Adding or evolving a project record (PRJ) in project-kit

project-kit is itself an adopter of its own kit (it self-hosts), so it has its own PRJ namespace at `.pkit/decisions/project/`. Records there capture project-kit-the-project's own implementation choices: the CLI binary name, the templating engine, distribution channel, self-hosting, and so on.

The process for adding a PRJ record in project-kit's own tree is the same one described in `.pkit/decisions/README.md` for any adopter — pick the next PRJ number, create `PRJ-NNN-slug.md`, follow the schema. The axiom and project-neutrality disciplines do **not** apply to PRJ records: project-kit's project-side records can name `pk`, reference the templating engine, talk about self-hosting, and so on.

---

## Refinements and supersessions

Same as the spec in `.pkit/decisions/README.md`. The spec applies symmetrically to COR and PRJ records; the only difference is which directory they live in and who maintains them.

---

## Refining the spec itself

The spec in `.pkit/decisions/README.md` is part of the kit's payload — every adopter receives it on sync. A change to the spec (the schema, statuses, naming convention, the invariant) propagates to every adopting project. Treat changes to the spec with the same care as a COR record.

Refinements to the spec go in the README directly. They are **not** recorded as a COR record — codifying the system in a record it is supposed to define would be self-referential. The same is true for the no-shared-files invariant: it lives in the README because it is foundational. Don't write a COR record that re-states it.

If a refinement is large enough to warrant a record, that record is *about* a specific change to the README, not about the system as a whole.
