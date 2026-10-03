"""Tests for the friction change check, `pkit friction check` (Task #990, COR-050).

Every test stands up a real adopter repository (`make_adopter_repo`), commits
a base state on `main`, branches `feature` off it and makes real commits (or
leaves uncommitted work) before running the check against `main`. The
documents come from `tests.friction_documents`.
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
from tests.friction_documents import CONFIG, SOURCE, T1, T2, document, friction_config, guide


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def _start(adopter: AdopterRepo, files: dict[str, str], config: str | None = None) -> None:
    """Commit the base state on `main` (the install included) and branch `feature` off it."""
    adopter.write({CONFIG: config or friction_config(), **SOURCE, **files})
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
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "change the CLI and update the guide",
        {
            "src/cli/main.py": "print('cli v2')\n",
            "docs/guide.md": guide(at=T2, outcome="updated", because=None, body="Body, v2."),
        },
    )
    result = _run(repo)
    assert _summary(result) == [
        ("answered", "docs/guide.md", "path:src/cli/**", "updated"),
    ]
    assert result.findings[0].artefact == "guide"
    assert not result.failing


def test_unchanged_with_a_new_justification_answers(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "change the CLI; the guide still holds",
        {
            "src/cli/main.py": "print('cli, refactored')\n",
            "docs/guide.md": guide(at=T2, because="a refactor: nothing the guide says moved"),
        },
    )
    (finding,) = _run(repo).findings
    assert finding.kind is fc.FindingKind.ANSWERED
    assert finding.answer is fc.Answer.UNCHANGED
    assert "a refactor: nothing the guide says moved" in finding.message


def test_a_deferral_introduced_in_the_diff_answers_its_anchor(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "change the CLI; defer the guide",
        {
            "src/cli/main.py": "print('cli v3')\n",
            "docs/guide.md": guide(deferred=[("path", "src/cli/**", "rewrite after the rename")]),
        },
    )
    (finding,) = _run(repo).findings
    assert (finding.kind, finding.answer) == (fc.FindingKind.ANSWERED, fc.Answer.DEFERRED)
    assert "rewrite after the rename" in finding.message


def test_a_changed_anchor_without_an_answer_is_friction(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit("change the CLI only", {"src/cli/main.py": "print('cli v4')\n"})
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert "revalidate the artefact, or defer the anchor" in result.findings[0].message


def test_a_pre_existing_deferral_does_not_cover_a_new_change(repo: AdopterRepo) -> None:
    deferred = [("path", "src/cli/**", "waiting on the rename")]
    _start(repo, {"docs/guide.md": guide(deferred=deferred)})
    repo.commit("change the CLI again", {"src/cli/main.py": "print('cli v5')\n"})
    (finding,) = _run(repo).findings
    assert finding.kind is fc.FindingKind.FRICTION
    assert "its deferral predates this diff" in finding.message


# --- a bump with nothing behind it ---------------------------------------------------


@pytest.mark.parametrize(
    ("head", "reason"),
    [
        pytest.param(
            guide(at=T2), "`unchanged-because` is the same as before", id="same-justification"
        ),
        pytest.param(
            guide(at=T2, outcome="updated", because=None),
            "`outcome: updated`, but the content did not change",
            id="updated-without-content-change",
        ),
        pytest.param(
            guide(at=T2, because="a new reason", body="Body, edited."),
            "`outcome: unchanged`, but the content changed",
            id="unchanged-although-content-changed",
        ),
    ],
)
def test_a_marker_bump_with_nothing_behind_it(repo: AdopterRepo, head: str, reason: str) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit("bump the marker", {"docs/guide.md": head})
    result = _run(repo)
    assert _summary(result) == [("bump", "docs/guide.md", None, None)]
    assert reason in result.findings[0].message
    assert result.failing


def test_a_bump_answers_no_changed_anchor(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "change the CLI; bump without a new reason",
        {"src/cli/main.py": "print('cli v6')\n", "docs/guide.md": guide(at=T2)},
    )
    assert [kind for kind, *_ in _summary(_run(repo))] == ["friction", "bump"]


def test_a_voluntary_revalidation_is_reported_as_such(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "improve the guide",
        {"docs/guide.md": guide(at=T2, outcome="updated", because=None, body="Clearer.")},
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
        "docs/a-engine.md": document(
            "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated"
        ),
        "docs/b-overview.md": document(
            "overview", anchors={"artefact": ["engine-notes"]}, at=T1, outcome="updated"
        ),
        "docs/c-intro.md": document(
            "intro", anchors={"artefact": ["overview"]}, at=T1, outcome="updated"
        ),
    }


def test_a_content_change_flags_its_dependants_upstream_first(repo: AdopterRepo) -> None:
    files = _chain()
    files["docs/0-first.md"] = document(
        "first", anchors={"artefact": ["intro"]}, at=T1, outcome="updated"
    )
    _start(repo, files)
    repo.commit(
        "the engine changed and its notes were updated",
        {
            "src/core/engine.py": "ENGINE = 2\n",
            "docs/a-engine.md": document(
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
            "docs/a-engine.md": document(
                "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, body="Reworded."
            ),
            "docs/b-overview.md": document(
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
            "docs/a-engine.md": document(
                "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, body="Reworked."
            ),
            "docs/b-overview.md": document(
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
            "docs/a-engine.md": document(
                "engine-notes",
                anchors={"path": ["src/core/**"]},
                at=T1,
                outcome="updated",
                deferred=[("path", "src/core/**", "later")],
            )
        },
    )
    assert _summary(_run(repo)) == []


def _crlf(text: str) -> str:
    return text.replace("\n", "\r\n")


def test_a_change_of_line_endings_alone_is_no_change_of_content(repo: AdopterRepo) -> None:
    """The target's text as it was, only its line endings changed: no dependant is asked,
    and an `updated` revalidation has no content change behind it (COR-050 point 5)."""
    _start(repo, _chain())
    notes = _chain()["docs/a-engine.md"]
    repo.commit("the engine notes, with CRLF", {"docs/a-engine.md": _crlf(notes)})
    assert _summary(_run(repo)) == []

    updated = document("engine-notes", anchors={"path": ["src/core/**"]}, at=T2, outcome="updated")
    repo.commit("and revalidated as updated", {"docs/a-engine.md": _crlf(updated)})
    result = _run(repo)
    assert _summary(result) == [("bump", "docs/a-engine.md", None, None)]
    assert "`outcome: updated`, but the content did not change" in result.findings[0].message


def test_a_working_tree_checked_out_with_crlf_is_read_as_git_s_objects_are(
    repo: AdopterRepo,
) -> None:
    """`core.autocrlf=true`: the working tree holds `\\r\\n` and the base `\\n`, and the
    head's answers read as they would with `\\n` — here, `unchanged` with its reason."""
    _start(repo, {"docs/guide.md": guide()})
    repo.git("config", "core.autocrlf", "true")
    repo.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    because = "a refactor: nothing the guide says moved"
    repo.write({"docs/guide.md": _crlf(guide(at=T2, because=because))})
    (finding,) = _run(repo).findings
    assert (finding.kind, finding.location, finding.answer) == (
        fc.FindingKind.ANSWERED,
        "docs/guide.md",
        fc.Answer.UNCHANGED,
    )
    assert because in finding.message


