"""Tests for project-management's `_lib/title_rules` — the one reader of titles.yaml's checks.

Two halves. The unit half drives `check_title` with small fixtures: each check
kind, the `text` group, the transition cap, and the refusal to pass a declared
check nothing can run. The shipped half reads the real `titles.yaml`: every
validation names a runnable check, every good example is clean, every bad
example is caught, and the companion JSON Schema refuses a validation with no
`check` — so a rule cannot sit in the schema unenforced again (#803).
"""

from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from project_kit.schemas_validate import SchemaPair, validate_pair

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAP_ROOT / "scripts"
TITLES_PATH = CAP_ROOT / "schemas" / "titles.yaml"
TITLES_SCHEMA_PATH = CAP_ROOT / "schemas" / "titles.schema.json"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _lib import title_rules  # noqa: E402

HARD = "[validation-severity:hard-reject]"
WARN = "[validation-severity:warning]"

# The bad example whose fault is visible only with the issue's kind label; the
# kind-prefix check that catches it runs in validate-issue (tested there).
_NEEDS_KIND_LABEL = {"[Task] Fix the auth bug in the login flow"}


@pytest.fixture(scope="module")
def shipped_titles() -> dict:
    return YAML(typ="safe").load(TITLES_PATH.read_text(encoding="utf-8"))


def _titles(*validations: dict, pattern: str | None = r"^\[Task\] (?P<text>.+)$") -> dict:
    return {"formats": {"issue-task": {"pattern": pattern, "validations": list(validations)}}}


def _labels(findings) -> list[str]:
    return [label for _severity, label, _detail in findings]


# --- lookups ----------------------------------------------------------


def test_pattern_for_returns_the_entry_regex() -> None:
    titles = {"formats": {"issue-task": {"pattern": r"^\[Task\] .+$"}}}
    assert title_rules.pattern_for(titles, title_rules.issue_key("task")) == r"^\[Task\] .+$"


def test_pattern_for_is_none_for_an_unknown_key_or_empty_schema() -> None:
    assert (
        title_rules.pattern_for({"formats": {"issue-task": {"pattern": "x"}}}, "issue-epic") is None
    )
    assert title_rules.pattern_for({}, "issue-task") is None


def test_pattern_for_is_none_for_a_free_form_surface() -> None:
    assert (
        title_rules.pattern_for({"formats": {"milestone": {"pattern": None}}}, "milestone") is None
    )


def test_declared_severity_reads_the_check_and_defaults() -> None:
    entry = {"validations": [{"check": "kind-prefix", "severity": WARN}]}
    assert title_rules.declared_severity(entry, "kind-prefix", "hard-reject") == "warning"
    assert title_rules.declared_severity(entry, "type-alignment", "hard-reject") == "hard-reject"


# --- the pattern check --------------------------------------------------


def test_no_entry_means_no_findings() -> None:
    assert title_rules.check_title({}, "issue-task", "anything") == []


def test_pattern_miss_without_a_declared_validation_hard_rejects() -> None:
    """An entry with only a pattern keeps its regex gate (the pre-#803 behaviour)."""
    titles = {"formats": {"issue-task": {"pattern": r"^\[Task\] .+$"}}}
    [(severity, label, _detail)] = title_rules.check_title(titles, "issue-task", "Task x")
    assert (severity, label) == ("hard-reject", "title.pattern")


def test_pattern_miss_uses_the_declared_severity_and_name() -> None:
    titles = _titles({"rule": "Prefix.", "check": "pattern", "name": "title.p", "severity": WARN})
    assert title_rules.check_title(titles, "issue-task", "nope")[0][:2] == ("warning", "title.p")


def test_pattern_miss_is_reported_alone() -> None:
    """The text checks read the text the pattern delimits; with no match there is none."""
    titles = _titles(
        {"rule": "R.", "check": "min-length", "length": 99, "name": "title.short", "severity": WARN}
    )
    assert _labels(title_rules.check_title(titles, "issue-task", "no prefix")) == ["title.pattern"]


# --- the text checks ----------------------------------------------------


