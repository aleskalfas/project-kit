"""A page anchored to a captured source (#1265; living-docs DEC-001 point 4).

living-docs registers the `source` anchor kind. A source outside the repository
is captured as one file of the capability's project tier,
`.pkit/capabilities/living-docs/project/sources/<name>.yaml`, and the kind's
resolver, `resolve-source`, answers that file from the name alone. Any change
to the file is the source's change; a name no file captures is a dead anchor.

Every test stands up a real adopter repository with living-docs installed and
runs the real checks over it:

1. a new version recorded stales the page — the change check asks it, the
   whole-repository check and the documentation-check filler find it stale —
   and an answer clears it;
2. nothing but a change to the source's file stales it, and any change to
   that file does;
3. a captured source of the wrong shape fails `pkit validate` under `data`
   and still answers, so the page stays judged;
4. a name nothing captures is dead in both checks, and reported by the
   validator without failing;
5. the layout: only a regular file of the exact name, through real folders,
   answers, and the validator fails every other entry;
6. a sources folder that cannot be read is no answer: the page is not judged;
7. the resolver's own surface: its arguments, the grammar, its human view,
   and that it runs offline from an empty uv cache, apart from any project it
   is run in;
8. the registration, as the one registry reads it;
9. a rule's origin citing a captured source;
10. the validator's reports;
11. a misspelt kind, with the nearest kind named, leaves the documentation
    check answering.

The capability's scripts are pointed at this interpreter in the adopter copy
— but for the one test that runs the resolver through its own `uv` shebang —
and the `pkit` they read through is the real CLI under this interpreter
(`pkit_on_path`). The library is reached through a small driver run in a
subprocess, as the validator's own tests do: `_lib` is every capability's
library name, so it is never imported here.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_repository as fr
from project_kit import friction_validate as fv
from project_kit import rule_sets as rs
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import T1, document

LD = Path(".pkit") / "capabilities" / "living-docs"
SCRIPTS = LD / "scripts"
RESOLVER = SCRIPTS / "resolve-source.py"
CONFIG = ".pkit/project/config.yaml"
SOURCES = f"{LD.as_posix()}/project/sources"
KEEP = f"{SOURCES}/keep-a-changelog.yaml"
PAGE = "docs/changelog.md"

ANCHOR = fd.Anchor("source", "keep-a-changelog")
KEEP_A_CHANGELOG = (
    'title: Keep a Changelog\nurl: https://keepachangelog.com/en/1.1.0/\nversion: "1.1.0"\n'
)


def _page(anchors: dict[str, list[str]] | None = None, **overrides: Any) -> str:
    """The changelog page: a signpost for users, resting on the release code and on
    Keep a Changelog, revalidated at T1."""
    values: dict[str, Any] = {
        "anchors": anchors or {"path": ["src/release/**"], "source": ["keep-a-changelog"]},
        "at": T1,
        "outcome": "updated",
        "body": "# Changelog\n\nEach release's entries, grouped by the kind of change.",
    }
    values.update(overrides)
    return document(None, reader="user", kind="signpost", **values)


def _config(mode: str) -> str:
    friction = {"mode": mode, "surface": ["src"]}
    return json.dumps(
        {
            "name": "adopter",
            "docs": {"user": "docs/", "internal": "tech-docs/"},
            "friction": friction,
        },
        indent=2,
    )


def _to_this_interpreter(repo: AdopterRepo, script: Path) -> None:
    path = repo.root / script
    body = path.read_text(encoding="utf-8").split("\n", 1)[1]
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")


def _adopter(make_adopter_repo: MakeAdopterRepo, mode: str = "enforcing") -> AdopterRepo:
    """living-docs installed, its scripts under this interpreter, the page and the
    captured source committed on `main`, and branch `feature` checked out."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    for script in ("validate.py", "fill-doc-check.py", "resolve-source.py"):
        _to_this_interpreter(repo, SCRIPTS / script)
    repo.write(
        {
            CONFIG: _config(mode),
            "src/release/notes.py": "NOTES = 1\n",
            PAGE: _page(),
            KEEP: KEEP_A_CHANGELOG,
        }
    )
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    return repo


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    return _adopter(make_adopter_repo)


