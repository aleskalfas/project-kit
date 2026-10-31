# Tests

`uv run pytest -q` runs the suite; `./scripts/check.sh` runs it together with the
other gates (see [CONTRIBUTING.md](../CONTRIBUTING.md) "Running checks").

## Running the suite

**While you build, run the tests of what you changed.** The full suite — some
21 300 tests — is the pre-push hook's and CI's to run, not a builder's (the
project's rules, `.pkit/rules/project.md`): run the test modules for the files
you changed, `uv run pytest -q tests/test_<module>.py ...`, and the fast gates,
`uv run pkit validate`, `uv run pkit friction check`,
`uv run pkit migrations check-diff`, `uv run pkit decisions check-diff` and
`uv run pkit release check`.

**CI skips the suite where only answers changed.** On a pull request whose only
changes since its most recent full run, which passed, are answers, CI runs the
short check: the aggregator without the suite (ADR-067, and
[CONTRIBUTING.md](../CONTRIBUTING.md), "Running checks"). Of the suite, it runs
only the tests marked `answers`.

- **Mark a test `@pytest.mark.answers`** when what it asserts can change with
  the repository's own answers, the answer files in
  `.pkit/project/friction/answers/`, beyond what `pkit validate` checks. An
  example is a test that every declared place has a revalidation in an answer
  file.
- **No mark is needed** for a test that only runs a validator over the tree.
  The short check runs `pkit validate` itself.
- **Unmarked,** such a test is skipped where only answers changed. An answer it
  would reject passes the short check, and the full run on `main` finds it after
  the landing.

**The full suite runs in parallel.** `scripts/check.sh` — the one command the
pre-push hook and CI's full run call — runs it in
[pytest-xdist](https://pytest-xdist.readthedocs.io/) workers, `-n auto` (one per
CPU), and then the tests marked `serial` on their own, in one process, in the
same step. `PKIT_TEST_WORKERS` sets the number of workers; `0` runs the whole
suite in one process. The two passes by hand:
`uv run pytest -q -n auto -m "not serial"`, then `uv run pytest -q -m serial`.
A plain `uv run pytest -q` still runs everything in one process, the `serial`
tests included.

**CI splits a full run across three machines** (ADR-078). The hook runs the
aggregator whole, on one machine. CI runs it as three parts side by side, each
a job of its own, which the aggregator defines:

- **two slices,** `./scripts/check.sh --shard 1/2` and `--shard 2/2`. Each runs
  its share of the parallel pass, in parallel workers, and nothing else;
- **the remainder,** `./scripts/check.sh --rest`: every other line of the
  aggregator, with the tests marked `serial` in the test step's place. No other
  worker shares its machine, as the mark asks.

**How the suite is cut.** A slice reads the tests left after the `serial` mark's
filter, in the order pytest collects them. It cuts them into runs of
consecutive tests, where the running time crosses each half of the total
(`tests/slices.py`). So every module stays in one slice, but the one a cut falls
in.

- **The times** come from the table of test times, `tests/test_times.json`: the
  time each test took in a full run in CI. A test the table lacks weighs the
  median, and an entry no test bears is ignored. A stale table costs time, never
  coverage, since the cut covers the tests collected.
- **The same cut in every slice.** It reads only the tests and the table, both
  fixed by the commit, so a slice run again by hand runs the same tests, with the
  same tests around them. A failing slice's summary says how.
- **What a slice reports.** It ends by printing its report: a digest of the tests
  collected, in order, with the table and the count of slices, how many tests it
  collected, and how many its share held. `checks` fails unless the slices report
  one digest and one count, and their shares add up to it.
- **An empty share fails.** A slice whose share holds no test fails, where the
  aggregator's passes of the tests marked `serial` and `answers` pass with none.
- **By hand:** `uv run pytest -n auto -m "not serial" --shard=1/2` runs a slice's
  tests alone. The option takes one token.

**Keeping the table.** The project's maintainer refreshes it, from CI's own times,
never a contributor's machine.

- **When:** a full run on `main` is held to twenty minutes. Refresh the table when
  full runs on `main` take longer, or when a tenth of the tests collected are
  missing from it. The summary of `checks` shows both: each part's time, and how
  many tests collected the table lacks.
- **How:** `uv run python -m tests.slices table` writes it from the times each
  slice of the newest full run on `main` that passed kept as an artifact of the
  run, `test-times-<i>-of-<N>`. `--run <id>` names another run. Review it like any
  change. No run writes the table, so a pull request's run cannot change what
  later runs read.

