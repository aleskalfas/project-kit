"""Tests for an artefact anchor on an id two artefacts share (Task #1818; COR-050 points
7 and 12).

Two artefacts may carry one id, as two analyses, or two components' places, could
give one. An anchor on that id names one of them only by the backbone's choice:
the first in walk order (`Discovery.find`). It is ambiguous, as an anchor on a
point id or a slug two share is, but warned of and never failed: both checks
report it as `shared-id`, naming every artefact with the id and the one it
stands on, enforcing mode passes it, and validation does not report it. Its
other findings are judged on the artefact it stands on. The change check reports
it where the change made it so — it added the anchor, no two artefacts had the
id at the base, or the artefact it stands on differs from the base's — and the
whole-repository check reports every one.
"""

from __future__ import annotations

import pytest

from project_kit import artefact_parts as ap
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit import friction_validate as fv
from project_kit.friction_check import record_naming
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, MANUAL, Timeline, friction_config, guide, manual

#: A second document with the manual's id, read after it: its path sorts after
#: `docs/manual.md`, so the walk meets it second.
LATER = "docs/zz-manual.md"

#: A second document with the manual's id, read before it.
EARLIER = "docs/a-manual.md"

ON_MANUAL = {"artefact": ["manual"]}
ON_USING = {"artefact": ["manual#using"]}


def _other_manual() -> str:
    """Another document with the id `manual`, its text the manual's but for its lead."""
    return manual(lead="Another manual, with the same id.")


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


def _start(timeline: Timeline, files: dict[str, str], *, mode: str = "warning") -> str:
    base = timeline.start(files, config=friction_config(mode=mode))
    timeline.adopter.checkout("feature", create=True)
    return base


def _findings(result: fc.ChangeCheck) -> list[tuple[str, str | None]]:
    return [(f.kind.value, None if f.anchor is None else f.anchor.value) for f in result.findings]


# --- the one reading ----------------------------------------------------------------


def _read(adopter: AdopterRepo, value: str) -> ap.AnchoredPart:
    discovery = fd.discover_artefacts(adopter.root)
    return ap.anchored_part(discovery, value, lambda path: record_naming(adopter.root, path))


