---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-27
---

# What an answer is, what it should be called, and what of it must be kept

## The question

Friction's "answers" (COR-050, COR-062) are committed to the repository, one YAML file per change, in `.pkit/project/friction/answers/`. Three questions, which may have one answer between them:

1. **What is the entity, and what should it be called?** "Friction" names a state of a document. "Answer" names a move in a conversation, and says nothing of what it does.
2. **What of it must outlive the change that wrote it?** As review evidence it belongs to the change. What does friction need after the merge?
3. **Where should that live?** The repository, the host's pull request, an issue, or a mix.

Nothing is decided here. This note explores, for the maintainer to decide.

## How it works today, in plain terms

- A document (a page, a use case, a glossary term) lists its **anchors**: the code, records or other documents it rests on.
- A change that alters an anchor leaves the document with **friction**: it may be out of date. The change check fails until the change answers for it.
- The change answers in one of three ways, written by `pkit friction revalidate` or `pkit friction defer` into one YAML file of the change's own:
  - **updated**: "I changed the document to match";
  - **unchanged**: "it still holds, because …";
  - **deferred**: "it is out of date on this anchor until #N".
- A reviewer other than the author checks each reason against the diff.
- After the merge, the **whole-repository check** works out, for every document, the commit where its latest answer landed (its revalidation point). Anything that changed under it since is **debt**. Deferrals are debt with a named follow-up. The fixers propose fixes from that list.

An example file (`20261026T024311Z-b91cff99.yaml`):

```yaml
answers:
  - artefact: .pkit/capabilities/doc-examples/README.md
    read:
      - 20261026T023422Z-1926903c.yaml
    revalidated:
      at: 2026-10-26T02:43:11Z
      outcome: unchanged
      unchanged-because: living-docs DEC-001 changed only where … so the page holds.
```

`read` lists the earlier answer files on that document this answer took into account. The newest answer that read the others replaces them. Two answers that never read each other were "answered apart", and are debt until one reads both (COR-062 point 7).

## Why it looks complex

- **373 files** on 27 October, 260 of them from the one-time move out of the documents' blocks (`moved-*.yaml`). Most hold no live answer: newer answers replaced them. Pruning is decided (COR-062 point 8) and not built (#2207).
- **Long `read` lists.** Each answer names every other answer file on its document, so a busy document's answer lists dozens of files.
- **One file per change, many documents per file.** A file is the change's, not the document's, so nothing in the folder is organised by document.
- **Nobody is meant to read it.** The commands are the interface (`pkit friction explain <doc>`, `pkit friction debt`), but the folder is what a newcomer sees.

## What the answers do: three jobs

1. **The change's own judgement, checked.** The author says whether each touched document still holds, and a reviewer checks it. This is the insurance that an agent assessed the change honestly. It needs the answer to exist **in the change**: the diff, the pull request.
2. **The marker for the whole-repository check.** "This document was judged at commit X." Without it, an `unchanged` document would read as stale forever after its anchor changed. It needs something **after the merge**.
3. **Known debt.** A deferral says "out of date until #N". It must outlive the change. The follow-up issue it names already carries most of it.

An `unchanged` reason also serves as an audit trail ("why did we think this still held?"), which the pull request's history on the host keeps too.

## The name

Same logic as "friction": name what the entity is, not the move that produces it. Candidates:

| Name | updated / unchanged | deferred | Weak spot |
|---|---|---|---|
| **reconciliation** | reconciled with its ground: by changing it, or confirmed as it is | reconciliation deferred to #N | none serious; pairs with "debt" (friction never reconciled) |
| judgement | judged still true, or brought true | judged out of date until #N | names the authority, not the effect; close to the reviewers' "verdict" |
| settlement | friction settled | settlement postponed | in English it leans to an agreement or a payment |
| attestation | attested true | a deferral attests nothing | |

The maintainer likes **reconciliation** (27 October). It also helps question 2: a reconciliation has a lasting result, *reconciled at commit X*, which is what friction needs, not the transcript of the review.

## Options for what is kept, and where

- **A. As today.** Every answer committed, in answer files. Works offline and on any host; a revert takes its answers with it. Cost: a growing folder, mostly dead, that nobody reads directly.
- **B. The judgement in the change, only the result kept.** The answers live in the pull request as review evidence (a generated comment, or the check's output, which the gate reads). A merge through a passing gate counts as reconciled, so the gate's merge is the marker. Only deferrals persist, as the follow-up issues they name or one small file. Cost: friction reads the host, which COR-050 avoided (a squash merge rebuilds the message; descriptions were rejected as a source); changes that bypass the gate (direct commits, projects with no gate) need another way to be seen; COR-050 and COR-062 largely superseded; the fixers' staleness reading rebuilt.
- **C. Keep the result, drop the transcript.** Commit only what friction needs after the merge: per document, the latest reconciliation's commit marker and open deferrals, in a compact form; the reasons stay in the change's review. Cost: a file that changes accept edits to again brings back conflicts between parallel changes, the problem answer files solved, unless the form is add-only too.
- **D. A as today, made readable.** Keep committed answers, but prune (#2207), and give the folder a README and a per-document view, so a reader sees state, not history.

## Forces

- The methodology runs offline and in a sandbox, with no host access, by design (rule 14, COR-028). B weakens that.
- Parallel changes must not conflict on bookkeeping (COR-062's whole reason). C must keep that.
- The release 2.0.0 ships the move into committed answer files. Few projects run it yet, so a second move later is cheap.
- A rename touches COR-050, COR-062, the glossary, the friction commands' words and the folder path (with a migration if the folder moves).

## Open questions

- Is the gate's merge a trustworthy enough marker for job 2, and what sees a change that bypassed it?
- Does anything need an `unchanged` reason after the merge, beyond audit?
- Could job 2's marker be derived from git alone (the merge commit of a change whose check passed), with no file at all?
- If B or C, what does the whole-repository check read on a fresh clone with no network?
