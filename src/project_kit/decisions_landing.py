"""What a change lands, and the proposals a state holds (COR-066 points 2 to 4; ADR-081).

`pkit decisions check-landing` runs it. This module is the one home of the comparison
(ADR-057 point 2): every reader in the binary calls it, and a component reads its
answer through the check's document.

**What it judges** is git's merge of the head into the base's tip, the *landing state*
(`landing_tree`). Each record and rule there is compared with its state at the tip, so
one the merge leaves as the tip holds it lands nothing. It reports each proposed there
and not at the tip, and lists each accepted there and not at the tip.

**Everything else is read at the base's tip,** which the change cannot move: the
refusal's key, the default branch's name, and, with the landing state, which files the
project receives and where the ADR folder is. Only a landing on the default branch is
refused, told by the name the run gave its base (`default_branch.branch_named`). A
doubt counts as the default branch: a name that is no branch's, or a declared name
that does not read.

**Which files the project receives** is asked of the working tree's copy of the
synced-copy test, once per state, against a *stand-in root* holding the test's three
inputs at that state (`_stand_in`). A file either reading skips is skipped, and a file
the two disagree on is reported. A state that cannot tell skips nothing, and says why.

**What it cannot read counts as proposed,** with why: a file that is not text, front
matter that does not parse, a status its kind does not have. A rule-set file the reader
cannot read counts as one proposal, and so does one with no mapping of rules, or with a
key written twice, whose reading is in doubt. So does an overlay at the landing state
that does not give the ADR folder, whatever the tip's does: an ADR behind it may be new.

**It gives no answer** (`NoAnswer`) only where it cannot compute what lands: no base is
named, a name is no commit or reads as one it does not name, the head and the base share
no history, the clone is shallow, the merge conflicts, git cannot compute a merge, any
other git command fails, or the synced-copy test cannot run. No answer is never an empty
list and never the refusal off, and it exits apart from a refusal (`NO_ANSWER_EXIT`).

**The list** (`_Walk`) reads each of the change's commits against the state before it
(`commit_contributions`), and shows only what lands.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Collection, Generator, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from project_kit import cli_render, default_branch, lifecycle_ownership
from project_kit import commit_contributions as contributions
from project_kit import decisions_check_diff as numbering
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.backbone_schemas import CONTAINER_KEY
from project_kit.config_at_commit import KeyAtCommit, key_at
from project_kit.decisions import OVERLAY_RELPATH
from project_kit.decisions_validate import record_space
from project_kit.friction_check import printable
from project_kit.friction_git import SHORT, CommitTree, FrictionCheckError, run_git
from project_kit.project_config import REFUSE_PROPOSALS_KEY
from project_kit.validate import VALID_DECISION_STATUSES

#: The version of the JSON document (`document`): raised when a key a reader relies on
#: changes its meaning or goes, never for a key added (ADR-081 point 8).
SCHEMA_VERSION = 1

#: The exit of a run that gives no answer, apart from a refusal's 1 and a usage error's 2.
NO_ANSWER_EXIT = 3

#: The kinds of thing the check reports.
RECORD = "record"
RULE = "rule"
RULE_SET_FILE = "rule-set-file"

#: The three inputs of the synced-copy test, kept by hand (ADR-081 point 3). A test holds
#: them to what the test reads.
MANIFEST_INPUT = ".pkit/manifest.yaml"
SOURCE_FILE_INPUT = "src/project_kit/__init__.py"
SOURCE_TREE_INPUT = ".pkit"

_MARKDOWN = ".md"


class NoAnswer(Exception):
    """The check cannot compute what lands, and `problem` says why (ADR-081 point 6)."""

    def __init__(self, problem: str) -> None:
        super().__init__(problem)
        self.problem = problem


# --- what the check gives --------------------------------------------------------------


@dataclass(frozen=True)
class Proposal:
    """A record, rule or rule-set file proposed at a state. `was` is its status at the
    state compared with, `None` where that holds none, and `why` what could not be read
    of it, where it counts as proposed for that."""

    kind: str
    name: str
    path: str
    was: str | None = None
    why: str | None = None

    def said(self) -> str:
        """How the line of the human view says it."""
        if self.why is not None:
            return f"counts as proposed: {self.why}"
        return "added proposed" if self.was is None else f"set back from {self.was}"


@dataclass(frozen=True)
class Work:
    """One commit's work, of which `paths` lands. A commit left with nothing to show stays
    listed, and says so (`nothing_lands`)."""

    commit: str
    subject: str
    paths: tuple[str, ...] = ()

    @property
    def nothing_lands(self) -> bool:
        return not self.paths


@dataclass(frozen=True)
class RuleEdits:
    """How a rule's content differs between two states: its fields by name, whether its
    section's text changed, and whether the later state holds it at all."""

    fields: tuple[str, ...] = ()
    text: bool = False
    removed: bool = False

    def said(self) -> str:
        if self.removed:
            return "removed"
        parts = [f"its {', '.join(self.fields)} altered"] if self.fields else []
        return ", ".join([*parts, *(["its text altered"] if self.text else [])])


#: What differs in a record or rule between two states: a record point by point, as the
#: numbering check reads an accepted record's, a rule as its content.
Edits = numbering.ChangedRecord | RuleEdits


@dataclass(frozen=True)
class Acceptance:
    """One commit that accepted a record or rule, with the rest of what it contributes,
    the change's commits before it that touch anything else, and the edits since."""

    commit: Work
    before: tuple[Work, ...] = ()
    edits: Edits | None = None


