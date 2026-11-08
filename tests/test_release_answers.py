"""The release step answers the friction its version edits raise (PRJ-014, #2378).

After `pkit release apply` writes, the release step writes an `unchanged` answer for
each artefact the change check asks about only because of version lines the release
rewrote, and that states none of the versions those lines held. Every other artefact
stays asked, named with why. Each test stands up a small source kit in a git
repository, with a friction place holding the documents, releases it in this process,
and reads what the step wrote and what the change check then asks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import answer_files as af
from project_kit import friction_check as fc
from project_kit import release, release_answers
from project_kit.cli import main
from project_kit.friction_discovery import Anchor
from project_kit.friction_git import FrictionCheckError
from tests.adopter_repo import GitRepo
from tests.test_answer_files import answer_path, answers, entry

PACKAGE = ".pkit/capabilities/demo/package.yaml"
T1 = "2026-10-01T09:00:00Z"
T2 = "2026-10-02T09:00:00Z"

_safe = YAML(typ="safe")


def _package(version: str = "0.3.0", backbone: str = ">=1.0.0,<1.6.0") -> str:
    return (
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        "  name: demo\n"
        f"  version: {version}\n"
        "description: Draws boxes.\n"
        f'requires_backbone: "{backbone}"\n'
    )


def _document(body: str, anchors: list[str] | None = None) -> str:
    front = {"pkit": {"friction": {"anchors": {"path": anchors or [PACKAGE]}}}}
    return f"---\n{json.dumps(front, indent=2)}\n---\n\n{body}\n"


def _changeset(root: Path, component: str, kind: str, name: str = "a.yaml") -> None:
    folder = root / ".changes" / "unreleased"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(
        f"component: {component}\nkind: {kind}\nbody: A change.\n", encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """A source kit at backbone 1.5.0 with one capability, `demo` at 0.3.0, and a
    friction place, `docs`, in enforcing mode, committed."""
    repo = GitRepo.init(tmp_path)
    repo.commit(
        "seed",
        {
            ".pkit/VERSION": "1.5.0\n",
            PACKAGE: _package(),
            ".pkit/project/config.yaml": json.dumps(
                {"name": "kit", "friction": {"mode": "enforcing", "places": ["docs"]}}
            )
            + "\n",
            "CHANGELOG.md": "# Changelog\n",
            "src/demo.py": "BOXES = 1\n",
        },
    )
    monkeypatch.chdir(tmp_path)
    return repo


def _release(repo: GitRepo, *changesets: tuple[str, str]) -> release_answers.ReleaseAnswers:
    """Commit what the test wrote and the changesets, and release them: the release step
    ends with its answers."""
    for index, (component, kind) in enumerate(changesets or (("demo", "minor"),)):
        _changeset(repo.root, component, kind, f"c{index}.yaml")
    repo.commit("before the release", None)
    kit = repo.root / ".pkit"
    return release.apply_release(kit, release.compute_release(kit))


def _asked(repo: GitRepo) -> list[tuple[str, str | None]]:
    """What the change check fails on over the release's writes and answers."""
    result = fc.run_change_check(repo.root, "HEAD")
    return [(f.kind.value, f.location) for f in result.failing]


def _entries(answer_file: str | None, root: Path) -> list[dict[str, Any]]:
    assert answer_file is not None
    return _safe.load((root / answer_file).read_text(encoding="utf-8"))["answers"]


# --- what the release answers ---------------------------------------------------------


def test_a_document_that_states_no_version_is_answered_and_the_check_passes(
    repo: GitRepo,
) -> None:
    repo.write({"docs/plain.md": _document("The demo capability draws boxes.")})

    found = _release(repo)

    assert found.answered == ("docs/plain.md",)
    assert found.left == ()
    assert found.file is not None and af.is_answer_file(found.file)
    (only,) = _entries(found.file, repo.root)
    assert only["artefact"] == "docs/plain.md"
    assert only["revalidated"]["outcome"] == "unchanged"
    assert only["revalidated"]["unchanged-because"] == (
        "The release rewrote only version lines in the files this artefact anchors. "
        f"In {PACKAGE}, `version: 0.3.0` became `version: 0.4.0`. The artefact states none "
        "of the versions those lines held, 0.3.0, so what it says still holds. The release "
        "step wrote this answer (PRJ-014)."
    )
    assert _asked(repo) == []


def test_the_release_diff_with_its_answers_is_still_a_release(repo: GitRepo) -> None:
    repo.write({"docs/plain.md": _document("The demo capability draws boxes.")})

    found = _release(repo)
    base = repo.head()
    repo.commit("chore(release): v1.5.0", None)

    assert found.file is not None
    assert release.is_release_diff(repo.root / ".pkit", base)


