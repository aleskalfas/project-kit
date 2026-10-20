"""What a fixer hands back, read by the run's contract (DEC-056 points 3 and 6).

A fixer ends its final message with one result line for each artefact its
brief names, and writes an answer for each artefact it proposes. This module
reads both, by the contract this capability sets for every fixer. The contract
is data, `schemas/fixer-contract.yaml`: the lead each result line starts with,
the three forms of a line, and the `none` reasons with what clears each. The
answer's fields are `schemas/fixer-answer.schema.json`. Nothing here reads
prose: a code on the line, and the answer's fields, decide.

- `load` reads the contract and checks it against its companion schema.
- `read_results` reads a fixer's final message (DEC-056 point 3). Every line
  that, stripped of the whitespace around it, starts with the lead is a result
  line. A fenced block's lines count the same, and a fence's own lines never
  start with the lead. A line must name the fixer the command started, one of
  the brief's names exactly, and, on a `none` line, one of the reasons. Any
  other result line is read for nothing, and reported. An artefact with no
  line, or more than one, gets no result: it counts as `failed`, with why.
- `read_answer` reads one artefact's answer: `<artefact>/answer.json` in the
  run's files. It must be a plain file, pass the schema and name the same
  artefact. Its diff must be a plain file in the artefact's own folder, and edit
  the artefact's own file and nothing else. A diff that names another file is a
  breach, and its proposal is set aside (DEC-056 point 6). Any other fault
  gives the artefact no result.
- `settle` applies `read_answer` to each proposed result, and fails a held or
  `none` artefact whose folder holds an answer.
- `standing` says whether a `none` stands, and under which class, or passes
  to the next run.

What gives the run as a whole no result, such as the wall-clock limit, is the
drift command's: it marks each artefact `failed` itself.
"""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cache
from pathlib import Path
from typing import Any

try:  # ruamel is declared by every pm script's PEP 723 header.
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # pragma: no cover — ruamel is in the kit's pyproject
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]

#: The capability's schemas: the contract as data, its companion, and the answer's.
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
CONTRACT_FILE = SCHEMAS / "fixer-contract.yaml"
CONTRACT_SCHEMA = SCHEMAS / "fixer-contract.schema.json"
ANSWER_SCHEMA = SCHEMAS / "fixer-answer.schema.json"

#: The version of the contract file this module reads.
SCHEMA_VERSION = 1

#: The states a result line gives an artefact, as the forms are keyed, and the
#: two states a reading adds: no result, and a proposal set aside as a breach is.
PROPOSED = "proposed"
HELD = "held"
NONE = "none"
FAILED = "failed"
SET_ASIDE = "set-aside"

#: What clears a `none` reason, as the contract's `cleared-by` names it.
BY_ARTEFACT = "artefact"
BY_SETUP = "setup"
BY_NEXT_RUN = "next-run"

#: The reason an artefact with no result counts under, and how many runs in a
#: row it fails before it stands as a setup's fault does (DEC-056 point 3).
FAILED_REASON = "failed"
FAILURES_TO_STAND = 2

#: The placeholders a form may hold, and the name each takes in a reading.
_PLACEHOLDERS = {
    "<agent>": "agent",
    "<artefact>": "artefact",
    "<reason>": "reason",
    "<the question>": "words",
    "<the reason in words>": "words",
}
_PLACEHOLDER = re.compile(r"<[^<>]+>")
#: A reason as a line may write one: a code of lowercase words joined by hyphens.
_CODE = r"[a-z]+(?:-[a-z]+)*"


class ContractError(Exception):
    """The contract's data cannot be read, or is off its own shape."""


# --- the contract ----------------------------------------------------------------------


