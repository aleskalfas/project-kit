"""project-management: a seat's agent runs its role's loop (#2143).

The project-manager agent reads its seat at the start of a session, and runs the
procedure of the seat's role from the pm skill (DEC-059 point 8, DEC-029). The
planner slices work and files it into the pool every seat shares, and the worker
takes the next ready Task, builds it and opens its pull request. Batch planning
plans a foundation first where the Tasks would share a choice nothing settles
yet (DEC-060). Held here:

- **the pm skill composes the work loop,** `work-loop.md`, deployed beside the
  other sub-procedures, and clean under `pkit refs validate`
- **the agent takes its seat first,** before any other operation, and keeps the
  loop's steps in the skill, a thin dispatcher (DEC-029). Neither the agent's
  seat section nor the loop names a harness
- **every command the loop gives is one the capability ships,** with flags that
  command takes, so the procedure cannot drift from the commands unnoticed
- **no role merges:** the loop gives no merge, and leaves the merge to the person
- **a released seat's Tasks in Review:** the loop says that `seats` names each
- **batch planning names the shared choices before it slices,** and a first plan
  files the foundation only (DEC-060)
- **the storyboard walks one round of each role** the loop serves
- **the worker mends its own pull requests first** (#2184): one that conflicts
  with the default branch, by merging that branch in, then a fix round, before
  the next Task. A released seat's pull request in Review is the person's to
  hand over, and the storyboard and the README show each situation
- **the README's exit table of `next-task`** names a declined prompt
- **a worker builds each Task through a fresh helper** (#2259): unnamed, so its
  whole result comes back (DEC-029), in the clone itself, with a brief that
  carries the Task, its branch and the conventions, writing nothing to GitHub.
  The session checks the result, pushes and opens the pull request, and builds
  in its own session where the harness cannot start a helper
- the checks flag a verb or a flag the capability does not ship, and pass one it does
"""

from __future__ import annotations

import re
import subprocess
import sys
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import refs

REPO = Path(__file__).resolve().parents[1]
CAPABILITY = REPO / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
SKILL = CAPABILITY / "skills" / "pm"
DISPATCHER = SKILL / "pm.md"
LOOP = SKILL / "work-loop.md"
BATCH_PLAN = SKILL / "batch-plan.md"
AGENT_FOLDER = CAPABILITY / "agents" / "project-manager"
AGENT = AGENT_FOLDER / "project-manager.md"
STORYBOARD = AGENT_FOLDER / "storyboard.md"
README = CAPABILITY / "README.md"
DEPLOYED = REPO / ".claude" / "skills" / "pm"

#: The section of the agent's "How you work" that takes its seat, first of all.
SEAT_SECTION = "### 0. Take your seat, first"

#: The names of harnesses an agent definition could lean on. A seat's agent runs
#: wherever the project runs it, so the loop and the seat section name none.
_HARNESSES = re.compile(r"\b(?:claude|codex|cursor|copilot|gemini|aider|windsurf)\b", re.I)

#: A command of the capability, as a procedure gives it: `pkit pm <verb>` and the
#: rest of its code span or line.
_COMMAND = re.compile(r"pkit pm ([a-z][a-z-]*)([^`\n]*)")
_FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z-]*)")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load(text: str) -> Any:
    return YAML(typ="safe").load(text)


def _front(path: Path) -> dict[str, Any]:
    _, front, _body = _text(path).split("---\n", 2)
    return _load(front) or {}


def _section(text: str, heading: str) -> str:
    """The section under *heading*, up to the next heading of its level or higher."""
    level = len(heading) - len(heading.lstrip("#"))
    after = text.split(f"{heading}\n", 1)[1]
    ends = re.search(rf"(?m)^#{{1,{level}}} ", after)
    return after[: ends.start()] if ends else after


def _flat(text: str) -> str:
    return " ".join(text.split())


@cache
def _help(verb: str) -> str:
    """What the capability's command *verb* prints for `--help`."""
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / f"{verb}.py"), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (verb, completed.stderr)
    return completed.stdout


