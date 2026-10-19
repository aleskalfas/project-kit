"""Tests for the release step: compute, write, broaden-at-release, the declared
floor raise, changelog, and consumption (PRJ-002 D3/D4). Plus a cutover check
that the legacy `version bump` path still works alongside the release path."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import cast

import click
import pytest
from click.testing import CliRunner

from project_kit import changesets, cli, release, session_guard, versioning
from project_kit.cli import main
from project_kit.manifest import read_backbone_manifest
from project_kit.migrations import parse_version_tuple
from tests import sessions
from tests.adopter_repo import GitRepo


def _make_kit(tmp_path: Path, backbone: str = "1.5.0") -> Path:
    """A source kit in a git repo (so `tag_version` has a HEAD to tag)."""
    repo = GitRepo.init(tmp_path)

    source_kit = tmp_path / ".pkit"
    source_kit.mkdir()
    (source_kit / "VERSION").write_text(f"{backbone}\n", encoding="utf-8")

    adapter = source_kit / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: adapter\n"
        "  name: claude-code\n"
        "  version: 0.5.0\n"
        'requires_backbone: ">=0.1.0,<1.6.0"\n',
        encoding="utf-8",
    )
    repo.commit("seed")
    return source_kit


def _add(source_kit: Path, component: str, kind: str, body: str, name: str) -> None:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(
        f"component: {component}\nkind: {kind}\nbody: {body}\n", encoding="utf-8"
    )


def _write_categorised(
    source_kit: Path,
    component: str,
    kind: str,
    body: str,
    category: str,
    name: str,
    *,
    pr: str | None = None,
) -> None:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    text = f"component: {component}\nkind: {kind}\nbody: {body}\ncategory: {category}\n"
    if pr is not None:
        text += f'pr: "{pr}"\n'
    (directory / name).write_text(text, encoding="utf-8")


def test_compute_takes_highest_segment_per_component(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "patch", "a small fix", "a.yaml")
    _add(source_kit, "backbone", "minor", "a new command", "b.yaml")

    plan = release.compute_release(source_kit)
    backbone = plan.backbone
    assert backbone is not None
    assert backbone.segment == "minor"
    assert backbone.new_version == "1.6.0"
    assert backbone.notes == ["a small fix", "a new command"]


def test_compute_computes_each_tier_independently(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add(source_kit, "claude-code", "patch", "adapter fix", "b.yaml")

    plan = release.compute_release(source_kit)
    by_name = {r.component.name: r for r in plan.releases}
    assert by_name["backbone"].new_version == "1.6.0"
    assert by_name["claude-code"].new_version == "0.5.1"


def test_compute_none_only_component_does_not_move(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "none", "docs only", "a.yaml")
    plan = release.compute_release(source_kit)
    assert plan.is_empty
    assert len(plan.consumed) == 1  # still consumed


def test_compute_refuses_unknown_component(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "nonexistent", "minor", "x", "a.yaml")
    with pytest.raises(click.ClickException, match="unknown component"):
        release.compute_release(source_kit)


def test_apply_writes_backbone_version_and_broadens(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "a new command", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    # Broaden-at-release (D4): the adapter's `<1.6.0` no longer covers 1.6.0,
    # so it broadens to `<1.7.0`.
    pkg = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert 'requires_backbone: ">=0.1.0,<1.7.0"' in pkg


def test_apply_writes_component_version_line(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "claude-code", "minor", "adapter feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    pkg = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert "  version: 0.6.0\n" in pkg
    # schema_version untouched.
    assert "schema_version: 1\n" in pkg
    # Backbone unmoved → no tag path; VERSION unchanged.
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_apply_generates_changelog_from_notes(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "Add `pkit release`.", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 7, 3))

    changelog = (source_kit.parent / "CHANGELOG.md").read_text()
    assert "# Changelog" in changelog
    assert "## 1.6.0 — 2026-07-03" in changelog
    # No category on the changeset → defaults to `Changed`; backbone entry plain.
    assert "### Changed" in changelog
    assert "- Add `pkit release`." in changelog


@pytest.mark.parametrize(("component", "moving"), [("backbone", "minor"), ("claude-code", "patch")])
def test_apply_writes_no_changelog_line_for_a_none_changeset(
    tmp_path: Path, component: str, moving: str
) -> None:
    """PRJ-002: a `none` changeset is recorded but adds no changelog line, even
    when another changeset moves its component (#1753)."""
    source_kit = _make_kit(tmp_path)
    _add(source_kit, component, moving, "Add a command.", "a.yaml")
    _write_categorised(
        source_kit, component, "none", "Record a design-ahead decision.", "Added", "b.yaml"
    )

    plan = release.compute_release(source_kit)
    (rel,) = plan.releases
    assert rel.notes == ["Add a command."]
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 10, 18))

    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "Add a command." in changelog
    assert "design-ahead" not in changelog
    assert "### Added" not in changelog  # the none changeset's category opens no group
    assert list(changesets.unreleased_dir(tmp_path).glob("*.yaml")) == []  # both consumed


def test_a_none_changeset_links_no_pull_request_and_is_not_counted_unlinked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `none` changeset's `pr` labels nothing: its entry is not written, so no
    reference is either, and the warning counts only the numbers that label one."""
    source_kit = _make_kit(tmp_path)  # no remote: bare numbers link nowhere
    _write_categorised(source_kit, "backbone", "patch", "A fix.", "Fixed", "a.yaml", pr="503")
    _write_categorised(source_kit, "backbone", "none", "Design ahead.", "Fixed", "b.yaml", pr="504")
    plan = release.compute_release(source_kit)

    entry = release.render_changelog_entry(
        plan, date(2026, 10, 18), repository_url="https://github.com/owner/repo"
    )
    assert "[#503]: https://github.com/owner/repo/pull/503" in entry
    assert "#504" not in entry

    release.apply_release(source_kit, plan, tag=False)
    assert "1 pull-request number(s)" in capsys.readouterr().err


def test_apply_prepends_new_entry_above_existing(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    (source_kit.parent / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.5.0 — 2026-06-01\n\n### backbone (1.4.0 → 1.5.0)\n- old\n",
        encoding="utf-8",
    )
    _add(source_kit, "backbone", "minor", "new", "a.yaml")
    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 7, 3))

    text = (source_kit.parent / "CHANGELOG.md").read_text()
    assert text.index("## 1.6.0") < text.index("## 1.5.0")
    assert text.count("# Changelog") == 1


def test_apply_deletes_consumed_changesets(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    _add(source_kit, "backbone", "none", "y", "b.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    remaining = list(changesets.unreleased_dir(source_kit.parent).glob("*.yaml"))
    assert remaining == []


def test_apply_cuts_tag_on_backbone_bump(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=True)

    result = subprocess.run(
        ["git", "tag", "-l", "v1.6.0"],
        capture_output=True,
        text=True,
        cwd=source_kit.parent,
        check=True,
    )
    assert result.stdout.strip() == "v1.6.0"


def test_apply_does_not_tag_by_default(tmp_path: Path) -> None:
    """Tag is a separate anchored step — default apply writes but cuts no tag."""
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan)  # tag defaults to False

    result = subprocess.run(
        ["git", "tag", "-l", "v1.6.0"],
        capture_output=True,
        text=True,
        cwd=source_kit.parent,
        check=True,
    )
    assert result.stdout.strip() == ""


def test_apply_empty_plan_is_noop(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    plan = release.compute_release(source_kit)
    assert plan.is_empty
    release.apply_release(source_kit, plan, tag=True)  # must not raise
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


# --- The cross-repository guard on a pushed tag (#1254) -------------------------


@pytest.fixture
def applied(monkeypatch: pytest.MonkeyPatch) -> list[str | None]:
    """`apply_release` stubbed: how each run's clearance passed, None for a
    run that pushes nothing and so carries none."""
    runs: list[str | None] = []

    def apply(
        source_kit: Path,
        plan: release.ReleasePlan,
        *,
        clearance: session_guard.Clearance | None,
        **_: object,
    ) -> None:
        runs.append(clearance.passed if clearance is not None else None)

    monkeypatch.setattr(cli, "apply_release", apply)
    return runs


def test_apply_pushing_a_tag_from_another_repository_is_refused_before_anything_is_written(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--tag --push` changes the hosting service: in another repository than
    the session's, with no terminal and no flag, the guard refuses at the
    entry — no version, changelog or changeset is touched, and nothing pushed."""
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    sessions.rooted_elsewhere(tmp_path_factory.mktemp("session"), monkeypatch)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["release", "apply", "--tag", "--push", "--yes"])
    assert result.exit_code == 1
    assert "the cross-repository guard refused" in result.stderr
    assert "Nothing was written or pushed" in result.stderr
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"
    assert list(changesets.unreleased_dir(tmp_path).glob("*.yaml"))


@pytest.mark.parametrize(
    ("args", "passed"),
    [
        (["--tag", "--push", "--allow-foreign-repo"], "flag"),
        (["--tag"], None),
    ],
    ids=["pushed-with-the-flag", "tagged-only-locally"],
)
def test_apply_from_another_repository_goes_with_the_flag_or_without_a_push(
    args: list[str],
    passed: str | None,
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    applied: list[str | None],
) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    sessions.rooted_elsewhere(tmp_path_factory.mktemp("session"), monkeypatch)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["release", "apply", *args, "--yes"])
    assert result.exit_code == 0, result.output
    assert applied == [passed]


