---
rule-set: USER
version: 1.2.0
inherits: [living-docs:LDOC@1]
scope:
  paths: [docs/**, README.md, .pkit/**/README.md]
  exclude: [.pkit/release/README.md]
  types: [living-docs:page]
rules:
  RS-USER-001:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-19T16:10:30Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 3 names the two rules a later major of LDOC brings, a successor of the rule on one home and a rule on text alternatives, and adds diagrams' text alternatives to what validation checks where its rule binds. Its sentence that the user space adds one rule, that reader paths stay unbroken, is as it was, so this rule holds.
  RS-USER-002:
    status: proposed
    origin: {why: "The pilot rewrote the permissions README under every accepted rule, and the page kept every claim (#2012). Its opening still said only how the decision core decides, never what a user gains from it. No example in its opening showed one decision (PR #2018). That a reader decides from the opening whether a page is for them is a reason, not a finding, since the pilot tested no readers."}
    pkit:
      friction:
        anchors: {artefact: ["living-docs:RS-LDOC-003", "living-docs:RS-LDOC-005", "RS-WRITE-001"]}
  RS-USER-003:
    status: proposed
    origin: {why: "The pilot rewrote the permissions README under every accepted rule (#2012). It told in prose alone how a deferred command passes from the hook to Claude Code, and on to the person. No diagram drew it, and no rule asked for one (PR #2018). That a diagram spares a reader from keeping each party in mind is a reason, not a finding, since the pilot tested no readers."}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-002#2", "living-docs:DEC-002#3", "living-docs:DEC-002#8"]}
  RS-USER-004:
    status: proposed
    origin: {why: "The pilot's rewrite of the permissions README named four commands of the diagnostic loop, and showed none of what they print (PR #2018). Output typed by hand drifts with nothing to tell. The page quoted the report's headline in prose, and the pilot found that the quote did not match the code (#2012). A fence that a run checks fails when the output moves."}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-002#6"]}
  RS-USER-005:
    status: proposed
    origin: {why: "The pilot rewrote the permissions README under every accepted rule (#2012). Its sections still followed the parts of the mechanism. No section told a reader how to turn enforcement on, and the one headed by what its reader does came near the end (PR #2018). That a reader comes to a page to do something is a reason, not a finding, since the pilot tested no readers."}
    pkit:
      friction:
        anchors: {artefact: ["living-docs:RS-LDOC-004"]}
# The part of a rule that project-kit's console-fence run, scripts/console_fences.py,
# checks (COR-051 point 2). Whoever judges the rest of the rule leaves that part to
# it. The run checks every page's `console` fences, whether this rule binds or not.
checks:
  RS-USER-004:
    - check: console-fences
      part: What each command in a `console` fence prints is the output the fence shows after it.
---

# The user space's definition

The rules project-kit's user space follows: the shared method, `living-docs:LDOC`, and the rules below. The user space is `docs/`, the top-level `README.md` (its entry point) and the adopter-facing READMEs under `.pkit/` ([ADR-055](../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3); the list and each place's assignment are in `.pkit/capabilities/living-docs/project/config.yaml`.

The set's scope selects the pages in those places by their type, living-docs' page type (living-docs DEC-001 point 4). It leaves out the release guide, a README under `.pkit/` that belongs to the technical space.

