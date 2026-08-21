"""Deterministic authoring stamps for the process shape operations (COR-044).

COR-044 pairs each shipped shape operation with a deterministic command that
does the stamping (the COR-005 skill/command split — the composite skill owns
the disciplines and the walkthrough, this module owns the stamp):

- `stamp_new_process` — scaffold a lint-clean definition (subject incl.
  cardinality and, optionally, where its domain data lives, states with
  meanings, transitions, entry/terminal marks) into a NAMED owning capability,
  plus a predicate STUB for every evaluable the declared shape demands:
  detection predicates always; transition gates, entry guards, a `resume_when`,
  and invariant checks when declared. Stubs follow the predicate-runner
  contract (read-only, subject argv + `--json`, fail-closed — an unimplemented
  stub exits non-zero so it can never read as green) and register in the owning
  capability's `package.yaml` commands tree.
- `couple_process` — append a `depends_on` entry (COR-038) to the invoker-named
  definition: upstream address, relation + mode validated against the CLOSED
  substrate vocabularies READ AS DATA from the shape contract (never a
  hardcoded list — a new relation kind is an enum value this module picks up,
  never a code change), and the required `why`.
- `handoff_process` — add a COR-042 hand-off contract (trigger + the two seam
  predicates) to an EXISTING coupling, validating the trigger is a state of the
  upstream definition where that definition is resolvable at authoring time
  (unresolvable degrades to a warning — health reports it indeterminate), and
  scaffolding + registering the `candidates` / `resolve` seam stubs when the
  named commands are not yet registered.

Version semantics (COR-044 point 3): a `couple` or `hand-off` edit is additive
and inert or report-only, so the definition `version` field is NEVER bumped
here — state/transition evolution is the deferred `amend` operation's
territory, and only it carries the bump.

All three stamps require an owning capability that is REGISTERED as a manifest
component — the same set contract discovery walks — so a stamp can never write
a definition nothing watches (#713); see `_require_owned_address`. No routing
logic lives here beyond that refusal (COR-044: walking a capability-less
adopter through the capability-authoring path, or through `pkit capabilities
register`, is the skill's judgment, never the stamp's).

Mutations round-trip through `ruamel.yaml` (comments, key order, and quoting
preserved — the same discipline as `schemas_authoring`), lint the result
against the shape contract before leaving it on disk, and restore the prior
file on a lint failure so a partial mutation never lingers.
"""

from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit.process import (
    PREDICATE_STUB_MARKER,
    ProcessDefinition,
    ProcessError,
    _load_command_registry,
    load_definition,
    parse_address,
)
from project_kit.process_graph import installed_capabilities

_KEBAB_CASE = re.compile(r"^[a-z][a-z0-9-]*$")

# The shape contract — the single source the closed vocabularies are read from
# (COR-044: closed substrate vocabularies are read as data, never restated).
_SHAPE_CONTRACT_RELPATH = Path(".pkit") / "schemas" / "_defs" / "process.schema.json"


class ProcessAuthoringError(Exception):
    """Raised when a process-authoring stamp cannot apply cleanly."""


# --- the closed vocabularies, read as data ---------------------------------


def _load_shape_contract(repo_root: Path) -> dict[str, Any]:
    """The shape contract's parsed JSON, or a clean error when absent/broken.

    Never falls back to a built-in copy: the contract file IS the vocabulary
    source, and a silent fallback would let the two drift.
    """
    path = repo_root / _SHAPE_CONTRACT_RELPATH
    if not path.is_file():
        raise ProcessAuthoringError(
            f"shape contract not found at {_SHAPE_CONTRACT_RELPATH} — the "
            "process substrate's schema is synced content; run `pkit sync`."
        )
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProcessAuthoringError(
            f"shape contract at {_SHAPE_CONTRACT_RELPATH} could not be read: {exc}"
        ) from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("$defs"), dict):
        raise ProcessAuthoringError(
            f"shape contract at {_SHAPE_CONTRACT_RELPATH} has no `$defs` block."
        )
    return parsed


def _enum_from_contract(repo_root: Path, pointer: tuple[str, ...], label: str) -> list[str]:
    """One closed vocabulary from the shape contract, addressed by key path.

    `pointer` walks from `$defs` (e.g. `("depends_on", "properties",
    "relation", "enum")`). A missing/malformed enum is a clean error — the
    vocabulary is the contract's to declare, never this module's to invent.
    """
    node: Any = _load_shape_contract(repo_root)["$defs"]
    for key in pointer:
        if not isinstance(node, dict) or key not in node:
            raise ProcessAuthoringError(
                f"shape contract declares no {label} vocabulary at "
                f"$defs/{'/'.join(pointer)} — cannot validate against it."
            )
        node = node[key]
    if not isinstance(node, list) or not all(isinstance(v, str) for v in node):
        raise ProcessAuthoringError(
            f"shape contract's {label} vocabulary at $defs/{'/'.join(pointer)} "
            "is not a list of strings."
        )
    return list(node)


def relation_vocabulary(repo_root: Path) -> list[str]:
    """COR-038's closed relation set, read from the shape contract."""
    return _enum_from_contract(
        repo_root, ("depends_on", "properties", "relation", "enum"), "relation"
    )


def mode_vocabulary(repo_root: Path) -> list[str]:
    """The `depends_on` mode set (pull | push), read from the shape contract."""
    return _enum_from_contract(
        repo_root, ("depends_on", "properties", "mode", "enum"), "mode"
    )


def cardinality_vocabulary(repo_root: Path) -> list[str]:
    """The subject cardinality set (COR-032), read from the shape contract."""
    return _enum_from_contract(
        repo_root, ("subject", "properties", "cardinality", "enum"), "cardinality"
    )


def authorisation_vocabulary(repo_root: Path) -> list[str]:
    """The transition authorisation set, read from the shape contract."""
    return _enum_from_contract(
        repo_root, ("transition", "properties", "authorisation", "enum"), "authorisation"
    )


