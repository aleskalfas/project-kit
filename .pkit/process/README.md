---
variant: specialized
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/process.py
        - src/project_kit/process_authoring.py
        - src/project_kit/process_dependencies.py
        - src/project_kit/process_graph.py
        - src/project_kit/process_health.py
        - src/project_kit/process_journal.py
        - .pkit/schemas/_defs/process.schema.json
        - .pkit/skills/core/process/process.md
        - .pkit/agents/core/process-author.md
        - src/project_kit/command_runner.py
        - src/project_kit/visibility.py
        - .pkit/migrations/backbone/1.150.0/001-keep-process-journal-logging.sh
      record: [COR-023, COR-032, COR-033, COR-034, COR-035, COR-036, COR-038, COR-042, COR-044, COR-048, COR-053, "project-management:DEC-049", "ADR-009#7", ADR-020, ADR-051, "ADR-057#5", ADR-062]
      artefact:
        - .pkit/process/shape.md
        - .pkit/process/engine.md
        - .pkit/process/connections.md
        - .pkit/process/shape.md#core-and-deferred
        - .pkit/process/shape.md#determinism-across-dynamic-structure
        - .pkit/process/engine.md#the-operations
        - .pkit/process/shape.md#detection-modes-core
        - .pkit/process/connections.md#the-generated-depends-on-list
        - .pkit/agents/README.md#write-carrying-categories
        - .pkit/lifecycle/README.md#how-a-registered-command-is-run
        - .pkit/lifecycle/README.md#validation-the-package-schema
        - .pkit/lifecycle/README.md#uninstall-origin-aware-removal-cor-031-d4
        - .pkit/cli/README.md#process-commands
        - .pkit/cli/README.md#process-new-capabilityprocess-id-flags
        - .pkit/cli/README.md#process-couple-addr---state-s---upstream-addr---relation-r---mode-m---why-prose---version-n---mandatory-reason
        - .pkit/cli/README.md#process-hand-off-addr---upstream-addr---trigger-state---candidates-cmd---resolve-cmd---state-s
        - .pkit/cli/README.md#process-health---process-addr---interpretation-only---json
        - .pkit/cli/README.md#regenerating-a-capabilitys-depends-on-list
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#configuration-file
---

# Process

The process substrate is a content-free state machine that a capability binds its own staged, gated process to ([COR-033](../decisions/core/COR-033-process-substrate.md)). This README and the three pages beside it are the substrate's specification. Why a capability binds a process, and how people author one and connect it, is in [the process guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/process/README.md).

- **Who owns what.** The backbone owns the shape contract and the engine. Each capability ships its own process definition, an instance that conforms to the shape.
- **What every process gets:** a deterministic validator of each move, and a memory of where each subject stands that explains itself ("The two guarantees" below). So an agent can rely on the substrate for three answers, and a person with no manual can read the same ones:
  - where am I
  - may I move
  - am I valid