def test_forbid_reads_the_text_after_the_prefix() -> None:
    titles = _titles(
        {"rule": "No x:.", "check": "forbid", "regex": "^x:", "name": "title.x", "severity": HARD}
    )
    assert _labels(title_rules.check_title(titles, "issue-task", "[Task] x: thing")) == ["title.x"]
    assert title_rules.check_title(titles, "issue-task", "[Task] thing x: later") == []


def test_forbid_reads_the_whole_title_without_a_text_group() -> None:
    titles = _titles(
        {"rule": "No x:.", "check": "forbid", "regex": "^x:", "name": "title.x", "severity": HARD},
        pattern=None,
    )
    assert _labels(title_rules.check_title(titles, "issue-task", "x: thing")) == ["title.x"]


def test_require_reports_a_missing_match() -> None:
    titles = _titles(
        {
            "rule": "Word.",
            "check": "require",
            "regex": "[a-z]{2,}",
            "name": "title.w",
            "severity": WARN,
        }
    )
    assert _labels(title_rules.check_title(titles, "issue-task", "[Task] 1 2")) == ["title.w"]
    assert title_rules.check_title(titles, "issue-task", "[Task] ok") == []


def test_min_and_max_length_bound_the_text() -> None:
    titles = _titles(
        {"rule": "Min.", "check": "min-length", "length": 5, "name": "title.min", "severity": WARN},
        {"rule": "Max.", "check": "max-length", "length": 8, "name": "title.max", "severity": WARN},
    )
    assert _labels(title_rules.check_title(titles, "issue-task", "[Task] abcd")) == ["title.min"]
    assert _labels(title_rules.check_title(titles, "issue-task", "[Task] abcdefghi")) == [
        "title.max"
    ]
    assert title_rules.check_title(titles, "issue-task", "[Task] abcdef") == []


def test_finding_carries_the_declared_severity_and_rule() -> None:
    titles = _titles(
        {"rule": "No x:.", "check": "forbid", "regex": "^x:", "name": "title.x", "severity": HARD}
    )
    [(severity, label, detail)] = title_rules.check_title(titles, "issue-task", "[Task] x: y")
    assert (severity, label) == ("hard-reject", "title.x")
    assert detail.startswith("No x:") and "'x:'" in detail


def test_context_checks_are_left_to_their_callers() -> None:
    titles = _titles(
        {"rule": "Kind.", "check": "kind-prefix", "name": "title.kind", "severity": HARD},
    )
    assert title_rules.check_title(titles, "issue-task", "[Task] anything at all") == []


# --- the transition cap -------------------------------------------------


def test_at_transition_a_blocking_text_check_reports_as_warning() -> None:
    titles = _titles(
        {"rule": "No x:.", "check": "forbid", "regex": "^x:", "name": "title.x", "severity": HARD}
    )
    [(severity, _label, _detail)] = title_rules.check_title(
        titles, "issue-task", "[Task] x: y", at_transition=True
    )
    assert severity == "warning"


def test_at_transition_the_pattern_still_refuses() -> None:
    titles = {"formats": {"issue-task": {"pattern": r"^\[Task\] .+$"}}}
    [(severity, _label, _detail)] = title_rules.check_title(
        titles, "issue-task", "no prefix", at_transition=True
    )
    assert severity == "hard-reject"


# --- a declared check nothing can run is an error, not a pass ------------


@pytest.mark.parametrize(
    "validation",
    [
        {"rule": "R.", "severity": HARD},
        {"rule": "R.", "check": "spelling", "name": "title.s", "severity": HARD},
        {"rule": "R.", "check": "forbid", "name": "title.f", "severity": HARD},
        {"rule": "R.", "check": "forbid", "regex": "(", "name": "title.f", "severity": HARD},
        {"rule": "R.", "check": "min-length", "name": "title.m", "severity": WARN},
        {"rule": "R.", "check": "max-length", "length": 0, "name": "title.m", "severity": WARN},
    ],
)
def test_an_unrunnable_validation_raises(validation: dict) -> None:
    with pytest.raises(ValueError, match=r"titles\.yaml formats\.issue-task"):
        title_rules.check_title(_titles(validation), "issue-task", "[Task] anything")


# --- the shipped titles.yaml --------------------------------------------


