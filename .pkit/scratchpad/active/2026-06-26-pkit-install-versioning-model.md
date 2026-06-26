---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-26
---

# pkit install / versioning model — how `pkit` should resolve and stay coherent

## The question

When one developer juggles **several project-kit source checkouts** *and* **several
adopter projects** on one machine, what should `pkit …` resolve to in each place, and
how do we keep the two version axes — the **binary** (the code that runs) and the
**project content** (`.pkit/`, including the agent prompts) — from drifting into a
broken mismatch?

This note fixes the *desired behaviour* first, then scores our in-flight mechanisms
(the `pkit-router`, the pinned `uv tool` install, the sync/upgrade flow) against it, so
we can tell whether the plans actually lead where we want.

## P0 — the guiding principle: implementation tech is invisible to adopters

**An adopter installs and uses pkit without ever needing to know it's built on Python or
uv.** They don't think about interpreters, virtualenvs, `uv tool`, wheels, or PATH — the
same way you install and use `git` or `docker` without caring what they're written in. An
adopter just wants pkit to work smoothly; the technology should be hidden wherever
possible. This is the experience bar; everything below is *means to it*.

**This is an audience claim, and it revisits PRJ-004's premise.** PRJ-004 chose "Python
tool via `uv tool install`" on the stated assumption that adopters are "people who already
have GitHub auth and already know where the repo is" — a small, uv-aware audience — and
rejected a curl-bash installer because *"we don't need the ease."* P0 asserts a *broader*
audience (people who neither know nor care about Python/uv). That doesn't break PRJ-004;
it **revises the premise PRJ-004 rested on**, which is a legitimate trigger to reopen it.

### How far to hide — the cost ladder

