---
id: DEC-052
title: Comment content model and house style — one model for every comment the capability posts
status: accepted
date: 2026-09-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> This record fixes one **content + house-style model** for every comment the capability
> *posts* on a GitHub issue or PR — such as filing, override/audit, move, and review
> verdict, which pkit **authors**, plus freeform notes and adopter hook messages, which it
> only **frames**
> and never rewrites. The load-bearing rule is the **boundary rule**: a comment earns its
> place only by carrying an *off-surface* fact — something GitHub's native surface does not
> already show — and never exists merely to restate the comment-author, the bare state
> transition, or the current version. Every posted comment wears one **frame** — a per-kind
> `<!-- pkit-<kind> -->` marker plus a universal `<sub>🧰 pkit · … </sub>` provenance footer
> — and authored payloads additionally follow the house style below. It fixes *what* each
> comment carries and *how it reads*; *how the string is composed* is a companion ADR
> (authored next).

## Context

Every GitHub comment the capability writes — filing, audit/override, move, review
verdict, and the pass-through of freeform notes and adopter hook messages — grew its
own ad-hoc shape. The maintainer feedback that prompted this was concrete: the audit
comment from the audit/journal model ([project-management:DEC-049-audit-journal-model])
restated `Bypassed by <actor>` (redundant with the comment-author *when pkit posts under
the actor's own identity*), read poorly, and didn't match the `🧰` filing line. Rather
than restyle one comment, the capability needs **one model for all of them** — what each
carries, and how it looks — so they read as one system and never duplicate what GitHub
already shows.

This record fixes the **content + style model**. It does **not** fix *how the string is
composed* — the renderer, its input contract, where it lives — which is a separate
architectural concern (see Implications).

## Decision

### The boundary rule (what a comment may carry)

A pkit-authored comment must **earn its place against GitHub's native surface** — it does
not exist merely to restate what GitHub already shows. For an *information-bearing*
comment (the kinds below) that means carrying an **off-surface fact** as its payload and
minimising restatement: on-surface facts appear only as necessary context. (A
*delivery-purpose* comment — e.g. a notification ping — is the narrow exception: its
value is the delivery, not the payload; it still wears the frame.) The recurring
on-surface facts a comment must not restate *as its point*:

- **the GitHub comment-author identity and post time** — shown on every comment (the
  author is the pkit tool/bot). This is *not* the **agent-within** identity: which `🤖`
  agent produced a finding is **off-surface** (GitHub does not show it), so per-actor
  identity is a legitimate payload — a forthcoming aggregate verdict carries several;
- **the bare state transition** — the issue timeline already shows label changes;
- **the current pkit version** — the provenance footer below already carries it (the
  *birth* version is a different, off-surface fact — see the filing kind).

### Two content categories

- **pkit-authored payload** — the capability composes the text (filing, audit/override,
  move, verdict). Governed by the house style below.
- **pass-through** — the text is the user's or the adopter's (freeform comments per
  [project-management:DEC-047-freeform-comment-verb]; hook messages). The capability
  **frames** it (the marker + footer below) but **never authors or restyles the
  payload** — the words stay the user's/adopter's.

### The house style

The **frame** — the trailing kind marker and the provenance footer — is on every comment
the capability **posts**, pass-through included. The **payload line** styling is for
pkit-*authored* payloads only; a pass-through comment carries the frame around the
user's untouched words.

- **Icon vocabulary — two tiers.** Two **semantic anchors are pinned in this record**
  because they carry meaning rather than decoration: `🧰`, the one "this is pkit" mark
  (in the footer, carried **once** per comment — the payload line does *not* repeat it),
  and `🤖`, an agent acting within pkit. Each authored **kind** additionally leads with its
  **own** distinguishing icon, and those per-kind glyphs are **decorative and schema-owned**
  (`comment-style.yaml`), tuned for human readability — not fixed here. The rule is the
  seam: this record pins the two universal semantic marks; the schema owns the per-kind
  decoration.
- **Payload line** (authored payloads only): `<kind-icon> <kind> — <payload>` — the
  kind label, **no `🧰 pkit` prefix** (the footer already marks it as pkit; repeating it
  is redundant). A **move** additionally names the transition it made,
  `<from> → <to>` (e.g. `backlog → in-progress`).
- **Kind marker:** a trailing `<!-- pkit-<kind> -->` HTML comment tags what the comment
  is, for the capability's own readers (the write-side counterpart to a read-side
  refusal). One marker per comment; each kind has its own.
