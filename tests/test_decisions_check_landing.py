"""`pkit decisions check-landing`: what a change's merge would land (COR-066, ADR-081).

Each test builds a repository whose `main` holds the base, cuts a branch `change`, and
commits there. Where the base moved on, `main` gains a commit after the branch left it.
Only commits are read, so nothing a test leaves in the working tree counts, the working
tree's copy of the synced-copy test aside.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from project_kit import commit_contributions, decisions_check_diff, install, lifecycle_ownership
from project_kit import decisions_landing as landing
from project_kit import project_config as pc
from project_kit.cli import main
from project_kit.decisions import OVERLAY_RELPATH
from project_kit.friction_check import printable
from project_kit.friction_git import CommitTree, FrictionCheckError
from tests.adopter_repo import GitRepo

REPO = Path(__file__).resolve().parents[1]
CONFIG = ".pkit/project/config.yaml"
MANIFEST = ".pkit/manifest.yaml"
OWNERSHIP = ".pkit/lifecycle/ownership.py"
PROJECT = ".pkit/decisions/project"
SEED = f"{PROJECT}/README.md"
RECORD = f"{PROJECT}/PRJ-001-a.md"
OTHER = f"{PROJECT}/PRJ-002-b.md"
CORE = ".pkit/decisions/core/COR-001-a.md"
RULES = "docs/rule-sets/cmn.md"
ON = "decisions:\n  refuse-proposals: true\n"
OFF = "decisions:\n  refuse-proposals: false\n"
FIRST, SECOND, THIRD = "RS-CMN-001", "RS-CMN-002", "RS-CMN-003"


def _record(status: str = "accepted", *, record_id: str = "PRJ-001", text: str = "Text") -> str:
    return (
        f"---\nid: {record_id}\ntitle: A record\nstatus: {status}\ndate: 2026-10-13\n"
        f"author: t\n---\n\n## Context\n\nWhy.\n\n## Decision\n\nWhat.\n\n"
        f"### 1. Point 1\n\n{text} of 1.\n\n## Rationale\n\nBecause.\n"
    )


def _other(status: str = "accepted") -> str:
    return _record(status, record_id="PRJ-002")


def _rules(
    rules: Mapping[str, str | None],
    *,
    name: str = "CMN",
    text: Mapping[str, str] | None = None,
) -> str:
    """A rule-set file holding `rules`: each id with its status, `None` writing none, and
    each section's text from `text`."""
    entries = "".join(
        f"  {rule_id}: {{}}\n" if status is None else f"  {rule_id}:\n    status: {status}\n"
        for rule_id, status in rules.items()
    )
    sections = "".join(
        f"## {rule_id} — A rule\n\n{(text or {}).get(rule_id, 'The statement')}.\n\n"
        for rule_id in rules
    )
    head = f"rule-set: {name}\nversion: 1.0.0\nscope:\n  - docs/**\nrules:\n{entries}"
    return f"---\n{head}---\n\n# Rules\n\n{sections}"


def _capability_manifest(origin: str | None) -> str:
    """A manifest registering the capability `cap`, with `origin` written where given."""
    written = "" if origin is None else f"    origin: {origin}\n"
    return f"components:\n  - kind: capability\n    name: cap\n{written}"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """A repository on `main` with no commit yet, the command's working directory."""
    made = GitRepo.init(tmp_path / "work")
    monkeypatch.chdir(made.root)
    monkeypatch.delenv("PKIT_CHECK_BASE", raising=False)
    return made


def _branch(repo: GitRepo, files: Mapping[str, str] | None = None) -> str:
    """`main` holds `files` at the branch point, and the branch `change` leaves it."""
    tip = repo.commit("start", {SEED: "Records.\n", **(files or {})})
    repo.checkout("change", create=True)
    return tip


def _on_main(repo: GitRepo, files: Mapping[str, str | None]) -> str:
    """Another change lands `files` on `main` after `change` left it."""
    repo.checkout("main")
    tip = repo.commit("another change", files)
    repo.checkout("change")
    return tip


def _run(*args: str, base: str | None = "main") -> Result:
    named = [] if base is None else ["--base", base]
    return CliRunner().invoke(main, ["decisions", "check-landing", *named, *args])


def _document(*args: str, base: str = "main") -> dict[str, Any]:
    return json.loads(_run("--json", *args, base=base).stdout)


