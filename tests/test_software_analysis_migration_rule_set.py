"""software-analysis 0.2.0: an earlier install gets the project rule set install declares.

From 0.2.0 the capability declares ANALYSIS, which its install creates (COR-017;
DEC-001, Implications). The migration creates it for a project that installed the
capability before, on install's conditions, by reading the backbone's answer
(`pkit capabilities project-rule-set software-analysis --json`) and writing the text
it gives. Pinned here: it creates the set where the answer says install would, it is
idempotent, it leaves a set that inherits SAN alone, and it never fails the upgrade
when the answer cannot be read.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from packaging.version import Version
from ruamel.yaml import YAML

from project_kit import declared_rule_sets as drs
from project_kit import migrations
from project_kit import rule_sets as rs
from tests.adopter_repo import MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "software-analysis"
MIGRATION = CAPABILITY / "migrations" / "0.2.0" / "002-create-the-analysis-rule-set.sh"
CREATED = "docs/rule-sets/analysis.md"


def _run(root: Path, path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={"ROOT": str(root), "PATH": path, "HOME": os.environ.get("HOME", "")},
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo) -> Path:
    """An adopter with software-analysis installed as an earlier release left it: the
    capability's copy in place, and no project rule set."""
    root = make_adopter_repo(capabilities=("software-analysis",)).root
    assert not (root / "docs" / "rule-sets").exists()
    return root


def test_the_migration_creates_the_set_install_would_create(
    project: Path, pkit_on_path: Path
) -> None:
    planned = drs.plan(
        project, "software-analysis", project / ".pkit/capabilities/software-analysis"
    )
    assert planned is not None and planned.creates

    result = _run(project, os.environ["PATH"])

    assert result.returncode == 0, result.stderr
    assert (
        "[ok] created the project rule set ANALYSIS at docs/rule-sets/analysis.md" in result.stdout
    )
    text = (project / CREATED).read_text(encoding="utf-8")
    assert text == planned.text
    # The set the capability declares, as DEC-001's Implications give it.
    assert text.startswith(
        "---\nrule-set: ANALYSIS\nversion: 1.0.0\ninherits: [software-analysis:SAN@1]\n"
        "scope:\n  types: [software-analysis:actor, software-analysis:term, "
        "software-analysis:use-case, software-analysis:journey]\nrules: {}\n---\n\n"
        "# ANALYSIS — The project's rules for its analysis\n"
    )
    discovery = rs.discover_rule_sets(project)
    assert [s.path for s in rs.inheritors(discovery, "software-analysis", "SAN")] == [CREATED]


def test_the_migration_run_by_the_runner_reads_the_running_pkit(
    project: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run by the migration runner, behind a `pkit` on the operator's `PATH` that
    gives no answer, the migration reaches the running pkit, whose reading command
    answers under the migration marker (ADR-065 point 14)."""
    bin_dir = tmp_path_factory.mktemp("decoy")
    decoy = bin_dir / "pkit"
    decoy.write_text("#!/bin/sh\necho 'not the running pkit' >&2\nexit 2\n", encoding="utf-8")
    decoy.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    migrations.execute_migration_scripts([MIGRATION], project, label="software-analysis")

    assert (project / CREATED).is_file()
    assert not (project / migrations.RUNNER_PARENT).exists()


def test_the_migration_run_again_changes_nothing(project: Path, pkit_on_path: Path) -> None:
    assert _run(project, os.environ["PATH"]).returncode == 0
    edited = (project / CREATED).read_text(encoding="utf-8") + "\nThe project's words.\n"
    (project / CREATED).write_text(edited, encoding="utf-8")

    again = _run(project, os.environ["PATH"])

    assert again.returncode == 0, again.stderr
    assert f"exists  {CREATED} inherits software-analysis:SAN already" in again.stdout
    assert (project / CREATED).read_text(encoding="utf-8") == edited


def test_the_migration_leaves_a_set_that_inherits_san_alone(
    project: Path, pkit_on_path: Path
) -> None:
    own = project / "docs" / "rule-sets" / "ours.md"
    own.parent.mkdir(parents=True)
    own.write_text(
        "---\nrule-set: OURS\nversion: 1.0.0\ninherits: [software-analysis:SAN@1]\n"
        "scope:\n  types: [software-analysis:actor]\nrules: {}\n---\n\n# OURS\n",
        encoding="utf-8",
    )

    result = _run(project, os.environ["PATH"])

    assert result.returncode == 0, result.stderr
    assert "docs/rule-sets/ours.md inherits software-analysis:SAN already" in result.stdout
    assert not (project / CREATED).exists()


def test_the_migration_warns_and_creates_nothing_where_the_name_is_taken(
    project: Path, pkit_on_path: Path
) -> None:
    taken = project / "docs" / "rule-sets" / "mine.md"
    taken.parent.mkdir(parents=True)
    taken.write_text(
        "---\nrule-set: ANALYSIS\nversion: 1.0.0\nscope:\n  paths: [docs/**]\nrules: {}\n---\n\n"
        "# ANALYSIS\n",
        encoding="utf-8",
    )

    result = _run(project, os.environ["PATH"])

    assert result.returncode == 0, result.stderr
    assert (
        "[warn] no project rule set created: rule set ANALYSIS is declared already" in result.stdout
    )
    assert not (project / CREATED).exists()


@pytest.mark.parametrize("with_pkit", [False, True], ids=["no-pkit", "no-answer"])
def test_the_migration_never_fails_the_upgrade_when_the_answer_cannot_be_read(
    project: Path, tmp_path_factory: pytest.TempPathFactory, with_pkit: bool
) -> None:
    bin_dir = tmp_path_factory.mktemp("bin")
    if with_pkit:
        # A pkit that gives no answer, as one run by hand from another release may.
        old = bin_dir / "pkit"
        old.write_text("#!/bin/sh\necho 'No such command' >&2\nexit 2\n", encoding="utf-8")
        old.chmod(0o755)
    path = f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin"

    result = _run(project, path)

    assert result.returncode == 0, result.stderr
    assert "[warn] no project rule set created" in result.stdout
    assert "pkit capabilities project-rule-set software-analysis" in result.stdout
    assert not (project / CREATED).exists()


def test_the_migration_lies_where_the_declaration_first_ships() -> None:
    """A project installed at or after the version that first declares the set never
    runs it, so a set it removed stays removed (COR-017). The declaration ships in the
    capability's next release, 0.2.0: the package still records the release before it,
    or that release."""
    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    assert package["project_rule_set"]["name"] == "ANALYSIS"
    assert MIGRATION.parent.name == "0.2.0"
    assert Version(package["component"]["version"]) <= Version("0.2.0")
