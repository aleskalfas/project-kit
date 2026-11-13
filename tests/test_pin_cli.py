"""Tests for `pkit pin` / `pkit unpin` (ADR-049).

The two operator gestures that manage a project's `.pkit/version-pin` directive:
`pin` writes it (freeze at the current content version by default, or reconcile
to a given version), `unpin` removes it. The pin token is a version number only
(a single leading `v` stripped), or a release candidate in PEP 440's normal form
(ADR-089 point 6) — branch / sha / other pre-release forms are refused.
The router reads the file elsewhere; these tests cover only the write/remove
gestures and the sync-exclusion invariant that neither `init` nor `sync` ever
touches the directive.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import router, upgrade
from project_kit.cli import main
from project_kit.sync import run_sync
from tests.adopter_repo import build_adopter_repo


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".pkit").mkdir()
    return tmp_path


def _write_manifest(
    tmp_path: Path, backbone_version: str, completed_version: str | None = None
) -> None:
    """Seed a minimal `.pkit/manifest.yaml` so `pin <version>` can read the
    current content version it compares the target against (ADR-049), with a
    completion where *completed_version* names one."""
    completed = f"completed_version: {completed_version}\n" if completed_version else ""
    (tmp_path / ".pkit" / "manifest.yaml").write_text(
        f"schema_version: 1\nbackbone_version: {backbone_version}\n{completed}components: []\n",
        encoding="utf-8",
    )


def test_pin_no_arg_freezes_at_content_version_not_running_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-arg `pin` freezes at the CONTENT version (`backbone_version`), not the
    running binary — even when the installed tool is ahead of synced content."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.5.0")
    monkeypatch.chdir(tmp_path)
    # Installed tool is ahead of the project's synced content; freeze at content.
    monkeypatch.setattr(router, "running_version", lambda: "9.9.9")

    result = CliRunner().invoke(main, ["pin"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "1.5.0"
    assert "1.5.0" in result.output


def test_pin_no_arg_refuses_when_manifest_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-arg `pin` has no recorded content version to freeze at → hard refuse."""
    _git_repo(tmp_path)  # .pkit/ exists but no manifest.yaml
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["pin"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    # Upgrade writes the manifest at its version (ADR-065 point 8), not sync.
    assert "pkit upgrade" in result.output
    assert "pkit sync" not in result.output


def test_pin_strips_leading_v_and_routes_bare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pin v1.145.0` normalises to the bare `1.145.0` — so the router builds
    `@v1.145.0`, never a broken `@vv1.145.0`."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.145.0")  # equal → freeze in place
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["pin", "v1.145.0"])

    assert result.exit_code == 0
    written = router.read_version_pin(tmp_path)
    assert written == "1.145.0"  # the leading `v` was stripped before writing
    # And the router routes the written pin to the bare `v<semver>` tag.
    assert f"@v{written}" in " ".join(router._pinned_base(written))
    assert "@vv" not in " ".join(router._pinned_base(written))


@pytest.mark.parametrize(
    "token",
    [
        "feature-branch",  # branch name
        "abc1234",  # commit sha
        "1.2.3a1",  # a pre-release other than a candidate
        "1.2.3.dev1",  # a dev release
        "1.2.3+build",  # build metadata
        "1.2",  # not three-part
        "latest",  # tag alias
    ],
)
def test_pin_refuses_non_semver_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token: str
) -> None:
    """Only a bare `MAJOR.MINOR.PATCH` semver, or a candidate's `X.Y.ZrcN`, is
    accepted; everything else is refused (exit non-zero, nothing written) — the
    router can't route it."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a refused token must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", token])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    assert "1.145.0" in result.output  # the "takes a version like …" guidance


@pytest.mark.parametrize("token", ["2.0.0-rc.1", "2.0.0RC1", "2.0.0.rc1", "v2.0.0-rc1"])
def test_pin_refuses_a_candidate_spelt_another_way_naming_its_normal_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token: str
) -> None:
    """A candidate spelt other than PEP 440's normal form is refused, and the
    message names the normal form, the only one whose tag the router reaches
    (ADR-089 point 6). Nothing is written."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a refused token must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", token])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    output = " ".join(result.output.split())
    assert "in PEP 440's normal form, 2.0.0rc1" in output
    assert "Nothing was written" in output


def test_pin_raises_a_project_at_a_final_release_to_a_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit pin 2.0.0rc1` in a project at a final release raises it to the
    candidate, as to any newer version: the candidate's own upgrade runs through
    the bypass, and the pin flips to the candidate's normal form last (ADR-089
    point 6, ADR-049 point 5). A leading `v` is stripped as for a release."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.9.0")
    router.pin_file_path(tmp_path).write_text("1.9.0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    handed: list[tuple[str, list[str], str | None]] = []

    def _fake_bypassed(pin: str, argv: list[str], _environ: object = None) -> int:
        handed.append((pin, argv, router.read_version_pin(tmp_path)))
        return 0

    monkeypatch.setattr(upgrade, "run_bypassed", _fake_bypassed)

    result = CliRunner().invoke(main, ["pin", "v2.0.0rc1"])

    assert result.exit_code == 0, result.output
    assert handed == [("2.0.0rc1", ["upgrade"], "1.9.0")]  # the pin flips after
    assert router.read_version_pin(tmp_path) == "2.0.0rc1"
    assert "@v2.0.0rc1" in " ".join(router._pinned_base("2.0.0rc1"))


@pytest.mark.parametrize(
    ("content", "target", "order"),
    [
        ("2.0.0rc1", "2.0.0rc1", "equal"),
        ("2.0.0rc1", "2.0.0", "newer"),  # a final release sorts above its candidates
        ("2.0.0rc1", "2.0.0rc2", "newer"),
        ("2.0.0", "2.0.0rc1", "older"),
        ("1.9.0", "2.0.0rc1", "newer"),
    ],
)
def test_pin_orders_a_candidate_by_pep_440(content: str, target: str, order: str) -> None:
    """The pin's target is ordered by PEP 440 against the recorded content, so a
    candidate sorts below its final release and above the release before it
    (ADR-089 point 6)."""
    assert upgrade._pin_order(target, content) == order


def test_pin_refuses_a_candidate_older_than_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A candidate older than the project's content is refused as an older
    release is, and nothing is written (ADR-089 point 6, ADR-049 point 3)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a downgrade must never reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "2.0.0rc1"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    assert "refusing to pin 2.0.0rc1: it is OLDER" in result.output


@pytest.mark.parametrize("target", ["2.0.0", "2.0.0rc2", "v2.1.0"])
@pytest.mark.parametrize(
    "completed", ["2.0.0rc1", "1.9.0"], ids=["on-it", "a-move-onto-it-cut-short"]
)
def test_pin_raises_a_project_on_a_candidate_to_no_other_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, completed: str
) -> None:
    """A raise of the pin refuses to move a project whose manifest records a release
    candidate to any release but that candidate, candidate or final, before it
    writes anything, and names the ways off. Where the move onto the candidate was
    cut short, it names `pkit upgrade --pre` too (ADR-092 point 7)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0rc1", completed)
    router.pin_file_path(tmp_path).write_text(f"{completed}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a raise off a candidate must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", target])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert (
        f"refusing to move this project to pkit {target.removeprefix('v')}: its manifest "
        "records the release candidate 2.0.0rc1"
    ) in output
    assert "leave the testers' branch" in output
    assert ("`pkit upgrade --pre` finishes it" in output) is (completed != "2.0.0rc1")
    assert router.read_version_pin(tmp_path) == completed


def test_pin_freezes_a_project_at_its_candidate_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinning a project at the candidate its content records freezes it in place,
    with no content sync (ADR-049, ADR-089 point 6)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0rc1")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("an equal pin must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "2.0.0rc1"])

    assert result.exit_code == 0, result.output
    assert router.read_version_pin(tmp_path) == "2.0.0rc1"


def test_pin_version_refuses_when_manifest_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pin <version>` has nothing to order the target against without a manifest
    → hard refuse (exit non-zero, nothing written)."""
    _git_repo(tmp_path)  # .pkit/ exists but no manifest.yaml
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a refused pin must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "1.99.0"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    # Upgrade writes the manifest at its version (ADR-065 point 8), not sync.
    assert "pkit upgrade" in result.output
    assert "pkit sync" not in result.output


