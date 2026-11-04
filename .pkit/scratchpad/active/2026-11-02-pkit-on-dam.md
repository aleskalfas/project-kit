---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-11-02
---

# pkit on DAM

**The question:** what does a project need so that pkit runs on DAM with no friction, and what form should that take: project rules, a starter kit, a capability someone installs, adapter work, backbone work, a request to DAM, or a mix?

DAM runs long-lived AI agents in sandboxes, each a microVM with a credential gateway beside it, reached from chat, Slack, Telegram and schedules (`github.com/dam-agents/dam`). pkit assumes one harness, Claude Code, on a person's machine. pkit already runs on DAM: this session is a DAM agent running pkit on Claude Code, in attended chat. This note maps where the two meet, ranks the friction by evidence, and sketches designs. It decides nothing.

**Sources.** DAM's repository at `main` 7932021fde (2 November 2026), cited `dam:<path>:<line>`; this sandbox; pkit at `3a83e71f`. Each fact is marked **[V]** where it was read in source, docs or the sandbox, and **[I]** where it is inferred. Each friction point also says whether it was **seen** in a real DAM session or only **read** in code.

## What DAM is, in the terms that matter here

- **Agent and sandbox.** An agent is a durable resource with one owner. It runs in a microVM as root, uid 0. `/home/agent` persists, the root overlay persists until an image with a new root generation boots, and `/tmp` is wiped at each boot. The agent hibernates when idle, and unkept background work dies with it; `platform-keep` keeps one job alive [V] (`dam:docs/architecture/agent-images.md:76-79,144`, `agent-lifecycle.md:184-250`).
- **Many repositories in one agent.** An agent's `~/work` may hold one repository or several. This VM has held `/home/agent/work/project-kit` and `/tmp/adopt` in earlier sessions, and now holds project-kit at `~/work` itself [V] (`~/.platform/touched-repositories.json`).
- **Harness, per session.** One image carries six harnesses: `claude-code`, `codex`, `pi`, `bob`, `copilot`, `hermes`. The harness is chosen per session; switching harness means a new session [V] (`agent-images.md:5-32`, `harness-config.md:39`, `sessions.md:7-18`).
- **Model, per turn.** Models are provider-qualified, such as `ibm/aws/claude-opus-5-5`, picked in the session's picker and applied from the next turn, through a local model router (`ANTHROPIC_BASE_URL=127.0.0.1:24180`). Editing the settings file changes neither model nor effort. Claude Code's tier aliases (`opus`, `sonnet`, `haiku`) resolve through the router's tier slots. A session can set a subagent model, which DAM forces over an agent definition's `model:` and the `Agent` tool's model argument [V] (`harness-config.md:189-240`, `/usr/local/lib/model-gateway.sh:53-57`).
- **Instructions, three layers.** Every harness reads `/etc/AGENTS.md` (the platform's), `~/AGENTS.md` (the owner's) and the repository's `AGENTS.md`/`CLAUDE.md`. On Claude Code, `AGENTS.md` loads beside `CLAUDE.md`. Nothing orders pkit's rules against the platform's [V] (`agent-images.md:121-137`, managed settings).
- **Skills, one flat store.** `~/.agents/skills`, keyed by skill name, shared by every harness; `~/.claude/skills` links to it [V] (`agent-skills.md:26-77`).
- **Two kinds of sub-agent.** A harness's built-in subagent runs in the same sandbox and shares workspace, instructions and settings; DAM's instructions prefer it. A **platform sub-agent** runs in a fresh sandbox, possibly on another harness and model, with a stated `need`, a seed repository, an install command, the connections it is given, the driver's egress rules, and a result checked against a JSON Schema. It gets only `/etc/AGENTS.md`, not the driver's repository rules, unless it is seeded with the repository [V] (`invocations.md:30-211`, `agent-images.md:128`).
- **Credentials as placeholders.** No credential is in the sandbox; the gateway swaps `platform:conn:<id>` for the real one on the wire. Git uses `gh`'s credential helper [V] (`connections.md:5-180`).
- **Sessions, and who is asking.** Chat is attended while a tab is open, and may have several senders. Schedules, one-time tasks, session messages and sub-agent outcomes are unattended. A permission prompt with nobody watching is recorded at once as a pending tool approval on Home and the approvals bell, answerable there for ten minutes, with who answered recorded; then it fails as an error. Relayed channel turns answer every permission prompt "no", resolve no sender, and treat a message that looks like the owner's as anyone's. In Slack, only the `reply` tool's text is posted [V] (`sessions.md:105-216`, `channel-turns.md:44-86`).
- **Claude Code as DAM runs it.** `--permission-mode=auto --allow-dangerously-skip-permissions`, `--disallowedTools=AskUserQuestion`, `--setting-sources=user,project,local`, plan mode denied. The repository's `.claude/settings.json`, hooks and agents load, from the folder the harness starts in [V] (this session's command line).
- **Settings with several writers.** `~/.claude/settings.json` is written by the platform at each harness start, by the Config panel, and by a kit's install, under a lock file [V] (`starter-kits.md:132-134`, `runtime-delivery.md:371-378`).
- **Starter kits.** A `kit.yaml` at a repository's root sets up a new agent: seed, install command, startup items, schedules, egress rules, default model, harnesses, providers, skills, connections. The platform never reads configuration back out of an agent's repository [V] (`starter-kits.md:7-288`).

