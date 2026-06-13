*Project-specific operational rules for project-kit-the-project. Loaded into the host `CLAUDE.md` alongside `core.md`. Tied to project-kit's specific tooling and structure; not propagated to adopters (each adopter authors their own `project.md` for rules that fail universal applicability per COR-014).*

## Tool hygiene

1. **Run `pkit` from the project root.** The dispatcher resolves the project root via `git rev-parse --show-toplevel` (with a CWD-walk fallback); staying at root avoids ambiguity in path resolution. Specific to pkit's CWD-resolution behaviour, so this rule lives here rather than in core.
