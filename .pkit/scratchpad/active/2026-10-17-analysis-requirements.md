---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-17
---

# Quality requirements and constraints in the analysis

The design round of #1393. software-analysis keeps actors, use cases, journeys and terms. This note designs the kind for what a use case does not hold: quality requirements and constraints. It works from real examples already stated in project-kit, as the maintainer decided on 17 October.

- **Read from main at `43981938`:** the records, the code and the examples below. #1370's acceptance of `SAN` landed after the reviews (`fceb363f`), and points 8 and 9 read it.
- **Citations:** records and rules by permanent id and point. Code by file and line at `43981938`.
- **Governed by:** software-analysis DEC-001, point 11 above all, which leaves this kind for a decision of its own. Points 1 to 4 give the shape every kind follows. #1447's rule links the analysis and the architecture.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Decided:** not yet. The maintainer decides the kind (#1393, criterion 4). The choices are in "For the maintainer".

## The question

What kind, or kinds, does the analysis need for quality requirements and constraints? With which parts, which anchors, which place and which ids? How does the architecture point at them, and how does one found in a decision record relate to that record?

## In short

**Two kinds, a quality requirement and a constraint, each a file of its own, numbered like use cases. A use case lists the requirements it must meet. A requirement anchors to the record that decides it, which stays its home. An architecture view anchors to the requirements it satisfies, and a record names them, as #1447 keeps records as anchor targets.**

- **Why two:** practice keeps them apart, and so do their readers. A quality requirement is a goal with a measure, which a design trades against others. A constraint is a limit the design takes as given. The analysis's places also give one kind each, with no kind field.
- **Their parts:** a quality requirement states itself, where it applies, its measure, what verifies it and why. A constraint states itself, where it applies, who imposes it and what verifies it. *Verified by* may read `None.`, and that is the point: today many examples are checked by nothing.
- **Their anchors:** each anchors to the record that decides or admits it, or else to the page that states it. It also anchors to the narrow code that verifies or holds it. A use case anchors to the requirements it lists, never the reverse.
- **The architecture:** a view anchors to the requirements it satisfies, extending #1447's rule for views. A record stays an anchor target and names the requirements it serves in its text. project-kit has no views yet, so at first this is a rule with nothing under it.
- **The home:** where a record decides a requirement, the record stays the home of that decision. Where a page states it and no record decides it, the page stays the home for now. Where only the analysis states it, the requirement is the only statement of itself.
- **Ids:** `QR-NNN` and `CNS-NNN`. `CON-` would sit one letter from `COR-`.
- **Beyond this issue:** the architect found two gaps in the anchors record that exist today, whatever this design does. They are for the maintainer apart from this kind ("Beyond this issue", below).
- **Start small:** no classification field, no anchor to actors, no list on journeys. Each comes when a reader needs it.
- **What it costs:** two kinds, two places, two id prefixes, the stamp and the check extended. No new rule in `SAN`.
- **What stays out:** a design decision no actor observes, a rule on how a text is written, and an assumption about the environment. Each already has a home.

## What the examples are

Sixty-one examples, found in four areas by searching project-kit's records, guides and code. Each was read at its source, and spot-checks confirmed the quotes.

### How they are classified

Each example reads as one of six things:

- **QR, a quality requirement:** a property of the system's behaviour that an actor relies on, and that a measure can show. Its ISO/IEC 25010:2023 characteristic follows in brackets.
- **CON, a constraint:** a limit on the solution that the design takes as given, imposed from outside it.
- **DD, a design decision:** a choice inside the design that no actor observes. It satisfies a requirement, and stays in its record.
- **RULE, a writing rule:** how a text artefact is written. Rule sets already hold such rules (COR-051).
- **ASM, an assumption:** what the environment must provide, which nothing in the system secures. A use case's *Assumptions* names it (software-analysis DEC-001 point 1).
- **OUT:** stated in no tracked file.

*Home* is where the requirement is decided. *Checked* says what holds it today: a test, a gate, a declaration, a reviewer, or nothing.

### Install, sync, upgrade, migrations and releases (L, 15)

| # | What it says | Reads as | Home | Checked |
|---|---|---|---|---|
| L1 | Every migration is safe to run twice, and a backbone migration is safe over any state | QR (reliability) | COR-010, "Migrations are mandatory", core rule 5 | `tests/test_backbone_migration_replay.py`. The "positive sign" is left to review |
| L2 | An interrupted transition never reads as finished, and the next one completes it | QR (reliability) | COR-059 point 6 | `tests/test_upgrade.py` |
| L3 | A command that copies content under another version than the project records stops, writes nothing and takes no override | QR (reliability) | COR-059 point 9 | `tests/test_sync.py`, `tests/test_capabilities_version_guard.py` |
| L4 | Only a version transition moves a recorded version, and only forward | DD | COR-059 points 2, 3 and 9 | tests |
| L5 | The pin file holds the old pin or the new one, never part of one, and an upgrade writes it last | QR (reliability) | split: ADR-049 the order, ADR-064 and `src/project_kit/router.py:282` the atomic write | `tests/test_router.py` |
| L6 | A pin that cannot be resolved never fails a command: the installed pkit runs, and warns | QR (reliability) | ADR-039 D2 | `tests/test_router.py` |
| L7 | Install and upgrade resolve compatibility across components before writing anything | QR (compatibility) | COR-010, "Cross-tier upgrade" | `tests/test_upgrade.py` |
| L8 | A choice that needs a person is never taken silently: with nobody to answer, the command writes nothing | QR (interaction capability) | COR-059 point 4 | one test, none for merge's prompting tier |
| L9 | Merge only adds to a file the project owns, and re-adds a safety entry the project removed | QR (security) | COR-002 | tests, none for the re-added entry |
| L10 | A change that breaks installed projects ships its migration in the same change | CON (organisational) | COR-010, core rule 7 | `pkit migrations check-diff`, for renames and removals only |
| L11 | A branch never writes a version number | CON (organisational) | PRJ-002 D1 and D3 | nothing refuses it: review alone |
| L12 | The release step only widens a `requires_backbone` bound, and raises a floor only when declared | DD | PRJ-002 D4 | `tests/test_release.py` |
| L13 | pkit runs on Python 3.11 or later, installed with `uv` from a git URL | CON (technical) | PRJ-003, PRJ-004 | `pyproject.toml:13`. A tagged install is unchecked |
| L14 | Migrations are shell scripts in `<major>.<minor>.0/` folders | DD | PRJ-003, COR-010 | `src/project_kit/migrations.py:36`, the scaffold |
| L15 | No release changes a core area or adapter until #1600 lands | CON (organisational), until #1600 | ADR-065 point 13 | `tests/test_area_name_clash.py` |

