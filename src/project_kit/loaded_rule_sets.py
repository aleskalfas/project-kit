"""Loaded rule sets and their loaded files (COR-068; ADR-075 points 2 to 5).

A *loaded* rule set (`loaded: true`) keeps operational rules: its accepted rules
bind on the work of the agent sessions that load a file generated from it, never
on an artefact (COR-068 points 1 and 2). This module is the one home of that file:

- **Where it goes** (`loaded_file_of`), by the set's owner, never by a key in the
  set (ADR-075 point 2): the backbone's set at `.pkit/rules/core.md`
  (`BACKBONE_LOADED_FILE`), a project's own at `.pkit/rules/project.md`
  (`PROJECT_LOADED_FILE`), the paths the harness's include reads. A capability's
  loaded set has none: validation refuses it (COR-068 point 4).
- **What it holds** (`project`), the one projection of a set into its file (ADR-075
  point 3): the set's body with each accepted rule's section under the heading
  `N. Title (RS-<SET>-NNN)`, at the level the set writes it, and each proposed,
  superseded or withdrawn rule's section left out. The prose before the first
  section, the group headings and the prose under them carry over as the set writes
  them. No front matter, and no text the set does not hold.
- **Writing it** (`generate`), what `pkit rule-sets generate` runs (ADR-075 point 4):
  the loaded file of each loaded set the repository authors, refusing before it
  writes anything where none is authored here but one arrives by sync, or a set
  cannot be read or does not join.
- **Checking it** (`staleness_findings`), the part of validation's `rule-sets` member
  that fails a loaded file out of step with its set (ADR-075 point 5): byte for
  byte once line endings are read as `\\n`, only where the set is authored, by the
  tree's own predicate (`is_synced_copy`).
- **Its budget** (COR-069; ADR-077 points 1 to 6): the one count of a rules file's
  words (`word_count`), which the check, the report and the generator all call;
  each rules file a session loads, with its count and its budget, and the findings
  of the member on them (`check_budgets`); and each budget a change raises, lowers,
  adds or removes, for `pkit rule-sets altered` (`budget_changes`). A rules file is
  the loaded file of a loaded set, or the project's rules kept as a plain file, whose
  budget is `rule-sets.plain-file-budget` in the configuration.

The generator and the check both call `project`, so a file the generator writes
always passes the check (ADR-075, "Why one function for the generator and the
check"). The set's body is read through the one reading of a document's parts
(`document_parts.Body`, ADR-057 point 2).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

import click

from project_kit import document_parts, lifecycle_ownership
from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.line_breaks import universal_newlines
from project_kit.project_config import PROJECT_CONFIG_RELPATH

#: The backbone's loaded set's loaded file: the path the harness's include reads
#: (ADR-075 point 2).
BACKBONE_LOADED_FILE = PurePosixPath(".pkit/rules/core.md")

#: A project's own loaded set's loaded file, the path the project's include reads
#: (ADR-075 point 6).
PROJECT_LOADED_FILE = PurePosixPath(".pkit/rules/project.md")

#: The command that writes a loaded file, as the findings and messages name it.
GENERATE_COMMAND = "pkit rule-sets generate"

# What may separate a rule's id from its title in its section's heading.
_TITLE_SEPARATORS = " \t—–-:"


def loaded_file_of(rule_set: rs.RuleSet) -> PurePosixPath | None:
    """The loaded file of a loaded set, by its owner; `None` for a capability's set,
    which has none (COR-068 point 4)."""
    if rule_set.component == fd.BACKBONE_COMPONENT:
        return BACKBONE_LOADED_FILE
    if rule_set.component is None:
        return PROJECT_LOADED_FILE
    return None


def rule_number(rule_id: str) -> int:
    """A rule's number, without its leading zeros: `RS-OPS-019` is 19."""
    return int(rule_id.rsplit("-", 1)[1])


def heading_title(heading: str, rule_id: str) -> str:
    """The title a rule's section heading gives after its id, its separator dropped."""
    return heading[len(rule_id) :].lstrip(_TITLE_SEPARATORS).strip()


