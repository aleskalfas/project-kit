"""What the workstream mutators read and write outside workstreams.yaml (DEC-018).

The file is the source of truth, and the substrate that carries the workstream
axis reflects it ([project-management:DEC-018-workstream-taxonomy-and-lifecycle]).
The mutators (`add` / `rename` / `merge` / `split` / `remove-workstream`) share
the reads and writes that keep that substrate, and the references to a slug, in
step with the file:

* **Carriers.** Which issues carry a workstream, read from whatever substrate
  carries the axis (`axis_carriage.carriage`): the kit's label, the adopter's own
  label or title prefix, or the board's `Workstream` field. `remove-workstream`
  refuses while any issue carries the slug, whatever the carriage.
* **Labels.** The repository's label names, and the move of one issue from one
  label to another.
* **The board.** The board's `Workstream` single-select field with its options in
  full, and the option lists that add, rename or drop an option. The reads go
  through the board read seam (`_lib/board_fields`) and the writes through the
  write seam (`_lib/substrate_writes`); nothing here builds a board call itself.
* **References.** The tracked files, and the issue, pull-request and comment
  bodies, that hold a typed reference to a slug, and the write of a body.

Every function that runs `gh` takes the runner as `gh_call`, so a script passes
its own (and a test its fake). The board reads take `board_call`, which defaults
to the board seam's own runner: a `gh project` read needs the owner that runner
splices, which a plain `gh` runner does not.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import axis_labels, board_fields, substrate_writes
from _lib.workstreams import rewrite_references

GhCall = Callable[..., "subprocess.CompletedProcess[str]"]

AXIS = "workstream"

# The board field that carries the axis: the Title-cased axis name, the name
# `set-field` writes a workstream value to.
FIELD_NAME = "Workstream"

# `gh issue list` / `gh label list` page through this many entries at most.
_LIST_LIMIT = "5000"


# ----- carriers ---------------------------------------------------------


@dataclass(frozen=True)
class Carrier:
    """One issue that carries a workstream; `item_id` is its card where a board carries it."""

    number: int | None
    title: str = ""
    item_id: str | None = None


@dataclass(frozen=True)
class CarriersRead:
    """Outcome of finding the issues that carry a workstream.

    `ok=False` means the read failed and nothing is known, which a caller that
    needs a count must not take for zero.
    """

    ok: bool
    carriers: tuple[Carrier, ...] = ()
    error: str | None = None


def _run(gh_call: GhCall, args: list[str], config: dict[str, Any], **kwargs: Any):
    """Run one `gh` command; return `(proc, None)`, or `(None, error)` on failure."""
    try:
        proc = gh_call(args, config, check=False, **kwargs)
    except FileNotFoundError:
        return None, "`gh` not on PATH. Install GitHub CLI."
    if proc.returncode != 0:
        return None, (proc.stderr or "").strip() or f"`{' '.join(args[:3])}` failed"
    return proc, None


def _issues(stdout: str) -> list[dict[str, Any]] | None:
    try:
        data = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return None
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else None


def issues_with_label(label: str, config: dict[str, Any], *, gh_call: GhCall) -> CarriersRead:
    """Every issue, open or closed, that carries the label `label`."""
    args = [
        "gh",
        "issue",
        "list",
        "--label",
        label,
        "--state",
        "all",
        "--limit",
        _LIST_LIMIT,
        "--json",
        "number,title",
    ]
    proc, error = _run(gh_call, args, config)
    if proc is None:
        return CarriersRead(ok=False, error=error)
    issues = _issues(proc.stdout)
    if issues is None:
        return CarriersRead(ok=False, error="`gh issue list` returned non-JSON output.")
    return CarriersRead(
        ok=True,
        carriers=tuple(
            Carrier(number=i.get("number"), title=str(i.get("title") or "")) for i in issues
        ),
    )


def issues_with_title_prefix(
    prefix: str, config: dict[str, Any], *, gh_call: GhCall
) -> CarriersRead:
    """Every issue, open or closed, whose title opens with `prefix` and a space."""
    args = [
        "gh",
        "issue",
        "list",
        "--state",
        "all",
        "--limit",
        _LIST_LIMIT,
        "--search",
        f'"{prefix}" in:title',
        "--json",
        "number,title",
    ]
    proc, error = _run(gh_call, args, config)
    if proc is None:
        return CarriersRead(ok=False, error=error)
    issues = _issues(proc.stdout)
    if issues is None:
        return CarriersRead(ok=False, error="`gh issue list` returned non-JSON output.")
    return CarriersRead(
        ok=True,
        carriers=tuple(
            Carrier(number=i.get("number"), title=str(i.get("title") or ""))
            for i in issues
            if str(i.get("title") or "").startswith(f"{prefix} ")
        ),
    )


def carriers(
    slug: str,
    *,
    carriage: str,
    config: dict[str, Any],
    substrate_map: axis_labels.SubstrateMap | None,
    gh_call: GhCall,
    board_call: GhCall | None = None,
) -> CarriersRead:
    """Every issue that carries `slug`, read from the substrate `carriage` names.

    A value no substrate can hold has no carrier: an adopter label or title
    prefix the map does not bind for `slug`, a derived axis, a degraded one,
    and a board with no usable `Workstream` field. A board that cannot be read
    is a failed read.
    """
    if carriage == "kit-label":
        return issues_with_label(axis_labels.label(AXIS, slug), config, gh_call=gh_call)
    if carriage in ("adopter-label", "title"):
        target = axis_labels.resolve_write(AXIS, slug, substrate_map)
        if target is axis_labels.DEGRADE or not isinstance(target, str):
            return CarriersRead(ok=True)
        if carriage == "adopter-label":
            return issues_with_label(target, config, gh_call=gh_call)
        return issues_with_title_prefix(target, config, gh_call=gh_call)
    if carriage == "board":
        read = read_board_field(config, board_call=board_call)
        if read.error is not None:
            return CarriersRead(ok=False, error=read.error)
        if read.field is None:
            return CarriersRead(ok=True)
        return board_carriers(read.field, slug, config, board_call=board_call)
    return CarriersRead(ok=True)


# ----- labels -----------------------------------------------------------


def label_names(config: dict[str, Any], *, gh_call: GhCall) -> tuple[set[str] | None, str | None]:
    """The repository's label names, lower-cased, or `(None, error)` when unreadable.

    Lower-cased because GitHub holds label names unique regardless of case.
    """
    args = ["gh", "label", "list", "--limit", _LIST_LIMIT, "--json", "name"]
    proc, error = _run(gh_call, args, config)
    if proc is None:
        return None, error
    labels = _issues(proc.stdout)
    if labels is None:
        return None, "`gh label list` returned non-JSON output."
    return {str(entry.get("name") or "").lower() for entry in labels}, None


def retag_issue(
    number: int, old_label: str, new_label: str, config: dict[str, Any], *, gh_call: GhCall
) -> str | None:
    """Move issue `number` from `old_label` to `new_label`; the error, or None."""
    args = [
        "gh",
        "issue",
        "edit",
        str(number),
        "--add-label",
        new_label,
        "--remove-label",
        old_label,
    ]
    _proc, error = _run(gh_call, args, config)
    return error


# ----- the board --------------------------------------------------------


@dataclass(frozen=True)
class BoardField:
    """The board's `Workstream` single-select field, with its options in full."""

    project_id: str
    field_id: str
    options: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class BoardFieldRead:
    """Outcome of reading the board's `Workstream` field.

    `error` says the board could not be read. `problem` says it was read and
    offers no single-select `Workstream` field to write. Neither is set when
    `field` is.
    """

    field: BoardField | None = None
    error: str | None = None
    problem: str | None = None


