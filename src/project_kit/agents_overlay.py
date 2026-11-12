"""Agent overlay diagnostics + reconcile + adopt (per COR-013).

The `pkit agents` surface: a read-only diagnostic of which kit-shipped agents
will deploy vs. be skipped. An agent is skipped only when it references an
overlay *category* the adopter's `.pkit/agents/project/overlay.yaml` does not
define through a *hard* channel (any list key or `reads.paths` /
`reads.records`); a category referenced *only* via `reads.patterns` is an
**optional read** (ADR-052) whose absence never skips — the agent deploys
without it and the undefined optional categories surface in their own
`Optional` footer state. Plus an explicit `reconcile` that surfaces the
missing categories into the overlay as
commented stubs or (when the conventional default directory exists) as
uncommented, deploy-ready entries, and an explicit `adopt` that creates the
conventional directories, wires the overlay uncommented, and deploys the agent
in one step.

This is a *backbone* read of *backbone-defined* artifacts: the agent
frontmatter format and the `<category>` placeholder convention are fixed by
COR-013 and shared across adapters. Only the *substitution + write* of a
resolved agent into a harness location is adapter-specific (the claude-code
adapter's `deploy-agents.sh` / `_resolve_agent.py`). Which definition of a name
is the agent, it asks the picker the deploy asks (`agent_definitions`, ADR-087).
It reproduces the adapter's *reference-detection* (which frontmatter keys may
carry placeholders), pinned to the adapter by a guard test
(`tests/test_agents_overlay.py`). It never writes a resolved agent; deployment
stays the adapter's job.

It also owns the backbone's single *value*-resolution helper
(:func:`load_overlay_values` + :func:`expand_placeholders`) — the same
override-then-default-then-undefined rules the adapter resolver applies, exposed
so every backbone consumer (the reference-graph's exactly-one-owner check, per
COR-013 rule 5) resolves placeholders one way instead of re-deriving them. A
parity test pins it to the adapter resolver's actual behaviour.

The overlay's per-agent block carries one more thing than categories: the
agent's model and effort (#1047). :func:`load_overlay_values` sets those keys
apart, and ``pkit agents`` reports each agent's effective setting, resolved by
:mod:`project_kit.agent_policy`.

The deploy ignores an override for an agent no source ships, and one naming a
category the agent's definition does not reference. :func:`unknown_overrides`
finds each from the same resolution, and ``pkit agents`` and the reference
graph's validation warn of it (#2468), as of a dotted category no installed
capability declares (:func:`undeclared_capability_categories`).

A capability's write categories (COR-073, ADR-088) are filled here too: the fill
commands, `reconcile --write` and `adopt`, write the default a capability's
query answers where the project set no value, and `reconcile` alone moves a
value still as written to a newer answer. :func:`plan_defaults` decides each
category's outcome for every writer, the capability's install among them, and
the status report shows a written value its query now answers otherwise
(:func:`written_defaults_drift`). The written line and the query live in
:mod:`project_kit.write_categories`.
"""

from __future__ import annotations

import io
import re
import shlex
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import click
from ruamel.yaml import YAML

from project_kit import (
    agent_definitions,
    agent_policy,
    cli_render,
    docs_roots,
    lifecycle_ownership,
    project_config,
)
from project_kit import write_categories as wcat

# Conventional default paths for well-known overlay categories, relative to
# the project root, **under the default documentation root** — the fallback
# literals (`docs/architecture`, `docs/architecture/decisions`). Per COR-049
# point 4 a category that locates a folder of documents derives from the
# project's *internal root* plus its conventional sub-path; the sub-paths are
# the one list the backbone owns, `docs_roots.CONVENTIONAL_SUBPATHS`. Register
# a new category's default there. reconcile / adopt resolve the defaults at
# run time through :func:`conventional_category_defaults`, so a project that
# declared another internal root gets its own locations; with the default root
# they equal this map exactly, so nothing changes for existing adopters.
#
# A category with no sub-path has no conventional default → always a commented
# stub.
CONVENTIONAL_CATEGORY_DEFAULTS: dict[str, str] = docs_roots.default_conventional_locations()


def conventional_category_defaults(target_root: Path) -> dict[str, str]:
    """The conventional default directory per category, derived from the
    project's internal documentation root (COR-049 point 4)."""
    return docs_roots.conventional_locations(target_root)


def write_carrying_categories(target_root: Path) -> frozenset[str]:
    """Overlay categories that carry write authority and ship as `[]` (ADR-051).

    Read from the tree's `.pkit/lifecycle/ownership.py`, through the backbone's
    one loader of it (`lifecycle_ownership`), so the set is declared once. An
    unreachable module — a tree that has not synced since the lifecycle area
    started carrying it — yields the empty set, which makes every category take
    the conventional-default path, the behaviour that predates the category.
    The deploy resolver, whose check is the load-bearing one, fails loudly
    instead.
    """
    mod = lifecycle_ownership.load_ownership(target_root)
    if mod is None:
        return frozenset()
    return frozenset(mod.WRITE_CARRYING_CATEGORIES)


# The frontmatter keys whose list items may hold `<category>` placeholders,
# mirrored from the claude-code adapter's `_resolve_agent.py`. A guard test
# extracts the adapter's like-named tuples and asserts equality, so a backbone
# scan can never silently drift from what the deployer actually resolves — nor
# on which channel is *hard* vs. *optional* (ADR-052).
#
# The reads channel is split: `reads.paths` / `reads.records` are hard (an
# undefined placeholder skips the agent), `reads.patterns` is the optional read
# channel (an undefined placeholder is dropped and the agent still deploys — the
# empty-is-normal corpus read of ADR-013 D1 / ADR-052). `RESOLVABLE_READS_KEYS`
# stays the union, so *reference detection* is unchanged: a `<project-conventions>`
# placeholder under `reads.patterns` is still detected as a referenced category.
RESOLVABLE_LIST_KEYS: tuple[str, ...] = ("owns", "needs", "answers")
HARD_READS_KEYS: tuple[str, ...] = ("paths", "records")
OPTIONAL_READS_KEYS: tuple[str, ...] = ("patterns",)
RESOLVABLE_READS_KEYS: tuple[str, ...] = HARD_READS_KEYS + OPTIONAL_READS_KEYS

_FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
_yaml = YAML(typ="safe")


@dataclass(frozen=True)
class AgentOverlayStatus:
    """Resolution readiness of one kit-shipped agent against the overlay."""

    name: str
    namespace: str  # "core" | "project" | "capability:<cap>"
    source: Path
    referenced: tuple[str, ...]  # overlay categories the agent references
    missing: tuple[str, ...]  # referenced but undefined (overrides considered)
    optional: tuple[str, ...]  # of `referenced`, those this agent reads optionally
    # Effective model and effort, in `agent_policy.POLICY_KEYS` order (#1047).
    policy: tuple[agent_policy.Setting, ...] = ()

    @property
    def deployable(self) -> bool:
        # An undefined *optional* read (a patterns-only category, ADR-052) does
        # not block: it drops at deploy and the agent ships as a generalist.
        # Only an undefined *hard* category skips the agent.
        return not (set(self.missing) - set(self.optional))


# --- discovery (the picker's answer, ADR-087) ----------------------------------


def discover_kit_agents(target_root: Path) -> dict[str, tuple[str, Path]]:
    """Return ``{name: (place, file)}`` for each name whose agent has one text.

    Which definition of a name is the agent is the picker's to say
    (`agent_definitions`, ADR-087): the place is ``project``, ``core`` or
    ``capability:<name>``, as the picker writes it. A name whose agent is
    refused for holding both layouts, one with no agent, and one the picker
    cannot tell are left out, and the validator reports each. Raises
    `agent_definitions.Unreachable` where the picker cannot be reached.
    """
    return agent_definitions.agents(agent_definitions.answer(target_root))


# --- reference-detection (mirrors _resolve_agent.py) -------------------------


