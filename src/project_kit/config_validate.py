"""The backbone configuration pass of `pkit validate` (COR-048 point 4).

The project's declarations to the backbone live in one project-owned file,
`.pkit/project/config.yaml` (COR-048 point 1; `report_context` reads its
`name` key). This module is the *strict* side of COR-048's "strict when
checked, forgiving when read": it validates the whole file against the
backbone-shipped `config.schema.json` (loaded from the project's tree, never
from a copy in the binary — ADR-056 point 1) and then runs the repository
checks the owning records ask for:

- **Shape.** Every JSON Schema violation is a finding; an unknown key is
  rendered by the shared renderer with the nearest known key
  (`backbone_schemas.render_unknown_key`, ADR-056 point 4). An absent or
  empty file is clean — defaults apply (COR-048 point 3); an unparsable one
  is an error.
- **Documentation roots** (COR-049 points 1 and 7): each root resolves, after
  following links, inside the repository and outside `.pkit/` — otherwise an
  error; a root that does not exist yet is a warning.
- **Friction paths** (COR-050 points 12 and 14): each place / surface /
  exclude pattern stays inside the repository — otherwise an error; a pattern
  matching nothing is a warning.
- **Connections** (COR-053 point 7, COR-052 point 4): each provider or
  contributor selection names an installed capability, read from the
  backbone manifest — otherwise an error naming the fix. Whether that
  capability *provides the role* or *fills the point* cannot be checked until
  package metadata declares connections; until then that is reported as
  information, never an error.

Findings are structured records (a JSON Pointer into the file, a severity,
a message) in a deterministic order: shape findings by position, then the
repository checks in a fixed order — docs, friction, connections — each entry in written order. Only errors fail validation.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

import click
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import backbone_schemas, cli_render
from project_kit.manifest import read_backbone_manifest
from project_kit.project_config import PROJECT_CONFIG_RELPATH, project_config_path

# The schema kind under `.pkit/schemas/backbone/` (ADR-056 point 1).
CONFIG_SCHEMA_KIND = "config"

# The methodology's own tree, which no documentation root may resolve into
# (COR-049 point 1).
METHODOLOGY_TREE = ".pkit"

# Where the records' repository checks look, by top-level key.
DOCS_KEY = "docs"
FRICTION_KEY = "friction"
FRICTION_PATTERN_KEYS = ("places", "surface", "exclude")
CONNECTIONS_KEY = "connections"
PROVIDERS_KEY = "providers"
SELECTIONS_KEY = "selections"

# What a key of the two pattern-constrained connection maps must look like,
# for the finding when one does not (COR-053 point 2's address forms).
ADDRESS_FORMS = {
    PROVIDERS_KEY: "<publisher>::<role>",
    SELECTIONS_KEY: "<publisher>::<role>:<point>",
}


class Severity(Enum):
    """Whether a finding fails validation, is only reported, or merely informs."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ConfigFinding:
    """One finding on the configuration file.

    `path` is a JSON Pointer into the file from its root (`""` for the file as
    a whole, `/docs/user` for a value).
    """

    path: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class ConfigReport:
    """Outcome of the pass over one project's configuration file."""

    location: str  # the file, relative to the project root
    present: bool  # False when absent or empty: defaults apply, nothing to check
    schema_present: bool  # False when the tree ships no config schema (skipped)
    findings: tuple[ConfigFinding, ...]

    def by_severity(self, severity: Severity) -> tuple[ConfigFinding, ...]:
        return tuple(f for f in self.findings if f.severity is severity)

    @property
    def errors(self) -> tuple[ConfigFinding, ...]:
        return self.by_severity(Severity.ERROR)

    @property
    def is_clean(self) -> bool:
        """No errors. Warnings and information never fail validation."""
        return not self.errors


