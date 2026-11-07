"""Tests for how demo-recording's `record.sh` reads a recording configuration (#2707, #2709).

A key the configuration lacks reads as empty, under the script's
`set -euo pipefail`. So `recordings_dir` falls back to `./recordings`, the font
keys to their defaults, and a missing `cwd` or window's bounds stops the script
with its message, never with no message at all.

A key it has reads as YAML reads it: a comment after a scalar or a window's
bounds is not part of the value, and neither are a scalar's quotes. A `#` inside
the quotes stays, and so does one with no space before it.

The script runs for real, from a copy of the capability's scripts, and no test
opens a window. The copy's `setup-windows.sh` only notes how it was called, and
a stub `osascript` only notes what the script dispatches. A stub `uname` lets
the macOS gate pass on any platform.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parents[1]
CAPABILITY = REPO / ".pkit" / "capabilities" / "demo-recording"
SCRIPTS = CAPABILITY / "scripts"
SCHEMA = CAPABILITY / "schemas" / "record-config.yaml"
NEW_BUNDLE = CAPABILITY / "skills" / "demo-recording" / "new-bundle.md"

MISSING_FIELDS = (
    "record.sh: config missing required fields (cwd / windows.recording / windows.control)"
)

CWD = "cwd: /the/demo/drives\n"
RECORDING_BOUNDS = "  recording: [50, 50, 1330, 850]\n"
CONTROL_BOUNDS = "  control: [50, 880, 750, 1150]\n"
CONFIGURATION = f"{CWD}windows:\n{RECORDING_BOUNDS}{CONTROL_BOUNDS}"
COMMENT = "   # iTerm bounds: [left, top, right, bottom]"

NOTE_WINDOW_CALL = 'printf "%s\\n" "$DCR_CWD" "$DCR_FONT_SIZE" "$DCR_FONT_NAME" "$1" "$2"'

STORYBOARD = """# A demo

## Step 1 — list the files

```shell
ls
```
"""


def _stub(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def _with_cwd(written: str) -> str:
    """The whole configuration, with `written` after its `cwd:`."""
    return CONFIGURATION.replace(CWD, f"cwd: {written}\n")


def _schema_example() -> str:
    return SCHEMA.read_text(encoding="utf-8")


def _new_bundle_template() -> str:
    fence = re.search(r"```yaml\n(.*?)```", NEW_BUNDLE.read_text(encoding="utf-8"), re.DOTALL)
    assert fence is not None
    return fence.group(1)


@dataclass
class Engine:
    """A copy of the scripts, a demo bundle beside it, and where the stubs note their calls."""

    scripts: Path
    stubs: Path
    bundle: Path
    opened: Path
    dispatched: Path

    def run(self, configuration: str, *args: str) -> subprocess.CompletedProcess[str]:
        """Run `record.sh` with `args` and `configuration` as the bundle's `record.yaml`."""
        config = self.bundle / "record.yaml"
        config.write_text(configuration, encoding="utf-8")
        path = os.pathsep.join(
            [str(self.stubs), str(Path(sys.executable).parent), os.environ["PATH"]]
        )
        return subprocess.run(
            ["bash", str(self.scripts / "record.sh"), *args, "--config", str(config)],
            capture_output=True,
            text=True,
            check=False,
            # An empty `DCR_LOG` leaves the log where the script puts it by default.
            env={**os.environ, "PATH": path, "DCR_LOG": ""},
        )

    def record(self, configuration: str) -> subprocess.CompletedProcess[str]:
        return self.run(configuration, str(self.bundle / "demo.md"))

    def video_folder(self) -> Path:
        """The folder of the video path the script dispatches to the second window."""
        output = re.search(r"--output (\S+)", self.dispatched.read_text(encoding="utf-8"))
        assert output is not None
        return Path(output.group(1)).parent

    def window_call(self) -> list[str]:
        """What the windows were opened with: cwd, font size, font name and both bounds."""
        return self.opened.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    scripts = tmp_path / "scripts"
    shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "demo.md").write_text(STORYBOARD, encoding="utf-8")
    opened = tmp_path / "opened"
    dispatched = tmp_path / "dispatched"
    _stub(
        scripts / "plugins" / "recording" / "setup-windows.sh",
        f'{NOTE_WINDOW_CALL} > "{opened}"',
    )
    _stub(stubs / "osascript", f'cat >> "{dispatched}"')
    _stub(stubs / "uname", "echo Darwin")
    _stub(stubs / "sleep", "exit 0")
    return Engine(scripts, stubs, bundle, opened, dispatched)