def placeholder_category(item: object) -> str | None:
    """The category name of a `<category>` list item, or None for a literal entry."""
    if isinstance(item, str) and item.startswith("<") and item.endswith(">"):
        return item[1:-1]
    return None


def _placeholders(items: object) -> set[str]:
    out: set[str] = set()
    if isinstance(items, list):
        for item in items:
            cat = placeholder_category(item)
            if cat is not None:
                out.add(cat)
    return out


def agent_front_matter(source: Path) -> dict[str, Any]:
    """An agent file's parsed front matter; empty when it has none or it is not a mapping."""
    m = _FRONTMATTER_RE.match(source.read_text(encoding="utf-8"))
    if not m:
        return {}
    fm = _yaml.load(io.StringIO(m.group(1))) or {}
    return fm if isinstance(fm, dict) else {}


def agent_referenced_categories(source: Path) -> set[str]:
    """Categories an agent references — `<cat>` items under the resolvable keys."""
    fm = agent_front_matter(source)
    cats: set[str] = set()
    for key in RESOLVABLE_LIST_KEYS:
        cats |= _placeholders(fm.get(key))
    reads = fm.get("reads")
    if isinstance(reads, dict):
        for k in RESOLVABLE_READS_KEYS:
            cats |= _placeholders(reads.get(k))
    return cats


def agent_category_roles(source: Path) -> tuple[set[str], set[str]]:
    """Split an agent's referenced categories into ``(hard, optional)``.

    Mirrors the adapter resolver's channel split (ADR-052): a category is
    *optional for this agent* iff it appears as a `<cat>` placeholder under
    ``reads.patterns`` and under *none* of its hard keys (``owns`` / ``needs`` /
    ``answers`` / ``reads.paths`` / ``reads.records``). A category referenced
    both optionally and hard is *hard* — the hard reference wins (Decision 2).

    ``hard`` and ``optional`` are disjoint and together equal
    :func:`agent_referenced_categories`.
    """
    fm = agent_front_matter(source)
    hard: set[str] = set()
    for key in RESOLVABLE_LIST_KEYS:
        hard |= _placeholders(fm.get(key))
    reads = fm.get("reads")
    patterns: set[str] = set()
    if isinstance(reads, dict):
        for k in HARD_READS_KEYS:
            hard |= _placeholders(reads.get(k))
        for k in OPTIONAL_READS_KEYS:
            patterns |= _placeholders(reads.get(k))
    optional = patterns - hard
    return hard, optional


# --- overlay ----------------------------------------------------------------

# The adopter overlay, relative to the project root.
OVERLAY_PATH = Path(".pkit") / "agents" / "project" / "overlay.yaml"


# What a command that needs a missing overlay names: the one command that creates it
# outside the lifecycle (ADR-065 point 11). `pkit init` refuses a project that has one.
_OVERLAY_REPAIR = "run `pkit agents reconcile --write`, which creates it from the seed."


def _overlay_path(target_root: Path) -> Path:
    return target_root / OVERLAY_PATH


@dataclass(frozen=True)
class OverlayValues:
    """The overlay's category *values*: top-level defaults + per-agent overrides.

    Mirrors what the adapter resolver reads: every top-level key except the
    reserved ``overrides`` is a default category; ``overrides.<agent>`` holds
    per-agent categories that *replace* (never merge with) the default. The
    policy keys of that block (``model``, ``effort`` — #1047) are not
    categories: they sit apart in ``policy``, keyed by agent the same way.
    """

    defaults: dict[str, Any]
    overrides: dict[str, dict[str, Any]]
    policy: dict[str, dict[str, Any]] = field(default_factory=dict)

    def resolve(self, agent_name: str, category: str) -> Any | None:
        """The value a category resolves to for one agent, or None if undefined.

        Precedence mirrors ``_resolve_agent.py``: the agent's own override wins,
        then the top-level default. ``None`` means *undefined* — which covers
        both an absent key and a bare key (``category:`` with no value), exactly
        as the adapter treats them (a hard reference skips the agent at deploy;
        an optional one is dropped, with a warning when the key is bare).
        """
        agent_overrides = self.overrides.get(agent_name) or {}
        if category in agent_overrides:
            return agent_overrides[category]
        if category in self.defaults:
            return self.defaults[category]
        return None


@dataclass(frozen=True)
class ResolvedEntry:
    """One resolved item of a placeholder-bearing frontmatter list.

    ``category`` records the overlay category the value came from, so a
    consumer can report *why* a path is in the list; None for a literal entry
    that needed no resolution.
    """

    value: str
    category: str | None


def load_overlay_values(target_root: Path) -> OverlayValues:
    """Read the adopter overlay's category values (defaults + per-agent overrides)."""
    path = _overlay_path(target_root)
    if not path.is_file() or path.stat().st_size == 0:
        return OverlayValues(defaults={}, overrides={})
    return overlay_values_of(_yaml.load(path.read_text(encoding="utf-8")) or {})


def overlay_values_of(data: object) -> OverlayValues:
    """The category values of a parsed overlay, as `load_overlay_values` reads them."""
    if not isinstance(data, dict):
        return OverlayValues(defaults={}, overrides={})
    data = cast("dict[Any, Any]", data)
    overrides_raw = data.get("overrides") or {}
    overrides: dict[str, dict[str, Any]] = {}
    policy: dict[str, dict[str, Any]] = {}
    if isinstance(overrides_raw, dict):
        for agent, block in overrides_raw.items():
            if isinstance(block, dict):
                overrides[str(agent)] = {
                    str(k): v for k, v in block.items() if k not in agent_policy.POLICY_KEYS
                }
                policy[str(agent)] = {
                    str(k): v for k, v in block.items() if k in agent_policy.POLICY_KEYS
                }
    defaults = {str(k): v for k, v in data.items() if k != "overrides"}
    return OverlayValues(defaults=defaults, overrides=overrides, policy=policy)


def expand_placeholders(
    items: Iterable[object],
    *,
    agent_name: str,
    overlay: OverlayValues,
) -> tuple[list[ResolvedEntry], list[str]]:
    """Substitute `<category>` items from the overlay; pass literals through.

    The backbone twin of the adapter resolver's ``expand_list``: a list value
    extends the output, a scalar contributes one entry, a literal (non-placeholder)
    item is kept as-is. Where the adapter *exits* on an undefined category
    referenced through a *hard* channel (which makes the deploy skip the agent,
    loudly — a patterns-only optional read is dropped instead, per ADR-052), this
    returns the undefined category names alongside the entries it could resolve —
    the caller decides what an unresolvable category means for it.

    Returns ``(entries, undefined_categories)``.
    """
    entries: list[ResolvedEntry] = []
    undefined: list[str] = []
    for item in items:
        category = placeholder_category(item)
        if category is None:
            entries.append(ResolvedEntry(value=str(item), category=None))
            continue
        resolved = overlay.resolve(agent_name, category)
        if resolved is None:
            undefined.append(category)
            continue
        values = resolved if isinstance(resolved, list) else [resolved]
        for value in values:
            if value is None:
                continue
            entries.append(ResolvedEntry(value=str(value), category=category))
    return entries, undefined


# --- status + reconcile ------------------------------------------------------


def agent_overlay_statuses(target_root: Path) -> list[AgentOverlayStatus]:
    values = load_overlay_values(target_root)
    defaults = set(values.defaults)
    out: list[AgentOverlayStatus] = []
    for name, (ns, src) in sorted(discover_kit_agents(target_root).items()):
        referenced = agent_referenced_categories(src)
        _hard, optional = agent_category_roles(src)
        defined = defaults | set(values.overrides.get(name, {}))
        missing = referenced - defined
        out.append(
            AgentOverlayStatus(
                name=name,
                namespace=ns,
                source=src,
                referenced=tuple(sorted(referenced)),
                missing=tuple(sorted(missing)),
                optional=tuple(sorted(optional)),
                policy=agent_policy.effective_policy(
                    agent_front_matter(src), values.policy.get(name, {})
                ),
            )
        )
    return out