@dataclass(frozen=True)
class Accepted:
    """A record or rule the change makes accepted, with each commit that accepted it."""

    kind: str
    name: str
    path: str
    was: str | None
    acceptances: tuple[Acceptance, ...] = ()


@dataclass(frozen=True)
class AcceptedOnBase:
    """A record or rule the base accepted since the branch left it, which the merge
    changes, and how it differs at the landing state from the tip."""

    kind: str
    name: str
    path: str
    edits: Edits


@dataclass(frozen=True)
class Landing:
    """What the check found.

    - `named`: the base as the run named it, and `base` as it resolved.
    - `is_default`: the base counts as the default branch (`declared_branch` is the name
      the tip declares).
    - `key` and `key_at_landing`: the refusal's key at the two states.
    - `proposals`, `accepted` and `accepted_on_base`: what the comparison found.
    - `disagreements`: each file the two readings of what the project receives disagree
      on, and `cannot_tell` why a state could not tell.
    - `standing`: the tip's proposals, on the run whose landing turns the key on."""

    named: str
    base: default_branch.Base
    head: str
    landing_tree: str
    declared_branch: KeyAtCommit
    is_default: bool
    key: KeyAtCommit
    key_at_landing: KeyAtCommit
    proposals: tuple[Proposal, ...] = ()
    accepted: tuple[Accepted, ...] = ()
    accepted_on_base: tuple[AcceptedOnBase, ...] = ()
    disagreements: tuple[str, ...] = ()
    cannot_tell: tuple[str, ...] = ()
    standing: tuple[Proposal, ...] = ()

    @property
    def refusal_on(self) -> bool:
        """Whether a reported proposal fails this landing (ADR-081 point 5)."""
        return self.is_default and self.key.value is True

    @property
    def refuses(self) -> bool:
        return self.refusal_on and bool(self.proposals)

    @property
    def key_changes(self) -> bool:
        return self.key.value != self.key_at_landing.value

    @property
    def warnings(self) -> tuple[str, ...]:
        """What the run prints on standard error."""
        said = (self.base.warning, self.key.warning, self.declared_branch.warning)
        return tuple(warning for warning in said if warning is not None)


# --- a state ---------------------------------------------------------------------------


@contextmanager
def _test_may_raise() -> Generator[None]:
    """Where the working tree's copy of the synced-copy test runs, directly or in discovery's
    walk: it is code the tree holds, so it may raise anything, and that gives no answer."""
    try:
        yield
    except (FrictionCheckError, NoAnswer):
        raise
    except Exception as exc:
        raise NoAnswer(f"the synced-copy test cannot run: it raised {exc!r}.") from exc


@dataclass(frozen=True)
class _State:
    """What one state holds of records and rules."""

    tree: CommitTree
    read: numbering.RecordsRead
    discovery: fd.Discovery
    rule_sets: rs.RuleSetDiscovery
    rule_files: frozenset[str]

    @cached_property
    def rules(self) -> dict[str, rs.Rule]:
        """Every rule, by location."""
        return {rule.location: rule for rule in self.rule_sets.rules}

    @cached_property
    def unread_rule_files(self) -> dict[str, str]:
        """Each rule-set file the reader could not read, with why. A link is claimed and
        never read, so it is one of them, and so is a file whose rules are in doubt."""
        found = {unread.path: f"the file {unread.problem}" for unread in self.rule_sets.unreadable}
        read = {rule_set.path for rule_set in self.rule_sets.rule_sets}
        for rel in self.rule_files - read - found.keys():
            found[rel] = "the file is a link, which the reader never reads"
        for rule_set in self.rule_sets.rule_sets:
            why = _rules_in_doubt(rule_set)
            if why is not None:
                found[rule_set.path] = why
        return found

    @property
    def paths(self) -> frozenset[str]:
        """Every record and rule-set file the state holds."""
        return frozenset({*self.read.records, *self.read.unreadable, *self.rule_files})


def _rules_in_doubt(rule_set: rs.RuleSet) -> str | None:
    """Why a file the reader read gives no sure reading of its rules: it holds no mapping
    of them, so the reader finds none, or it writes a key twice, so one value goes unread."""
    if not isinstance(rule_set.front_matter.get(fd.RULES_KEY), Mapping):
        return f"the file holds no mapping of `{fd.RULES_KEY}`"
    if rule_set.duplicate_keys:
        return f"the file writes {rule_set.duplicate_keys[0].key!r} twice, and reads the first"
    return None


def _read_state(root: Path, tree: CommitTree, adrs: Sequence[str | None]) -> _State:
    """The records and rules of the state `tree` holds. Discovery runs the working tree's
    copy of the synced-copy test, so what it raises there gives no answer."""
    read = numbering.read_records(tree, *adrs)
    with _test_may_raise():
        settings = fd.read_friction_settings(root, tree)
        rule_sets = rs.discover_rule_sets(root, settings, tree)
        discovery = fd.discover_artefacts(root, settings, tree)
        rule_files = frozenset(fd.rule_set_files(root, rule_sets.places, tree))
    return _State(tree, read, discovery, rule_sets, rule_files)


def _overlay_proposal(unread: str | None, was: str | None = None) -> tuple[Proposal, ...]:
    """The overlay as one proposal, where a state's does not give the ADR folder. Unlike a
    file unread at both states, it counts whatever the tip's does: what it hides may be new."""
    if unread is None:
        return ()
    why = f"the overlay {unread}, so an ADR may go unread"
    return (Proposal(RECORD, OVERLAY_RELPATH, OVERLAY_RELPATH, was, why),)


# --- which files the project receives --------------------------------------------------


