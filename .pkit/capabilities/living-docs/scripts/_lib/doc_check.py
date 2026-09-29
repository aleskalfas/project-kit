"""This capability's contribution to the documentation-check point (DEC-001 point 7).

`pkit::work-tracking:doc-check` is the data point the provider of the
`pkit::work-tracking` role defines: the documentation obligations a pull
request may owe (project-management DEC-053). This capability contributes the
two kinds a documentation capability owes it (DEC-053 point 4), read from the
backbone's whole-repository friction check, `pkit friction check --all --json`,
which judges HEAD against its history (COR-050):

- **`page-stale`** — one per page of the spaces the check reports `stale` or
  `deferred`: friction debt (COR-050 point 9). Its `document` is the page,
  whose answer in the diff — updated, unchanged with its justification, or
  deferred with its reason — meets it.
- **`code-undocumented`** — one per path of the declared surface that nothing
  anchors (COR-050 point 8). Its `path` is the code; its `document` is where a
  new page of the technical space goes, the internal root (DEC-001 point 1).
  The obligation leaves the point once a page anchors the code, since the
  check reads HEAD: that is how it is met (DEC-053 point 2).

Every obligation's source is `friction` — the signal, never the capability that
reads it, so another provider of the documentation role contributes under the
same enforcement setting — and its id is `friction:<reason>:<page or path>`,
so no two collide in the point's `additive` merge.

**Fail closed.** A check that gives no document, or a page whose friction lies
beyond a shallow clone's history, is no answer — raised, never an empty list:
the point is `fail`, and a gate never passes on fewer obligations than it
should. A repository with no commit owes nothing: there is no HEAD to judge.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

POINT = "pkit::work-tracking:doc-check"
POINT_VERSION = 1

#: The obligations' source, and their two reasons (the point's companion schema).
SOURCE = "friction"
PAGE_STALE = "page-stale"
CODE_UNDOCUMENTED = "code-undocumented"

#: The artefact states the whole-repository check reports that are friction debt.
DEBT_STATES = ("stale", "deferred")
UNREACHABLE = "unreachable"

Runner = Callable[..., subprocess.CompletedProcess[str]]


class NoAnswer(Exception):
    """The friction on the pages cannot be read in full: the filler gives no answer."""


def has_commit(root: str, run: Runner = subprocess.run) -> bool:
    """Whether HEAD names a commit — the history the friction check reads."""
    try:
        proc = run(
            ["git", "rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


def read_friction(root: str, run: Runner = subprocess.run) -> Mapping[str, Any]:
    """The whole-repository check's machine-readable document, through `pkit`.
    Raises NoAnswer when it gives none."""
    argv = ["pkit", "friction", "check", "--all", "--json"]
    try:
        proc = run(argv, cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise NoAnswer(f"`pkit` could not be run ({exc})") from exc
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if proc.returncode != 0 or not isinstance(document, Mapping) or "artefacts" not in document:
        detail = (proc.stderr or "").strip().splitlines()
        raise NoAnswer(
            f"`{' '.join(argv)}` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else "")
        )
    return document


def obligations(
    report: Mapping[str, Any], pages: Iterable[str], internal_root: str
) -> list[dict[str, Any]]:
    """The obligations `report` gives rise to: the pages' friction debt, then the
    uncovered surface, each sorted. Raises NoAnswer when a page's friction
    cannot be judged in this clone."""
    if report.get("dormant"):
        return []
    page_set = set(pages)
    reports = [
        a
        for a in report.get("artefacts") or []
        if isinstance(a, Mapping) and a.get("location") in page_set
    ]
    unjudged = sorted(str(a["location"]) for a in reports if a.get("state") == UNREACHABLE)
    if unjudged:
        raise NoAnswer(
            f"friction on {', '.join(unjudged)} cannot be judged: a point lies beyond this "
            f"shallow clone's history — fetch the full history (`git fetch --unshallow`)"
        )
    findings = [f for f in report.get("findings") or [] if isinstance(f, Mapping)]
    stale = sorted(
        (str(a["location"]), str(a["state"])) for a in reports if a.get("state") in DEBT_STATES
    )
    surface = sorted(str(p) for p in (report.get("measures") or {}).get("uncovered_surface") or [])
    return [
        *(_page_stale(page, state, findings) for page, state in stale),
        *(_code_undocumented(path, internal_root) for path in surface),
    ]


def envelope(value: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The filler envelope the command prints (COR-052 point 6)."""
    return {"schema_version": POINT_VERSION, "value": list(value)}


def _page_stale(page: str, state: str, findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    details = [_detail(f) for f in findings if f.get("location") == page]
    what = ", ".join(d for d in details if d)
    return {
        "id": f"{SOURCE}:{PAGE_STALE}:{page}",
        "source": SOURCE,
        "reason": PAGE_STALE,
        "document": page,
        "description": f"{state}{': ' + what if what else ''} — pkit friction explain {page}",
    }


def _detail(finding: Mapping[str, Any]) -> str:
    """One stale or deferred finding, as a few words: which anchor, and what of it."""
    kind = finding.get("kind")
    anchor = finding.get("anchor")
    if kind not in DEBT_STATES:
        return ""
    if not isinstance(anchor, Mapping):
        return "moved with no revalidation" if kind == "stale" else ""
    verb = "changed" if kind == "stale" else "deferred"
    return f"{anchor.get('kind')} {anchor.get('value')} {verb}"


def _code_undocumented(path: str, internal_root: str) -> dict[str, Any]:
    return {
        "id": f"{SOURCE}:{CODE_UNDOCUMENTED}:{path}",
        "source": SOURCE,
        "reason": CODE_UNDOCUMENTED,
        "document": "**" if internal_root == "." else f"{internal_root}/**",
        "path": path,
        "description": f"{path} is in the declared surface and nothing anchors it — "
        f"anchor it from a page",
    }
