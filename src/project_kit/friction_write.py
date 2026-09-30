"""The friction writers: `revalidate`, `defer`, `record-status` (COR-050 points 3, 4, 10 and 13).

Reading never writes; writing is always one of these three explicit
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
- `record-status` writes the tool-written `last-check` block from the
  whole-repository check at HEAD, only when the state it records changes
  (point 10): `as-of` moving on alone is no change, so a status that holds is
  never rewritten.

**Only the block changes.** Each writer replaces one key of the artefact's
`friction` block — the lines from that key through the end of its value, or,
in a block written in flow style, that key's characters — and leaves every
other byte of the file as it was. Before anything is written the result is
read back: the front matter must parse to exactly what it held with that one
key replaced, and the artefact must pass validation's per-artefact judgments
(`friction_validate.block_findings`), so a writer never writes what `pkit
validate` would refuse. Entries are kept in one order — deferrals by anchor
kind, then value; keys in the schema's order (`anchors`, `unanchored-because`,
`revalidated`, `last-check`; `at`, `outcome`, `unchanged-because`,
`deferred`) — so the same input always writes the same bytes.

**Consent.** `--yes`; or, on a terminal, a confirmation shown with the diff;
`--dry-run` shows the diff and writes nothing; a non-interactive run with
neither refuses, writes nothing, and names the command to run — the consent
rule of the configuration writer (COR-048 point 5), applied to the project's
own artefacts.
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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import click
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from project_kit import backbone_schemas as bs
from project_kit import cli_render
from project_kit import friction_repository as fr
from project_kit.friction_check import anchors_of, parsed_at
from project_kit.friction_discovery import (
    FRICTION_KEY,
    RULES_KEY,
    UNANCHORED_BECAUSE_KEY,
    Anchor,
    Artefact,
    ArtefactKind,
    discover_artefacts,
    held_message,
    parse_artefacts,
    split_front_matter,
)
from project_kit.friction_validate import block_findings
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
    FRICTION_KEY: ("anchors", UNANCHORED_BECAUSE_KEY, REVALIDATED, LAST_CHECK),
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


class ConsentRefused(click.ClickException):
    """Nobody could consent: not a terminal, and neither `--yes` nor `--dry-run` (point 13)."""


# --- the artefact ------------------------------------------------------------------


def find_artefact(target_root: Path, reference: str) -> Artefact:
    """The one artefact in the declared places that `reference` names.

    Its location first — `path` for a document, `path#id` for a collection
    entry — then any identifier an artefact anchor may use (its id; a
    document's path; a method rule's `<component>:<id>`). A reference naming
    none, or more than one, is refused with what it could have meant — and one
    naming a document a component holds says whose it is: a held document is
    no artefact, and carries no block to write (COR-050 point 1).
    """
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
    return matches[0]


@dataclass(frozen=True)
class _Source:
    """The artefact's file as read for the edit, and the artefact re-read from exactly that text."""

    rel: str  # the file, relative to the project root
    path: Path  # the file written — links resolved, so a link stays a link
    text: str
    offset: int  # where the front matter's YAML starts in `text`
    front_matter: str
    artefact: Artefact


def _read_source(target_root: Path, found: Artefact) -> _Source:
    path = (target_root / found.path).resolve()
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FrictionWriteError(f"cannot read {found.path}: {exc}. Nothing was written.") from exc
    if "\r" in text:
        raise FrictionWriteError(
            f"{found.path} holds carriage returns (`\\r`, as in Windows line endings); the "
            f"writers keep every other byte of a file as it was only for `\\n` line endings. "
            f"Nothing was written."
        )
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
        text=text,
        offset=text.index("\n") + 1,
        front_matter=front_matter,
        artefact=same[0],
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


def _carrier_keys(artefact: Artefact) -> tuple[str, ...]:
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
    """A deferral entry's place in the list: by anchor kind, then value (COR-050 point 4)."""
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


def _in_order(entry: Mapping[str, Any]) -> dict[str, Any]:
    """A deferral entry with its keys in the schema's order — `anchor` (`kind`, `value`), `reason` —
    and nothing dropped: a key the schema refuses stays, for validation to name."""

    def ordered(mapping: Mapping[str, Any], first: tuple[str, ...]) -> dict[str, Any]:
        head = {k: mapping[k] for k in first if k in mapping}
        return head | {k: v for k, v in mapping.items() if k not in first}

    out = ordered(entry, ("anchor", "reason"))
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
    target: str  # what is written, as a dotted path inside the carrier
    rel: str
    path: Path
    before: str
    after: str
    items: tuple[str, ...]  # what the write says, one line each
    first_line: int = 0
    last_line: int = 0
    unchanged: str | None = None
    notes: tuple[str, ...] = ()  # said before the write, never about it

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

    source = _read_source(target_root, find_artefact(target_root, reference))
    artefact = source.artefact
    _friction_block(artefact)
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
            kept.append(_in_order(entry))
            items.append(f"keeps deferral {label}   ({reason})")
        else:
            items.append(f"removes deferral {label}   ({reason})")
    return kept, items