@dataclass(frozen=True)
class _Received:
    """What the synced-copy test skips, one set per state asked, and why a state could
    not tell."""

    skipped: tuple[frozenset[str], ...]
    cannot_tell: tuple[str, ...] = ()


def _received(
    root: Path, states: Sequence[tuple[str, CommitTree]], paths: Collection[str]
) -> _Received:
    """Which of `paths` each named state says the project receives, each asked through a
    stand-in root of its own (ADR-081 point 3)."""
    with _test_may_raise():
        ownership = lifecycle_ownership.load_ownership(root)
    if ownership is None:
        said = "this tree holds no synced-copy test, so no file is skipped"
        return _Received(tuple(frozenset[str]() for _state in states), (said,))
    skipped: list[frozenset[str]] = []
    cannot_tell: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="pkit-landing-") as folder, _test_may_raise():
            for index, (name, tree) in enumerate(states):
                stand_in = Path(folder) / str(index)
                try:
                    stand_in.mkdir()
                    cannot_tell += _stand_in(root, stand_in, tree, ownership, name)
                except OSError as exc:
                    raise NoAnswer(f"no stand-in root can be made: {exc}.") from exc
                skipped.append(
                    frozenset(rel for rel in paths if ownership.is_synced_copy(stand_in, rel))
                )
    except OSError as exc:
        raise NoAnswer(f"no stand-in root can be made: {exc}.") from exc
    return _Received(tuple(skipped), tuple(cannot_tell))


def _stand_in(
    root: Path, stand_in: Path, tree: CommitTree, ownership: ModuleType, name: str
) -> list[str]:
    """Write the test's three inputs at a state into `stand_in`, and say why the state
    cannot tell. A manifest that does not read is left out: the test reads such a manifest
    as every capability shipped, which would skip the project's own records."""
    files = frozenset(tree.files())
    if SOURCE_FILE_INPUT in files:
        marker = stand_in / SOURCE_FILE_INPUT
        marker.parent.mkdir(parents=True)
        marker.touch()
    if any(rel.startswith(f"{SOURCE_TREE_INPUT}/") for rel in files):
        (stand_in / SOURCE_TREE_INPUT).mkdir()
    raw = tree.read_bytes([MANIFEST_INPUT]).get(MANIFEST_INPUT)
    if raw is None:
        return []
    manifest, unread = fd.read_mapping_at(root, tree, MANIFEST_INPUT)
    components: Any = manifest.get("components") or []
    if unread is None and not isinstance(components, list):
        unread = "lists its components in no list"
    if unread is not None:
        return [f"{name}: {MANIFEST_INPUT} {unread}, so that state skips no capability's file"]
    (stand_in / MANIFEST_INPUT).parent.mkdir(exist_ok=True)
    (stand_in / MANIFEST_INPUT).write_bytes(raw)
    return _unknown_origins(cast(list[Any], components), ownership, name)


def _unknown_origins(components: list[Any], ownership: ModuleType, name: str) -> list[str]:
    """Why a capability's files are not skipped: the manifest records an origin the test
    does not know. A sync mends it."""
    known = {
        value
        for constant, value in vars(ownership).items()
        if constant.startswith("ORIGIN_") and isinstance(value, str)
    }
    entries = [cast(Mapping[str, Any], e) for e in components if isinstance(e, Mapping)]
    return [
        f"{name}: the manifest records capability {entry.get('name')!r} with the origin "
        f"{entry['origin']!r}, which the test does not know, so no file of it is skipped"
        for entry in entries
        if entry.get("kind") == "capability"
        and "origin" in entry
        and str(entry["origin"]) not in known
    ]


# --- a record's and a rule's status ----------------------------------------------------


def _record_status(record: numbering.Record) -> tuple[str, str | None]:
    """A record's status, and why it counts as proposed where it cannot be read."""
    points = record.points
    if points.front_matter_problem is not None:
        return rs.PROPOSED, f"its front matter does not read: {points.front_matter_problem}"
    status = points.front_matter.get("status")
    if isinstance(status, str) and status in VALID_DECISION_STATUSES:
        return status, None
    if status is None:
        return rs.PROPOSED, "it writes no status"
    return rs.PROPOSED, f"its status {status!r} is not one a record has"


def _rule_status(rule: rs.Rule) -> tuple[str, str | None]:
    """A rule's status, and why it counts as proposed where it writes none it can have. A
    rule with no status is proposed (COR-051 point 4)."""
    status = rule.data.get("status")
    if isinstance(status, str) and status in rs.STATUSES:
        return status, None
    if status is None:
        return rs.PROPOSED, "it writes no status"
    return rs.PROPOSED, f"its status {status!r} is not one a rule has"


def _folded(text: str) -> str:
    return " ".join(text.split())


def _rule_edits(after: rs.Rule | None, before: rs.Rule) -> RuleEdits | None:
    """How a rule's content differs from `before` to `after`, the container never counted
    (COR-050 point 5), or `None` where it reads the same."""
    if after is None:
        return RuleEdits(removed=True)
    keys = sorted((after.data.keys() | before.data.keys()) - {CONTAINER_KEY})
    fields = tuple(key for key in keys if after.data.get(key) != before.data.get(key))
    text = _folded(after.section) != _folded(before.section)
    return RuleEdits(fields, text) if fields or text else None


# --- the comparison --------------------------------------------------------------------


@dataclass(frozen=True)
class _Judged:
    """One record or rule at the landing state, with its state at the tip."""

    kind: str
    name: str
    path: str
    status: str
    was: str | None
    why: str | None = None
    record: numbering.Record | None = None
    rule: rs.Rule | None = None


