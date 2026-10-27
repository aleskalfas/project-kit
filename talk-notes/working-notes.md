# Friday presentation — working notes

Started 25 October. Talk on Friday 30 October. Side quest beside the build work.

## The maintainer's ask

- An honest discussion first: what project-kit is good for, and what it is not.
- Find good use cases, and build the presentation on them.
- Ideal demo: a user installs project-kit, sets up project-management, software-engineering, software-analysis and living-docs, and builds a project with work running in parallel.

## Existing material

- `.agent-workspace/living-docs/talk-outline.md`: 18 slides and 6 demos built on the README's problems (forgetting, prompts, stale docs, self-graded work, copies that rot, updates that overwrite). It covers the backbone only; the capabilities get one slide (12).
- `README.md` on main: "Why project-kit", six highlights, the table against a hand-kept setup, "When not to use it".

## Honest assessment (PM's first take, to discuss)

**Where it earns its keep, from this week's work on project-kit itself**
- **Agents deliver, a person decides.** One project-manager agent files issues, dispatches builders, gathers reviewer verdicts and merges behind a gate. Dozens of pull requests landed this week that way; the maintainer took only the decisions.
- **Review that catches real errors.** Reviewers judge every pull request against accepted rules. Example: on #2062 the docs reviewer found three pages that still described the old behaviour, which the builder had marked as updated.
- **Docs that cannot go stale silently.** A change to code a page rests on asks for an answer, and a reviewer checks the answer.
- **Decisions that survive the session.** Records, the acceptance gate, rules loaded into every session.
- **Parallel work without collisions.** Each task runs on its own branch in its own worktree; answers live in files of their own (COR-062), so pull requests touching the same document no longer conflict.

