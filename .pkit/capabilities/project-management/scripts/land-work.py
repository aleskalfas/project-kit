#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "pathspec>=0.12",
# ]
# ///
"""Project-management capability — land-work (#1203).

Lands an issue's pull request in one command: waits for the checks on the PR's
head, has the reviewers whose verdicts are not fresh review that head, shows
the findings they left for a person to judge, reads the answers the change
wrote from the change check, runs the change check on the merge with the base
as it stands, and merges it through `done-work`. A project can name the checks
that start the review: the reviewers then run beside the rest, and the merge
still waits for every check. It composes
the verbs' own functions — the CI gate's reading (`_lib.ci_checks`),
`review-pr`'s review, `done-work`'s merge — and adds no review loop or merge
mechanic of its own. The rules it adds are on the answers the change wrote
and on the findings a reviewer left for a person to judge
([project-management:DEC-055-pr-lists-answers],
[project-management:DEC-065-answers-read-from-check]): it stops on answers it
cannot read, writes no list of them into the description and removes one an
earlier run left; a change with answers merges under the same authorisation
as any other, and the lines above the `ready:` line, the prompt or the merge
tell what changed and what is left out of date, as information. It prints each
`[person]` finding whole, and a `--yes` run merges only on verdicts carrying
them that it found when it started, standing for the head it merges.

    land-work <N> [--yes --expect-head SHA] [--wait-minutes M | --no-wait]
                  [--dry-run]

`--yes` is the authorisation to merge, and it is for a named head
([project-management:DEC-055-pr-lists-answers] point 3): `--yes` without
`--expect-head` is refused (exit 2) before anything is read, waited for or
reviewed (#1760).

Each step prints one line; the verbs it composes print their detail above it.
It stops at the first step that cannot go on, and its last line says why.
Just before that last line, whatever the outcome, it prints how many of the
fixers' proposals wait for the person, `fixers: N proposals wait for you`, with
the queue's folder, where any wait ([project-management:DEC-056-drift-fixers]
point 6, `_lib.drift_queue`). A queue that cannot be read prints a `warn:` line
there instead, and changes nothing else.

  head    The issue's branch and its open PR, found as `done-work` finds them
          — "gh did not answer" is never read as "no open PR". Of several
          local branches matching the issue, the one with its open PR; with
          more than one open, or when gh does not say, the run stops. The
          branch read here is handed to `review-pr` and `done-work`, so the
          open PRs are read once (`_lib.issue_branch`, #1608). The PR's head
          on GitHub is read once and pinned. `--expect-head` stops the run when
          it is not the head named, unless the authorisation for that head
          covers it: every change since lies inside answer files the change
          adds, a clean merge of the base counting as none, as the backbone
          answers
          it (`friction_answers.covers`, DEC-055 point 3). The line then says
          so, and the run goes on at the later head. Refused when the local branch holds
          commits that head lacks (the line gives the push) or has diverged
          from it. A local branch behind the head, or a checkout on another
          branch, is noted: land-work lands the head on GitHub, never the
          working tree. With no open PR it hands over to `done-work` only to
          complete a PR that has merged. Two open PRs that share the branch's
          name stop the run, naming both, since one may be a fork's. The pinned
          head then takes the test of which heads may start programs
          (`_lib.head_programs`, DEC-067); one that passes runs as any head
          does, and nothing is said of it. For a head from elsewhere the change
          check runs here, from git objects, before the run waits for checks or
          starts a reviewer. Where it needs a resolver, the person at a terminal
          can name the head for this run. Off a terminal, under `--yes` or in a
          dry run, the run stops (exit 9), and no flag goes on.
  ci      The PR's checks on the pinned head, read with the head they belong
          to and judged by the CI gate `done-work` applies, waited for up to
          `--wait-minutes` (default 30; `--no-wait` reads once). No check
          reported yet is never green. A failed check, and a PR that conflicts
          with its base (on which no `pull_request` workflow runs), stop the
          run before the review. So does a PR the host reads as behind a base
          it merges only up to date, with the merge of the base to make,
          unless the base merges through a queue, read once a run; where
          whether it does cannot be read, a line says so and the run goes on
          ([project-management:DEC-064-base-merge-named] point 2). Where the
          project names the checks that start the review
          (`review.agents.start_after_checks`), this step ends once each has
          passed and none has failed, and its line says the review starts
          beside the rest. A name no check bears is read once more, then
          warned of. The step then runs again once the review has ended,
          waiting up to as long for the rest, and every stop above stops the
          run before the merge ([project-management:DEC-063-task-builder]
          point 8). A `--yes` run names none, so it runs no reviewer until
          every check has passed: no stop of this step can fall between a
          verdict it posts and the findings' hold on it (DEC-055 point 3). A
          `--no-wait` run names none either, since it only reads.
  review  In agent review mode, `review-pr`'s review on the pinned head: a
          verdict judged fresh for that head is kept, a stale or missing one
          re-run. A CHANGES_REQUESTED, kept or new, stops the run before the
          merge with the first line of each `[block]` finding; a reviewer
          that could not be run stops it too. Where the review started beside
          checks still running, that last line also names each that has failed
          by then, so one fix round carries both. The advisories of the approvals
          are printed (DEC-028's finding tags, read by
          `_lib.agent_verdicts.findings`). `review-pr` works out the required
          set, so a reviewer a capability contributes runs though the project
          registers no local reviewer of its own (#1934). In human mode, and
          where the PR requires no local reviewer, there is nothing to run:
          the approval is `done-work`'s gate.
  findings to judge
          Each `[person]` finding, printed whole with the verdict's reviewer,
          from each reviewer's latest verdict as the merge gate selects it
          (`gate_candidates`, `gate_membership`), in either review mode; a
          verdict that no longer stands for the pinned head, by the gate's
          freshness rule, is printed marked stale. Its line begins
          `findings to judge:` (`FINDINGS`); a run with none prints nothing.
          A `--yes` run merges only when it found, at its start, every such
          verdict, and each stands for the pinned head; one posted by this
          run, or while it ran up to this step's read, stops it at `ready:`,
          and one that does not stand for the head stops every `--yes` run
          there, naming the review it waits for (DEC-055 point 3). Where the
          review ran beside checks, this step runs before the wait for the
          rest, so no way that wait ends hides a verdict the run posted, and
          again after it, for one posted during it. A stop inside the review
          step prints them too, with this step's line, just above its last
          line, so no way that step ends hides one. A verdict is judged there
          for the head the PR has then, and what cannot be read draws a `warn:`
          line and leaves the stop as it is. Verdicts
          that cannot be read, or whose reviewers cannot be resolved, stop
          the run, and so does a remote reviewer's `[person]` finding on a PR
          whose author cannot be read, since its verdict cannot be told from
          the author's own (#1485); this step comes before the answers', so
          such a stop has written nothing. Beside the findings, a line each:
          every decision record accepted where the head left the PR's base
          that the change alters, with each point it adds, alters or retires,
          as the backbone lists them at the pinned head
          (`_lib.accepted_records`, `pkit decisions check-diff --json`,
          #2161), counted among the findings to judge. They stand for the
          head, so a `--yes` for it covers them. At a later head an earlier
          head's authorisation covers, a list other than the one at the head
          authorised, or one that cannot be read there, stops a `--yes` run
          at `ready:`. A list that cannot be read stops the run.
  answers The answers the change wrote, and the friction settings it alters,
          derived from the change check at the pinned head against the PR's
          base (`_lib.friction_answers`, DEC-065 point 2). Its line begins
          `documents this change affects:` (`STEP`) and counts the documents
          the answers are on. What the person who authorises the merge is told
          is kept for the lines just above the `ready:` line, the prompt or the
          merge (DEC-065 point 4): what changed in each `updated` document, in
          the sentence its author wrote under the description's `## What
          changed in each updated document`; each document and each target of
          a link left out of date, with the words naming its follow-up; each
          answer the change check did not ask for, with its words; each
          friction setting changed. No line is told for any other answer. Each
          item under the sentences' heading it cannot read draws a `warn:` line
          naming its line and the form a sentence takes, and each sentence there
          on a document the change check does not mark `updated` draws one
          naming the edit that removes it, since no reviewer checks it
          (DEC-055 point 3); neither refuses. The description carries no list
          of the answers: the region an earlier run left there, both its
          markers and the heading directly above, is removed, and the line says
          so. A start marker with no end marker after it draws a `warn:` line,
          and the description stays as it is (DEC-065 point 1). Refused: answers
          that cannot be read (nothing is merged on a guess), a file the change
          touches whose front matter does not parse, a sentence that reads as a
          closing reference, which the host would close an issue with at merge,
          and — where there are answers or settings — a base whose commits since
          the head left it changed a file the answers' words are on, the file
          the change check names for an answer, an answer file or the
          artefact's own, or the friction settings the change alters (DEC-065
          point 5). A write the host answers with an error merges nothing.
          Beside what is told, each revalidation on the base's tip that the
          change's answer on its document did not read, which the check derived
          against the base it fetched (`answered_apart_at_tip`, DEC-055 point
          3): once merged, each and the change's own are answered apart. It
          stops nothing. So is each grant and refusal the change adds to the
          fixers' grant list or removes from it, a line each: `fixers` in this
          capability's project configuration, read where the head left its base
          and at the pinned head (`fixers.change_between`,
          [project-management:DEC-056-drift-fixers] point 2). A grant list that
          cannot be read stops the run, since what it cannot read it cannot
          show. At a later head an earlier head's authorisation covers, the
          change must be the one at the head authorised: any other, or one that
          cannot be read there, stops a `--yes` run at `ready:`, as an answer the
          change check did not ask for does. So does a document or a target left
          out of date that the head authorised did not leave, or an answer the
          run cannot read at that head.
  merge check
          The change check on the merge as it would land: the PR's base
          fetched, the merge of the pinned head with its tip built as a commit
          on no branch, and `pkit friction check --json` run against the tip,
          the head named as the change's own head (`--own-head`), as the checks
          on a PR run it (`friction_answers.merged`, DEC-055 point 6). It reads
          the merge from git objects first, and only the backbone's refusal to
          run an anchor's resolver away from it takes a temporary checkout: a
          head from elsewhere nobody named asks or stops there, as above
          (DEC-067 point 3). Where the head holds
          the tip its own check read, that check serves and nothing runs
          again. A check that fails there stops the run, with nothing merged,
          naming each document it fails on, a line each; in warning mode its
          findings are printed and stop nothing. A merge that conflicts stops
          the run with the merge to make, and a check that cannot be read
          stops it too. Its line begins `merge check:` (`MERGE_CHECK`).
  merge   `done-work` with the pinned head. Without `--yes`, off a terminal,
          land-work merges nothing: it runs `done-work`'s gates as a dry run
          and stops with a `ready:` line naming the head and the command that
          merges it; the lines above it tell what changed in each updated
          document and which are left out of date, as information. At a
          terminal, `done-work`'s prompt asks, naming the head, after the
          same lines. A change
          with answers merges under the same authorisation as any other; a
          run the findings to judge hold stops at `ready:`. So does a `--yes`
          run on a document the change check marks `updated` with no sentence,
          or a sentence on a document it does not. So does a run at a later
          head an earlier head's authorisation covers, where it finds a
          reviewer's finding to judge, an answer the change check did not ask
          for, or a document left out of date, a change to the fixers' grant
          list or a list of the accepted records the change alters, other than
          the one at the head authorised; one that merges says which head and
          why it was covered. Its gates,
          refusals and queue handling are done-work's own; land-work decides
          on how its run ended (`done_work.run`), never on its exit code. A
          merge the host refused, on a PR it reads as behind a base it merges
          only a branch up to date with, stops the run with the merge of the
          base to make, unless the base merges through a queue.

There is no flag that skips the checks or the review: the bypasses are
`done-work`'s, with their audit. Run again, land-work resumes: green checks on
the same head are not waited for, fresh verdicts are not re-run, and a PR that
merged is completed through `done-work`.

Exit codes: the table in the capability README, "Landing a pull request in
one command", is the one list of them; `EXIT_*` below name them.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    accepted_records,
    answers_told,
    bootstrap_gate,
    drift_queue,
    fixers,
    friction_answers,
    head_programs,
    issue_branch,
    merge_queue,
    pr_head,
    pr_merge,
    provenance,
    session_guard,
)
from _lib.agent_verdicts import (
    APPROVED,
    CHANGES_REQUESTED,
    PATH_LOCAL,
    PATH_REMOTE,
    TAG_ADVISORY,
    TAG_BLOCK,
    TAG_PERSON,
    Finding,
    Verdict,
    all_verdicts,
    gate_candidates,
    gate_membership,
    marked_candidates,
    pr_author,
    tagged,
)
from _lib.audit import short_sha
from _lib.ci_checks import (
    FAILED,
    NO_RUN,
    PASSED,
    RUNNING,
    CiGateResult,
    evaluate_ci_gate,
    named_checks_passed,
    unreported_checks,
)
from _lib.escaped_output import escaping
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.pr_review import REVIEW_VIEW_FIELDS, remote_baseline
from _lib.review_mode import resolve_mode
from _lib.verdict_freshness import Freshness, head_sha


def _load_verb(script: str, module_name: str) -> ModuleType:
    """A sibling verb's script, loaded as a module (its name has a hyphen), so
    land-work calls that verb's own functions rather than copies of them."""
    spec = importlib.util.spec_from_file_location(module_name, _HERE / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


done_work = _load_verb("done-work.py", "pm_land_work_done_work")
review_pr = _load_verb("review-pr.py", "pm_land_work_review_pr")

# The exit codes, one per action the caller takes; the README's table says
# what each covers and what to do.
#: Merged — or a PR that had merged completed — and the issue done.
EXIT_MERGED = 0
#: Something on the PR must change: hand it back.
EXIT_NEEDS_CHANGE = 1
#: Nothing was changed: a usage error, a refused invocation, or a reading.
EXIT_UNREADABLE = 2
#: The PR's head is not the one pinned, or not the one authorised.
EXIT_HEAD_MOVED = 3
#: Accepted, not yet seen merged: queued or unconfirmed (done-work's 4).
EXIT_ACCEPTED = done_work.EXIT_ACCEPTED
#: The wait for the checks ran out.
EXIT_CI_PENDING = 5
#: A reviewer could not be run, so the review is not complete.
EXIT_REVIEW_INCOMPLETE = 6
#: A step failed where running again completes it.
EXIT_RETRY = 7
#: Ready to merge, and not authorised to: nothing was merged.
EXIT_READY = 8
#: A head from elsewhere needs a person at a terminal: nothing was merged, and a second
#: run off a terminal changes nothing (DEC-067 point 3).
EXIT_PERSON = 9

#: How long the checks are waited for when `--wait-minutes` does not say.
DEFAULT_WAIT_MINUTES = 30.0
#: How often the checks are read while they are waited for.
POLL_SECONDS = 20.0

#: How each line of the answers step begins: the documents the answers are on, in
#: plain words.
STEP = friction_answers.NAME
#: The list of answers an earlier run wrote into the description, as the step names
#: it when it removes it (DEC-065 point 1).
_EARLIER_LIST = "the list of answers an earlier run left"
#: What the answers step and the `ready:` line call a change to the fixers' grant
#: list (DEC-056 point 2).
GRANTS = "a change to which fixers may start"
#: How the line of the step that prints the `[person]` findings begins.
FINDINGS = "findings to judge"
#: How the line of the step that checks the merge as it would land begins (DEC-055
#: point 6).
MERGE_CHECK = "merge check"
#: What that step reads of the PR: the verdicts and what the freshness rule
#: reads, and the author the gate excludes.
_FINDINGS_VIEW = (*REVIEW_VIEW_FIELDS, "author")

# The wait's sleep and clock, looked up when a wait runs.
_sleep: Callable[[float], None] = time.sleep
_monotonic: Callable[[], float] = time.monotonic


def _interactive() -> bool:
    """Whether a person can answer done-work's prompt (`move-issue`'s test)."""
    return sys.stdin.isatty()


#: How many lines of a CHANGES_REQUESTED with no tagged finding are printed.
_UNTAGGED_LINES = 3


class _Stop(Exception):
    """A step that cannot go on: the run's exit code and its last line."""

    def __init__(self, code: int, line: str) -> None:
        super().__init__(line)
        self.code = code
        self.line = line


@dataclass(frozen=True)
class _Head:
    """The PR head land-work pins, and where it was found."""

    issue: int
    pr_number: int
    branch: str
    oid: str
    #: The PR's base branch, as a line says it.
    base: str
    #: The remote the branch is pushed to and fetched from.
    remote: str
    #: The PR's base branch as GitHub names it; empty when it named none.
    base_branch: str = ""
    #: The PR comes from a fork, so its head is fetched by the ref its base
    #: repository keeps for it.
    cross_repository: bool = False
    #: The earlier head `--expect-head` authorised, where its authorisation covers this
    #: one: every change since lies inside answer files the change adds, a clean merge
    #: of the base counting as none (DEC-055 point 3). Empty where the head
    #: is the one named.
    authorised: str = ""
    #: The host's word on where the head lies (`isCrossRepository`), as the reading
    #: that named the head gave it: only False places it in the base's repository.
    placed: object = None
    #: The repository the head comes from, as the host names it.
    repository: str = ""
    #: What the test found of the head, and whether a person named it (DEC-067).
    standing: head_programs.Standing = head_programs.UNTAKEN

    @property
    def source(self) -> pr_head.Source:
        """Where the head is fetched from, where this clone lacks it: for a PR from a
        fork, the base's remote, which keeps a ref for it."""
        return pr_head.pull_request_source(
            self.branch,
            self.pr_number,
            cross_repository=self.cross_repository,
            base=self.base_branch,
            remote=self.remote,
        )

    @property
    def base_remote(self) -> str:
        """The remote a merge of the base is made from, as a line names it: the base's
        own for a PR from a fork, whose branch's remote is the fork's; else the
        branch's."""
        if self.cross_repository and self.base_branch:
            return pr_head.base_remote(self.base_branch)
        return self.remote

    @property
    def covered(self) -> str:
        """Why the authorisation for an earlier head covers this one, as a line says
        it, or "" where the head is the one authorised."""
        if not self.authorised:
            return ""
        earlier = short_sha(self.authorised)
        return (
            f"the authorisation for {earlier} covers it, since every change after {earlier} "
            f"lies inside answer files the change adds, a clean merge of "
            f"{self.base} counting as none"
        )


@dataclass(frozen=True)
class _Checks:
    """One reading of the PR, with the checks on the head it was read at."""

    head: str = ""
    state: str = ""
    rollup: list[dict[str, Any]] = field(default_factory=list)
    gate: CiGateResult | None = None
    #: GitHub's `mergeable`: MERGEABLE, CONFLICTING or UNKNOWN.
    mergeable: str = ""
    #: GitHub's `mergeStateStatus`: BEHIND where the head is out of date with a
    #: base the host merges only a branch up to date with.
    merge_state: str = ""
    #: Why the PR could not be read; empty when it was.
    problem: str = ""

    @property
    def conflicting(self) -> bool:
        return self.mergeable == "CONFLICTING"

    @property
    def behind(self) -> bool:
        return self.merge_state == "BEHIND"


@dataclass(frozen=True)
class _ReviewEnd:
    """How the review step ended, when it did not stop the run."""

    #: Every required reviewer approved — False only for a dry run that would
    #: run a reviewer.
    clear: bool
    #: What the approval is, as the `ready:` line says it.
    approval: str


@dataclass(frozen=True)
class _AnswersEnd:
    """How the answers step ended, when it did not stop the run: what the person
    who authorises the merge is told, as information, not a gate (DEC-065
    point 4). A change with answers merges under the same authorisation as any
    other."""

    #: How many documents the change updated, as `friction_answers.counted_told`
    #: counts them.
    updated: int = 0
    #: How many documents it leaves out of date: a deferral it wrote or a
    #: revalidation kept.
    left: int = 0
    #: How many targets of a link it leaves out of date: a `deferred` revisit
    #: entry (COR-050 point 16).
    targets: int = 0
    #: How many of the project's friction settings the change alters.
    settings: int = 0
    #: What the `ready:` line tells, a line each (`answers_told.at_head`).
    told: tuple[str, ...] = ()
    #: How many answers the change check did not ask for, reasons for having no
    #: anchors among them: each needed the person's acceptance, so a later head
    #: holding one is not covered by an earlier head's authorisation (DEC-055
    #: point 3). Their lines are in `told`.
    unasked: int = 0
    #: Each grant and refusal the change adds to the fixers' grant list or removes
    #: from it (DEC-056 point 2); its lines are in `told` too.
    grants: tuple[fixers.GrantChange, ...] = ()
    #: Why an earlier head's authorisation does not cover the grant list's change at
    #: the pinned head, as the `ready:` line says it, or "": the change differs from
    #: the one at the head authorised, or that one could not be read.
    grants_moved: str = ""
    #: How many revalidations on the base's tip the merge would leave answered apart
    #: from the change's own (`friction_answers.apart`); their lines are in `told` too.
    apart: int = 0
    #: The change check's document at the pinned head, which serves the check of the
    #: merge where the head holds the base's tip it read (`friction_answers.merged`).
    checked: Mapping[str, Any] | None = None
    #: Each document the description gives a sentence for that the change check does
    #: not mark `updated`: no reviewer checks it, so a run authorised up front holds
    #: until the author removes it (DEC-055 point 3).
    unlisted: tuple[str, ...] = ()
    #: Each document the change check marks `updated` that the description gives no
    #: sentence for: a run authorised up front holds until the author writes it
    #: (DEC-065 point 4).
    unsaid: tuple[str, ...] = ()
    #: Why an earlier head's authorisation does not cover what the pinned head leaves
    #: out of date, as the `ready:` line says it, or "": it left less, or what it
    #: left could not be read (`_left_moved`).
    left_moved: str = ""

    def phrase(self) -> str:
        """What the `ready:` line says of the lines above it —
        `, what changed in 1 updated document, 1 document left out of date and
        1 target of a link left out of date above, for information` — or ""
        when there is nothing to tell."""
        parts: list[str] = []
        if self.updated:
            noun = "document" if self.updated == 1 else "documents"
            parts.append(f"what changed in {self.updated} updated {noun}")
        if self.left:
            noun = "document" if self.left == 1 else "documents"
            parts.append(f"{self.left} {noun} left out of date")
        if self.targets:
            noun = "target of a link" if self.targets == 1 else "targets of a link"
            parts.append(f"{self.targets} {noun} left out of date")
        if self.unasked:
            noun = "answer" if self.unasked == 1 else "answers"
            parts.append(f"{self.unasked} {noun} this change was not asked for")
        if self.settings:
            parts.append(friction_answers.CHECKED)
        if self.grants:
            parts.append(GRANTS)
        if self.apart:
            noun = "revalidation" if self.apart == 1 else "revalidations"
            parts.append(f"{self.apart} {noun} answered apart once merged")
        if not parts:
            return ""
        said = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
        return f", {said} above, for information"


@dataclass(frozen=True)
class _FindingsEnd:
    """How the step that prints the `[person]` findings ended, when it did not
    stop the run."""

    #: How many `[person]` findings it printed.
    count: int = 0
    #: Why this run's `--yes` does not cover them, or None when it does — or
    #: when there is no `--yes`, or nothing for it to cover (DEC-055 point 3).
    held: str | None = None
    #: How many accepted decision records the change alters it printed (#2161).
    records: int = 0
    #: Why an earlier head's authorisation does not cover those records at the pinned
    #: head, as the `ready:` line says it, or "": the list differs from the one at the
    #: head authorised, or that one could not be read.
    records_moved: str = ""

    def phrase(self) -> str:
        """What the `ready:` line asks the person to judge — the `[person]` findings
        and the accepted records the change alters — with why a `--yes` does not
        cover it: `, 1 finding to judge above (…)`, or ""."""
        shown = self.count + self.records
        if not shown:
            return ""
        noun = "finding" if shown == 1 else "findings"
        held = f" ({self.held})" if self.held else ""
        return f", {shown} {noun} to judge above{held}"


# How the ci step ended, when it did not stop the run.
_CI_PASSED = "passed"
_CI_FIRST_PASSED = "first-passed"
_CI_WOULD_WAIT = "would-wait"
_CI_PR_MERGED = "merged"


@escaping
def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.yes and not args.expect_head:
        # An authorisation to merge is for a named head (DEC-055 point 3), and a
        # `--yes` that names none would merge whatever head the run finds, one the
        # person may not have been shown (#1760). It is refused before anything
        # is read, waited for or reviewed. No command with a head is offered: the
        # head to authorise is the one the `ready:` line names, once the person was
        # shown what that line prints.
        parser.error(
            "--yes needs --expect-head <sha>: an authorisation to merge is for a named "
            f"head. Nothing was done. Run `land-work {args.issue_number}` without --yes: "
            "its ready: line names the head and the command that merges it"
        )
    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return EXIT_UNREADABLE
    # The composed verbs gate each of these again; land-work gates them first
    # so a run they would refuse stops before it waits for any check.
    if not bootstrap_gate.enforce("land-work", capability_root=capability_root):
        return EXIT_UNREADABLE
    config = load_adopter_config(capability_root)
    members = done_work._read_members(capability_root, YAML(typ="safe"))
    membership = check_membership(members, resolve_invoker_identity(config=config))
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return EXIT_UNREADABLE
    guard = session_guard.enforce(override=args.allow_foreign_repo)
    if not guard:
        return EXIT_UNREADABLE
    # A confirmation given here — the flag, or a yes at the terminal — is
    # passed on to the verbs it composes, so their guards pass by it and the
    # operator is asked once; and only then (`_passed_through`). A flag the
    # operator gave stays given, whatever this comparison found.
    if session_guard.confirmed(guard):
        args.allow_foreign_repo = True
    try:
        return _land(args, config, capability_root)
    except _Stop as stop:
        _end(stop.line)
        return stop.code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Land an issue's pull request: wait for the checks on its head, have the "
            "reviewers whose verdicts are not fresh review it, and merge it through "
            "done-work. One line per step; a re-run resumes where a run stopped."
        ),
    )
    parser.add_argument("issue_number", type=int)
    wait = parser.add_mutually_exclusive_group()
    wait.add_argument(
        "--wait-minutes",
        type=pr_merge.minutes,
        default=None,
        metavar="MINUTES",
        help=(
            f"How long to wait for the checks on the PR's head (default "
            f"{DEFAULT_WAIT_MINUTES:g}), as long again for those still running once a "
            "review started beside them has ended, and, where the base merges through a "
            "queue, for the queue to merge it (passed to done-work)."
        ),
    )
    wait.add_argument(
        "--no-wait",
        action="store_true",
        help=(
            "Read the checks once, and return once the PR is queued where the base "
            "merges through a queue (exit 4). Run land-work again to go on."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what each step would do; review and merge nothing.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "The authorisation to merge the head --expect-head names, and refused "
            "without it (exit 2), before anything runs. Without --yes, off a terminal, "
            "land-work checks, reviews and runs done-work's gates, then stops with a "
            "`ready:` line (exit 8) naming the head and the command that merges it. At "
            "a terminal, done-work asks, naming the head. A change with friction answers "
            "merges under it as any other does. A finding to judge stops the run at "
            "`ready:` unless the run found its verdict when it started, standing for "
            "the head."
        ),
    )
    parser.add_argument(
        "--expect-head",
        type=_commit,
        default=None,
        metavar="SHA",
        help=(
            "The PR head the merge is authorised for (7 to 40 hex digits), which --yes "
            "needs: the run stops (exit 3) when the PR's head is another, unless every "
            "change since lies inside answer files the change adds, a clean "
            "merge of the base counting as none. The `ready:` line names it."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    return parser


def _commit(value: str) -> str:
    """`--expect-head`: a commit id or a prefix of one, 7 to 40 hex digits."""
    commit = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise argparse.ArgumentTypeError(f"{value!r} is not a commit id (7 to 40 hex digits)")
    return commit


def _land(args: argparse.Namespace, config: dict[str, Any], capability_root: Path) -> int:
    # The issue's branch, read once for the run and handed to the verbs it
    # composes (#1608).
    reading = issue_branch.read(args.issue_number, config)
    head = _pin_head(args, config, reading)
    if head is None:
        return _merge(args, None, config, reading)
    # Before any wait, review or temporary checkout: a head from elsewhere that needs
    # a person stops here, with nothing spent on it (DEC-067 point 3).
    head = _take_test(args, head, config, capability_root)
    # What a run authorised up front found when it started: the hold on the
    # `[person]` findings is what it found then (DEC-055 point 3).
    found = _found_at_start(head, config) if args.yes and not args.dry_run else None
    wait_for_checks = functools.partial(
        _wait_for_checks,
        head,
        wait_seconds=_wait_seconds(args),
        dry_run=args.dry_run,
        config=config,
        # Whether a PR read as behind stops here, read once a run: the queue is the base's.
        behind_stops=functools.cache(lambda: _behind_stops(head, config)),
    )
    ci = wait_for_checks(first=_checks_that_start_review(args, config))
    if ci == _CI_PR_MERGED:
        return _merge(args, None, config, reading)
    beside_checks = ci == _CI_FIRST_PASSED
    try:
        review = _review(args, head, config, reading, beside_checks=beside_checks)
    except _Stop:
        # However this step stops, the run shows the verdicts it leaves, which a later
        # `--yes` would find at its start (DEC-055 point 3).
        _findings_at_review_stop(head, config, capability_root)
        raise
    if beside_checks:
        # Before the wait: however it ends, this run shows the verdicts it posted, which
        # a later `--yes` would find at its start (DEC-055 point 3). The step runs again
        # below, for a verdict posted during the wait.
        _findings(args, head, config, capability_root, found)
        # The rest of the checks, which ran beside the review (DEC-063 point 8).
        ci = wait_for_checks(reviewed=True)
        if ci == _CI_PR_MERGED:
            return _merge(args, None, config, reading)
    # Before the answers: this step stops on what it cannot read, and a stop
    # here has written nothing.
    to_judge = _findings(args, head, config, capability_root, found)
    answers = _answers(args, head, config, capability_root)
    if args.dry_run and (ci != _CI_PASSED or not review.clear):
        _end(
            f"merge: (dry-run) would hand PR #{head.pr_number} at {short_sha(head.oid)} to "
            "done-work once the checks pass and the review approves"
        )
        return EXIT_MERGED
    # Last before the ready stop, the prompt or the merge: the merge as it would land,
    # with the base as it stands now (DEC-055 point 6).
    _merge_check(args, head, answers, config, capability_root)
    if args.dry_run:
        return _merge(args, head, config, reading, answers)
    holds = (
        _uncovered(head, to_judge, answers)
        + _unlisted_hold(head, answers)
        + _unsaid_hold(head, answers)
    )
    if args.yes and (to_judge.held is not None or holds):
        return _ready(args, head, review, config, answers, to_judge, reading, holds)
    if not args.yes and not _interactive():
        return _ready(args, head, review, config, answers, to_judge, reading)
    return _merge(args, head, config, reading, answers)


def _unlisted_hold(head: _Head, answers: _AnswersEnd) -> str:
    """Why a run authorised up front holds on the author's sentences, as the `ready:`
    line says it, or "": the description gives a sentence on a document the change
    check does not mark `updated`, which no reviewer checks. The person authorised
    before the warning was shown, so the run stops ready until the author removes
    it, as a `[person]` finding holds it (DEC-055 point 3)."""
    if not answers.unlisted:
        return ""
    names = ", ".join(answers.unlisted)
    one = len(answers.unlisted) == 1
    return (
        f"; held for the sentence{'' if one else 's'} on {names}, which no reviewer "
        f"checks (above): remove {'it' if one else 'them'} with `edit-pr {head.pr_number} "
        "--body-file <file>`, then run the command below again"
    )


def _unsaid_hold(head: _Head, answers: _AnswersEnd) -> str:
    """Why a run authorised up front holds on a missing sentence, as the `ready:` line
    says it, or "": the change check marks a document `updated` that the description
    gives no sentence for. The move to review refused that, but an edit after the
    verdict stales no verdict, and nothing else stops it here (DEC-065 point 4)."""
    if not answers.unsaid:
        return ""
    names = ", ".join(answers.unsaid)
    one = len(answers.unsaid) == 1
    return (
        f"; held for {names}, updated with no sentence on what changed (above): write "
        f"{'it' if one else 'them'} with `edit-pr {head.pr_number} --body-file <file>`, then "
        "run the command below again"
    )


def _uncovered(head: _Head, to_judge: _FindingsEnd, answers: _AnswersEnd) -> str:
    """Why the authorisation for an earlier head does not cover the pinned head after
    all, as the `ready:` line says it, or "": the later head holds what needs the
    person — a reviewer's `[person]` finding, an answer the change check did not ask
    for (DEC-055 point 3), what it leaves out of date beyond the head authorised
    (`_left_moved`), a change to the fixers' grant list other than the one at the head
    authorised (DEC-056 point 2), or a list of the accepted records the change alters
    other than the one at the head authorised (`_records_moved`)."""
    if not head.authorised:
        return ""
    needs: list[str] = []
    if to_judge.count:
        needs.append(f"{to_judge.count} finding{'' if to_judge.count == 1 else 's'} to judge")
    if to_judge.records_moved:
        needs.append(to_judge.records_moved)
    if answers.unasked:
        one = answers.unasked == 1
        needs.append(f"{answers.unasked} answer{'' if one else 's'} this change was not asked for")
    if answers.left_moved:
        needs.append(answers.left_moved)
    if answers.grants_moved:
        needs.append(answers.grants_moved)
    if not needs:
        return ""
    return (
        f"; the authorisation for {short_sha(head.authorised)} covers {short_sha(head.oid)} "
        f"only where nothing there needs a person, and it holds {' and '.join(needs)}"
    )


# ---- head ----------------------------------------------------------------


def _pin_head(
    args: argparse.Namespace, config: dict[str, Any], reading: issue_branch.Reading
) -> _Head | None:
    """The PR head to land, pinned; None when gh answered that the branch has
    no open PR (or there is no local branch to have one). Of several local
    branches, `reading` names the one with the issue's open PR (#1608)."""
    issue = args.issue_number
    if reading.refusal and not reading.none_open:
        for line in reading.refusal.splitlines():
            print(f"  {line}")
        raise _Stop(
            EXIT_UNREADABLE,
            f"head: stopped — which local branch is #{issue}'s cannot be told (above). "
            "Nothing was done",
        )
    branch = reading.branch
    if branch is None and reading.none_open:
        _say(
            f"head: no open PR on any of {', '.join(reading.matching)} — done-work "
            "completes a PR that has merged already"
        )
        return None
    if branch is None:
        _say(
            f"head: no local branch */{issue}-* — done-work completes a PR that has merged already"
        )
        return None
    lookup = done_work._lookup_prs(branch, "open", done_work._OPEN_PR_FIELDS, config)
    if lookup.problem:
        raise _Stop(
            EXIT_UNREADABLE,
            f"head: whether {branch} has an open PR could not be read: {lookup.problem}. "
            f"Nothing was done; run `land-work {issue}` again once gh answers",
        )
    try:
        pr = head_programs.one_open(lookup.prs, branch)
    except head_programs.TwoOpen as exc:
        raise _Stop(EXIT_UNREADABLE, f"head: stopped — {exc}") from exc
    if pr is None:
        _say(f"head: no open PR for {branch} — done-work completes a PR that has merged already")
        return None
    number = int(pr["number"])
    oid = str(pr.get("headRefOid") or "")
    if pr.get("isDraft"):
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"head: refused — PR #{number} is a draft; mark it ready with `review-work {issue}`",
        )
    if not oid:
        raise _Stop(EXIT_UNREADABLE, f"head: PR #{number}'s head could not be read")
    cross = bool(pr.get("isCrossRepository"))
    head = _Head(
        issue,
        number,
        branch,
        oid,
        base=str(pr.get("baseRefName") or "") or "the base branch",
        remote=pr_head.branch_remote(branch),
        base_branch=str(pr.get("baseRefName") or ""),
        cross_repository=cross,
        placed=pr.get("isCrossRepository"),
        repository=head_programs.repository(pr),
    )
    if args.expect_head and not oid.startswith(args.expect_head):
        head = _covered(head, args.expect_head)
    notes = _local_notes(head)
    if head.covered:
        notes.insert(0, head.covered)
    _say(f"head: {short_sha(oid)} (PR #{number}, {branch})" + "".join(f"; {n}" for n in notes))
    return head


def _take_test(
    args: argparse.Namespace, head: _Head, config: dict[str, Any], capability_root: Path
) -> _Head:
    """The pinned head with what the test of DEC-067 found of it. A head that passes
    runs as it always has, and nothing is said of it. For a head from elsewhere the
    change check runs now, from git objects, before the run waits for checks or starts
    a reviewer: where it needs a resolver, a person names the head or the run stops."""
    standing = head_programs.take_test(
        head.oid,
        head.placed,
        issue=head.issue,
        base=head.base_branch,
        source=head.source,
        capability_root=capability_root,
        config=config,
    )
    head = replace(head, standing=standing)
    if standing.passes:
        return head
    _say(f"head: {short_sha(head.oid)} is from elsewhere — {standing.elsewhere}")
    if not head.base_branch:
        # The answers step stops on it, with nothing started.
        return head
    found = friction_answers.checked(
        head.oid, head.base_branch, source=head.source, from_checkout=False
    )
    if found.needs_checkout:
        return _named_or_stopped(args, head, config, capability_root, step="head")
    return head


def _named_or_stopped(
    args: argparse.Namespace,
    head: _Head,
    config: dict[str, Any],
    capability_root: Path,
    *,
    step: str,
) -> _Head:
    """A head from elsewhere whose check needs a resolver, named by the person at this
    terminal, or the stop: no flag gives that word, so a dry run and a run authorised
    up front stop here, even at a terminal (DEC-067 points 3 and 4)."""
    if _interactive() and not args.yes and not args.dry_run:
        named = head_programs.ask(
            head.standing,
            command="land-work",
            number=head.pr_number,
            source_repository=head.repository,
            capability_root=capability_root,
            config=config,
        )
        if named.may_start:
            return replace(head, standing=named)
    raise _person_stop(head, step)


def _person_stop(head: _Head, step: str) -> _Stop:
    """The stop on a head from elsewhere whose check needs a resolver. Its line says
    why, that a second run changes nothing, how a person goes on, and what a merge
    through the other merge commands would leave out (DEC-067 points 3 and 9)."""
    return _Stop(
        EXIT_PERSON,
        f"{step}: stopped — PR #{head.pr_number}'s head {short_sha(head.oid)} is from "
        f"elsewhere ({head.standing.elsewhere}), and its change check needs a resolver, a "
        "program this run may not start. Nothing was merged. A second run changes nothing: "
        f"a person at a terminal can run `land-work {head.issue}` and name the head. A merge "
        "through `done-work` or `merge-pr` runs no change check and tells no answer",
    )


def _covered(head: _Head, authorised: str) -> _Head:
    """The pinned head, where the authorisation for the earlier head `authorised` covers
    it: every change from that head to this one lies inside answer files the change
    adds, a clean merge of the base counting as none, as the backbone answers it
    (DEC-055 point 3). Any other change, and an answer that cannot be read, stops the run
    before anything is checked, as a head nobody authorised does."""
    issue, number, sha = head.issue, head.pr_number, short_sha(head.oid)
    moved = (
        f"head: stopped — PR #{number}'s head is {sha}, not {authorised[:7]}, the head the "
        "merge was authorised for"
    )
    again = f"Nothing was done; `land-work {issue}` checks and reviews the new one"
    if not head.base_branch:
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"{moved}, and its base branch could not be read, so whether that authorisation "
            f"covers it cannot be told. {again}",
        )
    missing = pr_head.fetch_head(head.oid, head.source)
    found = (
        friction_answers.covers(authorised, head.oid, head.base_branch)
        if missing is None
        else friction_answers.Coverage(problem=missing)
    )
    if found.problem is None and (found.head != head.oid or not found.since.startswith(authorised)):
        found = replace(
            found,
            problem=f"the backbone answered for {found.since[:7]} to {found.head[:7]}, not "
            f"{authorised[:7]} to {sha}",
        )
    if found.problem is not None:
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"{moved}, and whether that authorisation covers it could not be told: "
            f"{found.problem}. {again}",
        )
    if not found.covered:
        listed = "; ".join(found.outside[:3]) + (
            f"; and {len(found.outside) - 3} more" if len(found.outside) > 3 else ""
        )
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"{moved}: an authorisation covers a later head only where every change since "
            f"lies inside answer files the change adds, a clean merge of "
            f"{head.base} counting as none, and these changes do not: {listed}. {again}",
        )
    return replace(head, authorised=found.since)


