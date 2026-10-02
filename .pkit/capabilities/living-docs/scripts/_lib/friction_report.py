"""The whole-repository friction check's findings, rendered for the people who answer them.

The change check guards a pull request. Friction no pull request touches — an
anchor changed outside its artefact's own change, debt older than the gate — is
found only by the whole-repository check (COR-050 point 6), which reports and
never fails (point 12). This module renders that check's machine-readable
document, `pkit friction check --all --json`, as one Markdown body a project
publishes where a person reads it, and says how much of it is outstanding, so
whoever publishes it knows whether anything is left to answer. It reads the
backbone's document and nothing else, as COR-050's Implications have a
component consume it, and it publishes nothing itself.

- **Outstanding** is every finding the check reports except `left-out`, which
  it reports and never owes: stale and deferred debt — a deferral postpones
  friction and is still debt (point 9) — dead anchors, unresolved kinds,
  over-broad anchors, unreadable front matter, and artefacts a shallow clone
  could not judge. The two measures (point 8) are rendered and never
  outstanding: they say what remains to anchor, not friction to answer, and a
  project starts with every artefact unanchored.
- **The same findings, the same body.** The body is a function of the document
  alone — no age, no run time, no HEAD — so a publisher that compares bodies
  changes nothing when nothing changed. A finding says since when by its
  origin's date; its age is counted from that.
- **Inert text.** What the document carries — paths, anchors, messages, deferral
  reasons, commit subjects — is set in code spans, so a reason naming
  `@someone` or `#123` notifies and links nobody, and none of it can break the
  body's structure.
- **Within a body's size.** Trackers cap a body (GitHub at 65 536 characters).
  Every list is shortened alike until the body fits `BUDGET`, each ending with
  how many more the check lists.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

#: The version of the publication `publication` answers.
SCHEMA_VERSION = 1

#: The findings that have a section of their own, in this order; every other kind
#: the check owes is rendered under "Other findings".
STALE = "stale"
DEFERRED = "deferred"

#: The kinds the check reports and never owes (the CLI reference, "Friction
#: checks"): rendered apart, and never outstanding.
NOT_OWED = frozenset({"left-out"})

#: The size a body keeps within: GitHub caps an issue body at 65 536 characters,
#: and a publisher adds lines of its own.
BUDGET = 60_000

#: The longest each list is shortened to, tried in turn until the body fits `BUDGET`.
LIMITS: tuple[int | None, ...] = (None, 100, 30, 10, 3)

INTRO = (
    "The whole-repository friction check (COR-050 point 6) judges every artefact in the "
    "declared places against the current history, and finds the friction no pull request "
    "answers. It reports and never fails anything. `pkit friction check --all` gives this "
    "report from HEAD, `pkit friction explain <artefact>` what clears one artefact's "
    "friction, and `pkit friction debt` the debt, oldest first."
)
DORMANT = (
    "The check is dormant: no place is declared, so nothing is anchored and nothing is "
    "demanded (COR-050 point 15)."
)
MORE = "`pkit friction check --all` lists them all"
CUT = "_The report is cut here to fit the body's size; `pkit friction check --all` gives it whole._"


def outstanding(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The findings of `document` still to answer: all but those never owed."""
    if document.get("dormant"):
        return []
    return [f for f in _findings(document) if f.get("kind") not in NOT_OWED]


def publication(document: Mapping[str, Any]) -> dict[str, Any]:
    """What a publisher reads: how many findings are outstanding, and the body."""
    return {
        "schema_version": SCHEMA_VERSION,
        "outstanding": len(outstanding(document)),
        "body": body(document),
    }


def body(document: Mapping[str, Any]) -> str:
    """The body, its lists shortened alike until it fits `BUDGET`; cut at a line if
    even the shortest lists do not fit."""
    text = ""
    for limit in LIMITS:
        text = render(document, limit=limit)
        if len(text) <= BUDGET:
            return text
    return text[:BUDGET].rsplit("\n", 1)[0] + f"\n\n{CUT}\n"


