"""The type-checking gate (PRJ-010): pyright over the tree, the package through a ratchet.

pyright checks the package (`src/`) in strict mode and everything else it checks
in standard mode, as `pyproject.toml`'s `[tool.pyright]` table sets by directory.
This tool runs it once and judges both (points 2 and 3):

- outside the package, any finding fails: the tests are gated outright;
- in the package, the findings are counted per file and rule against the
  committed baseline, `scripts/pyright-baseline.txt`. A count above its entry,
  or a finding under no entry, fails with the findings listed; a count below
  passes, and the run names the entries to lower.

It refuses what would step around the count (point 5): any suppression in the
package; anywhere, a `# type: ignore` (pyright honours none), a
`# pyright: ignore` naming no rule and a file comment setting the mode or a
rule's severity; in the tests, a `# pyright: ignore[<rule>]` with no reason after
it on the line; and a configuration that narrows what the package is checked
for. And it guards the baseline (point 4): its package total for any rule may
not rise against the change's base unless the change alters the lock or
pyright's configuration. Warnings count as well as errors.

From the repository root:

    uv run python scripts/pyright_ratchet.py          # the gate (`check`)
    uv run python scripts/pyright_ratchet.py lower    # lower the baseline to the commit's counts
    uv run python scripts/pyright_ratchet.py measure  # print the counts in the baseline's form

`lower` writes only lower counts, never a higher one or a new entry, and refuses
while a package file, the lock or pyright's configuration differs from the
commit, so the counts it writes are counts the commit meets (point 6).
`measure` writes nothing: a raise is a hand edit, for moved code or an upgrade
only, with its reason in the pull request (CONTRIBUTING.md, "Running checks").
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tokenize
import tomllib
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from project_kit import default_branch

ROOT = Path(__file__).resolve().parents[1]

#: The package, checked in strict mode through the ratchet; every other file
#: pyright checks is gated outright.
PACKAGE = "src"
BASELINE = "scripts/pyright-baseline.txt"
LOCK = "uv.lock"
PYPROJECT = "pyproject.toml"
#: pyright reads this in place of `pyproject.toml`'s table when it exists.
PYRIGHTCONFIG = "pyrightconfig.json"

LOWER_COMMAND = "uv run python scripts/pyright_ratchet.py lower"

#: The severities that count: a rule set to warning still counts (point 5).
COUNTED_SEVERITIES = frozenset({"error", "warning"})
#: The rule a finding pyright reports under no rule is counted under.
NO_RULE = "-"
#: How many findings the gate prints for one file and rule.
SHOWN_PER_ENTRY = 20

#: The rules strict mode leaves at the configured level in a file it covers,
#: with the level strict sets: pyright's `getStrictModeNotOverriddenRules`. A
#: configuration could lower these in the package, so the gate refuses a level
#: below strict's. Strict raises every other rule to its own level.
NOT_OVERRIDDEN_BY_STRICT: Mapping[str, str] = {"reportMissingModuleSource": "warning"}
LEVELS: Mapping[str, int] = {"none": 0, "information": 1, "warning": 2, "error": 3}

#: The variables through which pyright's Python package runs a pyright other
#: than the one the lock pins; the gate runs the locked one (point 7).
PYRIGHT_VERSION_OVERRIDES = (
    "PYRIGHT_PYTHON_FORCE_VERSION",
    "PYRIGHT_PYTHON_PYLANCE_VERSION",
    "PYRIGHT_PYTHON_USE_BUNDLED_PYRIGHT",
)

#: The comments pyright reads as suppressions, as its tokenizer matches them in a
#: comment's text: at its start or after a `#` within it.
TYPE_IGNORE = re.compile(r"(?:^|#)\s*type:\s*ignore(?:\s*\[[\s\w:,-]*\]|\s|$)")
PYRIGHT_IGNORE = re.compile(r"(?:^|#)\s*pyright:\s*ignore(?:\s*\[(?P<rules>[\s\w,-]*)\]|\s|$)")
#: A reason holds at least one letter.
REASON = re.compile(r"[^\W\d_]")
RULE_NAME = re.compile(r"[A-Za-z]\w*")

BASELINE_HEADER = """\
# The package's strict-mode pyright findings the gate admits, as `<file> <rule> <count>`
# (PRJ-010; scripts/pyright_ratchet.py). A count above its line, or a finding under no
# line, fails the gate. `uv run python scripts/pyright_ratchet.py lower` lowers counts and
# never raises one; a raise is a hand edit, for moved code or an upgrade only, with its
# reason in the pull request (CONTRIBUTING.md, "Running checks").
"""

Key = tuple[str, str]
Report = Mapping[str, Any]
RunPyright = Callable[[Path], Report]


class RatchetError(Exception):
    """A part of the gate cannot run: pyright failed, a file is unreadable, no base."""


@dataclass(frozen=True)
class Finding:
    path: str  # relative to the root, `/`-separated
    rule: str
    line: int
    column: int
    severity: str
    message: str

    @property
    def key(self) -> Key:
        return (self.path, self.rule)

    def render(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.column}: {self.severity}: {self.message} ({self.rule})"
        )


def in_package(path: str) -> bool:
    return path == PACKAGE or path.startswith(f"{PACKAGE}/")


# --- pyright's report -----------------------------------------------------------------------


def run_pyright(root: Path) -> Report:
    """`pyright --outputjson` over `root` as its configuration sets, on this interpreter."""
    env = {k: v for k, v in os.environ.items() if k not in PYRIGHT_VERSION_OVERRIDES}
    proc = subprocess.run(
        [sys.executable, "-m", "pyright", "--outputjson", "--pythonpath", sys.executable],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    # pyright exits 0 when it reports nothing and 1 when it reports findings;
    # anything else means it did not check the tree.
    if proc.returncode not in (0, 1):
        said = (proc.stderr or proc.stdout).strip()
        raise RatchetError(f"pyright exited {proc.returncode}: {said}")
    try:
        report: object = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RatchetError(f"pyright did not print a JSON report: {exc}") from exc
    if not isinstance(report, dict):
        raise RatchetError("pyright's report is not a JSON object")
    return {str(k): v for k, v in report.items()}


def findings_from_report(report: Report, root: Path) -> list[Finding]:
    """The counted findings of a pyright report, with paths relative to `root`."""
    diagnostics = report.get("generalDiagnostics")
    if not isinstance(diagnostics, list):
        raise RatchetError("pyright's report has no `generalDiagnostics` list")
    resolved_root = root.resolve()
    findings: list[Finding] = []
    for raw in diagnostics:
        if not isinstance(raw, dict) or raw.get("severity") not in COUNTED_SEVERITIES:
            continue
        path = Path(str(raw.get("file", "")))
        try:
            relative = path.resolve().relative_to(resolved_root).as_posix()
        except ValueError:
            relative = path.as_posix()
        start = raw.get("range", {}).get("start", {})
        message = str(raw.get("message", ""))
        findings.append(
            Finding(
                path=relative,
                rule=str(raw.get("rule") or NO_RULE),
                line=int(start.get("line", 0)) + 1,
                column=int(start.get("character", 0)) + 1,
                severity=str(raw["severity"]),
                message=message.splitlines()[0] if message else "",
            )
        )
    return findings


def count(findings: Iterable[Finding]) -> Counter[Key]:
    return Counter(f.key for f in findings)


# --- the baseline ---------------------------------------------------------------------------


def parse_baseline(text: str) -> dict[Key, int]:
    """A baseline's entries: `<file> <rule> <count>` lines; blank lines and `#` comments skipped."""
    baseline: dict[Key, int] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != 3 or not fields[2].isdigit() or int(fields[2]) < 1:
            raise RatchetError(
                f"{BASELINE} line {number}: expected `<file> <rule> <count>` with a count"
                f" above 0: {line!r}"
            )
        path, rule, n = fields
        if not in_package(path) or PurePosixPath(path).is_absolute() or ".." in path.split("/"):
            raise RatchetError(
                f"{BASELINE} line {number}: {path} is not in the package ({PACKAGE}/); the"
                " baseline counts only the package's findings"
            )
        if rule != NO_RULE and not RULE_NAME.fullmatch(rule):
            raise RatchetError(f"{BASELINE} line {number}: {rule!r} is not a rule name")
        if (path, rule) in baseline:
            raise RatchetError(f"{BASELINE} line {number}: {path} {rule} is listed twice")
        baseline[(path, rule)] = int(n)
    return baseline


