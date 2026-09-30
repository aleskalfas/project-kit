"""Data points: what each one resolves to, and why (COR-052; COR-053 point 2).

The second layer over the wiring. `connections` resolves who answers each role
and which counterparts reach each point; this module reads that `Wiring` —
never resolving it again — and, for every data point an active provider
defines, combines the point's fillers into one value by its declaration:

- **The fillers**, in precedence order (COR-052 point 4): the project's filler
  file, at the path the point's address maps to under the internal
  documentation root; each capability's contribution (`extensions.contributes`),
  its data written as `value` or printed by a command filler; the definer's
  `default`, which takes part
  `always` — like any other filler, at the lowest precedence — or only `alone`,
  when no other filler is declared (point 2).
- **The policy** (point 3). `single`: the first filler in precedence order
  answers alone; among several contributions the contributor selection picks
  one, and several with none selected leave the point unresolved. `union`:
  entries merged by id — a project entry replaces a capability's whole, a
  capability's replaces the default's — and two capabilities supplying one id
  is an error the project settles by overriding or removing it. `additive`:
  entries merged, any collision an error, the project's included; an entry
  leaves only through a removal override. A point that declares no policy is
  `single` (`connections.Point.policy`).
- **Removal overrides.** `remove` in the project's envelope — each entry an id
  and its reason — drops that id from every other filler before they merge.
- **Command fillers** (point 6). A contribution's `command` is a query: it
  takes no parameter. Its `commands:` leaf must declare the query contract
  (`query-contract: true`), or it is not run; it is run through the shared
  runner under the query policy — from the project root with `--json` alone,
  the offline marker set, in its own process group, bounded (read inside
  another run, by the time that run has left, in the outermost run's group) —
  and prints one filler envelope, `{schema_version, value}`, at the point's
  version. An
  abnormal exit, a timeout, output that is not that envelope, or a value that
  does not fit is no answer — never an empty one. The declaration is trusted,
  not enforced: nothing here holds the command to no network (ADR-057 point
  4), so each command filler carries whether it declares it, for the report.
- **The inert policy** (point 6). A filler meant to answer that cannot — its
  version differs, its command gives no answer, its value does not fit the
  point's schema — is inert.
  `fallback` resolves from the fillers that remain, with a warning naming it;
  `fail` leaves the whole point unresolved, with an error. An `alone` default
  is never promoted because a declared filler broke, and a point never
  resolves to a partial value.

A project filler is the project's to fix, so every defect in it is an error
whatever the point's inert policy (point 2): an envelope that breaks the
envelope schema (`backbone/filler.schema.json`), a version other than the
point's (the wiring's `[project filler version]` finding), a value the point's
schema refuses, removals on a `single` point. A file under the fillers prefix
whose path names no point is warned; one whose point no active provider
defines is inert — its envelope checked, its value never read.

`resolve_data_points` reads the repository and the one wiring;
`shared_resolution` computes it once per run of `pkit validate`
(`validators.once_per_run`): the `connections` member reports it, and the
status report shows how each point resolved. `resolve_point` resolves one
point alone, for `pkit connections resolve`: only its fillers are asked, so no
other point's command filler starts. Within a run each point resolves at most
once, whichever reader asks first, and points never read one another, so a
point resolved alone is the point resolved among all. A run of `pkit validate`
spans processes — a capability's validator reads a point through `pkit
connections resolve` — so each resolved point is also kept in the run cache
(`run_cache`), with the findings its resolution made and the bound it was
resolved under: whichever process of the run asks first resolves it, and every
other reads it (`shared_point`), its fillers started once. One resolution is
never kept: one in which a command filler gave no answer for want of the time
its asker had left (`CommandRun.clipped`) — a reader with more time might get
an answer, so the next reader resolves the point itself.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from referencing.exceptions import Unresolvable

from project_kit import backbone_schemas as bs
from project_kit import connections as cx
from project_kit import run_cache, validators
from project_kit.command_runner import (
    COMMANDS_KEY,
    Ending,
    RegisteredCommand,
    commands_of,
    resolve_command,
    run_command,
)
from project_kit.package_validate import role_of

# How a point's default takes part (COR-052 point 2), and its inert policy (point 6).
ALWAYS = "always"
ALONE = "alone"
FALLBACK = "fallback"
FAIL = "fail"

# The keys of a data point's declaration this layer reads, of a contribution's
# entry, and of the filler envelope.
DEFAULT_KEY = "default"
PARTICIPATION_KEY = "participation"
INERT_KEY = "inert"
VALUE_KEY = "value"
REMOVE_KEY = "remove"
ID_KEY = "id"
REASON_KEY = "reason"

# The origin of an entry, or of a `single` point's answer, that is not a
# capability. Each holds a space, so no component name can equal it.
PROJECT = "project filler"
DEFAULT = "the default"


# --- the model ------------------------------------------------------------


class FillerSource(Enum):
    """The three kinds of filler (COR-052 point 2)."""

    PROJECT = "project filler"
    CONTRIBUTION = "contribution"
    DEFAULT = "default"


class FillerState(Enum):
    """What became of one filler."""

    TAKEN = "taken"  # its answer is part of the point's value
    INERT = "inert"  # it was meant to answer and could not
    PASSED_OVER = "passed over"  # not asked: another answers first, not selected, not delivered


@dataclass(frozen=True)
class Filler:
    """One filler considered for a point, and what became of it.

    `name` is who fills: the project filler's path, the contributing
    capability, or the provider whose default it is. `supplies` is how:
    `file`, `value`, `command '<reference>'`, or the default's participation.
    """

    source: FillerSource
    name: str
    supplies: str
    state: FillerState
    reason: str = ""  # why it is inert or passed over
    # A command filler: whether its command declares the query contract — among
    # its limits, needing no network. Declared and trusted, never enforced
    # (ADR-057 point 4). None for any other filler.
    query_contract: bool | None = None

    @property
    def label(self) -> str:
        if self.source is FillerSource.PROJECT:
            return f"{PROJECT} {self.name}"
        if self.source is FillerSource.DEFAULT:
            return f"default of {self.name} ({self.supplies})"
        return f"{self.name} ({self.supplies})"


@dataclass(frozen=True)
class Entry:
    """One entry of a `union` or `additive` point's value, with where it came from."""

    id: str
    value: Any
    origin: str  # `PROJECT`, a capability, or `DEFAULT`
    replaces: tuple[str, ...] = ()  # union: the origins whose entry of this id it replaced


