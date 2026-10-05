*Project-specific operational rules for project-kit-the-project. Loaded into the host `CLAUDE.md` alongside `core.md`. Tied to project-kit's specific tooling and structure; not propagated to adopters (each adopter authors their own `project.md` for rules that fail universal applicability per COR-014).*

## Tool hygiene

1. **Run `pkit` from the project root.** The dispatcher resolves the project root via `git rev-parse --show-toplevel` (with a CWD-walk fallback); staying at root avoids ambiguity in path resolution. Specific to pkit's CWD-resolution behaviour, so this rule lives here rather than in core.
2. **While building, run the tests of what you changed; the full suite is the pre-push hook's and CI's.** A builder runs the test modules for the files it changed plus the fast gates — `uv run pkit validate`, `uv run pkit friction check`, `uv run pkit migrations check-diff`, `uv run pkit release check` — and leaves the full suite to `scripts/check.sh`, which the pre-push hook and CI run. The full suite is some 9 400 tests; six builders each running it on one machine took most of an hour apiece to learn what CI reported in minutes ([project-kit#1182](https://github.com/aleskalfas/project-kit/issues/1182)). `check.sh` runs it in parallel workers and lets at most two full suites run on a machine at once (`tests/README.md`, "Running the suite"). Specific to project-kit's own suite and check aggregator, so this rule lives here rather than in core.

## Writing

3. **Analysis artefacts follow the accepted rules of `WRITE`.** Analysis artefacts under `tech-docs/analysis/` follow the accepted rules of `WRITE` (`tech-docs/rule-sets/writing.md`). Specific to project-kit's own writing rule set, so this rule lives here rather than in core.
