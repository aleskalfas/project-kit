#!/usr/bin/env python3
"""storyboards/parser.py — core storyboard markdown parser.

Turns a storyboard .md file into a structured tree.  Knows about the
document structure (H1 title, Step headings, fenced blocks, prose)
but nothing about what specific fence language tags mean.  All
directive-level semantics are left to plugins.

Output tree shape::

    {
      "title":       str,
      "intro_prose": str,          # prose before the first Step heading
      "steps": [
        {
          "number": int,
          "title":  str,
          "prose":  str,           # all non-fence text in the step body
          "fences": [
            {
              "lang":    str,      # fence language tag (may be empty "")
              "content": str,      # text between the opening and closing ```
              "line":    int,      # 1-based line number of the opening ```
            },
            ...
          ],
        },
        ...
      ],
    }

Structural validation only — errors include line numbers.

CLI::

    parser.py <storyboard.md>             # emit JSON tree (stdout)
    parser.py <storyboard.md> --validate  # pretty-print tree + errors, exit 0/1
    parser.py <storyboard.md> --json      # same as default but explicit
"""

import json
import re
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(text: str) -> tuple[dict[str, Any], list[str]]:
    """Parse storyboard markdown text.

    Returns (tree, errors) where errors is a list of human-readable diagnostic
    strings (each may cite a line number).  A non-empty errors list means at
    least one structural problem was found; the returned tree is still as
    complete as possible (best-effort).
    """
    lines = text.splitlines()
    errors: list[str] = []

    # ---- strip optional YAML frontmatter (--- ... ---) --------------------
    # We detect it but do nothing with it — v1 storyboards don't use it.
    body_start = 0
    if lines and lines[0].strip() == "---":
        # find closing ---
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is not None:
            body_start = end + 1
        # else: unclosed frontmatter — treat whole file as body

    effective_lines = lines[body_start:]

    # ---- H1 title ----------------------------------------------------------
    title = ""
    title_line = None
    for i, ln in enumerate(effective_lines):
        m = re.match(r"^#\s+(.+)$", ln)
        if m:
            title = m.group(1).strip()
            title_line = body_start + i + 1  # 1-based global line number
            break

    if not title:
        errors.append("line 1: no H1 title found (expected '# <title>' near the top)")

    # ---- split into preamble + step sections -------------------------------
    # We split on `## Step N` headings.
    # Sections are: [preamble_lines, (num, title, body_lines), ...]
    #
    # We preserve original line numbers by passing the global offset.

    # Build a list of (line_number_1based, step_number, step_title)
    step_starts: list[tuple[int, int, str]] = []
    for i, ln in enumerate(effective_lines):
        m = re.match(
            r"^##\s+Step\s+(\d+)(?:\s+(?:—|--|-)?\s*(.+))?\s*$", ln
        )
        if m:
            step_num = int(m.group(1))
            step_title = (m.group(2) or "").strip()
            # Also handle em-dash: "## Step 2 — bind the tmux panes"
            # The regex above already captures everything after the number,
            # but strip leading dashes/em-dashes from the title.
            step_title = re.sub(r"^(?:—|--|-)?\s*", "", step_title).strip()
            global_line = body_start + i + 1
            step_starts.append((global_line, step_num, step_title))

    # Validate step numbering — numbers should be unique (they needn't be
    # contiguous, but duplicates are always a mistake).
    seen_nums: set[int] = set()
    for ln_no, snum, _ in step_starts:
        if snum in seen_nums:
            errors.append(
                f"line {ln_no}: duplicate Step {snum} — step numbers must be unique"
            )
        seen_nums.add(snum)

    # ---- extract intro prose (before the first Step heading) ---------------
    intro_lines: list[str] = []
    if step_starts:
        first_step_global_line = step_starts[0][0]
        # effective_lines index of that line
        first_idx = first_step_global_line - body_start - 1
        intro_lines = effective_lines[:first_idx]
    else:
        # No steps at all — everything is intro
        intro_lines = effective_lines[:]

    # Remove the H1 line from intro_lines (it's in title already)
    if title_line is not None:
        idx_in_intro = title_line - body_start - 1
        if 0 <= idx_in_intro < len(intro_lines):
            intro_lines = (
                intro_lines[:idx_in_intro] + intro_lines[idx_in_intro + 1 :]
            )

    intro_prose = _join_prose(intro_lines)

    # ---- parse each step body ----------------------------------------------
    steps: list[dict[str, Any]] = []

    for idx, (start_line, step_num, step_title) in enumerate(step_starts):
        # Determine end line (exclusive) of this step's body
        if idx + 1 < len(step_starts):
            end_line = step_starts[idx + 1][0]
        else:
            end_line = body_start + len(effective_lines) + 1

        # Slice the step body (lines AFTER the heading line)
        body_lines_start = start_line - body_start  # index into effective_lines
        body_lines_end = end_line - body_start - 1
        step_body_lines = effective_lines[body_lines_start:body_lines_end]
        step_body_global_offset = start_line  # line number of heading; body starts +1

        step, step_errors = _parse_step_body(
            step_num, step_title, step_body_lines, step_body_global_offset
        )
        errors.extend(step_errors)
        steps.append(step)

    tree: dict[str, Any] = {
        "title": title,
        "intro_prose": intro_prose,
        "steps": steps,
    }
    return tree, errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_step_body(
    num: int,
    title: str,
    body_lines: list[str],
    body_global_offset: int,
) -> tuple[dict[str, Any], list[str]]:
    """Parse the body lines of one step.

    body_global_offset is the 1-based line number of the *heading* line;
    body_lines[0] is the line immediately after it, so its 1-based number is
    body_global_offset + 1.
    """
    errors: list[str] = []
    fences: list[dict[str, Any]] = []
    prose_lines: list[str] = []

    i = 0
    while i < len(body_lines):
        ln = body_lines[i]
        global_line = body_global_offset + 1 + i  # 1-based

        # Opening fence: ``` optionally followed by a language tag
        fence_open = re.match(r"^```(\S*).*$", ln)
        if fence_open:
            lang = fence_open.group(1)
            fence_start_line = global_line
            content_lines: list[str] = []
            i += 1
            closed = False
            while i < len(body_lines):
                inner = body_lines[i]
                if re.match(r"^```\s*$", inner):
                    closed = True
                    i += 1
                    break
                content_lines.append(inner)
                i += 1
            if not closed:
                errors.append(
                    f"line {fence_start_line}: unclosed fenced block "
                    f"(lang={lang!r}) — missing closing ```"
                )
            fences.append(
                {
                    "lang": lang,
                    "content": "\n".join(content_lines),
                    "line": fence_start_line,
                }
            )
        else:
            prose_lines.append(ln)
            i += 1

    prose = _join_prose(prose_lines)

    step: dict[str, Any] = {
        "number": num,
        "title": title,
        "prose": prose,
        "fences": fences,
    }
    return step, errors


