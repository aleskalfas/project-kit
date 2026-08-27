---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-27
---

# Render seam — architect exploration (rationale companion)

> The `architect` agent's full exploration of the unified comment render seam,
> delivered via **file hand-off** because a spawned agent's text doesn't return to
> the caller in this harness (bug #771). Companion to
> `2026-08-27-render-seam-and-merge-gate-decisions.md` — that note is the
> *decisions*, this is the *reasoning*. Retire when the ADR is authored.
>
> Note: reflects the architect's *original* recommendation (a hidden machine
> block); the settled decision reads the human header instead (see the decisions
> note, A5) — the rest of the analysis stands.

## TL;DR — the recommended shape

1. **Build a typed renderer family over one shared frame assembler**, not a generic
   `render(kind, data)` and not template files. Callers pass presentation-free
   structured data (`AgentVerdict(agent, verdict, findings[])`); one `compose()`
   owns every byte — icons, headings, ordering, markers, footer.
2. **It lives in the project-management capability's `_lib/`**, not the backbone.
   There is exactly **one code consumer** today (pm's scripts). `software-engineering`
   consumes the *contract*, not the *function* — it ships no scripts at all
   (`scripts/` is a bare `.gitkeep`). Hoisting now trips the trigger ADR-003 already
   pinned for a shared `.pkit/lib/`.
3. **The house-style vocabulary is schema data, not code and not template files** —
   a new pm schema (`comment-style.yaml`) owning the icon vocabulary, verdict→emoji
   map, section labels, and *every machine-marker string*. Python constants bind to
   it with a drift-guard test, exactly the pattern issue #763 established for
   `integration_marker`.
4. **The renderer never writes footer bytes.** It calls provenance's
   `render_footer()`; `stamp()` (strip-then-append) stays the *body* path. Comments
   are composed once and never edited, so exactly-one holds by construction — a
   stronger guarantee than the body path's, and it avoids a real data-loss hazard.
5. **The load-bearing invariant is `parse(render(x)) == x`.** That round-trip test is
   the reason the seam earns its keep — it is the comment-surface analogue of the
   `strip_ansi(styled) == plain` invariant that ADR-011 pinned for CLI styling.

## Findings by severity

### Architectural concern — user authorisation required

**The aggregated one-review-per-round decision is not a rendering change. It changes
the unit the merge gate parses.** Today the model is *one comment = one reviewer's
verdict*, recognised by the comment's **first line** and keyed by
`(path, reviewer)`; that is the accepted agent-as-approver decision
(project-management:DEC-028) and the strict gate selector built on it
(ADR-042, realised in `_lib/agent_verdicts.py:gate_verdicts`). The settled house
style posts **one aggregate comment carrying N per-agent verdicts under one author
and one timestamp**. `latest_verdicts_per_reviewer` cannot express that: it reads one
token from line 1 and collapses per reviewer.

So this proposal *implicitly supersedes* part of DEC-028's decision. It should
supersede it *explicitly* — a DEC-028 amendment plus an ADR-042 companion — per the
supersession gesture in `.pkit/decisions/README.md`. **Blast radius is the merge
gate, which fails closed**: a renderer/parser mismatch does not produce ugly
comments, it produces PRs that cannot merge. This is the item needing the user's
explicit go-ahead before any implementation.

Second, coupled half of the same concern: the freeform-comment spoof guard
(`_lib/comment.py:structured_comment_reason`, per DEC-047) refuses any comment whose
first line matches the verdict grammar. **Any change to that grammar must land in the
same change-set as the guard**, or `pkit pm comment-pr` becomes a way to forge a
verdict the gate counts. Two consumers of one grammar; both must read it from the
same source.

### Fit issue

- **`src/project_kit/` is not a candidate home** and the brief's "BACKBONE" option
  should be read narrowly. Capability scripts are PEP 723 self-contained and run
  in-tree, where the global `pkit` runtime is not importable — the exact constraint
  that forced the permission decision core out of `src/` and into propagated neutral
  code (ADR-003). "Backbone" here can only mean *a new propagated neutral code home
  under `.pkit/`*, which is ADR-003's category and governed by its pinned revisit
  trigger.
- **`review-pr.py` currently lets the reviewer agent own the comment bytes below
  line 1** (`_format_verdict_comment(name, verdict, body)` splices the agent's raw
  stdout in). A house style the agent is free to ignore is not a house style. Fixing
  this means changing the *agent output contract* — the upstream half of the seam,
  which the design must answer or the renderer's input contract is fiction.
- **Marker strings are Python literals in three unrelated modules today**
  (`agent_verdicts.VERDICT_MARKER`, `comment.FREEFORM_MARKER`,
  `move-issue._AUDIT_MARKER`). Only provenance's sentinels are schema-bound. Fit
  issue against schemas-as-the-engine-data-layer (COR-018).

### Doc drift

- Making the provenance footer universal on **every comment** is a surface change to
  the version-provenance decision (DEC-041), whose scope today is *bodies plus a
  one-time filing comment*. Dropping the filing comment likewise amends DEC-041 and
  needs a check for readers of `<!-- pkit-provenance:filing -->`.
- ADR-037's guard test currently scans body writes (`gh issue edit --body-file` and
  kin). Extending the footer to comments extends the guard to `gh <subject> comment
  --body`, or the "sole constructor" claim quietly stops being true for the new
  surface.
