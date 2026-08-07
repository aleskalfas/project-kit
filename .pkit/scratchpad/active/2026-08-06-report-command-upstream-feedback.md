---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-06
---

# `pkit report` — built-in upstream-feedback channel

Design carrier for a new CLI surface: an adopter reports a pkit **bug** or freeform
**feedback** to the **main project-kit dev repo**, agent-assisted, with pkit +
capability versions and context auto-attached, and can then track the state of
their own reports (and any maintainer-derived issues) from the CLI. Origin: Mike's
adopter feedback (pkit 1.105 / pm 0.24) had no home — it was pasted into a chat.

## The problem this solves

Adopter feedback on pkit-the-tool currently has no first-class channel. An adopter
can open a GitHub issue by hand, but: (a) they must know to, and land on a
bug/feature template that fits awkwardly; (b) the maintainer gets a report with no
version/environment context (the single most useful thing for triage); (c) the
adopter has no easy way to see whether their report went anywhere. A built-in
`report` command is the classic tool pattern (`gh`/`rustc`-style bug-report) that
closes all three.

## Scope decision (settled with the user)

- The target is **fixed**: the canonical **project-kit dev repo** only. `report`
  is *only* an upstream-feedback channel to pkit's makers — it is **not** a
  general issue filer and it never touches the adopter's own project tracker.
- Therefore it is **not** a `project-management` capability feature (pm = the
  adopter's own repo). It is a distinct surface. (Placement — core CLI vs tiny
  capability — is an open question below.)
- It is a **deliberate cross-repo write** to a repo the session isn't rooted in.
  Sanctioned because the human explicitly invokes `report` (core.md rule 18's
  operator-gated exception); the command states the target plainly.

## Command palette

- `pkit report bug` — file a **structured** bug (agent helps: what you did,
  expected vs actual, repro). Lands as an issue labelled `bug` on the upstream.
- `pkit report feedback` — file **freeform** feedback (agent helps shape prose; no
  bug ceremony). Lands as an issue labelled `feedback`.
- `pkit report` (or `report list`) — list **my** reports + their states.
- `pkit report show <N>` — one report's detail: state + maintainer comments +
  linked/derived issues and their states.

## Design proposals (my defaults, for critique)

