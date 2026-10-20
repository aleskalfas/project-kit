#!/usr/bin/env python3
"""The Claude Code adapter's agent runner (ADR-066 points 1 to 4, 6, 8 to 10 and 12).

The backbone's run command, `pkit agents run`, starts this script as the
command the adapter registers under `run-agent`. It never runs on its own
behalf: a command that starts an agent asks the backbone, and the backbone
starts this runner, which starts Claude Code. The tie to `claude` lives here,
and nowhere in a capability.

**The request**, one JSON document on standard input: `schema_version` (1),
`agent`, `brief`, `limit_seconds`, `effort` (a level or null), and either
`folder` (the unconfined form, the review command's runs, ADR-066 point 10) or
`confined` (the confined form, the drift command's runs). A request that
carries any other key is refused, never run without it.

**The marker** (ADR-066 point 8). The runner refuses whenever `PKIT_AGENT_RUN`
is in its own environment, empty included, and sets `PKIT_AGENT_RUN=1` in the
harness's environment, so every process of a run inherits it.

**The unconfined form.** The runner refuses when `claude` is not on the path,
or when the agent is not deployed. It starts `claude -p --agent <agent>`, with
`--effort <level>` where one is set, in the request's folder. The run takes the
person's and the project's settings there, as a session started in that folder
would. The harness gets the runner's environment, less the backbone's
variables for its run of this runner (`RUN_VARIABLES`).

**The confined form** (ADR-066 points 2 to 6 and 9). Before the harness starts,
the runner refuses, naming the cause, when the harness's version lies outside
`TESTED_RANGE` (empty until the probe passes, so every confined run is refused
today), when the platform has no sandbox the harness can use, when this runner
is not the working copy's own, when the agent's definition fails its check, or
when the run's settings fail the part of the harness's settings schema the
runner writes. It then starts the harness in the run's workspace with only the
run's settings, the checked definition under a name unique to the run, and a
closed set of flags. It reads the harness's stream: a start report that does
not match the run's settings, or a hook, ends the run at once. The adapter's
README, "The agent runner", states each part.

**Both forms.** The brief goes on standard input, so no word of it is read as
a flag. The harness starts in a session of its own. At the limit the runner
ends the harness and every process still descended from it (`end_harness`).
Asked to stop (`SIGTERM`, `SIGHUP`, `SIGINT`), it ends the harness the same
way, then exits with no answer.

**The answer**, one JSON document on standard output, exit 0: `schema_version`
(1), `ending` (`finished`, `not-started`, `timed-out` or `refused`),
`exit_code` (the harness's when it finished, else null), `output`,
`diagnostics` (the harness's standard error), `reason`. For the unconfined form
`output` is the harness's standard output. For a confined request the answer
also carries `refused_calls` and `start_report`, and `output` is the agent's
final message, never a tool's result.

Runs under the system `python3`, standard library only, as the permission hook
does: no `uv`, nothing to provision.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

REQUEST_VERSION = 1
ANSWER_VERSION = 1

#: The harness's command line.
HARNESS = "claude"

#: The marker of a run (ADR-066 point 8). The runner refuses when it is in its
#: own environment, and sets it in the harness's. Nothing else sets or unsets it.
MARKER = "PKIT_AGENT_RUN"

#: The keys of an unconfined request. Any other key is refused.
REQUEST_KEYS = frozenset({"schema_version", "agent", "brief", "folder", "limit_seconds", "effort"})

#: The keys of a confined request: the unconfined form's, without `folder`,
#: with `confined`.
CONFINED_REQUEST_KEYS = (REQUEST_KEYS - {"folder"}) | {"confined"}

#: The keys of a request's `confined` object, and the ones that name a folder.
CONFINED_KEYS = frozenset(
    {"working_copy", "workspace", "temp", "pkit_folder", "project_root", "rules", "excluded"}
)
CONFINED_FOLDERS = ("working_copy", "workspace", "temp", "pkit_folder", "project_root")

#: The closed set of flags of the unconfined form (ADR-066 point 4), each with
#: whether it takes a value. No member approves a call by itself.
FLAGS = {"-p": False, "--agent": True, "--effort": True}

#: A confined run's tools (ADR-066 point 4): reading, searching, writing new
#: files and the shell.
RUN_TOOLS = ("Read", "Glob", "Grep", "Write", "Bash")

#: The one mode a confined run starts in: it refuses every call that would ask.
RUN_MODE = "dontAsk"

#: The closed set of flags of the confined form (ADR-066 point 4), each with
#: whether it takes a value. None of them approves a call, or loads
#: configuration other than the run's own. `--setting-sources ""` leaves out
#: every settings file; `--restricted` would also confine the file tools to the
#: workspace, and with no `--add-dir` the run could not read the clone. Which
#: of the two holds is a probe fact (ADR-066 point 3).
CONFINED_FLAGS = {
    "-p": False,
    "--setting-sources": True,
    "--settings": True,
    "--agents": True,
    "--agent": True,
    "--permission-mode": True,
    "--permission-prompts": True,
    "--tools": True,
    "--strict-mcp-config": False,
    "--disable-slash-commands": False,
    "--no-session-persistence": False,
    "--output-format": True,
    "--verbose": False,
    "--include-hook-events": False,
    "--effort": True,
}

#: The value each of those flags always takes in a confined run.
CONFINED_VALUES = {
    "--setting-sources": "",
    "--permission-mode": RUN_MODE,
    "--permission-prompts": "none",
    "--tools": ",".join(RUN_TOOLS),
    "--output-format": "stream-json",
}

#: The harness's effort levels, the methodology's vocabulary.
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

#: The longest limit a run takes, as the backbone bounds it: a week.
MAX_LIMIT_SECONDS = 7 * 24 * 60 * 60

#: An agent's name, as the backbone admits it: no flag, no path.
AGENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

#: The backbone's own variables for its run of this runner. The harness's run
#: is not part of that run, so they are not passed on.
RUN_VARIABLES = ("PKIT_COMMAND_DEADLINE", "PKIT_COMMAND_STRAYS", "PKIT_RUN_CACHE")

#: Where the process table is read: the system's own `ps` only, so no `ps` on
#: the run's PATH stands in for it.
PS_CANDIDATES = ("/bin/ps", "/usr/bin/ps")

#: How many times the runner walks the process table for descendants it has not
#: stopped yet. A stopped process starts nothing, so a few walks find them all.
END_ROUNDS = 10

FINISHED = "finished"
NOT_STARTED = "not-started"
TIMED_OUT = "timed-out"
REFUSED = "refused"

# --- the confined form's facts about the harness -----------------------------------
#
# Each value below rests on Claude Code's documentation and its 2.1.302 release
# until the probe (`probe-confined-run.py`, ADR-066 point 12) confirms it.

#: The harness versions the confined form was tested on: the lowest and the
#: highest, both included (ADR-066 points 2 and 12). Empty until the adapter's
#: author runs the probe on a harness and it passes. Only that author widens it
#: (COR-047 point 2).
TESTED_RANGE: tuple[str, ...] = ()

#: How the harness prints its version: the first `X.Y.Z` of `claude --version`.
VERSION = re.compile(r"(\d+)\.(\d+)\.(\d+)")

#: What the harness's sandbox needs (ADR-066 point 6). On macOS it is the
#: system's own `sandbox-exec`. On Linux it is bubblewrap and socat, found on
#: the run's PATH. Any other platform has no sandbox the harness can use.
MACOS_SANDBOX = "/usr/bin/sandbox-exec"
LINUX_SANDBOX = ("bwrap", "socat")

#: The harness's sign-in variables, as its documentation names them: its own,
#: then those of Amazon Bedrock, Google Vertex AI and Microsoft Foundry.
#: The harness's switch that strips the sign-in variables from every process it
#: starts, the run's shell included (ADR-066 point 4). A probe fact (point 12).
CREDENTIAL_SCRUB = "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"

SIGN_IN_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "AWS_REGION",
    "AWS_PROFILE",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_BEARER_TOKEN_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLOUD_ML_REGION",
    "ANTHROPIC_VERTEX_PROJECT_ID",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_FOUNDRY_API_KEY",
    "ANTHROPIC_FOUNDRY_RESOURCE",
)

#: The person's variables a confined run keeps, besides the sign-in ones and
#: the locale's `LC_*`: who the person is, and how the harness reaches its
#: model through a proxy or a gateway. No variable that changes the harness's
#: permissions, its sandbox or its configuration folder is among them, and no
#: `UV_*` (ADR-066 point 4).
KEPT_VARIABLES = (
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "LANG",
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "NO_PROXY",
    "no_proxy",
    "ANTHROPIC_BASE_URL",
)

#: The variables that place the temp folders in the run's temp folder: the
#: system's, and the harness's own, which places the shell's. That the shell's
#: temp folder lies there is a probe fact (ADR-066 points 6 and 12).
TEMP_VARIABLES = ("TMPDIR", "CLAUDE_CODE_TMPDIR")

#: The system's own folders, last on a confined run's PATH.
SYSTEM_PATH = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")

#: Where the backbone runs this runner from: the working copy's adapter folder
#: (ADR-066 point 3). The deploy's resolver lies beside it.
ADAPTER_FOLDER = Path(__file__).resolve().parent
ADAPTER_PATH = (".pkit", "adapters", "claude-code")
RESOLVER = "_resolve_agent.py"

#: The longest the runner waits for the harness's version, and for the
#: deploy's resolution of the agent. Both count against the run's limit.
VERSION_SECONDS = 30
RESOLVE_SECONDS = 120

#: How long the runner waits for the stream's last lines once the harness has
#: exited, and how often it looks whether it has.
STREAM_GRACE_SECONDS = 2
POLL_SECONDS = 0.5

#: The part of the harness's settings schema the runner writes, as data
#: (ADR-066 point 3). A nested dict is an object with only those keys, `bool` a
#: boolean, `RULES` a list of permission rules, `STRINGS` a list of strings, and
#: a tuple the values the schema accepts. The names and types are Claude Code
#: 2.1.302's, a probe fact: a `-p` run skips a value it rejects, so the runner
#: checks first.
RULES = "permission rules"
STRINGS = "strings"
SETTINGS_SCHEMA: dict[str, Any] = {
    "permissions": {
        "allow": RULES,
        "deny": RULES,
        "defaultMode": ("acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan"),
        "disableBypassPermissionsMode": ("disable",),
        "blockReadsOutsideWorkingDirectories": bool,
    },
    "sandbox": {
        "enabled": bool,
        "failIfUnavailable": bool,
        "autoAllowBashIfSandboxed": bool,
        "allowUnsandboxedCommands": bool,
        "excludedCommands": STRINGS,
        "network": {"allowedDomains": STRINGS},
    },
    "autoMemoryEnabled": bool,
}

#: What a confined run's settings always hold (ADR-066 points 3, 4 and 6): the
#: mode that refuses rather than asks, no bypass mode, the file tools' block on
#: reads outside the working folder (the run's `Read` rule opens the clone, a
#: probe fact), the sandbox on and failing closed, no auto-approval, no retry
#: outside it, no allowed host, and the harness's memory off.
RUN_SETTINGS_FIXED: dict[tuple[str, ...], Any] = {
    ("permissions", "defaultMode"): RUN_MODE,
    ("permissions", "disableBypassPermissionsMode"): "disable",
    ("permissions", "blockReadsOutsideWorkingDirectories"): True,
    ("sandbox", "enabled"): True,
    ("sandbox", "failIfUnavailable"): True,
    ("sandbox", "autoAllowBashIfSandboxed"): False,
    ("sandbox", "allowUnsandboxedCommands"): False,
    ("sandbox", "network", "allowedDomains"): [],
    ("autoMemoryEnabled",): False,
}

#: A permission rule as the harness's schema takes it: `Tool` or
#: `Tool(content)`. A file tool takes no `:*` prefix form, and an MCP tool no
#: content. A probe fact, as the schema above is.
PERMISSION_RULE = re.compile(r"([A-Za-z][A-Za-z0-9_-]*)(?:\((.+)\))?", re.DOTALL)
FILE_TOOLS = frozenset({"Read", "Edit", "Write", "Glob", "Grep", "NotebookEdit", "MultiEdit"})
CONTROL = re.compile(r"[\x00-\x1f\x7f]")

#: The rule family of each file tool: the harness matches a path only against
#: `Read(...)` rules for the tools that read, and only against `Edit(...)` rules
#: for the tools that write. So a folder rule is written in its family's name,
#: and any other tool is a family of its own. A probe fact.
RULE_FAMILY = {
    "Read": "Read",
    "Grep": "Read",
    "Glob": "Read",
    "Write": "Edit",
    "Edit": "Edit",
    "MultiEdit": "Edit",
    "NotebookEdit": "Edit",
}

#: The rule families a run's tools fall in.
RUN_FAMILIES = frozenset(RULE_FAMILY.get(tool, tool) for tool in RUN_TOOLS)

#: A tool's name in a rule, or in an agent's tools.
TOOL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

#: A command token a rule may hold: none holds whitespace, a quote, `*`, `(`,
#: `)` or a control character, so no token widens the rule it is rendered into.
TOKEN_REFUSED = re.compile(r"[\s'\"`*()\x00-\x1f\x7f]")

#: A folder a rule may name: none holds a character a path rule reads as a
#: pattern.
FOLDER_REFUSED = re.compile(r"[*?\[\]{}()\\\x00-\x1f\x7f]")

# --- the agent's definition ----------------------------------------------------

#: The front-matter fields of the methodology's shape (ADR-066 point 3): those
#: of `refs.Declared`, the shape the methodology gives its agents and skills,
#: with `reads` holding its three lists, and an agent's name, description,
#: tools, model and effort. A parity test holds this set to
#: `src/project_kit/refs.py`. Any other field refuses the run.
DEFINITION_FIELDS = frozenset(
    {
        "name",
        "description",
        "tools",
        "model",
        "effort",
        "reads",
        "owns",
        "needs",
        "answers",
        "gates",
        "storyboards",
        "composes",
    }
)

#: The prefix of a run's agent name: the definition is passed under a name
#: unique to the run, so no other agent answers to it.
RUN_AGENT_PREFIX = "pkit-run-"

#: The front matter and the body of a resolved definition, as the resolver
#: splits them.
FRONT_MATTER = re.compile(r"^---\n(.*?\n)---\n(.*)$", re.DOTALL)

#: A top-level field of the front matter.
FIELD_LINE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*))?")

#: A block scalar's header: its style and chomping, no indentation indicator.
BLOCK_HEADER = re.compile(r"([|>])([+-]?)(?:[ \t]+#.*)?")

#: The first characters of a node the reader does not take as a plain value.
PLAIN_REFUSED = tuple("[]{}&*!|>%@`,?#")

#: The escapes of a double-quoted scalar, as YAML reads them.
ESCAPES = {
    "\\": "\\",
    '"': '"',
    "/": "/",
    " ": " ",
    "0": "\0",
    "a": "\x07",
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "v": "\x0b",
    "f": "\f",
    "r": "\r",
    "e": "\x1b",
    "N": "\x85",
    "_": "\xa0",
    "L": chr(0x2028),
    "P": chr(0x2029),
}
ESCAPE = re.compile(r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|.)", re.DOTALL)

#: The resolver's warnings: a line with this prefix. One that drops the model
#: or the effort refuses the run, and only the optional-read warning does not.
WARNING_PREFIX = "warning: "
DROPPED_POLICY = re.compile(r"warning: (model|effort) ")
OPTIONAL_READ = "warning: optional category <"

# The harness, once started: what a signal to stop ends first.
_harness: list[subprocess.Popen[bytes]] = []


class Refused(Exception):
    """The run is refused before it starts; the message is the reason."""


def answer(
    ending: str,
    *,
    exit_code: int | None = None,
    output: str = "",
    diagnostics: str = "",
    reason: str = "",
    confined: bool = False,
    refused_calls: list[dict[str, str]] | None = None,
    start_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": ANSWER_VERSION,
        "ending": ending,
        "exit_code": exit_code,
        "output": output,
        "diagnostics": diagnostics,
        "reason": reason,
    }
    if confined:
        result["refused_calls"] = refused_calls or []
        result["start_report"] = start_report
    return result


def check_marker(env: dict[str, str]) -> None:
    """Refuse when the marker of a run is set at all, empty included."""
    if MARKER in env:
        raise Refused(
            f"{MARKER} is set, so this runner was started inside an agent run, and a run "
            "starts no other agent (ADR-066 point 8)"
        )


# --- the request ----------------------------------------------------------------------


def carries_confined(text: str) -> bool:
    """Whether the request asks for the confined form, read before its check,
    so even a refusal of it answers with the confined form's keys."""
    with contextlib.suppress(ValueError):
        request = json.loads(text)
        return isinstance(request, dict) and "confined" in request
    return False


