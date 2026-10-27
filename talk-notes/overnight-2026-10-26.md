# Overnight, 26–27 October: what was done, what waits for the maintainer

## Waits for you (only a person may)

1. **Authorise #2169** (records hygiene): it refines 20 accepted records in place, stating amendments as fact and citing points by number. The landing lists each record as a finding to judge.
2. **Accept COR-065, COR-066 and COR-067** (#2178), in **PR #2194**. The PR body says how to accept. Five rounds of the critic and the methodology reviewer, then the architect. On the architect's advice I split the old COR-066 in two: **COR-066** (a decision reaches the default branch only accepted) and **COR-067** (each point marked where it is carried out; the decision debt listed). You can accept COR-065 + COR-066 now and COR-067 later. Building them is #2191 and #2192, waiting on your acceptance. One thing the architect asks you to confirm: COR-065 point 3 (a lasting choice starts with its record) binds every project unconditionally, while COR-066's refusal and COR-067's tracking are switched on by keys. I think that asymmetry is right: point 3 is a judgement the author and reviewers make, not a mechanical check.
2b. **Accept software-engineering DEC-004** in **PR #2197** (#2152): a walking skeleton's conventions are drafted into the conventions corpus and accepted by you before code builds on them. The architect asks you to authorise knowingly (a) the first writer on the conventions seam, which ADR-013 and ADR-052 describe as read-only, guarded by your acceptance and review rather than a deploy-time check, and (b) a software-engineering record changing the outcome of project-management DEC-060 points 2 and 5. Useful for the demo's foundation step, not required for it. Reviewers approved; on acceptance I add one qualifier to the software-engineering README (a reviewer's finding I settled as fixed in that commit).
3. **Merge the 2.0.0 release pull request**, once prepared (see Release).
4. **The fixers question** (living-docs, analysis-resolver): still unanswered.
4b. **The two deny rules of your 17 October decision (#1648)** are not in the shipped permission profiles: nothing denies switching signing off, or an agent editing its own instructions or settings. #1678 carries both and waits for you to approve its scope. (A builder's comment saying this on #1648 was refused by the permission classifier; I did not post it in its place.)
4c. **Two revalidations in PR #2205** (#2204, docs say answers live in answer files): the CLI reference and the project-management README are rewritten, but the change check does not ask about them, so their answers are yours to accept (core rule 20). The PR body gives the two commands and what each says; accept them and I run them, or leave them and their old deferrals stay.
5. **#2175** (what a proposed record waits on) is held: COR-066 would replace it. Close it or keep it, your call.

## Landed overnight

- #2181 (#2143): the work loop — a seat's session takes its next task, builds, opens the pull request and loops.
- #2173 (#2165): `pkit refs records-for` and core rule 22 in your wording — before changing files, read the accepted records they lead to.
- #2185 (#2182): a clone that retakes its seat no longer revives the claims it made before the seat was released (claims count only after the holder's current take).
- #2190 (#2187): the 2.0.0 changesets name no unreleased version (1.150.0), and say what to do after upgrading (commit before validating; `pkit analysis link` and `overview`).
- #2188 (#2183): landing no longer switches a clone mid-task onto main; a clean clone on main is fast-forwarded, any other clone is left with one line saying so.
- #2193 (#2186): validation right after an upgrade, before it is committed, says the move ran and to commit, not to run it again.
- #2195 (#2184): the work loop has a worker mend its own pull requests first (a conflict: merge main in; changes requested: a fix round), then take the next Task; a released seat's pull request in Review waits for you to land or hand over.
- #2198 (#2189): merging a release leaves a clone mid-task alone too, as landing does; a test keeps the two copies of the clean-up in step.
- #2200 (#2196): `pkit pm seats` lists the Tasks in Review a released seat left, with their pull requests, for you to land or hand over.
- #2202 (#2201): core rules 7 and 12 state what is built (no "future" deploy-agents, no "when available" check-diff); what they ask is unchanged.
- #2205 (#2204, split from #1779): the documents say answers live in answer files — the schemas README (a new section), CONTRIBUTING, the SE, SA and LD READMEs, three glossary terms and a view; their #1779 deferrals dropped.
- #2208 (#2206): answers made apart are reported only — the friction report counts them apart and holds nothing open for them; the docs-reviewer checks that an answer replacing them judges both.

## Release 2.0.0

- `pkit release plan` on main: backbone 1.149.0 → 2.0.0; project-management 0.55.0, software-engineering 0.3.0, software-analysis 0.2.0, living-docs 0.2.0, doc-examples 1.0.0, claude-code 0.7.0, evidence 0.5.2, demo-recording 0.2.0. 760 changesets as of 01:00 on 27 October; same segments, one expected warning (the `backbone/1.150.0` migration folder, which runs inside the 1.149.0 → 2.0.0 window).
- Upgrade rehearsal 1.149.0 → 2.0.0: **safe to release, nothing blocks.** 751 changesets consumed; both a 1.149.0 install and a pre-answer-files development install upgraded cleanly, answers moved word for word, a second upgrade and a sync changed nothing, a fresh install with the four capabilities validates. Logs: `.agent-workspace/release/rehearsal/logs/`.
- Fixes before the release: #2186 and #2187, both landed.
- Not rehearsed: the 1.149.0 tool updating itself to tag v2.0.0 (needs the tag).
- **Docs that still describe answers in blocks:** 12 artefacts (the schemas, CLI and capability READMEs, CONTRIBUTING, three glossary terms, a view, a use case) carry deferrals waiting on #1779. Rewritten in PR #2205 (#2204, split from #1779). #1779 keeps the code still missing: pruning answer files with no live answer, retiring `friction resolve`, the friction report's answered-apart count, the docs-reviewer's answered-apart check.
- PR #1794 (the 19 October design note for #1779, a scratchpad) is still open; it can be retired now that COR-062 decided it.

## The talk

- Block 2 (rules) drafted for discussion in `.agent-workspace/presentation/areas.md`, same shape as block 1, with a grilling. Not yours yet: react and we rewrite it together. It found two rules that call built parts "future" or "when available" (filed).

## Not started, on purpose

- **#521** (hand a Task to another clone): written before seats; speaks of instances and markers, where DEC-059 has seats and claims. Needs re-scoping with you before anyone builds it.
- **#2170** (records-hygiene leftovers): waits on #2169, which touches the same records.
- **#2207** (prune answer files, retire `friction resolve`): after the release. `resolve` still serves branches open across the answer move, so retiring it inside 2.0.0 could strand them.
- **#2144** (the runbook): after the release and the demo run.

## The demo run

- Plan v2: `.agent-workspace/presentation/seats/runbook-plan.md` (after the critic): a fourth, seatless clone for landing; three phases with their own time boxes; a scripted recovery; the recorded run only from a release.
- Gaps found and filed: #2182 and #2183 (being fixed tonight for the release), #2184.

## COR-066 and COR-067 overnight: what changed, on my judgement

- **COR-066, landing accepted.** You accept a record in its change before work rests on it. A check of its own (not among the per-change checks, not in the pre-push hook) refuses to merge a proposal; the merge component runs it after the reviewers. The landing list shows each acceptance with the commit that made it and the edits since, so an acceptance an agent wrote alone is visible. Direct commits: you accept before the commit. A backbone key turns the refusal on (absent = off; install asks; upgrade never writes it).
- **COR-067, the debt.** A mark is declared: a document names, beside its anchors, the point it carries out and its own anchors on what carries it out; a reviewer checks it. Any other anchor marks nothing, so a design written before the code does not clear the debt. "Nothing to carry out" sits in the record's front matter, accepted by you with it. No "not yet carried out" reason: an unmarked point is the debt, listed with its age. Its own key and starting line; points accepted before it are listed apart, owed by nobody.