@dataclass(frozen=True)
class Removal:
    """A removal override of the project filler, and the fillers it dropped the id from."""

    id: str
    reason: str
    removed_from: tuple[str, ...]  # empty when it matched nothing


@dataclass(frozen=True)
class ResolvedPoint:
    """How one data point resolved (COR-052 point 7: shown, with why)."""

    address: str
    provider: str
    policy: str
    inert_policy: str
    participation: str | None  # the default's, when the point declares one
    fillers: tuple[Filler, ...]
    resolved: bool
    value: Any = None
    origin: str = ""  # `single`: the filler that answered
    entries: tuple[Entry, ...] = ()  # `union` / `additive`: the value's entries
    removals: tuple[Removal, ...] = ()
    why: str = ""  # why it is unresolved


@dataclass(frozen=True)
class DataResolution:
    """Every data point of the project, how each resolved, and the findings."""

    points: tuple[ResolvedPoint, ...]
    filler_files: int  # files under the fillers prefix, strays included
    findings: tuple[validators.Finding, ...]
    notes: tuple[str, ...] = ()

    def point(self, address: str) -> ResolvedPoint | None:
        return next((p for p in self.points if p.address == address), None)


# --- resolving ------------------------------------------------------------


def shared_resolution(target_root: Path) -> DataResolution:
    """The data points, resolved once per run of `pkit validate` over the run's one
    wiring (ADR-057 point 2); outside a run — the status report — afresh."""
    return validators.once_per_run(
        ("data-points", target_root.resolve()), lambda: resolve_data_points(target_root)
    )


def resolve_data_points(target_root: Path) -> DataResolution:
    """Resolve every data point an active provider defines (the module docstring),
    as one run: the wiring, the point schemas and the filler files are each
    computed once for it, whether or not `pkit validate` is running."""
    return validators.as_one_run(lambda: _resolve(target_root))


def _resolve(target_root: Path) -> DataResolution:
    """Every data point, each resolved once per run (`_resolved`): the project
    filler files' findings, then each point's in the wiring's order — the same
    answer whichever point a reader of the run asked for first."""
    run = _data_run(target_root)
    outcomes = [_resolved(run, binding) for binding in _data_points(run.wiring)]
    findings = [*run.envelope_findings, *(f for o in outcomes for f in o.findings)]
    return DataResolution(
        points=tuple(o.point for o in outcomes),
        filler_files=run.filler_files,
        findings=tuple(findings),
        notes=run.notes,
    )


def _data_points(wiring: cx.Wiring) -> list[cx.PointBinding]:
    """The data points the active providers define, in the wiring's order."""
    return [p for p in wiring.points if p.point.kind is cx.PointKind.DATA]


def _data_run(target_root: Path) -> _Run:
    """What every data point of a run reads — the one wiring, the point schemas,
    the project's filler files with their envelopes checked — made once per run."""
    return validators.once_per_run(
        ("data-points-run", target_root.resolve()), lambda: _new_run(target_root)
    )


def _new_run(target_root: Path) -> _Run:
    files = cx.project_fillers(target_root)
    schema, notes = _filler_schema(target_root)
    run = _Run(
        root=target_root,
        wiring=cx.shared_wiring(target_root),
        schemas=cx.container_wiring(target_root).points,
        fillers={f.address: f for f in files if f.address is not None},
        prefix=cx.fillers_prefix(target_root).as_posix(),
        envelope=schema,
        filler_files=len(files),
        notes=notes,
    )
    run.check_envelopes(files)
    run.envelope_findings = tuple(run.findings)
    return run


@dataclass(frozen=True)
class _PointOutcome:
    """One data point resolved, with the findings its resolution made."""

    point: ResolvedPoint
    findings: tuple[validators.Finding, ...]


def _resolved(run: _Run, binding: cx.PointBinding) -> _PointOutcome:
    """The point `binding` resolved, once per run: its fillers are asked — a command
    filler started — at most once, whichever reader asks first, in this process
    or, through the run cache, in any process `pkit validate` started. Points do
    not read one another, so a point resolved alone is the point resolved among all.

    A resolution in which a command filler ran out of the time its asker had
    left is not put in the run cache: another process of the run may have more
    time, and reads the point by resolving it. Within this process it is kept —
    no later reader here has more time than the first."""
    address = binding.point.address

    def resolve() -> _PointOutcome:
        shared = _shared_outcome(run.root, address)
        if shared is not None:
            return shared
        start = len(run.findings)
        resolution = _Point(run, binding)
        outcome = _PointOutcome(resolution.resolve(), tuple(run.findings[start:]))
        if not resolution.clipped:
            run_cache.write(_cache_key(run.root, address), _entry_of(outcome, resolution.bound))
        return outcome

    return validators.once_per_run(("data-point", run.root.resolve(), address), resolve)


# --- sharing a resolved point across the processes of a run ---------------


def _cache_key(target_root: Path, address: str) -> str:
    return f"data-point {target_root.resolve()} {address}"


def _entry_of(outcome: _PointOutcome, bound: float | None) -> dict[str, Any]:
    """A resolved point as the run cache keeps it: its document, the findings its
    resolution made, which the `connections` member reports, and the tightest
    bound a command filler of it ran under — the first asker's; None when none
    ran."""
    return {
        "bound": bound,
        "point": point_document(outcome.point),
        "findings": [
            {
                "location": f.location,
                "message": f.message,
                "severity": f.severity.value,
                "label": f.label,
            }
            for f in outcome.findings
        ],
    }


def _shared_outcome(target_root: Path, address: str) -> _PointOutcome | None:
    """The point `address` as another process of the run resolved it, or None:
    no run cache, the point not yet resolved, or an entry this reading does not
    understand — a miss, never an error; the point is then resolved here."""
    entry = run_cache.read(_cache_key(target_root, address))
    if not isinstance(entry, Mapping):
        return None
    shared = cast("Mapping[str, Any]", entry)
    try:
        findings = tuple(
            validators.Finding(
                str(f["location"]),
                str(f["message"]),
                validators.Severity(f["severity"]),
                str(f["label"]),
            )
            for f in cast("list[Mapping[str, Any]]", shared["findings"])
        )
        return _PointOutcome(point_from_document(shared["point"]), findings)
    except (KeyError, TypeError, ValueError):  # not an entry `_entry_of` wrote
        return None


