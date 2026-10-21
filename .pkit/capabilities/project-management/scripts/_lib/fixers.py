"""The fixers point and the grant list (DEC-056 points 1 and 2).

When the default branch leaves an artefact out of date, the agent that fixes
artefacts of its type proposes the answer, and the person decides it. Which
agent fixes which type is `pkit::work-tracking:fixers`, the data point this
capability defines as the provider of the work-tracking role (COR-052,
COR-053): one entry per artefact type, `{id, agent, description}` (its
companion schema, `schemas/fixers.schema.json`). A fixer starts on its own only
where the project granted it, in the grant list `fixers` of this capability's
project configuration, empty by default.

Five parts, so the commands over them stay thin and the drift command can call
the same functions:

- **Reading the point** (`read_point`, `point_of`): through the backbone's read
  command, `pkit connections resolve <point> --json`. Its `outcome` decides,
  never its `why`. `undefined` and `unfilled` mean no fixer is declared.
  `resolved` gives the entries. Any other outcome leaves the point unresolved,
  so no fixer may start (its inert policy is `fail`), and each inert filler is
  named with its fix.
- **The checks on each entry** (`check`), DEC-056 point 1's bad entries. An
  entry that fails one starts no agent, and nobody is asked about it:
  - a capability's entry that comes through a command filler, names a type
    that is not its own, or names an agent the capability does not ship. Each
    is reported, since the project cannot mend it.
  - an entry whose agent is not deployed. That is an error for the project's
    own entry, which the project can mend, and reported for a capability's.
  - an entry whose deployed agent claims paths (`owns`), lists no tools (the
    harness then grants it every tool), or holds a tool that changes existing
    files or starts agents (`CHANGING_TOOLS`, `STARTING_TOOLS`). A tool that
    writes new files stays, for its workspace.
- **The grant list** (`answers_of`, `record`, `answers_at`, `grant_change`):
  each agent the person was asked about, the types it was granted and the types
  it was refused. A type has at most one answer for an agent. `record` writes
  answers into the project configuration as text, every byte outside the
  `fixers` block kept, and reads the file back before it writes. `answers_at`
  reads the list at a commit, from git objects, and `grant_change` is each
  grant and refusal a change adds or removes, which the landing command lists
  before it stops ready, asks or merges.
- **The question** (`questions`, `question_text`, `grant_line`, `ask`): one
  question for each agent, about the types of its entries that pass the checks
  and have no answer. Its words are built from the declaration: the
  capability's name and the descriptions of the agent's entries. `ask` asks
  each at a terminal and hands each answer to its caller, which records it.
  With nobody to ask, `grant_line` is the one command line that grants the
  fixer the types the question named.
- **What may start** (`startable`, `stale_grants`, `stale_refusals`): the
  entries that pass the checks and are granted, and each grant or refusal that
  no entry names. Such a grant starts nothing, and validation warns of it with
  the command that revokes it. Such a refusal asks nothing and starts nothing,
  and validation reports it with the words to remove it by hand.

Nothing here decides when a grant counts. The drift command reads the grant
list at the default branch's commit (DEC-056 point 3), so a grant counts once
its change merges.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _lib import agents as agent_files

try:  # ruamel is declared by every pm script's PEP 723 header.
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # pragma: no cover — ruamel is in the kit's pyproject
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]

POINT = "pkit::work-tracking:fixers"

#: The grant list's key in this capability's project configuration, and the two
#: answers it records for a type.
CONFIG_KEY = "fixers"
CONFIG_RELATIVE = Path("project") / "config.yaml"
GRANTED = "granted"
REFUSED = "refused"
ANSWERS = (GRANTED, REFUSED)

#: The commands a person runs, as a printed line names them.
COMMAND = "pkit pm"
LIST_VERB = "list-fixers"
GRANT_VERB = "grant-fixer"
REVOKE_VERB = "revoke-fixer"
ASK_VERB = "ask-fixers"

#: The backbone's read commands, how long each may take, and the versions of
#: their documents this reading understands. A document without the key comes
#: from a backbone that predates it: version 1.
RESOLVE_ARGV = ("pkit", "connections", "resolve", POINT, "--json")
ARTEFACTS_ARGV = ("pkit", "friction", "artefacts", "--json")
TIMEOUT = 120
DOCUMENT_VERSION = 1
ARTEFACTS_VERSION = 1

#: The outcomes that declare no fixer, and the one that gives the entries.
OFF = frozenset({"undefined", "unfilled"})
RESOLVED = "resolved"

#: An entry's origin, and a filler's source, when it is the project's own filler
#: file; a filler's state when it was meant to answer and could not; how a
#: command filler says what it supplies (`command '<reference>'`).
PROJECT_FILLER = "project filler"
CONTRIBUTION = "contribution"
INERT = "inert"
COMMAND_SUPPLIES = "command "

#: The tools a fixer may not hold, in the harness's own names: those of the one
#: adapter that deploys agents (`_lib/agents`). A fixer only proposes, so it
#: changes no existing file and starts no agent. `Write`, which writes new
#: files, stays for its workspace (DEC-056 point 1).
CHANGING_TOOLS = frozenset({"Edit", "MultiEdit", "NotebookEdit"})
STARTING_TOOLS = frozenset({"Agent", "Task"})

#: The severities a finding takes (COR-055 point 4). Only `error` fails.
ERROR = "error"
WARNING = "warning"
REPORT = "report"

#: An agent's name, and an artefact type's (COR-056 point 1), as the schemas
#: write them: `fixers.schema.json` and the grant list in `config.schema.json`.
#: A test holds the schemas' patterns to these.
AGENT_NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
TYPE_NAME = re.compile(r"(?:(?:[a-z]|[a-z][a-z0-9-]*[a-z0-9]):)?[a-z][a-z0-9]*(?:-[a-z0-9]+)*")

#: A byte-order mark: kept where a file opens with one.
BOM = "\ufeff"

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Unreadable(Exception):
    """A backbone read command gave no document to read."""


class Malformed(Exception):
    """The project configuration, or its grant list, cannot be read as one."""


class Refused(Exception):
    """An answer cannot be written: nothing was written."""


# --- reading the point ---------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """One entry of the point: the agent that fixes artefacts of one type."""

    type: str
    agent: str
    description: str
    origin: str  # the contributing capability, or `PROJECT_FILLER`
    supplies: str = ""  # how its filler supplies it: `value`, `command '<ref>'`, `file`
    where: str = ""  # the file that declares it, for a finding's location

    @property
    def project(self) -> bool:
        return self.origin == PROJECT_FILLER

    @property
    def declared_by(self) -> str:
        """Who declares the entry, as a sentence names it."""
        return "the project's filler file" if self.project else self.origin


@dataclass(frozen=True)
class Point:
    """The point as this capability reads it. Unresolved, it gives no entry, and
    `why` and `inert` say why."""

    resolved: bool
    why: str = ""
    entries: tuple[Entry, ...] = ()
    inert: tuple[str, ...] = ()  # each inert filler and its fix, for people

    def types_of(self, agent: str) -> tuple[str, ...]:
        """Every type the point gives `agent`, in the point's order."""
        return tuple(e.type for e in self.entries if e.agent == agent)

    @property
    def agents(self) -> tuple[str, ...]:
        """Every agent the point names, in the point's order, each once."""
        return tuple(dict.fromkeys(e.agent for e in self.entries))