- The audit-comment template lives in `validation-severity.yaml`
  (`severities.bypassable-with-audit.audit_comment_template`, per DEC-049). If a
  comment-style schema becomes the format home, that entry either moves or becomes a
  pointer — leaving both is two sources of truth for one string.

### Worth recording

- The seam contract belongs in an ADR joining the existing seam family — the label
  read-path contract (ADR-026), the substrate write-path contract (ADR-031), the
  provenance write-path contract (ADR-037). Same construction-point-plus-guard shape,
  one new boundary.
- The content model and house style belong in a pm DEC, which the house-style
  scratchpad note already nominates as its retirement product.

### No concerns

Boundary placement of the *renderer itself* inside pm is clean. Comment rendering is
a project-management concern (it renders lifecycle-issue and PR comments, which is pm's
territory), and every current write path already lives there.

---

## The unifying principle

The provenance write-path contract (ADR-037) is built on one sentence: *the agent
never owns the footer bytes.* A script owns a region inside a document an agent
rewrites, so the write path strips whatever the agent did and reissues the region.

This proposal is that principle one altitude up: **the agent never owns the comment
bytes.** A reviewer agent emits *findings*; the kit composes the comment. An adopter
hook emits *a message*; the kit frames it. That single rule is what makes a house
style enforceable rather than aspirational, and it is the honest justification for
the seam existing at all.

It also resolves the presentation/data split without further argument: if the agent
never owns the bytes, the agent must hand over *data*, and the renderer must own
*everything else*.

## Design-space map

Five independent axes. They are genuinely independent — you can pick any point on
each — which is why the design reads as tangled until they are separated.

