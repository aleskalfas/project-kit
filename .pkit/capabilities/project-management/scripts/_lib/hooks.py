"""Lifecycle-hook engine per [project-management:DEC-024-lifecycle-hooks].

Adopters declare post-action steps in `project/hooks.yaml`; lifecycle
scripts call `fire_hooks(event, context, config)` at the end of their
happy path to execute the declared hooks for that event. Failure
semantics: report-and-continue — a hook failure does not propagate to
the primary script's exit code (per DEC-024's "rollback is not
attempted").

Per DEC-024's discovery contract, hook kinds are pluggable: each kind
declares its shape via a JSON schema at
`schemas/hook-kinds/<kind>.schema.json`. The kit ships four v1 kinds
(`set-board-field`, `post-comment`, `assign-milestone`,
`custom-script`); future kinds land per COR-007.

Exports:

    HookResult       — outcome of one hook (status, kind, detail)
    HookFailure      — exception raised internally on per-kind failures
    fire_hooks(event, context, config) -> list[HookResult]
        Main entry. Reads hooks.yaml, dispatches the event's hooks,
        returns a list of results (success / skipped / failed).
    load_hooks_file(capability_root) -> dict
        Reads + parses `project/hooks.yaml`; returns `{}` if absent.
        Pre-check uses this independently.
    hook_stamp(stamp_id, event, subject, number, transition) -> str
        The first line of a `post-comment` hook's comment, naming the hook
        and the firing it posted for.
    hook_comment_posted(comments, stamp) -> bool
        Whether that firing's comment is already on the issue or PR.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # pragma: no cover
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]


# Sibling module — added to sys.path by the calling script.
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    # Last-resort fallback for unusual import contexts (tests load the
    # module by file path and may not have _lib on sys.path).
    gh_run = None  # type: ignore[assignment]

# The sole constructor of the non-label substrate writes (ADR-031). The
# `set-board-field` / `assign-milestone` handlers below obtain their `gh` write
# from this primitive rather than string-building the argv inline; the
# report-and-continue posture they apply to its result stays here (DEC-024).
try:
    import substrate_writes  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib import substrate_writes  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        substrate_writes = None  # type: ignore[assignment]

# The own-comment check the audit writers share (#902): only a comment the
# account `gh` posts as wrote, and nobody has edited, may stop a `post-comment`
# hook from posting. Dual-form like `_lib/comment.py`: `_lib/` on sys.path when
# loaded by file path, `scripts/` when imported as `_lib.hooks`.
try:
    from audit import (  # type: ignore[import-not-found]
        is_own_unedited_comment,
        normalise_comment_body,
    )
except ImportError:  # pragma: no cover
    from _lib.audit import (  # type: ignore[no-redef]
        is_own_unedited_comment,
        normalise_comment_body,
    )


HOOKS_RELATIVE_PATH = "project/hooks.yaml"

#: The two ends of the stamp a `post-comment` hook writes as its comment's first
#: line (DEC-024). Between them is `<name>:<firing>` — see `hook_stamp`.
HOOK_STAMP_OPEN = "<!-- pkit-hook: "
HOOK_STAMP_CLOSE = " -->"

#: The longest hook name a stamp shows. The firing digest after the name keeps
#: apart two hooks whose shown names coincide once cut or cleaned.
HOOK_STAMP_NAME_MAX = 64

#: How many hex digits of the firing digest a stamp carries.
FIRING_DIGEST_LENGTH = 16

LIFECYCLE_EVENTS: frozenset[str] = frozenset(
    {
        "after_create_issue",
        "after_close_issue",
        "after_open_pr",
        "after_merge_pr",
        "after_move_issue",
    }
)

KIT_SHIPPED_KINDS: frozenset[str] = frozenset(
    {
        "set-board-field",
        "post-comment",
        "assign-milestone",
        "custom-script",
    }
)


@dataclass(frozen=True)
class HookResult:
    """Outcome of one hook execution."""

    index: int  # zero-based index within the event's hook list
    kind: str  # hook kind that ran
    status: str  # "ok" | "skipped" | "failed"
    detail: str  # one-line human-readable summary
    error: str | None = None  # populated when status == "failed"


class HookFailure(Exception):
    """Raised internally by per-kind handlers; caught by fire_hooks."""


# ----- public entry point -----------------------------------------------


def fire_hooks(
    event: str,
    context: dict[str, Any],
    config: dict[str, Any],
    *,
    capability_root: Path | None = None,
    dry_run: bool = False,
) -> list[HookResult]:
    """Fire every hook declared for `event` in `hooks.yaml`.

    `context` carries the lifecycle event's runtime data — typically:
        issue: {number, title, ...}    # for issue events
        pr:    {number, title, ...}    # for pr events
        repo:  "owner/name"             # always

    `config` is the adopter's parsed `project/config.yaml` (used by
    the gh helper for host pinning). Pass `dry_run=True` to list the
    hooks that would fire without executing them — the result entries
    have `status="skipped"` and `detail` describes the planned action.

    Report-and-continue: per-hook failures are caught and recorded as
    `status="failed"` HookResult entries; the function does not raise
    for hook failures. The function may raise on programming errors
    (invalid event name, malformed result from a handler).

    `capability_root` defaults to walking up from CWD for
    `.pkit/capabilities/project-management/`. Pass explicitly when
    calling from a context where the resolver can't find it.
    """
    if event not in LIFECYCLE_EVENTS:
        raise ValueError(f"unknown lifecycle event {event!r}. Allowed: {sorted(LIFECYCLE_EVENTS)}")

    if capability_root is None:
        capability_root = _resolve_capability_root()
    if capability_root is None:
        # No installed capability tree — no hooks to fire.
        return []

    hooks_doc = load_hooks_file(capability_root)
    by_event = hooks_doc.get("hooks") if isinstance(hooks_doc.get("hooks"), dict) else {}
    entries = by_event.get(event) if isinstance(by_event, dict) else None
    if not isinstance(entries, list) or not entries:
        return []

    results: list[HookResult] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            results.append(
                HookResult(
                    index=index,
                    kind="<unknown>",
                    status="failed",
                    detail=f"hook entry #{index} is not a mapping",
                    error="malformed hook entry",
                )
            )
            continue
        kind = str(entry.get("kind", "")).strip()
        if not kind:
            results.append(
                HookResult(
                    index=index,
                    kind="<unknown>",
                    status="failed",
                    detail=f"hook entry #{index} missing required `kind`",
                    error="malformed hook entry",
                )
            )
            continue
        if kind not in KIT_SHIPPED_KINDS:
            results.append(
                HookResult(
                    index=index,
                    kind=kind,
                    status="skipped",
                    detail=f"unknown kind {kind!r}; ignored at fire-time",
                )
            )
            continue

        try:
            result = _dispatch(
                event=event,
                index=index,
                entry=entry,
                kind=kind,
                context=context,
                config=config,
                capability_root=capability_root,
                dry_run=dry_run,
            )
        except HookFailure as exc:
            result = HookResult(
                index=index,
                kind=kind,
                status="failed",
                detail=str(exc),
                error=str(exc),
            )
        except Exception as exc:  # report-and-continue contract
            result = HookResult(
                index=index,
                kind=kind,
                status="failed",
                detail=f"unexpected exception: {exc}",
                error=str(exc),
            )
        results.append(result)

    _report(event, results, dry_run=dry_run)
    return results


def load_hooks_file(capability_root: Path) -> dict[str, Any]:
    """Read + parse `project/hooks.yaml`. Returns `{}` when absent or unparseable.

    Public so pre-check can use the same loader without duplicating the
    file-discovery logic.
    """
    if YAML is None:  # pragma: no cover
        return {}
    path = capability_root / HOOKS_RELATIVE_PATH
    if not path.is_file():
        return {}
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def hook_stamp(
    stamp_id: str,
    event: str,
    subject: str,
    number: int,
    transition: Any = None,
) -> str:
    """The first line of a `post-comment` hook's comment, which identifies one
    firing of one hook: `<!-- pkit-hook: <name>:<firing> -->`.

    A firing is the hook (`stamp_id`), the lifecycle `event`, the `subject` it
    fired on (`"issue"` or `"pr"` and its `number`), and the transition's from
    and to states when the event carries one (`after_move_issue`). These are
    all the context the call sites pass that tells their firings apart: the
    same hook may be declared on several events, and an issue moves through
    many transitions. A retry of the same firing reproduces the stamp; a firing
    that differs in any of these renders a different one. Firings that agree on
    all of them are one firing: a transition the issue makes a second time, a
    second close after a reopen. Telling those apart needs a fact the call site
    does not pass today, such as how many moves the issue has made.

    `<firing>` is a digest of those parts, so nothing from them — an adopter's
    state names, a template file name — is written into the HTML comment where
    it could close it early. `<name>` is `stamp_id` cut down for a reader:
    lower-case letters and digits, any other run of characters one hyphen, at
    most `HOOK_STAMP_NAME_MAX` characters, and `hook` if nothing is left. The
    digest hashes `stamp_id` as given, so two hooks whose names come out alike
    still stamp differently.
    """
    moved = transition if isinstance(transition, dict) else {}
    parts = (
        stamp_id,
        event,
        subject,
        str(number),
        str(moved.get("from") or ""),
        str(moved.get("to") or ""),
    )
    digest = hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()
    firing = digest[:FIRING_DIGEST_LENGTH]
    return f"{HOOK_STAMP_OPEN}{_stamp_name(stamp_id)}:{firing}{HOOK_STAMP_CLOSE}"


def hook_comment_posted(comments: Any, stamp: str) -> bool:
    """True when `comments` already hold the comment for the firing `stamp`
    names: one whose first line is `stamp`, posted by the account `gh` posts as
    and never edited (`_lib.audit.is_own_unedited_comment`, #902).

    A comment by anyone else, or an edited one, never counts, whatever it says,
    so nobody can suppress a hook's comment by posting its stamp. Every doubt
    resolves toward posting, as for the audit writers: a comment without the
    authorship fields (the identity could not be read) counts as someone
    else's, and an unreadable comment list arrives here empty. A stamp in the
    form earlier versions wrote, `<!-- pkit-hook: <id> -->`, names no firing and
    never equals one, so a hook may post once more where such a comment is.
    """
    for comment in comments or ():
        if not is_own_unedited_comment(comment):
            continue
        first_line = normalise_comment_body(comment.get("body")).split("\n", 1)[0]
        if first_line == stamp:
            return True
    return False


# ----- dispatch + per-kind handlers --------------------------------------


def _dispatch(
    *,
    event: str,
    index: int,
    entry: dict[str, Any],
    kind: str,
    context: dict[str, Any],
    config: dict[str, Any],
    capability_root: Path,
    dry_run: bool,
) -> HookResult:
    """Route entry to its kind handler. Each handler returns a HookResult."""
    if kind == "set-board-field":
        return _hook_set_board_field(index, entry, context, config, dry_run)
    if kind == "post-comment":
        return _hook_post_comment(event, index, entry, context, config, capability_root, dry_run)
    if kind == "assign-milestone":
        return _hook_assign_milestone(index, entry, context, config, dry_run)
    if kind == "custom-script":
        return _hook_custom_script(
            event=event,
            index=index,
            entry=entry,
            context=context,
            config=config,
            capability_root=capability_root,
            dry_run=dry_run,
        )
    raise HookFailure(f"no handler registered for kind {kind!r}")


def _hook_set_board_field(
    index: int,
    entry: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any],
    dry_run: bool,
) -> HookResult:
    field_id = entry.get("field_id")
    option_id = entry.get("single_select_option_id")
    text_value = entry.get("text_value")
    if not isinstance(field_id, str) or not field_id:
        raise HookFailure("missing or empty `field_id`")
    if not (option_id or text_value):
        raise HookFailure("set-board-field requires `single_select_option_id` or `text_value`")

    item_id = _board_item_id_for_context(context)
    if item_id is None:
        return HookResult(
            index=index,
            kind="set-board-field",
            status="skipped",
            detail="no board-item id in context (issue not on board)",
        )

    project_id = _board_project_id_from_context(context, config)
    if project_id is None:
        return HookResult(
            index=index,
            kind="set-board-field",
            status="skipped",
            detail="no Projects v2 board configured for the adopter",
        )

    if dry_run:
        which = (
            f"single_select_option_id={option_id}" if option_id else f"text_value={text_value!r}"
        )
        return HookResult(
            index=index,
            kind="set-board-field",
            status="skipped",
            detail=f"would set field_id={field_id} on item_id={item_id} ({which})",
        )

    # No pre-write idempotency guard here (unlike `assign-milestone` /
    # `post-comment`): benign because of HOW THE CALLER fires this hook, not a
    # handler property — the kit's only caller is `after_create_issue`, firing
    # exactly once on a freshly-created item. A future replay or non-create
    # caller (re-firing on an item that may already carry the field value) would
    # need a value-equality guard before the write to stay idempotent.
    #
    # Construct + execute the field-value write through the sole constructor
    # (ADR-031); apply DEC-024's report-and-continue posture to its result.
    if substrate_writes is None:  # pragma: no cover - defensive import fallback
        raise HookFailure("substrate_writes primitive unavailable")
    result = substrate_writes.write_field_value(
        config,
        item_id=item_id,
        field_id=field_id,
        project_id=project_id,
        single_select_option_id=str(option_id) if option_id else None,
        text_value=str(text_value) if text_value else None,
    )
    if not result.ok:
        raise HookFailure(result.detail)
    return HookResult(
        index=index,
        kind="set-board-field",
        status="ok",
        detail=result.detail,
    )


def _hook_post_comment(
    event: str,
    index: int,
    entry: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any],
    capability_root: Path,
    dry_run: bool,
) -> HookResult:
    template_path = entry.get("template_path")
    if not isinstance(template_path, str) or not template_path:
        raise HookFailure("missing or empty `template_path`")
    template_file = capability_root / template_path
    if not template_file.is_file():
        raise HookFailure(f"template not found at {template_file}")

    stamp_id = str(entry.get("stamp_id") or template_file.stem)

    issue_number = _issue_or_pr_number(context)
    if issue_number is None:
        return HookResult(
            index=index,
            kind="post-comment",
            status="skipped",
            detail="no issue/pr number in context",
        )

    subject = "pr" if "pr" in context else "issue"
    stamp = hook_stamp(stamp_id, event, subject, issue_number, context.get("transition"))
    template_text = template_file.read_text(encoding="utf-8")
    rendered = _render_template(template_text, context)
    body = f"{stamp}\n\n{rendered}"

    if dry_run:
        return HookResult(
            index=index,
            kind="post-comment",
            status="skipped",
            detail=f"would post comment to #{issue_number} from {template_path}",
        )

    # Post once per firing: skip only when this firing's own comment is there.
    comments = _read_comments(subject, issue_number, config)
    if hook_comment_posted(comments, stamp):
        return HookResult(
            index=index,
            kind="post-comment",
            status="ok",
            detail=f"comment for this firing ({stamp}) already posted; idempotent skip",
        )

    post_args = [
        "gh",
        subject,
        "comment",
        str(issue_number),
        "--body",
        body,
    ]
    proc = _gh_call(post_args, config)
    if proc.returncode != 0:
        raise HookFailure(f"gh comment failed: {proc.stderr.strip() or 'no stderr'}")
    return HookResult(
        index=index,
        kind="post-comment",
        status="ok",
        detail=f"posted comment to #{issue_number} from {template_path}",
    )


def _hook_assign_milestone(
    index: int,
    entry: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any],
    dry_run: bool,
) -> HookResult:
    title = entry.get("title")
    if not isinstance(title, str) or not title:
        raise HookFailure("missing or empty `title`")
    issue_number = (
        context.get("issue", {}).get("number") if isinstance(context.get("issue"), dict) else None
    )
    if issue_number is None:
        return HookResult(
            index=index,
            kind="assign-milestone",
            status="skipped",
            detail="no issue number in context",
        )

    if dry_run:
        return HookResult(
            index=index,
            kind="assign-milestone",
            status="skipped",
            detail=f"would set milestone={title!r} on #{issue_number}",
        )

    # Idempotency: skip if already set.
    current = context.get("issue", {}).get("milestone")
    if isinstance(current, dict) and current.get("title") == title:
        return HookResult(
            index=index,
            kind="assign-milestone",
            status="ok",
            detail=f"milestone={title!r} already set; idempotent skip",
        )

    # Construct + execute the milestone write through the sole constructor
    # (ADR-031); apply DEC-024's report-and-continue posture to its result.
    if substrate_writes is None:  # pragma: no cover - defensive import fallback
        raise HookFailure("substrate_writes primitive unavailable")
    result = substrate_writes.write_milestone(
        config,
        issue_number=issue_number,
        title=title,
    )
    if not result.ok:
        raise HookFailure(result.detail)
    return HookResult(
        index=index,
        kind="assign-milestone",
        status="ok",
        detail=result.detail,
    )


def _hook_custom_script(
    *,
    event: str,
    index: int,
    entry: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any],
    capability_root: Path,
    dry_run: bool,
) -> HookResult:
    script_rel = entry.get("script_path")
    if not isinstance(script_rel, str) or not script_rel:
        raise HookFailure("missing or empty `script_path`")
    script_path = capability_root / script_rel
    if not script_path.is_file():
        raise HookFailure(f"script not found at {script_path}")
    if not os.access(script_path, os.X_OK):
        raise HookFailure(f"script not executable: {script_path}")

    timeout = int(entry.get("timeout_seconds", 30))

    envelope = {
        **os.environ,
        "PKIT_HOOK_EVENT": event,
        "PKIT_REPO": str(context.get("repo", "")),
        "PKIT_HOOK_REPLAY": "true" if entry.get("_replay") else "false",
        "PKIT_DRY_RUN": "true" if dry_run else "false",
    }
    issue_number = (
        context.get("issue", {}).get("number") if isinstance(context.get("issue"), dict) else None
    )
    pr_number = context.get("pr", {}).get("number") if isinstance(context.get("pr"), dict) else None
    if issue_number is not None:
        envelope["PKIT_ISSUE_NUMBER"] = str(issue_number)
    if pr_number is not None:
        envelope["PKIT_PR_NUMBER"] = str(pr_number)
    # Thread gh.host so the script's own gh calls land on the right host.
    gh_block = config.get("gh") if isinstance(config, dict) else None
    if isinstance(gh_block, dict):
        host = gh_block.get("host")
        if isinstance(host, str) and host:
            envelope["GH_HOST"] = host

    if dry_run:
        return HookResult(
            index=index,
            kind="custom-script",
            status="skipped",
            detail=f"would run {script_rel} with envelope (PKIT_HOOK_EVENT={event})",
        )

    try:
        proc = subprocess.run(
            [str(script_path)],
            env=envelope,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HookFailure(f"script timed out after {timeout}s: {script_rel}") from exc
    except (FileNotFoundError, PermissionError) as exc:
        raise HookFailure(f"script invocation failed: {exc}") from exc
    if proc.returncode != 0:
        raise HookFailure(f"script exited {proc.returncode}: {proc.stderr.strip() or 'no stderr'}")
    return HookResult(
        index=index,
        kind="custom-script",
        status="ok",
        detail=f"ran {script_rel} (exit 0)",
    )


# ----- helpers -----------------------------------------------------------


def _gh_call(args: list[str], config: dict[str, Any]) -> subprocess.CompletedProcess:
    """Call gh through the helper. Direct subprocess fallback if helper missing."""
    if gh_run is not None:
        return gh_run(args, config, check=False)
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _stamp_name(stamp_id: str) -> str:
    """`stamp_id` as a stamp shows it — see `hook_stamp`."""
    name = re.sub(r"[^a-z0-9]+", "-", stamp_id.lower()).strip("-")
    return name[:HOOK_STAMP_NAME_MAX].rstrip("-") or "hook"


def _read_comments(subject: str, number: int, config: dict[str, Any]) -> list[dict[str, Any]]:
    """The issue's or PR's comments with their authorship fields, or `[]` when
    they cannot be read — which makes the hook post, the safe direction."""
    proc = _gh_call(["gh", subject, "view", str(number), "--json", "comments"], config)
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


def _resolve_capability_root() -> Path | None:
    """Walk up from CWD looking for .pkit/capabilities/project-management/."""
    cur = Path.cwd()
    while cur != cur.parent:
        candidate = cur / ".pkit" / "capabilities" / "project-management"
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return None


def _issue_or_pr_number(context: dict[str, Any]) -> int | None:
    issue = context.get("issue")
    if isinstance(issue, dict) and isinstance(issue.get("number"), int):
        return issue["number"]
    pr = context.get("pr")
    if isinstance(pr, dict) and isinstance(pr.get("number"), int):
        return pr["number"]
    return None


def _board_item_id_for_context(context: dict[str, Any]) -> str | None:
    issue = context.get("issue")
    if isinstance(issue, dict):
        item_id = issue.get("board_item_id")
        if isinstance(item_id, str) and item_id:
            return item_id
    pr = context.get("pr")
    if isinstance(pr, dict):
        item_id = pr.get("board_item_id")
        if isinstance(item_id, str) and item_id:
            return item_id
    return None


def _board_project_id_from_context(context: dict[str, Any], config: dict[str, Any]) -> str | None:
    """Resolve the Projects v2 GraphQL node id from context or config.

    Context wins (the firing script may have already resolved it for the
    primary operation). Falls back to config's `projects_v2_node_id` if
    present.
    """
    pid = context.get("project_node_id")
    if isinstance(pid, str) and pid:
        return pid
    pid = config.get("projects_v2_node_id") if isinstance(config, dict) else None
    if isinstance(pid, str) and pid:
        return pid
    return None


def _render_template(text: str, context: dict[str, Any]) -> str:
    """Render `{{ a.b.c }}` placeholders against the context dict.

    Minimal mustache subset: dotted paths, no conditionals, no loops.
    Unresolved paths render as `<missing: a.b.c>` so the operator sees
    the gap rather than silently posting empty values.
    """

    def _lookup(path: str) -> str:
        parts = path.strip().split(".")
        cur: Any = context
        for part in parts:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return f"<missing: {path}>"
        return str(cur) if cur is not None else ""

    return re.sub(
        r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}",
        lambda m: _lookup(m.group(1)),
        text,
    )


def _report(event: str, results: list[HookResult], *, dry_run: bool) -> None:
    """Print a per-event summary to stderr. Used after fire_hooks completes."""
    if not results:
        return
    label = "(dry-run)" if dry_run else ""
    ok = sum(1 for r in results if r.status == "ok")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")
    print(
        f"  hooks {label}{event}: {ok} ok, {skipped} skipped, {failed} failed",
        file=sys.stderr,
    )
    for r in results:
        if r.status == "failed":
            print(
                f"    [failed] #{r.index} {r.kind}: {r.error or r.detail}",
                file=sys.stderr,
            )