def _filler_schema(target_root: Path) -> tuple[Mapping[str, Any] | None, tuple[str, ...]]:
    """The envelope's schema from the tree, or None with the note saying why
    (ADR-056 point 1: a tree without it skips the shape check, never substitutes)."""
    try:
        return bs.load_backbone_schema(target_root, bs.FILLER_SCHEMA_KIND), ()
    except bs.BackboneSchemaMissing:
        note = "no filler schema present under .pkit/schemas/backbone/; envelopes not checked."
    except bs.BackboneSchemaInvalid:
        note = "the filler schema does not load (the `schemas` member says why); envelopes not checked."
    return None, (note,)


@dataclass(frozen=True)
class _Answer:
    """What one filler answered: a value, or why it is no answer."""

    value: Any = None
    inert: str | None = None
    removals: tuple[tuple[str, str, int], ...] = ()  # the project's: (id, reason, index)
    reported: bool = False  # an inert answer another finding already names

    @property
    def answered(self) -> bool:
        return self.inert is None


def _no_answer(reason: str, *, reported: bool = False) -> _Answer:
    return _Answer(inert=reason, reported=reported)


@dataclass
class _Candidate:
    """A filler, before it is asked; `ask` evaluates it at most once."""

    source: FillerSource
    name: str
    supplies: str
    evaluate: Callable[[], _Answer]
    location: str  # where a finding about it points
    who: str  # how a finding's message names it
    query_contract: bool | None = None  # a command filler: its command declares the contract
    answer: _Answer | None = None

    def ask(self) -> _Answer:
        if self.answer is None:
            self.answer = self.evaluate()
        return self.answer

    @property
    def origin(self) -> str:
        if self.source is FillerSource.PROJECT:
            return PROJECT
        if self.source is FillerSource.DEFAULT:
            return DEFAULT
        return self.name

    def filler(self, state: FillerState, reason: str = "") -> Filler:
        return Filler(self.source, self.name, self.supplies, state, reason, self.query_contract)


@dataclass
class _Run:
    """One resolution: what every point reads, and the findings gathered."""

    root: Path
    wiring: cx.Wiring
    schemas: Mapping[str, bs.ActivePoint]
    fillers: Mapping[str, cx.FillerFile]
    prefix: str
    envelope: Mapping[str, Any] | None  # the filler envelope's schema; None when the tree has none
    filler_files: int = 0  # files under the fillers prefix, strays included
    notes: tuple[str, ...] = ()
    findings: list[validators.Finding] = field(default_factory=list[validators.Finding])
    envelope_findings: tuple[validators.Finding, ...] = ()  # the filler files', before any point
    unsound: dict[str, str] = field(default_factory=dict[str, str])  # address → why it is not read

    def add(self, location: str, message: str, severity: validators.Severity) -> None:
        self.findings.append(validators.Finding(location, message, severity))

    def package_location(self, capability: str, pointer: str) -> str:
        component = self.wiring.declarations.by_name(capability)
        if component is None:
            return capability
        return validators.location_of(component.file, self.root, pointer)

    def filler_path(self, address: str) -> str:
        """Where the project filler for `address` lives, whether or not it exists —
        for a finding whose fix is written there."""
        sub = bs.filler_subpath(address)
        return f"{self.prefix}/{sub.as_posix()}" if sub is not None else self.prefix

    def check_envelopes(self, files: Iterable[cx.FillerFile]) -> None:
        """Every file under the prefix: a stray is warned, a malformed envelope is an
        error, a filler whose point no active provider defines is inert."""
        schema = self.envelope
        for file in files:
            if file.address is None:
                self.add(
                    file.path,
                    f"not a project filler: under {self.prefix}/ a filler's path is "
                    f"`<publisher>/<role>/<point>.yaml`, each part a word, and this one names "
                    f"no point, so it binds to nothing; move or remove it (COR-052 point 2).",
                    validators.Severity.WARNING,
                )
                continue
            if file.problem is not None:
                self.unsound[file.address] = "it does not parse"
                self.add(file.path, f"project filler {file.problem}", validators.Severity.ERROR)
                continue
            if schema is not None:
                problems = bs.envelope_findings(file.document, schema)
            elif isinstance(file.document, Mapping) and VALUE_KEY in file.document:
                problems = []
            else:
                problems = [("", "expected a mapping carrying `schema_version` and `value`.")]
            for pointer, message in problems:
                self.add(
                    _at(file.path, pointer),
                    f"{message} (the filler envelope, COR-052 point 2)",
                    validators.Severity.ERROR,
                )
            if problems:
                self.unsound[file.address] = "its envelope is malformed"
            if self.wiring.data_point(file.address) is None:
                self.add(
                    file.path,
                    f"project filler for {file.address!r}: {self._undefined(file.address)}; "
                    f"inert — its envelope is checked, its value is not read (COR-052 point 2).",
                    validators.Severity.REPORT,
                )

    def _undefined(self, address: str) -> str:
        return undefined_why(self.wiring, address)


def undefined_why(wiring: cx.Wiring, address: str) -> str:
    """Why no active provider defines the data point `address`."""
    role = role_of(address) or address
    binding = wiring.role(role)
    if binding is None or binding.active is None:
        return f"role {role!r} has no active provider"
    return (
        f"{binding.active!r}, the active provider of role {role!r}, defines no data "
        f"point {address!r}"
    )


