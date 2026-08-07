"""The `pkit` entry-point router (ADR-039).

The installed `pkit` binary is CWD- and pin-aware: on every invocation it
picks one of three routes, **cheap-first** — the routing decision is made here,
in stdlib-only code, *before* the heavy CLI (`click` / `ruamel` / the command
tree) is imported. Only the fall-through route pays that import.

Three routes, in order:

1. **Source checkout → exec the in-tree dispatcher.** When the current directory
   resolves inside a project-kit *source checkout*, exec that checkout's
   `.pkit/cli/pkit`, so the working tree runs and the deploy-primitive bypass
   survives. This folds in the one capability the retired `scripts/pkit-router`
   shim delivered.

2. **Project pins a version ≠ me → re-exec the pinned wheel.** When the enclosing
   *adopter* project pins a version (its `.pkit/version-pin` directive, per
   ADR-049) different from this binary's, run the command under `uvx …@<pin>`
   instead. Sound only because ADR-033 version-locks bundled content to the
   binary: the pinned wheel brings code *and* content from the same tag, so they
   cannot diverge.

3. **Match, or no pin, or not in a project → run self.** Import the CLI and run
   in-process.

Two escape hatches keep this safe: `PKIT_NO_ROUTE=1` bypasses routing entirely
(run self), and `PKIT_ROUTED=1` is the loop guard the re-exec'd process inherits
so it cannot route again. An unresolvable pin degrades **loudly to running
self** — it never hard-fails a routine command (ADR-039 D2).

This module deliberately imports only the standard library at module scope; the
heavy CLI import lives inside `_run_self()`, reached only on route 3.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Bypass: set by an operator to force in-process execution and skip all routing.
_BYPASS_ENV = "PKIT_NO_ROUTE"
# Loop guard: set on the environment of every re-exec so the child process does
# not route again (belt-and-suspenders against an infinite re-route, and it also
# stops a routine `pkit` subprocess spawned inside an already-pinned run from
# re-resolving the pin). Only route 2 sets it — route 1's dispatcher runs
# `python -m project_kit`, which never enters this router.
_LOOP_GUARD_ENV = "PKIT_ROUTED"

# The PRJ-004 canonical distribution URL. Route 2 pins by git tag `v<version>`
# appended after `@` (PRJ-004's tag-pinning form); tag⟺`.pkit/VERSION`
# correspondence is a release-discipline property owned by #464 (ADR-039 D3).
DISTRIBUTION_GIT_URL = "git+ssh://git@github.com/aleskalfas/project-kit.git"

# The project-owned pin directive (ADR-049). Its *presence* opts a project into
# per-project version pinning: the router reads it as the pin source and re-execs
# `uvx project-kit@<pin>` (route 2) so the pinned version serves every command. A
# plain one-line text file — a version, or a PRJ-004 tag/branch/sha token —
# project-owned and never kit-synced. Deliberately NOT `.pkit/VERSION`: that file
# records the *source tree's* own identity (route 1's CLI-version stamp), a
# different concern from the forward-looking run directive this file carries.
_PIN_FILE = "version-pin"

# Provenance override the CLI honours first (see the pm capability's
# provenance.py `_read_cli_version`). Route 1 sets it to the checkout's
# `.pkit/VERSION` so provenance reports `cli == tree`: in a source checkout the
# running *code* is the tree, but package metadata can lag a `.pkit/VERSION`-only
# bump (uv's build cache is keyed on `.py` changes, not the VERSION file), which
# otherwise surfaces as a spurious `cli ≠ tree` drift. Only route 1 sets it —
# on the pinned (route 2) and self (route 3) paths metadata is already accurate,
# so a genuine installed-CLI-vs-tree drift must still show.
_CLI_VERSION_ENV = "PKIT_CLI_VERSION"


def main(argv: list[str] | None = None) -> None:
    """Console-script entry point: route, then run whichever process should serve.

    `argv` defaults to the real process arguments; it is a parameter only so the
    routing decision is unit-testable without spawning a process.
    """
    resolved_argv = list(sys.argv[1:]) if argv is None else list(argv)
    if not _routing_suppressed(os.environ):
        # `_route` execs or `sys.exit`s when it takes route 1 or 2; it returns
        # only when the right answer is "run self" (route 3, or a loud degrade).
        _route(resolved_argv, os.environ)
    _run_self()


def _route(argv: list[str], environ) -> None:  # type: ignore[no-untyped-def]
    """Select and take a route. Returns iff the caller should run self."""
    root = _enclosing_project(Path.cwd())
    if root is None:
        return  # not inside any project → run self (a global pkit works anywhere)

    if is_source_checkout(root):
        # Route 1. Execs the dispatcher and never returns; on a broken checkout
        # (dispatcher missing / not executable) it warns and returns so we run
        # self rather than silently misrouting — we do NOT fall on to a pin.
        _exec_source_dispatcher(root, argv, environ)
        return

    # Route 2 candidate: an adopter project. It pins a version via its
    # `.pkit/version-pin` directive (ADR-049); a mismatch against this binary
    # means run the pin.
    pin = _resolve_pin(root)
    if pin is None:
        return  # no pin → run self
    running = running_version()
    if pin == running:
        return  # route 3 (match) → run self
    _run_pinned(pin, running, argv, environ)  # sys.exit on run; returns on degrade


# --- Routing predicates (all stdlib, all cheap) --------------------------------


def _routing_suppressed(environ) -> bool:  # type: ignore[no-untyped-def]
    """True when routing must be skipped: operator bypass or the loop guard."""
    return _env_true(environ, _BYPASS_ENV) or _env_true(environ, _LOOP_GUARD_ENV)


def _env_true(environ, name: str) -> bool:  # type: ignore[no-untyped-def]
    """True when an env var is set to a truthy value (`1` / `true` / `yes`)."""
    return environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def _enclosing_project(start: Path) -> Path | None:
    """Walk up from `start` to the first dir that looks like a project root.

    A project boundary is a `.pkit/` directory or a `.git` entry (dir or the
    worktree-marker file) — the same boundary `find_target_root` uses. Pure
    filesystem walk, no `git` subprocess: cheaper on the hot path than spawning
    a process, and it needs no external tool.
    """
    cur = start.resolve()
    while True:
        if (cur / ".pkit").is_dir() or (cur / ".git").exists():
            return cur
        if cur == cur.parent:
            return None
        cur = cur.parent


def is_source_checkout(root: Path) -> bool:
    """True iff `root` is a project-kit *source checkout* (not an adopter).

    The discriminator is the Python package source plus the in-tree dispatcher.
    An adopter has `.pkit/cli/pkit` too, but never `src/project_kit/` — so this
    fires only inside a real checkout, never in an adopter repo where execing
    the dispatcher (which `uv run`s a project-kit package that isn't there)
    would fail.
    """
    return (
        (root / "src" / "project_kit" / "__init__.py").is_file()
        and (root / ".pkit" / "cli" / "pkit").is_file()
    )


def _resolve_pin(root: Path) -> str | None:
    """The version a project pins via its `.pkit/version-pin` directive (ADR-049).

    ADR-039 left the pin source to the implementation; ADR-049 fills that slot
    with a dedicated, project-owned directive file (`.pkit/version-pin`) rather
    than `.pkit/VERSION` — the pin is a forward-looking *directive* the operator
    sets, distinct from `.pkit/VERSION`'s role as the *source tree's* identity.
    Returns None when there is no readable, non-empty pin file (→ no pin → run
    self), which is every un-pinned project's state.
    """
    return read_version_pin(root)


def pin_file_path(root: Path) -> Path:
    """The path to a project's `.pkit/version-pin` directive under `root` (ADR-049)."""
    return root / ".pkit" / _PIN_FILE


def read_version_pin(root: Path) -> str | None:
    """Read `root/.pkit/version-pin`, stripped; None when missing/unreadable/empty.

    Cheap and stdlib-only — a plain file read on the pre-click hot path
    (ADR-039), mirroring `_read_pkit_version`. This is the pin *source* the
    router honours (ADR-049); it is the sole reader of the pin directive shared
    by the router (route 2) and the `pin` / `upgrade` gestures.
    """
    try:
        text = pin_file_path(root).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def is_routed_child(environ) -> bool:  # type: ignore[no-untyped-def]
    """True when this process was re-exec'd by the router into a pinned version.

    The router sets the loop-guard env on the child it re-execs (route 2). A
    routed child that runs `pkit upgrade` cannot mutate the global tool from
    inside the pinned version, so it auto-advances its own pin to the latest
    release through the router bypass instead (ADR-049)."""
    return _env_true(environ, _LOOP_GUARD_ENV)


def is_route_bypassed(environ) -> bool:  # type: ignore[no-untyped-def]
    """True when routing was explicitly bypassed via PKIT_NO_ROUTE.

    Set by `run_bypassed` on the child it bootstraps (ADR-049). A `pkit upgrade`
    reached this way is the target version's own reconcile run *under* a pin
    raise, not a top-level upgrade — so it skips the redundant ADR-044 tool
    staleness probe (which would issue a second `git ls-remote` and print a
    nonsensical "tool is current" line mid-raise)."""
    return _env_true(environ, _BYPASS_ENV)


def _read_pkit_version(root: Path) -> str | None:
    """Read `root/.pkit/VERSION`, stripped; None when missing/unreadable/empty.

    Defensive and stdlib-only — a plain file read, cheap enough for the hot path
    (ADR-039). Reads the *source tree's* identity for the route-1 CLI-version
    stamp; the route-2 pin source is `read_version_pin` (ADR-049), a separate
    file — the two are deliberately distinct concerns.
    """
    try:
        text = (root / ".pkit" / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def running_version() -> str:
    """This binary's version. `project_kit.__init__` is import-light (it only
    reads a VERSION file), so this stays off the heavy-import path."""
    from project_kit import __version__

    return __version__


# --- Route executors -----------------------------------------------------------


def _exec_source_dispatcher(root: Path, argv: list[str], environ) -> None:  # type: ignore[no-untyped-def]
    """Route 1: exec the checkout's `.pkit/cli/pkit`. Returns only on degrade.

    Sets no loop guard: the dispatcher runs `python -m project_kit`, which does
    not re-enter this router, and leaving the guard unset preserves the retired
    shim's behaviour where a `pkit` subprocess spawned inside the checkout still
    runs the working tree.
    """
    dispatcher = root / ".pkit" / "cli" / "pkit"
    if os.access(dispatcher, os.X_OK):
        _stamp_cli_version(root, environ)
        os.execv(str(dispatcher), [str(dispatcher), *argv])  # replaces this process
    _warn(
        f"source checkout at {root} but {dispatcher} is missing or not "
        f"executable — running this binary ({running_version()}) instead. "
        f"Re-run `pkit sync` to restore the dispatcher."
    )


def _stamp_cli_version(root: Path, environ) -> None:  # type: ignore[no-untyped-def]
    """Inject `PKIT_CLI_VERSION = <checkout .pkit/VERSION>` for the dispatched
    process, so provenance reports `cli == tree` in a source checkout.

    Respects an explicit override: leaves an already-set value untouched. Reads
    the VERSION file defensively — a missing/unreadable/empty file leaves the
    var unset rather than guessing, so provenance falls back to package metadata
    exactly as before. `environ` is this process's `os.environ`, which the
    subsequent `os.execv` hands to the dispatched child.
    """
    if environ.get(_CLI_VERSION_ENV):
        return
    version = _read_pkit_version(root)
    if version is not None:
        environ[_CLI_VERSION_ENV] = version


def _run_pinned(pin: str, running: str, argv: list[str], environ) -> None:  # type: ignore[no-untyped-def]
    """Route 2: run the command under the pinned wheel, or degrade loudly to self.

    Two phases keep degradation clean (ADR-039 D2). First a resolution *probe*
    (`… project-kit --version`) proves the pin can be fetched/built at all; only
    if it can do we run the real command. So an unresolvable pin (offline,
    untagged, missing auth, no `uvx`) is caught *before* the command runs — we
    warn and return so the caller runs self, never double-executing a partially
    applied command. The probe pays a per-version fetch/build the first time,
    cached thereafter (the bounded, eyes-open cost ADR-039 records).
    """
    env = dict(environ)
    env[_LOOP_GUARD_ENV] = "1"  # the pinned wheel's router must not route again

    if not _pin_is_resolvable(pin, env):
        _warn(
            f"this project pins project-kit {pin} but the running binary is "
            f"{running}, and the pinned version could not be resolved (offline, "
            f"missing tag, auth, or uvx unavailable). Running {running} instead — "
            f"output may not match the pinned methodology. Align the pin, or re-run "
            f"where `uvx --from {DISTRIBUTION_GIT_URL}@v{pin} project-kit` resolves."
        )
        return

    completed = subprocess.run([*_pinned_base(pin), *argv], env=env)
    sys.exit(completed.returncode)


def _pinned_base(pin: str) -> list[str]:
    """The `uvx` prefix that runs project-kit at `pin`'s git tag (`v<pin>`)."""
    return ["uvx", "--from", f"{DISTRIBUTION_GIT_URL}@v{pin}", "project-kit"]


def run_bypassed(pin: str, argv: list[str], environ=None) -> int:  # type: ignore[no-untyped-def]
    """Run `pkit <argv>` at the wheel for `pin`, with routing bypassed; return the exit code.

    Uses the same `uvx --from …@v<pin>` base route 2 pins against, but sets
    PKIT_NO_ROUTE on the child so the bootstrapped process runs self rather than
    re-routing through a pin (which would loop or mis-resolve). The shared
    bootstrap the `pin` gesture's forward-reconcile builds on (ADR-049): pinning a
    project to a *newer* version needs that version's own code to sync content and
    run the forward migrations, so the reconcile runs under the target's wheel
    here rather than the currently-installed tool. Blocks until the child exits.

    The child must run **truly non-routed**: PKIT_NO_ROUTE alone is not enough
    when the caller is itself an already-routed child (the pinned-project case,
    the common one). The loop guard PKIT_ROUTED would otherwise leak into the
    bootstrapped grandchild — and its `pkit upgrade` would then re-detect itself
    as the routed pinned child and take the print/escape branch, syncing NOTHING,
    while the outer reconcile still flipped the pin forward (pin-ahead-of-content
    corruption, ADR-049). So drop PKIT_ROUTED from the child env; only
    PKIT_NO_ROUTE is set, and the grandchild reconciles content for real.
    """
    env = dict(os.environ if environ is None else environ)
    env[_BYPASS_ENV] = "1"
    env.pop(_LOOP_GUARD_ENV, None)  # never leak the loop guard into the bootstrapped child
    completed = subprocess.run([*_pinned_base(pin), *argv], env=env)
    return completed.returncode


def _pin_is_resolvable(pin: str, env) -> bool:  # type: ignore[no-untyped-def]
    """True iff the pinned wheel can be resolved and run (a `--version` probe).

    Any launch failure (`uvx` absent) or non-zero exit (fetch/build/tag error)
    means the pin is unresolvable — the caller then degrades to self.
    """
    try:
        probe = subprocess.run(
            [*_pinned_base(pin), "--version"],
            env=env,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False  # uvx not on PATH / not executable
    return probe.returncode == 0


def _run_self() -> None:
    """Route 3: import and run the in-process CLI. The heavy import lives here —
    reached only when no re-exec was taken — so routes 1 and 2 never pay it."""
    from project_kit.cli import main as cli_main

    cli_main(prog_name="pkit")


def _warn(message: str) -> None:
    """Emit a router diagnostic to stderr (never stdout — it is not command data)."""
    print(f"pkit: {message}", file=sys.stderr)
