"""The Projects-v2 board READ seam — name → id resolution for a board field write.

A field-value write (`_lib/substrate_writes.write_field_value`, ADR-031) needs
four **ids**: the project node id, the item (card) id for the issue, the field id,
and — for a single-select — the option id. An adopter's `project/config.yaml`
declares none of them: it carries the board *number* (`projects_v2_board_id`) and
a purely-optional node-id cache. Until now the four ids existed only inside
hand-authored `set-board-field` hook entries, which is why wiring the hook was the
painful "dig the ids out of the API by hand" step report #708 describes.

This module is the read half that removes that step: it resolves the ids from the
**names the adopter already speaks** (the board number in config, the Title-cased
axis name on the board, the classification value). It is the single home for those
reads — the same three reads that previously existed as private copies in
`back-fill.py` (project node id), `adopt-existing.py` (project node id + the live
field/option list) and `create-issue.py` (project node id, cache-first on the hot
create path). `back-fill` and `adopt-existing` now delegate here (per COR-007:
the third copy is where the shape gets extracted, not re-typed).

Reads only
----------
Nothing here mutates. The module resolves ids and reports what the board offers;
the *write* is constructed and executed exclusively by
`_lib/substrate_writes` (ADR-031's sole constructor), and board **membership**
(`gh project item-add`) is deliberately absent — it is a different operation
(DEC-019, named OUT of ADR-031 point 3), and a verb that sets a *field* has no
business granting membership. A missing card is therefore *reported*
(`ItemLookup(ok=True, item_id=None)`), for the caller to refuse on with a
remediation, exactly as `back-fill` reports "blocked — needs board membership".

Failure-posture neutrality (as in `substrate_writes`)
----------------------------------------------------
Every read returns a result object carrying `ok` plus, on failure, `gh`'s stderr
**verbatim** in `error`. A missing `read:project` scope is the single most likely
failure in practice, and its remedy lives in that stderr (`gh auth refresh -s
project`) — so the seam never paraphrases or swallows it. The caller decides what
a failure means (refuse, skip, warn); this module takes no view.

Injectable `gh_call`
--------------------
Each read accepts `gh_call`, the callable that actually shells out, defaulting to
the right constructor for the operation: `gh project` reads go through
`gh_project_run` (the #453 sole constructor that threads `GH_HOST` and splices
`--owner`), the GraphQL read through `gh_run`. Callers that already own a `gh`
seam — the delegating `back-fill` / `adopt-existing` wrappers, and tests — pass
their own, keeping their existing invocation path and patch point unchanged.

Exports:

    ProjectLookup / BoardFieldsRead / ItemLookup — the three read results
    board_number(config)            — the configured board NUMBER, or None
    default_owner(config)           — `gh.default_owner`, or None
    read_project_node_id(...)       — board number → project node id (rich)
    resolve_project_node_id(...)    — the same, as a bare `str | None`
    read_fields(...)                — the board's live fields + their options
    resolve_item_id(...)            — the issue's card (item) id on that board
    find_field / field_names / field_type / is_single_select
    option_id / option_names        — name → id matching over a read field
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Sibling module — the gh shell-out helpers that pin the adopter's host/owner
# (DEC-023). Imported the way `_lib.hooks` / `_lib.substrate_writes` do, with a
# defensive fallback for unusual import contexts (a test that loads a module by
# file path may not have `_lib` on sys.path).
try:
    from gh import gh_project_run, gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - defensive import fallback
    try:
        from _lib.gh import gh_project_run, gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_project_run = None  # type: ignore[assignment]
        gh_run = None  # type: ignore[assignment]


GhCall = Callable[..., "subprocess.CompletedProcess[str]"]

# GraphQL type names Projects v2 uses for its field kinds. Only the single-select
# kind is resolvable to an option id from a NAME, which is the whole mechanism
# here; the others are named so a refusal can say which kind it found.
SINGLE_SELECT_TYPE = "ProjectV2SingleSelectField"

# Bound on the per-issue card lookup. An issue on more than this many boards is
# not a case worth paginating for — the caller reports "not on the board" and the
# adopter's remediation (add the card) is the same either way.
_MAX_PROJECT_ITEMS = 100


@dataclass(frozen=True)
class ProjectLookup:
    """Outcome of resolving the board NUMBER to its project node id."""

    ok: bool
    node_id: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class BoardFieldsRead:
    """Outcome of reading the board's live fields (each with its options)."""

    ok: bool
    fields: tuple[dict[str, Any], ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ItemLookup:
    """Outcome of resolving the issue's card (item) id on the board.

    `ok=True, item_id=None` is the **membership** case — the read succeeded and
    the issue is genuinely not on the board (board membership is a post-creation
    step, so a just-filed issue may have no card yet). That is distinct from
    `ok=False`, which means the read itself failed and nothing is known.
    """

    ok: bool
    item_id: str | None = None
    error: str | None = None


# ----- config readers ----------------------------------------------------


def board_number(config: dict[str, Any]) -> str | None:
    """The configured board NUMBER as a string, or None when no board is configured.

    None covers both "the flag is off" (`has_projects_v2_board` falsey/absent) and
    "the flag is on but `projects_v2_board_id` is unset" — the two states every
    existing board reader collapses, since neither yields a board to read.
    pre-check is the gate that tells the adopter *which* of the two they are in.
    """
    if not isinstance(config, dict) or not config.get("has_projects_v2_board"):
        return None
    number = config.get("projects_v2_board_id")
    if number is None:
        return None
    return str(number)


def default_owner(config: dict[str, Any]) -> str | None:
    """The adopter's configured `gh.default_owner`, or None."""
    gh_block = config.get("gh") if isinstance(config, dict) else None
    if isinstance(gh_block, dict):
        owner = gh_block.get("default_owner")
        if isinstance(owner, str) and owner:
            return owner
    return None


# ----- the three reads ---------------------------------------------------


def read_project_node_id(
    config: dict[str, Any],
    *,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> ProjectLookup:
    """Resolve the board NUMBER to its Projects-v2 project node id (`PVT_…`).

    A `gh project view --format json` read of `.id` — the same read `pre-check`
    runs to verify the board resolves. The cached `projects_v2_node_id` is
    deliberately NOT consulted: a caller that also reads the board's *fields*
    (which are addressed by board NUMBER) would otherwise risk pairing field ids
    from one board with the node id of another if the cache were stale. The cache
    exists to spare the hot create path a round-trip (`create-issue`, #310); a
    one-issue verb can afford the read and get a guaranteed-consistent pair.

    Returns `ok=False` with `gh`'s stderr verbatim when the read fails, and
    `ok=True, node_id=None` only when the payload carries no usable `id`.
    """
    number = board_number(config)
    if number is None:
        return ProjectLookup(
            ok=False,
            error=(
                "no Projects v2 board configured — project/config.yaml needs "
                "`has_projects_v2_board: true` and `projects_v2_board_id: <number>`."
            ),
        )
    args = ["gh", "project", "view", number, "--format", "json"]
    proc, error = _invoke(args, config, owner=owner, gh_call=gh_call)
    if proc is None:
        return ProjectLookup(ok=False, error=error)
    payload = _parse_json(proc.stdout)
    if payload is None:
        return ProjectLookup(
            ok=False,
            error=f"`gh project view {number}` returned non-JSON output.",
        )
    node_id = payload.get("id") if isinstance(payload, dict) else None
    if isinstance(node_id, str) and node_id:
        return ProjectLookup(ok=True, node_id=node_id)
    return ProjectLookup(
        ok=True,
        node_id=None,
        error=f"`gh project view {number}` returned no project id.",
    )


def resolve_project_node_id(
    config: dict[str, Any],
    *,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> str | None:
    """The board's project node id, or None on any failure.

    The lossy form of :func:`read_project_node_id`, for callers whose contract is
    already "None means no board resolvable" (`back-fill`'s residual gate,
    `adopt-existing`'s inventory).
    """
    return read_project_node_id(config, owner=owner, gh_call=gh_call).node_id


def read_fields(
    config: dict[str, Any],
    *,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> BoardFieldsRead:
    """The board's live fields, each with its `id`, `name`, `type` and `options`.

    A `gh project field-list --format json` read. This is the payload every
    name-based resolution needs: the field whose NAME matches an axis, and (for a
    single-select) the option whose NAME matches the value. Options come back on
    the same read, which is what lets a refusal name what the board actually
    offers rather than only what was missing.

    `ok=False` carries `gh`'s stderr verbatim — the missing-`read:project`-scope
    case, whose remedy is in that text.
    """
    number = board_number(config)
    if number is None:
        return BoardFieldsRead(
            ok=False,
            error=(
                "no Projects v2 board configured — project/config.yaml needs "
                "`has_projects_v2_board: true` and `projects_v2_board_id: <number>`."
            ),
        )
    args = ["gh", "project", "field-list", number, "--format", "json"]
    proc, error = _invoke(args, config, owner=owner, gh_call=gh_call)
    if proc is None:
        return BoardFieldsRead(ok=False, error=error)
    payload = _parse_json(proc.stdout)
    if payload is None:
        return BoardFieldsRead(
            ok=False,
            error=f"`gh project field-list {number}` returned non-JSON output.",
        )
    fields = payload.get("fields") if isinstance(payload, dict) else payload
    if not isinstance(fields, list):
        return BoardFieldsRead(
            ok=False,
            error=f"`gh project field-list {number}` returned no `fields` list.",
        )
    return BoardFieldsRead(
        ok=True, fields=tuple(f for f in fields if isinstance(f, dict))
    )


def resolve_item_id(
    config: dict[str, Any],
    *,
    issue_node_id: str,
    project_node_id: str,
    gh_call: GhCall | None = None,
) -> ItemLookup:
    """The issue's card (item) node id on `project_node_id`, via one GraphQL read.

    Keyed on the ISSUE's own node id (`gh issue view --json id`) rather than on
    (repo, number): the issue is the thing we hold, and asking it for its
    `projectItems` needs no owner/repo re-derivation and cannot collide with a
    same-numbered issue from another repo on the same board — the collision
    `back-fill` has to defend against when it walks the whole board's items for a
    BULK plan. The two shapes are complementary: this is the one-issue lookup.

    Archived cards are included: an archived item still has field values worth
    writing, so reporting it as "not on the board" would send the adopter to add a
    duplicate card.

    Returns `ok=True, item_id=None` when the issue is simply not on this board
    (the membership case — the caller refuses with a remediation), and `ok=False`
    with stderr verbatim when the read failed.
    """
    query = (
        "query($issue: ID!) { node(id: $issue) { ... on Issue { "
        f"projectItems(first: {_MAX_PROJECT_ITEMS}, includeArchived: true) "
        "{ nodes { id project { id } } } } } }"
    )
    args = [
        "gh", "api", "graphql",
        "-f", f"query={query}",
        "-F", f"issue={issue_node_id}",
    ]
    proc, error = _invoke(args, config, owner=None, gh_call=gh_call)
    if proc is None:
        return ItemLookup(ok=False, error=error)
    payload = _parse_json(proc.stdout)
    if not isinstance(payload, dict):
        return ItemLookup(
            ok=False, error="`gh api graphql` returned non-JSON output for the card lookup."
        )
    node = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
    issue_block = node.get("node") if isinstance(node.get("node"), dict) else {}
    items = issue_block.get("projectItems") if isinstance(issue_block, dict) else None
    nodes = items.get("nodes") if isinstance(items, dict) else None
    for item in nodes or []:
        if not isinstance(item, dict):
            continue
        project = item.get("project")
        project_id = project.get("id") if isinstance(project, dict) else None
        item_id = item.get("id")
        if project_id == project_node_id and isinstance(item_id, str) and item_id:
            return ItemLookup(ok=True, item_id=item_id)
    return ItemLookup(ok=True, item_id=None)


# ----- name → id matching over a read field ------------------------------


def find_field(
    fields: tuple[dict[str, Any], ...] | list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    """The field whose NAME is `name` — exact match first, then case-insensitive.

    Exact-first so an adopter with two fields differing only in case gets the one
    they named; the case-insensitive fallback is there because the kit derives the
    name it looks for by Title-casing an axis (`priority` → `Priority`) and a board
    that spells it `PRIORITY` means the same field. Returns None when nothing
    matches — the caller then names what the board does offer.
    """
    for field in fields:
        if field.get("name") == name:
            return field
    lowered = name.lower()
    for field in fields:
        candidate = field.get("name")
        if isinstance(candidate, str) and candidate.lower() == lowered:
            return field
    return None


def field_names(
    fields: tuple[dict[str, Any], ...] | list[dict[str, Any]]
) -> list[str]:
    """Every field name on the board, in read order — for a diagnostic."""
    return [f["name"] for f in fields if isinstance(f.get("name"), str)]


def field_type(field: dict[str, Any]) -> str:
    """The field's Projects-v2 type name (e.g. `ProjectV2SingleSelectField`)."""
    value = field.get("type")
    return value if isinstance(value, str) else "<unknown>"


def is_single_select(field: dict[str, Any]) -> bool:
    """True when `field` is a single-select — the only kind resolvable by NAME.

    A text / number / date / iteration field has no option vocabulary to match a
    classification value against, so writing one would mean inventing a
    serialisation for the value. Out of scope by decision (#724): the caller
    refuses with the type it found rather than mangling it.
    """
    return field_type(field) == SINGLE_SELECT_TYPE


def option_names(field: dict[str, Any]) -> list[str]:
    """Every option name declared on a single-select field, in board order."""
    options = field.get("options")
    if not isinstance(options, list):
        return []
    return [
        o["name"]
        for o in options
        if isinstance(o, dict) and isinstance(o.get("name"), str)
    ]


def option_id(field: dict[str, Any], value: str) -> str | None:
    """The option id whose NAME is `value` — exact match first, then case-insensitive.

    Same matching rule as :func:`find_field`, for the same reason: the value comes
    from the adopter's classification vocabulary and the board's own spelling of it
    may differ only in case. None when no option matches.
    """
    options = field.get("options")
    if not isinstance(options, list):
        return None
    lowered = value.lower()
    fallback: str | None = None
    for option in options:
        if not isinstance(option, dict):
            continue
        name = option.get("name")
        oid = option.get("id")
        if not (isinstance(name, str) and isinstance(oid, str) and oid):
            continue
        if name == value:
            return oid
        if fallback is None and name.lower() == lowered:
            fallback = oid
    return fallback


# ----- invocation --------------------------------------------------------


def _invoke(
    args: list[str],
    config: dict[str, Any],
    *,
    owner: str | None,
    gh_call: GhCall | None,
) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    """Run one read; return `(proc, None)` on success or `(None, verbatim_error)`.

    `gh project` reads go through `gh_project_run` (the #453 sole constructor,
    which owns the `--owner` flag and threads `GH_HOST`); anything else through
    `gh_run`. A caller-supplied `gh_call` replaces the default and receives the
    same keyword arguments, so a caller that owns its own `gh` seam keeps it.
    """
    is_project_call = args[:2] == ["gh", "project"]
    runner = gh_call
    if runner is None:
        runner = gh_project_run if is_project_call else gh_run
    if runner is None:  # pragma: no cover - defensive import fallback
        return None, "the `gh` helper is unavailable in this import context."
    try:
        if is_project_call:
            proc = runner(args, config, fallback_owner=owner, check=False)
        else:
            proc = runner(args, config, check=False)
    except FileNotFoundError:
        return None, "`gh` not on PATH. Install GitHub CLI."
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip() or "no stderr"
        return None, stderr
    return proc, None


def _parse_json(stdout: str) -> Any:
    """Parse `stdout` as JSON, or return None when it is not JSON at all."""
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None