### Checks, validation, connections and the command line (C, 16)

| # | What it says | Reads as | Home | Checked |
|---|---|---|---|---|
| C1 | A command the backbone runs as a query ends within 30 seconds, or is killed | QR (performance efficiency) | COR-050 point 2 the bound, the lifecycle README its value | `src/project_kit/command_runner.py:141`, tests |
| C2 | A query needs no network, changes nothing and gives the same output for the same input | QR (reliability), or CON | COR-050 point 2, COR-052 point 6 | the declaration is checked, the obligations trusted (ADR-057 point 4) |
| C3 | A resolver that gives no answer fails closed, and its artefact is never judged current | QR (reliability) | COR-050 point 2 | tests |
| C4 | A validator that gives no answer fails validation, never a clean pass | QR (reliability) | COR-055 point 6 | tests |
| C5 | A gate never passes on part of a data point | QR (reliability) | COR-052 point 6 | tests. Whether a consumer chooses `fail` is unchecked |
| C6 | Reading commands never write | QR (security) | COR-050 points 12 and 13, COR-004 | one test, for `debt` and `explain` only |
| C7 | The same repository state gives the same `--json` bytes | QR (functional suitability) | the CLI README only | tests |
| C8 | Every reading document carries `schema_version`, and a reader refuses one it does not know | CON (convention) | the CLI README only | writers' constants, readers' refusals |
| C9 | Validation answers about the state, never about a base named for one run | DD | COR-055 point 2 | tests |
| C10 | The default branch is declared once and resolved in one place | DD | COR-054 points 1 and 5 | tests |
| C11 | A default branch that cannot be resolved is reported, never guessed | QR (reliability) | COR-054 point 4 | tests |
| C12 | A dead anchor is an error, never silence | QR (reliability) | COR-050 point 7 | tests |
| C13 | An invalid friction mode is an error, so enforcement is never switched off silently | QR (reliability) | COR-050 point 12 | tests |
| C14 | A suggestion of what to install never uses the network | QR (reliability), or CON | COR-053 point 8 | `tests/test_capability_plans.py:567` |
| C15 | Every mutating command takes `--dry-run` | QR (interaction capability) | COR-004 | **not met**: `config set`, `version bump` and `new decision` lack it |
| C16 | A failed run leaves a known partial state, with `validate` as the way back | QR (reliability) | COR-004 | **not measurable as stated** |

### Permissions, repositories, git and the merge (S, 16)

| # | What it says | Reads as | Home | Checked |
|---|---|---|---|---|
| S1 | A missing or unreadable reviewer verdict never satisfies the merge gate | QR (security) | project-management DEC-028 | tests |
| S2 | An approval stands only while nothing its reviewer checks has changed since the head it reviewed | QR (security) | project-management DEC-028 | tests |
| S3 | Only a verdict the reviewer path stamped counts, and a free comment cannot pass for one | QR (security) | project-management DEC-028, DEC-047 point 5 | tests |
| S4 | A required-reviewer set that cannot be resolved refuses the merge | QR (security) | project-management DEC-032 D1 and D2 | tests |
| S5 | No merge while a CI check fails or is pending, save through an audited `--bypass-ci` | QR (security) | the project-management README only | tests |
| S6 | A merge needs the person's authorisation for that pull request, tied to the head checked | CON (organisational) | project-management DEC-006, DEC-055 point 3 | `land-work --expect-head`. Whether a person gave it is unchecked |
| S7 | A session changes only its own repository, and the operator confirms a change to another | QR (security) | COR-039 | the session guards, tests. Raw `git -C` is unchecked |
| S8 | Where an allow and a deny conflict, the deny wins | QR (security) | COR-028 points 1 and 2 | tests |
| S9 | A delegated helper's whole result reaches the agent that delegated | ASM | COR-047, `.pkit/schemas/harness-requirements.yaml` | nothing yet |
| S10 | The project-manager agent may not run raw `gh` mutations | DD | the permissions README, project-management's grants | tests |
| S11 | A reviewer never changes the work it judges | CON (organisational) | the agents README, COR-024 | the critic's tool list alone |
| S12 | Commits follow Conventional Commits, and branches are named `<type>/<issue>-<slug>` | CON (convention) | COR-008 | pull-request titles checked, commit messages by reviewers only |
| S13 | No force-push to the default branch or a shared branch | CON (organisational) | project-management DEC-013 | the agents' guardrail denies every force-push, stricter than the record |
| S14 | The project-management capability needs GitHub and an authenticated `gh` | CON (technical) | project-management DEC-003 | implicit |
| S15 | A secret never goes on a command line | QR (security) | software-engineering's `security-reviewer` body | a reviewer's judgement |
| S16 | Commits are signed | OUT | no tracked file: only an operator's working brief | the operator's git |

### Documentation, analysis and the authoring tools (D, 14)

