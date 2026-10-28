# Design: operational rules sliced by the files they govern (for review)

Shaped in conversation with the maintainer on 28 October; not yet written into any record or code.

## The need

project-kit's operational rules (`.pkit/rules/core.md`, 22 numbered rules, about 2 500 words; the project's own `.pkit/rules/project.md`) reach every session through the Claude Code adapter's `@`-includes in `CLAUDE.md`, helpers included. The maintainer's framing (COR-065): decisions are the source, the system their projection, and the rules are the projection of the decisions into every session. Not every session needs every rule: by a draft count, about 7 are conduct any agent needs, and the rest govern specific work (migrations, methodology-owned files, files meant for include, records, answers on artefacts). The file grows (13 rules in June, 22 now). The maintainer wants each rule written once, in one place, with a single path for future rules, delivered only where it is needed. Rejected on the way: folding work rules into skills (scatters where rules are written; a rule in a skill binds only while it runs); tagging rules with the permission model's privileges (a critic found the coupling real: a grant decides whether a call may run without asking, is chosen per project and machine, and matched the right audience for about 3 of 26 rules); per-agent slicing in general (the main session, where commits, migrations and records happen, and seat workers, which are main sessions, load `CLAUDE.md` whole, as do helpers).

## The design

1. **Each rule has a stable id** (for example `conduct.destructive`, `migration.idempotent`), so a rule keeps its identity when the file is reorganised and citations stop depending on positions (rules are cited by number at least 91 times in 53 files; #1687).
2. **A rule may say which files it governs** (`applies-to:` with path globs, possibly the overlay categories such as `<adr-records>` and the methodology-owned trees as a curated vocabulary). A rule with none is part of the **floor**.
3. **Rules are written in one place**, the methodology's rules (and the project's own for project rules); the adapter projects them.
4. **The Claude Code adapter delivers:** the floor through the `CLAUDE.md` include, as today; each scoped rule as a Claude Code path-scoped rule file (`.claude/rules/pkit-<id>.md` with `paths:` frontmatter), which the harness loads into a session when it reads or edits a matching file. This reaches the main session, helpers and seat workers alike. A harness with no conditional loading gets every rule (fails toward more rules).
5. **What stays in the floor:** rules with no file to trigger them: conduct (destructive operations, retry once, one decision at a time, meaning before identifier), committing (conventional commits, signing), the permission layer, the workspace, other repositories, reading records before changing files.
6. **Trim first:** rules are shortened (rule 20 is 340 words) before any is moved.

## Known limits, as we see them

- A scoped rule loads when its file is first read or edited, so creating a brand-new file can miss it; wider paths soften it.
- Whether a rule is "about files" is the rule author's judgement.
- Moving rules out of the include changes what adopters' `CLAUDE.md` loads (a surface change; a migration), and the friction anchors on `core.md` (16 documents rest on it) would follow the rules.

## Questions for the review

What fails silently: a rule that should load and does not (and how anyone would notice); helpers and built-in agents (Explore, Plan) and confined runs (`--setting-sources ""`); worktrees; a project's own rules; adopters on other harnesses; rules that govern work, not files (authoring a record before any file exists, planning, reviewing); rules that refer to each other; the methodology's own sessions (project-kit itself) versus an adopter's; how a rule's scope is checked to match real paths; whether slicing pays for itself at this size compared with trimming alone.
