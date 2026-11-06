"""The whole-repository friction check's findings, rendered for the people who answer them.

`.github/workflows/friction-report.yml` runs the whole-repository friction check
(COR-050 point 6) on `main` and hands its machine-readable document, `pkit
friction check --all --json`, to this script. It renders that document as one
Markdown body, counts the findings that need an answer and says whether a prune is
due; `scripts/friction_tracking_issue.py` publishes all three. It is a function of the
document: it runs no check, reads no repository and talks to no tracker. It is
project-kit's own pipeline tooling, no part of what project-kit ships (ADR-055
point 5).

- **What needs an answer** is every finding but ADR-055 point 5's four kinds
  (`NO_ANSWER_NEEDED`). A deferral, `deferred`, is itself an answer (COR-050 point
  5), and the check reports `left-out` and `whole-and-parts` as owing nothing. Two
  revalidations made apart, `answered-apart`, are debt that no change owes, reported
  only until the next revalidation on the artefact judges them together (COR-062 point 7, ADR-068
  point 6). An `over-broad` anchor is reported only (COR-050 point 12). Its count
  moves as the window of commits slides, with no anchor changed, and nothing records a
  person's judgement that an anchor is fine, so it would hold the issue open for good
  (ADR-055 point 5, ADR-080). Deferrals, each with its reason,
  the revalidations answered apart and the over-broad anchors are listed in
  sections of their own, a `whole-and-parts` anchor beside `left-out` as reported, nothing
  owed, and the headline counts the revalidations answered
  apart separately from what needs an answer. The two measures (point 8) are rendered
  and never counted: they say what remains to anchor.
- **A prune is due** once `pkit friction prune` would remove `PRUNE_DUE` answer files
  or more (ADR-068 point 4). It is no finding, needs no answer and leaves the body as
  it is. The publication says so apart, and the publisher gives it an issue of its own.
- **The same findings, the same body.** The body is a function of the findings
  and the measures — no age, no run time, no HEAD — so a publisher that compares
  bodies changes nothing when nothing changed. A finding says since when by the
  UTC day of its origin, the day the check's own message names. An over-broad
  anchor is told in this module's words, not the check's, whose message counts
  the recent commits it flagged its artefact in and so moves with most pushes.
  The over-broad anchors are grouped as the check's own view groups them, by the
  `bar` each crossed (ADR-080 point 3): an anchor over the first bar is an entry
  of its own, and the anchors the second bar names on one artefact are one entry,
  the largest share first. A document that gives no `bar` lists each apart.
- **Inert text.** What the document carries — paths, anchors, messages, deferral
  reasons, commit subjects, dates — is set in code spans, so a reason naming
  `@someone` or `#123` notifies and links nobody, and none of it can break the
  body's structure. A path that is not valid UTF-8 is set with its bytes escaped
  (`caf\\xe9.md`).
- **Within a body's size.** Trackers cap a body (GitHub at 65 536 characters).
  While the body exceeds `BUDGET`, its lists are shortened by whole entries: the
  measures and the over-broad anchors first, then the deferrals, what was
  answered apart and what owes nothing, and the findings that need an answer
  last. Each shortened list ends
  with how many entries it does not show, and the body says how many in all.
- **A document it cannot fully read is refused** (`Unreadable`): text that is no
  JSON object, another check's document, a `schema_version` other than
  `DOCUMENT_VERSION`, or one without its findings or its measures. Nothing is
  rendered from it, least of all "nothing needs an answer". A document without
  `schema_version` reads as version 1, as the CLI reference says of this
  check's document ("Friction checks").

From the repository root:

    uv run python scripts/friction_report_body.py <friction.json>           the body
    uv run python scripts/friction_report_body.py <friction.json> --json    the publication
    uv run pkit friction check --all --json | uv run python scripts/friction_report_body.py -

The last is how to see locally what the tracking issue would say: the
rendering, without the marker and the notice line the publisher sets above it.
The publisher itself runs only in the workflow.

It exits 0 whatever the check found, and 1, saying why, when it has no document
to render.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

#: The version of `pkit friction check --all --json` this script reads, and the
#: `check` that document names itself by.
DOCUMENT_VERSION = 1
DOCUMENT_CHECK = "repository"

#: The version of the publication `publication` answers.
PUBLICATION_VERSION = 1

#: The kinds with a section of their own; every other kind that needs an answer
#: is rendered under "Other findings".
STALE = "stale"
DEFERRED = "deferred"
LEFT_OUT = "left-out"
OVER_BROAD = "over-broad"
ANSWERED_APART = "answered-apart"
WHOLE_AND_PARTS = "whole-and-parts"

#: The kinds that need no answer: a deferral is one (COR-050 point 5), the check
#: reports `left-out` and `whole-and-parts` as owing nothing (the CLI reference,
#: "Friction checks"; ADR-080 point 5), revalidations answered apart are debt reported
#: only, which no change owes (COR-062 point 7), and an over-broad anchor is reported
#: only, its count moving with no anchor changed (COR-050 point 12; ADR-055 point 5).
NO_ANSWER_NEEDED = frozenset({DEFERRED, LEFT_OUT, ANSWERED_APART, OVER_BROAD, WHOLE_AND_PARTS})

#: How many answer files a prune would remove make it due (ADR-068 point 4).
PRUNE_DUE = 100

#: The size a body keeps within: GitHub caps an issue body at 65 536 characters,
#: and the publisher adds lines of its own.
BUDGET = 60_000

#: The groups of lists, in the order they are shortened to fit `BUDGET`, and the
#: lengths each group's lists are shortened to, tried in turn.
MEASURES = "measures"
LISTED = "listed"
ANSWER = "answer"
SHORTENED_IN = (MEASURES, LISTED, ANSWER)
LIMITS = (100, 30, 10, 3, 0)

INTRO = (
    "The whole-repository friction check (COR-050 point 6) judges every artefact in the "
    "declared places against the current history, and finds the friction no pull request "
    "answers. Answer a finding in a pull request: revalidate the artefact, or defer the "
    "anchor with a reason. A deferral is an answer; it stays listed here. `pkit friction "
    "check --all` gives this report from HEAD, `pkit friction explain <artefact>` what "
    "clears one artefact's friction, and `pkit friction debt` the debt, oldest first."
)
DORMANT = (
    "The check is dormant: no place is declared, so nothing is anchored and nothing is "
    "demanded (COR-050 point 15)."
)
OTHER = (
    "Dead anchors, anchors of a kind nothing resolves, anchors on an id two artefacts share, "
    "what does not read — a file's front matter, or `friction.exclude` at a revalidation "
    "point — and artefacts a shallow clone could not judge."
)
APART = (
    "Two revalidations of one artefact, neither of which read the other: nobody has judged "
    "their combined state. No change owes an answer for it. The next revalidation on the "
    "artefact reads both and judges them together (COR-062 point 7)."
)
#: The bars an over-broad finding names in the document's `bar`: the first, the
#: anchor's own, and the second, the artefact's, whose anchors are one entry.
FLAGS = "flags"
ASKS = "asks"
#: What the body says of an over-broad entry, in place of the check's message: by the
#: bar it crossed, or, from a document that gives none, of either.
OVER_BROAD_SAID = {
    FLAGS: (
        "flagged its artefact in most of the recent commits (`pkit friction check --all` "
        "gives the count, and what to anchor instead)"
    ),
    ASKS: (
        "the anchors behind most of the many recent commits that asked the artefact for a "
        "revalidation that left it as it was, the largest share first (`pkit friction check "
        "--all` gives the counts, and what to anchor instead)"
    ),
    None: (
        "flagged its artefact in most of the recent commits, or is among the anchors behind "
        "most of the many recent commits that asked its artefact for a revalidation that "
        "left it as it was (`pkit friction check --all` gives the counts, and what to anchor "
        "instead)"
    ),
}
OVER_BROAD_LEAD = (
    "Anchors that ask their artefacts for an answer more often than ADR-080's bars allow. No "
    "change owes an answer for one. Narrow one where something names less, remove one its "
    "artefact does not rest on, or split what it stands on or its artefact, and revalidate "
    "the artefact."
)
WHOLE = "`pkit friction check --all` lists them all"


class Unreadable(Exception):
    """The text holds no whole-repository document this script fully reads."""


def read_document(text: str | bytes, source: str) -> Mapping[str, Any]:
    """The whole-repository check's document as `source` holds it. Raises
    Unreadable unless it is one this script reads in full."""
    try:
        loaded = json.loads(text)
    except ValueError as exc:
        raise Unreadable(f"{source} holds no JSON document ({exc})") from exc
    if not isinstance(loaded, Mapping):
        raise Unreadable(f"{source} holds no document of `pkit friction check --all --json`")
    document = cast("Mapping[str, Any]", loaded)
    if document.get("check") != DOCUMENT_CHECK:
        raise Unreadable(f"{source} holds no document of `pkit friction check --all --json`")
    # A document without the key reads as version 1 (the CLI reference, "Friction checks").
    version = document.get("schema_version", DOCUMENT_VERSION)
    if version != DOCUMENT_VERSION:
        raise Unreadable(
            f"{source} is a document of schema_version {version!r}; "
            f"this script reads {DOCUMENT_VERSION}"
        )
    findings = document.get("findings")
    if not isinstance(findings, list) or not all(
        isinstance(finding, Mapping)
        and isinstance(cast("Mapping[str, Any]", finding).get("kind"), str)
        for finding in cast("list[Any]", findings)
    ):
        raise Unreadable(f"{source} gives no list of findings, each with its kind")
    if not isinstance(document.get("measures"), Mapping):
        raise Unreadable(f"{source} gives no measures")
    return document


def needing_answer(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The findings of `document` that need an answer: all but `NO_ANSWER_NEEDED`,
    and none while the check is dormant."""
    if document.get("dormant"):
        return []
    return [f for f in _findings(document) if f["kind"] not in NO_ANSWER_NEEDED]


