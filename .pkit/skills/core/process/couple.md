# Coupling your process to an upstream one

This walkthrough declares that your process depends on another process. The declaration lands **in your own definition** and the upstream is untouched — per COR-038, a dependency is always recorded by the subscriber.

Read the dispatcher (`process.md`) first for the acceptance gate and the shared framing.

## What this does and does not do

A coupling is **metadata**. It records that a relationship exists, so that anyone reading your definition — human or tool — can see what your process leans on. The engine does not evaluate it: nothing gates on it, nothing moves because of it, no event fires. If the author expects declaring a coupling to *make something happen*, correct that expectation before stamping, or they will file a bug against working software.

What a coupling does buy: the relationship becomes visible and reviewable, and it is the thing a hand-off contract attaches to when the author wants the methodology to actually *check* the dependency (`hand-off.md`).

## The questions

### 1. Which of your states depends on something?

A coupling hangs off a state of *your* process — the position at which the dependency is real. "We can't start work until the design is settled" attaches to your starting state, not to your process as a whole. Get the specific state.

Be accurate about what the hosting state does, though: it is **audit colour** — it records where the dependency is meaningful for a reader. It does not scope any check. A hand-off contract added later walks the *upstream's* trigger state regardless of which of your states hosts the entry; the hosting state's only mechanical role is telling `hand-off` which entry you mean when one upstream is coupled from several of your states.

### 2. What is the upstream, and does it exist?

The upstream has two address forms; ask which one the author means:

- **By implementation** — `<capability>:<process-id>`: this one capability's definition, and no other.
- **By role** — `<publisher>::<role>:<point>`: the process *offered* at that point by whichever installed capability is the role's active provider (COR-053). Prefer it when the author depends on *what the process does* rather than on who ships it: replacing that capability with another providing the same role then touches nothing in the author's definition. It only works where a capability declares the role and offers the process under it in its package metadata — confirm the point exists before choosing it.

Confirm the address resolves to a real definition — **your check is the only real gate here**: the stamp only *warns* on an upstream it cannot resolve, it does not refuse, because an upstream may legitimately live in a capability that is not installed yet. A role address is resolved the way `health` resolves it, through the wiring, and the warning says why it reaches nothing (no provider installed, providers in conflict, no process at that point). A coupling onto a typo is worse than no coupling, because it reads as a declared relationship that nothing will ever check.

### 3. What kind of relationship is it?

The relation vocabulary is a **closed set read from the shape contract** — read it and offer exactly those values. Rather than reciting names at the author, ask what the dependency *does*, and map their answer:

- Does the upstream's state merely *inform* your reader, with nothing hanging on it?
- Does your work *become sensible only once* the upstream reaches readiness?
- Is your work *set in motion by* the upstream's progress?
- Are the two *constrained together* — a rule spanning both, rather than a one-way lean?

If the author's answer does not fit any value the contract carries, do not stretch one to fit. Say the vocabulary has no name for it, and stop — a mislabelled relation is a lie in a file people trust.

### 4. Pull or push?

Also a closed vocabulary. The distinction is *who does the reading*:

- **Pull** — your side reads the upstream on its own turn, when it needs to know.
- **Push** — something outside the engine mediates the relationship. Be explicit that the substrate does not provide this mediation; declaring `push` records how the world works, it does not wire anything up.

### 5. Why?

The reason is **required**, and it is not a formality — it is the field the render surfaces, so it is what a future reader (often the author, months later) uses to decide whether the coupling still earns its place. Push for a sentence about *purpose*, not a restatement of the relation: "we cannot start until the design settles, or we build the wrong thing" tells a reader something; "gates on readiness" does not.

### 6. Does it target one interface version?

Optional (`--version <n>`). An upstream's interface carries an integer version that changes only when its public contract breaks. Naming it pins the connection: it then connects only to an upstream offered at that same version, and any other version leaves it inert — which is what the author wants when their side relies on the contract as it stands today. Leave it out and the connection binds on the upstream's existence alone. Read the version off the upstream (the `version` in its definition's `interface` block, or the offered point's `schema_version`) rather than guessing it.

### 7. Is it mandatory?

Optional (`--mandatory <reason>`), and the default is **no**: a connection is optional unless the author can say why their capability cannot work without the upstream. The mark has teeth outside the definition — installing or upgrading the author's capability is **refused** while the upstream is missing (or at another version, with question 6 answered), and upgrading or uninstalling the upstream warns. The reason is required and is quoted in every one of those refusals and warnings, so push for one a stranger would accept: "reviews are meaningless without the issue they review" rather than "needed".

## Stamp it

Invoke `pkit process couple` with the settled values — `--version` and `--mandatory` only when questions 6 and 7 said so. `--dry-run` previews the entry in place. The command checks the address against the contract's grammar, validates relation and mode against the contract's vocabularies and refuses an unknown value by naming the legal set.

Two behaviours worth knowing before you run it:

- **Re-declaring the identical entry is a clean no-op**, so a re-run after an interruption is safe.
- **A conflicting declaration is refused, not overwritten** — a declared edge is a decision, not a draft. Several entries onto the same upstream are legitimate when the relation or mode differs; what is refused is the same relationship declared two different ways — a different reason, version or mark.

If the author wants to *change* an entry they already declared, that is the deferred repair path: name it (`amend`), and point at the hand-edit-plus-validate interim route recorded in `.pkit/cli/README.md`. Do not stamp your way around it.

The stamp does **not** bump the definition's version — an additive, inert declaration does not change what live subjects mean.

## Refresh the generated list

The capability's package metadata carries a generated copy of every coupling its definitions declare (the `depends-on` list in its `connections` block), which the capability lifecycle reads the mandatory marks from. The stamp writes the definition only, never package metadata, so when the copy is now stale it ends by naming the command that regenerates it: `pkit capabilities refresh <capability>`. **Run it** — `pkit validate` fails until the copy follows the definitions. A coupling that adds nothing new to the copy (another way of depending on an upstream already listed, at the same version and mark) leaves it fresh, and the stamp names nothing.

Refresh is an authoring-time command: it refuses a kit-shipped capability installed in an adopting project, whose package file is core-owned. If the author is coupling a definition there, stop — that definition is not theirs to edit either.

## Wrap up

- Ask whether this coupling should be **checked**, not merely recorded: if it represents work passing from the upstream to you, `hand-off.md` is the operation that makes a dropped hand-off visible. This is the most valuable question in the walkthrough, because a coupling alone will never tell anyone that something was forgotten.
- Read the entry back from the definition to confirm it landed as intended, and confirm the refresh ran if the stamp named it. `pkit validate` then confirms the definition is well-formed and the generated list fresh; beyond that no runtime check can say anything about a coupling — per COR-038 the engine never reads `depends_on`, which is exactly why the next operation exists.
- Commit per COR-008, the definition and the refreshed package file together.
