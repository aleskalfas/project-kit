"""Harness support: each adapter's answers to the core's harness requirements, and
the report of what a project's harness leaves unmet (COR-047 points 2 to 5).

The core declares what it requires of the harness that hosts it, as observable
behaviour, in `.pkit/schemas/harness-requirements.yaml`. Each adapter answers
for its own harness in its **support declaration**, `harness-support.yaml` in
its folder, shaped by `.pkit/schemas/harness-support.schema.json`: per core
requirement, a **grade** (`supported`, `at-cost` or `not-achievable`, the
vocabulary the adapters README owns), the cost an `at-cost` answer asks, the
harness versions the answer holds for, and the evidence for it.

The report resolves every core requirement, for each adapter the backbone
manifest registers, to exactly one of `satisfied`, `unsatisfied` or
`indeterminate`, with the adapter's grade and the provenance. It reads files
only: it never starts the harness, reads no configuration, environment or
version of it, and writes nothing. So it reaches no requirement's observation
point (COR-047 point 4), and resolves a `supported` or `at-cost` answer
`indeterminate`: nothing was read to confirm it. Only a `not-achievable` answer
that holds for every version resolves without one: the answer says the harness
cannot do it whatever its configuration, so the declaration is the whole input
and the result, `unsatisfied`, is `computed` (point 5). An answer that holds
for no version, or for a range of versions the pass cannot check, is not read
as the harness's support. No result is ever `satisfied` before an adapter gives
a pass a way to observe one.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit.manifest import read_backbone_manifest

#: The core's harness requirements, from the root.
REQUIREMENTS_FILE = Path(".pkit") / "schemas" / "harness-requirements.yaml"
#: The schema that shapes every adapter's support declaration, from the root.
SCHEMA_FILE = Path(".pkit") / "schemas" / "harness-support.schema.json"
#: An adapter's support declaration, in the adapter's folder.
DECLARATION = "harness-support.yaml"

SUPPORTED = "supported"
AT_COST = "at-cost"
NOT_ACHIEVABLE = "not-achievable"

SATISFIED = "satisfied"
UNSATISFIED = "unsatisfied"
INDETERMINATE = "indeterminate"

#: Derived by the pass from inputs it read in full (COR-047 point 5).
COMPUTED = "computed"

#: `harness_versions` for an answer that holds for every version.
UNBOUNDED = "unbounded"

#: Where a requirement's truth is visible, in words, for the reason a pass gives
#: (the observation points of `harness-requirements.schema.json`).
_WHERE = {
    "out-of-session": "outside a session, in the harness's configuration, environment, "
    "version or platform",
    "interposed-runtime": "only to code the harness runs at its own hook points",
    "in-session": "only to an agent inside a session of the harness",
}

_NAME = re.compile(r"[a-z][a-z0-9-]*")

_yaml: Any = YAML(typ="safe")


class SupportError(Exception):
    """The core's requirements, or an adapter's declaration, cannot be read."""


@dataclass(frozen=True)
class Requirement:
    """One core harness requirement, as the report needs it."""

    id: str
    title: str
    observation_point: str


@dataclass(frozen=True)
class Result:
    """One requirement resolved for one adapter's harness. `grade` is the adapter's
    grade where its answer covers the harness; `None` where there is no answer, or
    one that covers no version."""

    requirement: Requirement
    result: str
    reason: str
    grade: str | None = None
    provenance: str | None = None
    cost: str | None = None
    harness_versions: str | tuple[str, ...] | None = None

    @property
    def met(self) -> bool:
        return self.result == SATISFIED

    def as_json(self) -> dict[str, Any]:
        versions = self.harness_versions
        return {
            "id": self.requirement.id,
            "title": self.requirement.title,
            "observation_point": self.requirement.observation_point,
            "result": self.result,
            "grade": self.grade,
            "provenance": self.provenance,
            "cost": self.cost,
            "harness_versions": list(versions) if isinstance(versions, tuple) else versions,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class AdapterReport:
    """Every core requirement, resolved for one adapter's harness."""

    adapter: str
    declaration: str | None
    results: tuple[Result, ...] = field(default_factory=tuple)

    @property
    def unmet(self) -> tuple[Result, ...]:
        return tuple(r for r in self.results if not r.met)

    def as_json(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "declaration": self.declaration,
            "requirements": [r.as_json() for r in self.results],
            "unmet": len(self.unmet),
        }


# --- reading ---------------------------------------------------------------------------


def _load_yaml(path: Path, shown: str) -> Any:
    try:
        return _yaml.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise SupportError(f"{shown} cannot be read ({exc})") from None
    except YAMLError as exc:
        raise SupportError(" ".join(f"{shown} does not parse ({exc})".split())) from None