@dataclass(frozen=True)
class Contract:
    """The run's contract as `fixer-contract.yaml` holds it."""

    contract_version: int
    lead: str
    forms: Mapping[str, str]  # state -> form
    reasons: Mapping[str, str]  # reason -> what clears it
    patterns: tuple[tuple[str, re.Pattern[str]], ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if not self.patterns:
            object.__setattr__(self, "patterns", _patterns(self))

    @property
    def answer_file(self) -> str:
        """The answer's file name in an artefact's folder, as the proposed form names
        it: `answer.json`."""
        found = re.search(r"`<artefact>/([^`/]+)`", self.forms[PROPOSED])
        assert found is not None  # `load` checks it
        return found.group(1)

    def cleared_by(self, reason: str) -> str:
        """What clears `reason`: `artefact`, `setup` or `next-run`. ValueError for a
        reason the contract does not list."""
        if reason not in self.reasons:
            raise ValueError(f"{reason!r} is not a `none` reason of the contract")
        return self.reasons[reason]


def load(path: Path = CONTRACT_FILE) -> Contract:
    """The contract at `path`, checked against its companion schema and against the
    rules the schema cannot hold. Raises ContractError when it is not one."""
    if YAML is None:  # pragma: no cover — ruamel is in the kit's pyproject
        raise ContractError("ruamel.yaml is not installed")
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError) as exc:
        raise ContractError(f"{path.name} cannot be read: {exc}") from exc
    if not isinstance(data, Mapping) or data.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"{path.name} is not a contract of version {SCHEMA_VERSION}")
    errors = _schema_errors(path.parent / CONTRACT_SCHEMA.name, data)
    if errors:
        raise ContractError(f"{path.name} is off its schema: {errors}")
    forms = {str(k): str(v) for k, v in data["forms"].items()}
    reasons = {str(k): str(v["cleared-by"]) for k, v in data["reasons"].items()}
    lead = str(data["lead"])
    for state, form in forms.items():
        if not form.startswith(lead):
            raise ContractError(f"{path.name}: the {state} form does not start with the lead")
        unknown = [p for p in _PLACEHOLDER.findall(form) if p not in _PLACEHOLDERS]
        if unknown:
            raise ContractError(f"{path.name}: the {state} form holds {', '.join(unknown)}")
    if not re.search(r"`<artefact>/[^`/]+`", forms[PROPOSED]):
        raise ContractError(f"{path.name}: the proposed form names no answer file")
    if reasons.get(FAILED_REASON) != BY_NEXT_RUN:
        raise ContractError(f"{path.name}: `{FAILED_REASON}` is not cleared by the next run")
    return Contract(int(data["contract_version"]), lead, forms, reasons)


@cache
def _default() -> Contract:
    return load()


def _schema_errors(schema_path: Path, instance: Any) -> str:
    """The first errors of `instance` against the JSON Schema at `schema_path`, or ""
    when it passes. A schema or validator that cannot be loaded is an error too."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover — jsonschema is in the kit's pyproject
        return "jsonschema is not installed, so nothing can be checked"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"{schema_path.name} cannot be read ({exc})"
    found = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    shown = [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}" for e in found[:3]]
    return "; ".join(shown) + (f"; and {len(found) - 3} more" if len(found) > 3 else "")


def _patterns(contract: Contract) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Each form as a pattern, keyed by the state it gives. The agent and the reason
    are taken as any such token, so a line for another agent, or with a reason off
    the list, is told apart from one off the grammar."""
    out = []
    for state, form in contract.forms.items():
        parts, seen, at = [], set(), 0
        for found in _PLACEHOLDER.finditer(form):
            parts.append(re.escape(form[at : found.start()]))
            at = found.end()
            name = _PLACEHOLDERS[found.group(0)]
            if name in seen:
                parts.append(f"(?P={name})")
            elif name == "agent":
                parts.append(r"(?P<agent>[^()\s]+)")
            elif name == "artefact":
                parts.append(r"(?P<artefact>[^`]+)")
            elif name == "reason":
                parts.append(f"(?P<reason>{_CODE})")
            else:
                parts.append(r"(?P<words>\S.*)")
            seen.add(name)
        parts.append(re.escape(form[at:]))
        out.append((state, re.compile("".join(parts))))
    return tuple(out)