def read_request(text: str) -> dict[str, Any]:
    """The request, checked. Raises `Refused` naming what is wrong."""
    try:
        request = json.loads(text)
    except ValueError as exc:
        raise Refused(f"the request is not a JSON document: {exc}") from None
    if not isinstance(request, dict):
        raise Refused("the request is not a JSON object")
    confined = "confined" in request
    unknown = sorted(set(request) - (CONFINED_REQUEST_KEYS if confined else REQUEST_KEYS))
    if unknown:
        raise Refused(
            "the request carries keys this runner does not run: "
            + ", ".join(unknown)
            + (". The confined form takes no folder" if confined and "folder" in unknown else "")
        )
    version = request.get("schema_version")
    if version != REQUEST_VERSION or isinstance(version, bool):
        raise Refused(f"the request's schema_version is {version!r}; this runner reads 1")
    agent = request.get("agent")
    if not isinstance(agent, str) or not AGENT_NAME.fullmatch(agent):
        raise Refused(f"the agent {agent!r} is not a name")
    brief = request.get("brief")
    if not isinstance(brief, str) or not brief.strip() or "\0" in brief:
        raise Refused("the brief is empty, or not text")
    if confined:
        request["confined"] = read_confined(request["confined"])
    else:
        folder = request.get("folder")
        if (
            not isinstance(folder, str)
            or not Path(folder).is_absolute()
            or not Path(folder).is_dir()
        ):
            raise Refused(f"the folder {folder!r} is not a directory")
    limit = request.get("limit_seconds")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_LIMIT_SECONDS:
        raise Refused(f"the limit {limit!r} is not from 1 to {MAX_LIMIT_SECONDS} seconds")
    effort = request.get("effort")
    if effort is not None and effort not in EFFORT_LEVELS:
        raise Refused(f"the effort {effort!r} is not one of {', '.join(EFFORT_LEVELS)}")
    return request