def run_configuration_pass(target_root: Path) -> ConfigReport:
    """Validate the project's configuration file; never raises on its content."""
    location = PROJECT_CONFIG_RELPATH.as_posix()
    path = project_config_path(target_root)

    try:
        schema = backbone_schemas.load_backbone_schema(target_root, CONFIG_SCHEMA_KIND)
    except backbone_schemas.BackboneSchemaMissing:
        # A tree recorded before the schema landed: skip, never substitute
        # the binary's idea of the shape (ADR-056 point 1).
        return ConfigReport(
            location=location, present=path.is_file(), schema_present=False, findings=()
        )
    except backbone_schemas.BackboneSchemaInvalid as exc:
        # The load-check of `pkit schemas validate` owns the detailed report;
        # here it only means the file cannot be checked.
        return ConfigReport(
            location=location,
            present=path.is_file(),
            schema_present=True,
            findings=(ConfigFinding("", Severity.ERROR, f"cannot validate: {exc}"),),
        )

    if not path.is_file():
        return ConfigReport(location=location, present=False, schema_present=True, findings=())

    data, parse_error = _load_yaml(path)
    if parse_error is not None:
        return ConfigReport(
            location=location,
            present=True,
            schema_present=True,
            findings=(ConfigFinding("", Severity.ERROR, parse_error),),
        )
    if data is None:
        # An empty file: defaults apply (COR-048 point 3).
        return ConfigReport(location=location, present=False, schema_present=True, findings=())
    if not isinstance(data, Mapping):
        return ConfigReport(
            location=location,
            present=True,
            schema_present=True,
            findings=(
                ConfigFinding(
                    "",
                    Severity.ERROR,
                    f"the file must be a mapping of keys to values, not {_type_name(data)}.",
                ),
            ),
        )

    config = _string_keys(data)
    findings = _shape_findings(config, schema)
    # A value the shape pass refused is not checked again against the
    # repository: one finding per mistake.
    flagged = frozenset(f.path for f in findings)
    findings.extend(_docs_findings(target_root, config.get(DOCS_KEY), flagged))
    findings.extend(_friction_findings(target_root, config.get(FRICTION_KEY), flagged))
    findings.extend(_connections_findings(target_root, config.get(CONNECTIONS_KEY), flagged))
    return ConfigReport(
        location=location, present=True, schema_present=True, findings=tuple(findings)
    )


# --- shape -------------------------------------------------------------------


def _shape_findings(config: Mapping[str, Any], schema: Mapping[str, Any]) -> list[ConfigFinding]:
    """The JSON Schema pass, with every unknown key rendered by the shared renderer.

    Sorted by position, then message, so the order never depends on the
    validator's traversal.
    """
    registry = Registry().with_resource(
        uri=schema.get("$id", f"{CONFIG_SCHEMA_KIND}.schema.json"),
        resource=Resource.from_contents(schema, default_specification=DRAFT202012),
    )
    validator = Draft202012Validator(schema, registry=registry)
    findings: list[ConfigFinding] = []
    for error in validator.iter_errors(config):
        findings.extend(_render_schema_error(error))
    return sorted(findings, key=lambda f: (f.path, f.message))


def _render_schema_error(error: ValidationError) -> list[ConfigFinding]:
    """One finding per violation; an `additionalProperties` error becomes one per unknown key."""
    pointer = _pointer(error.absolute_path)
    if error.validator != "additionalProperties" or not isinstance(error.instance, Mapping):
        return [ConfigFinding(pointer, Severity.ERROR, error.message)]

    known = tuple((error.schema.get("properties") or {}).keys())
    patterns = error.schema.get("patternProperties") or {}
    unknown = sorted(
        key
        for key in error.instance
        if key not in known and not any(_matches(pattern, key) for pattern in patterns)
    )
    findings: list[ConfigFinding] = []
    for key in unknown:
        key_pointer = f"{pointer}/{_pointer_token(key)}"
        if known:
            message = backbone_schemas.render_unknown_key(key, known)
        else:
            # A pattern-keyed map (the two connection maps): there is no
            # known set to suggest from, only the address form the key must take.
            form = ADDRESS_FORMS.get(_last_segment(pointer), "the address form")
            message = f"key {key!r} is not a {form} address."
        findings.append(ConfigFinding(key_pointer, Severity.ERROR, message))
    return findings


