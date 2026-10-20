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
          at: 2026-10-19T19:00:00Z
          outcome: unchanged
          unchanged-because: DEC-001 gains the domain-model view kind, whose structure a later build declares. No kind this rule checks gains a part or a form, so this format rule holds as written.
  RS-SAN-002:
    status: accepted
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["software-analysis:DEC-001#3"]}
        revalidated:
          at: 2026-10-19T19:00:00Z
          outcome: unchanged
          unchanged-because: DEC-001 point 3 gives a domain-model view its id, VIEW- and the slug after its number. A use case's steps and variants stay append-only, so this rule holds as written.
  RS-SAN-003:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-001#1", "software-analysis:DEC-001#2", "software-analysis:DEC-001#3", "software-analysis:DEC-001#4"]
        revalidated:
          at: 2026-10-19T19:00:00Z
          outcome: unchanged
          unchanged-because: DEC-001 points 1 to 4 gain the domain-model view, its folder, its id and its anchors. Whose goal a use case is stays as decided, so this rule holds as written.
  RS-SAN-004:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["software-analysis:DEC-001#1", "software-analysis:DEC-001#2"]}
        revalidated:
          at: 2026-10-19T19:00:00Z
          outcome: unchanged
          unchanged-because: DEC-001 points 1 and 2 gain the domain-model view and its folder. A goal and its actor's needs stay as decided, so this rule holds as written.
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
            - "software-analysis:DEC-002#7"
            - "software-analysis:DEC-004#5"
            - "COR-050#1"
            - "COR-050#2"
            - "COR-050#5"
        revalidated:
          at: 2026-10-19T18:36:20Z
          outcome: updated
  RS-SAN-006:
    status: proposed
    origin: {decision: "software-analysis:DEC-002"}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-002#4", "software-analysis:DEC-002#6", "software-analysis:DEC-002#8"]
        revalidated:
          at: 2026-10-19T14:38:33Z
          outcome: unchanged
          unchanged-because: DEC-002 point 6 lets a requirement's actors name another analysis's actor, anchoring the records behind it, and keeps refines within its own analysis. The statement, measure and applies-to this rule compares with the records a requirement rests on read as before, so the rule holds as written.
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
        revalidated:
          at: 2026-10-19T19:00:00Z
          outcome: unchanged
          unchanged-because: DEC-001 points 1 and 4 gain the domain-model view and what it anchors. What names the source of a goal, a guarantee or a requirement is unchanged.
  RS-SAN-008:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors:
          record:
            - "software-analysis:DEC-001#1"
            - "software-analysis:DEC-001#2"
            - "software-analysis:DEC-001#12"
            - "software-analysis:DEC-002#4"
            - "software-analysis:DEC-003#10"
            - "software-analysis:DEC-004#3"
        revalidated:
          at: 2026-10-19T18:36:20Z
          outcome: updated
  RS-SAN-009:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors:
          record:
            - "software-analysis:DEC-001#1"
            - "software-analysis:DEC-001#2"
            - "software-analysis:DEC-001#12"
        revalidated:
          at: 2026-10-19T19:00:00Z
          outcome: unchanged
          unchanged-because: DEC-001 points 1, 2 and 12 gain the domain-model view, its folder and its place in the build order's first step. Preconditions, their producers and after stay as decided.
  RS-SAN-010:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors:
          record:
            - "software-analysis:DEC-001#2"
            - "software-analysis:DEC-001#4"
            - "COR-030"
        revalidated:
          at: 2026-10-19T19:00:00Z
          outcome: unchanged
          unchanged-because: DEC-001 points 2 and 4 gain the domain model's folder and what a view anchors, terms of its own analysis alone. Which analyses one may name is unchanged.
  RS-SAN-011:
    status: proposed
    origin: {decision: "software-analysis:DEC-004"}
    pkit:
      friction:
        anchors:
          record: ["software-analysis:DEC-004#4", "software-analysis:DEC-004#6"]