## Scope first

The friction differs by **harness** and by **session kind**, so a first step names both:

- **Harness:** Claude Code only, the one pkit has an adapter for, or Claude Code and others.
- **Session kind:** attended chat; scheduled and other unattended turns; Slack or Telegram channel turns; platform sub-agents.

A narrow first scope, **Claude Code on DAM, in attended chat and schedules**, covers how pkit is used on DAM today, and is the one this session has evidence for. It needs design 0 alone: attended chat is a laptop's consent case, and in a schedule, with no terminal, the person's steps are refused, which is safe. Design 1 matters only for multi-sender chat and channel turns, outside the narrow scope. Wider scopes multiply the work: each further harness needs an adapter (UC-019), and channel turns need consent that knows who is asking. demo-recording's DEC-004 is the pattern for a narrow start: assume one platform, gate it at one boundary, and defer the portability abstraction until a second user needs it (COR-007).

## The friction points, ranked by evidence

Ranked worst first within each group. **Seen** = hit in this session on DAM; **read** = found in code, not yet hit. The session kind it bites in is named.

### Seen: these bit this session

1. **Signing.** project-kit requires signed commits, by its own project rule 4, so this is no friction for other projects (COR-014); builders already commit unsigned, with the build command signing at hand-back (ADR-073 points 2 and 8). A DAM sandbox holds no key and no `gpg`. This session made an SSH signing key by hand, which the permission layer first refused as persistence, and the owner registered it on GitHub. A key in the VM is the kind of credential DAM keeps out of sandboxes, and every commit it signs vouches for the owner on an agent's work. *All session kinds.* [V]
2. **The bot account cannot hold a seat.** The sandbox first ran as a GitHub App account with no write access, so `take-seat` refused, and named another clone as the cause. Seats count only accounts with write access. Several DAM agents may share one account, which DEC-059 anticipates. *All.* [V] (this session; `take-seat.py`)
3. **Long waits against hibernation and tool timeouts.** pkit's waits for CI and reviewers run tens of minutes. A foreground command is cut at the harness's tool timeout, and a background wait was stopped at its limit; unkept background work dies when the agent sleeps. *All, worst unattended.* [V] (this session)
4. **Identity is per clone, and a sandbox is a clone.** pkit's clone key, instance id and seat hint live in a git-ignored `clone.json`. A restart keeps it under `/home/agent`; only a new agent is a new clone, which cannot take up its predecessor's seat. *Already decided:* seats are per clone and their keys never committed (project-management DEC-035 point 1, DEC-058), so changing it changes those records. *All.* [V] (`_lib/instance_identity.py:39`)
5. **Installing and warming pkit.** The install is `uv tool install git+ssh://…`; through DAM's gateway HTTPS with `gh`'s helper works, and SSH may not [I]. About 111 scripts run under `uv run --script`, and queries run offline, so a cold cache after a new root generation fails them [V] (`.pkit/cli/README.md:139`, `provisioning.py:1-25`). This session's `validate` once failed on a resolver with no answer until `pkit sync` ran [V].
6. **A query over its time limit.** *Already decided:* the 30-second bound is a fixed backbone constant, not a setting (ADR-057 point 3); changing it is the maintainer's call. On this sandbox, living-docs' doc-check filler took about 28 seconds against `validate`'s 30-second command limit, and failed inside `validate` while passing alone. A slower sandbox meets pkit's fixed limits sooner. *All.* [V] (this session; `command_runner.py:150`)

