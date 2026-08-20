"""Reviewer-contribution collector (per project-management:DEC-032).

DEC-032 makes the required-reviewer set resolve per PR from the closing
issues' classification, and lets an installed capability *contribute* a
requirement ("PRs in workstream `design` additionally require the
`design-reviewer`"). This module is the data foundation: it walks the
manifest-registered capabilities, reads each one's reviewer-contribution
declaration if present, validates the rules, and returns a resolution
structure the gate-checker (#145), `pre-check` (#146), and `review-pr`
(#147) consume.

Three disciplines from DEC-032 shape the walk:

  * **Manifest-scoped, orphan-safe.** The collector iterates capabilities
    registered in `.pkit/manifest.yaml`'s `components:` list — NOT
    arbitrary directories under `.pkit/capabilities/`. An orphan capability
    directory (botched uninstall, stash, rebase) must never silently inject
    a merge gate. This mirrors DEC-030's `collect_capability_overlays`.

  * **Deployed-agent constraint.** A contributed `reviewer` name carries
    the same constraint as a DEC-028 `local_registered:` entry — it must
    correspond to a deployed agent file (resolved via `_lib.agents`). An
    installed contribution naming an undeployed agent is NOT silently
    dropped: the matched rule stays in the result carrying its broken
    resolution status, so a consumer that resolves a PR's required set
    sees an unsatisfiable requirement (fail-closed) rather than a smaller
    one (fail-open). See "The fail-closed seam" below.

  * **Union over closing issues (D1).** A PR's required set is the UNION
    of contributions matched against the classification of *any* issue the
    PR closes. The collector owns that union once
    (`reviewers_for_issues`), so the three consumers cannot diverge on who
    is required.

The fail-closed seam
--------------------

A `ContributionRule` that matched a declaration but failed resolution
(its reviewer agent is undeployed, etc.) is kept in `rules` with
`deployed=False` and a `resolution_error`. The gate-checker thus *sees*
"design-reviewer required but unsatisfiable" and refuses by construction,
instead of silently dropping the requirement. So a consumer can't weaken
the gate by reading `rules`/`reviewers_for*` and forgetting a sibling
error channel, `ContributionCollection.ok` / `has_blocking_errors` is the
single predicate every consumer is meant to gate on first — making
fail-closed the path of least resistance.

Layering, mirroring the other `_lib` libraries (e.g. `workstreams.py`):

  * `parse_contributions(data, capability)` is the pure, side-effect-free
    core — it takes already-parsed YAML and validates shape, returning
    rules + errors. Callers that already hold parsed data use it directly.
  * `collect_contributions(...)` is the file-walking entry point — it reads
    the manifest, reads each registered capability's declaration, parses it,
    and resolves each `reviewer` against the deployed-agent directory.

Extraction (ADR-038)
--------------------
The orphan-safe manifest-walk, per-declaration read, and error taxonomy are no
longer implemented here — they are the shared contribution-collector core in
`_lib/contribution_collector.py`, of which this module is the first
instantiation (`collect_contributions` calls `contribution_collector.collect`
with the reviewer-specific parser + agent-deployed resolver, at the
`FAIL_CLOSED` disposition DEC-032 requires). The refactor is behaviour-
preserving: every public export below keeps its name, shape, and semantics, so
the #145/#146/#147 consumers are untouched. `ContributionError`,
`list_registered_capabilities`, and the `ERROR_PARSE` / `ERROR_MALFORMED`
constants are re-exported from the core so a consumer importing them from here
still resolves the one definition.

Exports (the types #145/#146/#147 import):

    ContributionError       — frozen dataclass: kind + capability + message
                              (re-exported from contribution_collector)
    ContributionRule        — frozen dataclass: capability, predicate,
                              reviewer, floor, deployed, resolution_error
    ContributionCollection  — frozen dataclass: rules + errors + walked,
                              with `ok` / `has_blocking_errors` /
                              `reviewers_for` / `reviewers_for_issues` /
                              `reviewers_for_floors`
    CONTRIBUTIONS_FILENAME  — the per-capability declaration filename
    parse_contributions(data, capability) -> tuple[rules, errors]
    list_registered_capabilities(manifest_data) -> tuple[str, ...]
    collect_contributions(repo_root, *, load_yaml=...) -> ContributionCollection
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

# The shared contribution-collector core (ADR-038). The manifest walk, the
# per-declaration read, the `ContributionError` type, and the `ERROR_PARSE` /
# `ERROR_MALFORMED` taxonomy live there now; this module instantiates it.
try:
    from _lib import contribution_collector as _cc
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    import contribution_collector as _cc  # type: ignore[no-redef]

# `_lib` is on sys.path when a script runs (each script inserts its scripts
# dir); the package-relative import keeps this module importable both as
# `_lib.review_contributions` and standalone via spec loading in tests.
try:
    from _lib.agents import agent_is_deployed as _default_agent_is_deployed
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from agents import agent_is_deployed as _default_agent_is_deployed  # type: ignore[no-redef]


# The declaration a contributing capability ships at its own root.
CONTRIBUTIONS_FILENAME = "review-contributions.yaml"

# Classification axes a `match` predicate may key on (per DEC-012). Both are
# `mutually_exclusive` in `classification.yaml`, so the single-value-per-axis
# read (and the resolver's per-axis multi-value guard) generalise cleanly. The
# DEC-032 amendment (2026-08-20) added `type` alongside `workstream`; this tuple
# is the single place to widen when a further mutually-exclusive axis is keyed.
SUPPORTED_MATCH_AXES = ("workstream", "type")

# The wildcard / axis-present token a `match.<axis>` value may carry (DEC-032
# amendment). A rule matching EVERY value of an axis writes `<axis>: "*"` rather
# than enumerating the fixed value set — forward-safe if a value is added later
# (enumerating would silently drop the rule for the new value). A `"*"` scalar
# parses to the `MATCH_ANY` sentinel; `"*"` inside a list is a literal value.
WILDCARD_TOKEN = "*"

# Diff-property floor kinds a rule may carry (DEC-032 amendment). A floor keys on
# the PR's *diff*, not a closing issue's classification, so it backstops D1's
# classification gate-escape for a floor-carrying reviewer. Only one kind exists
# now — `touches-code` (the diff touches non-documentation source). The tuple is
# the single place to widen; the collector validates a rule's floor against it.
FLOOR_TOUCHES_CODE = "touches-code"
SUPPORTED_FLOORS = (FLOOR_TOUCHES_CODE,)


class _MatchAny:
    """Sentinel: a wildcard axis predicate — matches ANY value present on the axis.

    A distinct singleton (not a string, not a tuple) so predicate-matching can
    tell "match every value of this axis" apart from an enumerated value tuple.
    Axis-*present* semantics: a `MATCH_ANY` axis matches a classification that
    carries some value for that axis, and matches NOTHING when the axis is absent
    (a sub-task / Milestone carrying no classification stays baseline-only per
    DEC-032 D1 — the wildcard widens across an axis's values, it does not fire on
    an entity that lacks the axis).
    """

    _instance: "_MatchAny | None" = None

    def __new__(cls) -> "_MatchAny":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "<review_contributions.MATCH_ANY>"


MATCH_ANY: _MatchAny = _MatchAny()

# A parsed `match.<axis>` predicate value: either the tuple of accepted values
# (OR within the axis) or the `MATCH_ANY` wildcard sentinel.
AxisMatch = "tuple[str, ...] | _MatchAny"

# Error kinds a consumer can branch on (structured, not string-matched). The
# two kind-agnostic classes come from the shared core (one definition); the
# undeployed-agent class is this kind's own resolution-error class.
ERROR_PARSE = _cc.ERROR_PARSE  # YAML failed to parse / read.
ERROR_MALFORMED = _cc.ERROR_MALFORMED  # declaration shape is invalid.
ERROR_UNDEPLOYED_AGENT = "undeployed-agent"  # rule names a missing agent file.

# The `ContributionError` type is the core's — re-exported so a consumer
# importing it from either module resolves the same class (isinstance-stable).
ContributionError = _cc.ContributionError

# `list_registered_capabilities` is the shared orphan-safe manifest reader —
# re-exported so its DEC-032 callers and tests keep the same import path.
list_registered_capabilities = _cc.list_registered_capabilities


@dataclass(frozen=True)
class ContributionRule:
    """One reviewer-contribution rule resolved from a capability.

    `predicate` is the classification match — a read-only mapping of axis
    name to either the tuple of accepted values (OR within an axis) or the
    `MATCH_ANY` wildcard sentinel (axis-present). A rule matches a closing
    issue when, for every axis in `predicate`, that issue's classification
    carries one of the accepted values — or, for a `MATCH_ANY` axis, carries
    any value at all (multi-axis is AND, per DEC-032). An *empty* predicate is
    NOT a classification rule: it matches no classification (see
    `reviewers_for`); a floor-only rule carries an empty predicate and its
    `floor`. `capability` records which capability contributed the rule, for
    provenance in error messages and diagnostics.

    `floor` is the optional diff-property floor kind (one of `SUPPORTED_FLOORS`,
    or `None`). A floor-carrying rule requires its reviewer whenever the PR's
    *diff* satisfies the floor — independent of classification — matched via
    `reviewers_for_floors`, not `reviewers_for`. A rule may carry a classification
    predicate, a floor, or both.

    `deployed` records whether the contributed `reviewer` resolved to a
    deployed agent file. A rule with `deployed=False` is an *unsatisfiable
    requirement* kept deliberately visible (DEC-032 D5) — a matching PR's
    gate must fail closed on it, not drop it. `resolution_error` carries
    the structured reason when `deployed` is False (else `None`).
    """

    capability: str
    predicate: Mapping[str, "tuple[str, ...] | _MatchAny"]
    reviewer: str
    floor: str | None = None
    deployed: bool = True
    resolution_error: ContributionError | None = None


@dataclass(frozen=True)
class ContributionCollection:
    """Outcome of collecting reviewer contributions across capabilities.

    `rules` is the resolution structure siblings consume: each entry pairs
    a classification match-predicate and/or a diff-property floor with a
    required reviewer (plus provenance and resolution status). The gate-checker
    filters `rules` by predicate-match against a PR's closing-issue
    classifications (`reviewers_for_issues`) AND by satisfied floor kinds
    against the PR's diff (`reviewers_for_floors`); `review-pr` invokes the
    unioned matched set. A rule whose reviewer is undeployed is present with
    `deployed=False` (see the module docstring's fail-closed seam) — it is
    NOT absent, so consumers cannot silently weaken the gate by reading
    only `rules`.

    `errors` carries structured `ContributionError`s that should surface
    rather than be silently swallowed — a malformed declaration, a parse
    error, or (DEC-032 D5) an installed contribution naming an undeployed
    agent. `ok` / `has_blocking_errors` is the single predicate a consumer
    is meant to gate on first. `capabilities_walked` records which
    manifest-registered capabilities were visited, for diagnostics.
    """

    rules: tuple[ContributionRule, ...]
    errors: tuple[ContributionError, ...] = ()
    capabilities_walked: tuple[str, ...] = ()

    @property
    def has_blocking_errors(self) -> bool:
        """True when any structured error was surfaced.

        Every `ContributionError` is blocking: a malformed declaration, a
        parse failure, and an undeployed-agent reference are all conditions
        a consumer must refuse on rather than proceed past (DEC-032 D5).
        Kept as a property so a careless consumer trips it with the minimal
        `if not collection.ok: refuse()`.
        """
        return bool(self.errors)

    @property
    def ok(self) -> bool:
        """True when collection produced no blocking errors. Inverse of
        `has_blocking_errors`; the affirmative spelling consumers gate on."""
        return not self.has_blocking_errors

    def reviewers_for(
        self, classification: Mapping[str, str]
    ) -> tuple[ContributionRule, ...]:
        """Matched rules whose predicate holds for `classification`.

        Returns the matched `ContributionRule`s (not bare names), so a
        consumer keeps each requirement's provenance (`capability`) and
        resolution status (`deployed` / `resolution_error`) — the
        gate-checker's refusal message wants "required by capability
        `ux-ui-design`" and "but its agent is undeployed".

        A rule matches when, for every axis in its predicate, the
        classification's value for that axis is one of the rule's accepted
        values (or, for a `MATCH_ANY` wildcard axis, the classification
        carries any value on that axis). A predicate keyed on an axis absent
        from `classification` matches nothing (DEC-032 D1: an entity carrying
        no such axis matches nothing → baseline only). A rule with an *empty*
        predicate (a floor-only rule) is NOT matched here — floor rules resolve
        via `reviewers_for_floors`, and an empty predicate must not vacuously
        match every classification. Deduplicated by reviewer name (first
        matching rule per reviewer wins); order follows first appearance in
        `rules` for determinism.
        """
        return self._dedup_by_reviewer(
            rule
            for rule in self.rules
            if rule.predicate and _predicate_matches(rule.predicate, classification)
        )

    def reviewers_for_floors(
        self, satisfied_floors: "Iterable[str]"
    ) -> tuple[ContributionRule, ...]:
        """Rules whose diff-property floor is in `satisfied_floors` (DEC-032 amendment).

        The diff-keyed counterpart to `reviewers_for`. `satisfied_floors` is the
        set of floor kinds the PR's *diff* satisfies (the resolver evaluates the
        diff → property mapping; this seam stays purely structural, matching a
        rule's declared `floor` against that set). A floor-carrying rule is
        required whenever its floor kind is satisfied, regardless of the closing
        issues' classification — so a diff that touches code pulls in a
        floor-carrying reviewer even for a `type:docs` / unclassified PR (D1's
        classification gate-escape, backstopped for floor-carrying reviewers).

        Deduplicated by reviewer name for determinism; matches the semantics of
        `reviewers_for` so the resolver can union the two result sets.
        """
        satisfied = set(satisfied_floors)
        return self._dedup_by_reviewer(
            rule
            for rule in self.rules
            if rule.floor is not None and rule.floor in satisfied
        )

    def reviewers_for_issues(
        self, classifications: Iterable[Mapping[str, str]]
    ) -> tuple[ContributionRule, ...]:
        """Union of matched rules across every closing issue's classification.

        This is the seam that owns DEC-032 D1's union: a PR's required
        contributed set is the union of contributions matched against the
        classification of *any* issue the PR closes. Owning it here (once)
        keeps the gate-checker (#145) and `review-pr` (#147) from each
        re-deriving the union and risking divergence on who is required.

        Each classification is matched independently (via `reviewers_for`);
        the results are unioned and deduplicated by reviewer name, first
        match across the whole iteration winning, for determinism. An empty
        iterable (a PR closing no issues) yields no contributed rules —
        baseline only, per D1.
        """
        return self._dedup_by_reviewer(
            rule
            for classification in classifications
            for rule in self.reviewers_for(classification)
        )

    @staticmethod
    def _dedup_by_reviewer(
        rules: Iterable[ContributionRule],
    ) -> tuple[ContributionRule, ...]:
        """Deduplicate rules by reviewer name, preserving first-seen order."""
        seen: set[str] = set()
        out: list[ContributionRule] = []
        for rule in rules:
            if rule.reviewer not in seen:
                seen.add(rule.reviewer)
                out.append(rule)
        return tuple(out)


def _predicate_matches(
    predicate: Mapping[str, "tuple[str, ...] | _MatchAny"],
    classification: Mapping[str, str],
) -> bool:
    """True when every axis in `predicate` holds in `classification`.

    Within an axis the accepted values are OR-ed (the classification's
    value need only be one of them); across axes the predicate is AND-ed
    (every axis must hold). A `MATCH_ANY` wildcard axis holds iff the
    classification carries any value on that axis (axis-present). An axis
    absent from `classification` fails the predicate — both for an enumerated
    tuple (its `.get` is None, in no value-tuple) and for `MATCH_ANY` (a
    missing value is not "any value present").
    """
    for axis, accepted in predicate.items():
        value = classification.get(axis)
        if accepted is MATCH_ANY:
            if value is None:
                return False
        elif value not in accepted:
            return False
    return True


def parse_contributions(
    data: Any, capability: str
) -> tuple[tuple[ContributionRule, ...], tuple[ContributionError, ...]]:
    """Validate one capability's parsed declaration into rules + errors.

    Pure and side-effect-free — takes already-parsed YAML (the caller
    reads the file). `capability` is the contributing capability's name,
    used both as rule provenance and to tag/prefix errors.

    `data` is expected to be a mapping shaped
    `{schema_version: int, contributions: [ {match: {...}, floor: str, reviewer: str}, ... ]}`.
    Each `match.<axis>` value may be a scalar string, the `"*"` wildcard
    (axis-present — matches every value of that axis), OR a list of strings
    (OR within the axis). A rule may carry a classification `match`, a
    diff-property `floor` (one of `SUPPORTED_FLOORS`), or both — but at least
    one of the two. `None` (absent/empty file) yields no rules and no errors —
    a capability that ships no declaration contributes nothing, which is not
    an error.

    Does NOT check the deployed-agent constraint — that needs filesystem
    access and lives in `collect_contributions`. This function validates
    only declaration *shape*; every error it returns is
    `ERROR_MALFORMED`.
    """
    prefix = f"capability `{capability}`: review-contributions"

    def malformed(message: str) -> ContributionError:
        return ContributionError(ERROR_MALFORMED, capability, message)

    if data is None:
        return (), ()

    if not isinstance(data, dict):
        return (), (malformed(f"{prefix} must be a mapping, got {type(data).__name__}"),)

    contributions = data.get("contributions")
    if contributions is None:
        return (), (malformed(f"{prefix} is missing the `contributions:` key"),)
    if not isinstance(contributions, list):
        return (), (
            malformed(
                f"{prefix}: `contributions` must be a list, "
                f"got {type(contributions).__name__}"
            ),
        )

    rules: list[ContributionRule] = []
    errors: list[ContributionError] = []
    for i, item in enumerate(contributions):
        rule, item_errors = _parse_rule(item, capability, i)
        if rule is not None:
            rules.append(rule)
        errors.extend(item_errors)

    return tuple(rules), tuple(errors)


def _parse_rule(
    item: Any, capability: str, index: int
) -> tuple[ContributionRule | None, list[ContributionError]]:
    """Validate one `contributions[]` entry into a rule or errors."""
    where = f"capability `{capability}`: contributions[{index}]"

    def malformed(message: str) -> ContributionError:
        return ContributionError(ERROR_MALFORMED, capability, message)

    if not isinstance(item, dict):
        return None, [malformed(f"{where} must be a mapping, got {type(item).__name__}")]

    errors: list[ContributionError] = []

    # A rule must declare a classification `match`, a diff-property `floor`, or
    # both — but at least one of the two (else it requires its reviewer never).
    match = item.get("match")
    floor = item.get("floor")
    if match is None and floor is None:
        return None, [
            malformed(f"{where} must declare a `match` predicate, a `floor`, or both")
        ]

    predicate: dict[str, tuple[str, ...] | _MatchAny] = {}
    if match is not None:
        if not isinstance(match, dict) or not match:
            errors.append(malformed(f"{where}.match must be a non-empty mapping"))
        else:
            predicate = _parse_match(match, where, errors, malformed)

    floor_kind = _parse_floor(floor, where, errors, malformed)

    reviewer = item.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer:
        errors.append(malformed(f"{where}.reviewer must be a non-empty string"))

    # A well-formed rule needs a usable requirement to key on: a non-empty
    # classification predicate OR a floor. Only emit when fully well-formed; a
    # partially broken entry surfaces its errors and contributes no silent rule.
    usable = bool(predicate) or floor_kind is not None
    if errors or not usable or not isinstance(reviewer, str) or not reviewer:
        return None, errors

    return (
        ContributionRule(
            capability=capability,
            predicate=MappingProxyType(predicate),
            reviewer=reviewer,
            floor=floor_kind,
        ),
        errors,
    )


def _parse_match(
    match: dict,
    where: str,
    errors: list[ContributionError],
    malformed: Callable[[str], ContributionError],
) -> dict[str, tuple[str, ...] | _MatchAny]:
    """Validate a rule's `match` mapping into a predicate (axis → values / MATCH_ANY)."""
    predicate: dict[str, tuple[str, ...] | _MatchAny] = {}
    for axis, raw in match.items():
        if axis not in SUPPORTED_MATCH_AXES:
            errors.append(
                malformed(
                    f"{where}.match: unsupported axis {axis!r} "
                    f"(supported: {', '.join(SUPPORTED_MATCH_AXES)})"
                )
            )
            continue
        if raw == WILDCARD_TOKEN:
            # `<axis>: "*"` — the wildcard / axis-present predicate. Matches every
            # value of the axis without enumerating the fixed set (forward-safe).
            predicate[axis] = MATCH_ANY
            continue
        values = _parse_match_values(raw, where, axis, errors, malformed)
        if values:
            predicate[axis] = values
    return predicate


def _parse_floor(
    floor: Any,
    where: str,
    errors: list[ContributionError],
    malformed: Callable[[str], ContributionError],
) -> str | None:
    """Validate a rule's optional `floor` against `SUPPORTED_FLOORS`.

    `None` (no floor declared) is valid — the rule keys on classification only.
    A non-string or unknown floor kind appends an error and yields `None`.
    """
    if floor is None:
        return None
    if not isinstance(floor, str) or floor not in SUPPORTED_FLOORS:
        errors.append(
            malformed(
                f"{where}.floor must be one of: {', '.join(SUPPORTED_FLOORS)}"
            )
        )
        return None
    return floor


def _parse_match_values(
    raw: Any,
    where: str,
    axis: str,
    errors: list[ContributionError],
    malformed: Callable[[str], ContributionError],
) -> tuple[str, ...]:
    """Normalise a `match.<axis>` value (scalar OR list) to a tuple.

    Per DEC-032 the cross-capability schema commits to scalar-or-list now
    (widening a scalar later would be a `schema_version` bump every
    contributing capability tracks). A scalar string becomes a 1-tuple; a
    list of non-empty strings becomes their tuple (deduplicated,
    order-preserving). Anything else appends an error and yields `()`,
    which the caller treats as "no usable predicate for this axis".
    """
    if isinstance(raw, str):
        raw_values: list[Any] = [raw]
    elif isinstance(raw, list):
        if not raw:
            errors.append(malformed(f"{where}.match.{axis} must be a non-empty list"))
            return ()
        raw_values = list(raw)
    else:
        errors.append(
            malformed(
                f"{where}.match.{axis} must be a non-empty string or a list of strings"
            )
        )
        return ()

    seen: set[str] = set()
    values: list[str] = []
    for value in raw_values:
        if not isinstance(value, str) or not value:
            errors.append(
                malformed(f"{where}.match.{axis} values must be non-empty strings")
            )
            return ()
        if value not in seen:
            seen.add(value)
            values.append(value)
    return tuple(values)


def collect_contributions(
    repo_root: Path,
    *,
    load_yaml: Callable[[Path], Any] = _cc.default_load_yaml,
    agent_is_deployed: Callable[[Path, str], bool] = _default_agent_is_deployed,
) -> ContributionCollection:
    """Walk manifest-registered capabilities and collect reviewer rules.

    `repo_root` is the project root (the directory holding `.pkit/`). The
    orphan-safe manifest walk + per-declaration read is the shared
    contribution-collector core (ADR-038); this function instantiates it with
    the reviewer-specific parser (`parse_contributions`) and an agent-deployed
    resolver, at the `FAIL_CLOSED` disposition DEC-032 requires:

      1. The core reads `.pkit/manifest.yaml`, lists registered capabilities
         (orphan-safe — directory presence is irrelevant), and reads each
         `review-contributions.yaml` if present, parsing + validating it.
      2. For each well-formed rule, the resolver checks the `reviewer`
         corresponds to a deployed agent file. A missing file (DEC-032 D5) does
         NOT drop the rule — the rule is kept with `deployed=False` and a
         structured `resolution_error`, AND a matching error is surfaced, so the
         requirement stays visible and the gate fails closed.

    `load_yaml` and `agent_is_deployed` are injectable so tests (and future
    harnesses) can substitute filesystem access without monkeypatching;
    `agent_is_deployed` defaults to the shared `_lib.agents` resolver that
    `pre-check.py` also uses (one deploy-path definition, per COR-007).

    Returns a `ContributionCollection`. A non-empty `errors` (equivalently
    `not collection.ok`) means a fail-and-surface condition for the caller
    (gate-checker / review-pr / pre-check); the rules — including any
    unsatisfiable ones — are still returned so a caller can report on both. The
    review declaration does not pin a `schema_version` at read time (the shape
    validator tolerates its absence), so no `expected_schema_version` is passed
    — behaviour-preserving with the pre-ADR-038 collector.
    """

    def _resolve(
        root: Path, capability: str, rule: ContributionRule
    ) -> tuple[ContributionRule, tuple[ContributionError, ...]]:
        if agent_is_deployed(root, rule.reviewer):
            return rule, ()
        # Undeployed reviewer: keep the requirement VISIBLE and unsatisfiable
        # rather than dropping it (fail-closed seam, DEC-032 D5).
        resolution_error = ContributionError(
            ERROR_UNDEPLOYED_AGENT,
            capability,
            f"capability `{capability}` contributes reviewer "
            f"`{rule.reviewer}` but no deployed agent file exists at "
            f".claude/agents/{rule.reviewer}.md — redeploy the "
            f"capability's agents or uninstall the capability.",
        )
        broken = ContributionRule(
            capability=rule.capability,
            predicate=rule.predicate,
            reviewer=rule.reviewer,
            deployed=False,
            resolution_error=resolution_error,
        )
        return broken, (resolution_error,)

    collection = _cc.collect(
        repo_root,
        filename=CONTRIBUTIONS_FILENAME,
        parse_entries=parse_contributions,
        disposition=_cc.Disposition.FAIL_CLOSED,
        resolve=_resolve,
        load_yaml=load_yaml,
    )
    return ContributionCollection(
        rules=collection.items,
        errors=collection.errors,
        capabilities_walked=collection.capabilities_walked,
    )
