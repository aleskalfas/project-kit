---
id: DEC-004
title: Assume macOS for v1; gate at the recording-plugin boundary, defer the portability abstraction
status: accepted
date: 2026-06-18
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

The recording machinery is macOS-specific: it injects keystrokes via `osascript` and System Events, controls iTerm2 windows via AppleScript, and captures the screen via `screencapture`. A Linux equivalent would need an entirely different stack (e.g. `xdotool`/`ydotool` for keystrokes, a different window manager and recorder). The capability has to take a position on platform, and there are three sub-questions:

1. **What platform does v1 support?** macOS only, or a cross-platform abstraction from the start?
2. **Where does the platform coupling live?** Is the whole capability macOS-bound, or only part of it?
3. **Is platform an adapter-overlay concern?** The kit ships a mechanism (per the project-management capability's adapter-overlay precedent) for a capability to contribute harness-settings overlays. Does OS portability belong there?

Getting these wrong is expensive in opposite directions: a premature cross-platform abstraction is speculative complexity (COR-007), while platform coupling smeared across the whole capability would taint the otherwise-neutral format and runner.

## Decision

1. **v1 assumes macOS (darwin).** No cross-platform abstraction is built.

2. **A single platform gate sits at the recording-plugin boundary (Layer 3 of [demo-recording:DEC-002-three-layer-plugin-architecture]), not at the capability or format entry.** The recording plugin's executable entry points refuse to run off darwin with a clear message; the parser, plugin interface, runner, and validator (Layers 1 + 2) stay platform-neutral and run anywhere.

3. **Platform is NOT modelled as a harness-settings adapter overlay** — the mechanism by which a capability contributes settings into a specific AI harness's configuration ([project-management:DEC-030-capability-contributed-adapter-overlays]). That mechanism addresses harness configuration, which is a different axis from operating-system portability. OS portability, when it is eventually needed, is a matter of a second recording backend, not a settings overlay.

## Rationale

**The platform boundary already coincides with an existing architectural boundary, so the gate has an obvious home.** [demo-recording:DEC-002-three-layer-plugin-architecture] established that all domain-and-platform knowledge lives in Layer 3 and that execution (not parsing) is where side effects happen. The macOS coupling is exactly the keystroke / window / capture machinery in that layer. Placing the gate at the format or capability entry would be wrong twice over: it would block the platform-neutral validate path (an author on Linux can still legitimately *validate* a storyboard's syntax), and it would falsely advertise the whole capability as macOS-bound when only its execution is.

**A single gate beats scattered checks.** One refusal point at the recording-plugin entry is auditable and cannot drift; sprinkling `uname` checks through the bash primitives would multiply the surface and risk inconsistency.

**Deferring the portability abstraction is COR-007 applied to platforms.** There is no Linux consumer today. Building a "keystroke injector + window manager + screen capturer" interface now, with a macOS implementation and a hypothetical Linux one, is the speculative extraction the pattern-extraction discipline forbids. When a real Linux consumer recurs, the portability story is naturally a *second recording backend* selected behind the Layer-2 plugin seam — the same seam the architecture already provides — not a retrofit. The clean layering keeps that future option cheap, exactly as it does for the format/recording split ([demo-recording:DEC-003-single-capability-deferred-split]).

**Harness-settings overlays are the wrong tool for OS portability.** The capability-contributed adapter-overlay precedent ([project-management:DEC-030-capability-contributed-adapter-overlays]) solves "this capability needs to contribute settings into a specific AI harness's config." Operating-system support is orthogonal: it is about which keystroke and capture primitives exist on the host, not about harness configuration. Reaching for the overlay mechanism here would conflate two independent axes and saddle the capability with overlay machinery it does not need.

### Alternatives considered

- **Cross-platform abstraction in v1** (an injector/window/capture interface with macOS + Linux backends). Rejected: speculative complexity with no Linux consumer (COR-007). The plugin seam already provides the future extension point if portability is ever earned.

- **Platform gate at the capability or format entry.** Rejected: blocks the platform-neutral validate path and mislabels the neutral Layers 1 + 2 as macOS-bound. The gate belongs where the platform coupling actually is — the recording plugin.

- **Model platform via a capability-contributed adapter overlay** ([project-management:DEC-030-capability-contributed-adapter-overlays]). Rejected: adapter overlays are for harness settings, a different concern from OS portability. Using them here conflates orthogonal axes.

## Implications

- This decision is authored before the toolkit is relocated, because it governs where the gate goes: the relocated recording plugin gains one darwin check at its executable boundary, and nothing is added to the parser, interface, runner, or validator.
- The README documents the macOS/iTerm2 requirement and the rationale for the boundary placement, so adopters know the format and validation work cross-platform while recording does not.
- If a Linux consumer ever recurs, the migration path is a second recording backend behind the existing plugin seam — not a rewrite, and not an adapter overlay. Until then, the portability question stays closed.
