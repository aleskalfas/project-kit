---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-29
---

# Minimum install surface

## The question

**What is the bare minimum project-kit should install, and what test decides whether a thing belongs in that minimum?**

Prompted by a concrete defect (capability `project/` trees ship the source project's own state into every adopter — see the leaks inventory below), but the defect is a symptom. The question underneath: *if the core deliverable is the mechanism for propagating methodology changes across projects, how much of the methodology itself must come along?*

## What installs today

`pkit init` propagates 12 areas (`PROPAGATED_AREAS` in `src/project_kit/install.py:93`), refreshed on every `pkit sync`:

`decisions` · `skills` · `cli` · `adapters` · `scratchpad` · `agents` · `schemas` · `permissions` · `rules` · `process` · `lifecycle` · `migrations`

Roughly 107 files. **Capabilities are deliberately excluded** — bundled as a distribution medium but installed on demand (ADR-033 §3), with an in-code comment saying so explicitly.

So an opt-in tier **already exists**, and one component already sits in it. The question is whether the line is currently in the right place.

## Forces

- **Propagation needs a spine.** Some things are load-bearing for sync itself: `VERSION`, the adopter's `manifest.yaml`, `lifecycle/ownership.py` (the single "does sync manage this path?" predicate that adapters' resolvers import *in the adopter's tree*), and `migrations/` (read from the adopter tree after sync). Remove these and propagation stops working.
- **A propagation mechanism with no content is just a file-copier.** The value an adopter gets is the accumulated methodology — the core records, the operational rules, the authoring skills. A "minimum install" that lands only the spine may be technically coherent and practically useless.
- **Universal applicability (COR-014) is already the test for content**, and it is not obviously being applied to *areas*. Does every adopting project need the process substrate? The permission model? The scratchpad convention?
- **Every propagated file is a maintenance surface.** It syncs, it can drift, it can leak (as `capabilities` just did), and it must be migrated when it moves.
- **Opt-in has a cost too.** A thing nobody installs is a thing nobody benefits from; the capability tier's own rationale notes that gating a discipline behind an explicit gesture is friction on the common path.

## Candidate positions (not yet weighed)

1. **Status quo** — 12 areas mandatory, capabilities opt-in. The line is where it is because each area was added when it was needed.
2. **Thin spine** — only what propagation itself requires (`VERSION`, `lifecycle`, `migrations`, `schemas`?); everything else becomes opt-in like capabilities.
3. **Spine + methodology core** — the spine plus the things that make it *a methodology* rather than a sync tool (`decisions/core`, `rules`), with tooling (`skills`, `agents`, `process`, `permissions`) opt-in.
4. **Per-area declaration** — each area declares its own tier rather than a hardcoded list, and the test is applied per area rather than decided once.

## Open questions

- What is the **test**? Candidates: "does propagation break without it?", "does every adopting project need it?" (COR-014), "is it load-bearing for another mandatory thing?"
- Is `capabilities`-style opt-in the right *mechanism* for areas, or would areas need something different?
- What does an adopter who installs the minimum actually *do* next — and is that path documented?
- Does the answer change for a **greenfield** adopter versus a **brownfield** one?
- Is there a difference between "installed" and "propagated on sync"? A thing could be seeded once and never refreshed, or refreshed but not seeded.

## The defect that prompted this

Verified, and filed separately as its own work. A fresh adopter installing the project-management capability receives 18 files of project-kit's own state:

- `project/adapter-overlays/claude-code.json` — the default-agent switch, already flipped. The adapter activates on file *presence*, so the adopter silently gets `project-manager` as their default agent, while DEC-030 guarantees "no activation file… unchanged on install".
- `project/workstreams.yaml` — project-kit's own work areas (`capabilities`, `schemas`, `cli`, …) become the adopter's allowed taxonomy.
- `project/config.yaml` — this repo's branch, host, and doc-mapping rules pointing at paths only project-kit has.
- 14 × `project/process/issue-lifecycle/*.journal.jsonl` — this repo's audit history, keyed by issue number, so an adopter's issue #446 inherits project-kit's #446 events. These are declared `runtime_ignore` in the capability's own `package.yaml` *and* git-ignored, yet ship anyway because force-include bypasses `.gitignore` — which also makes the build non-reproducible.
- `project/bootstrap-stamp.yaml` — not in the shipped build yet, but in the source tree now. It attests setup completed in *this* repo; seeded into an adopter with no `origin` remote, the setup gate reads "already bootstrapped" and fails open.

The mechanism is one line of packaging (`pyproject.toml:77` force-includes `.pkit/capabilities` wholesale) meeting one ownership rule (`project/` is adopter-owned by tier, `ownership.py:226`). Nobody decided to ship those journals; a broad include swallowed them. `pyproject.toml`'s own comment claims the bundle "is exactly the propagation surface" — that claim is currently false.

**Why it belongs in this note rather than only in the bug:** the leak happened at exactly the boundary this question is about. The packaging rule says "ship the whole component"; the ownership rule says "part of that component is the adopter's". If the install surface were derived from a *declared* rule rather than a hand-maintained list, the two could not disagree.

---

## The motivating use case (2026-08-30)

The bare-minimum question has a concrete goal behind it, and the goal reframes it.

**The scenario.** A colleague keeps a database of rules in his own `~/.claude/` folder. He wants to package those rules and distribute them to his colleagues' laptops and projects. The imagined workflow:

1. Create a git repo for building the package (e.g. `my-pkit-rules`).
2. Install **bare-minimum pkit** there.
3. Install some pkit **"creator" feature** — unclear whether that is a capability or something more core, since it would install *areas*. To be figured out.
4. Use it to transform the rules read from `~/.claude/` into a pkit capability — possibly just copying them and wiring them to the capability interface.
5. Colleagues install that capability into their own projects.

**Two requirements fall out, and the second is the ambitious one:**

- **No mixing.** project-kit's own decisions and rules must not blend with his. His package carries his content; pkit's core content stays separate and identifiable.
- **Adapter portability is the actual value.** The point is not merely transferring files. It is that *packaging something as a capability should guarantee it works across every adapter* — Claude Code today, Codex and others later. A rule authored once should not need re-authoring per harness.

**Why this motivates the cut.** If his repo installs all twelve areas, he inherits project-kit's decision corpus, operational rules, skills, and agents — none of which he wants, all of which mix with his. A minimum install is the precondition for his repo being *his*.

### What already exists

- **Capability authoring** — `pkit new capability` plus the paired `capability-author` skill. The scaffold is real.
- **Namespacing for decisions** — a capability carries its own `decisions/` in its own DEC namespace, so his records would not mix with core's by construction. This requirement is largely already met.
- **Per-adapter subtrees in a capability** — a capability may carry `adapters/<name>/`, so the shape for "this part is harness-specific" exists.
- **Opt-in installation** — capabilities are already installed on demand rather than auto-propagated.

### What does not exist, or is unverified

- **No rules-contribution mechanism.** A capability's `package.yaml` declares `commands`, `runtime_ignore`, `requires_backbone`, `aliases` — nothing for contributing operational rules. Today `.pkit/rules/` holds exactly `core.md` (kit) and `project.md` (adopter). **There is no third slot for "rules a capability brings."** This is the single largest gap for the use case, and it is squarely in the "what should a capability be able to contribute" family that the reviewer-contribution socket already solved for one case.
- **Adapter portability is asserted, not demonstrated.** Only one adapter exists (`claude-code`). Every claim that "packaging as a capability makes it work everywhere" is currently untested — there is no second adapter to test against. The capability's own `adapters/claude-code/` subtree suggests the seam is real, but a seam with one implementation is a hypothesis.
- **The "creator" feature's tier is genuinely unclear.** If it installs areas, it is doing something core-shaped. If it only scaffolds a capability, `capability-author` already covers it. The gap may be narrower than it appears: *importing existing `~/.claude/` content* is the new part, not capability creation.

### Questions this raises for the minimum-install question

- Does "minimum" mean *the same* minimum for every adopter, or does an adopter **building** a capability need a different install than one **consuming** one? Those may be two tiers, not one.
- If a capability can carry rules, agents, skills, and schemas, then the areas holding those in core are *format definitions*, not content. Does a consuming adopter need the format definition, or only the content that conforms to it?
- Is the adapter-portability promise a property of the **capability format** (declare intent, adapters realize it) or merely of **file layout** (each capability ships per-adapter subtrees and duplicates effort)? These give very different answers about what core must ship.

---

## Mental experiment: assume `requires_areas` shipped (2026-08-30)

Walked literally, to test whether a minimum install actually unblocks the motivating use case.

**Step 1 — install bare minimum.** Works.

**Step 2 — `pkit new capability my-rules`.** The command works: `pkit` is a Python package (`src/project_kit/`), independent of `.pkit/`, so nothing in the tree needs to exist first. But the paired `capability-author` skill lives in the `skills` area he declined, so he gets the deterministic stamp **without the disciplines**. To author properly he re-installs `skills`, and likely `decisions` (for citations) and `schemas` (to validate against).

> **Finding 1: the cut barely helps a builder.** Authoring pulls most of it back. The consumer is who gets small — which supports the earlier consumer/builder tier split, and means the cut is a *consumer-side* optimisation, not a builder-side one.

**Step 3 — the scaffold** gives `capabilities/my-rules/{agents,decisions,schemas,scripts,skills,templates,adapters,…}`.

**Step 4 — where do the rules go? Nowhere.** No `rules/` slot exists in a capability. `skills/` is semantically wrong (a skill is an *invoked procedure*; a rule is an *always-loaded constraint*), and `agents/` is wrong for the same reason.

**Step 5 — and even with a home, they would not load.** `adapters/claude-code/merge-claude-md.sh` inserts exactly two hardcoded includes — `@.pkit/rules/core.md` and `@.pkit/rules/project.md`. No third slot, no discovery of capability-contributed rules. The files would sit correctly packaged in the tree and never reach the agent.

> **Finding 2: the use case is blocked on two gaps that no amount of cutting fixes.**
> (a) a capability cannot **carry** rules; (b) an adapter cannot **deliver** capability-contributed rules.

> **Finding 3 — and this is the reframe:** gap (b) *is* the portability question. Claude Code delivers rules through `CLAUDE.md` `@`-includes; another harness will do something else. If a capability **declares** "I contribute rules" and each adapter **realizes** delivery its own way, the rules genuinely work on any harness. That is the promise the use case is built on, and today nothing implements it. **Cutting the install surface delivers none of it.**

**Consequence for sequencing:** rules-contribution is the unblocking work and the thing that would *prove* the portability claim. Minimum-install is ergonomics and should follow.

## Sketch: a rules-contribution mechanism

Non-normative. The shape follows two precedents already shipped, rather than inventing one.

**Precedent A — reviewer contributions (DEC-032).** A capability declares rules in its own file; the consumer walks the manifest to collect them; *the consumer never names the contributor*; an undeployed reference stays visible as an unsatisfiable requirement rather than being silently dropped.

**Precedent B — adapter overlays (DEC-030).** A capability ships `adapters/<name>/overlay.template.json`; the adapter merges it; presence is the activation signal; the adopter's live copy is adopter-owned.

**The shape, combining both:**

- A capability may carry `rules/*.md` — mirroring the area name, consistent with how a capability already mirrors area structure (`agents/`, `decisions/`, `schemas/`…).
- **The capability declares content; the adapter decides delivery.** Claude Code adds an `@`-include; another harness does whatever it does. The capability's rules file states rules — it never mentions `CLAUDE.md`, `@`-includes, or any harness mechanism. That separation is what makes the portability claim true rather than aspirational, and it is the same produce-versus-deliver split COR-045 fixed for agents.
- Discovery is the manifest walk over installed capabilities (orphan-safe, install-driven), not a filesystem scan.

**Open design questions:**

- **Precedence and ordering.** Core rules, capability rules, project rules — in what order, and who wins a conflict? Project-last seems right (the adopter has final say), but two capabilities contributing contradictory rules has no obvious answer.
- **Numbering.** `core.md` carries numbered hard rules (1–18) that are cited by number elsewhere. Capability rules cannot renumber into that sequence without breaking citations. Namespacing (`my-rules:3`) or unnumbered prose are the candidates.
- **Opt-out.** DEC-032's own rationale names a per-contribution opt-out as its anticipated next increment; the same question arises immediately here, and rules are *higher*-stakes than reviewers — they change how the agent behaves everywhere, not just at a merge gate.
- **One file or many?** A separate `@`-include per capability is traceable (you can see whose rule it is) but grows the host file; a merged file is tidy but loses provenance.
- **Does an adopter see them before installing?** Installing a capability would silently change agent behaviour across the whole project. Given the default-agent leak documented above — where presence alone activated something an accepted decision promised would stay off — this deserves an explicit gesture rather than implicit activation.

**Relationship to the minimum-install question:** these are separable. Rules-contribution unblocks the use case; minimum-install makes the consumer's tree small. Doing rules-contribution first also produces the evidence needed to judge the cut, because it forces an answer to "what must core define for a capability's content to be usable?" — which is the same question, approached from the side where it has a concrete consumer.