@dataclass
class _Point:
    """The resolution of one data point: its fillers, asked by precedence."""

    run: _Run
    binding: cx.PointBinding
    fillers: list[Filler] = field(default_factory=list[Filler])
    inert: list[_Candidate] = field(default_factory=list[_Candidate])
    validator: Draft202012Validator | None = None
    # The command fillers' runs: the tightest bound one ran under, and whether one
    # gave no answer for want of the time its asker had left (`CommandRun.clipped`).
    bound: float | None = None
    clipped: bool = False
    address: str = field(init=False)
    policy: str = field(init=False)
    inert_policy: str = field(init=False)
    default: tuple[Any, str] | None = field(init=False)  # (value, participation)

    def __post_init__(self) -> None:
        point = self.binding.point
        declaration = _declared(self.run.wiring.declarations, point.provider, point.pointer)
        self.address = point.address
        self.policy = point.policy or cx.SINGLE
        self.inert_policy = _inert_policy(declaration.get(INERT_KEY))
        self.default = _default(declaration.get(DEFAULT_KEY))

    def resolve(self) -> ResolvedPoint:
        return ResolvedPoint(
            address=self.address,
            provider=self.binding.point.provider,
            policy=self.policy,
            inert_policy=self.inert_policy,
            participation=self.default[1] if self.default is not None else None,
            **self._outcome(),
        )

    def _outcome(self) -> dict[str, Any]:
        if self.policy not in cx.COMBINATIONS:
            return self._unresolved(f"it declares an unknown combination policy {self.policy!r}")
        active = self.run.schemas.get(self.address)
        if active is None or active.validator is None:
            why = active.unavailable if active is not None else "no point schema is loaded"
            point = self.binding.point
            self.run.add(
                self.run.package_location(point.provider, f"{point.pointer}/schema"),
                f"the schema of data point {self.address!r} cannot be applied ({why}); the "
                f"point does not resolve until it can.",
                validators.Severity.WARNING,
            )
            return self._unresolved(f"its schema cannot be applied: {why}")
        self.validator = active.validator
        return self._single() if self.policy == cx.SINGLE else self._merged()

    # --- the candidates

    def _declared_fillers(self) -> tuple[_Candidate | None, list[cx.Binding]]:
        """The project filler and the contributions meant to answer. A contribution
        whose capability is a provider that is not the selected one is not
        delivered (COR-053 point 1): it is passed over here."""
        eligible: list[cx.Binding] = []
        for b in sorted(self.binding.bindings, key=lambda b: b.counterpart.capability):
            if b.counterpart.kind is not cx.CounterpartKind.CONTRIBUTION:
                continue
            if b.status is cx.BindingStatus.INERT_PROVIDER:
                self.fillers.append(
                    self._contribution(b).filler(
                        FillerState.PASSED_OVER,
                        f"not delivered: {b.counterpart.capability!r} provides a role for which "
                        f"it is not the selected provider",
                    )
                )
                continue
            eligible.append(b)
        return self._project(), eligible

    def _project(self) -> _Candidate | None:
        file = self.run.fillers.get(self.address)
        if file is None:
            return None
        return _Candidate(
            FillerSource.PROJECT,
            file.path,
            "file",
            lambda: self._project_answer(file),
            location=file.path,
            who=f"the project filler {file.path}",
        )

    def _contribution(self, b: cx.Binding) -> _Candidate:
        c = b.counterpart
        entry = _declared(self.run.wiring.declarations, c.capability, c.pointer)
        command = None if VALUE_KEY in entry else self._command(c)
        return _Candidate(
            FillerSource.CONTRIBUTION,
            c.capability,
            _supplies(entry, c),
            lambda: self._contribution_answer(b, entry, command),
            location=self.run.package_location(c.capability, c.pointer),
            who=f"the contribution of {c.capability!r}",
            query_contract=(
                command.entry.get(validators.QUERY_CONTRACT_KEY) is True
                if command is not None
                else None
            ),
        )

    def _command(self, c: cx.Counterpart) -> RegisteredCommand | None:
        """The `commands:` leaf a contribution names as its filler, when it names one
        that exists (the packages member reports one that does not)."""
        component = self.run.wiring.declarations.by_name(c.capability)
        if c.command is None or component is None:
            return None
        commands = commands_of(component.component_dir, component.package.get(COMMANDS_KEY))
        return resolve_command(commands, c.command)

    def _default_candidate(self) -> _Candidate | None:
        if self.default is None:
            return None
        value, participation = self.default
        point = self.binding.point
        return _Candidate(
            FillerSource.DEFAULT,
            point.provider,
            participation,
            lambda: self._value_answer(value),
            location=self.run.package_location(
                point.provider, f"{point.pointer}/{DEFAULT_KEY}/{VALUE_KEY}"
            ),
            who=f"the default of {point.provider!r}",
        )

    def _default_takes_part(self, declared: bool) -> bool:
        """`always`, or `alone` with no other filler declared (COR-052 point 2)."""
        return self.default is not None and (self.default[1] == ALWAYS or not declared)

    # --- the answers

    def _project_answer(self, file: cx.FillerFile) -> _Answer:
        unsound = self.run.unsound.get(self.address)
        if unsound is not None:
            return _no_answer(unsound, reported=True)
        if not self.binding.filler_compatible:
            return _no_answer(
                f"it targets version {file.version}; the point is at version "
                f"{self.binding.point.version}",
                reported=True,  # the wiring's `[project filler version]` error
            )
        document = cast("Mapping[str, Any]", file.document)
        problems = [(f"/{VALUE_KEY}{p}", m) for p, m in self._value_problems(document[VALUE_KEY])]
        removals = cast("list[Mapping[str, str]]", document.get(REMOVE_KEY) or [])
        if removals and self.policy == cx.SINGLE:
            problems.append(
                (
                    f"/{REMOVE_KEY}",
                    "a `single` point takes no removal overrides: its one answer is the "
                    "project filler's `value`.",
                )
            )
        for pointer, message in problems:
            self.run.add(
                _at(file.path, pointer),
                f"{message} (the project filler for {self.address!r}, COR-052 point 2)",
                validators.Severity.ERROR,
            )
        if problems:
            return _no_answer("its value does not fit the point", reported=True)
        return _Answer(
            document[VALUE_KEY],
            removals=tuple((r[ID_KEY], r[REASON_KEY], i) for i, r in enumerate(removals)),
        )

    def _contribution_answer(
        self, b: cx.Binding, entry: Mapping[str, Any], command: RegisteredCommand | None
    ) -> _Answer:
        c = b.counterpart
        if b.status is cx.BindingStatus.INERT_VERSION:
            return _no_answer(
                f"it targets version {c.version}; the point is at version "
                f"{self.binding.point.version}",
                reported=self.inert_policy == FALLBACK,  # the wiring's `[point version]` warning
            )
        if VALUE_KEY in entry:
            return self._value_answer(entry[VALUE_KEY])
        if c.command is not None:
            return self._command_answer(c.command, command)
        return _no_answer("it supplies no data: it declares neither `value` nor `command`")

    def _command_answer(self, reference: str, command: RegisteredCommand | None) -> _Answer:
        """Run a command filler under the query policy and read its envelope
        (COR-052 point 6; the lifecycle README, "How a registered command is
        run"). It takes no parameter: `--json` alone. Anything but a whole,
        fitting envelope is no answer. The first three defects are the packages
        member's errors as well, so under `fallback` they earn no second finding."""
        if command is None:
            return _no_answer(
                f"its command {reference!r} is not declared in `commands:`", reported=True
            )
        if command.entry.get(validators.QUERY_CONTRACT_KEY) is not True:
            return _no_answer(
                f"its command {reference!r} does not declare the query contract "
                f"(`{validators.QUERY_CONTRACT_KEY}: true`), so it is not run",
                reported=True,
            )
        if not command.script.is_file():
            return _no_answer(
                f"its command {reference!r} names a script that does not exist", reported=True
            )
        run = run_command(
            command.script,
            [validators.QUERY_FLAG],
            cwd=self.run.root,
            extra_env=validators.OFFLINE_MARKER,
        )
        self.bound = run.bound_seconds if self.bound is None else min(self.bound, run.bound_seconds)
        if run.ending is not Ending.ANSWERED:
            self.clipped = self.clipped or run.clipped
            return _no_answer(validators.why_no_answer(run, reference).rstrip("."))
        return self._envelope_answer(reference, run.document)

    def _envelope_answer(self, reference: str, document: Any) -> _Answer:
        """A command filler's answer: exactly the envelope — `schema_version` at the
        point's version and `value` — with a value that fits the point."""
        problems = (
            bs.envelope_findings(document, self.run.envelope)
            if self.run.envelope is not None
            else []
        )
        if not isinstance(document, Mapping) or VALUE_KEY not in document:
            problems = problems or [("", "expected the filler envelope `{schema_version, value}`")]
        if problems:
            pointer, message = problems[0]
            where = f" at {pointer}" if pointer else ""
            return _no_answer(
                f"command {reference!r} printed no filler envelope{where}: {message.rstrip('.')}"
            )
        envelope = cast("Mapping[str, Any]", document)
        if REMOVE_KEY in envelope:
            return _no_answer(
                f"command {reference!r} answered with `{REMOVE_KEY}`: removal overrides are "
                f"the project's alone"
            )
        version = envelope.get(bs.POINT_VERSION_FIELD)
        if version != self.binding.point.version:
            return _no_answer(
                f"command {reference!r} answered for version {version}; the point is at "
                f"version {self.binding.point.version}"
            )
        return self._value_answer(envelope[VALUE_KEY])

    def _value_answer(self, value: Any) -> _Answer:
        problems = self._value_problems(value)
        if not problems:
            return _Answer(value)
        pointer, message = problems[0]
        where = f" at {pointer}" if pointer else ""
        more = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        return _no_answer(f"its value does not fit the point{where}: {message}{more}")

    def _value_problems(self, value: Any) -> list[tuple[str, str]]:
        """`(pointer, message)` per way `value` does not fit the point: its schema,
        then — for `union` and `additive` — the entries' ids."""
        validator = cast(Draft202012Validator, self.validator)
        try:
            errors = sorted(
                validator.iter_errors(value), key=lambda e: [str(p) for p in e.absolute_path]
            )
        except Unresolvable as exc:
            return [("", f"the point's schema does not resolve `$ref` {exc.ref!r}")]
        problems = [
            ("".join(f"/{_token(p)}" for p in path), message)
            for error in errors
            for path, message in bs.expand_schema_error(error)
        ]
        if not problems and self.policy != cx.SINGLE:
            problems = _entry_problems(value)
        return problems

    # --- `single`: the first filler in precedence order answers alone

    def _single(self) -> dict[str, Any]:
        project, eligible = self._declared_fillers()
        declared = project is not None or bool(eligible)
        selected = self.binding.selected
        chain = [project] if project is not None else []
        behind: list[_Candidate] = []  # out of step, meant to answer unless the project does
        if selected is not None:
            for b in eligible:
                candidate = self._contribution(b)
                if b.counterpart.capability == selected:
                    chain.append(candidate)
                else:
                    self.fillers.append(
                        candidate.filler(
                            FillerState.PASSED_OVER,
                            f"not selected: the contributor selection names {selected!r}",
                        )
                    )
        else:
            bound = [b for b in eligible if b.status is cx.BindingStatus.BOUND]
            behind = [self._contribution(b) for b in eligible if b not in bound]
            if len(bound) > 1:
                for candidate in [*map(self._contribution, bound), *behind]:
                    self.fillers.append(candidate.filler(FillerState.PASSED_OVER, _AMBIGUOUS))
                return self._single_ambiguous(project)
            chain.extend(self._contribution(b) for b in bound)
        default = self._default_candidate()
        if default is not None and self._default_takes_part(declared):
            chain.append(default)

        answerer = self._ask_in_order(chain)
        for candidate in behind:
            if answerer is not None and answerer.source is FillerSource.PROJECT:
                self.fillers.append(
                    candidate.filler(FillerState.PASSED_OVER, "the project filler answers first")
                )
            else:
                self._mark_inert(candidate, candidate.ask())
        if default is not None and default not in chain:
            self._pass_over_default(default)

        if self.inert and self.inert_policy == FAIL:
            return self._unresolved(_FAIL_WHY)
        if answerer is not None:
            return self._resolved(
                value=cast(_Answer, answerer.answer).value, origin=answerer.origin
            )
        if selected is not None and not any(c.name == selected for c in chain):
            return self._unresolved(
                f"the contributor selection names {selected!r}, which does not contribute to it"
            )
        return self._unresolved("no filler answered" if chain or behind else _UNFILLED)

    def _single_ambiguous(self, project: _Candidate | None) -> dict[str, Any]:
        """Several contributions and no selection: only the project filler, which
        precedes them all, can answer; the default never stands in for a choice
        nobody made."""
        default = self._default_candidate()
        if default is not None:
            self.fillers.append(default.filler(FillerState.PASSED_OVER, _AMBIGUOUS))
        answerer = self._ask_in_order([project] if project is not None else [])
        if answerer is not None and not (self.inert and self.inert_policy == FAIL):
            return self._resolved(value=cast(_Answer, answerer.answer).value, origin=PROJECT)
        return self._unresolved(_AMBIGUOUS)

    def _ask_in_order(self, chain: list[_Candidate]) -> _Candidate | None:
        """Ask each in turn until one answers; the rest are passed over. Under
        `fail`, an inert filler stops the asking."""
        answerer: _Candidate | None = None
        stopped = False
        for candidate in chain:
            if answerer is not None:
                self.fillers.append(
                    candidate.filler(
                        FillerState.PASSED_OVER, f"{_owner(answerer.origin)} answers first"
                    )
                )
            elif stopped:
                self.fillers.append(candidate.filler(FillerState.PASSED_OVER, _STOPPED))
            else:
                answer = candidate.ask()
                if answer.answered:
                    answerer = candidate
                    self.fillers.append(candidate.filler(FillerState.TAKEN))
                else:
                    self._mark_inert(candidate, answer)
                    stopped = self.inert_policy == FAIL
        return answerer

    # --- `union` and `additive`: every filler answers, merged by id

    def _merged(self) -> dict[str, Any]:
        project, eligible = self._declared_fillers()
        declared = project is not None or bool(eligible)
        contributions = [self._contribution(b) for b in eligible]
        default = self._default_candidate()
        asking = [c for c in (project, *contributions) if c is not None]
        if default is not None and self._default_takes_part(declared):
            asking.append(default)
        for candidate in asking:
            answer = candidate.ask()
            if answer.answered:
                self.fillers.append(candidate.filler(FillerState.TAKEN))
            else:
                self._mark_inert(candidate, answer)
        if default is not None and default not in asking:
            self._pass_over_default(default)
        if self.inert and self.inert_policy == FAIL:
            return self._unresolved(_FAIL_WHY)
        taken = [c for c in asking if cast(_Answer, c.answer).answered]
        if not taken:
            return self._unresolved("no filler answered" if asking else _UNFILLED)
        return self._merge(taken)

    def _merge(self, taken: list[_Candidate]) -> dict[str, Any]:
        """The answers of `taken`, in precedence order, merged by the point's policy.
        The project's removal overrides first drop their ids from every other filler."""
        project = next((c for c in taken if c.source is FillerSource.PROJECT), None)
        project_answer = project.answer if project is not None else None
        own = _identified(project_answer.value) if project_answer is not None else []
        removals = project_answer.removals if project_answer is not None else ()
        removed = {rid for rid, _reason, _index in removals}
        dropped: dict[str, list[str]] = {}

        def kept(candidate: _Candidate) -> list[tuple[str, Any]]:
            out: list[tuple[str, Any]] = []
            for entry_id, value in _identified(cast(_Answer, candidate.answer).value):
                if entry_id in removed:
                    dropped.setdefault(entry_id, []).append(candidate.origin)
                else:
                    out.append((entry_id, value))
            return out

        capabilities = [(c.origin, kept(c)) for c in taken if c.source is FillerSource.CONTRIBUTION]
        default = next((kept(c) for c in taken if c.source is FillerSource.DEFAULT), [])
        records = tuple(
            Removal(rid, reason, tuple(dropped.get(rid, ()))) for rid, reason, _i in removals
        )
        for (rid, _reason, index), record in zip(removals, records, strict=True):
            if not record.removed_from and project is not None:
                self.run.add(
                    _at(project.name, f"/{REMOVE_KEY}/{index}"),
                    f"removal override {rid!r} matches no entry the other fillers of "
                    f"{self.address!r} supply; it removes nothing.",
                    validators.Severity.INFO,
                )
        merge = _union if self.policy == cx.UNION else _additive
        entries, collisions = merge(own, capabilities, default)
        for collision in collisions:
            self._collision(collision, project)
        if collisions:
            clash = "; ".join(f"{c.id!r} ({c.first}, {c.second})" for c in collisions)
            return self._unresolved(f"entries collide: {clash}", removals=records)
        return self._resolved(
            value=[e.value for e in entries], entries=tuple(entries), removals=records
        )

    def _collision(self, collision: _Collision, project: _Candidate | None) -> None:
        path = self.run.filler_path(self.address)
        if collision.index is not None and project is not None:
            location = _at(project.name, f"/{VALUE_KEY}/{collision.index}")
            message = (
                f"entry {collision.id!r} of the project filler collides with the one "
                f"{_owner(collision.first)} supplies to additive point {self.address!r}: an "
                f"additive point merges without overriding — drop theirs under `remove`, with "
                f"a reason, or give yours another id (COR-052 point 3)."
            )
        elif self.policy == cx.UNION:
            location = path
            message = (
                f"{_owner(collision.first)} and {_owner(collision.second)} both supply entry "
                f"{collision.id!r} to union point {self.address!r}; settle it in the project "
                f"filler at {path}: an entry with that id replaces both, or `remove` drops it "
                f"with a reason (COR-052 points 3 and 4)."
            )
        else:
            location = path
            message = (
                f"{_owner(collision.first)} and {_owner(collision.second)} both supply entry "
                f"{collision.id!r} to additive point {self.address!r}; drop the id under "
                f"`remove` in the project filler at {path}, with a reason, and supply the "
                f"entry you want there (COR-052 point 3)."
            )
        self.run.add(location, message, validators.Severity.ERROR)

    # --- endings

    def _mark_inert(self, candidate: _Candidate, answer: _Answer) -> None:
        self.inert.append(candidate)
        self.fillers.append(candidate.filler(FillerState.INERT, answer.inert or ""))

    def _pass_over_default(self, default: _Candidate) -> None:
        """An `alone` default with another filler declared: it does not answer, and
        a declared filler that broke never promotes it (COR-052 point 6)."""
        reason = (
            "not promoted: a declared filler is inert"
            if self.inert
            else "another filler is declared"
        )
        self.fillers.append(default.filler(FillerState.PASSED_OVER, reason))

    def _resolved(self, **outcome: Any) -> dict[str, Any]:
        self._report_inert(resolved=True)
        return {"fillers": tuple(self.fillers), "resolved": True, **outcome}

    def _unresolved(self, why: str, **outcome: Any) -> dict[str, Any]:
        """No value, never a partial one: a filler that answered is not taken."""
        self._report_inert(resolved=False)
        fillers = tuple(
            dataclasses.replace(f, state=FillerState.PASSED_OVER, reason=_UNUSED)
            if f.state is FillerState.TAKEN
            else f
            for f in self.fillers
        )
        return {"fillers": fillers, "resolved": False, "why": why, **outcome}

    def _report_inert(self, *, resolved: bool) -> None:
        """One finding per inert capability filler or default (COR-052 point 6): an
        error under `fail`; under `fallback` a warning, unless another finding
        already names it — an out-of-step contribution is the wiring's warning.
        The project filler's own errors name it whatever the policy."""
        for candidate in self.inert:
            answer = cast(_Answer, candidate.answer)
            if candidate.source is FillerSource.PROJECT:
                continue
            if self.inert_policy == FAIL:
                consequence = "the point's inert policy is `fail`, so it is unresolved"
                severity = validators.Severity.ERROR
            elif answer.reported:
                continue
            else:
                consequence = (
                    "the point resolves from the remaining fillers"
                    if resolved
                    else "no filler remains, so the point is unresolved"
                )
                severity = validators.Severity.WARNING
            self.run.add(
                candidate.location,
                f"{candidate.who} to {self.address!r} is inert: {answer.inert}; {consequence} "
                f"(COR-052 point 6).",
                severity,
            )


