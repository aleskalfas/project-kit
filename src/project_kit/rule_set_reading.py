"""The reading documents of the `rule-sets` group (COR-051 point 7; ADR-057 point 2).

Two reading commands give the reach walk's answer, which accepted rules bind
on an artefact, for a component's script or a migration to read rather than
walk routes or judge pins itself (ADR-057 point 1):

- `pkit rule-sets reach` (`reach_document`): the walk at one state — the
  working tree, or a commit named with `--at`. It lists each artefact on
  which an accepted rule binds, whose routes conflict, or from which a pin
  behind its set holds a rule back.
- `pkit rule-sets altered` (`altered_document`): the artefacts a change
  altered between a base and a head, with the walk's answer at each state
  that holds the artefact. The base is the change check's: the merge-base of
  the base `default_branch` resolves with the head (COR-054). The head is
  the working tree, or a commit named with `--head`. The diff and the pairing
  are the change check's own (`friction_check.read_diff`,
  `friction_check.pair_artefacts`), so an artefact is altered when it is
  added or removed, or its content differs. A move the pairing follows,
  keeping the content, alters nothing, and so does a change that only writes
  a revalidation. Each artefact also carries the rules the change brings it
  under, which bind on it at the head and did not at the base, and an
  artefact the change brings under a rule without altering it is listed
  apart (COR-057 point 2).

Each artefact carries its span and each rule its text, read at that state,
so a reader whose checkout is elsewhere has what it needs. Each part of a rule
a check is declared to enforce says whether that check is there
(`rule_sets.CheckPresence`, which validation reads too): a component's check
by the registrations of the state read, a backbone check by the `pkit` that
runs. Neither command
runs a query — no resolver, no filler — so git and the running tool's own
commands are all they read. Neither writes anything.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from project_kit import cli_render, default_branch
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.friction_git import SHORT, CommitTree
from project_kit.working_tree import WorkingTree

#: The version of the document `reach_document` returns. A change a reader could break
#: against — a key removed, renamed or given another meaning — raises it; a key added
#: does not.
REACH_SCHEMA_VERSION = 1

#: The version of the document `altered_document` returns, raised as the reach
#: document's is.
ALTERED_SCHEMA_VERSION = 1


# --- one state -------------------------------------------------------------------------


def reach_document(target_root: Path, commit: str | None = None) -> dict[str, Any]:
    """The walk at one state, as one stable document — what `pkit rule-sets reach --json`
    prints.

    - `commit`: the commit read, or `null` for the working tree.
    - `artefacts`: in discovery's walk order, each artefact on which an accepted
      rule binds, whose routes conflict, or from which a pin behind its set holds
      a rule back (`artefact_entry`). Any other artefact has no binding rule at
      this state.
    """
    tree = None if commit is None else CommitTree(target_root, commit)
    discovery, _rule_sets, answer = rs.reach_at(target_root, tree)
    presence = rs.CheckPresence(target_root, tree)
    return {
        "schema_version": REACH_SCHEMA_VERSION,
        "commit": commit,
        "artefacts": [
            artefact_entry(artefact, answer.of(artefact.location), presence)
            for artefact in discovery.artefacts
            if artefact.location in answer.by_location
        ],
    }


def artefact_entry(
    artefact: fd.Artefact, found: rs.ArtefactReach, presence: rs.CheckPresence
) -> dict[str, Any]:
    """One artefact and the walk's answer for it, at one state.

    - `location`, `path`, `id`, `kind` (`document` or `entry`): as the artefacts
      document names it (`pkit friction artefacts`).
    - `span`: for an entry, the lines of its file its section spans,
      `{first_line, last_line}`; `null` for a document.
    - `rules`: each accepted rule that binds on it (`rule_entry`), in path and
      written order.
    - `conflicts`: each conflict between its routes (`conflict_entry`).
    - `held`: each accepted rule a pin behind its set holds back from it
      (`held_entry`), in path and written order. It binds nothing.
    """
    span = artefact.span
    return {
        "location": artefact.location,
        "path": artefact.path,
        "id": artefact.id,
        "kind": artefact.kind.value,
        "span": None
        if span is None
        else {"first_line": span.first_line, "last_line": span.last_line},
        "rules": [rule_entry(binding, presence) for binding in found.bindings],
        "conflicts": [conflict_entry(conflict) for conflict in found.conflicts],
        "held": [held_entry(held) for held in found.held],
    }


def rule_entry(binding: rs.Binding, presence: rs.CheckPresence) -> dict[str, Any]:
    """One binding rule.

    - `rule`: its id as cited, the component in front for a method rule set;
      `id`: the bare id; `status`: `accepted`.
    - `rule_set`: its set as cited; `rule_set_path`: the set's file.
    - `covering`: the files of the project's own sets whose scope selects the
      artefact and from which a route reaches the rule's set.
    - `fills`: the extension points it binds as the fill of, as cited.
    - `checks`: the parts of it checks enforce, as its owner declares them,
      each `{check, part, there, problem}` (`check_entry`).
    - `text`: its section, headed by its id: the statement.
    """
    rule, rule_set = binding.rule, binding.rule_set
    return {
        "rule": rule_set.cite(rule.id),
        "id": rule.id,
        "status": rule.status,
        "rule_set": rule_set.citation,
        "rule_set_path": rule_set.path,
        "covering": [covering.path for covering in binding.covering],
        "fills": list(binding.fills),
        "checks": [check_entry(part, presence) for part in rule.checks],
        "text": rule.section,
    }


def check_entry(part: rs.CheckPart, presence: rs.CheckPresence) -> dict[str, Any]:
    """One part of a rule a check is declared to enforce (COR-051 point 2): `check` and
    `part` as declared, `there` whether the check is there, and `problem` why it is not,
    else `null`. A part whose check is not there goes back to whoever judges the rest of
    the rule."""
    problem = presence.problem(part)
    return {"check": part.check, "part": part.part, "there": problem is None, "problem": problem}


def held_entry(held: rs.HeldRule) -> dict[str, Any]:
    """One accepted rule a pin behind its set holds back (COR-051 point 7).

    - `rule`, `id`, `status`, `rule_set`, `rule_set_path`: as a binding rule's.
    - `pins`: each pin behind its set that leads towards the rule's set,
      `{by, by_rule_set, pin}`.
    - `text`: its section, headed by its id: the statement.
    """
    rule, rule_set = held.rule, held.rule_set
    return {
        "rule": rule_set.cite(rule.id),
        "id": rule.id,
        "status": rule.status,
        "rule_set": rule_set.citation,
        "rule_set_path": rule_set.path,
        "pins": [
            {"by": by.path, "by_rule_set": by.citation, "pin": str(pin)}
            for by, _index, pin in held.pins
        ],
        "text": rule.section,
    }


def conflict_entry(conflict: rs.Conflict) -> dict[str, Any]:
    """One conflict between the routes to an artefact (COR-051 point 7).

    - `{"kind": "pin", "rule_set", "rule_set_path", "version", "pins"}`: one set
      pinned at different majors; `pins` lists each pin on the routes,
      `{by, by_rule_set, pin}`.
    - `{"kind": "fill", "point", "brought"}`: the most specific sets bring
      different fills for one extension point; `brought` lists each set,
      `{by, by_rule_set, fills}`, `fills` the fills it brings, as cited.
    """
    if isinstance(conflict, rs.PinConflict):
        return {
            "kind": "pin",
            "rule_set": conflict.rule_set.citation,
            "rule_set_path": conflict.rule_set.path,
            "version": conflict.rule_set.version,
            "pins": [
                {"by": by.path, "by_rule_set": by.citation, "pin": str(pin)}
                for by, _index, pin in conflict.pins
            ],
        }
    return {
        "kind": "fill",
        "point": conflict.point,
        "brought": [
            {
                "by": by.path,
                "by_rule_set": by.citation,
                "fills": [held.cite(rule.id) for held, rule in fills],
            }
            for by, fills in conflict.brought
        ],
    }


# --- between a base and a head -----------------------------------------------------------


def altered_document(
    target_root: Path,
    base_ref: str | None = None,
    *,
    resolved: default_branch.Base | None = None,
    named: fc.HeadState | None = None,
) -> dict[str, Any]:
    """The artefacts a change altered, with the walk's answer at each state that holds
    them — what `pkit rule-sets altered --json` prints.

    The base is the merge-base of `base_ref` — else `$PKIT_CHECK_BASE`, else the
    default branch — with the head, as the change check takes it
    (`friction_check.resolve_base`); `resolved` is that base when the caller has read
    it already. The head is the working tree, or the commit `named` with `--head`.

    - `base`: `{ref, tip, commit, outdated}`, as the change check's document has it.
    - `head`: `{commit, uncommitted_paths, working_tree}`: HEAD and the paths the
      working tree changes beyond it, or the commit named with none;
      `working_tree` says which.
    - `artefacts`: each artefact the change altered, in the head's walk order, then
      those it removed in the base's: `{change, base, head, brought_under}`,
      `change` being `added`, `removed` or `changed`, and `base` and `head` the
      artefact at that state with the walk's answer there (`artefact_entry`) —
      `null` where that state does not hold it. An artefact with no binding rule at
      either state is listed too, with no rules. `brought_under` lists the rules
      the change brings it under (`brought_under`).
    - `brought_unaltered`: each artefact the change brought under a rule without
      altering it, in the head's walk order, in the same form, `change` being
      `unaltered`: a scope widened, a rule accepted, a pin updated or a place typed,
      or a move the pairing follows into a set's paths.

    Raises `FrictionCheckError` when the base cannot be compared, as the change check does.
    """
    head_tree: fd.RepositoryTree = (
        WorkingTree(target_root) if named is None else CommitTree(target_root, named.commit)
    )
    base_state = fc.resolve_base(target_root, base_ref, resolved=resolved, head=named)
    diff = fc.read_diff(target_root, base_state.commit, named)
    base_tree = CommitTree(target_root, base_state.commit)
    head_discovery, _head_sets, head_reach = rs.reach_at(target_root, head_tree)
    base_discovery, _base_sets, base_reach = rs.reach_at(target_root, base_tree)
    base_presence = rs.CheckPresence(target_root, base_tree)
    head_presence = rs.CheckPresence(target_root, None if named is None else head_tree)
    pairing = fc.pair_artefacts(base_discovery, head_discovery, diff)
    head = fc.HeadState(fc.head_commit(target_root), diff.uncommitted) if named is None else named

    def brought(before: fd.Artefact | None, after: fd.Artefact | None) -> list[str]:
        return brought_under(
            None if before is None else base_reach.of(before.location),
            None if after is None else head_reach.of(after.location),
        )

    def entry(
        change: str, before: fd.Artefact | None, after: fd.Artefact | None, rules: list[str]
    ) -> dict[str, Any]:
        return {
            "change": change,
            "base": None
            if before is None
            else artefact_entry(before, base_reach.of(before.location), base_presence),
            "head": None
            if after is None
            else artefact_entry(after, head_reach.of(after.location), head_presence),
            "brought_under": rules,
        }

    # Most unaltered artefacts are brought under nothing, so only those that are get an
    # entry, with the rule texts it carries.
    unaltered = [
        (before, after, rules)
        for before, after in pairing.unaltered
        if (rules := brought(before, after))
    ]
    return {
        "schema_version": ALTERED_SCHEMA_VERSION,
        "base": {
            "ref": base_state.ref,
            "tip": base_state.tip,
            "commit": base_state.commit,
            "outdated": base_state.outdated,
        },
        "head": {
            "commit": head.commit,
            "uncommitted_paths": head.uncommitted,
            "working_tree": named is None,
        },
        "artefacts": [
            entry(
                alteration.kind,
                alteration.before,
                alteration.after,
                brought(alteration.before, alteration.after),
            )
            for alteration in pairing.altered
        ],
        "brought_unaltered": [
            entry(UNALTERED, before, after, rules) for before, after, rules in unaltered
        ],
    }


#: How `altered_document` lists an artefact the change brought under a rule without
#: altering it, beside `added`, `removed` and `changed`.
UNALTERED = "unaltered"


def brought_under(base: rs.ArtefactReach | None, head: rs.ArtefactReach | None) -> list[str]:
    """The rules a change brings one artefact under (COR-057 point 2): each accepted rule
    that binds on it at the head and did not bind on it at the base, as cited, in the
    head's order. `base` is the walk's answer for the artefact at the base, `None` where
    the base does not hold it, so an added artefact is brought under every rule that
    binds on it. `head` is `None` for a removed artefact, brought under none. A rule a pin
    behind its set held back at the base bound nothing there, so a pin updated to reach
    it brings the artefact under it."""
    if head is None:
        return []
    before: set[str] = set() if base is None else {_cited(b) for b in base.bindings}
    return [cited for cited in dict.fromkeys(map(_cited, head.bindings)) if cited not in before]


def _cited(binding: rs.Binding) -> str:
    return binding.rule_set.cite(binding.rule.id)


# --- rendering ---------------------------------------------------------------------------


def render_json(document: Mapping[str, Any]) -> str:
    """Either document, as the stable JSON a script reads."""
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def render_reach_human(document: Mapping[str, Any]) -> str:
    """The read view of the walk at one state: each artefact with the rules that bind on
    it and the sets whose scope it reaches them through."""
    commit = document["commit"]
    state = "the working tree" if commit is None else f"commit {commit[:SHORT]}"
    lines = [cli_render.style("title", "Rules that bind on each artefact") + f" — {state}", ""]
    artefacts = document["artefacts"]
    if not artefacts:
        lines.append("  no accepted rule binds on any artefact")
    for artefact in artefacts:
        lines.append(f"  {artefact['location']}")
        lines.extend(_answer_lines(artefact, "    "))
    rules = {rule["rule"] for artefact in artefacts for rule in artefact["rules"]}
    lines.extend(["", f"{len(artefacts)} artefact(s), {len(rules)} rule(s) binding."])
    return "\n".join(lines) + "\n"


def render_altered_human(document: Mapping[str, Any]) -> str:
    """The read view of what a change altered: each artefact, how it was altered, and the
    rules that bind on it at the base and at the head."""
    base, head = document["base"], document["head"]
    head_name = (
        f"the working tree at {head['commit'][:SHORT]}"
        if head["working_tree"]
        else f"commit {head['commit'][:SHORT]}"
    )
    lines = [
        cli_render.style("title", "Artefacts the change altered")
        + f" — base {base['ref']} at {base['commit'][:SHORT]}, head {head_name}",
        "",
    ]
    if base["outdated"]:
        lines.append(
            cli_render.style(
                "warn",
                "  the base moved on after this branch left it; merge or "
                "rebase onto it for results that hold",
            )
        )
    artefacts = document["artefacts"]
    brought = document["brought_unaltered"]
    if not artefacts:
        lines.append("  the change altered no artefact")
    for entry in artefacts:
        lines.extend(_altered_lines(entry))
    if brought:
        lines.extend(["", "  Brought under a rule, unaltered:"])
    for entry in brought:
        lines.extend(_altered_lines(entry))
    ruled = sum(
        1
        for entry in artefacts
        if any(entry[side] is not None and entry[side]["rules"] for side in ("base", "head"))
    )
    lines.extend(
        [
            "",
            f"{len(artefacts)} artefact(s) altered, {ruled} with a binding rule; "
            f"{len(brought)} brought under a rule unaltered.",
        ]
    )
    return "\n".join(lines) + "\n"


def _altered_lines(entry: Mapping[str, Any]) -> list[str]:
    """One artefact of the change: how it was altered, the rules that bind on it at the
    base and at the head, and the rules the change brings it under."""
    shown = entry["head"] if entry["head"] is not None else entry["base"]
    lines = [f"  {entry['change']:<9} {shown['location']}"]
    for side in ("base", "head"):
        if entry[side] is None:
            continue
        if not entry[side]["rules"] and not entry[side]["conflicts"]:
            lines.append(f"    at the {side}: no rule binds")
        else:
            lines.append(f"    at the {side}:")
        lines.extend(_answer_lines(entry[side], "      "))
    if entry["brought_under"]:
        lines.append(f"    brought under: {', '.join(entry['brought_under'])}")
    return lines


def _answer_lines(artefact: Mapping[str, Any], indent: str) -> list[str]:
    lines: list[str] = []
    for rule in artefact["rules"]:
        through = ", ".join(rule["covering"])
        fills = f", fills {', '.join(rule['fills'])}" if rule["fills"] else ""
        lines.append(f"{indent}{rule['rule']}  ({rule['rule_set']}{fills})  through {through}")
        for part in rule["checks"]:
            missing = "" if part["there"] else f"  (not there: {part['problem']})"
            lines.append(f"{indent}  checked by {part['check']}: {part['part']}{missing}")
    for conflict in artefact["conflicts"]:
        if conflict["kind"] == "pin":
            pins = ", ".join(f"{pin['by_rule_set']} pins {pin['pin']}" for pin in conflict["pins"])
            lines.append(
                f"{indent}conflict: {conflict['rule_set']} pinned at different majors ({pins})"
            )
        else:
            brought = ", ".join(
                f"{by['by_rule_set']} brings {' and '.join(by['fills']) or 'none'}"
                for by in conflict["brought"]
            )
            lines.append(
                f"{indent}conflict: different fills for {conflict['point']} ({brought}); "
                f"no fill binds"
            )
    for held in artefact["held"]:
        pins = ", ".join(f"{pin['by_rule_set']} pins {pin['pin']}" for pin in held["pins"])
        lines.append(
            f"{indent}{held['rule']}  ({held['rule_set']})  held back, binding nothing: {pins}"
        )
    return lines
