"""The whole-repository friction check's findings, rendered for the people who answer them.

`.github/workflows/friction-report.yml` runs the whole-repository friction check
(COR-050 point 6) on `main` and hands its machine-readable document, `pkit
friction check --all --json`, to this script. It renders that document as one
Markdown body and counts the findings that need an answer;
`scripts/friction_tracking_issue.py` publishes both. It is a function of the
document: it runs no check, reads no repository and talks to no tracker. It is
project-kit's own pipeline tooling, no part of what project-kit ships (ADR-055
point 5).

- **What needs an answer** is every finding but two kinds (`NO_ANSWER_NEEDED`):
  `deferred`, a deferral being itself an answer (COR-050 point 5), and
  `left-out`, which the check reports as owing nothing. Deferrals are listed in
  a section of their own, each with its reason. The two measures (point 8) are
  rendered and never counted: they say what remains to anchor.
- **The same findings, the same body.** The body is a function of the findings
  and the measures — no age, no run time, no HEAD — so a publisher that compares
  bodies changes nothing when nothing changed. A finding says since when by the
  UTC day of its origin, the day the check's own message names. An over-broad
  anchor is told in this module's words, not the check's, whose message counts
  the tracked files and so moves with most pushes.
- **Inert text.** What the document carries — paths, anchors, messages, deferral
  reasons, commit subjects, dates — is set in code spans, so a reason naming
  `@someone` or `#123` notifies and links nobody, and none of it can break the
  body's structure. A path that is not valid UTF-8 is set with its bytes escaped
  (`caf\\xe9.md`).
- **Within a body's size.** Trackers cap a body (GitHub at 65 536 characters).
  While the body exceeds `BUDGET`, its lists are shortened by whole entries: the
  measures first, then the deferrals and what owes nothing, and the findings
  that need an answer last. Each shortened list ends with how many entries it
  does not show, and the body says how many in all.
- **A document it cannot fully read is refused** (`Unreadable`): text that is no
  JSON object, another check's document, a `schema_version` other than
  `DOCUMENT_VERSION`, or one without its findings or its measures. Nothing is
  rendered from it, least of all "nothing needs an answer".

From the repository root:

    uv run python scripts/friction_report_body.py <friction.json>           the body
    uv run python scripts/friction_report_body.py <friction.json> --json    the publication
    uv run pkit friction check --all --json | uv run python scripts/friction_report_body.py -

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

#: The kinds that need no answer: a deferral is one (COR-050 point 5), and the
#: check reports `left-out` as owing nothing (the CLI reference, "Friction checks").
NO_ANSWER_NEEDED = frozenset({DEFERRED, LEFT_OUT})

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
    "Dead anchors, anchors of a kind nothing resolves, over-broad anchors, what does not "
    "read — a file's front matter, or `friction.exclude` at a revalidation point — and "
    "artefacts a shallow clone could not judge."
)
#: What the body says of an over-broad anchor, in place of the check's message.
OVER_BROAD_SAID = (
    "matches most of the tracked files, so most changes would make it a revalidation: "
    "narrow it (`pkit friction check --all` gives the count)"
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
    version = document.get("schema_version")
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


def publication(document: Mapping[str, Any]) -> dict[str, Any]:
    """What the publisher reads: how many findings need an answer, and the body."""
    return {
        "schema_version": PUBLICATION_VERSION,
        "needs_answer": len(needing_answer(document)),
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
    left_out = [f for f in findings if f["kind"] == LEFT_OUT]
    sections: list[str] = []
    for title, lead, found, show_kind, group in (
        ("Stale: an anchor changed after the revalidation point", None, stale, False, ANSWER),
        ("Other findings that need an answer", OTHER, other, True, ANSWER),
        (
            "Deferred: answered with a reason, and holding nothing open",
            None,
            deferred,
            False,
            LISTED,
        ),
        ("Reported, nothing owed", None, left_out, True, LISTED),
    ):
        if found:
            sections += [f"### {title}", "", *([lead, ""] if lead else [])]
            sections += cut([_finding(f, show_kind) for f in found], group)
            sections.append("")
    sections += ["### Measures: reported, never failed (COR-050 point 8)", ""]
    sections += _measures(cast("Mapping[str, Any]", document["measures"]), cut)
    return _joined([_headline(stale, other), "", INTRO, "", *cut.notice(), *sections])


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


def _headline(stale: Sequence[Any], other: Sequence[Any]) -> str:
    if not stale and not other:
        return "**Nothing needs an answer.**"
    parts = [
        *([f"{len(stale)} stale"] if stale else []),
        *([f"{len(other)} other finding{'' if len(other) == 1 else 's'}"] if other else []),
    ]
    return f"**Needs an answer: {', '.join(parts)}.**"


def _finding(finding: Mapping[str, Any], show_kind: bool) -> str:
    """One finding: where, which anchor, since when — then what the check says of it."""
    head = [_code(str(finding.get("location") or finding.get("artefact") or "?"))]
    if show_kind:
        head.append(_code(str(finding["kind"])))
    anchor = finding.get("anchor")
    if isinstance(anchor, Mapping):
        named = cast("Mapping[str, Any]", anchor)
        head.append(_code(f"{named.get('kind')}:{named.get('value')}"))
    origin = finding.get("origin")
    if isinstance(origin, Mapping):
        date = cast("Mapping[str, Any]", origin).get("date")
        if isinstance(date, str):
            head.append(f"since {_code(_day(date))}")
    said = (
        OVER_BROAD_SAID
        if finding["kind"] == OVER_BROAD
        else _code(str(finding.get("message") or ""))
    )
    return f"- {' · '.join(head)}\n  {said}"


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
        help="Print the publication {schema_version, needs_answer, body}.",
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
