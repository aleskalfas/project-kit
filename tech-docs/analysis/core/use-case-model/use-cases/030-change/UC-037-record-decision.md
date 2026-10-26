---
id: UC-037
title: Record my decision beside the methodology's
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
  - ACT-ci-pipeline
  - ACT-merge-authoriser
  - ACT-operator
requirements:
  - REQ-002
  - REQ-004
  - REQ-005
  - REQ-009
  - REQ-012
after:
  - [UC-014, UC-049]
shortfalls:
  - at: 3
    issue: "#1765"
    record: ADR-034#1
  - at: "2d"
    issue: "#1884"
    record: COR-004
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/decisions.py
        - src/project_kit/decisions_validate.py
        - src/project_kit/decisions_check_diff.py
        - src/project_kit/record_points.py
        - src/project_kit/refs.py
        - src/project_kit/cli.py
        - .pkit/lifecycle/ownership.py
        - .pkit/skills/core/decision-author.md
        - .pkit/decisions/README.md
        - .pkit/rules/core.md
      record:
        - COR-024
        - COR-025
        - COR-051#5
        - COR-058#1
        - COR-058#3
        - COR-058#4
        - COR-058#7
        - COR-058#8
        - COR-054#3
        - COR-054#4
        - COR-049#5
        - COR-055#1
        - COR-004
        - ADR-034#1
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - ACT-ci-pipeline
        - ACT-merge-authoriser
        - ACT-operator
        - REQ-002
        - REQ-004
        - REQ-005
        - REQ-009
        - REQ-012
---

# UC-037 — Record my decision beside the methodology's

