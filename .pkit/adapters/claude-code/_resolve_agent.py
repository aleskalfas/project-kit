#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml"]
# ///
"""Resolve overlay placeholders in an agent file's frontmatter, write to stdout.

Invoked by `deploy-agents.sh` once per agent. Reads:

- arg 1: source agent file (`.pkit/agents/{core,project}/<name>/<name>.md`,
  or a capability's `.pkit/capabilities/<cap>/agents/<name>/<name>.md`)
- arg 2: agent name (used for per-agent overrides lookup)
- arg 3: overlay file (`.pkit/agents/project/overlay.yaml`)

Writes the resolved agent file content to stdout (frontmatter with
placeholders substituted + original body). Exits non-zero with a clear
error message if a placeholder references a category the overlay does
not define *through a hard channel* (any list key or `reads.paths` /
`reads.records`), or if a *write-carrying* category names sync-managed
content (the no-shared-files invariant at the agent surface, per ADR-051).
A category referenced *only* through `reads.patterns` is an **optional
read** (ADR-052): undefined, its item is dropped and the resolver still
exits 0 so the agent deploys as a generalist. A *bare* optional key (present,
no value) is dropped the same way but reported on stderr as a `warning:` line.

It also carries the agent's execution policy (#1047): `model:` and `effort:`
from the front matter, each overridable per agent under the overlay's
`overrides.<agent>` block. Absent or `inherit` writes no key, so the harness
default applies; a value the harness does not accept is not written either —
the agent deploys, inherits, and a `warning:` line names the value.

It rebases the agent's storyboards (COR-016) onto their source paths. A source
declares a storyboard by its bare sibling filename (`storyboard.md`), which
stays right wherever the agent's folder lives; the deployed copy lives
elsewhere, where that name resolves to nothing. So each `storyboards:` entry
naming a file beside the source is rewritten — in the list and wherever the
body cites it — to that file's project-root-relative path, the path the runtime
reads it from. An entry already written as a source path is left as written.

It ends the body with the adapter's workspace sentence (#2026): the session
scratch directory the harness's environment note names is replaced by the agent
workspace. The start hook (`session-start-hook.py`) gives every session and
subagent the same sentence, and a test holds the two equal.

It writes the agent's tool access from the answer of the agents area's reader,
`.pkit/agents/tool_access.py`, never from the author's text (ADR-086 point 3):
a grant as `tools`, a withheld list as Claude Code's `disallowedTools`, and no
key for a definition that names neither (ADR-085 point 1). Given
`--methodology-keys`, as the agent runner gives it, it keeps the methodology's
keys, `tools` and `withheld`, and the runner writes Claude Code's (ADR-086
point 4). A definition the reader refuses, or whose access Claude Code cannot
enforce or translate, by the adapter's declaration of tool access
(`tool-access.json`, which the reader applies), is refused before anything
else, with exit status 3 (`TOOL_ACCESS_REFUSED`): the deploy then removes the
copy it deployed before, since that copy may give tools the definition no
longer gives (COR-013 point 7).

Refused for another cause, such as an overlay category the project has not set
or a front matter that gives the agent another name than its file's (COR-013
point 8), it exits with status 1 (`REFUSED`). Given `--earlier <copy>`, the
copy the deploy wrote before from the same definition, it exits instead with
status 4 (`KEEP_EARLIER`) where the tool access that copy's mark records gives
nothing the current text's does not, each entry read whole with its argument
(ADR-087 point 4): the deploy then keeps that copy and says it is not of the
current text. Where the reader, the declaration, the ownership module or the
picker cannot be read, it cannot tell, and exits with status 5
(`CANNOT_TELL`): the deploy changes nothing for that name.

Given `--mark <place>`, as the deploy gives it, it writes the deploy's mark as
the front matter's first lines: the mark itself, then the definition the copy
is written from (its place, COR-013 point 8), the digest of the text it read, as
the agents area's picker computes it, and the tool access the reader read from
that text, in the methodology's keys (ADR-087 point 4).

Two other entries ask the agents area's picker, `.pkit/agents/definition_source.py`,
which definition of a name is the agent (COR-013 point 8, ADR-087 point 2):

- `--plan` writes, a line for each name some place ships, what the deploy does
  with it, tab-separated: `agent`, `refused`, `none` or `untold`, then the name
  and what that needs (`plan`). Where the picker cannot be reached, it exits
  with status 5 and writes nothing to standard output.
- `--pick <name>`, the agent runner's entry, writes one JSON document naming the
  file of the name's agent, or whether no place ships the name, or why it has no
  agent the runner may run (`pick_answer`).

The sync-managed check above is one this script *applies* but does not
*define*. The sync-managed predicate and the write-carrying category registry live
once, in the lifecycle layer's propagated `.pkit/lifecycle/ownership.py`,
and this resolver imports them (ADR-051 Decision point 3): re-deriving
the tier-ownership map per adapter would fork the predicate and silently
skip the check on the next harness. The import is the ADR-003 pattern —
a propagated in-tree module both the global `pkit` runtime and this
script can load.

Self-contained: PEP 723 inline metadata declares the `ruamel.yaml`
dependency, so `uv run --script` installs it transparently on first
invocation. No host pyproject.toml required.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from types import ModuleType

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

# `<root>/.pkit/adapters/claude-code/_resolve_agent.py` → `<root>`.
TARGET_ROOT = Path(__file__).resolve().parents[3]

# The agents area's reader of an agent's tool access (ADR-086 point 1), and this
# adapter's folder, which holds its declaration of tool access (point 4).
TOOL_ACCESS_READER = TARGET_ROOT / ".pkit" / "agents" / "tool_access.py"
ADAPTER_FOLDER = Path(__file__).resolve().parent

# The agents area's picker of which definition of a name is the agent (ADR-087
# point 2), which loads the lifecycle's reader of the records from this tree.
PICKER = TARGET_ROOT / ".pkit" / "agents" / "definition_source.py"

# The flag the agent runner passes: keep the methodology's keys of tool access.
METHODOLOGY_KEYS_FLAG = "--methodology-keys"

# The deploy's flags: write the mark, naming the place the definition is shipped
# from, and the copy the deploy wrote before from that definition.
MARK_FLAG = "--mark"
EARLIER_FLAG = "--earlier"

# The two entries that ask the picker: the deploy's plan, and the runner's pick.
PLAN_FLAG = "--plan"
PICK_FLAG = "--pick"

# The exit statuses `deploy-agents.sh` reads (ADR-087 point 4): refused for a cause
# other than the tool access, so the copy deployed before goes; refused for the tool
# access, so it goes too (COR-013 point 7); refused for another cause, where that
# copy gives nothing the current text does not, so it stays; and cannot tell, so
# nothing changes for the name.
REFUSED = 1
TOOL_ACCESS_REFUSED = 3
KEEP_EARLIER = 4
CANNOT_TELL = 5

# The deploy's mark, and the three lines beside it (ADR-087 point 4). The mark is
# the front matter's first line, which other parts and shipped migrations match;
# `deploy-agents.sh` holds the same value, and a test holds the two equal. YAML
# comments, so no harness reads them as keys.
MARKER = "# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync"
MARK_DEFINITION = "# pkit-definition: "
MARK_DIGEST = "# pkit-digest: "
MARK_TOOL_ACCESS = "# pkit-tool-access: "
# What the tool-access line records for a definition that names neither form.
NO_FORM = "none"
# How many lines of a copy the mark and its three lines lie within.
MARK_LINES = 5

# The frontmatter keys whose list items may carry `<category>` placeholders,
# split by *channel* per ADR-052. The backbone scanner (`agents_overlay.py`)
# mirrors these under the same names, and a parity test extracts both by name
# and asserts equality — so the two implementations cannot drift on which keys
# resolve, nor on which channel is hard vs. optional.
#
#   - RESOLVABLE_LIST_KEYS / HARD_READS_KEYS are *hard*: an undefined placeholder
#     fails the deploy and skips the agent.
#   - OPTIONAL_READS_KEYS (`reads.patterns`) is *optional*: an undefined
#     placeholder is dropped and the agent still deploys — the empty-is-normal
#     read channel (ADR-013 D1 / ADR-052). A category referenced *both* here and
#     under a hard key is hard (the hard reference wins).
RESOLVABLE_LIST_KEYS = ("owns", "needs", "answers")
HARD_READS_KEYS = ("paths", "records")
OPTIONAL_READS_KEYS = ("patterns",)

# The agent's execution policy (#1047): the front-matter keys carried into the
# deployed definition, and the values the harness accepts for them. The backbone
# (`agent_policy.py`) holds the same constants under the same names, and a parity
# test pins them — so `pkit agents` reports exactly what this resolver writes.
#
#   - Precedence: the overlay's `overrides.<agent>.<key>` > the front matter >
#     inherit. Inside an override block these keys set the policy; they are not
#     overlay categories.
#   - `inherit`, absent, or bare writes no key: the harness default applies.
#   - A value outside the vocabulary is not written: the agent deploys, inherits,
#     and a `warning:` line names the value.
#
# The harness also accepts an integer effort; the vocabulary here is the named
# levels, the same list `review-pr --effort` accepts.
POLICY_KEYS = ("model", "effort")
INHERIT = "inherit"
MODEL_ALIASES = (
    "sonnet",
    "opus",
    "haiku",
    "fable",
    "best",
    "opusplan",
    "sonnet[1m]",
    "opus[1m]",
    "fable[1m]",
)
FULL_MODEL_NAME_PATTERN = r"^(?:[A-Za-z0-9-]+\.)*claude-\S+$"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

# The sentence every resolved body ends with (#2026), worded against the
# harness's environment note, which names a session scratch directory outside
# the repository. `session-start-hook.py` holds the same constant under the same
# name, and a test pins the two equal.
WORKSPACE_NOTE = (
    "The session scratch directory your environment names is replaced by "
    "`.agent-workspace/` at the repository root: keep every intermediate file there, "
    "never in that directory."
)

# Prefix of a stderr line that reports a problem without failing the resolve.
# `deploy-agents.sh` prints these lines for an agent that still deploys; any
# other stderr from a successful run (e.g. from `uv`) stays hidden.
WARNING_PREFIX = "warning: "


class Refusal(Exception):
    """The definition is refused for a cause other than its tool access.

    `lines` are the reason, then any remediation. `access` is the current text's
    tool access, where it was read before the refusal.
    """

    def __init__(self, lines: list[str], access=None) -> None:
        super().__init__(lines[0])
        self.lines = lines
        self.access = access


class CannotTell(Exception):
    """A module or a declaration the resolution needs cannot be read; the message
    says which, and the fix."""


def load_module(path: Path, name: str) -> ModuleType:
    """The module at *path*, loaded from its file, writing no bytecode beside it.

    Raises when the file is absent or cannot be loaded; the caller names the cause.
    """
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def write_tool_access(
    fm_data: CommentedMap, access, keys: dict[str, str], methodology_keys: tuple[str, ...]
) -> None:
    """Write the reader's *access* into *fm_data* under *keys*, never the author's text.

    The key written takes the place of the one the author wrote. Each entry is
    written whole, with its argument, and an empty grant as an empty list. A
    definition that names neither form gets no key (ADR-085 point 1, ADR-086
    point 3).
    """
    position = next((index for index, key in enumerate(fm_data) if key in methodology_keys), 0)
    for key in methodology_keys:
        fm_data.pop(key, None)
    if access.form is None:
        return
    entries = CommentedSeq(str(entry) for entry in access.entries)
    entries.fa.set_flow_style()
    fm_data.insert(position, keys[access.form], entries)


def load_ownership():
    """Import the lifecycle layer's ownership predicates from the target tree.

    Raises when the module is absent; the caller turns that into a loud skip.
    Degrading is not an option: the module is also what says *which* categories
    are write-carrying, so without it the resolver cannot tell a checked grant
    from an unchecked one — and deploying an unchecked grant is the outcome
    ADR-051 exists to prevent.
    """
    path = TARGET_ROOT / ".pkit" / "lifecycle" / "ownership.py"
    if not path.is_file():
        raise FileNotFoundError(path)
    sys.path.insert(0, str(path.parent))
    import ownership  # deliberately lazy; see above.

    return ownership


def policy_hint(key: str, value: object) -> str | None:
    """What to write instead when *value* is not accepted for policy *key*; None if it is."""
    if key == "model":
        if isinstance(value, str) and (
            value == INHERIT or value in MODEL_ALIASES or re.match(FULL_MODEL_NAME_PATTERN, value)
        ):
            return None
        return (
            f"use {INHERIT}, an alias ({', '.join(MODEL_ALIASES)}) or a full model name (claude-…)"
        )
    if isinstance(value, str) and (value == INHERIT or value in EFFORT_LEVELS):
        return None
    return f"use {INHERIT} or one of {', '.join(EFFORT_LEVELS)}"


def carry_policy(fm_data: dict, overrides: dict, where_overridden: str, warn) -> None:
    """Write each policy key's effective value into *fm_data*, or drop the key.

    *overrides* holds the policy keys of the agent's overlay override block. The
    override wins over the front matter; `inherit`, absent and bare write
    nothing; a value the harness does not accept is dropped with a warning, so
    the agent still deploys and inherits.
    """
    for key in POLICY_KEYS:
        if overrides.get(key) is not None:
            value, where = overrides[key], f"{where_overridden}.{key}"
        elif fm_data.get(key) is not None:
            value, where = fm_data[key], "the front matter"
        else:
            fm_data.pop(key, None)
            continue
        hint = policy_hint(key, value)
        if hint is not None:
            warn(
                f"{key} {value!r} from {where} is not one the harness accepts — "
                f"not carried, the agent inherits; {hint}."
            )
            fm_data.pop(key, None)
        elif value == INHERIT:
            fm_data.pop(key, None)
        else:
            fm_data[key] = value


def rebase_sibling_storyboards(fm_data: dict, body: str, source_file: Path) -> str:
    """Rewrite each sibling `storyboards:` entry to its source path, and the body alike.

    A sibling entry is one that names a file beside the source (inside the
    project). Its citations in the body are rewritten where the entry stands as
    a whole path token — not inside a longer path, and not as the tail of a
    `<scenario>.storyboard.md` name.
    """
    entries = fm_data.get("storyboards")
    if not isinstance(entries, list):
        return body
    source_dir = source_file.resolve().parent
    for index, entry in enumerate(entries):
        if not isinstance(entry, str) or Path(entry).is_absolute():
            continue
        sibling = (source_dir / entry).resolve()
        if not sibling.is_file() or TARGET_ROOT not in sibling.parents:
            continue
        source_path = sibling.relative_to(TARGET_ROOT).as_posix()
        if source_path == entry:
            continue
        entries[index] = source_path
        body = re.sub(
            rf"(?<![\w./-]){re.escape(entry)}(?![\w/-]|\.\w)",
            lambda _match, path=source_path: path,
            body,
        )
    return body


def end_with_workspace_note(body: str) -> str:
    """*body* ending with the workspace sentence as its last paragraph, added once."""
    if WORKSPACE_NOTE in body:
        return body
    return f"{body.rstrip()}\n\n{WORKSPACE_NOTE}\n"


class ToolAccessRefused(Exception):
    """The definition is refused for its tool access; the message says why."""


def tool_access_line(access) -> str:
    """The tool access *access* as the mark records it: the methodology's key and
    its entries, each whole and quoted, or `none` for a definition naming neither."""
    if access.form is None:
        return NO_FORM
    entries = ", ".join(json.dumps(str(entry), ensure_ascii=False) for entry in access.entries)
    return f"{access.form}: [{entries}]"


def recorded_tool_access(copy: Path, reader: ModuleType):
    """The tool access the mark of the copy at *copy* records, or None where it
    records none or cannot be read: such a copy is not kept on a refusal."""
    try:
        with copy.open(encoding="utf-8") as handle:
            head = [handle.readline().rstrip("\n") for _ in range(MARK_LINES)]
    except (OSError, UnicodeDecodeError):
        return None
    if MARKER not in head:
        return None
    line = next((line for line in head if line.startswith(MARK_TOOL_ACCESS)), None)
    if line is None:
        return None
    recorded = line[len(MARK_TOOL_ACCESS) :].strip()
    if recorded == NO_FORM:
        return reader.Access(None)
    try:
        return reader.tool_access(f"---\n{recorded}\n---\n")
    except reader.Refused:
        return None


def resolve(
    source_file: str,
    agent_name: str,
    overlay_file: str,
    *,
    methodology_keys: bool,
    mark: str | None,
) -> str:
    """The resolved text of the agent *agent_name* from *source_file*.

    Raises `ToolAccessRefused` for a definition refused for its tool access,
    `Refusal` for one refused for another cause, and `CannotTell` where a module or
    the adapter's declaration it needs cannot be read.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    defaults: dict = {}
    agent_overrides: dict = {}
    overlay_path = Path(overlay_file)
    if overlay_path.is_file() and overlay_path.stat().st_size > 0:
        with overlay_path.open() as f:
            data = yaml.load(f) or {}
        overrides = data.pop("overrides", {}) or {}
        agent_overrides = overrides.get(agent_name, {}) or {}
        defaults = data
    # The policy keys of the override block set the agent's model and effort;
    # they are not categories, so they leave the category lookup below.
    policy_overrides = {
        key: agent_overrides.pop(key) for key in POLICY_KEYS if key in agent_overrides
    }

    def resolve_category(category: str):
        if category in agent_overrides:
            return agent_overrides[category]
        if category in defaults:
            return defaults[category]
        return None

    def is_bare(category: str) -> bool:
        """The key is present but carries no value (``cat:`` alone).

        ``resolve_category`` returns None for both a bare and an absent key; only a
        bare one is a half-finished edit by the adopter, worth telling them about.
        """
        return (category in agent_overrides or category in defaults) and resolve_category(
            category
        ) is None

    content = Path(source_file).read_text(encoding="utf-8")

    # The tool access first, so a definition refused for it is refused whatever
    # else it gets wrong, and the deploy removes its earlier copy (ADR-086 point 3).
    try:
        reader = load_module(TOOL_ACCESS_READER, "pkit_agents_tool_access")
        read_tool_access = reader.tool_access
        read_declaration = reader.read_declaration
        declaration_path = reader.declaration_path
        bad_declaration = reader.BadDeclaration
        harness_refusal = reader.harness_refusal
    except Exception as exc:
        raise CannotTell(
            f"{agent_name}: cannot read the agent's tool access: no reader at "
            f".pkit/agents/tool_access.py, or none this resolver can call ({exc}).\n"
            "Fix: run `pkit sync`, which copies the reader and this resolver together."
        ) from None
    try:
        declaration = read_declaration(ADAPTER_FOLDER)
    except bad_declaration as exc:
        declaration, cause = None, f"cannot be read: {exc}"
    else:
        cause = "is not there"
    if declaration is None:
        raise CannotTell(
            f"{agent_name}: cannot check the agent's tool access: the adapter's declaration of "
            f"tool access, {declaration_path(ADAPTER_FOLDER).relative_to(TARGET_ROOT)}, "
            f"{cause}.\nFix: run `pkit sync`, which copies it with this resolver."
        )
    try:
        access = read_tool_access(content)
    except reader.Refused as exc:
        raise ToolAccessRefused(f"{agent_name}: its tool access is refused: {exc}") from None

    match = re.match(r"^---\n(.*?\n)---\n(.*)$", content, re.DOTALL)
    if not match:
        raise Refusal([f"{agent_name}: agent file has no frontmatter"], access)
    fm_yaml = match.group(1)
    body = match.group(2)
    fm_data = yaml.load(io.StringIO(fm_yaml)) or {}

    problem = harness_refusal(access, list(fm_data), declaration)
    if problem is not None:
        raise ToolAccessRefused(
            f"{agent_name}: its tool access is refused, since {declaration.harness} cannot "
            f"enforce or translate it: {problem}"
        )

    # An agent's name is its file's name, and a definition whose front matter gives
    # another is refused (COR-013 point 8).
    written = fm_data.get("name")
    if written is not None and str(written) != agent_name:
        raise Refusal(
            [
                f"{agent_name}: its front matter names the agent {written!r}, not {agent_name!r}, "
                "the name of its file (COR-013 point 8)",
                f"Fix: write `name: {agent_name}`, or rename the file to the name it gives.",
            ],
            access,
        )

    def _placeholder_cats(items: object) -> list[str]:
        cats: list[str] = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and item.startswith("<") and item.endswith(">"):
                    cats.append(item[1:-1])
        return cats

    # The categories this agent references through a *hard* channel — any list
    # key or `reads.paths` / `reads.records`. Computed once, before expanding,
    # so the optional-read branch can tell a genuinely-optional category from one
    # that is also hard-referenced elsewhere (in which case the hard reference
    # wins and an undefined value still fails the deploy). Per ADR-052 Decision 2.
    # Kept in front-matter order, so a skip names the undefined ones as written.
    hard_order: list[str] = []
    for key in RESOLVABLE_LIST_KEYS:
        hard_order += _placeholder_cats(fm_data.get(key))
    reads_fm = fm_data.get("reads")
    if isinstance(reads_fm, dict):
        for k in HARD_READS_KEYS:
            hard_order += _placeholder_cats(reads_fm.get(k))
    hard_order = list(dict.fromkeys(hard_order))
    hard_cats: set[str] = set(hard_order)

    ownership_cache: list = []

    def ownership():
        """The lifecycle layer's ownership module, loaded on the first placeholder.

        Lazy so an agent with no placeholders at all needs nothing from the
        lifecycle tree; from the first placeholder onwards the module is required,
        because it is what says whether that category is write-carrying.
        """
        if not ownership_cache:
            try:
                ownership_cache.append(load_ownership())
            except Exception as exc:
                raise CannotTell(
                    f"{agent_name}: cannot load .pkit/lifecycle/ownership.py "
                    f"({exc}) — overlay categories cannot be validated.\n"
                    f"Fix: run `pkit sync` to propagate the lifecycle layer."
                ) from None
        return ownership_cache[0]

    def warn(message: str):
        # The `warning:` prefix is the contract with `deploy-agents.sh`, which
        # surfaces only prefixed stderr lines from a resolver run that succeeded.
        print(f"{WARNING_PREFIX}{message}", file=sys.stderr)

    def fail(reason_lines: list[str]):
        raise Refusal([f"{agent_name}: {reason_lines[0]}", *reason_lines[1:]], access)

    def expand_list(items: list, *, optional: bool = False):
        out: list = []
        for item in items:
            if isinstance(item, str) and item.startswith("<") and item.endswith(">"):
                cat = item[1:-1]
                own = ownership()
                resolved = resolve_category(cat)
                if resolved is None:
                    # An *optional read* (a `reads.patterns` category not also
                    # hard-referenced elsewhere) tolerates absence: drop the item
                    # and let the agent deploy — the empty-is-normal read channel
                    # (ADR-052 Decision 3). Any hard reference still fails loudly.
                    if optional and cat not in hard_cats:
                        # A *bare* optional key still deploys (an optional read
                        # never blocks), but it is reported: the adopter started
                        # to configure the category and left it empty, so dropping
                        # it silently would hide the half-finished edit.
                        if is_bare(cat):
                            warn(
                                f"optional category <{cat}> is set with no value in "
                                f"{overlay_file} — deployed without it. Set its paths, "
                                f"or comment the key out."
                            )
                        continue
                    # Undefined (absent key) or bare (`cat:` with no value) —
                    # both unresolvable, both skip the agent. The skip names
                    # every hard category left undefined, since `adopt` serves
                    # the agent only when each has a conventional folder. The
                    # shared module answers that per category (ADR-051
                    # Implications, #2469): the first one with remediation of
                    # its own gives it, else the deploy's generic `adopt` advice
                    # applies.
                    undefined = [c for c in hard_order if resolve_category(c) is None]
                    if len(undefined) > 1:
                        named = ", ".join(f"<{c}>" for c in undefined)
                        reason = f"categories {named} referenced but not defined"
                    else:
                        reason = f"category <{cat}> referenced but not defined"
                    remediation = next(
                        (
                            lines
                            for c in undefined
                            if (lines := own.undefined_category_remediation(c))
                        ),
                        [],
                    )
                    fail([f"{reason} in overlay ({overlay_file})", *remediation])
                values = resolved if isinstance(resolved, list) else [resolved]
                offences = own.sync_managed_offences(
                    TARGET_ROOT, cat, [str(v) for v in values if v is not None]
                )
                if offences:
                    fail(own.rejection_message(cat, offences))
                out.extend(values)
            else:
                out.append(item)
        return out

    for key in RESOLVABLE_LIST_KEYS:
        if key in fm_data and isinstance(fm_data[key], list):
            fm_data[key] = expand_list(fm_data[key])
    if "reads" in fm_data and isinstance(fm_data["reads"], dict):
        for k in HARD_READS_KEYS:
            if k in fm_data["reads"] and isinstance(fm_data["reads"][k], list):
                fm_data["reads"][k] = expand_list(fm_data["reads"][k], optional=False)
        for k in OPTIONAL_READS_KEYS:
            if k in fm_data["reads"] and isinstance(fm_data["reads"][k], list):
                fm_data["reads"][k] = expand_list(fm_data["reads"][k], optional=True)

    carry_policy(fm_data, policy_overrides, f"overrides.{agent_name}", warn)
    keys = {key: key for key in reader.KEYS} if methodology_keys else declaration.keys
    write_tool_access(fm_data, access, keys, reader.KEYS)
    body = rebase_sibling_storyboards(fm_data, body, Path(source_file))
    body = end_with_workspace_note(body)

    out = io.StringIO()
    yaml.dump(fm_data, out)
    marked = ""
    if mark is not None:
        marked = "".join(
            f"{line}\n"
            for line in (
                MARKER,
                f"{MARK_DEFINITION}{mark}",
                f"{MARK_DIGEST}{picker().digest(Path(source_file))}",
                f"{MARK_TOOL_ACCESS}{tool_access_line(access)}",
            )
        )
    return f"---\n{marked}{out.getvalue()}---\n{body}"


