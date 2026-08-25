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

Pure formatting + config reading: no `gh` wiring, so it is unit-testable
without a live repo.
"""

from __future__ import annotations

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
