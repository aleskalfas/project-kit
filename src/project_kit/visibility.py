"""Adopter-controlled git footprint (per ADR-009).

Two visibility modes over a per-component-declared footprint, realized entirely
through the per-clone `.git/info/exclude` — **no `.gitignore` the adopter owns is
ever written**:

- `shared` (default): pkit is committed; pkit's region is kept clear of
  `info/exclude`.
- `private`: the whole footprint goes into a pkit-owned delimited region in
  `.git/info/exclude` (uncommitted, parent-level — the only native channel that
  can hide `.pkit/` itself), and — because going private *means* "stop sharing
  pkit" — a confirm-gated `untrack` removes any already-tracked footprint files
  from the index (working copies preserved).

`untrack` is also a standalone, footprint-restricted, precondition-guarded verb
(the one backbone gesture that mutates adopter git-index state, bounded per
ADR-009 rule 5). With `runtime_ignored` it removes only the tracked files the
rendered `.pkit/.gitignore` ignores, a part of the footprint. pkit co-edits
nothing the adopter owns: the visibility modes write only `info/exclude`, which
git owns, and only within its own delimited region.

Separately, this module renders the pkit-owned `.pkit/.gitignore` for the
runtime-local files pkit writes (ADR-009 rule 7), wholesale from the backbone's
and each installed component's declarations and from the project's
configuration — the backbone's choice for the process journals taking
precedence over a component entry that still claims them. An ignore rule does
not untrack a file git already tracks, so the `visibility` member of `pkit
validate` warns of each tracked file the render ignores (`outcome`).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import click

from project_kit import cli_render, process_journal
from project_kit.manifest import read_backbone_manifest
from project_kit.validators import Finding, Outcome, Severity

# Core's OWN footprint. Naming `.pkit/` here is not the layering inversion
# ADR-009 rule 1 forbids — rule 1 bars core from naming adapter- or
# capability-specific footprint paths; core may declare its own directory.
# Components contribute the rest (e.g. the claude-code adapter's `.claude/`
# deploys) via package.yaml.
_BACKBONE_FOOTPRINT: tuple[str, ...] = (".pkit/",)

# Core's OWN runtime-local ignore set (ADR-009 rule 7). The seam analogous
# to `_BACKBONE_FOOTPRINT`, declared here because the backbone has no
# `package.yaml` to carry it. Rule 7's ownership test decides what belongs here:
# the tier that writes a runtime file declares its pattern, whoever owns the
# directory it lands in — so this list holds the runtime-local files core writes
# under `.pkit/`. The process journals core's engine writes pass the same test,
# though they land in each capability's `project/` subtree; their pattern
# follows a setting, so `resolve_runtime_ignore()` takes it from
# `process_journal`, not from this fixed list.
#
# Patterns are repo-root-relative strings declared verbatim, exactly as
# `footprint` declarations are (the aggregator stores them as-given; the T2
# `.pkit/.gitignore` renderer owns any rebasing onto the `.pkit/`-relative form
# the nested carrier wants — ADR-009 rule 7's `.pkit/`-subtree scope).
#
# The set covers two core surfaces, both of which have no `package.yaml` and so
# can ONLY declare through this core-level seam (the per-component `package.yaml`
# declarations are a separate task):
#   - the **backbone** itself — its Python bytecode caches scattered under
#     `.pkit/`; and
#   - the **permissions surface**, which is a backbone-propagated code directory
#     (synced via `PROPAGATED_AREAS`, like `adapters/`), NOT a COR-011
#     area/capability — so it has no `package.yaml` of its own and piggybacks
#     this core-level seam (ADR-009 rule 7's per-component declaration
#     seam). Its runtime-local files are
#     PRJ-006's diagnose capture-log + TTL armed marker, the sandbox provenance
#     sidecar, the ADR-032 per-machine active-profile sidecar, and the ADR-046
#     profile-realization ledger, all under `.pkit/permissions/project/`.
_BACKBONE_RUNTIME_IGNORE: tuple[str, ...] = (
    # Backbone: Python bytecode caches anywhere under `.pkit/`.
    ".pkit/**/__pycache__/",
    # Backbone: the folder of the migration runner's `pkit`, which lives only
    # while a set of migrations runs (ADR-065 point 14, `migrations.RUNNER_PARENT`).
    ".pkit/.migration-runner/",
    # Permissions surface (piggybacks this seam — no package.yaml of its own).
    ".pkit/permissions/project/diagnose.yaml",
    ".pkit/permissions/project/diagnose-log.jsonl",
    ".pkit/permissions/project/sandbox-provenance.yaml",
    # Per-machine active-profile sidecar (ADR-032): an operator's autonomy choice
    # is per-machine, so it lives gitignored, never committed as a team default.
    ".pkit/permissions/project/active-profile.yaml",
    # Profile-realization ledger (ADR-046): the per-machine provenance record of
    # the settings.local.json allow rules `apply` authored for the active
    # profile — derived from a per-machine activation, so gitignored like it.
    ".pkit/permissions/project/profile-realized-allows.yaml",
)

_BEGIN = "# >>> pkit footprint — managed by `pkit visibility`; do not edit >>>"
_END = "# <<< pkit footprint <<<"

_yaml_keys = ("footprint", "runtime_ignore")


# --- footprint aggregation ---------------------------------------------------


def _component_package_yaml(target_root: Path, kind: str, name: str) -> Path | None:
    if kind == "adapter":
        p = target_root / ".pkit" / "adapters" / name / "package.yaml"
    elif kind == "capability":
        p = target_root / ".pkit" / "capabilities" / name / "package.yaml"
    else:
        return None
    return p if p.is_file() else None


def _read_footprint_decl(package_yaml: Path) -> list[str]:
    """Read a component's `footprint:` list from package.yaml (tolerant)."""
    from ruamel.yaml import YAML

    try:
        data = YAML(typ="safe").load(package_yaml.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    raw = data.get("footprint") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def footprint(target_root: Path) -> list[str]:
    """Aggregate the footprint across installed components (backbone + each
    adapter/capability's declared `footprint`). De-duped, order-stable."""
    out: list[str] = list(_BACKBONE_FOOTPRINT)
    manifest = read_backbone_manifest(target_root)
    if manifest is not None:
        for entry in manifest.components:
            pkg = _component_package_yaml(target_root, entry.kind, entry.name)
            if pkg is not None:
                out.extend(_read_footprint_decl(pkg))
    return _dedupe(out)


# --- runtime-ignore aggregation (ADR-009 rule 7) ------------------------
#
# Mirror image of the footprint aggregation above: the same manifest-walk over
# installed adapters/capabilities, the same per-component package.yaml reader,
# the same core-level seam for the surfaces that have no package.yaml. The two
# keys (`footprint:` / `runtime_ignore:`) sit side-by-side in package.yaml and
# aggregate identically. This is T1 of EPIC #154 — the *collector*; the
# `.pkit/.gitignore` renderer that consumes this list is T2.


def _read_runtime_ignore_decl(package_yaml: Path) -> list[str]:
    """Read a component's `runtime_ignore:` list from package.yaml (tolerant)."""
    from ruamel.yaml import YAML

    try:
        data = YAML(typ="safe").load(package_yaml.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    raw = data.get("runtime_ignore") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


@dataclass(frozen=True)
class DroppedEntries:
    """A component's `runtime_ignore` entries the render leaves out: each claims
    the process journals while the project commits them, so the backbone's
    choice takes precedence (`process_journal.JournalSettings.drops_claim`)."""

    component: str
    entries: tuple[str, ...]  # as declared, repo-root-relative

    def describe(self) -> str:
        """`<component> '<entry>' — <why>`: the one wording of the rendered
        comment line and of the `pkit config set` report."""
        quoted = ", ".join(f"'{entry}'" for entry in self.entries)
        return f"{self.component} {quoted} — {process_journal.CLAIM_DROPPED}"


@dataclass(frozen=True)
class RuntimeIgnore:
    """What the `.pkit/.gitignore` render is made of (`resolve_runtime_ignore`)."""

    patterns: tuple[str, ...]  # repo-root-relative, de-duped, order-stable
    dropped: tuple[DroppedEntries, ...]  # one per component, in manifest order
    components: int  # the backbone seam plus each component a pattern comes from


def resolve_runtime_ignore(target_root: Path) -> RuntimeIgnore:
    """Aggregate runtime-local ignore patterns across installed components
    (backbone + permissions seam + each adapter/capability's declared
    `runtime_ignore`) — what the `.pkit/.gitignore` renderer wholesale-renders
    from (ADR-009 rule 7).

    The backbone's contribution has one configured part: the process journal
    (COR-033 point 7). The engine writes every journal and owns their path —
    inside each capability's `project/process/` — so the backbone, not a
    capability, declares the pattern, and declares it unless the project chose
    to commit its journals. Its choice takes precedence: while the journals are
    committed, a component entry that still claims them (a package older than
    the backbone's ownership) is left out and listed in `dropped`, so no
    component keeps committed journals ignored. Because the render is
    wholesale, the result follows the setting on the next render: install,
    sync, or a `pkit config set`."""
    journal = process_journal.read_settings(target_root)
    patterns: list[str] = [*_BACKBONE_RUNTIME_IGNORE, *journal.runtime_ignore_patterns()]
    dropped: list[DroppedEntries] = []
    components = 1  # the backbone/permissions core seam
    for name, declared in _component_runtime_ignore(target_root):
        kept = [p for p in declared if not journal.drops_claim(p)]
        lost = _dedupe([p for p in declared if journal.drops_claim(p)])
        patterns.extend(kept)
        components += 1 if kept else 0
        if lost:
            dropped.append(DroppedEntries(component=name, entries=tuple(lost)))
    return RuntimeIgnore(
        patterns=tuple(_dedupe(patterns)), dropped=tuple(dropped), components=components
    )


def runtime_ignore(target_root: Path) -> list[str]:
    """The patterns `resolve_runtime_ignore` aggregates: what the rendered
    `.pkit/.gitignore` ignores."""
    return list(resolve_runtime_ignore(target_root).patterns)


def _component_runtime_ignore(target_root: Path) -> list[tuple[str, list[str]]]:
    """Each installed adapter/capability's `runtime_ignore:` declaration, by
    component name, in manifest order."""
    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        return []
    declarations: list[tuple[str, list[str]]] = []
    for entry in manifest.components:
        pkg = _component_package_yaml(target_root, entry.kind, entry.name)
        if pkg is not None:
            declarations.append((entry.name, _read_runtime_ignore_decl(pkg)))
    return declarations


def _dedupe(paths: list[str]) -> list[str]:
    """Order-stable de-dupe — shared by `footprint` and `runtime_ignore`."""
    seen: set[str] = set()
    deduped: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            deduped.append(path)
    return deduped


# --- runtime-ignore renderer (ADR-009 rule 7) -----------------------
#
# The renderer that *consumes* the `resolve_runtime_ignore()` collector above and
# wholesale-regenerates the pkit-owned `.pkit/.gitignore`. Lives at the CORE
# tier (a sibling to the collector), invoked directly from the install path
# and BOTH sync paths — NOT from the adapter-primitives runner, which is adapter
# tier and would skip backbone/capability declarations when no adapter is
# installed (the layering inversion ADR-009 forbids).

_RUNTIME_IGNORE_PATH = ".pkit/.gitignore"

_RUNTIME_IGNORE_HEADER = (
    "# pkit-owned — rendered wholesale from the backbone's own declarations, each\n"
    "# installed component's `runtime_ignore:` declaration, and the project's\n"
    "# configuration in `.pkit/project/config.yaml` (ADR-009 rule 7), by\n"
    "# `pkit install`, `pkit sync`, and a `pkit config set` that changes the result.\n"
    "# DO NOT EDIT: regenerated from scratch every run; hand edits are overwritten.\n"
    "# An uninstalled component's lines are simply absent on the next render.\n"
)


def _render_pattern(pattern: str) -> str:
    """Rebase a repo-root-relative `runtime_ignore` pattern onto the form the
    nested `.pkit/.gitignore` needs.

    Patterns are stored repo-root-relative by the T1 collector (e.g.
    `.pkit/permissions/project/diagnose.yaml`, `.pkit/**/__pycache__/`). A nested
    `.gitignore` matches patterns relative to *its own* directory (`.pkit/`), so
    the `.pkit/` prefix is stripped on render — `.pkit/permissions/.../x` becomes
    `permissions/.../x`, which the file at `.pkit/.gitignore` matches correctly
    (ADR-009 rule 7's `.pkit/`-subtree scope). A pattern that is not under `.pkit/` cannot be
    covered by this carrier (none are in today's set); it is rendered verbatim
    rather than silently dropped, so a misdeclaration is visible in the output
    rather than swallowed.
    """
    prefix = ".pkit/"
    if pattern.startswith(prefix):
        stripped = pattern[len(prefix) :]
        return stripped if stripped else pattern
    return pattern


def render_runtime_ignore_content(target_root: Path) -> str:
    """Build the full text of `.pkit/.gitignore` from the aggregated
    `runtime_ignore` declarations and the configuration they follow. Pure: no
    filesystem writes, deterministic for a given set of installed components
    and configuration (so re-rendering is byte-identical).
    """
    return _render_content(resolve_runtime_ignore(target_root))


def _render_content(resolved: RuntimeIgnore) -> str:
    """The file's text: the header, the patterns, then one comment line per
    component whose entries the render left out, so a reader of the file sees
    why they are absent."""
    patterns = "".join(f"{_render_pattern(p)}\n" for p in resolved.patterns)
    dropped = "".join(f"# dropped: {d.describe()}\n" for d in resolved.dropped)
    return _RUNTIME_IGNORE_HEADER + "".join("\n" + part for part in (patterns, dropped) if part)


def render_runtime_ignore(target_root: Path, *, dry_run: bool = False) -> str:
    """Wholesale-regenerate `.pkit/.gitignore` from current installed
    components' `runtime_ignore:` declarations (ADR-009 rule 7).

    Idempotent: re-running on unchanged declarations produces byte-identical
    output and rewrites the same content. `--dry-run` prints a would-render
    summary (pattern count, component count) and writes nothing.

    Returns a one-line status message for the caller to echo.
    """
    return _render(target_root, resolve_runtime_ignore(target_root), dry_run=dry_run)


def _render(target_root: Path, resolved: RuntimeIgnore, *, dry_run: bool) -> str:
    """Write the render of `resolved` (dry-run: write nothing); its status line."""
    summary = (
        f"{_RUNTIME_IGNORE_PATH} "
        f"({len(resolved.patterns)} pattern(s) from {resolved.components} component(s))"
    )
    if dry_run:
        return cli_render.style("strong", f"  would render  {summary}")

    path = target_root / ".pkit" / ".gitignore"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_content(resolved), encoding="utf-8")
    return cli_render.style("strong", f"  rendered      {summary}")


@dataclass(frozen=True)
class Refreshed:
    """A re-render `refresh_runtime_ignore` made: the render's status line, and
    the component entries the new render leaves out, for the writer to report."""

    status: str
    dropped: tuple[DroppedEntries, ...]

    def report(self) -> str:
        """The status line, then one line per component whose entries were left out."""
        return "\n".join([self.status, *(f"  dropped       {d.describe()}" for d in self.dropped)])


def refresh_runtime_ignore(target_root: Path) -> Refreshed | None:
    """Re-render an existing `.pkit/.gitignore` whose content no longer matches
    what the declarations and configuration render to — for a writer that has
    just changed something the render reads (a configuration write, COR-033
    point 7). Returns the re-render with the component entries it leaves out
    (`resolve_runtime_ignore`), or None when there was nothing to do: the file
    matches, or there is no rendered file yet (install and sync create it; a
    configuration write does not)."""
    path = target_root / ".pkit" / ".gitignore"
    if not path.is_file():
        return None
    try:
        current = path.read_text(encoding="utf-8")
    except OSError:
        return None
    resolved = resolve_runtime_ignore(target_root)
    if current == _render_content(resolved):
        return None
    return Refreshed(status=_render(target_root, resolved, dry_run=False), dropped=resolved.dropped)


# --- git helpers -------------------------------------------------------------


def _git(target_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=target_root, capture_output=True, text=True, check=False
    )


def _info_exclude_path(target_root: Path) -> Path:
    """Resolve `.git/info/exclude` robustly (handles worktrees/submodules)."""
    res = _git(target_root, "rev-parse", "--git-path", "info/exclude")
    if res.returncode != 0:
        raise click.ClickException("not a git repository (git rev-parse failed).")
    p = Path(res.stdout.strip())
    return p if p.is_absolute() else (target_root / p)


def _repo_busy(target_root: Path) -> str | None:
    """Return a reason string if a merge/rebase/cherry-pick/revert is in progress."""
    checks = {
        "MERGE_HEAD": "a merge is in progress",
        "CHERRY_PICK_HEAD": "a cherry-pick is in progress",
        "REVERT_HEAD": "a revert is in progress",
        "rebase-merge": "a rebase is in progress",
        "rebase-apply": "a rebase is in progress",
    }
    for marker, reason in checks.items():
        res = _git(target_root, "rev-parse", "--git-path", marker)
        if res.returncode == 0 and (target_root / res.stdout.strip()).exists():
            return reason
    return None


def _tracked_footprint(target_root: Path, fp: list[str]) -> list[str]:
    res = _git(target_root, "ls-files", "-z", "--", *fp)
    if res.returncode != 0 or not res.stdout:
        return []
    return sorted(p for p in res.stdout.split("\0") if p)


def _staged_footprint(target_root: Path, fp: list[str]) -> list[str]:
    res = _git(target_root, "diff", "--cached", "--name-only", "-z", "--", *fp)
    if res.returncode != 0 or not res.stdout:
        return []
    return sorted(p for p in res.stdout.split("\0") if p)


# --- tracked runtime-ignored files (ADR-009 rules 5 and 7) ---------------------


class RuntimeIgnoreUnmatched(Exception):
    """Git could not match the tracked files against the render, so the set of
    tracked runtime-ignored files is not known (`tracked_runtime_ignored`)."""


# The variables that point a git command at another repository than the folder
# it runs in, as a hook's environment may: removed for the scratch repository.
_REPOSITORY_VARIABLES = frozenset({"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"})


def _run_git(
    cwd: Path, *args: str, stdin: str | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """A git command whose paths survive any bytes a file name holds."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        input=stdin,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )


def tracked_runtime_ignored(target_root: Path) -> list[str]:
    """The files git tracks under `.pkit/` that `.pkit/.gitignore` ignores, as
    the declarations and configuration render it (ADR-009 rule 7): what `pkit
    visibility untrack --runtime-ignored` removes from the index, and what the
    `visibility` member of `pkit validate` warns of.

    An ignore rule does not untrack a file git already tracks, so a file
    committed before a component declared it stays tracked. Git's own matcher
    decides, in a scratch repository whose only ignore rules are the render: the
    project's root `.gitignore`, `.git/info/exclude` (where private visibility
    hides all of `.pkit/`) and global excludes neither widen nor hide the set.
    The 1.150.0 backbone migration (`002-untrack-runtime-ignored-files`) matches
    the same way, from the rendered file. Sorted; empty outside a git work tree.
    Raises `RuntimeIgnoreUnmatched` when git cannot match."""
    try:
        inside = _run_git(target_root, "rev-parse", "--is-inside-work-tree")
    except OSError:
        return []  # no git: nothing is tracked
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return []
    listed = _run_git(target_root, "ls-files", "-z", "--", ".pkit/")
    if listed.returncode != 0:
        raise RuntimeIgnoreUnmatched(f"git ls-files exited {listed.returncode}")
    tracked = [path for path in listed.stdout.split("\0") if path]
    if not tracked:
        return []
    ignore_case = _run_git(target_root, "config", "--bool", "core.ignoreCase").stdout.strip()
    env = {k: v for k, v in os.environ.items() if k not in _REPOSITORY_VARIABLES}
    with tempfile.TemporaryDirectory() as scratch:
        repo = Path(scratch) / "repo"
        init = _run_git(
            Path(scratch), "-c", "init.defaultBranch=scratch", "init", "-q", str(repo), env=env
        )
        if init.returncode != 0:
            raise RuntimeIgnoreUnmatched(
                f"git init of a scratch repository exited {init.returncode}"
            )
        (repo / ".git" / "info").mkdir(parents=True, exist_ok=True)
        (repo / ".git" / "info" / "exclude").write_text("", encoding="utf-8")
        (repo / ".pkit").mkdir()
        (repo / ".pkit" / ".gitignore").write_text(
            render_runtime_ignore_content(target_root), encoding="utf-8"
        )
        matched = _run_git(
            repo,
            "-c",
            f"core.excludesFile={os.devnull}",
            "-c",
            f"core.ignoreCase={ignore_case or 'false'}",
            "check-ignore",
            "--no-index",
            "-z",
            "--stdin",
            stdin="\0".join(tracked) + "\0",
            env=env,
        )
    # check-ignore exits 1 when nothing matches; anything above 1 is an error.
    if matched.returncode > 1:
        raise RuntimeIgnoreUnmatched(f"git check-ignore exited {matched.returncode}")
    return sorted(path for path in matched.stdout.split("\0") if path)


def _tracked_runtime_ignored_or_refuse(target_root: Path) -> list[str]:
    try:
        return tracked_runtime_ignored(target_root)
    except RuntimeIgnoreUnmatched as exc:
        raise click.ClickException(
            f"could not match the tracked files under .pkit/ against .pkit/.gitignore ({exc}); "
            "nothing was untracked."
        ) from exc


def _staged_paths(target_root: Path, paths: list[str]) -> list[str]:
    """Which of `paths`, each read as itself and never as a pattern, have staged changes."""
    res = _run_git(
        target_root, "--literal-pathspecs", "diff", "--cached", "--name-only", "-z", "--", *paths
    )
    if res.returncode != 0 or not res.stdout:
        return []
    return sorted(p for p in res.stdout.split("\0") if p)


# What the `visibility` member says at each tracked file `.pkit/.gitignore` ignores.
_TRACKED_RUNTIME_IGNORED = (
    "tracked, though .pkit/.gitignore ignores it: a component declares it runtime-local "
    "(ADR-009 rule 7), and an ignore rule does not untrack a file git already tracks. "
    "Run `pkit visibility untrack --runtime-ignored`, then commit the removal; the working "
    "copy stays."
)


def outcome(target_root: Path) -> Outcome:
    """The `visibility` member of `pkit validate`: each file git tracks that
    `.pkit/.gitignore`, as the declarations render it, ignores
    (`tracked_runtime_ignored`), a warning at the file naming the fix. So a file
    a component declares after a project committed it is found without a
    migration of its own. A warning, since the project works on with the file
    tracked, and the fix is a commit the operator makes. Where git cannot match,
    one warning at `.pkit/.gitignore` says so."""
    try:
        tracked = tracked_runtime_ignored(target_root)
    except RuntimeIgnoreUnmatched as exc:
        return Outcome(
            ("tracked files not matched against .pkit/.gitignore; 1 warning(s).",),
            (
                Finding(
                    ".pkit/.gitignore",
                    f"could not match the tracked files under .pkit/ against it ({exc}), so "
                    "a tracked file it ignores is not reported. The tracked files under "
                    ".pkit/ that an ignore file matches: "
                    "`git ls-files -ci --exclude-per-directory=.gitignore -- .pkit/`.",
                    Severity.WARNING,
                ),
            ),
        )
    findings = tuple(Finding(path, _TRACKED_RUNTIME_IGNORED, Severity.WARNING) for path in tracked)
    return Outcome(
        (f"{len(findings)} tracked file(s) .pkit/.gitignore ignores; {len(findings)} warning(s).",),
        findings,
    )


# --- info/exclude region management ------------------------------------------


def _strip_region(text: str) -> str:
    """Remove pkit's delimited region (and a trailing blank line) if present."""
    if _BEGIN not in text:
        return text
    lines = text.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        if line.strip() == _BEGIN:
            skipping = True
            continue
        if skipping:
            if line.strip() == _END:
                skipping = False
            continue
        out.append(line)
    # Drop a trailing blank that the region may have left behind.
    while out and out[-1].strip() == "":
        out.pop()
    return ("\n".join(out) + "\n") if out else ""


def _region_present(target_root: Path) -> bool:
    path = _info_exclude_path(target_root)
    return path.is_file() and _BEGIN in path.read_text(encoding="utf-8")


def _write_region(target_root: Path, fp: list[str]) -> None:
    path = _info_exclude_path(target_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    base = _strip_region(path.read_text(encoding="utf-8")) if path.is_file() else ""
    block = "\n".join([_BEGIN, *fp, _END])
    new = (base.rstrip("\n") + "\n\n" if base.strip() else "") + block + "\n"
    path.write_text(new, encoding="utf-8")


def _region_lines(text: str) -> list[str] | None:
    """The patterns pkit's region holds, or None where the text holds no region."""
    if _BEGIN not in text:
        return None
    held: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.strip() == _BEGIN:
            inside = True
            continue
        if inside and line.strip() == _END:
            return held
        if inside:
            held.append(line)
    return held


def refresh_private_region(target_root: Path, *, dry_run: bool = False) -> str | None:
    """Re-render pkit's region of `.git/info/exclude` from the footprint, where the region
    is present, for install and sync: a component installed since `pkit visibility
    private` ran may declare footprint the region does not hold, which would then reach
    the shared tree (ADR-009 point 3). Returns the status line, or None where there was
    nothing to do: no git repository, no region, or a region that holds the footprint."""
    try:
        path = _info_exclude_path(target_root)
    except click.ClickException:
        return None
    if not path.is_file():
        return None
    held = _region_lines(path.read_text(encoding="utf-8"))
    if held is None:
        return None
    fp = footprint(target_root)
    if held == fp:
        return None
    what = f".git/info/exclude (pkit's private region, {len(fp)} path(s))"
    if dry_run:
        return f"  {'would render':<12} {what}"
    _write_region(target_root, fp)
    return f"  {'rendered':<12} {what}"


def _remove_region(target_root: Path) -> bool:
    path = _info_exclude_path(target_root)
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if _BEGIN not in text:
        return False
    path.write_text(_strip_region(text), encoding="utf-8")
    return True


# --- untrack -----------------------------------------------------------------


def untrack(
    target_root: Path,
    *,
    dry_run: bool = False,
    confirm: Callable[[str], bool] | None = None,
    runtime_ignored: bool = False,
) -> str:
    """Remove already-tracked footprint files from the index (working copies
    preserved). Footprint-only, confirm-gated, clean-precondition guarded.

    With `runtime_ignored`, only the tracked files the rendered `.pkit/.gitignore`
    ignores (`tracked_runtime_ignored`), a part of the footprint, each path read
    as itself: the standing fix for a file a component declares runtime-local
    after a project committed it (ADR-009 rules 5 and 7)."""
    noun = "runtime-ignored" if runtime_ignored else "footprint"
    fp = [] if runtime_ignored else footprint(target_root)
    busy = _repo_busy(target_root)
    if busy:
        raise click.ClickException(
            f"refusing to untrack — {busy}. Finish or abort it first, then re-run."
        )

    # Nothing tracked → clean no-op. Checked before the staged-changes guard so
    # a re-run after a prior untrack (which leaves *staged deletions* of these
    # paths) is idempotent rather than a false "staged changes" refusal.
    if runtime_ignored:
        tracked = _tracked_runtime_ignored_or_refuse(target_root)
    else:
        tracked = _tracked_footprint(target_root, fp)
    if not tracked:
        return (
            cli_render.style("strong", f"untrack: no tracked {noun} files — nothing to remove.")
            + "\n"
        )

    # A still-tracked file carrying a staged *modification* would entangle the
    # removal with a pending index — refuse (ADR-009 rule 5).
    if runtime_ignored:
        staged = _staged_paths(target_root, tracked)
    else:
        staged = [p for p in _staged_footprint(target_root, fp) if p in set(tracked)]
    if staged:
        raise click.ClickException(
            f"refusing to untrack — {noun} paths have staged changes:\n"
            + "\n".join(f"  {p}" for p in staged)
            + "\nCommit or unstage them first."
        )

    lines = [
        cli_render.style(
            "strong", f"{len(tracked)} tracked {noun} file(s) would be removed from the index:"
        )
    ]
    lines += [f"  {p}" for p in tracked[:20]]
    if len(tracked) > 20:
        lines.append(f"  … and {len(tracked) - 20} more")
    lines.append("")
    lines.append("Working copies are preserved (git rm --cached); they're removed from the")
    lines.append("shared tree on your next commit.")

    if dry_run:
        lines.append("")
        lines.append("(dry-run — nothing changed.)")
        return "\n".join(lines) + "\n"

    if confirm is not None and not confirm("\n".join(lines) + "\n\nProceed?"):
        return cli_render.style("strong", "untrack: cancelled — files left tracked.") + "\n"

    if runtime_ignored:
        res = _run_git(
            target_root, "--literal-pathspecs", "rm", "--cached", "--quiet", "--", *tracked
        )
    else:
        res = _git(target_root, "rm", "--cached", "--quiet", "--", *tracked)
    if res.returncode != 0:
        raise click.ClickException(f"git rm --cached failed:\n{res.stderr.strip()}")
    return (
        cli_render.style(
            "strong", f"untracked {len(tracked)} {noun} file(s) (working copies kept)."
        )
        + "\n"
    )


# --- visibility --------------------------------------------------------------


def status(target_root: Path) -> str:
    fp = footprint(target_root)
    private = _region_present(target_root)
    tracked = _tracked_footprint(target_root, fp)
    mode = "private" if private else "shared"
    gloss = (
        "pkit hidden via .git/info/exclude (this clone only)"
        if private
        else "pkit committed the ordinary way"
    )
    rows = [{"path": p} for p in fp]
    sections = [
        cli_render.section(
            rows=rows,
            columns=["path"],
            header="FOOTPRINT",
            gloss="aggregated across installed components",
            empty="(no footprint declared)",
        )
    ]
    st = cli_render.status("Visibility", mode, gloss=gloss, placement="header")
    commands = [
        ("pkit visibility private", "hide pkit from the shared tree (this clone)"),
        ("pkit visibility shared", "return pkit to committed (default)"),
        ("pkit visibility untrack --dry-run", "preview removing tracked footprint files"),
    ]
    if private and tracked:
        st = cli_render.status(
            "Visibility",
            mode,
            gloss=gloss,
            placement="header",
            warn=f"{len(tracked)} footprint file(s) still tracked — run `pkit visibility untrack`",
        )
    return cli_render.view(
        title=cli_render.title("Git footprint", mode, gloss="adopter-controlled (ADR-009)"),
        status=st,
        sections=sections,
        commands=commands,
    )


def set_visibility(
    target_root: Path,
    mode: str,
    *,
    dry_run: bool = False,
    confirm: Callable[[str], bool] | None = None,
) -> str:
    """Apply `shared` or `private`. `private` writes the info/exclude region and
    runs the confirm-gated untrack; `shared` clears the region."""
    if not (target_root / ".git").exists():
        raise click.ClickException("not a git repository.")
    fp = footprint(target_root)

    if mode == "shared":
        if dry_run:
            verb = "would clear" if _region_present(target_root) else "no pkit region in"
            return (
                cli_render.style(
                    "strong", f"shared: {verb} .git/info/exclude (pkit committed normally)."
                )
                + "\n"
            )
        removed = _remove_region(target_root)
        msg = (
            "cleared pkit's region from .git/info/exclude" if removed else "no pkit region to clear"
        )
        return (
            cli_render.style("strong", f"visibility: shared — {msg}; pkit is committed normally.")
            + "\n"
        )

    if mode == "private":
        lines = [
            cli_render.style(
                "strong", "visibility: private — pkit hidden from the shared tree (this clone)."
            )
        ]
        if dry_run:
            lines.append("")
            lines.append("would write to .git/info/exclude:")
            lines += [f"  {p}" for p in fp]
            lines.append("")
            lines.append(untrack(target_root, dry_run=True).rstrip("\n"))
            return "\n".join(lines) + "\n"
        _write_region(target_root, fp)
        lines.append(f"  wrote {len(fp)} footprint pattern(s) to .git/info/exclude")
        lines.append("")
        lines.append(untrack(target_root, dry_run=False, confirm=confirm).rstrip("\n"))
        return "\n".join(lines) + "\n"

    raise click.ClickException(f"unknown visibility mode {mode!r}; expected 'shared' or 'private'.")
