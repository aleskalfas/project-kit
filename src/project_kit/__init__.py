"""project-kit — methodology framework for AI-assisted software projects.

The package version is read from `.pkit/VERSION` (in a source checkout) or
from the bundled copy at `project_kit/_kit/VERSION` (in an installed wheel)
at import time, so a single source of truth for the backbone version is
preserved across both contexts. The bundled path is the same `_kit/` tree
`find_source_kit` falls back to (ADR-033) — one bundled VERSION, not a
separate version-only file that could disagree with the bundled tree.
"""

from importlib.resources import files
from pathlib import Path


def _read_version() -> str:
    # Source-tree path: .pkit/VERSION at the repo root, three levels up
    # from this file.
    src_tree_version = Path(__file__).resolve().parents[2] / ".pkit" / "VERSION"
    if src_tree_version.is_file():
        return src_tree_version.read_text(encoding="utf-8").strip()

    # Installed-wheel path: the bundled methodology tree's VERSION file, per
    # pyproject's `force-include` (`project_kit/_kit/VERSION`).
    bundled = files(__name__).joinpath("_kit", "VERSION")
    return bundled.read_text(encoding="utf-8").strip()


__version__ = _read_version()