# --- merging --------------------------------------------------------------


@dataclass(frozen=True)
class _Collision:
    """One id two fillers supply. `index` is the project entry's, when one is involved."""

    id: str
    first: str
    second: str
    index: int | None = None


def _union(
    own: list[tuple[str, Any]],
    capabilities: list[tuple[str, list[tuple[str, Any]]]],
    default: list[tuple[str, Any]],
) -> tuple[list[Entry], list[_Collision]]:
    """Entries by id: the default's, each replaced whole by a capability's, each
    replaced whole by the project's; two capabilities with one id collide unless
    the project supplies it. Sorted by id — a union is a set."""
    result = {entry_id: Entry(entry_id, value, DEFAULT) for entry_id, value in default}
    owners: dict[str, list[str]] = {}
    for origin, entries in capabilities:
        for entry_id, value in entries:
            owners.setdefault(entry_id, []).append(origin)
            if len(owners[entry_id]) == 1:
                replaced = (DEFAULT,) if entry_id in result else ()
                result[entry_id] = Entry(entry_id, value, origin, replaced)
    for entry_id, value in own:
        replaced = tuple(owners.get(entry_id, ())) or (
            (result[entry_id].origin,) if entry_id in result else ()
        )
        result[entry_id] = Entry(entry_id, value, PROJECT, replaced)
    own_ids = {entry_id for entry_id, _value in own}
    collisions = [
        _Collision(entry_id, names[0], names[1])
        for entry_id, names in sorted(owners.items())
        if len(names) > 1 and entry_id not in own_ids
    ]
    return [result[entry_id] for entry_id in sorted(result)], collisions


