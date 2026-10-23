---
id: REQ-051
title: A refused stamp of the analysis leaves every file as it was
status: active
statement: When `pkit analysis new` refuses, it leaves every file and folder of the project as it was.
measure: After a refusal, the project's files and folders equal those before the command ran, byte for byte. Each file the stamp writes is moved into place whole, so a failure halfway leaves the old file as it was.
applies-to: "Every form of `pkit analysis new`, an artefact, a domain-model view and a revalidation record alike, whenever it refuses, a refusal after its write included."
actors:
  - core:ACT-developer
  - core:ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/scripts/_lib/stamp.py
        - tests/test_software_analysis.py
        - tests/test_software_analysis_records.py
---

# REQ-051 · Quality · A refused stamp of the analysis leaves every file as it was

**Verified by:** Tests find that a file the stamp writes replaces the old one whole, keeping its mode. They find that a failed recording of the analysis location puts back each file and folder written, and records nothing. Tests of the record's refusals find no record written. No test interrupts a write halfway.

**Rationale:** The capability's README promises that a refused stamp writes nothing, and its stamp's code keeps that promise. A file left half written would leave the analysis in a state no command gave it. So would a location recorded for an artefact never written.
