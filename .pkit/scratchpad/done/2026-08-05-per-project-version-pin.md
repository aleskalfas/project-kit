---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-05
retired: 2026-08-06
produced:
  - ADR-045
---

# Per-project version pin: make the router's pin work for adopters (Option D)

Exploratory note (COR-012). Retires by producing an ADR-039 refinement (or a new ADR) + decision, or being dropped. It frames the question and the options; it does **not** pre-decide. This is **option D** — the seamless-upgrade end-state [ADR-044](../../../docs/architecture/decisions/ADR-044-upgrade-self-update-detect-instruct.md) named and deferred (print-only v1 shipped in v1.143.0).

## The question

The [ADR-039](../../../docs/architecture/decisions/ADR-039-pkit-entry-point-router.md) router is **designed** to run each project at its own pinned pkit version: when a project pins a version different from the running binary, the entry point re-execs `uvx project-kit@<pin>` and lets *that* serve the command. So a global-tool upgrade doesn't disturb a pinned project — the reproducibility guarantee. **But it is inert for adopters:** `_resolve_pin` reads `.pkit/VERSION`, and adopters have **no** `.pkit/VERSION` (verified absent in a real adopter; it is source-repo-only, the #545 family). No pin file → the router runs *self* (the global tool). So every adopter project runs whatever the global binary is, with **no per-project version-locking at all**. **How do we make the router's pin real for adopters — so `pkit upgrade` moves a project to a version and locks it there, with no global-tool mutation?**

Concretely: the payoff is that a global-tool upgrade stops disturbing pinned projects; each project runs the pkit whose content it holds; and `pkit upgrade` becomes an in-project pin-raise served ephemerally via `uvx` — **no global `uv tool install`, no shared-binary blast radius, no sandbox prompt** (the exact costs that sank the auto-install path in ADR-044).

## What is already known

- **The router mechanism (ADR-039).** Three routes: (1) source checkout → exec the in-tree dispatcher; (2) project pins a version ≠ running → re-exec `uvx project-kit@<pin>`; (3) otherwise run self. An unresolvable pin **degrades loudly to run-self, never bricks**. A loop guard stops the re-exec from re-routing.
- **The pin source today is `.pkit/VERSION`** (`_resolve_pin` → `_read_pkit_version`), justified as "run me under the version whose *content* I have" ([ADR-033](../../../docs/architecture/decisions/ADR-033-official-install-bundles-content.md) version-locks content to the binary). But that file is **not propagated to adopters** — so the pin is inert for exactly the population it was built for.
- **Adopters already carry `.pkit/manifest.yaml` `backbone_version`** (verified: `1.142.4` in a real adopter). It records the version the project's `.pkit/` **content** is synced to, `pkit upgrade` writes it, and [PRJ-007](../../../.pkit/decisions/project/PRJ-007-release-maintains-self-host-manifest.md) keeps it current. So "the version whose content I have" — the exact thing `.pkit/VERSION` was meant to express — **already exists** in every adopter, under a different filename.
- **uvx is per-project ephemeral, not a global mutation** (PRJ-004 uv-only). Running `uvx project-kit@vX` fetches + runs that version in a throwaway env; it does not touch the shared global tool. This is D's whole advantage over ADR-044's rejected `uv tool install --force`.

## Forces / tensions

- **Reproducibility vs staying-current** — the pin is the reproducibility guarantee; an upgrade is the deliberate act of moving it. D must keep upgrades deliberate (no silent drift), same as ADR-044.
- **The bootstrap-the-raise paradox (load-bearing)** — if a project is pinned to X, *every* command in it re-execs to X. So to move it *forward* you must run something **newer** than X to rewrite the pin. `pkit upgrade` cannot both be pinned-to-X and be the thing that raises past X without an explicit escape.
- **Content-and-code must move together** — to sync content to version Y you need Y's *code* (Y's bundle). So a raise is "run Y's pkit (via uvx) → its sync writes Y's content → the manifest records Y" — code and content advance as one, per ADR-033.
- **Offline / network** — every command in a pinned project may re-exec `uvx` (cached after first fetch); must honour ADR-039's cheap-hot-path + degrade-loudly-when-unfetchable posture.
- **No-shared-files** — a *new* pin file raises an ownership question (project-owned? kit-owned? synced?); reusing an existing per-project record sidesteps it.
- **The #545 adjacency** — adopters lacking `.pkit/VERSION` is itself arguably a latent inconsistency; one option *fixes that* rather than routing around it.

