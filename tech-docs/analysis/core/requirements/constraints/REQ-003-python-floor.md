---
id: REQ-003
title: The backbone's CLI runs on Python 3.11 or later
status: active
statement: The backbone's CLI, `pkit`, runs on Python 3.11 or later.
measure: The CLI's Python package declares `requires-python = ">=3.11"`, and its code uses nothing of the language or its standard library newer than Python 3.11.
applies-to: The backbone's CLI, the package under `src/project_kit/`, on every machine that runs it.
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

# REQ-003 · Constraint · The backbone's CLI runs on Python 3.11 or later

**Verified by:** The linter and the type checker hold the package's code to Python 3.11's syntax and standard library. The tests run on Python 3.13 alone, so no test runs on 3.11.

**Imposed by:** [PRJ-003](../../../../../.pkit/decisions/project/PRJ-003-implementation-language.md), which chose Python 3.11 or later for the CLI. It names that floor as the one "that mainstream <!-- pkit:not-the-term -->distributions and `uv` tools assume today", which gives "`tomllib`, structural pattern matching, exception groups". The choice is internal to project-kit, so adopters are unaffected: `uv` provisions a Python for `pkit` apart from their [project](../../glossary.md#term-project--project)'s own (PRJ-003).
