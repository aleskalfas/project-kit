#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — link-parent (verb-subject per DEC-020).

Links existing issues natively under the parent their body's first line names.
[project-management:DEC-005-linking-and-containment] keeps two records of an
issue's parent: the textual first-line parent-ref (the universal spine) and
GitHub's native sub-issue link (the canonical mechanism where the tracker
supports it). `create-issue` writes both, but an issue filed from a body file
while only `--parent` linked (#1033), filed by hand, or imported carries only
the text — it sits in pm's own tree yet under no parent in GitHub's sub-issue
panel. This verb makes the native record agree with the textual one. It reads
bodies; it never edits one.

Select issues by number, or every open issue with `--all-open`. Each selected
issue gets exactly one outcome:

  would link under #P      the first line names an issue parent (EPIC /
                           Feature / Umbrella) and the issue is not yet its
                           native sub-issue
  already linked under #P  the native link exists — it is never posted again
  milestone parent         a `Milestone:` first line: a milestone is not an
                           issue, so there is nothing to link under
  no parent line           the first line is not a parent-ref form the issue's
                           type allows, or the title's type is not recognised
  parent #P not found      the named parent is not an issue in this repository
  parent #P is closed      the parent is closed while the issue is open
  conflict                 the issue is natively a sub-issue of a different
                           parent than its first line names; an issue has one
                           native parent, so it is reported with both named
  unsupported              the instance has no native sub-issues (the seam's
                           verdict); nothing is linked, and that is no failure

A closed parent is linked only to a closed child. An open issue under a closed
parent is the state the close gate exists to prevent, and it usually means the
first line is stale, so it is reported instead of linked — reopen the parent or
re-parent the issue, and a re-run links it. A closed issue under a closed parent
(history) links normally.

A conflict is not linked either: taking the issue from the parent it has would
be a re-parent this verb was not asked for. `set-field <N> --parent <P>` makes
the two records agree on the parent you mean — it rewrites the first line and
moves the native link together.

The first line is read by `_lib.body_parent_ref`, the same reading
`create-issue` files and links by, against the forms the issue's own type
allows (`schemas/issue-types.yaml`). Issues are read through the containment
seam's corpus acquisition (`_lib.containment.fetch_issue_corpus`); the link is
made only by `_lib.containment.link_sub_issue`, which re-checks idempotency
itself, so a concurrent link is still reported as already linked. Each parent's
native sub-issues are read once per run (`_lib.containment.SubIssueReads`), for
the plan and the links alike, however many of its children are selected.

Containment mode ([project-management:DEC-039-containment-substrate-selection],
contract ADR-035): under `native` (the default) the plan's links are made. Under
`textual` nothing is linked — the first-line ref already is the record — and
each named parent's generated children comment is refreshed instead. That
refresh overwrites the parent's only parent-side view, so it is refused when
the issue list was not read in full, and withheld for any parent whose native
sub-issues could not be read.

`--dry-run` prints the plan and changes nothing. Otherwise the plan is printed
and consent is asked before any write; `--yes` skips the prompt, and a
non-interactive run without `--yes` refuses, naming the command to re-run.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/link-parent.py 101 102 --dry-run

Or via the dispatcher (per COR-021):
  pkit pm link-parent --all-open --dry-run

Exit codes:
  0  linked, already linked, nothing to link, a conflict reported, dry run, or
     declined at the prompt
  1  membership or foreign-repo refusal; or, in textual mode, a refusal to
     refresh children views from an issue list that was not read in full
  2  usage error — no selection or both selections, a number that is not an
     issue here, an un-bootstrapped project — or a non-interactive run
     without --yes
  3  gh failure — the issue list could not be read, a link or a
     children-view refresh failed, or a parent's children view was withheld
     because its native sub-issues could not be read (the other issues are
     still processed)
