"""software-analysis: a project adds to or tightens a kind's structure in a file of its own (#1367).

A project changes each analysis kind's shipped structure in
`project/structures.yaml`, keyed by kind, its shape bound by its path
(software-analysis DEC-001 point 1; COR-023):

- **a relabel** replaces a shipped part's label, hint and example, and **a
  field's hint** a front-matter field's, with no rule, and the part keeps its
  id, its place and its form;
- **a tightening** names a project rule and adds parts `after` an element,
  requires a shipped optional part, or closes the kind's list of labels. It
  binds once that rule and the format rule are accepted, on the artefacts the
  rule binds on, as `pkit rule-sets reach` reads them (#1408);
- **refused**: a shape no key says (relaxing, reordering, an invented form), a
  kind the capability does not ship, a cycle, a retired anchor;
- **reported**: a group whose rule is superseded or withdrawn, and a rule that
  binds on no artefact of the kind;
- the check and the stamp both read the file.

The reading and placement are tested on their own first, then the check's gate
with a reach given to it, then end to end in an adopter.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    NEW,
    RECORDS,
    STRUCTURES,
    VALIDATE,
    accepting_san,
    actor_at,
    front,
    installed,
    load_lib,
    run_script,
    stamped,
)
from tests.test_rule_sets import rule_set_text, rules

_STRUCTURE, _OWN, _CHECK, _MODEL = load_lib("structure", "project_structure", "check", "model")
S: Any = _STRUCTURE
P: Any = _OWN
C: Any = _CHECK
M: Any = _MODEL

KINDS: dict[str, Any] = S.read_kinds()
FILE = STRUCTURES


def _write(root: Path, text: str) -> None:
    path = root / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read(root: Path, text: str, kinds: dict[str, Any] | None = None) -> Any:
    _write(root, text)
    return P.read(root, kinds or KINDS)


def _problems(own: Any) -> list[tuple[str, str]]:
    return [(f.location.removeprefix(FILE), f.message) for f in own.problems]


SETUP = """\
schema_version: 1
kinds:
  actor:
    relabel:
      occasions: {label: Comes, hint: When the role comes to the system., example: Weekly.}
    front-matter:
      needs: {hint: "What the role needs, in one sentence.", example: Export the report.}
    tighten:
      - rule: RS-LOC-001
        closed: true
        add:
          - {id: setup, label: The setup, after: opening, hint: Where it works., example: A lab.}
          - {id: notes, label: Notes, after: context, hint: Anything else., example: None yet.,
             required: true}
          - {id: always, label: Always a person, after: setup, hint: Whether a person.,
             example: Yes.}
"""


# --- reading the file -------------------------------------------------------------------------


def test_no_file_changes_nothing(tmp_path: Path) -> None:
    own = P.read(tmp_path, KINDS)
    assert (own.present, own.problems, own.groups) == (False, (), ())
    assert P.relabelled(KINDS["actor"], own) is KINDS["actor"]


def test_a_relabel_and_a_field_s_hint_replace_text_and_keep_id_place_and_form(
    tmp_path: Path,
) -> None:
    own = _read(tmp_path, SETUP)
    assert own.problems == ()
    shipped, actor = KINDS["actor"], P.relabelled(KINDS["actor"], own)
    assert [e.id for e in actor.sections] == [e.id for e in shipped.sections]
    occasions = next(e for e in actor.sections if e.id == "occasions")
    before = next(e for e in shipped.sections if e.id == "occasions")
    assert (occasions.text, occasions.hint, occasions.example) == (
        "Comes",
        "When the role comes to the system.",
        "Weekly.",
    )
    assert (occasions.type, occasions.form, occasions.required, occasions.allows_none) == (
        before.type,
        before.form,
        before.required,
        before.allows_none,
    )
    (needs,) = actor.fields
    assert (needs.hint, needs.example, needs.form) == (
        "What the role needs, in one sentence.",
        "Export the report.",
        "sentence",
    )


def test_an_addition_sits_right_after_the_element_it_names(tmp_path: Path) -> None:
    """Pre-order: `setup` names the opening, so it comes before the shipped `occasions`,
    which follows the opening too, and `always`, which names `setup`, right after it."""
    own = _read(tmp_path, SETUP)
    actor = P.relabelled(KINDS["actor"], own)
    groups = own.of("actor")
    tightened = P.tightened(actor, groups, groups)
    assert [e.id for e in tightened.sections] == [
        "heading",
        "opening",
        "setup",
        "always",
        "occasions",
        "context",
        "notes",
    ]
    added = {e.id: e for e in tightened.sections if e.rule is not None}
    assert {i: (e.rule, e.required) for i, e in added.items()} == {
        "setup": ("RS-LOC-001", False),
        "always": ("RS-LOC-001", False),
        "notes": ("RS-LOC-001", True),
    }
    assert tightened.closed == ("RS-LOC-001",)
    assert P.tightened(actor, groups, []) is actor


def test_additions_naming_one_element_keep_the_file_s_order_across_groups(tmp_path: Path) -> None:
    """A group that does not apply is left out, and an addition naming one of its parts
    keeps the place it would have had."""
    own = _read(
        tmp_path,
        """\
schema_version: 1
kinds:
  actor:
    tighten:
      - rule: RS-LOC-001
        add:
          - {id: first, label: First, after: opening, hint: One., example: One.}
      - rule: RS-LOC-002
        add:
          - {id: second, label: Second, after: opening, hint: Two., example: Two.}
          - {id: under, label: Under first, after: first, hint: Three., example: Three.}
        require: [context]