def picker() -> ModuleType:
    """The agents area's picker in this tree, or `CannotTell` naming why it cannot be
    loaded."""
    try:
        module = load_module(PICKER, "pkit_agents_definition_source")
    except Exception as exc:
        raise CannotTell(
            f"cannot tell which definition of an agent is the agent: no picker at "
            f".pkit/agents/definition_source.py this resolver can load ({exc}).\n"
            "Fix: run `pkit sync`, which copies the picker and this resolver together."
        ) from None
    if not callable(getattr(module, "pick", None)) or not callable(getattr(module, "digest", None)):
        raise CannotTell(
            "the picker at .pkit/agents/definition_source.py has no `pick` or `digest`, "
            "which this resolver calls.\nFix: run `pkit sync`."
        )
    return module


def the_answer():
    """The picker's answer for this tree, or `CannotTell` naming why there is none."""
    module = picker()
    try:
        return module.pick(TARGET_ROOT)
    except module.RecordsUnreachable as exc:
        raise CannotTell(
            f"cannot tell which definition of an agent is the agent: {exc}.\n"
            "Fix: run `pkit sync`, which copies the lifecycle's reader with the picker."
        ) from None


def _field(text: str) -> str:
    """*text* as one tab-separated field: no tab or line break inside it."""
    return " ".join(text.split()) or "-"


