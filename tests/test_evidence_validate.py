"""Tests for the evidence citation validator
(`.pkit/capabilities/evidence/scripts/validate.py`).

Run as a subprocess against throwaway scopes — the validator is a standalone
PEP-723 script (uv resolves its `ruamel.yaml` dep), not a package module.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VALIDATE = REPO / ".pkit" / "capabilities" / "evidence" / "scripts" / "validate.py"


def _scope(tmp_path: Path, *, records: list[str], files: dict[str, str]) -> Path:
    scope = tmp_path / "scope"
    scope.mkdir()
    if records:
        body = "\n".join(
            f"  - id: {r}\n"
            f"    source_url: https://example.com\n"
            f"    fetched_at: 2026-01-01\n"
            f"    excerpt: grounding text"
            for r in records
        )
        evidence = f"schema_version: 1\nrecords:\n{body}\n"
    else:
        evidence = "schema_version: 1\nrecords: []\n"
    (scope / "evidence.yaml").write_text(evidence, encoding="utf-8")
    for name, content in files.items():
        (scope / name).write_text(content, encoding="utf-8")
    return scope


def _run(scope: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(VALIDATE), *args, str(scope)], capture_output=True, text=True, check=False
    )


def test_yaml_block_scalar_fence_does_not_swallow_citation(tmp_path: Path) -> None:
    """Regression: ``` inside a YAML block scalar must NOT strip a citation that
    follows it. Before the markdown-only fix, the fenced-block stripping ran over
    YAML too, silently dropping the citation (false pass)."""
    yaml_file = (
        "trip:\n"
        "  notes: |\n"
        "    Example config snippet:\n"
        "    ```\n"
        "    key: value\n"
        "    ```\n"
        "    Booked via the partner fare [ev:ghost-cite].\n"
    )
    scope = _scope(tmp_path, records=[], files={"trip.yaml": yaml_file})
    result = _run(scope)
    # `ghost-cite` resolves to no record → must be flagged, not silently dropped.
    assert result.returncode != 0, result.stdout + result.stderr
    assert "ghost-cite" in (result.stdout + result.stderr)


def test_yaml_citation_after_fence_resolves(tmp_path: Path) -> None:
    """A *valid* citation following a ``` in a YAML block scalar is counted."""
    yaml_file = (
        "notes: |\n"
        "  ```\n"
        "  example\n"
        "  ```\n"
        "  A grounded fact [ev:real-fact].\n"
    )
    scope = _scope(tmp_path, records=["real-fact"], files={"data.yaml": yaml_file})
    result = _run(scope)
    assert result.returncode == 0, result.stdout + result.stderr


def test_yaml_comment_citation_is_counted(tmp_path: Path) -> None:
    """A citation in a YAML `#` comment resolves (comments are not skip-regions)."""
    yaml_file = "start: 2026-07-11  # Saturday [ev:trip-dates]\n"
    scope = _scope(tmp_path, records=["trip-dates"], files={"trip.yaml": yaml_file})
    assert _run(scope).returncode == 0


def test_markdown_fence_is_still_stripped(tmp_path: Path) -> None:
    """No regression: example tokens inside a markdown fenced block are NOT
    counted (the markdown skip-region still applies to `.md`)."""
    md = (
        "A real claim [ev:real].\n\n"
        "```\n"
        "show the token form [ev:example-only] inside a code block\n"
        "```\n"
    )
    scope = _scope(tmp_path, records=["real"], files={"doc.md": md})
    result = _run(scope)
    # `example-only` is inside a fence → ignored → no unresolved-citation error.
    assert result.returncode == 0, result.stdout + result.stderr
