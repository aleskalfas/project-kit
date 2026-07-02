"""One orphan-safe contribution-collector core (per ADR-038).

The pm capability has three places where an installed capability contributes
into a pm-owned surface — settings-overlay/skill grants (DEC-030), required
reviewers (DEC-032), required labels (DEC-042). Each walks
`.pkit/manifest.yaml`'s `components:`, reads a per-capability declaration, and
handles malformed/parse errors, so each re-implements the same
**orphan-safety invariant**: a half-removed capability directory must never
inject a contribution. ADR-038 extracts that shared machinery here, once; each
contribution kind is a thin instantiation.

This module owns the parts that do NOT vary per kind:

  * **The manifest walk.** `list_registered_capabilities` reads
    `.pkit/manifest.yaml`'s `components:` — never the filesystem — so an orphan
    capability directory (botched uninstall, stash, rebase) is not walked.
  * **The per-declaration read.** For each registered capability, read its
    declaration file (`.pkit/capabilities/<cap>/<filename>`) if present; a
    parse failure becomes a structured `ContributionError` of kind
    `ERROR_PARSE`.
  * **`schema_version` validation.** When a kind declares an expected
    `schema_version`, a mismatch (or an absent/non-int version) becomes an
    `ERROR_MALFORMED` and the declaration is skipped. A kind that does not pin a
    version (`expected_schema_version=None`) skips this check.
  * **The error taxonomy.** `ERROR_PARSE` / `ERROR_MALFORMED` are the two
    kind-agnostic classes every instantiation shares; a kind may add its own
    resolution-error class (e.g. DEC-032's undeployed-agent) via its resolver.
  * **The fail-disposition policy (ADR-038 rule 4).** An instantiation declares
    `Disposition.FAIL_CLOSED` (a dropped contribution silently weakens a control
    — DEC-032's reviewer) or `Disposition.SKIP_AND_WARN` (self-healing /
    downstream fail-closed — DEC-042's label). The core records the disposition
    on the returned collection so a consumer branches on it uniformly.

What VARIES per kind, supplied by the instantiation to `collect`:

  * `filename`        — the declaration's filename at the capability root.
  * `parse_entries`   — a pure `(data, capability) -> (items, errors)` parser
                        validating the kind's per-entry schema. It is handed the
                        already-parsed, `schema_version`-validated mapping.
  * `resolve`         — an optional `(repo_root, capability, item) ->
                        (item, errors)` step (DEC-032: is the reviewer agent
                        deployed? DEC-042: none). Returns the (possibly
                        replaced) item plus any resolution errors.

The core is deliberately kept in pm's `_lib/` rather than the backbone: every
consumer today is a pm surface (ADR-038 rule 1). DEC-030's overlay/skill walker
is a later refactor target — it reads more than the shared shape — and is NOT
swallowed here (ADR-038 rule "why not swallow DEC-030's walker").
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # ruamel is in the kit's pyproject; this is defensive.
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]


# The two kind-agnostic error classes every instantiation shares. A kind may
# introduce its own resolution-error kind (e.g. DEC-032's undeployed-agent)
# through its resolver; those flow through the same `ContributionError` type.
ERROR_PARSE = "parse-error"  # YAML failed to parse / read.
ERROR_MALFORMED = "malformed-declaration"  # declaration shape / schema_version invalid.


class Disposition(enum.Enum):
    """How an instantiation treats a malformed / dropped contribution.

    The ADR-038 rule-4 discriminator, fixed here so a fourth kind cites it
    rather than re-deriving it: *does dropping this contribution fail open on a
    control, or degrade to a benign, downstream-caught state?*

    * ``FAIL_CLOSED`` — a dropped contribution silently weakens a control the
      contribution exists to enforce (a required reviewer, DEC-032). Every error
      is blocking; the consumer must refuse.
    * ``SKIP_AND_WARN`` — a dropped contribution is self-healing or
      independently fail-closed downstream (a required label, DEC-042: bootstrap
      re-provisions it and the consumer's own predicate refuses without it). An
      error skips that one contribution and warns; it does not block the surface.
    """

    FAIL_CLOSED = "fail-closed"
    SKIP_AND_WARN = "skip-and-warn"


@dataclass(frozen=True)
class ContributionError:
    """A structured problem surfaced while collecting contributions.

    `kind` is one of the module's (or an instantiation's) `ERROR_*` constants so
    a consumer branches on the failure class without string-matching `message`.
    `capability` is the contributing capability the problem came from, or `None`
    for a repo-level problem (an unparseable manifest). `message` is the
    human-readable detail for diagnostics and refusal/warning text.
    """

    kind: str
    capability: str | None
    message: str

    def __str__(self) -> str:  # keep human-readable formatting trivial.
        return self.message


TItem = TypeVar("TItem")


@dataclass(frozen=True)
class ContributionCollection(Generic[TItem]):
    """Outcome of collecting one kind of contribution across capabilities.

    `items` are the well-formed (and, if the kind resolves, resolved)
    contributions — the kind's own entry type (a reviewer rule, a label
    requirement). `errors` are the structured problems surfaced rather than
    swallowed. `capabilities_walked` records which manifest-registered
    capabilities were visited, for diagnostics. `disposition` is the kind's
    ADR-038 rule-4 posture, carried so a consumer branches uniformly on
    "block vs warn".

    `ok` / `has_blocking_errors` is the single predicate a consumer gates on
    first. Under `FAIL_CLOSED` every error is blocking; under `SKIP_AND_WARN`
    no error blocks (the errors are advisory warnings a consumer surfaces but
    does not refuse on).
    """

    items: tuple[TItem, ...]
    errors: tuple[ContributionError, ...] = ()
    capabilities_walked: tuple[str, ...] = ()
    disposition: Disposition = Disposition.FAIL_CLOSED

    @property
    def has_blocking_errors(self) -> bool:
        """True when a surfaced error should make a consumer refuse.

        Blocking iff the kind's disposition is `FAIL_CLOSED` and at least one
        error was surfaced. Under `SKIP_AND_WARN` the errors are warnings, not
        blockers, so this is False even when `errors` is non-empty — the
        consumer reads `warnings` (≡ `errors`) and advises.
        """
        return self.disposition is Disposition.FAIL_CLOSED and bool(self.errors)

    @property
    def ok(self) -> bool:
        """True when collection produced no *blocking* errors. The affirmative
        spelling a consumer gates on (`if not collection.ok: refuse()`)."""
        return not self.has_blocking_errors

    @property
    def warnings(self) -> tuple[ContributionError, ...]:
        """The surfaced errors as warnings — the `SKIP_AND_WARN` read channel.

        Alias of `errors`, spelled for the disposition whose consumer *advises*
        rather than refuses (a missing/malformed label, DEC-042). Kept as a
        distinct name so a `SKIP_AND_WARN` consumer's intent reads clearly at the
        call site (it iterates `warnings`, not `errors`)."""
        return self.errors


def list_registered_capabilities(manifest_data: Any) -> tuple[str, ...]:
    """Names of capabilities registered in a parsed backbone manifest.

    Reads `components:` and returns the `name` of every entry whose `kind` is
    `capability`, in manifest order. This is the orphan-safe source of truth for
    installed-ness (DEC-030 / DEC-032 / DEC-042): a capability directory present
    on disk but absent from `components:` is NOT walked.

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


