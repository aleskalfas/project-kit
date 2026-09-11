---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-27
---

# Comment render seam + house-style decisions (settled design → realization)

**Anchor task:** Feature #757 ("Design pkit comment house-style + render seam")
under EPIC #756. This note is *Feature A* — **how pkit composes any comment**. The
sibling *Feature B* (#795, under EPIC #725) — **how reviews are produced,
aggregated, and gate a merge** — is split onto its own branch
(`feat/795-...`); its decisions live in
`2026-08-28-review-output-and-merge-gate-decisions.md`.

**The one shared contract** that keeps A and B decoupled: the
**`format(data) → string`** seam interface + the review data schema. B consumes
this seam (and ships a temporary formatter behind it so it isn't blocked on A);
A owns the general renderer. Neither depends on the other's delivery.

Rationale companion (the architect's full exploration):
`2026-08-27-render-seam-architect-exploration.md`. This note is the *decisions*;
that one is the *reasoning*.

---

## Decisions

**A1 · Core principle.** *The agent never owns the comment bytes.* One shared helper
composes every pkit-authored comment from **structured data**; producers (review
agents, audit steps, hooks) hand over *data*, and the helper writes every character
(icons, layout, markers, footer). One altitude up from ADR-037's "the agent never
owns the footer bytes." This is what makes a house style enforceable rather than
aspirational.

**A2 · Home = project-management `_lib` (e.g. `comment_render.py`), not backbone.**
software-engineering ships **no scripts** (prompt files only) — it consumes the
*contract*, not the *function*. One code consumer today. **Written-down hoist
trigger:** move to a shared backbone home the day a *second capability ships code
that renders a pkit comment* (revisit ADR-003's `.pkit/lib/` then). Until then it
stays pm-owned.

**A3 · Style storage = three layers, each owning a different job** (not three
interchangeable ways to do one job):
- **Template file** → the human-visible layout, *with presentational logic only*
  (loop over findings, hide an empty section). The "template files" preference —
  accepted for the human layout.
- **Small schema (`comment-style.yaml`)** → the tokens: icons (🧰 tool / 🤖 agent),
  section labels (*Blocking:* / *Advisory:*), verdict→emoji map, and **every
  machine-marker string** (drift-guarded against code, the #763 pattern).
- **Code** → assembly, derivation (values computed once), and placing the
  machine-critical parts.
- Rule for "logic in the template": **presentational logic yes; computed/machine
  logic no** (anything the gate parses, or a value derived once). Accepted cost: a
  templating-engine dependency in the otherwise self-contained scripts.

**A4 · Footer.** Delegate the footer bytes to `provenance.render_footer()`; do NOT
reimplement. Comments are *constructed once and never edited*, so "exactly one
footer" holds **by construction** (stronger than the body path's strip-then-append).
**Hazard / decision:** never run `strip_footer`/`stamp()` over a *pass-through*
comment carrying a user's words — its cut-to-EOF would silently delete everything
after a pasted footer sentinel. **Rule: append-only for user-authored / pass-through
kinds** (freeform, hook). Footer-on-every-comment amends DEC-041 (needs a changeset;
check readers of `<!-- pkit-provenance:filing -->` before dropping the filing
comment).

**A5 · The verdict line is a schema-owned, drift-guarded render contract.** The
settled machine record reads the *human header* anchored on the verdict WORD (see
#795 for the gate-read side). The render seam's obligation here: emit the per-agent
verdict line to a **schema-owned contract**, and provide the `parse(render(x)) == x`
round-trip test so the renderer and the gate's parser can't drift. Only that verdict
line is load-bearing; the rest of the comment stays free to restyle. (The staleness
SHA the gate needs is a #795 concern — G2 — not carried in the human header.)

*(The DEC-028 / ADR-042 supersession this enables is a gate decision, authorised and
tracked in #795.)*

## Content model (from the house-style note)

The general boundary rule — **a pkit comment carries only off-surface facts** (never
who/when, the bare transition, or the version) — plus the per-kind payloads (drop the
filing comment; universal `<sub>` footer; `🧰 pkit <kind> — <payload>` frame; trailing
`<!-- pkit-<kind> -->` markers) are settled in `2026-08-18-pkit-comment-house-style.md`.

---

## Artifacts to produce (Feature A)

1. **pm DEC** — the comment content + house-style model (amends DEC-049 audit
   content, DEC-041 footer-on-comments, DEC-047 frame). #757's named product; retire
   the A-cluster design scratchpads as produced.
2. **project-kit ADR** — the render-seam contract: sole-constructor renderer; markers
   schema-owned with drift guards; footer delegated to provenance
   (constructed-vs-edited distinction); the `parse(render(x)) == x` round-trip
   invariant; a guard test proving nothing composes a pkit comment outside the seam;
   the pinned hoist trigger. 4th member of the seam family (ADR-026 / ADR-031 /
   ADR-037).

**Not a COR** unless the A2 hoist trigger fires. **Ordering:** DEC first (what it
renders) → ADR (how it holds). The DEC-028 verdict-grammar amendment is carried by
#795, coordinated via the shared seam contract.

## Next steps

1. Author the **pm DEC** (decision-author) from this note + the architect companion
   + `2026-08-18-pkit-comment-house-style`.
2. Author the **project-kit ADR** (render-seam contract).
3. Slice implementation under EPIC #756 (align all comment posters to the house
   style; the #690 audit-restyle folds in). Coordinate the verdict-line render
   contract with #795 (the gate reads it).

## References

- Issues: #757 (anchor) · #756 (EPIC) · #795 (sibling: review + gate, EPIC #725) ·
  #690 (audit-comment feedback) · #771 (agent-dispatch delivery).
- Decisions: DEC-041 (provenance footer) · DEC-047 (freeform comment) · DEC-049
  (audit / journal) · DEC-028 (verdict grammar — amended in #795).
- ADRs: ADR-037 (provenance write-path) · ADR-026 / ADR-031 (seam family) · ADR-003
  (shared-lib hoist trigger) · ADR-006 (view assembler) · ADR-011 (CLI styling /
  `strip_ansi` invariant).
- A-cluster scratchpads (this branch): `2026-08-18-pkit-comment-house-style` ·
  `2026-08-27-render-seam-architect-exploration`.
