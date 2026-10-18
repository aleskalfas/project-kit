---
rule-set: SAN
version: 1.0.0
rules:
  RS-SAN-001:
    status: accepted
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["software-analysis:DEC-001"]}
        revalidated:
          at: 2026-10-18T11:57:54Z
          outcome: unchanged
          unchanged-because: DEC-001 changed only by pointers to software-analysis DEC-002 on points 2, 4 and 11, and point 11 names constraints and quality requirements as examples of further kinds. Point 1, the kinds' declared structures this format rule carries, is unchanged, so the rule holds as written.
  RS-SAN-002:
    status: accepted
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["software-analysis:DEC-001#3"]}
  RS-SAN-003:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#1", "software-analysis:DEC-001#3", "software-analysis:DEC-001#4"]
        revalidated:
          at: 2026-10-18T11:58:01Z
          outcome: unchanged
          unchanged-because: Point 4 changed only by a pointer to software-analysis DEC-002 on the lead of what each kind anchors. What a use case anchors on its actor and its other actors, which this rule rests on, reads as before, and points 1 and 3 are unchanged.
  RS-SAN-004:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["software-analysis:DEC-001#1"]}
  RS-SAN-005:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors:
          record:
            - "software-analysis:DEC-001#2"
            - "software-analysis:DEC-001#4"
            - "software-analysis:DEC-001#9"
            - "software-analysis:DEC-001#11"
            - "software-analysis:DEC-002#5"
            - "software-analysis:DEC-002#6"
            - "COR-050#1"
            - "COR-050#2"
            - "COR-050#5"
        revalidated:
          at: 2026-10-18T15:02:47Z
          outcome: updated
  RS-SAN-006:
    status: proposed
    origin: {decision: "software-analysis:DEC-002"}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-002#4", "software-analysis:DEC-002#6", "software-analysis:DEC-002#8"]
  RS-SAN-007:
    status: proposed
    origin: {date: 2026-10-17, by: "Aleš Kalfas"}
    pkit:
      friction:
        anchors:
          record:
            - "software-analysis:DEC-001#1"
            - "software-analysis:DEC-001#4"
            - "software-analysis:DEC-001#11"
            - "software-analysis:DEC-002#4"
            - "software-analysis:DEC-002#6"
            - "software-analysis:DEC-002#8"
# What this capability's checks enforce of each rule (COR-051 point 2). Of
# the format rule, it is the structure each artefact kind ships: its parts,
# the glossary's head and its forms (DEC-001 point 1). Of the append-only
# rule, it is a comparison of each use case with the same use case where the
# change left its base: the default branch, or the base the comparison names
# (DEC-001 point 3; COR-054 point 3). `pkit validate` never runs that check
# (COR-055 point 2). A check enforces its part only where its rule binds.
# Whoever judges the rest of a rule leaves that part to the check. Where a
# project's rule tightens a structure, the project's set declares what the
# check enforces of that rule. RS-SAN-003 to RS-SAN-007 declare no check: a
# reviewer judges each.
checks:
  RS-SAN-001:
    - check: "software-analysis:validate"
      part: >-
        Every part its kind ships is present, in the order the structure gives,
        save a part a withdrawn artefact lacks. A missing title heading of an
        actor, a use case or a journey is left to the heading check, which holds
        it whatever the rule's status. No shipped part a writer fills is empty,
        and a part reads `None.` only where the structure allows it. A
        front-matter field the structure says may not read `None.` never does.

        The glossary carries its head wherever the rule binds on one of its
        terms. A shipped part or front-matter field that the structure gives a
        form holds that form, save on a withdrawn artefact. The forms are
        `sentence`, `numbered-steps`, `variants`, `steps-match-front-matter` and
        `definition`, each as the schema of the kinds' declared structure
        describes it.
  RS-SAN-002:
    - check: "software-analysis:check-numbers"
      part: >-
        Each step and each variant that a use case held where the change left
        its base, of a use case the working tree still holds, is neither
        renumbered nor removed. It is renumbered where its text stands in the
        working tree under another number or letter, one the base did not give
        that same text, and not under its own. It is removed where its number
        or letter is gone and it is not renumbered. A number or a letter that
        holds other text passes as an edit, and a step or a variant added
        passes whatever number or letter it takes. Whoever judges the rest of
        the rule judges these: a step replaced by another under its number, one
        renumbered and reworded at once whose old number holds another step,
        and the number or letter a new one takes.
