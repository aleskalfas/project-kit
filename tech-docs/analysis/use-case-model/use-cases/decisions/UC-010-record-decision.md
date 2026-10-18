---
id: UC-010
title: Record my decision beside the methodology's
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
  - ACT-merge-authoriser
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/decisions.py
        - src/project_kit/capability_namespace.py
        - src/project_kit/cli.py
        - src/project_kit/decisions_validate.py
        - src/project_kit/decisions_check_diff.py
        - src/project_kit/validate.py
        - src/project_kit/rule_sets.py
        - .pkit/skills/core/decision-author.md
        - .pkit/agents/core/critic.md
        - .pkit/agents/core/architect.md
        - .pkit/agents/core/methodology-reviewer.md
        - .pkit/rules/core.md
        - .pkit/decisions/README.md
      record:
        - COR-001
        - COR-005
        - COR-012
        - COR-024
        - COR-025
        - COR-051#4
        - COR-051#5
        - COR-054#4
        - COR-058#3
        - COR-058#4
        - COR-058#7
        - COR-058#8
        - COR-058#9
        - software-analysis:DEC-001#11
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - ACT-merge-authoriser
---

# UC-010 — Record my decision beside the methodology's

**Goal:** Record my decisions beside the methodology's, and build only on accepted ones.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): an agent with the `decision-author` skill drafts the record. The agent shows the developer the draft before committing it (the `decision-author` skill). The `critic` and the `methodology-reviewer` challenge the draft and never change it. The `architect` reviews it too, and writes the ADRs it keeps (COR-024 and COR-025).
- **Merge authoriser** (`ACT-merge-authoriser`): reviews the record and accepts it. The record binds only from then on.

**Preconditions:** None.

**Assumptions:**

- Work builds only on accepted records, and nothing at run time stops work that cites a proposed one (the acceptance gate, core rule 2). Only an accepted rule whose ground is a record not yet accepted fails validation (COR-051 point 5).
- Accepting a record is a person's act: an agent marks a record accepted only once the person it works for approves (the `decision-author` skill). A rule an agent drafted binds once a person's review accepts it (COR-051 point 4). No record says who accepts a decision record.
- The reviewers advise, and none of them rejects the draft by itself (COR-024).
- The record anchors no analysis artefact, not even a use case it answers (software-analysis DEC-001 point 11). No check finds such an anchor in general.
- In an adopting project, a core record arrives by sync, and nobody edits it there (core rules 1 and 4).

**Trigger:** The developer meets a choice that no accepted record settles.

**Main path:**

1. The developer, or an agent with the `decision-author` skill, stamps the record: `pkit new decision <namespace> <slug>`. The command's namespace is `project` for a PRJ record, `adr` for an ADR, or a capability's name for its DEC (COR-005 and COR-025).
2. The system numbers the record one past the highest its namespace holds, in the working tree or on the default branch. It writes the record `status: proposed`, with its front matter and headings, and prints `Stamped: <path>`.
3. The developer drafts the record's parts:
   - its Context
   - its Decision, with one heading for each point
   - its Rationale and its Implications
4. The `critic` challenges the draft. The `architect` reviews it next, where it touches the system's larger shape, and then the `methodology-reviewer` checks its disciplines (COR-024). The developer answers each finding in the draft.
5. The developer runs `pkit decisions validate` and `pkit validate`. They check the record's id and its points (COR-058 point 7), and the status of a core or a project record (`validate.py`).
6. The developer runs `pkit decisions check-diff`, which compares each record the change touches with where the branch left the default branch (COR-058 point 8).
7. The merge authoriser reviews the record and accepts it. The developer changes `status: proposed` to `status: accepted` in a commit of its own.
8. Work that builds on the decision starts once the record is accepted.

**Variants:**

- **1a.** The question is too large for one record. The developer thinks it through in a scratchpad note first, with `pkit new scratchpad <slug>`. The note retires once it has produced the record (COR-012), and the path rejoins at step 1.
- **1b.** The command's namespace is none of `core`, `project`, `adr` or the name of a capability the project holds. The stamp refuses with `unknown namespace '<namespace>': …`, and the path rejoins at step 1.
- **1c.** A record of the namespace already has the slug. The stamp refuses with `a record with slug '<slug>' already exists in the <namespace> namespace.`, and the path rejoins at step 1.
- **1d.** The record is an ADR. The `architect` agent, the ADRs' custodian, writes or audits it (COR-025). The path goes on at step 2.
- **2a.** The default branch cannot be read. The stamp numbers past the working tree alone, and warns: `… is numbered past the working tree alone, so a record on the default branch may already hold its number (COR-054 point 4).`
- **3a.** The decision refines an accepted record whose points are headings, rather than adding a record. The developer edits that record in place, as the decision records' README asks (COR-058 points 3 and 4):
  - a new point takes the next unused number, and no point is renumbered or its id reused
  - a dropped point is retired, with an entry in `retired-points` and a one-line stub
  - the record carries no revision marker, and no word that makes sense only against the old text

  The path goes on at step 4.
- **3b.** The decision refines a record in list form. A point inserted into its numbered list moves the numbers after it, until the record is converted to point headings (COR-058 point 9). The path goes on at step 4.
- **3c.** The decision overturns an accepted record whole. The new record sets `supersedes:` to the old record's id. The old record turns `superseded`, with a *Superseded by …* line at the top of its body, and an ADR also sets `superseded_by:`.
- **3d.** The decision overturns an accepted record in part. The new record sets no `supersedes:`. The old record stays accepted, and its top line reads *Partially superseded by …*.
- **5a.** Two records claim one id, or a record's front matter names another id than its file. `pkit decisions validate` fails, naming them, and the path rejoins at step 3.
- **5b.** A line of the record narrates its own revision, such as "this record originally …". `pkit decisions validate` warns of it, and never fails on it.
- **6a.** The change moves a point's text to another id, or drops a point without retiring it. `pkit decisions check-diff` fails, naming the record and the id, and the path rejoins at step 3.
- **6b.** Another change took the record's number, or a point's, on the default branch since the branch left it. `pkit decisions check-diff` fails, naming the next unused number. The developer moves the record or the point to that number, and the path rejoins at step 6.
- **7a.** The merge authoriser does not accept the record. It stays `proposed`, and no work builds on it. A rejected proposal is deleted before it lands, since a record has no `rejected` status (the decision records' README).

**Postconditions:** The record stands in its namespace, beside the methodology's, accepted after the merge authoriser's review, with every point id it held kept.

**Minimal guarantees:**

- A stamped record always opens `proposed` (`decisions.py`).
- A stamped record's number is past each one its namespace holds in the working tree or on the fetched default branch (`decisions.py`).
- Where `pkit decisions check-diff` runs, it fails on a point whose text moved to another id, and on a point dropped without being retired. It fails too on an id another change took first (COR-058 point 8).
- An accepted rule never rests on a record that is not accepted (COR-051 point 5, and `rule_sets.py`).
