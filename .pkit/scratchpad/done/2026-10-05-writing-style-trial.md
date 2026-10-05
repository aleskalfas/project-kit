---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-05
retired: 2026-10-05
produced:
  - tech-docs/rule-sets/writing.md
---

# The writing-style trial — plain language and ASD-STE100 on the actors document

## The question

Should project-kit write its documentation and its analysis by a published guideline, and if so by which parts of it?

- **The candidates:** plain language (ISO 24495-1) and ASD-STE100 Simplified Technical English.
- **The maintainer's preference:** lists, nested lists and sub-headings over long paragraphs. Something must show what matters most.
- **The test:** a style that changes meaning is disqualified for analysis artefacts.
- **What it produced:** the proposed rules of `WRITE`, project-kit's writing rule set (`tech-docs/rule-sets/writing.md`). Each rule's reason cites this note.

The trial's working files lived in the agent workspace, which is never committed. This note keeps what the rules rest on.

## Method

The same document was rewritten once per guideline, and the versions were compared.

- **Baseline:** project-kit's eight core actors, `tech-docs/analysis/use-case-model/actors.md` as in PR #1345.
- **Plain:** a rewrite by ISO 24495-1:2023. The standard is paywalled from 5.2.3 b) on, so the US Federal Plain Language Guidelines (FPLG) stood in for the rest.
- **STE, first run:** a rewrite by ASD-STE100 Issue 9 (2025-01-15), checked word by word against its full dictionary of 875 approved words.
- **STE, second run:** an independent rewrite by the same standard. An audit agent found 16 meaning shifts in it, and the rewriter fixed 11. The comparison did not measure this run.
- **Comparison:** the baseline, plain and the first STE run. A script counted words and sentences. Every need and every statement was checked by hand against the baseline and the records it cites.

Each rewrite had the same brief: the same facts, nothing added, nothing dropped, the same file shape, and technical names kept exactly.

### How the counts were made

- **Word:** a token between spaces that holds at least one letter or digit, once bold marks and backticks are removed. A hyphenated word, an id (`COR-050`) or a file name (`CLAUDE.md`) is one word.
- **Sentence:** it ends at `.`, `?` or `!` before a space or a line end. Each need and each list item ends one too. A lead-in that ends in a colon is one sentence. Semicolons and colons end none.
- **Not counted:** headings and bold labels. A list item that is only a label is no sentence.
- **Parentheses:** their words count toward their sentence. ASD-STE100 counts a parenthesis as a sentence of its own, so the rewriters' own figures differ.
- **Paragraph:** a block of prose between blank lines. List items were checked as paragraphs too.
- **Passive, rough:** a form of *be* or *get* before an *-ed* word or a common irregular participle.

## At a glance

| Metric | Baseline | Plain | STE |
|---|---|---|---|
| Words, needs (front matter) | 918 | 942 (+3%) | 1,089 (+19%) |
| Words, body | 948 | 1,103 (+16%) | 1,385 (+46%) |
| Sentences, needs (52 needs each) | 52 | 71 | 52 |
| Sentences, body | 48 | 94 | 130 |
| Average sentence, needs (words) | 17.7 | 13.3 | 20.9 |
| Average sentence, body (words) | 19.3 | 10.3 | 10.5 |
| Longest sentence, needs (words) | 26 | 24 | 35 |
| Longest sentence, body (words) | 49 | 22 | 25 |
| Sentences over 25 words (needs / body) | 1 / 10 | 0 / 0 | 5 / 0 |
| Paragraphs over 4 sentences | 8 of 9 | 0 of 9 | 1 of 46 |
| Most sentences in one paragraph or list item | 7 | 3 | 5 |
| List items in the body | 0 | 66 | 46 |
| Headings / bold labels / colon lead-ins | 9 / 0 / 0 | 9 / 40 / 2 | 9 / 0 / 14 |
| Semicolons (needs / body) | 0 / 4 | 0 / 1 | 0 / 0 |
| Passive voice, rough (needs / body) | 10 / 4 | 10 / 5 | 3 / 3 |
| First-person needs kept | yes (30 of 52) | yes (31 of 52) | **no** (0 of 52) |

The STE column is the first run. The second run's own notes report 1,250 words of needs and 1,501 of body, counted by whitespace alone.

## Facts kept

**Checked by script, and the same in every variant:**

- the ids, names, statuses and friction blocks, in the same order
- the number of needs per actor (9, 5, 7, 7, 9, 4, 5, 6) and the eight headings
- every record id, point, issue, agent name and quoted name

### Plain: nothing dropped, three wordings changed

