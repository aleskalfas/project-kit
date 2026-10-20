"""The run's contract of a fixer, as data, and its reading (#1744; project-management
DEC-056 points 3 and 6).

The drift command reads what a fixer hands back by one contract, held as data in
`schemas/fixer-contract.yaml`: the lead, the three forms of a result line, and the
`none` reasons with what clears each. `_lib/fixer_contract.py` reads the lines and
the answers by it. These tests hold:

- the record and the README to the data, both ways (COR-018): the forms, the lead,
  the reasons, and each reason's class;
- the reading of a final message: which lines count, what a line must match, what
  gives an artefact no result, and what is read for nothing;
- the reading of an answer and its diff, a diff that reaches another file being a
  breach;
- whether a `none` stands, by its class.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
PM = REPO / ".pkit" / "capabilities" / "project-management"
DATA = PM / "schemas" / "fixer-contract.yaml"
COMPANION = PM / "schemas" / "fixer-contract.schema.json"
RECORD = PM / "decisions" / "DEC-056-drift-fixers.md"
README = PM / "README.md"
MODULE = PM / "scripts" / "_lib" / "fixer_contract.py"


def _load() -> ModuleType:
    name = "pm_fixer_contract_under_test"
    spec = importlib.util.spec_from_file_location(name, MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fc = _load()
CONTRACT = fc.load()
AGENT = "living-docs"
PAGE = "docs/install.md"
GUIDE = "docs/guide.md"


def _data() -> dict[str, Any]:
    return YAML(typ="safe").load(DATA.read_text(encoding="utf-8"))


# --- the record and the README, held to the data ------------------------------------------


def _record() -> str:
    return RECORD.read_text(encoding="utf-8")


def _forms(text: str) -> list[str]:
    block = text.split("```text\n", 1)[1].split("```", 1)[0]
    return [line.strip() for line in block.splitlines() if line.strip()]


def _readme_contract() -> str:
    text = README.read_text(encoding="utf-8")
    return text.split("**The version covers what a fixer run passes and returns.**", 1)[1].split(
        "\n## ", 1
    )[0]


def test_the_data_passes_its_companion_and_reads_as_the_contract() -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads(COMPANION.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(_data())) == []
    assert list(CONTRACT.forms) == ["proposed", "held", "none"]
    assert CONTRACT.answer_file == "answer.json"


def test_the_contract_version_is_the_fixers_point_s() -> None:
    """The point's version covers the run's contract (DEC-056 point 1)."""
    package = YAML(typ="safe").load((PM / "package.yaml").read_text(encoding="utf-8"))
    point = package["connections"]["extension-points"]["accepts"]["pkit::work-tracking:fixers"]
    assert CONTRACT.contract_version == point["schema_version"] == 1


def test_the_record_s_forms_are_the_data_s() -> None:
    record = _record().split("- **The result.**", 1)[1]
    assert _forms(record) == list(CONTRACT.forms.values())
    # Each form is keyed by the state it gives.
    assert [f.split("): ", 1)[1].split(" ", 1)[0] for f in _forms(record)] == list(CONTRACT.forms)


def test_the_record_s_lead_is_the_data_s() -> None:
    counts = _record().split("**What counts as a line:**", 1)[1].split("\n", 1)[0]
    assert re.findall(r"starts with `([^`]+)`", counts) == [CONTRACT.lead]
    assert all(form.startswith(CONTRACT.lead) for form in CONTRACT.forms.values())


#: The record's words for each class of `none` reason, and the data's.
CLASSES = {"the artefact": "artefact", "the setup": "setup", "the next run": "next-run"}


def _record_reasons() -> dict[str, str]:
    """Each `none` reason the record names, with the class its bullet gives it, in the
    record's order. Each reason is named in backticks and glossed after a comma."""
    text = _record().split("**The `none` reasons**", 1)[1].split("\n### ", 1)[0]
    found: dict[str, str] = {}
    for words, rest in re.findall(r"^\s*- \*\*Cleared by ([a-z ]+):\*\*(.*)$", text, re.M):
        for code in re.findall(r"`([a-z]+(?:-[a-z]+)*)`, ", rest):
            assert code not in found, code
            found[code] = CLASSES[words]
    named = [c for c in re.findall(r"`([a-z]+(?:-[a-z]+)*)`, ", text) if c != "none"]
    assert named == list(found), "a reason named outside the three classes' bullets"
    return found


