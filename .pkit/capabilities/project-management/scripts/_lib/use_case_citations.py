"""Use-case citations in an issue body ([project-management:DEC-054-use-case-validation]).

Where the software-analysis capability is installed, an issue body may cite the
project's use cases by id — `UC-NNN`, numbered within the project
([software-analysis:DEC-001-software-analysis-discipline] point 3). A number is
settled only when its use case reaches the default branch, so a cited id that
is not a use case there is reported as a predicted decision id is: a warning,
the severity `body-format.yaml` gives both rules.

Three parts, so the validators that call them stay pure:

- `cited_use_cases(body)` — the ids a body cites.
- `read_for(body, repo_root, config)` — what validating the body needs: None
  when it cites no use case or software-analysis is not installed (the rule is
  inert), else the use cases on the default branch, or why they could not be
  read.
- `check(body, use_cases)` — the findings, as `(severity, label, detail)`.

**Installed** is the test every contribution from another capability passes:
software-analysis is registered in `.pkit/manifest.yaml`'s `components:`
(`contribution_collector.list_registered_capabilities`), whatever is on disk.

**The default branch** is the project's `default_branch` (`main` when the
configuration declares none), read at its remote-tracking ref `origin/<branch>`
when the clone has one — the closest local view of what has landed — else at
the local branch. Every read is made at the one commit that ref names.

**Where the use cases lie** is software-analysis's `analysis` location, read as
the backbone reads a capability's documentation location (COR-049): a location
recorded in the capability's `project/docs-locations.yaml` wins; else the one
its package metadata declares under `docs.locations`, under the root it names;
else the `analysis` sub-path of the internal documentation root, where the
software-analysis record puts it. The pm scripts do not import the backbone, so
this module mirrors `project_kit.docs_roots.read_capability_locations`, and
reads its files at the default branch rather than in the working tree.

**A use case** is a Markdown file anywhere under that location whose front
matter carries an `id` in the `UC-NNN` form, as software-analysis's use-case
template does. Grouping folders, file names and status do not matter: a
withdrawn use case keeps its file and its id.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

# The shared contribution-collector core owns the install test. Same import
# fallback as its other consumers, so this module loads both as
# `_lib.use_case_citations` and standalone via spec-loading in tests.
try:
    from _lib.contribution_collector import default_load_yaml, list_registered_capabilities
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from contribution_collector import (  # type: ignore[no-redef]
        default_load_yaml,
        list_registered_capabilities,
    )

CAPABILITY = "software-analysis"

#: The location name software-analysis declares for its artefacts, and the
#: sub-path of the internal root it lies at when nothing else says otherwise.
LOCATION = "analysis"

#: The severity of the predicted-decision-id rule, which this rule shares
#: (`body-format.yaml`'s universal body rules).
SEVERITY = "warning"
LABEL = "body.use-case-citation"
LABEL_UNVERIFIED = "body.use-case-citation.unverified"

#: A use-case id as a body cites it, and as a use case carries it.
CITATION = re.compile(r"\bUC-\d{3,}\b")
USE_CASE_ID = re.compile(r"^UC-\d{3,}$")

_MANIFEST = Path(".pkit") / "manifest.yaml"
_BACKBONE_CONFIG = PurePosixPath(".pkit") / "project" / "config.yaml"
_CAPABILITY_DIR = PurePosixPath(".pkit") / "capabilities" / CAPABILITY
_PACKAGE = _CAPABILITY_DIR / "package.yaml"
_RECORDED = _CAPABILITY_DIR / "project" / "docs-locations.yaml"

#: The documentation roots' default, and the audiences a location may name.
_DEFAULT_ROOT = "docs"
_INTERNAL = "internal"
_AUDIENCES = (_INTERNAL, "user")

_FRONT_MATTER_FENCE = "---"


@dataclass(frozen=True)
class UseCases:
    """The use cases on the default branch: the ref read, where, and their ids."""

    ref: str
    location: str
    ids: frozenset[str]


@dataclass(frozen=True)
class Unreadable:
    """The use cases on the default branch could not be read, and why."""

    reason: str


# --- the rule ------------------------------------------------------------------


def cited_use_cases(body: str) -> list[str]:
    """The use-case ids `body` cites, each once, in the order first cited."""
    return list(dict.fromkeys(CITATION.findall(body)))


def check(body: str, use_cases: UseCases | Unreadable | None) -> list[tuple[str, str, str]]:
    """The findings for the use cases `body` cites, as `(severity, label, detail)`.

    None — software-analysis not installed, or nothing cited — gives none. An
    unreadable default branch gives one finding saying the citations were not
    checked, never one reporting them unknown.
    """
    cited = cited_use_cases(body)
    if use_cases is None or not cited:
        return []
    if isinstance(use_cases, Unreadable):
        return [
            (
                SEVERITY,
                LABEL_UNVERIFIED,
                f"could not read the use cases on the default branch "
                f"({use_cases.reason}), so {_enumerate(cited)} "
                f"{'was' if len(cited) == 1 else 'were'} not checked. This is not "
                f"a report that {'it does' if len(cited) == 1 else 'they do'} "
                f"not exist.",
            )
        ]
    unknown = [uc for uc in cited if uc not in use_cases.ids]
    if not unknown:
        return []
    return [
        (
            SEVERITY,
            LABEL,
            f"cites {_enumerate(unknown)}, which "
            f"{'is not a use case' if len(unknown) == 1 else 'are not use cases'} "
            f"on the default branch ({use_cases.ref}, under {use_cases.location}/). "
            f"Cite only use cases that have landed: like a decision id, a "
            f"use-case number is a guess until then (DEC-054).",
        )
    ]


def _enumerate(ids: Sequence[str]) -> str:
    if len(ids) == 1:
        return ids[0]
    return f"{', '.join(ids[:-1])} and {ids[-1]}"


# --- what validating a body needs ----------------------------------------------


def read_for(body: str, repo_root: Path, config: Mapping[str, Any]) -> UseCases | Unreadable | None:
    """The use cases validating `body` is checked against.

    None when the body cites no use case, or when software-analysis is not
    installed: the rule is inert, and nothing is read. `config` is this
    capability's project configuration, for `default_branch`.
    """
    if not cited_use_cases(body):
        return None
    installed = _installed(repo_root)
    if installed is None:
        return Unreadable("the project manifest could not be read")
    if not installed:
        return None
    return default_branch_use_cases(repo_root, str(config.get("default_branch") or "main"))


def _installed(repo_root: Path) -> bool | None:
    """Whether software-analysis is registered in the manifest; None when the
    manifest cannot be read."""
    try:
        manifest = default_load_yaml(repo_root / _MANIFEST)
    except (OSError, RuntimeError):
        return None
    return CAPABILITY in list_registered_capabilities(manifest)


def default_branch_use_cases(repo_root: Path, branch: str) -> UseCases | Unreadable:
    """The use cases on `branch`, read at its remote-tracking ref when the clone
    has one, else at the local branch."""
    resolved = _resolve(repo_root, branch)
    if resolved is None:
        return Unreadable(f"neither origin/{branch} nor {branch} resolves in this clone")
    ref, commit = resolved
    settings = _read_texts(
        repo_root, commit, [str(p) for p in (_BACKBONE_CONFIG, _PACKAGE, _RECORDED)]
    )
    if settings is None:
        return Unreadable(f"git could not read {ref}")
    location = analysis_location(
        backbone_config=_parse_yaml(settings.get(str(_BACKBONE_CONFIG))),
        package=_parse_yaml(settings.get(str(_PACKAGE))),
        recorded=_parse_yaml(settings.get(str(_RECORDED))),
    )
    paths = _markdown_under(repo_root, commit, location)
    texts = _read_texts(repo_root, commit, paths) if paths is not None else None
    if texts is None:
        return Unreadable(f"git could not read {location}/ at {ref}")
    ids = {uc for text in texts.values() if (uc := front_matter_id(text)) is not None}
    return UseCases(ref=ref, location=location, ids=frozenset(ids))


# --- where the use cases lie ---------------------------------------------------


def analysis_location(*, backbone_config: Any, package: Any, recorded: Any) -> str:
    """software-analysis's `analysis` location, repository-relative, from the
    parsed backbone configuration, package metadata and recorded locations.

    Recorded > declared under its root > the `analysis` sub-path of the internal
    root. A declaration in another shape than `{path, root?}` reads as absent;
    `pkit validate` reports it.
    """
    recorded_path = _mapping(_mapping(recorded).get("locations")).get(LOCATION)
    if isinstance(recorded_path, str) and recorded_path.strip():
        return _normalise(recorded_path)
    sub_path, audience = LOCATION, _INTERNAL
    declared = _mapping(_mapping(_mapping(package).get("docs")).get("locations")).get(LOCATION)
    if isinstance(declared, Mapping):
        path = declared.get("path")
        root = declared.get("root", _INTERNAL)
        if isinstance(path, str) and path.strip() and root in _AUDIENCES:
            sub_path, audience = path, str(root)
    return _normalise(f"{_root(backbone_config, audience)}/{sub_path}")


def _root(backbone_config: Any, audience: str) -> str:
    """The documentation root for `audience`; the default where the value is not
    a non-empty relative path."""
    value = _mapping(_mapping(backbone_config).get("docs")).get(audience)
    if isinstance(value, str) and value.strip() and not PurePosixPath(value).is_absolute():
        return value
    return _DEFAULT_ROOT


def _normalise(path: str) -> str:
    """A repository-relative path without trailing slashes or `.` segments."""
    parts = [p for p in path.strip().replace("\\", "/").split("/") if p and p != "."]
    return "/".join(parts) or "."


# --- a use case ----------------------------------------------------------------


def front_matter_id(text: str) -> str | None:
    """The `UC-NNN` id in a Markdown file's front matter, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONT_MATTER_FENCE:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONT_MATTER_FENCE:
            value = _mapping(_parse_yaml("\n".join(lines[1:index]))).get("id")
            if isinstance(value, str) and USE_CASE_ID.match(value.strip()):
                return value.strip()
            return None
    return None


