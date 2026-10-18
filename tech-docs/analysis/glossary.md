---
TERM-anchor:
  name: anchor
  status: active
  definition: "declared link from an artefact to what makes it true: a path, a record, or another artefact"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#2
          - COR-050#7
TERM-answer:
  name: answer
  status: active
  definition: "statement an artefact carries on a change to its anchors: a revalidation, `updated` or `unchanged` with why, or a deferral with its reason"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_write.py
        record:
          - COR-050#3
          - COR-050#4
TERM-artefact:
  name: artefact
  status: active
  definition: document with front matter, or keyed entry of a collection file, in a declared place, which carries its own anchors and answers
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#1
TERM-base:
  name: base
  status: active
  definition: "commit a check compares a change with: where the change's branch left the default branch, or left a reference named for one run"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/default_branch.py
        record:
          - COR-054#2
          - COR-054#3
TERM-changeset:
  name: changeset
  status: active
  definition: file naming a component, the version segment a change moves it by, and a note for the changelog
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/changesets.py
        record:
          - PRJ-002#D1
          - PRJ-002#D2
TERM-component:
  name: component
  status: active
  definition: "installable part of the system with a version of its own: a capability or an adapter"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/manifest.py
        record:
          - COR-010
TERM-conventions-corpus:
  name: conventions corpus
  status: active
  definition: set of a project's own coding standards, which the producer agent reads from wherever the project's agents overlay points it
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-engineering/agents/software-engineer.md
        record:
          - software-engineering:DEC-001#2
          - software-engineering:DEC-001#4
          - ADR-013
TERM-debt:
  name: debt
  status: active
  definition: change under an artefact's anchor that the default branch carries unanswered or deferred, dated from the commit it came from
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_repository.py
          - src/project_kit/friction_report.py
        record:
          - COR-050#9
TERM-friction:
  name: friction
  status: active
  definition: finding that an anchor of an artefact changed with no answer standing for that change
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_check.py
          - src/project_kit/friction_repository.py
        record:
          - COR-050#1
          - COR-050#5
          - COR-050#6
TERM-methodology:
  name: methodology
  status: active
  definition: body of decision records, rules and conventions the system ships and enforces
  pkit:
    friction:
      unanchored-because: It names the whole body the system ships, so an anchor on its records and rules would match every change to them. COR-007 says what a methodology is in general, not what this word names here.
TERM-place:
  name: place
  status: active
  definition: path or glob that the project or a component declares as holding artefacts, the only files the backbone reads for anchors
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#1
          - COR-050#14
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

## TERM-anchor — anchor

**Example:** `.pkit/release/README.md` anchors `src/project_kit/changesets.py`, so a change to that file asks the page whether it still holds.

**Distinctions:**

- **Citation:** a record or a file that a document names in its text. A change to it asks the document nothing, unless an anchor names it too.
- **Dead anchor:** an anchor that resolves to nothing, such as a glob that matches no file. It is an error, never silence (COR-050 point 7).

## TERM-answer — answer

**Example:** a change renames a flag that a page describes, so the developer updates the page in the same change and revalidates it `updated`.

**Distinctions:**

- **Revalidation:** an answer saying the artefact was reviewed against the change. It is `updated`, its content changed with it, or `unchanged`, with why it still holds (COR-050 point 3).
- **Deferral:** an answer that puts off one anchor's change, with a reason naming the follow-up that will answer it (COR-050 point 4).
- **The list of answers:** the change check's list of every answer a change wrote, word for word, which a reviewer works from (COR-050 point 3). The answers themselves live on the artefacts.

## TERM-artefact — artefact

**Example:** each use case of the analysis is an artefact, and so is each page project-kit lists in `friction.places`, such as `.pkit/cli/README.md`.

**Distinctions:**

- **Decision record:** an artefact only where a place holds it (COR-050 point 1). A record anchor names a record whether or not a place holds it.
- **Held document:** a file a component keeps in a folder it declares, such as a log of its reviews. It is never an artefact, even inside a place (COR-050 point 1).

## TERM-base — base

**Example:** CI names the pull request's target in `PKIT_CHECK_BASE`, so each check compares the change with where its branch left that target.

**Distinctions:**

