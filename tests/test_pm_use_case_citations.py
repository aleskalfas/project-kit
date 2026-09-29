"""Use-case citations in issue bodies (project-management DEC-054, #889).

Where the software-analysis capability is installed, a use case an issue body
cites (`UC-NNN`) must be a use case on the default branch; one that is not is
reported like a predicted decision id — a warning. Without software-analysis
the rule is inert.

Covers `_lib/use_case_citations.py` on its own (what a body cites, the
findings, where the use cases lie, how a file is recognised as one, the reading
of a real repository's default branch, the install test), the rule inside the
two body validators (`validate-issue`, `edit-issue`), their main paths against
a repository with `gh` mocked, in both install states, and the rule's parity
with `body-format.yaml`.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.adopter_repo import GitRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAPABILITY_ROOT / "scripts"


def _load(module_name: str, path: Path) -> ModuleType:
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
def uc() -> ModuleType:
    return _load("pm_use_case_citations_under_test", SCRIPTS_DIR / "_lib" / "use_case_citations.py")


@pytest.fixture(scope="module")
def vi() -> ModuleType:
    return _load("pm_validate_issue_for_use_cases", SCRIPTS_DIR / "validate-issue.py")


@pytest.fixture(scope="module")
def ei() -> ModuleType:
    return _load("pm_edit_issue_for_use_cases", SCRIPTS_DIR / "edit-issue.py")


# --- a repository with use cases ---------------------------------------------

ANALYSIS = "tech-docs/analysis"
USE_CASES = f"{ANALYSIS}/use-case-model/use-cases"


def _use_case(uc_id: str, *, status: str = "active") -> str:
    return (
        f"---\nid: {uc_id}\nstatus: {status}\nactor: ACT-maintainer\n---\n\n"
        f"# {uc_id} — A goal\n\n**Goal:** something.\n"
    )


def _manifest(*capabilities: str) -> str:
    entries = "".join(
        f"  - kind: capability\n    name: {name}\n"
        f"    manifest: .pkit/capabilities/{name}/manifest.yaml\n"
        for name in capabilities
    )
    return f"schema_version: 1\nbackbone_version: 1.149.0\ncomponents:\n{entries}"


def _analysis_repo(root: Path, *, installed: bool = True) -> GitRepo:
    """A repository whose `main` carries use cases UC-001 (at the top),
    UC-002 (withdrawn) and UC-014 (grouped by area), a journey and a
    revalidation record that cites a use case, under an internal root
    `tech-docs/`."""
    repo = GitRepo.init(root)
    capabilities = (
        ("project-management", "software-analysis") if installed else ("project-management",)
    )
    repo.commit(
        "analysis",
        {
            ".pkit/manifest.yaml": _manifest(*capabilities),
            ".pkit/project/config.yaml": "docs:\n  user: docs/\n  internal: tech-docs/\n",
            f"{USE_CASES}/UC-001-run-a-suite.md": _use_case("UC-001"),
            f"{USE_CASES}/UC-002-old-flow.md": _use_case("UC-002", status="withdrawn"),
            f"{USE_CASES}/export/UC-014-export.md": _use_case("UC-014"),
            f"{ANALYSIS}/use-case-model/journeys/JRN-001-onboard.md": (
                "---\nid: JRN-001\nsteps: [UC-001, UC-014]\n---\n\n# JRN-001 — Onboard\n"
            ),
            f"{ANALYSIS}/revalidations/2026-09-01-export.md": (
                "---\ntrigger: planned\nartefacts: [UC-014]\n---\n\nid: UC-099 holds.\n"
            ),
        },
    )
    return repo


# --- what a body cites ---------------------------------------------------------


def test_cited_use_cases_are_found_once_in_order(uc: ModuleType) -> None:
    body = "Feature: #1\n\n## Use cases\n\n- UC-014 export\n- UC-001\n\nSee UC-014 again."
    assert uc.cited_use_cases(body) == ["UC-014", "UC-001"]


@pytest.mark.parametrize("text", ["UC-NNN", "UC-12", "JRN-001", "ACT-maintainer", "XUC-001"])
def test_what_is_not_a_use_case_citation(uc: ModuleType, text: str) -> None:
    assert uc.cited_use_cases(f"Mentions {text} only.") == []


# --- the findings --------------------------------------------------------------


def _known(uc: ModuleType, *ids: str) -> Any:
    return uc.UseCases(ref="origin/main", location=ANALYSIS, ids=frozenset(ids))


def test_no_finding_where_the_rule_is_inert(uc: ModuleType) -> None:
    assert uc.check("cites UC-042", None) == []


def test_no_finding_when_every_citation_exists(uc: ModuleType) -> None:
    assert uc.check("UC-001 and UC-002", _known(uc, "UC-001", "UC-002")) == []


def test_an_unknown_citation_is_reported_as_a_warning(uc: ModuleType) -> None:
    findings = uc.check("UC-001, UC-042 and UC-043", _known(uc, "UC-001"))
    assert len(findings) == 1
    severity, label, detail = findings[0]
    assert (severity, label) == ("warning", "body.use-case-citation")
    assert "UC-042 and UC-043" in detail
    assert "UC-001" not in detail
    assert "origin/main" in detail and ANALYSIS in detail


def test_an_unreadable_default_branch_says_the_citations_were_not_checked(
    uc: ModuleType,
) -> None:
    findings = uc.check("UC-042", uc.Unreadable("no ref"))
    assert findings == [
        (
            "warning",
            "body.use-case-citation.unverified",
            "could not read the use cases on the default branch (no ref), so UC-042 "
            "was not checked. This is not a report that it does not exist.",
        )
    ]


# --- where the use cases lie ---------------------------------------------------


def test_location_defaults_to_the_analysis_sub_path_of_the_internal_root(
    uc: ModuleType,
) -> None:
    assert uc.analysis_location(backbone_config=None, package=None, recorded=None) == (
        "docs/analysis"
    )
    assert (
        uc.analysis_location(
            backbone_config={"docs": {"internal": "tech-docs/"}}, package=None, recorded=None
        )
        == "tech-docs/analysis"
    )


def test_location_follows_the_package_declaration_and_its_root(uc: ModuleType) -> None:
    config = {"docs": {"internal": "tech-docs", "user": "site"}}
    declared = {"docs": {"locations": {"analysis": {"path": "product/analysis"}}}}
    assert (
        uc.analysis_location(backbone_config=config, package=declared, recorded=None)
        == "tech-docs/product/analysis"
    )
    user = {"docs": {"locations": {"analysis": {"path": "analysis", "root": "user"}}}}
    assert (
        uc.analysis_location(backbone_config=config, package=user, recorded=None) == "site/analysis"
    )


def test_a_recorded_location_wins(uc: ModuleType) -> None:
    declared = {"docs": {"locations": {"analysis": {"path": "product"}}}}
    recorded = {"locations": {"analysis": "docs/old-analysis/"}}
    assert (
        uc.analysis_location(backbone_config=None, package=declared, recorded=recorded)
        == "docs/old-analysis"
    )


def test_a_malformed_declaration_reads_as_absent(uc: ModuleType) -> None:
    for declaration in ("analysis", {"root": "internal"}, {"path": "a", "root": "elsewhere"}):
        package = {"docs": {"locations": {"analysis": declaration}}}
        assert (
            uc.analysis_location(backbone_config=None, package=package, recorded=None)
            == "docs/analysis"
        )


# --- a use case ------------------------------------------------------------------


def test_front_matter_id(uc: ModuleType) -> None:
    assert uc.front_matter_id(_use_case("UC-003")) == "UC-003"
    assert uc.front_matter_id("# UC-003 — no front matter\n") is None
    assert uc.front_matter_id("---\nid: JRN-001\n---\n") is None
    assert uc.front_matter_id("---\nid: [unclosed\n---\n") is None
    assert uc.front_matter_id("---\nid: UC-003\n") is None  # never closed


# --- the default branch of a real repository ------------------------------------


def test_the_default_branch_use_cases_are_read_by_front_matter(
    uc: ModuleType, tmp_path: Path
) -> None:
    repo = _analysis_repo(tmp_path)
    result = uc.default_branch_use_cases(repo.root, "main")
    assert result == uc.UseCases(
        ref="main", location=ANALYSIS, ids=frozenset({"UC-001", "UC-002", "UC-014"})
    )


def test_a_use_case_only_on_a_branch_is_not_on_the_default_branch(
    uc: ModuleType, tmp_path: Path
) -> None:
    repo = _analysis_repo(tmp_path)
    repo.checkout("feat/new-use-case", create=True)
    repo.commit("add UC-003", {f"{USE_CASES}/UC-003-new.md": _use_case("UC-003")})
    result = uc.default_branch_use_cases(repo.root, "main")
    assert isinstance(result, uc.UseCases)
    assert "UC-003" not in result.ids


def test_the_remote_tracking_ref_is_preferred(uc: ModuleType, tmp_path: Path) -> None:
    repo = _analysis_repo(tmp_path)
    fetched = repo.head()
    repo.commit("local only", {f"{USE_CASES}/UC-020-local.md": _use_case("UC-020")})
    repo.git("update-ref", "refs/remotes/origin/main", fetched)
    result = uc.default_branch_use_cases(repo.root, "main")
    assert isinstance(result, uc.UseCases)
    assert result.ref == "origin/main"
    assert "UC-020" not in result.ids


def test_an_unresolvable_default_branch_is_unreadable(uc: ModuleType, tmp_path: Path) -> None:
    repo = _analysis_repo(tmp_path)
    assert uc.default_branch_use_cases(repo.root, "trunk") == uc.Unreadable(
        "neither origin/trunk nor trunk resolves in this clone"
    )


def test_a_project_with_no_use_cases_yet_has_none(uc: ModuleType, tmp_path: Path) -> None:
    repo = GitRepo.init(tmp_path)
    repo.commit("empty", {"README.md": "hello\n"})
    assert uc.default_branch_use_cases(repo.root, "main") == uc.UseCases(
        ref="main", location="docs/analysis", ids=frozenset()
    )


# --- the install test: active only when software-analysis is installed ------------


def test_read_for_is_inert_when_software_analysis_is_not_installed(
    uc: ModuleType, tmp_path: Path
) -> None:
    repo = _analysis_repo(tmp_path, installed=False)
    assert uc.read_for("cites UC-042", repo.root, {}) is None


def test_read_for_reads_the_default_branch_when_installed(uc: ModuleType, tmp_path: Path) -> None:
    repo = _analysis_repo(tmp_path)
    result = uc.read_for("cites UC-042", repo.root, {"default_branch": "main"})
    assert isinstance(result, uc.UseCases)
    assert result.ids == frozenset({"UC-001", "UC-002", "UC-014"})


def test_read_for_reads_nothing_for_a_body_citing_no_use_case(
    uc: ModuleType, tmp_path: Path
) -> None:
    # No repository at all: nothing is read when nothing is cited.
    assert uc.read_for("no citations", tmp_path, {}) is None


def test_read_for_reports_an_unreadable_manifest(uc: ModuleType, tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    (tmp_path / ".pkit" / "manifest.yaml").write_text("components: [unclosed\n", encoding="utf-8")
    assert uc.read_for("UC-001", tmp_path, {}) == uc.Unreadable(
        "the project manifest could not be read"
    )


# --- inside the validators ---------------------------------------------------------

TASK_BODY = (
    "Feature: #10\n\n## What\n\nx\n\n## Acceptance criteria\n\n- [ ] y\n\n"
    "## Doc impact\n\nNo doc impact — internal.\n\n## Use cases\n\n- UC-001\n- UC-042\n"
)


def _labels(findings: list[Any]) -> list[str]:
    return [f.label for f in findings]


def test_validate_issue_reports_an_unknown_citation(vi: ModuleType, uc: ModuleType) -> None:
    findings = vi._validate_issue(
        issue={"title": "[Task] Do a thing", "body": TASK_BODY, "labels": []},
        issue_types={},
        titles={},
        body_format={},
        config={},
        use_cases=_known(uc, "UC-001"),
    )
    [finding] = [f for f in findings if f.label == "body.use-case-citation"]
    assert finding.severity == "warning"
    assert "UC-042" in finding.detail


def test_validate_issue_is_unchanged_where_the_rule_is_inert(vi: ModuleType) -> None:
    findings = vi._validate_issue(
        issue={"title": "[Task] Do a thing", "body": TASK_BODY, "labels": []},
        issue_types={},
        titles={},
        body_format={},
        config={},
    )
    assert not [label for label in _labels(findings) if label.startswith("body.use-case")]


def test_edit_issue_reports_an_unknown_citation_on_a_body_edit(
    ei: ModuleType, uc: ModuleType
) -> None:
    findings = ei._validate(
        title="[Task] Do a thing",
        body=TASK_BODY,
        issue_types={},
        titles={},
        body_format={},
        check_title=False,
        use_cases=_known(uc, "UC-001"),
    )
    assert _labels(findings) == ["body.use-case-citation"]


def test_edit_issue_drops_the_rule_on_a_title_only_edit(ei: ModuleType, uc: ModuleType) -> None:
    findings = ei._validate(
        title="[Task] Do a thing",
        body=TASK_BODY,
        issue_types={},
        titles={},
        body_format={},
        check_body=False,
        use_cases=_known(uc, "UC-001"),
    )
    assert "body.use-case-citation" not in _labels(findings)


# --- the main paths, gh mocked, in both install states ----------------------------


def _adopter(root: Path, *, installed: bool) -> Path:
    """The analysis repository with project-management's schemas and templates in
    place and its project configuration; returns the capability root."""
    _analysis_repo(root, installed=installed)
    capability_root = root / ".pkit" / "capabilities" / "project-management"
    for folder in ("schemas", "templates"):
        shutil.copytree(CAPABILITY_ROOT / folder, capability_root / folder)
    (capability_root / "project").mkdir()
    (capability_root / "project" / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\n", encoding="utf-8"
    )
    return capability_root


def _issue(number: int, config: dict[str, Any]) -> dict[str, Any]:
    return {"number": number, "title": "[Task] Do a thing", "body": TASK_BODY, "labels": []}


def _allow(*_args: object, **_kwargs: object) -> bool:
    return True


@pytest.fixture
def mocked_gh(vi: ModuleType, ei: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """`gh` never runs: the issue is served here, and the gates that would read
    `gh` or the session (bootstrap stamp, foreign-repo guard) let the run pass."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "someone")
    for module in (vi, ei):
        monkeypatch.setattr(module, "_gh_get_issue", _issue)
        monkeypatch.setattr(module.bootstrap_gate, "enforce", _allow)
    monkeypatch.setattr(ei.session_guard, "enforce", _allow)


