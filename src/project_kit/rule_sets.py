"""Rule-set files (COR-051): discovery by the location rule, parsing, validation.

A rule set is one Markdown file (COR-051 point 2). Its front matter holds the
data — the set's name, its version, what it inherits, its scope, and a map
from each rule's id to that rule's machine fields — and its body holds the
prose, one section per rule headed by the rule's id and title. A file is a
rule-set file because of where it is, never because of a field in it
(ADR-056 point 2): the location rule sits with the other place declarations
in `friction_discovery` (`rule_set_places`, `rule_set_files`). The reference
is the schemas README, "Rule-set files".

This module:

- defines the grammar of the RS id family (COR-051 point 3): rule ids
  `RS-<SET>-NNN`, extension points `#<name>`, a method rule set's component
  written in front, `<component>:`, and pins `<SET>@<major>`
  (`parse_rule_reference`, `parse_pin`). `refs` builds its prose citation
  patterns from these constants;
- discovers and parses every rule-set file (`discover_rule_sets`). A file
  that cannot be read, has no front matter, or whose front matter does not
  parse is kept as unreadable, so it is reported and never skipped;
- validates them (`validate_rule_sets`): the schema, strictly, with unknown
  keys through the shared renderer; the container inside each rule — the
  rule-set file is claimed before the container rule, so this pass and not
  the friction pass applies it; the join between data and prose; ids;
  origins; successors; inheritance (points 3, 5 and 7); the scope, which a
  method rule set never takes (point 2), and each type it names that no owner
  declares — a type finding artefact discovery raises and names this pass to
  report (COR-056 point 2; ADR-057 point 2). Whether a pinned
  major is still the inherited set's is a version relation: `pin_checks`
  hands it to the wiring resolver, which reports every version relation
  under `versions` (`connections.rule_set_pin_findings`), and `pkit status`
  shows each pin behind with the edit that re-pins it (`PinCheck.fix`);
- resolves citations to rules (`resolve_citation`) and lists rule ids
  claimed more than once in the rule-set space (`rule_id_collisions`), for
  `pkit refs` and `pkit decisions validate`;
- reads the parts of its rules a set declares checks enforce (`CHECKS_KEY`,
  `CheckPart`, COR-051 point 2), and reports a declaration for a rule the set
  lacks and a check that is not there;
- answers which accepted rules bind on each artefact of one state (`reach`,
  COR-051 point 7): the one home of that answer (ADR-057 point 2), which
  validation reads for the conflicts between routes, and the `rule-sets`
  reading commands give (`rule_set_reading`).

Deterministic: the same repository state gives the same findings in the same
order — files by path, each file's checks in a fixed order, then the
inheritance cycles, then the conflicts by artefact. The reader and the walk
read one state: the working tree, or a commit through discovery's tree.
Validation reads the working tree, and no history. Whether an id was *reused*
after its rule was deleted cannot be seen in one state; that is why retired
rules stay in place, so that a reused id is a duplicate this pass reports.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any, cast

import click
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from project_kit import backbone_schemas as bs
from project_kit import capabilities as caps
from project_kit import document_parts, validators
from project_kit import friction_discovery as fd
from project_kit.decisions import resolve_adr_records_dir

Severity = bs.Severity

# The kind under which the schema is read from the tree (`load_backbone_schema`).
SCHEMA_KIND = "rule-set"

# --- the RS id family (COR-051 point 3) ------------------------------------

#: A rule set's name: upper-case letters and digits, starting with a letter.
SET_NAME_PATTERN = r"[A-Z][A-Z0-9]*"
#: A rule's number: three digits, zero-padded below 100, or more without padding.
RULE_NUMBER_PATTERN = r"(?:[0-9]{3}|[1-9][0-9]{3,})"
#: A rule id: the family prefix, the rule set's name, and a number.
RULE_ID_PATTERN = rf"RS-{SET_NAME_PATTERN}-{RULE_NUMBER_PATTERN}"
#: An extension point's name, written after `#`.
POINT_NAME_PATTERN = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
#: A component's name, written in front of a method rule set's citations.
COMPONENT_PATTERN = r"[a-z](?:[a-z0-9-]*[a-z0-9])?"
#: A pinned major version.
MAJOR_PATTERN = r"(?:0|[1-9][0-9]*)"

_RULE_ID_RE = re.compile(rf"RS-(?P<set>{SET_NAME_PATTERN})-{RULE_NUMBER_PATTERN}")
_RULE_REFERENCE_RE = re.compile(
    rf"(?:(?P<component>{COMPONENT_PATTERN}):)?(?P<rule>{RULE_ID_PATTERN})"
    rf"(?:#(?P<point>{POINT_NAME_PATTERN}))?"
)
_PIN_RE = re.compile(
    rf"(?:(?P<component>{COMPONENT_PATTERN}):)?(?P<set>{SET_NAME_PATTERN})@(?P<major>{MAJOR_PATTERN})"
)
_DECISION_ID_RE = re.compile(
    rf"(?:(?P<capability>{COMPONENT_PATTERN}):(?P<dec>DEC-[0-9]{{3,}})|(?P<record>(?:COR|PRJ|ADR)-[0-9]{{3,}}))"
)
_SEMVER_MAJOR_RE = re.compile(r"(0|[1-9][0-9]*)\.")

# --- statuses (COR-051 point 4) --------------------------------------------

PROPOSED, ACCEPTED, SUPERSEDED, WITHDRAWN = "proposed", "accepted", "superseded", "withdrawn"
STATUSES: tuple[str, ...] = (PROPOSED, ACCEPTED, SUPERSEDED, WITHDRAWN)
#: A rule without a status is proposed, and binds nothing.
DEFAULT_STATUS = PROPOSED
RETIRED_STATUSES: frozenset[str] = frozenset({SUPERSEDED, WITHDRAWN})

# The quote form of an origin; the alternative is a `decision` (COR-051 point 5).
QUOTE_FIELDS: tuple[str, ...] = ("date", "by", "why")

#: The anchor kind that names another artefact (COR-050 point 2): the kind a
#: filling rule anchors to the rule it fills with (COR-051 point 7).
ARTEFACT_ANCHOR_KIND = "artefact"

_yaml = YAML(typ="safe")
_yaml_keeping_first = YAML(typ="safe")
_yaml_keeping_first.allow_duplicate_keys = True  # the first value is kept

_HEADING_ID = re.compile(rf"({RULE_ID_PATTERN})(?![A-Za-z0-9])")


# --- the grammar ---------------------------------------------------------------


@dataclass(frozen=True)
class RuleReference:
    """A rule, or an extension point it offers, as written.

    `[<component>:]RS-<SET>-NNN[#<point>]` — the component is written in
    front of a method rule set's rules (COR-051 point 6).
    """

    rule: str
    component: str | None = None
    point: str | None = None

    @property
    def set_name(self) -> str:
        return rule_set_name_of(self.rule) or ""

    @property
    def point_key(self) -> str:
        """The extension point without the component: `RS-<SET>-NNN#<point>`."""
        return f"{self.rule}#{self.point}" if self.point else self.rule

    def __str__(self) -> str:
        prefix = f"{self.component}:" if self.component else ""
        return f"{prefix}{self.point_key}"


@dataclass(frozen=True)
class Pin:
    """An inherited rule set and the major version pinned: `[<component>:]<SET>@<major>`."""

    set_name: str
    major: int
    component: str | None = None

    def __str__(self) -> str:
        prefix = f"{self.component}:" if self.component else ""
        return f"{prefix}{self.set_name}@{self.major}"


def rule_set_name_of(rule_id: str) -> str | None:
    """The set name a well-formed rule id carries, or None."""
    match = _RULE_ID_RE.fullmatch(rule_id)
    return match.group("set") if match else None


def parse_rule_reference(text: Any) -> RuleReference | None:
    """`[<component>:]RS-<SET>-NNN[#<point>]` as a `RuleReference`, or None."""
    if not isinstance(text, str):
        return None
    match = _RULE_REFERENCE_RE.fullmatch(text.strip())
    if match is None:
        return None
    return RuleReference(
        rule=match.group("rule"), component=match.group("component"), point=match.group("point")
    )


def parse_pin(text: Any) -> Pin | None:
    """`[<component>:]<SET>@<major>` as a `Pin`, or None."""
    if not isinstance(text, str):
        return None
    match = _PIN_RE.fullmatch(text.strip())
    if match is None:
        return None
    return Pin(
        set_name=match.group("set"),
        major=int(match.group("major")),
        component=match.group("component"),
    )


# --- the model -----------------------------------------------------------------

#: The front-matter key declaring the parts of the set's rules that checks enforce
#: (COR-051 point 2): beside the rules, never among a rule's own fields.
CHECKS_KEY = "checks"

#: The owner a backbone check is named with (`backbone:<command>`).
BACKBONE_OWNER = fd.BACKBONE_COMPONENT

_CHECK_NAME_RE = re.compile(rf"(?:(?P<owner>{COMPONENT_PATTERN}):)?(?P<name>\S(?:.*\S)?)")


@dataclass(frozen=True)
class CheckPart:
    """The part of a rule a check enforces, as the rule's owner declares it (COR-051 point 2).

    `check` names the check and whose it is, as written: `backbone:<command>`
    for the backbone's — a `pkit` command, its words separated by spaces —
    `<component>:<command>` for a command a component registers in its
    package metadata, and a bare name for the project's own tool. `part` says,
    in words, which part of the rule the check settles. `index` is the
    declaration's position in the rule's list, as written. The declaration is
    no part of the rule's content (COR-050), so declaring a check, or changing
    one, flags nothing anchored to the rule.
    """

    check: str
    part: str
    index: int

    @property
    def owner(self) -> str | None:
        """`backbone`, a component's name, or `None` for the project's own tool."""
        match = _CHECK_NAME_RE.fullmatch(self.check)
        return match.group("owner") if match else None

    @property
    def name(self) -> str:
        """The check's name without its owner: a command, or the project's tool."""
        match = _CHECK_NAME_RE.fullmatch(self.check)
        return match.group("name") if match else self.check


@dataclass(frozen=True, eq=False)
class Rule:
    """One rule: its data entry and the body section headed by its id.

    `data` is the entry as written (`{}` when the entry is not a mapping; the
    schema reports it). Every property reads forgivingly — a value of the
    wrong shape reads as absent — because the schema pass judges the shape.
    `checks` are the parts of it that checks enforce, as the set's
    front matter declares them beside the rule (`CHECKS_KEY`), never read
    from the entry. Compared by identity: each rule is parsed once.
    """

    id: str
    path: str  # the rule-set file, relative to the root
    data: Mapping[str, Any]
    section: str  # the body section headed by the id, or ""
    checks: tuple[CheckPart, ...] = ()

    @property
    def location(self) -> str:
        return f"{self.path}#{self.id}"

    @property
    def set_name(self) -> str | None:
        return rule_set_name_of(self.id)

    @property
    def status(self) -> str:
        """The written status, or `proposed` when there is none (COR-051 point 4).

        A status that is not one of the four is a schema error; until it is
        fixed the rule is read as proposed, so it binds nothing.
        """
        status = self.data.get("status")
        return status if isinstance(status, str) and status in STATUSES else DEFAULT_STATUS

    @property
    def binds(self) -> bool:
        return self.status == ACCEPTED

    @property
    def is_retired(self) -> bool:
        return self.status in RETIRED_STATUSES

    @property
    def origin(self) -> Mapping[str, Any] | None:
        origin = self.data.get("origin")
        return origin if isinstance(origin, Mapping) else None

    @property
    def offers(self) -> tuple[str, ...]:
        return tuple(
            point
            for point in _list(self.data.get("offers"))
            if isinstance(point, str) and re.fullmatch(POINT_NAME_PATTERN, point)
        )

    @property
    def fills(self) -> tuple[tuple[int, RuleReference], ...]:
        """Each well-formed fill with its index as written."""
        found: list[tuple[int, RuleReference]] = []
        for index, text in enumerate(_list(self.data.get("fills"))):
            reference = parse_rule_reference(text)
            if reference is not None and reference.point is not None:
                found.append((index, reference))
        return tuple(found)

    @property
    def successor(self) -> RuleReference | None:
        reference = parse_rule_reference(self.data.get("successor"))
        return reference if reference is not None and reference.point is None else None

    def anchors(self, kind: str) -> tuple[str, ...]:
        """The anchors of `kind` the rule's friction block declares, in written order.

        Read forgivingly like every field here: the container rule judges the
        block's shape, and a malformed block reads as declaring nothing.
        """
        container = self.data.get(bs.CONTAINER_KEY)
        friction = container.get(fd.FRICTION_KEY) if isinstance(container, Mapping) else None
        anchors = friction.get("anchors") if isinstance(friction, Mapping) else None
        values = anchors.get(kind) if isinstance(anchors, Mapping) else None
        return tuple(value for value in _list(values) if isinstance(value, str))


@dataclass(frozen=True)
class Section:
    """A body heading that opens with a rule id, or looks as if it should."""

    rule_id: str | None  # the well-formed id it opens with; None when it only starts with `RS-`
    heading: str


@dataclass(frozen=True)
class DuplicateKey:
    """A key written more than once in one mapping of the front matter."""

    pointer: str  # JSON Pointer of the mapping holding the key
    key: str
    lines: tuple[int, ...]  # 1-based line in the file of each occurrence


@dataclass(frozen=True, eq=False)
class RuleSet:
    """One rule-set file, parsed.

    `front_matter` is the parsed data with YAML dates and non-text keys
    rendered as written (`backbone_schemas.as_written`). Where a key was
    written twice, the first value is the one kept, and `duplicate_keys`
    says so. Compared by identity: each file is parsed once.
    """

    path: str
    place: fd.RuleSetPlace
    front_matter: Mapping[str, Any]
    body: str
    rules: tuple[Rule, ...]
    sections: tuple[Section, ...]
    duplicate_keys: tuple[DuplicateKey, ...] = ()

    @property
    def component(self) -> str | None:
        """The component a method rule set ships with; None for a project rule set."""
        return self.place.component

    @property
    def name(self) -> str | None:
        name = self.front_matter.get("rule-set")
        return name if isinstance(name, str) and re.fullmatch(SET_NAME_PATTERN, name) else None

    @property
    def version(self) -> str | None:
        version = self.front_matter.get("version")
        return version if isinstance(version, str) else None

    @property
    def major(self) -> int | None:
        match = _SEMVER_MAJOR_RE.match(self.version or "")
        return int(match.group(1)) if match else None

    @property
    def pins(self) -> tuple[tuple[int, Pin], ...]:
        """Each well-formed `inherits` entry with its index as written."""
        found: list[tuple[int, Pin]] = []
        for index, text in enumerate(_list(self.front_matter.get("inherits"))):
            pin = parse_pin(text)
            if pin is not None:
                found.append((index, pin))
        return tuple(found)

    @property
    def citation(self) -> str:
        """How the set is cited: `<component>:<SET>` for a method set, bare for a project one."""
        name = self.name or "?"
        return f"{self.component}:{name}" if self.component else name

    def cite(self, rule_id: str) -> str:
        """How one of its rules is cited: `<component>:RS-<SET>-NNN` for a method set, bare
        for a project one — a form every reader resolves, anchors included."""
        return f"{self.component}:{rule_id}" if self.component else rule_id

    @property
    def owner(self) -> str:
        """Who owns the set, in words."""
        if self.component is None:
            return "the project"
        if self.component == fd.BACKBONE_COMPONENT:
            return "the backbone"
        return f"capability {self.component}"

    def rule(self, rule_id: str) -> Rule | None:
        return self._rules_by_id.get(rule_id)

    @cached_property
    def _rules_by_id(self) -> dict[str, Rule]:
        return {rule.id: rule for rule in self.rules}


@dataclass(frozen=True)
class UnreadableRuleSet:
    """A rule-set file the pass cannot read as one: unreadable, no front matter, or unparsable."""

    path: str
    place: fd.RuleSetPlace
    problem: str  # completes "the rule-set file ..."


@dataclass(frozen=True)
class RuleSetDiscovery:
    """Every rule-set file the location rule claims, parsed, in path order."""

    places: tuple[fd.RuleSetPlace, ...]
    rule_sets: tuple[RuleSet, ...]
    unreadable: tuple[UnreadableRuleSet, ...]

    @property
    def rules(self) -> tuple[Rule, ...]:
        return tuple(rule for rule_set in self.rule_sets for rule in rule_set.rules)

    @cached_property
    def _by_name(self) -> dict[str, tuple[RuleSet, ...]]:
        grouped: dict[str, list[RuleSet]] = {}
        for rule_set in self.rule_sets:
            if rule_set.name is not None:
                grouped.setdefault(rule_set.name, []).append(rule_set)
        return {name: tuple(sets) for name, sets in grouped.items()}

    def sets_named(self, name: str) -> tuple[RuleSet, ...]:
        """The rule sets declaring `name`, in path order (more than one is a finding)."""
        return self._by_name.get(name, ())


# --- discovery -----------------------------------------------------------------


def discover_rule_sets(
    target_root: Path,
    settings: fd.FrictionSettings | None = None,
    tree: fd.RepositoryTree | None = None,
) -> RuleSetDiscovery:
    """Read every rule-set file the location rule claims, in path order.

    At one state, through discovery's tree (ADR-057 point 2): with a `tree` — a
    commit — the settings, the places, the files and their text are that
    state's; without one, the working tree's one listing, read from disk. The
    files are claimed as the walk claims them (`friction_discovery.rule_set_files`)
    and read as it reads them (`friction_discovery.document_texts`), so the reader
    and discovery find the same rule-set files at one state. A link is never read.
    """
    settings = settings if settings is not None else fd.read_friction_settings(target_root, tree)
    places = fd.rule_set_places(target_root, settings, tree)
    listing = tree if tree is not None else fd.working_tree(target_root)
    claimed = fd.rule_set_files(target_root, places, listing)
    texts = fd.document_texts(listing, sorted(claimed))
    rule_sets: list[RuleSet] = []
    unreadable: list[UnreadableRuleSet] = []
    for rel in sorted(claimed):
        text = texts[rel]
        if text is None:
            continue  # a link: never read as a document
        read = _read_rule_set(rel, claimed[rel], text)
        if isinstance(read, RuleSet):
            rule_sets.append(read)
        else:
            unreadable.append(read)
    return RuleSetDiscovery(places=places, rule_sets=tuple(rule_sets), unreadable=tuple(unreadable))


def _read_rule_set(
    rel: str, place: fd.RuleSetPlace, text: str | fd.ReadFailure
) -> RuleSet | UnreadableRuleSet:
    if isinstance(text, fd.ReadFailure):
        return UnreadableRuleSet(rel, place, f"cannot be read ({text.reason})")
    front_matter, body = document_parts.split_front_matter(text)
    if front_matter is None:
        return UnreadableRuleSet(
            rel,
            place,
            "has no front matter; a Markdown file in a rule-set place is a rule-set file, "
            "whose front matter holds its data",
        )
    data, duplicates, problem = _load_front_matter(front_matter)
    if problem is not None:
        return UnreadableRuleSet(rel, place, f"has front matter that does not parse ({problem})")
    if not isinstance(data, Mapping):
        return UnreadableRuleSet(rel, place, "has front matter that is not a mapping")
    data = bs.as_written(data)
    raw_rules: Any = data.get(fd.RULES_KEY)
    entries: Mapping[str, Any] = (
        cast("Mapping[str, Any]", raw_rules) if isinstance(raw_rules, Mapping) else {}
    )
    checks = _check_parts(data.get(CHECKS_KEY))
    rules = tuple(
        Rule(
            id=rule_id,
            path=rel,
            data=entry if isinstance(entry, Mapping) else {},
            section=document_parts.entry_section(body, rule_id),
            checks=checks.get(rule_id, ()),
        )
        for rule_id, entry in entries.items()
    )
    return RuleSet(
        path=rel,
        place=place,
        front_matter=data,
        body=body,
        rules=rules,
        sections=_sections(body),
        duplicate_keys=duplicates,
    )


def _check_parts(value: Any) -> dict[str, tuple[CheckPart, ...]]:
    """The declared check parts by rule id (`CHECKS_KEY`), read forgivingly: an entry
    without a text `check` and a text `part` is passed over, since the schema pass
    reports its shape."""
    if not isinstance(value, Mapping):
        return {}
    found: dict[str, tuple[CheckPart, ...]] = {}
    for rule_id, entries in cast("Mapping[Any, Any]", value).items():
        parts: list[CheckPart] = []
        for index, entry in enumerate(_list(entries)):
            declared: Mapping[str, Any] = (
                cast("Mapping[str, Any]", entry) if isinstance(entry, Mapping) else {}
            )
            check, part = declared.get("check"), declared.get("part")
            if isinstance(check, str) and isinstance(part, str):
                parts.append(CheckPart(check=check, part=part, index=index))
        if parts:
            found[str(rule_id)] = tuple(parts)
    return found


def _load_front_matter(text: str) -> tuple[Any, tuple[DuplicateKey, ...], str | None]:
    """(data, duplicate keys, problem). A duplicate key is reported, not fatal."""
    try:
        return _yaml.load(io.StringIO(text)), (), None
    except DuplicateKeyError:
        duplicates = _duplicate_keys(text)
        try:
            return _yaml_keeping_first.load(io.StringIO(text)), duplicates, None
        except YAMLError as exc:
            return None, (), _yaml_problem(exc)
    except YAMLError as exc:
        return None, (), _yaml_problem(exc)


def _duplicate_keys(text: str) -> tuple[DuplicateKey, ...]:
    """Every key written twice in one mapping, found on the composed node tree."""
    try:
        root = YAML(typ="safe").compose(io.StringIO(text))
    except YAMLError:
        return ()
    found: list[DuplicateKey] = []

    def walk(node: Node | None, pointer: str) -> None:
        if isinstance(node, MappingNode):
            lines: dict[str, list[int]] = {}
            first_values: dict[str, Node] = {}
            for key_node, value in node.value:
                if isinstance(key_node, ScalarNode):
                    # +1 for 1-based lines, +1 for the opening fence of the front matter.
                    lines.setdefault(key_node.value, []).append(key_node.start_mark.line + 2)
                    first_values.setdefault(key_node.value, value)
            found.extend(
                DuplicateKey(pointer, key, tuple(where))
                for key, where in lines.items()
                if len(where) > 1
            )
            for key, value in first_values.items():  # the value that is read
                walk(value, f"{pointer}/{_token(key)}")
        elif isinstance(node, SequenceNode):
            for index, item in enumerate(node.value):
                walk(item, f"{pointer}/{index}")

    walk(root, "")
    return tuple(found)


def _sections(body: str) -> tuple[Section, ...]:
    """The body headings that open with `RS-`, in order.

    Read by the one reading of where a part lies (`document_parts.body_headings`,
    `document_parts.heading_opens_with`), as the friction pass reads a rule's
    section, so the two find the same sections. A heading opens with a rule id
    only when it opens with the id as a whole token.
    """
    sections: list[Section] = []
    for heading in document_parts.body_headings(body):
        if not heading.title.startswith("RS-"):
            continue
        match = _HEADING_ID.match(heading.title)
        rule_id = match.group(1) if match else None
        if rule_id is not None and not document_parts.heading_opens_with(heading.title, rule_id):
            rule_id = None
        sections.append(Section(rule_id=rule_id, heading=heading.title))
    return tuple(sections)


# --- findings ------------------------------------------------------------------


class RuleSetFindingKind(Enum):
    """What a rule-set finding is about."""

    SCHEMA_UNAVAILABLE = "schema-unavailable"  # the tree ships no readable schema
    UNREADABLE = "unreadable"  # no front matter, or front matter that does not parse
    SHAPE = "shape"  # a JSON Schema violation
    UNKNOWN_KEY = "unknown-key"  # a key the schema does not know
    DUPLICATE_KEY = "duplicate-key"  # a key written twice in one mapping
    DUPLICATE_ID = "duplicate-id"  # a rule id written twice in `rules`
    MALFORMED_ID = "malformed-id"  # not `RS-<SET>-NNN`
    FOREIGN_SET_ID = "foreign-set-id"  # an id carrying another set's name
    REDEFINED_ID = "redefined-id"  # an inherited rule's id defined again
    DUPLICATE_SET_NAME = "duplicate-set-name"  # a set name another rule set declares
    MISSING_SECTION = "missing-section"  # data without a body section
    MISSING_DATA = "missing-data"  # a body section without data
    DUPLICATE_SECTION = "duplicate-section"  # two sections headed by one id
    MALFORMED_CONTAINER = "malformed-container"  # the container schema's or rule's error
    CONTAINER_REPORT = "container-report"  # an orphaned role block, an inert point block
    MISSING_ORIGIN = "missing-origin"  # an accepted rule without an origin
    INCOMPLETE_ORIGIN = "incomplete-origin"  # neither a complete quote nor a decision
    MISSING_DECISION = "missing-decision"  # the cited record does not exist
    DECISION_NOT_ACCEPTED = "decision-not-accepted"  # an accepted rule citing an unaccepted record
    UNRESOLVED_SOURCE_KIND = "unresolved-kind"  # a source of a kind nothing resolves
    MISSING_SOURCE = "missing-source"  # the cited source's resolver names no file for it
    UNANSWERED_SOURCE = "unanswered-source"  # the cited source's resolver gave no answer
    SUCCESSOR_NOT_FOUND = "successor-not-found"
    SUCCESSOR_OUT_OF_LINE = "successor-out-of-line"  # not in the set or one inheriting it
    INHERITED_SET_MISSING = "inherited-set-missing"
    INHERITANCE_NOT_ALLOWED = "inheritance-not-allowed"
    INHERITANCE_CYCLE = "inheritance-cycle"
    UNDECLARED_FILL = "undeclared-fill"
    DOUBLE_FILL = "double-fill"
    UNANCHORED_FILL = "unanchored-fill"  # a fill whose rule does not anchor to the rule it fills
    ORPHANED_FILL = "orphaned-fill"  # a fill of a superseded or withdrawn rule
    METHOD_SCOPE = "method-scope"  # a scope on a method rule set, which takes none
    UNKNOWN_SCOPE_TYPE = "scope-unknown-type"  # a scope naming a type no owner declares
    CHECK_FOR_NO_RULE = "check-for-no-rule"  # a check part declared for a rule the set lacks
    UNKNOWN_CHECK = "unknown-check"  # a backbone check or registered command that is not there
    PIN_CONFLICT = "pin-conflict"  # routes to one artefact pinning one set at different majors
    FILL_CONFLICT = "fill-conflict"  # the most specific sets bring different fills for a point


@dataclass(frozen=True)
class RuleSetFinding:
    """One finding: the file (`path`) or a rule (`path#id`), and a JSON Pointer inside it."""

    location: str
    pointer: str  # into the file's front matter, or into the rule's entry; "" for the whole
    severity: Severity
    kind: RuleSetFindingKind
    message: str

    @property
    def where(self) -> str:
        return f"{self.location} {self.pointer}".rstrip()


@dataclass(frozen=True)
class RuleSetValidation:
    """Outcome of the pass: what was found, and the discovery it ran over."""

    discovery: RuleSetDiscovery
    findings: tuple[RuleSetFinding, ...]

    @property
    def errors(self) -> tuple[RuleSetFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def reports(self) -> tuple[RuleSetFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.REPORT)

    @property
    def is_dormant(self) -> bool:
        """No rule-set file anywhere: nothing to judge."""
        return not self.discovery.rule_sets and not self.discovery.unreadable


def _error(location: str, pointer: str, kind: RuleSetFindingKind, message: str) -> RuleSetFinding:
    return RuleSetFinding(location, pointer, Severity.ERROR, kind, message)


def _report(location: str, pointer: str, kind: RuleSetFindingKind, message: str) -> RuleSetFinding:
    return RuleSetFinding(location, pointer, Severity.REPORT, kind, message)


# --- validation ----------------------------------------------------------------


def validate_rule_sets(target_root: Path) -> RuleSetValidation:
    """Run the pass over the project at `target_root`.

    A tree without a readable rule-set schema — one recorded before the schema
    landed — skips the kind and says so, never validating against a shape the
    tree never shipped (ADR-056 point 1).
    """
    discovery = discover_rule_sets(target_root)
    result = RuleSetValidation(discovery=discovery, findings=())
    if result.is_dormant:
        return result
    try:
        schema = bs.load_backbone_schema(target_root, SCHEMA_KIND)
    except (bs.BackboneSchemaMissing, bs.BackboneSchemaInvalid) as exc:
        reason = "is missing" if isinstance(exc, bs.BackboneSchemaMissing) else "does not load"
        location = str(bs.BACKBONE_SCHEMAS_DIR / f"{SCHEMA_KIND}.schema.json")
        message = (
            f"the rule-set schema {reason} in this tree, so rule-set files are not validated "
            f"(run `pkit sync`; `pkit schemas validate` reports a schema that does not load)."
        )
        finding = _report(location, "", RuleSetFindingKind.SCHEMA_UNAVAILABLE, message)
        return RuleSetValidation(discovery=discovery, findings=(finding,))

    catalogue = _Catalogue(target_root, discovery)
    findings: list[RuleSetFinding] = [
        _error(u.path, "", RuleSetFindingKind.UNREADABLE, f"the rule-set file {u.problem}.")
        for u in discovery.unreadable
    ]
    container_schema, note = _container_schema(target_root)
    if note is not None:
        findings.append(note)
    from project_kit import connections  # the resolver imports this module for its pins

    wiring = connections.container_wiring(target_root)
    scope_types = _scope_type_findings(target_root)
    for rule_set in discovery.rule_sets:
        findings.extend(_duplicate_key_findings(rule_set))
        findings.extend(_shape_findings(rule_set, schema))
        findings.extend(_scope_findings(rule_set, scope_types))
        findings.extend(_set_name_findings(rule_set, discovery))
        findings.extend(_id_findings(rule_set, catalogue))
        findings.extend(_join_findings(rule_set))
        if container_schema is not None:
            findings.extend(_container_findings(rule_set, container_schema, wiring))
        findings.extend(_origin_findings(rule_set, catalogue))
        findings.extend(_successor_findings(rule_set, catalogue))
        findings.extend(_inheritance_findings(rule_set, catalogue))
        findings.extend(_fill_findings(rule_set, catalogue))
        findings.extend(_check_part_findings(rule_set, catalogue))
    findings.extend(_cycle_findings(catalogue))
    findings.extend(_conflict_findings(reach(fd.shared_discovery(target_root), discovery)))
    return RuleSetValidation(discovery=discovery, findings=tuple(findings))


def _container_schema(target_root: Path) -> tuple[dict | None, RuleSetFinding | None]:
    """The tree's container schema, or a report saying the container check is skipped."""
    try:
        return bs.load_backbone_schema(target_root, "container"), None
    except (bs.BackboneSchemaMissing, bs.BackboneSchemaInvalid):
        location = str(bs.BACKBONE_SCHEMAS_DIR / "container.schema.json")
        message = (
            "the container schema is unavailable in this tree, so the container inside each "
            "rule is not checked (run `pkit sync`)."
        )
        return None, _report(location, "", RuleSetFindingKind.SCHEMA_UNAVAILABLE, message)


