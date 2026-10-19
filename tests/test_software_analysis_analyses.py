"""software-analysis: one analysis per component (#1815).

Held to software-analysis DEC-001 points 2, 3, 4 and 8, and DEC-003 point 6:

- **one analysis, as today**, needs no list and no change: it lies at the top of
  the analysis location, and the stamp, the check and the diagrams read it there;
- **several**, listed in the capability's settings file with their components,
  folders and what each builds on, each lie in a folder named after their
  component: the same places one folder down hold them, the stamp writes in the
  one `--analysis` names, and the check refuses an artefact no listed analysis
  holds;
- **ids** stay unique across a repository's analyses: one numbering of each
  numbered kind, its history included, and no named id two analyses share;
- **between analyses:** a field names its own analysis's artefacts, but for an
  actor of an analysis it builds on, named with it, which its glossary's head lists;
  the head's data is checked against its shape and the configuration, and its text
  against its data where the format rule binds; the configuration's list is held to
  what a component's package metadata declares, and a head's links to its floor;
- **what reads them all:** the readers point gives each actor the needs every
  analysis states for it, a diagram draws one analysis, and the core's friction
  reading gives each nested artefact its place's type.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    GLOSSARY,
    MAIN,
    SA,
    VALIDATE,
    accepting_san,
    fill,
    front,
    installed,
    load_lib,
    new,
    prepare_seeded,
    run_script,
    stamped,
)

#: The capability's settings file, where the analyses are listed (DEC-001 point 2).
SETTINGS = f"{SA.as_posix()}/project/config.yaml"
FILL_READERS = SA / "scripts" / "fill-readers.py"
DIAGRAM = SA / "scripts" / "diagram.py"


def listing(*entries: str) -> str:
    """The settings file listing `entries`, each an item of `analyses`."""
    return "pkit_schema: software-analysis:config\nschema_version: 1\nanalyses:\n" + "".join(
        entries
    )


CORE = "  - {component: core, folder: core}\n"
BILLING = "  - component: billing\n    folder: billing\n    builds-on:\n      - {analysis: core}\n"


def place(folder: str, rel: str) -> str:
    """A path of the analysis kept in `folder` of the location."""
    return f"{ANALYSIS}/{folder}/{rel}"


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


@pytest.fixture
def seeded(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=prepare_seeded)


@pytest.fixture
def two(project: AdopterRepo) -> AdopterRepo:
    """Two analyses, the core's and billing's, which builds on it, each with an actor
    and a use case stamped and filled."""
    project.write({SETTINGS: listing(CORE, BILLING)})
    stamped(project, "actor", "tester", "--analysis", "core", "--path", "src/**")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--analysis", "core")
    stamped(project, "actor", "clerk", "--analysis", "billing", "--path", "src/**")
    stamped(project, "use-case", "invoice", "--actor", "ACT-clerk", "--analysis", "billing")
    fill(project)
    return project


def check(repo: AdopterRepo, *args: str) -> dict[str, Any]:
    completed = run_script(repo, VALIDATE, "--json", *args)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def findings(document: Mapping[str, Any], severity: str = "error") -> list[tuple[str, str]]:
    """The findings of `severity`, but the report that no rule of `SAN` binds, said of
    every analysis no set of the project's own makes it bind on (DEC-001 point 1)."""
    return [
        (f["location"], f["message"])
        for f in document["findings"]
        if f["severity"] == severity and not f["message"].startswith("no rule of ")
    ]


def refused(completed: Any) -> str:
    assert completed.returncode == 1, completed.stdout
    return str(completed.stderr)


# --- the places and references, read alone -----------------------------------------------------