def _local_notes(head: _Head) -> list[str]:
    """What the local checkout says about the pinned head; refuses a local
    branch holding commits the head lacks. A head this clone lacks is fetched from
    its source first: for a PR from a fork, the ref its base repository keeps."""
    branch, oid, remote = head.branch, head.oid, head.remote
    tip = _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").stdout.strip()
    notes: list[str] = []
    if tip and tip != oid:
        # The source is read only for a head this clone lacks: for a PR from a fork,
        # it asks the backbone for the base's remote.
        fetched = None if pr_head.has_commit(oid) else pr_head.fetch(oid, head.source)
        if fetched is not None and not fetched.held:
            named = fetched.ref.removeprefix("refs/heads/")
            raise _Stop(
                EXIT_UNREADABLE,
                f"head: cannot tell whether local {branch} (at {short_sha(tip)}) holds commits "
                f"PR #{head.pr_number}'s head {short_sha(oid)} lacks: this clone does not have "
                f"that head. Fetch it (`git fetch {fetched.remote} {named}`) and run "
                f"`land-work {head.issue}` again",
            )
        ahead = _count_commits(f"{oid}..{tip}")
        behind = _count_commits(f"{tip}..{oid}")
        if ahead is None or behind is None:
            raise _Stop(
                EXIT_UNREADABLE,
                f"head: cannot compare local {branch} with PR #{head.pr_number}'s head "
                f"{short_sha(oid)}",
            )
        if ahead and behind:
            # No command is offered: when the PR's branch was force-pushed, a
            # pull would put back the commits the push replaced.
            raise _Stop(
                EXIT_NEEDS_CHANGE,
                f"head: refused — local {branch} and PR #{head.pr_number}'s head "
                f"{short_sha(oid)} have diverged ({_commits(ahead)} only here, "
                f"{_commits(behind)} only on the PR). Nothing was done",
            )
        if ahead:
            raise _Stop(
                EXIT_NEEDS_CHANGE,
                f"head: refused — local {branch} has {_commits(ahead)} PR "
                f"#{head.pr_number}'s head {short_sha(oid)} lacks. Push first: "
                f"`git push {remote} {branch}`",
            )
        notes.append(f"local {branch} is {_commits(behind)} behind it")
    current = _git("symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if current != branch:
        notes.append(f"this checkout is on {current or 'a detached HEAD'}, not {branch}")
    return notes


def _git(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], capture_output=True, text=True, check=False)


