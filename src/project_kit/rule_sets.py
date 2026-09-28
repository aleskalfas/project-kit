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
  origins; successors; inheritance (points 3, 5 and 7). Whether a pinned
  major is still the inherited set's is a version relation: `pin_checks`
  hands it to the wiring resolver, which reports every version relation
  under `versions` (`connections.rule_set_pin_findings`);
- resolves citations to rules (`resolve_citation`) and lists rule ids
  claimed more than once in the rule-set space (`rule_id_collisions`), for
  `pkit refs` and `pkit decisions validate`.

Deterministic: the same repository state gives the same findings in the same
order — files by path, each file's checks in a fixed order, then the
inheritance cycles. Nothing here touches git. Whether an id was *reused*
after its rule was deleted cannot be seen in one state; that is why retired
rules stay in place, so that a reused id is a duplicate this pass reports.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any

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
from project_kit import validators
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

_yaml = YAML(typ="safe")
_yaml_keeping_first = YAML(typ="safe")
_yaml_keeping_first.allow_duplicate_keys = True  # the first value is kept

_FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
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


@dataclass(frozen=True, eq=False)
class Rule:
    """One rule: its data entry and the body section headed by its id.

    `data` is the entry as written (`{}` when the entry is not a mapping; the
    schema reports it). Every property reads forgivingly — a value of the
    wrong shape reads as absent — because the schema pass judges the shape.
    Compared by identity: each rule is parsed once.
    """

    id: str
    path: str  # the rule-set file, relative to the root
    data: Mapping[str, Any]
    section: str  # the body section headed by the id, or ""

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
    target_root: Path, settings: fd.FrictionSettings | None = None
) -> RuleSetDiscovery:
    """Read every rule-set file the location rule claims, in path order."""
    settings = settings if settings is not None else fd.read_friction_settings(target_root)
    places = fd.rule_set_places(target_root, settings)
    claimed = fd.rule_set_files(target_root, places)
    rule_sets: list[RuleSet] = []
    unreadable: list[UnreadableRuleSet] = []
    for path, place in sorted(claimed.items(), key=lambda item: _rel(target_root, item[0])):
        read = _read_rule_set(target_root, path, place)
        if isinstance(read, RuleSet):
            rule_sets.append(read)
        else:
            unreadable.append(read)
    return RuleSetDiscovery(places=places, rule_sets=tuple(rule_sets), unreadable=tuple(unreadable))