def _real(path: str) -> Path:
    return Path(os.path.realpath(path))


def _inside(path: str | Path, folder: str | Path) -> bool:
    """Whether `path` lies strictly inside `folder`, links followed."""
    return _real(str(folder)) in _real(str(path)).parents


def read_confined(confined: Any) -> dict[str, Any]:
    """The request's `confined` object, checked: its folders, its rules and its
    exclusions."""
    if not isinstance(confined, dict):
        raise Refused("the request's confined is not a JSON object")
    unknown = sorted(set(confined) - CONFINED_KEYS)
    if unknown:
        raise Refused(
            "the request's confined carries keys this runner does not run: " + ", ".join(unknown)
        )
    missing = sorted(CONFINED_KEYS - set(confined))
    if missing:
        raise Refused("the request's confined lacks " + ", ".join(missing))
    for key in CONFINED_FOLDERS:
        value = confined[key]
        if not isinstance(value, str) or not os.path.isabs(value) or not os.path.isdir(value):
            raise Refused(f"the confined run's {key} {value!r} is not an absolute directory")
    if os.path.islink(confined["workspace"]) or not _inside(
        confined["workspace"], confined["working_copy"]
    ):
        raise Refused("the confined run's workspace is not a folder inside its working copy")
    if not _inside(confined["temp"], confined["workspace"]):
        raise Refused(
            "the confined run's temp folder is not inside its workspace, so the shell's temp "
            "folder could not lie there (ADR-066 point 6)"
        )
    if _real(confined["pkit_folder"]) == _real(confined["workspace"]) or _inside(
        confined["pkit_folder"], confined["workspace"]
    ):
        raise Refused(
            "the confined run's pkit folder lies in its workspace, a folder the run writes "
            "(ADR-066 point 6)"
        )
    rules = confined["rules"]
    if not isinstance(rules, dict) or set(rules) != {"allow", "deny"}:
        raise Refused("the confined run's rules are not an object of allow and deny")
    for side in ("allow", "deny"):
        if not isinstance(rules[side], list):
            raise Refused(f"the confined run's {side} rules are not a list")
        for rule in rules[side]:
            render_rule(rule)
    excluded = confined["excluded"]
    if not isinstance(excluded, list):
        raise Refused("the confined run's excluded commands are not a list")
    allowed = [rule["command"] for rule in rules["allow"] if "command" in rule]
    for prefix in excluded:
        render_command(prefix)
        if prefix not in allowed:
            raise Refused(
                f"the excluded command {prefix!r} is not one the run's rules allow "
                "(ADR-066 point 6)"
            )
    return confined


# --- the run's rules and settings -----------------------------------------------------


def render_command(tokens: Any) -> str:
    """A command's tokens, joined by one space. Raises `Refused` for a token
    that could widen the rule it is rendered into."""
    if not isinstance(tokens, list) or not tokens:
        raise Refused(f"the command {tokens!r} is not a list of tokens")
    for token in tokens:
        if not isinstance(token, str) or not token or TOKEN_REFUSED.search(token):
            raise Refused(
                f"the command token {token!r} is empty, or holds whitespace, a quote, `*`, "
                "a parenthesis or a control character"
            )
    return " ".join(tokens)


def render_rule(rule: Any) -> str:
    """One rule of the request, in the harness's terms. `{"tool": T}` is the
    whole tool; `{"tool": T, "folder": F}` is the tool on F and everything
    under it, written in T's rule family (`Write` as `Edit`, `Grep` and `Glob`
    as `Read`); `{"command": [...]}` is a shell command starting with those
    tokens."""
    if not isinstance(rule, dict):
        raise Refused(f"the rule {rule!r} is not an object")
    keys = set(rule)
    if keys == {"command"}:
        return f"Bash({render_command(rule['command'])}:*)"
    if keys not in ({"tool"}, {"tool", "folder"}):
        raise Refused(f"the rule {rule!r} is in none of the three forms")
    tool = rule["tool"]
    if not isinstance(tool, str) or not TOOL_NAME.fullmatch(tool):
        raise Refused(f"the rule's tool {tool!r} is not a tool's name")
    if keys == {"tool"}:
        return tool
    folder = rule["folder"]
    if (
        not isinstance(folder, str)
        or not folder.startswith("/")
        or FOLDER_REFUSED.search(folder)
        or os.path.normpath(folder) != (folder.rstrip("/") or "/")
    ):
        raise Refused(
            f"the rule's folder {folder!r} is not a plain absolute path, or holds a character "
            "a path rule reads as a pattern"
        )
    family = RULE_FAMILY.get(tool, tool)
    inner = folder.strip("/")
    return f"{family}(//{inner}/**)" if inner else f"{family}(//**)"


