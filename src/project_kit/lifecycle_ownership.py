"""The tool's one loader of the tree's ownership predicates (ADR-051).

The ownership questions — is this path the methodology's to manage, is it the
project's by tier, does it arrive here as a synced copy — are answered once, by
`.pkit/lifecycle/ownership.py`. That module lives in the tree rather than in
this package for the reason ADR-003 records for the permission core: an
adapter's deploy resolver runs in the adopter's tree, where `project_kit` is not
importable. So the backbone reads *the target tree's* copy, by path, rather than
keeping its own — one definition for the tool and every harness — and every
backbone reader loads it through here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

# Where the lifecycle area puts the module, relative to the project root.
OWNERSHIP_MODULE = Path(".pkit") / "lifecycle" / "ownership.py"


def load_ownership(target_root: Path) -> ModuleType | None:
    """The ownership module of the tree at *target_root*, or None when it has none.

    None means a tree that has not synced since the lifecycle area started
    carrying the module; each caller decides how to degrade, and says so.

    Loading writes nothing into the tree: no bytecode cache is left beside the
    module, since the commands that ask — validation, the friction checks — are
    reading commands, which never write (COR-050 point 13).
    """
    path = target_root / OWNERSHIP_MODULE
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("pkit_lifecycle_ownership", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module
