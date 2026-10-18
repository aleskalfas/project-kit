---
TERM-anchor:
  name: anchor
  status: active
  definition: declared link from an artefact to what makes it true, such as a path, a record or another artefact
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#2
          - COR-050#7
      revalidated:
        at: 2026-10-18T17:44:37Z
        outcome: unchanged
        unchanged-because: The change lists the files of a capability's documentation location that no place or held folder of it holds. What an anchor is, and how discovery reads one, is unchanged.
TERM-answer:
  name: answer
  status: active
  definition: "statement in an artefact's `friction` block on a change to its anchors: a revalidation with its outcome, or a deferral with its reason"
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_write.py
        record:
          - COR-050#3
          - COR-050#4
      revalidated:
        at: 2026-10-18T19:14:44Z
        outcome: unchanged
        unchanged-because: "The definition still holds: this change only alters where the reading of friction since and friction resolve finds a block or list, not what an answer is or what the writers write."
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
      revalidated:
        at: 2026-10-18T17:44:38Z
        outcome: unchanged
        unchanged-because: The change lists the files of a capability's documentation location that no place or held folder of it holds, never as artefacts. What an artefact is, and where discovery finds one, is unchanged.
TERM-base:
  name: base
  status: active
  definition: branch or other reference a check compares a change with, from the commit where the change's branch left it
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
  definition: file naming the backbone or a component, the version segment a change moves it by, and a note for the changelog
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
          - src/project_kit/changesets.py
        record:
          - COR-010
TERM-conventions-corpus:
  name: conventions corpus
  status: active
  definition: set of a project's own coding standards, kept where the project names it, which the agents that write and review its code read
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-engineering/agents/software-engineer.md
        record:
          - software-engineering:DEC-001#2
          - software-engineering:DEC-001#4
          - software-engineering:DEC-002#4
          - ADR-013
TERM-debt:
  name: debt
  status: active
  definition: "stale or deferred finding of the whole-repository check, dated from the commit it originates in: the change nobody answered, or the deferral"
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
  definition: finding that something an artefact rests on changed, such as an anchor's target or the anchor list, with no answer standing for it
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
          - COR-050#9
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
  definition: path or glob the project or a component declares, within which the backbone looks for documents that carry anchors
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/friction_discovery.py
        record:
          - COR-050#1
          - COR-050#14
      revalidated:
        at: 2026-10-18T17:44:40Z
        outcome: unchanged
        unchanged-because: The change lists the files of a capability's documentation location that none of its places or held folders holds. What a place is, and which files it matches, is unchanged.
TERM-surface-change:
  name: surface change
  status: active
  definition: alteration of the system that an adopter could observe, depend on or break against
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/release.py
        record:
          - PRJ-002#D1
          - PRJ-002#D2
          - COR-050#8
      revalidated:
        at: 2026-10-18T20:02:46Z
        outcome: unchanged
        unchanged-because: This change alters which changesets reach the changelog. What counts as a surface change, and that a person judges it, stays as it was.
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
- **Registered kind:** a kind of anchor a capability adds, with the command that resolves it. The backbone resolves paths, records and artefacts itself (COR-050 point 2).

## TERM-answer — answer

**Example:** a change renames a flag that a page describes, so the developer updates the page in the same change and revalidates it `updated`.

**Distinctions:**

- **Revalidation:** an answer saying the artefact was reviewed against the change. It is `updated`, its content changed with it, or `unchanged`, with why it still holds (COR-050 point 3).
- **Deferral:** an answer that puts off one anchor's change, with a reason naming the follow-up that will answer it (COR-050 point 4).
- **The list of answers:** the change check's list of every answer a change wrote, word for word, which a reviewer works from (COR-050 point 3). The answers themselves live on the artefacts.
- **A command's answer:** what a resolver or a validator returns to the check that runs it. A missing one fails that check, and is no artefact's answer.

## TERM-artefact — artefact

**Example:** each use case of the analysis is an artefact, and so is each entry of this glossary, a collection file. So is each page project-kit lists in `friction.places`, such as `.pkit/cli/README.md`.

**Distinctions:**

- **Decision record:** an artefact only where a place holds it (COR-050 point 1). A record anchor names a record whether or not a place holds it.
- **Held document:** a file a component keeps in a folder it declares, such as a log of its reviews. It is never an artefact, even inside a place (COR-050 point 1).

