"""Tests for the check-mesh script's pure logic.

Covers peer-URI parsing, peer-spec resolution from config, drift
comparison logic, and the summary builder.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "check-mesh.py"
)


@pytest.fixture(scope="module")
def cm():
    module_name = "pm_check_mesh_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- URI parsing -----------------------------------------------------


def test_parse_peer_uri_simple(cm) -> None:
    spec = cm.parse_peer_uri("github://owner/repo")
    assert spec is not None
    assert spec.owner == "owner"
    assert spec.repo == "repo"
    assert spec.full == "owner/repo"


def test_parse_peer_uri_with_path(cm) -> None:
    spec = cm.parse_peer_uri("github://owner/repo/path/to/mesh.yaml")
    assert spec is not None
    assert spec.owner == "owner"
    assert spec.repo == "repo"


def test_parse_peer_uri_rejects_invalid(cm) -> None:
    assert cm.parse_peer_uri("not-a-uri") is None
    assert cm.parse_peer_uri("https://github.com/owner/repo") is None
    assert cm.parse_peer_uri("") is None
    assert cm.parse_peer_uri(None) is None  # type: ignore[arg-type]


def test_parse_peer_uri_strips_whitespace(cm) -> None:
    spec = cm.parse_peer_uri("  github://owner/repo  ")
    assert spec is not None
    assert spec.full == "owner/repo"


# --- config resolution -----------------------------------------------


def test_resolve_peer_specs_from_mesh_peers(cm) -> None:
    config = {
        "mesh_peers": [
            "github://acme/repo1",
            "github://acme/repo2",
        ]
    }
    out = cm.resolve_peer_specs(config)
    assert isinstance(out, list)
    assert len(out) == 2
    assert {p.full for p in out} == {"acme/repo1", "acme/repo2"}


def test_resolve_peer_specs_from_mesh_source(cm) -> None:
    config = {"mesh_source": "github://acme/governance/path/mesh.yaml"}
    out = cm.resolve_peer_specs(config)
    assert isinstance(out, list)
    assert len(out) == 1


def test_resolve_peer_specs_both_set_concatenates(cm) -> None:
    config = {
        "mesh_peers": ["github://acme/repo1"],
        "mesh_source": "github://acme/governance",
    }
    out = cm.resolve_peer_specs(config)
    assert isinstance(out, list)
    assert len(out) == 2


def test_resolve_peer_specs_empty_when_neither_set(cm) -> None:
    out = cm.resolve_peer_specs({})
    assert isinstance(out, list)
    assert out == []


def test_resolve_peer_specs_rejects_non_list_mesh_peers(cm) -> None:
    out = cm.resolve_peer_specs({"mesh_peers": "github://acme/repo"})
    assert isinstance(out, str)
    assert "must be a list" in out


def test_resolve_peer_specs_rejects_invalid_uri(cm) -> None:
    out = cm.resolve_peer_specs({"mesh_peers": ["not-a-uri"]})
    assert isinstance(out, str)
    assert "invalid" in out


# --- comparison ------------------------------------------------------


def _make_state(cm, peer_full: str, labels=None, version=None, members=None, milestones=None):
    owner, _, repo = peer_full.partition("/")
    spec = cm.PeerSpec(owner=owner, repo=repo)
    return cm.PeerState(
        peer=spec,
        labels=labels or [],
        capability_version=version,
        members=members or [],
        milestones=milestones or [],
    )


def test_compare_no_drift_when_identical(cm) -> None:
    local = _make_state(
        cm,
        "us/local",
        labels=["type:feature", "type:bug", "priority:High"],
        version="0.6.0",
        members=[{"github_login": "alice"}],
        milestones=["M1"],
    )
    peer = _make_state(
        cm,
        "them/peer",
        labels=["type:feature", "type:bug", "priority:High"],
        version="0.6.0",
        members=[{"github_login": "alice"}],
        milestones=["M1"],
    )
    drift = cm._compare(local, [peer], {"has_projects_v2_board": False})
    assert drift == []


def test_compare_detects_version_drift(cm) -> None:
    local = _make_state(cm, "us/local", version="0.6.0")
    peer = _make_state(cm, "them/peer", version="0.5.0")
    drift = cm._compare(local, [peer], {})
    kinds = [d["kind"] for d in drift]
    assert "capability-version" in kinds


def test_compare_detects_type_label_drift(cm) -> None:
    local = _make_state(
        cm, "us/local", labels=["type:feature", "type:bug"]
    )
    peer = _make_state(
        cm, "them/peer", labels=["type:feature", "type:bug", "type:incident"]
    )
    drift = cm._compare(local, [peer], {})
    type_drift = [d for d in drift if d["kind"] == "type-labels"]
    assert len(type_drift) == 1
    assert type_drift[0]["in_peer_only"] == ["type:incident"]


def test_compare_skips_priority_labels_for_board_adopter(cm) -> None:
    local = _make_state(cm, "us/local", labels=["priority:High"])
    peer = _make_state(cm, "them/peer", labels=["priority:High", "priority:Low"])
    drift = cm._compare(local, [peer], {"has_projects_v2_board": True})
    assert not any(d["kind"] == "priority-labels" for d in drift)


def test_compare_flags_priority_drift_for_label_adopter(cm) -> None:
    local = _make_state(cm, "us/local", labels=["priority:High"])
    peer = _make_state(cm, "them/peer", labels=["priority:High", "priority:Low"])
    drift = cm._compare(local, [peer], {"has_projects_v2_board": False})
    assert any(d["kind"] == "priority-labels" for d in drift)


def test_compare_detects_member_drift(cm) -> None:
    local = _make_state(
        cm, "us/local", members=[{"github_login": "alice"}]
    )
    peer = _make_state(
        cm,
        "them/peer",
        members=[{"github_login": "alice"}, {"github_login": "bob"}],
    )
    drift = cm._compare(local, [peer], {})
    member_drift = [d for d in drift if d["kind"] == "members"]
    assert len(member_drift) == 1
    assert "bob" in member_drift[0]["in_peer_only"]


def test_compare_skips_members_when_either_empty(cm) -> None:
    """When either side is open-mode (empty members), skip the check."""
    local = _make_state(cm, "us/local", members=[])
    peer = _make_state(cm, "them/peer", members=[{"github_login": "x"}])
    drift = cm._compare(local, [peer], {})
    assert not any(d["kind"] == "members" for d in drift)


def test_compare_detects_milestone_drift(cm) -> None:
    local = _make_state(cm, "us/local", milestones=["M1", "M2"])
    peer = _make_state(cm, "them/peer", milestones=["M1"])
    drift = cm._compare(local, [peer], {})
    ms_drift = [d for d in drift if d["kind"] == "milestones"]
    assert len(ms_drift) == 1
    assert "M2" in ms_drift[0]["in_local_only"]


def test_compare_multiple_peers_each_contributes(cm) -> None:
    local = _make_state(cm, "us/local", version="0.6.0")
    peer1 = _make_state(cm, "p1/r", version="0.5.0")
    peer2 = _make_state(cm, "p2/r", version="0.6.0")
    drift = cm._compare(local, [peer1, peer2], {})
    peers_in_drift = [d.get("peer") for d in drift if d["kind"] == "capability-version"]
    assert "p1/r" in peers_in_drift
    assert "p2/r" not in peers_in_drift


# --- summary ---------------------------------------------------------


def test_summary_zero_drift(cm) -> None:
    assert "clean" in cm._summary([])


def test_summary_with_drift_mentions_count_and_severity(cm) -> None:
    s = cm._summary([{"kind": "type-labels"}, {"kind": "capability-version"}])
    assert "2" in s
    assert "warning" in s.lower()


# --- _extract_version helper -----------------------------------------


def test_extract_version_from_yaml(cm) -> None:
    text = (
        "schema_version: 2\n"
        "component:\n"
        "  kind: capability\n"
        "  name: project-management\n"
        "  version: 0.7.0\n"
    )
    assert cm._extract_version(text) == "0.7.0"


def test_extract_version_returns_none_on_malformed(cm) -> None:
    assert cm._extract_version("garbage") is None
    assert cm._extract_version("") is None
