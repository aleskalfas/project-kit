"""The validator registry behind `pkit validate` (ADR-058; #986).

- the backbone's members run in registry order and print one section each;
- a capability's validator, registered in package metadata, runs after them
  and its errors fail the umbrella; no answer is an error, never a clean pass;
- `--only` / `--skip` address members, `--no-refs` is `--skip refs`;
- warnings, information and reports print and never fail; errors do;
- every focused surface still works alone with the exit it always had;
- the refs member classifies drift as a warning, the rest as errors, and
  reads a bracketed `reads.patterns` declaration the way the deploy does.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import refs, validators
from project_kit.cli import main
from project_kit.manifest import ComponentRegistryEntry, read_backbone_manifest, write_backbone_manifest
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


def _register(
    root: Path,
    name: str,
    *,
    validators_yaml: str,
    script_body: str | None = None,
    script_path: str = "scripts/check.py",
) -> Path:
    """A synthetic capability at `.pkit/capabilities/<name>/` declaring `validators:`,
    registered in the backbone manifest; `script_body` writes an executable script."""
    cap_dir = root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"schema_version: 2\ncomponent:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n"
        f'description: Synthetic capability for validator tests.\nrequires_backbone: ">=0.1.0"\n'
        f"{validators_yaml}",
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
        if line.startswith("  ") and not line.startswith("    ") and line[2:3].isalpha()
        and not line.startswith("  All checks") and "validator(s) ran" not in line
        and "error(s) found" not in line
    ]


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
        validators_yaml="validators:\n  late:\n    script: scripts/late.py\n    help: Late.\n"
        "  early:\n    script: scripts/early.py\n    help: Early.\n    order: 5\n",
    )
    _register(
        adopter.root,
        "alpha",
        validators_yaml="validators:\n  citations:\n    script: scripts/c.py\n    help: C.\n",
    )
    names = [v.name for v in validators.registered_validators(adopter.root)]
    # `order: 5` sorts among the backbone's members; the default sorts after every one.
    assert names[0] == "zeta:early"
    assert names[1:13] == BACKBONE_ORDER
    assert names[13:] == ["alpha:citations", "zeta:late"]


def test_capability_block_is_read_defensively(adopter: AdopterRepo) -> None:
    _register(adopter.root, "odd", validators_yaml="validators: [not, a, mapping]\n")
    _register(
        adopter.root,
        "half",
        validators_yaml="validators:\n  noscript:\n    help: no script here\n"
        "  ok:\n    script: scripts/ok.py\n    help: Fine.\n    order: not-an-int\n",
    )
    registered = {v.name: v for v in validators.registered_validators(adopter.root)}
    assert "half:ok" in registered and "half:noscript" not in registered
    assert registered["half:ok"].order == validators.CAPABILITY_ORDER_DEFAULT
    assert not any(name.startswith("odd:") for name in registered)


def test_select_addresses_members_and_refuses_unknown_names(adopter: AdopterRepo) -> None:
    registered = validators.registered_validators(adopter.root)
    only = validators.select(registered, only=["refs", "manifests"])
    assert [v.name for v in only] == ["manifests", "refs"]  # registry order, not argument order
    skipped = validators.select(registered, skip=["refs"])
    assert "refs" not in [v.name for v in skipped] and len(skipped) == len(registered) - 1
    with pytest.raises(ValueError, match="unknown validator\\(s\\) 'nope'"):
        validators.select(registered, only=["nope"])


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
        validators_yaml="validators:\n  citations:\n    script: scripts/check.py\n"
        "    help: Every citation resolves.\n",
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
    assert clean.exit_code == 1  # same script, same answer: the member alone fails too


@pytest.mark.parametrize(
    ("script_body", "expect"),
    [
        (_answering(CLEAN_ANSWER, exit_code=3), "exited 3"),
        ("print('not json')\n", "did not print a JSON document"),
        (_answering([1, 2]), "printed a list, not a findings document"),
        (
            _answering({"findings": [{"severity": "fatal", "location": "x", "message": "y"}]}),
            "malformed finding at index 0",
        ),
        (None, "does not exist"),
    ],
)
def test_no_answer_from_a_capability_validator_is_an_error(
    adopter: AdopterRepo, script_body: str | None, expect: str
) -> None:
    _register(
        adopter.root,
        "cap",
        validators_yaml="validators:\n  thing:\n    script: scripts/check.py\n    help: T.\n",
        script_body=script_body,
    )
    result = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert result.exit_code == 1, result.output
    assert "no answer." in result.output
    assert "error    .pkit/capabilities/cap/package.yaml:/validators/thing" in result.output
    assert expect in result.output


def test_a_clean_capability_validator_passes_and_its_summary_prints(adopter: AdopterRepo) -> None:
    _register(
        adopter.root,
        "cap",
        validators_yaml="validators:\n  thing:\n    script: scripts/check.py\n    help: T.\n",
        script_body=_answering(CLEAN_ANSWER),
    )
    result = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert result.exit_code == 0, result.output
    assert "\n  cap:thing\n    3 thing(s) checked; 0 error(s).\n" in result.output


def test_the_packages_member_reports_a_validator_script_that_does_not_exist(
    adopter: AdopterRepo,
) -> None:
    _register(
        adopter.root,
        "cap",
        validators_yaml="validators:\n  thing:\n    script: scripts/missing.py\n    help: T.\n",
    )
    result = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert result.exit_code == 1, result.output
    assert ".pkit/capabilities/cap/package.yaml:/validators/thing/script" in result.output
    assert "validator 'thing' names script 'scripts/missing.py', which does not exist" in (
        result.output
    )


def test_an_unknown_key_inside_a_validator_entry_warns_with_the_nearest_known(
    adopter: AdopterRepo,
) -> None:
    _register(
        adopter.root,
        "cap",
        validators_yaml="validators:\n  thing:\n    script: scripts/check.py\n    help: T.\n"
        "    ordre: 5\n",
        script_body=_answering(CLEAN_ANSWER),
    )
    result = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert result.exit_code == 0, result.output
    assert "warning  .pkit/capabilities/cap/package.yaml:/validators/thing/ordre" in result.output
    assert "unknown key 'ordre'; did you mean 'order'?" in result.output


# --- the focused surfaces still work alone -----------------------------------


def test_each_focused_surface_still_runs_alone(adopter: AdopterRepo) -> None:
    runner = CliRunner()
    for args in (["schemas", "validate"], ["decisions", "validate"]):
        result = runner.invoke(main, args)
        assert result.exit_code == 0, (args, result.output)
        assert "validator(s) ran" not in result.output  # the umbrella's summary is the umbrella's
    # The shipped core skills carry drift; the focused surface fails on any finding,
    # as it always did, while the umbrella's member reports the same drift as warnings.
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
    (adopter.root / "notes").mkdir()
    (adopter.root / "notes" / "loose.yaml").write_text("a: 1\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["validate", "--only", "data"])
    assert result.exit_code == 0, result.output
    assert "no adopter data file is bound to a capability schema." in result.output

    (adopter.root / "notes" / "evidence.yaml").write_text(
        "pkit_schema: evidence:evidence-record\nschema_version: 1\nrecords: 7\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["validate", "--only", "data"])
    assert result.exit_code == 1, result.output
    assert "1 bound data file(s) checked; " in result.output
    assert "error    notes/evidence.yaml" in result.output
    # A dot-directory is never walked: a copy under `.notes/` is not adopter data.
    (adopter.root / ".notes").mkdir()
    (adopter.root / ".notes" / "evidence.yaml").write_text("pkit_schema: evidence:nope\n")
    again = CliRunner().invoke(main, ["validate", "--only", "data"])
    assert "1 bound data file(s) checked; " in again.output


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
    assert diagnoses == ["frontmatter declares pattern 'code-paths' but it is not referenced anywhere."]


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
    assert CliRunner().invoke(main, ["refs", "validate"]).exit_code == 1  # drift alone still fails it


# --- the answer document ------------------------------------------------------


def test_parse_answer_keeps_labels_and_every_severity() -> None:
    document = {
        "summary": ["one", 2],
        "findings": [
            {"severity": s, "location": f"f{i}", "message": "m", "label": "rel"}
            for i, s in enumerate(("error", "warning", "info", "report"))
        ],
    }
    outcome = validators.parse_answer(json.dumps(document), location="loc", script="s")
    assert outcome.summary == ("one", "2")
    assert [f.severity.value for f in outcome.findings] == ["error", "warning", "info", "report"]
    assert all(f.label == "rel" for f in outcome.findings)
    assert len(outcome.errors) == 1
