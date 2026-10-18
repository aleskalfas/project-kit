---
TERM-acceptance-gate:
  name: acceptance gate
  status: active
  definition: rule that work builds only on decisions and rules already accepted, and never on proposed ones
  pkit:
    friction:
      anchors:
        path:
          - .pkit/decisions/README.md
          - .pkit/rules/core.md
          - .pkit/skills/core/decision-author.md
        record:
          - COR-025
          - COR-051#4
          - COR-051#5
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
TERM-decision-record:
  name: decision record
  status: active
  definition: document stating one choice with its context and reasons, numbered in a namespace and binding once accepted
  pkit:
    friction:
      anchors:
        path:
          - src/project_kit/decisions.py
        record:
          - COR-025
          - COR-058#1
          - COR-058#3
TERM-epic:
  name: EPIC
  status: active
  definition: issue for one outcome, often spanning quarters, under which the Features, Umbrellas and Tasks that reach it are filed
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
        record:
          - project-management:DEC-004
          - project-management:DEC-008
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
TERM-head:
  name: head
  status: active
  definition: latest commit of a branch, such as the one a pull request would merge
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/land-work.py
          - src/project_kit/pull_request_landing.py
        record:
          - project-management:DEC-028
          - project-management:DEC-055#3
TERM-methodology:
  name: methodology
  status: active
  definition: body of decision records, rules and conventions the system ships and enforces
  pkit:
    friction:
      unanchored-because: It names the whole body the system ships, so an anchor on its records and rules would match every change to them. COR-007 says what a methodology is in general, not what this word names here.
TERM-page:
  name: page
  status: active
  definition: document of a space that declares its kind, and names the one reader it is written for
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        record:
          - living-docs:DEC-001#1
          - living-docs:DEC-001#3
          - living-docs:DEC-001#4
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
TERM-revalidation-record:
  name: revalidation record
  status: active
  definition: held document logging one review of artefacts against a version of the system, kept only when the review has something to say
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/scripts/_lib/revalidation.py
        record:
          - software-analysis:DEC-001#5
          - software-analysis:DEC-001#6
TERM-space:
  name: space
  status: active
  definition: "set of documents for one audience, under a documentation root or in places assigned to it, which its definition's rules bind"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        record:
          - living-docs:DEC-001#1
          - living-docs:DEC-001#2
          - COR-049
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
TERM-system:
  name: system
  status: active
  definition: software under discussion, which you install, run and extend
  pkit:
    friction:
      unanchored-because: It names the whole of pkit, so an anchor on its code would match every change. No record defines it.
TERM-use-case:
  name: use case
  status: active
  definition: "description of one actor's goal and of how the system fulfils it, kept in the analysis as an artefact"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/scripts/_lib/settled_use_cases.py
        record:
          - software-analysis:DEC-001#1
          - software-analysis:DEC-001#3
          - project-management:DEC-054#1
TERM-verdict:
  name: verdict
  status: active
  definition: "reviewer agent's judgement of a pull request at one commit, posted with the marker the merge gate reads"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
        record:
          - project-management:DEC-028
          - project-management:DEC-055#3
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-acceptance-gate — acceptance gate

**Example:** a change would cite a project record that is still proposed, so the change's author has the record accepted first, or pauses the change.

**Distinctions:**

- **Acceptance:** the change of a record's status from `proposed` to `accepted`, in a commit of its own. The gate asks for it before dependent work starts. An agent makes it only once the person it works for approves (the `decision-author` skill).
- **A rule's acceptance:** a rule an agent drafted binds only once a person's review accepts it (COR-051 point 4). An accepted rule rests only on accepted records (COR-051 point 5).

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

## TERM-decision-record — decision record

**Example:** PRJ-002 is one of project-kit's own, beside the methodology's core ones, such as COR-050.

**Distinctions:**

- **Point:** a numbered part of a record's Decision. A point keeps its id for good, even when the record is refined in place (COR-058 points 1 and 3).
- **Namespace:** where a record is numbered, apart from the others: the core's `COR`, the project's `PRJ`, its architecture's `ADR`, and each capability's `DEC` (COR-025). `pkit new decision` names one as `core`, `project`, `adr` or the capability's name.
- **Rule:** a statement in a rule set of what must hold of an artefact. A rule's origin may name the record it rests on.

## TERM-epic — EPIC

**Example:** the planner's intent to write project-kit's analysis is filed as one EPIC, with a Task under the EPIC for each area.

**Distinctions:**

- **Milestone:** the hosting service's field that scopes issues by date. An EPIC states an outcome, not a date (project-management DEC-004).
- **Task:** the issue type for one change, the only type that gets a branch and a pull request. Its parent is an EPIC, a Feature, an Umbrella or a Milestone (`issue-types.yaml`).
- **Who files one:** only the planner commits the project to an outcome, so the planner's authority files it (project-management DEC-008).

## TERM-friction — friction

**Example:** a change modifies `src/project_kit/release.py`, and the change check reports friction on `.pkit/release/README.md` until the page carries an answer.

