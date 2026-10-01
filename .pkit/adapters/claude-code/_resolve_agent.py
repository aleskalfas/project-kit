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

import io
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML

# `<root>/.pkit/adapters/claude-code/_resolve_agent.py` → `<root>`.
TARGET_ROOT = Path(__file__).resolve().parents[3]

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

# Prefix of a stderr line that reports a problem without failing the resolve.
# `deploy-agents.sh` prints these lines for an agent that still deploys; any
# other stderr from a successful run (e.g. from `uv`) stays hidden.
WARNING_PREFIX = "warning: "


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


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: _resolve_agent.py <source_file> <agent_name> <overlay_file>",
            file=sys.stderr,
        )
        return 2

    source_file, agent_name, overlay_file = argv[1], argv[2], argv[3]

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

    def resolve(category: str):
        if category in agent_overrides:
            return agent_overrides[category]
        if category in defaults:
            return defaults[category]
        return None

    def is_bare(category: str) -> bool:
        """The key is present but carries no value (``cat:`` alone).

        ``resolve`` returns None for both a bare and an absent key; only a bare
        one is a half-finished edit by the adopter, worth telling them about.
        """
        return (category in agent_overrides or category in defaults) and resolve(category) is None

    content = Path(source_file).read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?\n)---\n(.*)$", content, re.DOTALL)
    if not match:
        print(f"{source_file}: agent file has no frontmatter", file=sys.stderr)
        return 1
    fm_yaml = match.group(1)
    body = match.group(2)

    fm_data = yaml.load(io.StringIO(fm_yaml)) or {}

    def _placeholder_cats(items: object) -> set[str]:
        cats: set[str] = set()
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and item.startswith("<") and item.endswith(">"):
                    cats.add(item[1:-1])
        return cats

    # The categories this agent references through a *hard* channel — any list
    # key or `reads.paths` / `reads.records`. Computed once, before expanding,
    # so the optional-read branch can tell a genuinely-optional category from one
    # that is also hard-referenced elsewhere (in which case the hard reference
    # wins and an undefined value still fails the deploy). Per ADR-052 Decision 2.
    hard_cats: set[str] = set()
    for key in RESOLVABLE_LIST_KEYS:
        hard_cats |= _placeholder_cats(fm_data.get(key))
    reads_fm = fm_data.get("reads")
    if isinstance(reads_fm, dict):
        for k in HARD_READS_KEYS:
            hard_cats |= _placeholder_cats(reads_fm.get(k))

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
                print(
                    f"{agent_name}: cannot load .pkit/lifecycle/ownership.py "
                    f"({exc}) — overlay categories cannot be validated.\n"
                    f"Fix: run `pkit sync` to propagate the lifecycle layer.",
                    file=sys.stderr,
                )
                sys.exit(1)
        return ownership_cache[0]

    def warn(message: str):
        # The `warning:` prefix is the contract with `deploy-agents.sh`, which
        # surfaces only prefixed stderr lines from a resolver run that succeeded.
        print(f"{WARNING_PREFIX}{message}", file=sys.stderr)

    def fail(reason_lines: list[str]):
        print("\n".join([f"{agent_name}: {reason_lines[0]}", *reason_lines[1:]]), file=sys.stderr)
        sys.exit(1)

    def expand_list(items: list, *, optional: bool = False):
        out: list = []
        for item in items:
            if isinstance(item, str) and item.startswith("<") and item.endswith(">"):
                cat = item[1:-1]
                own = ownership()
                resolved = resolve(cat)
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
                    # both unresolvable, both skip the agent. The remediation
                    # depends on whether the category has a conventional default,
                    # which the shared module answers (ADR-051 Implications).
                    fail(
                        [
                            f"category <{cat}> referenced but not defined in overlay "
                            f"({overlay_file})",
                            *(own.undefined_category_remediation(cat) or []),
                        ]
                    )
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
    body = rebase_sibling_storyboards(fm_data, body, Path(source_file))

    out = io.StringIO()
    yaml.dump(fm_data, out)
    sys.stdout.write(f"---\n{out.getvalue()}---\n{body}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
