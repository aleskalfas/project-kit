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
aggregator (`scripts/check.sh`, the enforcement boundary of ADR-019). No base
named for one run reaches a member either: the query policy removes the
override from every validator and every data point's filler it starts, so
`pkit validate` answers the same for the same working tree, HEAD, fetched
history and default-branch commit, whatever base a pipeline named (ADR-058
point 7).

**A capability's validator is a query command** in the sense of ADR-057 point
3 (bounded, deterministic, needing no network, read-only). Its entry names a
leaf of the capability's `commands:` tree, so the same script is a focused
surface (`pkit <capability> <command>`) and a member of the umbrella, and the
leaf carries the declaration of the query contract, `query-contract: true`.
The registry runs the leaf's script under the *query policy* over the one
runner the backbone uses for every command it runs on a component's behalf
(`command_runner`, ADR-057 point 5): from the project root with the one
argument `--json`, the offline marker set in its environment and the base
override (`PKIT_CHECK_BASE`) removed from it, in its own process group,
bounded by the backbone's one command bound and killed as a group when it
overruns — inside another run, by the time that run has left and in the
outermost run's group — reading one JSON document — and nothing else — from
its standard output:
`{"summary": [...], "findings": [{"severity", "location", "message"}, ...]}`;
diagnostics go to standard error. No answer — a leaf without the declaration,
an abnormal exit, a timeout, output that is not exactly that document — is an
*error finding*, never a clean pass: the umbrella fails closed. An exit that is
uv's report of a dependency missing from its cache is named for what it is, an
environment not provisioned, with `pkit sync` — which provisions it — as the fix.
A `pkit` reading command the validator starts stays inside its bound — a
filler it starts gets the time remaining and the group (`command_runner`, "a
run inside a run") — and reads a data point the run resolved from the run
cache (`run_cache`) rather than resolving it again.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from ruamel.yaml import YAML

from project_kit import cli_render, default_branch, run_cache
from project_kit.command_runner import (
    COMMANDS_KEY,
    CommandRun,
    Ending,
    commands_of,
    parse_document,
    resolve_command,
    run_command,
)

# The owner of the backbone's own members; a capability's members are owned
# by the capability and addressed `<capability>:<name>`.
BACKBONE_OWNER = "backbone"

# The package-metadata key a component registers its validators under, and the
# key of an entry that names the `commands:` leaf answering for it.
VALIDATORS_KEY = "validators"
COMMAND_KEY = "command"

# The declaration a `commands:` leaf carries to say the command honours the
# query contract — bounded, deterministic, read-only, needing no network
# (ADR-057 point 3). `query-contract: true` is the literal ADR-058 specifies:
# a validator's leaf must carry it, the packages member reports one without
# it, and the runner here refuses it.
QUERY_CONTRACT_KEY = "query-contract"

# What a data point's command filler declares it reads beyond the working tree
# (COR-052 point 6), on its `commands:` leaf beside the query contract: the
# current history, and settled state — the default branch, as the backbone
# resolves it. Absent, the working tree only. `data_points` reads it; the
# package schema refuses any other value, and the packages member a leaf that
# declares it without the query contract.
READS_KEY = "reads"
READS_HISTORY = "history"
READS_SETTLED = "settled"
READS_STATES = (READS_HISTORY, READS_SETTLED)

# The one argument the umbrella passes a validator command. The leaf is also a
# focused surface that prints for people; with this flag it prints the
# findings document alone.
QUERY_FLAG = "--json"

# The offline marker (ADR-057 point 3), set in the environment of every query
# command the umbrella runs. `PKIT_OFFLINE` is what a well-behaved command
# reads; `UV_OFFLINE` makes `uv` honour it — a `uv run --script` shebang
# resolves the script's dependencies from uv's cache and never fetches, so
# `pkit init` and `pkit sync` provision them beforehand (`provisioning`). The
# lifecycle README's literals section documents both.
OFFLINE_MARKER: Mapping[str, str] = {"PKIT_OFFLINE": "1", "UV_OFFLINE": "1"}

# What a query command never inherits from its caller's environment: the base
# override a pipeline sets for its comparisons (COR-054 point 3). A query
# answers about the project's state, and a validator and a data point's filler
# take no base named for one run (COR-052 point 6, ADR-058 point 7) — so every
# validator and every filler, whichever command starts it, answers the same
# whatever base a pipeline named. The lifecycle README's query row says so.
QUERY_DROPPED_ENV: tuple[str, ...] = (default_branch.CHECK_BASE_ENV,)

# What `uv`, honouring the offline marker, prints on standard error when a
# script's dependency is not in its cache: the resolver's hint for a registry
# package, and the client's error for a file it would have to download (a
# direct URL). Matched with whitespace collapsed, since uv wraps its messages to
# the width it sees. `tests/test_provisioning.py` pins both against uv's text.
UV_OFFLINE_MISSES = (
    "because the network was disabled",
    "Network connectivity is disabled, but the requested data wasn't found in the cache",
)

# The no-answer of a query whose environment is not provisioned, and its fix.
NOT_PROVISIONED = "environment not provisioned — run `pkit sync`"

# Where a capability's validators sort when their entries name no `order`:
# after every backbone member, in capability order.
CAPABILITY_ORDER_DEFAULT = 1000

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


@dataclass(frozen=True)
class QueryCommand:
    """A capability's validator command as the registry runs it: the leaf's
    script, the reference that named it (for messages), whether the leaf
    declares the query contract, and the location of the entry — where every
    no-answer finding points."""

    script: Path
    reference: str
    declares_contract: bool
    location: str

    def run(self, target_root: Path) -> Outcome:
        if not self.declares_contract:
            return _no_answer(
                self.location,
                f"command {self.reference!r} does not declare the query contract "
                f"(`{QUERY_CONTRACT_KEY}: true` on its `commands:` entry); a validator "
                "runs only when it declares it.",
            )
        return run_query(target_root, self.script, location=self.location, reference=self.reference)


def capability_validators(target_root: Path) -> tuple[Validator, ...]:
    """The validators every registered component declares in its package metadata.

    An entry names a `commands:` leaf by `command`; the leaf's `help` is the
    validator's. Read defensively: a package file that does not parse, a
    `validators:` that is not a mapping, an entry without a string `command`,
    or one naming no leaf contributes nothing here — the packages member
    reports the defect. A leaf that does not declare the query contract *is*
    registered, and refused when run (the runner's backstop, ADR-057 point
    3): the umbrella fails closed on it rather than skipping it silently.
    `order` is taken when it is an integer, else the capability default.
    """
    from project_kit.package_validate import installed_package_files

    out: list[Validator] = []
    for owner, component_dir, package in installed_package_files(target_root):
        raw = _load_mapping(package)
        commands = commands_of(component_dir, raw.get(COMMANDS_KEY))
        block = raw.get(VALIDATORS_KEY)
        if not isinstance(block, Mapping):
            continue
        for raw_name, spec in block.items():
            name = str(raw_name)
            reference = spec.get(COMMAND_KEY) if isinstance(spec, Mapping) else None
            if not isinstance(reference, str):
                continue
            command = resolve_command(commands, reference)
            if command is None:
                continue
            query = QueryCommand(
                script=command.script,
                reference=reference,
                declares_contract=command.entry.get(QUERY_CONTRACT_KEY) is True,
                location=f"{_rel(package, target_root)}:/{VALIDATORS_KEY}/{name}/{COMMAND_KEY}",
            )
            order = spec.get("order")
            out.append(
                Validator(
                    name=f"{owner}:{name}",
                    run=query.run,
                    order=order
                    if isinstance(order, int) and not isinstance(order, bool)
                    else CAPABILITY_ORDER_DEFAULT,
                    owner=owner,
                    help=command.help,
                )
            )
    return tuple(out)


def _load_mapping(package: Path) -> Mapping[Any, Any]:
    try:
        raw = _yaml.load(package.read_text(encoding="utf-8"))
    except Exception:  # ruamel raises its own hierarchy; the packages member reports it
        return {}
    return raw if isinstance(raw, Mapping) else {}


def run_query(target_root: Path, script: Path, *, location: str, reference: str) -> Outcome:
    """Run one validator command under the query policy and read its answer (the
    contract in the module docstring): with `--json`, the offline marker set and
    the base override removed (`QUERY_DROPPED_ENV`), through the shared runner —
    from the project root, in its own process group, bounded by
    `command_runner.COMMAND_TIMEOUT_SECONDS` (inside another run, by the time
    it has left, in the outermost run's group). No answer is an error
    finding at `location` — the validator's own entry in the package file — so
    the umbrella fails closed."""
    if not script.is_file():
        return _no_answer(
            location,
            f"command {reference!r} names script {_rel(script, target_root)!r}, which does not "
            "exist.",
        )
    run = run_command(
        script,
        [QUERY_FLAG],
        cwd=target_root,
        extra_env=OFFLINE_MARKER,
        drop_env=QUERY_DROPPED_ENV,
    )
    if run.ending is Ending.ANSWERED:
        return _answer_of(run.document, location=location, command=reference)
    return _no_answer(location, why_no_answer(run, reference))


def not_provisioned(run: CommandRun) -> bool:
    """True when a query run gave no answer because its environment is not
    provisioned: it exited non-zero with uv's report that a dependency is not in
    its cache and the network is disabled — the offline marker's doing."""
    if run.ending is not Ending.ABNORMAL_EXIT:
        return False
    stderr = " ".join(run.stderr.split())
    return any(miss in stderr for miss in UV_OFFLINE_MISSES)


def why_no_answer(run: CommandRun, reference: str) -> str:
    """Why a query run did not answer: the message of a validator's no-answer
    finding, and the reason a command filler is inert (`data_points`). An
    environment not provisioned is named as such, with its fix, rather than as
    the exit it shows as."""
    if run.ending is Ending.NOT_STARTED:
        return f"command {reference!r} could not start: {run.detail}"
    if run.ending is Ending.TIMED_OUT:
        return f"command {reference!r} did not answer within {run.bound_described}."
    if not_provisioned(run):
        return (
            f"command {reference!r}: {NOT_PROVISIONED} (its dependencies are not in "
            "uv's cache, and a query runs offline)."
        )
    if run.ending is Ending.ABNORMAL_EXIT:
        detail = run.stderr.strip().splitlines()
        tail = f": {detail[-1]}" if detail else "."
        return f"command {reference!r} exited {run.returncode}{tail}"
    return _not_a_document(reference)


def _not_a_document(command: str) -> str:
    return f"command {command!r} did not print a JSON document on its standard output."


def parse_answer(text: str, *, location: str, command: str) -> Outcome:
    """The findings document a validator command prints, as an Outcome. Anything
    that is not exactly one — text that is not JSON, JSON that is not an
    object, a `summary` or `findings` missing or not a list, a malformed
    finding — is an error finding: the umbrella fails closed on a half-formed
    answer as on none."""
    try:
        document = parse_document(text)
    except ValueError:
        return _no_answer(location, _not_a_document(command))
    return _answer_of(document, location=location, command=command)


def _answer_of(document: Any, *, location: str, command: str) -> Outcome:
    """The parsed document as an Outcome, validated against the findings
    document's shape (`parse_answer`)."""
    if not isinstance(document, Mapping):
        return _no_answer(
            location, f"command {command!r} printed {_kind(document)}, not a findings document."
        )
    for key in ("summary", "findings"):
        if not isinstance(document.get(key), list):
            return _no_answer(
                location,
                f"command {command!r} answered without a `{key}` list: expected "
                '{"summary": [...], "findings": [...]}.',
            )
    findings: list[Finding] = []
    for index, entry in enumerate(document["findings"]):
        finding = _finding(entry)
        if finding is None:
            return _no_answer(
                location,
                f"command {command!r} answered with a malformed finding at index {index}: "
                f"expected `severity` (one of {_severities()}), `location` and `message`.",
            )
        findings.append(finding)
    summary = tuple(str(line) for line in document["summary"])
    return Outcome(summary=summary, findings=tuple(findings))


def _finding(entry: Any) -> Finding | None:
    if not isinstance(entry, Mapping):
        return None
    severity_value, location, message = (
        entry.get("severity"),
        entry.get("location"),
        entry.get("message"),
    )
    if (
        not isinstance(severity_value, str)
        or not isinstance(location, str)
        or not isinstance(message, str)
    ):
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
    return tuple(v for v in registered if (not only or v.name in only) and v.name not in skip)


# The values computed so far in the current run of `run_all`; None outside one.
_RUN_VALUES: ContextVar[dict[Hashable, Any] | None] = ContextVar("validate_run", default=None)

_T = TypeVar("_T")


def once_per_run(key: Hashable, compute: Callable[[], _T]) -> _T:
    """`compute()`, once per run of the umbrella for each `key`.

    Several members read one computation — the wiring is read by the
    `connections`, `versions`, `friction` and `rule-sets` members — and a
    second computation of it is a defect (ADR-057 point 2). Inside `run_all`
    the first reader computes the value and every later reader of the same key
    gets that value; outside a run — a focused surface, a member called on its
    own — it simply computes. Members only read the tree, so a value cannot go
    stale within a run.
    """
    values = _RUN_VALUES.get()
    if values is None:
        return compute()
    if key not in values:
        values[key] = compute()
    return values[key]


def as_one_run(compute: Callable[[], _T]) -> _T:
    """`compute()` as one run: inside `run_all` it already is one; outside — a
    reading command such as `pkit status` — the computations it shares through
    `once_per_run` are made once for it, as they would be under the umbrella."""
    if _RUN_VALUES.get() is not None:
        return compute()
    token = _RUN_VALUES.set({})
    try:
        return compute()
    finally:
        _RUN_VALUES.reset(token)


def run_all(target_root: Path, validators: Iterable[Validator]) -> list[Result]:
    """Run the members in order, as one run: a computation several members read
    (`once_per_run`) is computed once for all of them — and a resolved data
    point once for the `pkit` commands a member starts too, through the run
    cache (`run_cache`), open for the run's length."""
    token = _RUN_VALUES.set({})
    try:
        with run_cache.opened():
            return [Result(v, v.run(target_root)) for v in validators]
    finally:
        _RUN_VALUES.reset(token)


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
    counts = ", ".join(f"{sum(r.outcome.count(s) for r in results)} {s.value}(s)" for s in Severity)
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


def _kind(value: Any) -> str:
    return "null" if value is None else f"a {type(value).__name__}"


def location_of(path: Path, target_root: Path, pointer: str = "") -> str:
    """A finding's location: the path relative to the root, then `:` and the pointer when there is
    one."""
    rel = _rel(path, target_root)
    return f"{rel}:{pointer}" if pointer else rel


def counts_line(findings: Iterable[Finding], *severities: Severity) -> str:
    """`N error(s), M warning(s)` — one count per severity given, in that order."""
    listed = list(findings)
    return ", ".join(
        f"{sum(1 for f in listed if f.severity is s)} {s.value}(s)" for s in severities
    )
