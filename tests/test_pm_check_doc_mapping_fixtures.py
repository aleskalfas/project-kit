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
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT = CAPABILITY / "scripts" / "check-doc-mapping.py"

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


def run_fixture(tmp_path: Path, fixture: Fixture) -> Outcome:
    repo = _stage_repo(tmp_path, fixture)
    cap = _stage_capability(tmp_path, fixture.mapping)
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
        env={**os.environ, "NO_COLOR": "1"},
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


def test_every_fixture_has_its_expected_outcome() -> None:
    assert set(FIXTURES) == set(EXPECTED)