def project(rule_set: rs.RuleSet) -> str:
    """The loaded file of `rule_set`, as text with `\\n` line breaks (ADR-075 point 3).

    The set's body, read once (`document_parts.Body`). Each section headed by one of
    the set's rules — from its heading to the next heading of the same or a higher
    level — is either rewritten or left out:

    - an accepted rule's keeps its statement as the set writes it, under the heading
      `N. Title (RS-<SET>-NNN)` at the level the set writes it
    - any other rule's is left out, with the line breaks that end it

    Everything else carries over as written: the prose before the first section, the
    group headings and the prose under them. The text ends with one line break.
    """
    body = rule_set.body
    read = document_parts.Body.read(body)
    headings = read.headings
    out: list[str] = []
    position = 0
    for index, heading in enumerate(headings):
        if heading.start < position:
            continue  # inside a rule's section already taken
        rule = next(
            (r for r in rule_set.rules if document_parts.heading_opens_with(heading.title, r.id)),
            None,
        )
        if rule is None:
            continue
        end = next(
            (later.start for later in headings[index + 1 :] if later.level <= heading.level),
            len(body),
        )
        out.append(body[position : heading.start])
        if rule.binds:
            line_end = body.find("\n", heading.start)
            line_end = end if line_end == -1 or line_end > end else line_end
            title = heading_title(heading.title, rule.id)
            named = (
                f"{rule_number(rule.id)}. {title} ({rule.id})"
                if title
                else (f"{rule_number(rule.id)}. ({rule.id})")
            )
            out.append(f"{'#' * heading.level} {named}{body[line_end:end]}")
        position = end
    out.append(body[position:])
    return "".join(out).rstrip("\n") + "\n"


# --- what stops a projection --------------------------------------------------------


def unprojectable(rule_set: rs.RuleSet, discovery: rs.RuleSetDiscovery) -> str | None:
    """Why a loaded set's file cannot be projected, or None: its rules and sections do
    not join, it is a capability's, or its owner has another loaded set first by path.
    Each is a finding of validation's `rule-sets` member, which names the fix."""
    if any(True for _ in rs.join_findings(rule_set)):
        return "its rules and its sections do not join"
    if loaded_file_of(rule_set) is None:
        return f"it is {rule_set.owner}'s, and a capability's loaded set has no loaded file"
    first = first_loaded(discovery, rule_set.component)
    if first is not None and first is not rule_set:
        return f"{rule_set.owner} has a loaded rule set already, {first.citation}"
    return None


def first_loaded(discovery: rs.RuleSetDiscovery, component: str | None) -> rs.RuleSet | None:
    """The first loaded set of an owner by path: the one its loaded file is generated
    from. A second is validation's finding (COR-068 point 1)."""
    return next((s for s in discovery.rule_sets if s.loaded and s.component == component), None)


def loaded_sets(discovery: rs.RuleSetDiscovery) -> tuple[rs.RuleSet, ...]:
    return tuple(s for s in discovery.rule_sets if s.loaded)


def synced_copy_test(target_root: Path) -> Callable[[str], bool] | None:
    """Whether a set's file arrives here by sync: the tree's own predicate
    (`is_synced_copy`), keyed on origin and on the repository, never on the path
    (ADR-075 point 5). None for a tree without the ownership module."""
    ownership = lifecycle_ownership.load_ownership(target_root)
    if ownership is None:
        return None
    return lambda rel: bool(ownership.is_synced_copy(target_root, rel))


# --- the check (ADR-075 point 5) ------------------------------------------------------