def _count_commits(revisions: str) -> int | None:
    proc = _git("rev-list", "--count", revisions)
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return None


def _commits(count: int) -> str:
    return f"{count} commit" + ("" if count == 1 else "s")


# ---- ci --------------------------------------------------------------------


def _wait_seconds(args: argparse.Namespace) -> float:
    if args.no_wait:
        return 0.0
    minutes = DEFAULT_WAIT_MINUTES if args.wait_minutes is None else args.wait_minutes
    return minutes * 60


def _checks_that_start_review(args: argparse.Namespace, config: dict[str, Any]) -> tuple[str, ...]:
    """The checks whose pass starts the review, which the project names
    (`review.agents.start_after_checks`); none where it names none, or where the
    value is not a list of names, so the review waits for every check. `pkit data
    validate` refuses such a value.

    None for a run authorised up front: a stop in the wait for the rest would fall
    between a verdict it posted and the findings' hold, leaving the verdict found at
    the next run's start (DEC-055 point 3). None for `--no-wait`, which only reads."""
    if args.yes or args.no_wait:
        return ()
    review = config.get("review") if isinstance(config, dict) else None
    agents = review.get("agents") if isinstance(review, dict) else None
    named = agents.get("start_after_checks") if isinstance(agents, dict) else None
    if not isinstance(named, list) or not all(isinstance(name, str) for name in named):
        return ()
    return tuple(named)