# --- per file: the front matter as written ----------------------------------


def _duplicate_key_findings(rule_set: RuleSet) -> Iterable[RuleSetFinding]:
    """A key written twice: a duplicate rule id under `rules`, else a duplicate key."""
    rules_pointer = f"/{fd.RULES_KEY}"
    for duplicate in rule_set.duplicate_keys:
        lines = ", ".join(str(line) for line in duplicate.lines)
        if duplicate.pointer == rules_pointer:
            yield _error(
                f"{rule_set.path}#{duplicate.key}",
                "",
                RuleSetFindingKind.DUPLICATE_ID,
                f"rule id {duplicate.key} is written {len(duplicate.lines)} times in `rules` "
                f"(lines {lines}); an id names one rule, is never renumbered and is never "
                f"reused (COR-051 point 3). Give the new rule the next free number.",
            )
        else:
            yield _error(
                rule_set.path,
                f"{duplicate.pointer}/{_token(duplicate.key)}",
                RuleSetFindingKind.DUPLICATE_KEY,
                f"key {duplicate.key!r} is written {len(duplicate.lines)} times (lines {lines}); "
                f"only the first is read.",
            )


def _shape_findings(rule_set: RuleSet, schema: Mapping[str, Any]) -> list[RuleSetFinding]:
    """The JSON Schema pass: unknown keys through the shared renderer, sorted by position."""
    registry = Registry().with_resource(
        uri=schema.get("$id", f"{SCHEMA_KIND}.schema.json"),
        resource=Resource.from_contents(schema, default_specification=DRAFT202012),
    )
    validator = Draft202012Validator(schema, registry=registry)
    findings: list[RuleSetFinding] = []
    for error in validator.iter_errors(rule_set.front_matter):
        findings.extend(_render_schema_error(rule_set, error))
    return sorted(findings, key=lambda f: (f.location, f.pointer, f.message))