---

# SAN — the software-analysis method

The rules for a project's analysis artefacts, whatever the project. They rest on software-analysis DEC-001 points 1 to 4, 9 and 11, and DEC-002 points 4 to 6 and 8. Like every method rule set, this set takes no scope (COR-051 point 2). Its rules bind only through a set of the project's own that inherits it (COR-051 point 7). A rule binds nothing until it is accepted (COR-051 point 4). A revalidation record is a held document, which no rule binds on, so the capability checks its structure itself (DEC-001 point 1). How rules are named, grounded and inherited is the rule-set record's (COR-051), so it is not repeated here.

A rule's statement and its *How* bind. Inside a *How*, a "such as" phrase and a sentence that starts with "So" only illustrate.

## RS-SAN-001 — An analysis artefact carries its kind's structure

An analysis artefact carries its kind's declared structure.

- **How:**
  - **Parts.** Every part its kind ships is present, in the order the structure gives. A part with nothing to say reads `None.`, where its structure allows it. A part a project adds binds only where the project rule that asks for it binds too.
  - **The glossary's head.** The term kind's structure also declares the head of the glossary, the file that holds the terms. Where this rule binds on a term, the glossary that holds it carries its head.
  - **Forms.** A part or a front-matter field that the structure gives a form holds that form.
  - **Hints.** A hint binds nothing, so the voice a hint asks for is no part of this rule.
  - **History.** A withdrawn artefact is held to no part or form that came after its withdrawal.
  - **The `sentence` form.** Each text of this form, such as an actor's need, holds one sentence: no sentence ends before the text's last word.
    - **One text.** A body part of this form, such as a use case's *Goal*, is one text, and holds no Markdown list, not even inside a block quote. In a front-matter field that holds a list, such as an actor's `needs`, each item is one text.
    - **Where a sentence ends.** At `.`, `?` or `!` followed by a space and a capital letter, and at the end of the text. No other mark ends a sentence, such as `。`, `！` or the Greek question mark.
      - Any white space counts as a space, such as a line end, several spaces or a no-break space. A character a reader cannot see, such as a zero-width space, counts as nothing.
      - A mark inside a code span or a fenced block ends no sentence.
      - So a mark followed by a lowercase letter, as in "e.g. for" or "3. října", ends no sentence. One followed by a capital does, as in "Dr. Smith" or "z. B. Rechnungen", so a writer rewords such a text.
    - **A script without capital letters,** such as Chinese or Arabic: a mark followed by one of its letters ends no sentence. So a text in such a script is never split.

## RS-SAN-002 — A use case's steps and variants keep their numbers and letters

A use case's steps and variants keep their numbers and letters.

- **How:**
  - **Steps.** A change renumbers no step its use case held before the change, and removes none.
  - **Variants.** A change gives no variant its use case held before the change another step number or letter, and removes none.
  - **New ones.** Steps and variants are append-only. A new step takes a number higher than every number of its use case, and a new variant a letter after every letter of its step.
  - So a step added between two others takes such a number too, and a step that no longer happens stays under its number.

## RS-SAN-003 — A use case's actor is the one whose goal it is

A use case's actor is the one whose goal it is, and each other actor that takes part in it is one of its `other-actors`.

- **How:**
  - **What the check holds.** The stamp and the capability's check refuse a use case whose `actor` or `other-actors` names an actor the analysis does not hold. They also refuse a use case in force that names a withdrawn actor there. They do so whatever any rule's status, and this rule does not cover it.
  - **What an actor is.** A named role that uses the system. The analysis holds each actor as an artefact of its actor kind. The system that fulfils the goal is no actor.
  - **Whose goal.** A use case is one actor's goal and how the system fulfils it. Its `actor` is the actor that wants what the use case's part `goal` states.
  - **An actor that acts for another.** Where the goal is another actor's, an actor that acts for that one takes its part in the steps. It is never the use case's `actor`.
  - So an agent working for a person takes its part in the steps of that person's use cases.
  - **Who takes part.** Each actor that takes part in the use case is its `actor` or one of its `other-actors`. That holds wherever the body names the actor, such as in the trigger, a step or a variant.
  - So a use case breaks this rule while an actor that takes part in it is one the analysis does not hold yet.
  - **History.** This rule judges a use case in force. A withdrawn use case is history.

