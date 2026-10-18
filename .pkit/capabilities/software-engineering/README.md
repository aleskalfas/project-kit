---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/**
        - .pkit/capabilities/software-engineering/review-contributions.yaml
        - .pkit/capabilities/software-engineering/decisions/**
        - .pkit/capabilities/software-engineering/scripts/**
        - .pkit/capabilities/software-engineering/schemas/**
        - .pkit/capabilities/software-engineering/skills/**
      record: [COR-013, COR-024, COR-026, COR-030, COR-050, COR-057, ADR-013, ADR-052, "project-management:DEC-015", "project-management:DEC-028", "project-management:DEC-032", "project-management:DEC-055"]
    revalidated:
      at: 2026-10-18T16:38:23Z
      outcome: unchanged
      unchanged-because: COR-050 changes what a path anchor and a registered kind's anchor stand on in a file a place holds, and the Rationale behind it. This page cites COR-050 point 3, on who writes and who checks a change's answers, which the change leaves as it was.
---

# software-engineering capability

Formalises the discipline of **authoring code under a project's own conventions** — and reviewing it. It ships a *producer* agent, `software-engineer`, that writes and edits code by reading the project's conventions corpus and conforming to it, plus a **code-review panel** of three *reviewer* agents that check code at merge time and fold through the project-management merge gate. So the code an agent produces is clean, stable, and extensible by *this* project's standards, consistently across sessions, without the conventions being re-explained each time — and code that reaches the gate is actually reviewed. Install it in any project where agents write code; skip it where they don't (it's opt-in for exactly that reason, per [COR-026](../../decisions/core/COR-026-agent-placement-by-discipline.md)).

## What this capability ships

When an adopter runs `pkit capabilities install software-engineering`:

- `agents/software-engineer.md` — the producer agent. Reads the project's conventions corpus (the overlay-resolved `<project-conventions>` category) and conforms to it; carries no coding opinions of its own; self-checks conformance and defers judgment to the reviewer stack (`critic` / `architect` / `convention-compliance-reviewer`). Its project-level definition shadows the harness's generic same-named agent.
- `agents/code-reviewer.md`, `agents/security-reviewer.md`, `agents/docs-reviewer.md` — the **code-review panel** (see below).
- `review-contributions.yaml` — registers the panel into the project-management merge gate through the reviewer-contribution socket ([project-management:DEC-032]).
- `decisions/DEC-001-producer-agent-and-conventions-seam.md` — the producer discipline's invariant: the conventions-thin producer, the overlay-resolved seam, the producer/checker boundary, empty-tolerance.
- `decisions/DEC-002-code-review-panel.md` — the panel decision: its three agents, its home, the per-agent block-threshold and knowledge-split disciplines, and `docs-reviewer`'s check of a change's answers.

It deliberately ships **no conventions content** — the conventions corpus is adopter-owned and accretes over time (see Adopter setup).

## The code-review panel

The panel ([software-engineering:DEC-002-code-review-panel]) closes bug #715: before it, the merge gate assessed conventions but nothing reviewed the code, so a PR with real security defects could pass `APPROVED`. Three reviewer agents each emit the [project-management:DEC-028] verdict grammar (`Reviewer agent (local, <name>): APPROVED | CHANGES_REQUESTED` plus the verdict marker, `<!-- pkit-verdict sha=<head> base=<base> -->` once posted, naming the head and base reviewed) so they fold through the *existing* binary all-must-approve gate — no new aggregation. Each is read-only on what it reviews — it never changes the pull request or the repository — and keeps the working files a review needs, a dumped diff or a reproduction, in the agent workspace (the agents README's "Reviewers" paragraph).

**A diff too large for `gh pr diff`.** Each reviewer reads the PR's diff with `gh pr diff`, and when GitHub refuses it (a PR changing more than 300 files) reads the same diff from the local checkout — `git diff <base>...<head>`, with the base and head its brief names, or the PR's base branch and head commit when the brief names none — requesting changes for a diff it cannot read only when neither source yields it; this paragraph owns that rule, and each panel body carries it and points here.

| Agent | Remit | Blocks (CHANGES_REQUESTED) on | Advises (APPROVED-with-comments) on |
|---|---|---|---|
| `code-reviewer` | Generalist headline: correctness/logic (core), general code quality, API-surface / interface design. The "review this PR" an operator reaches for. | Objective correctness bugs; a break to an existing caller; a violation of an explicit `<project-conventions>` rule. | Style, naming nits, subjective structure, optional refactors. |
| `security-reviewer` | Auth, **secrets-in-argv**, **`shell=True` / command injection**, crypto misuse, dependency hygiene. (The first two are #715's demonstrated harm.) | Real, exploitable vulnerabilities the change owns — the #715 classes are blocks whenever the change introduces, exposes, moves, copies or widens them, or asserts them away. | Hardening suggestions, defense-in-depth, theoretical risk with no reachable path. |
| `docs-reviewer` | Documentation completeness (new public surface documented), docs-match-behaviour, understandability, and the answers the change wrote on its documents. Leans on [project-management:DEC-015]'s doc obligations. | Missing docs for new public surface (absent a `## Doc impact` justification); a doc the diff makes contradict the code; an answer that does not hold (below). | Clarity, wording, suggested examples, thin-but-not-wrong docs. |

**The reviewer of a change's answers.** A change may carry answers on the documents its edits affect: a revalidation, which says a document was updated or still holds, and a deferral, which leaves it out of date until a follow-up. The agent making the change writes them without asking first, and a reviewer other than that agent checks them (COR-050 point 3, [project-management:DEC-055] point 3). Which reviewer is the project's choice. `docs-reviewer` checks them wherever it reviews a pull request, as its docs-match-behaviour lens applied to the change's own claims about its documents ([software-engineering:DEC-002] D1). It reads the answers from the change check's own list (`pkit friction check`, "Answers written in this change"), never from an account the author wrote. Each of these is a `[block]` finding in its verdict:

- An `unchanged` reason that does not hold against the change.
- A deferral the change writes or rewords whose reason does not hold, or that names no open follow-up issue.
- A document revalidated as `updated` with no sentence on what changed under the description's `## What changed in each updated document`, or with one that does not match the diff. `docs-reviewer` reads that section as the commands that write the list read it. An item they cannot read, such as one naming the document in bold, gives no sentence, and the finding gives the form it needs.

A deferral the change keeps as it was is not judged again. An answer on an artefact the change check asked nothing about, and a reason for having no anchors, are a person's decision (COR-050 point 3). Whether the person accepted one is not something a reviewer can read, so `docs-reviewer` names each in an `[advisory]` finding rather than blocking on it. Where such an answer is `updated`, its sentence is checked like any other.

Where `docs-reviewer` does not review a pull request, nothing checks its answers but their writer, unless another reviewer does. That is so in a project that opts out of `docs-reviewer` and chooses no other reviewer of the answers, a limit COR-050 point 3 accepts. It is also so for an unclassified docs-only pull request, which pulls in no doc reviewer (the accepted gap below): COR-050 point 3 names no such case, so give such a pull request's closing issue a `type` label when the change wrote answers. A sentence edited in the description after the verdict is not checked again, since a description edit does not make a verdict stale ([project-management:DEC-055] point 5).

**Activation** (declared in `review-contributions.yaml`, resolved by pm per [project-management:DEC-032]):

- `code-reviewer` and `security-reviewer` ride the **`touches-code` diff floor** — required whenever a PR's diff touches any non-documentation file, *independent of the closing issue's classification*. Paths the project lists as never code (pm's `review.floors.not_code`; by default the changesets under `.changes/`) do not count. This backstops #715's gate-escape: a code-carrying PR filed against a `type:docs` or unclassified issue still pulls in the correctness and security reviewers.
- `docs-reviewer` rides **both** the `touches-code` floor **and** the `type` wildcard (`type: "*"`). The floor makes doc review fire on any code-carrying diff regardless of classification — so a code PR always gets doc review even when unclassified or filed against a `type:docs` issue; the wildcard keeps it firing for a docs-only classified PR (which the floor, correctly, does not require). The wildcard is forward-safe: a new `type` value added later still activates doc review.

**Accepted gap.** An *unclassified docs-only* PR — one whose diff touches no code (so the floor does not fire) and which closes no classified issue (so the `type:*` wildcard has nothing to match) — pulls in no doc reviewer. This is a named, accepted residual: the two activation paths are the diff (floor) and the classification (match), and such a PR presents neither. A docs PR gets doc review as soon as it is classified with any `type` label, or as soon as its diff also touches code.

**A floor approval outlives a change that touches no code.** A reviewer whose every rule is the floor keeps its `APPROVED` while the commits after the head it reviewed touch no code (pm's freshness rule, [project-management:DEC-028] "Stale-verdict handling"), so a wording fix or a changeset after review re-runs neither `code-reviewer` nor `security-reviewer`. `docs-reviewer` also carries the `type: "*"` rule — the documentation is its remit — so any change re-runs it, on a typed and an unclassified PR alike. A `CHANGES_REQUESTED` from any of the three goes stale on any change, since the fix it asks for may sit outside the floor.

So `code-reviewer` alone is *basic* review; the specialists alongside it make *complex* review, composable per install ([project-management:DEC-032]). A project that wants the panel without one of its reviewers opts out of that reviewer alone in pm's `review.agents.contributed_opt_out:`, with a reason — the rest of the panel keeps gating (the project-management README, "Opting out of a contributed reviewer").

**Block-threshold discipline.** Each agent withholds `APPROVED` **only on objective failures of the change, in its remit** ([software-engineering:DEC-002] D3). Each finding begins with one of three tags that say what it does to the merge, as the verdict decision sets them out ([project-management:DEC-028-agent-as-approver-paths]). `[block]` marks an objective failure of the change in the agent's remit, and it withholds `APPROVED`. `[person]` marks a finding that cites by id an accepted rule of the `<project-conventions>` corpus, where judging the change needs a reading the rule does not settle, or a fact it does not name. It withholds no approval, and it is shown to the person who authorises the merge. `[advisory]` marks every other finding: everything softer, and every defect the change merely sits beside. It withholds nothing. A pre-existing defect blocks only when the change asserts it away — its PR title or body claims to fix or guard against the behaviour, or text the diff adds or edits says the case is handled — and the defect survives within its remit; the remedy is to fix it or retract the claim. This keeps the binary all-must-approve gate from becoming a subjective merge-blocking veto that trains the `--bypass` reflex.

**Knowledge split.** Each agent body carries only *universal* review knowledge; project-specific rules are read from the overlay-resolved `<project-conventions>` corpus — the same corpus `software-engineer` produces against ([software-engineering:DEC-002] D4). An empty or absent corpus is tolerated: the agent reviews as a careful generalist and says so.

## Adopter setup

Install:

```
pkit capabilities install software-engineering
```

After install:

- **The agents deploy and work immediately — defining conventions is optional enrichment.** The panel and the producer read the project conventions corpus through the `<project-conventions>` overlay category, but that category is an **optional read** ([ADR-052](../../../tech-docs/architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md)): with it undefined the agents still deploy and act as careful generalists. `pkit agents reconcile` surfaces `project-conventions` as an *optional* category — framed "the agent already deploys without this" — never as a blocker.
- **Define where your conventions live to enrich the agents.** Add a `project-conventions` category to `.pkit/agents/project/overlay.yaml`, pointing at the path(s) where you keep your code conventions (or uncomment the stub `reconcile` appends and fill in the paths). The resolved path is delivered into each agent's frontmatter via `<project-conventions>` placeholder resolution ([ADR-013](../../../tech-docs/architecture/decisions/ADR-013-conventions-discovery-seam.md) D1); the agents then read whatever it resolves to.
- **An empty corpus is fine to start.** With no conventions defined yet, the agents behave as careful generalists and say so. Conventions accrete over time (e.g. via a generate → catch → encode loop); the agents pick them up as the corpus fills — no re-install needed.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[software-engineering:DEC-001-producer-agent-and-conventions-seam]`. Other capabilities and adopter content use the same form.

## Dependencies

- The kit's **agents area + overlay mechanism** ([COR-013](../../decisions/core/COR-013-agent-architecture.md)) — every agent (the producer and the panel) is deployed and its `<project-conventions>` placeholder resolved by `deploy-agents.sh`.
- The **reviewer stack** ([COR-024](../../decisions/core/COR-024-critic-and-architect-agents.md)) — `critic` / `architect` / `convention-compliance-reviewer` are how the producer's work gets checked, and `rule-set-reviewer` stands in the stack too (the agents README, ["The rule-set reviewer"](../../agents/README.md#the-rule-set-reviewer)). All four ship in core; no separate install.
- **project-management** ([COR-030](../../decisions/core/COR-030-capability-dependencies.md)) — a declared `requires_capabilities` dependency. The code-review panel registers through pm's reviewer-contribution socket and folds through its merge gate ([project-management:DEC-028] / [project-management:DEC-032], including the `type` axis and the `touches-code` floor of DEC-032 D1 that the panel's activation relies on). The lifecycle gates install/upgrade/uninstall on it.
- Convention *content* is out of scope here — the corpus is adopter-owned (see DEC-001's Implications).