def test_a_path_is_placed_at_the_top_or_one_folder_down() -> None:
    """A place at the top holds what lies beneath it, and one folder down, a `*` segment
    stands for one folder of any name; a reference names another analysis by its
    component before a colon (DEC-001 point 2)."""
    (model,) = load_lib("model")
    under: Any = model.under_place
    assert under("a/use-case-model/use-cases/x/UC-001-x.md", "a/use-case-model/use-cases")
    assert under("a/core/use-case-model/actors/ACT-x.md", "a/*/use-case-model/actors/**")
    assert under("a/core/glossary.md", "a/*/glossary.md")
    assert not under("a/glossary.md", "a/*/glossary.md")
    assert not under("a/core/x/use-case-model/actors/ACT-x.md", "a/*/use-case-model/actors/**")
    assert model.qualified("core:ACT-developer") == ("core", "ACT-developer")
    assert model.qualified("ACT-developer") == (None, "ACT-developer")
    (backbone,) = load_lib("backbone")
    assert backbone._pathspecs(["a/b", "a/*/c"]) == [":(literal)a", ":(literal)a/b"]


# --- one analysis, as today ------------------------------------------------------------------


def test_a_single_analysis_needs_no_list_and_no_change(seeded: AdopterRepo) -> None:
    """A project that lists nothing keeps its one analysis at the location's top, as
    every project did before several analyses could be kept: its artefacts pass, and the
    stamp writes there. Naming an analysis then is refused."""
    assert not (seeded.root / SETTINGS).exists()
    document = check(seeded)
    assert findings(document) == []
    assert not any("listed" in line for line in document["summary"])
    completed = new(seeded, "use-case", "export", "--actor", "ACT-tester")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines()[-1] == (
        f"stamped UC-003 at {ANALYSIS}/use-case-model/use-cases/UC-003-export.md"
    )
    said = refused(new(seeded, "actor", "clerk", "--analysis", "core"))
    assert "the project lists no analyses" in said


def test_an_artefact_one_folder_down_lies_in_no_analysis_while_none_is_listed(
    seeded: AdopterRepo,
) -> None:
    """With nothing listed, the one analysis lies at the top, so a file the nested places
    hold lies in no analysis (DEC-001 point 2)."""
    stray = place("billing", "use-case-model/actors/ACT-clerk.md")
    seeded.write(
        {
            stray: (seeded.root / f"{ANALYSIS}/use-case-model/actors/ACT-tester.md")
            .read_text(encoding="utf-8")
            .replace("ACT-tester", "ACT-clerk")
        }
    )
    (message,) = [m for where, m in findings(check(seeded)) if where == stray]
    assert "the project lists no analyses" in message and "(DEC-001 point 2)" in message


# --- several, each in its folder ----------------------------------------------------------


def test_several_analyses_are_stamped_each_in_its_folder_and_checked(two: AdopterRepo) -> None:
    """Each listed analysis takes the artefacts stamped in it, in its component's folder,
    with the same layout; one numbering of use cases runs across them (DEC-001 points 2
    and 3); and the check passes them."""
    assert front(two, place("core", "use-case-model/actors/ACT-tester.md"))["id"] == "ACT-tester"
    assert (
        front(two, place("core", "use-case-model/use-cases/UC-001-run-suite.md"))["actor"]
        == "ACT-tester"
    )
    assert (
        front(two, place("billing", "use-case-model/use-cases/UC-002-invoice.md"))["actor"]
        == "ACT-clerk"
    )
    assert stamped(two, "term", "bill", "--analysis", "billing", "--path", "src/**") == (
        "TERM-bill"
    )
    assert (
        stamped(
            two, "quality-requirement", "quick", "--analysis", "billing", "--actor", "ACT-clerk"
        )
        == "REQ-001"
    )
    fill(two)
    assert (two.root / place("billing", "glossary.md")).is_file()
    assert (two.root / place("billing", "requirements/quality/REQ-001-quick.md")).is_file()
    document = check(two)
    assert findings(document) == []
    assert "2 analysis(es) listed: core in core/, billing in billing/" in " ".join(
        document["summary"]
    )


def test_the_stamp_names_the_analysis_it_writes_in(two: AdopterRepo) -> None:
    """Where several are listed, `--analysis` names one of them; where one is, it may be
    left out (DEC-001 point 2)."""
    assert "name the one to write in, --analysis <component>" in refused(
        new(two, "actor", "auditor")
    )
    assert "--analysis shipping is no analysis the project lists" in refused(
        new(two, "actor", "auditor", "--analysis", "shipping")
    )
    two.write({SETTINGS: listing(CORE)})
    assert stamped(two, "actor", "auditor") == "ACT-auditor"
    assert (two.root / place("core", "use-case-model/actors/ACT-auditor.md")).is_file()