def _judged_records(landing: _State, tip: _State, skip: frozenset[str]) -> Iterator[_Judged]:
    """Each record of the landing state the project does not receive, paired as the
    numbering check pairs it. What cannot be read of it counts as proposed."""
    pairs = numbering.pair_records(landing.read.records, tip.read.records)
    for rel, record in sorted(landing.read.records.items()):
        before = pairs.get(rel)
        if rel in skip or (before is not None and before.rel in skip):
            continue
        status, why = _record_status(record)
        was = (
            _record_status(before)[0]
            if before is not None
            else (rs.PROPOSED if rel in tip.read.unreadable else None)
        )
        yield _Judged(RECORD, record.name, rel, status, was, why, record=record)
    for rel, why in sorted(landing.read.unreadable.items()):
        if rel in skip:
            continue
        held = tip.read.records.get(rel)
        was = _record_status(held)[0] if held is not None else None
        yield _Judged(
            RECORD,
            rel,
            rel,
            rs.PROPOSED,
            rs.PROPOSED if rel in tip.read.unreadable else was,
            why,
        )


def _rule_pairs(pairing: fc.Pairing, earlier: _State) -> dict[str, rs.Rule | None]:
    """For each rule the walk found at the later state, its rule at the earlier state, by
    the change check's pairing of artefacts. An entry that is no mapping makes no artefact,
    so it is read at its own location (`_paired`)."""
    paired: dict[str, rs.Rule | None] = {}
    for index, artefact in enumerate(pairing.head):
        if artefact.rule_set is not None:
            before = pairing.counterparts.get(index)
            if before is None or before.rule_set is None:
                paired[artefact.location] = None
            else:
                paired[artefact.location] = earlier.rules.get(before.location)
    return paired


def _paired(pairs: Mapping[str, rs.Rule | None], location: str, other: _State) -> rs.Rule | None:
    """The rule `pairs` gives for a location, else the other state's at that location."""
    return pairs[location] if location in pairs else other.rules.get(location)


def _judged_rules(
    landing: _State, tip: _State, skip: frozenset[str], pairing: fc.Pairing
) -> Iterator[_Judged]:
    """Each rule of the landing state the project does not receive, judged on its own, and
    each rule-set file the reader cannot read, as one proposal."""
    paired = _rule_pairs(pairing, tip)
    for location, rule in landing.rules.items():
        before = _paired(paired, location, tip)
        if rule.path in skip or (before is not None and before.path in skip):
            continue
        status, why = _rule_status(rule)
        was = _rule_status(before)[0] if before is not None else None
        yield _Judged(RULE, rule.id, rule.path, status, was, why, rule=rule)
    for rel, why in sorted(landing.unread_rule_files.items()):
        if rel not in skip:
            was = rs.PROPOSED if rel in tip.unread_rule_files else None
            yield _Judged(RULE_SET_FILE, rel, rel, rs.PROPOSED, was, why)


def _pairing(root: Path, earlier: _State, later: _State) -> fc.Pairing:
    """The change check's pairing of the artefacts of two states."""
    diff = fc.read_diff(root, earlier.tree.commit, fc.HeadState(later.tree.commit, 0))
    return fc.pair_artefacts(earlier.discovery, later.discovery, diff)


def _accepted_on_base(
    root: Path,
    fork: _State,
    tip: _State,
    landing: _State,
    skip: frozenset[str],
    landing_rules: Mapping[str, rs.Rule | None],
) -> Iterator[AcceptedOnBase]:
    """Each record and rule the tip holds accepted and the branch point does not, which
    the merge changes."""
    at_fork = numbering.pair_records(tip.read.records, fork.read.records)
    at_landing = numbering.pair_records(tip.read.records, landing.read.records)
    for rel, record in sorted(tip.read.records.items()):
        if rel in skip or _record_status(record)[0] != rs.ACCEPTED:
            continue
        before = at_fork.get(rel)
        if before is not None and _record_status(before)[0] == rs.ACCEPTED:
            continue
        after = at_landing.get(rel)
        edits = (
            numbering.ChangedRecord(rel, record.name, removed=True)
            if after is None
            else numbering.accepted_change(after, record)
        )
        if edits is not None:
            yield AcceptedOnBase(RECORD, record.name, rel, edits)
    earlier = _rule_pairs(_pairing(root, fork, tip), fork)
    for location, rule in tip.rules.items():
        if rule.path in skip or _rule_status(rule)[0] != rs.ACCEPTED:
            continue
        before = _paired(earlier, location, fork)
        if before is not None and _rule_status(before)[0] == rs.ACCEPTED:
            continue
        rule_edits = _rule_edits(_paired(landing_rules, location, landing), rule)
        if rule_edits is not None:
            yield AcceptedOnBase(RULE, rule.id, rule.path, rule_edits)


# --- the list: each acceptance with the work around it ---------------------------------


@dataclass(frozen=True)
class _Step:
    """One commit of the change, with the state before it and what it contributes."""

    commit: contributions.ChangeCommit
    prior: contributions.PriorState
    touched: frozenset[str]


def _rest_of(rule_set: rs.RuleSet | None, rule_id: str) -> tuple[Any, str] | None:
    """A rule-set file without one rule's own content: what an edit to it leaves alone."""
    if rule_set is None:
        return None
    entries = rule_set.front_matter.get(fd.RULES_KEY)
    others = (
        {key: value for key, value in cast(Mapping[str, Any], entries).items() if key != rule_id}
        if isinstance(entries, Mapping)
        else entries
    )
    rule = rule_set.rule(rule_id)
    body = rule_set.body
    if rule is not None and rule.section:
        body = body.replace(rule.section, "", 1)
    return {**rule_set.front_matter, fd.RULES_KEY: others}, _folded(body)