def read_board_field(config: dict[str, Any], *, board_call: GhCall | None = None) -> BoardFieldRead:
    """The board's `Workstream` field and its options, through the board read seam."""
    owner = board_fields.default_owner(config)
    project = board_fields.read_project_node_id(config, owner=owner, gh_call=board_call)
    if not project.ok or not project.node_id:
        return BoardFieldRead(error=project.error or "the board did not resolve to a project id.")
    fields = board_fields.read_fields(config, owner=owner, gh_call=board_call)
    if not fields.ok:
        return BoardFieldRead(error=fields.error)
    field = board_fields.find_field(fields.fields, FIELD_NAME)
    if field is None:
        offered = ", ".join(board_fields.field_names(fields.fields)) or "(no fields)"
        return BoardFieldRead(
            problem=(
                f"the board has no field named `{FIELD_NAME}`; it offers: {offered}. Add a "
                f"`{FIELD_NAME}` single-select on the board, or bind `workstream` to a label "
                "in project/substrate-map.yaml."
            )
        )
    if not board_fields.is_single_select(field):
        return BoardFieldRead(
            problem=(
                f"the board's `{FIELD_NAME}` field is a {board_fields.field_type(field)}, "
                "not a single-select, so it holds no workstream options."
            )
        )
    field_id = field.get("id")
    if not isinstance(field_id, str) or not field_id:
        return BoardFieldRead(error=f"the board's `{FIELD_NAME}` field has no id.")
    options = board_fields.read_field_options(config, field_id=field_id, gh_call=board_call)
    if not options.ok:
        return BoardFieldRead(error=options.error)
    return BoardFieldRead(
        field=BoardField(project_id=project.node_id, field_id=field_id, options=options.options)
    )