def render(document: Mapping[str, Any], *, limit: int | None = None) -> str:
    """The body, each list holding at most `limit` entries (all of them for `None`)."""
    owed = outstanding(document)
    lines = [_headline(owed), "", INTRO, ""]
    if document.get("dormant"):
        return _joined([*lines, DORMANT])
    stale = [f for f in owed if f.get("kind") == STALE]
    deferred = [f for f in owed if f.get("kind") == DEFERRED]
    other = [f for f in owed if f.get("kind") not in (STALE, DEFERRED)]
    not_owed = [f for f in _findings(document) if f.get("kind") in NOT_OWED]
    for title, findings, show_kind in (
        ("Stale: an anchor changed after the revalidation point", stale, False),
        ("Deferred: friction postponed, with its reason", deferred, False),
        ("Other findings", other, True),
        ("Reported, nothing owed", not_owed, True),
    ):
        if findings:
            lines += [f"### {title}", ""]
            lines += _capped([_finding(f, show_kind) for f in findings], limit)
            lines.append("")
    lines += ["### Measures: reported, never failed (COR-050 point 8)", ""]
    lines += _measures(document.get("measures") or {}, limit)
    return _joined(lines)


def _headline(owed: Sequence[Mapping[str, Any]]) -> str:
    if not owed:
        return "**Nothing outstanding.**"
    stale = sum(1 for f in owed if f.get("kind") == STALE)
    deferred = sum(1 for f in owed if f.get("kind") == DEFERRED)
    other = len(owed) - stale - deferred
    parts = [
        *([f"{stale} stale"] if stale else []),
        *([f"{deferred} deferred"] if deferred else []),
        *([f"{other} other finding{'' if other == 1 else 's'}"] if other else []),
    ]
    return f"**Outstanding: {', '.join(parts)}.**"


def _finding(finding: Mapping[str, Any], show_kind: bool) -> str:
    """One finding: where, which anchor, since when — then what the check says of it."""
    head = [_code(str(finding.get("location") or finding.get("artefact") or "?"))]
    if show_kind:
        head.append(_code(str(finding.get("kind"))))
    anchor = finding.get("anchor")
    if isinstance(anchor, Mapping):
        head.append(_code(f"{anchor.get('kind')}:{anchor.get('value')}"))
    origin = finding.get("origin")
    if isinstance(origin, Mapping) and isinstance(origin.get("date"), str):
        head.append(f"since {origin['date'][:10]}")
    return f"- {' · '.join(head)}\n  {_code(str(finding.get('message') or ''))}"


def _measures(measures: Mapping[str, Any], limit: int | None) -> list[str]:
    unanchored = [str(p) for p in measures.get("unanchored") or []]
    accepted = [a for a in measures.get("accepted_unanchored") or [] if isinstance(a, Mapping)]
    surface = [str(p) for p in measures.get("uncovered_surface") or []]
    lines: list[str] = []
    if unanchored or accepted:
        apart = f" ({len(accepted)} accepted with a reason, listed apart)" if accepted else ""
        lines += [
            "<details>",
            f"<summary>Unanchored artefacts: {len(unanchored)}{apart}</summary>",
            "",
            *_capped([f"- {_code(p)}" for p in unanchored], limit),
        ]
        if accepted:
            listed = [
                f"- {_code(str(a.get('location')))}: {_code(str(a.get('reason') or ''))}"
                for a in accepted
            ]
            lines += ["", "Accepted with a reason:", "", *_capped(listed, limit)]
        lines += ["", "</details>", ""]
    else:
        lines += ["Unanchored artefacts: none.", ""]
    if surface:
        lines += [
            "<details>",
            f"<summary>Uncovered surface: {len(surface)} "
            f"path{'' if len(surface) == 1 else 's'} nothing anchors</summary>",
            "",
            *_capped([f"- {_code(p)}" for p in surface], limit),
            "",
            "</details>",
        ]
    else:
        lines.append("Uncovered surface: none.")
    return lines


def _capped(entries: Sequence[str], limit: int | None) -> list[str]:
    if limit is None or len(entries) <= limit:
        return list(entries)
    return [*entries[:limit], f"- … and {len(entries) - limit} more: {MORE}"]


def _code(text: str) -> str:
    """`text` as one inline code span, whatever backticks it holds (CommonMark: a
    fence one backtick longer than its longest run, padded where it touches one)."""
    text = " ".join(text.split())
    if not text:
        return ""
    fence = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _findings(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [f for f in document.get("findings") or [] if isinstance(f, Mapping)]


def _joined(lines: Sequence[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"
