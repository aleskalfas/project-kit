"""pkit CLI entry point.

Phase 1 (foundation) shipped the dispatcher skeleton with `version`.
Phase 2 ports the bash dispatcher's commands one at a time:
PR-D adds `init`; PR-E adds `status`; PR-F adds `new decision`. Phase 3
adds the new COR-004 surface (sync, merge, upgrade, validate,
the rest of new).
"""

from __future__ import annotations

import math
import os
import shlex
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap

    from project_kit.capabilities import CapabilitySource, MandatoryUpstream

from project_kit import (
    __version__,
    cli_render,
    default_branch,
    friction_check,
    friction_report,
    friction_repository,
    friction_resolve,
    friction_write,
    pull_request_landing,
    router,
    scratchpads,
)
from project_kit import refs as refs_mod
from project_kit.agents import STORYBOARD_FILE, stamp_new_agent
from project_kit.decisions import stamp_decision
from project_kit.dispatcher import CapabilityDispatchGroup
from project_kit.install import (
    InitTargetReason,
    find_source_kit,
    find_target_root,
    install_kit,
    refuse_if_pkit_present,
    refuse_propagation_into_source,
    resolve_init_target,
    scan_pkit_installs,
    source_checkout_root,
    sync_remedy,
)
from project_kit.merge import run_merge
from project_kit.release import (
    ReleasePlan,
    apply_release,
    check_changesets,
    check_raised_ranges,
    check_shareable,
    compute_release,
    lint_release_format,
    merge_release_pr,
    migration_dir_mismatches,
    publish_release_notes,
    release_summary,
)
from project_kit.scaffolds import (
    AreaVariant,
    MigrationScope,
    MigrationTier,
    register_kit_shipped_component,
    stamp_adapter,
    stamp_area,
    stamp_capability,
    stamp_migration,
)
from project_kit.scratchpads import (
    stamp_new_scratchpad,
    stamp_reported,
    transition_to_done,
    transition_to_dropped,
)
from project_kit.status import report_status
from project_kit.storyboards import ArtifactKind, stamp_new_storyboard
from project_kit.sync import run_sync
from project_kit.upgrade import (
    freeze_at_content,
    reconcile_pin,
    run_tool_update,
    run_upgrade,
)
from project_kit.versioning import (
    PreKind,
    Segment,
    bump_pre,
    bump_version,
    promote_version,
    tag_version,
    unbump_version,
    untag_version,
)

if TYPE_CHECKING:
    from project_kit.process import ProcessEngine
    from project_kit.process_graph import Graph


@click.group(cls=CapabilityDispatchGroup, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="pkit")
@click.option(
    "--color",
    type=click.Choice(["auto", "always", "never"]),
    default="auto",
    show_default=True,
    help="Colourize human output: auto (TTY only) | always | never. Honours "
    "NO_COLOR; never load-bearing — plain text carries all structure (ADR-011).",
)
@click.pass_context
def main(ctx: click.Context, color: str) -> None:
    """project-kit CLI.

    Installed capabilities surface their subcommands lazily via the
    `CapabilityDispatchGroup` — namespaces resolve from the backbone
    manifest on every invocation, per [COR-021].
    """
    # The command boundary: resolve the colour decision once per process
    # (ADR-011 §2), so style() never has to sniff a stream it can't see.
    # Mirror the decision onto ctx.color so Click's echo honours it rather than
    # re-deciding (and stripping our SGR) by its own tty sniff.
    ctx.color = cli_render.resolve_color(color)
    # The second environment dimension, resolved the same way (ADR-024 §3): wrap
    # width once at the boundary, so wrap() never sniffs isatty() itself. Piped
    # is always no-wrap regardless of COLUMNS (the deliberate divergence from
    # colour's override precedence).
    cli_render.resolve_width()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.group()
def capabilities() -> None:
    """Manage installed capabilities (per COR-017): list, show, install, uninstall, upgrade.

    Noun-first, consistent with the other resource-domain groups
    (`schemas`, `permissions`, `refs`, `hooks`, `migrations`).
    """


@main.group("agents", invoke_without_command=True)
@click.pass_context
def agents(ctx: click.Context) -> None:
    """Inspect kit-shipped agents + their overlay-category resolution (per COR-013).

    No subcommand: report which agents will deploy vs. be skipped. An agent is
    skipped only when it references a category the project overlay doesn't define
    through a *hard* channel (`owns`/`needs`/`answers`/`reads.paths`/`reads.records`);
    a category referenced *only* via `reads.patterns` is an optional read (ADR-052)
    whose absence never skips — the agent deploys without it, and such undefined
    categories are surfaced in an `Optional` footer state. Each row also shows the
    agent's effective model and effort: the overlay's `overrides.<agent>` value,
    else the front matter's, else `inherit`. Deployment itself happens via
    `pkit sync`; configuration is `.pkit/agents/project/overlay.yaml`.
    """
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import agents_overlay as ao

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(ao.render_status(target_root), nl=False)


@agents.command("reconcile")
@click.option(
    "--write",
    is_flag=True,
    default=False,
    help="Append the missing categories to the overlay (default: dry-run, show only).",
)
def agents_reconcile(write: bool) -> None:
    """Surface referenced-but-undefined overlay categories into overlay.yaml as
    commented stubs (per COR-013). Explicit + idempotent; dry-run by default."""
    from project_kit import agents_overlay as ao

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        _added, report = ao.reconcile_overlay(target_root, write=write)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report, nl=False)


@agents.command("adopt")
@click.argument("agent_name", metavar="AGENT")
def agents_adopt(agent_name: str) -> None:
    """Create the conventional doc dirs, wire the overlay, and deploy AGENT.

    For each overlay category the agent references that is not yet defined in
    `.pkit/agents/project/overlay.yaml`:

    \b
    1. Creates the conventional default directory if absent (with a seed README
       explaining the directory's purpose).
    2. Writes the category into the overlay uncommented with the conventional path.
       An adopter-set value is never overwritten.

    An optional category (read only through `reads.patterns`) with no conventional
    default is left undefined and reported; the agent deploys without it.

    Then runs the adapter's deploy step so the agent ends up in `.claude/agents/`.

    Idempotent: re-running on an already-adopted agent reports no changes and
    re-deploys (the deploy step is itself idempotent).
    """
    from project_kit import agents_overlay as ao

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        result = ao.adopt_agent(target_root, agent_name)
    except click.ClickException:
        raise
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    lines: list[str] = []
    if result.dirs_created:
        lines.append(
            cli_render.style("strong", f"created {len(result.dirs_created)} director(ies):")
        )
        for d in result.dirs_created:
            lines.append(f"  {d}/")
            lines.append("    (seed README.md written explaining the directory's purpose)")
    if result.categories_wired:
        lines.append(
            cli_render.style(
                "strong", f"wired {len(result.categories_wired)} overlay categor(ies):"
            )
        )
        for cat in result.categories_wired:
            lines.append(f"  {cat}")
    if result.categories_already_set:
        lines.append(
            cli_render.style(
                "strong",
                f"{len(result.categories_already_set)} categor(ies) already defined (unchanged):",
            )
        )
        for cat in result.categories_already_set:
            lines.append(f"  {cat}")
    if result.categories_optional_unset:
        lines.append(
            cli_render.style(
                "strong",
                f"{len(result.categories_optional_unset)} optional categor(ies) left undefined "
                f"(the agent deploys without them):",
            )
        )
        for cat in result.categories_optional_unset:
            lines.append(f"  {cat}")
        lines.append(
            "  to give the agent your corpus: `pkit agents reconcile --write`, "
            "set real paths in overlay.yaml, then `pkit sync`."
        )
    if not result.dirs_created and not result.categories_wired:
        lines.append(
            cli_render.style(
                "strong",
                f"agent {agent_name!r}: no overlay changes needed."
                if result.categories_optional_unset
                else f"agent {agent_name!r}: overlay already complete — no changes.",
            )
        )
    if result.deployed:
        lines.append("")
        lines.append(cli_render.style("strong", f"agent {agent_name!r} deployed."))
    click.echo("\n".join(lines))


def _target_kit() -> Path:
    """The `.pkit/` of the project the `version` / `release` commands operate on.

    Resolved from the working directory (`find_target_root`, the same root every
    other command uses), **not** from `find_source_kit()`: that one follows the
    interpreter's own location, so with an editable install it names the checkout
    that owns the virtualenv whatever the cwd — and `release check` run from a git
    worktree would silently diff the main checkout instead (#877). The two roots
    coincide in the common self-host case (running from the checkout itself);
    when they differ, say so once on stderr so the operator knows which tree the
    command is reading and writing. Not an error — a worktree of the same repo is
    a legitimate place to run from.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    target_kit = target_root / ".pkit"
    if not target_kit.is_dir():
        raise click.ClickException(f"no .pkit/ at {target_root} — not a project-kit project.")
    checkout = source_checkout_root()
    if checkout is not None and checkout != target_root:
        click.echo(
            f"note: operating on {target_root} (working directory), "
            f"not on the checkout that owns this pkit ({checkout}).",
            err=True,
        )
    return target_kit


@main.group("config")
def config() -> None:
    """The backbone configuration file, `.pkit/project/config.yaml` (COR-048).

    Every key is owned by a core record and checked by `pkit validate`; the
    keys are documented in `.pkit/cli/README.md`, "Configuration file".
    """


@config.command("set")
@click.argument("key", metavar="KEY")
@click.argument("value", metavar="VALUE")
@click.option(
    "--yes", is_flag=True, default=False, help="Consent to the write without a prompt (CI)."
)
def config_set(key: str, value: str, yes: bool) -> None:
    """Set one backbone-owned KEY (dotted, e.g. `docs.internal`) to VALUE.

    The key must exist in the configuration schema and hold a single value;
    the reserved `project` block is never written. The result is validated
    before anything is written — an invalid value is refused. Writing needs
    consent (COR-048 point 5): an interactive confirmation, or `--yes`; a
    non-interactive run without `--yes` refuses and names the command to run.
    """
    from project_kit import backbone_schemas, project_config

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        schema = project_config.load_config_schema(target_root)
    except backbone_schemas.BackboneSchemaMissing as exc:
        raise click.ClickException(
            "this tree ships no backbone configuration schema, so keys cannot be checked; "
            "run `pkit sync` first."
        ) from exc
    resolved = project_config.resolve_key(schema, key)
    typed = project_config.coerce_value(resolved, value)

    def mutate(data: CommentedMap) -> None:
        project_config.set_value(data, resolved, typed)

    if not project_config.preview_config(target_root, mutate).changes:
        click.echo(f"{resolved.dotted} is already {typed}; nothing to write.")
        return
    rerun = f"pkit config set {shlex.quote(key)} {shlex.quote(value)} --yes"
    project_config.write_config(
        target_root,
        mutate,
        consent=project_config.Consent(yes=yes, rerun=rerun),
        description=f"Set {resolved.dotted} = {typed!r}",
    )
    click.echo(
        f"set {resolved.dotted} = {typed}  ({project_config.PROJECT_CONFIG_RELPATH.as_posix()})"
    )
    # The `.pkit/.gitignore` render reads the configuration (the process
    # journal's ignore line, COR-033 point 7): follow the new value now rather
    # than at the next sync, naming each component entry the render now leaves out.
    from project_kit import visibility as vis

    refreshed = vis.refresh_runtime_ignore(target_root)
    if refreshed is not None:
        click.echo(refreshed.report())


@main.group("docs")
def docs() -> None:
    """Documentation roots and the locations derived from them (COR-049).

    The roots are the configuration's `docs` key (`pkit config set
    docs.internal <path>`); `pkit status` shows them and every recorded
    location. Reference: `.pkit/cli/README.md`, "Configuration file".
    """


@docs.command("record-location")
@click.argument("capability", metavar="CAPABILITY")
@click.argument("name", metavar="NAME")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Consent to the write without a prompt (CI). Without it a terminal is asked; "
    "a non-interactive run refuses.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Say what would be recorded, and write nothing.",
)
def docs_record_location(capability: str, name: str, yes: bool, dry_run: bool) -> None:
    """Record where CAPABILITY's documentation location NAME now lies (COR-049 point 5).

    NAME is a location the capability declares in its package metadata
    (`docs.locations`), never a path. Until it is recorded it derives from a
    documentation root; the command writes where it lies now to the
    capability's `project/docs-locations.yaml`, so a later change of root
    moves nothing already written. A location already recorded is never
    overwritten: the command says where it lies and writes nothing. Writing
    needs consent (COR-048 point 5): a terminal is asked once, `--yes`
    consents non-interactively, and a non-interactive run without `--yes`
    refuses and names the command to run; `--dry-run` says what would be
    recorded and writes nothing. A capability's stamping command runs it with
    `--yes` when it places the first document there. Exit 1 when CAPABILITY
    is not installed or declares no location NAME.
    """
    from project_kit import docs_roots, project_config
    from project_kit.friction_discovery import installed_capability_names

    if yes and dry_run:
        raise click.UsageError(
            "--yes and --dry-run exclude each other: one writes, the other never does."
        )
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if capability not in installed_capability_names(target_root):
        raise click.ClickException(f"no capability named {capability!r} is installed.")
    found = docs_roots.capability_location(target_root, capability, name)
    if found is None:
        declared = sorted(docs_roots.capability_subpaths(target_root, capability))
        raise click.ClickException(
            f"{capability} declares no documentation location {name!r} in its "
            f"`docs.locations` (declared: {', '.join(declared) or 'none'})."
        )
    where = found.path.as_posix()
    if found.source is docs_roots.Source.EXPLICIT:
        click.echo(f"{capability} {name} = {where}  (recorded already)")
        return
    recorded_in = docs_roots.capability_locations_relpath(capability).as_posix()
    recording = f"{capability} {name} = {where}  ({recorded_in})"
    if dry_run:
        click.echo(f"would record {recording}")
        click.echo(cli_render.style("strong", "Dry run: nothing written."))
        return
    if not yes:
        if not project_config.stdin_is_tty():
            rerun = f"pkit docs record-location {shlex.quote(capability)} {shlex.quote(name)}"
            raise project_config.ConsentRefused(
                f"refusing to write {recorded_in} without consent: stdin is not a terminal "
                f"and --yes was not given (COR-048 point 5). Nothing was written.\n"
                f"To see the change first, run:\n  {rerun} --dry-run\n"
                f"To consent non-interactively, run:\n  {rerun} --yes"
            )
        click.confirm(
            f"Record {capability} {name} = {where} in {recorded_in}?", default=True, abort=True
        )
    docs_roots.record_location(
        target_root, capability, name, found.path, by="pkit docs record-location"
    )
    click.echo(f"recorded {recording}")


@main.group("repository")
def repository() -> None:
    """Facts about the repository every reader takes from one place (COR-054).

    The default branch is the configuration's `repository` key (`pkit config
    set repository.default-branch <name>`). Reference: `.pkit/cli/README.md`,
    "Configuration file".
    """


@repository.command("base")
@click.option(
    "--base",
    "base_ref",
    metavar="REF",
    default=None,
    help=f"The base to read: REF, instead of ${default_branch.CHECK_BASE_ENV}, else the "
    "default branch. A branch name resolves as the default branch does.",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit the stable JSON document."
)
def repository_base_command(base_ref: str | None, as_json: bool) -> None:
    """The default branch and the base a comparison reads (COR-054 point 5).

    The default branch: declared (`repository.default-branch`, else `main`)
    and resolved — the remote-tracking reference of its upstream, else
    origin/<name>, and the local branch only when there is no remote. The
    base: REF, else $PKIT_CHECK_BASE, else the default branch — its commit,
    where HEAD left it and whether it moved on since. A reader that used a
    local branch, and a declaration read as the default, say so on standard
    error. Read-only; it runs no discovery. It is how a capability's own
    script reads which commit is settled, without resolving a branch or
    computing a merge-base itself. Exit 0 when answered — a branch or base
    that resolves nowhere is an answer, with its problem; 2 on a usage error.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    settled = default_branch.settled(target_root, base_ref)
    _warn_settled(settled)
    document = settled.as_json()
    if as_json:
        click.echo(default_branch.render_json(document), nl=False)
    else:
        click.echo(default_branch.render_human(document), nl=False)


def _warn_settled(settled: default_branch.Settled) -> None:
    """What a reader of settled state says about it: a declaration read as the default
    (COR-048 point 4), and a branch read from the local branch (COR-054 point 2)."""
    for warning in settled.warnings:
        click.echo(f"warning: {warning}", err=True)


def _settled_base(target_root: Path, base_ref: str | None) -> default_branch.Base:
    """The base a diff-scoped command compares with — `base_ref`, else
    `$PKIT_CHECK_BASE`, else the default branch (COR-054 point 3) — with where HEAD
    left it; the problem, with its fix, refuses the run (point 4)."""
    settled = default_branch.settled(target_root, base_ref)
    found = settled.base
    if found.problem is not None or found.fork is None:
        raise click.ClickException(found.problem or f"the base {found.ref!r} cannot be compared.")
    _warn_settled(settled)
    return found


@main.group("pull-request")
def pull_request() -> None:
    """Landing a pull request on the hosting service — the one merge mechanic.

    Where a pull request's base merges through a merge queue, and where the PR
    stands in it; the repository's squash-commit defaults; the direct squash
    merge, the enqueue, the wait for the queue's merge and taking a PR out of
    the queue. Each runs `gh` from the working directory. `--json` writes each
    document as one line of JSON, which is how a capability's script calls it.
    Reference: `.pkit/cli/README.md`, "Pull-request commands".
    """


def _pull_request_json_option(command: Callable[..., None]) -> Callable[..., None]:
    return click.option(
        "--json",
        "as_json",
        is_flag=True,
        default=False,
        help="Write the document as one line of JSON.",
    )(command)


def _say_outcome(
    number: int,
    outcome: pull_request_landing.Outcome,
    as_json: bool,
    done: str,
) -> None:
    """Write a request's outcome — `done` when accepted — and exit 1 when it was not."""
    if as_json:
        click.echo(
            pull_request_landing.render_json(pull_request_landing.outcome_document(number, outcome))
        )
    elif outcome.accepted:
        click.echo(done)
    else:
        click.echo(f"error: {outcome.reason or 'gh refused it'}", err=True)
    if not outcome.accepted:
        raise SystemExit(1)


@pull_request.command("read")
@click.argument("number", type=int)
@_pull_request_json_option
def pull_request_read(number: int, as_json: bool) -> None:
    """Whether PR NUMBER's base merges through a queue, and where the PR stands.

    Read-only. Exit 0 when read; 1 when GitHub could not be read, with why.
    """
    document = pull_request_landing.reading_document(number)
    reading = document["reading"]
    if as_json:
        click.echo(pull_request_landing.render_json(document))
    elif reading is not None:
        if reading["has_queue"]:
            method = str(reading["merge_method"] or "an unreported method").lower()
            base = f"merges through a queue, by {method}"
        else:
            base = "merges directly"
        click.echo(f"PR #{number}: {reading['description']}\nBase: {base}")
    else:
        click.echo(f"error: PR #{number} could not be read: {document['unreadable']}", err=True)
    if reading is None:
        raise SystemExit(1)


@pull_request.command("squash-defaults")
@_pull_request_json_option
def pull_request_squash_defaults(as_json: bool) -> None:
    """The repository's default squash-commit title and message.

    A merge queue composes its squash commit from these. Read-only. Exit 0
    when read; 1 when they could not be read, with why.
    """
    document = pull_request_landing.squash_defaults_document()
    if as_json:
        click.echo(pull_request_landing.render_json(document))
    elif document["unreadable"] is None:
        click.echo(f"Squash commit: title {document['title']}, message {document['message']}")
    else:
        click.echo(f"error: {document['unreadable']}", err=True)
    if document["unreadable"] is not None:
        raise SystemExit(1)


@pull_request.command("merge")
@click.argument("number", type=int)
@click.option("--subject", required=True, help="The squash commit's subject: the PR title.")
@click.option("--head", "head_oid", default="", metavar="SHA", help="Merge only at this head.")
@click.option("--admin", is_flag=True, default=False, help="Merge around branch protection.")
@_pull_request_json_option
def pull_request_merge(
    number: int, subject: str, head_oid: str, admin: bool, as_json: bool
) -> None:
    """Squash-merge PR NUMBER directly, with SUBJECT as the commit's subject.

    Accepted is not proof of a merge: on a base that requires a queue, gh
    enqueues instead — `pull-request read` says which. Never deletes the head
    branch. Exit 0 when gh accepted it; 1 otherwise, with gh's reason.
    """
    outcome = pull_request_landing.squash_merge(
        number, subject=subject, head_oid=head_oid, admin=admin
    )
    _say_outcome(number, outcome, as_json, f"gh accepted the squash merge of PR #{number}")


@pull_request.command("enqueue")
@click.argument("number", type=int)
@click.option("--head", "head_oid", default="", metavar="SHA", help="Enqueue only this head.")
@_pull_request_json_option
def pull_request_enqueue(number: int, head_oid: str, as_json: bool) -> None:
    """Hand PR NUMBER to its base's merge queue; the queue makes the merge.

    The queue squashes by its own method, with a commit composed from the
    repository's squash-commit defaults. Exit 0 once GitHub took it in; 1
    otherwise, with gh's reason.
    """
    outcome = pull_request_landing.enqueue(number, head_oid=head_oid)
    _say_outcome(number, outcome, as_json, f"enqueued PR #{number}")


@pull_request.command("dequeue")
@click.argument("number", type=int)
@_pull_request_json_option
def pull_request_dequeue(number: int, as_json: bool) -> None:
    """Take PR NUMBER out of its base's merge queue, and confirm it is out.

    Exit 0 once a reading shows it neither queued nor merged; 1 otherwise.
    """
    outcome = pull_request_landing.dequeue(number)
    _say_outcome(number, outcome, as_json, f"PR #{number} is out of the merge queue")


@pull_request.command("wait")
@click.argument("number", type=int)
@click.option(
    "--head",
    "head_oid",
    default="",
    metavar="SHA",
    help="The head that was checked: a reading at another ends the wait.",
)
@click.option(
    "--seconds",
    type=click.FloatRange(min=0),
    default=None,
    help="How long to wait; 0 reads once. Default: as long as the queue estimates, "
    f"plus {pull_request_landing.ETA_MARGIN_SECONDS / 60:g} min, at most "
    f"{pull_request_landing.MAX_WAIT_SECONDS / 60:g} min.",
)
@_pull_request_json_option
def pull_request_wait(number: int, head_oid: str, seconds: float | None, as_json: bool) -> None:
    """Wait for the merge queue to merge PR NUMBER.

    Writes each reading that changes, then how the wait ended. The PR is
    declared out of the queue only on two readings running. Exit 0 when it
    merged; 4 when the time ran out with it still queued; 3 when it left the
    queue unmerged or its head moved; 1 when GitHub could not be read.
    """
    if seconds is not None and not math.isfinite(seconds):
        raise click.BadParameter("not a number of seconds", param_hint="--seconds")

    def report(reading: pull_request_landing.Reading) -> None:
        if as_json:
            document = pull_request_landing.wait_reading_document(number, reading)
            click.echo(pull_request_landing.render_json(document))
        else:
            click.echo(f"PR #{number} {reading.describe()}")

    try:
        wait = pull_request_landing.wait_for_merge(
            number, timeout_seconds=seconds, on_change=report, head_oid=head_oid
        )
    except pull_request_landing.Unreadable as exc:
        if as_json:
            document = pull_request_landing.wait_end_document(number, None, str(exc))
            click.echo(pull_request_landing.render_json(document))
        else:
            click.echo(f"error: PR #{number} could not be read: {exc}", err=True)
        raise SystemExit(1) from None
    if as_json:
        click.echo(
            pull_request_landing.render_json(pull_request_landing.wait_end_document(number, wait))
        )
    else:
        click.echo(f"ended: {wait.ended}")
    if wait.ended != pull_request_landing.MERGED:
        raise SystemExit(4 if wait.ended == pull_request_landing.STILL_QUEUED else 3)


def _graph_format_options(command: Callable[..., None]) -> Callable[..., None]:
    """The output options both graph commands share (`process graph`, `connections
    graph`): the adjacency view by default, or one of three other formats."""
    options = [
        click.option(
            "--flow",
            "fmt_flow",
            is_flag=True,
            default=False,
            help="ASCII downstream pipeline (work-flows-this-way) instead of the adjacency view.",
        ),
        click.option(
            "--mermaid",
            "fmt_mermaid",
            is_flag=True,
            default=False,
            help="Emit a mermaid flowchart (derived = thick ==>, declared-pull = -->, "
            "push = -.->, resolved = --o).",
        ),
        click.option(
            "--json",
            "fmt_json",
            is_flag=True,
            default=False,
            help="Emit the byte-stable machine form {nodes, edges, skipped} (no styling; "
            "deterministic order).",
        ),
        click.option(
            "--verbose",
            is_flag=True,
            default=False,
            help="Show each edge's `why` (default omits it).",
        ),
    ]
    for option in reversed(options):
        command = option(command)
    return command


def _refuse_several_formats(fmt_flow: bool, fmt_mermaid: bool, fmt_json: bool) -> None:
    if sum([fmt_flow, fmt_mermaid, fmt_json]) > 1:
        raise click.ClickException(
            "choose at most one of --flow / --mermaid / --json (the default is the adjacency view)."
        )


def _echo_graph(
    graph: Graph,
    *,
    fmt_flow: bool,
    fmt_mermaid: bool,
    fmt_json: bool,
    verbose: bool,
    title: str | None = None,
    flow_title: str | None = None,
    empty: str | None = None,
) -> None:
    """Render a graph in the chosen format, through the one set of renderers
    (`process_graph`); the titles default to the process graph's."""
    from project_kit import process_graph as pg

    if fmt_json:
        click.echo(pg.render_json(graph), nl=False)
    elif fmt_mermaid:
        click.echo(pg.render_mermaid(graph), nl=False)
    elif fmt_flow:
        click.echo(
            pg.render_flow(graph, verbose=verbose, title=flow_title or pg.PROCESS_FLOW_TITLE),
            nl=False,
        )
    else:
        click.echo(
            pg.render_adjacency(
                graph,
                verbose=verbose,
                title=title or pg.PROCESS_TITLE,
                empty=empty or pg.PROCESS_EMPTY,
            ),
            nl=False,
        )


@main.group("connections")
def connections_group() -> None:
    """Connection points (COR-053): the one wiring graph, the provider selection, and
    one data point as it resolves.

    The wiring the installed packages and the configuration resolve to is
    reported by `pkit validate` (its `connections` member) and shown by `pkit
    status` (its Connections section). Reference: `.pkit/cli/README.md`,
    "Connections commands".
    """


@connections_group.command("graph")
@_graph_format_options
@click.option(
    "--kind",
    "kinds",
    type=click.Choice(["data", "process", "event"]),
    multiple=True,
    help="Keep only edges of this kind (repeatable). `process` is exactly what "
    "`pkit process graph` renders.",
)
def connections_graph(
    fmt_flow: bool, fmt_mermaid: bool, fmt_json: bool, verbose: bool, kinds: tuple[str, ...]
) -> None:
    """Render the one wiring graph (COR-053 point 7), read-only.

    \b
    Every edge, in the process graph's format:
      derived    subprocess / cascade blocks of the process definitions
      annotated  their depends_on entries (either address form)
      resolved   the wiring resolver: provider → point ← counterparts —
                 accepts / emits / offers from the definer; contributes,
                 subscribes, fills from a counterpart; the mode is how the
                 edge stands (active, conflict, bound, inert (version), …)

    `pkit process graph` is this graph filtered to its process edges, so the
    two never disagree. It reads declarations only: no filler command runs, no
    position resolves. The generated depends-on list of package metadata is not
    drawn — the depends_on edges it copies are.
    """
    from project_kit import process as process_mod
    from project_kit import process_graph as pg
    from project_kit import wiring_graph as wg

    _refuse_several_formats(fmt_flow, fmt_mermaid, fmt_json)
    try:
        graph = wg.build_wiring_graph(process_mod.resolve_repo_root())
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    if kinds:
        graph = wg.with_kinds(graph, kinds)
    # Through the process graph's filter pass, unconstrained: a view shows the
    # nodes its edges touch, exactly as `process graph` renders its own.
    _echo_graph(
        pg.apply_filters(graph, pg.FilterSpec()),
        fmt_flow=fmt_flow,
        fmt_mermaid=fmt_mermaid,
        fmt_json=fmt_json,
        verbose=verbose,
        title=wg.TITLE,
        flow_title=wg.FLOW_TITLE,
        empty=wg.EMPTY,
    )


@connections_group.group("providers")
def connections_providers() -> None:
    """The provider selection (COR-053 point 7): which installed capability answers a
    role several provide — the configuration's `connections.providers` key."""


@connections_providers.command("set")
@click.argument("role", metavar="ROLE")
@click.argument("capability", metavar="CAPABILITY")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Consent to the write without a prompt (CI). Without it a terminal is asked, "
    "after the diff; a non-interactive run refuses.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be written, as a diff, and write nothing.",
)
def connections_providers_set(role: str, capability: str, yes: bool, dry_run: bool) -> None:
    """Select CAPABILITY as the provider of ROLE (`<publisher>::<role>`).

    Writes the `connections.providers` entry of `.pkit/project/config.yaml`
    through the consent-gated writer (COR-048 point 5), after checking that
    CAPABILITY is installed and declares ROLE. The diff is shown first;
    `--dry-run` stops there. A role conflict names this command as its fix.
    """
    from project_kit import connections_config

    if yes and dry_run:
        raise click.UsageError(
            "--yes and --dry-run exclude each other: one writes, the other never does."
        )
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    change = connections_config.plan(target_root, role, capability)
    key = connections_config.key(role)
    if not change.changes:
        click.echo(f"{key} is already {capability}; nothing to write.")
        return
    click.echo(change.diff(), nl=False)
    if dry_run:
        click.echo(cli_render.style("strong", "Dry run: nothing written."))
        return
    path = connections_config.write(target_root, role, capability, yes=yes)
    click.echo(f"set {key} = {capability}  ({path.relative_to(target_root).as_posix()})")


@connections_group.command("resolve")
@click.argument("address", metavar="ADDRESS")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit the stable JSON document."
)
def connections_resolve(address: str, as_json: bool) -> None:
    """Resolve the data point ADDRESS (`<publisher>::<role>:<point>`) and print it.

    The resolution `pkit validate` reports and `pkit status` shows (COR-052):
    the point's value — a `single` point's answer, or the entries of a `union`
    or `additive` point, each with its origin — how it resolved, or why it did
    not, and every filler considered. Read-only; only this point resolves, so
    only its command fillers run, as they do there, offline-marked and
    bounded. Inside a run of `pkit validate` — a validator reading the point —
    it reads the point from the run cache when the run has already resolved it
    (`from: run-cache` in the document); otherwise it resolves the point and
    caches it, so its fillers run once per validate. It is how a capability's
    own script reads a point it defines without importing the backbone. Exit 0
    when the point resolves; 1 when it does not, or when no active provider
    defines it, and the output says why.
    """
    import json

    from project_kit import backbone_schemas, data_points
    from project_kit.status import _data_point_lines

    if backbone_schemas.filler_subpath(address) is None:
        raise click.BadParameter(
            f"{address!r} is not a point address: `<publisher>::<role>:<point>`, each part "
            "a lowercase word.",
            param_hint="ADDRESS",
        )
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    point = data_points.shared_point(target_root, address)
    source, why = data_points.FROM_RUN_CACHE, ""
    if point is None:
        source = data_points.FROM_RESOLUTION
        point, why = data_points.resolve_point(target_root, address)
    if as_json:
        document = (
            data_points.point_document(point, source=source)
            if point is not None
            else data_points.undefined_document(address, why)
        )
        click.echo(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False))
    elif point is not None:
        click.echo("\n".join(_data_point_lines(point)))
    else:
        click.echo(f"{address}: not defined — {why}")
    if point is None or not point.resolved:
        raise SystemExit(1)


@main.group("friction")
def friction() -> None:
    """Anchors and friction (COR-050): the reading commands — the checks, the
    debt listing, one artefact's explanation, the places and artefacts
    discovery finds — which never write, the writers — revalidate, defer,
    record-status — which write one block, only with consent, and resolve,
    which resolves a merge's conflicting revalidations as text and writes no
    answer.

    Reference: `.pkit/cli/README.md`, "Friction checks"; the block itself is
    in `.pkit/schemas/README.md`, "The friction block".
    """


def _friction_consent_options(command: Callable[..., None]) -> Callable[..., None]:
    """`--yes` / `--dry-run`: the consent every friction writer asks for (COR-050 point 13)."""
    command = click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="Show what would be written, as a diff, and write nothing.",
    )(command)
    return click.option(
        "--yes",
        is_flag=True,
        default=False,
        help="Consent to the write without a prompt (CI). Without it a terminal is asked, "
        "after the diff; a non-interactive run refuses.",
    )(command)


def _friction_write(
    plan_of: Callable[[Path, bool], friction_write.Plan],
    yes: bool,
    dry_run: bool,
    rerun: list[str],
) -> None:
    """Build a writer's plan and apply it with the consent given (COR-050 point 13)."""
    if yes and dry_run:
        raise click.UsageError(
            "--yes and --dry-run exclude each other: one writes, the other never does."
        )
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    can_ask = not yes and not dry_run and friction_write.interactive()
    plan = plan_of(target_root, can_ask)
    friction_write.apply(plan, yes=yes, dry_run=dry_run, can_ask=can_ask, rerun=rerun)


@friction.command("revalidate")
@click.argument("artefact", metavar="ARTEFACT")
@click.option(
    "--outcome",
    type=click.Choice(friction_write.OUTCOMES),
    required=True,
    help="`updated`: the content changed with this revalidation; `unchanged`: it did not "
    "need to (then --because is required).",
)
@click.option(
    "--because",
    metavar="TEXT",
    default=None,
    help="With `unchanged`: why the content still holds against this change. Must differ "
    "from the justification already written.",
)
@click.option(
    "--keep",
    "keep",
    metavar="ANCHOR",
    multiple=True,
    help="Keep the deferral of ANCHOR (`kind:value`, or a value only one deferral has). "
    "Repeatable. A deferral not kept is removed; a terminal is asked about each.",
)
@_friction_consent_options
def friction_revalidate_command(
    artefact: str,
    outcome: str,
    because: str | None,
    keep: tuple[str, ...],
    yes: bool,
    dry_run: bool,
) -> None:
    """Write ARTEFACT's revalidation (COR-050 point 3): a fresh `at`, the outcome, and
    for `unchanged` a new `unchanged-because`.

    Rewrites the `revalidated` block and nothing else in the file. Re-states
    the deferrals kept — each named with --keep or confirmed at the prompt —
    and removes the rest (point 4). ARTEFACT is a location (`path`, or
    `path#id` for a collection entry) or an id.
    """
    rerun = ["pkit", "friction", "revalidate", artefact, "--outcome", outcome]
    if because is not None:
        rerun += ["--because", because]
    for anchor in keep:
        rerun += ["--keep", anchor]

    def plan_of(target_root: Path, can_ask: bool) -> friction_write.Plan:
        return friction_write.plan_revalidate(
            target_root,
            artefact,
            outcome=outcome,
            because=because,
            keep=keep,
            confirm_keep=friction_write.ask_keep if can_ask else None,
        )

    _friction_write(plan_of, yes, dry_run, rerun)


@friction.command("defer")
@click.argument("artefact", metavar="ARTEFACT")
@click.option(
    "--anchor",
    metavar="ANCHOR",
    required=True,
    help="The anchor whose friction is postponed: `kind:value`, or a value only one anchor "
    "of the artefact has. It must be one the artefact carries.",
)
@click.option("--reason", metavar="TEXT", required=True, help="Why it is postponed.")
@_friction_consent_options
def friction_defer_command(
    artefact: str, anchor: str, reason: str, yes: bool, dry_run: bool
) -> None:
    """Defer one anchor of ARTEFACT (COR-050 point 4): add its entry to `deferred`,
    or reword the reason of the entry already there.

    Writes the `deferred` list and nothing else — never `at`: a deferral is
    not a revalidation. The entry covers the anchor's changes up to the
    commit that introduces it; rewording its reason does not move that.
    """
    rerun = ["pkit", "friction", "defer", artefact, "--anchor", anchor, "--reason", reason]

    def plan_of(target_root: Path, _can_ask: bool) -> friction_write.Plan:
        return friction_write.plan_defer(target_root, artefact, anchor=anchor, reason=reason)

    _friction_write(plan_of, yes, dry_run, rerun)


@friction.command("record-status")
@click.argument("artefact", metavar="ARTEFACT")
@_friction_consent_options
def friction_record_status_command(artefact: str, yes: bool, dry_run: bool) -> None:
    """Record ARTEFACT's status in its tool-written `last-check` (COR-050 point 10).

    Runs the whole-repository check at HEAD and writes `state` (current,
    stale or deferred), `as-of` (HEAD) and, when stale, `since` — only when
    the state or `since` changes; otherwise it writes nothing and exits 0.
    The command an after-merge job would run; that job is not shipped.
    """
    rerun = ["pkit", "friction", "record-status", artefact]

    def plan_of(target_root: Path, _can_ask: bool) -> friction_write.Plan:
        return friction_write.plan_record_status(target_root, artefact)

    _friction_write(plan_of, yes, dry_run, rerun)


@friction.command("resolve")
@click.argument("paths", metavar="[PATH]...", nargs=-1)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show the resolution, with each file's diff, and write nothing.",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Stage the resolved files without a prompt. Without it a terminal is asked, after "
    "the diffs; a run that cannot ask leaves them unstaged and prints the `git add` to run.",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit the stable JSON document."
)
def friction_resolve_command(
    paths: tuple[str, ...], dry_run: bool, yes: bool, as_json: bool
) -> None:
    """Resolve a merge's conflicting revalidations as text (COR-050 point 3): each file in
    conflict — every one, or each PATH — whose conflicts all lie inside `revalidated` blocks.

    Only git's own conflict, untouched by hand, is resolved: the file's three
    versions are read from the index and merged again, and the result must be
    the working file. Only the blocks git conflicted on are decided: the answer
    from the side that changed it, the deferrals merged by anchor, and where
    both sides revalidated, the base side's answer — only when MERGE_HEAD, the
    branch merged in, is the change check's base. Any other conflict leaves the
    file as git left it, and says where. The file is written; it is staged only
    with --yes or at the prompt. It writes no answer: for each artefact both
    sides revalidated it names the revalidation owed once the merge is
    committed, `updated` or `unchanged` as its content bears out against the
    base side's. PATH is relative to the project root. Outside a merge there is
    nothing to resolve. Exit 1 when it leaves an artefact's file in conflict.
    """
    if yes and dry_run:
        raise click.UsageError(
            "--yes and --dry-run exclude each other: one stages, the other writes nothing."
        )
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    resolution = friction_resolve.plan_resolve(target_root, paths)
    written = () if dry_run else friction_resolve.write(target_root, resolution)
    staged: tuple[str, ...] = ()
    if as_json:
        if yes and written:
            staged = friction_resolve.stage(target_root, written)
        click.echo(
            friction_resolve.render_json(resolution, dry_run=dry_run, staged=staged), nl=False
        )
    else:
        click.echo(friction_resolve.render_human(resolution, dry_run=dry_run), nl=False)
        if written:
            if not yes and friction_write.interactive():
                click.echo("")
                click.echo(friction_resolve.render_diffs(resolution), nl=False)
                yes = click.confirm("Stage the resolved files (`git add`)?", default=True)
            if yes:
                staged = friction_resolve.stage(target_root, written)
            click.echo("")
            click.echo(friction_resolve.render_staging(written, staged), nl=False)
    if resolution.exit_code:
        raise SystemExit(resolution.exit_code)


@friction.command("check")
@click.option(
    "--base",
    "base_ref",
    metavar="REF",
    default=None,
    help=f"Compare against the merge-base of REF and HEAD. Default: ${friction_check.BASE_ENV}, "
    "else the default branch (`pkit repository base` shows it). A branch name resolves as "
    "the default branch does.",
)
@click.option(
    "--all",
    "whole_repository",
    is_flag=True,
    default=False,
    help=(
        "The whole-repository check: every artefact at HEAD against the current history "
        "(REF is not read). Reports stale and deferred debt, dead anchors and the two "
        "measures; never fails."
    ),
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit the stable JSON document."
)
def friction_check_command(base_ref: str | None, whole_repository: bool, as_json: bool) -> None:
    """The change check (COR-050 point 6): every artefact whose anchor changed in the diff
    carries an answer — updated, unchanged with why, or deferred.

    Reads git only and writes nothing: the working tree (uncommitted changes
    included) against the merge-base of REF — by default $PKIT_CHECK_BASE,
    else the default branch (COR-054). Reports friction, dead anchors of the
    change, bumps with nothing behind them and an outdated base. Exit 1 in
    enforcing mode on friction, a dead anchor, an unresolved kind or a bump;
    an outdated base never fails.

    With --all, the whole-repository check instead: every artefact at HEAD
    against the current history, each anchor judged from the artefact's
    revalidation point (derived from git, renames followed). Reports stale
    and deferred debt with their origins, dead anchors, over-broad anchors,
    unanchored artefacts — those accepted with a reason listed apart, never
    counted — and uncovered surface. Needs the full history, says so in a
    shallow clone, and exits 0 in either mode.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if whole_repository:
        report = friction_repository.run_repository_check(target_root)
        if as_json:
            click.echo(friction_repository.render_json(report), nl=False)
        else:
            click.echo(friction_repository.render_human(report), nl=False)
        return
    settled = default_branch.settled(target_root, base_ref)
    _warn_settled(settled)
    result = friction_check.run_change_check(target_root, base_ref, resolved=settled.base)
    if as_json:
        click.echo(friction_check.render_json(result), nl=False)
    else:
        click.echo(friction_check.render_human(result), nl=False)
    if result.exit_code:
        raise SystemExit(result.exit_code)


