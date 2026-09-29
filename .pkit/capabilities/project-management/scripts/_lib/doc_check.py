"""The doc-check data point — this capability's side of it (DEC-053).

`pkit::work-tracking:doc-check` is the data point this capability defines as
the provider of the `pkit::work-tracking` role (COR-052, COR-053): the
documentation obligations a pull request may owe. Its value is a list of
obligations with no diff in it — a data point takes no parameter (COR-052
point 6) — and `check-doc-mapping` applies it to a pull request's diff.

Three things live here, shared by the filler and the check:

- **The mapping as obligations.** `mapping_obligations` turns the project's
  code-to-doc mapping (`code_path_to_doc_mapping.rules` in `project/config.yaml`,
  DEC-015) into the point's entries, one per well-formed rule, keyed by the
  rule. `fill-doc-check` prints them: it is the point's always-included
  default filler, supplied as this capability's own contribution because the
  mapping is the project's configuration, which a static `default` in package
  metadata cannot hold.
- **The per-source enforcement settings** (DEC-053 point 3). The mapping keeps
  its own setting, `code_path_to_doc_mapping.enforce`; every other source is set
  under `doc_check.sources.<source>` — `advisory` (the default) or `enforcing`.
- **Reading the resolved point.** The check reads the point through the
  backbone's read command, `pkit connections resolve <point> --json`, rather
  than importing the backbone: the resolved value is the union of this
  capability's mapping obligations and whatever else fills the point (a
  documentation capability's contribution, the project's own filler file),
  after the project's removal overrides.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

POINT = "pkit::work-tracking:doc-check"
POINT_VERSION = 1

# The verb that fills the point with the mapping's obligations.
FILLER_VERB = "fill-doc-check"

# An obligation's fields (the companion schema, `schemas/doc-check.schema.json`).
MAPPING_SOURCE = "mapping"
MAPPING_REASON = "mapped-path-changed"
MAPPING_ID_PREFIX = "mapping:"

# The configuration: the mapping (DEC-015) and the other sources' settings.
MAPPING_KEY = "code_path_to_doc_mapping"
SETTINGS_KEY = "doc_check"
SOURCES_KEY = "sources"
ADVISORY = "advisory"
ENFORCING = "enforcing"
SETTINGS = (ADVISORY, ENFORCING)


# --- the mapping as obligations (the filler's side) ----------------------------


def mapping_obligations(rules: Any) -> list[dict[str, Any]]:
    """The point's entries for the mapping `rules`, in the rules' order.

    A rule that names no code pattern or no document list is skipped — the
    mapping check always skipped it, and the config schema refuses it. Each
    obligation is keyed by its rule: `mapping:<code pattern>`, and
    `mapping:<code pattern>#<n>` for the n-th rule repeating a pattern, so two
    rules on one pattern stay two obligations, each met on its own.
    """
    if not isinstance(rules, list):
        return []
    obligations: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for rule in rules:
        if not isinstance(rule, Mapping):
            continue
        code = str(rule.get("code", ""))
        documents = rule.get("docs")
        if not code or not isinstance(documents, list) or not documents:
            continue
        seen[code] = seen.get(code, 0) + 1
        suffix = f"#{seen[code]}" if seen[code] > 1 else ""
        obligations.append(
            {
                "id": f"{MAPPING_ID_PREFIX}{code}{suffix}",
                "source": MAPPING_SOURCE,
                "reason": MAPPING_REASON,
                "code": code,
                "documents": [str(d) for d in documents],
            }
        )
    return obligations


def envelope(config: Mapping[str, Any]) -> dict[str, Any]:
    """The filler envelope `fill-doc-check --json` prints (COR-052 point 6)."""
    mapping = config.get(MAPPING_KEY) or {}
    rules = mapping.get("rules") if isinstance(mapping, Mapping) else None
    return {"schema_version": POINT_VERSION, "value": mapping_obligations(rules)}


# --- the per-source settings -----------------------------------------------------


def source_settings(config: Mapping[str, Any]) -> tuple[dict[str, str], str | None]:
    """`(settings, problem)`: each contributed source's setting, and what is wrong
    with the block when something is. An absent block is no settings — every
    contributed source advisory."""
    block = config.get(SETTINGS_KEY)
    if block is None:
        return {}, None
    if not isinstance(block, Mapping):
        return {}, f"`{SETTINGS_KEY}` must be a mapping holding `{SOURCES_KEY}:` (DEC-053)."
    sources = block.get(SOURCES_KEY) or {}
    if not isinstance(sources, Mapping):
        return {}, (
            f"`{SETTINGS_KEY}.{SOURCES_KEY}` must map each source to "
            f"`{ADVISORY}` or `{ENFORCING}` (DEC-053)."
        )
    settings: dict[str, str] = {}
    for source, setting in sources.items():
        if source == MAPPING_SOURCE:
            return {}, (
                f"`{SETTINGS_KEY}.{SOURCES_KEY}.{MAPPING_SOURCE}` is not a setting: the "
                f"mapping keeps its own, `{MAPPING_KEY}.enforce` (DEC-053)."
            )
        if setting not in SETTINGS:
            return {}, (
                f"`{SETTINGS_KEY}.{SOURCES_KEY}.{source}` is {setting!r}; it is "
                f"`{ADVISORY}` or `{ENFORCING}` (DEC-053)."
            )
        settings[str(source)] = str(setting)
    return settings, None


def setting_of(settings: Mapping[str, str], source: str) -> str:
    """A contributed source's setting: advisory unless the project enforces it."""
    return settings.get(source, ADVISORY)


