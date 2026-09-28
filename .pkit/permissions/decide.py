"""Permission decision core (per COR-028 / ADR-003).

Harness-neutral, propagated, standalone module — imported by BOTH the
claude-code PreToolUse hook (which runs in the adopter tree at decision
time, where the global `pkit` is not importable) AND the `pkit permissions`
CLI. ADR-002's same-code invariant requires they decide identically, so the
logic lives here once and both call it.

Dependency direction (ADR-003): CLI and hook import this; this imports neither
`src/project_kit` nor any adapter. Recognizers arrive as catalog *data*
(privilege-catalog.yaml), never as adapter code.

Pure logic operates on plain dicts (a loaded grant model + privilege catalog);
the loaders are thin helpers. No third-party deps beyond PyYAML for the loaders
(the pure `decide()` path needs none).
"""
from __future__ import annotations

import fnmatch
import os
import re
from typing import Any

# A grant's privilege value is the COR-019 token `[privilege-catalog:<id>]`
# (or a list of them); strip to the bare id for matching against the catalog.
# The id half admits an OPTIONAL capability scope (`<cap>:<name>`) so a
# capability-contributed privilege (ADR-021) is referenced as
# `[privilege-catalog:trip-planning:ad-hoc-scraping]`. This is the COR-019
# token-grammar *clarification*: the namespace stays `privilege-catalog`; the
# id half gains permitted internal structure. The capture group keeps the WHOLE
# id half (including any embedded `:`), so the token round-trips to the catalog
# key exactly — a mis-resolved scoped token would empty the grant's privilege
# match and the deny would silently not bind (a fail-open hazard).
_TOKEN = re.compile(r"^\[privilege-catalog:([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\]$")
_SEP = re.compile(r"\s*(?:&&|\|\||\||;)\s*")
_ENVVAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# The leading-`cd` strip (ADR-025 Phase 1). A bare `cd <path>` prefix changes
# only the cwd — which the intent layer never confines — so stripping it reveals
# the already-granted intent of the remainder; it grants nothing new. We strip
# ONLY a bare `cd <single-path-arg>`: no quotes, no `$()`, no backtick, no
# redirection, no flags. Anything more complex is NOT stripped (falls through to
# existing behaviour). `_CD_SEP` matches the FIRST `&&` / `;` separator (the only
# separators that sequence a directory change before a granted command — a bare
# `cd src | gh …` makes no shell sense, so `|` / `||` are deliberately excluded).
_CD_SEP = re.compile(r"\s*(?:&&|;)\s*")
# Constructs the dumb splitter cannot be trusted on (ADR-004 dp-4 / ADR-025
# decision 2): a quote, command substitution `$(`, a backtick, or a `<` / `>`
# redirection. Their presence in the remainder of a cd-stripped compound makes
# the decision ABSTAIN — never auto-allow — because a per-segment matcher is
# structurally blind to what these compose into.
#
# `|` is DELIBERATELY EXCLUDED from this set (it does not force an abstain).
# Pipe-composition porosity (e.g. `gh … | sh`) is inherited UNCHANGED from the
# existing bare-command path: `segments()` already splits on `|` and the
# decision matches on the granted first segment, so `gh … | sh` decides the
# same with or without a leading `cd`. The cd-strip neither creates nor worsens
# it — `cd /x && gh … | sh` resolves to exactly the bare `gh … | sh` verdict.
# Adding `|` here would (a) re-introduce prompts on legitimate pipes like
# `gh … | jq` and (b) only HALF-fix pipe-to-shell — the bare form `gh … | sh`
# would stay porous — an inconsistent asymmetry for no real gain. The honest
# boundary for `| sh` is the OS sandbox (ADR-004: this layer is a speed-bump,
# not a boundary). Pipe handling is out of scope for ADR-025 Phase 1.
_UNTRUSTED = re.compile(r"""['"`<>]|\$\(""")
# A bare `cd <path>` first segment: literally `cd` then exactly one path token
# with no shell metacharacter and not a flag. The token is intentionally
# restrictive — the moment it carries anything the splitter can't trust, we do
# not strip.
_BARE_CD = re.compile(r"""^cd\s+([^\s'"`$<>|&;()]+)$""")


# ---- command segmentation + recognizer matcher ----------------------------

def segments(command: str) -> list[list[str]]:
    """Split a compound command into segments, each tokenized, with env-var
    prefixes (and a leading `export`) stripped. Fixes the `export X=1 && gh …`
    false-prompt that the flat settings matcher couldn't catch."""
    out: list[list[str]] = []
    for raw in _SEP.split(command.strip()):
        toks = raw.split()
        while toks and (toks[0] == "export" or _ENVVAR.match(toks[0])):
            toks = toks[1:]
        if toks:
            out.append(toks)
    return out


