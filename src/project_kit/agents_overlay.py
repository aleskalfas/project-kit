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
adapter's `deploy-agents.sh` / `_resolve_agent.py`). This module reproduces the
adapter's *discovery* (which files are agents, with what precedence) and
*reference-detection* (which frontmatter keys may carry placeholders) — the
latter pinned to the adapter by a guard test (`tests/test_agents_overlay.py`).
It never writes a resolved agent; deployment stays the adapter's job.

It also owns the backbone's single *value*-resolution helper
(:func:`load_overlay_values` + :func:`expand_placeholders`) — the same
override-then-default-then-undefined rules the adapter resolver applies, exposed
so every backbone consumer (the reference-graph's exactly-one-owner check, per
COR-013 rule 5) resolves placeholders one way instead of re-deriving them. A
parity test pins it to the adapter resolver's actual behaviour.
"""
from __future__ import annotations

import importlib.util
import io
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from ruamel.yaml import YAML

from project_kit import cli_render

# Conventional default paths for well-known overlay categories, relative to
# the project root.  reconcile checks whether the directory at this path
# exists before deciding whether to fill uncommented (detect-then-fill) or
# fall back to a commented stub.  Declared here — not in agent prose — so that
# reconcile can act on them programmatically and any future agent category can
# register its own default in the same place.
#
# Keys are overlay category names; values are the conventional-default directory
# path (string, relative to project root, no leading slash).  A missing key
# means "no conventional default" → always fall back to a commented stub.
CONVENTIONAL_CATEGORY_DEFAULTS: dict[str, str] = {
    "architecture-docs": "docs/architecture",
    "adr-records": "docs/architecture/decisions",
}


def _ownership_mod(target_root: Path) -> Any | None:
    """Load the lifecycle layer's ownership module from *target_root*, or None.

    The same-code gesture ADR-003 established for the permission core, applied
    to the tier-ownership predicate ADR-051 requires be implemented once: the
    module lives in-tree at `.pkit/lifecycle/ownership.py` because an adapter's
    deploy resolver runs where `project_kit` is not importable, and the backbone
    reads *that* copy rather than keeping its own.

    Returns None when the module is absent — a tree that has not synced since
    the lifecycle layer started carrying it. Callers degrade (the pre-ADR-051
    behaviour) rather than failing; the deploy resolver, whose check is the
    load-bearing one, fails loudly instead.
    """
    path = target_root / ".pkit" / "lifecycle" / "ownership.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("pkit_lifecycle_ownership", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_carrying_categories(target_root: Path) -> frozenset[str]:
    """Overlay categories that carry write authority and ship as `[]` (ADR-051).

    Read from the shared ownership module so the set is declared once. An
    unreachable module yields the empty set, which makes every category take the
    conventional-default path — the behaviour that predates the category.
    """
    mod = _ownership_mod(target_root)
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

    @property
    def deployable(self) -> bool:
        # An undefined *optional* read (a patterns-only category, ADR-052) does
        # not block: it drops at deploy and the agent ships as a generalist.
        # Only an undefined *hard* category skips the agent.
        return not (set(self.missing) - set(self.optional))


# --- discovery (mirrors deploy-agents.sh list_kit_names + source_for) --------

def _agent_names_in(dir_: Path) -> list[str]:
    if not dir_.is_dir():
        return []
    names: list[str] = []
    for entry in sorted(dir_.iterdir()):
        if entry.is_file() and entry.suffix == ".md":
            names.append(entry.stem)
        elif entry.is_dir():
            names.append(entry.name)
    return names


def _source_in(dir_: Path, name: str) -> Path | None:
    """Flat form preferred over folder form (COR-015 atomic-is-flat)."""
    flat = dir_ / f"{name}.md"
    if flat.is_file():
        return flat
    folder = dir_ / name / f"{name}.md"
    if folder.is_file():
        return folder
    return None


def discover_kit_agents(target_root: Path) -> dict[str, tuple[str, Path]]:
    """Return ``{name: (namespace, source_path)}`` for every kit-shipped agent.

    Precedence mirrors the adapter's ``source_for``: project wins over core,
    flat over folder within a namespace, then installed-capability agents.
    """
    agents_root = target_root / ".pkit" / "agents"
    caps_root = target_root / ".pkit" / "capabilities"

    # Collect candidate names across all namespaces (deduped later by precedence).
    names: set[str] = set()
    for ns in ("core", "project"):
        names.update(_agent_names_in(agents_root / ns))
    if caps_root.is_dir():
        for cap in sorted(caps_root.iterdir()):
            names.update(_agent_names_in(cap / "agents"))

    resolved: dict[str, tuple[str, Path]] = {}
    for name in sorted(names):
        # project then core, flat-before-folder handled by _source_in.
        for ns in ("project", "core"):
            src = _source_in(agents_root / ns, name)
            if src is not None:
                resolved[name] = (ns, src)
                break
        else:
            if caps_root.is_dir():
                for cap in sorted(caps_root.iterdir()):
                    src = _source_in(cap / "agents", name)
                    if src is not None:
                        resolved[name] = (f"capability:{cap.name}", src)
                        break
    return resolved


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


def agent_referenced_categories(source: Path) -> set[str]:
    """Categories an agent references — `<cat>` items under the resolvable keys."""
    text = source.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return set()
    fm = _yaml.load(io.StringIO(m.group(1))) or {}
    if not isinstance(fm, dict):
        return set()
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
    text = source.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return set(), set()
    fm = _yaml.load(io.StringIO(m.group(1))) or {}
    if not isinstance(fm, dict):
        return set(), set()
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

def _overlay_path(target_root: Path) -> Path:
    return target_root / ".pkit" / "agents" / "project" / "overlay.yaml"


@dataclass(frozen=True)
class OverlayValues:
    """The overlay's category *values*: top-level defaults + per-agent overrides.

    Mirrors what the adapter resolver reads: every top-level key except the
    reserved ``overrides`` is a default category; ``overrides.<agent>`` holds
    per-agent categories that *replace* (never merge with) the default.
    """

    defaults: dict[str, Any]
    overrides: dict[str, dict[str, Any]]

    def resolve(self, agent_name: str, category: str) -> Any | None:
        """The value a category resolves to for one agent, or None if undefined.

        Precedence mirrors ``_resolve_agent.py``: the agent's own override wins,
        then the top-level default. ``None`` means *undefined* — which covers
        both an absent key and a bare key (``category:`` with no value), exactly
        as the adapter treats them (the agent is skipped at deploy).
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
    data = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return OverlayValues(defaults={}, overrides={})
    overrides_raw = data.get("overrides") or {}
    overrides: dict[str, dict[str, Any]] = {}
    if isinstance(overrides_raw, dict):
        for agent, cats in overrides_raw.items():
            if isinstance(cats, dict):
                overrides[str(agent)] = dict(cats)
    defaults = {str(k): v for k, v in data.items() if k != "overrides"}
    return OverlayValues(defaults=defaults, overrides=overrides)


