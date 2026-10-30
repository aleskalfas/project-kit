---
rule-set: SWE
loaded: true
version: 1.0.0
rules:
  RS-SWE-001:
    status: accepted
    origin: {date: 2026-10-30, by: "Aleš Kalfas", why: "A builder that runs the whole suite on its change waits on what the project's own gate reports anyway, and builders working side by side each wait on it, so a builder runs the tests of what it changes and the project's fast checks, and leaves the full suite to that gate where the project has one (decided on project-kit#2269, with project-kit#1182 as the evidence)."}
    pkit:
      friction:
        unanchored-because: "A rule about how a session tests its own change while it builds; no record decides it and no file carries it out."
---

## Operational rules of the software-engineering capability

*These are the software-engineering capability's operational rules, kept as its loaded rule set `SWE` (COR-070). They bind on the work of every session in a project where software-engineering is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one of these rules cannot be kept with a rule of another capability's, stop the step and report the clash, rather than choose between them. Where a project's rule cannot be kept with one of these, this one binds. The loaded file is generated from `.pkit/capabilities/software-engineering/rule-sets/swe.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync or install edits neither.*

### RS-SWE-001 — While building, run the tests of what you changed

**While you build a change, run the tests of what it changes and the checks the project names as its fast checks.** Where the project runs its full suite in a gate on each change before it lands, you need not run it yourself. Where it runs it nowhere, run it once before you hand the change over, or say that you could not ([project-kit#2269](https://github.com/aleskalfas/project-kit/issues/2269)).
