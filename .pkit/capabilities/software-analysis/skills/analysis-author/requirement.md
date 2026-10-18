# Adding a requirement

A requirement says what must hold of the system beyond one actor's goal: how well it behaves, behaviour that holds across use cases, or a limit on the solution. It is a file, `REQ-NNN-<slug>.md`, in the folder of its kind under `requirements/`. The three kinds share one numbering, so a requirement keeps its id when it moves to another kind (DEC-002 point 2).

## 1. Is it a requirement, and of which kind?

Ask what the statement is about:

- **How well the system must behave**, such as how fast, how reliably or how safely: a **quality requirement**.
- **Behaviour that holds across use cases**, such as a business rule of the domain: a **functional requirement**.
- **A limit on the solution**, which the design takes as given: a **constraint**.
- **Behaviour that serves one actor's goal** is a use case, not a requirement (`use-case.md`). Write it as a use case, even when it reads like a rule.

The line between the kinds can blur. One obligation may read as a quality with its measure, or as a limit the design takes as given. Choose the kind its readers will treat it as: a design trades a quality against cost, and takes a constraint as given. Moving it later keeps its id.

A standard's list of quality characteristics, such as performance, reliability or security, may serve as a checklist when you look for quality requirements. The shipped kinds carry no field for it (DEC-002 point 4). A project that wants one adds it as a part of its own (`choose-templates.md`).

## 2. Ask what verifies it, and why it is needed

Ask both before you stamp it. A requirement is an obligation someone could check, even when nothing checks it yet.

- **What verifies it.** Name each test, check or review that shows it is met, by what it does and never by its path. Anchor the file of each test or check with `--path` (step 5). Where nothing verifies it yet, that part reads `None.`, so the gap is seen (DEC-002 point 5).
- **Why it is needed.** For a quality or a functional requirement, whose need it serves and why the system must meet it. For a constraint, who or what imposes it, and why the design cannot choose otherwise.

## 3. Name its actors, and what it refines

- **`--actor <ACT-id>`**, once for each actor whose need it meets, if any. Each must be in the analysis and in force. Stamp a missing one first (`actor.md`).
- **`--refines <REQ-id>`**, once for each requirement it refines, of any of the three kinds, if any. Each must be in the analysis and in force. A requirement never refines itself.

The stamp writes each in `actors` or `refines`, and anchors it. So a changed actor, or a changed requirement it refines, flags this one.

## 4. Choose the slug, the title and the area

- **Slug**: the obligation, in a few words: `fast-report`, `approved-only`, `client-country`. It names the file only.
- **`--title`**: the obligation as the heading reads it: `Show a report within two seconds`. The heading is `# REQ-NNN · <kind> · <title>`, the kind shown as `Quality`, `Functional` or `Constraint`.
- **`--area <word>`**: a folder per functional area, when the project groups requirements. A move to another area never changes the id. A move renames the file, so revalidate it in the same change (COR-050 point 3).

## 5. Decide what it rests on

- **`--path`**: the file of each test or check that verifies it, and the narrow code that holds it. Never every file of the class it binds, such as every command: that anchor is over-broad (COR-050 point 7).
- **`--record`**: each record it rests on, and each record that answers it.
  - Where a record states the requirement's measure, the requirement holds the measure. The record names the requirement when the project next changes it (DEC-002 point 9).
  - A record a component ships keeps its text, and never names one project's requirement.
- **An architecture view** that realises it, where the project keeps one: `--path` on the view's file.
- **Nothing anchors it back.** No record and no view anchors a requirement.

**A requirement with no anchor at all** may give the reason instead, such as one a stakeholder states before anything is built. Stamp it with `--unanchored-because "<why nothing embodies it>"`, which any of the three kinds takes. It then names no actor, refines no requirement, and has no path or record. A requirement with an actor, or anything else to anchor, gives those instead. The reason is a person's decision: an agent following this skill shows the person the reason word for word, and stamps only once they accept it.

## 6. Stamp it

```
pkit analysis new quality-requirement <slug> [--actor <ACT-id>]... [--refines <REQ-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
pkit analysis new functional-requirement <slug> [--actor <ACT-id>]... [--refines <REQ-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
pkit analysis new constraint <slug> [--actor <ACT-id>]... [--refines <REQ-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
pkit analysis new functional-requirement <slug> [--title "<Title>"] [--area <area>] --unanchored-because "<why nothing embodies it>"
```

It takes the next free number across the three kinds, on the default branch and in the working tree.

## 7. Fill it

Each field and part you fill holds its hint, which says what goes there and gives an example. Fill each as its hint says, and delete the hint. That covers the statement, the measure and where it holds, in the front matter, and each part of the body. Your answers from step 2 go in the parts on what verifies it and on why it is needed, or who imposes it.

Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first, and `pkit analysis check-numbers` before merging.

## Later

- **Changing its obligation.** A change to its statement, its measure or where it holds asks for a revisit of every anchor outside the analysis: each record, view, test and file of code it names (DEC-002 point 4). Its actors and the requirements it refines stay out. In the same change, answer each such target in one of three ways:
  - **Change it**, such as the test that checks the old measure.
  - **Say why it still stands:** `pkit friction revisit <REQ-id> --target <kind>:<value> --outcome unchanged --reason "<why>"`.
  - **Leave it out of date** until an open follow-up revisits it: `--outcome deferred`, its reason naming the follow-up.

  `pkit friction check` lists each target still owed (COR-050 point 16). A change to a body part asks for no revisit.
- **Changing its kind.** Move the file to the other kind's folder, and keep its id.
  - Rewrite it to that kind's structure. A constraint says who imposes it where the other two kinds say why they are needed, so that part changes.
  - The heading shows the new kind.
  - Revisit what it anchors, since a change of kind flags nothing by itself (DEC-002 point 4). Revalidate it in the same change (COR-050 point 3).
- **A record it contradicts.** Where it contradicts an accepted record it rests on, the record wins. Change the requirement, or change the record first (DEC-002 point 8).
- **Two requirements that conflict.** The choice between them is a decision, so a decision record holds it. No field relates the two (DEC-002 point 8).
- **Withdrawing.** Set `status: withdrawn` once no requirement in force refines it. The file stays, and its id is never used again. Revisit what it anchors, as for a change of kind (DEC-002 point 4).
