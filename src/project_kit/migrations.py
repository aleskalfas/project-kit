"""Migration runtime + authoring-time coverage check (per COR-010).

Four responsibilities:

1. **Runtime execution** — a migration is a per-minor-version script
   that bridges adopter state from one version to the next. The runner
   contract is the same across backbone, adapter, and capability tiers:

   - Scripts live under `<root>/<X.Y.0>/<NNN>-<slug>.sh`.
   - Execution walks version directories whose minor falls strictly
     above the installed minor and at-or-below the target minor.
   - Each script runs via `bash` with `ROOT=<target_root>` in the
     environment and `cwd` set to `target_root`.
   - A bare `pkit` in a script reaches the running pkit: the runner puts a
     `pkit` of its own first on the script's `PATH`, and sets the migration
     marker, under which every command that changes the installation refuses
     (ADR-065 point 14).
   - A non-zero exit halts the run.

2. **Authoring-time coverage check** — `check_diff_coverage` walks a
   git diff for changes that require migrations (per COR-010's
   "Migrations are mandatory on adopter-breaking surface changes"
   rule) and verifies the same diff includes a matching migration
   script. CI gates the merge; the agent uses it pre-commit.

3. **Which version a migration targets** — a migration's folder names the
   version it carries a project to, never one already released: the runner
   runs a folder only past the version a project records. The stamp
   (`scaffolds.stamp_migration`) allocates past the released version
   (`migration_target`), and the check (`released_targets`) fails a script a
   change lands at or below it. Both read the released version through
   `recorded_version`, from a tree: the stamp from the default branch, as an
   allocator (COR-054 point 3), the check from its base's tip.

4. **Each number once in a folder** — the runner runs a folder's scripts in
   the order of their names, so their numbers order them only while each is
   used once. The stamp numbers past the highest in the folder, and the check
   (`number_clashes`) fails a script a change lands with a number its folder
   holds, read as merging the base would leave it.
"""

from __future__ import annotations

import contextlib
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Generator, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

import click
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import __version__, cli_render, lifecycle_ownership
from project_kit.friction_git import SHORT, CommitTree

_VERSION_DIR_RE = re.compile(r"^\d+\.\d+\.0$")

# The migration marker (ADR-065 point 14): the migration runner sets it in its
# scripts' environment, never in its own process. Every command that changes
# the installation refuses while it is set (`refuse_inside_migration`). The
# router never reads it.
MIGRATION_ENV = "PKIT_MIGRATION"

# The folder inside the project, ignored by `.pkit/.gitignore`, where the runner
# makes the folder of its `pkit` (ADR-065 point 14). The backbone declares its
# pattern (`visibility._BACKBONE_RUNTIME_IGNORE`), so step 3 of a transition
# renders it before the first migration runs.
RUNNER_PARENT = ".pkit/.migration-runner"

# The prefix of each run's own folder, in the project folder or the temporary one.
_RUNNER_PREFIX = "pkit-migration-"

# How long the probe of the runner's `pkit` may take before it counts as failed.
_PROBE_TIMEOUT_SECONDS = 120

# A path under one of these prefixes is considered kit-owned (changes
# propagate to adopters via sync or upgrade). Paths under prefix's
# component-owned subdir (project/, namespace=project, etc.) are excluded.
Tier = Literal["backbone", "adapter", "capability"]


def parse_version_tuple(value: str) -> tuple[int, int, int]:
    """Parse `X.Y.Z` into a comparable int tuple. Raises on malformed input."""
    parts = value.split(".")
    if len(parts) < 3:
        raise click.ClickException(f"version {value!r} is not in major.minor.patch form.")
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as exc:
        raise click.ClickException(f"version {value!r} has non-integer components.") from exc


# --- which version a migration targets (COR-010; #1754) ---------------

# A full commit id, as a pipeline names a base; a line names it shortened.
_FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

# A script the runner runs (`[0-9]*.sh`), the digits its name opens with as its number.
_SCRIPT_NUMBER_RE = re.compile(r"^(\d+).*\.sh$")

# A released version: `major.minor.patch`, with a pre-release or build suffix allowed.
_RELEASE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.+-]*)?$")

# Typed `Any`: ruamel.yaml ships its loader untyped.
_safe_yaml: Any = YAML(typ="safe")

# Reads one file of a tree by its path from the project root: its bytes, or `None`
# where the tree holds no such file.
TreeReader = Callable[[str], bytes | None]


def version_cell(tier: Tier, component: str | None) -> str:
    """The file, from the project root, holding the version a tier's release writes:
    `.pkit/VERSION` for the backbone, the component's `package.yaml` for an adapter or
    a capability (PRJ-002 D3)."""
    if tier == "backbone":
        return ".pkit/VERSION"
    folder = "adapters" if tier == "adapter" else "capabilities"
    return f".pkit/{folder}/{component}/package.yaml"


