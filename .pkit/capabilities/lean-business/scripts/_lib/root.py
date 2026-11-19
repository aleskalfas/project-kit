"""Where a lean-business command runs: the project it is installed in.

Standard library only, so every command can import it, whatever it depends on.
"""

from __future__ import annotations

from pathlib import Path

#: This capability's name, as installed under `.pkit/capabilities/`, and as each of its
#: files names it in its binding (lean-business DEC-002 point 2).
CAPABILITY = "lean-business"

#: Where installed capabilities live, relative to the project root.
CAPABILITIES_DIR = ".pkit/capabilities"

#: The capability's own folder, relative to the project root.
CAPABILITY_DIR = f"{CAPABILITIES_DIR}/{CAPABILITY}"

#: The capability's own configuration (DEC-002 point 1), relative to the project root.
CONFIG = f"{CAPABILITY_DIR}/project/config.yaml"


def project_root() -> Path:
    """The project a command runs in: the nearest folder, from the working directory up,
    where this capability is installed, else the working directory."""
    start = Path.cwd()
    for folder in (start, *start.parents):
        if (folder / CAPABILITY_DIR).is_dir():
            return folder
    return start
