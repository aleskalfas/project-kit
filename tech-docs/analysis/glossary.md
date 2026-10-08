---
TERM-system:
  name: system
  status: active
  definition: software under discussion, which you install, run and extend
  pkit:
    friction: {}
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-system — system

**Example:** the system ends a pull request's landing `merged`, naming the head the pull request merged at (`pkit pull-request land`).

**Distinctions:**

- **pkit:** the product's name, kept in prose and in commands. The analysis says *the system* for the same software (PR #1374).
- **A system:** other software, such as the hosting service or the harness. The analysis names it for what it is, never a system (PR #1345, question 12).
- **A platform:** in COR-009, the hosting service a project's remote lives on. It is other software, never the system.
- **The methodology:** the body of decision records, rules and conventions the system ships and enforces. It is a term of its own, whose *Distinctions* point back here.
