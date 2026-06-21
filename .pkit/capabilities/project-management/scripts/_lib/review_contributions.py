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

Exports (the types #145/#146/#147 import):

    ContributionError       — frozen dataclass: kind + capability + message
    ContributionRule        — frozen dataclass: capability, predicate,
                              reviewer, deployed, resolution_error
    ContributionCollection  — frozen dataclass: rules + errors + walked,
                              with `ok` / `has_blocking_errors` /
                              `reviewers_for` / `reviewers_for_issues`
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

# `_lib` is on sys.path when a script runs (each script inserts its scripts
# dir); the package-relative import keeps this module importable both as
# `_lib.review_contributions` and standalone via spec loading in tests.
try:
    from _lib.agents import agent_is_deployed as _default_agent_is_deployed
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from agents import agent_is_deployed as _default_agent_is_deployed  # type: ignore[no-redef]

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # ruamel is in the kit's pyproject; this is defensive.
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]


# The declaration a contributing capability ships at its own root.
CONTRIBUTIONS_FILENAME = "review-contributions.yaml"

# Classification axes a `match` predicate may key on (per DEC-012). Only
# `workstream` is specified at v1 (DEC-032 D2); the set is the single
# place to widen when a second axis is added.
SUPPORTED_MATCH_AXES = ("workstream",)

# Error kinds a consumer can branch on (structured, not string-matched).
ERROR_PARSE = "parse-error"  # YAML failed to parse / read.
ERROR_MALFORMED = "malformed-declaration"  # declaration shape is invalid.
ERROR_UNDEPLOYED_AGENT = "undeployed-agent"  # rule names a missing agent file.


@dataclass(frozen=True)
class ContributionError:
    """A structured problem surfaced while collecting contributions.

    `kind` is one of the module's `ERROR_*` constants so a consumer can
    branch on the failure class (undeployed agent vs malformed declaration
    vs parse error) without string-matching `message`. `capability` is the
    contributing capability the problem came from, or `None` for a
    repo-level problem (e.g. an unparseable manifest). `message` is the
    human-readable detail for diagnostics and refusal text.
    """

    kind: str
    capability: str | None
    message: str

    def __str__(self) -> str:  # keep human-readable formatting trivial.
        return self.message


@dataclass(frozen=True)
class ContributionRule:
    """One reviewer-contribution rule resolved from a capability.

    `predicate` is the classification match — a read-only mapping of axis
    name to the tuple of accepted values (OR within an axis). A rule
    matches a closing issue when, for every axis in `predicate`, that
    issue's classification carries one of the accepted values (multi-axis
    is AND, per DEC-032). `capability` records which capability contributed
    the rule, for provenance in error messages and diagnostics.

    `deployed` records whether the contributed `reviewer` resolved to a
    deployed agent file. A rule with `deployed=False` is an *unsatisfiable
    requirement* kept deliberately visible (DEC-032 D5) — a matching PR's
    gate must fail closed on it, not drop it. `resolution_error` carries
    the structured reason when `deployed` is False (else `None`).
    """

    capability: str
    predicate: Mapping[str, tuple[str, ...]]
    reviewer: str
    deployed: bool = True
    resolution_error: ContributionError | None = None


@dataclass(frozen=True)
class ContributionCollection:
    """Outcome of collecting reviewer contributions across capabilities.

    `rules` is the resolution structure siblings consume: each entry pairs
    a match-predicate with a required reviewer (plus provenance and
    resolution status). The gate-checker filters `rules` by predicate-match
    against a PR's closing-issue classifications; `review-pr` invokes the
    matched set. A rule whose reviewer is undeployed is present with
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
        values. A predicate keyed on an axis absent from `classification`
        matches nothing (DEC-032 D1: an entity carrying no `workstream`
        axis matches nothing → baseline only). Deduplicated by reviewer
        name (first matching rule per reviewer wins); order follows first
        appearance in `rules` for determinism.
        """
        return self._dedup_by_reviewer(
            rule
            for rule in self.rules
            if _predicate_matches(rule.predicate, classification)
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
    predicate: Mapping[str, tuple[str, ...]],
    classification: Mapping[str, str],
) -> bool:
    """True when every axis in `predicate` holds in `classification`.

    Within an axis the accepted values are OR-ed (the classification's
    value need only be one of them); across axes the predicate is AND-ed
    (every axis must hold). An axis absent from `classification` fails the
    predicate (its `.get` is None, in no value-tuple).
    """
    for axis, accepted in predicate.items():
        if classification.get(axis) not in accepted:
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
    `{schema_version: int, contributions: [ {match: {...}, reviewer: str}, ... ]}`.
    Each `match.<axis>` value may be a scalar string OR a list of strings
    (OR within the axis). `None` (absent/empty file) yields no rules and no
    errors — a capability that ships no declaration contributes nothing,
    which is not an error.

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

    match = item.get("match")
    if not isinstance(match, dict) or not match:
        return None, [malformed(f"{where}.match must be a non-empty mapping")]

    predicate: dict[str, tuple[str, ...]] = {}
    errors: list[ContributionError] = []
    for axis, raw in match.items():
        if axis not in SUPPORTED_MATCH_AXES:
            errors.append(
                malformed(
                    f"{where}.match: unsupported axis {axis!r} "
                    f"(supported at v1: {', '.join(SUPPORTED_MATCH_AXES)})"
                )
            )
            continue
        values = _parse_match_values(raw, where, axis, errors, malformed)
        if values:
            predicate[axis] = values

    reviewer = item.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer:
        errors.append(malformed(f"{where}.reviewer must be a non-empty string"))

    # Only emit a rule when the entry is fully well-formed; a partially
    # broken entry surfaces its errors and contributes no (silent) rule.
    if errors or not predicate or not isinstance(reviewer, str) or not reviewer:
        return None, errors

    return (
        ContributionRule(
            capability=capability,
            predicate=MappingProxyType(predicate),
            reviewer=reviewer,
        ),
        errors,
    )


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