def _additive(
    own: list[tuple[str, Any]],
    capabilities: list[tuple[str, list[tuple[str, Any]]]],
    default: list[tuple[str, Any]],
) -> tuple[list[Entry], list[_Collision]]:
    """Entries in precedence order — the project's, each capability's, the
    default's; any id supplied twice collides, the project's included."""
    entries = [Entry(entry_id, value, PROJECT) for entry_id, value in own]
    seen = {entry_id: PROJECT for entry_id, _value in own}
    own_index = {entry_id: index for index, (entry_id, _value) in enumerate(own)}
    collisions: list[_Collision] = []
    for origin, supplied in [*capabilities, (DEFAULT, default)]:
        for entry_id, value in supplied:
            first = seen.get(entry_id)
            if first is None:
                seen[entry_id] = origin
                entries.append(Entry(entry_id, value, origin))
            elif first == PROJECT:
                collisions.append(_Collision(entry_id, origin, PROJECT, own_index[entry_id]))
            else:
                collisions.append(_Collision(entry_id, first, origin))
    return entries, collisions


def _entry_problems(value: Any) -> list[tuple[str, str]]:
    """A `union` or `additive` value is a list of entries, each a string — its own
    id — or a mapping carrying a string `id`, no id twice."""
    if not isinstance(value, list):
        return [("", "a union or additive point's value is a list of entries.")]
    problems: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, entry in enumerate(cast("list[Any]", value)):
        entry_id = _entry_id(entry)
        if entry_id is None:
            problems.append(
                (
                    f"/{index}",
                    "an entry is a string — its own id — or a mapping with a string `id`.",
                )
            )
        elif entry_id in seen:
            problems.append((f"/{index}", f"entry id {entry_id!r} appears twice."))
        else:
            seen.add(entry_id)
    return problems