def unshipped_verbs(text: str) -> list[str]:
    """Each verb *text* gives as `pkit pm <verb>` that no script of the capability carries."""
    return sorted(
        {verb for verb, _rest in _COMMAND.findall(text) if not (SCRIPTS / f"{verb}.py").is_file()}
    )


def unknown_flags(text: str) -> list[str]:
    """Each flag *text* gives a shipped command that the command's `--help` does not
    list, as `<verb> <flag>`."""
    found: list[str] = []
    for verb, rest in _COMMAND.findall(text):
        if not (SCRIPTS / f"{verb}.py").is_file():
            continue
        for flag in _FLAG.findall(rest):
            if not re.search(rf"(?<![\w-]){re.escape(flag)}\b", _help(verb)):
                found.append(f"{verb} {flag}")
    return sorted(set(found))


# --- the pm skill composes the work loop --------------------------------------------


def test_the_pm_skill_composes_the_work_loop() -> None:
    front = _front(DISPATCHER)
    assert "work-loop.md" in front["composes"]
    assert ".pkit/capabilities/project-management/skills/pm/work-loop.md" in front["reads"]["paths"]
    assert LOOP.is_file()
    # The dispatcher routes to it from its table of operations.
    assert "| work-loop |" in _text(DISPATCHER)


def test_the_work_loop_is_deployed_beside_the_other_sub_procedures() -> None:
    assert (DEPLOYED / "SKILL.md").resolve() == DISPATCHER.resolve()
    assert (DEPLOYED / "work-loop.md").resolve() == LOOP.resolve()


def test_refs_find_nothing_in_the_skill_or_the_agent() -> None:
    folders = tuple(str(p.relative_to(REPO)) for p in (SKILL, AGENT_FOLDER))
    assert [i for i in refs.validate_corpus(REPO) if i.location.startswith(folders)] == []


# --- the agent takes its seat first --------------------------------------------------


def test_the_agent_takes_its_seat_before_any_other_operation() -> None:
    text = _text(AGENT)
    how = text.split("## How you work\n", 1)[1]
    assert re.findall(r"(?m)^### .+$", how)[0] == SEAT_SECTION
    seat = _flat(_section(how, SEAT_SECTION))
    assert "`work-loop` sub-procedure" in seat
    assert "`pkit pm seats`" in seat and "`pkit pm take-seat`" in seat
    assert "[project-management:DEC-059-topology-of-seats] point 8" in seat
    # It dispatches to the loop, beside the other sub-procedures.
    assert "`work-loop.md`" in _section(how, "### 4. Dispatch to the sub-procedure")


def test_the_agent_keeps_the_loop_s_steps_in_the_skill() -> None:
    """A thin dispatcher (DEC-029): the agent names the loop, and the loop's commands
    live in the sub-procedure."""
    text = _text(AGENT)
    for step in ("next-task", "review-work", "release-seat"):
        assert step not in text, step
        assert step in _text(LOOP), step


def test_neither_the_seat_section_nor_the_loop_names_a_harness() -> None:
    how = _text(AGENT).split("## How you work\n", 1)[1]
    assert _HARNESSES.findall(_section(how, SEAT_SECTION)) == []
    assert _HARNESSES.findall(_text(LOOP)) == []


# --- every command the loop gives is one the capability ships ------------------------


@pytest.mark.parametrize("path", [LOOP, BATCH_PLAN, AGENT, STORYBOARD], ids=lambda p: p.name)
def test_every_command_given_is_one_the_capability_ships(path: Path) -> None:
    text = _text(path)
    assert unshipped_verbs(text) == []
    assert unknown_flags(text) == []


def test_the_loop_gives_the_commands_of_each_role() -> None:
    verbs = {verb for verb, _rest in _COMMAND.findall(_text(LOOP))}
    seat = {"seats", "take-seat", "release-seat"}
    planner = {"promote-issue"}
    worker = {"next-task", "show-issue", "check-criterion", "open-pr", "review-work"}
    assert seat | planner | worker <= verbs


# --- no role merges --------------------------------------------------------------------


