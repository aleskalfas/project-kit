---
name: docs-author
description: Author a project's documentation under the living-docs method — a page of a space, or a space's definition — through `pkit living-docs new`, choosing the space, the kind, the reader, where the file goes and what each statement rests on, giving each fact one home, and creating a space with the scope that selects its pages. Composite skill per COR-020, paired with `pkit living-docs new`; one sub-procedure per form. Use when writing a new page, or creating a documentation space.
metadata:
  wraps_commands:
    - pkit living-docs new
    - pkit living-docs validate
composes:
  - page.md
  - space.md
gates:
  - COR-005
  - COR-020
  - COR-049
  - COR-050
  - COR-051
reads:
  records:
    - COR-008
  paths:
    - .pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md
    - .pkit/capabilities/living-docs/README.md
    - .pkit/capabilities/living-docs/rule-sets/ldoc.md
    - .pkit/capabilities/living-docs/project/config.yaml
    - .pkit/project/config.yaml
---

# Authoring documentation

This is the **living-docs** capability's authoring skill. It covers the two things a project writes under the method: a page of a documentation space, and a space's definition. `pkit living-docs new` stamps each (COR-005's skill and command pairing).

- **The command owns what it writes:** a page's front matter from its template, a definition's scope and pin, and the check of the write.
- **This skill owns the choices behind it:** which space, which kind, which reader, where the file goes, and what each statement rests on.

The rule is [living-docs:DEC-001-living-docs-discipline], and the shared rules are `LDOC`, in `.pkit/capabilities/living-docs/rule-sets/ldoc.md`. The layout, the configuration and every command are in `.pkit/capabilities/living-docs/README.md`.

## Acceptance gate

Verify each record in `gates:` is `accepted`. Halt if any is `proposed` or `superseded`.

- **COR-005**: skill and command pairing. Each operation here writes through `pkit living-docs new`, never by copying a template by hand.
- **COR-020**: the composite folder form this skill follows.
- **COR-049**: documentation roots. The definitions live under the internal root, and their location is recorded the first time a definition is placed.
- **COR-050**: anchors and friction. Every page carries the friction block, and its anchors ground what it says.
- **COR-051**: rule sets. A space's definition is a project rule set whose scope says where `LDOC` binds.

## Pick the operation

| You want to | Sub-procedure | Command |
|---|---|---|
| Write a new page for one reader of a space | `page.md` | `pkit living-docs new page <file> --space <space> …` |
| Create a space, or give the user or technical space its definition | `space.md` | `pkit living-docs new space <space>` |

A page of a space with no definition is bound by no rule, so validation checks neither its reader nor its structure. Create the space first. Open the matching sub-procedure in this folder and follow it. The framing below applies to both.

Some work is the capability's `living-docs` agent's: whether a page still holds after a change, a page's review as its reader, and onboarding. This skill writes what it, or you, decided.

## Shared framing

### Stamp, never copy

The stamp writes a page's front matter from its kind's template, and a definition's scope from the places the project declared. It records the definitions location the first time. It then runs the validator's own check, and puts back what it wrote when the write brings an error the project did not have. A copied template gets none of that.

Each command takes `--dry-run`, which makes the checks before the write, prints each file it would write and writes nothing.

### Separate roots first

Both documentation roots default to `docs/`. Two roots that are one folder give no space (DEC-001 point 1). On a fresh project, set the user and internal roots to two folders first, under `docs` in `.pkit/project/config.yaml`. That is onboarding's first step. It is an edit of the backbone configuration, so an agent asks the person first.

### After stamping

1. **Check it.** `pkit living-docs validate`, then `pkit validate` and `pkit friction check`. A page new in its change counts as revalidated, and an anchor that resolves to nothing fails.
2. **Commit** per COR-008, one page or one space per commit where you can.