def read_point(run: Runner = subprocess.run) -> Point:
    """The point through `pkit connections resolve --json`. The command exits 1 on
    an unresolved point and still prints its document, so the document decides,
    never the exit code. No document at all raises Unreadable."""
    return point_of(_document(RESOLVE_ARGV, run))


def point_of(document: Mapping[str, Any]) -> Point:
    """The point a `pkit connections resolve --json` document states."""
    version = document.get("schema_version", DOCUMENT_VERSION)
    if version != DOCUMENT_VERSION:
        return Point(
            False,
            why=f"the backbone answered a document at version {version!r}; this reading "
            f"understands {DOCUMENT_VERSION}",
        )
    outcome = document.get("outcome")
    if document.get("defined") is False or outcome in OFF:
        return Point(True, why=str(document.get("why") or "nothing declares a fixer"))
    fillers = [f for f in document.get("fillers") or [] if isinstance(f, Mapping)]
    if outcome != RESOLVED:
        why = str(document.get("why") or "").strip() or f"it ended as {outcome!r}"
        inert = tuple(_inert(f) for f in fillers if f.get("state") == INERT)
        return Point(False, why=why, inert=inert)
    supplies = {
        str(f.get("name")): str(f.get("supplies") or "")
        for f in fillers
        if f.get("source") == CONTRIBUTION
    }
    filler_file = next(
        (str(f.get("name")) for f in fillers if f.get("source") == PROJECT_FILLER), ""
    )
    entries: list[Entry] = []
    for item in document.get("entries") or []:
        value = item.get("value") if isinstance(item, Mapping) else None
        if not isinstance(value, Mapping):
            continue
        origin = str(item.get("origin") or "")
        project = origin == PROJECT_FILLER
        entries.append(
            Entry(
                type=str(value.get("id") or ""),
                agent=str(value.get("agent") or ""),
                description=" ".join(str(value.get("description") or "").split()),
                origin=origin,
                supplies="file" if project else supplies.get(origin, ""),
                where=filler_file if project else f".pkit/capabilities/{origin}/package.yaml",
            )
        )
    return Point(True, why="" if entries else "the point holds no entry", entries=tuple(entries))