def test_every_shipped_validation_names_a_runnable_check(shipped_titles) -> None:
    for key, entry in shipped_titles["formats"].items():
        for item in entry["validations"]:
            assert item.get("check") in title_rules.CHECKS, (key, item["rule"])
            title_rules._require_runnable(key, item)


def test_every_shipped_good_example_is_clean(shipped_titles) -> None:
    for key, entry in shipped_titles["formats"].items():
        for title in entry["examples_good"]:
            assert title_rules.check_title(shipped_titles, key, title) == [], (key, title)


def test_every_shipped_bad_example_is_caught(shipped_titles) -> None:
    """Each bad example trips a check; the one needing a kind label is exempt here."""
    uncaught = {
        bad["title"]
        for key, entry in shipped_titles["formats"].items()
        for bad in entry.get("examples_bad") or []
        if not title_rules.check_title(shipped_titles, key, bad["title"])
    }
    assert uncaught == _NEEDS_KIND_LABEL


_CC = ("hard-reject", "title.conventional-commits-prefix")
_SCOPE = ("warning", "title.scope-prefix")


@pytest.mark.parametrize(
    ("key", "title", "finding"),
    [
        ("issue-epic", "[EPIC] feat(ownership): multi-instance coordination", _CC),
        ("issue-task", "[Task] fix: the crash when a parent issue has no body", _CC),
        ("issue-task", "[Bug] Fix: the crash when a parent issue has no body", _CC),
        ("issue-feature", "[Feature] instances: identity and ownership lifecycle", _SCOPE),
        ("issue-umbrella", "[Umbrella] cli: polish round for the walkthrough", _SCOPE),
        ("issue-task", "[Bug] Crash on start", ("warning", "title.short")),
        ("milestone", "M1", ("warning", "title.numeric-only")),
        ("pr", "feat(pm): Refuse the title.", ("warning", "title.summary-style")),
        ("pr", "fix(pm): " + "x" * 73, ("warning", "title.summary-length")),
    ],
)
def test_shipped_rule_fires(shipped_titles, key, title, finding) -> None:
    assert finding in [f[:2] for f in title_rules.check_title(shipped_titles, key, title)]


# --- the length rules ---------------------------------------------------


@pytest.mark.parametrize(
    ("key", "title"),
    [
        ("issue-epic", "[EPIC] Code review discipline"),
        ("issue-epic", "[EPIC] CLI capability"),
        ("issue-feature", "[Feature] Named per-user instances"),
        ("issue-umbrella", "[Umbrella] Walkthrough fixes"),
    ],
)
def test_a_short_territory_title_does_not_warn(shipped_titles, key, title) -> None:
    """EPIC, Feature and Umbrella name a territory, which is short by nature."""
    assert title_rules.check_title(shipped_titles, key, title) == []


@pytest.mark.parametrize("prefix", ["Task", "Bug", "Docs", "Test", "Refactor", "Chore"])
def test_a_short_work_title_warns_under_every_kind_prefix(shipped_titles, prefix) -> None:
    found = title_rules.check_title(shipped_titles, "issue-task", f"[{prefix}] Fix the parser")
    assert [f[:2] for f in found] == [("warning", "title.short")]


def test_only_task_titles_carry_a_length_floor(shipped_titles) -> None:
    floored = {
        key
        for key, entry in shipped_titles["formats"].items()
        if any(v["check"] == "min-length" for v in entry["validations"])
    }
    assert floored == {"issue-task"}


def test_a_pr_summary_of_60_characters_does_not_warn(shipped_titles) -> None:
    title = "fix(pm): " + "x" * 60
    assert title_rules.check_title(shipped_titles, "pr", title) == []


def test_a_pr_summary_of_80_characters_warns(shipped_titles) -> None:
    found = title_rules.check_title(shipped_titles, "pr", "fix(pm): " + "x" * 80)
    assert [f[:2] for f in found] == [("warning", "title.summary-length")]


def test_a_pr_summary_of_72_characters_is_the_edge(shipped_titles) -> None:
    assert title_rules.check_title(shipped_titles, "pr", "fix(pm): " + "x" * 72) == []
    assert title_rules.check_title(shipped_titles, "pr", "fix(pm): " + "x" * 73) != []


