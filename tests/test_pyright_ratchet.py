"""The type-checking gate, `scripts/pyright_ratchet.py` (PRJ-010).

Each behaviour runs against a fixture repository — a small package under `src/`,
its tests, a lock, `pyproject.toml`'s `[tool.pyright]` table and a baseline,
committed on `main` with the work on a branch — and a stand-in for pyright that
reports the findings a test names, so pyright itself never runs here. Only the
last test reads the installed pyright, to keep the gate's copy of one of its
rules in step with it.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import subprocess
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from scripts import pyright_ratchet as ratchet

PYRIGHT_TABLE = """\
[tool.pyright]
include = ["src", "tests"]
strict = ["src"]
typeCheckingMode = "standard"
enableTypeIgnoreComments = false
"""

PYPROJECT = f"""\
[project]
name = "fixture"

[tool.ruff]
line-length = 100

{PYRIGHT_TABLE}"""

A = "src/pkg/a.py"
B = "src/pkg/b.py"
TEST = "tests/test_a.py"
X = "reportUnknownMemberType"
Y = "reportUnknownVariableType"


@dataclass(frozen=True)
class Reported:
    """One finding the stand-in for pyright reports."""

    path: str
    rule: str | None = X
    line: int = 1
    severity: str = "error"
    message: str = "a finding"


def report(root: Path, findings: Iterable[Reported]) -> dict[str, Any]:
    """A `pyright --outputjson` report of `findings` under `root`."""
    diagnostics: list[dict[str, Any]] = []
    for f in findings:
        raw: dict[str, Any] = {
            "file": str(root / f.path),
            "severity": f.severity,
            "message": f.message,
            "range": {
                "start": {"line": f.line - 1, "character": 4},
                "end": {"line": f.line - 1, "character": 9},
            },
        }
        if f.rule is not None:
            raw["rule"] = f.rule
        diagnostics.append(raw)
    return {"version": "1.1.409", "generalDiagnostics": diagnostics}


def many(path: str, rule: str, n: int) -> list[Reported]:
    return [Reported(path, rule, line=i + 1) for i in range(n)]


class Tree:
    """The fixture repository, and the gate run over it."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def git(self, *args: str) -> str:
        done = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        return done.stdout

    def write(self, files: Mapping[str, str]) -> None:
        for path, text in files.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    def baseline(self, counts: Mapping[tuple[str, str], int]) -> None:
        self.write({ratchet.BASELINE: ratchet.render_baseline(counts)})

    def read_baseline(self) -> str:
        return (self.root / ratchet.BASELINE).read_text(encoding="utf-8")

    def commit(self, message: str = "change") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def run(self, command: str = "check", findings: Iterable[Reported] = ()) -> tuple[int, str]:
        reported = report(self.root, findings)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = ratchet.main([command], root=self.root, pyright=lambda _root: reported)
        return code, out.getvalue()


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Tree:
    """`main` carries the package, its tests, the lock, the configuration and a baseline
    of 2 findings in `a.py` under X; the work goes on the branch `topic`."""
    made = Tree(tmp_path / "repo")
    made.root.mkdir()
    made.git("init", "-q", "-b", "main")
    made.write(
        {
            "pyproject.toml": PYPROJECT,
            "uv.lock": "version = 1\n",
            "src/pkg/__init__.py": "",
            A: "A = 1\n",
            B: "B = 1\n",
            TEST: "def test_a() -> None:\n    assert True\n",
        }
    )
    made.baseline({(A, X): 2})
    made.commit("initial")
    made.git("switch", "-q", "-c", "topic")
    monkeypatch.setenv("PKIT_CHECK_BASE", "main")
    return made


# --- the package, counted per file and rule (point 3) ---------------------------------------


def test_the_counts_the_baseline_admits_pass(tree: Tree) -> None:
    code, out = tree.run(findings=many(A, X, 2))

    assert code == 0, out
    assert "pyright ratchet: ok" in out
    assert "lower" not in out


