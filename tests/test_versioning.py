"""Tests for `pkit version bump` (the Python port of `cmd_version_bump`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import pytest
from click.testing import CliRunner

from project_kit import cli, session_guard, versioning
from tests import sessions


@pytest.fixture
def tmp_kit(tmp_path: Path) -> Path:
    """A minimal fake source kit with VERSION + one component package.yaml."""
    (tmp_path / "VERSION").write_text("0.5.0\n", encoding="utf-8")

    # Synthesise a kit-shipped package.yaml with an upper bound that
    # will need broadening on a minor bump.
    adapter = tmp_path / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: adapter\n"
        "  name: claude-code\n"
        "  version: 0.1.0\n"
        'requires_backbone: ">=0.1.0,<0.6.0"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_bump_version_minor_writes_version_file(tmp_kit: Path) -> None:
    old, new = versioning.bump_version(tmp_kit, "minor")
    assert old == "0.5.0"
    assert new == "0.6.0"
    assert (tmp_kit / "VERSION").read_text(encoding="utf-8").strip() == "0.6.0"


def test_bump_version_patch_writes_version_file(tmp_kit: Path) -> None:
    old, new = versioning.bump_version(tmp_kit, "patch")
    assert old == "0.5.0"
    assert new == "0.5.1"


def test_bump_version_major_from_pre_one_promotes_to_one(tmp_kit: Path) -> None:
    """Per PRJ-002: 0.x -> 1.0.0 is THE 1.0 milestone bump, and is allowed."""
    old, new = versioning.bump_version(tmp_kit, "major")
    assert old == "0.5.0"
    assert new == "1.0.0"
    assert (tmp_kit / "VERSION").read_text(encoding="utf-8").strip() == "1.0.0"


def test_bump_version_major_post_one_increments_major(tmp_kit: Path) -> None:
    """Post-1.0 major bumps still work for spec breakage."""
    (tmp_kit / "VERSION").write_text("1.4.2\n", encoding="utf-8")
    old, new = versioning.bump_version(tmp_kit, "major")
    assert old == "1.4.2"
    assert new == "2.0.0"


def test_bump_version_minor_broadens_requires_backbone_when_out_of_range(tmp_kit: Path) -> None:
    """0.5.0 -> 0.6.0 takes the upper bound `<0.6.0` out of range; should broaden to `<0.7.0`."""
    versioning.bump_version(tmp_kit, "minor")
    pkg = (tmp_kit / "adapters" / "claude-code" / "package.yaml").read_text(encoding="utf-8")
    assert 'requires_backbone: ">=0.1.0,<0.7.0"' in pkg


def test_bump_version_patch_within_range_does_not_touch_requires_backbone(tmp_kit: Path) -> None:
    """0.5.0 -> 0.5.1 is still inside `<0.6.0`; should leave the range unchanged."""
    versioning.bump_version(tmp_kit, "patch")
    pkg = (tmp_kit / "adapters" / "claude-code" / "package.yaml").read_text(encoding="utf-8")
    assert 'requires_backbone: ">=0.1.0,<0.6.0"' in pkg


def test_bump_version_preserves_other_package_yaml_content(tmp_kit: Path) -> None:
    """The regex-based rewrite must not disturb other fields in package.yaml."""
    versioning.bump_version(tmp_kit, "minor")
    pkg = (tmp_kit / "adapters" / "claude-code" / "package.yaml").read_text(encoding="utf-8")
    for line in (
        "schema_version: 1",
        "component:",
        "  kind: adapter",
        "  name: claude-code",
        "  version: 0.1.0",
    ):
        assert line in pkg


def test_bump_version_refuses_when_version_file_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match="no VERSION file"):
        versioning.bump_version(tmp_path, "minor")


def test_bump_version_refuses_invalid_semver(tmp_kit: Path) -> None:
    (tmp_kit / "VERSION").write_text("not.a.version\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="not valid PEP 440"):
        versioning.bump_version(tmp_kit, "minor")


def test_bump_output_reports_broaden_with_full_range(
    tmp_kit: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The `broadened ...` line should include both old and new full quoted ranges."""
    versioning.bump_version(tmp_kit, "minor")
    captured = capsys.readouterr()
    assert (
        'broadened adapters/claude-code/package.yaml: ">=0.1.0,<0.6.0" -> ">=0.1.0,<0.7.0"'
        in captured.out
    )


