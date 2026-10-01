"""Provisioning query commands' environments before they run offline (#1092).

- `pkit init` and `pkit sync` resolve the environment of every registered
  command that declares the query contract, once, online, with `uv sync
  --script`; a re-run resolves nothing and says so; a command that cannot be
  provisioned is a warning, never a failure of the step;
- under the real uv, a query not yet provisioned gives the finding naming
  `pkit sync` (how the query policy reads uv's report is `test_validators`'s).

The end-to-end cases run the real `uv` against a one-wheel package index
served on the loopback interface, with a cache of their own, so they reach no
network and leave the user's cache alone; they are skipped where `uv` is not
installed.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import shutil
import socket
import stat
import sys
import threading
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import install, provisioning, sync
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

# The validator's finding when its query command is not provisioned.
NOT_PROVISIONED_FINDING = (
    "command 'check': environment not provisioned — run `pkit sync` (its dependencies "
    "are not in uv's cache, and a query runs offline)."
)

# The one inline dependency of the synthetic query command, served by the local index.
DEP = "pkit-probe-dep"
DEP_MODULE = "pkit_probe_dep"
WHEEL = f"{DEP_MODULE}-1.0-py3-none-any.whl"

QUERY_SCRIPT = f"""#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["{DEP}"]
# ///
import json

import {DEP_MODULE}

print(json.dumps({{"summary": [f"probe {{{DEP_MODULE}.VALUE}}"], "findings": []}}))
"""

needs_uv = pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv on the PATH")


def _register(
    root: Path, script_text: str = QUERY_SCRIPT, *, contract: bool = True, in_manifest: bool = True
) -> Path:
    """A capability `cap` registering the command `check` — declaring the query
    contract unless told not to — and the validator `cap:thing` that names it.
    Recorded in the manifest as incubated unless `in_manifest` is false, which
    leaves it authored in the repository for `capabilities register`."""
    cap_dir = root / ".pkit" / "capabilities" / "cap"
    script = cap_dir / "scripts" / "check.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(script_text, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    declaration = "    query-contract: true\n" if contract else ""
    (cap_dir / "package.yaml").write_text(
        "schema_version: 2\ncomponent:\n  kind: capability\n  name: cap\n  version: 0.1.0\n"
        'description: Synthetic capability for provisioning tests.\nrequires_backbone: ">=0.1.0"\n'
        f"commands:\n  check:\n    script: scripts/check.py\n    help: Check things.\n{declaration}"
        "validators:\n  thing:\n    command: check\n",
        encoding="utf-8",
    )
    if not in_manifest:
        (cap_dir / "README.md").write_text("# cap\n", encoding="utf-8")
        return script
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name="cap",
            manifest=".pkit/capabilities/cap/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(root, backbone)
    return script


def _command(script: Path) -> provisioning.QueryScript:
    return provisioning.QueryScript("cap", "check", script)


# --- which commands, and what each run does ----------------------------------


def test_every_installed_component_s_query_commands_are_found(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo(capabilities=("project-management",))
    found = [(c.owner, c.reference) for c in provisioning.query_commands(repo.root)]
    assert ("project-management", "fill-doc-check") in found
    # Only commands declaring the contract: pm registers many more leaves.
    assert all(ref == "fill-doc-check" for owner, ref in found if owner == "project-management")


def test_a_command_without_the_declaration_is_not_provisioned(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    root = make_adopter_repo().root
    _register(root, contract=False)
    assert provisioning.query_commands(root) == []


@dataclass
class _FakeUv:
    """Stands in for `provisioning._resolve`: answers per mode, records each call."""

    offline: str | None = "not in the cache"
    online: str | None = None
    calls: list[str] = field(default_factory=list)

    def __call__(self, script: Path, *, offline: bool) -> str | None:
        self.calls.append("offline" if offline else "online")
        return self.offline if offline else self.online


@pytest.mark.parametrize(
    ("uv", "state", "calls"),
    [
        (
            _FakeUv(offline="miss", online=None),
            provisioning.State.PROVISIONED,
            ["offline", "online"],
        ),
        (_FakeUv(offline=None), provisioning.State.ALREADY_PROVISIONED, ["offline"]),
        (
            _FakeUv(offline="miss", online="no route"),
            provisioning.State.NOT_PROVISIONED,
            ["offline", "online"],
        ),
    ],
)
def test_offline_first_then_online_only_when_needed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    uv: _FakeUv,
    state: provisioning.State,
    calls: list[str],
) -> None:
    script = tmp_path / "check.py"
    script.write_text(QUERY_SCRIPT, encoding="utf-8")
    monkeypatch.setattr(provisioning, "_resolve", uv)
    result = provisioning.provision(_command(script))
    assert (result.state, uv.calls) == (state, calls)


def test_nothing_to_provision_and_a_dry_run_ask_uv_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uv = _FakeUv()
    monkeypatch.setattr(provisioning, "_resolve", uv)
    plain = tmp_path / "plain.py"
    plain.write_text("#!/usr/bin/env python3\nprint('{}')\n", encoding="utf-8")
    with_metadata = tmp_path / "check.py"
    with_metadata.write_text(QUERY_SCRIPT, encoding="utf-8")

    assert provisioning.provision(_command(plain)).line == (
        "skipped",
        "query command 'check' (cap) — its script declares no inline dependencies, "
        "nothing to provision",
    )
    assert provisioning.provision(_command(tmp_path / "absent.py")).line == (
        "skipped",
        "query command 'check' (cap) — its script does not exist, nothing to provision",
    )
    assert provisioning.provision(_command(with_metadata), dry_run=True).line == (
        "would provision",
        "query command 'check' (cap)",
    )
    assert uv.calls == []


def test_no_uv_is_a_warning_naming_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "check.py"
    script.write_text(QUERY_SCRIPT, encoding="utf-8")
    monkeypatch.setattr(provisioning, "UV", "pkit-test-no-such-uv")
    assert provisioning.provision(_command(script)).line == (
        "warning",
        "query command 'check' (cap) not provisioned: `pkit-test-no-such-uv` is not on the PATH. "
        "It gives no answer offline until `pkit sync` runs with the network.",
    )


def test_init_runs_the_step(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[Path] = []
    monkeypatch.setattr(
        install, "provision_query_commands", lambda ctx: ran.append(ctx.target_root)
    )
    root = make_adopter_repo().root
    assert ran == [root]


# --- the capability verbs provision what they bring in (#1090) ---------------


def _provisioned(owner: str, reference: str) -> str:
    return (
        f"  provisioned  query command {reference!r} ({owner}) — its dependencies "
        "resolved into uv's cache\n"
    )


def test_capability_install_provisions_that_capability_s_query_commands(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Install provisions the installed capability's query commands with sync's
    lines, and only its: another component's are sync's to provision."""
    root = make_adopter_repo().root
    _register(root)
    uv = _FakeUv(offline="miss", online=None)
    monkeypatch.setattr(provisioning, "_resolve", uv)

    result = CliRunner().invoke(main, ["capabilities", "install", "project-management"])

    assert result.exit_code == 0, result.output
    assert _provisioned("project-management", "fill-doc-check") in result.output
    assert "(cap)" not in result.output
    scoped = provisioning.query_commands(root, component="project-management")
    assert [c.reference for c in scoped] == ["fill-doc-check"]
    assert uv.calls == ["offline", "online"] * len(scoped)