def tier_subject(tier: Tier, component: str | None) -> str:
    """How a message names a tier: `backbone`, or `capability <name>`."""
    return "backbone" if tier == "backbone" else f"{tier} {component}"


def recorded_version(tier: Tier, component: str | None, read: TreeReader) -> str | None:
    """The version a tree records for a tier, read through `read`, or `None` where the
    tree holds no such file. A file that records no `major.minor.patch` version
    refuses, naming it: whether a folder is released cannot be told without it."""
    cell = version_cell(tier, component)
    raw = read(cell)
    if raw is None:
        return None
    text = raw.decode("utf-8", "replace")
    value: object
    if tier == "backbone":
        value = text.strip()
    else:
        try:
            loaded: Any = _safe_yaml.load(text)
        except YAMLError as exc:
            raise click.ClickException(f"{cell} cannot be read as YAML: {exc}") from exc
        block = cast(dict[str, Any], loaded).get("component") if isinstance(loaded, dict) else None
        value = cast(dict[str, Any], block).get("version") if isinstance(block, dict) else None
    if not isinstance(value, str) or not _RELEASE_RE.match(value):
        raise click.ClickException(
            f"{cell} records no version in major.minor.patch form ({value!r})."
        )
    return value


def minor_of(version: str) -> tuple[int, int]:
    """The `(major, minor)` of a version, its patch and any suffix left out."""
    match = _RELEASE_RE.match(version)
    if match is None:
        raise click.ClickException(f"version {version!r} is not in major.minor.patch form.")
    return int(match.group(1)), int(match.group(2))


@dataclass(frozen=True)
class MigrationTarget:
    """The folder a migration stamped without a version goes in (`X.Y.0`), and why."""

    version: str
    reason: str


def migration_target(
    subject: str,
    released: str,
    where: str,
    *,
    own: str | None = None,
    folders: Iterable[str] = (),
) -> MigrationTarget:
    """The version a migration targets when none is given: never `released`'s minor or
    one below it, since a project at `released` never runs such a folder.

    It is the highest of: the next minor past `released`; the minor the working tree
    records (`own`), where it is above `released`, as on the branch of a project whose
    change bumps its own version; and the next major, where its folder already waits
    among `folders`, so a script written after a pending major change runs after that
    change's own migrations. A folder further ahead is never joined, since a change may
    target a later release on purpose (#465). The pending major is not predicted from
    changesets: the release computes the version (PRJ-002 D2/D3), and `release plan`
    warns where a folder does not match it. `subject` names the tier and `where` what
    records `released`, for the reason."""
    major, minor = minor_of(released)
    candidates: list[tuple[tuple[int, int], str]] = [
        ((major, minor + 1), f"the next minor past {subject} {released}, which {where} records")
    ]
    if own is not None and minor_of(own) > (major, minor):
        candidates.append(
            (
                minor_of(own),
                f"the version the working tree records for {subject}, {own}, above "
                f"{released} on {where}",
            )
        )
    if f"{major + 1}.0.0" in set(folders):
        candidates.append(
            (
                (major + 1, 0),
                f"the next major past {subject} {released}, whose folder {major + 1}.0.0/ "
                f"already waits",
            )
        )
    (target_major, target_minor), reason = max(candidates, key=lambda c: c[0])
    return MigrationTarget(f"{target_major}.{target_minor}.0", reason)


def version_folders(files: Iterable[str], root: str) -> set[str]:
    """The `X.Y.0` folders directly under `root` that hold a file, of the paths `files`."""
    prefix = root.rstrip("/") + "/"
    folders: set[str] = set()
    for rel in files:
        if rel.startswith(prefix):
            first = rel[len(prefix) :].split("/", 1)[0]
            if _VERSION_DIR_RE.match(first):
                folders.add(first)
    return folders


def pending_migration_scripts(
    migrations_root: Path,
    installed_version: str | None,
    target_version: str,
) -> list[Path]:
    """Collect migration scripts whose minor falls in (installed, target].

    `migrations_root` is the directory containing `<X.Y.0>/<NNN>-*.sh`
    subdirectories. Missing or non-versioned subdirectories are ignored.

    `installed_version` is the window's lower bound: for the backbone, the
    last completed transition (`completed_version`, ADR-065 point 3); for a
    component, the version its manifest records. `None` means no lower
    bound, and every shipped migration up to the target is pending. For the
    backbone that is the replay a missing completion runs once (point 5),
    which a backbone migration's contract makes safe over any state (COR-010).

    Returns scripts in execution order: version-dir ascending semver,
    then `NNN-*.sh` filename within each version-dir.
    """
    if not migrations_root.is_dir():
        return []

    target_minor = parse_version_tuple(target_version)[:2]
    if installed_version is None:
        installed_minor: tuple[int, int] = (-1, -1)
    else:
        installed_minor = parse_version_tuple(installed_version)[:2]

    scripts: list[Path] = []
    version_dirs = sorted(
        (p for p in migrations_root.iterdir() if p.is_dir() and _VERSION_DIR_RE.match(p.name)),
        key=lambda p: parse_version_tuple(p.name),
    )
    for version_dir in version_dirs:
        ver_minor = parse_version_tuple(version_dir.name)[:2]
        # Window: installed < version ≤ target. A minor below the
        # installed version is already applied; a minor above the target
        # version isn't shipping yet.
        if not (installed_minor < ver_minor <= target_minor):
            continue
        for script in sorted(version_dir.glob("[0-9]*.sh")):
            scripts.append(script)
    return scripts


