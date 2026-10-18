"""Tests for the answers a change wrote, in its pull request's description
(`_lib/friction_answers.py`, project-management DEC-055).

The list is the change check's: `derive` runs the real `pkit friction check
--head` in fixture repositories — from a checkout at another commit, and, where a
registered anchor kind's resolver must run, from a temporary checkout of the head.
The rendering, the closing-reference refusal and the section's place in a body are
tested on the check's document shape.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.anchor_kind_capabilities import RESOLVING, register_kinds
from tests.friction_documents import CONFIG, SOURCE, T1, document, friction_config, guide
from tests.test_friction_revisit import (
    DECISION,
    SOURCE_DOC,
    TEST_FILE,
    declare_linker,
    requirement,
)
from tests.test_friction_revisit import entry as revisit_entry

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
LIB_DIR = CAP_ROOT / "scripts" / "_lib"

HEAD = "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d"
MERGE_BASE = "0" * 40


@pytest.fixture(scope="module")
def fa() -> Iterator[ModuleType]:
    sys.path.insert(0, str(LIB_DIR))
    spec = importlib.util.spec_from_file_location(
        "pm_friction_answers_under_test", LIB_DIR / "friction_answers.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_friction_answers_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(LIB_DIR))


def _entry(
    location: str,
    answer: str | None,
    reason: str | None = None,
    *,
    anchor: tuple[str, str] | None = None,
    asked: bool = True,
    status: str = "stands",
    new: bool = False,
    kept: list[tuple[tuple[str, str], str | None]] | None = None,
    changed: list[tuple[str, str]] | None = None,
    put_back: bool = False,
) -> dict[str, Any]:
    """One entry of the change check's `answers`, as `--json` gives it."""
    return {
        "artefact": location.split("/")[-1].removesuffix(".md"),
        "location": location,
        "answer": answer,
        "anchor": None if anchor is None else {"kind": anchor[0], "value": anchor[1]},
        "reason": reason,
        "kept": [
            {"anchor": {"kind": kind, "value": value}, "reason": words}
            for (kind, value), words in (kept or [])
        ],
        "asked": asked,
        "status": status,
        "new": new,
        "put_back": put_back,
        "changed": [{"kind": kind, "value": value} for kind, value in (changed or [])],
    }


def _document(*answers: dict[str, Any], unreadable: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "check": "change",
        "base": {"ref": "origin/main", "commit": MERGE_BASE, "tip": MERGE_BASE, "outdated": False},
        "answers": list(answers),
        "unreadable": unreadable or [],
    }


# ---- the markers -------------------------------------------------------------


def test_the_markers_are_the_schemas(fa: ModuleType) -> None:
    schema = YAML(typ="safe").load((CAP_ROOT / "schemas" / "body-format.yaml").read_text("utf-8"))
    marker = schema["friction_answers_marker"]
    assert marker["heading"] == fa.HEADING
    assert marker["start_marker"] == fa.MARKER_START
    assert marker["end_marker"] == fa.MARKER_END


# ---- the rendering -------------------------------------------------------------


def test_each_answer_is_listed_with_its_words_and_marks(fa: ModuleType) -> None:
    """The section states the question once; each line names the document, the anchors
    the change modified that it relies on, and whether it is still true, with every flag
    and the words in full (#1468)."""
    merge_settings = ("path", ".pkit/adapters/claude-code/merge-settings.sh")
    document = _document(
        _entry(
            "README.md",
            "unchanged",
            "the change makes the settings merge keep every key under permissions",
            changed=[merge_settings],
        ),
        _entry(
            "docs/cli.md",
            "deferred",
            "Rewritten with the redesign.",
            anchor=("path", "src/cli/**"),
            asked=False,
        ),
        _entry("docs/api.md", "updated", None, status="bump", changed=[("path", "src/api/**")]),
        _entry("docs/faq.md", None, "Reworded.", status="edited", asked=False),
        _entry("docs/new.md", "unanchored", "A rule of the method.", asked=False, new=True),
        _entry(
            "docs/guide.md",
            "unchanged",
            "The guide holds.",
            changed=[("artefact", "ACT-clone"), ("record", "COR-050")],
            kept=[(("record", "DEC-1"), "Waiting on the record."), (("path", "x/**"), None)],
        ),
        _entry("docs/old.md", "unchanged", "Reverted.", status="written-back", asked=False),
        _entry(
            "docs/back.md",
            "deferred",
            "Later.",
            anchor=("path", "y/**"),
            changed=[("path", "y/**")],
            put_back=True,
        ),
        _entry(
            "docs/gone.md",
            "deferred",
            "Later.",
            anchor=("path", "z/**"),
            status="written-back",
            asked=False,
            put_back=True,
        ),
    )
    assert fa.render(document, HEAD) == "\n".join(
        [
            "## Documentation this change affects",
            "",
            f"<!-- pkit-friction-answers:start head={HEAD} base={MERGE_BASE} -->",
            "These documents rely on something this change modifies, and each answer says "
            "whether the document is still true.",
            "",
            "As of commit `1a2b3c4`.",
            "",
            "1. `README.md` relies on `.pkit/adapters/claude-code/merge-settings.sh`, which this "
            'change modifies. **Still accurate**: "``the change makes the settings merge keep '
            'every key under permissions``"',
            "2. `docs/cli.md` relies on `src/cli/**`. **Out of date, fixed later** (not asked for "
            'by this change): "``Rewritten with the redesign.``"',
            "3. `docs/api.md` relies on `src/api/**`, which this change modifies. **Updated in "
            "this change** (re-check date changed with nothing behind it)",
            "   - (what changed: the pull request's author has not said)",
            "4. `docs/faq.md` — **no decision recorded** (not asked for by this change) (edited "
            'without a new re-check): "``Reworded.``"',
            "5. `docs/new.md` — **not tied to anything** (new document) (not asked for by this "
            'change): "``A rule of the method.``"',
            "6. `docs/guide.md` relies on document `ACT-clone` and decision record `COR-050`, "
            'which this change modifies. **Still accurate**: "``The guide holds.``"',
            "   - (still out of date for changes to decision record `DEC-1`, fixed later: "
            '"``Waiting on the record.``")',
            "   - (still out of date for changes to `x/**`, fixed later)",
            "7. `docs/old.md` — **still accurate** (not asked for by this change) (re-check date "
            'set back to one it had before, which answers nothing): "``Reverted.``"',
            "8. `docs/back.md` relies on `y/**`, which this change modifies. **Out of date, fixed "
            'later** (an entry it had before, covering the anchor as it stood then): "``Later.``"',
            "9. `docs/gone.md` relies on `z/**`. **Out of date, fixed later** (not asked for by "
            "this change) (an entry it had before, which covers only what that one did): "
            '"``Later.``"',
            "<!-- pkit-friction-answers:end -->",
        ]
    )


@pytest.mark.parametrize(
    ("anchor", "said"),
    [
        (("path", "src/cli/**"), "`src/cli/**`"),
        (("record", "COR-050"), "decision record `COR-050`"),
        (("artefact", "ACT-clone"), "document `ACT-clone`"),
        (("symbol", "pkg.run"), "`symbol:pkg.run`"),
    ],
)
def test_an_anchor_is_named_in_plain_words(
    fa: ModuleType, anchor: tuple[str, str], said: str
) -> None:
    """An anchor of a core kind in plain words; one of a kind a capability
    registers as the change check names it, its kind in the code span too."""
    document = _document(_entry("docs/a.md", "deferred", "Later.", anchor=anchor, changed=[anchor]))
    section = fa.render(document, HEAD)
    modifies = f"relies on {said}, which this change modifies. **Out of date, fixed later**: "
    assert section is not None and modifies in section
    plain = said.replace("`", "")
    assert fa.lines(document) == [
        fa.QUESTION,
        f"1. docs/a.md relies on {plain}, which this change modifies. Out of date, fixed later: "
        '"Later."',
    ]


def test_an_answer_from_a_backbone_without_changed_anchors_still_reads(fa: ModuleType) -> None:
    """A document of a backbone that predates `changed` names no anchor it relies on, and
    still reads: the document, then the outcome."""
    entry = _entry("docs/a.md", "unchanged", "Holds.")
    del entry["changed"]
    assert fa.lines(_document(entry)) == [fa.QUESTION, '1. docs/a.md — still accurate: "Holds."']


