"""The process substrate engine (COR-033, homed in the binary per ADR-020).

Content-free state machine: it loads a `<capability>:<process-id>` definition,
resolves the subject's position from observable reality, validates/executes
moves through guarded transitions, and renders a self-explaining status view.
It knows nothing about issues, docs, screens, or trips — only states,
transitions, gates, a position, and a journal.

Ship-narrow (COR-033 P5 + COR-032): singleton or keyed subject, `inferred`
detection, static transition targets. A keyed process operates per a supplied
subject identifier (required — no singleton default) and never enumerates its
subjects; the engine simply threads that identifier through every predicate it
runs and through the per-subject journal path. The remaining deferred extension
points (stored / hybrid detection, hooks, breadth, resolver / open-region
targets, composition, cross-subject enumeration/cascade) are not implemented
here; the shape contract's enums already reject their values, so an
unrecognised value fails closed.

Invariants (COR-035): a process may declare position-independent always-checks
(`invariants: [{id, check, why}]`). The engine runs each `check` through the
SAME predicate runner that backs detection and gates (single-subject, threaded
with the subject id) and REPORTS the result — content-free, read-only, never
across subjects. A violation is surfaced on the status view AND reported by the
dedicated `validate` operation (report-only: it does not block moves or
remediate). An indeterminate check is fail-closed (reported as not holding).
NO subset-scoping / severity — both deferred (they un-defer with composition's
open region, which needs them boundary-enforcing).

Blocked (COR-034): a subject may declare a first-class `blocked` wait
(`blocked_on` ∈ {awaiting-human, awaiting-condition}, optional `assignee`) and
a `user` move may carry a `prompt`. The engine derives whether the subject is
*currently* blocked LIVE, and **resume differs by reason**:

- **awaiting-human** carries NO `resume_when`. It is blocked while the human is
  the SOLE way forward: the subject sits at a non-terminal position with an
  outgoing, not-yet-taken `user` move (gate-open or gate-closed alike) AND no
  currently-allowed autonomous (`agent-autonomous` / `script`) move the engine
  could take on its own instead. A gate-open autonomous move IS an escape (the
  engine can advance without a person -> not awaiting one); a gate-closed
  autonomous move is NOT. The resume is the person TAKING the user move
  (position advancing off the parked state). The engine consults no
  side-predicate — a satisfied side-fact while the move is still gate-closed
  must NOT report "not waiting".
- **awaiting-condition** carries a `resume_when` predicate. It is blocked while
  it has no legal move AND `resume_when` does not yet hold; the engine
  re-evaluates `resume_when` live and auto-clears when it holds (no human in
  the loop).

The flag is a derived overlay recomputed every call, never stored truth; the
enter/resume events are journal entries (no separate emission channel), written
only on the writing paths (`move` / `reconcile_blocked`) so the read-only
status view stays side-effect-free. A `move` reconciles the wait against the
TARGET state it just declared, so a park journals `blocked-enter` at park time.
Live evaluation is authoritative over any journal entry. Both shipped reasons
resolve from one subject's reality; the cross-subject reasons and the
hooks/selection slots stay deferred per COR-034.

Scope notes for this slice:

- *Multi-prompt-per-state is out of scope.* `_current_prompt` surfaces the
  FIRST outgoing `user` move's prompt; a state with two prompted `user` moves
  surfaces only one. Carrying several questions per state is a later slice.
- *`awaiting-condition` parks via `move` (with `assume_state`) are out of
  scope.* `reconcile_blocked(assume_state=...)` is exercised only for
  `awaiting-human` parks, where the outgoing `user` move is definitional of the
  target state, so the synthetic Position is sound. An `awaiting-condition`
  block's liveness depends on `has_no_legal_move` AND the live `resume_when`
  predicate against current reality — a combination only meaningful once the
  subject has actually settled into the parked state. So an `awaiting-condition`
  wait is reconciled ON DEMAND (the self-clear path: `reconcile_blocked` with NO
  `assume_state`, deriving from freshly-resolved reality), never at move time.
  No shipped process parks a subject into an `awaiting-condition` wait via a
  `move`; this engine does not support that combination.

The engine is invoked only as `pkit process …` (ADR-020): a backbone CLI
surface, never imported by a capability wrapper. Wrappers call it by
subprocess. Predicate commands the engine runs are themselves resolved through
the owning capability's `package.yaml` command registry and invoked as plain
subprocesses (explicit argv) — never a shell string.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import cli_render
from project_kit.install import find_target_root

_yaml = YAML(typ="safe")

# Singleton subject key (COR-033 P5: ship-narrow, one journey per process).
# A singleton process has no subject id, so every singleton journey tracks under
# this fixed key. A keyed process (COR-032) carries the real, caller-supplied
# subject id instead — threaded through the predicate runner and the journal
# path — and never defaults to this key.
SINGLETON_SUBJECT = "_"

# Predicate subprocess timeout. A predicate that overruns is indeterminate
# (fail-closed), exactly like an error or unparseable output.
_PREDICATE_TIMEOUT_SECONDS = 30


class ProcessError(Exception):
    """A user-facing engine error (bad address, unknown state, unreadable
    definition). Raised for conditions the operator must fix — distinct from a
    predicate that merely fails to evaluate (which is fail-closed, not an
    error)."""


# --- predicate evaluation -------------------------------------------------


@dataclass(frozen=True)
class PredicateOutcome:
    """The engine's verdict on one predicate evaluation.

    `result` is the boolean the engine acts on. For a deterministic check that
    is the predicate's own `result`; for an authorisation-artifact gate the
    engine computes it as `exists and produced_by != actor` and ignores any
    `result` the predicate supplied (cross-authority is non-overridable).

    `indeterminate` is the fail-closed flag: the predicate errored, timed out,
    returned unparseable JSON, or could not be resolved. When set, `result` is
    False and `reason` explains why it could not be evaluated.
    """

    result: bool
    reason: str
    indeterminate: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class PredicateRunner:
    """Resolves + runs a capability's predicate commands, caching each result.

    Caching is per-invocation per `(command, args)` (COR-033 performance note):
    a predicate is evaluated at most once even when several transitions share
    it. The cache is keyed before the gate-kind interpretation, so the same
    command reused as a detection predicate and a gate predicate runs once;
    each caller applies its own interpretation to the raw payload.
    """

    capability: str
    capability_dir: Path
    repo_root: Path
    subject: str
    _command_registry: dict[str, Path] = field(default_factory=dict)
    _raw_cache: dict[tuple[str, tuple[tuple[str, Any], ...]], dict[str, Any] | None] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self._command_registry = _load_command_registry(self.capability_dir)

    def evaluate_detection(self, predicate: dict[str, Any]) -> PredicateOutcome:
        """Run a detection predicate; the position is the state whose detection
        returns result=True. Uses the predicate's own `result`."""
        payload = self._run(predicate)
        if payload is None:
            return PredicateOutcome(
                result=False,
                reason=f"couldn't evaluate detection predicate {predicate.get('run')!r}",
                indeterminate=True,
            )
        result = bool(payload.get("result", False))
        reason = str(payload.get("reason", ""))
        return PredicateOutcome(result=result, reason=reason, detail=dict(payload))

    def evaluate_gate(self, gate: dict[str, Any], actor: str) -> PredicateOutcome:
        """Run a transition gate and interpret it per its `kind`.

        deterministic       -> uses the predicate's `result`.
        authorisation-artifact -> reads {exists, produced_by} and computes
                                 result = exists and produced_by != actor; any
                                 predicate-supplied `result` is ignored
                                 (cross-authority is non-overridable, COR-033 P4).

        An unrecognised gate kind fails closed (ADR-020 gate-honesty): never a
        silent pass.
        """
        kind = gate.get("kind")
        predicate = gate.get("predicate")
        if not isinstance(predicate, dict):
            return PredicateOutcome(
                result=False,
                reason="gate has no predicate to evaluate",
                indeterminate=True,
            )
        payload = self._run(predicate)
        if payload is None:
            return PredicateOutcome(
                result=False,
                reason=f"couldn't evaluate gate predicate {predicate.get('run')!r}",
                indeterminate=True,
            )

        if kind == "deterministic":
            return PredicateOutcome(
                result=bool(payload.get("result", False)),
                reason=str(payload.get("reason", "")),
                detail=dict(payload),
            )

        if kind == "authorisation-artifact":
            exists = bool(payload.get("exists", False))
            produced_by = payload.get("produced_by")
            result = exists and produced_by is not None and produced_by != actor
            if not exists:
                reason = "no authorisation artifact recorded"
            elif produced_by == actor:
                reason = (
                    f"authorisation artifact was produced by the actor being gated "
                    f"({actor!r}); cross-authority requires a different authority"
                )
            else:
                reason = f"authorised by {produced_by!r} (cross-authority)"
            return PredicateOutcome(result=result, reason=reason, detail=dict(payload))

        # Unrecognised / schema-future gate kind: fail closed (ADR-020).
        return PredicateOutcome(
            result=False,
            reason=f"unrecognised gate kind {kind!r}; failing closed (engine/definition skew)",
            indeterminate=True,
        )

    def _run(self, predicate: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve + run a predicate command, returning parsed JSON or None.

        None means indeterminate (unresolved name, non-zero exit, timeout, or
        unparseable JSON) — the caller maps that to a fail-closed outcome.
        """
        run_name = predicate.get("run")
        if not isinstance(run_name, str) or not run_name:
            return None
        with_args = predicate.get("with")
        cache_key = (run_name, _freeze(with_args))
        if cache_key in self._raw_cache:
            return self._raw_cache[cache_key]

        payload = self._invoke(run_name, with_args)
        self._raw_cache[cache_key] = payload
        return payload

    def _invoke(self, run_name: str, with_args: Any) -> dict[str, Any] | None:
        script = self._command_registry.get(run_name)
        if script is None:
            # Unregistered command: a self-explaining engine error, surfaced to
            # the operator — the definition references a command the capability
            # does not register. This is a definition bug, not a runtime
            # indeterminacy, so it is raised rather than treated fail-closed.
            registered = ", ".join(sorted(self._command_registry)) or "(none)"
            raise ProcessError(
                f"predicate command {run_name!r} is not registered in "
                f"{self.capability!r}'s package.yaml (registered: {registered})"
            )
        # COR-032: the engine threads the (singleton or keyed) subject id as the
        # first argv to every predicate, so a keyed predicate resolves the right
        # unit's reality. Singleton processes pass the fixed SINGLETON_SUBJECT.
        argv = [str(script), self.subject, "--json"]
        try:
            completed = subprocess.run(
                argv,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=_PREDICATE_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None
        try:
            parsed = json.loads(completed.stdout)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed


def _freeze(value: Any) -> tuple[tuple[str, Any], ...]:
    """Make a predicate's optional `with` mapping hashable for the cache key."""
    if not isinstance(value, dict):
        return ()
    return tuple(sorted((str(k), repr(v)) for k, v in value.items()))


def _load_command_registry(capability_dir: Path) -> dict[str, Path]:
    """Map each command a capability registers to its resolved script path.

    Walks the `commands:` tree in the capability's `package.yaml` (the same
    tree the dispatcher reads, COR-021) and records every leaf with a `script`.
    A predicate's `run:` must name one of these (COR-033 engine contract).
    """
    package_yaml = capability_dir / "package.yaml"
    if not package_yaml.is_file():
        return {}
    try:
        raw = _yaml.load(package_yaml.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    commands = raw.get("commands")
    if not isinstance(commands, dict):
        return {}
    registry: dict[str, Path] = {}
    _collect_command_scripts(commands, capability_dir, registry)
    return registry


def _collect_command_scripts(
    tree: dict[str, Any], capability_dir: Path, registry: dict[str, Path]
) -> None:
    """Recursively collect `{command_name: script_path}` from a commands tree."""
    for name, value in tree.items():
        if not isinstance(value, dict):
            continue
        script = value.get("script")
        if isinstance(script, str):
            registry[str(name)] = capability_dir / script
        else:
            _collect_command_scripts(value, capability_dir, registry)


# --- the process definition + engine --------------------------------------


@dataclass(frozen=True)
class ProcessDefinition:
    """A loaded, parsed process definition for one `<capability>:<id>`."""

    capability: str
    process_id: str
    capability_dir: Path
    data: dict[str, Any]

    @property
    def states(self) -> list[dict[str, Any]]:
        return [s for s in self.data.get("states", []) if isinstance(s, dict)]

    @property
    def transitions(self) -> list[dict[str, Any]]:
        return [t for t in self.data.get("transitions", []) if isinstance(t, dict)]

    @property
    def version(self) -> Any:
        return self.data.get("version")

    @property
    def cardinality(self) -> str:
        """The subject cardinality (`singleton` | `keyed`, COR-032).

        Defaults to `singleton` when the `subject` block omits it — the
        ship-narrow default and the shape the engine assumed before keyed.
        """
        subject = self.data.get("subject")
        if isinstance(subject, dict):
            value = subject.get("cardinality")
            if isinstance(value, str):
                return value
        return "singleton"

    @property
    def subject_key(self) -> str | None:
        """The descriptive `key` naming what identifies a keyed unit (COR-032),
        or None when unspecified. Engine does not interpret it; used only for
        clearer error messages."""
        subject = self.data.get("subject")
        if isinstance(subject, dict):
            value = subject.get("key")
            if isinstance(value, str) and value:
                return value
        return None

    @property
    def invariants(self) -> list[dict[str, Any]]:
        """The process's declared invariants (COR-035), or an empty list.

        Each is an `{id, check, why}`, holding process-wide. Additive — a
        definition declaring none returns `[]` and is byte-unchanged.
        """
        return [i for i in self.data.get("invariants", []) if isinstance(i, dict)]

    @property
    def blocked_declaration(self) -> dict[str, Any] | None:
        """The subject's optional `blocked` wait declaration (COR-034), or None.

        Authored on the `subject` block: `{blocked_on, resume_when?, assignee?}`
        — `resume_when` is required for `awaiting-condition` and forbidden for
        `awaiting-human` (the schema enforces this). Additive — a definition
        without it is byte-unchanged and never blocks.
        """
        subject = self.data.get("subject")
        if isinstance(subject, dict):
            blocked = subject.get("blocked")
            if isinstance(blocked, dict):
                return blocked
        return None

    def state(self, state_id: str) -> dict[str, Any] | None:
        for s in self.states:
            if s.get("id") == state_id:
                return s
        return None


@dataclass(frozen=True)
class TransitionCheck:
    """The live precheck of one transition out of the current state."""

    transition: dict[str, Any]
    outcome: PredicateOutcome
    has_gate: bool

    @property
    def to(self) -> str:
        return str(self.transition.get("to", ""))

    @property
    def trigger(self) -> str:
        return str(self.transition.get("trigger", ""))

    @property
    def prompt(self) -> str | None:
        """The question posed to a person on this move (COR-034), if authored.
        Surfaced on the status view; carried content-free (the engine never
        interprets it). Only a `user`-authorisation move carries one."""
        value = self.transition.get("prompt")
        return value if isinstance(value, str) and value else None

    @property
    def allowed(self) -> bool:
        return self.outcome.result

    @property
    def indeterminate(self) -> bool:
        return self.outcome.indeterminate


@dataclass(frozen=True)
class Position:
    """The resolved position of a subject.

    `state_id` is None when no state's detection predicate matched (the subject
    has no inferable position). `indeterminate` is True when at least one
    detection predicate could not be evaluated, so the position cannot be
    trusted — a fail-closed condition for `move`.
    """

    state_id: str | None
    indeterminate: bool
    detection_reasons: dict[str, PredicateOutcome] = field(default_factory=dict)


@dataclass(frozen=True)
class BlockedState:
    """The DERIVED, live blocked overlay on a subject (COR-034).

    NOT stored truth and NOT a definition state — it is recomputed from reality
    on every evaluation. Blocked-ness is derived per reason (COR-034 "Resume
    differs by reason"):

    - **awaiting-human** — live while the human is the SOLE way forward: the
      subject sits at a non-terminal position with an outgoing, not-yet-taken
      `user` move AND no currently-allowed autonomous (`agent-autonomous` /
      `script`) move the engine could take on its own instead. Whether the
      `user` move is currently gate-open (ready to take) or gate-closed (the
      human must intervene in reality first), it stays awaiting-human until
      taken. But if a gate-open autonomous move is available, the engine can
      advance without a person, so the subject is NOT awaiting one (a
      gate-closed autonomous move is not an escape — the engine cannot take
      it). The resume is the position advancing off the parked state — the
      engine consults **no** side-predicate (a `resume_when` is forbidden on
      this reason). Tying the resume to a side-predicate is wrong precisely
      because the two can disagree: a satisfied side-fact while the move is
      still gate-closed would falsely report "not waiting" on a subject that is
      genuinely stuck.

    - **awaiting-condition** — live while the subject has *no legal move* (the
      shipped 'no legal move' detection — a non-terminal position with no
      transition it can take on its own) AND its declared `resume_when`
      predicate does **not** yet hold; when `resume_when` holds the engine
      auto-clears the flag (this object is None). No human is in the loop.

    The live evaluation is authoritative over any journal entry (COR-033
    journal-is-intent-log). `since` and `assignee` are audit colour: `since`
    is read from the blocked-enter journal entry (the wait's age), `assignee`
    from the declaration. They never decide blocked-ness.
    """

    blocked_on: str
    at: str | None
    resume_reason: str
    since: str | None = None
    assignee: str | None = None
    prompt: str | None = None


@dataclass(frozen=True)
class MoveResult:
    """The outcome of an attempted move."""

    ok: bool
    reason: str
    journal_entry: dict[str, Any] | None = None


@dataclass(frozen=True)
class InvariantOutcome:
    """The engine's verdict on one invariant (COR-035).

    `holds` is the boolean the reader acts on: True when the invariant's `check`
    predicate returned result=True and was determinate. An indeterminate
    predicate (error / timeout / unparseable / unresolved) is **fail-closed** —
    `holds` is False (a check that could not be confirmed is treated as a
    violation, mirroring `resume_when`), and `indeterminate` flags that the
    failure was an evaluation failure rather than a confirmed False.

    `why` is the declaration's explanatory prose, surfaced on a violation.
    `reason` is the predicate's own reason (or the indeterminacy explanation).
    """

    invariant_id: str
    holds: bool
    why: str
    reason: str
    indeterminate: bool = False


class ProcessEngine:
    """Resolves position, validates + executes moves, renders status for one
    process definition + subject. Stateless across invocations (COR-033): every
    call rediscovers reality by running detection predicates live."""

    def __init__(
        self,
        definition: ProcessDefinition,
        repo_root: Path,
        subject: str = SINGLETON_SUBJECT,
    ) -> None:
        self.definition = definition
        self.repo_root = repo_root
        self.subject = subject
        self.runner = PredicateRunner(
            capability=definition.capability,
            capability_dir=definition.capability_dir,
            repo_root=repo_root,
            subject=subject,
        )

    @classmethod
    def for_subject(
        cls,
        definition: ProcessDefinition,
        repo_root: Path,
        subject: str | None,
    ) -> ProcessEngine:
        """Build an engine, resolving the subject per the definition's cardinality.

        singleton -> the supplied subject is ignored; the fixed SINGLETON_SUBJECT
        is used (one journey per process).
        keyed (COR-032) -> a subject is REQUIRED; absent it, raise a clear
        ProcessError (no singleton default for a keyed process).

        An unrecognised cardinality fails closed as a ProcessError rather than
        silently defaulting.
        """
        cardinality = definition.cardinality
        if cardinality == "keyed":
            if subject is None or subject == "":
                raise ProcessError(
                    f"process {definition.capability}:{definition.process_id} is keyed "
                    "(cardinality: keyed); --subject is required (it identifies which "
                    f"{definition.subject_key or 'unit'} to act on)."
                )
            return cls(definition, repo_root, subject=subject)
        if cardinality == "singleton":
            return cls(definition, repo_root, subject=SINGLETON_SUBJECT)
        raise ProcessError(
            f"process {definition.capability}:{definition.process_id} declares "
            f"unsupported subject cardinality {cardinality!r}; failing closed "
            "(expected 'singleton' or 'keyed')."
        )

    # --- position resolution ---------------------------------------------

    def resolve_position(self) -> Position:
        """Run each state's detection predicate; the position is the state whose
        predicate returns result=True. If any predicate is indeterminate and no
        state has yet matched, the position is indeterminate (fail-closed)."""
        reasons: dict[str, PredicateOutcome] = {}
        matched: str | None = None
        any_indeterminate = False
        for state in self.definition.states:
            state_id = str(state.get("id", ""))
            detection = state.get("detection")
            if not isinstance(detection, dict):
                continue
            if detection.get("mode") != "inferred":
                # Ship-narrow: only `inferred` is implemented. A future mode is
                # treated as indeterminate (fail-closed), never silently in-state.
                reasons[state_id] = PredicateOutcome(
                    result=False,
                    reason=f"detection mode {detection.get('mode')!r} not implemented "
                    "(ship-narrow)",
                    indeterminate=True,
                )
                any_indeterminate = True
                continue
            predicate = detection.get("predicate")
            if not isinstance(predicate, dict):
                continue
            outcome = self.runner.evaluate_detection(predicate)
            reasons[state_id] = outcome
            if outcome.indeterminate:
                any_indeterminate = True
            elif outcome.result and matched is None:
                matched = state_id
        if matched is not None:
            return Position(state_id=matched, indeterminate=False, detection_reasons=reasons)
        return Position(
            state_id=None, indeterminate=any_indeterminate, detection_reasons=reasons
        )

    # --- move prechecks --------------------------------------------------

    def transitions_from(self, state_id: str | None) -> list[dict[str, Any]]:
        """Transitions out of `state_id` — including `from: "*"` wildcards."""
        out: list[dict[str, Any]] = []
        for t in self.definition.transitions:
            origin = t.get("from")
            if origin == state_id or origin == "*":
                out.append(t)
        return out

    def precheck_transitions(self, state_id: str | None, actor: str) -> list[TransitionCheck]:
        """Live-precheck every transition out of the current state (COR-033
        performance note: only transitions *out of* the current state)."""
        checks: list[TransitionCheck] = []
        for t in self.transitions_from(state_id):
            gate = t.get("gate")
            if isinstance(gate, dict):
                outcome = self.runner.evaluate_gate(gate, actor)
                has_gate = True
            else:
                # No gate: the move is unconditionally allowed (the authorisation
                # token names WHO may move; the engine does not enforce that —
                # the caller does).
                outcome = PredicateOutcome(result=True, reason="no gate")
                has_gate = False
            checks.append(TransitionCheck(transition=t, outcome=outcome, has_gate=has_gate))
        return checks

    # --- blocked (the derived human-pause / wait overlay, COR-034) -------

    def has_no_legal_move(
        self, position: Position, checks: list[TransitionCheck]
    ) -> bool:
        """The shipped core 'no legal move' detection (COR-033, named by COR-034).

        True when the subject is parked: it has an inferred, non-terminal,
        determinate position out of which no transition is currently allowed.
        A terminal position is *done*, not stuck; an indeterminate or absent
        position is not a wait the engine can name (fail-closed elsewhere).
        """
        if position.indeterminate or position.state_id is None:
            return False
        state = self.definition.state(position.state_id) or {}
        if state.get("terminal"):
            return False
        return not any(check.allowed for check in checks)

    def has_pending_human_move(
        self, position: Position, checks: list[TransitionCheck]
    ) -> bool:
        """Whether the subject's *sole forward progress* is an untaken human
        move (COR-034 awaiting-human rule).

        Awaiting-human iff the human is the only way forward. Concretely, True
        when ALL of:

        (a) the position is inferred, determinate, and non-terminal;
        (b) there IS an outgoing `user`-authorisation move that has not yet
            been taken — whether its gate is currently open (ready to take) or
            closed (the human must intervene in reality first). A gate-closed
            `user` move still means the human is who must act, possibly after
            intervening, so it counts; and
        (c) there is NO currently-ALLOWED autonomous (`agent-autonomous` /
            `script`) move the engine could take on its own instead. "Allowed"
            here means gate-passing (or gateless): a gate-OPEN autonomous move
            is a real escape — the engine can advance without a person, so the
            subject is NOT awaiting one. A gate-CLOSED autonomous move is NOT an
            escape — the engine cannot take it, so it does not lift the wait.

        The subject stays awaiting-human until the `user` move is taken; the
        resume is the position advancing off this state, which removes the
        pending move. No side-predicate is consulted (COR-034: a `resume_when`
        is forbidden for awaiting-human precisely so the two can never disagree).
        The gate-state of the `user` move is deliberately NOT consulted in (b)
        for the same reason — only its presence-and-untaken-ness, plus the
        absence of an autonomous escape in (c), decides the wait.
        """
        if position.indeterminate or position.state_id is None:
            return False
        state = self.definition.state(position.state_id) or {}
        if state.get("terminal"):
            return False
        has_user_move = False
        has_autonomous_escape = False
        for check in checks:
            authorisation = check.transition.get("authorisation")
            if authorisation == "user":
                # Presence + untaken-ness only; gate-state is irrelevant here
                # (an untaken parked state still has the user move outgoing).
                has_user_move = True
            elif authorisation in ("agent-autonomous", "script") and check.allowed:
                # A gate-passing (or gateless) autonomous move the engine could
                # take on its own — the subject is not waiting on a person.
                has_autonomous_escape = True
        return has_user_move and not has_autonomous_escape

    def evaluate_blocked(
        self,
        position: Position,
        checks: list[TransitionCheck],
        actor: str,
    ) -> BlockedState | None:
        """Derive the subject's CURRENT blocked overlay LIVE (COR-034), or None.

        Recomputed from reality every call — never stored. Resume differs by
        reason (COR-034 "Resume differs by reason"):

        - **awaiting-human** — blocked while the subject is parked awaiting a
          person (`has_pending_human_move`): a non-terminal position with an
          outgoing, not-yet-taken `user` move AND no autonomous escape (a
          currently-allowed `agent-autonomous` / `script` move the engine could
          take instead). The resume is the move being taken (position advancing
          off the parked state); the engine consults **no** `resume_when`
          side-predicate. So a side-fact existing (e.g. a review file) does NOT
          clear the block — only taking the move (or an autonomous move becoming
          available) does.

        - **awaiting-condition** — blocked while the subject has no legal move
          (`has_no_legal_move`) AND its `resume_when` predicate does **not** yet
          hold. When `resume_when` holds the flag auto-clears (None); an
          indeterminate `resume_when` is fail-closed (treated as not-yet-holding
          — the subject stays blocked rather than silently resuming).

        `since` is read from the latest blocked-enter journal entry (the wait's
        age); it is audit colour and never decides blocked-ness. The wait's
        `prompt` (for an `awaiting-human` block) is the question on the current
        position's outgoing `user` move, surfaced here for convenience.
        """
        declaration = self.definition.blocked_declaration
        if declaration is None:
            return None

        blocked_on = str(declaration.get("blocked_on", ""))
        if blocked_on == "awaiting-human":
            # No side-predicate: blocked iff a pending human move sits ahead.
            if not self.has_pending_human_move(position, checks):
                return None
            resume_reason = "awaiting the person to take the pending move"
        elif blocked_on == "awaiting-condition":
            if not self.has_no_legal_move(position, checks):
                return None
            resume_when = declaration.get("resume_when")
            if not isinstance(resume_when, dict):
                # Schema requires resume_when for awaiting-condition; if a
                # malformed definition slips through, fail closed (stay blocked)
                # rather than silently resuming on a missing predicate.
                resume_reason = "resume_when missing; cannot evaluate self-clear"
            else:
                outcome = self.runner.evaluate_detection(resume_when)
                # resume_when holds (and is determinate) -> auto-clear.
                if outcome.result and not outcome.indeterminate:
                    return None
                resume_reason = outcome.reason or "resume condition not yet met"
        else:
            # An unrecognised / future reason: fail closed (no overlay) — the
            # schema enum already rejects these, so this is engine/definition
            # skew, not a wait the engine can name.
            return None

        assignee = declaration.get("assignee")
        return BlockedState(
            blocked_on=blocked_on,
            at=position.state_id,
            resume_reason=resume_reason,
            since=self._wait_since(),
            assignee=assignee if isinstance(assignee, str) and assignee else None,
            prompt=self._current_prompt(checks),
        )

    def _current_prompt(self, checks: list[TransitionCheck]) -> str | None:
        """The question (COR-034) on the current position's `user` move, if any.

        An `awaiting-human` wait poses its question on the move the person must
        take; surfaced on the per-move emission and lifted onto the blocked
        overlay for the human-pause view. Content-free passthrough. Returns the
        FIRST `user` move's prompt — multi-prompt-per-state is out of scope for
        this slice (see the module docstring's scope notes)."""
        for check in checks:
            if check.transition.get("authorisation") == "user" and check.prompt:
                return check.prompt
        return None

    def _wait_since(self) -> str | None:
        """The `ts` of the most recent blocked-enter event still open in the
        journal (the wait's age), or None. Audit colour only — read from the
        intent log, never authoritative over the live evaluation."""
        since: str | None = None
        for entry in self.read_journal():
            event = entry.get("event")
            if event == "blocked-enter":
                since = entry.get("ts") if isinstance(entry.get("ts"), str) else since
            elif event == "blocked-resume":
                since = None
        return since

    # --- invariants (the position-independent always-checks, COR-035) -----

    def evaluate_invariants(self) -> list[InvariantOutcome]:
        """Run each declared invariant's `check` and report whether it holds.

        Read-only and content-free (COR-035): the engine RUNS each `check`
        through the existing predicate runner — single-subject, threaded with
        the subject id — and REPORTS the result; it never interprets what the
        invariant means or acts on a violation beyond reporting. It never reads
        across subjects (COR-032).

        **Position-independent.** Invariants hold process-wide, so they are
        evaluated against current reality regardless of the subject's position
        — an indeterminate or absent position does not stop them being checked.
        (The position is reported alongside as context, not as a precondition.)

        **Fail-closed.** An invariant whose `check` is indeterminate (the
        predicate errored, timed out, returned unparseable JSON, or could not be
        resolved) is reported as NOT holding — a check that cannot be confirmed
        is treated as a violation, mirroring the blocked slot's `resume_when`
        handling rather than silently passing.

        Reuses the engine's `PredicateRunner` (and its per-invocation
        `(command, args)` cache), so an invariant sharing a command with a
        detection or gate predicate is evaluated at most once per invocation.
        """
        outcomes: list[InvariantOutcome] = []
        for invariant in self.definition.invariants:
            invariant_id = str(invariant.get("id", ""))
            why = str(invariant.get("why", ""))
            check = invariant.get("check")
            if not isinstance(check, dict):
                # Schema requires `check`; a malformed definition slipping
                # through is fail-closed (reported as not holding) rather than
                # silently passing.
                outcomes.append(
                    InvariantOutcome(
                        invariant_id=invariant_id,
                        holds=False,
                        why=why,
                        reason="invariant has no check predicate to evaluate",
                        indeterminate=True,
                    )
                )
                continue
            outcome = self.runner.evaluate_detection(check)
            outcomes.append(
                InvariantOutcome(
                    invariant_id=invariant_id,
                    # Fail-closed: an indeterminate check does NOT hold.
                    holds=outcome.result and not outcome.indeterminate,
                    why=why,
                    reason=outcome.reason,
                    indeterminate=outcome.indeterminate,
                )
            )
        return outcomes

    def can_move(self, to_state: str, actor: str) -> tuple[bool, str, Position]:
        """Validate a candidate move to `to_state`. Returns (allowed, reason,
        position). Refuses (fail-closed) on an indeterminate position, an
        unknown target, no matching transition, or a gate that does not pass."""
        position = self.resolve_position()
        if self.definition.state(to_state) is None:
            return False, f"unknown target state {to_state!r}", position
        if position.indeterminate:
            return (
                False,
                "position is indeterminate — a detection predicate could not be "
                "evaluated; refusing to move (fail-closed)",
                position,
            )
        candidates = [
            c for c in self.precheck_transitions(position.state_id, actor) if c.to == to_state
        ]
        if not candidates:
            origin = position.state_id or "(no position)"
            return (
                False,
                f"no transition from {origin!r} to {to_state!r}",
                position,
            )
        for check in candidates:
            if check.allowed:
                return True, f"move to {to_state!r} permitted: {check.outcome.reason}", position
        # All matching transitions refused; surface the first reason.
        first = candidates[0]
        return False, f"gate refused: {first.outcome.reason}", position

    def move(self, to_state: str, actor: str) -> MoveResult:
        """Execute a legal move: validate, then append a journal entry. Refuses
        (no journal write) when `can_move` refuses."""
        allowed, reason, position = self.can_move(to_state, actor)
        if not allowed:
            return MoveResult(ok=False, reason=reason)

        check = next(
            c
            for c in self.precheck_transitions(position.state_id, actor)
            if c.to == to_state and c.allowed
        )
        entry = self._build_journal_entry(
            from_state=position.state_id,
            to_state=to_state,
            check=check,
            actor=actor,
        )
        _validate_journal_entry(entry, self.definition)
        self._append_journal(entry)
        # The move lands the subject at `to_state`; journal the blocked
        # enter/resume that position implies AT PARK TIME (COR-034 G2), so a
        # parked awaiting-human wait records its `blocked-enter` now — making
        # `since` meaningful — rather than lazily, only once the human finally
        # acts. We reconcile against the TARGET state the move just declared,
        # not freshly-resolved reality: the domain side-effect detection reads
        # is applied by the wrapper around this call, so reality may still show
        # the source state at this instant. The enter/resume EVENTS are journal
        # entries themselves — there is no separate emission channel.
        self.reconcile_blocked(actor, assume_state=to_state)
        return MoveResult(ok=True, reason=reason, journal_entry=entry)

    def reconcile_blocked(
        self, actor: str, assume_state: str | None = None
    ) -> dict[str, Any] | None:
        """Bring the journal's wait audit in line with the live blocked overlay
        (COR-034), appending a `blocked-enter` or `blocked-resume` entry when
        the live state crossed the journal's last-recorded wait state. Returns
        the entry it appended, or None when nothing changed.

        This is the journaling seam for the wait: it runs on the `move` path
        (so a move into a parked position journals the enter AT PARK TIME, and
        a move that clears it journals the resume), and is exposed so a binding
        can also reconcile a SELF-clearing `awaiting-condition` wait (whose
        resume needs no human move) on demand. It is the only blocked path that
        WRITES — `evaluate_blocked` (used by the read-only status view) never
        does, so `status` stays side-effect-free (COR-033: status runs
        predicates live and must be read-only).

        `assume_state` lets the `move` path reconcile against the TARGET state
        the move just declared, rather than freshly-resolved reality — the
        domain side-effect detection reads is applied by the wrapper around the
        move, so reality may still show the source state at the instant the
        move journals. With no `assume_state`, blocked-ness is derived from live
        reality (the on-demand `awaiting-condition` self-clear path).

        The journal is the intent log; the CURRENT blocked-ness is always the
        live `evaluate_blocked`, authoritative over what is journaled here.
        """
        if assume_state is not None:
            # Reconcile as if the subject is AT the move's target (G2): build a
            # synthetic, determinate position for it and precheck its outgoing
            # transitions. This journals a parked awaiting-human wait's enter at
            # park time, even before the wrapper applies the domain side-effect.
            position = Position(state_id=assume_state, indeterminate=False)
        else:
            position = self.resolve_position()
        checks = self.precheck_transitions(position.state_id, actor)
        live = self.evaluate_blocked(position, checks, actor)
        was_blocked = self._journal_says_blocked()

        if live is not None and not was_blocked:
            entry = self._build_wait_entry("blocked-enter", live)
        elif live is None and was_blocked:
            # Resume: report the wait we are leaving (its reason/at from the
            # open enter entry), not a fresh derivation (the live overlay is
            # already None).
            entry = self._build_resume_entry()
        else:
            return None
        _validate_journal_entry(entry, self.definition)
        self._append_journal(entry)
        return entry

    def _journal_says_blocked(self) -> bool:
        """Whether the journal's last wait event left the subject blocked — i.e.
        a `blocked-enter` not yet followed by a `blocked-resume`. This is the
        audit trail's view, used only to decide whether a NEW enter/resume entry
        is owed; it is never authoritative over the live evaluation."""
        open_wait = False
        for entry in self.read_journal():
            event = entry.get("event")
            if event == "blocked-enter":
                open_wait = True
            elif event == "blocked-resume":
                open_wait = False
        return open_wait

    def _build_wait_entry(self, event: str, blocked: BlockedState) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "subject": self.subject,
            "event": event,
            "blocked_on": blocked.blocked_on,
        }
        if blocked.at is not None:
            entry["at"] = blocked.at
        if blocked.assignee is not None:
            entry["assignee"] = blocked.assignee
        return entry

    def _build_resume_entry(self) -> dict[str, Any]:
        """Build a `blocked-resume` entry, carrying forward the reason/position
        of the open `blocked-enter` it closes (audit colour for the resolved
        wait)."""
        entry: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "subject": self.subject,
            "event": "blocked-resume",
        }
        last_enter: dict[str, Any] | None = None
        for j in self.read_journal():
            if j.get("event") == "blocked-enter":
                last_enter = j
            elif j.get("event") == "blocked-resume":
                last_enter = None
        if last_enter is not None:
            if isinstance(last_enter.get("blocked_on"), str):
                entry["blocked_on"] = last_enter["blocked_on"]
            if isinstance(last_enter.get("at"), str):
                entry["at"] = last_enter["at"]
            if isinstance(last_enter.get("assignee"), str):
                entry["assignee"] = last_enter["assignee"]
        return entry

    # --- journal ---------------------------------------------------------

    def journal_path(self) -> Path:
        """The per-subject journal at the capability's adopter-owned project/
        subtree (COR-033 layout; the engine owns the path)."""
        return (
            self.definition.capability_dir
            / "project"
            / "process"
            / self.definition.process_id
            / f"{self.subject}.journal.jsonl"
        )

    def read_journal(self) -> list[dict[str, Any]]:
        """Read the append-only journal, oldest first. Skips unparseable lines
        rather than failing — the journal is an audit trail, best-effort to read
        for the status view."""
        path = self.journal_path()
        if not path.is_file():
            return []
        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(parsed, dict):
                entries.append(parsed)
        return entries

    def _build_journal_entry(
        self,
        from_state: str | None,
        to_state: str,
        check: TransitionCheck,
        actor: str,
    ) -> dict[str, Any]:
        transition = check.transition
        entry: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "subject": self.subject,
            "to": to_state,
            "trigger": str(transition.get("trigger", "")),
            "actor": actor,
        }
        if from_state is not None:
            entry["from"] = from_state
        if check.has_gate:
            entry["gate_result"] = "pass" if check.allowed else "fail"
        severity = transition.get("severity")
        if isinstance(severity, str):
            entry["severity"] = severity
        return entry

    def _append_journal(self, entry: dict[str, Any]) -> None:
        path = self.journal_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")


