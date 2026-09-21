"""The containment read-seam — resolve a parent's children native-where-present,
textual-otherwise, native-wins (DEC-005).

The counterpart to the write seam (test_pm_containment_write_seam.py). Where the
write half is the SOLE CONSTRUCTOR of the native link, the read half
(`_lib.containment.resolve_children`) is the SOLE RESOLVER of "what are this
parent's children?" — and both `show-tree` and the DEC-034 closure-fold
child-walk route through it, so no consumer re-derives containment by parsing
body parent-refs in parallel (ADR-026's one-read-seam discipline, mirrored on the
containment axis).

These tests are OFFLINE: the native `…/sub_issues` read is mocked at
`_gh_call` / `read_native_child_numbers`, the textual side is the in-hand corpus.

The acceptance cases the issue enumerates:
  * native-only parent
  * textual-only parent
  * mixed parent (some native + some textual), incl. a child present BOTH ways →
    not double-counted, native-wins
  * unsupported instance → textual-only (graceful)
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"
SEAM_MODULE = LIB / "containment.py"


@pytest.fixture(scope="module")
def containment():
    """Load the containment module via importlib (sibling _lib import)."""
    if str(LIB) not in sys.path:
        sys.path.insert(0, str(LIB))
    spec = importlib.util.spec_from_file_location(
        "pm_containment_read_under_test", SEAM_MODULE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_containment_read_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _native(*numbers: int) -> str:
    """A `gh api …/sub_issues` JSON payload carrying these child NUMBERS."""
    entries = ", ".join(f'{{"number": {n}, "id": {n * 1000}}}' for n in numbers)
    return f"[{entries}]"


def _stub_native(containment, monkeypatch, *, stdout: str, returncode: int = 0, stderr: str = ""):
    """Stub the native `…/sub_issues` GET at `_gh_call`.

    ``stderr`` matters: it is what separates an instance with no native
    substrate (404/410/422) from one that could not be reached (ADR-035 §5).
    """
    def fake_gh(args, config):
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(containment, "_gh_call", fake_gh)


# --- read_native_child_numbers: the native side --------------------------


def test_read_native_child_numbers_parses_numbers(containment, monkeypatch) -> None:
    _stub_native(containment, monkeypatch, stdout=_native(344, 350))
    nums = containment.read_native_child_numbers({}, parent_number=342)
    assert nums == {344, 350}


def test_read_native_child_numbers_empty_is_a_successful_empty_read(
    containment, monkeypatch
) -> None:
    """An empty array is a SUCCESSFUL read of a parent with no native children —
    an empty set, NOT None (None means unsupported/unreadable → textual fallback)."""
    _stub_native(containment, monkeypatch, stdout="[]")
    assert containment.read_native_child_numbers({}, parent_number=342) == set()


@pytest.mark.parametrize("returncode", [1])
def test_read_native_child_numbers_none_on_nonzero(containment, monkeypatch, returncode) -> None:
    _stub_native(containment, monkeypatch, stdout="", returncode=returncode)
    assert containment.read_native_child_numbers({}, parent_number=342) is None


def test_read_native_child_numbers_none_when_gh_missing(containment, monkeypatch) -> None:
    def boom(args, config):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(containment, "_gh_call", boom)
    assert containment.read_native_child_numbers({}, parent_number=342) is None


# --- resolve_children: the four acceptance cases --------------------------


def test_native_only_parent(containment, monkeypatch) -> None:
    """A parent whose children are all native sub-issues — none discovered only
    textually. All resolve NATIVE."""
    _stub_native(containment, monkeypatch, stdout=_native(344, 350))
    # Corpus carries the children's bodies but with NO textual parent-ref.
    corpus = {344: "## What\nno ref", 350: "## What\nno ref", 342: "EPIC body"}
    res = containment.resolve_children({}, parent_number=342, corpus=corpus)
    assert res.native_supported is True
    assert res.numbers == [344, 350]
    assert res.native_numbers == [344, 350]
    assert res.textual_numbers == []


def test_textual_only_parent(containment, monkeypatch) -> None:
    """No native sub-issues (empty native read); children discovered only via the
    textual body parent-ref. All resolve TEXTUAL."""
    _stub_native(containment, monkeypatch, stdout="[]")
    corpus = {
        344: "EPIC: #342\n\n## What",
        345: "EPIC: #342\n\n## What",
        342: "EPIC body, no parent",
        99: "EPIC: #1\n",  # a different parent — excluded
    }
    res = containment.resolve_children({}, parent_number=342, corpus=corpus)
    assert res.native_supported is True  # the read succeeded, just empty
    assert res.numbers == [344, 345]
    assert res.native_numbers == []
    assert res.textual_numbers == [344, 345]


def test_mixed_parent_native_wins_no_double_count(containment, monkeypatch) -> None:
    """THE load-bearing case (the live #342 shape): #344 is BOTH a native
    sub-issue AND carries a textual `EPIC: #342` ref → native wins, counted ONCE;
    #345 is textual-only. The union is {#344 native, #345 textual}, each once."""
    _stub_native(containment, monkeypatch, stdout=_native(344))
    corpus = {
        344: "EPIC: #342\n\n## What",   # native AND textual → native-wins
        345: "EPIC: #342\n\n## What",   # textual-only
        342: "EPIC body",
    }
    res = containment.resolve_children({}, parent_number=342, corpus=corpus)
    assert res.numbers == [344, 345], "the union, deduped — each child exactly once"
    assert res.native_numbers == [344], "#344 resolved NATIVE (native wins the conflict)"
    assert res.textual_numbers == [345], "#345 resolved TEXTUAL (projection-only)"
    # No double-count: #344 appears in exactly one substrate bucket.
    assert 344 not in res.textual_numbers


def test_mixed_native_child_absent_from_corpus_still_native(containment, monkeypatch) -> None:
    """A native sub-issue the textual corpus scan missed (e.g. linked outside the
    create path, no textual ref) is STILL a child — the native panel is
    authoritative (native-wins even when textual is silent)."""
    _stub_native(containment, monkeypatch, stdout=_native(344, 999))
    corpus = {344: "EPIC: #342\n", 345: "EPIC: #342\n", 342: "EPIC body"}
    res = containment.resolve_children({}, parent_number=342, corpus=corpus)
    assert res.numbers == [344, 345, 999]
    assert res.native_numbers == [344, 999]
    assert res.textual_numbers == [345]


_MIXED_CORPUS = {
    344: "EPIC: #342\n\n## What",
    345: "EPIC: #342\n\n## What",
    342: "EPIC body",
}


def test_unsupported_instance_is_textual_only_and_determinate(containment, monkeypatch) -> None:
    """An instance without native sub-issues degrades to TEXTUAL-ONLY, and that
    degradation is a COMPLETE answer — the mirror of the write side's UNSUPPORTED
    no-op. There is no native substrate to have missed anything (ADR-035 §5)."""
    _stub_native(containment, monkeypatch, stdout="", returncode=1, stderr="HTTP 404: Not Found")
    res = containment.resolve_children(
        {}, parent_number=342, corpus=_MIXED_CORPUS, corpus_complete=True
    )
    assert res.native_supported is False, "404 → no native substrate here"
    assert res.numbers == [344, 345], "textual projection still resolves both children"
    assert res.textual_numbers == [344, 345]
    assert res.complete is True, "textual-only is the whole answer when native is unsupported"


def test_unreadable_native_makes_the_resolution_incomplete(containment, monkeypatch) -> None:
    """A native read that FAILED is not the same as one that is unsupported.

    This is the fail-open ADR-035 §5 closes: collapsing the two let a transient
    error degrade silently to textual-only, dropping any natively-linked child
    whose body carries no parent-ref line. The seam must now say it cannot vouch
    for the set.
    """
    _stub_native(
        containment, monkeypatch, stdout="", returncode=1, stderr="error connecting: connection reset"
    )
    res = containment.resolve_children(
        {}, parent_number=342, corpus=_MIXED_CORPUS, corpus_complete=True
    )
    assert res.native_supported is True, "a reachable-but-failing endpoint is not 'unsupported'"
    assert res.complete is False, "a native child set may exist and was not seen"
    assert res.incomplete_reason and "native" in res.incomplete_reason


def test_parent_excludes_itself_and_foreign_children(containment, monkeypatch) -> None:
    _stub_native(containment, monkeypatch, stdout="[]")
    corpus = {
        342: "EPIC: #342\n",   # names itself — never its own child
        344: "EPIC: #342\n",
        99: "EPIC: #1\n",      # foreign parent
    }
    res = containment.resolve_children({}, parent_number=342, corpus=corpus)
    assert res.numbers == [344]


def test_childless_parent_resolves_empty(containment, monkeypatch) -> None:
    _stub_native(containment, monkeypatch, stdout="[]")
    res = containment.resolve_children(
        {}, parent_number=342, corpus={342: "EPIC body", 9: "EPIC: #1\n"}
    )
    assert res.numbers == []
    assert res.native_supported is True


# --- the two consumers route through the SAME seam (ADR-026) --------------


def _imports_containment(path: Path) -> bool:
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.endswith("containment"):
                return True
            if any(a.name == "containment" for a in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(a.name.endswith("containment") for a in node.names):
                return True
    return False


def test_show_tree_routes_child_building_through_the_seam() -> None:
    """show-tree resolves children via the seam, not by parsing body refs in the
    command — `_extract_parent_ref` (the old direct parser) is gone from it."""
    src = (SCRIPTS / "show-tree.py").read_text(encoding="utf-8")
    assert _imports_containment(SCRIPTS / "show-tree.py")
    assert "resolve_children" in src
    assert "_extract_parent_ref" not in src, (
        "show-tree still has the direct body-ref parser — it must resolve children "
        "through the containment seam (ADR-026 one-read-seam)"
    )


def test_closure_fold_cascade_members_routes_through_the_seam() -> None:
    """The DEC-034 closure-fold member source (`cascade_members`) resolves
    children via the SAME seam — no parallel reader (the load-bearing ADR-026
    point: a second consumer must not re-derive)."""
    src = (LIB / "lifecycle_predicates.py").read_text(encoding="utf-8")
    assert _imports_containment(LIB / "lifecycle_predicates.py")
    assert "resolve_children" in src


def test_close_issue_find_open_children_routes_through_the_seam() -> None:
    """close-issue's `_find_open_children` (the cascade-refusal diagnostic) also
    resolves via the seam — one reader of containment, not two."""
    src = (SCRIPTS / "close-issue.py").read_text(encoding="utf-8")
    assert _imports_containment(SCRIPTS / "close-issue.py")
    assert "resolve_children" in src


# --- acquisition: the seam owns it, and says when it did not see everything ---
#
# #846: `cascade-members` enumerated the whole tracker with a 500-row ceiling
# named `_OPEN_ISSUES_LIMIT` while querying `--state all`. At 507 issues it
# struck the ceiling on every call, so no container in the repo could close.


def _stub_gh_list(containment, monkeypatch, *, total: int, child_at: int, parent: int):
    """Stub `gh issue list`, HONOURING `--limit` the way gh does.

    Honouring the limit is what gives this test teeth: a caller asking for fewer
    rows than the tracker holds gets a short list, exactly as in production.
    """
    def fake_gh(args, config):
        if args[1] == "api":  # the native sub-issues read, not the corpus list
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404")
        limit = int(args[args.index("--limit") + 1])
        rows = [
            {
                "number": n,
                "state": "open",
                "body": (f"EPIC: #{parent}\n" if n == child_at else "## What\nno ref"),
            }
            for n in range(1, total + 1)
        ]
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps(rows[:limit]), stderr=""
        )

    monkeypatch.setattr(containment, "_gh_call", fake_gh)


def test_a_child_beyond_the_old_ceiling_still_resolves(containment, monkeypatch) -> None:
    """The regression #846 reported, at the size that caused it.

    A 600-issue tracker with the only child at row 550. Under the retired 500-row
    ceiling that row was never fetched, so the child was invisible and the gate
    reported indeterminate. The seam's ceiling is far above any plausible corpus,
    so the child resolves and the answer is complete.
    """
    _stub_gh_list(containment, monkeypatch, total=600, child_at=550, parent=5)
    res = containment.resolve_children({}, parent_number=5)
    assert res.numbers == [550], "the child past the old ceiling must be seen"
    assert res.complete is True


def test_striking_the_acquisition_ceiling_is_reported_not_swallowed(
    containment, monkeypatch
) -> None:
    """A struck ceiling yields an INCOMPLETE answer, never a short one served whole.

    This is the property `close-issue` lacked entirely: it fetched 500 rows and
    computed open children with no truncation check, so past 500 issues it would
    close a container over a child it never saw.
    """
    _stub_gh_list(
        containment, monkeypatch, total=containment.CORPUS_CEILING + 10, child_at=1, parent=5
    )
    res = containment.resolve_children({}, parent_number=5)
    assert res.complete is False
    assert res.incomplete_reason and "exhaustion" in res.incomplete_reason


def test_a_supplied_corpus_without_a_completeness_claim_is_not_vouched_for(
    containment, monkeypatch
) -> None:
    """A caller may still supply a corpus — but it must say whether it is whole.

    Absent the claim the seam reports incomplete rather than assuming, because
    assuming is precisely how four consumers ended up with four ceilings.
    """
    _stub_native(containment, monkeypatch, stdout="[]")
    res = containment.resolve_children({}, parent_number=5, corpus={9: "EPIC: #5\n"})
    assert res.numbers == [9]
    assert res.complete is False
