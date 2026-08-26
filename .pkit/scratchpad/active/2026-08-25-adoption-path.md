---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-25
---

# Adoption path

*Adversarial usability effort: challenge pkit's adoption, collect problems + con-arguments honestly, fix one by one, repeat. Findings are recorded as the maintainer drives adoption on their own; the agent observes and records, does not smooth over.*

## Framing (maintainer's)

- **Roles to support:** project-manager + developer. Two adoption paths — may or may not be identical (TBD).
- **Two perspectives of adoption:**
  - *Technical* — use the tool without being a rocket scientist; quickly understand install / upgrade / init; understand the difference between the pkit CLI and the initialized pkit in a project.
  - *Mental model* — quickly grasp the basic building blocks and concepts.
- **The argument to defeat (honestly):** why use pkit instead of ad-hoc Claude-generated functionality in the project? Claude can be quite good at generating working things. For-pkit args (reusability, maintainability, …) do not win if the user can't quickly understand and use pkit.
- **Honesty signal:** a colleague stopped using pkit — it didn't fit him; he didn't even finish setting up the project.

## Loop

challenge pkit → collect problems + con-arguments → fix → challenge → collect → fix → …

## Findings

*(recorded as they surface: what I did → what I expected → what happened / what was confusing / the con-argument. Each is a candidate fix.)*

**F1 — Container-type taxonomy causes hesitation before any work is held.**
Did: as PM, tried to pick a container for the adoption effort. Expected: an obvious "put work here." Got: hesitation across EPIC/Feature/Umbrella/Task/Milestone; reached for Milestone "because it's more flexible" (i.e. EPIC felt rigid/heavy); unsure whether PM + developer roles even share a path. The type system makes "where do I put some work" a non-obvious up-front decision.

