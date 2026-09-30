"""Tests for the surface-without-changeset CI guard (PRJ-002): surface
detection + the escape hatches."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import changesets, release
from project_kit.cli import main


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_repo(tmp_path: Path) -> Path:
    """A git repo with a source kit + one component, committed as `main`."""
    repo = tmp_path
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")

    source_kit = repo / ".pkit"
    (source_kit / "cli").mkdir(parents=True)
    (source_kit / "VERSION").write_text("1.5.0\n", encoding="utf-8")
    (source_kit / "cli" / "README.md").write_text("cli spec\n", encoding="utf-8")

    adapter = source_kit / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
        '  version: 0.5.0\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    (repo / "src" / "seed.txt").write_text("x\n", encoding="utf-8")

    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    _git(repo, "branch", "-M", "main")
    _git(repo, "checkout", "-q", "-b", "feature")
    return source_kit


def _commit_change(source_kit: Path, relpath: str, content: str = "changed\n") -> None:
    repo = source_kit.parent
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"touch {relpath}")


def _add_changeset(source_kit: Path, component: str, kind: str) -> None:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{component}-{kind}.yaml").write_text(
        f"component: {component}\nkind: {kind}\nbody: note\n", encoding="utf-8"
    )


def test_touched_backbone_via_src_change_without_changeset_fails(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "src/project_kit/foo.py")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == ["backbone"]
    assert result.missing == ["backbone"]
    assert not result.ok


def test_touched_backbone_with_changeset_passes(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _add_changeset(source_kit, "backbone", "minor")
    _commit_change(source_kit, "src/project_kit/foo.py")
    result = release.check_changesets(source_kit, "main")
    assert result.ok


def test_none_changeset_satisfies_the_guard(tmp_path: Path) -> None:
    """The `none` escape hatch: a declared non-surface change still counts."""
    source_kit = _make_repo(tmp_path)
    _add_changeset(source_kit, "backbone", "none")
    _commit_change(source_kit, ".pkit/cli/README.md")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == ["backbone"]
    assert result.ok


def test_skip_flag_passes_unconditionally(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "src/project_kit/foo.py")
    result = release.check_changesets(source_kit, "main", skip=True)
    assert result.skipped
    assert result.ok


def test_component_subtree_touch_requires_component_changeset(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, ".pkit/adapters/claude-code/new-file.md")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == ["claude-code"]
    assert result.missing == ["claude-code"]


def test_untracked_surface_path_is_not_flagged(tmp_path: Path) -> None:
    """A change outside every surface prefix / subtree does not trip the guard
    (documented false-negative territory — here `docs/` is not surface)."""
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "docs/notes.md")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == []
    assert result.ok


def test_touched_components_maps_prefixes_and_subtrees(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    components = changesets.discover_components(source_kit)
    files = [
        ".pkit/cli/README.md",  # backbone surface prefix
        ".pkit/adapters/claude-code/package.yaml",  # component subtree
        "README.md",  # neither
    ]
    touched = release.touched_components(components, files)
    assert set(touched) == {"backbone", "claude-code"}


# --- A declared floor rides on a change to its component or a release of it --
# (PRJ-002 D4)


def _add_floor_changeset(
    source_kit: Path,
    component: str,
    value: str = "1.5.0",
    *,
    kind: str = "minor",
    body: str = "Needs the backbone.",
) -> None:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{component}-floor.yaml").write_text(
        f"component: {component}\nkind: {kind}\nbody: {body}\n"
        f"custom:\n  requires_backbone: {value}\n",
        encoding="utf-8",
    )


def _merge_earlier_pr(source_kit: Path, *changes: tuple[str, str, str]) -> None:
    """Land `changes` — floor changesets as (component, value, kind) — on `main`
    as an earlier pull request, then restart `feature` from it."""
    repo = source_kit.parent
    _git(repo, "checkout", "-q", "main")
    for component, value, kind in changes:
        _add_floor_changeset(source_kit, component, value, kind=kind)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "an earlier pull request")
    _git(repo, "checkout", "-q", "-B", "feature")


def test_a_floor_on_a_none_changeset_for_an_untouched_component_is_refused(
    tmp_path: Path,
) -> None:
    """A backbone change declaring a floor for an adapter it neither changes nor
    releases: the floor would change what the adapter requires under an unchanged
    version."""
    source_kit = _make_repo(tmp_path)
    _add_changeset(source_kit, "backbone", "minor")
    _add_floor_changeset(source_kit, "claude-code", kind="none")
    _commit_change(source_kit, "src/project_kit/foo.py")

    result = release.check_changesets(source_kit, "main")

    assert result.missing == []
    assert [cs.path.name for cs in result.stray_floors] == ["claude-code-floor.yaml"]
    assert not result.ok


@pytest.mark.parametrize("kind", ["patch", "minor", "major"])
def test_a_floor_only_release_of_an_untouched_component_passes(tmp_path: Path, kind: str) -> None:
    """The correction path: a need found after the component shipped is declared on
    a changeset that moves its version, in a pull request that changes nothing
    under its tree."""
    source_kit = _make_repo(tmp_path)
    _add_floor_changeset(source_kit, "claude-code", "1.4.0", kind=kind)
    _commit_change(source_kit, "docs/notes.md")

    result = release.check_changesets(source_kit, "main")

    assert result.touched == []
    assert result.stray_floors == []
    assert result.ok


def test_a_floor_riding_on_a_change_to_its_component_passes(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _add_floor_changeset(source_kit, "claude-code", "release")
    _commit_change(source_kit, ".pkit/adapters/claude-code/new-file.md")

    result = release.check_changesets(source_kit, "main")

    assert result.touched == ["claude-code"]
    assert result.stray_floors == []
    assert result.ok


def test_a_readme_touch_counts_as_a_change_to_the_component(tmp_path: Path) -> None:
    """The tie reads paths: any file under the component's tree — a README edit
    too — is a change to the component, so it passes a floor the tie would refuse
    otherwise. A reminder, not a proof; the lint still refuses a floor on a `none`
    changeset, whatever the diff."""
    source_kit = _make_repo(tmp_path)
    _add_floor_changeset(source_kit, "claude-code", kind="none")
    _commit_change(source_kit, ".pkit/adapters/claude-code/README.md", "cosmetic\n")

    result = release.check_changesets(source_kit, "main")

    assert result.touched == ["claude-code"]
    assert result.stray_floors == []


def test_a_pending_floor_an_earlier_diff_added_is_not_this_diffs(tmp_path: Path) -> None:
    """Only the changesets the diff adds or edits are tied to it."""
    source_kit = _make_repo(tmp_path)
    _merge_earlier_pr(source_kit, ("claude-code", "1.5.0", "none"))
    _add_changeset(source_kit, "backbone", "minor")
    _commit_change(source_kit, "src/project_kit/foo.py")

    result = release.check_changesets(source_kit, "main")

    assert result.stray_floors == []
    assert result.ok


def test_a_note_only_edit_of_a_pending_floor_declares_nothing(tmp_path: Path) -> None:
    """The diff edits the changeset, but the floor it carries is the one the file
    held at the merge base: nothing is declared here, so nothing is judged."""
    source_kit = _make_repo(tmp_path)
    _merge_earlier_pr(source_kit, ("claude-code", "1.5.0", "none"))
    _add_floor_changeset(source_kit, "claude-code", "'1.5.0'", kind="none", body="Reworded.")
    _git(source_kit.parent, "add", "-A")
    _git(source_kit.parent, "commit", "-q", "-m", "reword the note")

    result = release.check_changesets(source_kit, "main")

    assert result.stray_floors == []
    assert result.ok


@pytest.mark.parametrize(
    ("edit", "stray"),
    [
        (("claude-code", "1.4.0", "none"), True),  # the value changed
        (("claude-code", "1.4.0", "patch"), False),  # a correction on a release of it
    ],
)
def test_changing_a_pending_floor_value_declares_it_here(
    tmp_path: Path, edit: tuple[str, str, str], stray: bool
) -> None:
    source_kit = _make_repo(tmp_path)
    _merge_earlier_pr(source_kit, ("claude-code", "1.5.0", "none"))
    component, value, kind = edit
    _add_floor_changeset(source_kit, component, value, kind=kind)
    _git(source_kit.parent, "add", "-A")
    _git(source_kit.parent, "commit", "-q", "-m", "correct the declared floor")

    result = release.check_changesets(source_kit, "main")

    assert [cs.requires_backbone for cs in result.stray_floors] == (["1.4.0"] if stray else [])
    assert result.ok is not stray


def test_moving_a_pending_floor_to_another_component_declares_it_here(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _merge_earlier_pr(source_kit, ("backbone", "1.5.0", "none"))
    directory = changesets.unreleased_dir(source_kit.parent)
    (directory / "backbone-floor.yaml").write_text(
        "component: claude-code\nkind: none\nbody: Needs the backbone.\n"
        "custom:\n  requires_backbone: 1.5.0\n",
        encoding="utf-8",
    )
    _git(source_kit.parent, "add", "-A")
    _git(source_kit.parent, "commit", "-q", "-m", "move the floor")

    result = release.check_changesets(source_kit, "main")

    assert [cs.component for cs in result.stray_floors] == ["claude-code"]


def test_the_escape_hatch_does_not_waive_the_floor_tie(tmp_path: Path) -> None:
    """The label waives the surface check, never the tie: a hatch that passed a
    floor would let any pull request raise any component's floor."""
    source_kit = _make_repo(tmp_path)
    _add_floor_changeset(source_kit, "claude-code", kind="none")
    _commit_change(source_kit, "src/project_kit/foo.py")

    result = release.check_changesets(source_kit, "main", skip=True)

    assert result.skipped
    assert result.missing == ["backbone"]  # waived
    assert [cs.path.name for cs in result.stray_floors] == ["claude-code-floor.yaml"]
    assert not result.ok