def render_baseline(counts: Mapping[Key, int]) -> str:
    lines = [f"{path} {rule} {n}\n" for (path, rule), n in sorted(counts.items()) if n > 0]
    return BASELINE_HEADER + "".join(lines)


def read_baseline(root: Path) -> dict[Key, int]:
    """The committed baseline as the working tree has it; a missing one fails closed."""
    path = root / BASELINE
    if not path.is_file():
        raise RatchetError(f"there is no baseline at {BASELINE}: the gate fails closed without one")
    return parse_baseline(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Comparison:
    #: Each entry the package exceeds, or a key with no entry: (entry, count).
    worse: dict[Key, tuple[int, int]]
    #: Each entry the package is below: (entry, count).
    better: dict[Key, tuple[int, int]]


def compare(baseline: Mapping[Key, int], current: Mapping[Key, int]) -> Comparison:
    worse = {
        key: (baseline.get(key, 0), n) for key, n in current.items() if n > baseline.get(key, 0)
    }
    better = {
        key: (n, current.get(key, 0)) for key, n in baseline.items() if current.get(key, 0) < n
    }
    return Comparison(worse=dict(sorted(worse.items())), better=dict(sorted(better.items())))


def lowered(baseline: Mapping[Key, int], current: Mapping[Key, int]) -> dict[Key, int]:
    """The baseline lowered to `current`: no count above its entry, no new entry, and
    no entry the package has no finding under."""
    return {key: min(n, current.get(key, 0)) for key, n in baseline.items() if current.get(key, 0)}


def rule_totals(baseline: Mapping[Key, int]) -> Counter[str]:
    totals: Counter[str] = Counter()
    for (_path, rule), n in baseline.items():
        totals[rule] += n
    return totals


# --- the files pyright checks ---------------------------------------------------------------


def pattern_matches(pattern: str, path: str) -> bool:
    """Whether a pyright path pattern (`include`, `exclude`, `ignore`, `strict`) reaches
    `path`, both relative to the root: `**` stands for any number of directories, `*`
    and `?` for characters within one, and a pattern reaches what lies below it."""
    pure = PurePosixPath(pattern.replace("\\", "/"))
    if pure.is_absolute():
        return False
    regex = ""
    for part in pure.parts:
        if part == ".":
            continue
        if part == "**":
            regex += "(?:[^/]+/)*"
            continue
        for char in part:
            regex += "[^/]*" if char == "*" else "[^/]" if char == "?" else re.escape(char)
        regex += "/"
    return re.match(regex, f"{path}/") is not None


def _skipped(directory: str) -> bool:
    """A directory pyright skips by default: hidden, a cache, `node_modules`."""
    return directory.startswith(".") or directory in ("__pycache__", "node_modules")


def python_files(root: Path, entries: Iterable[str]) -> list[str]:
    """The `.py` and `.pyi` files at or under the given root-relative entries."""
    found: set[str] = set()
    for entry in entries:
        start = root / entry
        paths = [start] if start.is_file() else []
        for directory, subdirectories, files in os.walk(start):
            subdirectories[:] = [d for d in subdirectories if not _skipped(d)]
            paths.extend(Path(directory, name) for name in files)
        found.update(
            path.relative_to(root).as_posix() for path in paths if path.suffix in (".py", ".pyi")
        )
    return sorted(found)


def _strings(config: Mapping[str, Any], key: str, default: list[str]) -> list[str]:
    value = config.get(key, default)
    if not isinstance(value, list):
        raise RatchetError(f"[tool.pyright] `{key}` is not a list")
    return [str(item) for item in value]


def checked_files(root: Path, config: Mapping[str, Any]) -> list[str]:
    """The files pyright checks and the gate reads: under `include`, outside `exclude`
    and `ignore`."""
    left_out = _strings(config, "exclude", []) + _strings(config, "ignore", [])
    return [
        path
        for path in python_files(root, _strings(config, "include", ["."]))
        if not any(pattern_matches(pattern, path) for pattern in left_out)
    ]


# --- the configuration (point 5) ------------------------------------------------------------


def pyright_table(pyproject_text: str | None) -> dict[str, Any]:
    """`[tool.pyright]` of a `pyproject.toml`'s text; empty when there is none."""
    if pyproject_text is None:
        return {}
    try:
        document = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError as exc:
        raise RatchetError(f"{PYPROJECT} does not parse: {exc}") from exc
    table = document.get("tool", {}).get("pyright", {})
    return dict(table) if isinstance(table, dict) else {}


def read_configuration(root: Path) -> dict[str, Any]:
    """pyright's configuration as the working tree has it."""
    if (root / PYRIGHTCONFIG).exists():
        raise RatchetError(
            f"{PYRIGHTCONFIG} would replace {PYPROJECT}'s [tool.pyright] table, which is the"
            " configuration the gate checks: keep pyright's configuration there"
        )
    path = root / PYPROJECT
    return pyright_table(path.read_text(encoding="utf-8") if path.is_file() else None)


def _level(value: object) -> int | None:
    if value is False:
        return LEVELS["none"]
    if value is True:
        return LEVELS["error"]
    return LEVELS.get(value) if isinstance(value, str) else None


def configuration_problems(config: Mapping[str, Any], package_files: Sequence[str]) -> list[str]:
    """How the configuration narrows what the package is checked for, if it does."""
    problems: list[str] = []

    def uncovered(entries: list[str]) -> list[str]:
        return [f for f in package_files if not any(pattern_matches(p, f) for p in entries)]

    outside = uncovered(_strings(config, "include", ["."]))
    if outside:
        problems.append(
            f"`include` leaves {len(outside)} package file(s) unchecked, {outside[0]} among them"
        )
    not_strict = uncovered(_strings(config, "strict", []))
    if not_strict:
        problems.append(
            f"the strict list does not cover {len(not_strict)} package file(s),"
            f" {not_strict[0]} among them: it names the package directory, `{PACKAGE}`"
        )
    for key in ("exclude", "ignore"):
        for pattern in _strings(config, key, []):
            reached = [f for f in package_files if pattern_matches(pattern, f)]
            if reached:
                problems.append(
                    f"`{key}` entry {pattern!r} reaches into the package: {len(reached)}"
                    f" file(s), {reached[0]} among them"
                )
    if config.get("enableTypeIgnoreComments") is not False:
        problems.append(
            "`enableTypeIgnoreComments` is not false: pyright is to honour no `# type: ignore`"
        )
    environments = config.get("executionEnvironments", [])
    scopes: list[tuple[str, Mapping[str, Any]]] = [("the table", config)]
    if isinstance(environments, list):
        for environment in environments:
            if not isinstance(environment, dict):
                continue
            scope: dict[str, Any] = {str(k): v for k, v in environment.items()}
            root = str(scope.get("root", "."))
            if any(pattern_matches(root, f) for f in package_files):
                scopes.append((f"the execution environment for {root!r}", scope))
    for where, settings in scopes:
        for rule, floor in NOT_OVERRIDDEN_BY_STRICT.items():
            level = _level(settings.get(rule)) if rule in settings else None
            if level is not None and level < LEVELS[floor]:
                problems.append(
                    f"{where} sets `{rule}` to {settings[rule]!r}, below the {floor} strict mode"
                    " reports; strict does not override that rule, so the package would be"
                    " checked for less"
                )
        if where != "the table" and settings.get("enableTypeIgnoreComments") is True:
            problems.append(f"{where} sets `enableTypeIgnoreComments` to true")
    return problems


# --- suppressions and file comments (point 5) -----------------------------------------------


def comment_problems(source: str, *, package: bool) -> list[tuple[int, str]]:
    """Each comment of a module's source the gate refuses, as (line, why)."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return []  # pyright reports what does not parse
    problems: list[tuple[int, str]] = []
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        line, text = token.start[0], token.string[1:]
        directive = text.strip()
        if directive.startswith("pyright:") and not directive[8:].strip().startswith("ignore"):
            problems.append(
                (
                    line,
                    "a file comment setting the mode or a rule's severity: the configuration"
                    " sets them, in pyproject.toml's [tool.pyright] table",
                )
            )
            continue
        if TYPE_IGNORE.search(text):
            why = "a `# type: ignore`, which pyright honours none of here: fix the finding"
            if not package:
                why += ", or name its rule and the reason: `# pyright: ignore[<rule>] <reason>`"
            problems.append((line, why))
        match = PYRIGHT_IGNORE.search(text)
        if match is None:
            continue
        rules = [r.strip() for r in (match.group("rules") or "").split(",") if r.strip()]
        if package:
            problems.append(
                (
                    line,
                    "a suppression in the package, which carries none: fix the finding — an"
                    " annotation, a `cast` to the type the code knows, a typed wrapper",
                )
            )
        elif not rules:
            problems.append(
                (
                    line,
                    "a `# pyright: ignore` naming no rule: name its rules, then give the reason",
                )
            )
        elif not REASON.search(text[match.end() :]):
            problems.append(
                (
                    line,
                    f"`# pyright: ignore[{', '.join(rules)}]` gives no reason: write it after"
                    " the rules, on the same line",
                )
            )
    return problems


def suppression_problems(root: Path, files: Iterable[str]) -> list[str]:
    problems: list[str] = []
    for path in files:
        try:
            source = (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RatchetError(f"cannot read {path}: {exc}") from exc
        for line, why in comment_problems(source, package=in_package(path)):
            problems.append(f"{path}:{line}: {why}")
    return problems


# --- git ------------------------------------------------------------------------------------


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def committed(root: Path, revision: str, path: str) -> str | None:
    """`path` as `revision` has it; None when it has no such file."""
    shown = _git(root, "show", f"{revision}:{path}")
    return shown.stdout if shown.returncode == 0 else None


def working(root: Path, path: str) -> str | None:
    file = root / path
    return file.read_text(encoding="utf-8") if file.is_file() else None


def changed_since(root: Path, revision: str) -> list[str]:
    """What the working tree changes, against `revision`, of what pyright's findings rest on
    besides the code: the lock and pyright's configuration."""
    changed: list[str] = []
    if committed(root, revision, LOCK) != working(root, LOCK):
        changed.append(LOCK)
    if pyright_table(committed(root, revision, PYPROJECT)) != pyright_table(
        working(root, PYPROJECT)
    ):
        changed.append(f"{PYPROJECT} [tool.pyright]")
    return changed


# --- the guard (point 4) --------------------------------------------------------------------


def guard(root: Path) -> tuple[list[str], list[str]]:
    """(problems, notes): the baseline's package totals per rule against the change's base."""
    base = default_branch.base(root)
    if base.problem is not None or base.fork is None:
        raise RatchetError(
            "the baseline guard cannot compare with the base: "
            + (base.problem or f"the base {base.ref!r} cannot be compared.")
        )
    before_text = committed(root, base.fork, BASELINE)
    if before_text is None:
        return [], []  # the change brings the baseline in
    before = rule_totals(parse_baseline(before_text))
    now = rule_totals(read_baseline(root))
    rose = {
        rule: (before.get(rule, 0), n) for rule, n in sorted(now.items()) if n > before.get(rule, 0)
    }
    if not rose:
        return [], []
    against = f"against {base.ref} (where this change left it, {base.fork[:12]})"
    listed = [f"  {rule}: {was} -> {n}" for rule, (was, n) in rose.items()]
    excuse = changed_since(root, base.fork)
    if excuse:
        return [], [
            f"The baseline's package totals rose {against}; the change alters"
            f" {' and '.join(excuse)}, so the guard lets it pass. Say in the pull request why"
            " the counts rose:",
            *listed,
        ]
    return [
        f"The baseline's package totals rose {against}, and the change alters neither {LOCK}"
        " nor pyright's configuration. A finding a change writes is fixed, never admitted;"
        " a raise is for moved code or an upgrade, and a move keeps every total:",
        *listed,
    ], []


# --- the commands ---------------------------------------------------------------------------


def _section(title: str, lines: Sequence[str]) -> list[str]:
    return [title, *(f"  {line}" for line in lines)] if lines else []


def _package_files(root: Path) -> list[str]:
    return python_files(root, [PACKAGE])


def _worse_lines(comparison: Comparison, package: Sequence[Finding]) -> list[str]:
    """Each entry the package exceeds, with the findings under it."""
    lines: list[str] = []
    for (path, rule), (entry, n) in comparison.worse.items():
        lines.append(f"{path} {rule}: {n}, the baseline admits {entry}")
        shown = sorted((f for f in package if f.key == (path, rule)), key=lambda f: f.line)
        lines.extend(f"  {f.render()}" for f in shown[:SHOWN_PER_ENTRY])
        if len(shown) > SHOWN_PER_ENTRY:
            lines.append(f"  ... and {len(shown) - SHOWN_PER_ENTRY} more")
    return lines


def check(root: Path, pyright: RunPyright) -> int:
    """The gate: 0 when it passes."""
    out: list[str] = []
    failed = False

    def fail(title: str, lines: Sequence[str]) -> None:
        nonlocal failed
        if lines:
            failed = True
            out.extend(_section(title, lines))

    try:
        config = read_configuration(root)
        fail(
            "The configuration narrows what the package is checked for (PRJ-010 point 5):",
            configuration_problems(config, _package_files(root)),
        )
        fail(
            "Comments the gate refuses (PRJ-010 point 5):",
            suppression_problems(root, checked_files(root, config)),
        )
    except RatchetError as exc:
        fail("The configuration cannot be read:", [str(exc)])

    summary: list[str] = []
    try:
        report = pyright(root)
        findings = findings_from_report(report, root)
        outside = [f for f in findings if not in_package(f.path)]
        fail(
            "Findings outside the package, which is gated outright (PRJ-010 point 2):",
            [f.render() for f in outside],
        )
        package = [f for f in findings if in_package(f.path)]
        current = count(package)
        baseline = read_baseline(root)
        comparison = compare(baseline, current)
        fail(
            "Package findings the baseline does not admit (PRJ-010 point 3) — fix them; the"
            " baseline does not rise to admit them:",
            _worse_lines(comparison, package),
        )
        if comparison.better:
            out.extend(
                _section(
                    "The package has fewer findings than the baseline admits under these"
                    f" entries: lower them in this change, `{LOWER_COMMAND}` once it is"
                    " committed (PRJ-010 point 3):",
                    [
                        f"{path} {rule}: {n}, the baseline admits {entry}"
                        for (path, rule), (entry, n) in comparison.better.items()
                    ],
                )
            )
        summary.append(
            f"pyright {report.get('version', '?')}: {len(outside)} finding(s) outside the"
            f" package; {len(package)} in it, {sum(baseline.values())} admitted"
        )
    except RatchetError as exc:
        fail("pyright's findings cannot be judged:", [str(exc)])

    try:
        problems, notes = guard(root)
        fail("The baseline guard (PRJ-010 point 4):", problems)
        out.extend(notes)
    except RatchetError as exc:
        fail("The baseline guard cannot run:", [str(exc)])

    out.extend(summary)
    out.append("pyright ratchet: FAILED" if failed else "pyright ratchet: ok")
    print("\n".join(out))
    return 1 if failed else 0


def lower_refusals(root: Path) -> list[str]:
    """What differs from the commit among what the counts rest on (point 6)."""
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", PACKAGE)
    if status.returncode != 0:
        raise RatchetError(f"git status failed: {status.stderr.strip()}")
    differing = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    return differing + changed_since(root, "HEAD")


def lower(root: Path, pyright: RunPyright) -> int:
    """Lower the baseline to the commit's counts; 0 when it is as low as they are."""
    try:
        read_configuration(root)
        differing = lower_refusals(root)
        if differing:
            print(
                "pyright ratchet: not lowering — the baseline is written from the commit, and"
                " these differ from it; commit them first:"
            )
            print("\n".join(f"  {path}" for path in differing))
            return 1
        baseline = read_baseline(root)
        current = count(f for f in findings_from_report(pyright(root), root) if in_package(f.path))
    except RatchetError as exc:
        print(f"pyright ratchet: {exc}", file=sys.stderr)
        return 1
    comparison = compare(baseline, current)
    if comparison.worse:
        print(
            "pyright ratchet: not lowering — the package has findings the baseline does not"
            " admit; the gate (`uv run python scripts/pyright_ratchet.py`) lists them:"
        )
        print(
            "\n".join(
                f"  {p} {r}: {n}, the baseline admits {e}"
                for (p, r), (e, n) in comparison.worse.items()
            )
        )
        return 1
    if not comparison.better:
        print("pyright ratchet: the baseline is already as low as the package's counts")
        return 0
    (root / BASELINE).write_text(render_baseline(lowered(baseline, current)), encoding="utf-8")
    print(f"pyright ratchet: lowered in {BASELINE}, for the change to commit:")
    for (path, rule), (entry, n) in comparison.better.items():
        print(f"  {path} {rule}: {entry} -> {n}" if n else f"  {path} {rule}: {entry} -> gone")
    return 0


def measure(root: Path, pyright: RunPyright) -> int:
    """Print the package's counts in the baseline's form; write nothing."""
    try:
        findings = findings_from_report(pyright(root), root)
    except RatchetError as exc:
        print(f"pyright ratchet: {exc}", file=sys.stderr)
        return 1
    print(render_baseline(count(f for f in findings if in_package(f.path))), end="")
    return 0


COMMANDS: Mapping[str, Callable[[Path, RunPyright], int]] = {
    "check": check,
    "lower": lower,
    "measure": measure,
}


def main(
    argv: Sequence[str] | None = None, *, root: Path = ROOT, pyright: RunPyright = run_pyright
) -> int:
    parser = argparse.ArgumentParser(
        prog="pyright_ratchet.py", description=(__doc__ or "").splitlines()[0]
    )
    parser.add_argument("command", nargs="?", choices=sorted(COMMANDS), default="check")
    args = parser.parse_args(argv)
    return COMMANDS[args.command](root, pyright)


if __name__ == "__main__":
    sys.exit(main())
