"""Tests for the notes-only GitHub Release path (`pkit release publish-notes`, #485).

The logic splits into a pure CHANGELOG-section extractor
(`extract_changelog_section`) and thin `gh` wrappers
(`_gh_release_exists` / `_gh_release_create_notes` / `_gh_release_edit_notes`).
The extractor is tested directly; `publish_release_notes` is tested with
`subprocess.run` monkeypatched so the argv passed to `gh` is asserted on — no
real Release, no network, no hardcoded repo — which is how "notes only, no
artifact" is *proven* rather than assumed.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import release

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


def _fake_run_factory(release_exists: bool, calls: list[dict]):
    """A `subprocess.run` stand-in: records argv + kwargs; view rc encodes existence."""

    def fake_run(cmd: list[str], **kwargs: object) -> _FakeCompleted:
        calls.append({"cmd": cmd, "kwargs": kwargs})
        if cmd[:3] == ["gh", "release", "view"]:
            return _FakeCompleted(returncode=0 if release_exists else 1)
        return _FakeCompleted(returncode=0)

    return fake_run


def _write_changelog(tmp_path: Path) -> Path:
    (tmp_path / "CHANGELOG.md").write_text(_TWO_SECTION_CHANGELOG, encoding="utf-8")
    return tmp_path


def _create_cmd(calls: list[dict]) -> list[str]:
    return next(c["cmd"] for c in calls if c["cmd"][:3] == ["gh", "release", "create"])


def test_publish_creates_notes_only_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_changelog(tmp_path)
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(False, calls))

    message = release.publish_release_notes(repo_root, "1.141.0")

    create = _create_cmd(calls)
    notes = release.extract_changelog_section(_TWO_SECTION_CHANGELOG, "1.141.0")
    # Notes-only, proven by exact argv: the ONLY positional after
    # `gh release create` is the tag (no trailing file path / artifact upload),
    # the body is supplied via --notes, --verify-tag guards a missing tag, and
    # there is no --generate-notes (we supply our own notes).
    assert create == [
        "gh", "release", "create", "v1.141.0",
        "--title", "v1.141.0",
        "--notes", notes,
        "--verify-tag",
    ]
    assert "Ship the notes-only GitHub Release. ([#485])" in notes
    assert "[#485]:" in notes
    assert "Published notes-only GitHub Release v1.141.0" in message


def test_publish_updates_when_release_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_changelog(tmp_path)
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(True, calls))

    message = release.publish_release_notes(repo_root, "1.141.0")

    # Idempotent: an existing Release is edited, never re-created.
    assert not any(c["cmd"][:3] == ["gh", "release", "create"] for c in calls)
    edit = next(c["cmd"] for c in calls if c["cmd"][:3] == ["gh", "release", "edit"])
    assert edit[3] == "v1.141.0"
    assert "--notes" in edit
    assert "--generate-notes" not in edit
    assert "Updated notes-only GitHub Release v1.141.0" in message


def test_publish_dry_run_does_not_call_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_changelog(tmp_path)

    def boom(*args: object, **kwargs: object) -> None:
        pytest.fail("--dry-run must not call gh")

    monkeypatch.setattr(release.subprocess, "run", boom)

    message = release.publish_release_notes(repo_root, "1.141.0", dry_run=True)

    assert "[dry-run]" in message
    assert "no artifact" in message
    assert "Ship the notes-only GitHub Release. ([#485])" in message


def test_publish_missing_version_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_changelog(tmp_path)
    monkeypatch.setattr(
        release.subprocess, "run", lambda *a, **k: pytest.fail("must not call gh")
    )
    with pytest.raises(click.ClickException) as exc:
        release.publish_release_notes(repo_root, "9.9.9")
    assert "no section for version '9.9.9'" in str(exc.value)


def test_publish_derives_repo_from_ambient_gh_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project-neutral: no hardcoded owner/repo — cwd is the repo, no --repo flag."""
    repo_root = _write_changelog(tmp_path)
    calls: list[dict] = []
    monkeypatch.setattr(release.subprocess, "run", _fake_run_factory(False, calls))

    release.publish_release_notes(repo_root, "1.141.0")

    for call in calls:
        assert call["kwargs"]["cwd"] == repo_root  # ambient context = the working dir
        assert "--repo" not in call["cmd"]  # no owner/repo baked in
