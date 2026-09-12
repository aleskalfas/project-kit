#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml"]
# ///
"""Resolve overlay placeholders in an agent file's frontmatter, write to stdout.

Invoked by `deploy-agents.sh` once per agent. Reads:

- arg 1: source agent file (`.pkit/agents/{core,project}/<name>/<name>.md`)
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
exits 0 so the agent deploys as a generalist.

This script *applies* that last check but does not *define* it. The
sync-managed predicate and the write-carrying category registry live
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
    import ownership  # noqa: PLC0415 — deliberately lazy; see above.

    return ownership


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

    def resolve(category: str):
        if category in agent_overrides:
            return agent_overrides[category]
        if category in defaults:
            return defaults[category]
        return None

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
                        continue
                    # Undefined (absent key) or bare (`cat:` with no value) —
                    # both unresolvable, both skip the agent. The remediation
                    # depends on whether the category has a conventional default,
                    # which the shared module answers (ADR-051 Implications).
                    fail([
                        f"category <{cat}> referenced but not defined in overlay "
                        f"({overlay_file})",
                        *(own.undefined_category_remediation(cat) or []),
                    ])
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

    out = io.StringIO()
    yaml.dump(fm_data, out)
    sys.stdout.write(f"---\n{out.getvalue()}---\n{body}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
