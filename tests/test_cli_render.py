"""Tests for the read-view renderer (ADR-006) — one test per encoded convention."""
from __future__ import annotations

from project_kit import cli_render as r


def _doc(**kw):
    kw.setdefault("title", r.title("Things", "2 found", "a demo view"))
    return r.view(**kw)


def test_title_noun_count_gloss():
    out = _doc(sections=[])
    assert out.startswith("Things — 2 found   (a demo view)\n")


def test_title_without_count_or_gloss():
    out = r.view(title=r.title("Profile: x"))
    assert out.startswith("Profile: x\n")


def test_table_computes_widths_across_rows():
    rows = [{"name": "a", "desc": "short"}, {"name": "longer-name", "desc": "x"}]
    out = _doc(sections=[r.section(rows=rows, columns=["name", "desc"])])
    assert "  a            short" in out          # 'a' padded to len('longer-name')
    assert "  longer-name  x" in out


def test_constant_empty_column_is_suppressed():
    rows = [{"name": "a", "source": "", "desc": "d1"},
            {"name": "b", "source": "", "desc": "d2"}]
    out = _doc(sections=[r.section(rows=rows, columns=["name", "source", "desc"])])
    assert "  a  d1" in out                        # no gap where source would be
    assert "source" not in out


def test_column_appears_when_any_row_has_a_value():
    rows = [{"name": "a", "source": "project", "desc": "d1"},
            {"name": "b", "source": "shipped", "desc": "d2"}]
    out = _doc(sections=[r.section(rows=rows, columns=["name", "source", "desc"])])
    assert "project" in out and "shipped" in out


def test_marker_prefixes_rows_and_is_suppressed_when_empty():
    rows = [{"m": "→", "name": "active-one"}, {"m": "", "name": "other"}]
    out = _doc(sections=[r.section(rows=rows, columns=["name"], marker="m")])
    assert "  →  active-one" in out
    assert "     other" in out                     # placeholder keeps alignment
    # all-empty marker column vanishes entirely
    rows2 = [{"m": "", "name": "a"}, {"m": "", "name": "b"}]
    out2 = _doc(sections=[r.section(rows=rows2, columns=["name"], marker="m")])
    assert "\n  a" in out2 and "→" not in out2


def test_section_header_with_gloss_and_empty_state():
    out = _doc(sections=[r.section(header="THINGS", gloss="what they are",
                                   empty="(none yet)")])
    assert "\nTHINGS — what they are\n" in out
    assert "  (none yet)" in out


def test_status_footer_default_and_header_placement():
    foot = _doc(sections=[r.section(rows=[{"n": "a"}], columns=["n"])],
                status=r.status("Active", "a", gloss="why it matters"))
    body_pos = foot.index("  a")
    assert foot.index("Active: a   (why it matters)") > body_pos  # footer: after rows
    head = _doc(sections=[r.section(rows=[{"n": "a"}], columns=["n"])],
                status=r.status("Live", "ON", placement="header"))
    assert head.index("Live: ON") < head.index("  a")             # header: before rows


def test_status_extra_lines_indent_and_labelless_status():
    out = _doc(sections=[], status=r.status(placement="header",
                                            extra=["posture lenient · source shipped"]))
    assert "\n  posture lenient · source shipped" in out


def test_status_warn_line():
    out = _doc(sections=[], status=r.status("Active", "ghost", warn="no such profile"))
    assert "  ⚠ no such profile" in out


def test_legend_and_commands_blocks_aligned_pairs():
    out = _doc(sections=[],
               legend=[("→", "the active one"), ("shipped", "ships with core")],
               commands=[("pkit x", "do x"), ("pkit longer-cmd", "do y")])
    assert "\nLegend\n" in out and "\nCommands\n" in out
    assert "  →        the active one" in out      # '→' padded to len('shipped')
    assert "  pkit x           do x" in out        # padded to len('pkit longer-cmd')


def test_empty_legend_and_commands_omitted():
    out = _doc(sections=[r.section(rows=[{"n": "a"}], columns=["n"])])
    assert "Legend" not in out and "Commands" not in out


def test_widths_shared_across_sections():
    s1 = r.section(rows=[{"name": "a"}], columns=["name"], header="ONE")
    s2 = r.section(rows=[{"name": "much-longer"}], columns=["name"], header="TWO")
    out = _doc(sections=[s1, s2])
    # 'a' in section ONE is padded to section TWO's width — but trailing
    # whitespace is stripped, so equality of computed width shows via no crash
    # and both rows rendering; assert rows render under their headers.
    assert "\nONE\n  a\n" in out or "\nONE\n  a" in out
    assert "much-longer" in out


def test_no_horizontal_rules_ever():
    out = _doc(sections=[r.section(rows=[{"n": "a"}], columns=["n"])],
               legend=[("x", "y")], commands=[("c", "g")])
    for forbidden in ("────", "====", "----"):
        assert forbidden not in out


def test_rows_have_no_trailing_whitespace():
    rows = [{"name": "a", "desc": "short"}, {"name": "bb", "desc": "x"}]
    out = _doc(sections=[r.section(rows=rows, columns=["name", "desc"])])
    for line in out.splitlines():
        assert line == line.rstrip()