def test_a_count_above_its_entry_fails_with_the_findings_listed(tree: Tree) -> None:
    code, out = tree.run(findings=[*many(A, X, 2), Reported(A, X, line=40, message="new")])

    assert code == 1
    assert f"{A} {X}: 3, the baseline admits 2" in out
    assert f"{A}:40:5: error: new ({X})" in out
    assert "pyright ratchet: FAILED" in out


def test_a_finding_in_a_file_the_baseline_does_not_list_fails(tree: Tree) -> None:
    code, out = tree.run(findings=[*many(A, X, 2), Reported("src/pkg/new.py", X)])

    assert code == 1
    assert f"src/pkg/new.py {X}: 1, the baseline admits 0" in out


def test_a_fix_under_one_rule_does_not_pay_for_a_finding_under_another(tree: Tree) -> None:
    code, out = tree.run(findings=[Reported(A, X), Reported(A, Y)])

    assert code == 1
    assert f"{A} {Y}: 1, the baseline admits 0" in out


def test_a_count_below_its_entry_passes_and_names_the_entry_to_lower(tree: Tree) -> None:
    code, out = tree.run(findings=many(A, X, 1))

    assert code == 0, out
    assert f"{A} {X}: 1, the baseline admits 2" in out
    assert ratchet.LOWER_COMMAND in out


def test_warnings_count_and_information_does_not(tree: Tree) -> None:
    findings = [
        *many(A, X, 2),
        Reported(A, X, line=9, severity="information"),
        Reported(B, Y, severity="warning"),
    ]
    code, out = tree.run(findings=findings)

    assert code == 1
    assert f"{B} {Y}: 1, the baseline admits 0" in out
    assert f"{A} {X}" not in out


def test_a_missing_baseline_fails_closed(tree: Tree) -> None:
    (tree.root / ratchet.BASELINE).unlink()

    code, out = tree.run()

    assert code == 1
    assert "there is no baseline" in out


@pytest.mark.parametrize(
    "line",
    [
        f"{A} {X}",
        f"{A} {X} two",
        f"{A} {X} 0",
        f"tests/test_a.py {X} 1",
        f"{A} not-a-rule 1",
    ],
    ids=["two-fields", "not-a-count", "zero", "outside-the-package", "not-a-rule"],
)
def test_a_malformed_baseline_fails(tree: Tree, line: str) -> None:
    tree.write({ratchet.BASELINE: f"# a comment\n{line}\n"})

    code, out = tree.run()

    assert code == 1
    assert f"{ratchet.BASELINE} line 2" in out


def test_an_entry_listed_twice_fails(tree: Tree) -> None:
    tree.write({ratchet.BASELINE: f"{A} {X} 1\n{A} {X} 2\n"})

    code, out = tree.run()

    assert code == 1
    assert "listed twice" in out


# --- everything else, gated outright (point 2) ----------------------------------------------


def test_any_finding_outside_the_package_fails(tree: Tree) -> None:
    code, out = tree.run(findings=[*many(A, X, 2), Reported(TEST, "reportArgumentType", 3)])

    assert code == 1
    assert f"{TEST}:3:5: error: a finding (reportArgumentType)" in out
    assert "gated outright" in out


def test_a_finding_under_no_rule_counts(tree: Tree) -> None:
    code, out = tree.run(findings=[*many(A, X, 2), Reported(B, None)])

    assert code == 1
    assert f"{B} {ratchet.NO_RULE}: 1, the baseline admits 0" in out


# --- running pyright ------------------------------------------------------------------------


def test_pyright_runs_on_this_interpreter_without_a_version_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(argv=argv, env=kwargs["env"], cwd=kwargs["cwd"])
        return subprocess.CompletedProcess(argv, 1, stdout='{"generalDiagnostics": []}')

    monkeypatch.setenv("PYRIGHT_PYTHON_FORCE_VERSION", "latest")
    monkeypatch.setattr(ratchet.subprocess, "run", fake_run)

    assert ratchet.run_pyright(tmp_path) == {"generalDiagnostics": []}
    assert seen["argv"][1:4] == ["-m", "pyright", "--outputjson"]
    assert seen["argv"][-2:] == ["--pythonpath", seen["argv"][0]]
    assert "PYRIGHT_PYTHON_FORCE_VERSION" not in seen["env"]
    assert seen["cwd"] == tmp_path