def staleness_findings(
    target_root: Path, discovery: rs.RuleSetDiscovery
) -> Iterable[rs.RuleSetFinding]:
    """Each loaded file out of step with its set, where the set is authored.

    For the first loaded set of the backbone and of the project, its file is compared
    with `project`'s text, byte for byte once line endings are read as `\\n`. A file
    that differs, or is missing, is an error naming the file, the set and the command
    that writes it. A set that arrives by sync is not compared: the project receives it
    and its file together and edits neither. A set that cannot be projected is left to
    the finding that says why. A tree without the ownership module cannot tell where a
    set is authored, so each loaded set is skipped with a report saying so.
    """
    candidates = [s for s in loaded_sets(discovery) if unprojectable(s, discovery) is None]
    if not candidates:
        return
    is_synced_copy = synced_copy_test(target_root)
    for rule_set in candidates:
        loaded_file = loaded_file_of(rule_set)
        assert loaded_file is not None  # unprojectable says so otherwise
        if is_synced_copy is None:
            yield rs.RuleSetFinding(
                rule_set.path,
                "",
                rs.Severity.REPORT,
                rs.RuleSetFindingKind.LOADED_FILE_UNCHECKED,
                f"the tree has no ownership module ({lifecycle_ownership.OWNERSHIP_MODULE}), "
                f"so whether {rule_set.citation} is authored here cannot be told, and "
                f"{loaded_file} is not compared with it (run `pkit sync`).",
            )
            continue
        if is_synced_copy(rule_set.path):
            continue
        problem = _stale(target_root / loaded_file, project(rule_set))
        if problem is not None:
            yield rs.RuleSetFinding(
                str(loaded_file),
                "",
                rs.Severity.ERROR,
                rs.RuleSetFindingKind.LOADED_FILE_STALE,
                f"{problem} the loaded file of {rule_set.citation} ({rule_set.path}), which "
                f"is generated from the set and kept in step with it in the same change "
                f"(COR-068 point 3). Run `{GENERATE_COMMAND}`, and edit the set, not the "
                f"loaded file.",
            )


def _stale(path: Path, expected: str) -> str | None:
    """Why the file at `path` is not `expected`, or None when it is."""
    if not path.is_file() or path.is_symlink():
        return "the file is missing, and it is"
    try:
        actual = universal_newlines(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError):
        return "the file cannot be read as text, and it is"
    return None if actual == expected else "the file differs from"


# --- the budget (COR-069; ADR-077 points 1 to 4) --------------------------------------

#: Unicode's White_Space property, character by character (the Unicode Character
#: Database's PropList.txt): what separates the words a budget counts (COR-069 point 1).
#: Named here rather than left to a language's split, which takes other characters as
#: space too, such as the information separators U+001C to U+001F (ADR-077 point 3).
WHITE_SPACE: frozenset[str] = frozenset(
    chr(code)
    for code in (
        *range(0x09, 0x0E),  # tab, line feed, line tabulation, form feed, carriage return
        0x20,  # space
        0x85,  # next line
        0xA0,  # no-break space
        0x1680,  # ogham space mark
        *range(0x2000, 0x200B),  # en quad to hair space
        0x2028,  # line separator
        0x2029,  # paragraph separator
        0x202F,  # narrow no-break space
        0x205F,  # medium mathematical space
        0x3000,  # ideographic space
    )
)

_WORD = re.compile("[^" + "".join(re.escape(c) for c in sorted(WHITE_SPACE)) + "]+")

#: The configuration block and key that give the project's plain rules file its budget
#: (COR-069 point 3; ADR-077 point 2), and the key as the findings name it.
RULE_SETS_BLOCK = "rule-sets"
PLAIN_FILE_BUDGET_KEY = "plain-file-budget"
PLAIN_FILE_BUDGET = f"{RULE_SETS_BLOCK}.{PLAIN_FILE_BUDGET_KEY}"

#: The configuration file, as the findings name it.
CONFIG_FILE = PROJECT_CONFIG_RELPATH.as_posix()


def word_count(text: str) -> int:
    """The words of a rules file's text: each run of characters none of which has
    Unicode's White_Space property (COR-069 point 1). The one count of a rules file:
    the check, the report and the generator all call it (ADR-077 point 3). It is not
    the prose lint's count, which serves the writing rules by another definition."""
    return sum(1 for _ in _WORD.finditer(text))


