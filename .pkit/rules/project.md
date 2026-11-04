*project-kit's own operational rules, loaded beside `core.md`. Each fails universal applicability (COR-014), so none reaches an adopter.*

## Tool hygiene

1. **Run `pkit` from the project root,** since it resolves the root from the working directory (the CLI README, "Installing pkit on PATH").
2. **While building in project-kit, run the tests of what you changed and its fast gates, and leave its full suite to `scripts/check.sh`.** Here, software-engineering's rule that a builder runs the tests of what it changed and the fast checks, and leaves the full suite to the project's gate (`software-engineering:RS-SWE-001`), reads as follows. A builder runs the test modules for the files it changed, and the fast gates `CONTRIBUTING.md` lists under "Running checks". A builder whose change touches a page, an analysis artefact or an anchor also runs `tests/test_self_host_documentation.py`. `scripts/check.sh` runs the full suite, which the pre-push hook runs whole and CI in parallel parts (ADR-078). The hook runs only where the clone opted into it (`CONTRIBUTING.md`, "Running checks"), and a seat's push of a build runs none (project-management DEC-063 point 7), so a builder takes CI as its change's first full run. CI skips the suite on a pull request whose only changes since a passing full run are answers (ADR-067). Specific to project-kit's own suite and check aggregator, so this rule lives here rather than in core.

## Writing

3. **Write the analysis under `tech-docs/analysis/` by `ANA` (`tech-docs/rule-sets/analysis.md`) and `WRITE` (`tech-docs/rule-sets/writing.md`), and software-analysis's templates and the structures its kinds declare by `WRITE`;** where a rule of `WRITE` would carry project-kit's own vocabulary or style into that shipped text, universal applicability wins (ADR-055 points 3 and 4; COR-014).

## Commits

4. **Sign every commit you make in this repository, and never switch signing off;** if a commit fails to sign, wait a minute before the one retry core rule 21 allows (project-kit#1648).