@pytest.mark.parametrize(
    ("status", "stdout"),
    [(2, ""), (3, "config error"), (1, "not json")],
    ids=["fatal", "configuration", "no-report"],
)
def test_pyright_that_does_not_check_the_tree_fails_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int, stdout: str
) -> None:
    monkeypatch.setattr(
        ratchet.subprocess,
        "run",
        lambda argv, **_: subprocess.CompletedProcess(argv, status, stdout=stdout, stderr=""),
    )

    with pytest.raises(ratchet.RatchetError):
        ratchet.run_pyright(tmp_path)


def test_a_report_the_gate_cannot_read_fails_it(tree: Tree) -> None:
    def broken(_root: Path) -> dict[str, Any]:
        raise ratchet.RatchetError("pyright exited 2: boom")

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = ratchet.main([], root=tree.root, pyright=broken)

    assert code == 1
    assert "pyright exited 2: boom" in out.getvalue()


# --- lowering (points 4 and 6) --------------------------------------------------------------


def test_lower_lowers_counts_and_drops_entries_with_no_finding(tree: Tree) -> None:
    tree.baseline({(A, X): 3, (B, Y): 2})
    tree.commit()

    code, out = tree.run("lower", findings=many(A, X, 1))

    assert code == 0, out
    assert ratchet.parse_baseline(tree.read_baseline()) == {(A, X): 1}
    assert f"{A} {X}: 3 -> 1" in out
    assert f"{B} {Y}: 2 -> gone" in out
    assert tree.run(findings=many(A, X, 1))[0] == 0


def test_lower_never_raises_a_count_or_adds_an_entry(tree: Tree) -> None:
    before = tree.read_baseline()

    code, out = tree.run("lower", findings=[*many(A, X, 3), Reported(B, Y)])

    assert code == 1
    assert "not lowering" in out
    assert tree.read_baseline() == before


def test_lowered_keeps_each_count_at_or_below_its_entry() -> None:
    baseline = {(A, X): 2, (B, Y): 4}
    current = {(A, X): 5, (B, Y): 1, ("src/pkg/c.py", X): 3}

    assert ratchet.lowered(baseline, current) == {(A, X): 2, (B, Y): 1}


def test_lower_says_when_there_is_nothing_to_lower(tree: Tree) -> None:
    code, out = tree.run("lower", findings=many(A, X, 2))

    assert code == 0
    assert "already as low" in out


@pytest.mark.parametrize(
    ("files", "named"),
    [
        ({A: "A = 2\n"}, A),
        ({"src/pkg/new.py": "N = 1\n"}, "src/pkg/new.py"),
        ({"uv.lock": "version = 2\n"}, "uv.lock"),
        (
            {"pyproject.toml": PYPROJECT.replace('"standard"', '"basic"')},
            "pyproject.toml [tool.pyright]",
        ),
    ],
    ids=["a-changed-module", "a-new-module", "the-lock", "the-pyright-table"],
)
def test_lower_refuses_while_what_the_counts_rest_on_differs_from_the_commit(
    tree: Tree, files: Mapping[str, str], named: str
) -> None:
    before = tree.read_baseline()
    tree.write(files)

    code, out = tree.run("lower", findings=many(A, X, 1))

    assert code == 1
    assert "commit them first" in out
    assert f"  {named}" in out
    assert tree.read_baseline() == before


def test_lower_runs_while_pyproject_differs_outside_the_pyright_table(tree: Tree) -> None:
    tree.write({"pyproject.toml": PYPROJECT.replace("line-length = 100", "line-length = 90")})

    code, out = tree.run("lower", findings=many(A, X, 1))

    assert code == 0, out
    assert ratchet.parse_baseline(tree.read_baseline()) == {(A, X): 1}


