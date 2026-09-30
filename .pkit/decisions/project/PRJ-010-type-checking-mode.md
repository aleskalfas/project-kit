---
id: PRJ-010
title: Type checking targets pyright's strict mode through a ratchet
status: proposed
date: 2026-10-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

pkit's type checker has been configured and never enforced. PRJ-003 committed the Python runtime to strict type checking "from the first commit", and `pyproject.toml` has named pyright's strict mode ever since, but the check aggregator (`scripts/check.sh`, which the pre-push hook and CI both run) never gated it, because the tree did not pass it. A setting nothing enforces is a wish: new code can add type errors freely, and nobody can tell whether the codebase is moving toward strict or away from it.

Measured for #840 with the locked pyright (1.1.409) over what `pyproject.toml` includes — `src/` and `tests/`, 334 files — after that issue's lint and format pass:

- **strict** (the configured mode): **37,328 errors in 245 files.** They are overwhelmingly missing and unknown annotations: `reportUnknownMemberType`, `reportUnknownParameterType`, `reportMissingParameterType`, `reportUnknownVariableType` and `reportUnknownArgumentType` alone account for 35,082 of them (94%). The other 89 files are already strict-clean.
- **standard**: 257 errors in 71 files — optional values used without a check, attributes read off a union, arguments of the wrong type. 62 of them are imports pyright cannot resolve: tests that import project-management's `_lib` package by name after putting its scripts folder on `sys.path`. With that folder on pyright's import path, standard reports 200 errors in 39 files.
- **basic**: 255 errors in 70 files, nearly the same set.

Every finding standard or basic reports is also a strict finding, file for file and rule for rule. No mode passes today. Reaching strict is a typing migration, not a cleanup; even standard and basic would need a cleanup of their own first.

## Decision

**pkit targets pyright's strict mode and gates it through a ratchet: the checker may not report more than it did before a change, and whatever it stops reporting it may not report again.**

1. **The mode is strict.** `pyproject.toml` keeps `typeCheckingMode = "strict"`; editors, contributors and the gate all see the same checker. No lower mode is gated alongside it: every finding standard or basic reports is also a strict finding, so the strict ratchet already holds them.
2. **The ratchet is a committed baseline of the current findings**, counted per file and per rule (`scripts/pyright-baseline.txt`), and a small script (`scripts/pyright-ratchet.py`) that runs pyright and compares. The aggregator runs it as its type-checking line, so the pre-push hook and CI both enforce it.
3. **A new finding fails.** A count above its baseline line — or any finding under a file or rule the baseline does not list — fails the gate, with the findings listed. A new file must therefore be strict-clean from its first commit. The fix is to fix it; the baseline never grows to admit it.
4. **An improvement is locked in.** A count below its baseline line also fails, until the change that made the improvement tightens the baseline with the script's `--update`, which only ever lowers counts. A file that becomes clean leaves the baseline, and the tool never puts it back: raising a count is a hand edit to the baseline that review sees.
5. **The staged path ends at plain strict.** The baseline shrinks as code is touched or deliberately typed; when it is empty the ratchet is the same as running pyright, and the gate line becomes `uv run pyright`.

## Rationale

**Why strict rather than a mode the tree passes.** The obvious gate — lower the mode until the tree passes — has no mode to land on: basic, the lowest that checks anything, reports 255 errors. Making standard or basic pass first is its own cleanup, larger than the change that introduces the gate. And lowering the configured mode would leave strict, the mode PRJ-003 committed to, with no mechanism behind it, when the 89 files already clean under strict show new code is being written to it anyway.

**Why a ratchet on strict rather than on a looser mode.** A ratchet on standard would stop new standard findings and nothing else: new code could keep arriving untyped, and strict would stay a wish. A ratchet on strict stops both at once, because strict reports everything standard does. Its cost is that new code must be strict-clean — which is the commitment PRJ-003 made, and which the recent code already meets.

**Why count per file and rule.** Line numbers move whenever code above them does, and messages name the types and symbols they are about, which change with any rename — either key would make the baseline churn on edits that change no finding. A count per file and rule is stable under both, and fine enough that a fix under one rule cannot pay for a regression under another, or a fix in one file for a regression in the next. What it cannot see is one finding swapped for another of the same rule in the same file; that is the price of stability, and small.

**Why an improvement fails until the baseline is tightened.** A baseline left looser than the tree is slack a later change can spend: fix three findings, and the next change could add three back unnoticed. Failing until the baseline matches the tree keeps it exact, so every improvement is permanent the moment it lands. The cost is one command in the change that made the improvement.

### Alternatives considered

- **Gate standard or basic outright.** Rejected for now: neither passes, and making either pass is a typing cleanup of its own. It stays available — a mode the tree comes to pass can be gated outright in addition.
- **Ratchet a lower mode.** Rejected: it prevents only the findings that mode reports, and leaves the configured strict mode unenforced.
- **Opt files into strict one by one** (pyright's `strict` list, over a lower default mode). Rejected: it guards the files on the list and nothing else, and a new file starts outside it — the ratchet holds every file, including the ones that do not exist yet.
- **Key the baseline by line or message.** Rejected: see above; the baseline would churn on every unrelated edit.
- **Switch to mypy.** Not reopened: PRJ-003 left pyright or mypy open, the configuration has been pyright's all along, and the choice of checker is not what kept the tree ungated.

## Implications

- **The change that implements this record lands after it is accepted.** It adds the script and its baseline, runs the ratchet from `scripts/check.sh`, and describes it in CONTRIBUTING.md's "Running checks" section; until then type checking stays ungated, as the aggregator's header says.
- **pyright's configuration grows two settings with the ratchet.** project-management's scripts folder goes on pyright's import path, so the tests that import that capability's `_lib` package by name are checked against it rather than reported as unresolved. And the platform is pinned (`pythonPlatform = "All"`), so the baseline cannot depend on the host that wrote it; today macOS and Linux report the same findings, file for file.
- **New code is written strict-clean.** A new module or test file carries parameter and return annotations; a test that needs an untyped module's attributes loads it by path, as the existing tests of capability scripts do.
- **A change that fixes findings tightens the baseline in the same change** (`--update`), and says so in its pull request; the gate refuses it otherwise.
- **The baseline belongs to one pyright version**, the one `uv.lock` pins. A change that upgrades pyright regenerates the baseline deliberately and states the difference, so an upgrade that reports more is a visible decision rather than a silent loosening.
- **Only `src/` and `tests/` are checked.** Capability scripts, the permission hook and the build hook run on other interpreters and import paths (their own `_lib` packages, a bare system `python3`) and stay outside pyright's `include`; bringing them in is follow-up work with its own configuration.
- **The typing migration is incremental and needs no further decision.** Each change that types code shrinks the baseline; when it is empty, the ratchet is retired in favour of plain `uv run pyright`.
- **Refines PRJ-003's type-checking line**: the checker is pyright, the mode strict, reached through this ratchet.
