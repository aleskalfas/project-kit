---
reader: maintainer
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/agents/project/overlay.yaml
        - tests/README.md
      record:
        - PRJ-013#1
        - PRJ-013#2
        - PRJ-013#3
        - PRJ-013#4
        - software-engineering:DEC-001#2
        - software-engineering:DEC-001#3
        - software-engineering:DEC-002#3
        - software-engineering:DEC-002#4
        - PRJ-010
      artefact:
        - CONTRIBUTING.md#running-checks
---

# Coding conventions

The conventions that project-kit's code, its tests and its scripts are written to. The agents' overlay, `.pkit/agents/project/overlay.yaml`, names this page as the project's conventions corpus. So the `software-engineer` agent writes code to it, and the code-review panel judges a change by it (software-engineering DEC-001 point 2, DEC-002 point 4).

The page therefore holds coding conventions only (PRJ-013 point 4). Those agents read only what the overlay names, so the page points to some conventions that a record or another document holds. How to run the checks is in [`CONTRIBUTING.md`, "Running checks"](../CONTRIBUTING.md#running-checks).

## Names, docstrings and comments

Write the names, docstrings and comments of your change plainly and precisely, in the manner of the module you change. A module's cryptic names license none in your change. Where there is no module to follow, as in a new module, test file or script, use ordinary good engineering judgement (PRJ-013 point 1). These are the opinions that live only in the corpus, never in an agent's definition (software-engineering DEC-001 point 3).

- **No convention requires a docstring.** The one above says how a docstring is written, never where one must be. Whether code needs one is judged in each change (PRJ-013 point 2).
- **Both are judgements.** A reviewer raises a finding under either as an `[advisory]` finding, never as a block (PRJ-013 point 3, software-engineering DEC-002 point 3).

## Lint, format and types

PRJ-010 decides how pyright checks the code. The package is in strict mode through a ratchet, everything else in standard mode, and the package keeps no suppression. What ruff's lint and format ask of the code is in [`CONTRIBUTING.md`](../CONTRIBUTING.md), "Running checks", its paragraph "Lint and format". Where a suppression is allowed, and how it names its rules and its reason, is in the same section's bullet "Suppressions", under "Type checking".

## Tests

How a test is written is in [`tests/README.md`](../tests/README.md), from its section "Type checking" on.
