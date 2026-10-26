---
id: COR-064
title: A reviewer checks every answer no change owes, which a person may delegate to an agent
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** some answers on artefacts are owed by no change. An example is an answer on a page that two changes left out of date by merging at once. Another is a reason why an artefact has nothing to anchor to. Each is a person's to accept, word for word, before anything writes it.

A person who decides what reaches the project's default branch may instead name one agent, in the project's committed configuration, to decide these answers in a person's place. The agent never decides an answer it drafted. It judges from what the files hold, and refers to a person what only someone's account could settle, such as whether a change was meant. A reviewer checks every answer no change owes, whoever decided it, as a change's own answers are checked. The person is told afterwards what the agent decided, and is not asked. Everything else a person decides stays theirs.

## Context

The anchors-and-friction record splits the answers on artefacts in two (COR-050 point 3).
- **The answers a change owes.** The agent making the change writes them without asking. A reviewer other than that agent checks them, and the person who authorises the merge is told what changed, as information.
- **Every other answer.** A person is shown it, word for word, and accepts it before it is written. So is every reason for having no anchors (COR-050 point 1).

Where agents do most of a project's work, the second kind comes in a steady stream. Two changes that merge at once leave a page out of date on the default branch, which neither was asked about. An agent proposes an answer for the debt the whole-repository check reports after each merge. A project describing itself for the first time gives a reason for each artefact with nothing to anchor to. Each waits until a person reads it and accepts it.

What the person adds there is a check of an artefact against what it rests on. That is the check a reviewer is placed to make, with the artefact and its anchors in front of it. A person asked for it many times a day accepts by habit, which is the rubber stamp the anchors-and-friction record guards against. Or the person asks not to be asked, and the debt waits.

What a person cannot hand to an agent is different. Accepting a decision, authorising a merge and judging whether a change was meant decide what the project does. No reviewer's check stands in for those.

## Decision

**A person who decides what reaches the project's default branch may name one agent, the *delegate*, in the project's configuration, to decide in place of a person the answers no change owes. The delegate never decides an answer it drafted, and judges from what the files hold. A reviewer checks every answer no change owes, whoever decided it, from the change check's own list, and blocks the merge when one does not hold. The person is told afterwards what the delegate decided, as information. The delegation covers these answers and nothing else a person decides.**

With no delegate named, every such answer is a person's, as COR-050 point 3 sets out. That is the default.

**The person** in this record is a person who decides what reaches the project's default branch: one who authorises merges into it, or commits to it directly. Such a person names the delegate. The delegation is the project's, and the delegate decides in place of any person who would otherwise decide an answer no change owes.

### 1. The answers a delegate decides

A delegate decides, in a person's place, the answers that COR-050 point 3 leaves to a person. These are the **answers no change owes**:
- an answer an agent writes on an artefact its change was not asked about, such as one for the debt the whole-repository check reports
- a revisit entry for a link's target that the change check does not ask for (COR-050 point 16)
- a revalidation that replaces revalidations answered apart, where the change was not asked for it (COR-062 point 7)
- a reason for having no anchors (COR-050 point 1)

The answers a change owes stay as COR-050 point 3 sets them. The agent making the change writes them, and a reviewer checks them.

**Deciding** is what a person's decision is in COR-050 point 3. The delegate reads the artefact, the outcome, and the justification or reason, word for word. It accepts the answer, rewords it within the bounds this record's point 3 sets, or declines it before anything writes it. The words it accepts or gives are the ones written.

**A component keeps its own.** Where a component's record says that a person decides an answer on its artefacts, that answer stays a person's until the component's record hands it to the delegate.

### 2. Named in committed configuration, by the person alone