""",
    )
    assert own.problems == ()
    actor = KINDS["actor"]
    first, second = own.of("actor")
    both = P.tightened(actor, own.of("actor"), [first, second])
    assert [e.id for e in both.sections][1:5] == ["opening", "first", "under", "second"]
    alone = P.tightened(actor, own.of("actor"), [second])
    assert [e.id for e in alone.sections][1:4] == ["opening", "under", "second"]
    assert alone.closed == ()


def test_require_makes_a_shipped_optional_part_required() -> None:
    import dataclasses

    actor = KINDS["actor"]
    optional = dataclasses.replace(
        actor,
        sections=tuple(
            dataclasses.replace(e, required=False) if e.id == "context" else e
            for e in actor.sections
        ),
    )
    group = P.Group("actor", 0, "RS-LOC-003", require=("context", "occasions"))
    tightened = P.tightened(optional, (group,), (group,))
    context = next(e for e in tightened.sections if e.id == "context")
    occasions = next(e for e in tightened.sections if e.id == "occasions")
    assert (context.required, context.rule) == (True, "RS-LOC-003")
    assert (occasions.required, occasions.rule) == (True, None)  # shipped required already


@pytest.mark.parametrize(
    ("entry", "pointer", "said"),
    [
        (
            "  persona:\n    relabel: {goal: {label: Aim}}\n",
            "/kinds/persona",
            "`persona` is no kind the capability ships",
        ),
        (
            "  actor:\n    relabel: {comes: {label: Arrives}}\n",
            "/kinds/actor/relabel/comes",
            "`comes` is no element of the actor kind",
        ),
        (
            "  actor:\n    relabel: {opening: {label: Who}}\n",
            "/kinds/actor/relabel/opening/label",
            "`opening` has no text to relabel",
        ),
        (
            "  actor:\n    relabel: {heading: {hint: The name.}}\n",
            "/kinds/actor/relabel/heading",
            "`heading` is a heading the stamp writes",
        ),
        (
            "  actor:\n    relabel: {context: {label: Occasions}}\n",
            "/kinds/actor/relabel/context/label",
            "`Occasions` is the text of `occasions` already",
        ),
        (
            "  actor:\n    front-matter: {status: {hint: Active or not.}}\n",
            "/kinds/actor/front-matter/status",
            "`status` is no front-matter field the actor kind gives a hint",
        ),
        (
            "  actor:\n    relabel: {context: {hint: Ends --> early.}}\n",
            "/kinds/actor/relabel/context",
            "would not stay one comment on one line",
        ),
    ],
)
def test_a_relabel_or_a_field_naming_what_the_kind_does_not_hold_is_refused(
    tmp_path: Path, entry: str, pointer: str, said: str
) -> None:
    own = _read(tmp_path, f"schema_version: 1\nkinds:\n{entry}")
    [(where, message)] = _problems(own)
    assert where == f":{pointer}"
    assert said in message
    assert (own.groups, own.relabels) == ((), {})  # read whole or not at all


def _tighten(*additions: str, require: str = "") -> str:
    lines = "\n".join(f"          - {a}" for a in additions)
    add = f"        add:\n{lines}\n" if additions else ""
    return (
        "schema_version: 1\nkinds:\n  actor:\n    tighten:\n      - rule: RS-LOC-001\n"
        f"{add}{require}"
    )


@pytest.mark.parametrize(
    ("text", "pointer", "said"),
    [
        (
            _tighten("{id: context, label: More, after: opening, hint: H., example: E.}"),
            "/kinds/actor/tighten/0/add/0/id",
            "`context` is an id the actor kind has taken",
        ),
        (
            _tighten("{id: more, label: Context, after: opening, hint: H., example: E.}"),
            "/kinds/actor/tighten/0/add/0/label",
            "`Context` is the text of `context` already",
        ),
        (
            _tighten("{id: more, label: More, after: nowhere, hint: H., example: E.}"),
            "/kinds/actor/tighten/0/add/0/after",
            "`nowhere` is no element of the actor kind",
        ),
        (
            _tighten(
                "{id: a, label: A, after: b, hint: H., example: E.}",
                "{id: b, label: B, after: a, hint: H., example: E.}",
            ),
            "/kinds/actor/tighten/0/add/0/after",
            "a cycle of additions has no place",
        ),
        (
            _tighten(require="        require: [nowhere]\n"),
            "/kinds/actor/tighten/0/require/0",
            "`nowhere` is no element of the actor kind",
        ),
        (
            # A part between the title and the opening would take the opening's lines.
            _tighten("{id: more, label: More, after: heading, hint: H., example: E.}"),
            "/kinds/actor/tighten/0/add/0/after",
            "the actor's opening text follows `heading`",
        ),
        (
            # A heading of the title's level would end the actor's own section.
            _tighten(
                "{id: more, type: heading, level: 1, label: More, after: context, hint: H.,"
                " example: E.}"
            ),
            "/kinds/actor/tighten/0/add/0/level",
            "a heading of level 1 would end the actor's own section",
        ),
        (
            # A heading deeper than where the part before it ends would be its content.
            _tighten(
                "{id: more, type: heading, level: 3, label: More, after: context, hint: H.,"
                " example: E.}"
            ),
            "/kinds/actor/tighten/0/add/0/level",
            "a heading of level 3 would read as the content of the part before it",
        ),
        (
            # A relabel that takes another part's text is reported where the relabel is.
            "schema_version: 1\nkinds:\n  actor:\n    relabel: {occasions: {label: Context}}\n",
            "/kinds/actor/relabel/occasions/label",
            "`Context` is the text of `context` already",
        ),
    ],
)
def test_a_tightening_that_has_no_place_or_clashes_is_refused(
    tmp_path: Path, text: str, pointer: str, said: str
) -> None:
    own = _read(tmp_path, text)
    found = _problems(own)
    assert any(where == f":{pointer}" and said in message for where, message in found), found
    assert own.groups == ()


def test_requiring_a_part_the_kind_requires_already_is_reported(tmp_path: Path) -> None:
    """Every part a kind ships is required, so `require` changes nothing today, and the
    reading says so without refusing the file."""
    own = _read(tmp_path, _tighten(require="        require: [context]\n"))
    assert own.problems == ()
    [note] = own.notes
    assert (note.severity, note.location) == ("report", f"{FILE}:/kinds/actor/tighten/0/require/0")
    assert note.message.startswith("`context` is required already")


def test_an_addition_naming_a_retired_element_is_an_error(tmp_path: Path) -> None:
    import dataclasses

    kinds = dict(KINDS)
    kinds["actor"] = dataclasses.replace(KINDS["actor"], retired=frozenset({"comes"}))
    own = _read(
        tmp_path,
        _tighten("{id: more, label: More, after: comes, hint: H., example: E.}"),
        kinds,
    )
    [(where, message)] = _problems(own)
    assert where == ":/kinds/actor/tighten/0/add/0/after"
    assert message.startswith("`comes` is an element the actor kind retired")


@pytest.mark.parametrize(
    ("entry", "pointer"),
    [
        # relaxing a shipped part: no key says it
        ("  actor:\n    relabel: {context: {required: false}}\n", "/kinds/actor/relabel/context"),
        (
            "  actor:\n    relabel: {context: {allows-none: false}}\n",
            "/kinds/actor/relabel/context",
        ),
        # reordering shipped parts: no key says it
        ("  actor:\n    order: [context, occasions]\n", "/kinds/actor"),
        # inventing a form
        (
            "  actor:\n    tighten:\n      - rule: RS-LOC-001\n        add:\n          - "
            "{id: more, label: More, after: opening, hint: H., example: E., form: haiku}\n",
            "/kinds/actor/tighten/0/add/0/form",
        ),
        # a label the check could never read: a label's bold marks are `*`
        (
            "  actor:\n    relabel: {context: {label: Con*text}}\n",
            "/kinds/actor/relabel/context/label",
        ),
        # a tightening that names no rule
        (
            "  actor:\n    tighten:\n      - add:\n          - "
            "{id: more, label: More, after: opening, hint: H., example: E.}\n",
            "/kinds/actor/tighten/0",
        ),
    ],
)
def test_relaxing_reordering_or_inventing_a_form_is_refused_by_the_shape(
    tmp_path: Path, entry: str, pointer: str
) -> None:
    own = _read(tmp_path, f"schema_version: 1\nkinds:\n{entry}")
    assert own.problems, "refused"
    assert any(f.location == f"{FILE}:{pointer}" for f in own.problems), _problems(own)
    assert all("schemas/structures.schema.json" in f.message for f in own.problems)


def test_the_carrier_is_its_own_schema_s_valid_instance() -> None:
    """The capability-side carrier binds the project's file by its path (COR-023)."""
    from ruamel.yaml import YAML

    schemas = load_lib("schemas")[0]
    carrier = YAML(typ="safe").load((Path(S.SCHEMAS) / "structures.yaml").read_text())
    assert carrier["binds_to"] == ["**/software-analysis/project/structures.yaml"]
    assert carrier["pkit_schema"] == "software-analysis:structures"
    assert schemas.structures_errors(carrier) == []