def test_pin_overwrites_an_existing_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0")
    monkeypatch.chdir(tmp_path)
    router.pin_file_path(tmp_path).write_text("1.0.0\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["pin", "2.0.0"])  # equal → freeze in place

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "2.0.0"


def test_unpin_removes_the_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    router.pin_file_path(tmp_path).write_text("1.99.0\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["unpin"])

    assert result.exit_code == 0
    assert not router.pin_file_path(tmp_path).exists()


def test_unpin_is_idempotent_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["unpin"])

    assert result.exit_code == 0  # no error when there is nothing to remove
    assert not router.pin_file_path(tmp_path).exists()


@pytest.mark.parametrize(
    ("backbone", "completed"),
    [("2.0.0rc1", "2.0.0rc1"), ("2.0.0rc1", "1.9.0")],
    ids=["on-it", "a-move-onto-it-cut-short"],
)
def test_unpin_refuses_in_a_project_on_a_candidate_and_names_the_ways_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backbone: str, completed: str
) -> None:
    """A project whose manifest records a release candidate stays pinned: `unpin`
    refuses, writes nothing, and names the ways off (ADR-089 point 7, PRJ-016 point
    4)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, backbone, completed)
    router.pin_file_path(tmp_path).write_text("2.0.0rc1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["unpin"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "refusing to remove this project's pin: its manifest records the release candidate " in (
        output
    )
    assert "leave the testers' branch" in output
    assert router.read_version_pin(tmp_path) == "2.0.0rc1"


def test_unpin_removes_the_pin_of_a_project_at_a_final_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0", "2.0.0")
    router.pin_file_path(tmp_path).write_text("2.0.0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["unpin"])

    assert result.exit_code == 0, result.output
    assert not router.pin_file_path(tmp_path).exists()


# --- `pin <version>` reconcile + downgrade guard (ADR-049) ----------------------


def test_pin_equal_version_freezes_without_content_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target == current content version → freeze in place, no content reconcile."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.5.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("equal pin must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "1.5.0"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "1.5.0"
    assert "Pinned project-kit to 1.5.0" in result.output


def test_pin_newer_version_reconciles_forward_then_flips_pin_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target > current → reconcile content forward under the target's own code,
    then flip the pin LAST: the pin is not yet advanced while the reconcile runs."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)

    seen: dict[str, object] = {}

    def _fake_bypassed(pin: str, argv: list[str], environ: object = None) -> int:
        # The pin must NOT yet be advanced when the forward reconcile runs.
        seen["pin_during_reconcile"] = router.read_version_pin(tmp_path)
        seen["target"] = pin
        seen["argv"] = argv
        return 0

    monkeypatch.setattr(upgrade, "run_bypassed", _fake_bypassed)

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code == 0
    assert seen["target"] == "2.0.0"
    assert seen["argv"] == ["upgrade"]
    assert seen["pin_during_reconcile"] is None  # flipped only after reconcile
    assert router.read_version_pin(tmp_path) == "2.0.0"  # flipped last


def test_pin_newer_version_passes_force_to_the_targets_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pin <newer> --force` passes `--force` to the target's upgrade, with the
    narrow reach `pkit upgrade --force` has there (ADR-065 point 9)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)
    handed: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        upgrade, "run_bypassed", lambda pin, argv, _environ=None: handed.append((pin, argv)) or 0
    )

    result = CliRunner().invoke(main, ["pin", "2.0.0", "--force"])

    assert result.exit_code == 0, result.output
    assert handed == [("2.0.0", ["upgrade", "--force"])]
    assert router.read_version_pin(tmp_path) == "2.0.0"


def test_pin_older_version_is_refused_under_force_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--force` reaches only the target's upgrade: the refusal of an older version
    still takes no override (ADR-049, ADR-065 point 9)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a downgrade must never reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "1.0.0", "--force"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    assert "forward-only" in result.output


def test_pin_newer_version_aborts_without_advancing_pin_on_reconcile_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-zero reconcile exit leaves the pin unmoved — the pin never advances
    past content that failed to land (ADR-049)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    router.pin_file_path(tmp_path).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(upgrade, "run_bypassed", lambda *_a, **_k: 3)

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code != 0
    assert router.read_version_pin(tmp_path) == "1.0.0"  # unmoved


def test_pin_newer_version_that_cannot_be_fetched_runs_nothing_and_keeps_the_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The raise probes its target before it runs it: a target the probe cannot
    fetch runs no upgrade, the pin stays as it was, and the message names the
    fetch that failed (ADR-090 point 2, ADR-049 point 5)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    router.pin_file_path(tmp_path).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def _not_fetched(pin: str, *_a: object, **_k: object) -> int:
        raise router.ReleaseNotFetched(pin)

    monkeypatch.setattr(upgrade, "run_bypassed", _not_fetched)

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code != 0
    assert router.read_version_pin(tmp_path) == "1.0.0"  # unmoved
    output = " ".join(result.output.split())
    assert "pkit 2.0.0 could not be fetched" in output
    assert "The pin was not advanced" in output
    assert f"`uvx --from {router.DISTRIBUTION_GIT_URL}@v2.0.0 project-kit --version`" in output


def test_bypassed_pin_raises_a_project_pinned_below_through_this_releases_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`PKIT_NO_ROUTE=1 pkit pin <version>`, run by this release's tool with a
    version at or after this release, raises a project pinned below it through
    this release's URL: the probe and the run each fetch the target from the
    repository's public HTTPS URL, the probe alone with git's terminal prompt
    off, and the pin moves to the target (ADR-090, its Limits)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    router.pin_file_path(tmp_path).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(router._BYPASS_ENV, "1")
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    target = router.running_version()

    spawned: list[tuple[list[str], dict[str, str]]] = []
    real_run = subprocess.run

    def _fake_run(cmd, *args, **kwargs):
        # Intercept only the `uvx …` spawns: the probe and the raise's run.
        if list(cmd[:1]) != ["uvx"]:
            return real_run(cmd, *args, **kwargs)
        spawned.append((list(cmd), kwargs["env"]))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(router.subprocess, "run", _fake_run)

    result = CliRunner().invoke(main, ["pin", target])

    assert result.exit_code == 0, result.output
    [(probe, probe_env), (run, run_env)] = spawned
    source = f"git+https://github.com/aleskalfas/project-kit.git@v{target}"
    assert probe == ["uvx", "--from", source, "project-kit", "--version"]
    assert run[:4] == ["uvx", "--from", source, "project-kit"]
    assert run[4] == "upgrade"
    assert probe_env["GIT_TERMINAL_PROMPT"] == "0"
    assert "GIT_TERMINAL_PROMPT" not in run_env
    assert router.read_version_pin(tmp_path) == target


def test_pin_older_version_is_refused_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target < current → hard refuse: exit non-zero, write no pin, touch no
    content (migrations are forward-only, COR-010)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a downgrade must never reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "1.0.0"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()  # nothing written
    # The manifest (content version) is untouched.
    manifest_text = (tmp_path / ".pkit" / "manifest.yaml").read_text(encoding="utf-8")
    assert "backbone_version: 2.0.0" in manifest_text
    assert "forward-only" in result.output
    # The rollback reverts each upgrade's commit, which restores the files a
    # migration edited outside `.pkit/` too (ADR-049 point 3).
    output = " ".join(result.output.split())
    assert "revert the commit of each upgrade since the earlier version: git revert <commit>" in (
        output
    )
    assert "inside `.pkit/` and outside" in output
    assert "git checkout" not in output


def test_pin_help_names_reverting_each_upgrade_to_roll_back() -> None:
    """`pkit pin --help` names the same rollback as the refusal (ADR-049 point 3)."""
    result = CliRunner().invoke(main, ["pin", "--help"])

    assert result.exit_code == 0, result.output
    output = " ".join(result.output.split())
    assert "revert the commit of each upgrade since that version to roll back" in output
    assert "git checkout" not in output


def test_pin_newer_in_routed_context_reconciles_content_not_just_flips_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pin <newer>` invoked as a routed child (PKIT_ROUTED set) bootstraps the
    reconcile with routing truly OFF — PKIT_NO_ROUTE set AND PKIT_ROUTED cleared —
    so the target's `upgrade` reaches its content-sync path instead of re-detecting
    itself as the routed pinned child and no-op'ing (which would flip the pin
    without syncing content: pin-ahead-of-content corruption). Regression for the
    env-leak (ADR-049)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")  # we are the pinned routed child

    captured: dict[str, Any] = {}
    real_run = subprocess.run

    def _fake_run(cmd, *args, **kwargs):
        # Intercept only the bootstrap `uvx …` spawn; delegate everything else
        # (the CLI's `git rev-parse` root resolution) to the genuine run, since
        # patching the shared `subprocess` module replaces `run` process-wide.
        if list(cmd[:1]) != ["uvx"]:
            return real_run(cmd, *args, **kwargs)
        captured["cmd"] = list(cmd)
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(cmd, 0)

    # run_bypassed spawns via router.subprocess.run — patch there so the real
    # env-clearing logic runs (not a stubbed run_bypassed).
    monkeypatch.setattr(router.subprocess, "run", _fake_run)

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code == 0
    cmd = captured["cmd"]
    assert cmd[-1] == "upgrade"
    assert f"{router.DISTRIBUTION_GIT_URL}@v2.0.0" in cmd
    env = captured["env"]
    assert env[router._BYPASS_ENV] == "1"  # routing bypassed for the reconcile
    assert router._LOOP_GUARD_ENV not in env  # cleared → grandchild reconciles for real
    assert router.read_version_pin(tmp_path) == "2.0.0"  # flipped after reconcile


# --- Every pin gesture writes through the pin's one writer (#1211) --------------


@pytest.mark.parametrize(
    ("args", "written"),
    [
        ([], "1.5.0"),  # freeze at the content version
        (["1.5.0"], "1.5.0"),  # equal → freeze in place
        (["2.0.0"], "2.0.0"),  # newer → reconcile, then raise the pin
    ],
)
def test_pin_writes_through_the_one_pin_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, args: list[str], written: str
) -> None:
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.5.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(upgrade, "run_bypassed", lambda *_a, **_k: 0)
    writes: list[tuple[Path, str | None]] = []
    monkeypatch.setattr(upgrade, "write_version_pin", lambda *call: writes.append(call))

    result = CliRunner().invoke(main, ["pin", *args])

    assert result.exit_code == 0, result.output
    assert writes == [(tmp_path, written)]


def test_unpin_removes_through_the_one_pin_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    router.pin_file_path(tmp_path).write_text("1.99.0\n", encoding="utf-8")
    writes: list[tuple[Path, str | None]] = []
    monkeypatch.setattr(router, "write_version_pin", lambda *call: writes.append(call))

    result = CliRunner().invoke(main, ["unpin"])

    assert result.exit_code == 0, result.output
    assert writes == [(tmp_path, None)]


# --- Sync-exclusion invariant (ADR-049): init / sync never touch the pin --------


def _install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Install the kit into a fresh repo, stubbing adapter primitives (no harness)."""
    build_adopter_repo(tmp_path, monkeypatch=monkeypatch)


def test_init_does_not_create_a_version_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit init` propagates only the kit-owned areas; the project-owned pin
    directive is never seeded (ADR-049 point 2; `pkit pin` or `pkit upgrade`
    creates it, ADR-064)."""
    _install(tmp_path, monkeypatch)
    assert not router.pin_file_path(tmp_path).exists()


def test_sync_preserves_an_existing_version_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit sync` never writes or clobbers `.pkit/version-pin` — it is
    project-owned, outside the propagated areas, and survives a content refresh."""
    _install(tmp_path, monkeypatch)
    router.pin_file_path(tmp_path).write_text("1.99.0\n", encoding="utf-8")

    run_sync(tmp_path)

    assert router.read_version_pin(tmp_path) == "1.99.0"
