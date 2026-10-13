"""project-management's workflow schema migrations run after the copy (#1460).

A version transition runs a capability's migrations after its copy (COR-010's
order, ADR-065 point 4). On an upgrade that crosses more than one version, the
kit-shipped `workflow.yaml` the copy brings can be newer than each script's
schema, and an override may be too. Neither is a change the script still has to
make, so neither may warn. A schema below the script's still warns.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "migrations"

# Each script, and the schema_version it brings the workflow to.
SCRIPTS = {
    2: MIGRATIONS / "0.15.0" / "001-workflow-yaml-schema-v2.sh",
    3: MIGRATIONS / "0.24.0" / "001-workflow-yaml-schema-v3.sh",
    4: MIGRATIONS / "0.26.0" / "001-workflow-yaml-schema-v4.sh",
}
# A schema past every script's, as a copy on a long jump brings it once a later
# release bumps the schema again.
_LATEST = "5"


def _adopter(tmp_path: Path, *, kit: str, override: str | None) -> Path:
    root = tmp_path / "adopter"
    cap = root / ".pkit" / "capabilities" / "project-management"
    (cap / "schemas").mkdir(parents=True)
    (cap / "schemas" / "workflow.yaml").write_text(
        f"schema_version: {kit}\nprocess:\n  id: issue-lifecycle\n", encoding="utf-8"
    )
    if override is not None:
        overrides = cap / "project" / "schema-overrides"
        overrides.mkdir(parents=True)
        (overrides / "workflow.yaml").write_text(f"schema_version: {override}\n", encoding="utf-8")
    return root


def _run(schema: int, root: Path) -> str:
    result = subprocess.run(
        ["bash", str(SCRIPTS[schema])],
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize("schema", sorted(SCRIPTS))
def test_a_copy_newer_than_the_script_gives_no_warning(tmp_path: Path, schema: int) -> None:
    out = _run(schema, _adopter(tmp_path, kit=_LATEST, override=None))

    assert "[warn]" not in out
    assert "no adopter override" in out


@pytest.mark.parametrize("schema", sorted(SCRIPTS))
def test_an_override_at_a_later_schema_gives_no_warning(tmp_path: Path, schema: int) -> None:
    out = _run(schema, _adopter(tmp_path, kit=_LATEST, override=_LATEST))

    assert "[warn]" not in out
    assert f"already at schema_version {_LATEST}" in out


@pytest.mark.parametrize("schema", sorted(SCRIPTS))
def test_an_override_below_the_scripts_schema_still_warns(tmp_path: Path, schema: int) -> None:
    out = _run(schema, _adopter(tmp_path, kit=_LATEST, override=str(schema - 1)))

    assert "[warn] adopter override of workflow.yaml needs manual migration" in out
    assert f"Required schema_version: {schema}" in out


@pytest.mark.parametrize("kit", ["1", "draft"])
@pytest.mark.parametrize("schema", sorted(SCRIPTS))
def test_a_copy_below_the_scripts_schema_still_warns(tmp_path: Path, schema: int, kit: str) -> None:
    out = _run(schema, _adopter(tmp_path, kit=kit, override=None))

    assert f"(expected {schema} or later); the copy may not have completed" in out
