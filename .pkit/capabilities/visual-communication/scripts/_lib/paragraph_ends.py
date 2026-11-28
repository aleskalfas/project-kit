"""The check of a paragraph that a line feed ends on a word kept off a line's end
(visual-communication DEC-075).

- **Which paragraphs** (point 1). Each paragraph of each text the scene holds, its runs'
  texts joined, as the scene holds them and the engine breaks them, that a line feed written
  in the text ends, where the text goes on after it: a later paragraph holds something
  other than a space. A paragraph that a line feed the engine added ends, one after each
  path of a list of paths but the last, is not read (`SceneResult.added`).
- **Which words.** A paragraph ends on a *kept word* where its last word, with nothing after
  it but spaces, is one the rules of the scene's language keep off the end of a line the
  engine breaks, found as the engine finds one before a space. The check reads them from
  the engine's own rules (`text.LanguageRules.kept_at_end`), so the two never disagree.
- **The finding** (point 2) asks for attention where the text is written, by the run whose
  text holds the word's first letter. Text the content gives lies in the content file of
  the scene's language, at the run's key path, for the piece's author. Text no content
  gives, such as a fact of the export, lies in the file of the component that shows it, at
  the text's trace, for whoever can correct that file. The finding names the paragraph by
  its place among the text's paragraphs, and the word. It carries the text's trace as its
  place, so that whatever reads it finds the page it lies on, and names no trace in its
  message, so a field drawn on several pages is one finding.

It states no reach, since no reader's instructions read its silence (DEC-063 point 1), and
compares no scenes: each finding is one scene's.

Reads no file, and knows nothing of the check's run: the check gives it each scene, the
paragraphs that the engine's line feeds end in it, and who owns a library version.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from typing import Any

from _lib import names
from _lib import pipeline as pl
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
    "move the word past the line feeds after it, so that it opens the paragraph the text goes "
    "on in, or reword the paragraph's end"
)


def kept_word_ends(
    scene: Mapping[str, Any],
    added: Mapping[str, Collection[int]],
    owner: Callable[[str], str],
) -> list[Finding]:
    """For each text `scene` holds, a finding for each of its paragraphs that a line feed
    written in the text ends on a word the rules of the scene's language keep off a line's
    end, where the text goes on after the line feed, in drawing order. `added` gives, for
    each text by its trace, the places of the paragraphs that a line feed the engine added
    ends, which are not read; `owner`, who corrects a library version, `<name>@<version>`,
    for a text no content gives that a library's component shows."""
    language = str(scene.get("language", ""))
    rules = rules_of(language)
    found: list[Finding] = []
    for text, shows in _texts(scene):
        trace = str(text.get("id", ""))
        paragraphs: Sequence[Sequence[Mapping[str, Any]]] = text.get("paragraphs") or []
        joined = ["".join(str(run.get("text", "")) for run in runs) for runs in paragraphs]
        unread = added.get(trace, ())
        for index, paragraph in enumerate(joined[:-1]):
            if index in unread or not _goes_on(joined[index + 1 :]):
                continue
            kept = rules.kept_at_end(paragraph)
            if kept is None:
                continue
            start, word = kept
            said = _said(index + 1, word, language)
            run = _run_at(paragraphs[index], start)
            found.append(_finding(said, run, trace, language, shows, owner))
    return found


def _texts(
    scene: Mapping[str, Any],
) -> Iterator[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """Each text `scene` holds, in drawing order, with the group of the component that shows
    it: the nearest group above it that names a component."""
    stack = [(child, scene) for child in reversed(scene.get("children") or [])]
    while stack:
        element, shows = stack.pop()
        if element.get("type") == "text":
            yield element, shows
        below = element if element.get("component") else shows
        stack.extend((child, below) for child in reversed(element.get("children") or []))


def _goes_on(after: Sequence[str]) -> bool:
    """Whether the text goes on after a line feed: one of the paragraphs `after` it holds
    something other than a space."""
    return any(paragraph.strip(" ") for paragraph in after)


def _run_at(runs: Sequence[Mapping[str, Any]], start: int) -> Mapping[str, Any]:
    """The run of a paragraph, `runs`, whose text holds the character at `start` of their
    texts joined."""
    reached = 0
    for run in runs:
        reached += len(str(run.get("text", "")))
        if start < reached:
            return run
    return runs[-1]


def _said(place: int, word: str, language: str) -> str:
    """What the finding on paragraph `place`, which ends on the kept word `word` of
    `language`, says (DEC-075 point 2)."""
    return (
        f"paragraph {place} ends on `{word}`, a word the rules of `{language}` keep off a "
        "line's end, and the line feed after it ends the line, so no break carries the word "
        "on to what follows it"
    )


def _finding(
    said: str,
    run: Mapping[str, Any],
    trace: str,
    language: str,
    shows: Mapping[str, Any],
    owner: Callable[[str], str],
) -> Finding:
    """The call for attention `said`, where the run `run` of the text `trace` is written
    (DEC-075 point 2): the content file of `language`, at the run's key path, where the
    content gives its text; else the file of the component the group `shows` names, at the
    text's trace: the piece's own, for its author, or a library version's, for whoever
    `owner` names."""
    source = str((run.get("sources") or {}).get("text", ""))
    place = {"place": trace}
    if source.startswith(CONTENT):
        content, where = pl.content_file(language), source.removeprefix(CONTENT)
        return Finding(
            KEPT_WORD_ENDS_PARAGRAPH, ATTENTION, said, content, where, FIX, who=AUTHOR, extra=place
        )
    library, _, name = str(shows.get("component", "")).partition("/")
    file = f"{pl.COMPONENTS}/{name}.yaml"
    if library == names.PIECE:
        return Finding(
            KEPT_WORD_ENDS_PARAGRAPH, ATTENTION, said, file, trace, FIX, who=AUTHOR, extra=place
        )
    version = shows.get("version")
    held = f"{library}@{version}" if version else library
    return Finding(
        KEPT_WORD_ENDS_PARAGRAPH,
        ATTENTION,
        said,
        file,
        trace,
        FIX,
        library=held,
        who=owner(held),
        extra=place,
    )
