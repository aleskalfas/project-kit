"""Process journal logging: the project's choice, read forgivingly (COR-033 point 7).

The process engine can keep an append-only, per-subject journal of the moves it
validates and executes — optional audit, never the source of truth (position is
always re-derived from reality). Whether it does is a project declaration in the
backbone configuration file (COR-048), under one key the core process record
owns:

    process:
      journal:
        enabled: false    # default — the engine writes and reads no journal
        committed: false  # when enabled: commit the journals, or keep them per clone

This module is the one reader of that key and the one owner of what follows from
it outside the engine: the ignore pattern the `.pkit/.gitignore` render
contributes through the backbone's runtime-ignore seam (ADR-009 rule 7). Journals
are ignored unless the project chose to commit them — so a project that enables
logging clone-local, and a project that never enabled it, both keep journal files
out of version control, and only an explicit `committed: true` lets them in. A
component that still declares the pattern itself would defeat that choice, so
while the journals are committed the render leaves its entry out
(`JournalSettings.drops_claim`, through `claims_journals`) and validation warns
on it.

Reading is forgiving (COR-048 point 4): an absent file, key or block, or a value
that is not a boolean, reads as the default; `pkit validate` is the strict side.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_kit.project_config import read_config

#: The configuration keys, as the schema declares them (`process.journal.*`).
PROCESS_KEY = "process"
JOURNAL_KEY = "journal"
ENABLED_KEY = "enabled"
COMMITTED_KEY = "committed"

#: Every process journal the engine can write, repo-root-relative. The engine
#: owns the path — `<capability>/project/process/<process-id>/<subject>.journal.jsonl`
#: (COR-033 layout) — so the backbone declares the pattern, not a capability.
JOURNAL_GLOB = ".pkit/capabilities/*/project/process/**/*.journal.jsonl"

#: What every reader of the journal says when logging is off, instead of
#: presenting an empty history as if nothing had happened.
NOT_ENABLED = "journal logging is not enabled for this project"

#: Why the render leaves out a component's entry claiming journals
#: (`JournalSettings.drops_claim`) — said beside the entry wherever it is named.
CLAIM_DROPPED = "the backbone owns the journal pattern while journals are committed"


@dataclass(frozen=True)
class JournalSettings:
    """The project's journal-logging choice; the defaults are the owning record's."""

    enabled: bool = False
    committed: bool = False

    @property
    def ignored(self) -> bool:
        """Whether journal files are kept out of version control: always, unless
        logging is on and the project chose to commit the journals."""
        return not (self.enabled and self.committed)

    def runtime_ignore_patterns(self) -> list[str]:
        """The journal's contribution to the backbone's runtime-ignore seam: the
        journal pattern unless the project commits its journals."""
        return [JOURNAL_GLOB] if self.ignored else []

    def drops_claim(self, pattern: str) -> bool:
        """Whether the `.pkit/.gitignore` render leaves out a component's
        `runtime_ignore` entry: the entry claims journals (`claims_journals`) and
        the project commits them. The backbone owns the journal pattern, so its
        choice takes precedence over a package older than that ownership
        (ADR-009 rule 7); while the journals stay ignored the entry is redundant
        and renders as declared."""
        return not self.ignored and claims_journals(pattern)

    def as_dict(self) -> dict[str, bool]:
        return {ENABLED_KEY: self.enabled, COMMITTED_KEY: self.committed}


def settings_from(config: Mapping[str, Any]) -> JournalSettings:
    """The journal settings from a parsed configuration mapping. Anything that
    is not a boolean where one is expected reads as the default."""
    process = config.get(PROCESS_KEY)
    journal = process.get(JOURNAL_KEY) if isinstance(process, Mapping) else None
    if not isinstance(journal, Mapping):
        return JournalSettings()
    return JournalSettings(
        enabled=_boolean(journal.get(ENABLED_KEY)),
        committed=_boolean(journal.get(COMMITTED_KEY)),
    )


def read_settings(target_root: Path) -> JournalSettings:
    """The project's journal settings, defaults for every zero-config state."""
    return settings_from(read_config(target_root))


def claims_journals(pattern: str) -> bool:
    """Whether a component's `runtime_ignore` pattern declares journals, the files
    whose ignore line the backbone owns: the pattern, read as a path, matches
    `JOURNAL_GLOB`. A component declaring it (a package older than the backbone
    owning the line) would keep journals ignored when the project commits them,
    so the render then leaves it out (`JournalSettings.drops_claim`) and
    `pkit validate` warns on it (`package_validate`)."""
    return fnmatch.fnmatchcase(pattern.strip(), JOURNAL_GLOB)


def _boolean(value: Any) -> bool:
    return value if isinstance(value, bool) else False