@friction.command("debt")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit the stable JSON document."
)
def friction_debt_command(as_json: bool) -> None:
    """The debt (COR-050 point 9): stale and deferred debt, oldest first, each with its
    origin — commit, author, date and change — derived from git.

    Exactly the stale and deferred findings of `pkit friction check --all`, from
    the same run of the whole-repository check: HEAD and its history, never the
    working tree. Artefacts a shallow clone cannot judge are named apart. Then
    its unanchored measure: the artefacts with no anchors and no reason,
    counted, and apart from them those accepted with the reason their
    `unanchored-because` gives. Writes nothing; exits 0.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    listing = friction_report.run_debt(target_root)
    if as_json:
        click.echo(friction_report.render_debt_json(listing), nl=False)
    else:
        click.echo(friction_report.render_debt_human(listing), nl=False)


@friction.command("explain")
@click.argument("artefact", metavar="ARTEFACT")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit the stable JSON document."
)
def friction_explain_command(artefact: str, as_json: bool) -> None:
    """Explain ARTEFACT's friction (COR-050 point 13): its anchors, its revalidation and
    deferral points, what changed since each, and what clears each finding.

    Every changed anchor is shown with the commits behind it, and each finding
    with the writer command that answers it (`revalidate … --outcome …`,
    `defer … --anchor … --reason …`) or the edit it needs. The findings are
    those `pkit friction check --all` reports for ARTEFACT; an unanchored one
    shows the reason its `unanchored-because` gives, if any. With --json, each
    commit also carries its paths (what the check read as the change), each
    path anchor its files at the revalidation point and at HEAD and those
    `friction.exclude` leaves out, and the document the artefact's body.
    ARTEFACT is a location (`path`, or `path#id` for a collection entry) or an
    id, looked up at HEAD. Writes nothing.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    explanation = friction_report.run_explain(target_root, artefact)
    if as_json:
        click.echo(friction_report.render_explain_json(explanation), nl=False)
    else:
        click.echo(friction_report.render_explain_human(explanation), nl=False)


@friction.command("artefacts")
@click.option(
    "--at",
    "at",
    metavar="REV",
    default=None,
    help="Read the state of commit REV — its configuration, its places and its files — "
    "from git objects instead of the working tree. Nothing is checked out.",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit the stable JSON document."
)
def friction_artefacts_command(at: str | None, as_json: bool) -> None:
    """The declared places, the files they hold and the artefacts in them, as
    discovery finds them (COR-050 point 1).

    One run of the discovery `pkit validate` reads, over the working tree —
    or, with --at, over one commit: each place — the project's and each
    capability's, with its location and root — the files it matches and the
    skips validation applies (a synced copy, a place outside the repository, a
    malformed declaration), every file read with its front matter's own
    fields, every artefact with its anchors or the reason it has none, and
    each folder of held documents
    a component declares, with the files it holds. Read-only. It is how a
    capability's own script reads where artefacts are, now or at another
    state, without importing the backbone or walking the places itself. Exit 0
    when answered; 1 when the configuration cannot be read or REV names no
    commit; 2 on a usage error.
    """
    from project_kit import friction_discovery, validators

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    tree = None
    if at is not None:
        commit = None if not at or at.startswith("-") else friction_check.commit_of(target_root, at)
        if commit is None:
            raise click.ClickException(f"--at {at!r} names no commit of this repository.")
        tree = friction_check.CommitTree(target_root, commit)
    problem = friction_discovery.unreadable_configuration(target_root, tree)
    if problem is not None:
        raise click.ClickException(f"{problem}; `pkit validate` reports it.")
    document = validators.as_one_run(
        lambda: friction_discovery.artefacts_document(target_root, tree)
    )
    if as_json:
        click.echo(friction_discovery.render_artefacts_json(document), nl=False)
    else:
        click.echo(friction_discovery.render_artefacts_human(document), nl=False)


@main.group(invoke_without_command=True)
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show this pkit's version, or bump the backbone version of the project at the working
    directory."""
    if ctx.invoked_subcommand is None:
        click.echo(f"pkit {__version__}")


@version.command("bump")
@click.argument("segment", type=click.Choice(["patch", "minor", "major", "pre"]))
@click.option(
    "--pre",
    "pre",
    type=click.Choice(["a", "b", "rc"]),
    default=None,
    help="Append a PEP 440 pre-release suffix (a=alpha, b=beta, rc=release-candidate). "
    "Pre-release bumps do not broaden requires_backbone.",
)
def version_bump(segment: str, pre: str | None) -> None:
    """Bump .pkit/VERSION (segment: patch | minor | major | pre).

    With `--pre <kind>`, appends a PEP 440 pre-release suffix
    (`X.Y.Z<kind>1`). Without it, `pre` as the segment increments the
    existing pre-release counter (`1.2.0rc1` -> `1.2.0rc2`). See PRJ-002.
    """
    source_kit = _target_kit()
    if segment == "pre":
        if pre is not None:
            raise click.ClickException(
                "`bump pre` and `--pre <kind>` are mutually exclusive. "
                "Use `bump pre` to increment an existing pre-release counter, "
                "or `bump <segment> --pre <kind>` to start a new pre-release line."
            )
        bump_pre(source_kit)
        return
    bump_version(source_kit, _cast_segment(segment), pre=_cast_pre(pre))


@version.command("promote")
def version_promote() -> None:
    """Drop the pre-release suffix from VERSION (e.g., `1.2.0rc3` -> `1.2.0`).

    Refuses if VERSION has no pre-release suffix. See PRJ-002.
    """
    source_kit = _target_kit()
    promote_version(source_kit)


@version.command("tag")
@click.option(
    "--push",
    is_flag=True,
    default=False,
    help="After tagging, push the new tag to the `origin` remote.",
)
def version_tag(push: bool) -> None:
    """Tag HEAD as `v<version>` from .pkit/VERSION (per PRJ-002 + PRJ-004)."""
    source_kit = _target_kit()
    tag_version(source_kit, push=push)


@version.command("untag")
@click.option(
    "--push",
    is_flag=True,
    default=False,
    help="Also delete the tag on the `origin` remote.",
)
def version_untag(push: bool) -> None:
    """Remove the `v<version>` tag matching .pkit/VERSION (local; --push for remote)."""
    source_kit = _target_kit()
    untag_version(source_kit, push=push)


@version.command("unbump")
def version_unbump() -> None:
    """Revert the most recent `bump`: narrow requires_backbone + rewrite VERSION.

    Order: run `pkit version untag` first; unbump refuses while the tag
    for the current VERSION still exists locally. Refuses when the prior
    version cannot be determined unambiguously (e.g., pre-release, pre-1.0
    boundary) — set VERSION by hand in that case.
    """
    source_kit = _target_kit()
    unbump_version(source_kit)


def _cast_segment(value: str) -> Segment:
    """Click's `Choice` already validates; this widens str → Segment for the type checker."""
    if value == "patch":
        return "patch"
    if value == "minor":
        return "minor"
    return "major"


def _cast_pre(value: str | None) -> PreKind | None:
    """Click's `Choice` already validates; widen str → PreKind for the type checker."""
    if value is None:
        return None
    if value == "a":
        return "a"
    if value == "b":
        return "b"
    return "rc"


@main.group()
def release() -> None:
    """Declared, release-driven version writes (PRJ-002).

    Feature branches *declare* version intent with changeset files under
    `.changes/unreleased/`; this group is the sole writer of version state,
    designed to run on `main` via a release PR. See `.pkit/release/README.md`.
    """


@release.command("plan")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit the computed release as JSON (for the release-PR automation).",
)
def release_plan(as_json: bool) -> None:
    """Preview the release computed from pending changesets (read-only)."""
    import json

    source_kit = _target_kit()
    plan = compute_release(source_kit)
    if as_json:
        click.echo(json.dumps(release_summary(source_kit, plan), indent=2))
        return
    _print_release_plan(plan)
    _warn_migration_mismatches(source_kit, plan)


@release.command("apply")
@click.option(
    "--tag",
    is_flag=True,
    default=False,
    help="Also cut the tag now. Off by default — tag is a separate step "
    "(`pkit version tag --push`) after the release commit lands on main.",
)
@click.option("--push", is_flag=True, default=False, help="With --tag, push the tag to origin.")
@click.option(
    "--no-broaden",
    is_flag=True,
    default=False,
    help="Skip widening released components' requires_backbone to cover the "
    "current backbone. Default is to broaden (releasing under backbone X "
    "asserts compatibility with X); pass this to keep an upper bound as "
    "authored. A floor a changeset declares is still raised.",
)
@click.option("--yes", is_flag=True, default=False, help="Skip the confirmation prompt (CI).")
def release_apply(tag: bool, push: bool, no_broaden: bool, yes: bool) -> None:
    """Consume changesets and write versions + changelog (the release write).

    The sole main-only writer of version state (PRJ-002 D3). Run from a
    release PR against `main` — not on every merge. Tagging is a separate,
    anchored step by default; see `pkit version tag`.

    On a component release, widens that component's `requires_backbone` to
    cover the repo's current backbone (the version being released under) unless
    `--no-broaden` is given; a backbone release widens every component as
    before. Both are widen-only. A changeset declaring `requires_backbone`
    raises its component's floor — to the backbone the release ships for
    `release`, or to the already-shipped `X.Y.Z` it names — raise-only, not
    skipped by `--no-broaden`, and stated in the component's changelog entry; a
    raise that would leave a range admitting no backbone refuses the release
    before anything is written, and one whose range would exclude the backbone
    the release ships (an upper bound `--no-broaden` keeps) is warned of before
    the confirmation. See `.pkit/release/README.md`.
    """
    source_kit = _target_kit()
    plan = compute_release(source_kit)
    _print_release_plan(plan)
    _warn_migration_mismatches(source_kit, plan)
    broaden = not no_broaden
    # Before the confirmation: an empty raised range refuses here, and a range that
    # excludes the backbone the release ships is shown with the plan it belongs to.
    for warning in check_raised_ranges(plan, broaden=broaden):
        click.echo(f"warning: {warning}", err=True)
    if plan.is_empty:
        apply_release(source_kit, plan, tag=tag, push=push, broaden=broaden)
        return
    if not yes:
        click.confirm("Write these versions and consume the changesets?", abort=True)
    apply_release(source_kit, plan, tag=tag, push=push, broaden=broaden)


@release.command("check")
@click.option(
    "--base",
    metavar="REF",
    default=None,
    help="Diff base for surface detection (the PR base ref). Default: $PKIT_CHECK_BASE, else "
    "the default branch (`pkit repository base` shows it).",
)
@click.option(
    "--skip",
    is_flag=True,
    default=None,
    help="Escape hatch: pass unconditionally. Also honoured via the "
    "PKIT_CHANGESET_SKIP env var (wired from the `skip-changeset` PR label).",
)
def release_check(base: str | None, skip: bool | None) -> None:
    """CI guard: fail if the diff touches a component's surface and adds or edits
    no changeset naming it, or the PR declares a `requires_backbone` floor for a
    component it neither touches nor moves.

    The diff is taken from where HEAD left the base — REF, else
    $PKIT_CHECK_BASE, else the default branch (COR-054); a base that resolves
    nowhere refuses the run with its fix. Escape hatch for the surface check: a
    `none` changeset for the component, or the `skip-changeset` label
    (PKIT_CHANGESET_SKIP env). Surface is a human judgment (PRJ-002 D2) — this
    path heuristic can mis-fire; the override exists. No escape hatch waives
    the floor tie. A pending changeset the diff leaves alone — another pull
    request's — does not count for this one, whatever component it names.
    """
    source_kit = _target_kit()
    fork = _settled_base(source_kit.parent, base).fork
    assert fork is not None  # `_settled_base` refuses a base without one
    skip_active = bool(skip) or _env_flag("PKIT_CHANGESET_SKIP")
    result = check_changesets(source_kit, fork, skip=skip_active)

    if result.skipped:
        click.echo(
            "changeset guard: surface check skipped (escape hatch active); "
            "declared floors still checked."
        )
    elif result.release_exempt:
        click.echo(
            "changeset guard: release PR — diff is only what `pkit release apply` "
            "writes (versions, CHANGELOG, consumed changesets); surface check exempt."
        )
    elif result.touched:
        click.echo(f"changeset guard: touched {', '.join(result.touched)}")
    if result.ok:
        if result.skipped or result.release_exempt:
            click.echo(
                "changeset guard: every floor this diff declares rides on its component — ok."
            )
        else:
            click.echo(
                "changeset guard: every touched component has a changeset in this diff — ok."
                if result.touched
                else "changeset guard: no surface-touched components — ok."
            )
        return
    problems: list[str] = []
    if not result.surface_ok:
        problems.append(
            "surface change without a changeset for: "
            + ", ".join(result.missing)
            + ".\n  Only a changeset this diff adds or edits counts, once committed: a pending "
            "changeset the diff leaves alone declares another pull request's change, not "
            "this one's, even when it names the same component."
            "\n  Add one with `changie new` (per .pkit/release/README.md), hand-write a "
            "changeset under .changes/unreleased/, drop a `none` changeset if it moves no "
            "user-facing surface, or apply the `skip-changeset` label."
            "\n  Decision-only PR (COR/PRJ/ADR/DEC)? Declare `none` for a design-ahead "
            "decision (the feature ships in a later PR) or a real changeset for a "
            "self-executing rule change — see PRJ-002."
        )
    if result.stray_floors:
        problems.append(
            "a requires_backbone floor declared for a component this diff neither touches "
            "nor moves:\n"
            + "\n".join(
                f"  {cs.path.name}: {cs.component!r} (kind: {cs.segment}, "
                f"requires_backbone: {cs.requires_backbone})"
                for cs in result.stray_floors
            )
            + "\n  A floor changes what the component requires, so it rides on a change to "
            "the component or on a release of it: declare it in the changeset of the pull "
            "request that changes the component, or — for a need found after the component "
            "shipped — on a changeset that moves its version (patch or above). The "
            "`skip-changeset` label does not waive this — see PRJ-002 D4."
        )
    raise click.ClickException("\n".join(problems))


@release.command("lint")
@click.option(
    "--skip",
    is_flag=True,
    default=None,
    help="Escape hatch: pass the format checks unconditionally (a requires_backbone "
    "floor field is still checked). Also honoured via the PKIT_CHANGELOG_LINT_SKIP "
    "env var.",
)
def release_lint(skip: bool | None) -> None:
    """Format lint: the OBJECTIVE changeset + CHANGELOG.md format subset.

    Checks the mechanically-verifiable subset only — a changeset's category is
    a Keep-a-Changelog group, its body is a non-empty sentence (not a bare
    reference, capitalized, period-ended), a `requires_backbone` floor field
    says `release` — in a release that ships a release version of the backbone
    — or names a backbone release the tree records (a `CHANGELOG.md` release
    heading, or the backbone it carries), at or below the backbone it carries,
    on a version-moving changeset of a capability or adapter whose range is
    `">=X.Y.Z,<A.B.C"` or `">=X.Y.Z"`, and `CHANGELOG.md` headings are
    well-formed. It does
    *not* judge plain language / jargon — that is the guide plus review. A
    reminder, not a proof; see `.pkit/release/README.md`.

    Reads committed files only (no PR context), so it runs in the shared check
    aggregator. Escape hatch: `--skip` or the PKIT_CHANGELOG_LINT_SKIP env var —
    except for the floor field, which the release itself refuses: an invalid one
    fails the lint either way, since it would block every later release on main.
    """
    source_kit = _target_kit()
    skip_active = bool(skip) or _env_flag("PKIT_CHANGELOG_LINT_SKIP")
    result = lint_release_format(source_kit, skip=skip_active)

    if result.ok:
        click.echo(
            "changelog lint: skipped (escape hatch active)."
            if result.skipped
            else "changelog lint: changesets + CHANGELOG.md are well-formed — ok."
        )
        return
    shown = result.floor_violations + ([] if result.skipped else result.violations)
    detail = "\n".join(f"  {v.source}: {v.message}" for v in shown)
    advice = (
        "\n  The escape hatch is active, but it does not cover a requires_backbone "
        "floor field: the release refuses one it cannot raise, which blocks every "
        "later release on main. Fix the field."
        if result.skipped
        else "\n  Fix the entries above, or apply the escape hatch (--skip / "
        "PKIT_CHANGELOG_LINT_SKIP) if an objective rule mis-fired — it does not "
        "cover a requires_backbone floor field. See the format guide in "
        ".pkit/release/README.md."
    )
    raise click.ClickException(
        "changeset / changelog format problems (the objective subset):\n" + detail + advice
    )


@release.command("merge")
@click.argument("pr", type=int)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Report what would be merged without merging.",
)
@click.option(
    "--no-wait",
    is_flag=True,
    default=False,
    help="Where the base merges through a queue: return once the PR is queued (exit 4). "
    "Run the same command again once it has merged to delete its head branch.",
)
@click.option(
    "--wait-minutes",
    type=click.FloatRange(min=0),
    default=None,
    metavar="MINUTES",
    help="Where the base merges through a queue: how long to wait for the queue to merge "
    f"the PR. Default: {pull_request_landing.wait_limit(None)}.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Where the base merges through a queue: enqueue a head the queue already dropped. "
    "Without it, such a head is refused until new commits are pushed.",
)
def release_merge(
    pr: int, dry_run: bool, no_wait: bool, wait_minutes: float | None, force: bool
) -> None:
    """Merge a release PR — the sanctioned path for a `chore(release):` PR.

    A release PR closes no issue, so the issue-PR merge gate (`pkit
    project-management merge-pr`) legitimately refuses it. This verb is the
    release flow's own merge: it is guarded to `release/*` heads (a non-release
    PR is refused, pointing at the issue-PR gate), merges only when the PR is
    open, mergeable, and its required checks are green, and lands it as one
    squash commit whose subject is the PR title — through the base's merge queue
    where it has one — deleting the head branch once GitHub reports the PR
    merged (best-effort; never a fork's head). Exit 4 when the queue still holds
    the PR, or a direct merge could not be confirmed: running it again once the
    PR has merged deletes the head branch. Exit 3 when the queue dropped the PR
    or its head moved; nothing is deleted then. A head the queue already
    dropped is not enqueued again without `--force`. It does **not** tag —
    `release-tag.yml` cuts the backbone tag on the resulting push to `main`
    (PRJ-004). Human-gated: a human decides to run it; nothing auto-merges.
    """
    if no_wait and wait_minutes is not None:
        raise click.UsageError("--no-wait and --wait-minutes are mutually exclusive.")
    if wait_minutes is not None and not math.isfinite(wait_minutes):
        raise click.BadParameter("not a number of minutes", param_hint="--wait-minutes")
    wait_seconds = 0.0 if no_wait else (wait_minutes * 60 if wait_minutes is not None else None)
    source_kit = _target_kit()
    report = merge_release_pr(
        source_kit.parent, pr, dry_run=dry_run, wait_seconds=wait_seconds, force=force
    )
    click.echo(report.text)
    if report.exit_code:
        raise SystemExit(report.exit_code)


@release.command("publish-notes")
@click.argument("version")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the notes that would be published without calling `gh`.",
)
def release_publish_notes(version: str, dry_run: bool) -> None:
    """Publish a notes-only GitHub Release for `v<version>` from CHANGELOG.md.

    Extracts that version's `CHANGELOG.md` section and creates the GitHub
    Release for tag `v<version>` with the section as its body — or updates the
    notes if the Release already exists (idempotent). The Release carries **no
    artifact**: it is a notes overlay on the git-tag install path (PRJ-004),
    never a file / tarball / wheel channel. Repo is derived from the ambient
    `gh` context (no hardcoded owner/repo). A missing tag is a clear error;
    `--dry-run` prints the notes without calling `gh`.
    """
    source_kit = _target_kit()
    click.echo(publish_release_notes(source_kit.parent, version, dry_run=dry_run))


@release.command("check-shareable")
@click.argument("component")
def release_check_shareable(component: str) -> None:
    """Check a capability is ready to be consumed externally-sourced (COR-041).

    A pre-sharing lint: before a capability is pulled whole at a pin by another
    repo, it must declare a `version`, a well-formed `package.yaml` manifest,
    and a bounded `requires_backbone` range the consumer's compatibility gate
    can evaluate. This reports pass or the specific gaps, and warns on cheaply
    detectable local-only assumptions (absolute paths / `file://` URLs). It
    checks any component by name — project-neutral, no project-kit specifics.
    """
    source_kit = _target_kit()
    report = check_shareable(source_kit, component)

    for warning in report.warnings:
        click.echo(f"  warning: {warning}")

    if report.ok:
        click.echo(f"shareability check: {component} is ready to be shared — ok.")
        return

    detail = "\n".join(f"  - {gap}" for gap in report.gaps)
    raise click.ClickException(
        f"{component} is not ready to be consumed externally-sourced:\n"
        + detail
        + "\n  Fix the gaps above, then re-run. See COR-041 / .pkit/release/README.md."
    )