def test_apply_pushing_a_tag_without_the_guards_clearance_writes_nothing(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    plan = release.compute_release(source_kit)
    with pytest.raises(TypeError, match="needs a clearance"):
        release.apply_release(source_kit, plan, tag=True, push=True)
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_render_changelog_keys_component_only_release_by_date(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "claude-code", "minor", "adapter feature", "a.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))
    # No backbone move → the section keys by date alone (no `<version> — date`).
    assert entry.startswith("## 2026-07-03\n")
    # The inline component tag surfaces which component moved and to what.
    assert "**claude-code 0.6.0** — adapter feature" in entry


def test_render_groups_entries_by_category(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "New thing.", "Added", "a.yaml")
    _write_categorised(source_kit, "backbone", "patch", "Broken thing.", "Fixed", "b.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    assert "### Added\n- New thing." in entry
    assert "### Fixed\n- Broken thing." in entry
    # Canonical KaC order: Added precedes Fixed.
    assert entry.index("### Added") < entry.index("### Fixed")


def test_render_tags_non_backbone_component_inline(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "Backbone thing.", "Added", "a.yaml")
    _write_categorised(source_kit, "claude-code", "minor", "Adapter thing.", "Added", "b.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    # Section keys on the backbone version; the backbone entry is plain, the
    # non-backbone one is tagged inline with its own name + new version.
    assert entry.startswith("## 1.6.0 — 2026-07-03")
    assert "- Backbone thing." in entry
    assert "- **claude-code 0.6.0** — Adapter thing." in entry


def test_render_resolves_pr_links_in_trailing_block(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "A change.", "Changed", "a.yaml", pr="465")
    _write_categorised(
        source_kit,
        "backbone",
        "patch",
        "A URL-linked fix.",
        "Fixed",
        "b.yaml",
        pr="https://example.test/pull/470",
    )
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(
        plan, date(2026, 7, 3), repository_url="https://github.com/owner/repo"
    )

    # Inline `([#N])` on the entry, definition resolved at the foot: a number
    # to the repository's pull request, a URL as written.
    assert "- A change. ([#465])" in entry
    assert "- A URL-linked fix. ([#470])" in entry
    assert "[#465]: https://github.com/owner/repo/pull/465" in entry
    assert "[#470]: https://example.test/pull/470" in entry
    # The link block sits below the entries.
    assert entry.index("### Changed") < entry.index("[#465]: ")


def test_render_labels_a_pr_number_without_a_link_when_no_repository_is_known(
    tmp_path: Path,
) -> None:
    """#514: a bare number with no repository to link into keeps its label and
    writes no reference — never the broken `[#465]: 465`."""
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "A change.", "Changed", "a.yaml", pr="465")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3), repository_url=None)

    assert "- A change. ([#465])" in entry
    assert "[#465]:" not in entry


def test_render_links_a_shared_label_to_the_url_when_the_number_has_no_repository(
    tmp_path: Path,
) -> None:
    """A number and a URL naming the same pull request share one label; with no
    repository the URL supplies the reference, and both entries link through it."""
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "A change.", "Changed", "a.yaml", pr="465")
    _write_categorised(
        source_kit,
        "backbone",
        "patch",
        "A fix.",
        "Fixed",
        "b.yaml",
        pr="https://example.test/pull/465",
    )
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    assert "- A change. ([#465])" in entry
    assert "- A fix. ([#465])" in entry
    assert entry.count("[#465]: ") == 1
    assert "[#465]: https://example.test/pull/465" in entry