def _strip_leading_cd(command: str) -> str | None:
    """If `command` is a compound whose FIRST segment is a bare `cd <path>`
    followed by `&&` / `;`, return the remainder (everything after that first
    separator). Otherwise return None — meaning "do not strip; fall through to
    existing behaviour" (ADR-025 Phase 1).

    Mirrors the leading-`export` / `VAR=` strip in `segments()` in spirit, but
    operates on the raw command string (the cwd-change has no privilege of its
    own to recognise) and is deliberately conservative: it strips ONLY a bare
    `cd` with a single path arg carrying no shell metacharacter. A `cd` with a
    quote, `$()`, backtick, redirection, a flag, or more than one arg is NOT a
    bare `cd`, so we return None and let the unchanged path decide — never a
    silent strip of something the dumb splitter can't trust.
    """
    parts = _CD_SEP.split(command.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    first, remainder = parts
    if not _BARE_CD.match(first.strip()):
        return None
    remainder = remainder.strip()
    return remainder or None


def _matches_bash(rule: dict[str, Any], toks: list[str]) -> bool:
    if "pattern" in rule:
        if re.search(rule["pattern"], " ".join(toks)):
            return True
        if "cmd" not in rule:
            return False
    if "cmd" in rule:
        if not toks or toks[0] != rule["cmd"]:
            return False
        if "subcommand" in rule:
            rest = [t for t in toks[1:] if not t.startswith("-")]
            if not rest or rest[0] not in rule["subcommand"]:
                return False
        if "flag_any" in rule:
            if not any(f in toks for f in rule["flag_any"]):
                return False
        return True
    return False


def recognized_privileges(catalog: dict[str, Any], request: dict[str, Any]) -> set[str]:
    """Which privilege ids does this request match?"""
    privileges = catalog.get("privileges", {})
    hits: set[str] = set()
    if request.get("type") == "tool":
        tool = request.get("tool")
        for name, spec in privileges.items():
            if tool in spec.get("recognize", {}).get("tool", []):
                hits.add(name)
    elif request.get("type") == "bash":
        segs = segments(request.get("command", ""))
        for name, spec in privileges.items():
            for rule in spec.get("recognize", {}).get("bash", []):
                if any(_matches_bash(rule, toks) for toks in segs):
                    hits.add(name)
                    break
    return hits


# ---- path-confined privileges: the agent workspace (#1043) ------------------
#
# A privilege whose recognizer carries `path` is confined to folders, each
# relative to the root of a checkout of the project: the project root, or a
# linked worktree of the same repository (a subagent working in a worktree has
# its workspace at that worktree's root). It is recognized only for a request
# whose TARGET lies inside one of those folders — never merely for the tool or
# command used — so a grant of it can neither reach nor deny a file elsewhere:
#
#   - a file tool listed in `path.tools`, by the path its payload names;
#   - a shell command whose only effect is a file inside: a text emitter (`cat`
#     reading a here-document or stdin, `echo`, `printf`) whose every output
#     redirect lands inside, or `rm` whose every operand does.
#
# `recognized_privileges` reads only `tool` / `bash`, and so do the settings
# projection and rule attribution; none of them can mistake a path-confined
# privilege for a session-wide tool allow.

# The only commands whose output, redirected into a folder, is all they do.
_EMITTERS = frozenset({"cat", "echo", "printf"})
# One here-document operator: `<<` or `<<-`, then a delimiter, quoted or not.
_HEREDOC = re.compile(r"""<<(-?)[ \t]*(?:'(\w+)'|"(\w+)"|(\w+))""")
# An output redirect (`>`, `>>`, `>|`, optionally fd-numbered) and its target.
_OUT_REDIRECT = re.compile(r"\d*(?:>>|>\||>)[ \t]*(\S*)")
# What the shell-write reading refuses anywhere on the command line: anything
# that could run a second command, join commands, or feed one from elsewhere.
_WRITE_REFUSED = re.compile(r"[`|&;<\n]|\$\(")
# A redirect target, and an `rm` operand (which may glob inside the folder).
_TARGET = re.compile(r"^[A-Za-z0-9._/@%+=:,-]+$")
_OPERAND = re.compile(r"^[A-Za-z0-9._/@%+=:,*?-]+$")


def _heredoc_is_literal(match: re.Match[str], after: list[str]) -> bool:
    """The here-document ends at its delimiter on the command's last line, and
    its body cannot run anything: the delimiter is quoted, or the body holds no
    command substitution."""
    delimiter = match.group(2) or match.group(3) or match.group(4)
    quoted = match.group(4) is None
    strip_tabs = match.group(1) == "-"
    for index, text in enumerate(after):
        if (text.lstrip("\t") if strip_tabs else text) == delimiter:
            body, trailing = after[:index], after[index + 1:]
            break
    else:
        return False
    if any(text.strip() for text in trailing):
        return False
    return quoted or not any("$(" in text or "`" in text for text in body)


def _rm_operands(words: list[str]) -> list[str]:
    """The operands of `rm <words>`: every word after `--`, and before it every
    word that is not an option."""
    operands: list[str] = []
    options_done = False
    for word in words:
        if not options_done and word == "--":
            options_done = True
        elif options_done or not word.startswith("-") or word == "-":
            operands.append(word)
    return operands


def _plain_operand(operand: str) -> bool:
    """A plain `rm` operand that may glob in its last component only: a glob
    earlier in the path expands before any `..` after it is applied, so it could
    pass through a symlinked entry and out of the folder."""
    head = operand.rpartition("/")[0]
    return bool(_OPERAND.match(operand)) and not any(ch in head for ch in "*?")


def _shell_write(command: str) -> tuple[str, list[str]] | None:
    """Read `command` as a shell command whose only effect is writing or deleting
    files: `(command_line, targets)`, or None for anything else.

    Two shapes and nothing more: a text emitter (`cat` with no operand, `echo`,
    `printf`) with one or more output redirects, optionally fed one literal
    here-document; or `rm` with its operands. `command_line` is the command
    without the here-document's body (data for the emitter, never run);
    `targets` are the redirect targets or the `rm` operands as written. Refused
    outright: a pipe, `;`, `&`, a `<` other than the one here-document, a
    backtick, `$(`, a second line outside that here-document, and a target that
    is not a plain path.
    """
    lines = command.strip().split("\n")
    line = lines[0]
    heredoc = _HEREDOC.search(line)
    if heredoc is not None:
        if line.count("<<") != 1 or not _heredoc_is_literal(heredoc, lines[1:]):
            return None
        line = line[: heredoc.start()] + line[heredoc.end():]
    elif len(lines) > 1:
        return None
    if _WRITE_REFUSED.search(line):
        return None
    targets = [m.group(1) for m in _OUT_REDIRECT.finditer(line)]
    words = _OUT_REDIRECT.sub(" ", line).split()
    if targets:
        if not all(_TARGET.match(t) for t in targets):
            return None
        if words and (words[0] not in _EMITTERS or (words[0] == "cat" and len(words) > 1)):
            return None
        return line.strip(), targets
    if heredoc is None and words and words[0] == "rm":
        operands = _rm_operands(words[1:])
        if operands and all(_plain_operand(o) for o in operands):
            return line.strip(), operands
    return None


def _enclosing_checkout(start: str) -> str | None:
    """The nearest directory at or above `start` holding a `.git` entry."""
    current = start
    while True:
        if os.path.lexists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _common_git_dir(checkout: str) -> str | None:
    """The git directory every worktree of `checkout`'s repository shares: its
    `.git` directory, or — for a linked worktree, whose `.git` is a `gitdir:`
    pointer — the directory that pointer's `commondir` names."""
    marker = os.path.join(checkout, ".git")
    if os.path.isdir(marker):
        return os.path.realpath(marker)
    try:
        with open(marker, encoding="utf-8") as fh:
            pointer = fh.read().strip()
    except OSError:
        return None
    if not pointer.startswith("gitdir:"):
        return None
    gitdir = os.path.realpath(os.path.join(checkout, pointer[len("gitdir:"):].strip()))
    try:
        with open(os.path.join(gitdir, "commondir"), encoding="utf-8") as fh:
            return os.path.realpath(os.path.join(gitdir, fh.read().strip()))
    except OSError:
        return gitdir


def _checkouts(path: str, root: str) -> list[str]:
    """The checkouts whose folders `path` may lie in: the project root, and the
    linked worktree of the same repository that holds `path`, if any."""
    project = os.path.realpath(root)
    found = [project]
    holder = _enclosing_checkout(os.path.dirname(path))
    if holder is not None and holder != project:
        common = _common_git_dir(holder)
        if common is not None and common == _common_git_dir(project):
            found.append(holder)
    return found


def _inside(target: str, request: dict[str, Any], folders: list[str]) -> bool:
    """Does `target` — absolute, or relative to the directory the request acts
    in — resolve strictly inside one of `folders` of a checkout of the project?
    False when the project root is unknown or the directory is unresolvable (a
    `cd -` prefix)."""
    root = request.get("root")
    if not root or not folders:
        return False
    base = request["target_cwd"] if "target_cwd" in request else (request.get("cwd") or root)
    if base is None:
        return False
    path = os.path.realpath(os.path.join(base, target))
    for checkout in _checkouts(path, root):
        for folder in folders:
            top = os.path.realpath(os.path.join(checkout, folder))
            if path != top and os.path.commonpath([path, top]) == top:
                return True
    return False


def _confined_privileges(
    catalog: dict[str, Any], request: dict[str, Any]
) -> tuple[set[str], str | None]:
    """The path-confined privileges `request` is recognized as, and — for a shell
    write into their folders — the command line the other recognizers read in
    place of the full command (a here-document's body is data, never run)."""
    confined = {
        pid: spec["recognize"]["path"]
        for pid, spec in catalog.get("privileges", {}).items()
        if isinstance(spec.get("recognize", {}).get("path"), dict)
    }
    if not confined:
        return set(), None
    if request.get("type") == "tool":
        target = request.get("path")
        if not isinstance(target, str) or not target:
            return set(), None
        hits = {
            pid for pid, spec in confined.items()
            if request.get("tool") in (spec.get("tools") or [])
            and _inside(target, request, spec.get("folders") or [])
        }
        return hits, None
    if request.get("type") == "bash":
        write = _shell_write(request.get("command", ""))
        if write is None:
            return set(), None
        line, targets = write
        hits = {
            pid for pid, spec in confined.items()
            if all(_inside(t, request, spec.get("folders") or []) for t in targets)
        }
        return hits, (line if hits else None)
    return set(), None


def _cd_directory(request: dict[str, Any]) -> str | None:
    """The directory a bare leading `cd <path>` moves to, resolved against the
    directory the request acts in; None for `cd -`, whose target is unknowable."""
    first = _CD_SEP.split(request.get("command", "").strip(), maxsplit=1)[0]
    match = _BARE_CD.match(first.strip())
    if match is None or match.group(1) == "-":
        return None
    base = request["target_cwd"] if "target_cwd" in request else (request.get("cwd") or request.get("root"))
    if not base:
        return None
    return os.path.normpath(os.path.join(base, os.path.expanduser(match.group(1))))


def _only_confined_writes_untrusted(catalog: dict[str, Any], request: dict[str, Any]) -> bool:
    """In a cd-stripped remainder that carries an untrusted construct, is every
    such construct a write into a path-confined folder?

    True for a shell write the confined recognizer accepts — its reading refuses
    anything that could run a second command, so a quote left in an emitter's
    arguments is text — and for a command whose output redirects all land in
    such a folder and which, with them set aside, carries nothing untrusted.
    Nothing else about the untrusted-construct rule changes."""
    if _confined_privileges(catalog, request)[0]:
        return True
    command = request.get("command", "")
    if "\n" in command:
        return False
    targets = [m.group(1) for m in _OUT_REDIRECT.finditer(command)]
    if not targets:
        return False
    folders = [
        folder
        for spec in catalog.get("privileges", {}).values()
        if isinstance(spec.get("recognize", {}).get("path"), dict)
        for folder in spec["recognize"]["path"].get("folders") or []
    ]
    if not all(_TARGET.match(t) and _inside(t, request, folders) for t in targets):
        return False
    return not _UNTRUSTED.search(_OUT_REDIRECT.sub(" ", command))


# ---- subjects, scope, decision ---------------------------------------------

def _privilege_ids(value: Any) -> set[str]:
    """Normalise a grant's `privilege` (token or list of tokens) to bare ids."""
    vals = value if isinstance(value, list) else [value]
    out: set[str] = set()
    for v in vals:
        m = _TOKEN.match(v) if isinstance(v, str) else None
        out.add(m.group(1) if m else v)
    return out


def _extract_host(url: str) -> str:
    """Extract the hostname from a URL string.  Returns an empty string if the
    URL cannot be parsed (no scheme, malformed, etc.) — a host that can never
    match a well-formed glob, so the grant is denied rather than silently passed.

    stdlib-only: uses urllib.parse which ships with every Python ≥ 3.6 and is
    safe inside macOS Seatbelt (ADR-014).
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.hostname or ""
    except Exception:
        return ""


def _scope_ok(
    scope: list[str] | None,
    cwd: str,
    *,
    scope_type: str | None = None,
    url: str | None = None,
) -> tuple[bool, str | None]:
    """Check whether a grant's scope constraint is satisfied.

    Returns (ok, rejection_reason_or_None).

    For ``directory``-scoped privileges (default for absent ``scope_type``):
      the grant's scope globs are matched against ``cwd`` via fnmatch.

    For ``domain``-scoped privileges (``scope_type="domain"``):
      positive allow-list semantics — the grant's scope globs are matched
      against the hostname extracted from ``url``.  Only matching hosts are
      allowed; non-matching hosts are blocked.

      Deny/negation scopes (any glob starting with ``!``) are explicitly
      unsupported and rejected with a clear reason rather than silently
      accepted.  Rationale: a tool-layer denylist is a false boundary — an
      agent's raw ``bash curl`` bypasses it at the agent-blind sandbox layer
      (ADR-004 §61).  Only positive allow-lists are honest at this layer.

    When ``scope`` is absent or empty the grant is unconstrained (anywhere).
    """
    if not scope:
        return True, None

    # Deny/negation scopes are explicitly unsupported for domain privileges.
    # Check upfront so the error message is clear regardless of scope_type.
    negation_globs = [pat for pat in scope if pat.startswith("!")]
    if negation_globs:
        return False, (
            f"deny/negation scopes are unsupported for domain-scoped privileges "
            f"({negation_globs!r}): a tool-layer denylist is a false boundary "
            f"(ADR-004 §61); use positive allow-list globs only"
        )

    if scope_type == "domain":
        host = _extract_host(url or "")
        if not host:
            return False, (
                f"domain-scope check failed: could not extract a hostname from "
                f"request URL {url!r}"
            )
        matched = any(fnmatch.fnmatch(host, pat) for pat in scope)
        if matched:
            return True, None
        return False, (
            f"domain-scope: host {host!r} does not match any allowed glob in "
            f"{scope!r}"
        )

    # directory scope (default)
    matched = any(
        fnmatch.fnmatch(cwd, pat) or fnmatch.fnmatch(cwd, pat.rstrip("*") + "*")
        for pat in scope
    )
    return matched, None


def _effective_grants(model: dict[str, Any], subject: str) -> list[dict[str, Any]]:
    keep = {"all", subject}
    return [g for g in model.get("grants", []) if g.get("subject") in keep]


def decide(
    model: dict[str, Any],
    catalog: dict[str, Any],
    request: dict[str, Any],
    posture: str | None = None,
) -> tuple[str, str]:
    """Decide a request: returns (decision, reason), decision in
    {allow, deny, abstain}. `abstain` defers to the harness's normal flow
    (lenient); strict maps an unmodeled request to deny.

    `request` = {type: "bash"|"tool", command|tool, cwd, subject[, url][, path]
    [, root]}. The optional `url` field carries the request URL for
    ``domain``-scoped privilege checks (web-fetch); `path` (a file tool's
    target) and `root` (the project root) feed the path-confined privileges
    (the agent workspace), which are recognized only for a target inside their
    folders. Effective grants = baseline (`all`) ∪ the subject's own grants;
    deny wins; a scoped allow denies the privilege outside its scope.

    Scope semantics by privilege ``scope_type`` (from the catalog):
      - ``directory`` (default): grant scope globs are matched against ``cwd``.
      - ``domain``: grant scope globs are matched against the URL hostname
        (positive allow-list; deny/negation globs are explicitly rejected).
    """
    posture = posture or model.get("posture", "lenient")
    subject = request["subject"]

    # Leading-`cd` strip (ADR-025 Phase 1). When a bash command's first segment
    # is a bare `cd <path> &&` / `cd <path> ;`, drop it and decide on the
    # remainder against the unchanged grant model — `cd src && gh pr list`
    # auto-approves exactly as `gh pr list` would. Conservative on two axes:
    #   - it strips ONLY a bare `cd` (`_strip_leading_cd` returns None otherwise,
    #     so a tricky `cd "/x; rm -rf ~" && …` falls through to the full-command
    #     path, where it is decided whole and at worst abstains — never silently
    #     allowed); and
    #   - if the remainder carries anything the dumb splitter can't be trusted on
    #     (a quote, `$()`, a backtick, a `<` / `>` redirection), it ABSTAINS
    #     rather than auto-allowing (ADR-004 dp-4, fail-closed-on-uncertainty) —
    #     unless every such construct is a write into a path-confined folder,
    #     the agent workspace (#1043): a redirect or here-document into it is
    #     not an untrusted construct, and nothing else about the rule changes.
    # The remainder is decided at the ORIGINAL cwd: stripping `cd` can never
    # grant a directory-scoped privilege the un-stripped command lacked. Only a
    # write target's relative path resolves against the `cd` directory — where
    # the shell will actually write it.
    if request.get("type") == "bash":
        remainder = _strip_leading_cd(request.get("command", ""))
        if remainder is not None:
            inner = {**request, "command": remainder, "target_cwd": _cd_directory(request)}
            if _UNTRUSTED.search(remainder) and not _only_confined_writes_untrusted(catalog, inner):
                return "abstain", (
                    "leading-cd strip: remainder carries an untrusted construct "
                    "(quote / $() / backtick / redirection) — fail closed"
                )
            return decide(model, catalog, inner, posture)

    # A request inside a path-confined privilege's folders is that privilege's;
    # a shell write there is read by the other recognizers without its
    # here-document body, which is data for the emitter and never run.
    confined, command_line = _confined_privileges(catalog, request)
    recognized = request if command_line is None else {**request, "command": command_line}
    hits = recognized_privileges(catalog, recognized) | confined
    privileges_catalog = catalog.get("privileges", {})
    matched_allow = False
    for g in _effective_grants(model, subject):
        privs = _privilege_ids(g.get("privilege"))
        overlap = hits & privs
        if not overlap:
            continue
        if g.get("effect", "allow") == "deny":
            return "deny", f"deny grant for {subject} on {sorted(overlap)}"
        # Determine scope_type from the catalog for the overlapping privileges.
        # When the overlap spans multiple privileges, use the most restrictive
        # scope_type: prefer "domain" > "directory" > None.  In practice a
        # single grant rarely covers privileges of mixed scope_type.
        scope_type: str | None = None
        for pid in overlap:
            pspec = privileges_catalog.get(pid, {})
            st = pspec.get("scope_type")
            if st == "domain":
                scope_type = "domain"
                break
            if st == "directory":
                scope_type = "directory"
        ok, reason = _scope_ok(
            g.get("scope"),
            request.get("cwd", ""),
            scope_type=scope_type,
            url=request.get("url"),
        )
        if ok:
            matched_allow = True
        else:
            deny_msg = reason or (
                f"{sorted(overlap)} allowed for {subject} only in "
                f"{g.get('scope')}, not {request.get('cwd')!r}"
            )
            return "deny", deny_msg
    if matched_allow:
        return "allow", f"allow grant for {subject} on {sorted(hits)}"
    if posture == "strict":
        return "deny", "strict posture: nothing grants this request"
    return "abstain", "lenient posture: defer to the harness's normal flow"


def _read_default_agent(project_root: str) -> str | None:
    """Read the configured default agent from .claude/settings.json.

    Returns the value of the top-level ``agent`` key if present and non-empty,
    otherwise ``None``.  Uses stdlib ``json`` only (the hook runs bare python3 —
    no third-party deps).  Any I/O or parse error silently returns ``None`` so
    the caller falls back to ``operator`` — never throw from subject resolution.
    """
    import json as _json
    import os.path as _osp

    path = _osp.join(project_root, ".claude", "settings.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = _json.load(fh)
        agent = data.get("agent")
        return str(agent) if agent and isinstance(agent, str) else None
    except Exception:
        return None


def hook_decide(
    model: dict[str, Any],
    catalog: dict[str, Any],
    payload: dict[str, Any],
    project_root: str | None = None,
) -> tuple[str, str]:
    """Decision-core entry point for a PreToolUse hook payload. Fails OPEN —
    any fault yields abstain (defer), never a silent block; non-negotiable
    denies are double-locked in the fail-closed native settings (ADR-002).

    Subject resolution (per issue #57):
      - ``agent_type`` present in payload → ``agent:<agent_type>`` (unchanged)
      - ``agent_type`` absent + ``project_root`` set + ``.claude/settings.json``
        has ``agent: X`` → ``agent:X`` (main session runs as the configured agent)
      - ``agent_type`` absent + no configured default → ``operator``

    Pass ``project_root`` (the adopter tree root) from the hook entry-point so
    main-session calls resolve to the configured agent, and so a path-confined
    privilege (the agent workspace) can locate its folders.  The CLI
    synthesizes payloads with explicit ``agent_type`` and does not need to pass
    a root; without one, no path-confined privilege is recognized.
    """
    try:
        agent_type = payload.get("agent_type")
        if agent_type:
            subject = f"agent:{agent_type}"
        elif project_root:
            default_agent = _read_default_agent(project_root)
            subject = f"agent:{default_agent}" if default_agent else "operator"
        else:
            subject = "operator"
        return decide(model, catalog, _payload_request(payload, subject, project_root))
    except Exception as exc:  # fail-open
        return "abstain", f"hook fault → fail-open: {exc!r}"


def _payload_request(
    payload: dict[str, Any], subject: str, project_root: str | None
) -> dict[str, Any]:
    """The decision request a PreToolUse payload describes."""
    tool = payload["tool_name"]
    if tool == "Bash":
        return {
            "type": "bash",
            "command": payload["tool_input"]["command"],
            "cwd": payload.get("cwd", ""),
            "subject": subject,
            "root": project_root,
        }
    tool_input = payload.get("tool_input", {})
    return {
        "type": "tool",
        "tool": tool,
        "cwd": payload.get("cwd", ""),
        "subject": subject,
        # Surface the URL for domain-scoped privilege checks (web-fetch).
        # WebFetch and WebSearch both supply `url` in tool_input; absent
        # for all other tools.  A missing key becomes None, which _scope_ok
        # treats as an unparseable host → deny for domain-scoped grants.
        "url": tool_input.get("url"),
        # A file tool's target, for the path-confined privileges (the agent
        # workspace): Read / Write / Edit name `file_path`, NotebookEdit
        # `notebook_path`.
        "path": tool_input.get("file_path") or tool_input.get("notebook_path"),
        "root": project_root,
    }


def targets_confined_path(
    catalog: dict[str, Any], payload: dict[str, Any], project_root: str | None
) -> bool:
    """Does a path-confined privilege — the agent workspace — recognize this
    PreToolUse payload, a bare leading `cd` aside?

    The diagnostic loop's defect test (#1043): the workspace is granted to
    every agent, so a prompt for a request it recognizes is a defect, not an
    allowlist gap. Never raises; any fault reads as False."""
    try:
        request = _payload_request(payload, "operator", project_root)
        while request.get("type") == "bash":
            remainder = _strip_leading_cd(request.get("command", ""))
            if remainder is None:
                break
            request = {**request, "command": remainder, "target_cwd": _cd_directory(request)}
        return bool(_confined_privileges(catalog, request)[0])
    except Exception:
        return False


# ---- thin loaders ----------------------------------------------------------

# ---- stdlib YAML-subset fallback -------------------------------------------
# Used by load_yaml() when ruamel.yaml is not importable (e.g. inside macOS
# Seatbelt where uv cannot run — ADR-014). Handles the subset the shipped files
# use: block mappings, block sequences, single-quoted and double-quoted scalars,
# flow sequences ([a, b, c]), block scalars (>-), booleans, integers, null,
# and # comments. No anchors, aliases, merge-keys, flow mappings, multi-doc,
# or custom tags — none appear in the shipped files.
#
# Invariant (ADR-002/ADR-003 same-code): the fallback parses the shipped files
# IDENTICALLY to ruamel.yaml safe-load. Covered by the conformance fixture
# tests/test_permission_decide.py::test_stdlib_fallback_parses_identically_to_ruamel.

def _stdlib_load_yaml(text: str) -> Any:
    """Minimal YAML-subset parser (stdlib-only, no third-party deps)."""
    import re as _re

    # ---- tokeniser helpers -------------------------------------------------

    def _parse_scalar(raw: str) -> Any:
        """Decode a YAML scalar string (already stripped) to a Python value."""
        s = raw.strip()
        if not s or s in ("~", "null", "Null", "NULL"):
            return None
        if s in ("true", "True", "TRUE"):
            return True
        if s in ("false", "False", "FALSE"):
            return False
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    def _unquote_single(s: str) -> str:
        """Strip surrounding single-quotes; handle '' → ' escape."""
        assert s.startswith("'") and s.endswith("'")
        return s[1:-1].replace("''", "'")

    def _unquote_double(s: str) -> str:
        """Strip surrounding double-quotes; handle \\n, \\t, \\\\ escapes."""
        assert s.startswith('"') and s.endswith('"')
        inner = s[1:-1]
        return inner.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")

    def _parse_value_token(token: str) -> Any:
        """Parse a single value token (scalar or simple unquoted string)."""
        t = token.strip()
        if t.startswith("'") and t.endswith("'") and len(t) >= 2:
            return _unquote_single(t)
        if t.startswith('"') and t.endswith('"') and len(t) >= 2:
            return _unquote_double(t)
        return _parse_scalar(t)

    def _split_flow_sequence(body: str) -> list:
        """Parse the interior of a flow sequence [...] into a Python list.
        Handles single- and double-quoted strings as atomic tokens."""
        items: list = []
        current = ""
        in_single = False
        in_double = False
        for ch in body:
            if ch == "'" and not in_double:
                in_single = not in_single
                current += ch
            elif ch == '"' and not in_single:
                in_double = not in_double
                current += ch
            elif ch == "," and not in_single and not in_double:
                s = current.strip()
                if s:
                    items.append(_parse_value_token(s))
                current = ""
            else:
                current += ch
        s = current.strip()
        if s:
            items.append(_parse_value_token(s))
        return items

    # ---- block-scalar collector (>- folded-strip, | literal-strip) ---------

    def _collect_block_scalar(lines: list, start_idx: int, indent: int) -> tuple[str, int]:
        """Collect lines for a block scalar starting at start_idx.
        Returns (scalar_value, next_line_index)."""
        # Determine the content indentation from the first non-empty content line.
        content_indent: int | None = None
        parts: list[str] = []
        i = start_idx
        while i < len(lines):
            raw = lines[i]
            stripped = raw.rstrip()
            if not stripped:
                parts.append("")
                i += 1
                continue
            col = len(stripped) - len(stripped.lstrip())
            if content_indent is None:
                content_indent = col
            if col < (content_indent if content_indent is not None else indent + 1):
                break
            parts.append(stripped[content_indent:] if content_indent else stripped)
            i += 1
        # Folded (>-): join non-empty runs with space, remove trailing newlines.
        result = " ".join(p for p in parts if p).rstrip()
        return result, i

    # ---- line preprocessor -------------------------------------------------

    def _strip_comment(line: str) -> str:
        """Remove inline # comments that are outside quotes."""
        out = ""
        in_single = False
        in_double = False
        for ch in line:
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                break
            out += ch
        return out.rstrip()

    # ---- recursive block parser --------------------------------------------

    def _parse_block(lines: list, idx: int, base_indent: int) -> tuple[Any, int]:
        """Parse a block node (mapping or sequence) at the given base_indent.
        Returns (value, next_idx)."""
        if idx >= len(lines):
            return None, idx

        result_map: dict | None = None
        result_seq: list | None = None
        i = idx

        while i < len(lines):
            raw = lines[i]
            stripped_raw = raw.rstrip()
            if not stripped_raw or stripped_raw.lstrip().startswith("#"):
                i += 1
                continue

            line = _strip_comment(stripped_raw)
            if not line.strip():
                i += 1
                continue

            col = len(line) - len(line.lstrip())

            # Back up to parent block
            if col < base_indent:
                break

            # New sibling at a HIGHER-than-expected indent inside parent — skip
            # (shouldn't happen in valid YAML, but be defensive).
            if col > base_indent and result_map is None and result_seq is None:
                # We're establishing the indent from the first entry.
                base_indent = col

            content = line.lstrip()

            # ---- sequence entry: starts with "- " --------------------------
            if content.startswith("- "):
                if result_map is not None:
                    break  # type switch — back to parent
                if result_seq is None:
                    result_seq = []
                value_part = content[2:].strip()
                if value_part:
                    # Inline value after "- "
                    if value_part.startswith("{"):
                        # Inline flow mapping — not needed for shipped files; skip.
                        result_seq.append(_parse_value_token(value_part))
                        i += 1
                    elif value_part.startswith("["):
                        body = value_part[1:value_part.rfind("]")]
                        result_seq.append(_split_flow_sequence(body))
                        i += 1
                    elif value_part.startswith("'") or value_part.startswith('"'):
                        result_seq.append(_parse_value_token(value_part))
                        i += 1
                    elif ":" in value_part:
                        # Inline mapping key: value on same line as "- "
                        child_lines = []
                        # first key:value is on this line
                        child_indent = col + 2
                        child_lines.append(" " * child_indent + value_part)
                        j = i + 1
                        while j < len(lines):
                            r2 = lines[j].rstrip()
                            if not r2 or r2.lstrip().startswith("#"):
                                j += 1
                                continue
                            c2 = len(r2) - len(r2.lstrip())
                            if c2 <= col:
                                break
                            child_lines.append(r2)
                            j += 1
                        child_val, _ = _parse_block(child_lines, 0, child_indent)
                        result_seq.append(child_val)
                        i = j
                    else:
                        result_seq.append(_parse_scalar(value_part))
                        i += 1
                else:
                    # "- " alone — nested block
                    child_indent = col + 2
                    child_val, i = _parse_block(lines, i + 1, child_indent)
                    result_seq.append(child_val)
                continue

            # ---- bare "- " (dash alone on line) ----------------------------
            if content.strip() == "-":
                if result_seq is None:
                    result_seq = []
                result_seq.append(None)
                i += 1
                continue

            # ---- mapping key: value ----------------------------------------
            colon_pos = -1
            in_s = False
            in_d = False
            for ci, ch in enumerate(content):
                if ch == "'" and not in_d:
                    in_s = not in_s
                elif ch == '"' and not in_s:
                    in_d = not in_d
                elif ch == ":" and not in_s and not in_d:
                    colon_pos = ci
                    break

            if colon_pos == -1:
                # Plain scalar continuation — treat as bare value
                i += 1
                continue

            key_raw = content[:colon_pos].strip()
            key = _parse_value_token(key_raw) if key_raw else None
            val_raw = content[colon_pos + 1:].strip()

            if result_seq is not None:
                break  # type switch
            if result_map is None:
                result_map = {}

            if not val_raw:
                # Value on subsequent lines
                i += 1
                # Peek at next non-blank, non-comment line
                j = i
                while j < len(lines):
                    r2 = lines[j].rstrip()
                    if not r2 or r2.lstrip().startswith("#"):
                        j += 1
                        continue
                    break
                if j >= len(lines):
                    result_map[key] = None
                    i = j
                    continue
                r2 = lines[j]
                c2 = len(r2) - len(r2.lstrip())
                # A block sequence is a valid mapping value at the SAME indent
                # level as the key — the "- " indicator provides the structural
                # indent for the sequence entries' content.  Without this check
                # the grants.yaml shape (key at col 0, "- " entries at col 0)
                # parses to None, silently dropping all adopter grants and
                # causing the zero-dep hook to fail open (issue #55).
                _r2_content = r2.lstrip()
                _same_level_seq = (
                    c2 == col
                    and (_r2_content.startswith("- ") or _r2_content == "-")
                )
                if c2 > col or _same_level_seq:
                    # Child block (deeper indent, OR same-indent block sequence)
                    child_val, i = _parse_block(lines, j, c2)
                    result_map[key] = child_val
                else:
                    result_map[key] = None
                continue
            else:
                # Inline value
                v = val_raw
                if v.startswith(">-") or v.startswith("|"):
                    # Block scalar
                    scalar_val, i = _collect_block_scalar(lines, i + 1, col + 1)
                    result_map[key] = scalar_val
                elif v.startswith("["):
                    close = v.rfind("]")
                    if close != -1:
                        body = v[1:close]
                        result_map[key] = _split_flow_sequence(body)
                    else:
                        result_map[key] = v
                    i += 1
                elif v.startswith("'") or v.startswith('"'):
                    result_map[key] = _parse_value_token(v)
                    i += 1
                else:
                    result_map[key] = _parse_scalar(v)
                    i += 1
                continue

        if result_map is not None:
            return result_map, i
        if result_seq is not None:
            return result_seq, i
        return None, i

    # ---- entry point -------------------------------------------------------
    lines = text.splitlines()
    # Strip document-start marker
    clean: list[str] = []
    for ln in lines:
        s = ln.rstrip()
        if s.lstrip() in ("---", "..."):
            continue
        clean.append(ln)
    result, _ = _parse_block(clean, 0, 0)
    return result if result is not None else {}


def load_yaml(path: str) -> dict[str, Any]:
    """Load a YAML file, returning a dict. Uses ruamel.yaml when available
    (the kit-wide library); falls back to the stdlib-only subset parser
    when ruamel.yaml is not importable (e.g. inside macOS Seatbelt, ADR-014).

    The stdlib fallback is in this SHARED loader — not duplicated in the hook
    — so the hook and the `pkit permissions` CLI reach identical parse results
    through the same code path (ADR-002/ADR-003 same-code invariant).
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        from ruamel.yaml import YAML as _YAML
        _yaml = _YAML(typ="safe")
        import io as _io
        result = _yaml.load(_io.StringIO(text))
    except ImportError:
        result = _stdlib_load_yaml(text)
    # Coerce a non-dict document (bare scalar, top-level list, empty/None) to {}
    # on BOTH parse paths. A hand-corrupted sidecar that parses to a scalar or
    # list must not make a downstream `.get()` raise under one parser (ruamel,
    # CLI) while degrading to {} under the other (stdlib, sandboxed hook) — the
    # same-code invariant (ADR-002/ADR-003) requires identical results.
    return result if isinstance(result, dict) else {}


def _exists(path: str) -> bool:
    import os.path

    return os.path.isfile(path)


def _capability_fragment_catalog(
    target_root: str, backbone_ids: set[str]
) -> tuple[dict[str, Any], list[str]]:
    """Privilege definitions contributed by installed capabilities (ADR-021).

    Walks the manifest ``components:`` list (the same install-state-as-gate the
    grants walk uses — NOT a glob of ``.pkit/capabilities/``) and for each
    component of kind ``capability`` reads its catalog fragment at
    ``.pkit/capabilities/<name>/permissions/privilege-catalog.yaml`` if present.
    An uninstalled or orphan capability directory contributes nothing.

    Returns ``(merged_privileges, rejections)``: a map of accepted scoped
    privilege ids → spec (each stamped ``provenance: capability:<name>`` for the
    reporting surface), and a list of human-readable rejection reasons.

    Three merge constraints (ADR-021), enforced here *before* the catalog
    reaches ``guardrail_denies`` or ``decide``:

    - **Capability-scoped ids.** A fragment id is rewritten to ``<cap>:<name>``
      regardless of how the fragment authored it, so attribution is intrinsic
      and a fragment can only ever introduce ids in its own namespace.
    - **Collision-rejecting.** A scoped id colliding with a backbone privilege
      or another capability's already-merged id is rejected (the colliding
      entry is dropped, not overwritten) — a fragment can never shadow or strip
      an existing definition.
    - **Guardrail-forbidding.** A fragment privilege carrying ``guardrail:
      true`` is rejected (dropped), so a capability can never install a deny
      that applies to every adopter by default.

    A rejected entry contributes NOTHING to the merged catalog rather than
    aborting the load: the backbone catalog stays intact, and the capability's
    own deny grant then references a privilege that does not exist (matching no
    request) — fail-CLOSED on the fragment's vocabulary, never a false allow.

    Stdlib-safe (ADR-002 / ADR-003 same-code invariant): reads through the
    existing ``load_yaml`` / ``_stdlib_load_yaml`` fallback and the existing
    manifest read; no third-party dependency, no ``src/project_kit`` import.
    """
    import os.path

    manifest_path = os.path.join(target_root, ".pkit", "manifest.yaml")
    if not _exists(manifest_path):
        return {}, []
    manifest = load_yaml(manifest_path)
    merged: dict[str, Any] = {}
    rejections: list[str] = []
    for component in manifest.get("components", []) or []:
        if not isinstance(component, dict):
            continue
        if component.get("kind") != "capability":
            continue
        name = component.get("name")
        if not name:
            continue
        frag_path = os.path.join(
            target_root, ".pkit", "capabilities", name,
            "permissions", "privilege-catalog.yaml",
        )
        if not _exists(frag_path):
            continue
        doc = load_yaml(frag_path)
        for raw_id, spec in (doc.get("privileges", {}) or {}).items():
            if not isinstance(spec, dict):
                continue
            scoped_id = f"{name}:{raw_id}"
            if spec.get("guardrail"):
                rejections.append(
                    f"{scoped_id}: a capability fragment may not define a "
                    f"guardrail (rejected)"
                )
                continue
            if scoped_id in backbone_ids or scoped_id in merged:
                rejections.append(
                    f"{scoped_id}: id collides with an existing privilege "
                    f"(rejected)"
                )
                continue
            entry = dict(spec)
            entry["provenance"] = f"capability:{name}"
            merged[scoped_id] = entry
    return merged, rejections


def load_catalog(target_root: str) -> dict[str, Any]:
    """Load the privilege catalog, merging installed capabilities' fragments.

    The merge lives HERE (not in ``load_model``) because both the PreToolUse
    hook and the ``pkit permissions`` CLI call ``load_catalog`` directly to
    learn which commands are recognised, and ``guardrail_denies`` runs on
    whatever this returns — so both readers get the identical merged catalog
    and the guardrail check gates the result before any deny is derived
    (ADR-021 decision 1; ADR-002 same-code invariant).

    The backbone catalog (``.pkit/schemas/privilege-catalog.yaml``) is the base;
    installed capabilities' fragments are merged in additively under the
    collision-rejecting, guardrail-forbidding rule of
    ``_capability_fragment_catalog``.
    """
    import os.path

    path = os.path.join(target_root, ".pkit", "schemas", "privilege-catalog.yaml")
    catalog = load_yaml(path) if _exists(path) else {}
    privileges = catalog.setdefault("privileges", {}) if isinstance(catalog, dict) else {}
    if not isinstance(privileges, dict):
        return catalog
    fragments, rejections = _capability_fragment_catalog(target_root, set(privileges))
    privileges.update(fragments)
    if rejections:
        # Surface rejected fragments on the catalog so the reporting layer can
        # show them; never silent (ADR-021 decision 6 — visibility).
        catalog["_fragment_rejections"] = rejections
    return catalog


def guardrail_denies(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Synthesize baseline `{subject: all, effect: deny}` grants for every
    privilege the catalog flags `guardrail: true`. The catalog is the single
    source of truth for the guardrail deny set (ADR-002's double-lock): these
    are the fail-open hook half; the harness ships matching fail-closed native
    denies. Returns one deny grant per guardrail privilege, sorted by id."""
    out: list[dict[str, Any]] = []
    for pid in sorted(catalog.get("privileges", {})):
        if catalog["privileges"][pid].get("guardrail"):
            out.append(
                {"subject": "all", "privilege": f"[privilege-catalog:{pid}]", "effect": "deny"}
            )
    return out


def active_profile(target_root: str, config: dict[str, Any]) -> Any:
    """Resolve the active permission profile name for a target tree (ADR-032).

    `active_profile` is per-machine state (an operator's autonomy choice), so it
    lives in a gitignored per-machine sidecar (`active-profile.yaml`, declared
    `runtime_ignore`), NOT in the tracked `config.yaml`. This is the SINGLE
    resolution point — the source of truth both the hook and the CLI read
    through (ADR-002/ADR-003 same-code invariant), so each operator's hook layers
    their own profile while the shared `config.yaml` policy stays committed.

    Resolution order: the sidecar's `active_profile` key, then a `config.yaml`
    fallback. The fallback is PERMANENT (issue #304): an adopter installed before
    ADR-032 — or mid-migration before the next `setup autonomy` relocation —
    still has `active_profile` in `config.yaml`, and reading it there keeps
    enforcement unchanged for them. The fallback is the simplest safe rule (read
    sidecar, else config) and costs nothing once the value is relocated, so it
    stays rather than being a removable migration crutch.

    Stdlib-safe (same-code invariant): reads through the shared `load_yaml` /
    `_stdlib_load_yaml` fallback; no third-party dependency, no
    `src/project_kit` import — decide.py runs as bare python in-sandbox."""
    import os.path

    sidecar = os.path.join(
        target_root, ".pkit", "permissions", "project", "active-profile.yaml"
    )
    if _exists(sidecar):
        name = load_yaml(sidecar).get("active_profile")
        if name:
            return name
    return config.get("active_profile")


def _active_profile_grants(target_root: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Grants contributed by the active permission profile (per ADR-005), if any.

    The profile is a LAYER, never an owner: its grants sit between the guardrail
    denies and the adopter's own grants.yaml, and the adopter's grants are
    unioned last so a manual `grant`/`revoke` is never overwritten by a profile.
    Resolves the active profile name via `active_profile` (the per-machine
    sidecar, with `config.yaml` fallback — ADR-032), then the profile file
    project-first (`project/profiles/<name>.yaml`) then shipped
    (`profiles/<name>.yaml`).

    Each grant dict is annotated with a ``_profile`` key naming the source
    profile (mirroring ``_capability_fragment_grants``' ``_capability``
    annotation). This is ADR-046's routing key: `apply` uses it to route
    profile-only realizer output to the per-machine settings file. The
    annotation rides along in the model unstripped — ``decide()`` reads only
    ``subject``/``privilege``/``effect``/``scope`` and ignores extra keys."""
    import os.path

    name = active_profile(target_root, config)
    if not name:
        return []
    for base in (
        os.path.join(target_root, ".pkit", "permissions", "project", "profiles"),
        os.path.join(target_root, ".pkit", "permissions", "profiles"),
    ):
        path = os.path.join(base, f"{name}.yaml")
        if _exists(path):
            out: list[dict[str, Any]] = []
            for grant in load_yaml(path).get("grants", []) or []:
                if isinstance(grant, dict):
                    annotated = dict(grant)
                    annotated["_profile"] = name
                    out.append(annotated)
                else:
                    out.append(grant)
            return out
    return []


def _capability_fragment_grants(target_root: str) -> list[dict[str, Any]]:
    """Grants contributed by installed capabilities (ADR-016).

    Walks the manifest ``components:`` list (NOT a glob of ``.pkit/capabilities/``)
    and for each component of kind ``capability`` reads its grants fragment at
    ``.pkit/capabilities/<name>/permissions/grants.yaml`` if present. An
    uninstalled or orphan capability directory contributes nothing — only
    manifest-registered components count.

    Each grant dict is annotated with a ``_capability`` key naming the source
    capability; ``load_model`` carries this through for the reporting layer
    (``pkit permissions overview`` / ``explain``). The annotation is never
    stripped — it rides along in the model, and ``decide()`` simply ignores
    keys it does not read (it reads only ``subject``, ``privilege``,
    ``effect``, and ``scope``). The profile layer's ``_profile`` annotation
    (ADR-046 routing key) works the same way.

    Stdlib-safe (ADR-002 / ADR-003 same-code invariant): reads files through
    the existing ``load_yaml`` / ``_stdlib_load_yaml`` fallback; no third-party
    dependency, no ``src/project_kit`` import.
    """
    import os.path

    manifest_path = os.path.join(target_root, ".pkit", "manifest.yaml")
    if not _exists(manifest_path):
        return []
    manifest = load_yaml(manifest_path)
    out: list[dict[str, Any]] = []
    for component in manifest.get("components", []) or []:
        if not isinstance(component, dict):
            continue
        if component.get("kind") != "capability":
            continue
        name = component.get("name")
        if not name:
            continue
        frag_path = os.path.join(
            target_root, ".pkit", "capabilities", name, "permissions", "grants.yaml"
        )
        if not _exists(frag_path):
            continue
        doc = load_yaml(frag_path)
        for grant in doc.get("grants", []) or []:
            if isinstance(grant, dict):
                annotated = dict(grant)
                annotated["_capability"] = name
                out.append(annotated)
    return out


def load_model(target_root: str, catalog: dict[str, Any]) -> dict[str, Any]:
    """Build the effective permission model for a target tree: the catalog-
    derived guardrail denies, then installed-capability fragments, then the
    active profile's grant-layer, then the adopter's authored grants — unioned
    in that order — plus posture/ownership_mode from project config.

    This is the SINGLE model loader (ADR-002's same-code invariant): the
    PreToolUse hook and the `pkit permissions` CLI both call it, so they decide
    and display from byte-identical models. Order is guardrails → capability
    fragments → profile → adopter (adopter last so manual grants are never
    clobbered, per ADR-005); `decide()` is deny-wins and order-independent
    regardless. Capability-fragment grants are annotated with ``_capability``
    for the reporting layer (ADR-016) and profile-layer grants with ``_profile``
    (ADR-046's realizer routing key); ``decide()`` ignores the extra keys.
    """
    import os.path

    perm_dir = os.path.join(target_root, ".pkit", "permissions", "project")
    grants_path = os.path.join(perm_dir, "grants.yaml")
    config_path = os.path.join(perm_dir, "config.yaml")
    grants_doc = load_yaml(grants_path) if _exists(grants_path) else {}
    config = load_yaml(config_path) if _exists(config_path) else {}
    return {
        "posture": config.get("posture", "lenient"),
        "ownership_mode": config.get("ownership_mode", "additive"),
        # `active_profile` is a decision-model input (it layers the profile's
        # grants below), and per ADR-032 it lives in the per-machine sidecar with
        # a `config.yaml` fallback — resolved through the single `active_profile`
        # helper so the hook and the CLI read the same per-machine source. This is
        # an ADDITIVE source-edit: `decide()`'s verdict path is byte-identical.
        "active_profile": active_profile(target_root, config),
        "grants": (
            guardrail_denies(catalog)
            + _capability_fragment_grants(target_root)
            + _active_profile_grants(target_root, config)
            + list(grants_doc.get("grants", []) or [])
        ),
    }
