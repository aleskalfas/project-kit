"""The decision ids an issue body cites, and whether a record holds each (DEC-010).

DEC-010 forbids a predicted decision id in a body: an id that no record holds
yet, written as if one did. `body-format.yaml` carries the rule under its id,
`body.predicted-decision-id`, at a warning. Three parts:

- **What a body cites** (`cited`):
  - a core, project or architecture record's id, `COR-NNN`, `PRJ-NNN` or
    `ADR-NNN`, standing alone as a word;
  - a capability's decision named with its capability, as COR-017 cites one,
    `[<capability>:DEC-NNN-<slug>]`, or `<capability>:DEC-NNN` with its slug or
    without. It is looked up by its capability and its number: the slug does not
    decide whether the decision exists;
  - never a bare `DEC-NNN`. A capability numbers its own decisions, so a
    `DEC-NNN` that names no capability names no record, and cannot be told
    predicted from real. It is not checked.

  An id in a fenced code block, an HTML comment, a struck-through span or the
  provenance footer is not read, as the backbone's body parser skips them
  (COR-013).
- **Asking the backbone** (`lookup`): `pkit refs lookup --json -- <id>...`, one
  run for every id a body cites, so the script never looks for a record's file
  itself. The ADR folder is the project's setting, and a capability's decisions
  lie where it is installed. A document of a version this reading does not know,
  or no document at all, is `NotChecked`, with why.
- **The rule** (`findings`): the backbone is asked only for a body that cites.
  Each cited id no record holds is named, in one finding under the rule's label.
  When the records could not be read, one notice under its own label says which
  ids were not checked, and why. Both are at the severity the schema gives the
  rule. Nothing here refuses or changes a verb's exit.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from _lib import body_rules, provenance

#: The rule's id in `body-format.yaml`, the label a cited id that no record holds
#: is reported under; and the label of the notice that the ids were not checked,
#: which is about the check and not against the body.
LABEL = "body.predicted-decision-id"
UNCHECKED = "body.decision-ids-unchecked"

#: The rule's severity where the schema carries no entry for it, as DEC-010 gives it.
DEFAULT_SEVERITY = "warning"

#: The backbone's read command, how long it may take, and the version of its
#: document this reading understands; another is not read.
ARGV = ("pkit", "refs", "lookup", "--json", "--")
TIMEOUT = 30
DOCUMENT_VERSION = 1

#: A record's id standing alone as a word, not the tail of a longer hyphenated
#: token such as a rule's id.
_RECORD = re.compile(r"(?<![\w-])(?:COR|PRJ|ADR)-\d+(?!\w)")
#: A capability's decision with its capability in front, bracketed or not.
_DECISION = re.compile(
    r"(?<![\w-])(?P<capability>[a-z][a-z0-9-]*[a-z0-9]):(?P<number>DEC-\d+)(?!\w)"
)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_STRUCK = re.compile(r"~~[^~\n]+~~")

Runner = Callable[..., subprocess.CompletedProcess[str]]

#: A finding as the validators take one: `(severity, label, detail)`.
Finding = tuple[str, str, str]


@dataclass(frozen=True)
class Answered:
    """What the backbone answered: for each id it answered, whether a record holds it."""

    held: Mapping[str, bool]


@dataclass(frozen=True)
class NotChecked:
    """The records could not be read, and why."""

    why: str


Reading = Answered | NotChecked

#: What asks the backbone for a validator: `lookup`, or a test's stand-in.
Reader = Callable[[Sequence[str]], Reading]


# --- what a body cites ---------------------------------------------------------------


def cited(body: str) -> list[str]:
    """The decision ids `body` cites, each once, in the order first cited: a record's
    id as written, and a capability's decision as `<capability>:DEC-NNN`."""
    text = "\n".join(body_rules.lines_outside_fences(provenance.strip_footer(body)))
    text = _STRUCK.sub(" ", _HTML_COMMENT.sub(" ", text))
    found: list[tuple[int, str]] = [(m.start(), m.group(0)) for m in _RECORD.finditer(text)]
    found += [(m.start(), f"{m['capability']}:{m['number']}") for m in _DECISION.finditer(text)]
    return list(dict.fromkeys(record for _start, record in sorted(found)))