def test_the_list_reads_as_the_change_check_s_own(fa: ModuleType) -> None:
    """All three places read the same way (#1468): the question is the change check's,
    and each answer's line, flags and kept deferrals are, word for word, the line the
    change check's closing list gives it."""
    from project_kit import friction_check as fc
    from project_kit.friction_discovery import Anchor

    status = fc.AnswerStatus

    def written(answer: str | None, reason: str | None, **fields: Any) -> Any:
        values: dict[str, Any] = {
            "anchor": None,
            "kept": (),
            "asked": True,
            "status": status.STANDS,
            "new": False,
        }
        values.update(fields)
        return fc.WrittenAnswer("doc", "docs/doc.md", answer, reason=reason, **values)

    cli, core = Anchor("path", "src/cli/**"), Anchor("path", "src/core/**")
    answers = [
        written("unchanged", "Holds.", changed=(cli,)),
        written("updated", None, changed=(cli, Anchor("artefact", "guide"), core)),
        written("deferred", "Later.", anchor=cli, changed=(cli,)),
        written("deferred", "Later.", anchor=core, asked=False),
        written(None, "Reworded.", asked=False, status=status.EDITED),
        written("unanchored", "A rule.", asked=False, new=True),
        written("unchanged", "Holds.", asked=False, status=status.BUMP),
        written("unchanged", "Back.", asked=False, status=status.WRITTEN_BACK),
        written("deferred", "Again.", anchor=cli, changed=(cli,), put_back=True),
        written(
            "deferred",
            "Again.",
            anchor=core,
            asked=False,
            status=status.WRITTEN_BACK,
            put_back=True,
        ),
        written(
            "unchanged",
            "Holds.",
            changed=(Anchor("record", "COR-050"), Anchor("symbol", "pkg.run")),
            kept=(fc.KeptDeferral(core, "Kept."), fc.KeptDeferral(cli, None)),
        ),
        written(None, "Edited.", changed=(cli,), asked=False, status=status.EDITED),
        written(
            "unchanged",
            "fine\x1b[2Kgone \u202eesrever",
            changed=(Anchor("path", "src/\u200bx/**"),),
            kept=(fc.KeptDeferral(core, "kept\nnext"),),
        ),
        # Revisit entries (COR-050 point 16): one for each outcome, then one with no
        # links or fields, one whose outcome alone changed, and one naming no target.
        *(
            written(
                fc.REVISITED,
                None if outcome == "updated" else "Why.",
                outcome=outcome,
                target=Anchor("path", "tests/test_x.py"),
                links=("verified-by", "traces"),
                fields=("statement", "threshold"),
            )
            for outcome in ("updated", "unchanged", "deferred")
        ),
        written(fc.REVISITED, "Later.", outcome="deferred", target=Anchor("record", "DEC-7")),
        written(
            fc.REVISITED,
            "Same.",
            outcome="deferred",
            target=Anchor("symbol", "pkg.run"),
            links=("verified-by",),
            asked=False,
            status=status.EDITED,
            new=True,
        ),
        written(fc.REVISITED, "Odd.", outcome=None, target=None),
    ]
    question = fc.ANSWERS_QUESTION
    assert f"{question[:1].upper()}{question[1:]}." == fa.QUESTION
    checks = [line.strip() for answer in answers for line in fc._answer_lines(answer)]
    listed = fa.lines(_document(*(answer.as_json() for answer in answers)))
    assert listed[0] == fa.QUESTION
    # An `updated` document's sentence is the author's, the one part of the list the
    # change check does not supply (DEC-055 point 1): every other line is the check's.
    said = f"({fa.UNSAID})"
    assert [line.strip() for line in listed].count(said) == 1
    checked = [line for line in listed[1:] if line.strip() != said]
    assert [re.sub(r"^\d+\. ", "", line.strip()) for line in checked] == checks


def test_the_check_s_terms_stay_out_of_the_section(fa: ModuleType) -> None:
    """The change check's own terms are its machine-readable list's: the section a
    reader sees names each answer and flag in plain words."""
    section = fa.render(
        _document(
            _entry("a.md", "unchanged", "Holds."),
            _entry("b.md", "deferred", "Later.", anchor=("path", "x/**"), asked=False, new=True),
            _entry("c.md", "unanchored", "A rule.", status="bump"),
            *(_revisit(f"r{n}.md", outcome, "Why.") for n, outcome in enumerate(OUTCOMES)),
        ),
        HEAD,
    )
    assert section is not None
    # The markers are HTML comments: a reader never sees them.
    shown = "\n".join(ln for ln in section.splitlines() if not ln.startswith("<!--")).lower()
    terms = ("unchanged", "deferred", "unanchored", "revisited", "friction", "artefact")
    for term in (*terms, "change check"):
        assert term not in shown, term


def test_documents_counts_each_document_once(fa: ModuleType) -> None:
    """A page that defers two anchors is one document the change affects."""
    answers = [
        _entry("docs/a.md", "deferred", "Later.", anchor=("path", "x/**")),
        _entry("docs/a.md", "deferred", "Later.", anchor=("path", "y/**")),
        _entry("docs/b.md", "updated"),
    ]
    assert fa.documents(answers) == 2
    assert fa.documents([]) == 0
    assert fa.affected(2, settings=False) == "2"
    assert fa.affected(2, settings=True) == "2, plus a change to which documents are checked"
    assert fa.affected(0, settings=True) == "none, but a change to which documents are checked"
    assert fa.affected(0, settings=False) == "none"


def test_a_change_that_wrote_no_answers_has_no_section(fa: ModuleType) -> None:
    assert fa.render(_document(), HEAD) is None
    assert fa.lines(_document()) == []


def test_files_the_check_could_not_read_are_counted_under_the_opening(fa: ModuleType) -> None:
    one = fa.render(_document(_entry("a.md", "updated"), unreadable=["b.md"]), HEAD)
    assert one is not None
    assert one.splitlines()[5] == "As of commit `1a2b3c4`. 1 document could not be read."
    two = fa.render(_document(_entry("a.md", "updated"), unreadable=["b.md", "c.md"]), HEAD)
    assert two is not None and "As of commit `1a2b3c4`. 2 documents could not be read." in two


def test_non_printable_characters_are_shown_escaped_as_the_human_view_shows_them(
    fa: ModuleType,
) -> None:
    words = "fine\x1b[1A\x1b[2Kgone ‮esrever\nnext"
    document = _document(_entry("docs/a​.md", "unchanged", words))
    section = fa.render(document, HEAD)
    assert section is not None
    assert "``fine\\x1b[1A\\x1b[2Kgone \\u202eesrever\\nnext``" in section
    assert "`docs/a\\u200b.md`" in section
    assert all(ch.isprintable() for line in section.splitlines() for ch in line)
    assert fa.lines(document) == [
        fa.QUESTION,
        '1. docs/a\\u200b.md — still accurate: "fine\\x1b[1A\\x1b[2Kgone \\u202eesrever\\nnext"',
    ]


def test_a_reason_with_backticks_sits_in_a_longer_code_span(fa: ModuleType) -> None:
    section = fa.render(_document(_entry("a.md", "unchanged", "the ``flag`` is `x`")), HEAD)
    # Ending on a backtick, the words are padded on both sides; CommonMark drops the pads.
    assert section is not None and ': "``` the ``flag`` is `x` ```"' in section
    section = fa.render(_document(_entry("a.md", "unchanged", "plain")), HEAD)
    assert section is not None and ': "``plain``"' in section


def test_the_terminal_list_carries_every_word_and_mark(fa: ModuleType) -> None:
    document = _document(
        _entry("docs/install.md", "unchanged", "Holds."),
        _entry("docs/cli.md", "deferred", "Later.", anchor=("path", "src/**"), asked=False),
        _entry("docs/g.md", "unchanged", "Holds.", kept=[(("path", "x/**"), "Kept.")]),
    )
    assert fa.lines(document) == [
        fa.QUESTION,
        '1. docs/install.md — still accurate: "Holds."',
        "2. docs/cli.md relies on src/**. Out of date, fixed later (not asked for by this "
        'change): "Later."',
        '3. docs/g.md — still accurate: "Holds."',
        '   (still out of date for changes to x/**, fixed later: "Kept.")',
    ]


# ---- revisit entries (COR-050 point 16) ------------------------------------------

SOURCE_REQ = "reqs/latency.md"
TEST_TARGET = ("path", "tests/test_latency.py")
#: The outcomes a revisit entry gives.
OUTCOMES = ("updated", "unchanged", "deferred")


def _revisit(
    location: str,
    outcome: str | None,
    reason: str | None = None,
    *,
    target: tuple[str, str] | None = TEST_TARGET,
    links: list[str] | None = None,
    fields: list[str] | None = None,
    asked: bool = True,
    status: str = "stands",
    new: bool = False,
) -> dict[str, Any]:
    """One revisit entry of the change check's `answers`, as `--json` gives it: the
    source's answer for one target, through `verified-by` by default, the change
    having modified the source's `threshold`."""
    revisit = _entry(location, "revisited", reason, asked=asked, status=status, new=new)
    revisit["changed"] = []
    revisit.update(
        outcome=outcome,
        target=None if target is None else {"kind": target[0], "value": target[1]},
        links=["verified-by"] if links is None else links,
        fields=["threshold"] if fields is None else fields,
    )
    return revisit


#: Each kind of revisit entry: a target revisited by changing it, one that still
#: stands, one left out of date, one whose outcome alone changed, and one the check
#: names no target or outcome for.
REVISITS = (
    _revisit(SOURCE_REQ, "updated"),
    _revisit(
        SOURCE_REQ,
        "unchanged",
        "The test asserts under 2 s, which meets 10 s too.",
        target=("artefact", "UC-status"),
    ),
    _revisit(
        SOURCE_REQ,
        "deferred",
        "The cache decision is revisited in #9999.",
        target=("record", "DEC-7"),
        links=["verified-by", "traces"],
        fields=["statement", "threshold"],
    ),
    _revisit(
        "reqs/new.md",
        "deferred",
        "Same.",
        target=("path", "x/**"),
        links=[],
        fields=[],
        asked=False,
        status="edited",
        new=True,
    ),
    _revisit(SOURCE_REQ, None, "Odd.", target=None, links=[], fields=[]),
)


