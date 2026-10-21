---
id: REQ-004
title: A check never reads a missing answer as one that found nothing
status: active
statement: A check of the backbone never reads a missing answer, from a command it runs or from git, as one that found nothing.
measure: A command that cannot start, ends abnormally, overruns its time or prints what cannot be read gives no answer. A validator whose command gives no answer fails validation. The change check reports an anchor whose resolver gives no answer as having none, and fails on it where the project enforces the check. The whole-repository check never reports that anchor's artefact `current`. A data point declared `fail` stays unresolved, whole, when a command that fills it gives no answer. A default branch that git cannot resolve is reported, never guessed.
applies-to: Validation, the change check, the whole-repository check, and each data point and default branch the backbone resolves for them, whichever component's command they run.
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
---

# REQ-004 · Quality · A check never reads a missing answer as one that found nothing

**Verified by:** Tests have the backbone run commands that time out, exit abnormally or print what cannot be read, and find each reported as giving no answer. Tests find that such a command fails validation, fails the change check where the project enforces it, and never leaves its artefact reported `current`. Tests find that a data point whose command gives no answer stays unresolved. Tests also find that a default branch the clone cannot read is reported, never guessed.

**Rationale:** A missing answer "is never an answer naming nothing" (COR-050 point 2). COR-055 gives the reason, under "Why no answer fails": "Silence must not read as health". A pass nobody earned means that "the gate reports the project in order when a check never ran, and nothing prompts anyone to look". So the CI pipeline can gate a merge on a check's exit status, and an adopter's merges wait on checks that ran.
