"""Tests for the friction writers — `revalidate`, `defer`, `record-status` (Task #992, COR-050).

Every test stands up a real adopter repository (`make_adopter_repo`) with a
place declared and writes documents in block-style YAML, so a test can say
exactly which bytes a writer may touch: the expected file is the original
with one block's lines replaced, compared whole. The status tests commit
real history, since `record-status` runs the whole-repository check at HEAD.
The last test is property-style: seeded random documents — both forms, block
and flow style, awkward texts — put through random writes, each read back by
discovery and passed through validation.
"""

from __future__ import annotations

import copy
import json
import random
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import friction_check as fc
from project_kit import friction_repository as fr
from project_kit import friction_write as fw
from project_kit.cli import main
from project_kit.friction_discovery import Anchor, discover_artefacts, split_front_matter
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import HISTORY_EPOCH, AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, friction_config

NOW = datetime(2026, 10, 5, 10, 0, 0, tzinfo=UTC)

GUIDE_PATH = "docs/guide.md"

HEAD = """\
---
id: guide
title: The CLI guide   # the artefact's own field
pkit:
  friction:
    anchors:
      path: [src/cli/**, src/core/**]
"""

REVALIDATED = """\
    revalidated:
      at: 2026-10-01T09:00:00Z
      outcome: unchanged
      unchanged-because: the CLI surface is as described
"""

TAIL = """\

  # a comment the writers never touch
status: draft
---

# The CLI guide

Body.
"""

GUIDE = HEAD + REVALIDATED + TAIL


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    adopter = make_adopter_repo()
    adopter.write({CONFIG: friction_config(), **SOURCE})
    return adopter


def _put(repo: AdopterRepo, text: str, rel: str = GUIDE_PATH) -> Path:
    repo.write({rel: text})
    return repo.root / rel


def _read(repo: AdopterRepo, rel: str = GUIDE_PATH) -> str:
    return (repo.root / rel).read_bytes().decode("utf-8")


def _cli(*args: str, input: str | None = None) -> Result:
    return CliRunner().invoke(main, ["friction", *args], input=input)


def _validation_errors(repo: AdopterRepo) -> list[str]:
    return [f"{f.where}: {f.message}" for f in validate_friction(repo.root).errors]


def _block(repo: AdopterRepo, location: str = GUIDE_PATH) -> Any:
    (artefact,) = [a for a in discover_artefacts(repo.root).artefacts if a.location == location]
    return artefact.friction


# --- revalidate ------------------------------------------------------------------------


def test_revalidate_unchanged_rewrites_the_block_and_nothing_else(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    plan = fw.plan_revalidate(
        repo.root,
        "guide",
        outcome="unchanged",
        because="a refactor; nothing the guide says moved",
        now=NOW,
    )
    fw.write(plan)

    assert (
        _read(repo)
        == HEAD
        + (
            "    revalidated:\n"
            "      at: 2026-10-05T10:00:00Z\n"
            "      outcome: unchanged\n"
            "      unchanged-because: a refactor; nothing the guide says moved\n"
        )
        + TAIL
    )
    assert (plan.first_line, plan.last_line) == (8, 11)
    assert plan.target == "pkit.friction.revalidated"
    assert _validation_errors(repo) == []


def test_revalidate_refuses_the_justification_already_written(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    for same in ("the CLI surface is as described", "  the CLI   surface is\nas described "):
        with pytest.raises(fw.FrictionWriteError, match="must change"):
            fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because=same)
    assert _read(repo) == GUIDE


def test_revalidate_unchanged_needs_a_justification_and_updated_takes_none(
    repo: AdopterRepo,
) -> None:
    _put(repo, GUIDE)
    for because in (None, "   "):
        with pytest.raises(fw.FrictionWriteError, match="needs `--because`"):
            fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because=because)
    with pytest.raises(fw.FrictionWriteError, match="carries none"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", because="why")


def test_a_placeholder_left_unfilled_is_refused_and_code_in_brackets_is_not(
    repo: AdopterRepo,
) -> None:
    """A command shown for a person writes what they supply as a placeholder; run as
    shown, it would write the placeholder as the justification or the reason."""
    _put(repo, GUIDE)
    shown = (
        "<why the content still holds>",
        "the flag moved; defect <the defect reference> reported",
    )
    for because in shown:
        with pytest.raises(fw.FrictionWriteError, match="still holds the placeholder"):
            fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because=because)
    with pytest.raises(fw.FrictionWriteError, match="`--reason` still holds the placeholder"):
        fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="<why it can wait>")
    result = _cli("revalidate", "guide", "--outcome", "unchanged", "--because", shown[1], "--yes")
    assert result.exit_code != 0 and "'<the defect reference>'" in result.output
    assert _read(repo) == GUIDE

    code = "parse() now returns Vec<u8> and a Map<String, int>; a < b and c > d still hold"
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because=code, now=NOW))
    assert _block(repo)["revalidated"]["unchanged-because"] == code


