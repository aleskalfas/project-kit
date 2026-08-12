"""Adopter `config.yaml` schema — accept/reject shape + the COR-023 binding (#691).

The project-management capability's `project/config.yaml` is the one file
every adopter hand-edits at install time, and it was the only adopter-facing
file in the capability shipping no companion JSON Schema (#689). Every reader
gets at it through defensive `.get()`, so a misspelled key was silently
ignored: `has_projects_v2_boards` (trailing `s`) left the adopter in
label-fallback mode with no signal until classification landed in the wrong
substrate.

Two concerns here:

  1. **Schema shape** — the companion accepts a well-formed config (minimal,
     full-surface, and the two shipped real ones) and rejects the malformed
     shapes, with `additionalProperties: false` naming the offending key.

  2. **Binding** — the `binds_to:` glob resolves the *installed* adopter
     config to this schema (the `no schema binding found` symptom from #689),
     and, because `config.yaml` is a generic name, does NOT claim the other
     `config.yaml` files that live in an installed tree.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import data_validate as dv

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
CONFIG_COMPANION = CAPABILITY / "schemas" / "config.schema.json"
CONFIG_CARRIER = CAPABILITY / "schemas" / "config.yaml"
ADOPTER_CONFIG = CAPABILITY / "project" / "config.yaml"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(CONFIG_COMPANION.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _errors(validator: Draft202012Validator, doc: Any) -> list[str]:
    return [e.message for e in validator.iter_errors(doc)]


def _minimal() -> dict[str, Any]:
    """The smallest config the capability accepts — pre-check's required set."""
    return {"schema_version": 1, "default_branch": "main", "workstreams": []}


# --- accept ---------------------------------------------------------------


def test_reference_instance_validates(validator: Draft202012Validator) -> None:
    """The shipped binding carrier is a valid config — it is both the schema's
    self-test instance and the template an adopter copies."""
    data = YAML(typ="safe").load(CONFIG_CARRIER.read_text(encoding="utf-8"))
    assert _errors(validator, data) == []


def test_shipped_adopter_config_validates(validator: Draft202012Validator) -> None:
    """project-kit self-hosts, so its own `project/config.yaml` is a real
    adopter config. A key the loader accepts but the schema misses would
    surface here."""
    data = YAML(typ="safe").load(ADOPTER_CONFIG.read_text(encoding="utf-8"))
    assert _errors(validator, data) == []


def test_minimal_config_validates(validator: Draft202012Validator) -> None:
    assert _errors(validator, _minimal()) == []


def test_full_surface_config_validates(validator: Draft202012Validator) -> None:
    """Every documented key at once — the schema must cover the whole surface
    the capability's scripts read, not just the common ones."""
    doc = _minimal() | {
        "gh": {"host": "github.example.com", "default_owner": "some-org"},
        "has_projects_v2_board": True,
        "projects_v2_board_id": 12,
        "projects_v2_node_id": "PVT_kwDOABCD",
        "pre_close_triage_lead_days": 3,
        "code_path_to_doc_mapping": {
            "enforce": True,
            "rules": [{"code": "src/**", "docs": ["README.md"]}],
        },
        "milestone_categories": {
            "milestone": {
                "title_format": "Milestone {n}: {name}",
                "close_trigger_default": "content-based",
                "description": "Outcome bundle of related EPICs.",
            }
        },
        "review": {
            "mode": "agent",
            "human_review": {"reviewer_role": "PM"},
            "agents": {
                "remote_registered": [{"github_login": "claude-bot"}],
                "local_registered": [{"name": "reviewer"}, {"name": "code-review"}],
            },
        },
        "mesh_peers": ["github://owner/repo"],
        "mesh_source": "github://governance-owner/repo/path/to/mesh.yaml",
        "repo_owner": "aleskalfas",
        "repo_name": "project-kit",
    }
    assert _errors(validator, doc) == []


def test_legacy_workstreams_shapes_accepted(validator: Draft202012Validator) -> None:
    """Both historical shapes of the `workstreams:` shim stay valid — the bare
    v0.2.0 list and the v0.5.0 mapping form `create-issue` still reads."""
    as_list = _minimal() | {"workstreams": ["capabilities", "cli"]}
    as_mapping = _minimal() | {"workstreams": {"capabilities": {"status": "active"}}}
    assert _errors(validator, as_list) == []
    assert _errors(validator, as_mapping) == []


# --- reject: the reported typo ------------------------------------------


def test_trailing_s_typo_refused_and_names_the_key(
    validator: Draft202012Validator,
) -> None:
    """The #689 case: `has_projects_v2_boards` used to be silently ignored and
    degrade the adopter to label mode. It must now fail, and the message must
    name the offending key so the adopter can find it."""
    doc = _minimal() | {"has_projects_v2_boards": True}
    messages = _errors(validator, doc)
    assert messages, "a misspelled key must not validate"
    assert any("has_projects_v2_boards" in m for m in messages), messages


def test_unknown_top_level_key_refused(validator: Draft202012Validator) -> None:
    doc = _minimal() | {"defualt_branch": "main"}
    assert any("defualt_branch" in m for m in _errors(validator, doc))


def test_unknown_nested_key_refused(validator: Draft202012Validator) -> None:
    """Nested blocks are closed too — a typo inside `gh:` is as silent as one
    at the top level."""
    doc = _minimal() | {"gh": {"hosts": "github.com"}}
    assert any("hosts" in m for m in _errors(validator, doc))


