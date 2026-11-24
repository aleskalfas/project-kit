# The calibration's readings

- bar: ['RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007'] at least professional; order: counting

## The head: each claim about the inputs, from a check

- **judge-1:** 20 folders, 20 documents kept, 20 read, 0 giving no reading
- **judge-2:** 20 folders, 20 documents kept, 20 read, 0 giving no reading
- **run-1:** 20 folders, 20 documents kept, 20 read, 0 giving no reading
- **run-2:** 20 folders, 20 documents kept, 20 read, 0 giving no reading
- **run-3:** 20 folders, 20 documents kept, 20 read, 0 giving no reading

**No reading, by page and piece** (read as no reading in every condition):
- judge-1: 0 pages and 0 pieces with no reading
- judge-2: 0 pages and 0 pieces with no reading
- run-1: 0 pages and 0 pieces with no reading
- run-2: 0 pages and 0 pieces with no reading
- run-3: 0 pages and 0 pieces with no reading

**The model, by its name alone,** the model id each document's name for it holds: the reviews name {'claude-fable-5-2': 60}; one id: True; the reference pins claude-fable-5-2; the pinned id: True. The judges name {'claude-fable-5-2': 20, 'claude-opus-5-5': 20}. As written, the reviews name {'claude-fable-5-2': 56, 'claude-fable-5-2 (Fable 5.2), as the harness names it. The harness states no effort.': 1, 'Fable 5.2, model ID claude-fable-5-2': 1, 'claude-fable-5-2 (Fable 5.2)': 1, 'claude-fable-5-2 (Fable 5.2). The harness names no effort.': 1}, and the judges {'claude-fable-5-2': 20, 'Claude Opus 5.5 (claude-opus-5-5)': 15, 'claude-opus-5-5': 5}.

**The effort, from the dispatcher's record:**
- run-1: {'agent': 'graphic-design-reviewer', 'model': 'fable', 'effort': 'none set by the dispatch'}
- run-2: {'agent': 'graphic-design-reviewer', 'model': 'fable', 'effort': 'none set by the dispatch'}
- run-3: {'agent': 'graphic-design-reviewer', 'model': 'fable', 'effort': 'none set by the dispatch'}

**Reads outside the allowlist,** by every file each document lists:
- judge-1: 200 files named as read over 20 documents, and 0 named only as not handed; 0 documents flagged
- judge-2: 228 files named as read over 20 documents, and 0 named only as not handed; 1 documents flagged
  - HVCG (rounds/round-4): `.agent-workspace/judge-2-HVCG-zoom/`, in “.agent-workspace/calibration-dev/folders/judge-2/HVCG/page-1.light.png to page-4.light.png and page-1.dark.png to page-4.dark.png; also enlarged crops and pixel measurements (contrast ratios, cap heights, line extents) of those same images, which I made in .agent-workspace/judge-2-HVCG-zoom/ and removed afterwards”
- run-1: 476 files named as read over 20 documents, and 19 named only as not handed; 0 documents flagged
- run-2: 490 files named as read over 20 documents, and 19 named only as not handed; 0 documents flagged
- run-3: 496 files named as read over 20 documents, and 19 named only as not handed; 0 documents flagged

**The judges' words:**
- judge-1: 0 grades below professional name no words
- judge-2: 0 grades below professional name no words

**What each folder held,** against its key:
- judge-1: 20 holds exactly the files the key records, byte for byte
- judge-2: 20 holds exactly the files the key records, byte for byte
- run-1: 20 holds exactly the files the key records, byte for byte
- run-2: 20 holds exactly the files the key records, byte for byte
- run-3: 20 holds exactly the files the key records, byte for byte

**Handed alike:** every source was handed the same files for each version

