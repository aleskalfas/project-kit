"""The prune: `pkit friction prune` (COR-062 point 8; ADR-068 point 4).

A change of its own removes the answer files in which no answer is live. It removes
files and adds none, so it changes no answer live at its head, owes nothing and flags
no dependant. It is a writing command, and names what it removes (COR-050 point 13).

- **What it reads.** HEAD and its full history, as the whole-repository check reads
  them: which answers are live, and the names in `read` that history agrees with
  (COR-062 points 4 and 5). `StateAnswers.prune` judges which files go. A shallow
  clone is refused, since a cut history cannot tell which names it agrees with.
- **What it keeps.** A file in which one answer is live stays whole. So does a file
  in which none is, where removing it would change an answer that is live:
  - one that cannot be read, since what it holds cannot be judged
  - one whose removal brings back an answer it replaced (COR-062 point 8, "What
    stays replaced")
  - one a live deferral keeps its point from (point 6)

  Each kept file is named with why.
- **What it writes.** It removes the files from the working tree, and stages and
  commits nothing. The removal lands as a change of its own, which adds no answer
  file, or the change check finds a prune mixed with answers (COR-062 point 3).
- **Consent.** `--yes`, or at a terminal a confirmation after the list. `--dry-run`
  lists and removes nothing. A run that can ask nobody, with neither, refuses and
  names both commands (COR-048 point 5, as every friction writer asks). The prune
  writes no answer, so the `--yes` command is named.
- **What it refuses**, removing nothing: a tree whose answer folder holds an
  uncommitted change, since the prune judges HEAD and a change of its own adds no
  answer file; no commit; no place declared; a place's file whose front matter does
  not parse, whose answers could not be told from answers on what is gone; answers
  not yet moved out of the blocks (COR-062 point 11).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_kit import answer_files, cli_render
from project_kit.answer_files import AnswerHistory
from project_kit.friction_discovery import discover_artefacts
from project_kit.friction_git import (
    SHORT,
    BlobReader,
    CommitTree,
    FrictionCheckError,
    commit_of,
    run_git,
)
from project_kit.friction_history import Walker, read_history

#: The `--json` document's version, under the rule every friction document follows.
SCHEMA_VERSION = 1

#: How many uncommitted paths a refusal names.
_NAMED = 3


@dataclass(frozen=True)
class KeptFile:
    """An answer file in which no answer is live that the prune keeps, and why."""

    path: str
    why: str


@dataclass(frozen=True)
class PrunePlan:
    """What the prune does at HEAD: the commit, how many answer files it holds and how
    many hold a live answer, the files it removes, repository-relative and sorted, and
    the files it keeps though no answer in them is live."""

    head: str
    files: int
    live: int
    remove: tuple[str, ...]
    kept: tuple[KeptFile, ...]


def plan_prune(target_root: Path) -> PrunePlan:
    """What `pkit friction prune` removes at HEAD, read with its full history.

    Raises `FrictionCheckError`, removing nothing, where it cannot judge (the module's
    "What it refuses")."""
    try:
        head = commit_of(target_root, "HEAD")
    except FrictionCheckError:
        head = None
    if head is None:
        raise FrictionCheckError(
            "HEAD names no commit (or this is not a git repository): the prune judges the "
            "answer files HEAD holds, so commit first. Nothing was removed."
        )
    _refuse_uncommitted(target_root)
    blobs = BlobReader(target_root)
    try:
        tree = CommitTree(target_root, head, blobs)
        rels = [rel for rel in tree.files() if answer_files.is_answer_file(rel)]
        if not rels:
            return PrunePlan(head, 0, 0, (), ())
        discovery = discover_artefacts(target_root, tree=tree)
        if not discovery.places:
            raise FrictionCheckError(
                "no place is declared, so no answer can be judged live, and the prune would "
                "take every answer file for one on what is gone. Nothing was removed."
            )
        if discovery.unreadable:
            named = ", ".join(sorted(u.path for u in discovery.unreadable)[:_NAMED])
            raise FrictionCheckError(
                f"front matter does not parse in {len(discovery.unreadable)} file(s) of the "
                f"places ({named}), so the answers on them cannot be told from answers on what "
                f"is gone: mend them first (`pkit validate` reports them). Nothing was removed."
            )
        answer_files.refuse_unmoved(discovery.artefacts, rels, target_root=target_root)
        history = read_history(target_root, head)
        if history.shallow:
            raise FrictionCheckError(
                "this clone is shallow: a name in `read` counts only where history agrees "
                "with it (COR-062 point 5), which a cut history cannot tell. Run `git fetch "
                "--unshallow` first. Nothing was removed."
            )
        state = AnswerHistory(history, Walker(history, blobs), blobs).head(head)
        pruning = state.prune(discovery)
    finally:
        blobs.close()
    return PrunePlan(
        head,
        len(rels),
        pruning.live,
        tuple(answer_files.path_of(name) for name in pruning.remove),
        tuple(KeptFile(answer_files.path_of(k.name), k.why) for k in pruning.kept),
    )


def _refuse_uncommitted(target_root: Path) -> None:
    """Refuse a working tree whose answer folder differs from HEAD's: the prune judges
    HEAD, and a change of its own adds no answer file (COR-062 point 3)."""
    listed = run_git(
        target_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--",
        f"{answer_files.FOLDER}/",
    )
    paths = [
        line[3:]
        for line in listed.stdout.decode("utf-8", "surrogateescape").split("\0")
        if len(line) > 3 and line[2] == " "
    ]
    if not paths:
        return
    named = ", ".join(paths[:_NAMED]) + (
        f" and {len(paths) - _NAMED} more" if len(paths) > _NAMED else ""
    )
    raise FrictionCheckError(
        f"the answer folder holds {len(paths)} uncommitted change(s) ({named}). The prune "
        f"judges the answer files HEAD holds, and lands as a change of its own, which adds "
        f"no answer file (COR-062 point 3): commit those answers, or set them aside, and "
        f"run it again. Nothing was removed."
    )


def remove(target_root: Path, plan: PrunePlan) -> tuple[str, ...]:
    """Remove each file the plan removes from the working tree, and return them. A file
    that is gone already is passed over."""
    removed: list[str] = []
    for rel in plan.remove:
        path = target_root / rel
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except OSError as exc:
            done = f" It removed {len(removed)} before it." if removed else ""
            raise FrictionCheckError(f"cannot remove {rel}: {exc}.{done}") from exc
        removed.append(rel)
    return tuple(removed)


def render_plan(plan: PrunePlan) -> str:
    """What the prune removes and what it keeps, one line per file."""
    title = (
        cli_render.style("title", "Friction prune")
        + f" — {answer_files.FOLDER}/ at {plan.head[:SHORT]}"
    )
    lines = [title, ""]
    if not plan.files:
        lines.append("  No answer file at HEAD: nothing to remove.")
        return "\n".join(lines) + "\n"
    lines.append(
        f"  {plan.files} answer file{'' if plan.files == 1 else 's'}; {plan.live} "
        f"hold{'s' if plan.live == 1 else ''} a live answer and stay whole."
    )
    if plan.remove:
        lines.append(f"  Removes {len(plan.remove)}, in which no answer is live (COR-062 point 8):")
        lines.extend(f"    {rel}" for rel in plan.remove)
    if plan.kept:
        lines.append(
            f"  Keeps {len(plan.kept)} in which no answer is live, since removing "
            f"{'it' if len(plan.kept) == 1 else 'them'} would change one that is:"
        )
        lines.extend(f"    {k.path} — {k.why}" for k in plan.kept)
    if not plan.remove:
        lines.append("  Nothing to remove.")
    return "\n".join(lines) + "\n"


def render_done(removed: tuple[str, ...]) -> str:
    """What the prune did, and what is left for the person to do."""
    return (
        f"Removed {len(removed)} answer file{'' if len(removed) == 1 else 's'}. Nothing is "
        f"staged or committed: commit the removal as a change of its own, which adds no "
        f"answer file (COR-062 point 3).\n"
    )


def render_json(plan: PrunePlan, *, dry_run: bool, removed: tuple[str, ...]) -> str:
    """The stable document: keys sorted, the same bytes for the same state and run."""
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "report": "prune",
        "dry_run": dry_run,
        "head": plan.head,
        "folder": answer_files.FOLDER,
        "files": plan.files,
        "live": plan.live,
        "remove": list(plan.remove),
        "removed": list(removed),
        "kept": [{"path": k.path, "why": k.why} for k in plan.kept],
    }
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


__all__ = [
    "SCHEMA_VERSION",
    "KeptFile",
    "PrunePlan",
    "plan_prune",
    "remove",
    "render_done",
    "render_json",
    "render_plan",
]