- **Where.** The friction key of the backbone configuration (COR-050 point 14) names the delegate: one agent, by its name. The name is the agent's identity, whichever run of it decides. It names none by default.
- **Only the person names it.** The key is written on the person's own word, naming the agent, under the consent the configuration asks (COR-048 point 5). No agent writes the key on its own initiative, with its own name or another's.
- **The default branch holds it.** A name counts where the default branch holds it. So naming a delegate takes a change into the default branch, and no change names a delegate for its own answers. The delegate decides only under its definition as the default branch holds it, so an edit to it that has not merged never decides.
- **Shown before it counts.** A change that names, changes or removes the delegate is shown to the person who authorises its merge, among what the change does. An authorisation given before that person could see it does not cover it.
- **Withdrawing.** A person's word stops the delegate in the session where it is given. The name leaves through a change, and once the default branch drops it, no agent decides as the delegate. The answers no change owes are then a person's again. What the delegate decided before stays as written, and a person may replace any of it (point 5).
- **A name that names no agent.** Validation fails a name that no agent of the project carries, saying to name another or remove it. An agent of the project is one the project, an installed component or the methodology ships. Until the name is mended, nobody decides as the delegate. The name is an agent's, not a component's, so an uninstall does not offer to clear it, as COR-048 point 2 asks for a component's name. An uninstall that takes the agent away fails validation in its own change, where the person mends the name.
- **An agent that knows the role.** An agent acts as the delegate only where its definition says when and how. Its definition then declares that it reads this record (COR-013). Validation warns of a name whose agent's definition does not, since naming it makes no agent decide.

### 3. Never on an answer it drafted, and from what the files hold

- **Another's draft.** The delegate decides an answer another agent drafted. That may be an agent that proposes answers on artefacts, or an agent making a change that found an answer the change check did not ask for. Such an agent names the answer for a decision and writes nothing until it is decided.
- **Not its own.** The delegate never decides an answer it drafted: one it proposed, or one its own change found unasked. Such an answer is a person's, as with no delegate.
- **Rewording within the draft.** The delegate may reword a justification, a reason or a sentence, as a person may. It never changes the outcome or the content a draft proposes, and never adds an answer the drafter did not propose. Such a change is a draft of its own, which goes back to the drafter or to a person.
- **Applying is not drafting.** An answer the delegate decided may be written by the agent that drafted it, or by the delegate, in a change made for that purpose. Writing it does not make the answer the delegate's own draft. Nor is deciding a review: the delegate judges a draft before anything writes it, not work under review.
- **From what the files hold.** The delegate judges an answer from what the artefact and its anchors hold, read from the repository's files. An account of them, such as a commit message, a pull request's text or a drafter's evidence, is a lead to read, never a ground. An answer that only such an account could settle goes to a person. Whether a change was meant is one such question, where the files do not settle it.
- **Against the friction it judged.** A decision stands only against what the artefact rested on when the delegate judged it. Where that changed before the answer is written, the answer is decided again.
- **Referring.** The delegate may refer any other answer to a person instead of deciding it.

### 4. A reviewer checks every answer no change owes

- **Every one, whoever decided it.** A reviewer checks each answer the change check marks as not asked for, and each reason for having no anchors, that a change writes. It checks them in every project, a delegate named or not, since the check cannot tell who decided one. It blocks the merge, or the direct commit, when one does not hold.
- **Not the delegate, not the drafter.** The reviewer is neither the delegate nor the agent that drafted the answer. Which reviewer is the project's choice, as in COR-050 point 3.
- **From the check's own list.** It works from the change check's own list (COR-050 point 12), never from an account the delegate or the change's author composed.
- **Against what each answers.** Such an answer answers no question the change raised. The reviewer checks a revalidation or a deferral against the explanation of the artefact's friction at the change's base (COR-050 point 13). It checks a revisit entry against its source and its target at the change's head. It checks a reason for having no anchors against what the artefact says. A deferral names an open follow-up, and an `updated` answer has a sentence that matches what changed (COR-050 point 3).
- **A person's answer the reviewer blocks.** A person who decided an answer the reviewer blocks may skip the review on record. The answer then stands unchecked by the person's recorded choice, the limit COR-050 point 3 accepts.
- **No reviewer, no delegation.** Where the project chose no reviewer for these answers, or chose the delegate itself, the delegate decides nothing, and the answers stay a person's. That is the delegate's discipline, which no check verifies, as COR-050 point 3 says of who read an answer.

### 5. The person is told, not asked