def _wait_for_checks(
    head: _Head,
    *,
    wait_seconds: float,
    dry_run: bool,
    config: dict[str, Any],
    behind_stops: Callable[[], bool],
    first: tuple[str, ...] = (),
    reviewed: bool = False,
) -> str:
    """Wait for the checks on the pinned head, as long as `wait_seconds`.

    Returns how it ended when the run goes on — the checks passed, each of `first`
    passed and none failed, a dry run would wait for them, or the PR merged
    meanwhile — and stops the run otherwise. The checks are read with the head they
    belong to, so a run on another head never counts: a head that moved stops the
    run. `reviewed` says the review has ended, as a stop then says.

    Every check reported can pass before one of `first` has started, so that reading
    is read once more. A name still unreported then is warned of, and the run reads
    the checks again once the review has ended.
    """
    issue, number = head.issue, head.pr_number
    started = _monotonic()
    said = ""
    read_again = False
    while True:
        checks = _read_pr(number, config)
        if checks.problem:
            progress = f"the checks could not be read: {checks.problem}"
            if dry_run or _monotonic() - started >= wait_seconds:
                raise _Stop(
                    EXIT_UNREADABLE,
                    f"ci: PR #{number}'s checks could not be read: {checks.problem}. "
                    f"Run `land-work {issue}` again",
                )
        elif checks.state == "MERGED":
            _say(f"ci: PR #{number} has merged meanwhile")
            return _CI_PR_MERGED
        elif checks.state != "OPEN":
            raise _Stop(
                EXIT_NEEDS_CHANGE,
                f"ci: PR #{number} is {checks.state.lower() or 'not open'}; nothing to land",
            )
        elif checks.head != head.oid:
            raise _Stop(
                EXIT_HEAD_MOVED,
                f"ci: stopped — PR #{number}'s head moved from {short_sha(head.oid)} to "
                f"{short_sha(checks.head)} while its checks were awaited. Nothing was "
                f"{'merged' if reviewed else 'reviewed or merged'}; `land-work {issue}` "
                "checks and reviews the new head",
            )
        elif checks.conflicting:
            raise _Stop(EXIT_NEEDS_CHANGE, _conflict_line("ci", head))
        elif checks.behind and behind_stops():
            raise _Stop(EXIT_NEEDS_CHANGE, _behind_line("ci", head))
        else:
            gate = checks.gate
            assert gate is not None
            missing = unreported_checks(checks.rollup, first)
            if gate.state == PASSED and (not missing or read_again or dry_run):
                return _all_passed(head, checks.rollup, missing)
            if gate.state == PASSED:
                read_again = True
                progress = f"{', '.join(missing)} not reported for {short_sha(head.oid)} yet"
            elif gate.state == FAILED:
                raise _Stop(
                    EXIT_NEEDS_CHANGE,
                    f"ci: failed on {short_sha(head.oid)} — {_failed_checks(gate)}. "
                    f"{'Merge' if reviewed else 'Review and merge'} not started",
                )
            elif gate.state == RUNNING and named_checks_passed(checks.rollup, first):
                return _first_passed(head, first, gate, wait_seconds, dry_run=dry_run)
            else:
                progress = (
                    f"no check has been reported for {short_sha(head.oid)} yet"
                    if gate.state == NO_RUN
                    else f"running on {short_sha(head.oid)}: {', '.join(gate.running)}"
                )
                if dry_run:
                    _say(f"ci: (dry-run) {progress} — would wait up to {_duration(wait_seconds)}")
                    return _CI_WOULD_WAIT
                waited = _monotonic() - started
                if waited >= wait_seconds:
                    raise _Stop(EXIT_CI_PENDING, _ran_out(head, gate, waited, wait_seconds))
        if progress != said:
            print(f"  ci: {progress}", flush=True)
            said = progress
        _sleep(max(0.0, min(POLL_SECONDS, wait_seconds - (_monotonic() - started))))


def _all_passed(head: _Head, rollup: list[dict[str, Any]], missing: tuple[str, ...]) -> str:
    """Say that every check reported passed on the pinned head, and how the step ends.
    Where `missing` holds a name no check bears, the configuration may be wrong or the
    check may start late, so a warning says so and the checks are read again after the
    review."""
    if missing:
        print(
            f"  warn: no check on {short_sha(head.oid)} is named {', '.join(missing)}, which "
            "review.agents.start_after_checks names, so the review waited for every check "
            "reported",
            flush=True,
        )
    _say(f"ci: passed on {short_sha(head.oid)}{_passed_detail(rollup)}")
    return _CI_FIRST_PASSED if missing else _CI_PASSED


def _first_passed(
    head: _Head,
    first: tuple[str, ...],
    gate: CiGateResult,
    wait_seconds: float,
    *,
    dry_run: bool,
) -> str:
    """Say that the checks that start the review passed on the pinned head and the
    rest still run, and how the step ends: the review starts beside them, or a dry
    run would start it (DEC-063 point 8)."""
    passed, rest = f"{', '.join(first)} passed on {short_sha(head.oid)}", ", ".join(gate.running)
    if dry_run:
        _say(
            f"ci: (dry-run) {passed} — would start the review, then wait up to "
            f"{_duration(wait_seconds)} for the rest: {rest}"
        )
        return _CI_WOULD_WAIT
    _say(f"ci: {passed} — the review starts beside the rest: {rest}")
    return _CI_FIRST_PASSED


def _failed_checks(gate: CiGateResult) -> str:
    """Each check that failed and where to read it, as a line says it."""
    return "; ".join(
        f"{check.name} ({check.outcome})" + (f" {check.url}" if check.url else "")
        for check in gate.failed
    )


def _read_pr(pr_number: int, config: dict[str, Any]) -> _Checks:
    """The PR's head, state, mergeability and checks, in one reading: the
    checks GitHub reports are the ones on the head it reports with them."""
    try:
        proc = gh_run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "headRefOid,state,mergeable,mergeStateStatus,statusCheckRollup",
            ],
            config,
            check=False,
        )
    except OSError as exc:
        return _Checks(problem=f"`gh` could not be run ({exc})")
    if proc.returncode != 0:
        return _Checks(problem=(proc.stderr or "").strip() or f"gh exited {proc.returncode}")
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return _Checks(problem="gh's answer is not JSON")
    if not isinstance(data, dict):
        return _Checks(problem="gh's answer names no pull request")
    raw = data.get("statusCheckRollup")
    rollup = [check for check in raw if isinstance(check, dict)] if isinstance(raw, list) else []
    return _Checks(
        head=str(data.get("headRefOid") or ""),
        state=str(data.get("state") or "").upper(),
        rollup=rollup,
        gate=evaluate_ci_gate(rollup),
        mergeable=str(data.get("mergeable") or "").upper(),
        merge_state=str(data.get("mergeStateStatus") or "").upper(),
    )


def _conflict_line(step: str, head: _Head) -> str:
    return (
        f"{step}: stopped — PR #{head.pr_number} conflicts with {head.base}, and GitHub runs "
        "no pull_request workflow on a PR that conflicts with its base. Merge "
        f"{head.base} into {head.branch} (`git merge {head.base_remote}/{head.base}`), resolve "
        f"the conflicts, push, and run `land-work {head.issue}` again"
    )


def _queued_base(pr_number: int, config: dict[str, Any]) -> bool | None:
    """Whether the PR's base merges through a queue, which builds the merge with the
    base itself: None where that cannot be read."""
    try:
        return merge_queue.read(pr_number, config).has_queue
    except merge_queue.Unreadable:
        return None


def _behind_stops(head: _Head, config: dict[str, Any]) -> bool:
    """Whether a PR the host reads as behind a base it merges only up to date stops
    at the `ci` step, before the review: where its base merges through no queue.
    Where whether it does cannot be read, one line says so and the run goes on: the
    merge step names the merge if the host refuses it
    ([project-management:DEC-064-base-merge-named] point 2)."""
    queued = _queued_base(head.pr_number, config)
    if queued is None:
        print(
            f"  ci: PR #{head.pr_number} reads as behind {head.base}, and whether {head.base} "
            "merges through a queue could not be read, so the run goes on: the merge step "
            f"names the merge of {head.base} if the host refuses the merge for it",
            flush=True,
        )
    return queued is False


