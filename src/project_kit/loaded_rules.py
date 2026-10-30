"""Which loaded files bind, and how each reaches a session (COR-070; ADR-076).

A loaded file holds a loaded set's accepted rules, and binds on the work of every
session that loads it (COR-068 point 2). The backbone's reaches a session through
the include the adapter keeps in the project's instruction file. A capability's
takes the same route through one index the backbone renders (COR-070 point 2).
This module is the one home of both answers:

- **Which loaded files bind** (`loaded_files`), every layer's with its owner: the
  backbone's, each loaded set of a capability the backbone manifest registers, and
  the project's own loaded set or plain rules file (ADR-076 point 1). A capability
  unregistered with its files kept is not in it. `pkit rule-sets loaded` prints it,
  the index takes its capabilities' entries from it, and the check reads it, so a
  capability's file is delivered exactly where it is checked.
- **How an adapter delivers them** (`delivery_forms`): its package metadata's
  `loaded_rules:` key gives its harness's syntax as data, `entry:`, `host:` and
  `line:` (ADR-076 point 4). The backbone names no adapter's paths or syntax.
- **The index** (`render_index`), `.pkit/rules/capabilities.md`, from those two:
  its marker line, then one entry per registered capability that ships a loaded
  set, in the order of their names. The lifecycle's render writes what it gives
  (`write_index`), and the check compares the file with the same function's
  output, so the two never disagree (ADR-076 point 4). A file at the index's path
  without the marker is someone else's, and nothing writes over it
  (`index_clash`, ADR-076 point 2).
- **Whether a host file holds a line** (`holds_line`): a trimmed line of its own,
  a CRLF ending read as `\\n`, outside fenced code. The adapter's merge primitive
  tests its copy of the line by the same definition, and one set of test cases
  holds the two to it (ADR-076 point 2).
- **The check** (`check_delivery`), part of validation's `rule-sets` member:
  `loaded-rules-undelivered` where the index is in the checkout and does not carry
  each registered capability's loaded file as it is, or the host file lacks the
  line, and a warning for each registered adapter that declares no delivery
  (ADR-076 point 5).
- **An import token in a loaded set** (`import_token_findings`): a token outside
  code that opens with the prefix a registered adapter's `entry:` declares, which
  the harness would read as an import of its own (ADR-076 point 1).
- **What a lifecycle step newly binds** (`compare`): two readings of one set's
  accepted rules, by id, status and statement, whatever its layer. Install, sync
  and upgrade print it for each loaded set they deliver (ADR-076 point 6).
"""

from __future__ import annotations

import os
import posixpath
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, cast

import click
from ruamel.yaml import YAML

from project_kit import document_parts, validators
from project_kit import friction_discovery as fd
from project_kit import loaded_rule_sets as lrs
from project_kit import rule_sets as rs
from project_kit.line_breaks import universal_newlines
from project_kit.manifest import read_backbone_manifest

# ruamel.yaml is untyped; a package's value is judged where it is read.
_yaml: Any = YAML(typ="safe")

#: The capabilities' rules index, beside core's and the project's loaded files: the
#: backbone's path, fixed by its owner as core's is (ADR-076 points 2 and 4).
INDEX_FILE = PurePosixPath(".pkit/rules/capabilities.md")

#: What opens the index's marker line. A file at the index's path whose first line
#: does not open with it is no index (`index_clash`).
INDEX_MARKER_TAG = "<!-- pkit: the capabilities' rules index"

#: The index's first line: an HTML comment, which the harness drops from what a session
#: holds (ADR-076, Context), saying who renders the file and that nobody edits it.
INDEX_MARKER = (
    f"{INDEX_MARKER_TAG}, rendered by the backbone from the installed capabilities' "
    "loaded rule sets at each install, sync and upgrade. Do not edit it. -->"
)

#: The adapter's package key that declares its delivery (ADR-076 point 4).
LOADED_RULES_KEY = "loaded_rules"
#: In `entry:`, the path of a capability's loaded file, read from the index's folder.
FILE_SLOT = "{file}"
#: In `line:`, the index's path, read from the host file's folder.
INDEX_SLOT = "{index}"