def test_a_revisit_entry_names_its_source_target_outcome_and_reason(fa: ModuleType) -> None:
    """Each revisit entry says, in words, the source, the target, the links that list
    it, the trigger fields the change modified, the outcome and its reason, with every
    flag (#1703): never the bare word the check's machine-readable list gives it."""
    document = _document(*REVISITS)
    section = fa.render(document, HEAD)
    assert section is not None
    assert section.splitlines()[7:-1] == [
        "1. `reqs/latency.md` names `tests/test_latency.py` through `verified-by`, and this "
        "change modifies its `threshold`. **Updated in this change**",
        "2. `reqs/latency.md` names document `UC-status` through `verified-by`, and this change "
        'modifies its `threshold`. **Still accurate**: "``The test asserts under 2 s, which '
        'meets 10 s too.``"',
        "3. `reqs/latency.md` names decision record `DEC-7` through `verified-by` and `traces`, "
        "and this change modifies its `statement` and `threshold`. **Out of date, fixed "
        'later**: "``The cache decision is revisited in #9999.``"',
        "4. `reqs/new.md` names `x/**`. **Out of date, fixed later** (new document) (not asked "
        "for by this change) (outcome changed without a new reason, which answers nothing): "
        '"``Same.``"',
        '5. `reqs/latency.md` names a target. **No decision recorded**: "``Odd.``"',
    ]
    assert fa.lines(document) == [
        fa.QUESTION,
        "1. reqs/latency.md names tests/test_latency.py through verified-by, and this change "
        "modifies its threshold. Updated in this change",
        "2. reqs/latency.md names document UC-status through verified-by, and this change "
        'modifies its threshold. Still accurate: "The test asserts under 2 s, which meets 10 s '
        'too."',
        "3. reqs/latency.md names decision record DEC-7 through verified-by and traces, and "
        'this change modifies its statement and threshold. Out of date, fixed later: "The '
        'cache decision is revisited in #9999."',
        "4. reqs/new.md names x/**. Out of date, fixed later (new document) (not asked for by "
        "this change) (outcome changed without a new reason, which answers nothing): "
        '"Same."',
        '5. reqs/latency.md names a target. No decision recorded: "Odd."',
    ]


def test_a_revisit_entry_s_texts_are_shown_escaped_in_code_spans(fa: ModuleType) -> None:
    """The target, the links and the trigger fields are the artefact's texts: each is
    shown escaped and set in a code span, so none is read as Markdown."""
    document = _document(
        _revisit(
            SOURCE_REQ,
            "unchanged",
            "Holds.",
            target=("path", "tests/*bold*\x1b.py"),
            links=["verified`by"],
            fields=["thres‮hold"],
        )
    )
    section = fa.render(document, HEAD)
    assert section is not None
    assert (
        "names `tests/*bold*\\x1b.py` through ``verified`by``, and this change modifies its "
        "`thres\\u202ehold`. **Still accurate**" in section
    )
    assert all(ch.isprintable() for line in section.splitlines() for ch in line)


def test_a_deferred_revisit_entry_is_told_and_counted_with_what_is_left_out_of_date(
    fa: ModuleType,
) -> None:
    """The person who authorises the merge is told each target a `deferred` revisit
    entry leaves out of date, with the source that names it and the words that name
    its follow-up, beside the documents left out of date (COR-050 points 3 and 16).
    A target is counted once, however many sources leave it out of date; one that
    still stands, or that the change revisited by changing it, is not told."""
    deferred = "The cache decision is revisited in #9999."
    document = _document(
        _entry("docs/d.md", "deferred", "With the redesign, #13.", anchor=("record", "COR-1")),
        _revisit(SOURCE_REQ, "updated"),
        _revisit(SOURCE_REQ, "unchanged", "Holds.", target=("artefact", "UC-status")),
        _revisit(SOURCE_REQ, "deferred", deferred, target=("record", "DEC-7")),
        _revisit("reqs/other.md", "deferred", "Also #9999.", target=("record", "DEC-7"), links=[]),
    )
    assert fa.told(document) == [
        'Left out of date: docs/d.md, for changes to decision record COR-1: "With the '
        'redesign, #13."',
        f"Left out of date: decision record DEC-7, which {SOURCE_REQ} names through "
        f'verified-by: "{deferred}"',
        'Left out of date: decision record DEC-7, which reqs/other.md names: "Also #9999."',
    ]
    assert fa.counted_told(document) == (0, 1, 1)
    counted = fa.counted_told(document)
    assert (counted.updated, counted.left, counted.targets) == (0, 1, 1)
    # A revisit entry whose words or target are not there is told all the same.
    bare = _document(_revisit(SOURCE_REQ, "deferred", None, target=None, links=[]))
    assert fa.told(bare) == [f"Left out of date: a target, which {SOURCE_REQ} names"]
    assert fa.counted_told(bare) == (0, 0, 1)


def test_a_target_revisited_by_its_own_change_is_listed_without_a_sentence(
    fa: ModuleType,
) -> None:
    """A target the change revisited by changing it is listed, for the reviewer who
    checks that its change meets the change to the source (COR-050 points 3 and 16).
    It is no revalidation, so it asks its author for no sentence, and marks its
    source updated nowhere: not in the list, not when an edit gives the sentences."""
    only = _document(_revisit(SOURCE_REQ, "updated"))
    said = {SOURCE_REQ: "The threshold is 10 s."}
    assert fa.given(only, said) == {}
    assert fa.unsaid(only, said) == []
    assert fa.told(only) == []
    assert fa.counted_told(only) == (0, 0, 0)
    section = fa.render(only, HEAD, (), said)
    assert section is not None
    assert section.splitlines()[7:-1] == [
        "1. `reqs/latency.md` names `tests/test_latency.py` through `verified-by`, and this "
        "change modifies its `threshold`. **Updated in this change**",
    ]
    block = fa.find(section)
    assert block is not None
    assert fa.given_in(block, said) == {}
    assert fa.with_sentences(block, said) == block
    # A source the change also revalidated as updated gives its sentence once, beside
    # its revalidation.
    both = _document(_entry(SOURCE_REQ, "updated"), _revisit(SOURCE_REQ, "updated"))
    assert fa.given(both, said) == said and fa.unsaid(both, said) == []
    listed = fa.render(both, HEAD, (), said)
    assert listed is not None
    assert listed.splitlines()[7:-1] == [
        "1. `reqs/latency.md` — **updated in this change**",
        "   - (what changed, in the words of the pull request's author: \"``The threshold is "
        '10 s.``")',
        "2. `reqs/latency.md` names `tests/test_latency.py` through `verified-by`, and this "
        "change modifies its `threshold`. **Updated in this change**",
    ]
    region = fa.find(listed)
    assert region is not None
    assert fa.given_in(region, said) == said
    assert fa.with_sentences(region, said) == region
    bare = "\n".join(line for line in region.splitlines() if "(what changed" not in line)
    assert fa.with_sentences(bare, said) == region
    assert fa.documents(both["answers"]) == 1


@pytest.mark.parametrize(
    "location", ["docs/x` names `y.md", "docs/a.md", "docs/`names`.md", "docs/a names b.md"]
)
def test_only_a_revisit_entry_s_line_reads_as_one(fa: ModuleType, location: str) -> None:
    """A document whose name or words quote a revisit entry's line stays an updated
    document, its sentence given: only the words after its code span tell."""
    said = {location: "Now says X."}
    document = _document(_entry(location, "updated", "the `x` names y"))
    block = fa.find(fa.render(document, HEAD, (), said) or "")
    assert block is not None
    assert fa.given_in(block, said) == said
    assert fa.with_sentences(block, said) == block


@pytest.mark.parametrize(
    ("revisit", "found"),
    [
        (
            _revisit(SOURCE_REQ, "deferred", "Later.", target=("path", "src/fixes #3/**")),
            "fixes #3",
        ),
        (_revisit(SOURCE_REQ, "deferred", "Later.", links=["closes #4"]), "closes #4"),
        (_revisit(SOURCE_REQ, "deferred", "Later.", fields=["resolves #5"]), "resolves #5"),
        (_revisit(SOURCE_REQ, "deferred", "This fixes #6."), "fixes #6"),
    ],
)
def test_a_revisit_entry_s_texts_are_read_for_closing_references(
    fa: ModuleType, revisit: dict[str, Any], found: str
) -> None:
    """Every text a revisit entry shows is read before the list is written: its
    target, its links and its trigger fields as well as its words."""
    assert fa.closing_reference(_document(revisit)) == (SOURCE_REQ, found)


@pytest.mark.parametrize(
    "revisit",
    [
        _revisit(SOURCE_REQ, "unchanged", "Holds.", target=("path", "a<!--.md")),
        _revisit(SOURCE_REQ, "unchanged", "Holds.", links=["-->"]),
        _revisit(SOURCE_REQ, "unchanged", "Holds.", fields=["<!--"]),
    ],
)
def test_a_revisit_entry_s_texts_are_read_for_comment_delimiters(
    fa: ModuleType, revisit: dict[str, Any]
) -> None:
    found = fa.comment_delimiter(_document(revisit))
    assert found is not None and found[0] == SOURCE_REQ


