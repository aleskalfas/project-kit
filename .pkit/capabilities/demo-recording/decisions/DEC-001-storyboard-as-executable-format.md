---
id: DEC-001
title: The storyboard markdown document IS the executable form
status: accepted
date: 2026-06-18
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

A recorded CLI demo is a sequence of typed actions — narrate this line, run that command, wait for the assistant, type into pane 2. That sequence has to live somewhere. Two storage media compete:

- **An executable prose document.** A plain markdown file with a title, step headings, and fenced directive blocks. The same file a colleague reads to understand the demo is the file the runner executes.
- **A structured data file plus a generator.** A YAML/JSON spec describing the demo's structure, consumed by a generator that produces (or directly drives) the actions. The human-readable artifact, if any, is generated from the data — the data is the source of truth, the readable form is downstream.

The choice is foundational: it fixes what an author edits, what the runner consumes, and whether the artifact is legible without tooling. Everything else in the capability (the parser, the plugin interface, the directive vocabulary) follows from it.

## Decision

**The storyboard markdown document is itself the executable form.** There is no separate data file and no generation step. An author writes a markdown file — an H1 title, optional YAML front-matter, `## Step N — <title>` headings, prose between steps, and fenced code blocks whose language tag names a directive — and the runner parses and executes that same file directly.

The document is the single source of truth. It reads as a coherent narrative in any markdown viewer with no tooling loaded; the fenced blocks carry the executable bits, and the prose around them carries the story a human reads. Unknown fence tags are warnings, not errors, so a storyboard stays readable even when the providing plugin is absent.

## Rationale

**Read-without-execute is the headline property.** A recorded demo is a communication artifact before it is an automation: a colleague needs to understand what the demo does without owning a Mac, iTerm2, or the recording toolkit. An executable prose document renders as that narrative for free — the title, the step titles, and the prose are exactly what a reader wants, and the fenced directives sit inline like stage directions. A data-file-plus-generator inverts this: the legible form is a build output, so reading the demo means either running the generator or reading raw structured data that was never meant for human eyes.

**One artifact, not two, avoids drift.** With a data file and a generated readable form, the two can fall out of sync — the classic generated-artifact hazard. Collapsing them into one document removes the failure mode entirely: there is nothing to keep in sync.

**The content is genuinely a linear script.** A CLI demo *is* an ordered sequence of beats — this is the shape a recorded walkthrough naturally takes. The `## Step N` container fits because the underlying thing being modelled is itself linear. The data-file medium earns its keep precisely when the content is *not* a linear script — when the source of truth is a set of parallel states, a component tree, or an interaction table that a deterministic generator must consume. That is a real and legitimate shape, but it is not the shape of a recorded CLI demo. A capability whose content was structured-and-branching would correctly reject the executable-prose medium for the same reasons this one embraces it; the medium follows the content, and recorded demos are linear prose-with-directives.

### Alternatives considered

- **Structured data file + generator.** Considered and rejected for recorded CLI demos. It is the right medium for content whose source of truth is a tree or a state set consumed by a deterministic renderer — the readable form is then genuinely a generated artifact and read-without-execute is irrelevant. Recorded demos are the opposite: linear, narrative, and most valuable when legible without tooling. Adopting the data medium here would add a generation step, a second artifact to keep in sync, and would make the demo unreadable without running the generator — all cost, no fit.

- **A driver script per demo (imperative bash/Python the author writes).** Considered and rejected. It collapses author intent and execution machinery into one file: the author has to write keystroke-injection plumbing, and a reader has to mentally execute bash to recover the demo's narrative. The executable-prose document keeps intent (what to narrate / run) declarative and legible while the machinery lives in the runner and plugins.

## Implications

- The parser ([demo-recording:DEC-002-three-layer-plugin-architecture]) operates on markdown and produces a structural tree; it is the first consumer of this decision.
- Authoring tooling targets markdown, not a schema editor: the `demo-recording` skill's `storyboard-author` operation walks the author through the document format. The one schema the capability ships models the *recording configuration* (the `record.yaml` shape), not the storyboard document — the document's grammar lives in the parser and the README spec, by this decision, because the document is prose-with-directives rather than structured data. (This record is authored ahead of the relocation that lands those scripts and that schema; it states design intent, not yet-shipped state.)
- Because the document is the source of truth, storyboard files are **adopter content**, not capability content. The capability ships the format, the parser, the runner, and the plugin; adopters write their own storyboards. See the README's adopter-vs-capability boundary.