def test_the_record_s_none_reasons_and_their_classes_are_the_data_s_both_ways() -> None:
    record = _record_reasons()
    assert list(record) == list(CONTRACT.reasons)
    assert record == dict(CONTRACT.reasons)
    assert set(CONTRACT.reasons.values()) == set(CLASSES.values())


def test_the_record_s_two_failures_in_a_row_are_the_module_s() -> None:
    text = _record().split("**Cleared by the next run:**", 1)[1].split("\n", 1)[0]
    assert "fails at two runs in a row then stands as the setup's faults do" in text
    assert fc.FAILURES_TO_STAND == 2
    assert CONTRACT.reasons[fc.FAILED_REASON] == fc.BY_NEXT_RUN


def test_the_readme_s_forms_and_lead_are_the_data_s() -> None:
    contract = _readme_contract()
    assert _forms(contract) == list(CONTRACT.forms.values())
    lines = contract.split("- **The result lines**", 1)[1].split("```text", 1)[0]
    assert re.findall(r"starts with `([^`]+)`", lines) == [CONTRACT.lead]


def test_the_readme_s_none_reasons_are_the_data_s_both_ways() -> None:
    table = re.findall(r"^    \| `([a-z-]+)` \| ", _readme_contract(), flags=re.MULTILINE)
    assert table == list(CONTRACT.reasons)


# --- the contract's own checks -----------------------------------------------------------------


def _contract_copy(tmp_path: Path, change: str, to: str) -> Path:
    shutil.copy(COMPANION, tmp_path / COMPANION.name)
    text = DATA.read_text(encoding="utf-8")
    assert change in text
    (tmp_path / DATA.name).write_text(text.replace(change, to, 1), encoding="utf-8")
    return tmp_path / DATA.name


@pytest.mark.parametrize(
    ("change", "to", "said"),
    [
        ("schema_version: 1", "schema_version: 2", "not a contract of version 1"),
        ("cleared-by: setup", "cleared-by: never", "off its schema"),
        ('held: "Fixer result (', 'held: "Result (', "does not start with the lead"),
        ('`: <the question>"', '`: <a question>"', "holds <a question>"),
        ("in `<artefact>/answer.json`", "in its folder", "names no answer file"),
    ],
)
def test_a_contract_off_its_shape_is_refused(
    tmp_path: Path, change: str, to: str, said: str
) -> None:
    with pytest.raises(fc.ContractError, match=re.escape(said)):
        fc.load(_contract_copy(tmp_path, change, to))


def test_a_contract_without_its_companion_is_refused(tmp_path: Path) -> None:
    shutil.copy(DATA, tmp_path / DATA.name)
    with pytest.raises(fc.ContractError, match="cannot be read"):
        fc.load(tmp_path / DATA.name)


def test_failed_must_pass_to_the_next_run(tmp_path: Path) -> None:
    text = DATA.read_text(encoding="utf-8").replace(
        "  failed:\n    cleared-by: next-run", "  failed:\n    cleared-by: setup"
    )
    shutil.copy(COMPANION, tmp_path / COMPANION.name)
    (tmp_path / DATA.name).write_text(text, encoding="utf-8")
    with pytest.raises(fc.ContractError, match="`failed` is not cleared by the next run"):
        fc.load(tmp_path / DATA.name)


# --- reading the result lines ------------------------------------------------------------------


