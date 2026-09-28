"""The validator registry behind `pkit validate` (ADR-058).

`pkit validate` is the one umbrella over every deterministic check of the
repository's *state* (COR-004). Each functionality registers a **validator**:
a name, an order, and a callable that reads the project at a root and answers
with an `Outcome` — the lines that summarise what it checked, and its
findings, each with a severity. The backbone registers its members in this
module (`BACKBONE_VALIDATORS`); a capability registers its own in its package
metadata (`validators:`, the lifecycle README's package-metadata reference),
which `capability_validators` reads defensively — a malformed entry is the
packages member's finding, never a crash here.

**Severity is the whole contract between a member and the umbrella.**

- `error` fails `pkit validate` (exit 1).
- `warning`, `info` and `report` print and never fail. A warning asks for
  attention (an unknown key with the nearest known one suggested, a declared
  reference the body has drifted from); an info states a fact (a default in
  use); a report is what an owning record says is *reported rather than
  judged* (an inert point block, an orphaned fill — COR-053 point 10,
  COR-051 point 9).

The members stay callable alone — `pkit schemas validate`, `pkit decisions
validate`, `pkit refs validate`, `pkit data validate <path>` and `pkit process
validate <address>` are the focused surfaces — and the umbrella never changes
what a member computes: it renders every outcome under one heading per
functionality, through one renderer, and applies the one exit rule.

**Not registered.** The diff-scoped checks — `pkit friction check`, `pkit
migrations check-diff`, `pkit release lint` — read a base ref and answer about
a *change*, not the tree's state. They stay their own lines of the check
aggregator (`scripts/check.sh`, the enforcement boundary of ADR-019).

**A capability's validator is a query command** in the sense of ADR-057
(bounded, deterministic, needing no network, read-only): the registry starts
its script from the project root with no arguments, bounds it by the same
constant the predicate runner uses, and reads one JSON document from its
standard output — `{"summary": [...], "findings": [{"severity", "location",
"message"}, ...]}`. No answer — an abnormal exit, a timeout, output that is
not that document — is an *error finding*, never a clean pass: the umbrella
fails closed. The start-bound-capture-parse primitive the runners share is
#1035's extraction; until it lands the runner here is the smallest thing that
honours the contract.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from project_kit import cli_render

# The owner of the backbone's own members; a capability's members are owned
# by the capability and addressed `<capability>:<name>`.
BACKBONE_OWNER = "backbone"

# The package-metadata key a component registers its validators under.
VALIDATORS_KEY = "validators"

# Where a capability's validators sort when their entries name no `order`:
# after every backbone member, in capability order.
CAPABILITY_ORDER_DEFAULT = 1000

# The time bound on a capability's validator script — the same thirty seconds
# the process engine gives a predicate (ADR-057 point 3).
QUERY_TIMEOUT_SECONDS = 30

_yaml = YAML(typ="safe")


# --- the shape --------------------------------------------------------


class Severity(Enum):
    """What a finding does to `pkit validate`: only `error` fails it."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    REPORT = "report"

    @property
    def fails(self) -> bool:
        return self is Severity.ERROR


@dataclass(frozen=True)
class Finding:
    """One finding of a validator.

    `location` is where to look, relative to the project root: a path, a path
    with a JSON Pointer (`file.yaml:/a/b`), or an entry inside a file
    (`rules.md#RS-CMN-001`). `label` is an optional qualifier printed after
    the location — the versions member names the relation a finding checks.
    """

    location: str
    message: str
    severity: Severity = Severity.ERROR
    label: str = ""


@dataclass(frozen=True)
class Outcome:
    """What a validator answers: summary lines, then findings."""

    summary: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()

    def count(self, severity: Severity) -> int:
        return sum(1 for f in self.findings if f.severity is severity)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity.fails)


@dataclass(frozen=True)
class Validator:
    """One registered member: its name, its order among the members, and how to run it."""

    name: str
    run: Callable[[Path], Outcome]
    order: int
    owner: str = BACKBONE_OWNER
    help: str = ""

    @property
    def sort_key(self) -> tuple[int, str, str]:
        return (self.order, self.owner, self.name)


@dataclass(frozen=True)
class Result:
    validator: Validator
    outcome: Outcome


# --- the backbone's members -------------------------------------------
#
# Each member's `run` imports its module when called, so listing the registry
# costs nothing and a member's module loads only when it runs. The order is
# the order of dependence: what a later member reads, an earlier one checked.


def _manifests(root: Path) -> Outcome:
    from project_kit import validate

    return validate.manifests_outcome(root)


def _schemas(root: Path) -> Outcome:
    from project_kit import schemas_validate

    return schemas_validate.outcome(root)


def _configuration(root: Path) -> Outcome:
    from project_kit import config_validate

    return config_validate.outcome(root)


def _packages(root: Path) -> Outcome:
    from project_kit import package_validate

    return package_validate.outcome(root)