@dataclass(frozen=True)
class UnknownOverride:
    """An entry under the overlay's ``overrides:`` that the deploy ignores (#2468).

    Either the block names an agent no source ships (``category`` is None), or it
    names a category the agent's definition does not reference, ``source`` being
    the definition that deploys under that name.
    """

    agent: str
    category: str | None = None
    source: str | None = None  # the deploying definition, relative to the project root

    @property
    def key(self) -> str:
        """The overlay key, ``overrides.<agent>`` or ``overrides.<agent>.<category>``."""
        if self.category is None:
            return f"overrides.{self.agent}"
        return f"overrides.{self.agent}.{self.category}"

    @property
    def reason(self) -> str:
        """Why the deploy ignores it."""
        if self.category is None:
            return f"no source ships an agent named {self.agent}"
        return f"{self.agent}'s definition, {self.source}, names no category <{self.category}>"


def unknown_overrides(target_root: Path) -> list[UnknownOverride]:
    """Each entry under ``overrides:`` that resolves nothing, sorted by key (#2468).

    Read from the same resolution the deploy applies: the overlay as
    :func:`load_overlay_values` reads it, and the picker's answer of which
    definition is the agent of each name (ADR-087). A block for an agent no source
    ships is one finding, whatever keys it holds, ``model`` and ``effort`` among
    them. In the block of an agent with one text, each category key its definition
    does not reference is one. The policy keys are no categories, so they are never
    one of those. A name some place ships whose agent has no one text is left to
    the validator's own finding.
    """
    values = load_overlay_values(target_root)
    picked = agent_definitions.answer(target_root)
    agents = agent_definitions.agents(picked)
    found: list[UnknownOverride] = []
    for agent in sorted(set(values.overrides) | set(values.policy)):
        if agent not in picked.picks:
            found.append(UnknownOverride(agent=agent))
            continue
        if agent not in agents:
            continue
        _ns, src = agents[agent]
        referenced = agent_referenced_categories(src)
        source = src.relative_to(target_root).as_posix()
        for category in sorted(set(values.overrides.get(agent, {})) - referenced):
            found.append(UnknownOverride(agent=agent, category=category, source=source))
    return found


@dataclass(frozen=True)
class UndeclaredCategory:
    """A dotted category of the overlay that no installed capability declares
    (ADR-088 point 1), such as one an uninstall left behind."""

    key: str  # the overlay key: `<category>` or `overrides.<agent>.<category>`
    category: str


def undeclared_capability_categories(target_root: Path) -> list[UndeclaredCategory]:
    """Each dotted category of the overlay, at the top level or in an override,
    that no installed capability declares. A dotted name is a capability's alone
    (COR-073 point 1), so nothing deploys from it until a capability declares it
    again. Warned of where an unknown override is, failing nothing."""
    declared = {category.name for category in wcat.installed(target_root)}
    values = load_overlay_values(target_root)
    found = [
        UndeclaredCategory(key=category, category=category)
        for category in sorted(values.defaults)
        if wcat.SEPARATOR in category and category not in declared
    ]
    for agent in sorted(values.overrides):
        found += [
            UndeclaredCategory(key=f"overrides.{agent}.{category}", category=category)
            for category in sorted(values.overrides[agent])
            if wcat.SEPARATOR in category and category not in declared
        ]
    return found


# --- a capability's defaults (COR-073, ADR-088 points 3 to 6) ----------------
#
# A writer of a default plans each write category against the overlay as it
# stands, with the writes it planned before (`plan_defaults`), then makes the
# writes and moves it chose (`apply_defaults`). Install, `reconcile`, `adopt` and
# the status report share the plan; each decides which of its writes to make.

#: A category the writer may write, and its answer, which passes.
WRITE = "write"
#: A line still as written, whose query now answers otherwise, and passes.
MOVE = "move"
#: A line still as written, whose query answers its value.
CURRENT = "current"
#: A line still as written, which this writer does not move.
WRITTEN = "written"
#: A value the project set, which no writer writes.
KEPT = "kept"
#: An answer one of whose paths the writer's check refuses.
REFUSED = "refused"
#: A query that gave no answer.
NO_ANSWER = "no-answer"


@dataclass(frozen=True)
class DefaultOutcome:
    """What a writer found for one write category."""

    category: wcat.WriteCategory
    kind: str
    paths: tuple[str, ...] = ()  # the answer, for a write, move, current or refused answer
    written: tuple[str, ...] = ()  # the value still as written, where there is one
    reason: str = ""  # why the answer was refused, or the query gave none
    note: str = ""  # the note the query gave
    over_content: tuple[str, ...] = ()  # the paths of a write or move that hold content

    @property
    def changes(self) -> bool:
        """Whether the outcome writes a line: a write or a move."""
        return self.kind in (WRITE, MOVE)


def plan_defaults(
    target_root: Path,
    categories: Iterable[wcat.WriteCategory],
    document: wcat.OverlayDocument,
    *,
    moves: bool,
) -> list[DefaultOutcome]:
    """Each category's outcome, in order, against *document* and the writes planned
    before it. *moves* asks the query of a line still as written too, as only
    `reconcile` and the status report do (ADR-088 point 6). *document* is left as
    it was. Raises `wcat.OverlayDoesNotRead` where the overlay does not parse."""
    ownership = lifecycle_ownership.load_ownership(target_root)
    scratch = wcat.OverlayDocument(document.text)
    scratch.data()
    outcomes: list[DefaultOutcome] = []
    for category in categories:
        found = scratch.still_as_written(category.name)
        written = tuple(found) if found is not None else ()
        if found is None and scratch.gives_value(category.name, category.owner):
            outcomes.append(DefaultOutcome(category, KEPT))
            continue
        if found is not None and not moves:
            outcomes.append(DefaultOutcome(category, WRITTEN, written=written))
            continue
        answer = wcat.ask(target_root, category)
        if isinstance(answer, wcat.NoAnswer):
            outcomes.append(
                DefaultOutcome(category, NO_ANSWER, written=written, reason=answer.reason)
            )
            continue
        if found is not None and list(answer.paths) == found:
            outcomes.append(
                DefaultOutcome(category, CURRENT, answer.paths, written, note=answer.note)
            )
            continue
        others = _other_grants(target_root, scratch, category)
        reason = wcat.refusal(target_root, category, answer.paths, others, ownership)
        if reason is None:
            try:
                if found is None:
                    scratch.write(category.name, answer.paths)
                else:
                    scratch.move(category.name, answer.paths)
            except wcat.OverlayDoesNotRead as exc:
                reason = str(exc)
        if reason is not None:
            outcomes.append(
                DefaultOutcome(category, REFUSED, answer.paths, written, reason, answer.note)
            )
            continue
        outcomes.append(
            DefaultOutcome(
                category,
                WRITE if found is None else MOVE,
                answer.paths,
                written,
                note=answer.note,
                over_content=tuple(p for p in answer.paths if wcat.holds_content(target_root, p)),
            )
        )
    return outcomes


def apply_defaults(document: wcat.OverlayDocument, outcomes: Iterable[DefaultOutcome]) -> None:
    """Make the write or move of each outcome in *document*, in order."""
    for outcome in outcomes:
        if outcome.kind == WRITE:
            document.write(outcome.category.name, outcome.paths)
        elif outcome.kind == MOVE:
            document.move(outcome.category.name, outcome.paths)


