# Changelog

## 1.148.0 — 2026-08-11

### Added
- The report channel's send path is API-primary (#662, from #660's dogfood inventory; first slice #659): with `gh` authenticated, the full send payload is shown once and an explicit confirm — naming the target AND the posting identity ("posts as @<login> to <owner/repo>") — posts via `gh`, so a real scratchpad-backed note travels as the issue body and is never URL-embedded. The prefilled-URL form survives only without `gh` auth or behind an explicit `--url`, within a documented ~6000-char budget (beyond it GitHub's edge hard-fails the form with HTTP 414), and always warns that the browser's logged-in account authors the submit; `--open` opens a within-budget form directly. `--yes`/autonomy now STAGES the composed payload (compose-time redaction findings ride the stage header) under the gitignored `.pkit/scratchpad/.report-drafts/` and prints one line; the new interactive-only `pkit report submit <id>` lists, reviews, confirms, posts, stamps, and cleans up — ADR-047's asymmetry intact: `--yes` stages, never posts.
- Every report's kind is now reliably visible (#663, from #660's dogfood inventory): all three kinds carry a consistent title prefix (`[Bug]`/`[CR]`/`[Feedback]`, prepended at compose before the project parenthetical — previously only change-requests were prefixed), and an API post applies a namespaced kind label (`report:bug`/`report:change-request`/`report:feedback` — namespaced so the channel never collides with the target repo's own label vocabulary), created on the target if missing (fixed color per kind, description "pkit report kind"). A label create/apply failure degrades to posting without the label — a warning, never a blocked send — since the prefix + the body kind-marker (still machine-authoritative) carry the kind everywhere, URL prefills included. The read side (`report inbox`/`show`/`list`) classifies label → marker → prefix, learning the namespaced labels, the legacy bare-kind labels, and all three prefixes — so a label-less URL filing like #660's `[Feedback]`-titled report now classifies — and `report show` renders an unplaceable issue honestly as `unclassified` instead of the kind-masquerading `report`.
- The report channel's bookkeeping now fires on every path (#664, from #660's dogfood inventory §C): any scratchpad-backed compose that ends at a URL instead of a post — `--url`, `--open`, the no-auth fallback, or an API post degraded to the URL — ends with the required tracking follow-up as its last line (`after filing in the browser, run: pkit scratchpad reported <slug> <issue-ref>`), so the manual stamp is never a hidden step; the compose-time redaction lint is test-pinned on all four paths (interactive API, `--url`/`--open`, `--yes` stage, `submit` resurface). The two tracking surfaces reconcile to one declared truth — the issue (upstream) is the truth for state, the note's frontmatter for what was sent — by derivation only: `report list` tags a row `[note: <slug>]` when a local `reported/` note references that issue (no sync mechanism, nothing stored). And the `report show` / `report --tree` Tracked-by rollups now render each fix's title and URL beside its number + state (bare numbers forced a browser round-trip), degrading to number + state when a ref can't be resolved offline.

