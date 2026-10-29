"""Core rule 20 and the agents README's "Friction writers" name revisit entries (#1736).

COR-050 point 16 adds a third answer an artefact carries: the entry for a target
of one of its links, in its `revisited` list. Points 3 and 16 make it an answer a
change owes like a revalidation or a deferral. These tests hold that the rule an
agent reads at session start, and the README it points to, say so:

- **the conflict**: an agent writes the revalidation or the revisit entry it owes
  for a combined state after resolving a conflict, citing point 16;
- **the follow-up**: a `deferred` revisit entry names an open follow-up, as a
  deferral does;
- **the reviewer**: it also checks each target the change revisited by changing
  it (README), and the person who authorises the merge is told what is left out
  of date, until which follow-up, not only "the deferrals";
- **any other entry**: one for a target the change was not asked about stays a
  person's decision;
- **the number**: the rule keeps its number, 20, and its id, `RS-OPS-020`, under
  "Answers on artefacts".

The rule is read from the loaded file a session loads, `.pkit/rules/core.md`, which is
generated from the backbone's loaded set `OPS` (COR-068).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CORE_RULES = REPO / ".pkit" / "rules" / "core.md"
AGENTS_README = REPO / ".pkit" / "agents" / "README.md"


RULE_20_HEADING = "### 20. A reviewer checks the answers a change owes (RS-OPS-020)"


def _rule_20() -> str:
    """Rule 20's statement, read from under its heading in the section that holds it."""
    text = CORE_RULES.read_text(encoding="utf-8")
    section = text.split("\n## Answers on artefacts\n", 1)[1].split("\n## ", 1)[0]
    headings = [line for line in section.splitlines() if line.startswith("### ")]
    assert headings == [RULE_20_HEADING], "rule 20 is not the one rule of its section"
    return section.split(f"{RULE_20_HEADING}\n", 1)[1].strip()


def _friction_writers() -> str:
    """The README's "Friction writers" paragraph, its bullets and its closing paragraph."""
    text = AGENTS_README.read_text(encoding="utf-8")
    return text.split("\n**Friction writers.**", 1)[1].split("\n## ", 1)[0]


def _change_bullet() -> str:
    """The bullet on an agent making a change."""
    section = _friction_writers()
    return section.split("\n- **An agent making a change**", 1)[1].split("\n- ", 1)[0]


def test_rule_20_keeps_its_number_and_title():
    assert _rule_20().startswith(
        "**A reviewer checks the answers your change owes, and a person, or the delegate"
        " they named, decides any other answer on an artefact.**"
    )


def test_rule_20_names_the_delegate_and_its_bounds():
    """A person may name a delegate to decide the answers no change owes (COR-064): named
    in the default branch's configuration. The rule names where the delegate is named and
    what a session does with neither the person nor the delegate, and that a reviewer checks
    every such answer, whoever decided it, blocking the merge or the direct commit on one that
    does not hold (COR-064 point 4). The delegate's own bound, never on its own draft, is the
    agents README's, which the rule cites."""
    rule = _rule_20()
    assert "or the delegate the default branch's configuration names (`friction.delegate`)" in rule
    assert (
        "The reviewer checks these too, whoever decided them, and blocks the merge, or the"
        " direct commit, on an answer or an `updated` sentence that does not hold." in rule
    )
    assert (
        "Where you can ask neither the person nor the delegate, return the commands and run"
        " none" in rule
    )
    assert '(COR-064; the agents README, "Friction writers")' in rule
    writers = _friction_writers()
    assert "**Whose drafts.** Only an answer another agent drafted." in writers
    assert "checks every such answer and reason a change writes, whoever decided it" in writers


@pytest.mark.parametrize(
    "words",
    [
        "Write the answers `pkit friction check` asks of your change, without asking the"
        " person to accept them,",
        "commit them with it, a new answer file among them (COR-062 point 1).",
        "make its reason judge their combined state (COR-062 point 7).",
        "Name an open follow-up in each deferral or `deferred` revisit entry,",
        "is told these sentences and what is left out of date, until which follow-up, as"
        " information.",
        "Write any other answer, on an artefact or a link's target, or every reason for having"
        " no anchors, only once a person accepted it word for word,",
        '(COR-064; the agents README, "Friction writers")',
    ],
)
def test_rule_20_names_revisit_entries(words):
    assert words in _rule_20()


@pytest.mark.parametrize(
    "words",
    [
        "`pkit friction revalidate`, `pkit friction defer` and `pkit friction revisit`",
        "those the change check (`pkit friction check`) asks of it. It asks nobody first.",
        "One flag marks a revalidation that replaces revalidations answered apart, and the"
        " reviewer checks that its reason judges their combined state (COR-062 point 7).",
        "The agent commits what the writers write with its change, a new answer file among it.",
        "The reviewer also checks that each target the change revisited by changing it meets"
        " the change to the source (COR-050 point 16).",
        "Each deferral, and each `deferred` revisit entry, the agent writes names an open"
        " follow-up in its reason.",
        "told those sentences and what is left out of date, until which follow-up, as"
        " information, not a gate (COR-050 point 3)",
    ],
)
def test_the_readme_bullet_agrees(words):
    assert words in _change_bullet()


def test_the_readme_leaves_any_other_entry_to_a_person():
    assert (
        "Any other answer — on an artefact or for a target a change was not asked about —"
        " and every reason for having no anchors is written by any agent only under the"
        " four conditions above."
    ) in _friction_writers()


@pytest.mark.parametrize(
    ("text", "stale"),
    [
        (_rule_20, "the revalidation of a combined state you owe"),
        (_rule_20, "the sentences and the deferrals"),
        (_rule_20, "on an artefact your change was not asked about"),
        (_change_bullet, "the revalidation of a combined state it owes"),
        (_change_bullet, "those sentences and the deferrals"),
        (_friction_writers, "on an artefact a change was not asked about"),
        # COR-062 overturns COR-050's rule on an answer owed after a conflict (#1873).
        (_rule_20, "after resolving a conflict"),
        (_change_bullet, "after resolving a conflict"),
    ],
)
def test_neither_names_only_the_revalidation(text, stale):
    """The wording from before point 16 is gone: it named only the revalidation of a
    combined state, and told the person only of "the deferrals"."""
    assert stale not in text()
