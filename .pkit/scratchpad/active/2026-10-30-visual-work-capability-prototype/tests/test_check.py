"""`check` reports nothing for both pieces: no overflow in either language, brand or font profile,
contrast of 4.5 or more in every mode, every glyph present, every reference found, every field allowed."""

from engine.checks import contrast, run


def test_check_reports_nothing(piece):
    problems = run(piece)
    assert problems == [], "\n".join(" ".join(p) for p in problems)


def test_no_text_overflows(piece):
    assert [p for p in run(piece) if p[0] == "FIT"] == []


def test_contrast_passes_in_every_mode(piece):
    assert [p for p in run(piece) if p[0] == "CONTRAST"] == []


def test_contrast_formula():
    assert round(contrast("#000000", "#ffffff"), 2) == 21.0
    assert round(contrast("#767676", "#ffffff"), 2) == 4.54