# --- a closed list of labels ------------------------------------------------------------------


ACTOR = """\
# ACT-tester — Tester

Whoever writes and runs the project's tests.

- **The setup:** a lab.
- **Occasions:** with every change.
- **Context:** the suite.
- **Notes:** none yet."""


def _lines(body: str) -> list[tuple[int, str]]:
    return [(i + 1, line) for i, line in enumerate(body.split("\n"))]


def test_a_closed_list_reports_each_undeclared_label_outside_a_part_with_a_form(
    tmp_path: Path,
) -> None:
    own = _read(tmp_path, SETUP)
    groups = own.of("actor")
    actor = P.tightened(P.relabelled(KINDS["actor"], own), groups, groups)
    body = (
        ACTOR.replace("**Occasions:**", "**Comes:**") + "\n- **Seen:** daily.\n\n```\n**Q:**\n```"
    )
    found = S.departures(_lines(body), actor)
    assert [(d.how, d.element.text, d.line, d.detail) for d in found] == [
        ("undeclared-label", "Seen", 9, "RS-LOC-001")
    ]
    # A part with a form is not read for it: a use case's steps hold bold runs of their own.
    use_case = P.tightened(KINDS["use-case"], (), ())
    import dataclasses

    closed = dataclasses.replace(use_case, closed=("RS-LOC-001",))
    steps = (
        "**Trigger:** The analyst asks.\n\n**Odd:** text.\n\n**Main path:**\n\n"
        "1. **Export:** the analyst exports.\n\n**Later:** still the main path's."
    )
    found = S.departures(_lines(steps), closed)
    assert [(d.how, d.element.text) for d in found if d.how == "undeclared-label"] == [
        ("undeclared-label", "Odd")
    ]
    # A record, or a withdrawn artefact, may predate the closing rule: nothing is reported.
    as_written = dataclasses.replace(closed, as_written=True)
    assert [d for d in S.departures(_lines(steps), as_written) if d.how == "undeclared-label"] == []


# --- the check's gate -------------------------------------------------------------------------


ACTOR_REL = "docs/analysis/use-case-model/actors/ACT-tester.md"
OTHER_REL = "docs/analysis/use-case-model/actors/ACT-other.md"
RECORD_REL = "docs/analysis/revalidations/2026-10-01-export.md"

SHIPPED_ACTOR = """\
# ACT-tester — Tester

Whoever writes and runs the project's tests.

- **Occasions:** with every change.
- **Context:** the suite."""


def _artefact(root: Path, rel: str, text: str, kind: str = "actor", **fields: Any) -> Any:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(f"---\nid: x\n---\n{text}\n", encoding="utf-8")
    return M.Artefact(
        kind=kind,
        id=None,
        path=rel,
        location=rel,
        entry=False,
        fields=fields,
        anchors={},
        span_read=True,
    )


