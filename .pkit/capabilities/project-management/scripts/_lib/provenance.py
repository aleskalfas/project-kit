"""Version-provenance stamp for issue/PR bodies + filing comments.

Realizes [project-management:DEC-041-version-provenance-stamp] (the what/why)
under the write-path contract of ADR-037. Two records, two jobs:

- **Filing comment** — a one-time, immutable comment the creating scripts
  post, recording the methodology version the issue/PR was *born under*.
  It answers "was this filed before or after the buggy upgrade?".
- **Footer** — a self-replacing, versions-only region at the foot of the
  body carrying the version of the *current* touch.

This module is the **sole constructor** of both (ADR-037): every
body-writing script routes its written-back body through `stamp()`, and
every creating script posts via `post_filing_comment()`. The agent never
authors the footer bytes.

The footer invariant is **strip-then-append-exactly-one**: `stamp()`
strips *any* provenance region from the incoming body — complete,
partial, orphaned, or doubled — by cutting from the first sentinel
through end-of-document, then appends exactly one fresh region. The
operation is idempotent regardless of the incoming body's state, so a
doubled or orphaned footer is structurally impossible.

The sentinel strings here are locked to the `provenance_marker` entry in
`body-format.yaml` by `tests/test_provenance.py` (single source of truth,
verified at test time rather than re-parsed on every call).

The **tree** (backbone) version resolves in order: (1) `.pkit/VERSION`
if present and non-empty — the source repo's source-of-truth, kept ahead
of the self-hosted manifest (which sits at a stale 1.0.0); (2) else
`.pkit/manifest.yaml`'s top-level `backbone_version` — the adopter's
canonical installed version, the same value `pkit status` reads (an
adopter install has no `.pkit/VERSION`); (3) else `unknown`.
"""

from __future__ import annotations

import datetime as _dt
import importlib.metadata
import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # defensive; ruamel is in the kit's pyproject.
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]

# Sentinels — MUST match body-format.yaml `provenance_marker`
# (`start_marker` / `end_marker`). Locked by test_provenance.py.
MARKER_START = "<!-- pkit-provenance:start -->"
MARKER_END = "<!-- pkit-provenance:end -->"
# Idempotency marker for the immutable filing comment (mirrors the
# hook engine's `<!-- pkit-hook: <id> -->` convention).
FILING_MARKER = "<!-- pkit-provenance:filing -->"

_UNKNOWN = "unknown"


@dataclass(frozen=True)
class Versions:
    """The provenance version axes (per DEC-041 item 3).

    `tree` (backbone) and `capability` answer *which methodology version
    governed this issue* — the load-bearing axes. `cli` is actor-tooling
    provenance (*which tool wrote this*); it may be None when the running
    interpreter cannot resolve the installed CLI.
    """

    tree: str
    capability: str
    cli: str | None

    @property
    def drifted(self) -> bool:
        """True when the installed CLI version differs from the synced tree."""
        return self.cli is not None and self.cli != self.tree


# --- version resolution ------------------------------------------------


def read_versions(capability_root: Path) -> Versions:
    """Resolve the three provenance version axes at call time.

    Write-time capture is the only moment the version in force can be
    observed (DEC-041 Context); this reads all three from disk / the
    running environment, never from git history.
    """
    return Versions(
        tree=_read_tree_version(capability_root),
        capability=_read_capability_version(capability_root),
        cli=_read_cli_version(capability_root),
    )


def _read_tree_version(capability_root: Path) -> str:
    # capability_root = .pkit/capabilities/<name>; .pkit/ = parents[1].
    # VERSION (source-repo source-of-truth) wins; else the manifest's
    # backbone_version (the adopter's canonical installed version); else
    # unknown. See the module docstring's resolution note.
    version = _read_version_file(capability_root.parents[1] / "VERSION")
    if version != _UNKNOWN:
        return version
    return _read_manifest_backbone_version(capability_root)


def _read_manifest_backbone_version(capability_root: Path) -> str:
    # Adopter installs carry no `.pkit/VERSION`; the canonical backbone
    # version lives in `.pkit/manifest.yaml`'s top-level `backbone_version`.
    # Self-contained per PEP 723 — parse with the already-imported ruamel
    # YAML rather than importing the backbone `project_kit.manifest` reader.
    path = capability_root.parents[1] / "manifest.yaml"
    if YAML is None:
        return _UNKNOWN
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        return _UNKNOWN
    version = data.get("backbone_version") if isinstance(data, dict) else None
    return str(version) if version else _UNKNOWN


def _read_version_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return _UNKNOWN
    return text or _UNKNOWN


def _read_capability_version(capability_root: Path) -> str:
    path = capability_root / "package.yaml"
    if YAML is None:
        return _UNKNOWN
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        return _UNKNOWN
    component = data.get("component") if isinstance(data, dict) else None
    version = component.get("version") if isinstance(component, dict) else None
    return str(version) if version else _UNKNOWN


