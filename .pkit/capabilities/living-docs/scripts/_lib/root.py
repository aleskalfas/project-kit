"""Where a living-docs command runs: the project it is installed in.

Standard library only, so a command with no dependencies of its own — the
`source` resolver — can import it as the validator and the filler do.
"""

from __future__ import annotations

from pathlib import Path

#: This capability's name, as installed under `.pkit/capabilities/`.
CAPABILITY = "living-docs"

#: Where installed capabilities live, relative to the project root.
CAPABILITIES_DIR = ".pkit/capabilities"


def project_root() -> Path:
    """The project a command runs in: the nearest folder, from the working directory
    up, where this capability is installed (`.pkit/capabilities/living-docs/`), else
    the working directory. Git is not asked: what the repository holds is read
    through the backbone, and a script asks git nothing of its own."""
    start = Path.cwd()
    for folder in (start, *start.parents):
        if (folder / CAPABILITIES_DIR / CAPABILITY).is_dir():
            return folder
    return start