**Laid out:**
- judge-1: laid out at 2026-11-18T23:10:50+00:00 from tech-docs/calibrations/graphic-design-review/next/plan.md at 352d4cfb85a4 (2026-11-19T00:09:50+01:00); committed before it was laid out; unchanged since
- judge-2: laid out at 2026-11-18T23:10:50+00:00 from tech-docs/calibrations/graphic-design-review/next/plan.md at 352d4cfb85a4 (2026-11-19T00:09:50+01:00); committed before it was laid out; unchanged since
- run-1: laid out at 2026-11-18T23:10:50+00:00 from tech-docs/calibrations/graphic-design-review/next/plan.md at 352d4cfb85a4 (2026-11-19T00:09:50+01:00); committed before it was laid out; unchanged since
- run-2: laid out at 2026-11-18T23:10:50+00:00 from tech-docs/calibrations/graphic-design-review/next/plan.md at 352d4cfb85a4 (2026-11-19T00:09:50+01:00); committed before it was laid out; unchanged since
- run-3: laid out at 2026-11-18T23:10:50+00:00 from tech-docs/calibrations/graphic-design-review/next/plan.md at 352d4cfb85a4 (2026-11-19T00:09:50+01:00); committed before it was laid out; unchanged since

## The control, on the judges' grades (order: counting)

Each clause, its counterparts' agreement, each judge read as the review, and whether it enters:

- condition 1, page 1, first draft below last failed: **contested**. XGX maintainer fail, judge-1 pass, judge-2 pass; VNH maintainer fail, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 holds.
- condition 1, page 1, last failed below first passed: **contested**. VNH maintainer fail, judge-1 pass, judge-2 pass; GPM maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 does not hold.
- condition 1, page 1, first passed about equal to last polished: **contested**. GPM maintainer pass, judge-1 pass, judge-2 pass; LTV maintainer pass, judge-1 pass, judge-2 fail. As the review: judge-1 holds, judge-2 does not hold.
- condition 2, page 1, last failed fails and first passed passes: **contested**. VNH maintainer fail, judge-1 pass, judge-2 pass; GPM maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 does not hold.
- condition 1, page 2, last failed below first passed: **entered**. LMZ maintainer fail, judge-1 fail, judge-2 fail; BRS maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 holds, judge-2 holds.
- condition 1, page 2, first passed about equal to last polished: **entered**. BRS maintainer pass, judge-1 pass, judge-2 pass; ZKD maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 holds, judge-2 holds.
- condition 2, page 2, last failed fails and first passed passes: **entered**. LMZ maintainer fail, judge-1 fail, judge-2 fail; BRS maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 holds, judge-2 holds.
- condition 1, page 3, first draft below last failed: **contested**. HMC maintainer fail, judge-1 fail, judge-2 fail; FXK maintainer fail, judge-1 pass, judge-2 fail. As the review: judge-1 holds, judge-2 holds.
- condition 1, page 3, last failed below first passed: **contested**. FXK maintainer fail, judge-1 pass, judge-2 fail; ZCG maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 holds.
- condition 2, page 3, last failed fails and first passed passes: **contested**. FXK maintainer fail, judge-1 pass, judge-2 fail; ZCG maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 holds.
- condition 1, page 4, first draft below last failed: **contested**. NKR maintainer fail, judge-1 fail, judge-2 fail; MCM maintainer fail, judge-1 pass, judge-2 pass. As the review: judge-1 holds, judge-2 holds.
- condition 1, page 4, last failed below first passed: **contested**. MCM maintainer fail, judge-1 pass, judge-2 pass; WMG maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 does not hold.
- condition 1, page 4, first passed about equal to last polished: **entered**. WMG maintainer pass, judge-1 pass, judge-2 pass; TLG maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 holds, judge-2 holds.
- condition 2, page 4, last failed fails and first passed passes: **contested**. MCM maintainer fail, judge-1 pass, judge-2 pass; WMG maintainer pass, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 does not hold.
- condition 1, the deck, first draft below last failed: **contested**. rounds/round-1 maintainer fail, judge-1 fail, judge-2 fail; rounds/round-4 maintainer fail, judge-1 pass, judge-2 fail. As the review: judge-1 holds, judge-2 holds.
- condition 1, the deck, last failed below first passed: **contested**. rounds/round-4 maintainer fail, judge-1 pass, judge-2 fail; rounds/round-5 maintainer pass, judge-1 pass, judge-2 fail. As the review: judge-1 does not hold, judge-2 does not hold.
- condition 2, the deck, last failed fails and first passed passes: **contested**. rounds/round-4 maintainer fail, judge-1 pass, judge-2 fail; rounds/round-5 maintainer pass, judge-1 pass, judge-2 fail. As the review: judge-1 does not hold, judge-2 does not hold.
- condition 4, page 1, the weak deck's page fails: **entered**. MPS maintainer fail, judge-1 fail, judge-2 fail. As the review: judge-1 holds, judge-2 holds.
- condition 4, page 2, the weak deck's page fails: **contested**. HLW maintainer fail, judge-1 fail, judge-2 pass. As the review: judge-1 holds, judge-2 does not hold.
- condition 4, page 3, the weak deck's page fails: **entered**. WBW maintainer fail, judge-1 fail, judge-2 fail. As the review: judge-1 holds, judge-2 holds.
- condition 4, page 4, the weak deck's page fails: **contested**. FTW maintainer fail, judge-1 pass, judge-2 pass. As the review: judge-1 does not hold, judge-2 does not hold.
- condition 4, the deck, the weak deck fails: **entered**. sets/capability-main maintainer fail, judge-1 fail, judge-2 fail. As the review: judge-1 holds, judge-2 holds.