#: The layers, in the order a session reads them (COR-070 point 4).
BACKBONE, CAPABILITY, PROJECT = "backbone", "capability", "project"

#: The command that prints the answer, as messages name it.
LOADED_COMMAND = "pkit rule-sets loaded"


class DeliveryKind(Enum):
    """What a finding of the delivery check is about (ADR-076 point 5)."""

    UNDELIVERED = "loaded-rules-undelivered"
    UNDECLARED = "loaded-rules-undeclared"


# --- which loaded files bind (ADR-076 point 1) ------------------------------------------


@dataclass(frozen=True)
class LoadedFile:
    """One layer's loaded file, with its owner.

    - `layer`: `backbone`, `capability` or `project`
    - `owner`: `backbone`, the capability's name, or `project`
    - `path`: the loaded file, relative to the root
    - `rule_set`, `set_path`: the loaded set it is generated from, as cited and where it
      is; `None` for a plain file, which no set generates (COR-068 point 7)
    - `present`: whether the checkout holds the file
    """

    layer: str
    owner: str
    path: str
    rule_set: str | None
    set_path: str | None
    present: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "owner": self.owner,
            "path": self.path,
            "rule_set": self.rule_set,
            "set_path": self.set_path,
            "present": self.present,
        }


def loaded_files(
    target_root: Path, discovery: rs.RuleSetDiscovery | None = None
) -> tuple[LoadedFile, ...]:
    """Every layer's loaded file, in the order a session reads them: the backbone's, each
    registered capability's by name, then the project's.

    A layer's file is the one generated from its first loaded set (`first_loaded`). The
    backbone and the project with no loaded set give their plain file where it is, as a
    project's `project.md` is before it is converted (COR-068 point 7). Only capabilities
    the backbone manifest registers count, so one unregistered with its files kept is
    left out though its set is still where it was.
    """
    discovery = discovery if discovery is not None else rs.discover_rule_sets(target_root)
    found: list[LoadedFile] = []

    def add(layer: str, owner: str, component: str | None, plain: PurePosixPath | None) -> None:
        rule_set = lrs.first_loaded(discovery, component)
        if rule_set is not None:
            path = lrs.loaded_file_of(rule_set)
            found.append(
                LoadedFile(
                    layer,
                    owner,
                    str(path),
                    rule_set.citation,
                    rule_set.path,
                    (target_root / path).is_file(),
                )
            )
        elif plain is not None and (target_root / plain).is_file():
            found.append(LoadedFile(layer, owner, str(plain), None, None, True))

    add(BACKBONE, BACKBONE, fd.BACKBONE_COMPONENT, lrs.BACKBONE_LOADED_FILE)
    for name in fd.installed_capability_names(target_root):
        add(CAPABILITY, name, name, None)
    add(PROJECT, PROJECT, None, lrs.PROJECT_LOADED_FILE)
    return tuple(found)


def capability_files(loaded: Iterable[LoadedFile]) -> tuple[LoadedFile, ...]:
    return tuple(f for f in loaded if f.layer == CAPABILITY)


# --- how an adapter delivers them (ADR-076 point 4) -------------------------------------


