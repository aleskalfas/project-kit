"""Documents, configuration and history for the friction tests (COR-050, COR-062).

Shared by the change-check, whole-repository-check and report tests: a
backbone configuration with a `friction` key, Markdown documents whose front
matter carries the `friction` block, and a `Timeline` laying down dated
commits. Front matter is written as JSON — valid YAML, and exact about
strings — so a test says precisely what an artefact holds.

**Answers.** A document here says an artefact's answers beside its anchors, as
the block held them before the move (`document`'s `at`, `outcome`, `because`
and `deferred`). A change writes them in answer files of its own (COR-062 point
1), so a test module that uses the fixture `answers_in_files` has every write
of an adopter repository take them out of the block into answer files, as a
change writes them (`settle_answers`): a new answer file whose entry names, in
`read`, every answer file present on the artefact, or the one no commit holds
yet, rewritten.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import answer_files as af
from project_kit import backbone_schemas as bs
from project_kit import friction_move
from project_kit.document_parts import split_front_matter
from project_kit.friction_discovery import (
    FRICTION_KEY,
    REVISITED_KEY,
    Anchor,
    Artefact,
    ArtefactKind,
    discover_artefacts,
    link_targets,
)
from project_kit.friction_write import (
    DEFERRAL_KEYS,
    REVALIDATED,
    REVISIT_KEYS,
    answer_file_text,
    carrier_keys,
    in_order,
    ordered_revalidation,
    without_key,
)
from project_kit.line_breaks import line_break, universal_newlines
from tests.adopter_repo import HISTORY_EPOCH, AdopterRepo, Author, GitRepo

CONFIG = ".pkit/project/config.yaml"
T1 = "2026-10-01T09:00:00Z"
T2 = "2026-10-02T09:40:12Z"
SOURCE = {"src/cli/main.py": "print('cli')\n", "src/core/engine.py": "ENGINE = 1\n"}


def friction_config(
    mode: str = "warning", places: tuple[str, ...] = ("docs",), **friction: Any
) -> str:
    """The backbone configuration file with a `friction` key: mode, places, and the rest."""
    block: dict[str, Any] = {"mode": mode, "places": list(places), **friction}
    return json.dumps({"name": "adopter", "friction": block}, indent=2) + "\n"


def document(
    artefact_id: str | None,
    *,
    anchors: dict[str, list[str]] | None = None,
    at: str | None = None,
    outcome: str | None = None,
    because: str | None = None,
    deferred: list[tuple[str, str, str]] | None = None,
    unanchored_because: str | None = None,
    body: str = "Body.",
    **fields: Any,
) -> str:
    """A document whose front matter carries the `friction` block, as JSON."""
    front: dict[str, Any] = {} if artefact_id is None else {"id": artefact_id}
    front.update(fields)
    revalidated: dict[str, Any] = {}
    if at is not None:
        revalidated["at"] = at
    if outcome is not None:
        revalidated["outcome"] = outcome
    if because is not None:
        revalidated["unchanged-because"] = because
    if deferred:
        revalidated["deferred"] = [
            {"anchor": {"kind": kind, "value": value}, "reason": reason}
            for kind, value, reason in deferred
        ]
    block: dict[str, Any] = {}
    if anchors is not None:
        block["anchors"] = anchors
    if unanchored_because is not None:
        block["unanchored-because"] = unanchored_because
    if revalidated:
        block["revalidated"] = revalidated
    front["pkit"] = {"friction": block}
    return f"---\n{json.dumps(front, indent=2)}\n---\n\n{body}\n"


def guide(**overrides: Any) -> str:
    """The workhorse artefact: `guide`, anchored to the CLI sources, revalidated at T1."""
    values: dict[str, Any] = {
        "anchors": {"path": ["src/cli/**"]},
        "at": T1,
        "outcome": "unchanged",
        "because": "the CLI surface is as described",
    }
    values.update(overrides)
    return document("guide", **values)


#: A project record whose points are headings, for anchors on one point (COR-050 point 2).
POINTED = ".pkit/decisions/project/PRJ-900-pointed.md"

#: Its points, in written order: id, title and text.
POINTS: tuple[tuple[str, str, str], ...] = (
    ("1", "First", "The first point."),
    ("2", "Second", "The second point."),
    ("3", "Third", "The third point."),
)


def pointed_record(
    points: tuple[tuple[str, str, str], ...] = POINTS,
    *,
    status: str = "accepted",
    title: str = "A pointed record",
    lead: str = "The record decides three things.",
    retired: Mapping[str, list[str]] | None = None,
    context: str = "Why it came up.",
    rationale: str = "Why this way.",
    preamble: str = "",
) -> str:
    """`PRJ-900`, its points written as headings in the order given (COR-058 point 1).

    A point whose title is `Retired` is a stub: give its text as the sentence
    its entry in `retired` gives (COR-058 point 4).
    """
    front: dict[str, Any] = {
        "id": "PRJ-900",
        "title": title,
        "status": status,
        "date": "2026-10-13",
        "author": "A. Author <a@example.com>",
    }
    if retired:
        front["retired-points"] = dict(retired)
    sections = "".join(f"### {pid}. {name}\n\n{text}\n\n" for pid, name, text in points)
    opening = f"{preamble}\n\n" if preamble else ""
    return (
        f"---\n{json.dumps(front, indent=2)}\n---\n\n{opening}## Context\n\n{context}\n\n"
        f"## Decision\n\n{lead}\n\n{sections}## Rationale\n\n{rationale}\n\n"
        f"## Implications\n\nNone.\n"
    )


#: An architectural record the place `docs` holds, so a record that is an artefact
#: (COR-050 point 1), found where the agents overlay names the ADR folder (`ADR_OVERLAY`).
ADR = "docs/architecture/decisions/ADR-007-recorded.md"
ADR_OVERLAY = {
    ".pkit/agents/project/overlay.yaml": "adr-records:\n  - docs/architecture/decisions/\n"
}

#: Its Decision, with two point headings, so an anchor may name its point 3.
ADR_DECISION = (
    "## Decision\n\nThe engine stays one module.\n\n### 1. One\n\nOne.\n\n### 3. Three\n\nThree.\n"
)


def adr(**overrides: Any) -> str:
    """`ADR-007` at `ADR`, carrying its own friction block: anchored to the engine and
    revalidated at T1, `outcome: updated`."""
    values: dict[str, Any] = {
        "anchors": {"path": ["src/core/**"]},
        "at": T1,
        "outcome": "updated",
        "title": "A recorded decision",
        "status": "accepted",
        "body": ADR_DECISION,
    }
    values.update(overrides)
    return document("ADR-007", **values)


#: An artefact the place `docs` holds, for path anchors on an artefact's file (COR-050
#: point 5, #1661): `notes`, anchored to the engine.
NOTES = "docs/notes.md"


def notes(**overrides: Any) -> str:
    """`notes` at `NOTES`, anchored to the engine and revalidated at T1, `outcome:
    updated`."""
    values: dict[str, Any] = {"anchors": {"path": ["src/core/**"]}, "at": T1, "outcome": "updated"}
    values.update(overrides)
    return document("notes", **values)


#: `notes` revalidated against an engine change, its content as it was: only its
#: container differs from `notes()`.
NOTES_HOLD = notes(at=T2, outcome="unchanged", because="the engine is still one module")


#: A document with a lead and sections, for anchors on one section or the lead (COR-050
#: point 2).
MANUAL = "docs/manual.md"

#: Its sections, in written order: heading and text.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("Installing", "Run the installer."),
    ("Using", "Run the tool."),
    ("Troubleshooting", "Ask for help."),
)


def manual(
    sections: tuple[tuple[str, str], ...] = SECTIONS,
    *,
    title: str = "A manual",
    lead: str = "What the manual is for.",
) -> str:
    """`docs/manual.md`, id `manual`: a first-level title, its lead, then each section as a
    second-level heading. It carries no friction block of its own."""
    front = {"id": "manual", "title": title}
    sections_text = "".join(f"## {heading}\n\n{text}\n\n" for heading, text in sections)
    return f"---\n{json.dumps(front, indent=2)}\n---\n\n# Manual\n\n{lead}\n\n{sections_text}"


#: A project record not yet converted, its points a numbered list (COR-058 point 2).
LISTED = ".pkit/decisions/project/PRJ-910-listed.md"


def listed_record() -> str:
    """`PRJ-910`, the points of `POINTS` written as a numbered list in its Decision's lead.

    An anchor on one of its points names nothing it can stand on, since a list's
    numbers are not permanent (COR-050 point 7).
    """
    items = "\n".join(f"{pid}. **{name}.** {text}" for pid, name, text in POINTS)
    return pointed_record((), title="A listed record", lead=items).replace("PRJ-900", "PRJ-910")


class Timeline:
    """Commits on an adopter repository, each a day after the last, so origins have known dates."""

    def __init__(self, adopter: AdopterRepo) -> None:
        self.adopter = adopter
        self.days = 0

    def _next(self) -> datetime:
        self.days += 1
        return HISTORY_EPOCH + timedelta(days=self.days)

    def start(self, files: Mapping[str, str], config: str | None = None) -> str:
        """The base commit on `main`: the install, the configuration, the sources and `files`."""
        self.adopter.write({CONFIG: config or friction_config(), **SOURCE, **files})
        return self.commit("base")

    def commit(
        self,
        message: str,
        files: Mapping[str, str | None] | None = None,
        *,
        author: Author | None = None,
    ) -> str:
        return self.adopter.commit(message, files, author=author, date=self._next())

    def commit_index(self, message: str) -> str:
        """Commit what the index holds — a gitlink staged with `git update-index`, say,
        which `commit` would stage away, having no checkout — dated as the next commit."""
        self.adopter.git("commit", "-q", "-m", message, date=self._next())
        return self.adopter.head()

    def rename(self, src: str, dst: str) -> str:
        return self.adopter.rename(src, dst, date=self._next())

    def merge(self, branch: str) -> str:
        return self.adopter.merge(branch, date=self._next())

    def squash_merge(self, branch: str) -> str:
        return self.adopter.squash_merge(branch, date=self._next())

    def revert(self, commit: str, *, mainline: int | None = None) -> str:
        """`git revert` of `commit`, dated as the next commit: what it changed, undone — for
        a merge commit, against its parent number `mainline`."""
        parent = () if mainline is None else ("-m", str(mainline))
        self.adopter.git("revert", "--no-edit", *parent, commit, date=self._next())
        return self.adopter.head()

    def cherry_pick(self, commit: str) -> str:
        """`git cherry-pick` of `commit` onto the current branch, dated as the next commit."""
        self.adopter.git("cherry-pick", commit, date=self._next())
        return self.adopter.head()


# --- answers in answer files (COR-062) ---------------------------------------------------

#: The keys of a block that held answers before the move (COR-062 point 1).
ANSWER_KEYS = (REVALIDATED, REVISITED_KEY)

#: How the answer files `settle_answers` adds are named: the prefix, then twelve
#: hexadecimal digits of the SHA-256 of the text, so one write always adds the same file.
SETTLED_PREFIX = "answer-"

_safe: Any = YAML(typ="safe")


class UnsettledAnswers(AssertionError):
    """A write `settle_answers` cannot make as a change makes it: write its answer files in
    the test itself."""


def answer_file_names(root: Path) -> list[str]:
    """The names of the answer files in the working tree at `root`, sorted."""
    folder = root / af.FOLDER
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if af.is_answer_file(f"{af.FOLDER}/{p.name}"))


def own_answer_file(root: Path) -> str:
    """The name of the change's own answer file: the one the working tree holds and no
    commit does, which the writers write into (ADR-068 point 3)."""
    committed = af.head_names(root)
    (name,) = [n for n in af.working_tree_files(root) if n not in committed]
    return name


def own_entry(root: Path, location: str) -> dict[str, Any]:
    """The entry for `location` in the change's own answer file (`own_answer_file`), as
    written; empty where it has none."""
    found = af.working_tree_files(root)[own_answer_file(root)]
    entries = cast(list[dict[str, Any]], found.document[af.ANSWERS_KEY])
    return next((dict(e) for e in entries if e[af.ARTEFACT_KEY] == location), {})


#: Whether writes leave answers in their blocks for now (`blocks_in_history`).
_HELD: list[bool] = [False]


@contextlib.contextmanager
def blocks_in_history() -> Iterator[None]:
    """Within it, each write leaves the artefacts' answers in their blocks, as a project's
    history before the move holds them: a test of how history is read lays such a history
    down, then moves the answers (`move_answers`) before a check reads the head (COR-062
    points 6 and 11)."""
    _HELD[0] = True
    try:
        yield
    finally:
        _HELD[0] = False


def move_answers(root: Path) -> None:
    """The move, as an upgrade makes it (COR-062 point 11): every answer the working tree's
    blocks hold, written into a moved answer file of its own and taken out of its block,
    left for the test to commit."""
    plan = friction_move.plan_move(root)
    for moved in plan.files:
        for answer in moved.answers:
            path = root / answer.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(answer.text.encode("utf-8"))
        (root / moved.path).write_bytes(moved.text.encode("utf-8"))


def settle_answers(root: Path, written: Iterable[str], *, taking: bool = True) -> None:
    """Take the answers out of the blocks of the artefacts in the files `written` — those a
    test just wrote — into answer files, as a change writes them (COR-062 points 1, 4 and 5).
    With `taking` false, only an artefact whose block holds answers is settled: the files
    may have been settled already, so a block holding none says nothing.

    For each artefact in them, its block's answers (`revalidated`, `revisited`) are
    compared with its live answers in the answer files a commit holds, as the writers
    write against them (`friction_write`):

    - **The same:** nothing is written, as a block written again with the same answers
      writes none.
    - **What changed:** written in the one answer file this helper wrote on the artefact
      that no commit holds yet, rewritten, else in a new one. Its entry names, in `read`,
      every other answer file present that answers the artefact. It holds a revalidation
      that differs, with every deferral re-stated, as `revalidate` writes one; else only
      the deferrals and revisit entries that differ, as `defer` and `revisit` write them.
    - **Every answer taken away:** the answer files this helper wrote on the artefact are
      removed, as a revert removes them (COR-062 point 8).
    - **One answer taken away** that no answer reading it can replace — a revalidation, a
      revisit entry, or a deferral beside no new revalidation (COR-062 point 5) — is
      refused (`UnsettledAnswers`): such a test writes its answer files itself.

    A file `git mv` renamed, or a document renamed in the same write, keeps its answers:
    an answer on its old location names it, as one followed through the rename does
    (COR-062 point 10). The block keeps everything else, its anchors among them.
    """
    rels = list(dict.fromkeys(written))
    if _HELD[0] or not any(rel.endswith(".md") for rel in rels):
        return  # held in the blocks for now, or no Markdown file, which alone holds artefacts
    present_rels = {rel for rel in rels if (root / rel).is_file()}
    holding = any(
        key in (root / rel).read_text(encoding="utf-8", errors="replace")
        for rel in present_rels
        if rel.endswith(".md")
        for key in ANSWER_KEYS
    )
    if not holding and (not taking or not answer_file_names(root)):
        return  # no block to take answers out of, and none to take back: nothing to read
    discovery = discover_artefacts(root)
    artefacts = [
        a
        for a in discovery.artefacts
        if a.path in present_rels
        and a.has_friction_block
        and not a.received
        and (taking or af.block_holds_answers(a))
    ]
    if not artefacts:
        return
    earlier = _renamed_documents(root, [rel for rel in rels if rel not in present_rels])
    staged = _staged_renames(root)
    wanted = {a.location: _block_entry(a) for a in artefacts}
    by_file: dict[str, list[Artefact]] = {}
    for artefact in artefacts:
        if af.block_holds_answers(artefact):
            by_file.setdefault(artefact.path, []).append(artefact)
    left = {rel for rel, holding in by_file.items() if not _take_out(root / rel, holding)}
    locate = af.working_locator(discovery, root)
    for artefact in artefacts:
        if artefact.path in left:
            continue  # its answers stay in the block, for a test of what refuses such a file
        moved_from = staged.get(artefact.path)
        if moved_from is not None:
            old: str | None = af.location_of(artefact, moved_from)
        elif artefact.kind is ArtefactKind.DOCUMENT:
            old = earlier.get(artefact.id)
        else:
            old = None
        targets = frozenset(
            anchor for link in discovery.links(artefact) for anchor in link_targets(artefact, link)
        )
        _settle_one(root, artefact, wanted[artefact.location], locate, old, targets)


def _block_entry(artefact: Artefact) -> dict[str, Any]:
    """The artefact's block answers as an answer file's entry holds them (COR-062 point 1),
    each list's entries with their keys in the schema's order; only its location where the
    block holds none."""
    friction: Any = artefact.friction
    block = cast(Mapping[str, Any], friction if isinstance(friction, Mapping) else {})
    entry: dict[str, Any] = {af.ARTEFACT_KEY: artefact.location}
    revalidated = block.get(REVALIDATED)
    if isinstance(revalidated, Mapping) and revalidated:
        entry[REVALIDATED] = ordered_revalidation(
            {
                key: _ordered(value, DEFERRAL_KEYS) if key == af.DEFERRED_KEY else value
                for key, value in cast(Mapping[str, Any], revalidated).items()
            }
        )
    revisited = block.get(REVISITED_KEY)
    if isinstance(revisited, list) and revisited:
        entry[REVISITED_KEY] = _ordered(revisited, REVISIT_KEYS)
    return entry


def _ordered(value: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(value, list):
        return value
    return [
        in_order(cast(Mapping[str, Any], item), keys) if isinstance(item, Mapping) else item
        for item in cast(list[Any], value)
    ]


def _take_out(path: Path, artefacts: list[Artefact]) -> bool:
    """Rewrite `path` with the answer keys of each artefact's block taken out: JSON front
    matter written again as `document` writes it, YAML front matter with only those keys'
    lines removed, or, where that cannot be done exactly, written again as JSON. A file
    that mixes line endings is left as it is, as the writers leave it: `False`."""
    written = path.read_bytes().decode("utf-8")
    newline = line_break(written)
    text = universal_newlines(written)
    front, _body = split_front_matter(text)
    if front is None or newline is None:
        return False
    offset = text.index("\n") + 1
    edited: str | None = None
    if not front.lstrip().startswith("{"):
        edited = front
        for artefact in artefacts:
            keys = (*carrier_keys(artefact), bs.CONTAINER_KEY, FRICTION_KEY)
            for key in ANSWER_KEYS:
                edited = None if edited is None else without_key(edited, keys, key)
    if edited is None:
        data = bs.as_written(_safe.load(front))
        for artefact in artefacts:
            holder: Any = data
            for step in (*carrier_keys(artefact), bs.CONTAINER_KEY, FRICTION_KEY):
                holder = holder.get(step) if isinstance(holder, dict) else None
            if isinstance(holder, dict):
                for key in ANSWER_KEYS:
                    holder.pop(key, None)
        edited = json.dumps(data, indent=2) + "\n"
    after = text[:offset] + edited + text[offset + len(front) :]
    path.write_bytes(after.replace("\n", newline).encode("utf-8"))
    return True


def _staged_renames(root: Path) -> dict[str, str]:
    """By its new path, the path each file `git mv` renamed from HEAD had there."""
    listed = GitRepo(root).git("diff", "--cached", "-M", "--name-status", "HEAD", check=False)
    found: dict[str, str] = {}
    for line in listed.stdout.splitlines():
        status, *paths = line.split("\t")
        if status.startswith("R") and len(paths) == 2:
            found[paths[1]] = paths[0]
    return found


def _renamed_documents(root: Path, deleted: list[str]) -> dict[str, str]:
    """By id, the path of each document HEAD holds that this write deleted: an artefact the
    write holds under that id is the document renamed."""
    found: dict[str, str] = {}
    for rel in deleted:
        if not rel.endswith(".md"):
            continue
        shown = GitRepo(root).git("show", f"HEAD:{rel}", check=False)
        if shown.returncode != 0:
            continue
        front, _body = split_front_matter(shown.stdout)
        try:
            data = _safe.load(front or "")
        except YAMLError:  # a file that does not parse names nothing
            continue
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            found[data["id"]] = rel
    return found


def _settle_one(
    root: Path,
    artefact: Artefact,
    entry: dict[str, Any],
    locate: Callable[[str], Artefact | None],
    old: str | None,
    targets: frozenset[Anchor],
) -> None:
    """Write one artefact's block answers in answer files (`settle_answers`): what they
    change against the live answers of the files a commit holds, in the change's own file.
    A deferral of an anchor the artefact no longer declares, and a revisit entry for a
    target no link takes (`targets`), answer nothing (COR-062 point 5)."""
    present = af.working_tree_files(root)

    def names_it(found: af.Entry) -> bool:
        if old is not None and found.location == old:
            return True
        named = locate(found.location)
        return named is not None and named.location == artefact.location

    entries = [e for f in present.values() for e in f.entries if names_it(e)]
    committed = af.head_names(root)
    own = sorted({e.file for e in entries if e.file.startswith(SETTLED_PREFIX)} - set(committed))
    if len(own) > 1:
        raise UnsettledAnswers(f"{artefact.location}: two uncommitted answer files answer it")
    for name in own:
        (root / af.path_of(name)).unlink()
    others = [e for e in entries if e.file not in own]
    declared = frozenset(
        Anchor(kind, value) for kind, values in artefact.anchors.items() for value in values
    )
    judged = af.liveness(
        others,
        set(present) - set(own),
        lambda _reader, _named: True,
        declared=declared,
        targets=targets,
    )
    text, _first, _last = answer_file_text([entry])
    parsed = af.read_answer_file("", text.encode("utf-8")).entries
    want = parsed[0] if parsed else None
    live = _live(judged)
    if _answers(want) == live:
        return
    files = sorted({e.file for e in others})
    if _answers(want) == _answers(None):
        _take_back(root, files)
        return
    assert want is not None
    restate = want.revalidation is not None and _answers(want)[0] != live[0]
    dropped = _dropped(want, judged, restate=restate)
    if dropped:
        raise UnsettledAnswers(
            f"{artefact.location}: this write takes away {dropped}, which no answer it adds "
            f"can replace (COR-062 point 5): write this test's answer files itself"
        )
    delta: dict[str, Any] = {af.ARTEFACT_KEY: artefact.location}
    if files:
        delta[af.READ_KEY] = files
    revalidated = dict(cast(Mapping[str, Any], entry.get(REVALIDATED) or {}))
    written = list(cast(list[Any], revalidated.get(af.DEFERRED_KEY) or []))
    if restate:
        delta[REVALIDATED] = revalidated
    else:
        changed = [written[d.index] for d in want.deferrals if (d.anchor, d.reason) not in live[1]]
        if changed:
            delta[REVALIDATED] = {af.DEFERRED_KEY: changed}
    revisits = list(cast(list[Any], entry.get(REVISITED_KEY) or []))
    changed_revisits = [
        revisits[r.index] for r in want.revisits if (r.anchor, r.outcome, r.reason) not in live[2]
    ]
    if changed_revisits:
        delta[REVISITED_KEY] = changed_revisits
    text, _first, _last = answer_file_text([delta])
    name = own[0] if own else f"{SETTLED_PREFIX}{hashlib.sha256(text.encode()).hexdigest()[:12]}"
    target = root / af.path_of(name if name.endswith(af.SUFFIX) else f"{name}{af.SUFFIX}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _take_back(root: Path, files: list[str]) -> None:
    """Every answer on the artefact taken away, as a revert takes them (COR-062 point 8): the
    answer files this helper wrote on it are removed. A file a test wrote itself is the
    test's to keep or remove."""
    for name in files:
        if name.startswith(SETTLED_PREFIX):
            (root / af.path_of(name)).unlink()


