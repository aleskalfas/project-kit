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
          at: 2026-10-17T22:14:47Z
          outcome: unchanged
          unchanged-because: DEC-001 changed in its Context, points 4 and 11, Rationale and Implications, on how the analysis anchors the decisions and views of the solution. Point 1, the kinds' declared structures this format rule carries, is unchanged, so the rule holds as written.
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
          at: 2026-10-17T22:14:48Z
          outcome: unchanged
          unchanged-because: "Point 4 changed only in what a use case anchors outside the analysis: the decisions that answer it and the views that realise it. Its anchors on its actor and its other actors, which this rule rests on, read as before, and points 1 and 3 are unchanged."
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
            - "COR-050#1"
        revalidated:
          at: 2026-10-17T20:04:12Z
          outcome: unchanged
          unchanged-because: COR-050 point 1 was reached only through the Decision's text outside its points, which says a record anchor stands on the record's content and what a record's content is. RS-SAN-005 asks that an artefact's anchors name what its statements rest on, and that an anchor on a part names only that part, which still holds.
# What this capability's checks enforce of each rule (COR-051 point 2). Of
# the format rule, it is the structure each artefact kind ships: its parts,
# the glossary's head and its forms (DEC-001 point 1). Of the append-only
# rule, it is a comparison of each use case with the same use case where the
# change left its base: the default branch, or the base the comparison names
# (DEC-001 point 3; COR-054 point 3). `pkit validate` never runs that check
# (COR-055 point 2). A check enforces its part only where its rule binds.
# Whoever judges the rest of a rule leaves that part to the check. Where a
# project's rule tightens a structure, the project's set declares what the
# check enforces of that rule. RS-SAN-003, RS-SAN-004 and RS-SAN-005 declare
# no check: a reviewer judges each.
checks:
  RS-SAN-001:
    - check: "software-analysis:validate"
      part: >-
        Every part its kind ships is present, in the order the structure gives,
        save a part a withdrawn artefact lacks. A missing title heading of an
        actor, a use case or a journey is left to the heading check, which holds
        it whatever the rule's status. No shipped part a writer fills is empty,
        and a part reads `None.` only where the structure allows it.

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

The rules for a project's analysis artefacts, whatever the project (software-analysis DEC-001 points 1 to 4, and 9). Like every method rule set, this set takes no scope (COR-051 point 2). Its rules bind only through a set of the project's own that inherits it (COR-051 point 7). A rule binds nothing until it is accepted (COR-051 point 4). A revalidation record is a held document, which no rule binds on, so the capability checks its structure itself (DEC-001 point 1). How rules are named, grounded and inherited is the rule-set record's (COR-051), so it is not repeated here.

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

## RS-SAN-005 — An artefact's anchors name what its statements rest on

An analysis artefact's anchors name what its statements rest on.

- **How:**
  - **Its statements.** They are its body and the front-matter fields a writer fills, such as an actor's `needs` or a term's `definition`.
  - **What a statement rests on.** What its kind anchors to, where a change to it can make the statement false. This list is whole:
    - An actor or a term rests on the code and the decisions that embody it.
    - A use case rests on its `actor` and its `other-actors`, the code it exercises and the decisions it relies on.
    - A journey rests on its actor, the use cases of its `steps` and its `relies-on`, and the code and decisions at its seams.
  - **Nothing else.** A statement about any other artefact rests on nothing this rule asks an anchor for. So a term that another term's distinctions name needs no anchor. Nor does this rule ask for an anchor that would close a cycle.
  - **Only what exists.** Code not yet written, or a decision not yet recorded, is nothing a statement rests on.
  - **Where to find it.** The code lies in the repository, within the surface the project declares for its analysis where it declares one. The decisions are the records a statement cites or applies.
  - **Which anchor names it.** A path anchor names code, a record anchor a decision, and an artefact anchor another artefact. An anchor on one part of a record or a document names only what that part stands on.
  - **Where to read the anchors.** An artefact's anchors are in its friction block. A glossary term's are in its entry.
  - **What the check holds.** The capability's check requires a use case's anchors on its `actor` and on each of its `other-actors`. It requires a journey's on its actor, and on exactly the use cases of its `steps` and its `relies-on`. It does so whatever any rule's status, and this rule does not cover it.
  - **What this rule judges.** The rest: the code and the decisions a statement rests on.
  - **A break.** A statement that rests on code or a decision that no anchor of the artefact names breaks this rule, until the artefact anchors it. So a use case's minimal guarantee that cites a decision breaks it while no record anchor names the decision.
  - **No anchors.** The core reports an artefact with no anchors, and no check fails on it. This rule still judges what its statements rest on.
  - **A reason for no anchors.** An actor or a term that gives a reason for having none is not judged under this rule. The reason is a person's answer, and only a person decides it.
  - **History.** This rule judges an artefact in force. A withdrawn artefact is history.