@dataclass(frozen=True)
class DeliveryForm:
    """How one adapter's harness reaches the capabilities' loaded files: an index of
    entries, reached from the host file by one line (`loaded_rules:`)."""

    adapter: str
    entry: str  # `@{file}`: one capability's loaded file, read from the index's folder
    host: str  # `CLAUDE.md`: the file that reaches the index, from the root
    line: str  # `@{index}`: the line that reaches it, read from the host's folder

    @property
    def entry_prefix(self) -> str:
        """The part of `entry:` before its path: the token that opens an import."""
        return self.entry.split(FILE_SLOT, 1)[0]

    def entry_for(self, loaded_file: str) -> str:
        """The index's entry for one loaded file, given from the root."""
        return self.entry.replace(FILE_SLOT, _relative(loaded_file, INDEX_FILE.parent))

    def file_of(self, entry: str) -> str | None:
        """The loaded file, from the root, an entry of the index names; None for a line of
        another form."""
        before, _slot, after = self.entry.partition(FILE_SLOT)
        if not entry.startswith(before) or not entry.endswith(after):
            return None
        written = entry[len(before) : len(entry) - len(after)] if after else entry[len(before) :]
        if not written:
            return None
        return posixpath.normpath(posixpath.join(INDEX_FILE.parent.as_posix(), written))

    @property
    def rendered_line(self) -> str:
        """The line the host file keeps, with the index's path read from the host's folder."""
        return self._line_to(str(INDEX_FILE))

    @property
    def core_line(self) -> str:
        """The same form's line for core's loaded file: the host's include of core's rules,
        after which the merge keeps the index's line."""
        return self._line_to(str(lrs.BACKBONE_LOADED_FILE))

    def _line_to(self, path: str) -> str:
        return self.line.replace(INDEX_SLOT, _relative(path, PurePosixPath(self.host).parent))


def _relative(path: str, start: PurePosixPath) -> str:
    return posixpath.relpath(path, start.as_posix() or ".")


def read_delivery_form(adapter: str, package: Mapping[str, Any]) -> DeliveryForm | None:
    """An adapter's `loaded_rules:` as its package writes it, read forgivingly: a key of
    another shape reads as none, which the package schema reports."""
    raw: Any = package.get(LOADED_RULES_KEY)
    if not isinstance(raw, Mapping):
        return None
    fields = cast("Mapping[str, Any]", raw)
    entry, host, line = (fields.get(key) for key in ("entry", "host", "line"))
    if not all(isinstance(value, str) and value for value in (entry, host, line)):
        return None
    assert isinstance(entry, str) and isinstance(host, str) and isinstance(line, str)
    if FILE_SLOT not in entry or INDEX_SLOT not in line:
        return None
    return DeliveryForm(adapter, entry, host, line)


@dataclass(frozen=True)
class Deliveries:
    """What the registered adapters declare: each form, and each adapter with none."""

    forms: tuple[DeliveryForm, ...]
    undeclared: tuple[str, ...]

    @property
    def differing(self) -> bool:
        """Whether the declared forms disagree on the index's entries (ADR-076 point 4)."""
        return len({form.entry for form in self.forms}) > 1

    @property
    def prefixes(self) -> tuple[str, ...]:
        """The import tokens the registered adapters' entries open with, but an empty one."""
        return tuple(dict.fromkeys(f.entry_prefix for f in self.forms if f.entry_prefix))


def delivery_forms(target_root: Path) -> Deliveries:
    """Each registered adapter's delivery, in the manifest's order (ADR-076 point 4)."""
    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        return Deliveries((), ())
    forms: list[DeliveryForm] = []
    undeclared: list[str] = []
    for entry in manifest.components:
        if entry.kind != "adapter":
            continue
        package_yaml = target_root / ".pkit" / "adapters" / entry.name / "package.yaml"
        try:
            data: Any = _yaml.load(package_yaml.read_text(encoding="utf-8"))
        except Exception:  # an unreadable package is the packages member's finding
            data = None
        form = (
            read_delivery_form(entry.name, cast("Mapping[str, Any]", data))
            if isinstance(data, Mapping)
            else None
        )
        if form is None:
            undeclared.append(entry.name)
        else:
            forms.append(form)
    return Deliveries(tuple(forms), tuple(undeclared))


# --- the index (ADR-076 points 2 and 4) --------------------------------------------------


class DifferingForms(click.ClickException):
    """The registered adapters declare entries of different forms, so one index cannot
    serve them (ADR-076 point 4)."""


def differing_message(deliveries: Deliveries) -> str:
    named = ", ".join(f"{form.adapter} (`{form.entry}`)" for form in deliveries.forms)
    return (
        f"the registered adapters declare different forms of the index's entries: {named}. "
        f"The index {INDEX_FILE} has one path, so it is not rendered until the record that "
        f"adds the second adapter decides how one index serves both (ADR-076 point 4)."
    )