| # | What it says | Reads as | Home | Checked |
|---|---|---|---|---|
| D1 | The stamp writes each file whole, or not at all | QR (reliability) | the software-analysis README only | `tests/test_software_analysis.py:493`. living-docs' copy is untested |
| D2 | A refused stamp writes nothing | QR (reliability) | the software-analysis and living-docs READMEs | tests |
| D3 | A filler gives the whole set or no answer | QR (reliability) | COR-052 point 6, software-analysis DEC-001 point 8 | tests |
| D4 | A check's message repeats the hint of the part it fails | QR (interaction capability) | software-analysis DEC-001 point 1 | tests |
| D5 | A shipped hint holds no sentence over 25 words and no semicolon | RULE | RS-WRITE-005 and RS-WRITE-008 | a test |
| D6 | Shipped text carries no project's vocabulary or style | RULE | COR-014 | nothing |
| D7 | A tool reads data from front matter only | DD | software-analysis DEC-001 point 1 | nothing |
| D8 | A capability works with no other component installed | QR (compatibility) | software-analysis DEC-001 point 10, living-docs DEC-001 point 9 | tests |
| D9 | Uninstalling a capability never removes the project's artefacts | QR (flexibility) | software-analysis DEC-001 point 2 | untested. living-docs' captured sources are the exception |
| D10 | Artefacts and records carry no declared versions | DD | software-analysis DEC-001 point 6 | the schemas |
| D11 | A later change of root moves no document | QR (interaction capability) | COR-049 point 6 | tests |
| D12 | A declared root that does not exist yet warns rather than fails | QR (reliability) | COR-049 point 7 | tests |
| D13 | An agent proposes a fix, and never applies it | CON (organisational) | living-docs DEC-001 point 5, software-analysis DEC-001 point 5 | the agents' tool lists |
| D14 | No control or bidirectional character in a text | RULE | RS-WRITE-018 | the prose lint |

C2 was found again in this area, in living-docs DEC-001 point 4, and is counted once.

### What the list shows

Of the 61, 37 read as quality requirements and 11 as constraints. 8 are design decisions, 3 writing rules, 1 an assumption, and 1 is stated nowhere.

- **They cut across use cases.** Nearly every one binds a class of commands: every query, every migration, every gate, every writer. Few belong to one use case. So a requirement stands alone, and says in words where it applies.
- **Most have a record as their home.** A COR, PRJ, DEC or ADR decides each. Two to seven other places restate it, such as READMEs, core rules, `CLAUDE.md`, help strings and test docstrings. Five have no record: D1, C7, C8 and S5 live in a guide, and S15 in an agent's body.
- **Records mix the problem with the solution.** Several ADRs hold a requirement with its mechanism. They are ADR-011, ADR-012, ADR-014, ADR-018, ADR-024, ADR-052, and ADR-057 point 3. Eight examples are design decisions no actor observes, such as C10 and D7.
- **Their checks often fall short of their words.**
  - C15 is not met.
  - C16 cannot be measured as written.
  - L11 is enforced by nothing.
  - C2 is declared and trusted, not enforced.
  - S11 binds only the critic.
  - S13's guardrail is stricter than its record.
  - D9 and L9's re-added entry are untested.
  - S15 rests on a reviewer's judgement.

  Most of these are quality requirements. A kind that asks each requirement what verifies it, and lets the answer be `None.`, shows them.
- **Actors' needs already state some of them,** in the actor's own voice:
  - ACT-ci-pipeline: "Run the checks offline once the checkout is provisioned" (C2).
  - ACT-adopter: "Upgrade it like a dependency, … with its migrations run for me and my own files left alone" (L1, L9).
  - ACT-methodology-maintainer: "Never ship a backbone change that breaks installed projects without the migration that carries them across" (L10).
  - ACT-operator: "Be asked before an agent changes a repository other than the session's own" (S7).
  - ACT-ai-agent: "Get a delegated agent's result back whole" (S9).

  So a requirement serves an actor's need, as a use case serves its goal.
- **About ten sit on a boundary.**
  - Six between the two kinds: C2, C8, C14, S6, S11 and D13. Each reads as a property with a measure, or as a limit taken as given.
  - Two between a constraint and an assumption: L13 and S14, a limit the environment must meet.
  - Two between a constraint and a design decision: S10 and L14, a limit the design chose for itself.
- **Some are temporary.** L15 holds until #1600 lands, so a requirement must be withdrawn when its reason ends.
- **Numbers are rare.** C1's 30 seconds is the one time bound. The suite's 9 400 tests and two parallel runs are a development practice, not a property of the system (project rule 2).
- **The membership test, applied to the process constraints.** DEC-001 admits an artefact that a change to the software can make false. A process constraint passes where the software holds it, through a check, a gate, a guardrail or a file the software reads:
  - L11 passes: a branch that edits a version file changes the software, and the release step reads that file.
  - S6 passes where `land-work` pins the head, and S13 where the agents' guardrail denies the push.
  - S12 passes for pull-request titles, which the merge checks, and not for commit messages, which no software reads.
  - S16, signed commits, fails. The brief named it as an example, but no tracked file states it. It is a rule of the operator's working brief, held by the operator's git. It would pass once a tracked check required it.

  A rule that only people keep, with nothing in the software to break, stays in the project's working rules. This reads DEC-001's test as it stands, and widens it nowhere.

## Established practice

- **RUP's supplementary specification.** It holds what the use-case model does not readily capture. That is requirements that bind the whole system's function, quality requirements in FURPS+'s categories (usability, reliability, performance, supportability), and design constraints. A requirement that binds one use case goes into that use case's special requirements instead. The use-case model and the supplementary specification together make up the software's requirements.
- **arc42.**
  - Section 1.2 names the system's top three to five quality goals. They drive the architecture's decisions (sections 4 and 9).
  - Section 2 lists architecture constraints. If needed, it splits them into technical, organisational and political, and convention constraints, each with its background.
  - Section 10 refines the goals into a quality tree and quality scenarios. A scenario gives its context, its source and stimulus, and a metric or acceptance criterion.
- **The SEI's quality attribute scenario** (Bass, Clements and Kazman), which ATAM uses, has six parts: source, stimulus, environment, artefact, response and response measure.
- **ISO/IEC/IEEE 29148:2018.** It treats quality requirements and constraints as kinds of requirement beside the functional ones. Each requirement should be singular, unambiguous and verifiable, among other characteristics. It carries a rationale, a method of verification (inspection, analysis, demonstration or test), and traces back to its source. Assumptions are listed apart.
- **ISO/IEC 25010:2023.** A product quality model of nine characteristics: functional suitability, performance efficiency, compatibility, interaction capability, reliability, security, maintainability, flexibility and safety. The 2011 edition had eight, with usability and portability where interaction capability and flexibility now stand, and no safety. It classifies qualities. It is no template, and constraints are not in it.
- **Volere's fit criterion** asks the same of every requirement: a measure that shows whether a solution meets it.