def _proposed(artefact: str, agent: str = AGENT) -> str:
    return f"Fixer result ({agent}): proposed `{artefact}` in `{artefact}/answer.json`"


def _held(artefact: str, question: str = "Is --out gone for good?") -> str:
    return f"Fixer result ({AGENT}): held `{artefact}`: {question}"


def _none(artefact: str, reason: str = "not-stale", words: str = "It holds.") -> str:
    return f"Fixer result ({AGENT}): none `{artefact}`: {reason}: {words}"


def _read(output: str, names: tuple[str, ...] = (PAGE, GUIDE)) -> Any:
    return fc.read_results(output, AGENT, names, CONTRACT)


def test_one_line_for_each_artefact_gives_each_its_result() -> None:
    results = _read(f"I read both pages.\n\n{_proposed(PAGE)}\n{_held(GUIDE)}\n")
    assert results.ignored == ()
    assert list(results.of) == [PAGE, GUIDE]
    assert results.of[PAGE] == fc.Result(PAGE, "proposed", answer=f"{PAGE}/answer.json")
    assert results.of[GUIDE] == fc.Result(GUIDE, "held", words="Is --out gone for good?")
    none = _read(_none(PAGE, "upstream", "It waits for docs/a.md."), (PAGE,)).of[PAGE]
    assert (none.state, none.reason, none.words) == ("none", "upstream", "It waits for docs/a.md.")


def test_lines_in_a_fence_count_the_same_and_the_fence_s_own_lines_are_none() -> None:
    output = f"Done.\n\n```text\n{_proposed(PAGE)}\n  {_none(GUIDE)}  \n```\n"
    results = _read(output)
    assert results.ignored == ()
    assert [r.state for r in results.of.values()] == ["proposed", "none"]


def test_a_line_behind_a_quote_mark_is_no_result_line() -> None:
    results = _read(f"> {_proposed(PAGE)}\n{_held(GUIDE)}\n")
    assert results.ignored == ()
    assert results.of[PAGE].state == "failed"
    assert results.of[PAGE].why == "no result line names it"


def test_every_line_counts_so_two_for_one_artefact_give_it_no_result() -> None:
    """A quoted line before the real one cannot stand in for it: both count."""
    for second in (_proposed(PAGE), _none(PAGE)):
        results = _read(f"{_proposed(PAGE)}\n{second}\n{_held(GUIDE)}")
        assert results.of[PAGE].state == "failed"
        assert results.of[PAGE].why == "2 result lines name it"
        assert results.of[GUIDE].state == "held"


@pytest.mark.parametrize(
    ("line", "why"),
    [
        (_none(PAGE, "not-wanted"), "its reason `not-wanted` is not one of"),
        (_none(PAGE, "Not-mine"), "matches none of the contract's forms"),
        (_proposed(PAGE).replace("answer.json", "other.json"), "matches none"),
        (f"Fixer result ({AGENT}): proposed `{PAGE}` in `{GUIDE}/answer.json`", "matches none"),
        (_proposed(PAGE) + " and more", "matches none"),
        (f"Fixer result ({AGENT}): held `{PAGE}`: ", "matches none"),
        (f"Fixer result ({AGENT}): none `{PAGE}`: refused", "matches none"),
        (f"Fixer result ({AGENT}) proposed `{PAGE}`", "matches none"),
        (_proposed(PAGE, agent="analysis-resolver"), "it is for agent analysis-resolver, not"),
        (_proposed("docs/other.md"), "it names an artefact the brief does not name"),
        (_proposed(PAGE + " "), "it names an artefact the brief does not name"),
        (_proposed(PAGE.upper()), "it names an artefact the brief does not name"),
    ],
)
def test_a_line_off_the_grammar_for_another_agent_or_artefact_is_read_for_nothing(
    line: str, why: str
) -> None:
    results = _read(f"{line}\n{_held(GUIDE)}", (PAGE, GUIDE))
    assert [ignored.line for ignored in results.ignored] == [line.strip()]
    assert why in results.ignored[0].why
    assert results.of[PAGE] == fc.Result(PAGE, "failed", why="no result line names it")
    assert results.of[GUIDE].state == "held"