def render_index(loaded: Sequence[LoadedFile], deliveries: Deliveries) -> str:
    """The index's text: the marker, then one entry per capability's loaded file in
    `loaded`, in the order given. With no declared form it holds the marker alone, and
    with forms that differ it is refused (`DifferingForms`)."""
    if deliveries.differing:
        raise DifferingForms(differing_message(deliveries))
    lines = [INDEX_MARKER]
    if deliveries.forms:
        form = deliveries.forms[0]
        lines.extend(form.entry_for(f.path) for f in capability_files(loaded))
    return "\n".join(lines) + "\n"


def index_text(target_root: Path) -> str:
    """What the index should hold in this tree: `render_index` over `loaded_files` and
    the registered adapters' forms."""
    return render_index(loaded_files(target_root), delivery_forms(target_root))


def is_index(text: str) -> bool:
    """Whether a file's text is an index the backbone rendered: its first line opens with
    the marker's tag. An empty file, which an interrupted write leaves, counts as one."""
    first = universal_newlines(text).split("\n", 1)[0]
    return not text or first.startswith(INDEX_MARKER_TAG)


def index_clash(target_root: Path) -> Path | None:
    """The file at the index's path that is no index, or None: one without the marker,
    or anything there that is not a file. Read-only."""
    path = target_root / INDEX_FILE
    if not os.path.lexists(path):
        return None
    if path.is_file() and not path.is_symlink():
        try:
            if is_index(path.read_bytes().decode("utf-8")):
                return None
        except (OSError, UnicodeDecodeError):
            pass
    return path


def refuse_index_clash(target_root: Path, *, command: str) -> None:
    """Stop a command that would render the index over a file that is not one.

    A transition calls it in its step 1, beside the clash of area names, and sync before
    it writes (ADR-076 point 2). It writes nothing and takes no override."""
    path = index_clash(target_root)
    if path is None:
        return
    raise click.ClickException(
        f"refusing to run `pkit {command}`: {INDEX_FILE} is not the capabilities' rules "
        f"index, since its first line is not the backbone's marker, and the backbone "
        f"renders the index at that path (ADR-076 point 2). Nothing was written. Move the "
        f"file elsewhere, or remove it if it holds nothing you need, then run "
        f"`pkit {command}` again."
    )


def write_index(target_root: Path, *, dry_run: bool = False) -> str:
    """Render the index whole, where it differs, and say what was done, in the lifecycle's
    status-line form. Writes nothing over a file that is no index, nor where the adapters'
    forms differ: the line says so, and validation fails it."""
    shown = str(INDEX_FILE)
    if index_clash(target_root) is not None:
        return f"  {'refused':<12} {shown} (a file that is not the index is there; nothing written)"
    deliveries = delivery_forms(target_root)
    if deliveries.differing:
        return f"  {'refused':<12} {shown} ({differing_message(deliveries)})"
    loaded = loaded_files(target_root)
    text = render_index(loaded, deliveries)
    names = [f.owner for f in capability_files(loaded)] if deliveries.forms else []
    holds = f"{len(names)} capability file(s)" + (f": {', '.join(names)}" if names else "")
    path = target_root / INDEX_FILE
    try:
        current = universal_newlines(path.read_bytes().decode("utf-8")) if path.is_file() else None
    except (OSError, UnicodeDecodeError):
        current = None
    if current == text:
        return f"  {'unchanged':<12} {shown} ({holds})"
    if dry_run:
        return f"  {'would render':<12} {shown} ({holds})"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return f"  {'rendered':<12} {shown} ({holds})"


# --- whether a host file holds a line (ADR-076 point 2) ----------------------------------


def holds_line(text: str, line: str) -> bool:
    """Whether `text` holds `line`: a line of its own once the spaces and tabs around it
    are trimmed and a CRLF ending is read as `\\n`, outside fenced code. A mention in a
    code span, in a fence or as part of a longer token does not hold it, since the
    harness imports none of these. The merge primitive's test is the same."""
    for candidate, outside in document_parts.lines_outside_fences(universal_newlines(text)):
        if outside and candidate.strip(" \t") == line:
            return True
    return False