def prune_due(document: Mapping[str, Any]) -> bool:
    """Whether `pkit friction prune` would remove `PRUNE_DUE` answer files or more. The
    document's `answers` came without a version change (the CLI reference, "Friction
    checks"), so one without them reads, and says no prune is due."""
    answers = document.get("answers")
    if not isinstance(answers, Mapping):
        return False
    prunable = cast("Mapping[str, Any]", answers).get("prunable")
    return isinstance(prunable, list) and len(cast("list[Any]", prunable)) >= PRUNE_DUE


def publication(document: Mapping[str, Any]) -> dict[str, Any]:
    """What the publisher reads: how many findings need an answer, whether a prune is
    due, and the body."""
    return {
        "schema_version": PUBLICATION_VERSION,
        "needs_answer": len(needing_answer(document)),
        "prune_due": prune_due(document),
        "body": body(document),
    }


def body(document: Mapping[str, Any]) -> str:
    """The body, its lists shortened group by group, in the order of `SHORTENED_IN`,
    until it fits `BUDGET`. It always comes to fit: what the document carries is
    all in the lists, and a list shortened to nothing is one line."""
    limits: dict[str, int | None] = dict.fromkeys(SHORTENED_IN)
    text = render(document, limits)
    for group in SHORTENED_IN:
        for limit in LIMITS:
            if len(text) <= BUDGET:
                return text
            limits[group] = limit
            text = render(document, limits)
    return text


