# Adding a glossary term

A term is a word of the domain and what it means. It is an entry of the glossary, `TERM-<slug>`, with a stable id separate from the name it is written as today, so a rename breaks nothing that cites it.

## 1. Does the word need pinning down?

Add a term when a word is used with a meaning particular to this project, when two words are used for one thing, or when one word is used for two. A word used as a dictionary would have it needs no entry.

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

- **`definition`** — what the term means, in one sentence.
- **The body section** — more when one sentence is not enough: where it applies, what it is not, an example.

Then run the checks in the shared framing's "After stamping".

## Later

- **Renaming** — write the new `name`, and put the old one first in `replaces:`, newest first. The id never changes.
- **Withdrawing** — set `status: withdrawn` when the word is no longer used; the entry and its id stay.