# --- the check (ADR-076 point 5) ---------------------------------------------------------


@dataclass(frozen=True)
class Delivery:
    """What the check found: its summary lines, then its findings."""

    summary: tuple[str, ...]
    findings: tuple[validators.Finding, ...] = ()


def _undelivered(location: str, message: str) -> validators.Finding:
    return validators.Finding(
        location, message, validators.Severity.ERROR, DeliveryKind.UNDELIVERED.value
    )


def check_delivery(target_root: Path) -> Delivery:
    """Compare what the registered adapters declare they deliver with what the checkout
    holds (ADR-076 point 5). Reads files only, never a session.

    - a registered adapter without `loaded_rules:` is a warning naming it and each
      capability that ships a loaded set: its harness's sessions load none of them
    - adapters whose entries differ fail, and the index is compared with nothing
    - an index that is not in the checkout is a summary line: its sessions load no
      capability's rules, and the next sync renders it
    - otherwise each of these fails, naming the adapter, the file and what mends it:
      the index differing from `render_index`'s text once line endings are read as
      `\\n`, an entry for a capability no longer registered among the differences; an
      entry naming a loaded file the checkout does not hold; and a host file that does
      not hold its line (`holds_line`)
    - a host file the checkout does not hold at all is a summary line, as the index's
      absence is: its sessions load no layer's rules through it, core's included, so
      no capability's delivery is out of step with core's there
    """
    loaded = loaded_files(target_root)
    capabilities = [f.owner for f in capability_files(loaded)]
    deliveries = delivery_forms(target_root)
    findings: list[validators.Finding] = []
    shipping = ", ".join(capabilities) if capabilities else "none ships one yet"
    for adapter in deliveries.undeclared:
        findings.append(
            validators.Finding(
                f".pkit/adapters/{adapter}/package.yaml",
                f"adapter {adapter} declares no `{LOADED_RULES_KEY}:`, so it delivers no "
                f"capability's rules, and its harness's sessions load none of them "
                f"(capabilities that ship a loaded set: {shipping}; COR-070 point 6).",
                validators.Severity.WARNING,
                DeliveryKind.UNDECLARED.value,
            )
        )
    if deliveries.differing:
        findings.append(_undelivered(str(INDEX_FILE), differing_message(deliveries)))
        return Delivery(
            (f"capabilities' rules index {INDEX_FILE}: not compared.",), tuple(findings)
        )
    path = target_root / INDEX_FILE
    if not os.path.lexists(path):
        return Delivery(
            (
                f"no capabilities' rules index here ({INDEX_FILE}): this checkout's sessions "
                f"load no capability's rules; `pkit sync` renders it.",
            ),
            tuple(findings),
        )
    expected = render_index(loaded, deliveries)
    try:
        actual = universal_newlines(path.read_bytes().decode("utf-8")) if path.is_file() else None
    except (OSError, UnicodeDecodeError):
        actual = None
    adapters = ", ".join(form.adapter for form in deliveries.forms) or "no adapter"
    if actual != expected:
        findings.append(_undelivered(str(INDEX_FILE), _differs(actual, expected, adapters)))
    form = deliveries.forms[0] if deliveries.forms else None
    if form is not None and actual is not None:
        wanted = set(expected.split("\n")[1:])
        for entry in actual.split("\n")[1:]:
            if not entry.strip() or entry not in wanted:
                continue
            named = form.file_of(entry)
            if named is not None and not (target_root / named).is_file():
                findings.append(
                    _undelivered(
                        str(INDEX_FILE),
                        f"the entry {entry!r} names {named}, which this checkout does not "
                        f"hold, so a session loads none of its rules though the index "
                        f"names them ({adapters}). The next `pkit sync`, or the "
                        f"capability's install, brings it.",
                    )
                )
    absent: list[str] = []
    for each in deliveries.forms:
        host = target_root / each.host
        line = each.rendered_line
        if not os.path.lexists(host):
            absent.append(each.host)
            continue
        try:
            text = host.read_bytes().decode("utf-8") if host.is_file() else None
        except (OSError, UnicodeDecodeError):
            text = None
        if text is not None and holds_line(text, line):
            continue
        findings.append(_undelivered(each.host, _host_lacks(each, line, text)))
    names = ", ".join(capabilities) if capabilities and form is not None else ""
    count = len(capabilities) if form is not None else 0
    hosts = ", ".join(f"{f.host} ({f.adapter})" for f in deliveries.forms) or "no host file"
    summary = [
        f"capabilities' rules index {INDEX_FILE}: {count} capability file(s)"
        f"{f' ({names})' if names else ''}, reached from {hosts}."
    ]
    summary.extend(
        f"{host} is not in this checkout, so its sessions load no layer's rules through it, "
        f"core's included; the next `pkit sync` writes it."
        for host in absent
    )
    return Delivery(tuple(summary), tuple(findings))