**Contested designs, and those a judge gives no reading, reported apart:**
- page 1 LTV: maintainer pass, judge-1 pass, judge-2 fail (contested)
- page 1 VNH: maintainer fail, judge-1 pass, judge-2 pass (contested)
- page 1 GZD: maintainer fail, judge-1 pass, judge-2 pass (contested)
- page 1 XGX: maintainer fail, judge-1 pass, judge-2 pass (contested)
- page 2 HLW: maintainer fail, judge-1 fail, judge-2 pass (contested)
- page 3 RTJ: maintainer pass, judge-1 fail, judge-2 pass (contested)
- page 3 FXK: maintainer fail, judge-1 pass, judge-2 fail (contested)
- page 3 CKM: maintainer fail, judge-1 pass, judge-2 pass (contested)
- page 4 MCM: maintainer fail, judge-1 pass, judge-2 pass (contested)
- page 4 FTW: maintainer fail, judge-1 pass, judge-2 pass (contested)
- the deck rounds/round-5: maintainer pass, judge-1 pass, judge-2 fail (contested)
- the deck variants/RS-GRAPHIC-004: maintainer pass, judge-1 fail, judge-2 pass (contested)
- the deck rounds/round-2: maintainer fail, judge-1 pass, judge-2 fail (contested)
- the deck rounds/round-3: maintainer fail, judge-1 pass, judge-2 fail (contested)
- the deck rounds/round-4: maintainer fail, judge-1 pass, judge-2 fail (contested)
- the deck variants/RS-COMM-003: maintainer fail, judge-1 pass, judge-2 fail (contested)

**Each covered rule's references:**

- **RS-COMM-003**
  - pair rounds/round-5 → variants/RS-COMM-003 (piece): contested; judge-1 grades the variant variants/RS-COMM-003 professional; judge-2 grades the variant variants/RS-COMM-003 professional
  - passed designs entered: ['rounds/round-5', 'variants/RS-GRAPHIC-004']; contested: none
  - the weak deck: ['sets/capability-main not a reference (judge-1 grades sets/capability-main professional)']
- **RS-GRAPHIC-001**
  - pair TLG → WDH (4): contested; judge-1 grades the variant WDH professional; judge-2 grades the variant WDH professional
  - passed designs entered: ['LTV', 'GPM', 'ZKD', 'MNH', 'BRS', 'ZCG', 'RTJ', 'TLG', 'WMG']; contested: none
  - the weak deck: ['MPS not a reference (judge-1 grades MPS professional; judge-2 grades MPS professional)', 'HLW not a reference (judge-1 grades HLW professional; judge-2 grades HLW professional)', 'WBW not a reference (judge-1 grades WBW professional; judge-2 grades WBW professional)', 'FTW not a reference (judge-1 grades FTW professional; judge-2 grades FTW professional)']
- **RS-GRAPHIC-002**
  - pair ZKD → MLV (2): entered
  - passed designs entered: ['LTV', 'GPM', 'ZKD', 'MNH', 'BRS', 'ZCG', 'RTJ', 'TLG', 'WMG']; contested: none
  - the weak deck: ['MPS entered', 'HLW not a reference (judge-2 grades HLW professional)', 'WBW entered', 'FTW not a reference (judge-1 grades FTW professional; judge-2 grades FTW professional)']
