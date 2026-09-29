"""check-doc-mapping's whole run, pinned byte for byte on fixtures (DEC-015, DEC-053).

`test_pm_check_doc_mapping.py` pins the matcher and the section parser; this
file pins what the script prints and how it exits, end to end: a real git
repository with a base and a head, a staged capability root holding the
mapping, a pull-request body file. Each fixture's standard output, standard
error and exit code are written out literally below, so the mapping check's
behaviour for a project without a documentation capability cannot change
without this file changing with it.

The script runs as a subprocess under this interpreter, from the fixture
repository, with `--capability-root` and `--pr-body-file` always given — so no
`gh` is reached and no real project is read.

Since the check reads its obligations from the resolved doc-check point
(DEC-053) through `pkit connections resolve`, a `pkit` stand-in on PATH answers
that read: it runs the real default filler, `fill-doc-check.py --json`, over the
fixture's capability root and wraps its envelope as the backbone resolves an
additive point with one filler — the mapping's obligations, in order, each
from project-management. The expected outcomes were captured before the check
read the point, and are unchanged.

The last fixture is the merge gate under the setting project-kit runs with
(#1012): the friction source enforcing, in an adopter with living-docs and
project-management installed, the point resolved by the real `pkit` — a
pull request with a stale page and unanchored code is refused naming both, and
passes once the page is revalidated and the path anchored.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import document as friction_document

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT = CAPABILITY / "scripts" / "check-doc-mapping.py"
FILLER = CAPABILITY / "scripts" / "fill-doc-check.py"

# The `pkit` stand-in: `pkit connections resolve <point> --json` from the default
# filler's real envelope. Records its argv; anything else it is asked fails.
PKIT_STANDIN = """\
import json, subprocess, sys
log, filler, capability = sys.argv[1:4]
argv = sys.argv[4:]
with open(log, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(argv) + "\\n")
if argv != ["connections", "resolve", "pkit::work-tracking:doc-check", "--json"]:
    sys.exit(f"unexpected pkit call: {argv}")
run = subprocess.run(
    [sys.executable, filler, "--json", "--capability-root", capability],
    capture_output=True, text=True, check=True,
)
obligations = json.loads(run.stdout)["value"]
print(json.dumps({
    "address": "pkit::work-tracking:doc-check", "defined": True,
    "provider": "project-management", "policy": "additive", "inert_policy": "fail",
    "participation": None, "resolved": True, "why": "", "value": obligations, "origin": "",
    "entries": [
        {"id": o["id"], "origin": "project-management", "replaces": [], "value": o}
        for o in obligations
    ],
    "removals": [],
    "fillers": [{"source": "contribution", "name": "project-management",
                 "supplies": "command 'fill-doc-check'", "state": "taken", "reason": "",
                 "query_contract": True}],
}))
"""

BASE_FILES = {
    "src/app.py": "print('app')\n",
    "src/util.py": "print('util')\n",
    "lib/core.py": "core = 1\n",
    "tools/build.sh": "echo build\n",
    "old/gone.py": "gone = 1\n",
    "README.md": "# Readme\n",
    "docs/api.md": "# API\n",
    "docs/lib.md": "# Lib\n",
    "docs/tools.md": "# Tools\n",
}

RULES = """\
code_path_to_doc_mapping:
  enforce: {enforce}
  rules:
    - {{ code: "src/**", docs: [README.md] }}
    - {{ code: "lib/**", docs: [docs/lib.md, docs/api.md] }}
    - {{ code: "tools/**", docs: [docs/tools.md] }}
    - {{ code: "old/**", docs: [docs/old.md] }}
    - {{ code: "src/**", docs: [docs/api.md] }}
    - {{ code: "never/**", docs: [docs/never.md] }}
"""


@dataclass(frozen=True)
class Fixture:
    """One run: the mapping block, what the head changes, the PR body."""

    mapping: str
    changes: dict[str, str] = field(default_factory=dict)
    deletions: tuple[str, ...] = ()
    body: str = ""


@dataclass(frozen=True)
class Outcome:
    code: int
    out: str
    err: str


# --- staging -----------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _write(root: Path, files: dict[str, str]) -> None:
    for relpath, text in files.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _stage_repo(tmp_path: Path, fixture: Fixture) -> Path:
    """A repository whose branch `base` holds BASE_FILES and whose HEAD adds the
    fixture's changes and deletions on top."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.name", "pkit-test")
    _git(repo, "config", "user.email", "pkit-test@example.com")
    _git(repo, "config", "commit.gpgsign", "false")
    _write(repo, BASE_FILES)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "branch", "base")
    _write(repo, fixture.changes)
    for relpath in fixture.deletions:
        (repo / relpath).unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "head")
    return repo