def find_option(field: BoardField, slug: str) -> dict[str, str] | None:
    """The option named `slug`, matched exactly first and then regardless of case."""
    for option in field.options:
        if option.get("name") == slug:
            return option
    for option in field.options:
        if str(option.get("name") or "").lower() == slug.lower():
            return option
    return None


def options_adding(field: BoardField, slug: str, description: str = "") -> list[dict[str, str]]:
    """The field's options with an option `slug` added at the end."""
    return [*field.options, {"name": slug, "description": description}]


def options_renaming(field: BoardField, old: str, new: str) -> list[dict[str, str]]:
    """The field's options with the option `old` named `new`, keeping its id."""
    target = find_option(field, old)
    return [
        {**option, "name": new} if target is not None and option is target else dict(option)
        for option in field.options
    ]


def options_without(field: BoardField, slugs: list[str]) -> list[dict[str, str]]:
    """The field's options without the options named in `slugs`."""
    dropped = [find_option(field, slug) for slug in slugs]
    return [dict(option) for option in field.options if not any(option is d for d in dropped)]


def write_options(
    config: dict[str, Any], field: BoardField, options: list[dict[str, str]]
) -> substrate_writes.SubstrateWriteResult:
    """Set the field's option list, through the write seam."""
    return substrate_writes.write_field_options(config, field_id=field.field_id, options=options)


def board_carriers(
    field: BoardField, slug: str, config: dict[str, Any], *, board_call: GhCall | None = None
) -> CarriersRead:
    """Every card whose `Workstream` value is the option `slug`."""
    option = find_option(field, slug)
    if option is None:
        return CarriersRead(ok=True)
    read = board_fields.read_items_with_option(
        config,
        project_node_id=field.project_id,
        field_name=FIELD_NAME,
        option_id=option["id"],
        gh_call=board_call,
    )
    if not read.ok:
        return CarriersRead(ok=False, error=read.error)
    return CarriersRead(
        ok=True,
        carriers=tuple(
            Carrier(number=item.number, title=item.title, item_id=item.item_id)
            for item in read.items
        ),
    )


def set_card_option(
    config: dict[str, Any], field: BoardField, item_id: str, option_id: str
) -> substrate_writes.SubstrateWriteResult:
    """Set one card's `Workstream` value to `option_id`, through the write seam."""
    return substrate_writes.write_field_value(
        config,
        item_id=item_id,
        field_id=field.field_id,
        project_id=field.project_id,
        single_select_option_id=option_id,
    )


# ----- references -------------------------------------------------------


def repo_root(capability_root: Path) -> Path | None:
    """The root of the repository the capability is installed in, or None."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(capability_root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return Path(proc.stdout.strip())


def _not_rewritten(relative: str) -> bool:
    """Whether a tracked file is left out of a reference rewrite.

    The methodology's `.pkit/` tree holds files the core owns, which a project
    never edits (the no-shared-files invariant), and its own accepted records.
    A changelog and the pending changesets record what happened, under the
    names it happened under.
    """
    parts = Path(relative).parts
    return bool(parts) and (
        parts[0] in (".pkit", ".changes") or parts[-1].upper() == "CHANGELOG.MD"
    )


def _inside(path: Path, root: Path) -> bool:
    """Whether `path`, every link in it followed, stays under `root`."""
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def files_referencing(root: Path, old_label: str) -> tuple[list[Path], str | None]:
    """The tracked text files under `root` that hold a typed reference to `old_label`.

    Only files git tracks are read, so a virtual environment or a build output
    is never rewritten, and the `.pkit/` tree and the changelog are left out
    (`_not_rewritten`). A file that is binary, not UTF-8, a link, or reached
    through a link out of `root` is skipped.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return [], "`git` not on PATH."
    if proc.returncode != 0:
        return [], (proc.stderr or b"").decode("utf-8", "replace").strip() or "git ls-files failed"
    found: list[Path] = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", "surrogateescape")
        if _not_rewritten(relative):
            continue
        path = root / relative
        if path.is_symlink() or not path.is_file() or not _inside(path, root):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data or old_label.encode("utf-8") not in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        # Rewriting the label to itself counts the references and changes nothing.
        _same, count = rewrite_references(text, old_label, old_label)
        if count:
            found.append(path)
    return found, None


