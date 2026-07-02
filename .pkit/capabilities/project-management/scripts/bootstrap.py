#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — bootstrap.

First-time adoption setup. Creates the methodology's required initial
GitHub state (labels for the three classification axes; optionally a
starter EPIC) so the capability is operational on a fresh project.

Additive idempotent: skips state that already exists. Never modifies
or deletes — that's the migrate script's job. Re-running on a
fully-bootstrapped project is a clean no-op.

Label-fallback mode: when `has_projects_v2_board` is false (the
adopter is not using a Projects v2 board), bootstrap also creates the
five lifecycle state labels (`state:todo`, `state:backlog`,
`state:in-progress`, `state:review`, `state:done`) derived from
`workflow.yaml`'s `states[].id` list. These labels are the substrate
for the `move-issue` state machine on label-fallback adopters.

Contract per the capability's DEC-017-prerequisites-bootstrap-migrate-
discipline. Programmatic, not AI-mediated.

Self-contained via PEP 723 inline metadata: run via
  uv run --script .pkit/capabilities/project-management/scripts/bootstrap.py

Exit codes:
  0  success (including "everything already exists")
  1  one or more creation operations failed
  2  usage error (capability not found; config unparseable; no PM
     authorisation for --with-starter-epic)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.gh import gh_run  # noqa: E402
from _lib.label_contributions import (  # noqa: E402
    LabelContribution,
    collect_label_contributions,
)


CAPABILITY_NAME = "project-management"
ADOPTER_CONFIG_PATH = "project/config.yaml"

# Default label colors. Adopters may override post-creation via gh label edit;
# bootstrap doesn't track or migrate color choices.
LABEL_COLORS = {
    "type": "1d76db",       # blue
    "priority": "d93f0b",   # red-orange
    "workstream": "0e8a16", # green
    "state": "fbca04",      # yellow — lifecycle state substrate for label-fallback adopters
}

LABEL_DESCRIPTIONS = {
    "type": "Classification axis: structural kind of work (per project-management:DEC-012-classification-axes).",
    "priority": "Classification axis: triage signal (per project-management:DEC-012-classification-axes).",
    "workstream": "Classification axis: cross-repo workstream (per project-management:DEC-012-classification-axes).",
    "state": "Lifecycle state (label-fallback substrate, per project-management workflow.yaml states).",
}


@dataclass(frozen=True)
class Action:
    """One bootstrap action taken (or skipped)."""

    label: str
    status: str  # "created" | "exists" | "skipped" | "failed"
    detail: str = ""


# ----- script entry --------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap a fresh project for the project-management capability. "
            "Creates labels and (optionally) a starter EPIC. Additive only."
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
        "--with-starter-epic",
        action="store_true",
        help=(
            "Also file a starter EPIC titled '[EPIC] Methodology adoption — "
            "initial hierarchy'. EPICs are PM-authority filing per DEC-008; "
            "passing this flag IS the PM authorisation."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating it.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Skip the 'apply this plan to <repo>?' confirmation prompt. "
            "Use only after you have read the plan in --dry-run output. "
            "Defaults off so accidental cwd-mismatched runs are caught."
        ),
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = _resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            "error: project-management capability not found. "
            "Run this script from within an adopter project with the "
            "capability installed at .pkit/capabilities/project-management/.",
            file=sys.stderr,
        )
        return 2

    config, config_err = _load_adopter_config(capability_root)
    if config is None:
        print(f"error: {config_err}", file=sys.stderr)
        return 2

    # gh: block validation + host-pinned auth check (per DEC-023).
    gh_err = _check_gh_block_and_auth(config)
    if gh_err is not None:
        print(f"error: {gh_err}", file=sys.stderr)
        return 2

    # Foreign-repo mutation guard (COR-039 / ADR-034) — bootstrap creates labels
    # and (optionally) a starter EPIC; gate before any write so an accidental
    # cwd-mismatched bootstrap (target repo != session anchor) is caught.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Read classification.yaml for the canonical label vocabularies.
    classification, class_err = _load_classification(capability_root)
    if classification is None:
        print(f"error: {class_err}", file=sys.stderr)
        return 2

    repo = _resolve_repo_name_with_owner()
    _print_context_header(repo, capability_root)

    has_board = bool(config.get("has_projects_v2_board"))

    # ---- compute the plan (read-only) ----
    plan = _compute_plan(
        config, classification, has_board, args.with_starter_epic, capability_root
    )
    _print_plan(plan)

    # ---- confirm before mutating ----
    if not plan.has_creates():
        print("Nothing to create — repo already in the methodology's expected initial state.")
        return 0

    if args.dry_run:
        print("(dry-run: skipping confirmation and execution; no GitHub mutations.)")
        return 0

    if not args.yes and not _confirm_apply(repo):
        print("Aborted by user. No GitHub mutations were performed.")
        return 0

    # ---- execute the plan ----
    actions = _execute_plan(plan, capability_root)
    _print_report(actions)

    failures = sum(1 for a in actions if a.status == "failed")
    return 0 if failures == 0 else 1


