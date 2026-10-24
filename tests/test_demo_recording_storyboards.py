"""Tests for demo-recording's storyboard engine (#1904; demo-recording DEC-001).

A fenced block whose tag no loaded plugin provides is a warning, not an error,
so an executable storyboard stays readable when a plugin is missing:
`validate` exits 0 on it, and the runner's dispatch, which `run` and `record`
read, goes on past it. A fenced block that breaks its directive's content, or
a storyboard that breaks the format, is still an error.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".pkit" / "capabilities" / "demo-recording" / "scripts"
RUNNER = SCRIPTS / "storyboards" / "runner.py"
VALIDATE_SH = SCRIPTS / "validate.sh"

UNKNOWN_TAG = "step 2 line 13: unrecognised directive 'mermaid' — is the providing plugin loaded?"

STORYBOARD = """# A demo

Opening prose.

## Step 1 — list the files

```shell
ls -la
```

## Step 2 — a diagram for the reader

```mermaid
graph TD
```

```sleep
2
```
"""

BROKEN_DIRECTIVE = """# A demo

## Step 1 — pause

```sleep
soon
```

```mermaid
graph TD
```
"""


def _plugin_module() -> ModuleType:
    """`storyboards/plugin.py`, loaded on its own: it imports nothing of the engine."""
    spec = importlib.util.spec_from_file_location(
        "demo_recording_plugin", SCRIPTS / "storyboards" / "plugin.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "demo.md"
    path.write_text(text, encoding="utf-8")
    return path


def _runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class TestRegistry:
    def test_an_unknown_tag_is_no_error(self) -> None:
        registry = _plugin_module().PluginRegistry()
        assert registry.validate_fence("mermaid", "graph TD", 2, 13) == []

    def test_an_unknown_tag_warns_with_its_step_and_line(self) -> None:
        registry = _plugin_module().PluginRegistry()
        assert registry.fence_warnings("mermaid", 2, 13) == [UNKNOWN_TAG]

    def test_a_known_tag_has_no_warning(self) -> None:
        plugin_module = _plugin_module()

        class Shell(plugin_module.Plugin):
            @property
            def name(self) -> str:
                return "fake"

            @property
            def fence_languages(self) -> list[str]:
                return ["shell"]

            def validate(self, lang: str, content: str) -> list[str]:
                return ["body is empty"] if not content.strip() else []

            def describe(self, lang: str, content: str) -> str:
                return content

            def actions(self, lang: str, content: str, context: dict) -> list[tuple[str, ...]]:
                return []

        registry = plugin_module.PluginRegistry()
        registry.register(Shell())
        assert registry.fence_warnings("shell", 1, 5) == []
        assert registry.validate_fence("shell", "", 1, 5) == [
            "step 1 line 5 [fake/shell]: body is empty"
        ]

    def test_an_unknown_tag_dispatches_a_warning(self) -> None:
        registry = _plugin_module().PluginRegistry()
        assert registry.actions_for_fence("mermaid", "graph TD", {}) == [
            ("warn_unknown_directive", "mermaid")
        ]


class TestValidate:
    def test_an_unknown_tag_warns_and_exits_0(self, tmp_path: Path) -> None:
        result = _runner(str(_write(tmp_path, STORYBOARD)), "--validate")
        assert result.returncode == 0, result.stderr
        assert "⚠ 1 warning(s):" in result.stderr
        assert f"  - {UNKNOWN_TAG}" in result.stderr
        assert "error" not in result.stderr
        assert "[UNKNOWN 'mermaid'] line 13" in result.stdout
        assert result.stdout.rstrip().endswith("✓ 2 step(s) parsed.  No errors.")

    def test_a_broken_directive_is_still_an_error(self, tmp_path: Path) -> None:
        result = _runner(str(_write(tmp_path, BROKEN_DIRECTIVE)), "--validate")
        assert result.returncode == 1
        assert "✗ 1 error(s):" in result.stderr
        assert "sleep: body must be a positive integer (seconds), got 'soon'" in result.stderr
        assert "⚠ 1 warning(s):" in result.stderr

    def test_a_storyboard_without_unknown_tags_has_no_warning(self, tmp_path: Path) -> None:
        text = STORYBOARD.replace("```mermaid\ngraph TD\n```\n\n", "")
        result = _runner(str(_write(tmp_path, text)), "--validate")
        assert result.returncode == 0, result.stderr
        assert "warning" not in result.stderr

    def test_the_validate_command_exits_0(self, tmp_path: Path) -> None:
        if not os.access(VALIDATE_SH, os.X_OK):
            pytest.skip("validate.sh is not executable in this checkout")
        # The script runs `python3`: the one of this test's interpreter.
        path = f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"
        env = {**os.environ, "PATH": path}
        result = subprocess.run(
            [str(VALIDATE_SH), str(_write(tmp_path, STORYBOARD))],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert f"  - {UNKNOWN_TAG}" in result.stderr


class TestDispatch:
    def test_run_and_record_go_on_past_an_unknown_tag(self, tmp_path: Path) -> None:
        result = _runner(str(_write(tmp_path, STORYBOARD)))
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == [
            "shell_run\tls -la",
            "warn_unknown_directive\tmermaid",
            "sleep_pause\t2",
        ]

    def test_a_broken_directive_still_refuses_the_storyboard(self, tmp_path: Path) -> None:
        result = _runner(str(_write(tmp_path, BROKEN_DIRECTIVE)))
        assert result.returncode == 1
        assert result.stdout == ""
        assert "sleep: body must be a positive integer" in result.stderr
        assert "mermaid" not in result.stderr
