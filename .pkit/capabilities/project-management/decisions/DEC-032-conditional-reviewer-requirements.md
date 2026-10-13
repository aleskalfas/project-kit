---
id: DEC-032
title: Conditional reviewer requirements — classification-resolved, capability-contributed, AND-composed
status: accepted
date: 2026-06-21
author: Ales Kalfas
---

pm's merge gate today requires the same single reviewer for every PR. This DEC makes the *required-reviewer set* resolve **per PR from the closing issues' classification** (and the PR's diff), and lets an **installed capability contribute** a requirement — "PRs in workstream `design` additionally require the `design-reviewer`". pm collects these rules by walking manifest-registered capabilities (the same orphan-safe walker [project-management:DEC-030-capability-contributed-adapter-overlays] uses), and a matching PR must collect a fresh `APPROVED` from its baseline reviewer **and** every contributed reviewer — *all-must-approve*. This realises the N≥2 multi-local extension [project-management:DEC-028-agent-as-approver-paths] already pinned the semantics for (all-must-approve) but capped at one agent per path for want of a second specialist. The `design-reviewer` is that second specialist.

## Context

[project-management:DEC-027-review-modes] sets review modes; [project-management:DEC-028-agent-as-approver-paths] defines how an agent's verdict satisfies `done-work` in agent mode. DEC-028 ships a **static** registered-reviewer list (`review.agents.local_registered:`), **singleton at v1** — `pre-check.py` refuses more than one local agent — with **all-must-approve** semantics already specified for the multi-local case (its "Multi-local-agent composition" section) and the list shape declared forward-compatible (its Implications). It deferred the actual N>1 extension per COR-007 until a second specialist-agent use case appeared.

That case has now appeared. The `ux-ui-design` capability (incubated in an adopter's own repo, hostable per [COR-031](../../../decisions/core/COR-031-capability-origin.md)) ships a `design-reviewer`. The adopter wants design-workstream PRs gated by that reviewer **in addition to** the baseline reviewer pm already runs. Two obstacles: the required reviewer is the same for every PR (no way to scope a requirement to PRs whose classification matches), and the only place to add one is the adopter's pm config — naming a capability-specific agent there couples pm to a discipline most adopters never install, breaking universal applicability ([COR-014](../../../decisions/core/COR-014-universal-applicability.md)) and the discipline-owns-its-agent placement rule ([COR-026](../../../decisions/core/COR-026-agent-placement-by-discipline.md)).

The pieces to solve both exist: [COR-030](../../../decisions/core/COR-030-capability-dependencies.md) gives a capability a versioned dependency edge on pm, and DEC-030 gives the manifest-walked, orphan-safe pattern for a capability to contribute into a pm-owned surface without pm naming the contributor. This DEC composes them onto the review gate.

## Decision

The required-reviewer set for a PR is **resolved per PR** from classification (and the PR's diff), may be **augmented by installed capabilities**, and is **AND-composed**. Five rules.

### D1 — The required local-reviewer set resolves from the PR's closing issues

For a PR, pm resolves the **required local-reviewer set** as:

> baseline (the project's `review.agents.local_registered:`) **∪** every contributed reviewer whose *match predicate* matches the classification of **any** issue the PR closes.

The match predicate keys on classification axes ([project-management:DEC-012-classification-axes]) — `workstream` and **`type`**. `type` is safe to key on: it is `mutually_exclusive` (so the single-value-per-issue logic and the multi-value guard generalize per-axis) and `required_on_every_issue` with a methodology-fixed value set. A rule that must match *every* type uses a **wildcard / axis-present** predicate (cleaner and forward-safe versus enumerating the fixed type values — which would silently drop the rule if a seventh type were ever added).

A contributed rule may additionally carry a **diff-property floor**, a predicate kind of its own beside the classification axis: it requires its reviewer whenever the PR's **diff** matches a property, independent of the closing issue's classification. Two floor kinds exist:

- **`touches-code`**, the floor of the code-review panel ([software-engineering:DEC-002]): the diff touches code (any non-docs source change). The adopter's not-code list (`review.floors.not_code` in the pm project config, changesets under `.changes/` when unset) narrows `touches-code` and no other floor. A changed path it names satisfies no `touches-code` floor.
- **`touches-ruled-artefact`**: the change alters an artefact on which an accepted rule binds, at the base or at the head ([COR-051](../../../decisions/core/COR-051-rule-sets.md) point 7).
  - **Altered** means added, removed, or with content that differs between the base and the head. Content is the artefact's body and own fields, never the methodology's container ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 5). So a change that only writes a revalidation alters nothing.
  - **The floor counts an artefact only when the change touches its file.** So a change to the configuration alone fires nothing, even one that brings files into the declared places or takes them out. A change to the rules alone alters no artefact they govern. A changed path is a file the change adds, removes or edits, a renamed file counted under its old path and its new one.
  - **The pairing of base and head artefacts** is the backbone's, the one the change check uses. So a move the pairing follows, keeping the content, alters nothing.
  - **One answer.** The backbone's `pkit rule-sets altered` gives which artefacts a change altered, and which accepted rules bind on each at the base and at the head. pm narrows that answer to the artefacts whose file the change touches, and computes nothing else.
  - **Read only when it can matter.** An artefact lives in a Markdown file. So pm asks the backbone only when a changed path is a Markdown file. It asks only while a contribution in force names this floor, one the project has not opted out of. A change that touches no Markdown file reads no commit, and a project with no such contribution pays nothing.
  - **Which rules.** The base is where the PR left its base branch, as the change check reads it. A rule accepted on the base branch after that counts once the PR merges the base. An approval the reviewer already gave stands through that clean merge (DEC-028). A rule reached only through a pin behind its set binds nothing, so it fires nothing. Validation reports the pin meanwhile, and fails wherever the check is enforced (COR-051 point 7).

**A floor pm does not know**, such as one a later release of pm defines, requires its reviewer on every change. pm does not refuse the whole declaration for it. So a contributor's newer floor meets a pm that carries this rule with one more required reviewer, never with every pull request refused. A floor that is not a non-empty name is a malformed declaration.

**What the ruled-artefact floor reads locally.** For a change that touches a Markdown file while a contribution in force names `touches-ruled-artefact`, resolution needs:

- the PR's head and the base branch's head as commits in the local repository
- the history between them, so the backbone can find where the PR left its base
- a backbone that has the command

A commit the checkout lacks is first fetched from origin by its object name. Each of these fails the resolution, with a reason naming the cause:

- a commit the fetch does not bring
- a shallow checkout
- a command that fails, or whose answer cannot be read
- a backbone without the command, the reason naming the backbone pm needs

A diff that cannot be read fails it too, as it does for `touches-code`. None of these causes drops the reviewer. This holds for every command that resolves a PR's required set. A base whose configuration cannot be read makes the command fail for each PR that left the base there and touches a Markdown file. Such a PR lands through the audited bypass ([project-management:DEC-026-work-ownership-lifecycle]), or once it merges the repaired base.

Because a floor keys on the *diff*, it **backstops the classification gate-escape** below: classification alone resolves an unclassified sub-task, a PR with no closing issue, and (for the code panel) a `type:docs`-but-code-touching PR to *baseline only*, which — for a discipline whose mandate is code review (#715) — would let code merge unreviewed. The floor removes that escape for any floor-carrying reviewer: a diff that touches code requires the code panel regardless of how the issue is labelled.

**Resolution domain** — because a PR's relation to issues is not 1:1, the rule is total:

- **One closing issue** → match against its classification.
- **Multiple closing issues** → **union** of all matched contributions (a PR closing a `design` issue and a `backend` issue requires both reviewers). This deliberately differs from DEC-012's *dominant-kind* rule for the `type` axis: `type` resolves the squash-commit prefix (one value needed); a required-reviewer gate is safer as a union (drop nothing a contributor asked for).
- **No closing issue** (hotfix/refactor opened directly) → no classification to match → **baseline only**.
- **Closing entity carries no classification axis** (a sub-task or Milestone — per DEC-012 these carry neither `workstream` nor `type`) → matches nothing → **baseline only**. This is a real gate-escape *for classification-keyed contributions*: design work filed/closed against a sub-task escapes the `design-reviewer`. The mitigation is procedural, not enforced — file gate-bearing work against a classified Task; the DEC names the escape rather than hiding it. A **floor-carrying** contribution is exempt: its diff-property floor requires the reviewer regardless of classification, so it cannot be escaped by (mis)classification. The code panel ([software-engineering:DEC-002]) carries the `touches-code` floor; `design-reviewer` carries none — so the escape's mitigation is procedural for a purely classification-keyed contribution such as `design-reviewer`, and enforced for the code panel.

The set is de-duplicated: a reviewer named by both the baseline and a contributed rule is required once.

### D2 — Capabilities contribute reviewer requirements; pm collects them by walking the manifest

A capability declares its reviewer-contribution rules in a dedicated declaration in its own subtree (each rule pairs a classification match-predicate with a required reviewer-agent name; the declaration's filename and schema are owned by the capability-schema reference, not pinned here). pm builds the resolution map with a collector that **iterates capabilities registered in `.pkit/manifest.yaml`'s `components:` list** — not arbitrary directories — exactly as DEC-030's `collect_capability_overlays` does, so an orphaned capability directory (botched uninstall, stash, rebase) can never silently inject a merge gate.

A contributed reviewer name carries the same constraint as a DEC-028 `local_registered` entry: it must correspond to a deployed agent file (`.claude/agents/<name>.md`, or wherever the harness deploys agents). The contributing capability ships that agent (per COR-026) and declares `requires_capabilities: project-management` (per COR-030). **pm never names a contributor** — it only reads contributions from whatever capabilities are installed.

**Scope: contributed reviewers register on the local path only.** A contributed remote bot would need a GitHub identity the contributing capability cannot ship, so at v1 every contributed reviewer is a local-path agent. The *baseline* reviewer may still be remote, local, or both (DEC-028 unchanged). One consequence to name: a `workstream:design` PR whose `design-reviewer` requirement is local-only **cannot close fully autonomously** on the remote (no-developer-at-keyboard) path — its contributed verdict needs a `review-pr` invocation. A remote contributed path is a later increment if the autonomous design-PR loop is ever needed.

### D3 — The resolved set is AND-composed; the gate-checker generalises across paths; the singleton cap lifts

The gate is satisfied when **every reviewer in the resolved required set is satisfied — by a fresh `APPROVED`, or by an operator's audited `satisfied-by-override`**. This requires one real change to DEC-028's gate-checker, not "everything unchanged" — because the resolved set can span the remote/local path boundary DEC-028's composition was built around. The corrected rule:

- **Per reviewer, OR across the paths that reviewer is registered on; AND across the required set.** A reviewer registered on both paths (e.g. the baseline reviewer with a bot *and* a local agent) is satisfied by either path's fresh `APPROVED` (DEC-028's existing per-reviewer OR). Any reviewer's conjunct is also satisfied by an operator's audited `satisfied-by-override` — `done-work --bypass-reviewer <name>` — a first-class state distinct from `APPROVED` (refinement per [project-management:DEC-050-per-reviewer-override]). The gate then requires **all** reviewers in the resolved set to be individually satisfied.
- Concretely, this **replaces DEC-028's gate-checker steps 6–7** (per-path satisfaction + cross-path OR) with the per-reviewer-OR / across-set-AND rule above; **steps 1–5 (marked verdict-shape match, identity/name filter, latest-per-agent, freshness of the latest) stand unchanged.** For a project with only the static baseline and no contributions, the two formulations coincide — so existing behaviour is preserved; the generalisation only bites once the set has more than one reviewer. Because it subsumes DEC-028's step 7, DEC-028's "Gate-checker algorithm" states the generalisation of steps 6–7 and points here (see Implications), so DEC-028 does not read a superseded formulation.
- Consequently `pre-check.py` no longer refuses more than one local agent (the **singleton cap lifts**). Verdict format, freshness, latest-per-agent, and author-exclusion rules are all unchanged from DEC-028.
- **Agent mode only.** This gate is DEC-028's agent-mode gate; in `human` mode (per DEC-027) a contributed reviewer's verdict is advisory, exactly as DEC-028 makes `review-pr` verdicts advisory in human mode — a `workstream:design` PR is hard-gated by `design-reviewer` only when the resolved mode is `agent`.

### D4 — `review-pr` invokes the resolved set

`review-pr <N>` resolves the required set for the PR and invokes every required reviewer (baseline + contributed) whose latest local-path verdict the gate would not already accept — a reviewer with a verdict fresh for the PR's head is reported and not re-run unless `--force` is passed — each invoked reviewer posting its own verdict, so the developer-at-keyboard flow produces exactly the verdicts the gate needs.

### D5 — Activation is install-driven; the resolved set is recomputed at gate time

A capability's reviewer contribution is **active when the capability is manifest-registered and its reviewer agent is deployed** — installing a review-discipline capability is the opt-in (no separate enable/disable toggle; contrast DEC-030, see Rationale). The required set is **recomputed at each gate check** from the current manifest, the PR's current classification, and the PR's current diff — with, for the ruled-artefact floor, the rules at its current base and head — it is not frozen at PR-open. This makes the lifecycle dynamics total:

- **Contributing capability uninstalled mid-PR** → its rule leaves the manifest → its reviewer drops out of the resolved set → the gate reverts toward baseline. No deadlock; the discipline left with the capability that owned it (the same disposition DEC-030 gives an uninstalled contribution).
- **Capability still installed but its agent undeployed** → a resolvable rule names a missing agent file → this is a broken install, surfaced as a clear error at `review-pr`/`done-work` with remediation (redeploy the capability, or uninstall it) — the same "registered name must have a deployed file" check DEC-028 already runs, not a silent deadlock.
- **PR reclassified mid-flight** (a `workstream` label edited) → recomputation adds or drops requirements. A newly-added reviewer has no verdict, so the gate correctly refuses until it approves. A dropped requirement is no longer gating — acceptable and symmetric with uninstall. Reclassification is thus a set-membership event the recompute handles directly (DEC-028's commit-keyed freshness does not need to model it).
- **PR diff changes mid-flight** (e.g. a `type:docs` PR gains a code-touching commit) → recomputation reads the *current* diff, so a diff-property floor newly requires its reviewer (which has no verdict yet) → the gate correctly refuses until it approves. Symmetric with reclassification; the recompute handles it directly.

Zero installed contributions, or a PR matching none, leaves the gate exactly as DEC-028 left it.

## Rationale

**Why contributed-and-resolved, not a static map in pm config.** The design-review discipline belongs to the capability that ships it, not to pm (COR-026, COR-014). Hard-coding `workstream:design → design-reviewer` into pm would force every adopter's pm to carry knowledge of a capability most never install. The COR-030 edge + DEC-030 manifest-walk keep pm universal: pm offers the resolution mechanism; capabilities supply the rules; pm stays ignorant of who contributes.

**Why AND-compose (N≥2) rather than replace (N=1).** A design-workstream PR carries two distinct concerns the project wants both checked — baseline review and design review. Replace-semantics would silently drop the baseline concern on exactly the PRs a specialist is added to. All-must-approve preserves every declared concern — DEC-028's own stated rationale for all-must-approve multi-local. The maintainer chose this composition deliberately over the lighter replace variant.

**Why this lifts DEC-028's cap rather than inventing a new mechanism.** DEC-028 pinned all-must-approve for multi-local and declared its list shape forward-compatible, capping at N=1 only because no project had two reviewer agents in use. pm's baseline `pm-reviewer` plus `ux-ui-design`'s `design-reviewer` is that second instance — a grounded recurrence, not a manufactured one.

**Why install-driven activation, and the cope-path for "install but don't gate".** Gating its discipline's PRs is the central reason to install a review-discipline capability, so a mandatory enable step is friction on the common path. The inverse reading has force, though — a hard merge gate is *higher*-stakes than DEC-030's settings-key injection, which DEC-030 nonetheless gated behind opt-in — so an adopter who wants a capability's other content but not its gate is a real case. Their cope-path today is explicit and unsatisfying: uninstall the capability, or `--bypass` each gated PR. Because the stakes are higher than DEC-030's, a per-contribution **opt-out** is the most likely near-term follow-up (not a vague COR-007 deferral); this DEC ships install-driven activation as the default and names the opt-out as the anticipated next increment.

**Why the contribution surface is attestation, not security.** DEC-028 framed its allowlist as attestation, not a security control — anyone with repo write can edit `local_registered:`; real enforcement is GitHub branch protection. This DEC *widens* that surface: the gate rules now also come from installed capabilities, and `ux-ui-design` is itself adopter-authored (incubated), so whoever can land a capability install can shape the gate — e.g. ship a rule routing their own PRs to an always-approving agent, or scope themselves out. The manifest-walk and deployed-agent-file checks prevent honest mistakes (orphan dirs, typos), **not** a motivated actor with write access. The trust model and the enforcement floor are exactly DEC-028's: attestation here, branch protection underneath.

**Why the gate is honest about the honor system.** Under the local path, both the baseline reviewer and a contributed `design-reviewer` post under the developer's own identity with author-exclusion relaxed (DEC-028's local-path trust model). So on a solo workflow the AND-composed "two distinct concerns" can be two attestations by the same person running `review-pr`. That is not a defect — it is DEC-028's deliberate trust posture — but the DEC states it plainly rather than overselling the gate's strength.

**Why manifest-walked collection.** Identical reasoning to DEC-030: the manifest is the source of truth for installed-ness; walking it (not the filesystem) stops a half-removed capability directory from silently imposing a merge gate.

**Why a floor on ruled artefacts.** A reviewer of the rules that govern documents has work when a change alters an artefact an accepted rule binds on. The rules' own scopes and statuses say which artefacts those are, so the floor reads them through the backbone's one answer. Path globs in each contribution would copy each scope out of its rule set. They would be blind to a rule's status, and to a change that only writes a revalidation. A classification match would let a label escape the gate, the escape the floor closes. The cost is one backbone command per resolution of a change that touches a Markdown file, while a contribution in force names the floor.

**Why the floor counts only artefacts in the files a change touches.** The reviewer judges only what the change owns ([COR-057](../../../decisions/core/COR-057-rule-set-reviewer.md) point 2). A change to the configuration that brings a page into the declared places, or takes one out, owns no passage of it. Counting such pages would read commits for every change, Markdown or not. The cost is that such a change draws no reviewer of the rules, though the backbone lists those pages as added or removed. It is shown to the person who authorises the merge as a change to which documents are checked ([project-management:DEC-055-pr-lists-answers] point 1).

**Why the not-code list narrows `touches-code` alone.** The list says which paths are not code. A project that lists `docs/**` there means its pages draw no code review, not that its pages escape the rules that govern them.

**Why an unknown floor requires its reviewer.** Refusing the declaration would refuse every pull request until pm is upgraded, and no opt-out clears that. Requiring the reviewer costs one review on a change the floor might not have reached. It never merges unreviewed what the floor would have caught. The cost is that a misspelt floor requires its reviewer everywhere instead of failing as malformed.

### Alternatives considered

- **N=1 replace — classification resolves the single required reviewer.** Rejected by maintainer decision: design PRs want baseline-plus-specialist, not specialist-instead-of-baseline.
- **Static `workstream → reviewer` map in pm's `project/config.yaml`.** Rejected — couples pm to capability-specific disciplines, breaking universal applicability and COR-026 placement.
- **DEC-030-style enable/disable toggle for the contribution.** Rejected as the *default* — the gate is the purpose of the capability. But the opt-out it represents is the named near-term follow-up (see Rationale), not a flat refusal.
- **Dominant-workstream resolution for multi-issue PRs** (mirroring DEC-012's dominant-kind). Rejected — dominant-kind exists to pick one commit prefix; a gate must not drop a contributor's requirement because another workstream "won". Union is the safe rule.
- **Any-approves when the set is N>1.** Rejected for DEC-028's reason — a passing-but-unrelated reviewer would satisfy a gate the project wanted N specific concerns checked for.

## Implications

- **`pre-check.py`** drops the singleton-per-path refusal for `local_registered:`; it validates that every name in the *resolvable* set (baseline + every contributed rule) has a corresponding deployed agent file, and validates the shape of each capability's contribution declaration. It warns of each floor this pm does not know, since that floor requires its reviewer on every change.
- **The pm capability gains a contribution collector** that walks `.pkit/manifest.yaml`'s `components:` for review-contribution declarations and builds the predicate→reviewer resolution map — analogous to DEC-030's `collect_capability_overlays`.
- **`done-work`'s gate-checker** resolves the required local set per PR (per D1's resolution domain), then applies the D3 rule (per-reviewer OR-across-paths, AND-across-the-set). All verdict-format / freshness / author-exclusion steps are unchanged.
- **`review-pr`** resolves the required set and invokes every member without a fresh verdict (D4).
- **Surface change, but migration-free.** This is a surface change per [PRJ-002] (new contribution mechanism + a validator that now *accepts* what it used to refuse), so the implementing PR bumps the pm capability and the backbone. No migration is required: `pre-check.py` previously *refused* N>1, so no adopter holds invalid N>1 state to bridge, and a project with no contributions or a non-matching PR behaves identically to DEC-028 ([COR-010](../../../decisions/core/COR-010-resource-lifecycle.md)).
- **The `type` axis and the diff-property floor** are realized by the resolver (`required_reviewers.py`) and the `review-contributions` schema gaining `type`-axis and diff-property support; [software-engineering:DEC-002]'s code-review panel is the first consumer of both. They are a surface change per [PRJ-002] (the resolver accepts a wider predicate) → a **pm-capability** changeset; the change touches pm-owned files only and reaches adopters through the tool bundle at the backbone release that bundles it (which is what makes an updated capability installable via `pkit upgrade`). Migration-free: additive (a project with no `type`-keyed or floor-carrying contribution, or a non-matching PR, resolves exactly as before).
- **The ruled-artefact floor** is realized by the resolver and the freshness rule, each reading `pkit rule-sets altered`. The `review-contributions` schema accepts `touches-ruled-artefact`. The collector keeps a floor it does not know, and the not-code list narrows `touches-code` alone. A pm release that ships the floor requires a backbone that has the command. A project whose contributions name only `touches-code` resolves exactly as before. One that names a floor pm does not know has that reviewer required on every change, where its declaration was refused.
- **DEC-028's gate-checker points here.** Because D3 subsumes DEC-028's step 7 (cross-path OR → cross-reviewer AND), DEC-028's "Gate-checker algorithm" carries a one-line generalisation of steps 6–7 and a forward pointer to DEC-032, so the accepted record does not state a superseded formulation. The pointer is part of this decision, not a navigational nicety. This DEC stands on DEC-026, DEC-027, DEC-028, COR-030, and DEC-030 — all accepted.
- **First consumer (illustrative).** The `ux-ui-design` capability ships `agents/design-reviewer.md` and a contribution rule matching `workstream: design` to `design-reviewer`, declaring `requires_capabilities: project-management`. A design-workstream PR then requires both the baseline `pm-reviewer` and the `design-reviewer` to APPROVE before `done-work` merges.
- **Implementation, now unblocked.** With this DEC accepted, the gate-checker generalisation, the `pre-check.py` cap lift, the contribution collector, the contribution-declaration schema, and `review-pr`'s resolution are authored under the conditional-reviewer feature, not here. DEC-028's pointer at steps 6–7 lands with this record.
- **Universal-applicability flag for methodology review.** "An installed capability contributes a requirement into another capability's gate, resolved from classification" could recur (a security capability contributing a required security reviewer; a compliance capability contributing an approval). If it recurs, the contribution mechanism may promote toward a kit-level pattern per COR-007.
- **The per-contribution opt-out has shipped (#148).** The anticipated increment the Rationale names: an adopter lists `{capability, reviewer, reason}` under `review.agents.contributed_opt_out:` in their own `project/config.yaml`; the shared resolver withdraws that contribution before matching, so `review-pr` and `done-work` agree; an entry naming no installed contribution fails closed; `pre-check` lists each opt-out with its reason.
