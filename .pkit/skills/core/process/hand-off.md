# Making a hand-off checkable

This walkthrough adds a **hand-off contract** to a coupling you already declared, which is what turns an inert relationship into one the methodology can check. Once it exists, the health surface can answer a question nothing else in the substrate answers: *is upstream work sitting ready with nobody picking it up?*

Read the dispatcher (`process.md`) first for the acceptance gate and the shared framing.

## What the check actually does

For each contract, the health walk finds the upstream subjects **currently at a nominated state**, asks your side which downstream subject corresponds to each, and reports every upstream subject whose answer is *nobody*. It asks about **existence**, not progress — whether a counterpart exists at all, not how far along it is. Downstream progress is that process's own business.

Two properties to convey before authoring, because they shape what the author should declare (per COR-042):

- **It reports; it never blocks.** No move is prevented, nothing is remediated. Its value is that a human or an automated run *notices*.
- **It reads live reality on each run.** There is no memory of "this subject was ready last week" — a subject that is not at the trigger *right now* is not in the report.

## The questions

### 1. Which coupling?

The contract attaches to a `depends_on` entry that already exists. If the author has not declared the dependency yet, do `couple.md` first — the contract is an addition to an edge, not a substitute for one.

Naming the upstream is normally enough to identify the entry. When the same upstream is coupled from several of your states, the stamp needs the hosting state too in order to know which entry you mean — that is the only thing the hosting state decides here.

### 2. At which upstream state is work ready to hand over? — and is that state *stable*?

This is the **trigger**, and this question carries the operation's first refusal.

The trigger must be a state the upstream subject **holds** until the hand-off happens (or until it ends). If the subject passes through it briefly — a moment during a move, a state something else immediately advances it out of — then a dropped hand-off leaves no trace, because by the time anyone checks, nobody is at the trigger. The check would report clean and the work would still be lost.

So ask directly: *once a subject reaches this state, does it stay there until someone picks the work up?* Do not accept a shrug. If the answer is no, the honest outcomes are to pick a different (stable) state, or to declare no contract at all — a contract on a fleeting trigger is worse than none, because it manufactures confidence. Do not stamp until this is answered.

### 3. How do we find the upstream subjects that are ready?

This is the **candidate source**: a predicate that answers "which subjects might be at the trigger?" Each candidate it returns is then confirmed one at a time against the engine's own reading of position, so the source may be broad — it may not be *wrong*.

Here is the operation's second refusal. A candidate source that fails loudly is safe: the check reports indeterminate and nobody is misled. A candidate source that **quietly returns nothing** — pointed at a directory that has since moved, a query whose filter silently matches zero rows — is the dangerous case, because "no candidates" is indistinguishable from "nothing is waiting", and the report goes green forever.

So ask: *what would make this source return nothing even though work is waiting, and how would anyone find out?* Push for a source that would fail rather than return empty when its assumptions break. Do not stamp until this is answered.

### 4. How do we find the downstream counterpart?

This is the **resolve** seam: given one upstream subject, which subject on your side corresponds to it — or none? Settle what the correspondence actually *is* in the author's terms ("the unit whose reference field carries the document's id"). Several answers are fine — existence of at least one satisfies the hand-off — and several upstream subjects legitimately resolving to the same downstream is fine too.

Both seams are predicates, so their logic is teeth-work, not shape-work. Here you settle what each *must answer*, and the stamp scaffolds a fail-closed stub for each new one; implementing them is the `process-author` agent's territory once it ships, and until then a hand-authored predicate against the predicate-runner contract in `.pkit/process/README.md`.

## Stamp it

Invoke `pkit process hand-off` with the settled trigger and both seams. `--dry-run` previews the contract. The command validates the trigger against the upstream definition where it can resolve it, refuses a state the upstream does not have, and scaffolds plus registers seam stubs that do not yet exist. As with `couple`, an identical contract is a clean no-op, a conflicting one is refused rather than overwritten, and the definition's version is not bumped.

## Implement the seams, then check interpretability

The contract is declared; the seams are stubs. Until both are implemented, the contract cannot be interpreted — which the completion check will tell you, and which is the honest state to be in.

Then run the done-signal, scoped to your own address:

```
pkit process health --interpretation-only --process <capability>:<process-id>
```

**Check the report actually found your contract before reading anything into a green.** If it says no contracts are declared, that is not a pass — you just declared one, so something is wrong with what the checker can see rather than with the contract. Treat "zero contracts" on an address you just authored as red until you have explained it; `.pkit/cli/README.md` records the current known cause and its remedy under the health command.

Otherwise, read the result carefully, because two very different things can be red:

- **Indeterminate** — the contract cannot be interpreted: an address that does not resolve, a trigger that is not a real state, a seam that is unregistered, missing, or still carrying the scaffold's stub marker. This is the authoring signal, and it must reach clean before the work is done.
- **A miss** — a real upstream subject with no downstream counterpart. This view does not report misses at all, deliberately: a fresh, correct contract routinely has them (upstream work waiting is the situation that motivated the contract), so miss-count is never the authoring done-signal.

When misses *are* what you want to see, that is the default `pkit process health` run — the operational check, not the authoring one.

## Wrap up

- Commit per COR-008: the contract and its seam stubs are one logical unit.
- Say plainly what the author has bought: from now on, a dropped hand-off at this trigger is visible to anyone who runs the check, and its exit code is the hook an automated run can gate on. Nothing is enforced — the value is that it stops being invisible.
