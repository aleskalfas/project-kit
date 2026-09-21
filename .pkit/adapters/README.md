---
variant: adapter-umbrella
---

# Adapters

Each AI harness — Claude Code, Codex, Cursor, etc. — has its own way of loading skills, agents, and configuration. The kit's own content (skills, agents, decisions, workflow) is harness-agnostic by design (per COR-006), but at some point the kit's content has to be **translated** for the harness an adopter is using: settings ported into the harness's expected file format and location, skills symlinked to the harness's expected directory, and so on.

That translation work lives here. Each harness has its own adapter directory, self-contained: `.pkit/adapters/<harness-name>/`.

## Layout

```
.pkit/adapters/
├── README.md                        # this file
└── <harness-name>/                  # one directory per supported harness
    ├── README.md                    # what this adapter handles, how to deploy it
    └── (harness-specific content)   # settings, deploy scripts, runtime artifacts
```

Per COR-005's bundle/adapter pattern: each adapter is an alternative implementation of "translate kit content for a specific harness." Adopters install the adapter that matches their AI tooling.

## Currently shipped

- **`claude-code/`** — the Claude Code adapter. Ships permissions baseline (settings/), a deploy script for skills (deploy-skills.sh), and the runtime conventions Claude Code expects.

## Harness requirements

The methodology depends on properties of the harness that hosts it — behaviour it cannot set, only require. Those requirements are declared once, as data, in `.pkit/schemas/harness-requirements.yaml` (companion `harness-requirements.schema.json`), governed by [COR-047](../decisions/core/COR-047-harness-requirement-declaration.md). Each entry states one requirement as **observable behaviour any harness could satisfy** — never as one harness's key, flag, or tool — names its **observation point** (where its truth is visible: outside a session, at the harness's own runtime hook points, or only to an agent inside a session), and cites the **evidence** that admitted it. Admission is demand-driven: an entry needs a demonstrated defect or a concrete design dependency, and a transient one names its retirement condition.

**What an adapter owes.** Each adapter answers the requirements for its own harness with a *support declaration*: a graded answer per requirement — the grading must distinguish "not achievable on this harness at all" from "achievable at a cost" — optionally bounded to a range of harness versions, and never widened automatically. The grade labels and the observation-point set are shared vocabulary owned by this area, so answers stay comparable across harnesses. An adapter that declares nothing owes nothing to exist: **silence resolves indeterminate, never satisfied**, so an incomplete declaration set never masquerades as a passing one.

**What the report says.** A verification pass resolves every requirement to `satisfied`, `unsatisfied`, or `indeterminate`, carrying the adapter's declared grade and whether the answer was `observed` or `computed`. A requirement whose observation point the pass cannot reach resolves `indeterminate` and names what could resolve it — a check that quietly passes what it did not examine is worse than no check. The layer **detects**; it does not alter the harness's configuration or duplicate a harness-owned value into methodology state. It runs on demand and at lifecycle boundaries, never on a per-operation path.

**Status.** The requirement set ships with its first entry (`delegated-result-complete`). The support-declaration shape, each adapter's answers, and the on-demand report are not yet shipped; until an adapter declares, every requirement resolves `indeterminate` for it — which is the honest state, not a defect.

## Adding a new harness

1. Create `.pkit/adapters/<new-harness-name>/`.
2. Add a `README.md` describing what the harness expects and how this adapter satisfies that.
3. Author the harness-specific content — typically some combination of settings/config files (matching the harness's format), deploy scripts (translating kit-shipped skills/agents to the harness's expected paths), and any runtime artifacts the harness needs.
4. Update this README's "Currently shipped" list.

The structural rule is light because adapters are heterogeneous by nature — Codex's settings format differs from Claude Code's; Cursor may not need a deploy script at all if it loads skills from canonical paths directly. Each adapter ships what's needed; the README of the adapter explains.
