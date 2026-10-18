"""Tests for a link whose source's change revisits its targets (#1667, COR-050 point 16).

A fixture capability, `linker`, declares one place, `reqs`, and on it a link:
its sources list their targets in the own field `verified-by`, and a change to
`statement` or `threshold` asks for a revisit of each. Every test stands up a
real adopter repository (`make_adopter_repo`), commits a base state on `main`,
branches `feature` off it and makes real commits before running the change
check against `main`. The tests cover the declaration and its validation, the
change check's findings and answers, validation's findings on the entries and
the link's field, and the `revisit` writer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_validate as fv
from project_kit import friction_write as fw
from project_kit import package_validate as pv
from project_kit.cli import main
from project_kit.manifest import (
    ORIGIN_KIT_SHIPPED,
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T1, T2, document, friction_config

LINKER = "linker"
SOURCE_DOC = "reqs/latency.md"
TEST_FILE = "tests/test_latency.py"
DECISION = "tests/decision.md"

#: The fixture capability's link: `verified-by` lists the targets, and a change to
#: `statement` or `threshold` asks for a revisit of each.
LINK = (
    "      revisits:\n"
    "        - targets: verified-by\n"
    "          when: [statement, threshold]\n"
    "          description: A changed statement or threshold asks after each verifying file.\n"
)


def declare_linker(root: Path, places: str = f"    - path: reqs\n{LINK}") -> None:
    """The fixture capability `linker` at `.pkit/capabilities/linker/`, registered once in
    the backbone manifest, declaring `places` under `friction.places`: by default the
    place `reqs` with the one link `LINK`. Called again, it rewrites the declaration."""
    cap_dir = root / ".pkit" / "capabilities" / LINKER
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"schema_version: 2\ncomponent:\n  kind: capability\n  name: {LINKER}\n"
        f"  version: 0.1.0\ndescription: Fixture capability declaring a link that revisits its "
        f'targets.\nrequires_backbone: ">=0.1.0"\nfriction:\n  places:\n{places}',
        encoding="utf-8",
    )
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    if any(c.name == LINKER for c in backbone.components):
        return
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=LINKER,
            manifest=f".pkit/capabilities/{LINKER}/manifest.yaml",
            origin=ORIGIN_KIT_SHIPPED,
        )
    )
    write_backbone_manifest(root, backbone)


def requirement(
    *,
    statement: str = "Status answers in 2 seconds.",
    threshold: Any = "2 s",
    verified_by: Any = (TEST_FILE, DECISION),
    revisited: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> str:
    """`REQ-1`, the source: anchored to the test file and a document, both listed in
    `verified-by`, revalidated at T1. `revisited` writes its `revisited` list; a
    `threshold` or `verified_by` of `None` leaves the field out."""
    fields: dict[str, Any] = {"statement": statement}
    if threshold is not None:
        fields["threshold"] = threshold
    if verified_by is not None:
        fields["verified-by"] = list(verified_by) if isinstance(verified_by, tuple) else verified_by
    values: dict[str, Any] = {
        "anchors": {"path": [TEST_FILE, DECISION]},
        "at": T1,
        "outcome": "unchanged",
        "because": "the test and the decision say what the requirement says",
        "body": "Why it matters.",
        **fields,
    }
    values.update(overrides)
    text = document("REQ-1", **values)
    if revisited is None:
        return text
    front, body = text.split("\n---\n", 1)
    data = json.loads(front.removeprefix("---\n"))
    data["pkit"]["friction"]["revisited"] = revisited
    return f"---\n{json.dumps(data, indent=2)}\n---\n{body}"


def entry(outcome: str, reason: str, value: str = TEST_FILE, kind: str = "path") -> dict[str, Any]:
    return {"anchor": {"kind": kind, "value": value}, "outcome": outcome, "reason": reason}


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    adopter = make_adopter_repo()
    declare_linker(adopter.root)
    return adopter


def _start(
    adopter: AdopterRepo, files: dict[str, str] | None = None, config: str | None = None
) -> None:
    """Commit the base state on `main` and branch `feature` off it."""
    base = {
        CONFIG: config or friction_config(places=("docs",)),
        **SOURCE,
        TEST_FILE: "def test_latency():\n    assert answer_time() < 2\n",
        DECISION: "Cache the status.\n",
        SOURCE_DOC: requirement(),
    }
    adopter.write({**base, **(files or {})})
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


def _run(adopter: AdopterRepo) -> fc.ChangeCheck:
    return fc.run_change_check(adopter.root, "main")


def _revisits(result: fc.ChangeCheck) -> list[tuple[str, str | None, str | None]]:
    """(kind, target, answer) per finding about a target, in report order."""
    kinds = {fc.FindingKind.REVISITED, fc.FindingKind.UNREVISITED}
    return [
        (
            f.kind.value,
            None if f.anchor is None else f"{f.anchor.kind}:{f.anchor.value}",
            None if f.answer is None else f.answer.value,
        )
        for f in result.findings
        if f.kind in kinds
    ]


def _revisit_answers(result: fc.ChangeCheck) -> list[dict[str, Any]]:
    document = json.loads(fc.render_json(result))
    return [a for a in document["answers"] if a["answer"] == fc.REVISITED]


# --- the declaration --------------------------------------------------------------------


def test_a_capability_place_declares_its_links(repo: AdopterRepo) -> None:
    repo.write({CONFIG: friction_config(places=("docs",)), SOURCE_DOC: requirement()})
    discovery = fd.discover_artefacts(repo.root)
    (source,) = [a for a in discovery.artefacts if a.path == SOURCE_DOC]
    (link,) = discovery.links(source)
    assert (link.targets, link.when) == ("verified-by", ("statement", "threshold"))
    assert link.pointer == "/friction/places/0/revisits/0"
    assert fd.link_targets(source, link) == (
        fd.Anchor("path", TEST_FILE),
        fd.Anchor("path", DECISION),
    )


def test_a_project_place_declares_no_link_and_switches_none_off(repo: AdopterRepo) -> None:
    # The project's root-wide place is walked first; the component's link still holds.
    repo.write({CONFIG: friction_config(places=("**",)), SOURCE_DOC: requirement()})
    discovery = fd.discover_artefacts(repo.root)
    (source,) = [a for a in discovery.artefacts if a.path == SOURCE_DOC]
    assert source.place.source == "project"
    assert [link.targets for link in discovery.links(source)] == ["verified-by"]


def test_the_package_schema_refuses_a_malformed_link(repo: AdopterRepo) -> None:
    declare_linker(
        repo.root,
        "    - path: reqs\n"
        "      revisits:\n"
        "        - {targets: pkit, when: [statement]}\n"
        "        - {targets: verified-by, when: []}\n"
        "        - {targets: verified-by}\n"
        "        - {targets: verified-by, when: [statement], extra: 1}\n"
        "        - {targets: verified-by, when: [statement]}\n",
    )
    repo.write({CONFIG: friction_config(places=("docs",))})
    errors = {
        finding.path
        for report in pv.validate_installed_packages(repo.root).reports
        if report.file == repo.root / ".pkit/capabilities/linker/package.yaml"
        for finding in report.findings
        if finding.severity is pv.Severity.ERROR
    }
    assert errors == {
        "/friction/places/0/revisits/0/targets",
        "/friction/places/0/revisits/1/when",
        "/friction/places/0/revisits/2",
        "/friction/places/0/revisits/3/extra",
    }
    # Read forgivingly: a link the schema refuses declares nothing.
    (place,) = [p for p in fd.read_friction_settings(repo.root).places if p.is_capability]
    assert [(link.targets, link.when) for link in place.revisits] == [
        ("verified-by", ("statement",)),
        ("verified-by", ("statement",)),
    ]


# --- the change check -----------------------------------------------------------------


def test_a_triggered_target_neither_changed_nor_answered_fails(repo: AdopterRepo) -> None:
    _start(repo, config=friction_config(mode="enforcing", places=("docs",)))
    repo.commit("relax the threshold", {SOURCE_DOC: requirement(threshold="10 s")})
    result = _run(repo)
    assert _revisits(result) == [
        ("unrevisited", f"path:{TEST_FILE}", None),
        ("unrevisited", f"path:{DECISION}", None),
    ]
    message = next(f.message for f in result.findings if f.kind is fc.FindingKind.UNREVISITED)
    assert "its `threshold` changed in this diff, and `verified-by` lists this target" in message
    assert result.failed and result.exit_code == 1
    assert "2 targets not revisited" in fc.render_human(result)


def test_warning_mode_reports_and_passes(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit("relax the threshold", {SOURCE_DOC: requirement(threshold="10 s")})
    result = _run(repo)
    assert {kind for kind, _target, _answer in _revisits(result)} == {"unrevisited"}
    assert not result.failed


def test_a_target_changed_in_the_change_is_revisited_and_listed(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit(
        "relax the threshold, and the test with it",
        {
            SOURCE_DOC: requirement(threshold="10 s"),
            TEST_FILE: "def test_latency():\n    assert answer_time() < 10\n",
            DECISION: "Cache the status: it answers in 10 seconds without one.\n",
        },
    )
    result = _run(repo)
    assert _revisits(result) == [
        ("revisited", f"path:{TEST_FILE}", "updated"),
        ("revisited", f"path:{DECISION}", "updated"),
    ]
    answers = _revisit_answers(result)
    assert [(a["target"]["value"], a["outcome"], a["asked"], a["reason"]) for a in answers] == [
        (DECISION, "updated", True, None),
        (TEST_FILE, "updated", True, None),
    ]
    assert answers[0]["links"] == ["verified-by"] and answers[0]["fields"] == ["threshold"]
    human = fc.render_human(result)
    assert (
        f"{SOURCE_DOC} names {TEST_FILE} through verified-by, and this change modifies its "
        f"threshold. Updated in this change" in human
    )


def test_an_entry_written_in_the_change_answers(repo: AdopterRepo) -> None:
    _start(repo, config=friction_config(mode="enforcing", places=("docs",)))
    repo.commit(
        "relax the threshold; the test and the decision still stand",
        {
            SOURCE_DOC: requirement(
                threshold="10 s",
                revisited=[
                    entry("unchanged", "the test asserts under 2 s, which meets 10 s too"),
                    entry("deferred", "the cache decision is revisited in #9999", DECISION),
                ],
            )
        },
    )
    result = _run(repo)
    assert _revisits(result) == [
        ("revisited", f"path:{TEST_FILE}", "unchanged"),
        ("revisited", f"path:{DECISION}", "deferred"),
    ]
    assert not result.failed
    answers = _revisit_answers(result)
    assert [(a["target"]["value"], a["outcome"], a["asked"], a["status"]) for a in answers] == [
        (DECISION, "deferred", True, "stands"),
        (TEST_FILE, "unchanged", True, "stands"),
    ]
    assert answers[1]["reason"] == "the test asserts under 2 s, which meets 10 s too"
    assert answers[1]["anchor"] is None
    human = fc.render_human(result)
    assert (
        f"{SOURCE_DOC} names {TEST_FILE} through verified-by, and this change modifies its "
        f'threshold. Still accurate: "the test asserts under 2 s, which meets 10 s too"' in human
    )


def test_an_entry_kept_from_the_base_answers_nothing_new(repo: AdopterRepo) -> None:
    kept = [
        entry("unchanged", "an earlier reason"),
        entry("unchanged", "an earlier reason", DECISION),
    ]
    _start(repo, {SOURCE_DOC: requirement(revisited=kept)})
    repo.commit("relax the threshold", {SOURCE_DOC: requirement(threshold="10 s", revisited=kept)})
    result = _run(repo)
    assert {kind for kind, _target, _answer in _revisits(result)} == {"unrevisited"}
    assert _revisit_answers(result) == []


def test_an_outcome_switched_alone_answers_nothing(repo: AdopterRepo) -> None:
    _start(repo, {SOURCE_DOC: requirement(revisited=[entry("deferred", "one reason")])})
    repo.commit(
        "relax the threshold; flip the outcome only",
        {SOURCE_DOC: requirement(threshold="10 s", revisited=[entry("unchanged", "one reason")])},
    )
    result = _run(repo)
    assert ("unrevisited", f"path:{TEST_FILE}", None) in _revisits(result)
    (answer,) = _revisit_answers(result)
    assert (answer["status"], answer["asked"]) == ("edited", False)
    assert "outcome changed without a new reason, which answers nothing" in fc.render_human(result)


def test_an_entry_written_with_nothing_triggered_is_not_asked_for(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit(
        "say why the test stands, though nothing changed",
        {SOURCE_DOC: requirement(revisited=[entry("unchanged", "unasked")])},
    )
    result = _run(repo)
    assert _revisits(result) == []
    (answer,) = _revisit_answers(result)
    assert (answer["asked"], answer["fields"], answer["links"]) == (False, [], ["verified-by"])
    assert "(not asked for by this change)" in fc.render_human(result)


def test_a_change_to_another_field_triggers_nothing(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit(
        "reword the rationale",
        {SOURCE_DOC: requirement(rationale="Users wait.", body="Why it matters, reworded.")},
    )
    assert _revisits(_run(repo)) == []


def test_a_field_added_or_removed_triggers(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit("drop the threshold", {SOURCE_DOC: requirement(threshold=None)})
    assert _revisits(_run(repo)) == [
        ("unrevisited", f"path:{TEST_FILE}", None),
        ("unrevisited", f"path:{DECISION}", None),
    ]


def test_a_reformatted_trigger_field_is_no_change(repo: AdopterRepo) -> None:
    _start(repo)
    text = requirement().replace('"threshold": "2 s"', '"threshold":    "2 s"')
    assert text != requirement()
    repo.commit("reformat", {SOURCE_DOC: text})
    assert _revisits(_run(repo)) == []


def test_a_source_new_in_the_change_triggers_nothing(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit(
        "a second requirement",
        {"reqs/second.md": requirement(threshold="5 s").replace("REQ-1", "REQ-2")},
    )
    assert _revisits(_run(repo)) == []


def test_a_target_added_to_the_link_in_the_change_owes_nothing(repo: AdopterRepo) -> None:
    _start(repo, {SOURCE_DOC: requirement(verified_by=(TEST_FILE,))})
    repo.commit(
        "relax the threshold, and link the decision",
        {SOURCE_DOC: requirement(threshold="10 s")},
    )
    assert _revisits(_run(repo)) == [("unrevisited", f"path:{TEST_FILE}", None)]


def test_an_anchor_the_link_does_not_list_owes_nothing(repo: AdopterRepo) -> None:
    _start(repo, {SOURCE_DOC: requirement(verified_by=(DECISION,))})
    repo.commit(
        "relax the threshold", {SOURCE_DOC: requirement(threshold="10 s", verified_by=(DECISION,))}
    )
    assert _revisits(_run(repo)) == [("unrevisited", f"path:{DECISION}", None)]


def test_a_source_in_no_linking_place_triggers_nothing(repo: AdopterRepo) -> None:
    # The same document in the project's place alone: never on by default.
    elsewhere = "docs/latency.md"
    _start(repo, {elsewhere: requirement().replace("REQ-1", "REQ-9")})
    repo.commit(
        "relax its threshold",
        {elsewhere: requirement(threshold="10 s").replace("REQ-1", "REQ-9")},
    )
    assert _revisits(_run(repo)) == []


def test_a_source_under_an_excluded_path_triggers_nothing(repo: AdopterRepo) -> None:
    config = friction_config(places=("docs",), exclude=["reqs/**"])
    _start(repo, config=config)
    repo.commit("relax the threshold", {SOURCE_DOC: requirement(threshold="10 s")})
    assert _revisits(_run(repo)) == []


def test_an_entry_beside_a_target_that_changed_is_asked_for(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit(
        "relax the threshold, change the test, and say so on the source too",
        {
            SOURCE_DOC: requirement(
                threshold="10 s", revisited=[entry("unchanged", "the new bound is asserted")]
            ),
            TEST_FILE: "def test_latency():\n    assert answer_time() < 10\n",
        },
    )
    result = _run(repo)
    assert ("revisited", f"path:{TEST_FILE}", "updated") in _revisits(result)
    test_answers = [a for a in _revisit_answers(result) if a["target"]["value"] == TEST_FILE]
    assert [(a["outcome"], a["asked"], a["status"]) for a in test_answers] == [
        ("updated", True, "stands"),
        ("unchanged", True, "stands"),
    ]


def test_a_target_two_links_list_is_asked_once(repo: AdopterRepo) -> None:
    declare_linker(
        repo.root,
        f"    - path: reqs\n{LINK}        - targets: answered-by\n          when: [threshold]\n",
    )
    linked: dict[str, Any] = {"answered-by": [DECISION]}
    _start(repo, {SOURCE_DOC: requirement(**linked)})
    repo.commit(
        "relax the threshold; one reason for the decision",
        {
            SOURCE_DOC: requirement(
                threshold="10 s",
                revisited=[entry("deferred", "the cache is revisited in #9999", DECISION)],
                **linked,
            )
        },
    )
    result = _run(repo)
    assert _revisits(result) == [
        ("unrevisited", f"path:{TEST_FILE}", None),
        ("revisited", f"path:{DECISION}", "deferred"),
    ]
    (decision,) = [f for f in result.findings if f.anchor == fd.Anchor("path", DECISION)]
    assert "`verified-by` and `answered-by` list this target" in decision.message
    (answer,) = _revisit_answers(result)
    assert (answer["links"], answer["fields"], answer["asked"]) == (
        ["verified-by", "answered-by"],
        ["threshold"],
        True,
    )


@pytest.mark.parametrize(("threshold", "asked"), [("2 s", False), ("10 s", True)])
def test_a_moved_source_triggers_only_by_its_fields(
    repo: AdopterRepo, threshold: str, asked: bool
) -> None:
    _start(repo)
    moved = "reqs/latency-moved.md"
    repo.rename(SOURCE_DOC, moved)
    repo.commit("edit it there", {moved: requirement(threshold=threshold, rationale="Moved.")})
    found = _revisits(_run(repo))
    assert found == (
        [("unrevisited", f"path:{TEST_FILE}", None), ("unrevisited", f"path:{DECISION}", None)]
        if asked
        else []
    )


def collection(**entries: dict[str, Any]) -> str:
    """A collection file under `reqs`: each entry its own fields and friction block, and
    a section headed by its id."""
    sections = "".join(f"## {entry_id}\n\nWhy it matters.\n\n" for entry_id in entries)
    return f"---\n{json.dumps(entries, indent=2)}\n---\n\n{sections}"


def collection_entry(
    threshold: str, revisited: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    block: dict[str, Any] = {"anchors": {"path": [TEST_FILE]}}
    if revisited:
        block["revisited"] = revisited
    return {"threshold": threshold, "verified-by": [TEST_FILE], "pkit": {"friction": block}}


def test_a_collection_entry_is_a_source_of_its_own(repo: AdopterRepo) -> None:
    coll = "reqs/coll.md"
    _start(
        repo,
        {coll: collection(**{"RS-1": collection_entry("2 s"), "RS-2": collection_entry("5 s")})},
    )
    repo.commit(
        "relax RS-1 only",
        {coll: collection(**{"RS-1": collection_entry("10 s"), "RS-2": collection_entry("5 s")})},
    )
    result = _run(repo)
    unrevisited = [f.location for f in result.findings if f.kind is fc.FindingKind.UNREVISITED]
    assert unrevisited == [f"{coll}#RS-1"]
    fw.write(
        fw.plan_revisit(
            repo.root, f"{coll}#RS-1", target=TEST_FILE, outcome="unchanged", reason="still holds"
        )
    )
    (source,) = [
        a for a in fd.discover_artefacts(repo.root).artefacts if a.location == f"{coll}#RS-1"
    ]
    assert source.friction["revisited"] == [entry("unchanged", "still holds")]
    assert fv.validate_friction(repo.root).errors == ()
    assert [kind for kind, _target, _answer in _revisits(_run(repo))] == ["revisited"]


def test_only_a_revisit_carries_the_new_keys(repo: AdopterRepo) -> None:
    _start(repo, {"docs/guide.md": document("guide", anchors={"path": ["src/cli/**"]})})
    repo.commit(
        "revalidate the guide",
        {
            "docs/guide.md": document(
                "guide", anchors={"path": ["src/cli/**"]}, at=T2, outcome="unchanged", because="x"
            )
        },
    )
    (answer,) = json.loads(fc.render_json(_run(repo)))["answers"]
    assert answer["answer"] == "unchanged"
    assert not {"outcome", "target", "links", "fields"} & answer.keys()


# --- validation ----------------------------------------------------------------------


def _link_findings(repo: AdopterRepo) -> list[tuple[str, str, str]]:
    kinds = {
        fv.FrictionFindingKind.DANGLING_REVISIT,
        fv.FrictionFindingKind.DUPLICATE_REVISIT,
        fv.FrictionFindingKind.ORPHANED_REVISIT,
        fv.FrictionFindingKind.MALFORMED_LINK_FIELD,
        fv.FrictionFindingKind.UNANCHORED_TARGET,
    }
    return [
        (f.kind.value, f.severity.value, f.pointer)
        for f in fv.validate_friction(repo.root).findings
        if f.kind in kinds
    ]


def test_validation_fails_a_dangling_and_a_repeated_revisit(repo: AdopterRepo) -> None:
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "x\n",
            DECISION: "y\n",
            SOURCE_DOC: requirement(
                verified_by=(TEST_FILE,),
                revisited=[
                    entry("unchanged", "listed"),
                    entry("unchanged", "again"),
                    entry("unchanged", "not listed", DECISION),
                ],
            ),
        }
    )
    assert _link_findings(repo) == [
        ("duplicate-revisit", "error", "/pkit/friction/revisited/1/anchor"),
        ("dangling-revisit", "error", "/pkit/friction/revisited/2/anchor"),
    ]


def test_validation_fails_a_link_field_that_names_no_anchor(repo: AdopterRepo) -> None:
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "x\n",
            DECISION: "y\n",
            SOURCE_DOC: requirement(verified_by=(TEST_FILE, "tests/missing.py")),
            "reqs/other.md": requirement(verified_by=TEST_FILE).replace("REQ-1", "REQ-2"),
        }
    )
    assert _link_findings(repo) == [
        ("unanchored-target", "error", "/verified-by"),
        ("malformed-link-field", "error", "/verified-by"),
    ]


def test_an_absent_link_field_lists_nothing(repo: AdopterRepo) -> None:
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "x\n",
            DECISION: "y\n",
            SOURCE_DOC: requirement(verified_by=None),
        }
    )
    assert _link_findings(repo) == []


def test_entries_where_no_place_declares_a_link_are_reported_only(repo: AdopterRepo) -> None:
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "x\n",
            DECISION: "y\n",
            "docs/latency.md": requirement(
                revisited=[entry("unchanged", "one"), entry("unchanged", "two")]
            ),
        }
    )
    assert _link_findings(repo) == [("orphaned-revisit", "report", "/pkit/friction/revisited")]


def test_the_container_schema_refuses_a_malformed_entry(repo: AdopterRepo) -> None:
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "x\n",
            DECISION: "y\n",
            SOURCE_DOC: requirement(
                revisited=[{"anchor": {"kind": "path", "value": TEST_FILE}, "outcome": "updated"}]
            ),
        }
    )
    malformed = [
        f.pointer
        for f in fv.validate_friction(repo.root).errors
        if f.kind is fv.FrictionFindingKind.MALFORMED_BLOCK
    ]
    assert malformed and all(p.startswith("/pkit/friction/revisited/0") for p in malformed)


# --- the writer ------------------------------------------------------------------------


@pytest.fixture
def written(repo: AdopterRepo) -> AdopterRepo:
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "x\n",
            DECISION: "y\n",
            SOURCE_DOC: requirement(),
        }
    )
    return repo


def _block(repo: AdopterRepo) -> Any:
    (source,) = [a for a in fd.discover_artefacts(repo.root).artefacts if a.path == SOURCE_DOC]
    return source.friction


def test_revisit_writes_one_entry_sorted_and_leaves_at(written: AdopterRepo) -> None:
    fw.write(
        fw.plan_revisit(
            written.root, "REQ-1", target=TEST_FILE, outcome="unchanged", reason="still under 2 s"
        )
    )
    fw.write(
        fw.plan_revisit(
            written.root,
            "REQ-1",
            target=f"path:{DECISION}",
            outcome="deferred",
            reason="revisited in #9999",
        )
    )
    block = _block(written)
    assert block["revisited"] == [
        entry("deferred", "revisited in #9999", DECISION),
        entry("unchanged", "still under 2 s"),
    ]
    assert block["revalidated"]["at"] == T1
    assert fv.validate_friction(written.root).errors == ()


def test_revisit_rewrites_the_entry_already_there(written: AdopterRepo) -> None:
    for reason in ("first", "second"):
        fw.write(
            fw.plan_revisit(
                written.root, "REQ-1", target=TEST_FILE, outcome="unchanged", reason=reason
            )
        )
    assert _block(written)["revisited"] == [entry("unchanged", "second")]
    again = fw.plan_revisit(
        written.root, "REQ-1", target=TEST_FILE, outcome="unchanged", reason=" second "
    )
    assert not again.changes
    assert "a later change needs new words" in (again.unchanged or "")


@pytest.mark.parametrize(
    ("target", "outcome", "reason", "refusal"),
    [
        (TEST_FILE, "updated", "x", "not 'updated'"),
        ("src/cli/main.py", "unchanged", "x", "has no target 'src/cli/main.py'"),
        (TEST_FILE, "unchanged", "<why it still stands>", "still holds the placeholder"),
        ("", "unchanged", "x", "give `--target`"),
        (TEST_FILE, "unchanged", " ", "give `--reason`"),
    ],
)
def test_revisit_refuses(
    written: AdopterRepo, target: str, outcome: str, reason: str, refusal: str
) -> None:
    with pytest.raises(fw.FrictionWriteError, match=None) as raised:
        fw.plan_revisit(written.root, "REQ-1", target=target, outcome=outcome, reason=reason)
    assert refusal in str(raised.value)


def test_revisit_refuses_an_artefact_no_place_links(written: AdopterRepo) -> None:
    written.write({"docs/plain.md": requirement().replace("REQ-1", "REQ-3")})
    with pytest.raises(fw.FrictionWriteError) as raised:
        fw.plan_revisit(written.root, "REQ-3", target=TEST_FILE, outcome="unchanged", reason="x")
    assert "declares a link that revisits its targets" in str(raised.value)


def test_the_revisit_command_writes_with_consent(written: AdopterRepo) -> None:
    args = ["friction", "revisit", SOURCE_DOC, "--target", TEST_FILE, "--outcome", "unchanged"]
    refused = CliRunner().invoke(main, [*args, "--reason", "still under 2 s"])
    assert refused.exit_code != 0
    assert "`--yes` writes without asking" in refused.output
    done = CliRunner().invoke(main, [*args, "--reason", "still under 2 s", "--yes"])
    assert done.exit_code == 0, done.output
    assert "Wrote pkit.friction.revisited" in done.output
    assert _block(written)["revisited"] == [entry("unchanged", "still under 2 s")]


# --- a link whose fields list what stays out ---------------------------------------------

#: A second place of the fixture capability, `obls`, whose link takes every anchor but
#: those its sources' `actors` and `refines` list, and asks after them when `statement`
#: changes (COR-050 point 16, the second way).
OBLIGATION = "obls/latency.md"
ACTOR_DOC = "docs/act.md"
ALL_BUT_PLACES = (
    f"    - path: reqs\n{LINK}"
    "    - path: obls\n"
    "      revisits:\n"
    "        - all-but: [actors, refines]\n"
    "          when: [statement]\n"
    "          description: A changed statement asks after every anchor but its actors.\n"
)


def obligation(
    *,
    statement: str = "Status answers in 2 seconds.",
    actors: Any = ("ACT-1",),
    revisited: list[dict[str, Any]] | None = None,
) -> str:
    """`OBL-1`, a source of the all-but link: anchored to the test file, the decision and
    the actor its `actors` lists, revalidated at T1. An `actors` of `None` leaves the
    field out."""
    fields: dict[str, Any] = {"statement": statement}
    if actors is not None:
        fields["actors"] = list(actors) if isinstance(actors, tuple) else actors
    text = document(
        "OBL-1",
        anchors={"path": [TEST_FILE, DECISION], "artefact": ["ACT-1"]},
        at=T1,
        outcome="unchanged",
        because="the test and the decision say what the obligation says",
        body="Why it matters.",
        **fields,
    )
    if revisited is None:
        return text
    front, body = text.split("\n---\n", 1)
    data = json.loads(front.removeprefix("---\n"))
    data["pkit"]["friction"]["revisited"] = revisited
    return f"---\n{json.dumps(data, indent=2)}\n---\n{body}"


@pytest.fixture
def obligations(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    adopter = make_adopter_repo()
    declare_linker(adopter.root, ALL_BUT_PLACES)
    return adopter


def _obligation_files(**overrides: str) -> dict[str, str]:
    """The files every all-but test starts from: the sources, the targets, the actor
    and `OBL-1`, each replaceable by keyword (`obligation_doc`, `config`)."""
    return {
        CONFIG: overrides.get("config", friction_config(places=("docs",))),
        **SOURCE,
        TEST_FILE: "def test_latency():\n    assert answer_time() < 2\n",
        DECISION: "Cache the status.\n",
        ACTOR_DOC: document("ACT-1", unanchored_because="A person.", body="An actor."),
        OBLIGATION: overrides.get("obligation_doc", obligation()),
    }


def _obligation_base(adopter: AdopterRepo, config: str | None = None) -> None:
    """Commit the all-but base state on `main` and branch `feature` off it."""
    adopter.write(_obligation_files(config=config or friction_config(places=("docs",))))
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


def _source(adopter: AdopterRepo) -> tuple[fd.Discovery, fd.Artefact]:
    discovery = fd.discover_artefacts(adopter.root)
    (source,) = [a for a in discovery.artefacts if a.path == OBLIGATION]
    return discovery, source


def test_a_link_takes_every_anchor_its_fields_do_not_list(obligations: AdopterRepo) -> None:
    obligations.write(_obligation_files())
    discovery, source = _source(obligations)
    (link,) = discovery.links(source)
    assert (link.targets, link.all_but, link.when) == (None, ("actors", "refines"), ("statement",))
    assert link.fields == ("actors", "refines")
    assert fd.link_targets(source, link) == (
        fd.Anchor("path", TEST_FILE),
        fd.Anchor("path", DECISION),
    )
    assert fd.links_said([link]) == "every anchor `actors` and `refines` do not list"


def test_a_malformed_field_listing_what_stays_out_keeps_nothing_out(
    obligations: AdopterRepo,
) -> None:
    obligations.write(_obligation_files(obligation_doc=obligation(actors="ACT-1")))
    discovery, source = _source(obligations)
    (link,) = discovery.links(source)
    assert fd.Anchor("artefact", "ACT-1") in fd.link_targets(source, link)


def test_the_package_schema_takes_one_way_of_choosing_targets(repo: AdopterRepo) -> None:
    declare_linker(
        repo.root,
        "    - path: reqs\n"
        "      revisits:\n"
        "        - {targets: verified-by, all-but: [actors], when: [statement]}\n"
        "        - {when: [statement]}\n"
        "        - {all-but: [], when: [statement]}\n"
        "        - {all-but: [actors, actors], when: [statement]}\n"
        "        - {all-but: [pkit], when: [statement]}\n"
        "        - {all-but: [actors, refines], when: [statement]}\n",
    )
    repo.write({CONFIG: friction_config(places=("docs",))})
    refused = {
        finding.path.split("/")[5]
        for report in pv.validate_installed_packages(repo.root).reports
        if report.file == repo.root / ".pkit/capabilities/linker/package.yaml"
        for finding in report.findings
        if finding.severity is pv.Severity.ERROR and finding.path.count("/") >= 5
    }
    assert refused == {"0", "1", "2", "3", "4"}
    # Read forgivingly: a link the schema refuses declares nothing, and a field it
    # repeats is read once.
    (place,) = [p for p in fd.read_friction_settings(repo.root).places if p.is_capability]
    assert [(link.targets, link.all_but) for link in place.revisits] == [
        (None, ("actors",)),
        (None, ("actors", "refines")),
    ]


def test_a_changed_obligation_asks_after_every_anchor_but_its_actors(
    obligations: AdopterRepo,
) -> None:
    _obligation_base(obligations, friction_config(mode="enforcing", places=("docs",)))
    obligations.commit("tighten", {OBLIGATION: obligation(statement="Status answers in 1 s.")})
    result = _run(obligations)
    assert _revisits(result) == [
        ("unrevisited", f"path:{TEST_FILE}", None),
        ("unrevisited", f"path:{DECISION}", None),
    ]
    message = next(f.message for f in result.findings if f.kind is fc.FindingKind.UNREVISITED)
    assert (
        "its `statement` changed in this diff, and the link takes every anchor `actors` and "
        "`refines` do not list, this target among them" in message
    )
    assert result.failed


def test_a_target_of_a_link_by_what_stays_out_is_answered_and_listed(
    obligations: AdopterRepo,
) -> None:
    # The changed test is also friction of `OBL-1` itself, its anchor, which this test
    # leaves unanswered: only the revisits are judged here.
    _obligation_base(obligations)
    obligations.commit(
        "tighten, and the test with it; the decision still stands",
        {
            OBLIGATION: obligation(
                statement="Status answers in 1 s.",
                revisited=[entry("unchanged", "caching still meets one second", DECISION)],
            ),
            TEST_FILE: "def test_latency():\n    assert answer_time() < 1\n",
        },
    )
    result = _run(obligations)
    assert _revisits(result) == [
        ("revisited", f"path:{TEST_FILE}", "updated"),
        ("revisited", f"path:{DECISION}", "unchanged"),
    ]
    answers = _revisit_answers(result)
    assert [(a["target"]["value"], a["links"], a["fields"]) for a in answers] == [
        (DECISION, [], ["statement"]),
        (TEST_FILE, [], ["statement"]),
    ]
    human = fc.render_human(result)
    assert (
        f"{OBLIGATION} names {TEST_FILE}, and this change modifies its statement. "
        f"Updated in this change" in human
    )


def test_a_change_to_a_field_listing_what_stays_out_alone_triggers_nothing(
    obligations: AdopterRepo,
) -> None:
    _obligation_base(obligations)
    obligations.commit("drop the actor", {OBLIGATION: obligation(actors=())})
    assert _revisits(_run(obligations)) == []


def test_validation_of_a_link_by_what_stays_out(obligations: AdopterRepo) -> None:
    # A value no anchor has keeps nothing out, so it is not failed. An entry on the
    # anchor the field keeps out names no target. A field in the wrong shape is failed.
    obligations.write(
        {
            **_obligation_files(
                obligation_doc=obligation(
                    actors=("ACT-1", "ACT-9"),
                    revisited=[entry("unchanged", "an actor", "ACT-1", kind="artefact")],
                )
            ),
            "obls/other.md": obligation(actors="ACT-1").replace("OBL-1", "OBL-2"),
        }
    )
    assert _link_findings(obligations) == [
        ("dangling-revisit", "error", "/pkit/friction/revisited/0/anchor"),
        ("malformed-link-field", "error", "/actors"),
    ]
    message = next(
        f.message
        for f in fv.validate_friction(obligations.root).findings
        if f.kind is fv.FrictionFindingKind.DANGLING_REVISIT
    )
    assert "links take every anchor `actors` and `refines` do not list" in message


def test_revisit_refuses_an_anchor_a_field_keeps_out(obligations: AdopterRepo) -> None:
    obligations.write(_obligation_files())
    with pytest.raises(fw.FrictionWriteError) as raised:
        fw.plan_revisit(
            obligations.root, "OBL-1", target="artefact:ACT-1", outcome="unchanged", reason="x"
        )
    assert "its links take every anchor `actors` and `refines` do not list" in str(raised.value)
    fw.write(
        fw.plan_revisit(
            obligations.root, "OBL-1", target=TEST_FILE, outcome="unchanged", reason="still"
        )
    )
    _discovery, source = _source(obligations)
    assert source.friction["revisited"] == [entry("unchanged", "still")]