def test_release_check_names_a_stray_floor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_kit = _make_repo(tmp_path)
    _add_floor_changeset(source_kit, "claude-code", kind="none")
    _commit_change(source_kit, "docs/notes.md")
    monkeypatch.chdir(source_kit.parent)

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 1, result.output
    assert "no surface-touched components — ok" not in result.stdout
    assert "a requires_backbone floor declared for a component this diff neither touches" in (
        result.output
    )
    assert "claude-code-floor.yaml: 'claude-code' (kind: none, requires_backbone: 1.5.0)" in (
        result.output
    )
    assert "on a changeset that moves its version (patch or above)" in result.output
    assert "surface change without a changeset" not in result.output


def test_release_check_with_the_label_still_refuses_a_stray_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_kit = _make_repo(tmp_path)
    _add_floor_changeset(source_kit, "claude-code", kind="none")
    _commit_change(source_kit, "src/project_kit/foo.py")
    monkeypatch.chdir(source_kit.parent)
    monkeypatch.setenv("PKIT_CHANGESET_SKIP", "1")

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 1, result.output
    assert "surface check skipped (escape hatch active)" in result.stdout
    assert "claude-code-floor.yaml" in result.output
    assert "does not waive this" in result.output
    assert "surface change without a changeset" not in result.output


