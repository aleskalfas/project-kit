"""The validator registry behind `pkit validate` (ADR-058; #986).

- the backbone's members run in registry order and print one section each;
- a capability's validator names a `commands:` leaf that declares the query
  contract; it runs after the backbone's members with `--json`, offline-marked,
  in its own process group, and its errors fail the umbrella; no answer — a
  leaf without the declaration, a timeout, a half-formed document — is an
  error, never a clean pass; an environment not provisioned — uv's report on
  standard error, pinned as uv prints it — is named as such, with `pkit sync`;
- `--only` / `--skip` address members, `--no-refs` is `--skip refs`;
- warnings, information and reports print and never fail; errors do;
- every focused surface still works alone with the exit it always had;
- the data member walks the project-owned folders under `.pkit/` and skips
  what nothing claims, unreadable files included;
- the refs member classifies drift as a warning, the rest as errors, and
  reads a bracketed `reads.patterns` declaration the way the deploy does.
"""

from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import command_runner, refs, validators
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

BACKBONE_ORDER = [
    "manifests",
    "schemas",
    "configuration",
    "packages",
    "connections",
    "versions",
    "friction",
    "rule-sets",
    "decisions",
    "refs",
    "process",
    "data",
]

CLEAN_ANSWER = {"summary": ["3 thing(s) checked; 0 error(s)."], "findings": []}


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def _leaf(
    token: str,
    *,
    script: str = "scripts/check.py",
    help_text: str = "Check things.",
    contract: bool = True,
) -> str:
    """One `commands:` leaf as YAML, declaring the query contract unless told not to."""
    declaration = "    query-contract: true\n" if contract else ""
    return f"  {token}:\n    script: {script}\n    help: {help_text}\n{declaration}"


def _register(
    root: Path,
    name: str,
    *,
    commands_yaml: str = "commands:\n" + _leaf("check"),
    validators_yaml: str = "validators:\n  thing:\n    command: check\n",
    script_body: str | None = None,
    script_path: str = "scripts/check.py",
) -> Path:
    """A synthetic capability at `.pkit/capabilities/<name>/` declaring `commands:`
    and `validators:`, registered in the backbone manifest; `script_body` writes
    an executable script. The defaults register `<name>:thing` on the leaf
    `check`, which declares the query contract."""
    cap_dir = root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"schema_version: 2\ncomponent:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n"
        f'description: Synthetic capability for validator tests.\nrequires_backbone: ">=0.1.0"\n'
        f"{commands_yaml}{validators_yaml}",
        encoding="utf-8",
    )
    if script_body is not None:
        script = cap_dir / script_path
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("#!/usr/bin/env python3\n" + script_body, encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability", name=name, manifest=f".pkit/capabilities/{name}/manifest.yaml"
        )
    )
    write_backbone_manifest(root, backbone)
    return cap_dir


def _answering(document: object, *, exit_code: int = 0) -> str:
    return f"import json, sys\nprint(json.dumps({document!r}))\nsys.exit({exit_code})\n"


def _sections(output: str) -> list[str]:
    """The member headings in the order printed (two-space indent, no further indent)."""
    return [
        line[2:]
        for line in output.splitlines()
        if line.startswith("  ")
        and not line.startswith("    ")
        and line[2:3].isalpha()
        and not line.startswith("  All checks")
        and "validator(s) ran" not in line
        and "error(s) found" not in line
    ]


def _member(root: Path, name: str) -> validators.Validator:
    [member] = [v for v in validators.registered_validators(root) if v.name == name]
    return member


# --- the registry ------------------------------------------------------------


def test_backbone_members_are_registered_in_dependence_order(adopter: AdopterRepo) -> None:
    registered = validators.registered_validators(adopter.root)
    assert [v.name for v in registered] == BACKBONE_ORDER
    assert all(v.owner == validators.BACKBONE_OWNER for v in registered)
    assert [v.order for v in registered] == sorted(v.order for v in registered)


