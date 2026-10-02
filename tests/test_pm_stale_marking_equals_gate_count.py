"""Regression guard: show-pr marks a verdict stale exactly when done-work's
gate would not count it (ADR-042 D2, #1195).

`show-pr --field review` shows each reviewer's latest verdict — a superset of
what the merge gate reads — and marks one stale, with the reason, when the
gate will not count it. Both judge by one freshness rule over one resolution,
wired once (`_lib.pr_review`), so the promise holds by construction. This
guard checks that it does, the way `test_pm_invoke_set_equals_gate_set`
checks the invoke set: it drives each consumer's REAL path — `show-pr`'s
`main()` with `--json`, `done-work`'s `_check_agent_gate`, and `review-pr`'s
verdict read — against one stubbed world (the same comments, commits,
closing issue, changed files, author changes and base history), and for
every row of the table asserts:

  * per verdict: show-pr shows it stale ⇔ the gate did not count it (it is
    absent from what `gate_verdicts` handed the gate) ⇔ review-pr does not
    skip it as fresh — and all three match the row's expectation, so a row
    cannot pass by the consumers agreeing on the wrong answer;
  * the gate passes ⇔ show-pr shows every required reviewer's verdict as an
    APPROVED that is not stale.

The property is over the verdicts the gate reads: each row gives every
required reviewer a verdict. A verdict carrying no marker at all is one the
gate never reads (#593), while show-pr displays it and judges it by the rule
alone; the row that shows this is marked as a known disagreement (strict
xfail), not as agreement.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


def _load(module_name: str, path: Path):
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and str(SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def dw():
    return _load("pm_dw_for_stale_parity", SCRIPTS_DIR / "done-work.py")


@pytest.fixture(scope="module")
def sp():
    return _load("pm_sp_for_stale_parity", SCRIPTS_DIR / "show-pr.py")


@pytest.fixture(scope="module")
def rpr():
    return _load("pm_rpr_for_stale_parity", SCRIPTS_DIR / "review-pr.py")


@pytest.fixture(scope="module")
def rc():
    return _load("pm_rc_for_stale_parity", SCRIPTS_DIR / "_lib" / "review_contributions.py")


PR = 99
ISSUE = 42
REVIEWED = "a" * 40
HEAD = "b" * 40
BASE = "c" * 40
ABANDONED_BASE = "d" * 40
COMMIT_TS = "2026-06-05T00:00:00Z"
BEFORE_THE_COMMIT = "2026-06-04T00:00:00Z"
AFTER_THE_COMMIT = "2026-06-06T00:00:00Z"

PINNED = f"<!-- pkit-verdict sha={REVIEWED} base={BASE} -->"
ON_THE_HEAD = f"<!-- pkit-verdict sha={HEAD} base={BASE} -->"
ON_AN_ABANDONED_BASE = f"<!-- pkit-verdict sha={HEAD} base={ABANDONED_BASE} -->"
NAMES_NO_HEAD = "<!-- pkit-verdict -->"
NO_MARKER = ""

REBASED = "aaaaaaa is no longer in the branch's history — the branch was rebased or force-pushed"


def _verdict(name: str, token: str = "APPROVED", *, marker: str = PINNED, at: str = ""):
    """A local reviewer's verdict comment. A verdict naming its head is posted
    before the latest commit, so only the head it names can keep it fresh."""
    body = f"Reviewer agent (local, {name}): {token}\n\n{name} reasons."
    if marker:
        body += f"\n\n{marker}"
    return {
        "author": {"login": "author"},
        "body": body,
        "createdAt": at or BEFORE_THE_COMMIT,
        "url": f"https://github.com/o/r/pull/{PR}#{name}",
    }


@dataclass(frozen=True)
class World:
    """One PR as GitHub, the repository and the project config describe it,
    and which required reviewer's verdict the gate should not count."""

    comments: tuple[dict, ...]
    #: Reviewer → whether its verdict is stale (the gate does not count it).
    stale: dict[str, bool]
    #: The author's changes since the reviewed head, or why they cannot be read.
    delta: tuple[str, ...] | str = ()
    base_kept: bool = True
    changed_files: tuple[str, ...] = ("src/app.py", "README.md")
    not_code: list[str] | None = None
    docs_reviewer: bool = False