def test_revalidate_updated_drops_the_old_justification(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW))
    assert (
        _read(repo)
        == HEAD
        + ("    revalidated:\n      at: 2026-10-05T10:00:00Z\n      outcome: updated\n")
        + TAIL
    )


def test_at_moves_on_every_revalidation(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    same_instant = datetime(2026, 10, 1, 9, 0, 0, 400_000, tzinfo=UTC)
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", now=same_instant)
    assert "at: 2026-10-01T09:00:01Z   (was 2026-10-01T09:00:00Z)" in plan.items


def test_revalidate_keeps_named_deferrals_and_removes_the_rest(repo: AdopterRepo) -> None:
    deferrals = (
        "      deferred:\n"
        "      - anchor: {kind: path, value: src/core/**}\n"
        "        reason: the core rewrite lands next sprint\n"
        "      - reason: waiting on the CLI redesign\n"
        "        anchor:\n"
        "          value: src/cli/**\n"
        "          kind: path\n"
    )
    _put(repo, HEAD + REVALIDATED + deferrals + TAIL)
    plan = fw.plan_revalidate(
        repo.root,
        "guide",
        outcome="unchanged",
        because="checked against the new flags",
        keep=["src/cli/**"],
        now=NOW,
    )
    fw.write(plan)
    assert (
        _read(repo)
        == HEAD
        + (
            "    revalidated:\n"
            "      at: 2026-10-05T10:00:00Z\n"
            "      outcome: unchanged\n"
            "      unchanged-because: checked against the new flags\n"
            "      deferred:\n"
            "        - anchor:\n"
            "            kind: path\n"
            "            value: src/cli/**\n"
            "          reason: waiting on the CLI redesign\n"
        )
        + TAIL
    )
    assert "keeps deferral path:src/cli/**   (waiting on the CLI redesign)" in plan.items
    assert "removes deferral path:src/core/**   (the core rewrite lands next sprint)" in plan.items
    assert _validation_errors(repo) == []


def test_revalidate_refuses_to_keep_what_is_not_deferred_or_would_dangle(
    repo: AdopterRepo,
) -> None:
    dangling = (
        "      deferred:\n"
        "      - anchor: {kind: record, value: COR-050}\n"
        "        reason: the record is being amended\n"
    )
    _put(repo, HEAD + REVALIDATED + dangling + TAIL)
    with pytest.raises(fw.FrictionWriteError, match=r"no deferral of 'src/cli/\*\*' to keep"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", keep=["src/cli/**"])
    with pytest.raises(fw.FrictionWriteError, match="would dangle"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", keep=["record:COR-050"])
    # Not kept, the dangling entry is removed — which is what validation asks for.
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW)
    assert any("no longer declares that anchor" in item for item in plan.items)
    fw.write(plan)
    assert _validation_errors(repo) == []


def test_revalidate_asks_about_each_deferral_on_a_terminal(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    deferrals = (
        "      deferred:\n"
        "      - anchor: {kind: path, value: src/cli/**}\n"
        "        reason: cli\n"
        "      - anchor: {kind: path, value: src/core/**}\n"
        "        reason: core\n"
    )
    _put(repo, HEAD + REVALIDATED + deferrals + TAIL)
    monkeypatch.setattr(fw, "interactive", lambda: True)
    # Keep the first, remove the second, then confirm the write.
    result = _cli(
        "revalidate", "guide", "--outcome", "unchanged", "--because", "reread", input="y\nn\ny\n"
    )
    assert result.exit_code == 0, result.output
    assert "Keep the deferral of path:src/cli/** — cli?" in result.output
    assert "+++ b/docs/guide.md" in result.output  # the diff comes before the confirmation
    deferred = _block(repo)["revalidated"]["deferred"]
    assert deferred == [{"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "cli"}]


# --- defer --------------------------------------------------------------------------------


def test_defer_adds_a_sorted_entry_and_leaves_at_byte_for_byte(repo: AdopterRepo) -> None:
    existing = (
        "      deferred:\n      - anchor: {kind: path, value: src/core/**}\n        reason: core\n"
    )
    _put(repo, HEAD + REVALIDATED + existing + TAIL)
    plan = fw.plan_defer(repo.root, "guide", anchor="path:src/cli/**", reason="the redesign")
    fw.write(plan)
    assert (
        _read(repo)
        == HEAD
        + REVALIDATED
        + (
            "      deferred:\n"
            "        - anchor:\n"
            "            kind: path\n"
            "            value: src/cli/**\n"
            "          reason: the redesign\n"
            "        - anchor:\n"
            "            kind: path\n"
            "            value: src/core/**\n"
            "          reason: core\n"
        )
        + TAIL
    )
    assert plan.target == "pkit.friction.revalidated.deferred"
    assert "at: not changed — a deferral is not a revalidation" in plan.items
    assert _validation_errors(repo) == []


def test_defer_on_an_artefact_never_revalidated_writes_deferred_alone(repo: AdopterRepo) -> None:
    _put(repo, HEAD + TAIL)
    fw.write(fw.plan_defer(repo.root, "guide", anchor="src/core/**", reason="later"))
    assert (
        _read(repo)
        == HEAD
        + (
            "    revalidated:\n"
            "      deferred:\n"
            "        - anchor:\n"
            "            kind: path\n"
            "            value: src/core/**\n"
            "          reason: later\n"
        )
        + TAIL
    )
    assert _validation_errors(repo) == []


def test_defer_refuses_an_anchor_the_artefact_does_not_carry(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    with pytest.raises(fw.FrictionWriteError, match=r"does not carry the anchor 'src/web/\*\*'"):
        fw.plan_defer(repo.root, "guide", anchor="src/web/**", reason="later")
    with pytest.raises(fw.FrictionWriteError, match="does not carry the anchor 'record:src/cli/"):
        fw.plan_defer(repo.root, "guide", anchor="record:src/cli/**", reason="later")
    with pytest.raises(fw.FrictionWriteError, match="names the anchor"):
        fw.plan_defer(repo.root, "guide", anchor="  ", reason="later")
    with pytest.raises(fw.FrictionWriteError, match="carries its reason"):
        fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="")
    assert _read(repo) == GUIDE


def test_defer_rewords_a_reason_and_the_same_reason_writes_nothing(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    fw.write(fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="first"))
    again = fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="  first ")
    assert not again.changes and "already deferred with this reason" in (again.unchanged or "")
    reworded = fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="second")
    assert any("does not move" in item for item in reworded.items)
    fw.write(reworded)
    assert _block(repo)["revalidated"]["deferred"] == [
        {"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "second"}
    ]


def test_a_value_carried_under_two_kinds_must_be_named_with_its_kind(repo: AdopterRepo) -> None:
    doc = HEAD.replace(
        "      path: [src/cli/**, src/core/**]\n",
        "      path: [src/cli/**]\n      artefact: [src/cli/**]\n",
    )
    _put(repo, doc + TAIL)
    with pytest.raises(fw.FrictionWriteError, match="name it as `kind:value`"):
        fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="later")
    plan = fw.plan_defer(repo.root, "guide", anchor="artefact:src/cli/**", reason="later")
    assert "adds deferral artefact:src/cli/**: later" in plan.items


# --- the answers the writers give, read by the checks ---------------------------------------


def _commit_base(repo: AdopterRepo, text: str = GUIDE) -> str:
    _put(repo, text)
    return repo.commit("base", files=None, date=HISTORY_EPOCH)


def test_revalidate_and_defer_answer_the_change_check(repo: AdopterRepo) -> None:
    base = _commit_base(repo)
    repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    before = fc.run_change_check(repo.root, base)
    assert [f.kind for f in before.findings] == [fc.FindingKind.FRICTION]

    fw.write(fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="the redesign"))
    deferred = fc.run_change_check(repo.root, base)
    assert [(f.kind, f.answer) for f in deferred.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.DEFERRED)
    ]

    _put(repo, GUIDE)
    fw.write(
        fw.plan_revalidate(
            repo.root, "guide", outcome="unchanged", because="the new flag is internal"
        )
    )
    unchanged = fc.run_change_check(repo.root, base)
    assert [(f.kind, f.answer) for f in unchanged.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.UNCHANGED)
    ]


def test_rewording_a_deferral_keeps_its_deferral_point(repo: AdopterRepo) -> None:
    _commit_base(repo)
    repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    fw.write(fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="first"))
    introduced = repo.commit("defer the CLI change", files=None)
    fw.write(fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="reworded"))
    repo.commit("reword the deferral", files=None)

    (report,) = fr.run_repository_check(repo.root).artefact_reports
    assert report.state is fr.ArtefactState.DEFERRED
    ((anchor, point),) = report.deferral_points
    assert anchor == Anchor("path", "src/cli/**")
    assert point is not None and point.sha == introduced


# --- record-status ------------------------------------------------------------------------


def _last_check(repo: AdopterRepo) -> Any:
    return _block(repo).get("last-check")


def test_record_status_writes_last_check_on_its_own_lines_only_when_it_changes(
    repo: AdopterRepo,
) -> None:
    _commit_base(repo)
    origin = repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    head = repo.head()

    result = _cli("record-status", "guide", "--yes")
    assert result.exit_code == 0, result.output
    assert _last_check(repo) == {"state": "stale", "as-of": head, "since": origin}
    written = _read(repo)
    status_lines = written.split(REVALIDATED, 1)[1].split(TAIL, 1)[0]
    assert status_lines.splitlines()[0] == "    last-check:"
    assert written.startswith(HEAD + REVALIDATED) and written.endswith(TAIL)
    # The status is container bookkeeping: the change check sees nothing to answer.
    assert fc.run_change_check(repo.root, head).findings == ()

    again = _cli("record-status", "guide", "--yes")
    assert again.exit_code == 0 and "Nothing to write" in again.output
    repo.commit("record the status", files=None)
    repo.commit("an unrelated page", {"README.md": "Hello.\n"})
    still = _cli("record-status", "guide", "--yes")
    assert still.exit_code == 0 and "Nothing to write" in still.output  # as-of alone is no change

    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because="v2 is internal"))
    revalidated = repo.commit("revalidate the guide", files=None)
    assert _cli("record-status", "guide", "--yes").exit_code == 0
    assert _last_check(repo) == {"state": "current", "as-of": revalidated}


def test_record_status_refuses_what_has_no_status(repo: AdopterRepo) -> None:
    _commit_base(repo)
    _put(repo, "---\nid: bare\npkit:\n  friction: {}\n---\nBody.\n", "docs/bare.md")
    with pytest.raises(fw.FrictionWriteError, match="no anchors or deferrals"):
        fw.plan_record_status(repo.root, "bare")
    _put(repo, GUIDE.replace("id: guide", "id: fresh"), "docs/fresh.md")
    with pytest.raises(fw.FrictionWriteError, match="commit it first"):
        fw.plan_record_status(repo.root, "fresh")


def test_record_status_in_a_flow_block_stays_inside_it(repo: AdopterRepo) -> None:
    flow = "---\nid: flow\npkit: { friction: { anchors: { path: [src/cli/**] } } }\n---\nBody.\n"
    _commit_base(repo, flow)
    head = repo.head()
    fw.write(fw.plan_record_status(repo.root, "flow"))
    assert _read(repo) == (
        "---\nid: flow\npkit: { friction: { anchors: { path: [src/cli/**] }, "
        f'last-check: {{state: "current", as-of: "{head}"}} }} }}\n---\nBody.\n'
    )
    assert _validation_errors(repo) == []


# --- consent ------------------------------------------------------------------------------


def test_without_consent_a_writer_refuses_and_names_the_command(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    result = _cli("defer", "guide", "--anchor", "src/cli/**", "--reason", "the redesign")
    assert result.exit_code == 1
    assert "refusing to write docs/guide.md without consent" in result.output
    assert (
        "pkit friction defer guide --anchor 'src/cli/**' --reason 'the redesign' --yes"
        in result.output
    )
    assert _read(repo) == GUIDE


def test_dry_run_shows_the_diff_and_writes_nothing(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    result = _cli("defer", "guide", "--anchor", "src/cli/**", "--reason", "later", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "Writes pkit.friction.revalidated.deferred in docs/guide.md" in result.output
    assert "+      deferred:" in result.output
    assert "Dry run: nothing written." in result.output
    assert _read(repo) == GUIDE


def test_a_terminal_confirms_after_the_diff_and_declining_writes_nothing(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _put(repo, GUIDE)
    monkeypatch.setattr(fw, "interactive", lambda: True)
    declined = _cli("defer", "guide", "--anchor", "src/cli/**", "--reason", "later", input="n\n")
    assert declined.exit_code == 1 and "Write this to docs/guide.md?" in declined.output
    assert _read(repo) == GUIDE
    accepted = _cli("defer", "guide", "--anchor", "src/cli/**", "--reason", "later", input="y\n")
    assert accepted.exit_code == 0 and "Wrote pkit.friction.revalidated.deferred" in accepted.output
    assert _read(repo) != GUIDE


def test_yes_and_dry_run_exclude_each_other(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    result = _cli("record-status", "guide", "--yes", "--dry-run")
    assert result.exit_code == 2 and "exclude each other" in result.output


# --- naming the artefact, and its forms -----------------------------------------------------

COLLECTION = """\
---
alpha:
  title: Alpha
  pkit:
    friction:
      anchors: {path: [src/cli/**]}
beta:
  title: Beta
  pkit:
    friction:
      anchors: {path: [src/core/**]}
---

## alpha

Alpha body.

## beta

Beta body.
"""


def test_an_entry_is_written_alone_in_its_collection(repo: AdopterRepo) -> None:
    _put(repo, COLLECTION, "docs/rules.md")
    fw.write(fw.plan_defer(repo.root, "docs/rules.md#alpha", anchor="src/cli/**", reason="x"))
    assert _read(repo, "docs/rules.md") == COLLECTION.replace(
        "      anchors: {path: [src/cli/**]}\n",
        "      anchors: {path: [src/cli/**]}\n"
        "      revalidated:\n"
        "        deferred:\n"
        "          - anchor:\n"
        "              kind: path\n"
        "              value: src/cli/**\n"
        "            reason: x\n",
    )
    assert _validation_errors(repo) == []


def test_a_rule_is_written_inside_its_rule_set(repo: AdopterRepo) -> None:
    rule_set = (
        "---\n"
        "name: cmn\n"
        "rules:\n"
        "  RS-CMN-001:\n"
        "    title: Name things\n"
        "    pkit:\n"
        "      friction:\n"
        "        anchors: {record: [COR-050]}\n"
        "---\n\n## RS-CMN-001 — Name things\n\nUse names.\n"
    )
    _put(repo, rule_set, "docs/rule-sets/cmn.md")
    plan = fw.plan_defer(repo.root, "RS-CMN-001", anchor="COR-050", reason="being amended")
    assert plan.artefact == "docs/rule-sets/cmn.md#RS-CMN-001"
    fw.write(plan)
    assert _read(repo, "docs/rule-sets/cmn.md") == rule_set.replace(
        "        anchors: {record: [COR-050]}\n",
        "        anchors: {record: [COR-050]}\n"
        "        revalidated:\n"
        "          deferred:\n"
        "            - anchor:\n"
        "                kind: record\n"
        "                value: COR-050\n"
        "              reason: being amended\n",
    )


def test_a_reference_must_name_exactly_one_artefact(repo: AdopterRepo) -> None:
    _put(repo, COLLECTION, "docs/rules.md")
    _put(repo, COLLECTION, "docs/more.md")
    with pytest.raises(fw.FrictionWriteError, match="names 2 artefacts"):
        fw.find_artefact(repo.root, "alpha")
    with pytest.raises(fw.FrictionWriteError, match=r"The file holds docs/rules\.md#alpha"):
        fw.find_artefact(repo.root, "docs/rules.md")
    assert fw.find_artefact(repo.root, "docs/more.md#beta").location == "docs/more.md#beta"


def test_an_artefact_without_a_friction_block_is_refused(repo: AdopterRepo) -> None:
    _put(repo, "---\nid: plain\ntitle: Plain\n---\nBody.\n", "docs/plain.md")
    with pytest.raises(fw.FrictionWriteError, match="carries no `friction` block"):
        fw.plan_revalidate(repo.root, "plain", outcome="updated")


def test_a_block_that_would_not_validate_is_not_written(repo: AdopterRepo) -> None:
    broken = GUIDE.replace("    anchors:\n", "    anchor-typo: 1\n    anchors:\n")
    _put(repo, broken)
    with pytest.raises(fw.FrictionWriteError, match="would not validate"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated")
    assert _read(repo) == broken


# --- property: what the writers write reads back, and validates -----------------------------

AWKWARD = (
    "plain words",
    "has: a colon",
    "hash # inside",
    "#starts with a hash",
    "- a dash",
    "* a star",
    "&anchor-like",
    "!tag-like",
    "'single quoted'",
    '"double quoted"',
    "trailing space ",
    " leading space",
    "two\nlines",
    "123",
    "true",
    "null",
    "yes",
    "2026-10-02",
    "2026-10-02T09:40:12Z",
    "ünïcödé — with a dash",
    "tab\there",
    "{braces}",
    "[brackets]",
    "a, b",
    "%percent",
    "@at",
    "`tick`",
    "back\\slash",
    "~",
    "0x1F",
    "1e3",
    ".inf",
    "line\u2028separator",
)

ANCHOR_VALUES = {
    "path": ("src/cli/**", "**/x.md", "*.py", "docs/a b.md", "src/[ab]/*.py", "a:b/c"),
    "record": ("COR-050", "software-analysis:DEC-001", "ADR-019"),
    "artefact": ("guide", "docs/other.md", "RS-CMN-001"),
}

_safe = YAML(typ="safe")


def _q(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _random_block(rng: random.Random) -> dict[str, Any]:
    anchors: dict[str, list[str]] = {}
    for kind in rng.sample(sorted(ANCHOR_VALUES), rng.randint(1, 3)):
        anchors[kind] = rng.sample(ANCHOR_VALUES[kind], rng.randint(1, 2))
    block: dict[str, Any] = {"anchors": anchors}
    revalidated: dict[str, Any] = {}
    if rng.random() < 0.6:
        revalidated["at"] = "2026-10-01T09:00:00Z"
        revalidated["outcome"] = rng.choice(("updated", "unchanged"))
        if revalidated["outcome"] == "unchanged":
            revalidated["unchanged-because"] = rng.choice(AWKWARD)
    carried = [(k, v) for k, values in anchors.items() for v in values]
    if rng.random() < 0.5:
        chosen = rng.sample(carried, rng.randint(1, len(carried)))
        revalidated["deferred"] = [
            {"anchor": {"kind": k, "value": v}, "reason": rng.choice(AWKWARD)} for k, v in chosen
        ]
    if revalidated:
        block["revalidated"] = revalidated
    if rng.random() < 0.3:
        block["last-check"] = {"state": "current", "as-of": "abc123"}
    return block


def _block_yaml(key: str, value: Any, indent: int, step: int, compact: bool) -> list[str]:
    """Block style with every text JSON-quoted: the fixture's own writer, not the module's."""
    pad = " " * indent
    if isinstance(value, Mapping):
        lines = [f"{pad}{key}:"]
        for k, v in value.items():
            lines += _block_yaml(k, v, indent + step, step, compact)
        return lines
    if isinstance(value, list) and value and isinstance(value[0], Mapping):
        lines = [f"{pad}{key}:"]
        dash = indent if compact else indent + step
        for item in value:
            inner: list[str] = []
            for k, v in item.items():
                inner += _block_yaml(k, v, dash + 2, step, compact)
            lines.append(" " * dash + "- " + inner[0][dash + 2 :])
            lines += inner[1:]
        return lines
    return [f"{pad}{key}: {_q(value)}"]


def _random_document(rng: random.Random) -> tuple[str, str, list[str]]:
    """(text, the reference of the artefact under test, the carrier's keys from the root)."""
    block = _random_block(rng)
    step = rng.choice((2, 4))
    compact = rng.random() < 0.5
    flow = rng.random() < 0.35
    collection = rng.random() < 0.4
    container = {"friction": block}
    if flow:
        carried = [f"{' ' * step}pkit: {_q(container)}"]
    else:
        carried = _block_yaml("pkit", container, step, step, compact)
    if collection:
        other = {"friction": {"anchors": {"path": ["src/**"]}}}
        lines = [
            "---",
            "alpha:",
            f"{' ' * step}title: {_q(rng.choice(AWKWARD))}",
            *carried,
            "beta:",
            *_block_yaml("pkit", other, step, step, compact),
            "---",
            "",
            "## alpha",
            "",
            "Alpha body.",
            "",
        ]
        return "\n".join(lines), "docs/doc.md#alpha", ["alpha"]
    dedented = [line[step:] for line in carried]
    lines = ["---", "id: doc", *dedented, "# a comment", "status: draft", "---", "", "Body.", ""]
    return "\n".join(lines), "doc", []


def _parsed_front_matter(text: str) -> Any:
    front_matter, _body = split_front_matter(text)
    return bs.as_written(_safe.load(front_matter or ""))


def _changed_region_is_front_matter(before: str, after: str) -> bool:
    prefix = 0
    while prefix < min(len(before), len(after)) and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < min(len(before), len(after)) - prefix
        and before[len(before) - 1 - suffix] == after[len(after) - 1 - suffix]
    ):
        suffix += 1
    closing = before.index("\n---\n", 3)
    return prefix > 4 and len(before) - suffix <= closing + 1


def _sorted_deferrals(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda e: (e["anchor"]["kind"], e["anchor"]["value"]))


def test_written_blocks_read_back_identically_and_validate(repo: AdopterRepo) -> None:
    for seed in range(40):
        rng = random.Random(seed)
        text, reference, carrier_keys = _random_document(rng)
        _put(repo, text, "docs/doc.md")
        location = "docs/doc.md" if not carrier_keys else reference
        model = copy.deepcopy(_block(repo, location))
        now = NOW
        for step in range(4):
            before = _read(repo, "docs/doc.md")
            carried = [(k, v) for k, values in model["anchors"].items() for v in values]
            revalidated = model.get("revalidated") or {}
            if rng.random() < 0.5:
                kind, value = rng.choice(carried)
                reason = f"{rng.choice(AWKWARD)} {seed}-{step}"
                plan = fw.plan_defer(repo.root, reference, anchor=f"{kind}:{value}", reason=reason)
                entries = [
                    e
                    for e in revalidated.get("deferred", [])
                    if (e["anchor"]["kind"], e["anchor"]["value"]) != (kind, value)
                ]
                entry = {"anchor": {"kind": kind, "value": value}, "reason": reason.strip()}
                revalidated = {**revalidated, "deferred": _sorted_deferrals([*entries, entry])}
            else:
                outcome = rng.choice(("updated", "unchanged"))
                because = f"{rng.choice(AWKWARD)} {seed}-{step}" if outcome == "unchanged" else None
                existing = revalidated.get("deferred", [])
                keep = [e for e in existing if rng.random() < 0.5]
                now += timedelta(minutes=1)
                plan = fw.plan_revalidate(
                    repo.root,
                    reference,
                    outcome=outcome,
                    because=because,
                    keep=[f"{e['anchor']['kind']}:{e['anchor']['value']}" for e in keep],
                    now=now,
                )
                revalidated = {"at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "outcome": outcome}
                if because is not None:
                    revalidated["unchanged-because"] = because.strip()
                if keep:
                    revalidated["deferred"] = _sorted_deferrals(keep)
            fw.write(plan)
            model["revalidated"] = revalidated
            after = _read(repo, "docs/doc.md")

            context = f"seed {seed}, step {step}:\n{before}\n---->\n{after}"
            assert _block(repo, location) == model, context
            expected = _parsed_front_matter(before)
            holder = expected
            for key in carrier_keys:
                holder = holder[key]
            holder["pkit"]["friction"] = model
            assert _parsed_front_matter(after) == expected, context
            assert _changed_region_is_front_matter(before, after), context
            assert _validation_errors(repo) == [], context
            if "deferred" in revalidated and plan.command == "defer":
                last = revalidated["deferred"][-1]
                repeat = fw.plan_defer(
                    repo.root,
                    reference,
                    anchor=f"{last['anchor']['kind']}:{last['anchor']['value']}",
                    reason=last["reason"],
                )
                assert not repeat.changes, context


# --- the read-back reads the container against the wiring (#1058) ------------


def test_the_read_back_reads_a_role_block_against_the_wiring(repo: AdopterRepo) -> None:
    """A block beside a role block: the read-back resolves the tree's wiring, as
    validation does. A role with no active provider is an orphan — a report,
    never a refusal — and the role block's bytes are left exactly as they were.
    (#1054 made the wiring a required input of the container check; #1055's
    read-back met it without one.)"""
    role_block = (
        "  documentation:\n    reading-evidence:\n      schema_version: 1\n      last-run: never\n"
    )
    _put(repo, HEAD + REVALIDATED + role_block + TAIL)
    plan = fw.plan_defer(repo.root, "guide", anchor="path:src/cli/**", reason="the redesign")
    fw.write(plan)
    text = _read(repo)
    assert role_block in text
    assert "reason: the redesign" in text