def _join_prose(lines: list[str]) -> str:
    """Join prose lines, collapsing runs of blank lines to a single newline."""
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _emit_json(tree: dict[str, Any]) -> None:
    print(json.dumps(tree, indent=2, ensure_ascii=False))


def _emit_validate(tree: dict[str, Any], errors: list[str]) -> int:
    """Pretty-print the parsed tree and any errors.  Returns exit code."""
    print(f"Storyboard: {tree['title'] or '(no title)'}")
    print()

    if tree["intro_prose"]:
        snippet = tree["intro_prose"]
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        print(f"  Intro: {snippet!r}")
        print()

    if not tree["steps"]:
        print("  (no steps found)")
    else:
        for s in tree["steps"]:
            suffix = f" — {s['title']}" if s["title"] else ""
            print(f"Step {s['number']}{suffix}")
            if s["fences"]:
                for f in s["fences"]:
                    tag = f["lang"] or "(no lang)"
                    snippet = f["content"]
                    if len(snippet) > 60:
                        snippet = snippet[:57] + "..."
                    print(f"  fence [{tag}] line {f['line']}: {snippet!r}")
            else:
                print("  (no fences)")
            print()

    if errors:
        print(f"\n✗ {len(errors)} structural error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    n = len(tree["steps"])
    print(f"✓ {n} step(s) parsed.  No structural errors.")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__, file=sys.stderr)
        return 0 if len(sys.argv) > 1 else 2

    path = sys.argv[1]
    validate = "--validate" in sys.argv[2:]
    # --json is the default / explicit alias
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        print(f"parser.py: cannot read {path}: {exc}", file=sys.stderr)
        return 1

    tree, errors = parse(text)

    if validate:
        return _emit_validate(tree, errors)

    # Default: emit JSON
    if errors:
        for e in errors:
            print(f"parser.py: {e}", file=sys.stderr)
        return 1
    _emit_json(tree)
    return 0


if __name__ == "__main__":
    sys.exit(main())
