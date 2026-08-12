# Scaffolding a new process

This walkthrough declares a process's shape from nothing: what it tracks, the states it moves through, how it moves, and a stub for every predicate the shape will need. It ends with a definition that lints clean and a set of unimplemented, fail-closed stubs — an honest skeleton, not a working process.

Read the dispatcher (`process.md`) first for the acceptance gate and the shared framing.

## Before the questions: where does the definition live?

A process definition is an artifact **of a capability** — its address is `<capability>:<process-id>`, and its predicates must be registered in that capability's package for the engine to run them. So the first thing to establish is the owning capability, and there are only two cases:

- **The author has one.** Confirm two things about it. It must be **registered with the project**, or the health surface will never walk what you author into it (see the trap in `hand-off.md`). And it must be **the author's own** — a capability the methodology ships is overwritten on the next sync, so a definition stamped there is silently destroyed later (the no-shared-files invariant; a capability incubated in the project is adopter-owned, per COR-031).
- **The author has none.** They need a capability first. Route them through the capability-authoring path (`capability-author`), then come back. A capability incubated in the project is first-class and adopter-owned, so this is a real route and not a detour into someone else's territory.

This routing is *this skill's* job and deliberately not the stamp's — `pkit process new` refuses a capability-less address with a clean error and no guesswork. Do not try to make the command do it.

## The questions

Work through these in order; each maps to a flag on the stamp. Keep the author's language, and translate to the contract's vocabulary yourself.

### 1. What is the subject?

The thing that moves through the process, and whether there is one of it or many:

- **Singleton** — one journey, no identity needed. "Our quarterly audit."
- **Keyed** — many independent units, each at its own position (per COR-032). "Each document." "Each application." Ask what identifies a unit and record it as the key; the engine does not interpret it, so a descriptive name is the point.

Worth knowing while you ask: the shape contract also records a pointer to where the subject's *domain* data lives (the process tracks a position, not the thing itself), but the stamp has no flag for it yet — so do not collect an answer you cannot stamp.

### 2. What are the states, and what does each mean?

Draw out the journey in the author's own words, then name each state and write its **meaning** as prose. The meaning is load-bearing: it is what a status view renders, so "waiting for the reviewer to accept or reject" beats "in review".

Two properties to settle per state:

- **Which are entry states** (where a subject starts — several are allowed, and one may be guarded), and **which are terminal** (where the journey ends, and which therefore double as the process's outcomes).
- **Declaration order matters.** It can be load-bearing for detection precedence, so keep the order the author describes rather than alphabetising.

Resist the urge to add states the author did not describe. A three-state process that matches reality is worth more than a seven-state one that anticipates it.

### 3. How does a subject move?

Each transition is `from → to`, plus the **trigger**: the named action that causes it. Ask what the author would *call* the action ("approve", "send-back", "publish") — that name becomes an identifier, so it must be kebab-case, and it is part of the transition's identity. Two transitions between the same pair of states are legitimate when their triggers differ (an `approve` beside a `force-approve`); the stamp addresses a transition by its full `(from, to, trigger)` key precisely so both remain reachable.

For each transition, settle **authorisation** — *who* may make this move. Read the contract's vocabulary and offer what it actually carries; as it stands that is three answers, not two: a human authorises it, an automated actor may make it unprompted, or a script performs it. The stamp defaults to requiring a human, which is the safe floor — only widen where the author is explicit about it.

Back-edges and self-loops are expressible; ask about them rather than assuming a forward-only journey. Real processes send things back.

### 4. Which moves are gated, and what else must hold?

- **Gates** — a transition that must not fire unless some condition holds. Ask *what would make this move wrong*; that answer is the gate. Also settle the gate's **kind** from the contract's vocabulary rather than letting it default silently: the two the stamp can scaffold are a condition computed over reality, and the presence of an authorisation artifact (someone's recorded approval). "The reviewer has approved it" is the second, not the first — a distinction easy to lose. The gate's *logic* is a predicate (teeth); here you declare which transitions have one and of what kind.
- **Invariants** (COR-035) — something that must stay true regardless of position, evaluated and surfaced rather than enforced. Ask what would mean "this subject is in a bad state no matter where it is".
- **Waits** (COR-034) — if the author describes waiting as a *place* ("it sits in pending"), check whether it is really a state or a wait: a wait is orthogonal to position and clears when its condition holds. Settle **why** it waits from the contract's reason vocabulary (awaiting a human, awaiting a condition, awaiting an inner process's outcome, awaiting an aggregate outcome), and note that awaiting-a-condition **requires** a resume condition — that condition is a predicate, so it becomes another stub — while awaiting-a-human must not have one. A wait is declarable on a fresh definition; adding one to an existing definition is a deferred operation.

### 5. Confirm before stamping

Read the shape back in the author's own vocabulary — states, movements, what is gated, what waits — and get an explicit yes. This is the cheapest moment to fix a wrong shape: the stamp is one-shot per process id, so a wrong shape means a manual cleanup rather than a re-run.

## Stamp it

Invoke `pkit process new` with the settled shape. Use `--dry-run` first when the shape is large — it previews the definition and every stub without writing. The stamp validates the shape against the contract *before* writing, so a rejection here means the shape is wrong, not the file.

The command writes the definition, one fail-closed stub per declared evaluable, and each stub's registration in the owning capability's package. Surface its output verbatim — the stub list is what the author's next phase works through.

## Hand the teeth over

Say plainly what now exists and what does not: the shape is declared and the process is addressable, but **every predicate is an unimplemented stub, so the process reads as entirely unreadable until they are written**. That is deliberate, not a defect — a stub that reported "true" would invent a position the process cannot actually detect.

The stub list is the next phase's worklist, in this order: detection predicates first (nothing else can be trusted until a position can be read), then gates, entry guards, wait conditions, and invariant checks. This is the teeth half — destined for the `process-author` agent, which has not shipped; until it does, implement each stub against the predicate-runner contract in `.pkit/process/README.md`, deleting each stub marker as you go.

## Wrap up

- `pkit process status` against a subject shows what the definition can currently read. Expect indeterminacy while stubs remain — that is the honest answer, not a failure.
- Commit per COR-008: the definition, the stubs, and the package registration are one logical unit.
- Declare the surface change if the project's versioning policy requires it; a new process is a surface an adopter can depend on.
