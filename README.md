---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - pyproject.toml
        - src/project_kit/router.py
        - src/project_kit/cli.py
        - src/project_kit/status.py
        - src/project_kit/install.py
        - src/project_kit/merge.py
        - src/project_kit/sync.py
        - src/project_kit/upgrade.py
        - src/project_kit/decisions.py
        - src/project_kit/decisions_validate.py
        - src/project_kit/default_branch.py
        - src/project_kit/migrations.py
        - .pkit/migrations/backbone/1.140.0/001-retire-pkit-router-shim.sh
        - src/project_kit/refs.py
        - src/project_kit/validate.py
        - src/project_kit/friction_check.py
        - src/project_kit/friction_write.py
        - src/project_kit/permissions.py
        - src/project_kit/report.py
        - .pkit/rules/core.md
        - .pkit/adapters/claude-code/merge-claude-md.sh
        - .pkit/adapters/claude-code/merge-settings.sh
        - .pkit/adapters/claude-code/deploy-agents.sh
        - .pkit/adapters/claude-code/settings/core/settings.json
        - .pkit/adapters/claude-code/permission-hook.py
        - .pkit/permissions/decide.py
        - .pkit/permissions/profiles/**
        - .pkit/schemas/privilege-catalog.yaml
        - .pkit/agents/core/critic.md
        - .pkit/agents/core/rule-set-reviewer.md
        - .pkit/agents/core/methodology-reviewer.md
        - .pkit/agents/core/convention-compliance-reviewer.md
        - .pkit/capabilities/project-management/scripts/create-issue.py
        - .pkit/capabilities/project-management/scripts/_lib/bootstrap_gate.py
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
        - .pkit/capabilities/living-docs/README.md#a-fresh-project-the-first-stamp-sets-the-roots-apart
        - .pkit/adapters/README.md#currently-shipped
---

# project-kit

project-kit installs a way of working with AI coding agents into your project, and keeps it current like a dependency. It is built for **[Claude Code](.pkit/adapters/README.md#currently-shipped)** today.

<!-- TODO(c): add a "first win: the code-review gate catches a real defect" section once the comment + review format (#756/#757) lands. -->

## Why

Every project that works with AI coding agents builds a way of working for them. It says where decisions are written down and which rules the agents follow. It also says what the agents may run. Built by hand in each project, it tends to break in six places:

- **Your agent forgets what the project decided.** Each session starts from the project's files, and last week's chat is not among them.
- **The agent asks about every harmless command, or may run one it never should.** You approve prompts without reading them, or turn them off.
- **Documentation goes stale silently.** The code changes, and the document that describes it still reads as true.
- **Nobody but the agent checks the agent's work.** The project's rules live in someone's head, and a change merges unchecked.
- **Each project's setup is a hand-made copy.** An improvement to the shared part has to be copied into every project by hand.
- **Taking an update could overwrite your own edits.** So nobody takes one, and the copies drift apart.

project-kit writes the shared part once, as a methodology. Your project installs it like a dependency and upgrades it like one.

## Highlights

- **[Your rules load into every session, and tell agents to build only on accepted decisions](#your-rules-load-into-every-session).**
- **[Routine commands run unasked, and dangerous ones are denied in their common forms](#routine-commands-run-unasked-and-dangerous-ones-are-denied).**
- **[A change to what a document rests on can't merge until someone says whether the document still holds, once your CI enforces the check](#no-change-leaves-a-document-stale-without-saying-so).**
- **[Reviewer agents come ready to call, each defined never to change the work it judges](#reviewer-agents-come-ready-to-call).**
- **[The methodology upgrades like a dependency](#the-methodology-upgrades-like-a-dependency):** one command, then a pinned version.
- **[Your files stay yours](#your-files-stay-yours):** a sync keeps the lines you added.

## How project-kit answers each problem

The examples run in a fresh repository after [Install](#install) and `pkit init`, with no remote, so some commands warn that they read the local branch. An id such as COR-028 names the record in `.pkit/decisions/` that decides the answer.

### Your rules load into every session

**Your decisions live in the repository, not in a chat that is gone.** `pkit init` adds two include lines to your `CLAUDE.md`, so Claude Code loads the methodology's rules and yours whenever a session starts. Those rules tell every agent to build only on accepted decisions, and an agent's draft starts as `proposed` ([the decisions README, "The acceptance gate"](.pkit/decisions/README.md#the-acceptance-gate)):

```console
$ grep @.pkit CLAUDE.md
@.pkit/rules/core.md
@.pkit/rules/project.md
$ grep -o "Only act on .accepted. decisions" .pkit/rules/core.md
Only act on `accepted` decisions
$ pkit new decision project use-postgres
warning: the default branch 'main' is read from the local branch 'main': this repository has no remote to read the shared one from, and a local branch can lag it or carry work nobody pushed (COR-054 point 2)
Stamped: .pkit/decisions/project/PRJ-001-use-postgres.md
$ grep status: .pkit/decisions/project/PRJ-001-use-postgres.md
status: proposed
```

### Routine commands run unasked, and dangerous ones are denied

**You see fewer prompts, and the common forms of the dangerous commands are refused.** `pkit permissions setup autonomy` activates a permission profile, and turns on the hook that enforces it in Claude Code and, except on macOS, the OS sandbox (COR-028). Then `git`, `gh` and `pkit` run unasked, and `sudo`, a recursive `rm` and `git push --force` are denied to every agent. The example runs only its first step, activating the `autonomous` profile, and the probe shows what the hook will decide, asking as you, the operator:

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

**A change to what a document rests on can't merge until someone says whether the document still holds, once your CI enforces the check.** A document lists its anchors in its front matter, and `pkit friction check` flags each document whose anchors a change touched (COR-050). The change answers each one: updated, unchanged with a reason, or deferred to a follow-up, and a reviewer your project chooses checks each reason. In the example:

- `docs/` holds documents
- a document there rests on `app.py`
- the check fails (`enforcing`) where by default it warns

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
$ echo 'print("hello")' > app.py && git add . && git commit -qm "Add the app and its document"
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

**Four reviewer agents ship with the methodology, each defined to judge the work, not to change it.** The `critic` challenges a draft (COR-024), and the `rule-set-reviewer` judges a change against the rules your project writes down and accepts (COR-057). They run when you or your agent call them, or when a merge gate requires them, such as the one in [project-management](.pkit/capabilities/project-management/README.md), an optional capability. Their definitions say so, and only the critic is also held to it by its tools:

```console
$ grep -l -e "never change the work under review" -e "never modify any artifact" .claude/agents/*.md
.claude/agents/convention-compliance-reviewer.md
.claude/agents/critic.md
.claude/agents/methodology-reviewer.md
.claude/agents/rule-set-reviewer.md
$ grep "^tools:" .claude/agents/critic.md .claude/agents/*-reviewer.md
.claude/agents/critic.md:tools: [Read, Glob, Grep, WebFetch]
.claude/agents/convention-compliance-reviewer.md:tools: [Read, Glob, Grep, Bash, Write]
.claude/agents/methodology-reviewer.md:tools: [Read, Glob, Grep, Bash, WebFetch, Write]
.claude/agents/rule-set-reviewer.md:tools: [Read, Glob, Grep, Bash, Write]
```

### The methodology upgrades like a dependency

**Your project stays at the methodology version it records until `pkit upgrade` moves it (COR-059).** **The upgrade brings the source's improvements in one step, and runs each migration a breaking change needs (COR-010).** It then pins the version it reached, for every clone.

At a terminal, when a newer `pkit` is out, the upgrade first installs that `pkit` on your machine. Every project there without a pin uses it.

Below, `uvx`, which comes with uv, fetches release 1.134.0 from GitHub and sets up a project with it. Your newer `pkit` leaves that project at 1.134.0 until the upgrade moves it:

```console
$ git init -q older-project
$ (cd older-project && uvx -q --from git+https://github.com/aleskalfas/project-kit.git@v1.134.0 pkit init | grep "^  stamped")
  stamped      .pkit/manifest.yaml (backbone v1.134.0; 1 adapter(s) registered)
$ (cd older-project && pkit status | grep "Backbone version")
  Backbone version:      1.134.0   (source <VERSION> — run `pkit upgrade --dry-run` to preview)
$ (cd older-project && pkit upgrade | grep -e "^Upgrading" -e "^  running" -e 1.140.0 -e rule-set-reviewer -e "^Pinned")
Upgrading backbone: 1.134.0 -> <VERSION>
  running <any> backbone migration(s), the replay (no completed transition -> v<VERSION>)
    • 1.140.0/001-retire-pkit-router-shim.sh
  created    .claude/agents/rule-set-reviewer.md
Pinned project-kit to <VERSION> (.pkit/version-pin).
$ (cd older-project && pkit status | grep "Backbone version")
  Backbone version:      <VERSION>   (up to date)
```

The upgrade ran the migrations up to the newer version, release 1.140.0's among them, and deployed the `rule-set-reviewer`, an agent 1.134.0 lacked.

### Your files stay yours

**A sync refreshes the methodology's files and keeps the lines you added.** Every file has one owner, the methodology or you ([the decisions README, "The no-shared-files invariant"](.pkit/decisions/README.md#the-no-shared-files-invariant), COR-001). Into `CLAUDE.md` and `.claude/settings.json`, a sync only adds what is missing (COR-002). Here your own line in `CLAUDE.md` survives a sync:

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
| Works with other agent tools | ✅ you write each tool's files | ❌ [Claude Code only](.pkit/adapters/README.md#currently-shipped), today |
| You choose every line and every allow | ✅ | ❌ its files are synced, and its allows return |
| Rules load into every session | ✅ | ✅ |
| An improvement reaches every project, on any machine | ❌ copied by hand, or one machine's `~/.claude/` | ✅ at each project's next upgrade |
| Taking an update keeps your own files | ❌ merged by hand | ✅ one owner per file, with listed exceptions |
| A deny catches other forms of its command | ❌ the start of a command only | ✅ once the hook is on |
| Stale documents flagged on the change | ❌ | ✅ once anchored in a declared place |
| Reviewer agents ready to call | ❌ written by you | ✅ four shipped |

## When not to use it

- **A one-off task.** Just ask Claude. project-kit is for work that repeats, must survive a new session, or spans projects and people.
- **Another agent tool.** project-kit works with [Claude Code only](.pkit/adapters/README.md#currently-shipped), today.
- **No room for the running cost.** Each change answers the documents whose anchors it touches, and each decision waits for acceptance. Someone also keeps the CI job.

## Install

Install `pkit` once, globally, and it serves every project on your machine.

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/) (the Python tool installer), and [`jq`](https://jqlang.org/), which the merge of Claude Code's settings needs.

Then install `pkit` from the git URL at the tag `latest`, which marks the highest release. The install fetches over SSH with your key, so the fence below shows no output:

```sh
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git@latest
```

To install a given release instead, name its tag, `@v<version>`, from the [releases page](https://github.com/aleskalfas/project-kit/releases). Either tag ties the version your project records to the content that tag holds.

uv fetches `latest` afresh on each install, while a git clone that holds an old `latest` must force-fetch it: `git fetch --force origin tag latest`.

*(HTTPS form if you authenticate with a token: `uv tool install git+https://github.com/aleskalfas/project-kit.git@latest`.)*

Check that your shell finds it:

```console
$ pkit --version
pkit, version <VERSION>
```

If your shell does not find `pkit`, this command adds `uv`'s tool directory to your `PATH`. It changes your shell's startup files, so its fence shows no output. Reopen your shell after it:

```sh
uv tool update-shell
```

The install needs only `uv`, `jq` and the one `uv tool install` command. `pkit` is now on your PATH, shared across all your projects.

### Two things named "pkit"

Two names look alike: the command `pkit`, and the methodology `.pkit/` that it installs.

- **`pkit`** — the **command** you just installed, once, globally.
- **`.pkit/`** — the **methodology** that command installs *into a project* (next step). The `pkit` command operates on it.

*(If it helps: `pkit` is to `.pkit/` as `git` is to `.git/` — one tool, a per-project directory it operates on.)*

## First win — stand it up

**In any repository, one command wires a working methodology into your project.** Below, `git init` makes a fresh repository to stand in for yours. `grep` keeps the three lines that say where `init` installs and that it finished:

```console
$ git init -q your-project
$ cd your-project && pkit init | grep -e "^pkit init" -e "^Install"
pkit init -> <project>/your-project  (git repository root — your current directory)
Installing project-kit into <project>/your-project
Install complete. Recommended next steps:
```

The methodology appears as `.pkit/`, and brings:

- decision records
- hard rules, loaded into your `CLAUDE.md`
- agents, deployed into Claude Code

`init` announces where it will install before writing anything, and asks first if that target isn't your current folder. `pkit status` shows how the methodology is wired, and `grep` keeps three of its lines here:

```console
$ pkit status | grep -e "Backbone version" -e deployed
  Backbone version:      <VERSION>   (up to date)
    skills deployed    <any> kit-managed:
    agents deployed    <any> kit-managed:
```

**That's it: your next AI session already sees the methodology, as [Your rules load into every session](#your-rules-load-into-every-session) shows.**

## The mental model

Think of pkit as a **package manager for your project's methodology**. Four ideas, and you can reason about the whole system:

1. **The tool vs. the install.** `pkit` (the CLI) manages `.pkit/` (the methodology in your repository) — exactly like a package manager and the packages it installs.
2. **Capabilities are packages.** A small always-there **backbone**, plus **opt-in capabilities** — disciplines you install only if you want them (issue-tracking, code-review, citations). Add what you need, ignore the rest.
3. **Two owners, never shared.** Every file belongs to *either* the methodology (synced — don't edit) *or* you (yours — never touched, apart from the ways below). **That's *why* a sync can't conflict with your edits, as [Your files stay yours](#your-files-stay-yours) shows.** The lifecycle's commands, `init`, `sync`, `upgrade` and a capability's install, write a file of yours only in these ways:
   - **`CLAUDE.md` and settings:** they add what is missing, and put back a methodology entry you removed, an allow included. `pkit init` first backs up an existing `.claude/settings.json` to `.claude/settings.json.pre-pkit`. The merge adds allows, such as `git`, `ssh`, `find`, `Edit` and `Write`, and denies.
   - **Elsewhere:**
     - an upgrade's migrations
     - the starter files `init` creates and an upgrade puts back ([the decisions README](.pkit/decisions/README.md#the-no-shared-files-invariant))
     - a capability's rule set ([the CLI README](.pkit/cli/README.md#the-project-rule-set-a-capability-declares))

     A name collision, or a capability's question, waits for your answer ([the lifecycle README](.pkit/lifecycle/README.md#a-new-collision), and [on questions](.pkit/lifecycle/README.md#a-data-points-question)).
4. **[Versioned, upgrades in one command](#the-methodology-upgrades-like-a-dependency).** `pkit upgrade` pulls new versions and runs any migrations automatically, like upgrading a dependency. It then pins the project to the version it reached. The project keeps that version when the installed pkit moves on (`--no-pin` skips the pin).

The shape of `.pkit/`:

```
.pkit/
├── decisions/     # the "why" — records (COR-… the methodology's · PRJ-… yours)
├── rules/         # hard rules, auto-loaded into your CLAUDE.md
├── agents/        # roles your AI delegates to (deployed into the harness)
├── skills/        # authoring procedures the AI runs
├── schemas/       # machine-readable config the tools read
├── capabilities/  # the disciplines you install (appears once you install one)
├── manifest.yaml  # what's installed, and at what version
└── …              # and more (cli, adapters, lifecycle, …)
```

## Next steps

**Add a discipline (a capability).** For example, team-style issue tracking bound to GitHub. Below, `grep` keeps the line that names the capability installed, and the agents it adds:

```console
$ pkit capabilities install project-management | grep -e "^  Installed" -e "created *.claude/agents"
  Installed capability 'project-management' v<any> at .pkit/capabilities/project-management/
  created    .claude/agents/pm-reviewer.md
  created    .claude/agents/project-manager.md
```

Then file issues and move them through the capability's governed workflow with `pkit project-management …`. At a terminal, the install also asks you the questions the capability declares ([the lifecycle README, on questions](.pkit/lifecycle/README.md#a-data-points-question)).

**The tool enforces the process, so you need not remember it: `create-issue` refuses to file an issue before `bootstrap` has run.**

```console
$ pkit capabilities install project-management | grep "^  Installed"
  Installed capability 'project-management' v<any> at .pkit/capabilities/project-management/
$ pkit project-management create-issue --type task --title "Add the app" 2>&1 | grep -e "^\[refused\]" -e "To fix"
[refused] create-issue: project-management prerequisites are not met (DEC-017's hard gate, in code per #747)
          → To fix: run `pkit project-management bootstrap`
```

**By role:**
- **Project managers** → the `project-management` capability: issue hierarchy, a state machine, branch and pull-request conventions, a merge gate. Start at [`.pkit/capabilities/project-management/README.md`](.pkit/capabilities/project-management/README.md).
- **Developers** → [`software-engineering`](.pkit/capabilities/software-engineering/README.md): an agent that writes code to *your* conventions, plus a code-review panel on your pull requests. When a pattern recurs, you can package it as a capability of your own, from the primitives already there: decisions, schemas, skills and agents.

Both documentation roots start as `docs/`, and no install changes them. The first time [living-docs](.pkit/capabilities/living-docs/README.md#a-fresh-project-the-first-stamp-sets-the-roots-apart) creates a space, it offers to move the internal root, which holds the maintainers' documents, to `tech-docs/`. Nothing an install placed in `docs/` before then moves with it. So create that space before you install software-analysis, or the rule set its install writes stays among your user documents.

**What actually gates on day one,** with the defaults (honestly — no more than this), is the structural checks your CI can run:

- decision-id uniqueness (`pkit decisions validate`)
- migration coverage (`pkit migrations check-diff`)
- reference-graph consistency (`pkit refs validate`)
- permission-gated mutations

The friction check stays dormant until you declare where your documents live. Installing `project-management` adds a real merge gate on pull requests.

## Go deeper

- **Adopting / navigating the methodology:** [`.pkit/README.md`](.pkit/README.md) — maps every area. The foundational pattern is in [`.pkit/decisions/README.md`](.pkit/decisions/README.md).
- **The command surface:** [`.pkit/cli/README.md`](.pkit/cli/README.md).
- **Working on project-kit itself:** [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Session instructions for AI agents:** [`CLAUDE.md`](CLAUDE.md).

---

*project-kit is opinionated scaffolding you still steer, and no substitute for thinking. It is no library, since nothing imports from it, and no registry package, since it installs from the git URL.*
