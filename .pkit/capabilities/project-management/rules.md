## Operational rules of the project-management capability

*These are the project-management capability's operational rules, kept as its loaded rule set `PM` (COR-070). They bind on the work of every session in a project where project-management is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one of these rules cannot be kept with a rule of another capability's, stop the step and report the clash, rather than choose between them. Where a project's rule cannot be kept with one of these, this one binds. The loaded file is generated from `.pkit/capabilities/project-management/rule-sets/pm.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync or install edits neither.*

### 1. A pull request names each issue it closes (RS-PM-001)

**A pull request that closes issues names each with a closing keyword (`Closes #N`), first in its body as project-management's template puts it.** `pkit pm edit-pr` and `pkit pm review-work` check that the body contains one (project-management DEC-013).

### 3. An issue carries one value on each required axis (RS-PM-003)

**Give each issue one value on each required axis the project's substrate map carries, and never two on one axis** (project-management DEC-012 and DEC-062).
