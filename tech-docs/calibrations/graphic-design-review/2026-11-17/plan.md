# The first held-out calibration of the graphic-design review: what it fixes before it runs (project-kit#3230)

**Status.** The plan for the run, with every question the maintainer was asked answered on 16 and 17 November. Nothing here has run. It is committed at a commit dated before the first run (#3230, first criterion). Read again on 17 November against `origin/main` at b8a4e111d, after #3325, #3328 (which took in #3334) and #3296 landed. The check of a text's size (#3185) has not landed, and the run does not wait for it: a check that lands after the calibration lapses its hold (visual-communication DEC-065 point 3). The maintainer started the run on 17 November.

**What it rests on.** It rests on visual-communication DEC-042 as accepted on `origin/main` (2026-11-14):
- its Context, for the four conditions and the first calibration's account
- point 3, for the bar
- point 9, for what a calibration fixes before it runs
- point 10, for what the hold reaches

The rules are read as the capability ships them once the issues in `blockers.md` land. That is `COMM` 1.0.0, and `GRAPHIC` at major 2, which #3325 landed. This plan is read again against that text before the first run.

**What it keeps apart.** The calibration grades by the canon alone. The yardstick was neither read nor used for this plan, and nothing here comes from it. This plan read the ladder, so it must not reach anyone who writes the canon, the reviewer's body or the design knowledge (DEC-042 point 9, a held-out ladder). The ladder is a board-game platform's deck, not the pkit deck.

## 0. The ladder and its reference

The calibration grades 20 versions of one deck against the maintainer's ranking, read on the six rules its bar covers.

- **The bar:** `{covers: [RS-COMM-003@1, RS-GRAPHIC-001@2, RS-GRAPHIC-002@2, RS-GRAPHIC-003@2, RS-GRAPHIC-006@2, RS-GRAPHIC-007@2], at-least: professional}`. `GRAPHIC`'s major is the one #3325 sets, 2 once it is accepted (answer 4). A page meets the bar where each of its unmarked grades on a covered rule is professional or above. The piece meets it where every page does, and each unmarked grade it takes as a whole does (DEC-042 point 1).
- **Rules left out of the bar:** each leaves under DEC-042 point 9.
  - RS-COMM-001, -002, -004 and -005, and RS-GRAPHIC-004: the ladder holds a part of each fixed (answer 5).
  - RS-GRAPHIC-005: its pair changes amount and size together, and #3345 tests it (answer 6).
  - RS-GRAPHIC-008: no version varies running text alone, and the next calibration tests it (answer 4).
- **The ladder:** 20 versions of one four-page deck, each a whole deck. The source lies in this checkout's `.agent-workspace/ladder/`, with its `manifest.md`. It was copied from the `w3245` worktree, and `ladder-digests.txt` holds every file's digest (answer 20).
  - Five rounds: `r1`, the first draft, to `r5`, the second polish.
  - Three sets. `main` is the capability's own drawing as main draws it, and stands for the weak deck. `grey` draws grey boxes. `form` draws each page in another structure's form.
  - Twelve variants, each `r5` changed on one page in what one rule judges.
  - Five anchors are real slides of other content, and the run leaves them out (answer 18).
  - Blind copies, one code per distinct image, lie under `.agent-workspace/ladder-judge/blind/`.
- **The reference:** the maintainer's ranking (`maintainer-ranking.md`, `your-order.json`), built on two outside judges' blind rankings. Judge 1 ran on Fable (`judge-1-fable.md`). Judge 2 ran on Opus (`judge-2-opus.md`), and its first run, on Sonnet, is kept for the record (`judge-2-sonnet.md`). Each holds the judge's overall grade and per-rule grades.
- **The reference for the bar:** his reading on the bar's rules, not his pass line as a whole. A design he fails only on a rule outside the bar is one the verdict must pass (answers-q5.md, "the reference for the bar").

The maintainer's order on each page, best first. **Bold** is a design that meets the bar on its rules by his reading. Everything below it on that page fails, apart from the designs marked *no reading*.

| Rank | Page 1, an order of levels | Page 2, a mapping | Page 3, a flow | Page 4, a session and code |
|---|---|---|---|---|
| 1 | **LTV** r5 | **ZKD** r5 | **ZCG** r5 | **TLG** r5 |
| 2 | **GPM** r4 | **MNH** r4 | **RTJ** var GRAPHIC-004 | **WMG** r4 |
| 3 | VNH r2 = r3 | **BRS** r2 = r3 | TXF r3, *no reading* | MCM r2 = r3 |
| 4 | PBV var GRAPHIC-007 | BBR var COMM-001, *no reading* | FXK r4 | WDH var GRAPHIC-001 |
| 5 | TXV var COMM-002, *no reading* | PVD var GRAPHIC-006 | CKM r2 | WDB var COMM-005, *no reading* |
| 6 | RWC form | HLW main | HMC r1 | FTW main |
| 7 | GZD grey | LMZ r1 | WBW main | NKR r1 |
| 8 | MPS main | TDF grey | MZK var COMM-004, *no reading* | ZWT grey |
| 9 | KST var GRAPHIC-003 | TNZ form | VFF grey | HGS var GRAPHIC-005, *no reading* |
| 10 | XGX r1 | MLV var GRAPHIC-002 | XPD form | VVL form |
| 11 | SST = DPR anchors, left out | SZP anchor, left out | RCJ anchor, left out | VJV anchor, left out |

- **Why each pass line sits where it does.** His answers to questions 1 and 2 moved the lines, read on the bar's rules.
  - VNH fails RS-GRAPHIC-001 (question 1, row 5).
  - LTV and GPM fail only RS-COMM-004 for the "your scene" tag, which is off the bar (rows 8 and 9, read again on 17 November).
  - BRS fails only RS-GRAPHIC-005, and RTJ only RS-GRAPHIC-004, both off the bar (rows 6 and 4).
  - MCM fails RS-GRAPHIC-007 and -004, FXK fails RS-GRAPHIC-002, and CKM fails RS-GRAPHIC-007 (question 2).
- **No reading.** TXF fails only on the layering rule, which no bar covers yet, so it leaves the reading (question 2). Nor do the variants of RS-COMM-001, -002, -004 and -005 and RS-GRAPHIC-005: BBR, TXV, MZK, WDB and HGS. He failed each by its own rule, and was never asked whether it also breaks a rule of the bar. These are reported and enter no condition.
- **The deck's order.** Strip A is `r5`'s order. Strip B is the RS-COMM-003 variant: pages 1, 4, 2, 3, with only the footers' numbers changed. The maintainer confirmed that A tells the story in order and B does not (question 3). Judge 1 grades RS-COMM-003 *professional* on A and *below competent* on B. Judge 2 grades it *excellent* on A and *competent* on B.
- **The same image in several versions.** Each variant leaves three pages as `r5` draws them. So `r5`'s page image stands in 9 decks on pages 1, 2 and 4 (LTV, ZKD, TLG), and in 10 on page 3 (ZCG). Rounds 2 and 3 are one image on pages 1, 2 and 4 (VNH, BRS, MCM).
- **The decks, by the pass lines.** A deck passes where every page does. Only `r5` and the RS-GRAPHIC-004 deck pass.
  - `r1` to `r4` fail. `r4` fails on page 3 alone, for FXK.
  - Every set fails.
  - Each variant deck of a covered rule fails on its changed page.
  - The RS-COMM-003 deck fails on RS-COMM-003, the piece's own rule.
  - The RS-GRAPHIC-004 deck passes, since RTJ meets the bar on its rules.
  - The decks of BBR, TXV, MZK, WDB and HGS have no reading.

## 1. How each covered rule is tested

Each covered rule has one pair: `r5`'s page, the *base*, against the variant that changes it in what the rule judges (DEC-042 point 9). The maintainer passes every base of a covered rule and fails every variant of one, so his order gives the direction on each pair.

**What the review's grades must show for a rule to pass its test.** They show it on both modes of the changed page, or on the piece for a rule judged on the piece. They show it in each of the three runs (answer 10):
- (a) the base's grade on the rule is *professional* or above;
- (b) the variant's grade on the rule is below *professional*;
- (c) so the variant stands below the base on that rule.

The test reads a grade whether or not the review marked it. The verdict leaves marked grades out (DEC-042 point 4), and the report shows each mark. Marks fall as the review gives them (answer 14).

Below, "judges" gives judge 1's grade, then judge 2's (Opus), on the rule, base then variant.

### RS-COMM-001, a page makes one point and shows it: left out of the bar
- **Pair:** page 2, ZKD → BBR. The lead is replaced by another page's point, and the title and the table stay.
- **Why left out:** the ladder holds fixed a layout with a lead left empty, and a figure's caption as its lead (answer 5).

### RS-COMM-002, the big picture comes first: left out of the bar
- **Pairs:** page 1, LTV → TXV, and deck A → deck B.
- **Why left out:** the ladder holds fixed whether a picture alone shows the whole before its parts (answer 5).

### RS-COMM-003, the pages tell the story in order: tested, thin
- **Pair:** deck A → deck B. The rule is judged on the piece only.
- **Reference:** the maintainer's, A in order and B not (question 3).
- **Judges:** A professional / excellent; B below competent / competent.
- **Thin:** one pair, and one grade a run. It is confounded with RS-COMM-002's piece part, which is off the bar.

### RS-COMM-004, the words fit the audience: left out of the bar
- **Pair:** page 3, ZCG → MZK.
- **Why left out:** the ladder holds fixed the words in a picture made elsewhere, since it has no screenshot (answer 5).

### RS-COMM-005, each fact names its source: left out of the bar
- **Pair:** page 4, TLG → WDB.
- **Why left out:** the ladder holds fixed a fact false against its source, and a picture made elsewhere (answer 5). The review is handed no source (answer 17).

### RS-GRAPHIC-001, one focal point: clean
- **Pair:** page 4, TLG → WDH. Every character has one weight and one colour, and no line is marked.
- **Reference:** TLG 1st, passes. WDH 4th, fails.
- **Judges:** base professional / excellent. Variant below competent / competent.
- **Side effect:** losing the mark also drops emphasis, which RS-GRAPHIC-007 reads.
- **Elsewhere:** the maintainer agrees with judge 1 that VNH, page 1's round 2, is below professional here (question 1, row 5).

### RS-GRAPHIC-002, what belongs together is grouped and lined up: clean, base contested by one judge
- **Pair:** page 2, ZKD → MLV. Each row's cells and signs stand at different heights and insets, and no rule separates the rows.
- **Reference:** ZKD 1st, passes. MLV 10th, fails.
- **Judges:** base competent / excellent. Variant below competent / below competent.
- **Base contested:** judge 1 grades ZKD *competent* here, since the "Kind" head sits off the icons' edge. The maintainer holds it professional (question 1, row 3).
- **Corroborating, not clean:** VVL (page 4, `form`, the steps reversed), for the part on steps joined in reading order, which no variant varies alone.

### RS-GRAPHIC-003, nothing extra: clean
- **Pair:** page 1, LTV → KST. Dice, discs and stripes are added around and over the stack.
- **Reference:** LTV 1st, passes. KST 9th, fails. The maintainer kept KST where it stands, not by how near it is to LTV.
- **Judges:** base professional / professional. Variant below competent / below competent.
- **The tag:** the maintainer reads the "your scene" tag on LTV and GPM as RS-COMM-004 (rows 8 and 9). So the base passes on this rule.
- **Side effect:** the decoration also covers words, so RS-GRAPHIC-001 and -007 drop in the judges' grades.

### RS-GRAPHIC-004, the same meaning looks the same: left out of the bar
- **Pair:** page 3, ZCG → RTJ, and deck `r5` → the RS-GRAPHIC-004 deck.
- **Why left out:** the ladder holds fixed whether a library's component is used, since it is free SVG (answer 5).

### RS-GRAPHIC-005, readable where it is shown: left out of the bar
- **Pair:** page 4, TLG → HGS. Both panels hold a longer session and a longer file, set at 11 px.
- **Why left out:** the amount and the size change together, so the pair cannot tell the two apart (answer 6). #3345's ladder varies size alone.

### RS-GRAPHIC-006, colour is never the only signal: clean
- **Pair:** page 2, ZKD → PVD. Each kind's sign and name, and the "Kind" head, become a blue or orange square, with a key under the table.
- **Reference:** ZKD 1st, passes. PVD 5th, fails.
- **Judges:** base professional / excellent. Variant below competent / below competent.
- **Side effect:** losing the names also moves RS-GRAPHIC-007 and -002.

### RS-GRAPHIC-007, the form says what the content says: clean for an added difference
- **Pair:** page 1, LTV → PBV. The four layers take four hues, where `r5` steps them in one shade.
- **Reference:** LTV 1st, passes. PBV 4th, fails. The maintainer moved PBV up: "it looks the same as the best, just different colours".
- **Judges:** base excellent / professional. Variant below competent / below competent.
- **The other half:** a difference the content has but the form drops is tested only by the `form` set against round 2, on all four pages. That set also moves RS-COMM-001 and RS-GRAPHIC-002, so it corroborates and is not clean.

### RS-GRAPHIC-008, running text is set to be read: left out of the bar
- **On this ladder: untested.** No version varies it alone, and the ladder holds little running text.
- **Why left out:** the next calibration's ladder varies running text (answer 4). The bar names `GRAPHIC@2`'s other rules singly.

### Summary
- **In the bar and clean:** RS-GRAPHIC-001, -002, -003 and -006, and RS-GRAPHIC-007 for an added difference. Judge 1 contests the base of -002.
- **In the bar and thin:** RS-COMM-003, with one pair and one grade a run.
- **Left out:** RS-COMM-001, -002, -004 and -005, and RS-GRAPHIC-004, -005 and -008.
- **Every rule rests on one pair,** on one page (answer 6). #3345 asks for two pairs per rule, on different pages.

## 2. The four conditions

DEC-042's Context gives them as conditions [project-kit#3151](https://github.com/aleskalfas/project-kit/issues/3151) set before the hold is turned on:

1. **Order:** "that the review order the ladder with the first draft below the last design the judge failed, that one below the first it judged professional, and that one about equal to the last it polished";
2. **The pass line:** "that the last it failed fail, and the first it judged professional pass";
3. **Stability:** "that the verdict be stable across the runs";
4. **The weak deck:** "that the deck as it stood on that default branch fail". On a held-out ladder, a design known to be weak stands for that deck (point 9), and here that is `main`.

Each is read for the bar, and for each covered rule alone (point 9). For the bar, conditions 1 to 3 are read on the deck and on each page. Each holds only where it holds on all five (answer 7).

### Their counterparts on the ladder

The series is the five rounds alone, and the pass lines are the maintainer's reading on the bar's rules (answer 7).

| | First draft | Last failed | First passed | Last polished |
|---|---|---|---|---|
| Page 1 | XGX `r1` | VNH `r2`=`r3` | GPM `r4` | LTV `r5` |
| Page 2 | LMZ `r1` | LMZ `r1` | BRS `r2`=`r3` | ZKD `r5` |
| Page 3 | HMC `r1` | FXK `r4` | ZCG `r5` | ZCG `r5` |
| Page 4 | NKR `r1` | MCM `r2`=`r3` | WMG `r4` | TLG `r5` |
| The deck, by the piece's verdict | `r1` | `r4` (fails on page 3 alone) | `r5` | `r5` |
| The weak deck | `main`: MPS, HLW, WBW, FTW, and its deck | | | |

- **Outside the series.** `main` stands for the weak deck (condition 4). The variants serve only their rules' pairs. The `grey` and `form` sets are reported apart.
- **Where a counterpart is degenerate.** On page 2 the first draft is the last failed design. On page 3 and on the deck, the first passed design is the last polished one. Each clause of condition 1 still reads somewhere:
  - first draft below last failed: pages 1, 3 and 4, and the deck;
  - last failed below first passed: everywhere;
  - first passed about equal to last polished: pages 1, 2 and 4.
- **Where the judges contest the reference at a counterpart.**
  - Page 4's last failed, MCM: both judges pass it, and judge 1 ranks it first.
  - Page 3's last failed, FXK: both judges pass it. On the deck, `r4` fails on FXK alone.
  - Page 1's last failed, VNH: both judges pass it, and judge 2 ranks it first.
  - Page 2's last polished, ZKD, which `r5` needs to pass: judge 1 grades RS-GRAPHIC-002 *competent*.

### Condition 1, order
- **For the bar:** the review's order of the counterparts on each page and on the deck, in each run and over the runs.
  - **Compute:** each counterpart's place, whether first draft < last failed < first passed, and whether the first passed and the last polished are about equal.
  - **The order from grades:** counting weak grades (answer 8). Of two versions, the one with fewer unmarked *below competent* grades on the bar's rules ranks higher. Then fewer *competent*, then more *excellent*. Equal on all three is a tie. A rule the review leaves ungraded counts in none.
  - **Thresholds:** "below" is strict, as stated, so a tie is not below. The first passed and the last polished are about equal where both meet the bar, in either order (answer 9).
  - **As evidence:** the rank agreement (Kendall's tau-b) between the review's order and the maintainer's, over the deck's own versions on each page, anchors apart. Also the share of the maintainer's ordered pairs the review keeps in order.
- **For a rule alone:**
  - the rule's pair stands in for the series, with its base (`r5`, the last polished) and its variant (the design that rule fails);
  - the clause "last failed below first passed" reads as the variant below the base on that rule, which is test (c) of section 1;
  - "first draft below last failed" has no counterpart for one rule;
  - the rule's grades on the rounds are reported but not tested, since the rounds vary many rules at once.
- **Context, not a threshold:** the outside rankings' agreement with each other, Kendall's tau-b over the deck's own versions, anchors apart:

  | | maintainer–judge 1 | maintainer–judge 2 | judge 1–judge 2 |
  |---|---|---|---|
  | Page 1 | 0.58 | 0.36 | 0.77 |
  | Page 2 | 0.63 | 0.63 | 1.00 |
  | Page 3 | 0.81 | 0.83 | 0.84 |
  | Page 4 | 0.85 | 0.81 | 0.86 |

### Condition 2, the pass line
- **For the bar:** the verdict fails the last failed design and passes the first passed one, on each page and on the deck.
  - **Compute:** the verdict on each counterpart in each run.
  - **Threshold:** pass or fail, as stated.
  - **Also report,** counting toward no acceptance: the verdict against the pass line on every version with a reading. The report gives false passes and false fails, per page and per run (answer 13).
- **For a rule alone,** in three parts:
  - the variant fails on the rule and the base passes on it, which is tests (a) and (b) of section 1;
  - the rule grades professional or above on each page design he passes: LTV, GPM, ZKD, MNH, BRS, ZCG, RTJ, TLG and WMG;
  - the judges put one grade below that line on those designs: judge 1 grades ZKD's RS-GRAPHIC-002 *competent*, which the maintainer holds professional.

### Condition 3, stability
- **For the bar:** the verdict on each page image is the same in each of three runs (answer 10). The Rationale asks the verdict to "say the same of the same page twice".
  - **Compute:** for each image, the number of runs that pass it and fail it. Also the share of images with one verdict in every run, and the share of deck versions with one piece verdict in every run.
  - **Compute within one run:** the verdict on the same image in each deck it stands in. That is `r5`'s pages in 9 or 10 decks, and VNH, BRS and MCM in `r2` and `r3`.
  - **Threshold:** every run gives every page image the same verdict. Within each run, every deck an image stands in gives it the same verdict.
- **For a rule alone:**
  - **Compute:** for each image, the rule's grade in each run, the share of exact agreement, the images where the rule crosses *professional* between runs, and the widest spread, in steps of grade.
  - **Threshold:** the rule stays on the same side of *professional* on each image in all three runs (answer 10).

### Condition 4, the weak deck fails
- **For the bar:** the verdict fails each of `main`'s four pages, and with them its deck, in every run (answer 11). The maintainer fails all four: MPS 8th, HLW 6th, WBW 7th, FTW 6th.
  - **Compute:** the verdict on each of its pages and on its deck, in each run.
  - **Threshold:** pass or fail, as stated.
- **For a rule alone:** the rule grades `main` below *professional* where both judges do (answer 12).
  - **Where both judges do:**
    - RS-GRAPHIC-001 on all four pages
    - RS-GRAPHIC-002 on MPS, WBW and FTW
    - RS-GRAPHIC-003 on MPS
    - RS-GRAPHIC-007 on HLW, WBW and FTW
  - **No counterpart:** RS-COMM-003 and RS-GRAPHIC-006.

### What else the run fixes before it runs, beside the bar, the ladder, the tests and the conditions (point 9)
- **One review per deck version per run.** It sees only that deck's images, under a fresh neutral code, and no other version and no earlier report. Grading never compares versions.
- **What the review is handed.**
  - A piece file for every version alike: the scratch piece's `explains: true`, `audience` and `shown`.
  - The brief's goals, through the intent command (answer 15). The brief is filled word for word from the judges' brief. No page takes a takeaway: each page states its point in its lead, and the brief's form gives a takeaway only where a page has no lead, never a copy of one (files.md, "The brief"). So that part of answer 15 is not followed, and the maintainer is told. The brief lies in `visual/pieces/ladder-scratch/brief.yaml` here, and the intent it hands is in `intent-output.txt`.
  - No source for the pages' facts (answer 17).
  - The same images the judges ranked, the 1600 × 900 copies, `main`'s included (answer 16).
- **No viewing step's report.** The review is handed the judges' copies, with no frames and no report. So it reads no check as having measured any image (DEC-062 point 3).
- **Restraint, recorded.** The review reads nothing under `ladder-judge/`, nor the ladder's source, the key, the rankings or this plan. Its report says what it read before grading (point 4).
- **What was calibrated, recorded before the first run:**
  - the model, Fable, by its full name, and its effort, pinned in the report (answer 19);
  - digests of the covered rules' text, the reviewer's definition, the design knowledge, the capability's code and its list of checks (point 9, what lapses the hold, with DEC-065 points 1 and 2), as `digests.txt` beside this plan gives them;
  - the number of runs, three;
  - the method that orders by grades, counting weak grades, and the tolerances above.
- **This plan, committed** at a commit dated before the first run, so the report can show that what the run fixed was fixed before it ran (#3230, first criterion).

## 3. What the report must show (#3230, criteria 2, 3 and 5)

The report shows each condition and each covered rule's evidence, and each version's images beside the judges' and the review's grades.

**At its head.**
- The bar as run, and the commit of this plan, dated before the first run.
- The model's full name and its effort, the digests and the number of runs.
- Each review's own list of what it read before grading.
- Where the ladder lies, and a digest of its images.
- Where no text's size was compared with its medium's minimum (DEC-046 point 8). Here that is every image, since no check measured any.

**A. The conditions** (criterion 2):
- One table for each condition, with the page or deck in rows and these columns:
  - the counterpart's code;
  - the reference's verdict or place;
  - the review's verdict or place in each run;
  - the computed figures, and *met* or *not met*.
- Then a matrix of the covered rules against the four conditions. Each cell is *met*, *not met* or *no counterpart*, and each rule's row carries its strength from section 1.

**B. Each version, page by page** (criterion 3). The cards run in the maintainer's order, with his pass line drawn between them. Each card holds:

```
┌ Page 3 · ZCG · r5 (and 9 variant decks) ───────────────────────────────────┐
│ [light image]   [dark image]          (the images the judges ranked)        │
│ Maintainer: 1st · passes     Judge 1: 1st · professional   Judge 2: 1st · … │
│ Review verdict:   run 1 pass   run 2 pass   run 3 FAIL ◆                     │
│ Rule           J1     J2     run 1 L/D    run 2 L/D    run 3 L/D             │
│ RS-GRAPHIC-001 prof   exc    prof/prof    prof/prof    comp/prof ◆ ◇         │
│ …                                                                            │
│ Marked: run 3 RS-GRAPHIC-007 need (names the tool); left out of the verdict  │
│ Same image elsewhere this run: deck v:GRAPHIC-003 run 3 pass ◆               │
└──────────────────────────────────────────────────────────────────────────────┘
```

**The marks, each on the cell it concerns:**
- ◆ a difference that counts:
  - the review's verdict differs from the maintainer's pass line;
  - a grade falls on the other side of *professional* from a judge's, and the mark says which judge;
  - the runs disagree on the verdict, or on a grade's side;
  - the same image gets a different verdict in another deck within one run;
  - light and dark fall on different sides.
- ◇ a smaller difference: another grade on the same side as the judge's, or as another run's.
- The review's place on the page, by counting weak grades, beside the maintainer's place.
- Each marked grade, *need* or *the asker's*, with what it names, and whether the verdict left it out.
- A version with no reading shows its grades and verdicts, with no mark against the pass line.

**C. Each rule's own evidence** (criterion 2). One card for each covered rule:
- the base and the variant of its changed page, side by side, in both modes;
- the reference's direction, and the two judges' grades on the rule;
- the review's grade on the rule in each run and mode;
- the result of each per-rule reading (section 2);
- its corroborating pairs, and what the ladder holds fixed of the rule.

For RS-COMM-003, the card shows strip A and strip B.

**D. The decks:**
- each deck version's four page verdicts and its piece-wide grades in each run, RS-COMM-003 the only one the bar covers;
- the piece's verdict against the reference's (only `r5` and the RS-GRAPHIC-004 deck pass), marked as in B.

**E. Outside the conditions.** The `grey` and `form` sets, apart. The anchors are left out (answer 18).

## 4. The maintainer's answers

Each question was put to the maintainer one at a time, and his words are kept in the file named.

1. **The bar against the reference:** asked row by row, on each design he passes that a judge graded below professional. Read on the bar's rules, VNH fails page 1, and LTV, GPM, BRS and RTJ pass (`answers-q1.md`). The tag and the reference for the bar are in `answers-q5.md`.
2. **The designs he fails that a judge passes:** MCM on RS-GRAPHIC-007 and -004, FXK on RS-GRAPHIC-002, and CKM on RS-GRAPHIC-007. TXF leaves the reading, as it fails only on the layering rule (`answers-q2.md`).
3. **The deck's order:** A tells the story in order and B does not, so RS-COMM-003 stays in the bar (`answers-q3.md`).
4. **RS-GRAPHIC-008:** left out of this bar, and tested on the next calibration's ladder (`answers-q4.md`).
5. **A rule with one part held fixed:** leaves the bar. That takes out RS-COMM-001, -002, -004 and -005, and RS-GRAPHIC-004 (`answers-q5.md`).
6. **One pair per rule:** enough here, with two pairs per rule in #3345. RS-GRAPHIC-005 leaves the bar, since its pair changes amount and size together (`answers-q5.md`).
7. **The counterparts:** read on the deck and on each page, each condition holding only where it holds on all five. The series is the rounds alone (`answers-q5.md`).
8. **The order from grades:** counting weak grades (`answers-q5.md`).
9. **"About equal":** both meet the bar, in either order (`answers-q5.md`).
10. **Stability:** three runs, the same verdict on every page image in each, and each rule on the same side of *professional* (`answers-q5.md`).
11. **The weak deck:** every page of `main` fails (`answers-q5.md`).
12. **Each rule alone:** the readings of section 2, with both judges' agreement as the reference on `main` (`answers-q5.md`).
13. **The verdict against his pass line on every version:** reported, counting toward no acceptance (`answers-q5.md`).
14. **Marked grades:** fall as the review gives them (`answers-q5.md`).
15. **The ladder's brief:** filled word for word from the judges' brief (`answers-q5.md`).
16. **Images:** the 1600 × 900 copies the judges ranked (`answers-q5.md`).
17. **RS-COMM-005's source:** none is handed (`answers-q5.md`).
18. **The anchors:** left out (`answers-q5.md`).
19. **The review's model:** Fable, pinned in the report (`answers-q5.md`).
20. **The ladder's files:** moved to this checkout's agent workspace before the run (`answers-q5.md`).

- **Note:** the second judge ran on Opus again at his asking, and the plan reads judge 2 as Opus (`answers-q5.md`, "The second judge's model").