def _inert(filler: Mapping[str, Any]) -> str:
    """An inert filler as a person reads it: who, how, why, and the fix."""
    name = str(filler.get("name") or "a filler")
    reason = str(filler.get("reason") or "").strip()
    how = str(filler.get("supplies") or "").strip()
    fix = (
        f"mend {name}"
        if filler.get("source") == PROJECT_FILLER
        else f"update {name}, pin it, or uninstall it"
    )
    return f"{name}{f' ({how})' if how else ''}: {reason or 'no answer'} — fix: {fix}"


def read_types(run: Runner = subprocess.run) -> dict[str, str]:
    """Each declared type and the component that declares it: the type
    registries the backbone lists beside its one answer for each artefact's type
    (COR-056 point 6), read through `pkit friction artefacts --json`. Raises
    Unreadable when it gives no such document."""
    document = _document(ARTEFACTS_ARGV, run)
    version = document.get("schema_version", ARTEFACTS_VERSION)
    if version != ARTEFACTS_VERSION:
        raise Unreadable(
            f"`{' '.join(ARTEFACTS_ARGV)}` answered a document at version {version!r}; "
            f"this reading understands {ARTEFACTS_VERSION}"
        )
    types = document.get("types")
    if not isinstance(types, Mapping):
        raise Unreadable(
            f"`{' '.join(ARTEFACTS_ARGV)}` lists no type registries (it predates them; "
            "upgrade the backbone)"
        )
    return {
        str(name): str(declared.get("component") or "")
        for name, declared in types.items()
        if isinstance(declared, Mapping)
    }