# --- the result lines ----------------------------------------------------------------------


@dataclass(frozen=True)
class Line:
    """One result line as the grammar reads it, for whichever agent it names."""

    agent: str
    state: str
    artefact: str
    reason: str | None = None
    words: str | None = None


def result_lines(output: str, contract: Contract | None = None) -> list[str]:
    """The lines of a fixer's final message read as result lines, each stripped:
    the message split at each line feed, and every line that starts with the lead."""
    lead = (contract or _default()).lead
    lines = (line.strip() for line in output.split("\n"))
    return [line for line in lines if line.startswith(lead)]


def parse_line(line: str, contract: Contract | None = None) -> Line | str:
    """The result `line` gives, or why it is off the grammar: no form matches it, or
    its `none` reason is not on the list."""
    contract = contract or _default()
    stripped = line.strip()
    for state, pattern in contract.patterns:
        matched = pattern.fullmatch(stripped)
        if matched is None:
            continue
        groups = matched.groupdict()
        reason = groups.get("reason")
        if reason is not None and reason not in contract.reasons:
            return f"its reason `{reason}` is not one of the contract's `none` reasons"
        return Line(groups["agent"], state, groups["artefact"], reason, groups.get("words"))
    return "it matches none of the contract's forms"


@dataclass(frozen=True)
class Result:
    """What a run gave one artefact the brief names."""

    artefact: str
    state: str  # proposed, held, none, failed, or set-aside once settled
    reason: str | None = None  # a none line's code
    words: str | None = None  # a held line's question, or a none line's reason in words
    answer: str | None = None  # a proposed line's answer file, relative to the run's files
    why: str | None = None  # why it has no result, or was set aside
    read: Answer | None = None  # a proposed result's answer, once settled


@dataclass(frozen=True)
class Ignored:
    """A result line read for nothing, and why."""

    line: str
    why: str


@dataclass(frozen=True)
class Results:
    """A run's results: one for each of the brief's names, in its order, and each
    result line read for nothing."""

    of: Mapping[str, Result]
    ignored: tuple[Ignored, ...] = ()


def read_results(
    output: str, agent: str, names: Sequence[str], contract: Contract | None = None
) -> Results:
    """The result each of the brief's `names` gets from the final message `output`
    of the fixer `agent` (DEC-056 point 3)."""
    contract = contract or _default()
    named = list(dict.fromkeys(names))
    lines: dict[str, list[Line]] = {name: [] for name in named}
    ignored: list[Ignored] = []
    for text in result_lines(output, contract):
        read = parse_line(text, contract)
        if isinstance(read, str):
            ignored.append(Ignored(text, read))
        elif read.agent != agent:
            ignored.append(Ignored(text, f"it is for agent {read.agent}, not {agent}"))
        elif read.artefact not in lines:
            ignored.append(Ignored(text, "it names an artefact the brief does not name"))
        else:
            lines[read.artefact].append(read)
    of: dict[str, Result] = {}
    for name in named:
        found = lines[name]
        if not found:
            of[name] = Result(name, FAILED, why="no result line names it")
        elif len(found) > 1:
            of[name] = Result(name, FAILED, why=f"{len(found)} result lines name it")
        else:
            line = found[0]
            answer = f"{name}/{contract.answer_file}" if line.state == PROPOSED else None
            of[name] = Result(name, line.state, line.reason, line.words, answer)
    return Results(of, tuple(ignored))


