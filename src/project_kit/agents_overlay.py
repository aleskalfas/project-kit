"""Agent overlay diagnostics + reconcile + adopt (per COR-013).

The `pkit agents` surface: a read-only diagnostic of which kit-shipped agents
will deploy vs. be skipped (because they reference an overlay *category* the
adopter's `.pkit/agents/project/overlay.yaml` does not define), plus an
explicit `reconcile` that surfaces the missing categories into the overlay as
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
"""
from __future__ import annotations

import io
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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

# The frontmatter keys whose list items may hold `<category>` placeholders,
# mirrored from the claude-code adapter's `_resolve_agent.py`. A guard test
# asserts this stays in sync, so a backbone scan can never silently drift from
# what the deployer actually resolves.
RESOLVABLE_LIST_KEYS: tuple[str, ...] = ("owns", "needs", "answers")
RESOLVABLE_READS_KEYS: tuple[str, ...] = ("paths", "records", "patterns")

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

    @property
    def deployable(self) -> bool:
        return not self.missing


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

def _placeholders(items: object) -> set[str]:
    out: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str) and item.startswith("<") and item.endswith(">"):
                out.add(item[1:-1])
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


# --- overlay ----------------------------------------------------------------

def _overlay_path(target_root: Path) -> Path:
    return target_root / ".pkit" / "agents" / "project" / "overlay.yaml"


def load_overlay(target_root: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Return (default category names, {agent: override category names})."""
    path = _overlay_path(target_root)
    if not path.is_file() or path.stat().st_size == 0:
        return set(), {}
    data = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return set(), {}
    overrides_raw = data.get("overrides") or {}
    overrides: dict[str, set[str]] = {}
    if isinstance(overrides_raw, dict):
        for agent, cats in overrides_raw.items():
            if isinstance(cats, dict):
                overrides[agent] = set(cats.keys())
    defaults = {k for k in data.keys() if k != "overrides"}
    return defaults, overrides


# --- status + reconcile ------------------------------------------------------

def agent_overlay_statuses(target_root: Path) -> list[AgentOverlayStatus]:
    defaults, overrides = load_overlay(target_root)
    out: list[AgentOverlayStatus] = []
    for name, (ns, src) in sorted(discover_kit_agents(target_root).items()):
        referenced = agent_referenced_categories(src)
        defined = defaults | overrides.get(name, set())
        missing = referenced - defined
        out.append(AgentOverlayStatus(
            name=name, namespace=ns, source=src,
            referenced=tuple(sorted(referenced)),
            missing=tuple(sorted(missing)),
        ))
    return out


def missing_categories(target_root: Path) -> list[str]:
    """Categories referenced by some agent but undefined in the overlay defaults."""
    missing: set[str] = set()
    for st in agent_overlay_statuses(target_root):
        missing.update(st.missing)
    return sorted(missing)


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
    status_part = None
    if skipped:
        cats = ", ".join(missing_categories(target_root))
        status_part = cli_render.status(
            "Skipped", f"{len(skipped)} agent(s)",
            gloss=f"undefined overlay categor(ies): {cats}",
            placement="footer",
            warn="run `pkit agents adopt <agent>` to create the conventional layout and deploy the agent in one step, or `pkit agents reconcile --write` to scaffold the missing categories into .pkit/agents/project/overlay.yaml, then re-run `pkit sync`",
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

    Four states per referenced category:

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

    # Partition missing categories: auto-fill (conventional dir exists) vs stub.
    auto_fill: list[tuple[str, str]] = []   # (category, path)
    to_stub: list[str] = []
    for cat in truly_missing:
        conv = _conventional_dir_exists(cat)
        if conv is not None:
            auto_fill.append((cat, conv))
        else:
            to_stub.append(cat)

    # Categories that are stubbed-but-commented: already in the file, need
    # the adopter to uncomment + fill paths before sync will deploy the agent.
    commented_stubs = [c for c in missing if _is_commented_stub(c)]

    lines: list[str] = []
    to_add: list[str] = []

    if auto_fill:
        to_add += [cat for cat, _ in auto_fill]
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
                "uncomment + set real paths, then `pkit sync` to deploy the skipped agent(s).\n"
                "Alternatively, run `pkit agents adopt <agent>` to create the conventional layout and deploy it."
            )
        else:
            lines.append("")
            lines.append("(dry-run — re-run with `--write` to append these stubs.)")

    if commented_stubs:
        if lines:
            lines.append("")
        lines.append(cli_render.style("strong",
            f"{len(commented_stubs)} categor(ies) already stubbed but still commented — action needed:"))
        for cat in commented_stubs:
            lines.append(f"  # {cat}")
        lines.append("")
        lines.append(
            "stub present but still commented — uncomment + set real paths in "
            "`.pkit/agents/project/overlay.yaml`, then `pkit sync`.\n"
            "Or run `pkit agents adopt <agent>` to create the conventional layout and deploy it."
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

    Raises :class:`click.ClickException` when the agent is unknown, or references
    a category that has no conventional default (so no canonical dir can be
    created — the adopter must set the path manually via ``reconcile``).
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

    # --- Check for categories without a conventional default ---
    no_default = [c for c in sorted(referenced) if c not in CONVENTIONAL_CATEGORY_DEFAULTS]
    if no_default:
        raise click.ClickException(
            f"agent {agent_name!r} references categor(ies) with no conventional default: "
            f"{', '.join(no_default)}.\n"
            f"Use `pkit agents reconcile --write` to add a commented stub, then set real "
            f"paths manually before running `pkit sync`."
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