| Level | What the adopter sees | Cost | Decision impact |
|---|---|---|---|
| **0 (today)** | `uv tool install git+ssh://…`; must install uv first, must know the URL | none | current PRJ-004 |
| **1 — branded one-liner** | one command "to install pkit"; internally checks/installs uv + runs `uv tool install` | small | **reopens PRJ-004** (it's the curl-bash PRJ-004 rejected) |
| **2 — native packages** | `brew install pkit`, `winget install pkit` — feels like any app | tap/registry infra, per-platform | PRJ-004 *deferred* these to a scale threshold |
| **3 — standalone binary** | one `pkit` executable, no Python/uv visible at all | repackage distribution (PyInstaller / PyOxidizer-class) | rewrites the PRJ-003/004 distribution model |

Higher = more infrastructure. (Caveat discussed: this isn't a clean linear "more hidden"
axis — these are partly different *delivery channels*, and even the standalone binary can't
hide `git` / a POSIX shell / `gh` that pkit shells out to. So "fully invisible" isn't
reachable by climbing; treat the table as a menu of channels, not strict rungs.)

**Operator decision (discussed, plain English): the target is "paste one line and it
works."** One command the user copies; it checks/installs uv if missing, then installs pkit;
they never type `uv` or the git URL. This is the download-and-run style PRJ-004 once rejected
("our users are techies, they don't need it") — choosing it now is a *deliberate reversal*
justified by the changed audience (non-technical adopters), to be recorded as a PRJ-004
successor. Two settled points:
- It is the install experience for *adopters/broad audience*, not the operator's own daily
  unblock (that's the floor fix).
- "Paste one line **and it works**" *requires* the floor fix (#333): the one-liner installs
  fine today, but the user's first real command (`pkit init`) is exactly what crashes — and
  a smooth path straight into a traceback is the worst failure for a non-technical audience.
  So: **floor fix first, one-liner as the next layer on top.** The one-liner itself is small
  once the floor is solid; deferred to "before broad distribution."

### Two caveats — invisibility is the *top* of the stack, not a substitute for the floor

- **Windows runtime still needs a POSIX shell.** Even a flawless installer can't make
  `init`/`sync`/`upgrade` run without bash (the adapter primitives + migrations, Layer 2
  below). Hiding uv at *install* time doesn't hide the bash dependency at *runtime*.
- **The wheel gap is the floor.** A smooth installer that lands a pkit which then can't
  `pkit init` (B4) isn't smooth. P0 sits *on top of* fixing B4–B6, not instead of it.

### Note on the "auto-install uv" / bootstrap-script idea

The no-clone adopter path **already exists** — `uv tool install git+ssh://…` makes *uv*
fetch + build; the adopter never clones. So a bootstrap script is **not** needed for
no-clone; its only residual job is *hiding/auto-installing uv* (Level 1 above). An
**in-repo** bootstrap script is rejected by principle (it reintroduces a clone). A
**network-fetched** one delivers Level 1 but is exactly PRJ-004's rejected curl-bash → it
must be a deliberate PRJ-004 successor, sequenced after the wheel gap. Most of what such a
script would do (`install-or-replace`) is already `uv tool install --force`.

## Two version axes (the core mental model)

- **Binary version** — the code executing `pkit …`; what agents shell out to. One
  pinned `uv tool` install per machine (plus per-checkout working trees in dev).
- **Project version** — the data: schemas, decisions, workflow, **and the deployed
  agent prompts**. Lives in each adopter's `.pkit/` tree (`.pkit/VERSION`).

An agent's *behaviour* is the project version; the `pkit` it calls is the binary
version. "Mismatch" = those two disagree for a given project.

## What we want (target behaviour)

1. **In a pkit source checkout**, bare `pkit` runs *that checkout's* working tree — so
   dev edits are live, per-CWD, across simultaneous checkouts.
2. **In an adopter project**, bare `pkit` runs a **stable** pkit that does *not* shift
   when I edit any dev checkout.
3. **Works in non-interactive agent shells** (the real consumer), not just interactive
   terminals.
4. **The official (recommended) adopter install can run the full adopter lifecycle** —
   `init`, `sync`, `upgrade` — not just read/operational commands. (This is the
   PRJ-004 promise.) "Official install" = `uv tool install git+ssh://…`, the one
   sanctioned method per PRJ-004 (it retired the `git clone` + symlink workaround).
5. **Version coherence is observable and the safe direction is the easy one**: I can see
   binary-vs-project drift, and the recommended remedy never wedges a project.
6. **Upgrading an adopter is a sanctioned, documented flow** that doesn't depend on
   knowing the router's internals.

## What we know (verified this session)

- The router (`scripts/pkit-router`) delivers 1–3: source-tree anchor = presence of
  `scripts/pkit-router` at repo root (adopters don't have it → fall through to pinned).
  Proven across six branches + a real adopter dir. ✓
- **The pinned `uv tool` binary cannot `init`/`sync`/`upgrade`.** The wheel ships only
  `src/project_kit` + the `VERSION` file (force-include), **not** the `.pkit/` tree;
  `find_source_kit()` is a pure filesystem walk (`<package>/../../.pkit`) with **no
  `importlib`/package-data fallback**. Empirical: pinned `pkit init` →
  `Error: source kit not found at …/uv/tools/project-kit/lib/python3.13/.pkit`. ✗ (breaks #4)
- `pkit upgrade` semantics (per the CLI README): compares the project's recorded core
  version against the version the CLI was built from, runs migrations, then `sync`s.
  **Refuses if the project is ahead of the CLI.** So it brings a project *up to the
  binary's version* and can't run from the pinned (no source) anyway.
- PRJ-004 (accepted) makes `uv tool install git+ssh://…` the official, *only* sanctioned
  adopter install, explicitly meant to retire the `git clone + .pkit/cli/pkit` bootstrap.
  The CLI README claims the binary "works against any adopting project" and lists
  `init`/`sync` — which contradicts the verified gap above.

## Failure modes when binary ↔ project drift

- **Project NEWER than pinned binary** (agents on v+1, pinned at v): older code reads
  newer schemas/states → `KeyError`-class failures, spurious validation errors, refusing
  valid transitions. And the normal remedy is blocked — `pkit upgrade` *refuses* when the
  project leads, and the pinned can't sync anyway. → **wedged.**
- **Project OLDER than pinned binary**: newer code against older content → errors or
  silently-applied new defaults the project never adopted. The intended fix (`pkit
  upgrade` to migrate up) **can't run from the pinned** (no source) → must drive from a
  checkout.
- **One pinned, many adopters at different `.pkit/` versions**: some adopter is always
  mismatched the moment versions diverge.
- **Dev tree can shove an adopter ahead of the pinned**: upgrading an adopter from a
  bleeding-edge checkout jumps its `.pkit/` to v+1 while the machine pinned stays at v.
- **Latent today**: everything is `1.124.0`, so nothing mismatches yet. The surface is
  hidden until working tree / `main` / pinned diverge.

## Desired-behaviour checklist (the bar to test plans against)

- [ ] **B1** Source checkout → bare `pkit` runs that checkout's working tree.
      *(router: DONE & verified)*
- [ ] **B2** Adopter → bare `pkit` runs a stable binary, immune to dev edits.
      *(router: DONE & verified)*
- [ ] **B3** Works in non-interactive agent shells. *(router: DONE & verified)*
- [ ] **B4** Official adopter install (`uv tool install`) can `init`. *(BROKEN — gap)*
- [ ] **B5** Official adopter install can `sync`. *(BROKEN — gap)*
- [ ] **B6** Official adopter install can `upgrade` (migrations + sync). *(BROKEN — gap)*
- [ ] **B7** Binary-vs-project drift is observable (a `pkit version` vs `.pkit/VERSION`
      check, ideally one command). *(partial — two manual reads today)*
- [ ] **B8** The safe drift direction (pinned ≥ project) is the documented default and
      the easy path; the wedging direction is prevented or clearly flagged. *(undocumented)*
- [ ] **B9** Adopter upgrade has a sanctioned, documented flow that doesn't require
      router internals. *(undocumented; today implicitly needs a checkout)*
- [ ] **B10** PRJ-004 + CLI README accurately describe what the pinned binary can/can't
      do (no false "works against any project" claim). *(currently contradictory)*
- [ ] **B11 (P0)** An adopter installs + uses pkit without needing to know it's Python/uv
      — tech hidden behind a branded experience (Level ≥1 on the P0 ladder).
      *(not met — Level 0 today; needs a PRJ-004 revisit)*

## Do our current plans lead the right way?

| Want | Mechanism in play | Verdict |
|---|---|---|
| B1–B3 | `pkit-router` (merged) | ✅ met & tested |
| B4–B6 | *(none yet)* — the wheel-omits-`.pkit/` gap | ❌ blocked; **needs the gap fix** |
| B7 | `pkit:which` (binary side only) | 🟡 partial — doesn't surface project `.pkit/VERSION` |
| B8–B10 | docs + PRJ revisit | ⬜ not started |
| B11 (P0) | none — Level 0 (`uv tool install`, tech exposed) | ⬜ not started; **PRJ-004 revisit** |

**Read:** the router half points the right way and is done. The versioning half does
**not** yet reach the target — B4–B6 are structurally blocked by the packaging gap, and
B7–B10 are unwritten. So the plans are *directionally right but incomplete*; the router
solved routing but exposed (didn't cause) the deeper versioning-coherence gap.

## Fix direction for the gap (B4–B6) — RESOLVED via critic + architect

Options weighed: (1) **bundle content into the wheel** + resolve via `importlib.resources`;
(2) fetch source at upgrade time (heavier, reintroduces network/auth — rejected); (3) revise
PRJ-004 + README to declare the tool install operational-only (concedes the gap, contradicts
P0 — rejected). **Option 1 chosen.** It makes `uv tool install` deliver the PRJ-004 promise
*and* collapses a drift axis (binary version == content version by construction), and it's
the foundation every higher P0 ladder level reuses (native packages, standalone binary all
still ship content with the code + resolve it as a package resource).

**Reviewer-corrected shape (the floor fix, #333):**

- **Bundle the *propagation surface*, not "the `.pkit/` tree."** The wheel bundles *what
  `pkit sync` propagates* — under `project_kit/_kit/` — which by the existing core/project
  ownership rule automatically *excludes* adopter-owned subtrees: `decisions/project/` (PRJ
  records — project-kit's own, must not ship as core), `scratchpad/{active,done,dropped}`
  contents, the maintainer's `manifest.yaml`, `.gitignore`, `__pycache__`. Defining the
  bundle this way means it can never drift from what sync actually copies.
- **Critic red flag — the bundle set is bigger than `PROPAGATED_AREAS`.** `capabilities/`
  and `migrations/` are read from `source_kit` but are NOT in the 10-area propagation list.
  Bundling only those 10 would leave a pinned install unable to `capabilities install`
  (capability subsystem silently dead) and unable to run backbone migrations.
- **Pre-existing bug to fix in-scope:** `migrations/` is not propagated to adopters at all,
  so backbone migrations have *never run* on any non-self-host adopter (latent — nobody's
  crossed a migration boundary yet). Architect: fix in this change (same defect class as the
  `capabilities/` omission; COR-010 presumes migrations reach adopters).
- **`find_source_kit()` precedence is a CONTRACT:** checkout `.pkit` (detected by
  `(.pkit/"decisions").is_dir()`) always wins; the bundled `_kit/` is fallback-only, resolved
  via `importlib.resources` so it can never be mistaken for a checkout. Preserves dev
  live-edit (B1) + self-host. `as_file()` lifetime must outlive the copy (ExitStack /
  materialize-once); trace the *zipped*-wheel path, not just unzipped `uv tool`.
- **Graceful guards:** add a source-missing guard at `sync`/`upgrade` entry (around
  `read_kit_version`) so any future incomplete bundle fails with a clean ClickException, not
  a raw `FileNotFoundError`.
- **Capability bundling = distribution medium, not activation.** All capability *source*
  ships in the wheel (the "repository"); `capabilities install` is still on-demand into the
  adopter (COR-017 opt-in boundary intact — the existing available-vs-installed split).

**Architect escalation: ADR-worthy + authorization required.** This establishes a standing
distribution invariant — *the official install resolves methodology content from bundled
package data, version-locked to the binary* — that clarifies (does not supersede) PRJ-004's
wheel-contents implication. Proposed **ADR-033**; lands `proposed`, needs acceptance before
implementation (gate). COR-007 follow-on flagged: *one* declaration of the kit-owned tree
consumed by both the build force-include and the propagator (today two hand-maintained lists
that drift — the `capabilities`/`migrations` omissions are the evidence).

## Open questions

**Resolved this session (by the reviewer passes):**
- ~~Is "binary carries its content" intended design or operational-only?~~ → **Intended
  design.** Architect ratified the binary↔content coupling; the gap is a defect, fix = bundle
  (option 1). → ADR-033.
- ~~Does this warrant an ADR?~~ → **Yes**, ADR-033 (clarifies PRJ-004, doesn't supersede).
- ~~Self-host nuance — does the fix disturb self-host?~~ → **No**, checkout-first precedence
  keeps self-host resolving to the real `.pkit/`; bundled `_kit/` only used in adopters.

**Still open (the brainstorm to finish):**
- **P0 scope/timing:** is the tech-agnostic audience in scope *now*, or does it wait for
  PRJ-004's stated revisit threshold (≈25–50 adopters / discoverability need)? P0 argues
  the trigger is *audience*, not *count* — but that's a strategic call to make explicitly.
- **How far up the P0 ladder** do we commit to (Level 1 one-liner vs 2 native packages vs
  3 standalone binary)? Each is a different cost/decision.
- **Windows as a goal?** Is native-Windows (no WSL/Git Bash) in scope for P0, or is
  "smooth on macOS/Linux, WSL on Windows" acceptable? Settling this bounds Layer-2 work.
- **Drift detection (B7):** a new `pkit doctor` / `pkit version --check` surface, or folded
  into existing `status`/`validate`? (Less urgent once the binary ships its own content —
  the official-install drift axis is collapsed; matters mainly for checkout-driven upgrades.)
- **COR-007 follow-on:** one declaration of the kit-owned tree consumed by both the build
  force-include and the propagator (`PROPAGATED_AREAS`) — fix now or file separately?

## Crystallises into (expected)

- A filed issue for the wheel/`find_source_kit` gap (B4–B6) — the immediate artifact, and
  the floor P0 sits on.
- A **PRJ-004 revisit** (or successor) driven by P0's broader-audience premise — settling
  how far up the invisibility ladder to go (Level 1 one-liner at minimum).
- Possibly an ADR on binary↔content coupling (option 1 vs 3) and/or platform scope
  (POSIX-first vs native Windows).
- Doc updates: CLI README accuracy (B10), an adopter upgrade flow (B9), a drift-safety
  note (B8). Retire this note via `pkit scratchpad done` citing those refs.