def requirements(root: Path) -> list[Requirement]:
    """The core's harness requirements, in the order the file declares them."""
    path = root / REQUIREMENTS_FILE
    shown = REQUIREMENTS_FILE.as_posix()
    if not path.is_file():
        raise SupportError(f"{shown} is missing")
    document = _load_yaml(path, shown)
    raw: Any = (
        cast(Mapping[str, Any], document).get("requirements")
        if isinstance(document, Mapping)
        else None
    )
    if not isinstance(raw, Mapping):
        raise SupportError(f"{shown} holds no `requirements` mapping")
    found: list[Requirement] = []
    for rid, entry in cast(Mapping[str, Any], raw).items():
        if not isinstance(entry, Mapping):
            raise SupportError(f"{shown}: requirement {rid!r} is not a mapping")
        fields = cast(Mapping[str, Any], entry)
        found.append(
            Requirement(
                id=str(rid),
                title=" ".join(str(fields.get("title") or "").split()),
                observation_point=str(fields.get("observation_point") or ""),
            )
        )
    return found


def is_adapter(root: Path, name: str) -> bool:
    """True when `name` is a plain name with a folder under `.pkit/adapters/`."""
    return bool(_NAME.fullmatch(name)) and (root / ".pkit" / "adapters" / name).is_dir()


def declaration_path(root: Path, adapter: str) -> Path:
    """Where `adapter` keeps its support declaration."""
    return root / ".pkit" / "adapters" / adapter / DECLARATION


def shape_problems(root: Path, adapter: str) -> list[tuple[str, str]]:
    """Each place `adapter`'s support declaration fails to parse or fails its schema,
    as (JSON pointer, message). A missing file is none: an adapter owes no
    declaration to exist (COR-047 point 3)."""
    path = declaration_path(root, adapter)
    if not path.is_file():
        return []
    try:
        document = _load_yaml(path, path.relative_to(root).as_posix())
    except SupportError as exc:
        return [("", str(exc))]
    import jsonschema

    try:
        schema: Any = json.loads((root / SCHEMA_FILE).read_text(encoding="utf-8"))
        validator: Any = jsonschema.Draft202012Validator(schema)
    except (OSError, ValueError, jsonschema.SchemaError) as exc:
        return [("", f"its schema, {SCHEMA_FILE.as_posix()}, cannot be read ({exc})")]
    errors: list[Any] = sorted(
        validator.iter_errors(document), key=lambda error: list(error.absolute_path)
    )
    return [
        ("/" + "/".join(str(part) for part in error.absolute_path), error.message)
        for error in errors
    ]


def unknown_answers(root: Path, adapter: str, known: Sequence[Requirement]) -> list[str]:
    """The requirement ids `adapter`'s declaration answers that the core does not
    declare: retired, or newer than this backbone. Empty for a declaration that
    is missing or fails its schema."""
    path = declaration_path(root, adapter)
    if not path.is_file() or shape_problems(root, adapter):
        return []
    document: Any = _load_yaml(path, path.relative_to(root).as_posix())
    answers = cast(Mapping[str, Any], document.get("requirements") or {})
    known_ids = {r.id for r in known}
    return [str(rid) for rid in answers if rid not in known_ids]


def load_declaration(root: Path, adapter: str) -> dict[str, Any] | None:
    """`adapter`'s support declaration, or None when it declares nothing. One that
    does not parse or that its schema refuses is an error, never read as a
    partial answer."""
    path = declaration_path(root, adapter)
    if not path.is_file():
        return None
    shown = path.relative_to(root).as_posix()
    problems = shape_problems(root, adapter)
    if problems:
        where, message = problems[0]
        raise SupportError(f"{shown}{where}: {message}")
    return dict(_load_yaml(path, shown))


def registered_adapters(root: Path) -> list[str]:
    """Each adapter the backbone manifest registers, in its order: the project's
    harness, as the run command reads it (ADR-066 point 1)."""
    backbone = read_backbone_manifest(root)
    if backbone is None:
        return []
    return [entry.name for entry in backbone.components if entry.kind == "adapter"]


# --- resolving -------------------------------------------------------------------------


def resolve(requirement: Requirement, answer: Mapping[str, Any] | None) -> Result:
    """Resolve one requirement from one adapter's answer (COR-047 points 3 to 5).

    No answer, and an answer that covers no version, are indeterminate with no
    grade. An answer bounded to tested versions is indeterminate: the pass does
    not read the harness's version. A `not-achievable` answer for every version is
    unsatisfied, computed from the answer alone. Any other is indeterminate: the
    pass reaches no observation point to confirm it."""
    if answer is None:
        return Result(
            requirement,
            INDETERMINATE,
            "no declaration: the adapter does not answer this requirement",
        )
    grade = str(answer.get("grade"))
    cost = " ".join(str(answer["cost"]).split()) if answer.get("cost") else None
    raw: Any = answer.get("harness_versions")
    versions: str | tuple[str, ...] = (
        tuple(str(v) for v in cast(list[Any], raw)) if isinstance(raw, list) else str(raw)
    )
    if versions == ():
        return Result(
            requirement,
            INDETERMINATE,
            f"the adapter's answer ({grade}) covers no harness version yet: its author "
            "has tested it on none",
            harness_versions=versions,
        )
    if isinstance(versions, tuple):
        return Result(
            requirement,
            INDETERMINATE,
            f"the answer holds for harness versions {versions[0]} to {versions[1]}, and "
            "this pass does not read the harness's version",
            grade,
            None,
            cost,
            versions,
        )
    if grade == NOT_ACHIEVABLE:
        return Result(
            requirement,
            UNSATISFIED,
            "the adapter declares it not achievable on this harness, whatever its configuration",
            grade,
            COMPUTED,
            cost,
            versions,
        )
    where = _WHERE.get(requirement.observation_point, requirement.observation_point)
    return Result(
        requirement,
        INDETERMINATE,
        f"its truth is visible {where} ({requirement.observation_point}); this pass "
        "reads only files, so nothing was read to confirm the declared grade",
        grade,
        None,
        cost,
        versions,
    )