def _render_schema_error(rule_set: RuleSet, error: ValidationError) -> list[RuleSetFinding]:
    path = [str(segment) for segment in error.absolute_path]
    schema_path = [str(segment) for segment in error.absolute_schema_path]
    if path == [fd.RULES_KEY] and "propertyNames" in schema_path:
        return [
            _error(
                f"{rule_set.path}#{error.instance}",
                "",
                RuleSetFindingKind.MALFORMED_ID,
                f"rule id {error.instance!r} is malformed: an id is `RS-<SET>-NNN` — the family "
                f"prefix, the rule set's name and a number of at least three digits, "
                f"zero-padded below 100 (COR-051 point 3).",
            )
        ]
    location, pointer = _locate(rule_set, path)
    unknown = bs.unknown_keys(error)
    if unknown:
        known = tuple((error.schema.get("properties") or {}).keys())
        return [
            _error(
                location,
                f"{pointer}/{_token(key)}",
                RuleSetFindingKind.UNKNOWN_KEY,
                bs.render_unknown_key(key, known),
            )
            for key in unknown
        ]
    # The status/successor coupling reads better said than as the schema's message.
    message = error.message
    if "dependentSchemas" in schema_path:
        pointer = "/successor"
        message = (
            "only a superseded rule names a successor: set `status: superseded`, or remove "
            "`successor` (COR-051 point 4)."
        )
    elif schema_path[-2:] == ["then", "required"]:
        message = "a superseded rule names its successor: add `successor` (COR-051 point 4)."
    return [_error(location, pointer, RuleSetFindingKind.SHAPE, message)]


def _locate(rule_set: RuleSet, path: Sequence[str]) -> tuple[str, str]:
    """(location, pointer): a rule's findings are placed on the rule, the rest on the file."""
    if len(path) >= 2 and path[0] == fd.RULES_KEY:
        return f"{rule_set.path}#{path[1]}", _pointer(path[2:])
    return rule_set.path, _pointer(path)


# --- per file: the scope -------------------------------------------------------


def _scope_findings(
    rule_set: RuleSet, scope_types: Mapping[str, list[RuleSetFinding]]
) -> Iterable[RuleSetFinding]:
    """What a set's scope gets wrong beyond its shape (COR-051 point 2): a scope on a
    method rule set, which takes none, and each type the scope names that no owner
    declares (COR-056 point 2), as discovery found it."""
    if rule_set.component is not None and fd.SCOPE_KEY in rule_set.front_matter:
        yield _error(
            rule_set.path,
            f"/{fd.SCOPE_KEY}",
            RuleSetFindingKind.METHOD_SCOPE,
            f"{rule_set.owner} ships this rule set, and a method rule set takes no scope: its "
            f"rules bind only through a set of the project's own that inherits it, so the "
            f"project keeps the choice not to inherit it (COR-051 points 2 and 7). Remove "
            f"`{fd.SCOPE_KEY}`.",
        )
    yield from scope_types.get(rule_set.path, [])