def execute_migration_scripts(
    scripts: list[Path],
    target_root: Path,
    label: str,
    *,
    label_rel_to: Path | None = None,
) -> None:
    """Run scripts in order via bash with ROOT env var. Halts on non-zero exit.

    Each script reaches the running pkit by a bare `pkit` (ADR-065 point 14):
    `runner_pkit` puts a `pkit` of the runner's own first on the scripts'
    `PATH`, checks it answers with this pkit's version before the first script,
    and sets the migration marker. Its folder is removed on every exit.

    `label` names the migration set in user-facing messages (e.g.
    `"backbone"`, `"capability 'evidence'"`, `"adapter 'claude-code'"`).
    `label_rel_to` is a base path used to render script paths in the
    output relatively — typically the component's root directory.
    Defaults to each script's parent's parent (the migrations root).
    """
    if not scripts:
        return

    with runner_pkit(target_root, label) as env:
        for script in scripts:
            rel: Path | str
            if label_rel_to is not None:
                try:
                    rel = script.relative_to(label_rel_to)
                except ValueError:
                    rel = script
            else:
                rel = script.name
            click.echo(f"    • {rel}")
            result = subprocess.run(
                ["bash", str(script)],
                env=env,
                cwd=target_root,
            )
            if result.returncode != 0:
                raise click.ClickException(
                    f"{label} migration {rel} exited with status {result.returncode}. "
                    f"Run halted — state may be inconsistent. Resolve the migration's "
                    f"failure mode (likely an unmet precondition or non-idempotent script) "
                    f"and re-run."
                )


# --- the runner's `pkit` and the migration marker (ADR-065 point 14) ----------


def refuse_inside_migration(command: str) -> None:
    """Stop a command that changes the installation when a migration runs it.

    The migration runner sets the marker (`MIGRATION_ENV`) in its scripts'
    environment. A command that propagates, seeds or merges, moves a recorded
    version, writes the pin, or changes the installed components calls this
    first, before it reads or writes anything, under `--dry-run` too. Any value
    but an empty one refuses, and nothing overrides it. A reading command never
    calls it (ADR-065 point 14).
    """
    if not os.environ.get(MIGRATION_ENV, ""):
        return
    raise click.ClickException(
        f"refusing to run `pkit {command}` inside a migration ({MIGRATION_ENV} is set): "
        "a migration never changes the installation it runs in (ADR-065 point 14). "
        "Nothing was written, and no flag overrides this refusal."
    )


@contextlib.contextmanager
def runner_pkit(target_root: Path, label: str) -> Generator[dict[str, str]]:
    """The environment of a set of migration scripts, with the runner's `pkit`
    first on its `PATH`, for the length of the block (ADR-065 point 14).

    The runner's `pkit` runs this pkit's code under this interpreter, with
    `-P`, so the project's root never shadows the package, and never enters
    the router. It lies in a fresh folder of its own inside `RUNNER_PARENT`,
    which `.pkit/.gitignore` ignores. Before the first script the runner asks
    a bare `pkit` for its version, as a script would. The answer counts only
    when the runner's own `pkit` gave it, with this pkit's version. Where the
    project folder cannot be made or written, or is not a folder only this
    user can write, or its `pkit` gives no such answer, the runner makes its
    folder in the temporary folder and asks again. A failure there too stops
    the run before any script runs. The environment also holds `ROOT` and the
    migration marker. Its folder is removed on every exit, and the project
    folder too once it is empty.
    """
    project_parent = target_root / RUNNER_PARENT
    failures: list[str] = []
    for parent in (project_parent, None):
        try:
            folder = _make_runner_folder(parent)
        except OSError as exc:
            failures.append(f"{_display(parent, target_root)}: {exc.strerror or exc}")
            continue
        try:
            env = _scripts_environment(target_root, folder)
            failed = _probe_runner_pkit(env, target_root, folder)
            if failed is None:
                yield env
                return
        finally:
            _remove_runner_folder(folder, parent)
        failures.append(f"{_display(folder, target_root)}: {failed}")
    lines = [
        f"the migration runner's `pkit` cannot run, so no {label} migration ran "
        "(ADR-065 point 14).",
        f"In the project: {failures[0]}",
        f"In the temporary folder: {failures[-1]}",
        "A folder that forbids running files is the usual cause. Set TMPDIR to a folder "
        "where files can run, which chooses where the temporary folder lies, and run the "
        "command again.",
    ]
    raise click.ClickException("\n       ".join(lines))