def _family(rule: dict[str, Any]) -> str:
    return "Bash" if "command" in rule else RULE_FAMILY.get(rule["tool"], rule["tool"])


def _within(path: str, folder: str) -> bool:
    folder = folder.rstrip("/")
    return path.rstrip("/") == folder or path.startswith(folder + "/")


def rules_meet(one: dict[str, Any], other: dict[str, Any]) -> bool:
    """Whether two of the request's rules reach a common call: they fall in one
    rule family, and one's folder or command lies within the other's. A rule of
    the whole tool reaches everything its family reaches."""
    if _family(one) != _family(other):
        return False
    if set(one) == {"tool"} or set(other) == {"tool"} or set(one) != set(other):
        return True
    if "command" in one:
        shorter, longer = sorted((one["command"], other["command"]), key=len)
        return longer[: len(shorter)] == shorter
    return _within(one["folder"], other["folder"]) or _within(other["folder"], one["folder"])


def held_denies(rules: dict[str, Any]) -> list[str]:
    """The request's denies the run's settings hold as native rules (ADR-066
    point 5). A deny of a tool that is not among the run's tools, such as
    `Edit`, is held by the tool list and not written: a bare `Edit` rule would
    take `Write` away from the workspace. Any other deny that reaches a call an
    allow reaches, in the same rule family, refuses the run."""
    held = []
    for deny in rules["deny"]:
        if deny.get("tool", "Bash") not in RUN_TOOLS:
            continue
        for allow in rules["allow"]:
            if rules_meet(deny, allow):
                raise Refused(
                    f"the deny {render_rule(deny)} would take away the allow "
                    f"{render_rule(allow)} in the same rule family, so the run's rules cannot "
                    "be held as native rules (ADR-066 point 5)"
                )
        held.append(render_rule(deny))
    return held


def held_by_tools(rule: str) -> bool:
    """Whether a deny copied from a settings file names only what the run's
    tool list already takes away: a tool outside it, with no content the
    harness matches a run's tool against. `Edit` alone is one; `Edit(path)` is
    not, since the harness matches `Write` against it. A rule the harness's
    schema would reject is kept, so the settings' check refuses it."""
    match = PERMISSION_RULE.fullmatch(rule)
    if match is None or rule_problem(rule) is not None:
        return False
    tool, content = match.groups()
    if tool in RUN_TOOLS:
        return False
    return content is None or RULE_FAMILY.get(tool, tool) not in RUN_FAMILIES


def left_out_settings(env: dict[str, str], working_copy: Path, project_root: Path) -> list[Path]:
    """The settings files a confined run leaves out, whose deny rules it
    carries (ADR-066 point 3): the person's user settings, the working copy's
    project settings, and the person's checkout's project and local
    settings."""
    config = env.get("CLAUDE_CONFIG_DIR") or os.path.join(
        env.get("HOME") or str(Path.home()), ".claude"
    )
    return [
        Path(config) / "settings.json",
        working_copy / ".claude" / "settings.json",
        project_root / ".claude" / "settings.json",
        project_root / ".claude" / "settings.local.json",
    ]


def settings_denies(paths: list[Path]) -> list[str]:
    """The deny rules of each settings file, copied as written. A file that
    is absent has none; one that cannot be read refuses the run, since its
    denies might be lost."""
    denies: list[str] = []
    for path in paths:
        if not os.path.lexists(path):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise Refused(f"the deny rules of {path} cannot be read: {exc}") from None
        if not isinstance(data, dict):
            raise Refused(f"the deny rules of {path} cannot be read: it is not a JSON object")
        permissions = data.get("permissions")
        if permissions is None:
            continue
        if not isinstance(permissions, dict):
            raise Refused(f"the deny rules of {path} cannot be read: its permissions are no object")
        deny = permissions.get("deny")
        if deny is None:
            continue
        if not isinstance(deny, list) or not all(isinstance(rule, str) for rule in deny):
            raise Refused(f"the deny rules of {path} are not a list of rules")
        denies.extend(deny)
    return denies