class _Walk:
    """The change's commits, each read against the state before it (ADR-081 point 4).

    In a walk of what the head reaches and the tip does not, every parent lies among the
    commits walked or in the tip's history, so a merge is always read against git's merge
    of its parents."""

    def __init__(
        self, root: Path, tip: str, head: str, adrs: Sequence[str | None], landed: frozenset[str]
    ) -> None:
        self._root = root
        self._adrs = adrs
        self._landed = landed
        self._trees: dict[str, CommitTree] = {}
        self._rule_sets: dict[str, dict[str, rs.RuleSet]] = {}
        self.commits = contributions.change_commits(root, tip, head)
        self.steps = tuple(self._step(commit) for commit in self.commits)

    def _step(self, commit: contributions.ChangeCommit) -> _Step:
        prior = contributions.prior_state(self._root, commit.parents, settled=lambda _parent: True)
        return _Step(commit, prior, contributions.contributed(self._root, prior, commit.commit))

    def _tree(self, state: str) -> CommitTree:
        if state not in self._trees:
            self._trees[state] = CommitTree(self._root, state)
        return self._trees[state]

    # What a state holds of one record.

    def _records_in(self, state: str, paths: frozenset[str]) -> dict[str, numbering.Record]:
        return numbering.read_records(self._tree(state), *self._adrs, only=paths).records

    def _record_at(
        self, record: numbering.Record, state: str, step: _Step
    ) -> numbering.Record | None:
        """The record at a state, among the files the step touches: no other file of it can
        tell the step from the state before it."""
        held = self._records_in(state, step.touched)
        return numbering.pair_records({record.rel: record}, held).get(record.rel)

    def _touches_records(self, step: _Step) -> bool:
        return any(record_space(rel, adr) for rel in step.touched for adr in self._adrs)

    # What a state holds of one rule.

    def _sets_at(self, state: str) -> dict[str, rs.RuleSet]:
        """Every rule set of a state, by path."""
        if state not in self._rule_sets:
            with _test_may_raise():
                found = rs.discover_rule_sets(self._root, tree=self._tree(state))
            self._rule_sets[state] = {rule_set.path: rule_set for rule_set in found.rule_sets}
        return self._rule_sets[state]

    def _rule_at(self, rule_id: str, state: str) -> rs.Rule | None:
        for rule_set in self._sets_at(state).values():
            rule = rule_set.rule(rule_id)
            if rule is not None:
                return rule
        return None

    def _mentions(self, step: _Step, rule_id: str) -> bool:
        """Whether a file the step touches names the rule at the commit or before it, so a
        step that leaves it alone costs no reading of the rule sets."""
        paths = sorted(rel for rel in step.touched if rel.endswith(_MARKDOWN))
        needle = rule_id.encode()
        return any(
            raw is not None and needle in raw
            for state in (step.commit.commit, *step.prior.states)
            for raw in self._tree(state).read_bytes(paths).values()
        )

    def _rule_around(
        self, rule_id: str, step: _Step
    ) -> tuple[rs.Rule | None, tuple[rs.Rule | None, ...]]:
        if not self._mentions(step, rule_id):
            return None, ()
        after = self._rule_at(rule_id, step.commit.commit)
        return after, tuple(self._rule_at(rule_id, state) for state in step.prior.states)

    def _only_its_own(self, rule_id: str, path: str, step: _Step) -> bool:
        """Whether the step changes a rule-set file only in the rule's own content."""
        rest = _rest_of(self._sets_at(step.commit.commit).get(path), rule_id)
        return all(
            _rest_of(self._sets_at(state).get(path), rule_id) == rest for state in step.prior.states
        )

    # What a step does beside one record or rule.

    def _record_elsewhere(self, record: numbering.Record, step: _Step) -> frozenset[str]:
        """What the step touches besides the record's own file, at either side of a move."""
        if not self._touches_records(step):
            return step.touched
        states = (step.commit.commit, *step.prior.states)
        held = (self._record_at(record, state, step) for state in states)
        return step.touched - {found.rel for found in held if found is not None}

    def _rule_elsewhere(self, rule_id: str, step: _Step) -> frozenset[str]:
        """What the step touches besides the rule's own content, so an edit to another rule
        in its file counts."""
        after, befores = self._rule_around(rule_id, step)
        own = {rule.path for rule in (after, *befores) if rule is not None}
        return step.touched - {
            path for path in own & step.touched if self._only_its_own(rule_id, path, step)
        }

    def _work(self, step: _Step, paths: frozenset[str]) -> Work:
        """A step's work, as much of it as lands."""
        commit = step.commit
        return Work(commit.commit, commit.subject, tuple(sorted(paths & self._landed)))

    # The list.

    def _before(
        self, accepting: _Step, elsewhere: Callable[[_Step], frozenset[str]]
    ) -> tuple[Work, ...]:
        """The change's commits before `accepting` that touch anything else. A commit on a
        parallel line counts as before, so only what descends from it is left out."""
        later = contributions.descendants(self.commits, accepting.commit.commit)
        found: list[Work] = []
        for step in self.steps:
            if step is accepting or step.commit.commit in later:
                continue
            paths = elsewhere(step)
            if paths:
                found.append(self._work(step, paths))
        return tuple(found)

    def record_acceptances(self, record: numbering.Record) -> tuple[Acceptance, ...]:
        """Each commit that holds the record accepted where the state before it does not."""
        found: list[Acceptance] = []

        def elsewhere(step: _Step) -> frozenset[str]:
            return self._record_elsewhere(record, step)

        for step in self.steps:
            if not self._touches_records(step):
                continue
            after = self._record_at(record, step.commit.commit, step)
            if after is None or _record_status(after)[0] != rs.ACCEPTED:
                continue
            befores = (self._record_at(record, state, step) for state in step.prior.states)
            if any(b is not None and _record_status(b)[0] == rs.ACCEPTED for b in befores):
                continue
            found.append(
                Acceptance(
                    self._work(step, elsewhere(step)),
                    self._before(step, elsewhere),
                    numbering.accepted_change(record, after),
                )
            )
        return tuple(found)

    def rule_acceptances(self, rule: rs.Rule) -> tuple[Acceptance, ...]:
        """Each commit that holds the rule accepted where the state before it does not."""
        found: list[Acceptance] = []

        def elsewhere(step: _Step) -> frozenset[str]:
            return self._rule_elsewhere(rule.id, step)

        for step in self.steps:
            after, befores = self._rule_around(rule.id, step)
            if after is None or _rule_status(after)[0] != rs.ACCEPTED:
                continue
            if any(b is not None and _rule_status(b)[0] == rs.ACCEPTED for b in befores):
                continue
            found.append(
                Acceptance(
                    self._work(step, elsewhere(step)),
                    self._before(step, elsewhere),
                    _rule_edits(rule, after),
                )
            )
        return tuple(found)