# --- the answers -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """An answer that passed every check: its fields as the schema holds them, and
    its files."""

    artefact: str
    fields: Mapping[str, Any]
    path: Path
    diff: Path | None

    @property
    def outcome(self) -> str:
        return str(self.fields["outcome"])


@dataclass(frozen=True)
class Unread:
    """Why an answer gives its artefact no result. A breach sets the proposal aside,
    as a breach of the run is (DEC-056 point 6)."""

    why: str
    breach: bool = False

    def __str__(self) -> str:
        return self.why


def read_answer(
    files_root: Path,
    artefact: str,
    answer_rel: str | None = None,
    contract: Contract | None = None,
) -> Answer | Unread:
    """The answer the run's files at `files_root` hold for `artefact`, or why it
    gives the artefact no result. `answer_rel`, where given, must be the file the
    proposed form names, `<artefact>/answer.json`."""
    contract = contract or _default()
    expected = f"{artefact}/{contract.answer_file}"
    if answer_rel is not None and answer_rel != expected:
        return Unread(f"the answer is named {answer_rel!r}, not {expected!r}")
    parts = _parts(artefact)
    if parts is None:
        return Unread(f"{artefact!r} is no plain path inside the run's files")
    path = files_root.joinpath(*parts, contract.answer_file)
    problem = _plain_file(files_root, [*parts, contract.answer_file])
    if problem:
        return Unread(f"its answer {expected}: {problem}")
    try:
        fields = json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_no_twice)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return Unread(f"its answer {expected} cannot be read as JSON: {exc}")
    errors = _schema_errors(ANSWER_SCHEMA, fields)
    if errors:
        return Unread(f"its answer {expected} is refused by the schema: {errors}")
    if fields["artefact"] != artefact:
        return Unread(f"its answer {expected} is written for another artefact")
    diff_rel = fields["diff"]
    if diff_rel is None:
        return Answer(artefact, fields, path, None)
    diff_parts = _parts(diff_rel)
    if diff_parts is None or diff_parts[: len(parts)] != parts or len(diff_parts) <= len(parts):
        return Unread(f"its diff {diff_rel} is not in the artefact's folder")
    problem = _plain_file(files_root, diff_parts)
    if problem:
        return Unread(f"its diff {diff_rel}: {problem}")
    diff = files_root.joinpath(*diff_parts)
    try:
        text = diff.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return Unread(f"its diff {diff_rel} cannot be read: {exc}")
    found = diff_problem(text, own_file(artefact))
    if found is not None:
        why, breach = found
        return Unread(f"its diff {diff_rel} {why}", breach=breach)
    return Answer(artefact, fields, path, diff)


def _no_twice(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """A JSON object, refused where it names a key twice: the person would read one
    value, and a reader might take the other."""
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"the key {key!r} is given twice")
        out[key] = value
    return out


def _parts(relative: str) -> list[str] | None:
    """`relative` split at each `/`, or None where it is no plain relative path: an
    absolute one, or one with an empty, `.` or `..` part."""
    if not relative or relative.startswith("/") or "\\" in relative or "\0" in relative:
        return None
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return parts


def _plain_file(root: Path, parts: Sequence[str]) -> str:
    """Why `root/parts…` is not a plain file reached through plain folders, or "".
    No part may be a link, so nothing reads outside the run's files."""
    at = root
    for index, part in enumerate(parts):
        at = at / part
        try:
            mode = os.lstat(at).st_mode
        except FileNotFoundError:
            return "it does not exist"
        except OSError as exc:
            return f"it cannot be read ({exc})"
        if stat.S_ISLNK(mode):
            return f"{'/'.join(parts[: index + 1])} is a link"
        last = index == len(parts) - 1
        if not last and not stat.S_ISDIR(mode):
            return f"{'/'.join(parts[: index + 1])} is not a folder"
        if last and not stat.S_ISREG(mode):
            return "it is not a plain file"
    return ""


def own_file(artefact: str) -> str:
    """The repository file an artefact lives in: its name up to any `#`, which names
    an entry in a collection file."""
    return artefact.split("#", 1)[0]


_HUNK = re.compile(r"@@ -\d+(?:,(?P<old>\d+))? \+\d+(?:,(?P<new>\d+))? @@(?: .*)?")
#: Git's extended header lines that change a file's name, mode or kind, never its text.
_RENAMES = ("rename from ", "rename to ", "copy from ", "copy to ")
_NOT_TEXT = (
    "new file mode",
    "deleted file mode",
    "old mode",
    "new mode",
    "similarity index",
    "dissimilarity index",
    "Binary files ",
    "GIT binary patch",
)
_DEV_NULL = "/dev/null"