def _behind_line(step: str, head: _Head) -> str:
    """The stop on a head the host reads as behind a base it merges only up to date:
    the merge of the base to make, which the landing names
    ([project-management:DEC-064-base-merge-named] point 1)."""
    return (
        f"{step}: stopped — the host merges only a branch up to date with {head.base}, and "
        f"reads PR #{head.pr_number} as behind it. Merge {head.base} into {head.branch} "
        f"(`git merge {head.base_remote}/{head.base}`), push, and run `land-work {head.issue}` "
        "again"
    )


def _ran_out(head: _Head, gate: CiGateResult, waited: float, wait_seconds: float) -> str:
    sha, issue = short_sha(head.oid), head.issue
    after = "(--no-wait)" if wait_seconds == 0 else f"after {_duration(waited)}"
    if gate.state == NO_RUN:
        return (
            f"ci: no check has been reported for {sha} {after}: its run has not started, or "
            "none will — no workflow runs on pull requests here, the workflows skip the "
            "paths this PR changes, its head commit asks to skip CI ([skip ci]), or a run "
            f"from a fork awaits approval. Run `land-work {issue}` again to keep waiting. "
            "Only in a project that runs no checks on pull requests — never because a "
            f"wait ran out — review it with `review-pr {issue}` and merge it, on the "
            f"person's authorisation, with `done-work {issue} --yes`: `done-work` does "
            "not wait for a check nobody reported"
        )
    return (
        f"ci: still running on {sha} {after}: {', '.join(gate.running)}. "
        f"Run `land-work {issue}` again to keep waiting"
    )


def _passed_detail(rollup: list[dict[str, Any]]) -> str:
    """` (8m, run <url>)` — how long the checks took and where to read them."""
    parts = [part for part in (_checks_took(rollup), _run_url(rollup)) if part]
    return f" ({', '.join(parts)})" if parts else ""


def _checks_took(rollup: list[dict[str, Any]]) -> str:
    started = [_instant(check.get("startedAt")) for check in rollup]
    completed = [_instant(check.get("completedAt")) for check in rollup]
    first = min((t for t in started if t is not None), default=None)
    last = max((t for t in completed if t is not None), default=None)
    if first is None or last is None or last < first:
        return ""
    return _duration((last - first).total_seconds())


def _run_url(rollup: list[dict[str, Any]]) -> str:
    """The workflow run the checks belong to, else the first check's page."""
    urls = [str(check.get("detailsUrl") or check.get("targetUrl") or "") for check in rollup]
    for url in urls:
        run = re.match(r"(https?://\S+/actions/runs/\d+)", url)
        if run:
            return f"run {run.group(1)}"
    first = next((url for url in urls if url), "")
    return f"run {first}" if first else ""


def _instant(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    return f"{seconds / 60:.0f}m"


# ---- review ----------------------------------------------------------------


def _review(
    args: argparse.Namespace,
    head: _Head,
    config: dict[str, Any],
    reading: issue_branch.Reading,
    *,
    beside_checks: bool,
) -> _ReviewEnd:
    """Have the reviewers whose verdicts are not fresh review the pinned head.

    Returns how the review ended when the run goes on, and stops it otherwise.
    The stop is chosen in this order: the head moved; a CHANGES_REQUESTED;
    something could not be read; a reviewer could not be run — so one
    reviewer's block is reported even when another timed out. `review-pr` is
    handed the issue's branch as this run read it (`reading`). `beside_checks`
    says checks still ran as the review started, so a CHANGES_REQUESTED's stop
    names each that has failed by then.
    """
    issue = head.issue
    labels = done_work._label_names(gh_get_issue(issue, config, fields="labels"))
    mode = resolve_mode(config, issue_labels=labels)
    if mode.mode == "human":
        _say(
            f"review: human review mode ({mode.source}) — no reviewer agent to run; "
            "the approval is done-work's gate"
        )
        return _ReviewEnd(clear=True, approval="the PR is approved")
    agents = _ReviewEnd(clear=True, approval="all required verdicts approved")
    # review-pr works out the required set itself, a contributed reviewer
    # included where the project registers no local reviewer of its own (#1934).
    argv = [str(issue), *_passed_through(args, review=True)]
    try:
        run = review_pr.review(
            argv, pinned_head=head.oid, branch_reading=reading, standing=head.standing
        )
    except (Exception, SystemExit) as exc:
        raise _Stop(
            EXIT_REVIEW_INCOMPLETE,
            f"review: stopped — review-pr failed ({_described(exc)}), so the review is not "
            f"complete. Run `land-work {issue}` again once it can run",
        ) from exc
    verdicts = {name: (token, run.kept_bodies.get(name, "")) for name, token in run.kept.items()}
    verdicts.update(run.posted)
    requested = [name for name, (token, _) in verdicts.items() if token == CHANGES_REQUESTED]
    for name in requested:
        for line in _blocking_lines(verdicts[name][1], head.pr_number):
            print(f"  [{name}] {line}")
    advisories = 0
    for name, (token, body) in verdicts.items():
        if token == APPROVED:
            for line in _first_lines(body, TAG_ADVISORY):
                print(f"  [{name}] {line}")
                advisories += 1
    if run.moved_to is not None:
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"review: stopped — PR #{head.pr_number}'s head is {short_sha(run.moved_to)}, "
            f"not {short_sha(head.oid)}, the head this run pinned. Nothing was merged; "
            f"`land-work {issue}` checks and reviews the new head",
        )
    if requested:
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"review: changes requested by {', '.join(requested)} — the blocking findings "
            f"are above{_failed_meanwhile(head, config) if beside_checks else ''}; merge not "
            "started",
        )
    if run.reason:
        raise _Stop(EXIT_UNREADABLE, f"review: stopped — {run.reason}")
    if run.failed:
        could_not = "; ".join(f"{name}: {why}" for name, why in run.failed.items())
        raise _Stop(
            EXIT_REVIEW_INCOMPLETE,
            f"review: stopped — a reviewer could not be run, so the review is not "
            f"complete ({could_not}). Run `land-work {issue}` again once it can run",
        )
    if run.exit_code != 0:
        raise _Stop(
            EXIT_REVIEW_INCOMPLETE,
            f"review: stopped — review-pr exited {run.exit_code}, so the review is not complete",
        )
    if not run.required:
        _say("review: no local reviewer is required — the approval is done-work's gate")
        return agents
    kept, ran = len(run.kept), len(run.posted)
    if args.dry_run:
        would = f"run {', '.join(run.would_run)}" if run.would_run else "run none"
        _say(f"review: (dry-run) would keep {kept} fresh and {would}")
        return _ReviewEnd(clear=not run.would_run, approval=agents.approval)
    noted = (
        f"; {advisories} advisor{'y' if advisories == 1 else 'ies'} above (every verdict in "
        f"full: `show-pr {head.pr_number} --field review`)"
        if advisories
        else ""
    )
    _say(f"review: {kept} kept fresh, {ran} re-run — all approved{noted}")
    return agents


def _failed_meanwhile(head: _Head, config: dict[str, Any]) -> str:
    """What the stop on a CHANGES_REQUESTED adds where the review ran beside checks:
    each that has failed by then, so one fix round carries both; "" where none has,
    or the checks cannot be read, since the stop stands without them."""
    checks = _read_pr(head.pr_number, config)
    if checks.head != head.oid or checks.gate is None or not checks.gate.failed:
        return ""
    return f", and a check failed on {short_sha(head.oid)}: {_failed_checks(checks.gate)}"


def _blocking_lines(body: str, pr_number: int) -> list[str]:
    """What a CHANGES_REQUESTED says blocks: the first line of each `[block]`
    finding, else the verdict's first lines and where to read it all."""
    blocking = _first_lines(body, TAG_BLOCK)
    if blocking:
        return blocking
    text = [
        friction_answers.shown(line.strip())
        for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith(("Reviewer agent (", "<!--"))
    ]
    pointer = (
        f"(no finding tagged blocking — read it all with `show-pr {pr_number} --field review`)"
    )
    return [*text[:_UNTAGGED_LINES], pointer]


def _first_lines(body: str, tag: str) -> list[str]:
    """The first line of each finding of `body` that counts as `tag` (DEC-028's
    finding tags; an untagged finding counts as `[advisory]`), its list marker
    dropped and every character a terminal would act on escaped."""
    return [friction_answers.shown(finding.first_line) for finding in tagged(body, tag)]


# ---- answers ---------------------------------------------------------------


def _answers(
    args: argparse.Namespace, head: _Head, config: dict[str, Any], capability_root: Path
) -> _AnswersEnd:
    """The answers the change wrote, and the friction settings it alters, derived
    from the change check at the pinned head against the PR's base (DEC-065 point
    2): what the person who authorises the merge is told, as information, kept for
    the lines above the `ready:` line, the prompt or the merge (DEC-065 point 4).
    The description carries no list of them: a region an earlier run left there is
    removed (DEC-065 point 1).
    Stops the run on answers it cannot read, on a file the change touches whose
    front matter does not parse, on a base that changed a file the answers' words
    are on or the friction settings the change alters, on a sentence that reads as a
    closing reference (DEC-065 point 5), and on a write the host answered with an
    error, which merges nothing; a dry run writes nothing."""
    issue, number, sha = head.issue, head.pr_number, short_sha(head.oid)
    if not head.base_branch:
        raise _Stop(
            EXIT_UNREADABLE,
            f"{STEP}: PR #{number}'s base branch could not be read, so the change check "
            f"has no base to be run against. Nothing was merged; run `land-work {issue}` "
            "again",
        )
    fed = answers_told.at_head(
        head.oid,
        head.base_branch,
        capability_root,
        lambda: _read_body(head, config),
        source=head.source,
        from_checkout=head.standing.may_start,
    )
    derived = fed.derived
    document = derived.document
    if derived.needs_checkout:
        # Only a base that moved since `_take_test` read it comes here.
        raise _person_stop(head, STEP)
    if document is None:
        raise _Stop(
            EXIT_UNREADABLE,
            f"{STEP}: the change check's answers at {sha} could not be read — "
            f"{derived.problem}. Nothing was merged; run `land-work {issue}` again",
        )
    touched = _unreadable_in_change(derived)
    if touched:
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"{STEP}: refused — front matter the change check cannot read, in "
            f"{_files(touched)} this change touches, so the answers on it cannot be read. "
            f"Fix it (`pkit validate` names the problem), push, and run `land-work {issue}` "
            "again",
        )
    grants = _grant_change(fed.grants, head)
    moved = _grants_moved(derived, head, capability_root, grants)
    body = fed.body
    _warn_unread(friction_answers.strip(body))
    unlisted = _warn_unlisted(document, body, head)
    if derived.listed and derived.outdated:
        _refuse_moved_base(derived, head)
    _refuse_closing_references(fed.sentences, head)
    settings = derived.settings
    counted = friction_answers.counted_told(document)
    end = _AnswersEnd(
        counted.updated,
        counted.left,
        counted.targets,
        settings=len(settings),
        told=fed.told,
        unasked=counted.unasked,
        grants=grants,
        grants_moved=moved,
        # Against the base's tip, which `derive` fetched for the run: they stop nothing
        # (DEC-055 point 3).
        apart=len(friction_answers.apart(document)),
        checked=document,
        unlisted=unlisted,
        unsaid=tuple(friction_answers.unsaid(document, fed.sentences)),
        left_moved=_left_moved(head, document),
    )
    count = friction_answers.documents(derived.answers)
    written = _with_grants(friction_answers.affected(count, settings=bool(settings)), grants)
    _say(f"{STEP}: {written}{_remove_list(args, head, body, config, capability_root)}")
    return end


def _refuse_closing_references(sentences: Mapping[str, str], head: _Head) -> None:
    """Refuse a sentence that reads as a closing reference, which nothing overrides:
    it stays in the description and the squash commit, so the host would close an
    issue with it at merge, past the checkbox gate and the cascade (DEC-065 point 5)."""
    found = friction_answers.closing_references(sentences)
    if found:
        said = "; ".join(friction_answers.closing_message(*one) for one in found)
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"{STEP}: refused — {said}, with `edit-pr {head.pr_number} --body-file <file>`, "
            f"and run `land-work {head.issue}` again. Nothing was written",
        )


def _left_moved(head: _Head, document: Mapping[str, Any]) -> str:
    """Where the head is a later one an earlier head's authorisation covers, why that
    authorisation does not cover what the pinned head leaves out of date, or "": it
    leaves something the head authorised did not, or that head's answers could not be
    read. The person was told what that head leaves, so anything more is what nobody
    told them (COR-050 point 3, DEC-065 point 4). A person's word covers the commit they
    named and no earlier one, so that head is read from a checkout only where the head
    passed the test (DEC-067 points 1 and 4)."""
    left = friction_answers.left_out(document)
    if not head.authorised or not left:
        return ""
    earlier = short_sha(head.authorised)
    found = friction_answers.checked(
        head.authorised, head.base_branch, from_checkout=head.standing.passes
    ).document
    if found is None:
        return f"something left out of date, with the answers at {earlier} unread"
    told = friction_answers.left_out(found)
    new = any(line not in told for line in left)
    return f"something left out of date that {earlier} did not leave" if new else ""


