"""The picker of an agent's definition and the lifecycle's reader of capability
records, staged into a test's own tree.

A command asks the picker, `.pkit/agents/definition_source.py`, which definition
of each name is the agent, and the picker reads which capabilities are installed,
their skips and the project's choices through `.pkit/lifecycle/capability_records.py`.
Both are loaded from the tree the command works on, or from the release it brings
(ADR-087 point 2), so a test that stands up a tree of its own copies both in.
"""

from __future__ import annotations

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: The two modules, relative to a `.pkit/` tree.
MODULES = (
    Path("agents") / "definition_source.py",
    Path("lifecycle") / "capability_records.py",
)


def stage_picker(pkit: Path) -> None:
    """Copy the picker and the records' reader into the `.pkit/` tree *pkit*, a
    project's or a release's."""
    for module in MODULES:
        target = pkit / module
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / ".pkit" / module, target)