def plain_file_budget(config: Mapping[str, Any]) -> int | None:
    """`rule-sets.plain-file-budget` from a configuration as read, or None where it is
    absent or of another shape, which the configuration pass reports (COR-048 point 4)."""
    block = config.get(RULE_SETS_BLOCK)
    if not isinstance(block, Mapping):
        return None
    return rs.read_budget(cast(Mapping[str, Any], block).get(PLAIN_FILE_BUDGET_KEY))


def measure(words: int, budget: int | None) -> str:
    """A file's count against its budget, as the report and the generator say it."""
    if budget is None:
        return f"{words} word(s), no budget"
    if words > budget:
        return f"{words} word(s), budget {budget}, {words - budget} over"
    return f"{words} word(s), budget {budget}, {budget - words} to spare"


@dataclass(frozen=True)
class RulesFile:
    """One rules file a session loads (COR-069 point 1), as validation counts it.

    - `path`: the loaded file of a loaded set, or the project's rules kept as a plain
      file, relative to the root
    - `words`: its count, of the file as written; None where there is no file to count:
      missing, a link, or not text
    - `budget`: the most words it may hold, or None where it has none
    - `rule_set`: the loaded set it is generated from; None for the plain file
    - `checked`: whether its owner can correct it here, so that validation fails it past
      its budget: a component's file where its set is authored, a project's own always
    """

    path: PurePosixPath
    words: int | None
    budget: int | None
    rule_set: rs.RuleSet | None
    checked: bool

    @property
    def budget_set_in(self) -> str:
        """Where its budget is set, as the findings name it."""
        if self.rule_set is None:
            return f"`{PLAIN_FILE_BUDGET}` in {CONFIG_FILE}"
        return f"`{rs.BUDGET_KEY}` in {self.rule_set.citation} ({self.rule_set.path})"


@dataclass(frozen=True)
class BudgetCheck:
    """The rules files a session loads here, and the member's findings on their budgets."""

    files: tuple[RulesFile, ...]
    findings: tuple[rs.RuleSetFinding, ...]


def check_budgets(target_root: Path, discovery: rs.RuleSetDiscovery) -> BudgetCheck:
    """Each rules file a session loads here with its count and its budget, and what
    validation's `rule-sets` member finds on them (COR-069 point 5; ADR-077 point 4).

    The rules files: the loaded file of the first loaded set of the backbone and of the
    project, by path, and the project's plain rules file where the project has no loaded
    set of its own and keeps one. A capability's loaded set has no loaded file (COR-068
    point 4), and a deployed copy of a loaded file is counted as the file it copies, so
    neither is a rules file here. Each is reported in every project.

    The findings, in this order:

    - a component's loaded set that gives no `budget`, where the set is authored
      (`loaded-set-without-budget`, an error)
    - a rules file holding more words than its budget, where its owner can correct it
      (`rules-file-over-budget`, an error): a component's where its set is authored, a
      project's own always. A project is never failed for a file it receives.
    - `rule-sets.plain-file-budget` set where the project keeps no plain rules file
      (`plain-file-budget-unused`, a warning)

    A tree without the ownership module cannot tell where a component's set is
    authored, so its file is counted and neither of the first two is judged on it; the
    staleness check reports the tree.
    """
    is_synced_copy = synced_copy_test(target_root)

    def authored(rule_set: rs.RuleSet) -> bool:
        return is_synced_copy is not None and not is_synced_copy(rule_set.path)

    key_budget = plain_file_budget(fd.configuration_at(target_root))
    own = first_loaded(discovery, None)
    files: list[RulesFile] = []
    for rule_set in (first_loaded(discovery, fd.BACKBONE_COMPONENT), own):
        loaded_file = None if rule_set is None else loaded_file_of(rule_set)
        if rule_set is None or loaded_file is None:
            continue
        checked = rule_set.component is None or authored(rule_set)
        words = _words_of(target_root / loaded_file)
        files.append(RulesFile(loaded_file, words, rule_set.budget, rule_set, checked))
    plain = target_root / PROJECT_LOADED_FILE
    has_plain = own is None and (plain.exists() or plain.is_symlink())
    if has_plain:
        files.append(RulesFile(PROJECT_LOADED_FILE, _words_of(plain), key_budget, None, True))

    findings: list[rs.RuleSetFinding] = [
        _missing_budget(rule_set)
        for rule_set in loaded_sets(discovery)
        if rule_set.component is not None
        and rs.BUDGET_KEY not in rule_set.front_matter
        and authored(rule_set)
    ]
    findings.extend(
        _over_budget(file)
        for file in files
        if file.checked
        and file.words is not None
        and file.budget is not None
        and file.words > file.budget
    )
    if key_budget is not None and not has_plain:
        findings.append(_unused_key(own))
    return BudgetCheck(tuple(files), tuple(findings))