def _remove_list(
    args: argparse.Namespace, head: _Head, body: str, config: dict[str, Any], capability_root: Path
) -> str:
    """Remove from the PR's description the region of answers an earlier run wrote
    (DEC-065 point 1): what the step's line says of it, or "" where the description
    carries none. A start marker with no end marker draws a warning, and the
    description stays as it is. A dry run removes nothing; a write the host answered
    with an error stops the run, which merges nothing."""
    if friction_answers.orphaned(body):
        print(f"  warn: {friction_answers.ORPHAN_WARNING}")
    if not friction_answers.has_list(body):
        return ""
    if args.dry_run:
        return f" — would remove {_EARLIER_LIST} from the pull request's description"
    problem = _write_body(head, _stamped(body, capability_root), config)
    if problem:
        raise _Stop(
            EXIT_RETRY,
            f"{STEP}: {_EARLIER_LIST} could not be removed from PR #{head.pr_number}'s "
            f"description: {problem}. Nothing was merged; run `land-work {head.issue}` again",
        )
    return f" — removed {_EARLIER_LIST} from the pull request's description"


def _with_grants(written: str, grants: tuple[fixers.GrantChange, ...]) -> str:
    """The step's count of documents, with a change to the fixers' grant list after
    it where the change makes one."""
    if not grants:
        return written
    return f"{written}{', but ' if written == 'none' else ', plus '}{GRANTS}"


def _grant_change(
    found: tuple[fixers.GrantChange, ...] | fixers.ChangeUnread, head: _Head
) -> tuple[fixers.GrantChange, ...]:
    """Each grant and refusal the change adds to the fixers' grant list or removes
    from it: `fixers` in this capability's project configuration, as `found` read
    it where the head left its base and at the head (DEC-056 point 2). A list that
    cannot be read stops the run, which merges nothing it could not show."""
    if not isinstance(found, fixers.ChangeUnread):
        return found
    issue, sha = head.issue, short_sha(head.oid)
    if found.at_head:
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"{STEP}: refused — the fixers' grant list at {sha} cannot be read ({found.why}), "
            f"so what the change does to it cannot be shown. Fix it (`pkit validate` names the "
            f"problem), push, and run `land-work {issue}` again. Nothing was written",
        )
    raise _Stop(
        EXIT_UNREADABLE,
        f"{STEP}: what the change does to the fixers' grant list could not be read "
        f"({found.why}), so it cannot be shown. Nothing was merged; run `land-work {issue}` "
        "again",
    )


def _grants_moved(
    derived: friction_answers.Derivation,
    head: _Head,
    capability_root: Path,
    grants: tuple[fixers.GrantChange, ...],
) -> str:
    """Where the head is a later one an earlier head's authorisation covers, why that
    authorisation does not cover its change to the fixers' grant list, or "": the
    change differs from the one at the head authorised, or that one could not be
    read. The run found the change at that head when the person was shown it, so
    another change at the later head is one nobody was shown (DEC-056 point 2).

    The change at the head authorised is read from where the pinned head left its
    base, which the change check names, and only where the head authorised left
    the base there too: otherwise it could not be read, and a person decides."""
    if not head.authorised:
        return ""
    earlier = short_sha(head.authorised)
    unread = f"a change to the fixers' grant list that could not be read at {earlier}"
    left = derived.merge_base
    if not _left_base_at(left, head.authorised, derived.tip):
        return unread
    found = fixers.change_between(left, head.authorised, capability_root)
    if isinstance(found, fixers.ChangeUnread):
        return unread
    if found != grants:
        return f"a change to which fixers may start other than the one at {earlier}"
    return ""


def _left_base_at(fork: str, oid: str, tip: str) -> bool:
    """Whether commit `oid` left the base, whose commit is `tip`, at `fork`: `fork` is
    in its history, and no later commit of the base is. Read by ancestry alone, since
    pm computes no fork point of its own (COR-054 point 5); False where git cannot
    say."""
    if not fork or not tip:
        return False
    if _git("merge-base", "--is-ancestor", fork, oid).returncode != 0:
        return False
    beyond = _count_commits(f"{fork}..{tip}")
    return beyond is not None and _count_commits(f"{oid}..{tip}") == beyond


def _refuse_moved_base(derived: friction_answers.Derivation, head: _Head) -> None:
    """Where the base moved on after the head left it, refuse when its commits
    since changed what the answers' words are on — the file the change check names
    for an answer, an answer file or the artefact's own (`listed_paths`) — or the
    friction settings the change alters: the merge could then land answers other
    than those the reviewer checked (DEC-065 point 5). An outdated base that changed
    none of them stops nothing; one whose changes cannot be read is refused, never
    guessed."""
    paths = friction_answers.listed_paths(derived.document or {})
    changed: list[str] | None = None
    if derived.merge_base and derived.tip:
        proc = _git("diff", "--name-only", "-z", "--no-renames", derived.merge_base, derived.tip)
        if proc.returncode == 0:
            changed = sorted(paths & set(proc.stdout.split("\0")))
    settings: tuple[Any, ...] | str = ()
    if derived.settings and changed is not None:
        settings = friction_answers.settings_change(derived.merge_base, derived.tip)
    if changed == [] and settings == ():
        return
    issue, number, sha = head.issue, head.pr_number, short_sha(head.oid)
    if changed is None or isinstance(settings, str):
        which = (
            "which of the answers' files and settings its commits since changed could not be read"
        )
    else:
        what = [f"{_files(changed)} the answers' words are on"] if changed else []
        what += [friction_answers.SETTINGS_WHERE + " the change alters"] if settings else []
        which = f"its commits since changed {' and '.join(what)}"
    raise _Stop(
        EXIT_NEEDS_CHANGE,
        f"{STEP}: refused — {head.base} moved on after PR #{number}'s head left it, and "
        f"{which}, so its merge can land answers other than those at {sha}. Merge "
        f"{head.base} into {head.branch} (`git merge {head.base_remote}/{head.base}`), push, and "
        f"run `land-work {issue}` again",
    )


def _unreadable_in_change(derived: friction_answers.Derivation) -> list[str]:
    """The files whose front matter does not parse at the head that the change
    touched: words on them may be answers the change check cannot read. A file
    the change did not touch holds no answer of the change. Where the change's
    files cannot be read, every such file counts."""
    if not derived.unreadable:
        return []
    proc = _git("diff", "--name-only", "-z", "--no-renames", derived.merge_base, derived.head)
    if proc.returncode != 0 or not derived.merge_base:
        return list(derived.unreadable)
    changed = set(proc.stdout.split("\0"))
    return [path for path in derived.unreadable if path in changed]


def _files(paths: list[str]) -> str:
    shown = ", ".join(paths[:3]) + (f" and {len(paths) - 3} more" if len(paths) > 3 else "")
    return f"{len(paths)} file{'' if len(paths) == 1 else 's'} ({shown})"


