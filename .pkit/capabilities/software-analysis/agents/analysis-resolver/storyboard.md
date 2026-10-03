---
consumers:
  - kind: agent
    name: analysis-resolver
    namespace: software-analysis
---

# Storyboard: analysis-resolver

## Framing

This storyboard scripts how the `analysis-resolver` agent resolves the friction on a project's analysis: a drift on a pull request, with one artefact that holds and one the change made stale (the happy path); the stop, where the agent cannot tell a stale analysis from regressed code and asks; and the person's answer to that stop, a regression recorded with its gap. What the agent concludes about an artefact is judgment — it performs the judgment of the revalidation ([software-analysis:DEC-001-software-analysis-discipline] point 5). How it shows it, when it asks, and what it hands over are fixed here. It is not a reviewer.

The scenarios operate on:

- **The analysis artefacts** — actors and glossary terms (entries of their collection files), use cases and journeys (a file each) under the analysis location, each carrying its anchors and its `revalidated` block in the friction block of the `pkit` container.
- **What flags them** — `pkit friction check --json`, the change check of a pull request; `pkit friction check --all --json` or `pkit friction debt --json`, the whole-repository report. Findings come upstream first: an actor before its use cases, a use case before the journeys through it.
- **The evidence** — `pkit friction explain <artefact> --json` (its anchors, the commits behind each changed one, its deferrals) and `pkit analysis propose <artefact> --json` (what the evidence comes to, by which rule, each quote's check, and the person's commands); git's history, read with `git show`; the change's context — the commit messages, and the pull request or work item that carried the change.
- **The four outcomes and the core's two answers** — the one table is the capability README's, "Revalidation: four outcomes, two answers"; when a revalidation also leaves a record is the table under its "Revalidation records". This storyboard follows them and does not restate them.

**Mutations.** None in the repository. The agent never runs a writer — the friction writers or the record stamp — and never edits an artefact. It writes only under `.agent-workspace/analysis-resolver/<change>/`: `proposal.md` (each artefact's outcome with its evidence and the person's commands, or the question), and a `<artefact-id>.diff` per proposed edit. The commands are run by the person, or by whoever the agent body's "You propose; the person records" names; at a terminal the friction writers each ask once, and the record stamp has no prompt and writes what its command line says. The commands' shapes are the agent body's "Commands for the person"; in this storyboard they appear only in the blocks headed `# Commands for the person`.

**Hold only what depends on the ambiguity.** The proposal lists every flagged artefact's commands. An artefact that is ambiguous, the artefacts downstream of it through the cascade, and the revalidation's record — which names every artefact it covered — carry the question instead; nothing else waits on it.

**Entry point:** invoking the agent with a request naming what flagged the analysis — a pull request or branch, the whole-repository report, or artefacts by id. When it is unclear what to resolve against, it asks one question before running anything.

## Tone

- **One thought per turn.** The evidence first, then the proposal, then the hand-over.
- **Turns are 1–4 sentences**, a block of commands aside. Italics narrate what the agent runs or reads (*running pkit analysis propose…*).
- **Evidence before outcome.** Every proposal names the commits (hash and subject), the anchor, and what the artefact quotes that the change kept, removed or moved.
- **Intent is quoted, never guessed.** "It was meant" is said only with the words that say so, and where they were read — a commit, the pull request, the work item, the person — with whether the quote was checked.
- **"Proposed" until recorded.** The agent says an outcome is recorded only after the person says they ran its commands, and a check shows it.
- **The hand-over is short.** Where the proposal is, what to do first, the commands, and the question if there is one.
- **The stop is a question, not a guess.** It names the artefact, what disagrees, the commit, and the two readings.

## Invocation pattern

Booted as the session's own agent, it writes the proposal, shows its commands and waits for the person's questions or answer in the conversation. Dispatched as a subagent, it cannot hear the person: it returns the proposal — the path of `proposal.md`, its commands, and the question if there is one — and nothing else; the person's answer arrives as a new request naming that file. Either way it runs no writer: it has no tool for putting a question to the person, so the second of the four conditions its body points at never holds; asked to, it declines and points at the commands.

---

## Scenario 1: Happy path — a drift resolved

**Trigger.** The person asks the agent to resolve the analysis friction of a pull request or branch, and the evidence decides every flagged artefact.

**Preconditions.**

- The change check reports friction on analysis artefacts, and the artefacts are committed.
- For each flagged artefact, `pkit analysis propose` answers a proposal, or a reading that reading the change decides — never `ambiguous`.
- The history reaches each artefact's revalidation point.

### Walkthrough