def _names(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    return [entry["name"] for entry in entries]


def _commits(found: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    """The commits that accepted `name`, from the list."""
    (entry,) = [item for item in found["accepted"] if item["name"] == name]
    return entry["commits"]


def _before(commit: Mapping[str, Any]) -> list[str]:
    return [work["commit"] for work in commit["before"]]


def _commit_bytes(repo: GitRepo, rel: str, raw: bytes) -> str:
    path = repo.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    repo.git("add", "--", rel)
    repo.git("commit", "-q", "-m", f"write {rel}")
    return repo.head()


def _ownership() -> str:
    """The shipped synced-copy test, for a tree that holds it."""
    return (REPO / OWNERSHIP).read_text(encoding="utf-8")


# --- the refusal and the key -----------------------------------------------------------


def test_a_record_added_proposed_is_refused_with_the_key_on(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("add", {RECORD: _record("proposed")})

    result = _run()

    assert result.exit_code == 1, result.output
    assert "PRJ-001" in result.output and "added proposed" in result.output
    assert "Refused: a proposal would land on the default branch." in result.output


def test_an_accepted_record_set_back_is_reported_with_what_it_was(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RECORD: _record("accepted")})
    repo.commit("back", {RECORD: _record("proposed")})

    found = _document()

    assert found["refuses"] is True
    assert found["proposals"] == [
        {"kind": "record", "name": "PRJ-001", "path": RECORD, "was": "accepted", "why": None}
    ]


def test_with_the_key_off_the_check_reports_passes_and_says_why(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("add", {RECORD: _record("proposed")})

    result = _run()

    assert result.exit_code == 0, result.output
    assert "PRJ-001" in result.output
    assert "Passes: the refusal is off" in result.output


def test_a_record_proposed_at_the_tip_too_blocks_nothing(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RECORD: _record("proposed")})
    repo.commit("edit", {RECORD: _record("proposed", text="Edited")})

    result = _run()

    assert result.exit_code == 0, result.output
    assert "No proposal would land." in result.output


def test_a_superseded_record_is_not_a_proposal(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("add", {RECORD: _record("superseded")})

    assert _run().exit_code == 0


def test_the_working_tree_is_never_read(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.write({RECORD: _record("proposed")})

    assert _run().exit_code == 0


def test_a_head_named_is_judged_rather_than_head(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    proposing = repo.commit("add", {RECORD: _record("proposed")})
    repo.commit("settled", {RECORD: _record("accepted")})

    assert _run().exit_code == 0
    assert _run("--head", proposing).exit_code == 1


def test_the_base_may_be_named_by_the_override(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("add", {RECORD: _record("proposed")})
    monkeypatch.setenv("PKIT_CHECK_BASE", "main")

    assert _run(base=None).exit_code == 1


def test_the_key_is_read_at_the_tip_so_turning_it_off_counts_once_landed(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("off", {CONFIG: OFF, RECORD: _record("proposed")})

    result = _run()

    assert result.exit_code == 1, result.output
    assert "from True to False" in result.output
    assert _document()["key"]["change"] == {"tip": True, "landing": False}


def test_turning_the_key_on_refuses_nothing_yet_and_lists_the_bases_proposals(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    repo.commit("on", {CONFIG: ON, OTHER: _other("proposed")})

    found = _document()

    assert found["refuses"] is False and found["key"]["refusal_on"] is False
    assert found["key"]["change"] == {"tip": False, "landing": True}
    assert _names(found["proposals"]) == ["PRJ-002"]
    assert _names(found["default_branch_proposals"]) == ["PRJ-001"]


def test_the_bases_proposals_are_listed_only_on_the_run_that_turns_the_key_on(
    repo: GitRepo,
) -> None:
    _branch(repo, {CONFIG: ON, RECORD: _record("proposed")})
    repo.commit("work", {"a.txt": "a\n"})

    assert _document()["default_branch_proposals"] == []


def test_a_landing_elsewhere_lists_no_proposals_of_the_base(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    repo.git("branch", "integration")
    repo.commit("on", {CONFIG: ON})

    assert _document(base="integration")["default_branch_proposals"] == []


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("decisions: [\n", "reads as False"),
        ("decisions:\n  refuse-proposals: 1\n", "1 is not a boolean"),
    ],
    ids=["a file that does not parse", "a value the key does not take"],
)
def test_what_does_not_read_at_the_tip_warns_and_reads_off(
    repo: GitRepo, text: str, said: str
) -> None:
    _branch(repo, {CONFIG: text})
    repo.commit("add", {RECORD: _record("proposed")})

    result = _run()

    assert result.exit_code == 0, result.output
    assert said in result.stderr
    assert said in _document()["key"]["warning"]


def test_a_misspelt_key_reads_as_absent(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: "decisions:\n  refuse-proposal: true\n"})
    repo.commit("add", {RECORD: _record("proposed")})

    found = _document()

    assert found["key"]["value"] is False and found["key"]["warning"] is None


# --- which base is the default branch --------------------------------------------------


def _remote(repo: GitRepo, branch: str, commit: str) -> None:
    repo.git("remote", "add", "origin", "https://example.invalid/x.git", check=False)
    repo.git("update-ref", f"refs/remotes/origin/{branch}", commit)


def test_a_landing_on_another_branch_refuses_nothing_and_gives_the_list(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.git("branch", "integration")
    repo.commit("add", {RECORD: _record("proposed"), OTHER: _other("accepted")})

    result = _run(base="integration")

    assert result.exit_code == 0, result.output
    assert "is not the default branch" in result.output
    found = _document(base="integration")
    assert found["default_branch"]["is_base"] is False
    assert _names(found["proposals"]) == ["PRJ-001"]
    assert _names(found["accepted"]) == ["PRJ-002"]


def test_a_base_named_only_by_a_commit_counts_as_the_default_branch(repo: GitRepo) -> None:
    tip = _branch(repo, {CONFIG: ON})
    repo.commit("add", {RECORD: _record("proposed")})

    assert _run(base=tip).exit_code == 1


def test_a_remotes_copy_counts_by_its_branchs_name(repo: GitRepo) -> None:
    tip = _branch(repo, {CONFIG: ON})
    repo.commit("add", {RECORD: _record("proposed")})
    _remote(repo, "main", tip)
    _remote(repo, "integration", tip)

    assert _run(base="origin/main").exit_code == 1
    assert _run(base="origin/integration").exit_code == 0


@pytest.mark.parametrize(
    "named",
    [
        "origin/HEAD",
        "refs/remotes/origin/HEAD",
        "origin/main~0",
        "origin/main^{commit}",
        "refs/heads/main~0",
        "origin/integration~0",
    ],
)
def test_a_base_whose_name_is_no_branchs_counts_as_the_default_branch(
    repo: GitRepo, named: str
) -> None:
    tip = _branch(repo, {CONFIG: ON})
    repo.commit("add", {RECORD: _record("proposed")})
    _remote(repo, "main", tip)
    _remote(repo, "integration", tip)
    repo.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

    assert _run(base=named).exit_code == 1
    assert _document(base=named)["default_branch"]["is_base"] is True


@pytest.mark.parametrize(
    "reference",
    ["refs/remotes/gone/sub/feature", "refs/remotes/solo"],
    ids=["a remote not listed", "no remote at all"],
)
def test_a_tracking_name_no_remote_holds_counts_as_the_default_branch(
    repo: GitRepo, reference: str
) -> None:
    tip = _branch(repo, {CONFIG: ON})
    repo.commit("add", {RECORD: _record("proposed")})
    repo.git("update-ref", reference, tip)

    assert _run(base=reference).exit_code == 1


def test_a_declared_name_that_does_not_read_leaves_no_base_told_apart(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: f"{ON}repository:\n  default-branch: origin/trunk\n"})
    repo.git("branch", "trunk", "main")
    repo.commit("add", {RECORD: _record("proposed")})

    result = _run(base="trunk")

    assert result.exit_code == 1, result.output
    assert "'origin/trunk' is not a branch name" in result.stderr


def test_the_name_of_the_default_branch_is_the_tips(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: f"{ON}repository:\n  default-branch: trunk\n"})
    repo.git("branch", "trunk", "main")
    repo.commit("add", {RECORD: _record("proposed")})

    assert _run(base="trunk").exit_code == 1
    assert _run(base="main").exit_code == 0


def test_a_change_cannot_move_the_name_of_the_default_branch(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    moved = f"{ON}repository:\n  default-branch: other\n"
    repo.commit("add", {CONFIG: moved, RECORD: _record("proposed")})

    assert _run().exit_code == 1


# --- no answer -------------------------------------------------------------------------


def _no_answer(result: Result, said: str) -> None:
    assert result.exit_code == landing.NO_ANSWER_EXIT, result.output
    assert "No answer:" in result.stderr and said in result.stderr


def test_a_run_that_names_no_base_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})

    _no_answer(_run(base=None), "names no base")


def test_a_base_that_names_no_commit_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})

    _no_answer(_run(base="nowhere"), "does not resolve")


def test_a_head_that_names_no_commit_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})

    _no_answer(_run("--head", "nowhere"), "names no commit")