def test_release_check_with_the_label_and_no_stray_floor_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "src/project_kit/foo.py")
    monkeypatch.chdir(source_kit.parent)
    monkeypatch.setenv("PKIT_CHANGESET_SKIP", "1")

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 0, result.output
    assert "surface check skipped (escape hatch active)" in result.stdout
    assert "every floor this diff declares rides on its component — ok" in result.stdout


# --- The release-PR exemption (#503): a release-apply footprint is exempt ---


def _apply_release_footprint(
    source_kit: Path, *, extra_files: dict[str, str] | None = None
) -> None:
    """Stage exactly `pkit release apply`'s output on the current branch.

    Bumps `.pkit/VERSION`, bumps the adapter's `package.yaml` version, prepends
    `CHANGELOG.md`, and deletes any pending changesets — the diff a release PR
    carries. `extra_files` injects unrelated edits to build a *mixed* diff.
    """
    repo = source_kit.parent

    (source_kit / "VERSION").write_text("1.6.0\n", encoding="utf-8")

    pkg = source_kit / "adapters" / "claude-code" / "package.yaml"
    pkg.write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
        '  version: 0.6.0\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )

    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.6.0 — 2026-07-07\n\n### Changed\n\n- A release.\n",
        encoding="utf-8",
    )

    for cs in changesets.unreleased_dir(repo).glob("*.yaml"):
        cs.unlink()

    for relpath, content in (extra_files or {}).items():
        target = repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore(release): v1.6.0")


def test_release_shaped_diff_is_exempt_without_a_label(tmp_path: Path) -> None:
    """A pure release-apply footprint passes the guard with no label / changeset."""
    source_kit = _make_repo(tmp_path)
    # A pending changeset that the release consumes (deleted in the footprint).
    _add_changeset(source_kit, "backbone", "minor")
    repo = source_kit.parent
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add changeset")

    _apply_release_footprint(source_kit)

    result = release.check_changesets(source_kit, "main")
    assert release.is_release_diff(source_kit, "main")
    assert result.release_exempt
    assert result.ok