def _of_anchor(findings: Any, anchor: fd.Anchor = ANCHOR) -> list[Any]:
    return [f for f in findings if f.anchor == anchor]


def _states(repo: AdopterRepo) -> dict[str, fr.ArtefactState]:
    return {r.location: r.state for r in fr.run_repository_check(repo.root).artefact_reports}


def _run(
    root: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """A capability script of the adopter copy, run from its root."""
    script, *rest = args
    return subprocess.run(
        [str(root / script), *rest], cwd=root, capture_output=True, text=True, env=env, check=False
    )


def _resolve(root: Path, value: str) -> list[str]:
    """The resolver's answer for `value`, run as the backbone runs it."""
    completed = _run(root, str(RESOLVER), "--json", "--", value)
    assert completed.returncode == 0, completed.stderr
    answer = json.loads(completed.stdout)
    assert set(answer) == {"paths"}
    return answer["paths"]


def _validate(root: Path) -> dict[str, Any]:
    """The validator's findings document, as `pkit validate` reads it."""
    completed = _run(root, str(SCRIPTS / "validate.py"), "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _findings(document: dict[str, Any], severity: str) -> list[tuple[str, str]]:
    """The validator's findings of `severity` about sources: on the sources folder, a
    `source` anchor or a rule's cited source."""
    return [
        (f["location"], f["message"])
        for f in document["findings"]
        if f["severity"] == severity
        and (
            f["location"].startswith(SOURCES)
            or f["location"].endswith(("/pkit/friction/anchors/source", "/origin/source"))
        )
    ]


def _fill_doc_check(root: Path) -> subprocess.CompletedProcess[str]:
    return _run(root, str(SCRIPTS / "fill-doc-check.py"), "--json")


# --- 1. the source changed: the page is asked, and an answer clears it ----------------------


@pytest.mark.parametrize(
    "answer",
    [
        ("--outcome", "updated"),
        ("--outcome", "unchanged", "--because", "grouping by kind of change is still the rule"),
    ],
)
def test_a_new_version_recorded_stales_the_page_until_it_is_answered(
    repo: AdopterRepo, answer: tuple[str, ...]
) -> None:
    repo.commit("read Keep a Changelog 1.2.0", {KEEP: KEEP_A_CHANGELOG.replace("1.1.0", "1.2.0")})

    asked = fc.run_change_check(repo.root, "main")
    [finding] = _of_anchor(asked.findings)
    assert finding.kind is fc.FindingKind.FRICTION
    assert finding.message.startswith(f"changed in this diff ({KEEP}) and carries no answer")
    assert asked.failed
    assert CliRunner().invoke(main, ["friction", "check", "--base", "main"]).exit_code == 1

    whole = fr.run_repository_check(repo.root)
    assert {r.location: r.state for r in whole.artefact_reports}[PAGE] is fr.ArtefactState.STALE
    [stale] = _of_anchor(whole.findings)
    assert stale.kind is fr.RepositoryFindingKind.STALE

    owed = _fill_doc_check(repo.root)
    assert owed.returncode == 0, owed.stderr
    [obligation] = json.loads(owed.stdout)["value"]
    assert (obligation["reason"], obligation["document"]) == ("page-stale", PAGE)
    assert obligation["description"] == (
        f"stale: source keep-a-changelog changed — pkit friction explain {PAGE}"
    )

    if "updated" in answer:  # an `updated` answer comes with the page's change
        page = repo.root / PAGE
        page.write_text(page.read_text(encoding="utf-8") + "\nAs of 1.2.0.\n", encoding="utf-8")
    answered = CliRunner().invoke(main, ["friction", "revalidate", PAGE, *answer, "--yes"])
    assert answered.exit_code == 0, answered.output
    repo.commit("answer the new version", files=None)
    cleared = fc.run_change_check(repo.root, "main")
    [met] = _of_anchor(cleared.findings)
    assert (met.kind, met.answer) == (fc.FindingKind.ANSWERED, fc.Answer(answer[1]))
    assert not cleared.failed
    assert _states(repo)[PAGE] is fr.ArtefactState.CURRENT


# --- 2. nothing but a change to the source's file stales it -------------------------------


def test_only_a_change_to_the_captured_file_asks_the_page(repo: AdopterRepo) -> None:
    other = document(
        None,
        anchors={"path": ["src/release/**"]},
        reader="user",
        kind="signpost",
        body="# About Keep a Changelog\n\nA changelog format, described in prose.",
    )
    repo.commit(
        "describe the source elsewhere, and change an unrelated file",
        {"docs/about-keep-a-changelog.md": other, "README.md": "Readme.\n"},
    )
    assert _of_anchor(fc.run_change_check(repo.root, "main").findings) == []
    assert _states(repo)[PAGE] is fr.ArtefactState.CURRENT

    # Any change to the file is the source's change — a title alone too.
    repo.commit(
        "retitle the source", {KEEP: KEEP_A_CHANGELOG.replace("Keep a Changelog\n", "KaC\n")}
    )
    [finding] = _of_anchor(fc.run_change_check(repo.root, "main").findings)
    assert finding.kind is fc.FindingKind.FRICTION
    assert _states(repo)[PAGE] is fr.ArtefactState.STALE


# --- 3. a source of the wrong shape fails validation and still answers ------------------------


@pytest.mark.parametrize(
    ("captured", "said"),
    [
        pytest.param(
            KEEP_A_CHANGELOG + "description: A changelog format.\n", "description", id="extra-key"
        ),
        pytest.param("title: [Keep a Changelog\n", "", id="unparsable"),
        pytest.param(KEEP_A_CHANGELOG.replace('"1.1.0"', "1.1"), "1.1", id="unquoted-version"),
    ],
)
def test_a_source_of_the_wrong_shape_fails_data_and_its_page_stays_judged(
    repo: AdopterRepo, captured: str, said: str
) -> None:
    repo.commit("capture the source wrongly", {KEEP: captured})
    data = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "data"])
    assert data.exit_code == 1, data.output
    assert KEEP in data.output and said in data.output
    assert _resolve(repo.root, "keep-a-changelog") == [KEEP]
    # Judged: the file changed since the page's revalidation, so it is stale, never unresolved.
    assert _states(repo)[PAGE] is fr.ArtefactState.STALE