def _collection(rc, world: World):
    """`code-reviewer` rides the code floor alone; `docs-reviewer`, when
    installed, rides it too but also every typed issue."""
    rules = [
        rc.ContributionRule(
            capability="software-engineering",
            predicate=MappingProxyType({}),
            reviewer="code-reviewer",
            floor=rc.FLOOR_TOUCHES_CODE,
        )
    ]
    if world.docs_reviewer:
        rules.append(
            rc.ContributionRule(
                capability="software-engineering",
                predicate=MappingProxyType({"type": rc.MATCH_ANY}),
                reviewer="docs-reviewer",
                floor=rc.FLOOR_TOUCHES_CODE,
            )
        )
    return rc.ContributionCollection(rules=tuple(rules))


def _config(world: World) -> dict:
    review: dict = {
        "agents": {"local_registered": [{"name": "pm-reviewer"}], "remote_registered": []}
    }
    if world.not_code is not None:
        review["floors"] = {"not_code": list(world.not_code)}
    return {"review": review}


def _pr_view(world: World) -> dict:
    return {
        "title": "feat(pm): a change",
        "body": f"Closes #{ISSUE}\n\n## Doc impact\n\nNone.",
        "state": "OPEN",
        "headRefName": f"feat/{ISSUE}-a-change",
        "baseRefName": "main",
        "mergedAt": None,
        "isDraft": False,
        "url": f"https://github.com/o/r/pull/{PR}",
        "reviewRequests": [],
        "author": {"login": "author"},
        "comments": list(world.comments),
        "commits": [{"oid": HEAD, "committedDate": COMMIT_TS}],
        "headRefOid": HEAD,
        "baseRefOid": BASE,
    }


def _stub_world(modules, monkeypatch, rc, world: World) -> None:
    """Answer every consumer's substrate seam from the same world."""
    from _lib.author_delta import AuthorDelta, BaseCheck

    def gh_run(args, config, **kwargs):
        joined = " ".join(args)
        if "closingIssuesReferences" in joined:
            stdout = json.dumps({"closingIssuesReferences": [{"number": ISSUE}]})
        elif args[:2] == ["gh", "api"] and "/files" in joined:
            stdout = "".join(json.dumps([path, None]) + "\n" for path in world.changed_files)
        elif args[:3] == ["gh", "pr", "view"]:
            stdout = json.dumps(_pr_view(world))
        else:
            raise AssertionError(f"the stubbed world does not answer {args}")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    def gh_get_issue(issue_number, config, *, fields):
        return {"labels": [{"name": "type:feature"}]}

    def author_delta(since, head, *, base_tip):
        assert (since, head, base_tip) == (REVIEWED, HEAD, BASE)
        if isinstance(world.delta, str):
            return AuthorDelta(error=world.delta)
        return AuthorDelta(paths=world.delta)

    def base_kept(reviewed_base, base_tip):
        assert base_tip == BASE
        return BaseCheck(kept=world.base_kept)

    for module in modules:
        monkeypatch.setattr(module, "gh_run", gh_run)
        monkeypatch.setattr(module, "gh_get_issue", gh_get_issue)
        monkeypatch.setattr(module, "collect_contributions", lambda root: _collection(rc, world))
        monkeypatch.setattr(module, "author_delta", author_delta)
        monkeypatch.setattr(module, "base_kept", base_kept)


def _bootstrapped_capability_root(tmp_path: Path) -> Path:
    """A capability root the #747 prerequisite gate lets show-pr run in."""
    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    project = cap_root / "project"
    project.mkdir(parents=True)
    (project / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: []\n", encoding="utf-8"
    )
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )
    return cap_root