def _differs(actual: str | None, expected: str, adapters: str) -> str:
    if actual is None:
        return (
            f"{INDEX_FILE} cannot be read as the capabilities' rules index ({adapters}). The "
            f"next `pkit sync` renders it again."
        )
    have = [line for line in actual.split("\n")[1:] if line.strip()]
    want = [line for line in expected.split("\n")[1:] if line.strip()]
    parts: list[str] = []
    missing = [line for line in want if line not in have]
    extra = [line for line in have if line not in want]
    if missing:
        parts.append(f"it lacks {', '.join(repr(m) for m in missing)}")
    if extra:
        parts.append(
            f"it holds {', '.join(repr(e) for e in extra)}, for no registered capability's "
            f"loaded set"
        )
    if not parts:
        parts.append("its text differs from what the backbone renders")
    return (
        f"{INDEX_FILE} is out of step with the capabilities `{LOADED_COMMAND}` lists "
        f"({adapters}): {'; '.join(parts)}. The backbone renders it, and nobody edits it; "
        f"the next `pkit sync` renders it again."
    )


def _host_lacks(form: DeliveryForm, line: str, text: str | None) -> str:
    if text is None:
        where = f"{form.host} cannot be read as text, so nothing reaches {INDEX_FILE}"
    else:
        where = f"{form.host} does not hold the line `{line}` that reaches {INDEX_FILE}"
    mend = "The next `pkit sync` inserts it."
    core = form.core_line
    if text is not None and core in text and not holds_line(text, core):
        mend = (
            f"Its include of core's rules, `{core}`, sits only in fenced code or a code "
            f"span, where the harness imports nothing, so the merge inserts nothing: move "
            f"the include out of the code, and the next `pkit sync` inserts this line after "
            f"it."
        )
    return (
        f"{where}, so a session loads no capability's rules ({form.adapter}; COR-070 point "
        f"6). {mend}"
    )


def summary_and_findings(
    target_root: Path,
) -> tuple[tuple[str, ...], tuple[validators.Finding, ...]]:
    """The check's lines and findings, for the `rule-sets` member's outcome."""
    delivery = check_delivery(target_root)
    return delivery.summary, delivery.findings


# --- an import token in a loaded set (ADR-076 point 1) ----------------------------------