# --- reject: missing required keys ---------------------------------------


@pytest.mark.parametrize("missing", ["schema_version", "default_branch", "workstreams"])
def test_missing_required_key_refused(validator: Draft202012Validator, missing: str) -> None:
    """The required set mirrors `pre-check.py`'s REQUIRED_ADOPTER_CONFIG_FIELDS,
    so shape validation and the pre-check gate agree on what a config must
    carry."""
    doc = _minimal()
    del doc[missing]
    assert any(missing in m for m in _errors(validator, doc))


def test_required_set_matches_pre_check() -> None:
    """Guard against the two drifting: pre-check names the required fields in
    Python, the schema names them in JSON.

    Parses the tuple rather than substring-matching the file: every one of
    these names also appears elsewhere in `pre-check.py` (the
    `workstreams.yaml` checks, the schema_version reads), so a containment
    check over the whole source is vacuous — it would stay green when the
    shim `workstreams` entry is dropped from the tuple, silently leaving the
    schema requiring a retired field. Set *equality* also catches the
    converse drift (a field added to pre-check, not to the schema).
    """
    pre_check = (CAPABILITY / "scripts" / "pre-check.py").read_text(encoding="utf-8")
    schema = json.loads(CONFIG_COMPANION.read_text(encoding="utf-8"))
    match = re.search(r"REQUIRED_ADOPTER_CONFIG_FIELDS\s*=\s*\(([^)]*)\)", pre_check)
    assert match is not None, "REQUIRED_ADOPTER_CONFIG_FIELDS not found in pre-check.py"
    gate_fields = set(re.findall(r'"([^"]+)"', match.group(1)))
    assert set(schema["required"]) == gate_fields, (
        f"schema required={sorted(schema['required'])} vs pre-check "
        f"REQUIRED_ADOPTER_CONFIG_FIELDS={sorted(gate_fields)} — the shape "
        f"companion and the gate must agree, or `pkit data validate` reports "
        f"green on a config pre-check refuses"
    )


# --- reject: value-level shapes the scripts enforce ----------------------


def test_board_id_must_be_a_number(validator: Draft202012Validator) -> None:
    """`projects_v2_board_id` is the board NUMBER from `gh project list`, not
    its node id — a `PVT_…` value here is the common confusion."""
    doc = _minimal() | {"projects_v2_board_id": "PVT_kwDOABCD"}
    assert _errors(validator, doc)


def test_review_mode_is_a_closed_set(validator: Draft202012Validator) -> None:
    doc = _minimal() | {"review": {"mode": "human-ish"}}
    assert _errors(validator, doc)


def test_doc_mapping_rule_needs_both_halves(validator: Draft202012Validator) -> None:
    """`check-doc-mapping` skips a rule missing `code` or `docs`, so a
    half-written rule is a rule that never fires — refuse it up front."""
    doc = _minimal() | {"code_path_to_doc_mapping": {"rules": [{"code": "src/**"}]}}
    assert _errors(validator, doc)


def test_milestone_category_needs_title_and_trigger(
    validator: Draft202012Validator,
) -> None:
    doc = _minimal() | {"milestone_categories": {"milestone": {"title_format": "M{n}: {name}"}}}
    assert _errors(validator, doc)


def test_milestone_close_trigger_is_a_closed_set(
    validator: Draft202012Validator,
) -> None:
    doc = _minimal() | {
        "milestone_categories": {
            "milestone": {"title_format": "M{n}: {name}", "close_trigger_default": "whenever"}
        }
    }
    assert _errors(validator, doc)


def test_mesh_peer_must_be_a_github_uri(validator: Draft202012Validator) -> None:
    """`check-mesh` exits with a usage error on any other form."""
    doc = _minimal() | {"mesh_peers": ["https://github.com/owner/repo"]}
    assert _errors(validator, doc)


# --- the COR-023 binding -------------------------------------------------


def test_installed_adopter_config_resolves_its_binding() -> None:
    """The #689 secondary symptom: `pkit data validate` on the adopter's config
    reported `no schema binding found`, making a correct config look
    mis-authored."""
    result = dv.resolve_binding(ADOPTER_CONFIG, REPO_ROOT)
    assert isinstance(result, dv.ResolvedBinding), getattr(result, "message", "")
    assert result.capability == "project-management"
    assert result.schema_name == "config"


def test_installed_adopter_config_validates_through_the_binding() -> None:
    issues = dv.validate_data_file(ADOPTER_CONFIG, REPO_ROOT)
    assert issues == [], [i.message for i in issues]


@pytest.mark.parametrize(
    "other_config",
    [
        Path(".pkit") / "project" / "config.yaml",
        Path(".pkit") / "permissions" / "project" / "config.yaml",
    ],
)
def test_glob_does_not_claim_unrelated_config_files(other_config: Path) -> None:
    """`config.yaml` is a generic name, so the glob is anchored at the installed
    path rather than the `**/config.yaml` form the sibling schemas use. A bare
    glob would claim these files (and any application config an adopter keeps)
    and turn correct files into loud validation failures."""
    path = REPO_ROOT / other_config
    assert path.is_file(), f"fixture drifted: {other_config} no longer exists"
    result = dv.resolve_binding(path, REPO_ROOT)
    assert isinstance(result, dv.BindingError)