# --- new artefacts, the anchor list, moves ------------------------------------------------


def test_an_artefact_new_in_the_diff_counts_as_revalidated(repo: AdopterRepo) -> None:
    _start(repo, {})
    repo.commit(
        "a new page next to a CLI change",
        {"src/cli/main.py": "print('new')\n", "docs/guide.md": guide()},
    )
    assert _summary(_run(repo)) == [("answered", "docs/guide.md", None, "new")]


def test_changing_the_anchor_list_needs_a_revalidation(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "anchor the guide to the engine too",
        {"docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/core/**"]})},
    )
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", None, None)]
    assert "anchor list changed" in result.findings[0].message


def test_a_revalidation_answers_an_anchor_list_change(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "anchor the guide to the engine too, and revalidate",
        {
            "docs/guide.md": guide(
                anchors={"path": ["src/cli/**", "src/core/**"]},
                at=T2,
                because="the guide already covered the engine's part",
            )
        },
    )
    assert _summary(_run(repo)) == [("answered", "docs/guide.md", None, "unchanged")]


def test_a_move_needs_a_revalidation(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.rename("docs/guide.md", "docs/cli/guide.md")
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/cli/guide.md", None, None)]
    assert "moved here from docs/guide.md" in result.findings[0].message


def test_a_move_with_a_revalidation_is_answered(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.rename("docs/guide.md", "docs/cli/guide.md")
    repo.commit("revalidate the moved guide", {"docs/cli/guide.md": guide(at=T2, because="moved")})
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
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "anchor to a path that does not exist",
        {
            "docs/guide.md": guide(
                anchors={"path": ["src/cli/**", "src/gone/**"]}, at=T2, because="extended"
            )
        },
    )
    result = _run(repo)
    assert _summary(result) == [
        ("dead-anchor", "docs/guide.md", "path:src/gone/**", None),
        ("answered", "docs/guide.md", None, "unchanged"),
    ]
    assert result.findings[0].message == "matches no file; the anchor was added in this diff"


def test_a_pre_existing_dead_anchor_is_not_the_change_checks(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/gone/**"]})})
    repo.commit("an unrelated change", {"src/core/engine.py": "ENGINE = 3\n"})
    assert _summary(_run(repo)) == []


def test_a_target_removed_by_the_diff_turns_the_anchor_dead(repo: AdopterRepo) -> None:
    _start(
        repo,
        {
            "docs/guide.md": guide(anchors={"path": ["src/core/engine.py"]}),
            "docs/other.md": document(
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
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "a kind nothing resolves",
        {
            "docs/guide.md": guide(
                anchors={"path": ["src/cli/**"], "use-case": ["UC-1"]}, at=T2, because="x"
            )
        },
    )
    result = _run(repo)
    assert _summary(result)[0] == ("unresolved-kind", "docs/guide.md", "use-case:UC-1", None)
    assert "no installed component registers a resolver" in result.findings[0].message
    assert result.failing


def test_a_registered_resolver_without_the_query_contract_is_refused(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "anchor a registered kind",
        {"docs/guide.md": guide(anchors={"use-case": ["UC-1"]}, at=T2, because="x")},
    )
    script = repo.root / ".pkit/capabilities/software-analysis/scripts/resolve-use-case.py"
    undeclared = fc.ResolverCommand(
        "use-case", "software-analysis", "resolve-use-case", script=script
    )
    result = _run(repo, registry={"use-case": undeclared})
    assert "does not declare the query contract" in result.findings[0].message
    # Naming no command of its capability: refused as the kind is, and said before the
    # declaration is looked for (`test_friction_anchor_kinds` runs real resolvers).
    nameless = fc.ResolverCommand(
        "use-case", "software-analysis", "resolve-use-case", query_contract=True
    )
    result = _run(repo, registry={"use-case": nameless})
    assert result.findings[0].kind is fc.FindingKind.UNRESOLVED_KIND
    assert result.findings[0].message.startswith("nothing installed resolves this kind: ")
    assert "is not declared in the `commands:` of software-analysis" in result.findings[0].message


@pytest.mark.parametrize(
    ("query_contract", "refused"),
    [
        (False, "does not declare the query contract"),
        (True, None),
    ],
)
def test_refuse_resolver_without_query_contract(query_contract: bool, refused: str | None) -> None:
    resolver = fc.ResolverCommand(
        "use-case", "software-analysis", "resolve-use-case", query_contract=query_contract
    )
    reason = fc.refuse_resolver_without_query_contract(resolver)
    if refused is None:
        assert reason is None
    else:
        assert reason is not None and refused in reason


def test_a_project_with_no_capability_installed_registers_no_kind(repo: AdopterRepo) -> None:
    """The registry reads installed capabilities alone: the backbone and the adapter
    register nothing, whichever shipped capabilities would."""
    assert fc.registered_anchor_kinds(repo.root) == {}


def test_a_record_anchor_changes_with_its_decision_file(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide(anchors={"record": ["COR-050"]})})
    record = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
    text = (repo.root / record).read_text(encoding="utf-8")
    repo.commit("amend the record", {record: text + "\nAmended.\n"})
    assert _summary(_run(repo)) == [("friction", "docs/guide.md", "record:COR-050", None)]


def test_a_record_anchor_naming_no_record_is_dead(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "anchor a record that does not exist",
        {"docs/guide.md": guide(anchors={"record": ["COR-999"]}, at=T2, because="x")},
    )
    result = _run(repo)
    assert _summary(result)[0] == ("dead-anchor", "docs/guide.md", "record:COR-999", None)
    assert "names no record" in result.findings[0].message


def test_a_capability_decision_resolves_as_a_record(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    decisions = sorted((adopter.pkit / "capabilities" / "evidence" / "decisions").glob("DEC-*.md"))
    stem = decisions[0].stem
    number = "-".join(stem.split("-")[:2])
    _start(adopter, {"docs/guide.md": guide(anchors={"record": [f"evidence:{number}"]})})
    rel = decisions[0].relative_to(adopter.root).as_posix()
    adopter.commit("amend it", {rel: decisions[0].read_text(encoding="utf-8") + "\nMore.\n"})
    assert _summary(_run(adopter)) == [
        ("friction", "docs/guide.md", f"record:evidence:{number}", None)
    ]


# --- paths ------------------------------------------------------------------------------------


def test_excluded_paths_do_not_change_an_anchor(repo: AdopterRepo) -> None:
    _start(
        repo,
        {"docs/guide.md": guide(), "src/cli/generated/table.py": "T = 1\n"},
        config=friction_config(exclude=["src/cli/generated"]),
    )
    repo.commit("regenerate", {"src/cli/generated/table.py": "T = 2\n"})
    assert _summary(_run(repo)) == []


# --- a change to `friction.exclude` (COR-050 point 7) ---------------------------------------

_GENERATED = {"src/cli/generated/table.py": "T = 1\n"}


def _guide_and_notes() -> dict[str, str]:
    """`guide` covers the generated code through `src/cli/**`; `notes`, on the engine, does not."""
    notes = document("notes", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated")
    return {"docs/guide.md": guide(), "docs/notes.md": notes, **_GENERATED}


def test_a_widening_over_files_the_diff_leaves_alone_is_reported_not_owed(
    repo: AdopterRepo,
) -> None:
    """The anchor loses a file it stood on that nothing in the diff changes: reported, never
    failed — and an artefact whose anchors it does not cover hears nothing of it."""
    _start(repo, _guide_and_notes())
    widened = {CONFIG: friction_config(exclude=["src/cli/generated"])}
    repo.commit("exclude the generated code", widened)
    result = _run(repo)
    assert _summary(result) == [("left-out", "docs/guide.md", "path:src/cli/**", None)]
    assert result.findings[0].message == (
        "`friction.exclude` now leaves out 1 file this anchor stood on at the base "
        "(src/cli/generated/table.py); no change to it in this diff"
    )
    assert not result.failing


def test_a_widening_over_a_file_the_diff_changes_is_a_question(repo: AdopterRepo) -> None:
    """A widening never hides a change: a file it leaves out that the diff changes too is
    the anchor's question, answered like any other."""
    _start(repo, _guide_and_notes())
    repo.commit(
        "regenerate the table, and exclude it",
        {
            "src/cli/generated/table.py": "T = 2\n",
            CONFIG: friction_config(exclude=["src/cli/generated"]),
        },
    )
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert result.findings[0].message == (
        "`friction.exclude` changed over it in this diff (now leaves out "
        "src/cli/generated/table.py, which this diff also changes) and carries no answer: "
        "revalidate the artefact, or defer the anchor"
    )
    assert result.failing

    repo.commit(
        "the guide holds without the generated code",
        {"docs/guide.md": guide(at=T2, because="the generated table was never described")},
    )
    assert _summary(_run(repo)) == [("answered", "docs/guide.md", "path:src/cli/**", "unchanged")]


def test_a_widening_and_a_change_to_the_same_anchor_are_both_named(repo: AdopterRepo) -> None:
    """COR-050 point 7: the exclusion question and the content change are one question, and
    its message names both; a widening that asks nothing leaves the change's question alone
    and is reported beside it."""
    _start(repo, _guide_and_notes())
    repo.commit(
        "change the CLI, regenerate the table and exclude it",
        {
            "src/cli/main.py": "print('cli v2')\n",
            "src/cli/generated/table.py": "T = 2\n",
            CONFIG: friction_config(exclude=["src/cli/generated"]),
        },
    )
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert result.findings[0].message.startswith(
        "changed in this diff (src/cli/main.py), and `friction.exclude` changed over it (now "
        "leaves out src/cli/generated/table.py, which this diff also changes) and carries no "
        "answer"
    )

    repo.checkout("main")
    repo.checkout("second", create=True)
    repo.commit(
        "change the CLI and exclude the table, left alone",
        {
            "src/cli/main.py": "print('cli v3')\n",
            CONFIG: friction_config(exclude=["src/cli/generated"]),
        },
    )
    result = _run(repo)
    assert _summary(result) == [
        ("friction", "docs/guide.md", "path:src/cli/**", None),
        ("left-out", "docs/guide.md", "path:src/cli/**", None),
    ]
    assert result.findings[0].message.startswith("changed in this diff and carries no answer")


def test_a_file_removed_under_a_new_exclusion_is_a_change_never_left_out(
    repo: AdopterRepo,
) -> None:
    """A file that is gone is not left out: its removal is the anchor's change, whatever the
    diff's `friction.exclude` now says of its path."""
    _start(repo, _guide_and_notes())
    repo.commit(
        "drop the table, and exclude where it was",
        {
            "src/cli/generated/table.py": None,
            CONFIG: friction_config(exclude=["src/cli/generated"]),
        },
    )
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert result.findings[0].message.startswith("changed in this diff and carries no answer")


def test_a_narrowed_exclusion_is_always_a_question(repo: AdopterRepo) -> None:
    """The anchor gains a file it was never checked against: the narrowing is the change,
    and a file the diff changes too is named as such."""
    _start(repo, _guide_and_notes(), config=friction_config(exclude=["src/cli/generated"]))
    repo.commit("stop excluding the generated code", {CONFIG: friction_config()})
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert result.findings[0].message.startswith(
        "`friction.exclude` changed over it in this diff (now lets in "
        "src/cli/generated/table.py) and carries no answer"
    )
    assert result.failing

    repo.commit("regenerate, now let in", {"src/cli/generated/table.py": "T = 2\n"})
    (finding,) = _run(repo).findings
    assert "(now lets in src/cli/generated/table.py, which this diff also changes)" in (
        finding.message
    )


def test_a_file_added_and_excluded_in_the_same_diff_is_no_change(repo: AdopterRepo) -> None:
    """The anchor never stood on it: nothing was taken away, and nothing it stands on changed."""
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "generate a table, and exclude it",
        {**_GENERATED, CONFIG: friction_config(exclude=["src/cli/generated"])},
    )
    assert _summary(_run(repo)) == []


def test_an_exclusion_that_kills_an_anchor_is_named_as_why(repo: AdopterRepo) -> None:
    anchors = {"path": ["src/cli/**", "src/cli/generated/**"]}
    _start(repo, {"docs/guide.md": guide(anchors=anchors), **_GENERATED})
    repo.commit(
        "exclude the generated code", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )
    result = _run(repo)
    assert _summary(result) == [
        ("dead-anchor", "docs/guide.md", "path:src/cli/generated/**", None),
        ("left-out", "docs/guide.md", "path:src/cli/**", None),
    ]
    assert result.findings[0].message == "matches only excluded files (1), excluded since this diff"


def test_record_and_artefact_anchors_are_untouched_by_an_exclusion(repo: AdopterRepo) -> None:
    """Excluded paths cover paths (COR-050 point 7): excluding the file a record or an
    artefact anchor names asks nothing of it, and a change to the record still does."""
    record = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
    target = document("target", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated")
    anchored = guide(anchors={"record": ["COR-050"], "artefact": ["target"]})
    _start(repo, {"docs/guide.md": anchored, "docs/target.md": target})
    repo.commit(
        "exclude the record and the target",
        {CONFIG: friction_config(exclude=[".pkit/decisions", "docs/target.md"])},
    )
    assert _summary(_run(repo)) == []

    text = (repo.root / record).read_text(encoding="utf-8")
    repo.commit(
        "amend the record, and the target's body",
        {
            record: text + "\nAmended.\n",
            "docs/target.md": document(
                "target", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated", body="v2"
            ),
        },
    )
    assert _summary(_run(repo)) == [
        ("friction", "docs/guide.md", "record:COR-050", None),
        ("friction", "docs/guide.md", "artefact:target", None),
    ]


def test_an_artefact_under_an_excluded_path_owes_no_answer(repo: AdopterRepo) -> None:
    """COR-050 point 7, as the whole-repository check reads it (#1152): an anchor of an
    excluded artefact changing asks it nothing — while what it declares is still checked."""
    generated = guide(anchors={"path": ["src/cli/**"]})
    _start(
        repo,
        {"docs/guide.md": guide(), "docs/generated/cli.md": generated},
        config=friction_config(exclude=["docs/generated"]),
    )
    repo.commit(
        "change the CLI; the generated page gains an anchor that resolves to nothing",
        {
            "src/cli/main.py": "print('cli v2')\n",
            "docs/generated/cli.md": guide(anchors={"path": ["src/cli/**", "src/gone/**"]}),
        },
    )
    assert _summary(_run(repo)) == [
        ("dead-anchor", "docs/generated/cli.md", "path:src/gone/**", None),
        ("friction", "docs/guide.md", "path:src/cli/**", None),
    ]


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        pytest.param(guide(at=T2), ("bump", None), id="blind-stamp"),
        pytest.param(
            guide(at=T2, because="regenerated from the same CLI"),
            ("revalidated", "unchanged"),
            id="justified",
        ),
    ],
)
def test_the_bump_of_an_excluded_artefact_is_judged(
    repo: AdopterRepo, head: str, expected: tuple[str, str | None]
) -> None:
    """It owes no answer, but a new `at` is judged like any other: a stamp made while
    excluded is the blind bump COR-050 point 3 guards against."""
    _start(
        repo, {"docs/generated/cli.md": guide()}, config=friction_config(exclude=["docs/generated"])
    )
    repo.commit("restamp the generated page", {"docs/generated/cli.md": head})
    kind, answer = expected
    assert _summary(_run(repo)) == [(kind, "docs/generated/cli.md", None, answer)]


def test_an_artefact_excluded_in_the_diff_owes_no_answer_and_one_let_in_revalidates(
    repo: AdopterRepo,
) -> None:
    """Exclusion is read at head: the artefact a widening covers owes nothing from then on,
    and one a narrowing lets back in must revalidate in the same change, as a moved one
    must — the base never asked it anything (COR-050 point 7)."""
    files = {"docs/guide.md": guide(), "docs/generated/cli.md": guide()}
    _start(repo, files, config=friction_config(exclude=["docs/generated"]))
    repo.commit(
        "change the CLI, and exclude the guide instead",
        {
            "src/cli/main.py": "print('cli v2')\n",
            CONFIG: friction_config(exclude=["docs/guide.md"]),
        },
    )
    result = _run(repo)
    assert _summary(result) == [
        ("friction", "docs/generated/cli.md", "path:src/cli/**", None),
        ("friction", "docs/generated/cli.md", None, None),
    ]
    assert result.findings[1].message == (
        "this diff's `friction.exclude` lets it back in, which needs a revalidation (a new `at`) "
        "in the same change"
    )

    repo.commit(
        "revalidate the page let back in",
        {"docs/generated/cli.md": guide(at=T2, because="the page still describes the CLI")},
    )
    assert [kind for kind, *_ in _summary(_run(repo))] == ["answered", "answered"]


def test_a_base_whose_exclusions_do_not_read_is_read_as_head(repo: AdopterRepo) -> None:
    """A `friction.exclude` the base cannot read is not a base that leaves nothing out: it
    is reported, and read as head's, so no widening is made up from it."""
    _start(repo, _guide_and_notes(), config=friction_config(exclude=5))
    repo.commit(
        "write the exclusions as a list", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )
    result = _run(repo)
    assert _summary(result) == [("unreadable", CONFIG, None, None)]
    assert "`friction.exclude` does not read at the base (`friction.exclude` is int (5)" in (
        result.findings[0].message
    )
    assert not result.failing


def test_an_artefact_is_not_anchored_to_its_own_file(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide(anchors={"path": ["docs/**"]})})
    repo.commit(
        "edit the guide's body only",
        {"docs/guide.md": guide(anchors={"path": ["docs/**"]}, body="New.")},
    )
    assert _summary(_run(repo)) == []


def test_uncommitted_work_is_part_of_the_diff(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.write({"src/cli/main.py": "print('uncommitted')\n", "src/cli/new.py": "NEW = 1\n"})
    result = _run(repo)
    assert _summary(result) == [("friction", "docs/guide.md", "path:src/cli/**", None)]
    assert result.head is not None and result.head.uncommitted == 2
    assert "+ working tree, 2 uncommitted paths" in fc.render_human(result)


def test_places_are_read_from_each_side(repo: AdopterRepo) -> None:
    _start(repo, {"notes/guide.md": guide()})
    # Declaring the place makes the guide new at head, not stale.
    repo.commit(
        "declare notes as a place",
        {CONFIG: friction_config(places=("docs", "notes")), "src/cli/main.py": "print('x')\n"},
    )
    assert _summary(_run(repo)) == [("answered", "notes/guide.md", None, "new")]


def test_a_capability_place_in_the_package_schema_shape_is_checked(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The place is read from each side's package metadata as `{path, location?}`."""
    repo = make_adopter_repo(capabilities=("evidence",))
    package = repo.root / ".pkit/capabilities/evidence/package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8")
        + "docs:\n  locations:\n    runs: {path: evidence}\n"
        + "friction:\n  places:\n    - {location: runs, path: '**/*.md'}\n",
        encoding="utf-8",
    )
    _start(repo, {"docs/evidence/guide.md": guide()}, config=friction_config(places=()))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('cli v6')\n"})
    assert _summary(_run(repo)) == [("friction", "docs/evidence/guide.md", "path:src/cli/**", None)]


# --- the base -----------------------------------------------------------------------------------


def test_an_outdated_base_is_reported_and_never_fails(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()}, config=friction_config(mode="enforcing"))
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
    _start(repo, {"docs/guide.md": guide()})
    base = repo.head()
    result = _run(repo)
    assert result.base is not None
    assert (result.base.commit, result.base.outdated) == (base, False)
    assert f"Base: main at {base[:12]}" in fc.render_human(result)