def _other_grants(
    target_root: Path, document: wcat.OverlayDocument, category: wcat.WriteCategory
) -> list[tuple[str, str]]:
    """Each `(agent, normalised path)` an agent other than *category*'s owner owns,
    resolved from *document*: the overlay as it stands, with the writes made
    earlier in the run. The category's own value leaves the comparison, since
    the write replaces it."""
    values = overlay_values_of(document.data())
    found: list[tuple[str, str]] = []
    for name, (_ns, source) in sorted(discover_kit_agents(target_root).items()):
        if name == category.owner:
            continue
        owns = agent_front_matter(source).get("owns")
        if not isinstance(owns, list):
            continue
        entries, _undefined = expand_placeholders(
            cast("list[object]", owns), agent_name=name, overlay=values
        )
        for entry in entries:
            path = wcat.normalised(entry.value)
            if entry.category != category.name and path:
                found.append((name, path))
    return found


def listed(paths: Iterable[str]) -> str:
    """Paths as a line shows them: `a/, b/`, or `[]` for none."""
    shown = ", ".join(paths)
    return shown or "[]"


def default_lines(outcome: DefaultOutcome, reaching: Iterable[str] = ()) -> list[str]:
    """The lines a writer shows for one outcome, indented under its heading."""
    name = outcome.category.name
    if outcome.kind == WRITE:
        lines = [category_location_line(name, listed(outcome.paths), reaching)]
    elif outcome.kind == MOVE:
        lines = [f"  {name}: {listed(outcome.written)} → {listed(outcome.paths)}"]
    else:
        lines = [f"  {name}: {outcome.reason}"]
    if outcome.note:
        lines.append(f"    ({outcome.note})")
    if outcome.over_content:
        lines.append(f"    holds content already: {listed(outcome.over_content)}")
    return lines


def written_defaults_drift(target_root: Path) -> list[DefaultOutcome]:
    """Each line still as written whose query now answers otherwise, or gives no
    answer: the status report's view (ADR-088 point 6). Writes nothing."""
    path = _overlay_path(target_root)
    if not path.is_file():
        return []
    document = wcat.OverlayDocument(path.read_text(encoding="utf-8"))
    found: list[DefaultOutcome] = []
    for category in wcat.installed(target_root):
        written = document.still_as_written(category.name)
        if written is None:
            continue
        answer = wcat.ask(target_root, category)
        if isinstance(answer, wcat.NoAnswer):
            found.append(
                DefaultOutcome(category, NO_ANSWER, written=tuple(written), reason=answer.reason)
            )
        elif list(answer.paths) != written:
            found.append(
                DefaultOutcome(category, MOVE, answer.paths, tuple(written), note=answer.note)
            )
    return found


def _policy_cell(setting: agent_policy.Setting) -> str:
    """One `pkit agents` cell: ``model inherit``, ``effort high (overlay)``, or
    the refused value when the deploy drops it."""
    cell = f"{setting.key} {setting.value}"
    if setting.problem is not None:
        return f"{cell} ({setting.source} value {setting.written!r} refused)"
    if setting.source == agent_policy.SOURCE_OVERLAY:
        return f"{cell} (overlay)"
    return cell


def missing_categories(target_root: Path) -> list[str]:
    """Categories referenced by some agent but undefined in the overlay defaults."""
    missing: set[str] = set()
    for st in agent_overlay_statuses(target_root):
        missing.update(st.missing)
    return sorted(missing)


def agents_reaching(target_root: Path) -> dict[str, list[str]]:
    """Each undefined category → the agents that reach it once it is recorded: every
    agent referencing it with no override of its own. Sorted by agent name."""
    reaching: dict[str, list[str]] = {}
    for st in agent_overlay_statuses(target_root):
        for cat in st.missing:
            reaching.setdefault(cat, []).append(st.name)
    return reaching


def category_location_line(category: str, path: str, agents: Iterable[str]) -> str:
    """One overlay category a command would record, as `reconcile`'s preview and
    `adopt`'s question both show it: ``  category = path  (reached by a, b)``."""
    names = ", ".join(agents)
    reach = f"  (reached by {names})" if names else ""
    return f"  {category} = {path}{reach}"


def optional_categories(target_root: Path) -> set[str]:
    """Categories every referencing agent reads *optionally* — none reads hard.

    A category is optional project-wide (ADR-052) iff at least one agent
    references it and *every* agent that references it does so through the
    optional read channel (`reads.patterns`, not also hard). Such a category
    never blocks a deploy: `reconcile` surfaces it as an enrichment, not a gap.
    A category any agent references hard is excluded, even if another agent
    reads it optionally.
    """
    optional: set[str] = set()
    hard: set[str] = set()
    for name, (_ns, src) in discover_kit_agents(target_root).items():  # noqa: B007
        h, o = agent_category_roles(src)
        hard |= h
        optional |= o
    return optional - hard