class TestRecordingsDir:
    def test_a_configuration_without_it_records_into_recordings(self, engine: Engine) -> None:
        result = engine.record(CONFIGURATION)
        assert result.returncode == 0, result.stderr
        recordings = engine.bundle / "recordings"
        assert engine.video_folder() == recordings
        assert len(list((recordings / ".logs").glob("*-demo.log"))) == 1

    def test_a_configuration_naming_a_folder_records_into_it(self, engine: Engine) -> None:
        result = engine.record(f"{CONFIGURATION}recordings_dir: ./takes\n")
        assert result.returncode == 0, result.stderr
        assert engine.video_folder() == engine.bundle / "takes"
        assert not (engine.bundle / "recordings").exists()


class TestRequiredFields:
    @pytest.mark.parametrize(
        "field",
        [CWD, RECORDING_BOUNDS, CONTROL_BOUNDS],
        ids=["cwd", "windows.recording", "windows.control"],
    )
    def test_a_configuration_without_one_stops_with_the_message(
        self, engine: Engine, field: str
    ) -> None:
        result = engine.record(CONFIGURATION.replace(field, ""))
        assert result.returncode == 2
        assert MISSING_FIELDS in result.stderr
        assert not engine.opened.exists()
        assert not engine.dispatched.exists()
        assert not (engine.bundle / "recordings").exists()

    def test_a_whole_configuration_opens_the_windows_with_its_values(self, engine: Engine) -> None:
        result = engine.record(CONFIGURATION)
        assert result.returncode == 0, result.stderr
        call = engine.window_call()
        assert call[0] == "/the/demo/drives"
        assert call[3:] == ["50,50,1330,850", "50,880,750,1150"]


class TestFonts:
    def test_a_configuration_without_them_opens_the_windows_with_the_defaults(
        self, engine: Engine
    ) -> None:
        result = engine.record(CONFIGURATION)
        assert result.returncode == 0, result.stderr
        assert engine.window_call()[1:3] == ["18", "Menlo-Regular"]

    def test_a_configuration_naming_them_opens_the_windows_with_them(self, engine: Engine) -> None:
        result = engine.record(f"{CONFIGURATION}font_size: 14\nfont_name: Monaco\n")
        assert result.returncode == 0, result.stderr
        assert engine.window_call()[1:3] == ["14", "Monaco"]


class TestWindowsAction:
    def test_a_configuration_without_cwd_stops_with_the_message(self, engine: Engine) -> None:
        result = engine.run(CONFIGURATION.replace(CWD, ""), "windows")
        assert result.returncode == 2
        assert "record.sh: config missing required fields" in result.stderr
        assert not engine.opened.exists()

    def test_a_whole_configuration_opens_the_windows(self, engine: Engine) -> None:
        result = engine.run(CONFIGURATION, "windows")
        assert result.returncode == 0, result.stderr
        assert engine.window_call()[0] == "/the/demo/drives"


