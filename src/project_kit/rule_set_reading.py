"""The reading documents of the `rule-sets` group (COR-051 point 7; ADR-057 point 2).

Two reading commands give the reach walk's answer, which accepted rules bind
on an artefact, for a component's script or a migration to read rather than
walk routes or judge pins itself (ADR-057 point 1):

- `pkit rule-sets reach` (`reach_document`): the walk at one state — the
  working tree, or a commit named with `--at`. It lists each artefact on
  which an accepted rule binds, whose routes conflict, or from which a pin
  behind its set holds a rule back. Given paths, it lists only the artefacts
  at those paths, and says for each path what the state holds there
  (`path_entry`), so a writer can read the rules of its files before it
  writes them. With `--preview`, the walk takes every proposed rule as
  accepted, and marks what holds only under the preview. Validation and
  every gate read the answer without it.
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

import bisect
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from project_kit import cli_render, default_branch
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.friction_git import SHORT, CommitTree
from project_kit.working_tree import WorkingTree, working_tree

#: The version of the document `reach_document` returns. A change a reader could break
#: against — a key removed, renamed or given another meaning — raises it; a key added
#: does not.
REACH_SCHEMA_VERSION = 1

#: The version of the document `altered_document` returns, raised as the reach
#: document's is.
ALTERED_SCHEMA_VERSION = 1


# --- one state -------------------------------------------------------------------------


def reach_document(
    target_root: Path,
    commit: str | None = None,
    *,
    preview: bool = False,
    paths: Sequence[str] | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """The walk at one state, as one stable document — what `pkit rule-sets reach --json`
    prints.

    - `commit`: the commit read, or `null` for the working tree.
    - `preview`: whether the walk took every proposed rule as accepted
      (`rule_sets.PREVIEW`). A superseded or withdrawn rule binds nothing either way.
    - `paths`: `null` when no path is given. Given `paths`, each read from `cwd` (the
      root by default) when relative, each path in the order given, with what the
      state holds there (`path_entry`).
    - `artefacts`: in discovery's walk order, each artefact on which a rule binds,
      whose routes conflict, or from which a pin behind its set holds a rule back
      (`artefact_entry`); given `paths`, only those at a path given. Any other
      artefact has no binding rule at this state.

    The walk is the same either way: the paths only narrow its answer.
    """
    tree = None if commit is None else CommitTree(target_root, commit)
    discovery, _rule_sets, answer = rs.reach_at(target_root, tree, preview=preview)
    presence = rs.CheckPresence(target_root, tree)
    given = (
        None
        if paths is None
        else _given_paths(target_root, discovery, tree, paths, target_root if cwd is None else cwd)
    )
    selected = None if given is None else {at for entry in given for at in entry["artefacts"]}
    return {
        "schema_version": REACH_SCHEMA_VERSION,
        "commit": commit,
        "preview": answer.preview,
        "paths": given,
        "artefacts": [
            artefact_entry(artefact, answer.of(artefact.location), presence)
            for artefact in discovery.artefacts
            if artefact.location in answer.by_location
            and (selected is None or artefact.location in selected)
        ],
    }


# What the state holds at a path given to `pkit rule-sets reach` (`path_entry`).

#: One artefact or more: a document, or the entries of a collection file.
ARTEFACT = "artefact"
#: A file that is no artefact: no declared place walks it, so no rule set selects it.
NOT_ARTEFACT = "not-artefact"
#: A file a declared place matches whose front matter does not parse: `pkit validate`
#: reports it.
UNREADABLE = "unreadable"
#: Files beneath it, none at it.
FOLDER = "folder"
#: No file at it, and none beneath it.
ABSENT = "absent"
#: A path outside the repository.
OUTSIDE = "outside"


def path_entry(
    given: str,
    path: str | None,
    artefacts: Sequence[str],
    *,
    unreadable: bool,
    files: Sequence[str],
) -> dict[str, Any]:
    """One path given to `pkit rule-sets reach`, with what the state holds there.

    - `given`: the path as given.
    - `path`: the repository-relative POSIX path it names, `.` for the root, or `null`
      outside the repository.
    - `answer`: what the state holds at the path, the first that holds: `outside` the
      repository; an `artefact`, or several entries of one collection file; a file
      `unreadable` as an artefact; a file that is `not-artefact`; a `folder`, with
      files beneath it; else `absent`.
    - `artefacts`: the locations of the artefacts at the path, in walk order. Those on
      which a rule binds, whose routes conflict or from which a rule is held back are
      the document's `artefacts`; on any other, no rule binds.

    `unreadable` says whether the walk could not read the file at `path`, and `files`
    are the sorted files of the state read, links included.
    """
    if path is None:
        answer = OUTSIDE
    elif artefacts:
        answer = ARTEFACT
    elif unreadable:
        answer = UNREADABLE
    elif _first_from(files, path) == path:
        answer = NOT_ARTEFACT
    elif _holds_beneath(files, path):
        answer = FOLDER
    else:
        answer = ABSENT
    return {"given": given, "path": path, "answer": answer, "artefacts": list(artefacts)}


def _holds_beneath(files: Sequence[str], path: str) -> bool:
    """Whether a file of the sorted `files` lies beneath the folder `path`, `.` the root."""
    if path == ".":
        return bool(files)
    return _first_from(files, f"{path}/").startswith(f"{path}/")


def _first_from(files: Sequence[str], start: str) -> str:
    """The first of the sorted `files` that is not before `start`, or `""`."""
    index = bisect.bisect_left(files, start)
    return files[index] if index < len(files) else ""


def repository_path(target_root: Path, given: str, cwd: Path) -> str | None:
    """The repository-relative POSIX path that `given` names, read from `cwd` when it is
    relative: `.` for the root, `None` outside the repository. It need not exist. Only
    the folders above its last part are resolved, so a link is named, never followed."""
    candidate = Path(os.path.normpath(given if os.path.isabs(given) else cwd / given))
    named = Path(os.path.realpath(candidate.parent)) / candidate.name
    try:
        return named.relative_to(target_root.resolve()).as_posix()
    except ValueError:
        return None


def _given_paths(
    target_root: Path,
    discovery: fd.Discovery,
    tree: CommitTree | None,
    paths: Sequence[str],
    cwd: Path,
) -> list[dict[str, Any]]:
    """Each path given, in order, with what the state `discovery` walked holds there."""
    at_path: dict[str, list[str]] = {}
    for artefact in discovery.artefacts:
        at_path.setdefault(artefact.path, []).append(artefact.location)
    unreadable = {found.path for found in discovery.unreadable}
    files = (working_tree(target_root) if tree is None else tree).files()
    entries: list[dict[str, Any]] = []
    for given in paths:
        path = repository_path(target_root, given, cwd)
        entries.append(
            path_entry(
                given,
                path,
                [] if path is None else at_path.get(path, []),
                unreadable=path is not None and path in unreadable,
                files=files,
            )
        )
    return entries


def artefact_entry(
    artefact: fd.Artefact, found: rs.ArtefactReach, presence: rs.CheckPresence
) -> dict[str, Any]:
    """One artefact and the walk's answer for it, at one state.

    - `location`, `path`, `id`, `kind` (`document` or `entry`): as the artefacts
      document names it (`pkit friction artefacts`).
    - `span`: for an entry, the lines of its file its section spans,
      `{first_line, last_line}`; `null` for a document.
    - `rules`: each rule that binds on it (`rule_entry`), in path and written
      order: an accepted one, and in a preview a proposed one too.
    - `conflicts`: each conflict between its routes (`conflict_entry`).
    - `held`: each rule a pin behind its set holds back from it (`held_entry`), in
      path and written order. It binds nothing.
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
      `id`: the bare id; `status`: its written status, `accepted`, or in a
      preview `proposed` too.
    - `previewed`: whether it binds here only under the preview: the answer
      without the preview does not bind it here. Always `false` without the
      preview.
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
        "previewed": binding.previewed,
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
    """One rule a pin behind its set holds back (COR-051 point 7).

    - `rule`, `id`, `status`, `rule_set`, `rule_set_path`, `previewed`: as a binding
      rule's. A held rule is previewed when it is proposed.
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
        "previewed": held.previewed,
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
    - `previewed`: whether the conflict stands only under the preview. A pin
      conflict depends on no status, so it is never previewed.
    """
    if isinstance(conflict, rs.PinConflict):
        return {
            "kind": "pin",
            "previewed": False,
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
        "previewed": conflict.previewed,
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
    it and the sets whose scope it reaches them through. A preview says so in its title,
    and marks what holds only under it. Given paths, each path with what the state holds
    there, then the text of each rule that binds (`_paths_lines`)."""
    commit = document["commit"]
    preview = document.get("preview") is True
    given = document.get("paths")
    state = "the working tree" if commit is None else f"commit {commit[:SHORT]}"
    on = "each artefact" if given is None else "the paths given"
    title = (
        f"Rules that would bind on {on}, every proposed rule taken as accepted"
        if preview
        else f"Rules that bind on {on}"
    )
    lines = [cli_render.style("title", title) + f" — {state}", ""]
    artefacts = document["artefacts"]
    statuses = "accepted or proposed" if preview else "accepted"
    if given is not None:
        lines.extend(_paths_lines(given, artefacts, state, statuses))
    else:
        if not artefacts:
            lines.append(f"  no {statuses} rule binds on any artefact")
        for artefact in artefacts:
            lines.append(f"  {artefact['location']}")
            lines.extend(_answer_lines(artefact, "    "))
    rules = {rule["rule"] for artefact in artefacts for rule in artefact["rules"]}
    binding = {
        rule["rule"]
        for artefact in artefacts
        for rule in artefact["rules"]
        if not rule.get("previewed")
    }
    only = f", {len(rules - binding)} only under the preview" if preview else ""
    counted = "" if given is None else f"{len(given)} path(s), "
    lines.extend(
        ["", f"{counted}{len(artefacts)} artefact(s), {len(rules)} rule(s) binding{only}."]
    )
    return "\n".join(lines) + "\n"


def _paths_lines(
    given: Sequence[Mapping[str, Any]],
    artefacts: Sequence[Mapping[str, Any]],
    state: str,
    statuses: str,
) -> list[str]:
    """Each path given, once, with the rules that bind on each artefact there or why none
    does; then the text of each rule that binds, once, so a writer can follow the rules of
    its files without reading another file. The entries of one collection file that have
    the same answer are listed together."""
    by_location = {artefact["location"]: artefact for artefact in artefacts}
    unruled = (f"    no {statuses} rule binds on it",)
    why = {
        NOT_ARTEFACT: "no declared place holds it as an artefact, so no rule set selects it",
        UNREADABLE: "a declared place holds it, but its front matter does not parse: "
        "`pkit validate` reports it",
        FOLDER: "a folder: give the files in it",
        ABSENT: f"{state} holds no file here, so no rule binds on it",
        OUTSIDE: "outside the repository, so no rule binds on it",
    }
    lines: list[str] = []
    shown: set[str] = set()
    for entry in given:
        named = entry["given"] if entry["path"] is None else entry["path"]
        if named in shown:
            continue
        shown.add(named)
        if entry["answer"] != ARTEFACT:
            lines.extend([f"  {named}", f"    {why[entry['answer']]}"])
            continue
        alike: dict[tuple[str, ...], list[str]] = {}
        for at in entry["artefacts"]:
            answer = tuple(_answer_lines(by_location[at], "    ")) if at in by_location else unruled
            alike.setdefault(answer, []).append(at)
        for answer, locations in alike.items():
            lines.append(f"  {_artefacts_named(named, locations, len(entry['artefacts']))}")
            lines.extend(answer)
    texts = {rule["rule"]: rule for artefact in artefacts for rule in artefact["rules"]}
    if texts:
        lines.extend(["", "The text of each rule that binds:"])
    for cited, rule in texts.items():
        lines.extend(["", f"  {cited}  ({rule['rule_set']}, {rule['status']})"])
        lines.extend(
            f"    {line}" if line.strip() else "" for line in rule["text"].rstrip().splitlines()
        )
    return lines


def _artefacts_named(path: str, locations: Sequence[str], at_path: int) -> str:
    """How the read view names artefacts at `path` that have one answer: a document, or an
    entry, by its location; several entries of the file by their ids, or as each of its
    entries where they are all `at_path` of them."""
    if len(locations) == 1:
        return locations[0]
    if len(locations) == at_path:
        return f"{path}, each of its {at_path} entries"
    ids = ", ".join(location.removeprefix(f"{path}#") for location in locations)
    return f"{path}, entries {ids}"


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
        lines.append(
            f"{indent}{rule['rule']}  ({rule['rule_set']}{fills})  through {through}"
            f"{_PREVIEWED if rule.get('previewed') else ''}"
        )
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
                f"no fill binds{_PREVIEWED if conflict.get('previewed') else ''}"
            )
    for held in artefact["held"]:
        pins = ", ".join(f"{pin['by_rule_set']} pins {pin['pin']}" for pin in held["pins"])
        lines.append(
            f"{indent}{held['rule']}  ({held['rule_set']})  held back, binding nothing: {pins}"
            f"{_PREVIEWED if held.get('previewed') else ''}"
        )
    return lines


#: How the read view marks what holds only under a preview.
_PREVIEWED = "  (previewed)"