## Candidate approaches (enumerated, not chosen)

- **(A) — Resolve the pin from `manifest.yaml` `backbone_version`** *(lean)*. Point `_resolve_pin` at the manifest's `backbone_version` (which adopters have, upgrade maintains, and which *is* the content-version). Route 2 then fires for adopters with **no new file**. `pkit upgrade` raises the pin by writing `backbone_version` to the target and syncing content to match. Smallest surface; reuses existing state; a small ADR-039 refinement (pin source). Risk: overloads `backbone_version` as *both* "content synced to" *and* "code to run" — but ADR-033 says those are the same thing, so the overload is arguably correct, not a conflation.
- **(B) — A new dedicated project-owned pin file.** An explicit `pin`/target-version file the router reads. Clean separation of "pinned code version" from "content version"; but a new artifact with its own schema + no-shared-files ownership + lifecycle, and it can drift from the manifest. Heavier; only justified if pin-version and content-version genuinely need to differ (do they?).
- **(C) — Make adopters carry `.pkit/VERSION`** (the file the router already reads). Fixes the #545-adjacent gap directly: propagate `.pkit/VERSION` to adopters and keep it current. Router needs no change. But it introduces a second per-project version record beside `manifest.yaml backbone_version` — two sources of the same truth, a drift risk the #545 family already shows is real.

### The bootstrap-the-raise mechanism (must be spelled out for whichever approach)

- **Explicit upgrade escapes its own pin.** `pkit upgrade [--to vY]` runs under a routing bypass (the existing `PKIT_NO_ROUTE`, or upgrade sets it) so the *currently-installed* binary — or the global tool — performs the raise rather than the pinned-X version re-serving. It resolves the target (latest via `git ls-remote`, or `--to vY`), then **runs the target's pkit via `uvx` to perform the sync** (target code → target content), and writes the pin (manifest `backbone_version`) to Y. After that, ordinary commands route to Y. This keeps "moving forward" a deliberate, explicit act and dissolves the paradox.
- **First run / un-pinned** stays route-3 (run self) exactly as today; install already writes `backbone_version`, so a fresh adopter is pinned from the start under (A).

## What would resolve this

1. **Pin source** — (A) manifest `backbone_version`, (B) new file, or (C) propagate `.pkit/VERSION`. (Lean A: no new file, reuses the content-version adopters already have.)
2. **The bootstrap-the-raise hand-off** — how `pkit upgrade` escapes its own pin to rewrite it (routing bypass + run-the-target-via-uvx-then-sync).
3. **Upgrade sequencing** — pin-raise + content-sync + migrations as one coherent, resumable operation, all under the target version's code.
4. **The ADR-039 refinement shape** — route 2's pin source changes (and possibly the offline/uvx-unfetchable degrade for a *manifest*-sourced pin). A refinement of ADR-039, plus likely a companion decision for the upgrade semantics.

## Lean (a lean, not a decision)

**Approach A** (manifest `backbone_version` as the pin), with the bootstrap-the-raise via an explicit `pkit upgrade [--to vY]` that runs under a routing bypass and performs the raise-then-sync under the target's code. It needs no new file, reuses per-project state adopters already carry, and makes the router's designed per-project version-locking finally fire for adopters. The crux to pressure-test is the bootstrap-the-raise hand-off and whether overloading `backbone_version` as the run-pin is a clean identity (per ADR-033) or a conflation.

## Related

ADR-039 (the router — D refines it), ADR-033 (content version-locked to the binary — grounds "run the version whose content I have"), ADR-044 (self-update; D is its deferred seamless increment), PRJ-007 (upgrade keeps manifest `backbone_version` current), PRJ-004 (uv-only / uvx), COR-010 (lifecycle / upgrade), and the #545 family (why adopters lack `.pkit/VERSION`).

---

## Critic pass (2026-08-05) — approach A has holes; reframe toward a dedicated pin

