"""The check of a text smaller than its medium allows (visual-communication DEC-055, DEC-028
point 1, DEC-046 point 5).

A piece names the media it is shown in under `media`, from the capability's words
(`layout.MEDIA`): a list, each medium showing every size the piece is drawn at, or a mapping
of each medium to the sizes it shows (DEC-055 point 1). The piece's top declares the
smallest text size of each medium its pages are made for under `smallest-text`, a fixed
length in px or a share of the page (points 2 and 3), which the scene's result carries
(`layout.SmallestText`). The check reads the scene, before any renderer runs, so one finding
serves every renderer (point 5).

- **What it measures** (point 4). The font size of each run of each text a page draws, as the
  scene holds it, against the smallest size of each medium that shows the scene's key, read
  for the page the run lies on. Both are rounded to 1/100 px, as the scene rounds a length,
  and a run at the smallest size passes. A page is taken at its own size, as its medium shows
  it: a fixed length is px of the page, and a share is read from the page's size.
- **What it fails** (point 6). A run below it, `text-too-small`, at its text's trace in the
  piece's own file, since the size comes from the component, the brand and the top together.
  A run below the smallest size of several media is one place, and takes one finding that
  names each.
- **What it states** (point 10). Where it could measure no text's size, a fact,
  `text-size-unmeasured`: for a piece that names no medium, a medium the top declares nothing
  for, a size no medium shows, and a page where a share gives no smallest size. Each names
  how far it covers: every language and every key, a key, or a page.
- **A share that gives no smallest size at a page** (point 7) is the formula's own finding,
  given as the engine's: a share that reads `:page-height` at a page that asks for no height,
  at the top's file where the top's own drawing draws that page, else at the piece's lock; a
  division by zero, and a length of zero or less, at the lock. Beside it the check states its
  own fact for that page.

It gives each finding scene by scene, unmerged, and compares scenes across no axis: each
finding rests on its own scene alone (DEC-063 point 1). The render's code merges them, as it
merges every scene finding (`checks.merged`). Its reach is `CHECK.reach`, in the words of its
entry in the capability's list of checks.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from _lib import formula as fm
from _lib import layout
from _lib import pipeline as pl
from _lib.findings import FACT, FAILS, Finding
from _lib.scene import SceneResult
from _lib.scene_checks import Found, Reach, SceneCheck

#: The finding on a run drawn smaller than its medium allows, and the fact the check states
#: where it could measure no text's size (DEC-055 points 6 and 10).
TEXT_TOO_SMALL = "text-too-small"
TEXT_SIZE_UNMEASURED = "text-size-unmeasured"

#: The check of a text's size against its medium, with its reach, since the reviewer reads
#: its silence (DEC-055 point 11, DEC-063 point 1). It compares scenes across no axis.
CHECK = SceneCheck(
    "a text smaller than its medium allows",
    id="text-size-by-medium",
    labels=(TEXT_TOO_SMALL, TEXT_SIZE_UNMEASURED),
    reach=Reach(
        measures=(
            "the font size of each run of each text a page draws, as the scene holds it, "
            "against the smallest size the piece's top declares for each medium that, as the "
            "piece's `media` names it, shows the scene's key, for the page the run lies on, "
            "both rounded to 1/100 px, a run at that size passing (DEC-055 point 4)",
            "each page at its own size, as its medium shows it: a fixed smallest size as px "
            "of the page, and a share of the page read from the page's width and height in "
            "the scene (DEC-055 point 3)",
        ),
        leaves_out=(
            "words inside a picture, made while preparing or elsewhere, which are pixels and "
            "no text the scene holds (DEC-046 point 5)",
            "how large a face's letters stand in their font size, which the review judges on "
            "the drawn page (DEC-055 point 4)",
            "how a viewer shows a page: a width other than the brand's at the size it is "
            "drawn at, a zoom, and a scale a presenter or a print sets (DEC-055 point 3)",
            "a text with no line, and a run of which no line draws a part, neither of which "
            "draws anything (DEC-063 point 1)",
            "a text that lies on no page the scene names, such as one a top whose slot holds "
            "its pages draws beside them (DEC-063 point 1)",
        ),
        states=(
            "`text-size-unmeasured`, for a piece that names no medium, which covers every "
            "run of the scene, in every language and at every key (DEC-055 point 10)",
            "`text-size-unmeasured`, for a medium the piece names whose smallest size its top "
            "does not declare, which covers every run at each key that medium shows, and "
            "names the medium, the top and the sizes a mapping gives it (DEC-055 point 10)",
            "`text-size-unmeasured`, for a size the piece is drawn at that no medium shows, "
            "which covers every run at each key of that size, and names the size "
            "(DEC-055 point 10)",
            "`text-size-unmeasured`, for a page where a share of the page gives no smallest "
            "size, which covers every run of that page at each key where it does not, and "
            "names the medium (DEC-055 points 7 and 10)",
        ),
        statements=(TEXT_SIZE_UNMEASURED,),
    ),
)

#: Where a statement on the piece's media lies (DEC-055 point 10).
MEDIA_WHERE = pl.MEDIA


def found(
    project: pl.Project,
    language: str,
    result: SceneResult,
    scene: Mapping[str, Any],
    engine: SceneCheck,
) -> list[Found]:
    """What the check finds in the scene of `language` at its key, `scene` its document:
    each statement where it could measure no text's size, each run too small for a medium
    that shows the key, and each formula's finding where a share gives no smallest size at a
    page, given as `engine`'s, the check of what the engine finds as it computes a scene,
    since a formula's finding is never this check's (DEC-055 points 4, 6, 7 and 10)."""
    media = project.piece.media
    size_key = result.scene.size_key
    if media is None:
        return [Found(_unnamed(), CHECK, None, None)]
    size = project.size_of(size_key)
    showing = [medium for medium, sizes in media.items() if sizes is None or size in sizes]
    if not showing:
        return [Found(_unshown(size), CHECK, None, size_key)]
    declared = result.smallest
    sizes = dict(declared.sizes) if declared is not None else {}
    top = declared.top if declared is not None else project.piece.top
    mapped = any(sizes_of is not None for sizes_of in media.values())
    found_here = [
        Found(_undeclared(medium, top, media[medium] if mapped else None), CHECK, None, size_key)
        for medium in showing
        if medium not in sizes
    ]
    measured = [medium for medium in showing if medium in sizes]
    if not measured or declared is None:
        return found_here
    for page in _pages(scene):
        trace = str(page["id"])
        height = result.heights.get(trace, layout.PageHeight(asks=False, own=False))
        minimums: dict[str, tuple[float, str]] = {}
        for medium in measured:
            value = sizes[medium]
            if isinstance(value, fm.Formula):
                given, faults = _share(value, page, height, medium, declared)
                found_here.extend(Found(f, engine, language, size_key, page=trace) for f in faults)
                if given is None:
                    stated = _no_share(medium, top, value, trace)
                    found_here.append(Found(stated, CHECK, language, size_key, page=trace))
                    continue
                of_page = f"{float(page['width']):g} × {float(page['height']):g} px"
                minimums[medium] = (given, f"`{value.text}` of the page {of_page}")
            else:
                minimums[medium] = (value, "")
        if not minimums:
            continue
        found_here.extend(
            Found(finding, CHECK, language, size_key, page=trace)
            for finding in _too_small(page, minimums, top, size)
        )
    return found_here


# --- the statements --------------------------------------------------------------------------


def _unnamed() -> Finding:
    return Finding(
        TEXT_SIZE_UNMEASURED,
        FACT,
        f"the piece names no medium it is shown in under `{pl.MEDIA}`, so no text's size was "
        "measured, in any language or at any size",
        file=pl.PIECE_FILE,
        where=MEDIA_WHERE,
    )


def _unshown(size: str | None) -> Finding:
    named = f"the size `{size}`" if size else "this key"
    return Finding(
        TEXT_SIZE_UNMEASURED,
        FACT,
        f"no medium the piece names under `{pl.MEDIA}` shows {named}, so no text's size was "
        "measured at it",
        file=pl.PIECE_FILE,
        where=MEDIA_WHERE,
    )


def _undeclared(medium: str, top: str, sizes: Sequence[str] | None) -> Finding:
    shows = (
        f", at the sizes the piece shows in it: {', '.join(f'`{each}`' for each in sizes)}"
        if sizes
        else ""
    )
    return Finding(
        TEXT_SIZE_UNMEASURED,
        FACT,
        f"the top `{top}` declares no smallest text size for `{medium}`, so no text's size "
        f"was measured in `{medium}`{shows}",
        file=pl.PIECE_FILE,
        where=MEDIA_WHERE,
    )


def _no_share(medium: str, top: str, value: fm.Formula, page: str) -> Finding:
    return Finding(
        TEXT_SIZE_UNMEASURED,
        FACT,
        f"the smallest size of `{medium}` that `{top}` declares, `{value.text}`, gives none "
        f"at the page `{page}`, so no text's size on it was measured in `{medium}`",
        file=pl.PIECE_FILE,
        where=page,
    )


# --- a share of the page ---------------------------------------------------------------------


def _share(
    formula: fm.Formula,
    page: Mapping[str, Any],
    height: layout.PageHeight,
    medium: str,
    declared: layout.SmallestText,
) -> tuple[float | None, list[Finding]]:
    """The smallest size a share of the page gives at `page`, read from the page's width and
    height in the scene; None, with the formula's finding, where it gives none (DEC-055
    point 7): it reads `:page-height` at a page that asks for no height, divides by zero, or
    gives a length of zero or less. The first lies at the top's file where the top's own
    drawing draws the page, which alone shows it, and every other at the piece's lock, which
    names no version."""
    trace = str(page["id"])
    at = f"at the page `{trace}`"
    under = f"`{declared.top}` of {declared.library or 'the piece'}"
    reads_height = any(
        isinstance(ref, fm.Engine) and ref.name == "page-height" for ref in formula.references()
    )
    if reads_height and not height.asks:
        why = (
            f"the smallest size of `{medium}`, `{formula.text}`, reads `:page-height` {at}, "
            "which asks for no height: it is as tall as its content, so a share of its height "
            "grows with the text it is held to"
        )
        if height.own:
            fix = "take the share of `:page-width`, or a fixed length"
            return None, [_at_top("formula-reach", why, medium, declared, fix)]
        return None, [_at_lock("formula-reach", f"under this lock, {under}: {why}")]
    sizes = {"page-width": float(page["width"]), "page-height": float(page["height"])}
    try:
        given = fm.evaluate(
            formula, lambda ref: sizes[ref.name] if isinstance(ref, fm.Engine) else 0
        )
    except fm.DivisionByZero as error:
        message = f"under this lock, {under}: the smallest size of `{medium}` {at}: {error}"
        return None, [_at_lock("division-by-zero", message)]
    given = fm.rounded(given, 2)
    if given <= 0:
        message = (
            f"under this lock, {under}: the smallest size of `{medium}`, `{formula.text}`, "
            f"gives {given:g} px {at}, and a smallest size is a length above zero"
        )
        return None, [_at_lock("component-shape", message)]
    return given, []


def _at_top(code: str, why: str, medium: str, declared: layout.SmallestText, fix: str) -> Finding:
    """A share's fault the top's file alone shows, at its value for `medium` (DEC-055 point
    7): in the locked version of a library's top, or in the piece's own top."""
    name = declared.top.partition("/")[2]
    return Finding(
        code,
        FAILS,
        f"{declared.top}: {why}",
        file=f"{pl.COMPONENTS}/{name}.yaml",
        where=f"{layout.SMALLEST_TEXT}.{medium}",
        library=declared.library,
        fix=fix,
    )


def _at_lock(code: str, message: str) -> Finding:
    """A share's fault only the piece's lock shows, which names no version (DEC-055 point 7)."""
    return Finding(
        code,
        FAILS,
        message,
        file=pl.PIECE_FILE,
        where="lock",
        fix="give the medium a share the page's size gives a length above zero under every "
        "brand, in the top; or draw the piece under a brand, or a top, under which it does",
    )


# --- the runs --------------------------------------------------------------------------------


def _too_small(
    page: Mapping[str, Any],
    minimums: Mapping[str, tuple[float, str]],
    top: str,
    size: str | None,
) -> list[Finding]:
    """A finding on each run of each text `page` draws whose font size, rounded to 1/100 px,
    is below the smallest size of one medium of `minimums` or more, each with that size and,
    for a share, the formula and the page's size it was read from; one finding a run, naming
    each such medium (DEC-055 points 4 and 6)."""
    found = []
    for text in _texts(page):
        for run in _drawn_runs(text):
            drawn = fm.rounded(float(run.get("font-size", 0)), 2)
            below = [
                (medium, minimum, read)
                for medium, (minimum, read) in minimums.items()
                if drawn < fm.rounded(minimum, 2)
            ]
            if below:
                found.append(_small(text, run, drawn, below, top, size))
    return found


def _small(
    text: Mapping[str, Any],
    run: Mapping[str, Any],
    drawn: float,
    below: Sequence[tuple[str, float, str]],
    top: str,
    size: str | None,
) -> Finding:
    source = str((run.get("sources") or {}).get("text") or text["id"])
    style = run.get("style") or "its role"
    held = "; and ".join(
        f"below the smallest size of `{medium}`, {minimum:g} px{f', {read}' if read else ''}"
        for medium, minimum, read in below
    )
    at = f"`{size}`" if size else "this size"
    elsewhere = ", ".join(f"`{medium}`" for medium, _, _ in below)
    return Finding(
        TEXT_TOO_SMALL,
        FAILS,
        f"the run of `{source}` is set in `{style}` at {drawn:g} px, {held}, which `{top}` "
        "declares",
        file=pl.PIECE_FILE,
        where=str(text["id"]),
        fix=f"set the run in a larger role: another style for it, or an option or a component "
        f"that sets the text larger; or a brand that sizes `{style}` larger at {at}. Only where "
        f"the piece is in fact shown so: have `{pl.MEDIA}` show {at} in no medium of "
        f"{elsewhere}, and another of the piece's sizes in it; or draw the piece at a size "
        f"whose type is larger, such as `projector` for a room, and name that size for it in "
        f"place of {at}. These two change where the piece is said to be shown, and clear the "
        "finding with no text made larger",
    )


def _drawn_runs(text: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Each run of `text` of which a line draws a part, once, in the order its lines draw
    them: a run that goes on past a line feed is one run of each paragraph it reaches, and
    is read once, by its source, its role and its size."""
    paragraphs = text.get("paragraphs") or []
    seen: set[Any] = set()
    for line in text.get("lines") or []:
        index = int(line.get("paragraph", 0))
        runs = paragraphs[index] if index < len(paragraphs) else []
        for span in line.get("spans") or []:
            place = int(span.get("run", 0))
            if place >= len(runs):
                continue
            run = runs[place]
            source = (run.get("sources") or {}).get("text") or (index, place)
            key = (source, run.get("style"), run.get("font-size"))
            if key not in seen:
                seen.add(key)
                yield run


def _pages(scene: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Each page the scene names, in drawing order."""
    wanted = set(scene.get("pages", []))
    stack = list(reversed(scene.get("children", [])))
    while stack:
        element = stack.pop()
        if element.get("id") in wanted:
            yield element
        elif element.get("type") == "group":
            stack.extend(reversed(element.get("children", [])))


def _texts(page: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Each text `page` draws, in drawing order."""
    stack = list(reversed(page.get("children", [])))
    while stack:
        element = stack.pop()
        if element.get("type") == "text":
            yield element
        elif element.get("type") == "group":
            stack.extend(reversed(element.get("children", [])))
