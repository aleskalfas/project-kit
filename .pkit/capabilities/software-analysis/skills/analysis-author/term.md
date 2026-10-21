# Adding a glossary term

A term is a word of the domain and what it means. It is an entry of the glossary, `TERM-<slug>`, with a stable id separate from the name it is written as today, so a rename breaks nothing that cites it.

## 1. Does the word need pinning down?

Add a term when a word or a phrase is used in a meaning of the project's domain, one a general dictionary does not give it. Add one too when two words are used for one thing, or one word for two. A word used as a dictionary has it needs no entry.

Before you stamp it, check that no term in force defines the concept already. DEC-001 point 12 gives no concept a second term, so give each concept one term (the shared framing's "Use the glossary's terms").

## 2. Choose the slug and the name

The word as the domain says it, in the singular — `sandbox`, `suite`. The slug is the id for ever; `--name` is how it is written today.

- **One name, one concept.** No other term in force of the analysis may hold the name, ignoring case, nor a term of an analysis it builds on, whether its head lists that term or not. Nor may the name be one another term replaces. `pkit analysis validate` refuses each (DEC-001 points 1 and 2).
- **Two concepts, one word.** Give each a qualified name, such as `business process` and `system process`. The bare word then stays an ordinary word, which no term defines.

## 3. Decide what it rests on

Where does the software or a decision embody the word — the type or module that implements it (`--path`), the decision that defines it (`--record`)? When nothing does, stamp it with `--unanchored-because "<why>"` instead.

## 4. Stamp it

```
pkit analysis new term <slug> --name "<Term>" [--path <glob>]... [--record <id>]...
pkit analysis new term <slug> --name "<Term>" --unanchored-because "<why nothing embodies it>"
```

## 5. Fill it

The stamp writes the entry's `definition` as its hint, `<!-- pkit:hint … -->`, which says what goes there and gives an example, as each part of the section holds its own. Fill each part as its hint says, and delete the hint: the `definition` in the front matter, and each part of the entry's section. Name each concept the definition uses by its term (the shared framing's "Use the glossary's terms").

Where the analysis keeps a domain model, the links between terms read two more fields, which you write by hand in the entry's front matter (DEC-001 point 1; DEC-004 point 7):

- **`noun-forms`** lists other forms of the name as a noun, such as its plural, `[sandboxes]`. List only forms that cannot read as a verb: `payments`, never `orders`. Each counts as a name, so no other term takes it.
- **`other-senses`** lists each phrase in which the name has another sense, one the distinctions tell apart, such as `in order to` beside the `order` a customer places. Each holds one of the term's names, and more. No link names the term inside it.

Then run `pkit analysis link` where the analysis keeps a domain model. A new term moves the links of each section that mentions it first. Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first.

## Later

- **Renaming** — write the new `name`, and put the old one first in `replaces:`, newest first. The id never changes.
- **Withdrawing** — set `status: withdrawn` when the word is no longer used; the entry and its id stay. A view in force explains no withdrawn term, so take its section out of the view that explains it, in the same change (`view.md`).
- **Its link to the domain model.** A term a domain-model view explains carries a line under its heading that links to its section. The stamp of the view writes it, and the check holds it equal to the view. Leave the line as the stamp wrote it, and write the line the check names when a view changes. A rename changes the section's heading in the view, and the link's section.
- **Its mentions' links.** A rename moves each link to the term's entry, since the entry's anchor gives its name. Run `pkit analysis link`, in this analysis and in each analysis of the repository that builds on it. A link on a word the text uses in another sense is a finding: reword a view's statement, or, in a glossary entry, list the phrase in `other-senses`. The escape `<!-- pkit:not-the-term -->` right before a mention serves last, such as for a word in a quotation.
- **Revalidating it** — read the section of the view that explains it too, since a changed definition can make the section untrue.
- **Its uses.** On a rename, a withdrawal or a changed definition, find each use of the term's name, and of the names it replaces, in the analysis's artefacts in force. Mend each in the same change: the new name, another term, or words that fit the new definition. Using a term asks for no anchor, so nothing flags those uses for you (the shared framing's "Use the glossary's terms").
