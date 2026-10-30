"""Loaded rule sets and their loaded files (COR-068; ADR-075 points 2 to 5).

A *loaded* rule set (`loaded: true`) keeps operational rules: its accepted rules
bind on the work of the agent sessions that load a file generated from it, never
on an artefact (COR-068 points 1 and 2). This module is the one home of that file:

- **Where it goes** (`loaded_file_of`), by the set's owner, never by a key in the
  set (ADR-075 point 2): the backbone's set at `.pkit/rules/core.md`
  (`BACKBONE_LOADED_FILE`), a project's own at `.pkit/rules/project.md`
  (`PROJECT_LOADED_FILE`), the paths the harness's include reads, and a
  capability's at `rules.md` at the root of its tree (`capability_loaded_file`,
  ADR-076 point 1), which the capabilities' rules index reaches (`loaded_rules`).
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
  tree's own predicate (`is_synced_copy`). Where a capability is authored, the same
  member fails its loaded set's preface that does not name it, and a `rules.md` at
  its root with no loaded set behind it (`capability_findings`, ADR-076 point 1).

The generator and the check both call `project`, so a file the generator writes
always passes the check (ADR-075, "Why one function for the generator and the
check"). The set's body is read through the one reading of a document's parts
(`document_parts.Body`, ADR-057 point 2).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import click

from project_kit import document_parts, lifecycle_ownership
from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.line_breaks import universal_newlines

#: The backbone's loaded set's loaded file: the path the harness's include reads
#: (ADR-075 point 2).
BACKBONE_LOADED_FILE = PurePosixPath(".pkit/rules/core.md")

#: A project's own loaded set's loaded file, the path the project's include reads
#: (ADR-075 point 6).
PROJECT_LOADED_FILE = PurePosixPath(".pkit/rules/project.md")

#: A capability's loaded file, at the root of its tree (ADR-076 point 1).
CAPABILITY_LOADED_FILE_NAME = "rules.md"

#: The command that writes a loaded file, as the findings and messages name it.
GENERATE_COMMAND = "pkit rule-sets generate"

# What may separate a rule's id from its title in its section's heading.
_TITLE_SEPARATORS = " \t—–-:"


def capability_loaded_file(name: str) -> PurePosixPath:
    """The loaded file of capability `name`'s loaded set, from the root: its name gives it,
    as one constant gives the backbone's (ADR-076 point 1)."""
    return PurePosixPath(fd.CAPABILITIES_DIR.as_posix()) / name / CAPABILITY_LOADED_FILE_NAME


def loaded_file_of(rule_set: rs.RuleSet) -> PurePosixPath:
    """The loaded file of a loaded set, by its owner (ADR-075 point 2; ADR-076 point 1)."""
    if rule_set.component == fd.BACKBONE_COMPONENT:
        return BACKBONE_LOADED_FILE
    if rule_set.component is None:
        return PROJECT_LOADED_FILE
    return capability_loaded_file(rule_set.component)


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
    not join, or its owner has another loaded set first by path. Each is a finding of
    validation's `rule-sets` member, which names the fix."""
    if any(True for _ in rs.join_findings(rule_set)):
        return "its rules and its sections do not join"
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

    For the first loaded set of each owner, the backbone, each capability and the
    project, its file is compared with `project`'s text, byte for byte once line endings
    are read as `\\n`. A file that differs, or is missing, is an error naming the file,
    the set and the command that writes it. A set that arrives by sync is not compared:
    the project receives it
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


def preface(rule_set: rs.RuleSet) -> str:
    """The prose before a set's first rule: its body up to the first heading that opens
    with one of its rules' ids, or the whole body when none does."""
    ids = [rule.id for rule in rule_set.rules]
    for heading in document_parts.body_headings(rule_set.body):
        if any(document_parts.heading_opens_with(heading.title, rule_id) for rule_id in ids):
            return rule_set.body[: heading.start]
    return rule_set.body