def _analysis(san: str, rules_: dict[str, str], *artefacts: Any) -> Any:
    return M.Analysis(
        location="docs/analysis",
        places={},
        artefacts=tuple(artefacts),
        strays=(),
        unreadable={},
        files={a.path: a.kind for a in artefacts},
        records=(),
        method_rules={"RS-SAN-001": san},
        project_rules={
            rule: M.ProjectRule(status, None, "docs/rule-sets/loc.md")
            for rule, status in rules_.items()
        },
    )


NOTES_REQUIRED = """\
schema_version: 1
kinds:
  actor:
    tighten:
      - rule: RS-LOC-001
        add:
          - {id: notes, label: Notes, after: context, hint: Anything else., example: None yet.,
             required: true}
"""


#: The format rule as the backbone's reading of where rules bind cites it.
SAN_RULE = "software-analysis:RS-SAN-001"


def _gate(
    root: Path, analysis: Any, *, preview: bool = False, reach: Any = None
) -> tuple[str, list[tuple[str, str, str]]]:
    """The structure check's summary and findings, `reach` giving where the project's rules
    bind. The format rule binds on every artefact, as through a set of the project's own
    that selects them all and inherits `SAN`: once accepted, and under the preview while
    it is proposed. The finding that says `SAN` binds on none is left out."""
    own = P.read(root, KINDS)
    given = reach if reach is not None else (lambda _root, **_kw: {})
    san = (analysis.method_rules or {}).get("RS-SAN-001")

    def reached(at: Path, *, preview: bool) -> dict[str, dict[str, bool]]:
        answer = {location: dict(rules) for location, rules in given(at, preview=preview).items()}
        if san == "accepted" or (preview and san == "proposed"):
            for artefact in analysis.artefacts:
                answer.setdefault(artefact.location, {})[SAN_RULE] = san != "accepted"
        return answer

    summary, found = C._structure(root, analysis, preview=preview, own=own, reach=reached)
    return summary, [
        (f.severity, f.location, f.message)
        for f in found
        if not f.message.startswith("no rule of software-analysis:SAN binds")
    ]


def test_a_tightening_binds_where_its_rule_binds_once_both_rules_are_accepted(
    tmp_path: Path,
) -> None:
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    other = _artefact(tmp_path, OTHER_REL, SHIPPED_ACTOR.replace("tester", "other"))
    asked: list[tuple[Path, bool]] = []

    def reach(root: Path, *, preview: bool) -> dict[str, dict[str, bool]]:
        asked.append((root, preview))
        return {ACTOR_REL: {"RS-LOC-001": False, "RS-WRITE-001": False}}

    summary, found = _gate(
        tmp_path, _analysis("accepted", {"RS-LOC-001": "accepted"}, tester, other), reach=reach
    )
    [(severity, location, message)] = found
    assert (severity, location) == ("error", ACTOR_REL)
    assert message.startswith(
        "`**Notes:**` is missing, and it comes after `**Context:**`: the project's rule "
        "RS-LOC-001 requires it of an actor (RS-LOC-001, RS-SAN-001). What goes there: "
    )
    # Read once, for the format rule and the group alike; the normal check never reads a
    # preview.
    assert asked == [(tmp_path, False)]
    assert "tightened where 1 of the project's group(s)" in summary
    # A proposed project rule binds nothing, and asks nothing more of the reading than
    # where the format rule binds.
    asked.clear()
    _summary, found = _gate(
        tmp_path, _analysis("accepted", {"RS-LOC-001": "proposed"}, tester), reach=reach
    )
    assert (found, asked) == ([], [(tmp_path, False)])


def test_a_group_whose_rule_binds_only_where_the_format_rule_does_not_tightens_nothing(
    tmp_path: Path,
) -> None:
    """A group applies only where the format rule binds too, so where its rule binds only
    elsewhere, it holds no artefact and the summary counts no group that binds."""
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    other = _artefact(tmp_path, OTHER_REL, SHIPPED_ACTOR.replace("tester", "other"))

    def reach(_root: Path, *, preview: bool) -> dict[str, dict[str, bool]]:
        return {ACTOR_REL: {SAN_RULE: False}, OTHER_REL: {"RS-LOC-001": False}}

    analysis = _analysis("accepted", {"RS-LOC-001": "accepted"}, tester, other)
    summary, found = C._structure(
        tmp_path, analysis, preview=False, own=P.read(tmp_path, KINDS), reach=reach
    )
    assert [(f.severity, f.location) for f in found] == []
    assert "1 artefact(s) and file head(s) checked" in summary
    assert "tightened where" not in summary


class _Reach:
    """A reading of where rules bind: `plain` without the preview, `previewing` with it.
    `asked` records whether each call asked for the preview."""

    def __init__(
        self,
        plain: dict[str, dict[str, bool]],
        previewing: dict[str, dict[str, bool]] | None = None,
    ) -> None:
        self.plain = plain
        self.previewing = previewing or {}
        self.asked: list[bool] = []

    def __call__(self, _root: Path, *, preview: bool) -> dict[str, dict[str, bool]]:
        self.asked.append(preview)
        return self.previewing if preview else self.plain


_reach = _Reach


def test_a_preview_places_a_proposed_rule_where_the_backbone_s_preview_says_it_binds(
    tmp_path: Path,
) -> None:
    """The preview reads `pkit rule-sets reach --preview` (#1607): a proposed rule's group
    binds where the rule would bind if it were accepted, and what it finds there is a
    preview's report."""
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    other = _artefact(tmp_path, OTHER_REL, SHIPPED_ACTOR.replace("tester", "other"))
    accepted = _reach({ACTOR_REL: {"RS-LOC-001": False}}, {ACTOR_REL: {"RS-LOC-001": False}})
    _summary, found = _gate(
        tmp_path,
        _analysis("proposed", {"RS-LOC-001": "accepted"}, tester),
        preview=True,
        reach=accepted,
    )
    [(severity, location, message)] = found
    assert (severity, location) == ("report", ACTOR_REL)
    assert message.startswith("preview: `**Notes:**` is missing")
    proposed = _reach({}, {ACTOR_REL: {"RS-LOC-001": True}})
    for san in ("proposed", "accepted"):
        _summary, found = _gate(
            tmp_path,
            _analysis(san, {"RS-LOC-001": "proposed"}, tester, other),
            preview=True,
            reach=proposed,
        )
        # Only the actor the rule would bind on, and as a preview's report whatever the
        # format rule's status: it never fails.
        [(severity, location, message)] = found
        assert (severity, location) == ("report", ACTOR_REL)
        assert message.startswith("preview: `**Notes:**` is missing")
    # Each reading is asked once a run. A proposed format rule is placed by the preview
    # alone; an accepted one by the reading without it, which a proposed project rule
    # asks nothing more of.
    assert proposed.asked == [True, False, True]
    # Without a preview, a proposed format rule reports nothing at all.
    assert _gate(tmp_path, _analysis("proposed", {"RS-LOC-001": "accepted"}, tester))[1] == []


