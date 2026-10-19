# Adding a glossary term

A term is a word of the domain and what it means. It is an entry of the glossary, `TERM-<slug>`, with a stable id separate from the name it is written as today, so a rename breaks nothing that cites it.

## 1. Does the word need pinning down?

Add a term when a word or a phrase is used in a meaning of the project's domain, one a general dictionary does not give it. Add one too when two words are used for one thing, or one word for two. A word used as a dictionary has it needs no entry.

Before you stamp it, check that no term in force defines the concept already. DEC-001 point 12 gives no concept a second term, so give each concept one term (the shared framing's "Use the glossary's terms").

## 2. Choose the slug and the name

The word as the domain says it, in the singular — `sandbox`, `suite`. The slug is the id for ever; `--name` is how it is written today.

## 3. Decide what it rests on

Where does the software or a decision embody the word — the type or module that implements it (`--path`), the decision that defines it (`--record`)? When nothing does, stamp it with `--unanchored-because "<why>"` instead.

## 4. Stamp it

```
pkit analysis new term <slug> --name "<Term>" [--path <glob>]... [--record <id>]...
pkit analysis new term <slug> --name "<Term>" --unanchored-because "<why nothing embodies it>"
```

## 5. Fill it

The stamp writes the entry's `definition` as its hint, `<!-- pkit:hint … -->`, which says what goes there and gives an example, as each part of the section holds its own. Fill each part as its hint says, and delete the hint: the `definition` in the front matter, and each part of the entry's section. Name each concept the definition uses by its term (the shared framing's "Use the glossary's terms").

Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first.

## Later

- **Renaming** — write the new `name`, and put the old one first in `replaces:`, newest first. The id never changes.
- **Withdrawing** — set `status: withdrawn` when the word is no longer used; the entry and its id stay.
- **Its uses.** On a rename, a withdrawal or a changed definition, find each use of the term's name, and of the names it replaces, in the analysis's artefacts in force. Mend each in the same change: the new name, another term, or words that fit the new definition. Using a term asks for no anchor, so nothing flags those uses for you (the shared framing's "Use the glossary's terms").
