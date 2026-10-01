"""The doc-check data point, end to end (#1000; DEC-053, COR-052, COR-053).

project-management provides the `pkit::work-tracking` role and defines
`pkit::work-tracking:doc-check`: additive, inert `fail`, its code-to-doc
mapping the always-included default filler (`fill-doc-check`, its own command
contribution). `check-doc-mapping` reads the resolved point through `pkit
connections resolve` and applies it to a pull request's diff.

Three layers:

- the pieces — the package declaration, the companion schema, the mapping as
  obligations, the per-source settings, reading the point document;
- the point through the real backbone, in an adopter repository with the
  capability installed — its default filler run as a query, a documentation
  capability contributing beside it;
- `check-doc-mapping` over that repository, reading the point through a `pkit`
  that is the real CLI: a contributed obligation naming a page met only by
  that page in the diff, one naming only a path unmet for as long as it is
  given, neither by a `## Doc impact` line; each source enforced on its own
  setting; an unresolved point failing the check, naming the filler and the fix.

The filler's `uv run --script` shebang is pointed at this interpreter in the
adopter copy, so no test reaches `uv` or the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import data_points as dp
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _lib import doc_check  # noqa: E402

POINT = "pkit::work-tracking:doc-check"
PM = "project-management"
DOCS_CAP = "docs-test"
PM_REL = Path(".pkit") / "capabilities" / PM
CHECK = PM_REL / "scripts" / "check-doc-mapping.py"
FILLER_FILE = "docs/pkit/fillers/pkit/work-tracking/doc-check.yaml"

RULES = """\
code_path_to_doc_mapping:
  enforce: {enforce}
  rules:
    - {{ code: "src/**", docs: [README.md] }}
    - {{ code: "lib/**", docs: [docs/lib.md] }}
