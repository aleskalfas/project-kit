---
id: DEC-004
title: The software-engineer writes the conventions a walking skeleton sets into the conventions corpus
status: proposed
date: 2026-10-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a walking skeleton is the thin slice, end to end, that a foundation builds before the slices of new work are planned. It settles conventions the slices share, such as how the code and its tests are laid out. When the software-engineer builds one, it writes each of those conventions into the project's conventions corpus, which it reads first. A person accepts the entries before the skeleton's code is built on them, so every later slice reads them as the project's rules. Where the corpus offers no location the project owns for them, the agent writes none and says so.

## Context

[software-engineering:DEC-001-producer-agent-and-conventions-seam] has the software-engineer read the project's conventions corpus before it writes code, and conform to it. The corpus is the project's own, found where the project's overlay points (point 2). An empty corpus is a normal early state: the agent says so, works by ordinary judgement and never invents a convention to fill the gap (point 5). How the corpus fills is deferred until real evidence shows it, as DEC-001's Implications say.

[project-management:DEC-060-foundation-before-slices] decides that where the Tasks of new work would share a choice that nothing settles, a foundation comes first. It is one Feature, whose body lists the choices it settles. Its Tasks hold accepted records of the architectural choices, then a walking skeleton built on them, whose merged code settles the choices of convention (point 2). The slices are planned only once the foundation is done, against the records and the skeleton's code (point 3).