An adversarial review (against the actual `router.py` / `upgrade.py` / `sync.py`) found the approach-A lean unsound as sketched. Recorded so the reframe doesn't re-tread it.

- **R1 — the bootstrap-the-raise escape is impossible as written, and naive A re-breaks ADR-044.** Routing happens in `main()` **before** the command is dispatched (the router is command-agnostic by design). So `pkit upgrade` in a pinned-X project re-execs into `uvx …@vX` *first*; that vX process sees "already at X — nothing to upgrade" and **no-ops forever**, even after the operator runs ADR-044's printed `uv tool install --force @vZ` (it still routes to X). "Upgrade sets `PKIT_NO_ROUTE`" can't work — the routing decision is a process ago. The pin-managing command cannot itself be run at the old pin.
- **R2 — A-specific silent-mutation hazard.** `sync._update_recorded_backbone_version` unconditionally writes `backbone_version = running-version` on every sync. If the pin *is* `backbone_version`, an offline `sync` in a pinned-X project degrades (ADR-039 D2) to run-self = global Z, and Z's sync rewrites the pin X→Z **silently** — the opposite of the reproducibility the pin exists for. ADR-039's benign *read*-degrade becomes a *mutate*-the-pin hazard once the pin is the sync-written field.
- **G1 — the overload blocks atomic/resumable upgrade.** sync writes `backbone_version` *before* migrations run; under A the pin advances mid-upgrade, and an interrupt leaves "pinned-Z, migrations half-applied" with no state to represent it. A separate pin gives the end-of-upgrade atomic flip.
- **G4 — `backbone_version` ≠ "run version" in general.** Capability content upgrades independently (`pkit capabilities upgrade`) without touching `backbone_version` (PRJ-007). So a project can hold `backbone_version=X` with capability content the vX bundle never shipped — the "same thing" identity is true of the wheel+its-bundle, not of the adopter's actual mixed content.
- **W1 — internal contradiction (mine).** A was defended with "content-version and run-version are the same (ADR-033)", while C was rejected for "two records of one truth drift." Both can't hold: if two records necessarily drift, A's overloaded field is already two-truths-in-one; if ADR-033 guarantees identity, a propagated `.pkit/VERSION` wouldn't drift either. Pick one identity story and apply it to both.
- **W2 — `--to vY` was over-engineering.** It is unbuilt scope and the sole source of the "turtles" recursion. Drop it: to reach a specific version the operator uses ADR-044's **shipped** `uv tool install --force @vY` then `pkit upgrade` — D **composes** with the print-only increment ADR-044 already ships.

### Reframed candidate (the shape to take to architect)

- **Dedicated project-owned pin file** (approach **B**, no longer "heavier" — its decoupling is the feature): a small operator-owned pin, separate from `backbone_version`. It is **not** auto-written by sync (kills R2) and can be the atomic end-of-upgrade flip (kills G1). No-shared-files: project-owned like `substrate-map.yaml`, never kit-synced.
- **The router runs the pin-*managing* commands unrouted** (a minimal, fixed carve-out — `upgrade`/`sync` run at the ambient/global version; everything else routes to the pin). This is the R1 fix and the load-bearing question for the architect: is "commands that operate *on* the pin run at the ambient version; commands that operate *under* the methodology run *at* the pin" a coherent refinement of ADR-039's command-agnostic router, or an unacceptable argv-coupling? (The critic's CA1 in a sharper form.)
- **Drop `--to vY`; compose with ADR-044** (W2). `pkit upgrade` raises the pin to the ambient tool's version (or latest via the ADR-044 `git ls-remote` it already does), then syncs — run unrouted, in-process, at the ambient version.
- **Open — do reads route, or only mutations?** ADR-039 routes *every* command so behaviour matches content (correctness of validation/gating depends on version⟺content). The critic's CA1 (route only mutations) cuts the hot-path uvx tax but risks running the wrong version's *behaviour* on a read. For a methodology tool, read-correctness may matter — so mutation-only routing is a real correctness/overhead tradeoff, not a free win. **Architect to weigh.**
- **Open — opt-in vs implicit pinning** (CA2): default run-self (today, zero tax) with pinning opt-in, vs every adopter pinned implicitly (surprising universal route-2 + a sudden global-flip the first time the tool upgrades). Given single-digit adopters and the confusion already fixed by ADR-044's print-only, opt-in may be the honest default.