**Target + identity.** Fixed upstream owner/repo held as a single constant (one
place to change if the repo ever moves). Reports file under the **reporter's own
`gh` identity** on the public upstream, so tracking is just
`gh issue list --repo <upstream> --author @me --state all`. No maintainer proxy, no
membership gate (that's a pm concern, not this).

**No-`gh`-auth fallback.** If `gh` isn't authenticated, `report bug/feedback`
composes the full body and prints a **prefilled GitHub "new issue" URL** (title +
body query params) for the user to open in a browser — degrade, don't block.
Tracking (`list`/`show`) needs auth; without it, degrade to "open the tracker".

**Auto-context block.** Every report appends a fenced `## Environment` section:
pkit `VERSION`, each installed capability + version (from the backbone manifest),
adapter, OS/arch, and the invoking `pkit` subcommand path if relevant. This is the
core value-add — deterministic, no PII beyond what the user typed.

**Agent-assisted formulation.** A **skill** (`report-author`?) the acting agent
invokes: it interviews the user briefly (what were you doing / what tripped you /
expected), drafts a tight title + body, shows it for approval, then calls the
`report` script to file. Keep the agent's job **structuring, not bloating** — a
crisp report, not AI slop. (Open q: skill vs a dedicated agent.)

**bug vs feedback + derived issues.** Both are upstream issues, differentiated by
label. A freeform **feedback** is the low-commitment door; the maintainer triages
it and may **derive** one or more `bug`/`feature` issues from it. Those derived
issues reference the feedback issue (GitHub native reference / task-list), so
`report show <feedback-N>` surfaces the derived issues + their states, and the
reporter tracks progress without leaving the CLI.

**Progress tracking.** `list` renders one line per report: `#N state title
(last-activity)`. `show <N>` adds the comment thread (maintainer replies) and the
derived-issue rollup. v1 is a live query each run; a "what's new since last view"
(unread) notion is a deliberate v2 (COR-007 — only if it earns its keep).

## Open questions (for critic / architect)

1. **Placement + record type.** Core `pkit report` in the backbone CLI (universal —
   every adopter can report pkit bugs), or a tiny dedicated capability? And is the
   governing decision a **COR** (universal principle: "the kit ships an
   upstream-feedback channel") with the target as a constant, or a **PRJ**
   (project-kit-specific, since the target *is* project-kit's repo)? Leaning:
   core CLI command + a PRJ (or CLI-spec) record, because the fixed target is
   pkit-product-specific, not a neutral principle every adopter's project follows.
2. **Cross-repo-write framing.** Does routing a write to a *fixed foreign repo*
   need more than rule-18's operator-gate — e.g., an explicit one-time confirm on
   first use, or a config acknowledgement? Where does the upstream owner/repo live
   so it's honest and overridable-for-forks-later without inviting misuse now?
3. **Identity / privacy.** Filing under the user's `gh` identity is cleanest for
   tracking, but the auto-context block + the user's prose go to a **public** repo.
   Is a "review the exact body before it's filed" gate mandatory (I think yes)?
   Any redaction concerns for the environment block (paths, usernames)?
4. **Spam / quality surface.** A frictionless `report` on a public repo is an
   easier spam vector than a hand-filed issue. Rate/asking-for-confirmation? Or is
   "same as opening a GitHub issue, plus better context" sufficient (I lean the
   latter)?
5. **Feedback ↔ derived-issue linkage mechanic.** GitHub native cross-reference vs
   a `derived-from: #N` label/convention vs a task-list on the feedback issue —
   which gives the cleanest `report show` rollup without bespoke state?
6. **Does this overlap the existing "Feedback to the spec" channel?** The pm README
   documents a *maintainer→upstream-spec* (pm-workflow) flow via scratchpad notes.
   That's a different direction (distiller→spec) than this (adopter→kit-repo); name
   the boundary so they don't get conflated.

## Resolved design (post critic + architect + user, 2026-08-07)

**Surface.**
- Reporter side (universal): `report bug`, `report feedback`, `report` (list =
  *my* reports), `report show <N>`.
- Maintainer side (target-repo-gated): `report inbox` (all incoming feedback),
  `report link/unlink <feedback-N> <fix-N>` (edit the feedback's `## Tracked by`).
- `report ... --on-behalf-of @login` — attributed reporting (not authorship; see
  below).

**Target = distribution PRJ config, not a neutral-core constant** (resolves the
critic/architect split): the backbone ships the *target-agnostic* report
mechanism; project-kit-the-distribution sets the target to its own repo via PRJ
config. Neutral core stays neutral (COR-014); a fork sets its own target; report
is inert/degrades if unconfigured. Not adopter-arbitrary, not a `--repo` flag —
one distribution-set target, so it never becomes a general foreign-issue-filer.

**Cross-repo safety (reporter side only — it writes to the foreign upstream).**
First realization of COR-039's reserved exception → ADR:
- Sits *outside* the `session_guard` interlock **by category** (intentional-foreign,
  never-could-be-local), NOT via an override flag.
- Never-silent: a per-invocation **target-naming confirm** ("posts a PUBLIC issue
  to `<owner/repo>` under your gh identity"); under `--yes`/autonomy **degrade to
  a draft** (prefilled URL / file), do not auto-post — a deliberate `--yes`
  asymmetry vs the rest of the CLI.
- **URL-first, `gh`-file opt-in** — works for everyone, browser = a review gate,
  no spam surface; gh-auto-file is the authenticated convenience.
- **Redaction by construction** — strip `$HOME`/abs-paths, kit-shipped
  capabilities only (`--include-private` opt-in), no repo-slug leak — *then* show
  for review. Load-bearing (public repo + real identity).

**Maintainer side = same-repo** (a pkit dev's cwd *is* the target) → plain issue
edits, no cross-repo gate. Gated by "cwd repo == report-target repo" — that gate
*is* "just for pkit developers" (structural, no role flag; inert elsewhere).

**Tracking model.**
- `list` = issues **authored by me OR attributed to me** (`--on-behalf-of` marker),
  so an on-behalf report still tracks for its beneficiary.
- `show <feedback-N>` = the feedback + a **`## Tracked by`** rollup: a GitHub
  task-list of `#N` references (many-to-many, non-owning — derived *or*
  pre-existing) with each linked issue's state. Chosen over native sub-issues
  (too strict / single-parent) and over a `derived-from:` label (bespoke).
- Maintainer-derived issues are maintainer-authored → they don't clutter the
  reporter's `list`; they surface under the parent feedback in `show`.

**On-behalf = attribution, not authorship.** GitHub stamps the authenticated user
as author; you cannot file *as* someone else. `--on-behalf-of @mike` files under
your identity + a "Reported for @mike" credit/marker; the marker restores @mike's
tracking. Soft consent nudge (public repo + their name).

**Value-add / why v1 includes tracking.** The auto-context block (version-stamped,
redacted) is the core value; tracking is the **adoption flywheel** (report → watch
it move → trust). There *is* a first trackable item (Mike's), so it's not
zero-instance; the only piece needing a producer (the derived rollup) is made real
by the `report link` verb + the `## Tracked by` convention.

**Boundary vs pm "Feedback to the spec".** Different direction: that is
distiller→upstream-*spec* (pm-workflow) via scratchpad notes; this is
adopter→*tool-repo*. Name it in the PRJ so they don't conflate.

**Records:** PRJ-008 (project-kit ships `report`; target = our repo; product
rationale) + ADR-045 (the cross-repo realization above) + CLI-spec entry. **No
COR** (fixed-target is product-specific; fails universal applicability — precedent
PRJ-004, the fixed install source). Version aggregation reuses an extracted
`collect_environment()` accessor shared with `status` (COR-007), reading the
*installed* manifest side.

## Next steps

- [x] `critic` + `architect` passes; findings folded above.
- [ ] Author PRJ-008 + ADR-045 + CLI-spec entry (proposed; not accepted).
- [ ] `methodology-reviewer` neutrality pass on the records.
- [ ] Show the records to the user before writing command code.
- [ ] On sign-off: build (`report` command + `report-author` skill + `report link`
      + tracking reads + the extracted `collect_environment()` + tests).
