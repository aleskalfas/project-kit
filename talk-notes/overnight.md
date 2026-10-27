# 27 October: state of play

Updated through the day. Each item says what it needs.

## Waits for you (coming back once built and reviewed)

1. **[#2224](https://github.com/aleskalfas/project-kit/pull/2224) — release-candidate records** (choice 8, one acceptance): PRJ-002, PRJ-004, new ADR-072, refinements of ADR-049/063/064/065, and the `CLAUDE.md` sentence. Being updated to your seven choices.
2. **#2234 — fixers run only when a person starts them, watched** (DEC-056 and ADR-066 edits). Before the release.
3. **[#2240](https://github.com/aleskalfas/project-kit/pull/2240) — guardrails see through wrappers and git configuration** (#1990, ADR-025 edit).
4. **#2214 — ADR-041 and the ownership code agree** (ADR-041 point 7 edit). After the release.

## Decided today

- **Release candidates (#2211):** a candidate's versions live only in its tag; the `rcN` suffix on backbone and moved components; a candidate raises no floor; candidates run their release's migrations, re-runs safe, a shipped script corrected only by a new one; `pkit upgrade --pre` opts in, a plain upgrade never moves onto a candidate; cut through the existing release workflow with a "pre-release" input (`pkit release --pre`), tag only, GitHub pre-release; the final is cut from the last candidate's commit and a PR brings its versions into main, main never frozen. Follow-up after 2.0.0: dev versions on main (`2.0.0.dev0`).
- **Releases only by hand:** the weekly run is removed (#2233); the stale release PR #800 closed (it had blocked every weekly run since 31 August).
- **The delegate:** the project manager decides answers no change owes (#2230); you are no longer asked about answers.
- **Fixers:** on request and watched, like the reviewers (#2234); the confined unattended form waits (#2225: Claude Code 2.1.310 needs an adapter fix).
- **#2026:** option B, the adapter tells every agent the workspace replaces the harness's scratch directory.
- **#1990:** yes and yes. **#2214:** fix the code for point 1, record points 2 and 3. **#2131:** anchor cycles resolved pair by pair, after the release. **#1678:** scope approved, built after #1990. **#2175** and #2166 closed (superseded by COR-066).
- **The landing guard (#2231):** DEC-055 point 6 accepted; landing refuses a merge whose combination with main leaves a document stale.
- **Before the release:** #2207, the prune command and retiring `friction resolve`.

## Landed today

- #2194 (COR-065, COR-066, COR-067), #2169 (records hygiene), #2219 (rollback = revert the upgrade's commit), #2227 (six stale pages answered), #2215, #2216 (page anchors), #2220 (timing test), #2210 (fixer grant), #2205, #2208 (answers in answer files), and others overnight.
- #2197 (DEC-004), #2230 (delegate), #2231 (landing guard), #2233 (releases by hand), #2235 (#2026, the workspace note for every agent).
- Landing now: #2237 (#2207, `friction prune`, `friction resolve` retired). Then #2239 runs the prune once on main.
- #2240 (#1990): reviewers asked for six wording fixes, being made; then back to the reviewers, and to you for the ADR-025 edit.

## The talk

- [Building blocks](building-blocks.md): block 1 (decisions), block 2 (rules, a draft for you to react to).
- [Working notes](working-notes.md), [the trial install](trial-run.md), [the demo run plan](demo-run-plan.md).
- The release-candidate path is the demo's install: `rc1` once #2224 is accepted and its build lands.