def test_a_head_named_like_a_commits_id_through_a_branch_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.git("branch", "abcdef1")

    _no_answer(_run("--head", "abcdef1"), "reads as a commit's id")


def test_a_head_that_shares_no_history_with_the_base_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.git("checkout", "-q", "--orphan", "apart")
    repo.commit("apart", {"a.txt": "a\n"})

    _no_answer(_run(), "share no history")


def test_no_project_tree_gives_no_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    _no_answer(_run(), "not in a project tree")


def test_with_no_answer_the_document_gives_only_why(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})

    result = _run("--json", base=None)

    assert result.exit_code == landing.NO_ANSWER_EXIT
    found = json.loads(result.stdout)
    assert set(found) == {"schema_version", "problem"}
    assert "names no base" in found["problem"]


def test_a_shallow_clone_gives_no_answer(
    repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _branch(repo)
    repo.commit("work", {"a.txt": "a\n"})
    shallow = tmp_path / "shallow"
    source = f"file://{repo.root}"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", "--branch", "change", source, str(shallow)],
        check=True,
    )
    monkeypatch.chdir(shallow)

    _no_answer(_run(base="origin/change"), "shallow")


@pytest.mark.parametrize("key", [ON, OFF], ids=["key on", "key off"])
def test_a_merge_that_conflicts_gives_no_answer_whatever_the_key(repo: GitRepo, key: str) -> None:
    _branch(repo, {CONFIG: key, RECORD: _record("proposed")})
    repo.commit("mine", {RECORD: _record("proposed", text="Mine")})
    _on_main(repo, {RECORD: _record("proposed", text="Theirs")})

    result = _run()

    _no_answer(result, RECORD)
    assert "merge the base into the change" in result.stderr


def test_a_git_that_cannot_merge_gives_no_answer(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("mine", {"a.txt": "a\n"})
    _on_main(repo, {"b.txt": "b\n"})

    def cannot(*_args: str) -> None:
        raise FrictionCheckError("`git merge-tree --write-tree` failed — it needs git 2.38.")

    monkeypatch.setattr(commit_contributions, "merge", cannot)

    _no_answer(_run(), "merge-tree")


def test_a_git_command_that_fails_gives_no_answer(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _branch(repo, {CONFIG: ON})

    def fails(*_args: str) -> None:
        raise FrictionCheckError("`git rev-parse` failed: a broken repository.")

    monkeypatch.setattr(landing, "run_git", fails)

    _no_answer(_run(), "a broken repository")


def test_a_copy_of_the_test_that_raises_on_loading_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.write({OWNERSHIP: "raise RuntimeError('broken copy')\n"})

    _no_answer(_run(), "broken copy")


def test_a_copy_that_raises_in_discoverys_run_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RULES: _rules({FIRST: "accepted"})})
    repo.write({OWNERSHIP: "raise RuntimeError('broken copy')\n"})

    _no_answer(_run(), "broken copy")


def test_a_copy_that_raises_when_asked_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RECORD: _record("accepted")})
    broken = "def is_synced_copy(root, path):\n    raise RuntimeError('broken answer')\n"
    repo.write({OWNERSHIP: broken})

    _no_answer(_run(), "broken answer")


