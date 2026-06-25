#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — corpus back-fill (report half, T2a).

The **auditable propose-and-cite report** for the one-time brownfield corpus
back-fill, per [project-management:DEC-037-adoption-ceremony] §2 and its
write-path contract [ADR-031](../../../../docs/architecture/decisions/ADR-031-substrate-write-path-contract.md).
A brownfield adopter wants a non-label substrate value seeded across every
existing issue — the AUJ grounding case: each issue's Projects-v2 `workstream`
field set to `Spyre`, and a time-based milestone assigned. That is a bulk
transform over hundreds of real, human-owned issues, so DEC-037 §2 makes it a
``migrate``-family operation governed by *enumerate → cite → confirm → apply*,
never a silent mass-edit.

This script is the **enumerate + cite + present** part — and the
**residual-pre-check gate**. It does NOT mutate anything; applying the plan is
T2b (a separate task). The four DEC-037 §2 safety properties split across the two
halves:

  * **non-silent** (this half) — the report IS the gate. It enumerates the
    proposed per-issue changes and cites why each is proposed; nothing is written.
  * **residual-pre-check gate** (this half) — refuse the whole operation if the
    residual hard-fail subset of ``pre-check`` fails. Four members (DEC-037 §2):
    ``gh`` auth invalid, repo inaccessible, ``substrate-map.yaml`` fails to parse,
    and — the fourth — a covered ``set-board-field`` intent IS declared yet the
    Projects-v2 board node id cannot be resolved at all (no board, or the board
    number does not resolve). The fourth is a CONJUNCTION computed *after* intent
    resolution: a field intent must be declared AND the board globally
    unresolvable. It is distinct from the *per-issue* case (the board resolves
    fine but a single issue simply isn't on it), which stays a per-issue
    ``blocked`` — global misconfiguration at the gate, per-issue membership gap per
    issue. A milestone-only back-fill (no field intent) does NOT gate on the board
    node id. DEC-036 made ``pre-check`` *degrade* a missing axis to a capability
    matrix rather than hard-refuse, so the gate is NOT "any pre-check failure" —
    only this residual subset that still breaks the plan's assumptions. A merely-
    degraded axis does NOT refuse the back-fill.
  * **re-validate at apply** and **value-equality idempotency** (T2b) — built by
    the apply engine, which consumes this report's plan. This half only *reads*
    each issue's current state and *annotates* whether a write looks already-
    satisfied, so the human reviewing the report sees it; the binding "skip vs
    write" decision is T2b's, made against a fresh read at apply time.

Where the back-fill intent comes from (the convergence DEC-037 §3/§4 named)
--------------------------------------------------------------------------
DEC-037 §4 is explicit that population logic is **not a new slot** — it extends
[project-management:DEC-024-lifecycle-hooks]. The new-issue *default* is a DEC-024
``after_create_issue`` hook (``set-board-field`` for the Projects-v2 field;
``assign-milestone`` for the milestone); the one-time back-fill *"reuses the same
kind handlers, driven by the back-fill rather than by a lifecycle event"* (DEC-037
§4) and *"the one-time back-fill drives the same primitive"* (ADR-031 §2). So this
report reads its intent from exactly those two hook kinds declared on
``after_create_issue`` in ``project/hooks.yaml``: each such hook entry is one
back-fill *intent*, applied one-time across the corpus instead of once per create.
That is the single declaration point DEC-037 §4 points at — it avoids inventing a
new substrate-map ``field:`` binding (DEC-037 §3 / ADR-031 name that as deferred
trunk-Feature schema work, NOT this task), and it makes the **citation** concrete:
"hook entry N (kind=set-board-field) on after_create_issue".

An undeclared semantic this couples (surfaced in the report header): because the
back-fill reads its intent from the *same* ``after_create_issue`` hook that seeds
the go-forward new-issue default, **declaring a go-forward default automatically
enrols the entire historical corpus** as a back-fill intent. An adopter who wants a
go-forward default but NOT retroactive stamping (or vice versa) cannot express that
today — one declaration drives both. This is a known scope boundary for a later
task; a separate intent-declaration surface is deliberately NOT built here (DEC-037
§2 — the report IS the gate, so the report states the coupling to make acceptance
informed rather than silently enrolling the corpus).

The substrate-map is still read — for the **residual gate** (it must parse) and so
the report can cite a per-axis ``default:`` when one corroborates the hook intent
(DEC-036 carries per-axis ``default:``). The map is not the *source* of the
field/milestone ids the writes need (those are the hook's ``field_id`` /
``single_select_option_id`` / ``title``); it is read for the gate and the citation.

