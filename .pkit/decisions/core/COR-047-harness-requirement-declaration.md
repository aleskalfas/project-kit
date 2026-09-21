---
id: COR-047
title: Harness requirements declared by the methodology, support declared by each adapter
status: accepted
date: 2026-09-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*The methodology's behaviour depends on properties of the external tool that hosts it, and those properties are not the methodology's to set. This record makes that dependency explicit: the methodology writes down what behaviour it needs, each adapter answers how far its harness provides it, and a question nobody has answered is reported as indeterminate rather than passing. The layer reports; it does not make anything conform.*

## Context

The methodology's behaviour depends on properties of the **harness** it runs under — the external tool that hosts its sessions, its agents, and their tool calls. Those properties are not the methodology's to set. A harness may lack a behaviour the methodology's design assumes; may gain it at one release and lose it at another; or may express it through configuration that several parties can set independently and whose resolved value the methodology cannot read in full.

Today such dependencies are **implicit**. They live in the reasoning behind a design rather than anywhere a reader can find them. Three consequences follow. An adopter whose own configuration removes a depended-upon property is never told. Whoever adapts the methodology to another harness has no list of what that harness must supply. And when a dependency does fail, the failure is frequently **silent** — a degraded result shaped like a correct one, so no one looks for a cause.

One domain has already solved this in miniature. [COR-028](COR-028-permission-model-realization.md) point 3 requires a permission realizer to declare which dimensions of the model its harness can natively enforce, and to **report the residual gap** rather than silently discard intent the harness cannot carry. The same shape recurs well outside permissions: support that exists only on some platforms, support that begins or ends at a particular harness release, and adopter configuration that defeats an intended posture. Per [COR-007](COR-007-pattern-extraction.md), a shape that recurs across domains earns a general carrier rather than another per-domain solution. This record's own trigger is such an instance: a harness feature which, when enabled, silently truncated the results delegated agents returned to the agent that delegated to them, leaving output that read as complete. It is the first requirement admitted under point 9.

What is missing is not enforcement machinery. It is a place to write the dependency down, an obligation on each adapter to answer it honestly, and a vocabulary in which "I cannot tell" is a reportable answer distinct from "all is well".

## Decision

**The methodology declares, in behavioural terms, the properties it requires of its harness; each adapter declares how far its harness supports them; and a requirement that is undeclared or unobservable is reported as indeterminate, never as satisfied.**

A declared property is a **harness requirement**. An adapter's answer is a **support declaration**, carrying a graded **support grade** rather than a boolean. A verification pass emits a **requirement report**.

**The report vocabulary is fixed here, because honest reporting is this record's substance.** Each requirement resolves to exactly one of **satisfied**, **unsatisfied**, or **indeterminate**. An `indeterminate` result carries its reason — no declaration exists for this harness, or the requirement's truth is not visible from where the pass ran — and never counts as satisfied. A `satisfied` or `unsatisfied` result additionally records its provenance: **observed**, or **computed** where the pass derived rather than read the answer. A report entry carries all three together — the resolved value, the adapter's declared support grade, and the provenance — so a grade of "not achievable on this harness" is never collapsed into a bare `unsatisfied`.

These are declarations of *dependency on a foreign system*, distinct from the evaluable hand-off contracts of [COR-042](COR-042-process-health.md), which govern connections between a project's own processes; the two vocabularies do not mix.

### 1. Requirements are stated as observable behaviour, never in a harness's vocabulary

A requirement names the behaviour the methodology depends on, in terms any harness could satisfy — not a configuration key, flag, tool, or setting of one particular harness. This applies [COR-014](COR-014-universal-applicability.md)'s neutrality test to a new artifact kind; the keys, files, and mechanisms belong on the adapter's side of that boundary per [COR-005](COR-005-bundle-pattern.md). What is new here is the **foreign-name risk**: a requirement staked on an external tool's own identifier silently stops meaning anything when its owner renames it, and the methodology learns nothing at the moment of change.