def test_lines_split_only_at_line_feeds_and_their_whitespace_is_stripped() -> None:
    """A line separator inside a held question is the question's own word; a carriage
    return before the feed is whitespace."""
    question = "Which one?" + chr(0x2028) + _proposed(GUIDE)
    results = _read(f"{_held(PAGE, question)}\r\n{_none(GUIDE)}\r\n")
    assert results.of[PAGE].words == question
    assert results.of[GUIDE].state == "none"
    assert fc.result_lines("a" + chr(0x2028) + _none(PAGE), CONTRACT) == []


def test_no_output_gives_every_artefact_no_result_and_names_count_once() -> None:
    results = _read("", (PAGE, PAGE, GUIDE))
    assert list(results.of) == [PAGE, GUIDE]
    assert {r.state for r in results.of.values()} == {"failed"}


# --- reading an answer -------------------------------------------------------------------------

DIFF = (
    f"diff --git a/{PAGE} b/{PAGE}\n"
    "index 1111111..2222222 100644\n"
    f"--- a/{PAGE}\n"
    f"+++ b/{PAGE}\n"
    "@@ -1,3 +1,3 @@\n"
    " # Install\n"
    "-Run it with --out.\n"
    "+Run it with --output.\n"
    " Done.\n"
)


def _answer(artefact: str = PAGE, **fields: Any) -> dict[str, Any]:
    name = artefact.split("/")[-1].split("#")[-1]
    return {
        "artefact": artefact,
        "outcome": "updated",
        "justification": None,
        "sentence": "Running it writes --output, which a3f9c1e renamed from --out.",
        "keep": [],
        "diff": f"{artefact}/{name}.diff",
        "first": [],
        **fields,
    }


def _files(
    tmp_path: Path, answer: Any = None, diff: str | None = DIFF, artefact: str = PAGE
) -> Path:
    """The run's files: the artefact's folder with its answer and its diff."""
    root = tmp_path / "files"
    folder = root.joinpath(*artefact.split("/"))
    folder.mkdir(parents=True, exist_ok=True)
    answer = _answer(artefact) if answer is None else answer
    text = answer if isinstance(answer, str) else json.dumps(answer)
    (folder / "answer.json").write_text(text, encoding="utf-8")
    if diff is not None and isinstance(answer, dict) and answer.get("diff"):
        (root / answer["diff"]).parent.mkdir(parents=True, exist_ok=True)
        (root / answer["diff"]).write_text(diff, encoding="utf-8")
    return root


def test_an_answer_that_holds_is_read_with_its_files(tmp_path: Path) -> None:
    root = _files(tmp_path)
    answer = fc.read_answer(root, PAGE, f"{PAGE}/answer.json", CONTRACT)
    assert isinstance(answer, fc.Answer)
    assert (answer.outcome, answer.path, answer.diff) == (
        "updated",
        root / PAGE / "answer.json",
        root / PAGE / "install.md.diff",
    )


def test_an_unchanged_answer_with_no_diff_is_read(tmp_path: Path) -> None:
    unchanged = _answer(outcome="unchanged", justification="It holds.", sentence=None, diff=None)
    assert isinstance(fc.read_answer(_files(tmp_path, unchanged), PAGE), fc.Answer)


def test_an_entry_s_answer_edits_its_collection_file(tmp_path: Path) -> None:
    term = "tech-docs/analysis/glossary.md#TERM-run"
    diff = DIFF.replace(PAGE, "tech-docs/analysis/glossary.md")
    root = _files(tmp_path, _answer(term), diff, artefact=term)
    assert fc.own_file(term) == "tech-docs/analysis/glossary.md"
    assert isinstance(fc.read_answer(root, term), fc.Answer)


