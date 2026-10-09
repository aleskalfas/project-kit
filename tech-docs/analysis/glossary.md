---
TERM-methodology:
  name: methodology
  status: active
  definition: body of decision records, rules and conventions the system ships and enforces
  pkit:
    friction:
      unanchored-because: It names the whole body the system ships, so an anchor on its records and rules would match every change to them. COR-007 says what a methodology is in general, not what this word names here.
TERM-system:
  name: system
  status: active
  definition: software under discussion, which you install, run and extend
  pkit:
    friction:
      unanchored-because: It names the whole of pkit, so an anchor on its code would match every change. No record defines it.
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-methodology — methodology

**Example:** the developer records a decision beside the methodology's, and builds only on accepted records, as the methodology's acceptance gate asks.

**Distinctions:**

- **The system:** the software under discussion, which you install, run and extend. A sentence that means the software, such as one about installing it, says *the system* (PR #1374). It is a term of its own, whose *Distinctions* point back here.
- **The methodology maintainer:** an actor, "whoever maintains a distribution of the methodology" (`ACT-methodology-maintainer`). The role also works on parts of the system, such as the backbone and its releases. So its name, which the maintainer kept (PR #1374), uses the word more widely than this term.
- **A capability's discipline:** what one capability packages, for a project to install or leave out (COR-017). A capability the system ships carries one part of the methodology, never the whole. A capability a project or its organisation writes is their own (COR-031 and COR-041).

## TERM-system — system

**Example:** the system ends a pull request's landing `merged`, naming the head the pull request merged at (`pkit pull-request land`).

**Distinctions:**

- **pkit:** the product's name, kept in prose and in commands. The analysis says *the system* for the same software (PR #1374).
- **A system:** other software, such as the hosting service or the harness. The analysis names it for what it is, never a system (PR #1345, question 12).
- **A platform:** in COR-009, the hosting service a project's remote lives on. It is other software, never the system.
- **The methodology:** the body of decision records, rules and conventions the system ships and enforces. It is a term of its own, whose *Distinctions* point back here.