# ----- plan computation + execution ----------------------------------


@dataclass
class Plan:
    """The bootstrap plan: what would be created vs already exists."""

    label_creates: list[tuple[str, str]]  # (axis, name)
    label_exists: list[str]                # names already in repo
    starter_epic: bool                     # whether to file the starter EPIC
    starter_epic_exists: bool              # whether it's already filed
    skipped_messages: list[str]            # explanatory skip notes (e.g., board mode)
    # Contributed labels (per DEC-042): a capability-declared label carrying its
    # own color/description, created through a per-label path OUTSIDE the axis
    # sole-constructor. Missing-vs-present is the same idempotency diff.
    contributed_label_creates: list[LabelContribution]  # to create
    contributed_label_exists: list[str]                 # names already in repo
    contributed_label_warnings: list[str]               # skip-and-warn notes (DEC-042)
    board_node_id: str | None = None       # resolved projects_v2_node_id to cache (#310)
    board_node_id_note: str = ""            # why no id is cached (cached / no board / unresolvable)

    def has_creates(self) -> bool:
        return (
            bool(self.label_creates)
            or bool(self.contributed_label_creates)
            or (self.starter_epic and not self.starter_epic_exists)
            or self.board_node_id is not None
        )


def _compute_plan(
    config: dict[str, Any],
    classification: dict[str, Any],
    has_board: bool,
    with_starter_epic: bool,
    capability_root: Path,
) -> Plan:
    """Compare schemas+config against existing GitHub state; emit the plan."""
    existing_labels = _fetch_existing_labels() or set()

    label_creates: list[tuple[str, str]] = []
    label_exists: list[str] = []
    skipped: list[str] = []

    def _plan_axis(axis: str, values: list[str]) -> None:
        for v in values:
            # Axis-label built only through the seam (ADR-026 sole-constructor).
            # bootstrap is the GREENFIELD label-palette provisioner — it
            # intentionally uses `label()` (kit identity), not `resolve_write`:
            # provisioning the kit's own labels IS its job. Brownfield adoption
            # against a present substrate-map enters via `adopt-existing` (#264),
            # not bootstrap — so this map-blind construction is greenfield-by-
            # construction, outside the write-rewire (#262/#265) scope.
            name = axis_labels.label(axis, v)
            if name in existing_labels:
                label_exists.append(name)
            else:
                label_creates.append((axis, name))

    type_values = classification.get("axes", {}).get("type", {}).get("values", [])
    _plan_axis("type", type_values)

    if has_board:
        skipped.append(
            "priority:* / workstream:* labels — board configured; "
            "those axes live as board fields (not labels)."
        )
        skipped.append(
            "state:* labels — board configured; state lives as a Projects v2 Status field."
        )
    else:
        priority_values = (
            classification.get("axes", {}).get("priority", {}).get("values", [])
        )
        _plan_axis("priority", priority_values)
        workstreams = _resolve_workstream_slugs(capability_root, config)
        if workstreams:
            _plan_axis("workstream", workstreams)
        else:
            skipped.append(
                "workstream:* labels — no workstreams declared "
                "(in workstreams.yaml or config.yaml fallback)."
            )
        # Label-fallback mode: create state:* labels from workflow.yaml states.
        state_ids = _resolve_state_ids(capability_root)
        if state_ids:
            _plan_axis("state", state_ids)
        else:
            skipped.append(
                "state:* labels — workflow.yaml missing or no states declared "
                "(capability install may be corrupt)."
            )

    # Contributed labels (DEC-042): capabilities registered in the manifest may
    # declare labels they need; provision any that are missing through a
    # per-label create path (their own color/description), reusing the same
    # existing-vs-missing diff. Skip-and-warn: a malformed declaration is warned,
    # not fatal.
    contributed_creates, contributed_exists, contributed_warnings = (
        _plan_contributed_labels(capability_root, existing_labels)
    )

    starter_epic_exists = False
    if with_starter_epic:
        starter_epic_exists = _starter_epic_already_filed()

    # Cache the invariant board → project-node-id mapping in config (#310) so
    # create-issue skips the per-create `gh project view` read. Only in board mode,
    # and only when not already cached.
    board_node_id, board_node_id_note = _plan_project_node_id(config, has_board)

    return Plan(
        label_creates=label_creates,
        label_exists=label_exists,
        starter_epic=with_starter_epic,
        starter_epic_exists=starter_epic_exists,
        skipped_messages=skipped,
        contributed_label_creates=contributed_creates,
        contributed_label_exists=contributed_exists,
        contributed_label_warnings=contributed_warnings,
        board_node_id=board_node_id,
        board_node_id_note=board_node_id_note,
    )