**Distinctions:**

- **Debt:** what the whole-repository check reports on the default branch. Friction nobody answered is stale debt, and a deferral is deferred debt (COR-050 point 9).
- **The `friction` block:** the block in an artefact's front matter that holds its anchors and answers (COR-050 point 1). It is no finding.

## TERM-head — head

**Example:** `land-work` stops ready naming the pull request's head, so the merge authoriser authorises the merge of that one commit.

**Distinctions:**

- **A later head:** a commit pushed after the authorised one, along the branch's own line. The authorisation covers it only where every change since lies inside `revalidated` blocks (project-management DEC-055 point 3). A clean merge of the target counts as no change.
- **What stands for a head:** a check's result, a verdict and an authorisation to merge. A verdict may stay fresh across a change outside what its reviewer checks (project-management DEC-028).
- **Base:** what a check compares a change with. The head is the change's own end.

## TERM-methodology — methodology

**Example:** the developer records a decision beside the methodology's, and builds only on accepted records, as the methodology's acceptance gate asks.

**Distinctions:**

- **The system:** the software under discussion, which you install, run and extend. A sentence that means the software, such as one about installing it, says *the system* (PR #1374). It is a term of its own, whose *Distinctions* point back here.
- **The methodology maintainer:** an actor, "whoever maintains a distribution of the methodology" (`ACT-methodology-maintainer`). The role also works on parts of the system, such as the backbone and its releases. So its name, which the maintainer kept (PR #1374), uses the word more widely than this term.
- **A capability's discipline:** what one capability packages, for a project to install or leave out (COR-017). A capability the system ships carries one part of the methodology, never the whole. A capability a project or its organisation writes is their own (COR-031 and COR-041).

## TERM-page — page

**Example:** `.pkit/cli/README.md` is one of project-kit's user space, and anchors the code of the commands it describes.

**Distinctions:**

- **Unclassified document:** a document in a space's places that declares no page kind, even one that names a reader. It is none until onboarding classifies it (living-docs DEC-001 point 4).
- **Decision record:** never one, though a page may anchor a record as the home of the facts the record decides (living-docs DEC-001 points 3 and 4).
- **Grounding:** a page's anchors ground each statement it makes, as a rule of `LDOC` asks. A page that breaks the rule is still a page (living-docs DEC-001 point 3).

## TERM-place — place

**Example:** project-kit lists `.pkit/cli/README.md` in `friction.places`, so the backbone reads that page's anchors.

**Distinctions:**

- **Documentation root:** where a project keeps its documents, for users or for itself. A place may lie inside a root, and a root may hold files no place reads.
- **Synced tree:** a folder that sync copies into the project from elsewhere, such as the methodology's records. It is never a place, or each refresh would read as friction (COR-050 point 14).
- **Held folder:** a folder a component declares for its held documents. No place reads a file in it as an artefact (COR-050 point 1).

## TERM-revalidation-record — revalidation record

**Example:** before a change is built, a planned revalidation record names the issue's body the developer reviewed, and the time its text was read. The record also names each gap, and the issue that builds the missing behaviour.

**Distinctions:**

- **Revalidation:** the answer on an artefact itself, which clears its friction. The held document never clears friction (software-analysis DEC-001 point 5).
- **When one is kept:** for a planned review, or for a gap or a regression found. A person's decision that an artefact was stale is kept too (software-analysis DEC-001 points 5 and 6).
- **Planned record:** a revalidation record of a review made before the code. It names the design it reviewed in `reviewed-against`, each source at its version (software-analysis DEC-001 point 6).

## TERM-space — space

**Example:** project-kit's technical one is `tech-docs/`, with `CONTRIBUTING.md` and the release guide, and its definition, `TECH`, inherits `LDOC`.

**Distinctions:**

- **Documentation root:** where a project keeps its documents, for users or for itself (COR-049). A space holds a root's documents, and those of the places the project assigns to it.
- **Definition:** the rule set of the project's own that names the rules the space's pages follow (living-docs DEC-001 point 2).

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

## TERM-use-case — use case

**Example:** UC-012 describes landing a change, so an issue that plans a change to landing names it in its `## Use cases` section.

**Distinctions:**

- **Journey:** one actor's path across several of its use cases, with the seams between them (software-analysis DEC-001 point 1).
- **A settled one:** one the default branch holds. Planning and issue bodies are checked against those alone (project-management DEC-054 point 1).
- **Need:** what an actor wants, in its front matter. A use case's goal is one of its actor's needs.

## TERM-verdict — verdict

**Example:** `docs-reviewer` approves the head of a pull request, and the merge gate counts that approval while it still stands for the head that merges.

**Distinctions:**

- **Finding for a person:** a passage a reviewer tags `[person]`. It withholds no approval, and waits for the merge authoriser (project-management DEC-028).
- **Authorisation to merge:** the person's, never a reviewer's (project-management DEC-055 point 3).
- **Merge gate:** the checks and approvals a merge waits for. A missing or unreadable verdict never satisfies it (project-management DEC-028).