def render_status(target_root: Path) -> str:
    """The `pkit agents` read-view: per-agent deploy readiness + overlay gaps."""
    statuses = agent_overlay_statuses(target_root)
    skipped = [s for s in statuses if not s.deployable]
    rows = [
        {
            "name": s.name,
            "namespace": s.namespace,
            "status": "deployable" if s.deployable else "SKIPPED",
            **{setting.key: _policy_cell(setting) for setting in s.policy},
            "missing": ", ".join(s.missing),
        }
        for s in statuses
    ]
    gloss = "deploy via `pkit sync`; configure paths in .pkit/agents/project/overlay.yaml"
    tables: list[dict[str, Any]] = [
        {
            "rows": rows,
            "columns": ["name", "namespace", "status", *agent_policy.POLICY_KEYS, "missing"],
            "header": "AGENTS",
            "gloss": "kit-shipped; resolved against the project overlay",
            "empty": "(no kit-shipped agents found)",
        }
    ]
    # Each override the deploy ignores (#2468), as a warning: nothing else changes.
    unknown = unknown_overrides(target_root)
    if unknown:
        tables.append(
            {
                "rows": [{"override": f"⚠ {u.key}", "reason": u.reason} for u in unknown],
                "columns": ["override", "reason"],
                "header": "UNKNOWN OVERRIDES",
                "gloss": "ignored by the deploy; correct or remove each in "
                f"{OVERLAY_PATH.as_posix()}",
            }
        )
    # Each dotted category no installed capability declares (ADR-088 point 1): a
    # warning, where the unknown overrides are.
    undeclared = undeclared_capability_categories(target_root)
    if undeclared:
        tables.append(
            {
                "rows": [
                    {"category": f"⚠ {u.key}", "reason": "no installed capability declares it"}
                    for u in undeclared
                ],
                "columns": ["category", "reason"],
                "header": "UNDECLARED CAPABILITY CATEGORIES",
                "gloss": "a dotted category is a capability's alone; remove each from "
                f"{OVERLAY_PATH.as_posix()}, or install the capability that declares it",
            }
        )
    # Each line still as written whose default now answers otherwise, or not at all
    # (ADR-088 point 6). Asked afresh; nothing is written.
    drift = written_defaults_drift(target_root)
    if drift:
        tables.append(
            {
                "rows": [
                    {
                        "category": d.category.name,
                        "written": listed(d.written),
                        "default now": listed(d.paths) if d.kind == MOVE else "(no answer)",
                        "why": d.reason or d.note,
                    }
                    for d in drift
                ],
                "columns": ["category", "written", "default now", "why"],
                "header": "WRITTEN DEFAULTS",
                "gloss": "still as written; `pkit agents reconcile` shows the move, "
                "`--write` makes it",
            }
        )
    sections = [cli_render.section(**table) for table in tables]
    # Undefined *optional* categories (ADR-052): patterns-only reads no agent
    # references hard. Their absence never skips an agent — surface them as a
    # non-blocking enrichment, not a gap.
    optional_undefined = sorted(
        set(missing_categories(target_root)) & optional_categories(target_root)
    )
    optional_line = None
    if optional_undefined:
        optional_line = (
            f"Optional categor(ies) undefined ({', '.join(optional_undefined)}): "
            f"agents deploy without them; `pkit agents reconcile` to define and enrich."
        )

    status_part = None
    if skipped:
        # Only *hard* missing categories skip an agent; the optional ones are
        # reported separately below and never contribute to a skip.
        missing = sorted(set(missing_categories(target_root)) - set(optional_undefined))
        cats = ", ".join(missing)
        # `adopt` serves a skipped agent only when each required category it
        # lacks has a conventional folder to create; for any other it refuses.
        # So the lead line names `adopt` only for the agents it serves (#2469).
        conventional = conventional_category_defaults(target_root)
        write_carrying_set = write_carrying_categories(target_root)
        # `adopt` also writes each capability's default its agent owns (ADR-088 point 6).
        owned_defaults = {(c.owner, c.name) for c in wcat.installed(target_root)}
        adoptable = [
            s.name
            for s in skipped
            if all(
                c in conventional or (s.name, c) in owned_defaults
                for c in set(s.missing) - set(s.optional)
            )
        ]
        warn_lines: list[str] = []
        if adoptable:
            who = "the skipped agent(s)" if len(adoptable) == len(skipped) else ", ".join(adoptable)
            warn_lines.append(f"Deploy {who}:  pkit agents adopt <agent>")
            warn_lines.append(
                "Custom doc layout:            "
                "pkit agents reconcile --write → set paths → pkit sync"
            )
        # A capability's category: its default is written by the fill commands.
        defaults = sorted({name for _owner, name in owned_defaults} & set(missing))
        if defaults:
            warn_lines.append(
                f"A capability's default ({', '.join(defaults)}): `pkit agents reconcile` shows "
                f"it, `--write` or `pkit agents adopt <agent>` writes it, then `pkit sync`."
            )
        # A category with no conventional folder, and not write-carrying, is the
        # project's to locate: `adopt` has no folder to create for it.
        no_folder = [
            c
            for c in missing
            if c not in conventional and c not in write_carrying_set and c not in defaults
        ]
        if no_folder:
            warn_lines.append(
                f"No conventional folder ({', '.join(no_folder)}): set the paths in overlay.yaml, "
                f"or stub them with `pkit agents reconcile --write`, then `pkit sync`."
            )
        # A write-carrying category (ADR-051) names paths only the adopter can
        # enumerate, so `adopt` has nothing to create for it — say so here rather
        # than let the lead line send the adopter to a command that must refuse.
        write_carrying = sorted(set(missing) & write_carrying_set)
        if write_carrying:
            warn_lines.append(
                f"Not adoptable ({', '.join(write_carrying)}): reconcile --write fills "
                f"it with an empty list; the agent then deploys inert."
            )
        if optional_line:
            warn_lines.append(optional_line)
        status_part = cli_render.status(
            "Skipped",
            f"{len(skipped)} agent(s)",
            gloss=f"undefined overlay categor(ies): {cats}",
            placement="footer",
            warn="\n".join(warn_lines),
        )
    elif optional_line:
        # Nothing skipped, but an optional read is undefined — inform, don't warn.
        status_part = cli_render.status(
            "Optional",
            f"{len(optional_undefined)} categor(ies) undefined",
            gloss="agents deploy without them",
            placement="footer",
            warn=optional_line,
        )
    commands = [
        (
            "pkit agents adopt <agent>",
            "create conventional dirs + wire overlay + deploy in one step",
        ),
        (
            "pkit agents reconcile [--write]",
            "auto-fill or stub missing overlay categories; then `pkit sync`",
        ),
        ("pkit sync", "re-deploy agents after editing the overlay"),
    ]
    return cli_render.view(
        title=cli_render.title("Agents", f"{len(statuses)} kit-shipped", gloss=gloss),
        sections=sections,
        status=status_part,
        commands=commands,
    )