def test_an_artefact_no_listed_analysis_holds_is_refused(two: AdopterRepo) -> None:
    """Listed, each analysis lies in its folder: a file at the location's top, or in a
    folder no entry lists, lies in no analysis (DEC-001 point 2)."""
    text = (two.root / place("core", "use-case-model/actors/ACT-tester.md")).read_text(
        encoding="utf-8"
    )
    top = f"{ANALYSIS}/use-case-model/actors/ACT-auditor.md"
    unlisted = place("shipping", "use-case-model/actors/ACT-packer.md")
    two.write(
        {
            top: text.replace("ACT-tester", "ACT-auditor"),
            unlisted: text.replace("ACT-tester", "ACT-packer"),
        }
    )
    found = dict(findings(check(two)))
    assert "lies at the top of the analysis location" in found[top]
    assert "which no analysis" in found[unlisted] and "lists takes" in found[unlisted]


def test_a_component_or_a_folder_listed_twice_is_refused(project: AdopterRepo) -> None:
    project.write(
        {
            SETTINGS: listing(
                CORE,
                "  - {component: core, folder: other}\n",
                "  - {component: billing, folder: core}\n",
                "  - component: shipping\n    folder: shipping\n    builds-on:\n"
                "      - {analysis: shipping}\n",
            )
        }
    )
    messages = [message for _where, message in findings(check(project))]
    assert any(m.startswith("core is listed twice") for m in messages)
    assert any(m.startswith("the folder core is listed twice") for m in messages)
    assert any("the analysis of shipping builds on itself" in m for m in messages)


# --- ids across the analyses -----------------------------------------------------------------


def test_no_two_analyses_share_an_id(two: AdopterRepo) -> None:
    """An actor's or a term's id is unique across the repository: the stamp refuses one
    another analysis holds, and the check one written by hand (DEC-001 point 3)."""
    assert "ACT-tester is held already" in refused(
        new(two, "actor", "tester", "--analysis", "billing")
    )
    copied = place("billing", "use-case-model/actors/ACT-tester.md")
    two.write(
        {
            copied: (two.root / place("core", "use-case-model/actors/ACT-tester.md")).read_text(
                encoding="utf-8"
            )
        }
    )
    original = place("core", "use-case-model/actors/ACT-tester.md")
    (found,) = [(w, m) for w, m in findings(check(two)) if m.startswith("the id ACT-tester")]
    # The finding lands on one of the two, and names the other.
    holder = copied if found[0] == original else original
    assert found[0] in (copied, original)
    assert found[1] == (
        f"the id ACT-tester is also held by {holder}: no two artefacts of a repository's "
        "analyses share an id, of any kind, so an id read anywhere in the repository names one "
        "artefact, and an id is never used again (DEC-001 point 3)"
    )


def test_one_numbering_runs_across_the_analyses_and_their_history(two: AdopterRepo) -> None:
    """A use case's number is past every number any analysis holds or its history gave,
    one deleted from the default branch included (DEC-001 point 3)."""
    two.commit("two analyses")
    gone = place("core", "use-case-model/use-cases/UC-003-retired.md")
    two.commit(
        "a use case",
        {
            gone: (two.root / place("core", "use-case-model/use-cases/UC-001-run-suite.md"))
            .read_text(encoding="utf-8")
            .replace("UC-001", "UC-003")
        },
    )
    two.commit("drop it", {gone: None})
    assert two.current_branch() == MAIN
    assert stamped(two, "use-case", "refund", "--actor", "ACT-clerk", "--analysis", "billing") == (
        "UC-004"
    )


