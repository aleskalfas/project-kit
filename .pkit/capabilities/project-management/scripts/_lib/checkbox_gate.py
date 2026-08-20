"""The DEC-007 checkbox close-gate — one implementation, every call site.

Markdown checkboxes are lifecycle-gating (project-management:DEC-007): an issue
carrying an unticked `- [ ]` box cannot transition to Done. That single rule is
reached from four independent places —

  * `close-issue`'s won't-do close and its cascade-eligibility close,
  * `done-work`'s pre-flight, run BEFORE the squash-merge is authorised
    (GitHub's `Closes #N` auto-closes the issue *on* merge, so a check after
    the merge gates nothing — DEC-007 words the PR-merge path that way for
    exactly this reason),
  * `merge-pr`'s sweep over every issue a PR closes, plus the PR's own body,
  * the process engine's `gate-checkboxes-ticked` predicate (via
    `lifecycle_predicates`),

— and it used to be written out separately at each of them. This module is the
single home for both halves of the rule: what counts as an unticked box, and
how a refusal reads. A call site supplies only its own remedy wording, because
what the operator should do next differs by path (tick before closing / before
merging / not skippable at all).
"""

from __future__ import annotations

import re

# A line is an unticked box when it is `- [ ]` (or `* [ ]`) followed by real
# content. A BARE `- [ ]` deliberately does not match: an item with no text is
# an unauthored skeleton, not a claim awaiting validation, and it is
# `placeholder_detection`'s signal to report — not this gate's.
_UNTICKED_RE = re.compile(r"^\s*[-*]\s+\[\s\]\s+\S")


def unticked_boxes(body: str | None) -> list[str]:
    """The stripped source lines of every unticked checkbox in *body*.

    A missing body (`None`, as `gh`'s JSON gives for an empty one) carries no
    boxes rather than raising.
    """
    return [
        line.strip()
        for line in (body or "").splitlines()
        if _UNTICKED_RE.match(line)
    ]


def all_boxes_ticked(body: str | None) -> bool:
    """True when *body* has no unticked checkbox.

    A body with no checkboxes at all is ticked-complete: DEC-007's gate applies
    only when boxes exist ("Bodies that genuinely have no checkboxes are
    unaffected").
    """
    return not unticked_boxes(body)


def refusal_message(unticked: list[str], *, remedy: str, scope: str = "") -> str:
    """Render the gate's refusal: header, one line per unticked box, remedy.

    *scope* qualifies the header when a path needs to name which gate refused
    (e.g. the cascade-eligibility variant); *remedy* is the path's own "what to
    do next" sentence.
    """
    header = "[refused] DEC-007 checkbox close-gate"
    if scope:
        header = f"{header} ({scope})"
    lines = [f"{header}:"]
    lines += [f"  - {box}" for box in unticked]
    lines += ["", f"  → {remedy}"]
    return "\n".join(lines)