def blocked_on_vocabulary(repo_root: Path) -> list[str]:
    """The wait-reason set (COR-034), read from the shape contract."""
    return _enum_from_contract(
        repo_root, ("blocked", "properties", "blocked_on", "enum"), "blocked_on"
    )


def gate_kind_vocabulary(repo_root: Path) -> list[str]:
    """The gate kind set (COR-033 P4), read from the shape contract."""
    return _enum_from_contract(
        repo_root, ("gate", "properties", "kind", "enum"), "gate kind"
    )


# The two gate kinds whose check is a capability predicate the stamp can stub.
# This is a STRUCTURAL fact about the contract (these kinds carry `predicate`;
# `subprocess-outcome` / `cascade-outcome` are ENGINE-computed from the
# `subprocess` / `cascade` blocks, which are deferred `new` surface per
# COR-044's named-deferred block-kind operations) — not a rival vocabulary; the
# declared kind is still validated against the contract's enum first.
_PREDICATE_GATE_KINDS = ("deterministic", "authorisation-artifact")


# --- definition lint (the shape contract as the checker) --------------------


def lint_process_block(repo_root: Path, process: dict[str, Any]) -> list[str]:
    """Validate one `process:` block against the shape contract's `process`
    $def. Returns the error messages (empty = lint-clean).

    This is the same contract `schemas validate` treats as the external
    `$schema` of a definition instance; running it at stamp time is what makes
    "lint-clean by construction" checkable rather than asserted.
    """
    contract = _load_shape_contract(repo_root)
    schema = {"$ref": "#/$defs/process", "$defs": contract["$defs"]}
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(process), key=lambda e: list(e.path))
    return [
        f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}" for e in errors
    ]


def _lint_or_restore(repo_root: Path, path: Path, original: str, label: str) -> None:
    """Re-lint a just-written definition file; restore the prior bytes and
    raise when the result does not conform (a stamp must never leave a
    definition dirtier than it found it)."""
    yaml = YAML(typ="safe")
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"))
        block = raw.get("process") if isinstance(raw, dict) else None
        issues = (
            lint_process_block(repo_root, block)
            if isinstance(block, dict)
            else ["no top-level `process:` block after the edit"]
        )
    except Exception as exc:  # unparseable after the edit — same restore path
        issues = [f"definition unreadable after the edit: {exc}"]
    if issues:
        path.write_text(original, encoding="utf-8")
        raise ProcessAuthoringError(
            f"{label} left the definition non-conforming; restored the prior "
            "file. Lint: " + "; ".join(issues)
        )


def _lint_in_memory(repo_root: Path, data: Any, label: str) -> None:
    """The dry-run counterpart of `_lint_or_restore`: lint the MUTATED but
    unwritten round-trip tree, so a preview reports the same conformance
    verdict a real run would — without a write to undo. (ruamel's round-trip
    containers are dict/list subclasses and its scalars are str subclasses, so
    the JSON Schema validator reads them directly.)"""
    block = data.get("process") if isinstance(data, dict) else None
    issues = (
        lint_process_block(repo_root, block)
        if isinstance(block, dict)
        else ["no top-level `process:` block after the edit"]
    )
    if issues:
        raise ProcessAuthoringError(
            f"{label} would leave the definition non-conforming (nothing was "
            "written). Lint: " + "; ".join(issues)
        )


# --- predicate stubs (the predicate-runner contract, scaffolded) ------------

# Payload examples per stub purpose — the runner-contract shape the implemented
# predicate must print (COR-033 engine contract; ADR-048 for the seams).
_STUB_PAYLOADS = {
    "detection": '{"result": <bool>, "reason": "<why>"}',
    "gate": '{"result": <bool>, "reason": "<why>"}',
    "authorisation-artifact gate": '{"exists": <bool>, "produced_by": "<login>", "reason": "<why>"}',
    "entry guard": '{"result": <bool>, "reason": "<why>"}',
    "resume_when": '{"result": <bool>, "reason": "<why>"}',
    "invariant check": '{"result": <bool>, "reason": "<why>"}',
    "hand-off candidates": '{"candidates": ["<upstream-subject-id>", ...], "reason": "<why>"}',
    "hand-off resolve": '{"downstream": ["<downstream-subject-id>", ...], "reason": "<why>"}',
}

_STUB_TEMPLATE = '''#!/usr/bin/env python3
"""Predicate stub: {purpose} for {address}.

Scaffolded by `pkit process {operation}` (COR-044). Implementing it is the
process-author agent's territory — turn the owner's intent into a working
predicate over reality. The contract it must follow (COR-033 engine contract,
.pkit/process/README.md "The predicate runner"):

- READ-ONLY. `status` and `health` run predicates live; mutating here is a
  side-effect bug.
- argv: the subject slot first ({subject_note}), then `--json`;
  cwd is the repo root.
- print ONE JSON object to stdout: {payload}
- FAIL-CLOSED: an error / timeout / non-zero exit / unparseable payload is
  INDETERMINATE, never a pass.

Until implemented this stub EXITS NON-ZERO (indeterminate, fail-closed) so an
unwritten predicate can never read as green.

{marker} — DELETE this line once the predicate is
implemented. `pkit process health --interpretation-only` reads it statically to
tell "seam declared but never written" from "seam written and merely failing",
so a seam no subject currently exercises still reports honestly.
"""
import json
import sys

subject = sys.argv[1] if len(sys.argv) > 1 else ""

# TODO(process-author): implement this predicate over the owner's reality,
# print the contract payload above, and exit 0.
print(json.dumps({{
    "reason": "stub not implemented yet ({purpose} for {address})",
}}))
sys.exit(1)
'''


@dataclass(frozen=True)
class PredicateStub:
    """One scaffolded predicate stub: the registered command name, the script
    it resolves to, and what the predicate is for (the stub's own docs)."""

    command: str
    script_relpath: str  # relative to the capability dir (the package.yaml form)
    purpose: str


