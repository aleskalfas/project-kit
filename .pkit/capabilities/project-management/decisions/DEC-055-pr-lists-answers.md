---
id: DEC-055
title: A pull request lists the answers its change wrote
status: proposed
date: 2026-10-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

An agent building a change may give the answers its own change owes — the revalidations and deferrals the change check asks of it — without asking anyone first. Those answers become a person's decision only when the person who authorises the merge is shown every one of them, word for word, from the change check's own list, and then authorises it; an authorisation given before the list was shown accepts none of them (COR-050 point 3). The change check gives that list in its machine-readable output (COR-050 point 12).

This capability is where a pull request's merge is authorised: the person reads the pull request's description, and the landing command stops, naming the head and the command that merges it, for them to authorise. If nothing puts the list there, the rule rests on an agent copying it by hand, and an authorisation given after the list was shown looks the same as one given before.

## Decision

**A pull request's description carries the change check's list of the answers its change wrote, written by this capability and never by an agent. The command that lands the pull request merges such a change on an authorisation given up front only when the list for the head it merges was already in the description.**

1. **The list.** This capability writes the answers a change wrote into the pull request's description, in a section of its own, `## Friction answers`, delimited so a command can find, compare and replace it whole. The list is the change check's own list of the answers the change wrote, derived at the pull request's head against its base, as the change check compares any change (COR-050 point 6). Each entry gives the artefact, the answer, its anchor where it has one, and the justification or reason word for word, with every flag the change check puts on it, and each deferral a revalidation kept; the list counts the files the check could not read. Where the change alters the friction settings that decide what the check asks — the places it reads or the files it leaves out (COR-050 points 1, 7 and 14) — the list also gives each such change as it was and as it is. The section is replaced whole whenever it is written and is never composed by an agent; a section under that heading that this capability did not write is removed. Where the change wrote no answers and alters no such setting, the landing command removes any list an earlier head left.
2. **Who writes it.** The command that opens the pull request writes it; every edit of the description through this capability carries it unchanged; the landing command derives it again before the merge.
3. **The authorisation.** The landing command prints every answer before it stops or asks. Where the change wrote answers or alters those settings, a run authorised up front merges only if it names the head it may merge and found the list for that head already in the description; one that had to write the list merges nothing and stops ready, whatever fails after the write. A run that asks at a terminal asks after the printed answers. The authorisation is the person's, to merge the pull request (Review → Done), not the review approval an agent may give (DEC-028). An entry flagged as not asked for, and a reason for having no anchors, needed the person's acceptance before it was written; authorising the merge does not give it. The landing command merges nothing and writes nothing when the list cannot be derived, when a file the change touches cannot be read for answers, when a word of the list reads as a closing reference or holds an HTML comment's delimiter, when the description cannot hold the list, or — where the change wrote answers or alters those settings — when the base's commits since the head left it changed a file that carries a listed answer or a kept deferral, or changed the settings the list shows, since that merge could land words the list does not show; a base that moved on otherwise stops nothing, as the change check itself only reports it (COR-050 point 12). These are firm stops with no override (DEC-014, DEC-046); the unheld path is point 5's.
4. **Never input.** No reader of the description treats the section as input — none that reads closing references or the `## Doc impact` section (DEC-013, DEC-015), or checks the template was filled (DEC-031). Nothing in the section closes an issue. The squash commit carries it as it carries the rest of the description.
5. **What this does not verify.** That a person read the list, or that their authorisation came after the list reached the description: a run authorised up front that finds the list already there — written when the pull request was opened, say, or by a run that then stopped ready, so the identical re-run of that run too — merges on an authorisation the command cannot date. Showing the list and asking for that head's authorisation is the agent's duty (COR-050 point 3). The landing command holds that a run authorised up front merged only a head whose list was already in the description, and did not write it itself. A merge through this capability's other merge commands, or outside this capability, is not held: after a fix round the description may carry the list of an earlier head, or none. A project that runs no checks on its pull requests lands through those other merge commands, since the landing command waits for checks, so its merges are not held either.

## Rationale