# --- tag_version tests --------------------------------------------------


import subprocess as _subprocess  # noqa: E402 — keep tag tests grouped here


@pytest.fixture
def tmp_kit_in_git(tmp_path: Path) -> Path:
    """A minimal kit inside a fresh git repo (so `git tag` has a HEAD to tag)."""
    repo = tmp_path
    _subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    _subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    _subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    source_kit = repo / ".pkit"
    source_kit.mkdir()
    (source_kit / "VERSION").write_text("1.0.0\n", encoding="utf-8")

    _subprocess.run(["git", "add", "."], cwd=repo, check=True)
    _subprocess.run(
        ["git", "commit", "-q", "-m", "chore(versioning): bump backbone to 1.0.0"],
        cwd=repo,
        check=True,
    )
    return source_kit


def _cleared(repo: Path) -> session_guard.Clearance:
    """The cross-repository guard's clearance for `repo`, outside any session:
    what a push to `origin` needs."""
    cleared = session_guard.clear(repo, confirmed=False, interactive=False)
    assert isinstance(cleared, session_guard.Clearance)
    return cleared


def test_tag_version_creates_annotated_tag(tmp_kit_in_git: Path) -> None:
    tag = versioning.tag_version(tmp_kit_in_git, push=False)
    assert tag == "v1.0.0"

    repo = tmp_kit_in_git.parent
    result = _subprocess.run(
        ["git", "tag", "-l", "v1.0.0"], capture_output=True, text=True, cwd=repo, check=True
    )
    assert result.stdout.strip() == "v1.0.0"


def test_tag_version_refuses_when_tag_exists(tmp_kit_in_git: Path) -> None:
    versioning.tag_version(tmp_kit_in_git)
    with pytest.raises(click.ClickException, match="already exists"):
        versioning.tag_version(tmp_kit_in_git)


def test_tag_version_refuses_when_version_file_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match="no VERSION file"):
        versioning.tag_version(tmp_path)


