---
id: REQ-004
title: A check never reads a missing result as one that found nothing
status: active
statement: A check of the backbone never reads a missing result, from a command it runs or from git, as one that found nothing.
measure: No check passes on a command that gave no result, or on a default branch git could not resolve. Each such case fails the check or is reported, as *Verified by* lists.
applies-to: Each check the backbone runs and each value the backbone resolves for one, whichever component's command fills the value.
actors:
  - ACT-ci-pipeline
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/command_runner.py
        - tests/test_command_runner.py
        - tests/test_friction_anchor_kinds.py
        - tests/test_validators.py
        - tests/test_data_points.py
        - tests/test_default_branch.py
      record:
        - COR-050#2
        - COR-050#12
        - COR-055#6
        - COR-052#6
        - COR-054#4
      artefact:
        - ACT-ci-pipeline
        - ACT-adopter
    revalidated:
      at: 2026-10-24T20:54:52Z
      outcome: updated
    revisited:
      - anchor:
          kind: path
          value: src/project_kit/command_runner.py
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: path
          value: tests/test_command_runner.py
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: path
          value: tests/test_data_points.py
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: path
          value: tests/test_default_branch.py
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: path
          value: tests/test_friction_anchor_kinds.py
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: path
          value: tests/test_validators.py
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: record
          value: COR-050#12
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: record
          value: COR-050#2
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: record
          value: COR-052#6
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: record
          value: COR-054#4
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
      - anchor:
          kind: record
          value: COR-055#6
        outcome: unchanged
        reason: The title, statement and measure say a missing result where they said a missing answer, for the same output. This target still backs the requirement as written.
---

# REQ-004 · Quality · A check never reads a missing result as one that found nothing

**Verified by:** Tests run commands that give no result in each way the command runner recognises:

- it cannot start
- it ends abnormally
- it overruns its time
- it prints output that cannot be read

Each is reported as giving no result, and tests find that:

- [validation](../../glossary.md#term-validation--validation) fails on such a command
- the [change check](../../glossary.md#term-change-check--change-check) fails on it where the [project](../../glossary.md#term-project--project) enforces the check
- the [whole-repository check](../../glossary.md#term-whole-repository-check--whole-repository-check) never reports its [artefact](../../glossary.md#term-artefact--artefact) `current`
- a [data point](../../glossary.md#term-data-point--data-point) declared `fail` stays unresolved when its command gives no result
- a [default branch](../../glossary.md#term-default-branch--default-branch) the clone cannot read is reported, never guessed

**Rationale:** A missing <!-- pkit:not-the-term -->answer "is never an <!-- pkit:not-the-term -->answer naming nothing" (COR-050 [point](../../glossary.md#term-point--point) 2). COR-055 gives the reason, under "Why no <!-- pkit:not-the-term -->answer fails": "Silence must not read as health". A pass nobody earned means that "the gate reports the [project](../../glossary.md#term-project--project) in order when a check never ran, and nothing prompts anyone to look". So the CI pipeline can gate a merge on a check's exit status, and an adopter's merges wait on checks that ran.
