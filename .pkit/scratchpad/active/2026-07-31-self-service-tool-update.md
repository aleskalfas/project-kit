---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-07-31
---

# Self-service tool update: can `pkit upgrade` get me the latest released tool on its own?

Exploratory note (COR-012). Retires by producing an ADR/COR decision, or being dropped. It frames the question and the options; it does **not** pre-decide.

## The question

Today, moving a project to a newer pkit is **two manual steps**: `uv tool install --force <url>@vX` to get a newer *tool* (its bundled kit), then `pkit upgrade` to bring the *project*'s `.pkit/` up to that tool's bundle. `pkit upgrade` upgrades the project **from** the tool's bundle — it has **no** way to update the tool itself or even discover that a newer release exists. There is no self-service "move me to the latest release" path, and the gap is unintuitive: an adopter (AUJ) ran `pkit upgrade`, got *"Already at backbone vX; nothing to upgrade"* against a stale global tool, and it was non-obvious that the fix lived in a *different* command (`uv`), not in re-running `pkit upgrade`. **Should pkit be able to fetch/run/repoint to the latest released tool on its own, and if so, in what shape?**

## What is already built (the reframe — most machinery exists)

pkit ships a **version router** ([ADR-039](../../../docs/architecture/decisions/ADR-039-pkit-entry-point-router.md), `src/project_kit/router.py`): when the enclosing project pins a version different from the running binary, the entry point **re-execs `uvx project-kit@<version>`** from a compiled-in distribution URL (`_DISTRIBUTION_GIT_URL`, the PRJ-004 canonical git URL). So pkit **already fetches and runs a specific released version of itself over the network, on its own** — the hard part. What's missing for *self-service-latest* is only:

1. **Discover the latest released tag** — a `git ls-remote --tags <url>` query. The router only ever runs the version a project *pins*, never "the newest available."
2. **A flow that repoints to it** — raise the project (and/or reinstall the tool) to that tag.

So this is a small increment on shipped infrastructure, not a from-scratch build. That materially changes the cost/benefit.

## What is already known / constraints

- **Two genuinely different upgrades, two scopes.** The *tool* is one `uv`-installed wheel shared across **all** the user's projects; a *project* is one repo. `pkit upgrade` today only touches the project's `.pkit/`. Updating the tool changes behaviour for **every** other project on the machine.
- **`pkit upgrade` is offline today** — it reads the tool's bundle; it makes no network call. A "discover latest tag" query adds one, so the command's failure posture changes: it must **degrade loudly, never brick** (the router's own posture per ADR-039 — an unresolvable pin runs self rather than hard-failing).
- **Distribution is uv-first but pip-supported** ([PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)). The router's fetch path is `uvx`; a pip-installed pkit differs. A self-updater must detect the installer or scope explicitly to uv.
- **Which upstream?** `_DISTRIBUTION_GIT_URL` is compiled in for canonical project-kit; a fork, a private mirror, or externally-sourced content ([COR-041](../../../.pkit/decisions/core/COR-041-external-source-distribution.md)) has a different source. The install does **not** currently record its upstream source URL in the manifest — so "reinstall from where?" is an open input for anything but the canonical repo.
- **Permission model.** `uv tool install --force` mutates the user's global environment. A *per-project* command escalating to a *global* mutation is a blast-radius / autonomy concern the sandbox + allowlist must vet (COR-028 family).
- **Router-pin subtlety (worth recording).** `_resolve_pin` reads the adopter's `.pkit/VERSION` — but **adopters don't have `.pkit/VERSION`** (it's source-repo-only; the #545 provenance-bug family). So for an adopter `_resolve_pin` returns `None` → the router runs **self** (the global tool). That is *why* AUJ's `pkit upgrade` ran the global tool and why reinstalling that tool fixed it. Consequence: the router's project-pin route is effectively **inert for adopters today**; any self-service-latest design has to reckon with the fact that the pin it would raise (`.pkit/VERSION`) isn't even present in an adopter tree.

## Candidate options (enumerated, not chosen)

- **(A) `pkit upgrade --self`** — `pkit upgrade` detects a newer release and, opt-in, reinstalls the tool then re-runs the project sync. Most seamless single gesture. Most to get wrong: it collapses the tool/project scopes, self-replaces a running binary (uv installs atomically, then re-exec — workable but fiddly), and makes a per-project command mutate the shared tool.
- **(B) `pkit self-update`** — a dedicated command: discover the latest tag → reinstall the tool (`uv tool install --force <url>@vlatest`, or route via `uvx`). Keeps "update the tool" and "update the project" as **two clean, separate one-liners** (`pkit self-update && pkit upgrade`). Honest about scope; discoverable; no silent cross-project side effect.
- **(C) detect-and-instruct** — `pkit upgrade` stays project-only, but when it detects the tool is behind the latest release it **prints the exact update command** (and why). Smallest honest win: it removes the *"nothing happened / what do I run?"* confusion — the thing actually hit — with **zero** blast-radius, no new mutation, no uv-coupling beyond a string. A natural first step that (B) can later supersede.

## What would resolve this (the axes a decision must fix)

1. **Scope rule** — is updating the shared tool an **explicit gesture** (its own command / opt-in flag) or an acceptable **side effect** of "upgrade this project"? (Leans toward explicit: cross-project blast-radius argues against silent.)
2. **Installer surface** — uv-only, or installer-agnostic (detect uv vs pip)? Scoping to uv first is defensible given the router already assumes it.
3. **Offline / failure posture** — the network "discover latest" must warn-and-continue, never brick, matching ADR-039.
4. **Upstream source** — canonical-URL-only first, or record/read the install's source so forks/private-mirrors/COR-041 consumers work? (Ties to "the install doesn't record its source" gap.)
5. **Interaction with the router + the adopter-`.pkit/VERSION` inertness** — does self-update repoint a pin, reinstall the tool, or both; and does the adopter even have the pin file the router keys on?

## Lean (a lean, not a decision)

First increment **(C)** — it directly kills the friction that surfaced, is nearly free, and commits us to nothing. Then **(B)** as the clean self-service command once the scope rule (axis 1) is settled. **(A)** last, if a single-gesture flow proves wanted after (B). The decision this note retires into should fix axes 1–4 at minimum; axis 5 (router interaction) may pull in a small ADR-039 refinement.

## Related

ADR-039 (the version router — the fetch-and-run-a-version machinery), PRJ-004 (distribution channel, uv/pip, tag-pinning), COR-041 (externally-sourced upstreams), COR-010 (lifecycle/upgrade), and the #545 provenance-bug family (why adopters lack `.pkit/VERSION`).