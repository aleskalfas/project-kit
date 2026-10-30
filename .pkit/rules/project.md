*Project-specific operational rules for project-kit-the-project. Loaded into the host `CLAUDE.md` alongside `core.md`. Tied to project-kit's specific tooling and structure; not propagated to adopters (each adopter authors their own `project.md` for rules that fail universal applicability per COR-014).*

## Tool hygiene

1. **Run `pkit` from the project root.** The dispatcher resolves the project root via `git rev-parse --show-toplevel` (with a CWD-walk fallback); staying at root avoids ambiguity in path resolution. Specific to pkit's CWD-resolution behaviour, so this rule lives here rather than in core.
2. **While building in project-kit, run its fast gates, and leave its full suite to `scripts/check.sh`.** This is how software-engineering's rule `software-engineering:RS-SWE-001` reads here. The fast gates are `uv run pkit validate`, `uv run pkit friction check`, `uv run pkit migrations check-diff`, `uv run pkit decisions check-diff` and `uv run pkit release check`. `scripts/check.sh` runs the full suite, and the pre-push hook and CI run it. CI skips the suite on a pull request whose only changes since a passing full run are answers (ADR-067). `check.sh` runs the suite in parallel workers and lets at most two full suites run on a machine at once (`tests/README.md`, "Running the suite"). Specific to project-kit's own suite and check aggregator, so this rule lives here rather than in core.

## Writing

3. **Write the analysis by `ANA`, and software-analysis's templates and structures by `WRITE`.** Whoever writes the analysis under `tech-docs/analysis/` follows the accepted rules of `ANA`, project-kit's rules for its analysis (`tech-docs/rule-sets/analysis.md`), and of `WRITE`, project-kit's general writing rules (`tech-docs/rule-sets/writing.md`). Whoever writes software-analysis's templates, or the structures its kinds declare (software-analysis DEC-001 point 1), follows `WRITE` (ADR-055 point 3). Where a rule of `WRITE` would carry project-kit's own vocabulary or style into that shipped text, universal applicability wins (COR-014). Examples are project-kit's glossary terms and its labels. The shipped text stays fit for any adopter. Specific to project-kit's own writing rules, so this rule lives here rather than in core.

## Commits

4. **Sign every commit you make in this repository, and never switch its signing off.** If a commit fails to sign, wait a minute before the one retry core rule 21 allows. Signing is project-kit's own policy, so this rule lives here rather than in core ([project-kit#1648](https://github.com/aleskalfas/project-kit/issues/1648#issuecomment-6247728164)).
