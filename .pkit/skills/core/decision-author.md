---
name: decision-author
description: Author a new decision record — a project's own PRJ or ADR record, a capability-scoped DEC, or, for the methodology's maintainers, a COR — with proper schema, disciplines, and citations. Use when adding a project-side, project-architectural, capability-internal, or methodology decision.
metadata:
  wraps_command: pkit new decision
gates:
  - COR-006
  - COR-008
  - COR-025
reads:
  records:
    - COR-024
    - COR-046
    - COR-049
  paths:
    - .pkit/decisions/README.md
    - .pkit/cli/README.md
    - .pkit/agents/project/overlay.yaml
---

# Authoring a decision record

This skill walks through adding a new decision record. A project writes two kinds of record of its own, in the same shape:

- **PRJ** records, under `.pkit/decisions/project/`, say how the project works: its workflow, tooling and conventions.
- **ADR** records, at the overlay-resolved `<adr-records>` path, `docs/architecture/decisions/` by default ([COR-025](../../decisions/core/COR-025-adr-decision-space.md)), say what the project built and why: its boundaries, technologies and integration patterns.

Two more kinds share the shape and this procedure:

- **DEC** records, under `.pkit/capabilities/<capability>/decisions/`, hold a decision internal to one capability's design. Each capability numbers its own; pass the capability's name as the namespace.
- **COR** records, under `.pkit/decisions/core/`, hold the methodology's own principles. Writing one is the methodology maintainers' case, in the methodology's source repository. A project receives them by sync and never edits them: to propose one, it contributes upstream (`.pkit/decisions/README.md`, "Adding a record").

## Acceptance gate (run first)

Per `.pkit/decisions/README.md`'s acceptance gate: before doing any procedural work, verify that every record listed in this skill's frontmatter `gates:` field is `accepted`. If any is `proposed` or `superseded`, halt and report — this skill cannot run on a draft hypothesis.

The current declared dependencies:

- **COR-006** — artifact roles. Used so this skill cites authoritative docs/decisions rather than restating them.
- **COR-008** — git workflow conventions. Used for the commit-message format in the final step.
- **COR-025** — the ADR decision space. Used to pick the record's kind in the first step.

## Procedure

### 1. Pick the kind of record

COR-025's scope test picks the kind, its three tests in order:

- **Does the rule apply to this one project, not to every project that adopts the methodology?** Then it is the project's: continue. A rule every adopter would need is a COR. Outside the methodology's source repository, stop there and propose it upstream.
- **Is it internal to one installed capability's discipline?** Then it is a DEC in that capability.
- **Otherwise, what question does it answer?** "How do we work, with what tooling, by what process?" is a PRJ. "What did we build, why these boundaries, why this technology?" is an ADR.

### 2. Read the disciplines

Read `.pkit/decisions/README.md`'s **Writing a record** section. Which disciplines bind depends on the kind:

- **Every record**, whatever its kind: lead with meaning, principles, not inventory, and the role named rather than its current holder (COR-046). It states the present, with no log of its revisions.
- **An ADR** adds architectural fit. Its readers are the project's architects, maintainers and on-call engineers, not the methodology's.
- **A COR**, the maintainers' case, adds the axiom discipline and project-neutrality.

### 3. Read the schema

Read `.pkit/decisions/README.md`'s **Schema** and **Statuses** sections. Every record has the same frontmatter and four required sections.

### 4. Pick a slug

Kebab-case, 2–4 words, describing what's decided. Examples: `content-mechanisms`, `merge-delivery`, `pr-workflow`, `git-conventions`, `pattern-extraction`.

### 5. Stamp the stub

Use the methodology's authoring command to scaffold the file (per `.pkit/cli/README.md` → "Authoring commands" → `new decision`):

```
pkit new decision project <slug>         # for PRJ
pkit new decision adr <slug>             # for ADR (per COR-025)
pkit new decision <capability> <slug>    # for DEC (capability-scoped)
pkit new decision core <slug>            # for COR (the maintainers' case)
```

