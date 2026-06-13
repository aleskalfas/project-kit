"""Scratchpad-note authoring and state transitions (per COR-012).

The deterministic part of `pkit new scratchpad` and `pkit scratchpad
<done|drop>`: file stamping, state-folder transitions, frontmatter
updates. The conversational layer (slug judgement, topic boundary,
body-drafting opening) is the `scratchpad-author` skill's job per
COR-005's "Skill / command pairing".
"""

from __future__ import annotations

import datetime as _dt
import io
import re
import subprocess
from pathlib import Path
from typing import Literal

import click
from ruamel.yaml import YAML

RetiredState = Literal["done", "dropped"]

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


ACTIVE_TEMPLATE = """\
---
authors:
  - {author}
started: {today}
---

# {title}
"""


def stamp_new_scratchpad(target_root: Path, slug: str, dry_run: bool = False) -> Path:
    """Stamp a new active-state scratchpad note.

    Path: `.pkit/scratchpad/active/<YYYY-MM-DD>-<slug>.md`. Frontmatter
    is seeded with `authors` (from git config) and `started` (today).
    Body opens with a level-1 heading derived from the slug — the author
    edits it on first pass.
    """
    _validate_slug(slug)
    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    active_dir = scratchpad_dir / "active"
    if not active_dir.is_dir():
        raise click.ClickException(
            f"{active_dir.relative_to(target_root)} does not exist. "
            f"Run 'pkit init' from this project's root first."
        )

    today = _today()
    target = active_dir / f"{today}-{slug}.md"
    if target.exists():
        raise click.ClickException(
            f"a scratchpad note already exists at {target.relative_to(target_root)}."
        )
    # Slugs are unique across the area, not just per state — refuse if
    # the same slug already lives in done/ or dropped/.
    existing = _find_in_any_state(scratchpad_dir, slug)
    if existing is not None:
        raise click.ClickException(
            f"slug {slug!r} already used by {existing.relative_to(target_root)}."
        )

    title = _slug_to_title(slug)
    content = ACTIVE_TEMPLATE.format(author=_resolve_author(), today=today, title=title)
    if not dry_run:
        target.write_text(content, encoding="utf-8")
    return target


def transition_to_done(
    target_root: Path,
    slug: str,
    produced: tuple[str, ...] = (),
    dry_run: bool = False,
) -> tuple[Path, Path]:
    """Move a note from active/ to done/, appending retired/produced frontmatter."""
    return _transition(target_root, slug, "done", produced=produced, dry_run=dry_run)


def transition_to_dropped(
    target_root: Path, slug: str, dry_run: bool = False
) -> tuple[Path, Path]:
    """Move a note from active/ to dropped/, appending retired frontmatter."""
    return _transition(target_root, slug, "dropped", produced=(), dry_run=dry_run)


def _transition(
    target_root: Path,
    slug: str,
    to_state: RetiredState,
    *,
    produced: tuple[str, ...],
    dry_run: bool,
) -> tuple[Path, Path]:
    scratchpad_dir = target_root / ".pkit" / "scratchpad"
    active_dir = scratchpad_dir / "active"
    if not active_dir.is_dir():
        raise click.ClickException(f"{active_dir.relative_to(target_root)} does not exist.")

    src = _resolve_in_state(active_dir, slug)
    if src is None:
        raise click.ClickException(
            f"no active scratchpad note matches {slug!r} in "
            f"{active_dir.relative_to(target_root)}."
        )

    dst_dir = scratchpad_dir / to_state
    dst = dst_dir / src.name
    if dst.exists():
        raise click.ClickException(f"target already exists at {dst.relative_to(target_root)}.")

    new_content = _add_retirement_frontmatter(src.read_text(encoding="utf-8"), produced=produced)
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst.write_text(new_content, encoding="utf-8")
        src.unlink()
    return src, dst


def _add_retirement_frontmatter(content: str, *, produced: tuple[str, ...]) -> str:
    """Parse YAML frontmatter, append `retired` (and optionally `produced`), re-serialise."""
    yaml = YAML()
    yaml.preserve_quotes = True
    # Match the indentation style of the stamped active-state notes:
    #   authors:
    #     - Name <email>
    yaml.indent(mapping=2, sequence=4, offset=2)

    fm_yaml, body = _split_frontmatter(content)
    data = yaml.load(io.StringIO(fm_yaml)) or {}
    if not isinstance(data, dict):
        raise click.ClickException("scratchpad note has malformed frontmatter (not a mapping).")

    # Use a date object (not a string) so ruamel.yaml serialises bare
    # (`retired: 2026-05-12`), not quoted (`retired: '2026-05-12'`).
    data["retired"] = _today_date()
    if produced:
        data["produced"] = list(produced)

    out = io.StringIO()
    yaml.dump(data, out)
    return f"---\n{out.getvalue()}---\n\n{body}"


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split a markdown file into (frontmatter_yaml, body). Both strings."""
    if not content.startswith("---"):
        raise click.ClickException("scratchpad note has no frontmatter block.")
    after_open = content[len("---") :].lstrip("\n")
    end_match = re.search(r"^---\s*$", after_open, re.MULTILINE)
    if not end_match:
        raise click.ClickException("scratchpad note has no closing frontmatter delimiter.")
    fm_yaml = after_open[: end_match.start()]
    body = after_open[end_match.end() :].lstrip("\n")
    return fm_yaml, body


def _resolve_in_state(state_dir: Path, slug: str) -> Path | None:
    """Find a scratchpad note by slug (kebab portion) or full filename."""
    if slug.endswith(".md"):
        candidate = state_dir / slug
        return candidate if candidate.is_file() else None
    matches = list(state_dir.glob(f"*-{slug}.md"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        raise click.ClickException(
            f"slug {slug!r} matches multiple notes: {names}. "
            f"Pass the full filename to disambiguate."
        )
    return None


def _find_in_any_state(scratchpad_dir: Path, slug: str) -> Path | None:
    """Search all three state folders for a note with this slug."""
    for state in ("active", "done", "dropped"):
        state_dir = scratchpad_dir / state
        if not state_dir.is_dir():
            continue
        try:
            match = _resolve_in_state(state_dir, slug)
        except click.ClickException:
            continue
        if match is not None:
            return match
    return None


def _slug_to_title(slug: str) -> str:
    """Convert kebab-case slug to a Title Case starting point for the H1.

    The author edits the H1 to whatever reads best; this is just a seed.
    """
    return slug.replace("-", " ").capitalize()


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise click.ClickException(
            "slug must be kebab-case (lowercase letters, digits, single hyphens)."
        )


def _today() -> str:
    """Today's date as ISO 8601 (`YYYY-MM-DD`). Indirected for test pinning."""
    return _today_date().isoformat()


def _today_date() -> _dt.date:
    """Today as a `datetime.date`. Indirected for test pinning; used directly
    when handing the value to a YAML serialiser that distinguishes date
    objects from strings (bare vs quoted scalar)."""
    return _dt.date.today()


def _resolve_author() -> str:
    """Read git config user.name / user.email; format as `Name <email>`."""
    name = _git_config("user.name")
    email = _git_config("user.email")
    if name and email:
        return f"{name} <{email}>"
    if name:
        return name
    return "<unknown>"


def _git_config(key: str) -> str:
    try:
        result = subprocess.run(["git", "config", key], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