def test_tag_version_refuses_invalid_semver(tmp_kit_in_git: Path) -> None:
    (tmp_kit_in_git / "VERSION").write_text("not-a-version\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="not valid PEP 440"):
        versioning.tag_version(tmp_kit_in_git)


def test_tag_version_annotation_includes_commit_subject(tmp_kit_in_git: Path) -> None:
    """The annotation message should carry the bump commit's subject for context."""
    versioning.tag_version(tmp_kit_in_git)
    repo = tmp_kit_in_git.parent
    result = _subprocess.run(
        ["git", "tag", "-n100", "v1.0.0"],
        capture_output=True,
        text=True,
        cwd=repo,
        check=True,
    )
    assert "chore(versioning): bump backbone to 1.0.0" in result.stdout


def test_tag_version_push_invokes_git_push(
    tmp_kit_in_git: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--push should result in a `git push origin <tag>` invocation.

    Avoids mocking subprocess.run directly (pyright can't type-check the
    spy against subprocess.run's full overload set). Instead, configures
    an empty bare repo as the `origin` remote so the real `git push`
    succeeds without any network call.
    """
    repo = tmp_kit_in_git.parent
    bare_remote = repo.parent / "remote.git"
    _subprocess.run(["git", "init", "--bare", "-q", str(bare_remote)], check=True)
    _subprocess.run(["git", "remote", "add", "origin", str(bare_remote)], cwd=repo, check=True)

    versioning.tag_version(tmp_kit_in_git, push=True, clearance=_cleared(repo))

    # Verify the tag landed on the remote.
    result = _subprocess.run(
        ["git", "ls-remote", "--tags", str(bare_remote)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "refs/tags/v1.0.0" in result.stdout


# --- untag_version tests ------------------------------------------------


def test_untag_version_removes_local_tag(tmp_kit_in_git: Path) -> None:
    """`untag` deletes the local tag and leaves the repo without it."""
    versioning.tag_version(tmp_kit_in_git)
    versioning.untag_version(tmp_kit_in_git)

    repo = tmp_kit_in_git.parent
    result = _subprocess.run(
        ["git", "tag", "-l", "v1.0.0"], capture_output=True, text=True, cwd=repo, check=True
    )
    assert result.stdout.strip() == ""


def test_untag_version_refuses_when_tag_missing(tmp_kit_in_git: Path) -> None:
    with pytest.raises(click.ClickException, match="does not exist locally"):
        versioning.untag_version(tmp_kit_in_git)


def test_untag_version_prints_remote_hint_without_push(
    tmp_kit_in_git: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    versioning.tag_version(tmp_kit_in_git)
    versioning.untag_version(tmp_kit_in_git)
    captured = capsys.readouterr()
    assert "git push origin :refs/tags/v1.0.0" in captured.out


def test_untag_version_push_deletes_remote_tag(
    tmp_kit_in_git: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """--push should delete the tag on the configured origin remote."""
    repo = tmp_kit_in_git.parent
    # Allocate the bare remote in its own per-test directory (NOT in
    # repo.parent — that's the shared pytest session tmp root and would
    # collide with the bare remote created in test_tag_version_push).
    bare_remote = tmp_path_factory.mktemp("untag-remote") / "remote.git"
    _subprocess.run(["git", "init", "--bare", "-q", str(bare_remote)], check=True)
    _subprocess.run(["git", "remote", "add", "origin", str(bare_remote)], cwd=repo, check=True)

    versioning.tag_version(tmp_kit_in_git, push=True, clearance=_cleared(repo))
    # Sanity check: tag is on the remote.
    result = _subprocess.run(
        ["git", "ls-remote", "--tags", str(bare_remote)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "refs/tags/v1.0.0" in result.stdout

    versioning.untag_version(tmp_kit_in_git, push=True, clearance=_cleared(repo))

    # Tag should be gone locally and on the remote.
    local = _subprocess.run(
        ["git", "tag", "-l", "v1.0.0"], capture_output=True, text=True, cwd=repo, check=True
    )
    assert local.stdout.strip() == ""
    remote = _subprocess.run(
        ["git", "ls-remote", "--tags", str(bare_remote)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "refs/tags/v1.0.0" not in remote.stdout


# --- the cross-repository guard on a push (#1254) ------------------------


def _remote_tags(bare_remote: Path) -> str:
    return _subprocess.run(
        ["git", "ls-remote", "--tags", str(bare_remote)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _local_tags(repo: Path) -> str:
    return _subprocess.run(
        ["git", "tag", "-l"], capture_output=True, text=True, cwd=repo, check=True
    ).stdout.strip()


@pytest.fixture
def pushable(
    tmp_kit_in_git: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """The kit `pkit version` acts on, its `origin` a bare repository a push
    reaches without a network: (source kit, bare remote)."""
    bare_remote = tmp_path_factory.mktemp("guarded-remote") / "remote.git"
    _subprocess.run(["git", "init", "--bare", "-q", str(bare_remote)], check=True)
    _subprocess.run(
        ["git", "remote", "add", "origin", str(bare_remote)], cwd=tmp_kit_in_git.parent, check=True
    )
    monkeypatch.setattr(cli, "_target_kit", lambda: tmp_kit_in_git)
    return tmp_kit_in_git, bare_remote


@pytest.fixture
def rooted_elsewhere(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A session rooted in another repository than the kit's."""
    sessions.rooted_elsewhere(tmp_path_factory.mktemp("session"), monkeypatch)


@pytest.fixture
def guard_passes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """How the cross-repository guard passed each change it was asked to
    clear, in order — `refused` for one it refused."""
    passes: list[str] = []
    clear = session_guard.clear

    def recording(*args: Any, **kwargs: Any) -> session_guard.Clearance | session_guard.Refusal:
        passage = clear(*args, **kwargs)
        passes.append(passage.passed if isinstance(passage, session_guard.Clearance) else "refused")
        return passage

    monkeypatch.setattr(session_guard, "clear", recording)
    return passes


def _tagged_and_pushed(source_kit: Path, bare_remote: Path) -> None:
    """`v1.0.0` made and pushed with git alone, so no guard is asked."""
    repo = source_kit.parent
    _subprocess.run(["git", "tag", "-a", "v1.0.0", "-m", "v1.0.0"], cwd=repo, check=True)
    _subprocess.run(
        ["git", "push", "-q", "origin", "v1.0.0"], cwd=repo, check=True, capture_output=True
    )
    assert "refs/tags/v1.0.0" in _remote_tags(bare_remote)


@pytest.mark.usefixtures("rooted_elsewhere")
@pytest.mark.parametrize("command", ["tag", "untag"])
def test_a_push_from_another_repository_with_no_terminal_and_no_flag_is_refused_untouched(
    command: str, pushable: tuple[Path, Path], guard_passes: list[str]
) -> None:
    """No terminal to ask (the runner's input is not one) and no flag: the
    guard refuses before the tag is made or deleted, so nothing changes
    locally and nothing reaches `origin`."""
    source_kit, bare_remote = pushable
    if command == "untag":
        _tagged_and_pushed(source_kit, bare_remote)
    local_before, remote_before = _local_tags(source_kit.parent), _remote_tags(bare_remote)
    result = CliRunner().invoke(cli.main, ["version", command, "--push"])
    assert result.exit_code == 1
    assert "the cross-repository guard refused" in result.stderr
    assert "--allow-foreign-repo" in result.stderr
    assert guard_passes == ["refused"]
    assert _local_tags(source_kit.parent) == local_before
    assert _remote_tags(bare_remote) == remote_before


@pytest.mark.usefixtures("rooted_elsewhere")
def test_the_flag_confirms_a_push_from_another_repository(
    pushable: tuple[Path, Path], guard_passes: list[str]
) -> None:
    _, bare_remote = pushable
    tagged = CliRunner().invoke(cli.main, ["version", "tag", "--push", "--allow-foreign-repo"])
    assert tagged.exit_code == 0, tagged.output
    assert "refs/tags/v1.0.0" in _remote_tags(bare_remote)
    untagged = CliRunner().invoke(cli.main, ["version", "untag", "--push", "--allow-foreign-repo"])
    assert untagged.exit_code == 0, untagged.output
    assert "refs/tags/v1.0.0" not in _remote_tags(bare_remote)
    assert guard_passes == ["flag", "flag"]


def test_with_no_anchor_a_push_needs_no_flag(
    pushable: tuple[Path, Path], guard_passes: list[str]
) -> None:
    """A pipeline — `release-tag.yml` runs `version tag --push` — has no
    session's anchor: the guard does not fire, and passes undetermined."""
    _, bare_remote = pushable
    result = CliRunner().invoke(cli.main, ["version", "tag", "--push"])
    assert result.exit_code == 0, result.output
    assert "refs/tags/v1.0.0" in _remote_tags(bare_remote)
    assert guard_passes == ["undetermined"]


@pytest.mark.usefixtures("rooted_elsewhere")
def test_a_tag_made_only_locally_runs_no_guard(
    pushable: tuple[Path, Path], guard_passes: list[str]
) -> None:
    """Without `--push` nothing reaches the hosting service, so nothing is
    guarded, even in another repository than the session's."""
    source_kit, bare_remote = pushable
    assert CliRunner().invoke(cli.main, ["version", "tag"]).exit_code == 0
    assert CliRunner().invoke(cli.main, ["version", "untag"]).exit_code == 0
    assert guard_passes == []
    assert _local_tags(source_kit.parent) == "" and "v1.0.0" not in _remote_tags(bare_remote)


@pytest.mark.parametrize("function", [versioning.tag_version, versioning.untag_version])
def test_a_push_without_the_guards_clearance_is_not_made(function: Any, pushable: Any) -> None:
    source_kit, bare_remote = pushable
    with pytest.raises(TypeError, match="needs a clearance"):
        function(source_kit, push=True)
    assert _remote_tags(bare_remote) == ""


def test_untag_version_accepts_prerelease_tag(tmp_kit_in_git: Path) -> None:
    """Pre-release versions (e.g., `v1.2.0rc1`) are valid tag forms per PRJ-004."""
    (tmp_kit_in_git / "VERSION").write_text("1.2.0rc1\n", encoding="utf-8")
    versioning.tag_version(tmp_kit_in_git)
    versioning.untag_version(tmp_kit_in_git)

    repo = tmp_kit_in_git.parent
    result = _subprocess.run(
        ["git", "tag", "-l", "v1.2.0rc1"],
        capture_output=True,
        text=True,
        cwd=repo,
        check=True,
    )
    assert result.stdout.strip() == ""


# --- unbump_version tests -----------------------------------------------


@pytest.fixture
def tmp_kit_in_git_with_component(tmp_path: Path) -> Path:
    """An in-git kit with a kit-shipped package.yaml — drives broaden/narrow tests."""
    repo = tmp_path
    _subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    _subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    _subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    source_kit = repo / ".pkit"
    source_kit.mkdir()
    (source_kit / "VERSION").write_text("0.5.0\n", encoding="utf-8")

    adapter = source_kit / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: adapter\n"
        "  name: claude-code\n"
        "  version: 0.1.0\n"
        'requires_backbone: ">=0.1.0,<0.6.0"\n',
        encoding="utf-8",
    )

    _subprocess.run(["git", "add", "."], cwd=repo, check=True)
    _subprocess.run(
        ["git", "commit", "-q", "-m", "chore(versioning): seed"],
        cwd=repo,
        check=True,
    )
    return source_kit


def test_unbump_version_reverts_minor(tmp_kit_in_git_with_component: Path) -> None:
    """`unbump` undoes `bump minor` end-to-end: VERSION + requires_backbone."""
    versioning.bump_version(tmp_kit_in_git_with_component, "minor")
    assert (tmp_kit_in_git_with_component / "VERSION").read_text().strip() == "0.6.0"

    old, new = versioning.unbump_version(tmp_kit_in_git_with_component)
    assert old == "0.6.0"
    assert new == "0.5.0"
    assert (tmp_kit_in_git_with_component / "VERSION").read_text().strip() == "0.5.0"

    pkg = (tmp_kit_in_git_with_component / "adapters" / "claude-code" / "package.yaml").read_text(
        encoding="utf-8"
    )
    assert 'requires_backbone: ">=0.1.0,<0.6.0"' in pkg


def test_unbump_version_reverts_patch(tmp_kit_in_git_with_component: Path) -> None:
    """1.2.3 -> 1.2.2 (decrement patch when patch > 0)."""
    (tmp_kit_in_git_with_component / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    old, new = versioning.unbump_version(tmp_kit_in_git_with_component)
    assert old == "1.2.3"
    assert new == "1.2.2"


def test_unbump_version_refuses_while_tag_exists(tmp_kit_in_git_with_component: Path) -> None:
    """Ordering: must `untag` before `unbump`."""
    versioning.bump_version(tmp_kit_in_git_with_component, "minor")
    versioning.tag_version(tmp_kit_in_git_with_component)

    with pytest.raises(click.ClickException, match="still exists locally"):
        versioning.unbump_version(tmp_kit_in_git_with_component)


def test_unbump_version_refuses_prerelease(tmp_kit_in_git_with_component: Path) -> None:
    """Pre-release decrements are ambiguous — refuse with a clear message."""
    (tmp_kit_in_git_with_component / "VERSION").write_text("1.2.0rc1\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="not strict semver"):
        versioning.unbump_version(tmp_kit_in_git_with_component)


def test_unbump_version_refuses_at_major_boundary(tmp_kit_in_git_with_component: Path) -> None:
    """1.0.0 -> unclear (would cross a major / go pre-1.0); refuse."""
    (tmp_kit_in_git_with_component / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="cannot determine prior version"):
        versioning.unbump_version(tmp_kit_in_git_with_component)


def test_unbump_version_refuses_at_pre_one_boundary(tmp_kit_in_git_with_component: Path) -> None:
    """0.0.0 has no prior — refuse."""
    (tmp_kit_in_git_with_component / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="cannot determine prior version"):
        versioning.unbump_version(tmp_kit_in_git_with_component)


def test_unbump_version_only_narrows_matching_upper_bounds(
    tmp_kit_in_git_with_component: Path,
) -> None:
    """A package.yaml with an already-wider bound is left alone on unbump."""
    # Manually widen the package.yaml beyond what a 0.5 -> 0.6 broaden
    # would produce (`<0.7.0`); should NOT be touched by unbump.
    pkg_file = tmp_kit_in_git_with_component / "adapters" / "claude-code" / "package.yaml"
    pkg_file.write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: adapter\n"
        "  name: claude-code\n"
        "  version: 0.1.0\n"
        'requires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (tmp_kit_in_git_with_component / "VERSION").write_text("0.6.0\n", encoding="utf-8")

    versioning.unbump_version(tmp_kit_in_git_with_component)
    pkg = pkg_file.read_text(encoding="utf-8")
    assert 'requires_backbone: ">=0.1.0,<2.0.0"' in pkg


def test_unbump_output_reports_narrow_with_full_range(
    tmp_kit_in_git_with_component: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The `narrowed ...` line includes both the old and new quoted ranges."""
    versioning.bump_version(tmp_kit_in_git_with_component, "minor")
    capsys.readouterr()  # drop bump output

    versioning.unbump_version(tmp_kit_in_git_with_component)
    captured = capsys.readouterr()
    assert (
        'narrowed adapters/claude-code/package.yaml: ">=0.1.0,<0.7.0" -> ">=0.1.0,<0.6.0"'
        in captured.out
    )


# --- bump --pre / bump pre / promote tests ------------------------------


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("rc", "1.2.0rc1"),
        ("a", "1.2.0a1"),
        ("b", "1.2.0b1"),
    ],
)
def test_bump_version_pre_starts_counter_at_one(
    tmp_kit: Path, kind: versioning.PreKind, expected: str
) -> None:
    """`bump minor --pre <kind>` produces `X.Y.0<kind>1`."""
    (tmp_kit / "VERSION").write_text("1.1.0\n", encoding="utf-8")
    old, new = versioning.bump_version(tmp_kit, "minor", pre=kind)
    assert old == "1.1.0"
    assert new == expected
    assert (tmp_kit / "VERSION").read_text(encoding="utf-8").strip() == expected


def test_bump_version_pre_does_not_broaden(tmp_kit: Path) -> None:
    """Pre-release bumps must NOT broaden requires_backbone."""
    versioning.bump_version(tmp_kit, "minor", pre="rc")
    pkg = (tmp_kit / "adapters" / "claude-code" / "package.yaml").read_text(encoding="utf-8")
    # The fixture sets upper to `<0.6.0`; without `--pre` this would
    # have broadened to `<0.7.0`. With `--pre` it must be untouched.
    assert 'requires_backbone: ">=0.1.0,<0.6.0"' in pkg


def test_bump_pre_increments_counter(tmp_kit: Path) -> None:
    """`bump pre` on `1.2.0rc1` -> `1.2.0rc2`."""
    (tmp_kit / "VERSION").write_text("1.2.0rc1\n", encoding="utf-8")
    old, new = versioning.bump_pre(tmp_kit)
    assert old == "1.2.0rc1"
    assert new == "1.2.0rc2"


def test_bump_pre_handles_double_digit_counter(tmp_kit: Path) -> None:
    """No off-by-one when the counter crosses single-digit boundaries."""
    (tmp_kit / "VERSION").write_text("1.2.0rc9\n", encoding="utf-8")
    _, new = versioning.bump_pre(tmp_kit)
    assert new == "1.2.0rc10"


def test_bump_pre_refuses_when_no_suffix(tmp_kit: Path) -> None:
    """`bump pre` on a stable version refuses (use `bump <segment> --pre <kind>`)."""
    (tmp_kit / "VERSION").write_text("1.2.0\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="no pre-release suffix to increment"):
        versioning.bump_pre(tmp_kit)


def test_promote_version_drops_suffix(tmp_kit: Path) -> None:
    """`promote` on `1.2.0rc3` -> `1.2.0`."""
    (tmp_kit / "VERSION").write_text("1.2.0rc3\n", encoding="utf-8")
    old, new = versioning.promote_version(tmp_kit)
    assert old == "1.2.0rc3"
    assert new == "1.2.0"
    assert (tmp_kit / "VERSION").read_text(encoding="utf-8").strip() == "1.2.0"


def test_promote_version_refuses_when_no_suffix(tmp_kit: Path) -> None:
    """`promote` on a stable version refuses."""
    (tmp_kit / "VERSION").write_text("1.2.0\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="no pre-release suffix to drop"):
        versioning.promote_version(tmp_kit)


def test_promote_version_does_not_broaden(tmp_kit: Path) -> None:
    """`promote` does not broaden — broaden is gated on `bump <segment>` (no `--pre`)."""
    (tmp_kit / "VERSION").write_text("0.6.0rc1\n", encoding="utf-8")
    versioning.promote_version(tmp_kit)
    pkg = (tmp_kit / "adapters" / "claude-code" / "package.yaml").read_text(encoding="utf-8")
    # The fixture sets upper to `<0.6.0`; promote on `0.6.0rc1` -> `0.6.0`
    # without broadening leaves it at `<0.6.0`.
    assert 'requires_backbone: ">=0.1.0,<0.6.0"' in pkg


def test_tag_version_accepts_prerelease(tmp_kit_in_git: Path) -> None:
    """`v1.2.0rc1` is a valid tag form per PRJ-004."""
    (tmp_kit_in_git / "VERSION").write_text("1.2.0rc1\n", encoding="utf-8")
    tag = versioning.tag_version(tmp_kit_in_git)
    assert tag == "v1.2.0rc1"


def test_bump_version_from_prerelease_strips_suffix(tmp_kit: Path) -> None:
    """`bump patch` on `1.2.0rc1` computes the segment bump from the
    stable trio (1.2.0 -> 1.2.1). The user has explicitly chosen to
    leave the pre-release line by bumping a segment.
    """
    (tmp_kit / "VERSION").write_text("1.2.0rc1\n", encoding="utf-8")
    _, new = versioning.bump_version(tmp_kit, "patch")
    assert new == "1.2.1"


# --- the declared floor raise (PRJ-002 D4) -----------------------------------


def _package_with(tmp_path: Path, requires_backbone_line: str) -> Path:
    pkg = tmp_path / "package.yaml"
    pkg.write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        "  name: houseware\n"
        "  version: 0.3.0\n"
        '# The floor is 1.2.0: requires_backbone: ">=1.2.0" names the reason.\n'
        f"{requires_backbone_line}\n",
        encoding="utf-8",
    )
    return pkg


@pytest.mark.parametrize(
    ("line", "floor"),
    [
        ('requires_backbone: ">=1.2.0,<2.0.0"', "1.2.0"),
        ('requires_backbone:   ">=1.2.0,<2.0.0"  # why', "1.2.0"),
        ('requires_backbone: ">=1.2.0"', "1.2.0"),
        # Shapes whose floor the release does not raise.
        ("requires_backbone: '>=1.2.0,<2.0.0'", None),
        ('requires_backbone: ">= 1.2.0,<2.0.0"', None),
        ('requires_backbone: ">=1.2.0, <2.0.0"', None),
        ('requires_backbone: "<2.0.0,>=1.2.0"', None),
        ('requires_backbone: ">=1.2.0rc1,<2.0.0"', None),
        ('requires_backbone: "*"', None),
        ("requires_backbone: >=1.2.0", None),
    ],
)
def test_requires_backbone_floor_reads_the_ranges_whose_floor_the_release_raises(
    tmp_path: Path, line: str, floor: str | None
) -> None:
    text = _package_with(tmp_path, line).read_text(encoding="utf-8")
    assert versioning.requires_backbone_floor(text) == floor


def test_raise_floor_rewrites_only_the_floor(tmp_path: Path) -> None:
    """The lower bound moves; the upper bound, the trailing comment and a comment
    that mentions the key stay as written."""
    pkg = _package_with(tmp_path, 'requires_backbone: ">=1.2.0,<2.0.0"  # floor: report link')

    changed = versioning.raise_component_requires_backbone_floor(pkg, "1.6.0")

    assert changed == ">=1.2.0 -> >=1.6.0"
    text = pkg.read_text(encoding="utf-8")
    assert 'requires_backbone: ">=1.6.0,<2.0.0"  # floor: report link\n' in text
    assert '# The floor is 1.2.0: requires_backbone: ">=1.2.0" names the reason.\n' in text


def test_raise_floor_is_raise_only(tmp_path: Path) -> None:
    pkg = _package_with(tmp_path, 'requires_backbone: ">=1.7.0,<2.0.0"')
    before = pkg.read_text(encoding="utf-8")

    assert versioning.raise_component_requires_backbone_floor(pkg, "1.6.0") is None
    assert versioning.raise_component_requires_backbone_floor(pkg, "1.7.0") is None
    assert pkg.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "comment",
    [
        '# was requires_backbone: ">=1.0.0,<1.4.0"',
        '  # requires_backbone: ">=1.0.0,<1.4.0"',
        'requires_backbone_note: ">=1.0.0,<1.4.0"',
    ],
)
def test_the_broaden_and_the_floor_read_the_key_not_a_line_mentioning_it(comment: str) -> None:
    """Both rewrites locate the range through one prefix — the top-level key at the
    start of a line — so a comment quoting an older range is never read, and the
    two always rewrite the same line."""
    text = f'{comment}\nrequires_backbone: ">=1.0.0,<1.5.0"\n'

    broadened = versioning.broaden_requires_backbone(text, "1.5.0")
    assert broadened is not None
    assert broadened[0] == f'{comment}\nrequires_backbone: ">=1.0.0,<1.6.0"\n'
    assert versioning.requires_backbone_floor(text) == "1.0.0"
    raised = versioning.raise_requires_backbone_floor(broadened[0], "1.5.0")
    assert raised is not None
    assert raised[0] == f'{comment}\nrequires_backbone: ">=1.5.0,<1.6.0"\n'
    assert versioning.requires_backbone_range(raised[0]) == ">=1.5.0,<1.6.0"


def test_raise_floor_refuses_a_range_with_no_floor(tmp_path: Path) -> None:
    pkg = _package_with(tmp_path, 'requires_backbone: "*"')
    with pytest.raises(click.ClickException, match=r"whose floor can be raised to 1\.6\.0"):
        versioning.raise_component_requires_backbone_floor(pkg, "1.6.0")


@pytest.mark.parametrize(
    ("version", "ceiling", "at_or_below"),
    [
        ("1.4.0", "1.5.0", True),
        ("1.5.0", "1.5.0", True),
        ("1.5.1", "1.5.0", False),
        ("1.6.0", "1.5.0", False),
        # A release sorts above its own pre-releases, which precede it.
        ("1.4.9", "1.5.0rc1", True),
        ("1.5.0", "1.5.0rc1", False),
    ],
)
def test_is_at_or_below_orders_by_pep_440(version: str, ceiling: str, at_or_below: bool) -> None:
    assert versioning.is_at_or_below(version, ceiling) is at_or_below


def test_is_at_or_below_refuses_what_is_not_a_version() -> None:
    with pytest.raises(click.ClickException, match="'latest' is not valid PEP 440"):
        versioning.is_at_or_below("latest", "1.5.0")