- **Afterwards, as information.** Each answer the delegate decided reaches the person after it was decided. The person learns the artefact, the outcome and the words, and that the delegate decided it.
- **Where.** An answer it decided reaches the person who authorises the merge of the change that writes it, with the change's answers (COR-050 point 3). An answer it declined reaches the person it works for, in its own report of what it decided, with why. It reaches the person who authorises the merge too, with the change that writes the answers it accepted, where there is one. A component that gathers for the person what was decided may bring these together in one report.
- **Never a gate.** A change carrying such answers merges under the same authorisation as any other.
- **Within reach.** A person may replace any answer the delegate decided with a later one (COR-062 point 5), or withdraw the delegate (point 2).

### 6. What stays the person's

The delegate judges an artefact against what it rests on, or that it rests on nothing. It decides nothing else a person decides. Among what stays a person's:
- naming and withdrawing the delegate (point 2)
- accepting a decision record or a rule, and every change to what an accepted one decides
- authorising a change's merge into the default branch
- a question an agent asks in place of proposing an answer, such as whether the change that left an artefact out of date was meant
- every consent a record asks of a person, such as before a configuration key is written (COR-048 point 5)

## Rationale

**Why a delegate, not a person deciding each answer.** An answer no change owes is a check of an artefact against what it rests on. The person reads it without the context an agent had in front of it, and a stream of such checks is accepted by habit. A delegate reads each answer with that context, and a reviewer checks the result. So a person keeps the decisions only a person can make (point 6), and the answers stop waiting.

**What the delegation does not change.** The person still authorises each merge into the default branch, and still answers each question only they can settle. The delegation moves them from reading each answer to being told of it. It does not take them out of the merge.

**Why a person still decides by default.** A project that wants each such answer read by a person keeps that by naming no delegate. The delegation is a choice, made once in review, and withdrawn by a change.

**Why a person who decides what reaches the default branch names it.** The delegate decides answers that reach the default branch. Only a person who lets changes reach it is placed to hand that decision on, and in a team any such person may. A name in the project's configuration binds the project, so every such person sees it in review, and any of them may withdraw it.

**Why committed configuration, on the default branch.** A name in a file the project commits is visible in review and in history. A name given in a session, or by an instruction to an agent, leaves no record and could be claimed by any agent. Read where the default branch holds it, a name counts only once its change has merged. So a change cannot make its own unasked answers the delegate's. The delegate's definition is read there too, so a change that edits it decides nothing until it merges.

**Why a change to the name is shown before it counts.** Naming a delegate hands it decisions a person made before. A merge authorised without seeing that change would hand them on unseen.

**Why a person's word stops the delegate in its session.** Stopping errs toward more asking, which harms nothing, so it needs no merge. A word reaches only the session where it is given, so the change that drops the name is what stops every other.

**Why the delegate never decides its own draft.** An answer no change owes has no change in the diff that raised it. Where one agent drafted it and another decided it, the drafter chose what to write and the delegate chose whether to write it. Where the drafter decided its own draft, the second choice would be gone. So the delegate may reword the words of a draft, but never its outcome or its content. A new outcome or new content is a draft of its own.

**Why it judges from the files, and refers what only an account settles.** A proposal's evidence, a commit message and a pull request's text are words someone wrote, and words can steer an agent. A person reading them can be misled too, but the delegate is an agent. Holding its judgment to the files bounds what steering can do. An answer stands only where the artefact and its anchors bear it out, and the reviewer checks that against the same files. A fluent reason the files do not contradict can still pass, and that is the hazard left. Whether a change was meant often rests on such an account alone, so a person settles it.

**Why a decision stands only against what it judged.** The delegate judged the artefact against what its anchors held then. A later change under it is a question nobody judged. Written anyway, the answer would cover it unseen.

**Why a reviewer checks every answer no change owes.** The delegate is an agent, and an agent can write a fluent reason that is wrong. The check cannot tell (COR-050 point 3). An independent reviewer is what replaces the person's reading, so without one there is no delegation. The check cannot tell who decided an answer either. A reviewer that checked only where a delegate is named would read the configuration at one commit, while the delegate decided under another. A withdrawal landing between them would leave the delegate's answers checked by nobody. Checking every such answer removes that question, and a person's answer that holds passes, so the check costs little. It also catches an answer an agent says a person accepted when none did.

**Why the reviewer is neither the delegate nor the drafter.** Each of them has judged the answer already. A reviewer's check is worth its independence.