def _make_runner_folder(parent: Path | None) -> Path:
    """A fresh folder holding the runner's `pkit`, in `parent`, or in the
    temporary folder when `parent` is None. The project folder is made only
    inside an existing `.pkit/`, and used only when it is a folder, not a
    link, that this user owns and no one else can write."""
    if parent is not None:
        with contextlib.suppress(FileExistsError):
            parent.mkdir(mode=0o700)
        held = os.lstat(parent)
        if (
            not stat.S_ISDIR(held.st_mode)
            or held.st_uid != os.getuid()
            or held.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise OSError(f"not a folder that only this user owns and can write: {parent}")
    folder = Path(tempfile.mkdtemp(prefix=_RUNNER_PREFIX, dir=parent))
    try:
        shim = folder / "pkit"
        shim.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -P -m project_kit "$@"\n',
            encoding="utf-8",
        )
        shim.chmod(0o755)
    except OSError:
        _remove_runner_folder(folder, parent)
        raise
    return folder


def _scripts_environment(target_root: Path, folder: Path) -> dict[str, str]:
    """The inherited environment, with `ROOT`, the runner's `pkit` first on
    `PATH`, and the migration marker."""
    env = dict(os.environ)
    inherited = env.get("PATH") or os.defpath
    env["PATH"] = f"{folder}{os.pathsep}{inherited}"
    env["ROOT"] = str(target_root)
    env[MIGRATION_ENV] = "1"
    return env


def _probe_runner_pkit(env: dict[str, str], target_root: Path, folder: Path) -> str | None:
    """None when a bare `pkit`, run as a script runs it, is the runner's own in
    `folder` and answers with this pkit's version; otherwise what it found or
    answered, or why it could not run. A folder whose path holds the `PATH`
    separator splits on `PATH`, so it never counts. Another `pkit` found first
    is never run."""
    shim = str(folder / "pkit")
    if os.pathsep in str(folder):
        return f"its path holds {os.pathsep!r}, which splits it on PATH"
    try:
        found = _bash(env, target_root, "command -v pkit").stdout.strip()
        if found != shim:
            return f"a bare `pkit` is {found or 'not found'}, not the runner's {shim}"
        probe = _bash(env, target_root, "pkit --version")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)
    answer = probe.stdout.strip()
    if probe.returncode == 0 and answer.split()[-1:] == [__version__]:
        return None
    errors = probe.stderr.strip().splitlines()
    said = answer or (errors[-1] if errors else "nothing")
    return f"`pkit --version` exited {probe.returncode} and said {said!r}, not {__version__}"


def _bash(env: dict[str, str], target_root: Path, command: str) -> subprocess.CompletedProcess[str]:
    """Run one probe command as a script's shell would: bash, the scripts'
    environment, the project's root as the working folder."""
    return subprocess.run(
        ["bash", "-c", command],
        env=env,
        cwd=target_root,
        capture_output=True,
        text=True,
        timeout=_PROBE_TIMEOUT_SECONDS,
        check=False,
    )


def _remove_runner_folder(folder: Path, parent: Path | None) -> None:
    """Remove the run's folder, and the project folder once it is empty."""
    shutil.rmtree(folder, ignore_errors=True)
    if parent is not None:
        with contextlib.suppress(OSError):
            parent.rmdir()


def _display(path: Path | None, target_root: Path) -> str:
    """A folder as the stop names it: relative to the project where it lies
    inside it, and the temporary folder itself where none could be made there."""
    if path is None:
        try:
            return tempfile.gettempdir()
        except OSError:
            return "the temporary folder, which cannot be found"
    try:
        return str(path.relative_to(target_root))
    except ValueError:
        return str(path)


def report_pending_migrations(
    scripts: list[Path],
    label: str,
    installed_version: str | None,
    target_version: str,
    *,
    dry_run: bool,
    label_rel_to: Path | None = None,
) -> None:
    """Print what migrations would run, without executing."""
    if not scripts:
        return
    verb = "would run" if dry_run else "running"
    click.echo(
        f"  {verb} {len(scripts)} migration(s) for {label} "
        f"({installed_version or 'unknown'} -> v{target_version})"
    )
    for script in scripts:
        rel: Path | str
        if label_rel_to is not None:
            try:
                rel = script.relative_to(label_rel_to)
            except ValueError:
                rel = script
        else:
            rel = script.name
        click.echo(f"    • {rel}")


# --- authoring-time coverage check (per COR-010 + rules/core.md #7) ----