def report(root: Path, adapters: Sequence[str] | None = None) -> list[AdapterReport]:
    """Every core requirement, resolved for each adapter in `adapters`, else each
    the manifest registers. Raises `SupportError` when the requirements, or a
    declaration, cannot be read."""
    known = requirements(root)
    names = list(adapters) if adapters is not None else registered_adapters(root)
    reports: list[AdapterReport] = []
    for name in names:
        # A registered name that is no plain name is never read as a path.
        document = load_declaration(root, name) if _NAME.fullmatch(name) else None
        answers: Mapping[str, Any] = (document or {}).get("requirements") or {}
        shown = (
            declaration_path(root, name).relative_to(root).as_posix()
            if document is not None
            else None
        )
        results = tuple(resolve(r, answers.get(r.id)) for r in known)
        reports.append(AdapterReport(name, shown, results))
    return reports


# --- rendering -------------------------------------------------------------------------


def unmet_count(reports: Sequence[AdapterReport], known: Sequence[Requirement]) -> int:
    """How many results are unmet: every requirement when no adapter is registered."""
    if not reports:
        return len(known)
    return sum(len(r.unmet) for r in reports)


def render_json(reports: Sequence[AdapterReport], known: Sequence[Requirement]) -> str:
    document = {
        "schema_version": 1,
        "requirements": [r.id for r in known],
        "adapters": [r.as_json() for r in reports],
        "unmet": unmet_count(reports, known),
    }
    return json.dumps(document, indent=2) + "\n"


#: What each token the human report shows means, in the order the Legend lists them.
_LEGEND = (
    (SATISFIED, "the harness meets it, as the pass confirmed"),
    (UNSATISFIED, "the harness does not meet it"),
    (INDETERMINATE, "not confirmed either way; never counted as satisfied (COR-047 point 3)"),
    (SUPPORTED, "the adapter: the harness provides it, nothing more asked"),
    (AT_COST, "the adapter: achievable, at the cost the row names"),
    (NOT_ACHIEVABLE, "the adapter: not achievable on this harness, whatever its configuration"),
    (COMPUTED, "derived by the pass from inputs it read in full (COR-047 point 5)"),
)


def _why(result: Result) -> str:
    """The row's reason, and the cost an at-cost answer that covers the harness names."""
    if result.cost is not None and result.grade is not None:
        return f"{result.reason} · cost: {result.cost}"
    return result.reason


def _row(result: Result) -> dict[str, str]:
    return {
        "result": result.result,
        "requirement": result.requirement.id,
        "grade": result.grade or "—",
        "provenance": result.provenance or "",
        "why": _why(result),
    }


_COLUMNS = ("result", "requirement", "grade", "provenance", "why")


def render_human(reports: Sequence[AdapterReport], known: Sequence[Requirement]) -> str:
    """The report as a read-view (the CLI README, "Command output conventions")."""
    from project_kit import cli_render as _cli_render

    cli_render: Any = _cli_render  # its parts are untyped dicts
    sections: list[dict[str, Any]] = []
    shown: set[str] = set()
    if not reports:
        rows = [
            _row(Result(r, INDETERMINATE, "no adapter is registered, so no harness answers it"))
            for r in known
        ]
        sections.append(
            cli_render.section(rows, _COLUMNS, header="NO ADAPTER", gloss="none is registered")
        )
    for adapter_report in reports:
        rows = [_row(r) for r in adapter_report.results]
        sections.append(
            cli_render.section(
                rows,
                _COLUMNS,
                header=adapter_report.adapter.upper(),
                gloss=adapter_report.declaration or "no support declaration",
                empty="the core declares no harness requirement",
            )
        )
    for section in sections:
        for row in cast(list[dict[str, str]], section["rows"]):
            shown.update((row["result"], row["grade"], row["provenance"]))
    total = len(known) if not reports else sum(len(r.results) for r in reports)
    return cli_render.view(
        title=cli_render.title(
            "Harness requirements",
            f"{unmet_count(reports, known)} unmet of {total}",
            "what the project's harness leaves unmet, from its adapter's declaration",
        ),
        sections=sections,
        legend=[(token, meaning) for token, meaning in _LEGEND if token in shown],
        commands=[("pkit harness report --json", "the machine form")],
    )