# --- the check -------------------------------------------------------------------------


def _landing_tree(root: Path, tip: str, head: str) -> str:
    """The tree git's merge of the head into the tip gives: the head's own where it
    descends from the tip. A conflict gives no answer, and the fix is to merge the base."""
    if contributions.is_ancestor(root, tip, head):
        return run_git(root, "rev-parse", f"{head}^{{tree}}").stdout.decode().strip()
    merged = contributions.merge(root, tip, head)
    if not merged.clean:
        named = ", ".join(merged.conflicted) or "files git does not name"
        raise NoAnswer(
            f"git's merge of {head[:SHORT]} into {tip[:SHORT]} conflicts on {named}: merge the "
            f"base into the change, resolve it, and run again."
        )
    return merged.tree


def _head_and_base(
    root: Path, base_ref: str | None, head_rev: str | None
) -> tuple[str, str, default_branch.Base]:
    """The base as named, the head, and the base as it resolves, or no answer."""
    named = base_ref if base_ref is not None else os.environ.get(default_branch.CHECK_BASE_ENV)
    if base_ref is None and not named:
        raise NoAnswer(
            f"the run names no base, and the check takes none by default: name it with --base "
            f"or ${default_branch.CHECK_BASE_ENV}."
        )
    head = contributions.commit_named(root, head_rev or "HEAD", "--head" if head_rev else "HEAD")
    if run_git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == b"true":
        raise NoAnswer(
            "this clone is shallow, so the change's commits may not all be here; fetch them "
            "(`git fetch --unshallow`) and run again."
        )
    base = default_branch.base(root, base_ref, head_rev=head)
    if base.problem is not None or base.tip is None or base.fork is None:
        raise NoAnswer(base.problem or f"the base {base.ref!r} cannot be compared.")
    return named or "", head, base


def _declared_branch(root: Path, tree: CommitTree) -> KeyAtCommit:
    return key_at(
        root,
        tree,
        default_branch.DOTTED_KEY,
        default=default_branch.DEFAULT_NAME,
        accepts=default_branch.is_branch_name,
        expected="a branch name",
    )


def _refusal_key(root: Path, tree: CommitTree) -> KeyAtCommit:
    def is_boolean(value: Any) -> bool:
        return isinstance(value, bool)

    return key_at(
        root, tree, REFUSE_PROPOSALS_KEY, default=False, accepts=is_boolean, expected="a boolean"
    )


def check(root: Path, base_ref: str | None = None, head_rev: str | None = None) -> Landing:
    """Judge what the head's merge into the base would land. `base_ref` is `--base`, else
    `$PKIT_CHECK_BASE` names the base. Raises `NoAnswer` where it cannot compute that."""
    try:
        return _check(root, base_ref, head_rev)
    except FrictionCheckError as exc:
        raise NoAnswer(exc.message) from exc


def _check(root: Path, base_ref: str | None, head_rev: str | None) -> Landing:
    named, head, base = _head_and_base(root, base_ref, head_rev)
    assert base.tip is not None and base.fork is not None  # `_head_and_base` refuses without
    landing_tree = _landing_tree(root, base.tip, head)
    at_tip, at_landing = CommitTree(root, base.tip), CommitTree(root, landing_tree)
    tip_adrs, _tip_unread = numbering.adr_folder_at(root, at_tip)
    landing_adrs, overlay_unread = numbering.adr_folder_at(root, at_landing)
    adrs = (tip_adrs, landing_adrs)
    tip, landing = _read_state(root, at_tip, adrs), _read_state(root, at_landing, adrs)

    paths = tip.paths | landing.paths
    received = _received(root, (("the tip", at_tip), ("the landing state", at_landing)), paths)
    tip_skips, landing_skips = received.skipped
    skip = tip_skips | landing_skips
    pairing = _pairing(root, tip, landing)
    judged = [
        *_judged_records(landing, tip, skip),
        *_judged_rules(landing, tip, skip, pairing),
    ]
    proposals = (
        *_overlay_proposal(overlay_unread),
        *(
            Proposal(item.kind, item.name, item.path, item.was, item.why)
            for item in judged
            if item.status == rs.PROPOSED and item.was != rs.PROPOSED
        ),
    )
    listed = [item for item in judged if item.status == rs.ACCEPTED and item.was != rs.ACCEPTED]

    declared_branch = _declared_branch(root, at_tip)
    branch = default_branch.branch_named(root, named)
    is_default = (
        branch is None or declared_branch.warning is not None or branch == declared_branch.value
    )
    key, key_at_landing = _refusal_key(root, at_tip), _refusal_key(root, at_landing)
    turned_on = is_default and key.value is not True and key_at_landing.value is True

    return Landing(
        named=named,
        base=base,
        head=head,
        landing_tree=landing_tree,
        declared_branch=declared_branch,
        is_default=is_default,
        key=key,
        key_at_landing=key_at_landing,
        proposals=proposals,
        accepted=_accepted(root, base.tip, head, adrs, listed, tip, landing),
        accepted_on_base=_on_base(root, base, adrs, tip, landing, skip, pairing),
        disagreements=tuple(sorted(tip_skips ^ landing_skips)),
        cannot_tell=received.cannot_tell,
        standing=proposals_at(root, base.tip) if turned_on else (),
    )


