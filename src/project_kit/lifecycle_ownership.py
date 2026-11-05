"""The tool's one loader of the tree's ownership predicates (ADR-051).

The ownership questions — is this path the methodology's to manage, is it the
project's by tier, does it arrive here as a synced copy — are answered once, by
`.pkit/lifecycle/ownership.py`. That module lives in the tree rather than in
this package for the reason ADR-003 records for the permission core: an
adapter's deploy resolver runs in the adopter's tree, where `project_kit` is not
importable. So the backbone reads *the target tree's* copy, by path, rather than
keeping its own — one definition for the tool and every harness — and every
backbone reader loads it through here.

Every `pkit new` command that writes into a tree a sync may write asks the
third question of its target before it writes anything
(`synced_copy_refusal`): what a project writes into a synced copy, the next
sync overwrites (core rule 1).
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


def synced_copy_refusal(target_root: Path, folder: Path, subject: str, instead: str) -> str | None:
    """Why a stamp may not write into *folder*, or None where the project authors it.

    The question is the tree's own predicate, `is_synced_copy`, keyed on origin
    and on the repository: a backbone tree, or a kit-shipped capability's, in a
    project that is not the methodology's source, and an externally-sourced
    capability's in any project. The next sync overwrites what a project writes
    there (core rule 1). *folder* need not exist yet. *subject* names what
    arrives as a copy, and *instead* where the project's own artefact goes. A
    tree without the module has no synced copy, as for validation.
    """
    ownership = load_ownership(target_root)
    if ownership is None:
        return None
    try:
        where = folder.relative_to(target_root).as_posix()
    except ValueError:
        where = folder.as_posix()
    if not ownership.is_synced_copy(target_root, where):
        return None
    return (
        f"{subject} arrives in this project as a synced copy: {where}/ is not the "
        "project's, and the next sync overwrites what is written there (the "
        f"no-shared-files invariant). {instead}"
    )
