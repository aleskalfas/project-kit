---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-30
---

# Demo-recording surface — multi-window stage (VS Code + browser + narration)

> Sibling to `2026-06-29-minimal-adoption-path.md` — the demo *scenarios* live there; this
> note defines the *surface* they record on, and the robust upgrade the demo-recording
> capability needs to drive it. Filled **step by step**; nothing is a conclusion until marked.

## The question

What is the recording **surface** for the pkit demos, and what upgrade does the
demo-recording capability need to drive it? Today the capability records iTerm2
RECORDING + CONTROL panes — CLI-only. The demos need a richer composed stage.

## Operator's surface vision (stated; to pin as we go)

Three surfaces, switched between during a take:
1. **VS Code (primary)** — run all CLI commands (integrated terminal) **and** show the repo
   changes (file tree / diffs / editor).
2. **Browser (secondary)** — show what's happening on GitHub live (issues, board, PRs).
3. **Narration** — when/where/how TBD. Options floated: (a) a dedicated narration **window**
   showing a presentation (md or pdf) whose current page we control; (b) **subtitles**
   overlaid on the action. Operator leans **(a) narration window first**.

Plus: the engine **switches between the three** as the storyboard progresses.

## Extension seam / constraints (noted, not decided)

- **Plugin architecture (DEC-002)** is the clean seam: the storyboard format is generic and
  recording is one plugin; new backends/directives register without touching the format. So
  VS Code / browser / narration are new backends — an extension, not a rewrite.
- **DEC-004** — recording is macOS/iTerm2-coupled today; this upgrade broadens the stage
  (VS Code, a browser, a presentation surface) and must keep the platform gate honest.
- **S1 already surfaced** adjacent needs (in the adoption note): `before_record`/setup hook,
  disposable-repo teardown, first-class agent-boot, `assert` directive.
- **Robust upgrade → architect review** when the model firms (capability architecture).

## What we've settled (the walk)

- **A1 — the capture model: fullscreen, one window at a time, swapping.** A single 1440p
  screen recording that shows exactly **one full window at any moment**; the engine **swaps**
  the active fullscreen window between the three surfaces as the demo runs. NOT composited /
  side-by-side. This keeps every surface large and legible and the viewer's attention on one
  thing — and dodges the legibility/attention risk of a tiled stage.
  - **The narration is its own full window — a presentation (md/pdf) — and it is the MAIN
    DRIVER.** The demo is structured *as a presentation*: slides are the spine; the engine
    cuts to VS Code to run/show CLI + repo, cuts to the browser to show GitHub, then back to
    the presentation. (This also answers the earlier window-vs-subtitles question: it's a
    presentation window, no subtitles needed.)
  - Build implication: the engine must **bring each app to fullscreen-front on cue** (a
    window-swap/app-activation mechanism across three apps) and **drive a controllable
    presentation** (advance pages) — a new backend per DEC-002, not the iTerm2 `panes` model.

- **A2 — presentation = PDF generated from Markdown.** Author narration as markdown → build a
  PDF → the presentation window is a **PDF viewer**, page-controlled by the engine
  (next/prev keystroke). Best of both: md authoring ergonomics; reliable page control; a
  distinct app from the GitHub browser (clean window-swap).

- **A3 — portability stance: build macOS-first, design OS-agnostic-*ready*.** Don't test
  Windows now. But pick cross-platform tools wherever it's free, and put the genuinely
  OS-specific bits behind clean **per-OS backend seams** (per DEC-002) so a Windows backend
  slots in later without rework. This **generalizes DEC-004's platform gate** (architect
  review when the model firms) rather than hard-committing to cross-platform now.
  - *Free / cross-platform:* Marp (md→PDF build, Node), Playwright (browser automation),
    ffmpeg **or** OBS (screen capture).
  - *Behind per-OS seams (macOS implemented first):* window swap-to-front, PDF viewer +
    page-advance, input injection.

- **A2-refinement:** Marp stands for the build (cross-platform). **macOS Preview was mac-only
  → it moves behind the per-OS "PDF viewer + page-advance" seam** (mac-first), not a fixed
  choice.

