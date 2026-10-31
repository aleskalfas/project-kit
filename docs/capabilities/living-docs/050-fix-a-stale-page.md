---
reader: act-developer
kind: guide
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/capabilities/living-docs/agents/living-docs/storyboard.md
      record: ["living-docs:DEC-001", "COR-050#3", "COR-050#4", "COR-050#5", "COR-050#6", "COR-050#9", "project-management:DEC-056"]
      artefact:
        - UC-045
        - ACT-developer
        - REQ-022
        - .pkit/capabilities/living-docs/agent.md#what-it-does
        - .pkit/capabilities/living-docs/agent.md#as-the-fixer-of-pages
        - .pkit/capabilities/living-docs/agent.md#what-it-never-does
        - .pkit/cli/README.md#friction-explain-artefact---json
        - .pkit/cli/README.md#friction-debt---json
        - .pkit/cli/README.md#friction-revalidate-artefact---outcome-updatedunchanged---because-text---keep-anchor---yes----dry-run
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
        - .pkit/capabilities/project-management/README.md#8-optional-grant-the-fixers-your-capabilities-declare
        - .pkit/capabilities/project-management/README.md#starting-the-fixers--fix-drift
---

# Fix a stale page

A page is stale when something it anchors changed and nobody has answered for the page since. Here you find out why a page was flagged, have the `living-docs` agent propose its fix, and answer for the page. What the agent reads and writes is in [the reference on the agent](../../../.pkit/capabilities/living-docs/agent.md#what-it-does).

## Contents

<!-- pkit:contents -->
- [Why the fix is proposed, not applied](#why-the-fix-is-proposed-not-applied)
- [Find the stale pages](#find-the-stale-pages)
- [Have the fix proposed](#have-the-fix-proposed)
- [Answer for the page](#answer-for-the-page)
- [Have stale pages fixed with nobody watching](#have-stale-pages-fixed-with-nobody-watching)
<!-- /pkit:contents -->

## Why the fix is proposed, not applied

A flagged page needs someone to judge which of its statements the change broke. An agent that rewrites the page alone can rewrite a true statement, or match the page to a bug in the code. So the agent proposes each fix with the commits behind it, and you decide what lands.

Here is a request and the agent's answers, as its storyboard, the script it follows, gives them:

```text
User: The install guide went stale after the output-flag change. Can you propose the fix?

living-docs: Running pkit friction explain on docs/install.md… It is stale on one anchor, path src/cli/**: two commits since its revalidation — a3f9c1e "feat(cli): rename --out to --output" and 7b21d04 "fix(cli): default output folder is ./out". Reading both against the page…

living-docs: Two passages in "Running it" no longer hold: the flag is still written `--out`, and the default folder is still given as the working directory. The anchor itself is right, and every other statement it grounds still holds, so the proposal rewrites those two passages and nothing else.

living-docs: Proposed: the diff is in .agent-workspace/living-docs/fix/install/install.md.diff and the pull-request body beside it, both naming the two commits and the anchor. Once the change is applied, the answer is yours to give: pkit friction revalidate docs/install.md --outcome updated. Anything to change in the proposal?

User: No, that's right.

living-docs: Then it's ready: `git apply --check` takes the diff cleanly on your branch. Nothing was applied.
```

## Find the stale pages

The change check of your pull request names each page the change flagged. `pkit friction debt` lists every page the default branch left stale, the oldest first ([the CLI reference](../../../.pkit/cli/README.md#friction-debt---json)). For one page, `pkit friction explain` names these ([the CLI reference](../../../.pkit/cli/README.md#friction-explain-artefact---json)):

- which anchor changed
- in which commit
- what clears it

Each fence on this page starts from a fresh project, so it first installs living-docs and creates the user space, their output dropped. Below, the page `docs/greet.md` anchors `src/greet.py`, and a later commit changed the script:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs new space user --yes >/dev/null 2>&1
$ mkdir -p src && echo 'print("Hello")' > src/greet.py
$ pkit living-docs new page docs/greet.md --space user --kind reference --reader user --title "Greeting" --path src/greet.py >/dev/null
$ git add -A && git commit -qm "Add the greeting and its page"
$ echo 'print("Hi")' > src/greet.py && git commit -qam "Say hi"
$ pkit friction debt | sed -n '/^DEBT/,/^$/p'
DEBT — oldest first, by the author date of its origin
  <any>  stale  docs/greet.md  path src/greet.py  <any>  Doc Examples  "Say hi"  today
$ pkit friction explain docs/greet.md | sed -n '/^FINDINGS/,/deferred/p'
FINDINGS — as pkit friction check --all reports them: what changed, what clears it
  stale  path src/greet.py  changed after its revalidation point <any>: first in <any> "Say hi" (Doc Examples, <any>), a change not put back since — revalidate the artefact, or defer the anchor again
    changed in, oldest first:
      <any>  Doc Examples  Say hi
    clears it — revalidate the artefact, or defer the anchor:
      updated    pkit friction revalidate docs/greet.md --outcome updated
      unchanged  pkit friction revalidate docs/greet.md --outcome unchanged --because '<why the content still holds>'
      deferred   pkit friction defer docs/greet.md --anchor path:src/greet.py --reason '<why it can wait>'
```

## Have the fix proposed

In Claude Code, ask your session to use the `living-docs` agent, such as "Use the living-docs agent to propose the fix for docs/greet.md". It reads each commit behind the changed anchor, then judges each statement the anchor grounds:

- **Still true:** left as it is.
- **No longer true:** rewritten to match.
- **Its ground moved,** such as a renamed file: its anchor re-pointed.
- **Grounded by nothing now:** given a new anchor, taken out, or raised with you as a question.
- **The change looks wrong,** rather than the page: the agent says so, and leaves the page alone.
- **Stale on a captured source:** the agent never fetches the source ([the reference, "What it never does"](../../../.pkit/capabilities/living-docs/agent.md#what-it-never-does)). It names both versions and the link, and asks you what changed in the source that bears on the page.

It writes a diff of the page and a pull-request body under `.agent-workspace/living-docs/fix/<page>/`, and applies nothing. Where no statement needs to change, it drafts the reason for an `unchanged` answer instead, for you to confirm or rewrite. Review the diff, then apply it:

```sh
git apply .agent-workspace/living-docs/fix/<page>/<file>.diff
```

## Answer for the page

The answer goes in the pull request that mends the page. For a page your own change flagged, the agent building the change may write it, and a reviewer other than that agent checks it. For a page the default branch left stale, you decide it. It is one of three:

- **`updated`:** you mended the page.
- **`unchanged`:** the page still holds, and you say why.
- **Deferred:** one anchor's change can wait, and your reason names the follow-up that will answer it. The page stays in the debt listing until then.

Below, the page is mended and answered `updated`, and the change check finds nothing left to answer. Commit the answer file the command writes with the page ([the CLI reference, "friction revalidate"](../../../.pkit/cli/README.md#friction-revalidate-artefact---outcome-updatedunchanged---because-text---keep-anchor---yes----dry-run)):

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs new space user --yes >/dev/null 2>&1
$ mkdir -p src && echo 'print("Hello")' > src/greet.py
$ pkit living-docs new page docs/greet.md --space user --kind reference --reader user --title "Greeting" --path src/greet.py >/dev/null
$ git add -A && git commit -qm "Add the greeting and its page"
$ git checkout -qb say-hi
$ echo 'print("Hi")' > src/greet.py && echo 'The script prints "Hi".' >> docs/greet.md
$ pkit friction revalidate docs/greet.md --outcome updated --yes | tail -1
Wrote answers[docs/greet.md].revalidated in .pkit/project/friction/answers/<any>.yaml.
$ pkit friction check 2>/dev/null | grep -e "^Friction" -e "^Result"
Friction change check — nothing to answer   (the blocks: pkit validate)
Result: passed   (warning)
```

The other two answers take the commands `pkit friction explain` printed under "Find the stale pages".

## Have stale pages fixed with nobody watching

With project-management installed, its command `pkit pm fix-drift` starts the agent on every page the default branch left stale ([project-management's README, "Starting the fixers"](../../../.pkit/capabilities/project-management/README.md#starting-the-fixers--fix-drift)). The agent then proposes each fix as above. It holds a page whose fix needs what only you know, such as what changed in a source, with one question.

- **The grant.** The command starts the agent only once your project grants it, which the install may have asked you about ([project-management's README, "Grant the fixers"](../../../.pkit/capabilities/project-management/README.md#8-optional-grant-the-fixers-your-capabilities-declare)).
- **Nothing applied.** Nothing the run proposes lands until you accept it.
