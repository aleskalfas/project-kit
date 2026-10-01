"""Tests for the Connections section of `pkit status` (#997, COR-053 point 7):
the wiring per role — its provider, a conflict with the exact command that
resolves it, orphaned — and per point — the bound fillers and counterparts, the
inert ones, the unmet mandatory marks — read from `pkit validate`'s own wiring,
leaving each data point's resolution to the Data points section."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from project_kit import connections as cx
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.connection_capabilities import (
    DOCS,
    GLOSSARY,
    PAGE_CREATED,
    READERS,
    READERS_FILLER,
    contributes,
    data_point,
    event_point,
    provider,
    stage,
    write_config,
)

INDENT = " " * 25


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def _connections_section(output: str) -> list[str]:
    return output.split("\n  Connections\n")[1].split("\n\n")[0].splitlines()


def _status(repo: AdopterRepo) -> str:
    result = CliRunner().invoke(main, ["--color", "never", "status"])
    assert result.exit_code == 0, result.output
    return result.output


def test_status_shows_each_role_and_what_reaches_each_point(repo: AdopterRepo) -> None:
    stage(
        repo,
        "docs-a",
        provider(
            accepts={READERS: data_point(mandatory={"reason": "pages cite readers"})},
            offers={PAGE_CREATED: event_point()},
        ),
    )
    stage(repo, "evidence", contributes(version=2, mandatory={"reason": "the pages cite it"}))
    stage(
        repo,
        "notifier",
        {
            "extensions": {
                "subscribes": [{"point": PAGE_CREATED, "schema_version": 1, "command": "publish"}]
            }
        },
    )
    stage(repo, "glossary-user", contributes(GLOSSARY))
    assert _connections_section(_status(repo)) == [
        "    roles              2 named: 1 active, 0 in conflict, 1 orphaned",
        f"{INDENT}pkit::analysis — orphaned: no installed capability provides it",
        f"{INDENT}{DOCS} → docs-a",
        "    points             2 defined: 1 unfilled, 2 unmet mandatory mark(s)",
        f"    {PAGE_CREATED}",
        f"{INDENT}event v1 · docs-a — 1 bound",
        f"{INDENT}bound    notifier (subscribes)",
        f"    {READERS}",
        f"{INDENT}data v1 · docs-a · mandatory — unfilled",
        f"{INDENT}inert    evidence (contributes) — targets v2; the point is at v1 · mandatory, "
        "unmet",
        f"{INDENT}unmet    mandatory, filled only by its default (reason: pages cite readers)",
        "    unreached          1 counterpart(s) reach no point:",
        f"{INDENT}glossary-user (contributes) {GLOSSARY} — no active provider",
    ]


def test_status_names_the_command_that_resolves_a_conflict(repo: AdopterRepo) -> None:
    stage(repo, "docs-a", provider(accepts={READERS: data_point()}))
    stage(repo, "docs-b", provider(accepts={READERS: data_point()}))
    stage(repo, "evidence", contributes())
    assert _connections_section(_status(repo)) == [
        "    roles              1 named: 0 active, 1 in conflict, 0 orphaned",
        f"{INDENT}{DOCS} — conflict: docs-a, docs-b provide it and none is selected",
        f"{INDENT}  fix: pkit connections providers set {DOCS} docs-a",
        f"{INDENT}  fix: pkit connections providers set {DOCS} docs-b",
        "    points             none defined",
        "    unreached          1 counterpart(s) reach no point:",
        f"{INDENT}evidence (contributes) {READERS} — no active provider",
    ]


def test_status_after_the_selection_shows_the_provider_filler_and_inert_contribution(
    repo: AdopterRepo,
) -> None:
    """The selected provider answers; the unselected one's contribution is not
    delivered; the project filler fills the point. The point's value is the Data
    points section's, not repeated under Connections."""
    stage(repo, "docs-a", provider(accepts={READERS: data_point()}))
    stage(repo, "docs-b", provider(accepts={READERS: data_point()}) | contributes())
    write_config(repo, f"connections:\n  providers:\n    {DOCS}: docs-a\n")
    repo.write({READERS_FILLER: json.dumps({"schema_version": 1, "value": ["developer"]})})
    output = _status(repo)
    assert _connections_section(output) == [
        "    roles              1 named: 1 active, 0 in conflict, 0 orphaned",
        f"{INDENT}{DOCS} → docs-a (selected; not selected: docs-b)",
        "    points             1 defined: 0 unfilled, 0 unmet mandatory mark(s)",
        f"    {READERS}",
        f"{INDENT}data v1 · docs-a — filled",
        f"{INDENT}bound    project filler {READERS_FILLER}",
        f"{INDENT}inert    docs-b (contributes) — not delivered: docs-b provides a role for which "
        "it is not the selected provider",
    ]
    assert "developer" not in "\n".join(_connections_section(output))
    assert "developer" in output.split("\n  Data points\n")[1]


def test_status_shows_a_selection_naming_no_provider_with_the_fix(repo: AdopterRepo) -> None:
    stage(repo, "docs-a", provider(accepts={READERS: data_point()}))
    stage(repo, "other")
    write_config(repo, f"connections:\n  providers:\n    {DOCS}: other\n")
    assert _connections_section(_status(repo))[:3] == [
        "    roles              1 named: 0 active, 0 in conflict, 0 orphaned",
        f"{INDENT}{DOCS} — the selection names 'other', which does not provide it",
        f"{INDENT}  fix: pkit connections providers set {DOCS} docs-a",
    ]


def test_status_on_a_fresh_install_names_no_role(repo: AdopterRepo) -> None:
    assert _connections_section(_status(repo)) == [
        "    roles              none named",
        "    points             none defined",
    ]


def test_status_reads_one_wiring_for_connections_and_data_points(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage(repo, "docs-a", provider(accepts={READERS: data_point()}))
    stage(repo, "evidence", contributes())
    calls = []
    resolve = cx.resolve_wiring

    def counting(root):
        calls.append(root)
        return resolve(root)

    monkeypatch.setattr(cx, "resolve_wiring", counting)
    _status(repo)
    assert len(calls) == 1