def test_capability_validators_sort_after_the_backbone_by_order_then_name(
    adopter: AdopterRepo,
) -> None:
    _register(
        adopter.root,
        "zeta",
        commands_yaml="commands:\n"
        + _leaf("late", help_text="Late.")
        + _leaf("early", help_text="Early."),
        validators_yaml="validators:\n  late:\n    command: late\n  early:\n    command: early\n    order: 5\n",
    )
    _register(
        adopter.root,
        "alpha",
        commands_yaml=(
            "commands:\n  citations:\n    check:\n      script: scripts/check.py\n"
            "      help: Every citation resolves.\n      query-contract: true\n"
        ),
        validators_yaml="validators:\n  citations:\n    command: citations check\n",
    )
    registered = validators.registered_validators(adopter.root)
    names = [v.name for v in registered]
    # `order: 5` sorts among the backbone's members; the default sorts after every one.
    assert names[0] == "zeta:early"
    assert names[1:13] == BACKBONE_ORDER
    assert names[13:] == ["alpha:citations", "zeta:late"]
    # The help is the leaf's — a nested leaf resolves like a top-level one.
    assert _member(adopter.root, "alpha:citations").help == "Every citation resolves."


def test_capability_block_is_read_defensively(adopter: AdopterRepo) -> None:
    _register(adopter.root, "odd", validators_yaml="validators: [not, a, mapping]\n")
    _register(
        adopter.root,
        "half",
        commands_yaml="commands:\n" + _leaf("check") + _leaf("bare", contract=False),
        validators_yaml="validators:\n  nocommand:\n    order: 1\n"
        "  nowhere:\n    command: missing\n"
        "  ok:\n    command: check\n    order: not-an-int\n"
        "  undeclared:\n    command: bare\n",
    )
    registered = {v.name: v for v in validators.registered_validators(adopter.root)}
    assert (
        "half:ok" in registered
        and registered["half:ok"].order == validators.CAPABILITY_ORDER_DEFAULT
    )
    # No command, or a command that names no leaf: the packages member's finding, not a member.
    assert "half:nocommand" not in registered and "half:nowhere" not in registered
    # A leaf without the declaration is a member — refused when run, never skipped silently.
    assert "half:undeclared" in registered
    assert not any(name.startswith("odd:") for name in registered)


def test_select_addresses_members_and_refuses_unknown_names(adopter: AdopterRepo) -> None:
    registered = validators.registered_validators(adopter.root)
    only = validators.select(registered, only=["refs", "manifests"])
    assert [v.name for v in only] == ["manifests", "refs"]  # registry order, not argument order
    skipped = validators.select(registered, skip=["refs"])
    assert "refs" not in [v.name for v in skipped] and len(skipped) == len(registered) - 1
    with pytest.raises(ValueError, match="unknown validator\\(s\\) 'nope'"):
        validators.select(registered, only=["nope"])


def test_a_computation_several_members_read_runs_once_per_run(tmp_path: Path) -> None:
    """Inside `run_all` each key is computed once and shared; outside, every call computes."""
    computed: list[str] = []

    def compute(key: str) -> str:
        computed.append(key)
        return f"value of {key}"

    def member(root: Path) -> validators.Outcome:
        values = [validators.once_per_run(key, lambda k=key: compute(k)) for key in ("a", "a", "b")]
        return validators.Outcome(summary=tuple(values))

    members = [validators.Validator(name, member, order) for order, name in enumerate(["x", "y"])]
    results = validators.run_all(tmp_path, members)
    assert computed == ["a", "b"]
    assert all(r.outcome.summary == ("value of a", "value of a", "value of b") for r in results)

    validators.run_all(tmp_path, members)  # a new run computes afresh
    assert computed == ["a", "b", "a", "b"]
    validators.once_per_run("a", lambda: compute("a"))  # outside a run: no sharing
    validators.once_per_run("a", lambda: compute("a"))
    assert computed == ["a", "b", "a", "b", "a", "a"]


# --- the umbrella command ----------------------------------------------------


def test_pkit_validate_prints_one_section_per_member_in_order_then_one_summary(
    adopter: AdopterRepo,
) -> None:
    result = CliRunner().invoke(main, ["validate"])
    assert result.exit_code == 0, result.output
    assert _sections(result.output) == BACKBONE_ORDER
    assert f"  {len(BACKBONE_ORDER)} validator(s) ran; 0 error(s)" in result.output
    assert result.output.rstrip().endswith("All checks passed.")


