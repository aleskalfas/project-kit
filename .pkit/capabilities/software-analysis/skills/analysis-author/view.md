# Adding a domain-model view

A domain-model view explains a group of related concepts, one section for each, and draws how they relate ([software-analysis:DEC-004-domain-model-views]). It is a file of its own, `domain-model/<number>-<slug>.md`, beside the glossary. The glossary defines each concept, and the view explains it. A project keeps views only where it chooses: a term no view explains stays as it is.

## 1. Is it a view?

Write one for a group of concepts a reader takes in at once, such as those of ordering, or of payment. Which concepts form a group is your choice.

- **Each concept has its term first.** A view explains concepts the glossary defines, under their terms' names. Where a concept has no term, go back and stamp it (`term.md`).
- **Each term is explained by one view.** No two views in force explain one term, so each explanation has one home. The stamp refuses a term another view explains.
- **The domain, never the software.** A view describes what the concepts are and how they relate, and nothing of how the system is built.

## 2. Choose its number, its slug and its title

- **The number** opens its file's name, such as `010`. It gives one valid order of the views, in which each uses only the views before it: a view names a concept another view explains only where that view's number is lower. Its form, such as its width and its steps, is your project's. A project with a rule of its own on the form, as project-kit's `ANA` has, keeps to that rule. The number is no part of the id, so a view given another number keeps every citation true.
- **The slug** is its id for ever, `VIEW-<slug>`, and an id is never used again. Name the group as the domain says it: `orders-and-payments`.
- **The title** is how the heading reads it, `--title "Orders and payments"`.

## 3. Choose the terms it explains

Name each with `--explains <TERM-id>`, in the order of its sections.

- **Its own analysis's terms alone.** A term the glossary's head lists from another analysis is explained there.
- **In force.** A term withdrawn is explained nowhere.
- **A concept of a lower view** may be named in this view's sections and diagram, to state a relation. It is no term this view explains. A relation between two views' concepts is stated in the higher view.

## 4. Decide what it rests on

The stamp anchors each term it explains, from `explains`. Add as `--record` each record its statements cite or apply. Each fact a section states under *Always true* rests on the record that decides it. A view anchors no code, so the stamp takes no `--path`: the term anchors the code that embodies it.

## 5. Stamp it

```
pkit analysis new view <slug> --number <number> --explains <TERM-id> [--explains <TERM-id>]... [--title "<Title>"] [--record <id>]...
```

The stamp writes the view, with one section for each term, headed by the term's name. It also writes each term's link to its section, on a line under the term's heading in the glossary. The check holds that line equal to the view.

## 6. Fill it

Each part holds its hint, which says what goes there and gives an example. Fill each part as its hint says, and delete the hint.

- **The opening** says what the group covers, then draws its class diagram. Draw the concepts, how they relate and the attributes that matter, in a Mermaid fence with an `accTitle`, an `accDescr` and no styling. Draw a concept of another view, or a term no view explains, by its name alone.
- **Each section** explains its concept for a newcomer, then gives its *Attributes*, its *Relations*, its *States* and what is *Always true* of it. Where the concept has a life cycle, draw its states after the text of *States*.
- **One home for each fact.** A diagram shows only what the sections state. What a section states fits exactly what the term's definition fits, never more and never less. An obligation the system must keep is a functional requirement, which names the concept by its term (`requirement.md`).
- **Its terms.** Write each concept by its term, a diagram's labels included (the shared framing's "Use the glossary's terms").

Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first. Where the format rule binds, the check holds each section's heading to the name of the term `explains` lists in its place.

## Later

- **A section added by hand.** Add its term to `explains`, in the section's place, and anchor the term. Write the term's link the check names, under the term's heading in the glossary. Moving a section to another view moves its term between the two lists, the two views' anchors and its link.
- **Renumbering or renaming its file** keeps its id where the slug stays. Each term it explains then links to the new file: write each link the check names.
- **Withdrawing** — set `status: withdrawn`, and remove each term's link to it. A withdrawn view explains nothing, so its terms may be explained by another view.
- **A term renamed** renames its section's heading, and its link's section. A page anchored on the section's old slug is then dead, and validation fails until the change mends it.
- **Revalidating a term** reads the section that explains it too. A change of code reaches a view only through a term whose revalidation changes it.
