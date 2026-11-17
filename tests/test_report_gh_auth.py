"""`pkit report` judges `gh` authentication on the report target's host alone (#3126).

`gh auth status` with no host exits non-zero when any host `gh` is logged in to
fails, such as a second account whose keychain read times out. `report` judged
that exit, so a failing second host sent a report by URL though the target's own
host passed. It now names the host `gh` reaches for `--repo REPORT_TARGET`.
`subprocess.run` is stubbed, so no `gh` runs.
"""

from __future__ import annotations

import json
import subprocess

import pytest

import project_kit.report as rep

DEFAULT = "github.com"
SECOND = "github.second.example.com"

LIST_HOSTS = ["gh", "auth", "status", "--json", "hosts"]
EVERY_HOST = ["gh", "auth", "status"]


def _judging(host: str) -> list[str]:
    return ["gh", "auth", "status", "-h", host]


class _FakeGh:
    """`gh auth status` over hosts that each pass or fail, recording each call.

    Like `gh`, it fails a call that names no host when any host fails, and
    lists every host with `--json hosts`, exiting zero whatever they report.
    """

    def __init__(self, hosts: dict[str, bool], *, lists_hosts: bool) -> None:
        self.hosts = hosts
        self.lists_hosts = lists_hosts
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
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
def fake_gh(monkeypatch):
    """Install a :class:`_FakeGh` as `report`'s `subprocess.run`, with `gh` on
    PATH and no `GH_HOST`."""
    monkeypatch.delenv("GH_HOST", raising=False)
    monkeypatch.setattr(rep.shutil, "which", lambda _name: "/usr/bin/gh")

    def install(hosts: dict[str, bool], *, lists_hosts: bool = True) -> _FakeGh:
        fake = _FakeGh(hosts, lists_hosts=lists_hosts)
        monkeypatch.setattr(rep.subprocess, "run", fake)
        return fake

    return install


def test_a_failing_second_host_does_not_fail_the_target_host(fake_gh) -> None:
    """The check passes on the host the report is filed to, whatever a second
    host logged in beside it reports."""
    fake = fake_gh({DEFAULT: True, SECOND: False})
    assert rep.gh_authenticated() is True
    assert fake.calls == [LIST_HOSTS, _judging(DEFAULT)]


def test_the_target_host_failing_fails_the_check(fake_gh) -> None:
    """The target's host decides, though a second host passes."""
    fake = fake_gh({DEFAULT: False, SECOND: True})
    assert rep.gh_authenticated() is False
    assert fake.calls == [LIST_HOSTS, _judging(DEFAULT)]


def test_the_one_logged_in_host_is_the_target_host(fake_gh) -> None:
    """Logged in to one host only, `gh` reaches that host for `--repo owner/repo`."""
    fake = fake_gh({SECOND: True})
    assert rep.gh_authenticated() is True
    assert fake.calls == [LIST_HOSTS, _judging(SECOND)]


def test_gh_host_names_the_target_host(fake_gh, monkeypatch) -> None:
    """The shell's `GH_HOST` names the host, with no hosts listed."""
    fake = fake_gh({DEFAULT: False, SECOND: True})
    monkeypatch.setenv("GH_HOST", SECOND)
    assert rep.gh_authenticated() is True
    assert fake.calls == [_judging(SECOND)]


def test_logged_in_nowhere_fails_the_check(fake_gh) -> None:
    fake = fake_gh({})
    assert rep.gh_authenticated() is False
    assert fake.calls == [LIST_HOSTS, _judging(DEFAULT)]


@pytest.mark.parametrize(
    ("hosts", "authenticated"),
    [({DEFAULT: True, SECOND: True}, True), ({DEFAULT: True, SECOND: False}, False)],
    ids=["every-host-passes", "a-host-fails"],
)
def test_a_gh_that_cannot_list_its_hosts_judges_every_host(
    fake_gh, hosts: dict[str, bool], authenticated: bool
) -> None:
    """A `gh` too old for `gh auth status --json` is judged as before #3126."""
    fake = fake_gh(hosts, lists_hosts=False)
    assert rep.gh_authenticated() is authenticated
    assert fake.calls == [LIST_HOSTS, EVERY_HOST]


def test_gh_that_will_not_start_is_not_authenticated(monkeypatch) -> None:
    """An `OSError` from starting `gh` reads as no authentication, as before."""
    monkeypatch.setenv("GH_HOST", DEFAULT)
    monkeypatch.setattr(rep.shutil, "which", lambda _name: "/usr/bin/gh")

    def _unstartable(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("gh will not start")

    monkeypatch.setattr(rep.subprocess, "run", _unstartable)
    assert rep.gh_authenticated() is False