def test_apply_links_a_pr_number_to_the_origin_repository(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    GitRepo(tmp_path).git("remote", "add", "origin", "git@github.com:owner/repo.git")
    _write_categorised(source_kit, "backbone", "patch", "A fix.", "Fixed", "a.yaml", pr="503")

    release.apply_release(source_kit, release.compute_release(source_kit))

    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- A fix. ([#503])" in changelog
    assert "[#503]: https://github.com/owner/repo/pull/503" in changelog


def test_apply_without_a_github_origin_labels_a_pr_number_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_kit = _make_kit(tmp_path)  # no remote at all
    _write_categorised(source_kit, "backbone", "patch", "A fix.", "Fixed", "a.yaml", pr="503")

    release.apply_release(source_kit, release.compute_release(source_kit))

    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- A fix. ([#503])" in changelog
    assert "[#503]:" not in changelog
    assert "without a link" in capsys.readouterr().err


@pytest.mark.parametrize(
    "remote",
    [
        "https://github.com/owner/repo.git",
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/",
        "https://x-access-token:secret@github.com/owner/repo.git",
        "git@github.com:owner/repo.git",
        "ssh://git@github.com/owner/repo.git",
        "ssh://git@github.com:22/owner/repo",
        "https://GitHub.com/owner/repo.git\n",
    ],
)
def test_github_repository_url_reads_owner_and_name_from_each_remote_form(remote: str) -> None:
    assert release.github_repository_url(remote) == "https://github.com/owner/repo"


@pytest.mark.parametrize(
    "remote",
    [
        "",
        "https://gitlab.com/owner/repo.git",
        "git@gitlab.com:owner/repo.git",
        "https://github.com.example.test/owner/repo",
        "https://github.com@example.test/owner/repo",
        "https://github.com/owner",
        "https://github.com/owner/repo/extra",
        "/srv/git/repo.git",
    ],
)
def test_github_repository_url_is_none_for_any_other_remote(remote: str) -> None:
    assert release.github_repository_url(remote) is None


def test_origin_repository_url_reads_the_origin_remote(tmp_path: Path) -> None:
    repo = GitRepo.init(tmp_path)
    assert release.origin_repository_url(tmp_path) is None
    repo.git("remote", "add", "origin", "https://github.com/owner/repo.git")
    assert release.origin_repository_url(tmp_path) == "https://github.com/owner/repo"


def test_render_omits_link_when_pr_absent(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "No PR here.", "Added", "a.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    assert "- No PR here." in entry
    assert "([#" not in entry  # no inline link
    assert "]: " not in entry  # no trailing reference block


def test_cutover_legacy_version_bump_still_works(tmp_path: Path) -> None:
    """The old in-branch path is untouched: `bump_version` writes + broadens,
    and the release path computes forward from whatever state it left."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")

    old, new = versioning.bump_version(source_kit, "minor")
    assert (old, new) == ("1.5.0", "1.6.0")
    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"

    # And the release path reads that new state as its current baseline.
    _add(source_kit, "backbone", "patch", "later fix", "a.yaml")
    plan = release.compute_release(source_kit)
    assert plan.backbone is not None
    assert plan.backbone.new_version == "1.6.1"


# --- #494: component-release auto-broaden to the current backbone ----------


def _write_capability(source_kit: Path, name: str, version: str, requires_backbone: str) -> Path:
    """Add a kit-shipped capability package.yaml under capabilities/<name>/."""
    cap = source_kit / "capabilities" / name
    cap.mkdir(parents=True)
    pkg = cap / "package.yaml"
    pkg.write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        f"  name: {name}\n"
        f"  version: {version}\n"
        f'requires_backbone: "{requires_backbone}"\n',
        encoding="utf-8",
    )
    return pkg


def test_component_release_broadens_to_current_backbone(tmp_path: Path) -> None:
    """A component release under backbone 1.5.0 widens the released component's
    upper bound to cover it — `<1.2.0` becomes `<1.6.0` (backbone minor + 1)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.2.0")
    _add(source_kit, "houseware", "minor", "house feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    text = pkg.read_text()
    assert "  version: 0.4.0\n" in text
    assert 'requires_backbone: ">=1.0.0,<1.6.0"' in text
    # Backbone did not move.
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_component_release_broaden_is_widen_only(tmp_path: Path) -> None:
    """A component whose range already covers (or exceeds) the current backbone
    is left untouched — the broaden never narrows a wider existing bound."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "houseware", "patch", "house fix", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    # Upper bound `<2.0.0` already covers backbone 1.5.0 → unchanged.
    assert 'requires_backbone: ">=1.0.0,<2.0.0"' in pkg.read_text()


def test_component_release_no_broaden_skips(tmp_path: Path) -> None:
    """`broaden=False` (the --no-broaden flag) leaves the range as authored."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.2.0")
    _add(source_kit, "houseware", "minor", "house feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, broaden=False)

    assert 'requires_backbone: ">=1.0.0,<1.2.0"' in pkg.read_text()


# --- PRJ-007: release keeps the self-host manifest backbone_version current ---


def _write_self_host_manifest(source_kit: Path, backbone_version: str) -> Path:
    """Write a self-host `.pkit/manifest.yaml` with a components registry."""
    path = source_kit / "manifest.yaml"
    path.write_text(
        "schema_version: 1\n"
        f"backbone_version: {backbone_version}\n"
        "components:\n"
        "  - kind: adapter\n"
        "    name: claude-code\n"
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml\n",
        encoding="utf-8",
    )
    return path


def test_apply_backbone_bump_updates_self_host_manifest(tmp_path: Path) -> None:
    """On a backbone bump, apply writes the new version into the self-host
    manifest's `backbone_version`, matching the new `.pkit/VERSION` (PRJ-007)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_self_host_manifest(source_kit, "1.0.0")
    _add(source_kit, "backbone", "minor", "a new command", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    version = (source_kit / "VERSION").read_text().strip()
    assert version == "1.6.0"
    updated = read_backbone_manifest(source_kit.parent)
    assert updated is not None
    assert updated.backbone_version == version


def test_apply_backbone_bump_preserves_other_manifest_keys(tmp_path: Path) -> None:
    """Only `backbone_version` moves — the components registry and schema
    version are preserved (PRJ-007)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_self_host_manifest(source_kit, "1.0.0")
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    updated = read_backbone_manifest(source_kit.parent)
    assert updated is not None
    assert updated.schema_version == 1
    assert [e.name for e in updated.components] == ["claude-code"]
    assert updated.components[0].kind == "adapter"


def test_apply_backbone_bump_rewrites_only_the_manifest_version_lines(
    tmp_path: Path,
) -> None:
    """The `backbone_version:` line is rewritten in place and the missing
    `completed_version:` line added right after it: a comment and an explicit
    default `origin:`, which a YAML round-trip drops, keep every byte — so the
    release's manifest diff is the lines the changeset guard admits (#1161,
    PRJ-007, ADR-065 point 3)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    original = (
        "schema_version: 1\n"
        "# The self-host install record (PRJ-007).\n"
        "backbone_version: 1.5.0\n"
        "components:\n"
        "  - kind: adapter\n"
        "    name: claude-code\n"
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml\n"
        "    origin: kit-shipped\n"
    )
    manifest = source_kit / "manifest.yaml"
    manifest.write_text(original, encoding="utf-8")
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert manifest.read_text(encoding="utf-8") == original.replace(
        "backbone_version: 1.5.0\n", "backbone_version: 1.6.0\ncompleted_version: 1.6.0\n"
    )


def test_apply_backbone_bump_rewrites_an_existing_completion_line(tmp_path: Path) -> None:
    """Both recorded states move to the release, each on its own line (PRJ-007,
    ADR-065 point 3): the source reads as complete at the version it ships."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    manifest = source_kit / "manifest.yaml"
    original = (
        "schema_version: 1\nbackbone_version: 1.5.0\ncompleted_version: 1.5.0\ncomponents: []\n"
    )
    manifest.write_text(original, encoding="utf-8")
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert manifest.read_text(encoding="utf-8") == original.replace("1.5.0", "1.6.0")
    updated = read_backbone_manifest(source_kit.parent)
    assert updated is not None and not updated.transition_incomplete


def test_apply_writes_a_completion_left_behind_when_the_backbone_line_is_current(
    tmp_path: Path,
) -> None:
    """Each line is checked on its own: a manifest whose backbone line already names
    the release still gains the completion beside it."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    manifest = source_kit / "manifest.yaml"
    manifest.write_text("schema_version: 1\nbackbone_version: 1.6.0\n", encoding="utf-8")
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert manifest.read_text(encoding="utf-8") == (
        "schema_version: 1\nbackbone_version: 1.6.0\ncompleted_version: 1.6.0\n"
    )


def test_apply_refuses_a_manifest_with_no_backbone_version_line(tmp_path: Path) -> None:
    """A self-host manifest the release cannot keep current is refused, naming it."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    (source_kit / "manifest.yaml").write_text("schema_version: 1\ncomponents: []\n")
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    with pytest.raises(click.ClickException, match="`backbone_version:` line"):
        release.apply_release(source_kit, release.compute_release(source_kit), tag=False)


def test_apply_capability_only_release_leaves_manifest_backbone(tmp_path: Path) -> None:
    """A capability-only release does not move the backbone, so the self-host
    manifest's `backbone_version` is untouched (PRJ-007)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.6.0")
    _write_self_host_manifest(source_kit, "1.0.0")
    _add(source_kit, "houseware", "minor", "house feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    # Backbone did not move → manifest backbone_version stays as authored.
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"
    updated = read_backbone_manifest(source_kit.parent)
    assert updated is not None
    assert updated.backbone_version == "1.0.0"


def test_apply_backbone_bump_no_manifest_is_noop(tmp_path: Path) -> None:
    """An apply in a repo with no self-host manifest is unaffected — the sync is
    source-repo-only mechanics and no-ops when there is nothing to maintain."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")  # _make_kit writes no manifest
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)  # must not raise

    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    assert read_backbone_manifest(source_kit.parent) is None


def test_backbone_release_still_broadens_all_components(tmp_path: Path) -> None:
    """No regression: a backbone release widens every component to the new
    backbone minor (the original PRJ-002 D4 broaden), not the component path."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.2.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    # Backbone 1.5.0 -> 1.6.0; every component broadens to <1.7.0.
    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    assert 'requires_backbone: ">=1.0.0,<1.7.0"' in pkg.read_text()
    adapter = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert 'requires_backbone: ">=0.1.0,<1.7.0"' in adapter


def _add_migration_dir(source_kit: Path, version: str) -> None:
    (source_kit / "migrations" / "backbone" / version).mkdir(parents=True, exist_ok=True)


def test_release_summary_shape_for_backbone_move(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "a new command", "a.yaml")
    plan = release.compute_release(source_kit)

    summary = release.release_summary(source_kit, plan)
    assert summary["empty"] is False
    assert summary["backbone_version"] == "1.6.0"
    assert summary["changesets_consumed"] == 1
    assert summary["migration_warnings"] == []
    releases = summary["releases"]
    assert isinstance(releases, list)
    assert releases[0]["component"] == "backbone"
    assert releases[0]["old_version"] == "1.5.0"
    assert releases[0]["new_version"] == "1.6.0"
    assert releases[0]["segment"] == "minor"
    assert releases[0]["notes"] == ["a new command"]


def test_release_summary_empty_plan(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    plan = release.compute_release(source_kit)

    summary = release.release_summary(source_kit, plan)
    assert summary["empty"] is True
    assert summary["backbone_version"] is None
    assert summary["releases"] == []


def test_migration_dir_no_warning_when_dir_matches_computed(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")  # 1.5.0 -> 1.6.0
    _add_migration_dir(source_kit, "1.6.0")
    plan = release.compute_release(source_kit)

    assert release.migration_dir_mismatches(source_kit, plan) == []


def test_migration_dir_warns_on_stale_prediction(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")  # computes 1.6.0
    _add_migration_dir(source_kit, "1.7.0")  # predicts a version the release won't cut
    plan = release.compute_release(source_kit)

    warnings = release.migration_dir_mismatches(source_kit, plan)
    assert len(warnings) == 1
    assert "backbone/1.7.0" in warnings[0]
    assert "1.6.0" in warnings[0]


def test_migration_dir_ignores_released_history(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    _add_migration_dir(source_kit, "1.5.0")  # == current VERSION, already-released history
    plan = release.compute_release(source_kit)

    assert release.migration_dir_mismatches(source_kit, plan) == []


def test_migration_dir_warns_when_release_moves_no_backbone(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "claude-code", "minor", "adapter feature", "a.yaml")  # no backbone move
    _add_migration_dir(source_kit, "1.6.0")  # future backbone dir with nothing to cut
    plan = release.compute_release(source_kit)

    warnings = release.migration_dir_mismatches(source_kit, plan)
    assert len(warnings) == 1
    assert "backbone/1.6.0" in warnings[0]


def _add_component_migration_dir(source_kit: Path, subtree: str, version: str) -> None:
    (source_kit / subtree / "migrations" / version).mkdir(parents=True, exist_ok=True)


def test_component_migration_dir_matching_its_computed_release_is_quiet(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.6.0")
    _add(source_kit, "houseware", "minor", "house feature", "a.yaml")  # 0.3.0 -> 0.4.0
    _add_component_migration_dir(source_kit, "capabilities/houseware", "0.4.0")
    _add_component_migration_dir(source_kit, "capabilities/houseware", "0.3.0")  # history
    plan = release.compute_release(source_kit)

    assert release.migration_dir_mismatches(source_kit, plan) == []


def test_component_migration_dir_warns_on_stale_prediction(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.6.0")
    _add(source_kit, "houseware", "patch", "house fix", "a.yaml")  # 0.3.0 -> 0.3.1
    _add_component_migration_dir(source_kit, "capabilities/houseware", "0.4.0")
    plan = release.compute_release(source_kit)

    assert release.migration_dir_mismatches(source_kit, plan) == [
        "migration dir capabilities/houseware/migrations/0.4.0 does not match the computed "
        "capability houseware release 0.3.1 (stale version prediction? see #465)."
    ]


def test_component_migration_dir_warns_when_release_moves_no_component_version(
    tmp_path: Path,
) -> None:
    """The adapter's dir predicts a release no changeset makes, while the backbone moves."""
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")  # 1.5.0 -> 1.6.0
    _add_component_migration_dir(source_kit, "adapters/claude-code", "0.6.0")
    plan = release.compute_release(source_kit)

    assert release.migration_dir_mismatches(source_kit, plan) == [
        "migration dir adapters/claude-code/migrations/0.6.0 predicts an adapter claude-code "
        "release, but the computed release moves no adapter claude-code version (stale "
        "prediction? see #465)."
    ]


def test_migration_dir_warnings_list_the_backbone_first(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.6.0")
    _add_component_migration_dir(source_kit, "capabilities/houseware", "0.4.0")
    _add_migration_dir(source_kit, "1.6.0")
    _add(source_kit, "claude-code", "patch", "adapter fix", "a.yaml")
    plan = release.compute_release(source_kit)

    warnings = release.migration_dir_mismatches(source_kit, plan)
    assert [w.split()[2] for w in warnings] == [
        "backbone/1.6.0",
        "capabilities/houseware/migrations/0.4.0",
    ]
    summary = release.release_summary(source_kit, plan)
    assert summary["migration_warnings"] == warnings


# --- The declared floor raise (PRJ-002 D4) ----------------------------------


def _add_floor(
    source_kit: Path, component: str, kind: str, name: str, *, value: str = "release"
) -> None:
    """A changeset declaring its component needs the backbone the release ships."""
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(
        f"component: {component}\nkind: {kind}\nbody: Needs the new backbone.\n"
        f"custom:\n  requires_backbone: {value}\n",
        encoding="utf-8",
    )


def _record_releases(source_kit: Path, *versions: str) -> None:
    """A `CHANGELOG.md` recording `versions` as backbone releases — the release
    headings an explicit floor must name one of (`recorded_backbone_releases`)."""
    ordered = sorted(versions, key=parse_version_tuple, reverse=True)
    sections = "".join(f"## {v} — 2026-01-01\n\n### Added\n- A release.\n\n" for v in ordered)
    (source_kit.parent / "CHANGELOG.md").write_text(f"# Changelog\n\n{sections}", encoding="utf-8")


def test_backbone_release_raises_a_declared_floor_to_the_new_backbone(tmp_path: Path) -> None:
    """The declared component's floor rises to the backbone the release ships; a
    component that declared nothing keeps its floor — the raise is never automatic."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    declared = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    silent = _write_capability(source_kit, "otherware", "0.1.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml")

    plan = release.compute_release(source_kit)
    assert plan.shipped_backbone == "1.6.0"
    assert [r.component.name for r in plan.floor_raises] == ["houseware"]
    release.apply_release(source_kit, plan, tag=False)

    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    assert 'requires_backbone: ">=1.6.0,<2.0.0"' in declared.read_text()
    assert "  version: 0.4.0\n" in declared.read_text()
    assert 'requires_backbone: ">=1.0.0,<2.0.0"' in silent.read_text()
    adapter = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert 'requires_backbone: ">=0.1.0,<1.7.0"' in adapter  # broadened, floor untouched


def test_component_release_raises_a_declared_floor_to_the_current_backbone(
    tmp_path: Path,
) -> None:
    """With no backbone move, the backbone the release ships is the current one."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "patch", "a.yaml")

    plan = release.compute_release(source_kit)
    assert plan.shipped_backbone == "1.5.0"
    release.apply_release(source_kit, plan, tag=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_declared_floor_raise_is_raise_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.5.0,<2.0.0")
    _add_floor(source_kit, "houseware", "patch", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()
    assert "already admits no backbone older than 1.5.0" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("component", "kind", "value", "problem"),
    [
        ("backbone", "minor", "release", "the backbone has no `requires_backbone`"),
        ("houseware", "none", "release", "a `none` changeset moves no version"),
        ("houseware", "minor", "latest", "takes `release` (the backbone this release ships)"),
        ("houseware", "minor", "1.4.0rc1", "no pre-release suffix or leading zero; got '1.4.0rc1'"),
        (
            "houseware",
            "minor",
            "1.6.0",
            "names backbone 1.6.0, above the backbone this tree carries",
        ),
        (
            "houseware",
            "minor",
            "1.4.7",
            "names backbone 1.4.7, which this tree records no release of",
        ),
        ("wildware", "minor", "release", "has a floor the release can raise"),
    ],
)
def test_compute_refuses_a_floor_field_it_cannot_carry(
    tmp_path: Path, component: str, kind: str, value: str, problem: str
) -> None:
    """A declared floor is never dropped silently: the release refuses to plan."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _write_capability(source_kit, "wildware", "0.3.0", "*")
    _add_floor(source_kit, component, kind, "a.yaml", value=value)

    with pytest.raises(click.ClickException, match="cannot raise a requires_backbone floor") as err:
        release.compute_release(source_kit)
    assert problem in err.value.message


def test_no_broaden_still_raises_a_declared_floor(tmp_path: Path) -> None:
    """`--no-broaden` keeps an upper bound as authored; a declared need still stands."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False, broaden=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()


def test_no_broaden_refuses_a_floor_the_upper_bound_cannot_hold(tmp_path: Path) -> None:
    """Raised under an upper bound that excludes the shipped backbone, the range would
    admit nothing — refused before anything is written."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.5.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")
    before = pkg.read_text()

    plan = release.compute_release(source_kit)
    with pytest.raises(click.ClickException, match="would admit no backbone"):
        release.apply_release(source_kit, plan, tag=False, broaden=False)

    assert pkg.read_text() == before
    assert list(changesets.unreleased_dir(source_kit.parent).glob("*.yaml"))


def test_no_broaden_does_not_refuse_a_floor_it_leaves_alone(tmp_path: Path) -> None:
    """A floor already above the shipped backbone is not raised, so its range is
    not the release's to refuse."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.7.0,<2.0.0")
    _add_floor(source_kit, "houseware", "patch", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False, broaden=False)

    assert 'requires_backbone: ">=1.7.0,<2.0.0"' in pkg.read_text()
    assert "  version: 0.3.1\n" in pkg.read_text()


def test_a_pre_release_backbone_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    """A component release under a pre-release `.pkit/VERSION` ships that
    pre-release, which no floor is raised to: the release refuses to plan, so
    `apply` never writes the component's version first and double-bumps on retry."""
    source_kit = _make_kit(tmp_path, backbone="1.6.0rc1")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")
    before = pkg.read_text()

    with pytest.raises(click.ClickException, match="not a release version") as err:
        release.compute_release(source_kit)
    assert "ships backbone '1.6.0rc1'" in err.value.message
    assert pkg.read_text() == before


def test_a_backbone_move_lifts_the_pre_release_refusal(tmp_path: Path) -> None:
    """Moving the backbone ships a release version, whatever `.pkit/VERSION` held."""
    source_kit = _make_kit(tmp_path, backbone="1.6.0rc1")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "patch", "backbone fix", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml")

    plan = release.compute_release(source_kit)
    assert plan.shipped_backbone == "1.6.1"
    release.apply_release(source_kit, plan, tag=False)
    assert 'requires_backbone: ">=1.6.1,<2.0.0"' in pkg.read_text()


def test_a_comment_naming_the_key_is_neither_broadened_nor_raised(tmp_path: Path) -> None:
    """A comment quoting an older range sits above the key. The broaden and the
    floor raise both rewrite the key, so the raised range still admits the
    backbone — were the comment broadened instead, the key would be left
    `">=1.5.0,<1.5.0"`, admitting nothing."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.5.0")
    comment = '# was requires_backbone: ">=1.0.0,<1.4.0"\n'
    pkg.write_text(pkg.read_text().replace("requires_backbone:", comment + "requires_backbone:"))
    _add_floor(source_kit, "houseware", "minor", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    text = pkg.read_text()
    assert comment in text
    assert 'requires_backbone: ">=1.5.0,<1.6.0"' in text


def test_the_empty_range_check_runs_with_the_broaden_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check is not a `--no-broaden` special case: every raise is checked
    against the range computed in memory. With a broaden that (hypothetically)
    widens nothing, the raised range would be empty, and nothing is written."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.5.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")
    before = pkg.read_text()

    def widens_nothing(package_text: str, backbone: str) -> tuple[str, str] | None:
        return None

    monkeypatch.setattr(versioning, "broaden_requires_backbone", widens_nothing)

    plan = release.compute_release(source_kit)
    with pytest.raises(click.ClickException, match="would admit no backbone"):
        release.apply_release(source_kit, plan, tag=False)

    assert pkg.read_text() == before
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_plan_says_when_the_backbone_does_not_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A floor declared in a component-only release resolves to the current
    backbone, which may predate the change the component needs: `plan` says so."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["release", "plan"])

    assert result.exit_code == 0, result.output
    out = result.stdout
    assert "  houseware: 0.3.0 -> 0.4.0 (minor)\n" in out
    assert "    requires_backbone floor raised to >=1.5.0\n" in out
    assert (
        "    backbone does not move this release; floor raised to current 1.5.0 "
        "— confirm the needed surface shipped in 1.5.0\n"
    ) in out


def test_plan_says_raised_only_when_the_range_changes(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.7.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add_floor(source_kit, "houseware", "patch", "b.yaml")

    (rel,) = release.compute_release(source_kit).floor_raises
    assert rel.floor_raise is not None
    assert not rel.floor_raise.raises
    assert rel.floor_raise.lines == [
        "requires_backbone floor stays >=1.7.0 (already at or above 1.6.0)"
    ]


def test_release_summary_carries_the_floor_raise(tmp_path: Path) -> None:
    """The release-PR workflow builds the PR body from `plan --json`."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml")

    summary = release.release_summary(source_kit, release.compute_release(source_kit))

    releases = cast("list[dict[str, object]]", summary["releases"])
    floors = {str(r["component"]): r["requires_backbone_floor"] for r in releases}
    assert floors["backbone"] is None
    assert floors["houseware"] == {
        "from": "1.0.0",
        "to": "1.6.0",
        "raised": True,
        "declared": "1.6.0",
        "names_release": True,
        "backbone": "1.6.0",
        "backbone_moves": True,
        "lines": ["requires_backbone floor raised to >=1.6.0"],
        "changelog": "Requires backbone >=1.6.0.",
    }


# --- An explicit, already-shipped floor (PRJ-002 D4) --------------------------


def test_an_explicit_floor_names_an_already_shipped_backbone(tmp_path: Path) -> None:
    """A need an older backbone meets raises the floor to that backbone, not to the
    one the release ships."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.3.0", "1.4.0", "1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml", value="1.3.0")

    plan = release.compute_release(source_kit)
    (rel,) = plan.floor_raises
    assert rel.floor_raise is not None
    assert rel.floor_raise.lines == ["requires_backbone floor raised to >=1.3.0"]
    release.apply_release(source_kit, plan, tag=False)

    assert 'requires_backbone: ">=1.3.0,<2.0.0"' in pkg.read_text()
    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"


def test_an_explicit_floor_at_the_current_backbone_needs_no_notice(tmp_path: Path) -> None:
    """The current backbone has shipped, so naming it is accepted; with the version
    named, a release that does not move the backbone raises no doubt about which
    one the component needs."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "patch", "a.yaml", value="1.5.0")

    plan = release.compute_release(source_kit)
    (rel,) = plan.floor_raises
    assert rel.floor_raise is not None
    assert rel.floor_raise.lines == ["requires_backbone floor raised to >=1.5.0"]
    release.apply_release(source_kit, plan, tag=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()


@pytest.mark.parametrize(
    ("first", "second", "floor"),
    [
        ("1.3.0", "1.4.0", "1.4.0"),
        ("1.4.0", "1.3.0", "1.4.0"),
        ("1.3.0", "release", "1.6.0"),
    ],
)
def test_the_highest_declared_floor_is_raised_to(
    tmp_path: Path, first: str, second: str, floor: str
) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.3.0", "1.4.0", "1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml", value=first)
    _add_floor(source_kit, "houseware", "patch", "c.yaml", value=second)

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert f'requires_backbone: ">={floor},<2.0.0"' in pkg.read_text()


def test_an_explicit_floor_stands_under_a_pre_release_backbone(tmp_path: Path) -> None:
    """A named, shipped backbone is a release version whatever `.pkit/VERSION`
    holds, so the pre-release refusal of `release` does not reach it."""
    source_kit = _make_kit(tmp_path, backbone="1.6.0rc1")
    _record_releases(source_kit, "1.3.0", "1.4.0", "1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml", value="1.5.0")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()


def test_the_release_a_pre_release_precedes_has_not_shipped(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.6.0rc1")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml", value="1.6.0")

    with pytest.raises(
        click.ClickException, match=r"above the backbone this tree carries \(1\.6\.0rc1"
    ):
        release.compute_release(source_kit)


def test_no_broaden_checks_an_explicit_floor_against_its_own_range(tmp_path: Path) -> None:
    """The raised range must admit the floor it names — not the shipped backbone,
    which an authored upper bound kept by `--no-broaden` may exclude on purpose."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.3.0", "1.4.0", "1.5.0")
    kept = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.4.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml", value="1.3.0")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False, broaden=False)
    assert 'requires_backbone: ">=1.3.0,<1.4.0"' in kept.read_text()

    empty = _write_capability(source_kit, "otherware", "0.1.0", ">=1.0.0,<1.3.0")
    _add_floor(source_kit, "otherware", "minor", "b.yaml", value="1.3.0")
    before = empty.read_text()
    plan = release.compute_release(source_kit)
    with pytest.raises(click.ClickException, match=r"does not admit 1\.3\.0"):
        release.apply_release(source_kit, plan, tag=False, broaden=False)
    assert empty.read_text() == before


def test_plan_json_names_an_explicit_floor_below_the_shipped_backbone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The release ships 1.6.0 and the changeset names 1.4.0: `plan --json` carries
    both, and says the floor was set by an explicit version, not `release`."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.4.0", "1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "Backbone change.", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml", value="1.4.0")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["release", "plan", "--json"])

    assert result.exit_code == 0, result.output
    summary = json.loads(result.stdout)
    (floor,) = [
        r["requires_backbone_floor"] for r in summary["releases"] if r["component"] == "houseware"
    ]
    assert floor == {
        "from": "1.0.0",
        "to": "1.4.0",
        "raised": True,
        "declared": "1.4.0",
        "names_release": False,
        "backbone": "1.6.0",
        "backbone_moves": True,
        "lines": ["requires_backbone floor raised to >=1.4.0"],
        "changelog": "Requires backbone >=1.4.0.",
    }


@pytest.mark.parametrize(
    ("explicit_name", "release_name"), [("a.yaml", "b.yaml"), ("b.yaml", "a.yaml")]
)
def test_an_explicit_floor_sets_the_floor_a_release_declaration_ties(
    tmp_path: Path, explicit_name: str, release_name: str
) -> None:
    """With the backbone not moving, `release` resolves to the current 1.5.0, which
    an explicit declaration also names. The explicit one sets the floor and carries
    the changelog sentence whatever the file order; the notice still follows the
    `release` declaration, whose need may postdate 1.5.0."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / explicit_name).write_text(
        "component: houseware\nkind: patch\nbody: Uses a shipped command.\n"
        "requires_backbone: '1.5.0'\n",
        encoding="utf-8",
    )
    (directory / release_name).write_text(
        "component: houseware\nkind: minor\nbody: Uses a new command.\n"
        "requires_backbone: release\n",
        encoding="utf-8",
    )

    plan = release.compute_release(source_kit)
    (rel,) = plan.floor_raises
    floor = rel.floor_raise
    assert floor is not None
    assert floor.setter.path.name == explicit_name
    assert not floor.names_release
    assert rel.floor_entry is floor.setter
    assert floor.lines[1].startswith("backbone does not move this release")

    entry = release.render_changelog_entry(plan, date(2026, 9, 30))
    assert "— Uses a shipped command. Requires backbone >=1.5.0.\n" in entry
    assert "— Uses a new command.\n" in entry


def test_a_written_range_that_excludes_the_shipped_backbone_is_warned_of(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--no-broaden` keeps an authored upper bound that admits the declared floor
    but not the backbone the release ships: the range is written as authored, and
    the plan `apply` shows before confirming warns of it — never refuses."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.3.0", "1.5.0")
    kept = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.4.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml", value="1.3.0")
    plan = release.compute_release(source_kit)

    assert release.check_raised_ranges(plan, broaden=True) == []
    assert release.check_raised_ranges(plan, broaden=False) == [
        "houseware: the range the release writes, '>=1.3.0,<1.4.0', admits the declared "
        "floor 1.3.0 but not the backbone this release ships, 1.5.0; the upper bound "
        "stays as authored (--no-broaden)."
    ]

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["release", "apply", "--no-broaden", "--yes"])

    assert result.exit_code == 0, result.output
    assert "warning: houseware: the range the release writes" in result.stderr
    assert 'requires_backbone: ">=1.3.0,<1.4.0"' in kept.read_text()


# --- The raised floor in the changelog ----------------------------------------


def test_the_changelog_entry_states_the_raised_floor(tmp_path: Path) -> None:
    """The entry of the changeset that set the floor ends with it, before the link;
    the component's other entries and the backbone's do not repeat it."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "Backbone change.", "a.yaml")
    _add(source_kit, "houseware", "patch", "A house fix.", "b.yaml")
    directory = changesets.unreleased_dir(source_kit.parent)
    (directory / "c.yaml").write_text(
        "component: houseware\nkind: minor\nbody: Uses the new command.\n"
        "custom:\n  category: Added\n  pr: '12'\n  requires_backbone: release\n",
        encoding="utf-8",
    )

    entry = release.render_changelog_entry(release.compute_release(source_kit), date(2026, 9, 30))

    assert (
        "- **houseware 0.4.0** — Uses the new command. Requires backbone >=1.6.0. ([#12])\n"
    ) in entry
    assert "- **houseware 0.4.0** — A house fix.\n" in entry
    assert "- Backbone change.\n" in entry
    assert entry.count("Requires backbone") == 1


def test_the_changelog_names_the_floor_the_setting_changeset_declared(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.3.0", "1.4.0", "1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml", value="1.3.0")
    _add_floor(source_kit, "houseware", "patch", "b.yaml", value="1.4.0")
    directory = changesets.unreleased_dir(source_kit.parent)
    (directory / "b.yaml").write_text(
        (directory / "b.yaml").read_text().replace("Needs the new backbone.", "Needs more."),
        encoding="utf-8",
    )

    entry = release.render_changelog_entry(release.compute_release(source_kit), date(2026, 9, 30))

    assert "- **houseware 0.4.0** — Needs the new backbone.\n" in entry
    assert "- **houseware 0.4.0** — Needs more. Requires backbone >=1.4.0.\n" in entry


@pytest.mark.parametrize(
    ("note", "entry"),
    [
        ("Uses the new command.", "Uses the new command. Requires backbone >=1.6.0."),
        ("Uses the new command", "Uses the new command. Requires backbone >=1.6.0."),
        ("Is it needed?", "Is it needed? Requires backbone >=1.6.0."),
        (
            "Uses two commands:\n- one\n- two",
            "Uses two commands:\n- one\n- two\n\nRequires backbone >=1.6.0.",
        ),
        ("Uses:\n1. one", "Uses:\n1. one\n\nRequires backbone >=1.6.0."),
    ],
)
def test_the_floor_sentence_is_punctuated_as_prose(tmp_path: Path, note: str, entry: str) -> None:
    """A period closes a note that lacks one before the sentence; after a note
    ending in a list, the sentence stands on its own line, not in the last item."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "Backbone change.", "a.yaml")
    directory = changesets.unreleased_dir(source_kit.parent)
    body = "\n".join(f"  {line}" for line in note.splitlines())
    (directory / "b.yaml").write_text(
        f"component: houseware\nkind: minor\nbody: |\n{body}\nrequires_backbone: release\n",
        encoding="utf-8",
    )

    rendered = release.render_changelog_entry(
        release.compute_release(source_kit), date(2026, 9, 30)
    )

    assert f"- **houseware 0.4.0** — {entry}\n" in rendered


def test_the_changelog_says_nothing_of_a_floor_that_stays(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.3.0", "1.4.0", "1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.4.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml", value="1.3.0")

    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 9, 30))

    assert "Requires backbone" not in entry
    summary = release.release_summary(source_kit, plan)
    (rel,) = cast("list[dict[str, dict[str, object]]]", summary["releases"])
    assert rel["requires_backbone_floor"]["changelog"] is None
    assert rel["requires_backbone_floor"]["lines"] == [
        "requires_backbone floor stays >=1.4.0 (already at or above 1.3.0)"
    ]


def test_apply_writes_the_raised_floor_into_the_changelog(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_releases(source_kit, "1.3.0", "1.4.0", "1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml", value="1.4.0")

    release.apply_release(
        source_kit, release.compute_release(source_kit), tag=False, today=date(2026, 9, 30)
    )

    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- **houseware 0.4.0** — Needs the new backbone. Requires backbone >=1.4.0.\n" in (
        changelog
    )


# --- The declared floor on another capability (PRJ-002 D4; COR-030) ----------


def _write_dependent(
    source_kit: Path, name: str, version: str, requires: str, *, extra: str = ""
) -> Path:
    """A capability that lists project-management in `requires_capabilities`."""
    pkg = _write_capability(source_kit, name, version, ">=1.0.0,<2.0.0")
    pkg.write_text(
        pkg.read_text(encoding="utf-8")
        + "# The panel folds through project-management's gate.\n"
        + "requires_capabilities:\n"
        + "  - name: project-management\n"
        + f'    version: "{requires}"  # the type axis\n'
        + extra,
        encoding="utf-8",
    )
    return pkg


def _add_capability_floor(
    source_kit: Path,
    component: str,
    kind: str,
    name: str,
    floors: dict[str, str],
    *,
    body: str = "Uses the new gate.",
) -> None:
    """A changeset declaring its component needs a version of each capability."""
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    lines = "".join(f"    {cap}: {value}\n" for cap, value in floors.items())
    (directory / name).write_text(
        f"component: {component}\nkind: {kind}\nbody: {body}\n"
        f"custom:\n  requires_capabilities:\n{lines}",
        encoding="utf-8",
    )


def _record_component_releases(source_kit: Path, component: str, *versions: str) -> None:
    """A `CHANGELOG.md` recording `versions` of `component` as its releases."""
    entries = "".join(f"- **{component} {v}** — A release.\n" for v in versions)
    (source_kit.parent / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## 2026-01-01\n\n### Added\n\n{entries}\n", encoding="utf-8"
    )


def test_a_release_floor_rises_to_the_version_the_release_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`release` names the project-management this release writes; the floor
    rises to it in place, its upper bound and comment kept, and the changelog
    entry of the declaring changeset says so."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "living-docs", "0.1.0", ">=0.54.0,<1.0.0")
    silent = _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _add(source_kit, "project-management", "minor", "A new floor.", "a.yaml")
    _add_capability_floor(
        source_kit, "living-docs", "minor", "b.yaml", {"project-management": "release"}
    )

    plan = release.compute_release(source_kit)
    rel = next(r for r in plan.releases if r.component.name == "living-docs")
    (floor,) = rel.capability_floors
    assert (floor.old_floor, floor.new_floor, floor.version, floor.moves) == (
        "0.54.0",
        "0.55.0",
        "0.55.0",
        True,
    )
    assert floor.names_release
    assert floor.lines == ["requires_capabilities project-management floor raised to >=0.55.0"]
    assert rel.capability_bounds == ()  # the bound admits 0.55.0: nothing to say of it
    assert release.dependency_range_problems(plan) == []

    release.apply_release(source_kit, plan, tag=False, today=date(2026, 9, 30))

    assert '    version: ">=0.55.0,<1.0.0"  # the type axis\n' in dependent.read_text()
    assert "  version: 0.2.0\n" in dependent.read_text()
    assert '    version: ">=0.54.0,<1.0.0"  # the type axis\n' in silent.read_text()
    assert "raised floor capabilities/living-docs/package.yaml on project-management" in (
        capsys.readouterr().out
    )
    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert (
        "- **living-docs 0.2.0** — Uses the new gate. Requires project-management >=0.55.0.\n"
    ) in changelog


def test_an_explicit_capability_floor_names_a_release_the_tree_records(tmp_path: Path) -> None:
    """A need an older release meets names that release; the capability need not
    move, and the floor rises to the version named, not to the current one."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_component_releases(source_kit, "project-management", "0.52.0", "0.53.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "living-docs", "0.1.0", ">=0.50.0,<1.0.0")
    _add_capability_floor(
        source_kit, "living-docs", "patch", "a.yaml", {"project-management": '"0.53.0"'}
    )

    plan = release.compute_release(source_kit)
    (floor,) = plan.releases[0].capability_floors
    assert (floor.new_floor, floor.version, floor.moves, floor.names_release) == (
        "0.53.0",
        "0.54.0",
        False,
        False,
    )
    release.apply_release(source_kit, plan, tag=False)

    assert 'version: ">=0.53.0,<1.0.0"' in dependent.read_text()


def test_a_capability_floor_at_or_above_the_declared_version_stays(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    _write_dependent(source_kit, "living-docs", "0.1.0", ">=0.54.0,<1.0.0")
    _add_capability_floor(
        source_kit, "living-docs", "patch", "a.yaml", {"project-management": '"0.54.0"'}
    )

    plan = release.compute_release(source_kit)
    (floor,) = plan.releases[0].capability_floors
    assert not floor.raises
    assert floor.lines == [
        "requires_capabilities project-management floor stays >=0.54.0 (already at or above 0.54.0)"
    ]
    entry = release.render_changelog_entry(plan, date(2026, 9, 30))
    assert "Requires project-management" not in entry
    (summary,) = cast(
        "list[dict[str, list[dict[str, object]]]]",
        release.release_summary(source_kit, plan)["releases"],
    )
    assert summary["requires_capabilities_floors"] == [
        {
            "capability": "project-management",
            "from": "0.54.0",
            "to": "0.54.0",
            "raised": False,
            "declared": "0.54.0",
            "names_release": False,
            "version": "0.54.0",
            "moves": False,
            "lines": [
                "requires_capabilities project-management floor stays >=0.54.0 "
                "(already at or above 0.54.0)"
            ],
            "changelog": None,
        }
    ]


@pytest.mark.parametrize(
    ("component", "kind", "floors", "problem"),
    [
        (
            "backbone",
            "minor",
            {"project-management": "release"},
            "the backbone has no `requires_capabilities`",
        ),
        (
            "living-docs",
            "none",
            {"project-management": '"0.54.0"'},
            "a `none` changeset moves no version",
        ),
        (
            "living-docs",
            "minor",
            {"project-management": "release"},
            "but no pending changeset moves project-management",
        ),
        (
            "living-docs",
            "minor",
            {"project-management": '"0.55.0"'},
            "names project-management 0.55.0, above the version this tree carries for it (0.54.0",
        ),
        (
            "living-docs",
            "minor",
            {"project-management": '"0.51.0"'},
            "names project-management 0.51.0, which this tree records no release of",
        ),
        ("living-docs", "minor", {"project-management": "latest"}, "takes `release`"),
        ("living-docs", "minor", {"project-management": "0.54"}, "write it in full and quoted"),
        (
            "living-docs",
            "minor",
            {"backbone": "release"},
            "names 'backbone', which is the backbone",
        ),
        (
            "living-docs",
            "minor",
            {"wildware": "release"},
            "which is no component this tree carries",
        ),
        ("living-docs", "minor", {"evidence": '"0.5.0"'}, "which 'living-docs' does not list"),
        ("houseware", "minor", {"project-management": '"0.54.0"'}, "lists 2 times"),
        ("oddware", "minor", {"project-management": '"0.54.0"'}, "the release cannot raise"),
    ],
)
def test_compute_refuses_a_capability_floor_it_cannot_carry(
    tmp_path: Path, component: str, kind: str, floors: dict[str, str], problem: str
) -> None:
    """A declared capability floor is never dropped silently: the release refuses."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_component_releases(source_kit, "project-management", "0.52.0", "0.53.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    _write_capability(source_kit, "evidence", "0.5.0", ">=1.0.0,<2.0.0")
    _write_dependent(source_kit, "living-docs", "0.1.0", ">=0.50.0,<1.0.0")
    _write_dependent(
        source_kit,
        "houseware",
        "0.1.0",
        ">=0.50.0,<1.0.0",
        extra='  - name: project-management\n    version: ">=0.40.0"\n',
    )
    odd = _write_capability(source_kit, "oddware", "0.1.0", ">=1.0.0,<2.0.0")
    odd.write_text(
        odd.read_text()
        + 'requires_capabilities: [{name: project-management, version: ">=0.5.0"}]\n',
        encoding="utf-8",
    )
    _add_capability_floor(source_kit, component, kind, "a.yaml", floors)

    with pytest.raises(
        click.ClickException, match="cannot raise a requires_capabilities floor"
    ) as err:
        release.compute_release(source_kit)
    assert problem in err.value.message


def test_a_release_floor_raised_past_the_upper_bound_widens_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A need on the project-management this release writes is a claim to run on
    it (PRJ-002 D4): a `release` floor raised to a major the bound excludes widens
    the bound up to the next major, and the changelog says both."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _add(source_kit, "project-management", "major", "A breaking change.", "a.yaml")
    _add_capability_floor(
        source_kit, "software-engineering", "minor", "b.yaml", {"project-management": "release"}
    )

    plan = release.compute_release(source_kit)
    rel = next(r for r in plan.releases if r.component.name == "software-engineering")
    (bound,) = rel.capability_bounds
    assert (bound.old_bound, bound.new_bound, bound.version, bound.setter.path.name) == (
        "1.0.0",
        "2.0.0",
        "1.0.0",
        "b.yaml",
    )
    assert bound.lines == [
        "requires_capabilities project-management upper bound widened to <2.0.0 (runs on 1.0.0)"
    ]
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 9, 30))

    assert '    version: ">=1.0.0,<2.0.0"  # the type axis\n' in dependent.read_text()
    assert (
        "widened upper bound capabilities/software-engineering/package.yaml on "
        "project-management: <1.0.0 -> <2.0.0"
    ) in capsys.readouterr().out
    assert (
        "- **software-engineering 0.3.0** — Uses the new gate. Requires project-management "
        ">=1.0.0. Runs on project-management <2.0.0.\n"
    ) in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")


def _add_runs_on(
    source_kit: Path, component: str, kind: str, name: str, runs_on: dict[str, str]
) -> None:
    """A changeset declaring its component runs on each capability's `value`."""
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    lines = "".join(f"  {cap}: {value}\n" for cap, value in runs_on.items())
    (directory / name).write_text(
        f"component: {component}\nkind: {kind}\nbody: Runs on the new major.\n"
        f"runs_on_capabilities:\n{lines}",
        encoding="utf-8",
    )


@pytest.mark.parametrize("broaden", [True, False])
def test_a_declared_runs_on_widens_the_upper_bound_and_keeps_the_floor(
    tmp_path: Path, broaden: bool
) -> None:
    """`runs_on_capabilities` widens the bound to admit the version this release
    writes, up to the next major; the floor stays as written, and `--no-broaden`
    does not skip it — it was declared."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _add(source_kit, "project-management", "major", "A breaking change.", "a.yaml")
    _add_runs_on(
        source_kit, "software-engineering", "patch", "b.yaml", {"project-management": "release"}
    )

    plan = release.compute_release(source_kit)
    rel = next(r for r in plan.releases if r.component.name == "software-engineering")
    assert rel.capability_floors == ()
    (summary,) = [
        r
        for r in cast(
            "list[dict[str, object]]", release.release_summary(source_kit, plan)["releases"]
        )
        if r["component"] == "software-engineering"
    ]
    assert summary["requires_capabilities_bounds"] == [
        {
            "capability": "project-management",
            "from": "1.0.0",
            "to": "2.0.0",
            "widened": True,
            "version": "1.0.0",
            "lines": [
                "requires_capabilities project-management upper bound widened to <2.0.0 "
                "(runs on 1.0.0)"
            ],
            "changelog": "Runs on project-management <2.0.0.",
        }
    ]
    release.apply_release(source_kit, plan, tag=False, broaden=broaden, today=date(2026, 9, 30))

    assert '    version: ">=0.54.0,<2.0.0"  # the type axis\n' in dependent.read_text()
    assert (
        "- **software-engineering 0.2.1** — Runs on the new major. Runs on project-management "
        "<2.0.0.\n"
    ) in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")


def test_a_declared_runs_on_a_bound_that_admits_the_version_leaves_it(tmp_path: Path) -> None:
    """Widen-only: a bound that admits the version this release writes stays, the
    plan says so, and the changelog says nothing of it."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _add(source_kit, "project-management", "minor", "A new floor.", "a.yaml")
    _add_runs_on(
        source_kit, "software-engineering", "patch", "b.yaml", {"project-management": "release"}
    )
    before = dependent.read_text()

    plan = release.compute_release(source_kit)
    rel = next(r for r in plan.releases if r.component.name == "software-engineering")
    (bound,) = rel.capability_bounds
    assert not bound.widens
    assert bound.lines == [
        "requires_capabilities project-management upper bound stays <1.0.0 (already admits 0.55.0)"
    ]
    assert bound.changelog_sentence is None
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 9, 30))

    assert dependent.read_text() == before.replace("version: 0.2.0", "version: 0.2.1")


def test_an_explicit_floor_and_a_declared_runs_on_ride_one_changeset(tmp_path: Path) -> None:
    """The floor names a release that has shipped, and the bound widens to the
    major this release writes: one changeset carries both claims."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_component_releases(source_kit, "project-management", "0.53.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.50.0,<1.0.0")
    _add(source_kit, "project-management", "major", "A breaking change.", "a.yaml")
    directory = changesets.unreleased_dir(source_kit.parent)
    (directory / "b.yaml").write_text(
        "component: software-engineering\nkind: minor\nbody: Uses both.\n"
        "requires_capabilities:\n  project-management: '0.53.0'\n"
        "runs_on_capabilities:\n  project-management: release\n",
        encoding="utf-8",
    )

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 9, 30))

    assert 'version: ">=0.53.0,<2.0.0"' in dependent.read_text()
    assert (
        "Uses both. Requires project-management >=0.53.0. Runs on project-management <2.0.0.\n"
    ) in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("component", "kind", "runs_on", "problem"),
    [
        (
            "backbone",
            "minor",
            {"project-management": "release"},
            "the backbone has no `requires_capabilities` to widen",
        ),
        (
            "software-engineering",
            "none",
            {"project-management": "release"},
            "a `none` changeset moves no version",
        ),
        (
            "software-engineering",
            "minor",
            {"evidence": "release"},
            "but no pending changeset moves evidence",
        ),
        (
            "software-engineering",
            "minor",
            {"project-management": "'1.0.0'"},
            "`runs_on_capabilities.project-management` takes only `release`",
        ),
        (
            "software-engineering",
            "minor",
            {"backbone": "release"},
            "names 'backbone', which is the backbone",
        ),
        (
            "software-engineering",
            "minor",
            {"wildware": "release"},
            "which is no component this tree carries",
        ),
        ("living-docs", "minor", {"project-management": "release"}, "does not list"),
        ("houseware", "minor", {"project-management": "release"}, "lists 2 times"),
        ("oddware", "minor", {"project-management": "release"}, "the release cannot widen"),
    ],
)
def test_compute_refuses_a_runs_on_it_cannot_carry(
    tmp_path: Path, component: str, kind: str, runs_on: dict[str, str], problem: str
) -> None:
    """A declared widening is never dropped silently: the release refuses."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    _write_capability(source_kit, "evidence", "0.5.0", ">=1.0.0,<2.0.0")
    _write_capability(source_kit, "living-docs", "0.1.0", ">=1.0.0,<2.0.0")
    _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.50.0,<1.0.0")
    _write_dependent(
        source_kit,
        "houseware",
        "0.1.0",
        ">=0.50.0,<1.0.0",
        extra='  - name: project-management\n    version: ">=0.40.0"\n',
    )
    odd = _write_capability(source_kit, "oddware", "0.1.0", ">=1.0.0,<2.0.0")
    odd.write_text(
        odd.read_text()
        + 'requires_capabilities: [{name: project-management, version: ">=0.5.0"}]\n',
        encoding="utf-8",
    )
    _add(source_kit, "project-management", "minor", "A new floor.", "a.yaml")
    _add_runs_on(source_kit, component, kind, "b.yaml", runs_on)

    with pytest.raises(
        click.ClickException, match="cannot widen a requires_capabilities upper bound"
    ) as err:
        release.compute_release(source_kit)
    assert problem in err.value.message


def test_an_explicit_floor_past_the_upper_bound_still_refuses_the_release(tmp_path: Path) -> None:
    """Only `release` claims to run on a version: an explicit floor at a release
    the bound excludes widens nothing, and `plan` refuses the empty range before
    `apply` writes anything."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_component_releases(source_kit, "project-management", "1.0.0")
    _write_capability(source_kit, "project-management", "1.0.0", ">=1.0.0,<2.0.0")
    _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _add_capability_floor(
        source_kit, "software-engineering", "minor", "a.yaml", {"project-management": "'1.0.0'"}
    )

    with pytest.raises(click.ClickException, match="admit no version of project-management"):
        release.compute_release(source_kit)


def test_a_range_that_excludes_the_version_a_release_writes_refuses_the_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project-management major two dependents' bounds exclude: `plan`, `plan
    --json` and `apply` refuse before anything is written, naming each dependent,
    its range, the capability and the version, and what to declare."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pm = _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _write_dependent(source_kit, "living-docs", "0.1.0", ">=0.40.0,<1.0.0")
    _add(source_kit, "project-management", "major", "A breaking change.", "a.yaml")
    before = dependent.read_text()

    with pytest.raises(click.ClickException) as err:
        release.compute_release(source_kit)
    message = err.value.message
    assert message.startswith(
        "cannot leave a capability whose range excludes the version of a capability it "
        "depends on (PRJ-002 D4); nothing was written:"
    )
    for name, version_range in (
        ("living-docs", ">=0.40.0,<1.0.0"),
        ("software-engineering", ">=0.54.0,<1.0.0"),
    ):
        assert (
            f"{name}: its range on project-management, {version_range!r}, excludes "
            "project-management 1.0.0, the version this release writes for it. If "
            f"{name} runs on project-management 1.0.0, declare it on a changeset of {name} "
            "that moves its version — `runs_on_capabilities: {project-management: release}`"
        ) in message

    monkeypatch.chdir(tmp_path)
    for args in (["release", "plan"], ["release", "plan", "--json"], ["release", "apply", "--yes"]):
        result = CliRunner().invoke(main, args)
        assert result.exit_code == 1, result.output
        assert "software-engineering: its range on project-management" in result.output

    assert dependent.read_text() == before
    assert "  version: 0.54.0\n" in pm.read_text()
    assert not (tmp_path / "CHANGELOG.md").exists()
    assert len(list(changesets.unreleased_dir(tmp_path).glob("*.yaml"))) == 1


def test_a_range_that_excludes_the_version_the_tree_carries_refuses_the_release(
    tmp_path: Path,
) -> None:
    """A dependency the release does not move is read at the version the tree
    carries. No declaration answers that, so the refusal names the pair and the
    correction a branch may make (PRJ-002 D1)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "1.0.0", ">=1.0.0,<2.0.0")
    _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _add(source_kit, "software-engineering", "patch", "A fix.", "a.yaml")

    with pytest.raises(click.ClickException) as err:
        release.compute_release(source_kit)

    assert (
        "excludes project-management 1.0.0, the version this release carries for it. No "
        "pending changeset moves project-management, so no declaration widens the range: "
        "correct it on a branch to admit project-management 1.0.0, moving only the bound that "
        "excludes it (PRJ-002 D1). `pkit validate` reports the pair out of range where both "
        "are installed."
    ) in err.value.message
    assert "runs_on_capabilities" not in err.value.message


def test_a_release_that_moves_no_version_is_not_refused_for_a_range(tmp_path: Path) -> None:
    """Only `none` changesets: the release writes no version and no tag, so a
    range out of step with the tree is left to validation, and the sweep runs."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "1.0.0", ">=1.0.0,<2.0.0")
    _write_dependent(source_kit, "software-engineering", "0.2.0", ">=0.54.0,<1.0.0")
    _add(source_kit, "software-engineering", "none", "Docs only.", "a.yaml")

    plan = release.compute_release(source_kit)

    assert plan.is_empty
    release.apply_release(source_kit, plan, tag=False)
    assert list(changesets.unreleased_dir(tmp_path).glob("*.yaml")) == []


def test_the_plan_json_carries_no_dependency_warnings(tmp_path: Path) -> None:
    """A range that excludes a dependency refuses the plan, so its JSON has no
    key for one."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "project-management", "minor", "A new floor.", "a.yaml")

    summary = release.release_summary(source_kit, release.compute_release(source_kit))

    assert "dependency_warnings" not in summary
    (rel,) = cast("list[dict[str, object]]", summary["releases"])
    assert rel["requires_capabilities_bounds"] == []


def test_both_floors_close_the_entry_of_the_changeset_that_set_them(tmp_path: Path) -> None:
    """The backbone's sentence first, then each capability's, in name order."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_component_releases(source_kit, "evidence", "0.4.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    _write_capability(source_kit, "evidence", "0.5.0", ">=1.0.0,<2.0.0")
    _write_dependent(
        source_kit,
        "living-docs",
        "0.1.0",
        ">=0.50.0,<1.0.0",
        extra='  - name: evidence\n    version: ">=0.1.0,<1.0.0"\n',
    )
    _add(source_kit, "project-management", "minor", "A new floor.", "a.yaml")
    directory = changesets.unreleased_dir(source_kit.parent)
    (directory / "b.yaml").write_text(
        "component: living-docs\nkind: minor\nbody: Uses both.\nrequires_backbone: release\n"
        "requires_capabilities:\n  project-management: release\n  evidence: '0.4.0'\n",
        encoding="utf-8",
    )

    entry = release.render_changelog_entry(release.compute_release(source_kit), date(2026, 9, 30))

    assert (
        "- **living-docs 0.2.0** — Uses both. Requires backbone >=1.5.0. Requires evidence "
        ">=0.4.0. Requires project-management >=0.55.0.\n"
    ) in entry


def test_an_explicit_capability_floor_is_bounded_by_the_installed_version(
    tmp_path: Path,
) -> None:
    """The version the tree carries is the one validation reads: a registered
    capability's manifest, not its package. Its package ahead of its manifest, an
    explicit floor at the package's version is refused, and one at the
    manifest's passes."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _record_component_releases(source_kit, "project-management", "0.53.0", "0.54.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    _write_dependent(source_kit, "living-docs", "0.1.0", ">=0.50.0,<1.0.0")
    receipt = source_kit / "capabilities" / "project-management" / "project" / "manifest.yaml"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: project-management\n"
        "  version: 0.53.0\n",
        encoding="utf-8",
    )
    (source_kit / "manifest.yaml").write_text(
        "schema_version: 1\nbackbone_version: 1.5.0\ncomponents:\n"
        "  - kind: capability\n    name: project-management\n"
        "    manifest: .pkit/capabilities/project-management/project/manifest.yaml\n",
        encoding="utf-8",
    )
    _add_capability_floor(
        source_kit, "living-docs", "patch", "a.yaml", {"project-management": '"0.54.0"'}
    )

    with pytest.raises(
        click.ClickException, match=r"above the version this tree carries for it \(0\.53\.0"
    ):
        release.compute_release(source_kit)

    _add_capability_floor(
        source_kit, "living-docs", "patch", "a.yaml", {"project-management": '"0.53.0"'}
    )
    (floor,) = release.compute_release(source_kit).releases[0].capability_floors
    assert floor.new_floor == "0.53.0"


def test_a_registry_that_does_not_read_leaves_the_release_planning(tmp_path: Path) -> None:
    """The release reads the registry only for the versions the tree carries. A
    registry entry it cannot read leaves each package's version, as before this
    read, and validation reports the registry."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    (source_kit / "manifest.yaml").write_text(
        "schema_version: 1\nbackbone_version: 1.5.0\ncomponents:\n  - kind: capability\n",
        encoding="utf-8",
    )
    _add(source_kit, "project-management", "patch", "A fix.", "a.yaml")

    plan = release.compute_release(source_kit)

    assert plan.versions.carries["project-management"] == "0.54.0"
    assert plan.versions.writes == {"project-management": "0.54.1"}


def test_the_release_commit_validates_after_a_release_floor_rises_on_project_management(
    tmp_path: Path,
) -> None:
    """A tree shaped like project-kit's source: project-management registered
    kit-shipped with no manifest (ADR-059), living-docs incubated. Validation reads
    project-management from the `package.yaml` whose `version:` line the release
    writes (PRJ-007 point 1, ADR-065 point 2). So after a release raises living-docs'
    floor to the project-management it writes, validation still reads the pair in
    range."""
    from project_kit import connections

    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pm = _write_capability(source_kit, "project-management", "0.54.0", ">=1.0.0,<2.0.0")
    dependent = _write_dependent(source_kit, "living-docs", "0.1.0", ">=0.54.0,<1.0.0")
    (source_kit / "manifest.yaml").write_text(
        "schema_version: 1\nbackbone_version: 1.5.0\ncomponents:\n"
        "  - kind: capability\n    name: project-management\n"
        "    manifest: .pkit/capabilities/project-management/project/manifest.yaml\n"
        "  - kind: capability\n    name: living-docs\n"
        "    manifest: .pkit/capabilities/living-docs/manifest.yaml\n"
        "    origin: incubated-in-repo\n",
        encoding="utf-8",
    )
    assert connections.versions_outcome(tmp_path).errors == ()
    _add(source_kit, "project-management", "minor", "A new floor.", "a.yaml")
    _add_capability_floor(
        source_kit, "living-docs", "minor", "b.yaml", {"project-management": "release"}
    )

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert "  version: 0.55.0\n" in pm.read_text(encoding="utf-8")
    assert 'version: ">=0.55.0,<1.0.0"' in dependent.read_text(encoding="utf-8")
    capabilities = source_kit / "capabilities"
    assert not [
        *capabilities.glob("*/manifest.yaml"),
        *capabilities.glob("*/project/manifest.yaml"),
    ]
    assert connections.versions_outcome(tmp_path).errors == ()


# --- Dogfood: the release that ships the backbone-owned journal line ---------

REPO_ROOT = Path(__file__).resolve().parent.parent

# The backbone release that took the process-journal ignore line over from the
# project-management package (#1120; its migration is
# `.pkit/migrations/backbone/1.150.0/001-keep-process-journal-logging.sh`).
JOURNAL_LINE_BACKBONE = "1.150.0"


def test_pending_release_leaves_project_management_on_the_journal_owning_backbone(
    tmp_path: Path,
) -> None:
    """project-management stopped declaring the journal ignore line when the backbone
    took it over, so on an older backbone its journals go unignored. Applying the
    pending changesets to a copy of this tree must leave its floor at or above that
    backbone: until the release that ships it has run, the changeset that dropped
    the line raises the floor; afterwards the package carries it."""
    source_kit = tmp_path / ".pkit"
    source_kit.mkdir()
    shutil.copy(REPO_ROOT / ".pkit" / "VERSION", source_kit / "VERSION")
    for package in (REPO_ROOT / ".pkit").rglob("package.yaml"):
        target = source_kit / package.relative_to(REPO_ROOT / ".pkit")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(package, target)
    pending = changesets.unreleased_dir(REPO_ROOT)
    if pending.is_dir():
        shutil.copytree(pending, changesets.unreleased_dir(tmp_path))

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 9, 29))

    package = source_kit / "capabilities" / "project-management" / "package.yaml"
    floor = versioning.requires_backbone_floor(package.read_text(encoding="utf-8"))
    assert floor is not None
    assert parse_version_tuple(floor) >= parse_version_tuple(JOURNAL_LINE_BACKBONE)
