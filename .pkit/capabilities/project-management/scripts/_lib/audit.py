"""The DEC-049 audit-comment primitives — one canonical format, one knob.

[project-management:DEC-049] makes the engine journal the canonical audit trail
and GitHub comments a *configurable, provenance-stamped projection* of it. Two
consequences bind every audit-comment writer, and this module owns both so no
writer re-derives them (COR-007):

  * **One canonical format from one schema field.** The human-readable audit
    line comes from `validation-severity.yaml`'s
    `severities.bypassable-with-audit.audit_comment_template`, carrying the
    uniform `<!-- pkit-audit -->` marker. #672's divergence came from a writer
    hardcoding its own `[audit] …` line; the fix is that nobody hardcodes one.
  * **One projection knob.** `audit.projection` (`off` | `audit` | `full`,
    default `audit`) decides how much of the journal is projected as comments.

Writers that need to say *more* than the template's actor/reason (e.g.
`done-work`'s per-reviewer override, which must also record which reviewer was
waived and its state at override time) render the canonical line from
`render_audit_comment` and append their own prose *below* it — the format stays
canonical, the detail is additive. They must not fork the line itself.

`move-issue` is the sole writer of the *transition* audit (DEC-049's
single-poster rule); this module is deliberately silent about who may write,
which is a per-mutation question the DEC settles, not a formatting one.

It also owns the one **own-comment recognition** every audit writer uses to stay
idempotent (#901, #902): a writer closes its comment with an `audit_key` naming
the specific audited act, and before posting it skips only when
`own_audit_posted` finds a comment whose body is EXACTLY the body it is about to
post, posted unedited by the account `gh` posts as. See that function for the
guard and its threat model. The fetch / scan / post wiring around it lives once
in `_lib.comment.post_audit_once`, which every audit writer calls.

Pure formatting, recognition + config reading: no `gh` calls, so it is
unit-testable without a live repo.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

#: The severity whose `audit_comment_template` is the canonical format (DEC-014).
SEVERITY_BYPASSABLE = "bypassable-with-audit"

#: The audit-comment provenance marker (DEC-049), uniform with the other
#: `<!-- pkit-* -->` markers (verdict / provenance / hook). Filterable; the
#: canonical audit-comment shape lives in the schema template below.
AUDIT_MARKER = "<!-- pkit-audit -->"

#: Fallback if the schema can't be read — must match the schema's canonical form.
AUDIT_TEMPLATE_FALLBACK = f"{AUDIT_MARKER}\nBypassed by <name> <<email>>: <reason>"

#: The opening of the trailing idempotency key that closes an audit comment.
#: It is a key, not a kind marker: the comment's kind is its own first-line
#: marker, and this line only lets a retry recognise a comment it already posted.
AUDIT_KEY_PREFIX = "<!-- pkit-audit-key: "

#: The projection levels (DEC-049 Decision 2), in increasing verbosity.
PROJECTION_OFF = "off"
PROJECTION_AUDIT = "audit"
PROJECTION_FULL = "full"
_PROJECTION_LEVELS = (PROJECTION_OFF, PROJECTION_AUDIT, PROJECTION_FULL)


def load_audit_template(capability_root) -> str:
    """The canonical audit-comment template, read from `validation-severity.yaml`'s
    `severities.bypassable-with-audit.audit_comment_template` — the single source
    of truth per DEC-049. Falls back to the known canonical form on any read error."""
    try:
        path = Path(capability_root) / "schemas" / "validation-severity.yaml"
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
        tmpl = data["severities"][SEVERITY_BYPASSABLE]["audit_comment_template"]
        return (
            tmpl.strip()
            if isinstance(tmpl, str) and tmpl.strip()
            else AUDIT_TEMPLATE_FALLBACK
        )
    except (OSError, YAMLError, KeyError, TypeError):
        # TypeError also covers a None root — a caller with no resolved capability
        # root still gets the canonical form rather than an exception.
        return AUDIT_TEMPLATE_FALLBACK


def render_audit_comment(capability_root, invoker, reason: str) -> str:
    """Render the one canonical audit comment (DEC-049) from the schema template:
    marker + actor (`<name> <<email>>`) + reason. The transition itself is recorded
    by the timeline (the comment carries the *why*, not the state). Renders cleanly
    when the email is unresolved."""
    template = load_audit_template(capability_root)
    name = (
        getattr(invoker, "github_login", None)
        or getattr(invoker, "email", None)
        or "unknown"
    )
    email = getattr(invoker, "email", None) or ""
    body = template.replace("<name>", name).replace("<reason>", reason)
    if email:
        body = body.replace("<email>", email)
    else:
        body = body.replace(" <<email>>", "").replace("<<email>>", "")
    return body


def audit_projection(config) -> str:
    """The audit-comment projection level (DEC-049): `off` | `audit` | `full`.
    Default `audit`. The engine journal records every governed mutation regardless
    of level; this only controls how much is projected as GitHub comments."""
    audit = config.get("audit") if isinstance(config, dict) else None
    level = audit.get("projection") if isinstance(audit, dict) else None
    return level if level in _PROJECTION_LEVELS else PROJECTION_AUDIT


def audit_key(writer: str, *components: str) -> str:
    """The idempotency key for one audited act: `<!-- pkit-audit-key: <writer>:<digest> -->`.

    `writer` is a code-literal name for the writing command and act (e.g.
    `done-work-bypass`); `components` are what identifies the specific act — what
    a retry repeats exactly and a distinct act does not (a reason, a head commit,
    a transition). Callers normalise them (strip a reason) before passing them.

    Hashed rather than interpolated so no component — a free-text reason, an
    adopter-configured reviewer name — can close the HTML comment early. The
    digest is opaque by design: the readable detail is in the comment's prose.
    It is also PREDICTABLE by design (anyone who knows the reason and the head
    can compute it), so it is not what stops suppression: `own_audit_posted`
    matches the WHOLE body, not the key. The key's job is to make two distinct
    acts render two distinct bodies.
    """
    digest = hashlib.sha256("\x00".join(components).encode("utf-8")).hexdigest()[:16]
    return f"{AUDIT_KEY_PREFIX}{writer}:{digest} -->"


def bypass_audit_key(writer: str, reason: str, head: str) -> str:
    """The idempotency key for a whole-gate or CI bypass: the stripped reason and
    the PR head commit (#902). A second bypass with a different reason, or the
    same reason after new commits, is a distinct act and gets its own key; a
    retry of the same bypass reproduces it. An unknown head contributes an empty
    component, which differs from every key minted with a known head, so a retry
    across that boundary posts again."""
    return audit_key(writer, reason.strip(), head or "")


#: How many characters of a commit SHA an audit comment's prose shows.
SHORT_SHA_LENGTH = 7


def short_sha(head: str) -> str:
    """The short form of a commit SHA for an audit comment's prose, or
    `unknown` when the head could not be read."""
    head = (head or "").strip()
    return head[:SHORT_SHA_LENGTH] if head else "unknown"


def render_ci_bypass_audit_body(
    marker: str,
    invoker,
    reason: str,
    failing_checks,
    head: str,
    key: str,
) -> str:
    """Render a CI-bypass audit comment — the one shape `done-work` and
    `merge-pr` share, differing only in their first-line kind `marker`.

    Follows the schema's `audit_comment_template`
    (`Bypassed by <name> <<email>>: <reason>`), names the checks the bypass
    overrode so the trail records *what* was skipped, names the short PR head
    the bypass was made against (two bypasses with the same reason either side
    of a force-push would otherwise read identically), and closes with the
    idempotency `key`.
    """
    name = (
        getattr(invoker, "github_login", None)
        or getattr(invoker, "email", None)
        or "<unresolved>"
    )
    email = getattr(invoker, "email", None) or "<unknown>"
    checks = ", ".join(failing_checks) or "(none named)"
    return (
        f"{marker}\n\n"
        f"Bypassed by {name} <{email}>: {reason.strip()}\n\n"
        f"CI-status gate overridden at PR head {short_sha(head)}; "
        f"non-passing checks: {checks}.\n\n"
        f"{key}"
    )


def normalise_comment_body(body) -> str:
    """A comment body with only line endings and trailing whitespace normalised:
    CRLF / CR become LF, each line loses its trailing whitespace, and trailing
    blank lines go. Nothing else changes — the comparison stays exact in every
    character a reader sees."""
    text = str(body or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).rstrip("\n")


def is_own_unedited_comment(comment) -> bool:
    """True when `comment` (a `gh … view --json comments` entry) was posted by
    the account `gh` posts as and has never been edited.

    Both fields come from GitHub itself: `viewerDidAuthor` is GitHub's answer to
    "did the viewer write this?" for whoever `gh` is logged in as, so no login is
    resolved or compared here; `includesCreatedEdit` is true once anyone has
    edited the comment. Anything else — a missing field, a non-boolean — counts
    as not-own, which makes the caller post again.

    "Own" is broader than "pkit wrote it": it is every comment that account
    wrote. See `own_audit_posted` for why that is acceptable.
    """
    return (
        isinstance(comment, dict)
        and comment.get("viewerDidAuthor") is True
        and comment.get("includesCreatedEdit") is False
    )


def own_audit_posted(comments, body: str) -> bool:
    """True when the exact audit comment `body` is already on the subject.

    The guard (#902). A comment counts only when it (a) was posted, unedited, by
    the account `gh` posts as (`is_own_unedited_comment`) and (b) has a body
    EQUAL to `body` after `normalise_comment_body` (line endings and trailing
    whitespace only). The body ends with the act's `audit_key`, so two distinct
    acts render two distinct bodies. So:

      * a retry of the same act finds its own earlier post and skips;
      * a distinct act renders a different body and posts;
      * a comment by anyone else cannot suppress a post, whatever it contains;
      * a comment by the trusted account that merely CONTAINS a key — a
        multi-line bypass reason quoting another writer's key line, a note
        pasted by hand — is not equal to the body, so it does not suppress.

    Threat model. The key is computable from public facts, and any signed-in
    GitHub user can comment on a public repo (on a private one, anyone with read
    access), so "carries the key" alone would let any commenter erase a
    gate-override record — and for a gate override that comment IS the record.

    The trusted identity is the account `gh` posts as. That is not "pkit's own
    path": in CI it is the workflow token's account, so every workflow using
    `GITHUB_TOKEN` posts as it; locally it is the operator, so every comment the
    operator ever typed by hand is "own" too. Exact-body matching is what
    narrows that down: a same-account comment suppresses a post only when it
    already says, word for word, what the post would say — in which case the
    record the post would leave is already there.

    `includesCreatedEdit` is defence in depth, not a boundary: it stops an own
    comment later edited INTO the exact body from counting (pkit never edits an
    audit comment after posting it). Anyone able to edit another person's comment
    can already delete it, so this does not protect against them, and the guard
    does not claim to stop someone holding the posting identity or delete rights.

    Every doubt resolves toward posting again, never toward skipping: an
    unreadable comment list, a comment without the authorship fields, a
    mismatch between the account running pkit and the account that posted
    earlier, a body that differs in any visible character. An extra audit
    comment is noise; a missing one is a lost record.
    """
    wanted = normalise_comment_body(body)
    for comment in comments or ():
        if not is_own_unedited_comment(comment):
            continue
        if normalise_comment_body(comment.get("body")) == wanted:
            return True
    return False
