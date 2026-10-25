---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - pyproject.toml
        - src/project_kit/router.py
        - src/project_kit/install.py
        - src/project_kit/merge.py
        - src/project_kit/sync.py
        - src/project_kit/upgrade.py
        - src/project_kit/decisions.py
        - src/project_kit/decisions_validate.py
        - src/project_kit/default_branch.py
        - src/project_kit/migrations.py
        - src/project_kit/refs.py
        - src/project_kit/validate.py
        - src/project_kit/friction_check.py
        - src/project_kit/friction_write.py
        - src/project_kit/permissions.py
        - src/project_kit/report.py
        - .pkit/rules/core.md
        - .pkit/adapters/claude-code/merge-claude-md.sh
        - .pkit/adapters/claude-code/merge-settings.sh
        - .pkit/adapters/claude-code/settings/core/settings.json
        - .pkit/adapters/claude-code/permission-hook.py
        - .pkit/permissions/decide.py
        - .pkit/permissions/profiles/**
        - .pkit/schemas/privilege-catalog.yaml
        - .pkit/agents/core/critic.md
        - .pkit/agents/core/rule-set-reviewer.md
        - .pkit/agents/core/methodology-reviewer.md
        - .pkit/agents/core/convention-compliance-reviewer.md
      record: [COR-001, COR-002, COR-010, COR-017, COR-024, COR-028, COR-050, COR-051, COR-054, COR-057, COR-059, COR-061, "living-docs:DEC-001#5", "project-management:DEC-028", PRJ-001, PRJ-004, PRJ-008, PRJ-011, ADR-007, "ADR-025#5", ADR-049, ADR-064, ADR-065]
      artefact:
        - ACT-adopter
        - ACT-ai-agent
        - ACT-developer
        - ACT-operator
        - JRN-001
        - JRN-002
        - JRN-003
        - REQ-021
        - .pkit/decisions/README.md#the-acceptance-gate
        - .pkit/decisions/README.md#the-no-shared-files-invariant
        - .pkit/permissions/README.md#a-deny-holds-against-the-forms-of-its-command
        - .pkit/permissions/README.md#compound-commands-segment-splitting--leading-cd-strip
        - .pkit/lifecycle/README.md#a-new-collision
        - .pkit/lifecycle/README.md#a-data-points-question
        - .pkit/cli/README.md#the-project-rule-set-a-capability-declares
        - .pkit/capabilities/project-management/README.md#
        - .pkit/capabilities/software-engineering/README.md#
        - .pkit/capabilities/evidence/README.md#
    revalidated:
      at: 2026-10-25T13:22:25Z
      outcome: updated
---

# project-kit

project-kit installs a way of working with AI coding agents into your project, and keeps it current like a dependency. It is built for **Claude Code** today.

<!-- TODO(c): add a "first win: the code-review gate catches a real defect" section once the comment + review format (#756/#757) lands. -->

## Why

Every project that works with AI coding agents builds a way of working for them. It says where decisions are written down, which rules the agents follow and what they may run. Built by hand in each project, it breaks in the same six places:

- **Your agent forgets what the project decided.** Each session starts from the project's files, and last week's chat is not among them.
- **The agent asks about every harmless command, or may run one it never should.** You approve prompts without reading them, or turn them off.
- **Documentation goes stale silently.** The code changes, and the page that describes it still reads as true.
- **Nobody but the agent checks the agent's work.** The project's rules live in someone's head, and a change merges unchecked.
- **Each project's setup is a hand-made copy.** An improvement to the shared part has to be copied into every project by hand.
- **Taking an update could overwrite your own edits.** So nobody takes one, and the copies drift apart.

project-kit writes the shared part once, as a methodology. Your project installs it like a dependency and upgrades it like one.

## Highlights

- **[Your rules load into every session](#your-rules-load-into-every-session),** and tell agents to build only on accepted decisions.
- **[Routine commands run unasked, and dangerous ones are denied](#routine-commands-run-unasked-and-dangerous-ones-are-denied)** in their common forms.
- **[No change leaves a document stale without saying so](#no-change-leaves-a-document-stale-without-saying-so),** once the document is anchored and your CI runs the check.
- **[Reviewer agents come ready to call](#reviewer-agents-come-ready-to-call),** defined never to change the work they judge.
- **[The methodology upgrades like a dependency](#the-methodology-upgrades-like-a-dependency):** one command, then a pinned version.
- **[Your files stay yours](#your-files-stay-yours):** a sync keeps what you wrote.

## How project-kit answers each problem

The examples run in a fresh repository after [Install](#install) and `pkit init`, with no remote, so some commands warn that they read the local branch. An id such as COR-028 names the record in `.pkit/decisions/` that decides the answer.

### Your rules load into every session

**Your decisions live in the repository, not in a chat that is gone.** `pkit init` adds two include lines to your `CLAUDE.md`, so Claude Code loads the methodology's rules and yours whenever a session starts. Those rules tell every agent to build only on accepted decisions, and an agent's draft starts as `proposed` ([the decisions README, "The acceptance gate"](.pkit/decisions/README.md#the-acceptance-gate)):

```console
$ grep @.pkit CLAUDE.md
@.pkit/rules/core.md
@.pkit/rules/project.md
$ pkit new decision project use-postgres
warning: the default branch 'main' is read from the local branch 'main': this repository has no remote to read the shared one from, and a local branch can lag it or carry work nobody pushed (COR-054 point 2)
Stamped: .pkit/decisions/project/PRJ-001-use-postgres.md
$ grep status: .pkit/decisions/project/PRJ-001-use-postgres.md
status: proposed
```

### Routine commands run unasked, and dangerous ones are denied

**You see fewer prompts, and the common forms of the dangerous commands are refused.** `pkit permissions setup autonomy` activates a permission profile, and turns on the hook that enforces it in Claude Code and, except on macOS, the OS sandbox (COR-028). Then `git`, `gh` and `pkit` run unasked, and `sudo`, a recursive `rm` and `git push --force` are denied to every agent. Before the hook is on, the probe shows what it will decide, asking as you, the operator:

```console
$ pkit permissions profile activate autonomous | grep "^profile"
profile 'autonomous' active — posture lenient; its grants are layered under your own (manual grants untouched).
$ pkit permissions probe | grep -e "^\[" -e "ED —" | head -n 8
[ 1/19] privilege escalation — `sudo whoami`
        REJECTED — deny grant for operator on ['privilege-escalation']
[ 2/19] recursive deletion — `rm -rf build/`
        REJECTED — deny grant for operator on ['destructive-fs']
[ 3/19] rewriting published history — `git push --force`
        REJECTED — deny grant for operator on ['vcs-history-rewrite']
[ 4/19] version control — `git status`
        ALLOWED — allow grant for operator on ['vcs']
```

> [!WARNING]
> A deny is a speed bump, not a boundary. Until the hook is on, Claude Code's own deny matches only a command's start, so `git push origin main --force` runs. With the hook on, a command behind an allowed wrapper, such as `find . -exec rm -rf {} +`, still runs ([the permissions README](.pkit/permissions/README.md#a-deny-holds-against-the-forms-of-its-command)).

### No change leaves a document stale without saying so

**A change to what a document rests on asks for an answer, so no anchored page goes stale unnoticed.** A document lists its anchors in its front matter, and `pkit friction check` flags each document whose anchors a change touched (COR-050). The change answers each one: updated, unchanged with a reason, or deferred to a follow-up, and a reviewer your project chooses checks each reason. Here `docs/` holds documents, a page there rests on `app.py`, and the check fails (`enforcing`) where by default it warns:

```console
$ mkdir -p .pkit/project && printf 'friction:\n  mode: enforcing\n  places: [docs/**]\n' >> .pkit/project/config.yaml
$ mkdir docs && printf -- '---\npkit:\n  friction:\n    anchors:\n      path: [app.py]\n---\n# Starting the app\n' > docs/start.md
$ cat docs/start.md
---
pkit:
  friction:
    anchors:
      path: [app.py]
---
# Starting the app
$ echo 'print("hello")' > app.py && git add . && git commit -qm "Add the app and its page"
$ echo 'print("hello, world")' > app.py
$ pkit friction check | grep -A 4 FINDINGS
warning: the default branch 'main' is read from the local branch 'main': this repository has no remote to read the shared one from, and a local branch can lag it or carry work nobody pushed (COR-054 point 2)
FINDINGS — upstream first along the anchors between artefacts
  docs/start.md
    friction  path app.py  changed in this diff and carries no answer: revalidate the artefact, or defer the anchor

Result: failed   (enforcing: 1 friction)
$ pkit friction revalidate docs/start.md --outcome unchanged --because "It starts the same way." --yes | tail -n 1
Wrote answers[docs/start.md].revalidated in .pkit/project/friction/answers/<any>.yaml.
$ pkit friction check | grep -A 4 FINDINGS
warning: the default branch 'main' is read from the local branch 'main': this repository has no remote to read the shared one from, and a local branch can lag it or carry work nobody pushed (COR-054 point 2)
FINDINGS — upstream first along the anchors between artefacts
  docs/start.md
    answered  path app.py  changed in this diff; answered: unchanged — It starts the same way.

Result: passed   (enforcing)
```

### Reviewer agents come ready to call

**Four reviewer agents ship with the methodology, each defined to judge the work and never to change it.** The `critic` challenges a draft (COR-024), and the `rule-set-reviewer` judges a change against the rules your project writes down and accepts (COR-057). They run when you or your agent call them, or when a merge gate requires them, such as the project-management capability's. Three definitions say "never change the work under review", and only the critic is also held to it by its tools:

```console
$ grep -l "never change the work under review" .claude/agents/*.md
.claude/agents/convention-compliance-reviewer.md
.claude/agents/methodology-reviewer.md
.claude/agents/rule-set-reviewer.md
$ grep "^tools:" .claude/agents/critic.md .claude/agents/rule-set-reviewer.md
.claude/agents/critic.md:tools: [Read, Glob, Grep, WebFetch]
.claude/agents/rule-set-reviewer.md:tools: [Read, Glob, Grep, Bash, Write]
```

### The methodology upgrades like a dependency

**Your project runs the version it records, until `pkit upgrade` moves it (COR-059).** The upgrade brings the source's improvements in one step, runs each migration a breaking change needs (COR-010), and pins the version it reached. At a terminal, when a newer `pkit` is out, it first installs it on your machine, so every project not yet pinned runs it too. A fresh project is already current, so here the upgrade only pins:

```console
$ grep backbone_version .pkit/manifest.yaml
backbone_version: <version>
$ pkit upgrade
Already at backbone v<version>; nothing to upgrade.
Pinned project-kit to <version> (.pkit/version-pin).
```

### Your files stay yours

**A sync refreshes the methodology's files and keeps what you wrote.** Every file has one owner, the methodology or you ([the decisions README, "The no-shared-files invariant"](.pkit/decisions/README.md#the-no-shared-files-invariant), COR-001). Into `CLAUDE.md` and `.claude/settings.json`, a sync only adds what is missing (COR-002). Here your own line in `CLAUDE.md` survives a sync:

```console
$ echo "Answer in English." >> CLAUDE.md
$ pkit sync | grep -e rules/core.md -e CLAUDE.md
  refreshed    .pkit/rules/core.md
  exists     CLAUDE.md (already includes @.pkit/rules/core.md)
$ tail -n 1 CLAUDE.md
Answer in English.
```

> [!WARNING]
> `pkit init` adds broad allows to `.claude/settings.json`, such as `Bash(ssh:*)`, `Bash(find:*)` and `Bash(mv:*)`, and each sync puts back one you delete.

An upgrade's migrations may also write a file of yours, and a starter file you deleted comes back (COR-059). [The mental model](#the-mental-model) lists every such way. Put your own rules in `.pkit/rules/project.md`, since an edit to a methodology file is lost at the next sync.

## Compared with a hand-kept setup

Without project-kit, the usual setup is a `CLAUDE.md` and agent files you keep by hand and copy from project to project.

| | Hand-kept `CLAUDE.md` and agent files | project-kit |
|---|---|---|
| Nothing to install or learn | ✅ | ❌ `uv`, `jq`, a CLI and its conventions |
| No running cost on each change | ✅ | ❌ answers, acceptances and a CI job |
| Works with other agent tools | ✅ you write each tool's files | ❌ Claude Code only, today |
| You choose every line and every allow | ✅ | ❌ its files are synced, and its allows return |
| Rules load into every session | ✅ | ✅ |
| An improvement reaches every project, on any machine | ❌ copied by hand, or one machine's `~/.claude/` | ✅ at each project's next upgrade |
| Taking an update keeps your own files | ❌ merged by hand | ✅ one owner for every file |
| A deny catches other forms of its command | ❌ the start of a command only | ✅ once the hook is on |
| Stale documents flagged on the change | ❌ | ✅ once anchored |
| Reviewer agents ready to call | ❌ written by you | ✅ four shipped |

## When not to use it

- **A one-off task.** Just ask Claude. project-kit pays off when work repeats, must survive a new session, or spans projects and people.
- **Another harness.** Claude Code's adapter is the only one built today.
- **No room for the running cost.** Each change answers the documents it touches, each decision waits for acceptance, and someone keeps the CI job.

## Install

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/) (the Python tool installer), and [`jq`](https://jqlang.org/), which the merge of Claude Code's settings needs.

Then install `pkit` once, globally, from the git URL at a release tag:

```
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git@v<version>
```

Replace `<version>` with the latest release, from the [releases page](https://github.com/aleskalfas/project-kit/releases). The tag ties the version your project records to the content it holds.

*(HTTPS form if you authenticate with a token: `uv tool install git+https://github.com/aleskalfas/project-kit.git@v<version>`.)*

Verify:

```
pkit --help
```

If that isn't found, run `uv tool update-shell` and reopen your shell (it adds `uv`'s tool directory to your `PATH`). That's the whole install: `uv`, `jq` and one command. `pkit` is now on your PATH, shared across all your projects.

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

One command, and a `.pkit/` appears: a working methodology wired into your project. It brings decision records, hard rules loaded into your `CLAUDE.md`, and agents deployed into Claude Code. `init` announces where it will install before writing anything, and asks first if that target isn't your current folder. See how it's wired:

```
pkit status
```

That's it — your next AI session already sees the methodology.

## The mental model

Think of pkit as a **package manager for your project's methodology**. Four ideas, and you can reason about the whole system:

1. **The tool vs. the install.** `pkit` (the CLI) manages `.pkit/` (the methodology in your repo) — exactly like a package manager and the packages it installs.
2. **Capabilities are packages.** A small always-there **backbone**, plus **opt-in capabilities** — disciplines you install only if you want them (issue-tracking, code-review, citations). Add what you need, ignore the rest.
3. **Two owners, never shared.** Every file belongs to *either* the kit (synced — don't edit) *or* you (yours — never touched, apart from the ways below). That's *why* a sync can't conflict with your edits, and why you keep everything you write. The lifecycle's commands, `init`, `sync`, `upgrade` and a capability's install, write a file of yours only in these ways:
   - **`CLAUDE.md` and settings:** they add what is missing, and put back a methodology entry you removed, an allow included. `pkit init` first backs up an existing `.claude/settings.json` to `.claude/settings.json.pre-pkit`. The merge adds allows, such as `git`, `ssh`, `find`, `Edit` and `Write`, and denies.
   - **Elsewhere:** an upgrade's migrations, the starter files `init` creates and an upgrade puts back ([the decisions README](.pkit/decisions/README.md#the-no-shared-files-invariant)), and a capability's rule set ([the CLI README](.pkit/cli/README.md#the-project-rule-set-a-capability-declares)). A name collision, or a capability's question, waits for your answer ([the lifecycle README](.pkit/lifecycle/README.md#a-new-collision), and [on questions](.pkit/lifecycle/README.md#a-data-points-question)).
4. **Versioned, upgrades cleanly.** `pkit upgrade` pulls new versions and runs any migrations automatically, like upgrading a dependency. It then pins the project to the version it reached, which it keeps when the installed pkit moves on (`--no-pin` skips the pin).

The shape of `.pkit/`:

```
.pkit/
├── decisions/     # the "why" — records (COR-… kit-owned · PRJ-… yours)
├── rules/         # hard rules, auto-loaded into your CLAUDE.md
├── agents/        # roles your AI delegates to (deployed into the harness)
├── skills/        # authoring procedures the AI runs
├── schemas/       # machine-readable config the tools read
├── capabilities/  # the disciplines you install (appears once you install one)
├── manifest.yaml  # what's installed, and at what version
└── …              # and more (cli, adapters, lifecycle, …)
```

## Next steps

**Add a discipline (a capability).** For example, team-style issue tracking bound to GitHub:

```
pkit capabilities install project-management
```

…then file and move issues through a governed workflow (`pkit project-management …`) — the process is enforced by the tool, not remembered by you.

**By role:**
- **Project managers** → the `project-management` capability: issue hierarchy, a state machine, branch/PR conventions, a merge gate. Start at [`.pkit/capabilities/project-management/README.md`](.pkit/capabilities/project-management/README.md).
- **Developers** → [`software-engineering`](.pkit/capabilities/software-engineering/README.md): an agent that writes code to *your* conventions, plus a code-review panel on your PRs. And when a pattern recurs, you can grow your own capability without re-erecting the framework — the primitives (decisions, schemas, skills, agents) are already there.

**What actually gates on day one,** with the defaults (honestly — no more than this): the structural checks your CI can run. They are decision-id uniqueness (`pkit decisions validate`), migration coverage (`pkit migrations check-diff`), reference-graph consistency (`pkit refs validate`), and permission-gated mutations. The friction check stays dormant until you declare where your documents live. Install `project-management` and you additionally get a real PR merge gate.

## Go deeper

- **Adopting / navigating the kit:** [`.pkit/README.md`](.pkit/README.md) — maps every area. The foundational pattern is in [`.pkit/decisions/README.md`](.pkit/decisions/README.md).
- **The command surface:** [`.pkit/cli/README.md`](.pkit/cli/README.md).
- **Working on project-kit itself:** [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Session instructions for AI agents:** [`CLAUDE.md`](CLAUDE.md).

---

*Not a library (nothing imports from it), not a registry package (it installs from the git URL), and not a substitute for thinking. It's opinionated scaffolding you still steer.*