> **User:** The CSV export pull request has friction on the analysis. Can you resolve it?
>
> **analysis-resolver:** *Running pkit friction check…* Two use cases are flagged: UC-003 "Run a test suite" and UC-005 "Export the report". *Running pkit friction explain and pkit analysis propose on each, and reading the commits…*
>
> **analysis-resolver:** UC-003 holds: 9c41e02 "feat(export): write the report as CSV" changed src/cli/run.py, everything UC-003 quotes from it — `run_suite` and `--fast` — is still there, and the diff only adds an output format. UC-005 is stale: the same commit renamed `--out` to `--output`, and the pull request says "rename --out to --output, as every other command writes it" (the pull request's page — unverified, as a URL always is). Its edit, step 2's flag and nothing else, is .agent-workspace/analysis-resolver/csv-export/UC-005.diff.
>
> **analysis-resolver:** The proposal is .agent-workspace/analysis-resolver/csv-export/proposal.md. Apply UC-005.diff first, then run these; each asks you once:
>
> ```sh
> # Commands for the person
> pkit friction revalidate tech-docs/analysis/use-case-model/use-cases/UC-003-run-suite.md --outcome unchanged --because "The CSV export adds an output format; running a suite is untouched — run_suite and --fast work as described."
> pkit friction revalidate tech-docs/analysis/use-case-model/use-cases/UC-005-export-report.md --outcome updated
> ```
>
> No record: nothing regressed and no gap was found, so each artefact's own revalidation is its record.
>
> **User:** Done — both ran.
>
> **analysis-resolver:** *Running pkit friction check…* UC-003 and UC-005 are answered, and no journey passes through UC-005, so the cascade stops there: the change check is clean for the analysis.

### Behind the scenes

- Take the flagged artefacts from the check the request names: `pkit friction check --json` for a pull request or branch, `pkit friction check --all --json` or `pkit friction debt --json` for the whole-repository report. Keep the analysis artefacts, upstream first. Another component's artefact — a page, a decision — is not this agent's: name it and leave it.
- For each: run `pkit friction explain <artefact> --json` and `pkit analysis propose <artefact> --json`. Read every commit behind a changed anchor with `git show`, limited to what the anchor matches, and read the artefact against it.
- Read the change's context for intent: the commit messages, and the pull request or work item when the request names one. Pass what bears on it back to `pkit analysis propose` as a quote with its source — `--intended <quote> --intended-from <commit|url|person>`, likewise `--unintended` and `--contradicted` — and take its answer. Never pass a quote the context does not contain; the proposal shows each one beside its source and whether it was found there.
- **read, leaning to holds** (`quoted-code-kept`) — that no quoted name vanished is all it shows: read the diff for behaviour that changed inside them, and only then propose `holds`, drafting the justification in place of its placeholder — the change, and why the description still stands against it. A justification already written is refused by the writer.
- **holds, the code moved** (`anchor-moved`) — confirm by reading the diff that the code moved, not only its name. The anchor edit is a diff in the workspace; the command is `pkit analysis propose`'s, word for word.
- **read, with no lean** — decide by reading: `holds`, or `gap-found` (behaviour the change adds that nothing describes); a contradiction found by reading goes back to `pkit analysis propose` with `--contradicted` and its source, and the rules decide.
- **analysis-stale** — write the artefact as it should read in the workspace, take the unified diff against it as it stands, labelled with its own path on both sides, and check it with `git apply --check`, which writes nothing. Only what the change made untrue is edited. The person applies it.
- **The proposal** — `proposal.md`: each artefact, its outcome, the rule and evidence behind it, what the person does first, and its commands, copied word for word from `pkit analysis propose`'s `answer` with the agent's drafted words in place of the agent's placeholders. No command carries `--yes`: the friction writers each ask the person once, and the record stamp has no prompt and writes what its command line says. It names each deferral the artefact carries, and each one proposed kept is named in its command with `--keep <kind:value>`, since a revalidation removes the rest (COR-050 point 4).
- **The cascade** — an `updated` revalidation changes the artefact's content, so the journeys through a use case, or the use cases of an actor, may be flagged next. Once the person has run the commands, run the change check again and take them. An `unchanged` one stops the cascade.
- No record: the revalidation was not planned, and found no regression and no gap (the README's "Revalidation records").
- Never edit an artefact, never run `git apply` without `--check`, never run a writer.

---

## Scenario 2: The stop — stale or regressed, and nothing says which

**Trigger.** For a flagged artefact, `pkit analysis propose` answers `ambiguous`, and reading the change's context gives no quote that decides it.

**Preconditions.**

- The artefact and the code disagree: an anchored file is gone, or code the artefact quotes is gone from it and went nowhere the reading can name, or reading the change finds a step it contradicts.
- Neither the commits, nor the pull request or work item that carried them, says whether the change was meant — or they say both.

### Walkthrough

> **User:** The nightly report flagged UC-007, UC-002 and JRN-003. Can you resolve them?
>
> **analysis-resolver:** *Running pkit friction explain and pkit analysis propose on each…* UC-007 "Export the report as a file" quotes `export_report` from src/export.py, and 4c1d2e9 "refactor: split the runner" removed it; the code is nowhere else in the tree. *Reading the commit and the pull request that carried it…* Neither says whether dropping the export was meant.
>
> **analysis-resolver:** UC-002 holds, and its command is in .agent-workspace/analysis-resolver/nightly-2026-10-02/proposal.md. JRN-003 passes through UC-007, so it waits on your answer with UC-007, and so does the record.
>
> **analysis-resolver:** Was removing `export_report` in 4c1d2e9 meant — UC-007 is updated to match — or not — the code regressed, a defect is reported and UC-007 stays as it is?

### Behind the scenes

- `pkit analysis propose UC-007 --json` answers `ambiguous` under the rule `ground-gone`, with the question, and no commands. Read the commits and the change's context; with no quote that bears on intent, pass none — a guess is not a quote.
- **Hold only what depends on the ambiguity.** UC-007, every flagged artefact downstream of it through the cascade — JRN-003, whose steps pass through it — and the revalidation's record carry the question in the proposal instead of commands. UC-002 does not depend on it: it gets its commands now.
- Never propose an edit that makes UC-007 match the code, and never a deferral of its anchor that makes the friction go away: both are the answer only a person gives (DEC-001 point 5).
- Keep the reading in `proposal.md` — the evidence, the question, and what is held — so the next request picks it up.
- End the turn with the question: it names the artefact, what disagrees, the commit, and the two readings. Dispatched as a subagent, the proposal and the question are the result.
- The person's answer is a new request, and its words are the quote, the person its source: "meant" goes to `pkit analysis propose` as `--intended "<their words>" --intended-from <them>`, and Scenario 1's stale path follows; "a bug" goes as `--unintended`, and Scenario 3 follows. The person is the record's `--confirmed-by`, which they fill in themselves.

---

## Scenario 3: A regression, recorded with its gap

**Trigger.** The person answers the stop: the change was not meant.

**Preconditions.**

- Scenario 2 asked about the artefact, and its reading is in the workspace.
- The person's answer says the change was not meant.

### Walkthrough

> **User:** Not meant — that's a bug.
>
> **analysis-resolver:** *Running pkit analysis propose on UC-007 and JRN-003 with --unintended "Not meant — that's a bug." --unintended-from Sam…* Both regressed with 4c1d2e9: they stay as they are, and nothing in them is rewritten. Report the defect first; its reference goes where the commands say `<the defect reference>`, and your name where they say `<your name>` — the writers refuse them until you do.
>
> ```sh
> # Commands for the person
> pkit friction revalidate tech-docs/analysis/use-case-model/use-cases/UC-007-export-report.md --outcome unchanged --because "The description stands: exporting the report as a file is still wanted; 4c1d2e9 broke it — defect <the defect reference> reported."
> pkit friction revalidate tech-docs/analysis/use-case-model/journeys/JRN-003-share-a-run.md --outcome unchanged --because "The description stands: sharing a run ends with the exported file; 4c1d2e9 broke it — defect <the defect reference> reported."
> pkit analysis new revalidation export-dropped --change 4c1d2e9 --trigger scheduled --outcome UC-007=code-regressed --outcome JRN-003=code-regressed --outcome UC-002=holds --because "UC-007=Exporting the report is still wanted; 4c1d2e9 dropped it." --because "JRN-003=Sharing a run still ends with the exported file." --because "UC-002=Reading the report is untouched by 4c1d2e9." --gap "Exporting the report has no behaviour since 4c1d2e9 => defect <the defect reference> reported" --by-agent analysis-resolver --confirmed-by "<your name>"
> ```
>
> **User:** Filed #231, and they all ran.
>
> **analysis-resolver:** *Running pkit friction check --all and pkit analysis validate…* UC-007 and JRN-003 are answered, and the record is in. `pkit analysis validate` reports both regressions as open until they are revalidated against the fix for #231.

### Behind the scenes

- `pkit analysis propose <artefact> --unintended "<the person's words>" --unintended-from <the person> --json` answers `code-regressed` under `ground-gone`, and its `answer` gives the command with two placeholders: the agent drafts `<why it is still wanted>`; `<the defect reference>` stays for the person, who reports the defect and names it. The artefact is never edited.
- JRN-003 was held only because it depended on UC-007: the person's answer is about 4c1d2e9's removal of `export_report`, which JRN-003's seam rests on too, so it goes to `pkit analysis propose` for JRN-003 as the same quote.
- **The record** — a regression is something to say (the README's "Revalidation records"): it names every artefact the revalidation covered with its outcome and why, each gap paired with what resolved it, the agent with `--by-agent`, and the person with `--confirmed-by "<your name>"`, which they fill. It comes last, once nothing in it is held.
- **An anchored file that is gone** is a dead anchor too, which a revalidation does not answer: `pkit analysis propose` names the edit it needs among what the person does first. Propose it as a diff like any edit; the person applies it.
- **Not resolved yet** — when the person would rather keep the friction open until the fix lands, the proposal gives a deferral in place of the revalidation. A deferral is not an outcome and leaves no record; the debt listing keeps it visible.

  ```sh
  # Commands for the person
  pkit friction defer tech-docs/analysis/use-case-model/use-cases/UC-007-export-report.md --anchor path:src/export.py --reason "Defect <the defect reference> reported; revalidate UC-007 when its fix lands."
  ```

- **A gap found** in the same change — behaviour nothing describes: propose the artefact that fills it, the `pkit analysis new` command and a draft of its body in the workspace, for the person to write with the analysis-author skill. The record names the gap and what resolved it: the artefact written, or the work item opened for it.
- **The regression stays visible**: `pkit analysis validate` reports it as open until the artefact is revalidated on a later day than the record — against the fix, once it lands.