1. **An ambiguity resolved** (maintainer, need 3). In "Release the backbone so adopters can upgrade and pin to it, *knowing* what each change since the last release means for them", the maintainer does the knowing by grammar. Plain gave it to the adopters, and the first STE run to the maintainer. At least one of them changed the meaning.
2. **A guard turned into a goal** (maintainer, need 4). "*Never* ship a backbone change that breaks installed projects without the migration…" became "Ship a backbone change that breaks installed projects *only with* the migration…". The logic holds, but the need now reads as a wish to ship breaking changes.
3. **A narrowing** (merge authoriser). "the acceptance gate gives it acceptance" became "gives it the acceptance of drafted records and rules".

**Format changes:**

- "(:65, :67)" became "(lines 65 and 67)", and "release README:22-29" became "release README, lines 22–29". The brief said to keep such names exactly.
- 19 of the 52 needs became two sentences. software-analysis makes a need one sentence (its DEC-001 point 1), and `readers.py` joins an actor's needs with "; " into one reader description.
- A reading guide and 40 labels were added. Neither is a domain fact.

### ASD-STE100, first run: nine claims changed

| # | Where | Baseline | STE | What changed |
|---|---|---|---|---|
| 1 | Developer | "That the backbone *itself* lands pull requests is *provisional* (ADR-061 point 3, *raised as* #1222)" | "The backbone *also* puts pull requests on the default branch. This function is *not permanent*" | "Not permanent" says the function will end. "Itself" and "raised" are lost. |
| 2 | Component author, need 7 | "how far *it* *meets* them, and report what of the permission model it cannot *enforce*" | "how much *the adapter agrees with* each requirement, and which parts of the permission model it cannot *apply*" | The subject and both verbs changed (COR-047 and COR-028 point 3). |
| 3 | Merge authoriser | "the same person's *review turns* a record or rule an agent drafted *into a binding one*" | "When the same person *examines* a record or rule…, that record or rule *becomes mandatory*" | Looking at a draft now makes it binding, even if the person rejects it. |
| 4 | Developer | "every change *passes* the acceptance gate and the friction check" | "the acceptance gate and the friction check *examine* each change" | The requirement to pass is gone. |
| 5 | Developer, need 3 | "*retire* the note once it has produced something" | "*complete* the note after it gives a result" | Retiring is a lifecycle act (COR-012). "Complete" reads as "finish writing". |
| 6 | Component author, need 5 | "*Carry* the projects… *across* a breaking change" | "*Help* the projects… to continue to operate after a breaking change" | The duty to supply the migration is weakened. |
| 7 | Operator | "*answer* what the methodology gates" | "*accepts or rejects the prompts* at the gates" | Narrowed to yes or no. Gates also ask for written answers. |
| 8 | Developer, need 5 | "*judging* an agent's proposed answer word for word… when it *cannot ask* me" | "*examines each word* of an agent's proposal… when the agent *cannot get a decision*" | Judging became reading. "Cannot ask" became "asked, with no answer". |
| 9 | CI pipeline | "ships no workflow, *only* checks…, *and* one base…" | "It supplies *only* checks… The backbone *also* supplies one base" | The split text contradicts itself. |

**Smaller shifts:**

- *Own* and *itself* lost their emphasis. "own trigger", "own review" and "own repository" lost "own", and "is itself a core act" became "also a core operation".
- "unit of work" (developer) and "piece of work" (merge authoriser) both became "task". Two terms were merged without the author.
- "have them validated" became "let *the system* validate them", which names a validator the baseline never named.
- "working under the methodology" became "obeys the methodology", a new claim of compliance.
- "misleading result" became "a result that gives incorrect information". A misleading result can be accurate.
- No need kept its first person.

### ASD-STE100, second run: the audit fixed wording, not vocabulary

- **Fixed after the audit:** 11 of 16 shifts, among them "provisional", "carry across" and "only through my own review".
- **Left by the dictionary:** "adopts" became "makes the decision to use", "rests on" became "the sources of", and "a question" became "a problem".
- **Left by other rules:** no need kept its first person. General words took American spelling beside British project terms.

## What each guideline did well and badly

### Plain language

**Did well:**

- **The same labels in the same order in every section** (ISO 24495-1, 5.2.3 a). It was the largest gain for scanning. A reader can jump to *When they come* in any actor.
- **The most important thing first** (ISO 24495-1, 5.2.2). Each section opened with one line that says who the actor is, and became scannable.
- **Side matter last, under *Note*** (ISO 24495-1, 5.2.5). The main description became shorter, with nothing dropped.
- **Lists for series of three or more, each with a lead-in** (FPLG, "Use lists"). Pairs and short series stayed in the sentence, as in "decisions, rules, notes, code and its documentation", so the lists did not clutter the page.
- **Short sentences.** The average body sentence fell from 19.3 words to 10.3, and the longest from 49 to 22.
- **Pronouns named.** "how far *it* meets them" became "how far *that harness* meets each requirement". COR-047 supports that reading.
- **Kept what matters here:** the first-person needs, and every project term.