def default_load_yaml(path: Path) -> Any:
    """Read + parse a YAML file with ruamel; return None when absent.

    Raises RuntimeError on a parse error so the caller can surface a clear
    `ERROR_PARSE` rather than swallowing malformed input.
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


def validate_schema_version(
    data: Any, capability: str, expected: int, prefix: str
) -> ContributionError | None:
    """Validate a declaration's top-level `schema_version`, per ADR-038 rule 2.

    Returns an `ERROR_MALFORMED` when `data` is a mapping whose `schema_version`
    is absent, non-integer, or not `expected`; else None. `data` that is not a
    mapping is left to the kind's own parser to reject (it produces a clearer
    shape message), so this returns None for it. `prefix` is the kind-scoped
    provenance the message leads with (e.g. "label-contributions").
    """
    if not isinstance(data, dict):
        return None
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        return ContributionError(
            ERROR_MALFORMED,
            capability,
            f"capability `{capability}`: {prefix} declaration is missing a "
            f"valid integer `schema_version` (expected {expected}).",
        )
    if version != expected:
        return ContributionError(
            ERROR_MALFORMED,
            capability,
            f"capability `{capability}`: {prefix} declaration `schema_version` "
            f"is {version}; this pm reads version {expected}. The declaration is "
            f"skipped until the contributor's schema matches (per ADR-038).",
        )
    return None


def collect(
    repo_root: Path,
    *,
    filename: str,
    parse_entries: Callable[
        [Any, str], tuple[tuple[TItem, ...], tuple[ContributionError, ...]]
    ],
    disposition: Disposition,
    expected_schema_version: int | None = None,
    schema_version_prefix: str = "contribution",
    resolve: Callable[
        [Path, str, TItem], tuple[TItem, tuple[ContributionError, ...]]
    ]
    | None = None,
    load_yaml: Callable[[Path], Any] = default_load_yaml,
) -> ContributionCollection[TItem]:
    """Walk manifest-registered capabilities and collect one kind's contributions.

    The orphan-safe shared shape (ADR-038 rule 2), realised once here:

      1. Read `.pkit/manifest.yaml` and list registered capabilities
         (orphan-safe — directory presence is irrelevant).
      2. For each, read `.pkit/capabilities/<cap>/<filename>` if present; a
         parse failure becomes an `ERROR_PARSE` and the capability is skipped.
      3. When `expected_schema_version` is set, validate the declaration's
         top-level `schema_version`; a mismatch becomes an `ERROR_MALFORMED` and
         the declaration is skipped (the whole capability's contributions drop —
         its schema is incompatible with what this pm reads).
      4. Hand the parsed mapping to `parse_entries` (the kind's shape validator);
         collect its items + malformed errors.
      5. For each well-formed item, run `resolve` if the kind supplies one
         (DEC-032: agent-deployed check). The resolver returns the (possibly
         replaced) item plus any resolution errors.

    `load_yaml` is injectable so tests substitute filesystem access without
    monkeypatching. The `disposition` is recorded on the returned collection so
    a consumer branches uniformly on block-vs-warn.

    Returns a `ContributionCollection`. Under `FAIL_CLOSED` a non-empty `errors`
    means the consumer must refuse; under `SKIP_AND_WARN` the errors are
    warnings and the well-formed items are still returned.
    """
    manifest_path = repo_root / ".pkit" / "manifest.yaml"
    try:
        manifest_data = load_yaml(manifest_path)
    except RuntimeError as exc:
        return ContributionCollection(
            items=(),
            errors=(ContributionError(ERROR_PARSE, None, str(exc)),),
            disposition=disposition,
        )

    capabilities = list_registered_capabilities(manifest_data)

    items: list[TItem] = []
    errors: list[ContributionError] = []

    for capability in capabilities:
        decl_path = (
            repo_root / ".pkit" / "capabilities" / capability / filename
        )
        try:
            decl_data = load_yaml(decl_path)
        except RuntimeError as exc:
            errors.append(ContributionError(ERROR_PARSE, capability, str(exc)))
            continue

        # An absent declaration contributes nothing — not an error. Skip the
        # schema_version check for it too (there is no version to validate).
        if decl_data is not None and expected_schema_version is not None:
            version_error = validate_schema_version(
                decl_data,
                capability,
                expected_schema_version,
                schema_version_prefix,
            )
            if version_error is not None:
                errors.append(version_error)
                continue

        cap_items, cap_errors = parse_entries(decl_data, capability)
        errors.extend(cap_errors)

        for item in cap_items:
            if resolve is None:
                items.append(item)
                continue
            resolved_item, resolve_errors = resolve(repo_root, capability, item)
            items.append(resolved_item)
            errors.extend(resolve_errors)

    return ContributionCollection(
        items=tuple(items),
        errors=tuple(errors),
        capabilities_walked=capabilities,
        disposition=disposition,
    )
