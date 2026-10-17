"""software-analysis: a use case's steps and variants stay append-only (#1375).

`pkit analysis check-numbers` held to software-analysis DEC-001 point 3: journeys
and evidence cite a step or a variant by its number or letter, so a step or a
variant renumbered or removed against the default branch is reported, naming the
use case and the number or letter. One added, and a use case new in the change,
pass. The check reads the base as the number check does (COR-054), so a shallow
clone that lacks it fails rather than passing. It is `check-numbers`' second
check, never run by `pkit analysis validate` (COR-055 point 2), and binds where the
append-only rule, RS-SAN-002, binds, with a preview as the structure check's (#1370).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo, sign_nothing
from tests.analysis_repo import (
    ANALYSIS_SET,
    MAIN,
    NUMBERS,
    SA,
    SAN_REL,
    USE_CASES,
    VALIDATE,
    accepting_san,
    fill,
    installed,
    load_lib,
    prepare,
    run_script,
    stamped,
    with_status,
)

RUN = f"{USE_CASES}/UC-001-run-suite.md"
STRUCTURES = f"{SA.as_posix()}/project/structures.yaml"

#: UC-001's main path and variants, as the default branch holds them.
STEPS = (
    (1, "The tester chooses `Run`."),
    (2, "The system runs the suite."),
    (3, "The system shows the result."),
)
VARIANTS = (
    ("2a", "A test hangs. The system stops it, and the path goes on at step 3."),
    ("3a", "No test ran. The system says so, and the use case ends."),
)

#: Steps 1 and 2 swapped: each renumbered.
SWAPPED = ((1, STEPS[1][1]), (2, STEPS[0][1]), STEPS[2])

_MAIN_PATH = re.compile(r"(\*\*Main path:\*\*).*?(?=\n\*\*Postconditions:\*\*)", re.DOTALL)


def with_steps(
    text: str, steps: Sequence[tuple[int, str]], variants: Sequence[tuple[str, str]]
) -> str:
    """A use case's `text` with its main path and variants written over as given."""
    path = "\n".join(f"{number}. {step}" for number, step in steps)
    lettered = "\n".join(f"- **{label}.** {variant}" for label, variant in variants)
    written, count = _MAIN_PATH.subn(
        lambda m: f"{m.group(1)}\n\n{path}\n\n**Variants:**\n\n{lettered or 'None.'}\n", text
    )
    assert count == 1, text
    return written


def _on_main(repo: AdopterRepo) -> None:
    """`prepare`, then an actor and UC-001 with three steps and two variants on main, the
    rules of `SAN` accepted and bound through a set of the project's own, and the branch
    `topic` leaving main there."""
    prepare(repo)
    stamped(repo, "actor", "tester")
    stamped(repo, "use-case", "run-suite", "--actor", "ACT-tester")
    fill(repo)
    text = (repo.root / RUN).read_text(encoding="utf-8")
    repo.write({**accepting_san(repo), RUN: with_steps(text, STEPS, VARIANTS)})
    repo.commit("UC-001 on main")
    repo.checkout("topic", create=True)