# ---- closing references ---------------------------------------------------------


@pytest.mark.parametrize(
    "words",
    [
        "This fixes #12 for good.",
        "Closes: owner/repo#3",
        "resolved https://github.com/o/r/issues/4",
        "FIXED #1",
        "close #9",
        "it resolves:#7",
    ],
)
def test_a_reason_that_reads_as_a_closing_reference_is_named(fa: ModuleType, words: str) -> None:
    document = _document(_entry("docs/ok.md", "updated"), _entry("docs/a.md", "unchanged", words))
    found = fa.closing_reference(document)
    assert found is not None and found[0] == "docs/a.md"


def test_a_kept_deferrals_reason_is_read_too(fa: ModuleType) -> None:
    document = _document(
        _entry("docs/a.md", "unchanged", "Holds.", kept=[(("path", "x"), "until fixes #3 lands")])
    )
    assert fa.closing_reference(document) == ("docs/a.md", "fixes #3")


def test_a_location_and_an_anchor_are_read_too(fa: ModuleType) -> None:
    document = _document(_entry("docs/fixes #3.md", "unchanged", "Holds."))
    assert fa.closing_reference(document) == ("docs/fixes #3.md", "fixes #3")
    document = _document(
        _entry("docs/a.md", "deferred", "Later.", anchor=("path", "src/closes #4/**"))
    )
    assert fa.closing_reference(document) == ("docs/a.md", "closes #4")


@pytest.mark.parametrize(
    "words",
    ["see #12", "the fix-up #12", "close to #3", "fixtures #2", "fixes the layout #2 section"],
)
def test_other_words_are_no_closing_reference(fa: ModuleType, words: str) -> None:
    assert fa.closing_reference(_document(_entry("docs/a.md", "unchanged", words))) is None


# ---- comment delimiters ----------------------------------------------------------


@pytest.mark.parametrize(
    ("entry", "found"),
    [
        (_entry("docs/a.md", "unchanged", "Quotes <!-- pkit-provenance:start -->."), "<!--"),
        (_entry("docs/a.md", "unchanged", "an arrow -->"), "-->"),
        (_entry("docs/a<!--.md", "unchanged", "Holds."), "<!--"),
        (_entry("docs/a.md", "unchanged", "Holds.", kept=[(("path", "x"), "until -->")]), "-->"),
    ],
)
def test_a_word_holding_a_comment_delimiter_is_named(
    fa: ModuleType, entry: dict[str, Any], found: str
) -> None:
    location = entry["location"]
    assert fa.comment_delimiter(_document(entry)) == (location, found)
    assert fa.comment_delimiter(_document(_entry("docs/a.md", "unchanged", "a -> b"))) is None


# ---- the section in a description ---------------------------------------------

FOOTER = (
    "<!-- pkit-provenance:start -->\n\n---\n<sub>🧰 pkit · tree `1` · pm `2`</sub>\n"
    "<!-- pkit-provenance:end -->"
)
BODY = "Closes #42\n\n## Summary\n\nDone.\n\n## Doc impact\n\nThe README.\n"


def _section(fa: ModuleType, *answers: dict[str, Any], head: str = HEAD) -> str:
    section = fa.render(_document(*answers), head)
    assert section is not None
    return section


def test_the_section_goes_last_before_the_footer_and_only_once(fa: ModuleType) -> None:
    section = _section(fa, _entry("a.md", "unchanged", "Holds."))
    stamped = fa.stamp(f"{BODY}\n{FOOTER}\n", section)
    assert stamped == f"{BODY}\n{section}\n\n{FOOTER}\n"
    again = fa.stamp(stamped, _section(fa, _entry("b.md", "updated")))
    assert again.count(fa.HEADING) == 1 and "b.md" in again and "a.md" not in again
    assert again.endswith(f"{FOOTER}\n")
    assert fa.stamp(BODY, section) == f"{BODY}\n{section}\n"


def test_stripping_leaves_the_rest_of_the_body_as_it_was(fa: ModuleType) -> None:
    section = _section(fa, _entry("a.md", "unchanged", "fixes #9"))
    assert fa.strip(fa.stamp(BODY, section)) == BODY
    assert fa.strip(fa.stamp(f"{BODY}\n{FOOTER}\n", section)) == f"{BODY}\n{FOOTER}\n"
    assert fa.strip(BODY) == BODY
    assert fa.stamp(fa.stamp(BODY, section), None) == BODY


def test_a_start_marker_with_no_end_is_stripped_through_the_footer(fa: ModuleType) -> None:
    """What follows a start marker whose end was lost is the list's words: they are
    stripped up to the provenance footer, or the end of the body, never left under
    the section above (`## Doc impact` last of all, read for the mapping's override)."""
    orphan = f"{BODY}\n{fa.HEADING}\n\n{fa.MARKER_START} head=x base=y -->\nleft\n"
    assert fa.strip(orphan) == BODY
    assert fa.strip(f"{orphan}\n{FOOTER}\n") == f"{BODY}\n{FOOTER}\n"
    assert fa.find(orphan) is None
    assert not fa.current(orphan, None) and fa.has_list(orphan)


def test_an_end_marker_with_no_start_is_stripped_alone(fa: ModuleType) -> None:
    orphan = f"{BODY}\nkept\n{fa.MARKER_END}\nafter\n"
    assert fa.strip(orphan) == f"{BODY}\nkept\n\nafter\n"


def test_markers_count_only_as_whole_lines(fa: ModuleType) -> None:
    """A sentence that mentions a marker is body text: no section, nothing stripped."""
    body = f"{BODY}\nThe list opens with `{fa.MARKER_START} head=… -->` and ends.\n"
    assert fa.current(body, None) and fa.strip(body) == body
    section = _section(fa, _entry("a.md", "unchanged", "Holds."))
    assert fa.current(fa.stamp(body, section), section)


def test_a_reason_quoting_the_provenance_marker_cuts_nothing(fa: ModuleType) -> None:
    """The footer starts only at a line that is its marker: a body quoting one, in
    a sentence, keeps every line, and the section still goes before the footer."""
    quoting = f"{BODY}\nThe footer opens with <!-- pkit-provenance:start --> as a line.\n"
    stamped = fa.stamp(f"{quoting}\n{FOOTER}\n", _section(fa, _entry("a.md", "updated")))
    assert "as a line." in stamped and stamped.endswith(f"{FOOTER}\n")
    assert stamped.index(fa.HEADING) > stamped.index("as a line.")


def _hand(heading: str) -> str:
    """A list typed by hand under `heading`, with no markers."""
    return (
        f"{heading}\n\n"
        "An agent's own list:\n\n"
        "```\n"
        "## not a heading, inside a fence\n"
        "1. docs/a.md — unchanged: fixes #9\n"
        "```\n"
    )


#: The section's heading, and the one an earlier run wrote it under.
HEADINGS = ("## Documentation this change affects", "## Friction answers")


@pytest.mark.parametrize("heading", HEADINGS, ids=["the heading", "the former heading"])
def test_a_section_no_command_wrote_is_stripped_whole(fa: ModuleType, heading: str) -> None:
    """An unmarked section under the heading — a list typed by hand — is stripped up
    to the next heading of level one or two outside a fenced block, or the footer;
    under the heading an earlier run wrote too."""
    assert heading in (fa.HEADING, fa.FORMER_HEADING)
    hand = _hand(heading)
    body = f"Closes #42\n\n## Summary\n\nDone.\n\n{hand}\n## Doc impact\n\nThe README.\n"
    assert fa.hand_written(body) and not fa.has_list(body)
    assert fa.strip(body) == BODY
    assert not fa.current(body, None)
    last = f"{BODY}\n{hand}\n{FOOTER}\n"
    assert fa.strip(last) == f"{BODY}\n{FOOTER}\n"
    section = _section(fa, _entry("a.md", "unchanged", "Holds."))
    assert fa.stamp(last, section) == f"{BODY}\n{section}\n\n{FOOTER}\n"
    assert not fa.current(f"{last}\n{section}\n", section)


def _former(fa: ModuleType, section: str) -> str:
    """`section` as an earlier run wrote it: under the former heading."""
    assert section.startswith(f"{fa.HEADING}\n")
    return fa.FORMER_HEADING + section.removeprefix(fa.HEADING)


def test_a_section_an_earlier_run_wrote_under_the_former_heading_is_replaced_whole(
    fa: ModuleType,
) -> None:
    """The markers identify the region; the former heading directly above it goes
    with it, so a new write leaves one section, under the new heading, and no
    stray heading of the old one."""
    earlier = _former(fa, _section(fa, _entry("a.md", "unchanged", "Old."), head="e" * 40))
    body = f"{BODY}\n{earlier}\n\n{FOOTER}\n"
    assert fa.has_list(body) and not fa.hand_written(body)
    assert fa.find(body) == fa.find(earlier)
    assert fa.strip(body) == f"{BODY}\n{FOOTER}\n"
    section = _section(fa, _entry("a.md", "unchanged", "New."))
    assert not fa.current(body, section) and not fa.current(body, None)
    stamped = fa.stamp(body, section)
    assert stamped == f"{BODY}\n{section}\n\n{FOOTER}\n"
    assert fa.FORMER_HEADING not in stamped and stamped.count(fa.HEADING) == 1
    assert fa.current(stamped, section)
    # A region carried as it is — edit-pr's way — is placed under the new heading.
    region = fa.find(body)
    assert region is not None
    carried = fa.stamp(BODY, region)
    assert carried == f"{BODY}\n{fa.HEADING}\n\n{region}\n" and fa.current(carried, region)


