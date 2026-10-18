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
- **the number**: the rule keeps its number, 20, under "Answers on artefacts".
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CORE_RULES = REPO / ".pkit" / "rules" / "core.md"
AGENTS_README = REPO / ".pkit" / "agents" / "README.md"


def _rule_20() -> str:
    """Rule 20's paragraph, read from the section that holds it."""
    text = CORE_RULES.read_text(encoding="utf-8")
    section = text.split("\n## Answers on artefacts\n", 1)[1].split("\n## ", 1)[0]
    paragraphs = [p.strip() for p in section.split("\n\n") if p.strip().startswith("20. ")]
    assert len(paragraphs) == 1, "rule 20 is not the one numbered rule of its section"
    return paragraphs[0]


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
        "20. **A reviewer checks the answers your change owes, and a person decides any"
        " other answer on an artefact.**"
    )


@pytest.mark.parametrize(
    "words",
    [
        "the revalidation or the revisit entry you owe for a combined state after resolving"
        " a conflict (COR-050 point 16), without asking first",
        "Name an open follow-up in the reason of each deferral, or `deferred` revisit"
        " entry, you write.",
        "told the sentences and what is left out of date, until which follow-up, as"
        " information, not a gate",
        "Any other answer, on an artefact or for a link's target your change was not asked about,",
        'Details: the agents README, "Friction writers".',
    ],
)
def test_rule_20_names_revisit_entries(words):
    assert words in _rule_20()


@pytest.mark.parametrize(
    "words",
    [
        "`pkit friction revalidate`, `pkit friction defer` and `pkit friction revisit`",
        "the revalidation or the revisit entry it owes for a combined state after resolving"
        " a conflict (COR-050 point 16)",
        "The reviewer also checks that each target the change revisited by changing it meets"
        " the change to the source (COR-050 point 16).",
        "Each deferral, and each `deferred` revisit entry, the agent writes names an open"
        " follow-up in its reason.",
        "A revisit's line names instead the target, the link's field that lists it and the"
        " trigger fields the change modified.",
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
    ],
)
def test_neither_names_only_the_revalidation(text, stale):
    """The wording from before point 16 is gone: it named only the revalidation of a
    combined state, and told the person only of "the deferrals"."""
    assert stale not in text()
