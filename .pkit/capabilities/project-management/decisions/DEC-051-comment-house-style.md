---
id: DEC-051
title: Comment content model and house style — one model for every pkit-authored comment
status: proposed
date: 2026-09-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

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

- **Icon vocabulary (schema-owned):** the footer's `🧰` is the one "this is pkit" mark,
  carried **once** per comment — the payload line does *not* repeat it. `🤖` denotes an
  agent acting within pkit. Each authored **kind** additionally leads with its **own**
  distinguishing icon. The concrete glyph per kind is a schema-owned token
  (`comment-style.yaml`), tuned for human readability — not fixed in this record.
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
  It stamps the *post's* provenance (not the content), so pass-through comments carry it
  too. It is the shared identity-and-version frame; it subsumes any per-kind version
  stamp.

### The per-kind content model

Each kind's off-surface payload:

| Kind | Comment? | Off-surface payload |
|---|---|---|
| provenance | footer (not a standalone comment) | the item's current pkit version |
| filing | yes (at creation) | the **birth version** (filed-under versions + date), frozen — the load-bearing before/after-upgrade record per [project-management:DEC-041-version-provenance-stamp]; wears the frame, **not** dropped (the footer carries only the *current* version and loses the birth version on the first edit) |
| override / audit | yes (projection ≥ `audit`) | the **reason** a gate was overridden, plus the **authoriser** when the comment is posted under a different identity than them (the bot-authored path), where the authoriser is off-surface; the authoriser is dropped only when it *equals* the comment-author (self-posted, where it is redundant) |
| move | yes (projection `full`) | the transition `<from> → <to>` as context + the **intent** as the off-surface core — trigger + **causation** (e.g. `cascade ← #613`); a compact gate-result roll-up may also ride as context, not as the comment's point |
| verdict | yes | the review **findings** + the machine gate signal — the same payload whether delivered as a comment or a native-review body (the transport is [project-management:DEC-028-agent-as-approver-paths]'s / #672's concern, not this record's) |
| freeform · hook | yes | the user's / adopter's words — pass-through (framed, payload never restyled). Two distinct kinds, each with its own marker (`pkit-freeform`, `pkit-hook`) |

**Composition — one mutation, one comment.** When a single mutation is both a move and an
override (a gated transition that required a bypass), it is **one** comment, honouring
DEC-049's one-audit-comment-per-mutation invariant: the move's intent carries the override
**reason** folded in (and the authoriser per the override rule), under a single marker.
There are never two comments — nor two markers — for one mutation.

Projection levels are owned by [project-management:DEC-049-audit-journal-model] (`off` /
`audit` / `full`); this record does **not** redefine which mutations a level covers. It
fixes the **content + frame** of each projected comment: at `audit`, the override's
reason; at `full`, DEC-049's every-governed-mutation set, each stamped with its
off-surface payload (the intent-log for a move, and so on). Narrowing `full` here would
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
  Projection-level *coverage* is unchanged (DEC-049's) — this record fixes only the
  *content* each level projects.
- **Amends the version-provenance stamp** ([project-management:DEC-041-version-provenance-stamp]):
  the footer is universal on **comments** the capability posts (pass-through included),
  not only bodies. The filing comment is **kept** — it remains the load-bearing
  birth-version record — and wears the house-style frame **prospectively**: new filing
  comments use it; existing immutable ones are not edited (no back-fill, per DEC-041). Its
  recorded content (the birth versions + date) is unchanged.
- **Amends the freeform-comment convention**
  ([project-management:DEC-047-freeform-comment-verb]): pass-through comments carry the
  frame (marker + footer) around the user's untouched payload.
- **Out of scope — the render seam.** *How* the string is composed — the renderer, its
  structured input contract (`format(data) → string`), where it lives, and the
  `parse(render(x)) == x` round-trip guarantee — is a project-architectural concern
  captured in a separate ADR authored next (ordering: this DEC fixes *what* is rendered;
  the ADR fixes *how it holds*).
- **Out of scope — the aggregated review verdict grammar.** The one-review-per-round
  format and the merge-gate parser it reshapes are Feature #795's amendment to the
  agent-as-approver model ([project-management:DEC-028-agent-as-approver-paths]); this
  record fixes only the verdict comment's *content boundary + frame*, not the grammar.
- Realisation aligns every comment poster to the model through the shared renderer; the
  #690 audit-restyle folds in as the first consumer.
