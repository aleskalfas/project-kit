"""Residual-placeholder detection for issue (and PR) bodies.

Reusable helper factored from validate-issue.py per DEC-031 so the
PR-side validator (#12) can import it without duplicating the logic.

Two signals (per DEC-031):

  1. *Empty required checkbox section* — a required checkbox section
     (as declared in body-format.yaml, ``has_checkboxes: true``) whose
     body contains zero *filled* items (``- [x]`` / ``- [X]``).
     Severity is phase-dependent: ``warning`` at create, ``hard-reject``
     at the first transition onward.  A trailing unfilled ``- [ ]``
     *alongside* real filled items is fine (lenient rule).

  2. *Surviving template placeholder prose* — text lines extracted at
     runtime from the matching ``templates/<Type>.md`` that still appear
     verbatim in the body.  Severity is always ``warning``.

The template fingerprint is derived at runtime so it stays in sync
automatically when a template is edited; no sentinel marker is added to
any template.
"""

from __future__ import annotations

import re
from pathlib import Path


# ---- template fingerprint extraction --------------------------------


def extract_placeholder_phrases(template_path: Path) -> list[str]:
    """Return prose lines from *template_path* that are placeholder text.

    The returned list contains the verbatim lines that an author is
    expected to replace.  Any line matching one of the skip patterns
    below is excluded:

    - YAML front-matter block (``---`` ... ``---``)
    - HTML comment blocks (``<!--`` ... ``-->``)
    - Markdown headings (``## ...``)
    - Checkbox lines (``- [ ]``, ``- [x]``, ``- [X]``)
    - Parent-ref placeholder lines (``Label: #``, ``Milestone: #``)
    - Blank lines

    The resulting strings are stripped of surrounding whitespace.
    """
    if not template_path.is_file():
        return []

    raw = template_path.read_text(encoding="utf-8")
    body = _strip_frontmatter(raw)
    lines = _strip_html_comments(body).splitlines()

    phrases: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        # Checkbox lines: empty or any state.
        if re.match(r"^-\s*\[[ xX?]\]", stripped):
            continue
        # Parent-ref placeholder: "Label: #" with nothing after the #.
        if re.match(r"^[A-Za-z]+:\s+#\s*$", stripped):
            continue
        # Milestone link placeholder: "Milestone: [#](../milestone/)" variants.
        if re.match(r"^Milestone:\s+\[?#\]?", stripped):
            continue
        phrases.append(stripped)

    return phrases


def _strip_frontmatter(raw: str) -> str:
    """Remove a leading ``---\\n...---\\n`` block if present."""
    if not raw.startswith("---\n"):
        return raw
    end = raw.find("\n---\n", 4)
    if end < 0:
        return raw
    return raw[end + len("\n---\n"):]


def _strip_html_comments(text: str) -> str:
    """Remove HTML comment blocks (``<!-- ... -->``, possibly multi-line)."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


# ---- checkbox-section detection -------------------------------------


def _filled_checkbox_re() -> re.Pattern[str]:
    """Regex matching a ticked checkbox item line."""
    return re.compile(r"^\s*-\s*\[[xX]\]", re.MULTILINE)


def _section_body(body: str, heading: str) -> str:
    """Extract the text between *heading* and the next ``##``-level heading.

    Returns an empty string when the heading is absent.
    """
    pattern = re.compile(
        r"^" + re.escape(heading) + r"\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(body)
    return m.group(1) if m else ""


def has_filled_checkbox_items(body: str, heading: str) -> bool:
    """Return True iff the section *heading* contains at least one filled item."""
    section = _section_body(body, heading)
    return bool(_filled_checkbox_re().search(section))


# ---- public API ------------------------------------------------------


PHASE_CREATE = "create"
PHASE_TRANSITION = "transition"


def detect_placeholder_residuals(
    *,
    body: str,
    structural_type: str,
    body_format: dict,
    capability_root: Path,
    phase: str = PHASE_TRANSITION,
) -> list[tuple[str, str, str]]:
    """Return a list of ``(severity, label, detail)`` tuples for placeholder findings.

    Parameters
    ----------
    body:
        The raw issue body text.
    structural_type:
        Lowercase structural type name (``"task"``, ``"epic"``, etc.).
    body_format:
        Parsed ``body-format.yaml`` data.
    capability_root:
        Path to the installed capability directory — used to locate
        ``templates/<Type>.md``.
    phase:
        ``"create"`` or ``"transition"`` (default).  Controls severity
        of the empty-checkbox-section signal.

    Returns
    -------
    list of ``(severity, label, detail)`` triples — empty when clean.
    """
    results: list[tuple[str, str, str]] = []

    # --- signal 1: empty required checkbox sections ------------------
    bodies_block = body_format.get("bodies") or {}
    type_body = bodies_block.get(structural_type)
    if isinstance(type_body, dict):
        required = type_body.get("required_sections") or []
        for section in required:
            if not isinstance(section, dict):
                continue
            if not section.get("has_checkboxes"):
                continue
            heading = str(section.get("heading", ""))
            if not heading:
                continue
            if heading not in body:
                # Section is missing — the required-section check fires
                # separately; skip here to avoid double-reporting.
                continue
            if not has_filled_checkbox_items(body, heading):
                severity = (
                    "warning" if phase == PHASE_CREATE else "hard-reject"
                )
                results.append((
                    severity,
                    "body.placeholder.empty-checkbox-section",
                    f"section {heading!r} has no filled items — "
                    f"body appears to be an unedited template skeleton.",
                ))

    # --- signal 2: surviving placeholder prose -----------------------
    # Locate the template for this structural type.  The title_prefix
    # from issue-types.yaml is the file stem (e.g. "EPIC", "Feature").
    # We resolve it by scanning templates/ for a case-insensitive match
    # rather than depending on the full schema being in memory here.
    template_path = _resolve_template(structural_type, capability_root)
    if template_path is not None:
        phrases = extract_placeholder_phrases(template_path)
        surviving = [p for p in phrases if p in body]
        if surviving:
            sample = surviving[0]
            results.append((
                "warning",
                "body.placeholder.template-prose",
                f"body still contains template placeholder text "
                f"(e.g. {sample!r}). Replace placeholder prose with "
                f"actual content.",
            ))

    return results


def _resolve_template(structural_type: str, capability_root: Path) -> Path | None:
    """Find the template file for *structural_type* under *capability_root/templates/*.

    Tries exact capitalisation variants (e.g. ``EPIC``, ``Epic``,
    ``epic``) before giving up.
    """
    templates_dir = capability_root / "templates"
    if not templates_dir.is_dir():
        return None
    # Build candidate stems from the structural type string.
    candidates = [
        structural_type.upper(),
        structural_type.capitalize(),
        structural_type.lower(),
        structural_type,
    ]
    for stem in candidates:
        p = templates_dir / f"{stem}.md"
        if p.is_file():
            return p
    return None