def test_the_former_heading_inside_a_region_goes_with_the_region(fa: ModuleType) -> None:
    """A region is its start marker's line through its end marker's, whatever it
    holds: the former heading inside one is the region's, never a section of its
    own typed by hand."""
    region = f"{fa.MARKER_START} head={HEAD} base={MERGE_BASE} -->\n{fa.FORMER_HEADING}\n\nold\n"
    body = f"{BODY}\n{fa.HEADING}\n\n{region}{fa.MARKER_END}\n"
    assert fa.has_list(body) and not fa.hand_written(body)
    assert fa.strip(body) == BODY
    section = _section(fa, _entry("a.md", "unchanged", "Holds."))
    assert fa.stamp(body, section) == f"{BODY}\n{section}\n"


def test_of_two_regions_the_last_is_found_and_neither_is_current(fa: ModuleType) -> None:
    old = _section(fa, _entry("a.md", "unchanged", "Old."), head="e" * 40)
    new = _section(fa, _entry("a.md", "unchanged", "New."))
    body = f"{BODY}\n{old}\n\n{new}\n"
    assert fa.find(body) == fa.find(new)
    assert not fa.current(body, new)
    assert fa.strip(body) == BODY


def test_a_region_is_found_and_restamped_whole(fa: ModuleType) -> None:
    section = _section(fa, _entry("a.md", "unchanged", "Holds."))
    region = fa.find(fa.stamp(BODY, section))
    assert region is not None and region.startswith(fa.MARKER_START)
    assert region.endswith(fa.MARKER_END)
    assert fa.stamp("New body.\n", region) == f"New body.\n\n{section}\n"


def test_a_description_whose_whitespace_the_host_changed_reads_as_current(
    fa: ModuleType,
) -> None:
    section = _section(fa, _entry("a.md", "unchanged", "Holds."))
    body = fa.stamp(BODY, section)
    hosted = "\r\n".join(line + ("  " if line else "") for line in body.split("\n")) + "\r\n\r\n"
    assert fa.current(hosted, section)
    assert not fa.current(body, _section(fa, _entry("a.md", "unchanged", "Holds!")))
    assert not fa.current(body, _section(fa, _entry("a.md", "unchanged", "Holds."), head="f" * 40))
    assert not fa.current(BODY, section)
    assert fa.current(BODY, None) and not fa.current(body, None)


def test_a_body_too_long_for_the_host_does_not_fit(fa: ModuleType) -> None:
    assert fa.fits("x" * fa.BODY_LIMIT)
    assert not fa.fits("x" * (fa.BODY_LIMIT + 1))


# ---- deriving, through the real change check --------------------------------------

BECAUSE = "the CLI change is internal: every command the guide shows is as described"


def _branch_with_an_answer(make_adopter_repo: MakeAdopterRepo) -> tuple[AdopterRepo, str]:
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    revalidated = guide(at="2026-10-03T10:00:00Z", because=BECAUSE)
    repo.commit("revalidate the guide", {"docs/guide.md": revalidated})
    return repo, repo.head()


