---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-27
---

# Render seam + merge-gate decisions (settled design → realization)

**Anchor task:** Feature #757 ("Design pkit comment house-style + aggregated review
format — scratchpad → DEC") under EPIC #756. Coordinates with #725 (code-review
discipline) and reshapes DEC-028 / DEC-032 / DEC-050. This note captures the
decisions settled in the design session so **realization continues from here** —
next step is authoring the records (below), then the implementation slices.

Detailed architect exploration (rationale, seam-family citations, candidate
shapes): `docs/architecture/decisions/DRAFT-render-seam-exploration.md` (untracked;
delivered via file hand-off because of bug #771 — see housekeeping). This note is
the *decisions*; that file is the *reasoning*.

---

## Part A — the comment render seam

**A1 · Core principle.** *The agent never owns the comment bytes.* One shared
helper composes every pkit-authored comment from **structured data**; producers
(review agents, audit steps, hooks) hand over *data*, and the helper writes every
character (icons, layout, markers, footer). One altitude up from ADR-037's "the
agent never owns the footer bytes." This is what makes a house style enforceable
rather than aspirational.

**A2 · Home = project-management `_lib` (e.g. `comment_render.py`), not backbone.**
Correction to an earlier assumption: software-engineering ships **no scripts**
(prompt files only) — it consumes the *contract*, not the *function*. So there is
one code consumer today. **Written-down hoist trigger:** move to a shared backbone
home the day a *second capability ships code that renders a pkit comment* (revisit
ADR-003's `.pkit/lib/` question then). Until then it stays pm-owned.

**A3 · Style storage = three layers, each owning a different job** (not three
interchangeable ways to do one job):
- **Template file** → the human-visible layout, *with presentational logic only*
  (loop over findings, hide an empty section). This is the "template files"
  preference — accepted for the human layout.
- **Small schema (`comment-style.yaml`)** → the tokens: icons (🧰 tool / 🤖 agent),
  section labels (*Blocking:* / *Advisory:*), verdict→emoji map, and **every
  machine-marker string** (drift-guarded against code, the #763 pattern).
- **Code** → assembly, derivation (aggregate verdict computed once), and placing
  the machine-critical parts.
- Rule for "logic in the template": **presentational logic yes; computed/machine
  logic no** (anything the gate parses, or a value derived once). Accepted cost: a
  templating-engine dependency in the otherwise self-contained scripts.

**A4 · Footer.** Delegate the footer bytes to `provenance.render_footer()`; do NOT
reimplement. Comments are *constructed once and never edited*, so "exactly one
footer" holds **by construction** (a stronger guarantee than the body path's
strip-then-append). **Hazard / decision:** never run `strip_footer`/`stamp()` over
a *pass-through* comment carrying a user's words — its cut-to-EOF would silently
delete everything the user wrote after a pasted footer sentinel. **Rule:
append-only for user-authored / pass-through kinds** (freeform, hook). Making the
footer universal on every comment amends DEC-041 (needs a changeset; check readers
of `<!-- pkit-provenance:filing -->` before dropping the filing comment).

**A5 · Machine record = read the human header, anchored on the verdict WORD.**
(Chosen over a hidden data block, on the "no divergence / what-you-see-is-what-the-
gate-does" argument.) The per-agent verdict line is a **schema-owned, drift-guarded
contract**; the parser keys on the stable uppercase token (`APPROVED` /
`CHANGES_REQUESTED`) and **ignores the decoration** (emoji, backticks) — so the
emoji/layout can be restyled freely as long as the verdict word stays. A
**round-trip test (`parse(render(x)) == x`)** guarantees renderer and parser agree.
Trade: only *that verdict line* is load-bearing; the rest of the comment stays free
to restyle.
- *SHA tension, resolved:* staleness needs the HEAD SHA, which isn't in the human
  header — resolved by gate-decision G2 (native reviews use GitHub's `commit_id`;
  comment verdicts embed the SHA as a tiny machine token). The SHA is a *fact, not a
  verdict*, so it does not reopen the divergence concern.

**A6 · NEEDS EXPLICIT SIGN-OFF (open).** One-review-per-round aggregation +
reading verdicts this way **supersedes part of DEC-028** (one-comment-one-verdict)
**and ADR-042** (first-line gate selector). This must be made *explicit* (a DEC-028
amendment + an ADR-042 companion), not a silent side-effect — the blast radius is
the merge gate, which **fails closed**. **Coupled:** the DEC-047 freeform spoof
guard reads the same grammar, so any grammar change ships **in the same change-set**
as the guard, or `comment-pr` becomes a verdict-forgery vector. *(Awaiting user
go-ahead before implementation.)*

---

## Part B — the merge gate

**G1 · Authority mode = hybrid.** Auto-detect by default (branch-protection /
self-authored signals), with an explicit config override
(`review_authority: pkit-verdict | github-native`). Solo → pkit's comment verdict
is the authority; team → GitHub's native review state is the authority (pkit's own
review is pre-flight/advisory there).

**G2 · Staleness mechanism = hybrid (best source per kind).** Native reviews use
GitHub's recorded `commit_id`; comment verdicts **embed the HEAD SHA** (a tiny
machine token — GitHub gives a plain comment no commit binding, only a timestamp).

**G3 · Staleness strictness = strict + per-reviewer audited override.** Any new
commit invalidates all applicable approvals (matches GitHub's own dismiss-stale
behaviour; composes with one-review-per-round anchored to a commit). Override lets
you keep a *specific* reviewer's approval, with an audited reason, when a change is
genuinely irrelevant to them — a human makes that call on the record, not the
machine guessing per-area.

**G4 · Mixed reviewers = authority-wins.** The mode's authority gates; the
non-authority kind is advisory (surfaced, never blocks). No per-reviewer
promotions.

**G5 · Override / bypass = audited override of pkit's OWN verdict.** In
pkit-authority (solo), `--bypass "reason"` past a blocking pkit verdict, recorded as
audit. Overriding native branch protection stays GitHub's `--admin` (operator
escalation pkit surfaces but does not own).