@dataclass(frozen=True)
class DiffTrigger:
    """A change in the diff that requires a migration."""

    kind: Literal["rename", "delete"]
    path: str  # destination path (for renames) or removed path (for deletes)
    old_path: str | None  # source path for renames; None for deletes
    tier: Tier
    component: str | None  # adapter/capability name; None for backbone


@dataclass(frozen=True)
class DiffMigration:
    """A migration script newly added in the diff."""

    path: str
    tier: Tier
    component: str | None


@dataclass(frozen=True)
class CoverageReport:
    """Result of a `check_diff_coverage` run.

    `landed` is each migration script the diff adds, or moves in by a rename: what
    `released_targets` judges."""

    triggers: tuple[DiffTrigger, ...]
    migrations: tuple[DiffMigration, ...]
    landed: tuple[str, ...] = ()

    @property
    def is_covered(self) -> bool:
        """Covered iff every (tier, component) with triggers has a matching migration."""
        if not self.triggers:
            return True
        trigger_keys = {(t.tier, t.component) for t in self.triggers}
        migration_keys = {(m.tier, m.component) for m in self.migrations}
        return trigger_keys.issubset(migration_keys)

    @property
    def uncovered_keys(self) -> list[tuple[Tier, str | None]]:
        """List of (tier, component) keys with triggers but no matching migration."""
        trigger_keys = {(t.tier, t.component) for t in self.triggers}
        migration_keys = {(m.tier, m.component) for m in self.migrations}
        return sorted(trigger_keys - migration_keys)


def check_diff_coverage(
    target_root: Path,
    base_ref: str,
    *,
    include_working_tree: bool = False,
) -> CoverageReport:
    """Walk the diff between `base_ref` and the project state; identify triggers + new migrations.

    By default the diff is `<base_ref>...HEAD` — committed branch changes
    only (what CI sees on a PR). With `include_working_tree=True`, the
    diff is `<base_ref>` against the working tree — captures committed
    + staged + unstaged changes (what's about to be committed). The
    pre-commit form for local use.

    Returns a CoverageReport. Callers (CLI / CI gate) check
    `report.is_covered` and surface `report.uncovered_keys` to the
    author when False.
    """
    entries = _git_diff_name_status(
        target_root, base_ref, include_working_tree=include_working_tree
    )
    triggers: list[DiffTrigger] = []
    migrations: list[DiffMigration] = []
    landed: list[str] = []
    for status, path, old_path in entries:
        if status == "A" and _is_migration_path(path):
            migrations.append(
                DiffMigration(
                    path=path,
                    tier=_migration_path_tier(path),
                    component=_migration_path_component(path),
                )
            )
            landed.append(path)
            continue
        if status == "R" and _is_migration_path(path):
            # A script moved into a folder lands there as an added one does.
            landed.append(path)
            continue
        if _is_migration_path(path):
            # Renames / deletes within a migrations dir don't trigger;
            # they're internal bookkeeping.
            continue
        if _is_decision_path(path):
            # Decision records (COR / PRJ / DEC) are kit-owned reference
            # content refreshed wholesale on sync — treecopy orphan-prunes a
            # removed/renamed record — so a rename or delete is never
            # adopter-breaking and triggers no migration.
            continue
        tier_info = _classify_path(path)
        if tier_info is None:
            continue
        if status == "D":
            triggers.append(
                DiffTrigger(
                    kind="delete",
                    path=path,
                    old_path=None,
                    tier=tier_info[0],
                    component=tier_info[1],
                )
            )
        elif status == "R":
            triggers.append(
                DiffTrigger(
                    kind="rename",
                    path=path,
                    old_path=old_path,
                    tier=tier_info[0],
                    component=tier_info[1],
                )
            )
    return CoverageReport(
        triggers=tuple(triggers), migrations=tuple(migrations), landed=tuple(landed)
    )


@dataclass(frozen=True)
class ReleasedTarget:
    """A migration script a change lands in a folder its tier has already released, or
    whose tier's version the base records in no readable form; `line` says which."""

    path: str
    tier: Tier
    component: str | None
    line: str