The common thread: quality requirements and constraints sit beside the use cases, not inside them, unless one binds a single use case. Each is singular, gives its reason, and says how it is verified. Constraints and qualities are kept apart, and decisions trace back to the qualities they serve.

## Forces

- **The membership test** (software-analysis DEC-001, Context): an artefact belongs if a change to the software can make it false. Code can break a quality requirement, or a constraint the software holds, and a decision can make one stale. So both pass, and revalidation's four outcomes fit them unchanged.
- **One home.** Most examples are decided in a record already. A second statement can drift. Friction catches a drift, but only where the requirement anchors to the record.
- **The problem apart from the solution** (#1447). The analysis says what the system must do. The architecture says how. Records hold both.
- **Cross-cutting.** A requirement anchored from many use cases, or to many, is flagged on every edit of each. COR-050 point 7 warns of anchors that broad.
- **Start small** (DEC-001 point 11). The need is real now: EPIC #1643 asks each area of project-kit's analysis for its requirements.
- **Universal.** The kinds ship to every adopter (COR-014). So their parts, hints and examples come from practice, not from project-kit's own content or style.

## The design

### 1. Two kinds

**A quality requirement and a constraint, each a kind of its own.**

- **The analysis's places require it.** Each place gives one kind, with no kind field, and each structure is keyed by kind (DEC-001 points 1 and 2). One kind with a type field would need a kind field and a structure per type, which neither DEC-001 nor the structures' schema has.
- **Practice keeps them apart.** arc42 gives each a section of its own. RUP lists design constraints apart from the qualities. 29148 names them as two kinds of requirement. 25010 classifies qualities only.
- **Their readers treat them apart.** A design trades quality requirements against each other, and against cost. It takes a constraint as given.
- **Their parts differ.** A quality requirement has a *Measure*, which may never read `None.`, since a quality nobody can measure is no requirement (29148, verifiable). A constraint has no measure. It names who imposes it.
- **The cost of the blur.** Six of the 48 could go either way. Moving one later means withdrawing it and stamping it again under the other prefix. The skill gives the test that decides: a property with a measure is a quality requirement, and a limit taken as given is a constraint.

### 2. Their parts and forms

In the shape the other kinds declare in `schemas/artefact-kinds.yaml`. Every part is required, as for every kind (DEC-001 point 1). The hints and examples use the plain report domain the shipped kinds use, never project-kit's own content (COR-014).

```yaml
quality-requirement:
  sections:
    - id: heading
      type: heading
      level: 1
      example: "# QR-001 — A failed export leaves no file"
    - id: requirement
      type: label
      text: Requirement
      form: sentence
      hint: What the system must do, and when, in one sentence. Name the condition, then the response.
      example: When an export fails, the system leaves no partial file behind.
    - id: applies-to
      type: label
      text: Applies to
      hint: Where it holds, such as one use case, the commands of one kind, or the whole system.
      example: Every export, whatever its format.
    - id: measure
      type: label
      text: Measure
      hint: The value or the condition that shows the requirement is met.
      example: No file is left after an export stops at any of its steps.
    - id: verified-by
      type: label
      text: Verified by
      allows-none: true
      hint: What verifies it today, such as a test, a check or a review, named by what it does. Write `None.` when nothing does.
      example: A test stops an export at each step and looks for a file.
    - id: rationale
      type: label
      text: Rationale
      hint: Why it is needed and what goes wrong without it. Name the record that decides it.
      example: An analyst may send a partial file on as if it were whole (DEC-003).

constraint:
  sections:
    - id: heading
      type: heading
      level: 1
      example: "# CNS-001 — Figures never leave the company's network"
    - id: constraint
      type: label
      text: Constraint
      form: sentence
      hint: What the solution must use, follow or avoid, in one sentence.
      example: The system stores and sends no figure outside the company's network.
    - id: applies-to
      type: label
      text: Applies to
      hint: Where it holds, such as one use case, the commands of one kind, or the whole system.
      example: Every export, every backup and every log.
    - id: imposed-by
      type: label
      text: Imposed by
      hint: Who or what imposes it, and why the design cannot choose otherwise. Name the record that admits it.
      example: The company's data policy, which the system must follow (DEC-004).
    - id: verified-by
      type: label
      text: Verified by
      allows-none: true
      hint: What verifies it today, such as a test, a check or a review, named by what it does. Write `None.` when nothing does.
      example: A security review of each change that adds a place to send data.
```

- **Front matter:** `id`, `title` and `status` (`active` or `withdrawn`), as a use case has, and the friction block. A companion schema for each kind checks them.
- **Forms:** only `sentence`, on the statement, which already ships. No new form.
- ***Measure* and *Verified by* apart.** The measure is the fit criterion, what a solution must reach. *Verified by* is what checks it today, 29148's method of verification. A requirement can have a clear measure and nothing that verifies it, as C15 and D9 do.
- **A path goes in the anchor, never in the body.** *Verified by* names a test by what it does. Its path goes in the requirement's anchors, inside the methodology's container, which is no content (COR-050 point 5). A path in the body is content, so renaming the test would flag every use case that lists the requirement.
- **Where "not met" goes.** A requirement the code does not meet, such as C15, is a revalidation's outcome, never a part. It is `code-regressed`, or `gap-found` where the behaviour never existed, recorded with its defect (DEC-001 points 5 and 6).
- **Why not the SEI's six parts.** Source, stimulus, environment and artefact sit well in one sentence. The examples state their condition and response in a clause each. The measure, and what verifies it, are what most often go missing (C15, C16), so each gets a part.
- **Why not a special-requirements part in the use case,** as RUP has. Nearly every example binds a class of commands, not one use case. A requirement that binds one use case is still a requirement, which that use case lists.

### 3. Their anchors

One new edge joins the cascade: a changed requirement flags the use cases that list it. Actors and requirements are parallel sources of use cases, since no anchor joins the two. The core reads the reporting order from the anchors alone (COR-050 point 11), so no order is claimed beyond them. No anchor runs from a use case's side back to a requirement, so no cycle forms (COR-050 point 5).

- **A requirement anchors to the home of what it states** (point 5). That is the record that decides or admits it, on its point where the record numbers its points as headings (COR-058). COR-059 does. COR-010 does not yet, so an anchor on it is whole. Where a page states it and no record decides it, it anchors to that page's section.
- **A requirement anchors to the narrow code that holds or verifies it.** That is the test its *Verified by* describes, or the module that holds the property. Never to every command of the class it binds: that anchor would be over-broad (COR-050 point 7).
- **What friction does, and what it does not.** Friction flags a requirement when its record, its test or its narrow code changes. A new command that breaks a cross-cutting property is not friction's to find. It is the test's, and its result reaches a revalidation through the evidence point (DEC-001 point 7).
- **A use case anchors to the requirements it must meet.** Its front matter lists them in `requirements`, an optional field, as `other-actors` is. So no live use case migrates. The stamp writes the anchors from the list, and the check requires them to match, as for other actors.
- **Why that direction:**
  - A changed requirement can make a use case false, such as the variant an interrupted upgrade takes (L2). A changed use case rarely makes a requirement false.
  - A cross-cutting requirement anchored to its use cases would be flagged on each of their edits. Listed by them, it flags them only when it changes, which is rarer.
  - It matches how use cases already anchor to actors.
- **A requirement that binds a class, or the whole system,** need not be listed by every use case of that class. Its *Applies to* says where it holds in words. A use case lists it where its steps depend on it.
- **No double flag.** A use case need not anchor a record that a requirement it lists already anchors, unless its own steps rest on that record. Otherwise one change to the record flags it twice. The skill says so.
- **A use case's own parts name it, never restate it.** A *Minimal guarantee* or an *Assumption* that a requirement states names the requirement's id, as it names a record today. "A failed export leaves no partial file (QR-001)." So the record, the requirement and the use case do not each state it.
- **Cross-cutting assumptions.** A limit the environment must meet, such as L13 or S14, is a constraint, which a use case's *Assumptions* names. A harness's behaviour stays in COR-047's catalogue, as S9 does.
- **Unanchored.** A requirement may rest on nothing the repository holds, such as a contract with a customer. It then carries `unanchored-because`, as an actor or a term may (DEC-001 point 9).
- **Not at first:** a journey's list of requirements, an anchor from a requirement to the actors it serves, and an anchor between two requirements. No example needs the first. The second would flag every requirement on each edit of an actor's needs, and the record anchor already gives the trace 29148 asks. The third would carry arc42's quality tree, which no reader asks for yet. Each can come when one does.

A worked example, from L1. A future use case of upgrading would list it in `requirements`.

```markdown
---
id: QR-001
title: A second run of a migration changes nothing
status: active
pkit:
  friction:
    anchors:
      record: [COR-010]
      path: [tests/test_backbone_migration_replay.py]
---

# QR-001 — A second run of a migration changes nothing

**Requirement:** When a migration runs again over a project it has already migrated, it changes nothing.

**Applies to:** Every migration of every tier, wherever an upgrade runs it.

**Measure:** A second run leaves every file, and the index, as the first run left them.

**Verified by:** A test replays every backbone migration over a fresh install. A capability's migrations are tested one script at a time.

**Rationale:** An adopter runs an upgrade again after one stops, and expects it to finish the job (COR-010).
```

### 4. How the architecture points at them

**A view anchors to the requirements it satisfies. A record stays an anchor target, and names the requirements it serves in its text.**

- **What #1447 decided** (the maintainer's decision of 10 October, `2026-10-08-analysis-and-architecture.md`). A use case anchors to the architecture records it rests on. A view, where one exists, anchors to the use cases it realises. Records are only ever anchor targets there.
- **What #1393 asks.** Its third criterion gives an example: "an architecture record or view anchors to the quality requirements and constraints it satisfies, as arc42's quality goals drive its decisions". For views, that is #1447's rule extended to the new kinds. For records, it reverses #1447's direction.
- **Why records do not anchor to requirements.** It is wrong for this corpus, and the mechanics stand in the way too:
  - **A record that decides a requirement and satisfies it would form a cycle by construction.** The requirement anchors to the record as its home, and the record would anchor to the requirement it serves. Seven ADRs in the list mix a requirement with its mechanism.
  - **Where another record decides the requirement, the anchor adds little.** An ADR that satisfies a requirement a COR decides can anchor that COR's point, and the same change flags it.
  - **A record that carries anchors changes its own file on each revalidation.** A whole record anchor changes when the record's file changes (COR-050 point 5, `src/project_kit/friction_check.py:1189`). So everything anchored to that record whole would be flagged each time.
  - **Cycles through records escape the core's check,** which reads artefact anchors alone (`src/project_kit/friction_validate.py:928`).
- **When records could anchor.** Once the analysis is itself the home of requirements, as in arc42, where quality goals come first and decisions follow. That is the third case of point 5 grown to the whole analysis. It needs the anchors record refined first ("Beyond this issue").
- **So:** a record names the requirements it serves by id, in its text, as it cites other records. A view anchors to them, as it anchors to use cases.
- **What #1393's third criterion gets.** It asks how the architecture points at these requirements under #1447's rule. In project-kit the answer is a rule with nothing under it at first: there are no views yet.
- **No check of a name in a record's text.** `pkit refs validate` resolves COR, PRJ and ADR ids only (`src/project_kit/refs.py:879`). An id is never reused (DEC-001 point 3), so a named id never points at another artefact. A withdrawal goes unseen, which is low risk. A check of it would be the capability's validator, and waits for a second need (COR-007).
- **What the analysis decides, and what it does not.** The analysis gives each requirement a stable id and a type, so a view can anchor to it. The architecture decides the rest, such as where a view lives and which agent writes its anchors (#1447's open questions).

### 5. Where a requirement's home is

Three cases. DEC-002 states them on its own, since the capability works with no other component installed (DEC-001 point 10). Living-docs DEC-001 point 3 is a parallel for pages, cited in the Rationale, not the ground.

- **A record decides it: the record is the home of that decision.** The requirement anchors to the record, and restates it in checkable form.
  - **A change starts at the record.** Friction carries it to the requirement, which is then revalidated.
  - **The requirement adds** what the record lacks: one singular statement, where it applies, its measure and what verifies it. And a catalogue by area, where today a reader looks through 59 COR, 10 PRJ, 64 ADR and 66 DEC records.
- **A page states it, and no record decides it: the page stays its home for now.** That is D1, C7, C8, S5 and S15. The requirement anchors to that page's section, or that file.
  - It is the reversed order DEC-001 point 9 allows on an existing project, where the documents are the ground truth. Actors already anchor page sections in this way.
  - **Where it flips:** when pages are built on the analysis (EPIC #234, after EPIC #1643). The page then anchors to the requirement for its grounding (living-docs DEC-001 point 4). The core's cycle check forces the flip, so it is never silent.
- **Only the analysis states it: the requirement is the only statement of itself.** That is a requirement gathered from a stakeholder in a new project, the primary case in arc42 and 29148. It anchors to code, or carries `unanchored-because`. A page that later states it anchors to it for grounding, and is the fact's home among the pages. This contradicts nothing in living-docs, whose rule decides a home only for what a page states.

### 6. Place, ids and numbering

- **Places,** under the analysis location, beside the use-case model, since RUP keeps the supplementary specification beside it:

  ```
  analysis/
  ├── glossary.md
  ├── use-case-model/ …
  ├── quality-requirements/
  │   ├── QR-001-<slug>.md
  │   └── <area>/QR-014-<slug>.md     optional grouping by area
  ├── constraints/
  │   └── CNS-001-<slug>.md
  └── revalidations/ …
  ```

- **Types:** `software-analysis:quality-requirement` and `software-analysis:constraint`, one for each place (DEC-001 point 2). No project place and no kind field, as for the other four.
  - **A clash on upgrade.** A project's own bare type named `constraint` would clash, and validation refuses such a clash (COR-056 point 2). The changeset says so. `design-constraint`, RUP's word, would make a clash rarer.
- **Ids:** `QR-NNN` and `CNS-NNN`, numbered within the project, three digits below 1000.
  - **Not `CON-`.** It differs from `COR-` by one letter, and the two would be cited side by side, as in "CON-004 (COR-010)". Every adopter sees COR ids, and an id is permanent once shipped (DEC-001 point 3). `LIM-` is another choice.
  - The rules of DEC-001 point 3 apply as they stand:
    - append-only, withdrawn and never deleted
    - the next free number past the default branch
    - a collision found by `check-numbers`
    - an id freed only by the numbering setting
- **Areas:** optional sub-folders, as for use cases. Moving a requirement between areas never changes its id. EPIC #1643's areas use the same folder names under each kind.

### 7. The stamp and the check

- **The stamp,** `pkit analysis new`:
  - `quality-requirement <slug> [--area <a>] [--title <t>]`
  - `constraint <slug> [--area <a>] [--title <t>]`
  - both with `--path` and `--record` for their anchors, or `--unanchored-because`
  - `use-case` gains `--requirement <id>`, repeatable, writing `requirements` and its anchors
  - each body rendered from its kind's structure, every part holding its hint
- **The check,** `pkit analysis validate`, holds the two kinds as it holds a use case:
  - the front matter against each kind's companion schema
  - the heading against the id and the title, the file's name against the id
  - placeholders and hints left in
  - each body against its structure, where RS-SAN-001 binds
  - each of a use case's `requirements` resolved to a requirement in force, and its anchor present
- **`check-numbers`** counts QR and CNS numbers as it counts UC and JRN. Its check of steps and variants does not apply.
- **Revalidation** is unchanged. The four outcomes, the record and `pkit analysis propose` read any kind.
- **The evidence point** takes QR and CNS ids. A test of a quality requirement's measure is exactly what it carries.
  - Its schema's artefact id pattern widens. Its branches for `steps` gain QR and CNS, which take none, as actors and terms do (`schemas/revalidation-evidence.schema.json:57`).
  - That is additive, so its version stays (COR-052 point 5).

### 8. `SAN`

**No new rule.** RS-SAN-001 already says an analysis artefact carries its kind's declared structure, so it covers both kinds.

- **What changes:** nothing in RS-SAN-001's content. RS-SAN-001 is accepted since #1370, and `SAN` is at 1.0.0. Its `checks` part names the kinds that carry a title heading, and the build adds the new kinds there. That part is no content of the rule, so `SAN`'s version stays (COR-051 point 2).
- **Not a breaking change.** Adding a kind fails no artefact the check passed before, since none of the new kinds exists yet (DEC-001 point 1).
- **Where it binds:** only where a set of the project's own selects the new types. project-kit's `ANA`, at 4.0.0 and pinned at `SAN@1`, selects four types today. Its scope gains two, versioned as COR-051 point 7 asks. Until a set selects them, no rule of `SAN` binds on them. The check counts them, as it counts any such artefact (DEC-001 point 1). The set that installing will create (#1613) selects all six.
- **Rules left as candidates,** to judge after project-kit writes its first area of requirements:
  - a requirement states one property of the problem, never the solution's mechanism
  - a requirement a record decides anchors to that record
  - a quality requirement's *Measure* names a value or a condition, not a hope

  Each needs judgement, not a check. The rule-set reviewer would judge them (COR-057).


### 9. The record

**A decision of its own, software-analysis DEC-002, as DEC-001 point 11 asks.** It holds the two kinds, their parts, their anchors, their places, their ids, and the three homes of point 5. No ADR: the content belongs to one capability, so a DEC is the kind of record for it (COR-025).

- **DEC-001 is refined in place** where its text names only four kinds:
  - the Decision's lead, "four kinds of product knowledge"
  - point 2, the places and the type registry
  - point 4, a changed requirement flags the use cases that list it
  - point 11, quality requirements and constraints leave the scope boundary
- **What stays.** Points 1 and 3 stay true of the kinds they name, and DEC-002 applies them to its own. The title stays, since it is still true. Every point anchor stands on the title, so changing it would flag each one.
- **What the lead's edit costs.** Every point stands on the lead's text (COR-050 point 5). So each anchor on a point of DEC-001 is flagged once, such as RS-ANA-001's on point 1 and RS-SAN-002's on point 3.
- **The order, with #1447.** #1447's refinement of point 11 lands first. It is decided, and needs nothing from this kind. Its view rule exists only in a scratchpad note until then, so DEC-002 could not extend it under the acceptance gate. EPIC #1643's use cases need #1447's hint now too. Then DEC-002 refines point 11 once more, naming requirements beside use cases. Point 11 stays the one home of the link between the analysis and the architecture, and DEC-002 refers to it.

## Beyond this issue

The architect found two gaps in the anchors record (COR-050). They exist today, whatever this design does.

- **What it found.** ADR-055 point 3 says every decision record under `tech-docs/` is an artefact that may carry anchors. The day one ADR carries a friction block, two things break:
  - each revalidation of that ADR changes its file, so every whole record anchor on it is flagged. One such anchor exists: ACT-methodology-maintainer anchors ADR-059 whole.
  - a cycle through a record anchor goes unseen by the cycle check and by the upstream-first order (COR-050 point 11).
- **What it recommends.** File the refinement as a core issue of its own, apart from #1393:
  - a record's methodology container is no part of what a whole anchor on that record stands on
  - the cycle check and the reporting order follow a record anchor to a record that is an artefact

  Until it lands, no ADR carries a friction block, and ADR-055 point 3 says so. The architect keeps ADR-055 and would write that caveat.
- **Why it is not this note's.** It refines an accepted core record, and limits an ADR's intended end state. The maintainer decides it. This note recommends no record anchor to a requirement, so it does not depend on it.

## Alternatives

- **One kind with a type field.** One place, one prefix, one template. A requirement that changes kind keeps its id. Not recommended: a place gives one kind and has no kind field (DEC-001 point 2), and one set of hints must serve both.
- **One collection file,** like the glossary, as RUP's single document. Not recommended: each entry carries a friction block and four or five parts, so the file grows long, and areas cannot group it.
- **A third kind for system-wide functional rules,** as RUP's supplementary specification holds them. Fail closed, never write and deterministic output read as such. Not recommended: 25010 classifies each as a quality, under fault tolerance, integrity or correctness. A third line would blur more than the one between the two kinds.
- **A requirement lists the use cases it applies to.** Not recommended: each edit of any of those use cases flags it. A cross-cutting one would list dozens.
- **Only the use case's own parts,** as RUP's special requirements. Not recommended: nearly every example binds many use cases.
- **No new kind.** The records stay the only home, and a page indexes them. Cheapest. Not recommended: nothing asks for a measure or for what verifies it, and nothing links a requirement to the use cases that must meet it.
- **Requirements as rules in a rule set.** Rule sets already carry ids, statuses, origins and anchors. Not recommended: a rule governs how an artefact is written, and its scope selects documents (COR-051 point 2). A requirement governs how the software behaves.
- **The SEI's six-part scenario as parts.** Not recommended: five parts carry what the examples state. The six suit a scenario workshop more than an artefact kept true.
- **Classification fields now:** a quality requirement's 25010 characteristic, and arc42's split of constraints. They would let a reader group requirements by quality. Not now: no tool reads them yet. A closed list in a companion schema binds always, and a project's own structures cannot change it. That would shut out a project that uses FURPS+ or 25010's 2011 edition (COR-014). The skill walks 25010's list as a checklist instead.
- **A requirement anchors to the actors it serves.** It gives the trace 29148 asks from a requirement to its source. Not now: an actor's needs are one field, so each edit of any need flags every requirement that names the actor. The record anchor gives the trace, and the *Rationale* names the actor in words.
- **Records anchor to the requirements they satisfy,** as #1393's example says. Not recommended: a record that decides a requirement and satisfies it would form a cycle, and elsewhere the anchor adds little (point 4). It fits once the analysis is the home of requirements, after the anchors record is refined.
- **A requirement lists the records that satisfy it.** It traces the problem to its solution. Not recommended: it puts the solution inside the problem's description, which #1447 keeps apart.
- **`CON-` for constraints.** The issue's own word. Not recommended: one letter from `COR-` (point 6).
- **Refine DEC-001 in place, with no DEC-002.** One record for the whole analysis. DEC-001 is already long, and point 11 asks for a decision of its own.
- **A place under `use-case-model/`.** Not recommended: RUP keeps the supplementary specification beside the use-case model, not inside it.

## For the maintainer

One choice per line, each with the recommendation first:

1. **Kinds:** two, a quality requirement and a constraint, or one with a type field.
2. **Parts:** *Requirement*, *Applies to*, *Measure*, *Verified by*, *Rationale*, and *Constraint*, *Applies to*, *Imposed by*, *Verified by*, as in point 2, or the SEI's six parts.
3. **Use cases and requirements:** a use case lists the requirements it must meet, or a requirement lists the use cases it applies to.
4. **Architecture:** a view anchors to the requirements it satisfies and a record names them, or records anchor too, once the analysis is their home.
5. **Home:** the record that decides a requirement, else the page that states it until pages are built on the analysis, else the requirement itself.
6. **Place and ids:** `quality-requirements/` with `QR-NNN` and `constraints/` with `CNS-NNN`, grouped by area optionally, or `LIM-NNN`, or `CON-NNN`.
7. **Type names:** `quality-requirement` and `constraint`, the changeset noting a clash with a project's own bare `constraint`, or `design-constraint`.
8. **Start small:** no classification field, no anchor to actors, no list on journeys, no anchor between requirements, or some of these now.
9. **`SAN`:** no new rule now, the three candidates judged after project-kit's first area.
10. **Record:** software-analysis DEC-002 after #1447's refinement of point 11 lands, with DEC-001's lead and points 2, 4 and 11 refined, or DEC-001 refined alone.
11. **Beyond this issue:** the anchors record's refinement as a core issue of its own, with ADR-055 point 3's caveat meanwhile, or not now.

## For the build, once decided

Filed after the maintainer's answer, under EPIC #1547:

- **#1447 first:** its refinement of DEC-001 point 11, as decided on 10 October.
- **The record:** DEC-002, and DEC-001's lead and points 2, 4 and 11 refined, with the decision-author skill. The critic, the architect and the methodology-reviewer review it.
- **The kinds:** their structures, companion schemas, rendered templates, types and places. The check for the two kinds. The evidence point's id pattern and `steps` branches. `SAN`'s `checks` part.
- **The stamp:** both kinds, their numbering in the stamp and in `check-numbers`, and `--requirement` on use cases, with the check of `requirements`.
- **The skill and the README:** an `analysis-author` sub-procedure for each kind, the test between them, and 25010 as a checklist. The skill also gives the rule against a double flag. `choose-templates` covers the new kinds. The README describes them, and its "Named for later" drops the supplementary specification.
- **project-kit:** `ANA`'s scope takes the two types. EPIC #1643's areas write their requirements, starting from the examples above.

## Others at work

- **#1370** accepted RS-SAN-001 and added RS-SAN-002, for append-only steps (`fceb363f`). Neither changes this design. RS-SAN-002 reaches no requirement, which has no steps.
- **#1447** is open, and lands before DEC-002 (point 9). Point 4 extends its rule for views.
- **#1613** creates a project's set on install. Its scope should select all six types.

## Review

The critic read the first draft, and the architect the second. Each finding is answered below, one line each.

### The critic

- **Records anchoring to requirements reverses #1447, which keeps records as anchor targets.** Fixed: point 4 cites #1393's criterion for the record arrow, states #1447's decision, and recommends records stay targets.
- **A record carrying a friction block changes its own file, flagging every whole anchor on it.** Accepted: no record anchors to a requirement. The gap itself went to "Beyond this issue", on the architect's finding.
- **The pair report contradicted COR-050 point 5, and longer loops escaped it.** Fixed: the pair report is gone. With records as targets, no loop runs through them.
- **The quality requirement had no part for what verifies it.** Fixed: both kinds have *Verified by*, which may read `None.`. *Measure* stays the fit criterion, and "not met" is a revalidation's outcome.
- **A requirement as the home of a fact no record decides contradicted living-docs DEC-001 point 3.** Fixed: the page stays the home until pages are built on the analysis (point 5).
- **The membership test was applied to S16 and not to S6, S12 and S13.** Fixed: "What the list shows" applies it to each, reading DEC-001's test as it stands.
- **DEC-001's refinements were incomplete.** Fixed: point 9 lists the lead and points 2, 4 and 11, and the flag the lead's edit raises.
- **`unanchored-because` cannot sit beside actor anchors.** Answered: no actor anchors at first.
- **How a cross-cutting requirement anchors to code.** Fixed: narrow code only, and a new command that breaks the property is the test's to find (point 3).
- **The overlap with *Minimal guarantees* and *Assumptions*.** Fixed: a use case's part names the requirement's id. An environment's limit is a constraint (point 3).
- **Anchors between requirements.** Answered: not at first (point 3).
- **Whether `requirements` is required, and journeys.** Fixed: optional, as `other-actors` is, and not on journeys at first.
- **A project's own bare type named `constraint` would clash.** Fixed: point 6 notes it, and choice 7 offers `design-constraint`.
- **The order with #1447, and where the pair rule lives.** Fixed: #1447 lands first, and the pair rule is gone (point 9).
- **The shipped hints carried project-kit's content.** Fixed: the sketch uses the plain report domain, and project-kit's example stands apart.
- **The build list missed the evidence schema's `steps` branches, the README's "Named for later" and `ANA`'s version.** Fixed: points 7 and 8, and the build list.
- **Actor anchors bring back the fan-in rejected elsewhere.** Accepted: dropped, and listed under Alternatives.
- **Classification fields have no reader, and closed lists shut out FURPS+.** Accepted: dropped, with 25010 as a checklist.
- **Writing the requirement finds C15, not revalidation.** Accepted: *Verified by* shows it, and a revalidation records "not met" with its defect.
- **The worked example showed reliance, not satisfaction, and cited two homes.** Fixed: the ADR example is gone, and QR-001 rests on COR-010 alone.
- **A special-requirements part costs no migration with zero use cases.** Accepted: the reason given is now that the examples cut across use cases.
- **The blur count was understated.** Fixed: about ten sit on a boundary, listed by boundary.
- **Counter-alternatives.** Adopted: records stay targets, a shared *Verified by*, and a smaller start. Listed: a third kind for system-wide functional rules. Answered: cross-cutting assumptions (point 3).
- **Factual errors.** Fixed: the `checks` part named no kinds at `43981938`, though it does since #1370. The note now counts five examples with no record, and names arc42's split and the SEI's scenario rightly. The claims about core records as places, and about project-kit's ADRs carrying anchors, are gone.

### The architect

Its verdict: sound, and an extension of #1447 that holds together. The findings:

- **The two gaps in the anchors record exist today (A1).** Moved to "Beyond this issue", as a core issue of its own. It is outside this issue, so it is reported to the maintainer word for word and no further round ran on it.
- **Records anchoring to requirements is wrong for this corpus (F1).** Accepted: point 4 gives the reason, and choice 4 ties the alternative to the analysis being the home.
- **The cascade order claimed more than the anchors make (F2).** Fixed: point 3 states only the new edge.
- **A test's path in the body flags every use case that lists the requirement (F3).** Fixed: the hint names a test by what it does, and the path goes in the anchor.
- **`CON-` sits one letter from `COR-` (F4).** Fixed: `CNS-`, with `LIM-` and `CON-` as choices.
- **The home rule left out a requirement only the analysis states (F5).** Fixed: point 5's third case, and where the page's case flips.
- **The membership test was reworded more widely (F6).** Fixed: the note reads "the software", as DEC-001 does.
- **ADR-055 point 3 needs a caveat (D1).** Part of "Beyond this issue", for the architect once the maintainer settles it.
- **DEC-001's title stays (D2).** Fixed: point 9.
- **No ADR now, one when the first view lands.** Noted in point 9.
- **A use case need not anchor a record its requirement already anchors.** Added to point 3 and the skill's build item.
- **A record's text naming a requirement has no check.** Noted in point 4.
- **#1447's refinement should land before DEC-002.** Fixed: point 9 and the build list.
- **Escalation.** The anchors record's refinement, and records anchoring to requirements, each need the maintainer's authorisation. Neither is in the recommended path.
