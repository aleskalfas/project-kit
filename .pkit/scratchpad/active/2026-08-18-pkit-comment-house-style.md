---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-18
---

# Pkit comment house style

Establish one coherent model for the GitHub comments pkit writes. Prompted by maintainer feedback on the DEC-049 audit comment: it restated `Bypassed by <actor>` (redundant with GitHub's own comment-author metadata), read poorly, and didn't match the `🧰` filing line — and the same treatment should extend to review verdicts. Rather than restyle one comment, define the model for all of them.

## Method — build bottom-up

Resist jumping to styling. Settle each layer before the next:

1. **Inventory** — every place pkit writes a comment (below).
2. **Where + why** — for each: where it is posted, when, and *why it needs to exist at all* — i.e. what it conveys that GitHub's native surface does not. Some may prove redundant.
3. **Content model** — *then* derive what data each carries. (TBD — after 1–2 settle.)
4. **House style** — *then* the formatting. (TBD.)

This note is currently at steps 1–2.

## Scope

**In scope:** the comments pkit authors on an adopter's **lifecycle issues/PRs**.

**The native surface we must not duplicate.** GitHub already shows, for free: the comment **author** and **timestamp**; the issue/PR **body**; **labels + the timeline** (label / assignee / milestone / state-label changes, merges, native reviews). A pkit comment earns its place only by carrying something *not* on that surface.

**Out of scope (separate surface):** the `report` feature's `pkit-report` / `pkit-report-draft` markers — these are metadata *inside the report feature's own upstream issues and local drafts* (the adopter→pkit reporting channel), not comments on lifecycle issues. Note and set aside.

**Two content categories** (the walk will sort each kind into one):
- **pkit-authored payload** — pkit composes the text (filing, audit, verdict). Candidate for a house style.
- **pass-through** — the text is the user's or adopter's (freeform, hook messages); pkit only frames it. Never restyled.

## Inventory walk — where · when · why · needed?

### A. Provenance — filing comment  → **RESOLVED: drop**
- **Where/when:** `create-issue`, `open-pr`, at creation.
- **Format:** `🧰 Filed under pkit — tree \`X\` · pm \`Y\` · cli \`Z\` — date` + `<!-- pkit-provenance:filing -->`.
- **Boundary test:** its only off-surface payload is the **creation-time version, frozen**. Everything else duplicates the native surface — *who* (creation event + author), *when* (creation timestamp; A's date is redundant), *pkit-managed* (the body footer B already says so). Frozen-creation-version is niche (you want the *current* version) and recoverable from edit history.
- **Resolution:** **drop A.** It does not earn a dedicated timeline comment once B is universal. (Impl note: check for readers of `pkit-provenance:filing`.)

### B. Provenance — body footer  → **RESOLVED: make universal**
- **Where/when today:** every body pkit writes/edits (`create-issue`, `edit-issue`, `edit-pr`, `open-pr`, `set-field`, criterion edits).
- **Format:** `<sub>🧰 pkit · tree \`X\` · pm \`Y\` · cli \`Z\`</sub>` + `<!-- pkit-provenance:start/end -->`.
- **Why:** the pkit version the *current* item is at — the one off-surface provenance fact worth carrying.
- **Resolution:** **B is the universal pkit stamp on every authored item — bodies AND comments.** Every pkit-authored comment ends with this `<sub>` footer (small, grey, unobtrusive). Consequences:
  - Subsumes per-kind version stamps (e.g. D's inline `— pkit <version>` — the footer carries it; D's payload simplifies).
  - A comment then has two orthogonal marker roles: its **kind** marker (`pkit-audit` / `pkit-verdict` — *what* it is) + the **provenance footer** (*which version* wrote it). They coexist; the footer is the shared identity+version frame.
  - Pass-through comments (F freeform, G hook) also get the footer (it's a pkit-posted item), even though their *payload* is the user's/adopter's.

### C. Audit — override (bypass / force)
- **Where/when:** `move-issue` (wrappers pass the reason through), on a `--bypass` / `--force` override, when projection ≥ `audit`. (DEC-049 / DEC-014.)
- **Format today:** `<!-- pkit-audit -->` + `Bypassed by <actor> <<email>>: <reason>`.
- **Why:** the **reason** a gate was overridden — the justification. The timeline shows the label change but never the *why*; this must survive a later failure and be visible to a reviewer.
- **Category:** pkit-authored payload. **Needed** (reason is genuinely off-surface). *Confirmed defect:* the `by <actor>` restates the comment author — drop it.

### D. Audit — move (full projection)  → **RESOLVED: keep, as an intent log**
- **Where/when:** `move-issue`, on *every* governed move, when projection = `full`. (DEC-049.)
- **Why (settled):** in a mixed human/pkit system, the timeline can't say whether a move was **pkit-governed or a manual edit**, nor **why** it happened; a visible, human-scannable log carries both (and `--check-drift` is CLI-only, on-demand — not for someone just reading the issue).
- **Payload = intent** (not the bare transition — that's on the timeline; not the version — that's the footer; not who/when — GitHub's):
  - **trigger** — which pkit gesture drove it (`start-work` / `review-work` / `done-work` / `promote` / cascade),
  - **causation** — the standout, for *caused* moves: forward cascade `← #613`, closure cascade `← all children done + criteria met` (answers "why did this move?", otherwise invisible),
  - **gate summary** — for gated moves, esp. `done-work`: `merged #718 · APPROVED · CI green`.
- **Concrete (footer carries the version):**
  - `🧰 pkit → \`in-progress\` · start-work`
  - `🧰 pkit → \`review\` · review-work · PR #718 ready`
  - `🧰 pkit → \`done\` · done-work · merged #718 · APPROVED · CI green`
  - `🧰 pkit → \`in-progress\` · cascade ← #613`
  - `🧰 pkit → \`done\` · cascade-close ← all children done + criteria met`
- **Resolution:** keep D at opt-in `full`; its payload is the **intent line** above. The causation cases earn the feature.

### E. Verdict — review
- **Where/when:** `review-pr`, on review. (DEC-028; native review added in #672.)
- **Format today:** `Reviewer agent (local, <name>): APPROVED|CHANGES_REQUESTED` + findings + `<!-- pkit-verdict -->`.
- **Why:** carries the review **findings** (off-surface) **and** is the **machine gate signal** — `done-work` parses the first line (exact match) to admit the merge.
- **Category:** pkit-authored payload. **Needed.** *Constraint:* the first-line grammar is load-bearing — any restyle changes the gate parser in lockstep.

### F. Freeform — pass-through
- **Where/when:** `comment-issue`, `comment-pr`. (DEC-047.)
- **Format:** the user's body + trailing `<!-- pkit-freeform -->`.
- **Why:** lets a user/agent post a comment *through the validated path*; the marker positively tags it as **user content** so pkit's own comment-readers don't mistake it for a structured signal (write-side counterpart to a read-side refusal).
- **Category:** pass-through. Content is the user's — **not restyled**; only the marker frame is pkit's.

### G. Hook — adopter pass-through
- **Where/when:** `fire_hooks` on lifecycle events. (DEC-024.)
- **Format:** the adopter-configured message + `<!-- pkit-hook: <id> -->`.
- **Why:** adopter extension point — the *message* is the adopter's.
- **Category:** pass-through. **Not restyled**; only the marker frame is pkit's.

## What the walk surfaces (to settle before content/style)

- **Two clean categories:** pkit-authored payload (A, C, D, E) vs pass-through (F, G). A house style governs only the former; the latter keeps the user/adopter words and just needs a *consistent marker frame*.
- **Necessity questions:**
  1. **A vs B** — ✅ **RESOLVED:** drop A; B (footer) becomes the universal pkit stamp on every authored item (bodies + comments).
  2. **D** — ✅ **RESOLVED:** keep, reframed as an **intent log** — payload is *trigger + causation + gate summary* (not the bare transition/version/who-when, which live on the timeline/footer/GitHub). Opt-in `full`; the causation cases (`cascade ← #613`, `cascade-close ← all children done`) earn the feature.
- **Confirmed content trims:** C drops `by <actor>` (redundant with the author).
- **Marker consistency** (small, but real): position differs (audit = leading; others = trailing) and only provenance uses `🧰`. A frame convention should unify position + identity across A–G, regardless of the payload decisions above.

## Content model (settled)

The general rule (the boundary test): **a pkit comment carries only off-surface facts** — never who/when (GitHub), the bare transition (timeline), or the version (footer). Per kind:

| Kind | Comment? | Off-surface payload | Category |
|---|---|---|---|
| provenance | footer, not a comment | pkit version of the item | **universal frame** on every body + comment |
| A filing comment | **dropped** | — | — |
| C override | yes (level ≥ `audit`) | the **reason** | pkit payload |
| D move | yes (level `full`) | **intent** — trigger + causation + gate summary | pkit payload |
| E verdict | yes | **findings** + the gate signal | pkit payload |
| F freeform | yes | the user's words (marker only) | pass-through |
| G hook | yes | the adopter's message (marker only) | pass-through |

Every comment C–G ends with the universal `<sub>🧰 pkit · tree · pm · cli</sub>` provenance footer. Projection levels (DEC-049, refined): **`off`** none · **`audit`** (default) overrides only (C) · **`full`** overrides + the move intent-log (C + D).

## Downstream — TBD (the basics are now settled)

- **House style** — one format for the *pkit-authored payloads* (C, D, E), derived from the content model; the `🧰` filing line is the visual reference. Confirmed direction: `🧰 pkit <kind> — <payload>` (Option B, per maintainer) + trailing `<!-- pkit-<kind> -->` + the universal `<sub>` footer. Marker position unified to trailing across all kinds.
- **Decisions** — pm DEC + amendments (DEC-049 audit content + levels, DEC-028 verdict/parser, DEC-024/047 frame, DEC-041 provenance → drop A / footer-on-comments); a shared `_lib` renderer; implementation slices. The #690 audit-restyle folds in.

## Retirement (COR-012)

Produces a pm DEC (pkit comment content + style model) + implementation slices under a new EPIC.