def test_no_stand_in_root_gives_no_answer(repo: GitRepo, monkeypatch: pytest.MonkeyPatch) -> None:
    _branch(repo, {CONFIG: ON})
    repo.write({OWNERSHIP: _ownership()})

    def no_folder(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("no space left")

    monkeypatch.setattr(landing.tempfile, "TemporaryDirectory", no_folder)

    _no_answer(_run(), "no stand-in root can be made")


# --- what it cannot read counts as proposed --------------------------------------------


@pytest.mark.parametrize(
    ("raw", "why"),
    [
        (b"\xff\xfe not text", "not UTF-8"),
        (b"---\nid: [\n---\n\nBody.\n", "front matter does not read"),
        (_record("maybe").encode(), "'maybe' is not one a record has"),
        (_record("proposed").replace("status: proposed\n", "").encode(), "writes no status"),
    ],
    ids=["not text", "front matter that does not parse", "a status it has not", "no status"],
)
def test_a_record_it_cannot_read_counts_as_proposed_with_why(
    repo: GitRepo, raw: bytes, why: str
) -> None:
    _branch(repo, {CONFIG: ON})
    _commit_bytes(repo, RECORD, raw)

    found = _document()

    assert found["refuses"] is True
    (proposal,) = found["proposals"]
    assert proposal["path"] == RECORD and why in proposal["why"]


def test_a_record_it_cannot_read_at_both_states_blocks_nothing(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    _commit_bytes(repo, RECORD, b"\xff one")
    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--ff-only", "change")
    repo.checkout("second", create=True)
    _commit_bytes(repo, RECORD, b"\xff two")

    assert _document()["proposals"] == []


@pytest.mark.parametrize(
    ("status", "why"),
    [("maybe", "'maybe' is not one a rule has"), (None, "writes no status")],
    ids=["a status it has not", "no status"],
)
def test_a_rule_it_cannot_read_counts_as_proposed_with_why(
    repo: GitRepo, status: str | None, why: str
) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("add", {RULES: _rules({FIRST: status})})

    found = _document()

    (proposal,) = found["proposals"]
    assert proposal["kind"] == landing.RULE and proposal["name"] == FIRST
    assert why in proposal["why"]


def test_a_rule_entry_that_is_no_mapping_counts_as_proposed(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    text = _rules({FIRST: "accepted"}).replace(
        f"  {FIRST}:\n    status: accepted\n", f"  {FIRST}: x\n"
    )
    repo.commit("add", {RULES: text})

    found = _document()

    assert _names(found["proposals"]) == [FIRST]


@pytest.mark.parametrize("status", ["withdrawn", "superseded"])
def test_a_retired_rule_never_reads_as_proposed(repo: GitRepo, status: str) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("add", {RULES: _rules({FIRST: status})})

    assert _document()["proposals"] == []


def test_a_rule_set_file_the_reader_cannot_read_counts_as_one_proposal(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RULES: _rules({FIRST: "accepted", SECOND: "accepted"})})
    repo.commit("break", {RULES: "No front matter here.\n"})

    found = _document()

    (proposal,) = found["proposals"]
    assert proposal["kind"] == landing.RULE_SET_FILE and proposal["path"] == RULES
    assert found["refuses"] is True


@pytest.mark.parametrize(
    "held",
    [{}, {RULES: _rules({FIRST: "accepted"})}],
    ids=["a new file", "over an accepted rule"],
)
@pytest.mark.parametrize(
    "written",
    [f"rules:\n  - {FIRST}\n", "rules:\n", ""],
    ids=["a list", "no value", "no key"],
)
def test_a_rule_set_file_with_no_mapping_of_rules_counts_as_one_proposal(
    repo: GitRepo, held: Mapping[str, str], written: str
) -> None:
    _branch(repo, {CONFIG: ON, **held})
    body = f"## {FIRST} — A rule\n\nThe statement.\n"
    repo.commit("add", {RULES: f"---\nrule-set: CMN\nversion: 1.0.0\n{written}---\n\n{body}"})

    found = _document()

    (proposal,) = found["proposals"]
    assert proposal["kind"] == landing.RULE_SET_FILE and proposal["path"] == RULES
    assert "no mapping" in proposal["why"] and found["refuses"] is True


def test_an_empty_mapping_of_rules_holds_no_proposal(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("add", {RULES: "---\nrule-set: CMN\nversion: 1.0.0\nrules: {}\n---\n"})

    assert _document()["proposals"] == []


@pytest.mark.parametrize(
    "written",
    [
        f"  {FIRST}:\n    status: accepted\n    status: proposed\n",
        f"  {FIRST}:\n    status: accepted\n  {FIRST}:\n    status: proposed\n",
    ],
    ids=["a status", "a rule"],
)
def test_a_rule_set_file_that_writes_a_key_twice_counts_as_one_proposal(
    repo: GitRepo, written: str
) -> None:
    _branch(repo, {CONFIG: ON})
    text = _rules({FIRST: "accepted"}).replace(f"  {FIRST}:\n    status: accepted\n", written)
    repo.commit("add", {RULES: text})

    found = _document()

    (proposal,) = found["proposals"]
    assert proposal["kind"] == landing.RULE_SET_FILE and proposal["path"] == RULES
    assert "twice" in proposal["why"] and found["refuses"] is True


def test_a_rule_set_file_that_is_a_link_counts_as_one_proposal(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RULES: _rules({FIRST: "accepted"})})
    (repo.root / "docs/rule-sets/link.md").symlink_to("cmn.md")
    repo.commit("link")

    (proposal,) = _document()["proposals"]

    assert proposal["kind"] == landing.RULE_SET_FILE
    assert proposal["path"] == "docs/rule-sets/link.md"
    assert "link" in proposal["why"]


# --- pairing ---------------------------------------------------------------------------


def test_a_record_moved_is_paired_not_added(repo: GitRepo) -> None:
    moved = f"{PROJECT}/PRJ-001-moved.md"
    _branch(repo, {CONFIG: ON, RECORD: _record("proposed")})
    repo.rename(RECORD, moved)

    found = _document()

    assert found["proposals"] == [] and found["accepted"] == []


def test_a_record_moved_and_set_back_is_reported(repo: GitRepo) -> None:
    moved = f"{PROJECT}/PRJ-001-moved.md"
    _branch(repo, {CONFIG: ON, RECORD: _record("accepted")})
    repo.commit("move", {RECORD: None, moved: _record("proposed")})

    (proposal,) = _document()["proposals"]

    assert proposal["path"] == moved and proposal["was"] == "accepted"


def test_each_rule_of_a_shared_file_is_judged_on_its_own(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RULES: _rules({FIRST: "accepted", SECOND: "accepted"})})
    repo.commit("edit", {RULES: _rules({FIRST: "accepted", SECOND: "proposed", THIRD: "proposed"})})

    found = _document()

    assert [(item["name"], item["was"]) for item in found["proposals"]] == [
        (SECOND, "accepted"),
        (THIRD, None),
    ]


def test_a_rule_set_moved_whole_keeps_its_rules_paired(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RULES: _rules({FIRST: "proposed"})})
    repo.rename(RULES, "docs/rule-sets/moved.md")

    assert _document()["proposals"] == []


def test_a_rule_moved_to_another_set_is_new_and_judged_as_added(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RULES: _rules({FIRST: "accepted"})})
    other = "docs/rule-sets/oth.md"
    repo.commit(
        "move",
        {
            RULES: _rules({FIRST: "superseded"}),
            other: _rules({"RS-OTH-001": "proposed"}, name="OTH"),
        },
    )

    (proposal,) = _document()["proposals"]

    assert proposal["name"] == "RS-OTH-001" and proposal["was"] is None


# --- what the merge leaves as the tip holds it -----------------------------------------


def test_a_record_the_base_accepted_after_the_branch_left_is_not_refused(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, RECORD: _record("proposed")})
    repo.commit("work", {"a.txt": "a\n"})
    _on_main(repo, {RECORD: _record("accepted")})

    found = _document()

    assert found["proposals"] == [] and found["accepted"] == []


