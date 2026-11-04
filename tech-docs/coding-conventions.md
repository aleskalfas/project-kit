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

The conventions that project-kit's code, its tests and its scripts are written to. The agents' overlay, `.pkit/agents/project/overlay.yaml`, names this page as the project's conventions corpus. So the `software-engineer` agent writes code to it, and the code-review panel's reviewers judge a change by its rules (software-engineering DEC-001 point 2, DEC-002 point 4). It therefore holds coding conventions only, and points to each coding convention that a record or another document already holds (PRJ-013 point 4). How to run the checks is in [`CONTRIBUTING.md`, "Running checks"](../CONTRIBUTING.md#running-checks).

## Names, docstrings and comments

Follow the code around your change. Write names, docstrings and comments as plainly and precisely as the module you change writes its own (PRJ-013 point 1). These are the opinions that live only in the corpus, never in an agent's definition (software-engineering DEC-001 point 3).

- **The conventions owe no docstring.** They say how a docstring is written, not where one must be (PRJ-013 point 2).
- **A departure is a judgement call.** A reviewer raises it as advisory, never as a block (PRJ-013 point 3, software-engineering DEC-002 point 3).

## Lint, format and types

PRJ-010 decides how pyright checks the code: the package in strict mode through a ratchet, everything else in standard mode, and no suppression left in the package. What ruff's lint and format ask of the code is in [`CONTRIBUTING.md`](../CONTRIBUTING.md), "Running checks", its paragraph "Lint and format". Where a suppression is allowed, and how it names its rules and its reason, is in the same section's bullet "Suppressions", under "Type checking".

## Tests

How a test is written is in [`tests/README.md`](../tests/README.md), from its section "Type checking" on.
