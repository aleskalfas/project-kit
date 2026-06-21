"""The process substrate engine (COR-031, homed in the binary per ADR-020).

Content-free state machine: it loads a `<capability>:<process-id>` definition,
resolves the subject's position from observable reality, validates/executes
moves through guarded transitions, and renders a self-explaining status view.
It knows nothing about issues, docs, screens, or trips — only states,
transitions, gates, a position, and a journal.

Ship-narrow (COR-031 P5): singleton subject, `inferred` detection, static
transition targets. The deferred extension points (keyed cardinality, stored /
hybrid detection, hooks, invariants, breadth, resolver / open-region targets,
composition) are not implemented here; the shape contract's enums already
reject their values, so an unrecognised value fails closed.

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

# Singleton subject key (COR-031 P5: ship-narrow, one journey per process).
# A keyed cardinality would carry the real subject id here; until that ships,
# every singleton process tracks one journey under this fixed key.
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

    Caching is per-invocation per `(command, args)` (COR-031 performance note):
    a predicate is evaluated at most once even when several transitions share
    it. The cache is keyed before the gate-kind interpretation, so the same
    command reused as a detection predicate and a gate predicate runs once;
    each caller applies its own interpretation to the raw payload.
    """

    capability: str
    capability_dir: Path
    repo_root: Path
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
                                 (cross-authority is non-overridable, COR-031 P4).

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
        argv = [str(script), SINGLETON_SUBJECT, "--json"]
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
    A predicate's `run:` must name one of these (COR-031 engine contract).
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
class MoveResult:
    """The outcome of an attempted move."""

    ok: bool
    reason: str
    journal_entry: dict[str, Any] | None = None


class ProcessEngine:
    """Resolves position, validates + executes moves, renders status for one
    process definition + subject. Stateless across invocations (COR-031): every
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
        """Live-precheck every transition out of the current state (COR-031
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
        return MoveResult(ok=True, reason=reason, journal_entry=entry)

    # --- journal ---------------------------------------------------------

    def journal_path(self) -> Path:
        """The per-subject journal at the capability's adopter-owned project/
        subtree (COR-031 layout; the engine owns the path)."""
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

    Resolves the capability's own instance schema at
    `.pkit/capabilities/<capability>/schemas/<process-id>.yaml` (COR-031
    binding layout), confirming its `process.id` matches the address.
    """
    capability, process_id = parse_address(address)
    capability_dir = repo_root / ".pkit" / "capabilities" / capability
    if not capability_dir.is_dir():
        raise ProcessError(f"capability {capability!r} is not installed at {capability_dir}")
    definition_path = capability_dir / "schemas" / f"{process_id}.yaml"
    if not definition_path.is_file():
        raise ProcessError(
            f"no process definition for {address!r} at "
            f"{definition_path.relative_to(repo_root)}"
        )
    try:
        raw = _yaml.load(definition_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProcessError(f"could not read process definition {definition_path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("process"), dict):
        raise ProcessError(
            f"{definition_path.relative_to(repo_root)} has no top-level `process:` block"
        )
    process = raw["process"]
    declared_id = process.get("id")
    if declared_id != process_id:
        raise ProcessError(
            f"process id mismatch: address {address!r} but definition declares "
            f"id {declared_id!r}"
        )
    return ProcessDefinition(
        capability=capability,
        process_id=process_id,
        capability_dir=capability_dir,
        data=process,
    )


def resolve_repo_root() -> Path:
    """The repo root, reusing the kit's root resolution (COR-031 engine
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

    # Legal moves with live prechecks.
    lines.append("")
    lines.append("  " + cli_render.style("heading", "Legal moves (live precheck):"))
    checks = engine.precheck_transitions(position.state_id, actor)
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
            }
            for c in checks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
