"""Foreign-repo mutation self-guard (per [COR-039] / [ADR-034]).

A session rooted in repo A can `cd` into a different project's repo B and
file an issue, author a record, or commit there — landing
mechanically-correct artifacts under the wrong project's governance.
[COR-039] fixes the principle (a session mutates only the repo it is rooted
in; cross-repo mutation is operator-gated, never silent); [ADR-034] records
the Claude Code realization: the mutating program itself compares the
**cd-invariant session anchor** against the **cd-derived mutation target**
and operator-gates on divergence.

The two reads, and why they diverge under the incident's `cd`:

  * **anchor** — the repo the session is *rooted* in. Read from
    ``CLAUDE_PROJECT_DIR``, the harness's session-launch contract, which is
    frozen at launch and **does not move with `cd`**. `cd /B && create-issue`
    leaves the anchor pointing at A. This is the one signal in the system
    that survives a `cd` (a second cwd-walk would resolve B and the
    comparison would be B-vs-B — the trap [ADR-034] rejects).
  * **target** — the repo the mutation will *land* in. Read from the cwd's
    git work-tree, i.e. exactly what `gh`/`git` act on. A `cd /B` redirects
    it to B.

  * **divergence** — the two resolve to *different* git repositories. On
    divergence the guard **refuses (under autonomy) or prompts
    (interactively)** — never a hard deny, so a genuinely-intended
    cross-repo mutation stays reachable via the per-change operator gate
    ([DEC-022] mesh-compatibility).

Honest about reach ([ADR-034] point 5, [COR-028] honesty discipline). This
is a **discipline-grade interlock, not a security boundary.** It catches the
*accidental-handoff* shape — the methodology's own validated path used while
the session is `cd`'d into the wrong repo — reliably, for that path. It does
**not** stop a determined bypass that routes around the methodology: a raw
``gh -R owner/B``, a raw ``git -C /B``, or ``unset CLAUDE_PROJECT_DIR``. Those
are the declared residual gap. In particular, when ``CLAUDE_PROJECT_DIR`` is
unset the guard **cannot determine** the anchor and therefore **does not
fire** (it never fabricates a "blocked" it cannot back) — see
:func:`evaluate`'s ``UNDETERMINED`` outcome.

Compute the check ONCE here ([COR-007]); the mutating scripts call
:func:`enforce` at the mutation seam rather than re-deriving the comparison.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Per-change operator override (ADR-034 point 4): an explicit, deliberate
# "yes, I mean this cross-repo mutation" signal, confirmed PER INVOCATION via
# the ``--allow-foreign-repo`` flag the mutating scripts expose. There is no
# env-var override: a session-sticky env switch ("set once, silently authorise
# every mutation for the whole session") is the reflexive-escape trap
# (rules/core.md 14-15) and contradicts ADR-034 point 4's "per change … never
# silent" framing. The per-invocation flag IS the per-change path and also
# serves CI / non-interactive use (pass it per call).

# Verdicts from :func:`evaluate`.
SAME_REPO = "same-repo"          # target == anchor → clean pass, no friction.
DIVERGED = "diverged"            # target != anchor → operator-gate fires.
OVERRIDDEN = "overridden"        # diverged, but the operator confirmed the override.
UNDETERMINED = "undetermined"    # anchor or target unresolvable → honest no-fire.

# Sub-classification of UNDETERMINED, for the fault-vs-non-coverage split (G-1).
NONCOVERAGE = "noncoverage"  # honest declared gap (unset anchor / non-git cwd) → silent.
FAULT = "fault"              # git errored/timed-out when it shouldn't have → warn.


@dataclass(frozen=True)
class RepoIdentity:
    """A git-only, network-free identity for "which repo will `gh`/`git` act on".

    ADR-034's contract is the repo the mutation *lands in*, not a work-tree
    path. Two reads that path-equality gets wrong — a linked worktree / second
    clone of the same repo (false DIVERGED), and two different repos at the
    same path (false SAME_REPO) — both collapse correctly when the identity is:

      * ``common_dir`` — ``git rev-parse --git-common-dir``, absolutised. Linked
        worktrees of one repo share a single ``.git`` common-dir, so they match.
      * ``origin_url`` — the normalised ``origin`` remote URL, or None when the
        repo has no ``origin``. Two clones of the same remote match here.

    A repo with no ``origin`` (fresh ``git init``) carries ``origin_url=None``
    and falls back to the common-dir comparison alone.
    """

    common_dir: Path
    origin_url: str | None


@dataclass(frozen=True)
class GuardOutcome:
    """The result of comparing the mutation target against the session anchor."""

    verdict: str  # one of SAME_REPO / DIVERGED / OVERRIDDEN / UNDETERMINED
    anchor_repo: Path | None  # the session-anchor git work-tree, or None if undetermined
    target_repo: Path | None  # the cwd-derived git work-tree, or None if undetermined
    reason: str               # human-readable explanation (residual-gap case names itself)
    # Only meaningful when verdict == UNDETERMINED: NONCOVERAGE (declared gap,
    # proceed silently) vs FAULT (git failed unexpectedly, proceed but warn).
    undetermined_kind: str | None = None

    @property
    def blocks(self) -> bool:
        """Whether this outcome should stop the mutation (absent an operator OK)."""
        return self.verdict == DIVERGED


class _GitFault(Exception):
    """A git invocation failed unexpectedly (errored / timed out / not on PATH).

    Distinct from "this directory is honestly not a git repo": that is signalled
    by :func:`_git_toplevel` returning None on a clean non-zero exit, not by
    raising. A raised fault drives the G-1 warn path; a None drives silent
    non-coverage.
    """


def _run_git(args: list[str], *, cwd: Path | str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C <cwd> <args>`` capturing output; raise :class:`_GitFault` if git can't run.

    Raises only on a transport-level failure (git not on PATH, a timeout, an
    OSError) — i.e. git couldn't run at all. A clean non-zero exit (e.g. "not a
    git repository", "no such remote") is returned to the caller to interpret,
    not raised, so honest non-coverage stays distinguishable from a fault.
    """
    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise _GitFault(f"git {' '.join(args)} could not run: {exc!r}") from exc