def test_measure_prints_the_counts_in_the_baseline_form_and_writes_nothing(tree: Tree) -> None:
    before = tree.read_baseline()

    code, out = tree.run("measure", findings=[*many(A, X, 4), Reported(B, Y), Reported(TEST)])

    assert code == 0
    assert ratchet.parse_baseline(out) == {(A, X): 4, (B, Y): 1}
    assert out.startswith(ratchet.BASELINE_HEADER)
    assert tree.read_baseline() == before


# --- the guard on the baseline's totals (point 4) -------------------------------------------


def test_a_rule_total_rising_against_the_base_fails(tree: Tree) -> None:
    tree.baseline({(A, X): 3})
    tree.commit()

    code, out = tree.run(findings=many(A, X, 3))

    assert code == 1
    assert "totals rose against main" in out
    assert f"{X}: 2 -> 3" in out


def test_a_move_between_files_keeps_every_total_and_passes(tree: Tree) -> None:
    tree.baseline({(A, X): 1, (B, X): 1})
    tree.commit()

    code, out = tree.run(findings=[Reported(A, X), Reported(B, X)])

    assert code == 0, out


@pytest.mark.parametrize(
    "files",
    [
        {"uv.lock": "version = 2\n"},
        {"pyproject.toml": PYPROJECT.replace('"standard"', '"basic"')},
    ],
    ids=["the-lock", "the-pyright-table"],
)
def test_a_rise_passes_when_the_change_alters_the_lock_or_the_configuration(
    tree: Tree, files: Mapping[str, str]
) -> None:
    tree.baseline({(A, X): 3})
    tree.write(files)
    tree.commit()

    code, out = tree.run(findings=many(A, X, 3))

    assert code == 0, out
    assert "Say in the pull request why the counts rose" in out


def test_the_guard_reads_where_the_change_left_the_base(tree: Tree) -> None:
    tree.git("switch", "-q", "main")
    tree.baseline({(A, X): 1})
    tree.commit("main lowers the baseline after the branch left it")
    tree.git("switch", "-q", "topic")

    code, out = tree.run(findings=many(A, X, 2))

    assert code == 0, out


def test_the_guard_passes_a_change_that_brings_the_baseline_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made = Tree(tmp_path / "repo")
    made.root.mkdir()
    made.git("init", "-q", "-b", "main")
    made.write({"pyproject.toml": PYPROJECT, A: "A = 1\n"})
    made.commit("initial")
    made.git("switch", "-q", "-c", "topic")
    made.baseline({(A, X): 2})
    made.commit()
    monkeypatch.setenv("PKIT_CHECK_BASE", "main")

    code, out = made.run(findings=many(A, X, 2))

    assert code == 0, out


