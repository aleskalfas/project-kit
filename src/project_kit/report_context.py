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
  invokes it by subprocess through the capability-command dispatcher's
  script resolution (COR-021 — the same mechanic every pm verb uses). The
  backbone never parses `workstreams.yaml`, never reads issue labels, and
  carries no knowledge of pm's schema; pm absent / verb absent / empty
  output all mean "no workstream", silently.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

#: The adopter-owned backbone project config, relative to the target root.
#: Holds project-level declarations (today: the report-context `name` key).
PROJECT_CONFIG_RELPATH = Path(".pkit") / "project" / "config.yaml"


def project_config_path(target_root: Path) -> Path:
    return target_root / PROJECT_CONFIG_RELPATH


def read_project_name(target_root: Path) -> str | None:
    """The declared `name` from the project config, or None when the file or
    key is absent / empty / unreadable (all normal zero-config states)."""
    path = project_config_path(target_root)
    if not path.is_file():
        return None
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def write_project_name(target_root: Path, name: str) -> Path:
    """Persist `name` into the project config (the prompt-once write-back).
    Creates the file/directory when absent; preserves any other keys."""
    path = project_config_path(target_root)
    yaml = YAML()  # round-trip: keep an existing file's other keys + comments
    data: dict = {}
    if path.is_file():
        try:
            loaded = yaml.load(path.read_text(encoding="utf-8"))
        except (OSError, YAMLError):
            loaded = None
        if isinstance(loaded, dict):
            data = loaded
    data["name"] = name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        yaml.dump(data, stream)
    return path


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
    `context-workstream` read verb via the dispatcher's script resolution
    (COR-021). Optional on every axis: capability not installed, verb not
    declared, script failing, or empty output all yield None."""
    from project_kit.dispatcher import resolve_capability_script

    script = resolve_capability_script(
        target_root, _WORKSTREAM_CAPABILITY, _WORKSTREAM_VERB
    )
    if script is None:
        return None
    try:
        proc = subprocess.run(
            [str(script)], cwd=target_root,
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None