def _show_pr_review(sp, monkeypatch, capsys, cap_root: Path, config: dict) -> list[dict]:
    """What `show-pr <PR> --json` shows as the latest verdicts."""
    monkeypatch.setattr(sp, "resolve_capability_root", lambda arg: cap_root)
    monkeypatch.setattr(sp, "load_adopter_config", lambda root: config)
    monkeypatch.setattr(sp, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(sp, "resolve_invoker_identity", lambda config: "dev")
    monkeypatch.setattr(
        sp,
        "check_membership",
        lambda members, invoker: SimpleNamespace(allowed=True, refusal_message=""),
    )
    monkeypatch.setattr(sys, "argv", ["show-pr", str(PR), "--json"])
    capsys.readouterr()
    assert sp.main() == 0
    return json.loads(capsys.readouterr().out)["review"]


def _gate(dw, monkeypatch, cap_root: Path, config: dict):
    """The gate's decision, and every verdict it counted."""
    counted: list = []
    calls: list[int] = []
    real = dw.gate_verdicts

    def spy(comments, **kwargs):
        calls.append(1)
        verdicts = real(comments, **kwargs)
        counted.extend(verdicts)
        return verdicts

    monkeypatch.setattr(dw, "gate_verdicts", spy)
    result = dw._check_agent_gate(PR, {}, config, "resolved", cap_root)
    assert calls == [1], f"the gate did not reach its count: {result.refusal_message}"
    return result, {verdict.body for verdict in counted}


def _review_pr_fresh(rpr, cap_root: Path, config: dict) -> set[str]:
    """The reviewers `review-pr` would skip as fresh."""
    review = rpr._resolve_review(PR, config, cap_root.parent.parent.parent)
    assert review.resolution.ok
    states = rpr._read_verdict_states(PR, review, config)
    assert states is not None
    return set(states.fresh)


_KNOWN_UNMARKED_DISAGREEMENT = pytest.mark.xfail(
    strict=True,
    reason=(
        "show-pr displays a verdict with no marker and judges it by the rule "
        "alone (DEC-028, #593), so one posted after the latest commit is shown "
        "fresh though the gate never reads it — a read-surface decision, not "
        "the resolver wiring"
    ),
)


CASES = [
    pytest.param(
        World(
            comments=(_verdict("pm-reviewer"), _verdict("code-reviewer")),
            delta=(),
            stale={"pm-reviewer": False, "code-reviewer": False},
        ),
        id="clean-merge-of-main",
    ),
    pytest.param(
        World(
            comments=(_verdict("pm-reviewer"), _verdict("code-reviewer")),
            delta=("README.md",),
            stale={"pm-reviewer": True, "code-reviewer": False},
        ),
        id="floor-approval-change-outside-its-floors",
    ),
    pytest.param(
        World(
            comments=(_verdict("pm-reviewer"), _verdict("code-reviewer")),
            delta=("src/app.py",),
            stale={"pm-reviewer": True, "code-reviewer": True},
        ),
        id="change-inside-a-floor",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer"),
                _verdict("code-reviewer", "CHANGES_REQUESTED"),
            ),
            delta=("README.md",),
            stale={"pm-reviewer": True, "code-reviewer": True},
        ),
        id="changes-requested-then-any-change",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer", marker=ON_THE_HEAD),
                _verdict("code-reviewer", "CHANGES_REQUESTED", marker=ON_THE_HEAD),
            ),
            stale={"pm-reviewer": False, "code-reviewer": False},
        ),
        id="changes-requested-nothing-changed",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer", marker=NAMES_NO_HEAD, at=AFTER_THE_COMMIT),
                _verdict("code-reviewer", marker=NAMES_NO_HEAD, at=AFTER_THE_COMMIT),
            ),
            stale={"pm-reviewer": False, "code-reviewer": False},
        ),
        id="marker-names-no-head-posted-after-the-commit",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer", marker=NAMES_NO_HEAD, at=BEFORE_THE_COMMIT),
                _verdict("code-reviewer", marker=NAMES_NO_HEAD, at=BEFORE_THE_COMMIT),
            ),
            stale={"pm-reviewer": True, "code-reviewer": True},
        ),
        id="marker-names-no-head-posted-before-the-commit",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer", marker=NO_MARKER, at=BEFORE_THE_COMMIT),
                _verdict("code-reviewer", marker=ON_THE_HEAD),
            ),
            stale={"pm-reviewer": True, "code-reviewer": False},
        ),
        id="no-marker-posted-before-the-commit",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer", marker=NO_MARKER, at=AFTER_THE_COMMIT),
                _verdict("code-reviewer", marker=ON_THE_HEAD),
            ),
            stale={"pm-reviewer": True, "code-reviewer": False},
        ),
        id="no-marker-posted-after-the-commit",
        marks=_KNOWN_UNMARKED_DISAGREEMENT,
    ),
    pytest.param(
        World(
            comments=(_verdict("pm-reviewer"), _verdict("code-reviewer")),
            delta=REBASED,
            stale={"pm-reviewer": True, "code-reviewer": True},
        ),
        id="reviewed-head-rebased-away",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer", marker=ON_AN_ABANDONED_BASE),
                _verdict("code-reviewer", marker=ON_AN_ABANDONED_BASE),
            ),
            base_kept=False,
            stale={"pm-reviewer": True, "code-reviewer": True},
        ),
        id="retargeted-onto-a-base-the-verdict-never-saw",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer", marker=ON_THE_HEAD),
                _verdict("code-reviewer", marker=ON_THE_HEAD),
            ),
            stale={"pm-reviewer": False, "code-reviewer": False},
        ),
        id="verdict-on-the-current-head",
    ),
    pytest.param(
        World(
            comments=(_verdict("pm-reviewer"), _verdict("code-reviewer")),
            delta=(".changes/unreleased/pm.yaml",),
            stale={"pm-reviewer": True, "code-reviewer": False},
        ),
        id="not-code-default-keeps-a-changeset-off-the-floor",
    ),
    pytest.param(
        World(
            comments=(_verdict("pm-reviewer"), _verdict("code-reviewer")),
            changed_files=("src/app.py", "generated/client.py"),
            not_code=["generated/**"],
            delta=("generated/client.py",),
            stale={"pm-reviewer": True, "code-reviewer": False},
        ),
        id="not-code-configured-keeps-its-paths-off-the-floor",
    ),
    pytest.param(
        World(
            comments=(_verdict("pm-reviewer"), _verdict("code-reviewer")),
            not_code=["generated/**"],
            delta=(".changes/unreleased/pm.yaml",),
            stale={"pm-reviewer": True, "code-reviewer": True},
        ),
        id="not-code-configured-replaces-the-default",
    ),
    pytest.param(
        World(
            comments=(
                _verdict("pm-reviewer"),
                _verdict("code-reviewer"),
                _verdict("docs-reviewer"),
            ),
            docs_reviewer=True,
            delta=("README.md",),
            stale={"pm-reviewer": True, "code-reviewer": False, "docs-reviewer": True},
        ),
        id="floor-and-classification-reviewer-held-to-any-change",
    ),
]