def _accepted(
    root: Path,
    tip_commit: str,
    head: str,
    adrs: Sequence[str | None],
    listed: Sequence[_Judged],
    tip: _State,
    landing: _State,
) -> tuple[Accepted, ...]:
    """The list: each listed record and rule, with each commit that accepted it."""
    if not listed:
        return ()
    landed = frozenset(
        path for path, _sides in contributions.raw_diff(root, tip.tree.commit, landing.tree.commit)
    )
    walk = _Walk(root, tip_commit, head, adrs, landed)
    found: list[Accepted] = []
    for item in listed:
        acceptances = (
            walk.record_acceptances(item.record)
            if item.record is not None
            else walk.rule_acceptances(cast(rs.Rule, item.rule))
        )
        found.append(Accepted(item.kind, item.name, item.path, item.was, acceptances))
    return tuple(found)


def _on_base(
    root: Path,
    base: default_branch.Base,
    adrs: Sequence[str | None],
    tip: _State,
    landing: _State,
    skip: frozenset[str],
    pairing: fc.Pairing,
) -> tuple[AcceptedOnBase, ...]:
    """The second list, read only where the base moved on since the branch left it."""
    assert base.fork is not None
    if base.fork == base.tip:
        return ()
    fork = _read_state(root, CommitTree(root, base.fork), adrs)
    after: dict[str, rs.Rule | None] = {}
    for index, artefact in enumerate(pairing.head):
        before = pairing.counterparts.get(index)
        if before is not None and before.rule_set is not None and artefact.rule_set is not None:
            after[before.location] = landing.rules.get(artefact.location)
    return tuple(_accepted_on_base(root, fork, tip, landing, skip, after))


def proposals_at(root: Path, commit: str) -> tuple[Proposal, ...]:
    """The project's own proposals a state holds: each proposed record and rule it does not
    receive, and each it cannot read, which counts as proposed. COR-067's decision-debt
    command finds the default branch's proposals here. Raises `NoAnswer` as `check` does."""
    try:
        return _proposals_at(root, commit)
    except FrictionCheckError as exc:
        raise NoAnswer(exc.message) from exc


def _proposals_at(root: Path, commit: str) -> tuple[Proposal, ...]:
    tree = CommitTree(root, commit)
    adrs, overlay_unread = numbering.adr_folder_at(root, tree)
    state = _read_state(root, tree, (adrs,))
    (skip,) = _received(root, (("the state", tree),), state.paths).skipped
    found = list(_overlay_proposal(overlay_unread, rs.PROPOSED))
    for rel, record in sorted(state.read.records.items()):
        status, why = _record_status(record)
        if rel not in skip and status == rs.PROPOSED:
            found.append(Proposal(RECORD, record.name, rel, rs.PROPOSED, why))
    for rel, why in sorted(state.read.unreadable.items()):
        if rel not in skip:
            found.append(Proposal(RECORD, rel, rel, rs.PROPOSED, why))
    for rule in state.rules.values():
        status, why = _rule_status(rule)
        if rule.path not in skip and status == rs.PROPOSED:
            found.append(Proposal(RULE, rule.id, rule.path, rs.PROPOSED, why))
    for rel, why in sorted(state.unread_rule_files.items()):
        if rel not in skip:
            found.append(Proposal(RULE_SET_FILE, rel, rel, rs.PROPOSED, why))
    return tuple(found)


# --- the document ----------------------------------------------------------------------


def _proposal_entry(proposal: Proposal) -> dict[str, Any]:
    return {
        "kind": proposal.kind,
        "name": proposal.name,
        "path": proposal.path,
        "was": proposal.was,
        "why": proposal.why,
    }


def _work_entry(work: Work) -> dict[str, Any]:
    return {
        "commit": work.commit,
        "subject": work.subject,
        "paths": list(work.paths),
        "nothing_lands": work.nothing_lands,
    }


def _edits_entry(edits: Edits | None) -> dict[str, Any] | None:
    if edits is None:
        return None
    if isinstance(edits, RuleEdits):
        return {"fields": list(edits.fields), "text": edits.text, "removed": edits.removed}
    return numbering.changed_entry(edits)


def _accepted_entry(accepted: Accepted) -> dict[str, Any]:
    return {
        "kind": accepted.kind,
        "name": accepted.name,
        "path": accepted.path,
        "was": accepted.was,
        "commits": [
            {
                **_work_entry(acceptance.commit),
                "before": [_work_entry(work) for work in acceptance.before],
                "edits_since": _edits_entry(acceptance.edits),
            }
            for acceptance in accepted.acceptances
        ],
    }