def test_a_landing_is_judged_at_the_merge_not_the_head(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("mine", {RECORD: _record("proposed")})
    _on_main(repo, {OTHER: _other("accepted")})

    found = _document()

    assert _names(found["proposals"]) == ["PRJ-001"]
    assert found["accepted"] == []


def test_a_head_that_descends_from_the_tip_lands_its_own_tree(repo: GitRepo) -> None:
    _branch(repo)
    head = repo.commit("work", {"a.txt": "a\n"})

    assert _document()["landing_tree"] == repo.git("rev-parse", f"{head}^{{tree}}").stdout.strip()


def test_a_merge_gives_the_tree_git_would_land(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("work", {"a.txt": "a\n"})
    tip = _on_main(repo, {"b.txt": "b\n"})

    found = _document()

    listed = repo.git("ls-tree", "--name-only", found["landing_tree"]).stdout.split()
    assert {"a.txt", "b.txt"} <= set(listed)
    assert found["base"]["tip"] == tip and found["base"]["fork"] != tip


# --- skipped where received ------------------------------------------------------------


def _adopter(files: Mapping[str, str] | None = None) -> dict[str, str]:
    return {OWNERSHIP: _ownership(), CONFIG: ON, **(files or {})}


def test_a_record_the_project_receives_is_skipped(repo: GitRepo) -> None:
    _branch(repo, _adopter())
    repo.commit("sync", {CORE: _record("proposed", record_id="COR-001")})

    assert _document()["proposals"] == []


def test_the_methodologys_source_judges_its_own_records(repo: GitRepo) -> None:
    _branch(repo, _adopter({"src/project_kit/__init__.py": ""}))
    repo.commit("add", {CORE: _record("proposed", record_id="COR-001")})

    assert _names(_document()["proposals"]) == ["COR-001"]


def test_a_method_rule_set_the_project_authors_is_judged(repo: GitRepo) -> None:
    method = ".pkit/rule-sets/cmn.md"
    _branch(repo, _adopter({"src/project_kit/__init__.py": ""}))
    repo.commit("add", {method: _rules({FIRST: "proposed"})})

    assert _names(_document()["proposals"]) == [FIRST]


def test_a_method_rule_set_the_project_receives_is_skipped(repo: GitRepo) -> None:
    method = ".pkit/rule-sets/cmn.md"
    _branch(repo, _adopter())
    repo.commit("sync", {method: _rules({FIRST: "proposed"})})

    assert _document()["proposals"] == []


def test_a_tree_with_no_test_skips_nothing_and_says_why(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON})
    repo.commit("add", {CORE: _record("proposed", record_id="COR-001")})

    found = _document()

    assert _names(found["proposals"]) == ["COR-001"]
    assert "holds no synced-copy test" in found["cannot_tell"][0]


CAPABILITY_RECORD = ".pkit/capabilities/cap/decisions/DEC-001-a.md"
CAPABILITY_RULES = ".pkit/capabilities/cap/rule-sets/cmn.md"


def _capability_record() -> str:
    return _record("proposed", record_id="DEC-001")


def test_a_kit_shipped_capabilitys_record_is_skipped(repo: GitRepo) -> None:
    _branch(repo, _adopter({MANIFEST: _capability_manifest("kit-shipped")}))
    repo.commit("sync", {CAPABILITY_RECORD: _capability_record()})

    assert _document()["proposals"] == []


def test_an_incubated_capabilitys_record_is_judged(repo: GitRepo) -> None:
    _branch(repo, _adopter({MANIFEST: _capability_manifest("incubated-in-repo")}))
    repo.commit("add", {CAPABILITY_RECORD: _capability_record()})

    assert _names(_document()["proposals"]) == ["DEC-001"]


def test_a_component_the_change_installs_is_skipped_and_the_readings_disagree(
    repo: GitRepo,
) -> None:
    _branch(repo, _adopter())
    repo.commit(
        "install",
        {MANIFEST: _capability_manifest("kit-shipped"), CAPABILITY_RECORD: _capability_record()},
    )

    found = _document()

    assert found["proposals"] == []
    assert found["received_disagreements"] == [CAPABILITY_RECORD]


def test_a_change_cannot_skip_its_own_proposal_by_breaking_the_manifest(repo: GitRepo) -> None:
    _branch(repo, _adopter({MANIFEST: _capability_manifest("incubated-in-repo")}))
    repo.commit("break", {MANIFEST: "components: [\n", CAPABILITY_RECORD: _capability_record()})

    found = _document()

    assert _names(found["proposals"]) == ["DEC-001"]
    assert any("does not read" in why or "no capability" in why for why in found["cannot_tell"])


def test_a_manifest_that_lists_no_components_counts_as_one_that_does_not_read(
    repo: GitRepo,
) -> None:
    _branch(repo, _adopter({MANIFEST: _capability_manifest("incubated-in-repo")}))
    repo.commit("break", {MANIFEST: "components: 1\n", CAPABILITY_RECORD: _capability_record()})

    found = _document()

    assert _names(found["proposals"]) == ["DEC-001"]
    assert any("no list" in why for why in found["cannot_tell"])


def test_an_unknown_origin_skips_nothing_and_says_why(repo: GitRepo) -> None:
    _branch(repo, _adopter({MANIFEST: _capability_manifest("from-the-moon")}))
    repo.commit("add", {CAPABILITY_RECORD: _capability_record()})

    found = _document()

    assert _names(found["proposals"]) == ["DEC-001"]
    assert any("'from-the-moon'" in why for why in found["cannot_tell"])


def test_a_kit_shipped_capabilitys_rule_set_is_skipped(repo: GitRepo) -> None:
    _branch(repo, _adopter({MANIFEST: _capability_manifest("kit-shipped")}))
    repo.commit("sync", {CAPABILITY_RULES: _rules({FIRST: "proposed"})})

    assert _document()["proposals"] == []


def test_a_change_cannot_skip_its_own_proposal_by_rewriting_the_manifest(repo: GitRepo) -> None:
    """A file either reading skips is skipped, so this is shown, not refused (ADR-081 point 3)."""
    _branch(repo, _adopter({MANIFEST: _capability_manifest("incubated-in-repo")}))
    repo.commit(
        "claim",
        {MANIFEST: _capability_manifest("kit-shipped"), CAPABILITY_RECORD: _capability_record()},
    )

    found = _document()

    assert found["proposals"] == []
    assert found["received_disagreements"] == [CAPABILITY_RECORD]


@pytest.mark.parametrize("source", [False, True], ids=["a project", "the methodology's source"])
@pytest.mark.parametrize(
    "manifest",
    [None, "kit-shipped", "incubated-in-repo", "externally-sourced"],
    ids=["no manifest", "kit-shipped", "incubated", "externally-sourced"],
)
def test_a_stand_in_answers_as_its_tree_would(
    repo: GitRepo, source: bool, manifest: str | None
) -> None:
    files = {OWNERSHIP: _ownership()}
    if manifest is not None:
        files[MANIFEST] = _capability_manifest(manifest)
    if source:
        files[landing.SOURCE_FILE_INPUT] = ""
    repo.commit("start", files)
    paths = [CORE, RECORD, CAPABILITY_RECORD, CAPABILITY_RULES, RULES, ".pkit/rule-sets/cmn.md"]
    ownership = lifecycle_ownership.load_ownership(repo.root)
    assert ownership is not None

    received = landing._received(repo.root, (("a state", CommitTree(repo.root, "HEAD")),), paths)

    assert received.skipped == (
        frozenset(rel for rel in paths if ownership.is_synced_copy(repo.root, rel)),
    )


def test_the_tests_source_markers_are_the_stand_ins_inputs() -> None:
    ownership = lifecycle_ownership.load_ownership(REPO)
    assert ownership is not None

    found = {"/".join(marker) for marker in ownership._SOURCE_MARKERS}

    assert found == {landing.SOURCE_FILE_INPUT, landing.SOURCE_TREE_INPUT}


def test_the_test_reads_nothing_but_the_stand_ins_inputs(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo.commit(
        "start",
        {
            OWNERSHIP: _ownership(),
            MANIFEST: _capability_manifest("kit-shipped"),
            landing.SOURCE_FILE_INPUT: "",
        },
    )
    ownership = lifecycle_ownership.load_ownership(repo.root)
    assert ownership is not None
    read: set[str] = set()

    def spying(name: str) -> Callable[..., Any]:
        real = getattr(pathlib.Path, name)

        def spy(self: pathlib.Path, *args: Any, **kwargs: Any) -> Any:
            if self.is_absolute() and self.is_relative_to(repo.root):
                read.add(self.relative_to(repo.root).as_posix())
            return real(self, *args, **kwargs)

        return spy

    paths = [CORE, RECORD, CAPABILITY_RECORD, CAPABILITY_RULES, ".pkit/rule-sets/cmn.md"]
    with monkeypatch.context() as patch:
        for name in ("read_text", "read_bytes", "open", "exists", "is_file", "is_dir"):
            patch.setattr(pathlib.Path, name, spying(name))
        for rel in paths:
            ownership.is_synced_copy(repo.root, rel)

    inputs = {landing.MANIFEST_INPUT, landing.SOURCE_FILE_INPUT, landing.SOURCE_TREE_INPUT}
    assert read and read <= inputs


# --- where it looks --------------------------------------------------------------------


def _overlay(folder: str) -> str:
    return f"adr-records:\n  - {folder}\n"


def test_a_change_hides_no_record_by_moving_the_adr_folder(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, OVERLAY_RELPATH: _overlay("docs/adr")})
    repo.commit(
        "hide",
        {
            OVERLAY_RELPATH: _overlay("docs/other"),
            "docs/adr/ADR-001-a.md": _record("proposed", record_id="ADR-001"),
        },
    )

    assert _names(_document()["proposals"]) == ["ADR-001"]


def test_a_record_in_the_folder_the_change_names_is_judged_too(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, OVERLAY_RELPATH: _overlay("docs/adr")})
    repo.commit(
        "move",
        {
            OVERLAY_RELPATH: _overlay("docs/other"),
            "docs/other/ADR-001-a.md": _record("proposed", record_id="ADR-001"),
        },
    )

    assert _names(_document()["proposals"]) == ["ADR-001"]


