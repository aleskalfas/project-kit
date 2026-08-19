"""Tests for the Projects-v2 board READ seam (`_lib/board_fields`, #724).

The seam is what makes `set-field --priority High` writable on a board-carried
axis: it turns the names an adopter already speaks (board number, `Priority`,
`High`) into the four ids a field-value write needs. These tests pin

  * the argv each read issues (host/owner threading is the `gh` helper's job; the
    seam must ask for the right thing),
  * name → id matching, including the case-insensitive fallback,
  * the failure contract: `ok=False` with gh's stderr VERBATIM (the missing
    `read:project` scope is the likeliest board failure and its remedy is in that
    text), and
  * the membership case — a successful card lookup that found no card is
    `ok=True, item_id=None`, distinct from a failed read.

Every `gh` invocation is a fake runner; nothing here touches a network.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
MODULE_PATH = SCRIPTS / "_lib" / "board_fields.py"


@pytest.fixture(scope="module")
def bf():
    if str(SCRIPTS / "_lib") not in sys.path:
        sys.path.insert(0, str(SCRIPTS / "_lib"))
    spec = importlib.util.spec_from_file_location("pm_board_fields_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_board_fields_under_test"] = module
    spec.loader.exec_module(module)
    return module


BOARD_CONFIG = {
    "has_projects_v2_board": True,
    "projects_v2_board_id": 7,
    "gh": {"default_owner": "an-org"},
}

FIELD_LIST_PAYLOAD = {
    "fields": [
        {"id": "PVTF_title", "name": "Title", "type": "ProjectV2Field"},
        {
            "id": "PVTSSF_priority",
            "name": "Priority",
            "type": "ProjectV2SingleSelectField",
            "options": [
                {"id": "opt_high", "name": "High"},
                {"id": "opt_low", "name": "Low"},
            ],
        },
    ]
}


def _runner(stdout: str = "{}", *, returncode: int = 0, stderr: str = "", calls=None):
    """A fake gh runner recording each argv it is handed."""

    def run(args, config, *, fallback_owner=None, check=False):
        if calls is not None:
            calls.append({"args": list(args), "fallback_owner": fallback_owner})
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    return run


# --- config readers ---------------------------------------------------------


def test_board_number_reads_the_configured_number(bf) -> None:
    assert bf.board_number(BOARD_CONFIG) == "7"


def test_board_number_none_without_the_flag(bf) -> None:
    assert bf.board_number({"projects_v2_board_id": 7}) is None


def test_board_number_none_without_the_id(bf) -> None:
    assert bf.board_number({"has_projects_v2_board": True}) is None


def test_default_owner_reads_the_gh_block(bf) -> None:
    assert bf.default_owner(BOARD_CONFIG) == "an-org"
    assert bf.default_owner({}) is None


# --- project node id --------------------------------------------------------


def test_read_project_node_id_resolves_the_board_number(bf) -> None:
    calls: list = []
    lookup = bf.read_project_node_id(
        BOARD_CONFIG,
        owner="an-org",
        gh_call=_runner(json.dumps({"id": "PVT_board7"}), calls=calls),
    )
    assert lookup.ok is True and lookup.node_id == "PVT_board7"
    assert calls[0]["args"] == ["gh", "project", "view", "7", "--format", "json"]
    assert calls[0]["fallback_owner"] == "an-org"


def test_read_project_node_id_refuses_without_a_configured_board(bf) -> None:
    lookup = bf.read_project_node_id({}, gh_call=_runner())
    assert lookup.ok is False
    assert "has_projects_v2_board" in (lookup.error or "")


def test_read_project_node_id_surfaces_stderr_verbatim(bf) -> None:
    stderr = "error: could not resolve to a ProjectV2 with the number 7"
    lookup = bf.read_project_node_id(
        BOARD_CONFIG, gh_call=_runner(returncode=1, stderr=stderr)
    )
    assert lookup.ok is False and lookup.error == stderr


def test_resolve_project_node_id_is_the_lossy_form(bf) -> None:
    assert (
        bf.resolve_project_node_id(
            BOARD_CONFIG, gh_call=_runner(json.dumps({"id": "PVT_board7"}))
        )
        == "PVT_board7"
    )
    assert bf.resolve_project_node_id(BOARD_CONFIG, gh_call=_runner(returncode=1)) is None


# --- field list + options ---------------------------------------------------


def test_read_fields_returns_fields_with_their_options(bf) -> None:
    calls: list = []
    read = bf.read_fields(
        BOARD_CONFIG, owner="an-org", gh_call=_runner(json.dumps(FIELD_LIST_PAYLOAD), calls=calls)
    )
    assert read.ok is True
    assert bf.field_names(read.fields) == ["Title", "Priority"]
    assert calls[0]["args"] == ["gh", "project", "field-list", "7", "--format", "json"]


def test_read_fields_surfaces_a_missing_scope_verbatim(bf) -> None:
    stderr = (
        "error: your authentication token is missing required scopes "
        "[read:project]. To request it, run: gh auth refresh -s read:project"
    )
    read = bf.read_fields(BOARD_CONFIG, gh_call=_runner(returncode=1, stderr=stderr))
    assert read.ok is False and read.error == stderr


def test_read_fields_reports_non_json_output(bf) -> None:
    read = bf.read_fields(BOARD_CONFIG, gh_call=_runner("not json"))
    assert read.ok is False and "non-JSON" in (read.error or "")


def test_read_fields_missing_gh_binary_is_a_failure_not_a_crash(bf) -> None:
    def boom(args, config, *, fallback_owner=None, check=False):
        raise FileNotFoundError

    read = bf.read_fields(BOARD_CONFIG, gh_call=boom)
    assert read.ok is False and "not on PATH" in (read.error or "")


# --- name → id matching -----------------------------------------------------


def test_find_field_matches_exactly_then_case_insensitively(bf) -> None:
    fields = ({"name": "priority", "id": "lower"}, {"name": "Priority", "id": "exact"})
    assert bf.find_field(fields, "Priority")["id"] == "exact"
    assert bf.find_field(fields, "PRIORITY")["id"] == "lower"  # first case-insensitive hit
    assert bf.find_field(fields, "Workstream") is None


def test_is_single_select_discriminates_the_supported_kind(bf) -> None:
    assert bf.is_single_select({"type": "ProjectV2SingleSelectField"}) is True
    assert bf.is_single_select({"type": "ProjectV2Field"}) is False
    assert bf.is_single_select({"type": "ProjectV2IterationField"}) is False
    assert bf.field_type({}) == "<unknown>"


def test_option_id_matches_exactly_then_case_insensitively(bf) -> None:
    field = FIELD_LIST_PAYLOAD["fields"][1]
    assert bf.option_id(field, "High") == "opt_high"
    assert bf.option_id(field, "hIgH") == "opt_high"
    assert bf.option_id(field, "Medium") is None


def test_option_id_prefers_an_exact_match_over_an_earlier_case_variant(bf) -> None:
    field = {
        "options": [{"id": "loose", "name": "high"}, {"id": "exact", "name": "High"}]
    }
    assert bf.option_id(field, "High") == "exact"


def test_option_names_lists_what_the_field_offers(bf) -> None:
    assert bf.option_names(FIELD_LIST_PAYLOAD["fields"][1]) == ["High", "Low"]
    assert bf.option_names({"type": "ProjectV2Field"}) == []


# --- the card (item) lookup -------------------------------------------------


def _items_payload(*pairs: tuple[str, str]) -> str:
    return json.dumps(
        {
            "data": {
                "node": {
                    "projectItems": {
                        "nodes": [
                            {"id": item_id, "project": {"id": project_id}}
                            for item_id, project_id in pairs
                        ]
                    }
                }
            }
        }
    )


def test_resolve_item_id_finds_the_card_on_the_right_board(bf) -> None:
    calls: list = []
    lookup = bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_board7",
        gh_call=_runner(
            _items_payload(("PVTI_other", "PVT_other"), ("PVTI_card42", "PVT_board7")),
            calls=calls,
        ),
    )
    assert lookup.ok is True and lookup.item_id == "PVTI_card42"
    argv = calls[0]["args"]
    assert argv[:3] == ["gh", "api", "graphql"]
    assert "issue=I_issue42" in argv


def test_resolve_item_id_reports_the_membership_case_as_no_card(bf) -> None:
    """A successful read that found no card on THIS board: `ok=True, item_id=None` —
    the caller refuses with a remediation rather than treating it as a read error."""
    lookup = bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_board7",
        gh_call=_runner(_items_payload(("PVTI_other", "PVT_other"))),
    )
    assert lookup.ok is True and lookup.item_id is None


def test_resolve_item_id_surfaces_a_scope_failure_verbatim(bf) -> None:
    stderr = (
        "your token has not been granted the required scopes to execute this query. "
        "missing: 'read:project'"
    )
    lookup = bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_board7",
        gh_call=_runner(returncode=1, stderr=stderr),
    )
    assert lookup.ok is False and lookup.error == stderr
    assert lookup.item_id is None


def test_resolve_item_id_includes_archived_cards_in_the_query(bf) -> None:
    """An archived card still has field values worth writing; reporting it as "not on
    the board" would send the adopter to add a duplicate."""
    calls: list = []
    bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_board7",
        gh_call=_runner(_items_payload(), calls=calls),
    )
    query = next(a for a in calls[0]["args"] if a.startswith("query="))
    assert "includeArchived: true" in query