def test_a_base_that_does_not_resolve_is_an_error(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    with pytest.raises(fc.FrictionCheckError, match="does not resolve"):
        fc.run_change_check(repo.root, "no-such-branch")
    result = _cli("--base", "no-such-branch")
    assert result.exit_code == 1 and "does not resolve" in result.output


def test_a_base_sharing_no_history_is_an_error(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    repo.git("checkout", "-q", "--orphan", "unrelated")
    repo.commit("an unrelated root", files=None)
    with pytest.raises(fc.FrictionCheckError, match="share no history"):
        fc.run_change_check(repo.root, "main")


# --- modes, dormancy, output ---------------------------------------------------------------------


def _cli(*args: str, env: dict[str, str] | None = None) -> Any:
    return CliRunner().invoke(main, ["friction", "check", *args], env=env)


def test_warning_mode_reports_and_passes(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()}, config=friction_config(mode="warning"))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('w')\n"})
    result = _cli("--base", "main")
    assert result.exit_code == 0, result.output
    assert "friction" in result.output
    assert "Result: passed" in result.output and "reported, not failed" in result.output


def test_enforcing_mode_fails_on_friction(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()}, config=friction_config(mode="enforcing"))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('e')\n"})
    result = _cli("--base", "main")
    assert result.exit_code == 1, result.output
    assert "Result: failed" in result.output


