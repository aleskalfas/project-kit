---
rule-set: SWE
loaded: true
version: 1.0.0
rules:
  RS-SWE-001:
    status: proposed
    origin: {date: 2026-10-30, by: "Aleš Kalfas", why: "Builders who each ran the full suite on one machine waited most of an hour to learn what the project's own gate reported in minutes, so a builder runs what its change touches and leaves the full suite to that gate (project-kit#1182)."}
    pkit:
      friction:
        anchors: {record: ["COR-070#5"]}
---

## Operational rules of the software-engineering capability

*These are the software-engineering capability's operational rules, kept as its loaded rule set `SWE` (COR-070). They bind on the work of every session in a project where software-engineering is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one cannot be kept with a rule of another capability's, stop the step and report the clash. The loaded file is generated from `.pkit/capabilities/software-engineering/rule-sets/swe.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync or install edits neither.*

### RS-SWE-001 — While building, run the tests of what you changed

**While you build a change, run the tests of what it changes and the project's fast checks, and leave the full suite to where the project runs it, where it runs one.** Run the test modules for the files your change touches, and the checks that answer in seconds. Where the project runs its full suite in a gate of its own, such as a hook before each push or its continuous integration, leave the suite to that gate, so sessions building side by side do not each wait on it. Where the project runs it nowhere, run the full suite once before you hand the change over.