- **RS-GRAPHIC-003**
  - pair LTV → KST (1): entered
  - passed designs entered: ['LTV', 'GPM', 'ZKD', 'MNH', 'BRS', 'ZCG', 'RTJ', 'TLG', 'WMG']; contested: none
  - the weak deck: ['MPS not a reference (judge-2 grades MPS professional)', 'HLW not a reference (judge-1 grades HLW professional; judge-2 grades HLW professional)', 'WBW not a reference (judge-1 grades WBW professional; judge-2 grades WBW professional)', 'FTW not a reference (judge-1 grades FTW professional; judge-2 grades FTW professional)']
- **RS-GRAPHIC-006**
  - pair ZKD → PVD (2): entered
  - passed designs entered: ['LTV', 'GPM', 'ZKD', 'MNH', 'BRS', 'ZCG', 'RTJ', 'TLG', 'WMG']; contested: none
  - the weak deck: ['MPS not a reference (judge-1 grades MPS professional; judge-2 grades MPS professional)', 'HLW not a reference (judge-1 grades HLW professional; judge-2 grades HLW professional)', 'WBW not a reference (judge-1 grades WBW professional; judge-2 grades WBW professional)', 'FTW not a reference (judge-1 grades FTW professional; judge-2 grades FTW professional)']
- **RS-GRAPHIC-007**
  - pair LTV → PBV (1): contested; judge-2 grades the base LTV competent
  - passed designs entered: ['GPM', 'ZKD', 'MNH', 'BRS', 'ZCG', 'TLG', 'WMG']; contested: ['LTV (judge-2 grades LTV competent)', 'RTJ (judge-1 grades RTJ competent)']
  - the weak deck: ['MPS not a reference (judge-1 grades MPS professional; judge-2 grades MPS professional)', 'HLW not a reference (judge-2 grades HLW professional)', 'WBW not a reference (judge-1 grades WBW professional; judge-2 grades WBW professional)', 'FTW not a reference (judge-1 grades FTW professional; judge-2 grades FTW professional)']

## The conditions for the bar, on the runs

- condition 1, page 1, first draft below last failed (XGX, VNH): contested
- condition 1, page 1, last failed below first passed (VNH, GPM): contested
- condition 1, page 1, first passed about equal to last polished (GPM, LTV): contested
- condition 2, page 1, last failed fails and first passed passes (VNH, GPM): contested
- condition 1, page 2, last failed below first passed (LMZ, BRS): entered: run-1 holds, run-2 holds, run-3 holds; scores run-1 ['(0, -1, 0)', '(0, 0, 0)']; run-2 ['(0, -1, 0)', '(0, 0, 0)']; run-3 ['(0, -1, 0)', '(0, 0, 0)']
- condition 1, page 2, first passed about equal to last polished (BRS, ZKD): entered: run-1 holds, run-2 holds, run-3 holds
- condition 2, page 2, last failed fails and first passed passes (LMZ, BRS): entered: run-1 holds, run-2 holds, run-3 holds
- condition 1, page 3, first draft below last failed (HMC, FXK): contested
- condition 1, page 3, last failed below first passed (FXK, ZCG): contested
- condition 2, page 3, last failed fails and first passed passes (FXK, ZCG): contested
- condition 1, page 4, first draft below last failed (NKR, MCM): contested
- condition 1, page 4, last failed below first passed (MCM, WMG): contested
- condition 1, page 4, first passed about equal to last polished (WMG, TLG): entered: run-1 holds, run-2 holds, run-3 holds
- condition 2, page 4, last failed fails and first passed passes (MCM, WMG): contested
- condition 1, the deck, first draft below last failed (rounds/round-1, rounds/round-4): contested
- condition 1, the deck, last failed below first passed (rounds/round-4, rounds/round-5): contested
- condition 2, the deck, last failed fails and first passed passes (rounds/round-4, rounds/round-5): contested
- condition 4, page 1, the weak deck's page fails (MPS): entered: run-1 does not hold, run-2 does not hold, run-3 does not hold
- condition 4, page 2, the weak deck's page fails (HLW): contested
- condition 4, page 3, the weak deck's page fails (WBW): entered: run-1 holds, run-2 holds, run-3 holds
- condition 4, page 4, the weak deck's page fails (FTW): contested
- condition 4, the deck, the weak deck fails (sets/capability-main): entered: run-1 holds, run-2 holds, run-3 holds