def document(found: Landing) -> dict[str, Any]:
    """The check's JSON document (ADR-081 point 8)."""
    key = found.key
    return {
        "schema_version": SCHEMA_VERSION,
        "problem": None,
        "base": {
            "named": found.named,
            "source": found.base.source,
            "ref": found.base.ref,
            "tip": found.base.tip,
            "fork": found.base.fork,
        },
        "head": found.head,
        "landing_tree": found.landing_tree,
        "default_branch": {
            "declared": found.declared_branch.value,
            "is_base": found.is_default,
            "warning": found.declared_branch.warning,
        },
        "key": {
            "name": key.key,
            "value": key.value,
            "read_at": key.commit,
            "warning": key.warning,
            "refusal_on": found.refusal_on,
            "change": {"tip": key.value, "landing": found.key_at_landing.value}
            if found.key_changes
            else None,
        },
        "proposals": [_proposal_entry(proposal) for proposal in found.proposals],
        "refuses": found.refuses,
        "accepted": [_accepted_entry(accepted) for accepted in found.accepted],
        "accepted_on_base": [
            {
                "kind": item.kind,
                "name": item.name,
                "path": item.path,
                "edits": _edits_entry(item.edits),
            }
            for item in found.accepted_on_base
        ],
        "received_disagreements": list(found.disagreements),
        "cannot_tell": list(found.cannot_tell),
        "default_branch_proposals": [_proposal_entry(proposal) for proposal in found.standing],
    }


def no_answer_document(problem: str) -> dict[str, Any]:
    """The document of a run with no answer: why, and nothing else (ADR-081 point 8)."""
    return {"schema_version": SCHEMA_VERSION, "problem": problem}


def render_json(found: Mapping[str, Any]) -> str:
    """A document as stable JSON: keys sorted, the same bytes for the same state."""
    return json.dumps(found, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# --- the human view --------------------------------------------------------------------


def _why_it_passes(found: Landing) -> str:
    """Why a run with proposals, or with none, does not fail."""
    if not found.is_default:
        return (
            f"{printable(found.named)} is not the default branch "
            f"({printable(str(found.declared_branch.value))}), so nothing is refused here"
        )
    if found.key.value is not True:
        return f"the refusal is off: {REFUSE_PROPOSALS_KEY} is not true at the base's tip"
    return "nothing would land proposed"


def _work_line(work: Work, nothing: str = "nothing of it lands") -> str:
    shown = ", ".join(printable(path) for path in work.paths) or nothing
    return f"{work.commit[:SHORT]} {printable(work.subject)}: {shown}"


def _accepted_lines(accepted: Accepted) -> Iterator[str]:
    yield f"    {printable(accepted.name)} (`{printable(accepted.path)}`)"
    if not accepted.acceptances:
        yield "      no commit of the change accepted it"
    for acceptance in accepted.acceptances:
        yield f"      accepted in {_work_line(acceptance.commit, 'nothing else of it lands')}"
        for work in acceptance.before:
            yield f"        before it: {_work_line(work)}"
        if acceptance.edits is not None:
            yield f"        edited since: {printable(acceptance.edits.said())}"


def render_human(found: Landing) -> str:
    """The base, whether the refusal is on, then what the check reports and lists."""
    title = cli_render.style("title", "Landing check")
    base = f"{printable(found.named)} at {(found.base.tip or '')[:SHORT]}"
    lines = [f"{title} — {found.head[:SHORT]} into {base}", ""]
    if found.proposals:
        lines.append(f"  {len(found.proposals)} proposal(s) would land:")
        for proposal in found.proposals:
            where = f"{printable(proposal.name)} (`{printable(proposal.path)}`)"
            lines.append(f"    {where}: {printable(proposal.said())}")
    else:
        lines.append("  No proposal would land.")
    if found.accepted:
        lines.append(f"  {len(found.accepted)} record(s) and rule(s) the change makes accepted:")
        for accepted in found.accepted:
            lines.extend(_accepted_lines(accepted))
    if found.accepted_on_base:
        lines.append("  Accepted on the base since the branch left it, and changed by the merge:")
        for item in found.accepted_on_base:
            where = f"{printable(item.name)} (`{printable(item.path)}`)"
            lines.append(f"    {where}: {printable(item.edits.said())}")
    if found.key_changes:
        lines.append(
            f"  The change sets {REFUSE_PROPOSALS_KEY} from {found.key.value} to "
            f"{found.key_at_landing.value}. It counts once it has landed."
        )
    if found.standing:
        lines.append(f"  {len(found.standing)} proposal(s) the base holds, for a person to settle:")
        for proposal in found.standing:
            lines.append(f"    {printable(proposal.name)} (`{printable(proposal.path)}`)")
    if found.disagreements:
        lines.append("  The tip and the landing state disagree on whether these are received:")
        lines.extend(f"    {printable(path)}" for path in found.disagreements)
    lines.extend(f"  {printable(why)}." for why in found.cannot_tell)
    lines.append("")
    if found.refuses:
        lines.append("  Refused: a proposal would land on the default branch.")
    else:
        lines.append(f"  Passes: {_why_it_passes(found)}.")
    return "\n".join(lines) + "\n"


__all__ = [
    "NO_ANSWER_EXIT",
    "RECORD",
    "RULE",
    "RULE_SET_FILE",
    "SCHEMA_VERSION",
    "Acceptance",
    "Accepted",
    "AcceptedOnBase",
    "Landing",
    "NoAnswer",
    "Proposal",
    "RuleEdits",
    "Work",
    "check",
    "document",
    "no_answer_document",
    "proposals_at",
    "render_human",
    "render_json",
]