def _env_flag(name: str) -> bool:
    """True when an env var is set to a truthy value (`1`/`true`/`yes`)."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def _warn_migration_mismatches(source_kit: Path, plan: ReleasePlan) -> None:
    """Echo any migration-dir prediction warnings (non-fatal; see #465)."""
    for warning in migration_dir_mismatches(source_kit, plan):
        click.echo(f"  warning: {warning}")


def _print_release_plan(plan: ReleasePlan) -> None:
    if plan.is_empty:
        click.echo("Release plan: no version moves.")
    else:
        click.echo("Release plan:")
        for rel in plan.releases:
            click.echo(
                f"  {rel.component.name}: {rel.old_version} -> {rel.new_version} ({rel.segment})"
            )
            if rel.floor_raise is not None:
                for line in rel.floor_raise.lines:
                    click.echo(f"    {line}")
            for note in rel.notes:
                click.echo(f"    - {note}")
    click.echo(f"  changesets to consume: {len(plan.consumed)}")


# Human phrase for each install-target classification, shown in the announcement.
# No phrase calls a non-repository a "git repository" (#787): DUBIOUS_OWNERSHIP is
# a real repo git refused, and PKIT_INSTALL is an adopted project — neither is
# mislabelled, and neither proceeds to an install.
_INIT_REASON_PHRASE: dict[InitTargetReason, str] = {
    InitTargetReason.GIT_ROOT: "git repository root — your current directory",
    InitTargetReason.GIT_SUBFOLDER: "git repository root — you are in a subfolder",
    InitTargetReason.DUBIOUS_OWNERSHIP: "a git repository git could not verify (dubious ownership)",
    InitTargetReason.BROKEN_GIT: "a git repository git cannot open (broken .git)",
    InitTargetReason.PKIT_INSTALL: "an existing project-kit install above your current directory",
    InitTargetReason.NONE: "your current directory — no git repository found above it",
}


def _stdin_is_tty() -> bool:
    """Whether stdin is an interactive terminal.

    Isolated so `pkit init`'s confirm gate is unit-testable: a piped
    `yes | pkit init` has a non-tty stdin and must be refused, not
    auto-confirmed (issue #780). An absent stdin (`sys.stdin` is None, as when
    the process is started with fd 0 closed) or a closed stream is not a
    terminal either — treated as non-interactive, not a crash (#913).
    """
    stdin = sys.stdin
    if stdin is None:
        return False
    try:
        return stdin.isatty()
    except (ValueError, OSError):  # ValueError: I/O operation on a closed file
        return False


def _confirm_install(target: Path, non_interactive_refusal: str) -> None:
    """Ask before installing into `target`; refuse when no one can answer.

    On a non-interactive stdin the prompt is never shown — the caller's refusal
    message is raised instead, so a piped `yes |` cannot auto-confirm (#780). A
    declined prompt aborts non-zero (`click.Abort`), so a chained next step does
    not run as if the install had happened (#913).
    """
    if not _stdin_is_tty():
        raise click.ClickException(non_interactive_refusal)
    click.confirm(f"Install project-kit into {target}?", default=False, abort=True)


def _announce_init_target(
    target: Path,
    reason: InitTargetReason,
    installs: list[Path],
    *,
    here: bool,
) -> None:
    """Print the resolved install target, why it was chosen, and any existing
    project-kit installs on the path between CWD and the target (issue #780).

    The announcement is `init`'s primary safety mechanism: it makes the target
    visible in *every* case — including the happy path — so a silent install at
    a resolved parent can no longer surprise the operator.
    """
    if here:
        click.echo(f"pkit init -> {target}  (current directory, --here)")
    else:
        click.echo(f"pkit init -> {target}  ({_INIT_REASON_PHRASE[reason]})")
    for install_dir in installs:
        at_target = install_dir.resolve() == target.resolve()
        where = "the target" if at_target else "between here and the target"
        click.echo(f"  found existing install at {install_dir}/.pkit  ({where})")


@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help=(
        "Show what would be installed without writing any files or prompting (per "
        "COR-004). Every refusal still applies."
    ),
)
@click.option(
    "--here",
    is_flag=True,
    default=False,
    help=(
        "Install into the current directory instead of a resolved parent. Refused "
        "when the current directory is a subfolder of a git worktree — a .pkit/ "
        "there is unreachable, as every command resolves to the git root — or is "
        "inside an existing project-kit project."
    ),
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help=(
        "Accept the confirm for a target that IS your current directory (a fresh "
        "non-git folder). It will NOT install at a resolved parent — use --root for "
        "that, so a non-interactive run never installs somewhere you are not standing."
    ),
)
@click.option(
    "--root",
    "root",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
    default=None,
    help=(
        "Install at this explicit path, non-interactively. The sanctioned way to "
        "install at a resolved parent (e.g. a git repository root) in CI, where a "
        "bare --yes is refused as a footgun. Refused when the path is a subfolder "
        "of a git worktree or inside an existing project-kit project. Mutually "
        "exclusive with --here."
    ),
)
def init(dry_run: bool, here: bool, yes: bool, root: Path | None) -> None:
    """First install: propagation + seed + merge per COR-001 / COR-002 / COR-004.

    Announces the resolved install target and why it was chosen, then confirms
    before installing anywhere other than the current directory (issue #780).
    Validates the resolved target so a broken/vestigial `.git` no longer offers a
    workspace folder as a root, and guides rather than silently installing into a
    repository git cannot verify (issue #787).
    """
    cwd = Path.cwd()

    if here and root is not None:
        raise click.ClickException(
            "Pass either --here or --root <path>, not both — they name different install targets."
        )

    # An explicit --root is the operator naming the target unambiguously — the
    # sanctioned non-interactive install-at-a-parent path (#787). It bypasses the
    # resolution-driven confirm and the cwd-to-target split-brain scan (which exist
    # to stop a *silent* install at a resolved parent), but not the checks on the
    # target itself: the shadowed-target refusal, the existing-.pkit refusal (an
    # already-adopted redirect or a stray .pkit, #913), and install_kit's own.
    if root is not None:
        target = root.resolve()
        # Resolve from the target as a steady-state command run there would. If
        # that lands anywhere but the target, a .pkit/ there is shadowed: below a
        # git worktree root (dubious or broken included) it is unreachable, and
        # below an install-marked ancestor it is a second, nested install. ADR-001
        # refuses both; explicit consent does not make the install usable (#914).
        enclosing_root, root_reason = resolve_init_target(target)
        if enclosing_root != target:
            if root_reason == InitTargetReason.PKIT_INSTALL:
                raise click.ClickException(
                    f"--root refused: {target} is inside the project-kit project at "
                    f"{enclosing_root}.\n"
                    f"       A second, nested install is not supported. Run "
                    f"{sync_remedy(enclosing_root, cwd)} to refresh that project."
                )
            if router.looks_like_pkit_install(enclosing_root / ".pkit"):
                raise click.ClickException(
                    f"--root refused: {target} is a subfolder of the git repository "
                    f"rooted at {enclosing_root},\n"
                    f"       which is already a project-kit project. A .pkit/ here would "
                    f"be unreachable — every\n"
                    f"       pkit command resolves to the git root. Run "
                    f"{sync_remedy(enclosing_root, cwd)} to refresh that project."
                )
            raise click.ClickException(
                f"--root refused: {target} is a subfolder of the git repository rooted "
                f"at {enclosing_root}.\n"
                f"       A .pkit/ created there would be unreachable — every pkit command "
                f"resolves to the\n"
                f"       git root, not this subfolder. Run `pkit init --root "
                f"{shlex.quote(str(enclosing_root))}` to install\n"
                f"       there, or make this folder its own git repository first."
            )
        # A .pkit entry at the target itself: a real install redirects to sync, a
        # stray one is named and must be moved aside (#913). Checked after the
        # shadow refusal, whose remedy is the right one for a shadowed target (a
        # shadowed install's `pkit sync` would resolve to the enclosing root). The
        # sync redirect names the target's location when cwd is outside it.
        refuse_if_pkit_present(target, cwd)
        # The target is itself a repository git will not vouch for. --root is the
        # escape the guided flow's refusal names, so install — but say what git
        # said, so a CI run does not install into an unverified tree unannounced.
        if root_reason == InitTargetReason.DUBIOUS_OWNERSHIP:
            click.echo(
                f"⚠ WARNING: {target} is a git repository git refused to verify "
                f"(dubious ownership / safe.directory).\n"
                f"       Proceeding because --root is explicit. If you trust its owner, "
                f"let git use it with:\n"
                f"       git config --global --add safe.directory {shlex.quote(str(target))}"
            )
        elif root_reason == InitTargetReason.BROKEN_GIT:
            click.echo(
                f"⚠ WARNING: {target} has a .git that git cannot open (a broken or "
                f"partial repository).\n"
                "       Proceeding because --root is explicit. Run `git -C "
                f"{shlex.quote(str(target))} "
                f"status` to see why."
            )
        click.echo(f"pkit init -> {target}  (explicit target, --root)")
        install_kit(target, dry_run=dry_run)
        return

    target, reason = resolve_init_target(cwd)

    # A structurally-real repository git refused to verify (dubious ownership /
    # safe.directory — routine in Docker / CI / sudo trees). Never silently drop a
    # shadowed .pkit/ inside it; guide the operator to the fix (#787). Fires ahead
    # of --here: installing at cwd here is exactly the shadowing footgun.
    if reason == InitTargetReason.DUBIOUS_OWNERSHIP:
        _announce_init_target(target, reason, [], here=here)
        # Already adopted (a Docker / CI checkout owned by another user): `--root`
        # would only refuse as already installed, so the remedy is the ownership
        # fix, then `pkit sync`. A stray non-install .pkit keeps the `--root`
        # remedy — that run names the stray entry and how to clear it (#913).
        if router.looks_like_pkit_install(target / ".pkit"):
            raise click.ClickException(
                f"{target} is already a project-kit project, but git refused to verify "
                f"its repository\n"
                f"       (dubious ownership / safe.directory). If you trust its owner, let "
                f"git use it with\n"
                f"       `git config --global --add safe.directory "
                f"{shlex.quote(str(target))}`, then run {sync_remedy(target, cwd)}\n"
                f"       to refresh the project."
            )
        raise click.ClickException(
            f"{target} looks like a git repository, but git refused to verify it "
            f"(dubious ownership / safe.directory).\n"
            f"       project-kit will not install a shadowed .pkit/ inside a repository "
            f"it cannot confirm.\n"
            f"       Fix the ownership (e.g. `git config --global --add safe.directory "
            f"{shlex.quote(str(target))}`) and\n"
            f"       re-run, or install there anyway with `pkit init --root "
            f"{shlex.quote(str(target))}`."
        )

    # A structurally-real repository git cannot open for a reason other than
    # ownership (a corrupt HEAD, a dangling worktree pointer). The safe.directory
    # remedy would fix nothing, so name the actual problem (#914). Refused like the
    # dubious case: installing inside a repository nobody can confirm is the same
    # shadowing footgun, and --here does not override it.
    if reason == InitTargetReason.BROKEN_GIT:
        _announce_init_target(target, reason, [], here=here)
        # Already adopted: as for dubious ownership, `--root` would refuse as
        # already installed, so the remedy is repairing the .git, then `pkit sync`
        # (#913). Removing the .git is not offered — it holds the project's history.
        if router.looks_like_pkit_install(target / ".pkit"):
            raise click.ClickException(
                f"{target} is already a project-kit project, but git cannot open its "
                f".git — a broken or\n"
                f"       partial repository. Run `git -C {shlex.quote(str(target))} status` "
                f"to see why and repair\n"
                f"       that .git, then run {sync_remedy(target, cwd)} to refresh the "
                f"project."
            )
        raise click.ClickException(
            f"{target} has a .git that git cannot open — a broken or partial "
            f"repository.\n"
            f"       project-kit will not install inside a repository it cannot "
            f"confirm.\n"
            f"       Run `git -C {shlex.quote(str(target))} status` to see why, then repair or "
            "remove "
            f"that .git and\n"
            f"       re-run, or install there anyway with `pkit init --root "
            f"{shlex.quote(str(target))}`."
        )

    # --here is refused when CWD is a strict subfolder of a git worktree — the
    # topology where a .pkit/ at CWD is unreachable, because every command resolves
    # to the git root, not the subfolder — and when CWD is inside an existing
    # install (a nested second install, ADR-001). At a git root or in a fresh
    # non-git folder it is honored (an explicit install at cwd).
    if here:
        if reason == InitTargetReason.GIT_SUBFOLDER and router.looks_like_pkit_install(
            target / ".pkit"
        ):
            raise click.ClickException(
                f"--here refused: the current directory is a subfolder of the git "
                f"worktree rooted at {target},\n"
                f"       which is already a project-kit project. A .pkit/ here would be "
                f"unreachable — every\n"
                f"       pkit command resolves to the git root. Run "
                f"{sync_remedy(target, cwd)} to refresh that project."
            )
        if reason == InitTargetReason.GIT_SUBFOLDER:
            raise click.ClickException(
                f"--here refused: the current directory is a subfolder of the git "
                f"worktree rooted at {target}.\n"
                f"       A .pkit/ created here would be unreachable — every pkit command "
                f"resolves to the\n"
                f"       git root, not this subfolder. Run `pkit init` from {target}, or "
                f"split this\n"
                f"       folder into its own git repository first."
            )
        # The same ancestor-install check the default path runs: an install between
        # cwd and the resolved target (a PKIT_INSTALL ancestor) means a .pkit/ here
        # would be a second, nested install — refused per ADR-001 (#914).
        enclosing = [d for d in scan_pkit_installs(cwd, target) if d.resolve() != cwd.resolve()]
        if enclosing:
            raise click.ClickException(
                f"--here refused: the current directory is inside the project-kit "
                f"project at {enclosing[0]}.\n"
                f"       A second, nested install is not supported. Run "
                f"{sync_remedy(enclosing[0], cwd)} to refresh that project."
            )
        target = cwd

    installs = scan_pkit_installs(cwd, target)
    off_target = [d for d in installs if d.resolve() != target.resolve()]

    _announce_init_target(target, reason, installs, here=here)

    # Already a project-kit project → refuse re-run. `init` is one-shot, not
    # idempotent (COR-004): re-running would resurface seeded content or silently
    # skip already-seeded paths. Recovery flows through `pkit sync`. This is also
    # the PKIT_INSTALL-ancestor redirect (#787): the ancestor is the target and it
    # carries a real install. A stray `.pkit` that is not an install is refused
    # here too, with what is wrong and how to clear it (#913). Fires before the
    # confirm so the operator is never prompted-then-refused for an install that
    # could not proceed anyway (#780).
    refuse_if_pkit_present(target, cwd)

    # An install sits between CWD and the target, but the target has none:
    # installing there would leave two installs straddling CWD (split-brain).
    # This is the observed #780 incident — refuse and point at the explicit
    # --root override (a bare --yes must never install off-cwd, #787).
    if off_target:
        found = off_target[0]
        raise click.ClickException(
            f"refusing to create a second project-kit install.\n"
            f"       Found an existing install at {found}/.pkit,\n"
            f"       but the resolved target {target} has none — installing there would\n"
            f"       leave two installs straddling your current directory (a split-brain).\n"
            f"       That install is shadowed: every pkit command here resolves to the "
            f"git root, so\n"
            f"       neither `pkit sync` nor `pkit init` reaches it. Run "
            f"`pkit init --root {shlex.quote(str(target))}`\n"
            f"       to install at {target} anyway."
        )

    # A target above cwd (a git repository root you are inside): install into it
    # interactively (explicit confirm on a tty), but never via a bare --yes on a
    # non-interactive stdin — that is the CI footgun #787 closes. --dry-run only
    # previews, so it skips the prompt.
    if target.resolve() != cwd.resolve():
        if yes:
            raise click.ClickException(
                f"--yes will not install at {target}, which is not your current "
                f"directory.\n"
                f"       This guards against a non-interactive run installing somewhere "
                f"you are not standing.\n"
                f"       Re-run with `pkit init --root {shlex.quote(str(target))}` to install "
                "there "
                f"explicitly, or cd into it first."
            )
        # Only a git subfolder reaches here (every other off-cwd reason is refused
        # above), and `--here` is refused in a subfolder — so the remedies name
        # the root, never `--here` (#913).
        if not dry_run:
            _confirm_install(
                target,
                f"the install target {target} is not your current directory, and "
                f"stdin is not a terminal.\n"
                f"       Re-run with `pkit init --root {shlex.quote(str(target))}` to "
                f"install there, or run `pkit init`\n"
                f"       from {target}.",
            )
        install_kit(target, dry_run=dry_run)
        return

    # Target IS the current directory (GIT_ROOT, --here, or a fresh non-git
    # folder). NONE still confirms — a fresh non-git folder offers to init here;
    # --yes / --here accept it, --dry-run previews. GIT_ROOT / --here install
    # straight (installing where you stand is never a footgun).
    if reason == InitTargetReason.NONE and not yes and not here and not dry_run:
        _confirm_install(
            target,
            f"no git repository found and stdin is not a terminal.\n"
            f"       Re-run with --yes to install project-kit into {target}.",
        )

    install_kit(target, dry_run=dry_run)


@main.command()
def status() -> None:
    """Show how project-kit is wired in this project (read-only)."""
    report_status()


@main.group("report", invoke_without_command=True)
@click.option("--tree", is_flag=True, help="Show each report with its tracked-by fixes nested.")
@click.pass_context
def report(ctx: click.Context, tree: bool) -> None:
    """Report a bug, change-request, or feedback about pkit (per PRJ-008 / ADR-047).

    With no subcommand, lists your reports and their states (flat; `--tree` nests
    each report's tracked-by fixes).

    Agent-assisted composing is the paired flow (per COR-005): the
    `report-author` skill draws out an actionable description and drives these
    verbs — reach for it rather than hand-composing (#665).
    """
    if ctx.invoked_subcommand is None:
        _run_report_list(tree=tree)


def _run_report_list(*, tree: bool = False) -> None:
    from project_kit.report import (
        REPORT_TARGET,
        gh_authenticated,
        list_my_reports,
        list_my_reports_tree,
        local_reported_notes,
    )

    if not gh_authenticated():
        click.echo(
            "Listing your reports needs `gh` auth. Meanwhile, view them at\n"
            f"    https://github.com/{REPORT_TARGET}/issues?q=is%3Aissue+author%3A%40me"
        )
        return

    # The one-tracking-truth cross-tag (#664): a row whose issue a local
    # reported/ note references is tagged [note: <slug>] — derived live,
    # never stored. The same notes also feed membership (#681): the list
    # functions union in locally-reported issues that carry no upstream
    # provenance marker (raw-gh-filed reports like #660).
    target_root = find_target_root()
    notes = local_reported_notes(target_root, REPORT_TARGET) if target_root else {}

    if tree:
        rows = list_my_reports_tree(REPORT_TARGET, target_root)
        if rows is None:
            raise click.ClickException("could not read your reports (gh error).")
        if not rows:
            click.echo("No reports yet — file one with `pkit report bug|feedback|change-request`.")
            return
        click.echo(f"Your reports to {REPORT_TARGET}:\n")
        for r, tracked in rows:
            click.echo(f"  {_report_row(r, _report_title(r, note=notes.get(r.number)))}")
            for n, fix in tracked.items():
                click.echo(f"      └ {_tracked_fix_row(n, fix)}")
        return

    reports = list_my_reports(REPORT_TARGET, target_root)
    if reports is None:
        raise click.ClickException("could not read your reports (gh error).")
    if not reports:
        click.echo("No reports yet — file one with `pkit report bug|feedback|change-request`.")
        return
    click.echo(f"Your reports to {REPORT_TARGET}:\n")
    for r in reports:
        click.echo(f"  {_report_row(r, _report_title(r, note=notes.get(r.number)))}")


def _report_row(r, title: str) -> str:
    """One report-list row (#678): number + kind + state + the rendered
    `title`, plus the report's OWN issue URL when the list query resolved it —
    so a row links straight to its issue, matching the tracked-fix rollup.
    A summary without a URL renders without the parenthetical."""
    row = f"#{r.number:<5} {r.kind:<15} {r.state:<12} {title}"
    return f"{row}  ({r.url})" if r.url else row


def _report_title(r, note: str | None = None) -> str:
    """Render a report's title, tagged with its project marker (`[project]`,
    ADR-050), a `(filed for you)` marker when attributed, and the local
    reported-note cross-tag (`[note: <slug>]`, #664) when a reported/
    scratchpad note references the issue."""
    title = f"{r.title}  [{r.project}]" if r.project else r.title
    if r.attributed:
        title = f"{title}  (filed for you)"
    return f"{title}  [note: {note}]" if note else title


def _tracked_fix_row(n: int, fix) -> str:
    """One Tracked-by rollup row (#664): number + state, plus the fix's title
    and URL when the read resolved them — so the reader learns WHAT is fixing
    them without a browser round-trip. Offline/unresolved degrades to
    number + state."""
    if fix.title or fix.url:
        return f"#{n:<6} {fix.state:<12} {fix.title}  ({fix.url})"
    return f"#{n:<6} {fix.state}"


@report.command("show")
@click.argument("number", type=int)
def report_show(number: int) -> None:
    """Show one report's state, maintainer comments, and its tracked-by fixes."""
    from project_kit.report import REPORT_TARGET, gh_authenticated, show_report

    if not gh_authenticated():
        click.echo(
            f"View it at https://github.com/{REPORT_TARGET}/issues/{number} "
            "(`gh` auth needed for CLI detail)."
        )
        return
    detail = show_report(REPORT_TARGET, number)
    if detail is None:
        raise click.ClickException(f"could not read report #{number} on {REPORT_TARGET}.")
    # An honest fallback for an issue the classifier can't place (no report
    # label, marker, or title prefix) — "report" here used to masquerade as a
    # kind (#663; pre-classifier-update #660 rendered that way).
    kind = detail["kind"] or "unclassified"
    click.echo(f"#{detail['number']}  {kind}  {detail['state']}  {detail['title']}")
    tracked = detail["tracked_by"]
    if tracked:
        click.echo("\n  Tracked by (the issues that will fix it):")
        for n, fix in tracked.items():
            click.echo(f"    {_tracked_fix_row(n, fix)}")
    comments = detail["comments"]
    if comments:
        last = comments[-1]
        first_line = (str(last.get("body") or "").strip().splitlines() or [""])[0]
        click.echo(f"\n  {len(comments)} maintainer comment(s); latest: {first_line}")


def _require_report_target() -> str:
    """Gate the maintainer side to running inside the report-target repo."""
    from project_kit.report import REPORT_TARGET, in_report_target

    if not in_report_target():
        raise click.ClickException(
            "the maintainer side (inbox/link/unlink) runs only inside the report "
            f"target repo ({REPORT_TARGET}). Cd into it and retry."
        )
    return REPORT_TARGET


@report.command("inbox")
@click.option(
    "--kind",
    type=click.Choice(["bug", "feedback", "change-request"]),
    default=None,
    help="Show only reports of this kind.",
)
@click.option(
    "--group-by",
    "group_by",
    type=click.Choice(["project"]),
    default=None,
    help="Group reports by the body marker's project= key (ADR-050; reports "
    "without one group under '(no project)').",
)
@click.option(
    "--resolved",
    is_flag=True,
    default=False,
    help="List open feedbacks/change-requests whose Tracked-by issues are all "
    "closed, and prompt (interactively) to comment + close each. Never closes "
    "without a per-report confirm.",
)
@click.option(
    "--yes",
    "assume_yes",
    is_flag=True,
    default=False,
    help="Non-interactive. With --resolved, lists only — never closes (the "
    "report family's --yes asymmetry).",
)
def report_inbox(kind: str | None, group_by: str | None, resolved: bool, assume_yes: bool) -> None:
    """(Maintainer) Triage queue: all reports on the target repo."""
    target = _require_report_target()
    if resolved:
        if kind or group_by:
            raise click.UsageError(
                "--resolved is its own view (feedbacks/change-requests only); "
                "it does not combine with --kind/--group-by."
            )
        _run_inbox_resolved(target, assume_yes=assume_yes)
        return
    _run_inbox_list(target, kind=kind, group_by=group_by)


def _run_inbox_list(target: str, *, kind: str | None, group_by: str | None) -> None:
    from project_kit.report import ReportSummary, list_inbox

    reports = list_inbox(target, kind=kind)
    if reports is None:
        raise click.ClickException("could not read the inbox (gh error).")
    if not reports:
        what = f"{kind} reports" if kind else "reports"
        click.echo(f"Inbox empty — no {what} filed yet.")
        return
    click.echo(f"Reports on {target}:\n")
    if group_by == "project":
        by_project: dict[str, list[ReportSummary]] = {}
        for r in reports:
            by_project.setdefault(r.project or "(no project)", []).append(r)
        for project in sorted(by_project):
            click.echo(f"  {project}")
            for r in by_project[project]:
                click.echo(f"    {_report_row(r, _inbox_title(r))}")
        return
    for r in reports:
        click.echo(f"  {_report_row(r, _inbox_title(r))}")


def _inbox_title(r) -> str:
    """An inbox row's title with its workstream marker (`[workstream]`,
    ADR-050) when the report carries one."""
    return f"{r.title}  [{r.workstream}]" if r.workstream else r.title


def _run_inbox_resolved(target: str, *, assume_yes: bool) -> None:
    """The `--resolved` close-prompt: list fully-tracked reports, then confirm a
    comment + close **per report, interactively only**. `--yes`/non-interactive
    never closes — listing is the whole autonomous surface (the same
    produce-don't-act asymmetry as the reporter side's --yes, ADR-047)."""
    from project_kit.report import close_report_as_resolved, list_resolved

    rows = list_resolved(target)
    if rows is None:
        raise click.ClickException("could not read the inbox (gh error).")
    if not rows:
        click.echo("Nothing resolved — no open report has all its tracked fixes closed.")
        return
    click.echo(f"Resolved reports on {target} (all tracked fixes closed):\n")
    for r, tracked in rows:
        refs = ", ".join(f"#{n}" for n in tracked)
        click.echo(f"  #{r.number:<5} {r.kind:<15} {r.title}  (tracked: {refs})")
    if assume_yes:
        click.echo(
            "\n--yes: listing only — closing needs an interactive per-report "
            "confirm (never autonomous)."
        )
        return
    click.echo("")
    for r, tracked in rows:
        if not click.confirm(f"Post a closing comment on #{r.number} and close it?", default=False):
            click.echo(f"Skipped #{r.number}.")
            continue
        if close_report_as_resolved(target, r.number, tracked):
            click.echo(f"Closed #{r.number} with a closing comment.")
        else:
            click.echo(f"Could not close #{r.number} (gh error); left open.")


@report.command("link")
@click.argument("feedback_n", type=int)
@click.argument("fix_n", type=int)
def report_link(feedback_n: int, fix_n: int) -> None:
    """(Maintainer) Add fix #FIX_N to feedback #FEEDBACK_N's Tracked-by section."""
    from project_kit.report import link_fix

    target = _require_report_target()
    if not link_fix(target, feedback_n, fix_n):
        raise click.ClickException(f"could not link #{fix_n} into #{feedback_n} (gh error).")
    click.echo(f"Linked #{fix_n} into #{feedback_n}'s Tracked by.")


@report.command("unlink")
@click.argument("feedback_n", type=int)
@click.argument("fix_n", type=int)
def report_unlink(feedback_n: int, fix_n: int) -> None:
    """(Maintainer) Remove fix #FIX_N from feedback #FEEDBACK_N's Tracked-by."""
    from project_kit.report import unlink_fix

    target = _require_report_target()
    if not unlink_fix(target, feedback_n, fix_n):
        raise click.ClickException(f"could not unlink #{fix_n} from #{feedback_n} (gh error).")
    click.echo(f"Unlinked #{fix_n} from #{feedback_n}'s Tracked by.")


def _echo_url_first(kind: str, url: str, target: str, note: str = "") -> None:
    if note:
        click.echo(note)
    click.echo(f"\nOpen this prefilled {kind} on {target} to file it:\n")
    click.echo(f"    {url}\n")
    click.echo(
        "Review the body in the browser before submitting — it carries a redacted "
        "environment block (versions/OS only; home paths stripped, private "
        "capability names withheld)."
    )


def _resolve_report_context(
    target_root: Path, *, workstream_override: str | None, interactive: bool
) -> tuple[str | None, str | None]:
    """Resolve the (project, workstream) context pair for a compose (ADR-050).

    Project: the declared config `name`; when absent on an **interactive**
    compose, prompt once (default: the git remote's repo name, never a path
    segment) and offer to persist the answer — the write-back is what makes
    the prompt once-per-project. Non-interactive/draft paths resolve config →
    remote fallback silently, no prompt. Workstream: `--workstream` override,
    else the pm capability's `context-workstream` read verb via the
    dispatcher; every miss degrades to omission.
    """
    from project_kit import report_context

    project = report_context.read_project_name(target_root)
    if project is None:
        fallback = report_context.git_remote_repo_name(target_root)
        if not interactive:
            project = fallback
        else:
            entered = click.prompt(
                "Project name for the report's context line (a declared name, "
                "never a path; blank to omit)",
                default=fallback or "",
                show_default=bool(fallback),
            ).strip()
            project = entered or None
            if project and click.confirm(
                f"Save name {project!r} to "
                f"{report_context.PROJECT_CONFIG_RELPATH} so future reports "
                "skip this prompt?",
                default=True,
            ):
                try:
                    report_context.write_project_name(target_root, project)
                except click.ClickException as exc:
                    # Context enriches a report, never gates one: an unwritable
                    # config (invalid or unparsable) loses the write-back only.
                    click.echo(f"warning: name not saved — {exc.format_message()}", err=True)

    if workstream_override is not None:
        workstream = workstream_override.strip() or None
    else:
        workstream = report_context.pm_workstream(target_root)
    return project, workstream