**Condition 3, stability.** Each image with a reading in the reference, in every run and every deck it stands in:

- page 1: 7 of 9 stable; 2 unstable; 0 not read in every run
  - stable: GPM (pass), KST (fail), LTV (pass), MPS (pass), RWC (fail), VNH (pass), XGX (pass)
  - unstable: GZD: run-1 fail; run-2 fail; run-3 pass
  - unstable: PBV: run-1 fail; run-2 fail; run-3 pass
  - left out, no reading in the reference: TXV
- page 2: 8 of 9 stable; 1 unstable; 0 not read in every run
  - stable: BRS (pass), LMZ (fail), MLV (fail), MNH (pass), PVD (fail), TDF (fail), TNZ (fail), ZKD (pass)
  - unstable: HLW: run-1 fail; run-2 fail; run-3 pass
  - left out, no reading in the reference: BBR
- page 3: 8 of 8 stable; 0 unstable; 0 not read in every run
  - stable: CKM (pass), FXK (pass), HMC (fail), RTJ (pass), VFF (fail), WBW (fail), XPD (fail), ZCG (pass)
  - left out, no reading in the reference: TXF, MZK
- page 4: 6 of 8 stable; 2 unstable; 0 not read in every run
  - stable: FTW (pass), MCM (pass), NKR (fail), TLG (pass), VVL (fail), WMG (pass)
  - unstable: WDH: run-1 pass; run-2 pass; run-3 fail
  - unstable: ZWT: run-1 fail; run-2 pass; run-3 pass
  - left out, no reading in the reference: WDB, HGS
- the deck: 13 of 15 stable; 2 unstable; 0 not read in every run
  - stable: rounds/round-5 (pass), variants/RS-GRAPHIC-004 (pass), rounds/round-1 (fail), rounds/round-2 (pass), rounds/round-3 (pass), rounds/round-4 (pass), sets/capability-main (fail), sets/form-contradicts (fail), sets/grey-boxes (fail), variants/RS-COMM-003 (pass), variants/RS-GRAPHIC-002 (fail), variants/RS-GRAPHIC-003 (fail), variants/RS-GRAPHIC-006 (fail)
  - unstable: variants/RS-GRAPHIC-001: run-1 pass; run-2 pass; run-3 fail
  - unstable: variants/RS-GRAPHIC-007: run-1 fail; run-2 fail; run-3 pass
  - left out, no reading in the reference: variants/RS-COMM-001, variants/RS-COMM-002, variants/RS-COMM-004, variants/RS-COMM-005, variants/RS-GRAPHIC-005

**The evidence,** the review's order against the maintainer's, counting toward no acceptance (designs with no reading in the reference, or in the run, left out):

- page 1 (left out, no reading in the reference: TXV):
  - run-1: over 9 designs, tau-b +0.30, his ordered pairs kept in order 47%
  - run-2: over 9 designs, tau-b +0.30, his ordered pairs kept in order 47%
  - run-3: over 9 designs, tau-b +0.30, his ordered pairs kept in order 31%
- page 2 (left out, no reading in the reference: BBR):
  - run-1: over 9 designs, tau-b +0.73, his ordered pairs kept in order 75%
  - run-2: over 9 designs, tau-b +0.71, his ordered pairs kept in order 78%
  - run-3: over 9 designs, tau-b +0.78, his ordered pairs kept in order 69%
- page 3 (left out, no reading in the reference: TXF, MZK):
  - run-1: over 8 designs, tau-b +0.78, his ordered pairs kept in order 71%
  - run-2: over 8 designs, tau-b +0.78, his ordered pairs kept in order 71%
  - run-3: over 8 designs, tau-b +0.78, his ordered pairs kept in order 71%
- page 4 (left out, no reading in the reference: WDB, HGS):
  - run-1: over 8 designs, tau-b +0.70, his ordered pairs kept in order 68%
  - run-2: over 8 designs, tau-b +0.60, his ordered pairs kept in order 54%
  - run-3: over 8 designs, tau-b +0.54, his ordered pairs kept in order 61%

**The verdict against the reference on every version with a reading,** counting toward no acceptance:

- run-1: 15 false passes, 0 false fails, 0 with no reading
  - false passes: ['p1 XGX in rounds/round-1 (contested)', 'p1 VNH in rounds/round-2 (contested)', 'p3 CKM in rounds/round-2 (contested)', 'p4 MCM in rounds/round-2 (contested)', 'deck rounds/round-2 (contested)', 'p1 VNH in rounds/round-3 (contested)', 'p4 MCM in rounds/round-3 (contested)', 'deck rounds/round-3 (contested)', 'p3 FXK in rounds/round-4 (contested)', 'deck rounds/round-4 (contested)', 'p1 MPS in sets/capability-main', 'p4 FTW in sets/capability-main (contested)', 'deck variants/RS-COMM-003 (contested)', 'p4 WDH in variants/RS-GRAPHIC-001', 'deck variants/RS-GRAPHIC-001']
  - false fails: []
- run-2: 16 false passes, 0 false fails, 0 with no reading
  - false passes: ['p1 XGX in rounds/round-1 (contested)', 'p1 VNH in rounds/round-2 (contested)', 'p3 CKM in rounds/round-2 (contested)', 'p4 MCM in rounds/round-2 (contested)', 'deck rounds/round-2 (contested)', 'p1 VNH in rounds/round-3 (contested)', 'p4 MCM in rounds/round-3 (contested)', 'deck rounds/round-3 (contested)', 'p3 FXK in rounds/round-4 (contested)', 'deck rounds/round-4 (contested)', 'p1 MPS in sets/capability-main', 'p4 FTW in sets/capability-main (contested)', 'p4 ZWT in sets/grey-boxes', 'deck variants/RS-COMM-003 (contested)', 'p4 WDH in variants/RS-GRAPHIC-001', 'deck variants/RS-GRAPHIC-001']
  - false fails: []
- run-3: 18 false passes, 0 false fails, 0 with no reading
  - false passes: ['p1 XGX in rounds/round-1 (contested)', 'p1 VNH in rounds/round-2 (contested)', 'p3 CKM in rounds/round-2 (contested)', 'p4 MCM in rounds/round-2 (contested)', 'deck rounds/round-2 (contested)', 'p1 VNH in rounds/round-3 (contested)', 'p4 MCM in rounds/round-3 (contested)', 'deck rounds/round-3 (contested)', 'p3 FXK in rounds/round-4 (contested)', 'deck rounds/round-4 (contested)', 'p1 MPS in sets/capability-main', 'p2 HLW in sets/capability-main (contested)', 'p4 FTW in sets/capability-main (contested)', 'p1 GZD in sets/grey-boxes (contested)', 'p4 ZWT in sets/grey-boxes', 'deck variants/RS-COMM-003 (contested)', 'p1 PBV in variants/RS-GRAPHIC-007', 'deck variants/RS-GRAPHIC-007']
  - false fails: []

## Each covered rule

### RS-COMM-003

- pair rounds/round-5 → variants/RS-COMM-003: contested (judge-1 grades the variant variants/RS-COMM-003 professional; judge-2 grades the variant variants/RS-COMM-003 professional)
- passed design rounds/round-5: professional or above wherever read
- passed design variants/RS-GRAPHIC-004: professional or above wherever read
- stability: one grade on 15 of 15; widest spread 0 step(s); crossing professional: none; no reading: none

### RS-GRAPHIC-001

- pair TLG → WDH: contested (judge-1 grades the variant WDH professional; judge-2 grades the variant WDH professional)
- passed design LTV: professional or above wherever read
- passed design GPM: professional or above wherever read
- passed design ZKD: professional or above wherever read
- passed design MNH: professional or above wherever read
- passed design BRS: professional or above wherever read
- passed design ZCG: professional or above wherever read
- passed design RTJ: professional or above wherever read
- passed design TLG: professional or above wherever read
- passed design WMG: professional or above wherever read
- stability: one grade on 34 of 34; widest spread 0 step(s); crossing professional: none; no reading: none

### RS-GRAPHIC-002