def _document(argv: Sequence[str], run: Runner) -> Mapping[str, Any]:
    """The JSON document a backbone read command prints, whatever its exit code."""
    shown = f"`{' '.join(argv)}`"
    try:
        proc = run(list(argv), capture_output=True, text=True, check=False, timeout=TIMEOUT)
    except FileNotFoundError as exc:
        raise Unreadable("`pkit` is not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise Unreadable(f"{shown} did not answer within {TIMEOUT}s") from exc
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        said = (proc.stderr or "").strip().splitlines()
        raise Unreadable(
            f"{shown} exited {proc.returncode} without its document"
            + (f": {said[-1]}" if said else "")
        )
    return document


# --- the checks on each entry ----------------------------------------------------------


@dataclass(frozen=True)
class Problem:
    """Why an entry starts no agent, and how serious that is for validation."""

    severity: str
    text: str


@dataclass(frozen=True)
class Checked:
    """An entry and what its checks found. With no problem, its agent may start
    once the project grants it."""

    entry: Entry
    problems: tuple[Problem, ...] = ()

    @property
    def startable(self) -> bool:
        return not self.problems


TypesReader = Callable[[], Mapping[str, str]]


def check(point: Point, repo_root: Path, types: TypesReader = read_types) -> list[Checked]:
    """Each entry of `point` with what its checks found (DEC-056 point 1). The type
    registries are read only when a capability's entry needs them, and once."""
    registry: list[Mapping[str, str] | str] = []

    def registered() -> Mapping[str, str] | str:
        if not registry:
            try:
                registry.append(types())
            except Unreadable as exc:
                registry.append(str(exc))
        return registry[0]

    return [Checked(e, tuple(_problems(e, repo_root, registered))) for e in point.entries]


def _problems(
    entry: Entry, repo_root: Path, registered: Callable[[], Mapping[str, str] | str]
) -> list[Problem]:
    found: list[Problem] = []
    if not entry.project:
        found += _capability_problems(entry, repo_root, registered)
    # The project can mend its own entry, so what it gets wrong asks for attention;
    # a capability's it cannot, so that is reported (COR-055 point 1).
    minor = REPORT if not entry.project else WARNING
    definition = agent_files.deployed_definition(repo_root, entry.agent)
    if definition is None:
        found.append(
            Problem(
                ERROR if entry.project else REPORT,
                f"agent {entry.agent} is not deployed (`pkit sync` deploys the agents of the "
                "installed components)",
            )
        )
        return found
    if definition.problem:
        found.append(Problem(minor, f"agent {entry.agent} cannot be read: {definition.problem}"))
        return found
    if definition.owns:
        found.append(
            Problem(
                minor,
                f"agent {entry.agent} claims paths ({', '.join(definition.owns)}), and a fixer "
                "only proposes",
            )
        )
    if definition.tools is None:
        found.append(
            Problem(
                minor,
                f"agent {entry.agent} lists no tools, so the harness grants it every tool, "
                "those that change existing files and start agents among them, and a fixer "
                "only proposes",
            )
        )
        return found
    for tools, what in (
        (CHANGING_TOOLS, "changes existing files"),
        (STARTING_TOOLS, "starts agents"),
    ):
        held = sorted(set(definition.tool_names) & tools)
        if held:
            found.append(
                Problem(
                    minor,
                    f"agent {entry.agent} holds {', '.join(held)}, a tool that {what}, and a "
                    "fixer only proposes",
                )
            )
    return found


def _capability_problems(
    entry: Entry, repo_root: Path, registered: Callable[[], Mapping[str, str] | str]
) -> list[Problem]:
    found: list[Problem] = []
    capability = entry.origin
    if entry.supplies.startswith(COMMAND_SUPPLIES):
        found.append(
            Problem(
                REPORT,
                f"{capability} gives it through a command filler ({entry.supplies}), and a "
                "capability gives its fixers as a static value",
            )
        )
    owner, colon, _name = entry.type.partition(":")
    if not colon or owner != capability:
        found.append(Problem(REPORT, f"{entry.type} is not a type of {capability}'s own"))
    else:
        declared = registered()
        if isinstance(declared, str):
            found.append(Problem(WARNING, f"its type could not be checked: {declared}"))
        elif declared.get(entry.type) != capability:
            found.append(
                Problem(REPORT, f"{capability} declares no type {entry.type} in its type registry")
            )
    if not agent_files.agent_is_shipped_by(repo_root, capability, entry.agent):
        found.append(Problem(REPORT, f"{capability} ships no agent {entry.agent}"))
    return found


# --- the grant list ----------------------------------------------------------------------


@dataclass(frozen=True)
class Answers:
    """The grant list: for each agent the person was asked about, each type's
    answer, `granted` or `refused`."""

    agents: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    def of(self, agent: str, artefact_type: str) -> str | None:
        return self.agents.get(agent, {}).get(artefact_type)

    def granted(self, agent: str) -> tuple[str, ...]:
        return tuple(t for t, a in self.agents.get(agent, {}).items() if a == GRANTED)


def load_config(path: Path) -> Mapping[str, Any]:
    """This capability's project configuration, strictly: a file that does not
    parse, or is not a mapping, raises Malformed. An absent file is empty."""
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Malformed(f"{path.name} cannot be read: {exc}") from exc
    return config_of(text, path.name)


def config_of(text: str, name: str) -> Mapping[str, Any]:
    """The configuration `text` holds, read as `load_config` reads a file; `name`
    is the file as a message names it."""
    if YAML is None:  # pragma: no cover — ruamel is in the kit's pyproject
        raise Malformed("ruamel.yaml is not installed")
    try:
        data = YAML(typ="safe").load(text)
    except YAMLError as exc:
        raise Malformed(f"{name} cannot be read: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise Malformed(f"{name} is not a mapping")
    return data


def missing_config(path: Path) -> str | None:
    """Why no answer can be written into the configuration at `path`, or None: an
    absent file is the project's to author first. A dry run says it as the write
    would."""
    if path.is_file():
        return None
    return (
        f"{path} does not exist: author project-management's configuration first "
        '(its README, "Adopter setup")'
    )


def answers_at(
    commit: str, path: str, run: Runner = subprocess.run, cwd: Path | None = None
) -> Answers:
    """The grant list as the configuration at `path`, a path from the repository's
    root, holds it at `commit`, read from git objects. A commit without the file
    has an empty list. Raises Unreadable where git cannot read the commit, and
    Malformed where the file is no configuration or its grant list is off its
    shape."""
    listed = _git_out(run, cwd, "ls-tree", "-z", commit, "--", path)
    if listed is None:
        raise Unreadable(f"the files of {commit[:7]} could not be read")
    record_ = listed.decode("utf-8", "replace").split("\0", 1)[0]
    if not record_:
        return Answers()
    meta, _tab, _name = record_.partition("\t")
    mode, kind, oid = [*meta.split(" "), "", "", ""][:3]
    if kind != "blob" or mode == "120000":
        raise Malformed(f"{path} at {commit[:7]} is not a file")
    blob = _git_out(run, cwd, "cat-file", "blob", oid)
    if blob is None:
        raise Unreadable(f"{path} at {commit[:7]} could not be read")
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Malformed(f"{path} at {commit[:7]} is not UTF-8") from exc
    return answers_of(config_of(text, f"{path} at {commit[:7]}"))


def _git_out(run: Runner, cwd: Path | None, *argv: str) -> bytes | None:
    """`git <argv>`'s output as bytes, or None where it failed or could not run."""
    try:
        proc = run(["git", *argv], cwd=cwd, capture_output=True, check=False, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout if isinstance(proc.stdout, bytes) else str(proc.stdout).encode("utf-8")


@dataclass(frozen=True, order=True)
class GrantChange:
    """One grant or refusal a change adds to the grant list or removes from it."""

    agent: str
    type: str
    added: bool
    answer: str  # `granted` or `refused`

    def said(self) -> str:
        """The change as a line says it to the person who authorises the merge."""
        if self.answer == GRANTED:
            if self.added:
                return f"Fixer grant added: {self.agent} may start on its own on {self.type}"
            return f"Fixer grant removed: {self.agent} no longer starts on its own on {self.type}"
        if self.added:
            return f"Fixer refusal added: {self.agent} is refused {self.type}"
        return f"Fixer refusal removed: {self.agent} is no longer refused {self.type}"


def grant_change(before: Answers, after: Answers) -> tuple[GrantChange, ...]:
    """Each grant and refusal `after` adds to `before` or removes from it, by agent
    and type, a removal before an addition. A type moved from refused to granted
    is a refusal removed and a grant added."""
    out: list[GrantChange] = []
    for agent in set(before.agents) | set(after.agents):
        types = set(before.agents.get(agent, {})) | set(after.agents.get(agent, {}))
        for artefact_type in types:
            was, now = before.of(agent, artefact_type), after.of(agent, artefact_type)
            if was == now:
                continue
            if was is not None:
                out.append(GrantChange(agent, artefact_type, False, was))
            if now is not None:
                out.append(GrantChange(agent, artefact_type, True, now))
    return tuple(sorted(out))


def answers_of(config: Mapping[str, Any]) -> Answers:
    """The grant list in `config`. Absent or empty, nobody was asked. A list in
    another shape raises Malformed: the readers never guess at a grant."""
    block = config.get(CONFIG_KEY)
    if block is None:
        return Answers()
    shape = (
        f"`{CONFIG_KEY}` maps each agent to its `{GRANTED}` and `{REFUSED}` lists of types "
        "(DEC-056 point 2)"
    )
    if not isinstance(block, Mapping):
        raise Malformed(shape)
    agents: dict[str, dict[str, str]] = {}
    for agent, lists in block.items():
        if not isinstance(agent, str) or not AGENT_NAME.fullmatch(agent):
            raise Malformed(f"{shape}; {agent!r} is not an agent's name")
        if lists is None:
            lists = {}
        if not isinstance(lists, Mapping) or set(lists) - set(ANSWERS):
            raise Malformed(f"{shape}; `{CONFIG_KEY}.{agent}` is not")
        answered: dict[str, str] = {}
        for answer in ANSWERS:
            types = lists.get(answer)
            if types is None:
                continue
            if not isinstance(types, list) or not all(isinstance(t, str) for t in types):
                raise Malformed(f"`{CONFIG_KEY}.{agent}.{answer}` is not a list of types")
            for artefact_type in types:
                if answered.get(artefact_type, answer) != answer:
                    raise Malformed(
                        f"`{CONFIG_KEY}.{agent}` both grants and refuses {artefact_type}"
                    )
                answered[artefact_type] = answer
        agents[agent] = answered
    return Answers(agents)


def record(path: Path, agent: str, types: Iterable[str], answer: str) -> bool:
    """Write `answer` for each of `types` of `agent` into the grant list of the
    configuration at `path`, and return whether the file changed. A type's other
    answer is taken away, so a type keeps one answer.

    The `fixers` block is laid out again as text, every other byte kept, and the
    file must read back as it was with only the grant list changed. Otherwise
    Refused is raised and nothing is written. An absent file is refused too: the
    configuration is the project's to author first."""
    if answer not in ANSWERS:
        raise ValueError(f"an answer is {GRANTED!r} or {REFUSED!r}, not {answer!r}")
    missing = missing_config(path)
    if missing is not None:
        raise Refused(missing)
    try:
        config = load_config(path)
        before = answers_of(config)
    except Malformed as exc:
        raise Refused(f"{path}: {exc}; fix it first") from exc
    after = {agent_: dict(answered) for agent_, answered in before.agents.items()}
    after.setdefault(agent, {}).update(dict.fromkeys(types, answer))
    if after == before.agents:
        return False
    text = path.read_bytes().decode("utf-8")
    bom = BOM if text.startswith(BOM) else ""
    text = text[len(bom) :]
    crlf = "\r\n" in text
    if crlf and text.count("\r\n") != text.count("\n"):
        raise Refused(f"{path} mixes line endings; give it one, then answer again")
    lf = text.replace("\r\n", "\n")
    updated = _spliced(lf, _block(after))
    try:
        reads = YAML(typ="safe").load(updated) if YAML is not None else None
    except YAMLError:
        reads = None
    wanted = {**dict(config), CONFIG_KEY: _value(after)}
    if reads != wanted:
        raise Refused(
            f"{path} would not read back unchanged around the `{CONFIG_KEY}` block, so nothing "
            f"was written: write the answer under `{CONFIG_KEY}` by hand, then check it with "
            f"`{COMMAND} {LIST_VERB}`"
        )
    path.write_bytes((bom + (updated.replace("\n", "\r\n") if crlf else updated)).encode("utf-8"))
    return True


def _value(agents: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    """The grant list as it reads back: each agent's non-empty lists, sorted."""
    out: dict[str, Any] = {}
    for agent, answered in agents.items():
        lists = {
            answer: sorted(t for t, a in answered.items() if a == answer) for answer in ANSWERS
        }
        out[agent] = {answer: types for answer, types in lists.items() if types}
    return out


def _block(agents: Mapping[str, Mapping[str, str]]) -> list[str]:
    """The `fixers` block's lines, laid out as the project's YAML is: mappings by
    two spaces, each list item under its key by two more."""
    value = _value(agents)
    if not value:
        return [f"{CONFIG_KEY}: {{}}"]
    lines = [f"{CONFIG_KEY}:"]
    for agent, lists in value.items():
        lines.append(f"  {agent}:" + ("" if lists else " {}"))
        for answer, types in lists.items():
            lines.append(f"    {answer}:")
            lines += [f"      - {t}" for t in types]
    return lines


#: The top-level key's line: `fixers:`, then a value on the line or a comment.
_KEY_LINE = re.compile(rf"^{CONFIG_KEY}:(?P<rest>.*)$")
_LEAD = (
    "# Fixers: each agent you were asked about, and the types you granted or refused it",
    "# (project-management DEC-056 point 2). Written by `pkit pm ask-fixers`,",
    "# `pkit pm grant-fixer` and `pkit pm revoke-fixer`.",
)


def _spliced(text: str, block: Sequence[str]) -> str:
    """`text` with its top-level `fixers` block replaced by `block`, from the key's
    line through the last indented line under it, or with `block` added at the end
    under a comment. A comment on the key's own line stays."""
    lines = text.split("\n")
    found = next(
        ((i, m) for i, line in enumerate(lines) if (m := _KEY_LINE.match(line)) is not None),
        None,
    )
    if found is None:
        lead = "" if not text or text.endswith("\n") else "\n"
        gap = "\n" if text.strip() else ""
        return text + lead + gap + "\n".join([*_LEAD, *block]) + "\n"
    start, match = found
    rest = match["rest"].strip()
    head = block[0] + (f"  {rest}" if rest.startswith("#") else "")
    last = start
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            continue
        if lines[i][:1] not in (" ", "\t"):
            break
        last = i
    return "\n".join([*lines[:start], head, *block[1:], *lines[last + 1 :]])


# --- the question ------------------------------------------------------------------------


@dataclass(frozen=True)
class Question:
    """The question about one agent: its entries whose types have no answer, and
    every type the point gives it."""

    agent: str
    entries: tuple[Entry, ...]
    all_types: tuple[str, ...]

    @property
    def types(self) -> tuple[str, ...]:
        return tuple(e.type for e in self.entries)


def questions(point: Point, checked: Sequence[Checked], answers: Answers) -> list[Question]:
    """One question for each agent, about the types of its entries that pass the
    checks and have no answer (DEC-056 point 2), in the point's order."""
    pending: dict[str, list[Entry]] = {}
    for item in checked:
        entry = item.entry
        if item.startable and answers.of(entry.agent, entry.type) is None:
            pending.setdefault(entry.agent, []).append(entry)
    return [Question(a, tuple(es), point.types_of(a)) for a, es in pending.items()]


def question_text(question: Question) -> str:
    """The question's words: built from the capability's name and the descriptions
    of the agent's entries, saying what the agent does on its own after each merge,
    and that nothing is applied until the person approves it."""
    kept = _joined(list(dict.fromkeys(e.description for e in question.entries)))
    origins = {e.origin for e in question.entries}
    if len(origins) == 1 and PROJECT_FILLER not in origins:
        subject, doer = next(iter(origins)), f"its agent {question.agent}"
    else:
        subject, doer = f"The agent {question.agent}", "it"
    return (
        f"{subject} can keep {kept} true on its own. After each merge, {doer} proposes a fix "
        "for each one that went out of date, and nothing is applied until you approve it. "
        "Turn this on?"
    )


def _joined(parts: Sequence[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return f"{', '.join(parts[:-1])} and {parts[-1]}"


def grant_line(question: Question) -> str:
    """The one command line that grants the fixer, naming each type the question
    named. A type the point gives the agent later is then a question of its own,
    never granted by a line printed before it existed (DEC-056 point 2)."""
    return _line(GRANT_VERB, question.agent, question.types)


def revoke_line(agent: str, types: Sequence[str] = ()) -> str:
    """The command line that revokes `agent`: every type it is granted or given,
    or only `types`."""
    return _line(REVOKE_VERB, agent, types)


def _line(verb: str, agent: str, types: Sequence[str]) -> str:
    return f"{COMMAND} {verb} {agent}" + "".join(f" --type {t}" for t in types)


def ask(
    pending: Sequence[Question],
    *,
    read: Callable[[], str],
    write: Callable[[str], None],
    answer: Callable[[Question, str], None],
) -> list[Question]:
    """Ask each question, and hand each answer to `answer`: `granted` for yes,
    the default, and `refused` for no. Returns the questions left unasked when the
    input ends (`read` raises EOFError): nobody answered them."""
    for index, question in enumerate(pending):
        while True:
            write(f"{question_text(question)} [Y/n] ")
            try:
                reply = read().strip().lower()
            except EOFError:
                write("\n")
                return list(pending[index:])
            if reply in ("", "y", "yes"):
                answer(question, GRANTED)
                break
            if reply in ("n", "no"):
                answer(question, REFUSED)
                break
            write("Answer y or n.\n")
    return []


# --- what may start ----------------------------------------------------------------------


def startable(checked: Sequence[Checked], answers: Answers) -> list[Entry]:
    """The entries whose agent may start: they pass the checks, and the grant
    list grants their agent their type."""
    return [
        c.entry
        for c in checked
        if c.startable and answers.of(c.entry.agent, c.entry.type) == GRANTED
    ]


def stale_grants(point: Point, answers: Answers) -> list[tuple[str, str]]:
    """`(agent, type)` for each grant no entry of the point names. It starts
    nothing (DEC-056 point 2)."""
    return [
        (agent, artefact_type)
        for agent in answers.agents
        for artefact_type in answers.granted(agent)
        if artefact_type not in point.types_of(agent)
    ]


def stale_refusals(point: Point, answers: Answers) -> list[tuple[str, str]]:
    """`(agent, type)` for each refusal no entry of the point names. It asks nothing
    and starts nothing, and no command removes it: a revoke only records one."""
    return [
        (agent, artefact_type)
        for agent, answered in answers.agents.items()
        for artefact_type, answer in answered.items()
        if answer == REFUSED and artefact_type not in point.types_of(agent)
    ]


# --- validation ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A finding in the form a validator answers with (COR-055)."""

    severity: str
    location: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "location": self.location, "message": self.message}


def findings(
    point: Point,
    checked: Sequence[Checked],
    answers: Answers,
    config_location: str,
) -> list[Finding]:
    """What validation says of the point's entries and of the grant list."""
    out = [
        Finding(
            problem.severity,
            item.entry.where or POINT,
            f"the fixer of {item.entry.type} (agent {item.entry.agent}, from "
            f"{item.entry.declared_by}) starts no agent: {problem.text}.",
        )
        for item in checked
        for problem in item.problems
    ]
    out += [
        Finding(
            WARNING,
            f"{config_location}:/{CONFIG_KEY}/{agent}/{GRANTED}",
            f"the grant of {artefact_type} to {agent} names what no entry of {POINT} gives "
            f"it, so it starts nothing. Revoke it: `{revoke_line(agent, [artefact_type])}`.",
        )
        for agent, artefact_type in stale_grants(point, answers)
    ]
    out += [
        Finding(
            REPORT,
            f"{config_location}:/{CONFIG_KEY}/{agent}/{REFUSED}",
            f"the refusal of {artefact_type} to {agent} names what no entry of {POINT} gives "
            f"it, so it asks nothing and starts nothing. To remove it, delete {artefact_type} "
            f"from `{CONFIG_KEY}.{agent}.{REFUSED}` in {config_location} by hand.",
        )
        for agent, artefact_type in stale_refusals(point, answers)
    ]
    return out