def test_the_loop_gives_no_merge_and_leaves_it_to_the_person() -> None:
    text = _text(LOOP)
    verbs = {verb for verb, _rest in _COMMAND.findall(text)}
    assert not verbs & {"land-work", "done-work", "merge-pr"}
    assert "**The merge is the person's.**" in text
    assert "[project-management:DEC-059-topology-of-seats] point 8" in _flat(text)


def test_the_worker_passes_no_override_that_is_the_person_s() -> None:
    """A refusal of `review-work` is mended, never overridden: `--force` and
    `--bypass-owner` are the person's (DEC-014), and the clash guard is one of the
    loop's checks."""
    text = _text(LOOP)
    for verb, rest in _COMMAND.findall(text):
        assert "--force" not in rest and "--bypass" not in rest, (verb, rest)
    assert "Never pass `--force` or `--bypass-owner`" in text


def test_the_worker_goes_on_with_what_its_clone_has_in_flight_first() -> None:
    """A new session resumes its Task In Progress, or a fix round, before it takes
    another (DEC-059 point 7), and goes on from a taken-over Task's branch."""
    worker = _section(_text(LOOP), "## 3. The worker's loop")
    resume = worker.index("**Go on with what this clone has in flight,**")
    assert resume < worker.index("`pkit pm next-task --yes`")
    flat = _flat(worker)
    assert (
        "take a new Task only once nothing is in flight, no pull request of yours waits on "
        "you, and the working tree is clean." in flat
    )
    assert "**A Task taken over.**" in flat and "Never force-push" in flat


def test_the_worker_mends_its_own_pull_requests_before_the_next_task() -> None:
    """Each time the loop starts, and each time it comes back after `review-work`,
    the worker reads its pull requests in Review by their branches: a conflict with
    the default branch first, then a fix round, and only then the next Task (#2184)."""
    worker = _section(_text(LOOP), "## 3. The worker's loop")
    flat = _flat(worker)
    assert "each time the loop starts and each time it comes back here after `review-work`" in flat
    assert "`pkit pm show-pr <branch>`" in flat
    conflict = worker.index("**It conflicts with the default branch,**")
    fix = worker.index("**A verdict at its head asks for changes:**")
    assert conflict < fix < worker.index("`pkit pm next-task --yes`")
    # A conflict is mended by merging the default branch in, never by rewriting.
    assert "merge the default branch in" in flat
    assert "Never rebase and never force-push" in flat
    # The fix round is transition-state's, and carries only the blocking findings.
    assert "[transition-state](transition-state.md)'s review step" in flat
    assert "fix only the blocking ones" in flat
    # The next round comes back to step 1.
    assert "go back to 1" in _flat(worker.split("6. **Take the next Task.**", 1)[1])


def _build_step() -> str:
    worker = _section(_text(LOOP), "## 3. The worker's loop")
    return worker.split("4. **Have a fresh helper build it.**", 1)[1].split("\n5. **", 1)[0]


def test_the_worker_builds_each_task_through_a_fresh_unnamed_helper() -> None:
    """Each Task starts in a clean context: a fresh helper builds it, passed no name
    so its whole result comes back (DEC-029's dispatch discipline), in the clone
    itself, since a linked worktree's identity is not decided (DEC-059 point 6)
    (#2259)."""
    worker = _section(_text(LOOP), "## 3. The worker's loop")
    assert "4. **Have a fresh helper build it.**" in worker
    assert worker.index("`pkit pm next-task --yes`") < worker.index("**Have a fresh helper")
    assert worker.index("**Have a fresh helper") < worker.index("`pkit pm open-pr <N>")
    step = _flat(_build_step())
    assert "It starts with none of this session's context" in step
    assert "no Task inherits the context of the one before it" in step
    assert "Pass the helper no name, so its whole result comes back to you" in step
    assert "[project-management:DEC-029-project-manager-agent-shape]" in step
    assert "never as the agent this seat names, so it takes no seat" in step
    assert "not in a linked worktree" in step
    assert "(DEC-059 point 6)" in step


