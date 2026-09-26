"""Audit-comment idempotence across every keyed writer (#901, #902).

Each audit comment `move-issue`, `done-work`, `merge-pr` and `handoff-issue`
post closes with an `<!-- pkit-audit-key: <writer>:<digest> -->` line hashed
from what identifies the specific audited act, so distinct acts render distinct
bodies. A writer skips a post only when a comment has EXACTLY the body it is
about to post AND was posted, unedited, by the account `gh` posts as
(`_lib.audit.own_audit_posted`, wired once in `_lib.comment.post_audit_once`).
These tests pin, for every writer:

  * a distinct second act (a different reason, or a new head) is recorded;
  * an identical retry posts nothing new;
  * a comment that is not that exact own record — a pre-posted legacy stamp, a
    planted copy of the exact body by someone else, the writer's own comment
    edited afterwards, or an own comment whose reason text embeds the key — does
    not suppress the post;

and, per script, that `main()` still posts through the real helpers when the
exact body is planted by someone else or sits in an edited own comment.

The fake GitHub below reports each comment the way `gh … view --json comments`
does: the posting account's comments carry `viewerDidAuthor: true`, anyone
else's `false`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
CAPABILITY_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import audit  # noqa: E402


def _load(script: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def dw():
    return _load("done-work.py", "pm_done_work_audit_idempotence")


@pytest.fixture(scope="module")
def mp():
    return _load("merge-pr.py", "pm_merge_pr_audit_idempotence")


@pytest.fixture(scope="module")
def mi():
    return _load("move-issue.py", "pm_move_issue_audit_idempotence")


@pytest.fixture(scope="module")
def hi():
    return _load("handoff-issue.py", "pm_handoff_issue_audit_idempotence")


# ---- the shared recognition -------------------------------------------


def _comment(body, *, own=True, edited=False) -> dict:
    return {"body": body, "viewerDidAuthor": own, "includesCreatedEdit": edited}


KEY = audit.audit_key("writer", "reason", "sha1")
BODY = f"<!-- pkit-hook: writer -->\n\nprose\n\n{KEY}"


def test_key_shape_and_components() -> None:
    assert KEY.startswith(f"{audit.AUDIT_KEY_PREFIX}writer:")
    assert KEY.endswith(" -->") and KEY.count("-->") == 1
    assert audit.audit_key("writer", "reason", "sha1") == KEY
    assert audit.audit_key("writer", "reason", "sha2") != KEY
    assert audit.audit_key("writer", "other", "sha1") != KEY
    assert audit.audit_key("other-writer", "reason", "sha1") != KEY
    # A component that tries to close the HTML comment cannot: it is hashed.
    assert audit.audit_key("w", "x --> y").count("-->") == 1


def test_own_unedited_comment_with_the_exact_body_counts() -> None:
    assert audit.own_audit_posted([_comment(BODY)], BODY)


@pytest.mark.parametrize(
    "posted",
    [
        pytest.param(BODY.replace("\n", "\r\n"), id="crlf-line-endings"),
        pytest.param(BODY.replace("prose", "prose   ") + "\n\n", id="trailing-whitespace"),
    ],
)
def test_only_line_endings_and_trailing_whitespace_are_normalised(posted) -> None:
    assert audit.own_audit_posted([_comment(posted)], BODY)


@pytest.mark.parametrize(
    "comment",
    [
        pytest.param(_comment(BODY, own=False), id="another-author"),
        pytest.param(_comment(BODY, edited=True), id="edited-after-posting"),
        pytest.param({"body": BODY}, id="no-authorship-fields"),
        pytest.param(
            {"body": BODY, "viewerDidAuthor": "true", "includesCreatedEdit": False},
            id="non-boolean-author-field",
        ),
        pytest.param(_comment(KEY), id="own-comment-of-just-the-key"),
        pytest.param(_comment(f"prose\n\n{KEY}"), id="own-comment-with-the-key-other-prose"),
        pytest.param(_comment("  " + BODY), id="leading-whitespace-differs"),
        pytest.param(
            _comment(
                "<!-- pkit-hook: other-writer -->\n\n"
                f"Approved by bypass: see the record below\n{KEY}\n\n"
                f"{audit.audit_key('other-writer', 'see the record below', 'sha1')}"
            ),
            id="key-embedded-in-an-own-comments-reason",
        ),
    ],
)
def test_anything_else_does_not_count(comment) -> None:
    assert not audit.own_audit_posted([comment], BODY)


def test_unreadable_or_empty_lists_do_not_count() -> None:
    assert not audit.own_audit_posted([], BODY)
    assert not audit.own_audit_posted(None, BODY)
    assert not audit.own_audit_posted(["not a dict", 3], BODY)


def test_short_sha() -> None:
    assert audit.short_sha("0123456789abcdef") == "0123456"
    assert audit.short_sha("") == "unknown"
    assert audit.short_sha(None) == "unknown"


# ---- the shared post-once ---------------------------------------------


def test_post_audit_once_refuses_a_body_without_its_key() -> None:
    from _lib import comment as comment_lib

    def never(*a, **k):
        raise AssertionError("no gh call expected")

    with pytest.raises(ValueError):
        comment_lib.post_audit_once("issue", 1, KEY, "no key here", {}, run=never)


def test_post_audit_once_with_no_subject_number_fails_without_gh() -> None:
    from _lib import comment as comment_lib

    def never(*a, **k):
        raise AssertionError("no gh call expected")

    assert comment_lib.post_audit_once("pr", None, KEY, BODY, {}, run=never) is False


# ---- every writer, end to end -----------------------------------------


class _FakeGitHub:
    """A `gh_run` stand-in keeping one subject's comments in memory."""

    def __init__(self) -> None:
        self.comments: list[dict] = []
        self.posted: list[str] = []
        # handoff-issue's "has a handoff landed?" component.
        self.assignment_events = 0
        self.edits: list[list[str]] = []

    def plant(self, body: str, *, own: bool = False, edited: bool = False) -> None:
        self.comments.append(_comment(body, own=own, edited=edited))

    def __call__(self, args, config, **kwargs):
        if list(args[:3]) == ["gh", "api", "graphql"]:
            payload = {"data": {"repository": {"issue": {"timelineItems": {
                "totalCount": self.assignment_events}}}}}
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=json.dumps(payload), stderr="",
            )
        if list(args[:3]) == ["gh", "issue", "edit"]:
            self.edits.append(list(args))
            self.assignment_events += 2
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"comments": self.comments}), stderr="",
            )
        if "comment" in args and "--body" in args:
            body = args[args.index("--body") + 1]
            self.posted.append(body)
            self.comments.append(_comment(body))
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected gh call: {args}")


