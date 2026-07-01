#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "jsonschema>=4.0",
# ]
# ///
"""Project-management capability — adopt-existing (inventory + draft, never apply).

The brownfield onboarding ceremony, per
[project-management:DEC-037-adoption-ceremony] §1. It is the brownfield analogue
of ``bootstrap``: where greenfield ``bootstrap`` *creates* the kit's own
substrate additively, brownfield ``adopt-existing`` *reads the existing
substrate and DRAFTS the binding* a brownfield adopter would otherwise
hand-author against hundreds of existing issues.

The load-bearing invariant (DEC-037 §1)
---------------------------------------
**It mutates nothing.** It inventories the live tracker through ``gh`` READS
only — ``gh label list``, ``gh issue list``, ``gh project field-list`` / ``view``,
``gh api graphql`` queries — and never writes the substrate-map, never edits a
label / field / issue, never installs anything. Output is a DRAFT
``substrate-map.yaml`` (to stdout or a clearly-named draft file the human moves
into place themselves) plus an AUDIT REPORT. The human owns acceptance.

Every ``gh`` call this script issues is a read. There is no write path here at
all, so the ADR-031 sole-constructor guard finds no covered substrate write to
flag (this script constructs none); the end-to-end mutate-nothing test asserts
only read ``gh`` calls are ever issued.

Why draft-not-apply, and the honest bound on it (DEC-037 §1)
-----------------------------------------------------------
An inferred substrate-map is a *hypothesis* about conventions a human
established implicitly. Applying it silently and then operating on a mis-inferred
binding would mis-map an entire corpus — so the human owns acceptance. But
draft-not-apply guards only the *map-write*: it does NOT make the map and the
later corpus back-fill (``back-fill.py``, computed THROUGH the accepted map) two
independent safety layers. They share the inferred map as a **common-mode
input** — one root inference confirmed twice, not defence-in-depth. The
mitigation DEC-037 §1 mandates, and the reason the audit report is the
load-bearing deliverable: **for each inferred binding, show the evidence it was
inferred from** (the labels / prefixes / states observed, with coverage signals)
so the human's acceptance is INFORMED, not reflexive.

The inference heuristics (corpus shape → candidate binding)
-----------------------------------------------------------
Each conceptual axis (DEC-036) is mapped onto the best-fitting existing
substrate, or marked ``unsupported`` when none fits:

  * **priority → label remap** — when native priority labels (``P0``/``P1``/``P2``,
    or ``priority:high`` etc.) are observed in use, draft a ``label`` binding
    remapping the kit values (High/Medium/Low) onto them. Cite the labels seen
    and their issue-usage coverage.
  * **type → title-prefix** — when ``[Task]`` / ``[Epic]`` / ``[Feature]``-style
    bracket prefixes are observed across issue titles, draft a ``title-prefix``
    binding. Cite the prefixes seen and how many sampled issues carry each.
  * **state → derive** — always draftable from the universal open/closed
    substrate plus a ``Blocked``-style label convention (DEC-033 detector swap,
    reduced state set). Cite whether a blocked-style label was actually observed.
  * **workstream → label remap | unsupported** — when ``workstream:*``-style
    labels are observed, draft a ``label`` binding; otherwise ``unsupported``
    (the AUJ case — no workstream encoding).

Inference reads ONLY what the reads returned; it never guesses a label/prefix it
did not see. Coverage signals (``n/m sampled issues``) accompany each binding so
the human can judge confidence.

Schema conformance self-check (DEC-037 §1 / the substrate-map schema)
---------------------------------------------------------------------
The drafted map is validated against ``substrate-map.schema.json`` before it is
emitted; the audit report states whether the draft validates, and emits each
schema error if not, so the human is not handed a draft that would fail
``pkit schemas validate``.

Self-contained via PEP 723 inline metadata; run via
  uv run --script .pkit/capabilities/project-management/scripts/adopt-existing.py
Or via the dispatcher (per COR-021):
  pkit project-management adopt-existing

Exit codes:
  0  inventory + draft + audit produced (the normal path, whatever the draft's
     shape — an all-`unsupported` draft is a valid brownfield outcome, not a
     failure)
  2  usage error (capability not found); or the inventory could not be read at
     all (`gh` not on PATH / repo inaccessible / auth invalid) so there is
     nothing to infer from. No write occurs in any case.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402

CAPABILITY_NAME = "project-management"

# How many issues to sample when inferring title-prefix / priority-label / state
# conventions. A sample, not the whole corpus — inference reads a convention, not
# every issue; the sample size is reported so the coverage signal is honest. Kept
# in step with pre-check's title-prefix sample limit so the two agree on "sample".
DEFAULT_SAMPLE_LIMIT = 200

# The cap on `gh label list`. A repo rarely has this many labels; if it does, the
# read is truncated and the inventory flags it (parallel to the issue-sample
# truncation honesty) rather than silently reporting a partial label set as whole.
LABELS_LIMIT = 1000

# The kit's own per-axis methodology values the draft remaps FROM (DEC-036). The
# remap maps these kit values onto the adopter's observed substrate.
PRIORITY_KIT_VALUES = ("High", "Medium", "Low")

# Recognised native priority-label shapes, highest→lowest, each a list of
# case-insensitive label-name candidates. The first observed candidate in each
# tier wins, so a repo using `P0/P1/P2` and a repo using `priority:high/...` both
# infer cleanly. Inference NEVER invents a tier it did not observe.
#
# IMPORTANT — the tier ORDER below is ASSUMED, not detected. We read the
# conventional `P0`=highest-urgency / `P2`=lowest-urgency direction (and the
# explicit `high`/`medium`/`low` words). Label NAMES and their usage counts carry
# no urgency ordering — a repo whose convention inverts this (`P0`=lowest) is
# indistinguishable from the corpus alone. So the inference draws the mapping in
# the conventional direction and the audit evidence flags it as assumed; the
# human must confirm the direction matches their convention (see `_infer_priority`).
#
# The kit-shaped `priority:<value>` candidates are built through the axis-label
# sole constructor (`axis_labels.label`) rather than spelled inline — both because
# that is the one legitimate constructor of an `<axis>:<value>` string (ADR-026 /
# the seam guard) and because it keeps the candidate names honest to the kit's own
# encoding. These are still only MATCH candidates against the adopter's observed
# labels; adopt-existing writes none of them.
def _priority_candidates(*kit_values: str) -> tuple[str, ...]:
    return tuple(axis_labels.label("priority", v) for v in kit_values)


PRIORITY_LABEL_TIERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("High", ("P0", *_priority_candidates("high"), "high priority")),
    ("Medium", ("P1", *_priority_candidates("medium"), "medium priority")),
    ("Low", ("P2", *_priority_candidates("low"), "low priority")),
)

# A bracket title-prefix, e.g. `[Task] do the thing` → captures `Task`.
_BRACKET_PREFIX_RE = re.compile(r"^\[([^\]]+)\]\s")

# Kit type values keyed by the lower-cased prefix text the adopter uses, so an
# observed `[Task]` maps to kit value `task`. Only prefixes whose lower-cased text
# matches a kit type value are remapped; an unrecognised prefix is reported as
# observed-but-unmapped (the human decides), never silently dropped or invented.
TYPE_KIT_VALUES = ("epic", "umbrella", "feature", "task")

# The conventional blocked-label name the state derive predicate reads (the AUJ
# `Blocked` label, ADR-026 §5). Centralised in the seam; mirrored here for the
# inventory probe so the audit can report whether it was actually observed.
BLOCKED_LABEL_NAME = axis_labels.BLOCKED_LABEL_NAME


# ===== inventory (reads only) ============================================


@dataclass
class LabelObservation:
    """One label observed on the tracker + how many sampled issues carry it."""

    name: str
    issue_usage: int  # number of sampled issues carrying this label


@dataclass
class PrefixObservation:
    """One title-prefix observed across sampled issue titles + its frequency."""

    prefix: str  # the bracketed text, e.g. "Task" (no brackets)
    count: int   # sampled issues whose title carries this prefix


@dataclass
class Inventory:
    """The live tracker's observed shape — the raw evidence inference reads.

    Every field is populated from a ``gh`` READ; nothing here is inferred or
    written. ``read_ok`` is False when the inventory could not be read at all
    (``gh`` missing / repo inaccessible) — the caller refuses with exit 2 rather
    than infer from nothing.
    """

    read_ok: bool
    labels: list[LabelObservation] = field(default_factory=list)
    title_prefixes: list[PrefixObservation] = field(default_factory=list)
    open_count: int = 0
    closed_count: int = 0
    sampled_issue_count: int = 0
    sample_truncated: bool = False
    labels_truncated: bool = False
    has_blocked_label: bool = False
    milestones_in_use: list[str] = field(default_factory=list)
    board_fields: list[dict[str, Any]] = field(default_factory=list)
    has_board: bool = False
    projects_v2_node_id: str | None = None


def take_inventory(
    config: dict[str, Any], *, sample_limit: int
) -> Inventory:
    """Inventory the live tracker through ``gh`` READS only (DEC-037 §1).

    Pulls: the repo's labels (``gh label list``); a sample of issues, open and
    closed, with their titles + labels + milestones (``gh issue list``); and — if
    a board is configured — its Projects-v2 fields (``gh project field-list``).
    From the issue sample it derives title-prefix frequencies, per-label issue
    usage, open/closed counts, the blocked-label convention, and milestone usage.

    Every call is a read. A failure to list labels OR sample issues at all (the
    minimum needed to infer anything) yields ``read_ok=False`` — the caller
    refuses rather than draft from an empty inventory.
    """
    labels_raw = _read_labels(config)
    issues = _read_issue_sample(config, limit=sample_limit)
    if labels_raw is None and issues is None:
        return Inventory(read_ok=False)

    labels_truncated = labels_raw is not None and len(labels_raw) == LABELS_LIMIT
    labels_raw = labels_raw or []
    issues = issues or []

    # Per-label issue usage across the sample (how many sampled issues carry it).
    usage: dict[str, int] = {name: 0 for name in labels_raw}
    open_count = 0
    closed_count = 0
    prefix_counts: dict[str, int] = {}
    milestones: dict[str, int] = {}
    for issue in issues:
        for lbl in _issue_label_names(issue):
            usage[lbl] = usage.get(lbl, 0) + 1
        state = str(issue.get("state", "")).upper()
        if state == "CLOSED":
            closed_count += 1
        else:
            open_count += 1
        prefix = _title_prefix(str(issue.get("title", "")))
        if prefix is not None:
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
        ms = issue.get("milestone")
        if isinstance(ms, dict):
            title = ms.get("title")
            if isinstance(title, str) and title:
                milestones[title] = milestones.get(title, 0) + 1

    label_observations = [
        LabelObservation(name=name, issue_usage=usage.get(name, 0))
        for name in labels_raw
    ]
    prefix_observations = sorted(
        (PrefixObservation(prefix=p, count=c) for p, c in prefix_counts.items()),
        key=lambda o: (-o.count, o.prefix),
    )
    has_blocked = _observed_blocked_label(labels_raw)

    board_fields, has_board = _read_board_fields(config)
    project_node_id = _read_project_node_id(config) if has_board else None

    return Inventory(
        read_ok=True,
        labels=label_observations,
        title_prefixes=prefix_observations,
        open_count=open_count,
        closed_count=closed_count,
        sampled_issue_count=len(issues),
        sample_truncated=len(issues) == sample_limit,
        labels_truncated=labels_truncated,
        has_blocked_label=has_blocked,
        milestones_in_use=sorted(milestones),
        board_fields=board_fields,
        has_board=has_board,
        projects_v2_node_id=project_node_id,
    )


def _read_labels(config: dict[str, Any]) -> list[str] | None:
    """The repo's label names via ``gh label list`` (a READ). ``None`` on failure.

    ``gh label list`` caps at ``--limit``; we request ``LABELS_LIMIT``. The caller
    flags truncation when the returned list FILLS that limit (``len == LABELS_LIMIT``
    in ``take_inventory``) — the same ``== limit`` detection the issue sample uses,
    so a partial label read is signalled rather than silently reported as the whole
    label set. The returned list is the label NAMES.
    """
    try:
        proc = gh_run(
            ["gh", "label", "list", "--limit", str(LABELS_LIMIT), "--json", "name"],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return [
        str(entry["name"])
        for entry in data
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    ]


def _read_issue_sample(
    config: dict[str, Any], *, limit: int
) -> list[dict[str, Any]] | None:
    """A sample of issues (open + closed) with title/labels/milestone/state.

    A READ (``gh issue list --state all``). ``None`` on failure. The sample is
    bounded by ``limit``; the caller flags truncation when the sample fills it, so
    the coverage signal is never silently capped.
    """
    try:
        proc = gh_run(
            [
                "gh", "issue", "list",
                "--state", "all",
                "--limit", str(limit),
                "--json", "number,title,labels,milestone,state",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def _read_board_fields(
    config: dict[str, Any]
) -> tuple[list[dict[str, Any]], bool]:
    """The configured Projects-v2 board's fields + their options (a READ).

    Returns ``(fields, has_board)``. ``has_board`` is False (and ``fields`` empty)
    when no board is configured (``has_projects_v2_board`` falsey /
    ``projects_v2_board_id`` unset) or the field-list read fails — a board is
    optional context for the inventory, not a precondition. Each field carries its
    ``name`` and (for single-selects) its ``options`` so the human can see which
    board field might carry an axis (e.g. workstream).
    """
    if not config.get("has_projects_v2_board"):
        return [], False
    board_number = config.get("projects_v2_board_id")
    if board_number is None:
        return [], False
    args = ["gh", "project", "field-list", str(board_number), "--format", "json"]
    owner = _resolve_owner(config)
    if owner:
        args += ["--owner", owner]
    try:
        proc = gh_run(args, config, check=False)
    except FileNotFoundError:
        return [], True
    if proc.returncode != 0:
        return [], True
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], True
    fields = payload.get("fields") if isinstance(payload, dict) else payload
    if not isinstance(fields, list):
        return [], True
    out = [f for f in fields if isinstance(f, dict)]
    return out, True


def _read_project_node_id(config: dict[str, Any]) -> str | None:
    """The configured board's Projects-v2 project node id via ``gh project view`` (a READ).

    Resolves board NUMBER → node id the way ``create-issue`` caches and
    ``back-fill`` reads. A READ only — DEC-037 §1's mutate-nothing invariant holds:
    adopt-existing RECOMMENDS caching this in config (surfaced in the audit +
    JSON), it never writes config itself. The human moves the recommendation into
    place, the same draft-not-apply posture as the substrate-map. Returns ``None``
    when no board is configured or the read fails.
    """
    if not config.get("has_projects_v2_board"):
        return None
    board_number = config.get("projects_v2_board_id")
    if board_number is None:
        return None
    owner = _resolve_owner(config)
    args = ["gh", "project", "view", str(board_number), "--format", "json"]
    if owner:
        args += ["--owner", owner]
    try:
        proc = gh_run(args, config, check=False)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    node_id = payload.get("id") if isinstance(payload, dict) else None
    return node_id if isinstance(node_id, str) and node_id else None


def _resolve_owner(config: dict[str, Any]) -> str | None:
    """The owner to scope a board lookup to: configured ``gh.default_owner``, else
    None (``gh project`` then uses its own default-owner behaviour)."""
    gh_block = config.get("gh") if isinstance(config, dict) else None
    if isinstance(gh_block, dict):
        owner = gh_block.get("default_owner")
        if isinstance(owner, str) and owner:
            return owner
    return None


def _issue_label_names(issue: dict[str, Any]) -> list[str]:
    """The label names on one ``gh issue list`` JSON record (robust to shape)."""
    labels = issue.get("labels")
    if not isinstance(labels, list):
        return []
    names: list[str] = []
    for lbl in labels:
        if isinstance(lbl, dict) and isinstance(lbl.get("name"), str):
            names.append(lbl["name"])
        elif isinstance(lbl, str):
            names.append(lbl)
    return names


def _title_prefix(title: str) -> str | None:
    """The bracketed prefix text of a title (``[Task] x`` → ``Task``), or None."""
    m = _BRACKET_PREFIX_RE.match(title)
    return m.group(1) if m else None


def _observed_blocked_label(label_names: list[str]) -> bool:
    """True when a ``Blocked``-style label is among the observed labels.

    Case-insensitive exact match on the conventional name the state derive
    predicate reads (ADR-026 §5) — the same name the live derive read uses, so the
    audit's "blocked label observed" claim matches what the binding would read.
    """
    target = BLOCKED_LABEL_NAME.casefold()
    return any(name.casefold() == target for name in label_names)


# ===== inference + audit (corpus shape → drafted bindings + evidence) =====


@dataclass
class AxisInference:
    """One axis's inferred binding + the evidence it was inferred from.

    ``binding`` is the drafted substrate-map fragment for this axis (the value
    placed under ``axes.<axis>``), or ``None`` when the axis has no axis-level
    binding to draft (state's binding lives under the axis too, so state still
    carries one). ``evidence`` is the human-readable "why" — the load-bearing
    DEC-037 §1 audit line. ``confidence`` is a coarse signal (``high`` / ``low`` /
    ``none``) derived from coverage, surfaced so the human can triage which
    inferences to scrutinise.
    """

    axis: str
    binding: dict[str, Any] | None
    evidence: str
    confidence: str  # "high" | "low" | "none"


@dataclass
class Draft:
    """The drafted substrate-map + the per-axis audit + the hierarchy inference."""

    inferences: list[AxisInference]
    hierarchy: str
    hierarchy_evidence: str

    def substrate_map(self) -> dict[str, Any]:
        """Assemble the drafted ``substrate-map.yaml`` document (DEC-036 schema).

        An axis with a binding lands under ``axes:`` with that binding. An axis the
        inference EVALUATED AND REJECTED (no fitting substrate) lands as an explicit
        ``{"unsupported": true}`` rather than being omitted (G5): absent ≡
        unsupported is still the load-bearing rule, but writing it explicitly makes
        the committed map SELF-DOCUMENTING — once the human discards the stdout
        audit, the artifact still records "considered this axis and rejected it,"
        distinguishing it from "never looked." Schema-valid either way (the
        ``unsupported: true`` oneOf branch). ``hierarchy:`` rides at the top level
        beside ``axes:`` (it is a parent-ref mode, not a label-encoded axis).
        """
        axes: dict[str, Any] = {}
        for inf in self.inferences:
            if inf.binding is not None:
                axes[inf.axis] = inf.binding
            else:
                axes[inf.axis] = {"unsupported": True}
        doc: dict[str, Any] = {
            "schema_version": 1,
            "pkit_schema": f"{CAPABILITY_NAME}:substrate-map",
            "hierarchy": self.hierarchy,
            "axes": axes,
        }
        return doc


def infer_draft(inventory: Inventory) -> Draft:
    """Infer a candidate substrate-map from the inventory, with per-axis evidence.

    Each axis is mapped onto the best-fitting observed substrate, or marked
    unsupported (drafted as an explicit ``unsupported: true``, G5) when none fits.
    Inference reads ONLY the inventory's
    observations — it never invents a label/prefix it did not see. The returned
    :class:`Draft` carries both the bindings and the DEC-037 §1 evidence.
    """
    inferences = [
        _infer_priority(inventory),
        _infer_type(inventory),
        _infer_state(inventory),
        _infer_workstream(inventory),
    ]
    hierarchy, hierarchy_evidence = _infer_hierarchy(inventory)
    return Draft(
        inferences=inferences,
        hierarchy=hierarchy,
        hierarchy_evidence=hierarchy_evidence,
    )


def _infer_priority(inventory: Inventory) -> AxisInference:
    """priority → native priority-label remap, or unsupported.

    Walks the priority-label tiers (P0/P1/P2, priority:high/..., …); for each kit
    value (High/Medium/Low) takes the first observed candidate label. A remap is
    drafted only over the tiers actually observed — a partial set (only P0/P1
    seen) drafts a partial remap and the evidence says so. None observed →
    unsupported (no binding), echoing any observed-but-unrecognised priority-ish
    labels so the human can tell "no priority axis" from "matcher didn't know my
    shape" (G2).

    Tier ORDERING is ASSUMED, never detected: label names + usage counts carry no
    urgency direction, so the remap is drawn in the conventional
    P0=High/P2=Low reading and the evidence flags that the human must confirm the
    direction (mirroring `_infer_hierarchy`'s honest hedge for the same kind of
    unverifiable-from-corpus inference). Confidence is therefore NEVER `high` —
    even a full P0/P1/P2 sweep is ordering-unverified, capped at `low`.
    """
    observed = {name.casefold(): obs for name, obs in _label_index(inventory)}
    remap: dict[str, str] = {}
    cited: list[str] = []
    for kit_value, candidates in PRIORITY_LABEL_TIERS:
        for cand in candidates:
            obs = observed.get(cand.casefold())
            if obs is not None:
                remap[kit_value] = obs.name
                cited.append(f"{kit_value}→{obs.name} ({obs.issue_usage} issue(s))")
                break
    if not remap:
        unmatched = _unmatched_priorityish_labels(inventory)
        echo = (
            " Observed labels that LOOK priority-ish but matched no recognised "
            "shape (P0/P1/P2 or priority:* or '<level> priority'): "
            + ", ".join(unmatched)
            + " — if one IS your priority axis, map it by hand."
            if unmatched
            else ""
        )
        return AxisInference(
            axis="priority",
            binding=None,
            evidence=(
                "no native priority labels (P0/P1/P2 or priority:* style) "
                "observed among the repo's labels — priority left UNSUPPORTED "
                "(written explicitly as `unsupported: true`; classification goes "
                "partial/advisory)."
                + echo
            ),
            confidence="none",
        )
    binding: dict[str, Any] = {"label": {"remap": remap}}
    # Seed a default from the median tier when present, else the first mapped.
    default_value = remap.get("Medium") or next(iter(remap.values()))
    binding["default"] = default_value
    coverage_note = (
        "all three tiers observed"
        if len(remap) == len(PRIORITY_KIT_VALUES)
        else (
            "PARTIAL — not all three tiers observed; the human should confirm "
            "the missing tier(s)."
        )
    )
    return AxisInference(
        axis="priority",
        binding=binding,
        evidence=(
            "priority→label-remap inferred from native priority labels in use: "
            + ", ".join(cited)
            + f". default seeded to `{default_value}`. "
            + coverage_note
            + " ORDERING ASSUMED, NOT DETECTED: the urgency direction (High←→Low) "
            "is read from the conventional P0=High / P2=Low convention, NOT "
            "detected from the corpus — label names and usage counts carry no "
            "ordering. If your convention is inverted (e.g. P0 = LOWEST urgency), "
            "this remap is upside-down; confirm the direction matches yours before "
            "accepting. (Confidence stays below `high` precisely because ordering "
            "is unverifiable from labels alone.)"
        ),
        confidence="low",
    )


def _unmatched_priorityish_labels(inventory: Inventory) -> list[str]:
    """Observed labels that read as priority-ish yet matched no recognised tier.

    Surfaced in the UNSUPPORTED evidence (G2) so a human staring at a repo full of
    `priority/high` / `prio:high` / `severity:1` sees the labels the matcher saw
    and passed over — distinguishing "no priority axis" from "unrecognised shape."
    A label is priority-ish if its name contains a priority/severity word; the kit
    `priority:*` shapes are already matched, so anything here is genuinely
    unrecognised. Capped to keep the report readable.
    """
    matched = {
        cand.casefold()
        for _kit, cands in PRIORITY_LABEL_TIERS
        for cand in cands
    }
    hints = ("priorit", "prio", "severit", "urgen")
    out: list[str] = []
    for name, obs in _label_index(inventory):
        folded = name.casefold()
        if folded in matched:
            continue
        if any(h in folded for h in hints):
            out.append(f"{name} ({obs.issue_usage} issue(s))")
    return out[:8]


def _infer_type(inventory: Inventory) -> AxisInference:
    """type → title-prefix remap, or unsupported.

    Reads the observed bracket prefixes whose lower-cased text matches a kit type
    value (``[Task]`` → ``task``). A prefix that matches no kit type is reported as
    observed-but-unmapped (the human decides whether it is a type) and not put in
    the remap. None of the observed prefixes matching a kit type → unsupported.
    """
    matched: dict[str, str] = {}  # kit value -> "[Prefix]"
    cited: list[str] = []
    unmapped: list[str] = []
    for obs in inventory.title_prefixes:
        kit_value = obs.prefix.casefold()
        if kit_value in TYPE_KIT_VALUES:
            matched[kit_value] = f"[{obs.prefix}]"
            cited.append(f"{kit_value}→[{obs.prefix}] ({obs.count} title(s))")
        else:
            unmapped.append(f"[{obs.prefix}] ({obs.count} title(s))")
    if not matched:
        seen = (
            "observed prefixes matched no kit type value: "
            + ", ".join(unmapped)
            if unmapped
            else "no bracket title-prefixes observed in the sampled titles"
        )
        return AxisInference(
            axis="type",
            binding=None,
            evidence=(
                f"type left UNSUPPORTED (written explicitly as `unsupported: "
                f"true`) — {seen}. The human may "
                "still map one of the observed prefixes by hand if it IS a type."
            ),
            confidence="none",
        )
    # Modulate confidence by COVERAGE — the fraction of sampled issues carrying a
    # MAPPED prefix (G7). A taxonomy in real use covers most issues; a coincidental
    # bracket marker (e.g. `[Feature] request:` used as a changelog tag) covers a
    # handful. Mirrors priority's coverage-driven confidence: thin coverage → `low`
    # confidence + an evidence note that the prefix may be coincidental, not a type.
    mapped_issue_count = sum(
        o.count for o in inventory.title_prefixes
        if o.prefix.casefold() in matched
    )
    sampled = inventory.sampled_issue_count
    coverage_frac = (mapped_issue_count / sampled) if sampled else 0.0
    LOW_COVERAGE_THRESHOLD = 0.10  # <10% of sampled issues carry a mapped prefix
    low_coverage = coverage_frac < LOW_COVERAGE_THRESHOLD
    evidence = (
        "type→title-prefix inferred from bracket prefixes in use: "
        + ", ".join(cited)
        + f". coverage: {mapped_issue_count}/{sampled} sampled issue(s) carry a "
        + f"mapped prefix ({coverage_frac:.0%})."
    )
    if low_coverage:
        evidence += (
            " LOW COVERAGE — only a small fraction of sampled issues carry these "
            "prefixes, so they may be a COINCIDENTAL bracket convention (a "
            "changelog marker, a one-off tag) rather than a type taxonomy. Confirm "
            "the prefixes are genuinely a type axis before accepting."
        )
    if unmapped:
        evidence += (
            " Also observed but NOT mapped (no matching kit type value): "
            + ", ".join(unmapped)
            + " — the human decides whether any is a type."
        )
    return AxisInference(
        axis="type",
        binding={"title-prefix": {"remap": matched}},
        evidence=evidence,
        confidence="low" if low_coverage else "high",
    )


def _infer_state(inventory: Inventory) -> AxisInference:
    """state → derive from open/closed (+ a Blocked label), the DEC-033 swap.

    Always draftable: every GitHub tracker has the open/closed substrate, so state
    derives to the reduced set (open / blocked / done). The ``blocked`` condition
    depends on a ``Blocked``-style label; the evidence states whether one was
    actually observed (so the human knows whether the blocked arm will ever fire).
    """
    blocked_condition = (
        f"issue is open and labelled {BLOCKED_LABEL_NAME}"
    )
    binding = {
        "derive": {
            "from": "open-closed",
            "states": {
                "open": f"issue is open and not labelled {BLOCKED_LABEL_NAME}",
                "blocked": blocked_condition,
                "done": "issue is closed",
            },
        }
    }
    if inventory.has_blocked_label:
        evidence = (
            "state→derive from open/closed + a blocked label (DEC-033 detector "
            f"swap). A `{BLOCKED_LABEL_NAME}` label WAS observed among the repo's "
            f"labels, so the `blocked` arm is live. open/closed counts in sample: "
            f"{inventory.open_count} open, {inventory.closed_count} closed. The "
            "reduced state set collapses Todo/Backlog/In-progress to one `open`."
        )
        confidence = "high"
    else:
        evidence = (
            "state→derive from open/closed (DEC-033 detector swap). NO "
            f"`{BLOCKED_LABEL_NAME}` label was observed, so the `blocked` arm will "
            "never fire as drafted — `open`/`done` derive cleanly from "
            f"open/closed ({inventory.open_count} open, {inventory.closed_count} "
            "closed in sample). The human may drop the `blocked` state or point it "
            "at a different label."
        )
        confidence = "low"
    return AxisInference(
        axis="state", binding=binding, evidence=evidence, confidence=confidence
    )


def _infer_workstream(inventory: Inventory) -> AxisInference:
    """workstream → label remap when workstream:* labels are seen, else unsupported.

    The AUJ case is unsupported (no workstream encoding). When ``workstream:*``
    labels ARE observed, draft a label binding mapping each observed slug onto its
    own label (an identity-ish remap the human refines). The board-field case
    (workstream on a Projects-v2 single-select) is surfaced in the report as
    context but NOT drafted as a binding — the substrate-map has no `field:` kind
    (DEC-037 §3 names that deferred), so a field-carried workstream is recorded for
    the human, not bound.
    """
    ws_labels = [
        obs for name, obs in _label_index(inventory)
        if name.casefold().startswith("workstream:")
    ]
    if ws_labels:
        remap = {
            obs.name.split(":", 1)[1]: obs.name
            for obs in ws_labels
            if ":" in obs.name
        }
        if remap:
            cited = ", ".join(
                f"{slug}→{label}" for slug, label in remap.items()
            )
            return AxisInference(
                axis="workstream",
                binding={"label": {"remap": remap}},
                evidence=(
                    "workstream→label-remap inferred from observed "
                    f"`workstream:*` labels: {cited}. The human should confirm "
                    "the kit-value→label mapping (drafted as slug-identity)."
                ),
                confidence="low",
            )
    # No workstream labels. Echo observed-but-unmatched grouping-ish labels (G3)
    # so a repo using `area:`/`team:`/`component:` sees them surfaced rather than a
    # bare "none observed" that can't be told from "matcher didn't know my shape".
    echo = ""
    unmatched = _unmatched_workstreamish_labels(inventory)
    if unmatched:
        echo = (
            " Observed labels that LOOK workstream/grouping-ish but use a prefix "
            "other than `workstream:` (area:/team:/component:/squad:/group:): "
            + ", ".join(unmatched)
            + " — if one IS your workstream axis, map it by hand (or re-prefix to "
            "`workstream:`)."
        )
    # Note a board-field candidate if one looks like it.
    field_note = _workstream_field_note(inventory)
    return AxisInference(
        axis="workstream",
        binding=None,
        evidence=(
            "workstream left UNSUPPORTED (written explicitly as `unsupported: "
            "true`) — no `workstream:*` labels observed."
            + echo
            + field_note
        ),
        confidence="none",
    )


def _unmatched_workstreamish_labels(inventory: Inventory) -> list[str]:
    """Observed labels that read as workstream/grouping-ish under a non-kit prefix.

    The matcher only recognises the kit `workstream:` prefix; a repo encoding the
    same axis as `area:`/`team:`/`component:`/`squad:`/`group:` drafts UNSUPPORTED.
    Echoing those labels (G3) lets the human distinguish "no workstream axis" from
    "my prefix isn't the one the matcher knows". Capped to keep the report readable.
    """
    hints = ("area:", "team:", "component:", "squad:", "group:")
    out: list[str] = []
    for name, obs in _label_index(inventory):
        folded = name.casefold()
        if folded.startswith("workstream:"):
            continue
        if any(folded.startswith(h) for h in hints):
            out.append(f"{name} ({obs.issue_usage} issue(s))")
    return out[:8]


def _workstream_field_note(inventory: Inventory) -> str:
    """A report note when a board single-select field looks workstream-shaped.

    The substrate-map cannot bind a field (no `field:` kind — DEC-037 §3 defers
    it), so this is surfaced as CONTEXT for the human (who would declare it on a
    DEC-024 `after_create_issue` hook instead), never drafted as a binding.
    """
    for f in inventory.board_fields:
        name = str(f.get("name", ""))
        if "workstream" in name.casefold():
            options = f.get("options")
            opt_names = (
                ", ".join(
                    str(o.get("name"))
                    for o in options
                    if isinstance(o, dict) and o.get("name")
                )
                if isinstance(options, list)
                else ""
            )
            return (
                f" NOTE: a Projects-v2 board field named `{name}` was observed"
                + (f" (options: {opt_names})" if opt_names else "")
                + " — the substrate-map has no `field:` binding kind (DEC-037 §3 "
                "defers it), so a field-carried workstream is declared on a "
                "DEC-024 `after_create_issue` hook, not in this map. Recorded as "
                "context for the human."
            )
    return ""


def _infer_hierarchy(inventory: Inventory) -> tuple[str, str]:
    """Infer the hierarchy MODE (gated / advisory) + its evidence.

    A brownfield tracker with no machine-checkable parent-refs is flat → advisory
    (the safe brownfield default for a tracker that cannot express required
    parents). We cannot positively detect parent-ref support from labels/titles
    alone, so the draft defaults to ``advisory`` (matching the AUJ flat-tracker
    case) and the evidence is explicit that this is a conservative draft the human
    confirms — NOT a positive detection.
    """
    return (
        "advisory",
        "hierarchy drafted as `advisory` (flat-tracker default): adopt-existing "
        "cannot positively detect machine-checkable parent-ref support from "
        "labels/titles, so it drafts the brownfield-safe `advisory` mode (parent-"
        "requiredness degrades to a body-text note; containment invariants stay "
        "HARD regardless). If your tracker DOES enforce parent-refs, set "
        "`hierarchy: gated`.",
    )


def _label_index(inventory: Inventory) -> list[tuple[str, LabelObservation]]:
    """The observed labels as ``(name, observation)`` pairs (order preserved)."""
    return [(obs.name, obs) for obs in inventory.labels]


# ===== schema self-check (DEC-037 §1) ====================================


@dataclass
class SchemaCheck:
    """Whether the drafted map validates against substrate-map.schema.json."""

    ran: bool          # False if the validator/schema could not be loaded
    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_draft(
    draft_map: dict[str, Any], capability_root: Path
) -> SchemaCheck:
    """Validate the drafted map against the companion JSON Schema (a self-check).

    Loads ``schemas/substrate-map.schema.json`` and validates the drafted document
    so the human is never handed a draft that would fail ``pkit schemas validate``.
    If the validator or schema cannot be loaded (jsonschema missing / schema file
    absent), returns ``ran=False`` — the report says the self-check could not run
    rather than claiming the draft is valid.
    """
    schema_path = capability_root / "schemas" / "substrate-map.schema.json"
    if not schema_path.is_file():
        return SchemaCheck(ran=False, valid=False, errors=["schema file not found"])
    try:
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover — jsonschema is a declared dependency
        return SchemaCheck(ran=False, valid=False, errors=["jsonschema unavailable"])
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SchemaCheck(ran=False, valid=False, errors=[f"schema unreadable: {exc}"])
    validator = Draft202012Validator(schema)
    errors = [e.message for e in validator.iter_errors(draft_map)]
    return SchemaCheck(ran=True, valid=not errors, errors=errors)


# ===== draft emission (YAML) =============================================


def render_draft_yaml(draft_map: dict[str, Any]) -> str:
    """Serialise the drafted substrate-map document to YAML.

    A header comment marks it explicitly as a DRAFT the human reviews and moves
    into place (never written to the live map by this script — DEC-037 §1).
    """
    from ruamel.yaml import YAML
    from io import StringIO

    header = (
        "# DRAFT substrate-map.yaml — generated by `adopt-existing` (DEC-037 §1).\n"
        "# This is a HYPOTHESIS about your tracker's conventions, NOT installed.\n"
        "# Review every binding against the audit report's evidence, edit as\n"
        "# needed, then move it to:\n"
        f"#   .pkit/capabilities/{CAPABILITY_NAME}/project/substrate-map.yaml\n"
        "# adopt-existing wrote NOTHING to your repo or your config.\n"
    )
    buf = StringIO()
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.dump(draft_map, buf)
    return header + buf.getvalue()


# ===== script entry ======================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "adopt-existing — the brownfield onboarding ceremony (DEC-037 §1). "
            "Inventories the live tracker (reads only), infers + DRAFTS a candidate "
            "substrate-map.yaml, and prints an audit report showing the EVIDENCE "
            "for each inferred binding. Mutates NOTHING — never writes the map, "
            "never edits a label/field/issue, never installs anything. The human "
            "reviews the draft + audit and moves the map into place themselves."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            "(default: <repo-root>/.pkit/capabilities/project-management/)."
        ),
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=DEFAULT_SAMPLE_LIMIT,
        help=(
            "Maximum number of issues to sample when inferring conventions "
            f"(default {DEFAULT_SAMPLE_LIMIT}). Truncation is reported, never "
            "silently capped."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Write the DRAFT substrate-map to this file instead of stdout. The "
            "audit report still goes to stdout. The file is a DRAFT the human "
            "reviews and moves into place — this is NOT the live substrate-map "
            "path, and the script refuses to write over it (DEC-037 §1)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit the inventory + inferences + draft + schema-check as a single "
            "machine-readable JSON document instead of the human report."
        ),
    )
    args = parser.parse_args()

    capability_root = _resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            "error: project-management capability not found. Run this script "
            "from within an adopter project that has the capability installed "
            "at .pkit/capabilities/project-management/.",
            file=sys.stderr,
        )
        return 2

    # Guard the draft-out path: never write the live substrate-map (DEC-037 §1).
    if args.out is not None and _is_live_map_path(args.out, capability_root):
        print(
            "error: --out points at the LIVE substrate-map path. adopt-existing "
            "drafts for review and NEVER writes the live map (DEC-037 §1). Choose "
            "a different draft path; move it into place yourself after review.",
            file=sys.stderr,
        )
        return 2

    config = load_adopter_config(capability_root)
    inventory = take_inventory(config, sample_limit=args.sample_limit)
    if not inventory.read_ok:
        print(
            "error: could not inventory the live tracker — `gh label list` and "
            "`gh issue list` both failed (gh not on PATH, repo inaccessible, or "
            "auth invalid). There is nothing to infer from; refusing rather than "
            "drafting from an empty inventory. No write occurred.",
            file=sys.stderr,
        )
        return 2

    draft = infer_draft(inventory)
    draft_map = draft.substrate_map()
    schema_check = validate_draft(draft_map, capability_root)
    draft_yaml = render_draft_yaml(draft_map)

    if args.json:
        print(json.dumps(
            _json_document(inventory, draft, draft_map, schema_check), indent=2
        ))
        return 0

    _emit_draft(draft_yaml, args.out)
    _print_audit_report(
        capability_root, config, inventory, draft, schema_check, args
    )
    return 0


def _emit_draft(draft_yaml: str, out: Path | None) -> None:
    """Emit the drafted YAML to ``out`` (a draft file) or stdout.

    Writing to a draft FILE is not a substrate mutation — it is the draft artifact
    the human reviews, never the live map (guarded above). When no ``--out`` is
    given the draft prints to stdout so the human can redirect it themselves.
    """
    if out is None:
        print("===== DRAFT substrate-map.yaml (review; NOT installed) =====")
        print(draft_yaml)
        return
    out.write_text(draft_yaml, encoding="utf-8")
    print(f"Draft substrate-map written to {out} (a DRAFT — review, then move it "
          "into place yourself). NOTHING was written to your repo or live config.")


def _is_live_map_path(out: Path, capability_root: Path) -> bool:
    """True when ``out`` resolves to the live substrate-map path (must be refused)."""
    live = (capability_root / axis_labels.SUBSTRATE_MAP_RELATIVE_PATH).resolve()
    try:
        return out.resolve() == live
    except OSError:
        return False


# ----- human audit report --------------------------------------------


def _print_audit_report(
    capability_root: Path,
    config: dict[str, Any],
    inventory: Inventory,
    draft: Draft,
    schema_check: SchemaCheck,
    args: argparse.Namespace,
) -> None:
    """The audit report — the load-bearing DEC-037 §1 deliverable.

    For each inferred binding it shows the EVIDENCE it was inferred from, with
    coverage/confidence signals, so the human's acceptance is informed rather than
    reflexive (the §1 mitigation for the map↔back-fill common-mode input).
    """
    repo = _resolve_repo_name_with_owner(config)
    print()
    print("adopt-existing (audit): project-management capability")
    print(f"  target repo: {repo}")
    print(f"  capability:  {capability_root}")
    print(
        "  posture:     INVENTORY + DRAFT ONLY — nothing was written to your "
        "repo, your labels, your issues, or your live config (DEC-037 §1)."
    )
    print()

    # --- inventory summary (what was observed) ---
    print("Inventory (observed via gh READS):")
    print(
        f"  labels: {len(inventory.labels)} on the repo"
        + (f" [TRUNCATED at the {LABELS_LIMIT}-label read cap — some labels were "
           "not read, so a priority/workstream axis under an unread label could be "
           "missed]" if inventory.labels_truncated else "")
        + f"; issues sampled: {inventory.sampled_issue_count} "
        f"({inventory.open_count} open, {inventory.closed_count} closed)"
        + (" [TRUNCATED at --sample-limit — raise it to widen the sample]"
           if inventory.sample_truncated else "")
    )
    if inventory.title_prefixes:
        top = ", ".join(
            f"[{o.prefix}]×{o.count}" for o in inventory.title_prefixes[:8]
        )
        print(f"  title-prefixes seen: {top}")
    else:
        print("  title-prefixes seen: none")
    print(
        f"  blocked-style label (`{BLOCKED_LABEL_NAME}`): "
        + ("OBSERVED" if inventory.has_blocked_label else "not observed")
    )
    if inventory.milestones_in_use:
        print(
            f"  milestones in use ({len(inventory.milestones_in_use)}): "
            + ", ".join(inventory.milestones_in_use[:8])
            + (" …" if len(inventory.milestones_in_use) > 8 else "")
        )
    else:
        print("  milestones in use: none observed in sample")
    if inventory.has_board:
        names = ", ".join(str(f.get("name")) for f in inventory.board_fields)
        print(f"  Projects-v2 board fields: {names or '(none listed)'}")
        if inventory.projects_v2_node_id:
            print(
                f"  Projects-v2 node id: {inventory.projects_v2_node_id} — "
                "RECOMMENDATION: add `projects_v2_node_id: "
                f"{inventory.projects_v2_node_id}` to project/config.yaml to skip "
                "create-issue's per-create `gh project view` read (#310). "
                "adopt-existing recommends; it does NOT write your config."
            )
    else:
        print("  Projects-v2 board: none configured")
    print()

    # --- per-axis inferred bindings + EVIDENCE (the load-bearing part) ---
    print("Inferred bindings — EACH with the evidence it was inferred from")
    print("(DEC-037 §1: judge each inference; do not rubber-stamp):")
    for inf in draft.inferences:
        verdict = (
            "bound" if inf.binding is not None
            else "UNSUPPORTED (explicit `unsupported: true` — evaluated, rejected)"
        )
        print(f"  • {inf.axis}: {verdict}  [confidence: {inf.confidence}]")
        print(f"      evidence: {inf.evidence}")
    print(f"  • hierarchy: {draft.hierarchy}")
    print(f"      evidence: {draft.hierarchy_evidence}")
    print()

    # --- schema self-check ---
    if not schema_check.ran:
        print(
            "Schema self-check: COULD NOT RUN — "
            + "; ".join(schema_check.errors)
            + ". Run `pkit schemas validate` after moving the draft into place."
        )
    elif schema_check.valid:
        print(
            "Schema self-check: the drafted map VALIDATES STRUCTURALLY against "
            "substrate-map.schema.json — `pkit schemas validate` would pass. Note "
            "this is necessary, not sufficient: the derive engine's acceptance of "
            "the drafted `state.derive` conditions is NOT verified here (that "
            "consumer is forward-declared, sibling Wave-2 work), so structural "
            "validity does not by itself confirm semantic safety. Review the "
            "evidence above, then move it into place."
        )
    else:
        print(
            "Schema self-check: the drafted map WOULD FAIL validation — fix these "
            "before moving it into place:"
        )
        for err in schema_check.errors:
            print(f"    ! {err}")
    print()

    # --- the honest bound (DEC-037 §1) ---
    print(
        "Honest bound (DEC-037 §1): draft-not-apply guards only the MAP write — "
        "you never get a silently-installed binding. It does NOT independently "
        "verify the map: the later corpus back-fill is computed THROUGH this map, "
        "so a wrong-but-rubber-stamped binding yields a wrong-but-plausible "
        "back-fill. That is why each binding above shows its evidence — review it, "
        "do not accept reflexively."
    )
    if args.out is None:
        print(
            "Next: review the draft above, redirect it to a file, edit, then move "
            "it to project/substrate-map.yaml yourself. adopt-existing will not."
        )


def _json_document(
    inventory: Inventory,
    draft: Draft,
    draft_map: dict[str, Any],
    schema_check: SchemaCheck,
) -> dict[str, Any]:
    """The machine-readable view: inventory + inferences + draft + schema-check."""
    return {
        "posture": "inventory-and-draft-only; mutates nothing (DEC-037 §1)",
        "inventory": {
            "labels": [
                {"name": o.name, "issue_usage": o.issue_usage}
                for o in inventory.labels
            ],
            "title_prefixes": [
                {"prefix": o.prefix, "count": o.count}
                for o in inventory.title_prefixes
            ],
            "open_count": inventory.open_count,
            "closed_count": inventory.closed_count,
            "sampled_issue_count": inventory.sampled_issue_count,
            "sample_truncated": inventory.sample_truncated,
            "labels_truncated": inventory.labels_truncated,
            "has_blocked_label": inventory.has_blocked_label,
            "milestones_in_use": inventory.milestones_in_use,
            "has_board": inventory.has_board,
            "board_fields": [
                str(f.get("name")) for f in inventory.board_fields
            ],
            "projects_v2_node_id": inventory.projects_v2_node_id,
        },
        "inferences": [
            {
                "axis": inf.axis,
                "binding": inf.binding,
                "evidence": inf.evidence,
                "confidence": inf.confidence,
            }
            for inf in draft.inferences
        ],
        "hierarchy": {
            "mode": draft.hierarchy,
            "evidence": draft.hierarchy_evidence,
        },
        "draft_substrate_map": draft_map,
        "schema_check": {
            "ran": schema_check.ran,
            "valid": schema_check.valid,
            "errors": schema_check.errors,
        },
    }


# ----- shared resolution helpers -------------------------------------


def _resolve_repo_name_with_owner(config: dict[str, Any]) -> str:
    try:
        proc = gh_run(
            ["gh", "repo", "view", "--json", "nameWithOwner"], config, check=False
        )
    except FileNotFoundError:
        return "<unresolved>"
    if proc.returncode != 0:
        return "<unresolved>"
    try:
        return json.loads(proc.stdout).get("nameWithOwner", "<unresolved>")
    except json.JSONDecodeError:
        return "<unresolved>"


def _resolve_capability_root(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_dir() else None
    cur = Path.cwd()
    while cur != cur.parent:
        candidate = cur / ".pkit" / "capabilities" / CAPABILITY_NAME
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return None


if __name__ == "__main__":
    sys.exit(main())
