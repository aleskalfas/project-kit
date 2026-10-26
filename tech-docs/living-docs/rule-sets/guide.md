---
rule-set: GUIDE
version: 1.0.0
inherits: [living-docs:LDOC@1, WRITE@2]
scope:
  paths: [docs/**, README.md]
  types: [living-docs:page]
rules:
  RS-GUIDE-001:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The pilot's first pass rewrote the permissions README under every accepted rule and kept every claim (#2012). It still never said what problem the model solves (PR #2018). The research found that the strongest pages open with the problem, in countable terms, such as pnpm's hundred copies of one package (pnpm.io/motivation). On 25 October the maintainer set where the problems come from: the needs and goals the analysis gives the page's readers (#1928)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#4", "living-docs:DEC-001#7"]}
  RS-GUIDE-002:
    status: accepted
    origin: {date: 2026-10-26, by: "Aleš Kalfas", why: "The research found that the strongest pages prove each claim in a way the reader can check. uv and ripgrep give benchmarks, each with its method. The weakest give labels with no proof, such as Vite's README and Rust's three pillars. The pilot's second pass stated five claims, and proved each by a command's real output (PR #2018). On 26 October the maintainer, Aleš Kalfas, set what comes first for a claim with no proof: \"We should not just reword our decisions when we see that they are not truth we should first have to care whether we have a gap in our implementation first.\" (#1928)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#4"]}
  RS-GUIDE-003:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The research found that trusted pages compare the thing with its alternatives. pnpm marks a feature table with ✅ and ❌ against npm and Yarn, and Renovate's comparison credits Dependabot where Dependabot is better. Diátaxis holds that an explanation can and must consider alternatives (diataxis.fr/explanation). The pilot's comparison credits Claude Code's own settings with setup and the cost of a call (PR #2018)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#4"]}
  RS-GUIDE-004:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The research found that trusted pages state an honest limit, such as ripgrep's \"Why shouldn't I use ripgrep?\" and \"What Kubernetes is not\". A reader told when a thing does not fit can trust what the page claims for it. That is a reason, not a finding, since the research tested no readers. The pilot's guide says when the model is not needed (PR #2018)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#4"]}
  RS-GUIDE-005:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The pilot's first pass explained the decision core in its first sentence, and showed no decision anywhere on the page (PR #2018). The research found that the strongest pages show a worked example early, as Git's chapter on rerere, direnv's README and uv's documentation do. That one case teaches faster than a mechanism is a reason, not a finding, since neither tested readers."}
  RS-GUIDE-006:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The research found that documentation sites draw their key mechanism once, as Vite, pnpm, Terraform and Docker each do. None of 85 READMEs drew a Mermaid diagram, so the rule leaves the entry README out. The pilot's second pass drew how a tool call is decided in one flowchart, beside the prose that explains it (PR #2018)."}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-002#2", "living-docs:DEC-002#3", "living-docs:DEC-002#8"]}
  RS-GUIDE-007:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The pilot's first pass named four commands of the diagnostic loop, and showed none of what they print (PR #2018). It quoted the report's headline in prose, and the pilot found that the quote did not match the code (#2012). Output typed by hand drifts with nothing to tell. A fence that a run checks fails when the output moves."}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-002#6"]}
  RS-GUIDE-008:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The pilot's first pass followed the parts of the mechanism. Its one section headed by what its reader does, \"Authoring a fragment\", came near the page's end, after most of its lookup material (PR #2018). The maintainer adopted the order of a reader's tasks, with reference last, on 25 October (#2022). That a reader comes to a guide to do something is a reason, not a finding, since the pilot tested no readers."}
  RS-GUIDE-009:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The research found callouts in 15 of 85 READMEs, each for a caveat, a status or a deprecation, and none for an advantage. GitHub's own writing guidance gives an article one or two callouts, and never two in a row (docs.github.com, basic writing and formatting syntax). A callout that sells loses the weight a warning needs."}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-002#7"]}
  RS-GUIDE-010:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The research found a short list of claims in 23 of 85 READMEs, such as uv's, ruff's and fd's. It sits under a heading such as Highlights or Features. A reader who scans the list reaches each claim's proof in one step. The entry README gave its highlights this form (#2027)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#4"]}
# The part of a rule that project-kit's console-fence run, scripts/console_fences.py,
# checks (COR-051 point 2). The run is the test of every page's `console` fences that
# living-docs DEC-002 point 6 asks for. It stands in for this rule's part only where the
# rule binds, and whoever judges the rest of the rule there leaves that part to it.
checks:
  RS-GUIDE-007:
    - check: console-fences
      part: What each command in a `console` fence prints is the output the fence shows after it.
---

# GUIDE — the guides' rules

The rules that project-kit's guides in `docs/` and its entry README, `README.md`, follow beyond those of every user page (ADR-069 point 4). They make a page say why the thing it describes exists, prove what it claims, and explain before it specifies.

- **What it binds:** its own rules, and those of `WRITE` and of the shared method, `living-docs:LDOC`, on each page its scope selects. The scope selects `docs/**` and `README.md` by path, and living-docs' page type, as the space definitions do.
- **Why a set of its own:** a scope belongs to a set (COR-051 point 2), and these rules bind the guides and the entry README alone. The references sit under `.pkit/`, outside the scope, so no rule here reaches one (ADR-069 point 1). `README.md` is in the scope by its path, whatever kind it names.
- **What it inherits:** `LDOC` at major 1, since a set that holds a project's documentation rules inherits it (living-docs DEC-001 point 3). `WRITE` at major 2, since the guides and the entry README follow it (ADR-069 point 4). This set's scope is the one that selects them all.
- **What it does not inherit:**
  - `USER`, whose scope selects every page this one does, so its rules bind there without a pin
  - `REWORK`, whose rules bind only on the pages its own scope lists, whoever inherits it (COR-051 point 7)
- **Accepted:** every rule of this set's own is accepted, and binds now beside `WRITE`'s and `LDOC`'s accepted rules (COR-051 point 4). They bind on every page the scope selects, the entry README included. The maintainer adopted the style they write down on 25 October, after research into how well-known projects state their advantages (#2022). RS-GUIDE-002 dates from 26 October, when he set its first step for a claim with no proof, a look for a gap (#1928).
- **How a rule reads:** a statement, then *How*, then examples, as in `WRITE`. Its reason is the `why` of its origin, in the front matter.
- **What binds:** a rule's statement and its *How*. The examples only illustrate them, and so do a "such as" phrase, a sentence that starts "An instance is", and a rule's *Note*.
- **The examples:** *Breaks the rule* quotes the permissions README's first pilot pass, at commit `fe244502` of PR #2018, unless it names another source. *Keeps the rule* quotes the permissions guide, `docs/permissions/README.md`, or the entry README, as this change leaves them. An example on no branch says so.
- **Accepting a rule added later:** it then binds on every page the scope selects, all at once. A break the rule's text settles on any of them withholds the rule-set reviewer's approval (COR-060 point 1). So the change that accepts it mends the pages that break it, or first leaves them out of the scope (COR-060 point 2).
- **Leaving a page out:** a page the scope leaves out loses `WRITE` and `LDOC` through this set too. `LDOC` still reaches it through `USER`.
- **Note:** whether any of these rules belongs in `LDOC` is a later question, once they have been tried on more pages.

## RS-GUIDE-001 — Open with the reader's problem

Open an introducing page's case with the problem that the thing it describes solves for its reader, stated concretely.

- **How:**
  - An introducing page is the README of a folder in `docs/` holding one area's, capability's or adapter's guide (ADR-069 point 1), or the entry README. The rule binds only on such a page.
  - The problem comes in the page's first second-level section after its lead and any contents list. The lead may say what the thing is.
  - The problem is a need or a goal the analysis gives, stated as what goes wrong while it is unmet. The need is an actor's, and the goal a use case's or a journey's. The page anchors the use case or journey it draws from, or the actor where neither states it.
  - Concretely means that each problem names what its reader meets: a count, a step that fails, or a thing they cannot do. A quality word alone, such as hard or slow, names none.
- **Breaks the rule:** the first pass's first second-level section, "The permission-prompt diagnostic loop", opens with "The diagnostic loop is opt-in and recommend-only." No section of the page names a problem the model solves.
- **Keeps the rule:** the entry README's "Why" lists six problems, such as "**Taking an update could overwrite your own edits.** So nobody takes one, and the copies drift apart." The page anchors the actors and the journeys they come from.

## RS-GUIDE-002 — Each advantage is a bold claim with a proof

State each advantage a page claims as one sentence in bold, and give a proof its reader can check.

- **How:**
  - An advantage is a sentence that says the thing spares its reader something or gains them something, such as fewer prompts. A sentence that only says what the thing is or does is none.
  - A limit the claim needs in order to hold, such as "in their common forms", stands inside the bold.
  - The proof follows the claim, or the claim links to it. It is one of these:
    - a command and its output, in a `console` fence (RS-GUIDE-007)
    - a measured number, with how it was measured: what, on what, and how many times
  - A claim with no proof is first checked against what the thing does, before its words change:
    - **The thing falls short of the claim:** file the gap as an issue. Narrow the claim to what holds, and restore it once the gap is closed.
    - **The thing does what the claim says:** add the proof, and keep the claim.
    - **The thing is not meant to do what the claim says:** cut the claim, or narrow it.
  - A record that decides the behaviour proves nothing, since it says what was decided, not what the software does.
  - Table cells are exempt, since a cell holds no sentence of its own.
- **Breaks the rule:** the entry README at commit `26199137` of PR #2030. Its mental model says "That's *why* a sync can't conflict with your edits, and why you keep everything you write." The claim is not in bold, and neither proves it nor links to a proof. At commit `922f8077` the README drops "in one step", though the upgrade takes one step and only the proof was missing.
- **Keeps the rule:** the fence after the guide's list of claims runs two calls in bypass mode, and the hook denies one and allows the other. It proves the claim "**Each agent's denies hold in every mode, the harness's most permissive included.**" The entry README's "in one step" is back, proved by a fence that upgrades a project made by release 1.134.0.

## RS-GUIDE-003 — Compare with the alternative, and credit it

Compare the thing an introducing page describes with what its reader would otherwise use, and credit the alternative where it is better.

- **How:**
  - An introducing page is the README of a folder in `docs/` holding one area's, capability's or adapter's guide (ADR-069 point 1), or the entry README. The rule binds only on such a page.
  - The alternative is what the reader uses without the thing, such as the harness's own settings, or files kept by hand. The page names it.
  - With three or more points of comparison, the comparison is a table. Each row is one point, each column one option, and each cell opens with ✅ or ❌. A cell may say why in a few words.
  - What the thing costs its reader is among the points, such as its setup and its running cost. Each point where the alternative is better is marked ✅ for the alternative.
- **Breaks the rule:** a table on no branch compares the model with Claude Code's settings on five points, each ✅ for the model. It leaves out setup and the cost of a call, where the settings are better.
- **Keeps the rule:** the guide's "Compared with the harness's own settings". Its rows "Setup" and "Cost of a call" mark Claude Code's settings ✅, and say why.

## RS-GUIDE-004 — Say when the reader does not need it

Say on an introducing page when its reader does not need the thing it describes, or what the thing is not.

- **How:**
  - An introducing page is the README of a folder in `docs/` holding one area's, capability's or adapter's guide (ADR-069 point 1), or the entry README. The rule binds only on such a page.
  - Each case is a situation the reader can recognise in their work, such as working alone, or something they might mistake the thing for. Name what serves them instead, where something does.
  - Keep the cases together, under a heading or a label of their own, such as "When not to use it".
- **Breaks the rule:** the first pass never says when a project can do without the model.
- **Keeps the rule:** the guide's "When you do not need it", such as "**Every agent may do the same.** A rule in the harness's settings says it once, for the whole session."

## RS-GUIDE-005 — A first example early

Show a first example of the thing at work before the page's first section on how the thing works, and before its first task section.

- **How:**
  - The example is one case the reader would meet, shown whole, such as a command with its output, or a call with its verdict.
  - A section on how the thing works is one whose subject is the thing's parts and what passes between them. A task section is one RS-GUIDE-008 names.
  - The rule binds on every page the scope selects but a signpost (RS-LDOC-005).
- **Breaks the rule:** the first pass explains the decision core in its first sentence, and shows no case of a decision anywhere on the page.
- **Keeps the rule:** the guide's first section shows the hook deny `gh issue edit 7` to the agent `researcher`, and allow it to `builder`. "How a tool call is decided" and "Turning it on" come after it.

## RS-GUIDE-006 — The key mechanism gets a diagram

Draw the key mechanism a guide explains in a diagram, in the section that explains it.

- **How:**
  - The key mechanism is the one the page's first section on how the thing works explains (RS-GUIDE-005). It is what passes between the thing's parts, and in what order. An instance is how a tool call is decided.
  - Write the diagram in the form living-docs DEC-002 gives one (points 2, 3 and 8).
  - The rule does not reach the entry README, nor a page with no section on how the thing works, such as one task's page.
- **Breaks the rule:** a rewrite on no branch of the guide's "How a tool call is decided" with its flowchart taken out. Its bullets alone tell how a call passes from the hook to the core, and on to the harness.
- **Keeps the rule:** the guide's "How a tool call is decided" holds a flowchart with its `accTitle` and `accDescr`, and a bullet for each part the flowchart draws.
- **Note:** once RS-LDOC-008 binds on these pages, living-docs' validation checks the diagram's text alternative.

## RS-GUIDE-007 — Commands with their real output

Show each command the page gives its reader to run with what it prints, in a `console` fence (living-docs DEC-002 point 6).

- **How:**
  - A command the page gives its reader to run is one in a fence, or one a task's step tells the reader to run. A command the prose names as where to look something up is not one. An instance is "`pkit permissions catalog` lists the privileges". Nor is a command the page quotes as input to what it describes, such as one the permission hook judges.
  - A command needs showing in one fence only, and the prose may name it again. A page may instead link to the section of another page that shows the command with its output, and anchor that section (RS-LDOC-002).
  - A command written with placeholders, such as `<cap>`, is shown run once with real values. Where its full output would bury what the reader needs, a filter in the command, such as `grep`, keeps the part that matters.
  - A command that cannot run as a test, such as one that needs the network or input, takes the form DEC-002 point 6 gives it. That form is a fence of its shell's language, such as `sh`, with no output. A command whose output differs from one operating system to another counts as one.
  - The rule does not reach a page with no command for its reader to run.
- **Breaks the rule:** the entry README at commit `26199137` of PR #2030. Its "Install" gives `pkit --help` in a fence with no language and no output, though the command can run as a test.
- **Keeps the rule:** the guide's "Find out why a call prompted" runs `diagnose on`, two calls, `diagnose report` and `diagnose off` in one `console` fence, each followed by what it printed.
- **Note:** the console-fence run checks the output part of this rule, as the set's `checks` declare (`CONTRIBUTING.md`, "The pages' console fences").

## RS-GUIDE-008 — Tasks in the order they depend on each other, lookup material last

Put each task section after the sections of the tasks it needs done first, and put the page's lookup material last.

- **How:**
  - A task section tells the reader how to do something with the thing, such as turning it on or finding why a call prompted. A section that only groups task sections, such as "Common tasks", counts as the first of them.
  - A task needs another done first when its steps fail, or show nothing, until the other is done. An instance is reading the diagnostic report before enforcement is on.
  - Lookup material is what a reader looks up rather than reads through, such as every key of a file, or links for going further. It comes after every task section.
  - The rule does not reach a page that has no task section.
- **Breaks the rule:** the first pass puts its one task section, "Authoring a fragment", near the page's end. Lookup material comes before it, such as how a compound command is split.
- **Keeps the rule:** the guide's "Turning it on" comes before "Common tasks", whose first task, "Find out why a call prompted", needs enforcement on. Its lookup material is in the reference, which it links.

## RS-GUIDE-009 — Callouts only for caveats, two at most, never in a row

Use a callout only for a caveat or a warning, at most two on a page, and never two in a row.

- **How:**
  - A callout is a block quote whose first line is `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]` or `[!CAUTION]` (living-docs DEC-002 point 7).
  - A caveat or a warning tells the reader of a limit or a risk, such as what the thing does not prevent. A selling point, a summary or a tip is neither, and stays in the prose.
  - Two callouts are in a row when nothing but blank lines stands between them.
- **Breaks the rule:** a callout on no branch, "> [!TIP] Each agent has grants of its own, down to the command." It sells a claim the guide's prose already proves.
- **Keeps the rule:** the guide's one callout, a `[!WARNING]`, opens with "A deny is a speed bump, not a security boundary". The entry README holds two warnings, with sections between them.

## RS-GUIDE-010 — The entry README's highlights

Give the entry README a highlight for each advantage it proves in a section of its own: a bold claim that links to its proof.

- **How:**
  - The highlights are a list under a heading of their own, such as "Highlights", after the problems the page opens with (RS-GUIDE-001).
  - Each item is one sentence. Its claim is in bold, as RS-GUIDE-002 asks, and links to the section that proves it.
  - An advantage only a comparison's table states needs no highlight.
  - The rule binds only on the user space's entry point, `README.md`.
- **Breaks the rule:** a list on no branch of bold labels with no claim and no link, such as "**Fast.** **Safe.** **Extensible.**"
- **Keeps the rule:** the entry README's "Highlights", such as "**[Your files stay yours](#your-files-stay-yours):** a sync keeps the lines you added."