def test_a_preview_takes_what_binds_from_the_reading_without_it(tmp_path: Path) -> None:
    """A preview can lose a binding (ADR-057 point 2), so what binds comes from the
    reading without it, and the preview adds only what it marks. An accepted rule's
    departure stays an error where the format rule is accepted, so the exit is the
    normal check's."""
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    lost = _reach({ACTOR_REL: {"RS-LOC-001": False}}, {})
    analysis = _analysis("accepted", {"RS-LOC-001": "accepted"}, tester)
    [(severity, location, message)] = _gate(tmp_path, analysis, preview=True, reach=lost)[1]
    assert (severity, location) == ("error", ACTOR_REL)
    assert message.startswith("`**Notes:**` is missing")
    assert lost.asked == [False, True]
    assert _gate(tmp_path, analysis, reach=lost)[1] == [(severity, location, message)]


def test_an_accepted_fill_of_a_proposed_rule_binds_where_the_preview_says(
    tmp_path: Path,
) -> None:
    """A fill binds only while the rule it fills is accepted too (COR-051 point 7), and the
    backbone's reading judges that: without the preview it lists the rule nowhere, which
    is reported, naming a rule it fills as one cause. The preview places it."""
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    analysis = M.Analysis(
        **{
            **_analysis("accepted", {}, tester).__dict__,
            "project_rules": {
                "RS-LOC-001": M.ProjectRule(
                    "accepted", None, "docs/rule-sets/loc.md", ("RS-WRITE-002",)
                )
            },
        }
    )
    reach = _reach({}, {ACTOR_REL: {"RS-LOC-001": True}})
    [normal] = _gate(tmp_path, analysis, reach=reach)[1]
    severity, location, message = normal
    assert (severity, location) == ("report", f"{FILE}:/kinds/actor/tighten/0")
    assert message.startswith("RS-LOC-001 binds on no actor of the analysis")
    assert "a rule it fills does not bind there" in message
    # The preview gives the normal check's findings, and adds its own as reports.
    [(severity, location, message), kept] = _gate(tmp_path, analysis, preview=True, reach=reach)[1]
    assert kept == normal
    assert (severity, location) == ("report", ACTOR_REL)
    assert message.startswith("preview: `**Notes:**` is missing")


def test_a_rule_that_binds_on_no_artefact_of_the_kind_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    _summary, found = _gate(
        tmp_path,
        _analysis("accepted", {"RS-LOC-001": "accepted"}, tester),
        reach=_reach({"docs/guide.md": {"RS-LOC-001": False}}),
    )
    [(severity, location, message)] = found
    assert (severity, location) == ("report", f"{FILE}:/kinds/actor/tighten/0")
    assert message.startswith("RS-LOC-001 binds on no actor of the analysis")


def test_the_reading_of_where_rules_bind_asks_for_the_preview_only_when_previewing(
    tmp_path: Path,
) -> None:
    """`backbone.reach` runs `pkit rule-sets reach --json`, with `--preview` only for a
    preview, and reads each project rule with its mark. A backbone that predates the
    preview says so."""
    backbone: Any = load_lib("backbone")[0]
    argvs: list[list[str]] = []
    document = {
        "schema_version": 1,
        "commit": None,
        "preview": True,
        "artefacts": [
            {
                "location": ACTOR_REL,
                "rules": [
                    {"rule": "RS-LOC-001", "previewed": True},
                    {"rule": "RS-WRITE-001", "previewed": False},
                    {"rule": "software-analysis:RS-SAN-001", "previewed": True},
                ],
            }
        ],
    }

    def run(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        argvs.append(argv)
        answer = {**document, "preview": "--preview" in argv}
        return subprocess.CompletedProcess(argv, 0, json.dumps(answer), "")

    # A method rule comes with its component in front, as it is cited: the format rule is
    # read from the same answer (DEC-001 point 1).
    assert backbone.reach(tmp_path, run, preview=True) == {
        ACTOR_REL: {"RS-LOC-001": True, "RS-WRITE-001": False, SAN_RULE: True}
    }
    backbone.reach(tmp_path, run)
    assert argvs == [
        ["pkit", "rule-sets", "reach", "--preview", "--json"],
        ["pkit", "rule-sets", "reach", "--json"],
    ]

    def old(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2, "", "Error: No such option: --preview\n")

    with pytest.raises(backbone.Unreadable, match="predates it"):
        backbone.reach(tmp_path, old, preview=True)

    def unmarked(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        answer = {k: v for k, v in document.items() if k != "preview"}
        return subprocess.CompletedProcess(argv, 0, json.dumps(answer), "")

    with pytest.raises(backbone.Unreadable, match="predates the preview"):
        backbone.reach(tmp_path, unmarked, preview=True)


def test_a_reach_that_cannot_be_read_applies_the_group_nowhere_and_says_so(tmp_path: Path) -> None:
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)

    def unreadable(_root: Path, *, preview: bool) -> dict[str, dict[str, bool]]:
        raise M.Unreadable("`pkit rule-sets reach --json` exited 1")

    # Where no rule binds cannot be read, no artefact is checked at all: one error says so,
    # at the analysis.
    summary, found = _gate(
        tmp_path, _analysis("accepted", {"RS-LOC-001": "accepted"}, tester), reach=unreadable
    )
    [(severity, location, message)] = found
    assert (severity, location) == ("error", "docs/analysis")
    assert message.startswith("where the rules of software-analysis:SAN bind cannot be read")
    assert "not checked — where the rule binds cannot be read" in summary
    # In a preview of a proposed format rule, it is a report, and the exit stays the normal
    # check's.
    _summary, found = _gate(
        tmp_path,
        _analysis("proposed", {"RS-LOC-001": "accepted"}, tester),
        preview=True,
        reach=unreadable,
    )
    [(severity, location, message)] = found
    assert (severity, location) == ("report", "docs/analysis")
    assert message.startswith("preview: where RS-SAN-001 would bind cannot be read")


def test_a_preview_reading_that_fails_keeps_the_normal_check_s_findings(tmp_path: Path) -> None:
    """Where only the preview's reading cannot be read, the groups still bind where the
    reading without it says, and the failure is a preview's report: it never fails."""
    _write(tmp_path, NOTES_REQUIRED)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)

    def plain_only(_root: Path, *, preview: bool) -> dict[str, dict[str, bool]]:
        if preview:
            raise M.Unreadable("`pkit rule-sets reach --preview --json` exited 2")
        return {ACTOR_REL: {"RS-LOC-001": False}}

    analysis = _analysis("accepted", {"RS-LOC-001": "accepted"}, tester)
    normal = _gate(tmp_path, analysis, reach=plain_only)[1]
    assert [(f[0], f[1]) for f in normal] == [("error", ACTOR_REL)]
    found = _gate(tmp_path, analysis, preview=True, reach=plain_only)[1]
    assert found[0] == normal[0]
    [(severity, location, message)] = found[1:]
    assert (severity, location) == ("report", f"{FILE}:/kinds/actor/tighten/0")
    assert message.startswith("preview: where RS-LOC-001 would bind cannot be read")