def list_registered_capabilities(manifest_data: Any) -> tuple[str, ...]:
    """Names of capabilities registered in a parsed backbone manifest.

    Reads `components:` and returns the `name` of every entry whose
    `kind` is `capability`, in manifest order. This is the orphan-safe
    source of truth for installed-ness (DEC-030 / DEC-032): a capability
    directory present on disk but absent from `components:` is NOT walked.

    Tolerates a missing/empty/malformed manifest by returning ().
    """
    if not isinstance(manifest_data, dict):
        return ()
    components = manifest_data.get("components")
    if not isinstance(components, list):
        return ()
    out: list[str] = []
    for entry in components:
        if not isinstance(entry, dict):
            continue
        if entry.get("kind") != "capability":
            continue
        name = entry.get("name")
        if isinstance(name, str) and name:
            out.append(name)
    return tuple(out)


def _default_load_yaml(path: Path) -> Any:
    """Read + parse a YAML file with ruamel; return None when absent.

    Raises RuntimeError on a parse error so the caller can surface a clear
    message rather than swallowing malformed input.
    """
    if not path.is_file():
        return None
    if YAML is None:  # ruamel unavailable — defensive, should not happen.
        raise RuntimeError("ruamel.yaml is not available to parse YAML")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.load(handle)
    except YAMLError as exc:
        raise RuntimeError(f"{path}: YAML parse error: {exc}") from exc


def collect_contributions(
    repo_root: Path,
    *,
    load_yaml: Callable[[Path], Any] = _default_load_yaml,
    agent_is_deployed: Callable[[Path, str], bool] = _default_agent_is_deployed,
) -> ContributionCollection:
    """Walk manifest-registered capabilities and collect reviewer rules.

    `repo_root` is the project root (the directory holding `.pkit/`). The
    walk:

      1. Reads `.pkit/manifest.yaml` and lists registered capabilities
         (orphan-safe — directory presence is irrelevant).
      2. For each, reads `.pkit/capabilities/<cap>/review-contributions.yaml`
         if present, parses + validates it.
      3. For each well-formed rule, checks the `reviewer` corresponds to a
         deployed agent file. A missing file (DEC-032 D5) does NOT drop the
         rule — the rule is kept with `deployed=False` and a structured
         `resolution_error`, AND a matching error is appended, so the
         requirement stays visible and the gate fails closed.

    `load_yaml` and `agent_is_deployed` are injectable so tests (and future
    harnesses) can substitute filesystem access without monkeypatching;
    `agent_is_deployed` defaults to the shared `_lib.agents` resolver that
    `pre-check.py` also uses (one deploy-path definition, per COR-007).

    Returns a `ContributionCollection`. A non-empty `errors` (equivalently
    `not collection.ok`) means a fail-and-surface condition for the caller
    (gate-checker / review-pr / pre-check); the rules — including any
    unsatisfiable ones — are still returned so a caller can report on both.
    """
    manifest_path = repo_root / ".pkit" / "manifest.yaml"
    try:
        manifest_data = load_yaml(manifest_path)
    except RuntimeError as exc:
        return ContributionCollection(
            rules=(),
            errors=(ContributionError(ERROR_PARSE, None, str(exc)),),
        )

    capabilities = list_registered_capabilities(manifest_data)

    rules: list[ContributionRule] = []
    errors: list[ContributionError] = []

    for capability in capabilities:
        decl_path = (
            repo_root
            / ".pkit"
            / "capabilities"
            / capability
            / CONTRIBUTIONS_FILENAME
        )
        try:
            decl_data = load_yaml(decl_path)
        except RuntimeError as exc:
            errors.append(ContributionError(ERROR_PARSE, capability, str(exc)))
            continue

        cap_rules, cap_errors = parse_contributions(decl_data, capability)
        errors.extend(cap_errors)

        for rule in cap_rules:
            if agent_is_deployed(repo_root, rule.reviewer):
                rules.append(rule)
                continue
            # Undeployed reviewer: keep the requirement VISIBLE and
            # unsatisfiable rather than dropping it (fail-closed seam).
            resolution_error = ContributionError(
                ERROR_UNDEPLOYED_AGENT,
                capability,
                f"capability `{capability}` contributes reviewer "
                f"`{rule.reviewer}` but no deployed agent file exists at "
                f".claude/agents/{rule.reviewer}.md — redeploy the "
                f"capability's agents or uninstall the capability.",
            )
            rules.append(
                ContributionRule(
                    capability=rule.capability,
                    predicate=rule.predicate,
                    reviewer=rule.reviewer,
                    deployed=False,
                    resolution_error=resolution_error,
                )
            )
            errors.append(resolution_error)

    return ContributionCollection(
        rules=tuple(rules),
        errors=tuple(errors),
        capabilities_walked=capabilities,
    )
