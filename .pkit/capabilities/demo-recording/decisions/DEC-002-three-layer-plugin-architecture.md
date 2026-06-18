---
id: DEC-002
title: Storyboard execution splits into three layers — parser, plugin interface, recording plugin
status: accepted
date: 2026-06-18
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

Given that the storyboard document is the executable form ([demo-recording:DEC-001-storyboard-as-executable-format]), something has to turn that document into actions. The naive shape is one module that reads the markdown, knows what `narrate` and `shell` mean, and fires the keystrokes. That shape couples three concerns that change for different reasons:

- **Document structure** — what an H1, a `## Step N` heading, and a fenced block are. This is stable and domain-agnostic.
- **The dispatch contract** — how a fence's language tag selects the code that handles it, and what that code returns. This is the seam where new directive families would attach.
- **Recording semantics** — what `boot`, `panes`, `narrate`, `chat`, `shell`, `wait`, `ready`, `keys`, `sleep` actually mean, and the macOS keystroke / pane-selection / screen-capture machinery that carries them out. This is the domain-specific, platform-specific part.

A monolith forces the stable structural code, the dispatch seam, and the volatile recording semantics to live and version together.

## Decision

Storyboard execution is split into **three layers with one-directional knowledge flow**:

1. **Parser (Layer 1)** — reads the storyboard markdown and produces a structural tree: `{title, intro_prose, steps:[{number, title, prose, fences:[{lang, content, line}]}]}`. It knows document structure and nothing about what any directive means. Validation here is purely structural (missing H1, duplicate step numbers, unclosed fences).

2. **Plugin interface (Layer 2)** — a `Plugin` abstract base class and a `PluginRegistry` that dispatches a fence by its language tag to the plugin that owns it. Each plugin implements three methods: `validate(lang, content) → errors`, `describe(lang, content) → one-line summary`, and `actions(lang, content, context) → list of (action_name, arg…) tuples`. A shared mutable `context` dict threads across the run. The registry knows nothing domain-specific; unknown tags are warnings.

3. **Recording plugin (Layer 3)** — owns the recording directive vocabulary and emits named action tuples. A bash runner dispatches each tuple to a concrete primitive (keystroke injection, pane selection, screen capture). All domain and platform knowledge lives here.

Layer 1 knows nothing of Layer 2 or 3; Layer 2 knows nothing of Layer 3's vocabulary; Layer 3 depends on both. The core (Layers 1 + 2) is domain-neutral by construction.

## Rationale

**The seam is where extension would attach, so it must be clean before extension arrives.** A second directive family — were one ever to recur — would register as another plugin against the unchanged Layer 2 interface, without touching the parser or the recording plugin. Keeping the interface domain-neutral now means the cost of that future extension is bounded to writing a plugin, not refactoring a monolith. This is the structural payoff even though the capability ships exactly one plugin today (see [demo-recording:DEC-003-single-capability-deferred-split] for why one).

**Python parses and validates; bash executes.** The `actions()` contract returns inert tuples rather than performing side effects. This keeps the entire parse-and-validate path testable without a Mac in the loop — a plugin's emitted action list can be inspected in pure Python — and confines the platform-specific keystroke machinery to the bash runner. The execution boundary is the same boundary as the platform boundary ([demo-recording:DEC-004-platform-coupling-and-gate-placement]), which is not a coincidence: the layer that executes is the layer that is platform-coupled.

**One-directional knowledge flow is what makes "the core knows nothing domain-specific" enforceable.** It is not a style preference: if the parser imported the recording vocabulary, the format would no longer be separable from recording, and the deferred-split option ([demo-recording:DEC-003-single-capability-deferred-split]) would be foreclosed. The layering preserves that option at near-zero cost.

### Alternatives considered

- **A single monolithic runner** that reads markdown and fires keystrokes directly. Rejected: couples stable structural parsing to volatile recording semantics, makes the parse path untestable without macOS, and forecloses any later separation of format from recording.

- **A two-layer split (parser + recording) with no plugin interface.** Rejected: it saves one abstraction but loses the clean dispatch seam, so the recording vocabulary leaks into the parser's dispatch logic. The plugin interface is cheap (an ABC plus a registry) and is exactly the seam that keeps the core neutral.

- **Plugins that execute directly (an `execute()` method instead of `actions()`).** Rejected: it pushes side effects into Python, crossing the execution boundary, and makes the plugin untestable without the platform. The action-tuple indirection is what buys testability and the clean Python/bash split.

## Implications

- The capability ships Layer 1 + Layer 2 as the domain-neutral core and Layer 3 as the one recording plugin, all under `scripts/` (parser, plugin interface, runner in one subtree; the recording plugin and its bash primitives in another). This record is authored ahead of the relocation that lands those scripts; it states the architecture the relocated code realises, not yet-shipped state.
- New recording directives are added by extending the recording plugin's three methods plus the bash runner's dispatch — no parser or interface change. The directive vocabulary is therefore reference material in the README, not a schema (a directive-vocabulary schema declared at the core would contradict this decision by pulling domain knowledge into a layer that must not have it).
- The clean layer boundary is the precondition for [demo-recording:DEC-003-single-capability-deferred-split]: the format/recording split, if it is ever earned, follows the existing Layer-1+2 / Layer-3 seam rather than imposing a new one.
