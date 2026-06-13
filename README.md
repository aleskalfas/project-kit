# project-kit

> A reusable methodology + workflow framework for AI-assisted projects.

**Status:** proposed. Specification phase. No code yet.

**CLI binary:** `pk`

---

## What this is

`project-kit` packages a working methodology — workflow rules, decision-record system, agent matrix, hard rules, scripts — into something that can be installed into any project and kept in sync as the methodology evolves.

The pattern: when an improvement is made in one project (a clearer hard rule, a better composite script, a sharper agent prompt), it lands in `project-kit` and propagates outward to the projects that have adopted it.

## What this is *not*

- Not a library. No imports from `project-kit` into runtime code. Other projects do not depend on it as a runtime artifact.
- Not a public product. Internal-use scaffolding. Naming, packaging, and design choices reflect that.
- Not a substitute for thinking. The methodology is opinionated but not exhaustive — projects still make their own architectural decisions.

## What's in the box

The kit installs / synchronises a fixed set of files and conventions into a target project:

- **`CLAUDE.md`** — project-level Claude Code session instructions. Carries hard rules, tool hygiene, "where to find things" tables, and pointers into the rest of the framework.
- **`.pkit/decisions/`** — Decision records (core and project namespaces). Schema, status conventions, README index format.
- **`.pkit/agents/`** — agent responsibility matrix governing delegation between specialists, plus base agent definitions.
- **`.pkit/workflow/`** — issue lifecycle, project board state machine, label axes, PR conventions, composite-script docs.
- **`.pkit/README.md`** — adopter-facing entry point that maps the kit's areas (decisions, rules, agents, workflow). Thin navigation index; the methodology lives in the area docs themselves.
- **`.claude/agents/`** — agent definitions (PM / orchestrator / software-engineer / qa-engineer / etc.) with shared hard rules and per-role responsibilities.
- **`scripts/`** — workflow scripts (`work-*.sh`, `pm-*.sh`, `issue-*.sh`, `project-*.sh`) that drive the issue/PR lifecycle.
- **`.mise.toml` task block** — `mise run` task wrappers around the scripts so the canonical commands (`mise run work:start <N>`, `mise run work:review <N>`, etc.) work identically across projects.
- **CONTRIBUTING.md skeleton** — testing requirements, commit-message conventions, branch strategy.

Each artifact is a **template** — the kit writes a per-project default; the project may then customise.

## Installation model

Two operations on a target project:

1. **`pk init`** — first-time install. Stamps the artifacts into a fresh repo, writing per-project values (project name, GHE host, repo slug, milestone names) where the templates take parameters. Idempotent — re-running detects existing artifacts and refuses to overwrite without `--force`.

2. **`pk sync`** — pull the latest version of the kit into a project that has already been initialised. Applies changes to artifacts the project hasn't customised; flags artifacts the project has customised so the user can review and merge changes manually.

Both operations leave a fingerprint file (`.project-kit.toml` or similar) recording the kit version + which artifacts have been customised. The fingerprint is what makes `sync` honest about what's been changed locally.

## CLI sketch

```
pk init [--repo <slug>] [--milestone <name>] [--force]
    Stamp the kit's artifacts into the current directory. Write
    per-project values into templates. Refuse to overwrite an
    existing kit installation unless --force.

pk sync [--dry-run]
    Update an existing kit installation to the current version.
    --dry-run prints what would change without writing.

pk status
    Print the kit version installed, which artifacts have been
    customised locally, and which are out of date relative to
    the kit's current version.

pk list
    List the kit's artifacts, grouped by category (rules / docs /
    agents / scripts / tasks).
```

## Initial scope (M0)

Get to a working `pk init` against a fresh repo. This means:

1. Package skeleton — `pyproject.toml`, package layout, dependencies.
2. CLI scaffolding — Click / Typer; `pk --help` works; `pk init` is a no-op stub.
3. Template authoring — assemble the kit's templates (CLAUDE.md, decision-record schema, workflow docs, scripts, agent definitions, mise tasks), parameterise where projects need to plug in their own values.
4. `pk init` writes the templated artifacts into a target directory.
5. Smoke test — running `pk init` in an empty directory produces a working kit installation that passes a basic sanity check.

`sync` and `status` come after M0. Not required to test the model.

## Out of scope (for the foreseeable future)

- Versioning / migrations between kit releases (deferred until there's a real need).
- A public PyPI release (internal install via `pip install git+...` or similar).
- A web UI / dashboard.
- Plugins / extensions (the kit is opinionated; if a project needs different artifacts, it forks).
- Validation of customised artifacts (`pk lint`).
- Cross-language support (the kit ships Python conventions; non-Python projects are out of scope until proven need).

## Open questions

The first session in this directory should resolve:

- **Templating engine.** Jinja2? Plain string substitution? Something simpler?
- **Customisation tracking.** How does `pk sync` know which artifacts the user has touched? Hash-on-install? Git-aware? A separate marker file?
- **Distribution.** `pip install git+ssh://github.com/...`? A wheel hosted somewhere? `uv tool install`?
- **Per-project values.** What's the minimal set the user must supply for `pk init` to produce a working kit? (project name, GHE host, repo slug, milestone names, default agent set?)
- **Agent definition variance.** Different projects need different specialist agents. Does the kit ship a base set + a customisation slot, or does the user opt in / out?

## Notes for the next session

The **authoring order** matters: hard rules and CLAUDE.md format first (they shape everything else), then decision-record system, then workflow scripts, then agent matrix. Doing them in any other order risks shipping artifacts that depend on rules the kit hasn't yet codified.

Don't over-engineer. The kit is small enough that two markdown files + a CLI + a few hundred lines of Python is plenty for M0. If `pk init` produces a directory containing the templated artifacts with project-specific values filled in, you're done with M0.