def _git_toplevel(start: Path | str) -> Path | None:
    """Resolve the git work-tree root containing *start*, or None if not in a repo.

    Returns None when *start* is honestly not inside a git work-tree (git exits
    non-zero cleanly). Raises :class:`_GitFault` when git could not run at all
    (the fault path); the caller distinguishes the two per G-1.
    """
    proc = _run_git(["rev-parse", "--show-toplevel"], cwd=start)
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    if not out:
        return None
    try:
        return Path(out).resolve()
    except OSError:
        return None


# The common remote transports that name one repo three different ways:
#   * scp-like ssh:  git@host:owner/repo(.git)
#   * ssh URL:       ssh://git@host/owner/repo(.git)
#   * https / http:  https://host/owner/repo(.git)
# Each canonicalises to a single ``host/owner/repo`` identity so the SAME repo
# fetched over ssh and over https does not false-DIVERGE. Anything these don't
# match (a local filesystem path origin, an exotic scheme) falls back to the
# strip+casefold below — never crash, never become *less* strict.
_SCHEME_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://(?P<rest>.*)$")
_SCP_LIKE_RE = re.compile(r"^[^/]+:[^/].*$")  # `host:path` with no `://` scheme.


def _strip_git_suffix(path: str) -> str:
    """Drop a single trailing ``.git`` and any trailing slashes from *path*."""
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    return path