def _run_report(
    kind: str,
    title: str,
    prose: str,
    on_behalf_of: str | None,
    include_private: bool,
    do_file: bool,
    assume_yes: bool,
    scratchpad_note: str | None = None,
    workstream_override: str | None = None,
    use_url: bool = False,
    open_browser: bool = False,
) -> None:
    """Reporter path (#662 realization of ADR-047). The **API post is
    primary**: with `gh` authenticated, the full payload (body + any overflow
    comment) is shown once, the confirm names the target AND the posting
    identity ("posts as @<gh login> to <owner/repo>"), and only then does the
    `gh` post run — the note travels as the issue body, never URL-embedded.

    The prefilled-URL form survives only where it is honest: no `gh` auth, or
    an explicit `--url`/`--open` — and only within `URL_BUDGET` (over it the
    form hard-fails at GitHub's edge, so the flow refuses with the API/stage
    alternatives instead). The URL form always warns that the BROWSER's
    logged-in account authors the submit. `--open` opens a within-budget form
    directly (degrades to the printed URL).

    `--yes`/autonomy **stages** the composed payload for the interactive-only
    `pkit report submit` and prints the submit command plus where the draft
    landed (resolved root + per-project store, #693) — it never posts
    (ADR-047: the deliberate `--yes` asymmetry, now stage-shaped). `--file` is
    kept as an explicit gesture; the API post is the default whenever `gh` is
    authenticated.

    Composing **outside a project** (no root resolves) warns loudly and marks
    the environment block NOT COLLECTED rather than emitting a fake-empty one
    (#693) — but still composes: a report from a scratch directory beats no
    report.

    `--scratchpad` inlines a note into the payload (COR-043): redaction-linted
    at compose time on every path (findings ride a stage file's header as
    warnings), oversize split into body-excerpt + ONE overflow comment
    confirmed as a single gesture, and stamped `reported` only on a
    fully-successful post — staged paths stamp at `report submit`, and any
    flow that ends at a URL instead of a post ENDS with the required
    `scratchpad reported` follow-up as its last line (#664). Every
    path carries the project/workstream context (ADR-050): line + marker +
    title parenthetical, stamped into the reported note's frontmatter."""
    from project_kit.report import (
        KIND_LABELS,
        REPORT_TARGET,
        URL_BUDGET,
        SendPayload,
        attach_note,
        build_new_issue_url,
        compose_report,
        current_login,
        gh_authenticated,
        lint_redaction,
        render_finding,
        stage_report,
    )

    del do_file  # accepted for compatibility — the API post is now the default
    # Two roots, deliberately distinct (#693): `project_root` is the RESOLVED
    # project (None outside one) and decides whether an environment can be
    # collected at all; `target_root` is where this invocation reads notes and
    # anchors its draft store, falling back to the cwd so a report composed
    # outside a project is still possible — loudly, never silently.
    project_root = find_target_root()
    target_root = project_root or Path.cwd()
    if project_root is None:
        _warn_no_project_context(target_root)
    _warn_reported_drift(target_root)
    want_url = use_url or open_browser
    gh_ok = gh_authenticated()
    # Interactive = the path that can actually post (the prompt-once name flow
    # runs only there; --yes / URL / no-auth paths resolve silently).
    interactive = not assume_yes and not want_url and gh_ok
    project, ws = _resolve_report_context(
        target_root,
        workstream_override=workstream_override,
        interactive=interactive,
    )
    try:
        title, body, url = compose_report(
            kind,
            title=title,
            prose=prose,
            target_root=project_root,
            on_behalf_of=on_behalf_of,
            include_private=include_private,
            project=project,
            workstream=ws,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    payload = SendPayload(body)
    findings: list = []
    note_path: Path | None = None
    if scratchpad_note:
        note_path = scratchpads.resolve_note(target_root, scratchpad_note)
        note_text = note_path.read_text(encoding="utf-8")
        findings = lint_redaction(note_text)
        payload = attach_note(body, note_path.name, note_text)
        url = build_new_issue_url(
            REPORT_TARGET,
            title=title,
            body=payload.body,
            label=KIND_LABELS[kind],
        )

    if assume_yes:
        # ADR-047 asymmetry: autonomy stages, it NEVER posts. Three short
        # lines — the submit command (the hand-off an agent surfaces, #662)
        # plus WHERE it landed, because the store is per-project (#693).
        draft = stage_report(
            target_root,
            kind=kind,
            title=title,
            payload=payload,
            findings=findings,
            note_path=note_path,
            project=project,
            workstream=ws,
        )
        click.echo(f"staged: pkit report submit {draft.draft_id}")
        _echo_stage_location(project_root, target_root)
        return

    if want_url or not gh_ok:
        _run_report_url_path(
            kind,
            url,
            payload,
            findings,
            gh_ok=gh_ok,
            explicit=want_url,
            open_browser=open_browser,
            note_path=note_path,
        )
        return

    # API-primary gated path: gh authenticated, interactive.
    if findings and not _confirm_past_redaction_findings([render_finding(f) for f in findings]):
        click.echo("Not posted — edit the note and re-run.")
        return
    if _confirm_send_payload(kind, payload, current_login()):
        outcome = _post_confirmed_payload(
            target_root,
            kind=kind,
            title=title,
            payload=payload,
            note_path=note_path,
            project=project,
            workstream=ws,
        )
        if outcome == "failed":
            if len(url) <= URL_BUDGET:
                _echo_url_first(
                    kind,
                    url,
                    REPORT_TARGET,
                    note="\ngh could not file it — use the prefilled URL instead:",
                )
                _echo_browser_identity_warning()
                _echo_reported_followup(note_path)
            else:
                draft = stage_report(
                    target_root,
                    kind=kind,
                    title=title,
                    payload=payload,
                    findings=findings,
                    note_path=note_path,
                    project=project,
                    workstream=ws,
                )
                click.echo(
                    "\ngh could not file it — staged for retry: "
                    f"pkit report submit {draft.draft_id}"
                )
                _echo_stage_location(project_root, target_root)
        return
    if len(url) <= URL_BUDGET:
        _echo_url_first(kind, url, REPORT_TARGET, note="\nNot posted.")
        _echo_browser_identity_warning()
        _echo_reported_followup(note_path)
    else:
        click.echo("\nNot posted — edit and re-run when ready.")


def _run_report_url_path(
    kind: str,
    url: str,
    payload,
    findings: list,
    *,
    gh_ok: bool,
    explicit: bool,
    open_browser: bool,
    note_path: Path | None = None,
) -> None:
    """The URL survivor path (#662): honest only without `gh` auth or on an
    explicit `--url`/`--open`, and only within `URL_BUDGET` — over it the
    prefilled form hard-fails at GitHub's edge, so refuse with the working
    alternatives instead of printing a URL that cannot be opened. Always warns
    that the browser's logged-in account authors the submit. A
    scratchpad-backed flow ENDS with the required `scratchpad reported`
    follow-up as its last line (#664 — a browser filing stamps nothing, so
    the flow must hand over the exact tracking gesture, loudly)."""
    from project_kit.report import (
        REPORT_TARGET,
        URL_BUDGET,
        open_in_browser,
        render_finding,
    )

    if len(url) > URL_BUDGET:
        alternative = (
            "Re-run without --url/--open to review + post via gh (the confirmed API path)."
            if gh_ok
            else "Authenticate gh (`gh auth login`) for the confirmed API "
            "path, or run with --yes to stage and have someone submit with "
            "`pkit report submit <id>`."
        )
        raise click.ClickException(
            f"the prefilled URL is {len(url)} chars — over the {URL_BUDGET}-char "
            "budget GitHub's edge accepts (longer request lines fail with "
            f"HTTP 414), so the browser form cannot carry this report. "
            f"{alternative}"
        )
    _echo_redaction_warnings([render_finding(f) for f in findings])
    note = "" if explicit else ("gh is not authenticated — falling back to the prefilled URL.")
    _echo_url_first(kind, url, REPORT_TARGET, note=note)
    _echo_browser_identity_warning()
    _echo_overflow_draft_note(payload)
    if open_browser:
        if open_in_browser(url):
            click.echo("\nOpened in your browser — check the signed-in account before submitting.")
        else:
            click.echo("\nCould not open a browser — copy the URL above.")
    _echo_reported_followup(note_path)


def _confirm_send_payload(kind: str, payload, login: str | None) -> bool:
    """Show the FULL send payload (body + any overflow comment) once and
    confirm it as a single gesture, naming both the target and the posting
    identity (#662 — the identity is surfaced so a CLI-vs-browser split can
    never misattribute an API post)."""
    from project_kit.report import REPORT_TARGET

    who = f"@{login}" if login else "your gh CLI identity (login unresolved)"
    click.echo(
        "tip: the paired `report-author` skill guides composing (COR-005) — "
        "hand-running the verbs skips that help.\n"
    )
    click.echo(
        f"This posts a PUBLIC {kind} issue to {REPORT_TARGET} as {who} — your "
        "gh CLI identity — with this body:\n"
    )
    click.echo(payload.body)
    if payload.overflow_comment is not None:
        click.echo(
            "\n…plus ONE overflow comment on the same issue, carrying the "
            "full note text (the body above holds an excerpt — one logical "
            "send, per ADR-047):\n"
        )
        click.echo(payload.overflow_comment)
    return click.confirm(f"\nPost as {who} to {REPORT_TARGET}?", default=False)


def _post_confirmed_payload(
    target_root: Path,
    *,
    kind: str,
    title: str,
    payload,
    note_path: Path | None,
    project: str | None,
    workstream: str | None,
) -> str:
    """Execute an already-confirmed send: ensure the kind label on the target
    (create-if-missing, #663 — part of the one confirmed send), post the
    issue, post the overflow comment (one logical send, ADR-047), stamp the
    attached note `reported`. A label ensure failure degrades to posting
    without the label — a warning, never a blocked send. Returns `"failed"`
    (issue not created — the caller names its fallback), `"incomplete"`
    (issue created, overflow comment failed — fail-closed: nothing stamped,
    remediation printed), or `"complete"`."""
    from project_kit.report import (
        KIND_LABELS,
        REPORT_TARGET,
        ensure_kind_label,
        file_report_via_gh,
        post_issue_comment,
    )

    label: str | None = KIND_LABELS[kind]
    if not ensure_kind_label(REPORT_TARGET, kind):
        click.echo(
            f"[warn] could not create/apply the {label!r} label on "
            f"{REPORT_TARGET} — posting without it (the title prefix + body "
            "marker still carry the kind)."
        )
        label = None
    posted = file_report_via_gh(REPORT_TARGET, title=title, body=payload.body, label=label)
    if not posted:
        return "failed"
    if payload.overflow_comment is not None:
        ok, error = post_issue_comment(REPORT_TARGET, posted, payload.overflow_comment)
        if not ok:
            click.echo(
                f"\n[warn] issue created at {posted}, but the overflow "
                "comment FAILED — the send did not complete as confirmed "
                "(ADR-047), so the note was NOT stamped reported."
            )
            click.echo(f"gh error: {error}")
            click.echo(
                "Remediation: post the full note text as a comment on "
                f"{posted} (retry `gh issue comment`, or edit the issue), "
                "then stamp manually with `pkit scratchpad reported`."
            )
            return "incomplete"
    click.echo(f"\n[ok] filed: {posted}")
    _stamp_reported_after_post(
        target_root, note_path, posted, project=project, workstream=workstream
    )
    return "complete"


def _echo_reported_followup(note_path: Path | None) -> None:
    """The required tracking follow-up when a scratchpad-backed compose ends
    in a URL/draft instead of a post (#664 / #660 C.7): the browser cannot
    stamp the note reported, so the flow's LAST line is the exact one-command
    gesture — loud, never a hidden step. No attached note ⇒ nothing to track
    ⇒ silent."""
    if note_path is None:
        return
    slug = scratchpads.note_slug(note_path.name)
    click.echo(
        "\nREQUIRED follow-up — the browser submit cannot stamp the note reported (COR-043):"
    )
    click.echo(f"after filing in the browser, run: pkit scratchpad reported {slug} <issue-ref>")


def _echo_browser_identity_warning() -> None:
    """The browser-identity trap, surfaced on every URL-form print (#662 —
    the CLI composes under the gh identity, but the browser submits as
    whoever is logged in THERE; #659 landed misattributed exactly this way)."""
    click.echo(
        "\nNote: the browser form submits as WHOEVER YOUR BROWSER IS LOGGED "
        "IN AS — check the signed-in account before submitting (it can "
        "silently differ from your gh CLI identity)."
    )


def _root_label(project_root: Path | None, cwd: Path) -> str:
    """How a report message names the root it resolved (#693). Terminal-only —
    paths are fine here; the composed ISSUE body stays path-free."""
    return str(project_root) if project_root is not None else f"no project — {cwd}"


def _warn_no_project_context(cwd: Path) -> None:
    """Loud compose-time warning when no project root resolved (#693). Nothing
    else in the output distinguished a report composed inside a fully-installed
    project from one composed in an empty scratch dir — the trap that caught
    one operator three times in a session. The compose still proceeds (a report
    from outside beats no report); the environment block says it was not
    collected, and this says why and how to fix it."""
    click.echo(
        f"Warning: no pkit project found at {cwd} — the environment block will "
        "be marked NOT COLLECTED (versions, adapter and capabilities are "
        "unknown, not empty), and any staged draft is anchored here rather "
        "than in your project. Run pkit report from your project root for a "
        "useful report.\n"
    )


def _echo_stage_location(project_root: Path | None, target_root: Path) -> None:
    """Name where a staged draft landed: the resolved project root and the
    per-project draft store (#693). Drafts are only visible to a `report
    submit` run under the same root, so the stage message that omitted both was
    the whole reason a draft staged elsewhere read as lost."""
    from project_kit.report import drafts_dir

    click.echo(f"  project root: {_root_label(project_root, target_root)}")
    click.echo(f"  draft store:  {drafts_dir(target_root)}")


def _warn_reported_drift(target_root: Path) -> None:
    """One-line pre-send drift lint (COR-043): a reported note modified since
    its stamp is surfaced before any report verb runs. Warning, never a gate."""
    drifted = scratchpads.drifted_reported_notes(target_root)
    if drifted:
        click.echo(
            "Warning: reported scratchpad note(s) modified since reported: "
            + ", ".join(drifted)
            + " (COR-043 freeze — follow-up thinking belongs in a new note).\n"
        )


def _echo_redaction_warnings(warnings: list[str]) -> None:
    """Draft-path form of the redaction lint: findings ride as warnings.
    Takes rendered lines (`report.render_finding`) so the stage-file header's
    stored warnings flow through the same surface."""
    if not warnings:
        return
    click.echo("Warning: possible un-redacted content in the attached note — review before filing:")
    for line in warnings:
        click.echo(f"  {line}")
    click.echo("")


def _confirm_past_redaction_findings(warnings: list[str]) -> bool:
    """Interactive form of the redaction lint: edit-or-send-anyway. Takes
    rendered lines, same as `_echo_redaction_warnings`."""
    click.echo("Possible un-redacted content in the attached note:")
    for line in warnings:
        click.echo(f"  {line}")
    return click.confirm("\nSend anyway? (decline to edit the note first)", default=False)


def _echo_overflow_draft_note(payload) -> None:
    """On draft/URL paths an oversize attachment can't carry its overflow
    comment — say so instead of silently dropping the full text."""
    if payload.truncated:
        click.echo(
            "\nNote: the attached note exceeds the issue-body budget — the draft "
            "body carries an excerpt. After filing, add the full note text as "
            "the first comment (the note file itself is the source)."
        )


def _stamp_reported_after_post(
    target_root: Path,
    note_path: Path | None,
    posted: str,
    *,
    project: str | None = None,
    workstream: str | None = None,
) -> None:
    """Stamp the attached note `reported` after a fully-successful post
    (COR-043: entering the state is produced by an actual send), carrying the
    resolved project/workstream pair into the frontmatter (ADR-050 / #643's
    optional stamp kwargs). Best-effort past the post: the foreign write
    already happened, so a stamp failure warns + names the manual gesture
    rather than erroring the command."""
    if note_path is None:
        return
    area = target_root / ".pkit" / "scratchpad"
    if note_path.parent not in (area / "active", area / "reported"):
        click.echo(f"note {note_path} is outside .pkit/scratchpad/active/ — not stamped reported.")
        return
    try:
        ref = scratchpads.normalize_issue_ref(posted.strip())
        stamp = stamp_reported(
            target_root,
            note_path.name,
            (ref,),
            project=project,
            workstream=workstream,
        )
    except click.ClickException as exc:
        click.echo(
            f"[warn] could not stamp the note reported ({exc.message}) — stamp "
            f"manually: pkit scratchpad reported {scratchpads.note_slug(note_path.name)} <ref>"
        )
        return
    if stamp.src != stamp.dst:
        click.echo(
            f"Stamped reported: {stamp.src.relative_to(target_root)} -> "
            f"{stamp.dst.relative_to(target_root)}"
        )
    elif stamp.added:
        click.echo(f"Recorded {', '.join(stamp.added)} on {stamp.dst.relative_to(target_root)}")


_REPORT_OPTS = [
    click.option("--title", required=True, help="One-line summary."),
    click.option("--body", "prose", required=True, help="The report text (prose)."),
    click.option(
        "--file",
        "do_file",
        is_flag=True,
        default=False,
        help="Post via `gh` after the confirm. Now the default whenever `gh` is "
        "authenticated; kept as an explicit gesture.",
    ),
    click.option(
        "--url",
        "use_url",
        is_flag=True,
        default=False,
        help="Use the prefilled browser-URL form instead of the gh post (within "
        "the URL budget only — an oversized report is refused with the API/stage "
        "alternatives; the BROWSER's logged-in account authors the submit).",
    ),
    click.option(
        "--open",
        "open_browser",
        is_flag=True,
        default=False,
        help="Open the prefilled form in your browser (implies --url; degrades "
        "to printing the URL).",
    ),
    click.option(
        "--yes",
        "assume_yes",
        is_flag=True,
        default=False,
        help="Non-interactive: STAGE the composed payload for `pkit report "
        "submit` — the foreign write is never auto-posted (ADR-047: --yes "
        "stages, never posts).",
    ),
    click.option(
        "--on-behalf-of",
        default=None,
        help="Attribute the report to @login (files under your identity).",
    ),
    click.option(
        "--include-private",
        is_flag=True,
        default=False,
        help="Include incubated (in-repo) capability names in the environment block.",
    ),
    click.option(
        "--scratchpad",
        "scratchpad_note",
        default=None,
        metavar="SLUG",
        help="Attach a scratchpad note (slug, filename, or path) as a collapsed "
        "as-sent section; redaction-linted at compose time, and stamped "
        "reported on a successful post only (COR-043).",
    ),
    click.option(
        "--workstream",
        "workstream_override",
        default=None,
        metavar="NAME",
        help="Workstream for the report's context line/marker, overriding the "
        "pm-derived value (branch → issue → workstream, when the "
        "project-management capability is installed; ADR-050).",
    ),
]


def _with_report_opts(fn):
    for opt in reversed(_REPORT_OPTS):
        fn = opt(fn)
    return fn


@report.command("bug")
@_with_report_opts
def report_bug(
    title: str,
    prose: str,
    do_file: bool,
    use_url: bool,
    open_browser: bool,
    assume_yes: bool,
    on_behalf_of: str | None,
    include_private: bool,
    scratchpad_note: str | None,
    workstream_override: str | None,
) -> None:
    """File a structured bug report to project-kit."""
    _run_report(
        "bug",
        title,
        prose,
        on_behalf_of,
        include_private,
        do_file,
        assume_yes,
        scratchpad_note,
        workstream_override,
        use_url,
        open_browser,
    )


@report.command("feedback")
@_with_report_opts
def report_feedback(
    title: str,
    prose: str,
    do_file: bool,
    use_url: bool,
    open_browser: bool,
    assume_yes: bool,
    on_behalf_of: str | None,
    include_private: bool,
    scratchpad_note: str | None,
    workstream_override: str | None,
) -> None:
    """File freeform feedback to project-kit."""
    _run_report(
        "feedback",
        title,
        prose,
        on_behalf_of,
        include_private,
        do_file,
        assume_yes,
        scratchpad_note,
        workstream_override,
        use_url,
        open_browser,
    )


@report.command("change-request")
@_with_report_opts
def report_change_request(
    title: str,
    prose: str,
    do_file: bool,
    use_url: bool,
    open_browser: bool,
    assume_yes: bool,
    on_behalf_of: str | None,
    include_private: bool,
    scratchpad_note: str | None,
    workstream_override: str | None,
) -> None:
    """File a change/feature request to project-kit.

    Structured-ish: the body is scaffolded into a motivation / desired behaviour /
    current workaround template (unless your prose already carries those
    headings). The title gets the `[CR]` prefix — every kind carries one
    (`[Bug]`/`[Feedback]`/`[CR]`, #663) so the maintainer inbox can classify
    it even when the GitHub label is dropped.
    """
    _run_report(
        "change-request",
        title,
        prose,
        on_behalf_of,
        include_private,
        do_file,
        assume_yes,
        scratchpad_note,
        workstream_override,
        use_url,
        open_browser,
    )


@report.command("submit")
@click.argument("draft_id", required=False)
@click.option(
    "--yes",
    "assume_yes",
    is_flag=True,
    default=False,
    help="Refused. submit is the human half of the stage+submit split and "
    "never runs non-interactively (ADR-047: autonomy stages, only a human "
    "posts).",
)
def report_submit(draft_id: str | None, assume_yes: bool) -> None:
    """(Human) Review + post a staged report draft; bare lists the drafts.

    The consuming half of the agent-stage + human-submit split (#662): a
    `--yes` compose stages its full payload under the gitignored
    `.pkit/scratchpad/.report-drafts/`; this verb loads it, re-surfaces the
    compose-time redaction warnings, shows the whole payload (body + any
    overflow comment), names the posting identity and target, and posts via
    `gh` only on an explicit confirm — then stamps/tracks exactly as a direct
    post (COR-043) and removes the stage file. Interactive-only: `--yes` is
    refused, so ADR-047's never-auto-post gate survives the new realization.

    The store is **per-project**, so every message here names the store path it
    read (and the root that resolved it) — a draft staged under another root is
    not lost, it is simply invisible from this one (#693).
    """
    from project_kit.report import (
        current_login,
        drafts_dir,
        gh_authenticated,
        list_staged,
        load_staged,
    )

    project_root = find_target_root()
    target_root = project_root or Path.cwd()
    store = drafts_dir(target_root)  # the store THIS invocation can see (#693)
    if draft_id is None:
        drafts = list_staged(target_root)
        if not drafts:
            click.echo(
                f"No staged report drafts in {store} — `pkit report <kind> … "
                "--yes` stages one (drafts are per-project)."
            )
            return
        click.echo(f"Staged report drafts ({store}):\n")
        for d in drafts:
            warn = f"  [{len(d.warnings)} redaction warning(s)]" if d.warnings else ""
            click.echo(f"  {d.draft_id:<28} {d.kind:<15} {d.title}{warn}")
        click.echo("\nReview + post one with `pkit report submit <id>`.")
        return
    if assume_yes:
        raise click.ClickException(
            "submit never runs non-interactively — `--yes` stages "
            "(`pkit report … --yes`), a human submits (ADR-047)."
        )
    draft = load_staged(target_root, draft_id)
    if draft is None:
        raise click.ClickException(
            f"no staged draft {draft_id!r} in {store} "
            f"(project root: {_root_label(project_root, target_root)}). "
            "Drafts are per-project — staged in a different project? Run "
            "submit from that project's root. `pkit report submit` lists the "
            "drafts visible here."
        )
    if not gh_authenticated():
        raise click.ClickException("submit posts via gh — authenticate first (`gh auth login`).")
    if draft.warnings and not _confirm_past_redaction_findings(list(draft.warnings)):
        click.echo("Not posted — draft kept; edit the source note and restage.")
        return
    if not _confirm_send_payload(draft.kind, draft.payload, current_login()):
        click.echo(f"\nNot posted — draft kept ({draft.draft_id}).")
        return
    note_path = (target_root / draft.note) if draft.note else None
    outcome = _post_confirmed_payload(
        target_root,
        kind=draft.kind,
        title=draft.title,
        payload=draft.payload,
        note_path=note_path,
        project=draft.project,
        workstream=draft.workstream,
    )
    if outcome == "failed":
        click.echo(
            f"\ngh could not file it — draft kept; retry `pkit report submit {draft.draft_id}`."
        )
        return
    if outcome == "incomplete":
        # The issue exists; the draft is kept ONLY as the source of the full
        # overflow text for the manual remediation — resubmitting would file
        # a duplicate issue.
        click.echo(
            f"Draft kept ({draft.draft_id}) as the source of the full text — "
            "do NOT resubmit; retry the comment instead."
        )
        return
    draft.path.unlink(missing_ok=True)
    click.echo(f"Draft removed: {draft.draft_id}")


@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be refreshed without writing any files (per COR-004).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an installed capability even when the source version is "
    "OLDER than the installed one (a downgrade). Without this, sync refuses "
    "such a downgrade rather than silently clobbering newer state (issue #524).",
)
def sync(dry_run: bool, force: bool) -> None:
    """Re-run propagation: refresh kit-owned content from source (per COR-001)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    run_sync(target_root, dry_run=dry_run, force=force)


@main.command()
@click.argument("targets", nargs=-1)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show which merge primitives would run without invoking them (per COR-004).",
)
def merge(targets: tuple[str, ...], dry_run: bool) -> None:
    """Re-run merge delivery on adapter-owned config files (per COR-002).

    Optional TARGETS filter to specific adapter names; all installed adapters
    that ship a merge primitive run by default.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    run_merge(target_root, targets=targets, dry_run=dry_run)


@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be upgraded without writing any files (per COR-004).",
)
@click.option(
    "--no-pin",
    "no_pin",
    is_flag=True,
    default=False,
    help="Keep this project un-pinned (opt out of pin-by-default): it keeps "
    "following the installed global tool. Per ADR-049.",
)
@click.option(
    "--no-self-update",
    "no_self_update",
    is_flag=True,
    default=False,
    help="Don't update the pkit tool itself when it's stale — just print the "
    "command (the old detect-and-instruct behaviour). Per ADR-044.",
)
def upgrade(dry_run: bool, no_pin: bool, no_self_update: bool) -> None:
    """Transition the project to a newer backbone (per COR-010).

    Bumps the project to the source kit's current backbone version. To
    upgrade a single capability, use `pkit capabilities upgrade <name>`.

    **Updates the pkit tool itself** when it is behind (ADR-044): it runs
    `uv tool install --force …@<latest>` and re-runs the upgrade under the new
    version — degrading to just printing the command when non-interactive or if the
    install is declined. `--no-self-update` keeps the print-only behaviour. Run
    outside any project, `pkit upgrade` updates the tool only.

    **Pins the project by default** at the version it upgrades to (ADR-049), so it
    stays version-locked with no separate `pkit pin` step. Pass `--no-pin` to keep
    it un-pinned. A project that is already pinned advances its pin either way;
    self-host is never pinned.
    """
    target_root = find_target_root()
    if target_root is None:
        # Outside any project: update the tool only ("just update my tool").
        run_tool_update(dry_run=dry_run, self_update=not no_self_update)
        return
    run_upgrade(target_root, dry_run=dry_run, pin=not no_pin, self_update=not no_self_update)


@main.command()
@click.argument("version", required=False)
def pin(version: str | None) -> None:
    """Pin this project to a pkit version (per ADR-049): write `.pkit/version-pin`.

    VERSION, when given, is a version number only — `1.145.0`, or `v1.145.0`
    (a single leading `v` is stripped). Branch, commit-sha, and pre-release /
    build-metadata pins are refused: the router can only route a bare `v<semver>`
    tag, so those are deferred. Both forms require `.pkit/manifest.yaml` (the
    project's recorded content version); run `pkit sync` first if it is absent.

    With no argument, freezes the project at its current CONTENT version
    (`.pkit/manifest.yaml`'s `backbone_version`) — the common case: lock this
    project where its content is, don't move it. With a VERSION token, the
    behaviour depends on how it orders against that content version:

    \b
    - equal   → freeze in place (write the pin, no content sync);
    - newer   → reconcile content forward to the target under that version's own
                code, then flip the pin last (atomically);
    - older   → REFUSED — pkit migrations are forward-only (COR-010), so there is
                no safe downgrade; `git checkout` the `.pkit/` tree to roll back.

    Once the directive exists, the pkit router re-execs `uvx project-kit@<pin>` so
    the pinned version serves every command; a global-tool upgrade no longer moves
    this project. Raise the pin later with `pkit upgrade`; remove it with
    `pkit unpin`.

    Refused in the methodology's source repository, where the router runs the
    checkout's own code before any pin is read (ADR-059).
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if version is None:
        freeze_at_content(target_root)
        return
    reconcile_pin(target_root, version)


@main.command()
def unpin() -> None:
    """Remove this project's version pin (per ADR-049): delete `.pkit/version-pin`.

    The project reverts to floating on the installed pkit binary — the router
    runs the installed tool as-is (today's un-pinned behaviour). Idempotent: it
    is fine to run when no pin file is present.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    pin_path = router.pin_file_path(target_root)
    if pin_path.exists():
        router.write_version_pin(target_root, None)
        rel = pin_path.relative_to(target_root)
        click.echo(f"Removed pin ({rel}); project now floats on the installed tool.")
    else:
        click.echo("No pin to remove; project already floats on the installed tool.")


@main.group("visibility", invoke_without_command=True)
@click.pass_context
def visibility(ctx: click.Context) -> None:
    """Control pkit's git footprint (per ADR-009). No subcommand = status.

    `shared` (default): pkit committed; `.git/info/exclude` kept clear.
    `private`: hide the whole footprint via the per-clone `.git/info/exclude`
    (no committed `.gitignore` is ever written) + a confirm-gated untrack.
    `untrack`: the standalone index cleanup (its own verb — the destructive
    git-index gesture is never silently folded into a mode flip).
    """
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import visibility as vis

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(vis.status(target_root), nl=False)


def _visibility_target() -> Path:
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    return target_root


@visibility.command("shared")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview clearing the .git/info/exclude region without changing anything.",
)
def visibility_shared(dry_run: bool) -> None:
    """Return pkit to committed (default): clear pkit's `.git/info/exclude` region."""
    from project_kit import visibility as vis

    click.echo(
        vis.set_visibility(_visibility_target(), "shared", dry_run=dry_run, confirm=click.confirm),
        nl=False,
    )


@visibility.command("private")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview the .git/info/exclude write + untrack set without changing anything.",
)
def visibility_private(dry_run: bool) -> None:
    """Hide the whole footprint via the per-clone `.git/info/exclude` (no committed
    `.gitignore` is ever written) + a confirm-gated untrack of tracked footprint files."""
    from project_kit import visibility as vis

    click.echo(
        vis.set_visibility(_visibility_target(), "private", dry_run=dry_run, confirm=click.confirm),
        nl=False,
    )


@visibility.command("untrack")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview the footprint files that would be removed from the index.",
)
def visibility_untrack(dry_run: bool) -> None:
    """Remove already-tracked pkit footprint files from the git index (per ADR-009).

    Footprint-only, confirm-gated, working-copy-preserving (`git rm --cached`).
    Refuses mid-merge/rebase or when footprint paths have staged changes. Its own
    subcommand so the one git-index-mutating gesture stays explicit, never folded
    silently into a `shared`/`private` mode flip.
    """
    from project_kit import visibility as vis

    click.echo(vis.untrack(_visibility_target(), dry_run=dry_run, confirm=click.confirm), nl=False)


@capabilities.command("upgrade")
@click.argument("name")
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="Prompt per collision (override / skip / inspect) when the upgraded "
    "source introduces new naming collisions (per COR-017).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Proceed even when upgrading this capability would desync an installed "
    "dependent's declared version range (COR-030) or leave another capability's "
    "mandatory process connection unmet (COR-053 point 6). Mirrors the uninstall "
    "--force shape; use when cascade-upgrading dependents manually.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would happen without writing any files.",
)
def upgrade_capability_cmd(name: str, interactive: bool, force: bool, dry_run: bool) -> None:
    """Refresh a single installed capability from source (per COR-017).

    Walks the capability's source subtree, detects any *new* naming
    collisions introduced since install, and either:
    - Refreshes in place if no new collisions are found, preserving any
      skip state from the original install.
    - Refuses (without --interactive) and suggests `--interactive` if
      new collisions exist.
    - Prompts per collision and then refreshes with the merged skip
      state (with --interactive).

    Also enforces capability dependency constraints (COR-030) with a
    direction-split disposition:
    - If the new source version of this capability (the *dependent*) has
      requirements its dependencies don't satisfy → refuse with hint.
    - If this capability is a *dependency* for other installed capabilities
      and the new version would fall outside their declared range → loud
      warning and require --force to proceed (not a hard block; a hard
      block would deadlock since cascade-upgrade is out of scope).
    """
    from project_kit import capabilities as caps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    source_kit = find_source_kit()
    # The methodology's source repository run by code that is not its own (the
    # gap, ADR-059): refuse before anything is read or written (#1090).
    refuse_propagation_into_source(
        target_root,
        source_kit,
        command=f"capabilities upgrade {name}",
        would=(
            "refresh the capability with that code — a kit-shipped one from that "
            "tree, over the one it is built from"
        ),
        own_code_does=None,
    )

    if not caps.is_installed(target_root, name):
        raise click.ClickException(
            f"capability {name!r} is not installed. Use `pkit capabilities install {name}` first."
        )

    # Origin-aware branch (COR-031 D1/D4): an incubated (in-repo) capability has
    # no kit source to reconcile against — the working tree *is* the source. It
    # must never hit the kit-source orphan path below (which would mislabel it
    # "no longer ships" and steer the adopter toward the destructive uninstall).
    # "Upgrade" for it means re-applying deploy from the in-repo tree, mirroring
    # the sync skip-branch.
    if caps.read_capability_origin(target_root, name) == caps.INCUBATED_IN_REPO:
        _upgrade_incubated_capability(target_root, source_kit, name, dry_run=dry_run)
        return
    # The methodology's source run by its own code (ADR-059 point 2): the tree a
    # kit-shipped capability is refreshed from is its own subtree, so there is
    # nothing to copy and no migration to run — re-deploy it in place (#1107).
    if caps.authored_in_source(target_root, source_kit, name):
        _upgrade_capability_in_source(target_root, source_kit, name, dry_run=dry_run)
        return

    capability_source = caps.find_capability_in_source(source_kit, name)
    if capability_source is None:
        raise click.ClickException(
            f"capability {name!r} no longer ships from source at {source_kit}/capabilities/. "
            "Use `pkit capabilities uninstall` to remove the orphan, or sync "
            "the source kit if you expect it to ship."
        )

    # --- Capability dependency check: direction-split (COR-030) ---

    # Direction 1 — this capability is the *dependent*: its new source version
    # may declare requires_capabilities that the installed dependencies don't
    # satisfy. Refuse with hint (operator controls which version to upgrade to).
    dep_conflicts = caps.check_capability_dependencies(
        target_root, capability_source.package.requires_capabilities
    )
    if dep_conflicts:
        lines = []
        for conflict in dep_conflicts:
            if conflict.reason == "absent":
                lines.append(
                    f"    - '{conflict.dep_name}' ({conflict.dep_version_range}) is not installed"
                )
            else:
                lines.append(
                    f"    - '{conflict.dep_name}' {conflict.dep_version_range} "
                    f"required but v{conflict.installed_version} is installed"
                )
        raise click.ClickException(
            f"capability {name!r} v{capability_source.package.version} has "
            f"unsatisfied dependencies:\n" + "\n".join(lines) + "\n"
            "Install or upgrade the required capabilities first, then retry."
        )
    # The same direction for its mandatory process connections (COR-053 point 6):
    # the new version's generated `depends-on` against the wiring it would leave.
    _refuse_unmet_mandatory_upstreams(target_root, capability_source)

    # Direction 2 — this capability is a *dependency*: upgrading it to the new
    # source version may push it outside the declared range of installed
    # dependents. Warn loudly + require --force (not a hard block — a hard block
    # would deadlock since cascade-upgrade is out of scope per COR-030).
    new_version = capability_source.package.version
    desynced_dependents = _find_desynced_dependents(
        target_root, dep_name=name, new_dep_version=new_version
    )
    if desynced_dependents and not force:
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"Warning: upgrading {name!r} to v{new_version} would desync "
                f"{len(desynced_dependents)} installed dependent(s):",
            )
        )
        for dep_cap, declared_range in desynced_dependents:
            click.echo(
                f"    - '{dep_cap}' declares {name!r} {declared_range} "
                f"(v{new_version} is outside this range)"
            )
        raise click.ClickException(
            "refusing to upgrade: the new version would desync installed dependents.\n"
            "Upgrade those capabilities to versions compatible with the new range, "
            "then retry — or pass --force to proceed anyway and fix dependents "
            "manually (the deadlock-free override per COR-030)."
        )
    if desynced_dependents and force:
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"Warning (--force): upgrading {name!r} to v{new_version} "
                f"desyncs {len(desynced_dependents)} dependent(s):",
            )
        )
        for dep_cap, declared_range in desynced_dependents:
            click.echo(
                f"    - '{dep_cap}' declares {name!r} {declared_range} "
                f"(v{new_version} is outside this range)"
            )
        click.echo(
            "  Proceeding under --force; upgrade dependent capabilities to restore consistency."
        )
    # The same direction for mandatory process connections aimed at this
    # capability (COR-053 point 6): warn, naming each, and proceed under --force.
    _warn_mandatory_counterparts(
        target_root,
        name,
        action=f"upgrading {name!r} to v{new_version}",
        verb="upgrade",
        force=force,
        replacement=capability_source,
    )

    # --- Collision detection ---

    # Detect collisions introduced by the upgraded source. Filter
    # self-collisions against the currently-installed copy — those will
    # be replaced in place.
    new_collisions = caps.detect_upgrade_collisions(target_root, capability_source)
    prior_skipped = list(caps.read_prior_skipped_artifacts(target_root, name))

    if new_collisions and not interactive:
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"{len(new_collisions)} new naming collision(s) introduced by "
                f"v{capability_source.package.version}:",
            )
        )
        for finding in new_collisions:
            click.echo(
                f"    - {finding.artifact_kind} '{finding.artifact_name}' "
                f"collides with {finding.target_path.relative_to(target_root)}"
            )
        raise click.ClickException(
            "refusing to upgrade with unresolved collisions. "
            "Re-run with --interactive to resolve them."
        )

    new_skipped: list[tuple[str, str]] = []
    if new_collisions and interactive:
        click.echo(
            "\n  "
            + cli_render.style(
                "strong", f"{len(new_collisions)} new collision(s) — resolve per artifact:"
            )
            + "\n"
        )
        for finding in new_collisions:
            choice = _resolve_collision_interactive(target_root, finding, dry_run=dry_run)
            if choice == "skip":
                new_skipped.append((finding.artifact_kind, finding.artifact_name))

    # Merge prior + new skip state. De-dup by (kind, name).
    merged_skipped = tuple(sorted(set(prior_skipped).union(new_skipped)))

    refreshed_path = caps.refresh_capability(
        target_root,
        capability_source,
        skipped_artifacts=merged_skipped,
        dry_run=dry_run,
    )

    verb = "Would refresh" if dry_run else "Refreshed"
    skip_note = f" ({len(merged_skipped)} artifact(s) skipped)" if merged_skipped else ""
    click.echo(
        "\n  "
        + cli_render.style(
            "strong",
            f"{verb} capability {name!r} -> v{capability_source.package.version} "
            f"at {refreshed_path.relative_to(target_root)}/{skip_note}",
        )
    )

    if not dry_run:
        # Re-run installed adapter primitives so the harness side picks
        # up any newly-added skills/agents from the upgraded capability,
        # then provision its query commands, as sync would (#1090).
        _deploy_capability(target_root, source_kit, name)


