"""Shared implementation for the `comment-issue` / `comment-pr` verbs (DEC-047).

A validated freeform-comment verb: the `project-manager` agent (denied direct
`gh` writes) posts evidence / analysis / triage notes on an issue or PR through
the same guarded path as every other mutating verb — the membership gate
(DEC-021) and the foreign-repo session interlock (COR-039), a context header,
and `--dry-run` / `--yes`. Per DEC-047 a comment mutates no lifecycle state, so
it carries no validation-severity finding; the only failure is an empty body.

Both `scripts/comment-issue.py` and `scripts/comment-pr.py` are thin wrappers
that call :func:`run_comment_verb` with their subject.

**Who posted.** Every clone posts under the same account, so GitHub's author
line cannot tell a planner's comment from a worker's or the person's own. The
verb ends each comment with a line that names the seat and instance of the
clone that runs it, or says the clone holds no seat, and a stamp that carries
the same for tooling (:class:`Poster`). A clone's identity is its seat's
(DEC-059 point 6), and which agent wrote a comment is an off-surface fact a
comment may carry (DEC-052's boundary rule). In a project with a topology, the
seat is confirmed on its state issue before the comment is posted, as for every
write that acts as an instance (DEC-059 point 6).

It is also the one home of the issue/PR comment `gh` wiring the audit writers
share: :func:`post_comment`, :func:`fetch_comments`, and :func:`post_audit_once`
— the fetch / scan / post-if-absent shape every audit comment (`done-work`,
`merge-pr`, `move-issue`, `handoff-issue`) goes through so it is posted at most
once per act (#902). The recognition rule itself is `_lib.audit.own_audit_posted`
(pure, no `gh`); this module only wires it to `gh`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

# Dual-form sibling imports so the module loads both as part of the `_lib`
# package (scripts/ on sys.path, the wrapper's path) and standalone-by-path
# (scripts/_lib/ on sys.path) — mirrors `_lib/pr_validation.py`'s idiom.
try:
    import session_guard  # type: ignore[import-not-found]
    from agent_verdicts import parse_verdict_line  # type: ignore[import-not-found]
    from audit import own_audit_posted  # type: ignore[import-not-found]
    from audit_log import code, encode  # type: ignore[import-not-found]
    from body_rules import lines_outside_fences  # type: ignore[import-not-found]
    from gh import gh_run, load_adopter_config  # type: ignore[import-not-found]
    from membership import (  # type: ignore[import-not-found]
        CAPABILITY_NAME,
        check_membership,
        resolve_capability_root,
        resolve_invoker_identity,
    )
except ImportError:  # pragma: no cover
    from _lib import session_guard  # type: ignore[no-redef]
    from _lib.agent_verdicts import parse_verdict_line  # type: ignore[no-redef]
    from _lib.audit import own_audit_posted  # type: ignore[no-redef]
    from _lib.audit_log import code, encode  # type: ignore[no-redef]
    from _lib.body_rules import lines_outside_fences  # type: ignore[no-redef]
    from _lib.gh import gh_run, load_adopter_config  # type: ignore[no-redef]
    from _lib.membership import (  # type: ignore[no-redef]
        CAPABILITY_NAME,
        check_membership,
        resolve_capability_root,
        resolve_invoker_identity,
    )

#: Human labels per subject for messages.
_SUBJECT_LABEL = {"issue": "issue", "pr": "PR"}

#: Marker appended to every freeform comment so it is positively distinguishable
#: from the methodology's *structured* comments (which carry their own markers —
#: `pkit-provenance` per DEC-041, `pkit-hook` per DEC-024). The write-side
#: counterpart to :func:`structured_comment_reason`'s read-side refusal (DEC-047).
FREEFORM_MARKER = "<!-- pkit-freeform -->"


def stamp_freeform(body: str) -> str:
    """Append the freeform marker (idempotent — never double-stamps)."""
    if FREEFORM_MARKER in body:
        return body
    return f"{body.rstrip()}\n\n{FREEFORM_MARKER}\n"


#: The stamp that names the clone that posted a freeform comment, and its
#: version, which changes only with the grammar.
POSTER_PREFIX = "pkit:posted-by"
POSTER_VERSION = 1

#: The stamp's fields, in the order it writes them: the names a claim's stamp
#: gives the same facts (DEC-059 point 9).
_POSTER_FIELDS = ("instance", "seat", "seat_number", "clone")

_POSTER_STAMP = re.compile(
    r"<!--\s*pkit:posted-by\s+v=(?P<v>[0-9]{1,6})"
    r"(?P<fields>(?:\s+[a-z][a-z0-9_]*=[^\s>]*)*)\s*-->"
)
_POSTER_PAIR = re.compile(r"([a-z][a-z0-9_]*)=([^\s>]*)")


@dataclass(frozen=True)
class Poster:
    """The clone that posts a freeform comment, as the comment names it.

    ``instance`` is the clone's instance number, where it has one. ``seat``,
    ``seat_number`` and ``clone``, the clone's key, are set where it holds a
    seat. A poster with no seat is a clone that holds none.
    """

    instance: int | None = None
    seat: str | None = None
    seat_number: int | None = None
    clone: str | None = None

    def named(self, *, shown: Callable[[str], str] = str) -> str:
        """How a line names the poster. ``shown`` writes the seat's name."""
        if self.seat is not None:
            return f"seat {shown(self.seat)}, instance {self.instance}"
        if self.instance is not None:
            return f"instance {self.instance}, which holds no seat"
        return "a clone that holds no seat"

    def line(self) -> str:
        """The line a person reads, in the comment's frame."""
        return f"<sub>🪑 Posted by {self.named(shown=code)}</sub>"

    def stamp(self) -> str:
        """The hidden stamp tooling reads: each field the poster has, encoded
        as the audit-log facility encodes a value."""
        values = {name: getattr(self, name) for name in _POSTER_FIELDS}
        fields = "".join(
            f" {name}={encode(str(value))}" for name, value in values.items() if value is not None
        )
        return f"<!-- {POSTER_PREFIX} v={POSTER_VERSION}{fields} -->"


