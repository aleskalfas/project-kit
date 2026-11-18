# The next calibration of the graphic-design review: what it fixes before it runs (project-kit#3397)

**Status.** The plan for the next run, mended from the first run's plan (`../2026-11-17/plan.md`) by what that run's diagnosis found. Nothing here has run on a held-out ladder. The ladder the next run grades does not exist yet, so section 1 fixes the form its reference takes, and the plan is committed again with that reference filled in, and its control, before the run. A dry run on the development set comes first (section 6). The plan was brought to the rules the default branch holds once they moved: the communication set at `COMM@2`, and the graphic set at `GRAPHIC@4`, which adds `RS-GRAPHIC-009` and gives the reviewer's body readings of `RS-GRAPHIC-002` and `RS-GRAPHIC-007` for a page drawn in layers.

**What it rests on.** It grades by `COMM@2` and `GRAPHIC@4`, as visual-communication DEC-068 and DEC-069 leave them. It rests on visual-communication DEC-042 as accepted on the default branch:
- its Context, for the four conditions;
- point 1, for the verdict;
- point 3, for the bar;
- point 4, for what the review is handed and the order of its reads;
- point 9, for what a calibration fixes before it runs;
- point 10, for what the hold reaches.

What lapses the hold is DEC-065's, and the comparison of a text's size with its medium is DEC-046 point 8's.

**What it keeps apart.** The calibration grades by the canon alone. The yardstick was neither read nor used for this plan, and nothing here comes from it. The first ladder is now a development set: the first run's diagnosis read it, so a change's effect on it shows fit, not calibration. The next ladder is held out, and must not reach anyone who writes the canon, the reviewer's body or the design knowledge (DEC-042 point 9).

**The run's files.** Each lies in `run/`, and each runs with `uv run --script`, from the repository's root:
- `layout.py` lays out every folder, for the review and the judges alike;
- `review-prompt.md` is the review's prompt;
- `judge-brief.md` is the judges' two prompts;
- `judge.schema.json` is the form of a judge's document;
- `order_check.py` checks the order's methods before one is fixed;
- `analyse.py` computes the control before the run and the readings after it;
- `digests.py` prints the digests the hold is compared on.

`dev/` holds the development set's reference, its digests, its control and its order check, and `judges_as_documents.py`, which writes the first judges' grades as documents.

## 0. What this plan mends

Each fault the first run's diagnosis found (its section 6), and where this plan answers it.

| Fault | What this plan does | Where |
|---|---|---|
| Pipeline 1: `analyse.py` stops on a document that does not parse | Each document's parse and schema errors are caught and named in the head, and the document gives no reading | section 2, "No reading" |
| Pipeline 2 and 3: a missing grade counted two ways, an empty document scored as best | One rule, per page: no reading enters no order, pair, stability or verdict | section 2, "No reading" |
| Pipeline 4: TXF under `out`, designs with no reading in the evidence | TXF under `no-reading`, and one rule for the evidence on every page | section 1; section 3, "The evidence" |
| Pipeline 5: stability lines worded wrongly | Each line names what is stable, what is not, and what has no reading | section 3, condition 3 |
| Pipeline 6: a false claim at the report's head | Every claim about the inputs comes from a check | section 4 |
| Pipeline 7a: the model compared with its effort as free text | The name alone, against the pin; the effort from the dispatcher's record | section 4 |
| Pipeline 7b: the restraint check reads only the kind | Every file each list names, against an allowlist | section 4 |
| Pipeline 8: the light and dark test cannot fire | Dropped | section 3, "Light and dark" |
| Method 1: no control on the references | The conditions computed on each judge's grades before the run; counterparts only where all three agree | section 2, "The control" |
| Method 2: the review and the judges handed different things | One folder per version, the same for both | section 2, "What is handed" |
| Method 3: judged side by side | The judges grade each version alone, then rank | section 2, "The judges" |
| Method 4: the order method never checked on the review's grades | Checked by a script on a spread like the review's, before it is fixed | section 3, condition 1 |
| Method 5: per-rule references on "both judges below" | Only where the judges name the rule's own words | section 2, "The control" |

## 1. The ladder and its reference

The reference is a file, `reference.json`, in the form `dev/reference.json` gives. The plan is committed with it, at a commit dated before the run's folders are laid out. It holds:

- **`piece`**, the piece's name, and **`page-ids`**, its pages' ids in the story's order.
- **`bar`**: what it covers, the grade it asks at least, and the major of each set it covers, in DEC-042 point 3's shape: now `COMM@2` and `GRAPHIC@4`. `analyse.py` and `digests.py` stop where a major is not its set's in the checkout they read, so the rules' words they read are those of the majors the run grades by.
- **`places`**: whether each covered rule is graded on each page, or once on the piece, as its text says (DEC-042 point 1).
- **`runs`**, three, and **`judges`**, `judge-1` and `judge-2`.
- **`model`**: the model the review runs on, by its full name.
- **`order`**: the order's method, as section 3 fixes it.
- **`orders`**: each deck version that shows the pages in another order, with that order.
- **`pages`**: the maintainer's order on each page, best first, and which designs pass, which fail and which have *no reading*, a design he was never asked about on the bar's rules.
- **`decks`**: the same for each deck version, by the piece's verdict.
- **`counterparts`**: on each page and on the deck, the first draft, the last failed, the first passed and the last polished, from the ladder's rounds alone.
- **`weak-deck`**: the design known to be weak, by deck and by page.
- **`pairs`**: each covered rule's pairs, each a base and the variant that changes it in what the rule judges, on a page or on the piece.
- **`reads`**: what the review and the judges may list as read, beside their own folder (section 4).

**The development set's reference** is the first run's, as `../2026-11-17/run/reference.json` gives it, in this form, with the majors a run now grades by, `COMM@2` and `GRAPHIC@4`. The maintainer gave its readings under `COMM@1` and `GRAPHIC@2`. TXF is moved from `out` to `no-reading`, as the first plan's section 0 has it, and nothing else of its reading, lines or pairs changes.

**The bar** of the next ladder is fixed with its reference, against project-kit's bar as the default branch holds it then: now `COMM@2`, and each rule of `GRAPHIC@4` but `RS-GRAPHIC-008`, `RS-GRAPHIC-009` among them. Each rule it covers is tested by a difference the ladder makes in what the rule judges, and a rule whose part the ladder holds fixed leaves the bar (DEC-042 point 9). Its pairs include those of `RS-GRAPHIC-009`, and pairs of `RS-GRAPHIC-002` and `RS-GRAPHIC-007` that vary what DEC-069's readings judge on a page drawn in layers, where the ladder varies them.

### What the development set can test

Each rule project-kit's bar covers, against the first ladder. By the bar's rule above, a rule leaves the development set's bar where the ladder holds a part of it fixed or no pair tests it, so its bar stays the first run's six rules.

| Rule | On the development set |
|---|---|
| `RS-COMM-001` | Leaves: the ladder holds fixed a page with its lead left empty, and a figure's caption as its lead (the first plan's answer 5). |
| `RS-COMM-002` | Leaves: the ladder holds fixed whether a picture alone shows the whole before its parts (answer 5). |
| `RS-COMM-003` | Tested, thinly: one pair, on the piece, `rounds/round-5` → `variants/RS-COMM-003`. |
| `RS-COMM-004` | Leaves: the ladder holds fixed the words in a picture made elsewhere, since it has no screenshot (answer 5). |
| `RS-COMM-005` | Leaves: the ladder holds fixed a fact false against its source, and a picture made elsewhere (answer 5). |
| `RS-GRAPHIC-001` | Tested: page 4, TLG → WDH. |
| `RS-GRAPHIC-002` | Tested on a page drawn in one layer: page 2, ZKD → MLV. |
| `RS-GRAPHIC-003` | Tested: page 1, LTV → KST. |
| `RS-GRAPHIC-004` | Leaves: the ladder holds fixed whether a library's component is used, since it is free SVG (answer 5). |
| `RS-GRAPHIC-005` | Leaves: its one pair, TLG → HGS, changes the amount of text and its size together (answer 6). |
| `RS-GRAPHIC-006` | Tested: page 2, ZKD → PVD. |
| `RS-GRAPHIC-007` | Tested, for an added difference: page 1, LTV → PBV. |
| `RS-GRAPHIC-009` | Leaves: no version varies a leader alone, so no pair tests it. |

