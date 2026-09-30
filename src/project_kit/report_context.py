"""Report context sourcing — project name + workstream (ADR-050 / #644).

Two sourcing rules with architectural weight, both degrade-to-omission
(context enriches a report, never gates one):

- **Project name is declared, never path-derived.** Source of truth is the
  `name` key in the adopter's project config (`.pkit/project/config.yaml` —
  the backbone-level adopter config, the same file PRJ-008's `report.target`
  concept belongs to). Fallback: the git remote's **repo name without the
  owner/org** (an adopter's private org name is itself potentially
  sensitive). Never a filesystem path segment — a directory basename is a
  path leaf by another name (ADR-050's extension of the PRJ-008 redaction
  discipline: a value that never originates in a path cannot leak one).
- **Workstream is pm-capability vocabulary; the backbone asks pm.** The
  pm capability ships the `context-workstream` read verb; this module
  resolves it through the capability-command dispatcher's lookup (COR-021 —
  the same mechanic every pm verb uses) and runs it through the backbone's
  bounded command runner (`command_runner`, the context-read policy), so a
  hung tracker call cannot hang the report. The backbone never parses
  `workstreams.yaml`, never reads issue labels, and carries no knowledge of
  pm's schema; pm absent / verb absent / empty output all mean "no
  workstream", silently — an overrun means it too, but says so.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from project_kit.command_runner import CommandRun, Ending, run_command
from project_kit.project_config import (  # noqa: F401 — re-exported for existing readers
    EDITOR_DIRECTIVE,
    PROJECT_CONFIG_RELPATH,
    Consent,
    project_config_path,
    read_config,
    write_config,
)


def read_project_name(target_root: Path) -> str | None:
    """The declared `name` from the project config, or None when the file or
    key is absent / empty / unreadable (all normal zero-config states)."""
    name = read_config(target_root).get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def write_project_name(target_root: Path, name: str, *, consent: Consent | None = None) -> Path:
    """Persist `name` into the project config (the prompt-once write-back),
    through the one consent-gated writer (COR-048 point 5). `consent` defaults
    to already-given: the caller has asked its own question ("save this
    name?") before calling. Creates the file when absent; preserves any other
    keys and the file's header."""

    def _set_name(data: dict) -> None:
        data["name"] = name

    return write_config(
        target_root,
        _set_name,
        consent=consent if consent is not None else Consent(yes=True),
        description=f"Save name {name!r}",
    )


def git_remote_repo_name(cwd: Path) -> str | None:
    """The `origin` remote's **repo name without the owner/org** (ADR-050's
    fallback), or None when there is no usable remote. Parses both URL forms
    (`https://host/owner/repo[.git]`, `git@host:owner/repo[.git]`)."""
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return _repo_name_from_url(proc.stdout.strip())


def _repo_name_from_url(url: str) -> str | None:
    """The last path segment of a git remote URL, `.git` stripped — the repo
    name alone, never the owner/org. Pure over its input."""
    if not url:
        return None
    tail = url.rstrip("/").split("/")[-1]
    # scp-style with no slash at all (`git@host:repo.git`)
    if ":" in tail:
        tail = tail.split(":")[-1]
    tail = tail.removesuffix(".git").strip()
    return tail or None


def resolve_project_name(target_root: Path) -> str | None:
    """The silent (non-interactive) resolution chain: declared config `name`,
    else the git remote's repo name, else None. **Never** any filesystem path
    segment — there is deliberately no directory-basename arm (ADR-050)."""
    return read_project_name(target_root) or git_remote_repo_name(target_root)


#: The pm capability + read verb the workstream derivation dispatches to
#: (ADR-050: the backbone asks pm; it never reads pm's vocabulary itself).
_WORKSTREAM_CAPABILITY = "project-management"
_WORKSTREAM_VERB = "context-workstream"


def pm_workstream(target_root: Path) -> str | None:
    """The current workstream, asked of the pm capability's
    `context-workstream` read verb: resolved through the dispatcher's lookup
    (COR-021) and run through the backbone's command runner under the
    context-read policy — from the project root, with no arguments and the
    environment unchanged but for the run's deadline (the verb asks the
    tracker), bounded by
    `command_runner.COMMAND_TIMEOUT_SECONDS`, the value read as text.

    Optional on every axis: capability not installed, verb not declared,
    script not starting or failing, output empty or not UTF-8 all yield None,
    silently. An overrun yields None too, but says so on stderr: the report
    waited the bound out, and goes on without the workstream."""
    from project_kit.dispatcher import resolve_capability_script

    script = resolve_capability_script(
        target_root, _WORKSTREAM_CAPABILITY, _WORKSTREAM_VERB
    )
    if script is None:
        return None
    run = run_command(script, [], cwd=target_root)
    if run.ending is Ending.TIMED_OUT:
        click.echo(
            f"warning: workstream omitted — {_WORKSTREAM_CAPABILITY} "
            f"{_WORKSTREAM_VERB} did not answer within {run.bound_described} "
            "and was stopped; pass --workstream to name it.",
            err=True,
        )
        return None
    return _printed_value(run)


def _printed_value(run: CommandRun) -> str | None:
    """The value a run of the verb printed, or None. The verb prints its value
    bare, not as a JSON document, so the runner's parse plays no part: a run
    that exited 0 carries its standard output whether or not that text parsed
    as JSON. Output that is not UTF-8 comes back with a `detail` saying so and
    is no value — never a repaired one."""
    if run.ending not in (Ending.ANSWERED, Ending.UNPARSABLE):
        return None
    if run.returncode != 0 or run.detail:
        return None
    return run.stdout.strip() or None