# --- 4. a name nothing captures is dead --------------------------------------------------


def test_a_name_nothing_captures_is_dead_and_the_page_is_judged_on_its_other_anchors(
    repo: AdopterRepo,
) -> None:
    dead = fd.Anchor("source", "no-such")
    anchors = {"path": ["src/release/**"], "source": ["keep-a-changelog", "no-such"]}
    repo.commit("rest the page on a source nobody captured", {PAGE: _page(anchors)})

    result = fc.run_change_check(repo.root, "main")
    [added] = _of_anchor(result.findings, dead)
    assert added.kind is fc.FindingKind.DEAD_ANCHOR
    assert added in result.failing and result.failed

    whole = fr.run_repository_check(repo.root)
    [reported] = _of_anchor(whole.findings, dead)
    assert reported.kind is fr.RepositoryFindingKind.DEAD_ANCHOR
    assert {r.location: r.state for r in whole.artefact_reports}[PAGE] is fr.ArtefactState.CURRENT

    validated = _validate(repo.root)
    assert _findings(validated, "error") == []
    [(location, message)] = _findings(validated, "report")
    assert location == f"{PAGE}:/pkit/friction/anchors/source"
    assert message.startswith(
        "anchor `source: no-such`, and no captured file answers it "
        f"({SOURCES}/no-such.yaml; a name is lower-case words"
    )


# --- 5. the layout -----------------------------------------------------------------------


def _layout_errors(root: Path) -> list[str]:
    return [location for location, _ in _findings(_validate(root), "error")]