Constructing the planned write (ADR-031, never inline)
------------------------------------------------------
The report shows the **exact** ``gh`` write that would run, constructed through
``_lib/substrate_writes``'s ``*_args`` constructors — never string-built here. The
sole-constructor guard (``test_pm_substrate_write_seam``) holds for the planned
argv too: even though this half does not *execute* the write, it does not
*construct* it inline either. Where a Projects-v2 item id cannot be resolved for an
issue (the issue is not on the board), the field write is reported as
**blocked — needs board membership** rather than fabricating an argv; T2b acts on
that honestly.

The plan output shape T2b consumes (``--json``)
-----------------------------------------------
``--json`` emits a machine-stable plan: a top-level object with ``schema_version``,
the resolved ``intents`` (each with its citation), and a flat ``proposed`` list of
per-issue / per-intent entries. Each ``proposed`` entry carries the constructed
``argv`` (the exact write), the ``citation``, the ``observed`` current value read
at plan time, and an ``idempotent_prediction`` (``"already-satisfied"`` /
``"would-write"`` / ``"blocked"``). T2b re-reads each issue at apply time (it must
NOT trust ``observed`` — that is the re-validate-at-apply property), drives the
write through the same primitive, and applies its own posture. This half builds the
plan; it does not build re-validate-at-apply, value-equality idempotency,
``--emit-script``, or apply (those are T2b).

Self-contained via PEP 723 inline metadata; run via
  uv run --script .pkit/capabilities/project-management/scripts/back-fill.py
Or via the dispatcher (per COR-021):
  pkit project-management back-fill

Exit codes:
  0  report produced (including "no intents declared" / "nothing to propose")
  2  usage error (capability not found), or the residual pre-check gate refused
     (auth / repo-access / map-parse) — the report is NOT produced in that case.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib import substrate_writes  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.hooks import HOOKS_RELATIVE_PATH, load_hooks_file  # noqa: E402


CAPABILITY_NAME = "project-management"
PLAN_SCHEMA_VERSION = 1

# The back-fill drives exactly the two DEC-024 non-label-substrate kinds (DEC-037
# §4 / ADR-031 §2). The other two kinds (`post-comment`, `custom-script`) are not
# substrate writes and are out of the back-fill's scope.
BACK_FILL_KINDS: tuple[str, ...] = ("set-board-field", "assign-milestone")
# The back-fill applies a default-seeding intent declared for new issues to the
# EXISTING corpus, so it reads the new-issue event's hooks (DEC-037 §4 "the same
# kind handlers, driven by the back-fill rather than by a lifecycle event").
BACK_FILL_SOURCE_EVENT = "after_create_issue"


# ----- resolved intents (the cite half) ------------------------------


@dataclass(frozen=True)
class BackFillIntent:
    """One resolved back-fill intent — a non-label substrate write to seed corpus-wide.

    Sourced from one ``after_create_issue`` hook entry of a covered kind. ``citation``
    is the human-readable "why this is proposed" line (DEC-037 §2 propose-and-cite);
    ``axis_default_note`` corroborates it with the substrate-map per-axis ``default:``
    when one is declared (DEC-036), else empty.
    """

    kind: str            # "set-board-field" | "assign-milestone"
    citation: str        # why this intent is proposed
    axis_default_note: str = ""
    # set-board-field params (the field-value write inputs, ADR-031 / hook schema)
    field_id: str | None = None
    single_select_option_id: str | None = None
    text_value: str | None = None
    # assign-milestone params (the milestone write input)
    milestone_title: str | None = None


@dataclass
class ProposedChange:
    """One proposed per-issue write — an intent applied to one issue."""

    issue_number: int
    issue_title: str
    kind: str
    citation: str
    # The exact gh write constructed via substrate_writes *_args (ADR-031), or
    # None when blocked (e.g. the field write needs a board item id we can't
    # resolve for this issue — reported, not fabricated).
    argv: list[str] | None
    observed: str | None          # current value read at plan time (for the human)
    prediction: str               # "already-satisfied" | "would-write" | "blocked"
    blocked_reason: str = ""


