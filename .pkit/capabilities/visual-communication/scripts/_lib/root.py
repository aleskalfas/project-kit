"""Where a visual-communication command runs: the project it is installed in.

Standard library only, so every command can import it, whatever it depends on.
"""

from __future__ import annotations

from pathlib import Path

#: This capability's name, as installed under `.pkit/capabilities/`, and as each file of
#: its format names it in its binding (DEC-002 point 3).
CAPABILITY = "visual-communication"

#: Where installed capabilities live, relative to the project root.
CAPABILITIES_DIR = ".pkit/capabilities"

#: The capability's own folder, relative to the project root.
CAPABILITY_DIR = f"{CAPABILITIES_DIR}/{CAPABILITY}"

#: The capability's project configuration (DEC-002 point 2), relative to the project root.
CONFIG = f"{CAPABILITY_DIR}/project/config.yaml"

#: What a render or an export makes that is not committed, local to each clone (DEC-002
#: point 1), declared in `package.yaml`'s `runtime_ignore`.
LOCAL = f"{CAPABILITY_DIR}/project/local"

#: The capability's own folder in the code that runs: its schemas and shipped libraries
#: lie beside the scripts.
SHIPPED = Path(__file__).resolve().parents[2]


def project_root() -> Path:
    """The project a command runs in: the nearest folder, from the working directory up,
    where this capability is installed, else the working directory."""
    start = Path.cwd()
    for folder in (start, *start.parents):
        if (folder / CAPABILITY_DIR).is_dir():
            return folder
    return start