def test_the_guard_fails_when_the_base_does_not_resolve(
    tree: Tree, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PKIT_CHECK_BASE", "no-such-branch")

    code, out = tree.run(findings=many(A, X, 2))

    assert code == 1
    assert "The baseline guard cannot run" in out


# --- suppressions and file comments (point 5) -----------------------------------------------


@pytest.mark.parametrize(
    "comment",
    [
        f"# pyright: ignore[{X}] the reason",
        "# pyright: ignore",
        "# type: ignore",
        "# type: ignore[arg-type]",
        "# noqa: E501  # type: ignore",
    ],
)
def test_the_package_carries_no_suppression(comment: str) -> None:
    problems = ratchet.comment_problems(f"x = f()  {comment}\n", package=True)

    assert [line for line, _ in problems] == [1]


@pytest.mark.parametrize(
    ("comment", "why"),
    [
        ("# pyright: ignore", "naming no rule"),
        ("# pyright: ignore[]", "naming no rule"),
        (f"# pyright: ignore[{X}]", "gives no reason"),
        (f"# pyright: ignore[{X}]   ", "gives no reason"),
        (f"# pyright: ignore[{X}] -- ", "gives no reason"),
        ("# type: ignore[arg-type]", "honours none"),
    ],
)
def test_a_test_suppression_names_its_rules_and_gives_its_reason(comment: str, why: str) -> None:
    problems = ratchet.comment_problems(f"x = f()  {comment}\n", package=False)

    assert len(problems) == 1
    assert why in problems[0][1]


@pytest.mark.parametrize(
    "comment",
    [
        f"# pyright: ignore[{X}] hands it a str on purpose",
        f"# pyright: ignore[{X}, {Y}] - the runtime check under test",
    ],
)
def test_a_test_suppression_with_its_rules_and_reason_passes(comment: str) -> None:
    assert ratchet.comment_problems(f"x = f()  {comment}\n", package=False) == []


@pytest.mark.parametrize("package", [True, False], ids=["package", "tests"])
@pytest.mark.parametrize(
    "comment",
    ["# pyright: basic", "# pyright: strict", f"#pyright: {X}=false", "# pyright: standard"],
)
def test_a_file_comment_setting_the_mode_or_a_severity_is_refused_everywhere(
    comment: str, package: bool
) -> None:
    problems = ratchet.comment_problems(f"{comment}\nx = 1\n", package=package)

    assert len(problems) == 1
    assert "file comment" in problems[0][1]


@pytest.mark.parametrize(
    "source",
    [
        'TEXT = "x = 1  # type: ignore"\n',
        'TEXT = """\n# pyright: basic\n"""\n',
        "# a `# pyright: ignore` would hide the line's findings\nx = 1\n",
        "# mentions pyright: ignorable, not a suppression\nx = 1\n",
    ],
    ids=["a-string", "a-docstring", "prose-in-a-comment", "a-longer-word"],
)
def test_text_pyright_does_not_read_as_a_suppression_is_not_refused(source: str) -> None:
    assert ratchet.comment_problems(source, package=True) == []


def test_the_gate_names_the_line_of_a_refused_comment(tree: Tree) -> None:
    tree.write({TEST: f"x = 1  # pyright: ignore[{X}]\n", A: "A = 1  # type: ignore\n"})

    code, out = tree.run(findings=many(A, X, 2))

    assert code == 1
    assert f"{TEST}:1: `# pyright: ignore[{X}]` gives no reason" in out
    assert f"{A}:1: a `# type: ignore`" in out


def test_files_the_configuration_leaves_out_are_not_read(tree: Tree) -> None:
    table = PYRIGHT_TABLE + 'exclude = ["tests/fixtures"]\n'
    tree.write(
        {
            "pyproject.toml": PYPROJECT.replace(PYRIGHT_TABLE, table),
            "tests/fixtures/sample.py": "# pyright: basic\n",
        }
    )

    assert "tests/fixtures/sample.py" not in ratchet.checked_files(
        tree.root, ratchet.read_configuration(tree.root)
    )
    code, out = tree.run(findings=many(A, X, 2))
    assert code == 0, out


# --- the configuration (point 5) ------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ('exclude = ["src/pkg"]', "`exclude` entry 'src/pkg' reaches into the package"),
        ('exclude = ["**/a.py"]', "`exclude` entry '**/a.py' reaches into the package"),
        ('ignore = ["src"]', "`ignore` entry 'src' reaches into the package"),
        ('strict = ["src/pkg/a.py"]', "the strict list does not cover"),
        ("strict = []", "the strict list does not cover"),
        ('include = ["tests"]', "`include` leaves"),
        ("enableTypeIgnoreComments = true", "`enableTypeIgnoreComments` is not false"),
        ('reportMissingModuleSource = "none"', "`reportMissingModuleSource` to 'none'"),
        ("reportMissingModuleSource = false", "`reportMissingModuleSource` to False"),
        (
            'reportMissingModuleSource = "information"',
            "`reportMissingModuleSource` to 'information'",
        ),
        (
            'executionEnvironments = [{ root = "src", reportMissingModuleSource = "none" }]',
            "the execution environment for 'src' sets `reportMissingModuleSource`",
        ),
    ],
)
def test_a_configuration_narrowing_the_package_fails(tree: Tree, change: str, why: str) -> None:
    key = change.split(" = ", 1)[0]
    kept = [line for line in PYRIGHT_TABLE.splitlines() if not line.startswith(f"{key} = ")]
    table = "\n".join([*kept, change]) + "\n"
    tree.write({"pyproject.toml": PYPROJECT.replace(PYRIGHT_TABLE, table)})

    code, out = tree.run(findings=many(A, X, 2))

    assert code == 1
    assert why in out