def summary_line(file: RulesFile) -> str:
    """One rules file's line under validation's `rule-sets` heading: its path, its
    count, and its budget or that it has none (ADR-077 point 4)."""
    if file.words is None:
        budget = "no budget" if file.budget is None else f"budget {file.budget}"
        return f"rules file {file.path}: no file to count, {budget}."
    return f"rules file {file.path}: {measure(file.words, file.budget)}."


#: What the findings past a budget, and the generator, tell whoever meets them (COR-069
#: point 4).
_TRIM = (
    "raising a budget is a person's decision (COR-069 point 4): trim the file, or bring "
    "the raise to the person who authorises the change"
)


def _over_budget(file: RulesFile) -> rs.RuleSetFinding:
    assert file.words is not None and file.budget is not None
    how = (
        ""
        if file.rule_set is None
        else f" Trim the rules in {file.rule_set.path} and run `{GENERATE_COMMAND}`."
    )
    return rs.RuleSetFinding(
        str(file.path),
        "",
        rs.Severity.ERROR,
        rs.RuleSetFindingKind.RULES_FILE_OVER_BUDGET,
        f"the rules file holds {file.words} words, {file.words - file.budget} past its "
        f"budget of {file.budget}, set as {file.budget_set_in}. Every session loads the "
        f"file whole, and {_TRIM}.{how}",
    )


def _missing_budget(rule_set: rs.RuleSet) -> rs.RuleSetFinding:
    return rs.RuleSetFinding(
        rule_set.path,
        "",
        rs.Severity.ERROR,
        rs.RuleSetFindingKind.LOADED_SET_WITHOUT_BUDGET,
        f"{rule_set.owner}'s loaded set {rule_set.citation} gives no `{rs.BUDGET_KEY}`. A "
        f"component's loaded set holds the file it generates to a budget in words, so that "
        f"each project receiving the file sees what it costs, and its growth is a raise a "
        f"person authorises (COR-069 point 2). Add `{rs.BUDGET_KEY}: <words>` beside "
        f"`{rs.LOADED_KEY}: true`; `{GENERATE_COMMAND}` prints the file's count.",
    )


def _unused_key(own: rs.RuleSet | None) -> rs.RuleSetFinding:
    if own is None:
        why = f"the project keeps no rules file at {PROJECT_LOADED_FILE}"
        fix = "Remove the key, or keep the project's rules there."
    else:
        why = (
            f"the project keeps its rules as the loaded set {own.citation} ({own.path}), "
            f"whose own `{rs.BUDGET_KEY}` bounds its loaded file"
        )
        fix = f"Move the budget into the set's `{rs.BUDGET_KEY}`, and remove the key."
    return rs.RuleSetFinding(
        CONFIG_FILE,
        f"/{RULE_SETS_BLOCK}/{PLAIN_FILE_BUDGET_KEY}",
        rs.Severity.WARNING,
        rs.RuleSetFindingKind.PLAIN_FILE_BUDGET_UNUSED,
        f"`{PLAIN_FILE_BUDGET}` bounds the project's rules kept as a plain file, but {why}, "
        f"so the key bounds nothing, and one budget has one place (COR-069 point 3). {fix}",
    )