def plan() -> int:
    """Write the deploy's plan: a tab-separated line for each name some place ships.

    - `agent`, the name, its place, its canonical file and how many places ship it:
      the definition the deploy resolves.
    - `refused`, the name, its place, why, and how many places ship it: an agent whose
      place holds both layouts, which the deploy does not resolve.
    - `none`, the name and why: no definition of it counts.
    - `untold`, the name and why: the records that decide it cannot be read.
    """
    try:
        answer = the_answer()
    except CannotTell as exc:
        print(str(exc), file=sys.stderr)
        return CANNOT_TELL
    for name, decided in answer.picks.items():
        shipped = str(len(decided.definitions))
        if decided.untold is not None:
            fields = ["untold", name, decided.untold]
        elif decided.agent is None:
            fields = ["none", name, decided.none or "no definition of it counts"]
        elif decided.refused is not None:
            fields = ["refused", name, decided.agent.place, decided.refused, shipped]
        else:
            fields = ["agent", name, decided.agent.place, str(decided.file), shipped]
        print("\t".join(_field(field) for field in fields))
    return 0


def pick_answer(name: str) -> dict:
    """The runner's answer for the agent *name*, as one JSON document's fields.

    `shipped` is False where no place ships the name. Otherwise it holds `agent`,
    the file of the definition the runner resolves, and its `place`, or one of
    `refused`, `none` and `untold`, saying why there is none to run.
    """
    try:
        answer = the_answer()
    except CannotTell as exc:
        return {"name": name, "shipped": True, "untold": str(exc).splitlines()[0]}
    decided = answer.picks.get(name)
    if decided is None:
        return {"name": name, "shipped": False}
    if decided.untold is not None:
        return {"name": name, "shipped": True, "untold": decided.untold}
    if decided.agent is None:
        return {"name": name, "shipped": True, "none": decided.none}
    if decided.refused is not None:
        return {"name": name, "shipped": True, "refused": decided.refused}
    return {
        "name": name,
        "shipped": True,
        "agent": str(decided.file),
        "place": decided.agent.place,
    }