def test_a_regular_file_where_the_folder_belongs_answers_nothing_and_fails(
    repo: AdopterRepo,
) -> None:
    shutil.rmtree(repo.root / SOURCES)
    (repo.root / SOURCES).write_text("not a folder\n", encoding="utf-8")
    assert _resolve(repo.root, "keep-a-changelog") == []
    [(location, message)] = _findings(_validate(repo.root), "error")
    assert location == SOURCES
    assert message.startswith(f"{SOURCES} is not a folder, so no source is read from it")


def test_a_linked_folder_answers_nothing_and_fails(repo: AdopterRepo, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    shutil.move(repo.root / SOURCES, elsewhere)
    (repo.root / SOURCES).symlink_to(elsewhere, target_is_directory=True)
    assert _resolve(repo.root, "keep-a-changelog") == []
    [(location, message)] = _findings(_validate(repo.root), "error")
    assert location == SOURCES
    assert message.startswith(f"{SOURCES} is a link, so no source is read from it")


@pytest.mark.parametrize("entry", ["link", "folder"])
def test_a_link_or_a_folder_of_the_name_answers_nothing_and_fails(
    repo: AdopterRepo, tmp_path: Path, entry: str
) -> None:
    captured = repo.root / KEEP
    if entry == "link":
        target = tmp_path / "keep-a-changelog.yaml"
        target.write_text(KEEP_A_CHANGELOG, encoding="utf-8")
        captured.unlink()
        captured.symlink_to(target)
    else:
        captured.unlink()
        captured.mkdir()
    assert _resolve(repo.root, "keep-a-changelog") == []
    [(location, message)] = _findings(_validate(repo.root), "error")
    assert location == KEEP
    assert f"is a {entry}; a captured source is a regular file, so it captures no source" in message


def test_a_name_outside_the_grammar_captures_nothing_on_any_disk(repo: AdopterRepo) -> None:
    """`Keep.yaml` is an error, and the anchor `keep` is dead even where the disk
    ignores case: the name is matched exactly, never looked up."""
    (repo.root / SOURCES / "Keep.yaml").write_text(KEEP_A_CHANGELOG, encoding="utf-8")
    assert _resolve(repo.root, "keep") == []
    assert _layout_errors(repo.root) == [f"{SOURCES}/Keep.yaml"]
    (repo.root / SOURCES / "notes.txt").write_text("Read on 2026-10-03.\n", encoding="utf-8")
    assert _layout_errors(repo.root) == [f"{SOURCES}/Keep.yaml", f"{SOURCES}/notes.txt"]


# --- 6. a folder that cannot be read is no answer ----------------------------------------


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root reads a folder of mode 000"
)
def test_a_sources_folder_that_cannot_be_read_leaves_the_page_unjudged(repo: AdopterRepo) -> None:
    folder = repo.root / SOURCES
    folder.chmod(0o000)
    try:
        unread = _run(repo.root, str(RESOLVER), "--json", "--", "keep-a-changelog")
        assert (unread.returncode, unread.stdout) == (1, "")
        assert "where sources are kept cannot be read" in unread.stderr

        result = fc.run_change_check(repo.root, "main")
        [finding] = _of_anchor(result.findings)
        assert finding.kind is fc.FindingKind.NO_ANSWER
        assert finding in result.failing

        assert _states(repo)[PAGE] is fr.ArtefactState.UNRESOLVED
        refused = CliRunner().invoke(main, ["friction", "record-status", PAGE, "--yes"])
        assert refused.exit_code != 0
        assert f"{PAGE} cannot be judged" in " ".join(refused.output.split())

        owed = _fill_doc_check(repo.root)
        assert (owed.returncode, owed.stdout) == (1, ""), owed.stderr
        assert f"friction on {PAGE} (unresolved) was not judged" in owed.stderr
        assert "an anchor's resolver gave no answer" in owed.stderr

        [(location, message)] = _findings(_validate(repo.root), "error")
        assert location == SOURCES
        assert message.startswith("the captured sources cannot be read")
    finally:
        folder.chmod(0o755)


