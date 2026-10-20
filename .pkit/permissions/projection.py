"""Realized-state projection (per COR-028 / ADR-002 / ADR-003 / #249).

The counterpart of `decide.py`: where `decide()` answers "should this request be
allowed?", `project()` answers "what native harness config does this model
*expect*?". `apply` writes that expected config; `diff` compares it to live —
both call this one function, so they can never disagree (ADR-002 same-code).

Harness-neutral and propagated like `decide.py` (ADR-003): imports neither
`src/project_kit` nor any adapter. "Neutral" here means *propagated, no
src/adapter import* — the emitted patterns are Claude-Code-shaped because the
catalog recognizers and tool names are; a second harness would render its own.

Scope (per the #249 critic pass):
  - Projects the **allow** side only. Guardrail *denies* are owned canonically by
    the adapter's core settings + the hook's catalog-derived model denies (the
    ADR-002 double-lock). Re-deriving the flag/subcommand recognizers as
    positional settings prefixes would *weaken* them, so denies are not projected.
  - Only `cmd`-only bash recognizers render to a faithful `Bash(<cmd>:*)`. A
    recognizer using `subcommand`/`flag_any`/`pattern` cannot be faithfully
    expressed as a positional settings prefix → `unprojectable`.
  - Settings are session-wide: only `subject: all` *bash* grants project to
    settings; per-agent / `operator` bash is hook-enforced (`runtime`). *Tool*
    privileges for `all`/`operator` do project to settings (session-wide tool
    allows); per-agent tool grants are `runtime` (frontmatter projection cut).
  - Scoped grants are confinement — sandbox-delegated (ADR-004), not settings →
    `unprojectable`.
  - Per-agent tool-gating is frontmatter-owned and has no consumer yet (#249
    cut it); per-agent tool grants are reported as `runtime`.
  - A path-scoped allow (the agent workspace) projects nothing: the hook
    recognizes a file tool's target, and any session-wide rule would reach
    beyond its folders → `runtime`.
"""

from __future__ import annotations

import re
from typing import Any

# Deliberately a second copy of decide.py's token regex (not an import): keeps
# project() free of decide.py's PyYAML-touching loaders. A COR-019 token-format
# change has two edit sites here and in decide.py — kept in sync intentionally.
_TOKEN = re.compile(r"^\[privilege-catalog:([a-z][a-z0-9-]*)\]$")


def _bare_ids(value: Any) -> list[str]:
    vals = value if isinstance(value, list) else [value]
    out: list[str] = []
    for v in vals:
        m = _TOKEN.match(v) if isinstance(v, str) else None
        out.append(m.group(1) if m else v)
    return out