CLOSED_TWICE = """\
schema_version: 1
kinds:
  actor:
    tighten:
      - rule: RS-NEW-001
        closed: true
      - rule: RS-OLD-001
        closed: true
"""

SETUP_FIRST = """\
schema_version: 1
kinds:
  actor:
    tighten:
      - rule: RS-NEW-001
        add:
          - {id: setup, label: The setup, after: opening, hint: Where., example: A lab.}
"""


def test_a_preview_reports_only_what_its_groups_add_whatever_part_it_is_about(
    tmp_path: Path,
) -> None:
    """What a body breaks without the preview keeps its severity in a preview, and only
    what the preview's groups add is a preview's report, though a finding may be about a
    shipped part, or credited to a rule the preview adds. So the exit is the normal
    check's."""
    _write(tmp_path, CLOSED_TWICE)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR + "\n- **Extra:** something.")
    analysis = _analysis("accepted", {"RS-NEW-001": "proposed", "RS-OLD-001": "accepted"}, tester)
    reach = _reach(
        {ACTOR_REL: {"RS-OLD-001": False}},
        {ACTOR_REL: {"RS-OLD-001": False, "RS-NEW-001": True}},
    )
    normal = _gate(tmp_path, analysis, reach=reach)[1]
    assert [f[0] for f in normal] == ["error"]
    assert _gate(tmp_path, analysis, preview=True, reach=reach)[1] == normal
    # A part a proposed group adds after the opening, carried last: the shipped parts
    # then read as out of order, which only the preview finds.
    _write(tmp_path, SETUP_FIRST)
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR + "\n- **The setup:** a lab.")
    analysis = _analysis("accepted", {"RS-NEW-001": "proposed"}, tester)
    reach = _reach({}, {ACTOR_REL: {"RS-NEW-001": True}})
    assert _gate(tmp_path, analysis, reach=reach)[1] == []
    found = _gate(tmp_path, analysis, preview=True, reach=reach)[1]
    assert found and all(f[0] == "report" and f[2].startswith("preview: ") for f in found)


def test_a_relabelled_part_is_looked_for_by_its_new_label(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "schema_version: 1\nkinds:\n  actor:\n    relabel: {occasions: {label: Comes}}\n",
    )
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    _summary, found = _gate(tmp_path, _analysis("accepted", {}, tester))
    [(_severity, _location, message)] = found
    assert message.startswith("`**Comes:**` is missing")
    relabelled = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR.replace("Occasions", "Comes"))
    assert _gate(tmp_path, _analysis("accepted", {}, relabelled))[1] == []


def test_a_part_that_binds_nothing_still_ends_the_part_before_it(tmp_path: Path) -> None:
    """A label a proposed rule adds binds nothing, yet a writer may already write it: it
    ends the part before it, so the shipped *Goal* stays one sentence."""
    _write(
        tmp_path,
        "schema_version: 1\nkinds:\n  use-case:\n    tighten:\n      - rule: RS-LOC-001\n"
        "        add:\n          - {id: why, label: Why, after: goal, hint: H., example: E.}\n",
    )
    use_case = (
        "# UC-007 — Export\n\n**Goal:** Export my report.\n\n**Why:** The board asks. It "
        "meets weekly.\n\n**Other actors:** None.\n\n**Preconditions:** None.\n\n"
        "**Assumptions:** None.\n\n**Trigger:** The analyst asks.\n\n**Main path:**\n\n"
        "1. The analyst exports.\n\n**Variants:** None.\n\n**Postconditions:** The file "
        "exists.\n\n**Minimal guarantees:** None."
    )
    rel = "docs/analysis/use-case-model/use-cases/UC-007-export.md"
    artefact = _artefact(tmp_path, rel, use_case, "use-case")
    analysis = _analysis("accepted", {"RS-LOC-001": "proposed"}, artefact)
    assert _gate(tmp_path, analysis)[1] == []


