"""Consolidate `.claude/settings.json` + `.claude/settings.local.json` permission allow lists.

A "subsumed" entry is a narrower permission rule fully covered by a
broader rule already present somewhere in the adopter's settings. The
canonical case: an adopter who once added `Bash(pkit new *)`,
`Bash(pkit refs *)`, `Bash(pkit --help)` keeps those entries (typically
in `settings.local.json` from interactive permission prompts) even
after the kit baseline grows `Bash(pkit:*)` in `settings.json`. The
narrow entries become inert duplicates — harmless, but visually noisy.

This module's job is to detect and (optionally) remove those duplicates
across **both** settings files:

- `.claude/settings.json` — committed project-wide config (kit baseline
  merged with project additions).
- `.claude/settings.local.json` — gitignored per-machine personal
  overrides (where Claude Code's interactive permission prompts
  typically accumulate narrow allows).

Subsumption is computed against the **union** of both files: a broader
rule in either file can subsume a narrower rule in either file. Apply
removes the redundant entry from whichever file(s) contain it.

Only `permissions.allow` is consolidated; `deny` is left alone (denies
should stay explicit for audit clarity).

v1 subsumption rules (kept deliberately narrow):
- `Bash(<prefix>:*)` subsumes `Bash(<prefix>)`, `Bash(<prefix> <args>)`,
  and `Bash(<prefix>:<args>)`.
- No Skill / Edit / Write / Read subsumption — those rules use exact
  names today and have no wildcard form.
- No path-glob equivalence — `Bash(.pkit/**/*.sh)` is treated as opaque.

Per the kit's "preserve adopter content" stance (per COR-001), this
module is the carrier for *deliberate* cleanup. Sync prints a hint when
opportunities are detected but doesn't act on them; the adopter runs
`pkit settings consolidate` explicitly when ready.

It also tells what a settings merge widens: the allow entries and the
top-level keys a version transition's merge adds to `.claude/settings.json`,
which the transition's report lists (ADR-065 point 4, `settings_widening`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import click

SETTINGS_FILENAMES: tuple[str, ...] = ("settings.json", "settings.local.json")


@dataclass(frozen=True)
class ConsolidationPair:
    """One redundant entry, the broader rule that subsumes it, and the file it lives in.

    `source_file` is None for in-memory pairs (produced by
    `plan_consolidation` against a raw list); it's set to the absolute
    settings-file path for pairs produced by
    `detect_consolidation_opportunities`.
    """

    redundant: str
    subsumed_by: str
    source_file: Path | None = None


@dataclass(frozen=True)
class ConsolidationPlan:
    """The outcome of analysing settings files for subsumption.

    For in-memory plans (`plan_consolidation`), `original` and
    `consolidated` describe the input/output lists. For file-walking
    plans (`detect_consolidation_opportunities`), they describe the
    combined union across files.
    """

    original: tuple[str, ...]
    consolidated: tuple[str, ...]
    pairs: tuple[ConsolidationPair, ...]

    @property
    def has_redundancies(self) -> bool:
        return bool(self.pairs)

    @property
    def files_to_modify(self) -> tuple[Path, ...]:
        """Distinct source files that have at least one redundant entry, in stable order."""
        seen: set[Path] = set()
        ordered: list[Path] = []
        for pair in self.pairs:
            if pair.source_file is None:
                continue
            if pair.source_file in seen:
                continue
            seen.add(pair.source_file)
            ordered.append(pair.source_file)
        return tuple(ordered)

    def pairs_in(self, source_file: Path) -> tuple[ConsolidationPair, ...]:
        """Subset of pairs that live in the given file."""
        return tuple(p for p in self.pairs if p.source_file == source_file)


def is_subsumed_by(narrower: str, broader: str) -> bool:
    """True if `broader` strictly subsumes `narrower` (and they're not the same entry).

    Only `Bash(<prefix>:*)`-shape entries act as subsumers. The narrower
    entry must be a `Bash(...)` rule whose inner content starts with
    `<prefix>` followed by a space (`<prefix> <args>`), a colon
    (`<prefix>:<args>`), or matches `<prefix>` exactly.
    """
    if narrower == broader:
        return False

    broader_inner = _strip_bash(broader)
    narrower_inner = _strip_bash(narrower)
    if broader_inner is None or narrower_inner is None:
        return False
    if not broader_inner.endswith(":*"):
        return False

    prefix = broader_inner[:-2]
    if not prefix:
        # `Bash(:*)` is degenerate; skip.
        return False

    if narrower_inner == prefix:
        return True
    if narrower_inner.startswith(prefix + " "):
        return True
    if narrower_inner.startswith(prefix + ":"):
        return True
    return False


def plan_consolidation(allow_list: list[str]) -> ConsolidationPlan:
    """Walk a single allow list (in-memory), identify subsumed entries, return the plan.

    Each entry is checked against every other entry; the first broader
    rule that subsumes it is recorded. Order in `consolidated` preserves
    the original order, minus the removed entries.

    Pairs from this function have `source_file=None`. For file-aware
    plans, use `detect_consolidation_opportunities`.
    """
    pairs: list[ConsolidationPair] = []
    redundant_set: set[str] = set()

    for narrower in allow_list:
        if narrower in redundant_set:
            continue
        for broader in allow_list:
            if narrower == broader:
                continue
            if is_subsumed_by(narrower, broader):
                pairs.append(ConsolidationPair(redundant=narrower, subsumed_by=broader))
                redundant_set.add(narrower)
                break

    consolidated = tuple(e for e in allow_list if e not in redundant_set)
    return ConsolidationPlan(
        original=tuple(allow_list),
        consolidated=consolidated,
        pairs=tuple(pairs),
    )


def detect_consolidation_opportunities(target_root: Path) -> ConsolidationPlan | None:
    """Walk `.claude/settings.json` + `.claude/settings.local.json`, return a file-aware plan.

    Returns None when neither file exists (or both are malformed).
    Subsumption is computed against the combined allow list — a broader
    rule in either file can subsume a narrower rule in either file.

    Each `ConsolidationPair` in the returned plan carries
    `source_file=<absolute path>`. If the same redundant entry appears
    in both files, two pairs are emitted (one per occurrence) so apply
    removes it from each.
    """
    claude_dir = target_root / ".claude"

    # Read each existing settings file. Order matters for stable output:
    # settings.json before settings.local.json.
    file_entries: list[tuple[Path, list[str]]] = []
    for filename in SETTINGS_FILENAMES:
        path = claude_dir / filename
        if not path.is_file():
            continue
        allow = _read_allow_list_from_file(path)
        if allow is None:
            continue
        file_entries.append((path, allow))

    if not file_entries:
        return None

    # Combined (entry, source_file) list — preserves duplicates across files.
    annotated: list[tuple[str, Path]] = []
    for path, entries in file_entries:
        for entry in entries:
            annotated.append((entry, path))

    combined = [entry for entry, _ in annotated]

    # Compute subsumption on the combined list. The raw plan emits one
    # pair per *unique* redundant entry; we then resolve which file(s)
    # the entry lives in.
    raw_plan = plan_consolidation(combined)
    redundant_to_subsumer: dict[str, str] = {p.redundant: p.subsumed_by for p in raw_plan.pairs}

    pairs: list[ConsolidationPair] = []
    for entry, source_file in annotated:
        if entry not in redundant_to_subsumer:
            continue
        pairs.append(
            ConsolidationPair(
                redundant=entry,
                subsumed_by=redundant_to_subsumer[entry],
                source_file=source_file,
            )
        )

    return ConsolidationPlan(
        original=tuple(combined),
        consolidated=tuple(raw_plan.consolidated),
        pairs=tuple(pairs),
    )


def apply_consolidation(target_root: Path, plan: ConsolidationPlan) -> list[Path]:
    """Write the consolidated allow lists back to each affected settings file.

    Groups pairs by source file, then for each file: re-reads, filters
    out the redundant entries, re-writes pretty-printed JSON. Preserves
    every other key (deny list, other settings) untouched.

    Returns the list of files modified, in stable order. A pair with
    `source_file=None` is skipped (it came from `plan_consolidation`
    and has no file to write back to).
    """
    modified: list[Path] = []
    for source_file in plan.files_to_modify:
        redundants = {p.redundant for p in plan.pairs_in(source_file)}
        data = json.loads(source_file.read_text(encoding="utf-8"))
        if "permissions" not in data or not isinstance(data["permissions"], dict):
            data["permissions"] = {}
        old_allow = data["permissions"].get("allow") or []
        new_allow = [e for e in old_allow if e not in redundants]
        data["permissions"]["allow"] = new_allow
        source_file.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        modified.append(source_file)
    return modified


def _strip_bash(entry: str) -> str | None:
    """Return the inner content of `Bash(...)`, or None if `entry` isn't a Bash rule."""
    if entry.startswith("Bash(") and entry.endswith(")"):
        return entry[5:-1]
    return None


def _read_allow_list_from_file(path: Path) -> list[str] | None:
    """Read a settings file, return its `permissions.allow` list, or None if malformed."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return _read_allow_list(data)


def _read_allow_list(data: Any) -> list[str] | None:
    """Extract `permissions.allow` as a list of strings, or None if missing/malformed."""
    if not isinstance(data, dict):
        return None
    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        return None
    allow = permissions.get("allow")
    if not isinstance(allow, list):
        return None
    return [str(entry) for entry in allow]


# --- What the settings merge widens (ADR-065 point 4) ----------------------------

# The project's additions to the merged settings, where an `ask` rule the
# project writes survives the merge (#1454).
PROJECT_SETTINGS_ADDITIONS = ".pkit/adapters/claude-code/settings/project/settings.json"


@dataclass(frozen=True)
class SettingsWidening:
    """What a settings merge adds to `.claude/settings.json`: each allow entry, and
    each top-level key, such as `hooks`, `env` or `sandbox`."""

    allow: tuple[str, ...] = ()
    keys: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.allow or self.keys)


def read_merged_settings(target_root: Path) -> dict[str, Any] | None:
    """`.claude/settings.json` as a mapping, or None where it is missing or is not
    a JSON object. A version transition reads it before and after the merge."""
    path = target_root / ".claude" / SETTINGS_FILENAMES[0]
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return cast("dict[str, Any]", data) if isinstance(data, dict) else None


def settings_widening(
    before: dict[str, Any] | None, after: dict[str, Any] | None
) -> SettingsWidening:
    """The allow entries and the top-level keys *after* holds that *before* does not."""
    if after is None:
        return SettingsWidening()
    held = set(_read_allow_list(before) or [])
    return SettingsWidening(
        allow=tuple(entry for entry in _read_allow_list(after) or [] if entry not in held),
        keys=tuple(key for key in after if before is None or key not in before),
    )


def report_widening(widening: SettingsWidening) -> None:
    """A version transition's lines for each widening the settings merge brings
    (ADR-065 point 4): an added allow entry, or an added top-level key. An `ask`
    rule in the project's additions brings the question back, and the last line
    says so."""
    if not widening:
        return
    click.echo("  The settings merge widens .claude/settings.json:")
    for entry in widening.allow:
        click.echo(f"    {'allow':<12} {entry}")
    for key in widening.keys:
        click.echo(f"    {'key':<12} {key}")
    click.echo(
        "  To be asked before an allowed entry runs, add it as an `ask` rule to "
        f"{PROJECT_SETTINGS_ADDITIONS}, then run `pkit merge`."
    )
