---
id: REQ-004
title: The command line runs on Python 3.11 or later
status: active
statement: The system's command line runs on Python 3.11 or later.
measure: The package declares `requires-python = ">=3.11"`, and its code uses nothing of the language or its standard library newer than Python 3.11.
applies-to: Every `pkit` command, on every machine that runs it.
actors: []
refines: []
pkit:
  friction:
    anchors:
      path:
        - pyproject.toml
        - .github/workflows/checks.yml
      record:
        - PRJ-003
---

# REQ-004 · Constraint · The command line runs on Python 3.11 or later

**Verified by:** The linter and the type checker hold the package's code to Python 3.11's syntax and standard library. The tests run on Python 3.13 alone, so no test runs on 3.11.

**Imposed by:** PRJ-003, which chose Python 3.11 or later for the system. It names that floor as the one "that mainstream distributions and `uv` tools assume today", which gives "`tomllib`, structural pattern matching, exception groups".