def _stub_body(
    purpose: str, address: str, operation: str, cardinality: str, payload_key: str
) -> str:
    subject_note = (
        "the fixed singleton sentinel"
        if cardinality == "singleton"
        else "the subject id"
    )
    if payload_key == "hand-off candidates":
        subject_note = "the contract's UPSTREAM PROCESS ADDRESS (the scope, ADR-048)"
    elif payload_key == "hand-off resolve":
        subject_note = "ONE upstream subject id (ADR-048)"
    return _STUB_TEMPLATE.format(
        purpose=purpose,
        address=address,
        operation=operation,
        subject_note=subject_note,
        payload=_STUB_PAYLOADS[payload_key],
        marker=PREDICATE_STUB_MARKER,
    )


def _round_trip_yaml() -> YAML:
    """The mutation-side YAML loader/dumper: round-trip mode (comments, key
    order, quoting preserved), house indent, no line-folding (a fold would
    rewrap prose the author laid out)."""
    rt = YAML(typ="rt")
    rt.preserve_quotes = True
    rt.indent(mapping=2, sequence=4, offset=2)
    rt.width = 100_000
    return rt


def _refuse_existing_stub_scripts(
    repo_root: Path, capability_dir: Path, stubs: list[PredicateStub]
) -> None:
    """Refuse when any stub's SCRIPT PATH is already taken.

    The registered-name check alone is not enough: a capability may hold a
    hand-written `scripts/<name>.py` it has not (yet) registered, and the stub
    path is derived from the command name, so scaffolding would silently
    overwrite real predicate code. Same never-silently-overwrite posture the
    stamps take for a declared coupling or contract. Pre-flighted so a refusal
    writes nothing at all; `_write_stub_script` enforces the same rule
    structurally at the write itself.
    """
    taken = sorted(
        (capability_dir / stub.script_relpath)
        for stub in stubs
        if (capability_dir / stub.script_relpath).exists()
    )
    if not taken:
        return
    listed = ", ".join(str(p.relative_to(repo_root)) for p in taken)
    raise ProcessAuthoringError(
        f"script path(s) already exist: {listed}; refusing to overwrite "
        "hand-written predicate code with a fail-closed stub. Register the "
        "existing script under the command name the shape demands, or rename "
        "the state/transition/seam so the derived path is free."
    )


def _write_stub_script(capability_dir: Path, stub: PredicateStub, body: str) -> Path:
    script_path = capability_dir / stub.script_relpath
    script_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Exclusive create: never clobber an existing script, even if the
        # caller's pre-flight was skipped or the file appeared since.
        with script_path.open("x", encoding="utf-8") as f:
            f.write(body)
    except FileExistsError as exc:
        raise ProcessAuthoringError(
            f"{script_path} already exists; refusing to overwrite it with a "
            "predicate stub."
        ) from exc
    script_path.chmod(
        script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )
    return script_path