def _option(args: list[str], flag: str) -> str | None:
    """The value after *flag* in *args*, both removed; None where *flag* is absent."""
    if flag not in args:
        return None
    index = args.index(flag)
    if index + 1 >= len(args):
        raise ValueError(f"{flag} takes a value")
    value = args[index + 1]
    del args[index : index + 2]
    return value


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args == [PLAN_FLAG]:
        return plan()
    if len(args) == 2 and args[0] == PICK_FLAG:
        print(json.dumps(pick_answer(args[1])))
        return 0
    methodology_keys = METHODOLOGY_KEYS_FLAG in args
    if methodology_keys:
        args.remove(METHODOLOGY_KEYS_FLAG)
    try:
        mark = _option(args, MARK_FLAG)
        earlier = _option(args, EARLIER_FLAG)
    except ValueError:
        args = []
        mark = earlier = None
    if len(args) != 3:
        print(
            "usage: _resolve_agent.py <source_file> <agent_name> <overlay_file> "
            f"[{METHODOLOGY_KEYS_FLAG}] [{MARK_FLAG} <place>] [{EARLIER_FLAG} <copy>]\n"
            f"       _resolve_agent.py {PLAN_FLAG}\n"
            f"       _resolve_agent.py {PICK_FLAG} <agent_name>",
            file=sys.stderr,
        )
        return 2

    source_file, agent_name, overlay_file = args
    try:
        text = resolve(
            source_file,
            agent_name,
            overlay_file,
            methodology_keys=methodology_keys,
            mark=mark,
        )
    except ToolAccessRefused as exc:
        print(str(exc), file=sys.stderr)
        return TOOL_ACCESS_REFUSED
    except CannotTell as exc:
        print(str(exc), file=sys.stderr)
        return CANNOT_TELL
    except Refusal as refusal:
        print("\n".join(refusal.lines), file=sys.stderr)
        if earlier is not None and refusal.access is not None and keeps(earlier, refusal.access):
            return KEEP_EARLIER
        return REFUSED
    sys.stdout.write(text)
    return 0


def keeps(earlier: str, access) -> bool:
    """Whether the copy at *earlier*, written from the agent's definition before, may
    stay while its current text is refused for a cause other than its tool access:
    only where the tool access its mark records gives nothing *access* does not
    (COR-013 point 8, ADR-087 point 4). A copy whose mark records none is not kept."""
    try:
        reader = load_module(TOOL_ACCESS_READER, "pkit_agents_tool_access")
    except Exception:
        return False
    recorded = recorded_tool_access(Path(earlier), reader)
    if recorded is None or not callable(getattr(reader, "gives_nothing_more", None)):
        return False
    return reader.gives_nothing_more(recorded, access)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
