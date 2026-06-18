"""plugins/recording/directives.py — recording plugin for storyboard directives.

Registers fence language tags: boot, panes, narrate, chat, shell, wait.

Directive vocabulary
--------------------

``boot``
    Pre-tmux startup.  Narrates into the bare recording shell (the only
    surface before panes exist), then wipes the line and runs the command.
    Content is a simple YAML-like block with two keys::

        narration: |
          One or more lines of narration text.
        command: ./run.sh restart ai

``panes``
    Binds logical role names to tmux pane numbers.  State-mutating: the
    context's pane map is updated and persists for subsequent directives.
    Content is a YAML-like map of ``<role>: <int>``::

        shell:   1
        chat:    2
        narrate: 3

``narrate``
    Types the fence body into the pane bound to the ``narrate`` role.

``chat``
    Types the fence body into the pane bound to the ``chat`` role.

``shell``
    Types the fence body into the pane bound to the ``shell`` role and
    presses Enter (runs the command).

``wait``
    Pure operator-coordination pause.  Content is the message shown to the
    operator in CONTROL.

``sleep``
    Pause for a fixed number of seconds.  Body is the duration (integer
    seconds), e.g.::

        20

    Differs from ``wait`` (operator-driven Enter) and ``ready`` (poll for
    a text pattern): ``sleep`` just waits the wall-clock time and advances.

``keys``
    Send modifier-key chords to the currently focused window/pane via
    osascript.  One chord per line.  Modifier syntax: ``modifier+key``,
    multiple modifiers chain with ``+`` (e.g. ``ctrl+shift+a``).  Bare
    key names (``Enter``, ``Escape``) emit the corresponding key code;
    everything else goes through System Events ``keystroke``::

        ctrl+b
        k

    Uses: send tmux prefix chords (``ctrl+b`` then a binding letter),
    submit Enter without typing text, etc.  Pure keystroke injection —
    does NOT bind to a ``panes`` role.

``ready``
    Poll the RECORDING iTerm session's visible text and advance once a
    given pattern appears.  Used to wait for a long-running command (a
    container start, tmux attach, etc.) to finish before the next step
    fires.  Two forms::

        # Plain-text form (terse):
        HUMAN

        # Structured form (when you need to set timeout):
        pattern: HUMAN
        timeout: 60          # seconds; default 30

    Default timeout is 30 seconds.  On timeout the storyboard halts with
    an error.

Execution boundary
------------------

The plugin's ``actions()`` method emits a list of (action_name, arg, ...)
tuples.  The bash runner dispatches each to the corresponding lib.sh
function.  Python never executes shell commands directly.

Pane selection
--------------

Before typing into any ``narrate`` / ``chat`` / ``shell`` target, the plugin
emits a ``select_pane <N>`` action.  lib.sh's ``select_tmux_pane`` sends
``C-b q <N>`` via osascript to bring the correct pane into focus inside the
iTerm tmux session, so the operator no longer needs to click the right pane
manually.

``panes`` blocks are state-mutating: the context dict carries a ``"panes"``
key that maps role names to tmux pane numbers.  If a directive fires before
any ``panes`` block, pane selection is skipped and a warning is emitted.
"""

from __future__ import annotations

import re
import sys
from typing import Any

from storyboards.plugin import Plugin


# ---------------------------------------------------------------------------
# Minimal YAML-like parser (stdlib only, no PyYAML)
# ---------------------------------------------------------------------------
# The panes block is a flat map: <key>: <int>
# The boot block has a scalar key `command:` and a multiline key `narration:`
# (using YAML block scalar `|`).  We handle just these shapes.


def _parse_simple_map(content: str) -> tuple[dict[str, str], list[str]]:
    """Parse a simple YAML-like flat map of ``key: value`` pairs.

    Returns (mapping, errors).  Values are stripped strings.
    """
    result: dict[str, str] = {}
    errors: list[str] = []
    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
        if not m:
            errors.append(f"line {lineno}: cannot parse key-value pair: {raw_line!r}")
            continue
        key, value = m.group(1), m.group(2).strip()
        result[key] = value
    return result, errors