**Why the description.** It is what the person reads before authorising the merge, and the squash commit carries it (DEC-013), so the answers that landed stay beside the change in the default branch's history.

**Why the capability writes it from the check.** What the person is shown must be the check's list, never an account the agent composed (COR-050 point 3). A section derived from the check's document at the pull request's head, and replaced whole on every write, cannot drift from the artefacts and keeps no entry of an earlier head. A section under the heading that this capability did not write is such an account, so it is removed rather than shown beside the list.

**Why the landing command derives it again.** The head that merges is often not the head the pull request was opened at: a fix round rewrites answers and adds others. Deriving at the head the landing command pinned, and comparing with the description, makes "the list in the description" mean the list for the head that merges.

**Why a run authorised up front that had to write the list stops.** That authorisation was given before the list for this head was in the description, so the person cannot have been shown it, and under COR-050 point 3 such an authorisation accepts none of the answers. Stopping ready hands the list back: the person is shown it and asked again (COR-050 point 3) before the run that merges; merging would act on an authorisation that covers nothing. Naming the head ties the authorisation to the one list that head has. What the stop holds is the order of the write against the run that merges; the order of the showing against the authorisation is the agent's (point 5).

**Why the friction settings are listed.** The settings decide what the change check asks. A change that empties the places, or excludes an artefact's files, makes the check ask nothing of it, and the list then shows no answer where one was owed. Listing the settings the change alters, and holding them as answers are held, shows the person what the change decided about what is asked, not only what it answered. The mode decides whether the check fails, not what it asks or lists, so a change to it adds nothing to the list.

**Why only a base that changed the list's files stops the landing.** The change check reports an outdated base and fails nothing on it (COR-050 point 12). What the landing command adds is the list's words, and those can differ from what merges only where the base's commits since the head left it changed a file they are on: the merge then combines two versions of words the list shows one of. Any other outdated base merges the list's words as they are shown.

**Why a reason that reads as a closing reference is refused, not escaped.** The host reads closing references in the description and the squash commit with its own parser, which this capability cannot make skip a section. Such a reason would close an issue at merge, so it is never written: the artefact's words are reworded. A word holding an HTML comment's delimiter is refused for a kindred reason: it could open or close a comment around the section's markers, hiding the list from the page or from the commands that find it.

**Why nothing reads the section as input.** Each reader of the description answers a question the description's author answers — which issues the change closes, which documents it accounts for, whether the template was filled. The section is written by a command from the artefacts' words; letting it answer those questions would let words written for an artefact meet obligations they were never written for.

### Alternatives considered

- **The list inside `## Doc impact`.** Rejected. That section is read for the mapping's override and for closing references, so the artefacts' words would become input there.
- **A pull-request comment.** Rejected. The description is the one place the person reads before authorising and the one the squash commit carries; a comment is a second place, and a later comment does not replace an earlier one.
- **A stamp trusted without deriving.** Rejected. A marker naming the head a list is for, trusted as written, accepts a list edited by hand or left from an earlier head; deriving again and comparing does not.
- **Spilling an over-long list elsewhere.** Rejected. The person would authorise the merge from a description that does not hold what they accept. A list the description cannot hold stops the landing, and the description's own text is shortened, the change split or the anchor narrowed.
- **Stopping on any outdated base where the change wrote answers.** Rejected. The stop falls between the landing command's ready stop and the person's authorisation, so on a busy default branch every such change would wait for it to stand still, each wait asking for a new head, new checks and a new review — while only a base that changed a file the list's words are on can land words the list does not show.

## Implications

- The command that opens the pull request derives the list at the pushed head and never refuses to open over it: a list it cannot derive, or cannot write, is left out with a warning, and the landing command writes it or refuses. The edit command derives nothing.
- The landing command gains a step between the review and the merge that derives the list, prints it and writes it into the description. The capability README documents the section and the step.
- Every reader of the description strips the section before it reads.
- The opt-in that fills an unwritten `## Doc impact` from the friction answers writes one line pointing at the section, naming no path and no reason, so it can meet no mapping obligation.
- [project-management:DEC-053-doc-check-slot] point 2 names this section as where the answers are listed. A line of it meets no obligation there.