def _matches(pattern: str, key: str) -> bool:
    return re.search(pattern, key) is not None


# --- documentation roots (COR-049) ------------------------------------------


def _docs_findings(target_root: Path, docs: Any, flagged: frozenset[str]) -> list[ConfigFinding]:
    if not isinstance(docs, Mapping):
        return []
    findings: list[ConfigFinding] = []
    for audience, value in docs.items():
        pointer = f"/{DOCS_KEY}/{audience}"
        if pointer in flagged or not isinstance(value, str) or not value:
            continue  # the shape pass already reported it
        findings.extend(_root_findings(target_root, pointer, value))
    return findings


def _root_findings(target_root: Path, pointer: str, value: str) -> list[ConfigFinding]:
    """One root: inside the repository and outside `.pkit/` after following links (error);
    not existing yet (warning)."""
    repo = target_root.resolve()
    candidate = target_root / value
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo):
        return [
            ConfigFinding(
                pointer,
                Severity.ERROR,
                f"documentation root {value!r} resolves to {resolved}, outside the repository; "
                f"a root must lie inside it (COR-049 point 1).",
            )
        ]
    if resolved == repo / METHODOLOGY_TREE or resolved.is_relative_to(repo / METHODOLOGY_TREE):
        return [
            ConfigFinding(
                pointer,
                Severity.ERROR,
                f"documentation root {value!r} resolves inside the methodology's own tree "
                f"({METHODOLOGY_TREE}/); a root must lie outside it (COR-049 point 1).",
            )
        ]
    if not resolved.is_dir():
        what = "is not a directory" if resolved.exists() else "does not exist yet"
        return [
            ConfigFinding(
                pointer,
                Severity.WARNING,
                f"documentation root {value!r} {what}; the default applies to readers "
                f"until it is created (COR-049 point 7).",
            )
        ]
    return []


# --- friction paths (COR-050) -----------------------------------------------


def _friction_findings(
    target_root: Path, friction: Any, flagged: frozenset[str]
) -> list[ConfigFinding]:
    if not isinstance(friction, Mapping):
        return []
    findings: list[ConfigFinding] = []
    for key in FRICTION_PATTERN_KEYS:
        patterns = friction.get(key)
        if not isinstance(patterns, list):
            continue
        for index, pattern in enumerate(patterns):
            pointer = f"/{FRICTION_KEY}/{key}/{index}"
            if pointer in flagged or not isinstance(pattern, str) or not pattern:
                continue  # the shape pass already reported it
            findings.extend(_pattern_findings(target_root, pointer, pattern))
    return findings


def _pattern_findings(target_root: Path, pointer: str, pattern: str) -> list[ConfigFinding]:
    """One path or glob: stays inside the repository (error otherwise); matches
    something (warning otherwise)."""
    normalised = os.path.normpath(pattern).replace(os.sep, "/")
    if PurePosixPath(pattern).is_absolute() or normalised == ".." or normalised.startswith("../"):
        return [
            ConfigFinding(
                pointer,
                Severity.ERROR,
                f"friction pattern {pattern!r} leaves the repository; every path in these "
                f"settings stays inside it (COR-050 point 14).",
            )
        ]
    if normalised == ".":
        return []  # the repository root itself matches everything
    if not _glob_matches_anything(target_root, normalised):
        return [
            ConfigFinding(
                pointer,
                Severity.WARNING,
                f"friction pattern {pattern!r} matches nothing in the repository; a dead "
                f"pattern keeps silence looking like health (COR-050 point 12).",
            )
        ]
    return []


def _glob_matches_anything(target_root: Path, pattern: str) -> bool:
    """Does `pattern`, relative to the root, match at least one path? `**` spans folders."""
    try:
        return next(iter(target_root.glob(pattern)), None) is not None
    except (ValueError, NotImplementedError):
        # An unsupported pattern (e.g. one glob library refuses) matches nothing.
        return False


# --- connections (COR-053, COR-052) ------------------------------------------