@pytest.mark.parametrize(
    "change",
    [
        'exclude = ["tests/fixtures"]',
        'ignore = ["tests/data"]',
        'reportMissingModuleSource = "warning"',
        'reportMissingModuleSource = "error"',
        f"{X} = false",
        'executionEnvironments = [{ root = "tests", reportMissingModuleSource = "none" }]',
    ],
)
def test_a_configuration_that_leaves_the_package_whole_passes(tree: Tree, change: str) -> None:
    table = PYRIGHT_TABLE + change + "\n"
    tree.write({"pyproject.toml": PYPROJECT.replace(PYRIGHT_TABLE, table)})

    code, out = tree.run(findings=many(A, X, 2))

    assert code == 0, out


def test_a_pyrightconfig_json_fails_the_gate(tree: Tree) -> None:
    tree.write({"pyrightconfig.json": "{}\n"})

    code, out = tree.run(findings=many(A, X, 2))

    assert code == 1
    assert "pyrightconfig.json would replace" in out


@pytest.mark.parametrize(
    ("pattern", "path", "reaches"),
    [
        ("src", "src/pkg/a.py", True),
        ("src/", "src/pkg/a.py", True),
        ("./src", "src/pkg/a.py", True),
        (".", "src/pkg/a.py", True),
        ("src/pkg/a.py", "src/pkg/a.py", True),
        ("**/a.py", "src/pkg/a.py", True),
        ("src/*/a.py", "src/pkg/a.py", True),
        ("src/*.py", "src/pkg/a.py", False),
        ("sr", "src/pkg/a.py", False),
        ("tests", "src/pkg/a.py", False),
        ("src/pkg/a", "src/pkg/a.py", False),
    ],
)
def test_a_path_pattern_reaches_what_lies_below_it(pattern: str, path: str, reaches: bool) -> None:
    assert ratchet.pattern_matches(pattern, path) is reaches


def test_the_rules_strict_does_not_override_are_the_installed_pyright_s() -> None:
    """The gate's copy of the rules strict mode leaves at the configured level, read from
    the pyright the lock pins. On a pyright upgrade that moves the function, re-read
    `getStrictModeNotOverriddenRules` and `getStrictDiagnosticRuleSet` by hand."""
    spec = importlib.util.find_spec("pyright")
    assert spec is not None and spec.origin is not None
    bundle = Path(spec.origin).parent / "dist" / "dist" / "pyright-internal.js"
    source = bundle.read_text(encoding="utf-8")

    listed = re.search(r"getStrictModeNotOverriddenRules=function\(\)\{return\[([^\]]*)\]", source)
    assert listed is not None, "pyright's bundle no longer reads as this test expects"
    rules = re.findall(r"DiagnosticRule\.(\w+)", listed.group(1))
    assert sorted(rules) == sorted(ratchet.NOT_OVERRIDDEN_BY_STRICT)
    for rule, level in ratchet.NOT_OVERRIDDEN_BY_STRICT.items():
        strict = re.search(r"getStrictDiagnosticRuleSet=function\(\)\{return\{(.*?)\}\}", source)
        assert strict is not None
        assert f'{rule}:"{level}"' in strict.group(1)


def test_the_baseline_form_round_trips() -> None:
    counts = {(B, X): 2, (A, Y): 1}
    text = ratchet.render_baseline(counts)

    assert text.splitlines()[-2:] == [f"{A} {Y} 1", f"{B} {X} 2"]
    assert ratchet.parse_baseline(text) == counts
    assert ratchet.rule_totals(counts) == Counter({X: 2, Y: 1})