def _connections(root: Path) -> Outcome:
    from project_kit import connections

    return connections.connections_outcome(root)


def _versions(root: Path) -> Outcome:
    from project_kit import connections

    return connections.versions_outcome(root)


def _friction(root: Path) -> Outcome:
    from project_kit import friction_validate

    return friction_validate.outcome(root)


def _rule_sets(root: Path) -> Outcome:
    from project_kit import rule_sets

    return rule_sets.outcome(root)


def _decisions(root: Path) -> Outcome:
    from project_kit import decisions_validate

    return decisions_validate.outcome(root)


def _refs(root: Path) -> Outcome:
    from project_kit import refs

    return refs.outcome(root)


def _process(root: Path) -> Outcome:
    from project_kit import process

    return process.definitions_outcome(root)


def _data(root: Path) -> Outcome:
    from project_kit import data_validate

    return data_validate.outcome(root)


_BACKBONE_MEMBERS: tuple[tuple[str, Callable[[Path], Outcome], str], ...] = (
    ("manifests", _manifests, "the backbone manifest and the component registry"),
    ("schemas", _schemas, "every schema pair, pointered instance and backbone file schema"),
    ("configuration", _configuration, "the configuration file against its schema and records"),
    ("packages", _packages, "every registered component's package metadata"),
    ("connections", _connections, "the wiring the packages and selections resolve to"),
    ("versions", _versions, "every version relation"),
    ("friction", _friction, "artefacts in the declared places: the container, deferrals, cycles"),
    ("rule-sets", _rule_sets, "every rule-set file: shape, ids, origins, inheritance"),
    ("decisions", _decisions, "decision-record front matter and id spaces"),
    ("refs", _refs, "the reference graph across agents, skills and hooks"),
    ("process", _process, "every process definition resolves"),
    ("data", _data, "adopter data files bound to a capability schema"),
)

BACKBONE_VALIDATORS: tuple[Validator, ...] = tuple(
    Validator(name=name, run=run, order=(index + 1) * 10, help=help_text)
    for index, (name, run, help_text) in enumerate(_BACKBONE_MEMBERS)
)


# --- a capability's members -------------------------------------------


def capability_validators(target_root: Path) -> tuple[Validator, ...]:
    """The validators every registered component declares in its package metadata.

    Read defensively: a package file that does not parse, a `validators:` that
    is not a mapping, or an entry without a string `script` contributes
    nothing here — the packages member reports the defect. `order` is taken
    when it is an integer, else the capability default.
    """
    from project_kit.package_validate import installed_package_files

    out: list[Validator] = []
    for owner, component_dir, package in installed_package_files(target_root):
        block = _validators_block(package)
        for raw_name, spec in block.items():
            name = str(raw_name)
            if not isinstance(spec, Mapping) or not isinstance(spec.get("script"), str):
                continue
            order = spec.get("order")
            out.append(
                Validator(
                    name=f"{owner}:{name}",
                    run=_script_runner(
                        component_dir / spec["script"],
                        location=f"{_rel(package, target_root)}:/{VALIDATORS_KEY}/{name}",
                    ),
                    order=order if isinstance(order, int) and not isinstance(order, bool)
                    else CAPABILITY_ORDER_DEFAULT,
                    owner=owner,
                    help=str(spec.get("help") or ""),
                )
            )
    return tuple(out)


def _validators_block(package: Path) -> Mapping[Any, Any]:
    try:
        raw = _yaml.load(package.read_text(encoding="utf-8"))
    except Exception:  # ruamel raises its own hierarchy; the packages member reports it
        return {}
    block = raw.get(VALIDATORS_KEY) if isinstance(raw, Mapping) else None
    return block if isinstance(block, Mapping) else {}


def _script_runner(script: Path, *, location: str) -> Callable[[Path], Outcome]:
    def run(target_root: Path) -> Outcome:
        return run_script(target_root, script, location=location)

    return run


