"""Tests for the friction change check, `pkit friction check` (Task #990, COR-050).

Every test stands up a real adopter repository (`make_adopter_repo`), commits
a base state on `main`, branches `feature` off it and makes real commits (or
leaves uncommitted work) before running the check against `main`. Documents
are written with JSON front matter — valid YAML, and exact about strings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

CONFIG = ".pkit/project/config.yaml"
T1 = "2026-10-01T09:00:00Z"
T2 = "2026-10-02T09:40:12Z"
SOURCE = {"src/cli/main.py": "print('cli')\n", "src/core/engine.py": "ENGINE = 1\n"}


def _config(mode: str = "warning", places: tuple[str, ...] = ("docs",), **friction: Any) -> str:
    block: dict[str, Any] = {"mode": mode, "places": list(places), **friction}
    return json.dumps({"name": "adopter", "friction": block}, indent=2) + "\n"


def _doc(
    artefact_id: str | None,
    *,
    anchors: dict[str, list[str]] | None = None,
    at: str | None = None,
    outcome: str | None = None,
    because: str | None = None,
    deferred: list[tuple[str, str, str]] | None = None,
    body: str = "Body.",
    **fields: Any,
) -> str:
    """A document whose front matter carries the `friction` block, as JSON."""
    front: dict[str, Any] = {} if artefact_id is None else {"id": artefact_id}
    front.update(fields)
    revalidated: dict[str, Any] = {}
    if at is not None:
        revalidated["at"] = at
    if outcome is not None:
        revalidated["outcome"] = outcome
    if because is not None:
        revalidated["unchanged-because"] = because
    if deferred:
        revalidated["deferred"] = [
            {"anchor": {"kind": kind, "value": value}, "reason": reason}
            for kind, value, reason in deferred
        ]
    block: dict[str, Any] = {}
    if anchors is not None:
        block["anchors"] = anchors
    if revalidated:
        block["revalidated"] = revalidated
    front["pkit"] = {"friction": block}
    return f"---\n{json.dumps(front, indent=2)}\n---\n\n{body}\n"


def _guide(**overrides: Any) -> str:
    """The workhorse artefact: `guide`, anchored to the CLI sources, revalidated at T1."""
    values: dict[str, Any] = {
        "anchors": {"path": ["src/cli/**"]},
        "at": T1,
        "outcome": "unchanged",
        "because": "the CLI surface is as described",
    }
    values.update(overrides)
    return _doc("guide", **values)


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def _start(adopter: AdopterRepo, files: dict[str, str], config: str | None = None) -> None:
    """Commit the base state on `main` (the install included) and branch `feature` off it."""
    adopter.write({CONFIG: config or _config(), **SOURCE, **files})
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


def _run(adopter: AdopterRepo, **kwargs: Any) -> fc.ChangeCheck:
    return fc.run_change_check(adopter.root, "main", **kwargs)


def _summary(result: fc.ChangeCheck) -> list[tuple[str, str | None, str | None, str | None]]:
    """(kind, location, anchor, answer) per finding, in report order."""
    return [
        (
            f.kind.value,
            f.location,
            None if f.anchor is None else f"{f.anchor.kind}:{f.anchor.value}",
            None if f.answer is None else f.answer.value,
        )
        for f in result.findings
    ]


# --- the three answers ---------------------------------------------------------


def test_a_changed_anchor_answered_by_an_update_is_not_friction(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "change the CLI and update the guide",
        {
            "src/cli/main.py": "print('cli v2')\n",
            "docs/guide.md": _guide(at=T2, outcome="updated", because=None, body="Body, v2."),
        },
    )
    result = _run(repo)
    assert _summary(result) == [
        ("answered", "docs/guide.md", "path:src/cli/**", "updated"),
    ]
    assert result.findings[0].artefact == "guide"
    assert not result.failing


def test_unchanged_with_a_new_justification_answers(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "change the CLI; the guide still holds",
        {
            "src/cli/main.py": "print('cli, refactored')\n",
            "docs/guide.md": _guide(at=T2, because="a refactor: nothing the guide says moved"),
        },
    )
    (finding,) = _run(repo).findings
    assert finding.kind is fc.FindingKind.ANSWERED
    assert finding.answer is fc.Answer.UNCHANGED
    assert "a refactor: nothing the guide says moved" in finding.message


def test_a_deferral_introduced_in_the_diff_answers_its_anchor(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "change the CLI; defer the guide",
        {
            "src/cli/main.py": "print('cli v3')\n",
            "docs/guide.md": _guide(deferred=[("path", "src/cli/**", "rewrite after the rename")]),
        },
    )
    (finding,) = _run(repo).findings
    assert (finding.kind, finding.answer) == (fc.FindingKind.ANSWERED, fc.Answer.DEFERRED)
    assert "rewrite after the rename" in finding.message


def test_a_changed_anchor_without_an_answer_is_friction(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit("change the CLI only", {"src/cli/main.py": "print('cli v4')\n"})
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert "revalidate the artefact, or defer the anchor" in result.findings[0].message


def test_a_pre_existing_deferral_does_not_cover_a_new_change(repo: AdopterRepo) -> None:
    deferred = [("path", "src/cli/**", "waiting on the rename")]
    _start(repo, {"docs/guide.md": _guide(deferred=deferred)})
    repo.commit("change the CLI again", {"src/cli/main.py": "print('cli v5')\n"})
    (finding,) = _run(repo).findings
    assert finding.kind is fc.FindingKind.FRICTION
    assert "its deferral predates this diff" in finding.message


# --- a bump with nothing behind it ---------------------------------------------------


@pytest.mark.parametrize(
    ("head", "reason"),
    [
        pytest.param(
            _guide(at=T2), "`unchanged-because` is the same as before", id="same-justification"
        ),
        pytest.param(
            _guide(at=T2, outcome="updated", because=None),
            "`outcome: updated`, but the content did not change",
            id="updated-without-content-change",
        ),
        pytest.param(
            _guide(at=T2, because="a new reason", body="Body, edited."),
            "`outcome: unchanged`, but the content changed",
            id="unchanged-although-content-changed",
        ),
    ],
)
def test_a_marker_bump_with_nothing_behind_it(repo: AdopterRepo, head: str, reason: str) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit("bump the marker", {"docs/guide.md": head})
    result = _run(repo)
    assert _summary(result) == [("bump", "docs/guide.md", None, None)]
    assert reason in result.findings[0].message
    assert result.failing


def test_a_bump_answers_no_changed_anchor(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "change the CLI; bump without a new reason",
        {"src/cli/main.py": "print('cli v6')\n", "docs/guide.md": _guide(at=T2)},
    )
    assert [kind for kind, *_ in _summary(_run(repo))] == ["friction", "bump"]


def test_a_voluntary_revalidation_is_reported_as_such(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "improve the guide",
        {"docs/guide.md": _guide(at=T2, outcome="updated", because=None, body="Clearer.")},
    )
    assert _summary(_run(repo)) == [("revalidated", "docs/guide.md", None, "updated")]


def test_a_reformatted_marker_is_not_a_revalidation(repo: AdopterRepo) -> None:
    # The same instant written unquoted: the parsed value of `at` did not change.
    written = "---\nid: guide\npkit:\n  friction:\n    anchors: {path: [src/cli/**]}\n"
    revalidated = "    revalidated: {at: %s, outcome: unchanged, unchanged-because: %s}\n"
    base = written + revalidated % (f'"{T1}"', "holds") + "---\n\nBody.\n"
    head = written + revalidated % (T1, "a new reason") + "---\n\nBody.\n"
    _start(repo, {"docs/guide.md": base})
    repo.commit("touch", {"src/cli/main.py": "print('x')\n", "docs/guide.md": head})
    assert [kind for kind, *_ in _summary(_run(repo))] == ["friction"]


# --- the cascade along artefact anchors, in truth-chain order ------------------------


def _chain() -> dict[str, str]:
    """`c` anchors `b`, `b` anchors `a`, `a` anchors the engine; walked c, b, a."""
    return {
        "docs/a-engine.md": _doc(
            "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated"
        ),
        "docs/b-overview.md": _doc(
            "overview", anchors={"artefact": ["engine-notes"]}, at=T1, outcome="updated"
        ),
        "docs/c-intro.md": _doc(
            "intro", anchors={"artefact": ["overview"]}, at=T1, outcome="updated"
        ),
    }


def test_a_content_change_flags_its_dependants_upstream_first(repo: AdopterRepo) -> None:
    files = _chain()
    files["docs/0-first.md"] = _doc(
        "first", anchors={"artefact": ["intro"]}, at=T1, outcome="updated"
    )
    _start(repo, files)
    repo.commit(
        "the engine changed and its notes were updated",
        {
            "src/core/engine.py": "ENGINE = 2\n",
            "docs/a-engine.md": _doc(
                "engine-notes",
                anchors={"path": ["src/core/**"]},
                at=T2,
                outcome="updated",
                body="Engine 2.",
            ),
        },
    )
    assert _summary(_run(repo)) == [
        ("answered", "docs/a-engine.md", "path:src/core/**", "updated"),
        ("friction", "docs/b-overview.md", "artefact:engine-notes", None),
    ]


def test_an_unchanged_revalidation_stops_the_cascade(repo: AdopterRepo) -> None:
    _start(repo, _chain())
    repo.commit(
        "engine notes edited; the overview still holds",
        {
            "docs/a-engine.md": _doc(
                "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, body="Reworded."
            ),
            "docs/b-overview.md": _doc(
                "overview",
                anchors={"artefact": ["engine-notes"]},
                at=T2,
                outcome="unchanged",
                because="the notes were reworded, not changed",
            ),
        },
    )
    assert _summary(_run(repo)) == [
        ("answered", "docs/b-overview.md", "artefact:engine-notes", "unchanged"),
    ]


def test_an_updated_revalidation_continues_the_cascade(repo: AdopterRepo) -> None:
    _start(repo, _chain())
    repo.commit(
        "engine notes edited; the overview updated with them",
        {
            "docs/a-engine.md": _doc(
                "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, body="Reworked."
            ),
            "docs/b-overview.md": _doc(
                "overview",
                anchors={"artefact": ["engine-notes"]},
                at=T2,
                outcome="updated",
                body="Overview, reworked.",
            ),
        },
    )
    assert _summary(_run(repo)) == [
        ("answered", "docs/b-overview.md", "artefact:engine-notes", "updated"),
        ("friction", "docs/c-intro.md", "artefact:overview", None),
    ]


def test_the_container_is_not_content(repo: AdopterRepo) -> None:
    _start(repo, _chain())
    # Only the target's own block changes (a deferral): its dependants see nothing.
    repo.commit(
        "defer on the engine notes",
        {
            "docs/a-engine.md": _doc(
                "engine-notes",
                anchors={"path": ["src/core/**"]},
                at=T1,
                outcome="updated",
                deferred=[("path", "src/core/**", "later")],
            )
        },
    )
    assert _summary(_run(repo)) == []


# --- new artefacts, the anchor list, moves ------------------------------------------------


def test_an_artefact_new_in_the_diff_counts_as_revalidated(repo: AdopterRepo) -> None:
    _start(repo, {})
    repo.commit(
        "a new page next to a CLI change",
        {"src/cli/main.py": "print('new')\n", "docs/guide.md": _guide()},
    )
    assert _summary(_run(repo)) == [("answered", "docs/guide.md", None, "new")]


def test_changing_the_anchor_list_needs_a_revalidation(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "anchor the guide to the engine too",
        {"docs/guide.md": _guide(anchors={"path": ["src/cli/**", "src/core/**"]})},
    )
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", None, None)]
    assert "anchor list changed" in result.findings[0].message


def test_a_revalidation_answers_an_anchor_list_change(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "anchor the guide to the engine too, and revalidate",
        {
            "docs/guide.md": _guide(
                anchors={"path": ["src/cli/**", "src/core/**"]},
                at=T2,
                because="the guide already covered the engine's part",
            )
        },
    )
    assert _summary(_run(repo)) == [("answered", "docs/guide.md", None, "unchanged")]


def test_a_move_needs_a_revalidation(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.rename("docs/guide.md", "docs/cli/guide.md")
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/cli/guide.md", None, None)]
    assert "moved here from docs/guide.md" in result.findings[0].message


def test_a_move_with_a_revalidation_is_answered(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.rename("docs/guide.md", "docs/cli/guide.md")
    repo.commit("revalidate the moved guide", {"docs/cli/guide.md": _guide(at=T2, because="moved")})
    assert _summary(_run(repo)) == [("answered", "docs/cli/guide.md", None, "unchanged")]


def test_an_entry_moved_between_collection_files_needs_a_revalidation(repo: AdopterRepo) -> None:
    def collection(*entries: str) -> str:
        front = {
            entry: {
                "status": "accepted",
                "pkit": {"friction": {"anchors": {"path": ["src/core/**"]}}},
            }
            for entry in entries
        }
        sections = "".join(f"## {entry} — a rule\n\nStatement.\n\n" for entry in entries)
        return f"---\n{json.dumps(front)}\n---\n\n{sections}"

    _start(repo, {"docs/rules-a.md": collection("RS-1", "RS-2"), "docs/rules-b.md": collection()})
    repo.commit(
        "move RS-2", {"docs/rules-a.md": collection("RS-1"), "docs/rules-b.md": collection("RS-2")}
    )
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/rules-b.md#RS-2", None, None)]
    assert result.findings[0].artefact == "RS-2"


def test_an_entry_body_section_is_part_of_its_content(repo: AdopterRepo) -> None:
    front = {
        "RS-1": {"status": "accepted"},
        "RS-2": {"pkit": {"friction": {"anchors": {"artefact": ["RS-1"]}}}},
    }
    text = "---\n{front}\n---\n\n## RS-1 — Name things\n\n{statement}\n\n## RS-2 — Other\n\nTwo.\n"
    _start(repo, {"docs/rules.md": text.format(front=json.dumps(front), statement="One.")})
    repo.commit(
        "reword RS-1",
        {"docs/rules.md": text.format(front=json.dumps(front), statement="One, reworded.")},
    )
    assert _summary(_run(repo)) == [("friction", "docs/rules.md#RS-2", "artefact:RS-1", None)]


# --- dead anchors and kinds --------------------------------------------------------------------


def test_an_anchor_added_dead_is_the_pull_requests(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "anchor to a path that does not exist",
        {
            "docs/guide.md": _guide(
                anchors={"path": ["src/cli/**", "src/gone/**"]}, at=T2, because="extended"
            )
        },
    )
    assert _summary(_run(repo)) == [
        ("dead-anchor", "docs/guide.md", "path:src/gone/**", None),
        ("answered", "docs/guide.md", None, "unchanged"),
    ]


def test_a_pre_existing_dead_anchor_is_not_the_change_checks(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide(anchors={"path": ["src/cli/**", "src/gone/**"]})})
    repo.commit("an unrelated change", {"src/core/engine.py": "ENGINE = 3\n"})
    assert _summary(_run(repo)) == []


def test_a_target_removed_by_the_diff_turns_the_anchor_dead(repo: AdopterRepo) -> None:
    _start(
        repo,
        {
            "docs/guide.md": _guide(anchors={"path": ["src/core/engine.py"]}),
            "docs/other.md": _doc(
                "other", anchors={"artefact": ["guide"]}, at=T1, outcome="updated"
            ),
        },
    )
    repo.commit(
        "remove the engine and the guide", {"src/core/engine.py": None, "docs/guide.md": None}
    )
    result = _run(repo)
    assert _summary(result) == [("dead-anchor", "docs/other.md", "artefact:guide", None)]
    assert "the diff removed or moved its target" in result.findings[0].message


def test_an_unresolved_kind_is_reported_apart_from_a_dead_anchor(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "a kind nothing resolves",
        {
            "docs/guide.md": _guide(
                anchors={"path": ["src/cli/**"], "use-case": ["UC-1"]}, at=T2, because="x"
            )
        },
    )
    result = _run(repo)
    assert _summary(result)[0] == ("unresolved-kind", "docs/guide.md", "use-case:UC-1", None)
    assert "no installed component registers a resolver" in result.findings[0].message
    assert result.failing


def test_a_registered_resolver_without_no_network_is_refused(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "anchor a registered kind",
        {"docs/guide.md": _guide(anchors={"use-case": ["UC-1"]}, at=T2, because="x")},
    )
    unconfined = fc.ResolverCommand("use-case", "software-analysis", "resolve-use-case")
    result = _run(repo, registry={"use-case": unconfined})
    assert "declares no network egress" in result.findings[0].message
    confined = fc.ResolverCommand("use-case", "software-analysis", "resolve-use-case", "none")
    result = _run(repo, registry={"use-case": confined})
    assert "is not run yet" in result.findings[0].message


@pytest.mark.parametrize(
    ("network", "refused"),
    [
        (None, "declares no network egress"),
        ("any", "declares network egress 'any'"),
        ("none", None),
    ],
)
def test_refuse_resolver_without_no_network(network: Any, refused: str | None) -> None:
    resolver = fc.ResolverCommand("use-case", "software-analysis", "resolve-use-case", network)
    reason = fc.refuse_resolver_without_no_network(resolver)
    if refused is None:
        assert reason is None
    else:
        assert reason is not None and refused in reason
    assert fc.registered_anchor_kinds(Path(".")) == {}


def test_a_record_anchor_changes_with_its_decision_file(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide(anchors={"record": ["COR-050"]})})
    record = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
    text = (repo.root / record).read_text(encoding="utf-8")
    repo.commit("amend the record", {record: text + "\nAmended.\n"})
    assert _summary(_run(repo)) == [("friction", "docs/guide.md", "record:COR-050", None)]


def test_a_record_anchor_naming_no_record_is_dead(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit(
        "anchor a record that does not exist",
        {"docs/guide.md": _guide(anchors={"record": ["COR-999"]}, at=T2, because="x")},
    )
    result = _run(repo)
    assert _summary(result)[0] == ("dead-anchor", "docs/guide.md", "record:COR-999", None)
    assert "names no record" in result.findings[0].message


def test_a_capability_decision_resolves_as_a_record(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    decisions = sorted((adopter.pkit / "capabilities" / "evidence" / "decisions").glob("DEC-*.md"))
    stem = decisions[0].stem
    number = "-".join(stem.split("-")[:2])
    _start(adopter, {"docs/guide.md": _guide(anchors={"record": [f"evidence:{number}"]})})
    rel = decisions[0].relative_to(adopter.root).as_posix()
    adopter.commit("amend it", {rel: decisions[0].read_text(encoding="utf-8") + "\nMore.\n"})
    assert _summary(_run(adopter)) == [
        ("friction", "docs/guide.md", f"record:evidence:{number}", None)
    ]


# --- paths ------------------------------------------------------------------------------------


def test_excluded_paths_do_not_change_an_anchor(repo: AdopterRepo) -> None:
    _start(
        repo,
        {"docs/guide.md": _guide(), "src/cli/generated/table.py": "T = 1\n"},
        config=_config(exclude=["src/cli/generated"]),
    )
    repo.commit("regenerate", {"src/cli/generated/table.py": "T = 2\n"})
    assert _summary(_run(repo)) == []


def test_an_artefact_is_not_anchored_to_its_own_file(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide(anchors={"path": ["docs/**"]})})
    repo.commit(
        "edit the guide's body only",
        {"docs/guide.md": _guide(anchors={"path": ["docs/**"]}, body="New.")},
    )
    assert _summary(_run(repo)) == []


def test_uncommitted_work_is_part_of_the_diff(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.write({"src/cli/main.py": "print('uncommitted')\n", "src/cli/new.py": "NEW = 1\n"})
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert result.head is not None and result.head.uncommitted == 2
    assert "+ working tree, 2 uncommitted paths" in fc.render_human(result)


def test_places_are_read_from_each_side(repo: AdopterRepo) -> None:
    _start(repo, {"notes/guide.md": _guide()})
    # Declaring the place makes the guide new at head, not stale.
    repo.commit(
        "declare notes as a place",
        {CONFIG: _config(places=("docs", "notes")), "src/cli/main.py": "print('x')\n"},
    )
    assert _summary(_run(repo)) == [("answered", "notes/guide.md", None, "new")]


# --- the base -----------------------------------------------------------------------------------


def test_an_outdated_base_is_reported_and_never_fails(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()}, config=_config(mode="enforcing"))
    repo.commit("feature work", {"src/core/engine.py": "ENGINE = 4\n"})
    repo.checkout("main")
    repo.commit("main moves on", {"README.md": "main moved\n"})
    repo.checkout("feature")
    result = _run(repo)
    assert _summary(result) == [("outdated-base", None, None, None)]
    assert result.base is not None and result.base.outdated
    assert result.base.tip != result.base.commit
    assert result.exit_code == 0


def test_every_run_names_the_base_commit_it_compared_against(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    base = repo.head()
    result = _run(repo)
    assert result.base is not None
    assert (result.base.commit, result.base.outdated) == (base, False)
    assert f"Base: main at {base[:12]}" in fc.render_human(result)


def test_a_base_that_does_not_resolve_is_an_error(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    with pytest.raises(fc.FrictionCheckError, match="does not resolve"):
        fc.run_change_check(repo.root, "no-such-branch")


# --- modes, dormancy, output ---------------------------------------------------------------------


def _cli(*args: str, env: dict[str, str] | None = None) -> Any:
    return CliRunner().invoke(main, ["friction", "check", *args], env=env)


def test_warning_mode_reports_and_passes(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()}, config=_config(mode="warning"))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('w')\n"})
    result = _cli("--base", "main")
    assert result.exit_code == 0, result.output
    assert "friction" in result.output
    assert "Result: passed" in result.output and "reported, not failed" in result.output


def test_enforcing_mode_fails_on_friction(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()}, config=_config(mode="enforcing"))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('e')\n"})
    result = _cli("--base", "main")
    assert result.exit_code == 1, result.output
    assert "Result: failed" in result.output


def test_enforcing_mode_passes_a_revalidated_change(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()}, config=_config(mode="enforcing"))
    repo.commit(
        "change the CLI and revalidate",
        {"src/cli/main.py": "print('r')\n", "docs/guide.md": _guide(at=T2, because="still true")},
    )
    result = _cli("--base", "main")
    assert result.exit_code == 0, result.output


def test_the_base_comes_from_the_environment(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    result = _cli("--json", env={fc.BASE_ENV: "main"})
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["base"]["ref"] == "main"


def test_dormant_without_places(repo: AdopterRepo) -> None:
    _start(
        repo, {"docs/guide.md": _guide()}, config=json.dumps({"friction": {"mode": "enforcing"}})
    )
    repo.commit("change the CLI only", {"src/cli/main.py": "print('d')\n"})
    result = _cli("--base", "main")
    assert result.exit_code == 0, result.output
    assert "no places declared; dormant." in result.output


@pytest.mark.parametrize("places", [(), ("docs",)], ids=["dormant", "awake"])
def test_a_mode_that_is_not_a_mode_reads_as_warning_and_says_so(
    repo: AdopterRepo, places: tuple[str, ...]
) -> None:
    _start(repo, {"docs/guide.md": _guide()}, config=_config(mode="enforcin", places=places))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('m')\n"})
    result = _run(repo)
    assert (result.mode, result.exit_code) == ("warning", 0)
    assert "friction.mode 'enforcin' is not a mode; read as warning" in fc.render_human(result)


def test_dormant_demands_no_repository(tmp_path: Path) -> None:
    result = fc.run_change_check(tmp_path, "main")
    assert (result.dormant, result.base, result.head, result.exit_code) == (True, None, None, 0)


def test_dormant_when_nothing_carries_the_container(repo: AdopterRepo) -> None:
    _start(
        repo, {"docs/plain.md": "---\ntitle: Plain\n---\n\nText.\n"}, config=_config("enforcing")
    )
    repo.commit("change the CLI only", {"src/cli/main.py": "print('d')\n"})
    result = _run(repo)
    assert result.dormant and result.findings == () and result.exit_code == 0
    assert "none carrying the `pkit` container; dormant." in fc.render_human(result)


def test_json_document_shape(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()}, config=_config(mode="enforcing"))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('j')\n"})
    result = _cli("--base", "main", "--json")
    assert result.exit_code == 1
    document = json.loads(result.output)
    assert sorted(document) == [
        "base",
        "check",
        "counts",
        "dormant",
        "failed",
        "findings",
        "head",
        "mode",
    ]
    assert (document["check"], document["mode"], document["dormant"], document["failed"]) == (
        "change",
        "enforcing",
        False,
        True,
    )
    assert sorted(document["base"]) == ["commit", "outdated", "ref", "tip"]
    assert sorted(document["head"]) == ["commit", "uncommitted_paths"]
    assert document["counts"]["friction"] == 1 and document["counts"]["places"] == 1
    (finding,) = document["findings"]
    assert finding == {
        "artefact": "guide",
        "location": "docs/guide.md",
        "kind": "friction",
        "anchor": {"kind": "path", "value": "src/cli/**"},
        "answer": None,
        "message": finding["message"],
    }


def test_output_is_deterministic(repo: AdopterRepo) -> None:
    files = _chain()
    files["docs/guide.md"] = _guide()
    _start(repo, files)
    repo.commit(
        "several changes",
        {"src/cli/main.py": "print('z')\n", "src/core/engine.py": "ENGINE = 9\n"},
    )
    first, second = _run(repo), _run(repo)
    assert fc.render_json(first) == fc.render_json(second)
    assert fc.render_human(first) == fc.render_human(second)
    assert [f.location for f in first.findings] == ["docs/a-engine.md", "docs/guide.md"]


def test_unparsable_front_matter_is_reported(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    repo.commit("break a page", {"docs/broken.md": "---\nid: [unclosed\n---\n"})
    result = _run(repo)
    assert _summary(result) == [("unreadable", "docs/broken.md", None, None)]
    assert not result.failing


# --- discovery through a tree agrees with the filesystem walk -------------------------------------


@pytest.mark.parametrize(
    "places",
    [
        ("docs",),
        ("docs/**/*.md",),
        ("docs/**",),
        ("docs/sub/*.md", "notes/guide.md"),
        ("*.md",),
        (".",),
        ("docs/s*/**/*.md", "notes"),
    ],
)
def test_listing_discovery_agrees_with_the_filesystem(
    repo: AdopterRepo, places: tuple[str, ...]
) -> None:
    files = {
        "README.md": _doc("readme"),
        "docs/a.md": _doc("a"),
        "docs/.hidden.md": _doc("hidden"),
        "docs/sub/b.md": _doc("b"),
        "docs/sub/deep/c.md": _doc("c"),
        "docs/data.yaml": "pkit: {}\n",
        "notes/guide.md": _guide(),
    }
    repo.write({CONFIG: _config(places=places), **files})
    on_disk = fd.discover_artefacts(repo.root)
    listed = fd.discover_artefacts(repo.root, tree=fc.WorkingTree(repo.root))
    assert [a.location for a in listed.artefacts] == [a.location for a in on_disk.artefacts]
    assert [a.place.pattern for a in listed.artefacts] == [
        a.place.pattern for a in on_disk.artefacts
    ]


def test_a_commit_tree_reads_what_the_commit_held(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": _guide()})
    base = repo.head()
    repo.commit("rewrite", {"docs/guide.md": _guide(body="Rewritten.")})
    tree = fc.CommitTree(repo.root, base)
    assert "docs/guide.md" in tree.files()
    assert tree.read_bytes(["docs/guide.md", "missing.md"]) == {
        "docs/guide.md": _guide().encode(),
        "missing.md": None,
    }
