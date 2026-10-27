# Trial run: install project-kit and four capabilities as a newcomer

25 October, 22:44–22:54. Scratch project `trial/demo-app`: a 4-file Python CLI (`greet`), `git init`, one commit, **no remote**.

## How it was run

- **pkit:** built from this checkout (main at 1aa50092, backbone 1.149.0) into `presentation/venv`. That is the same wheel a `uv tool install …@latest` builds, without the global install. The global `~/.local/bin/pkit` was kept off PATH.
- **Environment:** every command ran from `demo-app` in a clean environment: no `CLAUDE*` variables and the venv first on PATH. So pkit saw a plain shell, not an agent session.
- **Prompts:** commands ran without a terminal first. Where one deferred a question to a terminal, I answered it under a pseudo-terminal (`expect`).
- **Files:** raw output of each command is in `trial/raw/<label>.txt`. Timings are in `trial/raw/_index.tsv`, made by `trial/run.sh`.
- **GitHub:** nothing touched. No repository, label, issue or push. Only `pre-check` ran `gh auth status` (a read).

Times are wall-clock per command. Total pkit command time was about 134 s. About 77 s of that took the project from `init` to a green `pkit validate`. That excludes reading: the four capability READMEs are 3,700 lines.

## Step log

### 0. `pkit --help` (the README's "Verify"), 2.3 s, nothing asked
Lists 33 commands. The help text cites record ids (`[COR-021]`, `ADR-011`) that mean nothing to a newcomer.

### 1. `pkit init`, 8.7 s, nothing asked, exit 0
- **First line:** says where it installs ("git repository root — your current directory"). Good.
- **Output:** 110 lines, mostly `installed` / `created` file lines, and "Done." printed twice in the middle.
- **Next steps it prints,** some confusing:
  1. "Install pkit on PATH" with the `uv tool install` command, which you just used to run `init`.
  2. "Fill in `.pkit/capabilities/<name>/project/config.yaml`", before any capability is installed.
  3. "Backup at `.claude/settings.json.pre-pkit`": no backup exists, since there was no settings file before.
  4. Asks you to hand-edit `.gitignore` with 4 lines, including `!.claude/skills/`, and doesn't say why init doesn't write them.
- **Dangling include:** `CLAUDE.md` includes `@.pkit/rules/project.md`, which init does not create.
- **Settings:** `.claude/settings.json` gains 40 allows, including `Bash(ssh:*)`, `Bash(mv:*)`, `Bash(find:*)` and `Bash(gh:*)`. The README warns about this.

### 2a. project-management
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install project-management` | 7.5 s | deferred 1 | ok; deployed `pm` skill, `project-manager` and `pm-reviewer` agents |
| `pkit project-management ask-fixers` (at a terminal) | 1.9 s | no | "No fixer waits for an answer." |
| hand-write `project/config.yaml` (README example), then `pkit data validate …` | 0.9 s | no | ok |
| `pkit project-management bootstrap --dry-run` | 1.3 s | no | plans 15 labels; exit 0 |
| `pkit project-management pre-check` | 3.6 s | no | **FAILED**: 5 fail, 8 skip, 5 ok |
| `pkit project-management self-test --dry-run` | 1.1 s | no | prints its 6-step plan |

- **False alarm:** install ends with "1 question(s) … were not asked … Run each at a terminal: `pkit project-management ask-fixers`". Run at a terminal, that command has nothing to ask, because no installed capability declares a fixer yet.
- **No early warning about the missing repository:** `bootstrap --dry-run` shows `target repo: <unresolved>` and still exits 0. You learn you need a GitHub repository only at `pre-check`.
- **pre-check failures:** no bootstrap stamp, `gh repo view` failed, label list ×2, default branch. It also calls `workstreams:` in config.yaml, which the README's example uses, a "legacy config.yaml fallback". The config's reference comments mention "the 0.55.0 upgrade" while v0.54.0 is installed.
- **uv line leaks:** capability scripts print uv's "Installed 1 package in 2ms" before their own output.
- **Stopped here, needs GitHub:** `bootstrap` (labels; optional starter EPIC), a passing `pre-check`, `self-test` (creates and closes an issue and a milestone). Every pm verb except bootstrap, pre-check, migrate, adopt-existing and self-test refuses until bootstrap has run. That includes the `project-manager` agent ("Then use").

### 2b. software-engineering
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install software-engineering` | 8.3 s | no | ok; 4 agents: software-engineer, code-, security-, docs-reviewer |
| `pkit agents reconcile` / `--write` | 0.5 / 0.6 s | no | appends a commented `project-conventions` stub; clear "optional" message |