@pytest.mark.parametrize(
    "title",
    [
        "[Task] feat: support a prompt file for the gateway",
        "[Task] ci(release): pin the runner image",
    ],
)
def test_a_commit_type_prefix_draws_one_finding_not_two(shipped_titles, title) -> None:
    """The `scope:` rule skips a commit type, which the refusing rule already names."""
    assert _labels(title_rules.check_title(shipped_titles, "issue-task", title)) == [
        "title.conventional-commits-prefix"
    ]


@pytest.mark.parametrize(
    ("key", "title"),
    [
        ("issue-task", "[Bug] project-management: the review gate is unsatisfiable (mockingbird)"),
        ("issue-epic", "[EPIC] project-management: validator correctness and robustness"),
    ],
)
def test_a_component_scoped_title_warns_and_does_not_refuse(shipped_titles, key, title) -> None:
    """A bare lowercase `scope:` is a warning: reports and component titles carry it."""
    found = title_rules.check_title(shipped_titles, key, title)
    assert [f[:2] for f in found] == [_SCOPE]


def test_a_scoped_lowercase_token_is_a_scope_prefix(shipped_titles) -> None:
    found = title_rules.check_title(
        shipped_titles, "issue-task", "[Task] sandbox(cli): support a prompt file"
    )
    assert [f[:2] for f in found] == [("warning", "title.scope-prefix")]


def test_a_lowercase_token_starting_with_a_commit_type_is_still_a_scope_prefix(
    shipped_titles,
) -> None:
    found = title_rules.check_title(
        shipped_titles, "issue-task", "[Task] ci-runner: pin the image the release job uses"
    )
    assert [f[:2] for f in found] == [("warning", "title.scope-prefix")]


@pytest.mark.parametrize(
    "title",
    [
        "[EPIC] Permission model: model first-class harness tools in the catalog",
        "[EPIC] Capabilities-framework hardening: external-system dependency declaration",
        "[EPIC] Parallelization: primitive promotion and deterministic routing",
        "[EPIC] CI pipeline hardening for the release workflow and its checks",
    ],
)
def test_a_colon_after_a_territory_named_in_words_is_clean(shipped_titles, title) -> None:
    assert title_rules.check_title(shipped_titles, "issue-epic", title) == []


@pytest.mark.parametrize(
    ("key", "title"),
    [
        ("issue-epic", "[EPIC] PR review fidelity — native review state + pre-post preview"),
        ("issue-feature", "[Feature] Process substrate - open-region slot"),
        ("issue-task", "[Bug] close-issue journals each close it makes — once, not twice"),
    ],
)
def test_a_dash_and_a_short_specifier_are_clean(shipped_titles, key, title) -> None:
    assert title_rules.check_title(shipped_titles, key, title) == []


def _schema_messages(titles: dict, tmp_path: Path) -> list[str]:
    """Validate ``titles`` against the shipped companion, beside copies of its siblings."""
    for companion in TITLES_SCHEMA_PATH.parent.glob("*.schema.json"):
        shutil.copy(companion, tmp_path / companion.name)
    yaml_path = tmp_path / "titles.yaml"
    with yaml_path.open("w", encoding="utf-8") as fh:
        YAML().dump(titles, fh)
    pair = SchemaPair(yaml_path, tmp_path / TITLES_SCHEMA_PATH.name)
    return [issue.message for issue in validate_pair(pair, REPO_ROOT, resolve=False)]


def test_the_shipped_titles_pass_the_schema(shipped_titles, tmp_path) -> None:
    assert _schema_messages(shipped_titles, tmp_path) == []


def test_the_schema_refuses_a_validation_without_a_check(shipped_titles, tmp_path) -> None:
    broken = copy.deepcopy(shipped_titles)
    del broken["formats"]["issue-epic"]["validations"][1]["check"]

    messages = _schema_messages(broken, tmp_path)

    assert any("'check' is a required property" in message for message in messages), messages


def test_the_schema_refuses_a_length_check_without_a_length(shipped_titles, tmp_path) -> None:
    broken = copy.deepcopy(shipped_titles)
    shorts = [
        v for v in broken["formats"]["issue-task"]["validations"] if v["check"] == "min-length"
    ]
    del shorts[0]["length"]

    messages = _schema_messages(broken, tmp_path)

    assert any("'length' is a required property" in message for message in messages), messages