A convention settled only in code reaches a later agent only where that agent finds the code and reads the same pattern from it. The software-engineer reads the corpus first, and an empty corpus sends it to its own judgement. Each slice's agent then reads the skeleton in its own way, or not at all, and the slices drift as [project-management:DEC-060] warns. The code-review panel also reads the project's rules from the corpus, so it has no rule to hold a slice to (project-kit#2152).

## Decision

**When the software-engineer builds a walking skeleton, it writes into the conventions corpus each convention the skeleton settles, and a person accepts the entries before the skeleton's code is built on them. Where the corpus offers no location the project owns for them, the agent writes none and says so.**

### 1. The software-engineer writes each convention the skeleton settles

A walking skeleton is the Task of a foundation's Feature that builds one thin slice end to end ([project-management:DEC-060] point 2). When the software-engineer builds it, it writes into the conventions corpus each choice of convention the skeleton settles. These are the choices of convention the Feature's body lists, and any other the skeleton settles that later Tasks would otherwise each make.

This record binds the software-engineer alone. Any other builder of a skeleton, a person or another agent, is bound by [project-management:DEC-060] points 2 and 5, which point here.

The agent writes nothing for a choice that the corpus or an accepted record already settles, or one that binds nothing beyond the skeleton. An architectural choice, such as a library or where state lives, is a record's to decide and never an entry ([project-management:DEC-060] point 2). Where the records leave one open, the agent makes none in its place, and says so on its Task.

### 2. An entry states a rule, where the corpus keeps the project's conventions

- **A rule.** Each entry states its convention as a rule that a later change can follow without reading the skeleton. It may name the skeleton's code as its example. A convention that follows from an accepted record cites the record rather than restating its choice.
- **Its form and place.** An entry takes the form that the corpus already gives the project's own conventions, in the place that keeps them. A place is a spot, such as a file or a section of one, inside the location point 4 finds. In an empty corpus, the agent proposes a form and a place, and the person accepts them with the entries.
- **Where it binds.** The entries bind only as the corpus's own rules bind. Where the corpus is a project rule set, this record names the software-engineer as one of its writers (COR-051 point 6). The agent also proposes what the set then needs under COR-051 point 7, such as a new major version, and a scope that selects the files the slices will write. The person accepts these changes to the set with the entries.

### 3. A person accepts the entries before the code is built on them

- **The order.** The agent drafts the entries first, and a person accepts them in the skeleton's change before the skeleton's code is built on them. Where building the code shows that an entry does not hold, the agent changes the entry. The person accepts the changed entry before the change merges.
- **Nobody to ask.** Where the agent cannot reach a person to accept the entries, it builds no code on them. It hands back to whoever started it, with the drafted entries and its question, and leaves its Task In Progress, waiting for the answer. It tells that it cannot ask from the question itself, never from the wording of its task, as the friction writers do where they return their commands and run none (`.pkit/agents/README.md`, "Friction writers"). Started by another agent, it cannot ask either, unless the adapter in use declares that its question reaches the person.
- **A refused entry.** An entry the person refuses leaves the change. As the person says, the agent drafts another for its choice, or leaves the choice to the skeleton's code or to a record.
- **An act of its own.** The person accepts the entries having read them, since a person's review accepts a rule (COR-051 point 4). Authorising the merge, before the run or after it, accepts none.
- **Status.** Where the corpus gives its entries a status, as a rule set does, each entry stays proposed until the person accepts it. Where the corpus gives none, the change's description lists the entries, and the person accepts them there.
- **Origin.** Where an entry needs an origin, as an accepted rule does (COR-051 point 5), the origin carries the accepting person's words.

### 4. Where the corpus offers no location the project owns, the agent writes none

Where the project keeps its conventions is its own choice (DEC-001 point 2), so the agent never picks a location for them. It writes entries only inside the one location, among those `<project-conventions>` names, that passes both tests below. The place it writes inside that location passes them too. The tests decide in place of the agent's judgement:
- **The ownership test.** The path lies inside the repository, and the methodology's ownership predicates count it neither as content the methodology manages nor as a copy that a sync or a component's pinned source writes (`.pkit/lifecycle/README.md`, "The ownership predicates"). A rule set a component ships is such content, and a project never edits it (COR-051 point 6).
- **Another agent's paths.** No other agent's `owns`, resolved through the agent overlay as the deploy resolves it, contains the path. A path has at most one owning agent, which answers for it (COR-013).

It writes none where the corpus offers no such location, or no such place:
- it names nothing
- none of the locations it names passes both tests, or more than one does
- a test excludes the place inside the location that the entries would take

The agent then says so before it builds, and the skeleton's code alone settles the conventions ([project-management:DEC-060] point 2). Its hand-off lists each convention the skeleton set, with the entry it would have drafted, so the person can name a location and place the entries before the slices are planned.

### 5. A foundation's conventions stay in the corpus

- **A skeleton folded into the first slice.** Where the person folds the skeleton into the first slice ([project-management:DEC-060] point 2) and the software-engineer builds it, the agent writes the conventions that slice settles, as points 1 to 4 say.
- **A change to a convention a foundation set.** It goes through a Task of its own that changes the skeleton's code ([project-management:DEC-060] point 5). Where the software-engineer builds that Task, it changes the convention's entry too, where the convention has one, and a person accepts the changed entry as point 3 says.

### 6. Other work is left as DEC-001 has it

This record decides only the conventions a foundation settles. In other work, DEC-001 point 5 stands: the software-engineer never invents a convention to fill a gap. Whether other work writes the conventions it sets stays open, as DEC-001's Implications leave the corpus's content.

## Rationale

**Why the corpus, and not the code alone.** The software-engineer reads the corpus first, as the project's authority on its conventions. A convention held only in code reaches it only where it finds that code and reads the same pattern from it. Agents in separate clones read the skeleton each in their own way, so the slices drift one level below the choices [project-management:DEC-060] settles. The code-review panel blocks on a rule the corpus states ([software-engineering:DEC-002-code-review-panel] points 3 and 4), never on one it would have to infer.

**Why before the code is built on them.** A rule binds only once a person accepts it, as a decision record does (COR-051 point 4), and code rests only on what is accepted. A convention found wrong is cheaper to change before the skeleton's code repeats it. An entry the code then disproves is the one exception: the code that disproved it stands before the changed entry is accepted again, at the latest before the merge. So the entries and the code agree when they land.

**Why it waits when nobody can accept.** Code built on entries nobody accepted would rest on drafts, which point 3's order exists to prevent. Built first and asked later, the skeleton would already repeat the entries the person is asked to judge. An agent that can ask nobody hands a person's decision back unmade, as the friction writers do.

**Why in the skeleton's change.** The entries are drafted and accepted in the change whose code first follows them, and an entry the code disproves is reviewed again beside that code. The slices are planned once the foundation is done ([project-management:DEC-060] point 3), so the entries must stand by then. A change of their own after the skeleton would hold the slices back for a second review.

**Why a person accepts them, as an act of its own.** The agent chooses the skeleton's conventions. Entries that bound once it wrote them would make its own choices the project's authority. DEC-001 makes the corpus that authority and the agent its applier, and a person's acceptance keeps it so. A merge authorised before the run is read by no one, so it cannot accept entries nobody saw.

**Why no location is picked for the project, and why tests bound it.** Where the project keeps its conventions is its own choice, and the conventions outlive this capability (DEC-001 point 2). A location the agent picked could be one the project never reads. Content the methodology manages or copies in is rewritten by its source, so an entry there would be lost, and a path another agent owns is that agent's to answer for. The tests reuse predicates the methodology already asks of a path, and they choose among several locations too, so the agent's own reading never widens where it writes.

**Why this record binds the software-engineer alone.** This capability decides what its own agent does. Who builds a skeleton, and in what order, is for the record that sets the foundation to decide. So [project-management:DEC-060] points 2 and 5 bind every other builder, a person among them, where software-engineering is installed, on the reasons this record gives for the corpus.

**Why only a foundation's conventions.** Every change makes small choices, and writing each into the corpus would turn it into an inventory of them. A skeleton is the change whose work is to settle the conventions later work shares. How other work adds to the corpus needs evidence this record does not have.

**The cost.** The agent stops for the person's acceptance before it builds, so the skeleton takes longer, and the slices wait for it. Where it can reach no person, its Task waits In Progress until one answers. The corpus also starts from the agent's own choices, accepted by a person. Where it grew this way, a comparison of the agent with and without the corpus, which DEC-001 keeps possible, partly measures the agent against itself.

### Alternatives considered

- **The skeleton's code alone settles its conventions.** Rejected: each agent reads the pattern for itself, and the reviewers have no rule to hold a slice to.
- **The entries are decided in the foundation's records Task.** Not taken: [project-management:DEC-060] gives the conventions to the skeleton, and the records Task holds the architectural choices. Drafted in the skeleton's change, the entries travel with the code that first follows them.
- **A Task of its own for the entries, between the records and the skeleton.** Not taken: a convention often shows only once the skeleton is built, and a Task apart would draft the entries away from that code. How the foundation's Tasks are cut is project-management's to decide.
- **The entries are accepted at the merge, with the code.** Rejected: the skeleton's code would rest on drafts, as "Why before the code is built on them" says.
- **The entries are written in a Task after the skeleton.** Rejected, as "Why in the skeleton's change" says.
- **Authorising the merge accepts the entries.** Rejected, as "Why a person accepts them, as an act of its own" says.
- **This record binds whoever builds a skeleton.** Rejected, as "Why this record binds the software-engineer alone" says.
- **A category of its own for where entries go,** one the agent writes, beside the one every consumer reads. Rejected: two categories for one corpus can point at different locations. The agent writes the project's files as it writes code, and point 4's tests keep it off content the project does not own.
- **`owns: [<project-conventions>]` on the software-engineer.** Rejected for two reasons. A reference in `owns` makes the category a hard one for the agent, so every install that does not define it would skip the agent at deploy, where an optional read deploys without it ([pkit:ADR-052] points 1 and 2). An empty list, which deploys a write category inert ([pkit:ADR-051]), would leave the agent no corpus to read. And `owns` names the paths an agent answers for (COR-013), while no capability owns the corpus ([pkit:ADR-013] point 2) and this record leaves it with the person who accepts the entries.
- **Every change writes the conventions it sets.** Not taken, as "Why only a foundation's conventions" says.
- **A decision record for each convention.** Rejected: the software-engineer and the reviewers read conventions in the corpus, not in the records. A record for each one-line convention is also the weight that COR-051's Context names.
- **A point added to DEC-001 in place.** Rejected: the choice rests on [project-management:DEC-060], and carries reasons and alternatives of its own. It narrows DEC-001 point 5, which points here.

## Implications

- **The software-engineer's definition** says what it writes to the corpus when it builds a skeleton, that it drafts the entries before the code, and what it does when it can ask nobody. It names the predicates behind point 4's tests. Its line that it does not author the corpus says when it drafts entries for it.
- **The README's account of the corpus** says that a foundation's skeleton fills it.
- **DEC-001** gains a pointer to this record at point 5, where it keeps the agent from inventing conventions, and in its Implications, where the corpus's content is deferred.
- **[project-management:DEC-060] points 2 and 5** point to this record. A person accepts this record before the edits that rest on it land, and decides that refinement of DEC-060 as a decision of its own (the decisions README, "Refining an accepted record").
- **No command changes, and `<project-conventions>` stays an optional read,** in no agent's `owns`. No command answers point 4's tests for a path, so the software-engineer calls the ownership predicates and reads the agents' resolved `owns` itself. A read-only command for both is a later step, once the tests recur. No check reads whether a skeleton wrote its entries, and none at deploy keeps the agent off a path the tests exclude, so the reviewers of its change and the person who accepts the entries see where it wrote.
- **Named, and not decided here,** since each is project-management's to decide:
  - whether a skeleton's Task lists the corpus entries among its acceptance criteria
  - whether the first plan flags a corpus that offers no location, at its approval gate
  - how batch planning and the work loop carry the pointer of [project-management:DEC-060] points 2 and 5, and whether an accepted entry settles a choice as its point 1 counts one
  - how a skeleton's Task waits In Progress for the person's answer, where a claim on it can lapse ([project-management:DEC-059-topology-of-seats] point 9), which DEC-060's Implications leave open for a Task that waits