- **Core and deferred.** Each part of the shape is core, shipped now, or deferred. A deferred part is named in the shape, and built only when a binding needs it ([the shape page, "Core and deferred"](shape.md#core-and-deferred)). It then gains a decision of its own.
- <a id="grounding--status"></a>**Its grounding:** [COR-033](../decisions/core/COR-033-process-substrate.md)'s implications record the bindings that proved the substrate before it shipped.

## Contents

<!-- pkit:contents -->
- [Vocabulary — one substrate, two altitudes](#vocabulary--one-substrate-two-altitudes)
- [The two guarantees](#the-two-guarantees)
- [Gate-checkability (the load-bearing rule)](#gate-checkability-the-load-bearing-rule)
- [Layout](#layout)
- [Binding a process (how a capability uses this)](#binding-a-process-how-a-capability-uses-this)
- [The authoring layer](#the-authoring-layer)
- [The engine](#the-engine)
- [The pages beside this one](#the-pages-beside-this-one)
<!-- /pkit:contents -->

## Vocabulary — one substrate, two altitudes

The substrate's terms come at two altitudes ([COR-033](../decisions/core/COR-033-process-substrate.md) point 1).

- **State machine:** the content-free substrate. It holds states, guarded transitions and a position. Where the project keeps one, it also holds a journal. It knows nothing about issues, screens, documents or trips.
- **Process,** the depth altitude: one discipline's journey over its own subjects, bound to the substrate. A capability authors it.
- **Orchestration,** the breadth altitude, deferred: a system of interacting processes, where one process embeds or hands off to another. It is the same substrate, one altitude up.
- **A discipline's own lifecycle artefact,** such as an issue lifecycle's `workflow.yaml`, is a process definition under this vocabulary, and keeps its own name.

## The two guarantees

The substrate gives every process two guarantees ([COR-033](../decisions/core/COR-033-process-substrate.md) point 3).

- **A deterministic validator.** Given a definition and observable reality, three answers are definite. This holds even for dynamic structure ([the shape page, "Determinism across dynamic structure"](shape.md#determinism-across-dynamic-structure)). The answers are these:
  - where is this subject
  - may it move from here to there
  - is it valid
- **A memory that explains itself.** The status view shows four things, each with a live precheck that wins over any label in prose:
  - where the subject is
  - why it is there
  - how it got there
  - what it may do next
- **The status view's two renderings:** a narrative for people, and a structured form for agents and machines.

## Gate-checkability (the load-bearing rule)

Every transition gate reduces to one of two forms ([COR-033](../decisions/core/COR-033-process-substrate.md) point 4):

- **A deterministic predicate** that the engine evaluates over the subject's artefact or domain state.
- **A recorded authorisation artefact** that the engine confirms exists, and that an authority other than the actor being gated produced. Such an artefact is a person's merge, a reviewer's verdict or a CI check.

An actor's own assertion that a gate passed is never enough. A gate that rests on judgment must leave a trace that another authority made and a check can confirm, or validation is theatre.

- **What the engine compares.** For an authorisation artefact, the engine compares the `produced_by` its predicate reports with the actor the caller names ("The predicate runner" below). It confirms neither.
- **So the gate holds** only where the predicate reads a trace the actor cannot write, and the caller names the actor truthfully.

## Layout

A process's parts sit in five places:

```
src/project_kit/process.py          # the engine, in the pkit binary — it does not reach a project
.pkit/process/
  README.md                         # this page: vocabulary, guarantees, binding, authoring, the engine's contract (reaches a project)
  shape.md                          # the shape contract, field by field
  engine.md                         # the engine's operations
  connections.md                    # composition, the cascade fold, depends_on
.pkit/schemas/_defs/
  process.schema.json               # the shape contract as a JSON-Schema fragment (reaches a project);
                                    # capability instance schemas $ref it to inherit the shape
.pkit/capabilities/<capability>/schemas/<process-id>.yaml
                                    # each capability's own conforming process definition (instance)
.pkit/capabilities/<capability>/project/process/<process-id>/<subject>.journal.jsonl
                                    # each subject's journal, where the project keeps one
```

- **The engine** ships in the binary, as `pkit`'s `process` commands. Capabilities never implement the state machine again: they bind to it ([the engine page, "The operations"](engine.md#the-operations)).
- **The journal,** where kept, is data the project owns, committed or kept in each clone as the project chose. Its path is the engine's ("Where journals live" below).

## Binding a process (how a capability uses this)

A capability binds a process in four steps ([COR-033](../decisions/core/COR-033-process-substrate.md) point 2):

1. Author a process definition as the capability's own instance schema, at `.pkit/capabilities/<capability>/schemas/<process-id>.yaml`. It declares that it conforms to the shape contract, which is `../../../schemas/_defs/process.schema.json` from its folder.
   - Author it through the authoring layer below, not by hand, since the stamps own the file's correctness.
   - The edits no stamp makes yet are listed under "Deferred authoring operations" below.
2. Drive it through the capability's commands, each named by a verb and a subject, which call the engine ("Seam-ordering contract" below).
3. Address the process elsewhere as `<capability>:<process-id>`.
   - A parent embeds it by that address, through a `subprocess` state ([COR-036](../decisions/core/COR-036-process-composition.md)).
   - When its capability offers it under a role, another definition's `depends_on` may address it by role instead, as `<publisher>::<role>:<point>` ([COR-053](../decisions/core/COR-053-connection-points.md)).
   - Orchestration, a concurrent hand-off, stays deferred.
4. When a definition's `depends_on` changes, run `pkit capabilities refresh <capability>`, so that the package's generated `depends-on` list follows it ([the connections page, "The generated `depends-on` list"](connections.md#the-generated-depends-on-list)). `pkit validate` fails until it does.

The schema-binding grammar is unchanged ([COR-023](../decisions/core/COR-023-schema-binds-inline.md)). Capabilities stay independent peers that describe themselves.

## The authoring layer

Authoring a definition goes through three tiers, so it does not mean knowing these pages by heart. The layer's tiers are split by the kind of work each does ([COR-044](../decisions/core/COR-044-process-authoring-layer.md)). A definition's shape is declarative data with closed vocabularies, so a procedure can walk it. Its teeth are logic over the owner's reality, which takes judgment.

- **The commands,** `pkit process new`, `pkit process couple` and `pkit process hand-off` ([the CLI reference, "Process commands"](../cli/README.md#process-commands)):
  - They are deterministic stamps. They scaffold and change the definition, and validate every value against the vocabularies, read as data from the shape contract, `.pkit/schemas/_defs/process.schema.json`.
  - They scaffold a predicate stub that fails closed for each declared evaluable, and register it in the owning capability's package.
  - Each needs an owning capability that the project registers as a component, the same set that contract discovery walks. So a stamp can never write a definition that nothing watches. The CLI reference specifies the grammar, and that refusal.
  - A stamp also refuses a capability whose files the project receives as synced copies, such as one the methodology ships.
  - `pkit process health --interpretation-only --process <address>`, scoped to the definition, is the read-only check that pairs with them. It reports each hand-off contract it cannot interpret, a seam still a stub among them, and counts no missed hand-off.
  - That check reads hand-off contracts alone. A definition that declares none passes it, whatever stubs its states and gates still hold.
- **The `process` skill:** the walkthrough over those commands.
  - It asks the shape questions, and then stamps the answer. The questions are these:
    - what the subject is
    - what each state means
    - which moves are gated
    - whether a trigger is stable
    - whether a candidate source would fail loudly or return empty
  - It also owns the judgment the stamps refuse on purpose. It routes an adopter with no owning capability through capability authoring first.
- **The `process-author` agent:** the teeth, the predicates behind every evaluable the shape declares. They are detections, gates, entry guards, `resume_when`, invariant checks and both seams of a hand-off.
  - It turns the owner's intent, given in plain words, into predicates that satisfy the predicate-runner contract ("The predicate runner" below). Each is read-only and fails closed, and answers about the one subject it was given.
  - It finishes with the same check, scoped to the definition it worked on.
  - A problem of shape it uncovers goes back through the skill's operations, never fixed by hand. Registering a predicate stays with the commands.
  - Stubs fail closed until they are written, so an unwritten predicate reads as indeterminate, never green.

**Its write authority is yours to grant.** The agent owns exactly one overlay category, `process-authoring-targets` in the project's agents overlay ([the agents README, "Write-carrying categories"](../agents/README.md#write-carrying-categories)). The category ships as an explicit empty list.

- **What the agent owns:** nothing, until the project lists its own definition files and predicate-script locations there, one file at a time.
- **What it can never own:** content that sync manages. The deploy refuses an entry that resolves into it, and names the path, so a methodology-shipped definition can never enter the grant.
- **One definition for each invocation:** a discipline of the agent's body, not metadata.

**Deferred authoring operations.** This list is the authoritative one, and the `process` skill points here:

- **`amend`:** evolving states or transitions under live subjects, riding the definition's `version`. It is also the way to repair a coupling or a contract that was declared wrongly.
- **Adding a wait or an invariant to an existing definition** ([COR-034](../decisions/core/COR-034-human-pause-gate.md), [COR-035](../decisions/core/COR-035-process-invariants.md)). A fresh definition declares both through `pkit process new`.
- **Subprocess embedding, cascade folds and open regions,** the three blocks of structural composition. No stamp writes them in any definition, fresh or not ([COR-044](../decisions/core/COR-044-process-authoring-layer.md) point 3). Each lands when a real authoring case needs it.
  - The deferral is of authoring alone. The substrate resolves all three at run time today, so a definition that carries one behaves as these pages describe.
  - What is missing is the grammar of flags that would stamp it.

## The engine

Three parts of the engine's contract stand below ([COR-033](../decisions/core/COR-033-process-substrate.md)): the predicate runner, the seam-ordering contract and the optional journal. The engine's operations, and what each answers, are on [`engine.md`](engine.md#the-operations).

### The predicate runner (engine contract)

A predicate's `run:` names a command that the owning capability registers in its `package.yaml`. It is a leaf of the `commands:` tree, named by the leaf's own name, never a raw path or a shell string. The engine rejects a name that is not registered, with an error that explains itself.

#### How a predicate is run

The engine runs the resolved script through the backbone's one command runner, under the predicate policy. The runner is the lookup and bounded run that the validator registry's query runner shares ([the lifecycle README, "How a registered command is run"](../lifecycle/README.md#how-a-registered-command-is-run)).

- **Its arguments:** explicit argv, the subject and `--json`.
- **Where it runs:** with the working directory at the repository's root.
- **Its environment:** unchanged but for the run's deadline. A predicate may reach the network, so no offline marker is set.
- **Its bound:** the backbone's thirty-second command bound, in a process group of its own. Overrunning kills the whole group, so the interpreter that a `uv run --script` shebang starts as a grandchild stops too.
- **Inside another run:** bounded by the time that run has left, in the outermost run's group (the lifecycle README's "A run inside a run").

#### How an answer is read

The engine reads one JSON object from standard output, and reads it by the kind of predicate:

- **An `inferred` detection, and a `deterministic` gate:** the engine uses the predicate's `result`. So it does for every other predicate that answers `{result, reason}`: an entry guard, an invariant's `check`, a `resume_when`, and a cascade's `membership`.
- **A `classified` detection:** the engine reads `{state, reason}` by the rules in [the shape page's "Detection modes"](shape.md#detection-modes-core), and ignores any `result`. It is the one reading of `state`, and it applies to position resolution alone.
- **An `authorisation-artifact` gate:** the engine reads `{exists, produced_by}`, and computes the gate's result itself. The gate passes when `exists` is true, and `produced_by` is not null and differs from the actor. The engine enforces this cross-authority rule, and ignores any `result` the predicate supplies, so a predicate cannot override it.
- **How `result` and `exists` are read:** by their truth value. `false`, `null`, `0`, an empty string and an empty list or object read as false. Any other value reads as true, the string `"false"` included, so answer with JSON's `true` and `false`.

Predicates must be read-only. `status` runs them live, so a predicate that changes anything is a bug with side-effects.

#### Failure is fail-closed

A predicate that gives no answer is indeterminate, never a pass.

- **No answer:** the predicate errors, times out, prints unparseable JSON or anything but a JSON object, or does not resolve. Each state of a classifier whose answer the engine cannot read is indeterminate too.
- **What is shown:** `status` shows it apart ("couldn't evaluate: …"), and `move` refuses.
- **What else fails closed:** a gate kind the engine does not know, such as one from a newer schema, and a detection mode the engine does not implement. Each is an engine and a definition out of step. A definition whose states declare more than one detection mode fails closed too. None passes silently.
- **From an indeterminate position** no move is permitted, and `status` lists none as permitted. A `from: "*"` move that it shows there is refused, with `can-move`'s reason.
- **Gates are correctness boundaries,** unlike the permission hook, which fails open to stay available.

#### An indeterminate predicate says why

The reason names the predicate, and how its run ended:

- `it exited 2`
- `it was ended by signal 9`
- `it did not answer within 30 s and was stopped`
- `it could not start: …`
- `it printed no JSON document on its standard output`
- `it answered with JSON that is not an object`

What the predicate wrote on standard error is shown beside that reason, attributed to it. Standard error is the predicate's channel for diagnostics, never read as an answer.

- **In the narrative views and a refusal:** under a `the predicate said:` line. The narrative views are `status`, `validate`, `cascade` and `health`, and the refusals are `can-move`'s and `move`'s.
- **In the `--json` views:** a field of its own, `stderr_tail`, beside `reason`, null when there is nothing to show. It is never folded into a reason that a consumer may match on.
- **In `health`:** it is said of each indeterminate finding that a predicate is behind.
  - Such a finding is a `candidates` or `resolve` seam that gave no answer, or an answer without its list, which the reason names as such.
  - It is also an upstream position no detection could place, named by its first state left unevaluated.
  - Each entry of an `indeterminate` list in `health --json` carries `stderr_tail` beside `reason`.
- **In `status --json`:** the detections behind an indeterminate position are listed under `position.unevaluated`, as `{state, reason, stderr_tail}`. There is one entry for each state, even where one classifier's failure is behind several.
- **In the narrative views and a refusal,** one cause is printed once, with the states it leaves indeterminate listed beside it.

Only the tail of the stream is shown:

- its last 10 non-blank lines, and at most 1500 bytes of them, starting with `…` when cut
- decoded with replacement, so a binary stream cannot fail the read
- with every terminal escape sequence removed, and every other control or format character dropped, so a predicate can neither flood nor rewrite the operator's terminal

So a predicate that refuses for a reason the operator can fix should say so on standard error. An instance is a capability's prerequisite gate naming the command that fixes it. That is the message that reaches the operator. None of this changes a verdict: a predicate that cannot be evaluated is indeterminate, whatever it said.

#### Performance: the answer memo

The engine resolves position first, by running the detection predicates. Then it prechecks only the transitions out of the current state.

- **The answer memo.** While the engine reads one subject, it keeps each predicate's answer, keyed on the command and its `with` mapping. So a predicate runs at most once for each resolution of a subject's position. A classifier runs once for all the states that name it.
- **The subject an invocation names** has one memo for the whole invocation. Its predicates run once, however many of the engine's operations need the position.
- **An embedded inner process and a cascade member** get a fresh memo each time the engine resolves their position. One invocation can resolve a cascade member more than once, so a member's predicates run once for each resolution, not once for each invocation.
- **No position is kept** from one invocation to the next. That is the deferred `stored` detection mode.

### Seam-ordering contract (journal-as-intent-log)

A capability's wrapper applies its domain side-effect first, and then calls `move` with `--from`, which journals the move where a journal is kept. This contract holds for every binding, and orders the side-effect against the engine's journal write.

The journal is an intent log, not the source of truth. Live detection is authoritative ([COR-033](../decisions/core/COR-033-process-substrate.md) point 3):

- **Position is derived again each time.** The engine runs the detection predicates against current reality, and never reads a position back from the journal.
- **An entry records an attempt.** The journal entry the engine appends on a legal `move` records that a move was taken. The next `status` reports the real inferred position, whatever the journal says.
- **The same order either way.** The order below holds whether or not the project keeps a journal. With logging off, step 3 validates the move and records nothing.

The order a wrapper follows:

1. The wrapper reads the subject's position from the engine, by `status --json`: the move's origin.
2. The wrapper validates and applies its domain side-effect, such as creating the branch, opening the pull request or editing the label. That change makes live detection report the new state.
3. The wrapper calls the engine's `move` by subprocess, which journals the move where a journal is kept:

```
pkit process move <capability>:<process-id> --to <target> --from <origin>
```

#### Why `--from`

After step 2, live detection already reports the target.

- **Without `--from`,** an engine that took the live position for the origin would be asked for a move from the target to itself. It refuses that move where the definition declares no such transition. Where the definition declares one, a self-loop, it journals the wrong transition.
- **With `--from`,** the engine validates and journals the transition from the stated origin.
- **Bounded by reality.** The engine accepts the stated origin only while live detection places the subject at that origin, or at the target, and refuses it otherwise. The subject is at the origin while the side-effect is not visible yet.
- **When the subject already shows the target,** the origin is taken on the wrapper's word, bounded by the present but not verified. It selects the transition whose gate the engine evaluates.
- **Gates are evaluated against reality after the side-effect.** So the wrapper checks a gate that the move's own side-effect would flip, by `can-move`, before it writes.
- **Side-effect first, with `--from`,** is the canonical order. A wrapper that journals before it applies its side-effect leaves out `--from`, and the move starts at the live position. The cost is that an entry can exist for a side-effect that never landed.

#### When a step fails

Because detection is authoritative, the seam corrects itself whichever step fails.

- **Under the canonical order,** a journal write that fails after the side-effect leaves the journal one move short, and the wrapper reports it.
- **Under journal-first,** a side-effect that fails, wholly or in part, after the entry was written leaves an entry for a move that never landed.
- **Either way,** the next `status` runs detection live, and reports the subject's real inferred position. A journal entry does not say where the subject is: it only records the attempt.
- **A wrapper should still report** a failed side-effect to its caller. A failed side-effect cannot corrupt the engine's notion of position.
- **Wrappers read position from the engine,** by `status --json`, and never infer it again themselves. So position has one source of truth.

### The journal — optional audit (COR-033 point 7)

The engine can keep an append-only journal for each subject ([COR-033](../decisions/core/COR-033-process-substrate.md) point 7). It holds an entry for each move the engine executes, and for each wait's enter and resume.

- **Audit, not runtime.** Position, gates, invariants and the blocked overlay never read it. So the engine's verdicts are the same with it on or off:
  - where the subject is
  - whether it may move
  - whether it is valid
- **The project's choice.** The project declares it in the backbone configuration file ([the CLI reference, "Configuration file"](../cli/README.md#configuration-file)):

```yaml
# .pkit/project/config.yaml
process:
  journal:
    enabled: false    # default — keep no journal
    committed: false  # default — when kept, keep it per clone
```

| Mode | Setting | What the engine does | Journal files in version control | Who can rely on it |
|---|---|---|---|---|
| **Off** (default) | `enabled: false`, or no `process` block | Writes and reads no journal. `status` says "journal logging is not enabled for this project", and a wait has no `since` | Ignored, so a stray file is never committed | Nobody. The audit trail is whatever the binding names instead. For project-management, it is the tracker's timeline with pkit's audit comments |
| **Clone-local** | `enabled: true`, `committed: false` | Appends an entry for each move and each wait event. `status` shows how the subject got here | Ignored. Each clone keeps its own, absent from pull requests and lost with the clone | The clone that made the moves |
| **Committed** | `enabled: true`, `committed: true` | The same | Not ignored: commit them with the work that moved the subject | Everyone: shared, reviewable, durable |

#### Turning it on or off

The backbone's configuration command turns logging on, and a second setting commits the journals:

```
pkit config set process.journal.enabled true --yes
pkit config set process.journal.committed true --yes
```

- **Turning it on:** logging starts then, and nothing is filled in for the past.
- **Turning it off** leaves existing journal files where they are. The engine stops reading and extending them.
- **Upgrading.** The upgrade that introduced the setting keeps logging on for a project it finds keeping journals. That is the backbone migration `1.150.0/001-keep-process-journal-logging.sh`.
  - It writes `enabled: true`, with `committed` following whether git tracks those journals. Otherwise it writes nothing, so logging stays off.
  - It decides from the clone it runs in. A project whose journals lived only in other clones turns logging on itself.

#### An entry

Each line of a journal is one JSON object: a move's entry, or a wait's.

- **A move's entry** holds `ts`, `subject`, `to`, `trigger` and `actor`, and adds these keys:
  - **`from`:** where the origin is known.
  - **`gate_result`:** `pass` or `fail`, where the move has a gate.
  - **`severity`:** where the transition names one.
  - **`version`:** the pkit version that governed the move.
  - **`reason`:** the one place an entry says why its move was taken, written only where the caller gave `move` a `--reason` ([the engine page, "The operations"](engine.md#the-operations)).
- **A wait's entry** holds `ts`, `subject` and `event`, and adds the wait's keys:
  - **`event`:** `blocked-enter` or `blocked-resume`.
  - **`blocked_on`:** the wait's reason.
  - **`at` and `assignee`:** where the wait has them.

#### Journaling a wait

With logging on, a subject's wait is journaled as it starts and as it ends ([COR-034](../decisions/core/COR-034-human-pause-gate.md)). With logging off, the wait is as live and as blocking. Nothing records it, so it has no `since`.

- **The entries.** Entering a blocked position appends a `blocked-enter` entry, and leaving it appends a `blocked-resume` entry. Each is a journal entry, and no other channel emits them. The deferred `hooks` slot will react to these entries once it ships.
- **`since`:** the wait's age, read from the open `blocked-enter` entry. `assignee` is carried from the declaration.
- **Only a move journals a wait.** `status` runs predicates live and writes nothing. A `move` compares the wait at the target state it was given with the wait the journal shows open:
  - A move that parks a subject the journal shows unblocked journals `blocked-enter` as it parks. So `since` counts from then, not from when the person finally acts.
  - A move that leaves a wait the journal shows open, onto a position with no wait, journals `blocked-resume`.
  - A move from one parked state to another journals neither, so `since` still counts from the first park.
- **A wait that clears on its own,** such as an `awaiting-condition` whose `resume_when` turns true, takes no move. Its `blocked-resume` is journaled at the subject's next move, and no command journals it sooner.
- **The live reading wins.** Whether the subject is blocked now is always the live reading, never a journal entry: the pending move for `awaiting-human`, the `resume_when` predicate for `awaiting-condition`. So a resume not yet journaled never misstates the subject's state.

#### Where journals live

Each subject's journal is an append-only JSON Lines file in the owning capability's `project/` subtree, which the project owns:

```
.pkit/capabilities/<capability>/project/process/<process-id>/<subject>.journal.jsonl
```

- **Written** only where the project turns journal logging on.
- **Its path** is the engine's, and its ignore pattern is the backbone's. A capability does not declare either.
- **A sync** leaves it in place, since the subtree is the project's.
- **Uninstalling** a methodology-shipped capability deletes its folder, journals included ([the lifecycle README, "Uninstall"](../lifecycle/README.md#uninstall-origin-aware-removal-cor-031-d4)). Committed journals survive in version control's history.

#### The ignore rules follow the setting

The backbone writes the journal pattern, `.pkit/capabilities/*/project/process/**/*.journal.jsonl`, into the `.gitignore` it renders in `.pkit/`, and never into the project's root `.gitignore`.

- **When it is left out:** where the setting is `committed: true`, with `enabled: true`.
- **When it takes effect:** the configuration command renders the file again at once. A hand edit of the configuration takes effect at the next sync.
- **A journal already tracked** by git stays tracked, whatever the file says.

A capability that still declares the pattern in its own `runtime_ignore` is older than the backbone that took the line over. It cannot keep committed journals ignored:

- **While journals are committed,** the render leaves its entry out, and names it in a comment line. The configuration command reports it too:

```
# dropped: <capability> '<entry>' — the backbone owns the journal pattern while journals are committed
```

- **Validation warns on the entry then** ([the lifecycle README, "Validation: the package schema"](../lifecycle/README.md#validation-the-package-schema)). It names the cure for where the package comes from:
  - a methodology-shipped capability: upgrade it with the backbone
  - an externally sourced capability: move its pin to a release that drops the entry
  - the project's own capability: drop the entry
- **While journals stay ignored,** the entry is redundant. It renders as declared, without a warning.

## The pages beside this one

Each part of the substrate is described here, or on one of the pages beside this one:

- [`shape.md`](shape.md) — what a process definition declares, field by field: the subject, detection modes, waits, invariants and dynamic structure.
- [`engine.md`](engine.md) — the engine's operations, and what each answers or does.
- [`connections.md`](connections.md) — composition, the cascade fold and `depends_on`.

**Where each section that left this page went:**

- <a id="the-shape"></a>"The shape" is [`shape.md`, "The fields"](shape.md#the-fields).
- <a id="subject-cardinality-core"></a>"Subject cardinality" is [`shape.md`, under the same heading](shape.md#subject-cardinality-core).
- <a id="blocked--a-first-class-wait-core"></a>"Blocked — a first-class wait" is [`shape.md`, under the same heading](shape.md#blocked--a-first-class-wait-core).
- <a id="invariants--position-independent-always-checks-core"></a>"Invariants — position-independent always-checks" is [`shape.md`, under the same heading](shape.md#invariants--position-independent-always-checks-core).
- <a id="determinism-across-dynamic-structure-deferred"></a>"Determinism across dynamic structure" is [`shape.md`, under the same heading](shape.md#determinism-across-dynamic-structure).
- <a id="composition--cross-process-outcome-resolution-core"></a>"Composition" is [`connections.md`, under the same heading](connections.md#composition--cross-process-outcome-resolution-core).

The sections that other text names by their headings stand below, each leading to its new home.

### Detection modes (core)

The detection modes, and how the engine reads each, are [`shape.md`'s "Detection modes"](shape.md#detection-modes-core).

### Cascade — fold one child process's member outcomes (core)

The cascade fold is [`connections.md`'s "Cascade"](connections.md#cascade--fold-one-child-processs-member-outcomes-core).

### depends_on — inert cross-process connection metadata (core, COR-038)

`depends_on`, the mandatory mark and the generated `depends-on` list are [`connections.md`'s "depends_on"](connections.md#depends_on--inert-cross-process-connection-metadata-core-cor-038).