# What this capability's checks enforce of each rule (COR-051 point 2). Of
# the format rule, it is the structure each artefact kind ships: its parts,
# the glossary's head and its forms (DEC-001 point 1). Of the append-only
# rule, it is a comparison of each use case with the same use case where the
# change left its base: the default branch, or the base the comparison names
# (DEC-001 point 3; COR-054 point 3). `pkit validate` never runs that check
# (COR-055 point 2). Of the rule of logical consequence, it is what a script
# reads of a use case's `after` (DEC-001 point 1). A check enforces its part
# only where its rule binds. Whoever judges the rest of a rule leaves that part
# to the check. Where a project's rule tightens a structure, the project's set
# declares what the check enforces of that rule. RS-SAN-003 to RS-SAN-008,
# RS-SAN-010 and RS-SAN-011 declare no check: a reviewer judges each.
checks:
  RS-SAN-001:
    - check: "software-analysis:validate"
      part: >-
        Every part its kind ships is present, in the order the structure gives,
        save a part a withdrawn artefact lacks. A missing title heading of an
        actor, a use case, a journey, a quality requirement, a functional
        requirement, a constraint or a domain-model view is left to the heading
        check, which holds it whatever the rule's status. No shipped part a writer fills is empty,
        and a part reads `None.` only where the structure allows it. A
        front-matter field the structure says may not read `None.` never does.

        The glossary carries its head wherever the rule binds on one of its
        terms. A shipped part or front-matter field that the structure gives a
        form holds that form, save on a withdrawn artefact. The forms are
        `sentence`, `numbered-steps`, `variants`, `steps-match-front-matter`,
        `headings-match-front-matter` and `definition`, each as the schema of
        the kinds' declared structure describes it.
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
  RS-SAN-009:
    - check: "software-analysis:validate"
      part: >-
        Of a use case in force that writes `after`: each producer is a use case
        in force of its own analysis, the use case itself among them, or
        `environment`. `after` holds one entry for each precondition the part
        whose id is `preconditions` writes, in their order, and each entry names
        the producers its precondition's line opens with. A part that reads
        `None.` writes none. Where the use case's area carries a number, each
        entry names a producer in no later area: the environment, or a use case
        whose area carries no higher number. Whoever judges the rest of the rule
        judges a producer in an area without a number or in no area, and each
        use case that writes no `after`.
---

# SAN — the software-analysis method

The rules for a project's analysis artefacts, whatever the project. They rest on software-analysis DEC-001 points 1 to 4, 9, 11 and 12, and DEC-002 points 4 to 8. They also rest on DEC-003 point 10 and DEC-004 points 3 to 6. Like every method rule set, this set takes no scope (COR-051 point 2). Its rules bind only through a set of the project's own that inherits it (COR-051 point 7). A rule binds nothing until it is accepted (COR-051 point 4). A revalidation record is a held document, which no rule binds on, so the capability checks its structure itself (DEC-001 point 1). How rules are named, grounded and inherited is the rule-set record's (COR-051), so it is not repeated here.

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
  - **An actor of another analysis.** A use case may name an actor of an analysis its own builds on, with that analysis's name, such as `core:ACT-developer`. That actor is then one the head of its analysis's glossary lists.
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
  - **An actor of another analysis.** Where the `actor` names one, such as `core:ACT-developer`, its needs are those the use case's analysis states beside it, in its glossary's head. The needs its own analysis gives it are not read.
  - **One need, whole.** The goal states the same want as one of those needs. A goal breaks this rule where it states a want none of them states, two of them, or a narrower want than one of them.
  - So the goal "Export my report as a CSV file" breaks it where the actor's need is "Export my report as a file". A writer adds the narrower need to the actor, or states the need whole.
  - **Its words.** The goal's words and voice may differ from the need's. So the goal "Get my report exported to a file" states the need "Export my report as a file".
  - **History.** This rule judges a use case in force. A withdrawn use case is history.

## RS-SAN-005 — An artefact's anchors name what it rests on, and what answers or realises a use case or a requirement

An analysis artefact's anchors name what its statements rest on. A use case's or a requirement's anchors also name the decisions that answer it and the architecture views that realise it.