@pytest.mark.parametrize(
    "overlay",
    [
        "adr-records: [\n",
        "- docs/adr\n",
        "adr-records: docs/adr\n",
        "adr-records:\n  - 1\n",
        "adr-records:\n  - ../adr\n",
    ],
    ids=["no parse", "no mapping", "no list", "no text", "outside the repository"],
)
def test_an_overlay_that_gives_no_adr_folder_counts_as_one_proposal(
    repo: GitRepo, overlay: str
) -> None:
    _branch(repo, {CONFIG: ON, OVERLAY_RELPATH: overlay})
    repo.commit("add", {"docs/adr/ADR-001-a.md": _record("proposed", record_id="ADR-001")})

    found = _document()

    (proposal,) = found["proposals"]
    assert proposal["path"] == OVERLAY_RELPATH and "an ADR may go unread" in proposal["why"]
    assert found["refuses"] is True


def test_an_overlay_that_is_a_link_counts_as_one_proposal(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, "overlay.yaml": _overlay("docs/adr")})
    link = repo.root / OVERLAY_RELPATH
    link.parent.mkdir(parents=True)
    link.symlink_to("../../../overlay.yaml")
    repo.commit("link")

    (proposal,) = _document()["proposals"]

    assert proposal["path"] == OVERLAY_RELPATH and "link" in proposal["why"]


def test_a_change_that_mends_the_overlay_is_not_refused_for_it(repo: GitRepo) -> None:
    _branch(repo, {CONFIG: ON, OVERLAY_RELPATH: "adr-records: [\n"})
    repo.commit("mend", {OVERLAY_RELPATH: _overlay("docs/adr")})

    assert _run().exit_code == 0


@pytest.mark.parametrize(
    "files",
    [{}, {OVERLAY_RELPATH: "other: 1\n"}, {OVERLAY_RELPATH: "adr-records: []\n"}],
    ids=["no overlay", "no entry", "an empty entry"],
)
def test_an_overlay_that_names_no_adr_folder_holds_no_proposal(
    repo: GitRepo, files: Mapping[str, str]
) -> None:
    _branch(repo, {CONFIG: ON, **files})
    repo.commit("add", {"docs/adr/ADR-001-a.md": _record("proposed", record_id="ADR-001")})

    assert _document()["proposals"] == []


# --- the list --------------------------------------------------------------------------


def test_the_list_shows_the_commit_that_accepted_it_with_the_rest_of_its_work(
    repo: GitRepo,
) -> None:
    _branch(repo)
    accepting = repo.commit("accept", {RECORD: _record("accepted"), "code.py": "x = 1\n"})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["commit"] == accepting and commit["subject"] == "accept"
    assert commit["paths"] == ["code.py"]
    assert commit["nothing_lands"] is False