def diff_problem(text: str, own: str) -> tuple[str, bool] | None:
    """Why the unified diff `text` does not edit the file `own` alone, and whether
    that is a breach, or None. Every file header must read `--- a/<own>` and
    `+++ b/<own>`, as `git apply` reads them. A header naming another file is a
    breach. `/dev/null`, a rename, a mode or a binary patch, a line outside the
    diff's grammar, and a diff with no hunk give the artefact no result. The diff is
    read on past such a fault while its grammar holds, so a later file it reaches
    is still found as a breach."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    old_left = new_left = hunks = 0
    old_header: str | None = None
    in_file = False
    fault: str | None = None  # the first fault short of a breach
    for number, line in enumerate(lines, start=1):
        if old_left or new_left:
            tag = line[:1]
            if tag in (" ", "") and old_left and new_left:
                old_left, new_left = old_left - 1, new_left - 1
            elif tag == "-" and old_left:
                old_left -= 1
            elif tag == "+" and new_left:
                new_left -= 1
            elif tag != "\\":
                return f"breaks its hunk at line {number}", False
            continue
        if line.startswith("\\"):
            continue
        if line.startswith("diff --git "):
            pair = line.removeprefix("diff --git ")
            if pair != f"a/{own} b/{own}":
                named = _git_pair(pair)
                if named is None:
                    return f"reaches a file other than {own} at line {number}", True
                for side in named:
                    if side != own:
                        return f"reaches {side}, not only {own}", True
            in_file, old_header = False, None
            continue
        if line.startswith("index "):
            continue
        if line.startswith("--- ") or line.startswith("+++ "):
            old = line.startswith("--- ")
            if not old and old_header is None:
                return f"has a `+++` header with no `---` before it at line {number}", False
            side = _header(line[4:], "a/" if old else "b/")
            if side == _DEV_NULL:
                fault = fault or "creates or deletes a file instead of editing one"
            elif side is None:
                label = "a/" if old else "b/"
                fault = fault or f"has a header not labelled `{label}<path>` at line {number}"
            elif side != own:
                return f"reaches {side}, not only {own}", True
            if old:
                old_header, in_file = side or "", False
            else:
                old_header, in_file = None, True
            continue
        if line.startswith("@@"):
            matched = _HUNK.fullmatch(line)
            if matched is None or not in_file:
                return f"has no hunk header it can read at line {number}", False
            old_left = int(matched["old"]) if matched["old"] is not None else 1
            new_left = int(matched["new"]) if matched["new"] is not None else 1
            hunks += 1
            continue
        if line.startswith(_RENAMES):
            side = _unquoted(line.split(" ", 2)[2])
            if side != own:
                return f"reaches {side}, not only {own}", True
            fault = fault or f"renames or copies {own} instead of editing it"
            continue
        if line.startswith(_NOT_TEXT):
            fault = fault or f"changes more than {own}'s text at line {number}"
            continue
        return f"holds a line outside a unified diff at line {number}", False
    if old_left or new_left:
        return "ends inside a hunk", False
    if old_header is not None:
        return "ends after a `---` header", False
    if fault is not None:
        return fault, False
    if not hunks:
        return "holds no hunk", False
    return None


def _header(text: str, prefix: str) -> str | None:
    """The path a `---` or `+++` header names, its `a/` or `b/` label taken off, or
    `/dev/null`; None where it is not so labelled. A tab ends the name, as git and
    diff write one before a time or after a name with a space."""
    name = _unquoted(text.split("\t", 1)[0])
    if name is None:
        return None
    if name == _DEV_NULL:
        return name
    return name[len(prefix) :] if name.startswith(prefix) and len(name) > len(prefix) else None


def _git_pair(text: str) -> tuple[str, str] | None:
    """The two paths of a `diff --git` line, their `a/` and `b/` labels taken off, or
    None where they cannot be told apart."""
    if text.startswith('"'):
        end = _quote_end(text)
        if end is None or text[end + 1 : end + 2] != " ":
            return None
        first, rest = _unquoted(text[: end + 1]), text[end + 2 :]
    else:
        if text.endswith('"'):
            start = text.rfind(' "')
            if start < 0:
                return None
            first, rest = text[:start], text[start + 1 :]
        else:
            # Unquoted, `a/<path> b/<path>` names one path twice.
            half = (len(text) - 1) // 2
            first, rest = text[:half], text[half + 1 :]
            if text[half : half + 1] != " ":
                return None
    second = _unquoted(rest)
    if first is None or second is None:
        return None
    if not first.startswith("a/") or not second.startswith("b/"):
        return None
    return first[2:], second[2:]


_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def _quote_end(text: str) -> int | None:
    """The index of the quote that closes the quoted name `text` opens, or None."""
    index = 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == '"':
            return index
        index += 1
    return None


def _unquoted(text: str) -> str | None:
    """A path as git writes it in a header: as it is, or quoted with C escapes and
    octal bytes, decoded as UTF-8. None where the quoting does not read."""
    if not text.startswith('"'):
        return text
    if _quote_end(text) != len(text) - 1:
        return None
    out = bytearray()
    body, index = text[1:-1], 0
    while index < len(body):
        char = body[index]
        if char != "\\":
            out += char.encode("utf-8")
            index += 1
            continue
        code = body[index + 1 : index + 2]
        if code in _ESCAPES:
            out.append(_ESCAPES[code])
            index += 2
        elif re.fullmatch(r"[0-3][0-7]{2}", body[index + 1 : index + 4]):
            out.append(int(body[index + 1 : index + 4], 8))
            index += 4
        else:
            return None
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return None


# --- settling a run's results ------------------------------------------------------------------


def settle(results: Results, files_root: Path | None, contract: Contract | None = None) -> Results:
    """`results` with each proposed artefact's answer read, and a held or `none`
    artefact whose folder holds an answer given no result (DEC-056 point 3).
    `files_root` is the folder the run's files were copied to, or None where none
    were: then no proposal can be read."""
    contract = contract or _default()
    settled: dict[str, Result] = {}
    for name, result in results.of.items():
        if result.state == PROPOSED:
            if files_root is None:
                settled[name] = replace(result, state=FAILED, why="the run's files were not kept")
                continue
            answer = read_answer(files_root, name, result.answer, contract)
            if isinstance(answer, Unread):
                state = SET_ASIDE if answer.breach else FAILED
                settled[name] = replace(result, state=state, why=answer.why)
            else:
                settled[name] = replace(result, read=answer)
        elif result.state in (HELD, NONE) and files_root is not None:
            parts = _parts(name)
            held = parts is not None and os.path.lexists(
                files_root.joinpath(*parts, contract.answer_file)
            )
            settled[name] = (
                replace(
                    result,
                    state=FAILED,
                    why=f"it is {result.state}, and its folder holds an answer",
                )
                if held
                else result
            )
        else:
            settled[name] = result
    return Results(settled, results.ignored)


# --- what a `none` stands for -------------------------------------------------------------------


def standing(reason: str, failures: int = 1, contract: Contract | None = None) -> str | None:
    """Under which class a `none` of `reason` stands, `artefact` or `setup`, or None
    where it passes and the artefact is dispatched again at the next run.
    `failures` is how many runs in a row, this one included, the artefact counted
    as `failed`: at two, `failed` stands as a setup's fault does (DEC-056 point 3).
    An artefact with no result counts under `failed`."""
    cleared = (contract or _default()).cleared_by(reason)
    if cleared != BY_NEXT_RUN:
        return cleared
    if reason == FAILED_REASON and failures >= FAILURES_TO_STAND:
        return BY_SETUP
    return None
