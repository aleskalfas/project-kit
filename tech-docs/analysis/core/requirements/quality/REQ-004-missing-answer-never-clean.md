---
id: REQ-004
title: A check never reads a missing answer as one that found nothing
status: active
statement: A check of the backbone never reads a missing answer, from a command it runs or from git, as one that found nothing.
measure: No check passes on a command that gave no answer, or on a default branch git could not resolve. Each such case fails the check or is reported, as *Verified by* lists.
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
      at: 2026-10-22T23:47:20Z
      outcome: unchanged
      unchanged-because: The actors whose needs it meets each gain a summary, the first sentence of their opening, and nothing else of theirs changes. What it asks still holds.
---

# REQ-004 · Quality · A check never reads a missing answer as one that found nothing

**Verified by:** Tests run commands that give no answer in each way the command runner recognises:

- it cannot start
- it ends abnormally
- it overruns its time
- it prints output that cannot be read

Each is reported as giving no answer, and tests find that:

- validation fails on such a command
- the change check fails on it where the project enforces the check
- the whole-repository check never reports its artefact `current`
- a data point declared `fail` stays unresolved when its command gives no answer
- a default branch the clone cannot read is reported, never guessed

**Rationale:** A missing answer "is never an answer naming nothing" (COR-050 point 2). COR-055 gives the reason, under "Why no answer fails": "Silence must not read as health". A pass nobody earned means that "the gate reports the project in order when a check never ran, and nothing prompts anyone to look". So the CI pipeline can gate a merge on a check's exit status, and an adopter's merges wait on checks that ran.
