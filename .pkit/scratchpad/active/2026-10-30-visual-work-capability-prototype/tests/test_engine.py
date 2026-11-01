"""The engine's own rules (point 19): a loop is refused, naming it; a missing part has zero size at
its place; a formula allows only arithmetic; an id that leads nowhere is reported."""

import pytest

from engine.formula import FormulaError, evaluate, parse
from engine.layout import Instance, PageContext
from engine.model import Brand, EngineError, Spec


def context(piece, problems):
    brand = Brand(piece.library("ibm"))
    return PageContext(piece, brand, brand.tokens("standard"), "standard", "en", {}, "t", 1, 1, problems)


def instance(piece, data, fields=None, problems=None):
    spec = Spec(data, "test/component", piece.library("starter"))
    return Instance(context(piece, [] if problems is None else problems), spec, fields or {}, {}, ["t"], "t", {"width": 1000, "height": 500})


def test_a_loop_is_refused_naming_it(friday):
    inst = instance(friday, {"parts": {
        "a": {"box": {"fill": "surface"}, "width": "=b.width", "height": 10},
        "b": {"box": {"fill": "surface"}, "width": "=a.width", "height": 10}}})
    with pytest.raises(EngineError, match=r"loop .*: a\.width -> b\.width -> a\.width"):
        inst.emit()


def test_a_missing_part_has_zero_size_at_its_place(friday):
    data = {"fields": {"type": "object", "properties": {"head": {"type": "string"}}},
            "parts": {
                "head": {"when": "head", "text": "{head}", "style": "key", "y": 20, "width": "=width"},
                "body": {"box": {"fill": "surface"}, "y": "=head.bottom + min(head.height, @space.05)", "width": 100, "height": 50}}}
    without = instance(friday, data)
    assert without.get("head.height") == 0 and without.get("body.y") == 20
    with_head = instance(friday, data, {"head": "Hello"})
    assert with_head.get("body.y") == 20 + with_head.get("head.height") + 32


def test_a_formula_allows_arithmetic_only():
    assert evaluate("=max(2, 3) * (4 − 1) ÷ 3", lambda n: 0, lambda t: 0) == 3
    with pytest.raises(FormulaError):
        parse("=a > b")
    with pytest.raises(FormulaError, match="only min, max and round"):
        parse("=sqrt(4)")
    with pytest.raises(FormulaError, match="division by zero"):
        evaluate("=1 / count", lambda n: 0, lambda t: 0)


def test_a_tie_to_an_unknown_id_is_reported(friday):
    problems = []
    inst = instance(friday, {"parts": {"net": {"use": "{net}", "width": "=width"}}},
                    {"net": {"use": "starter/network", "left": [{"id": "a", "head": "A"}], "right": [{"id": "b", "head": "B"}],
                             "ties": [{"from": "a", "to": "nowhere"}]}}, problems)
    inst.emit()
    assert any(p[0] == "REF" and "nowhere" in p[2] for p in problems)


def test_a_field_a_component_does_not_take_is_reported(friday):
    problems = []
    inst = instance(friday, {"parts": {"card": {"use": "{card}", "width": "=width"}}},
                    {"card": {"use": "starter/card", "head": "A", "colour": "red"}}, problems)
    inst.emit()
    assert any(p[0] == "SCHEMA" and "colour" in p[2] for p in problems)


def test_an_option_word_not_in_its_list_is_reported(friday):
    problems = []
    inst = instance(friday, {"parts": {"card": {"use": "{card}", "width": "=width"}}},
                    {"card": {"use": "starter/card", "head": "A", "fill": "loud"}}, problems)
    inst.emit()
    assert any(p[0] == "SCHEMA" and "fill='loud'" in p[2] for p in problems)


def test_line_up_with_one_item_by_id_draws_the_arrow(friday):
    problems = []
    inst = instance(friday, {"parts": {"row": {"use": "{row}", "width": "=width"}}},
                    {"row": {"use": "starter/panels", "line-up": {"item": "c"}, "panels": [
                        {"use": "starter/groups", "groups": [{"head": "G", "items": [
                            {"id": "a", "text": "first"}, {"id": "b", "text": "second"}, {"id": "c", "text": "third"}]}]},
                        {"use": "starter/card", "head": "Beside c"}]}}, problems)
    inst.emit()
    assert problems == []
    panels = inst.child("row")
    group = panels.arrange("panels")
    c = panels.find("c")
    card = group.items[1]
    assert abs((card[2] + card[4] / 2) - (c[1] + c[3] / 2)) < 0.01  # the card's middle on c's middle
    assert len(group.extras) == 1  # the arrow from c to the card


def test_line_up_with_an_unknown_id_is_reported(friday):
    problems = []
    inst = instance(friday, {"parts": {"row": {"use": "{row}", "width": "=width"}}},
                    {"row": {"use": "starter/panels", "line-up": {"item": "nowhere"}, "panels": [
                        {"use": "starter/card", "head": "A"}, {"use": "starter/card", "head": "B"}]}}, problems)
    inst.emit()
    assert any(p[0] == "REF" and "nowhere" in p[2] for p in problems)


def test_distribute_spreads_items_over_a_length(friday):
    inst = instance(friday, {"fields": {"type": "object", "properties": {"items": {"type": "array"}}},
                             "draws": {"item": "starter/card"},
                             "parts": {"col": {"repeat": "items", "draw": "item", "width": 400,
                                               "stack": {"gap": 10, "distribute": 900}}}},
                    {"items": [{"id": "a", "head": "A"}, {"id": "b", "head": "B"}, {"id": "c", "head": "C"}]})
    group = inst.arrange("col")
    assert abs(group.height - 900) < 0.01
    tops = [it[2] for it in group.items]
    assert abs((tops[1] - tops[0]) - (tops[2] - tops[1])) < 0.01


def test_the_glossary_reports_a_never_word(friday):
    from engine.checks import glossary_problems
    found = glossary_problems(friday, "en", {"slides/x/lead": "Install the add-on first."})
    assert found and found[0][0] == "TERM" and "add-on" in found[0][2] and "capability" in found[0][2]
    assert glossary_problems(friday, "en", {"slides/x/lead": "Install the capability first."}) == []


def test_a_parent_reads_below_a_child_only_what_it_exposes(friday):
    inst = instance(friday, {"parts": {
        "card": {"use": "starter/card", "head": "A", "width": 300},
        "under": {"box": {"fill": "surface"}, "y": "=card.head.bottom", "width": 10, "height": 10}}})
    with pytest.raises(EngineError, match="does not expose 'head'"):
        inst.emit()