def render(document: Mapping[str, Any], limits: Mapping[str, int | None] | None = None) -> str:
    """The body, the lists of each group holding at most `limits[group]` entries
    (all of them for `None`, or for no `limits`)."""
    if document.get("dormant"):
        return _joined(["**Nothing needs an answer.**", "", INTRO, "", DORMANT])
    cut = _Cut(limits or {})
    findings = _findings(document)
    answer = needing_answer(document)
    stale = [f for f in answer if f["kind"] == STALE]
    other = [f for f in answer if f["kind"] != STALE]
    deferred = [f for f in findings if f["kind"] == DEFERRED]
    apart = [f for f in findings if f["kind"] == ANSWERED_APART]
    owing_nothing = [f for f in findings if f["kind"] in (LEFT_OUT, WHOLE_AND_PARTS)]
    broad = [f for f in findings if f["kind"] == OVER_BROAD]
    sections: list[str] = []
    for title, lead, entries, group in (
        (
            "Stale: an anchor changed after the revalidation point",
            None,
            [_finding(f, False) for f in stale],
            ANSWER,
        ),
        ("Other findings that need an answer", OTHER, [_finding(f, True) for f in other], ANSWER),
        (
            "Deferred: answered with a reason, and holding nothing open",
            None,
            [_finding(f, False) for f in deferred],
            LISTED,
        ),
        (
            "Answered apart: debt, reported only and holding nothing open",
            APART,
            [_finding(f, False) for f in apart],
            LISTED,
        ),
        ("Reported, nothing owed", None, [_finding(f, True) for f in owing_nothing], LISTED),
        (
            "Over-broad: reported, holding nothing open",
            OVER_BROAD_LEAD,
            _over_broad(broad),
            MEASURES,
        ),
    ):
        if entries:
            sections += [f"### {title}", "", *([lead, ""] if lead else [])]
            sections += cut(entries, group)
            sections.append("")
    sections += ["### Measures: reported, never failed (COR-050 point 8)", ""]
    sections += _measures(cast("Mapping[str, Any]", document["measures"]), cut)
    headline = _headline(stale, other, apart)
    return _joined([headline, "", INTRO, "", *cut.notice(), *sections])