def _read_rule_set(
    target_root: Path, path: Path, place: fd.RuleSetPlace
) -> RuleSet | UnreadableRuleSet:
    rel = _rel(target_root, path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return UnreadableRuleSet(rel, place, f"cannot be read ({exc})")
    front_matter, body = fd.split_front_matter(text)
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
    raw_rules = data.get(fd.RULES_KEY)
    rules = tuple(
        Rule(
            id=rule_id,
            path=rel,
            data=entry if isinstance(entry, Mapping) else {},
            section=fd.entry_section(body, rule_id),
        )
        for rule_id, entry in (raw_rules.items() if isinstance(raw_rules, Mapping) else ())
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
    """The body headings that open with `RS-`, outside fenced code, in order."""
    sections: list[Section] = []
    fence: str | None = None
    for line in body.splitlines():
        marker = _FENCE.match(line)
        if marker is not None:
            fence = None if fence == marker.group(1) else (fence or marker.group(1))
            continue
        if fence is not None:
            continue
        heading = _HEADING.match(line)
        if heading is None or not heading.group(2).startswith("RS-"):
            continue
        text = heading.group(2).strip()
        match = _HEADING_ID.match(text)
        sections.append(Section(rule_id=match.group(1) if match else None, heading=text))
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
    SUCCESSOR_NOT_FOUND = "successor-not-found"
    SUCCESSOR_OUT_OF_LINE = "successor-out-of-line"  # not in the set or one inheriting it
    INHERITED_SET_MISSING = "inherited-set-missing"
    INHERITANCE_NOT_ALLOWED = "inheritance-not-allowed"
    INHERITANCE_CYCLE = "inheritance-cycle"
    UNDECLARED_FILL = "undeclared-fill"
    DOUBLE_FILL = "double-fill"
    ORPHANED_FILL = "orphaned-fill"  # a fill of a superseded or withdrawn rule


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
    for rule_set in discovery.rule_sets:
        findings.extend(_duplicate_key_findings(rule_set))
        findings.extend(_shape_findings(rule_set, schema))
        findings.extend(_set_name_findings(rule_set, discovery))
        findings.extend(_id_findings(rule_set, catalogue))
        findings.extend(_join_findings(rule_set))
        if container_schema is not None:
            findings.extend(_container_findings(rule_set, container_schema, wiring))
        findings.extend(_origin_findings(rule_set, catalogue))
        findings.extend(_successor_findings(rule_set, catalogue))
        findings.extend(_inheritance_findings(rule_set, catalogue))
        findings.extend(_fill_findings(rule_set, catalogue))
    findings.extend(_cycle_findings(catalogue))
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
    """A cited source resolves through the one anchor-kind registry (ADR-057 point 2)."""
    source = origin.get("source")
    kind = source.get("kind") if isinstance(source, Mapping) else None
    if not isinstance(kind, str) or not kind:
        return  # absent, or malformed: the shape pass reports it
    # A source resolves only through a kind a capability registered (COR-051
    # point 5): the core anchor kinds are not source kinds, and this validator
    # resolves no source itself, so every source is gated on the registry and
    # never silently passed.
    registry = fd.registered_anchor_kinds(catalogue.target_root)
    resolver = registry.get(kind)
    reason = (
        "no installed capability registers a resolver for it"
        if resolver is None
        else fd.refuse_resolver_without_query_contract(resolver)
        or f"the resolver `{resolver.command}` that {resolver.capability} registers for it is not run yet"
    )
    if reason is not None:
        yield _report(
            rule.location,
            "/origin/source",
            RuleSetFindingKind.UNRESOLVED_SOURCE_KIND,
            f"source kind {kind!r} is unresolved: {reason}, so the source is not checked "
            f"(COR-051 point 5; COR-050 point 2).",
        )


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
    """Fills name points that inherited rules offer, each filled at most once (COR-051 point 7).

    A superseded or withdrawn rule binds nothing, so its fills are history:
    they are neither checked nor counted.
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
    yield from _double_fill_findings(rule_set, catalogue)


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
    chain, a record's status, a capability's declared dependencies.
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
            f"dependency on capability {parent.component}: add it to `requires_capabilities` in "
            f".pkit/capabilities/{child.component}/package.yaml (COR-030; COR-051 point 7)."
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

    def decision(self, record: str) -> tuple[Path | None, str | None]:
        """(the record's file, its status) for a cited decision id, or (None, None)."""
        if record not in self._decisions:
            path = _decision_file(self.target_root, record)
            status = _front_matter_status(path) if path is not None else None
            self._decisions[record] = (path, status)
        return self._decisions[record]

    def requires(self, capability: str) -> frozenset[str]:
        """The capabilities `capability` declares in `requires_capabilities` (COR-030)."""
        if capability not in self._requires:
            source = caps.find_capability_in_repo(self.target_root, capability)
            names = (
                frozenset(dep.name for dep in source.package.requires_capabilities)
                if source is not None
                else frozenset()
            )
            self._requires[capability] = names
        return self._requires[capability]


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
    `versions` (`connections.rule_set_pin_findings`).
    """

    rule_set: RuleSet  # the inheriting set
    index: int  # the pin's index in `inherits`, as written
    pin: Pin
    inherited: RuleSet

    @property
    def pointer(self) -> str:
        return f"/inherits/{self.index}"

    @property
    def problem(self) -> str | None:
        """Why the pin no longer holds, naming the new major; None while it does."""
        major = self.inherited.major
        if major is None or major == self.pin.major:
            return None  # an unreadable version is the inherited file's shape finding
        return (
            f"pins {self.pin}, but {self.inherited.citation} is at version "
            f"{self.inherited.version}, major {major}; review what changed in it, then update "
            f"the pin to {self.inherited.citation}@{major} (COR-051 point 7)."
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
        front_matter, _body = fd.split_front_matter(path.read_text(encoding="utf-8"))
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


def _names(fields: Sequence[str]) -> str:
    return ", ".join(f"`{name}`" for name in fields)


def _rel(target_root: Path, path: Path) -> str:
    return path.relative_to(target_root).as_posix()


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
