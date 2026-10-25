"""The friction writers: `revalidate`, `defer`, `revisit`, `record-status` (COR-050 points 3, 4,
10, 13 and 16).

Reading never writes; writing is always one of these four explicit
commands, each naming what it writes and writing only with consent (point 13):

- `revalidate` rewrites the `revalidated` block: a fresh `at`, the outcome,
  and — for `unchanged` — an `unchanged-because` that must differ from the one
  already written (point 3), and that holds no placeholder left unfilled. It
  re-states the deferrals the person keeps: each kept one is named on the
  command line (`--keep`) or confirmed at the prompt; every other entry is
  removed (point 4).
- `defer` writes the `deferred` list inside `revalidated` — one entry added,
  or an existing entry's reason reworded — and never touches `at`: a deferral
  is not a revalidation (point 4). An anchor the artefact does not carry is
  refused, and so is a reason that holds a placeholder left unfilled.
- `revisit` writes the `revisited` list — the entry for one target of a link
  the artefact's places declare, added or rewritten, with its outcome,
  `unchanged` or `deferred`, and its reason — and never touches `at`: an
  entry is no revalidation of the source (point 16). A target no link of the
  artefact lists is refused, and so is a reason that holds a placeholder.
- `record-status` writes the tool-written `last-check` block from the
  whole-repository check at HEAD, only when the state it records changes
  (point 10): `as-of` moving on alone is no change, so a status that holds is
  never rewritten.

**Where an answer is written** (COR-062 points 1, 4 and 10; ADR-068 point 3). An
artefact whose block holds no answer — no `revalidated` block and no `revisited`
list — gets `revalidate`'s, `defer`'s and `revisit`'s answer in an answer file of
the change's own (`_OwnFile`): the one answer file in the working tree that no
commit of the checkout holds, else a new one named for its UTC time and eight
random hexadecimal digits. Its entry for the artefact names, in `read`, every
other answer file present that answers the artefact. Two such uncommitted files
that each answer the artefact refuse the write, naming both. A revalidation
re-states the deferrals it keeps in its own entry. An artefact whose block holds
an answer gets it in the block, as below, until the move takes every answer out of
the blocks (`friction_move`): an artefact is read from one home, and written in
it. `record-status` always writes the block: `last-check` is status, not an
answer. An artefact the project receives by sync is refused: it owes the project
no answer (point 9).

**Only the block changes.** Each writer replaces one key of the artefact's
`friction` block — the lines from that key through the end of its value, or,
in a block written in flow style, that key's characters — and leaves every
other byte of the file as it was. Before anything is written the result is
read back: the front matter must parse to exactly what it held with that one
key replaced, and the artefact must pass validation's per-artefact judgments
(`friction_validate.block_findings`), so a writer never writes what `pkit
validate` would refuse. The edit is made in the file read with `\\n` line
breaks, as discovery reads it, and written back in the one line break the
file is written with — a `\\r\\n` file stays one, byte for byte outside the
key; a file that mixes them is refused, since no one line break would keep
its other bytes, and validation reports it. Entries are kept in one order — deferrals by anchor
kind, then value; keys in the schema's order (`anchors`, `unanchored-because`,
`revalidated`, `revisited`, `last-check`; `at`, `outcome`, `unchanged-because`,
`deferred`) — so the same input always writes the same bytes.

**Consent.** `--yes`; or, on a terminal, a confirmation shown with the diff;
`--dry-run` shows the diff and writes nothing; a non-interactive run with
neither refuses, writes nothing, and names the command to run — the consent
rule of the configuration writer (COR-048 point 5), applied to the project's
own artefacts. `record-status` names it with `--dry-run` and with `--yes`;
`revalidate`, `defer` and `revisit` name only the dry run and print no
ready-made `--yes` command: an answer on an artefact may be a person's
decision (point 3).
"""

from __future__ import annotations

import copy
import difflib
import io
import json
import os
import re
import shlex
import stat
import tempfile
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple, cast

import click
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from project_kit import answer_files as af
from project_kit import backbone_schemas as bs
from project_kit import cli_render
from project_kit import friction_repository as fr
from project_kit.answer_files import block_holds_answers
from project_kit.document_parts import split_front_matter
from project_kit.friction_check import REVISIT_OUTCOMES, anchors_of, parsed_at
from project_kit.friction_discovery import (
    FRICTION_KEY,
    REVISITED_KEY,
    RULES_KEY,
    UNANCHORED_BECAUSE_KEY,
    Anchor,
    Artefact,
    ArtefactKind,
    Discovery,
    RevisitLink,
    discover_artefacts,
    held_message,
    line_break,
    link_targets,
    links_said,
    parse_artefacts,
)
from project_kit.friction_validate import Severity, block_findings
from project_kit.line_breaks import universal_newlines
from project_kit.project_config import stdin_is_tty

# The keys of the block this module writes (COR-050 points 3, 4 and 10).
REVALIDATED = "revalidated"
DEFERRED = "deferred"
LAST_CHECK = "last-check"
AT = "at"
OUTCOME = "outcome"
BECAUSE = "unchanged-because"

#: The two outcomes of a revalidation (COR-050 point 3).
OUTCOMES: tuple[str, ...] = ("updated", "unchanged")
UNCHANGED = "unchanged"

# Where each key goes among its siblings: the schema's order, per parent.
_KEY_ORDER: dict[str, tuple[str, ...]] = {
    FRICTION_KEY: ("anchors", UNANCHORED_BECAUSE_KEY, REVALIDATED, REVISITED_KEY, LAST_CHECK),
    REVALIDATED: (AT, OUTCOME, BECAUSE, DEFERRED),
}

# `at` as the schema's `utc-timestamp` wants it, and the pattern that reads it.
_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_UTC_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")

# How much of a commit the summary shows.
_SHORT = 12

#: A placeholder: words in angle brackets, as a command shown for a person to run
#: writes what they supply — `<why the content still holds>`. A justification or a
#: reason still holding one says nothing, so the writers refuse it. A word with no
#: space in its brackets (`Vec<u8>`) or opening in capitals (`Map<String, int>`) is
#: code, not a placeholder.
PLACEHOLDER = re.compile(r"<[a-z][^<>\n]*\s[^<>\n]*>")

_safe = YAML(typ="safe")


class FrictionWriteError(click.ClickException):
    """A writer refused: nothing was written."""


class FileNotReplaced(FrictionWriteError):
    """`replace_file` refused one file; `reason` says why, for a caller writing several."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"{reason} Nothing was written.")
        self.reason = reason


class ConsentRefused(click.ClickException):
    """Nobody could consent: not a terminal, and neither `--yes` nor `--dry-run` (point 13)."""


# --- the artefact ------------------------------------------------------------------


def find_artefact(target_root: Path, reference: str) -> Artefact:
    """The one artefact in the declared places that `reference` names (`locate_artefact`)."""
    return locate_artefact(target_root, reference)[0]


def locate_artefact(target_root: Path, reference: str) -> tuple[Artefact, tuple[RevisitLink, ...]]:
    """The one artefact in the declared places that `reference` names, and the links its
    places declare whose source's change revisits their targets (COR-050 point 16).

    Its location first — `path` for a document, `path#id` for a collection
    entry — then any identifier an artefact anchor may use (its id; a
    document's path; a method rule's `<component>:<id>`). A reference naming
    none, or more than one, is refused with what it could have meant — and one
    naming a document a component holds says whose it is: a held document is
    no artefact, and carries no block to write (COR-050 point 1).
    """
    found, links, _discovery = _locate(target_root, reference)
    return found, links


def _locate(
    target_root: Path, reference: str
) -> tuple[Artefact, tuple[RevisitLink, ...], Discovery]:
    """`locate_artefact`, with the discovery it read."""
    discovery = discover_artefacts(target_root)
    held = discovery.holding(reference.split("#", 1)[0])
    if held is not None:
        raise FrictionWriteError(f"{held_message(held)} Nothing was written.")
    if not discovery.places:
        raise FrictionWriteError(
            "no places are declared (`friction.places` in .pkit/project/config.yaml, or a "
            "capability's), so no artefact can be written to. Nothing was written."
        )
    file_part = reference.split("#", 1)[0]
    for unreadable in discovery.unreadable:
        if unreadable.path == file_part:
            raise FrictionWriteError(
                f"{unreadable.path}: front matter does not parse ({unreadable.reason}); fix it "
                f"first — `pkit validate` reports it. Nothing was written."
            )
    matches = [a for a in discovery.artefacts if a.location == reference] or [
        a for a in discovery.artefacts if reference in a.identifiers
    ]
    if len(matches) > 1:
        listed = ", ".join(a.location for a in matches)
        raise FrictionWriteError(
            f"{reference!r} names {len(matches)} artefacts ({listed}); name one by its "
            f"location. Nothing was written."
        )
    if not matches:
        in_file = [a.location for a in discovery.artefacts if a.path == file_part]
        hint = f" The file holds {', '.join(in_file)}." if in_file else ""
        raise FrictionWriteError(
            f"no artefact in the declared places is named {reference!r} — give its location "
            f"(`path`, or `path#id` for a collection entry) or its id.{hint} Nothing was written."
        )
    return matches[0], discovery.links(matches[0]), discovery


@dataclass(frozen=True)
class _Source:
    """The artefact's file as read for the edit, and the artefact re-read from exactly that text.

    `written` is the file as it is on disk; `text` the same file with its line
    breaks read as `\\n` (`universal_newlines`), which every edit is made in,
    and `newline` the one line break the file is written with, which
    `as_written` gives an edited text back.
    """

    rel: str  # the file, relative to the project root
    path: Path  # the file written — links resolved, so a link stays a link
    written: str
    text: str
    newline: str
    offset: int  # where the front matter's YAML starts in `text`
    front_matter: str
    artefact: Artefact
    links: tuple[RevisitLink, ...] = ()  # the links its places declare (COR-050 point 16)

    def as_written(self, text: str) -> str:
        """`text`, edited with `\\n` line breaks, in the line break the file is written with."""
        return text if self.newline == "\n" else text.replace("\n", self.newline)


def _read_source(
    target_root: Path, found: Artefact, links: tuple[RevisitLink, ...] = ()
) -> _Source:
    path = (target_root / found.path).resolve()
    try:
        written = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FrictionWriteError(f"cannot read {found.path}: {exc}. Nothing was written.") from exc
    newline = line_break(written)
    if newline is None:
        raise FrictionWriteError(
            f"{found.path} mixes line endings (`\\n` on some lines, `\\r\\n` or a lone `\\r` on "
            f"others); the writers keep every other byte of a file as it was, which no one line "
            f"ending would — write it with one first (`pkit validate` reports it). Nothing was "
            f"written."
        )
    text = universal_newlines(written)
    front_matter, _body = split_front_matter(text)
    artefacts, reason = parse_artefacts(found.path, found.place, text, rule_set=found.rule_set)
    same = [a for a in artefacts if a.kind is found.kind and a.id == found.id]
    if front_matter is None or reason is not None or len(same) != 1:
        raise FrictionWriteError(
            f"{found.location} changed while it was being read; run the command again. "
            f"Nothing was written."
        )
    return _Source(
        rel=found.path,
        path=path,
        written=written,
        text=text,
        newline=newline,
        offset=text.index("\n") + 1,
        front_matter=front_matter,
        artefact=same[0],
        links=links,
    )


def _friction_block(artefact: Artefact) -> Mapping[str, Any]:
    """The artefact's `friction` block, or a refusal naming what to do first."""
    if not artefact.has_friction_block:
        raise FrictionWriteError(
            f"{artefact.location} carries no `{FRICTION_KEY}` block in its `{bs.CONTAINER_KEY}` "
            f'container: declare its anchors there first (the schemas README, "The friction '
            f'block"). Nothing was written.'
        )
    if not isinstance(artefact.friction, Mapping):
        raise FrictionWriteError(
            f"{artefact.location}: its `{FRICTION_KEY}` block is not a mapping; fix it first — "
            f"`pkit validate` reports it. Nothing was written."
        )
    return artefact.friction