**Why a reason for having no anchors is delegated too.** A project describing itself for the first time gives one for each role and concept no file carries, often dozens at once. Each says that nothing the artefact states rests on a file, which a reviewer can check against the artefact. It waives a measure, so the measure lists each apart, with its reason, and the person can see every one (COR-050 point 8).

**Why a component keeps its own.** A component's record that says a person decides answers on its artefacts may hold reasons this record cannot see, or may predate the delegate. Core does not presume a hand-over in a record it does not decide. Read either way, the record errs toward asking, which harms nothing. The component hands its answers on by refining its record where the record is authored.

**Why the person is told.** Told what the delegate decided, a person can replace an answer, or withdraw the delegate, at any time. Asked first, they would be back to judging each answer.

**Why the line falls where it does.** The delegate's work is reading: whether an artefact still says what is true of what it rests on. A reviewer can check that reading against the artefact and its anchors. Accepting a decision, authorising a merge and judging whether a change was meant decide what the project does. No reviewer's check stands in for them, so they stay a person's.

**Why one delegate.** One name gives one rule for who decides an answer, and one place for a person to look for what was decided.

### Alternatives considered

- **A person accepts every answer no change owes in one batch.** Not taken. It gathers the questions, but the person still judges each answer without its context.
- **A standing acceptance of every answer of a kind.** Rejected. Nobody would read each answer before it is written, which is the rubber stamp the anchors-and-friction record guards against. The delegate reads each, and a reviewer checks it.
- **Every answer no change owes checked by the reviewer alone, with no decision.** Rejected. The agent that drafted the answer would be the only one to choose whether to write it.
- **A delegate named in a session, or by an instruction to an agent.** Rejected. It leaves no record, and an agent could claim it.
- **Several delegates, one for each kind of artefact.** Not taken. It needs a rule for which decides an answer, and a person would follow several reports. A component that wants its answers kept from the delegate keeps them by its own record (point 1).
- **The delegate deciding its own drafts, checked by the reviewer alone.** Rejected. The choice whether to write the answer would be the drafter's alone.
- **Rewording without bounds.** Rejected. A delegate that could change an outcome, or write new content, would draft and decide at once.
- **The reviewer checking these answers only where a delegate is named.** Rejected. The configuration would be read at one commit and the decision made under another, so a withdrawal landing between them leaves answers checked by nobody.
- **The reviewer checking only the entries said to be the delegate's.** Rejected. A wrong account would leave an answer unchecked.
- **A field in the answer file naming who decided it.** Rejected. Anyone writing the file can write it, so no check could rely on it. The change and the delegate's report tell the person instead (point 5).
- **A delegate in a project that chose no reviewer.** Rejected. The answers would reach the default branch judged by agents alone.
- **Withdrawing by a person's word alone, everywhere at once.** Not taken. A word reaches one session, and an agent in another still finds its name on the default branch. The word stops its own session, and the change stops the rest.
- **The delegate also accepting records and authorising merges.** Rejected. Those decide what the project does, and no reviewer's check stands in for them.

## Implications

- **The anchors-and-friction record** is refined in place where it says a person decides these answers, and where its reviewer checks them: points 1, 3 and 16, point 14 for the key, and the Rationale on who decides. So is COR-062 point 7. Each points here. With no delegate named, a person decides each such answer, and a reviewer checks it too.
- **The backbone configuration's schema** gains the key. Validation fails a name that no agent of the project carries, and warns of one whose definition does not read this record.
- **The operational rules for agents, and the agents' guidance on who writes an answer,** say who decides an answer no change owes, and that a reviewer checks it.
- **An agent a person may name** says in its definition when it decides as the delegate and what it never decides (COR-013).
- **A reviewer that checks a change's answers** checks every answer no change owes that the change writes. A component that ships such a reviewer brings its definition in line.
- **A component that proposes answers** says how its proposals reach the delegate. One whose own proposals relied on a person's reading, as a defence against steered words, says what stands in for it before it hands them on.
- **A component through which merges are authorised** tells the person what the delegate decided, and shows a change to the delegate's name before the merge, as point 2 asks.
- **A component whose record keeps answers on its artefacts for a person** may hand them to the delegate by refining that record.
- **No migration.** The key is new, and absent by default.
