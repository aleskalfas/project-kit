"""Provisioning the environments of query commands before they run offline (#1092).

A query command — a component's validator, a command filler — runs with the
offline marker set (`validators.OFFLINE_MARKER`, ADR-058): `UV_OFFLINE=1` makes
a script with a `uv run --script` shebang resolve its inline dependencies from
uv's cache and never fetch. What such a script needs must therefore be in the
cache before its first offline run. `pkit init` and `pkit sync` put it there:
for every command a registered component declares under the query contract
whose script carries inline script metadata, they resolve the script's
environment once, online, through uv's own resolution — `uv sync --script
<path>`, which resolves the metadata and installs the environment into uv's
cache without running the script. `pkit capabilities install`, `register` and
`upgrade` do the same for the one capability they bring in (#1090).

**Idempotent.** Each script is first resolved with `--offline`, the condition
the query meets. When that succeeds the query will too: nothing is fetched and
the command is reported already provisioned. Only a script that fails offline
is resolved online.

**Never a failure of the step.** A command that cannot be provisioned — no
network, no `uv` — is a warning naming it, and init and sync go on: they keep
working offline. Until a run online provisions it, the query gives no answer,
and the query policy names why: "environment not provisioned — run `pkit sync`"
(`validators.why_no_answer`).

Provisioning happens outside the bounded run: it sets no offline marker, is not
bound by `command_runner.COMMAND_TIMEOUT_SECONDS`, and changes nothing of the
query contract. The lifecycle README's "How dependencies are provisioned before
an offline run" documents it.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from project_kit import validators
from project_kit.command_runner import registered_commands
from project_kit.package_validate import installed_package_files

# The executable that resolves a script's environment: the `uv` a `uv run
# --script` shebang finds on the same PATH.
UV = "uv"

# How long one resolution may run before provisioning gives up on it with a
# warning. uv bounds each request itself, retries included; this bounds one
# that never ends — waiting on a cache lock held elsewhere, say — so that init
# and sync always finish.
PROVISION_TIMEOUT_SECONDS = 300

# The opening line of inline script metadata (PEP 723) — what `uv run
# --script` resolves. A script without it has nothing to provision.
_INLINE_METADATA = re.compile(r"^# /// script[ \t]*$", re.MULTILINE)


class State(Enum):
    """How provisioning one command ended; the value is the verb its line prints."""

    PROVISIONED = "provisioned"  # resolved online
    ALREADY_PROVISIONED = "unchanged"  # resolved offline: nothing fetched
    NOTHING_TO_PROVISION = "skipped"  # no inline dependencies, or no script
    NOT_PROVISIONED = "warning"  # resolved neither offline nor online (`detail` says why)
    WOULD_PROVISION = "would provision"  # a dry run: uv is not asked


@dataclass(frozen=True)
class QueryScript:
    """A command a registered component declares under the query contract."""

    owner: str
    reference: str
    script: Path

    @property
    def label(self) -> str:
        return f"query command {self.reference!r} ({self.owner})"


@dataclass(frozen=True)
class Provisioning:
    """What provisioning one command did, and why when it could not."""

    command: QueryScript
    state: State
    detail: str = ""

    @property
    def line(self) -> tuple[str, str]:
        """The `(verb, detail)` status line init and sync print for it."""
        label = self.command.label
        if self.state is State.PROVISIONED:
            return (self.state.value, f"{label} — its dependencies resolved into uv's cache")
        if self.state is State.ALREADY_PROVISIONED:
            return (self.state.value, f"{label} — already provisioned")
        if self.state is State.NOTHING_TO_PROVISION:
            return (self.state.value, f"{label} — {self.detail}, nothing to provision")
        if self.state is State.NOT_PROVISIONED:
            return (
                self.state.value,
                f"{label} not provisioned: {self.detail}. It gives no answer offline "
                "until `pkit sync` runs with the network.",
            )
        return (self.state.value, label)


def query_commands(target_root: Path, *, component: str | None = None) -> list[QueryScript]:
    """Every command a registered component — capability or adapter — declares
    under the query contract (`query-contract: true` on its `commands:` leaf),
    in manifest order, then declaration order; only `component`'s when named."""
    return [
        QueryScript(owner, command.reference, command.script)
        for owner, component_dir, _package in installed_package_files(target_root)
        if component is None or owner == component
        for command in registered_commands(component_dir).values()
        if command.entry.get(validators.QUERY_CONTRACT_KEY) is True
    ]


def declares_inline_dependencies(script: Path) -> bool:
    """True when `script` carries inline script metadata for uv to resolve."""
    try:
        text = script.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return _INLINE_METADATA.search(text) is not None


def provision(command: QueryScript, *, dry_run: bool = False) -> Provisioning:
    """Resolve `command`'s script environment into uv's cache unless it already
    resolves offline. Never raises for what uv did."""
    if not command.script.is_file():
        # The packages member reports the missing script; there is nothing to resolve.
        return Provisioning(command, State.NOTHING_TO_PROVISION, "its script does not exist")
    if not declares_inline_dependencies(command.script):
        return Provisioning(
            command, State.NOTHING_TO_PROVISION, "its script declares no inline dependencies"
        )
    if dry_run:
        return Provisioning(command, State.WOULD_PROVISION)
    if _resolve(command.script, offline=True) is None:
        return Provisioning(command, State.ALREADY_PROVISIONED)
    failure = _resolve(command.script, offline=False)
    if failure is None:
        return Provisioning(command, State.PROVISIONED)
    return Provisioning(command, State.NOT_PROVISIONED, failure)


def ensure(
    target_root: Path, *, dry_run: bool = False, component: str | None = None
) -> list[tuple[str, str]]:
    """Provision every query command of the project at `target_root` — or only
    `component`'s, for a lifecycle verb that just brought that one in.

    Returns one `(verb, detail)` status line per command for the caller to
    print, and none when no component declares a query command."""
    return [
        provision(command, dry_run=dry_run).line
        for command in query_commands(target_root, component=component)
    ]


def _resolve(script: Path, *, offline: bool) -> str | None:
    """Resolve `script`'s environment with `uv sync --script` — offline, from the
    cache alone, or online. None when it resolved; else why it did not."""
    args = [UV, "sync", "--script", str(script)]
    if offline:
        args.append("--offline")
    try:
        done = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PROVISION_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return f"`{UV}` is not on the PATH"
    except subprocess.TimeoutExpired:
        return f"`{UV} sync --script` did not finish within {PROVISION_TIMEOUT_SECONDS} s"
    except OSError as exc:
        return f"`{UV}` could not start: {exc}"
    if done.returncode == 0:
        return None
    lines = [line.strip() for line in done.stderr.splitlines() if line.strip()]
    return f"`{UV} sync --script` exited {done.returncode}" + (f": {lines[-1]}" if lines else "")