def _words_of(path: Path) -> int | None:
    """The count of the file at `path` as written, or None where there is none to count:
    missing, a link, which the staleness check reads as no file, or not text."""
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return word_count(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


# --- what a change does to the budgets (ADR-077 point 6) --------------------------------

#: How a change sets a budget otherwise than its base.
RAISED, LOWERED, ADDED, REMOVED = "raised", "lowered", "added", "removed"


@dataclass(frozen=True)
class BudgetChange:
    """A budget of a rules file that a change sets otherwise than its base.

    - `set_by`: the loaded set as cited, or `rule-sets.plain-file-budget`
    - `path`: the file the budget is written in
    - `file`: the rules file it bounds; None for a capability's set, which has none
    - `base`, `head`: the budget at each state, None where it has none
    """

    set_by: str
    path: str
    file: str | None
    base: int | None
    head: int | None

    @property
    def change(self) -> str:
        if self.base is None:
            return ADDED
        if self.head is None:
            return REMOVED
        return RAISED if self.head > self.base else LOWERED


def budget_changes(
    target_root: Path,
    base: rs.RuleSetDiscovery,
    head: rs.RuleSetDiscovery,
    base_tree: fd.RepositoryTree,
    head_tree: fd.RepositoryTree | None,
) -> tuple[BudgetChange, ...]:
    """Each budget of a rules file that a change sets otherwise than its base (COR-069
    point 4): each loaded set's `budget`, the sets paired by how they are cited, those of
    the head in its path order and then those only the base holds; then
    `rule-sets.plain-file-budget`, read from the configuration each state holds (the
    working tree's where `head_tree` is None). A budget the schemas refuse reads as
    none."""
    before, after = _loaded_by_citation(base), _loaded_by_citation(head)
    changes: list[BudgetChange] = []
    for citation in [*after, *(c for c in before if c not in after)]:
        was, now = before.get(citation), after.get(citation)
        shown = now if now is not None else was
        assert shown is not None
        was_budget = None if was is None else was.budget
        now_budget = None if now is None else now.budget
        if was_budget != now_budget:
            loaded_file = loaded_file_of(shown)
            changes.append(
                BudgetChange(
                    citation,
                    shown.path,
                    None if loaded_file is None else str(loaded_file),
                    was_budget,
                    now_budget,
                )
            )
    was_key = plain_file_budget(fd.configuration_at(target_root, base_tree))
    now_key = plain_file_budget(fd.configuration_at(target_root, head_tree))
    if was_key != now_key:
        changes.append(
            BudgetChange(PLAIN_FILE_BUDGET, CONFIG_FILE, str(PROJECT_LOADED_FILE), was_key, now_key)
        )
    return tuple(changes)


def _loaded_by_citation(discovery: rs.RuleSetDiscovery) -> dict[str, rs.RuleSet]:
    """Each loaded set by how it is cited, the first by path where two share a name."""
    found: dict[str, rs.RuleSet] = {}
    for rule_set in loaded_sets(discovery):
        found.setdefault(rule_set.citation, rule_set)
    return found


# --- the generator (ADR-075 point 4) --------------------------------------------------


class GenerateRefusal(click.ClickException):
    """The generator refused before it wrote anything."""


@dataclass(frozen=True)
class Generated:
    """One loaded file the generator wrote, or found already in step."""

    rule_set: str  # the set as cited
    set_path: str
    path: str  # the loaded file, relative to the root
    changed: bool
    words: int  # the count of the text it writes (COR-069 point 1)
    budget: int | None  # the set's `budget`, or None


@dataclass(frozen=True)
class Received:
    """A loaded set that arrives by sync, whose file the generator leaves to sync."""

    rule_set: str
    path: str


@dataclass(frozen=True)
class Generation:
    written: tuple[Generated, ...]
    received: tuple[Received, ...]


def generate(target_root: Path, *, write: bool = True) -> Generation:
    """Write the loaded file of each loaded set the repository authors.

    Refuses, before it writes anything, where:

    - a rule-set file of the backbone or the project cannot be read, or a loaded set
      cannot be projected (`unprojectable`): the message names `pkit validate`
    - the tree has no ownership module, so where a set is authored cannot be told
    - no loaded set is authored here: none at all, or only sets that arrive by sync,
      whose files the next sync brings (COR-068 point 3)
    - a loaded file of a set authored here is a link, which the check reads as no
      loaded file (`_stale`), so the generator writes through none

    A set that arrives by sync beside one authored here is left, and listed. The file
    is written with `\\n` line breaks, and only where its text differs. Each file comes
    with the count of the text written and the set's budget (ADR-077 point 5): the
    generator writes a file past its budget all the same, and says so. `write=False`
    computes the same answer and writes nothing.
    """
    discovery = rs.discover_rule_sets(target_root)
    unreadable = [
        u for u in discovery.unreadable if u.place.component in (None, fd.BACKBONE_COMPONENT)
    ]
    if unreadable:
        raise GenerateRefusal(
            f"the rule-set file {unreadable[0].path} {unreadable[0].problem}, so it cannot "
            f"be told whether it is a loaded set, though it may be unrelated to any; "
            f"nothing was written. `pkit validate` reports it."
        )
    sets = loaded_sets(discovery)
    for rule_set in sets:
        problem = unprojectable(rule_set, discovery)
        if problem is not None:
            raise GenerateRefusal(
                f"the loaded rule set {rule_set.citation} ({rule_set.path}) cannot be "
                f"generated: {problem}; nothing was written. `pkit validate` names the fix."
            )
    if not sets:
        raise GenerateRefusal(
            "no loaded rule set is found here (a rule-set file with `loaded: true`), so "
            "there is no loaded file to generate."
        )
    is_synced_copy = synced_copy_test(target_root)
    if is_synced_copy is None:
        raise GenerateRefusal(
            f"the tree has no ownership module ({lifecycle_ownership.OWNERSHIP_MODULE}), so "
            f"it cannot be told whether a loaded set is authored here or arrives by sync; "
            f"nothing was written (run `pkit sync`)."
        )
    received = tuple(
        Received(s.citation, str(loaded_file_of(s))) for s in sets if is_synced_copy(s.path)
    )
    authored = [s for s in sets if not is_synced_copy(s.path)]
    if not authored:
        names = ", ".join(f"{r.rule_set} ({r.path})" for r in received)
        raise GenerateRefusal(
            f"every loaded rule set here arrives by sync: {names}. A project neither "
            f"generates nor edits a loaded file it receives; the next sync brings it "
            f"(COR-068 point 3)."
        )
    for rule_set in authored:
        loaded_file = loaded_file_of(rule_set)
        if loaded_file is not None and (target_root / loaded_file).is_symlink():
            raise GenerateRefusal(
                f"the loaded file of {rule_set.citation}, {loaded_file}, is a link, which "
                f"validation reads as no loaded file; nothing was written. Replace the link "
                f"with a file, or remove it, and run `{GENERATE_COMMAND}` again."
            )
    written: list[Generated] = []
    for rule_set in authored:
        loaded_file = loaded_file_of(rule_set)
        assert loaded_file is not None
        text = project(rule_set)
        target = target_root / loaded_file
        changed = _stale(target, text) is not None
        if changed and write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
        written.append(
            Generated(
                rule_set.citation,
                rule_set.path,
                str(loaded_file),
                changed,
                word_count(text),
                rule_set.budget,
            )
        )
    return Generation(tuple(written), received)


def render(generation: Generation) -> str:
    """The generator's report: for each loaded file, whether it changed, then its count
    against its budget on a line beneath; then each set left to sync. A file past its
    budget says what to do, as validation's finding does (ADR-077 point 5)."""
    lines: list[str] = []
    for item in generation.written:
        verb = "wrote" if item.changed else "unchanged"
        lines.append(f"  {verb:<10} {item.path}  (from {item.rule_set}, {item.set_path})")
        over = item.budget is not None and item.words > item.budget
        lines.append(f"{'':<13}{measure(item.words, item.budget)}{f'; {_TRIM}' if over else ''}")
    for item in generation.received:
        lines.append(f"  {'left':<10} {item.path}  ({item.rule_set} arrives by sync)")
    return "\n".join(lines) + "\n"