**G6 · Reviewer applicability — mostly already built (DEC-032 +
`review-contributions.yaml`).** "Review" is the general discipline; each reviewer
has a domain + an applicability predicate, of two kinds:
- **`floor`** — a diff-property (today only `touches-code`).
- **`match`** — a classification (e.g. `type:*`).
- Required set = baseline ∪ every contributed reviewer whose predicate matches;
  deduped; fail-closed; the *same resolver* invokes and gate-checks.
- Shipped panel already implements the intended model: code + security ride
  `touches-code`; docs rides `touches-code` (the *code→docs* doc-update obligation:
  "a code PR always gets doc review") **and** `match: type:*` (docs-only classified).
- **NEW decision:** add a **`touches-docs` floor** and put docs-reviewer on it, so a
  docs change fires doc review *from the diff alone* — closes the named gap
  (unclassified docs-only PR currently gets no doc review).
- security-reviewer fires on **all** code (via `touches-code`) — confirmed.

---

## Part C — artifacts to produce (realization)

Three records (per the architect's tier analysis); acceptance gate applies before
any implementation cites them:

1. **pm DEC** — comment content + house-style model (amends DEC-049 audit content,
   DEC-041 footer-on-comments, DEC-047 frame, **DEC-028 verdict grammar + aggregate
   unit**). #757's named product; retire the design scratchpads as produced.
2. **project-kit ADR** — the seam contract: sole-constructor renderer; markers
   schema-owned with drift guards; footer delegated to provenance (constructed-vs-
   edited distinction); the **`parse(render(x)) == x`** round-trip invariant; a guard
   test proving nothing composes a pkit comment outside the seam; the pinned hoist
   trigger. 4th member of the seam family (ADR-026 / ADR-031 / ADR-037).
3. **software-engineering DEC amendment** — DEC-002 panel shape: three independent
   verdicts → one aggregate round; reviewers emit *findings/data*, not comment bytes.

Plus the **gate-model realization**, which touches DEC-028 / DEC-032 / DEC-050 and
the pm-owned `review-contributions` schema + resolver: authority-mode config (G1),
comment-verdict SHA embedding (G2), the `touches-docs` floor (G6).

**Not a COR** unless the A2 hoist trigger fires. **Ordering:** DEC first (what it
renders) → ADR (how it holds).

---

## Next steps

1. **Get user sign-off on A6** (the DEC-028 / ADR-042 supersession) — blocks
   implementation.
2. Author the **pm DEC** (decision-author) from this note + the architect draft.
3. Author the **project-kit ADR** (seam contract).
4. Author the **software-engineering DEC amendment**.
5. Slice implementation tasks under EPIC #756 (align all comment posters to the
   house style; the #690 audit-restyle folds in) + gate changes coordinated with
   #725. The `touches-docs` floor is a small, self-contained slice that could ship
   early to close the doc-review gap.

## Housekeeping

- `docs/architecture/decisions/DRAFT-render-seam-exploration.md` is untracked and
  sits in the ADR directory only because that is the architect agent's sole
  writable path (bug #771: a spawned agent's text doesn't return to the caller, so
  it delivered via a file). **Relocate its content into the scratchpad area (or
  retire it) once the ADR is authored** — it is not an ADR.

## References

- Issues: #757 (anchor) · #756 (EPIC) · #725 (code-review discipline) · #670
  (native review) · #690 (audit-comment feedback) · #771 (agent-dispatch delivery).
- Decisions: DEC-028 (verdict grammar) · DEC-032 (reviewer resolution /
  contributions) · DEC-050 (per-reviewer override) · DEC-002 (se code-review panel)
  · DEC-041 (provenance footer) · DEC-047 (freeform comment) · DEC-049 (audit /
  journal).
- ADRs: ADR-037 (provenance write-path) · ADR-042 (first-line gate selector) ·
  ADR-026 / ADR-031 (seam family) · ADR-003 (shared-lib hoist trigger) · ADR-006
  (view assembler) · ADR-011 (CLI styling / `strip_ansi` invariant).
- Design scratchpads (this branch): the `2026-08-*-pkit-comment-house-style` /
  `code-review-*` notes.
