---
reader: act-developer
kind: guide
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/capabilities/living-docs/agents/living-docs/storyboard.md
      record: ["living-docs:DEC-001#3", "living-docs:DEC-001#6", "living-docs:DEC-001#7"]
      artefact:
        - UC-046
        - ACT-developer
        - REQ-022
        - .pkit/capabilities/living-docs/agent.md#what-it-does
        - .pkit/capabilities/living-docs/README.md#the-readers-point
        - docs/capabilities/living-docs/010-set-up-your-spaces.md#declare-your-readers
---

# Have a page read as its reader

The `living-docs` agent reads a page as the reader it names, and tells you what that reader would miss or would not need. Here you ask for that review, and act on what it finds. What the agent reads, and the record it writes, are in [the reference on the agent](../../../.pkit/capabilities/living-docs/agent.md#what-it-does).

## Why a page is read as its reader

A writer reads their own page as themselves, and fills each gap from what they already know. Whether the page answers its reader's questions, and only those, shows only when someone reads it as that reader. Validation checks that the page names a reader your project declares, and the review judges whether the page serves that reader.

Here is a request and the agent's answers, as its storyboard, the script it follows, gives them, for a review that finds nothing:

```text
User: Review the quick-start as its reader.

living-docs: Reading docs/quick-start.md… Its reader is `user`. Resolving the readers point… "People who use the system: what it does and how to use it." Resolving the reading-evidence point… No result for this page. Reading the page as that reader, against LDOC and the user space's definition…

living-docs: Nothing found. The page answers what a first-time user asks and nothing else, its steps lead on to the next page, and each statement rests on its anchors. No record written.
```

## Ask for the review

In Claude Code, ask your session to use the `living-docs` agent, such as "Use the living-docs agent to review docs/install.md as its reader". It reads the page as that reader, with the reader's needs as your project declares them ([Set up your spaces, "Declare your readers"](010-set-up-your-spaces.md#declare-your-readers)). It judges the page against the rules that bind on it, `LDOC`'s and its space's own:

- **Something found.** It writes one record, `.agent-workspace/living-docs/reader-review/<page>.md`. Each finding names the rule the page breaks and quotes the passage. It says what the reader misses or does not need, with a direction to take.
- **Nothing found.** It says so in one line, as above, and writes nothing.
- **A question for you.** A passage a rule leaves to your judgement, such as a fact the page states twice, is listed as a question rather than a break.
- **On a pull request.** Ask, and name the pull request, and the agent posts the record as a comment.
- **Reader paths.** The page's rules may ask that reader paths stay unbroken, as the user space's rule does. The agent then follows each of the reader's paths that passes through the page ([the reference, "The readers point"](../../../.pkit/capabilities/living-docs/README.md#the-readers-point)). With none, it follows the page's own links.

A finding reads like this one, on a page of the user space whose reader is `user`:

```text
### RS-LDOC-003: the page explains the hook's internals to a user

> The hook loads the model once for each process, and keeps it in memory.

- What the reader does not need: how the hook loads the model. A user who turns enforcement on acts on none of it.
- Direction: cut the sentence, or move it to a page of the technical space.
```

The agent leaves to validation what validation checks, such as whether the page names a reader your project declares. It changes nothing it reviews, so you mend each finding yourself.
