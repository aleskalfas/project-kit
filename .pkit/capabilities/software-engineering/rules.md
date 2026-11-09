## Operational rules of the software-engineering capability

*These are the software-engineering capability's operational rules, kept as its loaded rule set `SWE` (COR-070). They bind on the work of every session in a project where software-engineering is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one of these rules cannot be kept with a rule of another capability's, stop the step and report the clash, rather than choose between them. Where a project's rule cannot be kept with one of these, this one binds. The loaded file is generated from `.pkit/capabilities/software-engineering/rule-sets/swe.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync or install edits neither.*

### 1. While building, run the tests of what you changed (RS-SWE-001)

**While you build a change, run the tests of what it changes and the checks the project names as its fast checks.** Where the project runs its full suite in a gate on each change before it lands, you need not run it yourself. Where it runs it nowhere, run it once before you hand the change over, or say that you could not ([project-kit#2269](https://github.com/aleskalfas/project-kit/issues/2269)).