### Fixed
- List rows on both tracking surfaces now carry the full issue reference (#678, from #660's adopter feedback on the shipped #664 flow): `pkit report` / `report --tree` (and inbox) rows render the report's own URL beside the title, and `pkit scratchpad list` renders each reported ref's issue title + URL beside its number + state in the same single read — both degrading to number + state offline exactly as before.

## 1.147.1 — 2026-08-10

### Fixed
- Fixed the project-root walk accepting any bare `.pkit/` ancestor as a root (#656): a stray junk `~/.pkit/` made out-of-project `pkit upgrade` resolve `$HOME` and error with the seed-the-manifest remediation — inviting `pkit sync` into the home directory. The walk (`find_target_root`, the router's boundary walk, and the bash dispatcher's mirror) now requires an install marker — `manifest.yaml`, or `decisions/` for installs pre-dating the manifest layer — and skips bare/foreign `.pkit` dirs, continuing upward. Out-of-project `pkit upgrade` therefore reaches the ADR-044 tool-only update path as designed; the seed-the-manifest error remains reachable only inside a marker-qualified legacy root.

## 1.147.0 — 2026-08-10

### Added
- New `pkit report change-request` — a typed change/feature-request kind joining bug/feedback as a third sibling verb (#639, PRJ-008 refinement). A CR is structured-ish: the body is scaffolded into a motivation / desired behaviour / current workaround template, the title gets a `[CR]` prefix, and every composed report now carries a body kind-marker (`<!-- pkit-report: kind=… -->`) so the maintainer inbox classifies reports even when the GitHub label is dropped on URL-filed issues. All ADR-047 behaviour is identical to the existing verbs (URL-first, target-naming confirm, `--yes` produces-never-posts, redacted environment block). The maintainer inbox grew `--kind <bug|feedback|change-request>` filtering, `--group-by project` (grouping by a body project marker; degrades to `(no project)` until that marker ships), and `report inbox --resolved`: open feedbacks/CRs whose `## Tracked by` issues are all closed are listed and — interactively only — prompted per report for a closing comment + close; `--yes`/non-interactive lists without ever closing.
- COR-043 (accepted): scratchpad notes gain an optional `reported` side-state — lazily-created directory, frontmatter refs/date/content-hash, freeze-by-convention with drift detection, live pull-only upstream read-back and retire-prompt. ADR-050 pins report context sourcing (pm-provided workstream read-verb, declared project name, never paths); ADR-047 refined to the confirmed-send-payload unit for oversized attachments. Implementation follows (#642).
- Implemented the COR-043 scratchpad reported side-state (#643): `pkit report bug|feedback|change-request --scratchpad <slug>` inlines a note into the report as a collapsed as-sent section, with a compose-time redaction lint on every path (drafts included; interactive findings prompt edit-or-send-anyway). An oversized note is sent as an excerpted body plus one overflow comment carrying the full as-sent text, confirmed as a single gesture; a partial failure (issue posted, comment failed) stamps nothing and names the created issue with remediation and the verbatim error (ADR-047 refinement). A fully successful post moves the note to the lazily-created `reported/` with refs/date/content-hash frontmatter — draft/URL paths stamp nothing. New `pkit scratchpad reported <slug> <ref>...` is the manual stamp gesture (accepts issue URLs, appends refs idempotently), and new `pkit scratchpad list` resolves reported refs live (offline degrades to "state unknown"), flags notes modified since reported, and prompts retirement when all refs close. `scratchpad done`/`drop` now also retire from `reported/` (removing the lazy directory when it empties), and every report verb warns pre-send when a reported note has drifted.
- Every report now carries visible project + workstream context (ADR-050, #644): a human context line atop the composed body (`Project: … · Workstream: …`), `project=`/`workstream=` keys on the body report-marker, and a ` (<project>)` title parenthetical. The project name is declared — a `name` key in the adopter-owned `.pkit/project/config.yaml`, prompted once on an interactive compose with an offer to persist, falling back to the git remote's repo name without the owner/org — never a filesystem path segment; unresolvable renders an explicit "(project: not declared)" note. The workstream is asked of the project-management capability's new `context-workstream` read verb by subprocess through the capability dispatcher (`--workstream` overrides; pm absent means omitted — the backbone never reads pm vocabulary itself). A successful post stamps the pair into the reported note's frontmatter; `report inbox --group-by project` groups live on the marker, and `report`/`report inbox` rows show the project / workstream when present.
- **project-management 0.53.0** — Added the `context-workstream` read verb (pkit ADR-050, #644): resolves the current branch `<type>/<N>-<slug>` to issue #N and prints its bare `workstream:*` label value, or nothing when underivable. Read-only, always exits 0, not membership-gated; invoked by the backbone's report compose through the capability dispatcher so workstream vocabulary stays inside the capability.
- **project-management 0.53.0** — Added `--from-report <N>` to create-issue (and documented it as the batch-plan filing loop's pass-through flag, #645): filing a fix from feedback/change-request #N auto-links the new issue into #N's `## Tracked by` by invoking the backbone's canonical `pkit report link` editor (DEC-048's one-linker rule — never a second Tracked-by implementation). Maintainer-side same-repo, gated by the backbone verb (refusal surfaced verbatim); a link failure after a successful create warns with the exact remediation command and exits 4, never rolling the issue back. `requires_backbone` floor raised to 1.144.0 (the version shipping `report link`).

## 1.146.0 — 2026-08-09

### Changed
- **`pkit upgrade` now updates the pkit tool itself** when it is stale, instead of just printing the command (#638, ADR-044 amended). When the installed `pkit` is behind the latest release it runs `uv tool install --force …@v<latest>` and **re-runs the upgrade under the new version** — one seamless command, no manual step. Run **outside any project**, `pkit upgrade` performs this tool update alone instead of erroring on a missing project. It **degrades to just printing the command** (the old detect-and-instruct behaviour) when the session is non-interactive (no TTY — so a network install is never forced under automation), when `--no-self-update` is passed, or if the install fails/is declined — it never bricks. Safe because pin-by-default (v1.145.0) insulates projects from the global tool: self-update fires only on the un-pinned path, and a pinned project still runs its own version via the router's `uvx` re-exec (the ADR-039 multi-version invariant is preserved).

## 1.145.0 — 2026-08-09

### Changed
- **`pkit upgrade` now pins the project by default** at the version it upgrades to (#631, ADR-049 amended) — pinning becomes the norm so a project stays code⟺content-coherent with no separate `pkit pin` step, and never runs a newer global CLI over older un-migrated content. Pass **`--no-pin`** to keep a project un-pinned (it keeps following the installed global tool, running in-process; `pkit unpin` removes an existing pin). It pins at the **local** synced version (offline-safe — no `git ls-remote` lookup), writes the pin **last** (so a failed sync never leaves a pin ahead of content), and is a no-op on an already-pinned project (which still auto-advances its pin). Self-host is never pinned. **This reverses ADR-049's opt-in default** (a project now opts *out* of pinning rather than *in*) and supersedes the short-lived `--pin` opt-in from #627 (never released; removed). Note the new default moves a project into the pinned (uvx-re-exec) execution model on its next upgrade; the router degrades an unresolvable pin to running self, so a pinned project never bricks offline.

### Fixed
- **project-management 0.52.1** — The criteria primitives (check-criterion / uncheck-criterion / show-issue --field criteria) now resolve checkbox-bearing headings from body-format.yaml instead of hardcoding "## Acceptance criteria" — an EPIC's "## Success criteria" boxes can be ticked by index (previously refused with "0 acceptance criteria" while still gating the close) (#624).

## 1.144.0 — 2026-08-07

### Added
- Per-project version pinning via a project-owned `.pkit/version-pin` directive (#605, ADR-049). A project opts into running a fixed pkit version by committing the directive; the entry-point router reads it (moving the pin source from `.pkit/VERSION` — the slot ADR-039 left to implementation) and re-execs the pinned version, so a global-tool upgrade no longer moves a pinned project. Two new commands manage it: `pkit pin [<version>]` and `pkit unpin` (removes the directive). With no argument `pin` freezes the project at its current *content* version (`manifest.yaml`'s `backbone_version`); with a `<version>` (a version number only — a single leading `v` is stripped, and branch/sha/pre-release tokens are refused since the router routes only a bare `v<semver>` tag) it dispatches on how the target orders against the content version — equal freezes in place, a newer version reconciles content forward (under that version's own code, via the `PKIT_NO_ROUTE=1` bypass) and then flips the pin last, and an older version is refused because migrations are forward-only (COR-010; roll back with `git checkout` of `.pkit/` instead). Both forms require the manifest. `pkit upgrade` in a pinned project now *auto-advances* the pin to the latest release with no `uv tool install` and no manual step: detected as the routed pinned child, it resolves the latest tag (ADR-044's `git ls-remote` check) and, when latest is newer than the pin, reconciles content forward under the target's own code (via the `PKIT_NO_ROUTE=1` bypass) then flips the pin last (never ahead of content; an interrupted raise is recovered by an idempotent re-run) — a clear no-op when already at latest, a distinct message when the pin sits ahead of the newest release, and a loud degrade (pin unchanged) when the release source is unreachable. An un-pinned project's upgrade is unchanged. The directive is project-owned and never written or clobbered by `init` / `sync` / `upgrade`'s content pass.
- COR-042 (accepted): a depends_on entry may opt in to an evaluable hand-off contract (trigger + candidates/resolve seam predicates); a report-only `process health` operation reports missed hand-offs, exit non-zero on any miss or indeterminate. ADR-048 records the seam mechanism + sibling-module placement. COR-038's reader-set ruling re-scoped by amendment note; COR-035's deferred list updated (first family shipped). Implementation follows in #610 (#609).
- `pkit process health` landed per COR-042/ADR-048 (#610): the report-only missed-hand-off walk over opt-in `handoff` contracts on `depends_on` entries (additive schema sub-block: trigger + candidates/resolve seam predicates), homed in a sibling module beside the engine with the pinned import boundary; flow-direction report + byte-stable `--json`, `--process` filter, topological coupling order, exit non-zero on any miss or indeterminate.
- New `pkit report bug` / `pkit report feedback` — the built-in adopter→project-kit feedback channel (#613, PRJ-008 / ADR-047). Composes a bug or freeform-feedback report with a **redacted** environment block (pkit + capability versions, adapter, OS/arch — no filesystem paths; incubated capability names withheld unless `--include-private`) and prints a **prefilled GitHub new-issue URL** — the URL-first path works with no `gh` auth (the browser submit is the review gate). An opt-in `--file` posts via `gh` after an interactive **target-naming confirm**, degrading to the URL when `gh` isn't authenticated or under `--yes` (the foreign write is never auto-posted — the deliberate `--yes` asymmetry, ADR-047). `--on-behalf-of @login` attributes a report filed for someone else. `pkit report` (no subcommand) lists your reports + states — both those you authored and those filed **for** you (marked `filed for you`), so a beneficiary tracks a report they never authored — and `pkit report show <N>` adds the maintainer comments and the `## Tracked by` rollup (the issues that will fix it, with each one's state); `pkit report --tree` nests each report's tracked-by fixes under it. The maintainer side — `pkit report inbox` (triage queue) and `report link` / `unlink <feedback-N> <fix-N>` (wire a fix issue into a feedback's `## Tracked by`) — is enabled **only inside the report-target repo** and inert elsewhere (same-repo edits, no cross-repo gate). Ships the `report-author` skill: an agent interviews the reporter to draw out a clear, actionable bug/feedback description (redaction-aware for the prose), then files it via the command.

### Changed
- `pkit permissions apply` routes allow rules justified only by the active permission profile into the gitignored `.claude/settings.local.json`, tracked by a new provenance ledger sidecar (`.pkit/permissions/project/profile-realized-allows.yaml`) and recompute-replaced on every apply — a profile switch or deactivation heals its stale rules away; operator/harness-authored local rules are never touched (ADR-046, #611). Rules justified by committed model state keep realizing additively into `.claude/settings.json`, so activating a profile no longer produces tracked-file drift in repos that commit that file. `diff` reconciliation reads the two-file union; floor claims (probe double-lock, unjustified-rule attribution) stay committed-scope. Existing drift converges by restoring the tracked file and re-running `apply` (documented operator gesture; no migration).
- Design-ahead, no user-facing surface moves: accept PRJ-008 + ADR-047 for `pkit report` (the built-in adopter→project-kit feedback channel), and land the internal `collect_environment()` accessor + CLI-spec draft. The `report` command family itself ships in a later PR (#613), which carries the surface changeset.

## 1.143.1 — 2026-08-07

### Added
- **project-management 0.52.0** — New `comment-issue` / `comment-pr` verbs (#586, DEC-047): the project-manager agent — denied direct `gh` writes — can post a freeform comment (evidence, analysis, triage notes) on an issue or PR through the validated path, instead of a human pasting it. Membership + foreign-repo guarded, `--dry-run` / `--yes`, `--body` (comments take `--body` only; `--body-file` stays reserved for body writes). Because the methodology drives its merge gate off comment text, the verb refuses a body whose first line would impersonate a structured comment — a DEC-028 reviewer verdict, a human-mode `Approved`-prefix, or a DEC-014 audit template — so a freeform note can never spoof the gate or be read as an audit record; every posted comment also carries a `<!-- pkit-freeform -->` marker. No migration.

### Changed
- **project-management 0.52.0** — Settle the `--force` / `--bypass` override-flag convention (#570, DEC-046). `--bypass[-<gate>]` overrides a `bypassable-with-audit` gate (a required, audited reason; qualified per-gate when a command has several, e.g. `done-work`'s `--bypass` + `--bypass-ci`); `--force` overrides a `hard-reject` finding or a hard script precondition (boolean, audited where the substrate can carry it). DEC-014's `hard-reject` is amended to carry the out-of-band operator `--force` layer — recorded as a new `force_overridable: true` field on its `validation-severity.yaml` entry, so an agent dispatching on the severity token sees the override exists (`bypassable: false` stays: there is no in-band `--bypass` for a hard-reject). `edit-issue --force` and `remove-workstream --force` help text corrected (they overrode a hard-reject / precondition, not a bypassable gate). No behaviour change; no migration.
- **project-management 0.52.0** — The agent-mode merge gate now counts a DEC-028 reviewer verdict only when its comment carries a `<!-- pkit-verdict -->` provenance marker (#593). The reviewer path stamps it (`review-pr.py` on post; a directly-posting reviewer includes it), and `agent_verdicts.gate_verdicts` requires it. This closes the read side of the DEC-047 sentinel-spoof: a bare `Reviewer agent … APPROVED` first line — hand-typed, or a freeform note that reached the PR by any other path — no longer satisfies the gate unless the reviewer path stamped it. The read surface (`show-pr --field review`) stays permissive and still displays every verdict-shaped comment, marked or not. Verdicts are ephemeral (re-run `review-pr`), so no migration; DEC-028 amended.

### Fixed
- `pkit validate`'s backward citation check no longer flags un-actionable references on kit-owned agent/skill content (#584). Three kinds of body path reference are exempted from the reads.paths-declaration requirement because they are not overlay-resolved external reads: anchor/same-file links (already), decision-record links (`[COR-026](.../COR-026-…md)` — the record is the real reference, checked separately), and a capability artifact's pointers into its own tree (`scripts/*.py`, sibling sub-procedures, `project/config.yaml`). Record and hook citations, and paths resolving outside the capability, are still flagged. Also resolves a bare sibling `storyboards:` entry against the agent's own directory (not just target-root), fixing a false "file does not exist" for capability agents whose storyboard sits beside them.
- **project-management 0.52.0** — `move-issue` now refuses a bare `--bypass` that carries no reason, instead of silently substituting a placeholder audit reason (#580). The `bypassable-with-audit` gate records the reason in the audit comment (DEC-014) and the override-flag convention (DEC-046) requires it non-empty, so `move-issue <N> --to <state> --bypass` without a non-empty `--bypass-reason` is refused before any mutation or audit comment. Whitespace-only reasons count as missing. Wrapper call sites (promote-issue and friends) always pass a reason, so only the direct-invocation path is affected.
- **project-management 0.52.0** — `pkit data validate` now resolves the capability's seeded `project/workstreams.yaml` instead of reporting "no schema binding found" (#585). The capability shipped only `workstreams.schema.json` with no `schemas/workstreams.yaml`, so neither the `pkit_schema:` field path (the resolver requires the `<schema>.yaml` + `.schema.json` pair to exist) nor a `binds_to:` glob (read only from `schemas/*.yaml`) could bind the file. Ship a `schemas/workstreams.yaml` binding carrier declaring `binds_to: ["**/workstreams.yaml"]` (mirroring the instance-ownership / substrate-map schemas), let the companion accept the `binds_to` / `pkit_schema` fields, and add the self-describing `pkit_schema: project-management:workstreams` tag to the seed. No behaviour change to how workstreams are read; no migration.
- **project-management 0.52.0** — `merge-pr` no longer misreports a successful merge as a failure when the PR's head branch is checked out in a git worktree (#587). `gh pr merge --delete-branch` cannot delete a local branch that is checked out, so it merges the PR and deletes the remote branch, then exits non-zero on the failed local delete. `merge-pr` now detects that exact case — the head branch is checked out in a worktree AND the PR did in fact merge — and reports success, leaving the local branch in place with a notice naming the worktree. A genuine merge failure that merely coincides with a checked-out branch still fails (the post-merge re-check guards it). The normal squash-and-delete path is unchanged.
- **project-management 0.52.0** — `edit-issue` now scopes validation to the field(s) being edited (#583). It previously re-validated the whole issue state on every edit, so a title-only edit hard-rejected on an untouched body that predates the current body schema — a legacy issue could not take a clean title fix without a full body rewrite, and (before the `--force` crash fix) the escape hatch was unusable. A title-only edit now validates the new title but not the untouched body; a body-only edit validates the new body but not the untouched title; a body edit still validates the new body in full. No migration.

## 1.143.0 — 2026-08-03

### Added
- `pkit upgrade` now runs a best-effort staleness check against the release source (`git ls-remote --tags` on the compiled distribution URL) and, when the installed tool is behind the latest release, prints the exact `uv tool install --force <url>@v<latest>` command to update it (then re-run `pkit upgrade`) — it installs nothing itself (ADR-044). When the tool is current it says so plainly instead of the ambiguous "nothing to upgrade". The check is read-only and never fails the command: any lookup failure (offline, missing credentials, git unavailable, timeout) warns loudly and continues with today's project sync, and it is suppressed on a source checkout / self-host. ([#574])

### Changed
- **project-management 0.51.0** — Validate PR bodies at the ready-for-review transition, not only at merge (#569). `open-pr` (non-draft) and `review-work` (opening a ready PR, or flipping a draft to ready) now run the shared PR-body validator at merge-gate strictness and refuse a skeleton body (empty `## Summary`, a bare `- [ ]` `## Test plan`, empty `## Doc impact`), closing the fail-late trap where such a PR passed open + review and only blocked at `done-work`. Drafts stay exempt; a new `--force` flag on `open-pr` / `review-work` overrides a blocking body with an audit note. You can no longer take an empty body to ready-for-review — fill a draft first, or use `open-pr --body-file`.

### Fixed
- **project-management 0.51.0** — Fix `edit-issue --force`, which crashed with a `TypeError` before writing its audit comment — the `--force` audit-comment call site dropped the `config` argument to the internal comment helper. The documented escape hatch for editing a non-compliant issue works again.

[#574]: https://github.com/aleskalfas/project-kit/issues/574

## 1.142.7 — 2026-07-31

### Fixed
- Roll the backbone to carry the project-management 0.50.2 brownfield create-issue fixes (#557 the `--body-file` first-line check honours an advisory hierarchy; #559 the requiredness-gate substrate-awareness sweep) to adopters through `pkit upgrade`. project-management is a kit-shipped capability delivered bundled with the backbone, so these capability-only fixes need a backbone tag to reach adopters via the normal upgrade path; this bump tags the tree that already contains them. ([#559])
- **project-management 0.50.2** — The create-issue `--body-file` first-line parent-ref check now consults the hierarchy mode, mirroring the requiredness gate above it. Under `hierarchy: advisory` a non-parent-ref first line is accepted (parentless, body verbatim) so a flat brownfield tracker can file a prepared parentless body; greenfield / `hierarchy: gated` still hard-rejects a non-parent-ref first line unchanged. ([#557])
- **project-management 0.50.2** — Swept every create-issue requiredness/format refusal for substrate-map / hierarchy awareness (the create-side mirror of the read-side sweep). The workstream-requiredness gate now MIRRORS the writer's (`_build_labels`) write/no-write decision, reusing the same seam predicates and the same `resolve_write` — so the gate and the resolution cannot drift. It demands `--workstream` only when a workstream LABEL is the substrate (greenfield or an adopter-remapped `label` binding) AND no such label would be written for the omitted value; a `title-prefix` / `derive` / `unsupported` / absent axis is never label-written, so the gate no longer over-fires on those sibling arms (the earlier `served`-only predicate demanded a value for a `title-prefix`- or `derive`-bound axis that `_build_labels` never labels). An adopter-declared `default:` that resolves to a real write covers an omitted `--workstream` (the default supplies the label); a default that itself DEGRADEs does not, so the axis never silently drops. The explicit-`--workstream` value validation is now likewise substrate-aware — skipped under `workstream: unsupported` (the value is discarded by the writer, so validating it would false-refuse), kept for greenfield / served. Greenfield is byte-unchanged. The parent-requiredness, `--body-file` first-line gates were confirmed already substrate-aware; the title-format gate is left unchanged pending the brownfield-title-composition decision it is entangled with. Universal invariants (membership, cross-repo guard, unknown type, the kind/structural mismatch) stay hard. ([#559])

[#557]: https://github.com/aleskalfas/project-kit/issues/557
[#559]: https://github.com/aleskalfas/project-kit/issues/559

## 1.142.6 — 2026-07-30

### Fixed
- Roll the backbone to carry the project-management 0.50.1 brownfield `validate-issue` fix to adopters through `pkit upgrade`. project-management is a kit-shipped capability, so it reaches adopters bundled with the backbone; the fix landed between backbone tags (as a capability-only release), leaving no tag the upgrade path could deliver. This backbone bump tags the tree that already contains the fix so `pkit upgrade` delivers it. ([#553])

[#553]: https://github.com/aleskalfas/project-kit/issues/553

## 2026-07-30

### Fixed
- **project-management 0.50.1** — The `validate-issue` type-axis handling is now fully substrate-aware, so it agrees with `pre-check` on a brownfield repo across every `type` binding. A title carrying the adopter's own prefix (e.g. `[Epic]`, which diverges from the kit's rendered `[EPIC]`) resolves against the substrate-map's declared prefixes instead of false-failing `title.format`; a `type` bound to a label remap now demands one of the adopter's remapped labels (previously a missing type slipped through the close-gate); and a `type` bound to a title-prefix demands no kit `type:*` label but does demand a resolvable declared prefix — a title matching none of the adopter's declared prefixes hard-rejects `title.format` (an undeterminable structural type), consistent with the other served arms. All arms route through the axis-labels seam, and greenfield behaviour (a missing `type:*` label still hard-rejects) is unchanged. ([#553])

[#553]: https://github.com/aleskalfas/project-kit/issues/553

## 1.142.5 — 2026-07-10

### Changed
- **project-management 0.50.0** — Add `show-pr --field review` — surface the DEC-028 reviewer verdict (token + reasons) through the governed pm read path, so the verdict is no longer opaque after `review-pr`.

### Fixed
- The release step now keeps the source repo's own self-host manifest backbone version current on a backbone bump, so `pkit status` no longer misreports the self-host backbone as frozen at genesis.
- **project-management 0.50.0** — The provenance footer no longer stamps `tree unknown` in adopter installs — the backbone version now resolves from `.pkit/manifest.yaml` when `.pkit/VERSION` is absent.

## 1.142.4 — 2026-07-08

### Fixed
- `pkit sync`/`upgrade` no longer silently aborts when a listed skill or agent resolves to no canonical file. The claude-code deploy primitives ran an unguarded resolver whose benign "not found" tripped `set -e`, killing the run mid-way with no diagnostic (only the wrapper's opaque "exited with status 1"). The common trigger is a composite skill folder mid-build (COR-020): sub-procedures present but no `<name>/<name>.md` dispatcher yet. Both deploy scripts now skip the unresolvable item loudly — naming the skill/agent and the defect with a remediation hint — deploy the rest, and exit cleanly with an end-of-run summary. ([#537])

[#537]: https://github.com/aleskalfas/project-kit/issues/537

## 1.142.3 — 2026-07-08

### Fixed
- Scope the COR-018 companion-JSON-Schema requirement to actual schema definitions in `pkit schemas validate` (and register's capability self-consistency check). YAML fixtures under `examples/` (or named `*-example.yaml`) and instances that declare an external/shared `$schema` pointer (a `# yaml-language-server: $schema=` directive or a top-level `$schema:` key at a schema other than their own companion) are no longer wrongly flagged as schema definitions missing a companion. A genuine schema YAML with no companion is still flagged.

## 1.142.2 — 2026-07-08

### Added
- **project-management 0.49.0** — Add the `set-instance` command — set (or `--show` / `--clear`) this clone's opt-in, per-clone numeric instance id, the activation gate for instance ownership when one person runs several clones of a repo (DEC-035). The id is written to a git-ignored runtime file and read by the ownership lifecycle; a clone with no id set is unchanged. The claim / clash-guard / signed-listing behaviour that acts on the id follows in subsequent changes.

### Changed
- Documented COR-031's operational collision precedence in the CLI reference: register keeps the in-repo (incubated) copy on a kit-source name collision and surfaces that a kit-shipped version is available; sync leaves incubated untouched (D1). A doc clarification of already-decided behaviour (no COR change, no surface moved).

### Fixed
- `pkit sync` no longer silently downgrades a capability: when the source ships an older version than the one installed, sync now refuses — naming both versions and leaving the installed tree untouched — instead of overwriting newer work. `pkit sync --force` overrides the guard to downgrade deliberately (and loudly).
- `pkit capabilities register` no longer refuses an already-registered capability outright: it now branches on origin. An entry registered as `incubated-in-repo` is a clean no-op, and one registered `kit-shipped` — including the origin-unset default a manual registration leaves behind — is adopted in place: the origin is set to `incubated-in-repo` on the existing registry entry (no re-copy, no re-deploy) so `pkit sync` stops reconciling it against kit source. `--dry-run` shows the change without writing.

## 1.142.1 — 2026-07-07

### Fixed
- The changeset guard now exempts a release PR — a diff that is exactly `pkit release apply`'s footprint (version bumps, an updated CHANGELOG, and the consumed changesets deleted) passes with no `skip-changeset` label, because it is the release of already-declared changes, not a new surface change. A stray file outside that footprint keeps the guard firing, so the exemption never smuggles real surface through. ([#503])
- `pkit release merge`'s CI gate now dedupes a PR's check rollup to the latest run per check before deciding pass or fail. GitHub keeps every run of a check, so one that failed and was then re-run green (a fix-and-repush, a label re-trigger) previously left a stale failure that wrongly refused the merge; the gate now agrees with what `gh pr checks` reports. ([#504])
- **project-management 0.48.1** — The merge gate behind `merge-pr` and `done-work` now dedupes a PR's check rollup to the latest run per check before deciding pass or fail. GitHub keeps every run of a check, so one that failed and was then re-run green (a fix-and-repush, a label re-trigger) previously left a stale failure that wrongly refused the merge; the gate now agrees with what `gh pr checks` reports. ([#504])

[#503]: https://github.com/aleskalfas/project-kit/issues/503
[#504]: https://github.com/aleskalfas/project-kit/issues/504

## 1.142.0 — 2026-07-07

### Added
- Releasing a capability now keeps its compatibility claim current — the release step widens the released component's supported backbone range to the version it was released under, and a new `pkit release check-shareable` reports whether a capability is ready for another repository to consume. ([#494])
- **project-management 0.48.0** — The merge commands now refuse a pull request whose CI is red or still running, so an approved review can no longer land a failing build; a red check can be overridden deliberately with `--bypass-ci "<reason>"`, which records an audit note. ([#498])

### Changed
- The changeset-guard error now guides a decision-only PR to the right choice — a `none` changeset for a design-ahead decision, or a real one for a self-executing rule change. ([#497])

[#494]: https://github.com/aleskalfas/project-kit/issues/494
[#497]: https://github.com/aleskalfas/project-kit/issues/497
[#498]: https://github.com/aleskalfas/project-kit/issues/498

## 1.141.1 — 2026-07-05

### Fixed
- Filing an issue or PR from a project-kit source checkout no longer posts a spurious version-drift note — the tool now reports its version as the checked-out tree's version. ([#489])

[#489]: https://github.com/aleskalfas/project-kit/pull/489

## 1.141.0 — 2026-07-05

### Added
- Format problems in changeset and changelog files — an unknown category, an empty or malformed entry, or a broken changelog heading — are now caught before they land. ([#478])
- Completing a release PR now has its own checked command, so finishing a release no longer needs a hand-run raw merge.
- Each release now publishes a GitHub Release whose page shows that version's changelog, so you can see what changed at a glance. ([#485])

### Changed
- The changelog now follows Keep a Changelog and Common Changelog — plain, user-facing entries grouped by category, newest first. ([#477])

[#477]: https://github.com/aleskalfas/project-kit/pull/477
[#478]: https://github.com/aleskalfas/project-kit/pull/478
[#485]: https://github.com/aleskalfas/project-kit/issues/485

All notable changes to project-kit from `1.140.0` onward are recorded here,
newest first, following [Keep a Changelog](https://keepachangelog.com) with
[Common Changelog](https://common-changelog.org) language.

**Earlier history (before `1.140.0`) is not tracked per version** — see the git
tags and commit log for the full record. A few notable milestones from that
period:

- The declared, release-driven versioning system: version bumps are declared in
  changeset files and applied once at release time, keeping each tier's version
  independent and safe under concurrent work.
- The project-management workflow: file, validate, and move work items through a
  single validated command surface, with a review gate before anything merges.
- The adversarial review stack: separate critic, architect, methodology, and
  convention reviewers that check work before it lands.
- Steadier tooling: more robust parsing of reviewer verdicts and more faithful
  issue filing, among many smaller fixes.

## 1.140.0 — 2026-07-04

### Changed
- pkit now automatically runs the version each project pins, so one install works everywhere. ([#465])

### Removed
- The separate router shim — pkit installs one binary for everyone now. ([#465])

[#465]: https://github.com/aleskalfas/project-kit/pull/465