def test_a_document_that_states_a_version_a_line_held_is_left_and_still_asked(
    repo: GitRepo,
) -> None:
    repo.write(
        {
            "docs/plain.md": _document("The demo capability draws boxes."),
            "docs/states.md": _document("Its libraries need release 0.3.0 of the capability."),
        }
    )

    found = _release(repo)

    assert found.answered == ("docs/plain.md",)
    assert found.left == (
        release_answers.Left(
            "docs/states.md", "it states 0.3.0, which a line the release rewrote held"
        ),
    )
    assert _asked(repo) == [("friction", "docs/states.md")]


def test_a_version_the_rewritten_lines_still_hold_is_no_reason_to_ask(repo: GitRepo) -> None:
    # A backbone release widens the range's upper bound, 1.6.0 to 1.7.0, and keeps its
    # floor 1.0.0: a document that names the floor is answered, one that names the old
    # upper bound is left.
    repo.write(
        {
            "docs/floor.md": _document("It needs backbone 1.0.0 or later."),
            "docs/bound.md": _document("It runs on backbones before 1.6.0."),
        }
    )

    found = _release(repo, ("backbone", "minor"))

    assert found.answered == ("docs/floor.md",)
    assert [left.location for left in found.left] == ["docs/bound.md"]
    (only,) = _entries(found.file, repo.root)
    assert (
        f'In {PACKAGE}, `requires_backbone: ">=1.0.0,<1.6.0"` became '
        '`requires_backbone: ">=1.0.0,<1.7.0"`.' in only["revalidated"]["unchanged-because"]
    )


def test_a_version_counts_as_stated_only_as_a_whole_number(repo: GitRepo) -> None:
    repo.write(
        {
            "docs/longer.md": _document("Not 10.3.0, nor 0.3.0.1, nor 0.3.01."),
            "docs/tagged.md": _document("Released as v0.3.0."),
        }
    )

    found = _release(repo)

    assert found.answered == ("docs/longer.md",)
    assert [left.location for left in found.left] == ["docs/tagged.md"]


def test_a_version_in_the_documents_own_fields_counts_as_stated(repo: GitRepo) -> None:
    front = {"needs": "0.3.0", "pkit": {"friction": {"anchors": {"path": [PACKAGE]}}}}
    repo.write({"docs/fields.md": f"---\n{json.dumps(front)}\n---\n\nBoxes.\n"})

    found = _release(repo)

    assert found.answered == ()
    assert [left.location for left in found.left] == ["docs/fields.md"]


# --- what the release leaves to a person ----------------------------------------------


def test_a_document_asked_about_another_write_of_the_release_is_left(repo: GitRepo) -> None:
    repo.write({"docs/log.md": _document("The changelog lists each release.", ["CHANGELOG.md"])})

    found = _release(repo)

    assert found.answered == ()
    assert found.left == (
        release_answers.Left(
            "docs/log.md",
            "its anchor CHANGELOG.md stands on CHANGELOG.md, which the release changed in "
            "more than version lines",
        ),
    )
    assert _asked(repo) == [("friction", "docs/log.md")]


def test_a_document_whose_anchor_reaches_a_changeset_too_is_left(repo: GitRepo) -> None:
    # A file the release keeps holds the `.changes/**` anchor live once it deletes
    # every changeset.
    repo.write(
        {
            "docs/all.md": _document("The tree.", [".pkit/**", ".changes/**"]),
            ".changes/README.md": "Changesets.\n",
        }
    )

    found = _release(repo)

    assert found.answered == ()
    (left,) = found.left
    assert left.location == "docs/all.md"
    assert ".changes/unreleased/c0.yaml" in left.why


def test_a_package_file_changed_beyond_its_version_lines_leaves_its_documents(
    repo: GitRepo,
) -> None:
    repo.write({"docs/plain.md": _document("The demo capability draws boxes.")})
    repo.commit("the document", None)
    # An edit rides along in the package file, uncommitted when the release runs.
    _changeset(repo.root, "demo", "minor")
    repo.commit("the changeset", None)
    (repo.root / PACKAGE).write_text(
        _package().replace("Draws boxes.", "Draws circles."), encoding="utf-8"
    )
    kit = repo.root / ".pkit"

    found = release.apply_release(kit, release.compute_release(kit))

    assert found.answered == ()
    assert found.left == (
        release_answers.Left(
            "docs/plain.md",
            f"its anchor {PACKAGE} stands on {PACKAGE}, which the release changed in more "
            "than version lines",
        ),
    )