Nothing to configure. "would add 1 optional categor(ies)" reads oddly. The review panel works only through pm's merge gate on pull requests, so it needs GitHub too.

### 2c. software-analysis
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install software-analysis` | 11.9 s | deferred 1 | ok; created rule set `ANALYSIS` at `docs/rule-sets/analysis.md`; `analysis-author` skill, `analysis-resolver` agent |
| `pkit project-management ask-fixers` (terminal) | 3.9 s | **yes** | "software-analysis can keep your actors … true on its own … Turn this on? [Y/n]". Answered y; recorded in pm's config.yaml |

The question is plain and good. The rule set lands under `docs/` because both doc roots still default to `docs/` (see 2d). README adoption step 2, choosing each kind's parts with `validate --preview`, is a walkthrough for the skill in Claude. A CLI user has nothing to run for it.

### 2d. living-docs
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install living-docs` | 11.2 s | deferred 1 | ok; `docs-author` skill, `living-docs` agent |
| `pkit project-management ask-fixers` (terminal) | 2.0 s | **yes** | "living-docs can keep your pages true … Turn this on?". y |
| `pkit living-docs validate` | 1.9 s | no | 0 errors, 3 reports; "both documentation roots are 'docs' … onboarding separates them" |
| `pkit config set docs.internal tech-docs` | 1.2 s | **yes** (consent) | ok; also adds `docs/rule-sets` to `friction.places` so ANALYSIS stays found |
| `pkit living-docs new space user` / `technical` | 3.6 / 2.6 s | no | definitions under `tech-docs/living-docs/rule-sets/`; clear next steps |

- **Layout decision with no guidance:** on a fresh project both roots are `docs/`, and no space or page can be created until they differ. Neither the validator report nor the README says what to set. The only hint is a `tech-docs/` example in the CLI README's status section. Nested roots are refused, so `docs/internal` doesn't work.
- **Install order matters, and nothing says so:** because software-analysis went first, its ANALYSIS rule set stays under the **user** root, and the overlay's default ADR folder (`docs/architecture/decisions`) is under it too. Nothing flags either.

### 3. `pkit status` 5.9 s, `pkit validate` 8.9 s, nothing asked
- **`validate`:** 15 validators, **all checks passed**.
- **`status`:** 160 lines. Its terms (roles, points, fillers, "inert fail", "union · inert fallback") are heavy going for a newcomer.
- **Mislabelled agents and skills:** `status` lists the capability-deployed skills and agents (`pm`, `analysis-author`, `project-manager`, `code-reviewer` …) as "**user-managed (untouched by pkit)**". That is wrong-sounding.
- **Connections wired automatically:** 3 roles active, the fixers and doc-check points filled.

### 4. Analysis and a docs page
| Command | Time | Result |
|---|---|---|
| `pkit analysis new actor cli-user --name "Command-line user" --path src/greet/cli.py` | 3.4 s | recorded location `tech-docs/analysis`, wrote an overview page, stamped ACT-cli-user |
| `pkit analysis new use-case greet-someone --actor ACT-cli-user --title … --path …` | 2.9 s | stamped UC-001 |
| `pkit analysis validate` (unfilled) | 1.9 s | **exit 1, 16 errors**: every hint, reported twice ("still holds its hint" and "is empty") |
| (filled both by hand) `pkit analysis validate` | 1.9 s | **exit 1, 3 errors** |
| `pkit analysis overview`, then `validate` (and `--preview`) | 2.3 / 1.9 s | passes |
| `pkit living-docs new page docs/usage.md --space user --kind reference --reader user --title "Using greet" --path src/greet/cli.py --artefact UC-001` | 3.7 s | stamped; lists 3 placeholder lines |
| `pkit living-docs validate` (placeholders **still in**) | 3.1 s | **0 errors** |
| (filled) `pkit living-docs validate`, `pkit validate`, `pkit friction check` | 3.1 / 9.9 / 1.0 s | all pass |