def carrier_keys(artefact: Artefact) -> tuple[str, ...]:
    """The keys from the front matter's root to the mapping that carries the container."""
    if artefact.kind is ArtefactKind.DOCUMENT:
        return ()
    if artefact.rule_set is not None:
        return (RULES_KEY, artefact.id)
    return (artefact.id,)


# --- anchors named on the command line ----------------------------------------------


def _named_anchor(text: str, carried: Sequence[Anchor], what: str) -> Anchor | None:
    """The anchor among `carried` that `text` names: `kind:value`, or a value only one carries.

    A value may hold colons itself (`software-analysis:DEC-001`), so the text
    is read as `kind:value` only when what precedes the first colon is the
    kind of a carried anchor with that value; otherwise it is a bare value.
    """
    kind, sep, value = text.partition(":")
    if sep:
        exact = [a for a in carried if a.kind == kind and a.value == value]
        if exact:
            return exact[0]
    by_value = [a for a in carried if a.value == text]
    if len(by_value) > 1:
        kinds = ", ".join(f"{a.kind}:{a.value}" for a in by_value)
        raise FrictionWriteError(
            f"{text!r} is the value of more than one {what} ({kinds}); name it as "
            f"`kind:value`. Nothing was written."
        )
    return by_value[0] if by_value else None


def _anchor_list(anchors: Sequence[Anchor]) -> str:
    return ", ".join(f"{a.kind}:{a.value}" for a in anchors) if anchors else "none"


def _sort_key(entry: Any) -> tuple[str, str]:
    """A deferral or revisit entry's place in its list: by anchor kind, then value (COR-050
    points 4 and 16)."""
    anchor = entry.get("anchor") if isinstance(entry, Mapping) else None
    if not isinstance(anchor, Mapping):
        return ("", "")
    return (str(anchor.get("kind", "")), str(anchor.get("value", "")))


def _entry_anchor(entry: Any) -> Anchor | None:
    """The anchor a deferral entry names, when it is written as texts `kind` and `value`."""
    anchor = entry.get("anchor") if isinstance(entry, Mapping) else None
    if isinstance(anchor, Mapping):
        kind, value = anchor.get("kind"), anchor.get("value")
        if isinstance(kind, str) and isinstance(value, str):
            return Anchor(kind, value)
    return None


def _entry_reason(entry: Any) -> str:
    reason = entry.get("reason") if isinstance(entry, Mapping) else None
    return reason if isinstance(reason, str) else ""


#: The keys of a deferral entry, and of a revisit entry, in the schema's order.
DEFERRAL_KEYS: tuple[str, ...] = ("anchor", "reason")
REVISIT_KEYS: tuple[str, ...] = ("anchor", "outcome", "reason")


def in_order(entry: Mapping[str, Any], keys: tuple[str, ...] = DEFERRAL_KEYS) -> dict[str, Any]:
    """A deferral entry — or, with `REVISIT_KEYS`, a revisit entry — with its keys in the
    schema's order, `anchor` (`kind`, `value`) first, and nothing dropped: a key the
    schema refuses stays, for validation to name."""

    def ordered(mapping: Mapping[str, Any], first: tuple[str, ...]) -> dict[str, Any]:
        head = {k: mapping[k] for k in first if k in mapping}
        return head | {k: v for k, v in mapping.items() if k not in first}

    out = ordered(entry, keys)
    if isinstance(out.get("anchor"), Mapping):
        out["anchor"] = ordered(out["anchor"], ("kind", "value"))
    return out


def _fold(text: Any) -> str | None:
    """Text with its whitespace folded — as the change check compares a justification."""
    return " ".join(text.split()) if isinstance(text, str) else None


# --- the plan ----------------------------------------------------------------------


@dataclass(frozen=True)
class Plan:
    """One write a command would make: the file before and after, and what it says it writes.

    `after == before` when there is nothing to write; `unchanged` then says
    why. `first_line` and `last_line` are the lines of the new file the
    written block occupies (1-based).
    """

    command: str
    artefact: str  # its location
    target: str  # what is written: a dotted path inside the carrier, or the answer's entry
    rel: str
    path: Path
    before: str
    after: str
    items: tuple[str, ...]  # what the write says, one line each
    first_line: int = 0
    last_line: int = 0
    unchanged: str | None = None
    notes: tuple[str, ...] = ()  # said before the write, never about it
    # Written into an answer file of the change's own (COR-062; ADR-068 point 3), which
    # the write adds where `creates`.
    answer_file: bool = False
    creates: bool = False

    @property
    def changes(self) -> bool:
        return self.after != self.before


def plan_revalidate(
    target_root: Path,
    reference: str,
    *,
    outcome: str,
    because: str | None = None,
    keep: Sequence[str] = (),
    confirm_keep: Callable[[Anchor, str], bool] | None = None,
    now: datetime | None = None,
) -> Plan:
    """The write of `pkit friction revalidate` (COR-050 points 3 and 4).

    The block is rewritten whole: `at` from `now` (a second later when that
    would equal the `at` written, since `at` changes on every revalidation),
    the outcome, the justification for `unchanged`, and the kept deferrals.
    A deferral is kept when `keep` names it or `confirm_keep` says so; the
    rest are removed. Refused: an unknown outcome, `unchanged` without a
    justification, with the one already written or with a placeholder left
    unfilled (`PLACEHOLDER`), a justification with `updated`, and keeping a
    deferral the artefact does not carry or whose anchor it no longer declares.
    """
    if outcome not in OUTCOMES:
        raise FrictionWriteError(f"the outcome is `updated` or `unchanged`, not {outcome!r}.")
    justification = because.strip() if isinstance(because, str) else None
    if outcome == UNCHANGED and not justification:
        raise FrictionWriteError(
            "`--outcome unchanged` needs `--because`: why the content still holds against this "
            "change — the one piece of judgment the tool cannot supply (COR-050 point 3). "
            "Nothing was written."
        )
    if outcome != UNCHANGED and because is not None:
        raise FrictionWriteError(
            "`--because` is the justification of an `unchanged` outcome; an `updated` "
            "revalidation carries none — its answer is the changed content. Nothing was written."
        )
    if justification:
        _filled(justification, "--because")

    source, discovery = _source(target_root, reference)
    artefact = source.artefact
    _friction_block(artefact)
    if not block_holds_answers(artefact):
        own = _own_file(target_root, source, discovery)
        return own.revalidate(
            outcome=outcome,
            justification=justification,
            keep=keep,
            confirm_keep=confirm_keep,
            now=now or datetime.now(UTC),
        )
    previous = artefact.revalidated if isinstance(artefact.revalidated, Mapping) else {}
    if outcome == UNCHANGED and _fold(justification) == _fold(previous.get(BECAUSE)):
        raise FrictionWriteError(
            "the justification is the one already written; `unchanged-because` must change "
            "with every revalidation — say why the content holds against *this* change "
            "(COR-050 point 3). Nothing was written."
        )

    stamp = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if parsed_at(artefact) == stamp:
        stamp += timedelta(seconds=1)
    at = stamp.strftime(_AT_FORMAT)

    kept, items = _kept_deferrals(artefact, previous, keep, confirm_keep)
    value: dict[str, Any] = {AT: at, OUTCOME: outcome}
    if outcome == UNCHANGED:
        value[BECAUSE] = justification
    if kept:
        value[DEFERRED] = kept

    was = previous.get(AT)
    lines = [
        f"at: {at}" + (f"   (was {was})" if isinstance(was, str) else ""),
        f"outcome: {outcome}",
    ]
    if outcome == UNCHANGED:
        lines.append(f"unchanged-because: {justification}")
    lines.extend(items)
    return _plan(
        target_root,
        "revalidate",
        source,
        (FRICTION_KEY,),
        REVALIDATED,
        value,
        tuple(lines),
    )