@dataclass(frozen=True)
class _Writer:
    """One audit writer, reduced to: post an act identified by (reason, scope)."""

    module: str
    post: Callable[..., bool]
    # The fixed, non-keyed stamp this writer recognised before #902 — the
    # string any commenter could post to suppress the record.
    legacy_stamp: str


def _identity(module):
    return module.Identity(github_login="alice", email="alice@example.test")


def _dw_bypass(dw, reason, scope):
    return dw._post_bypass_audit_idempotent(42, reason, {}, head=scope)


def _dw_ci_bypass(dw, reason, scope):
    return dw._post_ci_bypass_audit(
        7, reason, _identity(dw), ("tests (FAILURE)",), {}, head=scope,
    )


def _dw_reviewer_override(dw, reason, scope):
    audit_rec = dw._OverrideAudit(
        reviewer="design-reviewer", capability=None,
        state="none (no verdict the gate counts)", block_comment_url=None,
        head=scope,
    )
    return dw._post_reviewer_override_audit(7, audit_rec, reason, _identity(dw), {})


def _mp_ci_bypass(mp, reason, scope):
    return mp._post_ci_bypass_audit(
        7, reason, _identity(mp), ("tests (FAILURE)",), {}, head=scope,
    )


def _mi_transition(mi, reason, scope):
    # move-issue's scope component is the engine-journal length (#901). The
    # reason is stripped before rendering, as `main` does.
    journal_length = int(scope.removeprefix("sha"))
    reason = reason.strip()
    key = mi._transition_audit_key("todo", "backlog", reason, journal_length)
    invoker = SimpleNamespace(github_login="alice", email="alice@example.test")
    body = mi._render_audit_comment(CAPABILITY_ROOT, invoker, reason) + "\n\n" + key
    return mi._post_transition_audit_once(42, body, key, {})