@dataclass
class _Cut:
    """Shortens lists to their group's limit, counting the entries it does not show."""

    limits: Mapping[str, int | None]
    not_shown: int = 0

    def __call__(self, entries: Sequence[str], group: str) -> list[str]:
        limit = self.limits.get(group)
        if limit is None or len(entries) <= limit:
            return list(entries)
        more = len(entries) - limit
        self.not_shown += more
        return [*entries[:limit], f"- … {more} not shown here: {WHOLE}"]

    def notice(self) -> list[str]:
        """The lines that say the body was shortened; none when it was not. Asked for
        once every list is made, and set above them."""
        if not self.not_shown:
            return []
        entries = "entry is" if self.not_shown == 1 else "entries are"
        return [
            f"_Shortened to fit the body's size: {self.not_shown} {entries} not shown. {WHOLE}._",
            "",
        ]


def _headline(stale: Sequence[Any], other: Sequence[Any], apart: Sequence[Any]) -> str:
    """What needs an answer, and, counted apart from it, what was answered apart."""
    if not stale and not other:
        line = "**Nothing needs an answer.**"
    else:
        parts = [
            *([f"{len(stale)} stale"] if stale else []),
            *([f"{len(other)} other finding{'' if len(other) == 1 else 's'}"] if other else []),
        ]
        line = f"**Needs an answer: {', '.join(parts)}.**"
    return f"{line} Reported only: {len(apart)} answered apart." if apart else line


def _finding(finding: Mapping[str, Any], show_kind: bool) -> str:
    """One finding: where, which anchor, since when — then what the check says of it."""
    head = [_where(finding)]
    if show_kind:
        head.append(_code(str(finding["kind"])))
    head += _anchor(finding)
    origin = finding.get("origin")
    if isinstance(origin, Mapping):
        date = cast("Mapping[str, Any]", origin).get("date")
        if isinstance(date, str):
            head.append(f"since {_code(_day(date))}")
    return f"- {' · '.join(head)}\n  {_code(str(finding.get('message') or ''))}"


def _over_broad(findings: Sequence[Mapping[str, Any]]) -> list[str]:
    """The over-broad findings, an entry each, but the second bar's on one artefact: one
    entry, naming its anchors in the document's order, the largest share first (ADR-080
    point 3). Each is told in this module's words, by the bar it crossed."""
    runs: list[list[Mapping[str, Any]]] = []
    for finding in findings:
        last = runs[-1][-1] if runs else None
        if (
            last is not None
            and finding.get("bar") == ASKS
            and last.get("bar") == ASKS
            and last.get("location") == finding.get("location")
        ):
            runs[-1].append(finding)
        else:
            runs.append([finding])
    entries: list[str] = []
    for run in runs:
        head = [_where(run[0]), *(anchor for f in run for anchor in _anchor(f))]
        bar = run[0].get("bar")
        said = OVER_BROAD_SAID.get(bar if isinstance(bar, str) else None, OVER_BROAD_SAID[None])
        entries.append(f"- {' · '.join(head)}\n  {said}")
    return entries


def _where(finding: Mapping[str, Any]) -> str:
    return _code(str(finding.get("location") or finding.get("artefact") or "?"))