def plan_defer(target_root: Path, reference: str, *, anchor: str, reason: str) -> Plan:
    """The write of `pkit friction defer` (COR-050 point 4).

    Adds one entry to `deferred` — or rewords the reason of the entry already
    deferring that anchor, which keeps its deferral point — and keeps the
    list sorted. `at`, `outcome` and `unchanged-because` are left byte for
    byte: a deferral is not a revalidation, and an artefact never revalidated
    gets a `revalidated` block holding `deferred` alone. Refused: an empty
    anchor or reason, a reason with a placeholder left unfilled, and an anchor
    the artefact does not carry.
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

    source = _read_source(target_root, find_artefact(target_root, reference))
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
        _in_order(e) if isinstance(e, Mapping) else e for e in entries if _entry_anchor(e) != named
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


def plan_record_status(target_root: Path, reference: str) -> Plan:
    """The write of `pkit friction record-status` (COR-050 point 10).

    Runs the whole-repository check at HEAD and writes the artefact's
    `last-check`: its `state` (stale wins over deferred), `as-of` HEAD, and,
    when stale, `since` — the oldest commit its staleness comes from. Nothing
    is written when the recorded `state` and `since` already say so, whatever
    `as-of` holds. Refused: an artefact with no anchors or deferrals (there is
    no state), one not at HEAD, and one whose points lie beyond a shallow
    clone's history.
    """
    source = _read_source(target_root, find_artefact(target_root, reference))
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
        before=source.text,
        after=source.text,
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
    carrier = _carrier_keys(source.artefact)
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
        before=source.text,
        after=after,
        items=items,
        first_line=first,
        last_line=last,
        notes=notes,
    )


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
    try:
        root = YAML().compose(io.StringIO(fm))
    except YAMLError as exc:  # pragma: no cover — discovery has already parsed it
        raise FrictionWriteError(f"{source.rel}: front matter does not parse: {exc}") from exc
    parent = root
    for step in keys:
        pair = _pair(parent, step) if isinstance(parent, MappingNode) else None
        if pair is None:
            raise FrictionWriteError(
                f"{source.artefact.location}: cannot find `{'.'.join(keys)}` written in the file "
                f"(is it reached through a YAML alias or merge key?); edit the block by hand. "
                f"Nothing was written."
            )
        parent = pair[1]
    if not isinstance(parent, MappingNode):
        raise FrictionWriteError(
            f"{source.artefact.location}: `{'.'.join(keys)}` is not a mapping; fix it first — "
            f"`pkit validate` reports it. Nothing was written."
        )
    existing = _pair(parent, key)
    if parent.flow_style:
        return _flow_splice(parent, existing, keys[-1], key, value)
    return _block_splice(fm, parent, existing, keys[-1], key, value, source)


def _pair(mapping: MappingNode, key: str) -> tuple[Node, Node] | None:
    for key_node, value_node in mapping.value:
        if isinstance(key_node, ScalarNode) and key_node.value == key:
            return key_node, value_node
    return None


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
        key_node, value_node = existing
        return _Splice(key_node.start_mark.index, _pair_end(key_node, value_node), written)
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
        for f in block_findings(a, schema, target_root)
        if f.severity is bs.Severity.ERROR
    ]
    if len(written) != 1 or errors:
        detail = "; ".join(f"{f.pointer or '(block)'}: {f.message}" for f in errors)
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
    lines.append(f"  Writes {plan.target} in {plan.rel}   ({span}; nothing else in the file)")
    lines.extend(f"    {item}" for item in plan.items)
    return "\n".join(lines) + "\n"


def render_diff(plan: Plan) -> str:
    """The write as a unified diff of the file."""
    diff = difflib.unified_diff(
        plan.before.splitlines(keepends=True),
        plan.after.splitlines(keepends=True),
        fromfile=f"a/{plan.rel}",
        tofile=f"b/{plan.rel}",
    )
    return "".join(diff)


def apply(plan: Plan, *, yes: bool, dry_run: bool, can_ask: bool, rerun: Sequence[str]) -> bool:
    """Show the plan and, with consent, write it; returns whether the file was written.

    `rerun` is the command as run, without `--yes` or `--dry-run`, for the
    refusal to name. A plan with nothing to write writes nothing and succeeds.
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
            raise ConsentRefused(
                f"refusing to write {plan.rel} without consent: stdin is not a terminal and "
                f"--yes was not given (COR-050 point 13). Nothing was written.\n"
                f"To see the change first, run:\n  {command_line(*rerun, '--dry-run')}\n"
                f"To consent non-interactively, run:\n  {command_line(*rerun, '--yes')}"
            )
        click.echo("")
        click.echo(render_diff(plan), nl=False)
        click.confirm(f"Write this to {plan.rel}?", default=True, abort=True)
    write(plan)
    click.echo(f"Wrote {plan.target} in {plan.rel}.")
    return True


def write(plan: Plan) -> None:
    """Write the plan's file atomically, keeping its mode; refuse if it changed since read."""
    try:
        current = plan.path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FrictionWriteError(f"cannot read {plan.rel}: {exc}. Nothing was written.") from exc
    if current != plan.before:
        raise FrictionWriteError(
            f"{plan.rel} changed since it was read; run the command again. Nothing was written."
        )
    mode = stat.S_IMODE(plan.path.stat().st_mode)
    tmp = plan.path.with_name(plan.path.name + ".pkit-tmp")
    try:
        tmp.write_bytes(plan.after.encode("utf-8"))
        os.chmod(tmp, mode)
        os.replace(tmp, plan.path)
    finally:
        tmp.unlink(missing_ok=True)


__all__ = [
    "OUTCOMES",
    "ConsentRefused",
    "FrictionWriteError",
    "Plan",
    "apply",
    "ask_keep",
    "command_line",
    "find_artefact",
    "interactive",
    "plan_defer",
    "plan_record_status",
    "plan_revalidate",
    "render_diff",
    "render_plan",
    "write",
]