def _unread(root: Path, artefact: str = PAGE, answer_rel: str | None = None) -> Any:
    found = fc.read_answer(root, artefact, answer_rel, CONTRACT)
    assert isinstance(found, fc.Unread), found
    return found


@pytest.mark.parametrize(
    ("answer", "said"),
    [
        ("{", "cannot be read as JSON"),
        ('{"artefact": "a", "artefact": "b"}', "is given twice"),
        (_answer(outcome="deferred"), "refused by the schema"),
        ({**_answer(), "command": "pkit friction revalidate"}, "refused by the schema"),
        (_answer(diff=None), "refused by the schema"),
        (_answer(artefact=GUIDE, diff=f"{PAGE}/install.md.diff"), "written for another artefact"),
        (_answer(diff=f"{GUIDE}/guide.md.diff"), "is not in the artefact's folder"),
        (_answer(diff=f"{PAGE}.diff"), "is not in the artefact's folder"),
    ],
)
def test_an_answer_off_the_contract_gives_no_result(tmp_path: Path, answer: Any, said: str) -> None:
    root = _files(tmp_path, answer, DIFF)
    (root / GUIDE).mkdir(parents=True, exist_ok=True)
    (root / GUIDE / "guide.md.diff").write_text(DIFF, encoding="utf-8")
    (root / f"{PAGE}.diff").write_text(DIFF, encoding="utf-8")
    unread = _unread(root)
    assert said in unread.why
    assert unread.breach is False


def test_a_missing_answer_or_one_named_otherwise_gives_no_result(tmp_path: Path) -> None:
    root = tmp_path / "files"
    (root / "docs").mkdir(parents=True)
    assert "does not exist" in _unread(root).why
    assert (
        "is named 'docs/install.md/other.json'"
        in _unread(_files(tmp_path), answer_rel=f"{PAGE}/other.json").why
    )
    assert "no plain path" in _unread(root, artefact="docs/../install.md").why


def test_an_answer_or_a_diff_reached_through_a_link_gives_no_result(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "answer.json").write_text(json.dumps(_answer()), encoding="utf-8")
    (elsewhere / "install.md.diff").write_text(DIFF, encoding="utf-8")
    root = _files(tmp_path)
    folder = root / PAGE
    (folder / "answer.json").unlink()
    os.symlink(elsewhere / "answer.json", folder / "answer.json")
    assert "is a link" in _unread(root).why
    (folder / "answer.json").unlink()
    (folder / "answer.json").write_text(json.dumps(_answer()), encoding="utf-8")
    (folder / "install.md.diff").unlink()
    os.symlink(elsewhere / "install.md.diff", folder / "install.md.diff")
    assert "is a link" in _unread(root).why
    # A folder on the way that is a link is refused too.
    shutil.rmtree(root / "docs")
    (root / "docs").symlink_to(tmp_path / "files-elsewhere", target_is_directory=True)
    assert "docs is a link" in _unread(root).why


def test_a_diff_that_is_a_folder_gives_no_result(tmp_path: Path) -> None:
    root = _files(tmp_path, diff=None)
    (root / PAGE / "install.md.diff").mkdir()
    assert "not a plain file" in _unread(root).why


def test_a_diff_that_reaches_another_file_is_a_breach(tmp_path: Path) -> None:
    root = _files(tmp_path, diff=DIFF + DIFF.replace(PAGE, ".github/workflows/ci.yml"))
    unread = _unread(root)
    assert unread.breach is True
    assert "reaches .github/workflows/ci.yml, not only docs/install.md" in unread.why


# --- the diff's own file, and nothing else -----------------------------------------------------

_HEADERS = f"--- a/{PAGE}\n+++ b/{PAGE}\n"
_HUNK = "@@ -1,2 +1,2 @@\n-old\n+new\n same\n"