def _scope_type_findings(target_root: Path) -> dict[str, list[RuleSetFinding]]:
    """The type findings artefact discovery names this pass to report (ADR-057 point
    2), by rule-set file: each type a scope names that no owner declares, at the
    severity discovery's one table gives it (`friction_discovery.TYPE_FINDINGS`)."""
    out: dict[str, list[RuleSetFinding]] = {}
    for finding in fd.shared_types(target_root).reported_by(fd.RULE_SETS_MEMBER):
        out.setdefault(finding.file, []).append(
            RuleSetFinding(
                finding.file,
                finding.pointer,
                Severity(finding.severity.value),
                RuleSetFindingKind.UNKNOWN_SCOPE_TYPE,
                finding.message,
            )
        )
    return out


# --- per file: names and ids ---------------------------------------------------


def _set_name_findings(rule_set: RuleSet, discovery: RuleSetDiscovery) -> Iterable[RuleSetFinding]:
    """A set name another rule set, earlier by path, already declares (COR-051 point 3)."""
    if rule_set.name is None:
        return
    same = discovery.sets_named(rule_set.name)
    first = same[0]
    if first is rule_set:
        return
    yield _error(
        rule_set.path,
        "/rule-set",
        RuleSetFindingKind.DUPLICATE_SET_NAME,
        f"rule set {rule_set.name} is also declared by {first.path}; rule-set names are unique "
        f"among rule sets, so that every rule id names one rule (COR-051 point 3). Rename one "
        f"of them.",
    )


def _id_findings(rule_set: RuleSet, catalogue: _Catalogue) -> Iterable[RuleSetFinding]:
    """An id that carries another set's name: a redefined inherited rule, or a foreign id."""
    if rule_set.name is None:
        return
    for rule in rule_set.rules:
        set_name = rule.set_name
        if set_name is None or set_name == rule_set.name:
            continue
        inherited = next(
            (a for a in catalogue.ancestors(rule_set) if a.rule(rule.id) is not None), None
        )
        if inherited is not None:
            yield _error(
                rule.location,
                "",
                RuleSetFindingKind.REDEFINED_ID,
                f"{rule.id} is a rule of the inherited set {inherited.citation}; an inheriting set "
                f"takes inherited rules unchanged and never redefines one (COR-051 point 7). "
                f"To change it, propose the change to its owner, {inherited.owner}.",
            )
        else:
            yield _error(
                rule.location,
                "",
                RuleSetFindingKind.FOREIGN_SET_ID,
                f"{rule.id} carries set name {set_name}, but this file is rule set "
                f"{rule_set.name}; a rule's id carries its own set's name (COR-051 point 3).",
            )


# --- per file: the join between data and prose --------------------------------


def _join_findings(rule_set: RuleSet) -> Iterable[RuleSetFinding]:
    """Every rule has a section and every section has data (COR-051 point 2)."""
    counts: dict[str, int] = {}
    for section in rule_set.sections:
        if section.rule_id is None:
            yield _error(
                rule_set.path,
                "",
                RuleSetFindingKind.MALFORMED_ID,
                f"the body heading {section.heading!r} opens like a rule id but is not one; a "
                f"rule's section is headed by its id `RS-<SET>-NNN` and its title.",
            )
            continue
        counts[section.rule_id] = counts.get(section.rule_id, 0) + 1
    data_ids = {rule.id for rule in rule_set.rules}
    for rule in rule_set.rules:
        if rule.set_name is not None and rule.id not in counts:
            yield _error(
                rule.location,
                "",
                RuleSetFindingKind.MISSING_SECTION,
                f"{rule.id} has data but the body has no section headed by its id; the statement "
                f"lives in a section headed `{rule.id} — <title>` (COR-051 point 2).",
            )
    for rule_id, count in counts.items():
        location = f"{rule_set.path}#{rule_id}"
        if rule_id not in data_ids:
            yield _error(
                location,
                "",
                RuleSetFindingKind.MISSING_DATA,
                f"the body has a section headed {rule_id} but `rules` has no entry for it; every "
                f"rule's machine fields live in the front matter (COR-051 point 2).",
            )
        if count > 1:
            yield _error(
                location,
                "",
                RuleSetFindingKind.DUPLICATE_SECTION,
                f"{count} body sections are headed {rule_id}; each rule has one section.",
            )


# --- per file: the container inside each rule ----------------------------------


def _container_findings(
    rule_set: RuleSet, schema: Mapping[str, Any], wiring: bs.ContainerWiring
) -> Iterable[RuleSetFinding]:
    """The container rule applied inside each rule entry, read against the active
    wiring (ADR-056 point 2; COR-053 point 10)."""
    for rule in rule_set.rules:
        if bs.CONTAINER_KEY not in rule.data:
            continue
        for finding in bs.validate_container(rule.data, schema, wiring=wiring).findings:
            is_error = finding.severity is Severity.ERROR
            yield RuleSetFinding(
                location=rule.location,
                pointer=finding.location,
                severity=finding.severity,
                kind=(
                    RuleSetFindingKind.MALFORMED_CONTAINER
                    if is_error
                    else RuleSetFindingKind.CONTAINER_REPORT
                ),
                message=finding.message,
            )


# --- per file: origins ---------------------------------------------------------


def _origin_findings(rule_set: RuleSet, catalogue: _Catalogue) -> Iterable[RuleSetFinding]:
    """Origins, checked deterministically (COR-051 point 5)."""
    for rule in rule_set.rules:
        if "origin" not in rule.data:
            if rule.binds:
                yield _error(
                    rule.location,
                    "",
                    RuleSetFindingKind.MISSING_ORIGIN,
                    "an accepted rule carries an origin — when it was decided, by whom and why "
                    "(`date`, `by`, `why`), or a `decision` record (COR-051 point 5).",
                )
            continue
        origin = rule.origin
        if origin is None:
            continue  # not a mapping: the shape pass reports it
        yield from _origin_form_findings(rule, origin)
        yield from _decision_findings(rule, origin, catalogue)
        yield from _source_findings(rule, origin, catalogue)


def _origin_form_findings(rule: Rule, origin: Mapping[str, Any]) -> Iterable[RuleSetFinding]:
    quote = [name for name in QUOTE_FIELDS if name in origin]
    if "decision" in origin and quote:
        yield _error(
            rule.location,
            "/origin",
            RuleSetFindingKind.INCOMPLETE_ORIGIN,
            "an origin is either the decider's words (`date`, `by`, `why`) or a `decision` "
            f"record, not both; this one has `decision` and {_names(quote)}.",
        )
    elif rule.binds and "decision" not in origin and len(quote) < len(QUOTE_FIELDS):
        missing = [name for name in QUOTE_FIELDS if name not in origin]
        yield _error(
            rule.location,
            "/origin",
            RuleSetFindingKind.INCOMPLETE_ORIGIN,
            f"an accepted rule carries a complete origin, and this one lacks {_names(missing)}; "
            f"add them, or cite a `decision` record instead (COR-051 point 5).",
        )


def _decision_findings(
    rule: Rule, origin: Mapping[str, Any], catalogue: _Catalogue
) -> Iterable[RuleSetFinding]:
    record = origin.get("decision")
    if not isinstance(record, str) or _DECISION_ID_RE.fullmatch(record) is None:
        return  # absent, or malformed: the shape pass reports it
    found, status = catalogue.decision(record)
    if found is None:
        yield _error(
            rule.location,
            "/origin/decision",
            RuleSetFindingKind.MISSING_DECISION,
            f"cites decision record {record}, which does not exist (COR-051 point 5).",
        )
    elif rule.binds and status != ACCEPTED:
        yield _error(
            rule.location,
            "/origin/decision",
            RuleSetFindingKind.DECISION_NOT_ACCEPTED,
            f"an accepted rule cites {record}, whose status is {status or 'unreadable'}; a "
            f"rule is accepted only on accepted grounds — accept the record first, or keep the "
            f"rule proposed (COR-051 point 5).",
        )


def _source_findings(
    rule: Rule, origin: Mapping[str, Any], catalogue: _Catalogue
) -> Iterable[RuleSetFinding]:
    """A cited source resolves through the anchor kind a capability registers for it
    (COR-051 point 5), judged by the one anchor-kind registry (ADR-057 point 2) and
    resolved by the resolver the kind registers, as the friction checks resolve an
    anchor of it (`AnchorKinds`).

    Validation fails unless a cited source resolves (COR-051 point 5), with one
    carve-out: a source kind with no resolver that may run — nothing installed
    registers it, or its registration is refused, which fails at the
    registration — is reported, never silently passed. A registered resolver
    that ran is not that case:

    - one that names no file for the source does not resolve it
      (`MISSING_SOURCE`): the citation is the project's to correct;
    - one that gives no answer has not resolved it either (`UNANSWERED_SOURCE`):
      the source could not be checked, and a pass nobody earned costs more than
      the second run a failure costs (COR-055 point 6).
    """
    source = origin.get("source")
    kind = source.get("kind") if isinstance(source, Mapping) else None
    if not isinstance(kind, str) or not kind:
        return  # absent, or malformed: the shape pass reports it
    reason = _source_kind_problem(kind, catalogue.anchor_kinds)
    if reason is not None:
        yield _report(
            rule.location,
            "/origin/source",
            RuleSetFindingKind.UNRESOLVED_SOURCE_KIND,
            f"source kind {kind!r} is unresolved: {reason}, so the source is not checked "
            f"(COR-051 point 5; COR-050 point 2).",
        )
        return
    value: Any = cast("Mapping[str, Any]", source).get("value")
    if not isinstance(value, str) or not value:
        return  # malformed: the shape pass reports it
    resolution = catalogue.resolutions.resolve(fd.Anchor(kind, value))
    resolver = catalogue.anchor_kinds[kind]
    if resolution.no_answer is not None:
        yield _error(
            rule.location,
            "/origin/source",
            RuleSetFindingKind.UNANSWERED_SOURCE,
            f"source {kind}:{value} could not be checked: its resolver gave no answer — "
            f"{resolution.no_answer}. If it overran its time or its environment is not "
            f"provisioned, run again (after `pkit sync`); otherwise the resolver "
            f"`{resolver.command}` of {resolver.capability} needs mending (COR-051 point 5; "
            f"COR-050 point 2).",
        )
    elif not resolution.paths:
        yield _error(
            rule.location,
            "/origin/source",
            RuleSetFindingKind.MISSING_SOURCE,
            f"cites source {kind}:{value}, which does not resolve: the resolver "
            f"`{resolver.command}` that {resolver.capability} registers for `{kind}` names no "
            f"file for it (COR-051 point 5).",
        )


def _source_kind_problem(kind: str, registry: Mapping[str, fd.ResolverCommand]) -> str | None:
    """Why a source of `kind` is unresolved, or None when the registry resolves it.

    A source is of a kind some capability resolves as an anchor kind (COR-051
    point 5), so the kinds the backbone resolves itself are not source kinds.
    Every other kind takes the verdict the friction checks give an anchor of
    that kind (`unresolved_kind_reason`): unregistered, registered by two
    capabilities, or refused — its command names no leaf, or lacks the query
    contract (COR-050 point 2).
    This validator runs no resolver of its own: a kind that passes is resolved
    by the registry's resolver (`AnchorKinds`), so a source is never silently
    passed.
    """
    if kind in fd.CORE_ANCHOR_KINDS:
        return (
            "the backbone resolves it as an anchor, never as a source — a source is of a kind "
            "an installed capability registers a resolver for"
        )
    return fd.unresolved_kind_reason(kind, registry)


# --- per file: successors ------------------------------------------------------