def test_every_artefact_with_the_id_is_named_and_the_first_is_read(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo()
    adopter.write({CONFIG: friction_config(), MANUAL: manual(), EARLIER: _other_manual()})
    discovery = fd.discover_artefacts(adopter.root)
    assert [a.path for a in discovery.named("manual")] == [EARLIER, MANUAL]
    first = discovery.find("manual")
    assert first is not None and first.path == EARLIER
    assert [a.path for a in discovery.named(MANUAL)] == [MANUAL]  # a path names one

    whole = _read(adopter, "manual")
    assert (whole.state, whole.target and whole.target.path) == (ap.PartState.WHOLE, EARLIER)
    assert whole.namesakes == (EARLIER, MANUAL)
    assert whole.shared_id == (
        f"is ambiguous: 2 artefacts have the id manual ({EARLIER}, {MANUAL}); read as naming "
        f"{EARLIER} — give them ids no two share, or name a document by its path"
    )
    part = _read(adopter, "manual#using")
    assert (part.state, part.target and part.target.path) == (ap.PartState.LIVE, EARLIER)
    assert part.namesakes == (EARLIER, MANUAL)
    assert part.shared_id is not None and part.shared_id.startswith("is ambiguous: 2 artefacts")


def test_an_id_one_artefact_has_is_not_shared(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo()
    adopter.write({CONFIG: friction_config(), MANUAL: manual()})
    for value in ("manual", "manual#using", MANUAL, f"{MANUAL}#", "nothing"):
        found = _read(adopter, value)
        assert (found.namesakes, found.shared_id) == ((), None)


# --- the change check ---------------------------------------------------------------


def test_an_artefact_the_change_gives_the_id_is_warned_of_and_fails_nothing(
    timeline: Timeline,
) -> None:
    _start(
        timeline,
        {MANUAL: manual(), "docs/guide.md": guide(anchors=ON_MANUAL)},
        mode="enforcing",
    )
    timeline.commit("a second manual", {LATER: _other_manual()})
    result = fc.run_change_check(timeline.adopter.root, "main")
    assert _findings(result) == [("shared-id", "manual")]
    (warning,) = result.findings
    assert warning.location == "docs/guide.md"
    assert warning.message == (
        f"is ambiguous: 2 artefacts have the id manual ({MANUAL}, {LATER}); read as naming "
        f"{MANUAL} — give them ids no two share, or name a document by its path; no two "
        f"artefacts had the id at the base"
    )
    assert (result.failed, result.exit_code) == (False, 0)
    assert '"shared-id": 1' in fc.render_json(result)
    human = fc.render_human(result)
    assert "shared-id" in human and "Result: passed" in human


def test_a_change_that_makes_the_anchor_read_another_artefact_is_friction_too(
    timeline: Timeline,
) -> None:
    """An artefact the walk meets first takes the anchor over: what it stands on differs,
    so the dependant owes an answer, and the warning names the artefact it now reads."""
    _start(timeline, {MANUAL: manual(), "docs/guide.md": guide(anchors=ON_MANUAL)})
    timeline.commit("an earlier manual", {EARLIER: _other_manual()})
    result = fc.run_change_check(timeline.adopter.root, "main")
    assert sorted(_findings(result)) == [("friction", "manual"), ("shared-id", "manual")]
    (warning,) = [f for f in result.findings if f.kind is fc.FindingKind.SHARED_ID]
    assert f"read as naming {EARLIER}" in warning.message


def test_a_change_that_moves_the_choice_on_a_shared_id_is_warned_of(timeline: Timeline) -> None:
    """The id was shared at the base already, and a third artefact, read first, takes the
    anchor over: the change owns the warning, which says so beside the friction."""
    _start(
        timeline,
        {MANUAL: manual(), LATER: _other_manual(), "docs/guide.md": guide(anchors=ON_MANUAL)},
    )
    timeline.commit("an earlier manual", {EARLIER: manual(lead="A third manual.")})
    result = fc.run_change_check(timeline.adopter.root, "main")
    assert sorted(_findings(result)) == [("friction", "manual"), ("shared-id", "manual")]
    (warning,) = [f for f in result.findings if f.kind is fc.FindingKind.SHARED_ID]
    assert warning.message.startswith("is ambiguous: 3 artefacts have the id manual")
    assert warning.message.endswith("; the diff changed which of them it stands on")


def test_a_rename_of_the_artefact_read_moves_no_choice(timeline: Timeline) -> None:
    _start(
        timeline,
        {MANUAL: manual(), LATER: _other_manual(), "docs/guide.md": guide(anchors=ON_MANUAL)},
    )
    timeline.rename(MANUAL, "docs/b-manual.md")
    assert _findings(fc.run_change_check(timeline.adopter.root, "main")) == []


def test_an_anchor_the_change_adds_on_a_shared_id_is_warned_of(timeline: Timeline) -> None:
    _start(timeline, {MANUAL: manual(), LATER: _other_manual(), "docs/guide.md": guide()})
    timeline.commit(
        "anchor the manual's section",
        {"docs/guide.md": guide(anchors={"path": ["src/cli/**"], **ON_USING})},
    )
    result = fc.run_change_check(timeline.adopter.root, "main")
    assert ("shared-id", "manual#using") in _findings(result)
    (warning,) = [f for f in result.findings if f.kind is fc.FindingKind.SHARED_ID]
    assert warning.message.endswith("; the anchor was added in this diff")


def test_an_id_shared_before_the_change_is_the_whole_repository_check_s(
    timeline: Timeline,
) -> None:
    _start(
        timeline,
        {MANUAL: manual(), LATER: _other_manual(), "docs/guide.md": guide(anchors=ON_MANUAL)},
    )
    timeline.commit("touch the sources", {"src/cli/main.py": "print('cli, again')\n"})
    assert _findings(fc.run_change_check(timeline.adopter.root, "main")) == []
    result = fr.run_repository_check(timeline.adopter.root)
    assert [(f.kind.value, f.anchor and f.anchor.value) for f in result.findings] == [
        ("shared-id", "manual")
    ]
    (report,) = result.artefact_reports
    assert report.state is fr.ArtefactState.CURRENT  # judged on the one it reads
    assert '"shared-id": 1' in fr.render_json(result)
    assert "1 anchor on a shared id" in fr.render_human(result)


def test_the_explanation_says_what_mends_it(timeline: Timeline) -> None:
    _start(
        timeline,
        {MANUAL: manual(), LATER: _other_manual(), "docs/guide.md": guide(anchors=ON_MANUAL)},
    )
    explanation = frep.run_explain(timeline.adopter.root, "docs/guide.md")
    (finding,) = explanation.findings
    assert finding.finding.kind is fr.RepositoryFindingKind.SHARED_ID
    assert finding.clears.startswith("give the artefacts that share its id ids no two share")


# --- validation -----------------------------------------------------------------------


def test_validation_does_not_fail_an_anchor_on_a_shared_id(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo()
    adopter.write(
        {
            CONFIG: friction_config(),
            MANUAL: manual(),
            LATER: _other_manual(),
            "docs/guide.md": guide(anchors={"artefact": ["manual", "manual#using"]}),
        }
    )
    result = fv.validate_friction(adopter.root)
    assert result.errors == ()
    assert not [f for f in result.findings if "ambiguous" in f.message]


def test_a_part_is_judged_on_the_artefact_the_anchor_stands_on(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The artefact read first has no `Using` section, so the anchor is dead there, though
    the other artefact with the id has one: validation fails it as any dead part anchor."""
    adopter = make_adopter_repo()
    adopter.write(
        {
            CONFIG: friction_config(),
            MANUAL: manual(),
            EARLIER: manual(sections=(("Installing", "Run the installer."),)),
            "docs/guide.md": guide(anchors=ON_USING),
        }
    )
    (error,) = fv.validate_friction(adopter.root).errors
    assert error.kind is fv.FrictionFindingKind.DEAD_SECTION_ANCHOR
    assert "is dead: manual has no heading whose slug is using" in error.message
    read = _read(adopter, "manual#using").target
    assert read is not None and read.path == EARLIER