def test_enforcing_mode_passes_a_revalidated_change(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()}, config=friction_config(mode="enforcing"))
    repo.commit(
        "change the CLI and revalidate",
        {"src/cli/main.py": "print('r')\n", "docs/guide.md": guide(at=T2, because="still true")},
    )
    result = _cli("--base", "main")
    assert result.exit_code == 0, result.output


def test_the_base_comes_from_the_environment(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    result = _cli("--json", env={fc.BASE_ENV: "main"})
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["base"]["ref"] == "main"
    # No remote here: the base is read from the local branch, and the check says so.
    assert "warning: the base 'main' is read from the local branch 'main'" in result.stderr


def test_dormant_without_places(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()}, config=json.dumps({"friction": {"mode": "enforcing"}}))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('d')\n"})
    result = _cli("--base", "main")
    assert result.exit_code == 0, result.output
    assert "no places declared; dormant." in result.output


@pytest.mark.parametrize("places", [(), ("docs",)], ids=["dormant", "awake"])
def test_a_mode_that_is_not_a_mode_reads_as_warning_and_says_so(
    repo: AdopterRepo, places: tuple[str, ...]
) -> None:
    _start(repo, {"docs/guide.md": guide()}, config=friction_config(mode="enforcin", places=places))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('m')\n"})
    result = _run(repo)
    assert (result.mode, result.exit_code) == ("warning", 0)
    assert "friction.mode 'enforcin' is not a mode; read as warning" in fc.render_human(result)


