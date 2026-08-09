---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-09
---

# Scratchpads as first-class hand-off artifacts in the report channel

## The question

An adopter's richest problem descriptions live in **scratchpad notes** — but the `pkit report` channel (PRJ-008) only carries a composed issue body, and the scratchpad has no lifecycle state that reflects what happened to the report. Should a scratchpad become a **first-class hand-off artifact**: attachable to a report, with its state wired (pull-only) to the reported issue's upstream state — and does the report surface need a **change/feature-request kind** to carry it?

## The worked example that motivates this (real, 2026-08-07..09)

The operator's actual workflow, exercised end-to-end this week:

1. Authored `2026-08-06-missed-handoff-detection.md` in trip-planner-agent-app's scratchpad — a full upstream request (definition, worked example, constraints, scope).
2. Opened a session **in the pkit repo**, pasted the scratchpad *path* by hand, and had the project-manager validate it, batch-plan it (#608/#609/#610), and ship it (COR-042 / ADR-048, `pkit process health`, v1.144.0).
3. The scratchpad still sits in trip-planner's `active/` — its retirement (`done --produced COR-042`) is a manual follow-up in another repo, and nothing in trip-planner shows that the request was picked up, worked, and **delivered**.

Every step of the hand-off worked — and every step was manual, cross-repo, and state-invisible. The proposal: `report` carries the scratchpad; the scratchpad carries the report's fate.

## Forces

- **The scratchpad is where the thinking is.** A structured bug form flattens a design-shaped request; the scratchpad *is* the right artifact (COR-012). Today it travels by paste or path.
- **Report kinds don't fit the common case.** PRJ-008 ships `bug` (structured) + `feedback` (freeform). The scratchpad hand-off is usually a **change/feature request** — today it rides `feedback` untyped, which costs the maintainer triage signal (`inbox` can't filter what isn't typed).
- **ADR-047's three bars are non-negotiable:** categorically-foreign + never-silent (confirm-or-draft; `--yes` produces, never posts) + fixed distribution-set target. Any attachment mechanism must fit *inside* the confirmed body — nothing may widen the write.
- **Redaction discipline** (PRJ-008): the environment block is redacted by construction. A scratchpad is *user-authored free text* — it can contain `$HOME` paths, private names, internal URLs. The confirm gate covers consent, but a pre-send redaction lint over the attached content would keep "never-silent done responsibly" honest.
- **Neutrality split (COR-014):** scratchpads are core (every adopter has them); the report *target* is distribution-level. Whatever state the scratchpad lifecycle gains must make sense **without** report configured — which pushes toward a general "this note's question moved into a tracker" state rather than a report-specific one (see the generalisation below).
- **Derive-don't-store / pull-only:** the scratchpad's "how is my report doing" view must be a **live read** of the upstream issue (cross-repo *read* is unrestricted per COR-039), never a synced/stored status that drifts. No eventing; the state is re-derived when asked — the same posture the process substrate takes everywhere (COR-033 P3, COR-038).
- **GitHub mechanics:** the issues API takes no arbitrary file attachments. Realistic carriers: **inline the scratchpad body** into the issue (collapsed `<details>` section), link the file's URL (only works for public adopter repos — usually false), or a gist (a *second* foreign write — new ADR-047 territory, likely disqualifying). Inline-in-body is the only carrier that stays inside the confirmed single write.

## Operator rulings (2026-08-09, in-session)

Three open questions below are resolved by operator direction; recorded here so the exploration narrows honestly:

1. **Naming: `reported`.** It best fits the meaning — the state exists *specifically in relation to the report channel's upstream repo* (for real adopters, pkit's home repo). The generalised `tracked` state (next section) is explicitly **not** wanted: scratchpads serve primarily as an in-project brainstorming place / thought-sharpener, and that primary role must stay untouched. `reported` is an **optional** side-state a note may enter, never a required stage of scratchpad life.
2. **The `reported/` directory is lazy.** It does not exist by default in a project — it is created when the first note enters it and **removed when it empties**. A project that never reports has no trace of the mechanism (matches the state's optional nature; an empty standing folder would advertise a workflow the project may never use).
3. **Reported notes carry dedicated metadata and are protected after send.** Frontmatter records the relation — the upstream issue ref(s), the reported date — and the note should be **protected against post-send modification**: what the upstream issue references must stay what was sent.

On protection mechanics (exploration, not yet ruled): scratchpads are edited as plain files, so hard prevention isn't available — but three honest layers are: (a) **convention** — `reported/` notes are frozen the way `done/` notes are, edits happen by starting a follow-up note; (b) **detection** — a content hash stamped into frontmatter at send; any list/status view surfaces "modified since reported" as drift; (c) **the authoritative snapshot is upstream anyway** — the report inlined the content into the issue body, so the as-sent text is preserved verbatim at the target regardless of local edits. (a)+(b) together seem right: cheap, honest, no write-gate machinery. A follow-up thought after a note is reported = a **new note** cross-referencing the reported one.

## The generalisation considered — and narrowed by ruling 1

The same hand-off happens **without** report: this very note's motivating example never used `report` — the operator hand-carried the scratchpad into a pkit session and the pm capability's batch-plan filed the issues. And adopters do the identical move *within their own repo* (scratchpad → own tracker via pm batch-plan). So the state question may be:

> A scratchpad gains a **`tracked`** (naming open: `reported` / `sent` / `handed-off`) lifecycle state meaning "this note's question has moved into a tracker," carrying one or more **issue refs** in frontmatter (e.g. `tracked: [aleskalfas/project-kit#608]`). *How* it got tracked — `report` verb, pm batch-plan, hand-filed — is producer detail, not state.

**Narrowed per operator ruling 1:** the general `tracked` state is out — `reported` is report-channel-specific, and the in-repo pm-batch-plan hand-off (scratchpad → own tracker) stays outside this design entirely. The generalisation is kept in the note only as the considered-and-rejected line, so a future reader knows it was weighed: the cost it would have paid is muddying the scratchpad's primary brainstorming role with tracker semantics every note would inherit. If the in-repo hand-off later wants its own visibility, that is a separate question (possibly COR-042's hand-off contract applied to the pm flow) — not this one.