@main.command()
@click.option(
    "--include-refs/--no-refs",
    default=True,
    show_default=True,
    help="Run the `refs` member; `--no-refs` is `--skip refs`, kept for scripts that pass it.",
)
@click.option(
    "--only",
    "only",
    multiple=True,
    metavar="NAME",
    help="Run only the named validator(s); repeatable. A capability's validator is "
    "addressed `<capability>:<name>`.",
)
@click.option(
    "--skip",
    "skip",
    multiple=True,
    metavar="NAME",
    help="Skip the named validator(s); repeatable.",
)
def validate(include_refs: bool, only: tuple[str, ...], skip: tuple[str, ...]) -> None:
    """Check project state against invariants (per COR-004): every registered validator,
    grouped by functionality. Exit 1 on errors only.

    The backbone's members run first — manifests, schemas, configuration,
    packages, connections, versions, friction, rule-sets, decisions, refs,
    process, data — then each installed capability's, registered in its
    package metadata (`validators:`, each naming a `commands:` leaf that
    declares the query contract). One renderer prints every section;
    warnings, information and reports print, only errors fail. The
    diff-scoped checks (`friction check`, `migrations check-diff`, `release
    lint`) are not members: they answer about a change, not the tree.
    Reference: `.pkit/cli/README.md`, "validate"; the registry's shape is ADR-058.
    """
    from project_kit import validators

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")
    skipped = [*skip, *([] if include_refs else ["refs"])]
    try:
        selected = validators.select(
            validators.registered_validators(target_root), only=only, skip=skipped
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    results = validators.run_all(target_root, selected)
    click.echo(validators.render(target_root, results), nl=False)
    if validators.has_errors(results):
        raise SystemExit(1)


# --- refs family (per COR-013 / #74) ----------------------------------


@main.group()
def refs() -> None:
    """Reference-graph operations across agents, skills, decisions, hooks (per COR-013)."""


@refs.command("validate")
def refs_validate() -> None:
    """Bidirectional consistency + hook closure + exactly-one-owner check across the artifact
    corpus."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    issues = refs_mod.validate_corpus(target_root)
    lines = [
        cli_render.style(
            "title",
            "Reference validation — bidirectional consistency + hook closure + exactly-one-owner",
        ),
        "",
    ]
    if not issues:
        lines.append("  " + cli_render.style("strong", "All checks passed."))
        click.echo("\n".join(lines) + "\n", nl=False)
        return
    lines.append("  " + cli_render.style("strong", f"{len(issues)} issue(s) found:"))
    for issue in issues:
        lines += [f"    {issue.location}", f"      → {issue.diagnosis}"]
    click.echo("\n".join(lines) + "\n", nl=False)
    raise SystemExit(1)


@refs.command("show")
@click.argument("artifact_name")
def refs_show(artifact_name: str) -> None:
    """Show outgoing references for one agent or skill (by name)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    matches = [a for a in artifacts if a.name == artifact_name]
    if not matches:
        raise click.ClickException(f"no agent or skill named {artifact_name!r}.")
    for art in matches:
        click.echo(cli_render.style("title", f"{art.kind} {art.namespace}/{art.name}"))
        click.echo(f"    path: {art.path.relative_to(target_root)}")
        for bucket, items in refs_mod.outgoing_refs(art).items():
            if items:
                click.echo("    " + cli_render.style("heading", f"{bucket}:"))
                for item in items:
                    click.echo(f"      {item}")


@refs.command("who-references")
@click.argument("target")
def refs_who_references(target: str) -> None:
    """Reverse lookup: list agents/skills that reference the target (path, record ID, hook)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    matches = refs_mod.who_references(artifacts, target)
    if not matches:
        click.echo(f"  no artifact references {target!r}.")
        return
    click.echo(cli_render.style("strong", f"{len(matches)} artifact(s) reference {target!r}:"))
    for art in matches:
        click.echo(f"    {art.kind} {art.namespace}/{art.name}")


@refs.command("lookup")
@click.argument("record_id")
def refs_lookup(record_id: str) -> None:
    """Resolve a record ID (`COR-005`, `PRJ-002`) to its file, a rule (`RS-CMN-001`,
    `RS-CMN-001#point`, `[living-docs:RS-LDOC-001]`) to its place in its rule set,
    or a role or point address (`[pkit::documentation]`, `[pkit::documentation:readers]`)
    to where an installed capability declares it."""
    from project_kit import rule_sets as rule_sets_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if refs_mod.is_address_citation(record_id):
        address = refs_mod.resolve_address(target_root, record_id)
        if address.malformed:
            raise click.ClickException(f"{record_id!r} is {address.problem}.")
        if not address.resolved:
            raise click.ClickException(f"{record_id!r} does not resolve: {address.problem}.")
        for location in address.locations:
            click.echo(location)
        return
    if rule_sets_mod.is_rule_citation(record_id):
        resolution = refs_mod.resolve_rule_citation(target_root, record_id)
        if not resolution.resolved:
            raise click.ClickException(f"{record_id!r} does not resolve: {resolution.problem}.")
        click.echo(resolution.location)
        return
    path = refs_mod.resolve_record(target_root, record_id)
    if path is None:
        raise click.ClickException(f"no record matches {record_id!r}.")
    click.echo(path.relative_to(target_root))


@refs.command("rename")
@click.argument("old")
@click.argument("new")
@click.option(
    "--dry-run", is_flag=True, default=False, help="Report what would change without writing."
)
def refs_rename(old: str, new: str, dry_run: bool) -> None:
    """Bulk rewrite a reference value across every agent/skill (frontmatter + body)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    modified = refs_mod.rename_reference(target_root, old, new, dry_run=dry_run)
    if not modified:
        click.echo(f"  no references to {old!r} found.")
        return
    verb = "would modify" if dry_run else "modified"
    click.echo(cli_render.style("strong", f"  {verb} {len(modified)} file(s):"))
    for path in modified:
        click.echo(f"    {path.relative_to(target_root)}")


@refs.command("rot")
def refs_rot() -> None:
    """List references to superseded records, dropped scratchpads, or missing files."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    issues = refs_mod.find_rot(target_root, artifacts)
    lines = [
        cli_render.style(
            "title", "Reference rot — superseded records, dropped scratchpads, missing files"
        ),
        "",
    ]
    if not issues:
        lines.append("  no rotten references found.")
        click.echo("\n".join(lines) + "\n", nl=False)
        return
    lines.append("  " + cli_render.style("strong", f"{len(issues)} rotten reference(s):"))
    for issue in issues:
        lines += [f"    {issue.location}", f"      → {issue.diagnosis}"]
    click.echo("\n".join(lines) + "\n", nl=False)


@refs.command("graph")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["ascii", "text", "dot"]),
    default="ascii",
    show_default=True,
    help="Output format. `ascii` (default) is a tree-style diagram with "
    "box-drawing characters; `text` is a plain outline; `dot` is Graphviz "
    "(pipe to `dot -Tpng > graph.png` to render).",
)
def refs_graph(fmt: str) -> None:
    """Emit the reference graph for visualisation or downstream tooling."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    if fmt == "dot":
        click.echo(refs_mod.emit_graph_dot(artifacts))
    elif fmt == "text":
        click.echo(refs_mod.emit_graph_text(artifacts))
    else:
        click.echo(refs_mod.emit_graph_ascii(artifacts))


# --- hooks family (per COR-013 / #74) ---------------------------------


@main.group()
def hooks() -> None:
    """Hook-registry queries (per COR-013): list, resolve, who-needs, who-provides."""


@hooks.command("list")
def hooks_list() -> None:
    """List every declared hook with its providers (in precedence order)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    providers = refs_mod.load_hook_providers(target_root)
    artifacts = refs_mod.load_artifacts(target_root)
    needed = {hk for art in artifacts for hk in art.declared.needs}
    declared_hooks = sorted({p.hook for p in providers} | needed)
    if not declared_hooks:
        click.echo("  no hooks declared.")
        return
    lines = [
        cli_render.style("title", f"Hooks — {len(declared_hooks)} declared")
        + "   (bound provider by precedence)"
    ]
    for hook in declared_hooks:
        winner = refs_mod.resolve_hook(providers, hook)
        marker = f" -> {winner.tier}:{winner.source}" if winner else " (no provider)"
        lines.append(f"  {hook}{marker}")
    click.echo("\n".join(lines) + "\n", nl=False)


@hooks.command("resolve")
@click.argument("hook")
def hooks_resolve(hook: str) -> None:
    """Show the currently-bound provider for a hook (by precedence)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    providers = refs_mod.load_hook_providers(target_root)
    winner = refs_mod.resolve_hook(providers, hook)
    if winner is None:
        raise click.ClickException(f"no provider declared for hook {hook!r}.")
    click.echo(f"  {hook} -> {winner.tier}:{winner.source} ({winner.implementation})")


@hooks.command("who-needs")
@click.argument("hook")
def hooks_who_needs(hook: str) -> None:
    """List agents/skills that declare `needs: <hook>`."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    matches = [a for a in artifacts if hook in a.declared.needs]
    if not matches:
        click.echo(f"  no artifact declares need for {hook!r}.")
        return
    click.echo(cli_render.style("strong", f"{len(matches)} artifact(s) need {hook!r}:"))
    for art in matches:
        click.echo(f"  {art.kind} {art.namespace}/{art.name}")


@hooks.command("who-provides")
@click.argument("hook")
def hooks_who_provides(hook: str) -> None:
    """List all providers for a hook (skills + adapter/capability package.yaml)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    providers = refs_mod.load_hook_providers(target_root)
    matches = [p for p in providers if p.hook == hook]
    if not matches:
        click.echo(f"  no provider declared for hook {hook!r}.")
        return
    order = {"project": 0, "capability": 1, "adapter": 2, "core": 3}
    matches.sort(key=lambda p: order.get(p.tier, 99))
    click.echo(cli_render.style("strong", f"{len(matches)} provider(s) for {hook!r}:"))
    for p in matches:
        click.echo(f"  {p.tier:8} {p.source:30} {p.implementation}")


@main.group()
def migrations() -> None:
    """Migration framework operations (per COR-010)."""


@migrations.command("check-diff")
@click.option(
    "--base",
    "base_ref",
    metavar="REF",
    default=None,
    help="Base ref to diff against. Default: $PKIT_CHECK_BASE, else the default branch "
    "(`pkit repository base` shows it).",
)
@click.option(
    "--include-working-tree",
    is_flag=True,
    default=False,
    help="Include staged + unstaged changes in the diff (pre-commit use). "
    "Without this flag, only committed changes are checked (CI's view).",
)
def migrations_check_diff(base_ref: str | None, include_working_tree: bool) -> None:
    """Verify migration coverage in the diff between the base and the project state.

    Walks the diff for migration-triggering changes (renames + deletions
    in kit-owned trees per COR-010 / `.pkit/rules/core.md` rule 7), then
    checks whether the same diff includes a matching migration script.

    The base is REF, else $PKIT_CHECK_BASE, else the default branch
    (COR-054); the diff starts where HEAD left it, and a base that resolves
    nowhere refuses the run with its fix. Default scope: committed branch
    changes only — what CI sees on a PR. With `--include-working-tree`, the
    scope extends to staged + unstaged changes — what's about to be
    committed. The pre-commit form for local use.

    Exits 0 when covered or no triggers exist; exits 1 when triggers
    exist without matching migrations, listing the affected tiers so the
    author can land the missing scripts.
    """
    from project_kit import migrations as migrations_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    fork = _settled_base(target_root, base_ref).fork
    assert fork is not None  # `_settled_base` refuses a base without one
    try:
        report = migrations_mod.check_diff_coverage(
            target_root, fork, include_working_tree=include_working_tree
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    migrations_mod.render_coverage_report(report)
    if not report.is_covered:
        raise SystemExit(1)


@main.group()
def permissions() -> None:
    """Inspect the permission model and reconcile it against live harness state (per COR-028).
    Read-only."""


@permissions.command("explain")
@click.argument("agent", required=False)
def permissions_explain(agent: str | None) -> None:
    """Render the per-agent permission mental model (grants, scopes, effects)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.explain(target_root, agent), nl=False)


@permissions.command("diff")
@click.argument("agent", required=False)
def permissions_diff(agent: str | None) -> None:
    """Reconcile the model against live `.claude/settings.json` — flags live rules no granted
    privilege justifies, and dimensions the harness can't enforce."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    report, _clean = perm.diff(target_root, agent)
    click.echo(report, nl=False)


@permissions.command("catalog")
def permissions_catalog() -> None:
    """List the privilege catalog (baseline + extensions)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.catalog(target_root), nl=False)


@permissions.command("overview")
def permissions_overview() -> None:
    """Role-grouped catalog overview: guardrails (deny by default) vs enablers (grant to enable),
    with provenance and who each is granted to."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.overview(target_root), nl=False)


@permissions.command("grant")
@click.argument("subject")
@click.argument("privilege")
@click.option(
    "--scope",
    multiple=True,
    help="Directory glob constraining the grant (repeatable; only for scope-typed privileges).",
)
@click.option("--deny", is_flag=True, default=False, help="Record a deny grant (default: allow).")
def permissions_grant(subject: str, privilege: str, scope: tuple[str, ...], deny: bool) -> None:
    """Grant SUBJECT a PRIVILEGE (optionally scoped) — writes the model."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.grant(target_root, subject, privilege, scope, deny))
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("revoke")
@click.argument("subject")
@click.argument("privilege")
def permissions_revoke(subject: str, privilege: str) -> None:
    """Remove SUBJECT's grant of PRIVILEGE."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.revoke(target_root, subject, privilege))


@permissions.command("scaffold")
@click.argument("capability")
def permissions_scaffold(capability: str) -> None:
    """Stamp CAPABILITY's permissions/ fragment skeleton (privilege-catalog.yaml + grants.yaml).

    Standalone (not a `new capability` flag) so it serves existing
    capabilities too. Stamps the two kit-owned fragment files with the
    correct shapes and inline guidance on both authoring footguns: fragment
    keys are authored BARE (the loader applies the `<cap>:` scope), a grant
    references a fragment privilege with the SCOPED token
    `[privilege-catalog:<cap>:<name>]`, and `guardrail: true` is forbidden in
    a fragment (per ADR-016 + ADR-021). Refuses an unknown capability; refuses
    to clobber an existing fragment file.
    """
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        stamped = perm.scaffold_fragment(target_root, capability)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc
    if not stamped:
        click.echo(
            f"Nothing stamped: both fragment files already exist under "
            f".pkit/capabilities/{capability}/permissions/ (left untouched)."
        )
        return
    for path in stamped:
        click.echo(f"Stamped: {path.relative_to(target_root)}")
    click.echo(
        "Next: replace the illustrative entries with this capability's own "
        "privilege(s) and deny(ies) — keep fragment keys BARE and reference "
        f"them with the scoped token `[privilege-catalog:{capability}:<name>]`. "
        "`pkit schemas validate` lints the grant tokens."
    )


@permissions.command("mode")
@click.argument("mode", required=False, type=click.Choice(["additive", "managed"]))
def permissions_mode(mode: str | None) -> None:
    """Show (no arg) or set the ownership mode: additive | managed."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.show_mode(target_root) if mode is None else perm.set_mode(target_root, mode))


@permissions.command("enable")
def permissions_enable() -> None:
    """Turn on live enforcement: register the PreToolUse hook + ensure the native guardrail denies
    (the double-lock). Opt-in per issue #247."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.enable(target_root))
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("disable")
def permissions_disable() -> None:
    """Turn off live enforcement: strip the PreToolUse hook registration (native guardrail denies
    stay)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.disable(target_root))
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("apply")
def permissions_apply() -> None:
    """Additively realize the model into `.claude/settings.json` (union the projected allow rules +
    ensure guardrail denies) and report the out-of-harness gap. Additive + idempotent; managed-mode
    wholesale regeneration is separate."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.apply(target_root), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.group("setup", invoke_without_command=True)
@click.pass_context
def permissions_setup(ctx: click.Context) -> None:
    """Goal-oriented setup commands (per ADR-007): stand up a composite goal stepwise + resumably.
    No goal = list goals."""
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.setup_list(target_root), nl=False)


@permissions_setup.group("autonomy", invoke_without_command=True)
@click.option(
    "--profile",
    default="autonomous",
    show_default=True,
    help="The autonomy profile to activate as the goal's intent layer.",
)
@click.option(
    "--remove-overrides",
    is_flag=True,
    default=False,
    help="Auto-confirm removal of per-machine overlay attributes that override "
    "the posture (settings.local.json only; never the committed baseline). "
    "A deliberate trust gesture — NOT covered by any blanket --yes.",
)
@click.pass_context
def permissions_setup_autonomy(ctx: click.Context, profile: str, remove_overrides: bool) -> None:
    """Stand up autonomous agents: profile + enforcement + OS sandbox, then prove it.

    Resumable: re-run after the session restart to verify; finished steps are
    skipped. The goal is declared reached only when the probe proof passes.

    Detects per-machine overlay attributes (settings.local.json) that silently
    override the intended posture, warns loudly, and offers to remove them —
    consent-gated. Removal happens only on an interactive confirmation or with
    `--remove-overrides`; without consent the conflict is warned-about only."""
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")

    # The override-removal consent gate (#399): a dedicated trust gesture, never
    # covered by a blanket --yes. `--remove-overrides` auto-confirms; otherwise
    # prompt interactively. A declined OR non-interactive prompt means warn-only
    # (deny), not an aborted setup — an EOF/abort on the confirm is caught and
    # treated as "no" so a non-tty run still completes the posture, warning only.
    def _confirm_remove(msg: str) -> bool:
        if remove_overrides:
            return True
        try:
            return bool(click.confirm(msg))
        except click.Abort:
            return False

    confirm = _confirm_remove
    try:
        report, ok = perm.setup_autonomy(target_root, profile=profile, confirm=confirm)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report, nl=False)
    if not ok:
        raise SystemExit(1)


@permissions_setup_autonomy.command("down")
def permissions_setup_autonomy_down() -> None:
    """Tear the autonomy goal's live switches down (hook + sandbox), reporting residual state
    loudly."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.setup_autonomy_down(target_root), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("probe")
@click.option(
    "--subject",
    default="operator",
    show_default=True,
    help="Decide as this subject: `operator` or `agent:<name>`.",
)
@click.option(
    "--live",
    is_flag=True,
    default=False,
    help="Also execute reachability probes against the sandbox credential "
    "denyRead floor (open-attempt only; never reads content).",
)
def permissions_probe(subject: str, live: bool) -> None:
    """Probe-by-probe proof that the current model rejects/allows what it declares.

    Drives the live hook's entry point (hook_decide) over curated concrete requests
    and checks each verdict against the declared model; also checks the native
    double-lock denies. Read-only; non-zero exit if any probe is broken."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        report, ok = perm.probe(target_root, subject=subject, live=live)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report, nl=False)
    if not ok:
        raise SystemExit(1)


@permissions.group("diagnose", invoke_without_command=True)
@click.pass_context
def permissions_diagnose(ctx: click.Context) -> None:
    """Opt-in permission-prompt diagnostic loop (per PRJ-006): capture deferred (prompted)
    decisions, classify + rank them, and report remediations it RECOMMENDS. No subcommand =
    status."""
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.diagnose_status(target_root), nl=False)


@permissions_diagnose.command("on")
# Default mirrors permissions._DIAGNOSE_DEFAULT_TTL_SECONDS (8h); kept literal
# here so the option default is available at decorator-eval time without importing
# the module at CLI load. `diagnose_on` is the single source of truth at runtime.
@click.option(
    "--ttl",
    "ttl_seconds",
    default=8 * 60 * 60,
    show_default=True,
    type=int,
    help="Seconds before the diagnostic session auto-expires (it can't stay silently armed).",
)
@click.option(
    "--no-redact",
    "no_redact",
    is_flag=True,
    default=False,
    help="Log full commands instead of redacting the command tail "
    "(redaction is on by default — the tail carries paths/secrets).",
)
def permissions_diagnose_on(ttl_seconds: int, no_redact: bool) -> None:
    """Arm a bounded diagnostic session (TTL-expiring). While armed, the hook appends each deferred
    decision to a local, git-ignored, size-capped log."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(
            perm.diagnose_on(target_root, ttl_seconds=ttl_seconds, redact=not no_redact), nl=False
        )
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_diagnose.command("off")
def permissions_diagnose_off() -> None:
    """Disarm the diagnostic session (remove the armed marker); the captured log is left in
    place."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.diagnose_off(target_root), nl=False)


@permissions_diagnose.command("status")
def permissions_diagnose_status() -> None:
    """Show armed/expired state + captured log size. Read-only."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.diagnose_status(target_root), nl=False)


@permissions_diagnose.command("report")
def permissions_diagnose_report() -> None:
    """Print the classified, frequency-ranked, recommend-only report over the captured log. Applies
    nothing; reports COVERAGE, not a predicted prompt decrement."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.diagnose_report(target_root), nl=False)


@permissions.group("sandbox", invoke_without_command=True)
@click.pass_context
def permissions_sandbox(ctx: click.Context) -> None:
    """OS-sandbox confinement (per ADR-004): prompt-free scripting inside the box. No subcommand =
    status."""
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.sandbox_status(target_root), nl=False)


@permissions_sandbox.command("enable")
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Also lock the unsandboxed fail-over escape hatch "
    "(allowUnsandboxedCommands: false). Optional hardening; breaks "
    "legit fail-over like `git push` / `gh` — pair with excludedCommands.",
)
@click.option(
    "--dangerously-allow-unconfined",
    is_flag=True,
    default=False,
    help="Operator-only, per-invocation: write failIfUnavailable: false "
    "(fail-open). Never a committable default — re-running enable "
    "without it restores fail-closed.",
)
def permissions_sandbox_enable(strict: bool, dangerously_allow_unconfined: bool) -> None:
    """Turn on the OS sandbox with prompt-free scripting (fail-closed, additive, idempotent)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(
            perm.sandbox_enable(
                target_root,
                strict=strict,
                dangerously_allow_unconfined=dangerously_allow_unconfined,
            ),
            nl=False,
        )
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.command("disable")
def permissions_sandbox_disable() -> None:
    """Turn the OS sandbox off (enabled: false); operator sandbox keys survive."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.sandbox_disable(target_root), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.group("toolkit")
def permissions_sandbox_toolkit() -> None:
    """Confinement toolkits (per ADR-008): per-tool sandbox allowances, classified
    narrowing/widening."""


@permissions_sandbox_toolkit.command("list")
def permissions_sandbox_toolkit_list() -> None:
    """List available confinement toolkits, marked by boundary effect + which are accommodated."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.confinement_list(target_root), nl=False)


@permissions_sandbox_toolkit.command("show")
@click.argument("name")
def permissions_sandbox_toolkit_show(name: str) -> None:
    """Show a toolkit's exact allowances, each marked narrowing or widening."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.confinement_show(target_root, name), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.command("accommodate")
@click.argument("tools", nargs=-1)
@click.option(
    "--detect",
    is_flag=True,
    default=False,
    help="Also scan the project for known tools (lockfiles/manifests) and accommodate them.",
)
@click.option(
    "--socket",
    "socket_path",
    default=None,
    help='Allow a one-off unix socket by path (e.g. --socket "$SSH_AUTH_SOCK") — '
    "narrowing, per-machine, never committed (per ADR-010). Use --name to label it.",
)
@click.option(
    "--name",
    default="manual",
    show_default=True,
    help="Logical name for a --socket allowance (its recompute-replace key).",
)
@click.option(
    "--remove",
    is_flag=True,
    default=False,
    help="Remove the named toolkits' (or the --socket --name) pkit-authored entries (operator "
    "entries untouched).",
)
def permissions_sandbox_accommodate(
    tools: tuple[str, ...], detect: bool, socket_path: str | None, name: str, remove: bool
) -> None:
    """Apply NARROWING allowances so legit tooling works inside the box.

    Toolkits (build caches, sockets) are recorded in permission-config and auto-applied
    by `setup autonomy`. `--socket <path>` is a one-off per-machine socket allowance
    (never committed) — for the SSH agent / signing sockets. For carving a command OUT
    of the box, use `sandbox exclude` (explicit, loud)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        if socket_path is not None or (remove and not tools and name != "manual"):
            click.echo(
                perm.accommodate_socket(target_root, socket_path or "", name=name, remove=remove),
                nl=False,
            )
        else:
            click.echo(perm.accommodate(target_root, tools, detect=detect, remove=remove), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.command("exclude")
@click.argument("command", required=False)
@click.option(
    "--weaker-tls",
    is_flag=True,
    default=False,
    help="Instead of excluding a command, weaken network TLS isolation (widening).",
)
@click.option(
    "--remove",
    is_flag=True,
    default=False,
    help="Put the command back inside the box (remove the exclusion).",
)
def permissions_sandbox_exclude(command: str | None, weaker_tls: bool, remove: bool) -> None:
    """WIDENING gesture: carve a command OUT of the box so it runs UNCONFINED.

    Loud, per-invocation, NEVER written to committed config, never proposed by detect,
    never applied by setup (per ADR-008). Reported by `sandbox status` and `probe`."""
    from project_kit import permissions as perm

    if not command and not weaker_tls:
        raise click.ClickException("give a COMMAND to exclude, or --weaker-tls.")
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(
            perm.sandbox_exclude(target_root, command or "", remove=remove, weaker_tls=weaker_tls),
            nl=False,
        )
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.group("profile")
def permissions_profile() -> None:
    """Named autonomy profiles (per ADR-005): a posture + a layered grant-set you select per
    project."""


@permissions_profile.command("list")
def permissions_profile_list() -> None:
    """List available profiles (shipped + project), marking the active one."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.list_profiles(target_root), nl=False)


@permissions_profile.command("show")
@click.argument("name")
def permissions_profile_show(name: str) -> None:
    """Show a profile's posture + layered grants."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.show_profile(target_root, name), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_profile.command("activate")
@click.argument("name")
@click.option(
    "--no-apply",
    is_flag=True,
    default=False,
    help="Set the model only; don't realize to settings (run `apply` yourself later).",
)
def permissions_profile_activate(name: str, no_apply: bool) -> None:
    """Activate a profile: set posture + layer its grants, then `apply` (unless --no-apply). Does
    not enable the hook."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.activate_profile(target_root, name, apply_after=not no_apply), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@main.group()
def decisions() -> None:
    """Decision-record integrity checks across every id-space (core, project, ADR, per-capability
    DEC, rules)."""


@decisions.command("validate")
def decisions_validate() -> None:
    """Detect duplicate decision ids within an id-space (per Feature #162).

    Scans every decision record — `COR-NNN` under `.pkit/decisions/core/`,
    `PRJ-NNN` under `.pkit/decisions/project/`, `ADR-NNN` at the
    overlay-resolved `<adr-records>` path, and per-capability `DEC-NNN`
    under `.pkit/capabilities/<cap>/decisions/` — and fails if two records
    claim the same id within the same id-space. Numbering is independent
    per id-space, so the same `DEC-001` in two different capabilities is
    not a collision.

    Also sanity-checks that each record's frontmatter id matches its
    filename number, and that no rule id (`RS-<SET>-NNN`, COR-051) is
    claimed twice across the rule sets. Exits non-zero on any duplicate or
    mismatch.

    Then warns, without failing, of every line where a record narrates its
    own revision — an amendment heading or marker, a revision stamped with an
    issue number or a date, change-log phrasing — since a record is refined in
    place and git history is its change log. Superseded records and records
    that arrive as synced copies are not read.
    """
    from project_kit import decisions_validate as decisions_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    report = decisions_mod.validate_decision_ids(target_root)
    decisions_mod.print_report(report)
    decisions_mod.print_narration(decisions_mod.revision_narration(target_root))
    if not report.is_clean:
        raise click.ClickException(f"{len(report.issues)} decision-id issue(s) found.")


@main.group()
def schemas() -> None:
    """Validate capability YAML schemas against their JSON Schema companions (per COR-018 + the
    .pkit/schemas/ area)."""


@schemas.command("validate")
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--shape-only",
    is_flag=True,
    default=False,
    help="Skip the cross-file reference-resolution pass; check shape only. "
    "Useful mid-refactor when a referenced target schema doesn't exist yet.",
)
def schemas_validate(path: Path | None, shape_only: bool) -> None:
    """Validate YAML schemas against their JSON Schema companions + resolve references.

    Default (no PATH): walks the core schemas area (`.pkit/schemas/`) and
    every installed capability's `schemas/` directory under the current
    project, validates each YAML against its sibling `<name>.schema.json`,
    and reports findings.

    With PATH: validates the YAML schemas at the given file or
    directory. Useful for adopters running the validator against
    non-capability data files that follow the same conventions.

    Two passes run by default:
    - **Shape** — does the YAML satisfy the JSON Schema (per COR-018)?
    - **References** — does every `[<namespace>:<id>]` token in the YAML
      resolve to a real id in the named namespace (per COR-019)?

    With `--shape-only`, only the shape pass runs. Targets must declare
    where their ids live via an `x-pkit-id-collection` annotation in the
    JSON Schema companion (a JSON Pointer into the data YAML).
    """
    from project_kit import schemas_validate as schemas_mod

    resolve = not shape_only
    if path is not None:
        report = schemas_mod.validate_path(path, target_root=find_target_root(), resolve=resolve)
    else:
        target_root = find_target_root()
        if target_root is None:
            raise click.ClickException("not in a project tree.")
        report = schemas_mod.validate_all(target_root, resolve=resolve)

    schemas_mod.print_report(report)
    if not report.is_clean:
        raise click.ClickException(f"{len(report.issues)} schema validation issue(s) found.")


@schemas.command("list")
def schemas_list() -> None:
    """List every schema in the core area and installed capabilities, grouped by owner.

    For each schema, shows whether it owns a namespace (companion declares
    `x-pkit-id-collection`) and, if so, how many entries the namespace
    holds plus a preview of the ids. Consumer schemas (no own namespace)
    are marked.
    """
    from project_kit import schemas_validate as schemas_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    summaries = schemas_mod.summarize_schemas(target_root)
    schemas_mod.print_schema_list(summaries)