@pytest.mark.parametrize("world", CASES)
def test_show_pr_marks_stale_exactly_what_the_gate_does_not_count(
    dw, sp, rpr, rc, monkeypatch, capsys, tmp_path, world: World
) -> None:
    cap_root = _bootstrapped_capability_root(tmp_path)
    config = _config(world)
    _stub_world((dw, sp, rpr), monkeypatch, rc, world)

    shown = {
        entry["reviewer"]: entry
        for entry in _show_pr_review(sp, monkeypatch, capsys, cap_root, config)
    }
    result, counted = _gate(dw, monkeypatch, cap_root, config)
    skipped = _review_pr_fresh(rpr, cap_root, config)

    assert set(shown) == set(world.stale), "every required reviewer has one verdict"
    for reviewer, entry in shown.items():
        uncounted = entry["body"] not in counted
        assert entry["stale"] == uncounted, (
            f"{reviewer}: show-pr says stale={entry['stale']} ({entry['freshness']}), "
            f"but the gate {'did not count' if uncounted else 'counted'} it"
        )
        assert (reviewer not in skipped) == uncounted, (
            f"{reviewer}: review-pr {'skips' if reviewer in skipped else 'runs'} it, "
            f"but the gate {'did not count' if uncounted else 'counted'} it"
        )
        assert entry["stale"] == world.stale[reviewer], entry["freshness"]

    all_counted_approvals = all(
        entry["verdict"] == "APPROVED" and not entry["stale"] for entry in shown.values()
    )
    assert result.passed == all_counted_approvals, result.refusal_message