"""

STALE_GUIDE = {
    "id": "friction:docs/guide.md",
    "source": "friction",
    "reason": "page-stale",
    "document": "docs/guide.md",
    "description": "an anchor of the guide changed",
}

# Code nothing documents: its answer is a page anchoring it, so it names no page.
UNANCHORED = {
    "id": "friction:code-undocumented:src/a.py",
    "source": "friction",
    "reason": "code-undocumented",
    "path": "src/a.py",
    "description": "src/a.py is in the declared surface and nothing anchors it — "
    "anchor it from a page",
}


def _schema() -> Draft202012Validator:
    return Draft202012Validator(
        json.loads((CAPABILITY / "schemas" / "doc-check.schema.json").read_text(encoding="utf-8"))
    )


# --- the pieces -------------------------------------------------------------------------


def test_pm_provides_the_role_and_accepts_the_point_with_its_companion_schema() -> None:
    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    connections = package["connections"]
    assert connections["roles"] == ["pkit::work-tracking"]
    point = connections["extension-points"]["accepts"][POINT]
    assert {k: point[k] for k in ("schema_version", "schema", "combination", "inert")} == {
        "schema_version": 1,
        "schema": "doc-check.schema.json",
        "combination": "additive",
        "inert": "fail",
    }
    assert point["description"].strip()
    # The default filler: its own command contribution, always taking part.
    (contribution,) = connections["extensions"]["contributes"]
    assert contribution == {
        "point": POINT,
        "schema_version": 1,
        "command": "fill-doc-check",
        "description": contribution["description"],
    }
    assert package["commands"]["fill-doc-check"]["query-contract"] is True
    assert (CAPABILITY / package["commands"]["fill-doc-check"]["script"]).is_file()


def test_the_mapping_becomes_one_obligation_per_rule_keyed_by_the_rule() -> None:
    rules = [
        {"code": "src/**", "docs": ["README.md"]},
        "not-a-rule",
        {"code": "lib/**"},
        {"docs": ["x.md"]},
        {"code": "tools/**", "docs": "not-a-list"},
        {"code": "src/**", "docs": ["docs/api.md", "docs/cli.md"]},
        {"code": "src/**", "docs": ["docs/more.md"]},
    ]
    obligations = doc_check.mapping_obligations(rules)
    assert [o["id"] for o in obligations] == [
        "mapping:src/**",
        "mapping:src/**#2",
        "mapping:src/**#3",
    ]
    assert obligations[1] == {
        "id": "mapping:src/**#2",
        "source": "mapping",
        "reason": "mapped-path-changed",
        "code": "src/**",
        "documents": ["docs/api.md", "docs/cli.md"],
    }
    assert doc_check.mapping_obligations(None) == []
    assert _schema().is_valid(obligations)


def test_the_companion_schema_separates_mapping_from_contributed_obligations() -> None:
    schema = _schema()
    assert schema.is_valid([STALE_GUIDE])
    for broken in (
        {**STALE_GUIDE, "document": ""},
        {k: v for k, v in STALE_GUIDE.items() if k != "document"},
        {**STALE_GUIDE, "reason": "mapped-path-changed"},
        {**STALE_GUIDE, "extra": 1},
        # A mapping obligation has the mapping's shape, whoever writes it.
        {**STALE_GUIDE, "source": "mapping"},
        {
            "id": "x",
            "source": "mapping",
            "reason": "mapped-path-changed",
            "code": "a/**",
            "documents": [],
        },
    ):
        assert not schema.is_valid([broken]), broken


def test_a_page_s_friction_names_its_page_and_undocumented_code_its_path() -> None:
    """`document` is required of `page-stale`, optional for `code-undocumented`:
    its subject is its `path`, answered by a page anchoring it, not by a page
    changing."""
    schema = _schema()
    assert schema.is_valid([UNANCHORED])
    assert schema.is_valid([{**UNANCHORED, "document": "docs/a.md"}])
    for broken in (
        {k: v for k, v in STALE_GUIDE.items() if k != "document"},
        {k: v for k, v in UNANCHORED.items() if k != "path"},
        {**UNANCHORED, "path": ""},
    ):
        assert not schema.is_valid([broken]), broken


@pytest.mark.parametrize(
    ("config", "settings", "problem"),
    [
        ({}, {}, None),
        ({"doc_check": {}}, {}, None),
        ({"doc_check": {"sources": {"friction": "enforcing"}}}, {"friction": "enforcing"}, None),
        ({"doc_check": ["x"]}, {}, "`doc_check` must be a mapping"),
        ({"doc_check": {"sources": ["friction"]}}, {}, "`doc_check.sources` must map"),
        ({"doc_check": {"sources": {"friction": "loud"}}}, {}, "is 'loud'"),
        (
            {"doc_check": {"sources": {"mapping": "enforcing"}}},
            {},
            "the mapping keeps its own, `code_path_to_doc_mapping.enforce`",
        ),
    ],
)
def test_per_source_settings(
    config: dict[str, Any], settings: dict[str, str], problem: str | None
) -> None:
    got, why = doc_check.source_settings(config)
    assert got == settings
    assert (why is None) if problem is None else (why is not None and problem in why)


def test_a_contributed_source_is_advisory_unless_the_project_enforces_it() -> None:
    assert doc_check.setting_of({}, "friction") == "advisory"
    assert doc_check.setting_of({"friction": "enforcing"}, "friction") == "enforcing"


def test_reading_the_point_takes_the_document_whatever_the_exit_code() -> None:
    document = {"address": POINT, "defined": True, "resolved": False, "why": "w", "fillers": []}

    def unresolved(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["pkit", "connections", "resolve", POINT, "--json"]
        return subprocess.CompletedProcess(argv, 1, json.dumps(document), "")

    point = doc_check.read_point(unresolved)
    assert (point.resolved, point.why) == (False, "w")

    def undefined(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        body = {"address": POINT, "defined": False, "resolved": False, "why": "no provider"}
        return subprocess.CompletedProcess(argv, 1, json.dumps(body), "")

    assert doc_check.read_point(undefined).why == "it is not defined: no provider"

    def old_backbone(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2, "", "Error: No such command 'connections'.\n")

    with pytest.raises(doc_check.PointUnreadable, match="No such command 'connections'"):
        doc_check.read_point(old_backbone)

    def absent(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(argv[0])

    with pytest.raises(doc_check.PointUnreadable, match="not on PATH"):
        doc_check.read_point(absent)


def test_only_the_capability_s_own_filler_supplies_mapping_obligations() -> None:
    (own,) = doc_check.mapping_obligations([{"code": "src/**", "docs": ["README.md"]}])
    point = doc_check.ResolvedPoint(
        resolved=True,
        entries=(
            (own["id"], PM, own),
            ("mapping:lib/**", DOCS_CAP, {**own, "id": "mapping:lib/**"}),
            (STALE_GUIDE["id"], DOCS_CAP, STALE_GUIDE),
        ),
    )
    split = doc_check.split(point, PM)
    assert split.mapping == [own]
    assert split.contributed == [STALE_GUIDE]
    assert split.problems == [
        "entry 'mapping:lib/**' from docs-test claims the `mapping` source, which only "
        "project-management's own filler supplies"
    ]


# --- the point through the backbone ------------------------------------------------------


def _pm_file(repo: AdopterRepo, relpath: str) -> Path:
    return repo.root / PM_REL / relpath


def _configure(repo: AdopterRepo, mapping: str, extra: str = "") -> None:
    """The project's pm config, and the stamp `check-doc-mapping`'s gate reads."""
    project = _pm_file(repo, "project")
    project.mkdir(parents=True, exist_ok=True)
    (project / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: []\n" + mapping + extra,
        encoding="utf-8",
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


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """An adopter with project-management installed and its mapping configured.
    The filler runs under this interpreter rather than `uv run --script`."""
    repo = make_adopter_repo(capabilities=(PM,))
    filler = _pm_file(repo, "scripts/fill-doc-check.py")
    body = filler.read_text(encoding="utf-8").split("\n", 1)[1]
    filler.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    _configure(repo, RULES.format(enforce="false"))
    return repo


def _contribute(repo: AdopterRepo, obligations: list[dict[str, Any]], *, version: int = 1) -> None:
    """A documentation capability contributing obligations to the point."""
    cap = repo.pkit / "capabilities" / DOCS_CAP
    cap.mkdir(parents=True, exist_ok=True)
    package = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": DOCS_CAP, "version": "0.1.0"},
        "description": "A documentation capability, for the test.",
        "requires_backbone": ">=0.0.0",
        "connections": {
            "extensions": {
                "contributes": [{"point": POINT, "schema_version": version, "value": obligations}]
            }
        },
    }
    with (cap / "package.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(package, handle)
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    if not any(e.name == DOCS_CAP for e in backbone.components):
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=DOCS_CAP,
                manifest=f".pkit/capabilities/{DOCS_CAP}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)


def _resolve(repo: AdopterRepo) -> dict[str, Any]:
    result = CliRunner().invoke(main, ["connections", "resolve", POINT, "--json"])
    return json.loads(result.output)


def test_the_point_resolves_to_the_mapping_through_its_default_filler(project: AdopterRepo) -> None:
    document = _resolve(project)
    assert (document["resolved"], document["policy"], document["inert_policy"]) == (
        True,
        "additive",
        "fail",
    )
    assert [(e["id"], e["origin"]) for e in document["entries"]] == [
        ("mapping:src/**", PM),
        ("mapping:lib/**", PM),
    ]
    assert document["value"] == doc_check.mapping_obligations(
        [{"code": "src/**", "docs": ["README.md"]}, {"code": "lib/**", "docs": ["docs/lib.md"]}]
    )
    (filler,) = document["fillers"]
    assert (filler["name"], filler["supplies"], filler["state"], filler["query_contract"]) == (
        PM,
        "command 'fill-doc-check'",
        "taken",
        True,
    )
    # Resolved cleanly: nothing for `pkit validate` to report about it.
    assert dp.resolve_data_points(project.root).findings == ()


def test_no_mapping_resolves_to_no_obligations(project: AdopterRepo) -> None:
    _configure(project, "")
    document = _resolve(project)
    assert (document["resolved"], document["value"]) == (True, [])


def test_a_documentation_capability_adds_to_the_mapping_and_removes_nothing(
    project: AdopterRepo,
) -> None:
    _contribute(project, [STALE_GUIDE])
    document = _resolve(project)
    assert document["resolved"]
    assert [(e["id"], e["origin"]) for e in document["entries"]] == [
        (STALE_GUIDE["id"], DOCS_CAP),
        ("mapping:src/**", PM),
        ("mapping:lib/**", PM),
    ]


# --- check-doc-mapping over the resolved point -----------------------------------------------


def _pkit_on_path(tmp_path: Path) -> Path:
    """A `pkit` that is the real CLI, under this interpreter."""
    bin_dir = tmp_path / "pkit-bin"
    bin_dir.mkdir()
    pkit = bin_dir / "pkit"
    pkit.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m project_kit "$@"\n', encoding="utf-8")
    pkit.chmod(0o755)
    return bin_dir


def _check(
    repo: AdopterRepo, tmp_path: Path, changes: dict[str, str], body: str = ""
) -> subprocess.CompletedProcess[str]:
    """Commit the project as it stands as `base`, then `changes` as the head, and
    run the check from the repository with the real `pkit` first on PATH."""
    repo.write({"README.md": "# R\n", "docs/guide.md": "# Guide\n", "docs/lib.md": "# Lib\n"})
    repo.commit("base")
    repo.git("branch", "base")
    repo.commit("head", changes)
    body_file = tmp_path / "body.md"
    body_file.write_text(body, encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{_pkit_on_path(tmp_path)}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    env.pop("PKIT_OFFLINE", None)
    return subprocess.run(
        [
            sys.executable,
            str(repo.root / CHECK),
            "--base",
            "refs/heads/base",
            "--pr-body-file",
            str(body_file),
        ],
        cwd=repo.root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_without_a_documentation_capability_only_the_mapping_is_checked(
    project: AdopterRepo, tmp_path: Path
) -> None:
    run = _check(project, tmp_path, {"src/a.py": "a\n"})
    assert (run.returncode, run.stdout) == (
        0,
        "check-doc-mapping: 2 rule(s), 1 changed file(s), mode=advisory\n"
        "  ✗ src/** → README.md (not updated; e.g. src/a.py)\n",
    )


def test_a_contributed_obligation_is_met_only_by_its_page_in_the_diff(
    project: AdopterRepo, tmp_path: Path
) -> None:
    _contribute(project, [STALE_GUIDE])
    body = "## Doc impact\n- docs/guide.md: no change needed, the anchor moved only\n"
    run = _check(project, tmp_path, {"lib/x.py": "x\n", "docs/lib.md": "# Lib 2\n"}, body)
    assert run.stdout == (
        "check-doc-mapping: 2 rule(s), 2 changed file(s), mode=advisory\n"
        "check-doc-mapping: 1 contributed obligation(s) from friction\n"
        "  ✓ lib/** → doc updated\n"
        "  ✗ [friction] docs/guide.md → no answer in the diff (page-stale)\n"
    )
    # Advisory by default: reported, and the check passes.
    assert run.returncode == 0
    assert run.stderr == (
        "\n[advisory] 1 friction obligation(s) unanswered. Set "
        "doc_check.sources.friction: enforcing to block.\n"
    )


def test_the_page_changed_in_the_diff_answers_it(project: AdopterRepo, tmp_path: Path) -> None:
    _contribute(project, [STALE_GUIDE])
    run = _check(project, tmp_path, {"docs/guide.md": "# Guide, revalidated\n"})
    assert (run.returncode, run.stderr) == (0, "")
    assert run.stdout.splitlines()[-2:] == [
        "  ✓ [friction] docs/guide.md → answered in the diff",
        "check-doc-mapping: every obligation met.",
    ]


def test_each_source_is_enforced_on_its_own_setting(project: AdopterRepo, tmp_path: Path) -> None:
    _configure(
        project,
        RULES.format(enforce="false"),
        "doc_check:\n  sources:\n    friction: enforcing\n",
    )
    _contribute(project, [STALE_GUIDE])
    run = _check(project, tmp_path, {"src/a.py": "a\n"})
    # The enforcing source fails the check; the advisory mapping only reports.
    assert run.returncode == 1
    assert run.stderr == (
        "\n[advisory] 1 mapping(s) would fire under enforce: true. Set "
        "code_path_to_doc_mapping.enforce: true (with surgical rules) to block.\n"
        "\n[refused] 1 friction obligation(s) unanswered — answer each on its page in this "
        "diff; a `## Doc impact` line does not meet them.\n"
    )


def test_enforcing_the_mapping_enforces_no_other_source(
    project: AdopterRepo, tmp_path: Path
) -> None:
    _configure(project, RULES.format(enforce="true"))
    _contribute(project, [STALE_GUIDE])
    run = _check(project, tmp_path, {"lib/x.py": "x\n", "docs/lib.md": "# Lib 2\n"})
    assert run.returncode == 0
    assert "[advisory] 1 friction obligation(s) unanswered" in run.stderr


@pytest.mark.parametrize(
    ("setting", "code", "summary"),
    [
        (
            "advisory",
            0,
            "[advisory] 1 friction obligation(s) unanchored. Set "
            "doc_check.sources.friction: enforcing to block.",
        ),
        (
            "enforcing",
            1,
            "[refused] 1 friction obligation(s) unanchored — anchor each path from a page; "
            "a `## Doc impact` line does not meet them.",
        ),
    ],
)
def test_an_unanchored_path_is_unmet_whatever_page_the_diff_changes(
    project: AdopterRepo, tmp_path: Path, setting: str, code: int, summary: str
) -> None:
    """A path obligation stays unmet while it is given — the internal root's
    pages changed, a `## Doc impact` line naming it — and the line names the fix.
    The page obligation beside it is met by its page, as before."""
    _configure(
        project,
        RULES.format(enforce="false"),
        f"doc_check:\n  sources:\n    friction: {setting}\n",
    )
    _contribute(project, [STALE_GUIDE, UNANCHORED])
    body = "## Doc impact\n- src/a.py: described in docs/guide.md\n"
    changes = {"docs/guide.md": "# Guide 2\n", "docs/new.md": "# New\n"}
    run = _check(project, tmp_path, changes, body)
    assert (run.returncode, run.stdout, run.stderr) == (
        code,
        "check-doc-mapping: 2 rule(s), 2 changed file(s), mode=advisory\n"
        "check-doc-mapping: 2 contributed obligation(s) from friction\n"
        "  ✓ [friction] docs/guide.md → answered in the diff\n"
        "  ✗ [friction] src/a.py → no page anchors it (code-undocumented); "
        "anchor `src/a.py` from a page\n",
        f"\n{summary}\n",
    )


def test_an_unresolved_point_fails_the_check_naming_the_filler_and_the_fix(
    project: AdopterRepo, tmp_path: Path
) -> None:
    _contribute(project, [STALE_GUIDE], version=2)
    run = _check(project, tmp_path, {"README.md": "# R 2\n"})
    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr.splitlines() == [
        f"[unresolved] the {POINT} point does not resolve: a filler meant to answer is inert, "
        "and the point's inert policy is `fail`. The check cannot see every obligation it "
        "should, so it fails rather than pass on fewer (DEC-053).",
        f"  inert: {DOCS_CAP} (value): it targets version 2; the point is at version 1",
        f"  fix: update {DOCS_CAP}, pin it, or uninstall it.",
    ]


# What uv prints when the offline run misses its cache (uv 0.9.30, verbatim; the
# query policy's reading of it is pinned in `test_provisioning.py`).
_UV_OFFLINE_MISS = (
    "  × No solution found when resolving script dependencies:\n"
    "  ╰─▶ Because ruamel-yaml was not found in the cache and you require\n"
    "      ruamel-yaml>=0.18, we can conclude that your requirements are\n"
    "      unsatisfiable.\n\n"
    "      hint: Packages were unavailable because the network was disabled. When\n"
    "      the network is disabled, registry packages may only be read from the\n"
    "      cache.\n"
)


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        # The likeliest real failure: its dependency not provisioned for the offline run.
        (
            f"sys.stderr.buffer.write({_UV_OFFLINE_MISS.encode()!r})\nsys.exit(1)\n",
            "command 'fill-doc-check': environment not provisioned — run `pkit sync` (its "
            "dependencies are not in uv's cache, and a query runs offline)",
        ),
        ("sys.exit(3)\n", "command 'fill-doc-check' exited 3"),
    ],
)
def test_the_mapping_s_own_filler_giving_no_answer_fails_the_check(
    project: AdopterRepo, tmp_path: Path, body: str, reason: str
) -> None:
    """No answer ends the same way whatever the cause: the point unresolved,
    never a pass on no obligations. The reason says which cause it was — an
    environment not provisioned names `pkit sync` — and the fix names the
    filler's own verb."""
    _pm_file(project, "scripts/fill-doc-check.py").write_text(
        f"#!{sys.executable}\nimport sys\n{body}", encoding="utf-8"
    )
    run = _check(project, tmp_path, {"src/a.py": "a\n"})
    assert (run.returncode, run.stdout) == (1, "")
    lines = run.stderr.splitlines()
    assert lines[1] == f"  inert: {PM} (command 'fill-doc-check'): {reason}"
    assert lines[2] == (
        "  fix: run `pkit pm fill-doc-check` to see why it gives no answer; when its "
        "environment is not provisioned, `pkit sync` provisions it for the offline run."
    )


def test_a_contributor_claiming_the_mapping_source_fails_the_check(
    project: AdopterRepo, tmp_path: Path
) -> None:
    (claimed,) = doc_check.mapping_obligations([{"code": "docs/**", "docs": ["x.md"]}])
    _contribute(project, [claimed])
    run = _check(project, tmp_path, {"README.md": "# R 2\n"})
    assert run.returncode == 1
    assert "entry 'mapping:docs/**' from docs-test claims the `mapping` source" in run.stderr


def test_a_removal_override_takes_an_obligation_out_and_is_printed(
    project: AdopterRepo, tmp_path: Path
) -> None:
    project.write(
        {
            FILLER_FILE: json.dumps(
                {
                    "schema_version": 1,
                    "value": [],
                    "remove": [{"id": "mapping:src/**", "reason": "README tracks src by hand."}],
                }
            )
        }
    )
    run = _check(project, tmp_path, {"src/a.py": "a\n"})
    assert (run.returncode, run.stderr) == (0, "")
    assert run.stdout == (
        "check-doc-mapping: 2 rule(s), 1 changed file(s), mode=advisory\n"
        "  − mapping:src/** → removed by the project filler: README tracks src by hand.\n"
        "check-doc-mapping: all touched mappings satisfied.\n"
    )