@schemas.command("show")
@click.argument("namespace")
def schemas_show(namespace: str) -> None:
    """Show one namespace's entries with one-line summaries.

    NAMESPACE matches the schema's filename stem (e.g., `issue-types`,
    `validation-severity`). Errors cleanly when the namespace is unknown
    or ambiguous (declared by multiple owners).
    """
    from project_kit import schemas_validate as schemas_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    detail = schemas_mod.detail_namespace(target_root, namespace)
    if isinstance(detail, str):
        raise click.ClickException(detail)
    schemas_mod.print_namespace_detail(detail, target_root=target_root)


@schemas.command("add")
@click.argument("namespace")
@click.argument("entry_id")
@click.option(
    "--from",
    "from_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to a YAML or JSON file with the new entry's data. Pass `-` "
    "or omit to read from stdin.",
)
def schemas_add(namespace: str, entry_id: str, from_path: Path | None) -> None:
    """Add a new entry to an existing namespace's id collection.

    NAMESPACE is the schema's filename stem; ENTRY_ID is the new entry's
    kebab-case id. Entry fields come from `--from <path>` (YAML or JSON)
    or stdin. The companion JSON Schema's per-entry shape governs which
    fields are required; the command re-validates after the write and
    restores the prior file if validation fails.

    Refuses if the entry id is already in use (use a different id, or
    edit the existing entry directly).
    """
    from project_kit import schemas_authoring as authoring

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    source: Path | None = None
    if from_path is not None and str(from_path) != "-":
        if not from_path.is_file():
            raise click.ClickException(f"file not found: {from_path}")
        source = from_path
    try:
        entry_data = authoring.load_entry_data(source)
        yaml_path = authoring.add_entry_to_namespace(target_root, namespace, entry_id, entry_data)
    except authoring.SchemaAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        f"Added entry {entry_id!r} to namespace {namespace!r} at "
        f"{yaml_path.relative_to(target_root)}."
    )


@schemas.command("rename")
@click.argument("namespace")
@click.argument("old_id")
@click.argument("new_id")
def schemas_rename(namespace: str, old_id: str, new_id: str) -> None:
    """Rename an entry id across the schemas mechanism.

    Updates three reference classes in one atomic operation:

    \b
    1. The namespace owner's collection (mapping key or list item id).
    2. Every value-position typed token `[<namespace>:<old_id>]` in
       any YAML under the core schemas area or installed capabilities.
    3. Every mapping-key reference in fields whose companion declares
       `x-pkit-keys-from-namespace: <namespace>`.

    All affected files are validated after the rewrite; on any failure,
    every file is restored to its prior state and the issues are
    surfaced.
    """
    from project_kit import schemas_authoring as authoring

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        result = authoring.rename_entry(target_root, namespace, old_id, new_id)
    except authoring.SchemaAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"Renamed {old_id!r} → {new_id!r} in namespace {namespace!r} "
        f"({len(result.changes)} change(s)):"
    )
    for change in result.changes:
        click.echo(f"  [{change.kind}] {change.yaml_path.relative_to(target_root)}")
        click.echo(f"    {change.detail}")


@schemas.command("resolve")
@click.argument("token")
def schemas_resolve(token: str) -> None:
    """Resolve a typed token (`[<namespace>:<id>]`) to its target entry.

    Useful when you encounter a token in someone else's schema or output
    and want to see what it points at. Errors cleanly when the token's
    shape is malformed, the namespace isn't installed, or the id isn't
    in the namespace's collection.
    """
    from project_kit import schemas_validate as schemas_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    resolution = schemas_mod.resolve_token_to_target(target_root, token)
    if isinstance(resolution, str):
        raise click.ClickException(resolution)
    schemas_mod.print_token_resolution(resolution, target_root=target_root)


@main.group()
def data() -> None:
    """Validate adopter data files against capability schemas (per COR-022)."""


@data.command("validate")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--shape-only",
    is_flag=True,
    default=False,
    help="Skip cross-file reference resolution; validate shape only (per COR-029).",
)
def data_validate(path: Path, shape_only: bool) -> None:
    """Validate adopter data files against their bound capability schemas.

    The binding from a data file to a schema resolves in two steps
    (per COR-023):

    \b
    1. **Field-first.** A top-level `pkit_schema: <capability>:<schema>`
       field in the data file is authoritative.
    2. **Capability fallback.** Otherwise, the resolver walks every
       installed capability's schema `binds_to:` globs and uses the first
       matching one.

    If neither yields a binding, the file is reported as unresolved.
    A schema-version mismatch between the data file's `schema_version`
    and the capability schema's `schema_version` is refused with a
    migration hint; auto-migration is out of scope in v1.

    By default a second pass resolves cross-file typed references (per
    COR-029): a `[<namespace>:<id>]` token at a field the schema marks
    `x-pkit-reference-namespace` must name an id defined by some in-scope
    file bound to that namespace. The validation scope is exactly PATH —
    the id pool is the union of in-scope bound files. A dangling or
    duplicate id is an error; a reference whose namespace has no bound file
    in scope is a warning (a normal in-progress state). `--shape-only`
    skips this pass.

    PATH is a file or directory. Directories are walked recursively for
    `*.yaml` files (`.pkit/` subtrees are excluded — those are kit-managed,
    not adopter data).
    """
    from project_kit import data_validate as data_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    report = data_mod.validate_path(path, target_root, resolve_references=not shape_only)
    data_mod.print_report(report)
    if report.has_errors:
        raise click.ClickException(f"{len(report.errors)} data-validation error(s) found.")


@main.group()
def settings() -> None:
    """Manage `.claude/settings.json` (per COR-002)."""


@settings.command("consolidate")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be removed without writing.",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt and write directly.",
)
def settings_consolidate(dry_run: bool, yes: bool) -> None:
    """Remove redundant entries from `.claude/settings.json` + `.claude/settings.local.json`.

    An entry is redundant when a broader rule in the union of both
    files already covers it — e.g., `Bash(pkit new *)` is redundant
    when `Bash(pkit:*)` is present (in either file). The merge
    primitive doesn't auto-clean these on sync (it only adds, per
    COR-001's preserve-adopter-content stance); this command is the
    explicit cleanup pass.

    Walks both `.claude/settings.json` (committed) and
    `.claude/settings.local.json` (gitignored, per-machine). A redundant
    entry is removed from whichever file(s) contain it.

    Default: print the plan grouped by file, prompt for confirmation,
    then write.
    --dry-run: print only.
    --yes:     skip confirmation.
    """
    from project_kit import settings_consolidate as consolidator

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    plan = consolidator.detect_consolidation_opportunities(target_root)
    if plan is None:
        click.echo("  no .claude/settings.json or .claude/settings.local.json at this project.")
        return
    if not plan.has_redundancies:
        click.echo("  no redundant entries across .claude/settings.json + settings.local.json.")
        return

    files = plan.files_to_modify
    click.echo(
        "  "
        + cli_render.style(
            "strong", f"Found {len(plan.pairs)} redundant entry(ies) across {len(files)} file(s):"
        )
        + "\n"
    )
    for source_file in files:
        rel = source_file.relative_to(target_root)
        file_pairs = plan.pairs_in(source_file)
        click.echo("  " + cli_render.style("heading", f"{rel} ({len(file_pairs)}):"))
        for pair in file_pairs:
            click.echo(f"    {pair.redundant!r}")
            click.echo(f"      subsumed by  {pair.subsumed_by!r}")
        click.echo()

    if dry_run:
        click.echo("  (dry-run — no changes written)")
        return

    if not yes:
        file_list = ", ".join(str(f.relative_to(target_root)) for f in files)
        confirmed = click.confirm(f"  Remove these entries from {file_list}?", default=False)
        if not confirmed:
            click.echo("  cancelled.")
            return

    modified = consolidator.apply_consolidation(target_root, plan)
    rels = ", ".join(str(f.relative_to(target_root)) for f in modified)
    click.echo(
        "  " + cli_render.style("strong", f"Removed {len(plan.pairs)} entry(ies) from {rels}.")
    )


# --- Capability commands (per COR-017) ------------------------------------


@capabilities.command("show")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print the machine form.")
def show_capability_cmd(name: str, as_json: bool) -> None:
    """Show a capability's connections, installed or not (COR-053 point 8).

    Read from its package metadata alone: the roles it provides, the points it
    accepts and offers, its extensions (contributes, subscribes, depends-on),
    and what would connect here — the live wiring for an installed capability,
    the wiring this project would have with it installed otherwise. Found in the
    local catalogue only: the installed tree, capabilities authored in this
    repository, the capabilities that ship with this pkit. Writes nothing.
    """
    from project_kit import capability_plans as plans

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")
    candidate = plans.find_candidate(target_root, find_source_kit(), name)
    if candidate is None:
        raise click.ClickException(
            f"no capability named {name!r} is installed, authored in this repository, or "
            f"ships with this pkit. Try `pkit capabilities list`."
        )
    view = plans.show(target_root, candidate)
    click.echo(plans.to_json(view) if as_json else plans.render_show(view), nl=False)


def _plan_flags(plan: bool, as_json: bool) -> None:
    """`--json` is the machine form of a plan; alone it asks for nothing."""
    if as_json and not plan:
        raise click.UsageError("--json prints the plan: pass it with --plan.")


@capabilities.command("install")
@click.argument("name")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be installed without writing files.",
)
@click.option(
    "--plan",
    is_flag=True,
    default=False,
    help="Show the connections the install would make, the role conflicts to resolve and "
    "what the capability needs, computed by the wiring resolver; writes nothing (COR-053 "
    "point 8).",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="With --plan: the machine form."
)
def install_capability_cmd(name: str, dry_run: bool, plan: bool, as_json: bool) -> None:
    """Install a capability: copy subtree into adopter, register in manifest, re-deploy."""
    from project_kit import capabilities as caps

    _plan_flags(plan, as_json)

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    source_kit = find_source_kit()
    # The methodology's source repository run by code that is not its own (the
    # gap, ADR-059): the install would copy the running code's capability
    # subtree into the tree it is built from. Refuse before anything else —
    # the plan included, since the install it previews would refuse (#1090).
    refuse_propagation_into_source(
        target_root,
        source_kit,
        command=f"capabilities install {name}",
        would="copy the capability's subtree from that tree into the one it is built from",
        own_code_does=None,
    )

    # A reserved name is refused before lookup, so the refusal names the
    # reservation rather than reporting the capability as missing.
    caps.refuse_reserved_capability_name(name)

    capability_source = caps.find_capability_in_source(source_kit, name)
    if capability_source is None:
        raise click.ClickException(
            f"no capability named {name!r} ships in this kit version. "
            f"Try `pkit capabilities list` to see what's available."
        )

    # Pre-flight: already installed?
    if caps.is_installed(target_root, name):
        raise click.ClickException(
            f"capability {name!r} is already installed. "
            f"Use `pkit capabilities upgrade {name}` to refresh."
        )

    if plan:
        # The plan runs before the gates: what the gates refuse on — the backbone
        # and dependency ranges — is among what the plan reports it needs.
        from project_kit import capability_plans as plans

        candidate = plans.candidate_of(capability_source, caps.KIT_SHIPPED, installed=False)
        if candidate is None:
            raise click.ClickException(f"capability {name!r}'s package.yaml does not read.")
        install_plan = plans.plan_install(target_root, candidate)
        click.echo(
            plans.to_json(install_plan) if as_json else plans.render_install_plan(install_plan),
            nl=False,
        )
        return

    # Pre-flight: backbone-version satisfaction. Shared with `register` via
    # `_check_backbone_satisfied` (COR-007 pattern-extraction): both capability-
    # entry paths refuse when the project's backbone is outside the capability's
    # requires_backbone range, so neither path can activate a capability the
    # backbone cannot support.
    _check_backbone_satisfied(target_root, capability_source)

    # Pre-flight: capability dependency check (COR-030).
    # Refuse if any declared dependency is absent or its installed version
    # is outside the required range. Never auto-installs.
    dep_conflicts = caps.check_capability_dependencies(
        target_root, capability_source.package.requires_capabilities
    )
    if dep_conflicts:
        lines = []
        for conflict in dep_conflicts:
            if conflict.reason == "absent":
                lines.append(
                    f"    - '{conflict.dep_name}' ({conflict.dep_version_range}) is not installed"
                )
            else:
                lines.append(
                    f"    - '{conflict.dep_name}' {conflict.dep_version_range} "
                    f"required but v{conflict.installed_version} is installed"
                )
        raise click.ClickException(
            f"capability {name!r} v{capability_source.package.version} has "
            f"unsatisfied dependencies:\n" + "\n".join(lines) + "\n"
            "Install or upgrade the required capabilities first."
        )

    # Pre-flight: mandatory process connections (COR-053 point 6). Refuse when an
    # upstream the capability marks mandatory is missing or incompatible.
    _refuse_unmet_mandatory_upstreams(target_root, capability_source)

    # The methodology's source run by its own code (ADR-059 point 2): the tree the
    # capability would be copied from is its destination. Register it in place —
    # a copy would put the tree onto itself (#1107).
    if caps.authored_in_source(target_root, source_kit, name):
        _install_capability_in_source(target_root, source_kit, capability_source, dry_run=dry_run)
        return

    # Pre-flight: collision detection.
    collisions = caps.detect_collisions(target_root, capability_source)
    skipped: list[tuple[str, str]] = []

    if collisions:
        click.echo(
            "\n  "
            + cli_render.style("strong", f"{len(collisions)} naming collision(s) detected:")
            + "\n"
        )
        for finding in collisions:
            choice = _resolve_collision_interactive(target_root, finding, dry_run=dry_run)
            if choice == "skip":
                skipped.append((finding.artifact_kind, finding.artifact_name))

    # Install.
    installed_path = caps.install_capability(
        target_root,
        capability_source,
        skipped_artifacts=tuple(skipped),
        dry_run=dry_run,
    )

    verb = "Would install" if dry_run else "Installed"
    skip_note = f" ({len(skipped)} artifact(s) skipped)" if skipped else ""
    click.echo(
        "\n  "
        + cli_render.style(
            "strong",
            f"{verb} capability {name!r} v{capability_source.package.version} "
            f"at {installed_path.relative_to(target_root)}/{skip_note}",
        )
    )

    if not dry_run:
        # Re-run installed adapter primitives so the harness picks up
        # the capability's newly-copied skills and agents (e.g.,
        # deploy-skills.sh symlinks them into .claude/skills/).
        # Mirrors what `pkit capabilities upgrade` does after refresh and
        # what `pkit init` does after its first-time copy. Then provision the
        # capability's query commands, so an offline `pkit validate` answers
        # without a `pkit sync` first (#1090).
        _deploy_capability(target_root, source_kit, name)


def _install_capability_in_source(
    target_root: Path,
    source_kit: Path,
    capability_source: CapabilitySource,
    *,
    dry_run: bool,
) -> None:
    """Install a capability whose subtree is its source: register it, copy nothing (#1107).

    In the methodology's source repository run by its own code
    (`caps.authored_in_source`), the capability `install` finds in the tree the
    running code resolves is the one at its destination. It is registered in
    place with origin `kit-shipped` (`caps.register_capability_in_source`) and
    deployed like any install. Its own skills and agents are no collision
    against themselves, so only a collision with *other* content is looked for,
    as `register` does; and since nothing is copied there is nothing to skip, so
    one is refused rather than resolved.
    """
    from project_kit import capabilities as caps

    name = capability_source.name
    _refuse_collisions_in_place(target_root, capability_source)
    registered_path = caps.register_capability_in_source(
        target_root, capability_source, dry_run=dry_run
    )

    verb, copied = ("Would register", "would be") if dry_run else ("Registered", "was")
    click.echo(
        "\n  "
        + cli_render.style(
            "strong",
            f"{verb} capability {name!r} v{capability_source.package.version} in place at "
            f"{registered_path.relative_to(target_root)}/: it is authored in this "
            f"repository, the methodology's source, so nothing {copied} copied (ADR-059).",
        )
    )

    if not dry_run:
        _deploy_capability(target_root, source_kit, name)


def _refuse_collisions_in_place(target_root: Path, capability_source: CapabilitySource) -> None:
    """Refuse a capability registered in place whose artefacts collide with other content.

    `register` (an incubated capability) and `install` of a capability authored in
    the methodology's source both register a subtree that is already in place:
    its own artefacts are not collisions against themselves
    (`caps.detect_incubated_collisions` filters them), and with nothing copied
    there is no skip to offer — the author renames the artefact instead.
    """
    from project_kit import capabilities as caps

    collisions = caps.detect_incubated_collisions(target_root, capability_source)
    if not collisions:
        return
    click.echo(
        "\n  "
        + cli_render.style(
            "strong", f"{len(collisions)} naming collision(s) with already-installed content:"
        )
        + "\n"
    )
    for finding in collisions:
        click.echo(
            f"    - {finding.artifact_kind} '{finding.artifact_name}' "
            f"collides with {finding.target_path.relative_to(target_root)}"
        )
    raise click.ClickException(
        "rename the colliding artifact(s) in your capability tree, then retry."
    )


@capabilities.command("register")
@click.argument("name")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be registered without writing files.",
)
def register_capability_cmd(name: str, dry_run: bool) -> None:
    """Register + activate a capability authored in this repo (per COR-031).

    The capstone of capability incubation: a capability the adopter wrote
    in its own `.pkit/capabilities/<name>/` is registered *in place* (no
    copy — source and destination are the same directory) and activated
    exactly like a kit-shipped install: its skills/agents deploy and it
    participates in dependency gating. Origin `incubated-in-repo` is
    recorded in install-state so `pkit sync` leaves it untouched.

    Distinct from `install`, which copies a capability *from kit source*
    into the adopter. `register` skips the "exists in kit source" pre-flight
    (the in-repo tree is the source) but keeps the pre-flights that still
    apply: backbone-version satisfaction, naming-collision detection, and
    the capability-dependency check (COR-030).

    Idempotent on an already-registered capability, branching on origin
    (COR-031 D2): if it is already `incubated-in-repo`, this is a clean no-op;
    if it is `kit-shipped` (including the origin-unset default a manual
    registration leaves behind), it is *adopted in place* — the applicable
    pre-flights re-run and the origin is set to `incubated-in-repo` on the
    existing registry entry (no re-copy, no re-deploy), so `pkit sync` stops
    reconciling it against kit source.
    """
    from project_kit import capabilities as caps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    source_kit = find_source_kit()
    # The methodology's source repository run by code that is not its own (the
    # gap, ADR-059): registering writes install-state with that code. Refuse
    # before anything else, as `install` does (#1090).
    refuse_propagation_into_source(
        target_root,
        source_kit,
        command=f"capabilities register {name}",
        would="register the capability with that code, writing install-state into the tree "
        "it is built from",
        own_code_does=None,
    )

    # A reserved name is refused before resolution, as in `install`.
    caps.refuse_reserved_capability_name(name)

    # Resolve the capability, preferring the in-repo (incubated) source.
    # Consulting both trees lets us surface the COR-031 boundary case where
    # a same-named capability now also ships from kit source — graduation
    # arriving unbidden — rather than silently shadowing it.
    resolved = caps.resolve_capability_source(
        name,
        source_kit=source_kit,
        target_root=target_root,
        prefer=caps.INCUBATED_IN_REPO,
    )
    if resolved is None or not resolved.in_repo:
        raise click.ClickException(
            f"no capability named {name!r} is authored in this repo at "
            f".pkit/capabilities/{name}/. To install a kit-shipped capability, "
            f"use `pkit capabilities install {name}`."
        )
    capability_source = resolved.source

    # Pre-flight: already registered? Branch on origin (COR-031 D2). A capability
    # added via the old manual workaround is registered with origin unset, which
    # reads back as kit-shipped — and `upgrade` refreshes from source without ever
    # setting `incubated-in-repo`, so there is no other path to protect it from
    # sync. Adopt it in place here; a genuinely incubated one is a clean no-op.
    already_registered = caps.is_installed(target_root, name)
    adopt_in_place = False
    if already_registered:
        current_origin = caps.read_capability_origin(target_root, name)
        if current_origin == caps.INCUBATED_IN_REPO:
            click.echo(
                "\n  "
                + cli_render.style(
                    "strong",
                    f"capability {name!r} is already registered as "
                    f"incubated-in-repo; nothing to do.",
                )
            )
            return
        # kit-shipped / unset → adopt in place: run the applicable pre-flights
        # below, then set origin on the existing entry (no re-copy, no re-deploy —
        # the subtree is already installed; this is an origin-state upgrade).
        adopt_in_place = True

    # COR-031 boundary: a same-named capability now also ships from kit
    # source (graduation, before graduation is specified). Surface it so the
    # adopter can decide, rather than silently registering the in-repo copy.
    # In the methodology's source repository the in-repo subtree *is* the kit
    # source (#1107), so there is no second copy to name.
    if resolved.in_kit_source and not caps.authored_in_source(target_root, source_kit, name):
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"Note: a capability named {name!r} also ships from kit source. "
                f"Registering the in-repo (incubated) copy; the kit-shipped one "
                f"is not installed.",
            )
        )

    # Pre-flight: self-consistency validation (COR-031 D1). The adopter
    # hand-authored this capability; nothing upstream validated it. Check its
    # own manifest/schemas/layout against the working tree before activating —
    # origin suppresses source-reconciliation, never self-validation.
    self_problems = caps.validate_capability_self_consistency(capability_source)
    if self_problems:
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"capability {name!r} is structurally invalid ({len(self_problems)} problem(s)):",
            )
            + "\n"
        )
        for problem in self_problems:
            click.echo(f"    - {problem}")
        raise click.ClickException(
            "fix the structural problems in your capability tree, then retry."
        )

    # Pre-flight: backbone-version satisfaction. The incubated capability
    # declares a requires_backbone range; refuse if this project's backbone
    # falls outside it (the shared gate also run by `install`, per
    # `_check_backbone_satisfied`).
    _check_backbone_satisfied(target_root, capability_source)

    # Pre-flight: capability dependency check (COR-030). Identical to the
    # kit-source install path — origin does not gate dependency edges.
    dep_conflicts = caps.check_capability_dependencies(
        target_root, capability_source.package.requires_capabilities
    )
    if dep_conflicts:
        lines = []
        for conflict in dep_conflicts:
            if conflict.reason == "absent":
                lines.append(
                    f"    - '{conflict.dep_name}' ({conflict.dep_version_range}) is not installed"
                )
            else:
                lines.append(
                    f"    - '{conflict.dep_name}' {conflict.dep_version_range} "
                    f"required but v{conflict.installed_version} is installed"
                )
        raise click.ClickException(
            f"capability {name!r} v{capability_source.package.version} has "
            f"unsatisfied dependencies:\n" + "\n".join(lines) + "\n"
            "Install or upgrade the required capabilities first."
        )

    # Pre-flight: mandatory process connections (COR-053 point 6), as install.
    _refuse_unmet_mandatory_upstreams(target_root, capability_source)

    if adopt_in_place:
        # Adopt in place: the capability is already registered and its subtree
        # already installed, so we do not re-copy or re-deploy — the only change
        # is the origin field on the existing registry entry (COR-031 D2). Skip
        # collision detection (the subtree's artifacts are already the installed
        # content and would self-collide); the applicable pre-flights above have
        # run. `--dry-run` shows the change and writes nothing.
        verb = "Would adopt" if dry_run else "Adopted"
        if not dry_run:
            caps.set_capability_origin(target_root, name, caps.INCUBATED_IN_REPO)
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"{verb} {name!r} v{capability_source.package.version} as "
                f"incubated-in-repo (was {current_origin}); pkit sync will now "
                f"leave it untouched.",
            )
        )
        return

    # Pre-flight: collision detection. The capability's own skills/agents
    # already live in its in-repo tree, so detect_collisions surfaces them
    # as self-collisions; filter those out (same shape as the upgrade path,
    # which excludes the capability's own installed tree). What remains is a
    # genuine collision against *other* installed content — refuse on it,
    # since register has no interactive skip path (the adopter authored the
    # tree and would rename the artifact rather than skip-copy it).
    _refuse_collisions_in_place(target_root, capability_source)

    # Register in place (no copy) + record origin incubated-in-repo.
    registered_path = caps.register_incubated_capability(
        target_root, capability_source, dry_run=dry_run
    )

    verb = "Would register" if dry_run else "Registered"
    click.echo(
        "\n  "
        + cli_render.style(
            "strong",
            f"{verb} incubated capability {name!r} v{capability_source.package.version} "
            f"(in-repo) at {registered_path.relative_to(target_root)}/",
        )
    )

    if not dry_run:
        # Run the SAME deploy primitives a kit-source install runs, so the
        # capability's skills/agents land in the harness (COR-031 D1: deploy
        # is identical regardless of origin) — its query-command provisioning
        # included (#1090).
        _deploy_capability(target_root, source_kit, name)


def _upgrade_incubated_capability(
    target_root: Path, source_kit: Path, name: str, *, dry_run: bool
) -> None:
    """Re-apply deploy for an incubated (in-repo) capability — never reconcile against kit source.

    For an incubated capability the working tree *is* the source (COR-031
    D1/D4): there is nothing to refresh from kit source, so "upgrade" simply
    re-runs the harness deploy primitives so any newly-authored skills/agents
    in the in-repo tree land in the harness. This mirrors the sync skip-branch
    (`sync._report_incubated_capability`): source-reconciliation stays
    suppressed; only self-owned deploy re-runs.

    The capability subtree must still be readable. If it has gone missing the
    install-state is stale, but we do not route to the kit-source orphan path
    (which would suggest the destructive uninstall) — we report it plainly.
    """
    from project_kit import capabilities as caps

    source = caps.find_capability_in_repo(target_root, name)
    if source is None:
        raise click.ClickException(
            f"incubated capability {name!r} is registered but its in-repo "
            f"subtree at .pkit/capabilities/{name}/ is missing or unreadable. "
            "Restore the authored subtree, then retry — this is an in-repo "
            "capability, so there is no kit source to upgrade from."
        )

    verb = "Would re-deploy" if dry_run else "Re-deployed"
    click.echo(
        "\n  "
        + cli_render.style(
            "strong",
            f"{verb} incubated capability {name!r} v{source.package.version} "
            f"from its in-repo tree (no kit-source reconciliation — COR-031).",
        )
    )

    if not dry_run:
        _deploy_capability(target_root, source_kit, name)


def _upgrade_capability_in_source(
    target_root: Path, source_kit: Path, name: str, *, dry_run: bool
) -> None:
    """Re-deploy a capability whose subtree is its source — never copy it onto itself (#1107).

    In the methodology's source repository run by its own code
    (`caps.authored_in_source`), the tree `upgrade` would refresh a kit-shipped
    capability from is the capability's own subtree. The source is already the
    state, as sync's self-host path has it: nothing is copied, no receipt is
    restamped and no migration runs — migrations carry an adopter's copy
    forward, and this is no copy. What upgrade still refreshes is what follows
    the tree: the deploy primitives re-run and the capability's query commands
    are provisioned. The dependency and collision pre-flights are skipped with
    the copy, as for an incubated capability: nothing new arrives.
    """
    from project_kit import capabilities as caps

    source = caps.find_capability_in_source(source_kit, name)
    if source is None:
        raise click.ClickException(
            f"capability {name!r} is registered, but its source at "
            f".pkit/capabilities/{name}/ is missing or unreadable. Restore it — it is "
            "the capability's source in this repository, not a copy — then retry."
        )

    verb, copied = ("Would re-deploy", "would be") if dry_run else ("Re-deployed", "was")
    ran = "would run" if dry_run else "ran"
    click.echo(
        "\n  "
        + cli_render.style(
            "strong",
            f"{verb} capability {name!r} v{source.package.version} from its source at "
            f".pkit/capabilities/{name}/: it is authored in this repository, the "
            f"methodology's source, so nothing {copied} copied and no migration {ran} "
            "(ADR-059).",
        )
    )

    if not dry_run:
        _deploy_capability(target_root, source_kit, name)


def _deploy_capability(target_root: Path, source_kit: Path, name: str) -> None:
    """Deploy a capability just brought in or refreshed, and provision its query commands.

    The tail `install`, `register` and `upgrade` share: re-run the installed
    adapter primitives so the harness picks up the capability's skills and
    agents, then provision its query commands, so an offline `pkit validate`
    answers without a `pkit sync` first (#1090). Deploy is identical whatever
    the capability's origin (COR-031 D1).
    """
    from project_kit import install as install_mod

    ctx = install_mod.InstallContext(
        target_root=target_root,
        source_kit=source_kit,
        dry_run=False,
    )
    install_mod.run_installed_adapter_primitives(ctx)
    install_mod.provision_query_commands(ctx, component=name)


def _check_backbone_satisfied(target_root: Path, capability_source: CapabilitySource) -> None:
    """Refuse if the project's backbone version is outside the capability's required range.

    The shared backbone-satisfaction pre-flight for both capability-entry
    paths (COR-007 pattern-extraction): `install` (kit-source copy) and
    `register` (in-repo incubated) both call this, so a capability cannot be
    activated when this project's backbone falls outside its requires_backbone
    range. An empty/unparseable range is treated as "no constraint" (the
    capability declared nothing enforceable), matching how the dependency
    check tolerates malformed ranges rather than blocking. The range is
    compared through the wiring resolver's one relation
    (`connections.range_admits`), as `pkit validate` compares it.
    """
    from project_kit.connections import range_admits
    from project_kit.manifest import read_backbone_manifest

    required = capability_source.package.requires_backbone
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return
    if range_admits(required, backbone.backbone_version) is False:
        raise click.ClickException(
            f"capability {capability_source.name!r} requires backbone "
            f"{required}, but this project is on backbone v{backbone.backbone_version}. "
            "Upgrade the backbone (`pkit upgrade`) or relax the capability's "
            "requires_backbone, then retry."
        )


def _refuse_unmet_mandatory_upstreams(
    target_root: Path, capability_source: CapabilitySource
) -> None:
    """Refuse the capability carrying a mandatory process connection its upstream
    would not meet — missing, or at another interface version (COR-053 point 6).

    The carrier's side of COR-030's direction split, shared by `install`,
    `register` and `upgrade`: the operator chooses which version of the carrier to
    install, so there is no deadlock, and no `--force`. The mark is read from the
    capability's generated `depends-on` list, the reason shown as the mark gives it.
    """
    from project_kit import capabilities as caps

    unmet = caps.unmet_mandatory_upstreams(target_root, capability_source)
    if not unmet:
        return
    raise click.ClickException(
        f"capability {capability_source.name!r} v{capability_source.package.version} has "
        f"{len(unmet)} unmet mandatory process connection(s):\n"
        + "\n".join(_mandatory_line(u, carrier=False) for u in unmet)
        + "\nInstall or upgrade the upstream first, then retry (COR-053 point 6)."
    )


def _warn_mandatory_counterparts(
    target_root: Path,
    name: str,
    *,
    action: str,
    verb: str,
    force: bool,
    replacement: CapabilitySource | None = None,
) -> None:
    """Warn, naming each counterpart, when uninstalling `name` — or upgrading it to
    `replacement` — would leave another capability's mandatory process connection
    unmet; proceed only under `--force` (COR-053 point 6).

    The targeted side of COR-030's direction split: never a hard block, since a
    hard block could deadlock. `action` names the operation in the warning
    (`uninstalling 'x'`), `verb` in the refusal (`uninstall`).
    """
    from project_kit import capabilities as caps

    broken = caps.mandatory_counterparts_left_unmet(target_root, name, replacement=replacement)
    if not broken:
        return
    header = f"Warning (--force): {action} leaves" if force else f"Warning: {action} would leave"
    click.echo(
        "\n  "
        + cli_render.style(
            "strong", f"{header} {len(broken)} mandatory process connection(s) unmet:"
        )
    )
    for counterpart in broken:
        click.echo(_mandatory_line(counterpart, carrier=True))
    if not force:
        raise click.ClickException(
            f"refusing to {verb}: another capability's mandatory process connection "
            "would be left unmet.\nUninstall or upgrade the dependent capabilities first, "
            "or pass --force to proceed anyway (the deadlock-free override, COR-053 point 6)."
        )
    click.echo("  Proceeding under --force; the dependents' marks stay unmet until resolved.")


def _mandatory_line(unmet: MandatoryUpstream, *, carrier: bool) -> str:
    """One unmet mark: the upstream, why it is not met, and the mark's reason —
    prefixed by the capability carrying it when that is not the one operated on."""
    who = f"{unmet.capability!r} depends on " if carrier else ""
    return f"    - {who}{unmet.process!r}: {unmet.problem} (mandatory: {unmet.reason})"