def _successor_findings(rule_set: RuleSet, catalogue: _Catalogue) -> Iterable[RuleSetFinding]:
    """Every successor exists, in the same set or in a set that inherits it (COR-051 point 4)."""
    for rule in rule_set.rules:
        successor = rule.successor
        if successor is None:
            continue
        if successor.rule == rule.id:
            yield _error(
                rule.location,
                "/successor",
                RuleSetFindingKind.SUCCESSOR_NOT_FOUND,
                f"{rule.id} names itself as its successor; a successor is the rule that "
                f"replaces it.",
            )
            continue
        target_set, _target, problem = catalogue.locate(successor)
        if problem is not None or target_set is None:
            yield _error(
                rule.location,
                "/successor",
                RuleSetFindingKind.SUCCESSOR_NOT_FOUND,
                f"names successor {successor}, but {problem} (COR-051 point 4).",
            )
        elif target_set is not rule_set and rule_set not in catalogue.ancestors(target_set):
            yield _error(
                rule.location,
                "/successor",
                RuleSetFindingKind.SUCCESSOR_OUT_OF_LINE,
                f"names successor {successor}, a rule of {target_set.citation}, which does not "
                f"inherit {rule_set.citation}; a successor sits in the same rule set, or in a "
                f"set that inherits it (COR-051 point 4).",
            )


# --- per file: inheritance -----------------------------------------------------


def _inheritance_findings(rule_set: RuleSet, catalogue: _Catalogue) -> Iterable[RuleSetFinding]:
    """Each pin names an existing set that this set may inherit (COR-051 point 7).

    Whether the pinned major is the set's is a version relation, reported with
    the others under `versions` (`pin_checks`; `connections.rule_set_pin_findings`).
    """
    for index, pin in rule_set.pins:
        pointer = f"/inherits/{index}"
        parent, problem = catalogue.resolve_pin(pin)
        if problem is not None:
            yield _error(rule_set.path, pointer, RuleSetFindingKind.INHERITED_SET_MISSING, problem)
        if parent is None:
            continue
        refusal = catalogue.inheritance_refusal(rule_set, parent)
        if refusal is not None:
            yield _error(
                rule_set.path, pointer, RuleSetFindingKind.INHERITANCE_NOT_ALLOWED, refusal
            )


def _fill_findings(rule_set: RuleSet, catalogue: _Catalogue) -> Iterable[RuleSetFinding]:
    """Fills name points that inherited rules offer, each filled at most once, and
    each filling rule anchors to the rule it fills (COR-051 point 7).

    A superseded or withdrawn rule binds nothing, so its fills are history:
    they are neither checked nor counted. An orphaned fill is to be removed,
    so its anchor is not asked for.
    """
    ancestors = catalogue.ancestors(rule_set)
    for rule in rule_set.rules:
        if rule.is_retired:
            continue
        for index, reference in rule.fills:
            pointer = f"/fills/{index}"
            target_set, target, problem = catalogue.locate(reference)
            if problem is not None or target_set is None or target is None:
                yield _error(
                    rule.location,
                    pointer,
                    RuleSetFindingKind.UNDECLARED_FILL,
                    f"fills {reference}, but {problem}; a rule fills only the extension points "
                    f"inherited rules offer (COR-051 point 7).",
                )
            elif target_set not in ancestors:
                yield _error(
                    rule.location,
                    pointer,
                    RuleSetFindingKind.UNDECLARED_FILL,
                    f"fills {reference}, but {target_set.citation} is not a set "
                    f"{rule_set.citation} inherits; a rule fills only the extension points "
                    f"inherited rules offer (COR-051 point 7).",
                )
            elif target.is_retired:
                instead = ", or fill a point its successor offers" if target.successor else ""
                yield _report(
                    rule.location,
                    pointer,
                    RuleSetFindingKind.ORPHANED_FILL,
                    f"fills {reference}, but {target.id} is {target.status}, so the fill is "
                    f"orphaned: remove it{instead} (COR-051 point 7).",
                )
            elif not _anchors_to(rule, target, catalogue):
                cited = target_set.cite(target.id)
                block = f"{bs.CONTAINER_KEY}.{fd.FRICTION_KEY}.anchors.{ARTEFACT_ANCHOR_KIND}"
                yield _error(
                    rule.location,
                    pointer,
                    RuleSetFindingKind.UNANCHORED_FILL,
                    f"fills {reference}, but {rule.id} does not anchor to {cited}; a filling "
                    f"rule anchors to the rule it fills, so a change to the inherited rule flags "
                    f"the fill — add {cited} to `{block}` (COR-051 point 7).",
                )
    yield from _double_fill_findings(rule_set, catalogue)


def _anchors_to(rule: Rule, target: Rule, catalogue: _Catalogue) -> bool:
    """Whether one of `rule`'s artefact anchors names `target`.

    An anchor names a rule when it resolves to it as a citation does — bare,
    or with the owning component in front — never through an extension point:
    the rule is the artefact, a point of it is not.
    """
    for value in rule.anchors(ARTEFACT_ANCHOR_KIND):
        reference = parse_rule_reference(value)
        if reference is None or reference.point is not None:
            continue
        _set, found, problem = catalogue.locate(reference)
        if problem is None and found is target:
            return True
    return False


def _double_fill_findings(rule_set: RuleSet, catalogue: _Catalogue) -> Iterable[RuleSetFinding]:
    """A point filled twice along the chain, reported where the second fill arrives.

    The chain of a set is the set and every set it inherits, each once. A
    double fill already present in one of the parents' chains is that
    parent's finding, so it is reported once, not on every descendant.
    """
    parents = catalogue.parents(rule_set)
    for point, fills in catalogue.fills_along(rule_set).items():
        if len(fills) < 2:
            continue
        if any(len(catalogue.fills_along(parent).get(point, ())) >= 2 for parent in parents):
            continue
        own = [f for f in fills if f.rule_set is rule_set]
        by = ", ".join(f"{f.rule.id} ({f.rule_set.citation})" for f in fills)
        message = (
            f"extension point {point} is filled {len(fills)} times along the inheritance chain "
            f"of {rule_set.citation}: by {by}; each point is filled at most once (COR-051 "
            f"point 7)."
        )
        if own:
            last = own[-1]
            yield _error(
                last.rule.location, f"/fills/{last.index}", RuleSetFindingKind.DOUBLE_FILL, message
            )
        else:
            yield _error(rule_set.path, "/inherits", RuleSetFindingKind.DOUBLE_FILL, message)


def _check_part_findings(rule_set: RuleSet, catalogue: _Catalogue) -> Iterable[RuleSetFinding]:
    """The parts of its rules a set declares checks enforce (COR-051 point 2).

    The rule's owner declares the part beside the rule, so a declaration for
    a rule the set does not hold is an error. A check is admitted when it is
    the backbone's, a command a component registers in its package metadata,
    or the project's own tool. One naming a backbone check that does not
    exist, or a command no installed component registers, is reported
    without failing: that part goes back to whoever judges the rest of the
    rule. A project's own tool is trusted by its name.
    """
    declared = rule_set.front_matter.get(CHECKS_KEY)
    if not isinstance(declared, Mapping):
        return
    for raw_id in cast("Mapping[Any, Any]", declared):
        rule_id = str(raw_id)
        if rule_set.rule(rule_id) is None and re.fullmatch(RULE_ID_PATTERN, rule_id):
            yield _error(
                rule_set.path,
                f"/{CHECKS_KEY}/{_token(rule_id)}",
                RuleSetFindingKind.CHECK_FOR_NO_RULE,
                f"declares a part a check enforces for {rule_id}, which is not a rule of "
                f"{rule_set.citation}; a rule's owner declares that part beside the rule, in "
                f"the set that holds it (COR-051 point 2).",
            )
    for rule in rule_set.rules:
        for part in rule.checks:
            problem = catalogue.check_problem(part)
            if problem is not None:
                yield _report(
                    rule_set.path,
                    f"/{CHECKS_KEY}/{_token(rule.id)}/{part.index}/check",
                    RuleSetFindingKind.UNKNOWN_CHECK,
                    f"{rule.id} declares a part the check `{part.check}` enforces, but "
                    f"{problem}; until it is there, that part goes back to whoever judges the "
                    f"rest of the rule (COR-051 point 2).",
                )


def _conflict_findings(answer: Reach) -> list[RuleSetFinding]:
    """The conflicts between the routes to one artefact, as the walk found them (COR-051
    point 7; `reach`): one set pinned at different majors, and the most specific sets
    bringing different fills for one extension point. Each is an error on the artefact,
    naming both routes; the pass computes neither itself."""
    findings: list[RuleSetFinding] = []
    for location, found in sorted(answer.by_location.items()):
        for conflict in found.conflicts:
            if isinstance(conflict, PinConflict):
                pins = ", ".join(
                    f"{by.citation} pins {pin} ({by.path})" for by, _index, pin in conflict.pins
                )
                findings.append(
                    _error(
                        location,
                        "",
                        RuleSetFindingKind.PIN_CONFLICT,
                        f"routes to this artefact pin {conflict.rule_set.citation} at different "
                        f"majors: {pins}; review {conflict.rule_set.citation} at version "
                        f"{conflict.rule_set.version} and update the pins together (COR-051 "
                        f"point 7).",
                    )
                )
            else:
                brought = ", ".join(
                    f"{by.citation} brings "
                    + (
                        " and ".join(held.cite(rule.id) for held, rule in rules)
                        if rules
                        else "none"
                    )
                    for by, rules in conflict.brought
                )
                findings.append(
                    _error(
                        location,
                        "",
                        RuleSetFindingKind.FILL_CONFLICT,
                        f"the most specific sets whose scope selects this artefact bring "
                        f"different fills for {conflict.point}: {brought}; no fill binds here "
                        f"until they agree (COR-051 point 7).",
                    )
                )
    return findings


def _cycle_findings(catalogue: _Catalogue) -> list[RuleSetFinding]:
    """Rule sets inheriting each other in a cycle, each cycle reported once."""
    findings: list[RuleSetFinding] = []
    for cycle in catalogue.cycles():
        head = cycle[0]
        shown = " -> ".join(s.citation for s in [*cycle, head])
        what = "inherits itself" if len(cycle) == 1 else "is part of an inheritance cycle"
        findings.append(
            _error(
                head.path,
                "/inherits",
                RuleSetFindingKind.INHERITANCE_CYCLE,
                f"rule set {head.citation} {what}: {shown}; inheritance has no order in which "
                f"a cycle's rules could apply — remove one of the pins.",
            )
        )
    return findings


# --- resolution ----------------------------------------------------------------


@dataclass(frozen=True)
class _Fill:
    """A valid fill: the filling rule, the index of the fill as written, the point it fills."""

    rule_set: RuleSet
    rule: Rule
    index: int
    point_key: str  # `RS-<SET>-NNN#<point>`, without the component


