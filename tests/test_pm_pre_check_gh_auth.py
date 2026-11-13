"""pre-check judges `gh` authentication on the project's host alone (#3007).

`gh auth status` with no host exits non-zero when any host `gh` is logged in to
fails, such as a second account whose keychain read times out. pre-check judged
that exit, so a failing second host failed it though the project's own host
passed. It now names the host: the configured `gh.host` (DEC-023), else the
host `gh` reaches for a call that names none. `subprocess.run` is stubbed, so no
`gh` runs.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
SCRIPT = SCRIPTS_DIR / "pre-check.py"

CONFIGURED = "github.example.com"
SECOND = "github.second.example.com"
DEFAULT = "github.com"

LIST_HOSTS = ["gh", "auth", "status", "--json", "hosts"]
EVERY_HOST = ["gh", "auth", "status"]


def _judging(host: str) -> list[str]:
    return ["gh", "auth", "status", "-h", host]


@pytest.fixture(scope="module")
def pc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_pre_check_gh_auth", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_pre_check_gh_auth"] = module
    spec.loader.exec_module(module)
    yield module


class _FakeGh:
    """`gh auth status` over hosts that each pass or fail, recording each call.

    Like `gh`, it fails a call that names no host when any host fails, and
    lists every host with `--json hosts`, exiting zero whatever they report.
    """

    def __init__(self, hosts: dict[str, bool], *, lists_hosts: bool) -> None:
        self.hosts = hosts
        self.lists_hosts = lists_hosts
        self.calls: list[list[str]] = []

    def __call__(self, argv, **_kwargs) -> subprocess.CompletedProcess[str]:
        argv = list(argv)
        self.calls.append(argv)
        if argv == LIST_HOSTS:
            if not self.lists_hosts:
                return subprocess.CompletedProcess(argv, 1, "", "unknown flag: --json")
            listed = {
                host: [{"host": host, "active": True, "state": "success" if ok else "timeout"}]
                for host, ok in self.hosts.items()
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps({"hosts": listed}), "")
        if argv == EVERY_HOST:
            passes = bool(self.hosts) and all(self.hosts.values())
        else:
            assert len(argv) == 5 and argv == _judging(argv[4]), argv
            passes = self.hosts.get(argv[4], False)
        return subprocess.CompletedProcess(argv, 0 if passes else 1, "", "")


@pytest.fixture
def fake_gh(pc, monkeypatch):
    """Install a :class:`_FakeGh` as pre-check's `subprocess.run`, with no `GH_HOST`."""
    monkeypatch.delenv("GH_HOST", raising=False)

    def install(hosts: dict[str, bool], *, lists_hosts: bool = True) -> _FakeGh:
        fake = _FakeGh(hosts, lists_hosts=lists_hosts)
        monkeypatch.setattr(pc.subprocess, "run", fake)
        return fake

    return install


# ----- a configured host ---------------------------------------------------


def test_a_configured_host_is_judged_alone(pc, fake_gh) -> None:
    """A failing second host does not fail the check where `gh.host` is set."""
    fake = fake_gh({CONFIGURED: True, SECOND: False})
    result = pc._check_gh_auth({"gh": {"host": CONFIGURED}})
    assert result.status == "ok"
    assert result.detail == f"host={CONFIGURED} (configured as `gh.host`)"
    assert fake.calls == [_judging(CONFIGURED)]


def test_a_configured_host_that_fails_fails_the_check(pc, fake_gh) -> None:
    """The configured host decides, though another host passes."""
    fake = fake_gh({CONFIGURED: False, DEFAULT: True})
    result = pc._check_gh_auth({"gh": {"host": CONFIGURED}})
    assert result.status == "fail"
    assert result.detail == f"`gh auth status -h {CONFIGURED}` reports no active authentication"
    assert result.remediation is not None
    assert f"`gh auth login -h {CONFIGURED}`" in result.remediation
    assert "DEC-023" in result.remediation
    assert fake.calls == [_judging(CONFIGURED)]


def test_the_configured_host_wins_over_gh_host(pc, fake_gh, monkeypatch) -> None:
    """Config wins over the shell's `GH_HOST` (DEC-023)."""
    fake = fake_gh({CONFIGURED: True, SECOND: False})
    monkeypatch.setenv("GH_HOST", SECOND)
    result = pc._check_gh_auth({"gh": {"host": CONFIGURED}})
    assert result.status == "ok"
    assert fake.calls == [_judging(CONFIGURED)]


# ----- no configured host: gh's default host -------------------------------


@pytest.mark.parametrize(
    "config",
    [None, {}, {"gh": None}, {"gh": {"default_owner": "acme"}}, {"gh": {"host": ""}}],
    ids=["unreadable", "no-gh-block", "null-gh-block", "owner-only", "empty-host"],
)
def test_a_failing_second_host_does_not_fail_the_default_host(pc, fake_gh, config) -> None:
    """With no host configured, the check passes on the default host, whatever
    a second host logged in beside it reports."""
    fake = fake_gh({DEFAULT: True, SECOND: False})
    result = pc._check_gh_auth(config)
    assert result.status == "ok"
    assert result.detail == f"host={DEFAULT} (`gh`'s default host)"
    assert fake.calls == [LIST_HOSTS, _judging(DEFAULT)]


def test_the_default_host_failing_fails_the_check(pc, fake_gh) -> None:
    """The default host decides, though a second host passes; the remediation
    names the host and the `gh.host` that would name another."""
    fake = fake_gh({DEFAULT: False, SECOND: True})
    result = pc._check_gh_auth({})
    assert result.status == "fail"
    assert result.remediation is not None
    assert f"`gh auth login -h {DEFAULT}`" in result.remediation
    assert "`gh.host`" in result.remediation
    assert fake.calls == [LIST_HOSTS, _judging(DEFAULT)]


def test_the_one_logged_in_host_is_the_default(pc, fake_gh) -> None:
    """Logged in to one host only, `gh` reaches that host for a call naming none."""
    fake = fake_gh({CONFIGURED: True})
    result = pc._check_gh_auth({})
    assert result.status == "ok"
    assert result.detail == f"host={CONFIGURED} (the one host `gh` is logged in to)"
    assert fake.calls == [LIST_HOSTS, _judging(CONFIGURED)]


def test_gh_host_names_the_default_host(pc, fake_gh, monkeypatch) -> None:
    """The shell's `GH_HOST` names the default host, with no hosts listed."""
    fake = fake_gh({DEFAULT: False, SECOND: True})
    monkeypatch.setenv("GH_HOST", SECOND)
    result = pc._check_gh_auth({})
    assert result.status == "ok"
    assert result.detail == f"host={SECOND} (from `GH_HOST`)"
    assert fake.calls == [_judging(SECOND)]


def test_logged_in_nowhere_fails_the_check(pc, fake_gh) -> None:
    fake = fake_gh({})
    result = pc._check_gh_auth({})
    assert result.status == "fail"
    assert fake.calls == [LIST_HOSTS, _judging(DEFAULT)]


@pytest.mark.parametrize(
    ("hosts", "status"),
    [({DEFAULT: True, SECOND: True}, "ok"), ({DEFAULT: True, SECOND: False}, "fail")],
    ids=["every-host-passes", "a-host-fails"],
)
def test_a_gh_that_cannot_list_its_hosts_judges_every_host(pc, fake_gh, hosts, status) -> None:
    """A `gh` too old for `gh auth status --json` is judged as before #3007."""
    fake = fake_gh(hosts, lists_hosts=False)
    result = pc._check_gh_auth({})
    assert result.status == status
    assert fake.calls == [LIST_HOSTS, EVERY_HOST]