# ----- script entry --------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Corpus back-fill — the auditable propose-and-cite REPORT half "
            "(DEC-037 §2). Enumerates the proposed per-issue non-label substrate "
            "writes (Projects-v2 field value; milestone), cites why each is "
            "proposed, and presents the report as the gate. Mutates nothing — "
            "applying the plan is a separate operation."
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
        "--json",
        action="store_true",
        help=(
            "Emit the machine-stable plan as JSON (the shape the apply engine "
            "consumes) instead of the human-readable report."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of issues to enumerate from the corpus (default 500).",
    )
    parser.add_argument(
        "--state",
        choices=("open", "closed", "all"),
        default="all",
        help=(
            "Which issues to enumerate (default: all). A corpus back-fill "
            "typically targets every issue, open and closed."
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

    config = load_adopter_config(capability_root)

    # The residual-pre-check gate, arm 1 (DEC-037 §2). The auth / repo-access /
    # map-parse checks do not depend on the resolved intents, so they run first;
    # refuse the whole operation on a residual hard-fail (the report is NOT
    # produced). The fourth member (declared field intent but board unresolvable)
    # is a CONJUNCTION over the intents, so it is computed below, after resolution.
    gate = _residual_pre_check(capability_root)
    if not gate.passed:
        _print_gate_refusal(gate)
        return 2

    substrate_map = axis_labels.load_substrate_map(capability_root)
    intents, intent_errors = _resolve_intents(capability_root, substrate_map)

    # Arm 2 (DEC-037 §2 fourth residual member): a covered set-board-field intent
    # IS declared AND the Projects-v2 board node id cannot be resolved at all. This
    # is a global precondition failure — surface it once, distinct from the per-
    # issue "board resolves but this issue isn't on it" case (which stays a per-
    # issue blocked). A milestone-only back-fill (no field intent) does NOT gate on
    # the board node id. Compute the node id once here; thread it through.
    has_field_intent = any(i.kind == "set-board-field" for i in intents)
    # Only resolve the board node id when a field intent actually needs it — a
    # milestone-only back-fill must not pay for (or gate on) the board read.
    project_node_id = _resolve_project_node_id(config) if has_field_intent else None
    if has_field_intent and project_node_id is None:
        _add_board_unresolvable_failure(gate)
        _print_gate_refusal(gate)
        return 2

    if not args.json:
        _print_context_header(capability_root, config)
        _print_gate_pass(gate)
        for err in intent_errors:
            print(f"  ! {err}")
        if intent_errors:
            print()

    if not intents:
        if args.json:
            print(json.dumps(_plan_document([], [], gate, truncated=False), indent=2))
        else:
            print(
                "No back-fill intents declared. The corpus back-fill drives the "
                f"`{', '.join(BACK_FILL_KINDS)}` hooks on `{BACK_FILL_SOURCE_EVENT}` "
                f"in {HOOKS_RELATIVE_PATH} (DEC-037 §4); none are declared, so "
                "there is nothing to propose."
            )
        return 0

    issues = _enumerate_corpus(config, limit=args.limit, state=args.state)
    truncated = len(issues) == args.limit
    target_repo = _resolve_repo_name_with_owner(config)
    item_ids = _resolve_board_item_ids(config, project_node_id, issues)
    proposed = _build_proposed_changes(
        intents, issues, item_ids, project_node_id, target_repo
    )

    if args.json:
        print(json.dumps(
            _plan_document(intents, proposed, gate, truncated=truncated), indent=2
        ))
    else:
        if truncated:
            _print_truncation_warning(args.limit)
        _print_report(intents, proposed, len(issues))

    return 0


# ----- residual pre-check gate ---------------------------------------


@dataclass
class GateResult:
    """The residual-pre-check gate outcome (DEC-037 §2 fourth property)."""

    passed: bool
    # (label, status, detail) per residual check, for the report.
    checks: list[tuple[str, str, str]] = field(default_factory=list)


def _residual_pre_check(capability_root: Path) -> GateResult:
    """Run ONLY the residual hard-fail subset of pre-check (DEC-037 §2).

    DEC-036 made pre-check degrade a missing axis to a capability matrix rather
    than hard-refuse, so the back-fill gates on the narrow subset that still
    hard-fails in brownfield — ``gh`` auth invalid, repo inaccessible, or
    ``substrate-map.yaml`` fails to parse — NOT the degraded-axis checks. To
    avoid drift, the three probes are pre-check's OWN check functions, loaded by
    file path (pre-check.py has a hyphen, so a plain import won't reach it) and
    reused verbatim rather than reimplemented (COR-007 — don't re-derive the
    diagnostic).

    A merely-degraded axis does NOT appear here and does NOT refuse the run.
    """
    pre_check = _load_pre_check_module(capability_root)
    checks: list[tuple[str, str, str]] = []

    if pre_check is None:
        # Defensive: the sibling diagnostic is missing/unloadable. Fail closed —
        # we cannot confirm the residual prerequisites, so we must not proceed to
        # propose writes against an unverified substrate.
        checks.append((
            "residual pre-check",
            "fail",
            "could not load pre-check.py to run the residual gate "
            "(auth / repo-access / map-parse). Refusing to proceed.",
        ))
        return GateResult(passed=False, checks=checks)

    # 1. gh auth, 2. repo accessible — always residual hard-fails.
    auth = pre_check._check_gh_auth()
    checks.append((auth.label, auth.status, auth.detail))
    repo = pre_check._check_repo_accessible()
    checks.append((repo.label, repo.status, repo.detail))

    # 3. substrate-map.yaml parse — only when a map is present (an absent map is
    #    greenfield, which is not a back-fill failure; and an absent map cannot
    #    "fail to parse"). The parse probe is pre-check's own, which distinguishes
    #    "present but unparseable / mis-shaped" (fail) from "parses" (ok).
    map_path = capability_root / axis_labels.SUBSTRATE_MAP_RELATIVE_PATH
    if map_path.is_file():
        parse = pre_check._check_substrate_map_parse(capability_root)
        checks.append((parse.label, parse.status, parse.detail))

    passed = all(status != "fail" for _, status, _ in checks)
    return GateResult(passed=passed, checks=checks)


def _add_board_unresolvable_failure(gate: GateResult) -> None:
    """Append the fourth residual-gate member's failure (DEC-037 §2) onto the gate.

    The conjunction "a covered set-board-field intent IS declared AND the
    Projects-v2 board node id cannot be resolved at all" is a *global* precondition
    failure computed after intent resolution. The caller has already established
    both conjuncts; this records the failure so the standard refusal path surfaces
    it once at the top, distinct from the per-issue membership block.
    """
    gate.passed = False
    gate.checks.append((
        "Projects v2 board resolvable",
        "fail",
        "declared set-board-field intent(s) cannot be served: no Projects v2 "
        "board resolvable (has_projects_v2_board false/unset, projects_v2_board_id "
        "missing, or the board number does not resolve via `gh project view`).",
    ))


def _load_pre_check_module(capability_root: Path) -> Any | None:
    """Load pre-check.py as a module by file path (its name has a hyphen).

    Reusing pre-check's exact residual-check logic (rather than reimplementing
    the auth/repo/parse probes) keeps the gate from drifting out of sync with the
    full diagnostic. Returns the loaded module, or None if it cannot be loaded.
    """
    pre_check_path = capability_root / "scripts" / "pre-check.py"
    if not pre_check_path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            "pm_pre_check_for_back_fill", pre_check_path
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 — a broken sibling must not crash the gate
        return None


# ----- intent resolution (cite half) ---------------------------------


def _resolve_intents(
    capability_root: Path,
    substrate_map: "axis_labels.SubstrateMap | None",
) -> tuple[list[BackFillIntent], list[str]]:
    """Resolve back-fill intents from the after_create_issue hooks (DEC-037 §4).

    Reads the covered kinds (``set-board-field`` / ``assign-milestone``) declared
    on ``after_create_issue`` in ``hooks.yaml`` and turns each into a
    :class:`BackFillIntent` with a concrete citation. Malformed entries are
    skipped with a reported error (the report shows them; they do not crash).

    Returns ``(intents, errors)``.
    """
    hooks_doc = load_hooks_file(capability_root)
    by_event = hooks_doc.get("hooks") if isinstance(hooks_doc.get("hooks"), dict) else {}
    entries = by_event.get(BACK_FILL_SOURCE_EVENT) if isinstance(by_event, dict) else None

    intents: list[BackFillIntent] = []
    errors: list[str] = []
    if not isinstance(entries, list):
        return intents, errors

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind", "")).strip()
        if kind not in BACK_FILL_KINDS:
            continue  # post-comment / custom-script / unknown — not a substrate write
        cite_prefix = (
            f"hook entry {index} (kind={kind}) on {BACK_FILL_SOURCE_EVENT} "
            f"in {HOOKS_RELATIVE_PATH} (DEC-037 §4 — the same write the per-create "
            f"default seeds, applied one-time over the corpus)"
        )
        if kind == "set-board-field":
            intent, err = _intent_from_set_board_field(entry, cite_prefix, substrate_map)
        else:  # assign-milestone
            intent, err = _intent_from_assign_milestone(entry, cite_prefix, substrate_map)
        if err:
            errors.append(f"skipping hook entry {index} (kind={kind}): {err}")
        if intent is not None:
            intents.append(intent)

    return intents, errors


def _intent_from_set_board_field(
    entry: dict[str, Any],
    citation: str,
    substrate_map: "axis_labels.SubstrateMap | None",
) -> tuple[BackFillIntent | None, str]:
    field_id = entry.get("field_id")
    option_id = entry.get("single_select_option_id")
    text_value = entry.get("text_value")
    if not isinstance(field_id, str) or not field_id:
        return None, "missing or empty `field_id`"
    if not (option_id or text_value):
        return None, "requires `single_select_option_id` or `text_value`"
    return (
        BackFillIntent(
            kind="set-board-field",
            citation=citation,
            axis_default_note=_workstream_default_note(substrate_map),
            field_id=field_id,
            single_select_option_id=str(option_id) if option_id else None,
            text_value=str(text_value) if text_value else None,
        ),
        "",
    )


def _intent_from_assign_milestone(
    entry: dict[str, Any],
    citation: str,
    substrate_map: "axis_labels.SubstrateMap | None",
) -> tuple[BackFillIntent | None, str]:
    title = entry.get("title")
    if not isinstance(title, str) or not title:
        return None, "missing or empty `title`"
    return (
        BackFillIntent(
            kind="assign-milestone",
            citation=citation,
            milestone_title=title,
        ),
        "",
    )


def _workstream_default_note(
    substrate_map: "axis_labels.SubstrateMap | None",
) -> str:
    """Cite the substrate-map per-axis `default:` for workstream when one exists.

    The AUJ field-value back-fill (`workstream=Spyre`) corroborates with the
    `workstream` axis's declared `default:` (DEC-036 carries per-axis `default:`).
    This is a supporting citation, not the source of the field id; empty when no
    default is declared (or greenfield).
    """
    default = axis_labels.axis_default("workstream", substrate_map)
    if default:
        return (
            f"corroborated by substrate-map.yaml `workstream` axis default "
            f"`{default}` (DEC-036 per-axis default:)"
        )
    return ""


# ----- corpus enumeration --------------------------------------------


def _enumerate_corpus(
    config: dict[str, Any], *, limit: int, state: str
) -> list[dict[str, Any]]:
    """List the corpus issues with the fields the report needs (a READ).

    Pulls ``number``, ``title``, and ``milestone`` (for value-equality
    annotation of the milestone intent). Board field-value current state is not
    available on the ``gh issue`` JSON surface, so the field intent's ``observed``
    is left unresolved (the human sees "unknown — re-validated at apply").
    """
    try:
        proc = gh_run(
            [
                "gh", "issue", "list",
                "--state", state,
                "--limit", str(limit),
                "--json", "number,title,milestone",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _resolve_project_node_id(config: dict[str, Any]) -> str | None:
    """Resolve the Projects-v2 project GraphQL node id the way the rest of pm does.

    The field-value write needs the *project* node id, but no adopter declares it
    directly in config — the documented board config is ``has_projects_v2_board`` +
    ``projects_v2_board_id`` (a board *number*), exactly as ``create-issue.py`` /
    ``pre-check.py`` read it. So this resolves the board *number* to its node id via
    a ``gh project view`` read (the same read ``pre-check`` runs to verify the board
    resolves), keyed by the configured ``gh.default_owner`` (or, absent that, the
    current repo's owner from ``gh repo view``). A READ only.

    Returns ``None`` when no board is configured (``has_projects_v2_board`` falsey
    or ``projects_v2_board_id`` unset) or the board number does not resolve. The
    caller treats a ``None`` as "no board resolvable" — which, when a field intent
    is declared, the residual gate's fourth member turns into a global refusal
    (DEC-037 §2), and otherwise leaves the milestone-only back-fill unaffected.
    """
    if not config.get("has_projects_v2_board"):
        return None
    board_number = config.get("projects_v2_board_id")
    if board_number is None:
        return None

    owner = _resolve_board_owner(config)
    view_args = ["gh", "project", "view", str(board_number), "--format", "json"]
    if owner:
        view_args += ["--owner", owner]
    try:
        proc = gh_run(view_args, config, check=False)
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


def _resolve_board_owner(config: dict[str, Any]) -> str | None:
    """The owner to scope the board lookup to: configured ``gh.default_owner``, else
    the current repo's owner (from ``gh repo view``). ``None`` if neither resolves —
    ``gh project view`` then falls back to its own default-owner behaviour."""
    gh_block = config.get("gh") if isinstance(config, dict) else None
    if isinstance(gh_block, dict):
        owner = gh_block.get("default_owner")
        if isinstance(owner, str) and owner:
            return owner
    repo = _resolve_repo_name_with_owner(config)
    if repo != "<unresolved>" and "/" in repo:
        return repo.split("/", 1)[0]
    return None


def _resolve_board_item_ids(
    config: dict[str, Any], project_node_id: str | None, issues: list[dict[str, Any]]
) -> dict[tuple[str, int], str]:
    """Map (repo, issue-number) → its Projects-v2 item node id, for the field write.

    The field-value write (`gh project item-edit --id <item>`) needs the issue's
    Projects-v2 *item* node id. Resolving it is a READ; this fetches the board's
    items once via the GraphQL surface and maps each item's content to its id.

    The map is keyed on **(repository nameWithOwner, issue number)**, not number
    alone: a Projects-v2 board can carry issues from multiple repos with colliding
    numbers, so issue #42 in the target repo and a #42 in another repo on the same
    board would otherwise resolve to whichever item the read saw last — a wrong
    item id flowing straight into the plan's argv. Keying on (repo, number) and
    matching only the target repo's issues (in :func:`_build_proposed_changes`)
    closes that collision.

    Returns ``{}`` when no board node id resolves or the read fails — every field
    intent then reports as blocked (needs membership) rather than guessing. Best-
    effort and bounded: a single paginated read.
    """
    if not isinstance(project_node_id, str) or not project_node_id:
        return {}

    query = (
        "query($project: ID!, $cursor: String) { node(id: $project) { "
        "... on ProjectV2 { items(first: 100, after: $cursor) { "
        "pageInfo { hasNextPage endCursor } nodes { id content { "
        "... on Issue { number repository { nameWithOwner } } } } } } } }"
    )
    out: dict[tuple[str, int], str] = {}
    cursor: str | None = None
    # Bound the pagination so a misconfigured board can't loop unboundedly.
    for _ in range(50):
        api_args = [
            "gh", "api", "graphql",
            "-f", f"query={query}",
            "-F", f"project={project_node_id}",
        ]
        if cursor:
            api_args += ["-F", f"cursor={cursor}"]
        try:
            proc = gh_run(api_args, config, check=False)
        except FileNotFoundError:
            return out
        if proc.returncode != 0:
            return out
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return out
        items_block = (
            payload.get("data", {}).get("node", {}).get("items", {})
            if isinstance(payload, dict)
            else {}
        )
        for node in items_block.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            content = node.get("content") or {}
            if not isinstance(content, dict):
                continue
            number = content.get("number")
            repo_block = content.get("repository") or {}
            repo = (
                repo_block.get("nameWithOwner")
                if isinstance(repo_block, dict)
                else None
            )
            item_id = node.get("id")
            if (
                isinstance(number, int)
                and isinstance(repo, str) and repo
                and isinstance(item_id, str) and item_id
            ):
                out[(repo, number)] = item_id
        page = items_block.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not isinstance(cursor, str) or not cursor:
            break
    return out


# ----- proposed-change computation (the enumerate half) --------------


def _build_proposed_changes(
    intents: list[BackFillIntent],
    issues: list[dict[str, Any]],
    item_ids: dict[tuple[str, int], str],
    project_id: str | None,
    target_repo: str,
) -> list[ProposedChange]:
    """Compute one proposed change per (issue, intent), with the constructed argv.

    The write argv is constructed through ``substrate_writes`` ``*_args`` (ADR-031,
    never inline). ``observed`` + ``prediction`` annotate the current state so the
    human sees what looks already-satisfied — but the binding skip/write decision
    is T2b's, made against a fresh read at apply time (re-validate-at-apply).

    ``item_ids`` is keyed on (repo, number); the field-value path matches only
    ``target_repo``'s issues so a colliding number on another repo's board item
    cannot resolve. The global "no board resolvable" case is handled upstream by
    the residual gate (DEC-037 §2 fourth member); ``project_id`` is ``None`` here
    only when no field intent gated (milestone-only back-fill).
    """
    proposed: list[ProposedChange] = []
    for issue in issues:
        number = issue.get("number")
        title = str(issue.get("title", ""))
        if not isinstance(number, int):
            continue
        for intent in intents:
            if intent.kind == "set-board-field":
                proposed.append(
                    _propose_field_value(
                        intent, number, title, item_ids, project_id, target_repo
                    )
                )
            else:  # assign-milestone
                proposed.append(
                    _propose_milestone(intent, number, title, issue)
                )
    return proposed


def _propose_field_value(
    intent: BackFillIntent,
    number: int,
    title: str,
    item_ids: dict[tuple[str, int], str],
    project_id: str | None,
    target_repo: str,
) -> ProposedChange:
    """Propose one Projects-v2 field-value write for one issue.

    Blocked (no fabricated argv) when THIS issue's board item id can't be resolved
    — the issue is simply not on the board (recoverable by adding it). The *global*
    "no board resolvable at all" case does NOT reach here: when a field intent is
    declared it is caught upstream by the residual gate's fourth member (DEC-037 §2)
    and refuses the whole run once; ``project_id`` being ``None`` here only happens
    for a milestone-only back-fill that never declared a field intent, so it is
    reported as a per-issue block too. Either way: per-issue grain, no fabricated
    argv. T2b acts on the block (establish membership, then write) honestly.
    """
    item_id = item_ids.get((target_repo, number))
    if item_id is None or project_id is None:
        reason = (
            f"issue not on the configured Projects v2 board (no item id for "
            f"{target_repo}#{number})"
            if project_id is not None
            else "no Projects v2 board resolvable for this milestone-only back-fill"
        )
        return ProposedChange(
            issue_number=number,
            issue_title=title,
            kind="set-board-field",
            citation=_full_citation(intent),
            argv=None,
            observed=None,
            prediction="blocked",
            blocked_reason=reason,
        )
    # Constructed through the sole constructor (ADR-031) — never string-built here.
    argv = substrate_writes.field_value_args(
        item_id=item_id,
        field_id=intent.field_id or "",
        project_id=project_id,
        single_select_option_id=intent.single_select_option_id,
        text_value=intent.text_value,
    )
    # The gh `issue` JSON surface does not expose the board field's current value,
    # so observed is unknown here; T2b re-validates at apply (DEC-037 §2).
    return ProposedChange(
        issue_number=number,
        issue_title=title,
        kind="set-board-field",
        citation=_full_citation(intent),
        argv=argv,
        observed=None,
        prediction="would-write",
    )


def _propose_milestone(
    intent: BackFillIntent,
    number: int,
    title: str,
    issue: dict[str, Any],
) -> ProposedChange:
    """Propose one milestone write for one issue, annotated with value-equality.

    The milestone intent's current value IS on the ``gh issue`` JSON surface, so
    this annotates ``already-satisfied`` when the issue's milestone already equals
    the target (the value-equality DEC-037 §2 idempotency, surfaced for the human
    — the binding skip is still T2b's at apply time).
    """
    target = intent.milestone_title or ""
    current_ms = issue.get("milestone")
    observed = (
        current_ms.get("title")
        if isinstance(current_ms, dict) and isinstance(current_ms.get("title"), str)
        else None
    )
    # Constructed through the sole constructor (ADR-031) — never string-built here.
    argv = substrate_writes.milestone_edit_args(issue_number=number, title=target)
    prediction = "already-satisfied" if observed == target else "would-write"
    return ProposedChange(
        issue_number=number,
        issue_title=title,
        kind="assign-milestone",
        citation=_full_citation(intent),
        argv=argv,
        observed=observed,
        prediction=prediction,
    )


def _full_citation(intent: BackFillIntent) -> str:
    """The full why-line for an intent, including any corroborating default note."""
    if intent.axis_default_note:
        return f"{intent.citation}; {intent.axis_default_note}"
    return intent.citation


# ----- plan document (the machine-stable T2b seam) -------------------


def _plan_document(
    intents: list[BackFillIntent],
    proposed: list[ProposedChange],
    gate: GateResult,
    *,
    truncated: bool,
) -> dict[str, Any]:
    """The machine-stable plan T2b consumes (`--json`).

    Shape (versioned so T2b can pin it):
      schema_version: int
      truncated: bool
      residual_pre_check: {passed, checks: [{label, status, detail}]}
      intents: [{kind, citation, ...params}]
      proposed: [{issue_number, issue_title, kind, citation, argv|null,
                  observed|null, prediction, blocked_reason}]

    ``truncated`` is True when the corpus enumeration hit ``--limit`` exactly, so
    the plan may be an INCOMPLETE view of the corpus — T2b must treat a truncated
    plan as not-the-whole-corpus (DEC-037's non-silent posture; a truncated plan
    reviewed as complete is an audit gap).

    ``argv`` is the EXACT constructed write (or null when blocked). T2b re-reads
    each issue at apply time (it must NOT trust ``observed``/``prediction`` —
    re-validate-at-apply), drives the write through the same primitive, and
    applies its own posture.
    """
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "truncated": truncated,
        "residual_pre_check": {
            "passed": gate.passed,
            "checks": [
                {"label": label, "status": status, "detail": detail}
                for label, status, detail in gate.checks
            ],
        },
        "intents": [
            {
                "kind": i.kind,
                "citation": _full_citation(i),
                "field_id": i.field_id,
                "single_select_option_id": i.single_select_option_id,
                "text_value": i.text_value,
                "milestone_title": i.milestone_title,
            }
            for i in intents
        ],
        "proposed": [
            {
                "issue_number": c.issue_number,
                "issue_title": c.issue_title,
                "kind": c.kind,
                "citation": c.citation,
                "argv": c.argv,
                "observed": c.observed,
                "prediction": c.prediction,
                "blocked_reason": c.blocked_reason,
            }
            for c in proposed
        ],
    }


# ----- human report --------------------------------------------------


def _print_context_header(capability_root: Path, config: dict[str, Any]) -> None:
    repo = _resolve_repo_name_with_owner(config)
    version = _read_capability_version(capability_root)
    print("back-fill (report): project-management capability")
    print(f"  target repo: {repo}")
    print(f"  capability:  {capability_root} (v{version})")
    print(f"  intent src:  {capability_root / HOOKS_RELATIVE_PATH} "
          f"({BACK_FILL_SOURCE_EVENT} hooks)")
    print(
        "  posture:     REPORT ONLY — no issue is mutated. Applying this plan "
        "is a separate operation (DEC-037 §2)."
    )
    print(
        "  scope note:  each `after_create_issue` hook of a covered kind "
        f"({', '.join(BACK_FILL_KINDS)}) is treated as a CORPUS-WIDE back-fill "
        "intent — so declaring a go-forward new-issue default automatically "
        "enrols the entire historical corpus. Separating a go-forward-only "
        "default from a retroactive back-fill is NOT yet expressible (one "
        "declaration drives both); known scope boundary, not built here."
    )
    print()


def _print_truncation_warning(limit: int) -> None:
    """Loudly warn that the corpus enumeration may have been truncated at --limit.

    The enumeration returned exactly ``limit`` issues, so there may be more the
    plan does not cover. DEC-037's posture is non-silent; a truncated corpus
    reviewed as the complete plan is an audit gap, so this is a prominent warning
    (the `--json` plan carries the same signal as a ``truncated`` boolean).
    """
    print(
        f"  !! WARNING: corpus may be TRUNCATED at {limit} issue(s) — the "
        f"enumeration returned exactly --limit ({limit}) issues, so the plan may "
        "be an INCOMPLETE view of the corpus. Re-run with a higher --limit to "
        "review the whole corpus (DEC-037 §2 — the report is the gate; a "
        "truncated plan reviewed as complete is an audit gap)."
    )
    print()


def _print_gate_pass(gate: GateResult) -> None:
    print("  Residual pre-check gate (auth / repo-access / map-parse):")
    for label, status, detail in gate.checks:
        marker = {"ok": "[ok]  ", "fail": "[fail]", "skip": "[skip]"}.get(status, "[?]")
        print(f"    {marker} {label} — {detail}")
    print("  → gate passed; proceeding under any merely-degraded axes (DEC-036).")
    print()


def _print_gate_refusal(gate: GateResult) -> None:
    print(
        "back-fill: REFUSED by the residual pre-check gate (DEC-037 §2).",
        file=sys.stderr,
    )
    print(
        "  The corpus back-fill gates on the residual hard-fail subset of "
        "pre-check — `gh` auth invalid, repo inaccessible, or substrate-map.yaml "
        "fails to parse. One of these failed:",
        file=sys.stderr,
    )
    for label, status, detail in gate.checks:
        if status == "fail":
            print(f"    [fail] {label} — {detail}", file=sys.stderr)
    print(
        "  A merely-degraded axis does NOT refuse the back-fill (DEC-036); only "
        "this residual subset does. Fix the failing prerequisite and re-run.",
        file=sys.stderr,
    )


def _print_report(
    intents: list[BackFillIntent],
    proposed: list[ProposedChange],
    issue_count: int,
) -> None:
    print(f"  {len(intents)} back-fill intent(s) over {issue_count} corpus issue(s):")
    for intent in intents:
        print(f"    - {_describe_intent(intent)}")
        print(f"      cite: {_full_citation(intent)}")
    print()

    would_write = [c for c in proposed if c.prediction == "would-write"]
    satisfied = [c for c in proposed if c.prediction == "already-satisfied"]
    blocked = [c for c in proposed if c.prediction == "blocked"]

    print(f"  Proposed per-issue changes ({len(proposed)} total):")
    for change in proposed:
        marker = {
            "would-write": "[write]  ",
            "already-satisfied": "[noop]   ",
            "blocked": "[blocked]",
        }[change.prediction]
        print(f"    {marker} #{change.issue_number} {change.kind}")
        if change.argv is not None:
            print(f"               would run: {_render_argv(change.argv)}")
        if change.observed is not None:
            print(f"               observed: {change.observed!r}")
        if change.prediction == "already-satisfied":
            print("               (value already matches — likely a no-op; "
                  "re-validated at apply)")
        if change.prediction == "blocked":
            print(f"               blocked: {change.blocked_reason}")
    print()
    print(
        f"  Summary: {len(would_write)} would write, "
        f"{len(satisfied)} already satisfied (likely no-op), "
        f"{len(blocked)} blocked."
    )
    print(
        "  This report is the gate (DEC-037 §2). NO write has run. Apply this "
        "plan via the back-fill apply operation, which re-validates each issue "
        "at apply time (re-validate-at-apply) before writing."
    )


def _describe_intent(intent: BackFillIntent) -> str:
    if intent.kind == "set-board-field":
        which = (
            f"single_select_option_id={intent.single_select_option_id}"
            if intent.single_select_option_id
            else f"text_value={intent.text_value!r}"
        )
        return (
            f"set-board-field: Projects-v2 field_id={intent.field_id} → {which} "
            "(across the corpus)"
        )
    return f"assign-milestone: milestone={intent.milestone_title!r} (across the corpus)"


def _render_argv(argv: list[str]) -> str:
    """Render a constructed argv for human display (display only — not executed)."""
    out: list[str] = []
    for token in argv:
        out.append(f'"{token}"' if " " in token else token)
    return " ".join(out)


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


def _read_capability_version(capability_root: Path) -> str:
    pkg = capability_root / "package.yaml"
    if not pkg.is_file():
        return "<unknown>"
    try:
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError
    except ImportError:  # pragma: no cover
        return "<unknown>"
    try:
        data = YAML(typ="safe").load(pkg.read_text(encoding="utf-8")) or {}
        return str(data.get("component", {}).get("version", "<unknown>"))
    except (OSError, YAMLError):
        return "<unknown>"


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