def released_targets(
    target_root: Path,
    landed: Sequence[str],
    *,
    base: str,
    tip: str,
    head: str | None = None,
) -> tuple[ReleasedTarget, ...]:
    """Each script of `landed` whose folder's minor is at or below the version its tier
    records at the base's tip `tip`, so a project already there never runs it.

    The tip, not the branch point: a release that lands after the branch was cut
    releases the folder all the same. A script in no `X.Y.0` folder has no version to
    judge. Skipped: a script the project receives by sync (`is_synced_copy`), and one
    the tip already holds, which the change did not bring: at its path, or under
    another name in its folder with the same content, as a rename leaves it. A tier
    the tip records no version for, such as a component the change adds, has nothing
    released. The script's content is read at commit `head`, or from the working tree
    when `head` is `None`. `base` is the base as named, for the line, a commit id
    shortened."""
    judged = [path for path in landed if _VERSION_DIR_RE.match(PurePosixPath(path).parent.name)]
    if not judged:
        return ()
    ownership = lifecycle_ownership.load_ownership(target_root)
    judged = [
        path
        for path in judged
        if ownership is None or not ownership.is_synced_copy(target_root, path)
    ]
    if not judged:
        return ()
    tree = CommitTree(target_root, tip)
    held = tree.files()
    held_set = set(held)
    head_tree = CommitTree(target_root, head) if head is not None else None
    if _FULL_COMMIT_RE.match(base):
        base = base[:SHORT]

    def read(rel: str) -> bytes | None:
        return tree.read_bytes([rel])[rel]

    def renamed(path: str) -> bool:
        """The tip holds the script's very content under another name in its folder."""
        if head_tree is not None:
            content = head_tree.read_bytes([path])[path]
        else:
            file = target_root / path
            content = file.read_bytes() if file.is_file() else None
        folder = PurePosixPath(path).parent
        beside = [rel for rel in held if PurePosixPath(rel).parent == folder]
        return content is not None and content in tree.read_bytes(beside).values()

    found: list[ReleasedTarget] = []
    for path in judged:
        if path in held_set:
            continue
        tier, component = _migration_path_tier(path), _migration_path_component(path)
        folder = PurePosixPath(path).parent.name
        label = tier + (":" + component if component else "")
        subject = tier_subject(tier, component)
        try:
            released = recorded_version(tier, component, read)
        except click.ClickException as exc:
            said = exc.message.rstrip(".")
            line = (
                f"[{label}] {path}: at {base}, {said}, so whether {folder} is released "
                f"cannot be told."
            )
            found.append(ReleasedTarget(path, tier, component, line))
            continue
        if released is None or minor_of(folder) > minor_of(released) or renamed(path):
            continue
        root = PurePosixPath(path).parent.parent.as_posix()
        upcoming = migration_target(subject, released, base, folders=version_folders(held, root))
        line = (
            f"[{label}] {path}: targets {folder}, but {base} already records {subject} "
            f"{released}, so a project at {released} never runs it. Move it to "
            f"{upcoming.version}/ or a later folder."
        )
        found.append(ReleasedTarget(path, tier, component, line))
    return tuple(found)


def script_number(name: str) -> int | None:
    """The number of a script the runner runs (`[0-9]*.sh`): the digits its file name
    opens with. `None` for a file the runner does not run."""
    match = _SCRIPT_NUMBER_RE.match(name)
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class NumberClash:
    """A migration script a change lands whose number another script in its folder
    holds; `line` names the other and the number to take."""

    path: str
    tier: Tier
    component: str | None
    line: str


def number_clashes(
    target_root: Path,
    landed: Sequence[str],
    *,
    base: str,
    fork: str,
    tip: str,
    head: str | None = None,
) -> tuple[NumberClash, ...]:
    """Each script of `landed` whose number another script in its folder holds. The
    runner runs a folder's scripts in the order of their names, so two of one number
    run in the order the rest of their names gives, which nobody chose.

    The folder is read as merging the base would leave it: its scripts at commit
    `head`, or in the working tree when `head` is `None`, less those the base's tip
    `tip` removed since the branch point `fork`, and with those the tip added since.
    So a number another change took on the base since the branch left it clashes
    too. Of two scripts the change lands with one number and no other beside them,
    only the later by name is named, so one renumbering mends it. Each script named
    is told a number of its own past the folder's highest. Skipped: a script
    in no `X.Y.0` folder, a file the runner does not run, and a script the project
    receives by sync (`is_synced_copy`). `base` is the base as named, for the line, a
    commit id shortened."""
    judged = [
        path
        for path in landed
        if _VERSION_DIR_RE.match(PurePosixPath(path).parent.name)
        and script_number(PurePosixPath(path).name) is not None
    ]
    if not judged:
        return ()
    ownership = lifecycle_ownership.load_ownership(target_root)
    judged = [
        path
        for path in judged
        if ownership is None or not ownership.is_synced_copy(target_root, path)
    ]
    if not judged:
        return ()
    folders = {PurePosixPath(path).parent.as_posix() for path in judged}
    at_head = _folder_scripts(target_root, head, folders)
    at_tip = _folder_scripts(target_root, tip, folders)
    at_fork = at_tip if fork == tip else _folder_scripts(target_root, fork, folders)
    taken_since = at_tip - at_fork
    merged = (at_head - (at_fork - at_tip)) | taken_since
    if _FULL_COMMIT_RE.match(base):
        base = base[:SHORT]

    def number(rel: str) -> int:
        return script_number(PurePosixPath(rel).name) or 0

    def named(rel: str) -> str:
        name = PurePosixPath(rel).name
        return f"{name} ({base} took it since this branch left it)" if rel in taken_since else name

    found: list[NumberClash] = []
    # The number each folder hands out next: one past its highest, then on, so two
    # scripts named in one folder are never told to take one number.
    upcoming: dict[str, int] = {}
    for path in sorted(judged):
        folder = PurePosixPath(path).parent.as_posix()
        beside = sorted(
            {*(r for r in merged if PurePosixPath(r).parent.as_posix() == folder), path}
        )
        others = [rel for rel in beside if rel != path and number(rel) == number(path)]
        if not others or (all(rel in judged for rel in others) and path < min(others)):
            continue
        take = upcoming.get(folder, max(number(rel) for rel in beside) + 1)
        upcoming[folder] = take + 1
        tier, component = _migration_path_tier(path), _migration_path_component(path)
        label = tier + (":" + component if component else "")
        line = (
            f"[{label}] {path}: its number {number(path):03d} is also held by "
            f"{' and '.join(named(rel) for rel in others)}, so the order they run in falls "
            f"to the rest of their names. Renumber it to {take:03d}, a number its folder "
            f"does not hold."
        )
        found.append(NumberClash(path, tier, component, line))
    return tuple(found)


