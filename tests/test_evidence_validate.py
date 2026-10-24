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
    yaml_file = "notes: |\n  ```\n  example\n  ```\n  A grounded fact [ev:real-fact].\n"
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


def _evidence(records: list[str]) -> str:
    """An evidence.yaml body holding one well-formed record per slug."""
    if not records:
        return "schema_version: 1\nrecords: []\n"
    body = "\n".join(
        f"  - id: {r}\n"
        f"    source_url: https://example.com\n"
        f"    fetched_at: 2026-01-01\n"
        f"    excerpt: grounding text"
        for r in records
    )
    return f"schema_version: 1\nrecords:\n{body}\n"


def _output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


# --- each scope is checked on its own (DEC-002, DEC-003) -------------------


def test_nested_scope_is_left_out_of_the_outer_run(tmp_path: Path) -> None:
    """A directory with an evidence.yaml of its own is its own scope. The outer
    run neither checks its citations against the outer records nor reads its
    evidence.yaml as citing text."""
    scope = _scope(tmp_path, records=["outer-fact"], files={"doc.md": "A [ev:outer-fact].\n"})
    inner = scope / "inner"
    inner.mkdir()
    (inner / "evidence.yaml").write_text(
        "schema_version: 1\n"
        "records:\n"
        "  - id: inner-fact\n"
        "    source_url: https://example.com\n"
        "    fetched_at: 2026-01-01\n"
        "    excerpt: A quoted token [ev:quoted-token] from the source.\n",
        encoding="utf-8",
    )
    (inner / "doc.md").write_text("B [ev:inner-fact].\n", encoding="utf-8")
    result = _run(scope)
    assert result.returncode == 0, _output(result)
    assert "1 citation(s) validated" in _output(result)


def test_nested_scope_citation_leaves_the_outer_record_an_orphan(tmp_path: Path) -> None:
    """A citation in a nested scope never names a record of the outer scope."""
    scope = _scope(tmp_path, records=["shared"], files={})
    inner = scope / "inner"
    inner.mkdir()
    (inner / "evidence.yaml").write_text(_evidence(["shared"]), encoding="utf-8")
    (inner / "doc.md").write_text("B [ev:shared].\n", encoding="utf-8")
    result = _run(scope, "--strict")
    assert result.returncode == 1, _output(result)
    assert "orphan record 'shared'" in _output(result)


def test_directory_above_a_nested_scope_stays_in_the_outer_scope(tmp_path: Path) -> None:
    """Only the directory holding the nested evidence.yaml is left out; a
    directory between the two scopes still belongs to the outer one."""
    scope = _scope(tmp_path, records=[], files={})
    middle = scope / "middle"
    inner = middle / "inner"
    inner.mkdir(parents=True)
    (inner / "evidence.yaml").write_text(_evidence([]), encoding="utf-8")
    (middle / "doc.md").write_text("A [ev:missing-fact].\n", encoding="utf-8")
    result = _run(scope)
    assert result.returncode == 1, _output(result)
    assert "middle/doc.md:1 — cited slug 'missing-fact' has no record." in _output(result)


# --- fenced code is skipped (DEC-003) ---------------------------------------


def test_fence_indented_in_a_list_item_is_skipped(tmp_path: Path) -> None:
    md = (
        "- A real claim [ev:real].\n"
        "- An example:\n"
        "\n"
        "  ```md\n"
        "  The token form [ev:example-only].\n"
        "  ```\n"
        "\n"
        "  ~~~\n"
        "  Another [ev:tilde-example].\n"
        "  ~~~\n"
    )
    scope = _scope(tmp_path, records=["real"], files={"doc.md": md})
    result = _run(scope)
    assert result.returncode == 0, _output(result)


def test_fence_in_a_block_quote_is_skipped(tmp_path: Path) -> None:
    md = "A real claim [ev:real].\n\n> ```\n> [ev:quoted-example]\n> ```\n"
    scope = _scope(tmp_path, records=["real"], files={"doc.md": md})
    result = _run(scope)
    assert result.returncode == 0, _output(result)


def test_citation_after_an_indented_fence_counts(tmp_path: Path) -> None:
    md = "- Item:\n\n  ```\n  code\n  ```\n\n  After it [ev:missing-after].\n"
    scope = _scope(tmp_path, records=[], files={"doc.md": md})
    result = _run(scope)
    assert result.returncode == 1, _output(result)
    assert "doc.md:7 — cited slug 'missing-after' has no record." in _output(result)


def test_fence_closes_only_on_a_run_as_long_as_its_opening(tmp_path: Path) -> None:
    """A four-backtick fence holding a three-backtick line closes on four."""
    md = "````md\n```\n[ev:inside-example]\n```\n````\nOutside [ev:missing-outside].\n"
    scope = _scope(tmp_path, records=[], files={"doc.md": md})
    result = _run(scope)
    assert result.returncode == 1, _output(result)
    assert "inside-example" not in _output(result)
    assert "doc.md:6 — cited slug 'missing-outside' has no record." in _output(result)


