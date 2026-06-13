"""project-kit — methodology framework for AI-assisted software projects.

The package version is read from `.pkit/VERSION` (in source) or from the
bundled copy at `project_kit/_kit_version.txt` (in installed wheel) at
import time, so a single source of truth for the backbone version is
preserved across both contexts.
"""

from importlib.resources import files
from pathlib import Path


def _read_version() -> str:
    # Source-tree path: .pkit/VERSION at the repo root, three levels up
    # from this file.
    src_tree_version = Path(__file__).resolve().parents[2] / ".pkit" / "VERSION"
    if src_tree_version.is_file():
        return src_tree_version.read_text(encoding="utf-8").strip()

    # Installed-wheel path: bundled file inside the package per pyproject's
    # `force-include`.
    bundled = files(__name__).joinpath("_kit_version.txt")
    return bundled.read_text(encoding="utf-8").strip()


__version__ = _read_version()
