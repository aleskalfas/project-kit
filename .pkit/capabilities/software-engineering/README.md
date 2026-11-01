---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/**
        - .pkit/capabilities/software-engineering/review-contributions.yaml
        - .pkit/capabilities/software-engineering/decisions/**
        - .pkit/capabilities/software-engineering/scripts/**
        - .pkit/capabilities/software-engineering/schemas/**
        - .pkit/capabilities/software-engineering/skills/**
        - .pkit/capabilities/software-engineering/rule-sets/swe.md
        - .pkit/capabilities/software-engineering/package.yaml
        - .pkit/lifecycle/ownership.py
        - .pkit/capabilities/project-management/scripts/_lib/required_reviewers.py
      record: ["software-engineering:DEC-003", COR-070, ADR-076, COR-013, COR-024, COR-026, COR-030, COR-050, COR-057, "COR-062#1", "COR-062#7", "COR-064#1", "COR-064#2", "COR-064#4", ADR-013, ADR-052, "project-management:DEC-015", "project-management:DEC-027", "project-management:DEC-028", "project-management:DEC-032", "project-management:DEC-050", "project-management:DEC-055", "project-management:DEC-060"]
      artefact:
        - RS-SWE-001
        - .pkit/agents/README.md#adopter-overlay
        - .pkit/agents/README.md#diagnosing--repairing-the-overlay
        - .pkit/agents/README.md#the-rule-set-reviewer
        - .pkit/agents/README.md#body-conventions
        - .pkit/rules/README.md#the-capabilities-rules-index
        - .pkit/capabilities/project-management/README.md#the-answers-a-change-wrote-in-its-pull-request-project-managementdec-055-pr-lists-answers
        - .pkit/capabilities/project-management/README.md#opting-out-of-a-contributed-reviewer-per-project-managementdec-032-conditional-reviewer-requirements
        - .pkit/capabilities/project-management/README.md#landing-a-pull-request-in-one-command--land-work-1203
        - .pkit/cli/README.md#capabilities--two-ways-in
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
        - .pkit/cli/README.md#friction-revalidate-artefact---outcome-updatedunchanged---because-text---keep-anchor---yes----dry-run
        - .pkit/cli/README.md#friction-defer-artefact---anchor-anchor---reason-text---yes----dry-run
        - .pkit/cli/README.md#friction-revisit-artefact---target-anchor---outcome-unchangeddeferred---reason-text---yes----dry-run
        - .pkit/cli/README.md#rule-sets-generate
---

# software-engineering capability

<a id="adopter-setup"></a>

software-engineering makes the code agents write follow a project's own conventions in every session, and has code reviewed, with its documentation, before it merges ([software-engineering:DEC-003-purpose]). Why it exists, and how people set it up and do its tasks, is in [software-engineering's guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/capabilities/software-engineering/README.md).

## Contents

<!-- pkit:contents -->
- [Installing it](#installing-it)
- [The conventions corpus](#the-conventions-corpus)
- [The producer: `software-engineer`](#the-producer-software-engineer)
- [The code-review panel](#the-code-review-panel)
- [Its operational rules](#its-operational-rules)
- [Citing this capability's decisions](#citing-this-capabilitys-decisions)
- [Dependencies](#dependencies)
<!-- /pkit:contents -->

<a id="what-this-capability-ships"></a>

## Installing it

`pkit capabilities install software-engineering` copies the capability into `.pkit/capabilities/software-engineering/`. It deploys the capability's four agents, and renders the rules index that loads its rules.

- **What it needs.** project-management, installed first, at a version in the range the capability's `package.yaml` declares under `requires_capabilities` (COR-030). Without it, the install refuses and names the capability it needs.
- **What it deploys.** The producer, `software-engineer`, and the three reviewers of the code-review panel: `code-reviewer`, `security-reviewer` and `docs-reviewer`. The adapter deploys each as it deploys any agent, in Claude Code into `.claude/agents/` (COR-013). There the project's `software-engineer` shadows the harness's own agent of that name.
- **Its reviewer contributions.** `review-contributions.yaml` registers the three reviewers in project-management's merge gate ([project-management:DEC-032]). Installing the capability turns them on, with no switch of their own ("When each reviewer is required" below). Opting one out is project-management's ("Basic or complex review" below).
- **Its rules.** `rule-sets/swe.md` and `rules.md` are its loaded rule set and the file generated from it ("Its operational rules" below).
- **What it writes.** Nothing of the project's configuration. It ships no conventions either, since the corpus is the project's own ("The conventions corpus" below).

## The conventions corpus

The conventions corpus is the project's own coding standards, kept where the project names them. Each agent of the capability reads it before it writes or judges code ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 2).

- **Where it is named.** The `project-conventions` category of the project's agent overlay lists the paths that hold it ([the agents README, "Adopter overlay"](../../agents/README.md#adopter-overlay)). `pkit agents reconcile --write` appends a stub of the category, to fill in.
- **How an agent finds it.** `pkit sync` deploys each agent with those paths under `reads.patterns` in its front matter. The agent's text keeps the placeholder `<project-conventions>`, and the agent reads whatever the category resolves to.
- **Optional.** With the category undefined, the read drops from each agent's front matter, and each agent still deploys. `pkit agents` lists the category as optional, and `pkit agents reconcile` proposes it as optional, never as a blocker.
- **Empty or silent.** An agent that finds no corpus, an empty one, or nothing on a choice says so. It then works by ordinary judgement, and never invents a convention to fill the gap ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 5). A walking skeleton is the one case where the software-engineer writes to the corpus ("A foundation fills the corpus" below).
- **Growing.** Each agent reads the corpus when it runs, so a convention added later applies with no new install. A path added to the category applies from the next `pkit sync`.
- **Owned by the project.** The corpus lives where the project's overlay points, so uninstalling the capability removes none of it ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 2).
- **Read by the reviewers too** ("Knowledge split" below).

## The producer: `software-engineer`

`software-engineer` writes and edits a change's code to the conventions corpus ([software-engineering:DEC-001-producer-agent-and-conventions-seam]). Dispatch it with the change to make, such as the code an issue asks for.

- **Before it writes code,** it reads the corpus.
- **While it writes,** it applies the corpus to each choice the change settles. Where the corpus says nothing, it keeps to cheap robustness, such as naming a value used twice, and adds no abstraction nobody asked for.
- **A design fork** that the corpus does not settle, it names with its trade-off, rather than choose in silence.
- **Before it hands off,** it reads its diff again against the corpus, and corrects what does not conform. No reviewer of the core's stack checks the corpus, since `convention-compliance-reviewer` checks only the methodology's own conventions ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 4). At the merge, `code-reviewer` blocks on a violation of a rule the corpus declares.
- **Judgement of the design** is the `critic`'s and the `architect`'s (COR-024). The agent invokes no reviewer, and merges nothing.
- **Findings on its work.** It fixes each one its reviewer tags `[block]`. It records each `[advisory]` one in the pull request, with how it was answered, rather than widen the fix to take it in.
- **What it does not do.** It gives no verdict and owns no corpus. It files no issue, opens no pull request as a step of the process, and starts no other agent.

### The answers it writes

The agent writes the answers the change check asks of its change, without asking first (COR-050 point 3). They are owed where the change makes an anchored artefact owe an answer.

- **The writers.** `pkit friction revalidate`, `pkit friction defer` and `pkit friction revisit`, each with `--yes` off a terminal ([the CLI reference](../../cli/README.md#friction-revalidate-artefact---outcome-updatedunchanged---because-text---keep-anchor---yes----dry-run)). It commits what they write with the change, a new answer file among it (COR-062 point 1).
- **Answers made apart.** Where the check flags one of its revalidations as replacing revalidations answered apart, the revalidation's reason judges their combined state (COR-062 point 7).
- **What each needs.** Each deferral, and each `deferred` revisit entry, names an open follow-up issue. Each artefact revalidated as `updated` gets one sentence on what changed, in the pull request's description ([project-management's README](../project-management/README.md#the-answers-a-change-wrote-in-its-pull-request-project-managementdec-055-pr-lists-answers)).
- **On a direct commit** to the default branch, it tells each sentence to the person it works for before the commit. It has the reviewer, where the project chose one, check before it commits. `docs-reviewer` cannot do that yet ("Where no reviewer's check holds the merge" below).
- **Its hand-off** says that the change wrote answers. It composes no list of them, since the reviewer reads the check's own.
- **What it never writes.** It names each of these in its hand-off instead, for a person or the delegate a person named to decide (COR-064 point 1):
  - an answer on an artefact its change did not flag, or for a debt the whole-repository check reports
  - a revisit entry for a target its change asks no revisit of, or one whose outcome alone changed
  - a reason for having no anchors

### A foundation fills the corpus

When the software-engineer builds a foundation's walking skeleton, it writes the conventions the skeleton settles into the corpus ([software-engineering:DEC-004-skeleton-conventions-in-corpus]). Every later slice then reads them as the project's rules. Where this capability is installed, [project-management:DEC-060] asks the same of anyone else who builds one, wherever the corpus offers a location the project owns.

The foundation comes first where the Tasks of new work would share a choice that nothing settles yet ([project-management:DEC-060]). It holds accepted records of the work's architectural choices, and then the walking skeleton. The skeleton is one thin slice built end to end, whose code sets the conventions the later slices share.

- **Written with the skeleton.** The agent writes an entry for each convention that building it settles, such as the layout of the code and its tests. It writes them as it builds, or once the code is built.
- **Accepted once.** A person accepts the entries once, with the skeleton's change, before the slices that rest on them are planned.
- **Accepted by a person.** Accepting is an act of its own on the entries' text, and authorising the merge accepts none. The change merges only once a person accepts the entries, so it waits in review until then.
- **Its status.** In a corpus that gives its entries a status, such as a rule set, the agent leaves each entry proposed. The person, or an agent the person answered directly, then sets it accepted. In any other corpus, the change's description lists the entries, and the person accepts them there.
- **Nobody to ask.** Where the agent can reach no person, it hands back the entries and its question. The change's description carries the question too. Started by another agent, it cannot ask either, unless the adapter in use declares that its question reaches the person. So an acceptance its caller relays accepts nothing.
- **Where they go.** An entry goes inside the one location the agent finds, where the corpus already keeps the project's conventions, in the form it gives them. In an empty corpus, the agent proposes a form, and a file or section inside that location, with the entries.
- **One location, or no entries.** Of the locations `<project-conventions>` names, the agent writes only inside one that lies in the repository and passes two tests:
  - The methodology neither manages it nor copies it in (`.pkit/lifecycle/ownership.py`). A rule set a component ships fails that test.
  - It lies in no other agent's `owns`.
- **No location found.** Where no location passes, or more than one does, the agent writes none and says so in its hand-off. The hand-off lists each convention with the entry it would have written, so a person can name a location before the slices are planned.
- **A foundation's conventions only.** A Task that changes a convention a foundation set changes the convention's entry, where it has one, with the code. A person accepts the changed entry with that change. Beyond a foundation's conventions, nothing here has the software-engineer write to the corpus.

## The code-review panel

The panel is three reviewer agents that judge a pull request at merge time ([software-engineering:DEC-002-code-review-panel]). Each gives its verdict in project-management's verdict grammar, so the verdicts fold through the gate's existing rule that every required reviewer approves ([project-management:DEC-028]).

- **The verdict.** Its first line is `Reviewer agent (local, <name>): APPROVED` or `Reviewer agent (local, <name>): CHANGES_REQUESTED`. The verdict marker follows the findings, as `<!-- pkit-verdict sha=<head> base=<base> -->` once posted, naming the head and base reviewed.
- **Read-only.** A reviewer never changes the pull request or the repository. It keeps the working files a review needs, such as a dumped diff or a reproduction, in the agent workspace ([the agents README, "Reviewers"](../../agents/README.md#body-conventions)).
- **Running it.** `pkit project-management review-pr <N>` runs each reviewer pull request `<N>` requires, and posts each verdict. `land-work` runs the same review as one of its steps ([project-management's README](../project-management/README.md#landing-a-pull-request-in-one-command--land-work-1203)).

**A diff too large for `gh pr diff`.** This rule is owned here, and each reviewer's definition carries it and points here:

- Each reviewer reads the pull request's diff with `gh pr diff`, which GitHub refuses for a pull request that changes more than 300 files.
- The reviewer then reads the same diff from the local checkout, `git diff <base>...<head>`, with the base and head its brief names. Where the brief names none, it takes the pull request's base branch and head commit.
- It requests changes for a diff it cannot read only when neither source yields it.

| Agent | Remit | Blocks (`CHANGES_REQUESTED`) on | Advises (`APPROVED` with comments) on |
| --- | --- | --- | --- |
| `code-reviewer` | The generalist: correctness and logic at its core, the code's general quality, and the design of its interfaces. It is the reviewer an operator reaches for to review a pull request. | An objective correctness bug, a break to an existing caller, or a violation of a rule the corpus declares. | Style, naming, subjective structure and optional refactors. |
| `security-reviewer` | Authentication and authorisation, secrets on a command line, `shell=True` and command injection, misused cryptography, and dependency hygiene. | A real, exploitable vulnerability the change owns. A secret on a command line, and a shell or interpreter command built from outside input, block wherever the change owns them. | Hardening, defence in depth, a `shell=True` built from a constant string, and a risk with no reachable path. |
| `docs-reviewer` | Whether new public surface is documented, and whether the documentation matches the behaviour and can be understood. It also checks the answers the change wrote, its revisits included. It leans on project-management's documentation obligations ([project-management:DEC-015]). | New public surface with no documentation, where a documentation obligation covers it and no `## Doc impact` reason excuses it. A document the diff makes contradict the code. An answer that does not hold. | Clarity, wording, a suggested example, and documentation thin but not wrong. |

- **Owning a defect.** The change owns a defect it introduces, newly exposes, moves, copies or widens, or one it asserts away ("How a finding is tagged" below).
- **A documentation obligation.** It is a code-to-doc mapping of project-management that covers the changed surface, or a documentation convention the corpus declares. With neither, missing documentation is advisory.

### When each reviewer is required

`review-contributions.yaml` declares when project-management's gate requires each reviewer ([project-management:DEC-032] point D1). Installing the capability turns the declaration on.

- **Agent review mode only.** The gate requires them where a pull request's review mode resolves to `agent`, the default. In `human` mode their verdicts only advise ([project-management:DEC-027], [project-management:DEC-032] point D3).
- **`code-reviewer` and `security-reviewer`** ride the floor `touches-code`. Each is required on a pull request whose diff changes code, whatever the closing issue's classification. The next two items say what counts as code.
- **What is documentation.** A file ending in `.md`, `.mdx`, `.markdown` or `.rst`, in any folder. So is an image, a diagram, a font or a PDF under a `docs/` folder. Every other file counts as code, YAML and JSON included (project-management's `scripts/_lib/required_reviewers.py`).
- **What is not code either.** The paths the project lists in project-management's `review.floors.not_code` do not count, by default the changesets under `.changes/`. Nor do the answer files, in the folder where the core keeps a change's answers, whatever the list says.
- **`docs-reviewer`** rides the same floor, and also the `type` wildcard, `type: "*"`. So it is required on each pull request that changes code. It is also required on each one whose closing issue has a `type`, a type added later included.
- **A pull request that changes code** draws all three, even when its closing issue is typed `docs` or has no type. A reviewer named by both the floor and the wildcard is required once.

**The accepted gap.** A pull request that changes only documents, and closes no issue with a `type`, draws no `docs-reviewer`. Its diff fires no floor, and the wildcard has no classification to match. It gets doc review once it closes an issue with any `type` label, or once its diff also changes code.

**A floor approval outlives a change that touches no code.** A reviewer whose every rule is a floor keeps its `APPROVED` while the commits after the head it reviewed change no code ([project-management:DEC-028], "Stale-verdict handling"). So a wording fix, a changeset or an answer after the review re-runs neither `code-reviewer` nor `security-reviewer`. `docs-reviewer` also carries the `type` rule, so any change re-runs it, on a typed and an unclassified pull request alike. A `CHANGES_REQUESTED` from any of the three goes stale on any change, since the fix it asks for may lie outside the floor.

**Basic or complex review.** `code-reviewer` alone is basic review, and the two specialists beside it make complex review ([software-engineering:DEC-002-code-review-panel] D5). To drop one reviewer and keep the rest gating, opt out of it in project-management's `review.agents.contributed_opt_out:`, with a reason ([project-management's README](../project-management/README.md#opting-out-of-a-contributed-reviewer-per-project-managementdec-032-conditional-reviewer-requirements)).

### How a finding is tagged

Each reviewer withholds `APPROVED` only on an objective failure of the change, in its remit ([software-engineering:DEC-002-code-review-panel] D3). Each finding opens with one of three tags, which say what it does to the merge ([project-management:DEC-028-agent-as-approver-paths]):

- **`[block]`** marks an objective failure of the change in the reviewer's remit. It withholds `APPROVED`.
- **`[person]`** marks a finding on a passage the change owns. It cites by id an accepted rule of the `<project-conventions>` corpus that binds on an artefact the change alters or brings under a rule. Judging the passage against that rule needs a reading the rule does not settle, or a fact the rule does not name. It withholds no approval, and it is shown to the person who authorises the merge.
- **`[advisory]`** marks every other finding: everything softer, and every defect the change merely sits beside. It withholds nothing.

Each reviewer's definition tags its findings alike. A pre-existing defect blocks only when the change asserts it away, and the defect survives within the reviewer's remit:

- **The assertion** is the pull request's title or body saying that the change fixes or guards against the behaviour. Text the diff adds or edits that says the case is handled is one too.
- **The remedy** is to fix the defect, or to retract the assertion.
- **Any other pre-existing defect** is advisory, however severe.

**Knowledge split.** Each reviewer's definition carries only review knowledge that holds in any project. The reviewer reads the project's own rules from the `<project-conventions>` corpus, the one the software-engineer writes against ([software-engineering:DEC-002-code-review-panel] D4). With no corpus, or an empty one, it reviews as a careful generalist, and says so.

### The reviewer of a change's answers

A reviewer other than their writer checks the answers a change wrote, and `docs-reviewer` does so wherever it reviews a pull request. The answers lie in answer files of the change's own, outside the documents (COR-062 point 1). A revalidation says a document was updated or still holds, and a deferral leaves it out of date until a follow-up. A change may also carry revisits ("Revisits" below).

- **Who checks them.** The agent making the change writes them without asking first, and a reviewer other than that agent checks them (COR-050 point 3, [project-management:DEC-055] point 3). Which reviewer is the project's choice.
- **`docs-reviewer`** checks them wherever it reviews a pull request, as its docs-match-behaviour lens applied to the change's claims about its documents ([software-engineering:DEC-002-code-review-panel] D1).
- **What it reads.** The change check's own list, the section "Answers written in this change" of `pkit friction check`, never an account the author wrote.

**Revisits.** An installed component may declare a link on the place that holds a document (COR-050 point 16).

- **Its targets.** The link takes some of the document's anchors as its targets, such as the tests that verify it.
- **When it asks.** A change to the link's trigger fields asks for a revisit of each target.
- **How a change answers.** A change answers a target that owes an answer by changing it, or by a revisit entry. The entry says `unchanged`, why the target still stands, or `deferred`, the open follow-up that will revisit it.

**What blocks.** Each of these is a `[block]` finding in `docs-reviewer`'s verdict:

- **An `unchanged` reason** that does not hold against the change.
- **A revalidation that replaces revalidations answered apart,** but does not hold against what changed since each of them (COR-062 point 7). That holds for its `unchanged` reason, and for an `updated` document.
- **A deferral** the change writes or rewords, whose reason does not hold, or that names no open follow-up issue.
- **An `updated` document** with no sentence on what changed, or with one that does not match the diff. The sentence lies under the description's `## What changed in each updated document`.
- **A revisit entry.** For a target that owes an answer, a revisit entry blocks in this case:
  - an entry the change writes with a new reason that does not hold against the change, or a `deferred` one that names no open follow-up
- **A revisit by change.** A target the change revisited by changing it, where the target contradicts what the trigger fields the change modified now say. An example is a test that still checks the value the change replaced.
- **A check it cannot run.** It cannot run the change check, so the answers would go unchecked.
- **Itself as the delegate.** The base's configuration names `docs-reviewer` as the delegate, so it would check answers it may have decided (COR-064 point 4).

**How a sentence is read.** `docs-reviewer` reads the section of sentences as the commands that write the list of answers read it. They read a sentence only from an item that opens with the document in a code span, as ``- `path`: sentence``. An item they cannot read, such as one naming the document in bold, gives no sentence, and the finding gives the form it needs.

**What it does not block on.**

- **A deferral the change keeps as it was.** It is not judged again.
- **A revisit line.** It needs no sentence, since a revisit is no revalidation.
- **A changed target** that contradicts nothing, yet leaves part of the change unmet. That is an `[advisory]` finding.
- **An `answered-apart` finding** of the change check. It is debt that no change owes.

**Answers no change owes.** These are a person's decision, or the decision of the delegate a person named (COR-050 point 3, COR-064 point 1):

- an answer on an artefact the change check asked nothing about
- a reason for having no anchors
- a revisit entry the change check does not ask for: one for a target that owes no answer, or one whose outcome alone changed

`docs-reviewer` checks each against what it answers, whoever decided it, and blocks where one does not hold (COR-064 point 4). It cannot read who decided one, so it also names each in an `[advisory]` finding. Where such an answer is `updated`, its sentence is checked like any other.

**Where no reviewer's check holds the merge:**

- **A project that opts out of `docs-reviewer`,** and chooses no other reviewer of the answers. COR-050 point 3 accepts that limit.
- **A pull request that changes only documents, and closes no issue with a `type`** ("The accepted gap" above). COR-050 point 3 names no such case. So where the change wrote answers, have the pull request close an issue that has a `type`.
- **A pull request in `human` review mode.** `docs-reviewer`'s verdict only advises there, and a person who approves checks the answers only by reading them ("When each reviewer is required" above).
- **A bypass on record.** A person merges past `docs-reviewer` with `done-work --bypass` or `--bypass-reviewer docs-reviewer`, giving a reason ([project-management:DEC-028], [project-management:DEC-050]).
- **A sentence edited in the description after the verdict.** An edit of the description makes no verdict stale, so nothing checks the sentence again ([project-management:DEC-055] point 5).
- **A change committed straight to the default branch.** `docs-reviewer` starts from a pull request's number, and requests changes where it cannot fetch one. So it cannot yet check such a change's answers before the commit, as COR-050 point 3 asks.

**What the person who authorises the merge is told** ([project-management:DEC-055] point 3):

- **The answers.** The landing command shows them the change's answers, and each revalidation the merge would leave answered apart from one of the change's own. The whole-repository check reports each such pair as debt until a revalidation reads both.
- **As information.** What they are shown stops nothing.
- **A later head.** Their authorisation covers a later head whose only changes since lie in the answer files the change adds, a clean merge of the base aside. `docs-reviewer`'s verdict goes stale on such a head, as on any change.

## Its operational rules

Wherever software-engineering is installed, every session loads the capability's operational rules, and its accepted rules bind on the session's work (COR-070).

- **Where they are kept.** `rule-sets/swe.md` holds the loaded rule set `SWE`. `rules.md` is the loaded file that `pkit rule-sets generate` writes from it. A project edits neither.
- **How a session reaches them.** Through the capabilities' rules index, which the project's `CLAUDE.md` includes ([the rules README, "The capabilities' rules index"](../../rules/README.md#the-capabilities-rules-index)).
- **Its rule.** `software-engineering:RS-SWE-001` says which tests a session runs while it builds a change, and when it runs the project's full suite.

## Citing this capability's decisions

Cite a decision of this capability by its filename stem, in its own content and elsewhere alike: `[software-engineering:DEC-001-producer-agent-and-conventions-seam]`, `[software-engineering:DEC-002-code-review-panel]`, `[software-engineering:DEC-003-purpose]` and `[software-engineering:DEC-004-skeleton-conventions-in-corpus]`. Cite its rule as `[software-engineering:RS-SWE-001]`.

## Dependencies

- **project-management,** a required dependency the capability declares (COR-030). The panel registers through its reviewer-contribution socket, and folds through its merge gate. It relies on the gate's `type` axis and its `touches-code` floor ([project-management:DEC-032] point D1). The lifecycle holds install, upgrade and uninstall to the declared range.
- **The agents area and its overlay** (COR-013). The adapter deploys each agent of the capability, and resolves its `<project-conventions>` placeholder.
- **The reviewer stack** (COR-024). `critic`, `architect` and `convention-compliance-reviewer` check the producer's work, and `rule-set-reviewer` stands in the stack too ([the agents README, "The rule-set reviewer"](../../agents/README.md#the-rule-set-reviewer)). All four ship in the core, with no install of their own.
- **Conventions content** is out of scope. The corpus is the project's own ([software-engineering:DEC-001-producer-agent-and-conventions-seam]).