@dataclass(frozen=True)
class Body:
    """One issue, pull-request or comment body that may hold a reference.

    `number` is the issue or pull request the body is on, and `comment_id` is
    set only for a comment.
    """

    number: int
    kind: str  # "issue" | "pull request" | "comment"
    author: str
    text: str
    comment_id: int | None = None


def bodies_referencing(
    old_label: str, config: dict[str, Any], *, gh_call: GhCall, cwd: Path | None = None
) -> tuple[list[Body], str | None]:
    """The issue, pull-request and comment bodies that hold a typed reference to `old_label`.

    GitHub's search finds the issues and pull requests whose title, body or
    comments hold the phrase, and each body found is then matched against the
    typed form here. Search splits `workstream:cli` into words, so it also finds
    `workstream:cli-tools`, which the local match then drops.
    """
    found: list[Body] = []
    hits: list[tuple[int, str]] = []
    for verb, kind in (("issue", "issue"), ("pr", "pull request")):
        args = [
            "gh",
            verb,
            "list",
            "--state",
            "all",
            "--limit",
            _LIST_LIMIT,
            "--search",
            f'"{old_label}"',
            "--json",
            "number,body,author",
        ]
        proc, error = _run(gh_call, args, config, cwd=cwd)
        if proc is None:
            return [], error
        entries = _issues(proc.stdout)
        if entries is None:
            return [], f"`gh {verb} list` returned non-JSON output."
        for entry in entries:
            number = entry.get("number")
            if not isinstance(number, int):
                continue
            hits.append((number, kind))
            text = str(entry.get("body") or "")
            if rewrite_references(text, old_label, old_label)[1]:
                author = entry.get("author") if isinstance(entry.get("author"), dict) else {}
                found.append(
                    Body(number=number, kind=kind, author=str(author.get("login") or ""), text=text)
                )
    for number, _kind in hits:
        args = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
            "--paginate",
            "--jq",
            ".[] | {id: .id, body: .body, login: .user.login}",
        ]
        proc, error = _run(gh_call, args, config, cwd=cwd)
        if proc is None:
            return [], error
        for line in (proc.stdout or "").splitlines():
            try:
                comment = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(comment, dict) or not isinstance(comment.get("id"), int):
                continue
            text = str(comment.get("body") or "")
            if rewrite_references(text, old_label, old_label)[1]:
                found.append(
                    Body(
                        number=number,
                        kind="comment",
                        author=str(comment.get("login") or ""),
                        text=text,
                        comment_id=comment["id"],
                    )
                )
    return found, None


def viewer(
    config: dict[str, Any], *, gh_call: GhCall, cwd: Path | None = None
) -> tuple[str | None, bool]:
    """The signed-in login, and whether it holds admin rights on the repository.

    Either half reads as unknown (None, False) when `gh` cannot say, so a caller
    edits no one else's comment it cannot vouch for.
    """
    proc, _error = _run(gh_call, ["gh", "api", "user", "--jq", ".login"], config, cwd=cwd)
    login = proc.stdout.strip() if proc is not None and proc.stdout.strip() else None
    proc, _error = _run(
        gh_call,
        ["gh", "api", "repos/{owner}/{repo}", "--jq", ".permissions.admin"],
        config,
        cwd=cwd,
    )
    admin = proc is not None and proc.stdout.strip() == "true"
    return login, admin


def write_body(
    body: Body, text: str, config: dict[str, Any], *, gh_call: GhCall, cwd: Path | None = None
) -> str | None:
    """Replace `body` on GitHub with `text`; the error, or None.

    The text goes on standard input, never in the command line.
    """
    if body.comment_id is not None:
        endpoint = f"repos/{{owner}}/{{repo}}/issues/comments/{body.comment_id}"
    else:
        endpoint = f"repos/{{owner}}/{{repo}}/issues/{body.number}"
    args = ["gh", "api", "-X", "PATCH", endpoint, "--input", "-"]
    _proc, error = _run(gh_call, args, config, cwd=cwd, input=json.dumps({"body": text}))
    return error