def _entry_id(entry: Any) -> str | None:
    if isinstance(entry, str) and entry:
        return entry
    if isinstance(entry, Mapping):
        entry_id = cast("Mapping[str, Any]", entry).get(ID_KEY)
        return entry_id if isinstance(entry_id, str) and entry_id else None
    return None


def _identified(value: Any) -> list[tuple[str, Any]]:
    """`(id, entry)` for each entry of a value `_entry_problems` accepted."""
    return [(cast(str, _entry_id(e)), e) for e in cast("list[Any]", value)]


# --- reading the declarations ---------------------------------------------


def _declared(declarations: cx.Declarations, capability: str, pointer: str) -> Mapping[str, Any]:
    """The mapping at the JSON Pointer `pointer` in `capability`'s package, or an empty one."""
    component = declarations.by_name(capability)
    node: Any = component.package if component is not None else None
    for token in pointer.split("/")[1:]:
        if isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = cast("list[Any]", node)[int(token)]
        elif isinstance(node, Mapping):
            node = cast("Mapping[str, Any]", node).get(token.replace("~1", "/").replace("~0", "~"))
        else:
            return {}
    return cast("Mapping[str, Any]", node) if isinstance(node, Mapping) else {}


def _inert_policy(value: Any) -> str:
    """`fallback` when absent. A value the schema refuses reads as `fail`: the
    reading under which a gate never passes on less than it meant to check."""
    if value is None:
        return FALLBACK
    return value if value in (FALLBACK, FAIL) else FAIL