### Read: these will bite once the scope widens

7. **Consent from the wrong person.** pkit takes a person's step from a terminal, or from `--yes` on the person's word (`_lib/consent.py:1-30`). That holds on DAM as on a laptop; what changes is *whose* word an agent sees. Chat may have several senders, and a channel turn resolves no sender, so "the owner said yes" in Slack text proves nothing. *Channel turns; multi-sender chat.* [V] (`channel-turns.md:44,86`)
8. **Permission prompts in channel turns.** *Already decided:* refusing a prompt nobody can answer is the designed outcome (COR-061 point 3, ADR-034 point 4). pkit's hook asks on a write outside the repository, and its cross-repo guard asks. In attended chat and in schedules the ask reaches Home and can be answered. In a relayed channel turn it is answered "no", so the step is refused. *Channel turns.* [V] (`channel-turns.md:54-60`; `permission-hook.py`, `session_guard.py`)
9. **The repository below the session's root.** Started one level above the repository, Claude Code loads none of it: not `CLAUDE.md`, not pkit's rules, not the start hook's sentence, not the default agent, and none of pkit's hooks. Started in the repository's root, all of them load. *All, where the session starts above the repository, as `~/work/project-kit` did in this VM.* [V] (observation 1, below)
10. **Two pkit projects in one agent.** `~/.agents/skills` is one flat store keyed by name, so two projects on different pkit versions cannot both hold `decision-author` there. pkit deploys skills under each repository's `.claude/skills/` today, so this binds only a design that deploys to the home. *Several repositories.* [V/I]
11. **Other harnesses get nothing.** On codex, pi, bob, copilot or hermes, pkit's rules, skills, agents, hooks and permissions do not reach the session: they are Claude Code files. pkit allows one runner (`agent_runs.py:375-395`), installs every adapter it ships with no step to choose (`install.py:1066-1068`), and hard-codes `claude-code` and `.claude/` in places in the backbone and project-management (`environment.py:135-140`, `status.py:222`, `_lib/agents.py:40`). *Any non-Claude harness.* [V]
12. **Model names outside Claude Code's vocabulary.** pkit accepts Claude Code's tier aliases and `claude-…` names (`agent_policy.py:44-58`). The aliases work on DAM through the router's tier slots. A provider-qualified name (`ibm/aws/claude-opus-5-5`), or any codex model, is refused; effort `minimal` is refused. No agent pkit ships names a model today. *Once an agent pins a DAM model, or another harness runs.* [V]
13. **Model ownership.** A `model:` in front matter competes with DAM's per-session picker, and loses when a session forces a subagent model; pkit records no model a run actually used [I]. *Same as 12.*
14. **Confined runs.** pkit's confined runs are refused everywhere today, since the runner's tested harness range is empty (`run-agent.py:176`); that is not DAM's doing. On DAM they would also need `bwrap` on `PATH` (the image ships one only inside the codex install) and `socat` (present). The VM is no substitute for ADR-066's confinement: points 4 and 6 forbid auto or bypass mode and any network host, while platform sub-agents run in exactly those modes under the driver's egress rules, and the VM keeps the agent away from the world, not one repository away from the rest of the VM, which may hold several repositories and a signing key. *Drift runs, future working runs.* [V]
15. **Two meanings of "sub-agent".** pkit's dispatch discipline (DEC-029: the `Agent` tool, no `name`, the 4064-character truncation) is Claude Code's built-in kind. A platform sub-agent seeded with the repository does load it all: `CLAUDE.md`, pkit's rules, the start hook's sentence, the platform's `/etc/AGENTS.md`, and the repository's default agent. That default agent is the trap. The repository's settings name `project-manager` as the default (`"agent": "project-manager"`), and its tool list holds no MCP tools, so the sub-agent cannot call the platform's `report_result`, and every such spawn fails with "the turn ended without a reported result". The repository's own configuration breaks the platform's sub-agents. *Platform sub-agents.* [V] (observation 2, below)
16. **Which instructions win.** COR-070 orders pkit's own rule layers; nothing orders them against `/etc/AGENTS.md`. The nearest precedent treats an organisation's managed settings as a layer above pkit's, stated as open (ADR-066 point 11). One clash is already patched by hand: pkit's start hook tells the agent DAM's session scratch directory is replaced by `.agent-workspace/`. *All.* [V]