- **How:**
  - **Its statements.** They are its body and the front-matter fields a writer fills, such as an actor's `needs` or a term's `definition`.
  - **Views.** A *view* named alone in this rule is an architecture view. A domain-model view is always named in full.
  - **What its anchors name.** What its kind anchors to, where a change to it can make one of its statements false. This list is whole:
    - An actor or a term rests on the code and the decisions that embody it. A term whose `definition` names a term the glossary's head lists also rests on that term.
    - A domain-model view rests on each term it explains, and the decisions its statements cite or apply. Each fact it states as always true rests on the record that decides it. It rests on no code, since it describes the domain, never the software.
    - A use case rests on its `actor` and its `other-actors`, each requirement in its `requirements`, the code it exercises and the decisions it cites or applies. Its anchors also name each decision that answers it and each architecture view that realises it. Each is asked for even where none of the use case's statements names it, since a change to it can leave the use case untrue of the system.
    - A journey rests on its actor, the use cases of its `steps` and its `relies-on`, each requirement in its `requirements`, and the code and decisions at its seams.
    - A requirement rests on each actor in its `actors`, each requirement in its `refines`, and the decisions it cites or applies. It also rests on the narrow code that holds it and the files that verify it. Its anchors also name each decision that answers it and each architecture view that realises it. Each is asked for even where none of its statements names it.
  - **Nothing else.** A statement about an artefact this list does not name rests on nothing this rule asks an anchor for. So a term that another term's distinctions name needs no anchor.
  - **Across analyses.** Where this list names an actor or a term of another analysis, the anchors name records, never that artefact itself. They name each record that artefact's own record anchors name, where the statements rest on what that record decides. Where that artefact anchors no record, nothing is asked in its place.
  - So a use case whose `actor` is `core:ACT-developer` anchors the records behind that actor, and never the actor.
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
  - **What the check holds.** The capability's check requires a use case's anchors on its `actor` and on each of its `other-actors`. It requires a journey's on its actor, and on exactly the use cases of its `steps` and its `relies-on`. It requires the anchors of a use case and of a journey on exactly the requirements each lists in `requirements`. Once the domain-model view is built, it requires a view's anchors on exactly the terms its `explains` lists, and refuses a path anchor on one. It does so whatever any rule's status, and this rule does not cover it.
  - **What this rule judges.** The rest:
    - the code and the decisions a statement rests on
    - the decisions that answer a use case or a requirement, and the views that realise one
    - a requirement's anchors on its `actors` and its `refines`
    - the records behind an actor or a term of another analysis
  - **A break.** A statement that rests on code or a decision that no anchor of the artefact names breaks this rule, until the artefact anchors it. An anchor on another analysis's artefact breaks it too, until the artefact anchors the records behind that one instead. So a use case's minimal guarantee that cites a decision breaks it while no record anchor names the decision. A use case or a requirement also breaks it while no anchor names a decision that answers it, or a view that realises it. A requirement breaks it too while no anchor names an actor in its `actors`, or a requirement in its `refines`.
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

## RS-SAN-008 — An artefact uses a domain concept only as the glossary defines it

An analysis artefact uses a domain concept only where a term of the glossary defines it, and names the concept by that term's name. No two terms define one concept.