def test_normal_surface_change_still_needs_a_changeset(tmp_path: Path) -> None:
    """A plain `src/` edit is not release-shaped and still fails with no changeset."""
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "src/project_kit/foo.py")
    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt
    assert result.missing == ["backbone"]
    assert not result.ok


def test_mixed_release_plus_src_edit_is_not_exempt(tmp_path: Path) -> None:
    """Release footprint PLUS an unrelated `src/` edit must NOT be exempted —
    the exemption cannot smuggle real surface through."""
    source_kit = _make_repo(tmp_path)
    _apply_release_footprint(
        source_kit, extra_files={"src/project_kit/foo.py": "real surface change\n"}
    )
    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt
    assert "backbone" in result.missing
    assert not result.ok


def test_release_shaped_manifest_with_extra_line_is_not_exempt(tmp_path: Path) -> None:
    """A `package.yaml` whose diff touches more than version-state lines is a
    real manifest edit, not release-shaped."""
    source_kit = _make_repo(tmp_path)
    repo = source_kit.parent

    (source_kit / "VERSION").write_text("1.6.0\n", encoding="utf-8")
    pkg = source_kit / "adapters" / "claude-code" / "package.yaml"
    # Adds a `description:` line alongside the version bump — not version-state.
    pkg.write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
        '  version: 0.6.0\n  description: new\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.6.0 — 2026-07-07\n\n### Changed\n\n- A release.\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore(release): v1.6.0")

    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt


def test_docs_only_diff_is_not_a_release(tmp_path: Path) -> None:
    """A non-surface, non-footprint diff is not release-shaped (and needs no
    exemption — the guard already passes it)."""
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "docs/notes.md")
    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt
    assert result.ok  # not surface at all


# --- A release is recognised by what it writes (#1161) -----------------------

_SELF_HOST_MANIFEST = (
    "schema_version: 1\n"
    "backbone_version: {version}\n"
    "components:\n"
    "  - kind: adapter\n"
    "    name: claude-code\n"
    "    manifest: .pkit/adapters/claude-code/project/manifest.yaml\n"
)


def _package(kind: str, name: str, version: str, requires: str, *, comment: str = "") -> str:
    return (
        f"schema_version: 1\ncomponent:\n  kind: {kind}\n  name: {name}\n  version: {version}\n"
        f'{comment}requires_backbone: "{requires}"\n'
    )


def _write_files(repo: Path, files: dict[str, str]) -> None:
    for relpath, content in files.items():
        target = repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _v1_149_base(source_kit: Path) -> None:
    """Land on `main` what the v1.149.0 release started from — a self-host
    manifest, two capabilities beside the adapter, a changelog, and a pending
    changeset for each component — then restart `feature` from it."""
    repo = source_kit.parent
    _git(repo, "checkout", "-q", "main")
    _write_files(
        repo,
        {
            ".pkit/manifest.yaml": _SELF_HOST_MANIFEST.format(version="1.5.0"),
            ".pkit/adapters/claude-code/package.yaml": _package(
                "adapter", "claude-code", "0.5.0", ">=0.1.0,<1.6.0"
            ),
            ".pkit/capabilities/project-management/package.yaml": _package(
                "capability",
                "project-management",
                "0.53.0",
                ">=1.4.0,<2.0.0",
                comment="# Floor 1.4.0: it runs a backbone command.\n",
            ),
            ".pkit/capabilities/software-engineering/package.yaml": _package(
                "capability", "software-engineering", "0.1.0", ">=1.0.0,<2.0.0"
            ),
            "CHANGELOG.md": "# Changelog\n\n## 1.5.0 — 2026-08-01\n\n### Added\n\n- Earlier.\n",
        },
    )
    for component in ("backbone", "claude-code", "project-management", "software-engineering"):
        _add_changeset(source_kit, component, "minor")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the pull requests the release consumes")
    _git(repo, "checkout", "-q", "-B", "feature")