@pytest.mark.parametrize("installed", [True, False])
def test_validate_issue_main_checks_citations_only_when_installed(
    vi: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mocked_gh: None,
    installed: bool,
) -> None:
    capability_root = _adopter(tmp_path, installed=installed)
    monkeypatch.setattr(
        sys, "argv", ["validate-issue", "7", "--capability-root", str(capability_root), "--json"]
    )
    vi.main()
    findings = json.loads(capsys.readouterr().out)["findings"]
    cited = [f for f in findings if f["label"].startswith("body.use-case")]
    if installed:
        assert [(f["severity"], f["label"]) for f in cited] == [
            ("warning", "body.use-case-citation")
        ]
        assert "UC-042" in cited[0]["detail"] and "UC-001" not in cited[0]["detail"]
    else:
        assert cited == []


@pytest.mark.parametrize("installed", [True, False])
def test_edit_issue_main_checks_citations_only_when_installed(
    ei: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mocked_gh: None,
    installed: bool,
) -> None:
    capability_root = _adopter(tmp_path, installed=installed)
    body_file = tmp_path / "body.md"
    body_file.write_text(TASK_BODY, encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "edit-issue",
            "7",
            "--capability-root",
            str(capability_root),
            "--body-file",
            str(body_file),
            "--dry-run",
        ],
    )
    assert ei.main() == 0  # a warning never refuses the edit
    out = capsys.readouterr().out
    assert ("[warning] body.use-case-citation:" in out) is installed


# --- parity with the schema --------------------------------------------------------


def test_the_rule_shares_the_predicted_decision_id_severity(uc: ModuleType) -> None:
    body_format: Any = YAML(typ="safe").load(  # pyright: ignore[reportUnknownMemberType]
        (CAPABILITY_ROOT / "schemas" / "body-format.yaml").read_text(encoding="utf-8")
    )
    rules: list[dict[str, str]] = body_format["universal_body_rules"]
    [predicted] = [r for r in rules if "predicted decision IDs" in r["rule"]]
    [citation] = [r for r in rules if "DEC-054" in r["rule"]]
    assert citation["severity"] == predicted["severity"]
    assert citation["severity"] == f"[validation-severity:{uc.SEVERITY}]"
