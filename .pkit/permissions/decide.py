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
import re
from typing import Any

# A grant's privilege value is the COR-019 token `[privilege-catalog:<id>]`
# (or a list of them); strip to the bare id for matching against the catalog.
_TOKEN = re.compile(r"^\[privilege-catalog:([a-z][a-z0-9-]*)\]$")
_SEP = re.compile(r"\s*(?:&&|\|\||\||;)\s*")
_ENVVAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


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


# ---- subjects, scope, decision ---------------------------------------------

def _privilege_ids(value: Any) -> set[str]:
    """Normalise a grant's `privilege` (token or list of tokens) to bare ids."""
    vals = value if isinstance(value, list) else [value]
    out: set[str] = set()
    for v in vals:
        m = _TOKEN.match(v) if isinstance(v, str) else None
        out.add(m.group(1) if m else v)
    return out


def _scope_ok(scope: list[str] | None, cwd: str) -> bool:
    if not scope:
        return True  # anywhere
    return any(
        fnmatch.fnmatch(cwd, pat) or fnmatch.fnmatch(cwd, pat.rstrip("*") + "*")
        for pat in scope
    )


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

    `request` = {type: "bash"|"tool", command|tool, cwd, subject}. Effective
    grants = baseline (`all`) ∪ the subject's own grants; deny wins; a scoped
    allow denies the privilege outside its scope.
    """
    posture = posture or model.get("posture", "lenient")
    subject = request["subject"]
    hits = recognized_privileges(catalog, request)
    matched_allow = False
    for g in _effective_grants(model, subject):
        privs = _privilege_ids(g.get("privilege"))
        overlap = hits & privs
        if not overlap:
            continue
        if g.get("effect", "allow") == "deny":
            return "deny", f"deny grant for {subject} on {sorted(overlap)}"
        if _scope_ok(g.get("scope"), request.get("cwd", "")):
            matched_allow = True
        else:
            return "deny", (
                f"{sorted(overlap)} allowed for {subject} only in "
                f"{g.get('scope')}, not {request.get('cwd')!r}"
            )
    if matched_allow:
        return "allow", f"allow grant for {subject} on {sorted(hits)}"
    if posture == "strict":
        return "deny", "strict posture: nothing grants this request"
    return "abstain", "lenient posture: defer to the harness's normal flow"


def hook_decide(
    model: dict[str, Any], catalog: dict[str, Any], payload: dict[str, Any]
) -> tuple[str, str]:
    """Decision-core entry point for a PreToolUse hook payload. Fails OPEN —
    any fault yields abstain (defer), never a silent block; non-negotiable
    denies are double-locked in the fail-closed native settings (ADR-002)."""
    try:
        agent_type = payload.get("agent_type")
        subject = f"agent:{agent_type}" if agent_type else "operator"
        tool = payload["tool_name"]
        if tool == "Bash":
            request = {
                "type": "bash",
                "command": payload["tool_input"]["command"],
                "cwd": payload.get("cwd", ""),
                "subject": subject,
            }
        else:
            request = {
                "type": "tool",
                "tool": tool,
                "cwd": payload.get("cwd", ""),
                "subject": subject,
            }
        return decide(model, catalog, request)
    except Exception as exc:  # fail-open
        return "abstain", f"hook fault → fail-open: {exc!r}"


# ---- thin loaders ----------------------------------------------------------

def load_yaml(path: str) -> dict[str, Any]:
    # Local import keeps the pure decide() path dependency-free. ruamel.yaml
    # is the kit-wide YAML library; the hook (a PEP723 `uv run --script`)
    # declares it as a dep so the loader is available in the adopter tree too.
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    with open(path, encoding="utf-8") as fh:
        return yaml.load(fh) or {}


def _exists(path: str) -> bool:
    import os.path

    return os.path.isfile(path)


def load_catalog(target_root: str) -> dict[str, Any]:
    """Load the privilege catalog from a target tree's standard location."""
    import os.path

    path = os.path.join(target_root, ".pkit", "schemas", "privilege-catalog.yaml")
    return load_yaml(path) if _exists(path) else {}


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


def _active_profile_grants(target_root: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Grants contributed by the active permission profile (per ADR-005), if any.

    The profile is a LAYER, never an owner: its grants sit between the guardrail
    denies and the adopter's own grants.yaml, and the adopter's grants are
    unioned last so a manual `grant`/`revoke` is never overwritten by a profile.
    Resolves the active profile name (`config.active_profile`) project-first
    (`project/profiles/<name>.yaml`) then shipped (`profiles/<name>.yaml`)."""
    import os.path

    name = config.get("active_profile")
    if not name:
        return []
    for base in (
        os.path.join(target_root, ".pkit", "permissions", "project", "profiles"),
        os.path.join(target_root, ".pkit", "permissions", "profiles"),
    ):
        path = os.path.join(base, f"{name}.yaml")
        if _exists(path):
            return list(load_yaml(path).get("grants", []) or [])
    return []


def load_model(target_root: str, catalog: dict[str, Any]) -> dict[str, Any]:
    """Build the effective permission model for a target tree: the catalog-
    derived guardrail denies, then the active profile's grant-layer, then the
    adopter's authored grants — unioned in that order — plus posture/
    ownership_mode from project config.

    This is the SINGLE model loader (ADR-002's same-code invariant): the
    PreToolUse hook and the `pkit permissions` CLI both call it, so they decide
    and display from byte-identical models. Order is guardrails → profile →
    adopter (adopter last so manual grants are never clobbered, per ADR-005);
    `decide()` is deny-wins and order-independent regardless.
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
        "active_profile": config.get("active_profile"),
        "grants": (
            guardrail_denies(catalog)
            + _active_profile_grants(target_root, config)
            + list(grants_doc.get("grants", []) or [])
        ),
    }