- **Default branch:** the branch the project's pull requests merge into. A base named for one run replaces it for that run only, and never changes it (COR-054 point 3).
- **A pull request's base:** the hosting service's name for the branch a pull request targets. A check's base is the commit where the change's branch left that branch.

## TERM-changeset — changeset

**Example:** a change adds a command to the `software-analysis` capability, so the developer adds a changeset naming `software-analysis` and `minor`.

**Distinctions:**

- **Version:** a branch never edits a version number, and declares its change in a changeset instead (PRJ-002 D1).
- **Segment:** the changeset's `kind`, one of `patch`, `minor`, `major` and `none`. It is a person's judgement of the change's surface, never read from the commit type (PRJ-002 D2).

## TERM-component — component

**Example:** the `software-analysis` capability is a component, so a change to its scripts declares a changeset that names it.

**Distinctions:**

- **Backbone:** the core every component depends on, released as one, with a version of its own (COR-010).

## TERM-conventions-corpus — conventions corpus

**Example:** the `software-engineer` agent reads the conventions corpus before it writes a change's code, and checks its own diff against it.

**Distinctions:**

- **The methodology's conventions:** conventional commits, branch names and the no-shared-files invariant, which bind every project. The `convention-compliance-reviewer` checks them, and never reads the corpus (software-engineering DEC-001 point 4).

## TERM-debt — debt

**Example:** `pkit friction debt` lists a page stale since the commit that renamed a command it describes, with that commit's author and date.

**Distinctions:**

- **Friction:** what a change owes, and answers before it merges. Debt is what the default branch carries when nobody answered it.
- **Stale and deferred:** stale debt is a change nobody answered, dated from that change. Deferred debt is a deferral, dated from the commit that introduced it (COR-050 point 9).
- **Ledger:** no file lists the debt. Each run derives it from git again (COR-050 point 9).

## TERM-friction — friction

**Example:** a change modifies `src/project_kit/release.py`, and the change check reports friction on `.pkit/release/README.md` until the page carries an answer.

**Distinctions:**

- **Debt:** friction the default branch carries, which the whole-repository check reports with the change it came from (COR-050 point 6).
- **The `friction` block:** the block in an artefact's front matter that holds its anchors and answers (COR-050 point 1). It is no finding.

## TERM-methodology — methodology

**Example:** the developer records a decision beside the methodology's, and builds only on accepted records, as the methodology's acceptance gate asks.

**Distinctions:**

- **The system:** the software under discussion, which you install, run and extend. A sentence that means the software, such as one about installing it, says *the system* (PR #1374). It is a term of its own, whose *Distinctions* point back here.
- **The methodology maintainer:** an actor, "whoever maintains a distribution of the methodology" (`ACT-methodology-maintainer`). The role also works on parts of the system, such as the backbone and its releases. So its name, which the maintainer kept (PR #1374), uses the word more widely than this term.
- **A capability's discipline:** what one capability packages, for a project to install or leave out (COR-017). A capability the system ships carries one part of the methodology, never the whole. A capability a project or its organisation writes is their own (COR-031 and COR-041).

## TERM-place — place

**Example:** project-kit lists `.pkit/cli/README.md` in `friction.places`, so the backbone reads that page's anchors.

**Distinctions:**

- **Documentation root:** where a project keeps its documents, for users or for itself. A place may lie inside a root, and a root may hold files no place reads.
- **Synced tree:** files sync copies from elsewhere, such as the methodology's records. It is never a place, or each refresh would read as friction (COR-050 point 14).
- **Held folder:** a folder a component declares for its held documents. No place reads a file in it as an artefact (COR-050 point 1).

## TERM-system — system

**Example:** the system ends a pull request's landing `merged`, naming the head the pull request merged at (`pkit pull-request land`).

**Distinctions:**

- **pkit:** the product's name, kept in prose and in commands. The analysis says *the system* for the same software (PR #1374).
- **A system:** other software, such as the hosting service or the harness. The analysis names it for what it is, never a system (PR #1345, question 12).
- **A platform:** in COR-009, the hosting service a project's remote lives on. It is other software, never the system.
- **The methodology:** the body of decision records, rules and conventions the system ships and enforces. It is a term of its own, whose *Distinctions* point back here.