## RS-SAN-004 — A use case's goal is one of its actor's needs

A use case's goal is one of its actor's needs.

- **How:**
  - **Where to read them.** The goal is the use case's part whose id is `goal`, whatever label a project gives it. The needs are the `needs` in the front matter of the actor that the use case's `actor` names.
  - **One need, whole.** The goal states the same want as one of those needs. A goal breaks this rule where it states a want none of them states, two of them, or a narrower want than one of them.
  - So the goal "Export my report as a CSV file" breaks it where the actor's need is "Export my report as a file". A writer adds the narrower need to the actor, or states the need whole.
  - **Its words.** The goal's words and voice may differ from the need's. So the goal "Get my report exported to a file" states the need "Export my report as a file".
  - **History.** This rule judges a use case in force. A withdrawn use case is history.

## RS-SAN-005 — An artefact's anchors name what it rests on, and what answers or realises a use case or a requirement

An analysis artefact's anchors name what its statements rest on. A use case's or a requirement's anchors also name the decisions that answer it and the architecture views that realise it.

- **How:**
  - **Its statements.** They are its body and the front-matter fields a writer fills, such as an actor's `needs` or a term's `definition`.
  - **What its anchors name.** What its kind anchors to, where a change to it can make one of its statements false. This list is whole:
    - An actor or a term rests on the code and the decisions that embody it.
    - A use case rests on its `actor` and its `other-actors`, the code it exercises and the decisions it cites or applies. Its anchors also name each decision that answers it and each architecture view that realises it. Each is asked for even where none of the use case's statements names it, since a change to it can leave the use case untrue of the system.
    - A journey rests on its actor, the use cases of its `steps` and its `relies-on`, and the code and decisions at its seams.
    - A requirement rests on each actor in its `actors`, each requirement in its `refines`, and the decisions it cites or applies. It also rests on the narrow code that holds it and the files that verify it. Its anchors also name each decision that answers it and each architecture view that realises it. Each is asked for even where none of its statements names it.
  - **Nothing else.** A statement about an artefact this list does not name rests on nothing this rule asks an anchor for. So a term that another term's distinctions name needs no anchor.
  - **No cycle excuses it.** An anchor this list asks for on a decision or a view is asked for even where anchors that run back from that decision or view would close a cycle.
  - **What it never asks for.** This rule asks no anchor for:
    - code not yet written
    - a decision that is not accepted: one not yet recorded, a proposed one or a superseded one
    - a view the project does not keep, or keeps outside its repository
  - **Where to find it.**
    - **Code** lies in the repository, within the surface the project declares for its analysis where it declares one.
    - **The decisions an artefact rests on** are the records its statements cite or apply, such as the decision to use git, for a use case that runs on git. An actor's or a term's are also the records that embody it.
    - **The decisions that answer a use case or a requirement** are the records made to meet what it asks, such as one that names it by its id. So the decision to write a report as CSV answers a use case that must export the report as a file. Each may be a core record, a capability's record or the project's own.
    - **The views that realise a use case or a requirement** are the architecture views the project keeps to show how the system carries it out. Such a view may name it by its id.
    - **The files that verify a requirement** are the files of the tests and checks named in its part whose id is `verified-by`.
    - **The code that holds a requirement** is the code that keeps it, never all the code its `applies-to` reaches.
  - **Which anchor names it.** A path anchor names code, a record anchor a decision, and an artefact anchor another artefact. A view a place holds takes an artefact anchor, and any other view takes a path anchor on its file. An anchor on one part of a record or a document names only what that part stands on.
  - **Where to read the anchors.** An artefact's anchors are in its friction block. A glossary term's are in its entry.
  - **What the check holds.** The capability's check requires a use case's anchors on its `actor` and on each of its `other-actors`. It requires a journey's on its actor, and on exactly the use cases of its `steps` and its `relies-on`. It does so whatever any rule's status, and this rule does not cover it.
  - **What this rule judges.** The rest:
    - the code and the decisions a statement rests on
    - the decisions that answer a use case or a requirement, and the views that realise one
    - a requirement's anchors on its `actors` and its `refines`
  - **A break.** A statement that rests on code or a decision that no anchor of the artefact names breaks this rule, until the artefact anchors it. So a use case's minimal guarantee that cites a decision breaks it while no record anchor names the decision. A use case or a requirement also breaks it while no anchor names a decision that answers it, or a view that realises it. A requirement breaks it too while no anchor names an actor in its `actors`, or a requirement in its `refines`.
  - **No anchors.** The core reports an artefact with no anchors, and no check fails on it. This rule still judges what its statements rest on.
  - **A reason for no anchors.** An actor or a term that gives a reason for having none is not judged under this rule. Nor is a requirement that gives one, with no `actors` and no `refines`. The reason is a person's answer, and only a person decides it.
  - **History.** This rule judges an artefact in force. A withdrawn artefact is history.