def _anchor(finding: Mapping[str, Any]) -> list[str]:
    """The finding's anchor, as the writers take it, or nothing where it names none."""
    anchor = finding.get("anchor")
    if not isinstance(anchor, Mapping):
        return []
    named = cast("Mapping[str, Any]", anchor)
    return [_code(f"{named.get('kind')}:{named.get('value')}")]


def _day(date: str) -> str:
    """The UTC day of `date`, an ISO 8601 instant — the day the check's messages
    name, whatever zone the author committed in. Text that is no such instant is
    given back as it is."""
    try:
        instant = datetime.fromisoformat(date)
    except ValueError:
        return date
    if instant.tzinfo is None:
        return instant.date().isoformat()
    return instant.astimezone(UTC).date().isoformat()


def _measures(measures: Mapping[str, Any], cut: _Cut) -> list[str]:
    unanchored = [str(p) for p in _listed(measures, "unanchored")]
    accepted = [
        cast("Mapping[str, Any]", a)
        for a in _listed(measures, "accepted_unanchored")
        if isinstance(a, Mapping)
    ]
    surface = [str(p) for p in _listed(measures, "uncovered_surface")]
    lines: list[str] = []
    if unanchored or accepted:
        apart = f" ({len(accepted)} accepted with a reason, listed apart)" if accepted else ""
        lines += [
            "<details>",
            f"<summary>Unanchored artefacts: {len(unanchored)}{apart}</summary>",
            "",
            *cut([f"- {_code(p)}" for p in unanchored], MEASURES),
        ]
        if accepted:
            listed = [
                f"- {_code(str(a.get('location')))}: {_code(str(a.get('reason') or ''))}"
                for a in accepted
            ]
            lines += ["", "Accepted with a reason:", "", *cut(listed, MEASURES)]
        lines += ["", "</details>", ""]
    else:
        lines += ["Unanchored artefacts: none.", ""]
    if surface:
        lines += [
            "<details>",
            f"<summary>Uncovered surface: {len(surface)} "
            f"path{'' if len(surface) == 1 else 's'} nothing anchors</summary>",
            "",
            *cut([f"- {_code(p)}" for p in surface], MEASURES),
            "",
            "</details>",
        ]
    else:
        lines.append("Uncovered surface: none.")
    return lines


def _listed(measures: Mapping[str, Any], key: str) -> list[Any]:
    value = measures.get(key)
    return cast("list[Any]", value) if isinstance(value, list) else []


def _code(text: str) -> str:
    """`text` as one inline code span, whatever backticks it holds (CommonMark: a
    fence one backtick longer than its longest run, padded where it touches one)."""
    text = " ".join(_printable(text).split())
    if not text:
        return ""
    fence = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _printable(text: str) -> str:
    """`text` with what is not valid UTF-8 escaped. The check decodes a path with
    `surrogateescape`, so a byte that is no UTF-8 arrives as a lone surrogate, which
    no output can encode: it is set as the byte it stands for (`caf\\xe9.md`)."""
    try:
        return text.encode("utf-8", "surrogateescape").decode("utf-8", "backslashreplace")
    except UnicodeEncodeError:  # a surrogate that stands for no byte
        return text.encode("utf-8", "backslashreplace").decode("utf-8")


def _findings(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return cast("list[Mapping[str, Any]]", document["findings"])


def _joined(lines: Sequence[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render the whole-repository friction check's findings as one Markdown body, and "
            "count those that need an answer. Reads a document, runs nothing, publishes nothing."
        ),
    )
    parser.add_argument(
        "document",
        help=(
            "The file `pkit friction check --all --json` was written to; `-` reads the "
            "document from standard input."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the publication {schema_version, needs_answer, prune_due, body}.",
    )
    args = parser.parse_args(argv)
    source = "standard input" if args.document == "-" else args.document
    try:
        data = sys.stdin.buffer.read() if args.document == "-" else Path(source).read_bytes()
        document = read_document(data, source)
    except OSError as exc:
        print(f"error: {source} cannot be read ({exc}); nothing to render.", file=sys.stderr)
        return 1
    except Unreadable as exc:
        print(f"error: {exc}; nothing to render.", file=sys.stderr)
        return 1
    made = publication(document)
    text = json.dumps(made, indent=2) + "\n" if args.json else made["body"]
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