**Did badly:**

- **One idea per sentence, applied to needs,** split 19 of them.
- **Positive language** turned a guard into a goal.
- **It resolved an ambiguity on its own,** and it reformatted citation locators.
- **Length:** the body grew by 16%, from the labels and the reading guide.
- **"Familiar words"** (ISO 24495-1, 5.3.2) could not apply. Almost every noun is a project term.
- **Not tested with readers** (ISO 24495-1, Principle 4).

### ASD-STE100

**Did well:**

- **Limits that can be counted:** 25 words a sentence (6.3), six sentences a paragraph (6.6), and no semicolons (8.1). The longest body sentence fell from 49 words to 25.
- **No omitted words** (4.2). "the whole-repository report the developer" became a full clause.
- **One wording per idea** (9.4). It made the sections parallel.
- **Some needs became clearer.** "named once for every check" became "given one time *for all the checks*", which cannot be read as once per check.

**Did badly:**

- **Its vocabulary caused the meaning changes.** Approved words and their approved meanings together caused eight of the nine material changes. The 875 words serve aircraft maintenance.
- **No first person.** Only the dictionary's pronouns are allowed (GR-3), so the role noun repeats instead.
- **No technical noun as a verb** (1.7). *land* became "puts … on the default branch".
- **Length:** the body grew by 46% and the needs by 19%. Five needs passed 25 words only because a parenthesis counts as a sentence of its own.
- **No labels.** To find when an actor comes, a reader must read topic sentences.
- **A split made one section contradict itself.**
- **Technical nouns need a project glossary** (1.5 and 1.8), which project-kit lacks.

## Recommendation

The comparison recommended one shared rule set: plain language's structure, ASD-STE100's countable limits, the maintainer's preference for lists, and a rule that keeps the meaning. It left out every vocabulary rule.

- **Structure:**
  - Open each section with a one-line statement of what it is about.
  - Give parallel sections the same bold labels, in the same order.
  - Put a series of three or more items in a list with a lead-in, and keep a series of two in the sentence.
  - Put side matter last, under *Note*.
- **Sentences and paragraphs:**
  - No sentence over 25 words, with parentheses counted in.
  - One idea per sentence in prose, but not in needs.
  - One topic a paragraph, and no more than four sentences. Four was the comparison's threshold. ASD-STE100 allows six, so four is project-kit's choice.
  - No semicolons in prose, and no omitted words.
- **Words and terms:**
  - Name the thing when a pronoun could point at two things.
  - One term for one thing, taken from the project's glossary, not from an outside dictionary.
  - The active voice when the actor is known.
- **Needs:** one sentence in the actor's first person, starting with a verb, at most 25 words.
- **Keeping meaning:** a rewrite never resolves an ambiguity, reframes a guard, or swaps a project term or a citation form without the author.

## What the review of the first draft changed

An adversarial review of `WRITE`'s first draft found rules that the trial did not support as written. The rules now differ from the recommendation in these ways:

- **What matters most:** a section opens with one sentence that says what matters most, in the maintainer's words, not only what the section is about.
- **Labels:** they come from one list, in its order, and a section may leave one out.
- **Lists:** only where the items are clauses or carry detail. Pairs and short series stay in the sentence, as the plain rewrite kept them. Needs and table cells are exempt.
- **Sentence length:** words and sentences are counted as this trial counted them. No script checks the limit yet.
- **Semicolons:** two citations in one parenthesis are joined with "and", since a citation can hold a comma.
- **Omitted words:** narrowed to a verb for each clause in a series. The broad form would have banned every labelled fragment.
- **Pronouns:** a referent comes from the author, or from a cited source that the author confirms.
- **Needs:** the rule covers a use case's goal too, which software-analysis DEC-001 point 1 makes the same user story.
- **Keeping meaning:** stated in general. The trial's changes were not all of the three kinds the draft named. A split contradicted itself, a requirement was dropped, a duty was weakened, a validator was added and emphasis was lost.

## Considered and not adopted

