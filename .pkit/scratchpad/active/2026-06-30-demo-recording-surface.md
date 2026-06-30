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

## Crystallises into (expected — placeholder)

- TBD: likely new demo-recording DECs (the surface model + per-backend directives) and
  capability code for the VS Code / browser / narration backends.
