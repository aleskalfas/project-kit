---
id: DEC-044
title: One shared audit-log facility — machine stamp plus overridable rendered presentation
status: accepted
date: 2026-07-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability posts audit comments today from several places in
several ad-hoc one-line formats — `Promoted Todo → Backlog …`, `Bypassed by …`,
`Handoff: @from → @to …`. This record replaces those scattered strings with **one
shared audit-log facility**: every audit/event comment is built the same way, from a
structured record, and each comment carries **two layers** — a fixed, hidden,
versioned **machine stamp** (what tooling and idempotence read) and a **rendered
human presentation** (what a person reads, deliberately kept readable and
adopter-overridable). The instance-ownership event log
([project-management:DEC-043-ownership-substrate-selection]) is this same facility
specialised with ownership event types; it does not get a parallel mechanism.

## Context

Audit comments are load-bearing across the capability: the Todo → Backlog promotion
records its verbal authorisation ([project-management:DEC-026-work-ownership-lifecycle]),
a `--bypass` override records its reason
([project-management:DEC-014-validation-severity-model]'s `bypassable-with-audit`
template), a handoff records who passed work to whom (DEC-026), and — newly —
instance-ownership claim / handoff / abandon / release events form an append-only log
([project-management:DEC-043-ownership-substrate-selection] D3). Every one of these is
"post a parseable, idempotent comment recording who did what, when, and why."

Today each is a hand-rolled string with its own shape, and the idempotence
(re-running a command must not double-post) is re-implemented per site against
[project-management:DEC-024-lifecycle-hooks]'s template-stamp discipline. Two costs
follow. First, the recurrence is unfactored — the same shape is built N times, so a
new event type (ownership) is tempted to invent an N+1th format rather than reuse a
carrier ([pkit:COR-007]'s pattern-extraction trigger, now met by the ownership event
log as an independent second-plus consumer). Second, the strings are **austere and
doing double duty** — a single line serves both as a machine signal (the `<verb>:`
prefix DEC-026 notes "future tooling may parse") and as the human message, so it can
be neither cleanly parseable nor genuinely readable.

The methodology must also stay **project-neutral** ([pkit:COR-014]): the kit cannot
impose one house aesthetic (emoji, callouts, tone) on every adopter. So the *format*
question and the *record* question have to be separated — the record structure is
the methodology's; the presentation is the adopter's to restyle.

## Decision

**Ship one shared audit-log facility that every audit/event comment flows through.**
It separates a fixed machine layer from an overridable presentation layer, and the
existing audit strings plus the new ownership event log are all expressed through it.

**1. A structured audit record is the input.** Every audit event is a record with a
fixed field vocabulary: `event` type (e.g. `promote`, `bypass`, `handoff`, `claim`,
`abandon`, `release`), `actor` (login + display name; email where the source has it),
`timestamp`, the affected subject, an event-specific structured `payload` (e.g.
`from`/`to` for a handoff, `instance` for a claim, `gate` for a bypass), and a
free-text `reason` where the event carries one. Call sites construct the record;
they never format the comment themselves.

**2. Each posted comment carries two layers.**
- A **hidden, versioned machine stamp** — a single HTML-comment line encoding the
  record's structured fields (`<!-- pkit:audit v=1 event=… … -->`). It is **fixed
  and stable**: tooling parses it, and the [project-management:DEC-024-lifecycle-hooks]
  template-stamp idempotence check dedups on it (re-running a command finds the
  existing stamp and skips or updates rather than double-posting). Its shape never
  changes for aesthetics, only via an explicit version bump.
- A **rendered human presentation** — generated from the record through a template.
  Nothing parses this layer, so it is free to be readable.

**3. The presentation template is adopter-overridable; the stamp is not.** The kit
ships a sensible default render; an adopter who wants a different house style edits
the template, and all tooling keeps working because the stamp is untouched. This is
the project-neutrality split: structure is the methodology's, aesthetics are the
adopter's.

**4. The default render is richer than today, and verbosity is per-event-type.** The
kit default uses GitHub-native alert callouts to carry event class visually
(routine → `[!NOTE]`, an override happened → `[!WARNING]`, terminal → `[!IMPORTANT]`),
a bold title line, and a consistent `actor · timestamp` metadata line, with the
reason as body text. **Authorisation events** (promote, bypass, handoff) render the
full callout; **routine, high-frequency events** (ownership claim / abandon churn)
render a compact one-liner, so the timeline is not flooded. The **exact default
aesthetic is confirmed against a live rendered ticket** during implementation, not
frozen here — this record fixes the *structure* (two layers, per-event verbosity,
overridable template), not the final glyphs.