def load_overlay(target_root: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Return (default category names, {agent: override category names})."""
    values = load_overlay_values(target_root)
    return set(values.defaults), {
        agent: set(cats) for agent, cats in values.overrides.items()
    }


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
    defaults, overrides = load_overlay(target_root)
    out: list[AgentOverlayStatus] = []
    for name, (ns, src) in sorted(discover_kit_agents(target_root).items()):
        referenced = agent_referenced_categories(src)
        _hard, optional = agent_category_roles(src)
        defined = defaults | overrides.get(name, set())
        missing = referenced - defined
        out.append(AgentOverlayStatus(
            name=name, namespace=ns, source=src,
            referenced=tuple(sorted(referenced)),
            missing=tuple(sorted(missing)),
            optional=tuple(sorted(optional)),
        ))
    return out


def missing_categories(target_root: Path) -> list[str]:
    """Categories referenced by some agent but undefined in the overlay defaults."""
    missing: set[str] = set()
    for st in agent_overlay_statuses(target_root):
        missing.update(st.missing)
    return sorted(missing)


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
            "missing": ", ".join(s.missing),
        }
        for s in statuses
    ]
    gloss = "deploy via `pkit sync`; configure paths in .pkit/agents/project/overlay.yaml"
    sections = [cli_render.section(
        rows=rows, columns=["name", "namespace", "status", "missing"],
        header="AGENTS", gloss="kit-shipped; resolved against the project overlay",
        empty="(no kit-shipped agents found)",
    )]
    # Undefined *optional* categories (ADR-052): patterns-only reads no agent
    # references hard. Their absence never skips an agent — surface them as a
    # non-blocking enrichment, not a gap.
    optional_undefined = sorted(set(missing_categories(target_root)) & optional_categories(target_root))
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
        warn_lines = [
            "Deploy the skipped agent(s):  pkit agents adopt <agent>",
            "Custom doc layout:            pkit agents reconcile --write → set paths → pkit sync",
        ]
        # A write-carrying category (ADR-051) names paths only the adopter can
        # enumerate, so `adopt` has nothing to create for it — say so here rather
        # than let the lead line send the adopter to a command that must refuse.
        write_carrying = sorted(set(missing) & write_carrying_categories(target_root))
        if write_carrying:
            warn_lines.append(
                f"Not adoptable ({', '.join(write_carrying)}): reconcile --write fills "
                f"it with an empty list; the agent then deploys inert."
            )
        if optional_line:
            warn_lines.append(optional_line)
        status_part = cli_render.status(
            "Skipped", f"{len(skipped)} agent(s)",
            gloss=f"undefined overlay categor(ies): {cats}",
            placement="footer",
            warn="\n".join(warn_lines),
        )
    elif optional_line:
        # Nothing skipped, but an optional read is undefined — inform, don't warn.
        status_part = cli_render.status(
            "Optional", f"{len(optional_undefined)} categor(ies) undefined",
            gloss="agents deploy without them",
            placement="footer",
            warn=optional_line,
        )
    commands = [
        ("pkit agents adopt <agent>", "create conventional dirs + wire overlay + deploy in one step"),
        ("pkit agents reconcile [--write]", "auto-fill or stub missing overlay categories; then `pkit sync`"),
        ("pkit sync", "re-deploy agents after editing the overlay"),
    ]
    return cli_render.view(
        title=cli_render.title("Agents", f"{len(statuses)} kit-shipped", gloss=gloss),
        sections=sections, status=status_part, commands=commands,
    )


def reconcile_overlay(target_root: Path, *, write: bool) -> tuple[list[str], str]:
    """Surface referenced-but-undefined categories into the overlay.

    Five states per referenced category:

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
    - **missing + conventional dir absent**: the category is absent AND there is
      no conventional default to auto-fill → add a commented stub; the adopter
      fills in real paths before ``pkit sync``.
    - **commented-stub**: a ``# cat:`` line exists but is unfilled → report
      "uncomment + set real paths" guidance; do NOT duplicate the stub.
    - **defined**: an uncommented ``cat:`` entry with paths → nothing to do;
      an adopter-set value is never overwritten.

    Dry-run unless ``write``. Returns (categories_added, report).
    ``categories_added`` covers **both** auto-filled (uncommented) and stubbed
    (commented) categories written to the file in this run.
    """
    missing = missing_categories(target_root)
    path = _overlay_path(target_root)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""

    def _is_defined(cat: str) -> bool:
        """Uncommented ``cat:`` line — sync/deploy considers this defined."""
        return bool(re.search(rf"(?m)^\s*{re.escape(cat)}\s*:", existing))

    def _is_commented_stub(cat: str) -> bool:
        """A ``# cat:`` stub exists but is not yet uncommented/filled."""
        return bool(re.search(rf"(?m)^\s*#\s*{re.escape(cat)}\s*:", existing))

    def _conventional_dir_exists(cat: str) -> str | None:
        """Return the conventional default path if its directory exists, else None."""
        default = CONVENTIONAL_CATEGORY_DEFAULTS.get(cat)
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
    auto_fill: list[tuple[str, str]] = []   # (category, path)
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

    lines: list[str] = []
    to_add: list[str] = []

    if empty_fill:
        to_add += empty_fill
        verb = "would fill" if not write else "filled"
        lines.append(cli_render.style(
            "strong",
            f"{verb} {len(empty_fill)} write-carrying categor(ies) with an empty list "
            f"— the agent deploys inert until you nominate paths:",
        ))
        for cat in empty_fill:
            lines.append(f"  {cat}: []")
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; run `pkit init` first.")
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
        lines.append(cli_render.style(
            "strong",
            f"{verb} {len(auto_fill)} categor(ies) — conventional default directory exists:",
        ))
        for cat, conv_path in auto_fill:
            lines.append(f"  {cat}: [{conv_path}]")
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; run `pkit init` first.")
            block_lines = ["", "# --- added by `pkit agents reconcile` (detect-then-fill) ---"]
            for cat, conv_path in auto_fill:
                block_lines += [f"{cat}:", f"  - {conv_path}"]
            with path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(block_lines) + "\n")
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
        lines.append(cli_render.style("strong", f"{verb} {len(to_stub)} commented categor(ies) to the overlay:"))
        lines += [f"  # {c}" for c in to_stub]
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; run `pkit init` first.")
            block_lines = ["", "# --- added by `pkit agents reconcile` — uncomment and set real paths ---"]
            for cat in to_stub:
                block_lines += [f"# {cat}:", "#   - <path/relative/to/project/root>"]
            with path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(block_lines) + "\n")
            lines.append("")
            lines.append(
                "Deploy the skipped agent(s):  pkit agents adopt <agent>\n"
                "Custom doc layout:            uncomment + set real paths in overlay.yaml, then `pkit sync`."
            )
        else:
            lines.append("")
            lines.append("(dry-run — re-run with `--write` to append these stubs.)")

    if optional_stub:
        to_add += optional_stub
        if lines:
            lines.append("")
        verb = "would add" if not write else "added"
        lines.append(cli_render.style(
            "strong",
            f"{verb} {len(optional_stub)} optional categor(ies) to the overlay "
            f"(the agent already deploys without them):",
        ))
        lines += [f"  # {c}" for c in optional_stub]
        if write:
            if not path.is_file():
                raise FileNotFoundError(f"overlay not found at {path}; run `pkit init` first.")
            block_lines = [
                "",
                "# --- added by `pkit agents reconcile` (optional read; the agent already deploys) ---",
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
            lines.append(cli_render.style("strong",
                f"{len(commented_hard)} categor(ies) already stubbed but still commented — action needed:"))
            for cat in commented_hard:
                lines.append(f"  # {cat}")
            lines.append("")
            lines.append(
                "Deploy the skipped agent(s):  pkit agents adopt <agent>\n"
                "Custom doc layout:            uncomment + set real paths in overlay.yaml, then `pkit sync`."
            )
        if commented_optional:
            if commented_hard:
                lines.append("")
            lines.append(cli_render.style("strong",
                f"{len(commented_optional)} optional categor(ies) already stubbed "
                f"(the agent already deploys without them):"))
            for cat in commented_optional:
                lines.append(f"  # {cat}")
            lines.append("")
            lines.append(
                "Optional — the agent already deploys. To give it your corpus: "
                "uncomment + set real paths in overlay.yaml, then `pkit sync`."
            )

    if not to_add and not commented_stubs:
        # Every referenced category is fully defined — nothing left to do.
        return [], cli_render.style("strong", "overlay is complete — every referenced category is defined.")

    return to_add, "\n".join(lines) + "\n"


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
    dirs_created: tuple[str, ...]   # relative paths of directories created
    categories_wired: tuple[str, ...]  # categories written to overlay (uncommented)
    categories_already_set: tuple[str, ...]  # categories that were already defined
    deployed: bool   # whether the deploy step ran


def adopt_agent(
    target_root: Path,
    agent_name: str,
    *,
    deploy_fn: Callable[[Path, str], bool] | None = None,
) -> AdoptResult:
    """Stand up an agent's overlay prerequisites in one step.

    For the named agent, for each overlay category it references that is not yet
    defined in ``.pkit/agents/project/overlay.yaml``:

    1. Ensure the conventional default dir exists — create it (with a seed README)
       if absent.  Uses :data:`CONVENTIONAL_CATEGORY_DEFAULTS` to resolve the path.
       Categories without a conventional default raise :class:`click.ClickException`
       because there is no canonical path to create.
    2. Write the category into the overlay **uncommented** with the conventional
       path.  An adopter-set value (already uncommented) is never overwritten.

    After wiring the overlay, invokes *deploy_fn* (a callable taking
    ``(target_root, agent_name)`` and returning ``True`` on success) to deploy the
    agent.  When *deploy_fn* is ``None``, falls back to invoking
    ``deploy-agents.sh`` directly (the claude-code adapter).

    Idempotent: re-running on an already-adopted agent makes no changes to the
    overlay or filesystem, deploys again (the deploy step itself is idempotent),
    and returns a result with empty *dirs_created* and *categories_wired*.

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
        raise click.ClickException(
            f"unknown agent {agent_name!r}.\n{hint}"
        )

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
            f"overlay not found at {path}; run `pkit init` first."
        )
    existing = path.read_text(encoding="utf-8")

    def _is_defined(cat: str) -> bool:
        return bool(re.search(rf"(?m)^\s*{re.escape(cat)}\s*:", existing))

    # Determine which categories need action.
    undefined = [c for c in sorted(referenced) if not _is_defined(c)]
    already_set = [c for c in sorted(referenced) if _is_defined(c)]

    # --- Check the categories still needing action for a conventional default ---
    # Judged over `undefined`, not everything referenced: an agent whose
    # write-carrying category is already set has nothing for adopt to create and
    # should just deploy, not error.
    no_default = [c for c in undefined if c not in CONVENTIONAL_CATEGORY_DEFAULTS]
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

    dirs_created: list[str] = []
    categories_wired: list[str] = []
    overlay_additions: list[tuple[str, str]] = []  # (category, path)

    for cat in undefined:
        conv_path = CONVENTIONAL_CATEGORY_DEFAULTS[cat]  # guarded above
        abs_dir = target_root / conv_path

        # 1. Ensure the conventional dir exists.
        if not abs_dir.is_dir():
            abs_dir.mkdir(parents=True, exist_ok=True)
            # Write a seed README explaining the directory's purpose.
            readme_content = _SEED_README_CONTENT.get(
                cat, _SEED_README_DEFAULT.format(category=cat)
            )
            (abs_dir / "README.md").write_text(readme_content, encoding="utf-8")
            dirs_created.append(conv_path)

        # 2. Record for overlay write.
        overlay_additions.append((cat, conv_path))
        categories_wired.append(cat)

    # 3. Write all new categories to the overlay in one append.
    if overlay_additions:
        block_lines = ["", "# --- added by `pkit agents adopt` ---"]
        for cat, conv_path in overlay_additions:
            block_lines += [f"{cat}:", f"  - {conv_path}"]
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(block_lines) + "\n")

    # 4. Deploy the agent.
    deployed = _deploy_agent(target_root, agent_name, deploy_fn=deploy_fn)

    return AdoptResult(
        agent=agent_name,
        dirs_created=tuple(dirs_created),
        categories_wired=tuple(categories_wired),
        categories_already_set=tuple(already_set),
        deployed=deployed,
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
