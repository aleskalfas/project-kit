"""An operating system a test sets, for the backbone's reading of a recorded
process (`project_kit.recorded_processes`, ADR-103), and a project whose
adapters declare a session (`project_kit.harness_session`)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from project_kit import harness_session as hs
from project_kit import recorded_processes as rp


@dataclass
class FakeSystem:
    """An operating system a test sets: the space it runs in, the table's entries
    by id, and what a null signal finds by id."""

    platform: str = "darwin"
    raw: rp.RawSpace = field(
        default_factory=lambda: rp.RawSpace("machine-1", "boot-1", None, False, True)
    )
    entries: dict[int, rp.Entry] = field(default_factory=dict[int, rp.Entry])
    signals: dict[int, str] = field(default_factory=dict[int, str])

    def space(self) -> rp.RawSpace:
        return self.raw

    def entry(self, pid: int) -> rp.Entry:
        return self.entries.get(pid, rp.Entry(False))

    def signal(self, pid: int) -> str:
        return self.signals.get(pid, rp.NONE)


def project(tmp_path: Path, declarations: dict[str, str | None]) -> Path:
    """A project of the test's own, under ``tmp_path``: each adapter of
    ``declarations`` registered, with the declaration of a session given,
    none where None, and an `origin` remote."""
    root = tmp_path / "proj"
    (root / ".pkit").mkdir(parents=True)
    components = "".join(
        f"  - kind: adapter\n    name: {name}\n"
        f"    manifest: .pkit/adapters/{name}/project/manifest.yaml\n"
        for name in declarations
    )
    registry = components or "  []\n"
    (root / ".pkit" / "manifest.yaml").write_text(
        f"backbone_version: 0.0.0\ncomponents:\n{registry}", encoding="utf-8"
    )
    for name, text in declarations.items():
        folder = root / ".pkit" / "adapters" / name
        folder.mkdir(parents=True)
        if text is not None:
            (folder / hs.DECLARATION).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "https://github.com/o/r"], check=True
    )
    return root
