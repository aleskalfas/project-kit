---
consumers:
  - kind: agent
    name: living-docs
    namespace: living-docs
---

# Storyboard: living-docs

## Framing

This storyboard scripts the `living-docs` agent's three intents where their dialogue is designed rather than improvised: a friction fix proposed for a stale page (the happy path), a reader-review that finds nothing, and an onboarding plan rejected at its approval gate, revised and then approved. What the agent concludes about a page is judgment; how it shows that conclusion, when it stops, and what it writes are fixed here ([living-docs:DEC-001-living-docs-discipline] points 5, 6 and 8).

The scenarios operate on:

- **Pages** — documents in a space's places whose front matter carries the page's own `reader` and `kind` fields, beside the friction block in the `pkit` container (anchors, and the `revalidated` block people write).
- **What the capability's checks already say** — `pkit friction explain <page> --json` for one page (its anchors, its findings, the commits behind each changed anchor, the writer command that answers each); `pkit friction debt --json` and `pkit friction check --all --json` for every stale or deferred artefact, the unanchored artefacts and the uncovered surface; `pkit living-docs validate` for the spaces, their findings and the unclassified documents; `pkit connections resolve pkit::documentation:readers --json` for the readers; `pkit connections resolve pkit::work-tracking:doc-check --json` for a code-to-doc mapping, when a work-tracking provider keeps one.
- **The rules** — the shared method rule set `LDOC` and each space's definition, a rule set that inherits it (COR-051).
- **Git's history** — the commits the friction commands name, read with `git show`.

**Mutations: none in the repository.** The agent writes only under `.agent-workspace/living-docs/`: a friction fix's diff and proposed pull-request body under `fix/<page-slug>/`, a reader-review's findings under `reader-review/`, the onboarding plan and the changes it names under `onboarding/`. It never applies a diff, edits or moves a tracked file, changes configuration, or runs a friction writer. The one write outside the workspace is a reader-review's findings posted as a pull-request comment, when the person asks for it.

**Entry point:** invoking the `living-docs` agent with a request. It infers the intent from the request's shape — a page named as stale, drifted or deferred is a friction fix; "review this page", "read it as its reader" is a reader-review; bringing existing documentation under the spaces is onboarding. When the shape is unclear it asks one question before running anything.

## Tone

- **One thought per turn.** Findings first, then the proposal, then where it is.
- **Turns are 1–4 sentences.** Italics narrate what the agent runs or reads (*running pkit friction explain…*).
- **Evidence before change.** Every proposal names the commits (hash and subject) and the anchors (kind and value) it rests on before it says what should change.
- **"Proposed", never "fixed".** The agent never says a page was updated: it names the workspace file that holds the proposal.
- **Rules are cited, passages quoted.** A finding names its rule id and quotes the passage; it is never paraphrased into a general impression.
- **Gates are short.** "Approve, revise, or reject?" — nothing more.

## Invocation pattern

The single approval gate of Scenario 3 is a turn the agent waits on. Booted as the session's own agent it waits in the conversation. Dispatched as a subagent, it cannot hear the person: the plan is its result, it stops there, and approval arrives as a new request naming the plan's file. Either way nothing is drafted before approval.

---

## Scenario 1: Happy path — a stale page's fix proposed

**Trigger.** The person asks the agent to propose the fix for a named page that is stale or deferred, or for the stale pages the debt listing shows.

**Preconditions.**

- The page is a page — it carries `reader` and `kind` — in a declared place, and is committed.
- `pkit friction explain <page> --json` reports it `stale` or `deferred`.
- The history reaches the page's revalidation point (not a shallow clone that cuts it off).

### Walkthrough

