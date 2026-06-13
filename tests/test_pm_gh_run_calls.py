"""Static scan: every `gh_run(...)` call in pm scripts passes `config`.

The signature is `gh_run(args: list[str], config: dict, **kwargs)`. Calls
that pass a kwarg as the second positional (e.g. `gh_run([...], check=False)`)
trigger `TypeError: missing 1 required positional argument: 'config'` at
runtime. The bug had been latent in audit-comment paths (close-issue,
edit-issue --force, reopen-*, close-pr, etc.) and was surfaced + fixed
in #209.

This is a meta-test: it grep-scans the script tree for the buggy pattern.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)

# Match `gh_run( [<list>], <kwarg>=...` — i.e. the second positional is a
# keyword argument instead of `config`. The valid pattern is
# `gh_run( [<list>], <identifier>, ...` where the second positional is a
# value (config dict).
BUGGY_CALL = re.compile(
    r"gh_run\(\s*\[[^\]]+\]\s*,\s*(check|env|capture_output|text|timeout)=",
    re.MULTILINE,
)


def _python_files_under(root: Path) -> list[Path]:
    return [
        p
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    ]


@pytest.mark.parametrize("script_path", _python_files_under(SCRIPTS_DIR), ids=lambda p: p.name)
def test_gh_run_calls_pass_config(script_path: Path) -> None:
    """Every gh_run(...) call in this script passes `config` as the second arg.

    A buggy call looks like `gh_run([...], check=False, ...)` — the
    second positional slot is filled by a kwarg, so `config` is missing.
    Fixed across the pm scripts in #209.
    """
    source = script_path.read_text(encoding="utf-8")
    matches = list(BUGGY_CALL.finditer(source))
    if not matches:
        return
    # Build a friendly error pointing at each buggy site.
    sites = []
    for m in matches:
        line_no = source[: m.start()].count("\n") + 1
        sites.append(f"  {script_path.name}:{line_no}: {m.group(0)[:80]!r}")
    pytest.fail(
        f"gh_run() call(s) missing the required `config` positional "
        f"argument in {script_path.name}:\n" + "\n".join(sites)
    )