def run_script(target_root: Path, script: Path, *, location: str) -> Outcome:
    """Run one capability validator script and read its answer (the contract in the
    module docstring). No answer is an error finding at `location` — the
    validator's own entry in the package file — so the umbrella fails closed."""
    rel = _rel(script, target_root)
    if not script.is_file():
        return _no_answer(location, f"validator script {rel!r} does not exist.")
    try:
        completed = subprocess.run(
            [str(script)],
            cwd=str(target_root),
            capture_output=True,
            text=True,
            timeout=QUERY_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError as exc:
        return _no_answer(location, f"validator script {rel!r} could not start: {exc}")
    except subprocess.TimeoutExpired:
        return _no_answer(
            location,
            f"validator script {rel!r} did not answer within {QUERY_TIMEOUT_SECONDS} s.",
        )
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        tail = f": {detail[-1]}" if detail else "."
        return _no_answer(
            location, f"validator script {rel!r} exited {completed.returncode}{tail}"
        )
    return parse_answer(completed.stdout, location=location, script=rel)


def parse_answer(text: str, *, location: str, script: str) -> Outcome:
    """The findings document a validator script prints, as an Outcome; a document
    that is not one is an error finding."""
    try:
        document = json.loads(text)
    except ValueError:
        return _no_answer(location, f"validator script {script!r} did not print a JSON document.")
    if not isinstance(document, Mapping):
        return _no_answer(location, f"validator script {script!r} printed {_kind(document)}, not a findings document.")
    findings: list[Finding] = []
    for index, entry in enumerate(_list(document.get("findings"))):
        finding = _finding(entry)
        if finding is None:
            return _no_answer(
                location,
                f"validator script {script!r} answered with a malformed finding at index {index}: "
                f"expected `severity` (one of {_severities()}), `location` and `message`.",
            )
        findings.append(finding)
    summary = tuple(str(line) for line in _list(document.get("summary")))
    return Outcome(summary=summary, findings=tuple(findings))


def _finding(entry: Any) -> Finding | None:
    if not isinstance(entry, Mapping):
        return None
    severity_value, location, message = entry.get("severity"), entry.get("location"), entry.get("message")
    if not isinstance(severity_value, str) or not isinstance(location, str) or not isinstance(message, str):
        return None
    try:
        severity = Severity(severity_value)
    except ValueError:
        return None
    label = entry.get("label")
    return Finding(location, message, severity, label if isinstance(label, str) else "")


def _no_answer(location: str, message: str) -> Outcome:
    return Outcome(summary=("no answer.",), findings=(Finding(location, message),))


def _severities() -> str:
    return ", ".join(s.value for s in Severity)


# --- the registry, the run, the rendering -----------------------------


def registered_validators(target_root: Path) -> tuple[Validator, ...]:
    """Every member, in the order they run: the backbone's, then each capability's."""
    members = (*BACKBONE_VALIDATORS, *capability_validators(target_root))
    return tuple(sorted(members, key=lambda v: v.sort_key))


def select(
    validators: Iterable[Validator], *, only: Sequence[str] = (), skip: Sequence[str] = ()
) -> tuple[Validator, ...]:
    """The members to run: `only` keeps the named ones, `skip` drops them.
    Raises ValueError naming a member neither list can address."""
    registered = list(validators)
    names = {v.name for v in registered}
    unknown = sorted((set(only) | set(skip)) - names)
    if unknown:
        raise ValueError(
            f"unknown validator(s) {', '.join(repr(n) for n in unknown)}; "
            f"registered: {', '.join(v.name for v in registered)}."
        )
    return tuple(
        v for v in registered if (not only or v.name in only) and v.name not in skip
    )


def run_all(target_root: Path, validators: Iterable[Validator]) -> list[Result]:
    return [Result(v, v.run(target_root)) for v in validators]


def has_errors(results: Iterable[Result]) -> bool:
    return any(r.outcome.errors for r in results)


def render(target_root: Path, results: Sequence[Result]) -> str:
    """The `pkit validate` report: one section per member, then one summary.

    A section is the member's heading, its summary lines, and each finding as
    `<severity>  <location>[  [label]]` over `→ <message>` — the same two
    lines whatever the member, so a misspelt key in the configuration file
    and one in a package file read the same (ADR-056 point 4).
    """
    lines = ["", cli_render.style("title", f"Validating {target_root}"), ""]
    for result in results:
        lines.append("  " + cli_render.style("heading", result.validator.name))
        lines.extend(f"    {line}" for line in result.outcome.summary)
        for finding in result.outcome.findings:
            label = f"  [{finding.label}]" if finding.label else ""
            lines.append(f"    {finding.severity.value:<9}{finding.location}{label}")
            lines.append(f"      → {finding.message}")
        lines.append("")
    counts = ", ".join(
        f"{sum(r.outcome.count(s) for r in results)} {s.value}(s)" for s in Severity
    )
    lines.append(f"  {len(results)} validator(s) ran; {counts}.")
    errors = sum(len(r.outcome.errors) for r in results)
    verdict = "All checks passed." if not errors else f"{errors} error(s) found."
    lines.append("  " + cli_render.style("strong", verdict))
    lines.append("")
    return "\n".join(lines)


# --- helpers ----------------------------------------------------------


def _rel(path: Path, target_root: Path) -> str:
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _kind(value: Any) -> str:
    return "null" if value is None else f"a {type(value).__name__}"


def location_of(path: Path, target_root: Path, pointer: str = "") -> str:
    """A finding's location: the path relative to the root, then `:` and the pointer when there is one."""
    rel = _rel(path, target_root)
    return f"{rel}:{pointer}" if pointer else rel


def counts_line(findings: Iterable[Finding], *severities: Severity) -> str:
    """`N error(s), M warning(s)` — one count per severity given, in that order."""
    listed = list(findings)
    return ", ".join(
        f"{sum(1 for f in listed if f.severity is s)} {s.value}(s)" for s in severities
    )
