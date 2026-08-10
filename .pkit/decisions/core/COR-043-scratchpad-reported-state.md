---
id: COR-043
title: A scratchpad note may enter an optional reported side-state when sent through the report channel
status: accepted
date: 2026-08-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*A scratchpad note that has been **sent through the built-in report channel** may enter an optional **`reported`** side-state: it moves to a lazily-created `reported/` directory, its frontmatter records where it went (issue refs, date, a content hash), and the tooling treats it as **frozen** — post-send edits are detected and surfaced, never silently carried. The state is read back **live**: listing resolves the referenced issues' current state on each ask and prompts retirement when they all close. Scratchpads' primary role — a brainstorming place that sharpens thought inside a project ([COR-012](COR-012-scratchpad-notes.md)) — is untouched: `reported` is opt-in, produced only by an actual send, and most notes never enter it.*

## Context

COR-012 gives exploratory notes a three-state lifecycle — `active/`, retired to `done/` (with `produced` refs) or `dropped/` — with the **folder as the state**. Separately, the methodology ships a universal **report surface** (a built-in command family that composes and files a report to a distribution-configured upstream target; the surface is core, the target is distribution config — see the CLI specification's report section).

In practice the two meet: an adopter's richest problem descriptions *are* scratchpad notes, and the natural gesture is to send the note itself as the report's substance (the report surface can inline a note into the composed report). Once that happens, three questions have no answer today: *where did this note go* (nothing records the resulting issue), *how is it doing* (nothing resolves the upstream state), and *is what I sent still what I have* (the local file can drift from the as-sent text the issue carries). The operator's grounding case: a note authored in one project, hand-carried upstream, planned and shipped there — while the note sat in `active/` indistinguishable from unsent brainstorming, its retirement a manual cross-repo memory exercise.

## Decision

**In plain terms:** when a note is actually sent as a report, the project may remember that — the note moves into a `reported/` folder that exists only while needed, its header says which issue(s) it became and fingerprints what was sent, and the tooling shows how those issues are doing and warns if the local file diverges from what went out. Nothing about ordinary scratchpad life changes; a note that is never reported never sees any of this.

1. **`reported` is an optional side-state of `active`, not a fourth lifecycle stage.** The lifecycle remains COR-012's three states; `reported` refines *active* ("still live, and currently sent upstream"). Retirement proceeds `reported/ → done/` (or `dropped/`) by the same human gestures with the same semantics; the reported note's `produced` refs at retirement naturally include the upstream issue(s). Directories keep encoding a note's **most specific state** — the folder-as-state rule is preserved, refined from "three folders" to "the folders encode the state, including this optional refinement of active" (COR-012 carries a refinement pointer to this record).
2. **The `reported/` directory is lazy.** It is created when the first note enters it and removed when it empties. A project that never reports shows no trace of the mechanism.
3. **Entering the state is produced by an actual send, never by intent.** The report surface stamps the note **only on a successful post** (the draft/URL path sends nothing and stamps nothing). Because the surface's primary posture is URL-first — the post may happen in a browser, outside the tooling — a **manual stamp gesture** exists (supply the note and the resulting issue ref); it also serves retroactive stamping of notes hand-carried before this record. Frontmatter records: the issue ref(s) (one note may become several issues), the reported date, and a **content hash of the full local file at send time**.
4. **Reported notes are frozen by convention and guarded by detection.** Notes are plain files; prevention is not honest — so the discipline is: a note in `reported/` is not edited (the as-sent text is preserved verbatim in the issue it became); follow-up thinking is a **new note** cross-referencing the reported one; and the tooling **detects** divergence (current content vs the stamped hash) and surfaces it wherever the note is listed and before any subsequent send from the project. Detection is a warning, never a gate.
5. **Read-back is live and pull-only.** Listing resolves each reported ref's upstream state at the moment of asking (a cross-repository *read*, unrestricted per [COR-039](COR-039-session-repo-mutation-boundary.md)); nothing is stored or synced, so nothing drifts (the derive-don't-store discipline). Offline or unresolvable degrades to "reported, state unknown" — never blocking, never guessing. When **all** of a note's refs are closed, the listing **prompts** retirement; it never auto-retires (retirement carries `produced` refs only a human can complete — COR-012's retirement-as-human-gesture is unchanged).

## Rationale

**Why core.** The state binds to the **universal report surface**, not to any distribution's target: "this note was sent through the built-in report channel" is meaningful in every adopting project, exactly as the report verbs themselves are. (That the channel is inert until a distribution configures a target is the degrade behaviour, not the placement argument.) A distribution- or capability-local state would fracture a universal artifact's lifecycle per-distribution.

**Why a side-state rather than a fourth stage.** All five grounding behaviours (stamp, freeze, drift-detect, live read-back, retire-prompt) qualify *active* notes; none changes what retirement means. Widening the lifecycle would force every note through a question ("was this reported?") that the overwhelming majority — brainstorming notes — never face. The side-state keeps COR-012's model intact and the brainstorming role pure, which the operator ruled load-bearing.

**Why freeze-plus-detect rather than a write gate.** Notes are files edited by anything; a hard gate is unenforceable theatre. The as-sent text is already preserved verbatim upstream (the issue body); locally, a hash makes divergence *visible* — which is all the integrity claim requires: nobody is misled, nothing is blocked.

**Why live read-back.** A stored status is a second copy of upstream truth and will lie (the same argument the connections layer settled — [COR-038](COR-038-process-connections.md)); a pull-only resolve at each ask is honest at the instant and costs one read.

### Alternatives considered

- **A general `tracked` state** ("this note's question moved into *some* tracker", produced also by in-repo planning flows). Rejected by operator ruling: it would soak tracker semantics into every note's life and muddy the brainstorming role; `reported` stays bound to the report channel. If in-repo hand-offs later want visibility, that is its own question.
- **A fourth lifecycle stage.** Rejected above — it taxes the majority case and complicates retirement for no behaviour the side-state doesn't already give.
- **Frontmatter-only marking (no directory).** Rejected — the folder-as-state visibility (`ls` shows the project's reported surface at a glance; transitions are `git mv`) is COR-012's deliberate mechanic, and a lazily-created directory costs nothing when unused.
- **Hard write-protection of reported notes.** Rejected — unenforceable for plain files; detection delivers the honest half.
- **Auto-retirement on upstream closure.** Rejected — retirement carries human-completed `produced` refs; the prompt is the right strength.
- **A stored/synced status cache.** Rejected — derive-don't-store; see Rationale.

## Implications

- **COR-012 carries a refinement pointer** to this record (the same extension gesture COR-012 itself applied to COR-006), landed in the same change-set as this record's acceptance. Its three-state principle and folder-as-state mechanic stand, refined as stated in point 1.
- **The scratchpad area reference** (`.pkit/scratchpad/README.md`) owns the field layout (frontmatter key names, hash algorithm, ref format) and the `reported/` directory semantics — reference content, not this record.
- **The report surface** gains the attach/stamp behaviour and the manual stamp gesture; the listing gains live resolution, drift surfacing, and the retire-prompt. Command-level detail lives in the CLI specification; the cross-repo-write posture of the send itself is governed by the architecture record for the report channel's foreign write (this record adds only same-repo state on the adopter's side plus cross-repo *reads*).
- **Surface change** — a new principle plus command surface — bumps the affected component's version per the project's versioning policy; the `reported/` directory is lazily-created project-owned content (pure addition, no migration).
- **Acceptance gates the implementing surface** — the attach/stamp/read-back behaviour may not land while this record is proposed (the acceptance gate).
