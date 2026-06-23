"""DEC-034 end-to-end parity — pm's CLOSURE-fold SHAPE resolved through the engine.

The engine's general cascade machine is proven in test_process_cascade_engine.py;
the pm binding shape + predicate bodies in test_pm_closure_cascade_binding.py.
This file closes the loop: it builds a fixture whose cascade declaration is the
SAME SHAPE pm ships — `op: all`, `outcome: done` (a terminal reached by BOTH
completion and won't-do), `on_empty: satisfied` — over a keyed child process with
a terminal `done` state, and proves the DEC-034 acceptance bullets resolve as the
decision requires:

  * a parent's children-half opens iff EVERY child reached `done`;
  * a CHILDLESS container's children-half is SATISFIED (closes — the on_empty
    divergence the amendment exists for), NOT blocked;
  * a WON'T-DO child (closed -> done) counts toward closure (the fold targets the
    terminal `done`, not a completed-only outcome);
  * an OPEN / milestone-rolled-forward child (non-terminal) HOLDS the fold
    unresolved (matches "an open child blocks eligibility", DEC-016);
  * a BROKEN membership read HOLDS the gate fail-closed (does NOT fail-open under
    `satisfied`) — COR-037 precedence.

File-backed: `_issue-<n>` holds each child's lifecycle position (done|in-progress
|...); `_children-<parent>` lists the parent's child ids. The membership predicate
reads only the candidate child's own reality (matching pm's engine-threads-only-
the-subject contract — the parent-scoping lives in the members source).
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from project_kit.process import ProcessEngine, load_definition

# Child process: a stand-in issue lifecycle. `done` is TERMINAL and is reached
# from a `closed` marker — covering BOTH won't-do and pr-merge (pm folds the
# terminal STATE, not a completed-only outcome). `in-progress` is non-terminal
# (an open / rolled-forward child), so it holds the fold unresolved.
_CHILD_DEFINITION = """\
process:
  id: issue-lifecycle
  version: 1
  subject:
    cardinality: keyed
    key: issue-number
  states:
    - id: done
      meaning: Closed (merged via PR, or won't-do).
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: issue-detect-done
    - id: in-progress
      meaning: Open, work in flight (or rolled forward).
      detection:
        mode: inferred
        predicate:
          run: issue-detect-in-progress
  transitions:
    - from: in-progress
      to: done
      trigger: close
      authorisation: script
"""

# Parent process: a container declaring pm's CLOSURE fold shape verbatim.
_CONTAINER_DEFINITION = """\
process:
  id: container
  version: 1
  subject:
    cardinality: keyed
    key: container-id
    blocked:
      blocked_on: awaiting-cascade-outcome
  cascade:
    runs: tracker:issue-lifecycle
    members:
      run: container-children
    membership:
      run: child-membership
    reducer:
      op: all
      outcome: done
    on_empty: satisfied
  states:
    - id: in-progress
      meaning: Container with children still to finish.
      detection:
        mode: inferred
        predicate:
          run: container-detect-in-progress
    - id: done
      meaning: Container closed (all children done).
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: container-detect-done
  transitions:
    - from: in-progress
      to: done
      trigger: close
      authorisation: agent-autonomous
      gate:
        kind: cascade-outcome
      why: Close once every child reached `done`.
"""


def _issue_detect(state_name: str) -> str:
    # A child's position: `_issue-<n>` holds 'done' (closed) or 'in-progress'.
    return (
        "import json, sys, pathlib\n"
        "subj = sys.argv[1]\n"
        "p = pathlib.Path(f'_issue-{subj}')\n"
        "cur = p.read_text().strip() if p.exists() else 'in-progress'\n"
        f"print(json.dumps({{'result': cur == {state_name!r}, "
        "'reason': f'issue {subj} is {cur!r}'}))\n"
    )


def _container_detect(state_name: str) -> str:
    return (
        "import json, sys, pathlib\n"
        "subj = sys.argv[1]\n"
        "p = pathlib.Path(f'_container-state-{subj}')\n"
        "cur = p.read_text().strip() if p.exists() else 'in-progress'\n"
        f"print(json.dumps({{'result': cur == {state_name!r}, "
        "'reason': f'container {subj} is {cur!r}'}))\n"
    )


# Members source: read ONLY the named container's child-list file (parent-scoped,
# mirroring pm's cascade-members walking the body parent-ref for one parent).
_CONTAINER_CHILDREN = (
    "import json, sys, pathlib\n"
    "subj = sys.argv[1]\n"
    "p = pathlib.Path(f'_children-{subj}')\n"
    "ids = [l.strip() for l in p.read_text().splitlines() if l.strip()] if p.exists() else []\n"
    "print(json.dumps({'members': ids, 'reason': f'{len(ids)} child(ren)'}))\n"
)

# Membership: answers from the CHILD's own reality (the engine threads only the
# candidate subject — pm's contract). `_child-parent-<n>` declares the child's
# parent; result True iff it names ANY parent (a hierarchy member). The
# parent-scoping is enforced upstream by the members source (pm's design).
_CHILD_MEMBERSHIP = (
    "import json, sys, pathlib\n"
    "subj = sys.argv[1]\n"
    "p = pathlib.Path(f'_child-parent-{subj}')\n"
    "parent = p.read_text().strip() if p.exists() else ''\n"
    "print(json.dumps({'result': parent != '', "
    "'reason': f'child {subj} parent={parent!r}'}))\n"
)


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_defs(pkit: Path) -> None:
    defs_dst = pkit / "schemas" / "_defs"
    defs_dst.mkdir(parents=True, exist_ok=True)
    source = (
        Path(__file__).resolve().parents[1]
        / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    defs_dst.joinpath("process.schema.json").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )


@pytest.fixture
def tracker_repo(tmp_path: Path) -> Path:
    repo = tmp_path
    pkit = repo / ".pkit"
    _install_defs(pkit)
    cap = pkit / "capabilities" / "tracker"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: tracker
  version: 0.1.0
description: pm closure-fold parity fixture (DEC-034).
commands:
  issue-detect-done: { script: scripts/issue_detect_done.py, help: x }
  issue-detect-in-progress: { script: scripts/issue_detect_in_progress.py, help: x }
  container-detect-in-progress: { script: scripts/container_detect_in_progress.py, help: x }
  container-detect-done: { script: scripts/container_detect_done.py, help: x }
  container-children: { script: scripts/container_children.py, help: x }
  child-membership: { script: scripts/child_membership.py, help: x }
""",
        encoding="utf-8",
    )
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "issue-lifecycle.yaml").write_text(_CHILD_DEFINITION, encoding="utf-8")
    (cap / "schemas" / "container.yaml").write_text(_CONTAINER_DEFINITION, encoding="utf-8")

    _write_script(scripts / "issue_detect_done.py", _issue_detect("done"))
    _write_script(scripts / "issue_detect_in_progress.py", _issue_detect("in-progress"))
    _write_script(scripts / "container_detect_in_progress.py", _container_detect("in-progress"))
    _write_script(scripts / "container_detect_done.py", _container_detect("done"))
    _write_script(scripts / "container_children.py", _CONTAINER_CHILDREN)
    _write_script(scripts / "child_membership.py", _CHILD_MEMBERSHIP)
    return repo