# --- loading --------------------------------------------------------------


def parse_address(address: str) -> tuple[str, str]:
    """Split a `<capability>:<process-id>` address. Raises ProcessError on a
    malformed address."""
    if address.count(":") != 1:
        raise ProcessError(
            f"malformed process address {address!r}; expected <capability>:<process-id>"
        )
    capability, process_id = address.split(":", 1)
    if not capability or not process_id:
        raise ProcessError(
            f"malformed process address {address!r}; expected <capability>:<process-id>"
        )
    return capability, process_id


def load_definition(repo_root: Path, address: str) -> ProcessDefinition:
    """Load the process definition addressed by `<capability>:<process-id>`.

    Resolution order in the capability's `schemas/` directory:

    1. The README-convention path `<process-id>.yaml` (the common case — file
       stem == process id).
    2. Failing that, a scan of `schemas/*.yaml` for a top-level `process:`
       block whose `id` matches `<process-id>`. This accommodates a capability
       whose instance file predates the convention and keeps its historical
       name (e.g. project-management's `workflow.yaml` holding
       `process.id: issue-lifecycle`).

    The declared `process.id` must match the address either way.
    """
    capability, process_id = parse_address(address)
    capability_dir = repo_root / ".pkit" / "capabilities" / capability
    if not capability_dir.is_dir():
        raise ProcessError(f"capability {capability!r} is not installed at {capability_dir}")
    schemas_dir = capability_dir / "schemas"

    by_convention = schemas_dir / f"{process_id}.yaml"
    if by_convention.is_file():
        process = _read_process_block(by_convention, repo_root)
        if process.get("id") != process_id:
            raise ProcessError(
                f"process id mismatch: address {address!r} but definition at "
                f"{by_convention.relative_to(repo_root)} declares id {process.get('id')!r}"
            )
        return ProcessDefinition(
            capability=capability,
            process_id=process_id,
            capability_dir=capability_dir,
            data=process,
        )

    # Fall back to a scan: find the schema file whose process.id matches.
    # Collect ALL matches: two files claiming one id is a definition bug, not
    # something to resolve silently by sort order.
    if schemas_dir.is_dir():
        matches: list[tuple[Path, dict[str, Any]]] = []
        for candidate in sorted(schemas_dir.glob("*.yaml")):
            try:
                raw = _yaml.load(candidate.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            block = raw.get("process")
            if isinstance(block, dict) and block.get("id") == process_id:
                matches.append((candidate, block))
        if len(matches) > 1:
            offenders = ", ".join(
                str(path.relative_to(repo_root)) for path, _ in matches
            )
            raise ProcessError(
                f"ambiguous process definition for {address!r}: multiple schema "
                f"files declare process.id {process_id!r} ({offenders}). Exactly "
                f"one definition may claim an id."
            )
        if matches:
            return ProcessDefinition(
                capability=capability,
                process_id=process_id,
                capability_dir=capability_dir,
                data=matches[0][1],
            )

    raise ProcessError(
        f"no process definition for {address!r}: neither "
        f"{by_convention.relative_to(repo_root)} exists nor does any schema in "
        f"{schemas_dir.relative_to(repo_root)} declare process.id {process_id!r}"
    )


def _read_process_block(path: Path, repo_root: Path) -> dict[str, Any]:
    """Read and return a schema file's top-level `process:` block, or raise."""
    try:
        raw = _yaml.load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProcessError(f"could not read process definition {path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("process"), dict):
        raise ProcessError(
            f"{path.relative_to(repo_root)} has no top-level `process:` block"
        )
    return raw["process"]


def resolve_repo_root() -> Path:
    """The repo root, reusing the kit's root resolution (COR-033 engine
    contract: predicates run with cwd = repo root)."""
    root = find_target_root()
    if root is None:
        raise ProcessError("not in a project tree.")
    return root


# --- journal-entry schema validation --------------------------------------


def _journal_entry_schema(pkit_dir: Path) -> dict[str, Any]:
    """Load the `journal_entry` $def from the shape contract, as a standalone
    schema (its `$ref`s, if any, resolve within the same $defs block)."""
    schema_path = pkit_dir / "schemas" / "_defs" / "process.schema.json"
    full = json.loads(schema_path.read_text(encoding="utf-8"))
    defs = full.get("$defs", {})
    entry_schema = dict(defs.get("journal_entry", {}))
    # Carry the sibling $defs so any internal $ref still resolves.
    entry_schema["$defs"] = defs
    return entry_schema


def _validate_journal_entry(entry: dict[str, Any], definition: ProcessDefinition) -> None:
    """Validate a journal entry against the shape contract before writing.

    Raises ProcessError on a schema violation — the engine must not write a
    malformed audit record.
    """
    # capability_dir is <pkit>/capabilities/<name>; parents[1] is the .pkit dir.
    pkit_dir = definition.capability_dir.parents[1]
    try:
        schema = _journal_entry_schema(pkit_dir)
    except (OSError, json.JSONDecodeError):
        # Schema unreadable: skip validation rather than blocking the move. The
        # entry shape is engine-controlled, so this is a soft floor, not a gate.
        return
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(entry), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        raise ProcessError(
            f"journal entry failed shape validation: {first.message}"
        )


# --- rendering ------------------------------------------------------------


def render_status_narrative(engine: ProcessEngine, actor: str) -> str:
    """Human narrative: where · why · how it got here · legal moves with live
    prechecks · next hint."""
    definition = engine.definition
    position = engine.resolve_position()
    lines: list[str] = []
    lines.append(
        cli_render.style(
            "title", f"Process {definition.capability}:{definition.process_id}"
        )
        + f"  (subject {engine.subject!r}, definition v{definition.version})"
    )
    lines.append("")

    # Where + why.
    if position.indeterminate and position.state_id is None:
        lines.append("  " + cli_render.style("strong", "Where: indeterminate"))
        for state_id, outcome in position.detection_reasons.items():
            if outcome.indeterminate:
                lines.append(f"    couldn't evaluate {state_id!r}: {outcome.reason}")
    elif position.state_id is None:
        lines.append("  " + cli_render.style("strong", "Where: no position"))
        lines.append("    no state's detection predicate matched current reality")
    else:
        state = definition.state(position.state_id) or {}
        lines.append(
            "  " + cli_render.style("strong", f"Where: {position.state_id}")
            + (f" — {state.get('meaning')}" if state.get("meaning") else "")
        )
        if state.get("terminal"):
            lines.append("    (terminal state)")

    # How it got here (journal).
    journal = engine.read_journal()
    lines.append("")
    lines.append("  " + cli_render.style("heading", "How it got here:"))
    if not journal:
        lines.append("    (no recorded moves)")
    else:
        for entry in journal:
            frm = entry.get("from", "·")
            lines.append(
                f"    {entry.get('ts', '')}  {frm} -> {entry.get('to')}  "
                f"[{entry.get('trigger')}] by {entry.get('actor')}"
            )

    # Invariants (COR-035) — surface VIOLATIONS on every status read (the
    # load-bearing half: an agent reading status sees a violation each read).
    # Only failures are shown here, to keep status terse; `validate` reports
    # the full set. A violation that could not be confirmed (indeterminate
    # check) is fail-closed and surfaced distinctly.
    violations = [inv for inv in engine.evaluate_invariants() if not inv.holds]
    if violations:
        lines.append("")
        lines.append("  " + cli_render.style("strong", "Invariant violations:"))
        for inv in violations:
            marker = "?" if inv.indeterminate else "✗"
            lines.append(f"    {marker} {inv.invariant_id}" + (f" — {inv.why}" if inv.why else ""))
            lines.append(f"        {inv.reason}")

    # Blocked overlay (COR-034) — the derived, live wait, if any.
    checks = engine.precheck_transitions(position.state_id, actor)
    blocked = engine.evaluate_blocked(position, checks, actor)
    if blocked is not None:
        lines.append("")
        lines.append(
            "  " + cli_render.style("strong", f"Blocked: {blocked.blocked_on}")
        )
        lines.append(f"        resume when: {blocked.resume_reason}")
        if blocked.since:
            lines.append(f"        since: {blocked.since}")
        if blocked.assignee:
            lines.append(f"        owner: {blocked.assignee}")
        if blocked.prompt:
            lines.append("        " + cli_render.style("strong", f"❓ {blocked.prompt}"))

    # Legal moves with live prechecks.
    lines.append("")
    lines.append("  " + cli_render.style("heading", "Legal moves (live precheck):"))
    if not checks:
        lines.append("    (none)")
    else:
        for check in checks:
            if check.indeterminate:
                marker = "?"
            elif check.allowed:
                marker = "✓"
            else:
                marker = "✗"
            line = f"    {marker} {check.to}  [{check.trigger}]"
            why = check.transition.get("why")
            if why:
                line += f" — {why}"
            lines.append(line)
            lines.append(f"        {check.outcome.reason}")
            # The question posed on this move (COR-034), if it carries one.
            if check.prompt:
                lines.append("        " + cli_render.style("strong", f"❓ {check.prompt}"))
            hint = check.transition.get("hint")
            if check.allowed and hint:
                lines.append("        next: " + cli_render.style("command", str(hint)))

    return "\n".join(lines) + "\n"


def render_status_json(engine: ProcessEngine, actor: str) -> str:
    """Structured status for an agent / machine consumer."""
    definition = engine.definition
    position = engine.resolve_position()
    checks = engine.precheck_transitions(position.state_id, actor)
    state = definition.state(position.state_id) if position.state_id else None
    blocked = engine.evaluate_blocked(position, checks, actor)

    payload: dict[str, Any] = {
        "process": f"{definition.capability}:{definition.process_id}",
        "subject": engine.subject,
        "version": definition.version,
        "position": {
            "state": position.state_id,
            "indeterminate": position.indeterminate,
            "meaning": state.get("meaning") if state else None,
            "terminal": bool(state.get("terminal")) if state else None,
        },
        # COR-034: the DERIVED, live blocked overlay (None when not blocked).
        # Recomputed every call from reality — never read back as stored truth.
        "blocked": (
            None
            if blocked is None
            else {
                "blocked_on": blocked.blocked_on,
                "at": blocked.at,
                "resume_reason": blocked.resume_reason,
                "since": blocked.since,
                "assignee": blocked.assignee,
                "prompt": blocked.prompt,
            }
        ),
        # COR-035: the position-independent always-checks, evaluated live.
        # Always present (the full set, so an agent reads every invariant's
        # state); a violated invariant has holds=False and is the surfaced half.
        "invariants": [
            {
                "id": inv.invariant_id,
                "holds": inv.holds,
                "indeterminate": inv.indeterminate,
                "why": inv.why,
                "reason": inv.reason,
            }
            for inv in engine.evaluate_invariants()
        ],
        "journal": engine.read_journal(),
        "legal_moves": [
            {
                "to": c.to,
                "trigger": c.trigger,
                "allowed": c.allowed,
                "indeterminate": c.indeterminate,
                "reason": c.outcome.reason,
                "why": c.transition.get("why"),
                "hint": c.transition.get("hint"),
                # COR-034: the question on this move (None unless authored).
                "prompt": c.prompt,
            }
            for c in checks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_validate_narrative(engine: ProcessEngine) -> str:
    """Human narrative for the COR-035 `validate` operation: run the subject's
    invariants and report which hold and which are violated.

    Read-only — evaluating invariants writes nothing and does not affect
    position or move-legality."""
    definition = engine.definition
    outcomes = engine.evaluate_invariants()
    lines: list[str] = []
    lines.append(
        cli_render.style("title", f"Validate {definition.capability}:{definition.process_id}")
        + f"  (subject {engine.subject!r}, definition v{definition.version})"
    )
    lines.append("")
    if not outcomes:
        lines.append("  (no invariants declared)")
        return "\n".join(lines) + "\n"
    for inv in outcomes:
        if inv.holds:
            marker = "✓"
        elif inv.indeterminate:
            marker = "?"
        else:
            marker = "✗"
        lines.append(f"  {marker} {inv.invariant_id}" + (f" — {inv.why}" if inv.why else ""))
        lines.append(f"        {inv.reason}")
    violations = [inv for inv in outcomes if not inv.holds]
    lines.append("")
    if violations:
        lines.append(
            "  " + cli_render.style("strong", f"{len(violations)} invariant(s) violated")
        )
    else:
        lines.append("  " + cli_render.style("strong", "all invariants hold"))
    return "\n".join(lines) + "\n"


def render_validate_json(engine: ProcessEngine) -> str:
    """Structured `validate` result (COR-035) for an agent / machine consumer.

    Reports each invariant's `{id, holds, why, reason}` plus an `ok` summary
    (True iff every invariant holds). Read-only."""
    definition = engine.definition
    outcomes = engine.evaluate_invariants()
    payload: dict[str, Any] = {
        "process": f"{definition.capability}:{definition.process_id}",
        "subject": engine.subject,
        "version": definition.version,
        "ok": all(inv.holds for inv in outcomes),
        "invariants": [
            {
                "id": inv.invariant_id,
                "holds": inv.holds,
                "indeterminate": inv.indeterminate,
                "why": inv.why,
                "reason": inv.reason,
            }
            for inv in outcomes
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
