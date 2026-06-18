"""storyboards/plugin.py — Plugin ABC and PluginRegistry.

Architecture
------------

A Plugin declares which fence language tags it owns and provides three methods:

``validate(lang, content) -> list[str]``
    Plugin-specific content validation.  Returns a list of error strings
    (empty = valid).  Called during ``--validate`` mode against every fence
    with a matching language tag.

``describe(lang, content) -> str``
    Returns a short human-readable summary of this fence for ``--validate``
    output.  E.g. ``panes shell=1 chat=2 narrate=3``.

``actions(lang, content, context) -> list[tuple[str, ...]]``
    Returns a list of (action, arg1, arg2, ...) tuples that the bash runner
    will dispatch.  This is the execution boundary: Python emits a flat list
    of named bash actions; the runner (run-storyboard.sh) dispatches each to
    the corresponding lib.sh function.

    ``context`` is a mutable dict shared across the entire storyboard run.
    Plugins may read and write to it (e.g. the ``panes`` directive writes the
    current role→pane-number map; subsequent directives read it to know which
    tmux pane to target).

Why ``actions`` instead of ``execute``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python owns parsing and validation; Bash owns execution.  A plugin that
emits Python-side side effects (subprocess calls, file writes) would cross
that boundary.  Instead, plugins describe *what to do* as a list of named
actions.  The bash runner dispatches each action to the corresponding lib.sh
primitive.  This keeps the execution model testable in Python (you can inspect
the action list without running anything) and keeps the macOS-specific
keystroke machinery entirely in bash.

PluginRegistry
--------------

Call ``registry.register(plugin)`` to add a plugin.  The registry dispatches
by ``lang``; multiple plugins may register different languages but a single
language tag may only be claimed by one plugin (the second registration wins
with a warning).

Unknown fence languages are reported as warnings during validate/dispatch, not
fatal errors — this lets storyboards be read without all plugins present.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Any


class Plugin(ABC):
    """Abstract base class for a storyboard execution plugin."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, e.g. ``"recording"``."""

    @property
    @abstractmethod
    def fence_languages(self) -> list[str]:
        """List of fence language tags this plugin handles."""

    @abstractmethod
    def validate(self, lang: str, content: str) -> list[str]:
        """Return a list of error strings for invalid fence content.

        An empty list means the fence is valid.  Each error should be a
        plain-English sentence; the caller will prefix it with step/line info.
        """

    @abstractmethod
    def describe(self, lang: str, content: str) -> str:
        """Return a one-line human summary of this fence (for --validate output).

        Example: ``'shell=1 chat=2 narrate=3'``
        """

    @abstractmethod
    def actions(
        self,
        lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """Return a list of (action_name, arg, ...) tuples for the bash runner.

        The runner dispatches each tuple to the lib.sh function named by
        action_name.  Positional args beyond the name are passed directly.
        """


class PluginRegistry:
    """Holds plugins and dispatches by fence language tag."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}  # lang -> plugin

    def register(self, plugin: Plugin) -> None:
        """Register a plugin.  Re-registration of an existing lang warns."""
        for lang in plugin.fence_languages:
            if lang in self._plugins:
                existing = self._plugins[lang]
                print(
                    f"plugin-registry: warning: language {lang!r} already "
                    f"registered by '{existing.name}'; overriding with "
                    f"'{plugin.name}'",
                    file=sys.stderr,
                )
            self._plugins[lang] = plugin

    def get(self, lang: str) -> Plugin | None:
        """Return the plugin for lang, or None if unknown."""
        return self._plugins.get(lang)

    def known_languages(self) -> list[str]:
        """Return all registered language tags (sorted)."""
        return sorted(self._plugins.keys())

    def validate_fence(
        self, lang: str, content: str, step_num: int, fence_line: int
    ) -> list[str]:
        """Validate one fence; return list of error strings (with context prefix)."""
        plugin = self.get(lang)
        if plugin is None:
            return [
                f"step {step_num} line {fence_line}: unrecognised directive "
                f"{lang!r} — is the providing plugin loaded?"
            ]
        raw_errors = plugin.validate(lang, content)
        prefix = f"step {step_num} line {fence_line} [{plugin.name}/{lang}]"
        return [f"{prefix}: {e}" for e in raw_errors]

    def describe_fence(
        self,
        lang: str,
        content: str,
        step_num: int,
        fence_line: int,
    ) -> str:
        """Return a formatted description line for --validate output."""
        plugin = self.get(lang)
        if plugin is None:
            return (
                f"  [UNKNOWN {lang!r}] line {fence_line}: "
                f"unrecognised directive — is the providing plugin loaded?"
            )
        desc = plugin.describe(lang, content)
        return f"  [{plugin.name}/{lang}] {desc}"

    def actions_for_fence(
        self,
        lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """Return bash action tuples for one fence.

        Unknown languages emit a single 'warn_unknown_directive' action
        (the bash runner prints a warning but continues).
        """
        plugin = self.get(lang)
        if plugin is None:
            return [("warn_unknown_directive", lang)]
        return plugin.actions(lang, content, context)
