# software-engineering capability

Formalises the discipline of **authoring code under a project's own conventions** — and reviewing it. It ships a *producer* agent, `software-engineer`, that writes and edits code by reading the project's conventions corpus and conforming to it, plus a **code-review panel** of three *reviewer* agents that check code at merge time and fold through the project-management merge gate. So the code an agent produces is clean, stable, and extensible by *this* project's standards, consistently across sessions, without the conventions being re-explained each time — and code that reaches the gate is actually reviewed. Install it in any project where agents write code; skip it where they don't (it's opt-in for exactly that reason, per [COR-026](../../decisions/core/COR-026-agent-placement-by-discipline.md)).

## What this capability ships

When an adopter runs `pkit capabilities install software-engineering`:

- `agents/software-engineer.md` — the producer agent. Reads the project's conventions corpus (the overlay-resolved `<project-conventions>` category) and conforms to it; carries no coding opinions of its own; self-checks conformance and defers judgment to the reviewer stack (`critic` / `architect` / `convention-compliance-reviewer`). Its project-level definition shadows the harness's generic same-named agent.
- `agents/code-reviewer.md`, `agents/security-reviewer.md`, `agents/docs-reviewer.md` — the **code-review panel** (see below).
- `review-contributions.yaml` — registers the panel into the project-management merge gate through the reviewer-contribution socket ([project-management:DEC-032]).
- `decisions/DEC-001-producer-agent-and-conventions-seam.md` — the producer discipline's invariant: the conventions-thin producer, the overlay-resolved seam, the producer/checker boundary, empty-tolerance.
- `decisions/DEC-002-code-review-panel.md` — the panel decision: its three agents, its home, and the per-agent block-threshold and knowledge-split disciplines.

It deliberately ships **no conventions content** — the conventions corpus is adopter-owned and accretes over time (see Adopter setup).

## The code-review panel

The panel ([software-engineering:DEC-002-code-review-panel]) closes bug #715: before it, the merge gate assessed conventions but nothing reviewed the code, so a PR with real security defects could pass `APPROVED`. Three read-only reviewer agents each emit the [project-management:DEC-028] verdict grammar (`Reviewer agent (local, <name>): APPROVED | CHANGES_REQUESTED` plus the `<!-- pkit-verdict -->` marker) so they fold through the *existing* binary all-must-approve gate — no new aggregation.

| Agent | Remit | Blocks (CHANGES_REQUESTED) on | Advises (APPROVED-with-comments) on |
|---|---|---|---|
| `code-reviewer` | Generalist headline: correctness/logic (core), general code quality, API-surface / interface design. The "review this PR" an operator reaches for. | Objective correctness bugs; a break to an existing caller; a violation of an explicit `<project-conventions>` rule. | Style, naming nits, subjective structure, optional refactors. |
| `security-reviewer` | Auth, **secrets-in-argv**, **`shell=True` / command injection**, crypto misuse, dependency hygiene. (The first two are #715's demonstrated harm.) | Real, exploitable vulnerabilities — the #715 classes are blocks whenever present. | Hardening suggestions, defense-in-depth, theoretical risk with no reachable path. |
| `docs-reviewer` | Documentation completeness (new public surface documented), docs-match-behaviour, understandability. Leans on [project-management:DEC-015]'s doc obligations. | Missing docs for new public surface (absent a `## Doc impact` justification); a doc the diff makes contradict the code. | Clarity, wording, suggested examples, thin-but-not-wrong docs. |

**Activation** (declared in `review-contributions.yaml`, resolved by pm per [project-management:DEC-032]):

- `code-reviewer` and `security-reviewer` ride the **`touches-code` diff floor** — required whenever a PR's diff touches any non-documentation file, *independent of the closing issue's classification*. This backstops #715's gate-escape: a code-carrying PR filed against a `type:docs` or unclassified issue still pulls in the correctness and security reviewers.
- `docs-reviewer` rides **both** the `touches-code` floor **and** the `type` wildcard (`type: "*"`). The floor makes doc review fire on any code-carrying diff regardless of classification — so a code PR always gets doc review even when unclassified or filed against a `type:docs` issue; the wildcard keeps it firing for a docs-only classified PR (which the floor, correctly, does not require). The wildcard is forward-safe: a new `type` value added later still activates doc review.

**Accepted gap.** An *unclassified docs-only* PR — one whose diff touches no code (so the floor does not fire) and which closes no classified issue (so the `type:*` wildcard has nothing to match) — pulls in no doc reviewer. This is a named, accepted residual: the two activation paths are the diff (floor) and the classification (match), and such a PR presents neither. A docs PR gets doc review as soon as it is classified with any `type` label, or as soon as its diff also touches code.

So `code-reviewer` alone is *basic* review; the specialists alongside it make *complex* review, composable per install ([project-management:DEC-032]).

**Block-threshold discipline.** Each agent withholds `APPROVED` **only on objective failures in its remit**; everything softer is an advisory comment posted under an `APPROVED` verdict ([software-engineering:DEC-002] D3). This keeps the binary all-must-approve gate from becoming a subjective merge-blocking veto that trains the `--bypass` reflex.

**Knowledge split.** Each agent body carries only *universal* review knowledge; project-specific rules are read from the overlay-resolved `<project-conventions>` corpus — the same corpus `software-engineer` produces against ([software-engineering:DEC-002] D4). An empty or absent corpus is tolerated: the agent reviews as a careful generalist and says so.

## Adopter setup

Install:

```
pkit capabilities install software-engineering
```

After install:

- **The agents deploy and work immediately — defining conventions is optional enrichment.** The panel and the producer read the project conventions corpus through the `<project-conventions>` overlay category, but that category is an **optional read** ([ADR-052](../../../docs/architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md)): with it undefined the agents still deploy and act as careful generalists. `pkit agents reconcile` surfaces `project-conventions` as an *optional* category — framed "the agent already deploys without this" — never as a blocker.
- **Define where your conventions live to enrich the agents.** Add a `project-conventions` category to `.pkit/agents/project/overlay.yaml`, pointing at the path(s) where you keep your code conventions (or uncomment the stub `reconcile` appends and fill in the paths). The resolved path is delivered into each agent's frontmatter via `<project-conventions>` placeholder resolution ([ADR-013](../../../docs/architecture/decisions/ADR-013-conventions-discovery-seam.md) D1); the agents then read whatever it resolves to.
- **An empty corpus is fine to start.** With no conventions defined yet, the agents behave as careful generalists and say so. Conventions accrete over time (e.g. via a generate → catch → encode loop); the agents pick them up as the corpus fills — no re-install needed.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[software-engineering:DEC-001-producer-agent-and-conventions-seam]`. Other capabilities and adopter content use the same form.

## Dependencies

- The kit's **agents area + overlay mechanism** ([COR-013](../../decisions/core/COR-013-agent-architecture.md)) — every agent (the producer and the panel) is deployed and its `<project-conventions>` placeholder resolved by `deploy-agents.sh`.
- The **reviewer stack** ([COR-024](../../decisions/core/COR-024-critic-and-architect-agents.md)) — `critic` / `architect` / `convention-compliance-reviewer` are how the producer's work gets checked. They ship in core; no separate install.
- **project-management** ([COR-030](../../decisions/core/COR-030-capability-dependencies.md)) — a declared `requires_capabilities` dependency. The code-review panel registers through pm's reviewer-contribution socket and folds through its merge gate ([project-management:DEC-028] / [project-management:DEC-032], including the `type`-axis + `touches-code` floor amendment the panel's activation relies on). The lifecycle gates install/upgrade/uninstall on it.
- Convention *content* is out of scope here — the corpus is adopter-owned (see DEC-001's Implications).