- **How:**
  - **Its statements.** They are its body and the front-matter fields a writer fills, such as an actor's `needs` or a requirement's `statement`. An artefact's title is one statement, wherever its heading repeats it, and a file's name is none. A term's statement is its `definition` alone. Its example only illustrates the definition, and its distinctions name words to tell them apart.
  - **A domain concept.** A word or a phrase that a statement uses in a meaning of the project's domain, one that a general dictionary does not give it. So a word used as a dictionary has it is no domain concept, unless a term holds it as its name.
  - **Defined.** A term in force defines one concept, the one its `name` names. A concept that a term's definition or its other parts only mention, or tell apart, is not defined by that term.
  - **Its name.** A statement names a defined concept by its term's `name`, also in these forms:
    - a form made from the name in the term's sense, such as a plural, a possessive or a verb
    - a phrase whose other words keep their dictionary meaning, such as "the last release". A phrase that names a thing of its own, such as "release tag", is a concept of its own. It names a thing of its own where the system keeps, shows or acts on what it names as one thing.
    - a pronoun or a shortened name that points back to the term, where the same part already named it
  - **A term's name in another sense.** Once a term holds a name, the name means the term's concept wherever a statement uses it, a sense a dictionary gives it included. The exception is a sense the term tells apart from its own.
  - **A definition and its own name.** The `definition` form refuses a word of the term's own name, and whether a definition holds one is that form's to check. Where such a word is the name of a term the definition relates to, such as its broader kind, the definition names that concept in other words. That is no break.
  - **What uses no concept.**
    - an actor, named by its name, a shortened name or the word its id is made of, and an artefact's id
    - a proper name, such as a person's, an organisation's, a product's or a standard's. A common noun beside it, such as "bank" in "the Northwind bank", is a word like any other.
    - the names of the analysis's kinds and of their parts, such as "use case", "precondition" or "minimal guarantee"
    - words quoted from a person or a document, such as a decision quoted as a source, or the wording of a law
    - text in a code span or a fenced block, which quotes code. A Mermaid fence quotes no code. The labels its diagram shows, its `accTitle` and its `accDescr` are statements. An id the diagram never shows uses no concept.
    - a part's label, and text the stamp writes from another artefact, such as a journey's step line, which copies a use case's title. A break in that text is the other artefact's.
  - **The glossary's head.** Wherever this rule binds on a term, each need that the head of its glossary states beside a listed actor is a statement too.
  - **A domain-model view.** Each of its sections explains the concept that the term its heading names defines, in that term's sense.
    - **A break.** A section breaks this rule where what it states widens or narrows what the term's `definition` fits. It then holds of something the definition does not fit, or fails of something the definition fits.
    - So a section may say more of the concept than its definition does, such as its attributes and its states. All of it holds of exactly what the definition fits.
  - **Where to read the glossary.** It is the glossary of the analysis that holds the artefact. It takes in the terms its head lists from the analyses it builds on, each as its own analysis's glossary defines it.
  - **A break.** An artefact breaks this rule, until it is mended, where a statement:
    - uses a domain concept that no term in force defines
    - names a defined concept by another word than its term's name, such as a name the term replaces, or a word of its own
    - uses a term's name in a meaning other than the term's own, unless the term tells that meaning apart from its own
  - **Two terms.** A term breaks this rule where another term in force defines the concept it defines. Two terms define one concept where whatever one definition fits, the other fits too, and neither term tells the other apart. Withdrawing one of them, or telling the two apart, mends it.
  - **A listed term's name.** A term breaks this rule where it takes the name of a term its glossary's head lists from another analysis.
  - **A renamed term.** A term breaks this rule while an artefact in force names its concept by a name the term replaces. So the change that renames a term owns the term's break, which lasts while any use of a name it replaces is left. To judge it, a reviewer reads the analysis's artefacts in force for the names the term replaces.
  - So a writer defines a term before an artefact uses its concept, and adds no second term for a concept the glossary defines.
  - **No anchor.** Using a term asks for no anchor on it.
  - **History.** This rule judges an artefact in force. A withdrawn artefact is history.

## RS-SAN-009 — A use case starts only from what is already true

A use case starts only from what is already true. Each of its preconditions names the use cases of its analysis that make it true.