@pytest.mark.parametrize(
    "diff",
    [
        pytest.param(DIFF, id="git-diff"),
        pytest.param(_HEADERS + _HUNK, id="headers-only"),
        pytest.param(f"--- a/{PAGE}\t2026-10-01\n+++ b/{PAGE}\t2026-10-02\n" + _HUNK, id="times"),
        pytest.param(_HEADERS + "@@ -1 +1 @@\n-old\n+new\n", id="counts-left-out"),
        pytest.param(_HEADERS + _HUNK + "@@ -9,1 +9,1 @@\n-a\n+b\n", id="two-hunks"),
        pytest.param(_HEADERS + "@@ -1,1 +1,1 @@\n-old\n+new\n\\ No newline at end of file\n"),
        pytest.param(
            _HEADERS + "@@ -1,2 +1,1 @@\n--- a/other.md\n same\n", id="a-removed-line-like-a-header"
        ),
        pytest.param(_HEADERS + "@@ -1,2 +1,2 @@\n-old\n+new\n\n", id="an-empty-context-line"),
    ],
)
def test_a_diff_of_the_artefact_s_own_file_alone_holds(diff: str) -> None:
    assert fc.diff_problem(diff, PAGE) is None


def test_a_name_git_quotes_is_read_as_git_writes_it() -> None:
    own = "docs/café.md"
    quoted = '"a/docs/caf\\303\\251.md"'
    diff = (
        f'diff --git {quoted} "b/docs/caf\\303\\251.md"\n'
        f'--- {quoted}\n+++ "b/docs/caf\\303\\251.md"\n' + _HUNK
    )
    assert fc.diff_problem(diff, own) is None
    assert fc.diff_problem(diff, PAGE) == ("reaches docs/café.md, not only docs/install.md", True)


@pytest.mark.parametrize(
    ("diff", "why"),
    [
        (f"--- a/{PAGE}\n+++ b/README.md\n" + _HUNK, "reaches README.md"),
        (f"--- a/README.md\n+++ b/{PAGE}\n" + _HUNK, "reaches README.md"),
        (_HEADERS + _HUNK + "--- a/x.md\n+++ b/x.md\n" + _HUNK, "reaches x.md"),
        (f"diff --git a/{PAGE} b/x.md\n" + _HEADERS + _HUNK, "reaches a file other than"),
        ("diff --git a/x.md b/x.md\n" + _HEADERS + _HUNK, "reaches x.md"),
        (f"diff --git a/{PAGE} b/xy.md\n" + _HEADERS + _HUNK, "reaches a file other than"),
        (f"diff --git a/{PAGE} b/{PAGE}\nrename from {PAGE}\nrename to x.md\n", "reaches x.md"),
        (f"--- /dev/null\n+++ b/{PAGE}\n" + _HUNK + "--- a/x.md\n+++ b/x.md\n", "reaches x.md"),
        (f"--- a/{PAGE}\r\n+++ b/{PAGE}\r\n" + _HUNK, "reaches docs/install.md\r"),
    ],
)
def test_a_diff_that_names_another_file_is_a_breach(diff: str, why: str) -> None:
    found = fc.diff_problem(diff, PAGE)
    assert found is not None and found[1] is True, found
    assert why in found[0]