def poster_of(clone: Any) -> Poster:
    """The poster that ``clone`` is, as ``instance_claims.this_clone`` answers
    it: None for a clone that takes no part in instance ownership."""
    if clone is None:
        return Poster()
    seat = clone.seat
    if seat is None:
        return Poster(instance=clone.instance)
    return Poster(clone.instance, seat.name, seat.number, clone.key)


def sign(body: str, poster: Poster) -> str:
    """``body`` with the line and the stamp that name ``poster`` after it. The
    words stay as they are, and come first (DEC-052)."""
    return f"{body.rstrip()}\n\n{poster.line()}\n\n{poster.stamp()}\n"


def read_poster(body: str) -> Poster | None:
    """The poster a comment's stamp names, or None where it carries none.

    The verb appends its stamp last, so the last stamp outside a fenced code
    block counts, and one the words quote above it never does. A stamp of a
    later version than this reader knows reads as None.
    """
    found: Poster | None = None
    for line in lines_outside_fences(body or ""):
        match = _POSTER_STAMP.fullmatch(line.strip())
        if match is None:
            continue
        if int(match.group("v")) > POSTER_VERSION:
            found = None
            continue
        values: dict[str, str] = {}
        for name, value in _POSTER_PAIR.findall(match.group("fields")):
            values.setdefault(name, unquote(value))
        found = Poster(
            _number(values.get("instance")),
            values.get("seat"),
            _number(values.get("seat_number")),
            values.get("clone"),
        )
    return found


def _number(value: str | None) -> int | None:
    return int(value) if value is not None and re.fullmatch(r"[0-9]{1,9}", value) else None