def import_token_findings(
    target_root: Path, discovery: rs.RuleSetDiscovery
) -> Iterable[rs.RuleSetFinding]:
    """Each token outside code, in any loaded set's body, core's included, that opens
    with an import prefix a registered adapter's `entry:` declares (ADR-076 point 1).

    A loaded file is imported, and a harness that imports files may read such a token in
    it as an import of its own. A path in backticks is code, and stays. Where no
    registered adapter declares a prefix, nothing is refused, so no harness's syntax is
    written into the backbone."""
    prefixes = delivery_forms(target_root).prefixes
    if not prefixes:
        return
    pattern = re.compile(
        r"(?<!\S)(?:" + "|".join(re.escape(prefix) for prefix in prefixes) + r")\S*"
    )
    for rule_set in lrs.loaded_sets(discovery):
        prose = document_parts.running_text(rule_set.body)
        for match in pattern.finditer(prose):
            line = prose.count("\n", 0, match.start()) + 1
            yield rs.RuleSetFinding(
                rule_set.path,
                "",
                rs.Severity.ERROR,
                rs.RuleSetFindingKind.LOADED_IMPORT_TOKEN,
                f"line {line} of the set's body holds {match.group(0)!r} outside code. It "
                f"opens with an import token of the harness the registered adapters declare, "
                f"so a session that loads the file could read it as an import of its own "
                f"(ADR-076 point 1). Put it in backticks, or reword it.",
            )


# --- what a lifecycle step newly binds (ADR-076 point 6) ---------------------------------


@dataclass(frozen=True)
class SetReading:
    """One reading of a loaded set's accepted rules: by id, each rule's title and its
    statement, with the set as cited and its version."""

    citation: str
    component: str | None
    version: str | None
    rules: Mapping[str, tuple[str, str]]


def read_set(rule_set: rs.RuleSet | None) -> SetReading | None:
    """A set's accepted rules as `compare` reads them; None for no set."""
    if rule_set is None:
        return None
    rules: dict[str, tuple[str, str]] = {}
    for rule in rule_set.rules:
        if not rule.binds:
            continue
        heading, _, statement = rule.section.partition("\n")
        title = lrs.heading_title(heading.lstrip("#").strip(), rule.id)
        rules[rule.id] = (title, " ".join(statement.split()))
    return SetReading(rule_set.citation, rule_set.component, rule_set.version, rules)


def read_component(component: str, component_dir: Path) -> SetReading | None:
    """The loaded set a component's files hold where they are now, read as
    `rs.component_rule_sets` reads them, or None: the backbone's at `.pkit/`, a
    capability's at its tree."""
    discovery = rs.component_rule_sets(component, component_dir)
    return read_set(lrs.first_loaded(discovery, component))


@dataclass(frozen=True)
class Bound:
    """What a step newly binds of one set (`compare`)."""

    citation: str
    component: str | None
    before: str | None  # the version replaced; None where the set is newly delivered
    after: str | None
    first: bool
    binds: tuple[tuple[str, str], ...] = ()
    changes: tuple[tuple[str, str], ...] = ()
    retires: tuple[tuple[str, str], ...] = ()

    @property
    def any(self) -> bool:
        return bool(self.binds or self.changes or self.retires)


def compare(before: SetReading | None, after: SetReading) -> Bound:
    """The rules `after` newly binds, changes or retires since `before`, by id, status and
    statement: accepted now and not then, accepted both times with another statement or
    title, and accepted then and not now. With no `before`, every accepted rule newly
    binds. It knows no layer."""
    was: Mapping[str, tuple[str, str]] = before.rules if before is not None else {}
    binds = tuple((i, t) for i, (t, _s) in after.rules.items() if i not in was)
    changes = tuple((i, t) for i, (t, s) in after.rules.items() if i in was and was[i] != (t, s))
    retires = tuple((i, t) for i, (t, _s) in was.items() if i not in after.rules)
    return Bound(
        after.citation,
        after.component,
        before.version if before is not None else None,
        after.version,
        before is None,
        binds,
        changes,
        retires,
    )