def reconcile_overlay(target_root: Path, *, write: bool) -> tuple[list[str], str]:
    """Surface referenced-but-undefined categories into the overlay.

    A write category an installed capability declares comes first (ADR-088 point
    6): each one no value is set for, or whose line is still as written, is
    asked of its query, and the preview shows each write, each move, each refused
    answer and each query with no answer; ``write`` makes the writes and moves
    (`_reconcile_defaults`). Such a category takes none of the states below.

    Six states per other referenced category:

    - **missing + write-carrying** (ADR-051): the category grants write
      authority over paths only the adopter can enumerate, so it has no
      conventional default and ships as an explicit empty list → write
      ``cat: []`` **uncommented**, which restores fresh-install parity: the
      agent deploys *inert* (owning nothing) rather than being skipped, and the
      adopter nominates paths when they are ready.
    - **missing + conventional dir exists** (detect-then-fill): the category is
      absent from the overlay AND the conventional default directory for it
      exists under the project root → write the category **uncommented** with
      that path, ready for ``pkit sync`` to deploy the agent with no manual
      editing.
    - **missing + optional** (ADR-052): the category is absent, has no
      conventional dir to auto-fill, and every agent reads it only through
      ``reads.patterns`` → add a commented stub framed as an enrichment; the
      agent already deploys without it.
    - **missing + conventional dir absent**: the category is absent AND there is
      no conventional default to auto-fill → add a commented stub; the adopter
      fills in real paths before ``pkit sync``.
    - **commented-stub**: a ``# cat:`` line exists but is unfilled → report
      "uncomment + set real paths" guidance; do NOT duplicate the stub.
    - **defined**: an uncommented ``cat:`` entry with paths → nothing to do;
      an adopter-set value is never overwritten.

    Dry-run unless ``write``. An auto-fill over a folder that already holds
    documents is recorded with no prompt: ``write``, given to a command that
    otherwise only shows what it would record, is the explicit confirmation
    (COR-049 point 5). Returns (categories_added, report).
    ``categories_added`` covers **both** auto-filled (uncommented) and stubbed
    (commented) categories written to the file in this run.

    **A missing overlay** is repaired here, the command that needs it: with
    ``write`` it is created from the seed first install writes, and nothing
    else is written in that run. The next dry run reads the six states above
    against it, so ``write`` records no category the person has not been shown
    (COR-049 point 5). It is the one writer outside the lifecycle that creates
    a seed path (ADR-065 point 11): sync creates none, and a version transition
    creates it only where it is missing. The dry run says it would.
    """
    path = _overlay_path(target_root)
    if not path.is_file():
        if not write:
            return [], (
                f"the agents overlay is missing ({OVERLAY_PATH.as_posix()}). Re-run with "
                "`--write` to create it from the seed first install writes. Then run "
                "`pkit agents reconcile` again to see each category the seed does not define.\n"
            )
        from project_kit.install import AGENTS_OVERLAY_SEED

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(AGENTS_OVERLAY_SEED, encoding="utf-8")
        return [], (
            f"created {OVERLAY_PATH.as_posix()} from the seed (it was missing). Run "
            "`pkit agents reconcile` to see each category the seed does not define, then "
            "`--write` to record them.\n"
        )
    # A write category comes first among the states (ADR-088 point 6): each one
    # point 4 lets a writer write, or still as written, is asked of its query.
    categories = wcat.installed(target_root)
    lines: list[str] = []
    to_add: list[str] = []
    if categories:
        defaults, lines = _reconcile_defaults(target_root, path, categories, write=write)
        to_add += defaults
    declared = {category.name for category in categories}

    missing = [c for c in missing_categories(target_root) if c not in declared]
    existing = path.read_text(encoding="utf-8")

    def _is_defined(cat: str) -> bool:
        """Uncommented ``cat:`` line — sync/deploy considers this defined."""
        return bool(re.search(rf"(?m)^\s*{re.escape(cat)}\s*:", existing))

    def _is_commented_stub(cat: str) -> bool:
        """A ``# cat:`` stub exists but is not yet uncommented/filled."""
        return bool(re.search(rf"(?m)^\s*#\s*{re.escape(cat)}\s*:", existing))

    conventional = conventional_category_defaults(target_root)

    def _conventional_dir_exists(cat: str) -> str | None:
        """Return the conventional default path (derived from the internal
        root) if its directory exists, else None."""
        default = conventional.get(cat)
        if default and (target_root / default).is_dir():
            return default
        return None

    truly_missing = [c for c in missing if not _is_defined(c) and not _is_commented_stub(c)]

    # Partition missing categories, in precedence order: empty-fill
    # (write-carrying, ADR-051), auto-fill (conventional dir exists),
    # optional-stub (a patterns-only read, ADR-052 — the agent already deploys),
    # or a plain (hard) stub.
    write_carrying = write_carrying_categories(target_root)
    optional = optional_categories(target_root)
    empty_fill: list[str] = []
    auto_fill: list[tuple[str, str]] = []  # (category, path)
    optional_stub: list[str] = []
    to_stub: list[str] = []
    for cat in truly_missing:
        if cat in write_carrying:
            empty_fill.append(cat)
            continue
        conv = _conventional_dir_exists(cat)
        if conv is not None:
            auto_fill.append((cat, conv))
        elif cat in optional:
            optional_stub.append(cat)
        else:
            to_stub.append(cat)

    # Categories that are stubbed-but-commented: already in the file, need
    # the adopter to uncomment + fill paths before sync will deploy the agent.
    commented_stubs = [c for c in missing if _is_commented_stub(c)]

    if empty_fill:
        if lines:
            lines.append("")
        to_add += empty_fill
        verb = "would fill" if not write else "filled"
        lines.append(
            cli_render.style(
                "strong",
                f"{verb} {len(empty_fill)} write-carrying categor(ies) with an empty list "
                f"— the agent deploys inert until you nominate paths:",
            )
        )
        for cat in empty_fill:
            lines.append(f"  {cat}: []")
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; {_OVERLAY_REPAIR}")
            block_lines = [
                "",
                "# --- added by `pkit agents reconcile` (write-carrying; ships empty) ---",
                "# These categories grant an agent WRITE authority over paths only you can",
                "# enumerate, so they ship as an explicit empty list: the agent deploys",
                "# owning nothing. Add your own paths when ready — an entry that resolves",
                "# into sync-managed content is refused at deploy time.",
            ]
            for cat in empty_fill:
                block_lines.append(f"{cat}: []")
            with path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(block_lines) + "\n")
            lines.append("")
            lines.append("empty list written — run `pkit sync` to deploy the agent(s) inert.")
        else:
            lines.append("")
            lines.append("(dry-run — re-run with `--write` to write these entries.)")

    if auto_fill:
        to_add += [cat for cat, _ in auto_fill]
        if lines:
            lines.append("")
        verb = "would auto-fill" if not write else "auto-filled"
        lines.append(
            cli_render.style(
                "strong",
                f"{verb} {len(auto_fill)} categor(ies) — conventional default directory exists:",
            )
        )
        reaching = agents_reaching(target_root)
        for cat, conv_path in auto_fill:
            lines.append(category_location_line(cat, conv_path, reaching.get(cat, ())))
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; {_OVERLAY_REPAIR}")
            # Choosing the location is what records it (COR-049 point 5); `--write`,
            # given after the dry run showed these entries, is the confirmation.
            lines.append("")
            for cat, conv_path in auto_fill:
                if docs_roots.record_location(
                    target_root, docs_roots.BACKBONE, cat, conv_path, by="pkit agents reconcile"
                ):
                    lines.append(
                        docs_roots.recording_notice(
                            target_root, docs_roots.BACKBONE, cat, conv_path
                        )
                    )
            lines.append("")
            lines.append("conventional paths written — run `pkit sync` to deploy the agent(s).")
        else:
            lines.append("")
            lines.append("(dry-run — re-run with `--write` to write these entries.)")

    if to_stub:
        to_add += to_stub
        if lines:
            lines.append("")
        verb = "would add" if not write else "added"
        lines.append(
            cli_render.style(
                "strong", f"{verb} {len(to_stub)} commented categor(ies) to the overlay:"
            )
        )
        lines += [f"  # {c}" for c in to_stub]
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; {_OVERLAY_REPAIR}")
            block_lines = [
                "",
                "# --- added by `pkit agents reconcile` — uncomment and set real paths ---",
            ]
            for cat in to_stub:
                block_lines += [f"# {cat}:", "#   - <path/relative/to/project/root>"]
            with path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(block_lines) + "\n")
            lines.append("")
            lines.append(
                "Deploy the skipped agent(s):  pkit agents adopt <agent>\n"
                "Custom doc layout:            uncomment + set real paths in overlay.yaml, then "
                "`pkit sync`."
            )
        else:
            lines.append("")
            lines.append("(dry-run — re-run with `--write` to append these stubs.)")

    if optional_stub:
        to_add += optional_stub
        if lines:
            lines.append("")
        verb = "would add" if not write else "added"
        lines.append(
            cli_render.style(
                "strong",
                f"{verb} {len(optional_stub)} optional categor(ies) to the overlay "
                f"(the agent already deploys without them):",
            )
        )
        lines += [f"  # {c}" for c in optional_stub]
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; {_OVERLAY_REPAIR}")
            block_lines = [
                "",
                "# --- added by `pkit agents reconcile` (optional read; the agent already deploys) "
                "---",
                "# These categories are OPTIONAL corpus reads: the agent deploys and works",
                "# without them (as a generalist). Uncomment and set paths to give it your",
                "# corpus — an enrichment, never a prerequisite.",
            ]
            for cat in optional_stub:
                block_lines += [f"# {cat}:", "#   - <path/relative/to/project/root>"]
            with path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(block_lines) + "\n")
            lines.append("")
            lines.append(
                "Optional — the agent already deploys. To give it your corpus: "
                "uncomment + set real paths in overlay.yaml, then `pkit sync`."
            )
        else:
            lines.append("")
            lines.append("(dry-run — re-run with `--write` to append these stubs.)")

    if commented_stubs:
        if lines:
            lines.append("")
        commented_optional = [c for c in commented_stubs if c in optional]
        commented_hard = [c for c in commented_stubs if c not in optional]
        if commented_hard:
            lines.append(
                cli_render.style(
                    "strong",
                    f"{len(commented_hard)} categor(ies) already stubbed but still commented — "
                    "action needed:",
                )
            )
            for cat in commented_hard:
                lines.append(f"  # {cat}")
            lines.append("")
            lines.append(
                "Deploy the skipped agent(s):  pkit agents adopt <agent>\n"
                "Custom doc layout:            uncomment + set real paths in overlay.yaml, then "
                "`pkit sync`."
            )
        if commented_optional:
            if commented_hard:
                lines.append("")
            lines.append(
                cli_render.style(
                    "strong",
                    f"{len(commented_optional)} optional categor(ies) already stubbed "
                    f"(the agent already deploys without them):",
                )
            )
            for cat in commented_optional:
                lines.append(f"  # {cat}")
            lines.append("")
            lines.append(
                "Optional — the agent already deploys. To give it your corpus: "
                "uncomment + set real paths in overlay.yaml, then `pkit sync`."
            )

    if not lines:
        # Every referenced category is fully defined — nothing left to do.
        return [], cli_render.style(
            "strong", "overlay is complete — every referenced category is defined."
        )

    return to_add, "\n".join(lines) + "\n"