- **Universal provenance footer:** every comment the capability posts ends with
  `<sub>🧰 pkit · tree <v> · pm <v> · cli <v></sub>` — the version-provenance stamp from
  [project-management:DEC-041-version-provenance-stamp], extended from bodies to comments.
  Its three axes are DEC-041's, in compact labels: `tree` = the **backbone version**, `pm`
  = the **capability version**, `cli` = the **installed-CLI version**. It stamps the
  *post's* provenance (not the content), so pass-through comments carry it too. It is the
  shared identity-and-version frame; it subsumes any per-kind version stamp. **On a comment
  the footer is a static, write-once stamp** — DEC-041's body footer is a *self-replacing*
  region that every body write strips and reissues, but a comment is posted once and never
  rewritten, so the comment footer records the versions in force at the post and does not
  re-render.

### The per-kind model: rules here, the roster is inventory

This record owns the durable **rules** every kind obeys (below). The *set* of kinds and
each kind's off-surface payload is **inventory** — it grows and shifts as the capability
gains verbs — so it is **destined for `comment-style.yaml`** (authored with the render
seam): once that schema exists, adding or changing a kind is a **schema entry governed by
the boundary rule**, not a rewrite of this record — the *principles-not-inventory* split.
Until then the current roster lives here (the table below); relocating it is an
implementation step, not a re-decision. The load-bearing **decisions** certain kinds carry
— filing's keep-not-drop, the override and move amendments to DEC-049, the verdict grammar
deferred to #795 — live in the Rationale and Implications below, **not** in the table, so
the table stays pure payload inventory that relocates without residue.

**Rules every kind obeys:**

- **Off-surface payload + frame.** Each authored kind carries an off-surface fact as its
  payload (the boundary rule) and wears the frame; the authored payload line is
  `<kind-icon> <kind> — <payload>`.
- **A transition names itself.** A **move** carries its transition `<from> → <to>` as
  context and its **intent** — trigger + causation (e.g. `cascade ← #613`) — as the
  off-surface core.
- **A reason-bearing transition puts its reason on its own line.** Some transitions carry a
  *rationale* rather than a mechanical trigger — a **won't-do close**, a **no-merge PR
  close**, a **reopen with a reason**. Their reason **drops to its own paragraph** (a clean
  sentence, or a short list; never crammed into the header line): a declined close reads
  `move · <from> → done — won't do` with the reason below, distinct from a completion close
  and from a mechanical close (a cascade or duplicate close carries only its trigger, via
  the intent rule above). The rationale is off-surface — GitHub shows *closed as not
  planned*, never *why* — so it is the comment's payload. Each such comment is written
  **once, by the mutator that performs the transition** (`close-issue`, `close-pr`,
  `reopen-issue`), preserving DEC-049's one-comment-per-mutation invariant.
- **Pass-through is framed, never restyled** (freeform, hook): the frame wraps the user's
  or adopter's untouched words; each pass-through kind keeps its own marker.

**The current roster** — pure `kind → payload` inventory, moving to `comment-style.yaml`
at implementation (the decisions these kinds carry live in the Rationale/Implications, not
here):

| Kind | Off-surface payload |
|---|---|
| filing | the **birth version** — the filed-under versions + date, frozen |
| override / audit | the **reason** a gate was overridden, plus the **authoriser** when the poster differs from them |
| move | the transition `<from> → <to>` + **intent** (trigger + causation); a **reason-bearing** move carries its reason as its own paragraph (the rule above) |
| verdict | the review **findings** + the machine gate signal |
| freeform · hook | pass-through — the user's / adopter's words, framed, never restyled (markers `pkit-freeform` / `pkit-hook`) |

**Composition — one mutation, one comment.** When a single mutation is both a move and an
override (a gated transition that required a bypass), it is **one** comment, honouring
DEC-049's one-audit-comment-per-mutation invariant: the move's intent carries the override
**reason** folded in (and the authoriser per the override rule), under a **single marker —
the primary kind's** (an audited move carries `pkit-move`; a standalone override,
`pkit-override`). There are never two comments — nor two markers — for one mutation.

