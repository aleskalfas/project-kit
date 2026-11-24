*project-kit's own operational rules, loaded beside `core.md`. Each fails universal applicability (COR-014), so none reaches an adopter.*

## Tool hygiene

1. **Run `pkit` from the project root,** since it resolves the root from the working directory (the CLI README, "Installing pkit on PATH").
2. **While building in project-kit, run the tests of what you changed and its fast gates, and leave its full suite to `scripts/check.sh`.** Here, software-engineering's rule that a builder runs the tests of what it changed and the fast checks, and leaves the full suite to the project's gate (`software-engineering:RS-SWE-001`), reads as follows. A builder runs the test modules for the files it changed, and the fast gates `CONTRIBUTING.md` lists under "Running checks". A builder whose change alters a page, an analysis artefact or the anchors a document declares also runs `tests/test_self_host_documentation.py`. `scripts/check.sh` runs the full suite, which CI runs in parallel parts (ADR-078). The pre-push hook runs `scripts/check.sh` whole, but only where the clone opted into the hook, and then in each of the clone's worktrees too (`CONTRIBUTING.md`, "Running checks"). Where no hook runs, CI's run is the change's first full run. CI skips the suite on a pull request whose only changes since a passing full run are answers (ADR-067). Specific to project-kit's own suite and check aggregator, so this rule lives here rather than in core.

## Writing

3. **Write the analysis under `tech-docs/analysis/` by `ANA` (`tech-docs/rule-sets/analysis.md`) and `WRITE` (`tech-docs/rule-sets/writing.md`), and software-analysis's templates and the structures its kinds declare by `WRITE`;** where a rule of `WRITE` would carry project-kit's own vocabulary or style into that shipped text, universal applicability wins (ADR-055 points 3 and 4; COR-014).

## Commits

4. **Sign every commit you make in this repository, and never switch signing off;** if a commit fails to sign, wait a minute before the one retry core rule 21 allows (project-kit#1648).

## Visual work

5. **Run no design loop in project-kit beyond the visual-communication capability's one round.** A *design loop* changes how a piece, a library or a brand looks (its layout, forms, type, colour or space), has a review or another critic read the result, and lets what that reading finds choose the next change. No session starts, resumes or dispatches one, in the repository or in any copy of it, save the designer's one round of mends (visual-communication DEC-070 point 2), and no critic but the capability's reviewer steers a change to how a piece, a library or a brand looks. Two things are outside this rule: a change to words, facts or translations that leaves the layout as it is, and drawing the designs a test grades, which never become another piece's, a library's or a brand's. A person may still ask for one further round, which mends what they name (DEC-070 point 2). DEC-070 binds the capability's designer alone; this rule binds every session, since project-kit authors the capability and its own pieces are what the review is tested on (project-kit#3478).