def _connections_findings(
    target_root: Path, connections: Any, flagged: frozenset[str]
) -> list[ConfigFinding]:
    if not isinstance(connections, Mapping):
        return []
    installed = _installed_capabilities(target_root)
    findings: list[ConfigFinding] = []
    for key, unverifiable in (
        (PROVIDERS_KEY, "provides role {address!r}"),
        (SELECTIONS_KEY, "fills point {address!r} and that it is a `single` point"),
    ):
        entries = connections.get(key)
        if not isinstance(entries, Mapping):
            continue
        for address, capability in entries.items():
            pointer = f"/{CONNECTIONS_KEY}/{key}/{_pointer_token(address)}"
            if pointer in flagged or not isinstance(capability, str) or not capability:
                continue  # the shape pass already reported it
            if capability not in installed:
                findings.append(
                    ConfigFinding(
                        pointer,
                        Severity.ERROR,
                        f"{capability!r} is not an installed capability; install it "
                        f"(`pkit capabilities install {capability}`) or remove the entry "
                        f"(COR-048 point 2).",
                    )
                )
                continue
            findings.append(
                ConfigFinding(
                    pointer,
                    Severity.INFO,
                    f"cannot verify that {capability!r} {unverifiable.format(address=address)} "
                    f"until package metadata declares connections; the capability is installed.",
                )
            )
    return findings


def _installed_capabilities(target_root: Path) -> frozenset[str]:
    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        return frozenset()
    return frozenset(entry.name for entry in manifest.components if entry.kind == "capability")


# --- rendering ---------------------------------------------------------------


def print_configuration_section(report: ConfigReport) -> None:
    """The "configuration" section of the validate report: state and every finding.

    Errors are also carried in the issue list (see `as_issues`), which is what
    fails the command; here they sit with the warnings and information so the
    whole file is read in one place.
    """
    click.echo("  " + cli_render.style("strong", "configuration") + f"  ({report.location})")
    if not report.schema_present:
        click.echo("    no config schema present in this tree; skipped.")
        click.echo()
        return
    if not report.present and not report.findings:
        click.echo("    absent or empty: defaults apply.")
        click.echo()
        return
    if not report.findings:
        click.echo("    valid.")
        click.echo()
        return
    counts = ", ".join(
        f"{len(report.by_severity(sev))} {sev.value}" for sev in Severity if report.by_severity(sev)
    )
    click.echo(f"    {counts}")
    for finding in report.findings:
        where = finding.path or "(file)"
        click.echo(f"    {finding.severity.value:<8}{where}")
        click.echo(f"      → {finding.message}")
    click.echo()


def as_issues(report: ConfigReport) -> list[tuple[str, str]]:
    """The errors as `(location, diagnosis)` pairs for the validate issue list."""
    return [
        (report.location, f"{finding.path or '(file)'}: {finding.message}")
        for finding in report.errors
    ]


# --- helpers -----------------------------------------------------------------


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    """Parse the file. Returns (data, None) or (None, reason)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"unreadable: {exc}."
    try:
        return YAML(typ="safe").load(text), None
    except YAMLError as exc:
        return None, f"does not parse as YAML: {str(exc).splitlines()[0]}"


def _string_keys(obj: Any) -> Any:
    """Every mapping key as text, recursively — JSON Schema and the renderer know only text keys."""
    if isinstance(obj, Mapping):
        return {str(k): _string_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_string_keys(x) for x in obj]
    return obj


def _type_name(value: Any) -> str:
    if isinstance(value, list):
        return "a list"
    if isinstance(value, str):
        return "a bare string"
    return f"a {type(value).__name__}"


def _pointer(segments: Iterable[Any]) -> str:
    parts = [_pointer_token(s) for s in segments]
    return "/" + "/".join(parts) if parts else ""


def _pointer_token(segment: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(segment).replace("~", "~0").replace("/", "~1")


def _last_segment(pointer: str) -> str:
    return pointer.rsplit("/", 1)[-1] if pointer else ""