def test_the_helper_s_brief_carries_the_task_its_branch_and_the_conventions() -> None:
    """The helper sees only its brief. It commits, and writes nothing to GitHub,
    since the session writes as the seat (#2259)."""
    step = _flat(_build_step())
    brief = step.split("**The brief**", 1)[1].split("**A foundation's choice", 1)[0]
    for part in ("number, title and branch", "acceptance criteria", "`## Doc impact` boxes"):
        assert part in brief, part
    assert "the project's conventions, its rules for commits among them" in brief
    assert "the tests and checks to run" in brief
    assert "the answers the project's change check asks" in brief
    assert "push nothing and write nothing to GitHub" in brief
    assert "runs none of the capability's commands that write" in brief
    assert "a sentence on what changed in it" in brief
    assert "makes no other choice in its place" in brief
    assert "what is left undone" in brief


def test_the_session_checks_the_result_then_ticks_pushes_and_opens_the_pr() -> None:
    """The seat's session acts on the result only once the clone bears it out, and
    makes every write as the seat: the ticks, the push and the pull request. It
    checks the seat before the helper starts and again before the push (DEC-059
    point 9)."""
    step = _flat(_build_step())
    assert step.index("Before you start it, check that `pkit pm seats`") < step.index(
        "**The brief**"
    )
    check = step.split("**Check the result against the clone**", 1)[1]
    check = check.split("**A result that leaves", 1)[0]
    assert "the working tree is clean" in check
    assert "Take no criterion on the helper's word alone" in check
    assert "`pkit pm check-criterion <N> <index>`" in check
    assert check.index("check-criterion") < check.index("Check the seat again")
    assert check.index("Check the seat again") < check.index("push the branch")
    assert "start one more fresh helper" in step
    assert "end the loop, and tell the person" in step


def test_a_foundation_that_does_not_hold_comes_before_a_second_helper() -> None:
    step = _build_step()
    foundation = step.index("**A foundation's choice that does not hold,** in the result")
    assert foundation < step.index("**A result that leaves the Task unfinished:**")
    assert "start no other helper" in _flat(step)


def test_a_result_the_clone_does_not_bear_out_discards_nothing() -> None:
    step = _flat(_build_step())
    lead = "**A result the clone does not bear out,**"
    assert lead in step
    assert "discard nothing" in step.split(lead, 1)[1].split("- **", 1)[0]


def test_dec_059_lets_a_worker_build_through_a_helper_that_acts_as_no_instance() -> None:
    """The procedure rests on DEC-059 points 2 and 6, refined in place (#2259)."""
    dec = _flat(_text(CAPABILITY / "decisions" / "DEC-059-topology-of-seats.md"))
    assert "a fresh helper builds each Task, so that each Task starts in a clean context" in dec
    assert "A helper that a worker starts to build a Task acts as no instance" in dec
    assert "**Why a worker builds each Task through a fresh helper.**" in dec


def test_the_worker_builds_in_its_session_where_the_harness_cannot_start_a_helper() -> None:
    step = _flat(_build_step())
    lead = "**Where the harness offers no way to start a helper,**"
    assert lead in step
    fallback = step.split(lead, 1)[1].split("- **", 1)[0]
    assert "say so, and build the Task in this session, as before" in fallback
    # A start that fails is retried once, then the loop ends (core rule 21).
    assert "run it once more, then end the loop and report what failed" in fallback


def test_the_storyboard_s_worker_builds_through_a_fresh_helper() -> None:
    worker = _flat(_section(_text(STORYBOARD), "## Scenario 13: A worker's round"))
    assert "*Starting a fresh helper to build it…*" in worker
    assert "with no name, so its whole result comes back" in worker
    assert "writes nothing to GitHub" in worker


def test_a_released_seat_s_pull_request_in_review_is_the_person_s_to_hand_over() -> None:
    """`next-task` never offers a Task in Review (DEC-059 point 7). It waits on its
    reviewers and the person, who lands it or hands it over (point 9, DEC-035
    point 4). A worker takes one up only where the person hands it over (#2184)."""
    worker = _flat(_section(_text(LOOP), "## 3. The worker's loop"))
    lead = "**A pull request that a released seat left in Review.**"
    assert lead in worker
    paragraph = worker.split(lead, 1)[1]
    assert "`next-task` never offers a Task in Review" in paragraph
    assert "[project-management:DEC-059-topology-of-seats] points 5 and 7" in paragraph
    assert "[project-management:DEC-035-instance-ownership] point 4" in paragraph
    assert "Take one up only where the person hands it to you." in paragraph
    # A hand-over moves no claim yet, and the loop says so.
    assert "`handoff-issue` does not move a claim between clones yet" in _flat(
        _section(_text(LOOP), "## Not in the loop yet")
    )