def test_a_record_or_a_withdrawn_artefact_keeps_a_part_s_earlier_label(tmp_path: Path) -> None:
    """A relabel binds every artefact in force, which is migrated to it. A record and a
    withdrawn artefact may predate it, so either label finds the part (DEC-001 point 1)."""
    _write(
        tmp_path,
        "schema_version: 1\nkinds:\n  actor:\n    relabel: {occasions: {label: Comes}}\n"
        "  revalidation-record:\n    relabel: {gaps: {label: Gaps found}}\n",
    )
    withdrawn = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR, status="withdrawn")
    record = tmp_path / RECORD_REL
    record.parent.mkdir(parents=True)
    body = "# 2026-10-01 — Export\n\n## Outcomes\n\n- **UC-001 — holds.** It holds.\n\n## Gaps"
    record.write_text(f"---\noutcomes: {{UC-001: holds}}\n---\n\n{body}\n\nNone.\n", "utf-8")
    data = {"outcomes": {"UC-001": "holds"}}
    analysis = _analysis("accepted", {}, withdrawn)
    assert _gate(tmp_path, analysis)[1] == []
    said, found = C._record_structure(tmp_path, [(RECORD_REL, data)], P.read(tmp_path, KINDS))
    assert found == []
    assert "1 revalidation record(s) checked" in said


RECORD_TIGHTENED = """\
schema_version: 1
kinds:
  revalidation-record:
    tighten:
      - rule: RS-LOC-002
        add:
          - {id: notes, type: heading, level: 2, label: Notes, after: gaps, hint: Anything else.,
             example: None., required: true}
"""


def test_a_tightening_of_the_record_s_kind_is_refused_saying_why(tmp_path: Path) -> None:
    """A record is a held document, which no rule binds on, so a tightening of its kind
    could never bind: the schema refuses one, and the check says why (DEC-001 point 1)."""
    own = _read(tmp_path, RECORD_TIGHTENED)
    [problem] = own.problems
    assert problem.location == f"{FILE}:/kinds/revalidation-record/tighten"
    assert problem.message.startswith(
        "a revalidation record's structure takes no tightening: a record is a held document, "
        "which no rule binds on"
    )
    # The schema refuses it on its own, whatever the group holds.
    from ruamel.yaml import YAML

    schemas = load_lib("schemas")[0]
    data = YAML(typ="safe").load(RECORD_TIGHTENED)
    assert [pointer for pointer, _m in schemas.structures_errors(data)] == [
        "/kinds/revalidation-record/tighten"
    ]
    # A relabel of the record's kind stays the project's to make.
    relabel = "schema_version: 1\nkinds:\n  revalidation-record:\n    relabel: {gaps: {label: G}}\n"
    assert _read(tmp_path, relabel).problems == ()


def test_a_record_is_held_to_its_structure_always_whatever_the_format_rule(
    tmp_path: Path,
) -> None:
    """No rule binds on a record, so the capability holds its body to the record's
    structure itself, always, as its schema holds its front matter: a part missing fails
    it whatever `SAN`'s status, and the finding cites the record point, not the format
    rule (DEC-001 point 1)."""
    record = tmp_path / RECORD_REL
    record.parent.mkdir(parents=True)
    data = {"outcomes": {"UC-001": "holds"}}
    body = "# 2026-10-01 — Export\n\n## Outcomes\n\n- **UC-001 — holds.** It holds.\n"
    record.write_text(f"---\noutcomes: {{UC-001: holds}}\n---\n\n{body}", encoding="utf-8")
    said, [found] = C._record_structure(tmp_path, [(RECORD_REL, data)])
    assert (found.severity, found.location) == ("error", RECORD_REL)
    assert found.message.startswith("the section `## Gaps` is missing")
    assert "(DEC-001 point 1)" in found.message and "RS-SAN-001" not in found.message
    assert said.startswith("records' structure, held always: 1 revalidation record(s) checked")
    # No record, no line.
    assert C._record_structure(tmp_path, []) == (None, [])


def test_a_group_whose_rule_is_retired_or_missing_is_reported_or_refused(tmp_path: Path) -> None:
    own = _read(tmp_path, NOTES_REQUIRED)
    analysis = _analysis("accepted", {})
    [(severity, location, message)] = [
        (f.severity, f.location, f.message) for f in C._own_findings(analysis, own)
    ]
    assert (severity, location) == ("error", f"{FILE}:/kinds/actor/tighten/0/rule")
    assert message.startswith("RS-LOC-001 is no rule of the project's own rule sets")
    superseded = M.Analysis(
        **{
            **analysis.__dict__,
            "project_rules": {
                "RS-LOC-001": M.ProjectRule("superseded", "RS-LOC-004", "docs/rule-sets/loc.md")
            },
        }
    )
    [finding] = C._own_findings(superseded, own)
    assert finding.severity == "report"
    assert "RS-LOC-001 is superseded, so the group binds nothing" in finding.message
    assert "name RS-LOC-004, which replaces it" in finding.message
    # An orphaned group binds nothing, in a preview too.
    tester = _artefact(tmp_path, ACTOR_REL, SHIPPED_ACTOR)
    orphaned = M.Analysis(**{**superseded.__dict__, "artefacts": (tester,)})
    assert _gate(tmp_path, orphaned, preview=True, reach=_reach({}, {ACTOR_REL: {}}))[1] == []


# --- end to end, in an adopter ----------------------------------------------------------------


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


LOC = "tech-docs/rule-sets/loc.md"


def _rule_set(status: str = "accepted", scope: str = "software-analysis:actor") -> str:
    entries = rules("RS-LOC-001")
    entries["RS-LOC-001"]["status"] = status
    return rule_set_text(
        {"rule-set": "LOC", "version": "1.0.0", "scope": {"types": [scope]}, "rules": entries}
    )


