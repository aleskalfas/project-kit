---
id: REQ-005
title: A check never passes on an answer it did not get
status: active
statement: A check of the backbone never takes a missing answer, from a command or a reading it relies on, for a pass.
measure: A command that cannot start, exits abnormally, overruns its time or prints what cannot be read is reported as giving no answer. A missing answer fails validation, and the change check reports one as a finding whose kind fails the check. The whole-repository check reports the artefact as not judged, and a data point a check reads stays unresolved. A default branch that cannot be resolved is reported, never guessed.
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

# REQ-005 · Quality · A check never passes on an answer it did not get

**Verified by:** Tests have the backbone run commands that time out, exit abnormally or print what cannot be read, and find each reported as no answer. Tests find that such a command fails validation, fails the change check where the project enforces that check, and never leaves its artefact reported current. Tests find that a data point whose command gives no answer stays unresolved. Tests also find that a default branch the clone cannot read is reported, never guessed.

**Rationale:** "Silence must not read as health" (COR-055). A pass nobody earned "reports the project in order when a check never ran, and nothing prompts anyone to look" (COR-055). So the CI pipeline can gate a merge on a check's exit status, and an adopter's merges wait on checks that ran.
