"""Tests for the friction writers — `revalidate`, `defer`, `record-status` (Task #992, COR-050,
COR-062).

Every test stands up a real adopter repository, its install committed once per
session (`committed_adopter`), with a place declared. It writes documents in
block-style YAML, so a test can say exactly which bytes a writer may touch.
`revalidate` and `defer` write the change's own answer file and leave the
artefact's file byte for byte, its answers already taken into an answer file
(`answers_in_files`). `record-status` replaces one key of the block, the
expected file the original with that key's lines replaced, compared whole. The
status tests commit real history, since `record-status` runs the
whole-repository check at HEAD. The property-style test puts seeded random
documents — both forms, block and flow style, awkward texts — through random
writes, each read back by the answer reader and passed through validation.
Three seeds take the round trip through the repository, and the rest the answer
files' pure layer, which starts no process (#2309).
"""

from __future__ import annotations

import copy
import json
import random
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple, cast

import pytest
from click.testing import CliRunner, Result
from ruamel.yaml import YAML

from project_kit import answer_files as af
from project_kit import backbone_schemas as bs
from project_kit import friction_check as fc
from project_kit import friction_repository as fr
from project_kit import friction_write as fw
from project_kit.cli import main
from project_kit.document_parts import split_front_matter
from project_kit.friction_discovery import Anchor, discover_artefacts, parse_artefacts
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import HISTORY_EPOCH, AdopterRepo
from tests.friction_documents import (
    CONFIG,
    SOURCE,
    friction_config,
    own_answer_file,
    own_entry,
)

#: The documents here say each artefact's answers beside its anchors, and each write
#: takes them into answer files, as a change writes them (COR-062 point 1).
pytestmark = pytest.mark.usefixtures("answers_in_files")

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

#: The guide as its file holds it once its answers are in an answer file (COR-062 point 1).
ANSWERED = HEAD + TAIL

RULE_SET_PATH = "docs/rule-sets/cmn.md"

#: A rule set whose one rule is revalidated.
RULE_SET = (
    "---\n"
    "name: cmn\n"
    "rules:\n"
    "  RS-CMN-001:\n"
    "    title: Name things\n"
    "    pkit:\n"
    "      friction:\n"
    "        anchors: {record: [COR-050]}\n"
    "        revalidated:\n"
    "          at: 2026-10-01T09:00:00Z\n"
    "          outcome: updated\n"
    "---\n\n## RS-CMN-001 — Name things\n\nUse names.\n"
)


@pytest.fixture
def repo(committed_adopter: AdopterRepo) -> AdopterRepo:
    committed_adopter.write({CONFIG: friction_config(), **SOURCE})
    return committed_adopter


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


def _own_name(repo: AdopterRepo) -> str:
    return own_answer_file(repo.root)


def _own_entry(repo: AdopterRepo, location: str = GUIDE_PATH) -> dict[str, Any]:
    return own_entry(repo.root, location)


def _entries_of(repo: AdopterRepo, location: str) -> list[dict[str, Any]]:
    """Every entry for `location` in the answer files of the working tree, as written."""
    return [
        dict(e)
        for found in af.working_tree_files(repo.root).values()
        for e in cast(list[dict[str, Any]], found.document[af.ANSWERS_KEY])
        if e[af.ARTEFACT_KEY] == location
    ]


# --- revalidate ------------------------------------------------------------------------


def test_revalidate_unchanged_writes_its_answer_file_and_nothing_else(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    plan = fw.plan_revalidate(
        repo.root,
        "guide",
        outcome="unchanged",
        because="a refactor; nothing the guide says moved",
        now=NOW,
    )
    fw.write(plan)

    assert _read(repo) == ANSWERED
    assert _own_entry(repo)["revalidated"] == {
        "at": "2026-10-05T10:00:00Z",
        "outcome": "unchanged",
        "unchanged-because": "a refactor; nothing the guide says moved",
    }
    assert plan.answer_file and plan.target == "answers[docs/guide.md].revalidated"
    assert _validation_errors(repo) == []


def test_revalidate_refuses_the_justification_already_written(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    written = af.working_tree_files(repo.root)
    for same in ("the CLI surface is as described", "  the CLI   surface is\nas described "):
        with pytest.raises(fw.FrictionWriteError, match="must differ"):
            fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because=same)
    assert _read(repo) == ANSWERED and af.working_tree_files(repo.root) == written


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
    assert _read(repo) == ANSWERED

    code = "parse() now returns Vec<u8> and a Map<String, int>; a < b and c > d still hold"
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because=code, now=NOW))
    assert _own_entry(repo)["revalidated"]["unchanged-because"] == code


