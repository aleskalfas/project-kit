---
reader: maintainer
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/agents/project/overlay.yaml
      record:
        - software-engineering:DEC-001#2
        - software-engineering:DEC-001#3
        - software-engineering:DEC-002#3
        - software-engineering:DEC-002#4
        - PRJ-010
---

# Coding conventions

The conventions that project-kit's code, its tests and its scripts are written to. The agents' overlay, `.pkit/agents/project/overlay.yaml`, names this page as the project's conventions corpus. So the `software-engineer` agent writes code to it, and the code-review panel's reviewers judge a change by its rules (software-engineering DEC-001 point 2, DEC-002 point 4). It therefore holds coding conventions only. How to run the checks, and how a change lands, is in [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Names, docstrings and comments

Follow the code around your change. Write names, docstrings and comments as plainly and precisely as the module you change writes its own. These are the opinions that live only in the corpus, never in an agent's definition (software-engineering DEC-001 point 3).

- **No docstring is owed by it.** It says how a docstring is written, not where one must be.
- **A departure is a judgement call.** A reviewer raises it as advisory, never as a block (software-engineering DEC-002 point 3).

## Lint, format and types

PRJ-010 decides how pyright checks the code: the package in strict mode through a ratchet, everything else in standard mode, and no suppression left in the package. What ruff's lint and format ask of the code is in [`CONTRIBUTING.md`](../CONTRIBUTING.md), "Running checks", its paragraph "Lint and format". Where a suppression is allowed, and what it gives, is in the same section's bullet "Suppressions", under "Type checking".

## Tests

How a test is written is in [`tests/README.md`](../tests/README.md), from its section "Type checking" on.