def _v1_149_release(source_kit: Path, *, manifest: str | None = None) -> None:
    """Commit the v1.149.0 release commit's shape by hand: the backbone VERSION,
    three package.yaml files (the adapter's version and requires_backbone, each
    capability's version only), the self-host manifest's backbone_version,
    CHANGELOG.md prepended, the consumed changesets deleted. `manifest`
    replaces the manifest the release writes."""
    repo = source_kit.parent
    _write_files(
        repo,
        {
            ".pkit/VERSION": "1.6.0\n",
            ".pkit/adapters/claude-code/package.yaml": _package(
                "adapter", "claude-code", "0.6.0", ">=0.1.0,<1.7.0"
            ),
            ".pkit/capabilities/project-management/package.yaml": _package(
                "capability",
                "project-management",
                "0.54.0",
                ">=1.4.0,<2.0.0",
                comment="# Floor 1.4.0: it runs a backbone command.\n",
            ),
            ".pkit/capabilities/software-engineering/package.yaml": _package(
                "capability", "software-engineering", "0.2.0", ">=1.0.0,<2.0.0"
            ),
            ".pkit/manifest.yaml": manifest or _SELF_HOST_MANIFEST.format(version="1.6.0"),
            "CHANGELOG.md": "# Changelog\n\n## 1.6.0 — 2026-08-24\n\n### Added\n\n- A release.\n\n"
            "## 1.5.0 — 2026-08-01\n\n### Added\n\n- Earlier.\n",
        },
    )
    for cs in changesets.unreleased_dir(repo).glob("*.yaml"):
        cs.unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore(release): v1.6.0")


def test_a_release_shaped_like_v1_149_0_passes_on_its_content(tmp_path: Path) -> None:
    """The self-host manifest's backbone_version is a release write: the diff
    passes the surface check it trips, with no label and no branch name."""
    source_kit = _make_repo(tmp_path)
    _v1_149_base(source_kit)
    _v1_149_release(source_kit)

    result = release.check_changesets(source_kit, "main")

    assert release.is_release_diff(source_kit, "main")
    assert result.missing == [
        "backbone",
        "claude-code",
        "project-management",
        "software-engineering",
    ]
    assert result.release_exempt
    assert result.ok


def test_release_check_passes_a_release_with_no_escape_hatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_kit = _make_repo(tmp_path)
    _v1_149_base(source_kit)
    _v1_149_release(source_kit)
    monkeypatch.chdir(source_kit.parent)
    monkeypatch.delenv("PKIT_CHANGESET_SKIP", raising=False)

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 0, result.output
    assert "release PR — diff is only what `pkit release apply` writes" in result.stdout
    assert "escape hatch" not in result.stdout


def test_a_manifest_edit_beside_backbone_version_is_not_the_release(tmp_path: Path) -> None:
    """The release rewrites the manifest's backbone_version line only; a registry
    entry riding along is a real edit, so the guard runs normally."""
    source_kit = _make_repo(tmp_path)
    _v1_149_base(source_kit)
    _v1_149_release(
        source_kit,
        manifest=_SELF_HOST_MANIFEST.format(version="1.6.0")
        + "  - kind: capability\n    name: extra\n    manifest: extra/manifest.yaml\n",
    )

    result = release.check_changesets(source_kit, "main")

    assert not release.is_release_diff(source_kit, "main")
    assert not result.release_exempt
    assert not result.ok


def test_a_requires_backbone_range_the_release_never_writes_is_not_the_release(
    tmp_path: Path,
) -> None:
    """The guard admits a changed `requires_backbone` line only in the shapes the
    broaden and the floor raise rewrite; a range opened to `*` riding along is a
    real edit, so the guard runs normally."""
    source_kit = _make_repo(tmp_path)
    _v1_149_base(source_kit)
    _v1_149_release(source_kit)
    _commit_change(
        source_kit,
        ".pkit/capabilities/software-engineering/package.yaml",
        _package("capability", "software-engineering", "0.2.0", "*"),
    )

    result = release.check_changesets(source_kit, "main")

    assert not release.is_release_diff(source_kit, "main")
    assert not result.release_exempt
    assert not result.ok