def test_a_number_another_analysis_took_on_the_default_branch_collides(two: AdopterRepo) -> None:
    """Two lines of work numbering a use case each, in two analyses, take one number: the
    number comparison reports it, as it does within one (DEC-001 point 3)."""
    two.commit("two analyses")
    two.checkout("topic", create=True)
    two.checkout(MAIN)
    stamped(two, "use-case", "audit", "--actor", "ACT-tester", "--analysis", "core")
    two.commit("UC-003 in core, on main")
    two.checkout("topic")
    ours = place("billing", "use-case-model/use-cases/UC-003-refund.md")
    two.write(
        {
            ours: (two.root / place("billing", "use-case-model/use-cases/UC-002-invoice.md"))
            .read_text(encoding="utf-8")
            .replace("UC-002", "UC-003")
        }
    )
    completed = run_script(two, SA / "scripts" / "check-numbers.py", "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stderr
    (collision,) = [f for f in json.loads(completed.stdout)["findings"] if f["severity"] == "error"]
    assert collision["location"] == ours
    assert collision["message"].startswith(
        f"UC-003 is numbered on main too, for {place('core', 'use-case-model/use-cases/')}"
    )


# --- between analyses ------------------------------------------------------------------------


def _head(
    analysis: str = "core", version: str = "1.149.0", needs: str = "Never lose a bill."
) -> str:
    """A glossary's head data, `builds-on`, listing ACT-tester and TERM-suite of `analysis`."""
    return (
        "builds-on:\n"
        f"  - analysis: {analysis}\n"
        f"    version: {version}\n"
        "    terms:\n"
        "      - {id: TERM-suite, name: suite}\n"
        "    actors:\n"
        "      - id: ACT-tester\n"
        "        name: Tester\n"
        f"        needs: [{json.dumps(needs)}]\n"
    )


def _head_text(
    analysis: str = "core", version: str = "1.149.0", need: str = "Never lose a bill."
) -> str:
    """The head's list that shows `_head`'s data."""
    return (
        f"- **From {analysis} at {version}:** the area of running suites.\n"
        f"  - **Term:** [suite](https://example.org/{analysis}/glossary.md#term-suite)\n"
        f"  - **Actor:** [Tester](https://example.org/{analysis}/ACT-tester.md)\n"
        f"    - {need}\n"
    )


def _with_head(repo: AdopterRepo, data: str, text: str) -> str:
    """The billing glossary, stamped, with `data` in its front matter and `text` after its
    opening paragraph."""
    stamped(repo, "term", "bill", "--analysis", "billing", "--path", "src/**")
    fill(repo)
    rel = place("billing", "glossary.md")
    written = (repo.root / rel).read_text(encoding="utf-8")
    written = written.replace("---\n", f"---\n{data}", 1)
    written = re.sub(r"(The names it replaces are kept\.\n)", rf"\1\n{text}", written, count=1)
    repo.write({rel: written})
    return rel


def test_an_actor_of_an_analysis_it_builds_on_is_named_with_it(two: AdopterRepo) -> None:
    """A use case names another analysis's actor with that analysis, as the head of its
    glossary lists it, and anchors the records behind it, never the actor (DEC-001 points
    2 and 4). Named bare, the actor is another analysis's, which only an actor field may
    name, and only so."""
    assert "is no actor the head of the glossary of the analysis of billing lists" in refused(
        new(
            two,
            "use-case",
            "audit",
            "--actor",
            "core:ACT-tester",
            "--analysis",
            "billing",
            "--record",
            "COR-001",
        )
    )
    _with_head(two, _head(), _head_text())
    assert "name them with --record" in refused(
        new(two, "use-case", "audit", "--actor", "core:ACT-tester", "--analysis", "billing")
    )
    assert (
        stamped(
            two,
            "use-case",
            "audit",
            "--actor",
            "core:ACT-tester",
            "--analysis",
            "billing",
            "--record",
            "COR-001",
        )
        == "UC-003"
    )
    written = front(two, place("billing", "use-case-model/use-cases/UC-003-audit.md"))
    assert written["actor"] == "core:ACT-tester"
    assert written["pkit"]["friction"]["anchors"] == {"record": ["COR-001"]}
    fill(two)
    assert findings(check(two)) == []

    bare = place("billing", "use-case-model/use-cases/UC-002-invoice.md")
    text = (two.root / bare).read_text(encoding="utf-8")
    two.write({bare: text.replace("actor: ACT-clerk", "actor: ACT-tester")})
    found = dict(findings(check(two)))
    tester = place("core", "use-case-model/actors/ACT-tester.md")
    assert found[f"{bare}:/actor"].startswith(
        f"actor ACT-tester lies in another analysis ({tester}): an artefact names its own "
        "analysis's artefacts alone"
    )
    assert "lies in another analysis" in refused(
        new(two, "use-case", "audit", "--actor", "ACT-tester", "--analysis", "billing")
    )


def test_a_journey_s_steps_are_use_cases_of_its_own_analysis(two: AdopterRepo) -> None:
    assert "use case UC-001 lies in another analysis" in refused(
        new(
            two,
            "journey",
            "month-end",
            "--actor",
            "ACT-clerk",
            "--analysis",
            "billing",
            "--step",
            "UC-002",
            "--step",
            "UC-001",
        )
    )


def test_an_analysis_names_only_those_it_builds_on(two: AdopterRepo) -> None:
    """The head lists only analyses its entry builds on, and an actor named with an
    analysis it does not build on is refused (DEC-001 point 2; RS-SAN-010)."""
    rel = _with_head(two, _head("shipping"), _head_text("shipping"))
    found = dict(findings(check(two)))
    assert "which its entry in" in found[f"{rel}:/builds-on/0/analysis"]
    two.write({SETTINGS: listing(CORE, "  - {component: billing, folder: billing}\n")})
    uc = place("billing", "use-case-model/use-cases/UC-002-invoice.md")
    text = (two.root / uc).read_text(encoding="utf-8")
    two.write({uc: text.replace("other-actors: []", "other-actors: [core:ACT-tester]")})
    found = dict(findings(check(two)))
    assert "which the analysis of billing does not build on" in found[f"{uc}:/other-actors/0"]


def test_the_head_s_data_has_its_shape_and_its_text_shows_it(two: AdopterRepo) -> None:
    """The head's data is held to its shape always; its text to its data where the format
    rule binds (DEC-001 points 1 and 2)."""
    two.write(accepting_san(two))
    rel = _with_head(two, _head(), _head_text())
    assert [f for f in findings(check(two)) if f[0].startswith(rel)] == []

    two.write(
        {
            rel: (two.root / rel)
            .read_text(encoding="utf-8")
            .replace("    - Never lose a bill.\n", "    - Never lose an invoice.\n")
        }
    )
    (message,) = [m for where, m in findings(check(two)) if where == rel]
    assert "`builds-on-matches-front-matter`" in message
    assert "the needs under Tester" in message

    two.write(
        {
            rel: (two.root / rel)
            .read_text(encoding="utf-8")
            .replace("version: 1.149.0", "versions: 1.149.0")
        }
    )
    found = dict(findings(check(two)))
    assert any(w.startswith(f"{rel}:/builds-on") for w in found)


def test_a_term_never_takes_the_name_of_a_term_its_head_lists(two: AdopterRepo) -> None:
    rel = _with_head(two, _head(), _head_text())
    text = (two.root / rel).read_text(encoding="utf-8")
    two.write({rel: text.replace("  name: Bill\n", "  name: suite\n")})
    found = dict(findings(check(two)))
    assert "is the name of core:TERM-suite" in found[f"{rel}#TERM-bill:/name"]


def test_the_list_is_held_to_what_a_component_declares(project: AdopterRepo) -> None:
    """Where a component declares its dependencies, as a capability does in its package
    metadata, an analysis builds only on those, optional where they are; and a head
    whose links name another version than the declared floor is warned of. The analysis
    of `core` is the backbone's (DEC-001 point 2)."""
    package = (project.root / SA / "package.yaml").read_text(encoding="utf-8")
    floor = re.search(r'requires_backbone: ">=([0-9.]+),', package)
    assert floor is not None
    sa = (
        "  - component: software-analysis\n    folder: sa\n    builds-on:\n"
        "      - {analysis: core}\n"
        "      - {analysis: project-management}\n"
        "      - {analysis: living-docs}\n"
    )
    project.write({SETTINGS: listing(CORE, sa)})
    found = dict(findings(check(project)))
    assert "declares it optional" in found[f"{SETTINGS}:/analyses/1/builds-on/1"]
    assert (
        "declares no dependency of software-analysis on living-docs"
        in found[f"{SETTINGS}:/analyses/1/builds-on/2"]
    )
    project.write(
        {
            SETTINGS: listing(
                CORE,
                "  - component: software-analysis\n    folder: sa\n    builds-on:\n"
                "      - {analysis: core}\n",
            )
        }
    )
    stamped(project, "term", "verdict", "--analysis", "software-analysis", "--path", "src/**")
    fill(project)
    rel = place("sa", "glossary.md")
    text = (project.root / rel).read_text(encoding="utf-8")
    project.write({rel: text.replace("---\n", f"---\n{_head(version='1.0.0')}", 1)})
    (warning,) = [m for where, m in findings(check(project), "warning") if "version" in where]
    assert f"declares {floor[1]} as the lowest version of core software-analysis needs" in warning
    project.write({rel: text.replace("---\n", f"---\n{_head(version=floor[1])}", 1)})
    assert [m for where, m in findings(check(project), "warning") if "version" in where] == []


# --- what reads them all ---------------------------------------------------------------------


def test_the_readers_point_gives_each_actor_the_needs_every_analysis_states(
    two: AdopterRepo,
) -> None:
    """An actor's reader carries its own needs, then those each analysis that lists it
    states beside it (DEC-001 point 8)."""
    _with_head(two, _head(needs="Never lose a bill."), _head_text())
    completed = run_script(two, FILL_READERS, "--json")
    assert completed.returncode == 0, completed.stderr
    readers = {r["id"]: r["description"] for r in json.loads(completed.stdout)["value"]}
    assert readers["act-tester"].endswith("; Never lose a bill.")
    assert "act-clerk" in readers


def test_a_diagram_draws_one_analysis_and_another_s_actor_by_its_id(two: AdopterRepo) -> None:
    """Where several are listed, the query names the analysis it draws, and an actor of
    another analysis is drawn among the actors by that id alone (DEC-003 point 6)."""
    completed = run_script(two, DIAGRAM, "use-cases")
    assert completed.returncode == 1
    assert "name the one to draw" in completed.stderr
    _with_head(two, _head(), _head_text())
    uc = place("billing", "use-case-model/use-cases/UC-002-invoice.md")
    text = (two.root / uc).read_text(encoding="utf-8")
    two.write({uc: text.replace("other-actors: []", "other-actors: [core:ACT-tester]")})
    completed = run_script(two, DIAGRAM, "use-cases", "--analysis", "billing")
    assert completed.returncode == 0, completed.stderr
    assert 'core_ACT_tester["core:ACT-tester"]' in completed.stdout
    assert "UC_002" in completed.stdout and "UC_001" not in completed.stdout


def test_a_record_is_kept_in_its_analysis_s_folder(two: AdopterRepo) -> None:
    completed = run_script(
        two,
        SA / "scripts" / "new.py",
        "revalidation",
        "lost-invoice",
        "--analysis",
        "billing",
        "--change",
        "#45",
        "--trigger",
        "drift",
        "--outcome",
        "UC-002=gap-found",
        "--because",
        "UC-002=An invoice can be lost, and nothing describes it.",
        "--gap",
        "UC-002: Nothing describes a lost invoice => UC-002 updated",
        "--by",
        "Sam",
    )
    assert completed.returncode == 0, completed.stderr
    written = completed.stdout.splitlines()[-1].split(" at ", 1)[1]
    assert written.startswith(place("billing", "revalidations/"))
    document = check(two)
    assert "1 revalidation record(s)" in document["summary"][0]
    assert [f for f in findings(document) if f[0] == written] == []


def test_the_core_s_reading_gives_each_nested_artefact_its_place_s_type(two: AdopterRepo) -> None:
    """The places are the capability's whatever the number of analyses: the core's
    friction reading gives each analysis's artefacts their types (DEC-001 point 2)."""
    listing_ = CliRunner().invoke(main, ["friction", "artefacts", "--json"])
    assert listing_.exit_code == 0, listing_.output
    types = {a["id"]: a["type"] for a in json.loads(listing_.output)["artefacts"]}
    assert types["ACT-clerk"] == "software-analysis:actor"
    assert types["UC-002"] == "software-analysis:use-case"
    assert GLOSSARY not in {a["path"] for a in json.loads(listing_.output)["artefacts"]}