def _register_commands(capability_dir: Path, stubs: list[PredicateStub]) -> None:
    """Append each stub to the capability `package.yaml` commands tree,
    round-trip-preserving. Collisions were pre-flighted by the caller."""
    package_path = capability_dir / "package.yaml"
    rt = _round_trip_yaml()
    data = rt.load(package_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProcessAuthoringError(
            f"{package_path} is not a YAML mapping; cannot register commands."
        )
    commands = data.get("commands")
    if commands is None:
        data["commands"] = commands = {}
    if not isinstance(commands, dict):
        raise ProcessAuthoringError(
            f"{package_path} has a non-mapping `commands:` block; cannot register."
        )
    for stub in stubs:
        commands[stub.command] = {
            "script": stub.script_relpath,
            "help": f"Predicate ({stub.purpose}). Stub — implement before relying on it.",
        }
    with package_path.open("w", encoding="utf-8") as f:
        rt.dump(data, f)


def _command_name(process_id: str, *parts: str) -> str:
    return "-".join([process_id, *parts])


def _gate_command_name(process_id: str, transition: "TransitionSpec") -> str:
    """A gate stub's command name, derived from the FULL transition key.

    A transition is keyed by (from, to, trigger): two edges between the same
    state pair are legal when their triggers differ (`approve` /
    `force-approve`), so a name derived from the pair alone would collide and
    leave the second edge ungateable. The trigger is kebab-checked at
    declaration, which keeps the derived name a well-formed command name.
    """
    source = transition.from_state.strip("*") or "any"
    return _command_name(
        process_id, "gate", source, transition.to_state, transition.trigger
    )


def _script_relpath(command: str) -> str:
    return "scripts/" + command.replace("-", "_") + ".py"


# --- shared address / capability resolution ---------------------------------


def _require_owned_address(repo_root: Path, address: str) -> tuple[str, str, Path]:
    """Resolve `<capability>:<process-id>` to its owning, REGISTERED capability.

    Three refusals, each naming a distinct cause and its remedy:

    1. **No `<capability>:` half.** The COR-044 boundary: the stamp REQUIRES a
       named owning capability and never routes — standing up a capability
       first is the composite skill's walkthrough judgment.
    2. **No capability directory.** Nothing on disk to stamp into.
    3. **A directory the project does not register as a component.** Contract
       discovery walks only the capabilities `installed_capabilities` names, so
       a definition stamped into an unregistered directory would be real,
       correct, and watched by nothing — `health` would report "no contracts
       declared" and exit 0 over it, the lying green COR-042 exists to prevent
       (#713). Shared with discovery through that one helper so the two can
       never disagree, FALLBACK INCLUDED: with no manifest, or a manifest
       listing no capabilities, the set is the filesystem scan, so a
       pre-manifest install stays authorable.

    Every stamp goes through here, so all three refuse identically.
    """
    if ":" not in address:
        raise ProcessAuthoringError(
            f"no owning capability given in {address!r}: a process definition "
            "is a capability-instance artifact (COR-044), addressed as "
            "<capability>:<process-id>. Name the owning capability; if none "
            "exists yet, author one first (the process-authoring skill walks "
            "that path — this command only stamps)."
        )
    try:
        capability, process_id = parse_address(address)
    except ProcessError as exc:
        raise ProcessAuthoringError(str(exc)) from exc
    capability_dir = repo_root / ".pkit" / "capabilities" / capability
    if not capability_dir.is_dir():
        raise ProcessAuthoringError(
            f"capability {capability!r} is not installed at "
            f"{capability_dir.relative_to(repo_root)}; a process definition "
            "needs an existing owning capability (COR-044 — this command does "
            "not create one)."
        )
    if capability not in installed_capabilities(repo_root):
        raise ProcessAuthoringError(
            f"capability {capability!r} exists at "
            f"{capability_dir.relative_to(repo_root)} but is not registered as "
            "a component with the project, so the process walk never discovers "
            "its definitions: whatever this stamp wrote would be watched by "
            "nothing, and `pkit process health` would report no contracts and "
            "exit 0 over it. Register it first, then re-run this stamp:\n"
            f"  pkit capabilities register {capability}"
        )
    return capability, process_id, capability_dir


def _locate_definition_file(repo_root: Path, definition: ProcessDefinition) -> Path:
    """The file a loaded definition came from, mirroring `load_definition`'s
    resolution order (convention path first, then the scan). The ambiguity
    case (two files claiming one id) already failed inside `load_definition`.
    """
    schemas_dir = definition.capability_dir / "schemas"
    by_convention = schemas_dir / f"{definition.process_id}.yaml"
    if by_convention.is_file():
        return by_convention
    yaml = YAML(typ="safe")
    for candidate in sorted(schemas_dir.glob("*.yaml")):
        try:
            raw = yaml.load(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(raw, dict):
            block = raw.get("process")
            if isinstance(block, dict) and block.get("id") == definition.process_id:
                return candidate
    raise ProcessAuthoringError(
        f"definition file for {definition.capability}:{definition.process_id} "
        "could not be located."
    )


# --- `process new` ----------------------------------------------------------


@dataclass(frozen=True)
class StateSpec:
    """One declared state: id, meaning, marks, and whether its entry is guarded."""

    state_id: str
    meaning: str
    entry: bool = False
    guarded_entry: bool = False
    terminal: bool = False


@dataclass(frozen=True)
class TransitionSpec:
    """One declared transition; `gate_kind` (when set) demands a gate stub."""

    from_state: str
    to_state: str
    trigger: str
    authorisation: str
    gate_kind: str | None = None


@dataclass(frozen=True)
class InvariantSpec:
    """One declared invariant (COR-035): id + why; the check is a stub."""

    invariant_id: str
    why: str


@dataclass(frozen=True)
class NewProcessResult:
    definition_path: Path
    stubs: tuple[PredicateStub, ...]
    warnings: tuple[str, ...] = ()


_DEFINITION_HEADER = """\
# yaml-language-server: $schema={schema_rel}
#
# Process definition for {address} — conforms to the substrate shape contract
# (COR-033; `.pkit/process/README.md` is the authoritative spec). Scaffolded by
# `pkit process new` (COR-044). Every predicate below is a registered STUB in
# ../package.yaml that FAILS CLOSED until implemented — implementing the teeth
# is the process-author agent's territory; evolving states/transitions is the
# deferred `amend` operation (which bumps `version`; couple/hand-off edits do
# not).
"""


def stamp_new_process(
    repo_root: Path,
    address: str,
    *,
    cardinality: str = "singleton",
    subject_key: str | None = None,
    domain_ref: str | None = None,
    states: list[StateSpec],
    transitions: list[TransitionSpec] | None = None,
    invariants: list[InvariantSpec] | None = None,
    blocked_on: str | None = None,
    dry_run: bool = False,
) -> NewProcessResult:
    """Scaffold a lint-clean process definition + its predicate stubs.

    Validates everything up front (so a refusal writes nothing), then writes
    the definition, the stub scripts, and the `package.yaml` registrations.
    The constructed `process` block is linted against the shape contract
    BEFORE any write — lint-clean by construction, not by promise.

    `domain_ref` is the optional pointer to where the subject's DOMAIN data
    lives, kept distinct from its process position. It applies to either
    cardinality, and the only check is that it carries something: the engine
    never interprets it and the contract fixes no form, so a stamp that
    guessed at one (a path? an address? a URL?) would refuse pointers the
    contract admits. Omitting it leaves the key out entirely — the shape
    requires only `cardinality`, so a definition without one is as valid as
    one with.

    `dry_run` reports exactly what a real run would stamp and writes nothing.
    It costs no fidelity here: every check, including the shape lint of the
    constructed block, already runs before the first write.
    """
    transitions = transitions or []
    invariants = invariants or []
    capability, process_id, capability_dir = _require_owned_address(repo_root, address)

    if not _KEBAB_CASE.match(process_id):
        raise ProcessAuthoringError(
            f"process id {process_id!r} must be kebab-case (^[a-z][a-z0-9-]*$)."
        )

    # One id, one definition: refuse when the id already resolves.
    definition_path = capability_dir / "schemas" / f"{process_id}.yaml"
    if definition_path.exists():
        raise ProcessAuthoringError(
            f"{definition_path.relative_to(repo_root)} already exists; "
            "`process new` is a one-shot scaffold (evolving a live definition "
            "is the deferred `amend` operation)."
        )
    try:
        load_definition(repo_root, address)
    except ProcessError:
        pass  # good: nothing claims the id yet
    else:
        raise ProcessAuthoringError(
            f"a schema in {capability!r} already declares process id "
            f"{process_id!r}; exactly one definition may claim an id."
        )

    # Subject block, vocabularies read as data.
    cardinalities = cardinality_vocabulary(repo_root)
    if cardinality not in cardinalities:
        raise ProcessAuthoringError(
            f"cardinality {cardinality!r} is not in the shape contract's set "
            f"({', '.join(cardinalities)})."
        )
    if subject_key is not None and cardinality != "keyed":
        raise ProcessAuthoringError(
            "--key names what identifies a KEYED unit (COR-032); it has no "
            "meaning for a singleton subject."
        )
    if domain_ref is not None and not domain_ref.strip():
        raise ProcessAuthoringError(
            "--domain-ref points at where the subject's domain data lives; an "
            "empty pointer says nothing. Omit the flag instead — the field is "
            "optional in the shape contract."
        )

    # States: unique kebab ids, non-empty meanings, consistent marks.
    if not states:
        raise ProcessAuthoringError("at least one --state is required.")
    seen: set[str] = set()
    for spec in states:
        if not _KEBAB_CASE.match(spec.state_id):
            raise ProcessAuthoringError(
                f"state id {spec.state_id!r} must be kebab-case."
            )
        if spec.state_id in seen:
            raise ProcessAuthoringError(f"state {spec.state_id!r} declared twice.")
        seen.add(spec.state_id)
        if not spec.meaning.strip():
            raise ProcessAuthoringError(
                f"state {spec.state_id!r} needs a meaning — the status view "
                "renders from it (COR-033)."
            )
        if spec.entry and spec.guarded_entry:
            raise ProcessAuthoringError(
                f"state {spec.state_id!r} is marked both plain entry and "
                "guarded entry; pick one."
            )
    state_ids = {s.state_id for s in states}

    # Transitions: endpoints must be declared states ("*" = any source).
    authorisations = authorisation_vocabulary(repo_root)
    gate_kinds = gate_kind_vocabulary(repo_root)
    for t in transitions:
        if t.from_state != "*" and t.from_state not in state_ids:
            raise ProcessAuthoringError(
                f"transition {t.from_state!r} -> {t.to_state!r} names an "
                f"undeclared source state."
            )
        if t.to_state not in state_ids:
            raise ProcessAuthoringError(
                f"transition {t.from_state!r} -> {t.to_state!r} names an "
                f"undeclared target state."
            )
        if not _KEBAB_CASE.match(t.trigger):
            raise ProcessAuthoringError(
                f"transition {t.from_state!r} -> {t.to_state!r} needs a "
                f"kebab-case trigger (got {t.trigger!r}). The trigger is the "
                "third component of a transition's key, and a gate stub's "
                "command name is derived from that key — so the stamp holds it "
                "to the same id discipline as every other id it writes."
            )
        if t.authorisation not in authorisations:
            raise ProcessAuthoringError(
                f"authorisation {t.authorisation!r} is not in the shape "
                f"contract's set ({', '.join(authorisations)})."
            )
        if t.gate_kind is not None:
            if t.gate_kind not in gate_kinds:
                raise ProcessAuthoringError(
                    f"gate kind {t.gate_kind!r} is not in the shape contract's "
                    f"set ({', '.join(gate_kinds)})."
                )
            if t.gate_kind not in _PREDICATE_GATE_KINDS:
                raise ProcessAuthoringError(
                    f"gate kind {t.gate_kind!r} is engine-computed from a "
                    "`subprocess` / `cascade` block — a deferred `new` surface "
                    "(COR-044 named-deferred block kinds), not a predicate stub."
                )
    # A transition's key is (from, to, trigger) — two edges between the same
    # pair are legal when their triggers differ (`approve` / `force-approve`),
    # but two with the SAME key are a duplicate that makes every per-transition
    # address (a gate's, above all) ambiguous.
    keys = [(t.from_state, t.to_state, t.trigger) for t in transitions]
    if len(set(keys)) != len(keys):
        duplicate = next(k for k in keys if keys.count(k) > 1)
        raise ProcessAuthoringError(
            f"transition {duplicate[0]!r} -> {duplicate[1]!r} on trigger "
            f"{duplicate[2]!r} is declared twice; a transition is keyed by "
            "(from, to, trigger)."
        )

    for inv in invariants:
        if not _KEBAB_CASE.match(inv.invariant_id):
            raise ProcessAuthoringError(
                f"invariant id {inv.invariant_id!r} must be kebab-case."
            )
        if not inv.why.strip():
            raise ProcessAuthoringError(
                f"invariant {inv.invariant_id!r} needs a why — it is surfaced "
                "on every violation (COR-035)."
            )
    if len({i.invariant_id for i in invariants}) != len(invariants):
        raise ProcessAuthoringError("invariant ids must be unique.")

    if blocked_on is not None:
        blocked_reasons = blocked_on_vocabulary(repo_root)
        if blocked_on not in blocked_reasons:
            raise ProcessAuthoringError(
                f"blocked_on {blocked_on!r} is not in the shape contract's set "
                f"({', '.join(blocked_reasons)})."
            )

    # The stubs the declared shape demands (COR-044: the teeth are every
    # evaluable the shape declares — detection always, the rest when declared).
    stubs: list[PredicateStub] = []
    bodies: dict[str, str] = {}

    def add_stub(command: str, purpose: str, payload_key: str) -> str:
        stub = PredicateStub(
            command=command, script_relpath=_script_relpath(command), purpose=purpose
        )
        stubs.append(stub)
        bodies[command] = _stub_body(purpose, address, "new", cardinality, payload_key)
        return command

    for spec in states:
        add_stub(
            _command_name(process_id, "detect", spec.state_id),
            f"detection — is the subject at {spec.state_id!r}?",
            "detection",
        )
    for spec in states:
        if spec.guarded_entry:
            add_stub(
                _command_name(process_id, "entry", spec.state_id),
                f"entry guard — may the journey start at {spec.state_id!r}?",
                "entry guard",
            )
    for t in transitions:
        if t.gate_kind is not None:
            payload_key = (
                "authorisation-artifact gate"
                if t.gate_kind == "authorisation-artifact"
                else "gate"
            )
            add_stub(
                _gate_command_name(process_id, t),
                f"{t.gate_kind} gate — may the subject move "
                f"{t.from_state!r} -> {t.to_state!r} on {t.trigger!r}?",
                payload_key,
            )
    if blocked_on == "awaiting-condition":
        add_stub(
            _command_name(process_id, "resume-when"),
            "resume_when — has the awaited external fact become true?",
            "resume_when",
        )
    for inv in invariants:
        add_stub(
            _command_name(process_id, "invariant", inv.invariant_id),
            f"invariant check — does {inv.invariant_id!r} hold?",
            "invariant check",
        )

    if len({s.command for s in stubs}) != len(stubs):
        raise ProcessAuthoringError(
            "declared shape produces duplicate predicate command names; rename "
            "the colliding states/transitions/invariants."
        )
    registry = _load_command_registry(capability_dir)
    collisions = sorted({s.command for s in stubs} & set(registry))
    if collisions:
        raise ProcessAuthoringError(
            f"command name(s) already registered in {capability!r}'s "
            f"package.yaml: {', '.join(collisions)}; the scaffold refuses to "
            "clobber existing commands."
        )
    _refuse_existing_stub_scripts(repo_root, capability_dir, stubs)
    package_path = capability_dir / "package.yaml"
    if not package_path.is_file():
        raise ProcessAuthoringError(
            f"{package_path.relative_to(repo_root)} not found; predicate stubs "
            "register in the owning capability's package.yaml "
            "(.pkit/process/README.md, the predicate runner)."
        )

    # Build the process block, then lint it BEFORE any write.
    subject_block: dict[str, Any] = {"cardinality": cardinality}
    if subject_key is not None:
        subject_block["key"] = subject_key
    if domain_ref is not None:
        subject_block["domain_ref"] = domain_ref
    if blocked_on is not None:
        blocked_block: dict[str, Any] = {"blocked_on": blocked_on}
        if blocked_on == "awaiting-condition":
            blocked_block["resume_when"] = {
                "run": _command_name(process_id, "resume-when")
            }
        subject_block["blocked"] = blocked_block

    states_block: list[dict[str, Any]] = []
    for spec in states:
        state_block: dict[str, Any] = {
            "id": spec.state_id,
            "meaning": spec.meaning,
            "detection": {
                "mode": "inferred",
                "predicate": {"run": _command_name(process_id, "detect", spec.state_id)},
            },
        }
        if spec.entry:
            state_block["entry"] = True
        if spec.guarded_entry:
            state_block["entry"] = {
                "when": {"run": _command_name(process_id, "entry", spec.state_id)}
            }
        if spec.terminal:
            state_block["terminal"] = True
        states_block.append(state_block)

    transitions_block: list[dict[str, Any]] = []
    for t in transitions:
        transition_block: dict[str, Any] = {
            "from": t.from_state,
            "to": t.to_state,
            "trigger": t.trigger,
            "authorisation": t.authorisation,
        }
        if t.gate_kind is not None:
            transition_block["gate"] = {
                "kind": t.gate_kind,
                "predicate": {"run": _gate_command_name(process_id, t)},
            }
        transitions_block.append(transition_block)

    process_block: dict[str, Any] = {
        "id": process_id,
        "version": 1,
        "subject": subject_block,
        "states": states_block,
        "transitions": transitions_block,
    }
    if invariants:
        process_block["invariants"] = [
            {
                "id": inv.invariant_id,
                "check": {"run": _command_name(process_id, "invariant", inv.invariant_id)},
                "why": inv.why,
            }
            for inv in invariants
        ]

    lint = lint_process_block(repo_root, process_block)
    if lint:
        raise ProcessAuthoringError(
            "constructed definition failed shape lint (a stamp bug — nothing "
            "was written): " + "; ".join(lint)
        )

    # All checks passed: write definition, stubs, registrations.
    if not dry_run:
        schema_rel = Path("..") / ".." / ".." / "schemas" / "_defs" / "process.schema.json"
        yaml = _round_trip_yaml()
        definition_path.parent.mkdir(parents=True, exist_ok=True)
        with definition_path.open("w", encoding="utf-8") as f:
            f.write(
                _DEFINITION_HEADER.format(
                    schema_rel=schema_rel.as_posix(), address=address
                )
            )
            f.write("\n")
            yaml.dump({"process": process_block}, f)
        for stub in stubs:
            _write_stub_script(capability_dir, stub, bodies[stub.command])
        _register_commands(capability_dir, stubs)

    warnings: list[str] = []
    if not any(s.entry or s.guarded_entry for s in states):
        warnings.append("no entry state marked — the definition declares no start.")
    if not any(s.terminal for s in states):
        warnings.append(
            "no terminal state marked — the process declares no outcome a "
            "parent could wire (COR-036)."
        )
    return NewProcessResult(
        definition_path=definition_path,
        stubs=tuple(stubs),
        warnings=tuple(warnings),
    )


# --- `process couple` -------------------------------------------------------


@dataclass(frozen=True)
class CoupleResult:
    definition_path: Path
    state_id: str
    changed: bool  # False = the identical entry was already declared (no-op)
    warnings: tuple[str, ...] = ()


def couple_process(
    repo_root: Path,
    address: str,
    *,
    state_id: str,
    upstream: str,
    relation: str,
    mode: str,
    why: str,
    dry_run: bool = False,
) -> CoupleResult:
    """Append a `depends_on` entry (COR-038) to the invoker-named definition.

    Mutates ONLY the named (subscriber) definition — coupling lives in the
    subscriber, the upstream is untouched (COR-038 / COR-044 owner-scoping by
    construction). `relation` and `mode` are validated against the closed
    vocabularies read from the shape contract. The definition `version` is NOT
    bumped: the entry is additive and inert (COR-044).

    An entry is identified by (upstream, relation, mode) — the shape puts no
    uniqueness constraint on `depends_on`, so one downstream state may legally
    depend on the same upstream in two different ways (an `informational` pull
    beside a `triggered-by` push). Idempotent on the identical entry (that key
    plus the same `why`): a clean no-op. Same key, different `why`: a genuine
    divergence, and it refuses — editing a declared edge is deliberate work,
    never a silent overwrite. Different key: a new, legal entry, appended.

    `dry_run` runs every check and reports what would change, writing nothing.
    """
    _require_owned_address(repo_root, address)
    try:
        definition = load_definition(repo_root, address)
    except ProcessError as exc:
        raise ProcessAuthoringError(str(exc)) from exc
    definition_path = _locate_definition_file(repo_root, definition)

    if definition.state(state_id) is None:
        known = ", ".join(s.get("id", "?") for s in definition.states)
        raise ProcessAuthoringError(
            f"{state_id!r} is not a state of {address!r} (states: {known}); "
            "a `depends_on` entry is hosted on one of the definition's states."
        )

    relations = relation_vocabulary(repo_root)
    if relation not in relations:
        raise ProcessAuthoringError(
            f"relation {relation!r} is not in COR-038's closed set as the shape "
            f"contract declares it ({', '.join(relations)})."
        )
    modes = mode_vocabulary(repo_root)
    if mode not in modes:
        raise ProcessAuthoringError(
            f"mode {mode!r} is not in the shape contract's set ({', '.join(modes)})."
        )
    if not why.strip():
        raise ProcessAuthoringError(
            "a `depends_on` entry requires a `why` — the human-readable reason "
            "the render surfaces (COR-038)."
        )

    warnings: list[str] = []
    if ":" not in upstream:
        raise ProcessAuthoringError(
            f"upstream {upstream!r} is not a process address; expected "
            "<capability>:<process-id> (COR-038's address grammar)."
        )
    try:
        parse_address(upstream)
    except ProcessError as exc:
        raise ProcessAuthoringError(str(exc)) from exc
    try:
        load_definition(repo_root, upstream)
    except ProcessError as exc:
        warnings.append(
            f"upstream {upstream!r} does not resolve to a definition here "
            f"({exc}); the entry is inert metadata (COR-038) so this is "
            "declarable, but a later hand-off contract on it would report "
            "indeterminate."
        )

    rt = _round_trip_yaml()
    original = definition_path.read_text(encoding="utf-8")
    data = rt.load(original)
    state_block = _rt_state_block(data, state_id, definition_path)

    existing = state_block.get("depends_on")
    if existing is not None and not isinstance(existing, list):
        raise ProcessAuthoringError(
            f"state {state_id!r} carries a non-list `depends_on`; fix the "
            "definition by hand before coupling."
        )
    for entry in existing or []:
        if not isinstance(entry, dict):
            continue
        key = (entry.get("upstream"), entry.get("relation"), entry.get("mode"))
        if key != (upstream, relation, mode):
            continue  # a different edge (or a different way of depending) — legal
        if entry.get("why") == why:
            return CoupleResult(
                definition_path=definition_path,
                state_id=state_id,
                changed=False,
                warnings=tuple(warnings),
            )
        raise ProcessAuthoringError(
            f"state {state_id!r} already declares this coupling on upstream "
            f"{upstream!r} ({relation}, {mode}) with a DIFFERENT why "
            f"({entry.get('why')!r}); refusing to overwrite a declared edge — "
            "edit the definition deliberately."
        )

    new_entry = {"upstream": upstream, "relation": relation, "mode": mode, "why": why}
    if existing is None:
        state_block["depends_on"] = [new_entry]
    else:
        existing.append(new_entry)

    if not dry_run:
        with definition_path.open("w", encoding="utf-8") as f:
            rt.dump(data, f)
        _lint_or_restore(repo_root, definition_path, original, "`process couple`")
    else:
        _lint_in_memory(repo_root, data, "`process couple --dry-run`")
    return CoupleResult(
        definition_path=definition_path,
        state_id=state_id,
        changed=True,
        warnings=tuple(warnings),
    )


def _rt_state_block(data: Any, state_id: str, definition_path: Path) -> Any:
    """The round-tripped state mapping with `state_id`, or a clean error."""
    process = data.get("process") if isinstance(data, dict) else None
    states = process.get("states") if isinstance(process, dict) else None
    if isinstance(states, list):
        for state in states:
            if isinstance(state, dict) and state.get("id") == state_id:
                return state
    raise ProcessAuthoringError(
        f"state {state_id!r} not found in {definition_path} on the round-trip "
        "read; the definition changed underneath the stamp."
    )


# --- `process hand-off` -----------------------------------------------------


@dataclass(frozen=True)
class HandoffResult:
    definition_path: Path
    state_id: str
    changed: bool  # False = the identical contract was already declared (no-op)
    stubs: tuple[PredicateStub, ...] = ()
    warnings: tuple[str, ...] = ()


def handoff_process(
    repo_root: Path,
    address: str,
    *,
    upstream: str,
    trigger: str,
    candidates: str,
    resolve: str,
    state_id: str | None = None,
    dry_run: bool = False,
) -> HandoffResult:
    """Add a COR-042 hand-off contract to an EXISTING coupling on the
    invoker-named definition.

    Refuses when no `depends_on` entry for `upstream` exists (`process couple`
    first — the contract is a sub-block of a declared coupling, never a
    free-floating edge). Validates the trigger is a state of the upstream
    definition WHERE that definition resolves at authoring time; an
    unresolvable upstream degrades to a warning (health will report the
    contract indeterminate until it resolves — never silently green).

    `candidates` / `resolve` name commands of the DECLARING capability: names
    not yet registered are scaffolded as fail-closed seam stubs (ADR-048
    payload shapes) and registered in package.yaml; already-registered names
    are reused untouched. The definition `version` is NOT bumped (the contract
    is additive and report-only, COR-044).

    `dry_run` runs every check and reports the contract and seam stubs it would
    write, writing nothing.
    """
    _require_owned_address(repo_root, address)
    try:
        definition = load_definition(repo_root, address)
    except ProcessError as exc:
        raise ProcessAuthoringError(str(exc)) from exc
    definition_path = _locate_definition_file(repo_root, definition)
    capability_dir = definition.capability_dir

    # Find the coupling: the depends_on entry naming this upstream.
    hosting: list[tuple[str, dict[str, Any]]] = []
    for state in definition.states:
        sid = state.get("id")
        for entry in state.get("depends_on") or []:
            if isinstance(entry, dict) and entry.get("upstream") == upstream:
                hosting.append((sid if isinstance(sid, str) else "?", entry))
    if state_id is not None:
        hosting = [(sid, e) for sid, e in hosting if sid == state_id]
    if not hosting:
        where = f" on state {state_id!r}" if state_id is not None else ""
        raise ProcessAuthoringError(
            f"{address!r} declares no coupling on upstream {upstream!r}{where}; "
            "a hand-off contract is a sub-block of an existing `depends_on` "
            "entry — run `pkit process couple` first (COR-042)."
        )
    if len(hosting) > 1:
        states_list = ", ".join(sid for sid, _ in hosting)
        raise ProcessAuthoringError(
            f"{address!r} couples to {upstream!r} on several states "
            f"({states_list}); pass --state to name the hosting entry."
        )
    hosting_state, _ = hosting[0]

    if not trigger.strip():
        raise ProcessAuthoringError("a hand-off contract requires a trigger state.")
    warnings: list[str] = []
    try:
        upstream_def = load_definition(repo_root, upstream)
    except ProcessError as exc:
        warnings.append(
            f"upstream {upstream!r} does not resolve at authoring time ({exc}); "
            "the trigger cannot be validated here and `health` will report the "
            "contract INDETERMINATE until it resolves."
        )
    else:
        if upstream_def.state(trigger) is None:
            known = ", ".join(s.get("id", "?") for s in upstream_def.states)
            raise ProcessAuthoringError(
                f"trigger {trigger!r} is not a state of {upstream!r} (states: "
                f"{known}); a phantom trigger would report indeterminate "
                "forever (COR-042). Declare a STABLE upstream state — one the "
                "subject holds until the hand-off happens."
            )

    for name, label in ((candidates, "candidates"), (resolve, "resolve")):
        if not _KEBAB_CASE.match(name):
            raise ProcessAuthoringError(
                f"{label} command name {name!r} must be kebab-case (it "
                "registers in the capability's package.yaml)."
            )

    # Scaffold + register the seam stubs for names not yet registered.
    registry = _load_command_registry(capability_dir)
    new_stubs: list[PredicateStub] = []
    bodies: dict[str, str] = {}
    seam_specs = [
        (
            candidates,
            "hand-off candidates",
            f"candidate source — which upstream subjects of {upstream!r} sit "
            f"at {trigger!r}? (the source PROPOSES; health confirms each "
            "through the engine's position resolution). A source that can "
            "silently return nothing against a wrong root is an authoring "
            "smell (COR-042) — error instead when the root is missing.",
        ),
        (
            resolve,
            "hand-off resolve",
            f"resolve seam — which downstream subject(s) of {address!r} pick "
            "up ONE upstream subject? Empty list = determinate absence (a "
            "MISS); error = indeterminate.",
        ),
    ]
    for name, payload_key, purpose in seam_specs:
        if name in registry:
            continue
        if name in bodies:
            raise ProcessAuthoringError(
                "candidates and resolve must be two distinct commands (the two "
                "seams answer different questions, ADR-048)."
            )
        stub = PredicateStub(
            command=name, script_relpath=_script_relpath(name), purpose=purpose
        )
        new_stubs.append(stub)
        bodies[name] = _stub_body(
            purpose, address, "hand-off", definition.cardinality, payload_key
        )
    # Pre-flight before the definition is touched: a seam whose script path is
    # taken must refuse with the definition still unedited.
    _refuse_existing_stub_scripts(repo_root, capability_dir, new_stubs)

    rt = _round_trip_yaml()
    original = definition_path.read_text(encoding="utf-8")
    data = rt.load(original)
    state_block = _rt_state_block(data, hosting_state, definition_path)
    entry_block = None
    for entry in state_block.get("depends_on") or []:
        if isinstance(entry, dict) and entry.get("upstream") == upstream:
            entry_block = entry
            break
    if entry_block is None:
        raise ProcessAuthoringError(
            f"coupling on {upstream!r} not found on the round-trip read; the "
            "definition changed underneath the stamp."
        )

    existing = entry_block.get("handoff")
    if existing is not None:
        same = (
            isinstance(existing, dict)
            and existing.get("trigger") == trigger
            and isinstance(existing.get("candidates"), dict)
            and existing["candidates"].get("run") == candidates
            and isinstance(existing.get("resolve"), dict)
            and existing["resolve"].get("run") == resolve
        )
        if same:
            return HandoffResult(
                definition_path=definition_path,
                state_id=hosting_state,
                changed=False,
                warnings=tuple(warnings),
            )
        raise ProcessAuthoringError(
            f"the coupling on {upstream!r} already carries a DIFFERENT "
            "hand-off contract; refusing to overwrite a declared contract — "
            "edit the definition deliberately."
        )

    entry_block["handoff"] = {
        "trigger": trigger,
        "candidates": {"run": candidates},
        "resolve": {"run": resolve},
    }
    if dry_run:
        _lint_in_memory(repo_root, data, "`process hand-off --dry-run`")
    else:
        with definition_path.open("w", encoding="utf-8") as f:
            rt.dump(data, f)
        _lint_or_restore(repo_root, definition_path, original, "`process hand-off`")

        for stub in new_stubs:
            _write_stub_script(capability_dir, stub, bodies[stub.command])
        if new_stubs:
            _register_commands(capability_dir, new_stubs)

    return HandoffResult(
        definition_path=definition_path,
        state_id=hosting_state,
        changed=True,
        stubs=tuple(new_stubs),
        warnings=tuple(warnings),
    )
