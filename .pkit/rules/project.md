*Project-specific operational rules for project-kit-the-project. Loaded into the host `CLAUDE.md` alongside `core.md`. Tied to project-kit's specific tooling and structure; not propagated to adopters (each adopter authors their own `project.md` for rules that fail universal applicability per COR-014).*

## Tool hygiene

1. **Run `pkit` from the project root.** The dispatcher resolves the project root via `git rev-parse --show-toplevel` (with a CWD-walk fallback); staying at root avoids ambiguity in path resolution. Specific to pkit's CWD-resolution behaviour, so this rule lives here rather than in core.
2. **While building, run the tests of what you changed; the full suite is the pre-push hook's and CI's.** A builder runs the test modules for the files it changed plus the fast gates — `uv run pkit validate`, `uv run pkit friction check`, `uv run pkit migrations check-diff`, `uv run pkit release check` — and leaves the full suite to `scripts/check.sh`, which the pre-push hook and CI run. The full suite is some 9 400 tests; six builders each running it on one machine took most of an hour apiece to learn what CI reported in minutes ([project-kit#1182](https://github.com/aleskalfas/project-kit/issues/1182)). `check.sh` runs it in parallel workers and lets at most two full suites run on a machine at once (`tests/README.md`, "Running the suite"). Specific to project-kit's own suite and check aggregator, so this rule lives here rather than in core.

## Writing

3. **Write the analysis by `WRITE`.** Everything under `tech-docs/analysis/` follows the accepted rules of `WRITE`, project-kit's general writing rules (`tech-docs/rule-sets/writing.md`). Specific to project-kit's own writing rules, so this rule lives here rather than in core.

## Decision records

4. **Keep every point at its number until project-kit's records are converted.** A record's points keep their numbers for good ([project-kit#1387](https://github.com/aleskalfas/project-kit/issues/1387)). Until project-kit's records are written as numbered headings, a refinement never changes an existing point's number. To insert or drop a point, first convert that record to numbered headings by hand. A new point then takes the next unused number, and a dropped point leaves its stub. The conversion of project-kit's records removes this rule. Specific to project-kit's own records and their conversion, so this rule lives here rather than in core.