## RS-SAN-006 — A requirement never contradicts an accepted record it rests on

A requirement never contradicts an accepted decision record it rests on.

- **How:**
  - **What it compares.** A requirement's `statement`, its `measure` and its `applies-to`, with each accepted decision record it rests on. Its body explains the obligation or says what verifies it, so this rule compares none of it.
  - **The records.** They are the records its record anchors name, each whole or the point its anchor names. The requirement rests on what they decide, save a decision made to meet what it asks. That decision answers it, and this rule compares nothing with it.
  - **Only what is in force.** A proposed record decides nothing yet, and a superseded one no longer does. Nor does a point another record overturns. This rule compares no requirement with any of them.
  - **A contradiction.** Where the requirement holds, as its `applies-to` says, the requirement and the record cannot both be kept. Its `measure` also contradicts the record where it accepts what the record rules out, or rules out what the record requires.
  - So a measure looser than a limit the record sets contradicts the record. Where the record decides nothing of what the requirement asks, the requirement adds to it.
  - **The record wins.** Where the two contradict, the requirement breaks this rule, until the record is changed. So a writer changes the requirement, or has the record changed first. A record a component ships is changed by its owner.
  - **Two requirements.** A conflict between two requirements is no break of this rule. It is a choice, so a decision record holds it.
  - **History.** This rule judges a requirement in force. A withdrawn requirement is history.

## RS-SAN-007 — Each goal, minimal guarantee and requirement names its source

Each goal, minimal guarantee and requirement names its source.

- **How:**
  - **What it judges.**
    - The goal of a use case or a journey: its part whose id is `goal`, whatever label a project gives it.
    - Each minimal guarantee of a use case or a journey, as its part whose id is `minimal-guarantees` states it.
    - Each requirement: what its `statement` asks, and what its `measure` sets unless it reads `None.`. Its sources together cover both.
  - **A source.** Any one of these names it:
    - **A record.** An accepted decision record the artefact anchors, which decides the item or was made to meet it. A point another record overturns decides nothing.
    - **A requirement's reason.** Its part whose id is `rationale`, or `imposed-by` on a constraint, where the part does not read `None.`.
    - **Existing behaviour.** Code the artefact anchors, which already does what the item says. A reader judges that the code does it, never how well, so this form sources no value a `measure` sets.
    - **A quoted decision.** The words of the person who decided, quoted in the artefact's body, with their name and the date. The quote names the item it sources, in its text or a label beside it, or it stands beside the item.
  - **What a source bears out.** A source names only what it bears out. So a reason that asks for speed sources no value of two seconds.
    - A record bears out what it decides or was made to meet.
    - A quote bears out what it decides, and code what it does.
    - A reason bears out what it says the system needs.
  - **Nothing else.** Anything else is no source, however plausible the item reads. So the need a goal states is no source of the goal, nor is a proposed record.
  - **Where to read the anchors.** An artefact's anchors are in its friction block.
  - **A break.** An item that no source names breaks this rule, until the artefact names one.
  - **History.** This rule judges an artefact in force. A withdrawn artefact is history.