def test_an_acceptance_alone_says_nothing_else_lands(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    repo.commit("accept", {RECORD: _record("accepted")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["paths"] == [] and commit["nothing_lands"] is True
    assert "nothing else of it lands" in _run().output


@pytest.mark.parametrize("separator", ["\x0c", "\u2028"], ids=ascii)
def test_a_subject_holding_a_line_separator_is_listed_whole(repo: GitRepo, separator: str) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    subject = f"accept{separator}it"
    accepting = repo.commit(subject, {RECORD: _record("accepted")})

    (commit,) = _commits(_document(), "PRJ-001")
    result = _run()

    assert commit["commit"] == accepting and commit["subject"] == subject
    assert result.exit_code == 0 and printable(subject) in result.stdout


def test_the_list_shows_the_work_before_each_acceptance(repo: GitRepo) -> None:
    _branch(repo)
    work = repo.commit("work", {"code.py": "x = 1\n"})
    repo.commit("record", {RECORD: _record("proposed")})
    repo.commit("accept", {RECORD: _record("accepted")})
    repo.commit("after", {"later.py": "y = 2\n"})

    (commit,) = _commits(_document(), "PRJ-001")

    assert _before(commit) == [work]
    assert commit["before"][0]["paths"] == ["code.py"]


def test_a_commit_touching_only_the_record_is_not_work_before(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("draft", {RECORD: _record("proposed")})
    repo.commit("redraft", {RECORD: _record("proposed", text="Redrafted")})
    repo.commit("accept", {RECORD: _record("accepted", text="Redrafted")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["before"] == []


def test_each_commit_that_accepted_it_is_listed(repo: GitRepo) -> None:
    _branch(repo)
    first = repo.commit("accept", {RECORD: _record("accepted")})
    repo.commit("back", {RECORD: _record("proposed")})
    second = repo.commit("again", {RECORD: _record("accepted")})

    commits = _commits(_document(), "PRJ-001")

    assert [commit["commit"] for commit in commits] == [first, second]


def test_the_edits_since_read_a_record_point_by_point(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("accept", {RECORD: _record("accepted")})
    repo.commit("edit", {RECORD: _record("accepted", text="Edited")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["edits_since"]["points"] == [{"id": "1", "change": "altered", "title": "Point 1"}]
    assert "edited since: point 1 (Point 1) altered" in _run().output


def test_no_edits_since_read_as_none(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("accept", {RECORD: _record("accepted")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["edits_since"] is None


def test_a_record_moved_after_it_was_accepted_keeps_its_acceptance(repo: GitRepo) -> None:
    moved = f"{PROJECT}/PRJ-001-moved.md"
    _branch(repo)
    accepting = repo.commit("accept", {RECORD: _record("accepted")})
    repo.rename(RECORD, moved)

    (entry,) = _document()["accepted"]

    assert entry["path"] == moved
    assert [commit["commit"] for commit in entry["commits"]] == [accepting]


def test_work_a_commit_undid_stays_listed_and_says_nothing_lands(repo: GitRepo) -> None:
    _branch(repo, {"code.py": "x = 0\n"})
    tried = repo.commit("try", {"code.py": "x = 1\n"})
    undone = repo.commit("undo", {"code.py": "x = 0\n"})
    repo.commit("accept", {RECORD: _record("accepted")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert _before(commit) == [tried, undone]
    assert all(work["nothing_lands"] for work in commit["before"])
    assert "nothing of it lands" in _run().output


def test_a_stacked_parents_record_is_on_the_list(repo: GitRepo) -> None:
    _branch(repo)
    parent = repo.commit("parent", {RECORD: _record("accepted")})
    repo.checkout("child", create=True)
    repo.commit("child", {"code.py": "x = 1\n"})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["commit"] == parent


def test_a_parent_that_landed_squashed_is_not_shown_again(repo: GitRepo) -> None:
    _branch(repo)
    parent = repo.commit("parent", {RECORD: _record("accepted"), "code.py": "x = 1\n"})
    repo.checkout("child", create=True)
    repo.commit("child", {OTHER: _other("accepted")})
    repo.checkout("main")
    repo.squash_merge("change")
    repo.checkout("child")

    found = _document()

    assert _names(found["accepted"]) == ["PRJ-002"]
    (commit,) = _commits(found, "PRJ-002")
    assert _before(commit) == [parent]
    assert commit["before"][0]["nothing_lands"] is True


def test_a_parallel_line_counts_as_before(repo: GitRepo) -> None:
    _branch(repo)
    repo.checkout("line", create=True)
    line = repo.commit("line", {"code.py": "x = 1\n"})
    repo.checkout("change")
    repo.commit("accept", {RECORD: _record("accepted")})
    repo.merge("line")

    (commit,) = _commits(_document(), "PRJ-001")

    assert _before(commit) == [line]


def test_what_descends_from_the_acceptance_is_not_before_it(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("accept", {RECORD: _record("accepted")})
    repo.commit("later", {"code.py": "x = 1\n"})
    repo.checkout("line", create=True)
    repo.commit("line", {"more.py": "y = 1\n"})
    repo.checkout("change")
    repo.merge("line")

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["before"] == []


def test_a_merge_that_only_joins_two_lines_accepts_nothing(repo: GitRepo) -> None:
    _branch(repo)
    repo.checkout("line", create=True)
    accepting = repo.commit("accept", {RECORD: _record("accepted")})
    repo.checkout("change")
    repo.commit("work", {"code.py": "x = 1\n"})
    repo.merge("line")

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["commit"] == accepting


def test_a_merge_that_changes_the_status_itself_accepted_it(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    repo.checkout("line", create=True)
    repo.commit("line", {"code.py": "x = 1\n"})
    repo.checkout("change")
    repo.commit("work", {"more.py": "y = 1\n"})
    repo.git("merge", "-q", "--no-commit", "--no-ff", "line")
    merged = repo.commit("merged", {RECORD: _record("accepted")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["commit"] == merged


def test_a_status_one_side_of_a_conflicted_merge_holds_is_not_the_merges_own(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    repo.checkout("line", create=True)
    accepting = repo.commit("accept", {RECORD: _record("accepted", text="Line")})
    repo.checkout("change")
    repo.commit("edit", {RECORD: _record("proposed", text="Change")})
    repo.git("merge", "-q", "--no-commit", "--no-ff", "line", check=False)
    repo.commit("settled", {RECORD: _record("accepted", text="Line")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["commit"] == accepting


def test_a_status_neither_side_of_a_conflicted_merge_holds_is_the_merges_own(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    repo.checkout("line", create=True)
    repo.commit("edit", {RECORD: _record("proposed", text="Line")})
    repo.checkout("change")
    repo.commit("edit", {RECORD: _record("proposed", text="Change")})
    repo.git("merge", "-q", "--no-commit", "--no-ff", "line", check=False)
    merged = repo.commit("settled", {RECORD: _record("accepted", text="Both")})

    (commit,) = _commits(_document(), "PRJ-001")

    assert commit["commit"] == merged


def test_a_rule_on_the_list_shows_its_commit_and_the_edits_since(repo: GitRepo) -> None:
    _branch(repo, {RULES: _rules({FIRST: "proposed"})})
    accepting = repo.commit("accept", {RULES: _rules({FIRST: "accepted"})})
    repo.commit("edit", {RULES: _rules({FIRST: "accepted"}, text={FIRST: "Edited"})})

    found = _document()

    (commit,) = _commits(found, FIRST)
    assert commit["commit"] == accepting and commit["paths"] == []
    assert commit["edits_since"] == {"fields": [], "text": True, "removed": False}


def test_an_edit_to_another_rule_in_its_file_counts_as_work(repo: GitRepo) -> None:
    both = {FIRST: "proposed", SECOND: "proposed"}
    _branch(repo, {RULES: _rules(both)})
    other = repo.commit("other", {RULES: _rules(both, text={SECOND: "Edited"})})
    repo.commit("own", {RULES: _rules(both, text={FIRST: "Mine", SECOND: "Edited"})})
    repo.commit(
        "accept",
        {
            RULES: _rules(
                {FIRST: "accepted", SECOND: "proposed"}, text={FIRST: "Mine", SECOND: "Edited"}
            )
        },
    )

    (commit,) = _commits(_document(), FIRST)

    assert _before(commit) == [other]
    assert commit["before"][0]["paths"] == [RULES]


def test_a_rule_accepted_beside_an_edit_to_another_shows_that_edit(repo: GitRepo) -> None:
    both = {FIRST: "proposed", SECOND: "proposed"}
    _branch(repo, {RULES: _rules(both)})
    repo.commit(
        "accept", {RULES: _rules({FIRST: "accepted", SECOND: "proposed"}, text={SECOND: "Edited"})}
    )

    (commit,) = _commits(_document(), FIRST)

    assert commit["paths"] == [RULES]


def test_a_rule_set_back_after_acceptance_is_not_on_the_list(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("accept", {RECORD: _record("accepted")})
    repo.commit("back", {RECORD: _record("proposed")})

    found = _document()

    assert found["accepted"] == []
    assert _names(found["proposals"]) == ["PRJ-001"]


# --- accepted on the base since the branch left it -------------------------------------


def test_the_second_list_shows_a_record_the_base_accepted_and_the_merge_changes(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record("proposed"), OTHER: _other("proposed")})
    repo.commit("edit", {OTHER: _other("proposed").replace("Why.", "Why not.")})
    _on_main(repo, {OTHER: _other("accepted"), RECORD: _record("accepted")})

    found = _document()

    (entry,) = found["accepted_on_base"]
    assert entry["name"] == "PRJ-002" and entry["edits"]["other_text"] is True
    assert "Accepted on the base since the branch left it" in _run().output


def test_the_second_list_leaves_out_what_the_merge_leaves_alone(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("proposed")})
    repo.commit("work", {"a.txt": "a\n"})
    _on_main(repo, {RECORD: _record("accepted")})

    assert _document()["accepted_on_base"] == []


def test_the_second_list_shows_a_rule_the_base_accepted_and_the_merge_changes(
    repo: GitRepo,
) -> None:
    both = {FIRST: "proposed", SECOND: "proposed"}
    _branch(repo, {RULES: _rules(both)})
    repo.commit("edit", {RULES: _rules(both, text={SECOND: "Edited"})})
    _on_main(repo, {RULES: _rules({FIRST: "proposed", SECOND: "accepted"})})

    found = _document()

    (entry,) = found["accepted_on_base"]
    assert entry["name"] == SECOND and entry["kind"] == landing.RULE
    assert entry["edits"] == {"fields": [], "text": True, "removed": False}


def test_what_the_branch_point_held_accepted_is_not_on_the_second_list(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("accepted")})
    repo.commit("edit", {RECORD: _record("accepted", text="Edited")})
    _on_main(repo, {"b.txt": "b\n"})

    assert _document()["accepted_on_base"] == []


# --- the document, and what stays as it is ---------------------------------------------


def test_the_document_gives_the_base_the_head_and_the_key(repo: GitRepo) -> None:
    tip = _branch(repo, {CONFIG: ON})
    head = repo.commit("work", {"a.txt": "a\n"})

    found = _document()

    assert found["schema_version"] == landing.SCHEMA_VERSION == 1
    assert found["problem"] is None
    assert found["base"]["named"] == "main" and found["base"]["tip"] == tip
    assert found["head"] == head
    assert found["default_branch"]["declared"] == "main"
    assert found["default_branch"]["is_base"] is True
    assert found["key"]["name"] == "decisions.refuse-proposals"
    assert found["key"]["value"] is True and found["key"]["read_at"] == tip
    assert found["key"]["refusal_on"] is True and found["key"]["change"] is None


def test_the_document_is_the_same_bytes_for_the_same_state(repo: GitRepo) -> None:
    _branch(repo)
    repo.commit("accept", {RECORD: _record("accepted"), "code.py": "x = 1\n"})

    assert _run("--json").stdout == _run("--json").stdout


def test_the_numbering_checks_document_stays_at_version_one() -> None:
    assert decisions_check_diff.SCHEMA_VERSION == 1


@pytest.mark.parametrize("gate", ["scripts/check.sh", ".githooks/pre-push"])
def test_the_check_gate_and_the_hook_leave_the_refusal_out(gate: str) -> None:
    assert "check-landing" not in (REPO / gate).read_text(encoding="utf-8")


def test_a_read_of_the_proposals_a_state_holds(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("proposed"), RULES: _rules({FIRST: None, SECOND: "accepted"})})
    _commit_bytes(repo, OTHER, b"\xff not text")

    found = landing.proposals_at(repo.root, repo.head())

    assert [(item.kind, item.name) for item in found] == [
        (landing.RECORD, "PRJ-001"),
        (landing.RECORD, OTHER),
        (landing.RULE, FIRST),
    ]


def test_a_read_of_a_state_counts_an_overlay_that_does_not_read(repo: GitRepo) -> None:
    _branch(repo, {OVERLAY_RELPATH: "adr-records: [\n"})

    (found,) = landing.proposals_at(repo.root, repo.head())

    assert (found.path, found.was) == (OVERLAY_RELPATH, "proposed")


def test_a_read_of_a_state_that_cannot_be_read_gives_no_answer(repo: GitRepo) -> None:
    _branch(repo)

    with pytest.raises(landing.NoAnswer):
        landing.proposals_at(repo.root, "0" * 40)


# --- the install writes the key only on the flag ---------------------------------------


@pytest.fixture
def no_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh repository to install into, the adapter's deploy primitives stubbed."""
    target = tmp_path / "target"
    GitRepo.init(target)
    monkeypatch.chdir(target)
    monkeypatch.setattr(install, "_run_adapter_primitive", lambda *_args: None)
    return target


def test_the_install_writes_the_key_on_the_flag(no_adapter: Path) -> None:
    result = CliRunner().invoke(main, ["init", "--refuse-proposals"])

    assert result.exit_code == 0, result.output
    assert pc.read_config(no_adapter)["decisions"] == {"refuse-proposals": True}


def test_the_install_writes_no_key_and_makes_no_offer_without_the_flag(no_adapter: Path) -> None:
    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code == 0, result.output
    assert "decisions" not in pc.read_config(no_adapter)
    assert "refuse-proposals" not in result.output


def test_a_dry_run_says_what_it_would_write_and_writes_nothing(no_adapter: Path) -> None:
    result = CliRunner().invoke(main, ["init", "--dry-run", "--refuse-proposals"])

    assert result.exit_code == 0, result.output
    assert "would write decisions.refuse-proposals: true" in result.output
    assert not (no_adapter / ".pkit").exists()
