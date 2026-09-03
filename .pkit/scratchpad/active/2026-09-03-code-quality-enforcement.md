---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-03
---

# Code quality enforcement

## The question

**How should this project raise and hold code quality across its script families — by declaring conventions, by mechanical enforcement, or both?** And relatedly: should the `software-engineering` capability ship conventions content, when today it deliberately ships none?

Parked rather than answered. Doing it properly needs work on the capability itself, which is more than the immediate cleanup (#807) warrants. This note holds what the debate established so it need not be re-derived.

## What prompted it

#807 measured the project-management script family: **47 helper names duplicated across scripts, 211 duplicated definitions, 43 of 47 divergent**. #793 was one instance — a structural-type resolver existing nine times across seven divergent bodies, so the same issue title resolved differently depending on which command you asked.

## Measurements, and how to reproduce them

65 scripts / 28.6k lines in `scripts/`, plus 38 modules / 12.3k lines in `scripts/_lib/`.

| Dimension | Finding | Verdict |
|---|---|---|
| Reusability | 47 duplicated helper names, 211 definitions, 43 divergent. `gh_get_issue`: 15 local copies in 13 flavours **while `_lib/gh.py` exports a shared one that 49 scripts import**. `_read_yaml`: 28 identical copies, no shared version. | worst |
| Modules | 605 functions in `scripts/`; `create-issue.main` ~682 lines, `validate-issue._validate_issue` 478, four more `main`s over 290; 14% of functions exceed 60 lines | poor — logic lives in `main`, so it cannot be reused, so the next script copies fragments out of it |
| Encapsulation | **157 distinct private (`_name`) functions called from tests** via module handles | leaky — the module boundary is fiction |
| Interfaces | 49 scripts reach GitHub via `_lib.gh`; only 4 shell out raw | good |
| Architecture | 38 `_lib` modules, 18 import siblings, `gh` fan-in 11, no cycles back into `scripts/` | sound |
| Abstraction | the five documented single-implementation seams (`checkbox_gate`, `audit`, `containment`, `pr_validation`, `structural_type`) all held | good where decided |

Method (re-runnable): parse `scripts/*.py` with `ast`, group top-level `def`s by name, hash normalised bodies, exclude each script's own `main`. Function lengths from `end_lineno - lineno`. Test-boundary count from regex over `tests/test_pm_*.py` for `\b\w{2,3}\._(\w+)\(`.

## The proposal that was rejected

Ship conventions as **templates** seeded into adopter-owned space, mirroring `enable-default-agent`'s kit-template → adopter-live-file copy: a universal tier (DRY, single responsibility, encapsulation), per-use-case tiers (single-file scripts vs installed package), and the adopter's own tier, with `<project-conventions>` resolving to all three.

It failed on the following, all verifiable:

**Its motivation was false.** The argument was that a kit-shipped corpus would be uneditable and therefore useless. But `project-conventions` is a patterns-only *optional read*, so pointing it at kit-owned content is mechanically legal — and this repo already does exactly that one line away: `architecture-docs: [CONTRIBUTING.md, .pkit/decisions/core/]`. The `architect` agent reads uneditable, sync-managed core records every session. For a *universal* tier, uneditable is the **feature**: sync keeps it current forever.

**The cited precedent argues the other way.** DEC-030 explicitly rejected hand-editable live files: *"Rejected because it conflicts with 'enable always overwrites' — and weakening enable's semantics to 'copy iff absent' would create the template-drift problem."* The proposal imported the mechanism while deleting the invariant that makes it safe.

**No delivery path exists for an editable-and-updatable file.** Seed-once (`treecopy.refresh_owned_tree`) never overwrites, so a kit improvement never reaches the adopter — the same defect as the capability `project/`-tree leak. Always-overwrite destroys the adopter's edits. There is no third path in the tree; the machinery for one (divergence detection / three-way merge / marker regions) does not exist and DEC-030 already deferred it.

**"No amendment needed" was false.** Three accepted artifacts state the capability ships no conventions *content*, independent of copy mechanism: ADR-013 D5 (*"Conventions content is out of scope"*), DEC-001's deferred item, and the capability README (*"It deliberately ships no conventions content"*). Templates are content.

**A parallel mechanism already works.** `.pkit/rules/core.md` (kit-owned, universal, synced) + `.pkit/rules/project.md` (adopter-owned) is a shipped, drift-free, two-tier universal-plus-project split. The proposal reinvented it with a copy step.

**And an existing contradiction was about to be layered on.** `software-engineer.md` already encodes a DRY floor in its body ("prefer naming a value used more than once, extracting a function written more than once"), which contradicts DEC-001 D3's *"structural opinions live only in the corpus, never in the agent body"* — and contaminates the with/without-corpus comparison DEC-001's rationale rests on. The proposed universal tier would have been tier 3 of 4, stacked on a tier already in breach.

## The finding that reorders everything

**The deficiency is declared-and-ungated, not undeclared.**

`pyproject.toml` selects real rule families (E, F, I, UP, B, SIM, RUF) and configures pyright. `scripts/check.sh` says plainly: *"ruff + pyright are configured in pyproject.toml but the tree does not yet pass them (hundreds of findings); adopting them is a separate cleanup and they are deliberately NOT gated here yet."* And lint scope is `src = ["src", "tests"]` — **the 65 capability scripts are not even included**.

So somebody decided, wrote it in a machine-readable place, switched the gate off, and excluded the offending tree. A prose corpus read by an agent would add a *second* unenforced layer on top of a first one already sitting there unenforced.

**The causal claim behind the whole proposal was wrong.** Would a rule saying "don't duplicate; put shared code in `_lib/`" have prevented the 15 `gh_get_issue` copies? The shared one already exists and 49 scripts already import it. Every author who wrote a local copy did so in a file that could have imported it. They did not fail to know the principle — they failed to **find the symbol**, and nothing told them. That is discoverability plus an import-graph check, not prose. `43 of 47 divergent` says the same: divergence means people re-derived rather than reused.

Nor does extracting a 682-line `main` need a corpus. Nobody is confused about whether that is too long; the rule families that flag its consequences are already selected, and the gate is off.

## Recommended order

1. **Turn on what is already declared.** Add `.pkit` to lint scope, gate ruff in `check.sh`, and add a duplicate-symbol guard: a name defined in more than one `scripts/*.py`, or defined locally when `_lib/` already exports it, is an error. Deterministic, catches all 47 names, and permanent. COR-007's recurrence test is met many times over; COR-006's discriminator points at a script plus a CI gate, not prose.
2. **Collapse the 15 `gh_get_issue` copies** onto the export that already exists.
3. **Fix the test boundary.** 157 private functions reached from tests means every extraction is also a test rewrite. Until that changes, a corpus rule about respecting module boundaries is *unexecutable at acceptable cost* — and shipping a rule the codebase structurally cannot follow trains everyone to ignore the corpus.
4. **Then** write conventions, for what is genuinely judgmental after mechanical enforcement has taken its share.

**Steps 1–3 need no decision records.** That is the finding that makes the work cheap, and it is why step 4 is far smaller than the debate assumed.

## If step 4 is ever picked up

- **Read directly, do not copy.** Ship `conventions/universal.md` in the capability and have the adopter list it in their overlay ahead of their own file. Uninstall removes the kit file (it was never adopter data); the adopter's own entry survives, which is all ADR-013 actually requires. Zero seeding, zero drift, zero new mechanism.
- **Or ship the harvester, not the opinions** — a skill deriving the corpus from this codebase's measured deficiencies. This is *already the documented plan*: the capability README says conventions accrete "e.g. via a generate → catch → encode loop", and DEC-001's deferred item says the same. It sidesteps the ships-no-content problem entirely, and is on-axiom for a methodology kit in a way that shipping DRY-as-prose is not.
- **Precedence is the load-bearing decision, not a detail.** With multiple tiers and no precedence rule, an agent handed a contradiction has no deterministic resolution — which recreates DEC-001's own complaint about "generic, session-to-session-inconsistent structural choices". Note that per-use-case selection *is* the aggregator ADR-013 D3/D4 deliberately deferred, naming ordering and conflict as the questions that "cannot be answered well from a single case".
- **Records required if it lands:** a companion/amending ADR in the 013 → 051 → 052 family for precedence and multi-source; a `software-engineering` DEC reversing the ships-no-content position and resolving the body-floor contradiction in the same record (either admit a floor tier or strip it from the agent body). No COR. No PRJ unless project-kit adopts a corpus for itself, which is a much cheaper separate act.
- **Beware a circular experiment.** Deriving conventions from a corpus's measured deficiencies and then measuring that same corpus proves only that you fixed what you looked at. If the empirical claim justifies shipping content against ADR-013 D5, the experiment must be able to fail — which needs a held-out corpus and an uncontaminated control.

## The cheapest baseline, for honest comparison

The observed *symptom* was eight review rounds reporting "no `project-conventions` category is defined". The fix for that symptom alone is one line in `.pkit/agents/project/overlay.yaml` pointing at a repo-local conventions file — no kit surface, no records. Any larger proposal should state what it buys over this.
