*project-kit's own operational rules, loaded beside `core.md`. Each fails universal applicability (COR-014), so none reaches an adopter.*

## Tool hygiene

1. **Run `pkit` from the project root,** since it resolves the root from the working directory (the CLI README, "Installing pkit on PATH").
2. **While building, run the tests of what you changed; the full suite is the pre-push hook's and CI's.** A builder runs the test modules for the files it changed plus the fast gates — `uv run pkit validate`, `uv run pkit friction check`, `uv run pkit migrations check-diff`, `uv run pkit decisions check-diff`, `uv run pkit release check` — and leaves the full suite to `scripts/check.sh`, which the pre-push hook runs whole and CI in parallel parts (ADR-078). CI skips the suite on a pull request whose only changes since a passing full run are answers (ADR-067). The suite is some 20 800 tests; six builders each running it on one machine took most of an hour to learn what CI reported in minutes ([project-kit#1182](https://github.com/aleskalfas/project-kit/issues/1182)). `check.sh` runs it in parallel workers, at most two full suites at once on a machine (`tests/README.md`, "Running the suite"). Specific to project-kit's own suite and check aggregator, so this rule lives here rather than in core.

## Writing

3. **Write the analysis under `tech-docs/analysis/` by `ANA` (`tech-docs/rule-sets/analysis.md`) and `WRITE` (`tech-docs/rule-sets/writing.md`), and software-analysis's templates and the structures its kinds declare by `WRITE`;** where a rule of `WRITE` would carry project-kit's own vocabulary or style into that shipped text, universal applicability wins (ADR-055 points 3 and 4; COR-014).

## Commits

4. **Sign every commit you make in this repository, and never switch signing off;** if a commit fails to sign, wait a minute before the one retry core rule 21 allows (project-kit#1648).