def _parse_panes_block(content: str) -> tuple[dict[str, int], list[str]]:
    """Parse a ``panes`` fence content into a ``role -> pane_number`` map.

    Expects lines of the form ``<role>: <integer>``.
    """
    raw, parse_errors = _parse_simple_map(content)
    result: dict[str, int] = {}
    errors = list(parse_errors)
    for key, val in raw.items():
        try:
            result[key] = int(val)
        except ValueError:
            errors.append(
                f"panes: value for {key!r} must be an integer, got {val!r}"
            )
    return result, errors


def _parse_sleep_block(content: str) -> tuple[int, list[str]]:
    """Parse a ``sleep`` directive's content into a duration in seconds.

    Body is a single integer (seconds).  Blank lines and # comments are
    ignored.  Returns ``(seconds, errors)``.  On parse failure ``seconds``
    is 0 and an error is reported.
    """
    errors: list[str] = []
    stripped = "\n".join(
        line for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ).strip()
    if not stripped:
        return 0, ["sleep: body must be a positive integer (seconds)"]
    try:
        seconds = int(stripped)
    except ValueError:
        return 0, [f"sleep: body must be a positive integer (seconds), got {stripped!r}"]
    if seconds <= 0:
        errors.append(f"sleep: seconds must be > 0, got {seconds}")
    return seconds, errors


def _parse_keys_block(content: str) -> tuple[list[str], list[str]]:
    """Parse a ``keys`` directive's content into a list of chord specs.

    Each non-empty, non-comment line is one chord.  Spec format:
    ``[mod1+[mod2+...]]key``, e.g. ``ctrl+b``, ``cmd+shift+t``,
    ``Enter``, ``Escape``.
    """
    chords: list[str] = []
    errors: list[str] = []
    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        chords.append(line)
    if not chords:
        errors.append("keys: at least one keystroke line is required")
    return chords, errors


def _parse_ready_block(content: str) -> tuple[dict[str, str], list[str]]:
    """Parse a ``ready`` directive's content.

    Two forms:
      - Plain text: the entire stripped content is the pattern; timeout
        defaults to 30 seconds.
      - Structured: a key-value map with at least ``pattern:`` and optionally
        ``timeout:`` (seconds, integer).

    Detection: if the first non-empty line looks like ``<key>:``, parse as
    structured; otherwise treat the body as the literal pattern.
    """
    stripped = content.strip()
    if not stripped:
        return {}, ["ready: directive body is empty"]
    first_line = stripped.splitlines()[0].strip()
    if re.match(r"^[\w-]+\s*:", first_line):
        parsed, errors = _parse_simple_map(content)
        parsed.setdefault("timeout", "30")
        return parsed, errors
    return {"pattern": stripped, "timeout": "30"}, []


def _parse_boot_block(content: str) -> tuple[dict[str, str], list[str]]:
    """Parse a ``boot`` fence content.

    Handles two forms for ``narration``::

        # Block scalar (YAML |)
        narration: |
          Line one.
          Line two.
        command: ./run.sh restart ai

        # Single-line
        narration: Now we'll run AI mode.
        command: ./run.sh restart ai
    """
    lines = content.splitlines()
    errors: list[str] = []
    result: dict[str, str] = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        m = re.match(r"^([\w-]+)\s*:\s*(.*)$", stripped)
        if not m:
            errors.append(f"boot: cannot parse line {i + 1}: {line!r}")
            i += 1
            continue

        key, rest = m.group(1), m.group(2).strip()

        if rest == "|":
            # Block scalar — collect indented lines that follow.
            block_lines: list[str] = []
            i += 1
            # Determine the indentation from the first non-empty line.
            base_indent: int | None = None
            while i < len(lines):
                inner = lines[i]
                if inner.strip() == "":
                    # Blank lines inside a block scalar are kept.
                    block_lines.append("")
                    i += 1
                    continue
                # Count leading spaces.
                indent = len(inner) - len(inner.lstrip())
                if base_indent is None:
                    base_indent = indent
                if indent < (base_indent or 0):
                    # De-dented: back to a new key.
                    break
                block_lines.append(inner[base_indent:] if base_indent else inner)
                i += 1
            result[key] = "\n".join(block_lines).strip()
        else:
            result[key] = rest
            i += 1

    return result, errors


