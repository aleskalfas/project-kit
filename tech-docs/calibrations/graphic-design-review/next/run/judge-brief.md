# The outside judges' brief

Each outside judge works in two parts, in this order, and each part's sessions are given the prompt below for that part and nothing else. A judge is a fresh session each time, so no session sees what another wrote.

1. **Grading alone.** One session for each deck version, given the folder `layout.py` laid out for it under `judge-<n>/<CODE>/`. That folder holds the same files, byte for byte, as each review's folder for the version (`review-prompt.md`). The session sees no other version.
2. **Ranking.** Once every version is graded, one session for each judge, given the blind copies side by side. It is not handed the grades of part 1.

In each prompt, `<FOLDER>` is replaced by the folder's path, `<CODE>` by its code, `<N>` by the number of pages, `<JUDGE>` by `judge-1` or `judge-2`, `<RULE-SETS>` by the path of the capability's `rule-sets/` folder, `<SCHEMA>` by the path of `judge.schema.json`, and `<BLIND>` by the path of the blind copies. No other word changes between sessions.

`analyse.py` reads part 1 alone. A coordinator keeps each session's reply as `judge-<n>/<CODE>.md`, as it was given, and edits none. Part 2's rankings are what the maintainer builds the reference on, as before.

## Part 1: grade one version alone

---

You are a senior designer, outside the tool that drew these pages, asked to grade one design of a deck by the rules below, at the standard of professional presentation design. Your grades are checked against other graders', so judge what you see, by the rules' own words.

What you may read:
- The files in `<FOLDER>`: `page-1.light.png` to `page-<N>.light.png` and their dark modes, `page-<n>.dark.png`; `handed.md`, who the piece is for, where it is shown, its pages' ids in order and the intent it was made for; and the piece's content file, which `handed.md` names.
- The two rule sets: `<RULE-SETS>/comm.md` and `<RULE-SETS>/graphic.md`.
- The form of your reply: `<SCHEMA>`.

Read nothing else: no other folder, no other version, no file named `key`, and nothing else under `.agent-workspace/`.

How to grade:
1. Read each rule from its set's file, not from memory.
2. For each page, grade each rule of `COMM` and `GRAPHIC` that judges a page, in words: *below competent*, *competent*, *professional* or *excellent*. Grade once for the piece as a whole each rule that judges the pages together, such as `RS-COMM-003`.
3. Under each grade, say in `evidence` what on the page decides it.
4. For each grade below *professional*, give in `words` each passage of the rule's text that the page breaks, copied word for word from its set's file. Give no passage of another rule, and no words of your own there.
5. Where a rule takes no grade on a page, or for the piece, list it under `not-graded`, with the passage of its text that leaves it out.
6. Grade the design on its own. Do not grade on a curve, and do not guess what other designs exist.

Your reply: one fenced YAML block in the form `<SCHEMA>` gives, and nothing before it. It names `judge: <JUDGE>`, `folder: <CODE>`, your model by its full name, and under `read` what you read, by kind and by path. Each grade names its page by the id `handed.md` gives it.

---

## Part 2: rank the versions side by side

---

You are a senior designer, outside the tool that drew these pages, asked to rank designs of a deck blind, by the rules below. Your ranking becomes the reference another grader is checked against, so judge what you see, by the rules, at the standard of professional presentation design.

What you may read:
- The images under `<BLIND>`: `page-<n>/light/<CODE>.png`, the same design's dark mode at `page-<n>/dark/<CODE>.png`, and the deck-order strips in `deck-order/`.
- The two rule sets: `<RULE-SETS>/comm.md` and `<RULE-SETS>/graphic.md`.

Read nothing else: no other file under `.agent-workspace/`, no worktree, no file named `key`, and no grade written before. The codes are random; nothing about a design is told by its code or its order in a folder.

How to judge:
1. For each page, look at every candidate in light mode. Then look at the dark mode of the three you rank highest, and of any whose light mode leaves you unsure.
2. For each candidate, give an overall grade in words, *below competent*, *competent*, *professional* or *excellent*, and one or two lines on what decides it.
3. **Rank** the page's candidates from best to worst. Ties are allowed; mark them.
4. **The deck's order:** where strips show the same pages in different orders, say which order tells the story better.
5. **Your pass line:** say, in one sentence per page, where on your ranking a page stops being one you would let a client present.

Your reply, in this shape, and nothing before it:

```
# Outside judge

## Page <n>
| Rank | Code | Overall | Why |
|---|---|---|---|
...
### Pass line
<one sentence>

## Deck order
...
```

---