def _hi_handoff(hi, reason, scope):
    # handoff-issue's scope component is the assignment-event count, read from
    # the fake's timeline: `sha<n>` plants n events before the post.
    hi.gh_run.assignment_events = int(scope.removeprefix("sha"))
    return hi._post_handoff_audit(42, "alice", "bob", reason, {})


WRITERS = {
    "done-work-bypass": _Writer(
        "dw", _dw_bypass, "<!-- pkit-hook: done-work-bypass -->"),
    "done-work-ci-bypass": _Writer(
        "dw", _dw_ci_bypass, "<!-- pkit-hook: done-work-ci-bypass -->"),
    "done-work-reviewer-override": _Writer(
        "dw", _dw_reviewer_override, "<!-- pkit-hook: done-work-reviewer-override"),
    "merge-pr-ci-bypass": _Writer(
        "mp", _mp_ci_bypass, "<!-- pkit-hook: merge-pr-ci-bypass -->"),
    "move-issue": _Writer(
        "mi", _mi_transition, "<!-- pkit-audit-key: move-issue:"),
    "handoff-issue": _Writer(
        "hi", _hi_handoff, "<!-- pkit-hook: handoff-issue:alice->bob -->"),
}


@pytest.fixture(params=sorted(WRITERS))
def writer(request, dw, mp, mi, hi, monkeypatch):
    spec = WRITERS[request.param]
    module = {"dw": dw, "mp": mp, "mi": mi, "hi": hi}[spec.module]
    gh = _FakeGitHub()
    monkeypatch.setattr(module, "gh_run", gh)

    def post(reason, scope="sha1"):
        return spec.post(module, reason, scope)

    return post, gh, spec


def test_identical_retry_posts_nothing_new(writer) -> None:
    post, gh, _ = writer
    assert post("flaky check") is True
    # Cosmetic whitespace in the reason is the same act.
    assert post("  flaky check ") is True
    assert len(gh.posted) == 1


def test_a_different_reason_is_recorded(writer) -> None:
    post, gh, _ = writer
    assert post("flaky check") is True
    assert post("release deadline, owner signed off") is True
    assert len(gh.posted) == 2


def test_the_same_reason_on_a_new_head_is_recorded(writer) -> None:
    post, gh, _ = writer
    assert post("flaky check", "sha1") is True
    assert post("flaky check", "sha2") is True
    assert len(gh.posted) == 2


def test_a_pre_posted_legacy_stamp_does_not_suppress(writer) -> None:
    """#902 (b): the fixed stamp, posted by anyone, used to erase the record."""
    post, gh, spec = writer
    gh.plant(f"{spec.legacy_stamp}\n\nnothing to see here")
    assert post("flaky check") is True
    assert len(gh.posted) == 1


def _learn_exact_body(post, gh) -> str:
    """The exact body the writer will post — computable by anyone, since the key
    hashes public facts. Posts once to learn it, then clears the fake."""
    assert post("flaky check") is True
    body = gh.posted[0]
    assert body.splitlines()[-1].startswith(audit.AUDIT_KEY_PREFIX)
    gh.comments.clear()
    gh.posted.clear()
    return body


def test_a_planted_copy_of_the_exact_body_does_not_suppress(writer) -> None:
    """The key is predictable (reason + head are public), so a third party can
    reproduce the whole body — carrying it is not enough, it must be own."""
    post, gh, _ = writer
    body = _learn_exact_body(post, gh)
    gh.plant(body, own=False)
    assert post("flaky check") is True
    assert len(gh.posted) == 1