def _dropped(want: af.Entry, judged: af.Liveness, *, restate: bool) -> str | None:
    """What the answers take away that an answer reading it cannot replace (COR-062 point 5):
    a live revalidation, a live deferral beside no revalidation re-stated, or a live revisit
    entry. `None` where they take nothing so."""
    if want.revalidation is None and judged.revalidations:
        return "a revalidation"
    kept = {d.anchor for d in want.deferrals}
    if not restate and any(d.anchor not in kept for _e, d in judged.deferrals):
        return "a deferral beside no new revalidation"
    targets = {r.anchor for r in want.revisits}
    if any(r.anchor not in targets for _e, r in judged.revisits):
        return "a revisit entry"
    return None


def _answers(entry: af.Entry | None) -> tuple[frozenset[Any], frozenset[Any], frozenset[Any]]:
    """An entry's answers, compared as the checks read them."""
    if entry is None:
        return frozenset(), frozenset(), frozenset()
    rev = entry.revalidation
    return (
        frozenset() if rev is None else frozenset({(rev.at, rev.outcome, rev.because)}),
        frozenset((d.anchor, d.reason) for d in entry.deferrals),
        frozenset((r.anchor, r.outcome, r.reason) for r in entry.revisits),
    )


def _live(judged: af.Liveness) -> tuple[frozenset[Any], frozenset[Any], frozenset[Any]]:
    """The live answers in the answer files present, compared as `_answers` gives them."""
    return (
        frozenset(
            (e.revalidation.at, e.revalidation.outcome, e.revalidation.because)
            for e in judged.revalidations
            if e.revalidation is not None
        ),
        frozenset((d.anchor, d.reason) for _e, d in judged.deferrals),
        frozenset((r.anchor, r.outcome, r.reason) for _e, r in judged.revisits),
    )


