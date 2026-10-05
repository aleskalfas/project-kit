---
rule-set: ANALYSIS
version: 0.1.0
inherits: [WRITE@0]
scope: [tech-docs/analysis/**]
rules:
  RS-ANALYSIS-001:
    status: proposed
    origin: {why: "A need is one sentence, and so is a use case's goal (software-analysis DEC-001 point 1). An actor's needs are joined into one reader description, and first person keeps the actor's voice (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
    pkit:
      friction:
        anchors:
          path: [.pkit/capabilities/software-analysis/scripts/_lib/readers.py]
          record: ["software-analysis:DEC-001"]
  RS-ANALYSIS-002:
    status: proposed
    origin: {why: "The core actors, as revised under these rules for PR #1345, use these nine labels and no other. Every actor's section takes them in this order, and leaves out the ones it has nothing for."}
    fills: [RS-WRITE-002#labels]
    pkit:
      friction:
        anchors:
          artefact: [RS-WRITE-002]
---

# ANALYSIS — project-kit's writing rules for its analysis

These rules say how project-kit writes its analysis: its general writing rules, `WRITE`, and the analysis's own rules below.

- **Where the rules apply:** everything under `tech-docs/analysis/`, which is this set's scope. project-kit's operational rules send whoever writes the analysis here (`.pkit/rules/project.md`).
- **What it inherits:** every rule of `WRITE` (`tech-docs/rule-sets/writing.md`), unchanged. This set adds rules and fills WRITE's extension points, but never relaxes a rule of WRITE (COR-051 point 7).
- **What it adds:** the rule for needs and goals (RS-ANALYSIS-001).
- **What it fills:** the list of labels for each kind of analysis document (RS-ANALYSIS-002, filling `RS-WRITE-002#labels`).
- **The pin:** `WRITE@0`, since WRITE stays below 1.0.0 while its rules are proposed. Once they are accepted, WRITE goes to 1.0.0, and the pin becomes `WRITE@1`.
- **The name, to confirm:** `ANALYSIS`. A set's name is permanent once on main, and is part of every rule id.
  - It names what the set governs, as `TECH` and `USER` name their spaces.
  - A component's set is named after the component, as living-docs' `LDOC` is. So a set that software-analysis ships would take a name of its own.
  - Validation refuses two sets of one name, and software-analysis is built in this repository. So a clash could not land unseen.
- **How a rule reads:** as in WRITE, a statement, then *How*, then examples. A rule's reason is the `why` of its origin (COR-051 point 5). RS-ANALYSIS-002 has no examples of its own, since RS-WRITE-002's use its list.
- **What binds:** a rule's statement and its *How*, as in WRITE.
- **Note:** a rule binds only once it is accepted, and an inherited rule binds here only once WRITE accepts it (COR-051 point 4).

## Needs and goals

This rule is for an actor's needs and a use case's goal.

### RS-ANALYSIS-001 — One need or goal, one sentence

Write each need of an actor, and each use case's goal, as one sentence in its actor's voice. That sentence is an imperative that starts with its verb, using *I*, *me*, *my* and *myself* wherever the actor refers to itself.

- **How:**
  - *Never* may come before the verb.
  - Never split a need or a goal into two sentences, and keep it within the limit of RS-WRITE-005.
  - A use case's goal is the same user story as a need (software-analysis DEC-001 point 1), so it takes the same form.
- **Breaks the rule:**
  - "Run every check with no terminal and no person to answer. Gate the merge on the check's exit status." (the plain rewrite, split in two)
  - "Find the agent's role definition deployed, …" (the first ASD-STE100 run, where the AI agent names itself)
- **Keeps the rule:**
  - "Run every check with no terminal and no person to answer, and gate the merge on its exit status." (the original)
  - "Find my role definition deployed, …" (the original)

## Labels

This rule says which labels each kind of analysis document gives its parallel sections.

### RS-ANALYSIS-002 — Each kind's list of labels

Take the labels of an analysis document's parallel sections from the list for its kind, in that list's order.

- **The actors file**, `tech-docs/analysis/use-case-model/actors.md`: *The setup*, *Always a person*, *Can be*, *Does*, *Comes*, *Brings*, *In the model*, *Core* and *Note*.
- **How:**
  - This rule fills `RS-WRITE-002#labels`, and the rest of RS-WRITE-002 holds as written. A section may leave out a label, and no label holds a pronoun.
  - A kind with no list here takes its labels as RS-WRITE-002 says.
  - A later kind's list joins this rule beside the actors file's, under the kind's name.