class TestTrailingComments:
    def test_a_comment_after_a_scalar_is_not_part_of_it(self, engine: Engine) -> None:
        result = engine.record(
            f"{_with_cwd(f'/the/demo/drives{COMMENT}')}"
            f"font_size: 14{COMMENT}\nfont_name: Monaco{COMMENT}\n"
        )
        assert result.returncode == 0, result.stderr
        assert engine.window_call()[:3] == ["/the/demo/drives", "14", "Monaco"]

    def test_a_comment_after_recordings_dir_is_not_part_of_the_folder(self, engine: Engine) -> None:
        result = engine.record(f"{CONFIGURATION}recordings_dir: ./takes{COMMENT}\n")
        assert result.returncode == 0, result.stderr
        assert engine.video_folder() == engine.bundle / "takes"

    def test_a_key_with_only_a_comment_falls_back_to_its_default(self, engine: Engine) -> None:
        result = engine.record(f"{CONFIGURATION}recordings_dir:{COMMENT}\n")
        assert result.returncode == 0, result.stderr
        assert engine.video_folder() == engine.bundle / "recordings"

    def test_a_required_key_with_only_a_comment_stops_with_the_message(
        self, engine: Engine
    ) -> None:
        result = engine.record(CONFIGURATION.replace(CWD, f"cwd:{COMMENT}\n"))
        assert result.returncode == 2
        assert MISSING_FIELDS in result.stderr

    @pytest.mark.parametrize(
        ("written", "read"),
        [
            ("/the/demo#1", "/the/demo#1"),
            (f"/the/demo#1{COMMENT}", "/the/demo#1"),
            ('/the/"demo # a comment', '/the/"demo'),
        ],
        ids=["no space before it", "and a comment after it", "a quote inside a plain value"],
    )
    def test_a_plain_value_ends_at_a_hash_with_a_space_before_it(
        self, engine: Engine, written: str, read: str
    ) -> None:
        result = engine.record(_with_cwd(written))
        assert result.returncode == 0, result.stderr
        assert engine.window_call()[0] == read

    @pytest.mark.parametrize(
        ("written", "read"),
        [
            ('"/the/demo #1"', "/the/demo #1"),
            ("'/the/demo #1'", "/the/demo #1"),
            ('"/the/demo #1"   # the "demo" folder', "/the/demo #1"),
            ("'/the/demo #1'   # the 'demo' folder", "/the/demo #1"),
            ('"/the/\\" demo #1"', '/the/\\" demo #1'),
            ("'/the/'' demo #1'", "/the/'' demo #1"),
        ],
        ids=[
            "double",
            "single",
            "double with a comment",
            "single with a comment",
            "double with an escaped quote",
            "single with an escaped quote",
        ],
    )
    def test_a_quoted_value_ends_at_its_closing_quote(
        self, engine: Engine, written: str, read: str
    ) -> None:
        result = engine.record(_with_cwd(written))
        assert result.returncode == 0, result.stderr
        assert engine.window_call()[0] == read

    def test_a_comment_after_a_windows_bounds_is_not_part_of_them(self, engine: Engine) -> None:
        result = engine.record(
            f"{CWD}windows:{COMMENT}\n"
            f"  recording: [50, 50, 1330, 850]{COMMENT}\n"
            f"  control: [50, 880, 750, 1150]{COMMENT} and more\n"
        )
        assert result.returncode == 0, result.stderr
        assert engine.window_call()[3:] == ["50,50,1330,850", "50,880,750,1150"]
        assert "--rect 50,50,1280,800 " in engine.dispatched.read_text(encoding="utf-8")

    def test_the_windows_action_reads_them_the_same_way(self, engine: Engine) -> None:
        result = engine.run(
            f"cwd: /the/demo/drives{COMMENT}\nwindows:\n"
            f"  recording: [50, 50, 1330, 850]{COMMENT}\n{CONTROL_BOUNDS}",
            "windows",
        )
        assert result.returncode == 0, result.stderr
        call = engine.window_call()
        assert call[0] == "/the/demo/drives"
        assert call[3] == "50,50,1330,850"

    @pytest.mark.parametrize(
        "example", [_schema_example, _new_bundle_template], ids=["schema", "new-bundle"]
    )
    def test_a_shipped_example_runs_with_the_values_yaml_reads_from_it(
        self, engine: Engine, example: Callable[[], str]
    ) -> None:
        written = example()
        result = engine.record(written)
        assert result.returncode == 0, result.stderr
        values = YAML(typ="safe").load(written)
        assert engine.window_call() == [
            values["cwd"],
            str(values["font_size"]),
            values["font_name"],
            ",".join(str(edge) for edge in values["windows"]["recording"]),
            ",".join(str(edge) for edge in values["windows"]["control"]),
        ]
        assert engine.video_folder() == engine.bundle / values["recordings_dir"]
