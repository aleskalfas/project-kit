"""Tests for how demo-recording's `record.sh` reads a recording configuration (#2707).

A key the configuration lacks reads as empty, under the script's
`set -euo pipefail`. So `recordings_dir` falls back to `./recordings`, the font
keys to their defaults, and a missing `cwd` or window's bounds stops the script
with its message, never with no message at all.

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
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".pkit" / "capabilities" / "demo-recording" / "scripts"

MISSING_FIELDS = (
    "record.sh: config missing required fields (cwd / windows.recording / windows.control)"
)

CWD = "cwd: /the/demo/drives\n"
RECORDING_BOUNDS = "  recording: [50, 50, 1330, 850]\n"
CONTROL_BOUNDS = "  control: [50, 880, 750, 1150]\n"
CONFIGURATION = f"{CWD}windows:\n{RECORDING_BOUNDS}{CONTROL_BOUNDS}"

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
