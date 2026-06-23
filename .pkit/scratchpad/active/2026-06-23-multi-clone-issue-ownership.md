---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-23
---

# Multi-clone issue ownership

## The question

When **one person** runs **several clones of the same repo**, each with its own `project-manager` session, GitHub shows the same human as assignee on every issue — so neither session can tell which in-flight issue is "owned" by which clone. How should the project-management capability let concurrent clone-instances of a single user distinguish, claim, and respect each other's in-flight work — **without** forcing this complexity on the common single-clone case?

## Forces

- **Single-clone must stay zero-ceremony.** The feature is opt-in; default-off. A solo user with one clone should never see an instance marker, a block, or a filter. (Mirrors the small-adopter-shortcut posture elsewhere in the capability.)
- **Cross-clone visibility requires a shared substrate.** For clone B to know clone A holds an issue, the ownership signal must live on GitHub (the shared substrate per [project-management:DEC-003-github-bound-substrate]), not in either clone's local filesystem.
- **Instance identity is inherently clone-local.** "Which clone am I?" cannot come from the shared repo — it must be configured per working copy and is meaningless to commit.
- **Advisory, not a lock.** GitHub labels/fields are not atomic; two instances can race. The mechanism can *reduce* collisions and make ownership legible, but it cannot be a hard mutex. Blocks are best-effort guards, not guarantees.
- **It rides existing lifecycle verbs.** Claim/release should happen "under the hood" inside the verbs that already mutate state (`start-work`, `handoff-issue`, close/merge) per [project-management:DEC-026-work-ownership-lifecycle], not as a new manual step.

## What's already known / constrained