def _canonicalize_transport(raw: str) -> str | None:
    """Collapse the common ssh/https remote forms to ``host/owner/repo``, or None.

    Recognises the three forms that name one GitHub/GitLab-style repo:
      * scp-like ssh   ``git@host:owner/repo(.git)``  → ``host/owner/repo``
      * ssh URL        ``ssh://git@host/owner/repo(.git)`` → ``host/owner/repo``
      * https / http   ``https://host/owner/repo(.git)``   → ``host/owner/repo``

    In each case a leading ``user@`` and the scheme are stripped, the host's
    ``:``-or-``/`` path separator is normalised to ``/``, and a trailing
    ``.git`` / ``/`` is dropped. Returns None for anything unrecognised (a local
    filesystem path, no scheme and no ``host:path`` colon) so the caller can fall
    back to the conservative strip+casefold — this stays a collapser, never a
    parser that could crash or over-match.
    """
    url = raw.strip()

    # Scheme URLs (ssh://, https://, http://, git://, ...): take the part after
    # ``://``, drop a userinfo ``user@`` prefix, then split host from path on the
    # first ``/``.
    scheme_match = _SCHEME_URL_RE.match(url)
    if scheme_match is not None:
        rest = scheme_match.group("rest")
        rest = rest.split("@", 1)[-1]  # drop a leading `user@`, if any.
        host, sep, path = rest.partition("/")
        if not sep or not host or not path:
            return None
        # Strip a possible `host:port` so the same host over different ports
        # still collapses (ports are not part of repo identity here).
        host = host.split(":", 1)[0]
        return f"{host}/{_strip_git_suffix(path)}"

    # scp-like ssh: `git@host:owner/repo(.git)` — no scheme, a `host:path` colon.
    if _SCP_LIKE_RE.match(url):
        userhost, _, path = url.partition(":")
        host = userhost.split("@", 1)[-1]  # drop a leading `user@`, if any.
        if not host or not path:
            return None
        return f"{host}/{_strip_git_suffix(path)}"

    return None


def _normalize_origin_url(raw: str) -> str:
    """Normalise an origin URL so two clones of the same remote compare equal.

    Canonicalises the common ssh/https transport forms to one
    ``host/owner/repo`` identity (via :func:`_canonicalize_transport`) so the
    SAME repo fetched over ``git@host:owner/repo.git`` and
    ``https://host/owner/repo.git`` compares equal rather than false-DIVERGEing.
    Anything that isn't one of those recognised forms (a local filesystem path
    origin, an exotic scheme) falls back to the conservative strip+casefold —
    drop a trailing ``.git`` / slash and case-fold — so the function never
    crashes and is never *less* strict than before. The whole result is
    case-folded (host and path casing are not significant for identity here).
    """
    canonical = _canonicalize_transport(raw)
    if canonical is not None:
        return canonical.casefold()
    url = _strip_git_suffix(raw.strip())
    return url.casefold()


def _origin_url(toplevel: Path) -> str | None:
    """The normalised ``origin`` remote URL for the repo at *toplevel*, or None.

    None when the repo has no ``origin`` remote (a clean non-zero exit from
    ``git remote get-url origin``) — the no-remote fallback case, not a fault.
    Raises :class:`_GitFault` if git could not run.
    """
    proc = _run_git(["remote", "get-url", "origin"], cwd=toplevel)
    if proc.returncode != 0:
        return None  # no `origin` remote (e.g. a fresh `git init`) — not a fault.
    out = proc.stdout.strip()
    if not out:
        return None
    return _normalize_origin_url(out)


def _repo_identity(start: Path | str) -> RepoIdentity | None:
    """Resolve the cd-invariant identity of the repo containing *start*, or None.

    Returns None when *start* is honestly not inside a git work-tree (declared
    non-coverage). Raises :class:`_GitFault` when git could not run (the warn
    path). Identity = (absolute git-common-dir, normalised origin URL); see
    :class:`RepoIdentity`.
    """
    toplevel = _git_toplevel(start)
    if toplevel is None:
        return None
    proc = _run_git(["rev-parse", "--git-common-dir"], cwd=toplevel)
    if proc.returncode != 0:
        return None
    common_raw = proc.stdout.strip()
    if not common_raw:
        return None
    common = Path(common_raw)
    if not common.is_absolute():
        # --git-common-dir is relative to the work-tree when inside it; anchor
        # it at the resolved toplevel so two worktrees of one repo (which share
        # the common-dir) resolve to the same absolute path.
        common = toplevel / common
    try:
        common = common.resolve()
    except OSError:
        return None
    return RepoIdentity(common_dir=common, origin_url=_origin_url(toplevel))


