"""Tests for `start-work` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "start-work.py"
)


@pytest.fixture(scope="module")
def sw():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_start_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_start_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _slug_from_title --------------------------------------------------


def test_slug_strips_type_prefix(sw) -> None:
    assert sw._slug_from_title("[Feature] add gh helper") == "add-gh-helper"


def test_slug_strips_punctuation(sw) -> None:
    assert sw._slug_from_title("[Bug] fix: hostname mismatch!") == "fix-hostname-mismatch"


def test_slug_caps_at_five_words(sw) -> None:
    assert sw._slug_from_title(
        "[Feature] one two three four five six seven"
    ) == "one-two-three-four-five"


def test_slug_handles_empty_after_prefix(sw) -> None:
    assert sw._slug_from_title("[EPIC]") == "untitled"


def test_slug_lowercases(sw) -> None:
    assert sw._slug_from_title("[Task] MIXED Case Title") == "mixed-case-title"


# ---- _derive_branch_prefix ---------------------------------------------
#
# The prefix now resolves the kit type *value* through the ADR-026 read seam
# (a `type:*` label OR a `[Prefix]` title) and maps it via classification.yaml's
# `pr_type_mapping`. The greenfield (label) arm below must stay byte-identical to
# the pre-fix behaviour; the brownfield (title-prefix) arm is the new coverage.

# A minimal classification carrying the two tables the derivation reads: the
# value→conv-type bridge (`pr_type_mapping`) and the title-prefix vocabulary
# (`title_prefix_by_value`). Mirrors the shipped classification.yaml.
_CLASSIFICATION = {
    "axes": {
        "type": {
            "title_prefix_by_value": {
                "feature": "Task",
                "bug": "Bug",
                "docs": "Docs",
                "test": "Test",
                "refactor": "Refactor",
                "maintenance": "Chore",
            },
        },
    },
    "pr_type_mapping": [
        {"issue_label_value": "feature", "pr_conv_type": "feat"},
        {"issue_label_value": "bug", "pr_conv_type": "fix"},
        {"issue_label_value": "docs", "pr_conv_type": "docs"},
        {"issue_label_value": "test", "pr_conv_type": "test"},
        {"issue_label_value": "refactor", "pr_conv_type": "refactor"},
        {"issue_label_value": "maintenance", "pr_conv_type": "chore"},
    ],
}


def test_branch_prefix_feature(sw) -> None:
    assert sw._derive_branch_prefix(
        ["type:feature", "priority:Medium"], "[Task] add x", _CLASSIFICATION, None
    ) == "feat"


def test_branch_prefix_bug(sw) -> None:
    assert sw._derive_branch_prefix(["type:bug"], "[Bug] fix x", _CLASSIFICATION, None) == "fix"


def test_branch_prefix_docs(sw) -> None:
    assert sw._derive_branch_prefix(
        ["workstream:cli", "type:docs"], "[Docs] doc x", _CLASSIFICATION, None
    ) == "docs"


def test_branch_prefix_missing_returns_none(sw) -> None:
    # No type:* label AND no recognised [Prefix] title ⇒ underivable.
    assert sw._derive_branch_prefix(["priority:High"], "no bracket prefix", _CLASSIFICATION, None) is None
    assert sw._derive_branch_prefix([], "", _CLASSIFICATION, None) is None


def test_branch_prefix_picks_first_match(sw) -> None:
    """Defensive: if labels somehow have both type:bug and type:feature, take the first."""
    result = sw._derive_branch_prefix(
        ["type:bug", "type:feature"], "[Bug] x", _CLASSIFICATION, None
    )
    # Order-dependent — accept either as long as it's recognised
    assert result in ("fix", "feat")


# ---- brownfield title-prefix arm (Task #442) ---------------------------


def test_branch_prefix_brownfield_bug_title_no_label(sw) -> None:
    """A brownfield `[Bug]`-titled Task with NO type:* label resolves `fix` —
    the read routes through the title-prefix arm of the seam, not a raw label."""
    assert sw._derive_branch_prefix([], "[Bug] hostname mismatch", _CLASSIFICATION, None) == "fix"


def test_branch_prefix_greenfield_label_still_wins(sw) -> None:
    """Greenfield stays byte-identical: `type:bug` label resolves `fix` even
    when the title carries a different (or no) bracket prefix."""
    assert sw._derive_branch_prefix(
        ["type:bug"], "no bracket prefix at all", _CLASSIFICATION, None
    ) == "fix"


# ---- adopter label-remap arm (#910) ------------------------------------


def _type_remap_map(module):
    """A substrate map binding `type` to the adopter's own `kind/*` labels."""
    return module.axis_labels.SubstrateMap(
        axes={"type": {"label": {"remap": {"bug": "kind/bug", "docs": "kind/docs"}}}}
    )


