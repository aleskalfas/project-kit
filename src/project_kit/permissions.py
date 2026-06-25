"""`pkit permissions` CLI — observability + model mutation over the permission model.

A thin orchestrator (per ADR-003): it loads the model + catalog (through the
propagated decision core's single `load_model`, preserving ADR-002's same-code
invariant), parses live harness state, and renders. `explain` / `diff` /
`catalog` are read-only; `grant` / `revoke` / `mode` mutate the model;
`enable` / `disable` toggle live enforcement by registering/stripping the
PreToolUse hook. The realizer's projection-based `apply` is a later batch.

`diff` here is attribution-based (it maps live settings rules back to catalog
privileges to flag unjustified grants). The *projection*-based diff — computing
expected settings from the model via the propagated decision core
(`.pkit/permissions/decide.py`), preserving ADR-002's same-code invariant —
lands with the realizer (`apply`), which produces that projection.

`probe` (#276) is the same-code-invariant VERIFIER — the conformance-fixture
role ADR-003 names: it drives the hook's actual entry point (`hook_decide`)
over curated concrete requests against the current model and checks each
verdict against an independent restatement of the declared contract.
"""
from __future__ import annotations

import fnmatch
import importlib.util
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML

from project_kit import cli_render

if TYPE_CHECKING:
    from packaging.version import Version

_yaml = YAML(typ="safe")


# ---- loaders ---------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return _yaml.load(fh) or {}


def _load_catalog(target_root: Path) -> dict[str, Any]:
    # Single catalog loader (same-code invariant): delegate to the decision
    # core so the CLI *displays* exactly the catalog the hook *decides* on.
    # When capability-fragment merging lands, it lands once — here — for both
    # readers, rather than diverging a CLI-only reader from the hook's.
    return _decide_mod(target_root).load_catalog(str(target_root))


