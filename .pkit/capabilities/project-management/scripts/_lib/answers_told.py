"""What the person who authorises the merge is told at one head (DEC-065 points 2
and 4).

The landing command and `show-pr --field answers` tell the same lines, so neither
feeds `friction_answers.told` itself. `at_head` feeds it for both: it derives the
answers, reads the change to the fixers' grant list, reads the author's sentences
and builds what `told` adds last. It stops nothing and prints nothing. What could
not be read it hands back (`AnswersTold`), since the landing command refuses in its
own words and the view reports in its own.

It lives apart from `friction_answers`, which also loads standalone by path, where
`fixers` cannot.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from _lib import fixers, friction_answers


@dataclass(frozen=True)
class AnswersTold:
    """What was read at one head, and the lines told from it. `derived.document` is
    None where the answers could not be derived, and `grants` says why where the
    grant list could not be read: either way nothing is told, and no description
    was read."""

    derived: friction_answers.Derivation
    grants: tuple[fixers.GrantChange, ...] | fixers.ChangeUnread = ()
    body: str = ""
    sentences: Mapping[str, str] = field(default_factory=dict)
    told: tuple[str, ...] = ()


def at_head(
    head: str,
    base: str,
    capability_root: Path,
    read_body: Callable[[], str],
    *,
    source: friction_answers.Source | None = None,
    from_checkout: bool = True,
) -> AnswersTold:
    """The answers derived at commit `head` against the branch `base`, the grant
    list's change from where the head left its base, the author's sentences in the
    description `read_body` gives, and what the person is told from them.

    `read_body` runs last, once the rest was read, so a caller that reads the
    description from the host holds it for no longer than it must. `from_checkout`
    is `friction_answers.checked`'s: the view passes False, and so starts
    no program the head holds."""
    derived = friction_answers.derive(head, base, source=source, from_checkout=from_checkout)
    if derived.document is None:
        return AnswersTold(derived)
    grants = fixers.change_between(derived.merge_base, head, capability_root)
    if isinstance(grants, fixers.ChangeUnread):
        return AnswersTold(derived, grants)
    body = read_body()
    sentences = friction_answers.sentences(body)
    told = friction_answers.told(
        derived.document, derived.settings, sentences, [change.said() for change in grants]
    )
    return AnswersTold(derived, grants, body, sentences, tuple(told))
