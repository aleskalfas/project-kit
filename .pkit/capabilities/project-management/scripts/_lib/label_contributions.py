"""Label-contribution collector (per project-management:DEC-042).

DEC-042 lets an installed capability declare a **custom label it needs** (e.g.
ux-ui-design's `needs-design` marker on UI Features); pm **provisions it at
bootstrap** and **advises at pre-check** if it is missing. This module is the
data foundation: it walks the manifest-registered capabilities, reads each one's
`label-contributions.yaml` if present, validates it, and returns the label
requirements bootstrap creates and pre-check checks.

It is the second instantiation of the shared, orphan-safe contribution-collector
core (`_lib/contribution_collector.py`, ADR-038) — the DEC-032 reviewer collector
is the first. The manifest walk, the per-declaration read, the `schema_version`
validation, and the error taxonomy live in the core; this module supplies only
what varies for the label kind:

  * the declaration filename (`label-contributions.yaml`);
  * the per-entry parser (`{id, default_name, color, description}`);
  * NO resolution step at collect time (a label's existence is checked at
    bootstrap / pre-check against the live repo, not here);
  * the **skip-and-warn** disposition (ADR-038 rule 4 / DEC-042 Lifecycle): a
    malformed label declaration skips *that* contribution and warns — it does
    NOT fail-close pm's entire pre-check the way a dropped reviewer does. The
    stakes are lower: bootstrap re-provisions a missing label and the consuming
    capability's own predicate fail-closes without it.

The resolution seam (DEC-042 D5)
--------------------------------
`resolve_contributed_label(repo_root, id)` is the accessor a consuming
capability MUST call rather than hard-coding a label's text. It ships **inert**
in v1 — it returns the contribution's `default_name`. The v2 follow-up (an
adopter override keyed by the contribution `id`) can relocate the name behind
this same seam without touching the contributor. Introducing the seam before any
consumer exists means no consumer can bypass it and bake in a name the pm→design
binding could not later move.

Exports:

    LabelContribution              — frozen dataclass: id, default_name, color,
                                      description, capability (provenance)
    LabelContributionCollection    — the collector outcome (items + warnings +
                                      walked); skip-and-warn disposition
    ContributionError              — re-exported from the core (kind-tagged)
    ERROR_PARSE / ERROR_MALFORMED  — re-exported error kinds
    LABEL_CONTRIBUTIONS_FILENAME   — the per-capability declaration filename
    LABEL_CONTRIBUTIONS_SCHEMA_VERSION — the version this pm reads
    parse_label_contributions(data, capability) -> (items, errors)
    collect_label_contributions(repo_root, *, load_yaml=...) -> collection
    resolve_contributed_label(repo_root, id, *, ...) -> str | None
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# The shared contribution-collector core (ADR-038). Same import fallback shape as
# the reviewer collector, so this module loads both as `_lib.label_contributions`
# and standalone via spec-loading in tests.
try:
    from _lib import contribution_collector as _cc
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    import contribution_collector as _cc  # type: ignore[no-redef]


# The declaration a contributing capability ships at its own root.
LABEL_CONTRIBUTIONS_FILENAME = "label-contributions.yaml"

# The declaration `schema_version` this pm reads. A contributor pinned to a
# different version has its declaration skipped-and-warned at collect time (the
# read-time compatibility check, DEC-042 D2) — never a silent mis-read.
LABEL_CONTRIBUTIONS_SCHEMA_VERSION = 1

# Error kinds — the two kind-agnostic classes from the shared core, re-exported
# so a consumer importing them from here resolves the one definition. The label
# kind adds no resolution-error class (there is no collect-time resolution).
ERROR_PARSE = _cc.ERROR_PARSE
ERROR_MALFORMED = _cc.ERROR_MALFORMED
ContributionError = _cc.ContributionError


@dataclass(frozen=True)
class LabelContribution:
    """One label a capability declares it needs (per DEC-042 D1).

    `id` is the stable handle a consumer resolves through
    `resolve_contributed_label` — it never hard-codes `default_name`. `color` is
    a 6-hex-digit GitHub label colour (no `#`); `description` is the label's
    description text. `capability` records which capability contributed the
    label, for provenance in warnings and bootstrap/pre-check reporting.
    """

    id: str
    default_name: str
    color: str
    description: str
    capability: str


@dataclass(frozen=True)
class LabelContributionCollection:
    """Outcome of collecting label contributions across capabilities.

    A thin, kind-named view over the shared core's collection: `labels` are the
    well-formed `LabelContribution`s bootstrap creates and pre-check checks;
    `warnings` are the structured problems (malformed declaration, parse error,
    `schema_version` mismatch) surfaced rather than swallowed. Per the
    skip-and-warn disposition (DEC-042 Lifecycle) a warning does NOT block pm —
    the affected contribution is simply absent, and the consumer advises.
    `capabilities_walked` records which manifest-registered capabilities were
    visited, for diagnostics.
    """

    labels: tuple[LabelContribution, ...]
    warnings: tuple[ContributionError, ...] = ()
    capabilities_walked: tuple[str, ...] = ()

    def label_for(self, contribution_id: str) -> LabelContribution | None:
        """The collected `LabelContribution` with this `id`, or None.

        First match wins if two capabilities contribute the same `id` (a
        collision the schema cannot prevent across capabilities); order follows
        the manifest walk, so it is deterministic. `resolve_contributed_label`
        is built on this.
        """
        for label in self.labels:
            if label.id == contribution_id:
                return label
        return None


def parse_label_contributions(
    data: Any, capability: str
) -> tuple[tuple[LabelContribution, ...], tuple[ContributionError, ...]]:
    """Validate one capability's parsed declaration into labels + errors.

    Pure and side-effect-free — takes the already-parsed, `schema_version`-
    validated mapping (the core reads the file and checks the version). `data`
    is expected to be a mapping shaped
    `{schema_version: 1, labels: [ {id, default_name, color, description}, ... ]}`.

    `None` (absent / empty file) yields no labels and no errors — a capability
    that ships no declaration contributes nothing, which is not an error. Every
    error returned is `ERROR_MALFORMED`; per the skip-and-warn disposition a
    malformed entry drops itself and warns, and a sibling well-formed entry in
    the same file still contributes.
    """
    prefix = f"capability `{capability}`: label-contributions"

    def malformed(message: str) -> ContributionError:
        return ContributionError(_cc.ERROR_MALFORMED, capability, message)

    if data is None:
        return (), ()

    if not isinstance(data, dict):
        return (), (malformed(f"{prefix} must be a mapping, got {type(data).__name__}"),)

    labels = data.get("labels")
    if labels is None:
        return (), (malformed(f"{prefix} is missing the `labels:` key"),)
    if not isinstance(labels, list):
        return (), (
            malformed(
                f"{prefix}: `labels` must be a list, got {type(labels).__name__}"
            ),
        )

    out: list[LabelContribution] = []
    errors: list[ContributionError] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(labels):
        label, item_errors = _parse_label(item, capability, i)
        errors.extend(item_errors)
        if label is None:
            continue
        if label.id in seen_ids:
            errors.append(
                malformed(
                    f"{prefix}: duplicate label id {label.id!r} within the "
                    f"declaration; each id must be unique."
                )
            )
            continue
        seen_ids.add(label.id)
        out.append(label)

    return tuple(out), tuple(errors)


def _parse_label(
    item: Any, capability: str, index: int
) -> tuple[LabelContribution | None, list[ContributionError]]:
    """Validate one `labels[]` entry into a `LabelContribution` or errors."""
    where = f"capability `{capability}`: labels[{index}]"

    def malformed(message: str) -> ContributionError:
        return ContributionError(_cc.ERROR_MALFORMED, capability, message)

    if not isinstance(item, dict):
        return None, [malformed(f"{where} must be a mapping, got {type(item).__name__}")]

    errors: list[ContributionError] = []
    values: dict[str, str] = {}
    for field in ("id", "default_name", "color", "description"):
        raw = item.get(field)
        if not isinstance(raw, str) or not raw:
            errors.append(malformed(f"{where}.{field} must be a non-empty string"))
        else:
            values[field] = raw

    if errors:
        # A partially broken entry surfaces its errors and contributes no
        # (silent) label — the same all-or-nothing per-entry rule the reviewer
        # parser uses.
        return None, errors

    return (
        LabelContribution(
            id=values["id"],
            default_name=values["default_name"],
            color=values["color"],
            description=values["description"],
            capability=capability,
        ),
        errors,
    )


def collect_label_contributions(
    repo_root: Path,
    *,
    load_yaml: Callable[[Path], Any] = _cc.default_load_yaml,
) -> LabelContributionCollection:
    """Walk manifest-registered capabilities and collect label requirements.

    `repo_root` is the project root (the directory holding `.pkit/`). Delegates
    the orphan-safe manifest walk, per-declaration read, and `schema_version`
    validation to the shared core (ADR-038), instantiated at the **skip-and-warn**
    disposition (DEC-042): a malformed / version-mismatched declaration skips
    that contribution and warns; it never blocks pm.

    `load_yaml` is injectable so tests substitute filesystem access without
    monkeypatching. Returns a `LabelContributionCollection`; the well-formed
    labels are what bootstrap creates and pre-check checks, and `warnings`
    carries anything skipped.
    """
    collection = _cc.collect(
        repo_root,
        filename=LABEL_CONTRIBUTIONS_FILENAME,
        parse_entries=parse_label_contributions,
        disposition=_cc.Disposition.SKIP_AND_WARN,
        expected_schema_version=LABEL_CONTRIBUTIONS_SCHEMA_VERSION,
        schema_version_prefix="label-contributions",
        load_yaml=load_yaml,
    )
    return LabelContributionCollection(
        labels=collection.items,
        warnings=collection.warnings,
        capabilities_walked=collection.capabilities_walked,
    )


def resolve_contributed_label(
    repo_root: Path,
    contribution_id: str,
    *,
    load_yaml: Callable[[Path], Any] = _cc.default_load_yaml,
) -> str | None:
    """Resolve a contributed label's `id` to its name — the DEC-042 D5 seam.

    Ships **inert** in v1: returns the contribution's `default_name` (or None
    when no manifest-registered capability contributes a label with this `id`).
    A consuming capability calls this rather than hard-coding the label text, so
    a future adopter override (keyed by `id`) can relocate the name behind this
    seam without touching the contributor. Do NOT add the v2 override storage
    here — v1 is deliberately the identity map.
    """
    collection = collect_label_contributions(repo_root, load_yaml=load_yaml)
    label = collection.label_for(contribution_id)
    return label.default_name if label is not None else None