def test_a_diff_that_only_consumes_changesets_is_not_a_release(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _v1_149_base(source_kit)
    for cs in changesets.unreleased_dir(source_kit.parent).glob("*.yaml"):
        cs.unlink()
    _git(source_kit.parent, "add", "-A")
    _git(source_kit.parent, "commit", "-q", "-m", "drop the changesets")

    assert not release.is_release_diff(source_kit, "main")


@pytest.mark.parametrize(
    ("pending", "floor", "heading"),
    [
        # A backbone release: the declared floor rises to the backbone it ships.
        ((("backbone", "minor", None), ("houseware", "minor", "release")), "1.6.0", "## 1.6.0"),
        # A component release: the floor rises to an already-shipped backbone.
        ((("houseware", "patch", "1.5.0"),), "1.5.0", "## 2026-09-30"),
    ],
)
def test_what_release_apply_writes_is_a_release_diff(
    tmp_path: Path,
    pending: tuple[tuple[str, str, str | None], ...],
    floor: str,
    heading: str,
) -> None:
    """The tie between the release step and the guard: the real `apply` — the
    versions, the broaden, a declared floor and the changelog line stating it
    (#1135), the self-host manifest, the consumed changesets — committed, is a
    diff the guard recognises as the release."""
    source_kit = _make_repo(tmp_path)
    repo = source_kit.parent
    _git(repo, "checkout", "-q", "main")
    _write_files(
        repo,
        {
            ".pkit/manifest.yaml": _SELF_HOST_MANIFEST.format(version="1.5.0"),
            ".pkit/capabilities/houseware/package.yaml": _package(
                "capability", "houseware", "0.3.0", ">=1.0.0,<1.5.0"
            ),
        },
    )
    for component, kind, value in pending:
        if value is None:
            _add_changeset(source_kit, component, kind)
        else:
            _add_floor_changeset(source_kit, component, value, kind=kind)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the pull requests the release consumes")
    _git(repo, "checkout", "-q", "-B", "feature")

    release.apply_release(source_kit, release.compute_release(source_kit), today=date(2026, 9, 30))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore(release)")

    houseware = (source_kit / "capabilities" / "houseware" / "package.yaml").read_text()
    assert f'requires_backbone: ">={floor},' in houseware
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert heading in changelog
    assert f"Requires backbone >={floor}." in changelog
    assert release.is_release_diff(source_kit, "main")


# --- The root the guard reads (#877): the working directory, not the checkout
# that owns the interpreter ----------------------------------------------------


def _make_checkout_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """A project-kit-shaped checkout on `main` plus a git worktree of it on a
    branch that adds a capability the checkout does not have, and touches it.

    Returns `(checkout, worktree)`. The checkout carries `.pkit/decisions/` so
    `source_checkout_root()` accepts it as the tree owning the interpreter.
    """
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    _make_repo(checkout)
    (checkout / ".pkit" / "decisions").mkdir()
    _git(checkout, "add", "-A")
    _git(checkout, "checkout", "-q", "main")

    worktree = tmp_path / "worktree"
    _git(checkout, "worktree", "add", "-q", "-b", "wt", str(worktree), "main")
    extra = worktree / ".pkit" / "capabilities" / "extra"
    extra.mkdir(parents=True)
    (extra / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: extra\n"
        '  version: 0.1.0\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (extra / "README.md").write_text("extra\n", encoding="utf-8")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "add extra capability")
    return checkout, worktree


def _point_interpreter_at(monkeypatch, checkout: Path) -> None:
    """Make `install.source_checkout_root()` derive `checkout` from `__file__` —
    the editable-install shape where the module lives inside one fixed tree."""
    from project_kit import install

    monkeypatch.setattr(install, "__file__", str(checkout / "src" / "project_kit" / "install.py"))


def test_guard_reads_the_worktree_at_cwd_not_the_interpreter_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """From a worktree, `release check` diffs and discovers components in the
    worktree — the `extra` capability exists only there — and says which tree it
    is operating on."""


    checkout, worktree = _make_checkout_with_worktree(tmp_path)
    _point_interpreter_at(monkeypatch, checkout)
    monkeypatch.chdir(worktree)

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 1, result.output
    assert "changeset guard: touched extra" in result.stdout
    assert "surface change without a changeset for: extra" in result.output
    assert "note: operating on" in result.stderr
    assert str(worktree.resolve()) in result.stderr
    assert str(checkout.resolve()) in result.stderr
    assert "note:" not in result.stdout


def test_guard_from_the_checkout_itself_is_silent_and_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Self-host / dev live-edit: cwd is the checkout, both roots coincide — no
    notice, and the worktree-only component is invisible."""


    checkout, _worktree = _make_checkout_with_worktree(tmp_path)
    _point_interpreter_at(monkeypatch, checkout)
    monkeypatch.chdir(checkout)

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 0, result.output
    assert "no surface-touched components" in result.stdout
    assert result.stderr == ""