#: A `gh` runner: `gh_run`'s signature. Audit writers pass their own module's
#: `gh_run` so a test that fakes a script's `gh` layer fakes these calls too.
GhRunner = Callable[..., object]


def post_comment(
    subject: str,
    number: int,
    body: str,
    config: dict,
    *,
    run: GhRunner | None = None,
) -> bool:
    """Post a comment on an issue or PR via `gh <subject> comment`.

    The one comment-post the freeform verbs and every audit writer share. `run`
    is the `gh` runner (default `gh_run`). Returns True on success; prints gh's
    stderr and returns False on any failure.
    """
    runner = run or gh_run
    try:
        proc = runner(
            ["gh", subject, "comment", str(number), "--body", body],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh {subject} comment failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def fetch_comments(
    subject: str, number: int, config: dict, *, run: GhRunner | None = None
) -> list[dict]:
    """The issue's or PR's comments as `gh <subject> view --json comments`
    returns them (whole entries, authorship fields included), or `[]` when they
    cannot be read.

    An unreadable list is deliberately indistinguishable from an empty one: the
    only consumer is the audit retry scan, and finding nothing makes it post
    again — the safe direction for an audit trail.
    """
    runner = run or gh_run
    try:
        proc = runner(
            ["gh", subject, "view", str(number), "--json", "comments"],
            config,
            check=False,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout)
    except (TypeError, ValueError):
        return []
    comments = data.get("comments") if isinstance(data, dict) else None
    if not isinstance(comments, list):
        return []
    return [c for c in comments if isinstance(c, dict)]


def post_audit_once(
    subject: str,
    number: int | None,
    key: str,
    body: str,
    config: dict,
    *,
    run: GhRunner | None = None,
    comments: list | None = None,
    present_note: str = "audit comment already present; idempotent skip",
    posted_note: str = "",
) -> bool:
    """Post the audit comment `body` unless that exact comment is already there.

    The one fetch / scan / post-if-absent shape behind every audit comment
    (#902). It skips only when `_lib.audit.own_audit_posted` finds a comment,
    posted unedited by the account `gh` posts as, whose body equals `body`
    (line endings and trailing whitespace aside). So a retry of the same act
    skips, a distinct act posts, nobody else's comment can suppress the record,
    and neither can a same-account comment that merely contains the key.

    `key` is the act's `_lib.audit.audit_key`; `body` must carry it as a line —
    it is what makes two distinct acts render two distinct bodies, so a body
    without it is a writer bug and raises `ValueError` before any `gh` call.

    `subject` is `"issue"` or `"pr"`. `run` is the `gh` runner (default
    `gh_run`). `comments` lets a caller thread an already-fetched list in, so N
    audits on one mutation cost one fetch; that is sound because each audit
    looks for its own distinct body.

    True when the comment is posted or already present; False when `number` is
    unknown or a needed post failed (the caller then aborts before mutating).
    """
    if key not in body.splitlines():
        raise ValueError(f"audit comment body does not carry its key {key!r}")
    if number is None:
        return False
    if comments is None:
        comments = fetch_comments(subject, number, config, run=run)
    if own_audit_posted(comments, body):
        print(f"  {present_note}")
        return True
    if not post_comment(subject, number, body, config, run=run):
        return False
    if posted_note:
        print(f"  {posted_note}")
    return True


def structured_comment_reason(body: str) -> str | None:
    """If `body`'s first line would be mis-parsed as a methodology-**structured**
    comment, return a human-readable reason; else None.

    A freeform comment must never be able to spoof a form the engine parses off a
    comment: a DEC-028 reviewer verdict (`done-work`'s agent-mode gate-checker
    reads the first line), a human-mode `Approved`-prefix approval
    (`done-work.py` counts a non-author comment that starts with `Approved`), or
    an audit-trail note (the DEC-014 `Bypassed by …` template / the
    `Approved by bypass:` bypass-audit line). Those are emitted only as
    side-effects of the verbs that own them — the freeform verb refuses to
    impersonate them so a note can never be counted as a gate decision or read
    as an audit record.
    """
    stripped = body.strip()
    if not stripped:
        return None
    first = stripped.splitlines()[0].strip()
    token, _kind, _name = parse_verdict_line(first)
    if token is not None:
        return "first line matches the DEC-028 reviewer-verdict grammar"
    if first.startswith("Approved"):
        return (
            "first line starts with `Approved` — `done-work` would count it as a "
            "human-mode approval"
        )
    if first.startswith("Bypassed by ") or first.startswith("Approved by bypass:"):
        return "first line matches an audit-comment template (DEC-014 / bypass audit)"
    return None


def resolve_body(body: str | None) -> str | None:
    """Validate the `--body` text (present, non-empty). Returns the text, or
    None on a usage error (message printed).

    Comments take `--body` only — per the capability convention, `--body-file`
    is reserved for issue/PR *body* writes (which route through the provenance
    seam); a comment is not a body write. An agent constructs the argv directly,
    so a multi-line `--body` string carries a long note without shell friction.
    """
    if body is None:
        print("error: nothing to post. Pass --body.", file=sys.stderr)
        return None
    if not body.strip():
        print("error: comment body is empty.", file=sys.stderr)
        return None
    return body


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    path = capability_root / "project" / "members.yaml"
    if not path.is_file():
        return []
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return []
    if not isinstance(data, dict):
        return []
    members = data.get("members") or []
    return members if isinstance(members, list) else []


def run_comment_verb(subject: str) -> int:
    """Full `comment-<subject>` flow: guards, body resolution, the clone that
    posts, and the post, framed with the line and stamp that name that clone."""
    label = _SUBJECT_LABEL[subject]
    parser = argparse.ArgumentParser(
        description=(
            f"Post a freeform comment on a GitHub {label} through the "
            "capability's validated path (membership + foreign-repo guards). "
            "The comment mutates no lifecycle state (DEC-047)."
        ),
    )
    parser.add_argument("number", type=int, help=f"GitHub {label} number.")
    parser.add_argument(
        "--body",
        default=None,
        help="Comment body text (required, non-empty). May be multi-line.",
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
        help="Print what would be posted; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    body = resolve_body(args.body)
    if body is None:
        return 2

    # A freeform comment must not impersonate a methodology-structured comment
    # the engine parses (DEC-047): a DEC-028 verdict, a human-mode `Approved`
    # approval, or an audit-trail note. Refuse before any mutation.
    spoof = structured_comment_reason(body)
    if spoof is not None:
        print(
            f"error: refusing to post — {spoof}. A freeform comment must not "
            "impersonate a structured comment the engine parses; reword the "
            "first line.",
            file=sys.stderr,
        )
        return 2

    # Foreign-repo mutation guard (COR-039 / ADR-034) before any gh mutation.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Who posts: the clone's seat, confirmed on its state issue, or no seat
    # (DEC-059 point 6). Imported here, since `instance_claims` imports this
    # module for its audit comments.
    from _lib import instance_claims

    try:
        clone = instance_claims.this_clone(
            capability_root, invoker.github_login, config, dry_run=args.dry_run
        )
    except instance_claims.Unconfirmed as exc:
        return instance_claims.say_unconfirmed(f"comment-{subject}", args.number, exc)
    poster = poster_of(clone)

    preview = body.strip().splitlines()[0] if body.strip() else ""
    if len(preview) > 72:
        preview = preview[:69] + "..."
    print(f"comment-{subject}: #{args.number}")
    print(f"  body: {len(body)} chars — {preview!r}")
    print(f"  posted by: {poster.named()}")

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Post the comment? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    if not post_comment(subject, args.number, stamp_freeform(sign(body, poster)), config):
        return 3

    print(f"\n[ok] commented on {label} #{args.number}.")
    return 0