def _kept_deferrals(
    artefact: Artefact,
    previous: Mapping[str, Any],
    keep: Sequence[str],
    confirm_keep: Callable[[Anchor, str], bool] | None,
) -> tuple[list[Any], list[str]]:
    """The deferrals a revalidation re-states, sorted, and a line for each kept or removed."""
    raw = previous.get(DEFERRED)
    entries: list[Any] = list(raw) if isinstance(raw, list) else []
    deferred = [a for a in (_entry_anchor(e) for e in entries) if a is not None]
    declared = anchors_of(artefact)

    named: set[Anchor] = set()
    for text in keep:
        anchor = _named_anchor(text, deferred, "deferral")
        if anchor is None:
            raise FrictionWriteError(
                f"{artefact.location} has no deferral of {text!r} to keep (its deferrals: "
                f"{_anchor_list(deferred)}). Nothing was written."
            )
        if anchor not in declared:
            raise FrictionWriteError(
                f"the deferral of {anchor.kind}:{anchor.value} cannot be kept: {artefact.location} "
                f"no longer declares that anchor, so the entry would dangle (COR-050 point 4). "
                f"Nothing was written."
            )
        named.add(anchor)

    kept: list[Any] = []
    items: list[str] = []
    seen: set[Anchor] = set()
    for entry in sorted(entries, key=_sort_key):
        anchor = _entry_anchor(entry)
        if anchor is None:
            items.append("removes a malformed deferral entry")
            continue
        if anchor in seen:
            items.append(f"removes a second entry for {anchor.kind}:{anchor.value}")
            continue
        seen.add(anchor)
        label = f"{anchor.kind}:{anchor.value}"
        reason = _entry_reason(entry)
        if anchor not in declared:
            items.append(
                f"removes deferral {label}   (the artefact no longer declares that anchor)"
            )
        elif anchor in named or (confirm_keep is not None and confirm_keep(anchor, reason)):
            kept.append(in_order(entry))
            items.append(f"keeps deferral {label}   ({reason})")
        else:
            items.append(f"removes deferral {label}   ({reason})")
    return kept, items


def plan_defer(
    target_root: Path,
    reference: str,
    *,
    anchor: str,
    reason: str,
    now: datetime | None = None,
) -> Plan:
    """The write of `pkit friction defer` (COR-050 point 4).

    Adds one entry to `deferred` — or rewords the reason of the entry already
    deferring that anchor, which keeps its deferral point — and keeps the
    list sorted. `at`, `outcome` and `unchanged-because` are left byte for
    byte: a deferral is not a revalidation, and an artefact never revalidated
    gets a `revalidated` block holding `deferred` alone. Refused: an empty
    anchor or reason, a reason with a placeholder left unfilled, and an anchor
    the artefact does not carry. An artefact whose block holds no answer gets
    its deferral in an answer file of the change's own (`_OwnFile.defer`).
    """
    anchor_text = anchor.strip()
    text = reason.strip()
    if not anchor_text:
        raise FrictionWriteError(
            "a deferral names the anchor whose friction it postpones: give `--anchor`. "
            "Nothing was written."
        )
    if not text:
        raise FrictionWriteError(
            "a deferral carries its reason: give `--reason`. Nothing was written."
        )
    _filled(text, "--reason")

    source, discovery = _source(target_root, reference)
    artefact = source.artefact
    block = _friction_block(artefact)
    carried = anchors_of(artefact)
    named = _named_anchor(anchor_text, carried, "anchor")
    if named is None:
        raise FrictionWriteError(
            f"{artefact.location} does not carry the anchor {anchor_text!r} (its anchors: "
            f"{_anchor_list(carried)}); a deferral must name one of them (COR-050 point 4). "
            f"Nothing was written."
        )
    if not block_holds_answers(artefact):
        own = _own_file(target_root, source, discovery)
        return own.defer(named, text, now=now or datetime.now(UTC))

    revalidated = block.get(REVALIDATED)
    if revalidated is not None and not isinstance(revalidated, Mapping):
        raise FrictionWriteError(
            f"{artefact.location}: its `{REVALIDATED}` is not a mapping; fix it first — "
            f"`pkit validate` reports it. Nothing was written."
        )
    raw = revalidated.get(DEFERRED) if isinstance(revalidated, Mapping) else None
    if raw is not None and not isinstance(raw, list):
        raise FrictionWriteError(
            f"{artefact.location}: its `{DEFERRED}` is not a list; fix it first — "
            f"`pkit validate` reports it. Nothing was written."
        )
    entries: list[Any] = list(raw or [])
    existing = [e for e in entries if _entry_anchor(e) == named]
    new_entry = {"anchor": {"kind": named.kind, "value": named.value}, "reason": text}
    label = f"{named.kind}:{named.value}"
    if len(existing) == 1 and _fold(_entry_reason(existing[0])) == _fold(text):
        return _unchanged(
            "defer",
            source,
            _target((FRICTION_KEY, REVALIDATED), DEFERRED),
            f"{label} is already deferred with this reason",
        )
    others = [
        in_order(e) if isinstance(e, Mapping) else e for e in entries if _entry_anchor(e) != named
    ]
    value = sorted([*others, new_entry], key=_sort_key)
    if existing:
        item = f"rewords the deferral of {label}: {text}   (its deferral point does not move)"
    else:
        item = f"adds deferral {label}: {text}"
    items = (item, "at: not changed — a deferral is not a revalidation")
    if isinstance(revalidated, Mapping):
        return _plan(
            target_root, "defer", source, (FRICTION_KEY, REVALIDATED), DEFERRED, value, items
        )
    return _plan(
        target_root, "defer", source, (FRICTION_KEY,), REVALIDATED, {DEFERRED: value}, items
    )


def plan_revisit(
    target_root: Path,
    reference: str,
    *,
    target: str,
    outcome: str,
    reason: str,
    now: datetime | None = None,
) -> Plan:
    """The write of `pkit friction revisit` (COR-050 point 16).

    Writes the entry for one target of a link the artefact's places declare in
    its `revisited` list — added, or the entry already naming the target
    rewritten — and keeps the list sorted by anchor. `at` is left byte for byte:
    an entry is no revalidation of the source. Refused: an outcome other than
    `unchanged` or `deferred`, an empty target or reason, a reason with a
    placeholder left unfilled, and a target no link of the artefact takes. An
    entry already written with this outcome and reason writes nothing: an entry
    answers only the change that writes it, so a later change needs new words.
    An artefact whose block holds no answer gets its entry in an answer file of
    the change's own (`_OwnFile.revisit`).
    """
    if outcome not in REVISIT_OUTCOMES:
        raise FrictionWriteError(
            f"a revisit's outcome is `unchanged` (the target still stands) or `deferred` (a "
            f"follow-up revisits it), not {outcome!r}; a target that changed needs no entry. "
            f"Nothing was written."
        )
    target_text = target.strip()
    text = reason.strip()
    if not target_text:
        raise FrictionWriteError(
            "a revisit names the target it answers for: give `--target`. Nothing was written."
        )
    if not text:
        raise FrictionWriteError(
            "a revisit carries its reason: give `--reason`. Nothing was written."
        )
    _filled(text, "--reason")

    source, discovery = _source(target_root, reference)
    artefact = source.artefact
    block = _friction_block(artefact)
    targets = list(dict.fromkeys(a for link in source.links for a in link_targets(artefact, link)))
    if not source.links:
        raise FrictionWriteError(
            f"no place holding {artefact.location} declares a link that revisits its targets, "
            f"so it has no target to answer for (COR-050 point 16). Nothing was written."
        )
    named = _named_anchor(target_text, targets, "target")
    if named is None:
        raise FrictionWriteError(
            f"{artefact.location} has no target {target_text!r}: its links take "
            f"{links_said(source.links)} (its targets: {_anchor_list(targets)}) (COR-050 "
            f"point 16). Nothing was written."
        )
    if not block_holds_answers(artefact):
        own = _own_file(target_root, source, discovery)
        return own.revisit(named, outcome, text, now=now or datetime.now(UTC))

    raw = block.get(REVISITED_KEY)
    if raw is not None and not isinstance(raw, list):
        raise FrictionWriteError(
            f"{artefact.location}: its `{REVISITED_KEY}` is not a list; fix it first — "
            f"`pkit validate` reports it. Nothing was written."
        )
    entries: list[Any] = list(cast(list[Any], raw or []))
    existing = [e for e in entries if _entry_anchor(e) == named]
    label = f"{named.kind}:{named.value}"
    if (
        len(existing) == 1
        and _entry_outcome(existing[0]) == outcome
        and _fold(_entry_reason(existing[0])) == _fold(text)
    ):
        return _unchanged(
            "revisit",
            source,
            _target((FRICTION_KEY,), REVISITED_KEY),
            f"{label} is already revisited `{outcome}` with this reason; an entry answers only "
            f"the change that writes it, so a later change needs new words",
        )
    others = [
        in_order(cast(Mapping[str, Any], e), REVISIT_KEYS) if isinstance(e, Mapping) else e
        for e in entries
        if _entry_anchor(e) != named
    ]
    new_entry = {
        "anchor": {"kind": named.kind, "value": named.value},
        "outcome": outcome,
        "reason": text,
    }
    value = sorted([*others, new_entry], key=_sort_key)
    verb = "rewrites the revisit entry of" if existing else "adds revisit entry"
    items = (
        f"{verb} {label}: {outcome} — {text}",
        "at: not changed — an entry is no revalidation of the source",
    )
    return _plan(target_root, "revisit", source, (FRICTION_KEY,), REVISITED_KEY, value, items)