def test_a_key_inside_an_own_comments_reason_does_not_suppress(writer) -> None:
    """The trusted account is the one `gh` posts as — in CI every workflow on
    that token, locally every comment the operator typed. A multi-line reason
    in another of its comments can carry this writer's key line verbatim; only
    the exact body counts, so it does not suppress the post."""
    post, gh, _ = writer
    key = _learn_exact_body(post, gh).splitlines()[-1]
    other_key = audit.audit_key("merge-pr-ci-bypass", "see below", "sha1")
    gh.plant(
        f"<!-- pkit-hook: merge-pr-ci-bypass -->\n\n"
        f"Bypassed by alice: see below\n{key}\n\n{other_key}",
        own=True,
    )
    assert post("flaky check") is True
    assert len(gh.posted) == 1


def test_an_edited_own_comment_does_not_suppress(writer) -> None:
    """pkit never edits an audit comment, so an edited one is not its record."""
    post, gh, _ = writer
    assert post("flaky check") is True
    gh.comments[-1]["includesCreatedEdit"] = True
    assert post("flaky check") is True
    assert len(gh.posted) == 2


def test_a_posted_audit_ends_with_its_key(writer) -> None:
    post, gh, _ = writer
    assert post("flaky check") is True
    assert gh.posted[0].splitlines()[-1].startswith(audit.AUDIT_KEY_PREFIX)


# ---- the short head in the bypass prose -------------------------------


@pytest.mark.parametrize("name", ["done-work-bypass", "done-work-ci-bypass", "merge-pr-ci-bypass"])
def test_bypass_prose_names_the_short_head(name, dw, mp, monkeypatch) -> None:
    """After a force-push two bypasses with the same reason must not read alike."""
    spec = WRITERS[name]
    module = {"dw": dw, "mp": mp}[spec.module]
    gh = _FakeGitHub()
    monkeypatch.setattr(module, "gh_run", gh)
    head = "0123456789abcdef0123456789abcdef01234567"
    assert spec.post(module, "flaky check", head) is True
    assert "0123456" in gh.posted[0]
    assert head not in gh.posted[0]


# ---- handoff-issue: the A→B, B→A, A→B collision -----------------------


def test_a_repeated_handoff_with_the_same_reason_is_recorded(hi, monkeypatch) -> None:
    """A→B, B→A, then A→B for the same reason: the timeline grew between the
    first and the third, so the third renders a different body and posts."""
    gh = _FakeGitHub()
    monkeypatch.setattr(hi, "gh_run", gh)
    assert hi._post_handoff_audit(42, "alice", "bob", "vacation", {})
    assert hi._reassign(42, "alice", "bob", {})
    assert hi._post_handoff_audit(42, "bob", "alice", "back", {})
    assert hi._reassign(42, "bob", "alice", {})
    assert hi._post_handoff_audit(42, "alice", "bob", "vacation", {})
    assert len(gh.posted) == 3


def test_a_retry_after_a_failed_reassign_posts_nothing_new(hi, monkeypatch) -> None:
    """A failed reassignment adds no timeline event, so the retry reproduces the
    comment exactly."""
    gh = _FakeGitHub()
    monkeypatch.setattr(hi, "gh_run", gh)
    assert hi._post_handoff_audit(42, "alice", "bob", "vacation", {})
    assert hi._post_handoff_audit(42, "alice", "bob", " vacation ", {})
    assert len(gh.posted) == 1


def test_an_unreadable_event_count_differs_from_a_readable_one(hi) -> None:
    assert hi._handoff_audit_key("a", "b", "r", None) != hi._handoff_audit_key("a", "b", "r", 0)
    assert hi._handoff_audit_key("a", "b", "r", 0) != hi._handoff_audit_key("a", "b", "r", 2)
    assert hi._handoff_audit_key("a", "b", " r ", 2) == hi._handoff_audit_key("a", "b", "r", 2)


# ---- main(), end to end, through the real post helpers ----------------
#
# One per script. Only the `gh` layer and the non-audit seams (membership,
# guards, merge mechanics, gates unrelated to the audit) are faked; the audit
# path from `main()` down to `_lib.comment.post_audit_once` is the real one.
# Each script runs once on a clean subject to learn the exact audit bodies it
# posts, then again with those bodies planted — by someone else, or as an own
# comment edited afterwards — and must post every audit again.

PLANTINGS = {
    "planted-by-someone-else": {"own": False, "edited": False},
    "own-but-edited": {"own": True, "edited": True},
}