### 2. Each adapter declares its support, graded, and may bound it by harness version

An adapter answers each requirement for its own harness. **The answer is graded rather than boolean, and the grading must distinguish "not achievable on this harness at all" from "achievable at a cost"** — those two carry different consequences for an adopter, and collapsing them into "unsupported" destroys the distinction. The specific grade labels are *vocabulary*, owned once by the adapters layer's shared specification so that answers remain comparable across harnesses; they are not each adapter's to invent.

An answer may additionally be bounded to a range of harness versions, since a foreign tool's behaviour changes across releases. A version bound is an assertion about software the methodology does not control, so it is **never widened automatically** — only by an author who has tested the claim.

### 3. Silence is indeterminate, never satisfaction

A requirement with no declaration for the harness in use resolves to `indeterminate`. It is never treated as `satisfied`. This keeps the declaration set honestly incomplete: a newly adapted harness owes no declarations in order to exist, and the absence of an answer can never masquerade as a passing one.

### 4. Every requirement names its observation point; what cannot be observed is reported, not passed

Requirements differ in *where* their truth is visible — some from outside a session, from configuration or environment or version; some only from within a running session, to something holding the harness's own view of its capabilities. A requirement therefore declares its observation point, and a verification pass that cannot reach that point resolves the requirement `indeterminate`, naming what could resolve it. A pass that silently reports success for what it did not examine is worse than no pass at all, because it converts a gap in knowledge into a false assurance. The set of observation points is vocabulary, owned alongside the grade labels under point 2.

### 5. Prefer the observed effect; a derived answer is marked as such or withheld

Where a harness resolves a property from several sources under its own precedence rules, verification reads the **resolved effect** the harness exposes, rather than reimplementing that precedence to predict it. A reimplemented resolution drifts the moment the harness changes its own, and then reports a confident wrong answer — the one failure mode that makes the whole layer worth less than nothing. Where no resolved value is exposed, the pass may derive one only from inputs it can read in full, and must mark that answer `computed`; where it cannot read every input the harness would consult, it resolves `indeterminate` under point 4.

### 6. This layer detects; it does not make the harness conform

A requirement report states what is and is not so. It does not alter the harness's configuration to satisfy a requirement, and no part of this layer claims a requirement is guaranteed. Whether a project may *mandate* a property — committing a requirement an operator's environment must satisfy — is a separate question of policy and authority, deferred to its own decision.

### 7. A value the harness owns is not duplicated into the methodology's own state

Where the harness owns and writes a value, the methodology does not author a parallel copy of it in order to assert a requirement. Two writers over one value produce a state that neither party can report correctly: the methodology reads its own copy while the harness acts on another, and the resulting disagreement is invisible to both. Reading such a value to *report* on it is always permitted; owning a second copy of it is not. How much of an adopter's harness-owned configuration the methodology may own within a given domain is that domain's question — for permissions, [COR-028](COR-028-permission-model-realization.md) point 4 answers it.

### 8. Verification runs on demand and at lifecycle boundaries, never on a per-operation path

A requirement report is produced when asked for, and surfaced where an adopter is already reading output — at lifecycle boundaries such as install and upgrade. It is not interposed on every operation. Verification placed on an operational hot path makes its own latency and failure modes the system's — the operation it was meant to protect becomes the first casualty of the diagnostic's own faults. The honest footprint is the one an adopter can run deliberately and an automated check can consume.

### 9. Admission is demand-driven, and bounded requirements name their retirement condition

A requirement is admitted only when a demonstrated defect or a concrete design dependency calls for it, and it cites that evidence. Requirements are not written speculatively, nor for harnesses that do not yet exist. A requirement that exists only because of a transient defect in a foreign tool names the condition under which it retires, so it disappears when that condition is met rather than accumulating as permanent debt.

## Rationale