def _read_cli_version(capability_root: Path) -> str | None:
    """Best-effort resolve the installed `pkit` CLI version.

    Chain, most-authoritative first: an explicit env override (a dispatcher
    may inject it), installed package metadata, the importable package's
    bundled VERSION, then a venv scan near the repo root. None when
    unresolvable — the footer then omits the CLI axis rather than lying.
    """
    override = os.environ.get("PKIT_CLI_VERSION")
    if override:
        return override.strip() or None

    try:
        return importlib.metadata.version("project-kit")
    except importlib.metadata.PackageNotFoundError:
        pass
    except Exception:  # metadata lookup must never break a write.
        pass

    spec = importlib.util.find_spec("project_kit")
    if spec is not None and spec.origin:
        bundled = Path(spec.origin).parent / "_kit" / "VERSION"
        if bundled.is_file():
            v = _read_version_file(bundled)
            if v != _UNKNOWN:
                return v

    repo_root = capability_root.parents[1].parent  # .pkit/.. = repo root
    for version_file in sorted(
        repo_root.glob(".venv/lib/python*/site-packages/project_kit/_kit/VERSION")
    ):
        v = _read_version_file(version_file)
        if v != _UNKNOWN:
            return v
    return None


# --- footer: strip-then-append-exactly-one -----------------------------


def render_footer(versions: Versions) -> str:
    """Build the one footer region. Versions only, no date (DEC-041 item 2).

    Shape obeys the `provenance_marker` constraints: opens with the start
    sentinel, a blank line then a `---` (a thematic break, never a setext
    underline, because a blank line precedes it), a `<sub>` line (no
    leading bullet, no heading, no checkbox, no file:line), then the end
    sentinel.
    """
    line = f"<sub>🧰 pkit · tree `{versions.tree}` · pm `{versions.capability}`"
    if versions.cli is not None:
        line += f" · cli `{versions.cli}`"
        if versions.drifted:
            line += " ⚠"
    line += "</sub>"
    return f"{MARKER_START}\n\n---\n{line}\n{MARKER_END}"


def strip_footer(body: str) -> str:
    """Remove any provenance region: from the first sentinel through EOF.

    Cutting to end-of-document (rather than matching a start/end pair)
    removes complete, partial, orphaned, or doubled regions alike — the
    read/validation-side twin of the write-side append. Trailing blank
    lines left behind are trimmed.
    """
    lines = body.splitlines()
    for i, ln in enumerate(lines):
        if MARKER_START in ln or MARKER_END in ln:
            head = "\n".join(lines[:i])
            return head.rstrip()
    return body.rstrip()


def stamp(body: str, versions: Versions) -> str:
    """Return `body` carrying exactly one current footer.

    Idempotent: strips whatever provenance state the incoming body was in,
    then appends one fresh region. Re-stamping identical versions is a
    no-op diff (the footer carries no date).
    """
    head = strip_footer(body)
    region = render_footer(versions)
    if not head:
        return region + "\n"
    return f"{head}\n\n{region}\n"


# --- filing comment: one-time, immutable -------------------------------


def render_filing_comment(versions: Versions, today: str | None = None) -> str:
    """Build the immutable filing comment body (with idempotency marker)."""
    if today is None:
        today = _dt.date.today().isoformat()
    line = (
        f"🧰 Filed under pkit — tree `{versions.tree}` · pm `{versions.capability}`"
    )
    if versions.cli is not None:
        line += f" · cli `{versions.cli}`"
        if versions.drifted:
            line += " ⚠ (cli ≠ tree)"
    line += f" — {today}"
    return f"{FILING_MARKER}\n\n{line}"


def post_filing_comment(
    issue_number: int,
    capability_root: Path,
    config: dict[str, Any],
    *,
    is_pr: bool = False,
    today: str | None = None,
) -> str:
    """Post the one-time filing comment. Best-effort, idempotent.

    Per DEC-041 item 5 the write is best-effort/report-and-continue: any
    failure returns a status string and never raises, so a failed
    provenance write cannot block the underlying create operation. Skips
    when a comment already carries `FILING_MARKER` (idempotent re-run).
    Returns a one-line human status for the caller to surface.
    """
    # Lazy: the pure footer/version helpers need no gh. Resolve whether
    # imported as a package (`_lib.provenance`, from a script) or by path
    # (`import gh`, from the test harness).
    try:
        from _lib.gh import gh_run
    except ImportError:
        from gh import gh_run

    versions = read_versions(capability_root)
    kind = "pr" if is_pr else "issue"

    # Idempotency: skip if the filing comment already exists.
    try:
        existing = gh_run(
            ["gh", kind, "view", str(issue_number), "--json", "comments"],
            config,
            check=False,
        )
        if existing.returncode == 0 and FILING_MARKER in (existing.stdout or ""):
            return f"provenance: filing comment already present on #{issue_number} (skip)"
    except FileNotFoundError:
        return "provenance: gh not on PATH; filing comment skipped"
    except Exception as exc:  # best-effort; never block the create.
        return f"provenance: filing-comment idempotency check failed ({exc}); skipped"

    body = render_filing_comment(versions, today)
    try:
        proc = gh_run(
            ["gh", kind, "comment", str(issue_number), "--body", body],
            config,
            check=False,
        )
    except FileNotFoundError:
        return "provenance: gh not on PATH; filing comment skipped"
    except Exception as exc:  # best-effort.
        return f"provenance: filing-comment post failed ({exc}); skipped"
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip() or "no stderr"
        print(
            f"provenance: filing-comment post to #{issue_number} failed: {detail}",
            file=sys.stderr,
        )
        return f"provenance: filing comment not posted to #{issue_number} (continuing)"
    drift = " [DRIFT: cli≠tree]" if versions.drifted else ""
    return f"provenance: filing comment posted to #{issue_number}{drift}"