# ---------------------------------------------------------------------------
# The plugin
# ---------------------------------------------------------------------------


class RecordingPlugin(Plugin):
    """Recording plugin — handles boot/panes/narrate/chat/shell/wait."""

    @property
    def name(self) -> str:
        return "recording"

    @property
    def fence_languages(self) -> list[str]:
        return ["boot", "panes", "narrate", "chat", "shell", "wait", "ready", "keys", "sleep"]

    # --- validate ------------------------------------------------------------

    def validate(self, lang: str, content: str) -> list[str]:
        dispatch = {
            "boot": self._validate_boot,
            "panes": self._validate_panes,
            "narrate": self._validate_text,
            "chat": self._validate_text,
            "shell": self._validate_text,
            "wait": self._validate_text,
            "ready": self._validate_ready,
            "keys": self._validate_keys,
            "sleep": self._validate_sleep,
        }
        fn = dispatch.get(lang)
        if fn is None:
            return [f"unknown lang {lang!r} (internal error)"]
        return fn(content)

    def _validate_boot(self, content: str) -> list[str]:
        parsed, errors = _parse_boot_block(content)
        if "narration" not in parsed:
            errors.append("boot: missing required key 'narration:'")
        elif not parsed["narration"].strip():
            errors.append("boot: 'narration' is empty")
        if "command" not in parsed:
            errors.append("boot: missing required key 'command:'")
        elif not parsed["command"].strip():
            errors.append("boot: 'command' is empty")
        return errors

    def _validate_panes(self, content: str) -> list[str]:
        _, errors = _parse_panes_block(content)
        if not errors:
            parsed, _ = _parse_panes_block(content)
            if not parsed:
                errors.append("panes: block is empty — need at least one role binding")
        return errors

    def _validate_text(self, content: str) -> list[str]:
        if not content.strip():
            return ["directive body is empty — add some text"]
        return []

    def _validate_keys(self, content: str) -> list[str]:
        _, errors = _parse_keys_block(content)
        return errors

    def _validate_sleep(self, content: str) -> list[str]:
        _, errors = _parse_sleep_block(content)
        return errors

    def _validate_ready(self, content: str) -> list[str]:
        parsed, errors = _parse_ready_block(content)
        if "pattern" not in parsed or not parsed.get("pattern", "").strip():
            errors.append("ready: missing or empty 'pattern' (terse form: just put the text on its own line)")
        timeout = parsed.get("timeout", "30")
        try:
            t = int(timeout)
            if t <= 0:
                errors.append(f"ready: timeout must be positive, got {t}")
        except ValueError:
            errors.append(f"ready: timeout must be an integer, got {timeout!r}")
        return errors

    # --- describe ------------------------------------------------------------

    def describe(self, lang: str, content: str) -> str:
        dispatch = {
            "boot": self._describe_boot,
            "panes": self._describe_panes,
            "narrate": self._describe_text,
            "chat": self._describe_text,
            "shell": self._describe_text,
            "wait": self._describe_text,
            "ready": self._describe_ready,
            "keys": self._describe_keys,
            "sleep": self._describe_sleep,
        }
        fn = dispatch.get(lang)
        if fn is None:
            return f"(unknown lang {lang!r})"
        return fn(lang, content)

    def _describe_boot(self, _lang: str, content: str) -> str:
        parsed, _ = _parse_boot_block(content)
        narration = parsed.get("narration", "").replace("\n", " ")
        if len(narration) > 60:
            narration = narration[:57] + "..."
        command = parsed.get("command", "")
        if len(command) > 40:
            command = command[:37] + "..."
        return f"narrate: {narration!r}  command: {command!r}"

    def _describe_panes(self, _lang: str, content: str) -> str:
        parsed, _ = _parse_panes_block(content)
        if not parsed:
            return "(empty)"
        parts = [f"{role}={num}" for role, num in sorted(parsed.items())]
        return "  ".join(parts)

    def _describe_text(self, lang: str, content: str) -> str:
        text = content.strip().replace("\n", " ")
        if len(text) > 80:
            text = text[:77] + "..."
        return f"{text!r}"

    def _describe_keys(self, _lang: str, content: str) -> str:
        chords, _ = _parse_keys_block(content)
        if not chords:
            return "(empty)"
        return " then ".join(chords)

    def _describe_sleep(self, _lang: str, content: str) -> str:
        seconds, _ = _parse_sleep_block(content)
        return f"pause {seconds}s"

    def _describe_ready(self, _lang: str, content: str) -> str:
        parsed, _ = _parse_ready_block(content)
        pattern = parsed.get("pattern", "")
        timeout = parsed.get("timeout", "30")
        if len(pattern) > 40:
            pattern = pattern[:37] + "..."
        return f"poll for {pattern!r} (timeout {timeout}s)"

    # --- actions -------------------------------------------------------------

    def actions(
        self,
        lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        dispatch = {
            "boot": self._actions_boot,
            "panes": self._actions_panes,
            "narrate": self._actions_typed,
            "chat": self._actions_typed,
            "shell": self._actions_typed,
            "wait": self._actions_wait,
            "ready": self._actions_ready,
            "keys": self._actions_keys,
            "sleep": self._actions_sleep,
        }
        fn = dispatch.get(lang)
        if fn is None:
            return []
        return fn(lang, content, context)

    def _actions_boot(
        self,
        _lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """boot: narrate-wipe-run into the bare recording shell.

        No focus prompt: the recording shell is the only surface when
        this runs (tmux isn't up yet), so the keystrokes land there
        automatically once the RECORDING window is the front iTerm
        window — which it is, because _session.sh activated it.
        """
        parsed, _ = _parse_boot_block(content)
        narration = parsed.get("narration", "").strip().replace("\n", " ")
        command = parsed.get("command", "").strip()
        return [
            ("narrate_wipe_run", narration, command),
        ]

    def _actions_panes(
        self,
        _lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """panes: update context — no bash action emitted (pure state update)."""
        parsed, _ = _parse_panes_block(content)
        if "panes" not in context:
            context["panes"] = {}
        context["panes"].update(parsed)
        # No bash actions — this is purely a state mutation.
        return []

    def _actions_typed(
        self,
        lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """narrate / chat / shell: select pane then type."""
        text = content.strip()
        pane_map: dict[str, int] = context.get("panes", {})

        pane_num = pane_map.get(lang)
        acts: list[tuple[str, ...]] = []

        if pane_num is None:
            # No pane bound for this role — warn and type without pane select.
            print(
                f"recording-plugin: warning: no pane bound for role {lang!r} "
                f"(add a 'panes' block before this directive)",
                file=sys.stderr,
            )
        else:
            acts.append(("select_pane", str(pane_num)))

        if lang in ("narrate", "chat"):
            acts.append(("narrate", text))
        else:  # shell
            acts.append(("shell_run", text))

        return acts

    def _actions_wait(
        self,
        _lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        return [("wait_only", content.strip())]

    def _actions_ready(
        self,
        _lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """ready: poll the RECORDING iTerm session text for a pattern."""
        parsed, _ = _parse_ready_block(content)
        pattern = parsed.get("pattern", "").strip()
        timeout = parsed.get("timeout", "30")
        return [("ready_wait", pattern, timeout)]

    def _actions_keys(
        self,
        _lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """keys: send one or more modifier-key chords via osascript."""
        chords, _ = _parse_keys_block(content)
        return [("send_key", chord) for chord in chords]

    def _actions_sleep(
        self,
        _lang: str,
        content: str,
        context: dict[str, Any],
    ) -> list[tuple[str, ...]]:
        """sleep: pause for N seconds, then advance."""
        seconds, _ = _parse_sleep_block(content)
        return [("sleep_pause", str(seconds))]