def _default(value: Any) -> tuple[Any, str] | None:
    """`(value, participation)`, or None when the point declares no well-formed
    default (the packages member reports a malformed one)."""
    if not isinstance(value, Mapping):
        return None
    block = cast("Mapping[str, Any]", value)
    participation = block.get(PARTICIPATION_KEY)
    if VALUE_KEY not in block or participation not in (ALWAYS, ALONE):
        return None
    return block[VALUE_KEY], cast(str, participation)


def _supplies(entry: Mapping[str, Any], counterpart: cx.Counterpart) -> str:
    """How a contribution supplies its data, as the status report names it."""
    if VALUE_KEY in entry:
        return VALUE_KEY
    if counterpart.command is not None:
        return f"command {counterpart.command!r}"
    return "nothing"  # the answer says so: neither `value` nor `command`


# --- wording ----------------------------------------------------------------

_AMBIGUOUS = "several capabilities contribute and none is selected"
_STOPPED = "not asked: a filler before it is inert, and the point's inert policy is `fail`"
_FAIL_WHY = "a filler meant to answer is inert, and the point's inert policy is `fail`"
_UNFILLED = "unfilled: no filler is declared and the point has no default"
_UNUSED = "answered, but the point does not resolve"


def _owner(origin: str) -> str:
    """An origin as a sentence names it."""
    if origin == PROJECT:
        return "the project filler"
    return origin if origin == DEFAULT else repr(origin)


def _at(path: str, pointer: str) -> str:
    return f"{path}:{pointer}" if pointer else path


def _token(segment: Any) -> str:
    return str(segment).replace("~", "~0").replace("/", "~1")


# --- `pkit validate` ----------------------------------------------------------


def summary_lines(resolution: DataResolution) -> list[str]:
    """The data points' lines under the `connections` heading: a count, then any note."""
    if not resolution.points and not resolution.filler_files:
        return []
    resolved = sum(1 for p in resolution.points if p.resolved)
    return [
        f"{len(resolution.points)} data point(s): {resolved} resolved, "
        f"{len(resolution.points) - resolved} unresolved; "
        f"{resolution.filler_files} project filler file(s).",
        *resolution.notes,
    ]


# --- `pkit connections resolve` ------------------------------------------------


def resolve_point(target_root: Path, address: str) -> tuple[ResolvedPoint | None, str]:
    """The data point `address` resolved, or None with why no active provider
    defines it — as one run, so the wiring is resolved once for both answers.

    Only that point resolves: its fillers are asked, and no other point's command
    filler starts. Within a run the wiring, the filler files and any point
    already resolved are shared (`validators.once_per_run`), so the point is the
    one `pkit validate` and `pkit status` resolve among all the others."""

    def run() -> tuple[ResolvedPoint | None, str]:
        data_run = _data_run(target_root)
        for binding in _data_points(data_run.wiring):
            if binding.point.address == address:
                return _resolved(data_run, binding).point, ""
        return None, undefined_why(data_run.wiring, address)

    return validators.as_one_run(run)


def shared_point(target_root: Path, address: str) -> ResolvedPoint | None:
    """The data point `address` as the run in progress already resolved it — in
    `pkit validate`, or in another command the run started — or None: outside
    a live run, or not yet kept in it (`_resolved` keeps no resolution cut short
    by its asker's time). Read before `resolve_point`, it spares even the wiring
    (the run cache, `run_cache`)."""
    shared = _shared_outcome(target_root, address)
    return shared.point if shared is not None else None


# Where the point a reading command prints came from: resolved by the command
# itself, or read from what the run in progress resolved (`shared_point`).
FROM_RESOLUTION = "resolution"
FROM_RUN_CACHE = "run-cache"


def point_document(point: ResolvedPoint, *, source: str = FROM_RESOLUTION) -> dict[str, Any]:
    """One resolved data point as the stable document `pkit connections resolve
    --json` prints — the read a capability's own script uses to consume a point
    it defines, without importing this package (the CLI README, "Connections
    commands"). Everything the status report shows, as data: `value` is None
    when the point does not resolve, and never a partial value. `from` says
    whether this command resolved it or read the run's resolution."""
    return {
        "address": point.address,
        "defined": True,
        "from": source,
        "provider": point.provider,
        "policy": point.policy,
        "inert_policy": point.inert_policy,
        "participation": point.participation,
        "resolved": point.resolved,
        "why": point.why,
        "value": point.value if point.resolved else None,
        "origin": point.origin,
        "entries": [
            {"id": e.id, "origin": e.origin, "replaces": list(e.replaces), "value": e.value}
            for e in point.entries
        ],
        "removals": [
            {"id": r.id, "reason": r.reason, "removed_from": list(r.removed_from)}
            for r in point.removals
        ],
        "fillers": [
            {
                "source": f.source.value,
                "name": f.name,
                "supplies": f.supplies,
                "state": f.state.value,
                "reason": f.reason,
                "query_contract": f.query_contract,
            }
            for f in point.fillers
        ],
    }


def point_from_document(document: Mapping[str, Any]) -> ResolvedPoint:
    """The inverse of `point_document`: the resolved point a document states.
    Raises KeyError, TypeError or ValueError on a document it did not write."""
    return ResolvedPoint(
        address=document["address"],
        provider=document["provider"],
        policy=document["policy"],
        inert_policy=document["inert_policy"],
        participation=document["participation"],
        fillers=tuple(
            Filler(
                FillerSource(f["source"]),
                f["name"],
                f["supplies"],
                FillerState(f["state"]),
                f["reason"],
                f["query_contract"],
            )
            for f in document["fillers"]
        ),
        resolved=document["resolved"],
        value=document["value"],
        origin=document["origin"],
        entries=tuple(
            Entry(e["id"], e["value"], e["origin"], tuple(e["replaces"]))
            for e in document["entries"]
        ),
        removals=tuple(
            Removal(r["id"], r["reason"], tuple(r["removed_from"])) for r in document["removals"]
        ),
        why=document["why"],
    )


def undefined_document(address: str, why: str) -> dict[str, Any]:
    """The document for an address no active provider defines as a data point."""
    return {
        "address": address,
        "defined": False,
        "from": FROM_RESOLUTION,
        "resolved": False,
        "why": why,
        "value": None,
    }