def _container(repo: Path, cid: str = "c1") -> ProcessEngine:
    return ProcessEngine(load_definition(repo, "tracker:container"), repo, subject=cid)


def _add_child(repo: Path, child: str, parent: str, position: str) -> None:
    list_file = repo / f"_children-{parent}"
    existing = list_file.read_text().splitlines() if list_file.exists() else []
    if child not in existing:
        existing.append(child)
    list_file.write_text("\n".join(existing) + "\n", encoding="utf-8")
    (repo / f"_child-parent-{child}").write_text(parent, encoding="utf-8")
    (repo / f"_issue-{child}").write_text(position, encoding="utf-8")


def _close_check(engine: ProcessEngine, actor: str = "agent"):
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, actor)
    return next(c for c in checks if c.to == "done")


# --- the parity bullets ---------------------------------------------------


def test_children_half_opens_when_every_child_done(tracker_repo: Path) -> None:
    _add_child(tracker_repo, "11", "c1", "done")
    _add_child(tracker_repo, "12", "c1", "done")
    fold = _container(tracker_repo).resolve_cascade_outcome()
    assert fold.opened is True
    assert fold.indeterminate is False
    assert fold.reached == 2 and fold.total == 2
    assert _close_check(_container(tracker_repo)).allowed is True


def test_open_child_holds_the_fold(tracker_repo: Path) -> None:
    # An open child (non-terminal) holds the fold unresolved — "an open child
    # blocks eligibility". This is also the milestone roll-forward case (DEC-016):
    # a rolled-forward child stays open/in-progress, so it holds.
    _add_child(tracker_repo, "11", "c1", "done")
    _add_child(tracker_repo, "12", "c1", "in-progress")
    fold = _container(tracker_repo).resolve_cascade_outcome()
    assert fold.opened is False
    assert fold.indeterminate is True  # the open child has no resolved terminal
    assert _close_check(_container(tracker_repo)).allowed is False


