# The calibration's readings

- bar: ['RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007'] at least professional
- runs read: 3 (the plan fixes 3)
- models named: [('claude-fable-5-2', '10 (the reasoning-effort value the harness gives this run; it names no level in words)'), ('claude-fable-5-2', 'Not given - the harness names no effort for this run.'), ('claude-fable-5-2', 'Not given to me by the harness, so I cannot name it.'), ('claude-fable-5-2', 'The harness named no effort to this run, so none can be given.'), ('claude-fable-5-2', 'The harness names no effort for this run, so none can be given.'), ('claude-fable-5-2', 'The harness names no effort for this run.'), ('claude-fable-5-2', 'The harness names no effort to me, so none can be given.'), ('claude-fable-5-2', 'The harness stated no effort for this run.'), ('claude-fable-5-2', 'The harness states no effort to me, so none is named.'), ('claude-fable-5-2', 'not given by the harness'), ('claude-fable-5-2', 'not given to me by the harness'), ('claude-fable-5-2', 'not stated by the harness to this agent'), ('claude-fable-5-2', 'not stated by the harness'), ('claude-fable-5-2', 'not told by the harness'), ('claude-fable-5-2', None), (None, None)]  <-- more than one
- reviews that list the brief's file or an earlier report before grading: none
- reviews that give no verdict, a covered rule left out: [(1, 'variants/RS-COMM-001', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (1, 'variants/RS-GRAPHIC-001', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (1, 'variants/RS-GRAPHIC-002', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (2, 'variants/RS-COMM-002', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (2, 'variants/RS-COMM-003', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (2, 'variants/RS-GRAPHIC-004', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (2, 'variants/RS-GRAPHIC-007', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'rounds/round-4', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'rounds/round-5', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'sets/capability-main', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'variants/RS-COMM-002', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'variants/RS-COMM-005', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'variants/RS-GRAPHIC-001', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'variants/RS-GRAPHIC-002', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007')), (3, 'variants/RS-GRAPHIC-003', ('RS-COMM-003', 'RS-GRAPHIC-001', 'RS-GRAPHIC-002', 'RS-GRAPHIC-003', 'RS-GRAPHIC-006', 'RS-GRAPHIC-007'))]

## Condition 1, order

### Page 1: first-draft XGX, last-failed VNH, first-passed GPM, last-polished LTV
- run 1: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -1, 0)  last-failed (0, 0, 1)  first-passed (0, 0, 0)  last-polished (0, 0, 1)
  - first draft below last failed: holds
  - last failed below first passed: DOES NOT HOLD
  - first passed about equal to last polished: holds
- run 2: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, 0, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 1)
  - first draft below last failed: DOES NOT HOLD
  - last failed below first passed: DOES NOT HOLD
  - first passed about equal to last polished: holds
- run 3: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -1, 0)  last-failed (0, 0, 1)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - first draft below last failed: holds
  - last failed below first passed: DOES NOT HOLD
  - first passed about equal to last polished: DOES NOT HOLD
- run 1, evidence over 10 designs: tau-b +0.54; his ordered pairs kept in order 71%
- run 2, evidence over 10 designs: tau-b +0.53; his ordered pairs kept in order 62%
- run 3, evidence over 10 designs: tau-b +0.26; his ordered pairs kept in order 49%

### Page 2: first-draft LMZ, last-failed LMZ, first-passed BRS, last-polished ZKD
- run 1: met; scores (-#below competent, -#competent, #excellent): first-draft (0, -1, 0)  last-failed (0, -1, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - last failed below first passed: holds
  - first passed about equal to last polished: holds
- run 2: met; scores (-#below competent, -#competent, #excellent): first-draft (0, -1, 0)  last-failed (0, -1, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - last failed below first passed: holds
  - first passed about equal to last polished: holds
- run 3: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -1, 0)  last-failed (0, -1, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - last failed below first passed: holds
  - first passed about equal to last polished: DOES NOT HOLD
- run 1, evidence over 10 designs: tau-b +0.41; his ordered pairs kept in order 56%
- run 2, evidence over 10 designs: tau-b +0.73; his ordered pairs kept in order 76%
- run 3, evidence over 10 designs: tau-b +0.34; his ordered pairs kept in order 44%

### Page 3: first-draft HMC, last-failed FXK, first-passed ZCG, last-polished ZCG
- run 1: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -2, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - first draft below last failed: holds
  - last failed below first passed: DOES NOT HOLD
- run 2: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -2, 0)  last-failed (0, 0, 0)  first-passed (0, -1, 0)  last-polished (0, -1, 0)
  - first draft below last failed: holds
  - last failed below first passed: DOES NOT HOLD
- run 3: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -1, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - first draft below last failed: holds
  - last failed below first passed: DOES NOT HOLD
- run 1, evidence over 9 designs: tau-b +0.65; his ordered pairs kept in order 64%
- run 2, evidence over 9 designs: tau-b +0.46; his ordered pairs kept in order 61%
- run 3, evidence over 9 designs: tau-b +0.43; his ordered pairs kept in order 53%

### Page 4: first-draft NKR, last-failed MCM, first-passed WMG, last-polished TLG
- run 1: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, 0, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - first draft below last failed: DOES NOT HOLD
  - last failed below first passed: DOES NOT HOLD
  - first passed about equal to last polished: holds
- run 2: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, 0, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - first draft below last failed: DOES NOT HOLD
  - last failed below first passed: DOES NOT HOLD
  - first passed about equal to last polished: holds
- run 3: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, 0, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - first draft below last failed: DOES NOT HOLD
  - last failed below first passed: DOES NOT HOLD
  - first passed about equal to last polished: DOES NOT HOLD
- run 1, evidence over 10 designs: tau-b +0.65; his ordered pairs kept in order 49%
- run 2, evidence over 10 designs: tau-b +0.65; his ordered pairs kept in order 49%
- run 3, evidence over 10 designs: tau-b +0.65; his ordered pairs kept in order 49%

### The deck: first-draft rounds/round-1, last-failed rounds/round-4, first-passed rounds/round-5, last-polished rounds/round-5
- run 1: met; scores (-#below competent, -#competent, #excellent): first-draft (0, -4, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 1)  last-polished (0, 0, 1)
  - first draft below last failed: holds
  - last failed below first passed: holds
- run 2: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -3, 0)  last-failed (0, 0, 0)  first-passed (0, -1, 1)  last-polished (0, -1, 1)
  - first draft below last failed: holds
  - last failed below first passed: DOES NOT HOLD
- run 3: NOT MET; scores (-#below competent, -#competent, #excellent): first-draft (0, -3, 0)  last-failed (0, 0, 0)  first-passed (0, 0, 0)  last-polished (0, 0, 0)
  - first draft below last failed: holds
  - last failed below first passed: DOES NOT HOLD

**Condition 1 for the bar: NOT MET**

## Condition 2, the pass line

- page 1, run 1: last failed VNH pass, first passed GPM pass: NOT MET
- page 1, run 2: last failed VNH pass, first passed GPM pass: NOT MET
- page 1, run 3: last failed VNH pass, first passed GPM none: NOT MET
- page 2, run 1: last failed LMZ fail, first passed BRS pass: met
- page 2, run 2: last failed LMZ fail, first passed BRS pass: met
- page 2, run 3: last failed LMZ fail, first passed BRS pass: met
- page 3, run 1: last failed FXK pass, first passed ZCG pass: NOT MET
- page 3, run 2: last failed FXK pass, first passed ZCG fail: NOT MET
- page 3, run 3: last failed FXK none, first passed ZCG none: NOT MET
- page 4, run 1: last failed MCM pass, first passed WMG pass: NOT MET
- page 4, run 2: last failed MCM pass, first passed WMG pass: NOT MET
- page 4, run 3: last failed MCM pass, first passed WMG none: NOT MET
- the deck, run 1: last failed rounds/round-4 pass, first passed rounds/round-5 pass: NOT MET
- the deck, run 2: last failed rounds/round-4 pass, first passed rounds/round-5 fail: NOT MET
- the deck, run 3: last failed rounds/round-4 none, first passed rounds/round-5 none: NOT MET

**Condition 2 for the bar: NOT MET**

Reported, counting toward no acceptance (answer 13): the verdict against the pass line on every version with a reading.
- run 1: false passes 12 ['p4 NKR in rounds/round-1', 'p1 VNH in rounds/round-2', 'p3 CKM in rounds/round-2', 'p4 MCM in rounds/round-2', 'deck rounds/round-2', 'p1 VNH in rounds/round-3', 'p4 MCM in rounds/round-3', 'deck rounds/round-3', 'p3 FXK in rounds/round-4', 'deck rounds/round-4', 'p4 FTW in sets/capability-main', 'deck variants/RS-COMM-003']
  false fails 0 []
- run 2: false passes 14 ['p1 XGX in rounds/round-1', 'p4 NKR in rounds/round-1', 'p1 VNH in rounds/round-2', 'p3 CKM in rounds/round-2', 'p4 MCM in rounds/round-2', 'deck rounds/round-2', 'p1 VNH in rounds/round-3', 'p4 MCM in rounds/round-3', 'deck rounds/round-3', 'p3 FXK in rounds/round-4', 'deck rounds/round-4', 'p4 FTW in sets/capability-main', 'p4 WDH in variants/RS-GRAPHIC-001', 'deck variants/RS-GRAPHIC-001']
  false fails 2 ['p3 ZCG in rounds/round-5', 'deck rounds/round-5']
- run 3: false passes 9 ['p4 NKR in rounds/round-1', 'p1 VNH in rounds/round-2', 'p3 CKM in rounds/round-2', 'p4 MCM in rounds/round-2', 'deck rounds/round-2', 'p1 VNH in rounds/round-3', 'p4 MCM in rounds/round-3', 'deck rounds/round-3', 'deck variants/RS-COMM-003']
  false fails 2 ['p3 RTJ in variants/RS-GRAPHIC-004', 'deck variants/RS-GRAPHIC-004']

## Condition 3, stability

- page 1: 3 of 10 images take one verdict in every run and every deck: GPM [(1, 'pass'), (2, 'pass'), (3, 'none')]; KST [(1, 'fail'), (2, 'fail'), (3, 'none')]; LTV [(1, 'none'), (1, 'pass'), (2, 'none'), (2, 'pass'), (3, 'none'), (3, 'pass')]; MPS [(1, 'fail'), (2, 'fail'), (3, 'none')]; PBV [(1, 'fail'), (2, 'none'), (3, 'fail')]; TXV [(1, 'pass'), (2, 'none'), (3, 'none')]; XGX [(1, 'fail'), (2, 'pass'), (3, 'fail')]
- page 2: 5 of 10 images take one verdict in every run and every deck: BBR [(1, 'none'), (2, 'pass'), (3, 'pass')]; HLW [(1, 'fail'), (2, 'fail'), (3, 'none')]; MLV [(1, 'none'), (2, 'fail'), (3, 'none')]; MNH [(1, 'pass'), (2, 'pass'), (3, 'none')]; ZKD [(1, 'none'), (1, 'pass'), (2, 'none'), (2, 'pass'), (3, 'none'), (3, 'pass')]
- page 3: 6 of 10 images take one verdict in every run and every deck: FXK [(1, 'pass'), (2, 'pass'), (3, 'none')]; RTJ [(1, 'pass'), (2, 'none'), (3, 'fail')]; WBW [(1, 'fail'), (2, 'fail'), (3, 'none')]; ZCG [(1, 'none'), (1, 'pass'), (2, 'fail'), (2, 'none'), (2, 'pass'), (3, 'none'), (3, 'pass')]
- page 4: 5 of 10 images take one verdict in every run and every deck: FTW [(1, 'pass'), (2, 'pass'), (3, 'none')]; TLG [(1, 'none'), (1, 'pass'), (2, 'none'), (2, 'pass'), (3, 'none'), (3, 'pass')]; WDB [(1, 'pass'), (2, 'pass'), (3, 'none')]; WDH [(1, 'none'), (2, 'pass'), (3, 'none')]; WMG [(1, 'pass'), (2, 'pass'), (3, 'none')]
- the deck: 8 of 20 deck versions take one piece verdict in every run: rounds/round-4, rounds/round-5, sets/capability-main, variants/RS-COMM-001, variants/RS-COMM-002, variants/RS-COMM-003, variants/RS-COMM-005, variants/RS-GRAPHIC-001, variants/RS-GRAPHIC-002, variants/RS-GRAPHIC-003, variants/RS-GRAPHIC-004, variants/RS-GRAPHIC-007

**Condition 3 for the bar: NOT MET**

## Condition 4, the weak deck fails

- run 1: MPS fail, HLW fail, WBW fail, FTW pass; its deck fail: NOT MET
- run 2: MPS fail, HLW fail, WBW fail, FTW pass; its deck fail: NOT MET
- run 3: MPS none, HLW none, WBW none, FTW none; its deck none: NOT MET

**Condition 4 for the bar: NOT MET**

## Each covered rule

### RS-COMM-003
- pair, run 1: base rounds/round-5 professional, variant variants/RS-COMM-003 professional: (a) holds, (b) FAILS, (c) FAILS
- pair, run 2: base rounds/round-5 professional, variant variants/RS-COMM-003 no grade: (a) holds, (b) FAILS, (c) FAILS
- pair, run 3: base rounds/round-5 no grade, variant variants/RS-COMM-003 professional: (a) FAILS, (b) FAILS, (c) FAILS
- on what the reference passes, unmarked grades below professional: 0
- across runs and decks: one grade on 17 of 20 decks; widest spread 1 step(s); crossing professional: ['sets/capability-main', 'sets/form-contradicts', 'variants/RS-COMM-001']
- on the weak deck: no counterpart

### RS-GRAPHIC-001
- pair, run 1: base TLG professional, variant WDH no grade: (a) holds, (b) FAILS, (c) FAILS
- pair, run 2: base TLG professional, variant WDH professional: (a) holds, (b) FAILS, (c) FAILS
- pair, run 3: base TLG no grade, variant WDH no grade: (a) FAILS, (b) FAILS, (c) FAILS
- on what the reference passes, unmarked grades below professional: 1 run 3 p3 RTJ in variants/RS-GRAPHIC-004 competent
- across runs and decks: one grade on 32 of 40 images; widest spread 1 step(s); crossing professional: ['p1 PBV', 'p1 RWC', 'p2 PVD', 'p2 TNZ', 'p3 HMC', 'p3 RTJ', 'p3 XPD']
- on the weak deck, below professional on ['MPS', 'HLW', 'WBW', 'FTW']: NOT MET (run 1 MPS professional; run 1 HLW professional; run 1 WBW professional; run 1 FTW professional; run 2 MPS professional; run 2 HLW professional; run 2 WBW professional; run 2 FTW professional; run 3 MPS no grade; run 3 HLW no grade; run 3 WBW no grade; run 3 FTW no grade)

### RS-GRAPHIC-002
- pair, run 1: base ZKD professional, variant MLV no grade: (a) holds, (b) FAILS, (c) FAILS
- pair, run 2: base ZKD professional, variant MLV below competent: (a) holds, (b) holds, (c) holds
- pair, run 3: base ZKD no grade, variant MLV no grade: (a) FAILS, (b) FAILS, (c) FAILS
- on what the reference passes, unmarked grades below professional: 1 run 2 p3 ZCG in rounds/round-5 competent
- across runs and decks: one grade on 35 of 40 images; widest spread 1 step(s); crossing professional: ['p1 RWC', 'p1 XGX', 'p2 TNZ', 'p3 ZCG', 'p4 VVL']
- on the weak deck, below professional on ['MPS', 'WBW', 'FTW']: NOT MET (run 1 FTW professional; run 2 FTW professional; run 3 MPS no grade; run 3 WBW no grade; run 3 FTW no grade)

### RS-GRAPHIC-003
- pair, run 1: base LTV professional, variant KST below competent: (a) holds, (b) holds, (c) holds
- pair, run 2: base LTV professional, variant KST below competent: (a) holds, (b) holds, (c) holds
- pair, run 3: base LTV no grade, variant KST no grade: (a) FAILS, (b) FAILS, (c) FAILS
- on what the reference passes, unmarked grades below professional: 0
- across runs and decks: one grade on 39 of 40 images; widest spread 1 step(s); crossing professional: ['p3 VFF']
- on the weak deck, below professional on ['MPS']: NOT MET (run 1 MPS professional; run 2 MPS professional; run 3 MPS no grade)

### RS-GRAPHIC-006
- pair, run 1: base ZKD professional, variant PVD below competent: (a) holds, (b) holds, (c) holds
- pair, run 2: base ZKD professional, variant PVD competent: (a) holds, (b) holds, (c) holds
- pair, run 3: base ZKD no grade, variant PVD competent: (a) FAILS, (b) holds, (c) FAILS
- on what the reference passes, unmarked grades below professional: 0
- across runs and decks: one grade on 39 of 40 images; widest spread 1 step(s); crossing professional: none
- on the weak deck: no counterpart

### RS-GRAPHIC-007
- pair, run 1: base LTV excellent, variant PBV competent: (a) holds, (b) holds, (c) holds
- pair, run 2: base LTV excellent, variant PBV no grade: (a) holds, (b) FAILS, (c) FAILS
- pair, run 3: base LTV no grade, variant PBV competent: (a) FAILS, (b) holds, (c) FAILS
- on what the reference passes, unmarked grades below professional: 0
- across runs and decks: one grade on 32 of 40 images; widest spread 1 step(s); crossing professional: ['p1 GZD', 'p1 KST', 'p1 MPS', 'p4 HGS', 'p4 VVL']
- on the weak deck, below professional on ['HLW', 'WBW', 'FTW']: NOT MET (run 1 HLW professional; run 1 WBW professional; run 1 FTW professional; run 2 HLW professional; run 2 WBW professional; run 2 FTW professional; run 3 HLW no grade; run 3 WBW no grade; run 3 FTW no grade)

## The covered rules against the four conditions

| Rule | 1 order | 2 pass line | 3 stability | 4 weak deck |
|---|---|---|---|---|
| RS-COMM-003 | NOT MET | NOT MET | NOT MET | no counterpart |
| RS-GRAPHIC-001 | NOT MET | NOT MET | NOT MET | NOT MET |
| RS-GRAPHIC-002 | NOT MET | NOT MET | NOT MET | NOT MET |
| RS-GRAPHIC-003 | NOT MET | NOT MET | NOT MET | NOT MET |
| RS-GRAPHIC-006 | NOT MET | NOT MET | met | no counterpart |
| RS-GRAPHIC-007 | NOT MET | NOT MET | NOT MET | NOT MET |
| **For the bar** | NOT MET | NOT MET | NOT MET | NOT MET |