**F2 — "Milestone" is not the flexible bucket it sounds like.**
Did: `pkit project-management create-milestone`. Expected: create a lightweight flexible container. Got: requires a pre-declared `category` in `project/config.yaml` `milestone_categories:` (can't be created ad-hoc), carries close-trigger semantics, and the only declared category is "outcome bundle of related EPICs; closes when every child EPIC closes" — so it bundles EPICs, not Tasks. Flexibility intuition (dateless/content-based) is partially met, but the shape contradicts "put a task under it."

**F3 (meta) — Ceremony before value.**
Deciding merely *how to hold* the work required learning milestone categories, close-triggers, and the EPIC→Task hierarchy — up-front cost paid before any adoption benefit. This is exactly the asymmetry that loses a new adopter (cf. the colleague who quit before finishing setup).

**F4 — Milestone layer has no evident payoff in the single-EPIC case.**
Observed: if one EPIC holds all the tasks, the Milestone (declared shape: "bundle of EPICs") wraps a single child and adds nothing. Question raised by the PM adopter: "why have Milestones then?" The container hierarchy carries a layer whose value isn't self-evident until you have *multiple* EPICs to bundle — so a first-time adopter meets it as pure overhead. Candidate: guidance on when a Milestone earns its keep (≥2 related EPICs), or don't surface it in the basic path at all.

**F5 — EPIC is forced to kind `feature`; can't file a maintenance/usability EPIC honestly.**
Did: `create-issue --type epic --kind maintenance`. Got: refused — "epic/feature/umbrella carry kind 'feature' by definition." But this adoption effort is genuinely usability/maintenance, not a shipped feature. The taxonomy forces a semantic label that doesn't fit, so the classification lies (this EPIC is labelled `type:feature`). Candidate: allow non-feature kinds on structural clusters, or relax the restriction / document the rationale so it doesn't read as the tool mislabeling the work.

## Decision so far

Drop the Milestone. Use: **EPIC** ("make adoption clear & simple") → this discovery Task (hosts the scratchpad) + friction-fix Tasks. Scratchpad persists on the discovery Task's branch (commit + push), retires to `done/` at the end.

**F6 — README has no actual install instructions (fails at step 0).**
Did: came to the pkit GitHub repo, looked for how to install. Expected: a copy-pasteable "get pkit" command in the first screen. Got: a `## Installation model` section that explains the *concept* of `init`/`sync`/`upgrade` and assumes `pkit` is already on PATH; the concrete command to obtain the CLI (the git URL / `uvx` / `uv tool install`) is nowhere — even though the text says "installs via a direct git URL," it never gives the URL or command. A newcomer cannot get from "found the repo" to "pkit running."
Con-argument (amplified): if I can't even install it in the first minute, ad-hoc Claude generation (zero install) wins by default — the up-front-cost asymmetry, hit at second zero.
Scope: prompts a from-the-ground review of README.md (and the docs generally).

**F6 addendum — the install command exists, but only in a decision record + the cli README, never the front door.**
The canonical `uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git` (+ `uv` prerequisite, HTTPS form for PAT) is in PRJ-004 and `.pkit/cli/README.md` — but not README.md. Even with full repo access it took a search to surface. Confirms: the front door must carry the literal install command, not defer it to depth docs.

## README rebuild (in progress)

Decided: rebuild README as an **adoption on-ramp** (not a navigation TOC). Headline first win = (a) `pkit init` → governed structure appears (one command, immediate). (b) file/move an issue through the governed workflow → moved to **next steps** (it needs capability install + bootstrap — too heavy to be the front-page win; ceremony-before-value, cf. F3). Code-review (c) deferred behind a hidden `<!-- TODO -->` until the comment/review format (#756/#757) lands.

### Decided: communicating `pkit` (the CLI) vs `.pkit/` (the installed methodology)
- **Lead plain:** "`pkit` is the command you install once (globally); `.pkit/` is the methodology it installs into each project — the `pkit` command operates on it."
- **Git analogy as a follow-on note** for anyone who wants more: "like `git` and `.git/` — one tool, a per-project directory it operates on."
- **Two-version nuance** (CLI version vs project `backbone_version`, pin/router) stays **out of the front door** — depth docs only, so it doesn't re-load the confusion it's meant to dissolve.

### README design — settled so far
- Shape: adoption **on-ramp**, not navigation TOC.
- Sections: (1) title+one-line what · (2) why/hook incl. honest "why not just ask Claude" · (3) **install** (`uv` prereq → `uv tool install git+ssh://…` → verify) · (4) **headline first win: `pkit init`** → structure appears + `pkit status` · (5) mental model (4–5 building blocks) · (6) next steps by role (incl. the issue-workflow win (b)) · (7) depth links · hidden `<!-- TODO(c) -->` for code-review.
- CLI-vs-`.pkit/`: plain + git note (placement TBD — likely a short callout right after install, or top of mental model).
- **§2 hook — SETTLED (honest-investment positioning; survived a critic stress-test):**
  - Spine: pkit isn't an alternative to Claude generating things — it's the *maintained, safe-to-update home* for that setup, so it doesn't rot and never fights your files.
  - Lead differentiator (answers "but I own my ad-hoc setup"): a hand-rolled CLAUDE.md/agents rots (nobody improves it; a fix in project A never reaches B; no safe update channel). pkit is that channel — and you keep everything you write (maintains only its own files, only on `sync`, structurally can't touch/conflict with yours).
  - "loads at session start" → demoted to table-stakes; real moat is the *coherent maintained set* (agents+skills+rules+gates), not a one-off you babysit.
  - Own the cost: real path (`uv` → `uv tool install git+…` → `pkit init`) + one concept (CLI vs `.pkit/`) + bounded estimate (~5 min, 3 commands). Don't hide the setup cliff.
  - "enforced" scoped to truth: structural checks CI can run (id-uniqueness, migration coverage, file-ownership, permission-gated mutations); +real PR merge gate *if* project-management installed. No claim of the deferred process enforcement.
  - Concession → qualifying threshold placed *after* value: "pays for its setup when work repeats / must survive a new session / spans projects-people; for a true one-off you won't feel it." (no upstream exit ramp)
  - Net shift: from "immediate wins that beat ad-hoc" (they honestly don't) → "the one thing ad-hoc can't give + the exact small cost + when it's worth it."
- Still to brainstorm: the **4–5 mental-model building blocks** (§5).

**F7 — Doc staleness is systemic, not just the README.**
The feature-inventory pass found the project-management capability README prose still says "v0.2.0 / migrations empty" while the manifest is v0.54.0 with populated migrations; software-engineering carries an older schema_version reference. Same class as F6 (docs drift from shipped reality) — so "rebuild/review docs from the ground" is broader than README.md; the capability READMEs need a currency pass too. Candidate: a doc-currency check, or generate version/status lines from the manifest rather than hand-writing them.

**F8 (strategic) — pkit's honest *immediate* differentiator over ad-hoc Claude is thin; the value is genuinely back-loaded.**
critic stress-test of the hook showed every "immediate proof" fails one of {immediate, differentiated-from-ad-hoc}: session-start loading is a native harness feature (not a moat); safe/maintained updates are real+differentiated but felt only on the 2nd sync; opt-in loses "minimal" to ad-hoc. The one true differentiator — a *maintained, safe-to-update channel that never touches your files* (no-shared-files) + *you keep everything you write* — is back-loaded and was buried.
Implication for adoption strategy: **do not fake immediacy.** The honest play is (1) drive setup cost to near-zero (the friction work), (2) frame pkit as an *investment* with a clear payoff threshold (repeats / survives a new session / spans projects-people), (3) answer the real objection ("I own my ad-hoc setup") head-on: pkit maintains only its own files, only on your command, and structurally can't overwrite yours. The colleague quit because cost was high AND immediate payoff invisible — spin can't fix that; only low cost + honest investment-framing can.

## Docs-that-stick levers (PERSIST — review all docs against these)

*Pattern extracted (COR-007) mid-README-work: a reusable docs-quality discipline.*

**Carrier — DECIDED: a doc now; let recurrence pull it up (do NOT ship as a capability).**
Rationale = pkit's own principles: COR-007 (extract on recurrence, n≈1 today → a capability now is speculative generality); COR-006/017 (a capability is a heavyweight discipline-bundle — wrong shape for 7 principles + a checklist); COR-014 (writing docs well is universal → core, not a project capability).
- **Now:** a **doc** — "Writing docs that stick" (the 7 levers as a reference guide). Cheapest carrier that holds the value; commits to nothing.
- **On recurrence** (applied to a few docs, proves useful): promote to a **skill** an agent runs, OR — lighter — feed the levers as knowledge the existing `software-engineering` **`docs-reviewer`** reads via the `<project-conventions>` corpus (the seam ADR-052 just repaired). No new capability needed for that path.
- **Only if it earns real weight** (own schemas/scripts/release cadence/cross-adopter demand): reconsider a dedicated carrier — and even then likely **core**, not an opt-in capability.
- **Review-all-docs-against-it** = a **Task** (under EPIC #775), separate from the doc.
- Meta (a genuine for-pkit argument, lived): the framework stopped us over-building here in real time — same class as F3 (ceremony before value).

1. **Anchor to an existing schema (analogy)** — map new concepts onto something the reader already models deeply; strength = *structural* mapping, not surface; fence where the analogy leaks.
2. **Curiosity gap / problem-first** — open with the felt pain so the concept arrives as the answer to a question they're already asking ("the hook inside").
3. **Concreteness + worked example** — show the actual tree/commands/before-after; abstraction floats, instances stick.
4. **Experience before model (ordering)** — a model explaining something you've *done* sticks; put mental model AFTER the first-win.
5. **Cognitive load / chunking (~4 max)** — chunk the pieces under one unifying metaphor so they're one chunk, not many.
6. **Honest emotion = recognition + relief + trust** — use recognition ("that's exactly my pain") and honesty-as-disarming; never hype/FOMO (repels, esp. at our honesty bar).
7. **Dual coding** — a small diagram/tree beside the words ~doubles retention.

## Core analogy (DECIDED): package-manager for your project's methodology
- backbone = the runtime/tool · capabilities = **packages you install** · no-shared-files = *you never edit installed packages, they never edit your code* · versioning = *lockfile + upgrade + migrations*.
- Fence (where it leaks): pkit installs **readable content into your repo**, not a hidden vendor dir.
- Chunks all four §5 building blocks onto one deep dev schema (lever 1+5).

## Docs principle (DECIDED): core stands alone, illustrated by real capabilities
- Explain the CORE abstractly (package-manager model needs no specific capability). Then anchor with a real worked example (`pkit capabilities install project-management` …) per lever 3. Core must be *separable* — "PM is one instance," never "you must know PM to get pkit." Use the most relatable capability (PM / code-review) for examples.

**F9 — the local-agent reviewer is non-deterministic; a defect can slip a lucky re-review.**
Observed while merging the README (#778): `docs-reviewer` posted CHANGES_REQUESTED on a "one-owner file invariant" over-claim, then on a re-run posted APPROVED on the *identical* content (a failed commit meant nothing had changed). Same input, opposite verdict.
Implication: local-agent review (DEC-028 local path) is *attestation*, not a deterministic gate — a real defect can pass if a re-review happens to miss it. Mitigations to weigh: (a) don't merge on an APPROVE that reverses a recent block without an independent human/second-pass confirm; (b) determinism aids — lower temperature / structured checklists in the reviewer contract; (c) the item-4 review-output rework (one combined, data-backed pass) reduces the surface. Also a for-the-README honesty point: "local review is attestation" must be stated plainly, not sold as a hard gate. Practical guardrail used this time: I merged only because the fix was *independently verifiable* correct, not because the reviewer flipped to APPROVE.

**F10 — the README teaches the wrong interaction model (CLI-by-hand vs agent-mediated).**
The new README's next-steps says "…then file and move issues through a governed workflow (`pkit project-management …`)" — implying the user hand-runs CLI subcommands. That's wrong. The real model: run `claude` in a pkit-init'd folder → it boots under the **`project-manager` agent** (the default agent), which is the *interface* to project-management; you converse, the agent runs the governed commands. You should NOT run `pkit project-management …` manually. Parallel: the **software-engineer** agent for the developer side.
Fix: the README (and the how-to-use docs) must teach the **agent-mediated** usage model — "you talk to an agent, it drives the governed tooling" — not CLI-by-hand. This is the seed of **"the next half of the story": how to USE pkit** (as a PM via project-manager; as a dev via software-engineer). Deferred by the maintainer for a later pass.
Meta-finding on review coverage: `docs-reviewer` passed this — it verifies *accuracy* (does the doc contradict the code) but not *usage-model correctness* (is this the intended way to use it). The panel has a blind spot for "right mental model," a distinct axis from "factually true."

**F11 (SERIOUS footgun) — `pkit init` silently installs into the *enclosing* git repo, not your CWD, when the CWD isn't its own repo.**
Did: made an empty folder `git-public/pkit_test`, `cd`'d in (did NOT `git init` it), ran `pkit init`. Expected: init into the current empty folder. Got: init resolved the project root via `git rev-parse --show-toplevel`, walked UP to the enclosing repo `git-public`, and installed/re-merged there — `.pkit/` core content, `.claude/settings.json` backed up (`.pre-pkit`) + merged, `.gitignore` rendered — mutating a directory the user did NOT intend.
It DID print "Installing project-kit into <git-public>", but there is no active confirmation gate when resolved-root ≠ CWD — the alarming fact rides by as a normal status line.
Severity: first hands-on step immediately hit a dangerous, real-file-mutating footgun — exactly what scares/loses an adopter (and could clobber a real enclosing project). The `.pre-pkit` settings backup is the one saving grace.
Fix candidates: (a) when resolved-root ≠ CWD, CONFIRM before mutating ("about to install into X, not your current folder — proceed?"); (b) refuse when CWD is not a git root unless `--here`/explicit target; (c) at minimum a LOUD warning, not a passing status line. Also: `git init` shouldn't be a hidden prerequisite for "init in this folder."