def _reconcile_defaults(
    target_root: Path, path: Path, categories: list[wcat.WriteCategory], *, write: bool
) -> tuple[list[str], list[str]]:
    """`reconcile`'s writes and moves of a capability's defaults (ADR-088 point 6).

    Shows each write as `category = paths` with the agents that reach it, each
    move from the value written to the new answer, and each refused answer and
    each query with no answer, with why. With *write*, makes each write and move
    it shows: `--write` is the consent, over content too (COR-049 point 5).
    Provisions nothing. Returns the categories it wrote or moved, and its lines.
    """
    document = wcat.OverlayDocument(path.read_text(encoding="utf-8"))
    try:
        outcomes = plan_defaults(target_root, categories, document, moves=True)
    except wcat.OverlayDoesNotRead as exc:
        return [], [f"the overlay does not read, so no default is written: {exc}"]
    reaching = agents_reaching(target_root)
    groups = (
        (WRITE, "would write", "wrote", "capability default(s) into the overlay:"),
        (MOVE, "would move", "moved", "written default(s) to its query's newer answer:"),
        (REFUSED, "refused", "refused", "answer(s), writing nothing for each:"),
        (NO_ANSWER, "no answer from", "no answer from", "default query(ies):"),
    )
    lines: list[str] = []
    for kind, dry, done, what in groups:
        shown = [o for o in outcomes if o.kind == kind]
        if not shown:
            continue
        if lines:
            lines.append("")
        lines.append(cli_render.style("strong", f"{done if write else dry} {len(shown)} {what}"))
        for outcome in shown:
            lines += default_lines(outcome, reaching.get(outcome.category.name, ()))
    changed = [o for o in outcomes if o.changes]
    if changed:
        lines.append("")
        if write:
            apply_defaults(document, changed)
            path.write_text(document.text, encoding="utf-8")
            lines.append(
                f"written in {OVERLAY_PATH.as_posix()}; edit a value and it is the project's. "
                "Run `pkit sync` to deploy the agent(s)."
            )
        else:
            lines.append("(dry-run — re-run with `--write` to write these entries.)")
    return [o.category.name for o in changed], lines


# Seed README content written into a newly-created conventional dir by `adopt`.
# Explains the directory's purpose so the adopter knows why it was created.
_SEED_README_CONTENT: dict[str, str] = {
    "architecture-docs": """\
# Architecture documentation

This directory holds architecture documentation for the project.
It was created by `pkit agents adopt` as the conventional location for the
`architecture-docs` overlay category used by the `architect` agent (per COR-024).

Place architecture documents here — ADRs, system overviews, design notes — that
the architect agent should read when performing its review duties.
""",
    "adr-records": """\
# Architecture Decision Records (ADRs)

This directory holds Architecture Decision Records for the project.
It was created by `pkit agents adopt` as the conventional location for the
`adr-records` overlay category used by the `architect` agent (per COR-024 + COR-025).

Author new ADRs here using `pkit new decision adr <slug>`.
""",
}

_SEED_README_DEFAULT = """\
# {category}

This directory was created by `pkit agents adopt` as the conventional location
for the `{category}` overlay category (see `.pkit/agents/project/overlay.yaml`).

Populate it with the files the agent expects to find here.
"""


@dataclass(frozen=True)
class AdoptResult:
    """Outcome of `adopt_agent` for one agent."""

    agent: str
    dirs_created: tuple[str, ...]  # relative paths of directories created
    categories_wired: tuple[str, ...]  # categories written to overlay (uncommented)
    categories_already_set: tuple[str, ...]  # categories that were already defined
    deployed: bool  # whether the deploy step ran
    # Optional reads (ADR-052) left undefined because they have no conventional
    # default: the agent deploys without them, so adopt neither refuses nor wires.
    categories_optional_unset: tuple[str, ...] = ()
    # Conventional dirs that existed but held nothing: given the seed README, as a
    # created dir is (COR-049 point 5).
    dirs_seeded: tuple[str, ...] = ()
    # What the command says of each category it recorded (`docs_roots.recording_notice`).
    notices: tuple[str, ...] = ()


def holds_entries(folder: Path) -> bool:
    """Whether `folder` is a directory holding any entry at all — a document, a
    sub-folder, a hidden file. One that is absent or empty holds nothing: recording
    an overlay category over it hands no document over (COR-049 point 5)."""
    return folder.is_dir() and any(folder.iterdir())


def recording_consent(
    target_root: Path,
    held: list[tuple[str, str]],
    rest: list[tuple[str, str]],
    *,
    yes: bool,
    rerun: str,
    preview: str | None = None,
) -> project_config.Consent:
    """The consent a command asks for one run that records overlay categories over
    folders holding documents (COR-049 point 5): what each recording puts within an
    agent's reach, and the rest of the run, which waits on the same answer. `rerun`
    is the command with `--yes` a refusal names; `preview`, one that shows the change
    without writing it."""
    reaching = agents_reaching(target_root)

    def listing(pairs: list[tuple[str, str]]) -> str:
        return "".join(
            category_location_line(cat, path, reaching.get(cat, ())) + "\n" for cat, path in pairs
        )

    detail = (
        "These folders already hold documents; recording each category puts them within "
        "reach of the agents named:\n" + listing(held)
    )
    if rest:
        detail += (
            "The run also records these, over folders it creates or that hold nothing:\n"
            + listing(rest)
        )
    return project_config.Consent(
        yes=yes,
        rerun=rerun,
        target=OVERLAY_PATH.as_posix(),
        rule="COR-049 point 5",
        preview=preview,
        detail=detail,
    )