def _allow_member(module, monkeypatch) -> None:
    monkeypatch.setattr(module, "load_adopter_config", lambda root: {})
    monkeypatch.setattr(module, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(
        module, "resolve_invoker_identity",
        lambda config=None: SimpleNamespace(github_login="octocat", email="o@e.com"),
    )
    monkeypatch.setattr(
        module, "check_membership",
        lambda members, invoker: SimpleNamespace(allowed=True, refusal_message=None),
    )
    monkeypatch.setattr(module.session_guard, "enforce", lambda **kw: True)
    monkeypatch.setattr(module.bootstrap_gate, "enforce", lambda *a, **kw: True)


_RED = [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]


def _wire_done_work(dw, monkeypatch) -> None:
    _allow_member(dw, monkeypatch)
    monkeypatch.setattr(dw, "resolve_capability_root", lambda arg: CAPABILITY_ROOT)
    monkeypatch.setattr(dw, "_find_issue_branch", lambda n: "fix/42-slug")
    monkeypatch.setattr(
        dw, "_find_pr_for_branch",
        lambda branch, config: {
            "number": 496, "title": "fix: x", "isDraft": False,
            "headRefOid": "0123456789abcdef",
        },
    )
    monkeypatch.setattr(dw, "_gh_get_issue", lambda n, config: {"labels": [], "body": ""})
    monkeypatch.setattr(
        dw, "resolve_mode",
        lambda config, issue_labels=None: SimpleNamespace(mode="human", source="default"),
    )
    monkeypatch.setattr(
        dw, "_check_approval_gate",
        lambda pr_number, pr, bypass_reason, config: dw._GateResult(
            passed=True, passed_via="bypass", refusal_message="",
        ),
    )
    monkeypatch.setattr(dw, "_gh_get_pr_body", lambda n, config: "## Test plan\n- [x] ok\n")
    monkeypatch.setattr(dw, "_check_pr_placeholder", lambda body, n, root: [])
    monkeypatch.setattr(dw, "_gh_get_status_rollup", lambda n, config: _RED)
    monkeypatch.setattr(dw.pr_merge, "squash_merge", lambda n, **kw: True)
    monkeypatch.setattr(dw.pr_merge, "delete_remote_branch", lambda b, c, **kw: None)
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", lambda b, c, **kw: None)
    monkeypatch.setattr(dw, "_invoke_move_issue", lambda n, target, root: 0)
    monkeypatch.setattr(
        sys, "argv",
        ["done-work.py", "42", "--bypass", "flaky reviewer",
         "--bypass-ci", "advisory guard", "--yes"],
    )


def _wire_merge_pr(mp, monkeypatch) -> None:
    _allow_member(mp, monkeypatch)
    monkeypatch.setattr(mp, "resolve_capability_root", lambda arg: CAPABILITY_ROOT)
    monkeypatch.setattr(
        mp, "_read_yaml",
        lambda path, loader: {"formats": {"pr": {"pattern": r"^fix: .+$"}}},
    )
    monkeypatch.setattr(
        mp, "_gh_get_pr",
        lambda n, config: {
            "title": "fix: a thing", "body": "Closes #42\n## Test plan\n- [x] ok",
            "state": "open", "url": "http://pr/99", "headRefName": "fix/42-slug",
            "headRefOid": "0123456789abcdef", "statusCheckRollup": _RED,
            "isCrossRepository": False,
        },
    )
    monkeypatch.setattr(
        mp, "_gather_unticked_findings", lambda n, body, closing, config: {},
    )
    monkeypatch.setattr(mp.pr_merge, "squash_merge", lambda n, **kw: True)
    monkeypatch.setattr(mp.pr_merge, "delete_remote_branch", lambda b, c, **kw: None)
    monkeypatch.setattr(mp.pr_merge, "cleanup_local", lambda b, c, **kw: None)
    monkeypatch.setattr(mp, "fire_hooks", lambda name, **kw: None)
    monkeypatch.setattr(
        sys, "argv", ["merge-pr.py", "99", "--bypass-ci", "advisory guard", "--yes"],
    )


def _wire_move_issue(mi, monkeypatch) -> None:
    _allow_member(mi, monkeypatch)
    monkeypatch.setattr(mi, "resolve_capability_root", lambda arg: CAPABILITY_ROOT)
    monkeypatch.setattr(
        mi, "_gh_get_issue",
        lambda n, config: {
            "title": "[Task] a thing", "body": "", "state": "OPEN",
            "labels": [{"name": "type:task"}], "milestone": None,
        },
    )
    monkeypatch.setattr(
        mi, "_engine_status",
        lambda n: {"position": {"state": "todo"}, "journal": [{}, {}]},
    )
    monkeypatch.setattr(mi.axis_carriage, "is_board_carried", lambda *a, **kw: False)
    monkeypatch.setattr(mi, "detect_placeholder_residuals", lambda **kw: [])
    monkeypatch.setattr(mi, "_gh_apply_state_label", lambda n, plan, config: True)
    monkeypatch.setattr(mi, "_journal_move", lambda *a, **kw: None)
    monkeypatch.setattr(mi, "fire_hooks", lambda name, **kw: None)
    monkeypatch.setattr(
        sys, "argv",
        ["move-issue.py", "42", "--to", "backlog", "--bypass",
         "--bypass-reason", "verbal PM approval", "--yes", "--no-cascade"],
    )


def _wire_handoff_issue(hi, monkeypatch) -> None:
    _allow_member(hi, monkeypatch)
    monkeypatch.setattr(hi, "resolve_capability_root", lambda arg: CAPABILITY_ROOT)
    monkeypatch.setattr(
        hi, "_gh_get_issue",
        lambda n, config: {"state": "OPEN", "assignees": [{"login": "alice"}]},
    )
    monkeypatch.setattr(
        sys, "argv",
        ["handoff-issue.py", "42", "--to", "@bob", "--reason", "vacation", "--yes"],
    )


# script → (module fixture name, wiring, how many audit comments one run posts)
MAIN_SCRIPTS = {
    "done-work": ("dw", _wire_done_work, 2),
    "merge-pr": ("mp", _wire_merge_pr, 1),
    "move-issue": ("mi", _wire_move_issue, 1),
    "handoff-issue": ("hi", _wire_handoff_issue, 1),
}


@pytest.mark.parametrize("planting", sorted(PLANTINGS))
@pytest.mark.parametrize("script", sorted(MAIN_SCRIPTS))
def test_main_posts_its_audit_despite_a_planted_or_edited_copy(
    script, planting, request, monkeypatch,
) -> None:
    fixture, wire, audits = MAIN_SCRIPTS[script]
    module = request.getfixturevalue(fixture)
    wire(module, monkeypatch)

    # Learn the exact bodies a clean run posts.
    learn = _FakeGitHub()
    monkeypatch.setattr(module, "gh_run", learn)
    assert module.main() == 0
    assert len(learn.posted) == audits
    assert all(b.splitlines()[-1].startswith(audit.AUDIT_KEY_PREFIX) for b in learn.posted)

    # Plant every one of them — then the run must post every one again.
    gh = _FakeGitHub()
    for body in learn.posted:
        gh.plant(body, **PLANTINGS[planting])
    monkeypatch.setattr(module, "gh_run", gh)
    assert module.main() == 0
    assert gh.posted == learn.posted


@pytest.mark.parametrize("script", sorted(MAIN_SCRIPTS))
def test_main_retry_skips_its_own_exact_audit(script, request, monkeypatch) -> None:
    """The control: the same comments, own and unedited, make the retry a no-op —
    so the planted/edited cases above post because of the guard, not because
    `main()` never looks."""
    fixture, wire, audits = MAIN_SCRIPTS[script]
    module = request.getfixturevalue(fixture)
    wire(module, monkeypatch)
    gh = _FakeGitHub()
    monkeypatch.setattr(module, "gh_run", gh)
    assert module.main() == 0
    assert len(gh.posted) == audits
    gh.assignment_events -= 2 * len(gh.edits)  # a handoff retry sees the pre-edit timeline
    assert module.main() == 0
    assert len(gh.posted) == audits
