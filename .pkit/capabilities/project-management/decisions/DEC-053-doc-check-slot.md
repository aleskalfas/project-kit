---
id: DEC-053
title: Documentation obligations for a change are collected through a slot
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

This capability already holds changes to their documentation duty ([project-management:DEC-015-doc-update-obligations]). Every Task and pull request carries a `## Doc impact` section that lists the doc updates made or justifies why there are none. Optionally, a project maps code paths to the documents that describe them, and a check warns, or refuses where the project enforces it, when mapped code changes without its document.

The mapping is a coarse guess written from the code's side, so broad rules fire on most changes. A documentation capability can do better. With pages anchored to what they describe (COR-050), it can say precisely which pages a change makes stale. It can also say which new code nothing documents, and propose the documentation statement itself. It must be able to contribute that without this capability depending on it, and without taking away this capability's own guarantees from projects that never install it.

## Decision

**What a change owes to its documentation is collected through a slot — a data point under the work-tracking role this capability provides, `<methodology>::work-tracking:doc-check` (refinement per COR-053). This capability's own checks are always one of its fillers, and a documentation capability may add to them.**

1. **The slot** (COR-052), resolved for a pull request against its diff:
   - **Its entries are documentation obligations.** Each names the document or path concerned, the reason (a mapped path changed, an anchored page went stale, new code is undocumented), and its source. Obligations from different sources are keyed so that they never collide or replace one another. A mapping obligation is keyed by its mapping rule, as today. Other obligations are keyed by document and source. The shape is a companion schema named after the point, at version 1.
   - **Policy:** `additive`. Obligations are requirements, so none may be dropped silently. A project removes one only through a removal override that records its reason, the audited escape the slots record provides. Keys include the source, so the policy's collision rule never fires between sources.
   - **Default:** always included. This capability's code-to-doc mapping is the default filler.
   - **Inert policy:** `fail`, because the slot feeds the merge gate. A documentation filler that goes out of step makes the check report "unresolved", naming the filler and the fix: update it, pin it, or uninstall it. It never reports a weaker pass.

   The requirement that every Task and pull request carries a well-formed `## Doc impact` section is not an obligation. It stays a rule of the gate itself ([project-management:DEC-015-doc-update-obligations]), whatever fills the slot.

2. **How obligations are met.**
   - **Mapping obligations are met exactly as today.** The diff touches one of the rule's documents, or the `## Doc impact` section names the changed code path or the rule's pattern. A project without a documentation capability sees no change.
   - **Obligations from other sources** are met by the artefact, not by the section (refinement per COR-050): a friction obligation on an anchored page is met when the page carries one of the core record's three answers in the diff — updated, unchanged with its justification, or deferred with its reason. This capability lists those answers in the description, in a section of their own written from the change check's list (refinement per [project-management:DEC-055-pr-lists-answers]); a documentation capability's agent may propose the `## Doc impact` section, but no line of either section meets anything on its own, because the check must hold for a pull request from any tool and with no description at all. An obligation for undocumented new code is met when a page anchoring that code appears in the diff; the audited escape is the removal override of point 1.
   - A section-wide "No doc impact" justification meets only mapping obligations, and only while the mapping's setting is advisory.

   An obligation left unaddressed is reported.

3. **Enforcement per source.** Each source of obligations has its own enforcement setting in this capability's project configuration.
   - The mapping keeps its existing setting.
   - Obligations contributed by a documentation capability have a separate setting, advisory by default.
   - Enforcing one never enforces another.

   As before, a warning at pull-request time is only a speed-bump. Real enforcement is the project wiring the documentation check as a required status in its continuous integration.

4. **What a documentation capability contributes.** When one contributes to the point, it contributes obligations of two kinds: friction on anchored pages, and uncovered surface — new code that nothing describes (COR-050 point 8). It may also propose a `## Doc impact` section through its own agent, for the author to confirm or edit. That proposal is not slot data, because the slot carries obligations only. An anchored page's friction is cleared on the page itself — a revalidation or a deferral (COR-050) — and the core change check verifies that; this capability's check reads the same machine-readable result rather than re-deriving it.

5. **Retiring the mapping.** Once a project's pages are anchored, the mapping duplicates what anchors say more precisely. A documentation capability's onboarding may convert mapping rules into page anchors and propose emptying the mapping, as the living-docs decision's onboarding describes. The project makes that a reviewed change. Until then, both sources contribute, and an update to a document named by both — present in the diff, with the page's answer — meets both.

## Rationale

**Why a slot, not a replacement.** Letting a documentation capability *replace* this capability's checks would make it re-implement them, or silently drop them. Letting it *add* keeps every guarantee for projects that never install it, and lets the better signal arrive when it is installed. Neither capability depends on the other.

**Why the section requirement stays in the gate.** The `## Doc impact` section is the human "did you think about documentation?" step, and it applies to Tasks at filing time, when there is no diff yet. Making it a slot entry would let a filler or a project file drop it. Keeping it in the gate keeps it unconditional.

**Why enforcement is per source.** A project that enforces a few precise mappings has not agreed to enforce a new, broader signal. Separate settings let each source earn enforcement on its own record.

**Why `fail`.** The slot decides whether a pull request may merge. A documentation filler that breaks must not leave the gate passing on fewer obligations than the project expects. This holds even when that filler's own obligations are only advisory. An unresolved slot says the check could not see everything it should, and the message names the filler and the fix. Per the slots record, the stricter use decides.

**Why retire the mapping by a reviewed change.** The mapping is the project's own configuration. Emptying it automatically at onboarding would remove a check the project might still rely on in its enforcement setup.

### Alternatives considered

- **A `union` slot.** Rejected. It lets a project override or suppress an obligation with no recorded reason.
- **Keep the checks separate.** Rejected. Two drift signals would fire on one change, with different precision and different noise.
- **The documentation capability replaces this capability's checks.** Rejected. It either duplicates them or loses them.
- **Run anchor friction here directly, without a documentation capability.** Rejected for now. Pages are anchored in practice only where a documentation capability does that work. If that changes, it can be added as another filler of the same slot.

## Implications

- **This capability** provides the work-tracking role, declares the point under it, ships its obligation schema and the per-source enforcement settings, and routes its existing mapping check through the slot as the default filler. Its documentation check reads the resolved slot. The mapping stays where it is configured today, as the default filler's input, so no migration is needed. Behaviour for projects without a documentation capability is unchanged.
- **[project-management:DEC-015-doc-update-obligations]** points at this record for how its checks are collected.
- **A documentation capability** may declare its contribution to this point, addressing the role.