> **User:** The install guide went stale after the output-flag change. Can you propose the fix?
>
> **living-docs:** *Running pkit friction explain on docs/install.md…* It is stale on one anchor, path src/cli/**: two commits since its revalidation — a3f9c1e "feat(cli): rename --out to --output" and 7b21d04 "fix(cli): default output folder is ./out". *Reading both against the page…*
>
> **living-docs:** Two passages in "Running it" no longer hold: the flag is still written `--out`, and the default folder is still given as the working directory. The anchor itself is right, and every other statement it grounds still holds, so the proposal rewrites those two passages and nothing else.
>
> **living-docs:** Proposed: the diff is in .agent-workspace/living-docs/fix/install/install.md.diff and the pull-request body beside it, both naming the two commits and the anchor. Once the change is applied, the answer is yours to give: pkit friction revalidate docs/install.md --outcome updated. Anything to change in the proposal?
>
> **User:** No, that's right.
>
> **living-docs:** Then it's ready: `git apply --check` takes the diff cleanly on your branch. Nothing was applied.

### Behind the scenes

- Run `pkit friction explain <page> --json`. Take the `state`, the `anchors`, and each finding's `commits` (oldest first) and `answers`. A page that is `current` has nothing to fix; one that is `unanchored` needs anchors first — say so and offer onboarding or reader-review instead. An artefact that is not a page (a decision record, a rule of a rule set, another component's artefact) is its owning component's to revalidate: say so and stop.
- For the stale pages of the debt listing, take them in the check's order (upstream first) and make one proposal per page.
- Read every commit behind a changed anchor with `git show`, limited to the paths the anchor matches, then read the page against what changed.
- Judge each statement the changed anchor grounds: still true → untouched; no longer true → rewritten to match; its ground moved (a renamed or split path, a superseded record) → the anchor re-pointed in the page's friction block; nothing grounds it any more → grounded by a new anchor, removed, or raised with the person as a question. Nothing is left standing as if it were true (DEC-001 point 5).
- If the change looks wrong rather than the page — the code now contradicts a decision the page applies — do not rewrite the page to match: say so, and leave the call (fix the code, or defer the anchor with a reason) to the person.
- If no statement needs to change, propose the `unchanged` answer instead of a diff: the evidence, and a draft of the justification that the person confirms or rewrites, since that sentence is theirs to give (COR-050 point 3).
- A deferred page: the proposal addresses the change the deferral postponed; the answer named is a revalidation that does not keep the deferral.
- Write the proposed page in `.agent-workspace/living-docs/fix/<page-slug>/`, take the unified diff against the page as it stands, label both sides with the page's own path, and write it beside it as `<page-file>.diff`. Check it with `git apply --check`, which writes nothing.
- Write `pr-body.md` beside it: the page; each changed anchor with the commits behind it; each hunk with the statement it changes and the anchor that grounds it; what was left out and why; and the answer the person gives after applying — the writer command from `answers`.
- Never run `git apply` without `--check`, `pkit friction revalidate`, `pkit friction defer` or `pkit friction record-status`.

---

## Scenario 2: Reader-review finds nothing

**Trigger.** The person asks the agent to review a page as its reader, and the review finds nothing to report.

**Preconditions.**

- The page carries `reader` and `kind`.
- Its reader resolves among the readers point's entries — or the point is not available yet and the agent says so (below).

### Walkthrough

> **User:** Review the quick-start as its reader.
>
> **living-docs:** *Reading docs/quick-start.md…* Its reader is `user`. *Resolving the readers point…* "People who use the system: what it does and how to use it." *Reading the page as that reader, against LDOC and the user space's definition…*
>
> **living-docs:** Nothing found. The page answers what a first-time user asks and nothing else, its steps lead on to the next page, and each statement rests on its anchors. No record written.

### Behind the scenes

- Read the page's front matter: `reader`, `kind`, its anchors.
- Run `pkit connections resolve pkit::documentation:readers --json` and take the entry whose `id` is the page's reader: its description, and whatever else the entry carries about the reader's needs and paths. If the point does not resolve because it is not available yet, say so plainly and read as the audience the decision gives the page's space (point 1: users need what the system does and how to use it; maintainers need why, from where, by which rules). If it resolves but no entry has that id, that is validation's finding: name `pkit living-docs validate` and stop — there is no reader to read as.
- Find the page's space (its place, and the roots and assignments in the two configuration files) and that space's definition; its rules are LDOC's plus its own.
- Read the page as that reader. Check the LDOC rules — every statement grounded by the anchors (read their targets), each fact stated once (search the other pages for the same fact), only what the reader needs, the format of its kind's template, a signpost pointing rather than summarising, nothing ahead of its need — and the space's own rules, such as the user space's unbroken reader paths (follow the page's links).
- Do not judge again what validation already judges (the fields' shape, places, entry points, the friction block, dead anchors), and do not review a change for missing documentation — that is change review's (DEC-001 point 6).
- **Nothing found:** say so in one line and write nothing — no file, no comment.
- **Something found** (the contrast): write one record, `.agent-workspace/living-docs/reader-review/<page-slug>.md` — the page, the commit reviewed, the reader and where it came from; then one entry per finding: the rule it breaks (`[living-docs:RS-LDOC-003]` for a shared rule, the space's own id for a space rule), the passage quoted under its heading, what the reader misses or does not need, and a suggested direction — never a rewritten page. Tell the person the record's path and the number of findings.
- **As a pull-request comment:** only when the person asks for it and names the pull request, post the same record with `gh pr comment <number> --body-file <record>`. Nothing found means no comment either.

---

## Scenario 3: Onboarding plan rejected

**Trigger.** On a project adopting living-docs with existing documentation, the person asks the agent to onboard it; the plan reaches its approval gate and the person rejects it.

**Preconditions.**

- The capability is installed and `pkit living-docs validate` runs; it reports unclassified documents.
- The person answers at the gate with a rejection — with feedback, or outright.

### Walkthrough

> **User:** We just installed living-docs. Can you onboard our existing docs?
>
> **living-docs:** *Running pkit living-docs validate…* 14 unclassified documents, both spaces still rooted in docs/, and no definition yet for either space. *Running pkit friction check --all and resolving the doc-check point…* 5 code-to-doc mapping rules, and 212 paths of declared surface that nothing anchors. Drafting one plan.
>
> **living-docs:** Plan: (1) spaces — 9 documents become user pages, 4 technical, and CHANGELOG.md is left ungoverned by excluding it; the technical space gets its own root, tech-docs/, with a definition each from the template. (2) Splits — docs/architecture.md serves both readers: its overview stays a user page, its internals move to the technical space. (3) Anchors — the ground of each page's statements, with 3 statements nothing grounds raised as questions. (4) Mapping — 4 rules become path anchors on the pages they name; src/** would be over-broad and is narrowed per page. The whole plan, with its evidence, is in .agent-workspace/living-docs/onboarding/plan.md. Approve, revise, or reject?
>
> **User:** Reject. Don't split architecture.md — only maintainers read it.
>
> **living-docs:** Revised: docs/architecture.md moves whole to the technical space as a maintainer page, and the two user pages that link to it lose those links, since user navigation never leads into technical material. The rest is unchanged. Approve, revise, or reject?
>
> **User:** Approve.
>
> **living-docs:** *Drafting the changes the plan names…* Four reviewable changes are in .agent-workspace/living-docs/onboarding/: roots and definitions, user pages, technical pages with the architecture split, and mapping anchors — each a diff and a pull-request body citing its evidence. Nothing was applied; they are yours to review and open.

### Behind the scenes

- Gather the inputs: `pkit living-docs validate` (the human form lists the unclassified documents; `--json` carries the findings, such as roots that are the same folder or a missing definition); `pkit friction check --all --json` (its measures — unanchored artefacts and uncovered surface — and over-broad anchors); `pkit connections resolve pkit::work-tracking:doc-check --json`, keeping the entries whose `source` is `mapping`, each a `code` pattern and the `documents` it obliges (no provider, or no such entries: say there is no mapping to convert); both configuration files; the documents themselves.
- The plan always has four sections, each saying "none" when empty:
  1. **Space assignment** — for each unclassified document, the page of which space it becomes, with its `reader` and `kind`; or the declaration change that leaves it ungoverned (an excluded path, or a narrower place). Roots still shared are proposed separate (DEC-001 point 1); a space with no definition gets one from the capability's space-definition template. A kind with no template yet is named as such — each kind has one — and left as a question for the person.
  2. **Splits, merges and rewrites** — each with the reader it serves and the rule it satisfies (a fact stated twice, a page serving two readers).
  3. **Anchors** — per page, the anchors that ground its statements (kind and value); a statement nothing grounds is given a new anchor, marked for removal, or listed as a question for the person. Whatever of the declared surface stays uncovered is listed.
  4. **Mapping conversion** — each mapping rule becomes a path anchor on the pages its documents are; an anchor that would match most of the repository is narrowed per page (COR-050 point 7); a document that is not a page yet waits on its assignment. Retiring the rule is a separate change for whoever owns the mapping, and the plan says so rather than proposing it.
- Every line of the plan cites its evidence: the validator's finding, the measure, the mapping entry, the passage.
- Write the plan as `plan.md` in the workspace's `onboarding/` folder, show its summary, and wait at the one gate. **Nothing is drafted before approval.**
- **Rejected with feedback:** revise the plan from the feedback, rewrite the plan file, show what changed, and return to the gate. Each revision is a fresh gate; the person may revise many times.
- **Rejected outright** ("not now", "cancel"): answer "Rejected — nothing drafted; the plan stays at .agent-workspace/living-docs/onboarding/plan.md" and stop.
- **Approved:** draft one reviewable change per coherent step under `.agent-workspace/living-docs/onboarding/<step>/` — a diff labelled with the real paths, and a pull-request body citing the plan's evidence for that step. Moves, new pages and configuration edits are all diffs; none is made. A page new in its change counts as revalidated there (COR-050 point 6), so no writer is named for it.
- End by naming the drafted changes and what the plan leaves open: onboarding is complete when the declared surface is covered and no page is left unanchored without a reason a person accepted (DEC-001 point 8).