- **A4 — capture + swap engine: OBS Studio, driven via obs-websocket.** Each surface
  (VS Code / browser / PDF) is an OBS *scene* (window-capture source); switching scenes =
  swapping windows in the recording — cross-platform for free, no OS window-activation. OBS
  is the recorder too. **Fully scriptable** (obs-websocket API; `obsws-python` / 
  `obs-websocket-js`): launch → configure scenes/sources → start → switch → stop, **zero
  per-recording manual steps**. *One-time machine setup only* (install OBS; enable websocket;
  grant macOS screen-recording TCC permission once — unavoidable for any recorder). Beats the
  ffmpeg+OS-window-activation alternative, which would need a per-OS window-swap backend.

## Emerging architecture (consolidated so far)

- **Surface:** single 1440p capture; one full window at a time; engine swaps between them.
- **Driver:** a **PDF presentation (built from Markdown via Marp)** is the spine; the engine
  cuts to **VS Code** (CLI + repo) and the **browser** (GitHub) for live action, then back.
- **Capture + swap:** **OBS** scenes via obs-websocket (cross-platform).
- **Browser automation:** **Playwright** (cross-platform).
- **Per-OS seams (macOS first):** input injection (type into VS Code / advance PDF), PDF
  viewer, and the macOS screen-record permission. All behind DEC-002-style backends.

- **A5 — delegate "video production" to OBS; keep our engine for *driving the demo*** (COR-007).
  Don't rebuild what OBS does: **transitions** (cut/fade/slide), **encoding/resolution/fps/
  output**, **overlays** (active-region highlight, section title / step counter, branding,
  subtitles), **audio mixing** (for future voiceover/TTS), **crop/zoom/scale filters**.
  - **Caveat (DEC-001):** drive all of it **via obs-websocket from the storyboard**, never by
    hand-configuring OBS's GUI — else the demo definition splits between our file and OBS
    config and the storyboard stops being the single source of truth. "Use more OBS" =
    "*drive* more of OBS from the storyboard."
  - **Keep the dependency lean:** prefer OBS **built-in** features over third-party plugins
    (cross-platform availability varies — matters for OS-agnostic-ready).
  - **Do NOT delegate:** interactive GitHub → keep **Playwright** (OBS browser source renders
    a URL but can't be *driven*). PDF-presentation-as-driver stays; OBS text overlays are an
    optional complement (subtitles/section title), not a replacement for the slide spine.

## Open questions (the walk)

- **Q5 (parked detail):** **Input injection** (the last per-OS piece) — keystrokes to VS Code
  / PDF (browser is Playwright). `pyautogui` (cross-platform, focus-then-type) vs per-OS
  (`cliclick`/AppleScript). Mental model: focus the target app to receive keys while OBS
  shows whatever scene. Settle when we build the input backend.

## Critic review — BLOCKER: not architect-ready as written

The OBS-centric design above reads as a confirming narrative whose load-bearing claims break
on the first disconfirming instance. **Must-fix before architect:**

1. **"No OS window-activation" (A4) is false.** Typing a beat (VS Code, PDF page-advance)
   needs the target app **OS-focused**; OBS swaps *display*, not *focus*. The per-OS window
   problem returns on nearly every beat — so A4's "OBS beats ffmpeg for free" comparison is
   invalid. Honest claim: OBS buys cross-platform *capture/encoding/transitions*, **not**
   freedom from a per-OS focus seam. Un-park the input model (old Q5) and re-derive A4 on
   that basis.
2. **OBS macOS capture is asserted, not verified.** Window Capture is deprecated on macOS 13+
   (→ ScreenCaptureKit); "captures even when not frontmost" + the scripted-launch/TCC
   interaction need a 20-min empirical check, not an assumption. RF for the whole spine.
3. **Determinism unaddressed** for the headline agent/live-GitHub demos. `assert` catches a
   bad take after the fact; it doesn't make takes repeatable. Needs a position on
   disposable-repo reset + clean slate, or an explicit "operator-supervised, not CI" scope cut.
4. **Decision-tension to frame for the architect as real amendments:** DEC-001 (OBS
   scene-collection/profile is GUI-configured external state → single-source-of-truth breaks
   unless bounded); DEC-002 (long-lived Playwright / obs-websocket sessions vs the
   inert-tuple→bash contract); DEC-004 (multiple per-OS seams vs the single-auditable-gate
   property).
5. **Scope — likely over-built.** Four new backends + hooks + assert + DEC-004 amendment for
   "author 9 demos one-by-one" may be too much. Weigh the leaner alternatives below.

### Leaner counter-alternatives (never weighed — do so before committing)
- **Pre-rendered slide *video* segments** stitched by ffmpeg around the live captures — no
  live PDF viewer, no page-advance injection, no third app to focus. Loses nothing for a
  recorded (non-interactive) artifact.
- **One VS Code window** holding terminal + editor + a markdown-preview pane, captured as a
  single window — kills most multi-app focus juggling; reuses the existing single-window
  engine. Browser stays the one genuine second surface.
- **Human-driven semi-scripted take** + one full-screen capture (no scene scripting, no
  websocket, no Playwright, no per-OS input seam) — ~20% of the build for demos that are
  non-repeatable anyway.

Agreement worth keeping: the **swap-one-window-at-a-time decision (A1) is right** — the
critique is of the *mechanism* (OBS), not the decision. Keeping Playwright over an OBS
browser-source is correctly reasoned.

## Architect review (ran out-of-order, *before* critic; presupposes OBS)

Filed as Feature **#364** under EPIC #359 (EPIC-under-EPIC forbidden by the schema → Feature
is the senior allowed child). Architect escalation — **conditional on choosing the OBS path
(Option A); moot if we pivot leaner (Option B):**
- **Supersede DEC-004, don't "generalise" it** — OBS relocates the platform coupling (capture
  + swap become cross-platform; only input injection / PDF viewer / macOS TCC stay per-OS).
  That's a partial supersession of a foundational decision → use the explicit supersession
  gesture.