#: Runs `answer` with `os.scandir` refusing, as a folder without read permission does.
SCANDIR_REFUSED = """
import os, sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from _lib import source_layout

def refused(path):
    raise PermissionError(13, "Permission denied", str(path))

os.scandir = refused
try:
    source_layout.answer(Path.cwd(), "keep-a-changelog")
except source_layout.Unreadable as exc:
    print(f"unreadable: {exc}")
"""


def test_answer_raises_unreadable_when_the_folder_cannot_be_listed(repo: AdopterRepo) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", SCANDIR_REFUSED, str(repo.root / SCRIPTS)],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("unreadable: ")
    assert completed.stdout.rstrip().endswith(f"{SOURCES}: Permission denied")


# --- 7. the resolver ---------------------------------------------------------------------


def test_the_resolver_answers_the_captured_file_from_the_arguments_it_is_given(
    repo: AdopterRepo,
) -> None:
    assert _resolve(repo.root, "keep-a-changelog") == [KEEP]
    longest = "a" * 64
    (repo.root / SOURCES / f"{longest}.yaml").write_text(KEEP_A_CHANGELOG, encoding="utf-8")
    assert _resolve(repo.root, longest) == [f"{SOURCES}/{longest}.yaml"]


@pytest.mark.parametrize(
    "value", ["-x", "--help", "../x", "Keep", "a/b", "a.b", "a--b", "a-", "a" * 65, ""]
)
def test_a_value_outside_the_grammar_answers_no_file(repo: AdopterRepo, value: str) -> None:
    for name in ("keep", "x", "a.b", "a--b", "a-", "a" * 65):
        (repo.root / SOURCES / f"{name}.yaml").write_text(KEEP_A_CHANGELOG, encoding="utf-8")
    assert _resolve(repo.root, value) == []


def test_without_the_project_tier_every_name_answers_no_file(repo: AdopterRepo) -> None:
    shutil.rmtree(repo.root / LD / "project")
    assert _resolve(repo.root, "keep-a-changelog") == []


def test_the_resolver_says_in_words_what_a_name_resolves_to(repo: AdopterRepo) -> None:
    found = _run(repo.root, str(RESOLVER), "keep-a-changelog")
    assert (found.returncode, found.stdout) == (0, f"{KEEP}\n")
    missing = _run(repo.root, str(RESOLVER), "no-such")
    assert (missing.returncode, missing.stdout) == (
        0,
        f"no source named 'no-such' is captured ({SOURCES}/no-such.yaml)\n",
    )
    assert _run(repo.root, str(RESOLVER)).returncode == 2