- pair ZKD → MLV, run-1: base professional, variant below competent: (a) holds, (b) holds, (c) holds
- pair ZKD → MLV, run-2: base professional, variant below competent: (a) holds, (b) holds, (c) holds
- pair ZKD → MLV, run-3: base professional, variant below competent: (a) holds, (b) holds, (c) holds
- passed design LTV: professional or above wherever read
- passed design GPM: professional or above wherever read
- passed design ZKD: professional or above wherever read
- passed design MNH: professional or above wherever read
- passed design BRS: professional or above wherever read
- passed design ZCG: professional or above wherever read
- passed design RTJ: professional or above wherever read
- passed design TLG: professional or above wherever read
- passed design WMG: professional or above wherever read
- weak deck MPS: not below in run-1 professional; run-2 professional; run-3 professional
- weak deck WBW: below professional in every run
- stability: one grade on 28 of 34; widest spread 1 step(s); crossing professional: ['p2 HLW', 'p2 PVD', 'p2 TNZ', 'p3 XPD', 'p4 NKR', 'p4 VVL']; no reading: none

### RS-GRAPHIC-003

- pair LTV → KST, run-1: base professional, variant below competent: (a) holds, (b) holds, (c) holds
- pair LTV → KST, run-2: base professional, variant below competent: (a) holds, (b) holds, (c) holds
- pair LTV → KST, run-3: base professional, variant below competent: (a) holds, (b) holds, (c) holds
- passed design LTV: professional or above wherever read
- passed design GPM: professional or above wherever read
- passed design ZKD: professional or above wherever read
- passed design MNH: professional or above wherever read
- passed design BRS: professional or above wherever read
- passed design ZCG: professional or above wherever read
- passed design RTJ: professional or above wherever read
- passed design TLG: professional or above wherever read
- passed design WMG: professional or above wherever read
- stability: one grade on 32 of 34; widest spread 1 step(s); crossing professional: ['p2 TDF', 'p3 XPD']; no reading: none

### RS-GRAPHIC-006

- pair ZKD → PVD, run-1: base professional, variant competent: (a) holds, (b) holds, (c) holds
- pair ZKD → PVD, run-2: base professional, variant competent: (a) holds, (b) holds, (c) holds
- pair ZKD → PVD, run-3: base professional, variant competent: (a) holds, (b) holds, (c) holds
- passed design LTV: professional or above wherever read
- passed design GPM: professional or above wherever read
- passed design ZKD: professional or above wherever read
- passed design MNH: professional or above wherever read
- passed design BRS: professional or above wherever read
- passed design ZCG: professional or above wherever read
- passed design RTJ: professional or above wherever read
- passed design TLG: professional or above wherever read
- passed design WMG: professional or above wherever read
- stability: one grade on 34 of 34; widest spread 0 step(s); crossing professional: none; no reading: none

### RS-GRAPHIC-007

- pair LTV → PBV: contested (judge-2 grades the base LTV competent)
- passed design GPM: professional or above wherever read
- passed design ZKD: professional or above wherever read
- passed design MNH: professional or above wherever read
- passed design BRS: professional or above wherever read
- passed design ZCG: professional or above wherever read
- passed design TLG: professional or above wherever read
- passed design WMG: professional or above wherever read
- stability: one grade on 21 of 34; widest spread 1 step(s); crossing professional: ['p1 GZD', 'p1 KST', 'p1 PBV', 'p2 MLV', 'p2 PVD', 'p4 WDH', 'p4 ZWT']; no reading: none

## The covered rules against the four conditions

| Rule | 1 order | 2 pass line | 3 stability | 4 weak deck |
|---|---|---|---|---|
| RS-COMM-003 | no counterpart | met | met | no counterpart |
| RS-GRAPHIC-001 | no counterpart | met | met | no counterpart |
| RS-GRAPHIC-002 | met | met | not met | not met |
| RS-GRAPHIC-003 | met | met | not met | no counterpart |
| RS-GRAPHIC-006 | met | met | met | no counterpart |
| RS-GRAPHIC-007 | no counterpart | met | not met | no counterpart |
| **For the bar** | met on the 2 of 5 places with a counterpart | met on the 1 of 5 places with a counterpart | not met | not met |

For the bar, by place:

| Condition | 1 | 2 | 3 | 4 | deck |
|---|---|---|---|---|---|
| 1 | no counterpart | met | no counterpart | met | no counterpart |
| 2 | no counterpart | met | no counterpart | no counterpart | no counterpart |
| 3 | not met | not met | met | not met | not met |
| 4 | not met | no counterpart | met | no counterpart | met |