17. **The gateway against confinement.** DAM's gateway injects the owner's credentials, on the wire, into every process's request to a connected host. ADR-073 point 3 refuses build hosts where the remote's or tracker's credentials reach, and its point on egress names exactly "the platform gives every process its credentials". ADR-066 point 4's scrub of the environment does nothing against it. Builder runs on DAM need the gateway's hosts declared, or must be refused. *Drift and builder runs.* [V] (`ADR-073-builder-runs.md:72-76,171`)
18. **The harness per session.** The one-runner refusal waits for a record on "how a project names its harness" (ADR-066 point 1); on DAM the harness is named per session, not per project. The rules index also refuses two adapters' entry forms. Both block design 4. *Any non-Claude harness.* [V]
19. **A session rooted above several repositories.** COR-039 assumes a session rooted in one repository. Claude Code sets the hooks' anchor, `CLAUDE_PROJECT_DIR`, to the folder it starts in, so a session started at `~/work` anchors there, above every repository in it. ADR-034's comparison then counts each repository below as inside the session, and none as foreign. pkit's own hook would not run there anyway, since it loads only from the repository's root (item 9). The variable reaches hooks only, never the agent's own shell. *Several repositories.* [V] (observation 1, below)

### Not friction today

- **User settings.** pkit writes no user settings and sets no `autoCompactWindow`, so DAM's lock protocol and per-model compaction bind only a future design that writes there.
- **`AskUserQuestion` and `CLAUDE_CODE_SESSION_ATTENDED`.** pkit uses neither. The session kind is visible in `~/.platform/session-metadata.json` (`meta.mode`), though not as a stable contract.
- **The project's own `sandbox.enabled: false`.** It is project-kit's setting, unchanged by DAM.

## Candidate designs

None is chosen. By new machinery, least first: 0, 3 (an existing kind of component), 7, 2, 1, 4, 5. Design 6 is off that axis, being DAM's work.

### 0. No new component: rules, a kit, and fixes