def _find_desynced_dependents(
    target_root: Path, dep_name: str, new_dep_version: str
) -> list[tuple[str, str]]:
    """Find installed capabilities whose declared range for *dep_name* excludes *new_dep_version*.

    Used by the single-capability upgrade direction-2 check (COR-030): when
    upgrading a dependency capability, detect installed dependents that would
    become desynced by the new version.

    Returns a list of (dependent_name, declared_range_string) pairs.
    Uses installed versions of the dependent side — only the dependency's
    version is moving; per the architect note in COR-030 + issue #90. Each
    range is compared through the wiring resolver's one relation
    (`connections.range_admits`); a range or version it cannot read is no
    constraint.
    """
    from project_kit import capabilities as caps
    from project_kit.connections import range_admits

    declared_dependents = caps.find_declared_dependents(target_root, dep_name)
    desynced: list[tuple[str, str]] = []
    for dep_cap in declared_dependents:
        pkg_yaml_path = target_root / ".pkit" / "capabilities" / dep_cap / "package.yaml"
        if not pkg_yaml_path.is_file():
            continue
        pkg = caps._read_package_yaml(pkg_yaml_path)
        if pkg is None:
            continue
        for req in pkg.requires_capabilities:
            if req.name != dep_name:
                continue
            admitted = range_admits(req.version, new_dep_version)
            if admitted is None:
                continue
            if not admitted:
                desynced.append((dep_cap, req.version))
            break
    return desynced


def _resolve_collision_interactive(target_root, finding, *, dry_run: bool) -> str:
    """Prompt the adopter for override/skip/inspect on a single collision.

    Loops on `inspect` (re-prompts after showing diff) until adopter
    picks override or skip. Returns the final choice as a string.
    """

    while True:
        click.echo(
            f"  - {finding.artifact_kind} '{finding.artifact_name}' "
            f"collides with existing {finding.target_path.relative_to(target_root)}"
        )
        choice = click.prompt(
            "    [override / skip / inspect]",
            type=click.Choice(["override", "skip", "inspect"]),
            default="inspect",
            show_default=False,
        )
        if choice == "inspect":
            _show_unified_diff(finding.target_path, finding.source_path)
            continue
        return choice


def _show_unified_diff(existing: Path, incoming: Path) -> None:
    """Display a unified diff between the existing file and the incoming one."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--no-index", "--color=always", str(existing), str(incoming)],
            capture_output=True,
            text=True,
        )
        click.echo(result.stdout)
    except FileNotFoundError:
        # git not available — fall back to a plain difflib diff.
        import difflib

        existing_lines = existing.read_text().splitlines(keepends=True)
        incoming_lines = incoming.read_text().splitlines(keepends=True)
        diff = difflib.unified_diff(
            existing_lines,
            incoming_lines,
            fromfile=str(existing),
            tofile=str(incoming),
        )
        for line in diff:
            click.echo(line, nl=False)


@capabilities.command("uninstall")
@click.argument("name")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Override the safety checks; remove even if references exist, other "
    "installed capabilities declare a dependency on this one (COR-030), or a "
    "mandatory process connection would be left unmet (COR-053 point 6).",
)
@click.option(
    "--purge",
    is_flag=True,
    default=False,
    help="For an incubated (in-repo) capability, also delete its authored "
    "subtree from disk — not just unregister it. Requires confirmation. "
    "Default for an incubated capability is to keep your authored files "
    "(COR-031). No effect on a kit-shipped capability, which always deletes "
    "its disposable copy.",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompts (for non-interactive use): --purge's, and in "
    "the methodology's source repository the one before unregistering a capability "
    "whose subtree is its source.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be removed without deleting files.",
)
@click.option(
    "--plan",
    is_flag=True,
    default=False,
    help="Show the fillers lost, the processes and other counterparts left without a "
    "provider and the artefacts whose role blocks would be orphaned, computed by the "
    "wiring resolver; writes nothing (COR-053 point 8).",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="With --plan: the machine form."
)
def uninstall_capability_cmd(
    name: str, force: bool, purge: bool, yes: bool, dry_run: bool, plan: bool, as_json: bool
) -> None:
    """Uninstall a capability: unregister, drop stale symlinks, and delete the subtree per origin.

    Removal is origin-aware (COR-031 D4). A kit-shipped capability's subtree
    is a disposable copy of kit source, so it is deleted. An incubated
    (in-repo) capability's subtree is the adopter's only copy of authored
    work, so it is *unregistered in place* — the files stay on disk unless
    you pass --purge (which confirms first).

    In the methodology's source repository the subtree is the capability's
    source, never a copy, so nothing is deleted whatever the origin: uninstall
    says what it would have deleted, asks, and unregisters only; --purge is
    refused (ADR-059; #1107).
    """
    from project_kit import capabilities as caps

    _plan_flags(plan, as_json)
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")

    source_kit = find_source_kit()
    # The methodology's source repository run by code that is not its own (the
    # gap, ADR-059): the subtree is the capability's source, which that code
    # cannot tell from a copy. Refuse before anything else, the plan included,
    # as the verbs that write do (#1090, #1107).
    refuse_propagation_into_source(
        target_root,
        source_kit,
        command=f"capabilities uninstall {name}",
        would=(
            "unregister the capability with that code and, where it is registered "
            "kit-shipped, delete its subtree — here the capability's source, not a copy"
        ),
        own_code_does=None,
    )

    if not caps.is_installed(target_root, name):
        raise click.ClickException(f"capability {name!r} is not installed.")

    origin = caps.read_capability_origin(target_root, name)
    incubated = origin == caps.INCUBATED_IN_REPO
    # The methodology's source run by its own code (ADR-059 point 2): the subtree
    # is the capability's source, which uninstall never deletes (#1107).
    in_source = caps.authored_in_source(target_root, source_kit, name)
    subtree = f".pkit/capabilities/{name}/"

    if plan:
        # Before the refusal checks: a plan shows what removal would change in the
        # wiring whether or not the removal would be refused.
        from project_kit import capability_plans as plans

        uninstall_plan = plans.plan_uninstall(target_root, name, origin)
        click.echo(
            plans.to_json(uninstall_plan)
            if as_json
            else plans.render_uninstall_plan(uninstall_plan),
            nl=False,
        )
        return

    if purge and in_source:
        raise click.ClickException(
            f"refusing `--purge`: {subtree} is where {name!r} is authored, the "
            "methodology's source, and uninstall never deletes a capability's source "
            "(ADR-059). Nothing was written. To remove the capability from the source, "
            f"delete it with git: `git rm -r .pkit/capabilities/{name}`."
        )

    # Declared-dependent safety check (COR-030): refuse when another installed
    # capability declares this one in its requires_capabilities. This catches
    # behavioural dependencies that leave no textual citation (complementing
    # the find_references check below). Both checks are gated by --force.
    if not force:
        declared_dependents = caps.find_declared_dependents(target_root, name)
        if declared_dependents:
            click.echo(
                "\n  "
                + cli_render.style(
                    "strong",
                    f"Refusing to uninstall {name!r}: "
                    f"{len(declared_dependents)} installed capability(ies) "
                    f"declare a dependency on it:",
                )
                + "\n"
            )
            for dep_cap in declared_dependents:
                click.echo(f"    - {dep_cap}")
            raise click.ClickException(
                "Uninstall or upgrade the dependent capabilities first, "
                "or pass --force to override."
            )

    # Mandatory process connections aimed at it (COR-053 point 6): warn, naming
    # each counterpart the removal leaves unmet; refused unless --force, and still
    # reported under --force.
    _warn_mandatory_counterparts(
        target_root, name, action=f"uninstalling {name!r}", verb="uninstall", force=force
    )

    # Reference safety check.
    if not force:
        references = caps.find_references(target_root, name)
        if references:
            click.echo(
                "\n  "
                + cli_render.style(
                    "strong",
                    f"Refusing to uninstall {name!r}: {len(references)} reference(s) found:",
                )
                + "\n"
            )
            # Show a compact summary (capped to first 10).
            for path, snippet in references[:10]:
                rel = path.relative_to(target_root) if target_root in path.parents else path
                click.echo(f"    {rel}: {snippet}")
            if len(references) > 10:
                click.echo(f"    ... and {len(references) - 10} more.")
            raise click.ClickException("Clean references first, or pass --force to override.")

    # --purge on an incubated capability deletes the adopter's only copy of
    # authored work — a destructive op. Confirm before proceeding (the
    # pause-before-destructive-ops discipline), unless --yes or --dry-run.
    if purge and incubated and not dry_run and not yes:
        cap_dir = target_root / ".pkit" / "capabilities" / name
        click.confirm(
            f"--purge will permanently delete the authored subtree at "
            f"{cap_dir.relative_to(target_root)}/ — the only copy of this "
            f"incubated capability's work. Continue?",
            abort=True,
        )

    # A kit-shipped registration is one whose uninstall deletes the subtree. In the
    # source that subtree is the capability's source, so uninstall does less than
    # the registration promises: say what it would have deleted and what it does
    # instead, and ask, unless --yes or --dry-run (#1107). An incubated one is
    # unregistered in place anyway (COR-031 D4), so there is nothing to ask.
    if in_source and not incubated:
        click.echo(
            f"\n  {name!r} is authored in this repository, the methodology's source: "
            f"{subtree} is the tree this code installs capabilities from, not a copy of it."
        )
        click.echo(
            "  Uninstalling a kit-shipped capability deletes its subtree; here that would "
            f"delete {subtree}, the capability's source. Uninstall unregisters it instead "
            "and deletes nothing (ADR-059)."
        )
        if not dry_run and not yes:
            click.confirm(f"Unregister {name!r} and keep {subtree}?", abort=True)

    outcome = caps.uninstall_capability(
        target_root, name, source_kit=source_kit, purge=purge, dry_run=dry_run
    )

    if outcome.files_deleted:
        verb = "Would remove" if dry_run else "Removed"
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"{verb} capability {name!r} from {outcome.cap_dir.relative_to(target_root)}",
            )
        )
    elif outcome.in_source and not incubated:
        verb, deleted = ("Would unregister", "would be") if dry_run else ("Unregistered", "was")
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"{verb} capability {name!r}; nothing {deleted} deleted: its source "
                f"stays at {subtree}.",
            )
        )
        if not dry_run:
            click.echo(f"  (`pkit capabilities install {name}` registers it again.)")
    else:
        # Incubated, kept in place (COR-031 D4): unregistered, files retained.
        verb = "Would unregister" if dry_run else "Unregistered"
        click.echo(
            "\n  "
            + cli_render.style(
                "strong",
                f"{verb} incubated capability {name!r} in place; your authored "
                f"files are kept at {outcome.cap_dir.relative_to(target_root)}/",
            )
        )
        # The source refuses --purge, so it is offered only where it applies.
        if not dry_run and not outcome.in_source:
            click.echo("  (pass --purge to delete the authored subtree as well.)")

    if not dry_run:
        # Re-run installed adapter primitives so the harness drops stale
        # entries of a deleted subtree (e.g., deploy-skills.sh's "stale
        # removal" pass). A subtree kept on disk was already undeployed
        # inside `uninstall_capability`, through each adapter's undeploy
        # primitive, since a deploy re-run cannot see it as gone.
        from project_kit import install as install_mod

        ctx = install_mod.InstallContext(
            target_root=target_root,
            source_kit=source_kit,
            dry_run=False,
        )
        install_mod.run_installed_adapter_primitives(ctx)


@capabilities.command("list")
def list_capabilities_cmd() -> None:
    """List capabilities available in the kit source and which are installed."""
    from project_kit import capabilities as caps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    source_kit = find_source_kit()
    available, installed = caps.list_capabilities(target_root, source_kit)
    origins = caps.installed_capability_origins(target_root)

    # Union of names the adopter can see: kit-source-available plus anything
    # installed. An incubated (in-repo) capability is installed but never in
    # `available` (it doesn't ship from kit source), so without the union it
    # would vanish from this list — exactly the visibility COR-031 requires.
    names = sorted(set(available) | set(installed))

    if not names:
        click.echo(
            cli_render.view(
                title=cli_render.title("Capabilities", "0 available"),
                sections=[cli_render.section(empty="(none ship in this kit version)")],
            ),
            nl=False,
        )
        return

    rows: list[dict[str, str]] = []
    for n in names:
        origin = origins.get(n, "")
        # Only mark origin for installed capabilities; an available-but-not-
        # installed one has no install-state origin to report.
        origin_label = (
            "incubated"
            if origin == caps.INCUBATED_IN_REPO
            else "kit-shipped"
            if n in installed
            else ""
        )
        rows.append(
            {
                "name": n,
                "status": "installed" if n in installed else "",
                "origin": origin_label,
            }
        )
    click.echo(
        cli_render.view(
            title=cli_render.title(
                "Capabilities",
                f"{len(names)} known",
                gloss="install with `pkit capabilities install <name>`",
            ),
            sections=[cli_render.section(rows=rows, columns=["name", "status", "origin"])],
            commands=[
                ("pkit capabilities install <name>", "install a kit-shipped one into this project"),
                ("pkit capabilities register <name>", "register an in-repo (incubated) one"),
            ],
        ),
        nl=False,
    )


@capabilities.command("refresh")
@click.argument("name")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what the generated list would hold without writing the package file.",
)
def refresh_capability_cmd(name: str, dry_run: bool) -> None:
    """Regenerate a capability's generated package metadata (COR-053 point 4).

    Rewrites `connections.extensions.depends-on` in
    `.pkit/capabilities/<name>/package.yaml` from the `depends_on` its process
    definitions declare, marked `generated: true`; the rest of the file is kept
    as written. Run it where the capability is authored — after coupling a
    process, or when `pkit validate` reports the list stale. A kit-shipped
    capability installed in an adopting project is refused: its package file is
    core-owned and sync would overwrite the edit.
    """
    from project_kit import capabilities as caps
    from project_kit import install as install_mod
    from project_kit import process_dependencies as deps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    caps.refuse_reserved_capability_name(name)
    cap_dir = target_root / ".pkit" / "capabilities" / name
    if not (cap_dir / "package.yaml").is_file():
        raise click.ClickException(
            f"no capability named {name!r} is authored in this repository at "
            f".pkit/capabilities/{name}/package.yaml."
        )
    kit_shipped = (
        caps.is_installed(target_root, name)
        and caps.read_capability_origin(target_root, name) == caps.KIT_SHIPPED
    )
    if kit_shipped and not install_mod.is_self_host(target_root, find_source_kit()):
        raise click.ClickException(
            f"capability {name!r} is kit-shipped: its package.yaml is core-owned and "
            "`pkit sync` overwrites it (the no-shared-files invariant). A stale "
            "`depends-on` list there is the capability author's to regenerate — report "
            "it upstream."
        )

    try:
        result = deps.refresh(cap_dir, dry_run=dry_run)
    except deps.RefreshError as exc:
        raise click.ClickException(str(exc)) from exc

    where = result.package_file.relative_to(target_root)
    count = f"{len(result.entries)} entry(ies)"
    if not result.changed:
        fresh = f"`{deps.DEPENDS_ON_KEY}` in {where} is fresh ({count}); nothing to write."
        click.echo("\n  " + cli_render.style("strong", fresh))
        return
    verb = "Would refresh" if dry_run else "Refreshed"
    click.echo(
        "\n  "
        + cli_render.style(
            "strong",
            f"{verb} `{'.'.join(deps.BLOCK_PATH)}` in {where}: {count} generated from the "
            "process definitions' `depends_on`.",
        )
    )
    for entry in result.entries:
        click.echo(f"    - {entry.text()}")


# --- New artifacts (decisions, agents, etc.) ------------------------------


@main.group()
def new() -> None:
    """Scaffold new methodology artifacts: decisions, adapters, migrations, areas, capabilities,
    schemas, scratchpads, agents, storyboards."""


@new.command("decision")
@click.argument("namespace")
@click.argument("slug")
def new_decision(namespace: str, slug: str) -> None:
    """Stamp a new decision-record stub.

    Namespaces:
      core           → COR-NNN at .pkit/decisions/core/
      project        → PRJ-NNN at .pkit/decisions/project/
      adr            → ADR-NNN at the overlay's <adr-records> path (per COR-024/COR-025)
      <capability>   → DEC-NNN at .pkit/capabilities/<capability>/decisions/ (Feature #162)

    Any NAMESPACE that is not core/project/adr is interpreted as a
    capability name; the command refuses if no such capability exists.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_decision(target_root, namespace=namespace, slug=slug)
    try:
        rel = target.relative_to(target_root)
    except ValueError:
        rel = target
    click.echo(f"Stamped: {rel}")


@new.command("area")
@click.argument("name")
@click.option(
    "--variant",
    type=click.Choice(["universal", "adapter-umbrella", "specialized"]),
    default="specialized",
    show_default=True,
    help="Variant determining the area's internal layout (per COR-011).",
)
def new_area(name: str, variant: str) -> None:
    """Scaffold a new area at .pkit/<name>/ (per COR-011)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_area(target_root, name=name, variant=_cast_area_variant(variant))
    rel = result.area_dir.relative_to(target_root)
    click.echo(f"Stamped: {rel}/ (variant: {variant})")


@new.command("adapter")
@click.argument("name")
def new_adapter(name: str) -> None:
    """Scaffold a new adapter at .pkit/adapters/<name>/ (per COR-005)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_adapter(target_root, name=name)
    rel = result.adapter_dir.relative_to(target_root)
    click.echo(f"Stamped: {rel}/")
    # Register in the backbone manifest so the adapter is immediately
    # discoverable (per COR-005's "Scaffold output is wired" implication).
    project_manifest_rel = f".pkit/adapters/{name}/project/manifest.yaml"
    register_kit_shipped_component(
        target_root, kind="adapter", name=name, manifest_path=project_manifest_rel
    )


@new.command("schema")
@click.argument("capability")
@click.argument("name")
@click.option(
    "--collection-form",
    type=click.Choice(["mapping", "list"]),
    default="mapping",
    show_default=True,
    help="Collection layout: `mapping` (keys are ids; the dominant form) or "
    "`list` (each item has `id:`; pick when entries need stable ordering or "
    "per-entry metadata that doesn't fit a mapping value). Ignored with "
    "`--no-namespace`.",
)
@click.option(
    "--collection-name",
    default="entries",
    show_default=True,
    help="Top-level YAML key holding the id collection (e.g., `types`, "
    "`states`, `severities`). Defaults to `entries`; pick a domain-specific "
    "name when one exists. Ignored with `--no-namespace`.",
)
@click.option(
    "--no-namespace",
    is_flag=True,
    default=False,
    help="Stamp a document-shaped schema (one resource per file) rather "
    "than a namespace owner. No top-level id collection, no "
    "`x-pkit-id-collection` annotation, flat `properties: {}` placeholder. "
    "Use for single-document specs (e.g., a `trip.yaml` describing one "
    "trip) where the file IS the resource, not a collection of entries.",
)
def new_schema(
    capability: str,
    name: str,
    collection_form: str,
    collection_name: str,
    no_namespace: bool,
) -> None:
    """Scaffold a new YAML + JSON Schema companion pair.

    CAPABILITY is the target: the reserved value `core` stamps into the
    core schemas area (`.pkit/schemas/`); any other value names a
    capability (`.pkit/capabilities/<capability>/schemas/`).

    Default: stamps a **namespace owner** — top-level id collection +
    `x-pkit-id-collection` annotation pointing at it. Pass
    `--no-namespace` to stamp a **document-shaped schema** instead: one
    resource per file, flat `properties: {}` placeholder, no collection
    annotation.

    Validates the stamp via `pkit schemas validate`; rolls back both
    files if anything fails. Refuses if the schema already exists, or if
    the capability doesn't exist (run `pkit new capability` first).
    """
    from project_kit import schemas_authoring as authoring

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        result = authoring.stamp_new_schema(
            target_root,
            capability=capability,
            name=name,
            collection_form=collection_form,
            collection_name=collection_name,
            no_namespace=no_namespace,
        )
    except authoring.SchemaAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc

    yaml_rel = result.yaml_path.relative_to(target_root)
    companion_rel = result.companion_path.relative_to(target_root)
    click.echo(f"Stamped: {yaml_rel}")
    click.echo(f"Stamped: {companion_rel}")
    if no_namespace:
        click.echo(
            "Next: declare the document's top-level fields in the "
            "companion's `properties`, then fill the YAML body accordingly."
        )
    else:
        click.echo(
            f"Next: fill the companion's $defs.entry.properties with per-entry "
            f"field declarations, then add entries via "
            f"`pkit schemas add {name} <id> --from <path>`."
        )


@new.command("capability")
@click.argument("name")
def new_capability(name: str) -> None:
    """Scaffold a new capability at .pkit/capabilities/<name>/ (per COR-017).

    Stamps `package.yaml`, an adopter-facing `README.md`, and the five
    standard subdirectories (decisions, skills, agents, scripts, schemas)
    so the author has a complete skeleton to populate.

    Unlike `pkit new adapter`, capabilities are NOT registered
    in the backbone manifest by the scaffolding step — they are
    kit-shipped from the source-of-edit's perspective, and adopters
    register them per-project via `pkit capabilities install <name>`.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_capability(target_root, name=name)
    rel = result.capability_dir.relative_to(target_root)
    click.echo(f"Stamped: {rel}/")


@new.command("migration")
@click.option(
    "--tier",
    type=click.Choice(["backbone", "adapter", "capability"]),
    required=True,
    help="Which migration tree the script lands in (per COR-010 / COR-017).",
)
@click.option(
    "--component",
    type=str,
    default=None,
    help="Component name; required for --tier adapter / capability.",
)
@click.option(
    "--version",
    type=str,
    default=None,
    help="Target minor version (X.Y.0). Defaults to the tier's current version.",
)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Kebab-case slug for the migration file (e.g., 'add-status-labels').",
)
@click.option(
    "--scope",
    type=click.Choice(["manifest-schema", "structural", "resource"]),
    default="resource",
    show_default=True,
    help="Migration scope (per COR-010); affects the script's boilerplate header.",
)
def new_migration(
    tier: str,
    component: str | None,
    version: str | None,
    name: str | None,
    scope: str,
) -> None:
    """Scaffold a numbered migration script in the right <X.Y.0>/ directory."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_migration(
        target_root,
        tier=_cast_migration_tier(tier),
        component=component,
        version=version,
        slug=name,
        scope=_cast_migration_scope(scope),
    )
    rel = result.script.relative_to(target_root)
    click.echo(f"Stamped: {rel}")


@new.command("agent")
@click.argument("namespace")
@click.argument("name")
@click.option(
    "--with-storyboard",
    is_flag=True,
    default=False,
    help="Stamp folder-form per COR-015 with a sibling storyboard.md per COR-016. "
    "Pass this when the agent drives a scripted interaction scenario; the "
    "storyboard is the design source authored before the agent body.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be stamped without writing the file (per COR-004).",
)
def new_agent(namespace: str, name: str, with_storyboard: bool, dry_run: bool) -> None:
    """Stamp a new agent stub (per COR-013 + COR-015).

    Namespaces:
      core           → .pkit/agents/core/<name>.md
      project        → .pkit/agents/project/<name>.md
      <capability>   → .pkit/capabilities/<capability>/agents/<name>.md (COR-017, COR-026)

    Any NAMESPACE that is not core/project is interpreted as a capability
    name; the command refuses if no such capability exists, and creates its
    agents/ folder on first use.

    With --with-storyboard, stamps folder layout with a sibling storyboard
    scaffold (per COR-016) — for agents driving scripted interaction scenarios.
    The agent declares the storyboard in its storyboards: front matter and
    cites it in its body; the storyboard names the agent in consumers:.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_new_agent(
        target_root,
        name=name,
        namespace=namespace,
        with_storyboard=with_storyboard,
        dry_run=dry_run,
    )
    rel = target.relative_to(target_root)
    verb = "Would stamp" if dry_run else "Stamped"
    if with_storyboard:
        sibling = target.parent / STORYBOARD_FILE
        rel_sb = sibling.relative_to(target_root)
        click.echo(f"{verb}: {rel}")
        click.echo(f"{verb}: {rel_sb}")
    else:
        click.echo(f"{verb}: {rel}")


@new.command("storyboard")
@click.argument("artifact_kind", type=click.Choice(["agent"]))
@click.argument("name")
@click.option(
    "--namespace",
    type=str,
    default=None,
    help="Where the agent lives: core, project or a capability name. "
    "Default: the agent the deploy resolves — project, capabilities by name, then core.",
)
@click.option(
    "--scenario",
    type=str,
    default=None,
    help="Slug for a per-scenario storyboard file (stamps `<scenario>.storyboard.md`). "
    "Default: one `storyboard.md` covering one or more scenarios.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be stamped without writing the file (per COR-004).",
)
def new_storyboard(
    artifact_kind: str,
    name: str,
    namespace: str | None,
    scenario: str | None,
    dry_run: bool,
) -> None:
    """Stamp a storyboard sibling to an implementing artifact (per COR-016).

    Today's only supported artifact-kind is `agent`. The command resolves
    the named agent — in core, project or a capability's agents/ folder,
    flat or folder form; --namespace pins where to look. If the agent is
    currently flat, it migrates to folder form first per COR-015. Future
    application classes (cli, migration, tutorial) slot in as additional
    artifact-kind values without renaming this command.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_new_storyboard(
        target_root,
        kind=_cast_artifact_kind(artifact_kind),
        name=name,
        namespace=namespace,
        scenario=scenario,
        dry_run=dry_run,
    )
    rel = target.relative_to(target_root)
    verb = "Would stamp" if dry_run else "Stamped"
    click.echo(f"{verb}: {rel}")


def _cast_artifact_kind(value: str) -> ArtifactKind:
    if value == "agent":
        return "agent"
    raise click.ClickException(f"unsupported artifact-kind: {value!r}")


@new.command("scratchpad")
@click.argument("slug")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be stamped without writing the file (per COR-004).",
)
def new_scratchpad(slug: str, dry_run: bool) -> None:
    """Stamp a new active-state scratchpad note (per COR-012)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_new_scratchpad(target_root, slug=slug, dry_run=dry_run)
    rel = target.relative_to(target_root)
    verb = "Would stamp" if dry_run else "Stamped"
    click.echo(f"{verb}: {rel}")


@main.group()
def scratchpad() -> None:
    """Manage scratchpad notes (per COR-012 + COR-043): retire notes to done or
    dropped, stamp them reported, and list them with live upstream read-back."""


@scratchpad.command("done")
@click.argument("slug")
@click.option(
    "--produced",
    multiple=True,
    metavar="REF",
    help="Artifact reference the note produced (record ID, file path, or URL). Repeatable.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would change without moving the file or writing frontmatter.",
)
def scratchpad_done(slug: str, produced: tuple[str, ...], dry_run: bool) -> None:
    """Move an active scratchpad note to done/, appending retired/produced frontmatter."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    src, dst = transition_to_done(target_root, slug=slug, produced=produced, dry_run=dry_run)
    src_rel = src.relative_to(target_root)
    dst_rel = dst.relative_to(target_root)
    verb = "Would move" if dry_run else "Moved"
    click.echo(f"{verb}: {src_rel} -> {dst_rel}")