**5. The existing audit strings migrate onto the facility.** The DEC-026 promote /
handoff strings and the DEC-014 bypass template are re-expressed as events through
this facility; their machine stamps preserve the parseable-prefix intent DEC-026
called out. The **instance-ownership event log** (DEC-043 D3) is this facility
specialised with the ownership event types — it is *not* a parallel comment
mechanism, and its per-object-atomic append semantics (one comment per event) are the
facility's normal append behaviour.

**6. The facility is presentation only — it changes no gate, transition, or
severity.** It is the carrier for audit comments; what *requires* an audit comment,
and at what severity, remains owned by DEC-014 / DEC-024 / DEC-026 / DEC-043. Posting
through the facility does not alter when a comment is required or what it authorises.

## Rationale

**Why one facility, not N formatters.** The same shape — parseable + idempotent +
who/what/when/why — recurs at every audit site, and the ownership event log is the
recurrence that trips [pkit:COR-007]'s extraction trigger (a second-plus independent
consumer of the shape). One carrier means idempotence and the stamp format are
implemented and audited once, and a new event type reuses the carrier instead of
inventing a format.

**Why split the stamp from the render.** The austerity of today's strings is a symptom
of one line doing two jobs — machine signal and human message. Splitting them lets the
machine layer be strict and stable (good for parsing and dedup) and the human layer be
warm and restyleable (good for reading), each optimised for its one job. It is also
the same authoritative-structured-data-plus-rendered-view split DEC-043 uses for the
ownership marker; using it for audit comments too keeps one mental model.

**Why the render is overridable but the stamp is not.** Project-neutrality
([pkit:COR-014]) forbids the kit imposing an aesthetic on every adopter, but tooling
and idempotence need a stable contract. Making the *presentation* the adopter's and
the *stamp* the methodology's satisfies both — restyling never breaks parsing.

**Why defer the exact default glyphs.** The aesthetic decision is genuinely one you
cannot make from a code block — it has to be judged against a real rendered comment on
a real ticket. Fixing the structure now and confirming the glyphs live avoids
freezing a look no one has seen rendered.

### Alternatives considered

- **Keep per-site hand-rolled strings.** Rejected — unfactored recurrence; each new
  event type re-implements idempotence and invents a format; COR-007 says extract.
- **One line doing both jobs (richer prefix string).** Rejected — cannot be both
  cleanly parseable and genuinely readable; the two-layer split removes the tension.
- **A fixed, kit-imposed rich format (no override).** Rejected — violates
  project-neutrality; an adopter cannot restyle audit comments to their house voice.
- **A separate ownership event-log mechanism.** Rejected — duplicates the audit-comment
  shape; the ownership log is this facility specialised, per DEC-043.
- **Freeze the default aesthetic now.** Rejected — the glyph choice needs a live
  rendered ticket to judge; fix structure, confirm look at implementation.

## Implications

- **A new schema** carries the audit record's field vocabulary, the machine-stamp
  format (versioned), the per-event-type verbosity defaults, and the default render
  template; the stamp format references [project-management:DEC-024-lifecycle-hooks]'s
  template-stamp idempotence. Adopter override is a template file the render resolves
  through.
- **A shared `_lib` audit-log module** is the single builder: call sites construct a
  record and hand it over; the module emits stamp + render and performs the DEC-024
  dedup. No script string-builds an audit comment inline (the sole-builder discipline,
  consistent with the seam-ADR family).
- **Migration of existing audit sites** — `promote-issue`, `done-work --bypass`,
  `handoff-issue`, and the DEC-014 `bypassable-with-audit` template re-express their
  comments as events through the facility. Because the machine stamp preserves the
  parseable intent and the human render is a superset of the old string, this is a
  behaviour-preserving refactor at the observable-audit level; confirm at impl whether
  any external parser depends on the *old* prefix (if so, the stamp carries a
  compatibility alias). Surface change → capability version bump per [pkit:PRJ-002];
  a migration is authored if any committed adopter artifact embeds the old format.
- **The instance-ownership event log** (DEC-043 D3, contract [pkit:ADR-041]) is emitted
  through this facility; the ownership-event comment sole-constructor ADR-041 names *is*
  this facility's builder specialised with ownership event types.
- **Deferred (named, not built):** the confirmed default glyph set (validated live);
  any adopter-facing template-authoring UX beyond editing the template file.
- **No engine interaction** — the facility is a comment carrier; DEC-014 / DEC-024 /
  DEC-026 / DEC-043 retain ownership of when an audit comment is required and what it
  authorises. Realm-blindness and the severity model are untouched.