For the narrow scope. Project rules for running on DAM (`project.md`, or the owner's `~/AGENTS.md`); a `kit.yaml` that installs `uv` and `pkit`, warms the cache, and sets a keep for long waits; fixes in the backbone for what bit this session (seat accounts, timeouts, clone identity). With one known user, this passes COR-007's recurrence test, and a capability does not yet.

### 1. Consent through the harness's prompt

*Observed (observation 3, below):* in DAM's attended chat, under auto mode, pkit's hook's `ask` on a write outside the repository was raised and answered by the person; the write then landed.

Removes items 7 and 8 at their root, but is neither harness-neutral nor free. A person's step would be a catalog privilege the adapter asks on: COR-028 has only allow and deny, and an `ask` is the Claude Code adapter's way of carrying out an abstain (ADR-002, as for hidden guardrails, ADR-025 point 2, and foreign writes, ADR-034 point 2). On a laptop it is the terminal prompt; in DAM chat or on Home it is an approval with who answered; in a Slack turn it is refused, which is right.
- **Costs.** It redefines "a person can answer", which COR-061 point 3 fixes as the terminal and COR-002, COR-048 and COR-059 also use: a core refinement. Enforcement is opt-in (`pkit permissions enable`), and consent is checked today in project-management's `_lib/consent.py`, not the hook.
- **Observed in attended chat only.** A hook's `ask` prompts under auto mode in DAM's chat (observation 3). Not yet observed: a scheduled turn, where DAM says the prompt reaches Home for ten minutes, and bypass mode, which DAM's `--allow-dangerously-skip-permissions` lets a session switch to.
- **An interlock, not proof.** A call wrapped in a script hides from the hook, as ADR-034 point 5 says of its own guard.

### 2. DAM as an environment in the adapter's support declarations

The Claude Code adapter answers COR-047's harness requirements for Claude Code as DAM starts it, and `pkit harness report` says what holds on DAM, in place of a separate `pkit dam doctor`. COR-047's Context already allows configuration that "several parties can set", and DAM is one. Two limits: hibernation, identity, signing and the flat skill store are host facts no adapter answers; and an answer bounded by environment is new shape, since COR-047 point 2 bounds only by harness version, so it needs a refinement and a `harness-support` schema version bump (COR-010). Until then, an answer's `cost` can name the condition.

### 3. A `dam` capability

An installable capability: loaded rules for DAM sessions (COR-070), permission grants, a kit template, connection fillers. It cannot carry a runner, a harness translation, or rule delivery; those are an adapter's (COR-005).
- **The wrong grain.** A capability is installed per project and committed, and its loaded rules bind every session with no opt-out (COR-070 point 3, which rejected loading them in some sessions only). DAM is a fact about one machine, and host facts go to per-machine files, never committed ones (ADR-010 point 3, ADR-032 Rule A). A `dam` capability would bind its rules and grants (ADR-016) on the same project's laptop sessions too.

### 7. The host as per-machine data

The missing design. The backbone reads a git-ignored, per-machine file of the ADR-032 kind that says which host this is, whether a session is attended, and how identity maps. DAM's own `~/AGENTS.md` and `kit.yaml` carry the host-level instructions and setup. This is COR-027's "variants as data" applied to hosts, and needs no new kind of component.

### 4. More harnesses

One adapter per further harness, codex first, with the backbone work they share: choosing the active harness (no record says how a project names its harness, ADR-066 point 1), the one-runner refusal, a model vocabulary the harness declares, and the hard-coded `claude-code` paths. Note that `install.py:1066-1068` installs every adapter shipped, so a second adapter meets the one-runner refusal whatever the design.

### 5. A host concept

A host would be a third kind beside harness and capability, owning how sessions start and whether anyone attends, where identity, credentials and signing come from, how long work may run, and which of COR-028's residual gaps it closes. The records already handle the axis piecemeal: host detection (ADR-010), per-machine routing (ADR-032), the macOS stance (ADR-014), demo-recording's gate (DEC-004), and the "out-of-harness" layer COR-028 point 3 sends gaps to, such as "a container or a virtual machine" (ADR-066 point 11), which DAM is. As a kind it fails COR-007: one instance, and a laptop is the absence of a host, not a second one. COR-017's deferral of "adapter-generalization-beyond-harnesses" is the wrong anchor, since COR-027 answered it with data inside a capability. If it ever becomes a kind, it needs a COR of its own, refining COR-005 and COR-017. Record the axis now; defer the kind.

### 6. Requests to DAM

Expose the session kind and the sender to the harness as a stable contract; follow symlinked skill files in Skill Sources; put `bwrap` on `PATH` in the image. A project can ship the `kit.yaml` it uses. Filing these on `dam-agents/dam` from a session rooted here changes another repository, which needs the operator's say first (core rule 19).

## Open questions

1. **Scope.** Which harnesses and which session kinds does a first step cover? The narrow scope needs design 0 alone, with COR-047 answers; wider ones bring 1, 4 and the rest.
2. **Consent.** Is the harness's permission prompt (design 1) the person's step on DAM, given that it records who answered? What should a channel turn do instead?
3. **Signing.** For project-kit only (project rule 4): should a DAM agent sign as its owner, given that DAM keeps credentials out of sandboxes, or commit unsigned, as ADR-073's builders do, with signing at hand-back?
4. **Identity.** Should a DAM agent's `PLATFORM_AGENT_ID` be pkit's clone identity, so a seat survives a rebuilt sandbox, and how do seats count agents that share one account?
5. **The repository's place.** Where does a pkit repository sit in an agent with several, and does pkit's harness configuration still load (item 9)?
6. **Models.** Largely settled: no second writer may own a value the harness owns (COR-047 point 7), and pkit's agents already inherit the model. Open only for a future agent that pins one.
7. **Which sub-agent for which job?** Reviewers in the same sandbox, or platform sub-agents seeded with the repository, which bring a chosen harness or model but not ADR-066's confinement?
8. **Where host behaviour lives.** Project rules, per-machine host data, an adapter's declarations, a capability, or a host kind (designs 0, 7, 2, 3, 5)? The architect's view: host facts belong in per-machine files (ADR-032 Rule A), and the kind is deferred.
9. **The harness per session.** How does a project, or a session, name its harness, when DAM picks one per session (item 18)?
10. **A session rooted above repositories.** Does COR-039 need a refinement for a session started above several repositories (item 19)?

## Observations, 4 November

Run in this sandbox, Claude Code 2.1.310, the repository at `3a83e71f`. Working files are in `.agent-workspace/obs/`.

### 1. A session started above the repository

Two non-interactive runs (`claude -p`, mode `dontAsk`), each asked what its instructions held, one started in the repository's root (`~/work`), one in its parent (`~`):

| What loaded | In the root | One level above |
|---|---|---|
| The project's `CLAUDE.md` | yes | no |
| pkit's rules (`RS-OPS-001`) | yes | no |
| The start hook's `.agent-workspace/` sentence | yes | no |
| The default agent (`project-manager`) | yes | none |
| `CLAUDE_PROJECT_DIR` in the agent's shell | unset | unset |

A probe hook, passed with `--settings`, logged what each hook receives: `CLAUDE_PROJECT_DIR` is the folder the session started in, `~/work` in the first run and `~` in the second, and the hook's working folder is the same. So Claude Code sets the anchor for hooks only, from where it starts.

### 2. A platform sub-agent seeded with the repository

One platform sub-agent on `claude-code`, seeded with the public repository at `3a83e71f`, asked the same and to report through `report_result`. Its kept conversation (`~/.platform/delegations/`) shows:
- the workspace is the repository's root, `~/work`;
- the project's `CLAUDE.md`, pkit's rules, the start hook's sentence and DAM's `/etc/AGENTS.md` all loaded;
- it ran as `project-manager`, the repository's default agent;
- it could not call `report_result`, since `project-manager`'s tools hold no MCP tools, so the spawn failed: "the sub-agent's turn ended without a reported result".

### 3. A hook's `ask` in attended chat

In this session, in DAM's chat under auto mode, a write to `/home/agent/obs-ask-probe.txt`, outside the repository, made pkit's hook answer `ask` (ADR-034 point 2), with its reason naming the anchor and the target. The prompt reached the person, who allowed it, and the write landed 13 seconds later. A scheduled turn was not observed.

### What the observations change

- **Item 9** is confirmed and worse than inferred: above the repository, nothing of pkit loads.
- **Item 15** has a new cause: the repository's own default agent breaks every platform sub-agent seeded with it. A fix is pkit's, not DAM's: the default-agent overlay (project-management DEC-030) applies to every session the repository starts, platform sub-agents included.
- **Item 19** is settled for hooks: the anchor is the starting folder. A session started above repositories counts all of them as its own.
- **Design 1** stands in attended chat; its scheduled-turn half is still unobserved.

## Next

- **Observed** on 4 November, above. Still open: a hook's `ask` in a scheduled turn.
- **Settle question 1 with the maintainer,** with the narrow claim: the narrow scope needs only design 0 and COR-047 answers.
- **For the narrow scope, the records it needs:** COR-047 answers with evidence, and perhaps one new requirement, that a detached process outlives the session's idle time, which ADR-073's detached builds rely on and hibernation breaks; and an ADR putting host facts in per-machine files, extending ADR-032 Rule A to hosting platforms. Any DAM rule in `project.md` must also read true on a laptop.

### What needs the maintainer's authorisation

1. Redefining "a person can answer" (COR-061).
2. Session roots that hold several repositories, against COR-039.
3. Any claim that DAM's VM or gateway closes a residual gap of COR-028: the believed-but-absent boundary ADR-004 point 4 guards against.
4. Builder runs on DAM, under ADR-073 point 3.
5. A new kind of component.
6. Changing ADR-057's fixed time limit.

## Review

Reviewed by critic on 2 November, before the maintainer read it. Its findings, all taken:
- **Re-rank by evidence and session kind.** The first draft ranked friction read in code above friction this session hit. The ranking above is by evidence, with the session kind each bites in.
- **Consent.** The first draft diagnosed a terminal; the issue on DAM is whose word an agent sees. It also missed that a prompt with nobody watching reaches Home and records who answered.
- **Confinement.** The first draft leaned toward "the VM is the confinement", against ADR-066 points 4 and 6, and called the session "more confined than pkit's design", which is false for files.
- **Missing points:** the repository below `~/work`; two pkit projects in one flat skill store; signing as a conflict with DAM's credential model; which instructions win; COR-017's deferred generalisation and COR-047's platform-only declarations.
- **Corrected facts:** `bwrap` ships in the codex install, though not on `PATH`; `sandbox.enabled: false` is the project's own setting; the session kind is visible in session metadata; pkit uses neither `AskUserQuestion` nor `CLAUDE_CODE_SESSION_ATTENDED`; model tier aliases work on DAM.
- **Framing.** "Harness or host?" was a false first question. Scope comes first, and a host concept is a third design, not a choice between two.

Reviewed by the architect on 2 November, after the critic. Its findings, all taken:
- **The narrow scope needs design 0 alone,** not designs 0 to 2.
- **Design 1** is the adapter's, not harness-neutral; it redefines COR-061's "a person can answer"; its auto-mode claim is unobserved.
- **Design 3 is at the wrong grain:** a committed capability binds a project's laptop sessions too, while host facts belong in per-machine files (ADR-010, ADR-032). Design 7, the host as per-machine data, added.
- **Design 5:** the host is a real axis, not yet a kind; COR-017's deferral is the wrong anchor, since COR-027 answered it.
- **Design 2** fits in part, and an answer bounded by environment needs a COR-047 refinement and a schema bump.
- **Added:** items 17–19 (the gateway against ADR-073's confinement, the harness per session, a session rooted above several repositories) and questions 9–10.
- **Already decided:** items 4, 6, 8 and 16, and questions 3 and 6, are settled by accepted records, each now noted where it stands.
- **Authorisations** the maintainer holds, listed under "Next".
