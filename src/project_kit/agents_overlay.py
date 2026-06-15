"""Agent overlay diagnostics + reconcile (per COR-013).

The `pkit agents` surface: a read-only diagnostic of which kit-shipped agents
will deploy vs. be skipped (because they reference an overlay *category* the
adopter's `.pkit/agents/project/overlay.yaml` does not define), plus an
explicit `reconcile` that surfaces the missing categories into the overlay as
commented stubs.

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
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from project_kit import cli_render

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
            warn="run `pkit agents reconcile --write` to scaffold the missing categories into .pkit/agents/project/overlay.yaml, fill in the paths, then re-run `pkit sync`",
        )
    commands = [
        ("pkit agents reconcile [--write]", "add missing overlay categories (commented)"),
        ("pkit sync", "re-deploy agents after editing the overlay"),
    ]
    return cli_render.view(
        title=cli_render.title("Agents", f"{len(statuses)} kit-shipped", gloss=gloss),
        sections=sections, status=status_part, commands=commands,
    )


def reconcile_overlay(target_root: Path, *, write: bool) -> tuple[list[str], str]:
    """Surface referenced-but-undefined categories into the overlay as commented
    stubs. Idempotent (skips categories already present, commented or not).
    Dry-run unless ``write``. Returns (categories_added, report)."""
    missing = missing_categories(target_root)
    path = _overlay_path(target_root)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""

    def already_present(cat: str) -> bool:
        # Defined (`cat:`) or already-stubbed (`# cat:`) — don't duplicate.
        return bool(re.search(rf"(?m)^\s*#?\s*{re.escape(cat)}\s*:", existing))

    to_add = [c for c in missing if not already_present(c)]
    if not to_add:
        if missing:
            return [], cli_render.style("strong",
                f"overlay already lists all {len(missing)} referenced categor(ies); nothing to add.")
        return [], cli_render.style("strong", "overlay is complete — every referenced category is defined.")

    block = ["", "# --- added by `pkit agents reconcile` — uncomment and set real paths ---"]
    for cat in to_add:
        block += [f"# {cat}:", "#   - <path/relative/to/project/root>"]
    stub = "\n".join(block) + "\n"

    verb = "would add" if not write else "added"
    lines = [cli_render.style("strong", f"{verb} {len(to_add)} commented categor(ies) to the overlay:")]
    lines += [f"  # {c}" for c in to_add]
    if write:
        if not path.is_file():
            raise FileNotFoundError(f"overlay not found at {path}; run `pkit init` first.")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(stub)
        lines.append("")
        lines.append("uncomment + set real paths, then `pkit sync` to deploy the skipped agent(s).")
    else:
        lines.append("")
        lines.append("(dry-run — re-run with `--write` to append these stubs.)")
    return to_add, "\n".join(lines) + "\n"