def test_capability_upgrade_provisions_the_refreshed_capability(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A kit-shipped capability's upgrade re-provisions it; one already in the
    cache says so and fetches nothing, as sync's re-run does."""
    make_adopter_repo(capabilities=("project-management",))
    uv = _FakeUv(offline=None)
    monkeypatch.setattr(provisioning, "_resolve", uv)

    result = CliRunner().invoke(main, ["capabilities", "upgrade", "project-management"])

    assert result.exit_code == 0, result.output
    assert (
        "  unchanged    query command 'fill-doc-check' (project-management) — already provisioned\n"
    ) in result.output
    assert uv.calls == ["offline"]


def test_register_and_an_incubated_upgrade_provision_the_capability(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An in-repo capability is deployed as a kit-shipped one is (COR-031 D1),
    its query commands included — on `register`, and on `upgrade`'s re-deploy."""
    root = make_adopter_repo().root
    _register(root, in_manifest=False)
    monkeypatch.setattr(provisioning, "_resolve", _FakeUv(offline="miss", online=None))
    runner = CliRunner()

    registered = runner.invoke(main, ["capabilities", "register", "cap"])
    assert registered.exit_code == 0, registered.output
    assert _provisioned("cap", "check") in registered.output

    upgraded = runner.invoke(main, ["capabilities", "upgrade", "cap"])
    assert upgraded.exit_code == 0, upgraded.output
    assert _provisioned("cap", "check") in upgraded.output


def test_a_dry_run_provisions_nothing(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    uv = _FakeUv()
    monkeypatch.setattr(provisioning, "_resolve", uv)
    make_adopter_repo()

    result = CliRunner().invoke(
        main, ["capabilities", "install", "project-management", "--dry-run"]
    )

    assert result.exit_code == 0, result.output
    assert "query command" not in result.output
    assert uv.calls == []


# --- end to end, with the real uv --------------------------------------------


@dataclass
class _LocalIndex:
    """A package index on the loopback interface serving the one wheel."""

    requests: list[str]


def _wheel(directory: Path) -> None:
    """A minimal pure-Python wheel of `DEP` whose module holds `VALUE = 42`."""
    files = {
        f"{DEP_MODULE}/__init__.py": "VALUE = 42\n",
        f"{DEP_MODULE}-1.0.dist-info/METADATA": (
            f"Metadata-Version: 2.1\nName: {DEP}\nVersion: 1.0\n"
        ),
        f"{DEP_MODULE}-1.0.dist-info/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: pkit-tests\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
    }
    record = []
    for name, text in files.items():
        digest = (
            base64.urlsafe_b64encode(hashlib.sha256(text.encode()).digest()).rstrip(b"=").decode()
        )
        record.append(f"{name},sha256={digest},{len(text.encode())}")
    record.append(f"{DEP_MODULE}-1.0.dist-info/RECORD,,")
    files[f"{DEP_MODULE}-1.0.dist-info/RECORD"] = "\n".join(record) + "\n"
    directory.mkdir(parents=True)
    with zipfile.ZipFile(directory / WHEEL, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    (directory / "index.html").write_text(f'<a href="{WHEEL}">{WHEEL}</a>\n', encoding="utf-8")


def _isolate_uv(monkeypatch: pytest.MonkeyPatch, cache: Path, index_url: str) -> None:
    """Point uv at a cache of the test's own and at `index_url` alone."""
    for name in (
        "UV_OFFLINE",
        "UV_INDEX",
        "UV_INDEX_URL",
        "UV_EXTRA_INDEX_URL",
        "UV_FIND_LINKS",
        "UV_NO_INDEX",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("UV_CACHE_DIR", str(cache))
    monkeypatch.setenv("UV_DEFAULT_INDEX", index_url)
    monkeypatch.setenv("UV_NO_CONFIG", "1")
    monkeypatch.setenv("UV_PYTHON", sys.executable)
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    monkeypatch.setenv("UV_HTTP_RETRIES", "0")


@pytest.fixture
def local_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[_LocalIndex]:
    served = tmp_path / "index"
    _wheel(served / "simple" / DEP)
    requests: list[str] = []

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            super().__init__(*args, directory=str(served), **kwargs)

        def log_message(self, format: str, *args: object) -> None:  # the base class's names
            requests.append(self.path)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _isolate_uv(
        monkeypatch, tmp_path / "uv-cache", f"http://127.0.0.1:{server.server_address[1]}/simple"
    )
    try:
        yield _LocalIndex(requests)
    finally:
        server.shutdown()
        server.server_close()


def _closed_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@needs_uv
def test_a_query_not_yet_provisioned_gives_the_finding_under_the_real_uv(
    make_adopter_repo: MakeAdopterRepo, local_index: _LocalIndex
) -> None:
    root = make_adopter_repo().root
    _register(root)
    result = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert result.exit_code == 1, result.output
    assert f"→ {NOT_PROVISIONED_FINDING}" in result.output
    assert local_index.requests == []  # the offline marker held: nothing was fetched


@needs_uv
def test_sync_provisions_a_fresh_tree_and_a_rerun_resolves_nothing(
    make_adopter_repo: MakeAdopterRepo, local_index: _LocalIndex, capsys: pytest.CaptureFixture[str]
) -> None:
    repo: AdopterRepo = make_adopter_repo()
    _register(repo.root)
    capsys.readouterr()

    sync.run_sync(repo.root)
    first = capsys.readouterr().out
    assert (
        "  provisioned  query command 'check' (cap) — its dependencies resolved into uv's cache\n"
        in first
    )
    assert any(WHEEL in path for path in local_index.requests)

    # The query now answers offline, through its shebang, from the cache.
    answered = CliRunner().invoke(main, ["validate", "--only", "cap:thing"])
    assert answered.exit_code == 0, answered.output
    assert "\n  cap:thing\n    probe 42\n" in answered.output

    local_index.requests.clear()
    sync.run_sync(repo.root)
    second = capsys.readouterr().out
    assert "  unchanged    query command 'check' (cap) — already provisioned\n" in second
    assert "provisioned  query command" not in second
    assert local_index.requests == []


@needs_uv
def test_without_the_network_sync_warns_and_completes(
    make_adopter_repo: MakeAdopterRepo,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_adopter_repo()
    _register(repo.root)
    _isolate_uv(monkeypatch, tmp_path / "uv-cache", f"http://127.0.0.1:{_closed_port()}/simple")
    capsys.readouterr()

    sync.run_sync(repo.root)  # never raises for a command it could not provision

    out = capsys.readouterr().out
    [warning] = [line for line in out.splitlines() if line.startswith("  warning ")]
    assert warning.startswith(
        "  warning      query command 'check' (cap) not provisioned: `uv sync --script` exited "
    )
    assert warning.endswith("It gives no answer offline until `pkit sync` runs with the network.")
    assert "Sync complete." in out
