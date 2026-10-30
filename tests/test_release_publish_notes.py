"""Tests for the notes-only GitHub Release path (`pkit release publish-notes`, #485).

The logic splits into a pure CHANGELOG-section extractor
(`extract_changelog_section`), the short notes that replace a section longer
than a Release keeps (`short_release_notes`, #2384), and thin `gh` wrappers
(`_gh_release_exists` / `_gh_release_create_notes` / `_gh_release_edit_notes`).
The extractor is tested directly; `publish_release_notes` is tested with
`subprocess.run` monkeypatched so the argv passed to `gh`, and the notes on its
standard input, are asserted on — no real Release, no network, no hardcoded
repo — which is how "notes only, no artifact" is *proven* rather than assumed.
The cross-repository guard the command runs at its entry (#1254) is tested
through the CLI on real repositories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import pytest
from click.testing import CliRunner

from project_kit import cli, release, session_guard
from tests import sessions

# --- CHANGELOG-section extraction (pure) -----------------------------


# Two sections so extraction of the top one must stop at the next `## ` heading;
# each carries its own trailing `[#N]:` reference-link block.
_TWO_SECTION_CHANGELOG = """# Changelog

Some preamble under the H1.

## 1.141.0 — 2026-07-05

### Added
- Ship the notes-only GitHub Release. ([#485])

[#485]: https://github.com/owner/repo/pull/485

## 1.140.0 — 2026-07-04

### Changed
- Older change. ([#465])

[#465]: https://github.com/owner/repo/pull/465
"""


def test_extract_returns_the_section_with_its_ref_block() -> None:
    section = release.extract_changelog_section(_TWO_SECTION_CHANGELOG, "1.141.0")
    assert section.startswith("## 1.141.0 — 2026-07-05")
    assert "Ship the notes-only GitHub Release. ([#485])" in section
    # The trailing reference-link block for THIS section is included so links resolve.
    assert "[#485]: https://github.com/owner/repo/pull/485" in section
    # It stops before the next release section — no bleed of the older entry.
    assert "1.140.0" not in section
    assert "[#465]" not in section


def test_extract_bottom_section_runs_to_end_of_file() -> None:
    section = release.extract_changelog_section(_TWO_SECTION_CHANGELOG, "1.140.0")
    assert section.startswith("## 1.140.0 — 2026-07-04")
    assert "[#465]: https://github.com/owner/repo/pull/465" in section
    assert section.endswith("\n")


def test_extract_matches_bracketed_kac_heading() -> None:
    text = "# Changelog\n\n## [1.2.0] - 2026-01-01\n\n### Added\n- A thing.\n"
    section = release.extract_changelog_section(text, "1.2.0")
    assert "A thing." in section


def test_extract_missing_version_errors_clearly() -> None:
    with pytest.raises(click.ClickException) as exc:
        release.extract_changelog_section(_TWO_SECTION_CHANGELOG, "9.9.9")
    assert "no section for version '9.9.9'" in str(exc.value)


def test_extract_current_repo_changelog_1_140_0() -> None:
    """The real CHANGELOG.md in this repo extracts its `1.140.0` section."""
    repo_root = Path(__file__).resolve().parent.parent
    text = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
    section = release.extract_changelog_section(text, "1.140.0")
    assert section.startswith("## 1.140.0 — 2026-07-04")
    assert "one install works everywhere. ([#465])" in section
    assert "[#465]: https://github.com/aleskalfas/project-kit/pull/465" in section


# --- publish_release_notes (subprocess.run monkeypatched) ------------


class _FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


_ORIGIN = "https://github.com/owner/repo.git"


def _fake_run_factory(release_exists: bool, calls: list[dict]):
    """A `subprocess.run` stand-in: records argv + kwargs; view rc encodes
    existence, and `origin` is a GitHub repository."""

    def fake_run(cmd: list[str], **kwargs: object) -> _FakeCompleted:
        calls.append({"cmd": cmd, "kwargs": kwargs})
        if cmd[:3] == ["gh", "release", "view"]:
            return _FakeCompleted(returncode=0 if release_exists else 1)
        if cmd[:4] == ["git", "remote", "get-url", "origin"]:
            return _FakeCompleted(stdout=f"{_ORIGIN}\n")
        return _FakeCompleted(returncode=0)

    return fake_run


def _write_changelog(tmp_path: Path, text: str = _TWO_SECTION_CHANGELOG) -> Path:
    (tmp_path / "CHANGELOG.md").write_text(text, encoding="utf-8")
    return tmp_path


def _long_changelog() -> str:
    """A changelog whose 2.0.0 section is longer than a Release keeps: entries
    of the backbone and of two components, one released before and one not,
    over older sections that record the earlier versions."""
    entry = "A change described at length, " + "word " * 40
    entries = []
    while sum(len(e) for e in entries) <= release.RELEASE_BODY_LIMIT:
        entries.append(f"- {entry}([#900])")
        entries.append(f"- **pm 0.55.0** — {entry}")
        entries.append(f"- **fresh 0.1.0** — {entry}")
    return (
        "# Changelog\n\n## 2.0.0 — 2026-10-30\n\n### Added\n"
        + "\n".join(entries)
        + "\n\n[#900]: https://github.com/owner/repo/pull/900\n\n"
        "## 1.149.0 — 2026-08-24\n\n### Fixed\n- **pm 0.54.0** — Newer pm.\n\n"
        "## 1.148.0 — 2026-08-11\n\n### Fixed\n- **pm 0.53.0** — Older pm.\n"
    )


def _gh_call(calls: list[dict], verb: str) -> dict:
    return next(c for c in calls if c["cmd"][:3] == ["gh", "release", verb])


def _cleared(repo_root: Path) -> session_guard.Clearance:
    """The cross-repository guard's clearance for `repo_root`, outside any session."""
    cleared = session_guard.clear(repo_root, confirmed=False, interactive=False)
    assert isinstance(cleared, session_guard.Clearance)
    return cleared


def _create_cmd(calls: list[dict]) -> list[str]:
    return next(c["cmd"] for c in calls if c["cmd"][:3] == ["gh", "release", "create"])


def test_publish_creates_notes_only_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_changelog(tmp_path)
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(False, calls))

    message = release.publish_release_notes(repo_root, "1.141.0", clearance=_cleared(repo_root))

    create = _create_cmd(calls)
    notes = release.extract_changelog_section(_TWO_SECTION_CHANGELOG, "1.141.0")
    # Notes-only, proven by exact argv: the ONLY positional after
    # `gh release create` is the tag (no trailing file path / artifact upload),
    # the body is read from standard input (`--notes-file -`), --verify-tag
    # guards a missing tag, and there is no --generate-notes (we supply our own
    # notes).
    assert create == [
        "gh",
        "release",
        "create",
        "v1.141.0",
        "--title",
        "v1.141.0",
        "--notes-file",
        "-",
        "--verify-tag",
    ]
    # A section within the limit is published whole, on standard input.
    assert _gh_call(calls, "create")["kwargs"]["input"] == notes
    assert "Ship the notes-only GitHub Release. ([#485])" in notes
    assert "[#485]:" in notes
    assert "Published notes-only GitHub Release v1.141.0" in message
    assert "its whole changelog section" in message


def test_publish_updates_when_release_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_changelog(tmp_path)
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(True, calls))

    message = release.publish_release_notes(repo_root, "1.141.0", clearance=_cleared(repo_root))

    # Idempotent: an existing Release is edited, never re-created.
    assert not any(c["cmd"][:3] == ["gh", "release", "create"] for c in calls)
    edit = _gh_call(calls, "edit")
    assert edit["cmd"] == ["gh", "release", "edit", "v1.141.0", "--notes-file", "-"]
    assert edit["kwargs"]["input"] == release.extract_changelog_section(
        _TWO_SECTION_CHANGELOG, "1.141.0"
    )
    assert "Updated notes-only GitHub Release v1.141.0" in message


def test_publish_dry_run_does_not_call_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _write_changelog(tmp_path)

    def boom(*args: object, **kwargs: object) -> None:
        pytest.fail("--dry-run must not call gh")

    monkeypatch.setattr(release.subprocess, "run", boom)

    message = release.publish_release_notes(
        repo_root, "1.141.0", clearance=_cleared(repo_root), dry_run=True
    )

    assert "[dry-run]" in message
    assert "no artifact" in message
    assert "its whole changelog section" in message
    assert "Ship the notes-only GitHub Release. ([#485])" in message


# --- a section longer than a Release keeps (#2384) ---------------------


_LONG_LINK = "https://github.com/owner/repo/blob/v2.0.0/CHANGELOG.md#200--2026-10-30"


@pytest.mark.parametrize("exists", [False, True], ids=["create", "edit"])
def test_a_long_section_is_published_as_short_notes_on_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exists: bool
) -> None:
    text = _long_changelog()
    assert len(release.extract_changelog_section(text, "2.0.0")) > release.RELEASE_BODY_LIMIT
    repo_root = _write_changelog(tmp_path, text)
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(exists, calls))

    message = release.publish_release_notes(repo_root, "2.0.0", clearance=_cleared(repo_root))

    call = _gh_call(calls, "edit" if exists else "create")
    notes = call["kwargs"]["input"]
    assert "--notes-file" in call["cmd"] and "--notes" not in call["cmd"]
    assert notes not in call["cmd"]
    assert len(notes) <= release.RELEASE_BODY_LIMIT
    assert notes == release.short_release_notes(
        text, "2.0.0", changelog_url="https://github.com/owner/repo/blob/v2.0.0/CHANGELOG.md"
    )
    assert notes.startswith("## 2.0.0 — 2026-10-30\n")
    assert f"]({_LONG_LINK})" in notes
    assert "- backbone 1.149.0 → 2.0.0\n" in notes
    assert "- fresh 0.1.0\n" in notes
    assert "- pm 0.54.0 → 0.55.0\n" in notes
    assert "A change described at length" not in notes
    assert "short notes" in message and "past the 125,000" in message


def test_the_dry_run_of_a_long_section_shows_the_short_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_changelog(tmp_path, _long_changelog())
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(False, calls))

    message = release.publish_release_notes(
        repo_root, "2.0.0", clearance=_cleared(repo_root), dry_run=True
    )

    assert not any(c["cmd"][0] == "gh" for c in calls)
    assert message.startswith("[dry-run] would publish notes-only GitHub Release v2.0.0")
    assert "with short notes, as its changelog section is" in message
    assert _LONG_LINK in message
    assert "A change described at length" not in message


def test_short_notes_without_a_repository_name_the_section() -> None:
    notes = release.short_release_notes(_long_changelog(), "2.0.0", changelog_url=None)
    assert "They are in the 2.0.0 section of `CHANGELOG.md`." in notes
    assert "](" not in notes


def test_section_releases_name_each_bump_from_the_changelog() -> None:
    assert release.changelog_section_releases(_long_changelog(), "2.0.0") == [
        ("backbone", "1.149.0", "2.0.0"),
        ("fresh", None, "0.1.0"),
        ("pm", "0.54.0", "0.55.0"),
    ]
    # The oldest section has nothing older to bump from.
    assert release.changelog_section_releases(_long_changelog(), "1.148.0") == [
        ("backbone", None, "1.148.0"),
        ("pm", None, "0.53.0"),
    ]


def test_the_2_0_0_section_of_this_repo_is_published_short() -> None:
    """The release that met the limit: its section is past it, its short
    notes fit and link to the section at its tag."""
    repo_root = Path(__file__).resolve().parent.parent
    text = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert len(release.extract_changelog_section(text, "2.0.0")) > release.RELEASE_BODY_LIMIT
    url = "https://github.com/aleskalfas/project-kit/blob/v2.0.0/CHANGELOG.md"
    notes = release.short_release_notes(text, "2.0.0", changelog_url=url)
    assert len(notes) <= release.RELEASE_BODY_LIMIT
    assert f"]({url}#200--2026-10-30)" in notes
    assert "- backbone 1.149.0 → 2.0.0\n" in notes


def test_publish_missing_version_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _write_changelog(tmp_path)
    monkeypatch.setattr(release.subprocess, "run", lambda *a, **k: pytest.fail("must not call gh"))
    with pytest.raises(click.ClickException) as exc:
        release.publish_release_notes(repo_root, "9.9.9", clearance=_cleared(repo_root))
    assert "no section for version '9.9.9'" in str(exc.value)


def test_publish_derives_repo_from_ambient_gh_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project-neutral: no hardcoded owner/repo — cwd is the repo, no --repo flag."""
    repo_root = _write_changelog(tmp_path)
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(False, calls))

    release.publish_release_notes(repo_root, "1.141.0", clearance=_cleared(repo_root))

    for call in calls:
        assert call["kwargs"]["cwd"] == repo_root  # ambient context = the working dir
        assert "--repo" not in call["cmd"]  # no owner/repo baked in


# --- the cross-repository guard (#1254) -------------------------------


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str, bool]]:
    """`publish_release_notes` stubbed: each run's repository, how its
    clearance passed, and whether it was a dry run. A run the guard refused
    reaches none of it, so nothing is read from GitHub or sent to it."""
    runs: list[tuple[Path, str, bool]] = []

    def publish(
        repo_root: Path, version: str, *, clearance: session_guard.Clearance, dry_run: bool
    ) -> str:
        runs.append((repo_root, clearance.passed, dry_run))
        return f"Published notes-only GitHub Release v{version}."

    monkeypatch.setattr(cli, "publish_release_notes", publish)
    return runs


@pytest.fixture
def foreign(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A session rooted in one repository, and `publish-notes` run in another."""
    _, target = sessions.rooted_elsewhere(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_target_kit", lambda: target / ".pkit")
    return target


def _publish(*args: str) -> Any:
    return CliRunner().invoke(cli.main, ["release", "publish-notes", "1.141.0", *args])


@pytest.mark.parametrize("dry_run", [[], ["--dry-run"]], ids=["run", "dry-run"])
def test_in_another_repository_with_no_terminal_and_no_flag_nothing_is_published(
    foreign: Path, published: list[tuple[Path, str, bool]], dry_run: list[str]
) -> None:
    result = _publish(*dry_run)
    assert result.exit_code == 1
    assert "the cross-repository guard refused" in result.stderr
    assert "--allow-foreign-repo" in result.stderr and "Nothing was published" in result.stderr
    assert published == []


def test_the_flag_confirms_publishing_in_another_repository(
    foreign: Path, published: list[tuple[Path, str, bool]]
) -> None:
    result = _publish("--allow-foreign-repo")
    assert result.exit_code == 0
    assert published == [(foreign, "flag", False)]


def test_with_no_anchor_it_publishes_undetermined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, published: list[tuple[Path, str, bool]]
) -> None:
    """A pipeline — `release-tag.yml` runs it — has no session's anchor: the
    guard does not fire, and needs no flag."""
    target = sessions.repository(tmp_path / "target", "https://github.com/octo/project.git")
    monkeypatch.setattr(cli, "_target_kit", lambda: target / ".pkit")
    result = _publish()
    assert result.exit_code == 0
    assert published == [(target, "undetermined", False)]


def test_a_publish_without_the_guards_clearance_asks_github_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clearance for another directory stops it before `gh` is asked."""
    repo_root = _write_changelog(tmp_path)
    monkeypatch.setattr(release.subprocess, "run", lambda *a, **k: pytest.fail("asked gh"))
    with pytest.raises(ValueError, match="the clearance is for"):
        release.publish_release_notes(
            repo_root, "1.141.0", clearance=_cleared(tmp_path / "elsewhere")
        )