def test_the_worker_starts_its_task_with_yes_and_no_person_s_move_is_its_own() -> None:
    """Starting a Task is the agent's own move (`workflow.yaml`: Backlog to In
    Progress is agent-autonomous), so the loop passes `--yes` to `next-task`. The
    moves a person authorises stay the person's."""
    workflow = _load(_text(CAPABILITY / "schemas" / "workflow.yaml"))
    transitions = workflow["process"]["transitions"]
    [start] = [t for t in transitions if (t["from"], t["to"]) == ("backlog", "in-progress")]
    assert start["authorisation"] == "agent-autonomous"
    assert "`pkit pm next-task --yes`" in _text(LOOP)
    # Scheduling a Task into the pool is the person's: the planner promotes it only
    # with the person's approval of the plan as its reason.
    [schedule] = [t for t in transitions if (t["from"], t["to"]) == ("todo", "backlog")]
    assert schedule["authorisation"] == "user"
    planner = _flat(_section(_text(LOOP), "## 2. The planner's loop"))
    assert "`pkit pm promote-issue <N> --reason" in planner
    assert "approval" in planner


def test_the_loop_says_seats_names_the_tasks_in_review_a_release_left() -> None:
    """A release leaves the clone's Tasks in Review with no owner, and no worker's
    loop takes them up: the loop says that `seats` names each, with its pull
    request, for the person (#2196)."""
    end = _flat(_section(_text(LOOP), "## 4. When the seat's work ends"))
    assert "`pkit pm seats` then names each such Task in Review, with its pull request" in end
    assert "for the person to land or to hand over" in end


# --- batch planning plans a foundation first --------------------------------------------


def test_batch_planning_names_the_shared_choices_before_it_slices() -> None:
    text = _text(BATCH_PLAN)
    slicing = _section(text, "### 3. Propose the slicing")
    first = slicing.index("**First, name the shared choices.**")
    assert first < slicing.index("**Hierarchy choice**")
    for judgement in ("**Settled:**", "**In hand:**", "**Open:**"):
        assert judgement in slicing, judgement
    flat = _flat(slicing)
    assert "[project-management:DEC-060-foundation-before-slices]" in flat
    assert "**Slice vertically** where the project declares a topology" in slicing
    # The first plan files the EPIC and the foundation's Feature, and no slice.
    assert "No slice is filed." in flat
    assert "The second plan starts once" in flat


def test_batch_planning_reads_the_seats_and_shows_each_judgement_at_its_gate() -> None:
    text = _text(BATCH_PLAN)
    assert "`pkit pm seats`" in _section(text, "### 1. Read intent and reference material")
    gate = _flat(_section(text, "### 5. Single approval gate"))
    assert "each shared choice with its judgement" in gate
    # The person sees, and so authorises, each move into Backlog (DEC-006).
    assert "Which issues the plan schedules into Backlog on approval" in gate


def test_batch_planning_schedules_through_the_capability_s_audited_command() -> None:
    """A Milestone schedules the issue it is attached to, so batch planning attaches
    one only through `promote-issue`, which audits the move, and never through a raw
    `gh issue edit`, which the agent is denied anyway."""
    filing = _section(_text(BATCH_PLAN), "### 6. File via primitives")
    assert "gh issue edit" not in filing
    assert '`pkit pm promote-issue <N> --reason "<the user\'s approval of the plan>"`' in filing


# --- the storyboard walks one round of each role ------------------------------------------