def test_unclosed_fence_drops_no_citation(tmp_path: Path) -> None:
    md = "```\nA claim after a stray fence [ev:missing-fact].\n"
    scope = _scope(tmp_path, records=[], files={"doc.md": md})
    assert _run(scope).returncode == 1


# --- a missing required field is a finding (DEC-003) ------------------------


def test_record_with_no_id_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    scope = tmp_path / "scope"
    scope.mkdir()
    (scope / "evidence.yaml").write_text(
        "schema_version: 1\n"
        "records:\n"
        "  - source_url: https://example.com\n"
        "    fetched_at: 2026-01-01\n"
        "    excerpt: grounding text\n"
        "  - id: real\n"
        "    source_url: https://example.com\n"
        "    fetched_at: 2026-01-01\n"
        "    excerpt: grounding text\n",
        encoding="utf-8",
    )
    (scope / "doc.md").write_text("A [ev:real] and [ev:missing-fact].\n", encoding="utf-8")
    result = _run(scope)
    out = _output(result)
    assert result.returncode == 1, out
    assert "Traceback" not in out
    assert "evidence.yaml#records[1] — record missing required field 'id'." in out
    # The path goes on: the citations are still checked.
    assert "cited slug 'missing-fact' has no record." in out
    assert "cited slug 'real'" not in out


def test_record_id_that_is_no_string_is_a_finding(tmp_path: Path) -> None:
    scope = tmp_path / "scope"
    scope.mkdir()
    (scope / "evidence.yaml").write_text(
        "schema_version: 1\n"
        "records:\n"
        "  - id: [a, b]\n"
        "    source_url: https://example.com\n"
        "    fetched_at: 2026-01-01\n"
        "    excerpt: grounding text\n",
        encoding="utf-8",
    )
    result = _run(scope)
    out = _output(result)
    assert result.returncode == 1, out
    assert "Traceback" not in out
    assert "evidence.yaml#records[1] — record id ['a', 'b'] is not kebab-case" in out


# --- the slug's form (DEC-001) ----------------------------------------------


def test_record_id_may_start_with_a_digit(tmp_path: Path) -> None:
    scope = _scope(tmp_path, records=["2fa-window"], files={"doc.md": "A [ev:2fa-window].\n"})
    result = _run(scope)
    assert result.returncode == 0, _output(result)


def test_record_id_with_a_capital_is_a_finding(tmp_path: Path) -> None:
    scope = _scope(tmp_path, records=["Api-limit"], files={})
    result = _run(scope)
    assert result.returncode == 1, _output(result)
    assert "record id 'Api-limit' is not kebab-case" in _output(result)


# --- a missing top-level `records` is a fault (DEC-002, DEC-003) ------------


def test_missing_records_key_fails_the_check(tmp_path: Path) -> None:
    scope = tmp_path / "scope"
    scope.mkdir()
    (scope / "evidence.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    result = _run(scope)
    assert result.returncode == 1, _output(result)
    assert "no top-level 'records' list." in _output(result)


def test_records_with_no_value_fails_the_check(tmp_path: Path) -> None:
    scope = tmp_path / "scope"
    scope.mkdir()
    (scope / "evidence.yaml").write_text("schema_version: 1\nrecords:\n", encoding="utf-8")
    result = _run(scope)
    assert result.returncode == 1, _output(result)
    assert "'records' must be a list." in _output(result)


# --- a directory that holds no evidence.yaml (DEC-003's failure table) ------


def test_directory_in_an_ancestor_scope_checks_that_scope(tmp_path: Path) -> None:
    """Run on a directory that holds no evidence.yaml, the check resolves its
    citations against the scope it lies in."""
    scope = _scope(tmp_path, records=["fact"], files={})
    sub = scope / "sub"
    sub.mkdir()
    (sub / "doc.md").write_text("A [ev:fact].\n", encoding="utf-8")
    result = _run(sub)
    out = _output(result)
    assert result.returncode == 0, out
    assert "checking the scope it lies in" in out
    assert "1 citation(s) validated against scope/evidence.yaml" in out


def test_directory_in_an_ancestor_scope_reports_its_unresolved_citation(
    tmp_path: Path,
) -> None:
    scope = _scope(tmp_path, records=["fact"], files={})
    sub = scope / "sub"
    sub.mkdir()
    (sub / "doc.md").write_text("A [ev:fact] and [ev:missing-fact].\n", encoding="utf-8")
    result = _run(sub)
    assert result.returncode == 1, _output(result)
    assert "sub/doc.md:1 — cited slug 'missing-fact' has no record." in _output(result)


def test_no_evidence_yaml_in_any_ancestor_is_an_error(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "doc.md").write_text("A [ev:fact].\n", encoding="utf-8")
    result = _run(bare)
    assert result.returncode == 1, _output(result)
    assert "nowhere to resolve" in _output(result)


def test_no_evidence_yaml_and_no_citation_passes(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "doc.md").write_text("No outside fact here.\n", encoding="utf-8")
    result = _run(bare)
    assert result.returncode == 0, _output(result)
    assert "nothing to validate" in _output(result)