- **The `user@instance1` assignee form is not possible on GitHub.** GitHub assignees must be real accounts; you cannot assign to a synthetic `user@instance1` handle. So instance identity has to be carried by a *second* signal layered on top of the single real assignee — a label, a Projects v2 field, a body marker, or a comment — **not** by encoding it into the assignee. (This is the first thing the user's sketch needs to bend around.)
- **The capability already has a label-fallback substrate** for classification axes ([project-management:DEC-012-classification-axes]) and a Projects-v2-or-labels split — an instance marker can reuse that machinery.
- **Team membership already sub-divides "who"** ([project-management:DEC-021-team-membership-gate]); an instance marker further sub-divides a single member's *sessions*. Worth checking the interaction.
- **The clone-local config is a runtime-local file** — exactly the class the `.pkit/.gitignore` `runtime_ignore:` renderer just shipped (EPIC #154 / ADR-009 Amendment 1) was built for. The per-clone instance-id file should be declared `runtime_ignore:` so it's never committed. (Nice reuse — no new ignore mechanism needed.)

## Candidate substrate for the instance marker (Decision D1)

- **(a) GitHub label** `instance:<id>` (parallel to `state:*`, `workstream:*`). Pro: reuses the label-fallback substrate, visible in the UI, filterable via `gh issue list --label`, easy to add/remove. Con: labels are repo-global and shared — adding/removing churns the label set; needs a created label per instance.
- **(b) Projects v2 single-select field** `Instance`. Pro: structured, doesn't pollute labels. Con: only works for adopters on a board; heavier; project-kit itself runs label-fallback.
- **(c) Body marker line** (e.g. `Instance: <id>` near the parent-ref). Pro: no label/field plumbing. Con: not filterable by `gh`, easy to miss, fights the body-format rules.
- **(d) A tracking comment.** Pro: carries history (who claimed when). Con: not filterable, noisy.

Leaning (a) label for the label-fallback path, with (b) as the board-substrate equivalent — mirroring how the capability already splits Priority/Workstream. **Open.**

**RESOLVED (2026-06-23): (a) GitHub label.** A bounded, pre-created pool of `instance:<N>` labels (default **4** → max 4 parallel instances of one user; enough for the use case). Refinements agreed/noted:

- The instance label is only meaningful **in combination with the assignee** — `instance:2` + assignee `alice` = alice's clone #2. So the pool is implicitly per-assignee; if two humans each run multiple clones, the disambiguator is the `(assignee, instance:N)` pair, not the label alone. Clean for the stated single-user case.
- The labels are **created only when the feature is enabled** (the opt-in gate, D7) — *not* at default `bootstrap`, so single-clone adopters never see them.
- Pool size defaults to 4 but is a candidate knob in the shared config (cheap to make the count configurable; default 4).
- Board-substrate equivalent (an `Instance` single-select field) deferred — project-kit runs label-fallback, so the label path is what gets dogfooded.

## Other open decisions (to brainstorm in sequence)

- **D2 — Instance identity & config split.** Shared committed config carries the *feature-enabled* flag (and maybe a registry of known instance ids + human-readable names); clone-local config (gitignored via `runtime_ignore:`) carries *this clone's* id. How is the id minted — user-chosen name, auto-UUID, derived from worktree path? Who validates uniqueness?

  **RESOLVED (2026-06-23): user explicitly sets the clone's instance number; no auto-minting, no prompt-gate.** The user tells the agent "you are instance 2"; the agent invokes a paired skill → command that writes the number into the **clone-local, gitignored config**. Consequences agreed:
  - **Unset = legacy behaviour.** A clone with no instance number behaves exactly as today: it does not tag, does not block, is not filtered — "the same mess until now." Protection exists only *between clones that have each set a number*. The user explicitly accepts that an unset clone has no guard. This makes **the presence of a clone-local instance id the de-facto activation gate** — folding most of D7 into D2.
  - **Minting:** user-chosen integer in `1..pool` (default pool 4, per D1). Uniqueness is **not enforced**, only best-effort warned (the command can check whether issues are already tagged `instance:N` under this assignee from elsewhere). Trivial mental model: "this terminal is instance 2."
  - **Carrier for the set action:** a small paired skill + `pkit project-management set-instance <N>` command (per [pkit:COR-005] skill/command pairing), writing the clone-local config. Optional friendly-name field deferred unless listing UX (D5) wants it.

  **D2a RESOLVED (2026-06-23): (i) no shared committed config.** Nothing new is committed to the repo. The `instance:N` labels are created **lazily** the first time any clone runs `set-instance` (create-if-absent, idempotent). Pool size is a default (4) baked into the command. Rationale: clones coordinate through the labels on GitHub — the real shared substrate ([project-management:DEC-003-github-bound-substrate]) — so they never need a committed file to agree. The whole feature's persistent state is: (1) the per-clone gitignored id, (2) the `instance:N` labels on GitHub. The friendly-name nicety can return later if D5 wants it. This also means the feature ships **without touching `bootstrap`** — pure additive, label pool materialises on demand.
- **D3 — Claim/ownership lifecycle.** When is an issue claimed (on `start-work` → in-progress?) and released (on merge/close, or `handoff-issue`)? Does claiming require the human to also be the assignee, or is the instance marker independent?

  **RESOLVED (2026-06-23): claim at CREATION — an instance owns a *realm*, not just its active work.** The instance stamps `instance:<my-id>` at `create-issue`, so an issue belongs to its creator's realm from birth — through Todo → Backlog → In Progress, not only the In-Progress window. Rationale (user): pm instances pick work off the **backlog**, so they must be able to tell, *while it sits in backlog*, which items are another instance's realm and "not intended for them." Claiming only at start-work would leave the backlog ambiguous — the exact problem. Model agreed:
  - **Primary claim = creation.** `create-issue` stamps the creating instance's label.
  - **Secondary claim = start-work on an *unclaimed* issue.** Issues born outside any instance (legacy, human-created via the GitHub UI, or filed before the feature was enabled) are an unclaimed **commons**; an instance taking one stamps it at `start-work`. So start-work still claims — but only when the issue has no realm yet.
  - **Release = terminal transitions** (`done-work` merge, `close-issue`) **+ explicit `handoff-issue`** (which re-stamps to the new owner — D6).
  - **Assignee coupling = (a) coupled.** `create-issue`/`start-work` already set the invoker as assignee, so the owner is the `(assignee, instance:N)` pair; you don't claim what you're not assigned. One owner concept, no second disagreeing signal.

  **Revises the closure-cascade pin (see Upstream alignment).** Under "claim = active work" the lean was *leaf-only* (containers unclaimed). Under "claim = realm from creation" that flips: when an instance files a whole arc (EPIC + Features + Tasks, as in a batch-plan), **the whole tree is that instance's realm** — so containers ARE claimed at creation too. The cascade still closes containers normally; release-on-close strips the creation-set label.

  **CONFIRMED (2026-06-23): whole tree by default, but reclaimable per the distribution need.** A filed arc is its creator's realm end to end (containers + leaves). BUT the realm is not frozen — the user must be able to **redistribute work** across instances (e.g. file an EPIC + 5 Tasks as instance 1, then hand 3 Tasks to instance 2). So the instance label is per-issue and re-stampable; "whole tree" is the *default at creation*, not an immovable block. This makes D6 (reclaim/transfer) load-bearing, not optional — see below.
- **D4 — Conflict behaviour.** When this instance acts on an issue marked owned by another instance: hard block, block-with-override, or warn-and-proceed? What severity token ([project-management:DEC-014-validation-severity-model])?

  **RESOLVED (2026-06-23): bypassable-with-audit.** An *ordinary* lifecycle verb (`start-work`, `done-work`, `edit-issue`, `move-issue`) acting on an issue in another instance's realm is refused by default but proceeds with `--bypass "<reason>"`, posting an audit comment recording that instance N acted on instance M's issue ([project-management:DEC-014-validation-severity-model] `bypassable-with-audit`). Rationale: matches the "advisory, not a hard mutex" force — labels race, so a hard-reject would give false confidence; bypassable leaves a trail when realms are crossed and keeps an honest escape hatch, while the default is "stop, not yours." The clean alternative to bypassing is to **reclaim** it (D6 pull), which removes the conflict rather than overriding it. Scope: applies ONLY to ordinary verbs; the reclaim gestures (push/pull, D6) are exempt — they are the sanctioned cross-realm path. Unclaimed-commons issues are not in any realm, so they trigger no guard.
- **D5 — Listing UX.** Auto-filter listings to this instance's issues, or show all with a "mine / other-instance / unclaimed" sign? A flag to see everything?

  **RESOLVED (2026-06-23): show all, signed; `--mine` to narrow.** Listings show every issue, each line annotated by realm — `● mine` / `○ instance N` / `· unclaimed` — with a `--mine` flag for focus. Rationale: directly serves the motivating need ("be aware which are mine vs someone else's") without hiding anything; the D4 guard already prevents *acting* on another realm by accident, so listings needn't *also* hide them — and seeing another realm's in-flight work is exactly what's needed to decide whether to reclaim a stalled clone's tasks (D6 pull). Auto-filter was rejected as optimising focus at the cost of the visibility that motivated the feature. Signing applies only when the feature is active (a clone-local id is set, per D2/D7); otherwise listings are unchanged.
- **D6 — Reassignment / transfer.** If another instance (or a different human) takes an issue, the old instance marker must be cleared/replaced. What's the transfer gesture, and does it tie to assignee change?

  **RESOLVED (2026-06-23): both push and pull are first-class reclaim gestures, via `handoff-issue`.**
  - **Push (owner gives):** `handoff-issue #X --to-instance 2` — the current owner re-stamps its own issue to another instance.
  - **Pull (taker takes):** `handoff-issue #X --to-instance self` (or a `claim` alias) — an instance reclaims an issue from another realm to itself.
  - **Granularity:** single issue + **subtree** (`--recursive` hands a whole branch in one gesture, mirroring whole-tree claim-at-creation). No arbitrary multi-select.
  - **Assignee tie:** for the same-human-multiple-clones case the GitHub assignee stays the same human; only the `instance:N` label flips. For a cross-human handoff, both the assignee and the instance label change (handoff-issue already reassigns per [project-management:DEC-026-work-ownership-lifecycle]).
  - **Key consequence for D4:** because reclaim (both directions) is now the *sanctioned, explicit* cross-realm path, D4's "block" is **not** about reclaim — it is only about **accidental ordinary mutations** (start-work, done-work, edit, move) on an issue sitting in another instance's realm. The two are different gestures: reclaim crosses realms on purpose; ordinary verbs stepping on another realm are the thing to guard. This cleanly reconciles "I want to take others' work" (pull, allowed) with the original "block if it's another instance's" (ordinary verbs, guarded).
- **D7 — Default-off activation gate.** Exactly what turns the feature on (shared flag present + clone-local id set?), and how do the scripts no-op cleanly when it's off?

  **RESOLVED (2026-06-23): folded into D2 — activation = a clone-local instance id is set.** No separate flag (D2a dropped the shared committed config). A clone with no instance id behaves exactly as today: `create-issue` doesn't stamp, the D4 guard doesn't fire, listings aren't signed, the `instance:N` labels are never created. The scripts no-op by reading the clone-local config once and short-circuiting the whole feature when it's absent. Single, legible on-switch: `set-instance <N>`.

## Upstream alignment (2026-06-23 pull → pm at 1.114.0)

A pull landed two pm decisions that reshape the substrate this feature rides. Neither blocks the design, but they sharpen three points and surface one naming hazard.

- **Lifecycle verbs now delegate state to the process engine ([project-management:DEC-033-rebind-issue-lifecycle-onto-process-substrate]).** `start-work` / `handoff-issue` / close still exist, but state-machine mechanics (position, transitions, journal) now live in the engine; the verbs keep their *pm-domain side-effects* (branch creation, assignment, cascade). **Consequence for D3:** the instance-claim/release is a **pm-domain side-effect** layered on those verbs — exactly like branch-creation — *not* engine/process state. The instance marker must stay out of the engine so the shared substrate stays content-free (DEC-033 D3). This actually strengthens the "rides existing verbs" force (line 19): we hook the same pm-domain seam branch-creation already uses.

- **Naming hazard — do NOT call the instance concept "membership."** The pull added [project-management:DEC-034-cascade-slot-binding] binding pm's closure cascade to the shared cascade slot ([pkit:COR-037-process-cascade]), with `cascade-members.py` / `cascade-membership.py`. So "membership" now has **two** load-bearing meanings in this capability: (1) *team* membership — who may mutate ([project-management:DEC-021-team-membership-gate]); (2) *cascade* membership — "is this issue a child of that parent," for the closure fold (DEC-034). The line-25 note ("team membership sub-divides *who*") still holds, but the eventual DEC must name our concept **instance ownership / instance claim**, never "instance membership" — three colliding "membership" terms would be a mess. (The `(assignee, instance:N)` framing in D1 already reads as *ownership*, so this is a wording discipline, not a redesign.)

- **Closure-cascade interaction for D3/D6.** Parents can now reach `done` via the COR-037 closure fold (all children done → parent eligible). A parent that auto-closes via the fold isn't "claimed by a clone" the way an in-flight leaf is. **Pin when D3 is decided:** instance labels live on *claimed in-flight* issues (the start-work→done window per D3), and the release-on-close path must also strip the marker if a *parent* carried one — but cascade-driven parent closure should not try to attribute an instance. Lean: only leaf/working issues get claimed; containers stay unclaimed. Confirm at D3.

- **Unaffected, re-verified:** DEC-003 (substrate), DEC-012 (classification/labels), DEC-014 (severity), DEC-021 (team membership), DEC-026 (work-ownership lifecycle), and the `runtime_ignore:` clone-local-config reuse (now shipped) are all intact post-pull. D1/D2/D2a stand unchanged.

## Resolved design (D1–D7) — one-paragraph summary

Opt-in, default-off, activated solely by setting a **clone-local, gitignored instance id** (`set-instance <N>`, pool default 4). Ownership is carried by a GitHub **`instance:N` label** (created lazily on first use; the `(assignee, instance:N)` pair is the owner) — never the assignee handle (impossible on GitHub), never a committed config. An instance owns a **realm**: issues are stamped at **creation** (the whole filed tree — containers + leaves), with `start-work` claiming **unclaimed-commons** issues (legacy / human-filed / pre-feature). Released on terminal transitions + `handoff-issue`. Work is redistributed by **reclaim — both push (`--to-instance N`) and pull (`--to-instance self`), single or subtree (`--recursive`)** — the sanctioned cross-realm path. Ordinary lifecycle verbs acting on **another** realm's issue are **bypassable-with-audit** (reclaim is the clean alternative). Listings **show everything, signed** by realm (`● mine / ○ instance N / · unclaimed`), `--mine` to narrow. Naming discipline: the concept is **instance ownership**, never "membership" (collides with DEC-021 team membership and DEC-034/COR-037 cascade membership).

## Status

**Design complete — D1–D7 all resolved.** Aligned to pm 1.114.0 (post DEC-033 rebind + DEC-034 cascade-slot-binding). Ready to crystallise. Next: run the resolved design past `critic` (and `architect` — it adds an ownership axis, touches the post-rebind verb seam, introduces a clone-local config, and adds a write-side stamping path across `create-issue` / `start-work` / `handoff-issue` / listing); then author a pm `DEC-NNN` (**instance ownership**) via `decision-author` and slice the implementation into an EPIC + Tasks (batch-plan), retiring this note with `pkit scratchpad done multi-clone-issue-ownership --produced DEC-NNN`.
