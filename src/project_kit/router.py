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
   *adopter* project pins a version (its `.pkit/VERSION`) different from this
   binary's, run the command under `uvx …@<pin>` instead. Sound only because
   ADR-033 version-locks bundled content to the binary: the pinned wheel brings
   code *and* content from the same tag, so they cannot diverge.

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
_DISTRIBUTION_GIT_URL = "git+ssh://git@github.com/aleskalfas/project-kit.git"

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

    if _is_source_checkout(root):
        # Route 1. Execs the dispatcher and never returns; on a broken checkout
        # (dispatcher missing / not executable) it warns and returns so we run
        # self rather than silently misrouting — we do NOT fall on to a pin.
        _exec_source_dispatcher(root, argv, environ)
        return

    # Route 2 candidate: an adopter project. It pins the version it installed
    # (its `.pkit/VERSION`); a mismatch against this binary means run the pin.
    pin = _resolve_pin(root)
    if pin is None:
        return  # no pin → run self
    running = _running_version()
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


def _is_source_checkout(root: Path) -> bool:
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
    """The version an adopter project pins: its installed `.pkit/VERSION`.

    ADR-039 leaves the pin source to the implementation; we reuse `.pkit/VERSION`
    — the adopter's installed *content* version — because ADR-033 version-locks
    content to the binary, so "run me under the version whose content I have"
    is exactly the right pin, and it needs no new file. Returns None when there
    is no readable, non-empty VERSION (→ no pin → run self).
    """
    return _read_pkit_version(root)


def _read_pkit_version(root: Path) -> str | None:
    """Read `root/.pkit/VERSION`, stripped; None when missing/unreadable/empty.

    Defensive and stdlib-only — a plain file read, cheap enough for the hot path
    (ADR-039). Shared by the pin resolver (route 2) and the route-1 CLI-version
    stamp so the two never diverge on how the VERSION file is read.
    """
    try:
        text = (root / ".pkit" / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def _running_version() -> str:
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
        f"executable — running this binary ({_running_version()}) instead. "
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
            f"where `uvx --from {_DISTRIBUTION_GIT_URL}@v{pin} project-kit` resolves."
        )
        return

    completed = subprocess.run([*_pinned_base(pin), *argv], env=env)
    sys.exit(completed.returncode)


def _pinned_base(pin: str) -> list[str]:
    """The `uvx` prefix that runs project-kit at `pin`'s git tag (`v<pin>`)."""
    return ["uvx", "--from", f"{_DISTRIBUTION_GIT_URL}@v{pin}", "project-kit"]


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
