# project-kit

> Install a working methodology into your AI-assisted project — and keep it maintained, like a dependency.

<!-- TODO(c): add a "first win: the code-review gate catches a real defect" section once the comment + review format (#756/#757) lands. -->

## Why

You've probably done this: you write your conventions into `CLAUDE.md`, have Claude generate a couple of agent files, and it works — until it **rots**. Nobody improves it, a fix you make in project A never reaches project B, and there's no safe way to pull updates. You end up owning a pile you now have to maintain by hand.

**project-kit is the missing piece: the maintained, versioned, *safe-to-update* home for your project's methodology** — the rules, decisions, agents, and disciplines your AI reads at the start of every session. It installs like a dependency and upgrades like one. And it **never touches the files you write** — every file has exactly one owner (the kit's, or yours), so an update structurally *cannot* clobber your work.

That's the honest pitch, including its limit:

> **For a genuine one-off, just ask Claude — really.** project-kit earns its setup when your work **repeats**, must **survive a new session**, or spans **projects and people**. The payoff is real but it accrues over time; the setup cost is small and paid once (below).

Built for **Claude Code** today.

## Install

**Prerequisite:** [`uv`](https://docs.astral.sh/uv/) (the Python tool installer).

Then install `pkit` once, globally, from the git URL:

```
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git
```

*(HTTPS form if you authenticate with a token: `uv tool install git+https://github.com/aleskalfas/project-kit.git`.)*

Verify:

```
pkit --help
```

That's the whole cost: `uv` + one command. `pkit` is now on your PATH, shared across all your projects.

### Two things named "pkit"

- **`pkit`** — the **command** you just installed, once, globally.
- **`.pkit/`** — the **methodology** that command installs *into a project* (next step). The `pkit` command operates on it.

*(If it helps: `pkit` is to `.pkit/` as `git` is to `.git/` — one tool, a per-project directory it operates on.)*

## First win — stand it up

In any repo:

```
cd your-project
pkit init
```

One command, and a `.pkit/` appears — a working methodology wired into your project: decision records, hard rules loaded into your `CLAUDE.md`, agents deployed into Claude Code. See how it's wired:

```
pkit status
```

That's it — your next AI session already sees the methodology.

## The mental model

Think of pkit as a **package manager for your project's methodology**. Four ideas, and you can reason about the whole system:

1. **The tool vs. the install.** `pkit` (the CLI) manages `.pkit/` (the methodology in your repo) — exactly like a package manager and the packages it installs.
2. **Capabilities are packages.** A small always-there **backbone**, plus **opt-in capabilities** — disciplines you install only if you want them (issue-tracking, code-review, citations). Add what you need, ignore the rest.
3. **Two owners, never shared.** Every file belongs to *either* the kit (synced — don't edit) *or* you (yours — never touched). That's *why* updates can't conflict, and why you keep everything you write.
4. **Versioned, upgrades cleanly.** `pkit upgrade` pulls new versions and runs any migrations automatically — like bumping a dependency, lockfile and all.

What `pkit init` created:

```
.pkit/
├── decisions/     # the "why" — records (COR-… kit-owned · PRJ-… yours)
├── rules/         # hard rules, auto-loaded into your CLAUDE.md
├── agents/        # roles your AI delegates to (deployed into the harness)
├── skills/        # authoring procedures the AI runs
├── schemas/       # machine-readable config the tools read
├── capabilities/  # the disciplines you install
└── manifest.yaml  # what's installed, and at what version
```

## Next steps

**Add a discipline (a capability).** For example, team-style issue tracking bound to GitHub:

```
pkit capabilities install project-management
```

…then file and move issues through a governed workflow (`pkit project-management …`) — the process is enforced by the tool, not remembered by you.

**By role:**
- **Project managers** → the `project-management` capability: issue hierarchy, a state machine, branch/PR conventions, a merge gate. Start at [`.pkit/capabilities/project-management/README.md`](.pkit/capabilities/project-management/README.md).
- **Developers** → `software-engineering`: an agent that writes code to *your* conventions, plus a code-review panel on your PRs. And when a pattern recurs, you can grow your own capability without re-erecting the framework — the primitives (decisions, schemas, skills, agents) are already there.

**What actually gates on day one** (honestly — no more than this): structural checks your CI can run — decision-id uniqueness, migration coverage, the one-owner file invariant, permission-gated mutations. Install `project-management` and you additionally get a real PR merge gate.

## Go deeper

- **Adopting / navigating the kit:** [`.pkit/README.md`](.pkit/README.md) — maps every area; the foundational pattern is in [`.pkit/decisions/README.md`](.pkit/decisions/README.md).
- **The command surface:** [`.pkit/cli/README.md`](.pkit/cli/README.md).
- **Working on project-kit itself:** [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Session instructions for AI agents:** [`CLAUDE.md`](CLAUDE.md).

---

*Not a library (nothing imports from it), not a registry package (installs from the git URL, per [PRJ-004](.pkit/decisions/project/PRJ-004-distribution-channel.md)), and not a substitute for thinking — it's opinionated scaffolding you still steer.*