class _Catalogue:
    """The rule sets of one repository state, indexed for the cross-file checks.

    Every answer is computed once and kept: ancestors, the fills along a
    chain, a record's status, a capability's declared dependencies, the
    registered anchor kinds.
    """

    def __init__(self, target_root: Path, discovery: RuleSetDiscovery) -> None:
        self.target_root = target_root
        self.discovery = discovery
        self._parents: dict[str, tuple[RuleSet, ...]] = {}
        self._ancestors: dict[str, tuple[RuleSet, ...]] = {}
        self._fills: dict[str, dict[str, list[_Fill]]] = {}
        self._decisions: dict[str, tuple[Path | None, str | None]] = {}
        self._requires: dict[str, frozenset[str]] = {}

    # -- rules and pins

    def locate(self, reference: RuleReference) -> tuple[RuleSet | None, Rule | None, str | None]:
        return locate_rule(self.discovery, reference)

    def resolve_pin(self, pin: Pin) -> tuple[RuleSet | None, str | None]:
        return resolve_pin(self.discovery, pin)

    def parents(self, rule_set: RuleSet) -> tuple[RuleSet, ...]:
        """The sets `rule_set` pins, resolved, in pin order."""
        if rule_set.path not in self._parents:
            found: list[RuleSet] = []
            for _index, pin in rule_set.pins:
                parent, _problem = self.resolve_pin(pin)
                if parent is not None and parent not in found:
                    found.append(parent)
            self._parents[rule_set.path] = tuple(found)
        return self._parents[rule_set.path]

    def ancestors(self, rule_set: RuleSet) -> tuple[RuleSet, ...]:
        """Every set `rule_set` inherits, directly or not, each once, nearest first.

        Never `rule_set` itself, even inside a cycle (the cycle is reported).
        """
        if rule_set.path not in self._ancestors:
            found: list[RuleSet] = []
            queue = list(self.parents(rule_set))
            while queue:
                current = queue.pop(0)
                if current is rule_set or current in found:
                    continue
                found.append(current)
                queue.extend(self.parents(current))
            self._ancestors[rule_set.path] = tuple(found)
        return self._ancestors[rule_set.path]

    def cycles(self) -> list[tuple[RuleSet, ...]]:
        """Inheritance cycles, each once, rotated to start at its member first by path.

        A depth-first walk in path order finds a cycle each time a pin leads
        back into the walk's own path; the same cycle met from two sides is
        reported once.
        """
        order = list(self.discovery.rule_sets)
        position = {id(rule_set): i for i, rule_set in enumerate(order)}
        white, grey, black = 0, 1, 2
        colour = [white] * len(order)
        seen: set[tuple[int, ...]] = set()
        found: list[tuple[RuleSet, ...]] = []
        for start in range(len(order)):
            if colour[start] != white:
                continue
            colour[start] = grey
            path = [start]
            stack = [iter(self.parents(order[start]))]
            while stack:
                parent = next(stack[-1], None)
                if parent is None:
                    colour[path.pop()] = black
                    stack.pop()
                    continue
                i = position[id(parent)]
                if colour[i] == grey:
                    cycle = path[path.index(i) :]
                    pivot = min(range(len(cycle)), key=lambda k: order[cycle[k]].path)
                    rotated = tuple(cycle[pivot:] + cycle[:pivot])
                    if rotated not in seen:
                        seen.add(rotated)
                        found.append(tuple(order[k] for k in rotated))
                elif colour[i] == white:
                    colour[i] = grey
                    path.append(i)
                    stack.append(iter(self.parents(parent)))
        return found

    def inheritance_refusal(self, child: RuleSet, parent: RuleSet) -> str | None:
        """Why `child` may not inherit `parent`, or None (COR-051 point 7; COR-030)."""
        if child.component is None or parent is child:
            return None  # a project rule set may inherit any; a self-pin is a cycle
        if parent.component is None:
            return (
                f"{child.citation} is a method rule set and cannot inherit the project rule set "
                f"{parent.citation}: a component ships to every project and cannot depend on "
                f"one project's rules."
            )
        if parent.component == fd.BACKBONE_COMPONENT or parent.component == child.component:
            return None  # the backbone's sets are inheritable by all; a component's own too
        if child.component == fd.BACKBONE_COMPONENT:
            return (
                f"the backbone's rule set {child.citation} cannot inherit {parent.citation}: the "
                f"backbone does not depend on a capability."
            )
        if parent.component in self.requires(child.component):
            return None
        return (
            f"capability {child.component} inherits {parent.citation} but does not declare a "
            f"required dependency on capability {parent.component}: add it to "
            f"`requires_capabilities` in .pkit/capabilities/{child.component}/package.yaml, "
            f"without `optional: true` (COR-030; COR-051 point 7)."
        )

    def fills_along(self, rule_set: RuleSet) -> dict[str, list[_Fill]]:
        """The valid fills of the set and of every set it inherits, by extension point."""
        if rule_set.path not in self._fills:
            chain: dict[str, list[_Fill]] = {}
            for member in (rule_set, *self.ancestors(rule_set)):
                for fill in self._valid_fills(member):
                    chain.setdefault(fill.point_key, []).append(fill)
            self._fills[rule_set.path] = chain
        return self._fills[rule_set.path]

    def _valid_fills(self, rule_set: RuleSet) -> Iterable[_Fill]:
        """The set's own fills that name a point an inherited rule offers.

        A retired rule's fills bind nothing and are left out.
        """
        ancestors = self.ancestors(rule_set)
        for rule in rule_set.rules:
            if rule.is_retired:
                continue
            for index, reference in rule.fills:
                target_set, target, problem = self.locate(reference)
                if problem is None and target is not None and target_set in ancestors:
                    yield _Fill(rule_set, rule, index, reference.point_key)

    # -- the repository

    @cached_property
    def anchor_kinds(self) -> dict[str, fd.ResolverCommand]:
        """The anchor kinds installed capabilities register, from the one registry
        the friction checks read (`registered_anchor_kinds`; ADR-057 point 2)."""
        return fd.registered_anchor_kinds(self.target_root)

    @cached_property
    def resolutions(self) -> fd.AnchorKinds:
        """The cited sources as their kinds' resolvers answer them — each resolver run
        once per value for the pass, as the friction checks run them, and its answer
        read against the working tree's one listing, which validation reads."""
        return fd.AnchorKinds(
            self.target_root,
            self.anchor_kinds,
            frozenset(fd.working_tree(self.target_root).files()),
        )

    def decision(self, record: str) -> tuple[Path | None, str | None]:
        """(the record's file, its status) for a cited decision id, or (None, None)."""
        if record not in self._decisions:
            path = _decision_file(self.target_root, record)
            status = _front_matter_status(path) if path is not None else None
            self._decisions[record] = (path, status)
        return self._decisions[record]

    def check_problem(self, part: CheckPart) -> str | None:
        """Why a declared check is not there, or `None` (`CheckPresence.problem`)."""
        return self.presence.problem(part)

    @cached_property
    def presence(self) -> CheckPresence:
        return CheckPresence(self.target_root)

    def requires(self, capability: str) -> frozenset[str]:
        """The capabilities `capability` declares required in `requires_capabilities`
        (COR-030). An optional dependency may be absent, so it admits no inheritance
        (COR-051 point 7)."""
        if capability not in self._requires:
            source = caps.find_capability_in_repo(self.target_root, capability)
            names = (
                frozenset(
                    dep.name for dep in source.package.requires_capabilities if not dep.optional
                )
                if source is not None
                else frozenset()
            )
            self._requires[capability] = names
        return self._requires[capability]


class CheckPresence:
    """Whether each declared check is there (COR-051 point 2; ADR-057 point 2), at one
    state. A component's check is there when a component installed at that state
    registers the command in its package metadata: the working tree's, or with `tree` the
    commit's. A backbone check is there when the `pkit` tool that runs has the command,
    whatever the state, since the tool ships in the binary and no commit holds it. The
    project's own tool is trusted by its name. Validation reports a check that is not
    there, and the reading commands give the same answer on each declared part
    (`rule_set_reading`). Every answer is read once and kept."""

    def __init__(self, target_root: Path, tree: fd.RepositoryTree | None = None) -> None:
        self.target_root = target_root
        self.tree = tree

    def problem(self, part: CheckPart) -> str | None:
        """Why a declared check is not there, or `None` when it is, or is trusted."""
        if part.owner is None:
            return None
        command = tuple(part.name.split())
        if part.owner == BACKBONE_OWNER:
            if command in self.backbone_commands:
                return None
            return f"the backbone has no check `pkit {part.name}`"
        registered = self.component_commands.get(part.owner)
        if registered is None:
            return f"no installed component is named {part.owner}"
        if command in registered:
            return None
        return f"{part.owner} registers no command `{part.name}` in its package metadata"

    @cached_property
    def backbone_commands(self) -> frozenset[tuple[str, ...]]:
        """Every command of the `pkit` tool, by its words: what a backbone check is named by."""
        from project_kit.cli import main  # the CLI imports this module

        return frozenset(_command_paths(main, ()))

    @cached_property
    def component_commands(self) -> dict[str, frozenset[tuple[str, ...]]]:
        """Each registered component's commands at this state, by their words, as the
        dispatcher reads what its package metadata registers (`command_runner`). A package
        that does not read registers nothing here, as it registers nothing there."""
        from project_kit.command_runner import COMMANDS_KEY, commands_of, registered_commands
        from project_kit.package_validate import installed_package_files

        if self.tree is not None:
            return {
                name: frozenset(commands_of(component_dir, package.get(COMMANDS_KEY)))
                for name, component_dir, package in fd.installed_packages_at(
                    self.target_root, self.tree
                )
            }
        return {
            name: frozenset(registered_commands(component_dir))
            for name, component_dir, _package in installed_package_files(self.target_root)
        }


def resolve_pin(discovery: RuleSetDiscovery, pin: Pin) -> tuple[RuleSet | None, str | None]:
    """(the pinned set, None), or (None, why not).

    The address must be the set's: a method set with its component, a project
    set bare (COR-051 point 6). (None, None) when two files declare the name
    under the same owner: the duplicate-name finding already reports that, so
    the pin adds nothing.
    """
    named = discovery.sets_named(pin.set_name)
    owned = [s for s in named if s.component == pin.component]
    if len(owned) == 1:
        return owned[0], None
    if owned:
        return None, None
    if not named:
        return None, (
            f"inherits {pin}, but no rule set is named {pin.set_name} in this repository "
            f"(COR-051 point 7)."
        )
    other = named[0]
    wanted = "a project rule set" if pin.component is None else f"a rule set of {pin.component}"
    return None, (
        f"inherits {pin}, but {pin.set_name} is not {wanted}: it belongs to {other.owner} — "
        f"write the pin as {other.citation}@{pin.major} (a method rule set is cited with its "
        f"component's name, a project one bare; COR-051 point 6)."
    )


@dataclass(frozen=True)
class PinCheck:
    """One inheritance pin that names an existing rule set: a version relation.

    Inheriting a set pins its major (COR-051 point 7); a newer major fails
    validation until the inheriting set's owner reviews it and updates the pin.
    `pkit validate` reports it with the other version relations, under
    `versions` (`connections.rule_set_pin_findings`); `pkit status` shows
    each such pin with its fix.
    """

    rule_set: RuleSet  # the inheriting set
    index: int  # the pin's index in `inherits`, as written
    pin: Pin
    inherited: RuleSet

    @property
    def pointer(self) -> str:
        return f"/inherits/{self.index}"

    @property
    def repinned(self) -> Pin | None:
        """The pin the inherited set's major now calls for; None while the pin holds.

        An unreadable inherited version is the inherited file's shape finding,
        so it asks for no new pin.
        """
        major = self.inherited.major
        if major is None or major == self.pin.major:
            return None
        return replace(self.pin, major=major)

    @property
    def behind(self) -> bool:
        """Whether the pin is behind its set: the set has moved on to a newer major
        (COR-051 point 7). No rule binds through a pin behind its set (`reach`). A pin
        ahead of its set is not behind, and `problem` reports it as a pin that does not
        hold. Nor is a pin whose set's version cannot be read: that is the inherited
        set's shape finding."""
        major = self.inherited.major
        return major is not None and self.pin.major < major

    @property
    def fix(self) -> str | None:
        """The edit that re-pins, once the inherited set has moved on; None while the pin holds."""
        repinned = self.repinned
        if repinned is None:
            return None
        return (
            f"review what changed in {self.inherited.citation}, then update the pin to "
            f"{repinned} in `inherits` of {self.rule_set.path}"
        )

    @property
    def problem(self) -> str | None:
        """Why the pin no longer holds, naming the new major and the fix; None while it does."""
        if self.repinned is None:
            return None
        return (
            f"pins {self.pin}, but {self.inherited.citation} is at version "
            f"{self.inherited.version}, major {self.inherited.major}; {self.fix} (COR-051 point 7)."
        )


def pin_checks(discovery: RuleSetDiscovery) -> tuple[PinCheck, ...]:
    """Every pin that names an existing rule set, in path and written order.

    A pin naming no set, or a set it may not inherit, is the rule-sets pass's
    finding; here it is simply not a check.
    """
    checks: list[PinCheck] = []
    for rule_set in discovery.rule_sets:
        for index, pin in rule_set.pins:
            inherited, _problem = resolve_pin(discovery, pin)
            if inherited is not None:
                checks.append(PinCheck(rule_set, index, pin, inherited))
    return tuple(checks)


