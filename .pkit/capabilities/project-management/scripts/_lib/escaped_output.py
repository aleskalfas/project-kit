"""A command's output, with what came from outside it escaped (DEC-067 point 7).

A head reaches a person through words as well as through programs. A problem the
change check states, a path, a title or a grant's words can hold a control
character, and such a character can move the cursor, erase a line or reorder what
follows. So each command [project-management:DEC-067-heads-that-start-programs]
names, and the documentation check, prints through `escaping`: every line it writes
to standard output or standard error passes through `friction_answers.shown`, as the
change check's human-readable report does, so no print of such a text can be missed.
`move-issue` and `close-issue` do too. `review-work` and `done-work` run them as
children, which write to the terminal past their parent's streams.

- A line end stays a line end, so a finding printed whole keeps its lines. A carriage
  return alone moves the cursor, so it is escaped, and one before a newline is kept,
  since the host stores a description written in a browser that way.
- The commands write no control character of their own, so what they say reads the
  same.
- Machine-readable output keeps its bytes. `json.dumps` writes each such character
  as an escape of its own, so its text has nothing to escape here.
- `input` writes its prompt through the stream, since the stream names no file
  descriptor for it to take the prompt past.
- An exception no command caught can quote such a text too, and Python reports it only
  after the streams are restored, so `_report` takes that report over.
"""

from __future__ import annotations

import functools
import io
import re
import sys
import traceback
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from types import TracebackType
from typing import Any, ParamSpec, TextIO, TypeVar

from _lib.friction_answers import shown

_P = ParamSpec("_P")
_R = TypeVar("_R")

#: A line's end, kept when a text is split on it.
_LINE_END = re.compile(r"(\r?\n)")


def lines(text: str) -> str:
    """`text` line by line, as `friction_answers.shown` writes each line, its line
    ends kept."""
    if text.isprintable():
        return text
    parts = _LINE_END.split(text)
    # `split` with one group gives each line at an even place, each line end at an odd.
    return "".join(part if place % 2 else shown(part) for place, part in enumerate(parts))


class _Escaping:
    """A text stream that escapes what is written to it (`lines`), and otherwise
    answers as the stream it wraps."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write(self, text: str) -> int:
        self._stream.write(lines(text))
        return len(text)

    def writelines(self, texts: Iterable[str]) -> None:
        for text in texts:
            self.write(text)

    def fileno(self) -> int:
        """Names no descriptor, so that `input` writes its prompt to this stream."""
        raise io.UnsupportedOperation("fileno")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


@contextmanager
def _escaped() -> Iterator[None]:
    """While inside, each write to standard output and standard error is escaped."""
    before = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _Escaping(sys.stdout), _Escaping(sys.stderr)  # type: ignore[assignment]
    try:
        yield
    finally:
        sys.stdout, sys.stderr = before


def _report(kind: type[BaseException], value: BaseException, trace: TracebackType | None) -> None:
    """Python's report of an exception that left a command, escaped."""
    sys.stderr.write(lines("".join(traceback.format_exception(kind, value, trace))))


def escaping(main: Callable[_P, _R]) -> Callable[_P, _R]:
    """`main`, with all it prints escaped: how a command's entry point is wrapped."""

    @functools.wraps(main)
    def run(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with _escaped():
            try:
                return main(*args, **kwargs)
            except Exception:
                sys.excepthook = _report
                raise

    return run