- **OBS-as-hard-dependency = new failure semantics** (a stateful daemon over a websocket:
  connection/version/scene-drift). Needs a DEC-001 corollary: the engine establishes all OBS
  scene state programmatically per take, never from hand-configured GUI state.
- Structure notes (apply either way): "**backend**" is overloaded — directive families
  (browser / presentation / assert) register at the DEC-002 Layer-2 seam; OBS / Marp /
  input-injection are Layer-3 infra that don't. And the **input-injection + `assert` track is
  lower-risk and should split** from the OBS surface upgrade.

**Reconciliation:** architect refined *how to land OBS*; critic questioned *whether OBS is
right / not over-scoped*. Critic's challenge is the more fundamental and logically first.

**DECISION — Option A (OBS) chosen.** So architect's escalation items are now **live**: when
the DECs are authored we must (1) *supersede* DEC-004 (the coupling relocates), and (2) add
the DEC-001 OBS-dependency corollary (engine establishes all OBS state programmatically).
Critic's must-fixes (esp. RF-1 input/focus model, RF-2 verify OBS macOS capture, RF-3
determinism) still gate the build.

## OBS dependency securing + the capability requirements gap (resolved)

**How it works today (verified):** a capability's `package.yaml` declares only
`requires_backbone` + `requires_capabilities`; install checks only those. There is **no field
for external system tools**, and no install-time check for OBS/ffmpeg/iTerm2 — the platform
requirement is enforced at **record time** (DEC-004), not install. So installing
demo-recording does NOT currently stop you for a missing OBS.

**OS-agnostic securing approach** (no universal GUI-app installer exists → one "ensure-OBS"
interface, per-OS recipe inside — same seam pattern):
- Install per-OS: macOS `brew install --cask obs`; Windows `winget install OBSProject.OBSStudio`.
- **Pin OBS ≥ 28** → obs-websocket built in (no plugin to manage).
- **Pre-seed the obs-websocket config file** (enable server + port + password) before launch,
  and **build scene state programmatically** per take → no GUI config step (satisfies the
  DEC-001 corollary).
- **Per-take health check** (installed → version → launched → websocket reachable) with clean
  per-OS remediation (architect escalation #2 / failure semantics).
- Unavoidable residual: macOS screen-recording **TCC** grant once (no recorder can script it).

**DECISION — add a `requires_system:` capability mechanism, behaviour (a):** declare external
tools (name + min version + per-OS install hint + probe) in the capability schema; **WARN at
install** if missing (preserves DEC-004 "author anywhere" neutrality) + **HARD-gate at record**;
a preflight/`doctor` check verifies. This is a **core capabilities-framework feature**
(benefits any capability with external deps), so it's a **schema_version bump + migration**,
not demo-recording-local.

## Crystallises into

- A **child of EPIC #359** — the demo-recording surface-upgrade track (likely its own child
  EPIC, since it revises DEC-004 + adds backends and needs `architect` review).
- Likely new **demo-recording DECs** (the surface model + per-backend directives) and
  capability code for the OBS / Playwright / presentation / input-injection backends.
- This note retires when that child EPIC + its DECs are filed.