#: An adopter's own Python project, whose one dependency no cache holds or index serves.
UNRESOLVABLE_PROJECT = """\
[project]
name = "adopter"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["pkit-no-such-distribution==9.9.9"]
"""


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv runs the resolver's shebang")
@pytest.mark.parametrize("project", [None, UNRESOLVABLE_PROJECT], ids=["no-project", "uv-project"])
def test_the_resolver_runs_offline_from_an_empty_uv_cache_apart_from_the_project(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path, project: str | None
) -> None:
    """It declares no dependencies in its inline metadata, so its `uv run --script`
    shebang needs nothing provisioned — under the offline marker, with a cache
    nothing was ever put in — and runs apart from the project it is run in: an
    adopter's `pyproject.toml` whose dependency cannot be resolved is neither
    installed, nor given a lock file or an environment."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    repo.write({KEEP: KEEP_A_CHANGELOG})
    if project is not None:
        repo.write({"pyproject.toml": project})
    env = {**os.environ, "UV_OFFLINE": "1", "UV_CACHE_DIR": str(tmp_path / "empty-cache")}
    env.pop("VIRTUAL_ENV", None)
    completed = _run(repo.root, str(RESOLVER), "--json", "--", "keep-a-changelog", env=env)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"paths": [KEEP]}
    assert not (repo.root / "uv.lock").exists()
    assert not (repo.root / ".venv").exists()


# --- 8. the registration -----------------------------------------------------------------


def test_living_docs_registers_the_source_kind_with_its_resolver(repo: AdopterRepo) -> None:
    assert fd.registered_anchor_kinds(repo.root) == {
        "source": fd.ResolverCommand(
            "source",
            "living-docs",
            "resolve-source",
            query_contract=True,
            script=repo.root / RESOLVER,
        )
    }
    packages = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "packages"])
    assert packages.exit_code == 0, packages.output


# --- 9. a rule's origin citing a captured source -----------------------------------------


def _rule_set(value: str) -> str:
    """A project rule set whose one rule cites the source `value` as its origin."""
    origin = {
        "date": "2026-10-03",
        "by": "A. Person",
        "why": "Entries are grouped by the kind of change.",
        "source": {"kind": "source", "value": value},
    }
    front = {
        "rule-set": "CMN",
        "version": "1.0.0",
        "scope": ["docs/**"],
        "rules": {"RS-CMN-001": {"status": "accepted", "origin": origin}},
    }
    return (
        f"---\n{json.dumps(front, indent=2)}\n---\n\n# Rules\n\n"
        "## RS-CMN-001 — Group entries by kind\n\nThe statement of RS-CMN-001.\n"
    )


def test_a_rule_s_origin_cites_a_captured_source(repo: AdopterRepo) -> None:
    rules = "tech-docs/rule-sets/cmn.md"
    repo.write({rules: _rule_set("keep-a-changelog")})
    assert rs.validate_rule_sets(repo.root).findings == ()

    repo.write({rules: _rule_set("no-such")})
    [missing] = rs.validate_rule_sets(repo.root).findings
    assert missing.kind is rs.RuleSetFindingKind.MISSING_SOURCE
    assert missing.where == f"{rules}#RS-CMN-001 /origin/source"


# --- 10. the validator's reports ---------------------------------------------------------


def test_the_validator_reports_what_names_nothing_and_what_nothing_names(
    repo: AdopterRepo,
) -> None:
    anchors = {"path": ["src/release/**"], "source": ["not-captured"]}
    repo.write(
        {
            PAGE: _page(anchors),
            f"{SOURCES}/common-changelog.yaml": 'title: Common Changelog\nversion: "2026-10-03"\n',
            "tech-docs/rule-sets/cmn.md": _rule_set("keep-a-changelog"),
        }
    )
    validated = _validate(repo.root)
    assert _findings(validated, "error") == []
    reports = dict(_findings(validated, "report"))
    assert set(reports) == {
        f"{PAGE}:/pkit/friction/anchors/source",
        f"{SOURCES}/common-changelog.yaml",
    }
    assert reports[f"{SOURCES}/common-changelog.yaml"].startswith(
        "captured source `common-changelog` is anchored by no artefact and cited by no rule's "
        "origin"
    )
    # Keep a Changelog is cited by the rule's origin, so it is not reported.
    (line,) = [line for line in validated["summary"] if line.startswith("sources")]
    assert line == (
        f"sources (DEC-001 point 4): 2 captured in {SOURCES}/; 1 anchor(s) or citation(s) "
        "naming none, 1 captured source(s) nothing anchors or cites."
    )
    human = _run(repo.root, str(SCRIPTS / "validate.py"))
    assert human.returncode == 0, human.stdout


# --- 11. a misspelt kind leaves the documentation check answering ------------------------


def test_a_misspelt_kind_is_reported_with_the_nearest_kind_and_the_check_still_answers(
    repo: AdopterRepo,
) -> None:
    anchors = {"path": ["src/release/**"], "sources": ["keep-a-changelog"]}
    repo.commit("misspell the kind", {PAGE: _page(anchors)})
    [report] = [
        f
        for f in fv.validate_friction(repo.root).findings
        if f.kind is fv.FrictionFindingKind.UNRESOLVED_KIND
    ]
    assert report.severity is fv.Severity.REPORT
    assert report.where == f"{PAGE} /pkit/friction/anchors/sources"
    assert report.message.endswith("Did you mean 'source'?")

    owed = _fill_doc_check(repo.root)
    assert owed.returncode == 0, owed.stderr
    assert json.loads(owed.stdout) == {"schema_version": 1, "value": []}
