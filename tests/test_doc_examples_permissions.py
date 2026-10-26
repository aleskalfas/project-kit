"""No grant the methodology ships allows a call to the doc-examples run (#2098;
doc-examples DEC-001 point 9).

The run starts every command a page, the setup step and the placeholders hold, as
the caller and confined by nothing of its own. So it is a program started by its
path, never a command of the methodology's CLI, and nothing the methodology ships
allows a call to it:

- **The shipped grants:** under each shipped profile, with the guardrails and every
  capability's shipped grants fragment, no subject any of them names, nor the
  operator or an agent they do not name, is allowed a call to the run.
- **The core baseline:** no allow rule of the settings the Claude Code adapter
  merges into the harness matches a call to the run, read as widely as its
  wildcards allow.
- **The privilege of its own:** the capability's catalog fragment defines
  `doc-examples:run-examples`, which recognizes the run's call by its path from the
  repository's root, and nothing else; the capability ships no grant of it, and a
  project's grant of it allows the call.

The model is built from the shipped files, as `load_model` composes them, through
the decision core the hook and the CLI share.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
DECIDE = REPO / ".pkit" / "permissions" / "decide.py"
PROFILES = REPO / ".pkit" / "permissions" / "profiles"
CAPABILITIES = REPO / ".pkit" / "capabilities"
BASELINE = REPO / ".pkit" / "adapters" / "claude-code" / "settings" / "core" / "settings.json"
PRIVILEGE = "doc-examples:run-examples"
RUN = ".pkit/capabilities/doc-examples/scripts/run-examples.py"

CALLS = (
    RUN,
    f"./{RUN} --update",
    f"python3 {RUN} README.md",
    f"python {RUN} --timeout 5",
)


@pytest.fixture(scope="module")
def decide_mod() -> Any:
    spec = importlib.util.spec_from_file_location("doc_examples_decide_under_test", DECIDE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def catalog(decide_mod: Any) -> dict[str, Any]:
    return decide_mod.load_catalog(str(REPO))


def _bash(command: str, subject: str) -> dict[str, str]:
    return {"type": "bash", "command": command, "cwd": str(REPO), "subject": subject}


def _shipped_fragments(decide_mod: Any) -> list[dict[str, Any]]:
    return [
        grant
        for fragment in sorted(CAPABILITIES.glob("*/permissions/grants.yaml"))
        for grant in decide_mod.load_yaml(str(fragment)).get("grants", []) or []
    ]


def _model(decide_mod: Any, catalog: dict[str, Any], profile: Path) -> dict[str, Any]:
    shipped = decide_mod.load_yaml(str(profile))
    return {
        "posture": shipped.get("posture", "lenient"),
        "grants": [
            *decide_mod.guardrail_denies(catalog),
            *_shipped_fragments(decide_mod),
            *(shipped.get("grants") or []),
        ],
    }


@pytest.mark.parametrize("profile", sorted(PROFILES.glob("*.yaml")), ids=lambda path: path.stem)
def test_no_shipped_profile_or_fragment_allows_a_call_to_the_run(
    decide_mod: Any, catalog: dict[str, Any], profile: Path
) -> None:
    model = _model(decide_mod, catalog, profile)
    subjects = {grant["subject"] for grant in model["grants"]} | {"operator", "agent:any"}

    allowed = [
        (subject, command)
        for subject in [*sorted(subjects - {"all"}), "all"]
        for command in CALLS
        if decide_mod.decide(model, catalog, _bash(command, subject))[0] == "allow"
    ]

    assert allowed == []


def _baseline_allows(rule: str, command: str) -> bool:
    """Whether a `Bash(...)` allow rule of the harness's settings matches `command`,
    read as widely as its wildcards allow: `:*` as any words after, and `*` as any
    text."""
    found = re.fullmatch(r"Bash\((.*)\)", rule)
    if found is None:
        return False
    body = found.group(1)
    if body.endswith(":*"):
        prefix = body[:-2]
        return command == prefix or command.startswith(prefix + " ")
    pattern = ".*".join(re.escape(part) for part in re.split(r"\*+", body))
    return (
        re.fullmatch(pattern, command) is not None
        or re.match(pattern + r"(\s|$)", command) is not None
    )


def test_no_allow_rule_of_the_core_baseline_matches_a_call_to_the_run() -> None:
    allow = json.loads(BASELINE.read_text(encoding="utf-8"))["permissions"]["allow"]

    matched = [(rule, call) for rule in allow for call in CALLS if _baseline_allows(rule, call)]

    assert matched == []
    # The matcher reads a rule as the harness does at its widest: it does match a
    # call the baseline means to allow.
    assert _baseline_allows("Bash(.pkit/**/*.sh)", ".pkit/adapters/claude-code/deploy-skills.sh")
    assert _baseline_allows("Bash(pkit:*)", "pkit doc-examples pages --json")


def test_the_run_has_a_privilege_of_its_own_that_no_shipped_grant_references(
    decide_mod: Any, catalog: dict[str, Any]
) -> None:
    assert not (CAPABILITIES / "doc-examples" / "permissions" / "grants.yaml").exists()
    for call in CALLS:
        assert PRIVILEGE in decide_mod.recognized_privileges(catalog, _bash(call, "operator"))
    for other in (
        f"/elsewhere/{RUN}",
        f"{RUN}.bak",
        f"uv run python {RUN}",
        f"sh -c '{RUN}'",
        "pkit doc-examples pages --json",
    ):
        assert PRIVILEGE not in decide_mod.recognized_privileges(
            catalog, _bash(other, "operator")
        ), other
    shipped = [
        grant
        for path in (
            *sorted(PROFILES.glob("*.yaml")),
            *sorted(CAPABILITIES.glob("*/permissions/grants.yaml")),
        )
        for grant in decide_mod.load_yaml(str(path)).get("grants", []) or []
    ]
    assert not any(PRIVILEGE in decide_mod._privilege_ids(grant["privilege"]) for grant in shipped)


def test_a_project_s_grant_of_the_privilege_allows_the_call(
    decide_mod: Any, catalog: dict[str, Any]
) -> None:
    model = {
        "posture": "lenient",
        "grants": [
            *decide_mod.guardrail_denies(catalog),
            {
                "subject": "agent:docs",
                "privilege": f"[privilege-catalog:{PRIVILEGE}]",
                "effect": "allow",
            },
        ],
    }

    assert decide_mod.decide(model, catalog, _bash(CALLS[2], "agent:docs"))[0] == "allow"
    assert decide_mod.decide(model, catalog, _bash(CALLS[2], "agent:other"))[0] != "allow"