# --- where accepted rules bind: the reach walk (COR-051 point 7; ADR-057 point 2) -----


@dataclass(frozen=True)
class Binding:
    """One accepted rule that binds on an artefact (COR-051 point 7).

    `covering` are the sets of the project's own whose scope selects the
    artefact, and from which a route leads to the rule's set with no pin on
    it behind its set, in path order. `fills` are the extension points the
    rule binds on the artefact as the fill of, each as cited
    (`[<component>:]RS-<SET>-NNN#<point>`), and empty for a rule that fills none.
    """

    rule: Rule
    rule_set: RuleSet
    covering: tuple[RuleSet, ...]
    fills: tuple[str, ...] = ()


@dataclass(frozen=True)
class PinConflict:
    """Routes to one artefact that pin one set at different majors (COR-051 point 7).

    `pins` are each pin on those routes that names the set: the set that pins
    it, the pin's index in that set's `inherits`, and the pin, in path order.
    """

    rule_set: RuleSet
    pins: tuple[tuple[RuleSet, int, Pin], ...]


@dataclass(frozen=True)
class FillConflict:
    """The most specific sets reaching one artefact bring different fills for one
    extension point, a fill against none included (COR-051 point 7).

    `point` is the extension point as cited; `brought` is each most specific
    set, in path order, with the accepted fills its chain brings for the point,
    each with the set holding it (none, one, or more where a chain fills it
    twice). No fill binds while it stands.
    """

    point: str
    brought: tuple[tuple[RuleSet, tuple[tuple[RuleSet, Rule], ...]], ...]


Conflict = PinConflict | FillConflict


@dataclass(frozen=True)
class HeldRule:
    """An accepted rule that a pin behind its set holds back from an artefact (COR-051
    point 7).

    Every route from the artefact to the rule's set passes a pin behind its set, so the
    rule binds nothing there until the pin is updated. A reviewer may still report a
    break of it, as a finding that informs (COR-057 point 1). `pins` are the pins
    behind their sets that lead towards the rule's set from the artefact's routes: the
    set that pins, the pin's index in that set's `inherits`, and the pin, in path order.
    """

    rule: Rule
    rule_set: RuleSet
    pins: tuple[tuple[RuleSet, int, Pin], ...]