def adopt_agent(
    target_root: Path,
    agent_name: str,
    *,
    yes: bool = False,
    deploy_fn: Callable[[Path, str], bool] | None = None,
) -> AdoptResult:
    """Stand up an agent's overlay prerequisites in one step.

    For the named agent, for each overlay category it references that is not yet
    defined in ``.pkit/agents/project/overlay.yaml``:

    1. Ensure the conventional default dir exists — create it (with a seed README)
       if absent, and give the seed README to one that exists but holds nothing.
       The path is the conventional default derived from the project's internal
       documentation root (:func:`conventional_category_defaults`). Categories
       without a conventional default raise :class:`click.ClickException` because
       there is no canonical path to create — unless the agent reads the category
       only optionally (ADR-052): then it is left undefined, reported in
       *categories_optional_unset*, and the agent deploys without it.
    2. Write the category into the overlay **uncommented** with the conventional
       path.  An adopter-set value (already uncommented) is never overwritten.

    Recording a category over a dir that already holds documents puts them within
    reach of every agent referencing it, so it takes consent (COR-049 point 5):
    ``yes``, else one question for the run at a terminal, else a refusal
    (:class:`project_config.ConsentRefused`). Which dirs hold documents is read for
    every category before anything is written — ``adr-records`` lies inside
    ``architecture-docs``, so a dir this run creates must not make its parent look
    occupied — and a "no" or a refusal leaves everything as it was: no dir, no
    overlay line, no deploy. A dir the run creates, or one holding nothing, is
    recorded without asking.

    After wiring the overlay, invokes *deploy_fn* (a callable taking
    ``(target_root, agent_name)`` and returning ``True`` on success) to deploy the
    agent.  When *deploy_fn* is ``None``, falls back to invoking
    ``deploy-agents.sh`` directly (the claude-code adapter).

    Idempotent: re-running on an already-adopted agent makes no changes to the
    overlay or filesystem, asks nothing, deploys again (the deploy step itself is
    idempotent), and returns a result with empty *dirs_created* and
    *categories_wired*.

    A write category a capability declares with the agent as its owner (ADR-088
    point 6) takes no folder: where no value is set, the query's answer is
    written, or the empty list for a category with no default, and over a path
    that holds content the same consent is taken. A value already set, or still
    as written, is left as it is. An answer refused, or a query with no answer,
    refuses the run before anything is written.

    Raises :class:`click.ClickException` when the agent is unknown, or when a
    category it still needs has no conventional default (so no canonical dir can
    be created — the adopter must set the path via ``reconcile``). For a
    *write-carrying* category (ADR-051) that refusal is structural rather than
    incidental, and says so: core cannot enumerate the adopter's paths, so
    ``reconcile``'s empty-list fill is the only honest path.
    """
    # --- Validate the agent exists and references categories ---
    kit_agents = discover_kit_agents(target_root)
    if agent_name not in kit_agents:
        known = sorted(kit_agents.keys())
        hint = f"  known: {', '.join(known)}" if known else "  (no kit-shipped agents found)"
        raise click.ClickException(f"unknown agent {agent_name!r}.\n{hint}")

    _ns, src = kit_agents[agent_name]
    referenced = agent_referenced_categories(src)
    if not referenced:
        raise click.ClickException(
            f"agent {agent_name!r} references no overlay categories — nothing to adopt."
        )

    # --- Load overlay ---
    path = _overlay_path(target_root)
    if not path.is_file():
        raise click.ClickException(
            f"overlay not found at {path}; {_OVERLAY_REPAIR} Then adopt again."
        )
    existing = path.read_text(encoding="utf-8")

    def _is_defined(cat: str) -> bool:
        return bool(re.search(rf"(?m)^\s*{re.escape(cat)}\s*:", existing))

    # The write categories the agent owns (ADR-088 point 6): each one point 4 lets
    # a writer write gets its query's answer, or `[]`; none is moved, and no folder
    # is created for one. Whether one has a value is read from the parsed overlay.
    document = wcat.OverlayDocument(existing)
    owned = [c for c in wcat.installed(target_root) if c.owner == agent_name]
    try:
        defaults = plan_defaults(target_root, owned, document, moves=False)
    except wcat.OverlayDoesNotRead as exc:
        raise click.ClickException(f"the overlay at {path} does not read: {exc}") from exc
    unanswered = [o for o in defaults if o.kind in (REFUSED, NO_ANSWER)]
    if unanswered:
        raise click.ClickException(
            f"agent {agent_name!r}: no default can be written for "
            + "; ".join(f"{o.category.name} ({o.reason})" for o in unanswered)
            + ". Nothing was written. Set the paths in the overlay yourself, or fix the "
            "capability's query and adopt again."
        )
    owned_names = {c.name for c in owned}

    # Determine which categories need action. An optional read (ADR-052) with no
    # conventional default is not a prerequisite — the agent deploys without it —
    # so it is set aside rather than refused; one *with* a default is wired as usual.
    _hard, optional = agent_category_roles(src)
    conventional = conventional_category_defaults(target_root)
    others = sorted(referenced - owned_names)
    optional_unset = [
        c for c in sorted(optional - owned_names) if not _is_defined(c) and c not in conventional
    ]
    undefined = [c for c in others if not _is_defined(c) and c not in optional_unset]
    already_set = [c for c in others if _is_defined(c)] + [
        o.category.name for o in defaults if not o.changes
    ]

    # --- Check the categories still needing action for a conventional default ---
    # Judged over `undefined`, not everything referenced: an agent whose
    # write-carrying category is already set has nothing for adopt to create and
    # should just deploy, not error.
    no_default = [c for c in undefined if c not in conventional]
    if no_default:
        write_carrying = write_carrying_categories(target_root)
        if set(no_default) <= write_carrying:
            # ADR-051: `adopt` structurally cannot serve a write-carrying
            # category — there is no conventional path to create for paths only
            # the adopter can enumerate. Point at the command that can.
            raise click.ClickException(
                f"agent {agent_name!r} references write-carrying categor(ies) "
                f"`adopt` cannot serve: {', '.join(no_default)}.\n"
                f"These grant write authority over paths only you can enumerate, so "
                f"there is no conventional default to create.\n"
                f"Run `pkit agents reconcile --write` — it fills them with an empty "
                f"list, and the agent deploys owning nothing until you nominate paths."
            )
        raise click.ClickException(
            f"agent {agent_name!r} references categor(ies) with no conventional default: "
            f"{', '.join(no_default)}.\n"
            f"Use `pkit agents reconcile --write` to add a commented stub, then set real "
            f"paths manually before running `pkit sync`."
        )

    # --- Consent, decided before anything is written (COR-049 point 5) ---
    # Each dir's state is read for every category first: `adr-records` lies inside
    # `architecture-docs`, so once this run created the one, the other would look
    # occupied. A dir that exists but holds nothing is treated as absent.
    overlay_additions = [(cat, conventional[cat]) for cat in undefined]  # guarded above
    absent = {cat for cat, conv_path in overlay_additions if not (target_root / conv_path).is_dir()}
    held = [(c, p) for c, p in overlay_additions if holds_entries(target_root / p)]
    writes = [o for o in defaults if o.changes]
    held_writes = [(o.category.name, listed(o.paths)) for o in writes if o.over_content]
    if held or held_writes:
        rest = [pair for pair in overlay_additions if pair not in held] + [
            (o.category.name, listed(o.paths)) for o in writes if not o.over_content
        ]
        held = held + held_writes
        recording_consent(
            target_root,
            held,
            rest,
            yes=yes,
            rerun=f"pkit agents adopt {shlex.quote(agent_name)} --yes",
            preview="pkit agents reconcile",
        ).confirm("Record them")

    dirs_created: list[str] = []
    dirs_seeded: list[str] = []
    for cat, conv_path in overlay_additions:
        if (cat, conv_path) in held:
            continue
        # 1. Ensure the conventional dir exists, with a seed README explaining its purpose.
        abs_dir = target_root / conv_path
        abs_dir.mkdir(parents=True, exist_ok=True)
        readme = abs_dir / "README.md"
        if not readme.exists():
            readme_content = _SEED_README_CONTENT.get(
                cat, _SEED_README_DEFAULT.format(category=cat)
            )
            readme.write_text(readme_content, encoding="utf-8")
        (dirs_created if cat in absent else dirs_seeded).append(conv_path)

    # 2. Write each default the agent owns, then record each chosen location in the
    #    overlay (COR-049 point 5), with consent given above where a path already
    #    held content; the rest takes none beyond running the command.
    notices: list[str] = []
    if writes:
        apply_defaults(document, writes)
        path.write_text(document.text, encoding="utf-8")
        notices += [
            f"wrote {o.category.name} = {listed(o.paths)} in {OVERLAY_PATH.as_posix()}, the "
            "capability's default; edit it and the value is the project's."
            for o in writes
        ]
    for cat, conv_path in overlay_additions:
        if docs_roots.record_location(
            target_root, docs_roots.BACKBONE, cat, conv_path, by="pkit agents adopt"
        ):
            notices.append(
                docs_roots.recording_notice(target_root, docs_roots.BACKBONE, cat, conv_path)
            )

    # 3. Deploy the agent.
    deployed = _deploy_agent(target_root, agent_name, deploy_fn=deploy_fn)

    return AdoptResult(
        agent=agent_name,
        dirs_created=tuple(dirs_created),
        categories_wired=tuple(cat for cat, _path in overlay_additions)
        + tuple(o.category.name for o in writes),
        categories_already_set=tuple(already_set),
        deployed=deployed,
        categories_optional_unset=tuple(optional_unset),
        dirs_seeded=tuple(dirs_seeded),
        notices=tuple(notices),
    )


def _deploy_agent(
    target_root: Path,
    agent_name: str,
    *,
    deploy_fn: Callable[[Path, str], bool] | None,
) -> bool:
    """Run the deploy step for a single agent.

    Falls back to invoking ``deploy-agents.sh`` from the claude-code adapter.
    Returns True on success; raises ClickException on failure.
    """
    if deploy_fn is not None:
        return deploy_fn(target_root, agent_name)

    adapters_root = target_root / ".pkit" / "adapters"
    deploy_script = adapters_root / "claude-code" / "deploy-agents.sh"
    if not deploy_script.is_file():
        # No claude-code adapter present — cannot deploy.
        raise click.ClickException(
            f"deploy-agents.sh not found at {deploy_script.relative_to(target_root)}. "
            f"Run `pkit init` first, or run `pkit sync` manually to deploy the agent."
        )

    result = subprocess.run(
        [str(deploy_script)],
        cwd=target_root,
        capture_output=False,
    )
    if result.returncode != 0:
        raise click.ClickException(
            f"deploy-agents.sh exited with status {result.returncode}. "
            f"See output above for details."
        )
    return True