def test_the_storyboard_walks_one_round_of_each_role() -> None:
    text = _text(STORYBOARD)
    planner = _flat(_section(text, "## Scenario 12: A planner's round"))
    worker = _flat(_section(text, "## Scenario 13: A worker's round"))
    assert "pkit pm take-seat" in planner and "first plan" in planner
    assert "pkit pm next-task --yes" in worker and "pkit pm review-work" in worker
    # The agent says that its storyboard walks the loops too.
    assert "the same storyboard walks one round of each role's loop" in _flat(_text(AGENT))


def test_the_storyboard_shows_each_situation_of_a_later_round_once() -> None:
    """A conflict, a fix round, and a released seat's pull request in Review, each
    once, in the round that follows Scenario 13 (#2184)."""
    text = _text(STORYBOARD)
    later = _flat(_section(text, "## Scenario 14: A worker's later round"))
    walk = later.split("### Walkthrough", 1)[1].split("### Behind the scenes", 1)[0]
    for situation in ("conflicts with `main`", "asks for changes", "you released"):
        assert walk.count(situation) == 1, situation
    assert "pkit pm show-pr feat/320-export-csv" in later
    assert "git merge origin/main" in later and "Never a rebase or a force-push" in later
    assert "`pkit pm next-task --yes`" in later and "never offers #325" in later


# --- the README ------------------------------------------------------------------------------


def test_the_readme_says_what_the_worker_does_in_each_situation() -> None:
    section = _flat(
        _text(README).split("#### A seat's agent and its loop", 1)[1].split("\n#### ", 1)[0]
    )
    assert "a pull request of its own that conflicts with the default branch" in section
    assert "a fix round on one whose verdict asks for changes" in section
    assert "**A pull request that a released seat left in Review**" in section


def test_the_readme_says_each_task_starts_in_a_clean_context() -> None:
    section = _flat(
        _text(README).split("#### A seat's agent and its loop", 1)[1].split("\n#### ", 1)[0]
    )
    assert "has a fresh helper agent build it in its own clone" in section
    lead = "**Each Task starts in a clean context**"
    assert lead in section
    bullet = section.split(lead, 1)[1].split("- **", 1)[0]
    assert "passes the helper no name" in bullet
    assert "[project-management:DEC-029-project-manager-agent-shape]" in bullet
    assert "writes nothing to GitHub" in bullet
    assert "Where the harness cannot start a helper" in bullet


def test_the_readme_lists_show_pr_s_mergeable_field_and_its_branch_form() -> None:
    section = _text(README).split("#### Read-only diagnostics", 1)[1].split("\n#### ", 1)[0]
    [fields] = [line for line in section.splitlines() if line.startswith("- **`show-pr`**")]
    assert "`mergeable`" in fields
    assert "pkit pm show-pr feat/42-add-dispatcher" in section


def test_the_readme_s_next_task_exit_table_names_a_declined_prompt() -> None:
    section = _text(README).split("#### Taking the next ready Task", 1)[1].split("\n#### ", 1)[0]
    [row] = [line for line in section.splitlines() if line.startswith("| 0 |")]
    assert "`Start #N?`" in row and "`aborted.`" in row


# --- the checks -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,flagged",
    [
        ("Run `pkit pm take-a-seat --role worker`.", ["take-a-seat"]),
        ("```\npkit pm next-work --yes\n```", ["next-work"]),
    ],
)
def test_the_check_flags_a_verb_the_capability_does_not_ship(text: str, flagged: list[str]) -> None:
    assert unshipped_verbs(text) == flagged


@pytest.mark.parametrize(
    "text,flagged",
    [
        ("Run `pkit pm next-task --all`.", ["next-task --all"]),
        ("`pkit pm take-seat --seat planner`", ["take-seat --seat"]),
    ],
)
def test_the_check_flags_a_flag_the_command_does_not_take(text: str, flagged: list[str]) -> None:
    assert unknown_flags(text) == flagged


@pytest.mark.parametrize(
    "text",
    [
        "Run `pkit pm next-task --yes`.",
        "`pkit pm take-seat [<name>] [--role <role>] --agent <definition>`",
        "`pkit pm open-pr <N> --draft --body-file <file>`",
    ],
)
def test_the_checks_pass_a_command_the_capability_ships(text: str) -> None:
    assert unshipped_verbs(text) == []
    assert unknown_flags(text) == []