def test_only_and_skip_and_the_legacy_no_refs(adopter: AdopterRepo) -> None:
    only = CliRunner().invoke(main, ["validate", "--only", "friction", "--only", "manifests"])
    assert only.exit_code == 0, only.output
    assert _sections(only.output) == ["manifests", "friction"]
    assert "2 validator(s) ran" in only.output

    skipped = CliRunner().invoke(main, ["validate", "--skip", "refs", "--skip", "data"])
    assert skipped.exit_code == 0, skipped.output
    assert _sections(skipped.output) == [n for n in BACKBONE_ORDER if n not in ("refs", "data")]

    legacy = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert _sections(legacy.output) == [n for n in BACKBONE_ORDER if n != "refs"]

    unknown = CliRunner().invoke(main, ["validate", "--only", "nope"])
    assert unknown.exit_code != 0
    assert "unknown validator(s) 'nope'" in unknown.output
    assert "registered: manifests, schemas" in unknown.output


def test_only_errors_fail_the_umbrella(adopter: AdopterRepo) -> None:
    config = adopter.root / ".pkit" / "project" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("docs:\n  internal: nowhere\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "warning  .pkit/project/config.yaml:/docs/internal" in result.output
    assert "0 error(s), 1 warning(s)" in result.output
    assert "All checks passed." in result.output

    (adopter.root / ".pkit" / "manifest.yaml").unlink()
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    assert "error    .pkit/manifest.yaml" in result.output
    assert result.output.rstrip().endswith("error(s) found.")
    assert "All checks passed." not in result.output


# --- a capability's validator: a query command -------------------------------


def test_a_capability_validator_runs_after_the_backbone_and_its_errors_fail(
    adopter: AdopterRepo,
) -> None:
    answer = {
        "summary": ["2 record(s) checked; 1 error(s), 1 info(s)."],
        "findings": [
            {"severity": "error", "location": "docs/a.md", "message": "cites nothing."},
            {"severity": "info", "location": "docs/b.md", "message": "fine."},
        ],
    }
    _register(
        adopter.root,
        "evidence-like",
        commands_yaml="commands:\n" + _leaf("check", help_text="Every citation resolves."),
        validators_yaml="validators:\n  citations:\n    command: check\n",
        script_body=_answering(answer),
    )
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    assert _sections(result.output)[-1] == "evidence-like:citations"
    section = result.output.split("\n  evidence-like:citations\n")[1]
    assert section.startswith("    2 record(s) checked; 1 error(s), 1 info(s).\n")
    assert "error    docs/a.md\n      → cites nothing." in section
    assert "info     docs/b.md\n      → fine." in section
    assert "1 error(s), 0 warning(s), 1 info(s), 0 report(s)." in result.output

    clean = CliRunner().invoke(main, ["validate", "--only", "evidence-like:citations"])
    assert clean.exit_code == 1  # same command, same answer: the member alone fails too


def test_the_runner_passes_json_and_marks_the_run_offline(adopter: AdopterRepo) -> None:
    _register(
        adopter.root,
        "cap",
        script_body=(
            "import json, os, sys\n"
            'print(json.dumps({"summary": [" ".join(sys.argv[1:]), os.environ.get("PKIT_OFFLINE", ""),'
            ' os.environ.get("UV_OFFLINE", ""), os.getcwd()], "findings": []}))\n'
        ),
    )
    outcome = _member(adopter.root, "cap:thing").run(adopter.root)
    assert outcome.findings == ()
    assert outcome.summary == ("--json", "1", "1", str(adopter.root.resolve()))


@pytest.mark.parametrize(
    ("script_body", "expect"),
    [
        (_answering(CLEAN_ANSWER, exit_code=3), "exited 3"),
        ("print('not json')\n", "did not print a JSON document"),
        (
            "import sys\nsys.stdout.buffer.write(b'\\xff\\xfe not json')\n",
            "did not print a JSON document",
        ),
        (_answering([1, 2]), "printed a list, not a findings document"),
        (_answering({}), "answered without a `summary` list"),
        (_answering({"summary": "x", "findings": []}), "answered without a `summary` list"),
        (_answering({"summary": [], "findings": "oops"}), "answered without a `findings` list"),
        (
            _answering({"summary": [], "findings": {"error": "crashed"}}),
            "answered without a `findings` list",
        ),
        (
            _answering(
                {
                    "summary": [],
                    "findings": [{"severity": "fatal", "location": "x", "message": "y"}],
                }
            ),
            "malformed finding at index 0",
        ),
        (None, "does not exist"),
    ],
)
def test_no_answer_from_a_capability_validator_is_an_error(
    adopter: AdopterRepo, script_body: str | None, expect: str
) -> None:
    _register(adopter.root, "cap", script_body=script_body)
    result = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert result.exit_code == 1, result.output
    assert "no answer." in result.output
    assert "error    .pkit/capabilities/cap/package.yaml:/validators/thing/command" in result.output
    assert expect in result.output


# uv's standard error when an offline run misses its cache, verbatim from uv
# 0.9.30: a registry package never fetched (the resolver's hint — the same hint
# ends the report when only the package's index page is cached), and a
# direct-URL dependency whose file was never downloaded (the client's error).
# `test_provisioning` meets the first under the real uv.
UV_MISSING_REGISTRY_PACKAGE = """\
  × No solution found when resolving script dependencies:
  ╰─▶ Because ruamel-yaml was not found in the cache and you require
      ruamel-yaml>=0.18, we can conclude that your requirements are
      unsatisfiable.

      hint: Packages were unavailable because the network was disabled. When
      the network is disabled, registry packages may only be read from the
      cache.
"""
UV_MISSING_DIRECT_URL = """\
  × Failed to download `pkit-probe-dep @
  │ http://127.0.0.1:9/pkit_probe_dep-1.0-py3-none-any.whl`
  ╰─▶ Network connectivity is disabled, but the requested data wasn't found in
      the cache for: `http://127.0.0.1:9/pkit_probe_dep-1.0-py3-none-any.whl`
"""

NOT_PROVISIONED_FINDING = (
    "command 'check': environment not provisioned — run `pkit sync` (its dependencies "
    "are not in uv's cache, and a query runs offline)."
)


NO_DOCUMENT = "command 'check' did not print a JSON document on its standard output."


def _ended(
    ending: command_runner.Ending, stderr: str, returncode: int = 1
) -> command_runner.CommandRun:
    return command_runner.CommandRun(ending, 30, returncode=returncode, stderr=stderr)


@pytest.mark.parametrize("stderr", [UV_MISSING_REGISTRY_PACKAGE, UV_MISSING_DIRECT_URL])
def test_uv_s_offline_miss_is_an_environment_not_provisioned(stderr: str) -> None:
    run = _ended(command_runner.Ending.ABNORMAL_EXIT, stderr)
    assert validators.not_provisioned(run)
    assert validators.why_no_answer(run, "check") == NOT_PROVISIONED_FINDING


def test_a_wrapped_report_is_still_recognised() -> None:
    # uv wraps to the width it sees: the phrase may break anywhere.
    stderr = "hint: Packages were unavailable because the\n   network was disabled."
    assert validators.not_provisioned(_ended(command_runner.Ending.ABNORMAL_EXIT, stderr))


@pytest.mark.parametrize(
    ("run", "message"),
    [
        (
            _ended(command_runner.Ending.ABNORMAL_EXIT, "Traceback …\nKeyError: 'x'\n"),
            "command 'check' exited 1: KeyError: 'x'",
        ),
        (_ended(command_runner.Ending.UNPARSABLE, "", returncode=0), NO_DOCUMENT),
        # uv's text on an ending that is not an exit is not read.
        (
            _ended(command_runner.Ending.UNPARSABLE, UV_MISSING_REGISTRY_PACKAGE, returncode=0),
            NO_DOCUMENT,
        ),
    ],
)
def test_any_other_no_answer_keeps_its_own_message(
    run: command_runner.CommandRun, message: str
) -> None:
    assert not validators.not_provisioned(run)
    assert validators.why_no_answer(run, "check") == message


def test_the_finding_names_pkit_sync_and_differs_from_a_command_answering_nothing(
    adopter: AdopterRepo,
) -> None:
    uv_report = UV_MISSING_REGISTRY_PACKAGE.encode()
    cap_dir = _register(
        adopter.root,
        "cap",
        script_body=f"import sys\nsys.stderr.buffer.write({uv_report!r})\nsys.exit(1)\n",
    )
    result = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert result.exit_code == 1, result.output
    assert "error    .pkit/capabilities/cap/package.yaml:/validators/thing/command" in result.output
    assert f"→ {NOT_PROVISIONED_FINDING}" in result.output

    # Exits 0 and prints nothing: no answer, and not the provisioning finding.
    (cap_dir / "scripts" / "check.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    silent = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert silent.exit_code == 1, silent.output
    assert "environment not provisioned" not in silent.output
    assert "command 'check' did not print a JSON document" in silent.output


def test_a_command_without_the_declaration_is_refused_by_the_runner_and_reported(
    adopter: AdopterRepo,
) -> None:
    _register(
        adopter.root,
        "cap",
        commands_yaml="commands:\n" + _leaf("check", contract=False),
        script_body=_answering(CLEAN_ANSWER),
    )
    # The runner's backstop: the script would answer cleanly, and is never started.
    refused = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert refused.exit_code == 1, refused.output
    assert "no answer." in refused.output
    assert (
        "command 'check' does not declare the query contract (`query-contract: true`"
        in refused.output
    )
    # The packages member reports the same entry, where the author can fix it.
    packages = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert packages.exit_code == 1, packages.output
    assert (
        "error    .pkit/capabilities/cap/package.yaml:/validators/thing/command" in packages.output
    )
    assert "validator 'thing' names command 'check', which does not declare the query contract" in (
        packages.output
    )


def test_a_timeout_kills_the_process_group_and_does_not_wait_on_the_grandchild(
    adopter: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A `uv run --script` shebang runs the interpreter as a grandchild; here the
    # script starts one itself, sharing the pipes, and both outlive the bound.
    _register(
        adopter.root,
        "cap",
        script_body=(
            "import subprocess, sys, time\n"
            'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
            'open(sys.argv[0] + ".pid", "w").write(str(child.pid))\n'
            "time.sleep(60)\n"
        ),
    )
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    started = time.monotonic()
    outcome = _member(adopter.root, "cap:thing").run(adopter.root)
    elapsed = time.monotonic() - started
    assert elapsed < 15, elapsed  # not the grandchild's sixty seconds
    assert [f.message for f in outcome.errors] == ["command 'check' did not answer within 1 s."]
    grandchild = int(
        (adopter.root / ".pkit" / "capabilities" / "cap" / "scripts" / "check.py.pid").read_text()
    )
    for _ in range(50):
        try:
            os.kill(grandchild, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        os.kill(grandchild, 9)
        pytest.fail("the grandchild survived the process-group kill")


def test_a_clean_capability_validator_passes_and_its_summary_prints(adopter: AdopterRepo) -> None:
    _register(adopter.root, "cap", script_body=_answering(CLEAN_ANSWER))
    result = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert result.exit_code == 0, result.output
    assert "\n  cap:thing\n    3 thing(s) checked; 0 error(s).\n" in result.output


def test_the_packages_member_reports_a_validator_naming_no_command(adopter: AdopterRepo) -> None:
    _register(adopter.root, "cap", validators_yaml="validators:\n  thing:\n    command: nope\n")
    assert "cap:thing" not in [v.name for v in validators.registered_validators(adopter.root)]
    result = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert result.exit_code == 1, result.output
    assert ".pkit/capabilities/cap/package.yaml:/validators/thing/command" in result.output
    assert (
        "validator 'thing': command 'nope' is not declared in `commands:` (declared: ['check'])."
        in (result.output)
    )


def test_an_unknown_key_inside_a_validator_entry_is_an_error_naming_the_nearest_known(
    adopter: AdopterRepo,
) -> None:
    _register(
        adopter.root,
        "cap",
        validators_yaml="validators:\n  thing:\n    command: check\n    ordre: 5\n",
        script_body=_answering(CLEAN_ANSWER),
    )
    result = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert result.exit_code == 1, result.output
    assert "error    .pkit/capabilities/cap/package.yaml:/validators/thing/ordre" in result.output
    assert "unknown key 'ordre'; did you mean 'order'?" in result.output


# --- the focused surfaces still work alone -----------------------------------


def test_each_focused_surface_still_runs_alone(adopter: AdopterRepo) -> None:
    runner = CliRunner()
    for args in (["schemas", "validate"], ["decisions", "validate"]):
        result = runner.invoke(main, args)
        assert result.exit_code == 0, (args, result.output)
        assert "validator(s) ran" not in result.output  # the umbrella's summary is the umbrella's
    # Given drift, the focused surface fails on any finding, as it always did,
    # while the umbrella's member reports the same drift as a warning.
    _agent(adopter.root, "drifter", "reads:\n  records:\n    - COR-001\n", "Cites nothing.")
    focused = runner.invoke(main, ["refs", "validate"])
    assert focused.exit_code == 1 and "Reference validation" in focused.output
    assert "validator(s) ran" not in focused.output
    assert runner.invoke(main, ["validate", "--only", "refs"]).exit_code == 0
    scope = adopter.root / "data"
    scope.mkdir()
    (scope / "loose.yaml").write_text("a: 1\n", encoding="utf-8")
    data = runner.invoke(main, ["data", "validate", str(scope)])
    assert data.exit_code == 1  # a named file nothing binds is a finding for the focused surface
    assert "no schema binding found" in data.output


def test_the_data_member_skips_what_nothing_binds_and_checks_what_something_does(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    notes = adopter.root / "notes"
    notes.mkdir()
    (notes / "loose.yaml").write_text("a: 1\n", encoding="utf-8")
    # Unreadable and unclaimed — a multi-document manifest — is not adopter data either.
    (notes / "manifest.yaml").write_text("a: 1\n---\nb: 2\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["validate", "--only", "data"])
    assert result.exit_code == 0, result.output
    assert "no adopter data file is bound to a capability schema." in result.output
    # The focused surface, handed the unreadable file by name, still reports it.
    focused = CliRunner().invoke(main, ["data", "validate", str(notes / "manifest.yaml")])
    assert focused.exit_code == 1 and "YAML parse error" in focused.output

    bad_record = "pkit_schema: evidence:evidence-record\nschema_version: 1\nrecords: 7\n"
    (notes / "evidence.yaml").write_text(bad_record, encoding="utf-8")
    result = CliRunner().invoke(main, ["validate", "--only", "data"])
    assert result.exit_code == 1, result.output
    assert "1 bound data file(s) checked; " in result.output
    assert "error    notes/evidence.yaml" in result.output
    # A dot-directory is never walked, nor a kit-managed folder under `.pkit/`.
    (adopter.root / ".notes").mkdir()
    (adopter.root / ".notes" / "evidence.yaml").write_text("pkit_schema: evidence:nope\n")
    managed = adopter.root / ".pkit" / "capabilities" / "evidence" / "skills"
    managed.mkdir(parents=True, exist_ok=True)
    (managed / "evidence.yaml").write_text("pkit_schema: evidence:nope\n")
    again = CliRunner().invoke(main, ["validate", "--only", "data"])
    assert "1 bound data file(s) checked; " in again.output
    # A project-owned folder under `.pkit/` is adopter data and is walked.
    owned = adopter.root / ".pkit" / "capabilities" / "evidence" / "project"
    owned.mkdir(parents=True, exist_ok=True)
    (owned / "evidence.yaml").write_text(bad_record, encoding="utf-8")
    # Unreadable but claimed by a glob (`**/evidence.yaml`): the failure is the finding.
    (notes / "deeper").mkdir()
    (notes / "deeper" / "evidence.yaml").write_text("a: 1\n---\nb: 2\n", encoding="utf-8")
    third = CliRunner().invoke(main, ["validate", "--only", "data"])
    assert "3 bound data file(s) checked; " in third.output
    assert "error    .pkit/capabilities/evidence/project/evidence.yaml" in third.output
    assert "error    notes/deeper/evidence.yaml\n      → YAML parse error" in third.output


def test_the_data_member_lists_the_repository_through_the_working_trees_one_listing(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The files git sees, as friction discovery lists them (ADR-057 point 2): a file git
    ignores and a file beneath a nested repository are not the repository's; the order
    is a walk's — a folder's files before its sub-folders, each by name."""
    import subprocess

    from project_kit import data_validate

    adopter = make_adopter_repo()
    root = adopter.root
    adopter.write(
        {
            ".gitignore": "build/\n",
            "build/out.yaml": "a: 1\n",
            "b.yaml": "a: 1\n",
            "a/z.yaml": "a: 1\n",
            "a/sub/y.yaml": "a: 1\n",
            ".pkit/project/extra.yaml": "a: 1\n",
        }
    )
    nested = root / "vendored"
    nested.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    (nested / "inside.yaml").write_text("a: 1\n", encoding="utf-8")
    listed = [
        p.relative_to(root).as_posix() for p in data_validate.discover_repository_data_files(root)
    ]
    assert [p for p in listed if not p.startswith(".pkit/")] == [
        "b.yaml",
        "a/z.yaml",
        "a/sub/y.yaml",
    ]
    assert ".pkit/project/extra.yaml" in listed
    assert listed.index(".pkit/project/extra.yaml") < listed.index("a/z.yaml")


# --- the refs member: drift warns, breakage fails, patterns read both ways ----


def _agent(root: Path, name: str, front_matter: str, body: str) -> Path:
    path = root / ".pkit" / "agents" / "project" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\n{front_matter}---\n\n{body}\n", encoding="utf-8")
    return path


def test_bracketed_pattern_declarations_are_read_the_way_the_deploy_reads_them(
    adopter: AdopterRepo,
) -> None:
    _agent(
        adopter.root,
        "producer",
        "reads:\n  patterns:\n    - <project-conventions>\n",
        "Read the `<project-conventions>` corpus before writing.",
    )
    _agent(
        adopter.root,
        "reviewer",
        "reads:\n  patterns:\n    - project-conventions\n",
        "Read the `<project-conventions>` corpus before reviewing.",
    )
    _agent(adopter.root, "silent", "reads:\n  patterns:\n    - code-paths\n", "Says nothing.")
    diagnoses = [
        i.diagnosis for i in refs.validate_corpus(adopter.root) if "agents/project" in i.location
    ]
    assert diagnoses == [
        "frontmatter declares pattern 'code-paths' but it is not referenced anywhere."
    ]


def test_refs_member_warns_on_drift_and_fails_on_a_hook_nobody_answers(
    adopter: AdopterRepo,
) -> None:
    _agent(adopter.root, "drifter", "reads:\n  records:\n    - COR-001\n", "Cites nothing.")
    outcome = refs.outcome(adopter.root)
    project = [f for f in outcome.findings if "agents/project" in f.location]
    assert [(f.severity, f.location) for f in project] == [
        (validators.Severity.WARNING, ".pkit/agents/project/drifter.md")
    ]
    assert outcome.errors == ()
    assert "0 error(s)," in outcome.summary[0] and "hook provider(s) checked" in outcome.summary[0]

    _agent(adopter.root, "needy", "needs:\n  - workflow.nothing\n", "Needs `workflow.nothing`.")
    outcome = refs.outcome(adopter.root)
    assert validators.Severity.ERROR in {f.severity for f in outcome.findings}
    umbrella = CliRunner().invoke(main, ["validate", "--only", "refs"])
    assert umbrella.exit_code == 1, umbrella.output
    focused = CliRunner().invoke(main, ["refs", "validate"])
    assert focused.exit_code == 1  # the focused surface fails on any finding, as before

    (adopter.root / ".pkit" / "agents" / "project" / "needy.md").unlink()
    assert CliRunner().invoke(main, ["validate", "--only", "refs"]).exit_code == 0
    assert (
        CliRunner().invoke(main, ["refs", "validate"]).exit_code == 1
    )  # drift alone still fails it


# --- the answer document ------------------------------------------------------


def test_parse_answer_keeps_labels_and_every_severity() -> None:
    document = {
        "summary": ["one", 2],
        "findings": [
            {"severity": s, "location": f"f{i}", "message": "m", "label": "rel"}
            for i, s in enumerate(("error", "warning", "info", "report"))
        ],
    }
    outcome = validators.parse_answer(json.dumps(document), location="loc", command="c")
    assert outcome.summary == ("one", "2")
    assert [f.severity.value for f in outcome.findings] == ["error", "warning", "info", "report"]
    assert all(f.label == "rel" for f in outcome.findings)
    assert len(outcome.errors) == 1


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"findings": []},
        {"summary": []},
        {"summary": "x", "findings": []},
        {"summary": [], "findings": None},
        {"summary": [], "findings": {"error": "crashed"}},
        {"summary": None, "findings": []},
    ],
    ids=[
        "empty",
        "no-summary",
        "no-findings",
        "summary-string",
        "findings-null",
        "findings-map",
        "summary-null",
    ],
)
def test_parse_answer_fails_closed_on_a_half_formed_document(document: object) -> None:
    outcome = validators.parse_answer(json.dumps(document), location="loc", command="c")
    assert outcome.summary == ("no answer.",)
    assert [f.location for f in outcome.errors] == ["loc"]
    assert "answered without a" in outcome.errors[0].message
