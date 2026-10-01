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
`_gh_call` / `read_native_children`; the textual side is either an in-hand
corpus or one the seam acquires, which this file also covers via `_stub_gh_list`.

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
    spec = importlib.util.spec_from_file_location("pm_containment_read_under_test", SEAM_MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_containment_read_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _native(*numbers: int) -> str:
    """A `gh api …/sub_issues` JSON payload carrying these child NUMBERS."""
    entries = ", ".join(f'{{"number": {n}, "id": {n * 1000}}}' for n in numbers)
    return f"[{entries}]"


def _stub_native(
    containment,
    monkeypatch,
    *,
    stdout: str,
    returncode: int = 0,
    stderr: str = "",
    repo_visible: bool = True,
):
    """Stub the native `…/sub_issues` GET at `_gh_call`, and the 404 probe.

    ``stderr`` (and, for a 422, the error body on ``stdout``) separates the
    conclusive answers — a 410, a 422 saying the feature is absent — from
    everything else.
    A **404 is ambiguous** — an absent endpoint and an invisible repository are
    textually identical — so it is settled by probing the parent issue.
    ``repo_visible`` is that probe's answer (#869).
    """

    def fake_gh(args, config):
        joined = " ".join(args)
        if "sub_issues" not in joined:  # the parent-issue probe
            return subprocess.CompletedProcess(
                args, 0 if repo_visible else 1, stdout="342", stderr=""
            )
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
        344: "EPIC: #342\n\n## What",  # native AND textual → native-wins
        345: "EPIC: #342\n\n## What",  # textual-only
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
    _stub_native(
        containment,
        monkeypatch,
        stdout="",
        returncode=1,
        stderr="HTTP 404: Not Found",
        repo_visible=True,
    )
    res = containment.resolve_children(
        {}, parent_number=342, corpus=_MIXED_CORPUS, corpus_complete=True
    )
    assert res.native_supported is False, "404 with the repo visible → endpoint absent"
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
        containment,
        monkeypatch,
        stdout="",
        returncode=1,
        stderr="error connecting: connection reset",
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
        342: "EPIC: #342\n",  # names itself — never its own child
        344: "EPIC: #342\n",
        99: "EPIC: #1\n",  # foreign parent
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
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 410: Gone")
        limit = int(args[args.index("--limit") + 1])
        rows = [
            {
                "number": n,
                "state": "open",
                "body": (f"EPIC: #{parent}\n" if n == child_at else "## What\nno ref"),
            }
            for n in range(1, total + 1)
        ]
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(rows[:limit]), stderr="")

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


# --- the ambiguous 404 (#869) ------------------------------------------------
#
# GitHub answers 404 both for "this endpoint is absent" and for "you may not
# know this repository exists". Reading the second as the first hands a close
# gate a determinate child set whenever a token lacks scope — and since a
# fine-grained PAT without `Issues: read` returns 404 rather than 401 on a
# private repo, it fails quietly while public-repo work keeps succeeding.


def test_an_invisible_repository_is_not_an_absent_endpoint(containment, monkeypatch) -> None:
    """The same 404, settled by whether the repository can be seen at all.

    Against the text-only predicate this asserted the opposite: `HTTP 404` alone
    resolved to UNSUPPORTED, so a credential fault produced a *complete*
    textual-only answer and the gate closed over any natively-linked child whose
    body carries no parent-ref line.
    """
    _stub_native(
        containment,
        monkeypatch,
        stdout="",
        returncode=1,
        stderr="HTTP 404: Not Found (https://api.github.com/repos/o/r/issues/342/sub_issues)",
        repo_visible=False,
    )
    res = containment.resolve_children(
        {}, parent_number=342, corpus=_MIXED_CORPUS, corpus_complete=True
    )
    assert res.complete is False, "a 404 we cannot attribute must not read as determinate"
    assert res.incomplete_reason and "native" in res.incomplete_reason
    assert res.native_supported is True, "the endpoint is not known to be absent"


_ABSENT_422_BODY = json.dumps(
    {"message": "Sub-issues are not enabled for this repository", "status": "422"}
)


@pytest.mark.parametrize(
    "stdout, stderr",
    [
        ("", "HTTP 410: Gone"),
        (_ABSENT_422_BODY, "gh: Sub-issues are not enabled for this repository (HTTP 422)"),
    ],
    ids=["410", "422-saying-absent"],
)
def test_conclusive_answers_need_no_probe(
    containment, monkeypatch, stdout: str, stderr: str
) -> None:
    """A 410, or a 422 whose message says the feature is absent, names
    feature-absence outright — an invisible repo never yields them.

    `repo_visible=False` would flip a 404; these must resolve UNSUPPORTED anyway,
    which proves they short-circuit before the probe rather than passing by luck.
    """
    _stub_native(
        containment,
        monkeypatch,
        stdout=stdout,
        returncode=1,
        stderr=stderr,
        repo_visible=False,
    )
    res = containment.resolve_children(
        {}, parent_number=342, corpus=_MIXED_CORPUS, corpus_complete=True
    )
    assert res.native_supported is False
    assert res.complete is True, "a conclusive absence is still a complete answer"