@dataclass(frozen=True)
class ArtefactReach:
    """The walk's answer for one artefact: the accepted rules that bind on it, in path
    and written order, the conflicts between its routes, and the accepted rules that
    pins behind their sets hold back from it, in path and written order."""

    bindings: tuple[Binding, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    held: tuple[HeldRule, ...] = ()


_NO_REACH = ArtefactReach()


@dataclass(frozen=True)
class Reach:
    """The walk's answer for one state (`reach`): each artefact on which a rule binds,
    whose routes conflict, or from which a pin behind its set holds a rule back, by
    location. Any other artefact has no binding rule."""

    by_location: Mapping[str, ArtefactReach]

    def of(self, location: str) -> ArtefactReach:
        return self.by_location.get(location, _NO_REACH)


def reach(discovery: fd.Discovery, rule_sets: RuleSetDiscovery) -> Reach:
    """Which accepted rules bind on each artefact of one state (COR-051 point 7).

    The one home of that answer (ADR-057 point 2), over the artefacts
    discovery found at one state and the rule sets read from the same state.
    A route starts at a set of the project's own whose scope selects the
    artefact — discovery's covering function says which do
    (`friction_discovery.covering_rule_sets`) — and follows what the set
    inherits, pin by pin. It passes only through sets whose own scope, where
    they have one, also selects the artefact. A method rule set takes no
    scope, so it starts no route and narrows none (COR-051 point 2).

    An accepted rule binds when a route leads to its set with no pin on it
    behind its set; whether a pin is behind is the pin check's
    (`PinCheck.behind`). A superseded or withdrawn rule binds nothing, so a
    successor binds where its own set is reached. A filling rule binds as
    the fill of an extension point only where the rule it fills binds
    through the filling set, and only while both are accepted. The most
    specific sets the offering rule binds through decide each point: those no
    other such set inherits. Where they bring different fills, a fill
    against none included, the answer names the conflict and no fill binds.
    The answer also names routes to one artefact that pin one set at
    different majors. That conflict holds back no binding: a rule binds
    through a route whose pins are not behind. Validation reports both
    conflicts from this answer (`validate_rule_sets`). The answer also names
    each accepted rule that only routes through a pin behind its set reach,
    which binds nothing (`HeldRule`).

    A rule that fills binds only as a fill, so one whose fills name no point
    an inherited rule offers binds nowhere. A most specific set brings the
    fill its chain holds, whatever its pins, where the fill binds through
    the filling set. Both read states validation fails. Runs no query: git,
    through discovery, is its only cost.
    """
    covering = fd.covering_rule_sets(discovery)
    walk = _Walk(rule_sets)
    found: dict[str, ArtefactReach] = {}
    for artefact in discovery.artefacts:
        selecting = frozenset(covering.get(artefact.location, ()))
        if not selecting:
            continue
        answer = walk.answer(selecting)
        if answer.bindings or answer.conflicts or answer.held:
            found[artefact.location] = answer
    return Reach(found)


def reach_at(
    target_root: Path, tree: fd.RepositoryTree | None = None
) -> tuple[fd.Discovery, RuleSetDiscovery, Reach]:
    """The walk at one state: the working tree, or the commit `tree` holds — its
    settings, its artefacts and its rule sets, each read through the same tree."""
    settings = fd.read_friction_settings(target_root, tree)
    discovery = fd.discover_artefacts(target_root, settings, tree)
    rule_sets = discover_rule_sets(target_root, settings, tree)
    return discovery, rule_sets, reach(discovery, rule_sets)


@dataclass(frozen=True)
class _Edge:
    """One pin a set's `inherits` holds that names an existing set."""

    rule_set: RuleSet  # the inheriting set
    index: int
    pin: Pin
    inherited: RuleSet
    behind: bool


@dataclass(frozen=True)
class _Filler:
    """An accepted rule that fills an extension point an inherited rule offers."""

    rule_set: RuleSet
    rule: Rule
    offering_set: RuleSet
    offering: Rule
    point: str  # the point's name


class _Walk:
    """The routes of one state's rule sets, followed for each set of selecting scopes.

    What an artefact's answer depends on is which sets' scopes select it, so
    artefacts that share those sets share one answer, computed once.
    """

    def __init__(self, rule_sets: RuleSetDiscovery) -> None:
        self.rule_sets = rule_sets
        self._edges: dict[str, tuple[_Edge, ...]] = {}
        self._ancestors: dict[str, frozenset[str]] = {}
        self._answers: dict[frozenset[str], ArtefactReach] = {}

    def edges(self, rule_set: RuleSet) -> tuple[_Edge, ...]:
        """Each pin of the set that names a set, with whether it is behind that set."""
        if rule_set.path not in self._edges:
            found: list[_Edge] = []
            for index, pin in rule_set.pins:
                inherited, _problem = resolve_pin(self.rule_sets, pin)
                if inherited is not None:
                    behind = PinCheck(rule_set, index, pin, inherited).behind
                    found.append(_Edge(rule_set, index, pin, inherited, behind))
            self._edges[rule_set.path] = tuple(found)
        return self._edges[rule_set.path]

    def ancestors(self, rule_set: RuleSet) -> frozenset[str]:
        """The paths of every set `rule_set` inherits, directly or not, whatever its pins."""
        if rule_set.path not in self._ancestors:
            seen: set[str] = set()
            queue = [edge.inherited for edge in self.edges(rule_set)]
            while queue:
                current = queue.pop(0)
                if current.path in seen or current is rule_set:
                    continue
                seen.add(current.path)
                queue.extend(edge.inherited for edge in self.edges(current))
            self._ancestors[rule_set.path] = frozenset(seen)
        return self._ancestors[rule_set.path]

    @cached_property
    def fillers(self) -> tuple[_Filler, ...]:
        """Every accepted rule's fill of a point a rule of a set it inherits offers."""
        found: list[_Filler] = []
        for rule_set in self.rule_sets.rule_sets:
            ancestors = self.ancestors(rule_set)
            for rule in rule_set.rules:
                for _index, reference in rule.fills:
                    target_set, target, problem = locate_rule(self.rule_sets, reference)
                    if (
                        problem is None
                        and target_set is not None
                        and target is not None
                        and target_set.path in ancestors
                        and reference.point is not None
                    ):
                        found.append(_Filler(rule_set, rule, target_set, target, reference.point))
        return tuple(found)

    def answer(self, selecting: frozenset[str]) -> ArtefactReach:
        if selecting not in self._answers:
            self._answers[selecting] = _Routes(self, selecting).answer()
        return self._answers[selecting]


class _Routes:
    """The routes from one artefact, known by the sets whose scopes select it."""

    def __init__(self, walk: _Walk, selecting: frozenset[str]) -> None:
        self.walk = walk
        self.selecting = selecting
        self.starts = tuple(
            s for s in walk.rule_sets.rule_sets if s.path in selecting and s.component is None
        )
        self._clean: dict[str, dict[str, RuleSet]] = {}

    def passes(self, rule_set: RuleSet) -> bool:
        """Whether a route may pass through the set: it has no scope of its own, or its
        scope selects the artefact. A method rule set takes no scope (COR-051 point 2),
        so one written on it narrows nothing; validation refuses it."""
        own = rule_set.component is None and rule_set.front_matter.get(fd.SCOPE_KEY) is not None
        return not own or rule_set.path in self.selecting

    def clean(self, start: RuleSet) -> dict[str, RuleSet]:
        """The sets a route from `start` reaches with no pin behind its set, `start`
        included, by path."""
        if start.path not in self._clean:
            seen = {start.path: start}
            queue = [start]
            while queue:
                for edge in self.walk.edges(queue.pop(0)):
                    target = edge.inherited
                    if edge.behind or target.path in seen or not self.passes(target):
                        continue
                    seen[target.path] = target
                    queue.append(target)
            self._clean[start.path] = seen
        return self._clean[start.path]

    def reached(self) -> frozenset[str]:
        """The paths of every set a route from the artefact reaches with no pin behind
        its set."""
        return frozenset(path for start in self.starts for path in self.clean(start))

    def anywhere(self) -> dict[str, RuleSet]:
        """Every set any route from the artefact reaches, through a pin behind its set
        too, by path."""
        seen = {s.path: s for s in self.starts}
        queue = list(self.starts)
        while queue:
            for edge in self.walk.edges(queue.pop(0)):
                target = edge.inherited
                if target.path not in seen and self.passes(target):
                    seen[target.path] = target
                    queue.append(target)
        return seen

    def answer(self) -> ArtefactReach:
        if not self.starts:
            return _NO_REACH
        conflicts: list[Conflict] = [*self._pin_conflicts()]
        bound, fill_conflicts = self._fills()
        conflicts.extend(fill_conflicts)
        filling = {
            id(rule) for s in self.walk.rule_sets.rule_sets for rule in s.rules if rule.fills
        }
        bindings: list[Binding] = []
        for rule_set in self.walk.rule_sets.rule_sets:  # path order
            covering = tuple(s for s in self.starts if rule_set.path in self.clean(s))
            if not covering:
                continue
            for rule in rule_set.rules:
                if not rule.binds:
                    continue
                if id(rule) in filling:
                    points = bound.get(id(rule))
                    if points:
                        bindings.append(Binding(rule, rule_set, covering, tuple(points)))
                    continue
                bindings.append(Binding(rule, rule_set, covering))
        return ArtefactReach(tuple(bindings), tuple(conflicts), self._held())

    def _held(self) -> tuple[HeldRule, ...]:
        """The accepted rules of each set that the routes reach only through a pin behind
        its set, in path and written order, each with the pins behind their sets that lead
        towards it (COR-051 point 7). A rule that fills binds only as a fill, so none is
        held back as a rule."""
        anywhere = self.anywhere()
        reached = self.reached()
        behind = [
            edge
            for path in sorted(anywhere)
            for edge in self.walk.edges(anywhere[path])
            if edge.behind and self.passes(edge.inherited)
        ]
        found: list[HeldRule] = []
        for rule_set in self.walk.rule_sets.rule_sets:  # path order
            if rule_set.path not in anywhere or rule_set.path in reached:
                continue
            pins = tuple(
                (edge.rule_set, edge.index, edge.pin)
                for edge in behind
                if edge.inherited is rule_set
                or rule_set.path in self.walk.ancestors(edge.inherited)
            )
            found.extend(
                HeldRule(rule, rule_set, pins)
                for rule in rule_set.rules
                if rule.binds and not rule.fills  # a fill binds only as a fill
            )
        return tuple(found)

    def _pin_conflicts(self) -> list[PinConflict]:
        """One set pinned at different majors by the routes from the artefact."""
        pins: dict[str, list[tuple[RuleSet, int, Pin]]] = {}
        sets: dict[str, RuleSet] = {}
        for rule_set in sorted(self.anywhere().values(), key=lambda s: s.path):
            for edge in self.walk.edges(rule_set):
                if self.passes(edge.inherited):
                    pins.setdefault(edge.inherited.path, []).append(
                        (rule_set, edge.index, edge.pin)
                    )
                    sets[edge.inherited.path] = edge.inherited
        return [
            PinConflict(sets[path], tuple(found))
            for path, found in sorted(pins.items())
            if len({pin.major for _set, _index, pin in found}) > 1
        ]

    def _fills(self) -> tuple[dict[int, list[str]], list[FillConflict]]:
        """Which fill binds for each extension point the routes reach, by the filling
        rule, and the points whose most specific sets disagree (COR-051 point 7)."""
        points: dict[tuple[int, str], list[_Filler]] = {}
        for filler in self.walk.fillers:
            points.setdefault((id(filler.offering), filler.point), []).append(filler)
        bound: dict[int, list[str]] = {}
        conflicts: list[FillConflict] = []
        for fillers in points.values():
            offering_set, offering = fillers[0].offering_set, fillers[0].offering
            if not offering.binds:
                continue  # a fill binds only while the rule it fills is accepted
            through = [s for s in self.starts if offering_set.path in self.clean(s)]
            specific = [
                s
                for s in through
                if not any(
                    s.path in self.walk.ancestors(other) for other in through if other is not s
                )
            ]
            brought = [(s, self._brought(s, fillers)) for s in specific]
            choices = {tuple(id(rule) for _held, rule in fills) for _s, fills in brought}
            point = f"{offering_set.cite(offering.id)}#{fillers[0].point}"
            if len(choices) > 1 or any(len(fills) > 1 for _s, fills in brought):
                conflicts.append(FillConflict(point, tuple(brought)))
            elif brought and brought[0][1]:
                _held, rule = brought[0][1][0]
                bound.setdefault(id(rule), []).append(point)
        conflicts.sort(key=lambda c: c.point)
        return bound, conflicts

    def _brought(
        self, start: RuleSet, fillers: Sequence[_Filler]
    ) -> tuple[tuple[RuleSet, Rule], ...]:
        """The accepted fills of one point that the chain of `start` holds, each with the
        set holding it (COR-051 point 7). The chain is `start` and every set it inherits,
        whatever its pins. A fill counts where it binds through the filling set: a route
        with no pin behind its set reaches that set, and leads on from it to the
        offering set."""
        chain = self.walk.ancestors(start) | {start.path}
        reached = self.reached()
        found: list[tuple[RuleSet, Rule]] = []
        for filler in fillers:
            path = filler.rule_set.path
            if not filler.rule.binds or path not in chain or path not in reached:
                continue
            fill = (filler.rule_set, filler.rule)
            if filler.offering_set.path in self.clean(filler.rule_set) and fill not in found:
                found.append(fill)
        return tuple(found)


def locate_rule(
    discovery: RuleSetDiscovery, reference: RuleReference
) -> tuple[RuleSet | None, Rule | None, str | None]:
    """(set, rule, None) for a reference that resolves; otherwise why it does not.

    The component, when written, must name the component that owns the rule's
    set; a bare reference resolves whichever set owns it, since set names are
    unique. A point, when written, must be one the rule offers.
    """
    named = discovery.sets_named(reference.set_name)
    if not named:
        return None, None, f"no rule set is named {reference.set_name}"
    if reference.component is not None:
        owned = [s for s in named if s.component == reference.component]
        if not owned:
            other = named[0]
            return (
                None,
                None,
                (
                    f"rule set {reference.set_name} belongs to {other.owner}, not to "
                    f"{reference.component}, and is cited {other.citation}"
                ),
            )
        named = tuple(owned)
    if len(named) > 1:
        paths = ", ".join(s.path for s in named)
        return (
            None,
            None,
            f"rule set name {reference.set_name} is declared by {len(named)} files ({paths})",
        )
    rule_set = named[0]
    rule = rule_set.rule(reference.rule)
    if rule is None:
        return rule_set, None, f"rule set {rule_set.citation} has no rule {reference.rule}"
    if reference.point is not None and reference.point not in rule.offers:
        offered = ", ".join(f"#{p}" for p in rule.offers) or "none"
        return (
            rule_set,
            rule,
            f"{reference.rule} offers no extension point #{reference.point} (it offers: {offered})",
        )
    return rule_set, rule, None


@dataclass(frozen=True)
class CitationResolution:
    """What a rule citation resolves to, or why it does not."""

    citation: str
    reference: RuleReference | None
    rule_set: RuleSet | None
    rule: Rule | None
    problem: str | None

    @property
    def resolved(self) -> bool:
        return self.problem is None

    @property
    def location(self) -> str | None:
        """`path#RS-<SET>-NNN`, the rule's place, when it resolves."""
        return self.rule.location if self.rule is not None else None


def resolve_citation(discovery: RuleSetDiscovery, citation: str) -> CitationResolution:
    """Resolve a citation to its rule: `RS-<SET>-NNN`, `RS-<SET>-NNN#<point>`, or either with
    the owning component in front, bracketed or not (`[<component>:RS-<SET>-NNN]`)."""
    text = citation.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    reference = parse_rule_reference(text)
    if reference is None:
        return CitationResolution(
            citation,
            None,
            None,
            None,
            "not a rule citation: a rule is cited `RS-<SET>-NNN`, an extension point it offers "
            "`RS-<SET>-NNN#<point>`, either with `<component>:` in front for a method rule set",
        )
    rule_set, rule, problem = locate_rule(discovery, reference)
    return CitationResolution(citation, reference, rule_set, rule, problem)


def is_rule_citation(text: str) -> bool:
    """Whether `text` has the shape of a rule citation (bracketed or not)."""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return parse_rule_reference(text) is not None


@dataclass(frozen=True)
class RuleIdCollision:
    """A rule id claimed more than once in the rule-set space."""

    rule_id: str
    paths: tuple[str, ...]  # one per claim, sorted; a file claiming it twice appears twice


def rule_id_collisions(discovery: RuleSetDiscovery) -> tuple[RuleIdCollision, ...]:
    """Every well-formed rule id claimed by more than one entry, across all rule sets."""
    claims: dict[str, list[str]] = {}
    for rule_set in discovery.rule_sets:
        for rule in rule_set.rules:
            if rule.set_name is not None:
                claims.setdefault(rule.id, []).append(rule_set.path)
        for duplicate in rule_set.duplicate_keys:
            if duplicate.pointer == f"/{fd.RULES_KEY}" and rule_set_name_of(duplicate.key):
                extra = [rule_set.path] * (len(duplicate.lines) - 1)
                claims.setdefault(duplicate.key, []).extend(extra)
    return tuple(
        RuleIdCollision(rule_id, tuple(sorted(paths)))
        for rule_id, paths in sorted(claims.items())
        if len(paths) > 1
    )


# --- decision records ----------------------------------------------------------


def _decision_file(target_root: Path, record: str) -> Path | None:
    """The file of a cited decision: `COR-`, `PRJ-`, `ADR-NNN`, or `<capability>:DEC-NNN`."""
    match = _DECISION_ID_RE.fullmatch(record)
    if match is None:
        return None
    if match.group("capability"):
        folder: Path | None = (
            target_root / fd.CAPABILITIES_DIR / match.group("capability") / "decisions"
        )
        local = match.group("dec")
    else:
        local = match.group("record")
        folder = _record_folder(target_root, local.split("-", 1)[0])
    if folder is None or not folder.is_dir():
        return None
    matches = sorted(folder.glob(f"{local}-*.md"))
    return matches[0] if matches else None


def _record_folder(target_root: Path, family: str) -> Path | None:
    if family == "COR":
        return target_root / ".pkit" / "decisions" / "core"
    if family == "PRJ":
        return target_root / ".pkit" / "decisions" / "project"
    try:  # ADR: the overlay-resolved folder, when the project has one
        return resolve_adr_records_dir(target_root)
    except click.ClickException:
        return None


def _front_matter_status(path: Path) -> str | None:
    try:
        front_matter, _body = document_parts.split_front_matter(path.read_text(encoding="utf-8"))
        data = _yaml.load(io.StringIO(front_matter)) if front_matter is not None else None
    except (OSError, UnicodeDecodeError, YAMLError):
        return None
    status = data.get("status") if isinstance(data, Mapping) else None
    return status if isinstance(status, str) else None


# --- rendering for `pkit validate` -------------------------------------------


def summary_lines(result: RuleSetValidation) -> list[str]:
    """The count line `pkit validate` prints under its `rule-sets` heading; the
    findings follow as the member's findings."""
    d = result.discovery
    if result.is_dormant:
        return ["no rule sets found."]
    rules = d.rules
    by_status = {status: sum(1 for rule in rules if rule.status == status) for status in STATUSES}
    statuses = ", ".join(f"{count} {status}" for status, count in by_status.items() if count)
    unreadable = f", {len(d.unreadable)} unreadable" if d.unreadable else ""
    breakdown = f" ({statuses})" if statuses else ""
    counts = (
        f"{len(d.rule_sets)} rule set(s){unreadable}, {len(rules)} rule(s){breakdown}; "
        f"{len(result.errors)} error(s), {len(result.reports)} report(s)."
    )
    return [counts]


UMBRELLA_SEVERITY = {
    Severity.ERROR: validators.Severity.ERROR,
    Severity.REPORT: validators.Severity.REPORT,
}


def outcome(target_root: Path) -> validators.Outcome:
    """The `rule-sets` member of `pkit validate`: the counts, then every finding —
    errors fail, reports print (COR-051)."""
    result = validate_rule_sets(target_root)
    findings = tuple(
        validators.Finding(
            f"{f.location}:{f.pointer}" if f.pointer else f.location,
            f.message,
            UMBRELLA_SEVERITY[f.severity],
        )
        for f in result.findings
    )
    return validators.Outcome(tuple(summary_lines(result)), findings)


# --- helpers ---------------------------------------------------------------------


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _command_paths(command: click.Command, prefix: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    """Every command beneath a click command, by its words, the command itself included
    when it has words."""
    if prefix:
        yield prefix
    if isinstance(command, click.Group):
        for name, sub in command.commands.items():
            yield from _command_paths(sub, (*prefix, name))


def _names(fields: Sequence[str]) -> str:
    return ", ".join(f"`{name}`" for name in fields)


def _pointer(segments: Iterable[Any]) -> str:
    parts = [_token(s) for s in segments]
    return "/" + "/".join(parts) if parts else ""


def _token(segment: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(segment).replace("~", "~0").replace("/", "~1")


def _yaml_problem(exc: YAMLError) -> str:
    problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        # +1 for 1-based lines, +1 for the opening fence of the front matter.
        return f"{problem} at line {mark.line + 2} col {mark.column + 1}"
    return str(problem)