**Goal:** Record my decisions beside the methodology's, and build only on accepted ones.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): drafts the [decision record](../../../glossary.md#term-decision-record--decision-record) through the `decision-author` [skill](../../../glossary.md#term-skill--skill), which pairs with the [stamp](../../../glossary.md#term-stamp--stamp). The agent leaves the record `proposed`, so that a person accepts it before any work builds on it ([UC-040](UC-040-accept-through-review.md)). The architect, as custodian of the architecture records, may draft an ADR ([COR-024](../../../../../../.pkit/decisions/core/COR-024-critic-and-architect-agents.md)).
- **CI pipeline** (`ACT-ci-pipeline`): runs the numbering check on each [pull request](../../../glossary.md#term-pull-request--pull-request) where the [project](../../../glossary.md#term-project--project) makes it a line of its check gate. It names the pull request's target as the [base](../../../glossary.md#term-base--base).
- **Merge authoriser** (`ACT-merge-authoriser`): accepts the record by their own review, before any work builds on it (UC-040).
- **Operator** (`ACT-operator`): is asked before the stamp writes in another repository than the session's own. So no such write happens silently ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- Work that builds on a [decision record](../../../glossary.md#term-decision-record--decision-record) cites only an accepted one, as the [acceptance gate](../../../glossary.md#term-acceptance-gate--acceptance-gate) asks. `pkit refs rot` lists each accepted record whose body cites a proposed one, and fails nothing. No check of the [system](../../../glossary.md#term-system--system) fails a [change](../../../glossary.md#term-change--change) for what it builds on, save a [rule](../../../glossary.md#term-rule--rule)'s origin (core rule 2 and [COR-051 point 5](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#5-origins-checked-deterministically)).
- The developer writes records only where the [project](../../../glossary.md#term-project--project) authors them, never in a folder of [synced copies](../../../glossary.md#term-synced-copy--synced-copy). Nothing stops an edit or a record written by hand there. [Sync](../../../glossary.md#term-sync--sync) owns those folders (core rule 1).

**Trigger:** The developer makes a choice that the [project](../../../glossary.md#term-project--project)'s records do not hold yet, such as a technology or a way of working.

**Main path:**

1. The developer picks the record's namespace by its scope ([COR-025](../../../../../../.pkit/decisions/core/COR-025-adr-decision-space.md)). The namespace is `project` for how the [project](../../../glossary.md#term-project--project) works, and it is `adr` for what the project builds and why. It is a [capability](../../../glossary.md#term-capability--capability)'s name for a decision inside a capability the project authors.
2. The developer runs `pkit new decision <namespace> <slug>`, or an AI agent runs it through the `decision-author` [skill](../../../glossary.md#term-skill--skill).
3. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** `pkit new decision` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

4. The system checks the slug and the namespace. It numbers the record one past the highest its namespace's folder holds, in the working tree or on the [default branch](../../../glossary.md#term-default-branch--default-branch) ([COR-054 point 3](../../../../../../.pkit/decisions/core/COR-054-default-branch.md#3-the-override-is-a-base-not-a-declaration)).
5. The system stamps `<PREFIX>-<NNN>-<slug>.md` with `status: proposed`, today's date and the author git names. It writes the four sections, with a first [point](../../../glossary.md#term-point--point) heading under the Decision, `### 1. Point title` ([COR-058 point 1](../../../../../../.pkit/decisions/core/COR-058-record-points.md#1-a-point-is-a-heading-with-its-id-and-title)). It prints `Stamped: <path>`.
6. The developer writes the title, the context, each point under a heading of its own, the rationale and the implications. Each point keeps its id for good ([COR-058 point 3](../../../../../../.pkit/decisions/core/COR-058-record-points.md#3-a-new-point-takes-the-next-unused-number-and-no-point-is-renumbered)).
7. The developer runs `pkit decisions validate`. The system checks that no two records of one namespace share an id, and that each record's id matches its file name. It checks each record's points, retired ids and stubs too ([COR-058 point 7](../../../../../../.pkit/decisions/core/COR-058-record-points.md#7-what-validation-checks)).
8. The developer runs `pkit decisions check-diff`. The system compares each record the [change](../../../glossary.md#term-change--change) touches with where the branch left its [base](../../../glossary.md#term-base--base). It also compares the ids the change takes with those the base took since ([COR-058 point 8](../../../../../../.pkit/decisions/core/COR-058-record-points.md#8-a-changes-numbering-is-checked-against-its-base)). It lists each point of an accepted record that the change adds, alters or retires, and fails nothing on that list (`decisions_check_diff.py`).
9. The developer commits the record as `proposed`. Work that builds on it waits until the merge authoriser accepts it ([UC-040](UC-040-accept-through-review.md)).

**Variants:**

- **1a.** In the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), the namespace may be `core`, for a principle that fits any [project](../../../glossary.md#term-project--project). The [system](../../../glossary.md#term-system--system) stamps a core record in `.pkit/decisions/core/`, which [UC-041](UC-041-keep-core-records-true.md) keeps fit for any project.
- **1b.** The decision refines an accepted record, and overturns nothing it decides. The developer edits the record in place, with no revision marker, and stamps nothing. A new [point](../../../glossary.md#term-point--point) takes the next unused number, and no point is renumbered ([COR-058 point 3](../../../../../../.pkit/decisions/core/COR-058-record-points.md#3-a-new-point-takes-the-next-unused-number-and-no-point-is-renumbered)). The path goes on at step 7.
- **1c.** On the path of 1b, a point is dropped, split or merged so that no point continues its claim. Its id goes into `retired-points`, with the points that took its text, and a one-line stub stays where it stood ([COR-058 point 4](../../../../../../.pkit/decisions/core/COR-058-record-points.md#4-a-retired-point-leaves-an-entry-and-a-stub)).
- **1d.** The decision overturns an accepted record. The new record sets `supersedes:` to the old record's id, and the path goes on at step 2. Once the new record is accepted, an edit of its own marks the old one `superseded`, as the decision-record specification says. A record overturned only in part stays accepted, its top line reading *Partially superseded by …*.
- **2a.** The namespace is `adr`, and the [overlay](../../../glossary.md#term-overlay--overlay) names a folder in `adr-records`. The system stamps the record there. It refuses a folder that does not exist, naming `mkdir -p <folder>`, and a folder inside `.pkit/` ([COR-025](../../../../../../.pkit/decisions/core/COR-025-adr-decision-space.md)).
- **2b.** The namespace is `adr`, and the overlay names no folder in `adr-records`. The system derives the folder from the internal [documentation root](../../../glossary.md#term-documentation-root--documentation-root), as `architecture/decisions/` under it. It records the folder in the overlay before it stamps, and says so ([COR-049 point 5](../../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#5-a-derived-location-is-recorded-when-it-is-first-used)). It names `pkit sync`, which deploys the [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) that read the folder.
- **2c.** On the path of 2b, the folder already holds documents, which the recording puts within reach of every agent that reads it. A terminal is asked once, and `--yes` consents without a prompt. Declined, or with nobody to ask and no `--yes`, the system records nothing and stamps nothing. The use case ends.
- **2d.** The developer passes `--dry-run`, as to each command whose edit reaches past what the person named. The system names the record it would [stamp](../../../glossary.md#term-stamp--stamp) and the folder it would record, and writes nothing ([REQ-009](../../../requirements/quality/REQ-009-preview-before-change.md)).

> [!WARNING]
> **Not built yet:** `pkit new decision` takes no `--dry-run`, and refuses the flag. [COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md) decides that a command whose widest effect reaches past what the person named offers one, and #1884 tracks it.

- **2e.** The namespace is `adr`, and the project holds no overlay. The system refuses, naming the overlay that ADR support needs, and writes nothing. The use case ends.
- **4a.** The [default branch](../../../glossary.md#term-default-branch--default-branch) cannot be read in this clone. The system says so on standard error, and numbers past the working tree alone ([COR-054 point 4](../../../../../../.pkit/decisions/core/COR-054-default-branch.md#4-unresolved-report-never-guess)). A record on the default branch may then hold the number already, which step 8 finds.
- **4b.** The slug is not kebab-case, or a record of the namespace holds it already. The system refuses and writes nothing, and the path rejoins at step 2.
- **4c.** The namespace names no [capability](../../../glossary.md#term-capability--capability) the project holds. The system refuses and writes nothing, and the use case ends.
- **4d.** The namespace is `core` outside the methodology's source repository, or names a capability whose files the project receives as [synced copies](../../../glossary.md#term-synced-copy--synced-copy). Such a capability is kit-shipped in a project other than the methodology's source repository, or externally sourced in any project. The system refuses and writes nothing, naming `project` and `adr` as where the project's decision goes (core rule 1). The use case ends.
- **7a.** Two records of one namespace share an id, or a record's id differs from its file name's number. The system fails, naming each, and the path rejoins at step 6.
- **7b.** A record's points break what [COR-058 point 7](../../../../../../.pkit/decisions/core/COR-058-record-points.md#7-what-validation-checks) holds, such as a stub whose sentence differs from its entry. The system fails, naming `<file>#<id>`, and the path rejoins at step 6. A duplicate point id, a gap in the ids or a misspelt point heading draws only a warning.
- **7c.** A line of a record narrates its own revision, such as an amendment heading or a correction stamped with a date. The system warns of it, naming the file and the line, and never fails on it. The developer states the fact plainly instead.
- **7d.** The project holds a record as a synced copy, such as a core record in a project that is not the source repository. [Validation](../../../glossary.md#term-validation--validation) reads that record for its id alone, since the project cannot mend it ([COR-055 point 1](../../../../../../.pkit/decisions/core/COR-055-validation.md#1-what-validation-owns)).
- **8a.** The [base](../../../glossary.md#term-base--base) resolves to no commit. The check refuses and names its fix, and never guesses a base ([COR-054 point 4](../../../../../../.pkit/decisions/core/COR-054-default-branch.md#4-unresolved-report-never-guess) and [REQ-004](../../../requirements/quality/REQ-004-missing-answer-never-clean.md)). The path rejoins at step 8.
- **8b.** Another [change](../../../glossary.md#term-change--change) landed a record of the same number on the default branch since the branch left it. The check fails, naming the record and the next unused number, since the first to land keeps its number. The developer moves the record to the next unused number, and the path rejoins at step 7.
- **8c.** The change renumbers a point, or drops one without retiring it. The check fails, naming `<file>#<id>`, and the path rejoins at step 6.
- **8d.** The project makes the numbering check a line of its check gate. The CI pipeline runs `pkit decisions check-diff` on each [pull request](../../../glossary.md#term-pull-request--pull-request), with `PKIT_CHECK_BASE` naming its target, and the check passes.
- **9a.** The merge authoriser approved the record's addition and its acceptance together. The developer commits it as `accepted`, as the `decision-author` [skill](../../../glossary.md#term-skill--skill) allows.
- **9b.** On the path of 1b or 1c, the developer commits the edit, and the record stays accepted.

**Postconditions:** A new record lies in its namespace's folder, numbered past every record the [default branch](../../../glossary.md#term-default-branch--default-branch) holds there. Each of its points stands under an id it keeps for good. It stays `proposed` until the merge authoriser accepts it, and a refined record stays accepted.

**Minimal guarantees:**

- A [stamp](../../../glossary.md#term-stamp--stamp) that refuses writes no record, and records no folder in the [overlay](../../../glossary.md#term-overlay--overlay) (`decisions.py`).
- The stamp writes in the overlay only the folder it derived, and only where the [project](../../../glossary.md#term-project--project) set none ([COR-049 point 5](../../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#5-a-derived-location-is-recorded-when-it-is-first-used) and [REQ-002](../../../requirements/functional/REQ-002-project-owned-writers.md)).
- A [default branch](../../../glossary.md#term-default-branch--default-branch) the stamp cannot read is said, and its number is taken from the working tree alone, never guessed ([COR-054 point 4](../../../../../../.pkit/decisions/core/COR-054-default-branch.md#4-unresolved-report-never-guess)).
- `pkit decisions validate` and `pkit decisions check-diff` write nothing, whatever they find ([REQ-005](../../../requirements/quality/REQ-005-reading-writes-nothing.md)).
- [Validation](../../../glossary.md#term-validation--validation) never fails a project on a [synced copy](../../../glossary.md#term-synced-copy--synced-copy), which the project cannot mend ([COR-055 point 1](../../../../../../.pkit/decisions/core/COR-055-validation.md#1-what-validation-owns)).
