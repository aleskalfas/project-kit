*project-kit's own operational rules, loaded beside `core.md`. Each fails universal applicability (COR-014), so none reaches an adopter.*

## Tool hygiene

1. **Run `pkit` from the project root,** since it resolves the root from the working directory (the CLI README, "Installing pkit on PATH").
2. **While building in project-kit, run the tests of what you changed and its fast gates, and leave its full suite to `scripts/check.sh`.** Here, software-engineering's rule that a builder runs the tests of what it changed and the fast checks, and leaves the full suite to the project's gate (`software-engineering:RS-SWE-001`), reads as follows. A builder runs the test modules for the files it changed plus the fast gates: `uv run pkit validate`, `uv run pkit friction check`, `uv run pkit migrations check-diff`, `uv run pkit decisions check-diff` and `uv run pkit release check`. `scripts/check.sh` runs the full suite, which the pre-push hook runs whole and CI in parallel parts (ADR-078). CI skips the suite on a pull request whose only changes since a passing full run are answers (ADR-067). `check.sh` runs the suite in parallel workers and lets at most two full suites run on a machine at once (`tests/README.md`, "Running the suite"). Specific to project-kit's own suite and check aggregator, so this rule lives here rather than in core.

## Writing

3. **Write the analysis under `tech-docs/analysis/` by `ANA` (`tech-docs/rule-sets/analysis.md`) and `WRITE` (`tech-docs/rule-sets/writing.md`), and software-analysis's templates and the structures its kinds declare by `WRITE`;** where a rule of `WRITE` would carry project-kit's own vocabulary or style into that shipped text, universal applicability wins (ADR-055 points 3 and 4; COR-014).

## Commits

4. **Sign every commit you make in this repository, and never switch signing off;** if a commit fails to sign, wait a minute before the one retry core rule 21 allows (project-kit#1648).