@pytest.mark.parametrize(
    ("diff", "why"),
    [
        ("", "holds no hunk"),
        (_HEADERS, "holds no hunk"),
        (f"--- /dev/null\n+++ b/{PAGE}\n" + _HUNK, "creates or deletes a file"),
        (f"--- a/{PAGE}\n+++ /dev/null\n" + _HUNK, "creates or deletes a file"),
        (f"--- {PAGE}\n+++ {PAGE}\n" + _HUNK, "a header not labelled `a/<path>`"),
        (f"+++ b/{PAGE}\n" + _HUNK, "a `+++` header with no `---` before it"),
        (f"--- a/{PAGE}\n" + _HUNK, "no hunk header it can read"),
        (_HEADERS + "@@ -1,2 +1,2 @@\n-old\n", "ends inside a hunk"),
        (_HEADERS + "@@ -1,1 +1,1 @@\n-old\n-older\n", "breaks its hunk"),
        (_HEADERS + "@@ nonsense @@\n", "no hunk header it can read"),
        ("Subject: a patch\n" + _HEADERS + _HUNK, "a line outside a unified diff at line 1"),
        (_HEADERS + _HUNK + f"--- a/{PAGE}\n", "ends after a `---` header"),
        (f"diff --git a/{PAGE} b/{PAGE}\nold mode 100644\nnew mode 100755\n", "more than"),
        (f"diff --git a/{PAGE} b/{PAGE}\nGIT binary patch\n", "more than"),
        (f"diff --git a/{PAGE} b/{PAGE}\ndeleted file mode 100644\n", "more than"),
        (f"diff --git a/{PAGE} b/{PAGE}\nrename from {PAGE}\nrename to {PAGE}\n", "renames"),
    ],
)
def test_a_diff_that_is_no_plain_edit_gives_no_result(diff: str, why: str) -> None:
    found = fc.diff_problem(diff, PAGE)
    assert found is not None and found[1] is False, found
    assert why in found[0]


# --- settling a run's results ------------------------------------------------------------------


def test_settling_reads_each_proposal_and_fails_a_held_or_none_folder_with_an_answer(
    tmp_path: Path,
) -> None:
    root = _files(tmp_path)
    third, fourth, fifth = "docs/third.md", "docs/fourth.md", "docs/fifth.md"
    for name in (GUIDE, third):
        (root / name).mkdir(parents=True)
    (root / GUIDE / "answer.json").write_text("{}", encoding="utf-8")
    _files(
        tmp_path,
        _answer(fourth),
        DIFF.replace(PAGE, ".github/ci.yml"),
        artefact=fourth,
    )
    output = "\n".join(
        [_proposed(PAGE), _held(GUIDE), _none(third), _proposed(fourth), _proposed(fifth)]
    )
    names = (PAGE, GUIDE, third, fourth, fifth)
    settled = fc.settle(fc.read_results(output, AGENT, names, CONTRACT), root, CONTRACT)
    states = {name: result.state for name, result in settled.of.items()}
    assert states == {
        PAGE: "proposed",
        GUIDE: "failed",
        third: "none",
        fourth: "set-aside",
        fifth: "failed",
    }
    assert isinstance(settled.of[PAGE].read, fc.Answer)
    assert settled.of[GUIDE].why == "it is held, and its folder holds an answer"
    assert "reaches .github/ci.yml" in (settled.of[fourth].why or "")
    assert "does not exist" in (settled.of[fifth].why or "")


def test_with_no_files_kept_no_proposal_can_be_read(tmp_path: Path) -> None:
    results = fc.read_results(f"{_proposed(PAGE)}\n{_held(GUIDE)}", AGENT, (PAGE, GUIDE), CONTRACT)
    settled = fc.settle(results, None, CONTRACT)
    assert settled.of[PAGE] == fc.Result(
        PAGE, "failed", answer=f"{PAGE}/answer.json", why="the run's files were not kept"
    )
    assert settled.of[GUIDE].state == "held"


# --- whether a `none` stands -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reason", "failures", "stands"),
    [
        ("not-mine", 1, "artefact"),
        ("not-stale", 1, "artefact"),
        ("refused", 1, "setup"),
        ("out-of-step", 1, "setup"),
        ("upstream", 1, None),
        ("upstream", 5, None),
        ("failed", 1, None),
        ("failed", 2, "setup"),
        ("failed", 3, "setup"),
    ],
)
def test_a_none_stands_by_what_clears_it(reason: str, failures: int, stands: str | None) -> None:
    assert fc.standing(reason, failures, CONTRACT) == stands


def test_a_reason_off_the_list_has_no_standing() -> None:
    with pytest.raises(ValueError, match="not a `none` reason"):
        fc.standing("gone", 1, CONTRACT)