def settled_write(adopter: AdopterRepo, files: Mapping[str, str | None]) -> None:
    """`AdopterRepo.write`, then the answers of what it wrote settled (`settle_answers`)."""
    GitRepo.write(adopter, files)
    settle_answers(adopter.root, files)


def settled_commit(
    adopter: AdopterRepo,
    message: str,
    files: Mapping[str, str | None] | None = None,
    *,
    author: Author | None = None,
    date: datetime | None = None,
) -> str:
    """`AdopterRepo.commit`, its writes settled (`settle_answers`) and the answer folder
    staged with them. With `files=None`, every change in the working tree is staged, the
    answers still in a block among them settled first."""
    if files is None:
        changed = adopter.git(
            "ls-files", "-z", "--modified", "--others", "--exclude-standard"
        ).stdout.split("\0")
        settle_answers(adopter.root, [rel for rel in changed if rel], taking=False)
        return GitRepo.commit(adopter, message, None, author=author, date=date)
    settled_write(adopter, files)
    adopter.git("add", "-A", "--", *files.keys())
    adopter.git("add", "-A", "--", af.FOLDER, check=False)
    # A block written again with the same answers in other words, once settled, may change
    # nothing: the commit is still made, as it was when the block held them.
    adopter.git("commit", "-q", "--allow-empty", "-m", message, author=author, date=date)
    return adopter.head()