- **The hint's own example fails:** the hints show `1. … 2. …` inline. Written that way, the Main path and Variants fail ("holds no numbered step"); they must be Markdown lists.
- **Overview needs a manual refresh:** the auto-written overview page goes stale on any edit, and the fix is a manual `pkit analysis overview` run.
- **Placeholders pass in living-docs:** a page full of template `<placeholders>` passes, because the `reference` kind requires only its H1. That is inconsistent with software-analysis, which fails every leftover hint.
- **Cross-capability touch:** the analysis actor automatically became a docs reader (`act-cli-user`).
- **The overview suggests a next step:** "No record states what the system is for yet. Write one with `pkit new decision` …".
- **No-remote warning everywhere:** most commands print "warning: the default branch 'main' is read from the local branch … (COR-054 point 2)".

### 5. Bonus: the stale-docs promise
I committed the setup (689 files, about 160,000 lines, for a 4-file project) and changed the greeting text in `cli.py`.
- **Flagged:** `pkit friction check` (1.3 s) flagged ACT-cli-user, UC-001 and `docs/usage.md`. The page's console example is now really wrong.
- **Answered:** `pkit friction revalidate … --outcome unchanged --because … --yes` (0.8 s) wrote an answer file.
- **Demo value:** this works and makes a clear demo moment.

## What worked smoothly
- **Install commands:** `init` and the four installs, 7–12 s each, with no errors and no surprises. Agents, skills and settings were deployed, and the capabilities wired to each other with no configuration.
- **Validation:** `pkit validate` is green right after setup. Validator messages say what to write and why.
- **Prompts:** the consent prompt of `config set` and the fixer questions are in plain language and explain their side effects.
- **Stamp commands:** `new space`, `new page` and `analysis new` are fast and say exactly what they wrote and what comes next.
- **Stale-doc detection:** a code change flags the documents resting on it, and `revalidate` answers them.

## What broke
- **pm cannot be set up without GitHub:** `pre-check` fails 5 checks, and every pm verb refuses until `bootstrap` has run against a GitHub repository.
- **Validation fails on freshly stamped artefacts:** stamped analysis artefacts fail until filled (by design), and the hint's own example form fails too.
- **Misleading output:**
  - the "question not asked" note after the pm install points to a command with nothing to ask;
  - `bootstrap --dry-run` gives no warning that there is no repository;
  - init's next steps name a backup that doesn't exist and an install you already did;
  - `CLAUDE.md` includes a `project.md` that doesn't exist.

Nothing crashed. The only non-zero exits were pre-check (no GitHub) and the analysis validator (unfilled artefacts).

## What needs GitHub
- **project-management:**
  - `bootstrap`: creates 15 labels and optionally a starter EPIC;
  - a passing `pre-check`: repository, labels, default branch, bootstrap stamp;
  - `self-test`: issue and milestone;
  - every issue and pull-request verb, `land-work`, the merge gate;
  - the `project-manager` agent ("File an EPIC for …");
  - `fix-drift`, which starts the granted fixers after a merge.
- **software-engineering:** its review panel and `docs-reviewer` act on pull requests through pm's merge gate.
- **The rest:** `pkit upgrade` (`git ls-remote` of the release tag) and `pkit report`. Neither was run.
- **Works fully offline:** software-analysis and living-docs: stamping, validating, the friction check and revalidating.

## Five roughest edges a live demo would hit
1. **project-management needs a real GitHub repository, prepared in advance.** Without one, `pre-check` prints 5 failures and nothing in pm runs, and `bootstrap --dry-run` doesn't warn first. A live bootstrap creates 15 labels on that repository.
2. **The documentation roots collide on a fresh project.** You must choose a layout (`pkit config set docs.internal tech-docs`) before living-docs can make a space, with no recommended value. Do it **before** installing software-analysis. Otherwise its rule set, and the default ADR folder, sit under the user docs root.
3. **Stamped analysis artefacts are red until hand-written.** Two files gave 16 errors, each reported twice. The hints' inline `1. … 2. …` example is rejected, and the overview needs `pkit analysis overview` after each edit. On stage, use the `analysis-author` skill in Claude or have the text ready to paste.
4. **Questions appear only at a real terminal.** Run from a script or an agent, each install defers the fixer question with a "not asked" note. After the pm install, the command that note names has nothing to ask. Run the installs at a real terminal, or pre-answer with `ask-fixers`.
5. **Output is long and dense.**
   - **Long:** `init` prints 110 lines, `status` 160 and `validate` 73.
   - **Repeated noise:** record ids like "(COR-054 point 2)" on almost every line, the no-remote warning on most commands, and uv's "Installed N packages" lines.
   - **Misleading:** `status` labels capability agents "user-managed".
   - **Scale of the commit:** the first commit is 689 files.
   - **For the demo:** filter output with `grep` or `tail`, or show it pre-recorded.
