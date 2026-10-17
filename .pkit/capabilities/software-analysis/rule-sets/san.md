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
# What this capability's check enforces of the format rule (COR-051 point 2;
# DEC-001 point 1). It is the structure each artefact kind ships: its parts,
# the glossary's head and its forms. The check enforces it only where the rule
# binds. Whoever judges the rest of the rule leaves it to the check. Where a
# project's rule tightens a structure, the project's set declares what the
# check enforces of that rule.
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
---

# SAN — the software-analysis method

The rules for a project's analysis artefacts, whatever the project (software-analysis DEC-001 point 1). Like every method rule set, this set takes no scope (COR-051 point 2). Its rules bind only through a set of the project's own that inherits it (COR-051 point 7). A rule binds nothing until it is accepted (COR-051 point 4). A revalidation record is a held document, which no rule binds on, so the capability checks its structure itself (DEC-001 point 1). How rules are named, grounded and inherited is the rule-set record's (COR-051), so it is not repeated here.

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
    - **One text.** In a list, each item is one text, and a nested item is one apart from the item it sits in. What a part holds outside its lists is one text too, a list inside a block quote included. In a front-matter field that holds a list, each item is one text.
    - A sentence ends at a full stop, a question mark or an exclamation mark. It ends there only where a space, a line end or the end of the text follows the mark.
    - A mark inside a code span ends no sentence.
    - So an abbreviation that ends in a full stop, such as "e.g.", ends a sentence wherever a space or a line end follows it.