def test_the_stamp_writes_the_project_s_labels_hints_and_parts(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    project.write({FILE: SETUP, LOC: _rule_set("proposed")})
    stamped(project, "actor", "tester")
    text = (project.root / actor_at("ACT-tester")).read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1]
    labels = re.findall(r"^\*\*([^*]+):\*\*", body, flags=re.MULTILINE)
    assert labels == ["The setup", "Always a person", "Comes", "Context", "Notes"]
    assert "<!-- pkit:hint When the role comes to the system. Example: Weekly. -->" in body
    # A part a project's rule adds names the rule, so a writer knows why it is there.
    assert "**The setup:** <!-- pkit:hint Where it works. (RS-LOC-001) Example: A lab. -->" in body
    assert front(project, actor_at("ACT-tester"))["needs"] == [
        "<!-- pkit:hint What the role needs, in one sentence. Example: Export the report. -->"
    ]


def test_the_stamp_leaves_out_an_orphaned_group_and_writes_a_record_s_relabels_only(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    project.write(
        {
            FILE: SETUP + "  revalidation-record:\n    relabel: {gaps: {label: Gaps found}}\n",
            LOC: _rule_set("withdrawn"),
        }
    )
    stamped(project, "actor", "tester")
    body = (project.root / actor_at("ACT-tester")).read_text(encoding="utf-8")
    assert "**The setup:**" not in body and "**Comes:**" in body
    record = run_script(
        project,
        NEW,
        "revalidation",
        "planned-export",
        "--change",
        "#45",
        "--trigger",
        "planned",
        "--outcome",
        "ACT-tester=holds",
        "--because",
        "ACT-tester=The role is as described.",
        "--reviewed-against",
        "the design @ this change",
    )
    assert record.returncode == 0, record.stderr
    [written] = (project.root / RECORDS).glob("*.md")
    text = written.read_text(encoding="utf-8")
    assert "\n## Gaps found\n" in text and "## Notes" not in text


def test_the_stamp_refuses_while_the_project_s_file_does_not_read(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    project.write({FILE: "schema_version: 1\nkinds:\n  persona: {relabel: {goal: {label: A}}}\n"})
    completed = run_script(project, NEW, "actor", "tester")
    assert completed.returncode == 1
    assert "the project's own structures cannot be read" in completed.stderr
    assert "`persona` is no kind the capability ships" in completed.stderr
    assert not (project.root / actor_at("ACT-tester")).exists()


def _validate(repo: AdopterRepo, *args: str) -> tuple[int, Any]:
    completed = run_script(repo, VALIDATE, "--json", *args)
    return completed.returncode, json.loads(completed.stdout)


def test_the_check_reads_where_the_rule_binds_through_the_backbone(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """End to end: the rule's status and where it binds come from the backbone's readings
    (`pkit friction artefacts`, `pkit rule-sets reach`), the format rule flipped to
    accepted in the adopter's copy as a fixture."""
    stamped(project, "actor", "tester", "--unanchored-because", "No code embodies it.")
    path = project.root / actor_at("ACT-tester")
    text = path.read_text(encoding="utf-8")
    filled = re.sub(r"<!-- pkit:hint .*? Example: (.*?) -->", r"\1", text)
    path.write_text(filled, encoding="utf-8")
    project.write({FILE: NOTES_REQUIRED, LOC: _rule_set("accepted"), **accepting_san(project)})
    code, document = _validate(project)
    said = [(f["severity"], f["location"], f["message"][:40]) for f in document["findings"]]
    assert said == [("error", actor_at("ACT-tester"), "`**Notes:**` is missing, and it comes af")]
    assert code == 0  # --json answers; the exit is the findings document's to tell
    # The rule's scope selects no actor: the tightening applies to none, and is reported.
    project.write({LOC: _rule_set("accepted", scope="software-analysis:term")})
    _code, document = _validate(project)
    said = [(f["severity"], f["location"]) for f in document["findings"]]
    assert said == [("report", f"{FILE}:/kinds/actor/tighten/0")]
    # `pkit data validate` holds the project's file to its schema by its path.
    result = CliRunner().invoke(main, ["data", "validate", FILE])
    assert result.exit_code == 0, result.output
    # The statuses come from the backbone's reading of every rule set, cited as each is.
    backbone = load_lib("backbone")[0]
    analysis = backbone.read_analysis(project.root)
    assert analysis.project_rules["RS-LOC-001"].status == "accepted"
    assert analysis.rule_statuses["software-analysis:RS-SAN-001"] == "accepted"


def test_the_preview_reads_where_a_proposed_rule_would_bind_through_the_backbone(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """End to end (#1607): a proposed project rule binds nothing, and `--preview` reads
    `pkit rule-sets reach --preview` to place its group on the actors its scope selects,
    as reports. `pkit validate` runs the normal check, which reads no preview."""
    stamped(project, "actor", "tester", "--unanchored-because", "No code embodies it.")
    path = project.root / actor_at("ACT-tester")
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"<!-- pkit:hint .*? Example: (.*?) -->", r"\1", text), "utf-8")
    project.write({FILE: NOTES_REQUIRED, LOC: _rule_set("proposed"), **accepting_san(project)})
    _code, document = _validate(project)
    assert document["findings"] == []
    _code, document = _validate(project, "--preview")
    said = [(f["severity"], f["location"], f["message"][:37]) for f in document["findings"]]
    assert said == [("report", actor_at("ACT-tester"), "preview: `**Notes:**` is missing, and")]
    # Where the proposed rule's scope selects no actor, the preview places it on none.
    project.write({LOC: _rule_set("proposed", scope="software-analysis:term")})
    _code, document = _validate(project, "--preview")
    said = [(f["severity"], f["location"]) for f in document["findings"]]
    assert said == [("report", f"{FILE}:/kinds/actor/tighten/0")]
    assert document["findings"][0]["message"].startswith(
        "preview: RS-LOC-001 would bind on no actor of the analysis, as `pkit rule-sets "
        "reach --preview` reads it"
    )