def _plan_contributed_labels(
    capability_root: Path, existing_labels: set[str]
) -> tuple[list[LabelContribution], list[str], list[str]]:
    """Diff capability-contributed labels (DEC-042) against existing repo labels.

    Returns ``(to_create, already_present_names, warnings)``. The collector walks
    the manifest-registered capabilities orphan-safely; a missing contributed
    label is planned for creation carrying its own color/description, and a
    malformed / version-mismatched declaration surfaces as a warning (skip-and-
    warn, DEC-042) rather than aborting the bootstrap.
    """
    repo_root = capability_root.parent.parent.parent
    collection = collect_label_contributions(repo_root)

    to_create: list[LabelContribution] = []
    present: list[str] = []
    for label in collection.labels:
        if label.default_name in existing_labels:
            present.append(label.default_name)
        else:
            to_create.append(label)

    warnings = [str(w) for w in collection.warnings]
    return to_create, present, warnings


def _plan_project_node_id(
    config: dict[str, Any], has_board: bool
) -> tuple[str | None, str]:
    """Decide whether to resolve + cache `projects_v2_node_id` (#310).

    Returns ``(node_id_to_cache, note)``. The id is non-None only when a board is
    configured, no id is cached yet, and the live `gh project view` read resolves
    one. In label-fallback mode (no board) this is a no-op (``(None, "")``) — the
    field stays absent, per the issue's "do nothing when no board is in use". The
    note explains the no-op cases (already cached / no board number / unresolvable)
    for the plan output.
    """
    if not has_board:
        return None, ""
    existing = config.get("projects_v2_node_id")
    if isinstance(existing, str) and existing:
        return None, f"projects_v2_node_id already cached (`{existing}`); left untouched"
    board_id = config.get("projects_v2_board_id")
    if board_id is None:
        return None, (
            "projects_v2_node_id — not cached (no projects_v2_board_id configured "
            "to resolve it from)"
        )
    resolved = _resolve_project_node_id(config, board_id)
    if resolved:
        return resolved, ""
    return None, (
        f"projects_v2_node_id — could not resolve node id for board #{board_id} "
        "(`gh project view` failed); create-issue will live-resolve per create"
    )


