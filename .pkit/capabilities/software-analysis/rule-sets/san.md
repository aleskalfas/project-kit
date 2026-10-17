---
rule-set: SAN
version: 0.1.0
rules:
  RS-SAN-001:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["software-analysis:DEC-001"]}
        revalidated:
          at: 2026-10-16T21:18:56Z
          outcome: updated
  RS-SAN-002:
    status: proposed
    origin: {decision: "software-analysis:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["software-analysis:DEC-001#3"]}
# What this capability's checks enforce of each rule (COR-051 point 2). Of the
# format rule, it is the structure each artefact kind ships: its parts, the
# glossary's head and its forms (DEC-001 point 1). Of the append-only rule, it
# is a comparison of each use case with where the change left its base: the
# default branch's, or the base the comparison names (DEC-001 point 3;
# COR-054 point 3). `pkit validate` never runs that check, so a project runs
# it in its check gate. A check
# enforces its part only where its rule binds. Whoever judges the rest of a
# rule leaves that part to the check. Where a project's rule tightens a
# structure, the project's set declares what the check enforces of that rule.
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
        renumbered nor removed. It is renumbered where its text now stands
        under another number or letter, one the base did not give that same
        text, and no longer under its own. It is removed where its number or
        letter is gone and it is not renumbered. A number or a letter that
        holds other text passes as an edit. So a step replaced by another under
        its number, and a step renumbered and reworded at once whose old number
        holds another step, are left to whoever judges the rest of the rule.
---

# SAN — the software-analysis method

The rules for a project's analysis artefacts, whatever the project (software-analysis DEC-001 points 1 and 3). Like every method rule set, this set takes no scope (COR-051 point 2). Its rules bind only through a set of the project's own that inherits it (COR-051 point 7). A rule binds nothing until it is accepted (COR-051 point 4). A revalidation record is a held document, which no rule binds on, so the capability checks its structure itself (DEC-001 point 1). How rules are named, grounded and inherited is the rule-set record's (COR-051), so it is not repeated here.

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
    - **Where a sentence ends.** At a full stop, a question mark or an exclamation mark followed by a space and a capital letter, and at the end of the text.
      - Any white space counts as a space, such as a line end, several spaces or a no-break space. A character a reader cannot see, such as a zero-width space, counts as nothing.
      - A mark inside code, a code span or a fenced block, ends no sentence.
      - So a mark followed by a lowercase letter, as in "e.g. for" or "3. října", ends no sentence. One followed by a capital does, as in "Dr. Smith" or "z. B. Rechnungen", so a writer rewords such a text.
    - **A script without capital letters,** such as Chinese or Arabic: a mark followed by one of its letters ends no sentence. So a text in such a script is never split.

## RS-SAN-002 — A use case's steps and variants keep their numbers and letters

A use case's steps and variants keep their numbers and letters.

- **How:**
  - **Steps.** A change renumbers no step its use case held before the change, and removes none.
  - **Variants.** A change gives no variant its use case held before the change another step number or letter, and removes none.
  - **New ones.** Steps and variants are append-only. A new step takes a number past the last of its use case, and a new variant a letter past the last of its step.
  - So a step added between two others still takes the next free number, and a step that no longer happens stays under its number.