**Why a sibling to COR-028 rather than widening it.** COR-028 governs a *control* relation: the model is authoritative and realized harness state is a projection of it, so a shortfall is a fidelity gap in the methodology's own model. A harness requirement is a *dependency* relation: the property belongs to foreign software the methodology cannot dictate, cannot project, and cannot make true. There is nothing for an adapter to render — its answer is an attestation about someone else's behaviour. Widening COR-028 would drag permission semantics (subjects, scopes, conflict resolution, configuration ownership) into a general principle that has no use for them, and would amend a record with live dependents. COR-028 point 3 is better read as the permission-domain instance of this record's general rule.

**Why behavioural terms (point 1).** The alternative — naming the harness's own switch — reads as more precise and is the more tempting draft. It fails twice: the neutral layer acquires one vendor's vocabulary, and the requirement stops meaning anything if that name changes, silently. Behavioural phrasing also lets a harness that achieves the same end by different means answer the requirement, which is the point of having adapters at all.

**Why graded, not boolean (point 2).** A boolean forces "not achievable here" to be recorded as failure, which is wrong: an honest "this harness cannot do it" is a complete, correct answer that tells an adopter to close the gap elsewhere. That is COR-028 point 3's reasoning, generalized. The labels are fixed centrally rather than per adapter because a report whose grades mean different things on different harnesses cannot be compared, and comparability is most of the value when another harness is adapted.

**Why silence must not read as success (point 3).** The opposite default is what makes capability matrices rot: every adapter is presumed compliant until someone proves otherwise, the incentive to declare disappears, and the report becomes decorative. Treating silence as `indeterminate` keeps the report truthful at every stage of completeness, and lets the declaration set grow demand-driven without ever lying in the interim.

**Why the observation point is part of the requirement (point 4).** Verification is not uniformly reachable. If that is not modelled, a pass must either misrepresent what it checked or refuse to model the interesting cases at all. Naming the observation point makes the limit explicit and preserves the option of a later, differently-positioned checker without redefining the requirement. The three-valued reporting this needs — with an indeterminate result carrying the failure signal rather than counting as clean — is the discipline COR-042 established for its health check, inherited here rather than reinvented.

**Why observation beats prediction (point 5).** A layer whose whole purpose is honesty must not manufacture its own most dangerous output. Predicting a foreign tool's resolution produces answers that are wrong *confidently* and *invisibly*, which is strictly worse than the silence it replaced.

**Why detection only (point 6), and why no second copy (point 7).** Conformance is a different question with a different owner: the methodology may state what it needs, but whether a project can compel an operator's environment is that project's policy, and it involves authority the methodology does not hold. Point 7 is the constraint that keeps the deferral honest — without it, the cheapest apparent route to "make it conform" is to mirror the harness's value into the methodology's own state, which produces exactly the split-ownership failure the layer exists to detect. Deferring conformance per COR-007 keeps this record shippable and leaves the harder question to a decision argued on its own merits.

**Why the footprint is on-demand (point 8).** The alternative — check at the moment of use, so a violation is caught where it matters — is genuinely attractive and genuinely wrong here: it puts a diagnostic in the path of the work, where its own faults degrade the operation it was meant to protect. A report an adopter runs deliberately, plus one surfaced where they are already reading output, carries the value without that exposure.

**Why demand-driven admission (point 9).** The predictable failure of this layer is not under-specification but rot: a matrix of speculative entries nobody maintains and nobody trusts. Requiring evidence for admission and a retirement condition for transient entries keeps the set small enough to stay true, and puts the burden of proof on the requirement rather than on the reader.

### Alternatives considered

