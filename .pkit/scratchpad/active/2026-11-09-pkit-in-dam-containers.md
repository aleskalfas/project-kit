---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-11-09
---

# pkit in DAM agent machines

## The question

How does a project that uses pkit run inside a DAM agent, so that pkit's skills, agents, hooks and rules take effect, and none of DAM's own setup breaks?

DAM ([dam-agents/dam](https://github.com/dam-agents/dam)) runs long-lived agents on Kubernetes, each in a microVM it calls a *machine*, with Claude Code as one of its harnesses. The trouble seen so far: a repository checked out under `./work` does not get its `.claude` applied. DAM also has its own skills and its own view of `.claude`, and it is not clear how Claude Code's subagents, which pkit leans on for parallel work, behave there.

The bounds the maintainer set:

- **DAM does not change.** Its code and its images stay as they are. A Starter Kit counts as configuration of DAM, not a change to it.
- **pkit may change.** It may become more configurable, or gain a capability that bootstraps it in DAM.
- **The session runs as `project-manager`.** The `agent` setting is one of pkit's main advantages, so the way must keep it and still leave DAM's functions working.
- **The user does nothing by hand.** Seeding the repository is the user's only step, whether through a Starter Kit or through pkit's own bootstrap.

## What DAM does

These are read from DAM's repository at `12a8817b7` (paths below are DAM's), unless marked *inferred*.

**The working directory is fixed.**

- Every session, terminal and harness process starts in `/home/agent/work`, with `HOME=/home/agent` (`packages/agent-runtime-api/src/modules/workspace/paths.ts`). The runtime rewrites the `cwd` of every ACP session frame to it (`packages/agent-runtime/src/modules/acp/domain/mappers.ts`, `rewriteCwd`), so no client can pick another.
- DAM's *workspace seed* clones a repository **into `work/` itself**, not into a folder under it (`packages/agent-runtime/src/modules/runtime-channel/drivers/workspace-seed-plugin.ts`). It refuses a non-empty `work/`, runs once, and clones shallow, at depth 50 (`packages/agent-runtime/src/modules/git/protocol-client.ts`). The seed comes from an agent's create request (`gitRepo`) or a Starter Kit (`seed`), with `into: work` (the default) or `into: home`.
- DAM's guidance assumes a project has its own folder under `~/work`, in passing: a project's tools go "in a `mise.toml` in its folder under `~/work`" (`/etc/AGENTS.md`). An agent that runs `git clone` itself lands the repository in `~/work/<name>/`, the case seen so far. The session's project is then `~/work`. *Measured* (open question 8): the repository's `.claude/settings.json` and hooks do not load, so the session does not run as its `agent`. Once a file under it is read, its skills load, each scoped to files under it, and so do its `CLAUDE.md` and the rules that includes. Whether its agents load was not measured.
- One disk holds `HOME`, `work/` included, and survives restarts and new images. Everything outside `HOME` is kept only while the image's root generation stays the same (`docs/architecture/vm-storage.md`).

**DAM owns two `.claude` layers, and writes nothing in the project's.**

- *Managed*, root-owned, highest precedence: `/etc/claude-code/managed-settings.json`. It allows the platform's MCP tools, denies `EnterPlanMode`, loads `AGENTS.md` beside `CLAUDE.md`, and registers a `SessionStart` hook on `clear`. `/etc/claude-code/CLAUDE.md` links to the platform's instructions, `/etc/AGENTS.md`.
- *User*, `~/.claude`:
  - DAM seeds it once from the image.
  - `~/.claude/skills` is a symlink to `~/.agents/skills`, DAM's skill store.
  - `~/.claude/settings.json` sets `permissions.defaultMode: auto`, among other keys.
  - Several writers share that file. `sync-claude-settings.mjs` re-asserts `env.OTEL_*` and a `Stop` and `SubagentStop` hook at every start. The harness-config driver writes `model`, `permissions.defaultMode`, `effortLevel` and the cache settings when the owner changes them. A Starter Kit's install may write it too, but only by DAM's lock protocol (`docs/architecture/starter-kits.md`).
- *Project*, `~/work/.claude`: DAM writes nothing there. An image may not ship files under `work/` at all (`packages/agents/.mise/tasks/check/empty-work-seed`). DAM's docs expect a repository's own `.claude/settings.json` to load as the project's (`docs/architecture/harness-config.md`).

**How Claude Code runs.**

- A long-lived ACP session through `@agentclientprotocol/claude-agent-acp` 0.96.0 (the Agent SDK), one `claude` subprocess per session. DAM passes no `--setting-sources`. The adapter's source on its main branch passes `settingSources: ["user", "project", "local"]`, so the project's settings load, if 0.96.0 does the same. The trial's agent ran 0.104.0, which loads them (open question 1).
- The terminal runs `claude --allow-dangerously-skip-permissions` in `work/`.
- Models go through an in-machine router (`ANTHROPIC_BASE_URL=http://127.0.0.1:…`), and credentials are placeholders that a gateway swaps on the wire. `GH_TOKEN` and git work through the same gateway, over HTTPS. The machine holds no SSH key.
- Claude Code's own sandbox is not used, and the image has no bubblewrap. Isolation is the machine and the egress gateway.
- Sessions run in auto mode unless the owner picks another. A Slack, Telegram or scheduled turn answers every permission prompt "no", except for the platform's own tools, and the turn goes on (`docs/architecture/channel-turns.md`). The trial saw this on Slack, and saw a headless chat run stall on an ask instead (open question 4).
- The platform's tools reach the session as MCP servers: the channel reply, `spawn_subagent`, onboarding's `mark_onboarding_complete` and others.

**Subagents.**

- Claude Code's own subagents are expected: "your harness's own subagent ... does work in this sandbox" (`/etc/AGENTS.md`). They share the machine, `HOME`, `work/`, the credentials and the egress rules.
- A session's `subagentModel` setting reaches Claude Code as `CLAUDE_CODE_SUBAGENT_MODEL` with `..._FORCE`, and then outranks any model an Agent call or agent definition names.
- Background agents keep the session alive through DAM's `Stop` and `SubagentStop` hook. A process the harness did not start as a background task dies when the machine hibernates, unless it runs under `platform-keep` (`/etc/AGENTS.md`).
- Cross-session messaging is off (`CLAUDE_CODE_HARBOR_KITE=0`, `crossSessionInbound: refuse`).
- DAM's own *platform sub-agents* are separate agents, each in a new machine with its own seed and install, started through `spawn_subagent` (`docs/architecture/invocations.md`). One agent's concurrent sessions share one `work/` and one `.git`.

**Installing tools.**

- The image has Python 3.12, uv, node, gh and git.
- `~/.local/bin` is not on `PATH`, so `uv tool install` puts `pkit` where nothing finds it. `~/.local/share/aube/bin` is on `PATH` and lives in `HOME`. A Starter Kit of DAM's own writes wrappers there (`helm/starter-kits/kits/spotlights/kit.yaml`).
- The default egress preset reaches `github.com` and PyPI over HTTPS.
- A Starter Kit's `install.command` runs once in `work/`, after the seed and before the first session. A kit's seed is fixed by the kit, and a kit that DAM's catalog links to must be public, as must its seed.

**GitHub.** DAM's GitHub connections are GitHub App sign-ins or installations (`docs/architecture/github-connections.md`). *Measured* (open question 5): an installation's token reaches the issue tracker and pushes plain commits, and GitHub refuses it a workflow file unless the App and the connection both hold the `workflows` permission. It cannot look itself up through `gh api user`, and GitHub refuses it as an assignee. Whether it reaches a Projects v2 board a user owns is still open.

## What pkit needs

- **The `pkit` command on `PATH`, at the project's release.**
  - `pkit sync` and the commands like it run only at the release the project records, or at the release it pins (ADR-065; `src/project_kit/sync.py`). An install at `@latest` serves only a project already at the latest release.
  - A pinned project is re-run through the router with `uvx --from git+ssh://git@github.com/aleskalfas/project-kit.git@v<pin>` (`src/project_kit/router.py`). `pkit upgrade` fetches over SSH too. Neither reaches GitHub from a DAM machine as it stands.
  - PRJ-004 allows the HTTPS URL with the same tag. The CLI reference names only SSH.
- **A project directory that is the session's project.** The Claude Code adapter writes only project-level files, all committed in the project:
  - `.claude/settings.json`, merged by `merge-settings.sh`: allows, denies, a `SessionStart` and `SubagentStart` hook, and the opt-in settings below. Each hook runs from `${CLAUDE_PROJECT_DIR}`.
  - `.claude/skills/<name>/`: real directories holding symlinks to `.pkit/skills/`.
  - `.claude/agents/*.md`: copies.
  - The root `CLAUDE.md`, whose `@` includes load the rule files.
- **The opt-in settings a project may carry,** each of which acts on every session that loads the project:
  - `agent`, through project-management's default-agent switch. project-kit's own settings set `agent: project-manager`.
  - `sandbox.enabled` with `failIfUnavailable: true`, through `pkit permissions sandbox enable`.
  - The `PreToolUse` permission hook on every tool, through `pkit permissions enable`, with its posture.
- **Python 3 for the hooks**, which are scripts run directly.
- **The git history pkit reads:** the default branch and its merge-base with the head (`src/project_kit/default_branch.py`).
- **Claude Code's Agent tool** for the reviewer stack and the builders, and git worktrees under `.claude/worktrees/`.
- **The `claude` command for unattended runs.** `pkit pm review-pr` starts each reviewer as a nested `claude` run through the adapter's runner. A confined run (ADR-066), such as a fixer's, is refused on every platform today, since the runner's tested range of Claude Code versions is empty (`run-agent.py`).
- **gh**, for every `pkit pm` command, with a Projects v2 board where the project uses one.

## Where the two meet

**Where they fit.**

- *Neither writes the other's files.* DAM keeps to the managed and user layers, and pkit to the project layer. pkit writes nothing under `~/.claude`.
- *A repository seeded into `work/` is the session's project.* Its committed `.claude/` and `CLAUDE.md` load as they do on a laptop. The `@` includes resolve inside `work/`, and `${CLAUDE_PROJECT_DIR}` is `~/work`.
- *Claude Code merges the layers.* Permission lists add up, and every layer's hooks run. pkit's hooks run beside DAM's `SessionStart` on `clear` and its `Stop` and `SubagentStop`.
- *Subagents work.* pkit's agents load from the project's `.claude/agents/`, and the Agent tool runs them in the same machine. Worktrees are allowed.
- *DAM's `AGENTS.md` loads beside pkit's `CLAUDE.md`.* Both are instructions, and neither replaces the other.

**Where they rub.** Separate files are not separate effects: a project's settings outrank the user's for a single-valued key, and act on the whole session, DAM's own tools included.

1. **A repository cloned into `~/work/<name>/` loads none of pkit's settings or hooks, and its skills and rules only once a file under it is read.** This is the case seen so far. The session does not run as `project-manager`. Once a file under the repository is read, its skills load, each scoped to files under it, and so do its `CLAUDE.md` and the rules that includes. Where one of its skills and a user skill share a name, the bare name loads the user's (open question 8). `/cd` into the folder is not available over the chat front-end (open question 9). Only a seed puts the repository at `work/` itself. An agent that already has `work/<name>/` cannot be seeded again: it needs a new agent, or the checkout moved up into `work/` by hand.
2. **The `agent` setting makes every session run as that agent,** chat, Slack, schedules, onboarding and kit updates alike. By Claude Code's documentation (the sub-agents page, "main-thread agent"), the session then takes the agent's system prompt, which replaces Claude Code's own, and its tool restrictions and model. `CLAUDE.md` still loads, so DAM's instructions in `/etc/claude-code/CLAUDE.md` still reach the session. *Measured on a laptop* (Claude Code 2.1.319, the `system` init message of `claude -p --agent …`): under `project-manager` the session has six tools, Read, Bash, Skill, Write, Edit and the agent tool, where Claude Code's catch-all agent has 34. A connected MCP server's tools are all gone, and so are the web tools, tool search, the background-shell monitor and the schedule tools. So under DAM the session would lose every platform tool: a channel turn could not reply, and an onboarding session could not report that it is done, which holds the agent's schedules for good. This is not DAM's alone: every project that turns the default agent on loses these tools today.
3. **A sandbox turned on in the machine would stop every session from starting,** since the image has no bubblewrap and the committed settings say `failIfUnavailable: true`. A fresh clone has it off: `sandbox.enabled` is per machine and lives in `.claude/settings.local.json` (ADR-032), and the committed settings say `enabled: false`. So this bites only if someone runs `pkit permissions sandbox enable` in the machine.
4. **The permission hook acts on DAM's tools too.**
   - Under a strict posture, it denies a call no grant covers, which may reach DAM's MCP tools and skills, ahead of the channel relay's allow-once.
   - In every mode it asks on an `Edit` or `Write` outside the repository. A channel turn answers "no", so DAM's own guidance for unattended turns breaks, such as writing an openrc service under `~/.config/rc/init.d`. A headless chat run stalls on the ask instead, for up to 24 hours (open question 4).
   - In auto mode it does not ask where a guardrail may hide (the adapter README, "When the hook asks").
5. **A shallow seed.** At depth 50, a long-lived default branch may share no history with the head within the clone. A seed from a branch other than the default may have no `origin/main` at all.
6. **A repository seeded `into: home` makes its `.claude/` the user layer, `~/.claude`.** pkit's sync would then write `~/.claude/settings.json` without DAM's lock, and `deploy-skills.sh` would write into DAM's skill store through the `~/.claude/skills` symlink. The root `CLAUDE.md` would be `~/CLAUDE.md`, outside the project `~/work`. Its `@` includes would count as external, and the seeded `~/.claude.json` has not approved those, so the rules would not load.
7. **A second repository.** Under a seed into `work/`, any other repository the agent clones lands inside the pkit checkout. Core rule 19 then has the agent stop and ask before each change to it, so one agent holds one pkit repository in practice.
8. **One `work/` for every session.** Two sessions of one agent, or a schedule beside a chat, share one checkout and one `.git`. pkit's seats and worktrees assume each clone has one owner at a time. In a project with seats, `project-manager`'s first step resumes a seat the clone holds already, so every Slack thread and schedule would resume that seat's loop.
9. **Long nested runs.** `pkit pm review-pr`'s reviewer runs are not the harness's background tasks, so they die if the machine hibernates mid-review, unless they run under `platform-keep`.
10. **Models.** No pkit agent names a model, so nothing is overridden. But with `subagentModel` set, every reviewer and builder runs on the owner's choice. The other way round, a project's overlay may set a model on `project-manager` (`overrides.<agent>.model`). That model then becomes every DAM session's, over DAM's model picker, and may be one DAM's model router does not list.
11. **Private visibility.** A project under `pkit visibility private` keeps pkit's files out of git, so a seed brings no `.pkit/` and nothing to load.
12. **Commit signing.** project-kit's own rules sign every commit, and the machine holds no key. A key made in the machine lives on the `HOME` disk and could be registered with GitHub once. That would put a credential inside the sandbox, where DAM's design keeps none. An adopter without the rule is unaffected.
13. **Symlinks.** `dam import` drops them, and DAM's skill listing skips symlinked skill directories. A seed's `git clone` keeps them, and pkit's skill directories are real directories, so a seeded checkout is unaffected.
14. **Who speaks in a channel turn.** DAM resolves no sender's identity, and gives the owner's messages no more weight than another's (`docs/channel-turns.md`). pkit's acts that a person must authorise, a merge, a record's acceptance, a fixer's consent, assume the person in the session is the one who authorises. Under `agent: project-manager` in a Slack thread, any member of the thread can authorise a merge. The maintainer's ruling (gap 5): that is the owner's choice, made when they choose which channels the agent reaches, and not the agent's to refuse.
15. **pkit's baseline acts on every session.** The core `settings.json` denies `rm -r*`, `git reset --hard` and `sudo`, and allows `Edit`, `Write` and `Bash(git:*)` everywhere. DAM defines a channel turn's reach as what auto mode allows without asking. *Measured* (open question 3): a project's allow rule skips auto mode's classifier, so pkit widens what a Slack turn may do, such as edit `~/.claude/settings.json` outside DAM's lock.
16. **The ACP adapter's own file tools.** DAM's clients, the web interface, the API server and the schedule trigger, all tell the ACP adapter they can read and write files. An earlier ACP adapter answered that by replacing Read, Write and Edit with its own `mcp__acp__*` tools. If it still did, the permission hook, which matches `Edit` and `Write` by name, would never see a write. *Measured on 0.104.0* (open question 2): it does not. The session's `Read`, `Write` and `Edit` are Claude Code's own, and the hook saw a `Write`.

## What pkit would need to keep `project-manager` and DAM both working

Within the bounds, the repository is seeded into `work/`, as only a seed puts it there. What stays is to make pkit's project layer fit a DAM session. Each gap below is pkit's, and none needs DAM to change.

**1. The session agent's tools.**

- *The gap:* `project-manager` lists its tools, and a session running as it keeps only those (rub 2). This holds on every host. DAM only makes the loss break a function.
- *Measured on a laptop,* with agents given inline by `--agents` and read from the `system` init message (Claude Code 2.1.319):
  - An agent with no `tools` inherits all 34 tools, the MCP server's eight included.
  - An agent with only `disallowedTools` keeps all but those it names: 32 of 34, the MCP tools among them.
  - `tools` naming `mcp__<server>__*` adds all of that server's tools. Naming a server the session lacks changes nothing and raises no error.
  - A subagent draws from the session's full set, not from the session agent's list: a reviewer dispatched from a `project-manager` session had the web tool that `project-manager` lacks.
- *Ways for pkit:*
  - (a) *Inherit, and deny what must not reach the agent.* `project-manager` drops `tools`, for `disallowedTools` or for nothing, and pkit narrows what it may do where it narrows it already, in the permission model. This works the same on every host and needs no knowledge of DAM. It keeps tool search too, so an MCP tool the session defers stays in reach. Its cost is the explicit list, in project-management's agent definition. project-management DEC-029 does not decide the list, but its dispatch paragraph assumes the agent cannot send a message to a teammate, which (a) makes false.
  - (b) *A project's own additions to a deployed agent's tools.* A new overlay entry names tools to add, such as `mcp__platform-outbound__*`. The agent's copy is committed, so every machine's agent names DAM's servers, which the measurement shows is harmless. But it mends the MCP tools only, and every adopter still loses the web tools and the rest.
  - (c) *A host profile,* set aside. Deploying other additions on a DAM machine than on a laptop flips the committed copy between them at each sync.

**2. Writes in `HOME`.**

- *The gap:* the permission hook, where a project enables it, asks before any `Edit` or `Write` to an absolute path outside the repository, in every mode (`permission-hook.py`). DAM's own guidance has the agent write in `HOME`, such as an openrc service under `~/.config/rc/init.d`, and a channel turn answers each such ask "no".
- *Ways for pkit:*
  - Ask only where the path lies inside another repository, the case the interlock is for (COR-039, ADR-034 point 2). This mends the gap on every host, with no list of DAM's folders. Check first what else rests on the broader ask, such as keeping intermediate files in the agent workspace (core rule 16).
  - Or a project-owned list of outside folders where a write does not prompt. pkit's `path` privilege forbids `/`, `~` and `..`, so the list needs a syntax of its own.

**3. The strict posture.**

- *The gap:* under a strict posture, the hook denies any call no grant covers. That reaches DAM's MCP tools and the shell commands DAM's guidance teaches, such as `rc-service`, `mise`, `platform-keep` and `agent-browser`.
- *What pkit lacks:* a grant names a tool by its exact name (`decide.py`), and DAM's tools change: onboarding's and a kit update's exist only while pending, and owners add servers of their own. A grant by prefix is a change to the permission model.
- *Meanwhile:* a project keeps the lenient posture, the default, in DAM.

**4. Installing pkit, with nobody at the keyboard.**

- *What must be right when a session starts:* the agent, the settings and the rules, which load from the committed project. With gap 1 mended in the committed agent, the first session runs well as `project-manager` before pkit is installed. Nothing DAM needs goes in `.claude/settings.local.json`: the sandbox stays off on a fresh clone (rub 3). And `agent` must stay in `.claude/settings.json`, the only file the permission hook reads it from.
- *Installing the command:* `uv tool install` of the project's release over HTTPS, into `~/.local/share/aube/bin`, which is on `PATH`. DAM's kits write their wrappers into that folder too, though no file is shared. A pinned version installed over HTTPS runs with no fetch (ADR-065 point 8). Only `pkit upgrade` still fetches over SSH, so it, and any fetch the router still makes, would fall back to HTTPS. That is a change to pkit, and needs no global rewrite of git's URLs in `~/.gitconfig`, a file DAM's seed writes too.
- *The full history:* `git remote set-branches origin '*'`, then `git fetch --unshallow`, since a seed clones one branch at depth 50.
- *When the bootstrap runs:*
  - From a Starter Kit's install command, before the first session. This is the cleanest.
  - Without a kit, in the first session that needs `pkit`, told by the project's rules where to find the bootstrap.
  - Not from pkit's session start hook. That hook is core's, uses only the standard library and never blocks, so teaching it one host puts host behaviour in core (COR-014). A capability cannot add a hook of its own either: the settings merge keeps the last writer's hook list whole, and the existing `settings.json` is the last writer (`merge-settings.sh`). The hook also fires on resume, clear and compaction, and in every session at once in a shared `work/`, so it would need a lock and a done-marker.

**5. Who authorises in a channel turn.**

- *The gap:* rub 14. A Slack turn does not say which person speaks.
- *The maintainer's ruling:* channel turns are where `project-manager` is meant to work, so it does not refuse there. Whoever writes in a channel the agent reaches may authorise, since the owner chose which channels it reaches. Who may authorise is a project's setting, `all` by default. Once a host names each turn's sender, the setting can name the senders whose word authorises, and the agent takes a person's act only from them.
- *What it needs:* with `all`, nothing new. A narrower setting needs the host to name the sender, which DAM does not do yet, and the agent to read the name from the host rather than from a message's prose, which a message could imitate. The setting is a choice later work builds on, so it needs a record, best drafted once a host names senders.

**6. Where pkit keeps it, and a Starter Kit.**

- *A pkit component for DAM* ships the bootstrap and a page on running in DAM. Whether it is a capability is open. A capability is an opt-in discipline (COR-017), and DAM is a host, an axis beside the harness and its adapter, so this is the architect's question. It may belong with the Claude Code adapter, or among the harness-support grades (COR-047), where DAM allows no confined runs.
- *A Starter Kit per repository:* its `seed` puts the repository at `work/`, and its install command runs the bootstrap. It is one kit per repository and must be public. It needs `kit.yaml` and an `ONBOARDING.md` in the project, and it is offered a kit update on every push to the seeded branch, so on every merge `project-manager` lands.
- *One generic Starter Kit with no seed:* its `ONBOARDING.md` asks for the repository, clones it into `work/` and runs the bootstrap. One kit serves every repository. Onboarding finishes before pkit's project layer loads, so marking it complete never depends on gap 1, and no push offers an update. The next session, started in `work/`, loads the project.

## Limits accepted

- *One pkit repository per agent* (rub 7). A builder's `git add -A` would commit another repository cloned inside it.
- *One checkout for every session* (rub 8). A DAM agent holds no seat of a topology.
- *Long reviews* run under `platform-keep`, or die when the machine hibernates (rub 9).
- *A private-visibility project* cannot run in DAM by a seed (rub 11).
- *Signed commits* need a key in the machine, which is the project's choice to make, not pkit's (rub 12).

## Other ways, set aside

- **pkit deploys to the user layer, `~/.claude`.** It would mix pkit's files with DAM's skill store and with the settings DAM rewrites, and the rules in `~/CLAUDE.md` would not load (rub 6).
- **DAM starts a session in a subfolder of `work/`.** That is a change to DAM, outside the bounds.
- **A nested `claude` started in the repository.** It doubles the sessions, loses DAM's session features for the nested one, and dies on hibernation.
- **A shim in `~/work` linking into `work/<name>/`.** `~/work` is no git repository, so the CLI's search for the project root fails there, and `${CLAUDE_PROJECT_DIR}` is not the repository.
- **A DAM-only variant of `project-manager`,** deployed to a locally excluded path and named in `.claude/settings.local.json`. The permission hook reads the agent only from `.claude/settings.json`, and the agent's name differs between machines.

## Leaning

- `project-manager` inherits the session's tools, less those it is withheld (gap 1, way (a)). It is a change for every host, mends the lost web tools on a laptop too, and is the decision that needs a record first. DAM's platform tools then reach it with no knowledge of DAM in pkit.
- The repository is seeded into `work/`, by a generic Starter Kit's onboarding, a kit per repository, or a plain create.
- A small bootstrap that pkit ships installs the pinned `pkit` over HTTPS and fetches the full history. `pkit upgrade` falls back to HTTPS.
- The write prompt narrows to other repositories (gap 2). The strict posture stays off in DAM until grants match by prefix (gap 3).
- In a channel turn, `project-manager` takes a person's acts from whoever writes there, until a project's setting names the senders who may authorise (gap 5).
- Where pkit keeps the DAM support goes to the architect (gap 6).

## Open questions

*Settled on a laptop:* a session agent's `tools` removes MCP tools, and built-in ones, from the session. A server named in `tools` that the session lacks is ignored.

### Answered on a live machine

Measured on 12 and 13 November 2026 on one DAM agent, recorded in full on #3004. The agent ran Claude Code 2.1.321 through `claude-agent-acp` 0.104.0, under DAM CLI 0.2.28 and DAM server 0.3.0-dev. The repository was a small public one, with pkit 2.2.0 installed by hand and pinned, and the permission hook on. The sessions were headless chat runs (`dam run`) and one Slack turn in a private channel, with the repository at the root of `work` unless an answer says otherwise.

1. **Does the ACP front-end load the project's settings, and honour the `agent` setting?** Yes, in chat and on Slack. The session ran as `project-manager`, and the `SessionStart` hook ran.
2. **Does it bring file tools of its own in place of `Read`, `Write` and `Edit`?** No. They are Claude Code's own, and the permission hook saw a `Write` (rub 16). DAM adds the `platform-outbound` MCP server, about 65 tools, which the hook sees as plain tool requests.
3. **Does a project's allow rule skip auto mode's classifier?** Yes. A call a project's allow rule matched, such as `Bash(gh:*)`, carried no classifier verdict, and only the call no rule covered carried one. So a `gh api` write to an issue passed both the hook and the classifier (rub 15).
   - #3127 has the hook refuse such `gh api` writes for `project-manager`.
   - #3006 states on pkit's page that an allow passes a call over the classifier, and the person decides whether that stays a limit.
4. **Does a hook's ask reach a channel turn as a "no", or does it stall the turn?** Each, by the kind of session:
   - *On Slack, a "no":* DAM refused the ask at once, the tool returned "User refused permission to run tool", and the turn went on.
   - *In a headless chat run, a stall:* the ask waited in DAM's approval inbox, which expires after 24 hours, and the turn stalled until it was answered. Denied, the tool returned "Tool permission request failed: Error: Tool use aborted".
   - So the hook's ask before a write outside the repository needs a change for hosts (gap 2). #3159 declares the harness requirement that an ask reaches a person, and #3161 decides whether a machine may name folders where such a write does not ask, or keeps the ask as a limit.
5. **Does the GitHub App's token reach the issue tracker, and push workflow files?**
   - *The tracker: yes.* `gh` signed in as the installation's bot through DAM's `GH_TOKEN` placeholder, read the repository, and opened and closed an issue. pkit's own commands reached GitHub too.
   - *A plain push: yes,* once `gh auth setup-git` has run.
   - *A workflow file: no,* by GitHub's rule: the App and the connection made from it must both hold the `workflows` permission. That is the setup's to grant.
   - *Who acts:* the token cannot call `gh api user`, and GitHub refuses the App's bot as an assignee, so pkit cannot tell which account is acting. #3162 has pkit say so, and #3164 decides how project-management's commands act under such an account.
6. **Is `claude` on `PATH` for the nested reviewer runs, and do they reach the model router?** Yes: a nested `claude -p` reached the router. `pkit` was not on `PATH`, since `uv tool install` puts it in `~/.local/bin`, which the sessions' `PATH` leaves out, and `uv tool update-shell` run over ssh did not reach them. The session-start hook and the install script said what was missing (#3002, #3005). #3006's page says that folder must be on the `PATH` the sessions start with.
7. **Which permission mode do chat and Slack sessions run in?** Auto, in both, from `permissions.defaultMode` in DAM's user settings.
8. **With the repository cloned into a folder below `work`, do its skills load once a file under it is read, and which runs where a project skill and a user skill share a name?**
   - *At session start:* none of the project's settings apply. The session did not run as `project-manager`, and no hook ran.
   - *Once a file under it is read:* its skills load, each scoped to files under it, and so do its `CLAUDE.md` and the rules that includes.
   - *A shared name:* the bare name loads the user's skill. The project's is reachable only by its qualified name, such as `pkit-dam-trial:platform-github`. #3033 has `pkit status` warn of a project skill hidden so.
9. **Does `/cd` into that folder work over the chat front-end?** No: "/cd isn't available in this environment". So only a seed makes a repository the session's project (rub 1).

**Also measured.** A `project-manager` session on the agent planned three Tasks with a critic review, filed them through pkit's commands, and built them with three `software-engineer` subagents at once, each in a worktree of its own. It stopped twice for the person:

- *No command declares a milestone category,* which filing a first Milestone needs (#3160).
- *pkit cannot tell who acts under an App's token* (question 5; #3162, #3164).

No command starts a Task in a worktree of its own, and `start-work` checks the branch out in the session's clone (#3163).

### Still open

- Does DAM plan to name each turn's sender, and in a form the agent reads from the platform rather than from the message (gap 5)?
- Does the agent's prompt replace anything the ACP front-end adds to the system prompt that DAM needs?
- Does an App's token reach a Projects v2 board a user owns? #3164 measures it.
- How long does the review stack take in one machine's quota?

## Next steps

- Gap 1's records are accepted: COR-013 point 7 (an agent's tool access: granted, withheld, or neither), ADR-085 (the Claude Code adapter writes a withheld list) and [project-management:DEC-068-session-agent-tools] (`project-manager` keeps the session's tools, less those it is withheld). Building them follows their acceptance, with #2948 and #2949.
- Ask the architect where pkit keeps DAM support (gap 6).
- The trial on a live machine is done ("Open questions" above). #3006 writes what it measured into pkit's page on running with nobody at the terminal, and retires this note.
- Add the HTTPS install line to the CLI reference, as PRJ-004 already allows.
