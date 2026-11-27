"""The check of a paragraph that ends on a word kept off a line's end (visual-communication
DEC-075).

- **Which paragraphs** (point 1). Each paragraph of a text the scene holds that a line feed
  ends: every one of its paragraphs but the last, each its runs' texts joined, as the scene
  holds them and the engine breaks them.
- **Which words.** A paragraph ends on a *kept word* where its last word, with nothing after
  it but spaces, is one the rules of the scene's language keep off the end of a line the
  engine breaks. The check reads them from the engine's own rules
  (`text.LanguageRules.kept_at_end`), so the two never disagree.
- **The finding** (point 2) asks the piece's author for attention, in the content file of
  the scene's language, at the key path of the run whose text holds the word's first letter,
  naming the paragraph by its place in the text and the word. It carries the text's trace id
  as its place, so that whatever reads it finds the page it lies on, and names no trace in
  its message, so a field drawn on several pages is one finding.

It states no reach, since no reader's instructions read its silence (DEC-063 point 1), and
compares no scenes: each finding is one scene's.

Reads no file, and knows nothing of the check's run: the check gives it each scene and the
content file of the scene's language.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from _lib.findings import ATTENTION, AUTHOR, Finding
from _lib.layout import CONTENT
from _lib.scene_checks import SceneCheck
from _lib.text import rules_of

#: The call for attention on a paragraph that a line feed ends on a kept word (DEC-075
#: point 2).
KEPT_WORD_ENDS_PARAGRAPH = "kept-word-ends-paragraph"

#: The check, which states no reach and compares no scenes (DEC-075 point 2).
CHECK = SceneCheck("a paragraph that a line feed ends on a word kept off a line's end")

#: The fix the finding names (DEC-075 point 2).
FIX = (
    "move the line feed before the word, so that the word opens the next paragraph with the "
    "word after it, or reword the paragraph's end"
)


def kept_word_ends(scene: Mapping[str, Any], content: str) -> list[Finding]:
    """For each text `scene` holds, a finding for each of its paragraphs that a line feed ends
    on a word the rules of the scene's language keep off a line's end, in the content file
    `content`, in drawing order."""
    language = str(scene.get("language", ""))
    rules = rules_of(language)
    found: list[Finding] = []
    for text in _texts(scene):
        paragraphs: Sequence[Sequence[Mapping[str, Any]]] = text.get("paragraphs") or []
        for place, runs in enumerate(paragraphs[:-1], start=1):
            kept = rules.kept_at_end("".join(str(run.get("text", "")) for run in runs))
            if kept is not None:
                start, word = kept
                trace = str(text.get("id", ""))
                where = _where(_run_at(runs, start), trace)
                found.append(_finding(place, word, language, content, where, trace))
    return found


def _texts(scene: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Each text `scene` holds, in drawing order."""
    stack = list(reversed(scene.get("children") or []))
    while stack:
        element = stack.pop()
        if element.get("type") == "text":
            yield element
        stack.extend(reversed(element.get("children") or []))


def _run_at(runs: Sequence[Mapping[str, Any]], start: int) -> Mapping[str, Any]:
    """The run of a paragraph, `runs`, whose text holds the character at `start` of their
    texts joined."""
    reached = 0
    for run in runs:
        reached += len(str(run.get("text", "")))
        if start < reached:
            return run
    return runs[-1]


def _where(run: Mapping[str, Any], trace: str) -> str:
    """Where a finding on a word in `run` lies in the content file: the key path of the run,
    as its source names it, or the text's trace where its source is no content's."""
    source = str((run.get("sources") or {}).get("text", ""))
    return source.removeprefix(CONTENT) if source.startswith(CONTENT) else trace


def _finding(place: int, word: str, language: str, content: str, where: str, trace: str) -> Finding:
    """The call for attention on paragraph `place` of the text `trace`, which ends on the kept
    word `word` of `language` (DEC-075 point 2)."""
    return Finding(
        KEPT_WORD_ENDS_PARAGRAPH,
        ATTENTION,
        f"paragraph {place} ends on `{word}`, a word the rules of `{language}` keep off a "
        "line's end, and the line feed after it ends the line, so no break carries the word "
        "on to the word after it",
        file=content,
        where=where,
        fix=FIX,
        who=AUTHOR,
        extra={"place": trace},
    )