def _print_plan(plan: Plan) -> None:
    print("Plan:")
    if plan.label_creates:
        for _, name in plan.label_creates:
            print(f"  + create label `{name}`")
    if plan.label_exists:
        print(f"  ({len(plan.label_exists)} label(s) already exist; will be left untouched)")
    for label in plan.contributed_label_creates:
        print(
            f"  + create contributed label `{label.default_name}` "
            f"(from capability `{label.capability}`)"
        )
    if plan.contributed_label_exists:
        print(
            f"  ({len(plan.contributed_label_exists)} contributed label(s) already "
            f"exist; will be left untouched)"
        )
    for warning in plan.contributed_label_warnings:
        print(f"  ! {warning}")
    if plan.starter_epic:
        if plan.starter_epic_exists:
            print("  (starter EPIC already filed; will be left untouched)")
        else:
            print("  + file starter EPIC `[EPIC] Methodology adoption — initial hierarchy`")
    if plan.board_node_id:
        print(f"  + cache projects_v2_node_id `{plan.board_node_id}` in config")
    if plan.board_node_id_note:
        print(f"  · {plan.board_node_id_note}")
    for msg in plan.skipped_messages:
        print(f"  · {msg}")
    print()


def _confirm_apply(repo: str) -> bool:
    """Single confirmation prompt naming the target repo."""
    if not sys.stdin.isatty():
        print(
            f"  ! Non-interactive shell; refusing to apply without explicit confirmation.\n"
            f"    Re-run from an interactive shell, or pass --yes after reviewing the plan."
        )
        return False
    while True:
        try:
            response = input(f"Apply this plan to `{repo}`? [y/N]: ").strip().lower()
        except EOFError:
            return False
        if response in ("y", "yes"):
            return True
        if response in ("", "n", "no"):
            return False
        print("  Please answer y or n.")


def _execute_plan(plan: Plan, capability_root: Path) -> list[Action]:
    """Run the gh mutations declared in the plan."""
    actions: list[Action] = []
    # Group creates by axis so we apply consistent color/description.
    by_axis: dict[str, list[str]] = {}
    for axis, name in plan.label_creates:
        by_axis.setdefault(axis, []).append(name)
    for axis, names in by_axis.items():
        actions.extend(_apply_label_creates(axis, names))
    for name in plan.label_exists:
        actions.append(Action(f"label `{name}`", "exists", "no-op"))
    # Contributed labels (DEC-042): each carries its OWN color/description and is
    # created through a per-label path — NOT grouped by axis, NOT routed through
    # the axis sole-constructor (a contributed label is not an axis label).
    for label in plan.contributed_label_creates:
        actions.append(_apply_contributed_label_create(label))
    for name in plan.contributed_label_exists:
        actions.append(Action(f"contributed label `{name}`", "exists", "no-op"))
    if plan.board_node_id:
        actions.append(_persist_project_node_id(capability_root, plan.board_node_id))
    if plan.starter_epic and not plan.starter_epic_exists:
        actions.append(_file_starter_epic(dry_run=False))
    elif plan.starter_epic and plan.starter_epic_exists:
        actions.append(
            Action(
                "starter EPIC",
                "exists",
                "already filed; no-op",
            )
        )
    return actions


