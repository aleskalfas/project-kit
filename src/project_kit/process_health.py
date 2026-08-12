"""The process-health check (COR-042 / ADR-048): the report-only missed-hand-off
walk over the opt-in `handoff` contracts declared on `depends_on` entries.

A `depends_on` entry MAY carry a hand-off contract — the upstream TRIGGER state
plus two binding-supplied seam predicates (`candidates`, `resolve`). This module
walks every installed process definition, evaluates ONLY the entries carrying a
contract (entries without one keep COR-038's full inert status — never evaluated
by anything), and reports every MISSED hand-off: an upstream subject currently
AT its trigger state whose downstream counterpart is ABSENT.

THE PLACEMENT POINT (ADR-048, load-bearing). This is a SIBLING READER beside the
engine, not part of it. Unlike the graph render (declarations only, never the
engine), health DOES read live reality — upstream positions through the engine's
own public per-subject resolution (`ProcessEngine.for_subject` +
`resolve_position`) plus the two binding predicates — and is safe by being
REPORT-ONLY, not by never-reading: no move is blocked, no state stored, nothing
journaled or remediated. The runtime operation paths (`status` / `can-move` /
`move` / `validate`) import NOTHING from this module and never read
`depends_on`; that boundary keeps COR-042's re-scoped reader-set claim
structurally true and is pinned by test (the mirror of the render's
never-invokes-the-engine pin).

The check's semantics, all fixed by COR-042:

- **Missed = absent.** `resolve` answers existence of the downstream
  counterpart, never its position or progress. >=1 downstream id satisfies the
  hand-off (fan-out); several upstreams may resolve to one downstream (fan-in) —
  each upstream is checked independently.
- **"At the trigger" is a live snapshot** — candidates are confirmed one subject
  at a time through the engine's position resolution at each run; the journal is
  never consulted (it would be silently incomplete under detection-over-reality).
- **An uninterpretable contract is INDETERMINATE, never green**: an upstream
  address that does not resolve to a definition, a trigger that is not a state
  of that definition, or a malformed contract block — reported distinctly,
  holding the exit code non-zero (a typo'd trigger must not report green
  forever).
- **Determinate-empty is clean; broken-empty is not.** A candidate source that
  evaluated without error and confirmed zero subjects is a clean, determinate
  answer (no lines for that contract). An erroring/unavailable candidate source,
  an erroring `resolve`, or an unreadable upstream position is indeterminate —
  never counted as "nothing missed".
- **One line per (contract x upstream subject)**, de-duplicated within a
  contract; subjects name-sorted.
- A definition that cannot be LOADED at all may hide contracts, so it is
  surfaced distinctly and counted indeterminate (fail-closed — the same
  lying-report argument), never silently dropped.

Seam realization (ADR-048, predicate-runner contract reused unchanged — one
subject positional + `--json`, cwd = repo root):

- `candidates` runs with the SUBJECT SLOT carrying the contract's UPSTREAM
  PROCESS ADDRESS (the scope it enumerates for); the trigger is statically known
  to the binding from the same contract declaration it owns. Payload:
  `{candidates: ["id", ...]}` — the source PROPOSES, the engine's per-subject
  position read disposes.
- `resolve` runs once per confirmed upstream subject, the subject slot carrying
  that UPSTREAM SUBJECT ID. Payload: `{downstream: ["id", ...]}` — non-empty =
  satisfied, explicitly EMPTY = determinate absence (a miss), anything else
  (error / no list) = indeterminate.

Both predicates are registered commands of the DECLARING (downstream)
capability's `package.yaml` — the same registry every engine predicate resolves
through.

Determinism: contracts order TOPOLOGICALLY over the contract wiring
(upstream-most processes first, name tie-breaks, deterministic name-order
fallback on declared cycles); subjects name-sorted; `--json` is byte-stable
(sorted keys, no TTY styling) like the graph's machine form. No time/age-based
ordering anywhere.

Exit contract (rendered by the CLI): non-zero on ANY miss or ANY indeterminate;
zero only when both totals are zero.

Over that walk sits the authoring layer's completion signal (COR-044): the
interpretation-only view, a pure CONSUMER of the report this module builds
(`build_interpretation`), which asks only whether every contract is
INTERPRETABLE and never counts a miss. It adds the one check the live walk
structurally cannot make — a STATIC read of both seams' registration and
implementation state — because the walk exercises `resolve` only for subjects
that happen to be at the trigger, and an authoring done-signal must not depend
on who is standing there when it runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_kit import cli_render
from project_kit.process import (
    PREDICATE_STUB_MARKER,
    PredicateRunner,
    ProcessDefinition,
    ProcessEngine,
    ProcessError,
    _load_command_registry,
    load_definition,
)
from project_kit.process_graph import discover_process_addresses

# Finding kinds — the only two things a per-subject line can report (a satisfied
# hand-off produces NO line, COR-042's one-line-per-miss shape).
KIND_MISSED = "missed"
KIND_INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class HandoffContract:
    """One declared, evaluable hand-off contract (COR-042 point 1).

    `downstream` is the process whose definition DECLARES the `depends_on`
    entry (the subscriber — work flows upstream -> downstream); `upstream` is
    the entry's upstream address. `state_id` is the hosting state — audit
    colour only, with NO semantic effect on the check (COR-042: the check reads
    upstream reality and downstream existence only). `handoff` is the raw
    declared block, validated at evaluation time (a malformed block is an
    uninterpretable contract — indeterminate, never green). `capability` /
    `capability_dir` locate the declaring capability's command registry, which
    both seam predicates resolve through.
    """

    downstream: str
    upstream: str
    state_id: str | None
    handoff: Any
    capability: str
    capability_dir: Path

    @property
    def trigger(self) -> str:
        """The declared trigger state, or "" when the block is malformed (kept
        renderable so an uninterpretable contract still gets a header line)."""
        if isinstance(self.handoff, dict):
            value = self.handoff.get("trigger")
            if isinstance(value, str):
                return value
        return ""


@dataclass(frozen=True)
class Finding:
    """One reported line under a contract.

    `subject` is the upstream subject id, or None for a CONTRACT-LEVEL
    indeterminacy (uninterpretable contract / broken candidate source — the
    whole contract could not be evaluated, so there is no subject to name).
    `kind` is `missed` or `indeterminate`; `reason` is the self-explaining why.
    """

    subject: str | None
    kind: str
    reason: str

    def sort_key(self) -> tuple[str, str, str]:
        return (self.subject or "", self.kind, self.reason)


@dataclass(frozen=True)
class ContractReport:
    """One evaluated contract: its findings plus the determinate audit counts.

    `at_trigger` / `satisfied` are colour ("how many were checked, how many
    picked up"); the findings are the report. A clean contract (all satisfied,
    or a determinate-empty candidate set) has NO findings.
    """

    contract: HandoffContract
    findings: tuple[Finding, ...]
    at_trigger: int
    satisfied: int

    @property
    def misses(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind == KIND_MISSED)

    @property
    def indeterminate(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind == KIND_INDETERMINATE)


@dataclass(frozen=True)
class SkippedDefinition:
    """A discovered process address whose definition could not be loaded.

    Surfaced AND counted indeterminate (unlike the render's advisory skip): an
    unreadable definition may declare contracts this walk cannot see, so a green
    report over it would lie — the same fail-closed argument as a broken
    candidate source. `reason` is the loader's own message.
    """

    address: str
    reason: str

    def sort_key(self) -> tuple[str, str]:
        return (self.address, self.reason)


@dataclass(frozen=True)
class HealthReport:
    """The whole walk's result: evaluated contracts (topologically ordered) plus
    the definitions that could not be read. Immutable; renders read it many
    ways."""

    contracts: tuple[ContractReport, ...]
    skipped: tuple[SkippedDefinition, ...]

    @property
    def missed_total(self) -> int:
        return sum(len(c.misses) for c in self.contracts)

    @property
    def indeterminate_total(self) -> int:
        """Every indeterminate line — per-subject and contract-level — plus one
        per unreadable definition (its contract set is unknown, fail-closed)."""
        return sum(len(c.indeterminate) for c in self.contracts) + len(self.skipped)

    @property
    def ok(self) -> bool:
        """The exit-code contract (COR-042): clean iff no miss AND no
        indeterminate."""
        return self.missed_total == 0 and self.indeterminate_total == 0


# --- collecting the declared contracts (declarations only) -----------------


def collect_contracts(
    repo_root: Path, addresses: list[str] | None = None
) -> tuple[list[HandoffContract], list[SkippedDefinition]]:
    """Walk every installed process definition's `depends_on` entries and
    collect the ones that OPT IN to a hand-off contract.

    The opt-in test is the presence of the `handoff` KEY: entries without it are
    never evaluated by anything (COR-038 preserved); an entry that declares the
    key with a malformed/null value HAS opted in and will evaluate
    indeterminate (a half-written contract must not read as green). Definitions
    that fail to load are returned as skipped, never silently dropped.
    """
    if addresses is None:
        addresses = discover_process_addresses(repo_root)
    contracts: list[HandoffContract] = []
    skipped: list[SkippedDefinition] = []
    for address in addresses:
        try:
            definition = load_definition(repo_root, address)
        except ProcessError as exc:
            skipped.append(SkippedDefinition(address=address, reason=str(exc)))
            continue
        contracts.extend(_contracts_of(address, definition))
    return contracts, skipped


def _contracts_of(address: str, definition: ProcessDefinition) -> list[HandoffContract]:
    """One definition's declared contracts, in declaration order."""
    out: list[HandoffContract] = []
    for state in definition.states:
        state_id = state.get("id")
        state_id = state_id if isinstance(state_id, str) else None
        depends_on = state.get("depends_on")
        if not isinstance(depends_on, list):
            continue
        for entry in depends_on:
            if not isinstance(entry, dict) or "handoff" not in entry:
                continue  # no opt-in: fully inert, untouched (COR-038)
            upstream = entry.get("upstream")
            out.append(
                HandoffContract(
                    downstream=address,
                    upstream=upstream if isinstance(upstream, str) else "",
                    state_id=state_id,
                    handoff=entry.get("handoff"),
                    capability=definition.capability,
                    capability_dir=definition.capability_dir,
                )
            )
    return out


# --- ordering: topological over the contract wiring ------------------------


def _topological_rank(contracts: list[HandoffContract]) -> dict[str, int]:
    """Rank every process participating in a contract, sources first.

    Kahn's algorithm over the upstream -> downstream coupling edges, taking the
    lexicographically-smallest ready node each step (name tie-break). When no
    node is ready but nodes remain (a declared cycle), the smallest-named
    remaining node is force-released — the deterministic name-order fallback the
    report contract fixes. The result is a total, deterministic rank.
    """
    nodes = sorted({c.upstream for c in contracts} | {c.downstream for c in contracts})
    successors: dict[str, set[str]] = {n: set() for n in nodes}
    indegree: dict[str, int] = {n: 0 for n in nodes}
    for c in contracts:
        if c.downstream not in successors[c.upstream] and c.upstream != c.downstream:
            successors[c.upstream].add(c.downstream)
            indegree[c.downstream] += 1

    rank: dict[str, int] = {}
    remaining = set(nodes)
    ready = sorted(n for n in nodes if indegree[n] == 0)
    while remaining:
        if not ready:
            # Declared cycle: force-release the smallest-named remaining node.
            ready = [min(remaining)]
        node = ready.pop(0)
        if node not in remaining:
            continue
        remaining.discard(node)
        rank[node] = len(rank)
        released = []
        for nxt in successors[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0 and nxt in remaining:
                released.append(nxt)
        ready = sorted(set(ready) | set(released))
    return rank


def _contract_sort_key(
    contract: HandoffContract, rank: dict[str, int]
) -> tuple[int, int, str, str]:
    """Total order for the report: upstream-most coupling groups first, then the
    downstream's rank, then trigger and hosting state. Python's stable sort
    keeps declaration order for exact duplicates (same triple declared twice),
    which is itself deterministic (sorted addresses, in-definition order)."""
    return (
        rank.get(contract.upstream, len(rank)),
        rank.get(contract.downstream, len(rank)),
        contract.trigger,
        contract.state_id or "",
    )


# --- evaluating one contract (live, read-only) -----------------------------


def _contract_indeterminate(
    contract: HandoffContract, reason: str
) -> ContractReport:
    """The whole contract could not be evaluated: one contract-level
    indeterminate finding (fail-closed — reported distinctly, never green)."""
    return ContractReport(
        contract=contract,
        findings=(Finding(subject=None, kind=KIND_INDETERMINATE, reason=reason),),
        at_trigger=0,
        satisfied=0,
    )


def evaluate_contract(repo_root: Path, contract: HandoffContract) -> ContractReport:
    """Evaluate one contract per COR-042 point 2. Read-only: it runs the two
    seam predicates and the upstream's detection predicates live, writing
    nothing — never `move`, never a journal entry.

    Order of fail-closed checks: malformed contract block -> unresolvable
    upstream address -> phantom trigger state -> broken candidate source; then
    per confirmed subject: unreadable position -> broken `resolve` -> explicit
    absence (the miss) / >=1 downstream id (satisfied, no line).
    """
    handoff = contract.handoff
    if not isinstance(handoff, dict):
        return _contract_indeterminate(
            contract,
            "hand-off contract is not a mapping (a half-written opt-in is "
            "uninterpretable; declare trigger/candidates/resolve or remove the "
            "`handoff` key)",
        )
    trigger = handoff.get("trigger")
    candidates_predicate = handoff.get("candidates")
    resolve_predicate = handoff.get("resolve")
    if (
        not isinstance(trigger, str)
        or not trigger
        or not isinstance(candidates_predicate, dict)
        or not isinstance(resolve_predicate, dict)
    ):
        return _contract_indeterminate(
            contract,
            "hand-off contract is malformed (needs trigger + candidates + "
            "resolve); uninterpretable, never green",
        )

    if not contract.upstream:
        return _contract_indeterminate(
            contract, "entry declares no upstream address to check against"
        )
    try:
        upstream_def = load_definition(repo_root, contract.upstream)
    except ProcessError as exc:
        return _contract_indeterminate(
            contract,
            f"upstream address {contract.upstream!r} does not resolve to a "
            f"definition: {exc}",
        )
    if upstream_def.state(trigger) is None:
        return _contract_indeterminate(
            contract,
            f"trigger {trigger!r} is not a state of {contract.upstream!r} "
            "(phantom trigger — a typo or a renamed upstream state must not "
            "report green)",
        )

    # The candidate source (ADR-048): a registered command of the DECLARING
    # capability, subject slot = the upstream address (the scope it enumerates).
    candidate_ids = _read_candidates(repo_root, contract, candidates_predicate)
    if candidate_ids is None:
        return _contract_indeterminate(
            contract,
            f"the candidate source {candidates_predicate.get('run')!r} could "
            "not be evaluated (errored / timed out / unparseable / "
            "unregistered, or returned no `candidates` list); broken-empty is "
            "never read as 'nothing missed'",
        )

    findings: list[Finding] = []
    at_trigger = 0
    satisfied = 0
    for candidate_id in candidate_ids:
        # Confirm the candidate is AT the trigger through the engine's own
        # per-subject position resolution — the source proposes, live detection
        # disposes (ADR-048; the live-snapshot rule, COR-042).
        try:
            engine = ProcessEngine.for_subject(upstream_def, repo_root, candidate_id)
            position = engine.resolve_position()
        except ProcessError as exc:
            findings.append(
                Finding(
                    subject=candidate_id,
                    kind=KIND_INDETERMINATE,
                    reason=f"upstream position could not be read: {exc}",
                )
            )
            continue
        if position.state_id != trigger:
            if position.state_id is None and position.indeterminate:
                findings.append(
                    Finding(
                        subject=candidate_id,
                        kind=KIND_INDETERMINATE,
                        reason="upstream position is indeterminate (a detection "
                        "predicate could not be evaluated); an unreadable "
                        "position is never read as 'not at the trigger'",
                    )
                )
            # Determinately elsewhere (or determinately positionless): not at
            # the trigger — no line (past-trigger subjects leave the report).
            continue

        at_trigger += 1
        downstream_ids = _read_resolution(
            repo_root, contract, resolve_predicate, candidate_id
        )
        if downstream_ids is None:
            findings.append(
                Finding(
                    subject=candidate_id,
                    kind=KIND_INDETERMINATE,
                    reason=f"the resolve predicate {resolve_predicate.get('run')!r} "
                    "could not be evaluated (errored / timed out / unparseable / "
                    "unregistered, or returned no explicit `downstream` list); "
                    "an error is never read as absence",
                )
            )
            continue
        if downstream_ids:
            satisfied += 1  # >=1 downstream exists: hand-off satisfied, no line
            continue
        findings.append(
            Finding(
                subject=candidate_id,
                kind=KIND_MISSED,
                reason="no downstream subject picks this up (resolve answered "
                "explicit absence)",
            )
        )

    return ContractReport(
        contract=contract,
        findings=tuple(sorted(findings, key=Finding.sort_key)),
        at_trigger=at_trigger,
        satisfied=satisfied,
    )


def _read_candidates(
    repo_root: Path, contract: HandoffContract, predicate: dict[str, Any]
) -> list[str] | None:
    """The de-duplicated, name-sorted upstream candidate ids from the
    `candidates` seam, or None when the source is broken (indeterminate).
    An explicit empty list is a DETERMINATE empty answer -> []."""
    runner = PredicateRunner(
        capability=contract.capability,
        capability_dir=contract.capability_dir,
        repo_root=repo_root,
        subject=contract.upstream,
    )
    try:
        payload = runner.run_raw(predicate)
    except ProcessError:
        # Unregistered command: for the report-only walk this folds into the
        # contract's indeterminacy rather than aborting the whole report.
        return None
    if payload is None:
        return None
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        return None
    # A malformed member makes the WHOLE payload uninterpretable (indeterminate):
    # silently filtering it would convert a broken answer into a determinate one
    # (empty -> clean), breaching COR-042's broken-is-never-determinate rule.
    if any(not isinstance(c, str) or not c for c in raw):
        return None
    # De-dup + name-sort: one line per (contract x subject), deterministic order.
    return sorted(set(raw))


def _read_resolution(
    repo_root: Path,
    contract: HandoffContract,
    predicate: dict[str, Any],
    upstream_subject: str,
) -> list[str] | None:
    """One upstream subject's downstream id(s) from the `resolve` seam.

    Returns the (possibly several — fan-out) downstream ids; [] for EXPLICIT
    determinate absence (the miss); None when the predicate is broken
    (indeterminate — an error is never read as absence)."""
    runner = PredicateRunner(
        capability=contract.capability,
        capability_dir=contract.capability_dir,
        repo_root=repo_root,
        subject=upstream_subject,
    )
    try:
        payload = runner.run_raw(predicate)
    except ProcessError:
        return None
    if payload is None:
        return None
    raw = payload.get("downstream")
    if not isinstance(raw, list):
        return None
    # Same strictness as the candidates seam: a malformed member is an
    # uninterpretable payload (indeterminate), never filtered into `[]`
    # (which would read as a determinate MISS from a broken answer).
    if any(not isinstance(d, str) or not d for d in raw):
        return None
    return list(raw)


# --- the whole walk --------------------------------------------------------


def build_report(repo_root: Path, focus: str | None = None) -> HealthReport:
    """Walk every declared contract and build the health report (COR-042).

    `focus` keeps only contracts touching that `<capability>:<process-id>` as
    either endpoint (only those are evaluated — the walk stays as narrow as the
    ask). Unreadable definitions are surfaced regardless of focus: whether they
    touch the focused process is exactly what cannot be known.
    """
    contracts, skipped = collect_contracts(repo_root)
    if focus is not None:
        contracts = [c for c in contracts if focus in (c.upstream, c.downstream)]
    rank = _topological_rank(contracts)
    ordered = sorted(contracts, key=lambda c: _contract_sort_key(c, rank))
    return HealthReport(
        contracts=tuple(evaluate_contract(repo_root, c) for c in ordered),
        skipped=tuple(sorted(skipped, key=SkippedDefinition.sort_key)),
    )


# --- rendering -------------------------------------------------------------


def _finding_line(finding: Finding) -> str:
    marker = "✗" if finding.kind == KIND_MISSED else "?"
    return f"    {marker} {finding.subject}  {finding.reason}"


def render_narrative(report: HealthReport) -> str:
    """The scannable text report: per contract a flow-direction header
    `upstream → downstream   @trigger`, one line per missed/indeterminate
    subject (satisfied subjects produce NO line), a clean note otherwise, then
    the summary. TTY-aware styling (never load-bearing); wrapped prose through
    `cli_render.wrap`."""
    lines: list[str] = []
    lines.append(
        cli_render.style("title", "Process health") + "  (missed hand-off check)"
    )
    if not report.contracts and not report.skipped:
        lines.append("")
        lines.append("  (no hand-off contracts declared)")

    for cr in report.contracts:
        contract = cr.contract
        lines.append("")
        header = cli_render.style(
            "strong", f"{contract.upstream} → {contract.downstream}"
        )
        trigger = contract.trigger or "(no trigger)"
        lines.append(f"  {header}   @{trigger}")
        if not cr.findings:
            if cr.at_trigger == 0:
                lines.append("    ✓ clean — no subjects at the trigger")
            else:
                lines.append(
                    f"    ✓ clean — {cr.at_trigger} subject(s) at the trigger, "
                    "every one picked up"
                )
            continue
        for finding in cr.findings:
            if finding.subject is None:
                # Contract-level indeterminacy: reported distinctly.
                lines.extend(
                    cli_render.wrap(
                        f"? contract indeterminate: {finding.reason}",
                        indent="    ",
                    )
                )
            else:
                lines.append(_finding_line(finding))

    if report.skipped:
        count = len(report.skipped)
        noun = "definition" if count == 1 else "definitions"
        lines.append("")
        lines.append(
            "  "
            + cli_render.style(
                "warn",
                f"⚠ {count} {noun} could not be loaded (contract set unknown — "
                "counted indeterminate):",
            )
        )
        for s in report.skipped:
            lines.extend(cli_render.wrap(f"{s.address} — {s.reason}", indent="    "))

    lines.append("")
    summary = f"{report.missed_total} missed, {report.indeterminate_total} indeterminate"
    lines.append(
        "  " + cli_render.style("strong" if not report.ok else "success", summary)
    )
    return "\n".join(lines) + "\n"


# --- the interpretation-only view (COR-044) --------------------------------


@dataclass(frozen=True)
class ContractInterpretation:
    """One contract seen through the authoring lens: everything that stops it
    being interpretable, and nothing else.

    `indeterminate` is the walker's own indeterminate findings for the contract
    PLUS the static seam findings (below) — a single list, because to the author
    they answer one question: is there anything here that is not yet
    interpretable?
    """

    contract: HandoffContract
    indeterminate: tuple[Finding, ...]


@dataclass(frozen=True)
class InterpretationReport:
    """The authoring-completion view over a `HealthReport`. Misses are absent by
    construction — not filtered at render time but never carried here — so no
    consumer of this report can accidentally make the done-signal depend on
    them."""

    contracts: tuple[ContractInterpretation, ...]
    skipped: tuple[SkippedDefinition, ...]

    @property
    def indeterminate_total(self) -> int:
        return sum(len(c.indeterminate) for c in self.contracts) + len(self.skipped)

    @property
    def ok(self) -> bool:
        """The variant's exit contract (COR-044): clean iff nothing is
        indeterminate. The default health run's contract is untouched."""
        return self.indeterminate_total == 0


def build_interpretation(report: HealthReport) -> InterpretationReport:
    """Re-read a completed `HealthReport` as the authoring done-signal.

    A pure CONSUMER of the walker's result — it takes a built report and never
    walks contracts itself (COR-042 point 5's design-once rule). What it adds is
    the STATIC seam check: the walk can only exercise a seam that some subject
    happens to reach, so a freshly authored contract with nobody at its trigger
    would otherwise report "interpretable" while its `resolve` seam is still an
    unwritten stub. That would be a lying done-signal on COR-044's own
    completion criterion, so interpretability is decided statically — the same
    verdict whatever reality holds at the moment of the run.
    """
    return InterpretationReport(
        contracts=tuple(
            ContractInterpretation(
                contract=cr.contract,
                indeterminate=cr.indeterminate + tuple(_static_seam_findings(cr.contract)),
            )
            for cr in report.contracts
        ),
        skipped=report.skipped,
    )


# The two seam slots a hand-off contract declares (COR-042 / ADR-048), in the
# order the check reports them.
_SEAM_SLOTS = ("candidates", "resolve")


def _static_seam_findings(contract: HandoffContract) -> list[Finding]:
    """Contract-level indeterminates that hold regardless of who is at the
    trigger: a seam the declaring capability does not register, one whose script
    is missing, or one that is still the scaffolded stub.

    Deliberately overlaps with the walk: a seam the walk DID exercise and found
    broken is reported twice, once per lens ("could not be evaluated" from the
    run, "is still the scaffolded stub" from the declaration). Both are true and
    both point at the same fix, and suppressing either would make the
    static/runtime split invisible to the author — the honest report is the
    union.
    """
    handoff = contract.handoff
    if not isinstance(handoff, dict):
        return []  # a malformed block: the walk's own finding says it better
    registry = _load_command_registry(contract.capability_dir)
    findings: list[Finding] = []
    for slot in _SEAM_SLOTS:
        predicate = handoff.get(slot)
        run_name = predicate.get("run") if isinstance(predicate, dict) else None
        if not isinstance(run_name, str) or not run_name:
            continue  # malformed declaration: the walk reports it as such
        script = registry.get(run_name)
        if script is None:
            findings.append(
                _seam_finding(
                    slot,
                    run_name,
                    f"names a command {contract.capability!r} does not register "
                    "in its package.yaml",
                )
            )
            continue
        if not script.is_file():
            findings.append(
                _seam_finding(
                    slot,
                    run_name,
                    f"registers a script that is not on disk ({script.name})",
                )
            )
            continue
        if _is_unimplemented_stub(script):
            findings.append(
                _seam_finding(
                    slot,
                    run_name,
                    "is still the scaffolded stub — it fails closed on every "
                    "subject, so the contract cannot yet tell the truth "
                    f"(implement it and delete the {PREDICATE_STUB_MARKER} line)",
                )
            )
    return findings


def _seam_finding(slot: str, run_name: str, problem: str) -> Finding:
    return Finding(
        subject=None,
        kind=KIND_INDETERMINATE,
        reason=f"the {slot} seam {run_name!r} {problem}",
    )


def _is_unimplemented_stub(script: Path) -> bool:
    """True when a predicate script still carries the scaffold's stub marker.

    An unreadable script is NOT called a stub — it is a different problem, and
    the walk reports it fail-closed when it runs the predicate.
    """
    try:
        return PREDICATE_STUB_MARKER in script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def render_interpretation_narrative(report: InterpretationReport) -> str:
    """The interpretation-only view (COR-044 / COR-042 point 5): the authoring
    layer's completion signal is "no indeterminates" — the contract resolves,
    the trigger is a real upstream state, the seams execute.

    Renders an `InterpretationReport`, which carries no miss surface at all — a
    fresh, correct contract routinely reports real misses (upstream work waiting
    is what motivated declaring it), so miss-count is never the authoring
    done-signal.
    """
    lines: list[str] = []
    lines.append(
        cli_render.style("title", "Process interpretability")
        + "  (authoring check — indeterminates only; misses are not counted)"
    )
    if not report.contracts and not report.skipped:
        lines.append("")
        lines.append("  (no hand-off contracts declared)")

    for cr in report.contracts:
        contract = cr.contract
        lines.append("")
        header = cli_render.style(
            "strong", f"{contract.upstream} → {contract.downstream}"
        )
        trigger = contract.trigger or "(no trigger)"
        lines.append(f"  {header}   @{trigger}")
        if not cr.indeterminate:
            lines.append(
                "    ✓ interpretable — the contract resolves and both seams are "
                "implemented and execute"
            )
            continue
        for finding in cr.indeterminate:
            if finding.subject is None:
                lines.extend(
                    cli_render.wrap(
                        f"? contract indeterminate: {finding.reason}",
                        indent="    ",
                    )
                )
            else:
                lines.append(_finding_line(finding))

    if report.skipped:
        count = len(report.skipped)
        noun = "definition" if count == 1 else "definitions"
        lines.append("")
        lines.append(
            "  "
            + cli_render.style(
                "warn",
                f"⚠ {count} {noun} could not be loaded (contract set unknown — "
                "counted indeterminate):",
            )
        )
        for s in report.skipped:
            lines.extend(cli_render.wrap(f"{s.address} — {s.reason}", indent="    "))

    lines.append("")
    clean = report.indeterminate_total == 0
    summary = f"{report.indeterminate_total} indeterminate (misses not counted)"
    lines.append("  " + cli_render.style("success" if clean else "strong", summary))
    return "\n".join(lines) + "\n"


def render_interpretation_json(report: InterpretationReport) -> str:
    """The interpretation-only machine form: the health `--json` shape minus
    every miss surface (no `misses` arrays, no missed/at_trigger/satisfied
    counts — those would let a consumer derive the miss count this view
    deliberately does not report). Byte-stable like the full form."""
    payload = {
        "contracts": [
            {
                "upstream": cr.contract.upstream,
                "downstream": cr.contract.downstream,
                "trigger": cr.contract.trigger or None,
                "state": cr.contract.state_id,
                "indeterminate": [
                    {"subject": f.subject, "reason": f.reason}
                    for f in cr.indeterminate
                ],
                "counts": {"indeterminate": len(cr.indeterminate)},
            }
            for cr in report.contracts
        ],
        "skipped": [
            {"address": s.address, "reason": s.reason} for s in report.skipped
        ],
        "totals": {"indeterminate": report.indeterminate_total},
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_json(report: HealthReport) -> str:
    """The byte-stable machine form (ADR-024's invariant: deterministic order,
    no TTY styling, identical bytes across runs). Contracts carry the report's
    topological order; keys sort; subject arrays are pre-sorted."""
    payload = {
        "contracts": [
            {
                "upstream": cr.contract.upstream,
                "downstream": cr.contract.downstream,
                "trigger": cr.contract.trigger or None,
                "state": cr.contract.state_id,
                "misses": [
                    {"subject": f.subject, "reason": f.reason} for f in cr.misses
                ],
                "indeterminate": [
                    {"subject": f.subject, "reason": f.reason}
                    for f in cr.indeterminate
                ],
                "counts": {
                    "at_trigger": cr.at_trigger,
                    "satisfied": cr.satisfied,
                    "missed": len(cr.misses),
                    "indeterminate": len(cr.indeterminate),
                },
            }
            for cr in report.contracts
        ],
        "skipped": [
            {"address": s.address, "reason": s.reason} for s in report.skipped
        ],
        "totals": {
            "missed": report.missed_total,
            "indeterminate": report.indeterminate_total,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
