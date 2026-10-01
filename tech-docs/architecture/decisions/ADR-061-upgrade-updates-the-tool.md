---
id: ADR-061
title: pkit upgrade updates a stale tool itself, and prints the command where it may not
status: proposed
date: 2026-10-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
supersedes: ADR-044
---

## Summary

**In plain terms:** `pkit upgrade` asks the release source whether a newer pkit exists. When the installed tool is behind, it updates it — `uv tool install --force` at the latest release — and runs the same upgrade again under the new tool, so one command brings both the tool and the project up to date. Where installing is not appropriate — no terminal, `--no-self-update`, a dry run, an install that fails or is declined — it prints the exact command instead. The check is best-effort and never fails the upgrade. It runs only where pkit runs as the installed tool itself, never in a process the router started at a project's pinned version, and never in the methodology's source repository. Run outside any project, `pkit upgrade` updates the tool alone. Updating the shared tool is safe because projects are pinned by default and run their own version.

## Context

Two things get upgraded, by two different means. The **tool** — the `uv`-installed wheel with its bundled methodology content, version-locked to it ([ADR-033](ADR-033-official-install-bundles-content.md)) — is one install shared by every project on the machine. A **project's** `.pkit/` content is brought up to whatever that tool bundles by `pkit upgrade` ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)), which reads the bundle and is otherwise offline. A project can therefore never get ahead of the tool: when the tool is behind the latest release, the project's upgrade reports nothing to do, and the fix is a `uv` command the operator has to know about.

The means to fetch a released version already exist: the entry-point router re-runs a pinned version through `uvx` from the compiled distribution URL ([ADR-039](ADR-039-pkit-entry-point-router.md)), the one channel the project distributes through, installed with `uv` only ([PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)). And projects are pinned by default: `pkit upgrade` writes a project's pin, and a pinned project runs the version its pin names, whatever tool the machine has installed ([ADR-062](ADR-062-projects-pinned-by-default.md)).

Replacing the tool is still a mutation of a binary outside any one project — a network install the operating-system sandbox gates where one runs — and an un-pinned project on the machine runs whatever it is replaced with.

## Decision

**`pkit upgrade` updates a stale tool and runs again under it; where it may not act, it prints the command.**

1. **Detect, best-effort.** `pkit upgrade` asks the release source for its highest `v<semver>` tag — `git ls-remote --tags` against the compiled distribution URL the router pins against, bounded by a short timeout. Any failure — offline, no credentials, `git` missing, the timeout, no parseable tag — warns on standard error and the upgrade carries on as if the tool were current. The check never fails the command. When the tool is current, the upgrade says so.

2. **Act when the tool is behind.** `pkit upgrade` runs `uv tool install --force <distribution URL>@v<latest>`, then replaces its own process with the same `pkit` command under the freshly installed tool, so content sync, migrations and the pin all run under the new bundle. The process it starts carries `PKIT_SELF_UPDATED=1` and never updates the tool again, whatever the version comparison says.

3. **Print the command where it may not act.** The upgrade prints the exact install command, and that `pkit upgrade` is to be run again, when standard input or standard output is not a terminal, when `--no-self-update` is passed, or when the install exits non-zero — failed, or declined at the sandbox's prompt. If the install succeeded but the new process cannot be started, it prints the same and carries on under the running tool. Under `--dry-run` it reports the install it would run and runs nothing.

4. **Only where pkit runs as the installed tool.** The tool step runs outside any project — where it is the whole of `pkit upgrade`, the "just update my tool" case, instead of an error about a missing project — and in a project the router left to the installed tool: an un-pinned project, or a pinned one whose pin matches it. It does not run in a process the router started at a pinned version (that upgrade advances its pin instead, ADR-062), nor when routing is bypassed (`PKIT_NO_ROUTE`, which is how a pin raise runs the target version's own upgrade), nor in the methodology's source repository, where the upgrade stops before this step: it hands over to sync when the code is the checkout's own, and refuses otherwise ([ADR-059](ADR-059-methodology-source-repository.md)).

5. **The tool, from its distribution URL, nothing else.** The step installs the tool from the compiled distribution URL and touches no externally-sourced content ([COR-041](../../../.pkit/decisions/core/COR-041-external-source-distribution.md)). The router's route decision is unchanged; this step only calls on the URL it already uses.

## Rationale

**Why act rather than print.** The friction is a stale tool the operator must notice and fix in a different command. Printing the command names the fix; acting removes the step. What argued against acting was its reach: reinstalling the shared tool moved every project on the machine at once, as a side effect of a command run in one of them. Pinning by default removes that reach. A pinned project runs its own version through the router and does not follow the installed tool, so updating the tool disturbs no pinned project. The projects it does move are those that opted out of pinning to follow the installed tool, and moving with it is what they asked for.

**Why a terminal is required.** An install under automation — a pipeline, a piped invocation — is a network side effect nobody is present to see, on a machine that may serve other jobs. Printing the command there costs nothing and leaves the decision with whoever reads the log.

**Why the sandbox keeps its prompt.** The install writes outside the project and reaches the network; where the sandbox runs, it gates that, and pkit does not allowlist the install to silence it — the permission model is worked with, not around (core rules 14 and 15). A decline is a non-zero exit, and a non-zero exit falls back to printing, so the worst case is the old behaviour, never a broken tool.

**Why run again under the new tool.** Content is locked to the binary that bundles it (ADR-033). Carrying on in the old process would sync the old bundle and pin the project to the old version; replacing the process makes the one command finish under the code it just installed.

**Why its own guard.** The router's loop guard, `PKIT_ROUTED`, marks a process the router started at a pinned version, and an upgrade that sees it takes the pinned path. Reusing it would send the re-run upgrade down the wrong branch. `PKIT_SELF_UPDATED` stops one thing — a second self-update — and stops it regardless of versions, so an install that succeeds yet leaves the reported version unchanged cannot loop.

### Alternatives considered

- **Detect and print only; never install** — the ruling of [ADR-044](ADR-044-upgrade-self-update-detect-instruct.md), which this record supersedes. Overturned: it kept the manual step, and its reason — that replacing the shared tool would move every project on the machine — stopped holding once projects are pinned by default. It remains the fallback of point 3.
- **Install in every session, terminal or not.** Rejected: a pipeline would replace its runner's tool unseen.
- **Ask `[y/N]` before installing.** Not taken: the operator who types `pkit upgrade` at a terminal is asking to be brought up to date, and with projects pinned the install reaches no further than that request; `--no-self-update` says no in advance, and the sandbox, where it runs, asks on its own.
- **A separate `pkit self-update` command.** Not taken: `pkit upgrade` outside a project already updates the tool alone, and a second command would split one intent — bring me up to date — across two.
- **Reuse the router's loop guard.** Rejected, for the reason above.

## Implications

- `pkit upgrade` may run `uv tool install --force` — interactively only, gated by the sandbox where it runs. `--no-self-update` keeps the print-only behaviour; `--dry-run` reports the install it would run. The flags and messages are described in the CLI reference's `upgrade` section (`.pkit/cli/README.md`).
- The behaviour lives in the upgrading code, so a machine gets it on the first upgrade run by a tool that carries it. No migration: no installed state changes shape.
- The printed and the run command are both `uv` commands, so the step depends on the `uv`-only frontend (PRJ-004).
- Stands on ADR-033, ADR-039, ADR-059, ADR-062, COR-010, COR-041 and PRJ-004, all accepted. ADR-039 is not reopened.
