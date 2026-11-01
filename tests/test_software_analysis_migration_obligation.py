"""software-analysis 0.3.0: each requirement an earlier release wrote gets its fingerprint.

From 0.3.0 each requirement carries `obligation`, and the check fails one without it,
whatever any rule's status (software-analysis DEC-006 point 6). The migration writes it on
each requirement that holds none, withdrawn ones included, from the plan the capability's
command prints and writes nothing by, `pkit analysis obligation --dry-run --json`
(DEC-006, Implications; COR-010). Pinned here: it writes the field where a requirement
holds none and leaves every other line as it was, it is idempotent, it leaves a value that
no longer matches its texts to the project, it reaches the running pkit under the runner,
and it never fails the upgrade when the plan cannot be read.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from packaging.version import Version
from ruamel.yaml import YAML

from project_kit import migrations
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import CONSTRAINTS, QUALITY, fingerprint, installed, requirement
from tests.test_software_analysis_check import check, errors

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "software-analysis"
MIGRATION = CAPABILITY / "migrations" / "0.3.0" / "001-write-each-obligation.sh"

#: Two requirements an earlier release wrote, one of them withdrawn, each without the field.
QUICK = f"{QUALITY}/REQ-004-quick-result.md"
LOCAL = f"{CONSTRAINTS}/REQ-001-local-runs.md"

#: The texts `requirement` writes.
TEXTS = {
    "statement": "The system shows a suite's result within two seconds of the run's end.",
    "measure": "None.",
    "applies-to": "Every run of a suite.",
}


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
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """An adopter whose requirements an earlier release wrote: none carries the field."""
    repo = installed(make_adopter_repo, monkeypatch)
    withdrawn = requirement("constraint", req_id="REQ-001", obligation=None)
    repo.write(
        {
            QUICK: requirement(obligation=None),
            LOCAL: withdrawn.replace('status: "active"', 'status: "withdrawn"'),
        }
    )
    return repo


def test_the_migration_writes_each_requirement_s_obligation_and_nothing_else(
    project: AdopterRepo,
) -> None:
    before = {rel: (project.root / rel).read_text(encoding="utf-8") for rel in (QUICK, LOCAL)}
    assert len(errors(check(project))) == 2

    result = _run(project.root, os.environ["PATH"])

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"  [ok] wrote the obligation of REQ-001 at {LOCAL} (DEC-006 point 6)",
        f"  [ok] wrote the obligation of REQ-004 at {QUICK} (DEC-006 point 6)",
    ]
    value = fingerprint(TEXTS)
    for rel, text in before.items():
        line = 'applies-to: "Every run of a suite."\n'
        wanted = text.replace(line, f"{line}obligation: {value}\n", 1)
        assert (project.root / rel).read_text(encoding="utf-8") == wanted
    assert errors(check(project)) == []


def test_the_migration_run_again_changes_nothing(project: AdopterRepo) -> None:
    assert _run(project.root, os.environ["PATH"]).returncode == 0
    written = {rel: (project.root / rel).read_bytes() for rel in (QUICK, LOCAL)}

    again = _run(project.root, os.environ["PATH"])

    assert again.returncode == 0, again.stderr
    assert again.stdout == "  exists  every requirement carries its obligation: nothing written\n"
    assert {rel: (project.root / rel).read_bytes() for rel in (QUICK, LOCAL)} == written


def test_the_migration_leaves_a_value_that_no_longer_matches_to_the_project(
    project: AdopterRepo,
) -> None:
    stale = requirement(obligation=fingerprint({**TEXTS, "measure": "Two seconds."}))
    project.write({QUICK: stale})

    result = _run(project.root, os.environ["PATH"])

    assert result.returncode == 0, result.stderr
    assert (
        "  exists  REQ-004 carries an obligation already, which no longer matches its texts: "
        "`pkit analysis obligation` writes it anew"
    ) in result.stdout.splitlines()
    assert (project.root / QUICK).read_text(encoding="utf-8") == stale


def test_the_migration_run_by_the_runner_reads_the_running_pkit(
    project: AdopterRepo,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run by the migration runner, behind a `pkit` on the operator's `PATH` that gives no
    answer, the migration reaches the running pkit, which runs the capability's command
    under the migration marker (ADR-065 point 14)."""
    bin_dir = tmp_path_factory.mktemp("decoy")
    decoy = bin_dir / "pkit"
    decoy.write_text("#!/bin/sh\necho 'not the running pkit' >&2\nexit 2\n", encoding="utf-8")
    decoy.chmod(0o755)
    with monkeypatch.context() as patched:
        patched.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
        migrations.execute_migration_scripts([MIGRATION], project.root, label="software-analysis")

    assert errors(check(project)) == []
    assert not (project.root / migrations.RUNNER_PARENT).exists()


@pytest.mark.parametrize("with_pkit", [False, True], ids=["no-pkit", "no-answer"])
def test_the_migration_never_fails_the_upgrade_when_the_plan_cannot_be_read(
    project: AdopterRepo, tmp_path_factory: pytest.TempPathFactory, with_pkit: bool
) -> None:
    bin_dir = tmp_path_factory.mktemp("bin")
    if with_pkit:
        # A pkit that gives no answer, as one run by hand from another release may.
        old = bin_dir / "pkit"
        old.write_text("#!/bin/sh\necho 'No such command' >&2\nexit 2\n", encoding="utf-8")
        old.chmod(0o755)
    before = (project.root / QUICK).read_bytes()

    result = _run(project.root, f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")

    assert result.returncode == 0, result.stderr
    assert "[warn] no requirement's obligation written" in result.stdout
    assert "`pkit analysis obligation` writes each" in result.stdout
    assert (project.root / QUICK).read_bytes() == before


def test_the_migration_lies_where_the_fingerprint_first_ships() -> None:
    """A project installed at or after the version that first writes the field never runs
    it: its stamp and its command write the field. That is the capability's next release,
    0.3.0, so the package still records the release before it, or that release."""
    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    assert "obligation" in package["commands"]
    assert MIGRATION.parent.name == "0.3.0"
    assert Version(package["component"]["version"]) <= Version("0.3.0")