def test_the_list_is_derived_at_the_head_from_another_checkout(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")
    repo.write({"notes.txt": "uncommitted, and not the head's\n"})
    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    assert [(a["location"], a["answer"], a["reason"], a["asked"]) for a in found.answers] == [
        ("docs/guide.md", "unchanged", BECAUSE, True)
    ]
    assert found.merge_base == repo.git("rev-parse", "main").stdout.strip()
    assert (found.outdated, found.unreadable) == (False, ())


def test_a_revisit_entry_derived_from_the_check_is_listed_in_words(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    """The real change check's revisit entries (#1703): a source whose trigger field
    changed, one target it revisits by changing it and one it leaves out of date. The
    list names both in words, and tells the person the one left out of date."""
    deferral = "the cache decision is revisited in #9999"
    repo = make_adopter_repo()
    declare_linker(repo.root)
    repo.write(
        {
            CONFIG: friction_config(places=("docs",)),
            **SOURCE,
            TEST_FILE: "def test_latency():\n    assert answer_time() < 2\n",
            DECISION: "Cache the status.\n",
            SOURCE_DOC: requirement(),
        }
    )
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    source = requirement(
        threshold="10 s", revisited=[revisit_entry("deferred", deferral, DECISION)]
    )
    test = "def test_latency():\n    assert answer_time() < 10\n"
    repo.commit("relax the threshold", {SOURCE_DOC: source, TEST_FILE: test})
    found = fa.derive(repo.head(), "main")
    assert found.problem is None, found.problem
    assert fa.lines(found.document) == [
        fa.QUESTION,
        f"1. {SOURCE_DOC} names {DECISION} through verified-by, and this change modifies its "
        f'threshold. Out of date, fixed later: "{deferral}"',
        f"2. {SOURCE_DOC} names {TEST_FILE} through verified-by, and this change modifies its "
        "threshold. Updated in this change",
    ]
    assert fa.told(found.document) == [
        f'Left out of date: {DECISION}, which {SOURCE_DOC} names through verified-by: "{deferral}"'
    ]
    assert fa.counted_told(found.document) == (0, 0, 1)


def test_a_base_that_moved_on_is_outdated(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")
    repo.commit("main moves on", {"src/core/engine.py": "ENGINE = 2\n"})
    found = fa.derive(head, "main")
    assert found.problem is None and found.outdated


def test_no_document_is_unreadable_never_a_pass(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    _repo, head = _branch_with_an_answer(make_adopter_repo)
    found = fa.derive(head, "no-such-base")
    assert found.document is None and found.answers == ()
    assert found.problem is not None and "no-such-base" in found.problem


@pytest.mark.parametrize(
    ("returncode", "stdout", "why"),
    [
        (0, '{"schema_version": 2, "answers": []}', "answered schema_version 2; this reads 1"),
        (0, '{"schema_version": 1, "findings": []}', "lists no answers"),
        (1, "", "it exited 1: Error: boom, with no JSON document"),
        (2, '{"schema_version": 1, "answers": []}', "it exited 2: Error: boom"),
    ],
)
def test_a_document_the_list_cannot_be_read_from_is_unreadable(
    fa: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    why: str,
) -> None:
    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode, stdout, "Error: boom\n")

    monkeypatch.setattr(fa.subprocess, "run", run)
    found = fa._run_check(HEAD, "main", cwd=None)
    assert isinstance(found, fa._NoDocument) and why in found.why and not found.elsewhere


def test_enforcing_modes_exit_1_still_carries_the_document(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 1, '{"schema_version": 1, "answers": []}', "")

    monkeypatch.setattr(fa.subprocess, "run", run)
    assert fa._run_check(HEAD, "integration/7-x", cwd=None) == {"schema_version": 1, "answers": []}
    assert seen == [
        ["pkit", "friction", "check", "--json", "--base", "integration/7-x", "--head", HEAD]
    ]


def test_the_check_runs_unrouted_with_the_base_named_whatever_the_environment(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Both runs — from the working directory and from a temporary checkout — run
    the same `pkit`, routing off, and the base is the one named, never the
    environment's `$PKIT_CHECK_BASE`."""
    monkeypatch.setenv("PKIT_CHECK_BASE", "elsewhere")
    seen: list[tuple[list[str], Any, str | None]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append((argv, kwargs.get("cwd"), kwargs["env"].get("PKIT_NO_ROUTE")))
        return subprocess.CompletedProcess(argv, 0, '{"schema_version": 1, "answers": []}', "")

    monkeypatch.setattr(fa.subprocess, "run", run)
    fa._run_check(HEAD, "main", cwd=None)
    fa._run_check(HEAD, "main", cwd=tmp_path)
    assert [(argv[argv.index("--base") + 1], cwd, unrouted) for argv, cwd, unrouted in seen] == [
        ("main", None, "1"),
        ("main", tmp_path, "1"),
    ]


def test_only_the_resolver_refusal_is_answered_from_a_checkout(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The backbone's refusal to run a resolver away from the head is told apart
    from every other failure, which is kept as the first run gave it."""
    refusal = (
        "Error: --head 1a2b3c4: the anchor source 'alpha' is resolved by its capability's "
        "command, which runs in the working tree and reads what is there — and the working\n"
        "tree is not 1a2b3c4 (HEAD is at 0000000). Run from a checkout at 1a2b3c4: HEAD at "
        "1a2b3c4, nothing uncommitted.\n"
    )
    stderr = [refusal]

    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, "", stderr[0])

    monkeypatch.setattr(fa.subprocess, "run", run)
    found = fa._run_check(HEAD, "main", cwd=None)
    assert isinstance(found, fa._NoDocument) and found.elsewhere
    stderr[0] = "Error: the base main does not resolve\n"
    found = fa._run_check(HEAD, "main", cwd=None)
    assert isinstance(found, fa._NoDocument) and not found.elsewhere


def test_a_base_that_cannot_be_fetched_is_unreadable(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.git("remote", "add", "origin", str(repo.root / "no-such-remote"))
    repo.git("update-ref", "refs/remotes/origin/main", repo.git("rev-parse", "main").stdout.strip())
    found = fa.derive(head, "main")
    assert found.document is None
    assert (
        found.problem is not None and "the base origin/main could not be fetched" in found.problem
    )


def test_a_resolver_runs_from_a_temporary_checkout_of_the_head(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    """A registered kind's resolver runs only from a checkout at the head named; run
    from `main`, the list is derived from a checkout of the head made for it and
    removed after."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    register_kinds(repo.root, "kinds", kinds={"source": "resolve"}, script_body=RESOLVING)
    repo.write({"sources/alpha.md": "alpha\n"})
    repo.write({"docs/sourced.md": document("sourced", anchors={"source": ["alpha"]}, at=T1)})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("the source changes", {"sources/alpha.md": "alpha, captured again\n"})
    deferred = document(
        "sourced",
        anchors={"source": ["alpha"]},
        at=T1,
        deferred=[("source", "alpha", "the recapture is checked with the next release")],
    )
    repo.commit("defer the source", {"docs/sourced.md": deferred})
    head = repo.head()
    repo.checkout("main")

    refused = subprocess.run(
        ["pkit", "friction", "check", "--json", "--base", "main", "--head", head],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 1 and "Run from a checkout at" in refused.stderr

    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    assert [(a["location"], a["answer"], a["reason"]) for a in found.answers] == [
        ("docs/sourced.md", "deferred", "the recapture is checked with the next release")
    ]
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert listed.count("worktree ") == 1, listed


def _branch_needing_its_resolver(make_adopter_repo: MakeAdopterRepo) -> tuple[AdopterRepo, str]:
    """A change whose list needs a registered kind's resolver, the clone on `main`."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    register_kinds(repo.root, "kinds", kinds={"source": "resolve"}, script_body=RESOLVING)
    repo.write({"sources/alpha.md": "alpha\n"})
    repo.write({"docs/sourced.md": document("sourced", anchors={"source": ["alpha"]}, at=T1)})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("the source changes", {"sources/alpha.md": "alpha, captured again\n"})
    deferred = document(
        "sourced",
        anchors={"source": ["alpha"]},
        at=T1,
        deferred=[("source", "alpha", "the recapture is checked with the next release")],
    )
    repo.commit("defer the source", {"docs/sourced.md": deferred})
    head = repo.head()
    repo.checkout("main")
    return repo, head


def test_no_checkout_is_made_when_the_first_run_answers(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")

    def no_checkout(_head: str) -> Any:
        raise AssertionError("a temporary checkout was made")

    monkeypatch.setattr(fa, "_checkout", no_checkout)
    found = fa.derive(head, "main")
    assert found.problem is None and len(found.answers) == 1


def test_a_failure_other_than_the_resolver_refusal_is_kept_with_no_checkout(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _branch_with_an_answer(make_adopter_repo)
    repo.checkout("main")
    repo.write({"notes.txt": "uncommitted\n"})
    monkeypatch.setattr(fa, "_checkout", lambda _head: pytest.fail("a checkout was made"))
    monkeypatch.setattr(fa, "_refresh_base", lambda _base: None)
    found = fa.derive(head, "no-such-base")
    assert found.document is None and found.problem is not None
    assert "--base no-such-base" in found.problem


def test_a_check_that_raises_inside_the_checkout_leaves_nothing_behind(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _branch_needing_its_resolver(make_adopter_repo)
    made: list[Path] = []
    mkdtemp = fa.tempfile.mkdtemp

    def recorded(**kwargs: Any) -> str:
        made.append(Path(mkdtemp(**kwargs)))
        return str(made[-1])

    run_check = fa._run_check

    def raising_inside(head_: str, base: str, *, cwd: Path | None) -> Any:
        if cwd is not None:
            assert (cwd / ".git").is_file()  # a linked worktree, made for this run
            raise RuntimeError("the check broke")
        return run_check(head_, base, cwd=cwd)

    monkeypatch.setattr(fa.tempfile, "mkdtemp", recorded)
    monkeypatch.setattr(fa, "_run_check", raising_inside)
    with pytest.raises(RuntimeError, match="the check broke"):
        fa.derive(head, "main")
    (scratch,) = made
    assert not scratch.exists()
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert listed.count("worktree ") == 1, listed
    assert not (repo.root / ".git" / "worktrees").exists() or not any(
        (repo.root / ".git" / "worktrees").iterdir()
    )


def test_only_this_runs_worktree_is_removed(
    fa: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    tmp_path: Path,
) -> None:
    """Cleanup takes away the checkout this run added, and leaves another stale
    worktree record — one a prune would take — as it found it."""
    repo, head = _branch_needing_its_resolver(make_adopter_repo)
    other = tmp_path / "someone-elses"
    repo.git("worktree", "add", "--detach", "--quiet", str(other), head)
    shutil.rmtree(other)  # stale: what `git worktree prune` would remove
    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    listed = repo.git("worktree", "list", "--porcelain").stdout
    assert str(other) in listed and listed.count("worktree ") == 2, listed


def test_a_termination_signal_removes_the_checkout(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    """SIGTERM — a harness's timeout — while the temporary checkout exists unwinds
    through its removal."""
    repo = make_adopter_repo()
    repo.write({"a.txt": "a\n"})
    repo.commit("base", files=None)
    script = tmp_path / "terminate.py"
    script.write_text(
        "import os, signal, sys\n"
        f"sys.path.insert(0, {str(LIB_DIR)!r})\n"
        "import friction_answers as fa\n"
        f"with fa._checkout({repo.head()!r}) as (path, why):\n"
        "    assert path is not None, why\n"
        "    print(path.parent, flush=True)\n"
        "    os.kill(os.getpid(), signal.SIGTERM)\n"
        "    raise AssertionError('not terminated')\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(script)], cwd=repo.root, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 128 + signal.SIGTERM, proc.stderr
    assert not Path(proc.stdout.strip()).exists()
    assert repo.git("worktree", "list", "--porcelain").stdout.count("worktree ") == 1


# ---- the friction settings a change alters -----------------------------------------


def test_a_change_that_sets_friction_dormant_lists_the_setting(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    """The settings decide what the change check asks: a change that empties the
    places makes the check dormant at its head, so it lists no answer — and the
    settings it altered are listed instead, as they were and as they are, read
    through the backbone's discovery at each commit."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    repo.commit("friction off", {CONFIG: friction_config(mode="enforcing", places=())})
    head = repo.head()
    found = fa.derive(head, "main")
    assert found.problem is None, found.problem
    assert found.answers == () and found.listed
    assert [(s.key, s.before, s.after) for s in found.settings] == [(fa.PLACES, ("docs",), ())]
    section = fa.render(found.document, head, found.settings)
    assert section is not None
    assert section.splitlines()[3:] == [
        "This change decided nothing about any document, but it changes which documents are "
        "checked.",
        "",
        f"As of commit `{head[:7]}`, no document is checked.",
        "",
        "- Checked locations: `docs` → none",
        fa.MARKER_END,
    ]
    assert fa.lines(found.document, found.settings) == ["Checked locations: docs → none"]


def test_a_change_that_excludes_an_artefact_lists_it(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.write({"docs/other.md": document("other", anchors={"path": ["src/core/**"]}, at=T1)})
    repo.commit("base", files=None)
    before = repo.head()
    excluding = friction_config(mode="enforcing", exclude=["docs/guide.md"])
    repo.commit("leave the guide out", {CONFIG: excluding})
    assert [(s.key, s.before, s.after) for s in fa.settings_change(before, repo.head())] == [
        (fa.EXCLUDED, (), ("docs/guide.md",))
    ]
    assert fa.settings_change(before, before) == ()


def test_settings_that_cannot_be_read_make_the_derivation_unreadable(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    repo.commit("base", files=None)
    before = repo.head()
    repo.commit("a broken configuration", {CONFIG: "friction: [unclosed\n"})
    found = fa.settings_change(before, repo.head())
    assert isinstance(found, str) and "pkit friction artefacts --json --at" in found
    assert fa.settings_change("", repo.head()) == (
        "the change check named no commit the head left its base at"
    )


def test_settings_follow_the_documents_one_line_each(fa: ModuleType) -> None:
    settings = [
        fa.Setting(fa.PLACES, ("docs",), ("docs", "guides")),
        fa.Setting(fa.EXCLUDED, (), ("docs/guide.md",)),
    ]
    section = fa.render(_document(_entry("a.md", "updated")), HEAD, settings)
    assert section is not None
    assert section.splitlines()[-8:] == [
        "1. `a.md` — **updated in this change**",
        "   - (what changed: the pull request's author has not said)",
        "",
        "It also changes which documents are checked:",
        "",
        "- Checked locations: `docs` → `docs`, `guides`",
        "- Documents excluded from checking: none → `docs/guide.md`",
        fa.MARKER_END,
    ]
    assert fa.lines(_document(), settings) == [
        "Checked locations: docs → docs, guides",
        "Documents excluded from checking: none → docs/guide.md",
    ]


def test_a_setting_is_read_for_closing_references_and_delimiters(fa: ModuleType) -> None:
    settings = [fa.Setting(fa.PLACES, (), ("fixes #5/**",))]
    assert fa.closing_reference(_document(), settings) == (fa.SETTINGS_WHERE, "fixes #5")
    settings = [fa.Setting(fa.PLACES, ("<!--/**",), ())]
    assert fa.comment_delimiter(_document(), settings) == (fa.SETTINGS_WHERE, "<!--")


# ---- the author's sentences (DEC-055 points 1 and 3) ----------------------------

#: A description whose author says what changed in each updated document.
SAID_BODY = (
    "Closes #42\n\n## Summary\n\nDone.\n\n"
    "## What changed in each updated document\n\n"
    "- `docs/a.md`: The install steps now name the renamed flag\n"
    "  and its old spelling.\n"
    "* `tech-docs/actors.md#ACT-one` — The actor is told what changed.\n"
    "- `docs/b.md` - Second item for b.\n"
    "- not a document\n"
    "- `docs/a.md`: A second sentence for a, not read.\n\n"
    "```\n- `docs/fenced.md`: inside a fence, not read\n```\n\n"
    "## Doc impact\n\n- `docs/elsewhere.md`: under another heading, not read\n"
)


def test_the_sentences_schema_heading_is_the_module_s(fa: ModuleType) -> None:
    schema = YAML(typ="safe").load((CAP_ROOT / "schemas" / "body-format.yaml").read_text("utf-8"))
    assert schema["friction_answers_marker"]["sentences_heading"] == fa.SENTENCES_HEADING


def test_the_sentences_are_read_from_the_author_s_section(fa: ModuleType) -> None:
    """One list item per document, the document in a code span, then the sentence;
    an item runs on over the lines under it; the first for a document wins; a
    fence, another section and an item naming no document are not read."""
    assert fa.sentences(SAID_BODY) == {
        "docs/a.md": "The install steps now name the renamed flag and its old spelling.",
        "tech-docs/actors.md#ACT-one": "The actor is told what changed.",
        "docs/b.md": "Second item for b.",
    }
    assert fa.sentences(BODY) == {}


@pytest.mark.parametrize(
    ("lines", "read"),
    [
        # A numbered item is a list item too.
        (["1. `docs/a.md`: Numbered."], {"docs/a.md": "Numbered."}),
        # A line that starts with `#` but is no heading runs the item on.
        (
            ["- `docs/a.md`: Rewrote the intro, as", "#123 asked."],
            {"docs/a.md": "Rewrote the intro, as #123 asked."},
        ),
        # A nested item is no sentence, and ends the one above it.
        (
            ["- `docs/a.md`: The intro.", "  - `docs/b.md` is linked from it", "- `docs/b.md`: B."],
            {"docs/a.md": "The intro.", "docs/b.md": "B."},
        ),
        # An HTML comment and a thematic break end an item; nothing after them joins it.
        (
            ["- `docs/a.md`: The intro.", "<!-- one item per document -->"],
            {"docs/a.md": "The intro."},
        ),
        (["- `docs/a.md`: The intro.", "---", "A paragraph."], {"docs/a.md": "The intro."}),
    ],
)
def test_an_item_is_a_top_level_list_item_and_ends_where_markdown_ends_it(
    fa: ModuleType, lines: list[str], read: dict[str, str]
) -> None:
    body = "## What changed in each updated document\n\n" + "\n".join(lines) + "\n"
    assert fa.sentences(body) == read


#: The form a warning names for a sentence.
FORM = "- `path`: sentence"


@pytest.mark.parametrize(
    ("lines", "read", "unread"),
    [
        # The read form gives its sentence and draws no warning.
        (["- `docs/a.md`: The intro."], {"docs/a.md": "The intro."}, []),
        # A path in bold, as on PR #1519: no sentence, and its line is named.
        (["- **docs/a.md:** The intro."], {}, [3]),
        # A path with no code span.
        (["- docs/a.md: The intro."], {}, [3]),
        # A bold code span is no code span right after the marker either.
        (["1. **`docs/a.md`**: The intro."], {}, [3]),
        # An item that names its document but gives no words.
        (["- `docs/a.md`:", "", "- `docs/b.md`: B."], {"docs/b.md": "B."}, [3]),
        # A list indented whole: no item starts in the first column.
        (["  - `docs/a.md`: The intro.", "  - `docs/b.md`: B."], {}, [3, 4]),
        # An item nested under a document's item is not one, nor is a thematic break.
        (
            ["- `docs/a.md`: The intro.", "  - **docs/b.md** is linked from it", "* * *"],
            {"docs/a.md": "The intro."},
            [],
        ),
        # An item indented less than the content of the item above is its sibling.
        (["- `docs/a.md`: The intro.", " - **docs/b.md:** B."], {"docs/a.md": "The intro."}, [4]),
        # A paragraph after a blank line ends the list: an indented item opens another.
        (
            ["- `docs/a.md`: The intro.", "", "Also:", "", "  - **docs/b.md:** B."],
            {"docs/a.md": "The intro."},
            [7],
        ),
        # A paragraph or a heading indented less than the item's content ends the list.
        (
            ["1. `docs/a.md`: A.", "", "  para", "   - **b**", "  ### H", " - **c**"],
            {"docs/a.md": "A."},
            [6, 8],
        ),
        # A comment or a fence inside an item's content leaves the list open.
        (
            [
                "- `docs/a.md`: A.",
                "  <!-- note -->",
                "  - nested",
                "  ```",
                "  x",
                "  ```",
                "  - too",
            ],
            {"docs/a.md": "A."},
            [],
        ),
        # Nothing inside an HTML comment renders, so nothing there is read or named.
        (["<!--", "- **docs/a.md:** An example.", "- `docs/b.md`: Another. -->"], {}, []),
        # A paragraph and an item under another heading are not the section's items.
        (["One sentence each:", "", "## Notes", "", "- **x**"], {}, []),
    ],
    ids=[
        "read form",
        "bold path",
        "no code span",
        "bold code span",
        "no words",
        "indented",
        "nested",
        "sibling",
        "new list",
        "outdented",
        "inside an item",
        "comment",
        "not an item",
    ],
)
def test_an_item_the_reading_cannot_read_is_named_by_its_line(
    fa: ModuleType, lines: list[str], read: dict[str, str], unread: list[int]
) -> None:
    """Every item under the heading either gives a sentence or is named, by the line
    it is on in the description, as the line is written."""
    body = "## What changed in each updated document\n\n" + "\n".join(lines) + "\n"
    assert fa.sentences(body) == read
    found = fa.unread(body)
    assert [item.line for item in found] == unread
    assert [item.text for item in found] == [body.split("\n")[n - 1] for n in unread]


def test_the_warning_names_the_line_and_the_form(fa: ModuleType) -> None:
    (item,) = fa.unread(SAID_BODY)  # `- not a document`
    assert (item.line, item.text) == (13, "- not a document")
    assert fa.SENTENCE_FORM == FORM
    assert fa.unread_warning(item) == (
        "line 13 of the description, under `## What changed in each updated document`, is not "
        f'read as a sentence: "- not a document" — write it as "{FORM}", starting in the '
        "line's first column, the document in a code span as the list names it"
    )


def test_a_line_keeps_its_number_past_the_list_and_is_shown_escaped(fa: ModuleType) -> None:
    """The list a command wrote is never read, yet its lines are counted, so the
    number is the line's in the description; a terminal is shown no control
    character of the author's."""
    listed = fa.render(_document(_entry("docs/a.md", "updated")), HEAD) or ""
    said = "## What changed in each updated document\n\n- **docs/a.md\x1b[2J:** Done.\n"
    body = f"Closes #42\n\n{listed}\n\n{said}\n{FOOTER}\n"
    (item,) = fa.unread(body)
    assert body.split("\n")[item.line - 1].startswith("- **docs/a.md")
    assert item.text == "- **docs/a.md\\x1b[2J:** Done."
    assert fa.sentences(body) == {}


def test_a_reason_quoting_the_updated_label_marks_no_entry_updated(fa: ModuleType) -> None:
    """The label counts only outside the code spans an artefact's words sit in."""
    document = _document(_entry("docs/a.md", "unchanged", "Was **updated in this change**."))
    block = fa.find(fa.render(document, HEAD) or "")
    assert block is not None
    assert fa.given_in(block, {"docs/a.md": "No."}) == {}
    assert fa.with_sentences(block, {"docs/a.md": "No."}) == block


def test_a_sentence_inside_the_list_or_the_footer_is_not_read(fa: ModuleType) -> None:
    """The list a command wrote is stripped first: a sentence it gives is never read
    back as the author's."""
    document = _document(_entry("docs/a.md", "updated"))
    listed = fa.stamp(SAID_BODY, fa.render(document, HEAD, (), {"docs/a.md": "Old."}))
    assert fa.sentences(listed)["docs/a.md"].startswith("The install steps")
    alone = fa.stamp(BODY, fa.render(document, HEAD, (), {"docs/a.md": "Old."}))
    assert fa.sentences(f"{alone}\n{FOOTER}\n") == {}


def test_each_updated_document_gives_its_sentence_or_says_there_is_none(fa: ModuleType) -> None:
    document = _document(
        _entry("docs/a.md", "updated", changed=[("path", "src/cli/**")]),
        _entry("docs/c.md", "updated", status="bump"),
        _entry("docs/b.md", "unchanged", "Holds."),
    )
    sentences = fa.given(document, fa.sentences(SAID_BODY))
    # Only the sentences of documents the list marks updated are given.
    assert sentences == {
        "docs/a.md": "The install steps now name the renamed flag and its old spelling."
    }
    assert fa.unsaid(document, sentences) == ["docs/c.md"]
    section = fa.render(document, HEAD, (), sentences)
    assert section is not None
    assert section.splitlines()[7:12] == [
        "1. `docs/a.md` relies on `src/cli/**`, which this change modifies. **Updated in this "
        "change**",
        "   - (what changed, in the words of the pull request's author: \"``The install steps "
        'now name the renamed flag and its old spelling.``")',
        "2. `docs/c.md` — **updated in this change** (re-check date changed with nothing behind "
        "it)",
        "   - (what changed: the pull request's author has not said)",
        '3. `docs/b.md` — **still accurate**: "``Holds.``"',
    ]
    assert fa.lines(document, (), sentences)[1:5] == [
        "1. docs/a.md relies on src/cli/**, which this change modifies. Updated in this change",
        "   (what changed, in the words of the pull request's author: \"The install steps now "
        'name the renamed flag and its old spelling.")',
        "2. docs/c.md — updated in this change (re-check date changed with nothing behind it)",
        "   (what changed: the pull request's author has not said)",
    ]


def test_what_the_person_is_told_is_the_sentences_and_what_is_left_out_of_date(
    fa: ModuleType,
) -> None:
    """As information, not a gate (DEC-055 point 3): what changed in each updated
    document, each document left out of date with the deferral's words — one the
    change wrote, or one a revalidation kept — and each setting changed. An answer
    that holds is the reviewer's to check, and is not told."""
    document = _document(
        _entry("docs/a.md", "updated"),
        _entry("docs/c.md", "updated"),
        _entry("docs/b.md", "unchanged", "Holds.", kept=[(("path", "x/**"), "Later, #12.")]),
        _entry("docs/d.md", "deferred", "With the redesign, #13.", anchor=("record", "COR-1")),
        _entry("docs/e.md", "unchanged", "Holds."),
    )
    settings = [fa.Setting(fa.PLACES, ("docs",), ("docs", "guides"))]
    told = fa.told(document, settings, {"docs/a.md": "Now says X."})
    assert told == [
        'What changed in docs/a.md: "Now says X."',
        "What changed in docs/c.md: the pull request's author has not said",
        'Left out of date: docs/b.md, for changes to x/**: "Later, #12."',
        'Left out of date: docs/d.md, for changes to decision record COR-1: "With the '
        'redesign, #13."',
        "Checked locations: docs → docs, guides",
    ]
    assert fa.counted_told(document) == (2, 2, 0)
    assert fa.told(_document(_entry("docs/e.md", "unchanged", "Holds."))) == []


def test_a_list_already_written_takes_the_sentences_as_they_now_stand(fa: ModuleType) -> None:
    """For an edit that derives nothing: each updated document's sentence as the
    author's section now has it, every other line — the check's words, the
    markers — as it was; the same list `render` gives with those sentences."""
    document = _document(
        _entry("docs/a.md", "updated"),
        _entry("docs/`tick`.md", "updated", changed=[("path", "src/**")]),
        _entry("docs/b.md", "unchanged", "Holds.", kept=[(("path", "x/**"), "Later.")]),
    )
    before = fa.find(fa.render(document, HEAD, (), {"docs/a.md": "Old words."}) or "")
    assert before is not None and "Old words." in before
    now = {"docs/`tick`.md": "Ticks are listed.", "docs/b.md": "Not updated, not given."}
    assert fa.given_in(before, now) == {"docs/`tick`.md": "Ticks are listed."}
    after = fa.with_sentences(before, fa.given_in(before, now))
    assert after == fa.find(fa.render(document, HEAD, (), now) or "")
    assert "Old words." not in after and "Not updated" not in after
    # A list written before sentences were given gains them in place.
    bare = "\n".join(line for line in before.splitlines() if "(what changed" not in line)
    assert fa.with_sentences(bare, fa.given_in(bare, now)) == after


@pytest.mark.parametrize(
    ("words", "closing", "delimiter"),
    [
        ("This fixes #12 for good.", ("docs/a.md", "fixes #12"), None),
        ("The footer: <!-- pkit-provenance:start -->", None, ("docs/a.md", "<!--")),
        ("Names #12 as the follow-up.", None, None),
    ],
)
def test_a_sentence_the_list_must_not_hold_is_named(
    fa: ModuleType,
    words: str,
    closing: tuple[str, str] | None,
    delimiter: tuple[str, str] | None,
) -> None:
    sentences = {"docs/a.md": words}
    assert fa.sentence_closing_reference(sentences) == closing
    assert fa.sentence_comment_delimiter(sentences) == delimiter


# -- a later head an authorisation covers (DEC-055 point 3) -------------------------


def test_the_backbone_says_a_later_head_of_answers_is_covered(
    fa: ModuleType, make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    """The real `pkit friction since`: the head after a revalidation alone is covered;
    the head after the code change is not, and the change outside is named."""
    repo, head = _branch_with_an_answer(make_adopter_repo)
    changed = repo.git("rev-parse", "HEAD~1").stdout.strip()
    found = fa.covers(changed[:9], head, "main")
    assert found == fa.Coverage(changed, head, True, inside=1)
    main = repo.git("rev-parse", "main").stdout.strip()
    found = fa.covers(main, head, "main")
    assert (found.covered, found.problem) == (False, None)
    assert found.outside == (
        f"src/cli/main.py ({changed[:7]}: not an artefact's file: no declared place holds it)",
    )


def _answering(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch, returncode: int, stdout: str
) -> list[tuple[list[str], str | None]]:
    """The backbone stood in for: each run's argv and whether routing was off."""
    seen: list[tuple[list[str], str | None]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append((argv, kwargs["env"].get("PKIT_NO_ROUTE")))
        return subprocess.CompletedProcess(argv, returncode, stdout, "Error: boom\n")

    monkeypatch.setattr(fa.subprocess, "run", run)
    monkeypatch.setattr(fa, "_refresh_base", lambda base: None)
    return seen


def _since_document(**fields: Any) -> str:
    document = {
        "schema_version": 1,
        "since": MERGE_BASE,
        "head": HEAD,
        "all_inside": True,
        "reason": None,
        "inside": ["docs/guide.md"],
        "outside": [],
        **fields,
    }
    return json.dumps(document)


def test_the_backbone_is_asked_unrouted_with_the_base_named(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PKIT_CHECK_BASE", "elsewhere")
    seen = _answering(fa, monkeypatch, 0, _since_document())
    assert fa.covers("0000000", HEAD, "integration/7-x").covered
    argv = ["pkit", "friction", "since", "0000000", "--head", HEAD, "--base", "integration/7-x"]
    assert seen == [([*argv, "--json"], "1")]


@pytest.mark.parametrize(
    ("returncode", "stdout", "why"),
    [
        (1, "", "it exited 1: Error: boom"),
        (0, "not json", "its answer is not JSON"),
        (0, '{"schema_version": 2}', "not a document of version 1"),
        (0, '{"schema_version": 1, "since": "a", "head": "b"}', "lacks what an answer needs"),
        (0, _since_document(all_inside="yes"), "lacks what an answer needs"),
        (0, _since_document(all_inside=False), "and the changes it names disagree"),
        (
            0,
            _since_document(outside=[{"path": "a.py", "commit": HEAD, "why": "added"}]),
            "and the changes it names disagree",
        ),
        (0, _since_document(reason="it was rebased"), "and the changes it names disagree"),
    ],
)
def test_an_answer_that_cannot_be_read_is_never_covered(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch, returncode: int, stdout: str, why: str
) -> None:
    _answering(fa, monkeypatch, returncode, stdout)
    found = fa.covers("0000000", HEAD, "main")
    assert not found.covered
    assert found.problem is not None and why in found.problem


def test_a_base_that_cannot_be_fetched_is_never_covered(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _answering(fa, monkeypatch, 0, _since_document())
    monkeypatch.setattr(fa, "_refresh_base", lambda base: "the base origin/main is gone")
    found = fa.covers("0000000", HEAD, "main")
    assert (found.covered, found.problem) == (False, "the base origin/main is gone")
    assert seen == []


def test_the_changes_outside_are_named_with_the_reason_first(
    fa: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = [{"path": "src/\x1b[31mx.py", "commit": HEAD, "why": "added"}]
    document = _since_document(all_inside=False, reason="it was rebased", outside=outside)
    _answering(fa, monkeypatch, 0, document)
    found = fa.covers("0000000", HEAD, "main")
    assert found.outside == ("it was rebased", f"src/\\x1b[31mx.py ({HEAD[:7]}: added)")