def test_a_document_with_a_live_deferral_is_left(repo: GitRepo) -> None:
    repo.write(
        {
            "docs/deferred.md": _document("Boxes.", [PACKAGE, "src/demo.py"]),
            answer_path("20261001T090000Z-aaaaaaaa"): answers(
                entry(
                    "docs/deferred.md",
                    at=T1,
                    deferred=[(Anchor("path", "src/demo.py"), "#12 rewrites the page")],
                )
            ),
        }
    )

    found = _release(repo)

    assert found.answered == ()
    assert found.left == (
        release_answers.Left("docs/deferred.md", "it carries a live deferral of path:src/demo.py"),
    )


def test_a_document_whose_answers_were_made_apart_is_left(repo: GitRepo) -> None:
    repo.write(
        {
            "docs/apart.md": _document("Boxes."),
            answer_path("20261001T090000Z-aaaaaaaa"): answers(
                entry("docs/apart.md", at=T1, because="one line of work read it")
            ),
            answer_path("20261002T090000Z-bbbbbbbb"): answers(
                entry("docs/apart.md", at=T2, because="another line of work read it")
            ),
        }
    )

    found = _release(repo)

    assert found.answered == ()
    assert found.left == (
        release_answers.Left(
            "docs/apart.md", "its answers were made apart, and their combined state needs judging"
        ),
    )


def test_an_answer_the_check_does_not_accept_is_taken_back(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo.write(
        {
            "docs/plain.md": _document("The demo capability draws boxes."),
            "docs/other.md": _document("Boxes again."),
        }
    )
    real = release_answers._not_standing

    def flags_one(result: fc.ChangeCheck, written: str) -> dict[str, str]:
        assert real(result, written) == {}
        return {"docs/other.md": "taken back for the test"}

    monkeypatch.setattr(release_answers, "_not_standing", flags_one)

    found = _release(repo)

    assert found.answered == ("docs/plain.md",)
    assert found.left == (release_answers.Left("docs/other.md", "taken back for the test"),)
    folder = repo.root / af.FOLDER
    assert [p.relative_to(repo.root).as_posix() for p in folder.glob("*.yaml")] == [found.file]
    assert [e["artefact"] for e in _entries(found.file, repo.root)] == ["docs/plain.md"]
    assert _asked(repo) == [("friction", "docs/other.md")]


# --- where it writes nothing ----------------------------------------------------------


def test_a_project_with_no_friction_place_gets_no_answer(repo: GitRepo) -> None:
    repo.write({".pkit/project/config.yaml": json.dumps({"name": "kit"}) + "\n"})

    found = _release(repo)

    assert found == release_answers.ReleaseAnswers()
    assert not (repo.root / af.FOLDER).exists()


# --- the command ----------------------------------------------------------------------


def test_release_apply_says_what_it_answered_and_what_it_left(repo: GitRepo) -> None:
    repo.write(
        {
            "docs/plain.md": _document("The demo capability draws boxes."),
            "docs/states.md": _document("Its libraries need release 0.3.0."),
        }
    )
    _changeset(repo.root, "demo", "minor")
    repo.commit("before the release", None)

    result = CliRunner().invoke(main, ["release", "apply", "--yes"])

    assert result.exit_code == 0, result.output
    (answer_file,) = (repo.root / af.FOLDER).glob("*.yaml")
    rel = answer_file.relative_to(repo.root).as_posix()
    assert (
        "Answered 1 artefact(s) the release's version edits ask about, in "
        f"{rel} (PRJ-014):\n  docs/plain.md\n"
        "Left 1 artefact(s) for a person to answer on the release branch before it merges "
        "(`pkit friction check` lists them):\n"
        "  docs/states.md: it states 0.3.0, which a line the release rewrote held\n"
    ) in result.output


def test_release_apply_warns_and_writes_no_answer_where_the_check_cannot_run(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo.write({"docs/plain.md": _document("The demo capability draws boxes.")})
    _changeset(repo.root, "demo", "minor")
    repo.commit("before the release", None)

    def cannot_run(_source_kit: Path) -> release_answers.ReleaseAnswers:
        raise FrictionCheckError("git is gone.")

    monkeypatch.setattr(release_answers, "write_release_answers", cannot_run)

    result = CliRunner().invoke(main, ["release", "apply", "--yes"])

    assert result.exit_code == 0, result.output
    assert "0.4.0" in (repo.root / PACKAGE).read_text(encoding="utf-8")
    assert not (repo.root / af.FOLDER).exists()
    assert (
        "warning: the release wrote no answers, since the change check cannot run: git is "
        "gone. Answer what `pkit friction check` asks of the release by hand."
    ) in result.stderr
