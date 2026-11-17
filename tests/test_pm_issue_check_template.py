"""The post-check workflow template's credential for the board ([pkit:ADR-096], Implications).

The workflow's own token reaches no Projects v2 board, so the template gains a
setting for a credential the board answers, unset as it ships: a person's token
(`PM_BOARD_TOKEN`) or a GitHub App's (`PM_BOARD_APP_ID`, `PM_BOARD_APP_KEY`).
Only the steps that read or add on the board hold it. Its add addresses the
board under the one owner the capability resolves, and counts as made only
where the board answers with the issue's card (point 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "templates"
    / ".github"
    / "workflows"
    / "pm-issue-check.yml"
)

#: The steps that read or add on the board.
BOARD_STEPS = {"Run pm validate-issue", "Auto-remediate board membership"}


@pytest.fixture(scope="module")
def steps() -> list[dict[str, Any]]:
    workflow = YAML(typ="safe").load(TEMPLATE.read_text(encoding="utf-8"))
    return workflow["jobs"]["check"]["steps"]


def _holds_the_board_credential(step: dict[str, Any]) -> bool:
    env = step.get("env") or {}
    token = str(env.get("GH_TOKEN") or "")
    return "PM_BOARD_TOKEN" in token or "board-app" in token


def test_only_the_steps_on_the_board_hold_its_credential(steps) -> None:
    holding = {step.get("name") for step in steps if _holds_the_board_credential(step)}
    assert holding == BOARD_STEPS


def test_the_credential_is_unset_as_shipped(steps) -> None:
    """Without the setting, each board step runs under the workflow's own token."""
    for step in steps:
        if step.get("name") in BOARD_STEPS:
            assert str(step["env"]["GH_TOKEN"]).endswith("|| secrets.GITHUB_TOKEN }}")
    [mint] = [step for step in steps if step.get("id") == "board-app"]
    assert mint["if"] == "vars.PM_BOARD_APP_ID != ''"


def test_the_add_has_one_owner_and_reads_its_answer(steps) -> None:
    """The add keeps no owner of its own: `gh.default_owner`, else the
    repository's. It asks for the board's answer and counts the add made only
    where that answer names a card."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "PM_PROJECT_BOARD_OWNER" not in text
    [add] = [step for step in steps if step.get("name") == "Auto-remediate board membership"]
    run = add["run"]
    assert "default_owner" in run and "OWNER=${OWNER:-$REPOSITORY_OWNER}" in run
    assert '--owner "$OWNER"' in run and "--format json" in run
    assert "d.get('id')" in run
