---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/process.py
        - src/project_kit/process_health.py
        - src/project_kit/process_journal.py
        - src/project_kit/command_runner.py
        - src/project_kit/visibility.py
        - src/project_kit/cli.py
        - .pkit/migrations/backbone/1.150.0/001-keep-process-journal-logging.sh
      record: [COR-032, COR-033, COR-034, COR-035, COR-042, COR-048, "project-management:DEC-049", ADR-009#7, ADR-020, ADR-057#5, ADR-062]
      artefact:
        - .pkit/process/shape.md#detection-modes-core
        - .pkit/lifecycle/README.md#how-a-registered-command-is-run
        - .pkit/lifecycle/README.md#validation-the-package-schema
        - .pkit/lifecycle/README.md#uninstall-origin-aware-removal-cor-031-d4
---

# The engine

This page gives the operations an agent asks of the engine, and how the engine runs and reads a predicate ([COR-033](../decisions/core/COR-033-process-substrate.md)). It also gives how a capability's command orders its change against a move, and the optional journal.

## Contents

<!-- pkit:contents -->
- [The operations](#the-operations)
- [The predicate runner (engine contract)](#the-predicate-runner-engine-contract)
- [Seam-ordering contract (journal-as-intent-log)](#seam-ordering-contract-journal-as-intent-log)
- [The journal — optional audit (COR-033 point 7)](#the-journal--optional-audit-cor-033-point-7)
<!-- /pkit:contents -->

## The operations

The backbone exposes the engine as the `process` command group of `pkit`. Its core operations act on a process addressed `<capability>:<process-id>`, each on one subject of it but `health`:

| Operation | What it answers or does |
|---|---|
| `status` | Where the subject is, and why. How it got here: the journal, or "journal logging is not enabled for this project". Its legal moves, each with a live precheck, and the next hint. Narrative, or `--json`, which carries `journal_logging: {enabled, committed}` beside `journal` |
| `can-move --to <state>` | Validates a candidate move by its gate's precheck, for the actor named. A refusal gives a reason that explains itself, and exits 1 |
| `move --to <state> [--from <state>] [--reason <text>]` | Executes a legal move, and records its journal entry where the project keeps a journal. It will run hooks once they ship. The verdict is the same with logging on or off, and a refusal exits 1 |
| `validate` | Runs the subject's invariants ([COR-035](../decisions/core/COR-035-process-invariants.md)), and reports which hold and which are violated. Narrative or `--json`. It exits non-zero on any violation |
| `cascade` | Resolves the cascade fold the process declares, outside any gated transition, and prints it, narrative or `--json`. A wrapper reads it to combine the fold with gates of its own |
| `health` | Walks every declared hand-off contract ([COR-042](../decisions/core/COR-042-process-health.md)), and reports missed hand-offs: upstream subjects at their trigger with no downstream counterpart |

- **`--subject <id>`** names the subject of a keyed process ([COR-032](../decisions/core/COR-032-keyed-process-subjects.md)). A singleton process takes none.
- **`move`'s `--from`** names the state the subject held before the caller applied the move's domain side-effect. The move is validated and journaled from there ("Seam-ordering contract" below).
- **`move`'s `--reason`** says why the caller took the move. An instance is the justification for overriding a gate the binding lets it bypass, or a move that one subject's move caused in another. It is recorded on the entry's `reason` as given, and no verdict reads it.
- **`health`** takes no subject. It runs outside the engine's runtime, reports only, and is deterministic. It prints narrative or `--json`, and exits non-zero on any miss or any indeterminate finding.
  - `--process <address>` scopes it to one process's contracts.
  - `--interpretation-only` reports only the contracts it cannot interpret, a seam still a stub among them, and counts no miss. It is the authoring check a definition's author runs, scoped to that definition.
- **`cascade`** exits 1 when the fold is not open, or when the process declares none.
- **`--actor <login>`** names the actor whose gates are checked. `status` and `can-move` take `operator` without it, and `move` the caller's `gh` login. A wrapper names one actor on each call, or a sign-off gate can give two verdicts.
- **A transition's `authorisation`** names who may take the move. The engine does not enforce it, and the caller does. The engine reads it only to tell an `awaiting-human` wait, and where a `prompt` goes.

**The engine is content-free.** It reads any capability's process definition and the subject's reality, and resolves and validates against them.

- **A capability's commands,** the discipline's wrappers named by a verb and a subject, supply the definition, the subject and any domain side-effects. They leave the mechanics of the state machine to the engine.
- **Where the engine's code lives:** in the `pkit` binary, `src/project_kit/process.py`, run only as `pkit`'s `process` commands. Its code does not reach a project. Only the process area's pages, the shape contract and the journal's home do.
- **How a wrapper calls it:** by subprocess, never by import.

## The predicate runner (engine contract)

A predicate's `run:` names a command that the owning capability registers in its `package.yaml`. It is a leaf of the `commands:` tree, named by the leaf's own name, never a raw path or a shell string. The engine rejects a name that is not registered, with an error that explains itself.

### How a predicate is run

The engine runs the resolved script through the backbone's one command runner, under the predicate policy. The runner is the lookup and bounded run that the validator registry's query runner shares ([the lifecycle README, "How a registered command is run"](../lifecycle/README.md#how-a-registered-command-is-run)).

- **Its arguments:** explicit argv, the subject and `--json`.
- **Where it runs:** with the working directory at the repository's root.
- **Its environment:** unchanged but for the run's deadline. A predicate may reach the network, so no offline marker is set.
- **Its bound:** the backbone's thirty-second command bound, in a process group of its own. Overrunning kills the whole group, so the interpreter that a `uv run --script` shebang starts as a grandchild stops too.
- **Inside another run:** bounded by the time that run has left, in the outermost run's group (the lifecycle README's "A run inside a run").

### How an answer is read

The engine reads one JSON object from standard output, and reads it by the kind of predicate:

- **An `inferred` detection, and a `deterministic` gate:** the engine uses the predicate's `result`. So it does for every other predicate that answers `{result, reason}`: an entry guard, an invariant's `check`, a `resume_when`, and a cascade's `membership`.
- **A `classified` detection:** the engine reads `{state, reason}` by the rules in [the shape page's "Detection modes"](shape.md#detection-modes-core), and ignores any `result`. It is the one reading of `state`, and it applies to position resolution alone.
- **An `authorisation-artifact` gate:** the engine reads `{exists, produced_by}`, and computes the gate's result itself. The gate passes when `exists` is true, and `produced_by` is not null and differs from the actor. The engine enforces this cross-authority rule, and ignores any `result` the predicate supplies, so a predicate cannot override it.
- **How `result` and `exists` are read:** by their truth value. `false`, `null`, `0`, an empty string and an empty list or object read as false. Any other value reads as true, the string `"false"` included, so answer with JSON's `true` and `false`.

Predicates must be read-only. `status` runs them live, so a predicate that changes anything is a bug with side-effects.

### Failure is fail-closed

A predicate that gives no answer is indeterminate, never a pass.

- **No answer:** the predicate errors, times out, prints unparseable JSON or anything but a JSON object, or does not resolve. Each state of a classifier whose answer the engine cannot read is indeterminate too.
- **What is shown:** `status` shows it apart ("couldn't evaluate: …"), and `move` refuses.
- **What else fails closed:** a gate kind the engine does not know, such as one from a newer schema, and a detection mode the engine does not implement. Each is an engine and a definition out of step. So does a definition whose states declare more than one detection mode. None passes silently.
- **From an indeterminate position** no move is permitted, and `status` lists none as permitted. A `from: "*"` move that it shows there is refused, with `can-move`'s reason.
- **Gates are correctness boundaries,** unlike the permission hook, which fails open to stay available.

### An indeterminate predicate says why

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

### Performance: the answer memo

The engine resolves position first, by running the detection predicates. Then it prechecks only the transitions out of the current state.

- **The answer memo.** While the engine reads one subject, it keeps each predicate's answer, keyed on the command and its `with` mapping. So a predicate runs at most once for each resolution of a subject's position. A classifier runs once for all the states that name it.
- **The subject an invocation names** has one memo for the whole invocation. Its predicates run once, however many of the engine's operations need the position.
- **An embedded inner process and a cascade member** get a fresh memo each time the engine resolves their position. One invocation can resolve a cascade member more than once, so a member's predicates run once for each resolution, not once for each invocation.
- **No position is kept** from one invocation to the next. That is the deferred `stored` detection mode.

## Seam-ordering contract (journal-as-intent-log)

This contract holds for every binding. It says how a capability's wrapper orders its own domain side-effect against the engine's journal write.

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

### Why `--from`

After step 2, live detection already reports the target.

- **Without `--from`,** an engine that took the live position for the origin would be asked for a move from the target to itself. It refuses that move where the definition declares no such transition. Where the definition declares one, a self-loop, it journals the wrong transition.
- **With `--from`,** the engine validates and journals the transition from the stated origin.
- **Bounded by reality.** The engine accepts the stated origin only while live detection places the subject at that origin, or at the target, and refuses it otherwise. The subject is at the origin while the side-effect is not visible yet.
- **When the subject already shows the target,** the origin is taken on the wrapper's word, bounded by the present but not verified. It selects the transition whose gate the engine evaluates.
- **Gates are evaluated against reality after the side-effect.** So the wrapper checks a gate that the move's own side-effect would flip, by `can-move`, before it writes.
- **Side-effect first, with `--from`,** is the canonical order. A wrapper that journals before it applies its side-effect leaves out `--from`, and the move starts at the live position. The cost is that an entry can exist for a side-effect that never landed.

### When a step fails

Because detection is authoritative, the seam corrects itself whichever step fails.

- **Under the canonical order,** a journal write that fails after the side-effect leaves the journal one move short, and the wrapper reports it.
- **Under journal-first,** a side-effect that fails, wholly or in part, after the entry was written leaves an entry for a move that never landed.
- **Either way,** the next `status` runs detection live, and reports the subject's real inferred position. A journal entry does not say where the subject is: it only records the attempt.
- **A wrapper should still report** a failed side-effect to its caller. A failed side-effect cannot corrupt the engine's notion of position.
- **Wrappers read position from the engine,** by `status --json`, and never infer it again themselves. So position has one source of truth.

## The journal — optional audit (COR-033 point 7)

The engine can keep an append-only journal for each subject ([COR-033](../decisions/core/COR-033-process-substrate.md) point 7). It holds an entry for each move the engine executes, and for each wait's enter and resume.

- **Audit, not runtime.** Position, gates, invariants and the blocked overlay never read it. So the engine's verdicts are the same with it on or off: where the subject is, whether it may move, and whether it is valid.
- **The project's choice.** The project declares it in the backbone configuration file, which the CLI reference describes:

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

### Turning it on or off

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

### An entry

Each line of a journal is one JSON object: a move's entry, or a wait's.

- **A move's entry** holds `ts`, `subject`, `to`, `trigger` and `actor`. It adds `from` where the origin is known, `gate_result` (`pass` or `fail`) where the move has a gate, and `severity` where the transition names one.
- **`version`** is the pkit version that governed the move.
- **`reason`** is the one place an entry says why its move was taken, as the caller gave it with `--reason`.
- **A wait's entry** holds `ts`, `subject` and `event`, `blocked-enter` or `blocked-resume`. It adds `blocked_on`, and `at` and `assignee` where the wait has them.

### Journaling a wait

With logging on, a subject's wait is journaled as it starts and as it ends ([COR-034](../decisions/core/COR-034-human-pause-gate.md)). With logging off, the wait is as live and as blocking, nothing records it, and it has no `since`.

- **The entries.** Entering a blocked position appends a `blocked-enter` entry, and leaving it a `blocked-resume` entry. Each is a journal entry, and no other channel emits them. The deferred `hooks` slot will react to these entries once it ships.
- **`since`,** the wait's age, is read from the open `blocked-enter` entry. `assignee` is carried from the declaration.
- **Only a move journals a wait.** `status` runs predicates live and writes nothing. A `move` compares the wait at the target state it was given with the wait the journal shows open:
  - A move that parks a subject the journal shows unblocked journals `blocked-enter` as it parks. So `since` counts from then, not from when the person finally acts.
  - A move that leaves a wait the journal shows open, onto a position with no wait, journals `blocked-resume`.
  - A move from one parked state to another journals neither, so `since` still counts from the first park.
- **A wait that clears on its own,** such as an `awaiting-condition` whose `resume_when` turns true, takes no move. Its `blocked-resume` is journaled at the subject's next move, and no command journals it sooner.
- **The live reading wins.** Whether the subject is blocked now is always the live reading, never a journal entry: the pending move for `awaiting-human`, the `resume_when` predicate for `awaiting-condition`. So a resume not yet journaled never misstates the subject's state.

### Where journals live

Each subject's journal is an append-only JSON Lines file in the owning capability's `project/` subtree, which the project owns:

```
.pkit/capabilities/<capability>/project/process/<process-id>/<subject>.journal.jsonl
```

- **Written** only where the project turns journal logging on.
- **Its path** is the engine's, and its ignore pattern the backbone's. A capability does not declare either.
- **A sync** leaves it in place, since the subtree is the project's.
- **Uninstalling** a methodology-shipped capability deletes its folder, journals included ([the lifecycle README, "Uninstall"](../lifecycle/README.md#uninstall-origin-aware-removal-cor-031-d4)). Committed journals survive in version control's history.

### The ignore rules follow the setting

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