What survives from the producer framing: `report … --scratchpad <slug>` is the producer — on successful post it stamps the frontmatter (refs, date, content hash) and moves the note to `reported/`. On the `--yes`/draft path **nothing is stamped** (nothing was sent). The read side (`pkit scratchpad list` / `status`) resolves each `reported` ref live and renders upstream state — and when **all** refs close, **prompts** retirement (`scratchpad done --produced <refs>`), never auto-retires (the note may deserve `--produced` refs only a human knows).

## Added requirement (operator, 2026-08-09): visible project + workstream context on every report

The operator runs **many projects with parallel workstreams**; when a report surfaces later (in `inbox`, in `list`, in a maintainer comment), connecting it back to *which project and which stream of work produced it* is the hard part of context-switching. So a report should carry **project name + workstream** as metadata that is:

- **Visible in the issue body** — a human-readable context line (e.g. `Project: trip-planner-agent-app · Workstream: render`), not only a hidden marker. The reader is the operator-as-maintainer three weeks later.
- **Also machine-parseable** — a marker line (the existing provenance-marker pattern) so `report inbox` and `report list` can group/filter by project without scraping prose.
- **Names, never paths** — the redaction discipline extended: the project identity must come from a *declared* source (a project-config `name` key, or the git remote's repo name), never derived from filesystem path strings. No `$HOME`, no directory segments.

Design notes:

- **Project name source (open):** explicit project-config key (most honest; prompts once on first report) → fallback to the git remote repo name (without the org? an adopter's private org name is itself potentially sensitive — the confirm gate shows whatever is chosen) → last resort, ask at compose time. Never the directory basename (a path leaf by another name).
- **Workstream source (open):** workstream is pm-capability vocabulary (the adopter's `workstreams.yaml`), not a backbone concept — layering matters. Candidates: (a) **derive from the current branch** — `<type>/<N>-<slug>` → issue #N → its workstream label; zero-effort and usually right, degrades cleanly when the branch isn't issue-shaped or pm isn't installed; (b) explicit `--workstream` flag; (c) omit. Leaning (a) with (b) as override — the derivation is read-only and capability-optional.
- **Not labels on the target repo.** Rendering adopter workstream names as upstream labels would pollute the target's label vocabulary with every adopter's local taxonomy; body metadata + marker keeps the target clean while staying filterable.
- **Interacts with #411** (version provenance on issues): same body-block, same triage motive — whichever lands first should shape the block so the other extends it rather than adding a second one.
- **Scratchpad tie-in:** a reported note's frontmatter could mirror the same pair (its project is ambient; its workstream may differ per note) — cheap to stamp at send alongside refs/date/hash.

## Candidate slices (roughly independent)

1. **`report change-request`** (or `--kind` on `feedback`): a typed third kind + `inbox` filter. Smallest slice; valuable alone; no scratchpad coupling.
2. **`report … --scratchpad <slug|path>`:** inline the note (collapsed section) into the composed body; redaction lint over the content; draft path carries it identically (`--yes` asymmetry untouched).
3. **`tracked` lifecycle state + frontmatter refs** in core scratchpad convention (COR-012 refinement or successor record): directory `tracked/` vs frontmatter-only flag is an open sub-question (directories are the existing state carrier; a note can be tracked by *several* issues, which frontmatter handles better).
4. **Producers append the ref:** `report` on successful post; pm batch-plan optionally (it knows its filed issues); manual `pkit scratchpad track <slug> <ref>` as the universal fallback.
5. **Read side:** `pkit scratchpad list` gains live upstream-state resolution for `reported` notes + the retirement prompt when all refs close. Offline ⇒ degrade to "reported (state unknown)" — never block, never store.
6. **Context metadata on every report** (independent of the scratchpad slices; likely the cheapest after 1): visible project + workstream line in the body + parseable marker; `inbox`/`list` grouping by project; names-not-paths sourcing rules. Coordinates with #411's provenance block.

## The `derive` fork (explored 2026-08-10, ruled by operator)

How does a maintainer turn feedback #N into fix issues without forgetting the `## Tracked by` link? Options weighed: (a) a `report derive <N>` verb wrapping issue-creation (thin passthrough to pm's create-issue via the capability dispatcher, degrading to a bare issue); (b) no derive — pm's create-issue/batch-plan grows `--from-report <N>`; (c) both.

**Operator ruling: no `derive` — it is too ambiguous a verb to support** (does it classify? does it plan? whose flags does it carry?). The covered paths are:

- **`--from-report <N>` on the pm side** (create-issue and batch-plan): filing a fix through the tooling that already owns classification and planning auto-links it into #N's `## Tracked by`.
- **The existing `report link <N> <fix>`** stays as the universal fallback (pre-existing issues, non-pm repos).
- **Load-bearing rule survives the ruling: the link-back is one obligation implemented once** — `--from-report` and `link` share the single `## Tracked by` editor, so the reporter's tracking loop cannot fork.

## Open questions (post-rulings)

- ~~Naming~~ → **`reported`** (ruling 1). ~~Required vs optional~~ → optional side-state (ruling 1). ~~Directory default~~ → lazy-created, removed-when-empty (ruling 2).
- **State carrier — mostly resolved by rulings 2+3:** a lazy `reported/` directory *plus* frontmatter metadata (refs list, `reported` date, content hash). Residual sub-question: a note reported against **several** issues gets one frontmatter list — fine; but can a note in `reported/` be reported *again* (a follow-up send)? Leaning no per the protection ruling — a follow-up is a new note.
- **Protection mechanics:** convention-freeze + hash-drift detection (a+b above) vs anything stronger. Where does drift surface — `scratchpad list` only, or also as a pre-send lint on the *next* report from the repo?
- **Does `done` require upstream closure?** Probably not — retirement stays a human gesture with `--produced`; upstream closure only *prompts* it.
- **One note → many issues:** done-able when *all* refs close, or when the container closes? (The #608 arc: one note → three issues under one Feature.)
- **Substrate or convention?** With the scope narrowed to an optional side-state, the process-substrate modelling looks like over-engineering — leaning plain convention + bespoke list view; keep the substrate line only as a rejected-alternative note when this crystallises.
- **Where do the records land?** The `reported` state + lazy-directory + protection metadata are core scratchpad convention (COR-012 refinement or successor COR). The `--scratchpad` attach + change-request kind are PRJ-008/CLI-spec refinements + an ADR-047 note (the confirm gate covers attached content). The redaction lint over attached content likely rides the same slice as the attach.
- **Inline size limits:** GitHub body cap (~65k chars); large scratchpads need truncation-with-consent or "excerpt + follow-up comment" — what's the rule, and does the hash cover the full local content or the as-sent excerpt? (Leaning: hash the full local file; the issue records what was sent; drift detection compares local-now vs local-at-send.)
- **Fork/self-host wrinkle:** in pkit's own repo the maintainer *is* the target — reporting a scratchpad to yourself is the same-repo edge ADR-047 already treats specially; probably just works as an ordinary issue + `reported/` move, but trace it once when designing.

## Depicted end-to-end flow (storyboard seed, validated in-session 2026-08-10)

Walked with the operator as mock CLI output and accepted ("seems solid"); when this crystallises, these steps become the COR-016 storyboard beside the implementing records. Derive-free per the ruling above.

**1. Send (reporter, in the adopter repo).** `pkit report change-request --scratchpad <slug>` composes: project (config `name`) + workstream (branch → issue → label, `--workstream` override) shown in the header; scratchpad inlined collapsed; redaction scan over the note is **interactive** (finding → edit-or-send-anyway, never silent, never a hard block); title carries the project in parens (`[CR] … (trip-planner-agent-app)`); body carries the visible context line + parseable marker + env block. Target-naming confirm before send; `--yes`/autonomy ⇒ draft only, nothing stamped.

**2. Stamp (on successful post only).** Note moves to lazily-created `reported/`; frontmatter gains `reported` (date), `reported_to` (ref list), `reported_hash` (full local file), `project`, `workstream`.

**3. Read-back (reporter, weeks later).** `pkit scratchpad list` resolves each reported ref live: upstream state + tracked-fix rollup per note; hash-drift flagged (`⚠ modified since reported`); offline ⇒ `reported (state unknown)`. Never stored, never blocking.

**4. Inbox (maintainer, in the target repo).** `pkit report inbox --group-by project` — grouped by the marker's project, workstream shown per row.

**5. Fix-filing (maintainer).** Through pm's own tooling with `--from-report <N>` (create-issue or batch-plan) — auto-links into #N's `## Tracked by`; `report link` for pre-existing issues. One shared linker.

**6. Close-prompt (maintainer).** `report inbox --resolved`: feedbacks whose tracked issues are all closed prompt a comment + close (the report-side cousin of pm's closure cascade; prompt, never auto).

**7. Retire-prompt (reporter).** All refs closed ⇒ `list` prompts `scratchpad done <slug> --produced <refs>` — a human gesture, never auto. Retirement empties `reported/` ⇒ the directory is removed.

**8. Post-send edit (protection).** Editing a `reported/` note ⇒ drift warning in `list` + pre-send lint on the next report from the repo; follow-up thoughts are a **new note** cross-referencing the reported one. The as-sent text lives verbatim in the issue.

**9. Edges.** Oversized note ⇒ excerpt + full text as follow-up comment, with consent, hash over the full local file; no `gh` auth ⇒ prefilled URL + draft (existing path); fork/self-host ⇒ same-repo edge, ordinary issue + normal stamp.

## What is already known (constraints to carry, not re-litigate)

- ADR-047: three bars + `--yes` produce-don't-send asymmetry — any attach rides the existing single confirmed write.
- PRJ-008: target fixed by distribution config; maintainer side same-repo; `## Tracked by` gives the *maintainer's* fix-linkage — the scratchpad's `tracked:` refs are the *reporter-side* mirror of the same loop.
- COR-039: cross-repo reads free; the only write stays the report itself.
- COR-012: retirement produces refs; `done`/`dropped` semantics unchanged by anything here.
- Related open work: #411 (version provenance for cross-version triage — feeds the same report block), #92 (user-feedback capability — the adopter-repo-direction cousin, keep distinct per PRJ-008).
