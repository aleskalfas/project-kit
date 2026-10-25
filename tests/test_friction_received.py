"""An artefact a project receives by sync owes it no answer (COR-062 point 9; #1873).

A rule of a method rule set arrives in an adopter by sync: the backbone's
`.pkit/rule-sets/` is a synced copy wherever the methodology is not authored. It
is still read as the location rule says (COR-051 point 2), and its anchors are
still checked, but neither check asks the project for an answer on it or reports
it stale, as for an artefact under an excluded path. The writers refuse it, and
the move leaves its answers where they are. A guide anchored to the same code is
asked as before.
"""

from __future__ import annotations

import pytest

from project_kit import friction_check as fc
from project_kit import friction_move as fm
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit import friction_write as fw
from project_kit.friction_discovery import discover_artefacts
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T1, friction_config, guide

RULES = ".pkit/rule-sets/xs.md"
RULE = f"{RULES}#RS-XS-001"
GUIDE = "docs/guide.md"

#: A method rule set whose one rule is anchored to the engine and revalidated at T1.
RECEIVED_RULES = f"""---
rule-set: XS
version: 1.0.0
rules:
  RS-XS-001:
    status: accepted
    pkit:
      friction:
        anchors:
          path: [src/core/**]
        revalidated:
          at: {T1}
          outcome: updated
---

# Rules

## RS-XS-001 — Rule one

The statement of RS-XS-001.
"""


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    adopter = make_adopter_repo()
    adopter.write(
        {
            CONFIG: friction_config(mode="enforcing"),
            **SOURCE,
            RULES: RECEIVED_RULES,
            GUIDE: guide(anchors={"path": ["src/core/**"]}),
        }
    )
    adopter.commit("base", files=None)
    return adopter


def test_a_rule_of_a_method_rule_set_is_read_as_received(repo: AdopterRepo) -> None:
    artefacts = {a.location: a for a in discover_artefacts(repo.root).artefacts}
    assert artefacts[RULE].received and artefacts[RULE].owes_no_answer
    assert not artefacts[GUIDE].received


def test_the_change_check_asks_a_received_artefact_nothing(repo: AdopterRepo) -> None:
    repo.checkout("feature", create=True)
    repo.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    result = fc.run_change_check(repo.root, "main")
    assert [(f.kind, f.location) for f in result.findings] == [(fc.FindingKind.FRICTION, GUIDE)]


def test_the_whole_repository_check_never_reports_a_received_artefact_stale(
    repo: AdopterRepo,
) -> None:
    repo.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    result = fr.run_repository_check(repo.root)
    assert [r.location for r in result.artefact_reports] == [GUIDE]
    stale = [f.location for f in result.findings if f.kind is fr.RepositoryFindingKind.STALE]
    assert stale == [GUIDE]
    assert frep.run_explain(repo.root, RULE).state == frep.RECEIVED


def test_the_writers_refuse_a_received_artefact(repo: AdopterRepo) -> None:
    for plan in (
        lambda: fw.plan_revalidate(repo.root, RULE, outcome="updated"),
        lambda: fw.plan_defer(repo.root, RULE, anchor="src/core/**", reason="later"),
        lambda: fw.plan_record_status(repo.root, RULE),
    ):
        with pytest.raises(fw.FrictionWriteError, match="arrives in this project by sync"):
            plan()


def test_the_move_leaves_a_received_artefact_s_answers(repo: AdopterRepo) -> None:
    plan = fm.plan_move(repo.root)
    assert [f.path for f in plan.files] == [GUIDE]
    (left,) = plan.left
    assert (left.artefact, left.path) == (RULE, RULES)
    assert "COR-062 point 9" in left.reason