@scratchpad.command("drop")
@click.argument("slug")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would change without moving the file or writing frontmatter.",
)
def scratchpad_drop(slug: str, dry_run: bool) -> None:
    """Move an active scratchpad note to dropped/, appending retired frontmatter."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    src, dst = transition_to_dropped(target_root, slug=slug, dry_run=dry_run)
    src_rel = src.relative_to(target_root)
    dst_rel = dst.relative_to(target_root)
    verb = "Would move" if dry_run else "Moved"
    click.echo(f"{verb}: {src_rel} -> {dst_rel}")


@scratchpad.command("reported")
@click.argument("slug")
@click.argument("refs", nargs=-1, required=True)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would change without moving the file or writing frontmatter.",
)
def scratchpad_reported(slug: str, refs: tuple[str, ...], dry_run: bool) -> None:
    """Manually stamp a note as sent through the report channel (per COR-043).

    Moves an active note to the lazily-created reported/ and records the issue
    REFS (owner/repo#N, or a GitHub issue URL — normalised), the date, and a
    content hash of the file as sent. On an already-reported note, appends the
    refs not yet recorded (idempotent for duplicates) and re-anchors the hash.
    Covers URL-path posts (the compose flow ends by naming this exact
    command as the required follow-up, #664) and retroactive marking — the
    automatic stamp happens on a successful `pkit report` API post (direct
    or via `report submit`).
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    stamp = stamp_reported(target_root, slug, refs, dry_run=dry_run)
    if not stamp.added:
        click.echo(
            f"Already recorded: {', '.join(stamp.duplicate)} on "
            f"{stamp.dst.relative_to(target_root)} — nothing to do."
        )
        return
    if stamp.src != stamp.dst:
        verb = "Would move" if dry_run else "Moved"
        click.echo(
            f"{verb}: {stamp.src.relative_to(target_root)} -> {stamp.dst.relative_to(target_root)}"
        )
    verb = "Would record" if dry_run else "Recorded"
    click.echo(f"{verb}: {', '.join(stamp.added)}")
    if stamp.duplicate:
        click.echo(f"Already recorded: {', '.join(stamp.duplicate)}")


@scratchpad.command("list")
def scratchpad_list() -> None:
    """List scratchpad notes by state (per COR-012 + COR-043).

    Reported notes resolve their upstream refs live via gh — pull-only,
    nothing stored; offline degrades to "state unknown" — flag divergence
    from the stamped hash, and prompt retirement when every ref is closed
    (never auto-retired: retirement stays a human gesture).
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    entries = scratchpads.list_notes(target_root)
    if not entries:
        click.echo("No scratchpad notes.")
        return
    for folder in ("active", "reported", "done", "dropped"):
        group = [e for e in entries if e.folder == folder]
        if not group:
            continue
        click.echo(f"{folder}/")
        for entry in group:
            if folder != "reported":
                click.echo(f"  {entry.name}")
                continue
            refs_text = ", ".join(_reported_ref_text(r) for r in entry.refs) or "(no refs recorded)"
            drift = "  [modified since reported]" if entry.drifted else ""
            click.echo(f"  {entry.name}  -> {refs_text}{drift}")
            if entry.refs and all(r.state == "closed" for r in entry.refs):
                produced = " ".join(f"--produced {r.ref}" for r in entry.refs)
                click.echo(
                    "      all refs closed — retire with: pkit scratchpad done "
                    f"{scratchpads.note_slug(entry.name)} {produced}"
                )


def _reported_ref_text(r: scratchpads.ReportedRefState) -> str:
    """One resolved ref in a `scratchpad list` row (#678): ref + state, plus
    the issue's title and URL when the live read resolved them — so the
    listing says WHAT was reported, matching the report side's rollup rows.
    Offline/unresolved degrades to ref + state exactly as before."""
    state = "state unknown" if r.state == "unknown" else r.state
    if r.title or r.url:
        return f"{r.ref} ({state}) {r.title}  ({r.url})"
    return f"{r.ref} ({state})"


def _cast_area_variant(value: str) -> AreaVariant:
    """Click's `Choice` already validates; this widens str → AreaVariant for pyright."""
    if value == "universal":
        return "universal"
    if value == "adapter-umbrella":
        return "adapter-umbrella"
    return "specialized"


def _cast_migration_tier(value: str) -> MigrationTier:
    """Click's `Choice` already validates; this widens str → MigrationTier for pyright."""
    if value == "backbone":
        return "backbone"
    if value == "capability":
        return "capability"
    return "adapter"


def _cast_migration_scope(value: str) -> MigrationScope:
    """Click's `Choice` already validates; this widens str → MigrationScope for pyright."""
    if value == "manifest-schema":
        return "manifest-schema"
    if value == "structural":
        return "structural"
    return "resource"


# --- process substrate (per COR-033 / ADR-020) ------------------------


@main.group()
def process() -> None:
    """Process-substrate engine (per COR-033): resolve position, validate +
    execute guarded moves, render the self-explaining status view.

    Content-free — addresses a capability's process definition as
    `<capability>:<process-id>` and reads the subject's reality. Homed in the
    binary (ADR-020); capability wrappers call it by subprocess.
    """


def _load_engine(address: str, subject: str | None) -> ProcessEngine:
    """Resolve the repo root + definition + engine for a process address."""
    from project_kit import process as process_mod

    try:
        repo_root = process_mod.resolve_repo_root()
        definition = process_mod.load_definition(repo_root, address)
        # COR-032: resolve the subject per cardinality — keyed requires --subject,
        # singleton ignores it and uses the fixed key.
        return process_mod.ProcessEngine.for_subject(definition, repo_root, subject)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc


@process.command("status")
@click.argument("address")
@click.option(
    "--subject",
    default=None,
    help="Subject key. Required for a keyed process (COR-032); ignored for a singleton (the fixed "
    "key is used).",
)
@click.option(
    "--actor",
    default="operator",
    show_default=True,
    help="Evaluate gate prechecks as this actor (cross-authority).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit structured JSON instead of the narrative view.",
)
def process_status(address: str, subject: str | None, actor: str, as_json: bool) -> None:
    """Where the subject is · why · how it got here · legal moves · next hint."""
    from project_kit import process as process_mod

    engine = _load_engine(address, subject)
    try:
        if as_json:
            click.echo(process_mod.render_status_json(engine, actor), nl=False)
        else:
            click.echo(process_mod.render_status_narrative(engine, actor), nl=False)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc


@process.command("can-move")
@click.argument("address")
@click.option("--to", "to_state", required=True, help="Target state id.")
@click.option(
    "--subject",
    default=None,
    help="Subject key. Required for a keyed process (COR-032); ignored for a singleton (the fixed "
    "key is used).",
)
@click.option(
    "--actor",
    default="operator",
    show_default=True,
    help="The actor being gated (cross-authority is computed against this).",
)
def process_can_move(address: str, to_state: str, subject: str | None, actor: str) -> None:
    """Validate a candidate move; refuse (fail-closed) with a self-explaining reason."""
    from project_kit import process as process_mod

    engine = _load_engine(address, subject)
    try:
        allowed, reason, _position = engine.can_move(to_state, actor)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    marker = "✓" if allowed else "✗"
    click.echo(f"  {marker} {reason}")
    if not allowed:
        raise SystemExit(1)


def _resolve_actor_identity() -> str:
    """Resolve the GitHub login of whoever is driving, for the `--actor` default.

    The cross-authority gate (COR-033 P4) compares `--actor` against an
    authorisation artifact's `produced_by` login, so the default must be a real
    GitHub login — not an authorisation token. We resolve it via `gh api user`
    rather than importing the project-management capability's membership helper:
    the binary must not depend on a capability tree (dependency boundary).

    Falls back to `"operator"` when `gh` is missing/unauthenticated, preserving
    the prior default so the command never fails on identity resolution alone.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return "operator"
    login = result.stdout.strip() if result.returncode == 0 else ""
    return login or "operator"


@process.command("move")
@click.argument("address")
@click.option("--to", "to_state", required=True, help="Target state id.")
@click.option(
    "--from",
    "from_state",
    default=None,
    help="The state the subject held before you applied this move's domain side-effect "
    "(the seam-ordering contract). The move is validated and journaled from there, and "
    "refused when live detection places the subject at neither this state nor the target. "
    "Omit it to move from the live position.",
)
@click.option(
    "--subject",
    default=None,
    help="Subject key. Required for a keyed process (COR-032); ignored for a singleton (the fixed "
    "key is used).",
)
@click.option(
    "--actor",
    default=None,
    help="The actor performing the move (recorded in the journal; gated "
    "cross-authority). Defaults to the resolved gh login of the "
    "current user.",
)
@click.option(
    "--reason",
    default=None,
    metavar="TEXT",
    help="Why the move was taken, recorded on its journal entry as given. The engine does not "
    "read it, so it never changes whether the move is allowed.",
)
def process_move(
    address: str,
    to_state: str,
    from_state: str | None,
    subject: str | None,
    actor: str | None,
    reason: str | None,
) -> None:
    """Execute a legal move; append the journal entry. Refuses an illegal move."""
    from project_kit import process as process_mod

    if actor is None:
        actor = _resolve_actor_identity()
    engine = _load_engine(address, subject)
    try:
        result = engine.move(to_state, actor, from_state=from_state, reason=reason)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    if not result.ok:
        click.echo("  " + cli_render.style("strong", f"refused: {result.reason}"))
        raise SystemExit(1)
    click.echo("  " + cli_render.style("strong", f"moved to {to_state!r}: {result.reason}"))


@process.command("cascade")
@click.argument("address")
@click.option(
    "--subject",
    default=None,
    help="Subject key. Required for a keyed process (COR-032); ignored for a singleton (the fixed "
    "key is used).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit structured JSON instead of the narrative view.",
)
def process_cascade(address: str, subject: str | None, as_json: bool) -> None:
    """Resolve the subject's declared cascade fold (COR-037) and report it.

    Reads the parent's `process.cascade` declaration, folds the named child
    process's member outcomes, and reports the single yes/no (`opened`) the
    fold resolves to — plus its determinacy and audit colour (reached/total).

    This exposes the engine's fold INDEPENDENTLY of a cascade-gated transition
    (which `status`/`can-move` require), so a wrapper can read the children-half
    of a composite eligibility decision and combine it with other gates itself
    (DEC-034: pm's close-eligibility is the conjunction of the checkbox gate AND
    this fold). Read-only; exits non-zero when the fold is NOT open (unresolved/
    fail-closed or a determinate "not yet").
    """
    import json

    from project_kit import process as process_mod

    engine = _load_engine(address, subject)
    try:
        resolution = engine.resolve_cascade_outcome()
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    if resolution is None:
        if as_json:
            click.echo(json.dumps({"cascade": None}, indent=2, sort_keys=True))
        else:
            click.echo("  (process declares no cascade)")
        raise SystemExit(1)
    if as_json:
        click.echo(
            json.dumps(
                {
                    "cascade": {
                        "runs": resolution.address,
                        "op": resolution.op,
                        "outcome": resolution.outcome,
                        "threshold": resolution.threshold,
                        "reached": resolution.reached,
                        "total": resolution.total,
                        "opened": resolution.opened,
                        "indeterminate": resolution.indeterminate,
                        "reason": resolution.reason,
                        # What a predicate the fold could not evaluate said
                        # (null when none failed, or it said nothing).
                        "stderr_tail": resolution.stderr_tail or None,
                    }
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        click.echo(process_mod.render_cascade_narrative(resolution))
    if not resolution.opened:
        raise SystemExit(1)


@process.command("validate")
@click.argument("address")
@click.option(
    "--subject",
    default=None,
    help="Subject key. Required for a keyed process (COR-032); ignored for a singleton (the fixed "
    "key is used).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit structured JSON instead of the narrative view.",
)
def process_validate(address: str, subject: str | None, as_json: bool) -> None:
    """Run the subject's invariants (COR-035); report which hold and which are
    violated. Read-only; exits non-zero if any invariant is violated."""
    from project_kit import process as process_mod

    engine = _load_engine(address, subject)
    try:
        if as_json:
            click.echo(process_mod.render_validate_json(engine), nl=False)
        else:
            click.echo(process_mod.render_validate_narrative(engine), nl=False)
        # The renderer already evaluated the invariants; this second call is a
        # no-op subprocess-wise (the PredicateRunner per-invocation cache returns
        # the same verdicts) so the exit code cannot disagree with the printed
        # report. If predicate caching is ever removed/per-call, evaluate once
        # here and pass the outcomes into the renderer instead.
        ok = all(inv.holds for inv in engine.evaluate_invariants())
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    if not ok:
        raise SystemExit(1)


@process.command("health")
@click.option(
    "--process",
    "focus_process",
    default=None,
    help="Only contracts touching this <capability>:<process-id> (as upstream or downstream).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit the byte-stable machine form (per-contract objects + totals; no styling).",
)
@click.option(
    "--interpretation-only",
    "interpretation_only",
    is_flag=True,
    default=False,
    help="Report INDETERMINATES only (the authoring completion signal, COR-044): "
    "does every contract resolve and its seams execute? Misses are not "
    "counted and do not affect the exit code.",
)
def process_health(focus_process: str | None, as_json: bool, interpretation_only: bool) -> None:
    """Walk every declared hand-off contract (COR-042) and report missed
    hand-offs — upstream subjects at their trigger state with no downstream
    counterpart.

    \b
    Takes NO subject: it walks the opt-in `handoff` contracts on `depends_on`
    entries across the configured wiring. Out-of-runtime and REPORT-ONLY — it
    reads live upstream positions through the engine's per-subject resolution
    plus the binding's candidates/resolve seam predicates (ADR-048), but blocks
    no move, writes no journal entry, remediates nothing. Entries without a
    contract are never evaluated.

    \b
    Fail-closed (COR-042): an uninterpretable contract (unresolvable upstream
    address, phantom trigger), a broken candidate source, an unreadable upstream
    position, or an erroring `resolve` is INDETERMINATE — reported distinctly,
    never counted as "nothing missed". A determinate-empty candidate set is
    clean. Deterministic: contracts order topologically over the wiring
    (upstream-most first, name tie-breaks), subjects name-sorted; no time/age
    ordering.

    Exits non-zero on any miss OR any indeterminate; 0 only when both are zero.

    \b
    --interpretation-only is the AUTHORING variant (COR-044): it consumes the
    SAME walk (never a parallel contract-walker, COR-042 point 5) but reports
    only the interpretability half — indeterminates — and counts NO misses (a
    fresh, correct contract routinely reports real misses; miss-count is never
    the authoring done-signal). It also checks BOTH seams statically — declared
    command registered, script present, no longer the scaffolded stub — so the
    answer does not depend on which subjects happen to sit at the trigger. With
    the flag, the exit code is non-zero on any indeterminate only. The default
    run's exit contract is unchanged.

    \b
    Scope it with --process <addr> when the question is "is MY contract done?":
    the bare form walks every contract in the project, so someone else's
    unimplemented seam would hold your done-signal red.
    """
    from project_kit import process as process_mod
    from project_kit import process_health as ph

    try:
        repo_root = process_mod.resolve_repo_root()
        report = ph.build_report(repo_root, focus=focus_process)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc

    if interpretation_only:
        interpretation = ph.build_interpretation(report)
        if as_json:
            click.echo(ph.render_interpretation_json(interpretation), nl=False)
        else:
            click.echo(ph.render_interpretation_narrative(interpretation), nl=False)
        if not interpretation.ok:
            raise SystemExit(1)
        return

    if as_json:
        click.echo(ph.render_json(report), nl=False)
    else:
        click.echo(ph.render_narrative(report), nl=False)
    if not report.ok:
        raise SystemExit(1)


# --- process authoring stamps (per COR-044) ---------------------------


def _authoring_repo_root():
    from project_kit import process as process_mod

    try:
        return process_mod.resolve_repo_root()
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc


def _echo_authoring_warnings(warnings: tuple[str, ...]) -> None:
    for warning in warnings:
        click.echo("  " + cli_render.style("warn", f"⚠ {warning}"))


def _split_pair(raw: str, sep: str, flag: str, shape: str) -> tuple[str, str]:
    head, _, tail = raw.partition(sep)
    if not head.strip() or not tail.strip():
        raise click.ClickException(f"{flag} {raw!r} is malformed; expected {shape}.")
    return head.strip(), tail.strip()


@process.command("new")
@click.argument("address")
@click.option(
    "--cardinality",
    default="singleton",
    show_default=True,
    help="Subject cardinality (validated against the shape contract's set).",
)
@click.option(
    "--key",
    "subject_key",
    default=None,
    help="Descriptive name of what identifies a KEYED unit (COR-032); keyed only.",
)
@click.option(
    "--domain-ref",
    "domain_ref",
    default=None,
    metavar="<pointer>",
    help="Pointer to where the subject's DOMAIN data lives — distinct from its "
    "process position (optional, either cardinality). Free-form: the "
    "engine never interprets it.",
)
@click.option(
    "--state",
    "state_flags",
    multiple=True,
    required=True,
    metavar="<id>=<meaning>",
    help="Declare a state (repeatable; declaration order is kept — it can be "
    "load-bearing for detection precedence). Every state gets a detection "
    "predicate stub.",
)
@click.option(
    "--entry",
    "entry_flags",
    multiple=True,
    metavar="<state-id>",
    help="Mark a state as an unconditional entry (repeatable).",
)
@click.option(
    "--guarded-entry",
    "guarded_entry_flags",
    multiple=True,
    metavar="<state-id>",
    help="Mark a state as a GUARDED entry (repeatable); scaffolds an entry-guard predicate stub.",
)
@click.option(
    "--terminal",
    "terminal_flags",
    multiple=True,
    metavar="<state-id>",
    help="Mark a state terminal — an outcome a parent may wire (repeatable).",
)
@click.option(
    "--transition",
    "transition_flags",
    multiple=True,
    metavar="<from>:<to>:<trigger>[:<authorisation>]",
    help="Declare a transition (repeatable). `from` may be `*` (any source). "
    "Authorisation defaults to `user` (the safe floor: nothing moves "
    "autonomously until the author decides otherwise).",
)
@click.option(
    "--gate",
    "gate_flags",
    multiple=True,
    metavar="<from>:<to>:<trigger>[:<kind>]",
    help="Gate a declared transition (repeatable); scaffolds a gate predicate "
    "stub. Addresses the transition by its FULL key including the trigger "
    "— two edges between the same state pair are legal when their triggers "
    "differ, and each is gated separately. Kind defaults to "
    "`deterministic`; `authorisation-artifact` is the other stubbed kind "
    "(engine-computed kinds ride the deferred subprocess/cascade block "
    "surface).",
)
@click.option(
    "--invariant",
    "invariant_flags",
    multiple=True,
    metavar="<id>=<why>",
    help="Declare a position-independent always-check (COR-035, repeatable); "
    "scaffolds a check predicate stub.",
)
@click.option(
    "--blocked",
    "blocked_on",
    default=None,
    help="Declare the subject's wait reason (COR-034; validated against the "
    "shape contract's set). `awaiting-condition` scaffolds a resume_when "
    "predicate stub.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="Report what would be stamped without writing anything.",
)
def process_new(
    address: str,
    cardinality: str,
    subject_key: str | None,
    domain_ref: str | None,
    state_flags: tuple[str, ...],
    entry_flags: tuple[str, ...],
    guarded_entry_flags: tuple[str, ...],
    terminal_flags: tuple[str, ...],
    transition_flags: tuple[str, ...],
    gate_flags: tuple[str, ...],
    invariant_flags: tuple[str, ...],
    blocked_on: str | None,
    dry_run: bool,
) -> None:
    """Scaffold a lint-clean process definition into its owning capability.

    ADDRESS is `<capability>:<process-id>` — the owning capability is REQUIRED
    (COR-044: a definition is a capability-instance artifact; the command
    errors cleanly without one and never routes through capability authoring —
    that walkthrough is the process-authoring skill's judgment).

    \b
    Stamps `.pkit/capabilities/<capability>/schemas/<process-id>.yaml` (subject
    incl. cardinality and an optional domain-data pointer, states with
    meanings, transitions, entry/terminal marks), validated against the shape
    contract BEFORE writing, plus a predicate STUB for every evaluable the
    declared shape demands — detection always; gates / entry guards /
    resume_when / invariant checks when declared. Stubs follow the
    predicate-runner contract (read-only, subject argv + `--json`) and FAIL
    CLOSED (exit non-zero) until implemented, so an unwritten predicate can
    never read as green; each registers in the owning capability's
    package.yaml. Implementing them is the process-author agent's territory.
    One-shot: refuses when the process id already resolves.
    """
    from project_kit import process_authoring as authoring

    repo_root = _authoring_repo_root()

    pairs = [_split_pair(raw, "=", "--state", "<id>=<meaning>") for raw in state_flags]
    declared_ids = {state_id for state_id, _ in pairs}
    for flag_name, mark in (
        ("--entry", entry_flags),
        ("--guarded-entry", guarded_entry_flags),
        ("--terminal", terminal_flags),
    ):
        for state_id in mark:
            if state_id not in declared_ids:
                raise click.ClickException(
                    f"{flag_name} {state_id!r} does not match a --state declaration."
                )
    states = [
        authoring.StateSpec(
            state_id=state_id,
            meaning=meaning,
            entry=state_id in entry_flags,
            guarded_entry=state_id in guarded_entry_flags,
            terminal=state_id in terminal_flags,
        )
        for state_id, meaning in pairs
    ]

    transitions: list[authoring.TransitionSpec] = []
    for raw in transition_flags:
        parts = [p.strip() for p in raw.split(":")]
        if len(parts) not in (3, 4) or not all(parts):
            raise click.ClickException(
                f"--transition {raw!r} is malformed; expected "
                "<from>:<to>:<trigger>[:<authorisation>]."
            )
        transitions.append(
            authoring.TransitionSpec(
                from_state=parts[0],
                to_state=parts[1],
                trigger=parts[2],
                authorisation=parts[3] if len(parts) == 4 else "user",
            )
        )
    for raw in gate_flags:
        parts = [p.strip() for p in raw.split(":")]
        if len(parts) not in (3, 4) or not all(parts):
            raise click.ClickException(
                f"--gate {raw!r} is malformed; expected <from>:<to>:<trigger>[:<kind>]."
            )
        kind = parts[3] if len(parts) == 4 else "deterministic"
        # A transition is keyed by (from, to, trigger): addressing a gate by the
        # state pair alone would leave a second edge between the same pair (an
        # `approve` beside a `force-approve`) permanently ungateable, and two
        # --gate flags on that pair silently last-wins.
        key = (parts[0], parts[1], parts[2])
        for index, t in enumerate(transitions):
            if (t.from_state, t.to_state, t.trigger) != key:
                continue
            if t.gate_kind is not None:
                raise click.ClickException(
                    f"--gate {raw!r} addresses a transition that is already "
                    "gated; declare one gate per transition."
                )
            transitions[index] = authoring.TransitionSpec(
                from_state=t.from_state,
                to_state=t.to_state,
                trigger=t.trigger,
                authorisation=t.authorisation,
                gate_kind=kind,
            )
            break
        else:
            raise click.ClickException(
                f"--gate {raw!r} does not match a --transition declaration "
                "(the address is <from>:<to>:<trigger>, the transition's full key)."
            )

    invariants = [
        authoring.InvariantSpec(*_split_pair(raw, "=", "--invariant", "<id>=<why>"))
        for raw in invariant_flags
    ]

    try:
        result = authoring.stamp_new_process(
            repo_root,
            address,
            cardinality=cardinality,
            subject_key=subject_key,
            domain_ref=domain_ref,
            states=states,
            transitions=transitions,
            invariants=invariants,
            blocked_on=blocked_on,
            dry_run=dry_run,
        )
    except authoring.ProcessAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc

    verb = "Would stamp" if dry_run else "Stamped"
    click.echo(f"{verb}: {result.definition_path.relative_to(repo_root)}")
    for stub in result.stubs:
        click.echo(f"  stub: {stub.command} -> {stub.script_relpath}  ({stub.purpose})")
    _echo_authoring_warnings(result.warnings)
    if dry_run:
        click.echo("Dry run — nothing was written.")
        return
    click.echo(
        "Next: implement each predicate stub (the process-author agent's "
        "territory), then `pkit process status " + address + "`."
    )


@process.command("couple")
@click.argument("address")
@click.option(
    "--state",
    "state_id",
    required=True,
    help="The hosting state of the coupling (a state of ADDRESS; the hosting "
    "state has no semantic effect on any check — audit colour, COR-042).",
)
@click.option(
    "--upstream",
    required=True,
    metavar="<capability>:<process-id>|<publisher>::<role>:<point>",
    help="The upstream process this definition depends on: by implementation, "
    "or by role — the process offered at that address by whichever "
    "capability is the role's active provider (COR-053 point 2).",
)
@click.option(
    "--relation",
    required=True,
    help="The connection kind, from COR-038's closed set as the shape contract "
    "declares it (read as data — a new relation kind is an enum value, "
    "never a code change).",
)
@click.option(
    "--mode",
    required=True,
    help="pull (read on the reader's turn) | push (mediated OUTSIDE the "
    "engine — no eventing); from the shape contract's set.",
)
@click.option(
    "--why",
    required=True,
    help="The human-readable reason the render surfaces (required, COR-038).",
)
@click.option(
    "--version",
    "interface_version",
    type=click.IntRange(min=1),
    default=None,
    metavar="<n>",
    help="The upstream interface version this connection targets: it connects "
    "only to an offered process at an equal version (COR-053 point 5).",
)
@click.option(
    "--mandatory",
    "mandatory",
    default=None,
    metavar="<reason>",
    help="Mark the connection mandatory, with the reason every refusal and "
    "warning it causes quotes: the capability lifecycle then refuses to "
    "install or upgrade this capability while the upstream is missing "
    "(COR-053 point 6).",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="Report what would change without writing anything.",
)
def process_couple(
    address: str,
    state_id: str,
    upstream: str,
    relation: str,
    mode: str,
    why: str,
    interface_version: int | None,
    mandatory: str | None,
    dry_run: bool,
) -> None:
    """Author a `depends_on` coupling into the invoker-named definition.

    Appends the entry to ADDRESS's hosting state (COR-038: coupling lives in
    the SUBSCRIBER's definition — the upstream is never touched), with
    `version` and the `mandatory` mark when given. The entry is inert metadata
    the runtime engine never evaluates; the definition `version` is NOT bumped
    (additive inert edit, COR-044). An upstream that does not resolve here — a
    role address through the wiring — is declarable (warned, not refused).

    An entry is identified by (upstream, relation, mode) — one state may
    legally depend on the same upstream in two different ways. Idempotent on
    the identical entry; refuses when that key is already declared with a
    DIFFERENT why, version or mark.

    The stamp writes the definition only. When the capability's generated
    `depends-on` list in package.yaml is left stale, it ends by naming
    `pkit capabilities refresh <capability>` — run it; `pkit validate` fails
    until the list follows the definitions (COR-053 point 4).
    """
    from project_kit import process_authoring as authoring

    repo_root = _authoring_repo_root()
    try:
        result = authoring.couple_process(
            repo_root,
            address,
            state_id=state_id,
            upstream=upstream,
            relation=relation,
            mode=mode,
            why=why,
            version=interface_version,
            mandatory=mandatory,
            dry_run=dry_run,
        )
    except authoring.ProcessAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc

    rel = result.definition_path.relative_to(repo_root)
    edge = ", ".join(
        [relation, mode]
        + ([f"v{interface_version}"] if interface_version is not None else [])
        + (["mandatory"] if mandatory is not None else [])
    )
    if not result.changed:
        click.echo(
            f"Already declared: {address} state {result.state_id!r} -> "
            f"{upstream} ({edge}); nothing to do."
        )
    else:
        click.echo(
            f"{'Would couple' if dry_run else 'Coupled'}: {address} state "
            f"{result.state_id!r} -> {upstream} ({edge}) in {rel} "
            "(definition version unchanged)."
        )
    _echo_authoring_warnings(result.warnings)
    if dry_run:
        click.echo("Dry run — nothing was written.")
    if result.refresh_command is not None:
        state = "after a real run would be" if dry_run else "is"
        click.echo(
            f"Next: `{result.refresh_command}` — the generated `depends-on` list in the "
            f"capability's package.yaml {state} stale against its process definitions, "
            "and `pkit validate` fails until it is regenerated (COR-053 point 4)."
        )


@process.command("hand-off")
@click.argument("address")
@click.option(
    "--upstream",
    required=True,
    metavar="<capability>:<process-id>",
    help="The coupled upstream process the contract checks against.",
)
@click.option(
    "--state",
    "state_id",
    default=None,
    help="Hosting state of the coupling; needed only when ADDRESS couples to "
    "the same upstream on several states. It names a state, so it cannot "
    "tell apart two entries on one state — the refusal names the hand edit.",
)
@click.option(
    "--trigger",
    required=True,
    help="The upstream state meaning 'ready to hand off'. Declare a STABLE "
    "state — a subject that transits an ephemeral trigger leaves the "
    "report, picked up or not (COR-042 authoring smell).",
)
@click.option(
    "--candidates",
    required=True,
    metavar="<command>",
    help="The candidate-source command of THIS capability (registered name; "
    "scaffolded as a fail-closed stub + registered when new). Subject "
    "slot = the upstream process address; payload {candidates: [...]}. "
    "A source that can silently return nothing against a wrong root is "
    "the sibling authoring smell — error instead (COR-042).",
)
@click.option(
    "--resolve",
    required=True,
    metavar="<command>",
    help="The resolve-seam command of THIS capability (registered name; "
    "scaffolded as a fail-closed stub + registered when new). Subject "
    "slot = one upstream subject id; payload {downstream: [...]} — "
    "empty = determinate absence (a miss), error = indeterminate.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="Report what would change without writing anything.",
)
def process_handoff(
    address: str,
    upstream: str,
    state_id: str | None,
    trigger: str,
    candidates: str,
    resolve: str,
    dry_run: bool,
) -> None:
    """Add a COR-042 hand-off contract to an existing coupling.

    Mutates ONLY the invoker-named (downstream) definition: the opt-in
    `handoff` sub-block — trigger + the two seam predicate refs — on the
    `depends_on` entry for --upstream. Refuses when no such coupling exists
    (`pkit process couple` first). Validates the trigger is a state of the
    upstream definition where it resolves at authoring time; an unresolvable
    upstream warns (health reports the contract indeterminate until it
    resolves — never silently green). The definition `version` is NOT bumped
    (additive report-only edit, COR-044).

    Finish by running `pkit process health --interpretation-only --process
    <addr>` — the authoring done-signal is NO indeterminates, never a zero
    miss-count. Scope it to your own address: the bare form walks every
    contract in the project.
    """
    from project_kit import process_authoring as authoring

    repo_root = _authoring_repo_root()
    try:
        result = authoring.handoff_process(
            repo_root,
            address,
            upstream=upstream,
            state_id=state_id,
            trigger=trigger,
            candidates=candidates,
            resolve=resolve,
            dry_run=dry_run,
        )
    except authoring.ProcessAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc

    rel = result.definition_path.relative_to(repo_root)
    if not result.changed:
        click.echo(
            f"Already declared: the coupling {upstream} -> {address} carries "
            f"this exact contract (@{trigger}); nothing to do."
        )
    else:
        verb = "Would declare contract" if dry_run else "Contract declared"
        click.echo(f"{verb}: {upstream} -> {address} @{trigger} in {rel} (version unchanged).")
        for stub in result.stubs:
            click.echo(
                f"  stub: {stub.command} -> {stub.script_relpath}  (implement "
                "before relying on the check — it fails closed until then)"
            )
    _echo_authoring_warnings(result.warnings)
    if dry_run:
        click.echo("Dry run — nothing was written.")
    elif result.changed:
        click.echo("Next: pkit process health --interpretation-only --process " + address)


@process.command("graph")
@_graph_format_options
@click.option(
    "--capability", default=None, help="Atomic filter: keep edges touching this capability."
)
@click.option(
    "--process",
    "focus_process",
    default=None,
    help="Atomic filter: focus on this <capability>:<process-id> (hops counted from it).",
)
@click.option(
    "--relation",
    "relations_csv",
    default=None,
    help="Atomic filter: keep only these relation kinds (csv).",
)
@click.option(
    "--mode",
    "mode",
    type=click.Choice(["pull", "push"]),
    default=None,
    help="Atomic filter: keep only edges of this mode.",
)
@click.option(
    "--source",
    "source",
    type=click.Choice(["derived", "annotated", "resolved"]),
    default=None,
    help="Atomic filter: keep only edges of this source (`resolved`: the offered-process edges the "
    "wiring resolver adds).",
)
@click.option(
    "--depth",
    type=int,
    default=None,
    help="Atomic filter: hops from the focused --process (requires --process). Without --direction "
    "it is UNDIRECTED (the depth-bounded neighbourhood), distinct from the directed "
    "--upstream-of/--downstream-of closures.",
)
@click.option(
    "--direction",
    type=click.Choice(["in", "out"]),
    default=None,
    help="Atomic filter: with --process, keep only its out- or in-edges (requires --process).",
)
@click.option(
    "--enforced",
    is_flag=True,
    default=False,
    help="Preset = source:derived ∪ relation:gates-on-readiness (the edges that actually block).",
)
@click.option(
    "--advisory",
    is_flag=True,
    default=False,
    help="Preset = relation:informational,triggered-by (no runtime block).",
)
@click.option("--seams", is_flag=True, default=False, help="Preset = cross-capability edges only.")
@click.option("--connectors", is_flag=True, default=False, help="Preset = mode:push.")
@click.option(
    "--declared",
    is_flag=True,
    default=False,
    help="Preset = source:annotated (the inert depends_on layer).",
)
@click.option(
    "--derived",
    is_flag=True,
    default=False,
    help="Preset = source:derived (the composition/aggregation layer).",
)
@click.option(
    "--cycles", is_flag=True, default=False, help="Preset = edges lying on a dependency cycle."
)
@click.option(
    "--upstream-of",
    "upstream_of",
    default=None,
    help="Preset = transitive closure of what this <addr> depends on.",
)
@click.option(
    "--downstream-of",
    "downstream_of",
    default=None,
    help="Preset = transitive closure of what depends on this <addr>.",
)
def process_graph(
    fmt_flow: bool,
    fmt_mermaid: bool,
    fmt_json: bool,
    capability: str | None,
    focus_process: str | None,
    relations_csv: str | None,
    mode: str | None,
    source: str | None,
    depth: int | None,
    direction: str | None,
    enforced: bool,
    advisory: bool,
    seams: bool,
    connectors: bool,
    declared: bool,
    derived: bool,
    cycles: bool,
    upstream_of: str | None,
    downstream_of: str | None,
    verbose: bool,
) -> None:
    """Render the configured cross-process topology (COR-038): a READ-ONLY view
    of process DEFINITIONS.

    \b
    The render is DERIVED edges (from each definition's subprocess/cascade
    blocks) ∪ ANNOTATED edges (from each state's depends_on list) — no edge
    expressible both ways (COR-038's derive-don't-annotate) — plus the
    RESOLVED `offers` edges by which a role-addressed depends_on reaches the
    process offering it. It is the one wiring graph (`pkit connections graph`,
    COR-053 point 7) filtered to its process edges, so the two never disagree.
    It reads DECLARATIONS only: it never resolves a live subject position, never
    runs a predicate, never moves anything (that is the safety point).

    \b
    Presets are documented EXPANSIONS of the atomic filters (a preset is a named
    combo, not magic), and AND-combine with any atomic filters you also pass:
      --enforced      = source:derived ∪ relation:gates-on-readiness
      --advisory      = relation:informational,triggered-by
      --seams         = cross-capability edges only
      --connectors    = mode:push
      --declared      = source:annotated
      --derived       = source:derived
      --cycles        = edges on a dependency cycle
      --upstream-of   = transitive closure following dependency direction
      --downstream-of = transitive closure against dependency direction

    \b
    Composition order (defensible, pinned): when --enforced is combined with a
    closure or cycle preset (--upstream-of / --downstream-of / --cycles), the
    closure/cycle detection runs OVER THE ENFORCED-NARROWED edge set -- the
    enforced union is applied first, then the closure walks only what survived.
    So `--enforced --upstream-of X` answers "what blocking edges is X
    (transitively) gated by", not "narrow X's full closure to the blocking
    edges".

    \b
    --depth is the depth-bounded NEIGHBOURHOOD of --process. Without --direction
    it is UNDIRECTED (out- and in-edges both, within N hops) -- distinct from the
    directed --upstream-of / --downstream-of closures. --depth / --direction
    require --process (they count hops FROM it); passing either alone is a usage
    error rather than a silent no-op.
    """
    from project_kit import process as process_mod
    from project_kit import process_graph as pg
    from project_kit import wiring_graph as wg

    _refuse_several_formats(fmt_flow, fmt_mermaid, fmt_json)
    # --depth / --direction count hops FROM the focused --process, so they are
    # only meaningful with it. They are consumed inside the --process focus pass;
    # without --process they would be silently ignored (G3), so fail loudly.
    if focus_process is None and (depth is not None or direction is not None):
        raise click.ClickException(
            "--depth / --direction require --process (they count hops from the focused process)."
        )
    relations = (
        frozenset(r.strip() for r in relations_csv.split(",") if r.strip())
        if relations_csv
        else frozenset()
    )
    base = pg.FilterSpec(
        capability=capability,
        process=focus_process,
        relations=relations,
        modes=frozenset([mode]) if mode else frozenset(),
        sources=frozenset([source]) if source else frozenset(),
        depth=depth,
        direction=direction,
    )
    spec = pg.expand_presets(
        base,
        enforced=enforced,
        advisory=advisory,
        seams=seams,
        connectors=connectors,
        declared=declared,
        derived=derived,
        cycles=cycles,
        upstream_of=upstream_of,
        downstream_of=downstream_of,
    )
    try:
        repo_root = process_mod.resolve_repo_root()
        view = wg.process_view(wg.build_wiring_graph(repo_root))
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    _echo_graph(
        pg.apply_filters(view, spec),
        fmt_flow=fmt_flow,
        fmt_mermaid=fmt_mermaid,
        fmt_json=fmt_json,
        verbose=verbose,
    )


if __name__ == "__main__":
    main()
