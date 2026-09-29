"""Front matter in a Markdown text: where it is, and its value.

A text has front matter when it opens with a `---` line closed by the next
`---` line — the rule the backbone's discovery reads artefacts by. Where
artefacts are is never read here: the stamp reads the templates and the
collection file it adds an entry to, and the check reads the heading of a
file discovery names and the revalidation records, which are not artefacts
and lie in no place.
"""

from __future__ import annotations

import datetime
import io
import re
from typing import Any

from ruamel.yaml import YAML

_FENCE = re.compile(r"^---[ \t]*$", re.MULTILINE)

#: A level-one heading, its closing hashes left out; and the opening of fenced code.
_H1 = re.compile(r"^#[ \t]+(?P<text>.*?)(?:[ \t]+#+)?[ \t]*$")
_CODE_FENCE = re.compile(r"^[ ]{0,3}(?P<fence>`{3,}|~{3,})")

_safe = YAML(typ="safe")


def front_matter_span(text: str) -> tuple[int, int] | None:
    """The start and end of the YAML between the fences, or `None` without front matter."""
    first = text.find("\n")
    if not text.startswith("---") or first == -1 or text[:first].rstrip() != "---":
        return None
    closing = _FENCE.search(text, first + 1)
    return None if closing is None else (first + 1, closing.start())


def split(text: str) -> tuple[str | None, str]:
    """(front-matter YAML, body); `(None, text)` without front matter. The body
    starts after the closing fence, leading blank lines left out."""
    span = front_matter_span(text)
    if span is None:
        return None, text
    start, end = span
    closing_end = text.find("\n", end)
    body = "" if closing_end == -1 else text[closing_end + 1 :]
    return text[start:end], body.lstrip("\n")


def heading(body: str) -> str | None:
    """The text of the body's first level-one heading, `# …`, outside fenced code;
    `None` without one."""
    fence: str | None = None
    for line in body.splitlines():
        opening = _CODE_FENCE.match(line)
        if fence is not None:
            if opening is not None and opening["fence"].startswith(fence):
                fence = None
            continue
        if opening is not None:
            fence = opening["fence"]
            continue
        found = _H1.match(line)
        if found is not None:
            return found["text"]
    return None


def load(yaml_text: str) -> Any:
    """The YAML's value, dates and times as the ISO text they were written as.
    Raises ruamel's YAMLError when it does not parse."""
    return _dated(_safe.load(io.StringIO(yaml_text)))


def _dated(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _dated(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_dated(item) for item in value]
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value