def project(model: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    """Render a model into its expected native config + the residual buckets.

    Returns {
      "settings":      {"allow": [pattern...], "deny": []},  # session-wide native
      "runtime":       [{subject, privilege, reason}...],    # hook-enforced, not native
      "unprojectable": [{subject, privilege, reason}...],    # no native layer expresses it
    }
    `settings.deny` is always empty by design (see module docstring).
    """
    privileges = catalog.get("privileges", {})
    allow: list[str] = []
    runtime: list[dict[str, str]] = []
    unprojectable: list[dict[str, str]] = []

    def note(bucket: list, subject: str, pid: str, reason: str) -> None:
        bucket.append({"subject": subject, "privilege": pid, "reason": reason})

    for g in model.get("grants", []):
        if g.get("effect", "allow") != "allow":
            continue  # denies are canonically owned (double-lock), not projected
        subject = g.get("subject", "?")
        scoped = bool(g.get("scope"))
        for pid in _bare_ids(g.get("privilege")):
            spec = privileges.get(pid, {})
            recog = spec.get("recognize", {})
            if scoped:
                note(
                    unprojectable,
                    subject,
                    pid,
                    "scoped grant — confinement is sandbox-delegated (ADR-004), "
                    "not expressible in session-wide settings",
                )
                continue
            if recog.get("path"):
                # A path-scoped allow (the agent workspace, #1043) is keyed on
                # a file tool's target, which only the hook sees; a session-wide
                # tool allow would reach beyond its folders, so none is
                # emitted — a harness that needed an explicit rule for the
                # folder would render it here.
                note(
                    runtime,
                    subject,
                    pid,
                    "path-scoped allow — the hook recognizes a file tool's "
                    "target; a session-wide rule would reach beyond its folders",
                )
            tools = recog.get("tool", []) or []
            bash = recog.get("bash", []) or []
            if tools:
                if subject in ("all", "operator"):
                    allow.extend(tools)  # session-wide tool allow
                else:
                    note(
                        runtime,
                        subject,
                        pid,
                        "per-agent tool grant — enforced live by the hook "
                        "(type:tool); native frontmatter projection deferred (#249)",
                    )
            if bash:
                if subject != "all":
                    note(
                        runtime,
                        subject,
                        pid,
                        "per-agent/operator command rules can't be expressed "
                        "session-wide; hook-enforced (ADR-004)",
                    )
                else:
                    for rule in bash:
                        if set(rule) - {"cmd"}:  # subcommand / flag_any / pattern
                            note(
                                unprojectable,
                                subject,
                                pid,
                                "recognizer uses subcommand/flag_any/pattern — not "
                                "faithfully renderable as a positional settings prefix",
                            )
                        elif "cmd" in rule:
                            allow.append(f"Bash({rule['cmd']}:*)")

    return {
        "settings": {"allow": sorted(set(allow)), "deny": []},
        "runtime": runtime,
        "unprojectable": unprojectable,
    }


# ---- the rules of one agent run (ADR-066 point 5) ----------------------------
#
# A capability declares the rules of the agent runs its commands start in a
# file of its own (`permissions/runs.yaml`), which no session's model composes.
# The backbone's run command reads it at the pinned commit, fills in the run's
# folders and expands the backbone's own command lists, and projects it here,
# for that run alone, into the three forms a runner renders as native rules:
#
#   {"tool": T}                  the whole tool
#   {"tool": T, "folder": F}     the tool on F and everything under it
#   {"command": [tok, ...]}      a shell command whose tokens start with these
#
# The run's rules are denies (COR-028 point 1). One of them denies every call
# that none of what the run needs recognises: a privilege written with
# `except` and nothing else. The runner holds it the other way round, by
# allowing only what it leaves open, and refusing the rest without asking, so
# its `except` list becomes the run's allow list. Every other deny, the run's
# floor and the session model's denies for every agent or the run's own, is
# held in one of two ways:
#
#   - It reaches nothing the allow list allows. The allow list then holds it,
#     and each part of it a native rule can name is also written as a native
#     deny.
#   - It reaches something the allow list allows. Each part that does must be
#     written as a native deny, which takes it away from the allow list, as a
#     deny prevails over every allow. A part no native rule can name refuses
#     the run (ADR-066 point 3), since nothing would hold it.
#
# "Reaches" is judged conservatively: where the projection cannot tell that two
# recognizers never match the same call, it takes them to.

_RUN_FOLDERS = ("{working-copy}", "{workspace}")


def _first_non_flag(tokens: list[str]) -> str | None:
    """The first token that is no flag, as the session matcher reads a
    subcommand (`decide._matches_bash`)."""
    return next((t for t in tokens if not t.startswith("-")), None)


def _pattern_command(pattern: str) -> str | None:
    """The literal command a recognizer's pattern opens with, such as `rm` in
    `^rm(?=\\s)…`, or None when it names none plainly."""
    m = re.match(r"^\^([A-Za-z0-9._-]+)(?:\(\?=\\s\)|\\s|\(\\s\|\$\)|\\b|\(\?:\\s|\s)", pattern)
    return m.group(1) if m else None


def _bash_reaches(deny: dict[str, Any], allow: dict[str, Any]) -> bool:
    """Whether a deny's shell recognizer may match a call an allowed one
    (`{cmd, args?}`) matches."""
    cmd = allow["cmd"]
    args = list(allow.get("args") or [])
    if "pattern" in deny and _pattern_command(deny["pattern"]) in (None, cmd):
        return True
    if "cmd" not in deny or deny["cmd"] != cmd:
        return False
    if "args" in deny:
        theirs = list(deny["args"])
        shorter = min(len(theirs), len(args))
        return theirs[:shorter] == args[:shorter]
    if "subcommand" in deny:
        first = _first_non_flag(args)
        return first is None or first in deny["subcommand"]
    return True


def _parts(recognize: dict[str, Any]) -> list[tuple[str, Any]]:
    """A recognizer's parts, each one call shape: ("tool", T), ("folder", (T,
    F)) or ("bash", rule)."""
    parts: list[tuple[str, Any]] = [("tool", t) for t in recognize.get("tool", []) or []]
    path = recognize.get("path") or {}
    for tool in path.get("tools", []) or []:
        for folder in path.get("folders", []) or []:
            parts.append(("folder", (tool, folder)))
    parts += [("bash", rule) for rule in recognize.get("bash", []) or []]
    return parts


def _reaches(part: tuple[str, Any], allowed: list[tuple[str, Any]]) -> bool:
    """Whether a deny's part may match a call one of the allowed parts matches."""
    kind, value = part
    for akind, avalue in allowed:
        if kind == "bash" and akind == "bash":
            if _bash_reaches(value, avalue):
                return True
        elif kind != "bash" and akind != "bash":
            tool = value if kind == "tool" else value[0]
            atool = avalue if akind == "tool" else avalue[0]
            if tool == atool:
                return True
    return False


def _native(part: tuple[str, Any]) -> dict[str, Any] | None:
    """The part as a native rule's form, or None where no such form names it."""
    kind, value = part
    if kind == "tool":
        return {"tool": value}
    if kind == "folder":
        return {"tool": value[0], "folder": value[1]}
    if set(value) - {"cmd", "args"}:
        return None  # a subcommand, a flag or a pattern: no prefix names it
    return {"command": [value["cmd"], *(value.get("args") or [])]}


#: A privilege token as a run's rules write it: the id may carry the scope of
#: the capability whose file defines it (`<capability>:<id>`, ADR-021).
_RUN_TOKEN = re.compile(r"^\[privilege-catalog:([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\]$")


def _ids(value: Any) -> list[str]:
    """The bare ids a rule's privilege names; a value that is no token names none."""
    values = value if isinstance(value, list) else [value]
    ids: list[str] = []
    for item in values:
        m = _RUN_TOKEN.match(item) if isinstance(item, str) else None
        if m:
            ids.append(m.group(1))
    return ids


def project_run(
    privileges: dict[str, Any],
    rules: list[dict[str, Any]],
    model_denies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project one run's rules into the native rule forms a runner renders.

    `privileges` maps each privilege id the rules and denies name — the run's
    file's, scoped `<capability>:<id>`, and the session catalog's — to its
    entry, with the run's folders already filled in and the backbone's command
    lists (`kit`) already expanded. `rules` are the run's own (subject `all`,
    effect `deny`); `model_denies` the session model's denies that bind on the
    run's agent. Returns `{"allow": [...], "deny": [...], "held": [{privilege,
    how}], "refused": str | None}`: on a refusal, the run must not start.
    """
    out: dict[str, Any] = {"allow": [], "deny": [], "held": [], "refused": None}

    def refuse(reason: str) -> dict[str, Any]:
        out["refused"] = reason
        return out

    def spec(pid: str) -> dict[str, Any] | None:
        entry = privileges.get(pid)
        return entry.get("recognize") if isinstance(entry, dict) else None

    # The one deny of everything the run does not need.
    complements = []
    for rule in rules:
        for pid in _ids(rule.get("privilege")):
            recognize = spec(pid)
            if recognize is not None and set(recognize) == {"except"}:
                complements.append((pid, recognize))
    if len(complements) != 1:
        return refuse(
            "a run's rules hold "
            + ("no" if not complements else "more than one")
            + " deny of every call none of what the run needs recognises, so no allow "
            "list can hold them"
        )
    first, recognize = complements[0]
    allowed_ids = _ids(recognize["except"])
    allowed: list[tuple[str, Any]] = []
    for pid in allowed_ids:
        allowed_spec = spec(pid)
        if allowed_spec is None:
            return refuse(f"the run needs {pid}, which no privilege defines")
        unknown = set(allowed_spec) - {"tool", "path", "bash"}
        if unknown:
            return refuse(
                f"the run needs {pid}, whose {', '.join(sorted(unknown))} a native allow "
                "rule cannot name"
            )
        for part in _parts(allowed_spec):
            native = _native(part)
            if native is None:
                return refuse(
                    f"the run needs {pid}, which a native allow rule cannot name: "
                    "a subcommand, a flag or a pattern"
                )
            if part[0] == "folder" and part[1][1] in _RUN_FOLDERS:
                return refuse(f"the run's folder {part[1][1]} was not filled in for {pid}")
            if native not in out["allow"]:
                out["allow"].append(native)
            allowed.append(part)
    out["held"].append({"privilege": first, "how": "allow list"})

    denies = [(rule, "run") for rule in rules] + [(grant, "model") for grant in model_denies]
    for grant, origin in denies:
        for pid in _ids(grant.get("privilege")):
            if pid == first:
                continue
            recognize = spec(pid)
            if recognize is None:
                continue  # names no privilege: it recognises nothing
            excepted = set(_ids(recognize.get("except") or []))
            open_parts = [
                part
                for part, owner in zip(allowed, _owners(allowed_ids, privileges), strict=True)
                if owner not in excepted
            ]
            base = {k: v for k, v in recognize.items() if k != "except"}
            if not base:
                if open_parts:
                    return refuse(
                        f"the {origin} deny of {pid} takes away what the run needs, and no "
                        "native rule can name every call but a few"
                    )
                out["held"].append({"privilege": pid, "how": "allow list"})
                continue
            if set(base) - {"tool", "path", "bash"}:
                return refuse(f"the {origin} deny of {pid} is in a form the run cannot hold")
            scoped = bool(grant.get("scope"))
            how = "allow list"
            for part in _parts(base):
                reaching = _reaches(part, open_parts)
                native = _native(part)
                if reaching and (excepted or scoped or native is None):
                    return refuse(
                        f"the {origin} deny of {pid} reaches what the run needs, and no "
                        "native rule can hold it there"
                    )
                if native is not None and not (excepted and _reaches(part, allowed)):
                    if native not in out["deny"]:
                        out["deny"].append(native)
                    how = "native deny" if reaching else "allow list and native deny"
            out["held"].append({"privilege": pid, "how": how})
    return out


def _owners(allowed_ids: list[str], privileges: dict[str, Any]) -> list[str]:
    """The privilege each allowed part comes from, in `project_run`'s order."""
    owners: list[str] = []
    for pid in allowed_ids:
        entry = privileges.get(pid) or {}
        owners += [pid] * len(_parts(entry.get("recognize") or {}))
    return owners