def _apply_label_creates(axis: str, names: list[str]) -> list[Action]:
    color = LABEL_COLORS.get(axis, "ededed")
    description = LABEL_DESCRIPTIONS.get(axis, "")
    out: list[Action] = []
    for name in names:
        proc = subprocess.run(
            [
                "gh",
                "label",
                "create",
                name,
                "--color",
                color,
                "--description",
                description,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            out.append(Action(f"label `{name}`", "created"))
        else:
            out.append(
                Action(
                    f"label `{name}`",
                    "failed",
                    f"`gh label create` exit {proc.returncode}: {proc.stderr.strip()}",
                )
            )
    return out


def _apply_contributed_label_create(label: LabelContribution) -> Action:
    """Create one capability-contributed label (DEC-042), carrying its own
    color/description. Parallel to `_apply_label_creates` but per-label rather
    than axis-grouped, since each contribution declares its own presentation.
    Never routes through the axis sole-constructor — a contributed label is not
    a classification-axis label."""
    proc = subprocess.run(
        [
            "gh",
            "label",
            "create",
            label.default_name,
            "--color",
            label.color,
            "--description",
            label.description,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    tag = f"contributed label `{label.default_name}`"
    if proc.returncode == 0:
        return Action(tag, "created", f"from capability `{label.capability}`")
    return Action(
        tag,
        "failed",
        f"`gh label create` exit {proc.returncode}: {proc.stderr.strip()}",
    )


def _starter_epic_already_filed() -> bool:
    """Check whether the starter EPIC has already been filed."""
    title = "[EPIC] Methodology adoption — initial hierarchy"
    proc = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--search",
            f'in:title "{title}"',
            "--state",
            "all",
            "--json",
            "number,title,state",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    try:
        for issue in json.loads(proc.stdout):
            if issue.get("title") == title:
                return True
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return False


# ----- projects_v2_node_id cache (#310) ------------------------------


def _resolve_project_node_id(
    config: dict[str, Any], board_id: int | str
) -> str | None:
    """Resolve board NUMBER → Projects-v2 project node id via `gh project view` (a READ).

    Mirrors ``back-fill.py``'s / ``create-issue.py``'s resolver: scopes to the
    configured ``gh.default_owner`` (or the current repo's owner) and reads ``.id``
    off ``gh project view --format json``. Returns ``None`` when gh is absent, the
    call fails, or the payload carries no id. Bootstrap resolves this ONCE at
    adoption and caches it so create-issue can skip the per-create read (#310).
    """
    owner = _resolve_board_owner(config)
    view_args = ["gh", "project", "view", str(board_id), "--format", "json"]
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
    except (json.JSONDecodeError, ValueError):
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
    repo = _resolve_repo_name_with_owner()
    if repo != "<unresolved>" and "/" in repo:
        return repo.split("/", 1)[0]
    return None


def _persist_project_node_id(capability_root: Path, node_id: str) -> Action:
    """Write ``projects_v2_node_id: <id>`` into the adopter config (#310).

    Uses ruamel round-trip (not ``typ="safe"``) so the config's comments and
    formatting survive the rewrite — the config edited here is the same file
    adopters keep hand-authored comments in. Value-level idempotent: re-running
    with the same id rewrites the same value.
    """
    path = capability_root / ADOPTER_CONFIG_PATH
    yaml = YAML()  # round-trip preserves comments; typ="safe" would strip them
    yaml.preserve_quotes = True
    try:
        data = yaml.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError) as exc:
        return Action("projects_v2_node_id", "failed", f"config read failed: {exc}")
    if not isinstance(data, dict):
        return Action(
            "projects_v2_node_id", "failed", "config top-level is not a mapping"
        )
    data["projects_v2_node_id"] = node_id
    try:
        with path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh)
    except OSError as exc:
        return Action("projects_v2_node_id", "failed", f"config write failed: {exc}")
    return Action("projects_v2_node_id", "created", f"cached `{node_id}` in config")


# ----- label fetching ------------------------------------------------


def _fetch_existing_labels() -> set[str] | None:
    proc = subprocess.run(
        ["gh", "label", "list", "--limit", "500", "--json", "name"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        return {label["name"] for label in json.loads(proc.stdout)}
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


# ----- starter EPIC --------------------------------------------------


def _file_starter_epic(*, dry_run: bool) -> Action:
    """File the methodology-adoption starter EPIC.

    Per [project-management:DEC-008-pm-and-implementer-roles], EPICs are
    PM-authority filing. The `--with-starter-epic` flag is the PM's
    explicit gesture; the script does not re-prompt.
    """
    title = "[EPIC] Methodology adoption — initial hierarchy"
    body = _STARTER_EPIC_BODY

    # Refuse if an EPIC with the same title already exists.
    proc = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--search",
            f'in:title "{title}"',
            "--state",
            "all",
            "--json",
            "number,title,state",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        try:
            for issue in json.loads(proc.stdout):
                if issue.get("title") == title:
                    return Action(
                        "starter EPIC",
                        "exists",
                        f"already filed as #{issue['number']} (state: {issue['state']})",
                    )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    if dry_run:
        return Action("starter EPIC", "created", "(dry-run) would file")

    proc = subprocess.run(
        [
            "gh",
            "issue",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--label",
            axis_labels.label("type", "maintenance"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        url = proc.stdout.strip()
        return Action("starter EPIC", "created", url)
    return Action(
        "starter EPIC",
        "failed",
        f"`gh issue create` exit {proc.returncode}: {proc.stderr.strip()}",
    )


_STARTER_EPIC_BODY = """\
## Outcome

This EPIC scopes the bootstrap work needed to operationalise the
project-management methodology on this project. It exists as a default
parent for Tasks filed during the early adoption phase, before the
project's longer-term EPIC structure has crystallised.

## Success criteria

- [ ] Methodology operational end-to-end on this project (pre-check passes; bootstrap idempotent; project-manager runs)
- [ ] Successor EPICs filed covering this project's actual workstreams (each EPIC scoping a workstream's outcome)
- [ ] Tasks filed during bootstrap migrated under the appropriate successor EPIC once they exist
- [ ] This EPIC closes when its successors have absorbed all in-flight work
"""


# ----- helpers -------------------------------------------------------


def _load_adopter_config(capability_root: Path) -> tuple[dict[str, Any] | None, str]:
    path = capability_root / ADOPTER_CONFIG_PATH
    if not path.is_file():
        return None, (
            f"adopter config missing at {path}. "
            f"See the capability README's 'Adopter setup' section."
        )
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError) as exc:
        return None, f"failed to read/parse {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"{path} top-level is not a mapping"
    return data, ""


def _check_gh_block_and_auth(config: dict[str, Any]) -> str | None:
    """Validate the optional `gh:` block and authenticate against `gh.host` if set.

    Per DEC-023, both `gh.host` and `gh.default_owner` are optional; their
    absence is equivalent to delegating to ambient state. When `gh.host`
    is configured, this function runs `gh auth status -h <host>` and
    fails fast with a `gh auth login -h <host>` remediation hint if the
    host isn't authenticated. Returns None on success, or an error
    message string on failure.
    """
    raw = config.get("gh")
    if raw is None:
        return None  # no override; delegate to ambient state
    if not isinstance(raw, dict):
        return (
            "`gh:` is present in config but not a mapping. "
            "Either remove it or set it to a YAML mapping with optional "
            "`host:` / `default_owner:` fields. See DEC-023."
        )

    allowed = {"host", "default_owner"}
    extras = sorted(set(raw.keys()) - allowed)
    if extras:
        return (
            f"unknown key(s) under `gh:`: {', '.join(extras)}. "
            "DEC-023 allows only `host:` and `default_owner:` under `gh:` at v1."
        )

    for field in ("host", "default_owner"):
        value = raw.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            return (
                f"`gh.{field}` must be a non-empty string when set; "
                f"got {value!r}. Either remove the field or set it properly."
            )

    host = raw.get("host")
    if not isinstance(host, str) or not host:
        return None  # no host pinning; nothing further to verify

    proc = subprocess.run(
        ["gh", "auth", "status", "-h", host],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return (
            f"`gh auth status -h {host}` reports no active authentication. "
            f"Run `gh auth login -h {host}` and follow the prompts. "
            "DEC-023 requires the adopter's configured host to be authenticated locally."
        )
    return None


def _resolve_workstream_slugs(
    capability_root: Path, config: dict[str, Any]
) -> list[str]:
    """Read workstream slugs from workstreams.yaml (canonical) or config legacy.

    Implements DEC-018's source-of-truth precedence: dedicated file wins
    if it exists; otherwise fall back to `config.yaml.workstreams`.
    """
    ws_path = capability_root / "project" / "workstreams.yaml"
    if ws_path.is_file():
        try:
            data = YAML(typ="safe").load(ws_path.read_text(encoding="utf-8")) or {}
        except (OSError, YAMLError):
            data = {}
        ws = data.get("workstreams") if isinstance(data, dict) else None
        if isinstance(ws, list):
            return [s for s in ws if isinstance(s, str)]
        if isinstance(ws, dict):
            return [
                s
                for s, attrs in ws.items()
                if isinstance(s, str)
                and (
                    not isinstance(attrs, dict)
                    or attrs.get("status", "active") == "active"
                )
            ]
        return []
    # Legacy fallback.
    legacy = config.get("workstreams") or []
    if isinstance(legacy, list):
        return [s for s in legacy if isinstance(s, str)]
    return []


def _resolve_state_ids(capability_root: Path) -> list[str]:
    """Read lifecycle state IDs from workflow.yaml's `states[].id` list.

    Since the schema_version 3 rebind (DEC-033) the states live under a
    top-level `process:` block; this resolver reads there, falling back to the
    top level for a pre-v3 override. Returns the IDs in canonical lifecycle
    order (todo, backlog, in-progress, review, done) so label creation is
    stable regardless of the file's declaration order. Returns an empty list
    when the file is missing or unreadable.
    """
    path = capability_root / "schemas" / "workflow.yaml"
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        return []
    block = data.get("process") if isinstance(data.get("process"), dict) else data
    states = block.get("states") or []
    ids = [
        str(s["id"])
        for s in states
        if isinstance(s, dict) and isinstance(s.get("id"), str)
    ]
    canonical = ["todo", "backlog", "in-progress", "review", "done"]
    known = [s for s in canonical if s in ids]
    extra = [s for s in ids if s not in canonical]
    return known + extra


def _load_classification(
    capability_root: Path,
) -> tuple[dict[str, Any] | None, str]:
    path = capability_root / "schemas" / "classification.yaml"
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError) as exc:
        return None, f"failed to read {path}: {exc} (capability install may be corrupt)"
    if not isinstance(data, dict):
        return None, f"{path} top-level is not a mapping"
    return data, ""


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


def _print_context_header(repo: str, capability_root: Path) -> None:
    """Print the target repo + capability + config paths before any action.

    Surfaces *which* repo and *which* capability install the script is
    operating on. Defensive against running the script in the wrong
    project tree (multiple checkouts open, wrong cwd, etc.).
    """
    version = _read_capability_version(capability_root)
    config_path = capability_root / ADOPTER_CONFIG_PATH
    print("bootstrap: project-management capability")
    print(f"  target repo: {repo}")
    print(f"  capability:  {capability_root} (v{version})")
    print(f"  config:      {config_path}")
    print()


def _resolve_repo_name_with_owner() -> str:
    """Best-effort `<owner>/<repo>` for the current working tree.

    Returns `<unresolved>` when `gh repo view` fails — the calling code
    surfaces that to the user as part of the header so they can abort
    before any mutation.
    """
    proc = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner"],
        capture_output=True,
        text=True,
        check=False,
    )
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
        data = YAML(typ="safe").load(pkg.read_text(encoding="utf-8")) or {}
        return str(data.get("component", {}).get("version", "<unknown>"))
    except (OSError, YAMLError):
        return "<unknown>"


def _print_report(actions: list[Action]) -> None:
    print()
    print("Result:")
    created = sum(1 for a in actions if a.status == "created")
    exists = sum(1 for a in actions if a.status == "exists")
    skipped = sum(1 for a in actions if a.status == "skipped")
    failed = sum(1 for a in actions if a.status == "failed")
    for a in actions:
        marker = {
            "created": "[created]",
            "exists": "[exists] ",
            "skipped": "[skipped]",
            "failed": "[failed] ",
        }[a.status]
        line = f"  {marker} {a.label}"
        if a.detail:
            line += f"  {a.detail}"
        print(line)
    print()
    print(
        f"Bootstrap complete. Created {created}; skipped {exists} existing; "
        f"{skipped} by mode; {failed} failed."
    )


if __name__ == "__main__":
    sys.exit(main())
