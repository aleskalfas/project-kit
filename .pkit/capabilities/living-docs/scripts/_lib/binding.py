"""Where the shared method's rules bind on the pages, read as the backbone answers it.

An accepted rule binds on an artefact where a route leads to the rule's set from
a set of the project's own whose scope selects the artefact, with no pin on it
behind its set (COR-051 point 7). `LDOC` takes no scope, as no method rule set
does, so its rules bind on a page only through such a set: the page's space
definition, scoped to the space's pages (DEC-001 points 2 and 3).

The backbone gives that one answer for every artefact, and a check reads it
(COR-051, Implications). A capability script runs in its own environment and
never imports the backbone, so it reads the answer through the backbone's read
command, `pkit rule-sets reach --json` (the CLI README, "Rule-set commands"),
and never walks a route, reads a scope or judges a pin itself.

The validator enforces the parts of `LDOC`'s rules its set declares under
`checks` (COR-051 point 2; DEC-001 point 6), each only where its rule binds: a
page's structure where RS-LDOC-004 binds on it, and its reader where RS-LDOC-003
binds (DEC-001 point 3).

The answer is read by its keys (ADR-097 point 3). A key the reading needs that is
missing, null, of another type, or a kind of artefact it does not know, is an
answer it cannot tell anything from: `Unreadable`. Read as nothing binding, it
would leave a page unchecked where a rule binds on it.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _lib import backbone
from _lib import document_keys as keys

#: The document version this reading understands (the CLI reference, "Rule-set
#: commands"). A later backbone raises it only when a key or a value of a set goes,
#: and no key or value comes to mean anything else; the reading refuses a version
#: other than this one.
SCHEMA_VERSION = 1

ARGV = ("pkit", "rule-sets", "reach", "--json")

#: How the answer names a whole document, as against an entry of a collection file.
DOCUMENT, ENTRY = "document", "entry"

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Unreadable(Exception):
    """The backbone's read command gave no answer this reading understands."""


@dataclass(frozen=True)
class Binding:
    """The accepted rules that bind on each document artefact, by its file's path,
    each cited as the backbone cites it: with the component in front for a rule of
    a method rule set, `living-docs:RS-LDOC-004`. A document the answer does not
    list has no rule binding on it."""

    rules: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def binds(self, path: str, rule: str) -> bool:
        """Whether `rule`, as cited, binds on the document at `path`."""
        return rule in self.rules.get(path, frozenset())


def read_binding(root: Path, run: Runner = backbone.run) -> Binding:
    """Where the rules bind in the project at `root`, at its working tree, through
    `pkit rule-sets reach --json`. Raises Unreadable when there is no answer to
    read: `pkit` absent, a backbone without the command, a configuration it cannot
    read, a crash."""
    try:
        proc = run(list(ARGV), cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise Unreadable(f"`pkit` could not be run ({exc})") from exc
    try:
        document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        detail = (proc.stderr or "").strip().splitlines()
        raise Unreadable(
            f"`{' '.join(ARGV)}` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else "")
        )
    return binding_of(document)


def binding_of(document: Mapping[str, Any]) -> Binding:
    """The `pkit rule-sets reach --json` document as a Binding. Raises Unreadable for
    a version other than this reading's, and for an answer it cannot tell anything
    from at a key it reads (ADR-097 point 3)."""
    version = document.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise Unreadable(
            f"`{' '.join(ARGV)}` answered schema_version {version!r}; "
            f"this capability reads {SCHEMA_VERSION}"
        )
    if not isinstance(document.get("artefacts"), list):
        raise Unreadable(f"`{' '.join(ARGV)}` answered without its artefacts")
    try:
        return Binding(_rules(document))
    except keys.Untold as exc:
        raise Unreadable(
            f"`{' '.join(ARGV)}` answered a document this capability cannot read: {exc}"
        ) from exc


def _rules(document: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    """The rules that bind on each document artefact, by its path. An entry of a
    collection file is no page, so it is left out."""
    rules: dict[str, frozenset[str]] = {}
    for where, entry in keys.objects(document, "artefacts", ""):
        if keys.one_of(entry, "kind", where, (DOCUMENT, ENTRY)) != DOCUMENT:
            continue
        rules[keys.text(entry, "path", where)] = frozenset(
            keys.text(rule, "rule", inner) for inner, rule in keys.objects(entry, "rules", where)
        )
    return rules