| Axis | Options | Notes |
|---|---|---|
| **A. Abstraction** | generic `render(kind, data)` · typed renderer family · pure template expansion | Determines where a missing field fails: at the call site, at render, or silently in the output. |
| **B. Home** | pm `_lib/` · new propagated neutral code home under `.pkit/` · `src/project_kit/` | Third option excluded by the in-tree import constraint (ADR-003's reasoning). |
| **C. Style source** | inline Python strings · template files · schema entries | Determines whether a house-style tweak is a code edit, a designer edit, or a data edit. |
| **D. Footer** | renderer owns bytes · renderer delegates to provenance | Determines whether ADR-037's sole-constructor claim survives. |
| **E. Machine record** | human header *is* the grammar · separate embedded machine block · both posted separately | The one with merge-gate blast radius. |

The recommendation is **A: typed family · B: pm `_lib/` · C: schema · D: delegate ·
E: embedded machine block**, argued below.

---

## 1 · The abstraction and the structured-input contract

### The three candidate shapes

**Shape 1 — one generic `render(kind, data)`.** A `kind` string selects a template;
`data` is a dict.

- *For:* one entry point; new kinds are pure data; trivially serialisable.
- *Against:* `data` is untyped, so a renamed or missing field yields a silently
  truncated comment rather than an error. On a merge-gate surface, a silently
  missing `blocking` list is a reviewer's objection quietly disappearing. Mitigable
  with schema-declared required fields validated at render time — which is most of
  a type system, hand-rolled.

**Shape 2 — a typed renderer family over one frame assembler** *(recommended)*.

```
render_review(round: ReviewRound) -> str
render_gate(summary: GateSummary) -> str
render_override(o: Override) -> str
render_move(m: MoveIntent) -> str
frame(kind, header, blocks, marker) -> str      # the single byte-owner
```

Every public renderer builds semantic parts and hands them to one `frame()` that
owns heading levels, icon placement, blank-line rhythm, marker position, and the
footer call. This is the shape ADR-006 chose for CLI read-views ("string/tuple
helpers carrying semantic data feed a single `view(...)` assembler that owns *all*
layout decisions"), transposed to forge markdown.

- *For:* per-kind contracts are explicit at the call site (a missing field is a
  `TypeError`, not a blank section); the frame is the single place a cross-cutting
  invariant is enforced; each kind's data shape is independently testable; the
  A′→typed promotion path ADR-006 documented is already trodden ground here.
- *Against:* adding a *kind* is a code edit. Acceptable — kinds are rare (five in the
  whole content model) and each one genuinely has a different shape. Adding a
  *finding*, changing an *icon*, relabelling a *section* stays a data edit, which is
  the change that actually recurs.

**Shape 3 — pure template-file expansion.** `templates/comments/review.md` with a
substitution syntax; the renderer only fills slots.

- *For:* house style evolves with zero code edits; a non-programmer can iterate.
- *Against, and this is decisive:* the house style has **conditionals** — omit an
  empty `*Advisory:*` group, collapse an APPROVED-with-no-findings block to its
  headline, pluralise counts, suppress a group per projection level. Templates
  expressing conditionals need a template language (a new dependency, or a
  hand-rolled one), and logic migrates into templates where it is untestable. Worse:
  **it makes machine markers a template author's responsibility**, which is precisely
  the ownership ADR-037 spent a whole record removing. A template author who reflows
  a file can silently break the merge gate.

### The structured-input contract

Presentation-free by construction — no emoji, no markdown tokens, no `⛔️`, no
`` ` `` at any call site:

```python
Severity   = Literal["blocking", "advisory"]
Verdict    = Literal["APPROVED", "CHANGES_REQUESTED"]

@dataclass(frozen=True)
class Finding:
    text: str                 # one sentence, no leading bullet
    severity: Severity
    file: str | None = None   # renderer formats `file:line`, caller never does
    line: int | None = None

@dataclass(frozen=True)
class AgentVerdict:
    agent: str                # bare name; renderer adds 🤖 and the code fence
    verdict: Verdict
    findings: tuple[Finding, ...] = ()
    note: str | None = None   # the round-3 "prior block resolved" prose

@dataclass(frozen=True)
class ReviewRound:
    pr: int
    head_sha: str
    verdicts: tuple[AgentVerdict, ...]
    # aggregate verdict + the `code ✓ · security ✗` roll-up are DERIVED here,
    # never passed in — one place computes them, so header and body cannot disagree.
```

Three rules that make the decoupling real and testable:

- **Derive, never accept, anything computable.** The aggregate verdict is
  `CHANGES_REQUESTED if any(...)`. Accepting it as a parameter is how a header comes
  to claim ✅ over a body full of ⛔️.
- **Versions are not a caller concern.** The frame resolves them via
  `provenance.read_versions(capability_root)`.
- **Guard the decoupling with a grep test:** no emoji codepoint and no markdown
  control token appears in any call site outside the renderer module and its schema.
  Cheap, and it is the enforcement half of ADR-011's "authors tag meaning, the
  renderer owns the bytes."

---

## 2 · Where it lives

**Recommendation: `.pkit/capabilities/project-management/scripts/_lib/comment_render.py`.**

### Why not the backbone

Two different things are called "backbone" and they fail for different reasons.

`src/project_kit/` is **excluded by the same argument ADR-003 used** for the
permission decision core: capability scripts are self-contained per PEP 723 and run
in the adopter's tree, where the global `pkit` runtime is not importable. The
provenance module already documents living with this — it re-parses YAML with its own
loader rather than importing `project_kit.manifest`. A renderer in `src/` would be
unreachable from the very scripts that need it.

A **new propagated neutral code home** under `.pkit/` (the category ADR-003 created,
which today has exactly one member) is architecturally *possible* — but ADR-003 also
pinned the trigger for growing it: *"Revisit and extract a shared `.pkit/lib/` only if
a second, unrelated neutral propagated library appears — the recurrence test, not the
first instance, earns the abstraction."* Creating one now for a single code consumer
is the speculative generality that record already rejected once.

### On "software-engineering is a live second consumer"

This needs a precise correction, because the whole placement question turns on it.
The `software-engineering` capability ships **no scripts** — `scripts/` contains only
`.gitkeep`. Its reviewer agents are markdown prompts; `review-pr.py` (pm) invokes
them, parses their stdout, and posts. So:

- **Second consumer of the *contract*** — yes, unambiguously. Its three agent files
  each hardcode the verdict grammar and the `<!-- pkit-verdict -->` marker in prose.
- **Second consumer of the *renderer function*** — no. Not one line of
  `software-engineering` code would import it.

That distinction has a clean architectural answer, and it is the same move ADR-003
made for recognizers: **harness- and capability-shaped knowledge crosses the boundary
as *data*, never as a code import.** Share the *contract* as a schema every capability
may read (declared via the reference graph's `reads.paths`, per COR-013/COR-018);
keep the *renderer* as pm code with one consumer. `software-engineering` already
declares a versioned dependency on pm (`requires_capabilities: project-management
>=0.54.0,<1.0.0`), which is the right coupling for a data contract and the wrong one
to lean on for a code import across a capability boundary.

### The pinned hoist trigger

> When a **second capability ships a script that renders a pkit comment**, hoist
> `comment_render` to a propagated neutral code home and revisit ADR-003's
> `.pkit/lib/` question at the same time. Until then it stays pm-owned.

Writing the trigger down is what makes this a decision rather than a deferral.

### No-shared-files check (COR-001)

Clean. The module and the schema are kit-owned propagated files; adopters never edit
them. Adopter customisation of the house style, if ever wanted, is an *extension*
concern (a `project/`-side override) and should be treated as out of scope for v1 —
a per-adopter house style would undermine the one property the seam exists to buy.

---

## 3 · The template mechanism

**Recommendation: schema-owned vocabulary + code-owned assembly. No template files.**

Split the style surface in two by *change cadence*, which is the split COR-018 draws
between decisions, schemas, and engine code:

| What | Home | Changes when |
|---|---|---|
| Icon vocabulary (`🧰` = tool, `🤖` = agent), verdict→emoji map (`CHANGES_REQUESTED`→`⛔️`), section labels (`*Blocking:*`), heading levels, roll-up glyphs (`✓ ✗ ⤼`), **every marker string**, projection levels | `schemas/comment-style.yaml` (+ `.schema.json`) | The house style evolves |
| Assembly, conditionals, derivation, ordering | `_lib/comment_render.py` | A kind is added or its structure changes |

A new schema file, not an extension of `body-format.yaml`: that schema is explicitly
about *bodies* (required sections, checkbox rules, the parent-ref, the provenance
region's read-side contract). Comments are a different artifact with a different
validation story. One entry needs to be **shared and cross-referenced**, not
duplicated — the provenance marker pair, which `body-format.yaml` already owns; the
comment-style schema points at it rather than restating it, and a drift-guard test
asserts they agree (the #763 pattern, which exists precisely because two schemas
restating one marker slug drifted).

**Where the audit template goes.** `validation-severity.yaml`'s
`audit_comment_template` is today's only schema-owned comment format. Under a unified
seam it becomes the odd one out: a raw string with `<name>`/`<reason>` placeholders,
substituted by `str.replace` in `move-issue.py`, alongside a hardcoded Python
fallback that must be kept byte-identical by hand. Recommendation: **the override
comment becomes a renderer kind**, and the severity schema's entry is either removed
in favour of the style schema, or reduced to a cross-reference. Leaving both is two
sources of truth for one comment; the DEC-049 work already fought that exact battle
once.

**Why not template files, restated in one line:** conditionals need a language, and
markers must not be an author-editable byte.

---

## 4 · Footer composition

**Recommendation: the renderer delegates the footer bytes to provenance, and
comments use a different exactly-one mechanism than bodies do.**

The insight worth pinning: **bodies are edited; comments are constructed.**

- A **body** round-trips — fetched, handed to an agent, written back. The incoming
  text may already carry a footer in any state (clean, doubled, mangled). Hence
  strip-then-append-exactly-one, and hence ADR-037.
- A **comment** is composed once from structured data and never edited by the kit.
  There is no incoming state. So exactly-one holds *by construction* — the frame
  appends one footer to a string it just built.

That is a **stronger** guarantee than the body path's, and it should be stated that
way rather than reusing `stamp()` reflexively.

Concretely: `provenance.render_footer(versions)` stays the sole source of the footer
bytes and the frame calls it; `provenance.stamp()` remains the body-write seam. Add a
guard test asserting the `<sub>🧰 pkit …` byte sequence is constructed nowhere except
`render_footer` — extending ADR-037's construction-test-plus-guard shape to the
comment surface.

### A real hazard: do not run `stamp()` over user content

`strip_footer` cuts **from the first sentinel through end-of-document**. On a
kit-owned body that is exactly right. On a **pass-through comment carrying a user's
words** it is data loss: a user who pastes an issue body into a `comment-pr` note —
entirely plausible, since the kit stamps every body with that footer — would have
everything after the pasted sentinel silently deleted.

Recommendation: for pass-through kinds (freeform, hook), **append without stripping**.
The worst case is a cosmetically doubled footer in a comment that quoted one; the
alternative worst case is destroying a user's text. Flagged as an open question
because it is a judgement call about which failure the project prefers.

### Surface-change accounting

Footer-on-every-comment is adopter-observable on every pkit-posted comment →
amends DEC-041 (whose scope is bodies plus the filing comment), needs a changeset
declaring the surface impact per PRJ-002, and needs a check for readers of the
`<!-- pkit-provenance:filing -->` marker before the filing comment is dropped. Not a
COR-010 migration trigger on its own — no rename, no `schema_version` bump, no
breaking CLI signature.

---

## 5 · Machine markers and the human/machine coexistence

This is where the design either holds or quietly breaks the merge gate.

### What is parsed off comments today

| Marker / grammar | Read by | Failure mode if broken |
|---|---|---|
| First-line verdict grammar + `<!-- pkit-verdict -->` | `gate_verdicts` (merge gate), `show-pr --field review` | **Merge blocked** (fail-closed) |
| Same grammar, read defensively | `structured_comment_reason` (DEC-047 spoof guard) | **Forgeable verdict** (fail-open) |
| `<!-- pkit-provenance:start/end -->` | `strip_footer`, body validators | Footer mis-scanned as body content |
| `<!-- pkit-audit -->` | audit filtering, `pm history` | Audit trail unfilterable |
| `<!-- pkit-freeform -->`, `<!-- pkit-hook: <id> -->` | comment classification, hook idempotency | Misclassification; duplicate hook posts |

### The aggregate problem

The house style's aggregate review is one comment with N per-agent blocks:

```
## 🧰 pkit review — ⛔️ CHANGES_REQUESTED · code ✗ · security ✗ · docs ✗
### 🤖 `code-reviewer` → ⛔️ CHANGES_REQUESTED
...
```

Line 1 is now a *roll-up*, not a reviewer's verdict; there is no per-reviewer author
or timestamp to key on. Three ways out:

**(i) Embedded machine block** *(recommended)*. The comment carries a
marker-delimited, structured payload the gate parses:

```
<!-- pkit-verdict:data
round: {pr: 758, head: a1b2c3d}
verdicts:
  - {agent: code-reviewer, verdict: CHANGES_REQUESTED}
  - {agent: security-reviewer, verdict: CHANGES_REQUESTED}
-->
```

- *For:* the human render is free to evolve without touching a parser; the gate reads
  a format designed for machines; per-agent verdicts, the HEAD anchor, and the
  timestamp are all first-class; invisible in rendered markdown.
- *Against:* the same string carries two representations, so they could disagree.
- *Mitigation, and this is the whole argument for the unified seam:* both are emitted
  by one function from one input, and a **round-trip test asserts
  `parse(render(x)) == x`**. Divergence becomes structurally impossible rather than
  reviewed-for. This is the direct analogue of ADR-011's `strip_ansi(styled) ==
  plain` invariant — one representation is derived from the other and a test pins it.

**(ii) Human header *is* the grammar** (what the surface-template note currently
proposes: "the house-styled header line **is** the gate-parsed verdict line").

- *For:* one representation, so nothing can diverge; least new machinery.
- *Against:* every house-style tweak becomes a lockstep parser change whose failure
  mode is blocked merges — on a style that the notes themselves describe as still
  settling. And it re-couples presentation to the gate at exactly the moment the
  project decided presentation should be free to move. Also fragile in the specific
  way ADR-037 documented: an LLM-adjacent surface reflowing a heading breaks a
  regex over emoji and backticks.

**(iii) Post both** — aggregate for humans, per-reviewer verdict comments for the
machine. Rejected by the settled house style (one review per round) and it
reintroduces the exact comment-noise the model was cleaning up.

### Supporting rules, regardless of which option wins

- **Marker strings move into the schema**, and each Python constant gets a
  byte-identity drift-guard test against its schema entry — the #763 pattern, which
  already exists in `tests/test_pm_integration_marker.py` as a worked example.
- **The gate parser and the DEC-047 spoof guard read the same schema entry.** Two
  consumers, one source, one COR-007-shaped extraction.
- **Grammar compatibility window.** Adopters have open PRs carrying old-grammar
  verdicts. A parser that only understands the new grammar stops counting them, and
  GitHub comments cannot be migrated. Recommendation: the parser accepts **both**
  grammars for one minor cycle, with the old path removed on a named release. This is
  a genuine adopter-breaking surface change even though it trips none of COR-010's
  syntactic triggers (no rename, no `schema_version` bump, no CLI signature change) —
  worth surfacing to the user explicitly rather than letting the check-diff tool's
  silence imply safety.
- **The agent output contract is the upstream half.** If agents must emit findings
  rather than prose, `review-pr._invoke_agent` needs a structured parse. Reuse the
  hard-won lesson already recorded in that function: **scan for the block anywhere in
  stdout, not at a fixed position** — the line-1-only parse "failed intermittently and
  posted no verdict, stalling the merge." Fail-closed on an unparseable block (no
  verdict → gate stays blocked), matching today's posture. Note the happy
  side-effect: once the agent emits data, its prompt no longer needs to carry marker
  bytes at all, which *removes* the cross-capability lockstep coupling that currently
  hardcodes the grammar in three `software-engineering` agent files and their deployed
  copies.

---

## 6 · The generalization boundary

**Recommendation: the seam's medium is *forge markdown that a machine also parses*.
That is the boundary — not "comments", and not "all human-facing output".**

| Surface | In? | Why |
|---|---|---|
| Verdict / audit / override / gate-summary comments | **Yes** | The core case. |
| Native GitHub review bodies | **Yes** | Same rendered payload, different transport — `review-pr` already passes the identical string to both. |
| Inline diff comments (`🧰 agent — finding`) | **Yes** | Same medium, same vocabulary, a cheap extra kind. |
| Freeform + hook pass-through | **Frame only** | The payload is the user's or adopter's; only markers and footer are the kit's. |
| Issue / PR **bodies** | **No** | Governed by `templates/` for shape and ADR-037 for the footer. Bodies round-trip through an agent; comments do not. Different invariant, different owner. Shared: the footer bytes, already factored. |
| CLI human output | **No** | Different medium (terminal, ANSI, no markers, no parser) with its own accepted renderer (ADR-006) and styling layer (ADR-011). |
| Hook engine internals, engine journal, `pm history` | **No** | Machine records, not human comments. |
| The `report` feature's `pkit-report` markers | **No** | Explicitly set aside as a separate surface by the house-style note. |

**Over-generalization risk, named.** The tempting move is "one renderer for all pkit
output". It fails on first contact: the CLI renderer's invariant is *structure must
read with zero styling*; the comment renderer's is *the machine record must survive
any style change*. An abstraction spanning ANSI-vs-markdown-vs-HTML-markers would
have almost no shared behaviour left — it would be a `str` with extra steps. Two
renderers, one *conceptual* discipline (semantic input, renderer owns bytes,
invariant pinned by test), zero shared code. That the disciplines rhyme is a sign the
principle is right, not that the modules should merge.

**Under-generalization risk, also named.** Shipping this for verdicts only, then
retrofitting audit and gate comments later, reproduces today's scattered surface with
newer strings. If the seam ships, all five pkit-authored kinds converge on it in the
same arc — that convergence is what the ADR-026/ADR-031/ADR-037 family calls the
construction surface, and a partial convergence is a guard test that cannot be
written.

---

## 7 · Artifact tier

Three artifacts, three jobs — the split ADR-037 and DEC-041 already model:

1. **pm DEC — the content and style model.** What each comment kind carries, the
   boundary test (a pkit comment carries only off-surface facts), the icon
   vocabulary's rationale, projection levels. Amends DEC-049 (audit content and
   levels), DEC-041 (footer universal on comments; filing comment dropped), DEC-047
   (frame convention), and **DEC-028 (the verdict grammar and the aggregate unit)**.
   The house-style scratchpad note already names this as its retirement product.
2. **project-kit ADR — the seam contract.** One sole-constructor renderer; markers
   schema-owned with drift guards; footer delegated to provenance with the
   constructed-vs-edited distinction; the `parse(render(x)) == x` round-trip
   invariant; the guard test proving nothing composes a pkit comment outside the
   seam; the pinned hoist trigger. Fourth member of the seam family, cited alongside
   ADR-026 / ADR-031 / ADR-037. Concrete paths are in scope here per PRJ-005.
3. **A `software-engineering` DEC amendment** — DEC-002's panel shape shifts from
   three independent verdicts to one aggregate round, and its reviewer agents stop
   emitting comment bytes.

**Not a COR.** Nothing here is universally applicable to every adopting project yet —
it is one capability's comment surface. A COR becomes the right carrier only if the
hoist trigger in section 2 fires and the renderer becomes backbone-shared.

**Ordering.** The DEC is the load-bearing one and should settle first: the ADR pins
*how the seam holds*, which is only answerable once *what it renders* is fixed. Both
need acceptance before implementation cites them — the acceptance gate applies
(`.pkit/decisions/README.md`).

### Escalation flag

**Authorisation is needed from the architectural perspective before implementation
begins**, on one item: *the aggregate review supersedes DEC-028's one-comment-one-
verdict model and ADR-042's first-line selector, on a fail-closed merge gate.* The
supersession must be explicit (a DEC-028 amendment and an ADR-042 companion), not a
side-effect of a rendering change. Everything else in this exploration is additive,
recoverable, or advisory.

---

## Cross-cutting risks

1. **Merge-gate blast radius.** The gate fails closed; a renderer/parser drift means
   nobody can merge. Mitigations: the round-trip test, schema-owned grammar, and a
   dual-grammar compatibility window.
2. **Spoof-guard coupling.** `structured_comment_reason` must move in lockstep with
   the grammar, or the freeform verb becomes a forge-a-verdict vector. Fail-open
   direction — worse than the fail-closed risk above, because it is silent.
3. **Data loss on user content.** `strip_footer`'s cut-to-EOF is correct for
   kit-owned bodies and destructive for pass-through user text. Do not reuse
   `stamp()` on comments carrying a user's words.
4. **Two sources of truth for one string.** The audit template, the marker constants,
   and the provenance sentinels each currently exist in more than one place with a
   hand-maintained fallback. Every one of them needs a drift guard or a single home.
5. **Capability-boundary erosion.** If `software-engineering` ever imports pm's
   `_lib` directly, the version pin in `requires_capabilities` becomes load-bearing
   for a Python import — a much tighter coupling than a data contract, and one that
   breaks the moment an adopter installs the capabilities at skewed versions.
   Contract-as-data avoids this entirely.
6. **Over-generalization into CLI output** (section 6) and **partial convergence**
   (also section 6) — the two failure modes at either end of the scope dial.
7. **Agent-output reliability.** The renderer's input contract is only as good as the
   agents' ability to emit it. An LLM emitting structured YAML is more fragile than
   an LLM emitting one fixed line; budget for the fail-closed path and the
   scan-anywhere parse.

---

## Open questions for the user

Ordered by decision weight. Worth taking **one at a time** — several are independent
and stacking them makes the conversation harder than it needs to be.

1. **Machine record for the aggregate: embedded data block (i) or human-header-as-
   grammar (ii)?** Everything else in the design is downstream of this. Recommendation:
   (i), on the fail-closed blast-radius argument.
2. **Footer on pass-through user comments: strip the payload or append only?**
   Recommendation: append only — a doubled footer beats deleting a user's text.
3. **Grammar compatibility window** — dual-grammar for one minor cycle, or a hard
   cutover with a release note? Recommendation: dual, since GitHub comments cannot
   be migrated.
4. **Scope of the first arc** — all five pkit-authored kinds converge at once, or
   verdicts first? Recommendation: all five; a partial convergence cannot carry a
   guard test.
5. **Style vocabulary home** — a new `comment-style.yaml`, or grow `body-format.yaml`?
   Recommendation: new file; `body-format` is about bodies, and comments are a
   different artifact.
6. **Confirm the pinned hoist trigger's wording** (section 2), so the deferral is a
   decision with a named condition rather than an open question that resurfaces.
7. **Adopter-overridable house style — in or out for v1?** Recommendation: out.
   Per-adopter styling would undermine the one property the seam exists to buy.

---

*Prepared by the `architect` agent, advisory per COR-024. No ADR or DEC was authored —
this is exploration, and the acceptance gate applies to anything built on it.*