**Where it costs, said plainly**
- **Running cost.** Answers, reviews and fix rounds take time and tokens: one link pass owed 109 answers (#2064 now fixes that), and this session hit a weekly usage limit.
- **Ceremony and learning curve.** Many concepts: records, places, anchors, answers, rule sets, gates.
- **Claude Code only.** One adapter.
- **Not finished.** Fixers not switched on; the analysis is hard to read on GitHub until #2065 lands; the adoption path is still open (#775).

**Parallel workstreams, what exists**
- project-management's *workstream* is a label that groups issues, not a way to run work in parallel.
- Running in parallel is what the project-manager agent does with the harness: builders in their own git worktrees, one issue and branch each, reviewers run at once, a merge gate. project-kit supplies the rails (issue per task, branch names, answer files that do not conflict, the gate, integration branches for a chain, DEC-013). No single command fans the work out.

## Audience (decided 25 October)

Colleagues who develop an AI agentic platform: users create agents and interact with them, each agent running in its own sandbox. So they build agent runtimes themselves. What they care about: governing what an agent may do, sandboxes, agents delegating to agents, human-in-the-loop, memory across sessions, running many agents at once, cost.

**Angle this suggests:** project-kit as a field report on running a team of AI agents on a real codebase, and the rails that made it safe. Their platform's problems (permissions, sandbox gaps, delegation, approvals, parallel agents) are project-kit's daily problems, solved at the repository layer.

**Lessons from this week that speak to them directly:**
- A named sub-agent's result arrived cut at 4,064 characters, and the prefix read as complete (the harness requirement `delegated-result-complete`, COR-047).
- A message from a sub-agent is not the user's approval: the permission-laundering rule.
- A builder wrote outside the sandbox's granted folder and put a prompt on the maintainer's phone at night (#2026); the fix was a binding rule and a workspace folder every agent is granted.
- Prompt fatigue: the permission model exists so the person reads the prompts that matter (COR-028).
- Reviews in rounds: each fix round found more stale text, until the builder was told to sweep the whole page.
- Cost: a weekly usage limit stopped four agents mid-work; each resumed from its worktree.

## Parallel work: what exists and what is in progress

- **Works today, proven this week:** one project-manager session fans out builders, each in its own git worktree on its own issue branch; reviewers run at once; a merge gate lands each pull request; answers live in files of their own so parallel pull requests do not conflict (COR-062).
- **Built:** instance ownership for several clones of one repository: an instance id, claims and handoff (DEC-035, DEC-043, DEC-045 accepted; `set-instance`, `handoff-issue`), on EPIC #508.
- **Proposed:** the parallelization primitive (DEC-025, proposed; scratchpad `2026-05-26-parallelization-primitive.md`, from the interaction-gateway project): lanes, typed `Blocked by:`, the ready frontier; EPIC #564. The ladder of what can start now and what can run side by side (#1548).
- **Postponed until software-analysis and living-docs existed, which they now do:** multi-clone coordination, recovering every clone's direction after all sessions die (EPIC #943).
- **Agents do the work, the person decides in batches** (EPIC #1673): a chain merging into an integration branch (#1676), agents building only on merged work (#1680), decisions in one batch (#1675).

## Angle (decided 25 October)

**A field report:** "Running a team of AI agents on a real codebase", with project-kit as the rails and the install-and-build demo as the high point.

**Numbers for the hook** (GitHub search, 25 October): 156 pull requests merged on project-kit in the last 7 days, 492 in the last month; 234 issues filed in the last 7 days. Mostly agent-built, merged behind the gate; the maintainer took the decisions.

## Draft skeleton (about 25 minutes)

1. **Hook** — 156 pull requests in a week; one person deciding. What made that safe?
2. **The team** — a diagram: the person, the project-manager agent, builders in their own worktrees, the reviewer panel, the merge gate.
3. **Lessons, each a failure paired with the rail that fixed it**
   - Memory: Monday forgot Friday → records, the acceptance gate, rules in every session.
   - Permissions: prompt fatigue and the sandbox edge → one permission model, a workspace every agent is granted.
   - Delegation: a truncated hand-off read as complete; a sub-agent's "approval" → dispatch rules, no laundering.
   - Self-graded work → reviewers that judge against accepted rules, a merge gate.
   - Stale docs → a change to what a page rests on asks for an answer.
   - Parallel collisions → one branch and worktree per issue, answers in files of their own.
   - Cost → the honest bill: answers, review rounds, usage limits.
4. **Demo** — install, four capabilities, a project sliced and built in parallel.
5. **Limits and what is next** — Claude Code only; the parallelization EPICs.
6. **What carries over to an agent platform** — the takeaways for people who build sandboxed agents.

## Demo format (decided 25 October)

**Recorded.** Real evidence from this week's work backs the lessons.

## Trial install (25 October), in short

Full log: `trial-run.md`. Setup took about 77 s of commands from `init` to a passing `pkit validate`; nothing crashed. software-analysis and living-docs work fully offline; project-management needs a GitHub repository set up first, and the review panel acts through its merge gate. The stale-docs moment works and makes a clear demo beat. Rough edges filed under the adoption EPIC #775: #2083 (init's next steps), #2084 (documentation roots collide), #2085 (status labels), #2086 (false "question not asked"), #2087 (pm says late that it needs GitHub), #2088 (analysis hints), #2089 (living-docs placeholders pass), #2090 (output noise). #2083 and #2087 are being built for the demo.

**Demo prerequisites:** a fresh GitHub repository for the demo project, created by the maintainer; the internal docs root set before software-analysis installs (`pkit config set docs.internal tech-docs`), until #2084 lands; installs run at a real terminal so the fixer questions are asked.

## Direction change (25 October, later)

The maintainer reconsidered the field report: he wants a **feature demonstration on the agentic platform**. A repository with project-kit and the needed capabilities installed, set up for parallel work across workstreams: two or three agents, each with its own checkout of the same repository, each working on a different area. Possibilities to be discussed; he suggests **finishing the parallel work organization first**.

**The platform's sandboxes run Claude Code** (other runtimes too, but the demo focuses on Claude Code). So project-kit works there in full: agents, skills, rules, the permission hook. An inventory of what project-kit offers for parallel clones today is being gathered.

**Topologies to choose from:**
- (a) **A planner and builders:** one project-manager session slices the work and files it per workstream; two or three platform agents, each a Claude Code session in its own clone, named and bound to a workstream, pull their workstream's issues, build, open pull requests, and land behind the gate. Recommended.
- (b) **Peers:** each platform agent owns a workstream end to end, planning included.
- (c) **One session fanning out:** builders in worktrees of one clone, as this week; it shows nothing of the platform.

## What is built for parallel clones (inventory, 25 October)

- **Built on main:** workstreams in full (DEC-018; `add-workstream`, `create-issue --workstream`, `context-workstream`); `set-instance` records a clone's id, and nothing reads it yet; the ownership seam library, which no command calls; the assignee gate in `start-work` (tells people apart, not clones); integration-branch bases (DEC-013); a decision-number clash warning (`pkit decisions check-diff`).
- **Decided, not built:** claim at creation and release at close (#519), the clash guard (#520), signed listings and `handoff --to-instance` (#521), named instances routed by workstream (#512), `create-instance` (#513), the audit-log facility (#511); a worktree inheriting its clone's id (#1140).
- **Proposed only:** lanes, typed `Blocked by:`, the ready frontier (DEC-025); the ladder (#1548).
- **The project-management README's instance section overstates:** it says create-issue, start-work and handoff-issue write the ownership marker; none does.
- **Gaps that would bite two clones under one login:** clone B can start clone A's issue; two clones starting one issue at once both succeed; nothing shows who owns what; routing by workstream rests on the prompt; dependencies are prose.
- **Smallest set to close them:** #519, #520, #521; #512 for routing; #1140 if agents use worktrees. Order and file overlap need DEC-025.

## (a) and (b) compared on an example

Example project: a link shortener with three workstreams, `api` (a REST service), `web` (a page that calls it) and `docs`.

| Moment | (a) A planner and builders | (b) Peers |
|---|---|---|
| Kickoff: "build a link shortener" | The planner writes the analysis (who uses it, what they do), slices it into issues per workstream, and files the API contract as the first `api` task. The person approves one plan. | Each peer plans its own workstream from the brief. Three plans, written at once, each with its own guess at the API's shape. |
| `web` needs `POST /links` | The plan already orders it: the web form depends on the contract task; the web agent starts with the page layout meanwhile. | The web peer files a request in `api` or waits; the API peer has to notice it. Coordination by issue comments. |
| Both want to edit the shared `README.md` | The planner sees it at slicing and gives it to `docs`. | Nobody sees it until the second pull request conflicts. |
| A task turns out twice as big | The builder stops and reports; the planner re-slices; the person decides once. | The peer re-plans on its own; the person learns of it in its next pull request. |
| The person's load | One conversation, one batch of decisions. | Three conversations, decisions from three directions. |
| Ownership in project-kit | The planner creates every issue, so builders must take them over: needs handoff to an instance or a claim at start (#521). | Each peer creates its own issues, so it owns them at creation (DEC-035 point 3): needs only #519. |
| On stage | A clear story: one plan, three lanes, one gate. Rests on a good plan up front. | Looks more autonomous; riskier live, and project-kit has no built coordination between peers. |

**A middle way:** the planner files one Feature per workstream and the cross-workstream contracts; each workstream agent slices its own Feature into tasks, owning them at creation, and builds them.

## Why not one agent with subagents? (honest comparison, 25 October)

**One session with subagents, as this week:**
- Gains: one mind holds the whole picture, so coordination is free; the planner gives each builder a different issue, so nothing collides and no claim machinery is needed; proven at 156 pull requests a week; the person talks to one agent.
- Costs, lived this week:
  - **One context holds all coordination.** The planner's context filled and was compacted several times; once it lost track of two open pull requests (#1997, #1869) until a later check found them.
  - **One failure stops everything.** A usage limit stopped four builders at once.
  - **Subagents are fire-once.** They cannot ask the person, cannot be continued, and report once; a subagent at the nesting limit cannot dispatch its own reviewers (the #1869 fixer had no Agent tool).
  - **The planner is the bottleneck.** Every review settlement and every merge passes through it, one at a time.
  - **One sandbox, one account, one set of permissions** for every builder.
  - **No memory per area.** Each builder starts cold and re-reads its brief.

**Separate agents, each in its own sandbox and clone:**
- Gains: isolation per agent (permissions, secrets, quota, blast radius); one agent failing leaves the others running; each keeps its own context, and can stay with its area for days and learn it; a person, or several people, can talk to each agent directly; it scales past one machine and one account.
- Costs: coordination must live outside any one mind, in the tracker: claims, a clash guard, visibility of who owns what, dependencies, contracts between workstreams; more tokens, since each agent reads the repository itself; more for the person to watch unless a planner gathers the decisions.

**The key point:** in the one-session model, the coordination state lives in the planner's context, which is fragile. With separate agents it must live in the tracker, which is durable, inspectable and survives a crash. project-kit already puts it there (issues, branches, answers in files, the gate); the clone-ownership pieces (#519, #520, #521) finish it.

**When each wins:** one person, one machine, work that fits in days: one agent with subagents. Isolation needed, several people, work that outlives a session, or one failure must not stop the rest: separate agents. Both compose: each separate agent may use subagents of its own.

## Business value of separate agents, not buzzwords (25 October)

The maintainer asked for real value: does it speed up or improve development significantly?

**Where a pull request's time went last week** (the 100 most recent merged, `pr_stats.py`): median 1.3 hours from open to merge (middle half 0.6 to 2.9); a median 35 minutes between consecutive merges into `main`; at most 7 merges in one hour; CI's full suite takes about 30 minutes (18,724 tests). So for one person the limits are CI, the serial merge into `main` and the person's decisions, not how many agents type code.

**Honest conclusion:** for one person, separate agents add little speed over one agent with subagents. The significant gains are elsewhere:
1. **Development capacity scales with people, not with one session.** One planning session serves one person. A team of five, each directing an agent in their own area, decides five times as much in parallel; project-kit keeps their agents from colliding. This is the platform's business case: it serves teams.
2. **No ceiling on one context.** The planner here was compacted several times in one day and lost track of two pull requests. Small, separate contexts lose less; measurable as dropped or redone work.
3. **Specialised agents, if it holds:** an agent that stays with one area for days should need fewer review rounds than a builder starting cold (this week, #2062 took four rounds as each found more). A hypothesis to measure, not a claim.
4. **Capacity:** one account's limit stopped four builders at once; separate sandboxes spread the load.

**What would speed up both shapes:** a merge queue (#1867) and a faster CI, since they bound merges into `main` either way.

**Proposal: measure instead of claim.** Run the demo project's backlog twice, one agent with subagents and then three separate agents, and report: hours to land the backlog, minutes of the person's time, review rounds per pull request, tokens, and work dropped or done twice.

## Direction: configurable topologies (25 October)

The maintainer agreed to measure, and asked first to finish parallelization in project-kit: project-kit provides the possibility and the adopter chooses the topology. Strategies to support: one planner and several workers; several separate agents, each running its own subagents, each in its own domain, by area (api, web, docs) or by discipline (design, development, testing).

**Started:** #519 (claims written at creation and start, released at close) and #1140 (a worktree reads its clone's id, which subagent workers need) are being built. A design note on configurable topologies is being drafted (`design-topologies.md`), to go to the critic and the architect before the maintainer decides, one decision at a time.

**Decided (25 October):** the topology setup is shared through the project's committed pkit configuration. This overturns project-management DEC-045 point 2 (per-user, machine-local, never committed) for shared platforms; recorded on #512.

**The ownership issues are from 7 July** (#508, #510–#513, #519–#521, filed with DEC-045 the same day), three and a half months and many changes ago (answer files, the merge gate, a separate audit trail in DEC-049, workstreams in their own file). Likely outdated: #512 (per-user topology, now overturned), #511 (overlaps DEC-049's audit trail), #513 (provisioning clones is the platform's job), and #519's claim at creation (in planner-and-workers the planner creates everything, so workers must claim at start). Likely still valid: the clash guard (#520) and the signed listing (#521). After the design note, each is checked against today's code and the new direction, then rewritten or closed. #519's pull request is held until the claim rule is settled.

## Where the analysis comes in (proposed, 25 October)

The method says analysis first: the project manager reads the use cases before slicing, and each planned Feature and Task names the use case it serves (project-management DEC-054); a feature's analysis lands ahead of its code (#1680). So:
1. **Analysis now**, in project-management's analysis (`tech-docs/analysis/project-management/`, which has UC-060 to UC-064 and ACT-planner today): the actors (the person, a planner agent, a worker agent, a domain agent) and the use cases of parallel work, such as configuring the setup, planning across domains, a worker taking its next task, two agents reaching for one task, handing work from design to development, an agent resuming after its session died, seeing who works on what, and measuring a setup. Starting material: the pilot's ten coordination use cases, removed with the pilot (#890), readable at commit f78ec818 (`tech-docs/analysis/use-case-model/use-cases/coordination/`), and the design note being drafted.
2. **Walk the design note against the use cases**, then its decisions with the maintainer, one at a time.
3. **Records:** the setup in the project configuration, DEC-045 point 2 overturned, DEC-025 promoted or replaced.
4. **Rewrite or close the July issues,** each naming its use cases; then build. #519's pull request waits for this.

The analysis can be part of the demo: use cases written first, agents building against them.

## Review of #2103, decisions so far (26 October)

- **ACT-director removed:** the maintainer asked why not the person who onboards a project. The core's ACT-adopter is that person: UC-082 (set up the topology), UC-091 (measure topologies) and JRN-004 become the adopter's; UC-090 (see who works on what) the planner's; the operator still starts each agent's session.
- **An instance's identity, recommended:** a clone sets itself by name (`set-instance api-worker`), the name must be an entry of the committed topology; the number DEC-035 uses for the lowest-wins tie-break and the `instance:N` label is derived from the entry's position, never typed. Refines DEC-035 point 1 and DEC-045 point 1. Taken unless the maintainer objects.

## The maintainer's model of parallel clones (26 October)

1. The adopter defines the topology in a committed project config, shared through git: the seats, each with a role and its workstreams or domain (how they are targeted is open), and the agent a seat acts as, plus settings a seat may need.
2. A clone claims a seat, then acts by that seat's role. Claims are not committed: they live on GitHub (option b).
3. Workers sharing one pool lock an issue and release it when done or stopped (DEC-035's ownership, #519–#521); a dead agent's lock needs a release.
4. **A new kind of issue for shared state** (his words: "living state issue"), as a general mechanism for various configs: one issue per piece of shared, changing state, outside the work hierarchy. Its comments are the event log and its description the current state derived from them (the comment-log substrate DEC-043 and ADR-041 already decide). A seat is the first such state; claiming a seat is the same lock as claiming a task. What is reviewed stays in committed config; what changes at run time lives in state issues.

## UC-082 and the clone's side, decided so far (26 October)

- Seat claims live on GitHub, one **state issue per seat** (option b, then 1): claiming a seat is the same lock as claiming a task.
- **State issues** are a general mechanism for shared runtime state (the maintainer's "living state issue").
- **A clone picks its seat (c):** by name when given (`take-seat api-worker`), else the first free seat, optionally of a role (`take-seat --role worker`).
- Harness-agnostic wording throughout: "an agent session in its harness", never a named harness.
- **Task locks vs seats differ:** a task lock follows the four layers (release on done or stop, renewal by the work, a generous limit, a returning clone re-checks before writing). A seat's idle sensitivity is configurable; **the first mode is the most tolerant: a seat stays claimed until the clone releases it, or the organizer clone releases it by force.** No silence-based expiry in that mode.
- **A clone becomes its seat's agent (c):** the project-manager agent by default, reading the seat's role (planner, worker, lead) and running that role's procedure; a seat may name another agent, which drives the seat's work through the same take, lock and land procedure the project-manager agent's skill provides.
- **How a seat targets its work:** by default no scope: workers take the next ready task from one shared pool, highest priority first, skipping tasks that wait on others; the planner slices work vertically, so one agent can finish a task or Feature end to end across layers; the issue lock keeps agents apart. Scope stays an optional filter: by discipline for specialist seats (design, testing), later by workstream for an owned area. Workstreams as software layers are not the partition (component teams cost cross-layer coordination).
- **The organizer (c):** a seat marked as organizer in the topology (typically the planner's) may force-release other seats, and the adopter can always force-release from any clone; each force release is recorded on the seat's state issue.

## Open questions (one at a time)

1. ~~Audience~~, ~~angle~~, ~~demo format~~: decided above.
2. The skeleton, item by item, starting with the hook.
2. Live or recorded demo of the agent work.
3. Which toy project to build in the demo.
4. A GitHub repository for the demo project (needed by project-management).

## Trial run

A trial install into a scratch project in the workspace, to find the rough edges before we promise anything: see `trial-run.md` when it lands.

## Goal reconsidered (decided 26 October, afternoon)

The maintainer reconsidered Friday: the main goal is to present project-kit itself, its building blocks and the motives behind it. Show how lightweight it is and what it gives without any capability. Present the capabilities too, more briefly. The parallel-clones showcase moves to a later talk, once there are comparison data (one agent without pkit against clones with pkit, plus a day-two change). The seats build loses its Friday deadline. Candidate base: `.agent-workspace/living-docs/talk-outline.md` (18 slides, 6 live demos on the backbone, one slide on capabilities).