Projection levels are owned by [project-management:DEC-049-audit-journal-model] (`off` /
`audit` / `full`); this record does **not** redefine which mutations a level covers. It
fixes the **content + frame** of each projected comment: at `audit`, the override-or-authorisation
reason (a bypass justification, or a won't-do rationale); at `full`, DEC-049's
every-governed-mutation set, each stamped with its off-surface payload (the intent-log for
a move, and so on). Narrowing `full` here would
let a governed mutation read as ungoverned under DEC-049's drift check — so coverage
stays DEC-049's.

## Rationale

A single model makes every pkit comment recognisable and consistent, and the boundary
rule is what earns each comment its place — a comment that only restates the author, the
timeline, or the version is noise the reader must wade through. Splitting payload from
pass-through keeps the house style honest: the capability styles what it authors and
never rewrites a human's words.

### Alternatives considered

- **Restyle each comment kind ad-hoc.** Rejected — it is how the drift that prompted this
  arose; there is no single place the model lives, so it re-drifts.
- **A per-kind inline version stamp.** Rejected — the universal footer already carries the
  version once; a second stamp is the redundancy the boundary rule forbids.
- **Drop the filing comment once the footer is universal.** Rejected — the footer carries
  only the *current-touch* version and, per
  [project-management:DEC-041-version-provenance-stamp], loses the birth version on the
  first edit under a newer version; reconstructing it from history is a lossy heuristic,
  not ground truth. The filing comment is the sole record of the birth version, so it
  stays — reframed, not dropped.

## Implications

- **Amends the audit/journal model** ([project-management:DEC-049-audit-journal-model]):
  the override comment drops the authoriser only when it equals the comment-author
  (keeping it on the bot-authored path, where it is off-surface); the move comment is
  reframed as the intent-log; an overridden move is one comment carrying both payloads
  (the composition rule above), preserving the one-comment-per-mutation invariant.
  DEC-049's **sole-writer** rule — named there as `move-issue` — is generalised to *the
  underlying mutator of each governed transition*: reason-bearing closures and reopens
  (`close-issue`, `close-pr`, `reopen-issue`) each write their own single comment, bringing
  those transitions into audit-content scope while keeping the no-double-post guarantee (one
  comment per mutation, written by the mutator, never a wrapper).
  DEC-049's uniform `<!-- pkit-audit -->` marker is refined to the **per-kind** marker model
  (an audited move carries `pkit-move`, a standalone override `pkit-override`), so an audited
  mutation is tagged by its kind rather than one generic audit marker.
  Projection-level *coverage* is unchanged (DEC-049's) — this record fixes only the
  *content* each level projects.
- **Amends the version-provenance stamp** ([project-management:DEC-041-version-provenance-stamp]):
  the footer is universal on **comments** the capability posts (pass-through included),
  not only bodies. On a comment it is a **static, write-once** stamp — a different object
  from DEC-041's *self-replacing* body region (whose strip-and-reissue seam is ADR-037's),
  so writing provenance onto comments is the companion render-seam ADR's concern, not
  ADR-037's body seam. The filing comment is **kept** — it remains the load-bearing
  birth-version record — and wears the house-style frame **prospectively**: new filing
  comments use it; existing immutable ones are not edited (no back-fill, per DEC-041). Its
  recorded content (the birth versions + date) is unchanged.
- **Amends the freeform-comment convention**
  ([project-management:DEC-047-freeform-comment-verb]): pass-through comments carry the
  frame (marker + footer) around the user's untouched payload.
- **The roster is inventory, destined for the schema.** The *set* of kinds and each kind's
  payload is inventory: it lives in the table above **today** and moves to
  `comment-style.yaml` when the render seam is implemented. From then on a new *roster
  entry* — a kind's marker + payload — is a **schema change governed by the boundary rule**,
  not a rewrite of this record, and the render-seam ADR's drift guard (ADR-054, once
  accepted) keeps the schema and the reading code in sync. A new *rule* — like the
  reason-bearing grammar this record adds — is still a decision here: the split is durable
  rules in the DEC, evolving roster in the schema.
- **Back-references land on acceptance.** The three records amended above
  ([project-management:DEC-049-audit-journal-model],
  [project-management:DEC-041-version-provenance-stamp],
  [project-management:DEC-047-freeform-comment-verb]) each gain an
  `> **Amended by [project-management:DEC-052]**` note when this DEC is accepted, per the
  bidirectional precedent DEC-050 set with DEC-032 / DEC-046.
- **Out of scope — the render seam.** *How* the string is composed — the renderer, its
  structured input contract (`format(data) → string`), where it lives, the
  `parse(render(x)) == x` round-trip guarantee, and **where comment provenance is written**
  (the static footer + immutable filing comment on comments, which ADR-037's body
  strip-and-reissue seam does not cover) — is a project-architectural concern captured in a
  separate ADR authored next (ordering: this DEC fixes *what* is rendered; the ADR fixes
  *how it holds*).
- **Out of scope — the aggregated review verdict grammar.** The one-review-per-round
  format and the merge-gate parser it reshapes are Feature #795's amendment to the
  agent-as-approver model ([project-management:DEC-028-agent-as-approver-paths]); this
  record fixes only the verdict comment's *content boundary + frame*, not the grammar.
- Realisation aligns every comment poster to the model through the shared renderer; the
  #690 audit-restyle folds in as the first consumer.
