"""Tests for the version-provenance helper (_lib/provenance.py).

Covers the load-bearing strip-then-append-exactly-one invariant of
ADR-036 (doubling is structurally impossible under arbitrary incoming
body state), the footer shape constraints from body-format.yaml's
`provenance_marker` entry, version resolution, and a lock asserting the
module's sentinel constants match the schema (single source of truth).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
LIB_DIR = CAP_ROOT / "scripts" / "_lib"
LIB_PATH = LIB_DIR / "provenance.py"


@pytest.fixture(scope="module")
def prov():
    # _lib on sys.path so a lazy `import gh` inside post_filing_comment resolves.
    sys.path.insert(0, str(LIB_DIR))
    module_name = "pm_provenance_lib_under_test"
    spec = importlib.util.spec_from_file_location(module_name, LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def versions(prov):
    return prov.Versions(tree="1.131.0", capability="0.42.0", cli="1.128.0")


# --- footer shape ------------------------------------------------------


def test_footer_is_delimited_by_the_sentinels(prov, versions) -> None:
    footer = prov.render_footer(versions)
    assert footer.startswith(prov.MARKER_START)
    assert footer.rstrip().endswith(prov.MARKER_END)


def test_footer_carries_versions_and_no_date(prov, versions) -> None:
    footer = prov.render_footer(versions)
    assert "1.131.0" in footer and "0.42.0" in footer and "1.128.0" in footer
    # No date in the footer (DEC-041 item 2) — date lives in the comment.
    import datetime as dt

    assert dt.date.today().isoformat() not in footer


def test_footer_flags_cli_tree_drift(prov) -> None:
    drifted = prov.Versions(tree="1.131.0", capability="0.42.0", cli="1.128.0")
    aligned = prov.Versions(tree="1.131.0", capability="0.42.0", cli="1.131.0")
    assert "⚠" in prov.render_footer(drifted)
    assert "⚠" not in prov.render_footer(aligned)


def test_footer_omits_cli_axis_when_unresolved(prov) -> None:
    v = prov.Versions(tree="1.131.0", capability="0.42.0", cli=None)
    footer = prov.render_footer(v)
    assert "cli" not in footer


def test_footer_shape_obeys_marker_constraints(prov, versions) -> None:
    """An un-stripped footer must not collide with any scanned construct."""
    footer = prov.render_footer(versions)
    body_lines = [
        ln
        for ln in footer.splitlines()
        if ln.strip() and not ln.strip().startswith("<!--")
    ]
    for ln in body_lines:
        s = ln.strip()
        assert not s.startswith("- ") and not s.startswith("* ")  # no bullet
        assert not s.startswith("#")  # no ATX heading
        assert "- [ ]" not in s and "- [x]" not in s  # no checkbox
    # The `---` separator must sit under a blank line (thematic break, not
    # a setext underline) so it can never render as a heading.
    lines = footer.splitlines()
    sep_idx = lines.index("---")
    assert lines[sep_idx - 1].strip() == ""


# --- strip-then-append-exactly-one (the load-bearing invariant) --------


def test_stamp_appends_one_footer_to_clean_body(prov, versions) -> None:
    out = prov.stamp("## What\n\nDo the thing.\n", versions)
    assert out.count(prov.MARKER_START) == 1
    assert out.count(prov.MARKER_END) == 1
    assert out.startswith("## What")


def test_stamp_is_idempotent(prov, versions) -> None:
    once = prov.stamp("body text", versions)
    twice = prov.stamp(once, versions)
    assert once == twice
    assert twice.count(prov.MARKER_START) == 1


def test_stamp_replaces_a_stale_footer(prov) -> None:
    old = prov.Versions(tree="1.128.0", capability="0.40.0", cli="1.128.0")
    new = prov.Versions(tree="1.131.0", capability="0.42.0", cli="1.131.0")
    stamped_old = prov.stamp("content", old)
    restamped = prov.stamp(stamped_old, new)
    assert restamped.count(prov.MARKER_START) == 1
    assert "1.131.0" in restamped and "0.42.0" in restamped
    assert "0.40.0" not in restamped


@pytest.mark.parametrize(
    "corrupt_tail",
    [
        # doubled region
        "\n\n<!-- pkit-provenance:start -->\n\n---\n<sub>a</sub>\n<!-- pkit-provenance:end -->"
        "\n<!-- pkit-provenance:start -->\n\n---\n<sub>b</sub>\n<!-- pkit-provenance:end -->",
        # orphaned start (end dropped by an agent reflow)
        "\n\n<!-- pkit-provenance:start -->\n\n---\n<sub>a</sub>",
        # orphaned end (start dropped)
        "\n\n---\n<sub>a</sub>\n<!-- pkit-provenance:end -->",
        # start marker only, mid-mangled
        "\n\n<!-- pkit-provenance:start -->",
    ],
)
def test_stamp_collapses_any_corrupt_region_to_one(prov, versions, corrupt_tail) -> None:
    """Doubling/orphaning is impossible: strip-all then append-one."""
    body = "## What\n\nReal content the author wrote.\n" + corrupt_tail
    out = prov.stamp(body, versions)
    assert out.count(prov.MARKER_START) == 1
    assert out.count(prov.MARKER_END) == 1
    # The real content survives; the corrupt region is gone.
    assert "Real content the author wrote." in out


def test_strip_footer_returns_body_unchanged_when_absent(prov) -> None:
    body = "## What\n\nNo footer here.\n"
    assert prov.strip_footer(body) == body.rstrip()


def test_strip_footer_leaves_no_trailing_separator(prov, versions) -> None:
    stamped = prov.stamp("content", versions)
    assert prov.strip_footer(stamped) == "content"


# --- filing comment ----------------------------------------------------


def test_filing_comment_carries_marker_and_date(prov, versions) -> None:
    comment = prov.render_filing_comment(versions, today="2026-07-01")
    assert comment.startswith(prov.FILING_MARKER)
    assert "2026-07-01" in comment
    assert "Filed under" in comment


# --- version resolution ------------------------------------------------


def test_read_versions_reads_tree_and_capability(prov, tmp_path) -> None:
    cap = tmp_path / ".pkit" / "capabilities" / "demo"
    cap.mkdir(parents=True)
    (tmp_path / ".pkit" / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    (cap / "package.yaml").write_text(
        "component:\n  kind: capability\n  name: demo\n  version: 3.2.1\n",
        encoding="utf-8",
    )
    v = prov.read_versions(cap)
    assert v.tree == "9.9.9"
    assert v.capability == "3.2.1"


def test_read_versions_degrades_to_unknown_on_missing_files(prov, tmp_path) -> None:
    cap = tmp_path / ".pkit" / "capabilities" / "demo"
    cap.mkdir(parents=True)
    v = prov.read_versions(cap)
    assert v.tree == "unknown"
    assert v.capability == "unknown"


# --- single source of truth: sentinels match the schema ----------------


def test_sentinels_match_body_format_schema(prov) -> None:
    from ruamel.yaml import YAML

    schema = YAML(typ="safe").load(
        (CAP_ROOT / "schemas" / "body-format.yaml").read_text(encoding="utf-8")
    )
    marker = schema["provenance_marker"]
    assert prov.MARKER_START == marker["start_marker"]
    assert prov.MARKER_END == marker["end_marker"]