def _folder_scripts(target_root: Path, ref: str | None, folders: set[str]) -> set[str]:
    """The scripts the runner runs in `folders`, each a path from the project root: at
    commit `ref`, or in the working tree when `ref` is `None`."""
    if ref is None:
        return {
            f"{folder}/{file.name}"
            for folder in folders
            if (target_root / folder).is_dir()
            for file in (target_root / folder).iterdir()
            if file.is_file() and script_number(file.name) is not None
        }
    return {
        rel
        for rel in CommitTree(target_root, ref).files()
        if PurePosixPath(rel).parent.as_posix() in folders
        and script_number(PurePosixPath(rel).name) is not None
    }


def _git_diff_name_status(
    target_root: Path, base_ref: str, *, include_working_tree: bool = False
) -> list[tuple[str, str, str | None]]:
    """Run `git diff --name-status` against `base_ref`. Returns (status, path, old_path?).

    `include_working_tree=False` (default): committed-only diff
    (`<base>...HEAD`). Matches CI's view of the PR.

    `include_working_tree=True`: base vs working tree (`<base>`).
    Includes committed + staged + unstaged changes. For pre-commit use.
    """
    target = base_ref if include_working_tree else f"{base_ref}...HEAD"
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", target],
            cwd=str(target_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git diff against {base_ref!r} failed: {exc.stderr or exc.stdout}".strip()
        ) from exc
    entries: list[tuple[str, str, str | None]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status_code = parts[0]
        kind = status_code[0]
        if kind == "R" and len(parts) >= 3:
            entries.append(("R", parts[2], parts[1]))
        elif kind == "C" and len(parts) >= 3:
            entries.append(("A", parts[2], None))
        elif len(parts) >= 2:
            entries.append((kind, parts[1], None))
    return entries


def _is_decision_path(path: str) -> bool:
    """True if `path` is a decision record (COR / PRJ / DEC).

    Decision records are kit-owned reference content; `pkit sync` refreshes the
    set wholesale (treecopy prunes orphaned/renamed records), and no
    adopter-owned state references a record by filename. So renaming or removing
    one is never adopter-breaking — it owes no migration. Matches the core /
    project decision area and every capability's `decisions/` subtree.
    """
    if path.startswith(".pkit/decisions/"):
        return True
    parts = path.split("/")
    return (
        len(parts) >= 4
        and parts[0] == ".pkit"
        and parts[1] == "capabilities"
        and parts[3] == "decisions"
    )


def _classify_path(path: str) -> tuple[Tier, str | None] | None:
    """Classify a path's tier + component, or None if not kit-owned."""
    # Adopter-owned subtrees: skip.
    if path.startswith(".pkit/decisions/project/"):
        return None
    if path.startswith(".pkit/skills/project/"):
        return None
    if path.startswith(".pkit/agents/project/"):
        return None
    if path.startswith(".pkit/scratchpad/"):
        return None
    if path == ".pkit/rules/project.md":
        return None
    if path.startswith(".pkit/workflow/project/"):
        return None

    # Component subtrees.
    # NB: per COR-027 the bundle pattern is retired; deletion of `.pkit/workflow/`
    # paths falls through to backbone-tier inference below (the workflow area
    # itself is being removed by COR-027).

    if path.startswith(".pkit/adapters/"):
        parts = path.split("/", 4)
        if len(parts) >= 3:
            component = parts[2]
            if len(parts) >= 4 and parts[3] == "project":
                return None
            return ("adapter", component)

    if path.startswith(".pkit/capabilities/"):
        parts = path.split("/", 4)
        if len(parts) >= 3:
            component = parts[2]
            if len(parts) >= 4 and parts[3] == "project":
                return None
            return ("capability", component)

    # Backbone-tier trees.
    backbone_prefixes = (
        ".pkit/decisions/core/",
        ".pkit/skills/core/",
        ".pkit/agents/core/",
        ".pkit/lifecycle/",
        ".pkit/schemas/",
        ".pkit/cli/",
        ".pkit/migrations/",
        ".pkit/workflow/",  # legacy: the workflow area was retired in COR-027;
        # deletions of leftover content trigger backbone migrations.
    )
    for prefix in backbone_prefixes:
        if path.startswith(prefix):
            return ("backbone", None)
    if path == ".pkit/rules/core.md":
        return ("backbone", None)
    return None


def _is_migration_path(path: str) -> bool:
    """True if path is an actual migration script under any tier's `migrations/` dir.

    Migration scripts are `*.sh` or `*.py` files inside a per-version
    directory like `<X.Y.0>/`. Other content inside migrations/
    (`.gitkeep`, READMEs, etc.) doesn't count — they're scaffolding,
    not migrations.
    """
    if not path.startswith(".pkit/"):
        return False
    is_in_migrations = path.startswith(".pkit/migrations/") or "/migrations/" in path
    if not is_in_migrations:
        return False
    # Restrict to the per-version dir's script files.
    return path.endswith(".sh") or path.endswith(".py")


def _migration_path_tier(path: str) -> Tier:
    """Determine the tier of a migration script."""
    if path.startswith(".pkit/migrations/"):
        return "backbone"
    if path.startswith(".pkit/adapters/"):
        return "adapter"
    if path.startswith(".pkit/capabilities/"):
        return "capability"
    return "backbone"


def _migration_path_component(path: str) -> str | None:
    """Extract the component name from a migration script path; None for backbone."""
    if path.startswith(".pkit/adapters/"):
        parts = path.split("/", 3)
        return parts[2] if len(parts) >= 3 else None
    if path.startswith(".pkit/capabilities/"):
        parts = path.split("/", 3)
        return parts[2] if len(parts) >= 3 else None
    return None


def render_coverage_report(report: CoverageReport) -> None:
    """Render a CoverageReport to stdout in CLI-friendly form."""
    click.echo()
    if not report.triggers:
        click.echo("  No migration-triggering changes in diff.")
        if report.migrations:
            click.echo(
                f"  ({len(report.migrations)} migration script(s) "
                f"in diff, no triggers — that's fine.)"
            )
        click.echo()
        return

    click.echo(
        "  " + cli_render.style("strong", f"{len(report.triggers)} migration trigger(s) in diff:")
    )
    for t in report.triggers:
        tier_label = t.tier + (":" + t.component if t.component else "")
        if t.kind == "rename":
            click.echo(f"    [{tier_label}] rename: {t.old_path} → {t.path}")
        else:
            click.echo(f"    [{tier_label}] delete: {t.path}")
    click.echo()

    if report.migrations:
        click.echo(
            "  "
            + cli_render.style("heading", f"{len(report.migrations)} migration script(s) in diff:")
        )
        for m in report.migrations:
            tier_label = m.tier + (":" + m.component if m.component else "")
            click.echo(f"    [{tier_label}] {m.path}")
        click.echo()

    if report.is_covered:
        click.echo(
            "  "
            + cli_render.style(
                "strong",
                "Verdict: COVERED (every tier:component with triggers has a matching migration).",
            )
        )
    else:
        click.echo(
            "  "
            + cli_render.style(
                "strong",
                "Verdict: UNCOVERED. Author migrations for the following tiers before merging:",
            )
        )
        for tier, component in report.uncovered_keys:
            tier_label = tier + (":" + component if component else "")
            click.echo(f"    - {tier_label}")
    click.echo()


def render_released_targets(found: Sequence[ReleasedTarget]) -> None:
    """Render what `released_targets` found, with its own verdict; nothing when it found
    nothing."""
    if not found:
        return
    click.echo(
        "  "
        + cli_render.style(
            "strong", f"{len(found)} migration script(s) in diff target a released version:"
        )
    )
    for target in found:
        click.echo(f"    {target.line}")
    click.echo()
    click.echo(
        "  "
        + cli_render.style(
            "strong",
            "Verdict: RELEASED. Move each script above to a version not yet released "
            "before merging.",
        )
    )
    click.echo()


def render_number_clashes(found: Sequence[NumberClash]) -> None:
    """Render what `number_clashes` found, with its own verdict; nothing when it found
    nothing."""
    if not found:
        return
    click.echo(
        "  "
        + cli_render.style(
            "strong",
            f"{len(found)} migration script(s) in diff take a number their folder holds:",
        )
    )
    for clash in found:
        click.echo(f"    {clash.line}")
    click.echo()
    click.echo(
        "  "
        + cli_render.style(
            "strong",
            "Verdict: NUMBER TAKEN. Renumber each script above before merging.",
        )
    )
    click.echo()
