"""The native sub-issue (containment) link sole-constructor seam.

DEC-005 makes GitHub's native sub-issues field the canonical containment
mechanism: every parent-link mutation sets the native link in addition to the
textual first-line parent-ref. ``_lib/containment`` is the **sole constructor**
of that native write (``gh api repos/.../issues/<parent>/sub_issues`` POST),
applying ADR-031's sole-constructor discipline to a third non-label substrate
(distinct from the field-value / milestone writes ``_lib/substrate_writes``
covers). Two halves, both required to make the invariant structural:

  * **Half (a) — the construction + behaviour test**: the primitive constructs
    the covered write, resolves the child's database id, is idempotent by
    value-equality, and degrades to a no-op on an unsupported instance.
  * **Half (b) — the grep/AST guard**: no script string-builds the
    ``gh api …/sub_issues`` POST inline except the sole-constructor module.

The guard recognises the OPERATION (``gh api`` carrying a ``…/sub_issues`` POST
path), not bare token membership — the same operation-shaped recognition the
substrate-write guard uses — so a read (``GET``) or a coincidental mention does
not over-fire, and an inline write anywhere but the seam is caught.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"

# The one allow-listed constructor — the seam itself legitimately builds the
# covered `gh api …/sub_issues` argv; everything else must ask it.
SEAM_MODULE = LIB / "containment.py"


# =========================================================================
# Half (a) — the construction + behaviour test
# =========================================================================


@pytest.fixture(scope="module")
def containment():
    """Load the containment primitive via importlib (sibling _lib import)."""
    if str(LIB) not in sys.path:
        sys.path.insert(0, str(LIB))
    spec = importlib.util.spec_from_file_location(
        "pm_containment_under_test", SEAM_MODULE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_containment_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --- the primitive constructs the covered write --------------------------


def test_add_sub_issue_args_constructs_the_post(containment) -> None:
    args = containment.add_sub_issue_args(parent_number=342, child_database_id=999)
    assert args == [
        "gh", "api",
        "-X", "POST",
        "repos/{owner}/{repo}/issues/342/sub_issues",
        # `-F` (typed integer field), NOT `-f` — the endpoint rejects a string id
        # with HTTP 422; the live-smoke regression that found this is pinned here.
        "-F", "sub_issue_id=999",
    ]


def test_list_sub_issues_args_constructs_the_paginated_get(containment) -> None:
    args = containment.list_sub_issues_args(parent_number=342)
    assert args == [
        "gh", "api",
        "--paginate",
        "repos/{owner}/{repo}/issues/342/sub_issues",
    ]


# --- child database-id resolution (number/node-id are NOT it) ------------


def test_resolve_issue_database_id_reads_integer_id(containment, monkeypatch) -> None:
    """The endpoint keys on the integer DATABASE id, resolved via
    `gh api repos/.../issues/<n> --jq .id` (NOT the node id `gh issue view`
    returns)."""
    captured: dict = {}

    def fake_gh(args, config):
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="4775677101\n", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    assert containment.resolve_issue_database_id({}, issue_number=344) == 4775677101
    # asks the REST issue endpoint with --jq .id (not `gh issue view --json id`).
    assert captured["args"][:2] == ["gh", "api"]
    assert "--jq" in captured["args"]
    assert captured["args"][captured["args"].index("--jq") + 1] == ".id"


def test_resolve_issue_database_id_none_on_failure(containment, monkeypatch) -> None:
    def fake_gh(args, config):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    assert containment.resolve_issue_database_id({}, issue_number=344) is None


def test_resolve_issue_database_id_none_on_non_integer(containment, monkeypatch) -> None:
    def fake_gh(args, config):
        return subprocess.CompletedProcess(args, 0, stdout="not-a-number\n", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    assert containment.resolve_issue_database_id({}, issue_number=344) is None


# --- link_sub_issue: the happy path links the resolved id ----------------


def test_link_sub_issue_links_on_success(containment, monkeypatch) -> None:
    """Resolves the child id, finds no existing link, POSTs the add → LINKED."""
    calls: list[list[str]] = []

    def fake_gh(args, config):
        calls.append(args)
        if "--jq" in args:  # resolve database id
            return subprocess.CompletedProcess(args, 0, stdout="999\n", stderr="")
        if "--paginate" in args:  # list existing sub-issues (none)
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        # the POST add
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.LINKED
    assert result.ok is True
    # the POST carried the resolved database id (typed `-F`), not the number.
    post = next(a for a in calls if "POST" in a)
    assert "-F" in post
    assert post[post.index("-F") + 1] == "sub_issue_id=999"


# --- idempotency: an already-linked child is a value-equality no-op ------


def test_link_sub_issue_already_linked_is_noop(containment, monkeypatch) -> None:
    """When the child's database id is already among the parent's sub-issues,
    skip the add (value-equality idempotency per DEC-026) → ALREADY, ok."""
    posted = {"add": False}

    def fake_gh(args, config):
        if "--jq" in args:
            return subprocess.CompletedProcess(args, 0, stdout="999\n", stderr="")
        if "--paginate" in args:
            # child 999 is already a sub-issue.
            return subprocess.CompletedProcess(
                args, 0, stdout='[{"id": 999, "number": 344}]', stderr=""
            )
        posted["add"] = True  # pragma: no cover — must not be reached
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.ALREADY
    assert result.ok is True
    assert posted["add"] is False, "the add must NOT run when already linked"


# --- graceful degradation: unsupported instance → no-op, not failure -----


@pytest.mark.parametrize("status", [404, 410, 422])
def test_link_sub_issue_unsupported_status_degrades(containment, monkeypatch, status) -> None:
    """A 404 / 410 / 422 from the endpoint means the instance lacks sub-issue
    support — degrade to a no-op (UNSUPPORTED), NOT a failure. The textual ref
    is the fallback."""
    def fake_gh(args, config):
        if "--jq" in args:
            return subprocess.CompletedProcess(args, 0, stdout="999\n", stderr="")
        if "--paginate" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        return subprocess.CompletedProcess(
            args, 1, stdout="", stderr=f"gh: HTTP {status}: not available"
        )

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.UNSUPPORTED
    assert result.ok is False  # the native link is absent...
    assert "unsupported" in result.detail.lower()


def test_link_sub_issue_not_found_phrasing_degrades(containment, monkeypatch) -> None:
    """`gh` sometimes phrases a missing endpoint as "Not Found" without a code —
    still treated as unsupported."""
    def fake_gh(args, config):
        if "--jq" in args:
            return subprocess.CompletedProcess(args, 0, stdout="999\n", stderr="")
        if "--paginate" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="gh: Not Found (HTTP 404)")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.UNSUPPORTED


def test_link_sub_issue_genuine_failure_is_failed_not_unsupported(
    containment, monkeypatch
) -> None:
    """A non-"unsupported" error (auth/network — e.g. HTTP 500) is FAILED, not
    UNSUPPORTED — a genuine problem to report, still non-fatal to the create."""
    def fake_gh(args, config):
        if "--jq" in args:
            return subprocess.CompletedProcess(args, 0, stdout="999\n", stderr="")
        if "--paginate" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="gh: HTTP 500: server error")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.FAILED
    assert result.ok is False


def test_link_sub_issue_unresolvable_child_is_failed(containment, monkeypatch) -> None:
    """If the child's database id cannot be resolved, the link is FAILED (no add
    attempted) — but never raises; the create still has the textual ref."""
    def fake_gh(args, config):
        if "--jq" in args:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom")
        raise AssertionError("must not reach list/add when id resolution fails")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.FAILED


def test_link_sub_issue_missing_gh_binary_is_failed_not_raised(containment, monkeypatch) -> None:
    """A missing `gh` is carried as FAILED, not raised — posture-neutral."""
    state = {"calls": 0}

    def fake_gh(args, config):
        # id resolution succeeds; the add raises FileNotFoundError.
        state["calls"] += 1
        if "--jq" in args:
            return subprocess.CompletedProcess(args, 0, stdout="999\n", stderr="")
        if "--paginate" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        raise FileNotFoundError("gh")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.FAILED


def test_link_proceeds_to_add_when_list_unreadable(containment, monkeypatch) -> None:
    """A failed idempotency READ must NOT wrongly report ALREADY — the linker
    proceeds to the add (whose own outcome is authoritative)."""
    def fake_gh(args, config):
        if "--jq" in args:
            return subprocess.CompletedProcess(args, 0, stdout="999\n", stderr="")
        if "--paginate" in args:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="transient")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.link_sub_issue({}, parent_number=342, child_number=344)
    assert result.outcome == containment.LinkOutcome.LINKED


# --- create-issue obtains the link FROM the primitive --------------------


def _imports_containment(path: Path) -> bool:
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


def test_create_issue_routes_through_the_primitive() -> None:
    """create-issue's --parent path obtains the native link from the primitive
    (half a for the create site), not an inline `gh api …/sub_issues` build."""
    create_src = (SCRIPTS / "create-issue.py").read_text(encoding="utf-8")
    assert _imports_containment(SCRIPTS / "create-issue.py")
    assert "link_sub_issue" in create_src


# =========================================================================
# Render-on-demand textual children view (DEC-039 D4 / ADR-035 section 4)
# =========================================================================
#
# The parent-side children comment: a generated do-not-edit view written by FULL
# OVERWRITE through one construction point (`refresh_children_comment`), refreshed
# by the read path, NEVER an append. Offline — gh is mocked at `_gh_call`.


def _resolution(containment, *natives: int, textuals: tuple[int, ...] = ()):
    """Build a ChildResolution directly (native-wins already applied upstream)."""
    children = [
        containment.ResolvedChild(number=n, substrate=containment.ChildSubstrate.NATIVE)
        for n in natives
    ] + [
        containment.ResolvedChild(number=n, substrate=containment.ChildSubstrate.TEXTUAL)
        for n in textuals
    ]
    children.sort(key=lambda c: c.number)
    return containment.ChildResolution(children=tuple(children), native_supported=True)


# --- the rendered body: marker, content matches resolution ---------------


def test_render_carries_the_do_not_edit_marker(containment) -> None:
    """The rendered body carries the find-existing marker AND a visible
    do-not-edit notice so both a source reader and a comment reader are warned."""
    body = containment.render_children_comment_body(
        parent_number=342, resolution=_resolution(containment, 344)
    )
    assert containment.CHILDREN_VIEW_MARKER in body
    assert "do not edit" in body.lower()


def test_render_content_matches_resolution(containment) -> None:
    """Each resolved child appears as a `#<n>` link; a textual-only child is
    marked `(textual)`, a native child is unmarked (native is the default)."""
    body = containment.render_children_comment_body(
        parent_number=342,
        resolution=_resolution(containment, 344, textuals=(345,)),
        titles={344: "native child", 345: "textual child"},
    )
    assert "- #344 — native child" in body
    assert "_(textual)_" not in body.split("#344", 1)[1].split("\n", 1)[0]
    assert "- #345 — textual child  _(textual)_" in body
    # only the resolved children, no extras.
    assert "#343" not in body and "#346" not in body


def test_render_empty_child_set_is_explicit(containment) -> None:
    """A parent whose children were all removed renders an explicit no-children
    line — an honest current view, not a stale list."""
    body = containment.render_children_comment_body(
        parent_number=342, resolution=_resolution(containment)
    )
    assert containment.CHILDREN_VIEW_MARKER in body
    assert "No children" in body


def test_render_is_deterministic(containment) -> None:
    """Same resolution → byte-identical body — the property the idempotency
    value-equality skip depends on."""
    res = _resolution(containment, 344, 345)
    a = containment.render_children_comment_body(parent_number=342, resolution=res)
    b = containment.render_children_comment_body(parent_number=342, resolution=res)
    assert a == b


# --- the argv constructors (sole-constructor) ----------------------------


def test_create_comment_args_constructs_the_post(containment) -> None:
    args = containment.create_comment_args(parent_number=342, body="hello")
    assert args == [
        "gh", "api",
        "-X", "POST",
        "repos/{owner}/{repo}/issues/342/comments",
        "-f", "body=hello",
    ]


def test_update_comment_args_constructs_the_patch(containment) -> None:
    """The OVERWRITE: a PATCH on the comment id, not a second POST/append."""
    args = containment.update_comment_args(comment_id=99, body="hello")
    assert args == [
        "gh", "api",
        "-X", "PATCH",
        "repos/{owner}/{repo}/issues/comments/99",
        "-f", "body=hello",
    ]


# --- find-existing: the marker round-trips -------------------------------


def _comments_payload(*entries: tuple[int, str]) -> str:
    import json as _json
    body = ", ".join(
        f'{{"id": {cid}, "body": {_json.dumps(text)}}}' for cid, text in entries
    )
    return f"[{body}]"


def test_find_children_comment_round_trips_the_marker(containment, monkeypatch) -> None:
    """A marked comment is found by its marker and its (id, body) returned; an
    unmarked comment is ignored."""
    marked = containment.CHILDREN_VIEW_MARKER + "\n### Children\n- #344\n"

    def fake_gh(args, config):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=_comments_payload((1, "a normal human comment"), (7, marked)),
            stderr="",
        )

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    found = containment.find_children_comment({}, parent_number=342)
    assert found is not None
    assert found[0] == 7
    assert containment.CHILDREN_VIEW_MARKER in found[1]


def test_find_children_comment_none_when_absent(containment, monkeypatch) -> None:
    def fake_gh(args, config):
        return subprocess.CompletedProcess(
            args, 0, stdout=_comments_payload((1, "just chatter")), stderr=""
        )

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    assert containment.find_children_comment({}, parent_number=342) is None


# --- refresh: native-mode no-op ------------------------------------------


def test_refresh_native_mode_is_noop(containment, monkeypatch) -> None:
    """In native mode the writer is a no-op (the native panel suffices) — no gh
    call at all, the single mode gate."""
    def fake_gh(args, config):  # pragma: no cover — must not be reached
        raise AssertionError("native mode must not touch gh")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.refresh_children_comment(
        {}, parent_number=342, corpus={}, containment_mode="native"
    )
    assert result.outcome is containment.RefreshOutcome.SKIPPED
    assert result.ok is True


# --- refresh: create when absent, overwrite (not append) when present ----


def test_refresh_creates_when_no_marked_comment(containment, monkeypatch) -> None:
    """Textual mode, no existing marked comment → POST a new comment (CREATED)."""
    calls: list[list[str]] = []

    def fake_gh(args, config):
        calls.append(args)
        if "/comments" in " ".join(args) and "--paginate" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if "--paginate" in args:  # native sub_issues read → unsupported (textual)
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.refresh_children_comment(
        {}, parent_number=342, corpus={344: "Feature: #342\n"}, containment_mode="textual"
    )
    assert result.outcome is containment.RefreshOutcome.CREATED
    # exactly one comment WRITE, and it is a POST to .../comments (not a PATCH).
    writes = [c for c in calls if "POST" in c and "/comments" in " ".join(c)]
    assert len(writes) == 1


def test_refresh_overwrites_existing_marked_comment_not_appends(
    containment, monkeypatch
) -> None:
    """Textual mode, an existing marked comment whose body is STALE → PATCH it in
    place (UPDATED). NEVER a second POST — overwrite, not append."""
    calls: list[list[str]] = []
    stale = containment.CHILDREN_VIEW_MARKER + "\nstale content\n"

    def fake_gh(args, config):
        calls.append(args)
        joined = " ".join(args)
        if "/comments" in joined and "--paginate" in args:
            return subprocess.CompletedProcess(
                args, 0, stdout=_comments_payload((55, stale)), stderr=""
            )
        if "--paginate" in args:  # native read → textual fallback
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.refresh_children_comment(
        {}, parent_number=342, corpus={344: "Feature: #342\n"}, containment_mode="textual"
    )
    assert result.outcome is containment.RefreshOutcome.UPDATED
    # the write is a PATCH on the comment id — NOT a POST (which would append).
    patches = [c for c in calls if "PATCH" in c]
    posts = [c for c in calls if "POST" in c and "/comments" in " ".join(c)]
    assert len(patches) == 1
    assert "repos/{owner}/{repo}/issues/comments/55" in patches[0]
    assert posts == [], "a refresh must overwrite, never post a second comment"


# --- refresh: idempotent (same child set → no write) ---------------------


def test_refresh_idempotent_when_body_unchanged(containment, monkeypatch) -> None:
    """When the existing marked comment's body equals the freshly-rendered body,
    skip the write (UNCHANGED) — no comment-edit churn on a re-render."""
    # Render the body the same way the refresh will, so the existing comment is
    # byte-equal to what would be written.
    res = _resolution(containment, textuals=(344,))
    current = containment.render_children_comment_body(parent_number=342, resolution=res)
    calls: list[list[str]] = []

    def fake_gh(args, config):
        calls.append(args)
        joined = " ".join(args)
        if "/comments" in joined and "--paginate" in args:
            return subprocess.CompletedProcess(
                args, 0, stdout=_comments_payload((55, current)), stderr=""
            )
        if "--paginate" in args:  # native read → textual fallback
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404")
        raise AssertionError("no write must happen on an unchanged body")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.refresh_children_comment(
        {}, parent_number=342, corpus={344: "Feature: #342\n"}, containment_mode="textual"
    )
    assert result.outcome is containment.RefreshOutcome.UNCHANGED
    assert not any("PATCH" in c or "POST" in c for c in calls)


def test_refresh_content_matches_resolve_children(containment, monkeypatch) -> None:
    """The written body reflects exactly what resolve_children resolves from the
    corpus — the comment is a derived view of the seam, not an independent scan."""
    captured: dict = {}

    def fake_gh(args, config):
        joined = " ".join(args)
        if "/comments" in joined and "--paginate" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if "--paginate" in args:  # native read → textual fallback
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404")
        # the POST create — capture the body argument.
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    corpus = {344: "Feature: #342\n", 345: "Feature: #342\n", 999: "unrelated\n"}
    containment.refresh_children_comment(
        {}, parent_number=342, corpus=corpus, containment_mode="textual"
    )
    body_field = next(a for a in captured["args"] if a.startswith("body="))
    assert "#344" in body_field and "#345" in body_field
    assert "#999" not in body_field  # not a child of 342


# --- refresh: failure-posture-neutral ------------------------------------


def test_refresh_failed_read_is_failed_not_duplicate_post(containment, monkeypatch) -> None:
    """A failed comment-LIST read must NOT be treated as 'no comment' (which would
    duplicate-post) — it is FAILED, non-fatal to the caller."""
    def fake_gh(args, config):
        joined = " ".join(args)
        if "/comments" in joined and "--paginate" in args:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="transient")
        if "--paginate" in args:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404")
        raise AssertionError("must not write when the comment list is unreadable")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.refresh_children_comment(
        {}, parent_number=342, corpus={344: "Feature: #342\n"}, containment_mode="textual"
    )
    assert result.outcome is containment.RefreshOutcome.FAILED
    assert result.ok is False


def test_refresh_write_failure_is_failed_not_raised(containment, monkeypatch) -> None:
    def fake_gh(args, config):
        joined = " ".join(args)
        if "/comments" in joined and "--paginate" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if "--paginate" in args:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 500")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    result = containment.refresh_children_comment(
        {}, parent_number=342, corpus={344: "Feature: #342\n"}, containment_mode="textual"
    )
    assert result.outcome is containment.RefreshOutcome.FAILED


def test_create_issue_routes_children_view_through_the_primitive() -> None:
    """create-issue's textual-mode --parent path obtains the children-view refresh
    from the primitive (half a for the create site), not an inline comment build."""
    create_src = (SCRIPTS / "create-issue.py").read_text(encoding="utf-8")
    assert "refresh_children_comment" in create_src


# =========================================================================
# Half (b) — the grep/AST guard
# =========================================================================
#
# Recognises the covered write OPERATIONS over a resolved argv:
#   (1) `gh api` carrying a `…/sub_issues` POST path (the native containment
#       link write — #344), and
#   (2) `gh api` carrying a `…/comments` POST-or-PATCH path (the render-on-demand
#       textual children-view write — DEC-039 D4 / ADR-035 section 4).
# Both are constructed ONLY by the seam (`_lib/containment.py`); any inline build
# elsewhere is flagged. A read (no POST/PATCH marker) does not match; a
# coincidental token list does not match; `gh issue comment` (a different verb,
# used by handoff for an APPEND audit comment, not the `gh api` children-view
# write) is not the covered operation and does not match.


GH = "gh"
API_SUBCOMMAND = "api"
SUB_ISSUES_PATH_MARKER = "/sub_issues"
COMMENTS_PATH_MARKER = "/comments"
POST_MARKERS = ("POST",)
# The children-view write is the OVERWRITE (PATCH) of an existing comment OR the
# POST of the first one — both are the covered children-view write operation.
COMMENT_WRITE_MARKERS = ("POST", "PATCH")


def _all_scanned_scripts() -> list[Path]:
    return [
        p
        for p in sorted(SCRIPTS.rglob("*.py"))
        if p != SEAM_MODULE and "__pycache__" not in p.parts
    ]


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _resolve_element(node: ast.AST, names: dict[str, str]) -> str | None:
    """Resolve one argv element to its literal text, or None (opaque).

    Handles bare constants, names bound to string literals, f-strings (the
    literal text around interpolations), `.format`, `%`, and `+` concatenation —
    the same shapes the substrate-write guard resolves, scoped to what a
    sub-issues argv plausibly uses (the path is an f-string `f"repos/.../{n}/sub_issues"`).
    """
    text = _const_str(node)
    if text is not None:
        return text
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if isinstance(node, ast.JoinedStr):
        return "".join(
            t for t in (_const_str(p) for p in node.values) if t is not None
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return _const_str(node.left)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_element(node.left, names)
        right = _resolve_element(node.right, names)
        return (left or "") + (right or "") if (left or right) else None
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "format":
            return _resolve_element(func.value, names)
    return None


def _resolve_sequence(node: ast.AST, names: dict[str, str]) -> list[str | None] | None:
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_resolve_element(e, names) for e in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_sequence(node.left, names)
        right = _resolve_sequence(node.right, names)
        if left is not None or right is not None:
            return (left or [None]) + (right or [None])
    return None


def _collect_string_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            text = _const_str(node.value)
            if text is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = text
    return bindings


def _collect_accumulated_argvs(
    tree: ast.AST, names: dict[str, str]
) -> list[tuple[int, list[str | None]]]:
    """Resolve list variables assembled across statements via `.extend`/`.append`.

    Per-scope (module body + each function body), seeding each name from its
    initial sequence assignment and folding literal `.extend`/`.append` calls. A
    `.extend`/`.append` whose argument is a CALL contributes an opaque element —
    so a seam-routed splice is not seen as a literal POST while an inline literal
    splice is. Mirrors the substrate-write guard's accumulation tracker, scoped
    to the shapes this guard needs.
    """
    out: list[tuple[int, list[str | None]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        accumulated: dict[str, list[str | None]] = {}
        seed_lines: dict[str, int] = {}
        _fold_block(node.body, names, accumulated, seed_lines)
        for name, seq in accumulated.items():
            out.append((seed_lines.get(name, 0), seq))
    return out


_NESTED_BLOCK_ATTRS = ("body", "orelse", "finalbody", "handlers")


def _fold_block(
    body: list[ast.stmt],
    names: dict[str, str],
    accumulated: dict[str, list[str | None]],
    seed_lines: dict[str, int],
) -> None:
    for stmt in body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    seq = _resolve_sequence(stmt.value, names)
                    if seq is not None:
                        accumulated[target.id] = list(seq)
                        seed_lines[target.id] = stmt.lineno
            continue
        call = _expr_call(stmt)
        if call is not None:
            _fold_accumulation_call(call, names, accumulated)
            continue
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for attr in _NESTED_BLOCK_ATTRS:
            nested = getattr(stmt, attr, None)
            if not nested:
                continue
            for item in nested:
                if isinstance(item, ast.ExceptHandler):
                    _fold_block(item.body, names, accumulated, seed_lines)
                elif isinstance(item, ast.stmt):
                    _fold_block([item], names, accumulated, seed_lines)


def _fold_accumulation_call(
    call: ast.Call,
    names: dict[str, str],
    accumulated: dict[str, list[str | None]],
) -> None:
    func = call.func
    if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)):
        return
    name = func.value.id
    if name not in accumulated or not call.args:
        return
    if func.attr == "extend":
        seq = _resolve_sequence(call.args[0], names)
        accumulated[name].extend(seq if seq is not None else [None])
    elif func.attr == "append":
        accumulated[name].append(_resolve_element(call.args[0], names))


def _expr_call(stmt: ast.stmt) -> ast.Call | None:
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return stmt.value
    return None


def _literals(elements: list[str | None]) -> list[str]:
    return [e for e in elements if e is not None]


def _has_subsequence(literals: list[str], sub: tuple[str, ...]) -> bool:
    if not sub:
        return True
    n = len(sub)
    return any(tuple(literals[i:i + n]) == sub for i in range(len(literals) - n + 1))


def _is_sub_issue_write(elements: list[str | None]) -> bool:
    """`gh api … POST …/sub_issues` recognised as an operation.

    Requires the `gh api` subcommand run, a literal carrying the `/sub_issues`
    path, AND a POST marker (`-X POST` or a `POST` token). A bare `gh api
    …/sub_issues` GET (the idempotency LIST read) lacks the POST marker and does
    NOT match — only the WRITE is covered.
    """
    literals = _literals(elements)
    if not _has_subsequence(literals, (GH, API_SUBCOMMAND)):
        return False
    has_path = any(SUB_ISSUES_PATH_MARKER in lit for lit in literals)
    has_post = any(marker in literals for marker in POST_MARKERS)
    return has_path and has_post


def _is_children_comment_write(elements: list[str | None]) -> bool:
    """`gh api … POST|PATCH …/comments` recognised as an operation.

    The render-on-demand children-view write (DEC-039 D4 / ADR-035 section 4):
    requires the `gh api` subcommand run, a literal carrying the `/comments`
    path, AND a POST or PATCH marker (the create or the overwrite). A bare `gh api
    --paginate …/comments` GET (the find-existing LIST read) lacks the write
    marker and does NOT match — only the WRITE is covered. `gh issue comment`
    (handoff's append audit comment) is a different verb (`issue comment`, not
    `api`) and is not the covered operation.
    """
    literals = _literals(elements)
    if not _has_subsequence(literals, (GH, API_SUBCOMMAND)):
        return False
    has_path = any(COMMENTS_PATH_MARKER in lit for lit in literals)
    has_write = any(marker in literals for marker in COMMENT_WRITE_MARKERS)
    return has_path and has_write


def _candidate_argvs(
    tree: ast.AST,
    names: dict[str, str],
    accumulated: list[tuple[int, list[str | None]]],
) -> list[tuple[int, list[str | None]]]:
    out: list[tuple[int, list[str | None]]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.BinOp)):
            seq = _resolve_sequence(node, names)
            if seq is not None:
                out.append((node.lineno, seq))
    out.extend(accumulated)
    return out


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = _collect_string_bindings(tree)
    accumulated = _collect_accumulated_argvs(tree, names)
    out: list[str] = []
    seen: set[int] = set()
    for lineno, elements in _candidate_argvs(tree, names, accumulated):
        if lineno in seen:
            continue
        if _is_sub_issue_write(elements):
            seen.add(lineno)
            out.append(
                f"{path.name}:{lineno}: inline native sub-issue write "
                f"(`gh api … POST …/sub_issues`) — route through "
                f"_lib.containment.add_sub_issue_args / link_sub_issue"
            )
        elif _is_children_comment_write(elements):
            seen.add(lineno)
            out.append(
                f"{path.name}:{lineno}: inline children-view comment write "
                f"(`gh api … POST|PATCH …/comments`) — route through "
                f"_lib.containment.create_comment_args / update_comment_args / "
                f"refresh_children_comment"
            )
    return out


@pytest.mark.parametrize(
    "path", _all_scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS))
)
def test_no_inline_sub_issue_write_construction(path: Path) -> None:
    """No pm script string-builds the native sub-issue write outside the seam."""
    violations = _violations(path)
    assert not violations, (
        "native sub-issue write constructed outside the sole-constructor seam:\n  "
        + "\n  ".join(violations)
    )


def test_seam_module_is_the_one_allow_listed_constructor() -> None:
    """The seam itself builds the covered argv — excluded from the scan by name;
    this pins that it is the one place the construction lives."""
    assert SEAM_MODULE.exists()
    assert _violations(SEAM_MODULE), (
        "the seam must be the constructor of the sub-issue write — if empty, the "
        "construction has moved out of the seam"
    )


def _violations_for_source(tmp_path: Path, name: str, src: str) -> list[str]:
    p = tmp_path / name
    p.write_text(src, encoding="utf-8")
    return _violations(p)


def test_guard_detects_clean_list_literal_sub_issue_write(tmp_path: Path) -> None:
    bad = _violations_for_source(
        tmp_path, "bad.py",
        'args = ["gh", "api", "-X", "POST", '
        '"repos/{owner}/{repo}/issues/342/sub_issues", "-f", f"sub_issue_id={cid}"]\n',
    )
    assert bad, "guard failed to flag a clean-list inline sub-issue write"


def test_guard_detects_fstring_path_sub_issue_write(tmp_path: Path) -> None:
    """The path is an f-string interpolating the parent number — the literal
    `/sub_issues` text is recovered and recognised."""
    bad = _violations_for_source(
        tmp_path, "bad_fstring.py",
        'args = ["gh", "api", "-X", "POST", '
        'f"repos/{{owner}}/{{repo}}/issues/{parent}/sub_issues", "-f", body]\n',
    )
    assert bad, "guard failed to flag an f-string-path inline sub-issue write"


def test_guard_detects_extend_accumulation_sub_issue_write(tmp_path: Path) -> None:
    """EVASION: `.extend` accumulation. A literal POST spliced across statements
    is caught; a seam-routed `cmd.extend(add_sub_issue_args(...))` is NOT."""
    bad = _violations_for_source(
        tmp_path, "bad_extend.py",
        "cmd = ['gh', 'api', '-X', 'POST']\n"
        "cmd.extend([f'repos/{{owner}}/{{repo}}/issues/{p}/sub_issues'])\n"
        "cmd.extend(['-f', body])\n",
    )
    assert bad, "guard failed to flag a `.extend`-accumulated sub-issue write"

    good = _violations_for_source(
        tmp_path, "good_extend.py",
        "cmd = ['gh', 'api']\n"
        "cmd.extend(add_sub_issue_args(parent_number=p, child_database_id=cid))\n",
    )
    assert not good, "guard wrongly flagged a seam-routed `.extend` splice"


def test_guard_does_not_flag_the_list_read(tmp_path: Path) -> None:
    """The idempotency READ (`gh api --paginate …/sub_issues`, no POST) is NOT a
    covered write — only the WRITE is flagged. A future inline read must stay
    clean."""
    read = _violations_for_source(
        tmp_path, "read.py",
        'args = ["gh", "api", "--paginate", '
        '"repos/{owner}/{repo}/issues/342/sub_issues"]\n',
    )
    assert not read, "guard over-fired on a `/sub_issues` GET read (no POST)"


def test_guard_does_not_overfire_on_coincidental_token_lists(tmp_path: Path) -> None:
    """Operation recognition, not bare token membership: a prose/allowlist list
    mentioning the tokens without the `gh api` + POST + path operation is NOT
    flagged."""
    prose = _violations_for_source(
        tmp_path, "prose.py",
        "HELP = ['POST to /sub_issues to link', 'gh api is the seam']\n",
    )
    assert not prose, "guard over-fired on a prose list mentioning the tokens"


def test_guard_leaves_seam_routed_create_issue_clean() -> None:
    """The live create-issue file routes through the seam — no inline write."""
    assert not _violations(SCRIPTS / "create-issue.py")


# --- children-view comment write: the second covered operation -----------


def test_guard_detects_inline_children_comment_post(tmp_path: Path) -> None:
    """An inline `gh api … POST …/comments` build (the children-view CREATE) is
    flagged — it must route through the seam."""
    bad = _violations_for_source(
        tmp_path, "bad_comment_post.py",
        'args = ["gh", "api", "-X", "POST", '
        '"repos/{owner}/{repo}/issues/342/comments", "-f", f"body={text}"]\n',
    )
    assert bad, "guard failed to flag an inline children-comment POST"


def test_guard_detects_inline_children_comment_patch(tmp_path: Path) -> None:
    """An inline `gh api … PATCH …/comments` build (the children-view OVERWRITE)
    is flagged — the overwrite is as much a covered write as the create."""
    bad = _violations_for_source(
        tmp_path, "bad_comment_patch.py",
        'args = ["gh", "api", "-X", "PATCH", '
        'f"repos/{{owner}}/{{repo}}/issues/comments/{cid}", "-f", body]\n',
    )
    assert bad, "guard failed to flag an inline children-comment PATCH"


def test_guard_does_not_flag_the_comment_list_read(tmp_path: Path) -> None:
    """The find-existing READ (`gh api --paginate …/comments`, no POST/PATCH) is
    NOT a covered write — only the write is flagged."""
    read = _violations_for_source(
        tmp_path, "comment_read.py",
        'args = ["gh", "api", "--paginate", '
        '"repos/{owner}/{repo}/issues/342/comments"]\n',
    )
    assert not read, "guard over-fired on a `/comments` GET read (no write marker)"


def test_guard_does_not_flag_gh_issue_comment_verb(tmp_path: Path) -> None:
    """`gh issue comment` (handoff's append audit comment) is a DIFFERENT verb,
    not the `gh api …/comments` children-view write — it must not be flagged."""
    other = _violations_for_source(
        tmp_path, "issue_comment.py",
        'cmd = ["gh", "issue", "comment", str(n), "--body", body]\n',
    )
    assert not other, "guard over-fired on `gh issue comment` (a different verb)"


def test_seam_constructs_the_children_comment_write() -> None:
    """The seam is the one place the children-comment write is built — it MUST
    contain a covered children-comment write construction (excluded from the scan
    by name)."""
    src = SEAM_MODULE.read_text(encoding="utf-8")
    assert "/comments" in src and "PATCH" in src
