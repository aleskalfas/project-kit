"""Per-contribution opt-out of a capability-contributed reviewer (DEC-032, #148).

DEC-032 D5 makes a capability's reviewer contribution active the moment the
capability is installed — installing a review-discipline capability is the
opt-in, and there is no enable toggle. Its Rationale names the case that
leaves uncovered: an adopter who wants the capability's other content but not
its merge gate, whose only cope-paths were uninstalling the capability or
`--bypass`-ing every gated PR. This module is the anticipated opt-out.

The opt-out lives in the adopter's own pm config (`project/config.yaml`, which
`pkit sync` never touches), one entry per contributed requirement:

    review:
      agents:
        contributed_opt_out:
          - capability: software-engineering
            reviewer: docs-reviewer
            reason: "Docs are reviewed by the tech-writing team."

An entry names ONE `(capability, reviewer)` pair. Every rule that capability
contributes for that reviewer — classification-matched and diff-floor alike —
leaves the resolution, so the reviewer is neither invoked by `review-pr` nor
required by `done-work`. Nothing else moves: the capability stays installed,
its other contributed reviewers still apply, the same reviewer contributed by
another capability is still required, and a reviewer the baseline
(`local_registered`) names is still required — the opt-out withdraws a
*contribution*, never the adopter's own registration. An opted-out rule's
undeployed-agent error leaves with it: a requirement that no longer applies
cannot make the gate unsatisfiable.

`reason` is required. An opt-out weakens a merge gate, so it states why; the
reason is what `pre-check` shows next to each opt-out and `review-pr` prints
when it resolves a PR's reviewers.

Validation, both fail-closed
----------------------------

  * **Shape** (`parse_opt_outs`) — a list of mappings carrying exactly
    `capability`, `reviewer` and a non-empty `reason`, no pair listed twice.
    The config schema enforces the same shape at `pkit validate`; it is
    checked again here because the pm loader does not schema-validate, and a
    gate that silently ignored a malformed entry would leave the adopter
    believing a requirement was withdrawn when it was not (or, with an extra
    key such as a scope the mechanism does not have, withdrawn more widely
    than they wrote).
  * **Against the installed contributions** (`OptOuts.problems_against`) —
    the capability must be installed and must contribute that reviewer. An
    entry naming anything else is a typo or a leftover from an uninstall, and
    is reported rather than dropped, so an intended opt-out never silently
    fails to apply.

The resolver turns either into a non-ok resolution (both consumers refuse,
naming the entry); `pre-check` reports each as a `fail`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from _lib.review_contributions import ContributionCollection, ContributionRule


# The key under `review.agents` in the adopter's pm config.
OPT_OUT_KEY = "contributed_opt_out"

# The config path every message names, so an error points at the line to fix.
OPT_OUT_PATH = f"review.agents.{OPT_OUT_KEY}"

# The keys an entry carries — all required, nothing else accepted.
_ENTRY_KEYS = ("capability", "reviewer", "reason")


@dataclass(frozen=True)
class ContributionOptOut:
    """One adopter opt-out: `capability`'s contributed `reviewer` stops gating.

    `index` is the entry's position in the configured list, kept so every
    message names the exact entry (`review.agents.contributed_opt_out[1]`).
    """

    capability: str
    reviewer: str
    reason: str
    index: int = 0

    @property
    def where(self) -> str:
        return f"{OPT_OUT_PATH}[{self.index}]"

    def covers(self, rule: ContributionRule) -> bool:
        """True when `rule` is a contribution this opt-out withdraws."""
        return rule.capability == self.capability and rule.reviewer == self.reviewer


@dataclass(frozen=True)
class OptOuts:
    """The project's configured opt-outs, or the shape errors that void them.

    `entries` holds the well-formed opt-outs; `errors` the shape problems
    found parsing the configured list. A consumer gates on `ok` first: when
    the list is malformed the adopter's intent is unknown, so nothing is
    applied and the caller refuses (see the module docstring).
    """

    entries: tuple[ContributionOptOut, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def apply(self, collection: ContributionCollection) -> ContributionCollection:
        """`collection` without the opted-out rules and their resolution errors.

        Filtering happens on the collection's rules, before any predicate is
        matched, so a reviewer that two capabilities contribute stays required
        through the capability not opted out. (Matching de-duplicates by
        reviewer name, keeping the first rule; filtering its result instead
        could drop the one rule kept for that reviewer and lose the other
        capability's requirement with it.) An opted-out rule's undeployed-agent
        error is dropped with it; every other error stays.
        """
        kept = [rule for rule in collection.rules if not self.withdraws(rule)]
        if len(kept) == len(collection.rules):
            return collection
        dropped_errors = [
            rule.resolution_error
            for rule in collection.rules
            if self.withdraws(rule) and rule.resolution_error is not None
        ]
        return replace(
            collection,
            rules=tuple(kept),
            errors=tuple(error for error in collection.errors if error not in dropped_errors),
        )

    def withdraws(self, rule: ContributionRule) -> bool:
        """True when any configured opt-out withdraws `rule`."""
        return any(entry.covers(rule) for entry in self.entries)

    def problems_against(
        self, collection: ContributionCollection
    ) -> tuple[tuple[ContributionOptOut, str], ...]:
        """Each entry naming a contribution that is not installed, with why.

        `collection` is the full collection (before `apply`). An entry is a
        problem when its capability contributes no reviewer requirement at
        all — not installed, or installed without contributions — or does not
        contribute the named reviewer. Returns `(entry, message)` pairs, in
        list order; empty when every entry names a real contribution.
        """
        contributed: dict[str, list[str]] = {}
        for rule in collection.rules:
            names = contributed.setdefault(rule.capability, [])
            if rule.reviewer not in names:
                names.append(rule.reviewer)
        installed = set(collection.capabilities_walked)
        problems: list[tuple[ContributionOptOut, str]] = []
        for entry in self.entries:
            reviewers = contributed.get(entry.capability)
            if reviewers is None:
                state = (
                    "is installed but contributes no reviewer requirement"
                    if entry.capability in installed
                    else "is not an installed capability contributing reviewer requirements"
                )
                problems.append((entry, f"{entry.where}: capability `{entry.capability}` {state}"))
            elif entry.reviewer not in reviewers:
                problems.append(
                    (
                        entry,
                        f"{entry.where}: capability `{entry.capability}` contributes "
                        f"no reviewer `{entry.reviewer}` (it contributes: "
                        f"{', '.join(sorted(reviewers))})",
                    )
                )
        return tuple(problems)


NO_OPT_OUTS = OptOuts()


def read_opt_outs(config: Any) -> OptOuts:
    """The opt-outs configured in the adopter's pm config, parsed and shape-checked.

    `config` is the whole `project/config.yaml` mapping. An absent `review`,
    `review.agents` or opt-out list is no opt-outs (the default: every
    installed contribution applies, as DEC-032 D5 ships it).
    """
    review = config.get("review") if isinstance(config, Mapping) else None
    agents = review.get("agents") if isinstance(review, Mapping) else None
    raw = agents.get(OPT_OUT_KEY) if isinstance(agents, Mapping) else None
    return parse_opt_outs(raw)


def parse_opt_outs(raw: Any) -> OptOuts:
    """Shape-check a configured opt-out list into `OptOuts`.

    `None` is no opt-outs. Anything malformed — not a list, an entry that is
    not a mapping, a missing / empty / non-string field, an unknown key, or a
    `(capability, reviewer)` pair listed twice — is reported, and then no
    entry is returned at all: a half-applied list is not what the adopter
    wrote.
    """
    if raw is None:
        return NO_OPT_OUTS
    if not isinstance(raw, list):
        return OptOuts(errors=(f"`{OPT_OUT_PATH}` must be a list, got {type(raw).__name__}",))

    entries: list[ContributionOptOut] = []
    errors: list[str] = []
    first_seen: dict[tuple[str, str], int] = {}
    for index, item in enumerate(raw):
        where = f"{OPT_OUT_PATH}[{index}]"
        if not isinstance(item, Mapping):
            errors.append(
                f"`{where}` must be a mapping with `capability`, `reviewer` and "
                f"`reason`, got {type(item).__name__}"
            )
            continue
        item_errors = _entry_errors(item, where)
        if item_errors:
            errors.extend(item_errors)
            continue
        entry = ContributionOptOut(
            capability=item["capability"].strip(),
            reviewer=item["reviewer"].strip(),
            reason=item["reason"].strip(),
            index=index,
        )
        pair = (entry.capability, entry.reviewer)
        if pair in first_seen:
            errors.append(
                f"`{where}` repeats the opt-out of `{entry.reviewer}` from "
                f"`{entry.capability}` (already `{OPT_OUT_PATH}[{first_seen[pair]}]`)"
            )
            continue
        first_seen[pair] = index
        entries.append(entry)

    if errors:
        return OptOuts(errors=tuple(errors))
    return OptOuts(entries=tuple(entries))


def _entry_errors(item: Mapping, where: str) -> list[str]:
    """Shape problems with one opt-out entry (empty when well-formed)."""
    errors = [
        f"`{where}` has unknown key `{key}` (an entry carries only "
        f"{', '.join(f'`{k}`' for k in _ENTRY_KEYS)})"
        for key in item
        if key not in _ENTRY_KEYS
    ]
    for key in _ENTRY_KEYS:
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            detail = (
                " — an opt-out withdraws a merge gate, so it states why" if key == "reason" else ""
            )
            errors.append(f"`{where}.{key}` must be a non-empty string{detail}")
    return errors