"""

from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels, body_parent_ref, bootstrap_gate, containment, session_guard
from _lib.containment import (
    LinkOutcome,
    LinkResult,
    NativeParent,
    NativeReadOutcome,
    SubIssueReads,
    link_sub_issue,
)
from _lib.gh import load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.structural_type import infer_structural_type

VERB = "link-parent"

# A first line quoted in a report is clipped so one prose line cannot swamp it.
_QUOTE_LIMIT = 60


class Outcome(Enum):
    """What one selected issue got. The value is its label in the summary.

    The plan assigns each issue WOULD_LINK, ALREADY_LINKED, CONFLICT,
    UNSUPPORTED, MILESTONE_PARENT, NO_PARENT_LINE or PARENT_UNAVAILABLE;
    applying it turns WOULD_LINK into LINKED, ALREADY_LINKED, CONFLICT,
    UNSUPPORTED or FAILED. TEXTUAL replaces WOULD_LINK in textual containment
    mode, where nothing is linked. The declaration order is the summary's order.
    """

    WOULD_LINK = "would link"
    LINKED = "linked"
    ALREADY_LINKED = "already linked"
    TEXTUAL = "textual only"
    MILESTONE_PARENT = "milestone parent"
    NO_PARENT_LINE = "no parent line"
    PARENT_UNAVAILABLE = "parent not found or closed"
    CONFLICT = "conflict (another native parent)"
    UNSUPPORTED = "not linked (unsupported)"
    FAILED = "failed"


@dataclass(frozen=True)
class Entry:
    """One selected issue's outcome and the line that reports it.

    ``parent`` is the issue parent the first line names, when it names one.
    ``native`` is how reading that parent's native sub-issues went during the
    plan (native mode only), which tells a refused link on an instance whose
    sub-issues demonstrably work from one on an instance without them.
    """

    issue: int
    outcome: Outcome
    detail: str
    parent: int | None = None
    native: NativeReadOutcome | None = None


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.all_open and args.issues:
        parser.error("give issue numbers or --all-open, not both")
    if not args.all_open and not args.issues:
        parser.error("give one or more issue numbers, or --all-open")

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("link-parent", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    membership = check_membership(members, resolve_invoker_identity(config=config))
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    # Kind-driven Task prefixes ([Bug] / [Docs] / ...) live in classification.yaml;
    # without it a kind-prefixed Task reads as an unrecognised type.
    classification = _read_yaml(capability_root / "schemas" / "classification.yaml", yaml_loader)
    mode = axis_labels.containment_mode(capability_root)
    textual = mode == axis_labels.CONTAINMENT_TEXTUAL

    # One read of every issue, open and closed: it supplies the selected
    # bodies, whether each named parent exists and is open, and — in textual
    # mode — the corpus the children views are rendered from.
    corpus = containment.fetch_issue_corpus(config, fields="number,title,body,state")
    if corpus is None:
        print(
            "error: the issue list could not be read (gh failed); nothing was examined.",
            file=sys.stderr,
        )
        return 3
    if not corpus.complete:
        print(
            "[warn] the issue list was not read in full: issues past what was "
            "read are not examined, and a parent missing from it is reported as "
            "not found.",
            file=sys.stderr,
        )
    rows = _rows_by_number(corpus)

    if args.all_open:
        selected = sorted(number for number, row in rows.items() if _is_open(row))
    else:
        selected = sorted(set(args.issues))
        unknown = [number for number in selected if number not in rows]
        if unknown:
            where = "" if corpus.complete else " as read (the list was not read in full)"
            print(
                "error: not an issue in this repository"
                f"{where}: {', '.join(f'#{n}' for n in unknown)} (a pull request, "
                "or no such number). Nothing was linked.",
                file=sys.stderr,
            )
            return 2

    entries = [
        classify(
            number,
            rows,
            issue_types,
            classification,
            corpus_complete=corpus.complete,
        )
        for number in selected
    ]
    # One read of each parent's native sub-issues for the whole run: the plan
    # reads through it, and the links made after consent reuse the same reads.
    reads = SubIssueReads(config)
    if textual:
        entries = [_as_textual(entry) for entry in entries]
    else:
        entries = check_native_links(entries, config, reads)

    _print_plan(entries, mode=mode, dry_run=args.dry_run)

    refresh_parents = _refresh_targets(entries) if textual else []
    if refresh_parents and not corpus.complete:
        # The children comment replaces the parent's only parent-side view of
        # its children wholesale and carries no hedge of its own, so a short
        # list published there reads as the complete one (ADR-035 point 5).
        print(
            "[refused] children views not refreshed: the issue list was not read "
            "in full, and a partial list would read as the complete one.",
            file=sys.stderr,
        )
        return 1
    pending = (
        len(refresh_parents)
        if textual
        else sum(1 for entry in entries if entry.outcome is Outcome.WOULD_LINK)
    )

    if args.dry_run:
        print("\n[dry-run] nothing written.")
        return 0
    if not pending:
        print("\nnothing to refresh." if textual else "\nnothing to link.")
        return 0

    # Foreign-repo mutation guard (COR-039 / ADR-034): the plan above only
    # read; this is the first write.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    prompt = (
        f"Refresh {pending} children view(s)? [y/N] "
        if textual
        else f"Link {pending} issue(s) under their first-line parent? [y/N] "
    )
    stop = _consent(yes=args.yes, prompt=prompt, rerun=_rerun_command(args))
    if stop is not None:
        return stop

    if textual:
        failed = _refresh_children_views(refresh_parents, config=config, corpus=corpus, mode=mode)
    else:
        entries = apply_links(entries, config, reads)
        failed = any(entry.outcome is Outcome.FAILED for entry in entries)
    print(f"done: {_summary(entries)}")
    return 3 if failed else 0


# ---- the plan ----------------------------------------------------------


def classify(
    number: int,
    rows: dict[int, dict],
    issue_types: dict,
    classification: dict,
    *,
    corpus_complete: bool,
) -> Entry:
    """The plan's outcome for one issue, from the issue list alone (no gh).

    Reads the first line against the forms the issue's type allows. An issue
    parent that exists becomes WOULD_LINK — unless it is closed while the issue
    is open (see the module docstring); whether the link already exists is
    asked of the native side separately (:func:`check_native_links`).
    """
    row = rows[number]
    title = str(row.get("title") or "")
    body = str(row.get("body") or "")

    structural_type = infer_structural_type(title, issue_types, classification=classification)
    types = issue_types.get("types") or {}
    type_entry = types.get(structural_type) if structural_type else None
    if not isinstance(type_entry, dict):
        return Entry(
            number,
            Outcome.NO_PARENT_LINE,
            "no parent line — the title's type prefix is not recognised, so its "
            "parent-ref form is unknown",
        )

    ref = body_parent_ref.parse_first_line(body, str(type_entry.get("parent_ref_form", "")))
    if ref is None:
        line = body_parent_ref.first_line(body)
        if not line:
            return Entry(number, Outcome.NO_PARENT_LINE, "no parent line — the body is empty")
        return Entry(
            number,
            Outcome.NO_PARENT_LINE,
            f"no parent line — {_quote(line)} is not a parent-ref form for type "
            f"{structural_type!r}",
        )
    if ref.milestone:
        return Entry(
            number,
            Outcome.MILESTONE_PARENT,
            f"milestone parent (milestone #{ref.number}) — no issue link",
        )

    parent = ref.number
    if parent == number:
        return Entry(
            number,
            Outcome.NO_PARENT_LINE,
            f"no parent line — the first line names #{number} itself",
        )
    parent_row = rows.get(parent)
    if parent_row is None:
        unread = "" if corpus_complete else " (the issue list was not read in full)"
        return Entry(
            number,
            Outcome.PARENT_UNAVAILABLE,
            f"parent #{parent} not found — not linked{unread}",
            parent=parent,
        )
    if not _is_open(parent_row) and _is_open(row):
        return Entry(
            number,
            Outcome.PARENT_UNAVAILABLE,
            f"parent #{parent} is closed while #{number} is open — not linked",
            parent=parent,
        )
    return Entry(number, Outcome.WOULD_LINK, f"would link under #{parent}", parent=parent)


def check_native_links(entries: list[Entry], config: dict, reads: SubIssueReads) -> list[Entry]:
    """Settle, read-only, which planned links already exist or cannot be made.

    Each distinct parent's native sub-issues are read once, through the run's
    ``reads`` (the links made later reuse them): a child already among them is
    ALREADY_LINKED and is never posted again (DEC-026 value-equality); an
    instance whose sub-issues read as unsupported links nothing. A child not
    among them has its own native parent read (:func:`_check_child_parent`),
    so one already under a different parent is reported as a CONFLICT here,
    in the plan, rather than discovered at the add. A read that fails leaves
    the link planned — the linker checks again before it posts.
    """
    checked: list[Entry] = []
    for entry in entries:
        if entry.outcome is not Outcome.WOULD_LINK or entry.parent is None:
            checked.append(entry)
            continue
        parent = entry.parent
        read = reads.read(parent)
        if read.outcome is NativeReadOutcome.UNSUPPORTED:
            checked.append(
                replace(
                    entry,
                    outcome=Outcome.UNSUPPORTED,
                    detail=(
                        f"not linked under #{parent} — native sub-issues are "
                        "unsupported on this instance; the first line stays the record"
                    ),
                    native=read.outcome,
                )
            )
        elif read.outcome is NativeReadOutcome.READ and entry.issue in read.numbers:
            checked.append(
                replace(
                    entry,
                    outcome=Outcome.ALREADY_LINKED,
                    detail=f"already linked under #{parent}",
                    native=read.outcome,
                )
            )
        else:
            checked.append(_check_child_parent(entry, read.outcome, config))
    return checked


def _check_child_parent(entry: Entry, native: NativeReadOutcome, config: dict) -> Entry:
    """A planned link, checked against the child's own native parent.

    Only reached for a child its parent's list does not show, so a run whose
    links already exist reads no child records. A child whose record could not
    be read keeps its planned link; the linker reads it again before posting.
    """
    parent = entry.parent
    state = containment.read_link_state(config, issue_number=entry.issue)
    holder = state.parent if state is not None else None
    if holder is not None and parent is not None and holder.is_issue(parent):
        return replace(
            entry,
            outcome=Outcome.ALREADY_LINKED,
            detail=f"already linked under #{parent}",
            native=native,
        )
    if holder is not None:
        return replace(
            entry,
            outcome=Outcome.CONFLICT,
            detail=_conflict_detail(holder, parent),
            native=native,
        )
    if native is NativeReadOutcome.UNREADABLE:
        return replace(
            entry,
            detail=(
                f"would link under #{parent} (#{parent}'s sub-issues could "
                "not be read; the link checks again before posting)"
            ),
            native=native,
        )
    return replace(entry, native=native)


def _conflict_detail(holder: NativeParent | None, parent: int | None) -> str:
    """The report line for a conflict: the parent the issue has natively, and the
    one its first line names."""
    held = holder.ref if holder is not None else "another parent"
    return (
        f"conflict — natively a sub-issue of {held}, but the first line names "
        f"#{parent}; not linked (an issue has one native parent)"
    )


def _as_textual(entry: Entry) -> Entry:
    """Textual containment mode links nothing: the first line is the record."""
    if entry.outcome is not Outcome.WOULD_LINK:
        return entry
    return replace(
        entry,
        outcome=Outcome.TEXTUAL,
        detail=(
            f"under #{entry.parent} — textual mode links nothing (the first line is the record)"
        ),
    )


def _refresh_targets(entries: list[Entry]) -> list[int]:
    """The parents whose children view a textual-mode run refreshes."""
    return sorted(
        {e.parent for e in entries if e.outcome is Outcome.TEXTUAL and e.parent is not None}
    )


# ---- applying the plan -------------------------------------------------


def apply_links(entries: list[Entry], config: dict, reads: SubIssueReads) -> list[Entry]:
    """Make every planned link through the sole constructor, reporting each.

    The linker is handed the run's ``reads``, so its idempotency check reuses
    the parent reads the plan made instead of reading each parent again per
    child.
    """
    applied: list[Entry] = []
    for entry in entries:
        if entry.outcome is not Outcome.WOULD_LINK or entry.parent is None:
            applied.append(entry)
            continue
        result = link_sub_issue(
            config,
            parent_number=entry.parent,
            child_number=entry.issue,
            sub_issues=reads,
        )
        done = _after_link(entry, result)
        marker = {
            Outcome.LINKED: "[ok]",
            Outcome.ALREADY_LINKED: "[ok]",
            Outcome.CONFLICT: "[warn]",
            Outcome.UNSUPPORTED: "[warn]",
        }.get(done.outcome, "[fail]")
        print(f"  {marker} #{done.issue} {done.detail}")
        applied.append(done)
    return applied


def _after_link(entry: Entry, result: LinkResult) -> Entry:
    """Map the linker's outcome onto the issue's final outcome.

    UNSUPPORTED is the seam's no-op for an instance without sub-issues, not a
    failure — unless this run already read the same parent's sub-issues
    successfully, in which case the instance plainly has them and the refusal
    is specific to this link: that one is reported as a failure, stating only
    what was established.

    CONFLICT — the issue went under another parent after the plan read it, or
    its record does not carry the parent and GitHub's refusal named the rule —
    is reported like the plan's conflicts, naming the parent where the seam
    could establish it.

    Where GitHub refused the link, its own words follow the line (#808): the
    seam's ``detail`` already carries them, and a line written here quotes them
    through :meth:`LinkResult.quoting_github`.
    """
    parent = entry.parent
    if result.outcome is LinkOutcome.LINKED:
        return replace(entry, outcome=Outcome.LINKED, detail=f"linked under #{parent}")
    if result.outcome is LinkOutcome.ALREADY:
        return replace(
            entry,
            outcome=Outcome.ALREADY_LINKED,
            detail=f"already linked under #{parent} (no change)",
        )
    if result.outcome is LinkOutcome.CONFLICT:
        return replace(
            entry,
            outcome=Outcome.CONFLICT,
            detail=result.quoting_github(_conflict_detail(result.current_parent, parent)),
        )
    if result.outcome is LinkOutcome.UNSUPPORTED:
        if entry.native is NativeReadOutcome.READ:
            return replace(
                entry,
                outcome=Outcome.FAILED,
                detail=result.quoting_github(
                    f"not linked under #{parent} — GitHub refused the link as "
                    f"unsupported, although #{parent}'s sub-issues read on this "
                    "instance"
                ),
            )
        return replace(
            entry,
            outcome=Outcome.UNSUPPORTED,
            detail=f"not linked under #{parent} — {result.detail}",
        )
    return replace(
        entry,
        outcome=Outcome.FAILED,
        detail=f"not linked under #{parent} — {result.detail}",
    )


def _refresh_children_views(
    parents: list[int],
    *,
    config: dict,
    corpus: containment.IssueCorpus,
    mode: str,
) -> bool:
    """Refresh each parent's generated children comment; True if any failed.

    Only reached with a complete corpus (the caller refuses otherwise). A
    complete corpus is not enough on its own: the seam must also vouch for each
    parent's child set, which it cannot when that parent's native sub-issues
    read failed. Such a parent's view is not written — the write replaces the
    whole view, so a short list would stand as the complete one (ADR-035 point
    5) — and the seam's own reason is reported. The writer is the one
    construction point for the view (``refresh_children_comment``: full
    overwrite of the one marked comment, a no-op when already current).
    """
    failed = False
    bodies, titles = corpus.bodies, corpus.titles
    for parent in parents:
        resolution = containment.resolve_children(
            config, parent_number=parent, corpus=bodies, corpus_complete=True
        )
        if not resolution.complete:
            failed = True
            print(
                f"  [refused] children view of #{parent} not refreshed: "
                f"{resolution.incomplete_reason}"
            )
            continue
        result = containment.refresh_children_comment(
            config,
            parent_number=parent,
            corpus=bodies,
            containment_mode=mode,
            titles=titles,
        )
        failed = failed or not result.ok
        print(f"  {'[ok]' if result.ok else '[fail]'} {result.detail}")
    return failed


def _consent(*, yes: bool, prompt: str, rerun: str) -> int | None:
    """Ask before writing. None to proceed; otherwise the exit code to stop with.

    A non-interactive run cannot be asked, so without ``--yes`` it refuses and
    names the command that carries the consent.
    """
    if yes:
        return None
    if not sys.stdin.isatty():
        print(
            "error: refusing to write without consent — this run is not "
            "interactive. Review the plan above (or add --dry-run), then re-run "
            f"with --yes:\n  {rerun}",
            file=sys.stderr,
        )
        return 2
    try:
        reply = input(prompt).strip().lower()
    except EOFError:
        reply = ""
    if reply in ("y", "yes"):
        return None
    print("aborted.", file=sys.stderr)
    return 0


def _rerun_command(args: argparse.Namespace) -> str:
    """The same invocation, carrying consent."""
    parts = ["pkit", "pm", VERB]
    parts += ["--all-open"] if args.all_open else [str(n) for n in sorted(set(args.issues))]
    if args.capability_root is not None:
        parts += ["--capability-root", str(args.capability_root)]
    if args.allow_foreign_repo:
        parts.append("--allow-foreign-repo")
    parts.append("--yes")
    return shlex.join(parts)


# ---- reporting ---------------------------------------------------------


def _print_plan(entries: list[Entry], *, mode: str, dry_run: bool) -> None:
    scope = (
        " (links nothing; refreshes the named parents' children views)"
        if mode == axis_labels.CONTAINMENT_TEXTUAL
        else ""
    )
    run = "  [dry-run]" if dry_run else ""
    print(f"{VERB}: {len(entries)} issue(s) — containment: {mode}{scope}{run}")
    for entry in entries:
        print(f"  #{entry.issue}  {entry.detail}")
    targets = _refresh_targets(entries)
    if targets:
        print(f"children views to refresh: {', '.join(f'#{p}' for p in targets)}")
    if any(entry.outcome is Outcome.CONFLICT for entry in entries):
        print(_CONFLICT_REMEDY)
    print(f"plan: {_summary(entries)}")


# A conflict is two records naming different parents; which one is right is the
# operator's call, so the verb names the one command that makes them agree
# either way rather than picking a side.
_CONFLICT_REMEDY = (
    "to resolve a conflict, set the parent you mean: "
    "`pkit pm set-field <N> --parent <P>` rewrites the first line and moves the "
    "native link together"
)


def _summary(entries: list[Entry]) -> str:
    """Counts per outcome, in a fixed order, omitting the empty ones."""
    counts = {outcome: 0 for outcome in Outcome}
    for entry in entries:
        counts[entry.outcome] += 1
    parts = [f"{n} {outcome.value}" for outcome, n in counts.items() if n]
    return ", ".join(parts) if parts else "no issues selected"


def _quote(line: str) -> str:
    clipped = line if len(line) <= _QUOTE_LIMIT else line[: _QUOTE_LIMIT - 1] + "…"
    return repr(clipped)


# ---- helpers -----------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Link existing issues natively under the parent their body's first "
            "line names (an EPIC / Feature / Umbrella ref), so GitHub's sub-issue "
            "panel agrees with the textual parent record. Idempotent: an existing "
            "link is reported, never re-posted. Honours the containment mode "
            "(textual: links nothing, refreshes the children views)."
        ),
    )
    parser.add_argument(
        "issues",
        nargs="*",
        type=_issue_number,
        metavar="ISSUE",
        help="Issue number(s) to link. Mutually exclusive with --all-open.",
    )
    parser.add_argument(
        "--all-open",
        action="store_true",
        help="Examine every open issue in the repository.",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what each issue would get; change nothing.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=("Write without the confirmation prompt. Required in a non-interactive run."),
    )
    session_guard.add_override_argument(parser)
    return parser


def _issue_number(text: str) -> int:
    try:
        number = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an issue number: {text!r}") from None
    if number <= 0:
        raise argparse.ArgumentTypeError(f"not an issue number: {text!r}")
    return number


def _rows_by_number(corpus: containment.IssueCorpus) -> dict[int, dict]:
    return {row["number"]: row for row in corpus.rows if isinstance(row.get("number"), int)}


def _is_open(row: dict) -> bool:
    return str(row.get("state") or "").upper() == "OPEN"


def _read_yaml(path: Path, yaml_loader: YAML) -> dict:
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    data = _read_yaml(capability_root / "project" / "members.yaml", yaml_loader)
    members = data.get("members") or []
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
