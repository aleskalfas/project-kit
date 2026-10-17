"""A use case's steps and variants stay append-only (DEC-001 point 3).

Inside a use case, steps are numbered and variants are lettered after the step
they branch from. Journeys and evidence cite a step or a variant by its number
or its letter, so renumbering one silently points every citation at another.
This check keeps them append-only. It is the second check of `pkit analysis
check-numbers`, beside its check of a number two branches took
(`_lib/numbers.py`): both guard one promise, that a number, once given, never
changes meaning.

- **What it compares.** Each use case in the working tree, with the same use
  case as the base held it where this branch left it: the merge-base the
  backbone names in `pkit repository base --json` (COR-054 points 3 and 5), the
  reading `check-numbers` already holds. So it answers about the change, as the
  friction change check does, and what the default branch did since is not
  this change's. A use case is known by its id, never by its path, so one moved
  into an area is compared too. A use case the merge-base does not hold is new
  in the change, has nothing to compare, and passes.
- **What it reads.** A use case's steps are the numbered items of the part
  whose form lists steps, its *Main path*, and its variants the lettered items
  of its *Variants* part. Both are found as the structure check finds a part
  and reads its list (`structure.parts`, `_lib/forms.py`), with a use-case kind
  of this check's making (`_kind`): the shipped one as the project's own
  structures relabel it, a part found by its shipped label too, and a label any
  of the project's groups adds, whatever its rule, ending the part before it.
  Both sides are read with that one kind. A step is known by its number, a
  variant by its step's number and its letter, in either case. Its text is what
  follows, white space folded. The text at the merge-base is read from the
  clone alone (`backbone.text_at`).
- **What it reports,** for each step or variant the merge-base held:
  - **renumbered:** its text stands under another number or letter, one the
    merge-base did not give that text, and no longer under its own;
  - **removed:** the working tree holds neither its number or letter, nor its
    text under another.
- **What passes.** A step or a variant added passes, whatever new number or
  letter it takes, after the last or between two. So does one whose number now
  holds other text and whose own text stands nowhere else: an edit, since the
  check cannot tell a reworded step from another one. A step that no longer
  happens stays under its number, as RS-SAN-002 says. The check matches text
  alone, so it misses a step renumbered and reworded at once whose number still
  holds a step. And it reads a new step that repeats, word for word, the old
  text of a step this change rewords as that step renumbered.
- **Where it binds.** Where the append-only rule, RS-SAN-002, binds on the use
  case in the working tree, and at its status, as the structure check holds a
  body where the format rule binds (`_lib/check.py`): the backbone's one
  reading of where a rule binds, `pkit rule-sets reach` (COR-051 point 7).
  Accepted, each finding is an error. Under any other status nothing is
  compared, unless a preview is asked for and the rule is proposed: then it is
  compared where `pkit rule-sets reach --preview` says the rule would bind,
  and each finding is a report opening `preview:`, which never fails. The
  summary counts the use cases the rule does not bind on. `SAN` declares this
  check under the rule's `checks` (COR-051 point 2).
- **Not a validator.** It reads the base, so it answers about a change rather
  than the tree, and `pkit analysis validate` never runs it (COR-055 point 2).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from _lib import backbone, forms, project_structure, structure
from _lib.check import ACCEPTED, PREVIEW, PROPOSED, unchecked
from _lib.findings import ERROR, REPORT, Finding
from _lib.model import (
    CAPABILITY,
    STEPS_RULE,
    USE_CASE,
    Analysis,
    Artefact,
    Unreadable,
    identity,
)

#: What the summary line about this check opens with.
SUBJECT = "steps"

#: The append-only rule as the backbone's reading of where rules bind cites it, with
#: the capability's name in front (COR-051 point 6).
CITED_STEPS_RULE = f"{CAPABILITY}:{STEPS_RULE}"

#: How a step or a variant the merge-base held departs from it.
RENUMBERED, REMOVED = "renumbered", "removed"

#: How a renumbered or removed step, or variant, is put right, as the check says it.
_STEP_FIX = {
    RENUMBERED: (
        "give it back its number, and number a new step higher than every number of its use case"
    ),
    REMOVED: "put it back under its number, even if it no longer happens",
}
_VARIANT_FIX = {
    RENUMBERED: "give it back its label, and letter a new variant after every letter of its step",
    REMOVED: "put it back under its label, even if it no longer happens",
}


@dataclass(frozen=True)
class Item:
    """A step or a variant as a body gives it: its number or label, the line it opens on,
    and its text after the number or label, white space folded."""

    key: str
    line: int
    text: str


@dataclass(frozen=True)
class Read:
    """A use case's steps and variants, each in the body's order."""

    steps: tuple[Item, ...] = ()
    variants: tuple[Item, ...] = ()


def compare(
    root: Path,
    analysis: Analysis,
    ref: str,
    fork: str,
    before: Callable[[], Analysis],
    *,
    preview: bool = False,
    reach: Callable[..., Mapping[str, Mapping[str, bool]]] = backbone.reach,
) -> tuple[list[str], list[Finding]]:
    """Each use case in the working tree at `root` against the same use case at `fork`,
    where this branch left the base `ref`, whose analysis `before` reads. Returns the
    summary's lines and the findings. Raises Unreadable when what the merge-base holds
    cannot be read."""
    use_cases = analysis.of_kind(USE_CASE)
    if not use_cases:
        return [f"{SUBJECT}: no use case here; nothing to compare."], []
    rules = analysis.method_rules
    status = None if rules is None else rules.get(STEPS_RULE)
    if status == ACCEPTED:
        severity, label = ERROR, ""
    elif status == PROPOSED and preview:
        severity, label = REPORT, PREVIEW
    else:
        said = unchecked(
            status,
            rules is None,
            preview,
            subject=SUBJECT,
            command="pkit analysis check-numbers",
            rule=STEPS_RULE,
        )
        return [said], []
    head = f"{SUBJECT} ({STEPS_RULE}, {status}{', previewed as accepted' if label else ''})"
    binds, binds_not = ("would bind", "would not bind") if label else ("binds", "does not bind")
    try:
        at = reach(root, preview=status != ACCEPTED)
    except Unreadable as exc:
        return [f"{head}: not checked — where the rule {binds} cannot be read."], [
            Finding(
                severity,
                analysis.location or ".",
                f"{label}where {STEPS_RULE} {binds} cannot be read: {exc}. No use case's steps "
                f"and variants are compared until it can (COR-051 point 7)",
            )
        ]
    bound = [u for u in use_cases if CITED_STEPS_RULE in (at.get(u.location) or {})]
    unbound = len(use_cases) - len(bound)
    unbound_said = (
        f" The rule {binds_not} on {unbound} of the {len(use_cases)} use case(s) here, so they "
        f"are not compared."
        if unbound
        else ""
    )
    if not bound:
        return [f"{head}: nothing compared.{unbound_said}"], []
    try:
        kind = _kind(root)
    except _NoKind as exc:
        return [f"{head}: not checked — {exc.summary}{unbound_said}"], [
            Finding(severity, exc.location, label + exc.message)
        ]

    earlier = before()
    fork_short = fork[: backbone.SHORT]
    found: list[Finding] = []
    new = departing = 0
    for use_case in sorted(bound, key=lambda u: u.path):
        was = _held(earlier, use_case)
        if was is None:
            new += 1
            continue
        try:
            now = (root / use_case.path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # the core reports a file it cannot read
        try:
            then = backbone.text_at(root, fork, was.path)
        except backbone.GitFailed as exc:
            raise Unreadable(
                f"this clone lacks {was.path} where this branch left it, at {fork_short}: {exc}. "
                f"Nothing is fetched here, so a partial clone must hold that file"
            ) from exc
        changed = _changes(use_case, read(then, kind), read(now, kind), ref, fork_short)
        departing += bool(changed)
        found += [Finding(severity, use_case.path, label + message) for message in changed]
    where = "would bind, as `pkit rule-sets reach --preview` reads it" if label else "binds"
    never = ", reported and never failing" if label else ""
    line = (
        f"{head}: {len(bound)} use case(s) where the rule {where}, compared with {ref} where "
        f"this branch left it ({fork_short}); {new} new in this change, and {departing} "
        f"renumbering or removing a step or a variant{never}.{unbound_said}"
    )
    return [line], found


def read(text: str, kind: structure.Kind) -> Read:
    """A use case's steps and variants, from its file's `text`, as `kind` gives its parts:
    the part whose form lists steps, and the part of the `variants` form, each as the
    kind ships it, not one a project adds."""
    steps: list[Item] = []
    variants: list[Item] = []
    for element, part in structure.parts(structure.body_lines(text), kind):
        if element.added:
            continue
        if element.form in forms.STEP_FORMS and not steps:
            steps = [Item(str(n), item.line, said) for n, item, said in forms.steps(part)]
        elif element.form == forms.VARIANTS and not variants:
            variants = [Item(key, item.line, said) for key, item, said in forms.variants(part)]
    return Read(tuple(steps), tuple(variants))


def _changes(use_case: Artefact, then: Read, now: Read, ref: str, fork: str) -> list[str]:
    """What the working tree did to each step and variant the merge-base held: each one
    renumbered or removed, as a message."""
    messages: list[str] = []
    for noun, was, is_now, fix in (
        ("step", then.steps, now.steps, _STEP_FIX),
        ("variant", then.variants, now.variants, _VARIANT_FIX),
    ):
        for key, how, moved in _departures(was, is_now):
            held = f"{use_case.id}'s {noun} {key}, as {ref} held it where this branch left it"
            held += f" ({fork}),"
            if moved is not None:
                happened = f"{held} now stands as {noun} {moved.key}, at line {moved.line}"
            else:
                happened = f"{held} is gone"
            messages.append(
                f"{happened}: journeys and evidence cite a {noun} by its "
                f"{'number' if noun == 'step' else 'step and letter'}, so it is never "
                f"renumbered or removed — {fix[how]} (DEC-001 point 3)"
            )
    return messages


def _departures(was: Sequence[Item], now: Sequence[Item]) -> list[tuple[str, str, Item | None]]:
    """Each item of `was` that `now` renumbered or removed: its key, how, and the item that
    now holds its text, if any."""
    then_by_key = _first_by_key(was)
    now_by_key = _first_by_key(now)
    then_text = {key: item.text for key, item in then_by_key.items()}
    found: list[tuple[str, str, Item | None]] = []
    for key, item in then_by_key.items():
        same = now_by_key.get(key)
        if same is not None and same.text == item.text:
            continue
        # Its text under another key, one the merge-base did not give that text.
        moved = next(
            (
                other
                for other in now
                if item.text
                and other.key != key
                and other.text == item.text
                and then_text.get(other.key) != item.text
            ),
            None,
        )
        if moved is not None:
            found.append((key, RENUMBERED, moved))
        elif same is None:
            found.append((key, REMOVED, None))
    return found


def _first_by_key(items: Sequence[Item]) -> dict[str, Item]:
    """Each key's first item: a number or label written twice is the structure check's."""
    found: dict[str, Item] = {}
    for item in items:
        found.setdefault(item.key, item)
    return found


def _held(earlier: Analysis, use_case: Artefact) -> Artefact | None:
    """The use case the merge-base held under the same id, as `identity` spells it — the
    one at the same path where two hold it — or `None`: new in the change."""
    if not use_case.id:
        return None
    same = [
        a for a in earlier.of_kind(USE_CASE) if a.id and identity(a.id) == identity(use_case.id)
    ]
    return next((a for a in same if a.path == use_case.path), same[0] if same else None)


class _NoKind(Exception):
    """The use-case kind cannot be read: the summary's words, and a finding's location and
    message."""

    def __init__(self, summary: str, location: str, message: str) -> None:
        super().__init__(message)
        self.summary = summary
        self.location = location
        self.message = message


def _kind(root: Path) -> structure.Kind:
    """The use-case kind its steps and variants are read with: as shipped, relabelled by the
    project's own structures, each label any of the project's groups adds ending the part
    before it, and a part found by its shipped label too. Raises `_NoKind` when the
    declaration or the project's file cannot be read."""
    try:
        kinds = structure.read_kinds()
    except structure.Unreadable as exc:
        raise _NoKind(
            "the declaration cannot be read.",
            _shown(structure.KINDS_FILE, root),
            f"the kinds' structures cannot be read: {exc}. No use case's steps and variants "
            f"are compared until they can (DEC-001 point 1)",
        ) from exc
    own = project_structure.read(root, kinds)
    if own.problems:
        raise _NoKind(
            f"the project's own structures, {project_structure.FILE}, cannot be read; "
            f"`pkit analysis validate` says why.",
            project_structure.FILE,
            "the project's own structures cannot be read, so no use case's steps and variants "
            "are compared until they can: `pkit analysis validate` says why (DEC-001 point 1)",
        )
    groups = own.of(USE_CASE)
    kind = project_structure.tightened(
        project_structure.relabelled(kinds[USE_CASE], own), groups, (), groups
    )
    return dataclasses.replace(kind, as_written=True)


def _shown(path: Path, root: Path) -> str:
    """A path as a finding locates it: relative to the project root where it lies under it."""
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
