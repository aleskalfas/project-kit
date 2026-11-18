---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/process.py
        - src/project_kit/process_health.py
        - src/project_kit/cli.py
      record: [COR-032, COR-033, COR-034, COR-035, COR-042, ADR-020, ADR-098]
---

# The engine

The operations an agent asks of the process engine, and what each answers or does ([COR-033](../decisions/core/COR-033-process-substrate.md)). The predicate runner, the seam-ordering contract and the journal are in the process area's README.

## The operations

The backbone exposes the engine as the `process` command group of `pkit`. Each core operation but `health` acts on one subject of a process, addressed `<capability>:<process-id>`, and `health` walks every declared hand-off contract. The operations are these:

| Operation | What it answers or does |
|---|---|
| `status` | Where the subject is, and why. How it got here: the journal, or "journal logging is not enabled for this project". Its legal moves, each with a live precheck, and the next hint. Narrative, or `--json`, which carries `journal_logging: {enabled, committed}` beside `journal` |
| `can-move --to <state>` | Validates a candidate move by its gate's precheck, for the actor named. A refusal gives a reason that explains itself, and exits 1 |
| `move --to <state> [--from <state>] [--reason <text>]` | Executes a legal move, and records its journal entry where the project keeps a journal. It will run hooks once they ship. The verdict is the same with logging on or off, and a refusal exits 1 |
| `validate` | Runs the subject's invariants ([COR-035](../decisions/core/COR-035-process-invariants.md)), and reports which hold and which are violated. Narrative or `--json`. It exits non-zero on any violation |
| `cascade` | Resolves the cascade fold the process declares, outside any gated transition, and prints it, narrative or `--json`. A wrapper reads it to combine the fold with gates of its own |
| `health` | Walks every declared hand-off contract ([COR-042](../decisions/core/COR-042-process-health.md)), and reports missed hand-offs: upstream subjects at their trigger with no downstream counterpart |

- **`--subject <id>`** names the subject of a keyed process ([COR-032](../decisions/core/COR-032-keyed-process-subjects.md)). A singleton process ignores it.
- **`move`'s `--from`:** what it names, and when to give it, is the process README's "Seam-ordering contract".
- **`move`'s `--reason`** says why the caller took the move. An instance is the justification for overriding a gate the binding lets it bypass, or a move that one subject's move caused in another. It is recorded on the entry's `reason` as given, and no verdict reads it.
- **`health`** takes no subject. It runs outside the engine's runtime, reports only, and is deterministic. It prints narrative or `--json`, and exits non-zero on any miss or any indeterminate finding.
  - Its flags are the CLI reference's.
- **`cascade`** exits 1 when the fold is not open, or when the process declares none.
- **`--actor <name>`** names the actor whose gates are checked, in the binding's terms. That is the authority the move is made by, as the binding's records name it ([the process README, "Gate-checkability"](README.md#gate-checkability-the-load-bearing-rule)).
  - **From the caller alone.** The engine asks no service for the actor, and takes no default. No fixed value stands for an actor nobody named. An actor given blank names none.
  - **One actor on each call.** `status`, `can-move` and `move` each judge a gate for the actor named, or for none. So a wrapper names the same actor on each call, or a sign-off gate can give two verdicts.
  - **By hand.** A person names the actor as the binding's reference says, such as an account as `pkit account read` prints it. The engine takes the person's word, so a misspelt actor is a false one.
- **With no actor named,** a cross-authority gate whose authorisation exists and names its producer is not judged. Its predicate runs, and its reason gives what the predicate answered, the producer included.
  - **`move` and `can-move` refuse the move.** The refusal says that no actor was named. It asks the caller to name the authority the move is made by, in the binding's terms.
  - **`status` marks the move `?`,** with the reason that no actor was named. For a wait, the engine reads the gate as one that may be open. So the missing actor makes no wait.
  - **Every other gate is judged as for any actor.** A gate whose authorisation does not exist, or names no producer, is shut.
  - **A move none of whose gates compares the actor goes on.** Its journal entry records the actor as empty. `status` shows such a move as made "by no named actor".
- **The structured status.** Each entry of `legal_moves[]` in `status --json` carries two keys about its move's verdict.
  - **`legal_moves[].indeterminate`:** true where the engine can give the move's gate no verdict. Such a move fails closed, and its `reason` says why. The engine gives it for these:
    - a predicate that gave no answer
    - a gate with no predicate, or of a kind the engine does not know
    - a keyed inner process with no subject
    - a cross-authority gate not judged for want of an actor
    - every move from an indeterminate position, where no gate runs
  - **`legal_moves[].needs_actor`:** true only on an entry not judged for want of an actor, whose `indeterminate` is true. It is false on every other entry, another indeterminate one among them. A caller acts on it only by naming the actor and asking again. A document without the key reads as false.
- **A transition's `authorisation`** names who may take the move. The engine does not enforce it, and the caller does. The engine reads it only to tell an `awaiting-human` wait, and where a `prompt` goes.

**The engine is content-free.** It reads any capability's process definition and the subject's reality, and resolves and validates against them.

- **A capability's commands,** its wrappers, supply the definition, the subject and any domain side-effects. They leave the mechanics of the state machine to the engine.
- **Where the engine's code lives:** in the `pkit` binary, `src/project_kit/process.py`, run only as `pkit`'s `process` commands. Its code does not reach a project. Only the process area's pages, the shape contract and the journal's home do.
- **How a wrapper calls it:** by subprocess, never by import.