def _read_body(head: _Head, config: dict[str, Any]) -> str:
    """The PR's description as GitHub has it; stops the run when it cannot be read."""
    pr_number = head.pr_number
    problem = ""
    try:
        proc = gh_run(["gh", "pr", "view", str(pr_number), "--json", "body"], config, check=False)
    except OSError as exc:
        problem = f"`gh` could not be run ({exc})"
    else:
        if proc.returncode != 0:
            problem = (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
        else:
            try:
                data = json.loads(proc.stdout)
            except ValueError:
                data = None
            if isinstance(data, dict):
                return str(data.get("body") or "")
            problem = "gh's answer names no pull request"
    raise _Stop(
        EXIT_UNREADABLE,
        f"{STEP}: PR #{pr_number}'s description could not be read: {problem}. Nothing was "
        f"merged; run `land-work {head.issue}` again",
    )


def _warn_unread(description: str) -> None:
    """A warning for each item under the description's sentences heading that gives
    no sentence, naming its line in `description` — the description as this run
    leaves it, without a list an earlier run wrote — and the form a sentence
    takes."""
    for item in friction_answers.unread(description):
        print(f"  warn: {friction_answers.unread_warning(item)}")


def _warn_unlisted(document: Mapping[str, Any], description: str, head: _Head) -> tuple[str, ...]:
    """A warning for each sentence the author gives in `description` on a document
    the change check's `document` at the pinned head does not mark `updated`: no
    reviewer checks it, so the author removes it with the edit named (DEC-055
    point 3). It refuses nothing; the documents it names hold a run authorised up
    front (`_unlisted_hold`)."""
    said = friction_answers.sentences(description)
    found = tuple(friction_answers.unlisted(document, said))
    for location in found:
        warning = friction_answers.unlisted_warning(location, head.oid, head.pr_number)
        print(f"  warn: {warning}")
    return found


def _stamped(body: str, capability_root: Path) -> str:
    """`body` without a list an earlier run wrote, and the provenance footer last, as
    every body-writing script writes one (ADR-037)."""
    stripped = friction_answers.strip(provenance.strip_footer(body))
    return provenance.stamp(stripped, provenance.read_versions(capability_root))


def _write_body(head: _Head, body: str, config: dict[str, Any]) -> str:
    """Write the PR's description; why it failed, or "" when it did not."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(body)
        path = f.name
    try:
        argv = ["gh", "pr", "edit", str(head.pr_number), "--body-file", path]
        try:
            proc = gh_run(argv, config, check=False)
        except OSError as exc:
            return f"`gh` could not be run ({exc})"
        if proc.returncode == 0:
            return ""
        return (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
    finally:
        with contextlib.suppress(OSError):
            Path(path).unlink()


# ---- the merge as it would land ----------------------------------------------


def _merge_check(
    args: argparse.Namespace,
    head: _Head,
    answers: _AnswersEnd,
    config: dict[str, Any],
    capability_root: Path,
) -> None:
    """The change check on the merge of the pinned head with the PR's base as it stands,
    fetched now (`friction_answers.merged`, DEC-055 point 6), said in one line. Stops the
    run, with nothing merged, where the check fails there, naming each document it
    fails on above the line; where the merge conflicts; and where the check cannot be
    read. A base the head already holds, at the tip the head's own check read, is that
    check's: nothing is run again. A merge can need a resolver its head did not, so for
    a head from elsewhere nobody named, that asks or stops as the head's own check does
    (DEC-067 point 3)."""
    issue, sha, base = head.issue, short_sha(head.oid), head.base
    found = friction_answers.merged(
        head.oid,
        head.base_branch,
        checked=answers.checked,
        from_checkout=head.standing.may_start,
    )
    if found.needs_checkout:
        _named_or_stopped(args, head, config, capability_root, step=MERGE_CHECK)
        found = friction_answers.merged(head.oid, head.base_branch, checked=answers.checked)
    if found.problem is not None:
        raise _Stop(
            EXIT_UNREADABLE,
            f"{MERGE_CHECK}: the change check on {sha} merged with {base} could not be read "
            f"— {friction_answers.shown(found.problem)}. Nothing was merged; run "
            f"`land-work {issue}` again",
        )
    merge_into = (
        f"Merge {base} into {head.branch} (`git merge {head.base_remote}/{base}`), "
        if found.merge != head.oid
        else ""
    )
    if found.conflicts:
        files = _files([friction_answers.shown(path) for path in found.conflicts])
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"{MERGE_CHECK}: refused — {sha} conflicts with {base} as it stands, at "
            f"{short_sha(found.tip)}, in {files}. Merge {base} into {head.branch} (`git merge "
            f"{head.base_remote}/{base}`), resolve the conflicts, push, and run "
            f"`land-work {issue}` again. Nothing was merged",
        )
    tip = short_sha(found.tip)
    where = (
        f"{sha} merged with {base} at {tip}"
        if found.merge != head.oid
        else f"{sha}, which holds {base} at {tip}"
    )
    documents = _print_findings_at_merge(found.failing)
    if not found.failed:
        # In warning mode the check fails nothing: what it finds is shown, and stops
        # nothing (COR-050 point 12).
        reported = (
            f", and reports {_count(len(documents), 'document')} above, which the project's "
            "friction mode fails nothing on: for information"
            if documents
            else ""
        )
        _say(f"{MERGE_CHECK}: the change check passes on {where}{reported}")
        return
    named = (
        f", on {_count(len(documents), 'document')} ({', '.join(documents)}), above"
        if documents
        else ", on findings this command does not name: `pkit friction check` names them"
    )
    settle = (
        f"{merge_into}settle each finding there"
        if merge_into
        else f"Settle each finding in {head.branch}"
    )
    raise _Stop(
        EXIT_NEEDS_CHANGE,
        f"{MERGE_CHECK}: refused — the change check fails on {where}{named}. {settle}, push, "
        f"and run `land-work {issue}` again. Nothing was merged",
    )


def _print_findings_at_merge(findings: tuple[Mapping[str, Any], ...]) -> list[str]:
    """Each finding a line, `<document>: <kind> — <message>`, every character a terminal
    would act on escaped; the documents they are on, each once, in order."""
    shown = friction_answers.shown
    documents: list[str] = []
    for finding in findings:
        location = shown(str(finding.get("location") or "?"))
        kind, message = str(finding.get("kind") or "?"), str(finding.get("message") or "")
        print(f"  {location}: {shown(kind)} — {shown(message)}")
        if location not in documents:
            documents.append(location)
    return documents


def _count(count: int, noun: str) -> str:
    return f"{count} {noun}" + ("" if count == 1 else "s")


# ---- findings to judge -----------------------------------------------------


def _found_at_start(head: _Head, config: dict[str, Any]) -> frozenset[Verdict] | None:
    """Every verdict on the PR as this run found it at its start, whoever
    posted it, or None when the PR's comments could not be read.

    A verdict is the one found only when every word of its comment, its
    author's name and its time are the same, so one edited or posted since is
    another. None finds nothing: each verdict carrying a `[person]` finding is
    then new to the run, so a read that fails holds the run, never lets it
    merge (DEC-055 point 3)."""
    data = _view(head.pr_number, ("comments",), config)
    if isinstance(data, str):
        return None
    return frozenset(all_verdicts(data.get("comments") or []))


def _view(pr_number: int, fields: tuple[str, ...], config: dict[str, Any]) -> dict[str, Any] | str:
    """`gh pr view <N> --json <fields>`, or why it could not be read."""
    try:
        proc = gh_run(
            ["gh", "pr", "view", str(pr_number), "--json", ",".join(fields)], config, check=False
        )
    except OSError as exc:
        return f"`gh` could not be run ({exc})"
    if proc.returncode != 0:
        return (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return "gh's answer is not JSON"
    if not isinstance(data, dict):
        return "gh's answer names no pull request"
    return data


@dataclass(frozen=True)
class _PersonVerdict:
    """A verdict carrying `[person]` findings, as the step judged it."""

    verdict: Verdict
    findings: tuple[Finding, ...]
    freshness: Freshness


def _findings(
    args: argparse.Namespace,
    head: _Head,
    config: dict[str, Any],
    capability_root: Path,
    found: frozenset[Verdict] | None,
) -> _FindingsEnd:
    """Print each `[person]` finding whole, from each reviewer's latest verdict
    as the merge gate selects it, and say whether this run's `--yes` covers
    them (DEC-055 point 3). A verdict that no longer stands for the pinned
    head, by the gate's freshness rule, is printed marked stale. Then print
    each accepted decision record the change alters, a line each (#2161).

    `found` is what the run found at its start, None when it read nothing or
    holds nothing. A run with neither prints nothing, and goes on as it would
    without the step. Stops the run when the verdicts cannot be read, the head
    moved, or — with a `[person]` finding to show — the reviewers whose
    verdicts count cannot be resolved, as when a remote reviewer's verdict
    carries one and the PR's author cannot be read; and when the accepted
    records the change alters cannot be read.

    The accepted records are derived from the pinned head and where it left
    its base, so they stand for the head and are there when the run starts:
    a `--yes` for that head covers them, as it covers a `[person]` finding
    whose verdict the run found at its start, standing for the head. The
    `ready:` stop that names the head shows them, and the pm skill has them
    shown before any `--yes` is asked for. At a later head an earlier head's
    authorisation covers, the list must be the one at the head authorised
    (`_records_moved`): a merge of the base can move where the head left it,
    and so the list, though the author changed nothing but answers."""
    judged = _person_verdicts(head, config, capability_root)
    # Before the records, so a stop on them does not hide a finding read here.
    for one in judged:
        _print_findings(one)
    altered = _accepted_records(head)
    moved = _records_moved(head, altered)
    if not judged and not altered:
        return _FindingsEnd(records_moved=moved)
    for line in accepted_records.lines(altered):
        print(f"  {line}")
    count = _findings_in(judged)
    held = _held(args, head, judged, found) if judged else None
    _say(_findings_line(count + len(altered), judged))
    return _FindingsEnd(count, held, records=len(altered), records_moved=moved)


def _findings_at_review_stop(head: _Head, config: dict[str, Any], capability_root: Path) -> None:
    """Print each `[person]` finding whole as the review step stops, with the step's
    line, as `_findings` prints them. One reviewer's block, or one that failed, would
    otherwise hide what another posted in this run, and a later `--yes` would find that
    verdict at its start and merge on it (DEC-055 point 3).

    The head may have moved, which is that stop's own, so a verdict is judged for the
    head the PR has now. Nothing here changes the stop: what it cannot read draws a
    `warn:` line."""
    try:
        judged = _person_verdicts(head, config, capability_root, any_head=True)
    except _Stop as unread:
        print(f"  warn: {unread.line}", flush=True)
        return
    if not judged:
        return
    for one in judged:
        _print_findings(one)
    _say(_findings_line(_findings_in(judged), judged))


def _findings_in(judged: list[_PersonVerdict]) -> int:
    """How many `[person]` findings `judged` carry."""
    return sum(len(one.findings) for one in judged)


def _findings_line(shown: int, judged: list[_PersonVerdict]) -> str:
    """The step's line: how many findings are above, and how many of `judged`'s are
    marked stale."""
    stale = _findings_in([one for one in judged if not one.freshness.fresh])
    return f"{FINDINGS}: {shown}, above" + (f" ({stale} marked stale)" if stale else "")


def _accepted_records(head: _Head) -> tuple[accepted_records.Altered, ...]:
    """The accepted decision records the change alters, derived at the pinned head
    against the PR's base (`accepted_records.derive`, #2161). Stops the run when they
    cannot be read, since what the step cannot read it cannot show."""
    issue, number = head.issue, head.pr_number
    if not head.base_branch:
        raise _Stop(
            EXIT_UNREADABLE,
            f"{FINDINGS}: PR #{number}'s base branch could not be read, so the accepted "
            f"records this change alters cannot be listed. Nothing was merged; run "
            f"`land-work {issue}` again",
        )
    derived = accepted_records.derive(head.oid, head.base_branch)
    if derived.problem is not None:
        raise _Stop(
            EXIT_UNREADABLE,
            f"{FINDINGS}: the accepted records this change alters at {short_sha(head.oid)} "
            f"could not be read — {derived.problem}. Nothing was merged; run "
            f"`land-work {issue}` again",
        )
    return derived.records


def _records_moved(head: _Head, records: tuple[accepted_records.Altered, ...]) -> str:
    """Where the head is a later one an earlier head's authorisation covers, why that
    authorisation does not cover the accepted records the change alters, or "": the list
    differs from the one at the head authorised, or that one could not be read. The
    person was shown the list at that head, so another list at the later head is one
    nobody was shown, as another change to the fixers' grant list is (DEC-056 point 2).
    A merge of the base can bring one: where the head left the base moves, so a record
    the base accepted meanwhile can join the list."""
    if not head.authorised:
        return ""
    earlier = short_sha(head.authorised)
    found = accepted_records.derive(head.authorised, head.base_branch)
    if found.problem is not None:
        return f"accepted records this change alters that could not be read at {earlier}"
    if found.records != records:
        return f"a change to accepted records other than the one at {earlier}"
    return ""


def _person_verdicts(
    head: _Head, config: dict[str, Any], capability_root: Path, *, any_head: bool = False
) -> list[_PersonVerdict]:
    """Each latest verdict carrying a `[person]` finding, as the merge gate selects it,
    judged by the gate's freshness rule; none where no marked verdict carries one.
    Stops the run when the verdicts cannot be read, the head moved, or — with a
    `[person]` finding to show — the reviewers whose verdicts count cannot be
    resolved. `any_head` reads them at whichever head the PR has, and judges them for
    it, so a head that moved stops nothing."""
    issue, number = head.issue, head.pr_number
    data = _view(number, _FINDINGS_VIEW, config)
    if isinstance(data, str):
        raise _Stop(
            EXIT_UNREADABLE,
            f"{FINDINGS}: PR #{number}'s verdicts could not be read: {data}. Nothing was "
            f"merged; run `land-work {issue}` again",
        )
    now = head_sha(data)
    if now != head.oid and not any_head:
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"{FINDINGS}: stopped — PR #{number}'s head is {short_sha(now) or 'unknown'}, "
            f"not {short_sha(head.oid)}, the head this run pinned. Nothing was merged; "
            f"`land-work {issue}` checks and reviews the new head",
        )
    comments = data.get("comments") or []
    # Only a marked verdict carrying a `[person]` finding needs the gate's
    # selection: without one there is nothing to show, from anyone.
    if not any(_person(verdict) for verdict in marked_candidates(comments)):
        return []
    # A remote verdict counts only from someone other than the PR's author:
    # with no author read, `gate_membership` counts none, so a remote
    # reviewer's `[person]` finding would go unshown, though its verdict may
    # not be the author's own (#1485). A local verdict is read with no author
    # exclusion, so its findings are shown as before.
    author = pr_author(data)
    remote = frozenset(remote_baseline(config))
    if not author and any(
        verdict.path == PATH_REMOTE and verdict.reviewer in remote and _person(verdict)
        for verdict in marked_candidates(comments)
    ):
        raise _unresolved(issue, f"PR #{number}'s author could not be read")
    review = done_work._resolve_review(number, config, capability_root.parent.parent.parent)
    if not review.resolution.ok:
        error = review.resolution.error
        raise _unresolved(issue, error.message if error is not None else "the resolution failed")
    remote_ok, local_ok = gate_membership(
        remote_baseline=remote,
        required_local=review.resolution.required_local,
        author_login=author,
    )
    freshness = review.freshness_rule(data)
    return [
        _PersonVerdict(verdict, person, freshness.assess(verdict))
        for verdict in gate_candidates(
            comments, local_reviewer_ok=local_ok, remote_reviewer_ok=remote_ok
        )
        if (person := _person(verdict))
    ]


def _unresolved(issue: int, why: str) -> _Stop:
    """The stop when whose verdicts count cannot be told, and so which
    `[person]` findings to show: nothing is shown and nothing merged."""
    return _Stop(
        EXIT_UNREADABLE,
        f"{FINDINGS}: whose verdicts count could not be resolved ({why}), so the "
        f"findings a reviewer left for a person to judge cannot be shown. Nothing was "
        f"merged; run `land-work {issue}` again",
    )


def _person(verdict: Verdict) -> tuple[Finding, ...]:
    return tuple(tagged(verdict.body, TAG_PERSON))


def _print_findings(judged: _PersonVerdict) -> None:
    """Each `[person]` finding of one verdict, whole, under its reviewer —
    marked stale when the verdict no longer stands for the head — with every
    character a terminal would act on escaped."""
    shown = friction_answers.shown
    name = shown(judged.verdict.reviewer)
    stale = "" if judged.freshness.fresh else f"(stale: {shown(judged.freshness.reason)}) "
    lead = f"  [{name}] {stale}"
    under = " " * len(f"  [{name}] ")
    for finding in judged.findings:
        first, *rest = finding.text.split("\n")
        print(f"{lead}{shown(first)}")
        for line in rest:
            print(f"{under}{shown(line)}".rstrip())


def _held(
    args: argparse.Namespace,
    head: _Head,
    judged: list[_PersonVerdict],
    found: frozenset[Verdict] | None,
) -> str | None:
    """Why this run's `--yes` does not cover the `[person]` findings, or None
    when it does, or when there is no `--yes` to cover them (DEC-055 point 3).

    It covers them only when the run found, at its start, each verdict carrying
    them, and each stands for the head it merges. A verdict that does not
    stand for that head holds every run until its reviewer posts again for the
    head, and the reason names that review; one this run posted, or one
    posted while it ran, holds only this run."""
    if not args.yes or args.dry_run:
        return None
    sha = short_sha(head.oid)
    stale = [one for one in judged if not one.freshness.fresh]
    if stale:
        one = len(stale) == 1
        names = ", ".join(friction_answers.shown(o.verdict.reviewer) for o in stale)
        again = (
            f"; `review-pr {head.issue}` runs a local reviewer again"
            if any(o.verdict.path == PATH_LOCAL for o in stale)
            else ""
        )
        return (
            f"{_whose(stale)} {'does' if one else 'do'} not stand for {sha}, so no --yes "
            f"covers {_them(stale)} until {names} {'posts' if one else 'post'} one that "
            f"does{again}"
        )
    if found is None:
        return (
            f"the verdicts could not be read when this run started, so its --yes does not "
            f"cover {_them(judged)}"
        )
    new = [one for one in judged if one.verdict not in found]
    if new:
        return (
            f"{_whose(new)} came after this run's --yes was given, so the --yes does not "
            f"cover {_them(new)}"
        )
    return None


def _whose(judged: list[_PersonVerdict]) -> str:
    """`code-reviewer's verdict`, or `the verdicts of a, b`."""
    names = [friction_answers.shown(one.verdict.reviewer) for one in judged]
    if len(names) == 1:
        return f"{names[0]}'s verdict"
    return f"the verdicts of {', '.join(names)}"


def _them(judged: list[_PersonVerdict]) -> str:
    """How the findings of `judged` are named: `its finding`, `their findings`."""
    count = _findings_in(judged)
    owner = "its" if len(judged) == 1 else "their"
    return f"{owner} finding{'' if count == 1 else 's'}"


# ---- merge -----------------------------------------------------------------


def _ready(
    args: argparse.Namespace,
    head: _Head,
    review: _ReviewEnd,
    config: dict[str, Any],
    answers: _AnswersEnd,
    to_judge: _FindingsEnd,
    reading: issue_branch.Reading,
    uncovered: str = "",
) -> int:
    """No authorisation to merge — none given, a `--yes` the findings to judge above
    hold, or one for an earlier head that does not cover this one after all
    (`uncovered`, DEC-055 point 3): run done-work's gates as a dry run on the
    pinned head, and say the head is ready, with the command that merges it —
    and, where a verdict carrying a finding to judge does not stand for the head,
    the review it waits for. Above the `ready:` line, what the person who
    authorises the merge is told, as information, not a gate (DEC-065 point 4):
    what changed in each updated document, in its author's sentence, which
    documents are left out of date, with each deferral's words, which targets of
    a link are left out of date, with each revisit entry's words, each answer the
    change check did not ask for, the friction settings changed, each revalidation
    the merge would leave answered apart, and each grant and refusal the change
    adds to the fixers' grant list or removes."""
    argv = [str(head.issue), *_passed_through(args, review=False), "--dry-run"]
    try:
        end = done_work.run(argv, pinned_head=head.oid, branch_reading=reading)
    except (Exception, SystemExit) as exc:
        failure = _described(exc)
        raise _Stop(*_done_work_failed(failure, head.issue, head, config, merging=False)) from exc
    if end.kind != done_work.PLANNED:
        code, line = _judged(end, head, args, config)
        _end(line)
        return code
    for line in answers.told:
        print(f"  {line}")
    _end(
        f"ready: {short_sha(head.oid)} — CI passed, {review.approval}{answers.phrase()}"
        f"{to_judge.phrase()}{uncovered}; merge "
        f"with: pkit pm land-work {head.issue} --yes --expect-head {head.oid}"
    )
    return EXIT_READY


def _merge(
    args: argparse.Namespace,
    head: _Head | None,
    config: dict[str, Any],
    reading: issue_branch.Reading,
    answers: _AnswersEnd | None = None,
) -> int:
    """Hand over to done-work — to land the pinned head, or, with no open PR,
    only to complete a PR that has merged — and say in one line how it ended.
    What the person who authorises the merge is told (`answers.told`) is printed
    first, before done-work asks or merges (DEC-065 point 4)."""
    for line in answers.told if answers is not None else ():
        print(f"  {line}")
    argv = [str(args.issue_number), *_passed_through(args, review=False)]
    end = _run_done_work(argv, head, config, reading, merging=not args.dry_run)
    if end.kind == done_work.PLANNED:
        _end("merge: (dry-run) done-work's plan is above")
        return EXIT_MERGED
    code, line = _judged(end, head, args, config)
    if head is not None and head.authorised and code == EXIT_MERGED:
        line = f"{line}, at {short_sha(head.oid)} — {head.covered}"
    _end(f"merge: (dry-run) {line.removeprefix('merge: ')}" if args.dry_run else line)
    return code


def _run_done_work(
    argv: list[str],
    head: _Head | None,
    config: dict[str, Any],
    reading: issue_branch.Reading,
    *,
    merging: bool,
) -> Any:
    """How done-work's run ended (`done_work.DoneWorkRun`), handed the issue's
    branch as this run read it. When it raised, the run stops, with what
    GitHub reports of the PR."""
    try:
        if head is None:
            return done_work.run(argv, merged_only=True, branch_reading=reading)
        return done_work.run(argv, pinned_head=head.oid, branch_reading=reading)
    except (Exception, SystemExit) as exc:
        issue = int(argv[0])
        failed = _done_work_failed(_described(exc), issue, head, config, merging=merging)
        raise _Stop(*failed) from exc


def _done_work_failed(
    failure: str, issue: int, head: _Head | None, config: dict[str, Any], *, merging: bool
) -> tuple[int, str]:
    """The code and the line for a done-work run that raised: what happened to
    the PR is read from GitHub — when the run was one that could merge it.
    One reading that does not find it merged says what it found, never that
    it did not merge: a request done-work sent before it raised may still
    show, and the re-run reads the PR first."""
    if head is None:
        return EXIT_RETRY, (
            f"merge: stopped — done-work failed ({failure}) completing #{issue}'s merged PR. "
            f"Run `land-work {issue}` again to complete it"
        )
    number = head.pr_number
    if not merging:
        return EXIT_RETRY, (
            f"merge: not merged — done-work failed ({failure}). Run `land-work {issue}` again"
        )
    reading = _read_pr(number, config)
    if reading.problem:
        return EXIT_ACCEPTED, (
            f"merge: unconfirmed — done-work failed ({failure}), and whether PR #{number} "
            f"merged could not be read: {reading.problem}. Run `land-work {issue}` again once "
            "GitHub answers"
        )
    if reading.state == "MERGED":
        return EXIT_RETRY, (
            f"merge: merged{_as_commit(number, config)}, but done-work failed after the merge "
            f"({failure}). Run `land-work {issue}` again to complete #{issue}"
        )
    state = reading.state.lower() or "of no reported state"
    return EXIT_RETRY, (
        f"merge: not seen merged — done-work failed ({failure}), and one reading since finds "
        f"PR #{number} {state}. Run `land-work {issue}` again: it reads the PR first, and "
        "completes it if it has merged"
    )


def _judged(
    end: Any, head: _Head | None, args: argparse.Namespace, config: dict[str, Any]
) -> tuple[int, str]:
    """The exit code and the line for how done-work's run ended."""
    issue = args.issue_number
    kind, reason = end.kind, end.reason
    again = f"run `land-work {issue}` again"
    if head is None:
        if kind == done_work.MERGED:
            return EXIT_MERGED, f"merge: #{issue} completed through its merged PR"
        if kind == done_work.FOLLOW_UP_OWED:
            return EXIT_RETRY, (
                f"merge: #{issue}'s PR has merged, but a step after the merge failed: "
                f"{reason} — {again} to complete it"
            )
        if kind == done_work.DECLINED:
            return EXIT_READY, f"merge: declined — #{issue}'s merged PR was not completed"
        if kind == done_work.REFUSED and end.retry:
            return EXIT_RETRY, (
                f"merge: not completed — {reason} Run `land-work {issue}` again to check, "
                "review and land it"
            )
        if kind == done_work.UNREADABLE:
            return EXIT_UNREADABLE, f"merge: stopped — {reason}"
        return EXIT_NEEDS_CHANGE, f"merge: refused — {reason}"
    number = head.pr_number
    if kind == done_work.MERGED:
        return EXIT_MERGED, f"merge: merged{_as_commit(number, config)}"
    if kind == done_work.FOLLOW_UP_OWED:
        return EXIT_RETRY, (
            f"merge: merged{_as_commit(number, config)}, but a step after the merge failed: "
            f"{reason} — {again} to complete #{issue}"
        )
    if kind in (done_work.QUEUED, done_work.UNCONFIRMED):
        return _accepted(head, queued=kind == done_work.QUEUED, config=config)
    if kind == done_work.DECLINED:
        return EXIT_READY, (
            f"merge: declined — PR #{number} at {short_sha(head.oid)} was not merged"
        )
    if kind == done_work.HEAD_MOVED:
        return EXIT_HEAD_MOVED, f"merge: stopped — {reason}"
    if kind == done_work.UNREADABLE:
        return EXIT_UNREADABLE, f"merge: stopped — {reason}"
    if kind == done_work.REFUSED and end.retry and not args.dry_run:
        return _request_failed(head, reason, config)
    if kind == done_work.REFUSED and end.retry:
        return EXIT_RETRY, f"merge: not merged — {reason}; {again}"
    return EXIT_NEEDS_CHANGE, f"merge: refused — {reason}"


def _request_failed(head: _Head, reason: str, config: dict[str, Any]) -> tuple[int, str]:
    """done-work merged nothing, and a re-run may help: what GitHub reports of
    the PR now says which — a head that moved, a conflict, a head behind a base
    the host merges only a branch up to date with, a merge meanwhile. A head behind
    a base that merges through a queue names no merge, as at the `ci` step: the queue
    builds the merge with the base itself (DEC-064 point 2)."""
    issue, number = head.issue, head.pr_number
    again = f"run `land-work {issue}` again"
    now = _read_pr(number, config)
    if now.problem:
        return EXIT_RETRY, f"merge: not merged — {reason}; {again}"
    if now.state == "MERGED":
        return EXIT_RETRY, (
            f"merge: merged meanwhile{_as_commit(number, config)}, though done-work reports "
            f"{reason} — {again} to complete #{issue}"
        )
    if now.head and now.head != head.oid:
        return EXIT_HEAD_MOVED, (
            f"merge: stopped — PR #{number}'s head moved from {short_sha(head.oid)} to "
            f"{short_sha(now.head)} before the merge. Nothing was merged; `land-work {issue}` "
            "checks and reviews the new head"
        )
    if now.conflicting:
        return EXIT_NEEDS_CHANGE, _conflict_line("merge", head)
    if now.behind and _queued_base(number, config) is not True:
        return EXIT_NEEDS_CHANGE, _behind_line("merge", head)
    return EXIT_RETRY, f"merge: not merged — {reason}; {again}"


def _accepted(head: _Head, *, queued: bool, config: dict[str, Any]) -> tuple[int, str]:
    """done-work's queued or unconfirmed end, said as GitHub now reports the PR.

    A queued PR read neither merged nor queued left the queue: not merged. An
    unconfirmed one read so stays unconfirmed — its request may still show,
    and one reading never says it was not made."""
    issue, number = head.issue, head.pr_number
    again = f"run `land-work {issue}` again once it merges"
    try:
        reading: merge_queue.Reading | None = merge_queue.read(number, config)
    except merge_queue.Unreadable:
        reading = None
    if reading is None:
        if queued:
            return EXIT_ACCEPTED, (
                f"merge: queued, as done-work reports — PR #{number} could not be read again; "
                f"{again}"
            )
        return EXIT_ACCEPTED, (
            f"merge: unconfirmed — whether PR #{number} merged is not known; {again}"
        )
    if reading.merged:
        return EXIT_RETRY, (
            f"merge: merged meanwhile — run `land-work {issue}` again to complete #{issue}"
        )
    if reading.queued:
        return EXIT_ACCEPTED, f"merge: queued — PR #{number} {reading.describe()}; {again}"
    if not queued:
        # An unconfirmed merge or enqueue may still show: one reading of neither
        # does not say it was not made (ADR-061 point 7), so it stays unconfirmed.
        return EXIT_ACCEPTED, (
            f"merge: unconfirmed — PR #{number} reads neither merged nor queued "
            f"({reading.describe()}), which does not tell whether the request was made; read "
            f"it with `pkit pull-request read {number}`, and run `land-work {issue}` again: "
            "it merges the PR if it has not merged"
        )
    return EXIT_RETRY, (
        f"merge: not merged — PR #{number} is neither merged nor in the merge queue "
        f"({reading.describe()}); run `land-work {issue}` again to merge it"
    )


def _as_commit(pr_number: int, config: dict[str, Any]) -> str:
    """` as <merge commit>` — for a PR GitHub reports merged — or "" when the
    merge commit cannot be read."""
    try:
        proc = gh_run(
            ["gh", "pr", "view", str(pr_number), "--json", "mergeCommit"], config, check=False
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return ""
    commit = data.get("mergeCommit") if isinstance(data, dict) else None
    oid = str(commit.get("oid") or "") if isinstance(commit, dict) else ""
    return f" as {short_sha(oid)}" if oid else ""


# ---- composing the verbs ---------------------------------------------------


def _passed_through(args: argparse.Namespace, *, review: bool) -> list[str]:
    """The flags a composed verb is handed: review-pr takes the dry run and
    the root; done-work also takes `--yes` and the wait for a queue."""
    argv: list[str] = []
    if args.dry_run:
        argv.append("--dry-run")
    if args.capability_root is not None:
        argv += ["--capability-root", str(args.capability_root)]
    if args.allow_foreign_repo:
        argv.append("--allow-foreign-repo")
    if review:
        return argv
    if args.yes:
        argv.append("--yes")
    if args.no_wait:
        argv.append("--no-wait")
    elif args.wait_minutes is not None:
        argv += ["--wait-minutes", f"{args.wait_minutes:g}"]
    return argv


def _described(exc: BaseException) -> str:
    """An exception a composed verb raised, in a few words."""
    if isinstance(exc, SystemExit):
        return f"it exited {exc.code}"
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def _say(line: str) -> None:
    sys.stderr.flush()
    print(line, flush=True)


def _end(line: str) -> None:
    """The run's last line, whatever the outcome, with the count of the fixers'
    proposals that wait for the person just before it (DEC-056 point 6)."""
    waiting = _waiting()
    if waiting:
        _say(waiting)
    _say(line)


def _waiting() -> str | None:
    """The line counting the fixers' proposals that wait for the person, or None
    where nothing waits or there is no queue: a repository with no main working
    tree keeps none. A queue that cannot be read gives a `warn:` line, and changes
    nothing else."""
    try:
        queue = drift_queue.folder()
        if not isinstance(queue, Path):
            return None
        index = drift_queue.read_index(queue)
    except (drift_queue.Unreadable, OSError) as exc:
        return (
            f"warn: the fixers' queue cannot be read, so whether proposals wait is not known: {exc}"
        )
    return drift_queue.count_line(drift_queue.waiting(index), queue)


if __name__ == "__main__":
    sys.exit(main())