def _entry_outcome(entry: Any) -> str | None:
    """A revisit entry's outcome as written, when it is text."""
    if not isinstance(entry, Mapping):
        return None
    outcome = cast(Mapping[str, Any], entry).get("outcome")
    return outcome if isinstance(outcome, str) else None


def plan_record_status(target_root: Path, reference: str) -> Plan:
    """The write of `pkit friction record-status` (COR-050 point 10).

    Runs the whole-repository check at HEAD and writes the artefact's
    `last-check`: its `state` (stale wins over deferred), `as-of` HEAD, and,
    when stale, `since` — the oldest commit its staleness comes from. Nothing
    is written when the recorded `state` and `since` already say so, whatever
    `as-of` holds. Refused: an artefact with no anchors or deferrals (there is
    no state), one not at HEAD, and one the check did not judge — its points
    lie beyond a shallow clone's history, or an anchor of it cannot be
    resolved: a status is a judgment, and neither is one.
    """
    source, _discovery = _source(target_root, reference)
    artefact = source.artefact
    block = _friction_block(artefact)
    if not anchors_of(artefact) and not artefact.deferrals:
        raise FrictionWriteError(
            f"{artefact.location} has no anchors or deferrals, so the check finds no state to "
            f"record. Nothing was written."
        )
    result = fr.run_repository_check(target_root)
    reports = [r for r in result.artefact_reports if r.location == artefact.location]
    if not reports or result.head is None:
        raise FrictionWriteError(
            f"{artefact.location} is not in HEAD as it stands: the status is the whole-repository "
            f"check's, which reads HEAD only — commit it first. Nothing was written."
        )
    report = reports[0]
    if report.state is fr.ArtefactState.UNREACHABLE:
        raise FrictionWriteError(
            f"{artefact.location} cannot be judged: a point of it lies beyond this clone's "
            f"history — fetch the full history (`git fetch --unshallow`) and run again. "
            f"Nothing was written."
        )
    if report.state is fr.ArtefactState.UNRESOLVED:
        unresolved = next(
            f
            for f in result.findings
            if f.location == artefact.location and f.kind in fr.UNRESOLVED_KINDS
        )
        anchor = unresolved.anchor
        named = "" if anchor is None else f"{anchor.kind} {anchor.value}: "
        raise FrictionWriteError(
            f"{artefact.location} cannot be judged: an anchor of it cannot be resolved "
            f"({named}{unresolved.message}). Nothing was written."
        )

    value: dict[str, Any] = {"state": report.state.value, "as-of": result.head.commit}
    origins = [
        f.origin
        for f in result.findings
        if f.location == artefact.location
        and f.kind is fr.RepositoryFindingKind.STALE
        and f.origin is not None
    ]
    if report.state is fr.ArtefactState.STALE and origins:
        value["since"] = min(origins, key=lambda c: (c.date, c.sha)).sha

    notes: tuple[str, ...] = ()
    if result.head.uncommitted:
        notes = (
            f"the status is of HEAD {result.head.commit[:_SHORT]}; "
            f"{result.head.uncommitted} uncommitted path(s) are not read",
        )
    as_of = _recorded_as_of(block.get(LAST_CHECK), value)
    if as_of is not None:
        return _unchanged(
            "record-status",
            source,
            _target((FRICTION_KEY,), LAST_CHECK),
            f"last-check already records `{value['state']}`"
            + (f" since {value['since'][:_SHORT]}" if "since" in value else "")
            + f" (as of {as_of[:_SHORT]}); a status is written only when it changes",
            notes,
        )
    items = [f"state: {value['state']}", f"as-of: {value['as-of']}   (HEAD)"]
    if "since" in value:
        items.append(f"since: {value['since']}   (where the staleness comes from)")
    return _plan(
        target_root,
        "record-status",
        source,
        (FRICTION_KEY,),
        LAST_CHECK,
        value,
        tuple(items),
        notes=notes,
    )


def _recorded_as_of(existing: Any, value: Mapping[str, Any]) -> str | None:
    """The `as-of` of a well-formed `last-check` that already records `value`, `as-of` aside;
    `None` when the status would change."""
    if not isinstance(existing, Mapping):
        return None
    as_of = existing.get("as-of")
    written = {k: v for k, v in existing.items() if k != "as-of"}
    wanted = {k: v for k, v in value.items() if k != "as-of"}
    return as_of if isinstance(as_of, str) and as_of and written == wanted else None


def _target(parent: Sequence[str], key: str) -> str:
    """What a write names as its target: the key's dotted path inside the carrier."""
    return ".".join((bs.CONTAINER_KEY, *parent, key))


def _unchanged(
    command: str, source: _Source, target: str, why: str, notes: tuple[str, ...] = ()
) -> Plan:
    return Plan(
        command=command,
        artefact=source.artefact.location,
        target=target,
        rel=source.rel,
        path=source.path,
        before=source.written,
        after=source.written,
        items=(),
        unchanged=why,
        notes=notes,
    )


def _plan(
    target_root: Path,
    command: str,
    source: _Source,
    parent: tuple[str, ...],
    key: str,
    value: Any,
    items: tuple[str, ...],
    *,
    notes: tuple[str, ...] = (),
) -> Plan:
    """Splice `key: value` into the block, read the result back, and describe the write."""
    carrier = carrier_keys(source.artefact)
    keys = (*carrier, bs.CONTAINER_KEY, *parent)
    splice = _splice(source, keys, key, value)
    front_matter = (
        source.front_matter[: splice.start] + splice.text + source.front_matter[splice.end :]
    )
    after = (
        source.text[: source.offset]
        + front_matter
        + source.text[source.offset + len(source.front_matter) :]
    )
    _read_back(target_root, source, after, (*keys, key), value)
    start = source.offset + splice.start
    end = start + len(splice.text)
    first = after.count("\n", 0, start) + 1
    last = after.count("\n", 0, max(end - 1, start)) + 1
    return Plan(
        command=command,
        artefact=source.artefact.location,
        target=_target(parent, key),
        rel=source.rel,
        path=source.path,
        before=source.written,
        after=source.as_written(after),
        items=items,
        first_line=first,
        last_line=last,
        notes=notes,
    )


# --- answers in an answer file of the change's own -----------------------------------
#
# An artefact whose block holds no answer gets its answers in an answer file (COR-062
# points 1 and 4; ADR-068 point 3): the one answer file in the working tree that no
# commit of the checkout holds, a new one where there is none. Until the move, an
# artefact whose block holds an answer keeps getting them there (`block_holds_answers`),
# as the reading of a state reads it from one home.