def render_bound(bound: Sequence[Bound], *, capabilities_delivered: bool) -> str:
    """What install, sync and upgrade print: for each loaded set delivered, its name and
    version and each rule it newly binds, changes or retires. Where no adapter in use
    declares a delivery, a capability's set says that its rules bind no session here,
    rather than list them as bound (COR-070 point 3). Information, not a gate."""
    if not bound:
        return ""
    lines = ["", "  " + "Loaded rules — what this step newly binds (COR-070 point 3):"]
    for item in bound:
        version = item.after or "no version"
        moved = (
            f"{version} (first delivered)"
            if item.first
            else (f"{item.before} -> {version}" if item.before != item.after else version)
        )
        head = f"    {item.citation} {moved}"
        is_capability = item.component not in (None, fd.BACKBONE_COMPONENT)
        if is_capability and not capabilities_delivered:
            lines.append(
                f"{head}: its rules bind no session in this project, since no adapter in use "
                f"delivers a capability's rules."
            )
            continue
        if not item.any:
            lines.append(f"{head}: no rule newly binds, changes or retires.")
            continue
        lines.append(f"{head}:")
        for verb, rules in (
            ("binds", item.binds),
            ("changes", item.changes),
            ("retires", item.retires),
        ):
            lines.extend(f"      {verb:<8} {rule_id}  {title}" for rule_id, title in rules)
    return "\n".join(lines)


def echo_bound(target_root: Path, bound: Sequence[Bound]) -> None:
    """Print `render_bound` for the sets a step delivered, reading the adapters in use."""
    if not bound:
        return
    delivered = bool(delivery_forms(target_root).forms)
    click.echo(render_bound(bound, capabilities_delivered=delivered))


def component_folder(target_root: Path, component: str) -> Path:
    """Where a component's files are in the project: the backbone's at `.pkit/`, a
    capability's at its tree."""
    if component == fd.BACKBONE_COMPONENT:
        return target_root / ".pkit"
    return target_root / fd.CAPABILITIES_DIR / component


def read_delivered(target_root: Path) -> dict[str, SetReading | None]:
    """Each component's loaded set as the project holds it now, the backbone's and each
    registered capability's: what a step reads before it copies (ADR-076 point 6)."""
    names = [fd.BACKBONE_COMPONENT, *fd.installed_capability_names(target_root)]
    return {name: read_component(name, component_folder(target_root, name)) for name in names}


def bound_by(
    before: Mapping[str, SetReading | None], delivered: Sequence[tuple[str, Path]]
) -> tuple[Bound, ...]:
    """What a step newly binds: each component it delivers, read where the step copies it
    from (or, for a step that copies nothing, where it is), compared with its reading
    `before`. A component that brings no loaded set is left out."""
    found: list[Bound] = []
    for name, folder in delivered:
        after = read_component(name, folder)
        if after is not None:
            found.append(compare(before.get(name), after))
    return tuple(found)


# --- `pkit rule-sets loaded` --------------------------------------------------------------


def loaded_document(target_root: Path) -> dict[str, Any]:
    """The stable JSON document `pkit rule-sets loaded --json` prints."""
    return {
        "schema_version": 1,
        "loaded": [f.as_json() for f in loaded_files(target_root)],
        "index": {"path": str(INDEX_FILE), "present": (target_root / INDEX_FILE).is_file()},
    }


def render_loaded_human(target_root: Path) -> str:
    """The read view: each layer's loaded file with its owner, in the order a session
    reads them."""
    loaded = loaded_files(target_root)
    rows = [
        (
            f.layer,
            f.owner,
            f.path,
            (f"{f.rule_set} ({f.set_path})" if f.rule_set else "a plain file")
            + ("" if f.present else ", missing"),
        )
        for f in loaded
    ]
    lines = [f"Loaded files — {len(loaded)}   (every layer's, in the order a session reads them)"]
    lines.append("")
    if not rows:
        lines.append("  (none)")
    widths = [max((len(row[i]) for row in rows), default=0) for i in range(3)]
    for row in rows:
        cells = [row[i].ljust(widths[i]) for i in range(3)]
        lines.append("  " + "  ".join([*cells, row[3]]).rstrip())
    return "\n".join(lines) + "\n"


def render_index_for(target_root: Path, adapter: str) -> str:
    """The index's text for one registered adapter's form, as `--index` prints it."""
    deliveries = delivery_forms(target_root)
    named = [f for f in deliveries.forms if f.adapter == adapter]
    if not named and adapter not in deliveries.undeclared:
        raise click.ClickException(f"no registered adapter is named {adapter!r}.")
    return render_index(loaded_files(target_root), Deliveries(tuple(named), ()))