def _stage_capability(tmp_path: Path, mapping: str) -> Path:
    """A bootstrapped capability root outside the repository (so it is not part
    of the diff): the companion config schema, a config carrying `mapping`, and
    an unbound bootstrap stamp."""
    cap = tmp_path / "capability"
    (cap / "schemas").mkdir(parents=True)
    (cap / "schemas" / "config.schema.json").write_text(
        (CAPABILITY / "schemas" / "config.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (cap / "project").mkdir()
    (cap / "project" / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: []\n" + mapping,
        encoding="utf-8",
    )
    (cap / "project" / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )
    return cap


def _stage_pkit(tmp_path: Path, cap: Path) -> Path:
    """A directory holding the `pkit` stand-in, to put first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pkit-standin.py").write_text(PKIT_STANDIN, encoding="utf-8")
    pkit = bin_dir / "pkit"
    pkit.write_text(
        "#!/bin/sh\n"
        f'exec "{sys.executable}" "{bin_dir / "pkit-standin.py"}" '
        f'"{tmp_path / "pkit-calls.log"}" "{FILLER}" "{cap}" "$@"\n',
        encoding="utf-8",
    )
    pkit.chmod(0o755)
    return bin_dir


def pkit_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "pkit-calls.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def run_fixture(tmp_path: Path, fixture: Fixture) -> Outcome:
    repo = _stage_repo(tmp_path, fixture)
    cap = _stage_capability(tmp_path, fixture.mapping)
    bin_dir = _stage_pkit(tmp_path, cap)
    body = tmp_path / "body.md"
    body.write_text(fixture.body, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--base",
            "base",
            "--pr-body-file",
            str(body),
            "--capability-root",
            str(cap),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "NO_COLOR": "1",
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        },
        check=False,
    )
    return Outcome(proc.returncode, proc.stdout, proc.stderr)


# --- the fixtures and what each prints -----------------------------------------

TOUCHING = {
    "src/app.py": "print('app 2')\n",
    "lib/core.py": "core = 2\n",
    "docs/api.md": "# API 2\n",
    "tools/build.sh": "echo build 2\n",
}

FIXTURES: dict[str, Fixture] = {
    "no-mapping": Fixture(mapping="", changes={"src/app.py": "x\n"}),
    "no-rules": Fixture(
        mapping="code_path_to_doc_mapping:\n  enforce: true\n  rules: []\n",
        changes={"src/app.py": "x\n"},
    ),
    "mapping-not-a-mapping": Fixture(
        mapping="code_path_to_doc_mapping: [src/**]\n", changes={"src/app.py": "x\n"}
    ),
    "advisory-mixed": Fixture(
        mapping=RULES.format(enforce="false"),
        changes=TOUCHING,
        deletions=("old/gone.py",),
        body="## Summary\nx\n\n## Doc impact\n- tools/build.sh: internal only\n\n## Test plan\n",
    ),
    "enforce-mixed": Fixture(
        mapping=RULES.format(enforce="true"),
        changes=TOUCHING,
        deletions=("old/gone.py",),
        body="## Summary\nx\n\n## Doc impact\n- tools/build.sh: internal only\n",
    ),
    "enforce-override-by-glob": Fixture(
        mapping=RULES.format(enforce="true"),
        changes={"src/util.py": "u\n", "docs/api.md": "# API 3\n"},
        body="## Doc impact\nNo doc impact: SRC/** is internal plumbing\n",
    ),
    "enforce-no-doc-impact-line-meets-nothing": Fixture(
        mapping=RULES.format(enforce="true"),
        changes={"src/util.py": "u\n"},
        body="## Doc impact\nNo doc impact: internal refactor only.\n",
    ),
    "enforce-all-satisfied": Fixture(
        mapping=RULES.format(enforce="true"),
        changes={"src/app.py": "a\n", "README.md": "# R\n", "docs/api.md": "# A\n"},
    ),
    "untouched": Fixture(
        mapping=RULES.format(enforce="true"), changes={"unmapped/x.txt": "x\n"}
    ),
    "malformed-rules-are-skipped": Fixture(
        mapping=(
            "code_path_to_doc_mapping:\n"
            "  enforce: true\n"
            "  rules:\n"
            "    - just-a-string\n"
            "    - { code: 'src/**' }\n"
            "    - { docs: [README.md] }\n"
            "    - { code: 'lib/**', docs: [docs/lib.md] }\n"
        ),
        changes={"src/app.py": "x\n", "lib/core.py": "y\n"},
    ),
}

EXPECTED: dict[str, Outcome] = {
    "no-mapping": Outcome(0, "check-doc-mapping: no rules configured; skipped.\n", ""),
    "no-rules": Outcome(0, "check-doc-mapping: no rules configured; skipped.\n", ""),
    "mapping-not-a-mapping": Outcome(
        2,
        "",
        "error: code_path_to_doc_mapping must be a mapping with `enforce:` and "
        "`rules:` (per ADR-019).\n",
    ),
    "advisory-mixed": Outcome(
        0,
        "check-doc-mapping: 6 rule(s), 4 changed file(s), mode=advisory\n"
        "  ✗ src/** → README.md (not updated; e.g. src/app.py)\n"
        "  ✓ lib/** → doc updated\n"
        "  ⊘ tools/** → overridden via `## Doc impact` (audited)\n"
        "  ✓ src/** → doc updated\n",
        "\n[advisory] 1 mapping(s) would fire under enforce: true. Set "
        "code_path_to_doc_mapping.enforce: true (with surgical rules) to block.\n",
    ),
    "enforce-mixed": Outcome(
        1,
        "check-doc-mapping: 6 rule(s), 4 changed file(s), mode=enforce\n"
        "  ✗ src/** → README.md (not updated; e.g. src/app.py)\n"
        "  ✓ lib/** → doc updated\n"
        "  ⊘ tools/** → overridden via `## Doc impact` (audited)\n"
        "  ✓ src/** → doc updated\n",
        "\n[refused] 1 mapping(s) unsatisfied — update the mapped doc(s), or add a "
        "`## Doc impact` line naming the code path.\n",
    ),
    "enforce-override-by-glob": Outcome(
        0,
        "check-doc-mapping: 6 rule(s), 2 changed file(s), mode=enforce\n"
        "  ⊘ src/** → overridden via `## Doc impact` (audited)\n"
        "  ✓ src/** → doc updated\n"
        "check-doc-mapping: all touched mappings satisfied.\n",
        "",
    ),
    "enforce-no-doc-impact-line-meets-nothing": Outcome(
        1,
        "check-doc-mapping: 6 rule(s), 1 changed file(s), mode=enforce\n"
        "  ✗ src/** → README.md (not updated; e.g. src/util.py)\n"
        "  ✗ src/** → docs/api.md (not updated; e.g. src/util.py)\n",
        "\n[refused] 2 mapping(s) unsatisfied — update the mapped doc(s), or add a "
        "`## Doc impact` line naming the code path.\n",
    ),
    "enforce-all-satisfied": Outcome(
        0,
        "check-doc-mapping: 6 rule(s), 3 changed file(s), mode=enforce\n"
        "  ✓ src/** → doc updated\n"
        "  ✓ src/** → doc updated\n"
        "check-doc-mapping: all touched mappings satisfied.\n",
        "",
    ),
    "untouched": Outcome(
        0,
        "check-doc-mapping: 6 rule(s), 1 changed file(s), mode=enforce\n"
        "check-doc-mapping: all touched mappings satisfied.\n",
        "",
    ),
    "malformed-rules-are-skipped": Outcome(
        1,
        "check-doc-mapping: 4 rule(s), 2 changed file(s), mode=enforce\n"
        "  ✗ lib/** → docs/lib.md (not updated; e.g. lib/core.py)\n",
        "\n[refused] 1 mapping(s) unsatisfied — update the mapped doc(s), or add a "
        "`## Doc impact` line naming the code path.\n",
    ),
}


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_the_mapping_check_prints_exactly_what_it_did(tmp_path: Path, name: str) -> None:
    assert run_fixture(tmp_path, FIXTURES[name]) == EXPECTED[name]


@pytest.mark.parametrize("name", sorted(set(FIXTURES) - {"mapping-not-a-mapping"}))
def test_the_rules_it_applies_are_the_ones_the_point_resolves_to(
    tmp_path: Path, name: str
) -> None:
    """The same bytes, and they came through the point: the check read it once.
    (A malformed mapping is refused before the point is read, as before.)"""
    run_fixture(tmp_path, FIXTURES[name])
    assert pkit_calls(tmp_path) == [
        '["connections", "resolve", "pkit::work-tracking:doc-check", "--json"]'
    ]


def test_every_fixture_has_its_expected_outcome() -> None:
    assert set(FIXTURES) == set(EXPECTED)


# --- a documentation capability's obligations, enforced (#1012) ------------------
#
# The setting project-kit runs with: `doc_check.sources.friction: enforcing`.
# The point here is the real one — an adopter with living-docs and
# project-management installed, the backbone resolving the point, living-docs'
# filler reading the whole-repository friction check at the branch's head — so
# the obligations are the ones a stale page and unanchored code give rise to.

LIVING_DOCS_REL = Path(".pkit") / "capabilities" / "living-docs"
PM_REL = Path(".pkit") / "capabilities" / "project-management"

BACKBONE_CONFIG = {
    "name": "adopter",
    "docs": {"user": "docs/", "internal": "tech-docs/"},
    "friction": {"mode": "enforcing", "surface": ["src"]},
}

PM_CONFIG = (
    "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"
    "code_path_to_doc_mapping:\n  enforce: false\n  rules: []\n"
    "doc_check:\n  sources:\n    friction: enforcing\n"
)

# A line naming each obligation, which meets neither: a contributed obligation
# is met on the page, never by the section.
DOC_IMPACT = "## Doc impact\n- docs/guide.md: still accurate\n- src/b.py: an internal helper\n"


def _guide(*anchors: str, body: str) -> str:
    return friction_document(
        None,
        anchors={"path": list(anchors)},
        at="2026-10-01T09:00:00Z",
        outcome="updated",
        reader="user",
        kind="signpost",
        body=body,
    )


def _to_this_interpreter(repo: AdopterRepo, script: Path) -> None:
    """A capability script run under this interpreter, not `uv run --script`."""
    path = repo.root / script
    body = path.read_text(encoding="utf-8").split("\n", 1)[1]
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")


@pytest.fixture
def enforcing_project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """The adopter at its base: `src/a.py`, and the user page describing it."""
    repo = make_adopter_repo(capabilities=("living-docs", "project-management"))
    for script in (LIVING_DOCS_REL, PM_REL):
        _to_this_interpreter(repo, script / "scripts" / "fill-doc-check.py")
    repo.write(
        {
            ".pkit/project/config.yaml": json.dumps(BACKBONE_CONFIG, indent=2) + "\n",
            f"{PM_REL}/project/config.yaml": PM_CONFIG,
            f"{PM_REL}/project/bootstrap-stamp.yaml": (
                "schema_version: 1\n"
                "bootstrap:\n"
                "  completed_at: '2026-01-01T00:00:00+00:00'\n"
                "  capability_version: 0.0.0-test\n"
                "  by: bootstrap\n"
                "  repo:\n"
            ),
            "src/a.py": "A = 1\n",
            "docs/guide.md": _guide("src/a.py", body="`src/a.py` holds A, set to 1."),
            "tech-docs/README.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# Notes\n",
        }
    )
    repo.commit("base")
    repo.git("branch", "base")
    return repo


def _merge_gate(repo: AdopterRepo, tmp_path: Path) -> Outcome:
    """check-doc-mapping on the branch against `base`, as the gate's `doc check`
    line runs it (`scripts/check.sh`, a required status)."""
    body = tmp_path / "body.md"
    body.write_text(DOC_IMPACT, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PKIT_OFFLINE"}
    proc = subprocess.run(
        [
            sys.executable,
            str(repo.root / PM_REL / "scripts" / "check-doc-mapping.py"),
            "--base",
            "base",
            "--pr-body-file",
            str(body),
        ],
        cwd=repo.root,
        capture_output=True,
        text=True,
        env={**env, "NO_COLOR": "1"},
        check=False,
    )
    return Outcome(proc.returncode, proc.stdout, proc.stderr)


def test_the_merge_gate_refuses_unmet_contributed_obligations_until_they_are_met(
    enforcing_project: AdopterRepo, tmp_path: Path
) -> None:
    """One branch in two states. It changes code a page anchors without answering
    on the page, and adds code nothing anchors: the check refuses, naming both.
    Revalidating the page — with the writer a contributor runs — and anchoring
    the new path from it leaves no obligation, and the check passes."""
    repo = enforcing_project
    repo.commit("change a, add b", {"src/a.py": "A = 2\n", "src/b.py": "B = 1\n"})
    assert _merge_gate(repo, tmp_path) == Outcome(
        1,
        "check-doc-mapping: 0 rule(s), 2 changed file(s), mode=advisory\n"
        "check-doc-mapping: 2 contributed obligation(s) from friction\n"
        "  ✗ [friction] docs/guide.md → no answer in the diff (page-stale)\n"
        "  ✗ [friction] src/b.py → no page anchors it (code-undocumented); "
        "anchor `src/b.py` from a page\n",
        "\n[refused] 1 friction obligation(s) unanswered — answer each on its page in this "
        "diff; a `## Doc impact` line does not meet them.\n"
        "\n[refused] 1 friction obligation(s) unanchored — anchor each path from a page; "
        "a `## Doc impact` line does not meet them.\n",
    )

    repo.write(
        {
            "docs/guide.md": _guide(
                "src/a.py", "src/b.py", body="`src/a.py` holds A, set to 2; `src/b.py` holds B."
            )
        }
    )
    revalidated = CliRunner().invoke(
        main, ["friction", "revalidate", "docs/guide.md", "--outcome", "updated", "--yes"]
    )
    assert revalidated.exit_code == 0, revalidated.output
    repo.commit("describe a and b")
    assert _merge_gate(repo, tmp_path) == Outcome(
        0, "check-doc-mapping: no rules configured; skipped.\n", ""
    )
