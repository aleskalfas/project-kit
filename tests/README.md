# Tests

`uv run pytest -q` runs the suite; `./scripts/check.sh` runs it together with the
other gates (see [CONTRIBUTING.md](../CONTRIBUTING.md) "Running checks").

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
