# Tests

`uv run pytest -q` runs the suite; `./scripts/check.sh` runs it together with the
other gates (see [CONTRIBUTING.md](../CONTRIBUTING.md) "Running checks").

## Running the suite

**While you build, run the tests of what you changed.** The full suite — some
9 400 tests — is the pre-push hook's and CI's to run, not a builder's (the
project's rules, `.pkit/rules/project.md`): run the test modules for the files
you changed, `uv run pytest -q tests/test_<module>.py ...`, and the fast gates,
`uv run pkit validate`, `uv run pkit friction check`,
`uv run pkit migrations check-diff` and `uv run pkit release check`.

**The full suite runs in parallel.** `scripts/check.sh` — the one command the
pre-push hook and CI run, with no arguments in both — runs it in
[pytest-xdist](https://pytest-xdist.readthedocs.io/) workers, `-n auto` (one per
CPU), and then the tests marked `serial` on their own, in one process, in the
same step. `PKIT_TEST_WORKERS` sets the number of workers; `0` runs the whole
suite in one process. The two passes by hand:
`uv run pytest -q -n auto -m "not serial"`, then `uv run pytest -q -m serial`.
A plain `uv run pytest -q` still runs everything in one process, the `serial`
tests included.

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
it. The package under test is held to strict mode through a ratchet instead;
its baseline and how to lower it are in [CONTRIBUTING.md](../CONTRIBUTING.md),
"Running checks".

## The adopter-repository fixture

Most tests that need "a project with the kit installed" should not `git init`
and call `install_kit` by hand. `tests/adopter_repo.py` provides one builder
and `tests/conftest.py` exposes it as two fixtures:

| Fixture | Gives you | Reach for it when |
|---|---|---|
| `make_adopter_repo` | A factory: `make_adopter_repo(capabilities=(), history=False, chdir=True, root=tmp_path)` returning an `AdopterRepo`. | A test drives the CLI or the Python API against an installed adopter. `make_adopter_repo()` with no arguments is the bare shape — `git init`ed `tmp_path`, backbone installed, adapter shell primitives stubbed, cwd moved there, **no commits** — that the per-file `installed_target` / `kit_target` fixtures wrap. |
| `adopter_repo` | `make_adopter_repo(history=True)`: the same adopter with the scripted history committed; `adopter_repo.history` holds the SHAs. | A test needs real git state — validators that read history, the friction engine (COR-050), anything tracing a front-matter field across commits. |

Outside a fixture (a plain helper that takes `tmp_path` and `monkeypatch`), call
`build_adopter_repo(root, monkeypatch=monkeypatch, ...)` directly.

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