def test_wont_do_child_counts_toward_closure(tracker_repo: Path) -> None:
    # A won't-do child is CLOSED -> resolves to the terminal `done`, exactly like
    # a pr-merge completion. Both children done -> the fold opens. This proves the
    # fold targets the terminal STATE `done`, not a completed-only outcome (DEC-034).
    _add_child(tracker_repo, "11", "c1", "done")  # pr-merge completion
    _add_child(tracker_repo, "12", "c1", "done")  # won't-do (also closed -> done)
    fold = _container(tracker_repo).resolve_cascade_outcome()
    assert fold.opened is True
    assert fold.reached == 2 and fold.total == 2


def test_childless_container_is_satisfied_not_blocked(tracker_repo: Path) -> None:
    # THE on_empty divergence: a CHILDLESS container's children-half is SATISFIED
    # (the gate opens), so close-eligibility reduces to the checkbox gate —
    # identical to pm today. NOT fail-closed.
    fold = _container(tracker_repo).resolve_cascade_outcome()  # no children added
    assert fold.total == 0
    assert fold.opened is True
    assert fold.indeterminate is False  # determinate "satisfied", not a failure
    assert _close_check(_container(tracker_repo)).allowed is True


def test_broken_membership_read_holds_the_gate(tracker_repo: Path) -> None:
    # THE precedence bullet: a broken membership read on a POPULATED container does
    # NOT fail-open under `satisfied` — indeterminate membership overrides on_empty,
    # so the fold stays unresolved and the gate stays SHUT.
    _add_child(tracker_repo, "11", "c1", "done")
    _add_child(tracker_repo, "12", "c1", "done")
    scripts = tracker_repo / ".pkit" / "capabilities" / "tracker" / "scripts"
    _write_script(scripts / "child_membership.py", "import sys\nsys.exit(7)\n")
    fold = _container(tracker_repo).resolve_cascade_outcome()
    assert fold.indeterminate is True
    assert fold.opened is False  # NOT opened by satisfied — precedence holds
    assert _close_check(_container(tracker_repo)).allowed is False


def test_broken_members_source_holds_the_gate(tracker_repo: Path) -> None:
    # Companion: a broken members SOURCE (enumeration) is indeterminate before the
    # empty-set branch, so `satisfied` cannot fail-open on a broken enumeration.
    scripts = tracker_repo / ".pkit" / "capabilities" / "tracker" / "scripts"
    _write_script(scripts / "container_children.py", "import sys\nsys.exit(9)\n")
    fold = _container(tracker_repo).resolve_cascade_outcome()
    assert fold.indeterminate is True
    assert fold.opened is False