def run_settings(confined: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """The run's own settings (ADR-066 points 3 to 6): its allow list, its
    denies and those of each settings file it leaves out, less those the tool
    list holds, and the fixed values."""
    settings: dict[str, Any] = {}
    for path, value in RUN_SETTINGS_FIXED.items():
        place = settings
        for key in path[:-1]:
            place = place.setdefault(key, {})
        place[path[-1]] = list(value) if isinstance(value, list) else value
    rules = confined["rules"]
    copied = settings_denies(
        left_out_settings(env, Path(confined["working_copy"]), Path(confined["project_root"]))
    )
    denies = held_denies(rules) + [rule for rule in copied if not held_by_tools(rule)]
    settings["permissions"]["allow"] = list(
        dict.fromkeys(render_rule(rule) for rule in rules["allow"])
    )
    settings["permissions"]["deny"] = list(dict.fromkeys(denies))
    settings["sandbox"]["excludedCommands"] = [
        render_command(prefix) for prefix in confined["excluded"]
    ]
    return settings


def rule_problem(rule: Any) -> str | None:
    """What makes `rule` one the harness's schema would reject, or None."""
    if not isinstance(rule, str) or not rule.strip():
        return "is empty"
    if CONTROL.search(rule):
        return "holds a control character"
    match = PERMISSION_RULE.fullmatch(rule)
    if match is None:
        return "is not of the form Tool or Tool(content)"
    tool, content = match.groups()
    if "_" not in tool and not tool[0].isupper():
        return "names a tool that does not start with a capital"
    if tool.startswith("mcp__") and content is not None:
        return "gives an MCP tool a pattern"
    if content is not None and tool in FILE_TOOLS and ":*" in content:
        return "uses the :* prefix form on a file tool"
    if content == ":*":
        return "has no prefix before :*"
    return None


def _schema_problems(value: Any, schema: Any, where: str) -> list[str]:
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            return [f"{where or 'the settings'} is not an object"]
        inner = [(key, f"{where}.{key}" if where else key) for key in value]
        problems = [
            f"{name} is not a key the runner writes" for key, name in inner if key not in schema
        ]
        for key, name in inner:
            if key in schema:
                problems += _schema_problems(value[key], schema[key], name)
        return problems
    if schema is bool:
        return [] if isinstance(value, bool) else [f"{where} is not a boolean"]
    if isinstance(schema, tuple):
        return [] if value in schema else [f"{where} {value!r} is not one of {', '.join(schema)}"]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return [f"{where} is not a list of strings"]
    if schema == RULES:
        return [
            f"{where} rule {rule!r} {problem}"
            for rule in value
            for problem in [rule_problem(rule)]
            if problem
        ]
    return []


def check_settings(settings: dict[str, Any]) -> None:
    """Refuse settings that fail the part of the harness's settings schema the
    runner writes, or that miss a value a confined run always holds."""
    problems = _schema_problems(settings, SETTINGS_SCHEMA, "")
    for path, value in RUN_SETTINGS_FIXED.items():
        place: Any = settings
        for key in path:
            place = place.get(key) if isinstance(place, dict) else None
        if place != value:
            problems.append(f"{'.'.join(path)} is not {json.dumps(value)}")
    if problems:
        raise Refused(
            "the run's settings fail the harness's settings schema, or the confined form: "
            + "; ".join(problems)
        )


# --- the harness, its version and its platform -------------------------------------------


def find_harness(env: dict[str, str]) -> str:
    """The harness on the runner's PATH, made absolute. A relative PATH entry
    gives a relative path, found from the runner's folder: keep that one, not
    one the run's folder holds."""
    harness = shutil.which(HARNESS, path=env.get("PATH"))
    if harness is None:
        raise Refused(f"the `{HARNESS}` command line is not on PATH")
    return os.path.abspath(harness)


def harness_version(
    harness: str, env: dict[str, str], cwd: str, timeout: float = VERSION_SECONDS
) -> tuple[int, int, int]:
    """The harness's version, as `claude --version` prints it."""
    try:
        done = subprocess.run(
            [harness, "--version"],
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=max(timeout, 1),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refused(f"`{HARNESS} --version` could not be read: {exc}") from None
    version = _version_of(done.stdout.decode("utf-8", errors="replace"))
    if done.returncode != 0 or version is None:
        raise Refused(f"`{HARNESS} --version` printed no version (exit {done.returncode})")
    return version


def _version_of(text: str) -> tuple[int, int, int] | None:
    match = VERSION.search(text)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return (major, minor, patch)


def check_tested_range() -> None:
    """Refuse every confined run while no harness version is tested."""
    if len(TESTED_RANGE) != 2 or None in (_version_of(bound) for bound in TESTED_RANGE):
        raise Refused(
            "no harness version lies in the range the confined form was tested on: the range "
            "is empty until the adapter's author runs the probe (probe-confined-run.py) on a "
            "harness and widens it (ADR-066 points 2 and 12)"
        )


def check_version(version: tuple[int, int, int]) -> None:
    """Refuse a harness whose version lies outside `TESTED_RANGE`."""
    check_tested_range()
    shown = ".".join(str(part) for part in version)
    low, high = (_version_of(bound) for bound in TESTED_RANGE)
    assert low is not None and high is not None
    if not low <= version <= high:
        raise Refused(
            f"the harness's version {shown} lies outside the range the confined form was "
            f"tested on, {TESTED_RANGE[0]} to {TESTED_RANGE[1]}. Only the adapter's author "
            "widens it, after the probe passes on a newer harness (ADR-066 points 2 and 12)"
        )


def sandbox_gap(platform: str, path: str) -> str | None:
    """Why the platform offers no sandbox the harness can use, or None."""
    if platform == "darwin":
        if os.access(MACOS_SANDBOX, os.X_OK):
            return None
        return f"macOS's sandbox, {MACOS_SANDBOX}, is not there"
    if platform.startswith("linux"):
        missing = [name for name in LINUX_SANDBOX if shutil.which(name, path=path) is None]
        if not missing:
            return None
        return f"the sandbox needs {' and '.join(missing)} on the run's PATH"
    return f"the platform {platform} offers no sandbox the harness can use"


def resolver_of(working_copy: Path) -> Path:
    """The deploy's resolver beside this runner, once this runner is the
    working copy's own: the backbone runs the clone's copy, so the resolution
    it applies is the pinned commit's (ADR-066 point 3)."""
    expected = _real(str(working_copy)).joinpath(*ADAPTER_PATH)
    if _real(str(ADAPTER_FOLDER)) != expected:
        raise Refused(
            f"this runner lies in {ADAPTER_FOLDER}, not in the working copy's adapter folder "
            f"{expected}, so the deploy's resolution it applies would not be the pinned "
            "commit's (ADR-066 point 3)"
        )
    return ADAPTER_FOLDER / RESOLVER


def confined_environment(
    env: dict[str, str], confined: dict[str, Any], harness: str
) -> dict[str, str]:
    """The harness's environment in a confined run (ADR-066 point 4): only what
    the harness and the run's commands need. PATH puts the run's `pkit` first,
    then the folders of the harness and git, then the system's. The temp
    variables name the run's temp folder, and the marker is set. The harness's
    own scrub of the sign-in variables from every process it starts is turned
    on by name (`CREDENTIAL_SCRUB`), rather than left to its default."""
    folders = [confined["pkit_folder"], os.path.dirname(harness)]
    git = shutil.which("git", path=env.get("PATH"))
    if git is not None:
        folders.append(os.path.dirname(os.path.abspath(git)))
    folders.extend(SYSTEM_PATH)
    kept = {
        key: value
        for key, value in env.items()
        if key in KEPT_VARIABLES or key in SIGN_IN_VARIABLES or key.startswith("LC_")
    }
    return {
        **kept,
        "PATH": os.pathsep.join(dict.fromkeys(folders)),
        **dict.fromkeys(TEMP_VARIABLES, confined["temp"]),
        CREDENTIAL_SCRUB: "1",
        MARKER: "1",
    }


# --- the agent's definition ------------------------------------------------------------


def agent_source(working_copy: Path, agent: str) -> Path | None:
    """The agent's file in the working copy, as the deploy picks it among
    agents of one name: the project's, then an installed capability's (the
    first by name), then core's, each flat before folder form."""
    pkit = working_copy / ".pkit"
    capabilities = pkit / "capabilities"
    folders = [pkit / "agents" / "project"]
    if capabilities.is_dir():
        folders += [entry / "agents" for entry in sorted(capabilities.iterdir())]
    folders.append(pkit / "agents" / "core")
    for folder in folders:
        for candidate in (folder / f"{agent}.md", folder / agent / f"{agent}.md"):
            if candidate.is_file():
                return candidate
    return None


def _unreadable(field: str, why: str) -> Refused:
    return Refused(f"the agent's definition is not in the form the runner reads: {field} {why}")


def front_matter(text: str) -> dict[str, list[str]]:
    """Each top-level field of the front matter with its lines: first the text
    after its colon, then each line below it, as the resolver wrote them."""
    fields: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.split("\n"):
        if line.startswith("#"):
            continue
        if not line.strip() or line[0] in " \t" or line == "-" or line.startswith("- "):
            if current is None:
                if line.strip():
                    raise _unreadable("the front matter", f"opens with {line!r}")
                continue
            current.append(line)
            continue
        match = FIELD_LINE.fullmatch(line.rstrip())
        if match is None:
            raise _unreadable("the front matter", f"holds {line!r}")
        name = match.group(1)
        if name in fields:
            raise _unreadable(name, "is written twice")
        current = fields[name] = [match.group(2) or ""]
    return fields


def _fold(parts: list[str]) -> str:
    """Lines folded as YAML folds a flow scalar: one space between lines, and
    a line break for each empty line."""
    text = ""
    breaks = 0
    for part in parts:
        if part == "":
            breaks += 1
        elif not text:
            text, breaks = part, 0
        else:
            text += ("\n" * breaks or " ") + part
            breaks = 0
    return text


def _without_comment(text: str) -> str:
    return re.split(r"[ \t]#", text, maxsplit=1)[0].rstrip()


def _plain(head: str, rest: list[str], field: str) -> str:
    if head.startswith(PLAIN_REFUSED):
        raise _unreadable(field, "is not a plain value")
    parts = [_without_comment(head)]
    for line in rest:
        text = line.strip()
        if text.startswith("#"):
            raise _unreadable(field, "holds a comment line")
        parts.append(_without_comment(text))
    if any(": " in part or part.endswith(":") for part in parts):
        raise _unreadable(field, "holds a mapping")
    return _fold(parts)


def _unescape(text: str, field: str) -> str:
    def one(match: re.Match[str]) -> str:
        code = match.group(1)
        if code[0] in "xuU" and len(code) > 1:
            return chr(int(code[1:], 16))
        if code in ESCAPES:
            return ESCAPES[code]
        raise _unreadable(field, f"holds the escape \\{code}")

    return ESCAPE.sub(one, text)


def _quoted(head: str, rest: list[str], field: str) -> str:
    raw, quote = "\n".join([head, *rest]), head[0]
    index = 1
    while index < len(raw):
        if quote == '"' and raw[index] == "\\":
            index += 2
            continue
        if raw[index] == quote:
            if quote == "'" and raw[index + 1 : index + 2] == "'":
                index += 2
                continue
            break
        index += 1
    else:
        raise _unreadable(field, "has no closing quote")
    body, tail = raw[1:index], raw[index + 1 :].strip()
    if tail and not tail.startswith("#"):
        raise _unreadable(field, "goes on after its closing quote")
    lines = body.split("\n")
    if quote == '"' and any(line.rstrip().endswith("\\") for line in lines[:-1]):
        raise _unreadable(field, "holds an escaped line break")
    if len(lines) > 1:
        lines = [lines[0].rstrip(), *(line.strip() for line in lines[1:-1]), lines[-1].lstrip()]
    text = _fold(lines)
    return text.replace("''", "'") if quote == "'" else _unescape(text, field)


def _block(head: str, rest: list[str], field: str) -> str:
    match = BLOCK_HEADER.fullmatch(head)
    if match is None:
        raise _unreadable(field, "has a block header the runner does not read")
    style, chomp = match.groups()
    indent = next((len(line) - len(line.lstrip(" ")) for line in rest if line.strip()), None)
    if indent is None:
        return ""
    lines: list[str] = []
    for line in rest:
        if not line.strip():
            lines.append("")
        elif len(line) - len(line.lstrip(" ")) < indent:
            raise _unreadable(field, "is indented less than its first line")
        else:
            lines.append(line[indent:])
    while lines and lines[-1] == "":
        lines.pop()
    if style == ">":
        if any(line[:1] in (" ", "\t") for line in lines):
            raise _unreadable(field, "holds a line indented more than its first")
        text = _fold(lines)
    else:
        text = "\n".join(lines)
    return text if chomp == "-" else text + "\n"


def scalar(lines: list[str], field: str) -> str:
    """A field's value as text: plain, quoted, or a block."""
    head, rest = lines[0].strip(), lines[1:]
    if head[:1] in ("|", ">"):
        return _block(head, rest, field)
    if head[:1] in ('"', "'"):
        return _quoted(head, rest, field)
    return _plain(head, rest, field)


def _item(text: str, field: str) -> str:
    if text[:1] in ('"', "'"):
        return _quoted(text, [], field)
    return _plain(text, [], field)


def tool_list(lines: list[str], field: str = "tools") -> list[str]:
    """The agent's tools: a flow list, a block list, or one comma-separated
    string."""
    head, rest = lines[0].strip(), lines[1:]
    if head.startswith("["):
        raw = " ".join([head, *(line.strip() for line in rest)])
        close = raw.find("]")
        tail = raw[close + 1 :].strip() if close != -1 else ""
        if close == -1 or (tail and not tail.startswith("#")):
            raise _unreadable(field, "is not a closed list")
        body = raw[1:close]
        if any(mark in body for mark in "[]{}"):
            raise _unreadable(field, "nests a collection")
        names = [_item(item.strip(), field) for item in body.split(",") if item.strip()]
    elif head == "" or head.startswith("#"):
        names = []
        for line in rest:
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            if not text.startswith("- "):
                raise _unreadable(field, f"holds {text!r} in a list")
            names.append(_item(_without_comment(text[2:].strip()), field))
    else:
        names = [name.strip() for name in scalar(lines, field).split(",") if name.strip()]
    for name in names:
        if not TOOL_NAME.fullmatch(name):
            raise _unreadable(field, f"names {name!r}, which is not a tool's name")
    return names


def resolve_definition(
    resolver: Path,
    source: Path,
    agent: str,
    overlay: Path,
    cwd: Path,
    env: dict[str, str],
    timeout: float = RESOLVE_SECONDS,
) -> str:
    """The deploy's resolution of the agent's file: its text. Refuses where the
    resolver fails, or warns that it drops a value the run passes."""
    try:
        done = subprocess.run(
            [str(resolver), str(source), agent, str(overlay)],
            cwd=str(cwd),
            env={key: value for key, value in env.items() if key not in RUN_VARIABLES},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=max(timeout, 1),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refused(f"the deploy's resolution of the agent could not run: {exc}") from None
    errors = done.stderr.decode("utf-8", errors="replace")
    if done.returncode != 0:
        first = next((line for line in errors.splitlines() if line.strip()), "")
        raise Refused(
            "the deploy would not resolve the agent's definition: "
            + (first.strip() or f"its resolver exited with {done.returncode}")
        )
    for line in errors.splitlines():
        if not line.startswith(WARNING_PREFIX) or line.startswith(OPTIONAL_READ):
            continue
        if DROPPED_POLICY.match(line):
            raise Refused(
                "the deploy would drop a value the run passes, and nobody watches the run to "
                f"read its warning: {line[len(WARNING_PREFIX) :]}"
            )
        raise Refused(
            "the deploy warns, and the runner cannot tell whether it drops a value the run "
            f"passes: {line[len(WARNING_PREFIX) :]}"
        )
    return done.stdout.decode("utf-8", errors="replace")


def checked_definition(
    working_copy: Path,
    agent: str,
    effort: str | None,
    resolver: Path,
    env: dict[str, str],
    timeout: float = RESOLVE_SECONDS,
) -> dict[str, Any]:
    """The agent's definition as a confined run passes it (ADR-066 point 3):
    the deploy's resolution of the file the deploy picks, checked against the
    methodology's shape. It holds the description, the body as the prompt, the
    tools, the model and the effort, the caller's effort over the
    definition's. The other fields of the shape are read and never passed."""
    source = agent_source(working_copy, agent)
    if source is None:
        raise Refused(
            f"the working copy holds no definition of {agent} that the deploy would pick: no "
            f"{agent}.md or {agent}/{agent}.md in .pkit/agents/project, a capability's agents "
            "folder or .pkit/agents/core"
        )
    if not _inside(source, working_copy):
        raise Refused(f"the agent's file {source} leads outside the working copy")
    overlay = working_copy / ".pkit" / "agents" / "project" / "overlay.yaml"
    if os.path.lexists(overlay) and not _inside(overlay, working_copy):
        raise Refused(f"the overlay {overlay} leads outside the working copy")
    text = resolve_definition(resolver, source, agent, overlay, working_copy, env, timeout)
    match = FRONT_MATTER.match(text)
    if match is None:
        raise Refused("the deploy's resolution of the agent gave no front matter")
    fields = front_matter(match.group(1))
    outside = sorted(set(fields) - DEFINITION_FIELDS)
    if outside:
        raise Refused(
            "the agent's definition carries fields outside the methodology's shape: "
            + ", ".join(outside)
            + ". A confined run refuses them rather than trim them (ADR-066 point 3)"
        )
    description = scalar(fields["description"], "description") if "description" in fields else ""
    if not description.strip():
        raise Refused("the agent's definition has no description")
    prompt = match.group(2)
    if not prompt.strip():
        raise Refused("the agent's definition has no instructions")
    definition: dict[str, Any] = {"description": description, "prompt": prompt}
    if "tools" in fields:
        definition["tools"] = tool_list(fields["tools"])
    model = scalar(fields["model"], "model").strip() if "model" in fields else ""
    if model:
        definition["model"] = model
    chosen = effort
    if chosen is None and "effort" in fields:
        chosen = scalar(fields["effort"], "effort").strip() or None
    if chosen is not None:
        if chosen not in EFFORT_LEVELS:
            raise Refused(f"the agent's effort {chosen!r} is not one of {', '.join(EFFORT_LEVELS)}")
        definition["effort"] = chosen
    return definition


# --- the command line --------------------------------------------------------------------


def command(harness: str, agent: str, effort: str | None) -> list[str]:
    """The unconfined form's command line: the closed set's flags, and nothing
    else."""
    argv = [harness, "-p", "--agent", agent]
    if effort is not None:
        argv += ["--effort", effort]
    check_flags(argv)
    return argv


def confined_command(
    harness: str,
    run_name: str,
    definition: dict[str, Any],
    settings: dict[str, Any],
    effort: str | None,
) -> list[str]:
    """The confined form's command line: the closed set's flags, each with
    the value it always takes, and nothing else."""
    argv = [
        harness,
        "-p",
        "--setting-sources",
        CONFINED_VALUES["--setting-sources"],
        "--settings",
        json.dumps(settings),
        "--agents",
        json.dumps({run_name: definition}),
        "--agent",
        run_name,
        "--permission-mode",
        RUN_MODE,
        "--permission-prompts",
        CONFINED_VALUES["--permission-prompts"],
        "--tools",
        CONFINED_VALUES["--tools"],
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--output-format",
        CONFINED_VALUES["--output-format"],
        "--verbose",
        "--include-hook-events",
    ]
    if effort is not None:
        argv += ["--effort", effort]
    check_flags(argv, CONFINED_FLAGS, CONFINED_VALUES)
    return argv


def check_flags(
    argv: list[str],
    flags: dict[str, bool] | None = None,
    values: dict[str, str] | None = None,
) -> None:
    """Raise `Refused` when the command line passes a flag outside the closed
    set, a flag twice, a flag's value that reads as a flag, or a value other
    than the one the form always passes."""
    flags = FLAGS if flags is None else flags
    seen: set[str] = set()
    index = 1
    while index < len(argv):
        token = argv[index]
        if token not in flags:
            raise Refused(f"the command line passes {token!r}, which is not in the closed set")
        if token in seen:
            raise Refused(f"the command line passes {token!r} twice")
        seen.add(token)
        if flags[token]:
            index += 1
            if index >= len(argv) or argv[index].startswith("-"):
                raise Refused(f"the command line passes {token!r} with no value")
            if values is not None and token in values and argv[index] != values[token]:
                raise Refused(
                    f"the command line passes {token} {argv[index]!r}; the form passes only "
                    f"{values[token]!r}"
                )
        index += 1


def harness_environment(env: dict[str, str]) -> dict[str, str]:
    """The unconfined form's environment: the runner's, less the backbone's
    variables for its run, with the marker set."""
    kept = {key: value for key, value in env.items() if key not in RUN_VARIABLES}
    return {**kept, MARKER: "1"}


# --- the end of a run ---------------------------------------------------------------------


def process_table() -> dict[int, tuple[int, int]]:
    """Each process's parent and process group, as the system's `ps` lists
    them, by pid. Empty when no such `ps` can be read: the harness's own group
    is then all the runner ends."""
    ps = next((path for path in PS_CANDIDATES if os.access(path, os.X_OK)), None)
    if ps is None:
        return {}
    try:
        listed = subprocess.run(
            [ps, "-A", "-o", "pid=,ppid=,pgid="],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    table: dict[int, tuple[int, int]] = {}
    for line in listed.stdout.decode("ascii", errors="replace").splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            pid, ppid, pgid = (int(field) for field in fields)
        except ValueError:
            continue
        table[pid] = (ppid, pgid)
    return table


def descendants(root: int, table: dict[int, tuple[int, int]]) -> set[int]:
    """Every process the table shows descended from `root`."""
    children: dict[int, list[int]] = {}
    for pid, (ppid, _pgid) in table.items():
        children.setdefault(ppid, []).append(pid)
    found: set[int] = set()
    waiting = [root]
    while waiting:
        for child in children.get(waiting.pop(), ()):
            if child != root and child not in found:
                found.add(child)
                waiting.append(child)
    return found


def _signal_group(pgid: int, signum: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pgid, signum)


def end_harness(process: subprocess.Popen[bytes]) -> None:
    """End the harness and every process still descended from it.

    The harness leads a process group of its own, but Claude Code starts each
    shell command in a session of its own, so a kill of that one group would
    leave the commands running. The runner stops the harness's group first, so
    the harness starts nothing more. It then walks the process table for the
    harness's descendants and stops each one's group, until a walk finds no
    group it has not stopped, and then kills every group it stopped. A process
    that left the tree before the limit, as one that daemonises leaves it, is
    not found. Never the runner's own group, nor a group of 0 or 1."""
    own = os.getpgrp()
    stopped: list[int] = []

    def stop_group(pgid: int) -> bool:
        if pgid <= 1 or pgid == own or pgid in stopped:
            return False
        stopped.append(pgid)
        _signal_group(pgid, signal.SIGSTOP)
        return True

    stop_group(process.pid)
    for _ in range(END_ROUNDS):
        table = process_table()
        new = False
        for pid in sorted(descendants(process.pid, table)):
            new = stop_group(table[pid][1]) or new
        if not new:
            break
    for pgid in stopped:
        _signal_group(pgid, signal.SIGKILL)


# --- the unconfined form -------------------------------------------------------------------


def agent_file(agent: str, folder: Path, env: dict[str, str]) -> Path | None:
    """Where Claude Code finds the agent's definition: `.claude/agents/<agent>.md`
    in the folder or a folder above it, else in the person's own agents folder
    (`$CLAUDE_CONFIG_DIR/agents`, else `~/.claude/agents`). None when neither has
    it."""
    name = f"{agent}.md"
    for place in (folder, *folder.parents):
        candidate = place / ".claude" / "agents" / name
        if candidate.is_file():
            return candidate
    config = env.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    candidate = Path(config) / "agents" / name
    return candidate if candidate.is_file() else None


def run_unconfined(request: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """Run an unconfined request, and answer how it ended."""
    harness = find_harness(env)
    folder = Path(request["folder"])
    agent = request["agent"]
    if agent_file(agent, folder, env) is None:
        raise Refused(
            f"the agent {agent} is not deployed: no .claude/agents/{agent}.md in {folder} "
            "or a folder above it, nor in the person's own agents folder"
        )
    argv = command(harness, agent, request.get("effort"))
    try:
        process = subprocess.Popen(
            argv,
            cwd=str(folder),
            env=harness_environment(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        return answer(NOT_STARTED, reason=f"`{HARNESS}` could not be started: {exc}")
    _harness.append(process)
    limit = request["limit_seconds"]
    try:
        raw_out, raw_err = process.communicate(
            request["brief"].encode("utf-8", errors="replace"), timeout=limit
        )
    except subprocess.TimeoutExpired:
        end_harness(process)
        process.wait()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        return answer(
            TIMED_OUT,
            reason=(
                f"the agent did not finish within {limit} s, so the harness was ended "
                "with every process still descended from it"
            ),
        )
    return answer(
        FINISHED,
        exit_code=process.returncode,
        output=raw_out.decode("utf-8", errors="replace"),
        diagnostics=raw_err.decode("utf-8", errors="replace"),
    )


# --- the confined form ---------------------------------------------------------------------


def start_report_mismatch(report: dict[str, Any]) -> str | None:
    """Where the harness's start report does not match the run's settings
    (ADR-066 point 9): its mode, a tool outside the run's, any MCP server or
    plugin. None when it matches."""
    mode = report.get("permissionMode")
    if mode != RUN_MODE:
        return f"the harness started in the mode {mode!r}, not {RUN_MODE}"
    tools = report.get("tools")
    if not isinstance(tools, list):
        return "the start report names no tools"
    extra = sorted(str(tool) for tool in tools if tool not in RUN_TOOLS)
    if extra:
        return "the harness offers tools outside the run's: " + ", ".join(extra)
    for key, what in (
        ("mcp_servers", "MCP servers"),
        ("mcp_server_errors", "MCP servers"),
        ("plugins", "plugins"),
        ("plugin_errors", "plugins"),
    ):
        listed = report.get(key, [] if key.endswith("errors") else None)
        if not isinstance(listed, list):
            return f"the start report does not list the harness's {what}"
        if listed:
            return f"the harness loaded {what}: {json.dumps(listed)}"
    return None


class Stream:
    """What the runner reads of a confined run's stream (ADR-066 point 9): the
    start report, the result, and what ends the run at once."""

    def __init__(self) -> None:
        self.report: dict[str, Any] | None = None
        self.result: dict[str, Any] | None = None

    def take(self, line: bytes) -> str | None:
        """Read one line; the mismatch that ends the run, or None."""
        try:
            event = json.loads(line.decode("utf-8", errors="replace"))
        except ValueError:
            return None
        if not isinstance(event, dict):
            return None
        kind, subtype = event.get("type"), event.get("subtype")
        if kind == "system" and isinstance(subtype, str) and subtype.startswith("hook_"):
            return (
                f"the harness ran a hook ({event.get('hook_event')!r}, "
                f"{event.get('hook_name')!r}), and a confined run loads none"
            )
        if self.report is None:
            if kind == "system" and subtype == "init":
                self.report = event
                return start_report_mismatch(event)
            if kind != "system":
                return f"the harness reported {kind!r} before its start report"
            return None
        if kind == "result":
            self.result = event
        return None

    def output(self) -> str:
        """The agent's final message: the result's text, never a tool's."""
        text = (self.result or {}).get("result")
        return text if isinstance(text, str) else ""

    def refused_calls(self) -> list[dict[str, str]]:
        """The calls the harness refused, as it reports them."""
        denials = (self.result or {}).get("permission_denials")
        if not isinstance(denials, list):
            return []
        calls = []
        for denial in denials:
            if not isinstance(denial, dict):
                continue
            given = denial.get("tool_input")
            calls.append(
                {
                    "tool": str(denial.get("tool_name", "")),
                    "input": given if isinstance(given, str) else json.dumps(given),
                }
            )
        return calls


def _feed(stream: Any, data: bytes) -> None:
    with contextlib.suppress(OSError, ValueError):
        stream.write(data)
    with contextlib.suppress(OSError, ValueError):
        stream.close()


def _read_lines(stream: Any, lines: queue.Queue[bytes | None]) -> None:
    with contextlib.suppress(OSError, ValueError):
        for line in iter(stream.readline, b""):
            lines.put(line)
    lines.put(None)


def _collect(stream: Any, chunks: list[bytes]) -> None:
    with contextlib.suppress(OSError, ValueError):
        for chunk in iter(lambda: stream.read(65536), b""):
            chunks.append(chunk)


def watch(
    argv: list[str], cwd: str, env: dict[str, str], brief: str, deadline: float, limit: int
) -> dict[str, Any]:
    """Start the harness, read its stream, and answer how the run ended."""
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        return answer(NOT_STARTED, reason=f"`{HARNESS}` could not be started: {exc}", confined=True)
    _harness.append(process)
    lines: queue.Queue[bytes | None] = queue.Queue()
    errors: list[bytes] = []
    reader = threading.Thread(target=_read_lines, args=(process.stdout, lines), daemon=True)
    threads = [
        threading.Thread(
            target=_feed, args=(process.stdin, brief.encode("utf-8", errors="replace")), daemon=True
        ),
        reader,
        threading.Thread(target=_collect, args=(process.stderr, errors), daemon=True),
    ]
    for thread in threads:
        thread.start()
    stream = Stream()
    mismatch: str | None = None
    timed_out = False
    while mismatch is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        try:
            line = lines.get(timeout=min(remaining, POLL_SECONDS))
        except queue.Empty:
            if process.poll() is None:
                continue
            # The harness has exited: read the stream's last lines, and stop
            # waiting for a pipe that a stray process may hold open.
            reader.join(timeout=STREAM_GRACE_SECONDS)
            while mismatch is None:
                try:
                    line = lines.get_nowait()
                except queue.Empty:
                    break
                if line is None:
                    break
                mismatch = stream.take(line)
            break
        if line is None:
            break
        mismatch = stream.take(line)
    if mismatch is None and not timed_out:
        try:
            process.wait(timeout=max(deadline - time.monotonic(), 0.1))
        except subprocess.TimeoutExpired:
            timed_out = True
    if mismatch is not None or timed_out:
        end_harness(process)
    process.wait()
    for thread in threads:
        thread.join(timeout=STREAM_GRACE_SECONDS)
    diagnostics = b"".join(errors).decode("utf-8", errors="replace")
    if mismatch is not None:
        return answer(
            REFUSED,
            reason=f"the run was ended at once: {mismatch} (ADR-066 point 9)",
            diagnostics=diagnostics,
            confined=True,
            start_report=stream.report,
        )
    if timed_out:
        return answer(
            TIMED_OUT,
            reason=(
                f"the agent did not finish within {limit} s, so the harness was ended "
                "with every process still descended from it"
            ),
            diagnostics=diagnostics,
            confined=True,
            start_report=stream.report,
        )
    if stream.report is None:
        return answer(
            REFUSED,
            reason=(
                "the harness gave no start report, so nothing shows the run was confined "
                f"(ADR-066 point 9); it exited with {process.returncode}"
            ),
            diagnostics=diagnostics,
            confined=True,
        )
    return answer(
        FINISHED,
        exit_code=process.returncode,
        output=stream.output(),
        diagnostics=diagnostics,
        confined=True,
        refused_calls=stream.refused_calls(),
        start_report=stream.report,
    )


def run_confined(request: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """Run a confined request (ADR-066 points 2 to 6 and 9), and answer how it
    ended. The limit counts from here, so the checks before the start count
    against it."""
    deadline = time.monotonic() + request["limit_seconds"]
    confined = request["confined"]
    working_copy = Path(confined["working_copy"])
    workspace = confined["workspace"]
    harness = find_harness(env)
    run_env = confined_environment(env, confined, harness)
    gap = sandbox_gap(sys.platform, run_env["PATH"])
    if gap is not None:
        raise Refused(f"the harness cannot sandbox the run: {gap} (ADR-066 point 6)")
    check_tested_range()
    check_version(
        harness_version(
            harness, run_env, workspace, min(VERSION_SECONDS, deadline - time.monotonic())
        )
    )
    resolver = resolver_of(working_copy)
    effort = request.get("effort")
    definition = checked_definition(
        working_copy,
        request["agent"],
        effort,
        resolver,
        env,
        min(RESOLVE_SECONDS, deadline - time.monotonic()),
    )
    settings = run_settings(confined, env)
    check_settings(settings)
    run_name = RUN_AGENT_PREFIX + secrets.token_hex(8)
    argv = confined_command(harness, run_name, definition, settings, effort)
    return watch(argv, workspace, run_env, request["brief"], deadline, request["limit_seconds"])


def run(request: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """Run the request in its form, and answer how it ended."""
    if "confined" in request:
        return run_confined(request, env)
    return run_unconfined(request, env)


def stop(signum: int, _frame: object) -> None:
    """Asked to stop: end the harness first (`end_harness`), then exit with no
    answer."""
    for process in _harness:
        end_harness(process)
    os._exit(128 + signum)


def main() -> int:
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, stop)
    env = dict(os.environ)
    text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    confined = carries_confined(text)
    try:
        check_marker(env)
        result = run(read_request(text), env)
    except Refused as refused:
        result = answer(REFUSED, reason=str(refused), confined=confined)
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