#: The commits whose answer files a writer never writes into: HEAD's, and those of a
#: merge, a cherry-pick or a revert in progress, which another line of work added
#: (COR-062 point 10).
_NOT_OWN = ("HEAD", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD")

# The keys of an entry, in the schema's order (ADR-068 point 2).
_ENTRY_ORDER = (af.ARTEFACT_KEY, af.READ_KEY, REVALIDATED, REVISITED_KEY)


def _source(target_root: Path, reference: str) -> tuple[_Source, Discovery]:
    """The artefact `reference` names, its file read for the write, and the discovery
    that found it. An artefact the project receives by sync is refused: it owes the
    project no answer, and its answers are its source's (COR-062 point 9)."""
    found, links, discovery = _locate(target_root, reference)
    if found.received:
        raise FrictionWriteError(
            f"{found.location} arrives in this project by sync, so it owes the project no "
            f"answer: its answers are written where it is authored (COR-062 point 9). Nothing "
            f"was written."
        )
    return _read_source(target_root, found, links), discovery


def _own_file(target_root: Path, source: _Source, discovery: Discovery) -> _OwnFile:
    """Where the artefact's answers are written: the answer file of the change's own, and
    every other answer file present that answers the artefact, which the answer reads.

    The change's own file is one the working tree holds and no commit of `_NOT_OWN`
    holds: the one of them that answers the artefact already, else the newest, else a
    new one. Two that each answer the artefact refuse the write, naming both: each
    would have to name the other (COR-062 point 10).
    """
    artefact = source.artefact
    present = af.working_tree_files(target_root)
    at_head = af.head_names(target_root)
    held = at_head.union(*(af.head_names(target_root, ref) for ref in _NOT_OWN[1:]))
    locate = af.working_locator(discovery, target_root)

    def names_it(entry: af.Entry) -> bool:
        found = locate(entry.location)
        return found is not None and found.location == artefact.location

    answering = sorted(n for n, f in present.items() if any(names_it(e) for e in f.entries))
    uncommitted = sorted(n for n in present if n not in held)
    own = [n for n in answering if n not in held]
    if len(own) > 1:
        listed = ", ".join(af.path_of(n) for n in own)
        raise FrictionWriteError(
            f"{artefact.location} is answered in {len(own)} answer files no commit holds yet "
            f"({listed}). A writer writes into the one answer file of this change's own, and "
            f"two would each have to name the other (COR-062 point 10): move this artefact's "
            f"entries into one of them, or commit one, and run the command again. Nothing was "
            f"written."
        )
    name = own[0] if own else (uncommitted[-1] if uncommitted else None)
    before = ""
    entries: list[dict[str, Any]] = []
    index: int | None = None
    if name is not None:
        before, entries, index = _own_entries(target_root, present[name], artefact, names_it)
    locations = {artefact.location} | {
        e.location for f in present.values() for e in f.entries if names_it(e)
    }
    state = af.StateAnswers(
        present,
        # An uncommitted entry honours a name of a file HEAD holds (COR-062 point 5). A
        # name a committed entry carries is read as honoured too: telling it needs the
        # history the checks read, and a writer only offers what it may keep with it.
        lambda _reader, named: named in at_head,
        lambda a: tuple(locations) if a.location == artefact.location else (a.location,),
    )
    return _OwnFile(
        target_root=target_root,
        source=source,
        name=name,
        present=present,
        entries=entries,
        index=index,
        before=before,
        read=tuple(n for n in answering if n != name),
        judged=state.liveness(artefact, discovery),
    )


def _own_entries(
    target_root: Path,
    answer_file: af.AnswerFile,
    artefact: Artefact,
    names_it: Callable[[af.Entry], bool],
) -> tuple[str, list[dict[str, Any]], int | None]:
    """The change's own answer file as written: its text, its entries, and the position of
    the one naming the artefact. Refused where it does not read, departs from the answer
    files' schema, or names the artefact twice: `pkit validate` reports each."""
    rel = af.path_of(answer_file.name)
    path = target_root / rel
    if path.is_symlink() or answer_file.document is None:
        problem = "is a link" if path.is_symlink() else answer_file.problem or "cannot be read"
        raise FrictionWriteError(
            f"{rel}, this change's answer file, {problem}; mend it or remove it first — `pkit "
            f"validate` reports it. Nothing was written."
        )
    try:
        before = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FrictionWriteError(f"cannot read {rel}: {exc}. Nothing was written.") from exc
    schema, _why = af.load_schema(target_root)
    if schema is not None and af.shape_findings(answer_file, schema):
        raise FrictionWriteError(
            f"{rel}, this change's answer file, departs from the answer files' schema; mend "
            f"it first — `pkit validate` reports it. Nothing was written."
        )
    document = cast(Mapping[str, Any], answer_file.document)
    entries = [dict(cast(Mapping[str, Any], e)) for e in document[af.ANSWERS_KEY]]
    positions = [e.index for e in answer_file.entries if names_it(e)]
    if len(positions) > 1:
        raise FrictionWriteError(
            f"{rel} answers {artefact.location} in {len(positions)} entries; a file holds one "
            f"entry per artefact — mend it first (`pkit validate` reports it). Nothing was "
            f"written."
        )
    return before, entries, positions[0] if positions else None


@dataclass(frozen=True)
class _OwnFile:
    """An artefact's answers as the change's own answer file holds them, and what an answer
    written there reads (COR-062 point 4; ADR-068 point 3).

    `name` is the file written into, `None` where the write adds one; `entries` its
    entries as written, `index` the one naming the artefact. `read` names every other
    answer file present that answers the artefact. `judged` is the artefact's answers in
    the answer files present, its own entry's among them.
    """

    target_root: Path
    source: _Source
    name: str | None
    present: Mapping[str, af.AnswerFile]
    entries: list[dict[str, Any]]
    index: int | None
    before: str
    read: tuple[str, ...]
    judged: af.Liveness

    @property
    def artefact(self) -> Artefact:
        return self.source.artefact

    @property
    def own(self) -> Mapping[str, Any]:
        """The artefact's entry in the change's own file, empty where it has none."""
        return {} if self.index is None else self.entries[self.index]

    # --- the three answers ---------------------------------------------------------

    def revalidate(
        self,
        *,
        outcome: str,
        justification: str | None,
        keep: Sequence[str],
        confirm_keep: Callable[[Anchor, str], bool] | None,
        now: datetime,
    ) -> Plan:
        """The revalidation in the change's own entry (COR-050 point 3, COR-062 point 5):
        a fresh `at`, the outcome and its justification, and the deferrals it keeps,
        re-stated. It replaces every revalidation it reads, and each deferral it reads
        that it does not re-state."""
        read = [e.revalidation for e in self.judged.entries if e.revalidation is not None]
        if outcome == UNCHANGED and any(_fold(justification) == r.because for r in read):
            raise FrictionWriteError(
                "the justification is one a revalidation this answer reads gives already; "
                "`unchanged-because` must differ from that of each revalidation it reads — "
                "say why the content holds against *this* change (COR-050 point 3, COR-062 "
                "point 5). Nothing was written."
            )
        stamp = now.astimezone(UTC).replace(microsecond=0)
        while any(r.at == stamp for r in read):
            stamp += timedelta(seconds=1)
        at = stamp.strftime(_AT_FORMAT)
        kept, items = self._kept(keep, confirm_keep)
        revalidated: dict[str, Any] = {AT: at, OUTCOME: outcome}
        if outcome == UNCHANGED:
            revalidated[BECAUSE] = justification
        if kept:
            revalidated[DEFERRED] = kept
        lines = [f"at: {at}", f"outcome: {outcome}"]
        if outcome == UNCHANGED:
            lines.append(f"unchanged-because: {justification}")
        lines.extend(items)
        entry = self._entry(revalidated, self.own.get(REVISITED_KEY))
        return self._plan("revalidate", REVALIDATED, entry, tuple(lines), now)

    def defer(self, anchor: Anchor, reason: str, *, now: datetime) -> Plan:
        """One deferral in the change's own entry (COR-050 point 4, COR-062 point 5): it
        replaces the deferral of its anchor it reads, keeping that one's point."""
        label = f"{anchor.kind}:{anchor.value}"
        live = [d for _e, d in self.judged.deferrals if d.anchor == anchor]
        if live and all(d.reason == _fold(reason) for d in live):
            return _unchanged(
                "defer",
                self.source,
                self._target(f"{REVALIDATED}.{DEFERRED}"),
                f"{label} is already deferred with this reason",
            )
        revalidated = dict(cast(Mapping[str, Any], self.own.get(REVALIDATED) or {}))
        others = [
            in_order(cast(Mapping[str, Any], e)) if isinstance(e, Mapping) else e
            for e in cast(list[Any], revalidated.get(DEFERRED) or [])
            if _entry_anchor(e) != anchor
        ]
        new_entry = {"anchor": {"kind": anchor.kind, "value": anchor.value}, "reason": reason}
        revalidated[DEFERRED] = sorted(
            [*others, *self._newly_read(revalidated, {anchor}), new_entry], key=_sort_key
        )
        if live:
            item = (
                f"rewords the deferral of {label}: {reason}   (it replaces the deferral it "
                f"reads, and keeps its deferral point)"
            )
        else:
            item = f"adds deferral {label}: {reason}"
        items = (item, "at: not changed — a deferral is not a revalidation")
        entry = self._entry(ordered_revalidation(revalidated), self.own.get(REVISITED_KEY))
        return self._plan("defer", f"{REVALIDATED}.{DEFERRED}", entry, items, now)

    def revisit(self, target: Anchor, outcome: str, reason: str, *, now: datetime) -> Plan:
        """One revisit entry in the change's own entry (COR-050 point 16, COR-062 point 5):
        it replaces the entry for its target it reads."""
        label = f"{target.kind}:{target.value}"
        live = [r for _e, r in self.judged.revisits if r.anchor == target]
        if live and all((r.outcome, r.reason) == (outcome, _fold(reason)) for r in live):
            return _unchanged(
                "revisit",
                self.source,
                self._target(REVISITED_KEY),
                f"{label} is already revisited `{outcome}` with this reason; an entry answers "
                f"only the change that writes it, so a later change needs new words",
            )
        others = [
            in_order(cast(Mapping[str, Any], e), REVISIT_KEYS) if isinstance(e, Mapping) else e
            for e in cast(list[Any], self.own.get(REVISITED_KEY) or [])
            if _entry_anchor(e) != target
        ]
        new_entry = {
            "anchor": {"kind": target.kind, "value": target.value},
            "outcome": outcome,
            "reason": reason,
        }
        revalidated: Any = self.own.get(REVALIDATED)
        if isinstance(revalidated, Mapping) and AT in revalidated:
            held = cast(Mapping[str, Any], revalidated)
            restated = self._newly_read(held, set())
            if restated:
                kept = [*cast(list[Any], held.get(DEFERRED) or []), *restated]
                revalidated = ordered_revalidation({**held, DEFERRED: sorted(kept, key=_sort_key)})
        verb = "rewrites the revisit entry of" if live else "adds revisit entry"
        items = (
            f"{verb} {label}: {outcome} — {reason}",
            "at: not changed — an entry is no revalidation of the source",
        )
        entry = self._entry(revalidated, sorted([*others, new_entry], key=_sort_key))
        return self._plan("revisit", REVISITED_KEY, entry, items, now)

    # --- what the answers keep -----------------------------------------------------

    def _kept(
        self, keep: Sequence[str], confirm_keep: Callable[[Anchor, str], bool] | None
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """The live deferrals a revalidation re-states, sorted, and a line for each kept or
        dropped (COR-050 point 4, COR-062 point 5)."""
        reasons = self._live_reasons()
        named: set[Anchor] = set()
        for text in keep:
            anchor = _named_anchor(text, list(reasons), "deferral")
            if anchor is None:
                raise FrictionWriteError(
                    f"{self.artefact.location} has no live deferral of {text!r} to keep (its "
                    f"deferrals: {_anchor_list(list(reasons))}); a deferral of an anchor it no "
                    f"longer declares answers nothing (COR-062 point 5). Nothing was written."
                )
            named.add(anchor)
        kept: list[dict[str, Any]] = []
        items: list[str] = []
        for anchor in sorted(reasons, key=lambda a: (a.kind, a.value)):
            reason = reasons[anchor]
            label = f"{anchor.kind}:{anchor.value}"
            if anchor in named or (confirm_keep is not None and confirm_keep(anchor, reason)):
                kept.append(
                    {"anchor": {"kind": anchor.kind, "value": anchor.value}, "reason": reason}
                )
                items.append(f"keeps deferral {label}   ({reason})")
            else:
                items.append(f"drops deferral {label}   ({reason})")
        return kept, items

    def _live_reasons(self, files: Collection[str] | None = None) -> dict[Anchor, str]:
        """Each live deferral's anchor, with its reason as written — of `files` only, where
        given. Of two deferrals of one anchor made apart, the newer file's reason."""
        found: dict[Anchor, str] = {}
        for entry, deferral in sorted(self.judged.deferrals, key=lambda p: (p[0].file, p[1].index)):
            if files is None or entry.file in files:
                found[deferral.anchor] = self._reason(entry, deferral)
        return found

    def _reason(self, entry: af.Entry, deferral: af.Deferment) -> str:
        """A deferral's reason as its answer file writes it, its words folded where that
        cannot be read."""
        document = self.present[entry.file].document
        try:
            written = document[af.ANSWERS_KEY][entry.index][REVALIDATED][DEFERRED][deferral.index]
            reason = written["reason"]
        except (KeyError, IndexError, TypeError):
            reason = None
        return reason if isinstance(reason, str) else deferral.reason or ""

    def _newly_read(
        self, revalidated: Mapping[str, Any], written: Collection[Anchor]
    ) -> list[dict[str, Any]]:
        """Where the change's own entry holds a revalidation, the live deferrals of the
        files its `read` gains, re-stated unless it keeps their anchor already or
        `written` names it: a deferral or a revisit entry is no revalidation, so writing
        one never lets the revalidation drop a deferral it never read (COR-062 point 5)."""
        if AT not in revalidated:
            return []
        gained = set(self.read) - set(cast(list[str], self.own.get(af.READ_KEY) or []))
        if not gained:
            return []
        held = {_entry_anchor(e) for e in cast(list[Any], revalidated.get(DEFERRED) or [])}
        return [
            {"anchor": {"kind": anchor.kind, "value": anchor.value}, "reason": reason}
            for anchor, reason in self._live_reasons(gained).items()
            if anchor not in held and anchor not in written
        ]

    # --- the file ------------------------------------------------------------------

    def _entry(self, revalidated: Any, revisited: Any) -> dict[str, Any]:
        """The artefact's entry: its location, what it read, and its answers."""
        entry: dict[str, Any] = {af.ARTEFACT_KEY: self.artefact.location}
        if self.read:
            entry[af.READ_KEY] = list(self.read)
        if revalidated:
            entry[REVALIDATED] = revalidated
        if revisited:
            entry[REVISITED_KEY] = revisited
        return {key: entry[key] for key in _ENTRY_ORDER if key in entry}

    def _target(self, key: str) -> str:
        return f"{af.ANSWERS_KEY}[{self.artefact.location}].{key}"

    def _plan(
        self, command: str, key: str, entry: dict[str, Any], items: tuple[str, ...], now: datetime
    ) -> Plan:
        """The file with the artefact's entry in it, read back, and what the write says."""
        entries = list(self.entries)
        position = len(entries) if self.index is None else self.index
        if self.index is None:
            entries.append(entry)
        else:
            entries[position] = entry
        name = self.name
        _answer_folder(self.target_root)
        while name is None or (self.name is None and name in self.present):
            name = af.new_name(now)
        text, first, last = answer_file_text(entries, position)
        self._read_back(name, text, entries)
        rel = af.path_of(name)
        read = ", ".join(self.read) if self.read else "no other answer file answers it"
        return Plan(
            command=command,
            artefact=self.artefact.location,
            target=self._target(key),
            rel=rel,
            path=self.target_root / rel,
            before=self.before,
            after=text,
            items=(*items, f"read: {read}"),
            first_line=first,
            last_line=last,
            answer_file=True,
            creates=self.name is None,
        )

    def _read_back(self, name: str, text: str, entries: list[dict[str, Any]]) -> None:
        """Refuse unless `text` reads back as exactly `entries`, in the answer files' shape."""
        read = af.read_answer_file(name, text.encode("utf-8"))
        schema, _why = af.load_schema(self.target_root)
        findings = [] if schema is None else af.shape_findings(read, schema)
        raw: Any = read.document
        document: Mapping[str, Any] = (
            cast(Mapping[str, Any], raw) if isinstance(raw, Mapping) else {}
        )
        if read.problem is not None or findings or document.get(af.ANSWERS_KEY) != entries:
            detail = "; ".join(f"{p or '(file)'}: {m}" for p, m in findings) or read.problem
            raise FrictionWriteError(
                f"{af.path_of(name)}: the answer would not read back as written"
                f"{f' — {detail}' if detail else ''}. Nothing was written."
            )


def _answer_folder(target_root: Path) -> None:
    """Refuse to add an answer file unless the answer folder, and each folder above it, is
    a folder of the repository's own or not there yet: never a link, which would write the
    answer elsewhere (COR-062 point 2)."""
    current = target_root
    for part in PurePosixPath(af.FOLDER).parts:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise FrictionWriteError(
                f"{current.relative_to(target_root).as_posix()} is a link or a file, so no "
                f"answer file can be added in {af.FOLDER}: the answer folder is a folder of "
                f"the project's own (COR-062 point 2). Nothing was written."
            )


def ordered_revalidation(revalidated: Mapping[str, Any]) -> dict[str, Any]:
    """A `revalidated` mapping with its keys in the schema's order."""
    order = _KEY_ORDER[REVALIDATED]
    head = {k: revalidated[k] for k in order if k in revalidated}
    return head | {k: v for k, v in revalidated.items() if k not in order}


def answer_file_text(
    entries: Sequence[Mapping[str, Any]], position: int = -1
) -> tuple[str, int, int]:
    """An answer file holding `entries`, in block style as the writers write it, and the
    lines entry `position` occupies (1-based; `0, 0` where it names none)."""
    lines = [f"{af.ANSWERS_KEY}:"]
    first = last = 0
    for index, entry in enumerate(entries):
        item = _item_lines(entry, 2)
        if index == position:
            first, last = len(lines) + 1, len(lines) + len(item)
        lines.extend(item)
    return "\n".join(lines) + "\n", first, last


# --- the edit ----------------------------------------------------------------------


@dataclass(frozen=True)
class _Splice:
    """Replace the front matter's characters `[start, end)` with `text`; an insertion when equal."""

    start: int
    end: int
    text: str


def _splice(source: _Source, keys: Sequence[str], key: str, value: Any) -> _Splice:
    """Where `key: value` goes in the mapping `keys` leads to, and its text there.

    In a block mapping, an existing key's lines — from the key through the line
    its value ends on — are replaced by the value rendered in block style at
    the key's indentation; a new key is inserted after the sibling that
    precedes it in the schema's order. In a flow mapping (`{…}`) the key's
    characters are replaced, or the key inserted, in flow style. The mapping
    must exist and be written directly, not through an alias.
    """
    fm = source.front_matter
    parent = _node_at(_composed(fm), keys)  # discovery has parsed it: it composes
    if parent is None:
        raise FrictionWriteError(
            f"{source.artefact.location}: cannot find `{'.'.join(keys)}` written in the file "
            f"(is it reached through a YAML alias or merge key?); edit the block by hand. "
            f"Nothing was written."
        )
    if not isinstance(parent, MappingNode):
        raise FrictionWriteError(
            f"{source.artefact.location}: `{'.'.join(keys)}` is not a mapping; fix it first — "
            f"`pkit validate` reports it. Nothing was written."
        )
    existing = _pair(parent, key)
    if _in_flow(parent):
        return _flow_splice(parent, existing, keys[-1], key, value)
    return _block_splice(fm, parent, existing, keys[-1], key, value, source)


def without_key(front_matter: str, keys: Sequence[str], key: str) -> str | None:
    """`front_matter` with `key` and its value taken out of the mapping `keys` lead to, every
    other character kept; `None` where that cannot be done exactly — the mapping not written
    directly, the key not starting its line, or the mapping left with no key.

    In a block mapping the key's lines go, from the key through the line its value ends
    on. In a flow mapping (`{…}`) its characters go, with the comma beside them.
    """
    parent = _node_at(_composed(front_matter), keys)
    if not isinstance(parent, MappingNode):
        return None
    existing = _pair(parent, key)
    if existing is None:
        return front_matter
    held: Any = getattr(parent, "value", ())  # ruamel's nodes are untyped
    pairs = cast("list[tuple[Node, Node]]", held)
    if len(pairs) < 2:
        return None
    key_node, value_node = existing
    if _in_flow(parent):
        position = next(i for i, pair in enumerate(pairs) if pair[0] is key_node)
        start, end = _pair_span(key_node, value_node)
        if position + 1 < len(pairs):
            end = _first_index(pairs[position + 1][0])
        else:
            start = _pair_end(*pairs[position - 1])
        return front_matter[:start] + front_matter[end:]
    first = _first_index(key_node)
    start = _line_start(front_matter, first)
    if front_matter[start:first].strip():
        return None
    end = _through_line(front_matter, start, _pair_end(key_node, value_node))
    return front_matter[:start] + front_matter[end:]


def _first_index(node: Node) -> int:
    """Where a node's text starts in the front matter."""
    mark: Any = getattr(node, "start_mark", None)  # ruamel's nodes are untyped
    return cast(int, mark.index)


def _composed(front_matter: str) -> Node | None:
    """The front matter's node tree, positions included; `None` when it does not parse."""
    try:
        root: Node | None = YAML().compose(io.StringIO(front_matter))
    except YAMLError:
        return None
    return root


def _node_at(root: Node | None, keys: Sequence[str]) -> Node | None:
    """The value `keys` lead to from `root`, each step a key written in a mapping; `None`
    where a step is not written directly — reached through an alias or merge key — or not
    at all."""
    node = root
    for step in keys:
        pair = _pair(node, step) if isinstance(node, MappingNode) else None
        if pair is None:
            return None
        node = pair[1]
    return node


def _pair(mapping: MappingNode, key: str) -> tuple[Node, Node] | None:
    for key_node, value_node in mapping.value:
        if isinstance(key_node, ScalarNode) and key_node.value == key:
            return key_node, value_node
    return None


class KeySpan(NamedTuple):
    """Where a key is written: `[start, end)` from its first character to its value's last,
    and whether the mapping holding it is written in flow style (`{…}`)."""

    start: int
    end: int
    flow: bool


def key_span(front_matter: str, keys: Sequence[str]) -> KeySpan | str:
    """Where the last of `keys` is written in `front_matter`: from its key's first character
    to its value's last — the characters a write in flow style replaces, and in block style
    the key's lines without their indentation or line break.

    Each step is the key the parsed front matter reads under that text: each key is read
    rendered as text (`backbone_schemas.as_written`), as discovery reads it, so `0x1` is
    read as `1` and `true` as `True`. A key written as the step but read otherwise is
    another key. Else why the key cannot be told, as words that follow its name: the
    front matter does not parse, a mapping on the path holds a merge key, through which
    keys written elsewhere are read as its own, two of its keys are read as the step, or
    none is.
    """
    root = _composed(front_matter)
    if root is None:
        return "is not in front matter that parses"
    constructor: Any = YAML(typ="safe").constructor  # ruamel's constructor is untyped
    node: Node = root
    parent: MappingNode | None = None
    pair: tuple[Node, Node] | None = None
    for step in keys:
        if not isinstance(node, MappingNode):
            return f"is not written under a key read as `{step}`"
        parent = node
        read: list[tuple[Node, Node]] = []
        held: Any = getattr(node, "value", ())  # ruamel's nodes are untyped
        for key_node, value_node in cast("list[tuple[Node, Node]]", held):
            if getattr(key_node, "tag", None) == _MERGE_TAG:
                return (
                    "is reached through a merge key, which reads keys written elsewhere as "
                    "its mapping's own"
                )
            if _read_as(constructor, key_node) == step:
                read.append((key_node, value_node))
        if len(read) > 1:
            return f"cannot be told apart: two keys on its path are read as `{step}`"
        if not read:
            return f"is not written under a key read as `{step}`"
        pair = read[0]
        node = pair[1]
    if pair is None or parent is None:
        return "is named by no key"
    return KeySpan(*_pair_span(*pair), flow=_in_flow(parent))


# The tag YAML resolves a merge key to, written `<<` or tagged `!!merge`.
_MERGE_TAG = "tag:yaml.org,2002:merge"


def _read_as(constructor: Any, key_node: Node) -> str | None:
    """A key as the parsed front matter reads it: built as YAML builds it, a sequence held
    as a tuple, then rendered as text (`backbone_schemas.as_written`), or `None` where it
    cannot be built."""
    try:
        key = constructor.construct_object(key_node, deep=True)
    except (YAMLError, TypeError, ValueError, KeyError):
        return None
    if isinstance(key, list):
        key = tuple(cast("list[Any]", key))
    try:
        rendered = cast("Mapping[str, Any]", bs.as_written({key: None}))
    except TypeError:  # a key no mapping can hold
        return None
    return next(iter(rendered))


def _in_flow(mapping: MappingNode) -> bool:
    """Whether a mapping is written in flow style (`{…}`)."""
    return mapping.flow_style is True


def written_key(key: str, value: Any, *, column: int, flow: bool) -> str:
    """`key: value` as the writers write it, for the span `key_span` gives of a key starting
    at `column`: in flow style, or in block style with each further line indented from
    `column` — from the key's first character to the value's last."""
    if flow:
        return f"{key}: {_flow(value)}"
    return _block(key, value, column)[column:].removesuffix("\n")


def _rank(parent_key: str, key: str) -> int:
    order = _KEY_ORDER.get(parent_key, ())
    return order.index(key) if key in order else -1


def _block_splice(
    fm: str,
    parent: MappingNode,
    existing: tuple[Node, Node] | None,
    parent_key: str,
    key: str,
    value: Any,
    source: _Source,
) -> _Splice:
    if existing is not None:
        key_node, value_node = existing
        start = _line_start(fm, key_node.start_mark.index)
        if fm[start : key_node.start_mark.index].strip():
            raise FrictionWriteError(
                f"{source.artefact.location}: `{key}` does not start its line; edit the block by "
                f"hand. Nothing was written."
            )
        end = _through_line(fm, start, _pair_end(key_node, value_node))
        return _Splice(start, end, _block(key, value, key_node.start_mark.column))
    indent = parent.value[0][0].start_mark.column
    rank = _rank(parent_key, key)
    before = [pair for pair in parent.value if _rank(parent_key, _key_text(pair[0])) < rank]
    if before:
        key_node, value_node = before[-1]
        at = _through_line(fm, _line_start(fm, key_node.start_mark.index), _pair_end(*before[-1]))
    else:
        at = _line_start(fm, parent.value[0][0].start_mark.index)
    return _Splice(at, at, _block(key, value, indent))


def _flow_splice(
    parent: MappingNode,
    existing: tuple[Node, Node] | None,
    parent_key: str,
    key: str,
    value: Any,
) -> _Splice:
    written = f"{key}: {_flow(value)}"
    if existing is not None:
        start, end = _pair_span(*existing)
        return _Splice(start, end, written)
    rank = _rank(parent_key, key)
    after = [pair for pair in parent.value if _rank(parent_key, _key_text(pair[0])) > rank]
    if after:
        at = after[0][0].start_mark.index
        return _Splice(at, at, f"{written}, ")
    if parent.value:
        at = _pair_end(*parent.value[-1])
        return _Splice(at, at, f", {written}")
    at = parent.start_mark.index + 1  # just inside `{`
    return _Splice(at, at, written)


def _key_text(node: Node) -> str:
    return node.value if isinstance(node, ScalarNode) else ""


def _pair_span(key_node: Node, value_node: Node) -> tuple[int, int]:
    """A key and its value in the text: from the key's first character to the value's last."""
    return cast(int, key_node.start_mark.index), _pair_end(key_node, value_node)


def _pair_end(key_node: Node, value_node: Node) -> int:
    """Where a key's value ends in the text: its last character, not the next token."""
    end = _content_end(value_node)
    return key_node.end_mark.index if end is None else end


def _content_end(node: Node) -> int | None:
    """Where a node's own text ends; `None` for an empty value, which has no text.

    A scalar and a flow collection end at their end mark. A block collection's
    end mark is the next token — past trailing comments and blank lines — so
    its own text ends where its last child's does.
    """
    if isinstance(node, MappingNode) and not node.flow_style and node.value:
        return _pair_end(*node.value[-1])
    if isinstance(node, SequenceNode) and not node.flow_style and node.value:
        last = _content_end(node.value[-1])
        return node.value[-1].start_mark.index if last is None else last
    if isinstance(node, ScalarNode) and node.value == "" and node.style is None:
        return None
    return node.end_mark.index


def _line_start(text: str, index: int) -> int:
    return text.rfind("\n", 0, index) + 1


def _through_line(text: str, start: int, end: int) -> int:
    """The end of the line holding the character before `end`, trailing blank lines left out."""
    newline = text.find("\n", max(end - 1, start))
    stop = len(text) if newline == -1 else newline + 1
    while stop > start:
        line_start = text.rfind("\n", start, stop - 1) + 1
        if line_start <= start or text[line_start:stop].strip():
            break
        stop = line_start
    return stop


# --- rendering ---------------------------------------------------------------------


def _block(key: str, value: Any, indent: int) -> str:
    """`key: value` in block style at `indent`, one line per scalar, ending with a newline."""
    return "".join(line + "\n" for line in _block_lines(key, value, indent))


def _block_lines(key: str, value: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, Mapping) and value:
        lines = [f"{pad}{key}:"]
        for child_key, child in value.items():
            lines.extend(_block_lines(str(child_key), child, indent + 2))
        return lines
    if isinstance(value, list) and value:
        lines = [f"{pad}{key}:"]
        for item in value:
            lines.extend(_item_lines(item, indent + 2))
        return lines
    return [f"{pad}{key}: {_scalar(key, value)}"]


def _item_lines(item: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(item, Mapping) and item:
        inner: list[str] = []
        for child_key, child in item.items():
            inner.extend(_block_lines(str(child_key), child, indent + 2))
        return [f"{pad}- {inner[0][indent + 2 :]}", *inner[1:]]
    return [f"{pad}- {_scalar(None, item)}"]


def _scalar(key: str | None, value: Any) -> str:
    """A value as one YAML scalar: plain where it reads back as the same text, else quoted.

    `at` is written as the bare timestamp the schema documents; YAML reads it
    as an instant, which discovery renders back to the same text.
    """
    if isinstance(value, Mapping):
        return "{}"
    if isinstance(value, list):
        return "[]"
    if not isinstance(value, str):
        return json.dumps(value)
    if key == AT and _UTC_TIMESTAMP.match(value):
        return value
    if value and value == value.strip() and "\n" not in value and _reads_back(value, value):
        return value
    return _quoted(value)


def _quoted(text: str) -> str:
    quoted = json.dumps(text, ensure_ascii=False)
    return quoted if _reads_back(quoted, text) else json.dumps(text)


def _reads_back(written: str, text: str) -> bool:
    """Whether `k: <written>` reads back as exactly the text `text`."""
    try:
        data = _safe.load(f"k: {written}\n")
    except YAMLError:
        return False
    return isinstance(data, Mapping) and data.get("k") == text and isinstance(data.get("k"), str)


def _flow(value: Any) -> str:
    """A value in flow style, every text quoted, for a block written as `{…}`."""
    if isinstance(value, Mapping):
        inner = ", ".join(f"{_flow_key(k)}: {_flow(v)}" for k, v in value.items())
        return "{" + inner + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_flow(v) for v in value) + "]"
    if isinstance(value, str):
        return _quoted(value)
    return json.dumps(value)


def _flow_key(key: Any) -> str:
    text = str(key)
    return text if re.fullmatch(r"[a-z][a-z-]*", text) else _quoted(text)


# --- reading back ------------------------------------------------------------------


def _read_back(
    target_root: Path, source: _Source, after: str, keys: Sequence[str], value: Any
) -> None:
    """Refuse unless `after` holds exactly the front matter as it was with `keys` set to `value`,
    and the artefact passes validation's per-artefact judgments."""
    front_matter, _body = split_front_matter(after)
    try:
        read = bs.as_written(_safe.load(front_matter or ""))
    except YAMLError:
        read = None
    expected = copy.deepcopy(bs.as_written(_safe.load(source.front_matter)))
    holder = expected
    for step in keys[:-1]:
        holder = holder[step]
    holder[keys[-1]] = bs.as_written(value)
    if read != expected:
        raise FrictionWriteError(
            f"{source.artefact.location}: the block could not be rewritten without changing "
            f"anything else in the front matter (does it use YAML anchors or aliases?); edit it "
            f"by hand. Nothing was written."
        )
    artefact = source.artefact
    reread, _reason = parse_artefacts(
        artefact.path, artefact.place, after, rule_set=artefact.rule_set
    )
    written = [a for a in reread if a.kind is artefact.kind and a.id == artefact.id]
    schema = _container_schema(target_root)
    errors = [
        f
        for a in written
        for f in block_findings(a, schema, target_root, source.links)
        if f.severity is Severity.ERROR
    ]
    if len(written) != 1 or errors:
        detail = "; ".join(f"{f.pointer or '(block)'}: {f.message.rstrip('.')}" for f in errors)
        raise FrictionWriteError(
            f"{artefact.location}: the block would not validate after the write — "
            f"{detail or 'the artefact would not read back'}. Fix the block first "
            f"(`pkit validate` reports it). Nothing was written."
        )


def _container_schema(target_root: Path) -> dict | None:
    """The tree's container schema, or `None` where validation skips the block check too."""
    try:
        return bs.load_backbone_schema(target_root, "container")
    except (bs.BackboneSchemaMissing, bs.BackboneSchemaInvalid):
        return None


# --- consent and the write ---------------------------------------------------------


def interactive() -> bool:
    """Whether a confirmation can be asked: stdin is a terminal."""
    return stdin_is_tty()


def ask_keep(anchor: Anchor, reason: str) -> bool:
    """The prompt for a deferral a revalidation was not told to keep; removing is the default."""
    shown = f" — {reason}" if reason else ""
    return click.confirm(
        f"Keep the deferral of {anchor.kind}:{anchor.value}{shown}?", default=False
    )


def _filled(text: str, flag: str) -> None:
    """Refuse `text` while it still holds a placeholder: the words are the person's."""
    found = PLACEHOLDER.search(text)
    if found is not None:
        raise FrictionWriteError(
            f"`{flag}` still holds the placeholder {found.group(0)!r}: write in its place what "
            f"it asks for — the one piece of judgment the tool cannot supply (COR-050 point "
            f"3). Nothing was written."
        )


def command_line(*words: str) -> str:
    """A command as the user would type it, each word quoted where the shell needs it."""
    return " ".join(shlex.quote(word) for word in words)


def render_plan(plan: Plan) -> str:
    """What the command writes: the artefact, the block and its lines, one line per item."""
    title = cli_render.style("title", f"Friction {plan.command}") + f" — {plan.artefact}"
    lines = [title, ""]
    lines.extend(f"  ⚠ {note}" for note in plan.notes)
    if not plan.changes:
        lines.append(f"  Nothing to write: {plan.unchanged}.")
        return "\n".join(lines) + "\n"
    span = (
        f"line {plan.first_line}"
        if plan.first_line == plan.last_line
        else f"lines {plan.first_line}-{plan.last_line}"
    )
    if plan.creates:
        where = "a new answer file of this change"
    elif plan.answer_file:
        where = "this change's answer file, not yet committed; its other entries kept"
    else:
        where = "nothing else in the file"
    lines.append(f"  Writes {plan.target} in {plan.rel}   ({span}; {where})")
    lines.extend(f"    {item}" for item in plan.items)
    return "\n".join(lines) + "\n"


def render_diff(plan: Plan) -> str:
    """The write as a unified diff of the file — from nothing, for a file it adds."""
    diff = difflib.unified_diff(
        plan.before.splitlines(keepends=True),
        plan.after.splitlines(keepends=True),
        fromfile="/dev/null" if plan.creates else f"a/{plan.rel}",
        tofile=f"b/{plan.rel}",
    )
    return "".join(diff)


def apply(
    plan: Plan,
    *,
    yes: bool,
    dry_run: bool,
    can_ask: bool,
    rerun: Sequence[str],
    writes_answer: bool = False,
) -> bool:
    """Show the plan and, with consent, write it; returns whether the file was written.

    `rerun` is the command as run, without `--yes` or `--dry-run`, for the
    refusal to name. A plan with nothing to write writes nothing and succeeds.
    A writer whose plan is an answer on an artefact (`writes_answer`: revalidate,
    defer) is refused without a ready-made `--yes` command to run: an answer may
    be a person's decision (COR-050 point 3) — every answer but the ones a change
    owes, which the agent making it may write and a reviewer checks — so the
    refusal names the dry run and says what `--yes` does.
    """
    click.echo(render_plan(plan), nl=False)
    if not plan.changes:
        return False
    if dry_run:
        click.echo("")
        click.echo(render_diff(plan), nl=False)
        click.echo("")
        click.echo(cli_render.style("strong", "Dry run: nothing written."))
        return False
    if not yes:
        if not can_ask:
            consent = (
                "`--yes` writes without asking. An answer on an artefact may be a person's "
                "decision (COR-050 point 3)."
                if writes_answer
                else f"To consent non-interactively, run:\n  {command_line(*rerun, '--yes')}"
            )
            what = f"{plan.rel}, the answer on {plan.artefact}," if plan.answer_file else plan.rel
            raise ConsentRefused(
                f"refusing to write {what} without consent: stdin is not a terminal and "
                f"--yes was not given (COR-050 point 13). Nothing was written.\n"
                f"To see the change first, run:\n  {command_line(*rerun, '--dry-run')}\n"
                f"{consent}"
            )
        click.echo("")
        click.echo(render_diff(plan), nl=False)
        click.confirm(f"Write this to {plan.rel}?", default=True, abort=True)
    write(plan)
    click.echo(f"Wrote {plan.target} in {plan.rel}.")
    return True


def write(plan: Plan) -> None:
    """Write the plan's file atomically, keeping its mode; refuse if it changed since read.
    A file the plan adds is created, never written over one that appeared since."""
    if plan.creates:
        create_file(plan.path, plan.rel, plan.after)
    else:
        replace_file(plan.path, plan.rel, plan.before, plan.after)


def create_file(path: Path, rel: str, text: str) -> None:
    """Create the file at `path` (`rel` names it) holding `text`, its folders with it;
    refuse, writing nothing, where anything is at the path already."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(text)
    except FileExistsError as exc:
        raise FileNotReplaced(
            f"{rel} appeared since it was planned; run the command again."
        ) from exc
    except OSError as exc:
        raise FileNotReplaced(f"cannot write {rel}: {exc}.") from exc


def replace_file(path: Path, rel: str, before: str, after: str) -> None:
    """Replace the file at `path` (`rel` names it) with `after` atomically, keeping its mode;
    refuse, writing nothing, unless it still holds `before`."""
    try:
        current = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FileNotReplaced(f"cannot read {rel}: {exc}.") from exc
    if current != before:
        raise FileNotReplaced(f"{rel} changed since it was read; run the command again.")
    mode = stat.S_IMODE(path.stat().st_mode)
    # A temporary file of a fresh name, created where nothing stood, so no link planted
    # beside the file can take the write elsewhere.
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    tmp = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(after.encode("utf-8"))
            os.fchmod(handle.fileno(), mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


__all__ = [
    "DEFERRAL_KEYS",
    "OUTCOMES",
    "REVISIT_KEYS",
    "REVISIT_OUTCOMES",
    "ConsentRefused",
    "FileNotReplaced",
    "FrictionWriteError",
    "KeySpan",
    "Plan",
    "answer_file_text",
    "apply",
    "ask_keep",
    "carrier_keys",
    "command_line",
    "create_file",
    "find_artefact",
    "in_order",
    "interactive",
    "key_span",
    "locate_artefact",
    "ordered_revalidation",
    "plan_defer",
    "plan_record_status",
    "plan_revalidate",
    "plan_revisit",
    "render_diff",
    "render_plan",
    "replace_file",
    "without_key",
    "write",
    "written_key",
]
