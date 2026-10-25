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
      at: 2026-10-24T22:54:12Z
      outcome: unchanged
      unchanged-because: The refs module gains the lookup of several ids in one document. The README names only pkit refs validate, which is untouched.
---

# project-kit

> project-kit installs a way of working with AI coding agents into your project, and keeps it current like a dependency.

Built for **Claude Code** today.

<!-- TODO(c): add a "first win: the code-review gate catches a real defect" section once the comment + review format (#756/#757) lands. -->

## Why

Every project that works with AI coding agents builds a way of working for them. It says where decisions are written down, which rules the agents follow and what they may run. Built by hand in each project, it breaks in the same places:

- **Your agent forgets what the project decided.** An agent starts each session from its files, and last week's chat is not among them. → [Your rules load into every session](#your-rules-load-into-every-session)
- **The agent asks about every harmless command, or may run one it never should.** You end up approving prompts without reading them, or turning them off. → [Routine commands run unasked](#routine-commands-run-unasked-and-the-guardrails-are-denied)
- **Documentation goes stale silently.** The code changes, and the page that describes it still reads as true. → [Each document says what it rests on](#each-document-says-what-it-rests-on)
- **Nobody but the agent checks the agent's work.** The project's rules live in someone's head, and a change merges without the checks the project decided on. → [A reviewer other than the author](#a-reviewer-other-than-the-author-checks-each-change)
- **Each project's setup is a hand-made copy.** An improvement made in one never reaches the others, and every copy rots. → [The methodology upgrades like a dependency](#the-methodology-upgrades-like-a-dependency)
- **Taking an update could overwrite your own edits.** So nobody takes one, and the copies drift further apart. → [Your files stay yours](#your-files-stay-yours)

project-kit writes that way of working once, as a methodology. Your project installs it like a dependency and upgrades it like one. So an improvement made once at the source reaches your project at its next upgrade.

## How project-kit answers each problem

Each principle cites the record in `.pkit/decisions/` that decides it. A *capability* is an opt-in discipline you install on top, such as living-docs. The examples run in a fresh repository after [Install](#install) and `pkit init`. It has no remote, so some commands warn that they read the local default branch.

### Your rules load into every session

`pkit init` adds two include lines to your `CLAUDE.md`. So Claude Code loads the methodology's rules, and your own in `.pkit/rules/project.md`, whenever a session starts. Your decisions are records in the repository, and an agent's draft starts as `proposed`.

- **Principle:** nothing binds until it is accepted. The loaded rules tell every agent to build only on accepted records ([the decisions README, "The acceptance gate"](.pkit/decisions/README.md#the-acceptance-gate)). Accepting is a one-line status change, which you review like any other change.
- **Gain:** each session works from what the repository records, not from a chat that is gone.

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

### Routine commands run unasked, and the guardrails are denied

One permission model says what each agent may do. project-kit's adapter for Claude Code, the one built today, enforces it through a hook and Claude Code's settings.

- **How:** `pkit permissions setup autonomy` activates a profile and turns the hook on. Commands such as `git`, `gh` and `pkit` then run unasked. The guardrails, `sudo`, a recursive `rm` and `git push --force`, are denied to every agent, and a deny wins over an allow.
- **Principle:** the methodology owns the permission model, and what the harness cannot enforce is reported, never dropped (COR-028).
- **Gain:** fewer prompts, and the common forms of the dangerous commands refused. A deny is a speed bump, not a boundary: a wrapper such as `uv run` slips past it ([the permissions README](.pkit/permissions/README.md#compound-commands-segment-splitting--leading-cd-strip)).

With the profile active and the hook still off, the probe shows what the hook will decide. It asks as you, and agents get the same denies:

```console
$ pkit permissions profile activate autonomous | grep "^profile"
profile 'autonomous' active — posture lenient; its grants are layered under your own (manual grants untouched).
$ pkit permissions probe | head -n 19
Permission probes — does the model do what it declares?   profile: autonomous · posture: lenient · subject: operator

DECISION LAYER — each probe is the verdict the live PreToolUse hook would return

[ 1/19] privilege escalation — `sudo whoami`
        REJECTED — deny grant for operator on ['privilege-escalation']
        ✓ works — matches the declared model

[ 2/19] recursive deletion — `rm -rf build/`
        REJECTED — deny grant for operator on ['destructive-fs']
        ✓ works — matches the declared model

[ 3/19] rewriting published history — `git push --force`
        REJECTED — deny grant for operator on ['vcs-history-rewrite']
        ✓ works — matches the declared model

[ 4/19] version control — `git status`
        ALLOWED — allow grant for operator on ['vcs']
        ✓ works — matches the declared model
```

### Each document says what it rests on

A document can list its anchors in its front matter: the code, the decisions and the other documents that make it true.

- **How:** `pkit friction check` compares your branch with its base. Each document whose anchors the change touched has *friction* until the change answers it: updated, unchanged with a reason, or deferred to a follow-up.
- **Principle:** a change to what a document rests on asks for an answer (COR-050).
- **Gain:** no change leaves an anchored document stale without saying so. The check warns until you set it to `enforcing`, and holds a merge once your CI requires it. With the living-docs capability, an agent proposes each fix for you to review (living-docs DEC-001 point 5).

In a scratch repository, a page about starting the app is anchored to `app.py`. An edit to `app.py` fails the check until the page is answered:

```console
$ mkdir -p .pkit/project && printf 'friction:\n  mode: enforcing\n  places: [docs/**]\n' > .pkit/project/config.yaml
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
Wrote pkit.friction.revalidated in docs/start.md.
$ pkit friction check | grep -A 4 FINDINGS
warning: the default branch 'main' is read from the local branch 'main': this repository has no remote to read the shared one from, and a local branch can lag it or carry work nobody pushed (COR-054 point 2)
FINDINGS — upstream first along the anchors between artefacts
  docs/start.md
    answered  path app.py  changed in this diff; answered: unchanged — It starts the same way.

Result: passed   (enforcing)
```

### A reviewer other than the author checks each change

Reviewer agents ship with the methodology, each defined never to change the work it judges.

- **How:** your agent can have the `critic` challenge a draft before you see it. The `rule-set-reviewer` judges a change against your written rules, your *rule sets*. CI can run `pkit validate` and `pkit friction check`, which ask nobody anything.
- **Principle:** a reviewer other than the author judges the work, against accepted rules alone (COR-024 and COR-057).
- **Gain:** once a gate or your CI requires them, your rules apply to every change, not only when someone remembers them. Without one, the reviewers advise. project-kit ships the checks and the reviewers, the project-management capability ships a merge gate, and you add the CI job.

```sh
pkit sync && pkit validate && pkit friction check
```

### The methodology upgrades like a dependency

`pkit upgrade` moves your project to a newer release in one step, and runs each migration that carries it across a breaking change.

- **Principle:** a project stays at its version until an upgrade moves it (COR-059). A change that would break installed projects ships with its migration (COR-010).
- **Gain:** an improvement made once at the methodology's source reaches the shared part of every project at its next upgrade. A fix you need goes back to that source with `pkit report`.
- **The pin:** the upgrade pins the project to the version it reached. Commit the pin, and pkit runs that version in every clone, or tells you when it falls back to the one installed.

### Your files stay yours

Every file in your project has one owner, the methodology or you, never both.

- **How:** `pkit sync` rewrites only the methodology's files, at the version your project records. Into two files of yours that Claude Code reads, `CLAUDE.md` and `.claude/settings.json`, it adds only what is missing. It never removes or rewrites what you wrote, though it puts back a methodology entry you removed.
- **Principle:** one owner for every file ([the decisions README, "The no-shared-files invariant"](.pkit/decisions/README.md#the-no-shared-files-invariant), COR-001 and COR-002).
- **Gain:** taking an update keeps what you wrote. Put your own rules in `.pkit/rules/project.md`, since an edit to a methodology file is lost at the next sync.

Here a line of your own in `CLAUDE.md` survives a sync that refreshes the methodology's rules:

```console
$ echo "Answer in English." >> CLAUDE.md
$ pkit sync | grep -e rules/core.md -e CLAUDE.md
  refreshed    .pkit/rules/core.md
  exists     CLAUDE.md (already includes @.pkit/rules/core.md)
$ tail -n 1 CLAUDE.md
Answer in English.
```

The lifecycle's commands, `init`, `sync`, `upgrade` and a capability's install, write a file of yours only in these other ways:

- **Settings:** `pkit init` first backs up an existing `.claude/settings.json` to `.claude/settings.json.pre-pkit`. The merge adds allows, such as `git`, `Edit` and `Write`, and denies, and puts back a deny you removed.
- **Elsewhere:** an upgrade's migrations, the starter files `init` creates and an upgrade puts back ([the decisions README](.pkit/decisions/README.md#the-no-shared-files-invariant)), and a capability's rule set ([the CLI README](.pkit/cli/README.md#the-project-rule-set-a-capability-declares)). A name collision, or a capability's question, waits for your answer ([the lifecycle README](.pkit/lifecycle/README.md#a-new-collision), and [on questions](.pkit/lifecycle/README.md#a-data-points-question)).

## When it pays off

> **For a genuine one-off, just ask Claude — really.** project-kit earns its setup when your work **repeats**, must **survive a new session**, or spans **projects and people**. The payoff is real but accrues over time.

The setup is one install ([below](#install)). After it, each change owes its anchored pages an answer, each decision waits for acceptance, and you keep a CI job.

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

If that isn't found, run `uv tool update-shell` and reopen your shell (it adds `uv`'s tool directory to your `PATH`). That's the whole cost: `uv`, `jq` and one command. `pkit` is now on your PATH, shared across all your projects.

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
3. **Two owners, never shared.** Every file belongs to *either* the kit (synced — don't edit) *or* you (yours — never touched, apart from the ways "Your files stay yours" lists above). That's *why* updates can't conflict, and why you keep everything you write.
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