**Revised lean:** dedicated pin file + a minimal router carve-out for pin-managing commands + drop `--to` (compose with ADR-044) + likely opt-in; reads-route-vs-mutations-only and opt-in-vs-implicit are the two questions for the architect. This is sound enough to take to architect *as a reframe*, with R1's carve-out as the load-bearing item to rule on.

---

## Architect pass (2026-08-05) — reframe corrected on one load-bearing point; shape settled

The architect reviewed the reframe. Verdict: architect-clear to proceed to a decision, conditional on **one correction** — the router carve-out is rejected; the escape belongs in the operator gesture, not the router.

- **Q1 (the gate) — REJECT the argv-aware router carve-out.** Making the router run `upgrade`/`sync` unrouted while routing everything else reopens ADR-039's *command-agnostic* contract, is a fragile pre-click argv parse, and is unsafe in **both** error directions (mis-classify a pin-managing command → it routes and no-ops; mis-classify a methodology command → it runs at the wrong version). Instead: the pin-raise escape lives in the **operator gesture** using the router's *existing* `PKIT_NO_ROUTE` bypass — `uv tool install --force <url>@vZ && PKIT_NO_ROUTE=1 pkit upgrade` — and `pkit upgrade` reads `PKIT_ROUTED=1` to detect it is the pinned child and print the actionable escape line. **Zero router change; ADR-039 stays closed.** Forgetting the bypass is benign (routes to X, no-ops with a message). **Drop `sync` from any escape** — once the pin is a dedicated file (not sync-written), sync-under-pin is *correct* and must not escape (this also dissolves R2).
- **Q2 — route ALL commands, not mutations-only.** For a methodology tool the *reads* (validate / status / gating) are the most correctness-sensitive; version⟺content must hold for them. Uniform routing stays (it is foundational to ADR-039's soundness). The CA1 mutation-only cut is rejected.
- **Q3 — dedicated project-owned pin DIRECTIVE file, not `backbone_version`, not named `VERSION`.** COR-006 artifact-role distinction: `backbone_version` is a **record** (a receipt of the last sync); the pin is a **directive** (a forward-looking, operator-owned control input) — a lockfile (`.python-version` model): committed, project-owned, never kit-synced, flipped last (atomic end-of-upgrade). Don't name it `VERSION` (re-imports the confusion). **Not an ADR-039 reopening** — ADR-039 *explicitly defers the pin source to implementation* (its lines 94-95, 155, #465), so choosing a dedicated file fills a slot ADR-039 left open.
- **Q4 — opt-in.** Pin-file presence is the signal; absent → route-3 run-self (today's zero-tax default). The file is created by the deliberate raise, not by install. Costed choices are opted into.
- **Q5 (advisory lean) — DEFER the build.** At single-digit adopters, ADR-044's print-only already relieved the *actual* reported friction; D's value is real but **latent** (no adopter currently wedged). COR-007 speculative-generality caution → record the reframe's conclusion and revisit on concrete demand rather than build now. **Advisory, not a gate.**
- **Escalation — none** under the recommended shape (ADR-039 not reopened). The decision to record is a **new ADR** (this file → ADR-045), not an ADR-039 amendment. Only the rejected argv-carve-out path would have needed foundational authorization.

**Settled shape (build, if built):** dedicated project-owned pin directive file (lockfile model, never sync-written) · opt-in (presence = pinned; absent = run-self) · route **all** commands · bootstrap-the-raise via the **existing** `PKIT_NO_ROUTE` bypass in the operator gesture + `pkit upgrade` detecting `PKIT_ROUTED` and printing the escape · drop `--to`, compose with ADR-044's shipped `uv tool install --force` · no router change, ADR-039 stays closed.

**Build-vs-defer:** the architect leans defer (Q5); the maintainer has the concrete need (multiple projects on different pkit versions under one global install — the exact demand Q5 said would justify building), so **build**. Recorded as ADR-045.