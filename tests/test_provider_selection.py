"""Tests for `pkit connections providers set` (#997, COR-053 point 7): the
provider selection written into the backbone configuration through the
consent-gated writer (COR-048 point 5) — the diff first, `--dry-run` stopping
there, `--yes` or a terminal's confirmation writing it — after checking that the
capability declares the role; and the role-conflict report naming the exact
command that resolves it."""

from __future__ import annotations

import pytest
from click.testing import CliRunner, Result

from project_kit import config_validate as cv
from project_kit import connections as cx
from project_kit import project_config as pc
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.connection_capabilities import (
    DOCS,
    READERS,
    data_point,
    provider,
    stage,
    write_config,
)

CONFIG = ".pkit/project/config.yaml"


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """`pkit::documentation` provided twice, no selection: a role conflict."""
    repo = make_adopter_repo()
    stage(repo, "docs-a", provider(accepts={READERS: data_point()}))
    stage(repo, "docs-b", provider(accepts={READERS: data_point()}))
    stage(repo, "other")
    return repo


def _set(*args: str, input: str | None = None) -> Result:
    return CliRunner().invoke(main, ["connections", "providers", "set", *args], input=input)


def _config(repo: AdopterRepo) -> str | None:
    path = pc.project_config_path(repo.root)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def test_dry_run_shows_the_diff_and_writes_nothing(repo: AdopterRepo) -> None:
    result = _set(DOCS, "docs-b", "--dry-run")
    assert result.exit_code == 0, result.output
    assert f"--- a/{CONFIG}" in result.output and f"+++ b/{CONFIG}" in result.output
    assert f"+{pc.EDITOR_DIRECTIVE}" in result.output  # the file the write would create
    assert "+connections:\n+  providers:\n+    pkit::documentation: docs-b\n" in result.output
    assert result.output.rstrip().endswith("Dry run: nothing written.")
    assert _config(repo) is None


def test_yes_writes_the_selection_and_resolves_the_conflict(repo: AdopterRepo) -> None:
    before = cx.resolve_wiring(repo.root).role(DOCS)
    assert before is not None and before.conflict
    result = _set(DOCS, "docs-b", "--yes")
    assert result.exit_code == 0, result.output
    assert f"set connections.providers.{DOCS} = docs-b  ({CONFIG})" in result.output
    assert "+    pkit::documentation: docs-b" in result.output  # the diff is shown
    role = cx.resolve_wiring(repo.root).role(DOCS)
    assert role is not None and role.active == "docs-b" and not role.conflict
    assert cv.run_configuration_pass(repo.root).errors == ()  # validate accepts what it wrote


def test_the_write_keeps_the_files_other_keys_and_comments(repo: AdopterRepo) -> None:
    write_config(
        repo,
        "# our settings\nname: alpha  # the project\nconnections:\n  providers:\n"
        f"    {DOCS}: docs-a\n",
    )
    result = _set(DOCS, "docs-b", "--yes")
    assert result.exit_code == 0, result.output
    assert "-    pkit::documentation: docs-a\n+    pkit::documentation: docs-b\n" in result.output
    text = _config(repo) or ""
    assert text.startswith("# our settings\nname: alpha  # the project\n")
    assert pc.EDITOR_DIRECTIVE not in text
    assert f"    {DOCS}: docs-b\n" in text


def test_a_terminal_confirms_after_the_diff(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: True)
    result = _set(DOCS, "docs-a", input="y\n")
    assert result.exit_code == 0, result.output
    diff_at = result.output.index("+    pkit::documentation: docs-a")
    prompt = f"Set connections.providers.{DOCS} = 'docs-a' in {CONFIG}?"
    assert diff_at < result.output.index(prompt)
    assert f"    {DOCS}: docs-a\n" in (_config(repo) or "")


def test_non_interactive_without_yes_refuses_naming_the_exact_command(repo: AdopterRepo) -> None:
    result = _set(DOCS, "docs-b")
    assert result.exit_code != 0
    assert "stdin is not a terminal and --yes was not given" in result.output
    assert "pkit connections providers set pkit::documentation docs-b --yes" in result.output
    assert _config(repo) is None


def test_a_capability_that_does_not_declare_the_role_is_refused(repo: AdopterRepo) -> None:
    result = _set(DOCS, "other", "--yes")
    assert result.exit_code != 0
    assert (
        "refusing to select 'other' for role 'pkit::documentation': 'other' does not provide "
        "role 'pkit::documentation' (it provides no role); the installed providers of the role "
        "are 'docs-a', 'docs-b': `pkit connections providers set pkit::documentation docs-a` or "
        "`pkit connections providers set pkit::documentation docs-b` (COR-053 point 7)."
    ) in " ".join(result.output.split())
    assert _config(repo) is None


def test_a_capability_that_is_not_installed_is_refused(repo: AdopterRepo) -> None:
    result = _set(DOCS, "ghost", "--dry-run")
    assert result.exit_code != 0
    assert "'ghost' is not an installed capability" in result.output
    assert "`pkit capabilities install ghost`" in result.output
    assert _config(repo) is None


def test_the_same_selection_again_writes_nothing(repo: AdopterRepo) -> None:
    assert _set(DOCS, "docs-a", "--yes").exit_code == 0
    before = _config(repo)
    result = _set(DOCS, "docs-a", "--yes")
    assert result.exit_code == 0, result.output
    assert f"connections.providers.{DOCS} is already docs-a; nothing to write." in result.output
    assert _config(repo) == before


def test_yes_and_dry_run_exclude_each_other(repo: AdopterRepo) -> None:
    result = _set(DOCS, "docs-a", "--yes", "--dry-run")
    assert result.exit_code == 2
    assert "--yes and --dry-run exclude each other" in result.output


def test_the_role_conflict_names_the_command_that_resolves_it(repo: AdopterRepo) -> None:
    """`pkit validate` names the command once per provider; running one clears it."""
    result = CliRunner().invoke(main, ["validate", "--no-refs", "--only", "connections"])
    assert result.exit_code == 1, result.output
    flat = " ".join(result.output.split())
    for name in ("docs-a", "docs-b"):
        assert f"`pkit connections providers set pkit::documentation {name}`" in flat
    assert _set(DOCS, "docs-a", "--yes").exit_code == 0
    again = CliRunner().invoke(main, ["validate", "--no-refs", "--only", "connections"])
    assert again.exit_code == 0, again.output


def test_the_preview_is_what_the_write_makes(repo: AdopterRepo) -> None:
    """The dry run's diff is computed by the writer's own path: the preview's text
    is byte for byte what the write then puts in the file."""
    mutate = pc.set_path
    change = pc.preview_config(
        repo.root, lambda data: mutate(data, (cx.CONNECTIONS_KEY, cx.PROVIDERS_KEY, DOCS), "docs-b")
    )
    assert change.before == "" and change.changes
    assert _config(repo) is None
    pc.write_config(
        repo.root,
        lambda data: mutate(data, (cx.CONNECTIONS_KEY, cx.PROVIDERS_KEY, DOCS), "docs-b"),
        consent=pc.Consent(yes=True),
    )
    assert _config(repo) == change.after