## TERM-base — base

**Example:** CI names the pull request's target in `PKIT_CHECK_BASE`, so that target is each check's base. Each compares the change from where its branch left the target.

**Distinctions:**

- **Default branch:** the base of every check that names no other. A base named for one run replaces it for that run only, and never changes it (COR-054 point 3).
- **Where the branch left it:** the commit a check measures the change from, git's merge-base of the branch and the base. The base itself may have moved on since.
- **A pull request's base:** the hosting service's name for the branch a pull request targets. The analysis calls that branch the pull request's target, and CI names it as the checks' base.

## TERM-changeset — changeset

**Example:** a change adds a command to the `software-analysis` capability, so the developer adds a changeset naming `software-analysis` and `minor`.

**Distinctions:**

- **Version:** a branch never edits a version number, and declares its change in a changeset instead (PRJ-002 D1).
- **Segment:** the changeset's `kind`, one of `patch`, `minor`, `major` and `none`. It is a person's judgement of the change's surface, never read from the commit type (PRJ-002 D2).

## TERM-component — component

**Example:** the `software-analysis` capability is a component, so a change to its scripts declares a changeset that names it.

**Distinctions:**

- **Backbone:** the core every component depends on. It is released as one whole, with a version of its own (COR-010).
- **A changeset's `component`:** the field names the backbone too, as `backbone`. So a changeset names the backbone or a component.

## TERM-conventions-corpus — conventions corpus

**Example:** the `software-engineer` agent reads the conventions corpus before it writes a change's code, and checks its own diff against it.

**Distinctions:**

- **The methodology's conventions:** conventional commits, branch names and the no-shared-files invariant, which bind every project. The `convention-compliance-reviewer` checks them, and never reads the corpus (software-engineering DEC-001 point 4).
- **The reviewers' knowledge:** what each code-review agent knows of any project. The project's own rules come from the corpus alone (software-engineering DEC-002 point 4).

## TERM-debt — debt

**Example:** `pkit friction debt` lists a page stale since the commit that renamed a command it describes, with that commit's author and date.

**Distinctions:**

- **Friction:** a finding that a change owes an answer, which the change gives before it merges. Friction nobody answered stays on the default branch as stale debt.
- **Stale and deferred:** stale debt is a change nobody answered, dated from that change. Deferred debt is a deferral, dated from the commit that introduced it (COR-050 point 9).
- **Ledger:** no file lists the debt. Each run derives it from git again (COR-050 point 9).

## TERM-friction — friction

**Example:** a change modifies `src/project_kit/release.py`, and the change check reports friction on `.pkit/release/README.md` until the page carries an answer.

**Distinctions:**

- **Debt:** what the whole-repository check reports on the default branch. Friction nobody answered is stale debt, and a deferral is deferred debt (COR-050 point 9).
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
- **Synced tree:** a folder that sync copies into the project from elsewhere, such as the methodology's records. It is never a place, or each refresh would read as friction (COR-050 point 14).
- **Held folder:** a folder a component declares for its held documents. No place reads a file in it as an artefact (COR-050 point 1).

## TERM-surface-change — surface change

**Example:** a new subcommand of `pkit` is a surface change, so its pull request declares it in a changeset (PRJ-002 D1).

**Distinctions:**

- **A component's surface paths:** the paths the changeset guard reads as a component's surface. A change to one only suggests a surface change, and a person judges it (PRJ-002 D2).
- **Declared surface:** the paths a project or a component says its descriptions ought to cover. Those no artefact anchors are reported as uncovered (COR-050 point 8).

## TERM-system — system

**Example:** the system ends a pull request's landing `merged`, naming the head the pull request merged at (`pkit pull-request land`).

**Distinctions:**

- **pkit:** the product's name, kept in prose and in commands. The analysis says *the system* for the same software (PR #1374).
- **A system:** other software, such as the hosting service or the harness. The analysis names it for what it is, never a system (PR #1345, question 12).
- **A platform:** in COR-009, the hosting service a project's remote lives on. It is other software, never the system.
- **The methodology:** the body of decision records, rules and conventions the system ships and enforces. It is a term of its own, whose *Distinctions* point back here.