**The parallel pass ends by printing its 30 slowest tests** (`--durations=30`),
in every run: in a local run's output, and in the log of each slice's step in
CI.

**A test that cannot share the machine with other workers** is marked
`@pytest.mark.serial`. Make it worker-safe instead when you can — whatever it
writes under `tmp_path`, every change to the environment or the working
directory through `monkeypatch`, no fixed path, port or order of tests it relies
on. Mark it only when it needs something every worker shares, and say what in
a comment beside the marker. The serial tests today share the processor: each
bounds a run by a second or a few seconds of wall-clock time and needs
interpreters started inside it, which a machine busy with other workers misses.
A test whose short bound is incidental gets the default bound instead.

**At most two full suites run at once on a machine.** Before its test step,
`check.sh` takes one of two slots, lock files under
`${XDG_CACHE_HOME:-~/.cache}/pkit/`, and frees it after. A third run waits,
printing the two runs it waits for — process, checkout and start time — and goes
on when one of them ends, however it ends: a slot is an `flock` lock, which the
operating system releases when the run holding it ends, killed included. When the slots cannot be
opened (a read-only cache directory, a sandbox that does not allow it), the step
says so and runs without the limit. `tests/test_check_script.py` pins both the
passes and the slots.

**A test calls the code in its own process.** A process of `pkit` or of a
capability script costs a third of a second to a second, and most tests check
what the code answers, not that a process ran it (#2313). So a test keeps a real
process only where the process is the point. The rule below says which tests do,
and how a test is converted.

The rule: which tests keep a real process, and how one is converted (#2314,
choice 2).

1. Per command, one or two end-to-end tests keep a real process. So do one test
   per output mode, and one per registered validator, filler or resolver, run
   through `pkit`'s runner.
2. A converted test enters where the process test entered. That is the script's
   `main(argv)` in the test's own process, or a public function where the
   assertion is on its result, and never a private helper alone.
3. Convert a test rather than delete it. Delete only an exact duplicate, and name
   the test that keeps its assertion.
4. A template is built by the real code in the test's own process, never written
   by hand.
5. Each slice proves its conversion with a planted-bug spot-check against its old
   tests and its new ones.

**A kept process test is marked with its reason**:
`@pytest.mark.process("<why the process is the point>")`. A guard, the autouse
fixture `process_starts`, counts each process of `pkit` or a capability script
the test starts, and fails a test that starts one without the mark. It counts
from the start itself, so the count is the same on every run. It does not count
what an adopter template's build starts, nor what a test of the runner asks of
`run_command` itself.

**The guard holds every module but those in its baseline**,
`tests/process_guard_baseline.txt`: the modules left as they are when #2313
closed, under the reason each stays (#2329). A change that marks or converts a
module's starts takes it out, and no module is ever added. So a new module is held
from its first test.

**What a converted test calls** lives in `tests/in_process.py`:

- `load(capability, *names)` loads a capability's scripts, such as `validate.py`,
  and its `_lib` modules in the test's own process. Each capability's `_lib` is
  kept apart in `sys.modules`. While a call loads, no `_lib` folder is on the
  import path and no `_lib` module imported by path is in `sys.modules`. Given
  `lib=`, a `_lib` package the test already imported, it loads the scripts into
  that package instead, so they run with what the test patched there.
  `run_main(script, *args, cwd=...)` runs a script's `main` as its process ran.
- `route_pkit(monkeypatch, backbone)` answers every `pkit` call of a capability
  with the backbone's CLI in the test's own process. Each capability makes its
  calls through one private function, `_lib.backbone._run`, looked up when
  called, and the route replaces only that function. The argument lists and the
  documents are unchanged (ADR-057 point 1). project-management's streaming
  starts (`agent_runs`, `merge_queue`) and its top-level scripts' calls do not
  go through it, and its route takes the keywords its calls pass (`timeout`, an
  `env` with routing off, UTF-8 decoding with `replace`), which the in-process
  `pkit` itself refuses.
- `InProcessPkit`, the in-process `pkit`, answers as a process does. It gives a
  `CompletedProcess` with its exit code and standard error apart, from the
  working directory given, in the environment the runner gives a query. An
  exception is exit 1 with its traceback, a keyword it does not model is
  refused, and the backbone's caches are cleared before each call.
- `start_in_process(monkeypatch)` starts in the test's own process each command
  the backbone's runner starts for a component, such as a validator. The
  runner's one lookup still resolves the command, so a broken registration still
  fails. Given `lib=`, it loads each script of that `_lib`'s capability into it.
  `tests/pm_lifecycle_world.py` starts project-management's predicates so.

**A test leaves the import path as it found it.** A fixture that puts a folder on
`sys.path` takes it off after its tests, through `monkeypatch.syspath_prepend` or
its own teardown. A folder left on the path outlives the test, and every later
test on its worker imports from it. A capability's `_lib` folder left so made
eleven of `friction_answers`' tests start a real `pkit` on one of CI's workers
(#2353).

**The spot-check** is `uv run python scripts/spot_check.py BUGS --base REF TEST...`.
It plants each bug the JSON file BUGS lists, one at a time, and runs the tests as
REF holds them and as they are now. It exits 1 when the new tests miss a bug the
old tests caught. Where a change converted a helper module the old tests share,
`--old-helper FILE` puts it at its version at REF for the old run alone. The bugs
of #2315 are in `tests/spot_checks/`.

**The slowest modules**, by the time their tests take together, setup included,
measured again once #2313's slices had merged (#2329). CI's seconds are the median
of three full runs on `main` on 30 October, from the times each slice keeps
(`test-times-<i>-of-2`). A slice's runner has four workers. In those runs the
parallel pass summed 3 600 to 4 900 s of test time. The local seconds are one run
of the aggregator's two passes, `-n auto`, on 31 October, on a 12-core Mac other
builders were sharing. That run summed 31 250 s of test time and took 53 minutes
on the clock.

| Module | Tests | CI, s | Per test | Slowest test | Locally, s |
|---|---:|---:|---:|---:|---:|
| `test_software_analysis_check.py` | 61 | 164 | 2.7 | 16.4 | 823 |
| `test_software_analysis_overview.py` | 18 | 141 | 7.8 | 19.9 | 1 067 |
| `test_living_docs_new.py` | 56 | 121 | 2.2 | 34.8 | 486 |
| `test_software_analysis.py` | 51 | 117 | 2.3 | 8.1 | 1 432 |
| `test_living_docs_spaces.py` | 180 | 117 | 0.6 | 7.7 | 340 |
| `test_friction_repository.py` | 162 | 109 | 0.7 | 1.4 | 2 376 |
| `test_self_host_documentation.py` | 41 | 100 | 2.4 | 42.1 | 121 |
| `test_friction_check.py` | 148 | 87 | 0.6 | 1.5 | 1 613 |

**What is left is mostly `git`.** #2313's slices took most starts of `pkit` and of
the capability scripts out of the slow tests, and measured each area on #2313. A
friction or analysis test still commits and reads its history through tens of
`git` processes. On a Mac other builders share, each takes a third of a second or
more. So these modules take five to over twenty times as long there as in CI.

A software-analysis test stamps, links and writes the overview in its own
process, through `tests/analysis_repo.py` (#2319). A script a test runs through
`run_script`, such as the number check, runs as a process, and the test carries
the `process` mark with why. What its tests share is built once ("Built once,
copied for each test", below). A test that stays slow says why in a comment above
it.

## Type checking

**The tests are type-checked in pyright's standard mode and gated outright**
([PRJ-010](../.pkit/decisions/project/PRJ-010-type-checking-mode.md)): the
check aggregator's `types` step fails on any finding in a test, with no baseline
to read or update. Standard mode asks for no annotation, fixtures included; it
reports the defects a run can miss — an optional value used unchecked, an
attribute read off a union, an argument of the wrong type. Narrow what a test
reads (`assert value is not None`) and type a helper for what it is handed. Check
a module while you write it with `uv run pyright tests/test_<module>.py`, which
reads the same configuration; `uv run python scripts/pyright_ratchet.py` runs
the whole step.

**A suppression names its rules and gives its reason on the same line.** It is
for code that is ill-typed on purpose, such as a test handing a function a type
its signature rules out to reach the check under test:

```python
assert audit.short_sha(None) == "unknown"  # pyright: ignore[reportArgumentType] a head that could not be read arrives as None
```

The step refuses a `# pyright: ignore` that names no rule or gives no reason, a
`# type: ignore` (pyright is told to honour none), and a file comment that sets
the mode or a rule's severity (`# pyright: basic`). A rule is relaxed for the
tests only in `pyproject.toml`'s `[tool.pyright]` table, with its reason beside
it.

**The package is held to strict mode through a ratchet instead**: its findings,
counted per file and rule, may not exceed the committed baseline,
`scripts/pyright-baseline.txt`. When the step says the package has fewer than
the baseline admits, commit the change and run
`uv run python scripts/pyright_ratchet.py lower`, which writes only lower
counts; commit the baseline it writes in the same pull request.
[CONTRIBUTING.md](../CONTRIBUTING.md), "Running checks", has the rest — what to
do when a change raises a count, and the only causes for raising the baseline.

## The adopter-repository fixture

Most tests that need "a project with the kit installed" should not `git init`
and call `install_kit` by hand. `tests/adopter_repo.py` provides one builder
and `tests/conftest.py` exposes it as three fixtures:

| Fixture | Gives you | Reach for it when |
|---|---|---|
| `make_adopter_repo` | A factory: `make_adopter_repo(capabilities=(), history=False, chdir=True, root=tmp_path, prepare=None, fresh=False)` returning an `AdopterRepo`, a copy of a template built once per session (below). | A test drives the CLI or the Python API against an installed adopter. `make_adopter_repo()` with no arguments is the bare shape — `git init`ed `tmp_path`, backbone installed, adapter shell primitives stubbed, cwd moved there, **no commits** — that the per-file `installed_target` / `kit_target` fixtures wrap. |
| `adopter_repo` | `make_adopter_repo(history=True)`: the same adopter with the scripted history committed; `adopter_repo.history` holds the SHAs. | A test needs real git state — validators that read history, the friction engine (COR-050), anything tracing a front-matter field across commits. |
| `committed_adopter` | `make_adopter_repo(prepare=commit_install)`: the bare shape, its install committed on `main` in one commit dated `INSTALLED_AT` (`tests/friction_documents.py`). | A test commits a base of its own, as the friction tests do. It then commits only its own files, never the whole installed `.pkit/` (#2320). |

Outside a fixture (a plain helper that takes `tmp_path` and `monkeypatch`), call
`build_adopter_repo(root, monkeypatch=monkeypatch, ...)` directly; it builds the
adopter afresh on every call.

A capability script under test that reads through the backbone — `pkit
connections resolve`, `pkit friction check`, `pkit friction artefacts` — needs
a `pkit` on PATH. The
`pkit_on_path` fixture puts the real CLI under this interpreter first on PATH,
bypassing the entry-point router, so the read never reaches `uv` or the
network. Point the script's own `uv run --script` shebang at `sys.executable`
in the adopter copy for the same reason.

Every test starts outside any run of the backbone's command runner: an autouse
fixture, `outside_any_run`, clears `PKIT_COMMAND_DEADLINE`,
`PKIT_COMMAND_STRAYS` and `PKIT_RUN_CACHE`, so a suite started by a command the
runner runs behaves as one started from a terminal. A test that needs a run
inside a run starts one for real, through `run_command` (the lifecycle README,
"A run inside a run").

### Built once, copied for each test

**Each shape of adopter is built once per session and copied for every test
that asks for it** (#1204). The first test that asks for a shape — the
capabilities, the scripted history or none, and the module's `prepare` — builds
it into a template under the session's base temporary directory, and every
test, that one included, gets a private copy at its `root`. The pytest-xdist
workers share the templates: the first worker to ask for a shape builds it
holding a lock on it, and a worker asking meanwhile waits for it rather than
building it again. The copy is a clone where the platform has one
(`clonefile(2)` on macOS, a few calls whatever the size of the tree) and a
file-by-file copy elsewhere; either way every file is the copy's own, so a test
may change anything in it. The backbone and the capabilities are installed in
an interpreter of its own, started with the environment the session began
with, so nothing a test patches or sets reaches a template, whichever test asks
first.

**A module whose tests start with the same slow setting-up hands it over as
`prepare`**: a module-level function that takes the `AdopterRepo` and lays down
what the module's tests start from — a seed stamped, a history committed. It
runs once per session, from the template's root, and what it leaves is in every
copy. `tests/analysis_repo.py` is the worked example: stamping the
software-analysis seed (`prepare_seeded`, the modules' `seeded` fixture) asks
`pkit` some two dozen times, which no copy pays again.
A `prepare` depends on nothing but the repository it is handed — nothing of the
test that happens to ask first, which may be in any module — and its full name
is the template's key, so a lambda or a nested function is refused. It runs in
that first test, with that test's fixtures, so every fixture that asks for a
`prepare` that runs the scripts takes `pkit_on_path`. Setting-up that costs
little — a few files written — stays in the test or its fixture; what a copy
saves is the install, the commits and the scripts.

**A test of the install itself passes `fresh=True`** and gets its own run of it,
in the test: one that patches the install and asserts what it did, reads what
`pkit init` prints, or counts the times something in it ran. A `root` that
already holds anything is built fresh too, since the install treats a
directory with something in the way differently from an empty one.

**What every copy of a template shares**: its commit SHAs, and the times the
install and the `prepare` wrote — the template's, from earlier in the run, not
the test's own. A test that compares such a time with its own clock reads the
template's.

### What the `AdopterRepo` offers

- `root`, `pkit` (`root/.pkit`), `source_kit` (the kit the install came from).
- `install_capabilities("project-management", ...)` — kit-shipped capabilities,
  in order; refuses a dependent whose dependency is not installed yet, the way
  `pkit capabilities install` does.
- Git helpers inherited from `GitRepo`, each returning the resulting SHA:
  `commit(message, {path: content_or_None}, author=Author(...), date=datetime)`,
  `rename(src, dst)`, `merge(branch)` (a `--no-ff` merge commit),
  `squash_merge(branch)`, plus `checkout`, `head`,
  `current_branch`, `shas(path, follow=True)` and raw `git(*args)`.
  Pass `files=None` to `commit` to stage everything in the working tree.
  `date` should be timezone-aware; `author` / `date` set both the author and
  committer sides.

`GitRepo.init(path)` stands alone for repos that are not adopters (the release
tests use it for a synthetic source kit).

### The scripted history

`history=True` lays down, oldest first on `main`:

1. `initial` — the installed `.pkit/` plus `notes/alpha.md` with front matter
   `title: Alpha` / `status: draft`.
2. `rename` — `git mv notes/alpha.md docs/alpha.md`, content untouched.
3. `squash_merge` — branch `topic` (two commits: `status: draft` → `review` in
   `docs/alpha.md`, then `docs/beta.md` added) squashed into one commit with a
   single parent. The side commits stay reachable through `topic` and are in
   `history.side`.

Commit dates step one day apart from `HISTORY_EPOCH` (2026-01-01T12:00Z). The
shape is chosen so "last commit in which field X changed, following renames"
has a non-trivial answer: `status` → `squash_merge`; `title` → `initial`, which
`docs/alpha.md` reaches only via `--follow`. `tests/test_adopter_repo.py` pins
these properties.

### What it deliberately does not replace

Helpers that stage a **synthetic** tree with controlled versions — a fake source
kit (`_make_kit` in `test_changesets.py`, `test_release.py`,
`test_release_shareable.py`), a fake capability at a chosen `schema_version`
(`_make_adopter` in the `test_pm_workflow_v*_migration.py` files), or bare
markers for the entry-point router (`_make_adopter` in `test_router.py`) — stay
as they are. Their tests assert on the synthetic values; a real install would
change what they test, not just how the tree is built.

## A repository a test commits in

**A fixture that commits turns signing off in its temporary repository**
(#1484). A developer's git configuration may sign every commit through an agent,
such as 1Password's, that asks on their screen and fails when nobody answers. The
repository's own configuration overrides it. `GitRepo.init` turns signing off in
every repository it makes, the adopter templates included. A fixture that makes
its own repository, by `git init` or `git clone`, calls `sign_nothing(root)` from
`tests/adopter_repo.py` before its first commit: no commit or tag made there is
signed. A clone does not inherit the setting, so a clone a test commits in needs
the call too; a copied directory and a linked worktree keep it. Where only the
test's own commands commit, `-c commit.gpgsign=false` on each of them does the
same. Never turn signing off in the developer's configuration or the checkout's.

**The suite refuses to sign.** An autouse fixture, `signing_refused`, points
`GIT_CONFIG_GLOBAL` at a configuration of the session's own
(`refusing_global_config`): the user's own global files first, then signing on
for every commit and a signing program that refuses. A commit in a repository
that has not turned signing off fails at once, on every machine and in CI, with a
message naming this section, and no test reaches the developer's signing agent. A
test that sets `GIT_CONFIG_GLOBAL` itself, or runs git with an environment of its
own, is outside the guard; turn signing off in its repositories all the same.
`tests/test_adopter_repo.py` pins the guard and the helpers.