def test_a_422_on_its_status_alone_is_not_an_absent_endpoint(containment, monkeypatch) -> None:
    """#808: 422 is GitHub's generic "Unprocessable Entity". Without a message
    saying the feature is absent it proves nothing about the instance, so the
    read is unreadable — an incomplete answer — never a determinate
    textual-only one."""
    _stub_native(
        containment,
        monkeypatch,
        stdout=json.dumps({"message": "Validation Failed", "status": "422"}),
        returncode=1,
        stderr="gh: Validation Failed (HTTP 422)",
    )
    res = containment.resolve_children(
        {}, parent_number=342, corpus=_MIXED_CORPUS, corpus_complete=True
    )
    assert res.complete is False
    assert res.native_supported is True, "the endpoint is not known to be absent"


def test_a_misread_422_is_not_remembered_as_unsupported_for_the_run(
    containment, monkeypatch
) -> None:
    """The run's reads (`SubIssueReads`) remember each parent's outcome, and a
    caller like `link-parent` plans every child of that parent from it. A 422
    that does not say the feature is absent must not be what it remembers as
    "unsupported" — only a genuine absence is."""
    _stub_native(
        containment,
        monkeypatch,
        stdout="",
        returncode=1,
        stderr="gh: HTTP 422: Unprocessable Entity",
    )
    reads = containment.SubIssueReads({})
    assert reads.read(342).outcome is containment.NativeReadOutcome.UNREADABLE

    _stub_native(
        containment,
        monkeypatch,
        stdout=_ABSENT_422_BODY,
        returncode=1,
        stderr="gh: Validation Failed (HTTP 422)",
    )
    assert reads.read(343).outcome is containment.NativeReadOutcome.UNSUPPORTED


# --- the full attribution table (#869) ---------------------------------------


def _classify(containment, monkeypatch, *, stderr: str, repo_visible: bool, stdout: str = ""):
    """Run the failure classifier with the parent-issue probe stubbed."""

    def fake_gh(args, config):
        if "sub_issues" in " ".join(args):
            return subprocess.CompletedProcess(args, 1, stdout=stdout, stderr=stderr)
        return subprocess.CompletedProcess(args, 0 if repo_visible else 1, stdout="342", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    return containment._classify_native_failure({}, parent_number=342, stderr=stderr, stdout=stdout)


@pytest.mark.parametrize(
    "stdout, stderr, repo_visible, expected, why",
    [
        # Unchanged by #808: 410 is conclusive by status, and 404 is probed.
        ("", "gh: HTTP 410: Gone", False, "UNSUPPORTED", "410 needs no probe"),
        # A 422 is read by its message (#808), and never probed.
        (
            _ABSENT_422_BODY,
            "gh: Validation Failed (HTTP 422)",
            False,
            "UNSUPPORTED",
            "a 422 whose message says the feature is absent needs no probe",
        ),
        (
            "",
            "gh: HTTP 422: Unprocessable Entity",
            True,
            "UNREADABLE",
            "a 422 on its status alone is not absence",
        ),
        (
            json.dumps({"message": "Sub issue may only have one parent", "status": "422"}),
            "gh: Sub issue may only have one parent (HTTP 422)",
            True,
            "UNREADABLE",
            "the one-parent rule is not absence",
        ),
        (
            "",
            "gh: Sub-issue not found (HTTP 422)",
            True,
            "UNREADABLE",
            "a 422 saying 'not found' is not gh's code-less 404, so it is not probed",
        ),
        # Ambiguous: same status, opposite meanings, settled by the probe.
        (
            "",
            "gh: HTTP 404: Not Found (https://api.github.com/repos/o/r/issues/342/sub_issues)",
            True,
            "UNSUPPORTED",
            "404 + parent visible -> the endpoint is absent",
        ),
        (
            "",
            "gh: HTTP 404: Not Found (https://api.github.com/repos/o/r/issues/342/sub_issues)",
            False,
            "UNREADABLE",
            "404 + parent unreachable -> a visibility fault",
        ),
        # gh's code-less phrasing of the same ambiguity, per the predicate's own note.
        ("", "gh: Not Found", True, "UNSUPPORTED", "bare not-found + parent visible"),
        ("", "gh: Not Found", False, "UNREADABLE", "bare not-found + parent unreachable"),
        # Never ambiguous, so never probed.
        ("", "gh: HTTP 401: Bad credentials", True, "UNREADABLE", "auth is not absence"),
        ("", "error connecting to api.github.com", True, "UNREADABLE", "network is not absence"),
    ],
)
def test_native_failure_attribution(
    containment,
    monkeypatch,
    stdout: str,
    stderr: str,
    repo_visible: bool,
    expected: str,
    why: str,
) -> None:
    """Every classification case, pinned against realistic `gh` output.

    The two 404 rows are the point: identical text, opposite verdicts, decided by
    whether the repository can be seen at all. A fine-grained token missing
    `Issues: read` returns 404 rather than 401 on a private repo, so without the
    probe that row reads as "this instance has no sub-issues" and a close gate
    answers from the textual side alone (#869). The 422 rows are #808's: the
    status alone decides nothing, the message does.
    """
    outcome = _classify(
        containment, monkeypatch, stderr=stderr, repo_visible=repo_visible, stdout=stdout
    )
    assert outcome.name == expected, why