def _decide_mod(target_root: Path):
    """Import the target tree's propagated decision core (`.pkit/permissions/
    decide.py`). The CLI builds its model through the *same* loader the
    PreToolUse hook uses, preserving ADR-002's same-code invariant — there is
    exactly one `load_model`, and it lives in `decide.py`."""
    path = target_root / ".pkit" / "permissions" / "decide.py"
    if not path.is_file():
        raise PermissionsError(f"decision core not found at {path}.")
    spec = importlib.util.spec_from_file_location("pkit_perm_decide", path)
    if spec is None or spec.loader is None:
        raise PermissionsError(f"decision core could not be loaded from {path}.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _projection_mod(target_root: Path):
    """Import the target tree's propagated realized-state projector
    (`.pkit/permissions/projection.py`). The same-code counterpart of
    `_decide_mod`: `diff` (here) and `apply` (later) render expected config
    through the *same* `project()` (ADR-002 same-code; #249)."""
    path = target_root / ".pkit" / "permissions" / "projection.py"
    if not path.is_file():
        raise PermissionsError(f"projection core not found at {path}.")
    spec = importlib.util.spec_from_file_location("pkit_perm_projection", path)
    if spec is None or spec.loader is None:
        raise PermissionsError(f"projection core could not be loaded from {path}.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_model(target_root: Path) -> dict[str, Any]:
    catalog = _load_catalog(target_root)
    return _decide_mod(target_root).load_model(str(target_root), catalog)


# ---- shared helpers --------------------------------------------------------

# Admits the optional capability scope in the id half (`<cap>:<name>`) so a
# capability-contributed privilege (ADR-021) round-trips here exactly as it
# does in the decision core's `_TOKEN`. Backbone single-segment ids still match.
_BARE = re.compile(r"^\[privilege-catalog:([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\]$")
# A simple settings allow/deny pattern like `Bash(gh:*)` or `Bash(git push --force:*)`.
_BASH_RULE = re.compile(r"^Bash\((.+?)(?::\*)?\)$")
_TOOL_RULE = re.compile(r"^([A-Z][A-Za-z]+)$")


def _bare(token: str) -> str:
    m = _BARE.match(token)
    return m.group(1) if m else token


def _subjects(model: dict) -> list[str]:
    seen: list[str] = []
    for g in model["grants"]:
        if g["subject"] not in seen:
            seen.append(g["subject"])
    return seen


def _attribute_rule(rule: str, catalog: dict) -> str | None:
    """Map a live settings.json permission pattern back to a catalog privilege
    id, if one recognizes it. Best-effort over the simple `Bash(<cmd>...)` /
    `<Tool>` shapes; returns None when nothing in the catalog claims it."""
    privileges = catalog.get("privileges", {})
    m = _BASH_RULE.match(rule)
    if m:
        head = m.group(1).split()[0]
        for pid, spec in privileges.items():
            for r in spec.get("recognize", {}).get("bash", []):
                if r.get("cmd") == head:
                    return pid
        return None
    if _TOOL_RULE.match(rule):
        for pid, spec in privileges.items():
            if rule in spec.get("recognize", {}).get("tool", []):
                return pid
    return None


def _live_settings(target_root: Path) -> dict[str, list[str]]:
    path = target_root / ".claude" / "settings.json"
    if not path.is_file():
        return {"allow": [], "deny": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"allow": [], "deny": []}
    perms = data.get("permissions", {})
    return {"allow": perms.get("allow", []), "deny": perms.get("deny", [])}


# ---- explain ---------------------------------------------------------------

def _subject_gloss(subject: str) -> str:
    if subject == "all":
        return "every agent and the operator"
    if subject == "operator":
        return "the human / main session"
    if subject.startswith("agent:"):
        return f"the {subject.split(':', 1)[1]} subagent"
    return ""


_EXPLAIN_LEGEND = [
    "Legend",
    "  allow / deny   the subject may / may not use the privilege",
    "  guardrail      denied for everyone, always — can't be granted around",
    "  posture        lenient = uncovered requests defer to Claude Code · strict = denied",
    "  ownership      additive = only adds to settings.json · managed = owns the permissions region",
    "  subjects       all = every agent + operator · operator = the human · agent:<name> = one subagent",
]
_EXPLAIN_COMMANDS = [
    "Commands",
    "  pkit permissions grant <subj> <priv> [--scope G] [--deny]   add a grant",
    "  pkit permissions revoke <subj> <priv>                       remove a grant",
    "  pkit permissions overview                                   privilege vocabulary + live status",
]


def explain(target_root: Path, agent: str | None) -> str:
    catalog = _load_catalog(target_root)
    guardrail_ids = {p for p, s in catalog.get("privileges", {}).items() if s.get("guardrail")}
    model = _load_model(target_root)
    posture = model.get("posture", "lenient")
    ownership = model.get("ownership_mode", "additive")

    def is_guardrail_grant(g: dict) -> bool:
        return g.get("effect") == "deny" and all(
            pid in guardrail_ids for pid in _grant_priv_ids(g.get("privilege"))
        )

    title = (
        cli_render.style("title", "Permission policy — who may (allow) or may not (deny) each privilege")
        + "   (vocabulary: `pkit permissions overview`)"
    )
    banner = f"  posture: {posture} · ownership: {ownership}"

    subjects = _subjects(model)
    if agent:
        want = agent if agent in ("all", "operator") else f"agent:{agent}"
        if want not in subjects:
            note = f"no grants declared for {want!r}."
            if want != "all":
                note += "  It still inherits the `all` guardrails — run `pkit permissions explain`."
            return "\n".join([title, "", banner, "", note]) + "\n"
        subjects = [want]

    shown = [g for subj in subjects for g in model["grants"] if g["subject"] == subj]
    name_w = max((len(", ".join(_grant_priv_ids(g.get("privilege")))) for g in shown), default=0)

    lines = [title, "", banner]
    for subj in subjects:
        lines.append("\n" + cli_render.style("heading", f"{subj}  ({_subject_gloss(subj)})"))
        for g in (x for x in model["grants"] if x["subject"] == subj):
            names = ", ".join(_grant_priv_ids(g.get("privilege")))
            eff = g.get("effect", "allow")
            mark = "  guardrail" if is_guardrail_grant(g) else ""
            scope = f"  scope: {', '.join(g['scope'])}" if g.get("scope") else ""
            cap = g.get("_capability")
            cap_note = f"  (contributed by capability: {cap})" if cap else ""
            lines.append(f"  {eff:5} {names:{name_w}}{mark}{scope}{cap_note}")

    if not any(not is_guardrail_grant(g) for g in model["grants"]):
        lines.append(
            "\n  (no capability granted to any agent yet — agents fall through to the posture above)"
        )

    lines += ["", cli_render.style("heading", _EXPLAIN_LEGEND[0]), *_EXPLAIN_LEGEND[1:],
              "", cli_render.style("heading", _EXPLAIN_COMMANDS[0]), *_EXPLAIN_COMMANDS[1:]]
    return "\n".join(lines) + "\n"


# ---- catalog ---------------------------------------------------------------

def catalog(target_root: Path) -> str:
    cat = _load_catalog(target_root)
    privileges = cat.get("privileges", {})
    if not privileges:
        return "privilege catalog is empty.\n"
    lines = [cli_render.style("title", f"{len(privileges)} privilege(s):")]
    for pid in sorted(privileges):
        spec = privileges[pid]
        scope = f"  [scope: {spec['scope_type']}]" if spec.get("scope_type") else ""
        lines.append(f"  {pid:22} {spec.get('description', '')}{scope}")
    return "\n".join(lines) + "\n"


# ---- overview --------------------------------------------------------------

def _grant_priv_ids(value: Any) -> list[str]:
    vals = value if isinstance(value, list) else [value]
    return [_bare(v) for v in vals]


def _provenance(spec: dict) -> str:
    """Where a privilege came from. Today every entry is the backbone baseline;
    when capability-fragment merging lands, the merge will stamp a `provenance`
    field (`capability:<name>`) the loader sets — this reads it forward-compatibly."""
    return spec.get("provenance", "backbone")


def overview(target_root: Path) -> str:
    """A role-grouped overview of the catalog: which privileges are guardrails
    (denied for everyone — the 'don't do bad things' floor) vs enablers (inert
    until granted — the 'let an agent work' set), each with its provenance and
    who it's granted to. The vocabulary view; `explain` is the policy view."""
    catalog = _load_catalog(target_root)
    privileges = catalog.get("privileges", {})
    if not privileges:
        return "privilege catalog is empty.\n"
    model = _load_model(target_root)

    # privilege id -> {allow: [subjects], deny: [subjects]}
    grants: dict[str, dict[str, list[str]]] = {}
    for g in model.get("grants", []):
        eff = g.get("effect", "allow")
        for pid in _grant_priv_ids(g.get("privilege")):
            grants.setdefault(pid, {"allow": [], "deny": []}).setdefault(eff, []).append(
                g.get("subject", "?")
            )

    # Capability-contributed denies (ADR-016 narrowing-but-reported): collect all
    # grants whose source is a capability fragment (annotated with _capability).
    cap_deny_grants: list[dict] = [
        g for g in model.get("grants", [])
        if g.get("_capability") and g.get("effect") == "deny"
    ]

    guardrails = sorted(p for p, s in privileges.items() if s.get("guardrail"))
    enablers = sorted(p for p, s in privileges.items() if not s.get("guardrail"))

    def _scope(spec: dict) -> str:
        return f"[{spec['scope_type']}-scope]" if spec.get("scope_type") else ""

    # Compute column widths across ALL rows so the two sections align together.
    id_w = max((len(p) for p in privileges), default=0)
    desc_w = max((len(s.get("description", "")) for s in privileges.values()), default=0)
    scope_w = max((len(_scope(s)) for s in privileges.values()), default=0)
    prov_w = max((len(_provenance(s)) for s in privileges.values()), default=0)

    def _row(pid: str, note: str) -> str:
        spec = privileges[pid]
        cols = [f"{pid:{id_w}}", f"{spec.get('description',''):{desc_w}}"]
        if scope_w:
            cols.append(f"{_scope(spec):{scope_w}}")
        cols.append(f"{_provenance(spec):{prov_w}}")
        cols.append(note)
        return "  " + "  ".join(cols)

    # Enforcement banner — the strong "is the hook live?" indication.
    # Also runs the enforcement-runtime self-check when enforcement is ON, so
    # `overview` surfaces a dead hook loudly (ADR-002 amendment).
    on = _enforcement_on(target_root)
    posture = model.get("posture", "lenient")
    ownership = model.get("ownership_mode", "additive")
    unmodeled = "denied" if posture == "strict" else "deferred to Claude Code"
    runtime_fault: str | None = None
    if on:
        rt_ok, rt_detail = _hook_runtime_check(target_root)
        if rt_ok:
            status = "ON — the PreToolUse hook checks every agent tool call against the model below"
        else:
            status = (
                "ON (registered) but ENFORCEMENT-RUNTIME FAULT — hook CANNOT START; "
                "enforcement currently fail-open on every call"
            )
            runtime_fault = rt_detail
    else:
        status = "OFF — declared but not enforced live; run `pkit permissions enable`"
    sb = _sandbox_block(target_root)
    confinement_probe: str | None = None
    if sb.get("enabled") is True:
        sandbox_line = "  sandbox ON — scripting runs prompt-free inside the OS box"
        if sb.get("failIfUnavailable") is not True:
            sandbox_line += "  ⚠ fail-open — run `pkit permissions sandbox enable` to restore fail-closed"
        else:
            sandbox_line += " (fail-closed)"
        # Actual-confinement write probe: verify the box is actually confining.
        probe_result = _confinement_write_probe()
        if probe_result == "denied":
            sandbox_line += " · confinement verified (write outside workspace DENIED)"
        elif probe_result == "allowed":
            sandbox_line += (
                "\n  ⚠ WARNING: sandbox configured ON but NOT actually confining — "
                "out-of-workspace write SUCCEEDED. Session may be running outside the "
                "box (restart needed) or the sandbox cannot initialize. "
                "Run `pkit permissions sandbox enable` to re-check."
            )
            confinement_probe = "allowed"
    else:
        sandbox_line = (
            "  sandbox OFF — scripting prompts; "
            "`pkit permissions sandbox enable` for prompt-free scripting in the OS box"
        )

    lines: list[str] = [
        cli_render.style("title", f"Permission catalog — {len(privileges)} privilege(s)")
        + "   (the vocabulary; who-may-do-what is `pkit permissions explain`)",
        "",
        cli_render.style("strong", f"Live enforcement: {status}"),
    ]
    if runtime_fault:
        lines += [
            f"  ⚠ enforcement-runtime fault: {runtime_fault}",
            "  The hook is registered but cannot start. Fix: verify python3 is available,",
            "  .pkit/permissions/decide.py exists, and .pkit/schemas/privilege-catalog.yaml",
            "  is present. Re-run `pkit permissions enable` after fixing.",
        ]
    lines += [
        f"  posture {posture} (unmodeled requests {unmodeled}) · "
        f"ownership {ownership} (how much of settings.json the realizer owns)",
        sandbox_line,
    ]
    # Mandatory egress reporting (ADR-015 narrowing-but-reported): surface every
    # applied allow-host host with source + the verbatim honesty gloss, always,
    # in permissions overview.
    egress_lines = _egress_report_lines(target_root)
    if egress_lines:
        lines.extend(egress_lines)
    # Rejected capability-catalog fragments (ADR-021 decision 6 — visibility):
    # never let a fragment fail to merge silently. The loader stamps rejection
    # reasons on the catalog; surface them loudly so an operator sees a
    # capability whose privilege did NOT enter the catalog (and why).
    rejections = catalog.get("_fragment_rejections") or []
    if rejections:
        lines += [
            "",
            cli_render.style("heading", "REJECTED CAPABILITY FRAGMENTS — a fragment privilege did NOT merge (ADR-021)"),
        ]
        for reason in rejections:
            lines.append(f"  ⚠ {reason}")
    lines += [
        "",
        cli_render.style("heading", "GUARDRAILS — always denied for every agent; the safety floor you cannot grant around"),
    ]
    for pid in guardrails:
        lines.append(_row(pid, "denied for all · double-locked"))
    if not guardrails:
        lines.append("  (none)")

    lines += [
        "",
        cli_render.style("heading", "ENABLERS — a capability an agent can use only once you grant it (otherwise inert)"),
    ]
    for pid in enablers:
        allowed = grants.get(pid, {}).get("allow", [])
        granted = ", ".join(allowed) if allowed else "—"
        # Annotate any subjects that are capability-denied on this privilege.
        denied_by_cap = [
            f"{g['subject']} (capability: {g['_capability']})"
            for g in cap_deny_grants
            if pid in _grant_priv_ids(g.get("privilege"))
        ]
        deny_note = f"  DENIED for: {', '.join(denied_by_cap)}" if denied_by_cap else ""
        lines.append(_row(pid, f"granted to: {granted}{deny_note}"))
    if not enablers:
        lines.append("  (none)")

    # Mandatory capability-deny attribution (ADR-016 narrowing-but-reported):
    # surface every capability-contributed deny with its source capability so
    # the operator can always see why an agent is denied a privilege.
    if cap_deny_grants:
        lines += [
            "",
            cli_render.style("heading", "CAPABILITY-CONTRIBUTED DENIES — auto-applied by installed capabilities (ADR-016)"),
        ]
        for g in cap_deny_grants:
            subj = g.get("subject", "?")
            cap = g.get("_capability", "?")
            privs = ", ".join(_grant_priv_ids(g.get("privilege")))
            lines.append(
                f"  {subj} — DENY {privs}  (contributed by capability: {cap})"
            )

    cap_note = (
        "ships with core; capability:<name> = added by an installed capability"
    )
    lines += [
        "",
        cli_render.style("heading", "Legend"),
        "  double-locked      denied in BOTH the hook (model) and Claude Code's native",
        "                     settings — so it holds even if the hook is off/faulting",
        "  granted to: —      no agent has this enabler yet",
        "  [directory|domain-scope]  the grant can be limited to paths or hosts via --scope",
        f"  backbone           {cap_note}",
        "",
        cli_render.style("heading", "Commands"),
        "  pkit permissions explain [agent]        who may do what (the policy view)",
        "  pkit permissions grant <subj> <priv>    enable a capability for a subject "
        "(--scope, --deny)",
        "  pkit permissions revoke <subj> <priv>   remove a grant",
        "  pkit permissions diff                   compare the model to live settings.json",
        "  pkit permissions enable | disable       turn live enforcement on / off",
        "  pkit permissions sandbox [enable|disable]  OS-box confinement: prompt-free scripting",
    ]
    return "\n".join(lines) + "\n"


# ---- diff ------------------------------------------------------------------

def diff(target_root: Path, agent: str | None) -> tuple[str, bool]:
    """Reconcile the model against live harness state. Returns (report, clean).

    Read-only and honest about scope: it reports rule *presence* + attribution,
    not invocation form. The high-value finding is live allow/deny rules that no
    granted privilege justifies (the "unjustified grant" flag)."""
    catalog = _load_catalog(target_root)
    model = _load_model(target_root)
    live = _live_settings(target_root)

    # Which privilege ids does the model grant (allow) to anyone?
    granted: set[str] = set()
    for g in model["grants"]:
        if g.get("effect", "allow") != "allow":
            continue
        privs = g["privilege"] if isinstance(g["privilege"], list) else [g["privilege"]]
        granted.update(_bare(p) for p in privs)

    lines: list[str] = [cli_render.style("title", "permissions diff (model ↔ live .claude/settings.json):")]
    extra: list[str] = []
    for rule in live["allow"]:
        pid = _attribute_rule(rule, catalog)
        if pid is None:
            extra.append(f"  ⚠ extra (no catalog privilege recognizes it): {rule}")
        elif pid not in granted:
            extra.append(f"  ⚠ unjustified (live allows {rule} → {pid}, but no subject is granted {pid})")
    if extra:
        lines.append("\n" + cli_render.style("heading", "live allow rules not justified by the model:"))
        lines.extend(extra)
    else:
        lines.append("  ✓ every live allow rule is justified by a granted privilege.")

    # Projection-based reconciliation (model → expected native settings, #249).
    # Augments the attribution view above: what the model would *realize* into
    # session-wide settings vs what's live. Uses the shared project() so this
    # view and `apply`'s emission can't disagree (ADR-002 same-code).
    proj = _projection_mod(target_root).project(model, catalog)
    expected = set(proj["settings"]["allow"])
    live_allow = set(live["allow"])
    ownership = model.get("ownership_mode", "additive")
    lines.append("\n" + cli_render.style("heading", "model → settings projection (expected session-wide allow rules):"))
    if not expected:
        lines.append("  (the model projects no session-wide allow rules yet)")
    else:
        applied = sorted(expected & live_allow)
        not_applied = sorted(expected - live_allow)
        lines.append(f"  applied: {len(applied)}/{len(expected)} expected rule(s) present live")
        if not_applied:
            lines.append(
                f"  not applied: {', '.join(not_applied)}  "
                f"(a future `apply` would write these to settings)"
            )
        if ownership == "managed":
            drift = sorted(
                r for r in (live_allow - expected) if _attribute_rule(r, catalog) in granted
            )
            if drift:
                lines.append(
                    f"  drift (managed mode): {', '.join(drift)}  "
                    f"(live, but not in the model's projection — a future `apply` would heal)"
                )
    lines.extend(_gap_report(target_root, proj))
    lines.append(
        "\nnote: reports rule presence + attribution, not invocation form; "
        "the command boundary is session-wide, not per-agent."
    )
    return "\n".join(lines) + "\n", not extra


def _gap_report(target_root: Path, proj: dict[str, Any]) -> list[str]:
    """The shared out-of-harness gap report: model intent that does NOT realize
    into session-wide settings — grants the hook enforces at runtime, grants no
    native layer expresses, and adapter-declared unenforceable dimensions. Used
    by both `diff` and `apply` so the two never describe the gap differently."""
    out: list[str] = []
    if proj["runtime"]:
        out.append(
            f"  {len(proj['runtime'])} grant(s) enforced at runtime, not in settings "
            f"(per-agent / scoped → the hook)"
        )
    if proj["unprojectable"]:
        out.append(
            f"  {len(proj['unprojectable'])} grant(s) no native layer expresses "
            f"(scoped / recognizer-shape — see ADR-004)"
        )
    enf = _load_yaml(target_root / ".pkit" / "adapters" / "claude-code" / "permission-enforcement.yaml")
    unenforceable = [
        d for d, spec in enf.get("dimensions", {}).items()
        if spec.get("enforcement") == "none"
    ]
    if unenforceable:
        out.append(
            f"⚠ not natively enforceable (declare + enforce out-of-harness): "
            f"{', '.join(unenforceable)}"
        )
    return out


# ---- mutation: grant / revoke / mode ---------------------------------------

_SUBJECT = re.compile(r"^(all|operator|agent:[a-z][a-z0-9-]*)$")
# A bare privilege id: a backbone single segment, or a capability-scoped
# `<cap>:<name>` (ADR-021). `grant`/`revoke` accept either; the token built
# from it (`[privilege-catalog:<id>]`) round-trips through the widened `_BARE`.
_PRIV_ID = re.compile(r"^[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?$")


class PermissionsError(Exception):
    """Raised on an invalid mutation (bad subject, unknown privilege, …)."""


def _project_dir(target_root: Path) -> Path:
    return target_root / ".pkit" / "permissions" / "project"


def _grants_path(target_root: Path) -> Path:
    return _project_dir(target_root) / "grants.yaml"


def _config_path(target_root: Path) -> Path:
    return _project_dir(target_root) / "config.yaml"


def _dump_yaml(path: Path, data: dict) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


def _read_grants_doc(target_root: Path) -> dict[str, Any]:
    path = _grants_path(target_root)
    if path.is_file():
        doc = _load_yaml(path)
        doc.setdefault("schema_version", 1)
        doc.setdefault("grants", [])
        return doc
    return {"schema_version": 1, "grants": []}


def _grant_matches(g: dict, subject: str, token: str) -> bool:
    if g.get("subject") != subject:
        return False
    gp = g.get("privilege")
    return gp == token or (isinstance(gp, list) and gp == [token])


def grant(target_root: Path, subject: str, privilege: str,
          scope: tuple[str, ...] | list[str], deny: bool) -> str:
    if not _SUBJECT.match(subject):
        raise PermissionsError(
            f"invalid subject {subject!r}; expected `all`, `operator`, or `agent:<name>`."
        )
    if not _PRIV_ID.match(privilege):
        raise PermissionsError(f"invalid privilege id {privilege!r} (expected kebab-case).")
    privileges = _load_catalog(target_root).get("privileges", {})
    if privilege not in privileges:
        raise PermissionsError(
            f"privilege {privilege!r} is not in the catalog — run `pkit permissions catalog`."
        )
    if scope and not privileges[privilege].get("scope_type"):
        raise PermissionsError(
            f"privilege {privilege!r} has no scope_type; --scope is not allowed for it."
        )
    doc = _read_grants_doc(target_root)
    token = f"[privilege-catalog:{privilege}]"
    effect = "deny" if deny else "allow"
    scope_list = list(scope)
    for g in doc["grants"]:
        if _grant_matches(g, subject, token):
            g["effect"] = effect
            if scope_list:
                g["scope"] = scope_list
            else:
                g.pop("scope", None)
            _dump_yaml(_grants_path(target_root), doc)
            return _grant_msg("updated", subject, effect, privilege, scope_list)
    entry: dict[str, Any] = {"subject": subject, "privilege": token, "effect": effect}
    if scope_list:
        entry["scope"] = scope_list
    doc["grants"].append(entry)
    _dump_yaml(_grants_path(target_root), doc)
    return _grant_msg("granted", subject, effect, privilege, scope_list)


def _grant_msg(verb: str, subject: str, effect: str, privilege: str, scope: list[str]) -> str:
    s = f"{verb}: {subject} {effect} {privilege}"
    return s + (f" (scope: {', '.join(scope)})" if scope else "")


def revoke(target_root: Path, subject: str, privilege: str) -> str:
    token = f"[privilege-catalog:{privilege}]"
    doc = _read_grants_doc(target_root)
    before = len(doc["grants"])
    doc["grants"] = [g for g in doc["grants"] if not _grant_matches(g, subject, token)]
    if len(doc["grants"]) == before:
        return f"no grant matched {subject} {privilege}; nothing to revoke."
    _dump_yaml(_grants_path(target_root), doc)
    return f"revoked: {subject} {privilege}"


# ---- scaffold: capability permission fragment (ADR-016 + ADR-021) ----------
#
# `pkit permissions scaffold <cap>` stamps the two kit-owned fragment files a
# capability ships in its own `permissions/` directory:
#   - privilege-catalog.yaml — the privilege DEFINITION half (ADR-021)
#   - grants.yaml            — the deny POLICY half (ADR-016)
# Both are hand-authored today, and a misauthored token fails QUIETLY (a bare
# `[privilege-catalog:<name>]` instead of the scoped `[privilege-catalog:<cap>:
# <name>]` matches no merged privilege, so the deny silently does not bind —
# the fail-open hazard ADR-021 names). The stamped files carry inline comment
# guidance capturing both footguns so the author lands the scoped form. The
# `pkit schemas validate` fragment-token lint (lint_capability_fragment_grants)
# is the structural backstop that catches a bare token if the comment is missed.

_FRAGMENT_CATALOG_TEMPLATE = """\
schema_version: 1
# Capability-contributed privilege-catalog FRAGMENT (ADR-021).
#
# Discovered by `load_catalog` via the manifest walk — merged into the central
# catalog ONLY when the `{name}` capability is an installed component.
#
# Footguns (read before authoring):
#   1. Author keys BARE (kebab-case, no scope prefix). The loader rewrites each
#      key to the capability-scoped id `{name}:<key>`. So the entry below
#      becomes `{name}:ad-hoc-scraping` in the merged catalog, and a grant must
#      reference it with the SCOPED token (see grants.yaml). Do NOT write the
#      `{name}:` prefix here — that would double-scope it.
#   2. `guardrail: true` is FORBIDDEN in a fragment. A capability may extend the
#      recognised vocabulary but may never install a deny on every adopter by
#      default; the loader REJECTS a fragment entry carrying it.
#
# Replace the illustrative entry below with this capability's own privilege(s),
# or delete this file if the capability ships no privilege definition.
privileges:
  ad-hoc-scraping:
    description: <one-line, domain-readable description of what this privilege permits>
    recognize:
      bash:
        - cmd: curl
        - cmd: wget
"""

_FRAGMENT_GRANTS_TEMPLATE = """\
schema_version: 1
# Capability-contributed intent-grant FRAGMENT (ADR-016).
#
# Discovered by `load_model` via the manifest walk — applies ONLY when the
# `{name}` capability is an installed component. On the deny side a capability
# grant survives via deny-wins; the operator overrides it with an explicit
# allow grant in their own `project/grants.yaml`.
#
# Footgun: reference a capability-contributed privilege (defined in this
# capability's privilege-catalog.yaml fragment) with the SCOPED token
# `[privilege-catalog:{name}:<name>]` — the `{name}:` scope is REQUIRED.
# A BARE `[privilege-catalog:<name>]` resolves to no merged privilege, so the
# deny silently does NOT bind (a fail-open hazard). A backbone privilege is
# still referenced bare (e.g. `[privilege-catalog:issue-tracker-write]`).
#
# Replace the illustrative grant below with this capability's own deny(ies),
# or delete this file if the capability ships no grant policy.
grants:
  - subject: agent:<this-capability-agent>
    privilege: '[privilege-catalog:{name}:ad-hoc-scraping]'
    effect: deny
"""


def scaffold_fragment(target_root: Path, capability: str) -> list[Path]:
    """Stamp a capability's `permissions/` fragment skeleton (ADR-016 + ADR-021).

    Writes `.pkit/capabilities/<capability>/permissions/{privilege-catalog,
    grants}.yaml` with the correct shapes and inline guidance on both authoring
    footguns (bare fragment keys vs the scoped grant token; the guardrail ban).

    Refuses an unknown capability (no `package.yaml`) and refuses to clobber an
    existing fragment file — the same no-overwrite discipline the other
    `new`/scaffold commands hold. Returns the paths stamped (a subset of the
    two, since an already-present file is left untouched).
    """
    if not _PRIV_ID.match(capability) or ":" in capability:
        raise PermissionsError(
            f"invalid capability name {capability!r}; expected kebab-case."
        )
    cap_dir = target_root / ".pkit" / "capabilities" / capability
    if not (cap_dir / "package.yaml").is_file():
        raise PermissionsError(
            f"unknown capability {capability!r}: no "
            f"{cap_dir.relative_to(target_root)}/package.yaml. Scaffold the "
            f"capability first (`pkit new capability {capability}`), or check "
            f"the name."
        )
    perms_dir = cap_dir / "permissions"
    perms_dir.mkdir(parents=True, exist_ok=True)
    stamped: list[Path] = []
    for filename, template in (
        ("privilege-catalog.yaml", _FRAGMENT_CATALOG_TEMPLATE),
        ("grants.yaml", _FRAGMENT_GRANTS_TEMPLATE),
    ):
        path = perms_dir / filename
        if path.is_file():
            continue  # no-clobber: leave an authored fragment untouched
        path.write_text(template.format(name=capability), encoding="utf-8")
        stamped.append(path)
    return stamped


# ---- lint: capability-fragment grant-token resolution (ADR-021) ------------
#
# A grant's privilege token must resolve to a privilege that EXISTS in the
# merged catalog, or the deny silently does not bind (the bare-vs-scoped
# fail-open hazard ADR-021 names: `[privilege-catalog:ad-hoc-scraping]` authored
# where the merged id is `<cap>:ad-hoc-scraping`). `decide.py` matches against
# the merged catalog at runtime, so this lint MUST resolve through the SAME
# merge (`load_catalog`) and the SAME token normaliser (`_privilege_ids`) to
# agree with the runtime exactly — a divergent reimplementation could pass a
# token the hook then fails to bind. Covers HAND-authored fragments (it walks
# the on-disk grants.yaml of every installed capability), not just the ones the
# `permissions grant` command writes.


@dataclass(frozen=True)
class FragmentGrantIssue:
    """One unresolved grant token in a capability's grants fragment."""

    capability: str
    grants_path: Path
    token: str
    fix_hint: str


def lint_capability_fragment_grants(target_root: Path) -> list[FragmentGrantIssue]:
    """Check every installed capability's grants fragment for tokens that
    resolve to no privilege in the MERGED catalog (ADR-021's fail-open hazard).

    Reuses the decision core's `load_catalog` (the same merge the hook runs) and
    `_privilege_ids` (the same token normaliser), so a token this lint passes is
    a token the runtime binds — and one it FAILS is one the runtime would
    silently drop. Walks the manifest `components:` list for kind=capability
    (install-state-as-gate, matching the runtime walk); a capability without a
    `permissions/grants.yaml` contributes nothing. Returns one issue per
    unresolved token.

    No-ops (returns []) when the project has no propagated decision core or no
    manifest — without either there is no permission subsystem to lint against
    (e.g. a bare schema-only tree).
    """
    decide_path = target_root / ".pkit" / "permissions" / "decide.py"
    manifest_path = target_root / ".pkit" / "manifest.yaml"
    if not decide_path.is_file() or not manifest_path.is_file():
        return []
    mod = _decide_mod(target_root)
    catalog = mod.load_catalog(str(target_root))
    known_ids = set(catalog.get("privileges", {}))

    manifest = _load_yaml(manifest_path)
    issues: list[FragmentGrantIssue] = []
    for component in manifest.get("components", []) or []:
        if not isinstance(component, dict) or component.get("kind") != "capability":
            continue
        name = component.get("name")
        if not name:
            continue
        grants_path = (
            target_root / ".pkit" / "capabilities" / name / "permissions" / "grants.yaml"
        )
        if not grants_path.is_file():
            continue
        doc = _load_yaml(grants_path)
        for grant in doc.get("grants", []) or []:
            if not isinstance(grant, dict):
                continue
            raw = grant.get("privilege")
            tokens = raw if isinstance(raw, list) else [raw]
            # Resolve per-token so the message names the exact offending token.
            for token in tokens:
                if not isinstance(token, str):
                    continue
                ids = mod._privilege_ids(token)
                if ids & known_ids:
                    continue
                bare = token[len("[privilege-catalog:"):-1] if token.startswith("[privilege-catalog:") and token.endswith("]") else None
                scoped_guess = f"[privilege-catalog:{name}:{bare}]" if bare and ":" not in bare else None
                fix = (
                    f"token resolves to no privilege in the merged catalog. If "
                    f"this references {name}'s own fragment privilege, it likely "
                    f"needs the `{name}:` scope: {scoped_guess}."
                    if scoped_guess
                    else (
                        "token resolves to no privilege in the merged catalog — "
                        "check the privilege id, the `<cap>:` scope, and that the "
                        "defining capability is installed."
                    )
                )
                issues.append(
                    FragmentGrantIssue(
                        capability=name,
                        grants_path=grants_path,
                        token=token,
                        fix_hint=fix,
                    )
                )
    return issues


def show_mode(target_root: Path) -> str:
    cfg = _load_yaml(_config_path(target_root))
    return (
        f"ownership_mode: {cfg.get('ownership_mode', 'additive')}   "
        f"posture: {cfg.get('posture', 'lenient')}"
    )


def set_mode(target_root: Path, mode: str) -> str:
    path = _config_path(target_root)
    cfg = _load_yaml(path) if path.is_file() else {}
    cfg.setdefault("schema_version", 1)
    cfg.setdefault("posture", "lenient")
    cfg["ownership_mode"] = mode
    _dump_yaml(path, cfg)
    msg = f"ownership_mode set to {mode}."
    if mode == "managed":
        msg += " (note: managed-mode realization is not yet implemented — wave 2.)"
    return msg


# ---- enable / disable live enforcement (claude-code) -----------------------
#
# Opt-in live enforcement per the issue #247 "Option B" decision (the DEC-030
# default-agent toggle precedent): a PreToolUse hook fires per Bash/tool call,
# so registering it is the adopter's explicit choice, not an install default.
#
# `enable` writes ONLY to the live `.claude/settings.json` (never a merge
# source): the `hooks` registration lives outside any realizer-owned region
# (ADR-002), and the merge primitive treats existing target top-level keys as
# last-write-wins survivors — so a registration written here survives re-merge,
# and `disable` must explicitly strip it (the DEC-030 strip-logic pattern).
#
# The hook script itself is a propagated adapter file (sync owns its lifecycle);
# enable/disable manage only its registration — there is no script to deploy or
# remove, hence no orphaned-script class of bug.

HOOK_COMMAND = "${CLAUDE_PROJECT_DIR}/.pkit/adapters/claude-code/permission-hook.py"
# Match all tools: `decide()` is the real filter (it abstains on anything the
# catalog doesn't recognize), so a static broad matcher can't go stale as the
# catalog grows — unlike a matcher derived from the catalog at enable time. The
# per-call cost of the broad match is the accepted tradeoff that makes this
# opt-in rather than on-by-default.
HOOK_MATCHER = "*"


def _settings_path(target_root: Path) -> Path:
    """The COMMITTED settings file — the shared baseline + narrowing floor. In a
    repo that tracks `.claude/`, this ships to every checkout (ADR-029)."""
    return target_root / ".claude" / "settings.json"


def _settings_local_path(target_root: Path) -> Path:
    """The GITIGNORED per-machine settings file — the widening + per-machine
    deviations (ADR-029). Claude Code deep-merges this over `settings.json`, so a
    widening routed here never lands in a committed file (ADR-008 rule 4 by
    construction). Its sandbox keys are read back via `_sandbox_block`'s union."""
    return target_root / ".claude" / "settings.local.json"


def _core_settings_denies(target_root: Path) -> list[str]:
    """The harness baseline's fail-closed native denies — the double-lock half
    that holds even if the hook faults. Sourced from the adapter's canonical
    core settings so there is no second hand-maintained deny list here."""
    core = target_root / ".pkit" / "adapters" / "claude-code" / "settings" / "core" / "settings.json"
    if not core.is_file():
        return []
    try:
        data = json.loads(core.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("permissions", {}).get("deny", []))


def _adapter_installed(target_root: Path, name: str) -> bool:
    manifest = target_root / ".pkit" / "manifest.yaml"
    data = _load_yaml(manifest)
    for entry in data.get("components", []) or []:
        if isinstance(entry, dict) and entry.get("kind") == "adapter" and entry.get("name") == name:
            return True
    return False


def _read_settings(target_root: Path) -> dict[str, Any]:
    path = _settings_path(target_root)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PermissionsError(f"{path} is not readable JSON: {exc}") from exc


def _write_settings(target_root: Path, data: dict[str, Any]) -> None:
    path = _settings_path(target_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_settings_local(target_root: Path) -> dict[str, Any]:
    """Read the gitignored per-machine settings file (ADR-029). Empty dict when
    absent. Same JSON-fault discipline as `_read_settings`."""
    path = _settings_local_path(target_root)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PermissionsError(f"{path} is not readable JSON: {exc}") from exc


def _write_settings_local(target_root: Path, data: dict[str, Any]) -> None:
    path = _settings_local_path(target_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _hook_entry_registered(pretooluse: list) -> bool:
    return any(
        isinstance(entry, dict)
        and any(
            isinstance(h, dict) and h.get("command") == HOOK_COMMAND
            for h in entry.get("hooks", []) or []
        )
        for entry in pretooluse
    )


def _enforcement_on(target_root: Path) -> bool:
    """True if the PreToolUse enforcement hook is registered live. Read-only,
    degrades to False on a missing/unreadable settings file (used by `overview`)."""
    path = _settings_path(target_root)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    hooks = data.get("hooks") if isinstance(data, dict) else None
    pre = hooks.get("PreToolUse", []) if isinstance(hooks, dict) else []
    return _hook_entry_registered(pre)


# ---- enforcement-runtime self-check (ADR-002 amendment) --------------------
#
# Distinct from the decision-time fail-open (§32 in ADR-002). An
# enforcement-runtime fault means the hook CANNOT START — its python3 runtime
# can't be found, the script has a syntax error, or `decide.py` is missing.
# When the runtime is dead, the hook never reaches decide() and silently
# abstains on EVERY call: the operator believes enforcement is live when it
# is not. This class of fault is fail-LOUD (ADR-002 amendment), not fail-open.
#
# Mechanism: run the hook script directly under `sys.executable` (the same
# python3 that will be found via `#!/usr/bin/env python3` in the hook's
# shebang) with a minimal probe payload. Three outcomes:
#   - Exits 0 + stdout or no-stdout → hook started and decided (runtime OK)
#   - Exits 0 + no output, payload is malformed by design → abstain (runtime OK)
#   - Any exception launching the process, or non-zero exit → runtime FAULT
#
# The probe payload is a deliberately minimal (but valid) Bash request so the
# hook exercises load_catalog + load_model + hook_decide. It does NOT need to
# match any real privilege: the decision (allow/deny/abstain) is irrelevant;
# we are testing whether the hook CAN RUN, not what it decides.

_RUNTIME_PROBE_PAYLOAD = json.dumps({
    "tool_name": "Bash",
    "tool_input": {"command": "echo pkit-runtime-probe"},
    "cwd": "/tmp",
})


def _hook_runtime_check(target_root: Path) -> tuple[bool, str]:
    """Probe whether the hook script can start. Returns (ok, detail).

    ok=True  → hook started and ran (runtime is healthy); may have abstained.
    ok=False → hook could not start (enforcement-runtime fault — fail-loud).
    This is NOT a decision correctness check (that's `probe`); it is purely
    a startup-reachability check per the ADR-002 amendment.
    """
    import subprocess
    import sys as _sys

    hook_path = target_root / ".pkit" / "adapters" / "claude-code" / "permission-hook.py"
    if not hook_path.is_file():
        return False, f"hook script not found at {hook_path}"
    try:
        result = subprocess.run(
            [_sys.executable, str(hook_path)],
            input=_RUNTIME_PROBE_PAYLOAD,
            capture_output=True,
            text=True,
            timeout=10,
            env={
                "CLAUDE_PROJECT_DIR": str(target_root),
                "PATH": os.environ.get("PATH", ""),
            },
        )
        if result.returncode != 0:
            detail = (result.stderr or "").strip()
            return False, f"hook exited {result.returncode}" + (f": {detail}" if detail else "")
        return True, "hook started and returned exit 0"
    except FileNotFoundError as exc:
        return False, f"python3 interpreter not found: {exc}"
    except Exception as exc:
        return False, f"could not launch hook: {exc!r}"


# ---- OS confinement write probe (ADR-002 amendment / ADR-014 §6) -----------
#
# `sandbox enable` reports config-ON, but Claude Code silently runs unconfined
# when the box cannot initialize unless `failIfUnavailable: true` is set
# (ADR-014 evidence 6). Even with failIfUnavailable set, the self-check must
# verify *actual* confinement — not just that the config reads ON — so that
# `permissions overview` can report "sandbox configured but NOT actually
# confining" when config disagrees with a real probe.
#
# Mechanism: attempt to create a temporary file outside the workspace (at
# /private/tmp or /tmp, which the Seatbelt box denies). If the write succeeds,
# confinement is NOT active from this process's perspective. If it is denied
# (PermissionError / OSError), confinement is active.
#
# Contract (same as probe --live): reachability only; the probe file is
# deleted immediately on success. The probe is NOT conclusive from a plain
# terminal (outside the box); it is conclusive ONLY from inside a Claude
# Code session that has the sandbox active. `overview` annotates accordingly.

def _confinement_write_probe() -> str:
    """Attempt a write outside the workspace. Returns 'denied' | 'allowed' | 'error'.

    'denied' → OS blocked it → confinement is active.
    'allowed' → OS permitted it → NOT confined (or probe ran outside the box).
    'error'   → unexpected error (treat as inconclusive).
    """
    import tempfile
    import uuid

    probe_name = f"pkit-confinement-probe-{uuid.uuid4().hex[:8]}"
    # Use /private/tmp on macOS (real path behind /tmp symlink) then /tmp as fallback.
    for probe_dir in ("/private/tmp", "/tmp"):
        probe_path = Path(probe_dir) / probe_name
        try:
            probe_path.write_text("x", encoding="utf-8")
            try:
                probe_path.unlink()
            except OSError:
                pass
            return "allowed"
        except PermissionError:
            return "denied"
        except OSError:
            continue
    return "error"


def enable(target_root: Path) -> str:
    """Register the PreToolUse enforcement hook, ensure the fail-closed native
    guardrail denies are present (the double-lock), and run the startup
    self-check to detect dead-hook enforcement-runtime faults loudly (per the
    ADR-002 amendment). Idempotent."""
    if not _adapter_installed(target_root, "claude-code"):
        raise PermissionsError(
            "the claude-code adapter is not installed in this project; "
            "live enforcement is harness-specific, so there is nothing to enable."
        )
    settings = _read_settings(target_root)
    changes: list[str] = []

    hooks = settings.setdefault("hooks", {})
    pretooluse = hooks.setdefault("PreToolUse", [])
    if _hook_entry_registered(pretooluse):
        changes.append("hook already registered")
    else:
        pretooluse.append(
            {"matcher": HOOK_MATCHER, "hooks": [{"type": "command", "command": HOOK_COMMAND}]}
        )
        changes.append("registered PreToolUse hook")

    perms = settings.setdefault("permissions", {})
    deny = perms.setdefault("deny", [])
    added = [d for d in _core_settings_denies(target_root) if d not in deny]
    if added:
        deny.extend(added)
        changes.append(f"ensured {len(added)} native guardrail deny(ies)")
    else:
        changes.append("native guardrail denies already present")

    _write_settings(target_root, settings)
    result = "live enforcement enabled: " + "; ".join(changes) + "."

    # Enforcement-runtime self-check (ADR-002 amendment): verify the hook can
    # actually start. A dead runtime (can't import decide.py, python3 not found,
    # etc.) would silently make every call fail-open; that is an enforcement-
    # runtime fault and must be surfaced loudly, not hidden.
    ok, detail = _hook_runtime_check(target_root)
    if not ok:
        result += (
            "\n\nWARNING: enforcement-runtime fault — hook registered but CANNOT START.\n"
            f"  diagnosed: {detail}\n"
            "  The hook is NOT currently gating tool calls. Enforcement is fail-open on\n"
            "  EVERY call until this is resolved. Check that `python3` is available,\n"
            "  that .pkit/permissions/decide.py exists, and that .pkit/schemas/\n"
            "  privilege-catalog.yaml is present. Run `pkit permissions probe` for detail.\n"
            "  State surfaced in `pkit permissions overview`."
        )
    return result


def disable(target_root: Path) -> str:
    """Strip the PreToolUse enforcement hook registration (the DEC-030 strip-
    logic pattern), preserving any other adopter hooks and the baseline native
    denies. Idempotent."""
    path = _settings_path(target_root)
    if not path.is_file():
        return "live enforcement already disabled: no .claude/settings.json."
    settings = _read_settings(target_root)
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict) or not hooks.get("PreToolUse"):
        return "live enforcement already disabled: no PreToolUse hook registered."

    kept: list = []
    stripped = False
    for entry in hooks["PreToolUse"]:
        if not isinstance(entry, dict):
            kept.append(entry)
            continue
        inner = [
            h for h in entry.get("hooks", []) or []
            if not (isinstance(h, dict) and h.get("command") == HOOK_COMMAND)
        ]
        if len(inner) != len(entry.get("hooks", []) or []):
            stripped = True
        if inner:
            entry["hooks"] = inner
            kept.append(entry)
        # entry whose only hook was ours → dropped entirely (no orphan).

    if not stripped:
        return "live enforcement already disabled: pkit hook not registered."

    if kept:
        hooks["PreToolUse"] = kept
    else:
        hooks.pop("PreToolUse", None)
    if not hooks:
        settings.pop("hooks", None)

    _write_settings(target_root, settings)
    return (
        "live enforcement disabled: stripped the PreToolUse hook registration "
        "(native guardrail denies left in place)."
    )


# ---- sandbox confinement (ADR-004 / ADR-005, #274) --------------------------
#
# The sandbox writer ADR-005 deferred: turn on Claude Code's OS sandbox
# (macOS Seatbelt / Linux bubblewrap) with `autoAllowBashIfSandboxed`, so
# scripting (bash / python3) runs prompt-free INSIDE the box instead of
# prompting the operator. This closes the autonomous profile's documented gap
# ("scripting rides the (deferred) sandbox").
#
# Fail-closed invariant (ADR-004 §4 "fail-closed"): prompt-suppression
# conditioned on confinement MUST fail closed — `sandbox_enable` always pairs
# auto-allow with `failIfUnavailable: true` (session refuses if the box can't
# start, rather than silently running unsandboxed — the harness default is
# fail-open). The sole way to write `failIfUnavailable: false` is the loud,
# per-invocation `--dangerously-allow-unconfined` operator gesture; it is never
# persisted as a default — re-running `enable` without it restores the floor.
#
# Reconciliation of ADR-005's `allowUnsandboxedCommands: false` requirement:
# NOT required for safety. The unsandboxed *fail-over* path (a command that
# fails inside the box retried outside via `dangerouslyDisableSandbox`) rides
# the normal permission flow — allowlist or prompt — and is never auto-allowed;
# only *sandboxed* commands are auto-approved. Forcing `false` breaks legit
# fail-over (`git push` / `gh` need network/SSH reach the box blocks), so the
# key is left at harness default; `--strict` writes it as optional hardening.
# The reconciliation note lives in ADR-005.
#
# Writes are additive over the operator's `sandbox` block: operator keys
# (`excludedCommands`, `network`, extra `denyRead` entries, …) survive both
# enable and disable. The default sandbox read policy still permits credential
# paths, so `enable` also writes a credential `denyRead` floor. The harness
# does NOT hot-reload `sandbox.enabled` — enable/disable print a restart note;
# the other keys hot-reload.

SANDBOX_CREDENTIAL_DENY_READ = ["~/.ssh", "~/.aws", "~/.config/gh", "~/.netrc"]

_RESTART_NOTE = (
    "note: `sandbox.enabled` is not hot-reloaded — restart the Claude Code "
    "session for it to take effect."
)


def _sandbox_block_in(data: dict[str, Any]) -> dict[str, Any]:
    sb = data.get("sandbox") if isinstance(data, dict) else None
    return sb if isinstance(sb, dict) else {}


def _merge_sandbox_blocks(committed: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two `sandbox` blocks the way Claude Code does at runtime
    (ADR-029, verified against the sandboxing docs): array-valued keys
    (`excludedCommands`, `filesystem.denyRead`/`allowRead`/`allowWrite`,
    `network.allowedHosts`/`allowUnixSockets`) UNION across scopes — the
    committed floor survives when the local file adds entries; scalar keys
    (`enabled`, `failIfUnavailable`, `allowUnsandboxedCommands`, …) take the
    local (higher-precedence) value with the rest preserved.

    The union read this produces is what lets every reader (`sandbox status`,
    `disable`, the self-heal, the seal/provenance checks) find an authored entry
    in whichever file its classification routed it to (ADR-029 cond. 5)."""
    out: dict[str, Any] = {}
    for key in set(committed) | set(local):
        cv, lv = committed.get(key), local.get(key)
        if isinstance(cv, list) or isinstance(lv, list):
            merged_list = list(cv or [])
            for item in (lv or []):
                if item not in merged_list:
                    merged_list.append(item)
            out[key] = merged_list
        elif isinstance(cv, dict) or isinstance(lv, dict):
            out[key] = _merge_sandbox_blocks(cv or {}, lv or {})
        else:
            out[key] = lv if key in local else cv
    return out


def _sandbox_block(target_root: Path) -> dict[str, Any]:
    """The EFFECTIVE live `sandbox` block — the runtime union of the committed
    `settings.json` floor and the gitignored `settings.local.json` widenings,
    deep-merged exactly as Claude Code merges them (ADR-029). Read-only;
    degrades to {} when neither file is present/readable. Used by `overview`,
    `sandbox status`, the self-heal, and the seal checks, all of which must see
    an authored entry regardless of which file routing landed it in."""
    committed = _sandbox_block_in(_read_settings_or_empty(target_root, _settings_path(target_root)))
    local = _sandbox_block_in(_read_settings_or_empty(target_root, _settings_local_path(target_root)))
    return _merge_sandbox_blocks(committed, local)


def _read_settings_or_empty(target_root: Path, path: Path) -> dict[str, Any]:
    """Tolerant JSON read for the read-only union surfaces — {} on absent or
    unreadable, never raising (status/overview must not crash on a bad file)."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _auto_accommodate_narrowing_toolkits(target_root: Path) -> str:
    """Auto-apply the narrowing allowances of any confinement toolkit whose
    detect globs match the project AND whose allowances are ALL narrowing
    (never widening — ADR-008 rule 3/4).

    Called by `sandbox enable` to make the confined CLI usable without a
    manual `sandbox accommodate` step. The uv toolkit is the primary consumer
    (the `~/.cache/uv` write allowance, needed by the confined `pkit`/`uv`
    CLI on Linux/bubblewrap; inert-but-harmless on macOS per ADR-014).

    Routes through the single provenance writer `_apply_allowances` /
    `_record_accommodation` — the same path `accommodate` uses (ADR-008 rule 2;
    no second write path). Idempotent: `_apply_allowances` is a set-union write
    and `_record_accommodation` de-duplicates the config list.

    allow-host narrowing (ADR-015 narrowing-but-reported): toolkits whose ONLY
    narrowing allowances are `allow-host` for named, bounded hosts are also
    auto-applied here. ANY toolkit with an `allow-host * / any` value is kept in
    the widening class (its effect is `widening` in the data) and is excluded by
    the no-widening guard below. Egress hosts applied here are surfaced in the
    mandatory-reporting lines of `sandbox_status` / `overview`.

    Returns a human-readable note for the `sandbox enable` output, or an
    empty string when no toolkit is detected."""
    toolkits = _load_toolkits(target_root)
    # Any toolkit with at least one NARROWING allowance qualifies — we apply ONLY
    # its narrowing allowances (`_narrowing` filters out widening per allowance).
    # A toolkit may now be MIXED (the `uv` toolkit carries both its `~/.cache/uv`
    # narrowing cache and its macOS `exclude-command` widening — ADR-027); the
    # narrowing half is still safe-to-auto-apply, and the widening half is never
    # written here (it rides the explicit-gesture / required-auto-apply paths).
    candidates = {
        name: spec for name, spec in toolkits.items()
        if _narrowing(spec.get("allowances", []))
    }
    detected = [t for t in _detect_tools(target_root, candidates) if t in candidates]
    if not detected:
        return ""
    applied: list[str] = []
    for tool in detected:
        narrowing = _narrowing(candidates[tool].get("allowances", []))
        _apply_allowances(target_root, narrowing, tool)
        _record_accommodation(target_root, tool, add=True)
        applied.append(tool)
    values = []
    for tool in applied:
        values += [a.get("value", "") for a in _narrowing(candidates[tool].get("allowances", []))]
    note = (
        f"auto-accommodated: {', '.join(applied)} (narrowing — {', '.join(v for v in values if v)}; "
        f"effective on Linux/bubblewrap; inert on macOS per ADR-014)"
    )
    # Mandatory egress reporting (ADR-015 narrowing-but-reported): surface any
    # allow-host allowances applied by auto-accommodation with the verbatim gloss.
    egress_lines = _egress_report_lines(target_root)
    if egress_lines:
        note += "\n" + "\n".join(egress_lines)
    return note


def sandbox_enable(target_root: Path, strict: bool = False,
                   dangerously_allow_unconfined: bool = False) -> str:
    """Turn on the OS sandbox with prompt-free scripting, fail-closed.
    Additive over the operator's `sandbox` block; idempotent.

    Auto-accommodates the uv-cache narrowing allowance (`~/.cache/uv`) when
    the uv confinement toolkit is detected (via its `detect` globs — `uv.lock`
    or `pyproject.toml` present in the project). This is a narrowing-only
    allowance (ADR-008 rule 3): it makes the confined `pkit`/`uv` CLI usable
    on Linux/bubblewrap without enlarging the agent's reach. The allowance is
    written through the same provenance writer `sandbox accommodate` uses
    (ADR-008 rule 2 — single writer). On macOS the uv CLI is excluded from the
    box (ADR-014), so the allowance is inert but harmless there. Idempotent:
    re-running this when uv is already accommodated is a no-op."""
    if not _adapter_installed(target_root, "claude-code"):
        raise PermissionsError(
            "the claude-code adapter is not installed in this project; the "
            "sandbox is harness-specific, so there is nothing to enable."
        )
    # ADR-029 + ADR-032 routing: the operator-invariant floor (`autoAllowBash
    # IfSandboxed`, `failIfUnavailable`, the credential `denyRead` floor) is
    # COMMITTED → `settings.json`. Two keys route per-machine: the
    # `allowUnsandboxedCommands` seal (a deviation) AND `enabled` itself —
    # `enabled` is operator-activated and HARNESS-CO-OWNED (the `/sandbox` panel
    # writes it into `settings.local.json`), so pkit defers to that local key and
    # never authors a parallel committed copy (ADR-032 Rule B defer branch — the
    # split-brain fix for the believed-off-but-on disable bug). This one primitive
    # owns these destinations and routes each key. Both `enabled` and the seal are
    # read off the runtime union (`_sandbox_block`) so the checks find them
    # wherever they live.
    settings = _read_settings(target_root)
    sb = settings.setdefault("sandbox", {})
    changes: list[str] = []

    # `enabled` routes to the harness-co-owned local file (ADR-032 Rule B). Read
    # the union so an already-on box (committed OR local) is a no-op; write only
    # the single local key the harness `/sandbox` panel reads.
    if _sandbox_block(target_root).get("enabled") is True:
        changes.append("sandbox already enabled")
    else:
        local = _read_settings_local(target_root)
        local.setdefault("sandbox", {})["enabled"] = True
        _write_settings_local(target_root, local)
        changes.append("enabled the OS sandbox")
    if sb.get("autoAllowBashIfSandboxed") is not True:
        sb["autoAllowBashIfSandboxed"] = True
        changes.append("auto-allow for sandboxed Bash")

    # The fail-closed invariant (ADR-004): always written, so a previous
    # dangerous run (or a hand-edit) can't leave the floor lowered.
    fail_closed = not dangerously_allow_unconfined
    if sb.get("failIfUnavailable") is not fail_closed:
        sb["failIfUnavailable"] = fail_closed
        changes.append(
            "fail-closed (failIfUnavailable: true)" if fail_closed
            else "FAIL-OPEN (failIfUnavailable: false)"
        )

    # The seal is a widening/deviation → routed to the per-machine local file.
    # Its current value is read from the runtime union (committed + local).
    seal_now = _sandbox_block(target_root).get("allowUnsandboxedCommands")
    if strict:
        if seal_now is not False:
            local = _read_settings_local(target_root)
            local.setdefault("sandbox", {})["allowUnsandboxedCommands"] = False
            _write_settings_local(target_root, local)
            changes.append("strict mode (allowUnsandboxedCommands: false)")
        # Record that pkit authored the seal (ADR-028 cond. 5 / ADR-008 rule 2):
        # the provenance entry is what lets a later non-strict enable reverse
        # the *posture's* seal while leaving an operator's hand-set `false`
        # untouched. Idempotent — a re-seal is a no-op on the ledger.
        _record_seal_provenance(target_root)
    else:
        # not strict → the unsandboxed escape is OPEN: restore the harness default
        # (fail-over via the normal permission flow) by dropping the seal — but
        # ONLY when pkit authored it (provenance present). This is the reversibility
        # lever ADR-028 cond. 5 names: `sandbox enable` without --strict reverses
        # the *posture's* pkit-set seal, so the operator regains the
        # `dangerouslyDisableSandbox` stopgap outside the autonomy posture. A
        # `false` with NO pkit provenance is an operator's hand-set choice — left
        # UNTOUCHED (ADR-008 rule 2: never wipe an operator's hand-set entry). The
        # seal lives in the per-machine local file (ADR-029) — clear it there, and
        # clear the provenance alongside to keep ledger and live config in sync.
        if seal_now is False and _seal_is_pkit_authored(target_root):
            local = _read_settings_local(target_root)
            local_sb = local.get("sandbox")
            if isinstance(local_sb, dict):
                local_sb.pop("allowUnsandboxedCommands", None)
                _write_settings_local(target_root, local)
            _clear_seal_provenance(target_root)
            changes.append("strict off (unsandboxed escape restored)")

    fs = sb.setdefault("filesystem", {})
    deny = fs.setdefault("denyRead", [])
    added = [p for p in SANDBOX_CREDENTIAL_DENY_READ if p not in deny]
    if added:
        deny.extend(added)
        changes.append(f"credential denyRead floor (+{len(added)} path(s))")
    else:
        changes.append("credential denyRead floor already present")

    _write_settings(target_root, settings)

    # Auto-accommodate narrowing-only toolkit allowances detected in the project
    # (ADR-008 rule 3). Applies only the uv toolkit on `sandbox enable` — the
    # full detect+seed path lives in `setup autonomy` (_setup_accommodations).
    # Here we narrow to toolkits whose ALL allowances are narrowing (never widen
    # on auto-detect), and only those whose detect globs match the project tree.
    # Uses the same provenance writer as `sandbox accommodate` — single writer
    # (ADR-008 rule 2). Idempotent: _apply_allowances is a set-union write.
    uv_accommodation_note = _auto_accommodate_narrowing_toolkits(target_root)

    lines = ["sandbox enabled: " + "; ".join(changes) + "."]
    if uv_accommodation_note:
        lines.append(uv_accommodation_note)
    if dangerously_allow_unconfined:
        lines.append(
            "⚠ DANGEROUS: failIfUnavailable is OFF — if the OS sandbox cannot "
            "start, the session silently runs UNCONFINED (the fail-open ADR-004 "
            "forbids). Per-invocation operator gesture only; re-run "
            "`pkit permissions sandbox enable` without the flag to restore the "
            "fail-closed floor."
        )
    if strict:
        lines.append(
            "strict: the unsandboxed fail-over escape hatch is locked — commands "
            "that fail inside the box (e.g. `git push` / `gh` needing network/SSH) "
            "cannot be retried outside it; use `excludedCommands` for those."
        )
    lines.append(_RESTART_NOTE)

    # Enforcement-runtime self-check (ADR-002 amendment): same check as
    # `enable` — wire into `sandbox enable` because this is the combined
    # "enforcement + confinement" path that operators run for full autonomy.
    hook_ok, hook_detail = _hook_runtime_check(target_root)
    if not hook_ok:
        lines += [
            "",
            "WARNING: enforcement-runtime fault — hook registered but CANNOT START.",
            f"  diagnosed: {hook_detail}",
            "  The hook is NOT currently gating tool calls (enforcement fail-open on",
            "  EVERY call). Fix before relying on enforcement. Run `pkit permissions",
            "  enable` for the detailed warning. State surfaced in `pkit permissions overview`.",
        ]

    # Actual-confinement write probe (ADR-002 amendment / ADR-014 §6): verify
    # the sandbox is ACTUALLY confining — not just that the config reads ON.
    # A write outside the workspace succeeds when the session runs unconfined
    # (box can't init without failIfUnavailable, or this is a plain terminal).
    # Report "configured but NOT actually confining" when config-ON disagrees
    # with the probe. Probe is inconclusive from outside the box (plain terminal
    # or session not yet restarted) — annotate that honestly.
    if fail_closed:
        probe_result = _confinement_write_probe()
        if probe_result == "denied":
            lines += [
                "",
                "confinement verified: out-of-workspace write DENIED by the OS — "
                "the sandbox is actually confining.",
            ]
        elif probe_result == "allowed":
            lines += [
                "",
                "WARNING: sandbox configured ON but NOT actually confining — an out-of-workspace",
                "  write SUCCEEDED. Possible causes: (a) this process is running outside the box",
                "  (plain terminal / session not yet restarted after enable), (b) the OS sandbox",
                "  could not initialize and `failIfUnavailable` is not yet in effect (restart the",
                "  session). If this warning persists from a Claude Code session, the box is NOT",
                "  confining — investigate before relying on sandbox confinement.",
                "  State surfaced in `pkit permissions overview`.",
            ]
        # probe_result == "error" → inconclusive; no annotation.

    return "\n".join(lines) + "\n"


def sandbox_disable(target_root: Path) -> str:
    """Turn the OS sandbox off by writing the single per-machine `enabled: false`
    the harness `/sandbox` panel reads (ADR-032 Rule B defer branch), leaving
    operator keys (excludedCommands, denyRead floor, …) in place. Idempotent.

    `enabled` is harness-co-owned and routes to `settings.local.json` (where the
    panel writes it); the runtime is the deep-merge union and `enabled` is a scalar
    local-wins key (ADR-029). The believed-off-but-on disable bug was pkit flipping
    a *committed* `enabled` while the harness-local `enabled: true` kept the box on.
    The fix: pkit writes the SAME local key, so the union resolves off. A drifted
    committed `enabled: true` (pre-ADR-032 state) is also cleared so the union has
    no residual ON source; a credential floor and other committed keys stay put."""
    # Already off in the union → nothing to do (idempotent).
    if _sandbox_block(target_root).get("enabled") is not True:
        return "sandbox already disabled.\n"

    # Write the single local `enabled: false` — the key the harness reads. Because
    # `enabled` is scalar local-wins, this resolves the union OFF even when a
    # committed `enabled: true` is still present (which we also clear below).
    local = _read_settings_local(target_root)
    local.setdefault("sandbox", {})["enabled"] = False
    _write_settings_local(target_root, local)

    # Clear any drifted COMMITTED `enabled: true` (pre-ADR-032, pkit used to author
    # it there). Leave the rest of the committed floor untouched; only the stale
    # `enabled` source is stripped so nothing in the union claims the box on.
    if _settings_path(target_root).is_file():
        committed = _read_settings(target_root)
        csb = committed.get("sandbox")
        if isinstance(csb, dict) and csb.get("enabled") is True:
            csb["enabled"] = False
            _write_settings(target_root, committed)

    return (
        "sandbox disabled (enabled: false in settings.local.json — the key the "
        "harness reads; other sandbox keys left in place; scripting prompts "
        "again).\n" + _RESTART_NOTE + "\n"
    )


def sandbox_status(target_root: Path) -> str:
    """Render the sandbox confinement state (read-only), including the actual-
    confinement write probe so `sandbox status` reports config-ON-but-not-
    confining loudly (ADR-002 amendment / ADR-014 §6)."""
    sb = _sandbox_block(target_root)
    enabled = sb.get("enabled") is True
    lines = [cli_render.style("title", "Sandbox confinement — prompt-free scripting inside the OS box (ADR-004)"), ""]
    if not enabled:
        lines.append(
            "  " + cli_render.style("strong", "OFF") + " — scripting (bash / python3) rides the normal permission flow "
            "(prompts); run `pkit permissions sandbox enable`."
        )
        return "\n".join(lines) + "\n"

    auto = sb.get("autoAllowBashIfSandboxed", True)  # harness default: true
    fail_closed = sb.get("failIfUnavailable") is True
    strict = sb.get("allowUnsandboxedCommands") is False
    deny = (sb.get("filesystem") or {}).get("denyRead", []) or []
    missing = [p for p in SANDBOX_CREDENTIAL_DENY_READ if p not in deny]

    # Actual-confinement write probe: verify the box is actually confining.
    # Reports honestly: DENIED = proven, ALLOWED = not confining (or outside box).
    probe_result = _confinement_write_probe()

    lines.append("  " + cli_render.style("strong", "ON") + " — sandboxed commands run confined to the box (Seatbelt / bubblewrap)")
    lines.append(
        "  auto-allow      "
        + ("on — sandboxed Bash runs prompt-free" if auto
           else "off — sandboxed Bash still prompts")
    )
    lines.append(
        "  fail mode       "
        + ("closed — session refuses if the box can't start (the ADR-004 invariant)"
           if fail_closed else
           "⚠ OPEN — if the box can't start the session runs UNCONFINED; "
           "re-run `sandbox enable` to restore fail-closed")
    )
    if probe_result == "denied":
        confinement_line = "  actual confinement  VERIFIED — out-of-workspace write DENIED by the OS  ✓"
    elif probe_result == "allowed":
        confinement_line = (
            "  actual confinement  ⚠ NOT CONFINING — out-of-workspace write SUCCEEDED; "
            "session may be outside the box (restart needed) or sandbox cannot initialize"
        )
    else:
        confinement_line = (
            "  actual confinement  inconclusive (probe could not write to /tmp); "
            "run from a Claude Code session to prove confinement"
        )
    lines.append(confinement_line)
    lines.append(
        "  fail-over       "
        + ("strict — locked; failing commands can't retry outside the box" if strict
           else "default — failing commands retry outside the box via the normal "
                "permission flow (never auto-allowed)")
    )
    # Honest reported state of the live `allowUnsandboxedCommands` value (ADR-028
    # cond. 4): sealed only when the key is actually false — never a fail-open
    # claim of a boundary the configuration does not hold.
    lines.append(
        "  unsandboxed escape "
        + ("sealed (strict) — the per-command `dangerouslyDisableSandbox` escape "
           "is inert; an agent can't silently disable the box" if strict
           else "OPEN — the per-command `dangerouslyDisableSandbox` escape can "
                "disable the box for a call; run `sandbox enable --strict` "
                "(or `setup autonomy`) to seal it")
    )
    lines.append(
        "  credential floor "
        + ("complete — " + ", ".join(SANDBOX_CREDENTIAL_DENY_READ) + " deny-read"
           if not missing else
           f"⚠ incomplete — missing denyRead for: {', '.join(missing)}; "
           "re-run `sandbox enable`")
    )
    excluded = sb.get("excludedCommands") or []
    if excluded:
        # Attribute each excluded command by its provenance tag (ADR-027 cond. 3):
        # `_required` = pkit auto-applied a platform-mandatory exclusion; `_manual`
        # (or any other tag / no tag) = an operator's hand-added carve-out. The
        # reader tolerates BOTH old `_manual` and new `_required` entries.
        prov = _load_provenance(target_root)
        required_cmds = {
            e.get("value") for e in prov
            if e.get("toolkit") == _REQUIRED_TOOLKIT and e.get("kind") == "exclude-command"
        }
        auto = [c for c in excluded if c in required_cmds]
        operator = [c for c in excluded if c not in required_cmds]
        lines.append(f"  excluded        {len(excluded)} command(s) run outside the box")
        if auto:
            lines.append(
                f"                  {', '.join(sorted(auto))} — auto-applied (required: "
                f"platform-mandatory, necessity-verified — ADR-027)"
            )
        if operator:
            lines.append(
                f"                  {', '.join(sorted(operator))} — operator-set "
                f"(explicit `sandbox exclude` gesture)"
            )
    # Mandatory egress reporting (ADR-015 narrowing-but-reported): surface every
    # applied allow-host host with source + the verbatim honesty gloss.
    egress_lines = _egress_report_lines(target_root)
    if egress_lines:
        lines.append("")
        lines.extend(egress_lines)
    lines += [
        "",
        cli_render.style("heading", "Commands"),
        "  pkit permissions sandbox enable [--strict]   turn on (fail-closed, additive)",
        "  pkit permissions sandbox disable             turn off (operator keys survive)",
        "  pkit permissions overview                    full permission + enforcement state",
    ]
    return "\n".join(lines) + "\n"


# ---- apply (additive realization, #250) ------------------------------------

def apply(target_root: Path) -> str:
    """Additively realize the model into the harness (per ADR-002 additive mode).

    Unions the model's projected session-wide allow rules into live
    `.claude/settings.json` and ensures the fail-closed guardrail denies (the
    double-lock), then reports the out-of-harness gap. Writes the live target
    in-process — like `enable`, and deliberately NOT via a merge source:
    projected allows are model-derived realizer output, and parking them in a
    hand-edited source would accrete drift additive mode can't heal on revoke.

    Additive only — never removes or replaces (managed-mode wholesale
    regeneration is #252). Idempotent: a set-union write, so re-running is a
    fixed point. The settings + gap report use the same `project()` /
    `_gap_report` as `diff`, so realization and reconciliation can't disagree.
    """
    if not _adapter_installed(target_root, "claude-code"):
        raise PermissionsError(
            "the claude-code adapter is not installed; `apply` realizes into its "
            "settings.json and has nothing to write without it."
        )
    catalog = _load_catalog(target_root)
    model = _load_model(target_root)
    if model.get("ownership_mode") == "managed":
        # Additive-only by guard, not by omission: managed mode wholesale-
        # regenerates the region (the #252 seam), which this realizer does not do.
        raise PermissionsError(
            "ownership_mode is `managed`, but managed-mode apply (wholesale region "
            "regeneration) is not yet implemented (#252). This is the additive "
            "realizer — set `pkit permissions mode additive` to use it."
        )
    proj = _projection_mod(target_root).project(model, catalog)

    settings = _read_settings(target_root)
    perms = settings.setdefault("permissions", {})
    allow = perms.setdefault("allow", [])
    deny = perms.setdefault("deny", [])

    expected = proj["settings"]["allow"]
    added_allow = [r for r in expected if r not in allow]
    allow.extend(added_allow)
    added_deny = [d for d in _core_settings_denies(target_root) if d not in deny]
    deny.extend(added_deny)

    changed = bool(added_allow or added_deny)
    if changed:
        _write_settings(target_root, settings)

    lines: list[str] = []
    if changed:
        parts = []
        if added_allow:
            parts.append(f"{len(added_allow)} allow rule(s)")
        if added_deny:
            parts.append(f"{len(added_deny)} guardrail deny(ies)")
        lines.append(cli_render.style(
            "strong",
            "applied (additive): added " + " + ".join(parts) + " to .claude/settings.json.",
        ))
    else:
        lines.append(cli_render.style("strong", "applied (additive): already realized — nothing to add."))
    if expected:
        lines.append(f"  model's session-wide allow rules: {', '.join(sorted(expected))}")

    gap = _gap_report(target_root, proj)
    if gap:
        lines.append("\n" + cli_render.style("heading", "out-of-harness gap (enforced elsewhere or not natively expressible):"))
        lines.extend(gap)
    return "\n".join(lines) + "\n"


# ---- profiles (#255 / ADR-005) ---------------------------------------------
#
# A profile is a named, selectable autonomy level: posture + a LAYERED per-agent
# grant-source. `use` writes `active_profile` + posture to config; the model
# loader (decide.load_model) layers the profile's grants between the guardrail
# denies and the adopter's own grants.yaml — never overwriting manual grants.
# Confinement (sandbox) is referenced in a profile's prose, not written (ADR-005
# defers the sandbox writer). `use` does NOT enable the hook (orthogonal, #247).

def _shipped_profiles_dir(target_root: Path) -> Path:
    return target_root / ".pkit" / "permissions" / "profiles"


def _project_profiles_dir(target_root: Path) -> Path:
    return target_root / ".pkit" / "permissions" / "project" / "profiles"


def _profile_names(d: Path) -> list[str]:
    return sorted(p.stem for p in d.glob("*.yaml")) if d.is_dir() else []


def _resolve_profile(target_root: Path, name: str) -> tuple[Path, dict[str, Any]] | None:
    """Resolve a profile by name, project-first then shipped. (path, doc) or None."""
    for d in (_project_profiles_dir(target_root), _shipped_profiles_dir(target_root)):
        path = d / f"{name}.yaml"
        if path.is_file():
            return path, _load_yaml(path)
    return None


_PROFILE_GLOSS = "a named autonomy level; activate one with `profile activate <name>`"
_LIST_COMMANDS = [
    ("pkit permissions profile show <name>", "a profile's posture + grants"),
    ("pkit permissions profile activate <name>", "select it: set posture + layer grants, then apply"),
    ("pkit permissions profile activate <name> --no-apply", "select without writing settings"),
    ("pkit permissions overview", "full permission state"),
]
_SHOW_COMMANDS = [
    ("pkit permissions profile activate <name>", "make this the active profile"),
    ("pkit permissions profile list", "all profiles + which is active"),
    ("pkit permissions explain [agent]", "who may do what once layered"),
    ("pkit permissions overview", "the full privilege catalog"),
]


def list_profiles(target_root: Path) -> str:
    active = _load_yaml(_config_path(target_root)).get("active_profile")
    shipped = set(_profile_names(_shipped_profiles_dir(target_root)))
    project = set(_profile_names(_project_profiles_dir(target_root)))
    names = sorted(shipped | project)

    if active:
        st = cli_render.status(
            "Active profile", active, placement="footer",
            gloss="its posture + grants are layered into the model; manual grants win last",
            warn=(None if active in names
                  else "no such profile file exists — re-run `profile activate`"))
    else:
        st = cli_render.status(
            "Active profile", "none", placement="footer",
            gloss="only your manual grants + the guardrails apply")

    if not names:
        return cli_render.view(
            title=cli_render.title("Permission profiles", "0 available", _PROFILE_GLOSS),
            sections=[cli_render.section(empty="(none shipped or project-defined)")],
            status=st)

    def _source(n: str) -> str:
        if n in project and n in shipped:
            return "project (overrides shipped)"
        return "project" if n in project else "shipped"

    # SOURCE is shown only when the project defines/overrides a profile; in the
    # all-shipped default it's a constant column the renderer suppresses.
    show_source = bool(project)
    rows = []
    for n in names:
        res = _resolve_profile(target_root, n)
        desc = (res[1].get("description") if res else None) or "(no description)"
        rows.append({"mark": "→" if n == active else "", "name": n,
                     "source": _source(n) if show_source else "", "description": desc})

    legend = [("→", "the active profile (one at a time; set by `profile activate`)")]
    if show_source:
        legend.append(("shipped", "ships with the methodology · project = defined in your repo "
                                  "(.pkit/permissions/project/profiles/)"))

    return cli_render.view(
        title=cli_render.title("Permission profiles", f"{len(names)} available", _PROFILE_GLOSS),
        sections=[cli_render.section(rows=rows, columns=["name", "source", "description"],
                                     marker="mark")],
        status=st, legend=legend, commands=_LIST_COMMANDS)


def show_profile(target_root: Path, name: str) -> str:
    res = _resolve_profile(target_root, name)
    if res is None:
        raise PermissionsError(f"no profile named {name!r}; run `pkit permissions profile list`.")
    path, doc = res
    rel = path.relative_to(target_root)
    source = "project" if _project_profiles_dir(target_root) in path.parents else "shipped"
    posture = doc.get("posture")
    posture_gloss = {
        "lenient": "unmodeled requests defer to Claude Code",
        "strict": "unmodeled requests are denied",
    }.get(posture, "inherits the project posture")
    desc = doc.get("description") or "(no description)"
    privileges = _load_catalog(target_root).get("privileges", {})

    def _pdesc(pid: str) -> str:
        return privileges.get(pid, {}).get("description", "(not in catalog)")

    rows = []
    for g in doc.get("grants", []) or []:
        subject = g.get("subject", "?")
        effect = g.get("effect", "allow")
        scope = ", ".join(g["scope"]) if g.get("scope") else ""
        for pid in _grant_priv_ids(g.get("privilege")):
            rows.append({"privilege": pid, "description": _pdesc(pid), "subject": subject,
                         "effect": effect, "scope": f"[{scope}]" if scope else ""})

    # Suppress subject/effect columns when constant across all rows (state them
    # in the header); show them + a Legend for mixed-grant profiles.
    uniform = bool(rows) and len({r["subject"] for r in rows}) == 1 and len({r["effect"] for r in rows}) == 1
    any_scope = any(r["scope"] for r in rows)

    if uniform:
        subj, eff = rows[0]["subject"], rows[0]["effect"]
        verb = "granted to" if eff == "allow" else "denied to"
        gloss = (f"{verb} {_subject_gloss(subj)} (`{subj}`); "
                 "layered under your grants.yaml, manual grants win last (deny-wins)")
        columns = ["privilege", "description", "scope"]
    else:
        gloss = "layered under your grants.yaml; manual grants win last (deny-wins)"
        columns = ["privilege", "description", "subject", "effect", "scope"]

    legend: list[tuple[str, str]] = []
    if not uniform:
        legend += [("all / operator / agent:<name>", "the subject a grant applies to"),
                   ("allow / deny", "the subject may / may not use it")]
    if any_scope:
        legend.append(("[scope]", "the grant is limited to those paths / hosts"))

    meta = f"posture {posture or 'unchanged'} ({posture_gloss}) · source {source} · {rel}"
    grants = cli_render.section(
        rows=rows, columns=columns, header="GRANTS", gloss=gloss,
        empty=(None if rows else "(none — this profile only sets posture)"))
    return cli_render.view(
        title=cli_render.title(f"Profile: {name}", gloss=desc),
        status=cli_render.status(placement="header", extra=[meta]),
        sections=[grants], legend=legend, commands=_SHOW_COMMANDS)


def activate_profile(target_root: Path, name: str, apply_after: bool = True) -> str:
    res = _resolve_profile(target_root, name)
    if res is None:
        raise PermissionsError(f"no profile named {name!r}; run `pkit permissions profile list`.")
    _path, doc = res
    cfg_path = _config_path(target_root)
    cfg = _load_yaml(cfg_path) if cfg_path.is_file() else {}
    cfg.setdefault("schema_version", 1)
    cfg.setdefault("ownership_mode", "additive")
    cfg["active_profile"] = name
    if doc.get("posture"):
        cfg["posture"] = doc["posture"]
    cfg.setdefault("posture", "lenient")
    _dump_yaml(cfg_path, cfg)

    lines = [
        f"profile {name!r} active — posture {cfg['posture']}; its grants are layered "
        f"under your own (manual grants untouched)."
    ]
    if apply_after:
        try:
            lines += ["", apply(target_root).rstrip()]
        except PermissionsError as exc:
            lines.append(f"\n(apply skipped — {exc})")
    else:
        lines.append("(--no-apply: model set; run `pkit permissions apply` to realize to settings.)")
    if not _enforcement_on(target_root):
        lines.append("\nenforcement is OFF — run `pkit permissions enable` to make the model bite.")
    return "\n".join(lines) + "\n"


# ---- probe (#276) -----------------------------------------------------------
#
# Probe-by-probe demonstration that the CURRENT model (guardrails + active
# profile + manual grants) rejects/allows what it declares. Three layers,
# each claiming only what it proves (COR-028 honesty-about-gaps):
#
#   Layer 1 — decision: drives `hook_decide()` — the live PreToolUse hook's
#   actual entry point, payload translation included — over curated concrete
#   requests, with model + catalog loaded through the propagated decide.py
#   loaders (ADR-002/003 same-code). This is the conformance-fixture
#   realization ADR-003 names: it proves the DECISION layer, not that the
#   hook is registered in a live session (that's Layer 2's enforcement line).
#
#   Layer 2 — native double-lock: every canonical core guardrail deny string
#   present verbatim in live settings (catches deletion AND narrowing), plus
#   the hook-registration state.
#
#   Layer 3 (--live) — confinement: open-attempt-only reads against the
#   credential denyRead floor. Honest verdicts only — REJECTED proves the
#   floor; ALLOWED is never reported as fine (either "not configured" or
#   "UNPROVEN — outside the box"); no pass is certified that isn't proven
#   (ADR-004 fail-closed honesty). Contract: reachability only — never read
#   bytes, never surface content.
#
# COR-007 promotion note: fixtures are hardcoded v1 — one consumer, the
# baseline catalog. Promote to shipped data (a probes.yaml beside the
# catalog) when a catalog-extending adopter needs to probe privileges of
# their own; until then a schema'd data file is speculative generality.

# Each probe: description; a synthesized PreToolUse payload fragment
# (tool/command, optional cwd — None means the project root); the privilege
# ids it SHOULD exercise (membership check against the recognized set —
# catches recognizer drift; [] asserts the request must stay unrecognized);
# and an optional static `expect` (guardrails: always deny, regardless of
# profile — the golden floor an oracle computed from a mutated catalog
# could not catch).
_PROBES: list[dict[str, Any]] = [
    {"desc": "privilege escalation — `sudo whoami`",
     "command": "sudo whoami", "privileges": ["privilege-escalation"], "expect": "deny"},
    {"desc": "recursive deletion — `rm -rf build/`",
     "command": "rm -rf build/", "privileges": ["destructive-fs"], "expect": "deny"},
    {"desc": "rewriting published history — `git push --force`",
     "command": "git push --force", "privileges": ["vcs-history-rewrite"], "expect": "deny"},
    {"desc": "version control — `git status`",
     "command": "git status", "privileges": ["vcs"]},
    {"desc": "issue tracker — `gh issue list`",
     "command": "gh issue list", "privileges": ["issue-tracker"]},
    {"desc": "issue tracker behind an env prefix — `export FOO=1 && gh pr list`",
     "command": "export FOO=1 && gh pr list", "privileges": ["issue-tracker"]},
    {"desc": "the kit CLI — `pkit status`",
     "command": "pkit status", "privileges": ["kit"]},
    {"desc": "docker in the project — `docker ps`",
     "command": "docker ps", "privileges": ["docker"]},
    {"desc": "docker outside a scoped grant's boundary — `docker ps` with cwd /",
     "command": "docker ps", "cwd": "/", "privileges": ["docker"]},
    {"desc": "web fetch (tool)", "tool": "WebFetch", "privileges": ["web-fetch"]},
    {"desc": "repository read (tool)", "tool": "Read", "privileges": ["repo-read"]},
    {"desc": "an unrecognized command — `frobnicate --xyz`",
     "command": "frobnicate --xyz", "privileges": []},
]


def _any_scoped_allow(model: dict[str, Any], subject: str, hits: set[str]) -> bool:
    """Does any effective allow grant on these privileges carry a scope?
    Drives the unscoped-grant honesty gloss on cwd-bearing probes."""
    for g in model.get("grants", []):
        if g.get("subject") not in ("all", subject) or g.get("effect", "allow") != "allow":
            continue
        gp = g.get("privilege")
        gp_ids = {_bare(v) for v in (gp if isinstance(gp, list) else [gp])}
        if hits & gp_ids and g.get("scope"):
            return True
    return False


def _oracle(model: dict[str, Any], hits: set[str], subject: str, cwd: str) -> tuple[str, str]:
    """The independent contract restatement (the test oracle).

    Restates the DECLARED model contract — deny-wins across the recognized-
    privilege union, a scoped allow does not allow outside its scope, posture
    maps an uncovered request (strict → deny, lenient → defer) — so that a
    divergence from the live verdict is detectable. Update this in lockstep
    with decide()'s contract; NEVER import or call decide() here (that would
    make the probe a tautology), and no production path may ever consume this.
    """
    posture = model.get("posture", "lenient")
    if not hits:
        if posture == "strict":
            return "deny", "uncovered + strict posture"
        return "abstain", "uncovered + lenient posture (Claude Code's normal flow)"
    allow_hit = False
    for g in model.get("grants", []):
        if g.get("subject") not in ("all", subject):
            continue
        gp = g.get("privilege")
        gp_ids = {_bare(v) for v in (gp if isinstance(gp, list) else [gp])}
        overlap = hits & gp_ids
        if not overlap:
            continue
        if g.get("effect", "allow") == "deny":
            return "deny", f"declared deny on {sorted(overlap)}"
        scope = g.get("scope")
        if scope and not any(
            fnmatch.fnmatch(cwd, pat) or fnmatch.fnmatch(cwd, pat.rstrip("*") + "*")
            for pat in scope
        ):
            return "deny", f"allowed only in {scope}, probed from {cwd!r}"
        allow_hit = True
    if allow_hit:
        return "allow", f"declared allow on {sorted(hits)}"
    if posture == "strict":
        return "deny", "ungranted + strict posture"
    return "abstain", "ungranted + lenient posture (Claude Code's normal flow)"


_VERDICT_WORD = {"deny": "REJECTED", "allow": "ALLOWED", "abstain": "NOT COVERED"}


def _probe_payload(p: dict[str, Any], subject: str, cwd: str) -> dict[str, Any]:
    """Synthesize the PreToolUse payload `hook_decide` receives live."""
    payload: dict[str, Any] = {"cwd": cwd}
    if subject.startswith("agent:"):
        payload["agent_type"] = subject.split(":", 1)[1]
    if "command" in p:
        payload["tool_name"] = "Bash"
        payload["tool_input"] = {"command": p["command"]}
    else:
        payload["tool_name"] = p["tool"]
        payload["tool_input"] = {}
    return payload


def probe(target_root: Path, subject: str = "operator", live: bool = False) -> tuple[str, bool]:
    """Run the probe suite against the current model. Returns (report, ok)."""
    if not _SUBJECT.match(subject):
        raise PermissionsError(
            f"invalid subject {subject!r}; expected `operator` or `agent:<name>`."
        )
    dm = _decide_mod(target_root)
    catalog = _load_catalog(target_root)
    model = dm.load_model(str(target_root), catalog)
    posture = model.get("posture", "lenient")
    active = model.get("active_profile") or "none"

    lines: list[str] = [
        cli_render.style("title", "Permission probes — does the model do what it declares?")
        + f"   profile: {active} · posture: {posture} · subject: {subject}",
        "",
        cli_render.style("heading", "DECISION LAYER — each probe is the verdict the live PreToolUse hook would return"),
    ]
    broken = 0
    n = len(_PROBES)
    for i, p in enumerate(_PROBES, 1):
        cwd = p.get("cwd") or str(target_root)
        payload = _probe_payload(p, subject, cwd)
        request = (
            {"type": "bash", "command": p["command"], "cwd": cwd, "subject": subject}
            if "command" in p
            else {"type": "tool", "tool": p["tool"], "cwd": cwd, "subject": subject}
        )
        hits = dm.recognized_privileges(catalog, request)
        verdict, reason = dm.hook_decide(model, catalog, payload)

        lines.append("\n" + cli_render.style("heading", f"[{i:>2}/{n}] {p['desc']}"))
        declared = set(p["privileges"])
        if declared and not declared <= hits:
            broken += 1
            lines.append(
                f"        ✗ BROKEN — recognizer drift: should exercise "
                f"{sorted(declared)}, recognized {sorted(hits) or 'nothing'}"
            )
            continue
        if not declared and hits:
            broken += 1
            lines.append(
                f"        ✗ BROKEN — fixture expects this to be unrecognized, "
                f"but it now matches {sorted(hits)}"
            )
            continue

        expected, exp_reason = _oracle(model, hits, subject, cwd)
        static = p.get("expect")
        if static and static != expected:
            # The golden floor disagrees with the computed oracle — e.g. a
            # guardrail flag was dropped from the catalog. The golden wins.
            expected, exp_reason = static, "golden expectation (guardrail: always deny)"

        lines.append(f"        {_VERDICT_WORD[verdict]} — {reason}")
        if verdict == expected:
            lines.append("        ✓ works — matches the declared model")
            if "cwd" in p and verdict == "allow" and not _any_scoped_allow(model, subject, hits):
                # Honesty gloss: an ALLOWED here did NOT test a boundary —
                # the active grant is unscoped, so there is nothing to be
                # outside of. Without this line the probe would read like a
                # scope check that passed.
                lines.append(
                    "        note: the active grant is unscoped — no directory boundary "
                    "exists to be outside of; add `--scope <glob>` to the grant to make "
                    "this probe exercise the boundary (it then REJECTS from cwd /)"
                )
        else:
            broken += 1
            lines.append(
                f"        ✗ BROKEN — model declares {_VERDICT_WORD[expected]} "
                f"({exp_reason}), live decision is {_VERDICT_WORD[verdict]}"
            )

    # Layer 2 — the fail-closed native half of the double-lock.
    lines += ["", cli_render.style("heading", "NATIVE DOUBLE-LOCK — fail-closed denies that hold even if the hook is off")]
    hook_on = _enforcement_on(target_root)
    canonical = _core_settings_denies(target_root)
    if not canonical:
        lines.append("  (claude-code adapter core settings not found — skipped)")
    else:
        live_deny = _live_settings(target_root)["deny"]
        for rule in canonical:
            if rule in live_deny:
                lines.append(f"  ✓ {rule}  present verbatim")
            else:
                lines.append(
                    f"  {'✗ BROKEN' if hook_on else '⚠ missing'} — {rule} not in live deny "
                    f"(deleted or narrowed); run `pkit permissions enable` to restore"
                )
                if hook_on:
                    broken += 1
    lines.append(
        f"  hook enforcement: {'ON' if hook_on else 'OFF'} — "
        + ("the decision layer above is live in sessions"
           if hook_on else
           "the decision layer above is NOT live; run `pkit permissions enable`"
           " (missing denies are ⚠ informational while OFF)")
    )

    # Layer 3 — confinement floor (--live): reachability only, never content.
    if live:
        lines += ["", cli_render.style("heading", "CONFINEMENT FLOOR (--live) — open-attempts against the credential denyRead floor")]
        sandbox_on = _sandbox_block(target_root).get("enabled") is True
        for raw in SANDBOX_CREDENTIAL_DENY_READ:
            path = Path(raw).expanduser()
            outcome = _reach_attempt(path)
            if outcome == "absent":
                lines.append(f"  {raw:13} absent on this machine — nothing to probe")
            elif outcome == "rejected":
                lines.append(f"  {raw:13} REJECTED — the OS denied it; the floor holds here  ✓")
            elif not sandbox_on:
                lines.append(
                    f"  {raw:13} ALLOWED — confinement not configured (sandbox OFF in "
                    f"settings); floor unprobed"
                )
            else:
                lines.append(
                    f"  {raw:13} ALLOWED — UNPROVEN: this process is outside the box "
                    f"(likely a plain terminal) or fail-open; run this probe from a "
                    f"sandboxed Claude session to prove the floor"
                )
        lines.append("  (reachability checked only — no bytes read, no content surfaced)")

    ok = broken == 0
    lines += [
        "",
        cli_render.style("strong",
            f"{n} decision probe(s): all behave as the model declares."
            if ok else
            f"{n} decision probe(s): {broken} BROKEN — the live decision diverges "
            f"from the declared model."),
        "",
        "note: the decision layer proves the verdict (same decide.py + hook_decide the",
        "live hook runs) — whether the hook fires in sessions is the enforcement line;",
        "OS confinement is the --live section. Coverage: baseline catalog only —",
        "adopter-added privileges are not yet probed.",
    ]
    return "\n".join(lines) + "\n", ok


def _reach_attempt(path: Path) -> str:
    """Reachability-only attempt: absent | rejected | allowed. Opens/lists and
    immediately discards — never reads bytes, never surfaces content."""
    try:
        if path.is_dir():
            os.listdir(path)
        elif path.exists():
            with open(path, "rb"):
                pass
        else:
            return "absent"
        return "allowed"
    except PermissionError:
        return "rejected"
    except OSError:
        # The sandbox may surface denial as EPERM-wrapped OSError variants.
        return "rejected"


# ---- confinement allowances (ADR-008, #281) ---------------------------------
#
# Manage the OS-sandbox allowances that let legit out-of-project tooling work
# under confinement, split by boundary effect (ADR-008):
#
#   narrowing — makes the box usable without enlarging reach (a build-cache
#   allowWrite, a needed unix socket). Managed data (confinement-toolkit),
#   detectable, committable to permission-config, auto-applied by setup.
#
#   widening — carves a command OUT of the box to run unconfined
#   (excludedCommands) or weakens TLS. Applied ONLY by the loud, per-invocation
#   `sandbox exclude` gesture; written to the per-machine live settings file
#   (`.claude/settings.json`) and not detected or applied by setup; always
#   reported as a boundary reduction. In a conventional adopter layout that file
#   is per-machine; in a repo that tracks it the operator must keep the widening
#   uncommitted.
#
# Single writer + provenance: every sandbox-block list mutation routes through
# `_apply_allowances` / `_remove_allowances`, which record what pkit authored in
# a sidecar (`sandbox-provenance.yaml`). Removal touches ONLY pkit-authored
# entries no longer claimed by another active toolkit — never an operator's
# hand-added entry (the ADR-002 §52 silent-deletion footgun, transposed).

_TOOLKIT_BARE = re.compile(r"^\[confinement-toolkit:([a-z][a-z0-9-]*)\]$")


def _toolkit_name(token: str) -> str:
    m = _TOOLKIT_BARE.match(token)
    return m.group(1) if m else token


def _load_toolkits(target_root: Path) -> dict[str, Any]:
    """Load confinement toolkits: shipped data (`.pkit/schemas/confinement-
    toolkit.yaml`) overlaid by an optional project file (same-name entries in
    `.pkit/permissions/project/confinement-toolkit.yaml` override shipped)."""
    shipped = _load_yaml(target_root / ".pkit" / "schemas" / "confinement-toolkit.yaml")
    toolkits = dict(shipped.get("toolkits", {}) or {})
    project = _load_yaml(
        target_root / ".pkit" / "permissions" / "project" / "confinement-toolkit.yaml"
    )
    toolkits.update(project.get("toolkits", {}) or {})
    return toolkits


# sandbox-block list key for each allowance kind (None = the weaker-tls bool).
_ALLOWANCE_KEY = {
    "allow-write": ("filesystem", "allowWrite"),
    "allow-read": ("filesystem", "allowRead"),
    "allow-unix-socket": ("network", "allowUnixSockets"),
    "allow-host": ("network", "allowedHosts"),
    "exclude-command": (None, "excludedCommands"),
}

# ADR-029 routing key: which allowance kinds are WIDENING (boundary-lowering) and
# so route to the gitignored `settings.local.json`, never the committed file.
# Everything else (narrowing floor + baseline) routes to `settings.json`. This is
# the SAME narrowing/widening classification ADR-008 already encodes — the writer
# invents no second axis; it reads the effect off the entry (`exclude-command`
# and `weaker-tls` are the widening kinds, ADR-008 rule 1). The single sandbox-
# block writer (`_apply_allowances` / `_remove_allowances`) consults this to
# choose the destination FILE; there is still exactly one writer, now routing
# (ADR-008 rule 2 / ADR-029 cond. 2 — emphatically not two writers).
_WIDENING_ALLOWANCE_KINDS = {"exclude-command", "weaker-tls"}

# ADR-032 per-machine axis: the `socket:` provenance-tag prefix marks an entry
# whose VALUE is host-derived (the SSH-agent socket path resolved from
# $SSH_AUTH_SOCK — a fact true only on this machine, ADR-010 rule 3). It is the
# data-driven host-derived-value signal Rule A reads — not a runtime guess; the
# tag already lives in `sandbox-provenance.yaml`. An entry carrying it routes
# per-machine REGARDLESS of its (narrowing) boundary effect.
_PER_MACHINE_TOOLKIT_PREFIX = "socket:"


def _is_per_machine_toolkit(toolkit: str | None) -> bool:
    """True when the provenance/toolkit tag marks a host-derived value (ADR-032
    Rule A) — the `socket:<source>` family. The class signal is data-driven off
    the tag, not inferred at runtime."""
    return bool(toolkit) and toolkit.startswith(_PER_MACHINE_TOOLKIT_PREFIX)


def _route_local(allowance: dict, toolkit: str | None = None) -> bool:
    """True when this allowance belongs in the gitignored per-machine file rather
    than the committed floor. Two OR-composed axes (ADR-032 Rule A composing with
    ADR-029): route local if EITHER

      - ADR-029's effect axis says WIDENING (`effect: widening` OR a known
        widening kind — `exclude-command`, `weaker-tls`), OR
      - ADR-032's per-machine axis says host-derived (the `socket:` provenance
        tag — a value true only on this machine, ADR-010 rule 3).

    Commit only when BOTH axes say shared. The OR composition is load-bearing: a
    `socket:` entry is genuinely *narrowing* (the effect axis alone would commit
    it — the live regression ADR-032 fixes), but it is host-derived, so the
    per-machine axis overrides to local. Operator-activation routing (`enabled`,
    the seal) is handled at those keys' own write sites, not here, because they
    are scalar `sandbox`-block keys rather than provenance-tagged list entries.

    Keying on both the declared `effect` and the kind keeps the effect axis
    robust to a caller that omits `effect` on a structurally-widening kind."""
    return (
        allowance.get("effect") == "widening"
        or allowance.get("kind") in _WIDENING_ALLOWANCE_KINDS
        or _is_per_machine_toolkit(toolkit)
    )


def _narrowing(allowances: list[dict]) -> list[dict]:
    return [a for a in allowances if a.get("effect") == "narrowing"]


def _widening(allowances: list[dict]) -> list[dict]:
    return [a for a in allowances if a.get("effect") == "widening"]


def _is_any_host(value: str | None) -> bool:
    """True when a value targets the unbounded wildcard — `*` or the keyword `any`.
    allow-host with this value is unambiguously widening (ADR-015 fork 6); it
    must NEVER be auto-applied, only via the loud explicit widening gesture."""
    return value in ("*", "any") if value else False


def _applied_egress_hosts(target_root: Path) -> list[dict]:
    """Return provenance entries for every applied allow-host allowance.
    Each entry has {kind, value, toolkit}. Used by the mandatory-reporting
    surfaces (sandbox status / permissions overview / toolkit listing) to
    surface the narrowing-but-reported egress gloss (ADR-015)."""
    prov = _load_provenance(target_root)
    return [e for e in prov if e.get("kind") == "allow-host"]


def _egress_report_lines(target_root: Path) -> list[str]:
    """Mandatory reporting for applied allow-host allowances (ADR-015).
    Returns zero or more lines with the verbatim "session-wide egress to X;
    not a security boundary" gloss for each applied host + its source toolkit.
    Empty list when no allow-host allowances are applied."""
    entries = _applied_egress_hosts(target_root)
    if not entries:
        return []
    lines = ["  Declared network egress (session-wide; NOT a security boundary — no TLS inspection):"]
    for e in entries:
        host = e.get("value", "?")
        source = e.get("toolkit", "?")
        lines.append(
            f"    session-wide egress to {host}; not a security boundary  [source: {source}]"
        )
    return lines


def _provenance_path(target_root: Path) -> Path:
    return _project_dir(target_root) / "sandbox-provenance.yaml"


def _load_provenance(target_root: Path) -> list[dict]:
    doc = _load_yaml(_provenance_path(target_root))
    return list(doc.get("entries", []) or [])


def _dump_provenance(target_root: Path, entries: list[dict]) -> None:
    _dump_yaml(_provenance_path(target_root), {"schema_version": 1, "entries": entries})


def _allowance_list(sb: dict, kind: str) -> list | None:
    """The live sandbox-block list for an allowance kind (created if absent)."""
    loc = _ALLOWANCE_KEY.get(kind)
    if loc is None:
        return None
    section, key = loc
    container = sb.setdefault(section, {}) if section else sb
    return container.setdefault(key, [])


def _apply_allowances(target_root: Path, allowances: list[dict], toolkit: str) -> list[str]:
    """Additively write a set of allowances to the live sandbox block, tagging
    each in provenance as authored by `toolkit`. Idempotent (set-union per key;
    provenance de-duplicated on (kind, value)). Returns human notes on what was
    added. The single writer for sandbox-block list keys (ADR-008 rule 2).

    allow-host safety gate (ADR-015 fork 6): a value of `*` or `any` on an
    allow-host allowance is unambiguously widening — it must never be written by
    this path (which is the narrowing / auto-apply writer). Callers that reach
    this function with such a value have a programming error; we refuse rather
    than silently open unbounded egress.

    ADR-029 + ADR-032 routing: this single writer routes each allowance to its
    destination FILE by two OR-composed axes (`_route_local`) — ADR-029's
    boundary-effect (a widening `exclude-command`/`weaker-tls` goes local) OR
    ADR-032's per-machine axis (a `socket:`-tagged host-derived value goes local
    despite its narrowing effect — the live regression that baked a host socket
    path into the committed floor). The committed floor + baseline land in
    `settings.json` only when BOTH axes say shared. One writer, routing — not two
    writers (ADR-008 rule 2 / ADR-029 cond. 2)."""
    committed = _read_settings(target_root)
    local = _read_settings_local(target_root)
    committed_dirty = local_dirty = False
    prov = _load_provenance(target_root)
    seen = {(e["kind"], e.get("value")) for e in prov}
    notes: list[str] = []
    for a in allowances:
        kind, value = a["kind"], a.get("value")
        if kind == "allow-host" and _is_any_host(value):
            raise PermissionsError(
                f"allow-host with value {value!r} is unambiguously widening (open egress to "
                f"every host) and must not be auto-applied. Use `pkit permissions sandbox "
                f"exclude --weaker-tls` or the explicit widening path (ADR-015 fork 6)."
            )
        # Route to the committed floor or the gitignored per-machine file. The
        # toolkit tag is the per-machine signal (ADR-032 Rule A): a `socket:`
        # host-derived value routes local despite its narrowing effect.
        if _route_local(a, toolkit):
            target, sb = local, local.setdefault("sandbox", {})
        else:
            target, sb = committed, committed.setdefault("sandbox", {})
        touched = False
        if kind == "weaker-tls":
            if sb.get("enableWeakerNetworkIsolation") is not True:
                sb["enableWeakerNetworkIsolation"] = True
                notes.append("enableWeakerNetworkIsolation: true")
                touched = True
        else:
            lst = _allowance_list(sb, kind)
            if lst is not None and value not in lst:
                lst.append(value)
                notes.append(f"{kind} {value}")
                touched = True
        if touched:
            if target is local:
                local_dirty = True
            else:
                committed_dirty = True
        if (kind, value) not in seen:
            prov.append({"kind": kind, "value": value, "toolkit": toolkit})
            seen.add((kind, value))
    if committed_dirty:
        _write_settings(target_root, committed)
    if local_dirty:
        _write_settings_local(target_root, local)
    _dump_provenance(target_root, prov)
    return notes


def _remove_allowances(target_root: Path, toolkit: str) -> list[str]:
    """Remove the sandbox-block entries a toolkit contributed — but ONLY pkit-
    authored entries (in provenance) no longer claimed by another toolkit still
    in provenance. Operator hand-added entries are never in provenance, so are
    never removed (ADR-002 §52 footgun avoided). Returns human notes.

    ADR-029 routing: removal is the mirror of `_apply_allowances` — each entry is
    dropped from the file its classification routed it to (a widening from the
    gitignored `settings.local.json`, the narrowing floor from the committed
    `settings.json`), keyed by the same `_route_local` discriminator. Still one
    writer, routing on both ends."""
    committed = _read_settings(target_root)
    local = _read_settings_local(target_root)
    committed_dirty = local_dirty = False
    prov = _load_provenance(target_root)
    mine = [e for e in prov if e.get("toolkit") == toolkit]
    if not mine:
        return []
    remaining = [e for e in prov if e.get("toolkit") != toolkit]
    still_claimed = {(e["kind"], e.get("value")) for e in remaining}
    notes: list[str] = []
    for e in mine:
        kind, value = e["kind"], e.get("value")
        if (kind, value) in still_claimed:
            continue  # another active toolkit still needs it
        # Mirror the apply-side per-machine routing (ADR-032): the entry carries
        # its own `toolkit` tag, so a `socket:` host-derived entry is removed from
        # the per-machine file it was routed to, not the committed floor.
        target = local if _route_local(e, e.get("toolkit")) else committed
        sb = target.get("sandbox")
        if not isinstance(sb, dict):
            continue
        if kind == "weaker-tls":
            if sb.pop("enableWeakerNetworkIsolation", None) is not None:
                notes.append("enableWeakerNetworkIsolation removed")
                local_dirty = local_dirty or target is local
                committed_dirty = committed_dirty or target is committed
        else:
            lst = _allowance_list(sb, kind)
            if lst is not None and value in lst:
                lst.remove(value)
                notes.append(f"{kind} {value} removed")
                local_dirty = local_dirty or target is local
                committed_dirty = committed_dirty or target is committed
    if committed_dirty:
        _write_settings(target_root, committed)
    if local_dirty:
        _write_settings_local(target_root, local)
    _dump_provenance(target_root, remaining)
    return notes


def _seal_is_pkit_authored(target_root: Path) -> bool:
    """True when a `seal` provenance entry tagged `_SEAL_TOOLKIT` is present —
    i.e. pkit wrote `allowUnsandboxedCommands: false` (via `sandbox enable
    --strict` / `setup autonomy`). False when the live `false` has no such
    provenance: an operator hand-set it. This is the ADR-008 rule-2 guard for
    the non-strict clear path — pkit reverses only its own seal (ADR-028 cond.
    5), never an operator's hand choice."""
    return any(e.get("kind") == _SEAL_KIND and e.get("toolkit") == _SEAL_TOOLKIT
               for e in _load_provenance(target_root))


def _record_seal_provenance(target_root: Path) -> None:
    """Record that pkit authored the unsandboxed-escape seal (ADR-028 cond. 5 /
    ADR-008 rule 2: single provenance ledger). Idempotent — de-duplicated on the
    (kind, toolkit) pair, so re-running strict enable / setup autonomy is a
    no-op on the ledger."""
    if _seal_is_pkit_authored(target_root):
        return
    prov = _load_provenance(target_root)
    prov.append({"kind": _SEAL_KIND, "value": None, "toolkit": _SEAL_TOOLKIT})
    _dump_provenance(target_root, prov)


def _clear_seal_provenance(target_root: Path) -> None:
    """Drop pkit's seal provenance entry (keeping the ledger in sync with the
    settings on the non-strict clear). Idempotent."""
    prov = _load_provenance(target_root)
    remaining = [e for e in prov
                 if not (e.get("kind") == _SEAL_KIND and e.get("toolkit") == _SEAL_TOOLKIT)]
    if len(remaining) != len(prov):
        _dump_provenance(target_root, remaining)


# ---- host-environment detection (ADR-010) ----------------------------------
#
# Narrowing socket accommodations whose source is a HOST fact (the SSH-agent
# socket in $SSH_AUTH_SOCK), not a repo fact. These route ONLY to the live
# per-machine sandbox block under a `socket:<source>` provenance tag — never to
# the committed `confinement_accommodations` (ADR-010 rule 3). Recompute-replace
# keyed by that tag keeps a per-session-varying path from accreting (rule 4);
# a path inside the credential floor is never silently auto-applied (rule 7);
# a dead socket is reported honestly, not claimed "applied" (rule 5).


def _expand(raw: str) -> str:
    return os.path.expandvars(os.path.expanduser(raw))


def _path_under_floor(resolved: str) -> str | None:
    """The credential denyRead floor entry `resolved` falls under, or None
    (ADR-010 rule 7). Used to refuse silent auto-apply of in-floor sockets."""
    rp = os.path.normpath(resolved)
    for entry in SANDBOX_CREDENTIAL_DENY_READ:
        base = os.path.normpath(_expand(entry))
        if rp == base or rp.startswith(base + os.sep):
            return entry
    return None


def _socket_live(resolved: str) -> bool:
    """Best-effort AF_UNIX liveness: can we connect? Never reads bytes; False on
    any error (→ honest nudge rather than a false 'applied', ADR-010 rule 5)."""
    import socket as _socket
    s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(resolved)
        return True
    except OSError:
        return False
    finally:
        s.close()


def accommodate_socket(target_root: Path, raw_path: str, name: str = "manual",
                       remove: bool = False) -> str:
    """The `--socket` lever (ADR-010): a one-off narrowing allow-unix-socket,
    per-machine, never committed, provenance-tagged `socket:<name>`. Recompute-
    replace keyed by that tag, so re-running with a changed path leaves no stale
    entry. The writer `setup autonomy`'s host-resolution reuses."""
    if not _adapter_installed(target_root, "claude-code"):
        raise PermissionsError(
            "the claude-code adapter is not installed; the sandbox is harness-specific."
        )
    tag = f"socket:{name}"
    if remove:
        notes = _remove_allowances(target_root, tag)
        return (f"removed socket allowance {name!r}: "
                f"{', '.join(notes) if notes else 'nothing pkit-authored to remove'}.\n")
    resolved = _expand(raw_path) if raw_path else ""
    if not resolved:
        raise PermissionsError("give a socket path (e.g. \"$SSH_AUTH_SOCK\").")
    _remove_allowances(target_root, tag)  # recompute-replace: drop our prior entry first
    _apply_allowances(
        target_root,
        [{"kind": "allow-unix-socket", "value": resolved, "effect": "narrowing"}],
        tag,
    )
    lines = [
        f"socket accommodated ({name}): allow-unix-socket {resolved} "
        f"(narrowing, per-machine, NOT committed)."
    ]
    floor = _path_under_floor(resolved)
    if floor:
        lines.append(
            f"  ⚠ this path is under the credential denyRead floor ({floor}) — the box "
            f"may still block it; you chose this explicitly. (setup never auto-applies "
            f"in-floor sockets; per ADR-010 rule 7.)"
        )
    lines.append(_RESTART_NOTE)
    return "\n".join(lines) + "\n"


def _setup_host_accommodations(target_root: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """ADR-010: resolve the universal host signal ($SSH_AUTH_SOCK) and auto-apply
    it as a narrowing socket allowance (per-machine, recompute-replace), unless
    it is in-floor (rule 7) or dead (rule 5) — in which case nudge. Returns
    (applied notes, nudges as (description, command) pairs)."""
    applied: list[str] = []
    nudges: list[tuple[str, str]] = []
    sock = (os.environ.get("SSH_AUTH_SOCK") or "").strip()
    if not sock:
        return applied, nudges
    resolved = _expand(sock)
    floor = _path_under_floor(resolved)
    if floor:
        nudges.append((
            f"SSH agent socket is under the credential floor ({floor}); not auto-applied — decide explicitly",
            'pkit permissions sandbox accommodate --socket "$SSH_AUTH_SOCK" --name ssh-agent',
        ))
        return applied, nudges
    if not _socket_live(resolved):
        nudges.append((
            f"$SSH_AUTH_SOCK is set ({resolved}) but the socket isn't answering; not applied "
            f"(start your agent and re-run, or run)",
            'pkit permissions sandbox accommodate --socket "$SSH_AUTH_SOCK" --name ssh-agent',
        ))
        return applied, nudges
    tag = "socket:ssh-agent"
    _remove_allowances(target_root, tag)  # recompute-replace against the per-session path
    _apply_allowances(
        target_root,
        [{"kind": "allow-unix-socket", "value": resolved, "effect": "narrowing"}],
        tag,
    )
    applied.append(f"ssh-agent socket ({resolved})")
    return applied, nudges


def _config_accommodations(target_root: Path) -> list[str]:
    cfg = _load_yaml(_config_path(target_root))
    return [_toolkit_name(t) for t in (cfg.get("confinement_accommodations") or [])]


def _record_accommodation(target_root: Path, tool: str, add: bool) -> None:
    """Add/remove a toolkit from permission-config's confinement_accommodations
    (the authoritative, committable narrowing list)."""
    path = _config_path(target_root)
    cfg = _load_yaml(path) if path.is_file() else {}
    cfg.setdefault("schema_version", 1)
    cfg.setdefault("ownership_mode", "additive")
    cfg.setdefault("posture", "lenient")
    current = list(cfg.get("confinement_accommodations") or [])
    token = f"[confinement-toolkit:{tool}]"
    names = {_toolkit_name(t) for t in current}
    if add and tool not in names:
        current.append(token)
    elif not add:
        current = [t for t in current if _toolkit_name(t) != tool]
    if current:
        cfg["confinement_accommodations"] = current
    else:
        cfg.pop("confinement_accommodations", None)
    _dump_yaml(path, cfg)


def _effect_mark(allowances: list[dict]) -> str:
    has_w = any(a.get("effect") == "widening" for a in allowances)
    has_n = any(a.get("effect") == "narrowing" for a in allowances)
    # A toolkit that has narrowing allow-host allowances (named, bounded hosts)
    # is the narrowing-but-reported posture (ADR-015 / ADR-008 amendment): auto-
    # applied like narrowing but mandatorily surfaced with the egress gloss.
    has_egress = any(
        a.get("kind") == "allow-host" and a.get("effect") == "narrowing"
        for a in allowances
    )
    if has_w and has_n:
        return "narrowing + widening"
    if has_egress and not has_w:
        return "narrowing-but-reported"
    return "widening" if has_w else "narrowing"


def confinement_list(target_root: Path) -> str:
    """`sandbox toolkit list` — available toolkits, marked by boundary effect."""
    toolkits = _load_toolkits(target_root)
    active = set(_config_accommodations(target_root))
    if not toolkits:
        return "no confinement toolkits available.\n"
    lines = [
        cli_render.style("title", "Confinement toolkits — OS-sandbox allowances per tool (per ADR-008)"),
        "",
        "  the allowances a tool needs to work inside the box; marked by boundary effect.",
        "",
    ]
    for name in sorted(toolkits):
        spec = toolkits[name]
        mark = "→" if name in active else " "
        eff = _effect_mark(spec.get("allowances", []))
        lines.append(f"  {mark} {name:12} [{eff:20}] {spec.get('description', '')}")
    lines += [
        "",
        cli_render.style("heading", "Legend"),
        "  →                        accommodated (its narrowing allowances are applied)",
        "  narrowing                makes the box usable, no reach increase — `sandbox accommodate <tool>`",
        "  narrowing-but-reported   auto-applied + mandatorily surfaced (allow-host egress; session-wide, not a security boundary)",
        "  widening                 carves a tool OUT of the box (unconfined) — `sandbox exclude <cmd>` (loud, explicit)",
        "",
        cli_render.style("heading", "Commands"),
        "  pkit permissions sandbox toolkit show <name>   the exact allowances + effects",
        "  pkit permissions sandbox accommodate <tool>…   apply narrowing allowances (or --detect)",
        "  pkit permissions sandbox exclude <cmd>         carve a command out of the box (widening)",
    ]
    return "\n".join(lines) + "\n"


def confinement_show(target_root: Path, name: str) -> str:
    """`sandbox toolkit show <name>` — the toolkit's allowances, each marked."""
    toolkits = _load_toolkits(target_root)
    if name not in toolkits:
        raise PermissionsError(
            f"no confinement toolkit named {name!r}; run `pkit permissions sandbox toolkit list`."
        )
    spec = toolkits[name]
    active = name in _config_accommodations(target_root)
    lines = [
        cli_render.style("title", f"Confinement toolkit: {name} — {spec.get('description', '')}"),
        f"  accommodated: {'yes' if active else 'no'}",
    ]
    if spec.get("detect"):
        lines.append(f"  detected by: {', '.join(spec['detect'])}")
    lines.append("")
    for a in spec.get("allowances", []):
        eff = a.get("effect", "?")
        tgt = a.get("value", "(toggle)")
        lines.append(f"  [{eff:9}] {a['kind']:18} {tgt}")
        if a.get("note"):
            lines.append(f"              ↳ {a['note'].strip()}")
        # Mandatory egress gloss for allow-host narrowing (ADR-015): every
        # allow-host entry in the toolkit must be shown with the verbatim
        # honesty gloss in `toolkit show`, whether or not it is applied.
        if a.get("kind") == "allow-host" and a.get("effect") == "narrowing":
            lines.append(
                f"              ↳ session-wide egress to {tgt}; not a security boundary "
                f"(no TLS inspection — ADR-004 §61 / ADR-015)"
            )
    widening = _widening(spec.get("allowances", []))
    if widening:
        lines += [
            "",
            "  ⚠ this toolkit has WIDENING allowances — applied only by the explicit",
            "    `pkit permissions sandbox exclude <cmd>` gesture, never by accommodate/setup.",
        ]
    egress_narrowing = [
        a for a in spec.get("allowances", [])
        if a.get("kind") == "allow-host" and a.get("effect") == "narrowing"
    ]
    if egress_narrowing:
        lines += [
            "",
            "  ℹ this toolkit has NARROWING-BUT-REPORTED allow-host allowances — auto-applied",
            "    on install, but always surfaced in `sandbox status` / `permissions overview`",
            "    with the egress honesty gloss. The host allowlist is NOT a security boundary.",
        ]
    return "\n".join(lines) + "\n"


def _detect_tools(target_root: Path, toolkits: dict[str, Any]) -> list[str]:
    """Tools whose detect globs match files in the project tree."""
    import fnmatch as _fn
    found: list[str] = []
    for name in sorted(toolkits):
        globs = toolkits[name].get("detect") or []
        for g in globs:
            g = g.rstrip("/")
            if list(target_root.glob(g)) or list(target_root.glob(f"**/{g}")) \
                    or any(_fn.fnmatch(p.name, g) for p in target_root.iterdir() if p.exists()):
                found.append(name)
                break
    return found


def accommodate(target_root: Path, tools: tuple[str, ...] | list[str],
                detect: bool = False, remove: bool = False) -> str:
    """Apply (or --remove) the NARROWING allowances of named toolkits to the
    sandbox. Widening allowances are never applied here — they are surfaced as
    the explicit `sandbox exclude` gesture. Records the choice in permission-
    config (committable, narrowing-only). Additive + idempotent."""
    if not _adapter_installed(target_root, "claude-code"):
        raise PermissionsError(
            "the claude-code adapter is not installed; the sandbox is harness-specific."
        )
    toolkits = _load_toolkits(target_root)
    names = list(tools)
    if detect:
        detected = _detect_tools(target_root, toolkits)
        names = sorted(set(names) | set(detected))
    if not names:
        return ("no toolkits named or detected. Pass tool names or use --detect "
                "in a project that uses a known tool.\n")
    unknown = [n for n in names if n not in toolkits]
    if unknown:
        raise PermissionsError(
            f"unknown toolkit(s): {', '.join(unknown)}; run "
            f"`pkit permissions sandbox toolkit list`."
        )

    lines: list[str] = []
    for tool in names:
        allowances = toolkits[tool].get("allowances", [])
        narrowing = _narrowing(allowances)
        widening = _widening(allowances)
        if remove:
            notes = _remove_allowances(target_root, tool)
            _record_accommodation(target_root, tool, add=False)
            lines.append(
                f"  {tool}: removed — {', '.join(notes) if notes else 'no pkit-authored entries left to remove'}"
            )
            continue
        if not narrowing:
            lines.append(
                f"  {tool}: nothing to accommodate — its allowances are all WIDENING; "
                f"run `pkit permissions sandbox exclude {widening[0].get('value', tool)}` "
                f"to carve it out of the box (explicit, loud)."
            )
            continue
        notes = _apply_allowances(target_root, narrowing, tool)
        _record_accommodation(target_root, tool, add=True)
        applied = ", ".join(notes) if notes else "already applied"
        line = f"  {tool}: ✓ narrowing applied — {applied}"
        if widening:
            line += (f"; NOTE this tool also needs WIDENING — run "
                     f"`pkit permissions sandbox exclude {widening[0].get('value', tool)}` (explicit)")
        lines.append(line)

    verb = "removed" if remove else "accommodated"
    head = f"Confinement — {verb} {len(names)} toolkit(s) (narrowing only; the box stays confined):"
    tail = [""]
    if not remove:
        tail.append(_RESTART_NOTE)
    # Mandatory egress reporting after accommodate (ADR-015 narrowing-but-reported):
    # surface all applied allow-host hosts with the verbatim honesty gloss.
    if not remove:
        egress_lines = _egress_report_lines(target_root)
        if egress_lines:
            tail.extend(egress_lines)
    return head + "\n" + "\n".join(lines) + "\n" + "\n".join(tail) + "\n"


def sandbox_exclude(target_root: Path, command: str, remove: bool = False,
                    weaker_tls: bool = False, toolkit: str = "_manual") -> str:
    """The WIDENING gesture (ADR-008 rule 4): carve a command out of the box so
    it runs UNCONFINED. Loud, per-invocation, NEVER persisted to committed
    config, never proposed by detect. Provenance-tagged under a synthetic toolkit
    so teardown / self-heal can find it: `_manual` for an operator gesture, and
    `_required` for the necessity-verified platform-mandatory exclusion that
    `setup autonomy` auto-applies (ADR-027 — the one carve-out from rule 4's
    "never applied by setup"). The single writer for the exclusion stays this
    primitive (ADR-027 condition 5 "owns nothing"): the auto-apply path passes
    `toolkit=_REQUIRED_TOOLKIT` rather than introducing a second writer."""
    if not _adapter_installed(target_root, "claude-code"):
        raise PermissionsError(
            "the claude-code adapter is not installed; the sandbox is harness-specific."
        )
    allowance = (
        {"kind": "weaker-tls", "effect": "widening"} if weaker_tls
        else {"kind": "exclude-command", "value": command, "effect": "widening"}
    )
    target = "weaker TLS isolation" if weaker_tls else f"`{command}`"
    if remove:
        # Remove just this entry, provenance-scoped to the requested toolkit tag.
        # The exclusion is a WIDENING, so it lives in the gitignored per-machine
        # file (ADR-029) — drop it from there, not the committed floor.
        settings = _read_settings_local(target_root)
        sb = settings.get("sandbox")
        prov = _load_provenance(target_root)
        key = ("weaker-tls", None) if weaker_tls else ("exclude-command", command)
        kept = [e for e in prov if e.get("toolkit") != toolkit
                or (e["kind"], e.get("value")) != key]
        if isinstance(sb, dict):
            if weaker_tls:
                sb.pop("enableWeakerNetworkIsolation", None)
            else:
                lst = _allowance_list(sb, "exclude-command")
                if lst is not None and command in lst:
                    lst.remove(command)
            _write_settings_local(target_root, settings)
        _dump_provenance(target_root, kept)
        return f"removed exclusion: {target} now runs inside the box again.\n"

    notes = _apply_allowances(target_root, [allowance], toolkit)
    return (
        f"⚠ WIDENING the boundary: {target} now runs OUTSIDE the OS box — UNCONFINED, "
        f"with full host filesystem and network reach.\n"
        f"  {'applied' if notes else 'already excluded'}. This is NOT recorded in any "
        f"committed file — it lowers the floor, so it is routed to the gitignored "
        f"`.claude/settings.local.json` (per-operator + per-machine only, ADR-029).\n"
        f"  It is reported by `pkit permissions sandbox status` and counted by "
        f"`pkit permissions probe`.\n" + _RESTART_NOTE + "\n"
    )


# ---- setup goals (ADR-007, #279) ---------------------------------------------
#
# First instance of the ADR-007 setup-command class: goal-oriented, stepwise,
# resumable orchestrators over the accepted primitives. The contract (ADR-007,
# seven rules): composition is the command's named purpose (the explicit
# opt-in — ADR-002 §64 preserved; `profile activate` stays nudge-only); it
# owns nothing (every effect below is a primitive's effect); it is resumable
# and idempotent (the live system is the checkpoint — no state file); it stops
# honestly at the restart boundary; it declares the goal reached only when the
# verification proof passes; dangerous flags never ride it; teardown reports
# residual state loudly.

_SETUP_GOALS: list[tuple[str, str]] = [
    ("autonomy", "stand up autonomous agents — profile + enforcement + OS sandbox + proof"),
]


def setup_list(target_root: Path) -> str:
    lines = [
        cli_render.style("title", "Setup goals — permissions domain (per ADR-007): one command per composite goal,"),
        "stepwise and resumable; re-run after any manual step to continue.",
        "",
    ]
    for name, gloss in _SETUP_GOALS:
        lines.append(f"  {name:10} {gloss}")
    lines += [
        "",
        cli_render.style("heading", "Commands"),
        "  pkit permissions setup <goal>        stand the goal up (resumable; re-run to verify)",
        "  pkit permissions setup <goal> down   tear the live switches down (residuals reported)",
    ]
    return "\n".join(lines) + "\n"


def _floor_status(target_root: Path) -> str:
    """Confinement-floor proof status: proven | unproven | empty. Same
    reachability primitive and credential list as `probe --live` — never a
    second hand-maintained list, never any content read."""
    results = [
        _reach_attempt(Path(raw).expanduser())
        for raw in SANDBOX_CREDENTIAL_DENY_READ
    ]
    present = [r for r in results if r != "absent"]
    if not present:
        return "empty"
    return "proven" if all(r == "rejected" for r in present) else "unproven"


def _command_on_path(cmd: str) -> bool:
    """Is `cmd` (the head token of an exclude-command value) on PATH? A nudge-only
    host signal (ADR-010 bounded host-probing) — used to detect a widening tool is
    in use even without a repo marker. Never gates an auto-apply."""
    import shutil
    return shutil.which(cmd.split()[0]) is not None if cmd else False


def _detect_signing(target_root: Path) -> tuple[str, str] | None:
    """If git commit-signing-over-ssh is configured, return (description, command)
    nudging the socket accommodation the box can't reach. Bounded host-probing
    (git config) for a NUDGE only (ADR-010); never auto-applied. Recognizes the
    1Password helper to name its socket precisely; generic otherwise. Returns None
    when signing isn't configured or the socket is already accommodated."""
    import subprocess

    def _cfg(key: str) -> str:
        try:
            r = subprocess.run(["git", "config", "--get", key], cwd=target_root,
                               capture_output=True, text=True, check=False)
        except (OSError, ValueError):
            return ""
        return r.stdout.strip() if r.returncode == 0 else ""

    if _cfg("gpg.format") != "ssh":
        return None
    program = _cfg("gpg.ssh.program")
    if not program:
        return None
    live = {_expand(s) for s in (_sandbox_block(target_root).get("network") or {}).get("allowUnixSockets", [])}
    low = program.lower()
    if "op-ssh-sign" in low or "1password" in low:
        sock = "~/.1password/agent.sock"
        if _expand(sock) in live:
            return None  # already accommodated
        return ("commit-signing via 1Password (op-ssh-sign) — the box can't reach its agent socket",
                f"pkit permissions sandbox accommodate --socket {sock} --name signing")
    return (f"commit-signing via {os.path.basename(program)} — the box can't reach its agent socket",
            "pkit permissions sandbox accommodate --socket <its-agent-socket> --name signing")


_VOLATILE_SOCK_PREFIXES = (
    "/var/run/com.apple.launchd.",
    "/private/var/run/com.apple.launchd.",
    "/private/tmp/com.apple.launchd.",
)


def _setup_stability_tip(target_root: Path) -> list[str]:
    """ADR-010 detect-to-nudge: when $SSH_AUTH_SOCK is a *volatile* per-session
    launchd path (rotates on reboot, so the accommodation goes stale) AND a
    *stable* agent socket (1Password) is present, emit a one-time tip guiding the
    operator to route SSH through the stable socket — truly run-once. Bounded
    host-probing (env + a socket's existence), nudge-only, nothing auto-applied.
    Self-vanishing: once $SSH_AUTH_SOCK is non-volatile this returns []. Conforms
    to the CLI output convention (Title-case header, whitespace, no rules)."""
    sock = (os.environ.get("SSH_AUTH_SOCK") or "").strip()
    if not sock:
        return []
    resolved = _expand(sock)
    if not any(resolved.startswith(p) for p in _VOLATILE_SOCK_PREFIXES):
        return []  # already stable → no tip
    if not Path("~/.1password/agent.sock").expanduser().exists():
        return []  # no stable alternative to recommend
    shell = os.path.basename(os.environ.get("SHELL", "") or "")
    rc = {"zsh": "~/.zshrc", "bash": "~/.bashrc"}.get(shell, "your shell startup file")
    return [
        "",
        "  " + cli_render.style("heading", "Optional — make SSH survive reboots (run-once)"),
        "",
        "    Your SSH agent socket changes on every reboot, so you'd re-run setup after each one.",
        "    To make autonomy truly run-once, route SSH through 1Password's stable socket:",
        "",
        '      1. 1Password → Settings → Developer → turn on "Use the SSH agent".',
        f"      2. Add this line to {rc}:",
        "             export SSH_AUTH_SOCK=~/.1password/agent.sock",
        "      3. Open a new terminal, then run `pkit permissions setup autonomy` once more.",
        "",
        "    After that the socket never moves — set once, done.",
    ]


# Names that the looser nudge predicate treats as platform-mandatory on macOS:
# the declared candidate commands (`uv`, `gh` — ADR-030), plus `pkit` aliased to
# `uv`'s required-ness (excluding `uv` covers `pkit` only via `uv run pkit`, head
# token `uv`). Data-driven off `_REQUIRED_CANDIDATES` so a new candidate becomes
# nudge-required automatically — no second hardcoded name-set to keep in sync.
def _required_candidate_names() -> set[str]:
    return {cmd for cmd, _ in _REQUIRED_CANDIDATES} | {"pkit"}


def _widening_required_on_platform(tool: str, cmd: str) -> bool:
    """Is this widening exclusion MANDATORY on the current platform (vs an
    operator's optional choice)? Derived AT RUNTIME — never a toolkit-schema field
    (architect: derive it, don't schematise). The mandatory cases on macOS: a
    command in the declared required candidate set (`uv`, `gh` — ADR-030) cannot
    run inside the Seatbelt box (a fixed mach-service denial, no setting fixes it —
    ADR-014), so excluding it is not optional; `pkit` is aliased to `uv`. Anything
    NOT in the candidate set (e.g. `docker`) is an optional widening the operator
    may accept.

    This is the LOOSER platform+name predicate (no detect-fence / version conjunct).
    It drives the NUDGE-copy path only — whether a widening reads as "REQUIRED on
    macOS" vs "optional". The AUTO-APPLY path (ADR-027/ADR-030) needs each member's
    full verifier on top — see `_REQUIRED_CANDIDATES` and `_required_verifier`."""
    import sys as _sys
    if _sys.platform != "darwin":
        return False
    names = _required_candidate_names()
    return tool in names or cmd in names


# The macOS uv Seatbelt panic (ADR-014): a fixed SCDynamicStore mach-service
# denial that no narrowing accommodation fixes, so the command must run OUTSIDE
# the box. The panic is present in EVERY current uv release until an upstream fix
# ships — so the auto-apply carve-out (ADR-027 condition 1) is gated on the
# FIXED release, not on a known-bad ceiling: an installed uv is still affected
# whenever it is BELOW the known-fixed release (and, while no fix is known, ALL
# readable versions are affected). Gating on a known-bad ceiling would be wrong —
# the day a still-broken uv ships above the first known-bad release, a ceiling
# test would (incorrectly) stop auto-applying.
#
# There is no known-FIXED release yet (`None`) — when one ships, set
# `_UV_KNOWN_FIXED_RELEASE` to it; a uv at or above it leaves the box able to
# host the command, so auto-apply self-disables (and self-heal removes any entry
# it previously applied). `_UV_KNOWN_BAD_FLOOR` records the FIRST observed
# known-bad release for documentation/provenance only — it does NOT gate
# auto-apply (see `_uv_required_exclusion`).
_UV_KNOWN_BAD_FLOOR = "0.9.8"          # informational: first observed known-bad
_UV_KNOWN_FIXED_RELEASE: str | None = None

# Distinct provenance tag for the auto-applied platform-REQUIRED exclusion
# (ADR-027 condition 3). NOT `_manual` (operator-set) — so status, teardown, and
# self-heal can tell a pkit-required carve-out from an operator's hand-added one.
_REQUIRED_TOOLKIT = "_required"

# Distinct provenance tag for the pkit-authored unsandboxed-escape SEAL
# (`allowUnsandboxedCommands: false`, ADR-028). The seal is the autonomy
# posture's pkit-set default — distinct from an operator who hand-sets `false`
# (no provenance). The tag is what lets the non-strict `sandbox enable` clear
# reverse ONLY the posture's own seal (ADR-028 cond. 5) while leaving an
# operator's hand-set choice untouched (ADR-008 rule 2). `kind: "seal"` is a
# scalar-key provenance entry, not a list-allowance like `exclude-command`.
_SEAL_TOOLKIT = "_strict"
_SEAL_KIND = "seal"


def _read_uv_version() -> Version | None:
    """Read the installed uv's version robustly, as a packaging Version (or None
    when uv is absent / unparseable). Used by the auto-apply necessity check
    (ADR-027 condition 1) — the sandbox is off during `setup autonomy`, so the
    subprocess runs unconfined and can reach the binary. Tolerates the
    `uv 0.9.8 (Homebrew 2025-11-07)` shape (take the second whitespace token)."""
    import shutil
    import subprocess

    from packaging.version import InvalidVersion, Version

    exe = shutil.which("uv")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True,
                           check=False, timeout=10)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    parts = (r.stdout or "").strip().split()
    if len(parts) < 2:
        return None
    try:
        return Version(parts[1])
    except InvalidVersion:
        return None


def _uv_required_exclusion(target_root: Path) -> bool:
    """The AUTO-APPLY conjunct (ADR-027 condition 1) for the macOS uv exclusion:
    necessity-VERIFIED, not merely believed. True only when ALL hold:

      - the platform is macOS (the looser predicate; never on Linux/bubblewrap,
        where uv runs confined once its cache is accommodated — condition 2);
      - a uv repo marker is present (real project use — `uv.lock` / `pyproject`
        via the toolkit's own detect globs — condition 3, not bare PATH);
      - the installed uv is BELOW the known-fixed release — i.e. the
        SystemConfiguration panic still occurs. The panic is in every release
        until a fix ships, so while `_UV_KNOWN_FIXED_RELEASE is None` EVERY
        readable version qualifies (we do NOT gate on a known-bad ceiling — an
        above-ceiling still-unfixed uv must keep auto-applying).

    A uv at/above a known-fixed release returns False → the box can host the
    command again, so auto-apply self-disables and self-heal (condition 6)
    removes any entry it previously applied. The looser platform+name predicate
    (`_widening_required_on_platform`) stays for the NUDGE path; this is the
    version-gated AUTO path only."""
    if not _widening_required_on_platform("uv", "uv"):
        return False
    toolkits = _load_toolkits(target_root)
    if "uv" not in _detect_tools(target_root, toolkits):
        return False
    from packaging.version import Version

    installed = _read_uv_version()
    if installed is None:
        # macOS + repo marker but uv unreadable: cannot VERIFY necessity, so do
        # NOT auto-apply (the keystone is verified-not-believed). The nudge path
        # still surfaces the gesture for the operator to run by hand.
        return False
    # Gate on the FIXED release: no fix known (None) → every readable version is
    # affected → required; otherwise required iff still below the fix.
    return _UV_KNOWN_FIXED_RELEASE is None or installed < Version(_UV_KNOWN_FIXED_RELEASE)


def _gh_required_exclusion(target_root: Path) -> bool:
    """The AUTO-APPLY conjunct (ADR-030 conditions 1-4) for the macOS gh exclusion:
    necessity-VERIFIED, not believed. True only when ALL hold:

      - the platform is macOS (the `com.apple.SecurityServer` mach-service denial
        is Seatbelt-specific; on Linux/bubblewrap gh runs confined — condition 4);
      - the `.github/` detect glob is present (real project use of gh — workflows,
        issue templates, a GitHub-hosted repo — condition 4, NEVER bare gh-on-PATH).

    Unlike `_uv_required_exclusion` there is NO version coordinate: gh's failure is
    PLATFORM-PERMANENT on macOS (Go's crypto/x509 reaches a blocked mach-service;
    SSL_CERT_FILE is a darwin no-op, so no cert accommodation reaches past it —
    ADR-030 condition 3 / Evidence 1-2). The verdict is reviewed on Claude Code /
    gh updates, not auto-healed by a version check. So this verifier is a pure
    platform-AND-detect conjunct: macOS AND `.github/` detected → required, full
    stop. There is no installed-version read because there is nothing a version
    could falsify (a verifier that gated on a version would never fire — ADR-030
    "Why permanent-reviewed rather than version-gated")."""
    import sys as _sys
    if _sys.platform != "darwin":
        return False
    toolkits = _load_toolkits(target_root)
    return "gh" in _detect_tools(target_root, toolkits)


# The DECLARED candidate set for the auto-applied, platform-mandatory REQUIRED
# subclass (ADR-027, generalised to a verified set by ADR-030 condition 6). This
# is the COR-007 extraction triggered by the arrival of the SECOND member: the
# per-member knowledge that used to live as three inline `uv` literals
# (`_widening_required_on_platform`, the nudge-skip, the self-heal `cmd == "uv"`)
# is lifted into one auditable table the writer reads.
#
# What is DATA here is only the candidate set + per-member verifier-binding: which
# commands are eligible, and which runtime verifier governs each member's
# necessity. The necessity VERDICT stays runtime-derived (the #247 / ADR-030
# stance) — "required: true" is NEVER frozen into committed data; the verifier is
# consulted live against platform / version / evidence state on every run.
#
# Each member declares:
#   command       — the head token excluded from the box (the `sandbox exclude`
#                   value).
#   verifier_name — the NAME of the runtime necessity check (target_root -> bool),
#                   resolved against this module at CALL time (not captured as a
#                   reference) so the verdict tracks the live function — the
#                   indirection keeps the verifier swappable for tests and makes
#                   the binding plain auditable data, not a frozen closure. `uv` →
#                   the version-floor verifier (self-disables on a fixed release);
#                   `gh` → the macOS-permanent-reviewed verifier (platform +
#                   `.github/` detect, no version coordinate — ADR-030 condition 3).
# Platform and detect-fence are encoded INSIDE each verifier (they differ per
# member: uv gates on a uv repo marker + version floor, gh on `.github/` + the
# permanent mach-service denial), so the table binds the command to its verifier
# and the verifier owns the member-specific conjuncts.
_REQUIRED_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("uv", "_uv_required_exclusion"),
    ("gh", "_gh_required_exclusion"),
)


def _required_verifier(command: str) -> Callable[[Path], bool] | None:
    """The runtime necessity verifier bound to a candidate command, or None if the
    command is not in the declared required candidate set. Resolves the bound
    verifier NAME against the live module (so a test-swapped verifier is honoured).
    Used by the self-heal loop and the apply loop to re-check each `_required`
    candidate against its OWN member's verifier (ADR-030 condition 6) instead of a
    hardcoded `cmd == "uv"`."""
    for cmd, verifier_name in _REQUIRED_CANDIDATES:
        if cmd == command:
            return globals()[verifier_name]
    return None


# Fail fast at import if a candidate names a verifier that does not resolve — a
# future third member with a typo'd verifier name surfaces here, not as a KeyError
# mid-`setup autonomy` (W1 hardening for the ADR-030 declared-set seam).
for _cand_cmd, _cand_verifier in _REQUIRED_CANDIDATES:
    assert _cand_verifier in globals(), (
        f"_REQUIRED_CANDIDATES: {_cand_cmd!r} binds verifier {_cand_verifier!r} "
        f"which does not resolve in this module"
    )


def _widening_desc(tool: str, cmd: str) -> tuple[str, str]:
    """The nudge label + body for one widening exclusion — required-vs-optional
    copy chosen at runtime (see _widening_required_on_platform). Returns
    (label, body): the label is the short head that anchors the item at the
    4-space margin; the body is the explanatory prose the caller hang-wraps under
    it. Both plain (the caller styles / wraps the returned text)."""
    if _widening_required_on_platform(tool, cmd):
        if cmd == "gh" or tool == "gh":
            return (
                f"`{tool}` — REQUIRED on macOS:",
                (
                    "`gh` can't run inside the box (a fixed Seatbelt mach-service "
                    "denial; no setting fixes it), so it must run unconfined — its "
                    "network egress is then UNCONFINED (ADR-004 §61). Not optional — "
                    "the documented macOS stance (ADR-014/ADR-030). `setup autonomy` "
                    "auto-applies this in a `.github/` project. Still gated by the "
                    "permission hook."
                ),
            )
        return (
            f"`{tool}` — REQUIRED on macOS:",
            (
                "`uv` can't run inside the box (a fixed Seatbelt panic; no "
                "setting fixes it), so it must run unconfined. Not optional — "
                "the documented macOS stance (ADR-014). Still gated by the "
                "permission hook."
            ),
        )
    return (
        f"`{tool}` — optional:",
        (
            f"excluding it lets `{cmd}` run unconfined (widening). Only do this "
            "if you want it to work in a sandboxed session."
        ),
    )


def _setup_next_steps(target_root: Path, widening: list[tuple[str, str]],
                      host_nudges: list[tuple[str, str]]) -> list[str]:
    """Render the consolidated NEXT block: explicit gestures the project needs but
    setup will NOT run for the operator — widening (lowers the box) and
    narrowing-but-unresolvable (signing socket, host nudges). Each item is a
    description line + the command on its own indented line (copy-paste ready).
    Empty list if none."""
    signing = _detect_signing(target_root)
    if not (widening or host_nudges or signing):
        return []

    # Title-case header + blank-line zoning, NO horizontal rules — per the CLI
    # output convention (.pkit/cli/README.md "Command output conventions"): zones
    # are marked by header case + whitespace, never drawn rules. Each command
    # goes on its own indented line so it's copy-paste-obvious.
    #
    # The description is author prose: route it through cli_render.wrap (ADR-024)
    # so long / multi-line copy hangs under the 4-space label (continuations at 6
    # spaces) instead of wrapping flush to column 0. The command is a copy-paste
    # token, NOT prose — it stays on its own un-wrapped line at 8 spaces
    # (backtick-quoted), styled as before.
    # Each item: a label anchored at the 4-space margin, an optional body of
    # explanatory prose, then the command on its own un-wrapped 8-space line
    # (a copy-paste token, never wrapped). The body is author prose routed through
    # cli_render.wrap (ADR-024): the label is the inline line-1 prefix
    # (first_line_indent = its visible width), so the body's continuation lines
    # hang under it at indent(4) + hang(2) = 6 spaces instead of wrapping flush to
    # column 0. A bodyless item is just the label line.
    def _item(label: str, command: str, body: str = "") -> list[str]:
        if not body:
            head = cli_render.wrap(label, indent="    ", hang="  ")
        else:
            prefix = f"    {label} "
            tail = cli_render.wrap(body, indent="    ", hang="  ",
                                   first_line_indent=len(prefix))
            head = [prefix + tail[0], *tail[1:]]
        return ["", *head, f"        `{command}`"]

    out = ["", "  " + cli_render.style("heading", "Next — run these yourself (setup never lowers the box for you)")]
    for tool, cmd in widening:
        label, body = _widening_desc(tool, cmd)
        out += _item(label, f"pkit permissions sandbox exclude {cmd}", body)
    if signing:
        out += _item(f"{signing[0]} (narrowing — box stays confined):", signing[1])
    for desc, command in host_nudges:
        out += _item(f"{desc}:", command)
    out += [
        "",
        "    (each persists once run; `accommodate` choices re-apply on every future setup.)",
    ]
    return out


def _setup_accommodations(target_root: Path, profile: str) -> tuple[list[str], list[tuple[str, str]]]:
    """The narrowing-apply step of `setup autonomy` (ADR-008): on first run, seed
    the active profile's recommended toolkits + detected tools into permission-
    config (narrowing only); then apply every recorded toolkit's NARROWING
    allowances. Returns (applied tool names, widening nudges as (tool, cmd)).
    Widening is NEVER applied here — only surfaced as an explicit-gesture nudge."""
    toolkits = _load_toolkits(target_root)
    acc = _config_accommodations(target_root)
    if not acc:
        res = _resolve_profile(target_root, profile)
        recommended = (
            [_toolkit_name(t) for t in (res[1].get("recommended_accommodations") or [])]
            if res else []
        )
        detected = _detect_tools(target_root, toolkits)
        seed = sorted(set(recommended) | set(detected))
        for t in seed:
            if t in toolkits and _narrowing(toolkits[t].get("allowances", [])):
                _record_accommodation(target_root, t, add=True)
        acc = _config_accommodations(target_root)

    applied: list[str] = []
    for t in acc:
        if t not in toolkits:
            continue
        narrowing = _narrowing(toolkits[t].get("allowances", []))
        if narrowing:
            _apply_allowances(target_root, narrowing, t)
            applied.append(t)

    # Widening nudges: tools that need carving out of the box — surfaced, never
    # applied (ADR-008 rule 4). A widening tool counts as "in use" if a repo
    # marker matches OR its command is on PATH (the host signal makes gh-style
    # detection robust; nudge-only per ADR-010). Skip anything already excluded.
    sb = _sandbox_block(target_root)
    excluded = set(sb.get("excludedCommands") or [])
    in_use = set(_detect_tools(target_root, toolkits))
    for t in toolkits:
        for w in _widening(toolkits[t].get("allowances", [])):
            if w.get("kind") == "exclude-command" and _command_on_path(w.get("value", "")):
                in_use.add(t)
    nudges: list[tuple[str, str]] = []
    for t in sorted(in_use):
        for w in _widening(toolkits[t].get("allowances", [])):
            cmd = w.get("value")
            if w.get("kind") == "exclude-command" and cmd and cmd not in excluded:
                # A platform-REQUIRED, necessity-verified exclusion is auto-applied
                # by setup (ADR-027/ADR-030), not nudged — drop it from the nudge
                # list so it isn't surfaced twice. Data-driven: ask the command's
                # candidate-set verifier whether the auto path WILL apply it (uv
                # below a fix + marker; gh on macOS + `.github/`). Optional widenings
                # (docker) and a required candidate the verifier declines (an
                # unverifiable / fixed uv, gh off macOS or without `.github/`) still
                # nudge here.
                verifier = _required_verifier(cmd)
                if verifier is not None and verifier(target_root):
                    continue
                nudges.append((t, cmd))
    return applied, nudges


def _relocate_tracked_required_exclusions(target_root: Path) -> list[str]:
    """Relocate a pre-ADR-029 `_required` exclusion sitting in the TRACKED
    `settings.json` into the gitignored `settings.local.json` (Task #275).

    ADR-029 routes NEW widenings to the local file, but a required exclusion
    applied by a pre-ADR-029 `setup autonomy` run still sits in the tracked
    `settings.json` as working-copy drift. The auto-apply idempotency guard
    ("already excluded in the union? skip") never relocates it, so the rule-4
    drift lingers. This pass closes that residual at runtime — the convergence
    IS the migration mechanism (no one-shot lifecycle script; #275 judgment).

    Scope (the safety criterion — ADR-008 rule 2 provenance-scoped):
      - A required-CANDIDATE command (in `_REQUIRED_CANDIDATES`) present in the
        committed file's `excludedCommands` AND `_required`-provenanced (pkit
        authored it) is MOVED.
      - An operator `_manual` carve-out is NEVER relocated.
      - An UNTAGGED/foreign committed entry (no provenance record for it) is left
        UNTOUCHED — even for a required-candidate command, because we cannot
        positively confirm pkit authored it (a pre-ADR-027 entry may be untagged;
        the conservative call is don't move what you didn't author).

    No un-exclude window (the live-throughout guarantee): the local copy is
    written first WHEN NEEDED — the entry is in local BEFORE it leaves the
    committed file, so the union never un-excludes. When the entry is already in
    local (a half-done prior run), that first write is skipped and we go straight
    to the strip; this is still safe because local already carries the command, so
    the union is unbroken across the strip. In the write-then-strip case the entry
    is briefly in BOTH files; after the strip it is in local only. Either way the
    runtime union (`_sandbox_block`, which deep-merges both files) ALWAYS contains
    the command — a reader / hook never sees it absent from both files at any point.

    Idempotent: an entry already only in `settings.local.json` (absent from the
    committed file) is a no-op; re-running converges with no double-write.

    Returns report lines (one per relocation) for the [3/4] confinement block."""
    prov = _load_provenance(target_root)
    required_provenanced = {
        e.get("value") for e in prov
        if e.get("toolkit") == _REQUIRED_TOOLKIT and e.get("kind") == "exclude-command"
    }
    candidate_cmds = {cmd for cmd, _ in _REQUIRED_CANDIDATES}

    committed = _read_settings(target_root)
    committed_sb = committed.get("sandbox")
    if not isinstance(committed_sb, dict):
        return []
    committed_excl = committed_sb.get("excludedCommands")
    if not isinstance(committed_excl, list):
        return []

    # Only required-candidate, `_required`-provenanced entries that are actually
    # in the committed file are relocation candidates. `_manual` and untagged
    # entries are absent from `required_provenanced`, so they fall away here.
    to_move = [
        cmd for cmd in committed_excl
        if cmd in candidate_cmds and cmd in required_provenanced
    ]
    if not to_move:
        return []

    # Step 1 — write the LOCAL copy first (the union still has the committed copy,
    # so the command stays excluded throughout). Add only what's missing locally.
    local = _read_settings_local(target_root)
    local_sb = local.setdefault("sandbox", {})
    local_excl = local_sb.setdefault("excludedCommands", [])
    local_added = False
    for cmd in to_move:
        if cmd not in local_excl:
            local_excl.append(cmd)
            local_added = True
    if local_added:
        _write_settings_local(target_root, local)

    # Step 2 — now strip the committed copy (local already carries it, so the
    # union is unchanged across this write — no un-exclude window).
    committed_sb["excludedCommands"] = [c for c in committed_excl if c not in to_move]
    if not committed_sb["excludedCommands"]:
        committed_sb.pop("excludedCommands", None)
    _write_settings(target_root, committed)

    return [
        f"relocated `{cmd}` exclusion to settings.local.json "
        f"(was in tracked settings.json — ADR-029)"
        for cmd in to_move
    ]


def _relocate_per_machine_sandbox_state(target_root: Path) -> list[str]:
    """Relocate pre-ADR-032 per-machine sandbox state that drifted into the
    TRACKED `settings.json` over to the gitignored `settings.local.json` (ADR-032).

    Two per-machine fields are in scope here (NOT `active_profile`, deferred to a
    separate task):

      - the host SOCKET (`network.allowUnixSockets`) — a `socket:`-provenanced
        host-derived value (ADR-032 Rule A). Effect-axis routing alone baked the
        resolved host path (`/Users/<operator>/.1password/agent.sock`) into the
        committed floor; this moves it to its per-machine home. The committed
        floor keeps at most the path-free `confinement_accommodations` intent —
        NEVER the resolved path, which this pass strips.
      - `enabled` — operator-activated, harness-co-owned (ADR-032 Rule B defer
        branch). A drifted committed `enabled: true` moves to the local file the
        harness `/sandbox` panel reads.

    Mirrors `_relocate_tracked_required_exclusions`'s discipline:
      - No-clobber, live-throughout (#288): the local destination is written
        BEFORE the committed source is stripped, so the runtime union never loses
        the value mid-move. A value already present in local is not overwritten.
      - Provenance-scoped: only a `socket:`-tagged socket value is moved; an
        untagged/foreign `allowUnixSockets` entry is left UNTOUCHED (don't move
        what pkit didn't author). `enabled` is a scalar pkit baseline key, moved
        by presence (it has no per-value provenance tag).
      - Floors stay committed: `denyRead`, `failIfUnavailable`,
        `autoAllowBashIfSandboxed`, `allowedHosts` are operator-invariant (Rule A
        complement) and are never relocated by this pass.
      - Idempotent: a field already only in `settings.local.json` is a no-op.

    Returns one report line per relocation for the quiet [3/4] continuation."""
    committed = _read_settings(target_root)
    committed_sb = committed.get("sandbox")
    if not isinstance(committed_sb, dict):
        return []

    reports: list[str] = []
    local = _read_settings_local(target_root)
    local_sb = local.setdefault("sandbox", {})
    local_dirty = committed_dirty = False

    # --- socket (host-derived value, `socket:` provenance, Rule A) -------------
    prov = _load_provenance(target_root)
    socket_values = {
        e.get("value") for e in prov
        if e.get("kind") == "allow-unix-socket"
        and _is_per_machine_toolkit(e.get("toolkit"))
    }
    committed_net = committed_sb.get("network")
    committed_sockets = (
        committed_net.get("allowUnixSockets")
        if isinstance(committed_net, dict) else None
    )
    if isinstance(committed_sockets, list) and socket_values:
        to_move = [s for s in committed_sockets if s in socket_values]
        if to_move:
            # Step 1 — write local first (union still has the committed copy, so
            # the socket stays accommodated throughout). Add only what's missing.
            local_net = local_sb.setdefault("network", {})
            local_sockets = local_net.setdefault("allowUnixSockets", [])
            for s in to_move:
                if s not in local_sockets:
                    local_sockets.append(s)
                    local_dirty = True
            # Step 2 — strip the committed copy (local already carries it).
            committed_net["allowUnixSockets"] = [
                s for s in committed_sockets if s not in to_move
            ]
            if not committed_net["allowUnixSockets"]:
                committed_net.pop("allowUnixSockets", None)
            committed_dirty = True
            reports.extend(
                f"relocated host socket `{s}` to settings.local.json "
                f"(host-derived value — was in tracked settings.json; ADR-032)"
                for s in to_move
            )

    # --- enabled (operator activation, harness-co-owned, Rule B defer) ---------
    # A drifted committed `enabled: true` (pre-ADR-032 pkit authored it there).
    # Move it to the harness-co-owned local key the panel reads.
    if committed_sb.get("enabled") is True:
        # Write local first only when local doesn't already assert a value (no
        # clobber of a live local `enabled`, whoever set it).
        if "enabled" not in local_sb:
            local_sb["enabled"] = True
            local_dirty = True
        committed_sb["enabled"] = False
        committed_dirty = True
        reports.append(
            "relocated `enabled` to settings.local.json "
            "(operator activation, harness-co-owned — was in tracked "
            "settings.json; ADR-032)"
        )

    if local_dirty:
        _write_settings_local(target_root, local)
    if committed_dirty:
        _write_settings(target_root, committed)
    return reports


def _untagged_required_candidate_advisories(target_root: Path) -> list[str]:
    """Advise (don't act) when a required-CANDIDATE command sits UNTAGGED in the
    committed `settings.json` — a relocation candidate the prior pass SKIPPED for
    lack of provenance (can't confirm pkit authored it, so it stays put; correct
    but, until now, silent). Matches the operator's inform-me preference: name the
    drift and the one-command fix rather than leaving it unexplained.

    Detect: command in `_REQUIRED_CANDIDATES` AND present in the committed file's
    `excludedCommands` AND neither `_required`- NOR `_manual`-provenanced. A
    `_manual` entry is a deliberate operator carve-out (not drift) and is NEVER
    advised on; a `_required` entry was already relocated by the pass above."""
    prov = _load_provenance(target_root)
    tagged = {
        e.get("value") for e in prov
        if e.get("toolkit") in (_REQUIRED_TOOLKIT, "_manual")
        and e.get("kind") == "exclude-command"
    }
    candidate_cmds = {cmd for cmd, _ in _REQUIRED_CANDIDATES}

    committed = _read_settings(target_root)
    committed_sb = committed.get("sandbox")
    if not isinstance(committed_sb, dict):
        return []
    committed_excl = committed_sb.get("excludedCommands")
    if not isinstance(committed_excl, list):
        return []

    untagged = [
        cmd for cmd in committed_excl
        if cmd in candidate_cmds and cmd not in tagged
    ]
    return [
        f"note: an untagged `{cmd}` exclusion is in your committed settings.json — "
        f"pkit won't move what it didn't author. Run "
        f"`pkit permissions sandbox exclude --remove {cmd}` then re-run setup to "
        f"relocate it cleanly, or remove the line by hand."
        for cmd in untagged
    ]


def _setup_required_exclusions(target_root: Path) -> tuple[list[str], list[str]]:
    """Auto-apply (and self-heal) the platform-MANDATORY, necessity-verified
    sandbox exclusion — the one carve-out from ADR-008 rule 4's "never applied by
    setup", sanctioned by ADR-027. Returns (loud_lines, confirmed_lines):
    `loud_lines` feed the own "pkit applied it for you" block (a boundary just
    lowered — self-heal + fresh apply); `confirmed_lines` are quiet [3/4]
    confinement-continuation confirmations for the no-op case (the exclusion was
    already in place — nothing applied, but reported so it isn't a silent gap).
    Both empty when there's nothing to say.

    Apply (conditions 1-5): when `_uv_required_exclusion` verifies the macOS uv
    Seatbelt panic still occurs AND uv is not already excluded, shell to the real
    `sandbox_exclude` primitive under the distinct `_required` provenance tag and
    fire the existing UNCONFINED banner. The exclusion is a widening, so
    `sandbox_exclude` routes it to the gitignored `settings.local.json` (ADR-029)
    — condition 4 by construction: a widening never lands in the committed
    `settings.json`, so there is nothing for an operator to keep uncommitted.
    `sandbox_exclude` touches nothing else.

    Already in place: when the exclusion is required AND already excluded (the
    auto-apply is a no-op), report a quiet confirmation rather than going silent —
    the operator needs to see the platform-mandatory exclusion is handled, just as
    the strict seal and accommodations are confirmed even when already present.

    Self-heal (condition 6): when a previously auto-applied `_required` exclusion
    is no longer required (uv upgraded past a fixed release, or we're on Linux),
    REMOVE it through the same primitive and report the removal. Only `_required`
    entries are touched — an operator's `_manual` carve-out of the same command is
    never removed here (the distinct tag is what keeps teardown honest)."""
    if not _adapter_installed(target_root, "claude-code"):
        return [], []

    loud: list[str] = []
    confirmed: list[str] = []

    # Relocation pass first (Task #275): move any pre-ADR-029 `_required` exclusion
    # that drifted into the TRACKED `settings.json` over to the gitignored
    # `settings.local.json`, restoring rule-4's never-committed-by-construction
    # guarantee on already-installed machines. Runs before self-heal/apply so the
    # union below reflects the relocated state. The relocation lines are quiet
    # [3/4] confinement continuations (the runtime effect is UNCHANGED — the
    # command stays excluded throughout — so they confirm rather than alarm).
    confirmed.extend(_relocate_tracked_required_exclusions(target_root))

    # Advisory pass (untagged required-candidate drift): the relocation above
    # could only MOVE provenanced entries; an untagged committed exclusion for a
    # required candidate is left untouched but, until now, silently. Surface a
    # one-command-fix note as a quiet [3/4] continuation — inform, don't act.
    confirmed.extend(_untagged_required_candidate_advisories(target_root))

    prov = _load_provenance(target_root)
    required_entries = {
        e.get("value") for e in prov
        if e.get("toolkit") == _REQUIRED_TOOLKIT and e.get("kind") == "exclude-command"
    }

    # Self-heal first: drop any auto-applied required exclusion no longer warranted.
    # Data-driven (ADR-030 condition 6): re-check each previously auto-applied
    # `_required` entry against ITS OWN member's verifier in the declared candidate
    # set — no hardcoded `cmd == "uv"` literal. An entry whose command is no longer
    # a candidate (e.g. its member was removed) has no verifier → not still
    # required → self-healed, which is the safe convergence.
    for cmd in sorted(c for c in required_entries if c):
        verifier = _required_verifier(cmd)
        still_required = verifier is not None and verifier(target_root)
        if not still_required:
            sandbox_exclude(target_root, cmd, remove=True, toolkit=_REQUIRED_TOOLKIT)
            loud.append(
                f"  self-healed: `{cmd}` is no longer a required exclusion "
                f"(no longer macOS-mandatory — uv past a fixed release, gh on Linux, "
                f"or marker gone) — removed; it runs inside the box again."
            )

    # Apply: each candidate whose verifier confirms necessity AT RUNTIME (the
    # verdict is never frozen into data — ADR-030 condition 6). Read LIVE union
    # state (committed + per-machine local) so each branch reflects what the box
    # actually excludes, not just what we'd write. Per-member apply copy is loud
    # and member-specific (uv names its local-runtime carve-out; gh names its
    # UNCONFINED network egress — ADR-030 condition 2).
    for cmd, _verifier_name in _REQUIRED_CANDIDATES:
        verifier = _required_verifier(cmd)
        if verifier is None or not verifier(target_root):
            continue
        sb = _sandbox_block(target_root)
        already = cmd in set(sb.get("excludedCommands") or [])
        if not already:
            sandbox_exclude(target_root, cmd, toolkit=_REQUIRED_TOOLKIT)
            loud.extend(_required_apply_lines(cmd))
        else:
            # No-op apply: the required exclusion is already in place. Confirm it
            # quietly so the operator isn't left unsure it's handled (Task #274 /
            # ADR-030 condition 2 — the already-in-place gh case is confirmed too).
            confirmed.append(_required_confirm_line(cmd))
    return loud, confirmed


def _required_apply_lines(cmd: str) -> list[str]:
    """The LOUD apply banner for a freshly auto-applied `_required` exclusion —
    member-specific (ADR-030 condition 2). `uv` names its local-runtime carve-out;
    `gh` names its UNCONFINED network egress (the materially larger boundary
    statement — ADR-004 §61). A candidate with no bespoke copy falls back to a
    generic loud line so the set never applies silently."""
    if cmd == "uv":
        return [
            "  ⚠ REQUIRED exclusion auto-applied: `uv` (and `pkit`, which runs "
            "via `uv run`) now runs OUTSIDE the OS box — UNCONFINED, with full "
            "host filesystem and network reach.",
            "    macOS-mandatory and necessity-verified: uv "
            f"{_UV_KNOWN_BAD_FLOOR}-class hits a fixed Seatbelt panic the box "
            "cannot host (ADR-014/ADR-027). NOT recorded in any committed file "
            "(per-machine only); reported by `sandbox status` and counted by "
            "`probe`; still gated by the permission hook. A fixed uv "
            "self-disables this on the next setup run.",
        ]
    if cmd == "gh":
        return [
            "  ⚠ REQUIRED exclusion auto-applied: `gh` runs OUTSIDE the box — its "
            "network egress is UNCONFINED (ADR-004 §61). Full host reach for a "
            "command whose whole purpose is talking to GitHub.",
            "    macOS-mandatory and necessity-verified: gh's Go TLS handshake "
            "hits a fixed `com.apple.SecurityServer` Seatbelt denial the box "
            "cannot host (ADR-014/ADR-030); no cert accommodation reaches past it "
            "(SSL_CERT_FILE is a darwin no-op). Detect-fenced to `.github/` "
            "projects. PERMANENT — no version self-heal; reviewed on Claude Code "
            "updates. NOT recorded in any committed file (per-machine only); "
            "reported by `sandbox status`; still gated by the permission hook. "
            "Revert: `pkit permissions sandbox exclude --remove gh`.",
        ]
    return [
        f"  ⚠ REQUIRED exclusion auto-applied: `{cmd}` now runs OUTSIDE the OS box "
        "— UNCONFINED. Platform-mandatory, necessity-verified (ADR-027/ADR-030)."
    ]


def _required_confirm_line(cmd: str) -> str:
    """The quiet already-in-place confirmation for a `_required` exclusion (#274 /
    ADR-030 condition 2) — member-specific so gh's egress note differs from uv's."""
    if cmd == "gh":
        return (
            "required exclusion: ✓ `gh` already excluded "
            "(macOS-mandatory, egress UNCONFINED — ADR-030)"
        )
    return (
        f"required exclusion: ✓ `{cmd}` already excluded "
        "(platform-mandatory, necessity-verified — ADR-027)"
    )


def setup_autonomy(target_root: Path, profile: str = "autonomous") -> tuple[str, bool]:
    """Stand up the autonomy goal (ADR-007 first instance). Returns (report, ok);
    ok is False only when verification finds the decision layer BROKEN."""
    lines = [
        f"Setup goal: autonomy — autonomous agents (ADR-007)   profile: {profile}",
        "",
    ]
    # [1/4] intent — the profile (grants + posture), applied. Primitive: activate_profile.
    model = _load_model(target_root)
    if model.get("active_profile") == profile:
        lines.append(f"  [1/4] intent        ✓ already — profile {profile!r} active")
    else:
        activate_profile(target_root, profile, apply_after=True)
        lines.append(
            f"  [1/4] intent        ✓ done — profile {profile!r} activated "
            f"(grants layered under yours + applied)"
        )
    # [2/4] enforcement — the PreToolUse hook. Primitive: enable.
    if _enforcement_on(target_root):
        lines.append("  [2/4] enforcement   ✓ already — PreToolUse hook registered")
    else:
        enable(target_root)
        lines.append(
            "  [2/4] enforcement   ✓ done — PreToolUse hook registered + "
            "native guardrail denies ensured"
        )
    # Per-machine relocation pass (ADR-032): move pre-ADR-032 host socket /
    # `enabled` drift out of the TRACKED `settings.json` into the gitignored
    # `settings.local.json` (no-clobber, write-local-before-strip). Runs BEFORE the
    # confinement state is read below so a relocated `enabled` is reflected in the
    # union; its lines are quiet [3/4] continuations (the runtime effect is
    # unchanged — values stay live throughout the move).
    per_machine_relocations = _relocate_per_machine_sandbox_state(target_root)

    # [3/4] confinement — the OS sandbox, always fail-closed AND strict. Primitive:
    # sandbox_enable with strict=True (no flag pass-through per ADR-007 rule 6).
    # Strict is the autonomy posture's default (ADR-028): it composes the existing
    # `sandbox enable --strict` write (`allowUnsandboxedCommands: false`) so the
    # per-command `dangerouslyDisableSandbox` escape is inert under autonomy — an
    # agent cannot silently disable the box. The seal is the existing primitive's
    # effect (no new writer, "owns nothing" per ADR-007 rule 2), reversible by
    # turning strict off (`sandbox enable` without --strict, or autonomy down).
    sb = _sandbox_block(target_root)
    was_on = sb.get("enabled") is True
    sealed = sb.get("allowUnsandboxedCommands") is False
    if was_on and sb.get("failIfUnavailable") is True and sealed:
        lines.append(
            "  [3/4] confinement   ✓ already — OS sandbox enabled "
            "(fail-closed, unsandboxed escape sealed)"
        )
    else:
        sandbox_enable(target_root, strict=True)
        lines.append(
            "  [3/4] confinement   ✓ done — OS sandbox enabled "
            "(fail-closed, strict — unsandboxed escape sealed, credential denyRead floor)"
        )

    # Confinement accommodations (ADR-008 + ADR-010 host): make the box usable —
    # narrowing only, applied automatically. Rendered as a hanging-indent
    # continuation of the [3/4] step (aligned under the status column), so it
    # reads as a detail OF confinement, not a peer step.
    applied, nudges = _setup_accommodations(target_root, profile)
    host_applied, host_nudges = _setup_host_accommodations(target_root)
    applied = applied + host_applied
    cont = " " * 22  # aligns step continuations under the [N/4] status column
    if applied:
        lines.append(f"{cont}accommodations: {', '.join(applied)} — reachable; box stays confined")
    else:
        lines.append(f"{cont}accommodations: none needed (no known tool detected)")
    # ADR-032 per-machine relocation report (quiet [3/4] continuations).
    for line in per_machine_relocations:
        lines.append(f"{cont}{line}")

    # Required-exclusion auto-apply + self-heal (ADR-027). The LOUD lines (fresh
    # apply / self-heal) go in their OWN block — NOT folded into the quiet
    # narrowing "accommodations:" line, because they LOWER the box for a command
    # the platform cannot confine; held with the other action blocks below. The
    # CONFIRMED lines (the exclusion was already in place — a no-op) are quiet
    # [3/4] confinement continuations alongside "accommodations:", so the
    # already-handled platform-mandatory exclusion is visible, not silent (#274).
    required_lines, required_confirmed = _setup_required_exclusions(target_root)
    for line in required_confirmed:
        lines.append(f"{cont}{line}")

    # Action blocks are HELD and appended after the step spine + verdict, so they
    # don't interrupt [3/4]→[4/4]. The REQUIRED-exclusion block leads (it reports
    # a boundary pkit just lowered for you, loudly); `Next` = explicit gestures
    # you run; the stability tip is `Optional`. Order signals priority.
    required_block: list[str] = []
    if required_lines:
        required_block = [
            "",
            "  " + cli_render.style("heading",
                                    "Required exclusion (platform-mandatory; pkit applied it for you)"),
            *required_lines,
        ]
    action_blocks = (
        required_block
        + _setup_next_steps(target_root, nudges, host_nudges)
        + _setup_stability_tip(target_root)
    )

    if not was_on:
        # The honest boundary (rule 4): sandbox.enabled is not hot-reloaded.
        lines += [
            "  [4/4] verification  → blocked: sandbox.enabled is not hot-reloaded",
            f"{cont}restart the session, then re-run — finished steps are skipped and the floor is proven",
            "",
            "  " + cli_render.style("strong", "Result: configured. Restart the session and re-run to enable the box and prove the goal."),
        ]
        return "\n".join(lines + action_blocks) + "\n", True

    # [4/4] verification — the goal is reached only when the proof passes
    # (rule 5). Decision layer via the probe suite; confinement floor via the
    # same reachability primitive `probe --live` uses.
    _report, decisions_ok = probe(target_root, live=False)
    if not decisions_ok:
        lines += [
            "  [4/4] verification  ✗ BROKEN — the live decision layer diverges from the declared model",
            f"{cont}run `pkit permissions probe` for the per-probe detail",
            "",
            "  " + cli_render.style("strong", "Result: BROKEN — fix the decision layer before relying on autonomy."),
        ]
        return "\n".join(lines + action_blocks) + "\n", False
    floor = _floor_status(target_root)
    if floor == "proven":
        lines += [
            "  [4/4] verification  ✓ decision layer proven · credential floor REJECTED by the OS",
            "",
            "  " + cli_render.style("strong", "Result: goal reached — autonomous agents: configured, confined, and proven."),
        ]
        return "\n".join(lines + action_blocks) + "\n", True
    lines += [
        "  [4/4] verification  ✓ decision layer proven · OS confinement floor not provable from here",
        f"{cont}you're outside the box (not yet restarted); re-run after restart — or `pkit permissions probe --live` — to prove it",
        "",
        "  " + cli_render.style("strong", "Result: configured and decision-proven. One step left: restart the session, then re-run to prove the OS confinement floor."),
    ]
    return "\n".join(lines + action_blocks) + "\n", True


def setup_autonomy_down(target_root: Path) -> str:
    """Tear down the autonomy goal's live switches; report residual state
    loudly (ADR-007 rule 7 — never a bare success)."""
    lines = [cli_render.style("title", "Teardown: autonomy — reversing the live switches (ADR-007)"), ""]
    msg = disable(target_root)
    lines.append(
        "  enforcement   ✓ " + ("hook already off" if "already" in msg
                                else "PreToolUse hook stripped (guardrail denies stay)")
    )
    msg = sandbox_disable(target_root)
    lines.append(
        "  confinement   ✓ " + ("sandbox already off" if "already" in msg
                                else "sandbox disabled (restart to drop the running box)")
    )
    # Reverse the auto-applied REQUIRED exclusion pkit stood up (ADR-027 cond. 6 /
    # ADR-007 rule 7): setup applied it, so teardown removes it through the same
    # primitive and reports it. Operator `_manual` carve-outs are NOT touched here
    # — those stay residual (reported below) because pkit never set them.
    prov = _load_provenance(target_root)
    auto_required = [
        e.get("value") for e in prov
        if e.get("toolkit") == _REQUIRED_TOOLKIT and e.get("kind") == "exclude-command"
    ]
    for cmd in sorted(c for c in auto_required if c):
        sandbox_exclude(target_root, cmd, remove=True, toolkit=_REQUIRED_TOOLKIT)
        lines.append(
            f"  required excl ✓ auto-applied `{cmd}` exclusion removed — back inside the box"
        )
    model = _load_model(target_root)
    active = model.get("active_profile")
    lines += ["", "  " + cli_render.style("heading", "residual (deliberately left — review it):")]
    if active:
        lines.append(
            f"    · profile {active!r} is STILL ACTIVE in the model "
            f"(posture {model.get('posture', 'lenient')}) — now UNENFORCED: "
            f"nothing checks or confines it"
        )
    else:
        lines.append("    · no active profile; manual grants (if any) remain in the model")
    # Re-read provenance: the required-exclusion removal above rewrote it.
    prov = _load_provenance(target_root)
    # Widening = operator `_manual` carve-outs (the `_required` ones were just
    # reversed). Narrowing = everything else (toolkit accommodations).
    narrowing_left = [e for e in prov if e.get("toolkit") not in ("_manual", _REQUIRED_TOOLKIT)]
    widening_left = [e for e in prov if e.get("toolkit") == "_manual"]
    if narrowing_left:
        tools = sorted({e.get("toolkit") for e in narrowing_left})
        lines.append(
            f"    · narrowing accommodations remain ({', '.join(tools)}) — harmless "
            f"(they don't widen the boundary); `sandbox accommodate --remove <tool>` to drop"
        )
    if widening_left:
        cmds = ", ".join(e.get("value") or "weaker-tls" for e in widening_left)
        lines.append(
            f"    · ⚠ WIDENING exclusions remain ({cmds}) — these run UNCONFINED; "
            f"`sandbox exclude --remove <cmd>` to put them back in the box"
        )
    lines += [
        "    · sandbox operator keys (excludedCommands, denyRead floor, …) left in settings",
        "    · realized allow rules from earlier `apply` runs remain in .claude/settings.json",
        "",
        "  lower intent too: `pkit permissions profile activate read-only`   · "
        "re-arm: `pkit permissions setup autonomy`",
    ]
    return "\n".join(lines) + "\n"


# ---- diagnose: permission-prompt diagnostic loop (PRJ-006) -------------------
#
# The opt-in, recommend-only MVP. Capture lives in the claude-code adapter hook
# (`.pkit/permissions/diagnose_capture.py`, imported after the decision is fixed
# and fail-safe-wrapped); this CLI half is the harness-agnostic arm/disarm,
# status, classifier, and report. The two halves share two files under
# `.pkit/permissions/project/` (the per-project mutable permissions state, beside
# config.yaml / grants.yaml):
#
#   diagnose.yaml      — the ARMED MARKER: a flat `key: value` YAML carrying a TTL
#                        so a session auto-expires and can't stay silently on
#                        (PRJ-006 sub-decision 5). The hook reads it with one
#                        cheap stat+read per call.
#   diagnose-log.jsonl — the captured log: one JSON record per DEFERRED decision,
#                        size-capped (drop-oldest) with the command tail redacted
#                        by default. Git-ignored via the project `.gitignore`.
#
# Recommend-only (PRJ-006 sub-decision 4): the classifier orders + explains the
# report and emits remediations it RECOMMENDS; it never applies a change. The
# captured signal is a SUPERSET of real prompts (the hook sees only its own
# abstain, not whether the harness prompted), so the report states COVERAGE, not
# a predicted prompt-count decrement.

# Default bounded-session TTL: long enough for a working session, short enough to
# auto-expire by the next day. The operator picks a value via `diagnose on --ttl`.
_DIAGNOSE_DEFAULT_TTL_SECONDS = 8 * 60 * 60  # 8 hours
# Default size cap (drop-oldest) and redaction posture — written into the marker
# so the hook and the report agree on one source of truth.
_DIAGNOSE_DEFAULT_MAX_ENTRIES = 2000
_DIAGNOSE_DEFAULT_REDACT = True


def _diagnose_marker_path(target_root: Path) -> Path:
    return _project_dir(target_root) / "diagnose.yaml"


def _diagnose_log_path(target_root: Path) -> Path:
    return _project_dir(target_root) / "diagnose-log.jsonl"


def _diagnose_read_marker(target_root: Path) -> dict[str, Any] | None:
    """Read the armed marker (the same flat `key: value` shape the hook's capture
    half writes-and-reads). None when absent. Uses the safe YAML loader — the
    marker is trivial scalars, but going through `_load_yaml` keeps the CLI side
    tolerant of a hand-edited marker."""
    path = _diagnose_marker_path(target_root)
    if not path.is_file():
        return None
    return _load_yaml(path)


def _diagnose_is_armed(marker: dict[str, Any] | None, now: float) -> bool:
    """Armed AND unexpired. A malformed/zero-ttl marker reads as not-armed
    (fail-safe — matches the hook's `_armed`)."""
    if not marker:
        return False
    armed_at = marker.get("armed_at")
    ttl = marker.get("ttl_seconds")
    if not isinstance(armed_at, int) or not isinstance(ttl, int) or ttl <= 0:
        return False
    return now < armed_at + ttl


def diagnose_on(target_root: Path, ttl_seconds: int = _DIAGNOSE_DEFAULT_TTL_SECONDS,
                redact: bool = _DIAGNOSE_DEFAULT_REDACT,
                max_entries: int = _DIAGNOSE_DEFAULT_MAX_ENTRIES) -> str:
    """Arm a bounded diagnostic session: write the armed marker with a TTL. While
    armed, the hook appends each deferred decision to the log. Idempotent — re-
    arming refreshes `armed_at` (extends the window) and the cap/redaction knobs.
    """
    import time
    if ttl_seconds <= 0:
        raise PermissionsError("--ttl must be a positive number of seconds.")
    marker = {
        "schema_version": 1,
        "armed_at": int(time.time()),
        "ttl_seconds": int(ttl_seconds),
        "max_entries": int(max_entries),
        "redact": bool(redact),
    }
    # Write the marker as the flat `key: value` shape the hook's stdlib reader
    # parses (no nested structures), via the shared YAML dumper.
    _dump_yaml(_diagnose_marker_path(target_root), marker)
    hours = ttl_seconds / 3600
    return (
        f"diagnostic session armed — capturing deferred (prompted) decisions for "
        f"{hours:.1f}h (auto-expires).\n"
        f"  redaction: {'on (command tail dropped)' if redact else 'OFF (full commands logged)'} · "
        f"size cap: {max_entries} entries (drop-oldest)\n"
        f"  the log is local + git-ignored: {_diagnose_log_path(target_root).relative_to(target_root)}\n"
        f"  run `pkit permissions diagnose report` to see the classified, ranked, "
        f"recommend-only report · `diagnose off` to disarm.\n"
    )


def diagnose_off(target_root: Path) -> str:
    """Disarm: remove the armed marker. The log is left in place (read it with
    `report`; clear it by deleting the file). Idempotent."""
    path = _diagnose_marker_path(target_root)
    if not path.is_file():
        return "diagnostic session already off (no armed marker).\n"
    path.unlink()
    return (
        "diagnostic session disarmed — the hook stops capturing.\n"
        "  the captured log is left in place; run `pkit permissions diagnose report` "
        "to read it, or delete it to clear.\n"
    )


def _diagnose_read_log(target_root: Path) -> list[dict[str, Any]]:
    """Read the captured JSONL log into a list of records. Skips malformed lines
    rather than failing — the report tolerates a partially-written log."""
    path = _diagnose_log_path(target_root)
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def diagnose_status(target_root: Path) -> str:
    """Show armed/expired state + log size. Read-only."""
    import time
    marker = _diagnose_read_marker(target_root)
    now = time.time()
    log = _diagnose_read_log(target_root)
    lines = [cli_render.style("title", "Permission-prompt diagnostics — opt-in capture session (PRJ-006)"), ""]
    if marker is None:
        lines.append("  state    OFF — no armed session; the hook captures nothing")
    elif _diagnose_is_armed(marker, now):
        remaining = int(marker["armed_at"] + marker["ttl_seconds"] - now)
        lines.append(
            f"  state    ARMED — capturing deferred decisions · expires in {remaining // 60} min"
        )
        lines.append(
            f"  config   redaction {'on' if marker.get('redact', True) else 'OFF'} · "
            f"size cap {marker.get('max_entries', _DIAGNOSE_DEFAULT_MAX_ENTRIES)} (drop-oldest)"
        )
    else:
        lines.append(
            "  state    EXPIRED — the marker's TTL has elapsed; the hook captures "
            "nothing. Re-arm with `diagnose on`"
        )
    lines.append(f"  log      {len(log)} captured entry(ies) at "
                 f"{_diagnose_log_path(target_root).relative_to(target_root)}")
    lines += [
        "",
        cli_render.style("heading", "Commands"),
        "  pkit permissions diagnose on [--ttl <s>] [--no-redact]   arm a bounded session",
        "  pkit permissions diagnose off                            disarm",
        "  pkit permissions diagnose report                         the classified, ranked report",
    ]
    return "\n".join(lines) + "\n"


# The group taxonomy (PRJ-006 sub-decision 6: lives in code, not the record —
# it is inventory that churns as the classifier meets real data). Each group is a
# (id, matcher, remediation, band) tuple. `band` is the action contract — the
# classifier is ADVISORY for ranking only (PRJ-006 sub-decision 3): it groups raw
# command text to ORDER and EXPLAIN the report; it never authorizes a change.
#
#   recommend     a remediation we recommend the operator apply (the MVP applies
#                 NOTHING — recommend-only; the auto-fix arc is deferred)
#   judgement     a real trade-off only the operator can settle
#   document      unfixable — document + route around
_DIAGNOSE_GROUPS: list[dict[str, Any]] = [
    {"id": "interpreter", "band": "judgement",
     "heads": {"python", "python3", "node", "ruby", "perl", "sed", "awk"},
     "remediation": "allowlist the interpreter (broad) OR route via a dedicated "
                    "tool / named command — your call"},
    {"id": "shell-shape", "band": "judgement",
     "remediation": "narrow to single commands, or extract a named project "
                    "command (COR-007) the matcher can vet"},
    {"id": "egress", "band": "recommend",
     "heads": {"curl", "wget", "http", "https"},
     "remediation": "if the host maps to a shipped toolkit, recommend "
                    "`pkit permissions sandbox accommodate <toolkit>` "
                    "(toolkit-keyed, never host-keyed — recommend-only)"},
    {"id": "allowlist-gap", "band": "recommend",
     "remediation": "recommend granting the matching catalog privilege (a NEW "
                    "catalog privilege is never auto-fixable — operator task)"},
]
# Shell-shape markers: forms the matcher can't vet without running them.
_DIAGNOSE_SHELL_SHAPE = ("&&", "||", "|", ";", "$(", "`", "<(", ">(", "<<", "for ", "while ")


def _diagnose_command_head(command: str) -> str:
    """The leading program token of a (possibly redacted) command, ignoring a
    leading `env`-style assignment prefix. Best-effort over redacted text."""
    for tok in command.split():
        if "=" in tok and not tok.startswith("-"):
            continue  # skip `FOO=bar` env prefixes
        return tok
    return ""


def _diagnose_classify(record: dict[str, Any]) -> str:
    """Assign a record to a group id. Advisory only (PRJ-006 sub-decision 3):
    re-derives the group from raw command text since the deferral reason carries
    no group signal. The worst case of a misclassification here is a wrong RANK,
    never a wrong change — the MVP applies nothing."""
    command = str(record.get("command", ""))
    if any(marker in command for marker in _DIAGNOSE_SHELL_SHAPE):
        return "shell-shape"
    head = _diagnose_command_head(command)
    for group in _DIAGNOSE_GROUPS:
        heads = group.get("heads")
        if heads and head in heads:
            return group["id"]
    # No specific group matched → the catch-all allowlist-gap (a recognized but
    # ungranted-or-uncovered command).
    return "allowlist-gap"


_DIAGNOSE_BAND_ORDER = ["recommend", "judgement", "document"]
_DIAGNOSE_BAND_HEADING = {
    "recommend": "RECOMMENDED — remediations pkit recommends (MVP applies NOTHING; recommend-only)",
    "judgement": "NEEDS YOUR JUDGEMENT — real trade-offs only you can settle",
    "document": "CAN'T FIX — document & route around",
}


def diagnose_report(target_root: Path) -> str:
    """Render the classified, ranked, recommend-only report over the captured
    log. Read-only and applies NOTHING (PRJ-006 sub-decision 4) — it groups,
    ranks by frequency, and emits a recommended remediation per group, stating
    COVERAGE (the captured signal is a superset of real prompts) rather than a
    predicted prompt-count decrement."""
    import time
    log = _diagnose_read_log(target_root)
    marker = _diagnose_read_marker(target_root)
    armed = _diagnose_is_armed(marker, time.time())

    title = cli_render.style(
        "title", "Permission-prompt diagnosis — captured deferred decisions, classified + ranked"
    )
    state = "ARMED" if armed else ("EXPIRED" if marker else "off")
    header = f"  captured: {len(log)} deferred decision(s) · session: {state}"
    if not log:
        return "\n".join([
            title, "", header, "",
            "  nothing captured yet. Arm a session with `pkit permissions diagnose on`, "
            "work normally, then re-run this report.",
        ]) + "\n"

    by_group: dict[str, list[dict[str, Any]]] = {}
    for rec in log:
        by_group.setdefault(_diagnose_classify(rec), []).append(rec)

    groups_by_id = {g["id"]: g for g in _DIAGNOSE_GROUPS}

    lines = [title, "", header,
             "  note: this is a SUPERSET of real prompts (the hook sees its own "
             "deferral, not whether the harness prompted) — read counts as COVERAGE.",
             ""]

    rank = 0
    for band in _DIAGNOSE_BAND_ORDER:
        band_groups = sorted(
            (gid for gid, recs in by_group.items()
             if groups_by_id.get(gid, {}).get("band", "recommend") == band),
            key=lambda gid: len(by_group[gid]), reverse=True,
        )
        if not band_groups:
            continue
        band_total = sum(len(by_group[gid]) for gid in band_groups)
        lines.append(cli_render.style("heading", _DIAGNOSE_BAND_HEADING[band])
                     + f"   {band_total} deferral(s) · {len(band_groups)} group(s)")
        for gid in band_groups:
            rank += 1
            recs = by_group[gid]
            top = _diagnose_top_commands(recs)
            remediation = groups_by_id.get(gid, {}).get(
                "remediation", "review these commands and decide a remediation")
            lines.append(f"  [{rank}] {gid:14} {len(recs):>3}×   {top}")
            lines.append(f"      → {remediation}")
        lines.append("")

    lines += [
        cli_render.style("strong",
                         "recommend-only: this report applies NOTHING — it ranks + recommends. "
                         "Apply the remediations yourself."),
        "  (auto-fix is deferred per PRJ-006; a new catalog privilege is never auto-fixable.)",
    ]
    return "\n".join(lines) + "\n"


def _diagnose_top_commands(records: list[dict[str, Any]], limit: int = 3) -> str:
    """The most-frequent (redacted) command heads in a group, with counts —
    evidence before verdict, so the classification is trusted."""
    counts: dict[str, int] = {}
    for rec in records:
        key = str(rec.get("command") or rec.get("tool") or "?")
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return " · ".join(f"{cmd} ({n}×)" for cmd, n in ranked)