The command picks the next number in the id-space, stamps the frontmatter (`id`, `title` placeholder, `status: proposed`, today's `date`, `author` from git config), and writes the four required section headers (`## Context`, `## Decision`, `## Rationale`, `## Implications`) with empty bodies, but for a first point heading under `## Decision`, `### 1. Point title`.

For the `adr` namespace, the target directory is resolved from `.pkit/agents/project/overlay.yaml`'s top-level `adr-records:` key (first entry). A directory named there must exist before stamping — if not, the command refuses with a `mkdir -p` hint. If the key is present but empty, or the path points inside `.pkit/`, the command refuses with a pointer to COR-024/COR-025. With no `adr-records:` key, the command derives the directory from the project's internal documentation root (`docs/architecture/decisions/` by default) and records it in the overlay before stamping, saying what it recorded and which root it came from ([COR-049](../../decisions/core/COR-049-documentation-roots.md) point 5). A folder that is absent or empty is created and recorded without asking. A folder that already holds documents is recorded only with consent, because the recording puts those documents within reach of every agent that references `adr-records`: a terminal is asked once, `--yes` consents without a prompt, and a run with nobody to ask and no `--yes` records nothing and stamps nothing, naming the command to run with `--yes`.

For a **capability namespace** (any namespace that is not `core`/`project`/`adr`), the record stamps under `.pkit/capabilities/<capability>/decisions/` with the `DEC` prefix, numbered independently within that capability. The capability must already exist (have a `package.yaml`); the command refuses an unknown name. The `decisions/` subdirectory is created on first use. Duplicate-id collisions across the corpus are caught by `pkit decisions validate` (wired into the check gate).

This is the deterministic half of authoring. The conversational half — drafting the body — happens in the next steps.

### 6. Draft the body

Open the stamped file and fill in:

- **Title** — replace the placeholder with the actual short imperative title.
- **`## Context`** — what situation prompted this decision?
- **`## Decision`** — what was decided. Single crisp sentence ideally. A complex decision gives each part a point: a heading with its number and a title, `### 1. Title`, which keeps that number for good (`.pkit/decisions/README.md`, "Schema"). The stamped point heading sets the points' level, and once it is there a numbered list in the record is a list, never points. Delete it before the record first lands if the decision has no parts (`.pkit/decisions/README.md`, "Adding a record").
- **`## Rationale`** — why this choice over alternatives. May include an `### Alternatives considered` sub-section.
- **`## Implications`** — what does this mean for code, tests, workflow, downstream decisions?

### 7. Self-check against disciplines

Before showing the draft, walk it against each discipline that binds its kind (step 2):

- *Lead with meaning* (every record): is the title short and declarative? Does a plain-language summary open the record so a reader grasps the decision in under a minute before the rigor? Do any sentences pile up cross-references and bury their own meaning? If the decision isn't recoverable on a first read, revise the on-ramp before showing it.
- *Principles, not inventory* (every record): does the body capture rules among alternatives, or has it slipped into enumerating state? Tag candidate content as *rule* or *state*; state gets a one-line cross-reference, not enumeration.
- *The role, not its current holder* (every record): would a sentence become false if a path, module or function it names were renamed, with no decision changed? Then it meant the role: name the part instead, sharply enough that only one thing could play it.
- *Architectural fit* (ADR): does the record answer "what did we build / why these boundaries / why this technology"? If it answers "how do we work / what's our process", it belongs in PRJ.
- *Axiom* (COR): every term used has a prior definition in an earlier core record, is generic English/Markdown/filesystem vocabulary, or names a known external tool.
- *Project-neutrality* (COR): would the record make sense, and apply, read in any project that adopts the methodology? If it says how the methodology's own source project is built, it belongs in that project's PRJ records.

If any check fails, revise.

### 8. Show the draft for review

Surface the draft to the user. Do **not** commit until approved. The acceptance gate forbids using the new record as a basis for downstream work until it's accepted; the same caution applies to committing — uncommitted drafts can still be revised cheaply.

### 9. Commit (after approval)

Per COR-008, use conventional-commits format. Type is `decision`; scope reflects the area:

```
decision(<scope>): add <ID> <short title>

<body — 1–3 paragraphs summarising context and decision>

Status: proposed.

Co-Authored-By: <as appropriate>
```

The record lands as `proposed`. Acceptance is a separate gesture (status flip + a follow-up commit, per the acceptance gate). Do **not** mark the new record `accepted` in the same commit unless the user explicitly approves both the addition and the acceptance together.

## Variations

- **Refining an existing accepted record** — not this skill's work: this skill authors new records. A refinement that introduces no new decision is an edit in place, made as `.pkit/decisions/README.md` → "Refining an accepted record" says.
- **Superseding an existing record** — this skill authors the superseding record; set `supersedes:` in its frontmatter to the id of a record it replaces whole, such as `supersedes: PRJ-NNN`. A record that overturns another only in part sets none. The edit to the superseded record is a separate step, made as `.pkit/decisions/README.md` → "Refining an accepted record" says.