- **`RS-GRAPHIC-009` and DEC-069's readings cannot be tested on it.** Page 3 is drawn in layers: its three hand-overs are notes, each tied by a leader to an arrow of the flow. Its designs draw those leaders in more than one way, such as ending in a ring under the arrow (ZCG), stopping short of it (TXF) or crossing it (FXK). But each such design differs from the others in more than its leaders, and the reference holds no reading of any on `RS-GRAPHIC-009`. The pairs of `RS-GRAPHIC-002` and `RS-GRAPHIC-007` lie on pages drawn in one layer, so no pair tests the readings DEC-069 gives them.
- **One reading of the reference rests on a defect the reviewer's body now gives another rule.** The maintainer fails FXK, page 3's last failed, on `RS-GRAPHIC-002`, for hand-over lines that cross the arrows (the first plan's answers to question 2). The reviewer's body now cites `RS-GRAPHIC-009` for a leader that runs on past its thing, and DEC-069 point 5 gives it alone whether a leader can be followed past the lines it meets. The development set's bar does not cover it. The reference keeps his reading, so page 3's clauses on FXK read the review against a reading the body may no longer give.

## 2. How the run reads

### What is handed

`layout.py` lays out one folder for each deck version, for each run of the review and for each judge, under a fresh code of four capital letters. Each file is made once for the version and copied to every folder byte for byte. So the review and the judges are handed the same things, and each key records the digest of every file its folders hold. A folder holds:

- **The images:** each page in its light and its dark mode, the copies the judges rank. A version that has no blind copy takes its own images, resized as the blinding tool resized, once `layout.py` has checked that the resize reproduces a blind copy.
- **`handed.md`:** the piece's audience, where it is shown, that it explains, its pages' ids in this deck's order, and the intent the intent command prints.
- **The piece's content file,** under its own name: each page's words and the visual it asks for, its slides in this deck's order, with no comment. A version whose words differ from the piece's takes its own content file.

Left out, for the review and the judges alike:
- the viewing step's frames and report;
- the brand, the brief's file and the sources of the pages' facts;
- the anchors, the keys, the rankings, the ladder's source and every other version.

So no check has measured any image, and the report says so on every page (DEC-046 point 8).

**Why the content, and no frames.** The first run handed the judges each page's point, structure and content, and the review the images and one goal. 56 lines of the review's notes put a doubt off for want of the content, the frames or the brand. This plan hands both the content, which the reviewer's body has the review read beside each image. The frames and the viewing step's report need the capability's viewing step to have drawn the piece, which a ladder drawn outside the capability does not give, so neither is handed either one.

**Each review** sees one folder alone, in a session that saw no other version and no earlier report, with `review-prompt.md` as its prompt.

### The judges

Each judge works in two parts, with `judge-brief.md`:
1. **Grading alone.** One fresh session for each version, given that version's folder alone, which grades each page on each rule of `COMM` and `GRAPHIC`, and the piece on each rule that judges the pages together. Below *professional*, each grade gives the rule's own words the page breaks. Each rule that takes no grade is listed as not graded, with the passage that leaves it out. The document takes `judge.schema.json`'s form.
2. **Ranking.** Once every version is graded, one session ranks each page's blind copies side by side, without its grades of part 1. The maintainer builds the reference on the rankings, as before.

The control reads part 1 alone. The judges read the rule sets alone, never the reviewer's body, so a reading the body holds, such as DEC-069's of `RS-GRAPHIC-002` and `RS-GRAPHIC-007` on a page drawn in layers, is the review's alone.

### No reading

- **A document gives no reading** on any page, nor on the piece, where it was not kept, does not parse, or its schema refuses it (`review.schema.json` for a review, `judge.schema.json` for a judge). `pkit visual verdict` refuses such a document too.
- **A page has no reading** where its document neither grades nor lists as not graded a covered rule that judges a page.
- **The piece has no reading** where its document does the same for a covered rule that judges the piece, or where one of its pages has none.

A reading that is missing enters no verdict, order, pair, stability or evidence. A clause of a condition that rests on one is not met, and the head counts each by its cause. The coordinator keeps each document as it was given, records one that fails its schema, and dispatches no review again for it.

### The verdict

The verdict on each page and on the piece is the capability's own, by the code `pkit visual verdict` runs. A marked grade is left out of the verdict, as DEC-042 point 4 has it.

### The control, before the run

`analyse.py control` runs on the judges' part-1 documents before the run, and its output, `control.json`, is committed with the plan. `analyse.py run` computes it again and stops where it differs.

- **A counterpart enters** a condition only where the maintainer and both judges put it on the same side of the bar. Where they do not, it is *contested*, and where a judge gives it no reading, it is reported as such. Each is reported apart, and none is replaced by another design.
- **A clause enters** only where its counterparts enter, and each judge, read as the review is read, meets it. A clause a judge fails tests the reference, not the review, so it leaves the conditions, and the control says which.
- **For the bar,** a condition is read on each place where a clause enters, and the control names each place where none does. The maintainer accepts that set of places with the plan, before the run.
- **A rule's pair stands** where both judges grade the base *professional* or above on the rule, and the variant below it, each in its own session. Each grade below *professional* must give at least one passage, and every passage it gives must be the rule's own words. A passage is where it holds at least three words and appears word for word in the rule's heading or text in its set's file. Case, the marks of emphasis and code, curly quotes and the quotes and punctuation around the passage are set aside.
- **A design the maintainer passes** stands for a rule's pass line where neither judge grades it below *professional* on the rule. A judge that lists the rule as not graded on it stands with that.
- **The weak deck** stands for a rule where both judges grade it below *professional* on the rule, each with the rule's own words.

## 3. The four conditions

DEC-042's Context gives them as conditions [project-kit#3151](https://github.com/aleskalfas/project-kit/issues/3151) set before the hold is turned on. Each is read for the bar, on each page and on the deck, and for each covered rule alone, as the first plan's section 2 reads them, with what follows.

### Condition 1, order

- **The clauses:** the first draft below the last failed, the last failed below the first passed, both strict, and the first passed about equal to the last polished, where both meet the bar in either order (the first plan's answer 9).
- **The order from grades** is `counting`, which the maintainer chose for the first plan (its answer 8) and kept for this one, on 2026-11-18, after `order_check.py` had run on the development set (`dev/order-check.md`). A version ranks by how many covered rules it meets at each grade, from the highest. A rule the review leaves ungraded counts in none.
- **How the check reads:**
  - It takes the pairs where one design dominates another in a judge's grades: at least as high on every covered rule, and higher on one. So the pairs favour no method, and the maintainer's order enters nowhere.
  - It maps each judge's grades onto the spread of the review's grades by their rank, ties broken at random, and moves each grade a step at the rate the review's runs disagree.
  - It counts, for each method, the pairs each keeps, ties and inverts, over 500 seeded draws.
- **What the check found.** On the review-like spread, `counting` keeps 59.9% of the pairs, ties 30.4% and inverts 9.7%. `lowest-then-average` keeps 61.8%, `average` 60.1% and `lowest` 51.1%, which ties 42.9%.
- **Why not the check's own rule.** The rule `order_check.py` fixed before it ran, the fewest inverted pairs first, picks `lowest`. But condition 1's clauses are strict, so a tie fails them as an inversion does, and `lowest` keeps the fewest pairs. `counting` keeps nearly as many as the best, and keeping it changes no choice after its result was seen.
- **As evidence, toward no acceptance:** Kendall's tau-b between the review's order and the maintainer's on each page, and the share of his ordered pairs the review keeps in order. One rule on every page: a design with no reading in the reference is left out, and so is a design with no reading in that run, each named.

### Condition 2, the pass line

As the first plan reads it. Also reported, toward no acceptance: the verdict against the reference on every version with a reading, with each false pass and false fail on a contested design marked.

### Condition 3, stability

- **For the bar:** each image with a reading in the reference, in every run and every deck it stands in.
  - *Stable:* every reading is given, and all are the same.
  - *Unstable:* two readings differ.
  - *Not read:* the readings given agree, and one is missing.
- **Each line** says how many of the images are stable, names each stable image with its verdict, and names each unstable or unread image with its verdict in each run, the decks where it differs and the decks where it has no reading. Images with no reading in the reference are named apart.
- **Met** on a place where every image is stable. The deck is read the same way, on each deck version.
- **For a rule alone:** the rule stays on the same side of *professional* on each image in every run and deck, and a missing reading leaves it not met.

### Condition 4, the weak deck fails

As the first plan reads it, on the weak deck's pages and its deck. For a rule alone, on each page where the weak deck stands for it (section 2).

### Light and dark: dropped

The first plan's test that light and dark fall on the same side cannot fire. The review grades each rule once on a page, for both its modes, since a grade's place is a page or the piece (`review.schema.json`). A variant that differs in one mode alone would also be read on the page's one grade, so it is read as that rule's pair, and nothing about the modes is left to test. Grades for each mode would change DEC-042, not a plan. So the test is dropped. A ladder that asks whether the review reads the dark mode varies a covered rule in that mode alone, and the rule's pair reads it. The report shows both modes on every card.

## 4. The head: each claim about the inputs, from a check

The report's head makes no claim about what the run read, handed or was run on that `analyse.py`'s head does not compute. The report's writer copies those lines and words none of its own about them. They are:

- **The documents:** for each run and each judge, how many folders, how many documents were kept and read, and each that gives no reading, with why.
- **No reading, by page and by piece,** counted for each source, with each cause beside a document that was read.
- **The model, by its name alone,** in every document whose front can be read: how many names, whether there is one, and whether it is the one `reference.json` pins. The judges' names are reported apart.
- **The effort,** from the dispatcher's record, `dispatch.json` in each run's folder of reports, which the coordinator writes with the model and the effort it dispatched. A review cannot see its effort, so its document's word is not read.
- **What each document lists as read,** against an allowlist:
  - every file named in the words of every list, before and after grading, is resolved against the document's own folder, its files and the files `reads` names, by its path in the repository's main checkout or in the checkout the analysis runs in;
  - a file that resolves to none is reported with the words that name it;
  - so is a brief's file or an earlier report listed before grading.
  - A document that does not parse is read for its lists up to its grades.
- **The judges' words:** how many grades below *professional* give none.
- **What each folder held** against its key, file by file and byte by byte.
- **Whether each version was handed alike** to every run and every judge, by the digests each key records.
- **The plan's commit:** whether each key's folders were laid out from a commit that holds this plan, dated before they were laid out, with the plan unchanged since and its folder clean.

The allowlist for the review is the capability's rule sets, design knowledge and decisions, the review's schema and its reference instance, the capability's outputs, checks, components and files documents, the core records, and the project's rule sets, which the reviewer's body has it search for a set that inherits one of the capability's. For the judges it is the two rule sets and `judge.schema.json`. Where a session's harness keeps a log of its reads, it is kept beside the report. This plan's check reads the documents' lists alone.

## 5. What else the run fixes before it runs

- **One review for each deck version in each run,** under a fresh code, seeing no other version and no earlier report.
- **The model,** by its full name, in `reference.json`. Its effort is the dispatcher's, recorded in `dispatch.json`.
- **The number of runs,** three.
- **The digests** the hold is compared on: the covered rules' text, the reviewer's definition, the design knowledge, the capability's code and its list of checks (DEC-042 point 9, DEC-065 points 1 and 2). `digests.py` prints them at the commit the run starts from, into `digests.txt` beside this plan, and the development set's into `dev/digests.txt`.
- **The order's method,** and the control's output, `control.json`.
- **This plan, committed** at a commit dated before the run's folders are laid out. `layout.py` refuses to lay out from a plan folder that holds uncommitted changes, and records the commit in every key.

## 6. The dry run, on the development set

Before the next run, the pipeline runs end to end on the first ladder: the layout, the collection, the schema, `analyse.py` and the report. It tunes nothing: no condition, threshold or reference changes to fit what it shows. It grades by `COMM@2` and `GRAPHIC@4`, and `dev/digests.txt` holds the digests at the commit it starts from.

1. **The judges' documents.** The first judges graded side by side, named no words and graded `RS-COMM-003` on two decks alone. `dev/judges_as_documents.py` writes their grades as part-1 documents, changing no grade, so the control can run. Until the judges grade each version alone, no per-rule pair stands on them.
2. **The order check,** `order_check.py`, on those documents and the first run's reviews: `dev/order-check.md`.
3. **The control,** `analyse.py control`: `dev/control.md` and `dev/control.json`.
4. **The layout,** `layout.py`, from this plan as committed, for three runs and two judges. It lies under `.agent-workspace/calibration-dev/` at the repository's root: the folders in `folders/`, the keys in `keys/`, which no review or judge is told to read, and the reports in `reports/`.
5. **The run,** by walled coordinators, each briefed in that folder, who return only counts, retries and failures:
   - three runs of twenty reviews, with `review-prompt.md`, on the model `reference.json` pins;
   - each judge's part 1 with `judge-brief.md`, then its part 2: judge 1 on Fable and judge 2 on Opus, as the first ladder's judges ran.
6. **The control again,** `analyse.py control` on the judges' part-1 documents of step 5, kept as `dev/dry-control.md` and `dev/dry-control.json`, and committed before anyone reads the reviews' reports.
7. **The readings,** `analyse.py run` against that control, and the report from them.

The development set hands every version the scratch piece's content, `../2026-11-17/piece/content.en.yaml`. Its leads differ from what three variants draw: those of RS-COMM-001, -002 and -004, whose decks have no reading in the reference.

## 7. What the report must show

As the first plan's section 3, with these changes:
- **Its head is section 4's,** and nothing else at the head claims anything about the inputs.
- **The conditions' tables** show each clause as entered, contested or with no reading from a judge, and read only those entered.
- **The contested designs,** and those a judge gives no reading, stand in a table of their own, with the maintainer's and each judge's side.
- **Each card** marks no difference between light and dark, since no grade is given for a mode.
- **A version with no reading** shows why, and no grade or verdict for that page.