def test_revalidate_updated_drops_the_old_justification(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW))
    assert _read(repo) == ANSWERED
    assert _own_entry(repo)["revalidated"] == {"at": "2026-10-05T10:00:00Z", "outcome": "updated"}


def test_at_moves_on_every_revalidation(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    same_instant = datetime(2026, 10, 1, 9, 0, 0, 400_000, tzinfo=UTC)
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", now=same_instant)
    assert "at: 2026-10-01T09:00:01Z" in plan.items


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
    assert _read(repo) == ANSWERED
    assert _own_entry(repo)["revalidated"] == {
        "at": "2026-10-05T10:00:00Z",
        "outcome": "unchanged",
        "unchanged-because": "checked against the new flags",
        "deferred": [
            {
                "anchor": {"kind": "path", "value": "src/cli/**"},
                "reason": "waiting on the CLI redesign",
            }
        ],
    }
    assert "keeps deferral path:src/cli/**   (waiting on the CLI redesign)" in plan.items
    assert "drops deferral path:src/core/**   (the core rewrite lands next sprint)" in plan.items
    assert _validation_errors(repo) == []


def test_revalidate_refuses_to_keep_what_is_not_deferred_or_answers_nothing(
    repo: AdopterRepo,
) -> None:
    """A deferral of an anchor the artefact no longer declares answers nothing, so it is
    not live, and keeping it is refused as keeping one never written is (COR-062 point
    5). Not kept, it is not written again, and validation fails nothing."""
    dangling = (
        "      deferred:\n"
        "      - anchor: {kind: record, value: COR-050}\n"
        "        reason: the record is being amended\n"
    )
    _put(repo, HEAD + REVALIDATED + dangling + TAIL)
    with pytest.raises(fw.FrictionWriteError, match=r"no live deferral of 'src/cli/\*\*' to keep"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", keep=["src/cli/**"])
    with pytest.raises(fw.FrictionWriteError, match="answers nothing"):
        fw.plan_revalidate(repo.root, "guide", outcome="updated", keep=["record:COR-050"])
    plan = fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW)
    assert not any("COR-050" in item for item in plan.items)
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
    assert f"+++ b/{af.FOLDER}/" in result.output  # the diff comes before the confirmation
    deferred = _own_entry(repo)["revalidated"]["deferred"]
    assert deferred == [{"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "cli"}]


# --- defer --------------------------------------------------------------------------------


def test_defer_adds_a_sorted_entry_and_leaves_at_as_it_was(repo: AdopterRepo) -> None:
    existing = (
        "      deferred:\n      - anchor: {kind: path, value: src/core/**}\n        reason: core\n"
    )
    _put(repo, HEAD + REVALIDATED + existing + TAIL)
    plan = fw.plan_defer(repo.root, "guide", anchor="path:src/cli/**", reason="the redesign")
    fw.write(plan)
    assert _read(repo) == ANSWERED
    assert _own_entry(repo)["revalidated"] == {
        "at": "2026-10-01T09:00:00Z",
        "outcome": "unchanged",
        "unchanged-because": "the CLI surface is as described",
        "deferred": [
            {"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "the redesign"},
            {"anchor": {"kind": "path", "value": "src/core/**"}, "reason": "core"},
        ],
    }
    assert plan.target == "answers[docs/guide.md].revalidated.deferred"
    assert "at: not changed — a deferral is not a revalidation" in plan.items
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
    assert _read(repo) == ANSWERED


def test_defer_rewords_a_reason_and_the_same_reason_writes_nothing(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    fw.write(fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="first"))
    again = fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="  first ")
    assert not again.changes and "already deferred with this reason" in (again.unchanged or "")
    reworded = fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="second")
    assert any("keeps its deferral point" in item for item in reworded.items)
    fw.write(reworded)
    assert _own_entry(repo)["revalidated"]["deferred"] == [
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

    (repo.root / af.path_of(_own_name(repo))).unlink()  # the deferral taken back
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
    status_lines = written.split(HEAD, 1)[1].split(TAIL, 1)[0]
    assert status_lines.splitlines()[0] == "    last-check:"
    assert written.startswith(HEAD) and written.endswith(TAIL)
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
    with pytest.raises(fw.FrictionWriteError, match="no anchors or live deferrals"):
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


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            ("defer", "guide", "--anchor", "src/cli/**", "--reason", "the redesign"), id="defer"
        ),
        pytest.param(
            ("revalidate", "guide", "--outcome", "unchanged", "--because", "v2 is internal"),
            id="revalidate",
        ),
    ],
)
def test_without_consent_an_answer_is_refused_with_no_ready_made_yes(
    repo: AdopterRepo, command: tuple[str, ...]
) -> None:
    """An answer may be a person's decision (COR-050 point 3): the refusal names the
    dry run and says what `--yes` does, and prints no command that writes."""
    _put(repo, GUIDE)
    own = f"{af.FOLDER}/{_own_name(repo)}"
    result = _cli(*command)
    assert result.exit_code == 1
    rerun = fw.command_line("pkit", "friction", *command)
    refusal = (
        f"refusing to write {own}, the answer on {GUIDE_PATH}, without consent: stdin is not a "
        "terminal and --yes was not given (COR-050 point 13). Nothing was written.\n"
        "To see the change first, run:\n"
        f"  {rerun} --dry-run\n"
        "`--yes` writes without asking. An answer on an artefact may be a person's decision "
        "(COR-050 point 3).\n"
    )
    assert result.output[-len(refusal) :] == refusal
    assert f"{rerun} --yes" not in result.output
    assert not any(line.strip().endswith("--yes") for line in result.output.splitlines())
    assert _read(repo) == ANSWERED


def test_without_consent_record_status_refuses_and_names_the_command(repo: AdopterRepo) -> None:
    _commit_base(repo)
    repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})
    written = _read(repo)
    result = _cli("record-status", "guide")
    assert result.exit_code == 1
    assert result.output.endswith(
        "refusing to write docs/guide.md without consent: stdin is not a terminal and --yes "
        "was not given (COR-050 point 13). Nothing was written.\n"
        "To see the change first, run:\n"
        "  pkit friction record-status guide --dry-run\n"
        "To consent non-interactively, run:\n"
        "  pkit friction record-status guide --yes\n"
    )
    assert _read(repo) == written


def test_dry_run_shows_the_diff_and_writes_nothing(repo: AdopterRepo) -> None:
    _put(repo, GUIDE)
    own = f"{af.FOLDER}/{_own_name(repo)}"
    written = _read(repo, own)
    result = _cli("defer", "guide", "--anchor", "src/cli/**", "--reason", "later", "--dry-run")
    assert result.exit_code == 0, result.output
    assert f"Writes answers[docs/guide.md].revalidated.deferred in {own}" in result.output
    assert "+      deferred:" in result.output
    assert "Dry run: nothing written." in result.output
    assert (_read(repo), _read(repo, own)) == (ANSWERED, written)


def test_a_terminal_confirms_after_the_diff_and_declining_writes_nothing(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _put(repo, GUIDE)
    own = f"{af.FOLDER}/{_own_name(repo)}"
    written = _read(repo, own)
    monkeypatch.setattr(fw, "interactive", lambda: True)
    declined = _cli("defer", "guide", "--anchor", "src/cli/**", "--reason", "later", input="n\n")
    assert declined.exit_code == 1 and f"Write this to {own}?" in declined.output
    assert _read(repo, own) == written
    accepted = _cli("defer", "guide", "--anchor", "src/cli/**", "--reason", "later", input="y\n")
    assert accepted.exit_code == 0
    assert "Wrote answers[docs/guide.md].revalidated.deferred" in accepted.output
    assert _read(repo, own) != written and _read(repo) == ANSWERED


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
      revalidated:
        at: 2026-10-01T09:00:00Z
        outcome: updated
beta:
  title: Beta
  pkit:
    friction:
      anchors: {path: [src/core/**]}
      revalidated:
        at: 2026-10-01T09:00:00Z
        outcome: updated
---

## alpha

Alpha body.

## beta

Beta body.
"""


#: Each entry's revalidation in `COLLECTION`, as its block wrote it.
_ENTRY_REVALIDATED = (
    "      revalidated:\n        at: 2026-10-01T09:00:00Z\n        outcome: updated\n"
)


def test_an_entry_is_answered_alone_in_its_collection(repo: AdopterRepo) -> None:
    _put(repo, COLLECTION, "docs/rules.md")
    written = _read(repo, "docs/rules.md")
    fw.write(fw.plan_defer(repo.root, "docs/rules.md#alpha", anchor="src/cli/**", reason="x"))
    assert written == COLLECTION.replace(_ENTRY_REVALIDATED, "")
    assert _read(repo, "docs/rules.md") == written
    # Each entry is answered in an answer file of its own here (`answers_in_files`).
    (alpha,) = _entries_of(repo, "docs/rules.md#alpha")
    assert alpha["revalidated"] == {
        "at": "2026-10-01T09:00:00Z",
        "outcome": "updated",
        "deferred": [{"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "x"}],
    }
    (beta,) = _entries_of(repo, "docs/rules.md#beta")
    assert "deferred" not in beta["revalidated"]
    assert _validation_errors(repo) == []


def test_a_rule_is_answered_by_its_place_in_its_rule_set(repo: AdopterRepo) -> None:
    _put(repo, RULE_SET, RULE_SET_PATH)
    plan = fw.plan_defer(repo.root, "RS-CMN-001", anchor="COR-050", reason="being amended")
    assert plan.artefact == "docs/rule-sets/cmn.md#RS-CMN-001"
    fw.write(plan)
    assert _read(repo, RULE_SET_PATH) == RULE_SET.replace(
        "        revalidated:\n          at: 2026-10-01T09:00:00Z\n          outcome: updated\n", ""
    )
    assert _own_entry(repo, plan.artefact)["revalidated"]["deferred"] == [
        {"anchor": {"kind": "record", "value": "COR-050"}, "reason": "being amended"}
    ]


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
    """`record-status` writes the block, and never one validation would refuse."""
    broken = ANSWERED.replace("    anchors:\n", "    anchor-typo: 1\n    anchors:\n")
    _commit_base(repo, broken)
    with pytest.raises(fw.FrictionWriteError, match="would not validate"):
        fw.plan_record_status(repo.root, "guide")
    assert _read(repo) == broken


def test_a_reason_for_no_anchors_beside_anchors_is_not_written_over(repo: AdopterRepo) -> None:
    """Validation refuses `unanchored-because` beside anchors (COR-050 point 12), so a
    writer of the block, reading its result back, refuses to write over the pair."""
    beside = ANSWERED.replace("    anchors:\n", "    unanchored-because: Stale.\n    anchors:\n")
    _commit_base(repo, beside)
    with pytest.raises(fw.FrictionWriteError, match="stands beside anchors"):
        fw.plan_record_status(repo.root, "guide")
    assert _read(repo) == beside


# --- line endings ------------------------------------------------------------------------------


def _crlf(text: str) -> str:
    """`text` as a clone with `core.autocrlf=true` checks it out: every line ending `\\r\\n`."""
    return text.replace("\n", "\r\n")


#: Each writer's plan, by its command's name.
_PLANNERS: dict[str, Callable[..., fw.Plan]] = {
    "revalidate": fw.plan_revalidate,
    "defer": fw.plan_defer,
    "record-status": fw.plan_record_status,
}


@pytest.mark.parametrize(
    ("rel", "text", "command", "reference", "options"),
    [
        pytest.param(
            GUIDE_PATH,
            GUIDE,
            "revalidate",
            "guide",
            {"outcome": "unchanged", "because": "the change is internal", "now": NOW},
            id="document-revalidate",
        ),
        pytest.param(
            GUIDE_PATH,
            GUIDE,
            "defer",
            "guide",
            {"anchor": "src/cli/**", "reason": "later"},
            id="document-defer",
        ),
        pytest.param(GUIDE_PATH, GUIDE, "record-status", "guide", {}, id="document-record-status"),
        pytest.param(
            "docs/rules.md",
            COLLECTION,
            "revalidate",
            "docs/rules.md#beta",
            {"outcome": "updated", "now": NOW},
            id="entry-revalidate",
        ),
        pytest.param(
            RULE_SET_PATH,
            RULE_SET,
            "defer",
            "RS-CMN-001",
            {"anchor": "COR-050", "reason": "amended"},
            id="rule-defer",
        ),
        pytest.param(
            RULE_SET_PATH,
            RULE_SET,
            "revalidate",
            "RS-CMN-001",
            {"outcome": "unchanged", "because": "the record's amendment is editorial", "now": NOW},
            id="rule-revalidate",
        ),
    ],
)
def test_a_crlf_file_is_written_back_with_crlf_byte_for_byte(
    repo: AdopterRepo,
    rel: str,
    text: str,
    command: str,
    reference: str,
    options: dict[str, Any],
) -> None:
    """The write a writer plans for the `\\n` file, planned for its `\\r\\n` twin: the
    same key, the same lines, and every line ending `\\r\\n` — each other byte as it was.
    A writer of an answer file writes the same answer file for both, and leaves the
    artefact's `\\r\\n` file as it was."""
    _put(repo, text, rel)
    repo.commit("base", files=None, date=HISTORY_EPOCH)  # record-status reads HEAD
    at_head = _read(repo, rel)
    lf = _PLANNERS[command](repo.root, reference, **options)
    assert lf.changes

    _put(repo, _crlf(text), rel)
    written = _read(repo, rel)
    assert written == _crlf(at_head)
    crlf = _PLANNERS[command](repo.root, reference, **options)
    fw.write(crlf)

    if crlf.answer_file:
        assert _read(repo, rel) == written
        assert crlf.after == lf.after
    else:
        assert _read(repo, rel) == _crlf(lf.after)
        assert crlf.before == written
    assert (crlf.target, crlf.first_line, crlf.last_line, crlf.items) == (
        lf.target,
        lf.first_line,
        lf.last_line,
        lf.items,
    )
    assert _validation_errors(repo) == []


def test_a_link_planted_beside_the_file_takes_no_write(repo: AdopterRepo, tmp_path: Path) -> None:
    """The rewrite goes through a temporary file of a fresh name: a link a branch plants
    where an older writer put its temporary file leads nowhere."""
    _put(repo, GUIDE)
    own = f"{af.FOLDER}/{_own_name(repo)}"
    outside = tmp_path / "outside.txt"
    (repo.root / f"{own}.pkit-tmp").symlink_to(outside)
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="updated", now=NOW))
    assert not outside.exists()
    assert not (repo.root / own).is_symlink()
    assert "outcome: updated" in _read(repo, own)
    assert sorted(p.name for p in (repo.root / af.FOLDER).iterdir()) == [
        af.name_of(own),
        f"{af.name_of(own)}.pkit-tmp",
    ]


def test_a_file_mixing_line_endings_is_refused_and_left_as_it_is(repo: AdopterRepo) -> None:
    mixed = _crlf(GUIDE).replace("\r\n", "\n", 1)
    _put(repo, mixed)
    for plan in (
        lambda: fw.plan_defer(repo.root, "guide", anchor="src/cli/**", reason="later"),
        lambda: fw.plan_revalidate(repo.root, "guide", outcome="updated"),
    ):
        with pytest.raises(fw.FrictionWriteError, match=f"{GUIDE_PATH} mixes line endings"):
            plan()
    assert _read(repo) == mixed


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
    # The block always holds an answer, so the writers write in it: one that holds none
    # gets its answers in an answer file (COR-062 point 1; `test_friction_write_answer_files`).
    if not revalidated or rng.random() < 0.5:
        chosen = rng.sample(carried, rng.randint(1, len(carried)))
        revalidated["deferred"] = [
            {"anchor": {"kind": k, "value": v}, "reason": rng.choice(AWKWARD)} for k, v in chosen
        ]
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


class _RandomWrite(NamedTuple):
    """One random write: the writer's command and its arguments, the entry's `revalidated`
    it leaves (the model), and the clock after it."""

    command: str
    arguments: dict[str, Any]
    revalidated: dict[str, Any]
    now: datetime


def _random_write(
    rng: random.Random,
    context: str,
    anchors: Mapping[str, Sequence[str]],
    revalidated: dict[str, Any],
    now: datetime,
) -> _RandomWrite:
    """A deferral of one carried anchor, or a revalidation keeping some of the deferrals,
    each text an awkward one ending in `context`; `revalidated` is the model before it."""
    if rng.random() < 0.5:
        kind, value = rng.choice([(k, v) for k, values in anchors.items() for v in values])
        reason = f"{rng.choice(AWKWARD)} {context}"
        entries = [
            e
            for e in revalidated.get("deferred", [])
            if (e["anchor"]["kind"], e["anchor"]["value"]) != (kind, value)
        ]
        entry = {"anchor": {"kind": kind, "value": value}, "reason": reason.strip()}
        return _RandomWrite(
            "defer",
            {"anchor": f"{kind}:{value}", "reason": reason},
            {**revalidated, "deferred": _sorted_deferrals([*entries, entry])},
            now,
        )
    outcome = rng.choice(("updated", "unchanged"))
    because = f"{rng.choice(AWKWARD)} {context}" if outcome == "unchanged" else None
    keep = [e for e in revalidated.get("deferred", []) if rng.random() < 0.5]
    now += timedelta(minutes=1)
    model: dict[str, Any] = {"at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "outcome": outcome}
    if because is not None:
        model["unchanged-because"] = because.strip()
    if keep:
        model["deferred"] = _sorted_deferrals(keep)
    arguments = {
        "outcome": outcome,
        "because": because,
        "keep": [f"{e['anchor']['kind']}:{e['anchor']['value']}" for e in keep],
        "now": now,
    }
    return _RandomWrite("revalidate", arguments, model, now)


#: The random-writes test's seeds: 40 random documents, each answered four times.
SEEDS = range(40)

#: The seeds that take the round trip through the repository (#2309). Between them they hold
#: a document and a collection entry, block and flow style, a block with a revalidation and
#: one without, and deferrals and revalidations, each revalidation keeping a deferral. Every
#: other seed takes the answer files' pure layer, which starts no process.
ROUND_TRIP_SEEDS = (7, 10, 14)


# Some seconds a seed: its writes start about a hundred git processes, in the writers and in
# validation, which read the repository.
@pytest.mark.parametrize("seed", ROUND_TRIP_SEEDS)
def test_written_answers_read_back_identically_and_validate(repo: AdopterRepo, seed: int) -> None:
    """The round trip through the repository: a random document's answers are taken into an
    answer file of the change's own, then written four times at random by the writers. The
    artefact's file stays byte for byte, the answer file reads back as the model, and
    validation passes."""
    rng = random.Random(seed)
    text, reference, carrier_keys = _random_document(rng)
    _put(repo, text, "docs/doc.md")
    location = "docs/doc.md" if not carrier_keys else reference
    anchors = _block(repo, location)["anchors"]
    revalidated: dict[str, Any] = copy.deepcopy(_own_entry(repo, location).get("revalidated") or {})
    written = _read(repo, "docs/doc.md")
    now = NOW
    for step in range(4):
        write = _random_write(rng, f"{seed}-{step}", anchors, revalidated, now)
        if write.command == "defer":
            plan = fw.plan_defer(repo.root, reference, **write.arguments)
        else:
            plan = fw.plan_revalidate(repo.root, reference, **write.arguments)
        revalidated, now = write.revalidated, write.now
        fw.write(plan)

        context = f"seed {seed}, step {step}:\n{text}\n---->\n{plan.after}"
        assert _read(repo, "docs/doc.md") == written, context
        assert _own_entry(repo, location).get("revalidated") == revalidated, context
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


def test_written_answers_read_back_identically_and_validate_in_the_pure_layer(
    repo: AdopterRepo,
) -> None:
    """Every other seed, through the answer files' pure layer, which starts no process: the
    document is read as discovery reads it, and each of the four writes is the change's own
    answer file as the writers write it (`answer_file_text`). That file reads back as the
    model, departs in nothing from the answer files' schema, and every answer in it is live.
    The artefact's file is the repository's to keep: the round trip checks it."""
    schema, why = af.load_schema(repo.root)
    assert schema is not None, why
    (place,) = discover_artefacts(repo.root).places
    name = "20261005T100000Z-00000000.yaml"
    for seed in (s for s in SEEDS if s not in ROUND_TRIP_SEEDS):
        rng = random.Random(seed)
        text, reference, carrier_keys = _random_document(rng)
        location = "docs/doc.md" if not carrier_keys else reference
        artefacts, _why = parse_artefacts("docs/doc.md", place, text)
        (artefact,) = [a for a in artefacts if a.location == location]
        block = cast(Mapping[str, Any], artefact.friction)
        declared = {Anchor(k, v) for k, values in artefact.anchors.items() for v in values}
        # The block's answers, taken into the change's own answer file before the first write.
        revalidated: dict[str, Any] = copy.deepcopy(block["revalidated"])
        now = NOW
        for step in range(4):
            write = _random_write(rng, f"{seed}-{step}", block["anchors"], revalidated, now)
            revalidated, now = write.revalidated, write.now
            entry = {
                af.ARTEFACT_KEY: location,
                af.REVALIDATED_KEY: fw.ordered_revalidation(revalidated),
            }
            after, _first, _last = fw.answer_file_text([entry], 0)
            found = af.read_answer_file(name, after.encode("utf-8"))

            context = f"seed {seed}, step {step}:\n{text}\n---->\n{after}"
            assert found.document == {af.ANSWERS_KEY: [entry]}, context
            assert af.shape_findings(found, schema) == [], context
            judged = af.liveness(found.entries, {name}, lambda _reader, _named: True)
            assert judged.revalidations == (found.entries if "at" in revalidated else ()), context
            assert [d.anchor for _e, d in judged.deferrals] == [
                Anchor(e["anchor"]["kind"], e["anchor"]["value"])
                for e in revalidated.get("deferred", [])
            ], context
            assert {d.anchor for _e, d in judged.deferrals} <= declared, context


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
    _commit_base(repo, HEAD + REVALIDATED + role_block + TAIL)
    fw.write(fw.plan_record_status(repo.root, "guide"))
    text = _read(repo)
    assert role_block in text
    assert "    last-check:\n" in text


# --- where a block is written: under the keys discovery reads (#1750) -----------------


ENTRY_PATH = ("pkit", "friction", "revisited")


@pytest.mark.parametrize(
    ("front_matter", "keys", "found"),
    [
        # Written apart, read alike: `0x1` is read as `1`, and is the key found for it.
        ("0x1: {pkit: {friction: {revisited: [read]}}}\n", ("1", *ENTRY_PATH), "[read]"),
        # Written alike, read apart: the key found is the one read under its text, never
        # an earlier key written the same.
        (
            "true: {pkit: {friction: {revisited: [dropped]}}}\n"
            "'true': {pkit: {friction: {revisited: [read]}}}\n'True': 0\n",
            ("true", *ENTRY_PATH),
            "[read]",
        ),
        (
            "0x1: {pkit: {friction: {revisited: [dropped]}}}\n"
            "'0x1': {pkit: {friction: {revisited: [read]}}}\n'1': 0\n",
            ("0x1", *ENTRY_PATH),
            "[read]",
        ),
        (
            "!!null pkit: {friction: {revisited: [dropped]}}\n"
            "pkit: {friction: {revisited: [read]}}\n",
            ENTRY_PATH,
            "[read]",
        ),
        (
            "pkit:\n  friction:\n    !!null revisited: [dropped]\n    revisited: [read]\n",
            ENTRY_PATH,
            "[read]",
        ),
        # Two keys read alike off the path leave it as it is.
        (
            "1: one\n'1': two\npkit: {friction: {revisited: [read]}}\n",
            ENTRY_PATH,
            "[read]",
        ),
        # Two keys read alike on the path: which one holds the list cannot be told.
        (
            "1: {pkit: {friction: {revisited: [dropped]}}}\n"
            "'1': {pkit: {friction: {revisited: [read]}}}\n",
            ("1", *ENTRY_PATH),
            "cannot be told apart: two keys on its path are read as `1`",
        ),
        (
            "'1': {pkit: {friction: {revisited: [dropped]}}}\n"
            "0x1: {pkit: {friction: {revisited: [read]}}}\n",
            ("1", *ENTRY_PATH),
            "cannot be told apart: two keys on its path are read as `1`",
        ),
        # A merge key on the path, `<<` or tagged, reads keys written elsewhere as its own.
        (
            "pkit:\n  friction:\n    !!merge revisited: {anchors: x, revisited: [read]}\n",
            ENTRY_PATH,
            "is reached through a merge key, which reads keys written elsewhere as its "
            "mapping's own",
        ),
        (
            "pkit:\n  <<: {friction: {revisited: [read]}}\n",
            ENTRY_PATH,
            "is reached through a merge key, which reads keys written elsewhere as its "
            "mapping's own",
        ),
        ("pkit: {friction: {}}\n", ENTRY_PATH, "is not written under a key read as `revisited`"),
    ],
)
def test_a_key_is_found_as_discovery_reads_it(
    front_matter: str, keys: tuple[str, ...], found: str
) -> None:
    """`key_span` finds each step under the key discovery reads it by, rendered as text,
    or says why it cannot be told (#1750)."""
    span = fw.key_span(front_matter, keys)
    if isinstance(span, str):
        assert span == found
    else:
        assert front_matter[span.start : span.end] == f"{keys[-1]}: {found}"