def capability_findings(
    target_root: Path, discovery: rs.RuleSetDiscovery
) -> Iterable[rs.RuleSetFinding]:
    """What a capability's loaded set and its loaded file get wrong where the capability is
    authored (ADR-076 point 1), by the tree's own predicate (`is_synced_copy`):

    - a loaded set whose preface does not name its capability: a session reads the file,
      not the records, so the file says whose layer its rules are (COR-070 point 1). Only
      the name is checked; the rest of the preface is judged by whoever accepts the set
    - a `rules.md` at the root of a registered capability with no loaded set behind it, so
      a file left behind by a removed set is never delivered unchecked

    A tree without the ownership module cannot tell where a capability is authored, and
    the staleness check reports that already, so nothing is judged here.
    """
    is_synced_copy = synced_copy_test(target_root)
    if is_synced_copy is None:
        return
    for rule_set in loaded_sets(discovery):
        component = rule_set.component
        if component in (None, fd.BACKBONE_COMPONENT) or is_synced_copy(rule_set.path):
            continue
        if first_loaded(discovery, component) is not rule_set:
            continue  # a second loaded set is its own finding
        if component not in preface(rule_set):
            yield rs.RuleSetFinding(
                rule_set.path,
                "",
                rs.Severity.ERROR,
                rs.RuleSetFindingKind.LOADED_PREFACE,
                f"the preface of {rule_set.citation}, the prose before its first rule, does "
                f"not name its capability, {component}. A session reads the loaded file, not "
                f"the records, so the file says whose rules they are and how they stand to "
                f"core's and to a project's (COR-070 point 1; the rules README gives the "
                f"sentence). Name {component} in the preface.",
            )
    for name in fd.installed_capability_names(target_root):
        loaded_file = capability_loaded_file(name)
        if not (target_root / loaded_file).is_file() or is_synced_copy(str(loaded_file)):
            continue
        if first_loaded(discovery, name) is not None:
            continue
        yield rs.RuleSetFinding(
            str(loaded_file),
            "",
            rs.Severity.ERROR,
            rs.RuleSetFindingKind.LOADED_FILE_ORPHANED,
            f"capability {name} holds a loaded file, {loaded_file}, but ships no loaded rule "
            f"set it is generated from, so its rules would reach every session with nothing "
            f"to check them (ADR-076 point 1). Remove the file, or restore the set it was "
            f"generated from in {fd.CAPABILITIES_DIR.as_posix()}/{name}/{fd.RULE_SETS_SEGMENT}/ "
            f"and run `{GENERATE_COMMAND}`.",
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

    - a rule-set file of the backbone, of the project or of a capability authored here
      cannot be read, or a loaded set cannot be projected (`unprojectable`): the
      message names `pkit validate`
    - the tree has no ownership module, so where a set is authored cannot be told
    - no loaded set is authored here: none at all, or only sets that arrive by sync,
      whose files the next sync brings (COR-068 point 3)
    - a loaded file of a set authored here is a link, which the check reads as no
      loaded file (`_stale`), so the generator writes through none

    A set that arrives by sync beside one authored here is left, and listed. The file
    is written with `\\n` line breaks, and only where its text differs. `write=False`
    computes the same answer and writes nothing.
    """
    discovery = rs.discover_rule_sets(target_root)
    synced = synced_copy_test(target_root)
    unreadable = [
        u
        for u in discovery.unreadable
        if u.place.component in (None, fd.BACKBONE_COMPONENT)
        or (synced is not None and not synced(u.path))
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
        if (target_root / loaded_file).is_symlink():
            raise GenerateRefusal(
                f"the loaded file of {rule_set.citation}, {loaded_file}, is a link, which "
                f"validation reads as no loaded file; nothing was written. Replace the link "
                f"with a file, or remove it, and run `{GENERATE_COMMAND}` again."
            )
    written: list[Generated] = []
    for rule_set in authored:
        loaded_file = loaded_file_of(rule_set)
        text = project(rule_set)
        target = target_root / loaded_file
        changed = _stale(target, text) is not None
        if changed and write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
        written.append(Generated(rule_set.citation, rule_set.path, str(loaded_file), changed))
    return Generation(tuple(written), received)


def render(generation: Generation) -> str:
    """The generator's report: one line for each loaded file, then each set left to sync."""
    lines: list[str] = []
    for item in generation.written:
        verb = "wrote" if item.changed else "unchanged"
        lines.append(f"  {verb:<10} {item.path}  (from {item.rule_set}, {item.set_path})")
    for item in generation.received:
        lines.append(f"  {'left':<10} {item.path}  ({item.rule_set} arrives by sync)")
    return "\n".join(lines) + "\n"