def test_branch_prefix_reads_a_remapped_type_label(sw) -> None:
    """The adopter's `kind/bug` label is their type substrate: it resolves `fix`
    through the map, where the bare `type:` prefix scan found nothing (#910)."""
    assert sw._derive_branch_prefix(
        ["kind/bug"], "no bracket prefix", _CLASSIFICATION, _type_remap_map(sw)
    ) == "fix"


def test_branch_prefix_ignores_kit_type_label_under_a_remap(sw) -> None:
    """Under a `type` label remap the kit's `type:*` labels are not the
    substrate, so a leftover `type:docs` does not decide the prefix."""
    assert sw._derive_branch_prefix(
        ["type:docs", "kind/bug"], "no bracket prefix", _CLASSIFICATION,
        _type_remap_map(sw),
    ) == "fix"


# ---- _branch_matches_shape --------------------------------------------


def test_branch_matches_shape_valid(sw) -> None:
    assert sw._branch_matches_shape("feat/42-add-gh-helper", 42) is True
    assert sw._branch_matches_shape("fix/177-membership-hostname", 177) is True
    assert sw._branch_matches_shape("docs/29-branch-naming", 29) is True


def test_branch_matches_shape_wrong_number(sw) -> None:
    assert sw._branch_matches_shape("feat/42-foo", 99) is False


def test_branch_matches_shape_no_slug(sw) -> None:
    assert sw._branch_matches_shape("feat/42", 42) is False


def test_branch_matches_shape_uppercase_rejected(sw) -> None:
    assert sw._branch_matches_shape("Feat/42-foo", 42) is False


# ---- type coverage against the REAL shipped classification.yaml -------


def test_every_shipped_type_value_resolves_a_branch_prefix(sw) -> None:
    """Every kind in the real classification.yaml (both label and title arms)
    resolves a branch prefix — no shipped type value is left underivable.

    Reads the shipped schema rather than a fixture so the two tables the
    derivation depends on (`pr_type_mapping`, `title_prefix_by_value`) can't
    drift out of coverage silently."""
    import importlib.util as _ilu

    scripts = SCRIPT.parent
    spec = _ilu.spec_from_file_location(
        "pm_classification_rules_under_test", scripts / "_lib" / "classification_rules.py"
    )
    assert spec is not None and spec.loader is not None
    cr = _ilu.module_from_spec(spec)
    spec.loader.exec_module(cr)

    from ruamel.yaml import YAML

    classification = YAML(typ="safe").load(
        (scripts.parent / "schemas" / "classification.yaml").read_text(encoding="utf-8")
    )
    prefix_by_value = cr.title_prefix_by_value(classification)
    assert prefix_by_value, "shipped classification.yaml carries no title_prefix_by_value"

    for value, title_prefix in prefix_by_value.items():
        # Label arm: a greenfield type:<value> label resolves a prefix.
        via_label = sw._derive_branch_prefix(
            [f"type:{value}"], f"[{title_prefix}] x", classification, None
        )
        assert via_label is not None, f"no branch prefix for label type:{value}"
        # Title arm: the same value resolves identically off the [Prefix] title
        # with no type:* label present (the brownfield path).
        via_title = sw._derive_branch_prefix([], f"[{title_prefix}] x", classification, None)
        assert via_title == via_label, (
            f"label vs title-prefix arm disagree for kind {value!r}: "
            f"{via_label!r} vs {via_title!r}"
        )


# ---- resolve_base_branch (#835, #903) ----------------------------------
#
# The shared resolver in `_lib/lifecycle_inference`; start-work and the
# PR-opening verbs all call it. End-to-end wiring per verb lives in
# test_pm_pr_base_branch.py.


def test_base_defaults_to_config_default_branch(sw) -> None:
    assert sw.infer.resolve_base_branch({"default_branch": "trunk"}, "EPIC: #1\n\n## What\nx") == "trunk"


def test_base_defaults_to_main_when_unconfigured(sw) -> None:
    assert sw.infer.resolve_base_branch({}, "EPIC: #1\n\n## What\nx") == "main"


def test_base_is_integration_branch_when_marked(sw) -> None:
    body = "Integration: integration/508-multi-instance-ownership\nFeature: #510\n\n## What\nx"
    assert sw.infer.resolve_base_branch({"default_branch": "main"}, body) == (
        "integration/508-multi-instance-ownership"
    )


def test_base_ignores_a_malformed_marker(sw) -> None:
    # A malformed marker is not a valid integration branch — fall back to default.
    body = "Integration: integration/Bad_Slug!!\nFeature: #510\n\n## What\nx"
    assert sw.infer.resolve_base_branch({"default_branch": "main"}, body) == "main"


def test_explicit_base_wins_over_marker_and_default(sw) -> None:
    body = "Integration: integration/508-multi-instance-ownership\nFeature: #510\n"
    assert sw.infer.resolve_base_branch(
        {"default_branch": "trunk"}, body, explicit="release/2"
    ) == "release/2"