RS-USER-001 binds. RS-USER-002 to RS-USER-005 are proposed, and bind nothing until the maintainer accepts them (COR-051 point 4). They ask a page to explain before it specifies. They come from the pilot rewrite of the permissions README (#2012).

- **How a proposed rule reads:** a statement, then *How*, then examples, as in `WRITE`. Its reason is the `why` of its origin, in the front matter.
- **What binds:** a rule's statement and its *How*. The examples only illustrate them, and so do a "such as" phrase and a rule's *Note*.
- **The examples:** *Breaks the rule* quotes the permissions README at commit `fe244502` of PR #2018, on `docs/2012-permissions-readme-pilot`. *Keeps the rule* is a rewrite on no branch.
- **Accepting a rule:** it then binds on every page the set's scope selects, all at once. A break the rule's text settles on any of them withholds the rule-set reviewer's approval (COR-060 point 1). So the change that accepts it mends the pages that break it. Or it first narrows where the rule binds, such as through a set whose scope widens a page at a time (COR-060 point 2).
- **Note:** whether any of the proposed rules belongs in `LDOC` is a later question, once they have been tried on more pages.

## RS-USER-001 — Reader paths stay unbroken

The paths the user space's readers take through its pages stay unbroken.

## RS-USER-002 — Open with what the reader gets, and an example

Open the page with what its reader gets from the thing it describes, and a first example of it.

- **How:**
  - The opening is the text between the page's title and the next heading. Both the gain and the example sit there.
  - The reader is the one the page's `reader` field names (RS-LDOC-003). What they get is what they can do, or what stops happening to them, once they use the thing. How it works comes later.
  - The example is one concrete case the reader would meet, such as a command and its output, or a request and its answer. It may follow the paragraph the `reference` template gives the opening.
  - Where RS-WRITE-001 binds too (#1350), the page's first sentence keeps both rules by saying what the reader gets.
  - A page of the `signpost` kind is exempt, since it points into a folder (RS-LDOC-005).
- **Breaks the rule:** "The decision core decides each tool call against the permission model (COR-028): allow, deny or abstain." The opening says how the core decides, never what a user gains from it, and shows no decision.
- **Keeps the rule:** "Permissions let your agents run the commands the project grants without asking you each time, and turn back the commands it denies." An example follows. Under the shipped settings, `git commit -m "fix: x"` runs unasked, and `git push --force` is denied.

## RS-USER-003 — A flow among three or more parties gets a diagram

Where a page describes a flow among three or more parties, show the flow in a diagram as well as in prose.

- **How:**
  - A flow is something passed from party to party in order, such as a request or a decision. A party is a person, or a program that runs in a process of its own, such as a harness or a hook.
  - A page describes a flow where it gives the flow's steps. A page that names a flow in a sentence, and leaves its steps to another page, does not.
  - Write the diagram in the form living-docs DEC-002 gives a diagram (point 2), with its text alternative (point 8). It draws what the prose states, and nothing more, so it is a view of that prose (point 3).
  - Put the diagram in the section whose prose it draws. Where that prose spans sections, put it in the first.
  - The rule does not reach a flow between two parties, however many steps it takes.
- **Breaks the rule:** in "A deny holds against the forms of its command", a deferred command passes from the hook to Claude Code, then to the person. Two paragraphs of prose tell it, and no diagram draws it. One sentence reads "The Claude Code hook asks the person on such a command, except in auto and bypass mode, where the person chose not to be asked."
- **Keeps the rule:** the same two paragraphs, with a sequence diagram and its text alternative beside them. The diagram draws the command going from the agent to Claude Code, the hook's answer, and Claude Code's question to the person.
- **Note:** a reviewer judges the text alternative, until a rule that living-docs' validation checks asks for it on these pages.

## RS-USER-004 — A command the reader runs is shown with its output

Show each command the page tells its reader to run with what it prints, in a `console` fence (living-docs DEC-002 point 6).

- **How:**
  - A command the page tells its reader to run is one it gives as a step, or as the way to see a result. A command the page quotes as input to what it describes is not, such as one the permission hook judges.
  - A command needs showing in one fence only, and the prose may name it again. A page may instead link to the section of another page that shows the command with its output (RS-LDOC-002).
  - A command written with placeholders, such as `<cap>`, is shown run once with real values. Where its full output would bury what the reader needs, show a run on a case small enough that its output stays short.
  - Some commands cannot run as a test, such as one that needs the network, input or a setup the run cannot give. Each takes the form DEC-002 point 6 gives it, and this rule asks no output of it.
  - The rule does not reach a page with no command for its reader to run.
- **Breaks the rule:** "**Arm, disarm and report, in the CLI:** `pkit permissions diagnose on`, `off`, `status` and `report`." The page shows none of what the four commands print.
- **Keeps the rule:** one `console` fence that runs `on`, `status`, `report` and `off` in turn, each followed by what it prints. `<any>` stands for the time left before the session expires.
- **Note:** project-kit's console-fence run checks every `console` fence on a page, as the set's `checks` declare (`CONTRIBUTING.md`, "The pages' console fences").

## RS-USER-005 — Tasks first, lookup material last

Order the sections of a page that serves tasks by its reader's tasks, and put its lookup material last.

- **How:**
  - A task is what the reader comes to do with the thing the page describes, such as turning it on or finding why something failed. A page serves tasks where it tells its reader how to do one.
  - Give each task a section headed by what the reader does. Order the tasks as a reader meets them, such as setting up before daily use.
  - A task's section says in a few words what each term it uses means, or links to where the page explains it.
  - Explanation of how the thing works comes after the tasks. Lookup material comes last. It is what a reader looks up rather than reads through, such as every key of a file.
  - Where the page's kind fixes an order of sections (RS-LDOC-004), that order holds for the sections it names, and this rule orders the rest.
  - The rule does not reach a page that serves no task, such as a signpost.
- **Breaks the rule:** the sections follow the parts of the mechanism, and "The permission-prompt diagnostic loop" comes first. No section tells a reader how to turn enforcement on. The one section headed by what its reader does, "Authoring a fragment", sits near the end.
- **Keeps the rule:** sections such as "Turning permissions on", "Granting an agent a command" and "Finding why a command prompted" come first. A section on how the core splits a compound command follows them. The lookup material comes last, such as the forms a deny matches.