# --- git at the default branch -------------------------------------------------


def _resolve(repo_root: Path, branch: str) -> tuple[str, str] | None:
    """The first of `origin/<branch>`, `<branch>` naming a commit, with that commit."""
    for ref in (f"origin/{branch}", branch):
        proc = _git(repo_root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if proc is not None and proc.returncode == 0:
            return ref, proc.stdout.decode("utf-8").strip()
    return None


def _markdown_under(repo_root: Path, commit: str, location: str) -> list[str] | None:
    """Every Markdown file under `location` at `commit`; None when git fails."""
    proc = _git(repo_root, "ls-tree", "-r", "-z", "--name-only", commit, "--", location)
    if proc is None or proc.returncode != 0:
        return None
    names = proc.stdout.decode("utf-8").split("\0")
    # A name with a newline cannot be asked of `cat-file --batch`, which reads
    # one object per line.
    return [n for n in names if n.endswith(".md") and "\n" not in n]


def _read_texts(repo_root: Path, commit: str, paths: Sequence[str]) -> dict[str, str] | None:
    """The text of each of `paths` at `commit` that is a file there, read in one
    `git cat-file --batch`; a path missing at `commit` is left out. None when
    git fails."""
    if not paths:
        return {}
    request = "".join(f"{commit}:{path}\n" for path in paths).encode("utf-8")
    proc = _git(repo_root, "cat-file", "--batch", stdin=request)
    if proc is None or proc.returncode != 0:
        return None
    out, position = proc.stdout, 0
    texts: dict[str, str] = {}
    for path in paths:
        end = out.find(b"\n", position)
        if end < 0:
            return None
        # `<sha> <type> <size>` then the content and a newline; `<name> missing`
        # (or `ambiguous`) alone otherwise.
        fields = out[position:end].split(b" ")
        position = end + 1
        if len(fields) == 3 and fields[2].isdigit():
            size = int(fields[2])
            if fields[1] == b"blob":
                texts[path] = out[position : position + size].decode("utf-8", errors="replace")
            position += size + 1
    return texts


def _git(
    repo_root: Path, *args: str, stdin: bytes | None = None
) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=repo_root, input=stdin, capture_output=True, check=False
        )
    except OSError:
        return None


# --- forgiving reads -----------------------------------------------------------


def _parse_yaml(text: str | None) -> Any:
    if text is None:
        return None
    try:
        return YAML(typ="safe").load(text)
    except YAMLError:
        return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