- **Widen COR-028 point 3 to cover all harness dependencies.** Rejected — conflates a control relation with a dependency relation, imports permission semantics into a general rule, and amends a record with live dependents. A forward pointer from COR-028 carries the relationship without the cost.
- **Declare requirements using the harness's own configuration keys.** Rejected under point 1 — crosses the neutrality boundary and stakes the requirement on a name its owner may change.
- **Treat an undeclared requirement as satisfied.** Rejected under point 3 — removes every incentive to declare and makes the report decorative.
- **Let each adapter define its own grade labels.** Rejected under point 2 — destroys comparability across harnesses and leaves the undeclared-requirement rule with nothing canonical to compare against.
- **Enforce conformance: have the methodology write the harness's configuration to satisfy a requirement.** Deferred, not rejected, per COR-007 — a project that genuinely must mandate a property will need it, and it can then be designed as a policy decision with the authority question faced squarely. Point 7 fences the tempting shortcut in the meantime.
- **Ship a complete harness-capability matrix up front.** Rejected under point 9 — speculative breadth is the rot mechanism, and completeness is not required for the report to be useful once silence reads as `indeterminate`.
- **Interpose verification on every operation.** Rejected under point 8 — a diagnostic in the path of the work trades away the thing it protects.
- **Document the dependencies in prose and rely on the existing per-domain checks.** Rejected as the whole answer, though it is most of the near-term value: prose alone gives no adapter an obligation to answer, and no reader a signal when an answer is missing.

## Implications

- **An adopter sees the report, not the machinery.** An adopter whose configuration defeats a requirement is told which requirement, at what grade their harness supports it, and whether that answer was observed or computed — closing the gap Context named first: today such an adopter is never told at all.
- **The requirement set and the support declarations are structured data, not prose.** Three decision points consume them mechanically — point 3 detects a *missing* declaration, which presupposes an enumerable requirement set to compare against; point 4 requires an observation point per requirement; point 2 requires a grade and an optional version bound per answer. That is engine data, so both carry a declared shape under [COR-018](COR-018-capability-schemas.md)'s schemas mechanism, as COR-028's model and privilege catalog do. Documentation *describes* them; it does not hold them.
- **The narrative homes are the adapters layer's shared specification and each adapter's own documentation.** The adapters area's reference document (today `.pkit/adapters/README.md`) gains the cross-cutting account — what a requirement is, what an adapter owes, the shared grade and observation-point vocabulary — and its guidance for adding a harness gains the declaration step once the declaration shape exists. Each adapter's own documentation carries its harness's answers in prose alongside the declared data.
- **Adapters gain a declaration responsibility, but owe nothing to exist.** Under point 3 an adapter that declares nothing produces honest `indeterminate` results rather than false `satisfied` results, so no harness is blocked from shipping by this record.
- **Acceptance lands with a real requirement, not an empty set.** Accepting this record obliges naming at least one requirement with its evidence in the same change-set. Under point 9 plus point 3, an empty requirement set would make every report vacuously `indeterminate` and the mechanism unexercised — the failure COR-042 guarded against with its own grounding-first obligation.
- **COR-028 point 3 is reclassified as an instance.** That record's realizer-declares-and-reports rule becomes the permission-domain application of this general principle. COR-028 gains a forward pointer here; its own decision points are unchanged and it is not superseded.
- **Harness version bounds are a separate axis from the methodology's own compatibility ranges.** [COR-010](COR-010-resource-lifecycle.md)'s compatibility ranges relate the methodology's own components to each other and are resolved at upgrade; a harness bound asserts something about foreign software. The range grammar may be shared, but the two are not the same field and a harness bound is never subject to automatic widening (point 2).
- **The verification surface is its own, not one of COR-042's deferred signal families.** COR-042's health surface reads across a project's own processes; a requirement report reads a foreign system's properties. They are separate surfaces with separate subjects, and the shared three-valued reporting discipline is inheritance, not merger.
- **Conformance remains open, and so does the consequence of a negative report.** Nothing here lets a project compel a property. Equally, whether the methodology itself should refuse, degrade, or proceed when a requirement resolves `unsatisfied` is not decided here — it is deferred with conformance, since both turn on authority this record does not claim.
- **Whoever adapts another harness inherits the list.** The practical payoff is that the properties the methodology depends on become explicit and reviewable before a new harness is adapted, instead of being rediscovered as defects afterwards.