# --- reading the resolved point (the check's side) --------------------------------


class PointUnreadable(Exception):
    """The backbone's read command gave no document to read."""


@dataclass(frozen=True)
class ResolvedPoint:
    """The resolved point, as `pkit connections resolve --json` prints it."""

    resolved: bool
    why: str = ""
    # (id, origin, obligation) per entry, in the point's order.
    entries: tuple[tuple[str, str, Mapping[str, Any]], ...] = ()
    removals: tuple[Mapping[str, Any], ...] = ()
    fillers: tuple[Mapping[str, Any], ...] = ()

    @property
    def inert(self) -> list[Mapping[str, Any]]:
        return [f for f in self.fillers if f.get("state") == "inert"]


Runner = Callable[..., subprocess.CompletedProcess[str]]


def read_point(run: Runner = subprocess.run) -> ResolvedPoint:
    """Read the resolved point through `pkit connections resolve --json`.

    The command exits 1 on an unresolved point and still prints its document,
    so the document decides, not the exit code. No document at all — `pkit`
    absent, a backbone without the command, a crash — raises PointUnreadable.
    """
    argv = ["pkit", "connections", "resolve", POINT, "--json"]
    try:
        proc = run(argv, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise PointUnreadable("`pkit` is not on PATH") from exc
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if not isinstance(document, Mapping) or "resolved" not in document:
        detail = (proc.stderr or "").strip().splitlines()
        raise PointUnreadable(
            f"`{' '.join(argv)}` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else "")
        )
    return parse_point(document)


def parse_point(document: Mapping[str, Any]) -> ResolvedPoint:
    """The `pkit connections resolve --json` document as a ResolvedPoint."""
    if document.get("defined") is False:
        return ResolvedPoint(resolved=False, why=f"it is not defined: {document.get('why', '')}")
    entries = tuple(
        (str(e.get("id", "")), str(e.get("origin", "")), e.get("value") or {})
        for e in document.get("entries") or []
        if isinstance(e, Mapping)
    )
    return ResolvedPoint(
        resolved=bool(document.get("resolved")),
        why=str(document.get("why") or ""),
        entries=entries,
        removals=tuple(r for r in document.get("removals") or [] if isinstance(r, Mapping)),
        fillers=tuple(f for f in document.get("fillers") or [] if isinstance(f, Mapping)),
    )


@dataclass(frozen=True)
class Obligations:
    """The resolved point's obligations, by how each is met."""

    mapping: list[Mapping[str, Any]]
    contributed: list[Mapping[str, Any]]
    problems: list[str]


def split(point: ResolvedPoint, own: str) -> Obligations:
    """Mapping obligations and contributed ones. Only `own` — this capability's
    filler — supplies mapping obligations: one from any other origin would be
    met by a `## Doc impact` line and ruled by the mapping's setting, which a
    contributor may not claim, so it is a problem, never an obligation."""
    mapping: list[Mapping[str, Any]] = []
    contributed: list[Mapping[str, Any]] = []
    problems: list[str] = []
    for entry_id, origin, obligation in point.entries:
        if obligation.get("source") != MAPPING_SOURCE:
            contributed.append(obligation)
        elif origin == own:
            mapping.append(obligation)
        else:
            problems.append(
                f"entry {entry_id!r} from {origin} claims the `{MAPPING_SOURCE}` source, "
                f"which only {own}'s own filler supplies"
            )
    return Obligations(mapping, contributed, problems)


def removed(point: ResolvedPoint) -> list[tuple[str, str]]:
    """`(id, reason)` of each removal override that removed an obligation."""
    return [
        (str(r.get("id", "")), str(r.get("reason", "")))
        for r in point.removals
        if r.get("removed_from")
    ]


def sources_of(obligations: Sequence[Mapping[str, Any]]) -> list[str]:
    """The sources the obligations come from, sorted, each once."""
    return sorted({str(o.get("source", "")) for o in obligations})
