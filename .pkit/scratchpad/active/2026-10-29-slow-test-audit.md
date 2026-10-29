---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-29
---

# The slow tests: which need a process, and which do not

The question: of the 2,065 tests that each took 1 s or more in a 4-worker run on main on 29 October (84% of the suite's 8,706 test-seconds), which need to start a process, and which check something the code could answer in the test's own process. Four read-only agents classified every one; nothing was run, so every "after" figure is an estimate. EPIC #2313 plans the rewrite; its foundation is #2314, and #2315 the walking skeleton.

| Class | Tests | Seconds now | After (estimate) |
|---|---:|---:|---:|
| process: needs the real process | 449 | 1,300 | 1,300 |
| direct: the same check in-process | 1,393 | 5,236 | ~250 |
| duplicate: repeats another test | 96 | 216 | 0 |
| other: slow for another reason | 127 | 543 | ~120 |

Each test's class, reason and target are in the four sibling files `2026-10-29-slow-test-audit-<area>.tsv` (test id, seconds, class, reason, target). The critic's review of the plan narrowed the rule: convert rather than delete, delete only exact duplicates, and enter a converted test through the command's own `main()`; so a "duplicate" below is a candidate, not a verdict.

## software-analysis

395 tests of 1 s or more (29 Oct, `-n 4`), 3,112 s, 30 modules. Each test's line is in `audit-software-analysis.tsv`.

| Class | Tests | Seconds now | After |
|---|---:|---:|---:|
| process | 31 | 226.7 | 226.7 (unchanged) |
| direct | 342 | 2,840.2 | 17.1 (0.05 s each) |
| duplicate | 16 | 37.5 | 0 (removed) |
| other | 6 | 7.4 | 2.7 |
| **All** | **395** | **3,111.8** | **≈ 247** |

If each direct test that still reads an adopter copy in-process costs 0.3 s instead of 0.05 s, the total is about 325 s (27 direct tests need no repository at all, and 56 need real git). That saves 2,790 to 2,865 s, about 90% of the area's time.

Process tests kept, one or two for each command: stamp (first stamp's stdout, mixed-endings refusal, record subcommand's warning), validate (`pkit validate` member), overview (writes, refuses), check-numbers (collision, base refusal), renumber (dry-run, no tty, --yes), propose (stop, cannot-explain), link, met-by (lists, no answer), check-pointers (fails, refusal), diagram, fill-readers and fill-use-cases (resolve, fail-closed), the fixers point, the 0.2.0 migration's three bash runs. Git-bound kept: 5 change-check cases in revisits and one shallow-fetch placement. The duplicates are revisits' other kinds and fields, whose identical link is already pinned in-process by `test_each_kind_declares_the_link`.

## Per module (seconds, after with direct at 0.05 s)

| Module `test_software_analysis*` | Tests | p/d/u/o | Now | After |
|---|---:|---|---:|---:|
| (main) | 34 | 2/32/0/0 | 343.6 | 11.7 |
| _overview | 15 | 2/13/0/0 | 321.1 | 37.4 |
| _analyses | 19 | 0/19/0/0 | 308.9 | 1.0 |
| _check | 53 | 1/52/0/0 | 307.6 | 5.8 |
| _numbering | 25 | 0/25/0/0 | 303.3 | 1.3 |
| _renumber | 9 | 1/8/0/0 | 208.2 | 53.5 |
| _numbers | 16 | 2/14/0/0 | 177.9 | 30.6 |
| _requirement_stamp | 13 | 0/13/0/0 | 139.0 | 0.7 |
| _resolver | 24 | 2/22/0/0 | 130.5 | 21.1 |
| _connections | 20 | 2/18/0/0 | 102.9 | 7.1 |
| _term_links | 17 | 1/16/0/0 | 98.9 | 3.6 |
| _records | 29 | 1/28/0/0 | 79.7 | 3.4 |
| _views | 15 | 0/15/0/0 | 66.2 | 0.8 |
| _append_only | 12 | 0/12/0/0 | 62.4 | 0.6 |
| _requirement_lists | 7 | 2/5/0/0 | 59.9 | 14.4 |
| _skill | 3 | 0/3/0/0 | 55.3 | 0.2 |
| _after | 8 | 0/8/0/0 | 50.3 | 0.4 |
| _revisits | 21 | 5/0/16/0 | 49.1 | 11.6 |
| _id_links | 3 | 0/3/0/0 | 41.9 | 0.2 |
| _structure | 6 | 0/6/0/0 | 40.1 | 0.3 |
| _shortfalls | 10 | 0/10/0/0 | 37.7 | 0.5 |
| _pointers | 11 | 3/8/0/0 | 30.0 | 7.5 |
| _project_structure | 5 | 0/5/0/0 | 26.9 | 0.2 |
| _record_links | 4 | 0/4/0/0 | 25.0 | 0.2 |
| _use_cases | 3 | 2/1/0/0 | 20.7 | 18.1 |
| _rule_set | 6 | 0/0/0/6 | 7.4 | 2.7 |
| _fixer | 2 | 1/1/0/0 | 7.0 | 4.5 |
| _diagrams, _migration_rule_set, _forms | 5 | 4/1/0/0 | 10.3 | 7.5 |

## Shared changes that unlock most of it
1. **One runner seam in `_lib/backbone.py`.** Every `run: Runner = subprocess.run` default is bound when the function is defined, and `stamp.stamp` and `check.check` pass no runner. Resolve the runner when the function is called, through one module-level runner. A test fixture can then send each `["pkit", ...]` argv to `project_kit.cli.main` through CliRunner, in the repository's directory, with the offline marker set. This one change makes the in-process targets callable: `stamp.stamp`, `revalidation.stamp_record`, `check.check`, `numbers.compare`, `pointers.check`, `renumber.plan` and `renumber.apply`, `reading.read`, `links.plan` (through `backbone.lookup`) and `overview.write`. It covers about 300 of the 342 direct tests.
2. **In-process helpers in `tests/analysis_repo.py`.** `stamped`, `new`, `link`, `fill` and the modules' `check()` would call the libraries through that runner instead of `run_script`. One example is `new.py`'s `_parser()` with `_stamp_artefact` and `overview.refresh`, without the prints. The scripts' `_lib` stays isolated as `load_lib` isolates it. The script modules (`new.py`, `propose.py`, `met-by.py`) are loaded from their paths. The templates' `prepare` functions (`prepare_seeded`, `_ground`, `_piloted`, `_chain`, `_flag`, `_leave_main`) and the per-test `two` fixture (4 stamps and a fill for each test) use the same helpers. Without that, a template's build cost only moves to whichever test asks first. Several listed times are mostly such a build.
3. **In-memory fixtures for the pure readers.** Build a `model.Analysis` and an `analyses.Listing` in memory, as `_analysis` and `_headed` already do in the overview module. `overview.render`, `overview.findings`, `diagrams.diagrams`, `readers.readers`, `append_only.compare`, `shortfalls.read` and `chain.*` then need no stamp at all.
4. The kept process tests stamp their setup too. With change 2, each runs only its one command as a process. That would take most of the 227 s, such as 53 s for renumber's test and 27 s for the number check's.

## What I could not judge
- I measured nothing, because no test was to be run. The cost of an in-process reading (`friction artefacts`, `repository base`, `rule-sets reach`) on an adopter copy is unknown, which is why the after column has a range: 0.05 s against 0.3 s.
- `_revisits` and `_rule_set` start no capability process. Whether their time goes to git or to the backbone's whole-adopter discovery needs a profile. So I left revisits' kept cases as process and estimated the rule-set cases at about 0.5 s.
- Two direct targets live in other capabilities, and I did not find their functions. One is living-docs' reader check, for `test_a_page_may_name_an_actor_as_its_reader`. The other is project-management's fixer-definition check, for `test_an_agent_that_holds_edit_starts_no_fixer`.
- The validator's human mode, which exits 1 on an error, has no slow process test left. It relies on the fast `test_the_check_is_reached_under_the_capability_and_its_alias`, which I did not read.

## friction

622 tests, 1,856.6 s (29 Oct, 4 workers). Estimated after: about 638 s, a saving of about 1,219 s. Read from the code only: no test was run. Line by line: `audit-friction.tsv`.

## Per class

| Class | Tests | Seconds now | After |
|---|---:|---:|---:|
| direct | 395 | 993.8 | 99.7 (95 at 0.05 s; 277 at 0.3 s; 23 at 0.5-0.8 s, which run the check twice) |
| process | 157 | 473.8 | 473.8 (unchanged) |
| other | 50 | 346.7 | 64.1 |
| duplicate | 20 | 42.3 | 0 |

Most direct tests already call the library in-process (`run_change_check`, `run_repository_check`, `plan_*`, `validate_friction`). Their time goes to git and to discovery over the installed adopter, not to a `pkit` process. Process tests are mostly the shape of history: merges (`-s ours`, conflicts, octopus, criss-cross), reverts, cherry-picks, renames followed, shallow clones, and `at` values written back. The rest are one or two wiring keepers per command, real resolver scripts, the CI gate and the project-management script's backbone calls.

## Per module, seconds now -> after (tests)

| Module | Now -> after | Module | Now -> after |
|---|---|---|---|
| test_friction_repository (140) | 438.2 -> 303.9 | test_friction_section_anchors (17) | 42.6 -> 9.7 |
| test_friction_check (129) | 301.9 -> 63.1 | test_friction_check_answer_files (26) | 42.0 -> 14.6 |
| test_friction_write (20) | 229.0 -> 19.0 | test_answer_files (21) | 37.1 -> 22.8 |
| test_friction_derived_links (18) | 143.5 -> 4.0 | test_friction_write_answer_files (10) | 23.0 -> 9.8 |
| test_friction_anchor_kinds (52) | 139.8 -> 26.4 | test_friction_report_body (8) | 19.8 -> 2.9 |
| test_pm_friction_answers (20) | 112.4 -> 44.7 | test_friction_move (10) | 14.8 -> 7.2 |
| test_friction_report (35) | 90.7 -> 52.4 | test_friction_shared_ids (7) | 12.5 -> 2.0 |
| test_friction_revisit (31) | 75.5 -> 9.3 | test_friction_artefacts (9) | 12.4 -> 3.9 |
| test_friction_point_anchors (21) | 51.5 -> 13.4 | test_friction_prune (4), _gate (2) | 6.2 -> 2.9, 6.1 -> 4.3 |
| test_friction_since (33) | 42.8 -> 16.4 | _validate (5), _tracking_issue (2), _received (2) | 5.4 -> 0.2, 5.1 -> 3.9, 4.3 -> 0.8 |

## Shared changes, by reach

1. **A template with the install committed.** Today `Timeline.start`, `_start`, `_commit_base` and the fixtures call `commit(files=None)` on an adopter with no commits. That stages the whole installed `.pkit/`, and `settled_commit` (`answers_in_files`) runs discovery over it, in every test. A module-level `prepare` that commits the install, `CONFIG` and `SOURCE` once per session, with `feature` branched and `Timeline` resuming at its day, is what lets the 298 direct tests that need git reach about 0.3 s: 783 s now. It would also take about 0.5 s off each process test, some 78 s, which the estimate leaves out.
2. **A slim, in-memory reading for writers and validation.** `validate_friction` takes no tree, and `plan_*`/`own_entry` walk the whole adopter with about 8 git calls a plan. This takes in the 190 s property test and the 95 tests at 0.05 s. `discover_artefacts(tree=...)` exists already, and `validate_friction` would need the same parameter.
3. **The 190 s test (`test_written_answers_read_back_identically_and_validate`).** Class other: 40 seeds × 4 random writes, each a full plan, a write, a read-back and `validate_friction` over the installed tree. With a repeat `plan_defer` after each defer, that is about 420 heavy calls at about 0.45 s. Since COR-062 the artefact's file is never written, so the random front matter only reaches discovery. Cheaper form, about 8 s: run all seeds through the pure layer (`friction_write.answer_file_text` -> `answer_files.read_answer_file` + `shape_findings`), keep the repository round trip for three seeds, and validate once per seed.
4. **Module prepares for shared histories.** These take in 15 repository tests (`_kept_base_side`, `_answered_then_reverted`, `_deferral_dropped`, `_revalidated_while_merging`, `_removed_by_a_merge`, `_old_line`), the report `_debt_history` and the report-body `_history`. Fold `since`'s author_delta cross-check (7 cases) into the sibling tests that build the same histories. Run one time spelling end to end; the other 16 spelling cases become unit cases of `parsed_at`.
5. **Stand-ins at the process boundary.** pm `friction_answers.py`: stand in `_refresh_base`, `_run_check` and `_discovery_at` (15 tests, 70.7 -> 3 s); each call now starts `pkit` two to four times. Anchor kinds: monkeypatch `friction_discovery.run_resolver` (18 tests, 47.3 s); three keepers keep a real resolver.
6. **Pure functions already there:** `friction_since._judge` (12 tests); `render_human`/`render_json` on a constructed result (check, since, debt); `resolver_answer` and `unresolved_kind_reason`; `artefact_parts`/`record_points` standings (8 point-anchor duplicates of `test_record_points.py`); `answer_files.liveness`/`StateAnswers`.

**Wiring keepers.** `check`: `test_json_document_shape`, plus the `--head` clean-checkout test. `check --all`: `test_exit_zero_in_enforcing_mode`, `test_json_document_shape`. `debt`: one test. `explain`: human and `--json`, plus `test_the_commands_named_clear_the_finding`, which runs explain's printed commands through the writers. `since`, `artefacts --at`, `revisit`, `defer`, `record-status`, `prune`: one each. Also the move migration, one or two per pm backbone call, and the CI gate (`test_a_stale_page_fails_the_pull_request_and_its_revalidation_passes_it`).

## Could not judge

- **Nothing measured.** How each test's time splits between commits, discovery and check runs is inferred. The 0.3 s floor assumes change 1, and a test that runs three or four checks will sit nearer 0.6 s. Near-equal parameters took 10.1 s and 3.8 s (`test_a_record_edited_and_re_answered_then_both_reverted`): noise.
- **No seam for a base without git.** `run_change_check` cannot take its base as an in-memory tree and diff: it reads `CommitTree`, `read_diff` and the answers' history. So no change-check test goes below about 0.3 s without such a seam.
- **Derived links.** Their 43.5, 39.7 and 18.7 s are the software-analysis templates (`_cited`, `_kinds`, `_domain`), paid by whichever test asks first. `_domain` and `_kinds` are shared with `test_software_analysis_term_links.py`, so only `_cited`'s cost leaves the suite; the rest moves there. The module's real suite saving is nearer 85 s than 140 s.
- **Renames inside one diff** are classed direct with git in the check modules; the one repository-check case stays process. A judgment call.
- **validate_friction at 0.05 s.** Whether it reaches that without the backbone install is open: it reads the container schema and the ownership module from the install.

## living-docs

238 tests of 1 s or more in a 4-worker run on 29 Oct, 686 s, in 6 modules. Each test is classed in `audit-living-docs.tsv`. Almost every one starts the capability's validator (`validate.py --json`) or stamp (`new.py`) as a process, and that process starts `pkit` 2 to 8 more times (`friction artefacts`, `rule-sets reach`, `connections resolve`, `refs lookup`, `docs record-location`, `config set`). Most tests assert a finding, a summary line, a `Refused` or a written file. All of these are function results.

| Class | Tests | Seconds now |
|---|---:|---:|
| process | 9 | 57.3 |
| direct | 214 | 565.4 |
| duplicate | 11 | 33.6 |
| other | 4 | 30.2 |

Process tests kept, per command:
- **validate**: as a member of `pkit validate`, and its human view.
- **new**: the page form's stdout, and the space form's run of `pkit config set`, whose output shares the terminal.
- **resolve-source**: the source kind end to end, and its exit-1 no-answer path.
- **fill-doc-check**: the point's filler, the pm doc-mapping gate, and git called only inside `pkit`.

| Module | Now (s) | After (s) |
|---|---:|---:|
| test_living_docs_spaces.py | 245.2 | 14.7 |
| test_living_docs_new.py | 183.5 | 25.2 |
| test_living_docs_sources.py | 100.3 | 17.1 |
| test_living_docs_mentions.py | 85.3 | 1.1 |
| test_living_docs_points.py | 71.0 | 18.5 |
| test_living_docs_agent.py | 1.2 | 0.3 |
| **total** | **686.5** | **76.8** |

How the "after" column is counted: direct tests at 0.05 s each, duplicates removed, process tests unchanged. The four "other" tests are estimated one by one: 8.0, 0.05, 0.4 and 0.3 s.

## Shared changes that unlock it

1. **The `pkit` reads, answered in this process (unlocks 150 direct tests, 409 s).** Two parts are needed:
   - **A seam for the places reading.** `spaces.checked` already takes `read`, `reach` and `look` as parameters, and the stamp passes them through. The places reading is the exception: `_classify` and `pages` call `read_artefacts(root)`, with the subprocess runner fixed when the function is defined. Add an `artefacts=` parameter beside the other three, or bind each `_lib` reader's `Runner` at call time.
   - **A test fixture.** It answers `["pkit", ...]` with `CliRunner().invoke(main, argv[1:])` in the given cwd and returns a `CompletedProcess`. The argv contract is still checked; only the process start is skipped. Precedents: `tests/pull_request_backbone.py` `in_process`, and `_off_a_terminal` in `test_handed_over_writers.py`.
   - **What it unlocks.** The validator tests, the stamp tests and the readers tests can then call `spaces.checked`, `stamp.stamp_page` and `stamp.stamp_space` directly.
2. **`load_lib(capability, *names)` (unlocks 64 tests, 157 s, with change 1 or alone).** This generalises `tests/analysis_repo.py`'s `load_lib` so that `spaces`, `stamp` and `mentions`, which import `_lib` by that name, can be imported in-process.
   - It retires the driver subprocesses that exist only to import `_lib`: `PROBE`, `KINDS_DRIVER` and `SCANDIR_REFUSED`.
   - With it, the pure tests need no adopter at all. These are `formats.headings`, `departures` and `diagrams`, `source_layout.answer`, the stamp's `_config_text`, `_new_file` and `_internal_folder`, and `mentions.read` with a lookup stub.
3. **For `test_living_docs_sources.py` only: route the `source` resolver in-process.** Monkeypatch `fd.run_resolver` so that the backbone's friction checks and `rs.validate_rule_sets` resolve `source` anchors through `source_layout.answer` and `fd.resolver_answer`. Two process tests keep the real resolver's contract.

Change 1 unlocks the most. It is one parameter in the living-docs `_lib` plus a fixture of about 15 lines.

## What I could not judge

- **The 0.05 s figure is optimistic for 150 tests.** A direct test that keeps an adopter copy makes 3 or 4 in-process backbone reads per `spaces.checked`, and the sources tests keep git commits and the in-process friction checks. At about 0.3 s each, the total after is about 130 s, not 77 s.
- **`fill-doc-check`'s `reading()` runs its three reads in threads.** `CliRunner` swaps `sys.stdout` and is not thread-safe. Its direct tests therefore call `doc_check.has_commit`, `read_friction` and `obligations` one by one, or stub the three reads.
- **I did not check whether the CLI install matches the test-helper install.** `test_a_fresh_project_gets_one_layout_whatever_order_it_installs_in` installs through `pkit capabilities install`. Only if that does what `AdopterRepo.install_capabilities` does (for #2084's layout) can the two orders become templates, at about 1 s instead of 8 s.
- **A judgement call on the validator's human view.** I kept `test_a_page_left_unanchored_counts_unless_its_block_gives_an_accepted_reason` as the process test for it. With only one end-to-end test per command, it would move to `validate.main()` with capsys, saving 3.1 s.
- **I could not confirm the backbone's in-process caches are safe.** The `lru_cache`s I saw in `friction_discovery` are keyed by text and patterns, not by path, so a write between two reads looks safe. I did not check every read command for state held per process.

## other

810 tests of 1 s or more (29 Oct, `-n 4`), 1,641 s together, 93 modules; one line each in `audit-other.tsv`. Judged by reading the tests and the code they reach; nothing was run. After: direct 0.05 s, duplicate 0, process unchanged, other as each line's cheaper form says (unchanged where it says "profile first").

| Class | Tests | Seconds now | After |
|---|---:|---:|---:|
| direct | 442 | 837 | 22 |
| process | 252 | 542 | 542 |
| other | 67 | 159 | 49 |
| duplicate | 49 | 103 | 0 |
| **all** | **810** | **1,641** | **613** |

Process, by reason: about 120 tests (210 s) are git itself (merge-base, upstreams, shallow clones, renames, history read by the friction engine); the rest are scripts run as a whole (check.sh, migrations and their replay, the adapter's deploy scripts, install and upgrade runs, `uv build`, real uv), process boundaries (deadlines, kills, signals, a child's environment, the system python3, a pty), and one or two wiring tests kept per command.

| Module | Tests | Now (s) | After (s) | process / direct / duplicate / other |
|---|---:|---:|---:|---|
| `test_default_branch.py` | 29 | 89 | 76 | 26 / 3 / 0 / 0 |
| `test_pm_doc_check_point.py` | 22 | 88 | 9 | 2 / 17 / 3 / 0 |
| `test_pm_ruled_artefacts.py` | 26 | 73 | 16 | 4 / 11 / 11 / 0 |
| `test_process_cascade_engine.py` | 24 | 64 | 1 | 0 / 24 / 0 / 0 |
| `test_release_check.py` | 45 | 58 | 17 | 12 / 29 / 4 / 0 |
| `test_latest_tag.py` | 16 | 53 | 24 | 6 / 8 / 2 / 0 |
| `test_process_engine.py` | 32 | 52 | 6 | 2 / 28 / 2 / 0 |
| `test_process_health.py` | 24 | 52 | 7 | 2 / 22 / 0 / 0 |
| `test_upgrade.py` | 32 | 52 | 34 | 18 / 13 / 1 / 0 |
| `test_pm_land_work.py` | 33 | 51 | 18 | 5 / 16 / 0 / 12 |
| `test_rule_reach.py` | 26 | 50 | 20 | 8 / 17 / 1 / 0 |
| `test_self_host_documentation.py` | 9 | 49 | 13 | 3 / 1 / 0 / 5 |
| `test_pm_closure_cascade_foreign_child.py` | 15 | 49 | 7 | 1 / 14 / 0 / 0 |
| `test_decisions_check_diff.py` | 29 | 43 | 7 | 3 / 26 / 0 / 0 |
| `test_pm_fixers.py` | 19 | 43 | 18 | 6 / 13 / 0 / 0 |
| `test_pm_check_doc_mapping_fixtures.py` | 17 | 37 | 12 | 1 / 8 / 0 / 8 |
| `test_process_blocked_engine.py` | 23 | 36 | 1 | 0 / 23 / 0 / 0 |
| `test_migrations_check.py` | 18 | 35 | 13 | 6 / 12 / 0 / 0 |
| `test_check_script.py` | 18 | 33 | 33 | 18 / 0 / 0 / 0 |
| `test_decisions.py` | 20 | 33 | 14 | 9 / 2 / 9 / 0 |
| the other 73 modules | 333 | 604 | 265 | |

## The shared changes that unlock most of it

1. **An in-process predicate runner** (about 160 tests, 300 s to 8 s). Every process-engine test, the pm closure-cascade tests and the classifier tests pay one python interpreter per predicate per resolution, because `PredicateRunner._invoke` runs each registered command through `run_command`. A shared fixture that replaces `_invoke` with an in-process table already exists for pm (`tests/pm_lifecycle_world.py`, `answer_from_tracker`); generalise it to fixture predicates and to pm's predicate scripts called through their `main()`. Keep the few tests that pin the run's ending (exit code, stderr tail, the system python3).
2. **Capability scripts' `main()` in-process with their backbone readers stubbed** (about 50 tests, 140 s to 3 s). check-doc-mapping, the fixer verbs, close-issue's refusal, done-work's composition and `ruled_altered` already take a `run=`/`gh_run=`/`ruled_altered=` seam; the tests start the script, and inside it `pkit connections resolve`, `pkit friction check`, `pkit rule-sets altered` and a fake `gh`, as processes. Keep one end-to-end test per verb.
3. **Split pure judgments from git reads** (about 110 tests, 170 s to 6 s): `release._correction_problem` and the range-key comparison, `release_writes` patterns, `GuardResult.ok`, `decisions_check_diff._points`/`_taken_points` (or `check` over in-memory `_Tree` states), `migrations.released_targets`/`number_clashes`/`migration_target`, `prose_lint.lint_text`, `rule_set_reading.brought_under` over `rs.reach` of two in-memory states, land-work's `_refuse_moved_base`/`_grants_moved`/`_records_moved`. Some need a small refactor: the judgment is inline beside the `git` call today.
4. **Remove the 49 duplicates** (103 s): mostly pm tests re-proving the backbone's answer through a subprocess (`rule-sets altered` cases already in `test_rule_reach.py`), per-namespace or per-kind parameters of one path, and exempt verbs the coverage guard already pins.
5. **Cheaper seeds and shared readings** (other): seeded-analysis templates written as files rather than stamped through the SA scripts (about 37 s charged to two first tests), one module-scoped `validate_friction(REPO)` / `validate_rule_sets(REPO)` in `test_self_host_documentation.py`, one run per fixture in `test_pm_check_doc_mapping_fixtures.py`, the stub fixture in `test_install.py` (9 s), stubbed endings for 1 s timeouts, and in-process matrices for the permission hook.

Not changed by these: the 120 git tests. A session-built seed repository copied per test (as the adopter templates are) would cut their setup — `test_release_check.py`'s `_make_repo` and `test_default_branch.py`'s `_repo`/`_bare` rebuild the same few commits per test — but not their own git reads.

## What I could not judge

- No line is `unjudged`. Eighteen `other` lines (23 s) say "profile first", and four more (5 s) see nothing cheaper: in-process pm verb tests (`test_pm_move_issue.py`, `test_pm_promote_issue.py`, `test_pm_review_work.py`, `test_pm_start_work.py`, `test_pm_show_tree.py`, `test_config_validate.py`, and the `pm_lifecycle_world` journal and cascade tests) whose second is not visible in the code; a first-in-worker import of move-issue or repeated YAML loading is likely, but only a profile can tell.
- A test's seconds include any session template its worker built first (41.8 s in `test_default_branch.py`'s three-reader test, 17 s and 19.9 s in the handed-over-writers and held-records tests). Reclassifying the test moves that cost to whichever test asks next; only a cheaper template removes it.
- The 0.05 s for a direct test is optimistic where the direct form still needs a small git repository or the refactor in point 3; and where I named a `_private` function, the test may prefer the public function once it is split.
