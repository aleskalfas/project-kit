---
id: DEC-003
title: Ship one capability now; split format from recording only when a second backend recurs
status: accepted
date: 2026-06-18
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

The three-layer architecture ([demo-recording:DEC-002-three-layer-plugin-architecture]) makes a tempting boundary visible: Layers 1 + 2 (the parser and the plugin interface) are domain-neutral, while Layer 3 (the recording plugin) is the only domain-specific consumer. That invites a packaging question — should the kit ship **two** capabilities?

- An `executable-storyboards` capability — the generic document format, parser, plugin interface, runner, and validator, knowing nothing about recording.
- A `recording` capability — the one plugin, depending on the format capability.

Splitting is only worth its cost if a **second, independent consumer of the format genuinely exists** — some non-recording discipline that wants the same step-plus-fenced-directive document with its own directive vocabulary. The kit's pattern-extraction discipline (COR-007) forbids extracting an abstraction speculatively: extract only when the shape *actually* recurs.

A candidate second consumer was examined directly: a ux/ui-design discipline, on the claim that it wanted the same executable-document format with its own directives (`screen`, `component`, `interaction`, and the like). The way to settle such a claim is to try to *disprove* the fit from the candidate's real needs — to author one believable example in the generic format and see whether the format stays out of the way or has to be fought — rather than to rubber-stamp it. That examination is reproduced as the contrast case in the Rationale below; it is the substance of this decision, not an external authority.

## Decision

**Ship `demo-recording` as a single capability.** It owns the generic storyboard format (parser, plugin interface, runner, validator) and the CLI-recording plugin together. The internal three-layer seam ([demo-recording:DEC-002-three-layer-plugin-architecture]) is preserved, but the package is one.

**Defer the format/recording split** until a second, independent, *non-recording* execution backend actually recurs. The explicit split criterion: when a genuine second consumer registers a non-recording directive vocabulary against the Layer-2 interface and would ship its own plugin, *then* extract `executable-storyboards` (Layers 1 + 2) into its own capability and have both `recording` and the new consumer depend on it. Until that consumer exists, no split.

## Rationale

**The candidate second consumer was examined and did not hold — here is the reasoning in full, so the decision rests on the argument, not on a deferred authority.** That discipline's source of truth is *structured data* — a set of parallel states, each a component tree, plus an interaction contract — consumed by a deterministic generator, not a linear `## Step N`-with-prose-directives document. Four things break when one tries to host it in the generic format: (1) the linear step container is the wrong shape for a tree-and-a-set — a flow narrates one path, but the *set* of states (resolving / none / some / error) has nowhere to live in a single linear journey; (2) the directives it could name would *carry* structured YAML rather than *be* prose directives, so the markdown step scaffold becomes a wrapper around data, not a host for it — nameable is not the same as fitting; (3) its execution would be an in-process tree-to-medium render (tree → HTML / CLI / TUI), not a stream of action tuples for a bash dispatcher, so the recording execution model does not transfer; and (4) read-without-execute is irrelevant when the readable form is the *rendered* screen, which needs the generator anyway. Hand-authoring one believable example confirms it: the prose around a `screen` fence adds nothing, and a "state" step and an "action" step end up masquerading as sibling steps — the format is fought, not used. The one slice of that discipline that *did* sit naturally in an executable storyboard was "record a demo of a generated UI walking a flow" — which is the recording consumer again, pointed at a generated UI instead of a terminal, not an independent second consumer. That argues *against* the split, not for it.

**One real consumer is exactly the COR-007 threshold for shipping, and exactly below the threshold for splitting.** Recorded CLI demos are a field-proven, recurring need — that earns the capability. A second *format* consumer is not proven — that withholds the split. Shipping the abstraction now would be the speculative extraction COR-007 forbids: two capabilities, a cross-capability dependency, and version-compatibility obligations, all to serve one consumer.

**The split stays cheap to do later because the seam already exists.** Because [demo-recording:DEC-002-three-layer-plugin-architecture] keeps the core domain-neutral with one-directional knowledge flow, a future split follows the existing Layer-1+2 / Layer-3 boundary mechanically — it relocates code along a line that is already drawn, rather than discovering and cutting a new one. Deferring therefore costs almost nothing in future rework while saving the upfront cost and the standing dependency now.

### Alternatives considered

- **Split now into `executable-storyboards` + `recording`.** Rejected: no proven second consumer, so it is a speculative extraction (COR-007). It also imposes a capability-to-capability dependency and version-compatibility coupling immediately, for a single real consumer.

- **Collapse the three layers into a recording-only monolith** (give up the internal seam since there is only one plugin). Rejected: that would throw away the cheap option value of a clean split later and would re-couple the stable parser to the volatile recording semantics. Keeping the seam internal is free; discarding it is not.

## Implications

- The capability is named `demo-recording`, not `executable-storyboards` — the package name reflects what it does today (record CLI demos), with the generic format as an internal module rather than a separately-installable unit.
- No `requires_capabilities` edge is declared for the format, because the format is not a separate capability.
- If and when the split is earned, it is a structural change worth its own change-set: extract Layers 1 + 2 into `executable-storyboards`, leave Layer 3 in `recording`, and declare the dependency. The split criterion in the Decision section is the trigger; absent a recurring non-recording backend, the question stays closed.
- The naming also sidesteps a same-repo collision with the methodology's COR-016 *scripted-scenario* storyboards (a different sense of "storyboard"): the recording capability's authoring skill is named `demo-storyboard-author` to keep the two senses distinct.