- **ASD-STE100's approved words and approved meanings** (1.1 to 1.4, and 9.2): together they caused eight of the nine material meaning changes. Project verbs such as *land*, *ship* and *retire* are not among the 875 words.
- **ASD-STE100's "no technical noun as a verb"** (1.7 and 1.13): *land*, *ship*, *commit* and *pin* are defined project verbs. Their replacements lost precision and added words.
- **ASD-STE100's dictionary-only pronouns** (GR-3): they remove *I* and *my* from the needs.
- **ASD-STE100's simple tenses, with no *-ing* form and no phrasal verb** (3.1 to 3.5, and 9.3): the text became stilted. "carry across" became "continue to operate after", which changed its meaning.
- **ASD-STE100's count of a parenthesis as a sentence of its own** (8.3 to 8.7): it let a 35-word need pass a 25-word limit.
- **ASD-STE100's vertical-list punctuation, on needs** (4.3): needs are data, not a list in prose. One need per actor ended with a full stop.
- **ASD-STE100's American spelling** (1.14): the project writes British English, and its ids carry it, as in `ACT-merge-authoriser`.
- **ISO 24495-1's familiar words, in analysis artefacts** (5.3.2): almost every noun there is a project term. A glossary serves instead.
- **ISO 24495-1's "leave out what readers do not need", in analysis artefacts** (5.1.6 d): every cut drops a fact. Side matter moves under *Note* instead.
- **FPLG's one idea per sentence, on needs:** it splits a need in two, against software-analysis DEC-001 point 1.
- **FPLG's positive language, on guards:** "Never ship X without Y" turned into a goal to ship X.
- **FPLG's "address the reader as you":** it does not fit a catalogue of roles.
- **The active voice when the actor is known** (FPLG, "Use active voice", and ASD-STE100 3.6): proposed in `WRITE`'s first draft, then dropped after review. The original was already mostly active, so the trial showed no gain. It showed only the rule's limit: a rewrite made a passive active and named a validator the original never named.

**Not tested:** testing with readers (ISO 24495-1, Principle 4). Neither rewrite did it, so the trial cannot judge it.

## Applied

The proposed rules were then applied twice: to the core actors, and to two reference pages. The limits held, except where the meaning rule kept a sentence as written.

### The core actors

The actors document was rewritten under the rules on its own branch, for PR #1345. A second review then reworded RS-WRITE-002 and RS-WRITE-003, and the document was revised to match. The *After* column counts that revision.

| Metric | Before | After |
|---|---|---|
| Words, needs / body | 918 / 926 | 917 / 881 |
| Average sentence, needs / body (words) | 17.7 / 19.3 | 17.6 / 11.0 |
| Longest sentence, needs / body (words) | 26 / 49 | 25 / 24 |
| Sentences over 25 words, needs / body | 1 / 10 | 0 / 0 |
| Paragraphs or list items over four sentences | 8 of 9 | 0 of 64 |
| Bold labels / list items | 0 / 0 | 37 / 55 |
| Semicolons, body | 4 | 0 |

- **Facts:** a script checked the ids, citations and number of needs against the original. The body lost 45 words to bold labels, which are not counted. A word diff found no fact lost.
- **Body words:** 926 here against the trial's 948, because the trial counted the headings.
- **What the meaning rule held back:** twelve spots, each a question for the author.
  - Two splits would choose a reading. The developer's "whatever tracks the work" may cover the landing too. The merge authoriser's "so" may follow from both clauses.
  - Eight readings, most of them a pronoun's, were left for the author.
  - Two pairs of terms may each name one thing.
- **What it found in the rules:** the examples of RS-WRITE-005 and RS-WRITE-006 broke other rules of the set. Both examples are fixed.

### Two reference pages

The rules were then tried on two reference pages, on the branch `docs/1348-write-tryout`, which is not to be merged.

- **The pages:** the section on `pkit analysis new` in the software-analysis README, and the opening and four commands of the CLI reference's friction section.

| Measure | `pkit analysis new` | Friction section |
|---|---|---|
| Words, prose | 1,368 → 1,457 (+6.5%) | 6,309 → 6,541 (+3.7%) |
| Average sentence, prose (words) | 41.1 → 14.3 | 34.1 → 12.7 |
| Longest sentence, prose (words) | 109 → 33 | 352 → 65 |
| Sentences over 25 words, prose | 23 → 1 | 90 → 3 |
| Paragraphs or list items over four sentences | 1 → 0 | 14 → 0 |
| Semicolons | 15 → 0 | 82 → 0 |

- **Gains:** lists, the sentence limit and the paragraph limit helped most. Table cells read more easily too. The text grew by 6.5% and 3.7%, against 16% in the trial's plain rewrite.
- **Costs:**
  - The key lists of `--json` nested four levels deep.
  - A code span counts as words, so a quoted message filled a sentence alone. The fix added sentences that carry nothing.
  - Splits moved pronouns away from their nouns. Each noun named is a reading that the author must confirm. Twelve other spots stayed as written, for the author.
  - RS-WRITE-002 did not fit. The command sections differ too much for one list of labels.
  - Three slips were caught: two moves broke a pointer each, and an editing tool wrote a bidi control character.
- **What reference pages need:** these exceptions, before the spaces inherit the set:
  - a code span counts as one word
  - command synopses are exempt
  - a fixed form for JSON key references
  - table cells may be fragments that start with their verb
  - labels that other text cites stay stable
  - a limit on how deep lists nest
  - a check for control and bidi characters