def test_dormant_demands_no_repository(tmp_path: Path) -> None:
    result = fc.run_change_check(tmp_path, "main")
    assert (result.dormant, result.base, result.head, result.exit_code) == (True, None, None, 0)


def test_dormant_when_nothing_carries_the_container(repo: AdopterRepo) -> None:
    _start(
        repo,
        {"docs/plain.md": "---\ntitle: Plain\n---\n\nText.\n"},
        config=friction_config("enforcing"),
    )
    repo.commit("change the CLI only", {"src/cli/main.py": "print('d')\n"})
    result = _run(repo)
    assert result.dormant and result.findings == () and result.exit_code == 0
    assert "none carrying the `pkit` container; dormant." in fc.render_human(result)


def test_json_document_shape(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()}, config=friction_config(mode="enforcing"))
    repo.commit("change the CLI only", {"src/cli/main.py": "print('j')\n"})
    result = _cli("--base", "main", "--json")
    assert result.exit_code == 1
    document = json.loads(result.stdout)
    assert sorted(document) == [
        "base",
        "check",
        "counts",
        "dormant",
        "failed",
        "findings",
        "head",
        "mode",
        "schema_version",
    ]
    assert document["schema_version"] == fc.CHANGE_SCHEMA_VERSION == 1
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
    files["docs/guide.md"] = guide()
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
    _start(repo, {"docs/guide.md": guide()})
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
        "README.md": document("readme"),
        "docs/a.md": document("a"),
        "docs/.hidden.md": document("hidden"),
        "docs/sub/b.md": document("b"),
        "docs/sub/deep/c.md": document("c"),
        "docs/data.yaml": "pkit: {}\n",
        "notes/guide.md": guide(),
    }
    repo.write({CONFIG: friction_config(places=places), **files})
    on_disk = fd.discover_artefacts(repo.root)
    listed = fd.discover_artefacts(repo.root, tree=fc.WorkingTree(repo.root))
    assert [a.location for a in listed.artefacts] == [a.location for a in on_disk.artefacts]
    assert [a.place.pattern for a in listed.artefacts] == [
        a.place.pattern for a in on_disk.artefacts
    ]


def test_a_commit_tree_reads_what_the_commit_held(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": guide()})
    base = repo.head()
    repo.commit("rewrite", {"docs/guide.md": guide(body="Rewritten.")})
    tree = fc.CommitTree(repo.root, base)
    assert "docs/guide.md" in tree.files()
    assert tree.read_bytes(["docs/guide.md", "missing.md"]) == {
        "docs/guide.md": guide().encode(),
        "missing.md": None,
    }
