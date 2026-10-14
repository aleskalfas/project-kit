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
# The part of the format rule that this capability's check enforces (COR-051
# point 2 and DEC-001 point 1): the parts each kind ships, and the forms its
# declared structure gives. The check enforces it only where the rule binds,
# and whoever judges the rest of the rule leaves that part to it.
checks:
  RS-SAN-001:
    - check: "software-analysis:validate"
      part: >-
        Every part its kind ships is present, in the order the structure gives. A
        part with nothing to say reads `None.`, where the structure allows it. A part
        or a front-matter field that the structure gives a form holds that form, in
        each item of a list. A revalidation record is held to the structure in force
        when it was written. A withdrawn artefact is held to no part or form that
        came after its withdrawal.
---

# SAN — the software-analysis method

The rules for a project's analysis artefacts and revalidation records, whatever the project (software-analysis DEC-001 point 1). Like every method rule set, this set takes no scope (COR-051 point 2). A rule binds nothing until it is accepted (COR-051 point 4). How rules are named, grounded and inherited is the rule-set record's (COR-051), so it is not repeated here.

A rule's statement and its *How* bind. Inside a *How*, a "such as" phrase and a sentence that starts with "So" only illustrate.

## RS-SAN-001 — An analysis artefact or a revalidation record carries its kind's structure

An analysis artefact or a revalidation record carries its kind's declared structure, and each kind has a template.

- **How:**
  - **Parts.** Every part its kind ships is present, in the order the structure gives. A part with nothing to say reads `None.`, where its structure allows it. A part a project adds binds only where the project rule that asks for it binds too.
  - **Forms.** A part or a front-matter field that the structure gives a form holds that form. In a list, each item holds it.
  - **Hints.** A hint binds nothing, so the voice a hint asks for is no part of this rule.
  - **History.** A revalidation record is held to the structure in force when it was written. A withdrawn artefact is held to no part or form that came after its withdrawal.
  - **The `sentence` form.** Text of this form, such as an actor's need, holds one sentence: no sentence ends before the text's last word.
    - A sentence ends at a full stop, a question mark or an exclamation mark. It ends there only where a space, a line end or the end of the text follows the mark.
    - A mark inside a code span ends no sentence.
    - So an abbreviation that ends in a full stop, such as "e.g.", ends a sentence wherever a space or a line end follows it.