def references_need_yes(yes: bool, dry_run: bool) -> bool:
    """Whether a run that would rewrite references must refuse before it starts.

    DEC-018 confirms each file and body by default, and `--yes` batches them. A
    run with no shell to ask and no `--yes` could confirm none of them, so it
    is refused before anything changes, rather than left half done.
    """
    return not yes and not dry_run and not sys.stdin.isatty()


def confirm_each(yes: bool) -> Callable[[str], bool]:
    """A per-object confirmation, the default DEC-018 sets for rewriting references.

    It asks in an interactive shell, and `--yes` opts into batch confirmation.
    A shell that cannot answer declines: an edit of a body cannot be rolled
    back, so the mutators refuse such a run up front (`references_need_yes`).
    """

    def confirm(question: str) -> bool:
        if yes:
            return True
        if not sys.stdin.isatty():
            return False
        return input(question).strip().lower() in ("y", "yes")

    return confirm


@dataclass
class RewriteOutcome:
    """What a reference rewrite changed, left alone, and failed to change."""

    rewritten: list[str]
    skipped: list[str]
    failed: list[str]


def rewrite_everywhere(
    old_label: str,
    *,
    target: Callable[[int | None, str], str | None],
    confirm: Callable[[str], bool],
    root: Path | None,
    config: dict[str, Any],
    gh_call: GhCall,
    stamp: Callable[[str], str] | None = None,
    cwd: Path | None = None,
) -> RewriteOutcome:
    """Rewrite each typed reference to `old_label`, in the tracked files and on GitHub.

    `target(number, where)` names the label a reference becomes, or None to
    leave it: `number` is the issue or pull request a body is on, and None for
    a file. `confirm(question)` asks before each file and each body is written.
    `stamp` re-stamps an issue or pull-request body before it is written. A
    comment by someone else is left, with a warning, unless the signed-in login
    holds admin rights on the repository (DEC-018).
    """
    outcome = RewriteOutcome(rewritten=[], skipped=[], failed=[])
    if root is None:
        outcome.failed.append("files: the repository root could not be found")
    else:
        paths, error = files_referencing(root, old_label)
        if error is not None:
            outcome.failed.append(f"files: {error}")
        for path in paths:
            where = str(path.relative_to(root))
            new_label = target(None, where)
            if new_label is None:
                outcome.skipped.append(f"{where}: no workstream chosen")
                continue
            if not _inside(path, root):
                outcome.skipped.append(f"{where}: reached through a link out of the repository")
                continue
            text = path.read_text(encoding="utf-8")
            new_text, count = rewrite_references(text, old_label, new_label)
            if not confirm(f"Rewrite {count} reference(s) in {where} to `{new_label}`? [y/N] "):
                outcome.skipped.append(f"{where}: declined")
                continue
            try:
                path.write_text(new_text, encoding="utf-8")
            except OSError as exc:
                outcome.failed.append(f"{where}: {exc}")
                continue
            outcome.rewritten.append(f"{where}: {count} reference(s)")

    bodies, error = bodies_referencing(old_label, config, gh_call=gh_call, cwd=cwd)
    if error is not None:
        outcome.failed.append(f"GitHub bodies: {error}")
        return outcome
    login, admin = viewer(config, gh_call=gh_call, cwd=cwd) if bodies else (None, False)
    for body in bodies:
        where = f"#{body.number} {body.kind}" + (
            f" {body.comment_id}" if body.comment_id is not None else ""
        )
        if body.kind == "comment" and not admin and (login is None or body.author != login):
            outcome.skipped.append(
                f"{where}: a comment by {body.author or 'someone else'}, and you hold no "
                "admin rights on the repository"
            )
            continue
        new_label = target(body.number, where)
        if new_label is None:
            outcome.skipped.append(f"{where}: no workstream chosen")
            continue
        new_text, count = rewrite_references(body.text, old_label, new_label)
        if body.kind != "comment" and stamp is not None:
            new_text = stamp(new_text)
        if not confirm(f"Rewrite {count} reference(s) in {where} to `{new_label}`? [y/N] "):
            outcome.skipped.append(f"{where}: declined")
            continue
        error = write_body(body, new_text, config, gh_call=gh_call, cwd=cwd)
        if error is not None:
            outcome.failed.append(f"{where}: {error}")
            continue
        outcome.rewritten.append(f"{where}: {count} reference(s)")
    return outcome
