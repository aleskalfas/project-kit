# Adding a requirement

A requirement is what binds many use cases at once. It is a file, `REQ-NNN-<slug>.md`, in the folder of its kind under `requirements/`. The three kinds share one numbering, so a requirement keeps its id when it moves to another kind (DEC-002 point 2).

## 1. Is it a requirement, and of which kind?

Ask what the statement is about:

- **How well the system must behave**, such as how fast, how reliably or how safely: a **quality requirement**.
- **Behaviour that holds across use cases**, such as a business rule of the domain: a **functional requirement**.
- **A limit on the solution**, which the design takes as given: a **constraint**.
- **Behaviour that serves one actor's goal** is a use case, not a requirement (`use-case.md`). Write it as a use case, even when it reads like a rule.

The line between the kinds can blur. A property with a measure and a limit taken as given may describe one obligation. Choose the kind its readers will treat it as: a design trades a quality against cost, and takes a constraint as given. Moving it later keeps its id.

A standard's list of quality characteristics, such as performance, reliability or security, may serve as a checklist when you look for quality requirements. It is never a field: the folder gives the kind, and no part names a characteristic (DEC-002 point 4).

## 2. Ask what verifies it, and why it is needed

Ask both before you stamp it. A requirement no one can check, or no one needs, is not worth keeping.

- **What verifies it.** Name each test, check or review that shows it is met, by what it does. A requirement nothing verifies yet is still kept: its *Verified by* reads `None.`, so the gap is seen (DEC-002 point 5).
- **Why it is needed.** For a quality or a functional requirement, whose need it serves and why the system must meet it. For a constraint, who or what imposes it, and why the design cannot choose otherwise.

## 3. Name its actors, and what it refines

- **`--actor <ACT-id>`**, once for each actor whose need it meets, if any. Each must be in the analysis and in force. Stamp a missing one first (`actor.md`).
- **`--refines <REQ-id>`**, once for each requirement it narrows, of any of the three kinds, if any. Each must be in the analysis and in force. A requirement never refines itself.

The stamp writes each in `actors` or `refines`, and anchors it. So a changed actor, or a changed requirement it refines, flags this one.

## 4. Choose the slug, the title and the area

- **Slug**: the obligation, in a few words: `fast-report`, `approved-only`, `client-country`. It names the file only.
- **`--title`**: the obligation as the heading reads it: `Show a report within two seconds`. The heading is `# REQ-NNN · <kind> · <title>`, the kind shown as `Quality`, `Functional` or `Constraint`.
- **`--area <word>`**: a folder per functional area, when the project groups requirements. A move to another area never changes the id.

## 5. Decide what it rests on

- **`--path`**: the file of each test or check that verifies it, and the narrow code that holds it. Never every file of the class it binds, such as every command: that anchor is over-broad (COR-050 point 7).
- **`--record`**: each record it rests on, and each record that answers it. Where a record states the requirement's measure, the requirement holds the measure, and the record names the requirement when it is next changed (DEC-002 point 9).
- **An architecture view** that realises it, where the project keeps one: `--path` on the view's file.
- **Nothing anchors it back.** No record and no view anchors a requirement.

**A requirement nothing embodies**, such as one a stakeholder states before anything is built, takes `--unanchored-because "<why nothing embodies it>"` instead. It then has no anchor at all: no actor, no requirement it refines, and no path or record. The reason is a person's decision: an agent following this skill shows the person the reason word for word, and stamps only once they accept it.

## 6. Stamp it

```
pkit analysis new quality-requirement <slug> [--actor <ACT-id>]... [--refines <REQ-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
pkit analysis new functional-requirement <slug> [--actor <ACT-id>]... [--refines <REQ-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
pkit analysis new constraint <slug> [--actor <ACT-id>]... [--refines <REQ-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
pkit analysis new constraint <slug> [--title "<Title>"] --unanchored-because "<why nothing embodies it>"
```

It takes the next free number across the three kinds, on the default branch and in the working tree.

## 7. Fill it

Each field and part you fill holds its hint, which says what goes there and gives an example. Fill each as its hint says, and delete the hint.

- **`statement`**, in the front matter: the obligation, in one sentence. Say what the system achieves, never how it is built.
- **`measure`**: the value or the condition that shows it is met. Write `None.` when there is none yet.
- **`applies-to`**: where it holds, such as a class of commands or the whole system. It never reads `None.`. Name no use case or journey here.
- ***Verified by*** and ***Rationale***, or ***Imposed by*** on a constraint, in the body: your answers from step 2.

Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first.

## Later

- **Changing its kind.** Move the file to the other kind's folder, and keep its id. Rewrite it to that kind's structure: a constraint's *Imposed by* becomes *Rationale*, and the reverse. The heading shows the new kind. Revalidate it in the same change (COR-050 point 3).
- **A record it contradicts.** Where it contradicts an accepted record it rests on, the record wins. Change the requirement, or change the record first (DEC-002 point 8).
- **Two requirements that conflict.** The choice between them is a decision, so a decision record holds it. No field relates the two (DEC-002 point 8).
- **Withdrawing.** Set `status: withdrawn` once no requirement in force refines it. The file stays, and its id is never used again.
