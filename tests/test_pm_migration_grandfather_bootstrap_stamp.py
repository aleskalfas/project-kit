"""The 0.54.0 migration carries a pre-gate install past the new gate (#747).

At 0.54.0 the prerequisite gate starts refusing every non-exempt pm verb on a
project with no bootstrap stamp. Installs made before that version have none —
they were bootstrapped before the stamp existed — so without this migration a
routine `pkit sync` would make every previously-working command refuse. That is
the adopter-breaking surface change COR-010 wants a same-change-set migration
for, and this is the test that the mitigation actually works: after the
migration runs, the gate opens.

What it deliberately does NOT claim: that a bootstrap was *observed*. No local,
network-free read can tell "installed and bootstrapped" from "installed but
never bootstrapped", so the stamp is marked `by: migration-grandfather` — a
recorded presumption. Pinning that marker here keeps a later reader from
mistaking it for an attested event.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
MIGRATION = CAPABILITY / "migrations" / "0.54.0" / "001-grandfather-bootstrap-stamp.sh"
GATE_MODULE = CAPABILITY / "scripts" / "_lib" / "bootstrap_gate.py"


@pytest.fixture(scope="module")
def gate():
    sys.path.insert(0, str(CAPABILITY / "scripts"))
    spec = importlib.util.spec_from_file_location("pm_gate_for_migration_test", GATE_MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(CAPABILITY / "scripts"))


def _pre_gate_install(tmp_path: Path, *, version: str = "0.53.0") -> Path:
    """An install as it looks BEFORE 0.54.0: config present, no stamp."""
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    (cap / "package.yaml").write_text(
        "schema_version: 2\ncomponent:\n  kind: capability\n"
        f"  name: project-management\n  version: {version}\n"
        'requires_backbone: ">=1.26.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (cap / "project" / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: []\n", encoding="utf-8"
    )
    return cap


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        capture_output=True,
        text=True,
        check=False,
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def test_a_pre_gate_install_is_refused_before_the_migration(gate, tmp_path) -> None:
    """The breakage the migration exists to prevent, stated first."""
    cap = _pre_gate_install(tmp_path)
    assert not gate.evaluate(cap).ok


def test_the_migration_opens_the_gate(gate, tmp_path) -> None:
    cap = _pre_gate_install(tmp_path)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "created" in proc.stdout
    outcome = gate.evaluate(cap)
    assert outcome.ok, outcome.reason


def test_the_stamp_records_a_presumption_not_an_observation(gate, tmp_path) -> None:
    """`by: migration-grandfather` is the honest marker, and the recorded version
    is the installed one — so a grandfathered project does not also read as
    stale on the same upgrade."""
    cap = _pre_gate_install(tmp_path, version="0.53.0")
    _run(tmp_path)
    stamp = gate.evaluate(cap).stamp
    assert stamp.by == "migration-grandfather"
    assert stamp.capability_version == "0.53.0"
    # Unbound: it attests a presumption, so it claims no repository it never
    # verified. A bootstrap/migrate-written stamp binds; this one does not.
    assert stamp.repo is None


def test_the_written_stamp_validates_against_its_schema(tmp_path) -> None:
    from jsonschema import Draft202012Validator

    cap = _pre_gate_install(tmp_path)
    _run(tmp_path)
    document = YAML(typ="safe").load(
        (cap / "project" / "bootstrap-stamp.yaml").read_text(encoding="utf-8")
    )
    import json

    schema = json.loads(
        (CAPABILITY / "schemas" / "bootstrap-stamp.schema.json").read_text(encoding="utf-8")
    )
    assert [e.message for e in Draft202012Validator(schema).iter_errors(document)] == []


def test_re_running_leaves_an_existing_stamp_untouched(tmp_path) -> None:
    """Idempotence (COR-010's script contract), and more: a real
    bootstrap-written stamp must never be downgraded to a presumption by a
    later sync."""
    cap = _pre_gate_install(tmp_path)
    stamp_path = cap / "project" / "bootstrap-stamp.yaml"
    stamp_path.write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-02-02T00:00:00+00:00'\n"
        "  capability_version: 0.40.0\n"
        "  by: bootstrap\n"
        "  repo: github.com/acme/widget\n",
        encoding="utf-8",
    )
    before = stamp_path.read_text(encoding="utf-8")
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert "already present" in proc.stdout
    assert stamp_path.read_text(encoding="utf-8") == before


def test_an_absent_capability_is_a_clean_skip(tmp_path) -> None:
    """The capability is optional; a root without it must not fail the upgrade."""
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert "not installed" in proc.stdout