- **How:**
  - **A precondition.** A state a use case makes true, by its postconditions or a guarantee, which no step checks. A condition that holds only in some cases is a variant's, not a precondition.
  - **Its producers.** Every use case in force of the same analysis that makes a precondition true, any one of them enough. A producer is another use case, or the use case itself.
  - So a release that starts from the last release names itself.
  - **The environment.** What the environment gives alone is an assumption, stated only in the part whose id is `assumptions`, with the record that admits it. Where it is an alternative to a use case, it is stated in that precondition's line instead, with its record. So no environment fact is stated twice.
  - **The words.** Each line of the part whose id is `preconditions` opens with its producers, such as `**From UC-003:**`, `**From UC-001 or UC-064:**` or `**From UC-059, or Environment:**`.
  - **Meaning.** A producer's postconditions or guarantees make the precondition true, read as their words state them.
  - **Initial use cases.** A use case that needs no other one has no precondition. Its part whose id is `preconditions` reads `None.`, and it writes no `after`.
  - **A new producer.** A use case breaks this rule while another use case in force has a precondition that it makes true and that does not name it. So the change that adds a use case, or splits one, owns that break. To judge it, a reviewer reads the analysis's preconditions for the states the new use case makes true.
  - **`after`.** A use case may list its producers in `after`, one entry for each precondition, in its order. An entry lists use-case ids, the use case's own among them, and `environment`, never `environment` alone. Where `after` is written, it names the producers the words name.
  - **An area's number.** A number that opens an area's folder name gives one valid order in which the areas build on each other, never their importance. Where a use case's area carries one, each of its preconditions has at least one producer in its own area or a lower-numbered one. The environment counts as one before every area. A later producer may stand beside it, as an alternative.
  - **No number.** A use case in an area without a number, or in no area, has no place in that order. This item then asks nothing of it.
  - **What a check can hold.** Of a use case that writes `after`, a script can read:
    - that each producer is a use case in force of the same analysis, or `environment`
    - that `after` names the producers the words name
    - that each precondition of a use case in a numbered area has at least one producer in its own area or a lower-numbered one

    Until this set declares a check of them under `checks`, a reviewer judges them too.
  - **Its limits.** No script that reads `after` can settle these, so a reviewer judges each:
    1. **Meaning.** The producers' ids show structure alone. Whether a producer's postcondition makes the precondition true is read from the words.
    2. **Alternatives and loops.** Real dependencies hold both. So a precondition may name several producers, the environment beside them, and its own use case.
    3. **The environment.** It is no escape. Each environment fact names its record, and the record admits the fact.
    4. **A partial order.** Use cases build on each other in a partial order. The areas' numbers show one valid order of it, never the only one.
    5. **A picture.** `after` holds a partial order, so any picture drawn from it shows one reading of the chain. The use cases are what this rule judges.
    6. **A split or a merge.** Splitting or merging use cases can leave a list of producers incomplete, and so can a new use case.
    7. **A closed loop.** A loop of use cases inside one area, with no way out to the environment, meets every item a script can read. A reviewer judges whether each chain, followed back, ends at an initial use case or at the environment.
  - **No anchor.** `after` draws no anchor. So a changed postcondition flags no use case that names its use case as a producer. A reviewer of that change reads each one.
  - **History.** This rule judges a use case in force. A withdrawn use case is history.
  - **Note:** software-analysis DEC-001 calls this the rule of logical consequence.

## RS-SAN-010 — An analysis names only the analyses its component depends on

An analysis artefact names another analysis only where its component depends on that analysis's component, and names an optional one only as an option.

- **How:**
  - **What names an analysis.** An artefact names another analysis where it names that analysis, or one of its artefacts, such as `core:TERM-change` or `core:ACT-developer`. The glossary's head names each analysis it lists terms or actors from.
  - **Which analyses.** Those of the components its own component depends on, required or optional. Where the components declare their dependencies, such as in a capability's package metadata, those declarations say which. Elsewhere, software-analysis's project configuration lists them.
  - So the analysis of a component that depends on no other names no other analysis, as a methodology's core names none of its capabilities'.
  - **A required one.** It is the analysis's environment. What it provides is stated as assumptions, each naming the record that admits it.
  - **An optional one.** A statement that relies on it says that it holds where that component is present. The analysis works without it.
  - **The glossary's head.** Wherever this rule binds on a term, it judges the head of the glossary that holds the term too.
  - **A break.** An artefact breaks this rule where it names an analysis of a component its own does not depend on. It also breaks it where it relies on an optional one as though that component were always present.
  - **History.** This rule judges an artefact in force. A withdrawn artefact is history.

## RS-SAN-011 — A domain-model view uses only the views before it

A domain-model view names a concept that another view of its analysis explains only where that view's number is lower.

- **How:**
  - **A view's number.** The number its file's name opens with, compared as a number. Two views may share one, and then neither names a concept the other explains.
  - **What a view explains.** Each concept whose term its `explains` lists, while the view is in force.
  - **What it names.** A concept whose term one of its statements uses, by the term's name or a form made from it, such as a plural. Its statements are its body, the labels of its diagrams included.
  - **The glossary first.** A view may name any term in force that no view of its analysis explains, since the glossary comes before the views.
  - **Another analysis.** A term the head of its glossary lists from another analysis is used as that analysis defines it. Whatever explains it there, this rule asks nothing of it.
  - So a relation between the concepts of two views is stated in the view with the higher number.
  - **A new section.** A view also breaks this rule while a view of its analysis with an equal or a lower number names a concept it explains. So the change that adds a section to a view, or moves one into it, owns that break. To judge it, a reviewer reads those views for the term's name.
  - **No anchor.** A view's uses of other views lie in its prose and its diagrams, which draw no anchor. So no check sees them, and a reviewer judges each.
  - **History.** This rule judges a domain-model view in force. A withdrawn view is history.
