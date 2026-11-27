---
id: DEC-004
title: The lean coach guides a session through the method, and the person judges
status: accepted
date: 2026-11-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability ships one agent, the lean coach. A session opened with it is in the method from its first reply: the coach loads the skill, says where the ideas stand, and from then on guides as the skill does. It has no tool that edits a file, and writes an idea's files only through the commands. Where no person answers in its conversation, it writes nothing and asks nothing. Any agent that follows the skill explains the whole method, in its own words, takes a judgement only from the person's own answer in its conversation, and drafts nothing where no person answers. The coach is no project's default agent unless the project makes it one.

## Context

The capability's main way in is a conversation with an agent through its skill ([lean-business:DEC-001-lean-business-discipline] point 3), and it shipped no agent of its own. A session opened as a general agent, which may load the skill on its own and may not. Until it does, it answers as a general agent would.

Once loaded, the skill reaches each step only as far as the agent keeps reading it. In Claude Code, a compaction of the conversation keeps the system prompt, re-attaches the start of each skill invoked within a budget, and brings back only a few of the files the agent read, the most recently changed first ([skills](https://code.claude.com/docs/en/skills.md) and [context window](https://code.claude.com/docs/en/context-window.md), read on 2026-11-24). The skill's sub-procedures are such files. And a skill can only ask that every write go through the commands, since the agent that follows it keeps whatever tools its session gives.

Two questions about any agent that follows the skill came up with the coach. Where no person answers in its conversation, as with a helper another session dispatched, nothing said whose answer it may record. And a person may ask about a part of the method the capability leaves for later.

## Decision

### 1. One agent, the lean coach

The capability ships one agent, `lean-coach`, a session's guide through the method. Its definition holds only what is the coach's own:

- how it reads the skill (point 2)
- the briefing in its first reply (point 3)
- what it does where no person answers (point 4)
- its tools (point 5)

The skill holds every step and every rule on judgements, and the definition cites them, never restates them (COR-006). The skill stays any agent's, so a session without the coach guides through it as DEC-001 point 3 says.

### 2. It reads the skill, and reads it again

- **When a session starts,** it loads the capability's skill through the harness's tool for skills, so the harness keeps its text through a compaction where it can.
- **Before each step,** it opens the step's sub-procedure afresh. Before each judgement, it reads again the skill's rules on judgements, its shared framing. Neither is followed from what an earlier turn remembered.
- **Where the harness refuses that tool,** it reads the skill's files with the tool that reads a file, and knows that a compaction may then keep less of them.

This standing rule lives in the definition, which the harness keeps as the session's own instructions.

### 3. It briefs in its first reply

DEC-001 point 10 has an agent read the briefing before it proposes anything, and the skill opens each session with it. The coach does it unprompted: its first reply, whatever the person's first message, says where the ideas stand and what waits for them, from `pkit lean status`.

### 4. Where no person answers, it writes nothing

Where no person answers in its conversation, as when another session dispatches it as a helper, or a run starts it with a prompt that no person attends, the coach writes nothing and asks no judgement:

- it reports where the ideas stand and the check's findings, leaving out the bar and the estimates of an experiment not yet declared (point 9)
- it explains the method
- it says that the work waits for a session with the person, started as the coach

### 5. Its tools

- **A grant.** The definition grants the tools the coach has, so a tool it does not name is not given, a later harness release's included (COR-013 point 7). It is granted the tool that reads a file, the session's shell, the tool that loads a skill, and the tools that search files where the harness has them.
- **Withheld by the grant:** every tool that edits a file, the web tools, any connected server's tools, and the tool that starts another agent.
- **A limit on what the shell does.** Through it the coach runs only the `pkit lean` commands, the methodology's read-only commands that core's rules ask before a change, the commands that read files and version control's history, and a commit of an idea's files on the person's word, as the skill's end of a session says. So its only writes are the `pkit lean` commands and that commit, and it runs nothing that brings the web into the conversation or starts another agent. The grant removes the likeliest ways around this limit; the rest rests on the definition alone. Its definition names none of the commands that write an answer on an artefact: where a commit owes such answers, the coach commits nothing, and gives the person the commands for a session that can write them and have them checked.
- **Its costs are accepted.** The coach keeps no intermediate files, its drafts living in the conversation. A session it opens has no file editing, no web and no other agents, so a person who wants those works in another session, as they do for a commit that owes answers on artefacts.
- **The lenient posture.** The permission model's posture decides a call no grant covers: a lenient one leaves it to the harness's own rules, a strict one denies it (the permissions README, "Grants and verdicts"). A strict posture does not suit the coach. The person's words reach the commands as arguments, and a strict posture denies a command wherever they hold a construct it does not trust, such as a parenthesis or a dollar sign, whatever grants the project holds. So a project that runs the coach keeps the default, lenient posture.

### 6. Starting it

- **For one session,** a person starts the coach as the session's agent. The README says how.
- **For every session of a project,** the project names the coach its default through the project's side of the settings merge (COR-002). A project has one default agent. Where another holds that place, such as a work tracker's agent, the person starts the coach for each session on an idea. The README says how the merge orders the settings that name a default. The coach fits as a default in a repository kept for ideas, since every session there has only the coach's tools.
- **The capability makes no agent a default,** and ships no command that makes one. A command like project-management's default-agent toggle ([project-management:DEC-030-capability-contributed-adapter-overlays]) waits until a use asks for it (COR-007).
- **Where the ideas live,** in a product's repository or one of their own, this record decides nothing. Either serves.

### 7. Whose answer any agent records

An agent that follows the skill, the coach or another, takes a judgement, or the person's words for the files, only from an answer the person gave in its own conversation, and runs the skill's confirmation step with the person there. None of these is such an answer: an answer another session passes on, a message from another session, a prompt the session scheduled for itself, and the prompt of a run no person attends. DEC-003 point 5's "once the person has answered in the session" means this.

### 8. Any agent explains the whole method

An agent that follows the skill explains any part of the method the person asks about, in its own words, the parts the capability leaves for later included (DEC-001 point 2). For such a part it says that the capability holds no data of it, and where its finding goes in the files, such as an experiment's result. Explaining a part holds no data, command or judgement of it, so it carries none of the part. Where a question goes beyond the method, the agent says so before it answers, so the person knows the answer is not the method's.

Its own words reach this explaining too: no passage of the book, even when asked to quote one, and no wording of a template the book prints for any part of the method (DEC-001 point 5).

### 9. Where no person answers, any agent drafts nothing

An agent that follows the skill, the coach or another, drafts nothing for the files where no person answers in its conversation: no judgement and none of the person's words. In what it reports, it leaves out the bar and the estimates of an experiment not yet declared, since each estimate is a guess made alone before the declaration ([lean-business:DEC-002-lean-business-data-model] point 9). It says that the work waits for a session with the person.

## Rationale

**Why an agent beside the skill.** A session opened as the coach is in the method from its first reply, with no need for the agent to load the skill on its own. The rule to read the skill again before each step and each judgement lives in the definition, which the harness keeps as the session's instructions. And the grant leaves out the file-editing tools, the likeliest way an agent writes around the commands.

**Why it cites the skill and never restates it.** An agent references and does not embed (COR-006). Restated rules would drift from the skill's, and nothing would say which text wins. The rules for every agent that follows the skill (points 7, 8 and 9) live in the skill, since a person may do the capability's work with any agent.

**Why an answer only from the agent's own conversation.** The commands hold a judgement to the person through a run's claim that they decided in the session, and the skill has the agent show the person the command's own question before it records anything (DEC-003 point 5). An agent with no person in its conversation can neither check that an answer passed on is the person's nor show them the question.

**Why a helper drafts nothing.** A draft returned to a session that follows no such rule could reach the person with an experiment's bar before their own estimate, which they make alone (DEC-002 point 9), or be recorded from an answer that session passes on.

**Why a grant, where project-manager has a withheld list.** Project-manager is a project's working agent, and it needs the session's tools ([project-management:DEC-068-session-agent-tools]). The coach needs few. The tools it must lack are the editing tools, the web tools and the tool that starts another agent, and it is a default only where a project chose it, so a grant of those few costs it nothing it needs.

**Why no web tools.** Numbers from outside would anchor the estimate, the one answer the person makes alone (DEC-002 point 9). Finding out about customers is run outside the capability, and comes back as an experiment's result (DEC-001 point 2).

**Why no other agents.** An agent the coach started would have its own tools and its own rules, so none of the coach's limits would hold for what it did.

**Why no answers on artefacts.** Such an answer judges another of the project's documents, which the method does not reach, and a reviewer other than its writer checks it (core rule 20), which the coach cannot start. So a commit that owes one waits for a session that can do both.

**Why no default.** A project's sessions open with one agent, and which one is the project's choice. Two capabilities that each set it would collide, which project-management's toggle does not support.

**Why explaining a part left for later does not carry it.** DEC-001 point 2 has each such part join by a record of its own, because joining means data, commands and judgements the capability must hold. An explanation holds none of these, and a person who runs the part outside the capability needs to know what it is.

**Why no storyboard.** A storyboard is recommended for a scripted scenario (COR-016). The coach's dialogue is the skill's: its steps for asking a judgement and each sub-procedure's example. Its own turns, the briefing and the report where no person answers, are a status and a sentence, not designed dialogue.

### Alternatives considered

- **The skill alone.** Rejected: a session would still open outside the method, and nothing would hold the habit of reading it again.
- **The skill's rules restated in the definition.** Rejected: two texts would drift.
- **Points 7, 8 and 9 in the coach alone.** Rejected: a person may follow the skill with any agent, and that agent needs them too.
- **An agent for each step.** Rejected: one idea runs through one loop, and the steps are already the skill's sub-procedures.
- **A withheld list, as project-manager's.** Rejected: a tool a later release adds would reach the coach until someone withheld it, and the coach needs few.
- **A helper that drafts and returns questions.** Rejected, as the rationale says.
- **The coach as default on install.** Rejected: it would take a project's sessions from the agent the project chose.
- **Web tools, to research alternatives and markets for the person.** Rejected for now, as the rationale says. A later record may grant them once a use shows what research belongs in the loop.
- **A deny on the shell's reach, shipped by the capability.** Not now: it binds only where the permission model judges a call as the coach's. Where the coach is the project's default agent, the model judges the person's own typed commands as the coach's too, so the deny would bind on them, and a session started with the coach for that session alone may not be judged as the coach's at all (the permissions README, "Default-agent subject resolution"). The definition's limit holds either way.
- **Holding a draft's bar out of the status's structured output.** Not now: the experiment's file holds the bar too, so point 9 is needed in any case.

## Implications

- **DEC-001 point 3 is refined.** Its first way in comes to read: "a conversation with an agent through the skill, the main way in: the capability's lean coach, or any agent that follows the skill, the skill drafting through the commands (refinement per [lean-business:DEC-004-lean-business-coach])".
- **DEC-003 point 5 is refined.** Its bullet on a run off a terminal comes to read: "off a terminal, it moves only with an explicit flag that says the person decided, which an agent passes only once the person has answered in the session, in its own conversation with them (refinement per [lean-business:DEC-004-lean-business-coach])".
- **The skill** carries points 7, 8 and 9. Its rules for asking a judgement name the answers that are not the person's and what an agent does where no person answers, and its section on the capability's own words gains the explaining of the method.
- **The agent** is stamped as `agents/lean-coach.md` through `pkit new agent lean-business lean-coach`, and deployed by the adapter with the capability's skill.
- **The README** lists the agent under what the capability ships. Its setup says how to start the coach for a session, how a project makes it the default and how the settings merge orders a default, and which grants the coach's commands need under the permission model, which judges every call of a session whose default agent is the coach as that agent's. It anchors the agent and this record. Since it anchors DEC-001 point 3 and DEC-003 point 5, the refinements flag it for revalidation.
- **A test** holds that the grant names no tool that edits a file, no web tool and no tool that starts an agent.
- **A changeset** of the capability declares the agent.