# --- asking the backbone -------------------------------------------------------------


def lookup(ids: Sequence[str], run: Runner = subprocess.run) -> Reading:
    """Whether a record holds each of `ids`, through `pkit refs lookup --json`, which
    exits 0 whether an id resolves or not. No document at all, as from a `pkit`
    that is absent, a backbone that predates the command, a crash or no answer in
    time, is NotChecked."""
    argv = [*ARGV, *ids]
    try:
        proc = run(argv, capture_output=True, text=True, check=False, timeout=TIMEOUT)
    except FileNotFoundError:
        return NotChecked("`pkit` is not on PATH")
    except subprocess.TimeoutExpired:
        return NotChecked(f"`pkit refs lookup` did not answer within {TIMEOUT}s")
    except OSError as exc:
        return NotChecked(f"`pkit` could not be run ({exc})")
    stderr = proc.stderr or ""
    if proc.returncode != 0 and ("No such command" in stderr or "No such option" in stderr):
        return NotChecked(
            "the installed backbone predates `pkit refs lookup --json`; upgrade it (`pkit upgrade`)"
        )
    try:
        document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        detail = [line for line in stderr.strip().splitlines() if line]
        return NotChecked(
            f"`pkit refs lookup --json` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else "")
        )
    return reading_of(document)


def reading_of(document: Mapping[str, Any]) -> Reading:
    """What a `pkit refs lookup --json` document says of each id it answers. A
    document of a version this reading does not know is NotChecked."""
    version = document.get("schema_version")
    if version != DOCUMENT_VERSION:
        return NotChecked(
            f"`pkit refs lookup` answered schema_version {version!r}; this reading "
            f"understands {DOCUMENT_VERSION}"
        )
    held: dict[str, bool] = {}
    lookups = document.get("lookups")
    for entry in lookups if isinstance(lookups, list) else []:
        if (
            isinstance(entry, Mapping)
            and isinstance(entry.get("id"), str)
            and isinstance(entry.get("resolved"), bool)
        ):
            held[entry["id"]] = entry["resolved"]
    return Answered(held)


# --- the rule ------------------------------------------------------------------------


def findings(body: str, body_format: Mapping[str, Any], read: Reader | None) -> list[Finding]:
    """What the rule reports on `body`. Nothing, and the backbone is not asked, where
    no reader is given or the body cites no decision id."""
    if read is None:
        return []
    ids = cited(body)
    if not ids:
        return []
    severity = body_rules.rule_severity(body_format, LABEL, DEFAULT_SEVERITY)
    return judge(ids, read(ids), severity)


def judge(ids: Sequence[str], reading: Reading, severity: str) -> list[Finding]:
    """What the rule says of the cited `ids`, read against `reading`: one finding
    naming the ids that no record holds, and one notice naming those not checked."""
    if not ids:
        return []
    if isinstance(reading, NotChecked):
        detail = (
            f"decision ids not checked ({_enumerate(ids)}): the records could not be "
            f"read — {reading.why}. None is reported as predicted on that ground."
        )
        return [(severity, UNCHECKED, detail)]
    unheld = [record for record in ids if reading.held.get(record) is False]
    unanswered = [record for record in ids if record not in reading.held]
    out: list[Finding] = []
    if unheld:
        detail = (
            f"cites {_enumerate(unheld)}, which no record holds. Cite a decision only "
            "once its record exists, and describe one not yet written without an id."
        )
        out.append((severity, LABEL, detail))
    if unanswered:
        detail = (
            f"decision ids not checked ({_enumerate(unanswered)}): `pkit refs lookup` "
            "gave no answer for them. None is reported as predicted on that ground."
        )
        out.append((severity, UNCHECKED, detail))
    return out


def _enumerate(ids: Sequence[str]) -> str:
    if len(ids) == 1:
        return ids[0]
    return f"{', '.join(ids[:-1])} and {ids[-1]}"