@pytest.fixture
def branched(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with `topic` leaving main after UC-001 (`_on_main`)."""
    return installed(make_adopter_repo, monkeypatch, then=_on_main)


def numbers(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis check-numbers …`, run as the dispatcher runs it."""
    return run_script(repo, NUMBERS, *args)


def document(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(completed.stdout)


def rewrite(
    repo: AdopterRepo,
    steps: Sequence[tuple[int, str]],
    variants: Sequence[tuple[str, str]],
    path: str = RUN,
) -> None:
    text = (repo.root / path).read_text(encoding="utf-8")
    repo.write({path: with_steps(text, steps, variants)})


def fork_of(repo: AdopterRepo) -> str:
    return repo.git("merge-base", MAIN, "HEAD").stdout.strip()[:12]


def steps_line(answer: dict[str, Any]) -> str:
    (line,) = [s for s in answer["summary"] if s.startswith("steps")]
    return line


# --- what it reports (DEC-001 point 3) -----------------------------------------------------


def test_a_renumbered_step_or_variant_fails_naming_the_use_case_and_its_number(
    branched: AdopterRepo,
) -> None:
    """A step inserted under number 2 moves steps 2 and 3, and the variant of old step 2
    follows it to 3a: each is a renumbering, which points every citation of it at
    another step."""
    rewrite(
        branched,
        [(1, STEPS[0][1]), (2, "The system checks the suite."), (3, STEPS[1][1]), (4, STEPS[2][1])],
        [("3a", VARIANTS[0][1]), ("4a", VARIANTS[1][1])],
    )
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stdout + completed.stderr
    answer = document(completed)
    fork = fork_of(branched)
    assert [(f["severity"], f["location"]) for f in answer["findings"]] == [("error", RUN)] * 4
    line = (branched.root / RUN).read_text(encoding="utf-8").splitlines().index("3. " + STEPS[1][1])
    assert answer["findings"][0]["message"] == (
        f"UC-001's step 2, as main held it where this branch left it ({fork}), now stands as "
        f"step 3, at line {line + 1}: journeys and evidence cite a step by its number, so it is "
        "never renumbered or removed — give it back its number, and number a new step past the "
        "last (DEC-001 point 3)"
    )
    moved = [
        re.sub(r", at line \d+", "", f["message"]).split(":", 1)[0] for f in answer["findings"]
    ]
    held = f"as main held it where this branch left it ({fork}),"
    assert moved == [
        f"UC-001's step 2, {held} now stands as step 3",
        f"UC-001's step 3, {held} now stands as step 4",
        f"UC-001's variant 2a, {held} now stands as variant 3a",
        f"UC-001's variant 3a, {held} now stands as variant 4a",
    ]
    assert steps_line(answer) == (
        f"steps (RS-SAN-002, accepted): 1 use case(s) where the rule binds, compared with main "
        f"where this branch left it ({fork}); 0 new in this change, and 1 renumbering or "
        "removing a step or a variant."
    )
    read_view = numbers(branched, "--base", MAIN)
    assert read_view.returncode == 1
    assert f"  error  {RUN}\n" in read_view.stdout


def test_a_removed_step_or_variant_fails(branched: AdopterRepo) -> None:
    rewrite(branched, STEPS[:2], VARIANTS[:1])
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stdout + completed.stderr
    fork = fork_of(branched)
    assert [f["message"] for f in document(completed)["findings"]] == [
        f"UC-001's step 3, as main held it where this branch left it ({fork}), is gone: "
        "journeys and evidence cite a step by its number, so it is never renumbered or "
        "removed — put it back under its number, marked withdrawn if it no longer happens "
        "(DEC-001 point 3)",
        f"UC-001's variant 3a, as main held it where this branch left it ({fork}), is gone: "
        "journeys and evidence cite a variant by its step and letter, so it is never "
        "renumbered or removed — put it back under its label, marked withdrawn if it no "
        "longer happens (DEC-001 point 3)",
    ]


def test_a_step_whose_text_moved_to_a_new_number_is_renumbered_not_removed(
    branched: AdopterRepo,
) -> None:
    """Step 3's number left out, and its text written as step 7: a renumbering."""
    rewrite(branched, [*STEPS[:2], (7, STEPS[2][1])], VARIANTS)
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1
    ((finding,),) = [document(completed)["findings"]]
    assert "UC-001's step 3, as main held it" in finding["message"]
    assert "now stands as step 7, at line " in finding["message"]


# --- what passes ----------------------------------------------------------------------------


def test_added_and_edited_steps_and_variants_pass(branched: AdopterRepo) -> None:
    """A step added after the last, one added between two under a new number, a variant
    added after its step's last and one for a new step, and a step reworded: nothing
    renumbered or removed."""
    rewrite(
        branched,
        [
            (1, "The tester chooses `Run` in the menu."),
            (5, "The system checks the suite."),
            *STEPS[1:],
            (4, "The system keeps the result."),
        ],
        [*VARIANTS, ("2b", "A test fails. The system marks it, and goes on."), ("5a", "No suite.")],
    )
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    answer = document(completed)
    assert answer["findings"] == []
    assert "0 new in this change, and 0 renumbering" in steps_line(answer)


def test_a_use_case_new_in_the_change_passes_and_a_moved_one_is_compared(
    branched: AdopterRepo,
) -> None:
    """UC-002 is new in the change: nothing to compare. UC-001 moved into an area is
    known by its id, so its steps are still compared there."""
    stamped(branched, "use-case", "read-report", "--actor", "ACT-tester")
    fill(branched)
    moved = f"{USE_CASES}/core/UC-001-run-suite.md"
    branched.rename(RUN, moved)
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    answer = document(completed)
    assert answer["findings"] == []
    assert "2 use case(s) where the rule binds" in steps_line(answer)
    assert "1 new in this change, and 0 renumbering" in steps_line(answer)
    rewrite(branched, SWAPPED, VARIANTS, path=moved)
    swapped = numbers(branched, "--base", MAIN, "--json")
    assert swapped.returncode == 1
    assert [f["location"] for f in document(swapped)["findings"]] == [moved, moved]


# --- the base: as the number check reads it (COR-054) ---------------------------------------


@pytest.mark.parametrize(
    ("depth", "refusal"),
    [
        (("--single-branch", "--branch", "topic"), "the default branch 'main' resolves"),
        (("--no-single-branch",), "share no history to compare; in a shallow clone"),
    ],
)
def test_a_shallow_clone_that_lacks_the_default_branch_fails_rather_than_passing(
    branched: AdopterRepo, tmp_path: Path, depth: tuple[str, ...], refusal: str
) -> None:
    """A clone one commit deep holds no default branch, or no merge-base with it: the step
    renumbered on `topic` cannot be compared, and the check says why rather than pass."""
    rewrite(branched, SWAPPED, VARIANTS)
    branched.commit("topic swaps two steps")
    shallow = tmp_path / "shallow"
    source = f"file://{branched.root}"
    branched.git("clone", "-q", "--depth", "1", *depth, source, str(shallow))
    sign_nothing(shallow)
    clone = AdopterRepo(shallow, source_kit=branched.source_kit)
    clone.git("checkout", "-q", "topic")
    completed = numbers(clone, "--json")
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert refusal in completed.stderr


# --- where it runs, and where it binds ------------------------------------------------------


def test_validate_does_not_run_it(branched: AdopterRepo) -> None:
    """A renumbered step is `check-numbers`' alone: the validator answers about the working
    tree, and reads no base (COR-055 point 2)."""
    rewrite(branched, SWAPPED, VARIANTS)
    validated = json.loads(run_script(branched, VALIDATE, "--json").stdout)
    assert not [s for s in validated["summary"] if s.startswith("steps")]
    assert not [f for f in validated["findings"] if "now stands as step" in f["message"]]
    assert numbers(branched, "--base", MAIN).returncode == 1


def test_it_binds_under_the_append_only_rule_s_status_with_its_preview(
    branched: AdopterRepo,
) -> None:
    """The append-only rule proposed, the format rule accepted: nothing compared, and the
    summary says so, unless the preview is asked for, whose findings are reports that
    never fail. The format rule's status gates the structure alone (#1370)."""
    rewrite(branched, SWAPPED, VARIANTS)
    san = (branched.root / SAN_REL).read_text(encoding="utf-8")
    branched.write({SAN_REL: with_status(san, "RS-SAN-002", "proposed")})
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    answer = document(completed)
    assert answer["findings"] == []
    assert steps_line(answer) == (
        "steps (RS-SAN-002, proposed): not checked — the rule binds nothing until it is "
        "accepted (COR-051 point 4); `pkit analysis check-numbers --preview` shows what it "
        "would report."
    )
    previewed = numbers(branched, "--base", MAIN, "--preview", "--json")
    assert previewed.returncode == 0, previewed.stdout + previewed.stderr
    findings = document(previewed)["findings"]
    assert [f["severity"] for f in findings] == ["report", "report"]
    assert all(f["message"].startswith("preview: UC-001's step ") for f in findings)
    assert steps_line(document(previewed)).startswith(
        "steps (RS-SAN-002, proposed, previewed as accepted): 1 use case(s) where the rule "
        "would bind, as `pkit rule-sets reach --preview` reads it,"
    )
    assert numbers(branched, "--base", MAIN, "--preview").returncode == 0


def test_it_binds_where_the_append_only_rule_binds_whatever_the_format_rule(
    branched: AdopterRepo,
) -> None:
    """The append-only rule accepted and the format rule proposed: steps are compared,
    and a renumbering fails, since the append-only rule alone gates it (#1370)."""
    rewrite(branched, SWAPPED, VARIANTS)
    san = (branched.root / SAN_REL).read_text(encoding="utf-8")
    branched.write({SAN_REL: with_status(san, "RS-SAN-001", "proposed")})
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stdout + completed.stderr
    answer = document(completed)
    assert [f["severity"] for f in answer["findings"]] == ["error", "error"]
    assert steps_line(answer).startswith(
        "steps (RS-SAN-002, accepted): 1 use case(s) where the rule binds,"
    )


def test_it_binds_only_through_a_set_of_the_project_s_own(branched: AdopterRepo) -> None:
    """The append-only rule accepted, and no set of the project's own: it binds on no use case,
    so nothing is compared, and the summary says so."""
    rewrite(branched, SWAPPED, VARIANTS)
    branched.write({ANALYSIS_SET: None})
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    answer = document(completed)
    assert answer["findings"] == []
    assert steps_line(answer) == (
        "steps (RS-SAN-002, accepted): nothing compared. The rule does not bind on 1 of the 1 "
        "use case(s) here, so they are not compared."
    )


def test_project_structures_it_cannot_read_fail_rather_than_pass(branched: AdopterRepo) -> None:
    """The project's own structures relabel the parts it reads: while they cannot be read,
    nothing is compared, and the check fails where the rule binds, saying why."""
    rewrite(branched, SWAPPED, VARIANTS)
    branched.write({STRUCTURES: "kinds: 3\n"})
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stdout + completed.stderr
    answer = document(completed)
    assert [(f["severity"], f["location"]) for f in answer["findings"]] == [("error", STRUCTURES)]
    assert steps_line(answer).startswith(
        f"steps (RS-SAN-002, accepted): not checked — the project's own structures, {STRUCTURES}, "
        "cannot be read;"
    )


# --- the comparison itself --------------------------------------------------------------------


def test_steps_and_variants_are_read_as_the_structure_check_reads_them() -> None:
    """Bold and plain numbers alike, a variant's letter in either case, and the text after
    the number, white space folded."""
    append_only, structure = load_lib("append_only", "structure")
    kind = structure.read_kinds()["use-case"]
    text = (
        "---\nid: UC-001\n---\n\n# UC-001 — Run\n\n**Main path:**\n\n"
        "1. The tester\n   chooses `Run`.\n- **2.** The system runs it.\n\n"
        "**Variants:**\n\n- **2A.** It hangs.\n- 2b. It fails.\n\n**Postconditions:** Done.\n"
    )
    read = append_only.read(text, kind)
    assert [(i.key, i.text) for i in read.steps] == [
        ("1", "The tester chooses `Run`."),
        ("2", "The system runs it."),
    ]
    assert [(i.key, i.text) for i in read.variants] == [("2a", "It hangs."), ("2b", "It fails.")]


@pytest.mark.parametrize(
    ("then", "now", "found"),
    [
        # A swap renumbers both.
        (
            [("1", "A"), ("2", "B")],
            [("1", "B"), ("2", "A")],
            [("1", "renumbered"), ("2", "renumbered")],
        ),
        # A copy of a step's text under a new number moves nothing.
        ([("1", "A"), ("2", "B")], [("1", "A"), ("2", "B"), ("3", "B")], []),
        # Two steps of one text, each kept: nothing.
        ([("1", "A"), ("2", "A")], [("1", "A"), ("2", "A")], []),
        # A reworded step is an edit; one gone with no text left anywhere is removed.
        ([("1", "A"), ("2", "B")], [("1", "A2")], [("2", "removed")]),
        # A step with no text is never found elsewhere.
        ([("1", ""), ("2", "B")], [("2", ""), ("3", "B")], [("1", "removed"), ("2", "renumbered")]),
    ],
)
def test_what_counts_as_renumbered_or_removed(
    then: list[tuple[str, str]], now: list[tuple[str, str]], found: list[tuple[str, str]]
) -> None:
    (append_only,) = load_lib("append_only")

    def items(pairs: list[tuple[str, str]]) -> list[Any]:
        return [append_only.Item(key, n, text) for n, (key, text) in enumerate(pairs, 1)]

    departures = append_only._departures(items(then), items(now))
    assert [(key, how) for key, how, _moved in departures] == found
