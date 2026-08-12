"""The `pkit process new / couple / hand-off` authoring stamps (COR-044) and
the interpretation-only health variant.

These tests pin the load-bearing facts:

- `new` scaffolds a LINT-CLEAN definition (subject incl. cardinality, states
  with meanings, transitions, entry/terminal marks) into a NAMED owning
  capability, with a fail-closed predicate stub for every evaluable the
  declared shape demands (detection always; gates / entry guards /
  resume_when / invariant checks when declared), each registered in the
  owning capability's package.yaml; it errors cleanly when no owning
  capability is given (NO routing — that is the skill's judgment);
- `couple` appends a `depends_on` entry to the invoker-named definition,
  validating relation/mode against the CLOSED vocabularies READ AS DATA from
  the shape contract (a widened enum is accepted with no code change), and
  NEVER bumps the definition version (additive inert edit, COR-044);
- `hand-off` adds the COR-042 contract to an EXISTING coupling only, validates
  the trigger against the upstream definition where resolvable at authoring
  time, scaffolds + registers the seam stubs, and likewise never bumps the
  version;
- both mutations are idempotent on the identical declaration and refuse to
  overwrite a DIFFERENT declared edge/contract;
- the interpretation-only check reports INDETERMINATES only — misses are not
  counted and do not affect its exit code — and is a CONSUMER of the existing
  health walker (COR-042 point 5's design-once rule), with the default health
  run's exit contract untouched.

Fixtures mirror `test_process_health.py`: a scratch repo carrying the REAL
shape contract (copied from the source tree — the vocabularies must come from
the contract file, which is exactly what the read-as-data tests exercise) and
file-backed predicate scripts.
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import process_authoring as pa
from project_kit import process_health as ph
from project_kit import schemas_validate
from project_kit.cli import main
from project_kit.process import ProcessError, load_definition
from project_kit.schemas_validate import _is_schema_definition

_SOURCE_ROOT = Path(__file__).resolve().parents[1]
_SHAPE_CONTRACT = _SOURCE_ROOT / ".pkit" / "schemas" / "_defs" / "process.schema.json"


def _write_package_yaml(cap: Path, name: str) -> None:
    cap.joinpath("package.yaml").write_text(
        "schema_version: 2\n"
        "component:\n"
        "  kind: capability\n"
        f"  name: {name}\n"
        "  version: 0.1.0\n"
        f"description: Authoring fixture capability ({name}).\n",
        encoding="utf-8",
    )


@pytest.fixture
def authoring_repo(tmp_path: Path) -> Path:
    """A scratch repo with the real shape contract + two empty capabilities
    (`design` upstream, `delivery` downstream)."""
    defs_dir = tmp_path / ".pkit" / "schemas" / "_defs"
    defs_dir.mkdir(parents=True)
    shutil.copy(_SHAPE_CONTRACT, defs_dir / "process.schema.json")
    for name in ("design", "delivery"):
        cap = tmp_path / ".pkit" / "capabilities" / name
        cap.mkdir(parents=True)
        _write_package_yaml(cap, name)
    return tmp_path


def _stamp_screen(repo: Path) -> pa.NewProcessResult:
    """The upstream fixture: keyed design:screen with an entry, a terminal
    trigger-suitable state, and one transition."""
    return pa.stamp_new_process(
        repo,
        "design:screen",
        cardinality="keyed",
        subject_key="screen-id",
        states=[
            pa.StateSpec("drafting", "Drafting the screen design.", entry=True),
            pa.StateSpec("ready", "Ready to hand off.", terminal=True),
        ],
        transitions=[pa.TransitionSpec("drafting", "ready", "approve", "user")],
    )


def _stamp_unit(repo: Path) -> pa.NewProcessResult:
    """The downstream fixture: singleton delivery:unit."""
    return pa.stamp_new_process(
        repo,
        "delivery:unit",
        states=[
            pa.StateSpec("building", "Building a unit for a readied screen.", entry=True)
        ],
    )


def _couple_unit(repo: Path, **overrides) -> pa.CoupleResult:
    kwargs = dict(
        state_id="building",
        upstream="design:screen",
        relation="triggered-by",
        mode="push",
        why="A unit builds the screen the design process readied.",
    )
    kwargs.update(overrides)
    return pa.couple_process(repo, "delivery:unit", **kwargs)


def _handoff_unit(repo: Path, **overrides) -> pa.HandoffResult:
    kwargs = dict(
        upstream="design:screen",
        trigger="ready",
        candidates="unit-handoff-candidates",
        resolve="unit-handoff-resolve",
    )
    kwargs.update(overrides)
    return pa.handoff_process(repo, "delivery:unit", **kwargs)


def _registered_commands(repo: Path, capability: str) -> dict:
    from ruamel.yaml import YAML

    package = repo / ".pkit" / "capabilities" / capability / "package.yaml"
    data = YAML(typ="safe").load(package.read_text(encoding="utf-8"))
    return data.get("commands") or {}


def _definition_version(repo: Path, capability: str, process_id: str) -> int:
    from ruamel.yaml import YAML

    path = repo / ".pkit" / "capabilities" / capability / "schemas" / f"{process_id}.yaml"
    data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    return data["process"]["version"]


# --- `process new`: scaffold correctness + lint-cleanliness -----------------


def test_new_scaffolds_lint_clean_definition(authoring_repo: Path) -> None:
    result = _stamp_screen(authoring_repo)
    assert result.definition_path.is_file()

    # Loads through the engine's own loader and lints clean against the shape
    # contract — the checkable form of "lint-clean by construction".
    definition = load_definition(authoring_repo, "design:screen")
    assert pa.lint_process_block(authoring_repo, definition.data) == []

    # The declared shape landed: subject incl. cardinality, states with
    # meanings, transitions, entry/terminal marks.
    assert definition.data["subject"] == {"cardinality": "keyed", "key": "screen-id"}
    states = {s["id"]: s for s in definition.states}
    assert states["drafting"]["meaning"] == "Drafting the screen design."
    assert states["drafting"]["entry"] is True
    assert states["ready"]["terminal"] is True
    (transition,) = definition.transitions
    assert (transition["from"], transition["to"], transition["trigger"]) == (
        "drafting",
        "ready",
        "approve",
    )

    # Detection stubs ALWAYS: one per state, registered + on disk + executable.
    commands = _registered_commands(authoring_repo, "design")
    for state_id in ("drafting", "ready"):
        name = f"screen-detect-{state_id}"
        assert name in commands
        script = (
            authoring_repo / ".pkit" / "capabilities" / "design" / commands[name]["script"]
        )
        assert script.is_file()
        assert script.stat().st_mode & stat.S_IXUSR


def test_new_definition_is_a_schema_instance_not_a_schema(authoring_repo: Path) -> None:
    # The stamped YAML declares the shape contract as its external `$schema`,
    # so `schemas validate` treats it as an instance (no companion demanded).
    result = _stamp_screen(authoring_repo)
    assert not _is_schema_definition(result.definition_path)


def test_stamped_definition_passes_the_project_wide_schema_gate(
    authoring_repo: Path, monkeypatch
) -> None:
    # The gate `scripts/check.sh` runs is `pkit schemas validate` with NO PATH
    # — a different walk from the path-scoped one. Both must classify a stamped
    # definition the same way, or the first adopter to stamp one inherits a red
    # CI demanding a companion JSON Schema that categorically cannot exist.
    _stamp_screen(authoring_repo)
    assert schemas_validate.validate_all(authoring_repo).is_clean

    monkeypatch.setattr("project_kit.cli.find_target_root", lambda: authoring_repo)
    result = CliRunner().invoke(main, ["schemas", "validate"])
    assert result.exit_code == 0, result.output
    assert "screen.yaml" not in result.output

    # The exemption is scoped to instances: a real schema YAML with no
    # companion is still caught by the same walk.
    (authoring_repo / ".pkit" / "capabilities" / "design" / "schemas" / "orphan.yaml").write_text(
        "types:\n  thing:\n    meaning: A thing.\n", encoding="utf-8"
    )
    assert not schemas_validate.validate_all(authoring_repo).is_clean


def test_new_stubs_fail_closed_and_are_read_only(authoring_repo: Path) -> None:
    # The predicate-runner contract: subject argv + --json, one JSON object on
    # stdout, and FAIL-CLOSED until implemented — a non-zero exit the runner
    # reads as indeterminate, never as a pass. And read-only: running it
    # writes nothing.
    _stamp_screen(authoring_repo)
    script = (
        authoring_repo
        / ".pkit"
        / "capabilities"
        / "design"
        / "scripts"
        / "screen_detect_drafting.py"
    )
    before = {p for p in authoring_repo.rglob("*") if p.is_file()}
    completed = subprocess.run(
        [sys.executable, str(script), "screen-1", "--json"],
        cwd=str(authoring_repo),
        capture_output=True,
        text=True,
        check=False,
    )
    after = {p for p in authoring_repo.rglob("*") if p.is_file()}
    assert completed.returncode != 0  # fail-closed: never green unimplemented
    assert isinstance(json.loads(completed.stdout), dict)  # contract-shaped output
    assert after == before  # read-only


def test_new_stubs_every_declared_evaluable(authoring_repo: Path) -> None:
    # Gates, guarded entries, resume_when, and invariant checks each demand a
    # stub WHEN DECLARED (COR-044: the teeth are every evaluable the shape
    # declares).
    pa.stamp_new_process(
        authoring_repo,
        "design:ladder",
        states=[
            pa.StateSpec("open", "Openable rung.", guarded_entry=True),
            pa.StateSpec("shut", "Shut rung.", terminal=True),
        ],
        transitions=[
            pa.TransitionSpec(
                "open", "shut", "close", "user", gate_kind="authorisation-artifact"
            )
        ],
        invariants=[pa.InvariantSpec("has-owner", "Every ladder names an owner.")],
        blocked_on="awaiting-condition",
    )
    commands = set(_registered_commands(authoring_repo, "design"))
    assert {
        "ladder-detect-open",
        "ladder-detect-shut",
        "ladder-entry-open",
        "ladder-gate-open-shut",
        "ladder-resume-when",
        "ladder-invariant-has-owner",
    } <= commands
    # The declaration wired each stub where the shape demands it — and the
    # result still lints clean (the conditional blocks conform too).
    definition = load_definition(authoring_repo, "design:ladder")
    assert pa.lint_process_block(authoring_repo, definition.data) == []
    states = {s["id"]: s for s in definition.states}
    assert states["open"]["entry"] == {"when": {"run": "ladder-entry-open"}}
    (transition,) = definition.transitions
    assert transition["gate"]["predicate"] == {"run": "ladder-gate-open-shut"}
    assert definition.data["subject"]["blocked"]["resume_when"] == {
        "run": "ladder-resume-when"
    }
    (invariant,) = definition.invariants
    assert invariant["check"] == {"run": "ladder-invariant-has-owner"}


def test_new_requires_an_owning_capability(authoring_repo: Path) -> None:
    # No capability half in the address: a clean, routing-free error (COR-044 —
    # the capability walkthrough is the skill's judgment, never the stamp's).
    with pytest.raises(pa.ProcessAuthoringError, match="owning capability"):
        pa.stamp_new_process(
            authoring_repo, "orphan", states=[pa.StateSpec("only", "Only state.")]
        )
    with pytest.raises(pa.ProcessAuthoringError, match="not installed"):
        pa.stamp_new_process(
            authoring_repo, "ghost:orphan", states=[pa.StateSpec("only", "Only state.")]
        )
    # Nothing was written anywhere.
    assert not list((authoring_repo / ".pkit" / "capabilities").rglob("*.yaml"))[2:]


def test_new_is_one_shot(authoring_repo: Path) -> None:
    _stamp_screen(authoring_repo)
    original = (
        authoring_repo / ".pkit" / "capabilities" / "design" / "schemas" / "screen.yaml"
    ).read_text(encoding="utf-8")
    with pytest.raises(pa.ProcessAuthoringError, match="already exists"):
        _stamp_screen(authoring_repo)
    current = (
        authoring_repo / ".pkit" / "capabilities" / "design" / "schemas" / "screen.yaml"
    ).read_text(encoding="utf-8")
    assert current == original


def test_new_refuses_dangling_references(authoring_repo: Path) -> None:
    with pytest.raises(pa.ProcessAuthoringError, match="undeclared target"):
        pa.stamp_new_process(
            authoring_repo,
            "design:broken",
            states=[pa.StateSpec("only", "Only state.")],
            transitions=[pa.TransitionSpec("only", "ghost", "go", "user")],
        )
    with pytest.raises(pa.ProcessAuthoringError, match="declared twice"):
        pa.stamp_new_process(
            authoring_repo,
            "design:broken",
            states=[pa.StateSpec("dup", "One."), pa.StateSpec("dup", "Two.")],
        )
    with pytest.raises(pa.ProcessAuthoringError, match="engine-computed"):
        pa.stamp_new_process(
            authoring_repo,
            "design:broken",
            states=[pa.StateSpec("a", "A."), pa.StateSpec("b", "B.")],
            transitions=[
                pa.TransitionSpec("a", "b", "go", "user", gate_kind="cascade-outcome")
            ],
        )


def test_new_refuses_to_clobber_an_unregistered_script(authoring_repo: Path) -> None:
    # The registered-NAME check is not enough: a capability may hold a
    # hand-written script it has not registered, and the stub path is derived
    # from the command name — so the stamp must pre-flight the PATH too, or it
    # overwrites real predicate code with a fail-closed stub.
    scripts = authoring_repo / ".pkit" / "capabilities" / "design" / "scripts"
    scripts.mkdir(parents=True)
    hand_written = scripts / "screen_detect_drafting.py"
    hand_written.write_text("# real predicate code\n", encoding="utf-8")
    with pytest.raises(pa.ProcessAuthoringError, match="already exist"):
        _stamp_screen(authoring_repo)
    assert hand_written.read_text(encoding="utf-8") == "# real predicate code\n"
    # A refusal writes nothing at all — not even the definition.
    assert not (
        authoring_repo / ".pkit" / "capabilities" / "design" / "schemas" / "screen.yaml"
    ).exists()


def test_handoff_refuses_to_clobber_an_unregistered_seam_script(
    authoring_repo: Path,
) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo)
    scripts = authoring_repo / ".pkit" / "capabilities" / "delivery" / "scripts"
    hand_written = scripts / "my_resolver.py"
    hand_written.write_text("# real resolve seam\n", encoding="utf-8")
    with pytest.raises(pa.ProcessAuthoringError, match="already exist"):
        _handoff_unit(authoring_repo, resolve="my-resolver")
    assert hand_written.read_text(encoding="utf-8") == "# real resolve seam\n"
    # The definition is untouched: the pre-flight runs before the edit.
    definition = load_definition(authoring_repo, "delivery:unit")
    assert "handoff" not in definition.states[0]["depends_on"][0]


def test_new_cli_requires_capability_and_matching_marks(
    authoring_repo: Path, monkeypatch
) -> None:
    monkeypatch.setattr("project_kit.process.resolve_repo_root", lambda: authoring_repo)
    runner = CliRunner()
    result = runner.invoke(
        main, ["process", "new", "orphan", "--state", "only=Only state."]
    )
    assert result.exit_code != 0
    assert "owning capability" in result.output
    result = runner.invoke(
        main,
        [
            "process",
            "new",
            "design:thing",
            "--state",
            "only=Only state.",
            "--entry",
            "ghost",
        ],
    )
    assert result.exit_code != 0
    assert "--entry 'ghost'" in result.output


# --- `process couple`: closed vocab as data + version-unbumped --------------


def test_couple_appends_entry_version_unbumped(authoring_repo: Path) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    result = _couple_unit(authoring_repo)
    assert result.changed
    assert result.warnings == ()

    definition = load_definition(authoring_repo, "delivery:unit")
    (state,) = definition.states
    (entry,) = state["depends_on"]
    assert entry == {
        "upstream": "design:screen",
        "relation": "triggered-by",
        "mode": "push",
        "why": "A unit builds the screen the design process readied.",
    }
    # COR-044 version semantics: an additive inert edit does NOT bump.
    assert _definition_version(authoring_repo, "delivery", "unit") == 1
    # Still lint-clean, and the scaffold's header comment survived the
    # round-trip (comments preserved).
    assert pa.lint_process_block(authoring_repo, definition.data) == []
    text = result.definition_path.read_text(encoding="utf-8")
    assert "yaml-language-server" in text


def test_couple_refuses_outside_the_closed_vocabularies(authoring_repo: Path) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    with pytest.raises(pa.ProcessAuthoringError) as excinfo:
        _couple_unit(authoring_repo, relation="composed-subprocess")
    # The refusal NAMES the closed set as the contract declares it.
    assert "informational" in str(excinfo.value)
    with pytest.raises(pa.ProcessAuthoringError, match="mode 'poll'"):
        _couple_unit(authoring_repo, mode="poll")
    with pytest.raises(pa.ProcessAuthoringError, match="requires a `why`"):
        _couple_unit(authoring_repo, why="   ")
    # A refused couple writes nothing.
    definition = load_definition(authoring_repo, "delivery:unit")
    assert "depends_on" not in definition.states[0]


def test_couple_vocabulary_is_read_as_data(authoring_repo: Path) -> None:
    # Widen the relation enum in the REPO's shape contract: the new value is
    # accepted with no code change — the vocabulary lives in the contract,
    # never hardcoded (COR-044).
    contract_path = (
        authoring_repo / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["$defs"]["depends_on"]["properties"]["relation"]["enum"].append(
        "future-relation"
    )
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    result = _couple_unit(authoring_repo, relation="future-relation")
    assert result.changed
    definition = load_definition(authoring_repo, "delivery:unit")
    assert definition.states[0]["depends_on"][0]["relation"] == "future-relation"


def test_couple_is_idempotent_and_refuses_conflicts(authoring_repo: Path) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    assert _couple_unit(authoring_repo).changed
    again = _couple_unit(authoring_repo)
    assert not again.changed  # identical entry: clean no-op
    definition = load_definition(authoring_repo, "delivery:unit")
    assert len(definition.states[0]["depends_on"]) == 1
    with pytest.raises(pa.ProcessAuthoringError, match="DIFFERENT coupling"):
        _couple_unit(authoring_repo, relation="informational", mode="pull")


def test_couple_validates_the_hosting_state(authoring_repo: Path) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    with pytest.raises(pa.ProcessAuthoringError, match="not a state of"):
        _couple_unit(authoring_repo, state_id="ghost")


def test_couple_warns_on_unresolvable_upstream(authoring_repo: Path) -> None:
    # COR-038: the entry is inert metadata, so an upstream that does not
    # resolve HERE is declarable — warned, never refused.
    _stamp_unit(authoring_repo)
    result = _couple_unit(authoring_repo, upstream="elsewhere:thing")
    assert result.changed
    assert any("does not resolve" in w for w in result.warnings)


# --- `process hand-off`: contract on an existing coupling -------------------


def test_handoff_requires_an_existing_coupling(authoring_repo: Path) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    with pytest.raises(pa.ProcessAuthoringError, match="process couple"):
        _handoff_unit(authoring_repo)


def test_handoff_adds_contract_scaffolds_seams_version_unbumped(
    authoring_repo: Path,
) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo)
    result = _handoff_unit(authoring_repo)
    assert result.changed
    assert [s.command for s in result.stubs] == [
        "unit-handoff-candidates",
        "unit-handoff-resolve",
    ]

    definition = load_definition(authoring_repo, "delivery:unit")
    (entry,) = definition.states[0]["depends_on"]
    assert entry["handoff"] == {
        "trigger": "ready",
        "candidates": {"run": "unit-handoff-candidates"},
        "resolve": {"run": "unit-handoff-resolve"},
    }
    assert pa.lint_process_block(authoring_repo, definition.data) == []
    # Version unbumped (additive report-only edit, COR-044).
    assert _definition_version(authoring_repo, "delivery", "unit") == 1
    # Seam stubs registered in the DECLARING capability + on disk, fail-closed.
    commands = _registered_commands(authoring_repo, "delivery")
    for name in ("unit-handoff-candidates", "unit-handoff-resolve"):
        assert name in commands
        script = (
            authoring_repo / ".pkit" / "capabilities" / "delivery" / commands[name]["script"]
        )
        completed = subprocess.run(
            [sys.executable, str(script), "any", "--json"],
            cwd=str(authoring_repo),
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode != 0


def test_handoff_refuses_a_phantom_trigger_where_upstream_resolves(
    authoring_repo: Path,
) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo)
    with pytest.raises(pa.ProcessAuthoringError, match="phantom trigger"):
        _handoff_unit(authoring_repo, trigger="aproved-typo")
    definition = load_definition(authoring_repo, "delivery:unit")
    assert "handoff" not in definition.states[0]["depends_on"][0]


def test_handoff_warns_when_upstream_unresolvable(authoring_repo: Path) -> None:
    # The trigger cannot be validated against a definition that does not
    # resolve at authoring time: warn and proceed — health reports the
    # contract indeterminate until it resolves (never silently green).
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo, upstream="elsewhere:thing")
    result = _handoff_unit(authoring_repo, upstream="elsewhere:thing")
    assert result.changed
    assert any("INDETERMINATE" in w for w in result.warnings)


def test_handoff_is_idempotent_and_refuses_conflicts(authoring_repo: Path) -> None:
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo)
    assert _handoff_unit(authoring_repo).changed
    again = _handoff_unit(authoring_repo)
    assert not again.changed and again.stubs == ()
    with pytest.raises(pa.ProcessAuthoringError, match="DIFFERENT"):
        _handoff_unit(authoring_repo, trigger="drafting")


def test_handoff_reuses_registered_seam_commands(authoring_repo: Path) -> None:
    # A name the capability already registers is REUSED — no stub scaffolded,
    # no clobber.
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo)
    from ruamel.yaml import YAML

    delivery = authoring_repo / ".pkit" / "capabilities" / "delivery"
    existing = delivery / "scripts" / "existing_candidates.py"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("#!/usr/bin/env python3\nprint('{}')\n", encoding="utf-8")
    package = delivery / "package.yaml"
    rt = YAML(typ="rt")
    data = rt.load(package.read_text(encoding="utf-8"))
    data.setdefault("commands", {})["existing-candidates"] = {
        "script": "scripts/existing_candidates.py",
        "help": "pre-registered",
    }
    with package.open("w", encoding="utf-8") as f:
        rt.dump(data, f)
    result = _handoff_unit(authoring_repo, candidates="existing-candidates")
    assert [s.command for s in result.stubs] == ["unit-handoff-resolve"]
    assert (
        "pre-registered"
        in _registered_commands(authoring_repo, "delivery")["existing-candidates"]["help"]
    )


# --- the interpretation-only check (COR-044 / COR-042 point 5) --------------

_DETECT_SCREEN = (
    "#!/usr/bin/env python3\n"
    "import json, sys, pathlib\n"
    "subj = sys.argv[1]\n"
    "p = pathlib.Path(f'_screen-{subj}')\n"
    "cur = p.read_text().strip() if p.exists() else ''\n"
    "print(json.dumps({'result': cur == STATE, 'reason': f'marker is {cur!r}'}))\n"
)

_CANDIDATES_OK = (
    "#!/usr/bin/env python3\n"
    "import json, pathlib\n"
    "ids = [l.strip() for l in pathlib.Path('_screens').read_text().splitlines() if l.strip()]\n"
    "print(json.dumps({'candidates': ids, 'reason': 'listed'}))\n"
)

_RESOLVE_NONE = (
    "#!/usr/bin/env python3\n"
    "import json\n"
    "print(json.dumps({'downstream': [], 'reason': 'nothing picks this up'}))\n"
)


def _implement_upstream_side(repo: Path) -> None:
    """Implement everything EXCEPT the downstream `resolve` seam: file-backed
    detection and a determinate candidate source. `resolve` stays the
    scaffolded stub."""
    design_scripts = repo / ".pkit" / "capabilities" / "design" / "scripts"
    for state in ("drafting", "ready"):
        script = design_scripts / f"screen_detect_{state}.py"
        script.write_text(
            _DETECT_SCREEN.replace("STATE", repr(state)), encoding="utf-8"
        )
    delivery_scripts = repo / ".pkit" / "capabilities" / "delivery" / "scripts"
    (delivery_scripts / "unit_handoff_candidates.py").write_text(
        _CANDIDATES_OK, encoding="utf-8"
    )
    for script in (*design_scripts.iterdir(), *delivery_scripts.iterdir()):
        script.chmod(script.stat().st_mode | stat.S_IXUSR)


def _implement_seams(repo: Path) -> None:
    """Replace the scaffolded stubs with working implementations: file-backed
    detection, a determinate candidate source, and a resolve that answers
    explicit absence — a fully INTERPRETABLE contract with real misses."""
    _implement_upstream_side(repo)
    resolve = (
        repo / ".pkit" / "capabilities" / "delivery" / "scripts" / "unit_handoff_resolve.py"
    )
    resolve.write_text(_RESOLVE_NONE, encoding="utf-8")
    resolve.chmod(resolve.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def contract_repo(authoring_repo: Path) -> Path:
    """The authored pair with a declared contract, implemented seams, and one
    upstream subject at the trigger with no pickup — interpretable, one miss."""
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo)
    _handoff_unit(authoring_repo)
    _implement_seams(authoring_repo)
    (authoring_repo / "_screens").write_text("screen-1\n", encoding="utf-8")
    (authoring_repo / "_screen-screen-1").write_text("ready", encoding="utf-8")
    return authoring_repo


def _invoke_health(repo: Path, monkeypatch, *args: str):
    monkeypatch.setattr("project_kit.process.resolve_repo_root", lambda: repo)
    return CliRunner().invoke(main, ["process", "health", *args])


def test_interpretation_only_does_not_count_misses(contract_repo, monkeypatch) -> None:
    # The default run sees the miss (exit contract UNCHANGED, COR-042)...
    default = _invoke_health(contract_repo, monkeypatch)
    assert default.exit_code == 1
    assert "1 missed, 0 indeterminate" in default.output
    # ...the interpretation-only variant exits CLEAN on the same reality: the
    # contract resolves and its seams execute — a real miss is not an
    # authoring failure (COR-044: miss-count is never the authoring
    # done-signal).
    interp = _invoke_health(contract_repo, monkeypatch, "--interpretation-only")
    assert interp.exit_code == 0, interp.output
    assert "missed" not in interp.output
    assert "0 indeterminate" in interp.output
    assert "interpretable" in interp.output


def test_interpretation_only_json_carries_no_miss_surface(
    contract_repo, monkeypatch
) -> None:
    result = _invoke_health(contract_repo, monkeypatch, "--interpretation-only", "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["totals"] == {"indeterminate": 0}
    (contract,) = payload["contracts"]
    assert set(contract) == {
        "upstream",
        "downstream",
        "trigger",
        "state",
        "indeterminate",
        "counts",
    }
    # No miss surface anywhere — not even derivably (no at_trigger/satisfied).
    assert contract["counts"] == {"indeterminate": 0}
    assert "misses" not in json.dumps(payload)


def test_interpretation_only_reports_indeterminates(contract_repo, monkeypatch) -> None:
    # Break the candidate source: the contract stops being interpretable and
    # the variant exits non-zero, naming the indeterminacy.
    scripts = contract_repo / ".pkit" / "capabilities" / "delivery" / "scripts"
    (scripts / "unit_handoff_candidates.py").write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.exit(1)\n", encoding="utf-8"
    )
    result = _invoke_health(contract_repo, monkeypatch, "--interpretation-only")
    assert result.exit_code == 1
    assert "1 indeterminate" in result.output
    assert "contract indeterminate" in result.output


def test_interpretation_only_consumes_the_health_walker(
    contract_repo, monkeypatch
) -> None:
    # COR-042 point 5's design-once rule: the variant is a CONSUMER of the
    # existing walker — the same `build_report` walk, re-rendered — never a
    # parallel contract-walker. Pin it by interposing on the walker and
    # asserting the variant's output derives from what it returned.
    calls: list = []
    real_build_report = ph.build_report

    def spying_build_report(repo_root, focus=None):
        calls.append(focus)
        return real_build_report(repo_root, focus=focus)

    monkeypatch.setattr(ph, "build_report", spying_build_report)
    result = _invoke_health(
        contract_repo, monkeypatch, "--interpretation-only", "--process", "delivery:unit"
    )
    assert result.exit_code == 0, result.output
    assert calls == ["delivery:unit"]  # one walk, focus threaded through


def test_interpretation_only_module_has_no_second_walker() -> None:
    # The variant lives beside the walker and calls no walk of its own: the
    # view builder and both renderers consume a HealthReport.
    import inspect

    for consumer in (
        ph.build_interpretation,
        ph.render_interpretation_narrative,
        ph.render_interpretation_json,
    ):
        source = inspect.getsource(consumer)
        assert "build_report" not in source
        assert "collect_contracts" not in source
        assert "evaluate_contract" not in source


# --- the STATIC seam check: interpretability can't depend on who's at the
# trigger (COR-044's done-signal) -------------------------------------------


@pytest.fixture
def unexercised_contract_repo(authoring_repo: Path) -> Path:
    """The authored pair with a declared contract, an EMPTY candidate set, and
    the `resolve` seam still the scaffolded stub.

    Nobody is at the trigger, so the walk never runs `resolve` — the case where
    a purely runtime interpretability check has nothing to say."""
    _stamp_screen(authoring_repo)
    _stamp_unit(authoring_repo)
    _couple_unit(authoring_repo)
    _handoff_unit(authoring_repo)
    _implement_upstream_side(authoring_repo)
    (authoring_repo / "_screens").write_text("", encoding="utf-8")
    return authoring_repo


def test_interpretation_only_catches_an_unexercised_stub_seam(
    unexercised_contract_repo, monkeypatch
) -> None:
    # The done-signal must not read green on a seam that was never written just
    # because no subject happened to exercise it.
    result = _invoke_health(
        unexercised_contract_repo, monkeypatch, "--interpretation-only"
    )
    assert result.exit_code == 1, result.output
    assert "resolve seam" in result.output
    assert "still the scaffolded stub" in result.output


def test_default_health_contract_is_untouched_by_the_static_check(
    unexercised_contract_repo, monkeypatch
) -> None:
    # COR-042's exit contract is misses + RUNTIME indeterminates. The static
    # seam check belongs to the authoring view only: the same reality that
    # fails --interpretation-only leaves the default run clean.
    result = _invoke_health(unexercised_contract_repo, monkeypatch)
    assert result.exit_code == 0, result.output
    assert "0 missed, 0 indeterminate" in result.output


def test_interpretation_only_clean_when_seams_are_implemented_and_idle(
    unexercised_contract_repo, monkeypatch
) -> None:
    # The converse: fully implemented seams with an empty candidate set is the
    # authoring done-state, and it reports clean.
    _implement_seams(unexercised_contract_repo)
    result = _invoke_health(
        unexercised_contract_repo, monkeypatch, "--interpretation-only"
    )
    assert result.exit_code == 0, result.output
    assert "0 indeterminate" in result.output
    assert "interpretable" in result.output


def test_interpretation_only_reports_missing_and_unregistered_seams(
    unexercised_contract_repo, monkeypatch
) -> None:
    _implement_seams(unexercised_contract_repo)
    scripts = unexercised_contract_repo / ".pkit" / "capabilities" / "delivery" / "scripts"
    (scripts / "unit_handoff_resolve.py").unlink()
    result = _invoke_health(
        unexercised_contract_repo, monkeypatch, "--interpretation-only"
    )
    assert result.exit_code == 1, result.output
    assert "not on disk" in result.output

    # Drop the registration too: the seam then names a command the declaring
    # capability does not register.
    package = unexercised_contract_repo / ".pkit" / "capabilities" / "delivery" / "package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "unit-handoff-resolve", "unit-handoff-resolve-renamed"
        ),
        encoding="utf-8",
    )
    result = _invoke_health(
        unexercised_contract_repo, monkeypatch, "--interpretation-only"
    )
    assert result.exit_code == 1, result.output
    assert "does not register" in result.output


def test_interpretation_json_carries_the_static_findings(
    unexercised_contract_repo, monkeypatch
) -> None:
    result = _invoke_health(
        unexercised_contract_repo, monkeypatch, "--interpretation-only", "--json"
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["totals"]["indeterminate"] == 1
    (contract,) = payload["contracts"]
    (finding,) = contract["indeterminate"]
    assert finding["subject"] is None
    assert "scaffolded stub" in finding["reason"]
    assert "misses" not in json.dumps(payload)


def test_full_stack_via_cli_commands(authoring_repo: Path, monkeypatch) -> None:
    # The whole authoring flow through the CLI grammar the README records:
    # new -> couple -> hand-off -> interpretation-only, on one repo.
    monkeypatch.setattr("project_kit.process.resolve_repo_root", lambda: authoring_repo)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "process", "new", "design:screen",
            "--cardinality", "keyed", "--key", "screen-id",
            "--state", "drafting=Drafting the screen design.",
            "--state", "ready=Ready to hand off.",
            "--entry", "drafting", "--terminal", "ready",
            "--transition", "drafting:ready:approve",
        ],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        main,
        [
            "process", "new", "delivery:unit",
            "--state", "building=Building a unit.",
            "--entry", "building",
        ],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        main,
        [
            "process", "couple", "delivery:unit",
            "--state", "building",
            "--upstream", "design:screen",
            "--relation", "triggered-by",
            "--mode", "push",
            "--why", "A unit builds the readied screen.",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "version unchanged" in result.output

    result = runner.invoke(
        main,
        [
            "process", "hand-off", "delivery:unit",
            "--upstream", "design:screen",
            "--trigger", "ready",
            "--candidates", "unit-handoff-candidates",
            "--resolve", "unit-handoff-resolve",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "version unchanged" in result.output

    _implement_seams(authoring_repo)
    (authoring_repo / "_screens").write_text("", encoding="utf-8")
    result = runner.invoke(main, ["process", "health", "--interpretation-only"])
    assert result.exit_code == 0, result.output
    assert "0 indeterminate" in result.output