def _same_identity(anchor: RepoIdentity, target: RepoIdentity) -> bool:
    """SAME_REPO iff same git-common-dir OR same (non-None) normalised origin URL.

    The common-dir match collapses linked worktrees of one repo; the origin
    match collapses separate clones of one remote. When either repo lacks an
    origin (``origin_url is None``), only the common-dir comparison applies —
    so two distinct no-remote repos at different common-dirs are DIVERGED, while
    the worktrees of one no-remote repo still match on the common-dir.
    """
    if anchor.common_dir == target.common_dir:
        return True
    if (
        anchor.origin_url is not None
        and target.origin_url is not None
        and anchor.origin_url == target.origin_url
    ):
        return True
    return False


def _anchor_dir() -> str | None:
    """The session anchor directory from ``CLAUDE_PROJECT_DIR``, or None.

    None is the declared residual-gap signal: with no anchor the guard
    cannot determine which repo the session is rooted in, and per [ADR-034]
    point 5 it must NOT pretend coverage — it falls back to no-fire.
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return env if env else None


def _resolve(start: Path | str) -> tuple[Path | None, RepoIdentity | None]:
    """Resolve *start* to (display work-tree, identity), or (None, None) for non-coverage.

    The work-tree toplevel is the human-readable path the divergence message
    shows; the :class:`RepoIdentity` is what the SAME/DIVERGED decision compares.
    Returns (None, None) when *start* is honestly not in a git repo. Propagates
    :class:`_GitFault` when git could not run — :func:`evaluate` turns that into
    the FAULT-flavoured UNDETERMINED so the caller can warn (G-1).
    """
    toplevel = _git_toplevel(start)
    if toplevel is None:
        return None, None
    return toplevel, _repo_identity(toplevel)


def evaluate(
    *,
    override: bool = False,
    target_cwd: Path | str | None = None,
    anchor_dir: str | None = None,
) -> GuardOutcome:
    """Compare the mutation target against the session anchor. Pure; no network I/O.

    Resolution:
      * anchor — the repo identity of ``CLAUDE_PROJECT_DIR`` (``anchor_dir``
        overrides the env read for tests);
      * target — the repo identity of the cwd (``target_cwd`` overrides
        ``Path.cwd()`` for tests).

    "Identity" is the git-only, network-free notion ADR-034 means by "the repo
    `gh`/`git` would act on": git-common-dir (collapses linked worktrees) plus
    normalised origin URL (collapses clones of one remote). See
    :class:`RepoIdentity` and :func:`_same_identity`. Path-equality is NOT used
    — it gave both false DIVERGED (a worktree / second clone) and false
    SAME_REPO (different repos at one path).

    Outcomes:
      * ``UNDETERMINED`` — the anchor is unset, OR either side is not inside a
        git work-tree, OR a git invocation failed. Carries ``undetermined_kind``:
        ``NONCOVERAGE`` (the declared residual gap — proceed silently) or
        ``FAULT`` (git errored when it shouldn't have — proceed but warn, G-1).
        The honest residual-gap fallback ([ADR-034] point 5): the guard cannot
        back a "blocked" verdict, so it does not fire.
      * ``SAME_REPO`` — target and anchor are the same repo identity. Clean
        pass, no friction (the ordinary in-tree mutation; also a worktree /
        second clone of the session's own repo).
      * ``OVERRIDDEN`` — diverged, but ``override`` is set (the operator
        confirmed the per-change cross-repo gate). Pass with an advisory.
      * ``DIVERGED`` — target and anchor are different repo identities and no
        override. The operator-gate fires (refuse-or-prompt at the caller).

    ``override`` is the per-invocation ``--allow-foreign-repo`` flag the caller
    passes; there is no env override (a session-sticky switch is rejected — see
    the module-level override comment / G-2).
    """
    override = bool(override)

    anchor_dir = anchor_dir if anchor_dir is not None else _anchor_dir()
    if anchor_dir is None:
        # Honest non-coverage: no anchor at all → proceed silently (G-1).
        return GuardOutcome(
            verdict=UNDETERMINED,
            anchor_repo=None,
            target_repo=None,
            undetermined_kind=NONCOVERAGE,
            reason=(
                "CLAUDE_PROJECT_DIR is unset — the session anchor cannot be "
                "determined, so the foreign-repo guard does not fire. This is "
                "the declared residual gap (ADR-034 point 5), not a clean "
                "same-repo result."
            ),
        )

    target = target_cwd if target_cwd is not None else Path.cwd()
    try:
        anchor_repo, anchor_id = _resolve(anchor_dir)
        target_repo, target_id = _resolve(target)
    except _GitFault as fault:
        # The anchor is set AND we tried to resolve a real path, but git failed
        # to run (errored / timed out / not on PATH). This is a FAULT, not honest
        # non-coverage: warn rather than silently disabling the interlock (G-1).
        return GuardOutcome(
            verdict=UNDETERMINED,
            anchor_repo=None,
            target_repo=None,
            undetermined_kind=FAULT,
            reason=(
                "the foreign-repo guard could not resolve repo identity because "
                f"a git invocation failed unexpectedly ({fault}); proceeding "
                "without the interlock."
            ),
        )

    if anchor_id is None or target_id is None:
        # One side is honestly not a git repo (clean non-zero git exit). Declared
        # non-coverage → proceed silently (G-1).
        return GuardOutcome(
            verdict=UNDETERMINED,
            anchor_repo=anchor_repo,
            target_repo=target_repo,
            undetermined_kind=NONCOVERAGE,
            reason=(
                "anchor or target is not inside a git work-tree — the "
                "foreign-repo guard cannot compare repositories and does not "
                "fire (it does not claim coverage it cannot back)."
            ),
        )

    if _same_identity(anchor_id, target_id):
        return GuardOutcome(
            verdict=SAME_REPO,
            anchor_repo=anchor_repo,
            target_repo=target_repo,
            reason="mutation target is the session's own repo.",
        )

    if override:
        return GuardOutcome(
            verdict=OVERRIDDEN,
            anchor_repo=anchor_repo,
            target_repo=target_repo,
            reason=(
                f"cross-repo mutation confirmed by operator override: "
                f"target {target_repo} differs from session anchor "
                f"{anchor_repo}."
            ),
        )

    return GuardOutcome(
        verdict=DIVERGED,
        anchor_repo=anchor_repo,
        target_repo=target_repo,
        reason=(
            f"mutation target {target_repo} is a DIFFERENT repo than the "
            f"session anchor {anchor_repo}."
        ),
    )


def _is_autonomous(interactive: bool | None) -> bool:
    """Whether the gate should refuse (autonomy) rather than prompt (interactive).

    ``interactive`` lets the caller force the mode (and lets tests pin it).
    When None, autonomy is inferred: a non-tty stdin (CI / agent / piped) is
    autonomous; a tty is interactive. ``PM_INVOKER_LOGIN`` (the CI/agent
    identity signal used by membership resolution) also marks autonomy.
    """
    if interactive is not None:
        return not interactive
    if os.environ.get("PM_INVOKER_LOGIN"):
        return True
    try:
        return not sys.stdin.isatty()
    except (ValueError, OSError):
        return True


def _divergence_message(outcome: GuardOutcome) -> str:
    """The honest refuse/prompt explanation for a DIVERGED outcome.

    Names the mechanism an interlock against *accidental* cross-repo handoff
    (not a wall), states the two ways forward (re-root, or confirm the
    override), and cites COR-039. Per [ADR-034] point 5 / [COR-028] it must
    NOT overstate: a determined bypass (raw `gh -R`, raw `git -C`,
    `unset CLAUDE_PROJECT_DIR`) routes around this and is the declared
    residual gap.
    """
    return (
        "[refused] cross-repo mutation interlock (COR-039 / ADR-034)\n"
        f"          → This session is anchored to: {outcome.anchor_repo}\n"
        f"          → But the mutation would land in: {outcome.target_repo}\n"
        "          → That second repo's governance (its rules, conventions, "
        "agents, permission model) is NOT loaded in this session, so the "
        "mutation would run under the wrong project's context.\n"
        "          → This is an interlock against an *accidental* cross-repo "
        "handoff, not a security boundary — a determined bypass (raw "
        "`gh -R`, `git -C`, or unsetting CLAUDE_PROJECT_DIR) is out of its "
        "reach and unaffected.\n"
        "          → To proceed: open a session rooted in "
        f"{outcome.target_repo}, OR — if you genuinely intend this "
        "cross-repo mutation — confirm the override per invocation "
        "(pass --allow-foreign-repo)."
    )


def add_override_argument(parser) -> None:
    """Register the per-change cross-repo override flag on a script's argparse parser.

    Centralises the flag name and help text (COR-007) so every mutating
    script exposes ``--allow-foreign-repo`` identically. The script reads
    ``args.allow_foreign_repo`` and passes it to :func:`enforce`.
    """
    parser.add_argument(
        "--allow-foreign-repo",
        action="store_true",
        help=(
            "Confirm a deliberate cross-repo mutation (operator override per "
            "COR-039 / ADR-034). By default a mutation whose target repo "
            "differs from the session anchor (CLAUDE_PROJECT_DIR) is gated; "
            "this flag is the per-change operator confirmation (pass it per "
            "invocation — it is also how CI / non-interactive callers confirm)."
        ),
    )


def enforce(
    *,
    override: bool = False,
    interactive: bool | None = None,
    target_cwd: Path | str | None = None,
    anchor_dir: str | None = None,
    stream=None,
) -> bool:
    """Run the foreign-repo guard at a mutation seam; return True iff the mutation may proceed.

    This is the single call site the mutating scripts use (COR-007): compute
    the comparison ONCE, then gate. The caller invokes it AFTER membership /
    validation and BEFORE the `gh`/`git` mutation, e.g.::

        if not session_guard.enforce(override=args.allow_foreign_repo):
            return 1

    Behaviour by outcome:
      * SAME_REPO → returns True silently (no friction).
      * UNDETERMINED → returns True (the guard never blocks what it cannot
        evaluate), but the two flavours print differently (G-1):
          - NONCOVERAGE (unset anchor / non-git cwd) → silent. This is the
            declared residual gap, an expected state, not worth a warning.
          - FAULT (git errored/timed-out when it shouldn't have) → prints a
            one-line ``[warning]`` first, so a flaky-git failure that loses the
            interlock on a *possible* cross-repo mutation leaves a trace rather
            than silently disabling the guard.
      * OVERRIDDEN → returns True after printing a one-line advisory that a
        cross-repo mutation is proceeding under operator override.
      * DIVERGED → operator-gate. Interactive: prompt; a "yes" returns True
        (the per-change confirm), anything else returns False. Autonomous
        (non-tty / agent / CI): refuse-with-explanation, returns False.

    Never raises for a guard fault — a failure to evaluate degrades to the
    UNDETERMINED no-fire (warned, per above), never a silent block.

    ``stream`` defaults to the *current* ``sys.stderr`` (resolved at call time,
    not import time, so test capture and stream redirection are honoured).
    """
    if stream is None:
        stream = sys.stderr
    try:
        outcome = evaluate(
            override=override, target_cwd=target_cwd, anchor_dir=anchor_dir
        )
    except Exception as exc:  # a guard fault must never silently block a mutation
        print(
            f"[warning] foreign-repo guard could not evaluate ({exc!r}); "
            "proceeding without the interlock (residual gap, not a block).",
            file=stream,
        )
        return True

    if outcome.verdict == SAME_REPO:
        return True

    if outcome.verdict == UNDETERMINED:
        if outcome.undetermined_kind == FAULT:
            print(
                f"[warning] foreign-repo guard: {outcome.reason} (residual gap, "
                "not a block).",
                file=stream,
            )
        # NONCOVERAGE: proceed silently — the declared, expected gap.
        return True

    if outcome.verdict == OVERRIDDEN:
        print(
            f"[advisory] proceeding with cross-repo mutation under operator "
            f"override — {outcome.reason}",
            file=stream,
        )
        return True

    # DIVERGED — operator-gate.
    print(_divergence_message(outcome), file=stream)
    if _is_autonomous(interactive):
        # Under autonomy: refuse-with-explanation (the message above is the
        # explanation). No prompt — there is no operator at the keyboard.
        return False
    # Interactive: offer the per-change confirm at the keyboard.
    try:
        reply = input("Proceed with the cross-repo mutation anyway? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print("aborted.", file=stream)
        return False
    return reply.strip().lower() in ("y", "yes")
