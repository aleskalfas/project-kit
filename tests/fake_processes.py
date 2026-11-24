"""An operating system a test sets, for the backbone's reading of a recorded
process (`project_kit.recorded_processes`, ADR-103)."""

from __future__ import annotations

from dataclasses import dataclass, field

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