def test_base_never_reflects_the_checked_out_branch(sw) -> None:
    # The resolver takes only (config, body, explicit) — there is no HEAD input,
    # so the currently-checked-out branch can never leak into the base (#835).
    import inspect

    sig = inspect.signature(sw.infer.resolve_base_branch)
    assert list(sig.parameters) == ["config", "body", "explicit"]


# ---- transition gate + late failure (#942) -----------------------------
#
# Drive the real `main()` with its gates and gh/git seams stubbed, against the
# shipped workflow.yaml / issue-types.yaml, and record every mutation.

CAP_ROOT = SCRIPT.parent.parent


def _task(labels: list[str], *, assignees: list[dict] | None = None) -> dict:
    return {
        "title": "[Task] do the thing",
        "labels": labels,
        "assignees": assignees or [],
        "state": "OPEN",
        "body": "Feature: #1\n\n## What\nx",
        "milestone": None,
    }


@pytest.fixture
def run_main(sw, monkeypatch):
    """Returns `run(issue, move_rc=0) -> (rc, mutations)` over stubbed seams."""
    from types import SimpleNamespace

    def run(issue: dict, move_rc: int = 0):
        mutations: list[tuple] = []
        monkeypatch.setattr(sys, "argv", ["start-work", "42", "--yes"])
        monkeypatch.setattr(sw, "resolve_capability_root", lambda _e: CAP_ROOT)
        monkeypatch.setattr(sw.bootstrap_gate, "enforce", lambda *a, **k: True)
        monkeypatch.setattr(sw.session_guard, "enforce", lambda **k: True)
        monkeypatch.setattr(sw, "load_adopter_config", lambda _r: {"default_branch": "main"})
        monkeypatch.setattr(sw, "_read_members", lambda *a: [])
        monkeypatch.setattr(
            sw, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
        )
        monkeypatch.setattr(sw, "check_membership", lambda *a: SimpleNamespace(allowed=True))
        monkeypatch.setattr(sw.axis_labels, "load_substrate_map", lambda _r: None)
        monkeypatch.setattr(sw, "_gh_get_issue", lambda _n, _c: issue)
        monkeypatch.setattr(sw, "_existing_branch_for_issue", lambda _n: None)

        def create_branch(name, base):
            mutations.append(("branch", name))
            return True

        def set_assignee(n, login, config):
            mutations.append(("assignee", login))
            return True

        def move_issue(n, target, root, allow):
            mutations.append(("move", target))
            return move_rc

        monkeypatch.setattr(sw, "_create_branch", create_branch)
        monkeypatch.setattr(sw, "_set_assignee", set_assignee)
        monkeypatch.setattr(sw, "_invoke_move_issue", move_issue)
        return sw.main(), mutations

    return run


def test_refuses_from_todo_before_any_mutation(run_main, capsys) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:todo"]))
    assert rc == 2
    assert mutations == []  # no branch, no assignee, no move
    err = capsys.readouterr().err
    assert "'todo'" in err
    assert "move-issue 42 --to backlog" in err


def test_refuses_from_todo_inferred_without_a_state_label(run_main, capsys) -> None:
    # No state:* label and no milestone resolves Todo through the shared reader.
    rc, mutations = run_main(_task(["type:bug"]))
    assert rc == 2
    assert mutations == []
    assert "move-issue 42 --to backlog" in capsys.readouterr().err


def test_proceeds_from_backlog(run_main) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]))
    assert rc == 0
    assert mutations == [
        ("branch", "fix/42-do-the-thing"), ("assignee", "me"), ("move", "in-progress"),
    ]


def test_proceeds_when_already_in_progress(run_main) -> None:
    # move-issue treats in-progress → in-progress as an idempotent no-op.
    rc, mutations = run_main(_task(["type:bug", "state:in-progress"]))
    assert rc == 0
    assert ("move", "in-progress") in mutations


def test_refusal_without_a_stepping_stone_lists_legal_targets(run_main, capsys) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:review"]))
    assert rc == 2
    assert mutations == []
    assert "legal targets from 'review'" in capsys.readouterr().err


def test_late_move_failure_names_branch_and_assignee(run_main, capsys) -> None:
    rc, mutations = run_main(_task(["type:bug", "state:backlog"]), move_rc=3)
    assert rc == 3  # move-issue's exit code passes through
    assert [m[0] for m in mutations] == ["branch", "assignee", "move"]
    err = capsys.readouterr().err
    last_block = err[err.rindex("[failed]"):]
    assert "the issue did not move" in last_block
    assert "fix/42-do-the-thing" in last_block
    assert "@me" in last_block


def test_late_move_failure_omits_an_assignee_it_did_not_write(run_main, capsys) -> None:
    issue = _task(["type:bug", "state:backlog"], assignees=[{"login": "me"}])
    rc, mutations = run_main(issue, move_rc=3)
    assert rc == 3
    assert ("assignee", "me") not in mutations
    err = capsys.readouterr().err
    assert "fix/42-do-the-thing" in err
    assert "@me" not in err
