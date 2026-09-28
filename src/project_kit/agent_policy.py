"""Per-agent model and effort — an agent's execution policy (#1047).

An agent's front matter may declare the model it runs on (`model:`) and the
effort it reasons at (`effort:`); the adopter may override either per agent in
the overlay (`overrides.<agent>.model` / `.effort`). Both keys are optional and
default to **inherit**: nothing is carried into the deployed definition, and
the harness applies its own default — a dispatched agent runs on its caller's
model and effort, a headless one on the operator's settings. An adopter who
sets nothing sees no change.

This module is the backbone's one home for that policy: the vocabulary the
values are checked against, and the precedence that yields an agent's
*effective* setting — the overlay override, else the front matter, else
inherit. `pkit agents` reports the effective settings, `pkit validate` (the
`refs` member) reports a value outside the vocabulary.

The vocabulary is the harness's: the claude-code adapter's `_resolve_agent.py`
carries the same constants and applies the same precedence when it writes the
deployed file, and a parity test pins the two by name. A value outside the
vocabulary is never written — the deploy drops it and the agent inherits — so
a typo degrades to today's behaviour rather than to a definition the harness
refuses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MODEL = "model"
EFFORT = "effort"

# The front-matter keys this module governs, in the order they are reported.
# Reserved inside an overlay's `overrides.<agent>` block: there they set the
# agent's policy rather than name an overlay category.
POLICY_KEYS: tuple[str, ...] = (MODEL, EFFORT)

# The value that carries nothing: the harness default applies.
INHERIT = "inherit"

# The harness's model aliases (Claude Code's own list), each resolving to the
# latest model of its family. A full model name is accepted too — below.
MODEL_ALIASES: tuple[str, ...] = (
    "sonnet", "opus", "haiku", "fable", "best", "opusplan",
    "sonnet[1m]", "opus[1m]", "fable[1m]",
)

# A full model name: `claude-…`, optionally provider-qualified
# (`us.anthropic.claude-…`). The shape the harness documents for `--model`.
FULL_MODEL_NAME_PATTERN = r"^(?:[A-Za-z0-9-]+\.)*claude-\S+$"
_FULL_MODEL_NAME_RE = re.compile(FULL_MODEL_NAME_PATTERN)

# The harness's effort levels — the same list `review-pr --effort` accepts. (The
# harness also takes an integer; the vocabulary is the named levels.)
EFFORT_LEVELS: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max")

# Where an effective setting came from.
SOURCE_DEFAULT = "default"  # nothing declares a value: inherit
SOURCE_FRONT_MATTER = "front matter"
SOURCE_OVERLAY = "overlay"


def value_problem(key: str, value: Any) -> str | None:
    """Why *value* is not acceptable for policy *key*, or None when it is."""
    if key == MODEL:
        if isinstance(value, str) and (
            value == INHERIT or value in MODEL_ALIASES or _FULL_MODEL_NAME_RE.match(value)
        ):
            return None
        return (
            f"model {value!r} is not one the harness accepts — use `{INHERIT}`, an alias "
            f"({', '.join(MODEL_ALIASES)}) or a full model name (`claude-…`)"
        )
    if key == EFFORT:
        if isinstance(value, str) and (value == INHERIT or value in EFFORT_LEVELS):
            return None
        return (
            f"effort {value!r} is not a level the harness accepts — use `{INHERIT}` "
            f"or one of {', '.join(EFFORT_LEVELS)}"
        )
    raise ValueError(f"not a policy key: {key!r}")


@dataclass(frozen=True)
class Setting:
    """One policy key's effective value for one agent.

    ``value`` is what the deploy carries, or ``INHERIT`` when it carries
    nothing. ``written`` is the value as written at ``source`` (None when no
    one wrote one); ``problem`` says why it was refused, in which case the
    deploy drops it and ``value`` is ``INHERIT``.
    """

    key: str
    value: str
    source: str
    written: Any = None
    problem: str | None = None


def effective_setting(key: str, *, declared: Any = None, override: Any = None) -> Setting:
    """The effective setting of *key*: the overlay override, else the front
    matter, else inherit. A bare key (no value) counts as absent."""
    if override is not None:
        written, source = override, SOURCE_OVERLAY
    elif declared is not None:
        written, source = declared, SOURCE_FRONT_MATTER
    else:
        return Setting(key=key, value=INHERIT, source=SOURCE_DEFAULT)
    problem = value_problem(key, written)
    if problem is not None:
        return Setting(key=key, value=INHERIT, source=source, written=written, problem=problem)
    return Setting(key=key, value=written, source=source, written=written)


def effective_policy(
    front_matter: dict[str, Any], overrides: dict[str, Any]
) -> tuple[Setting, ...]:
    """Every policy key's effective setting, in ``POLICY_KEYS`` order.

    *front_matter* is the agent's parsed front matter; *overrides* its
    overlay policy block (the policy keys of ``overrides.<agent>``).
    """
    return tuple(
        effective_setting(key, declared=front_matter.get(key), override=overrides.get(key))
        for key in POLICY_KEYS
    )
