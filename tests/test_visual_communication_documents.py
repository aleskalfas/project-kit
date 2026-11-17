"""Each document a visual-communication command prints for a program holds its contract
(ADR-097 point 7).

Each test runs the command's script in the test's own process (`tests/in_process.py`), from
a project the command's own tests build, and holds what it prints to the contract pinned
here with `tests/document_contracts.py`. A key or a value that goes, or comes back, fails
until the same change updates the pin, beside the changeset that declares the break.
`tests/test_capability_documents.py` holds the ratchet over every capability's commands.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.document_contracts import Contract, Form, check
from tests.in_process import load, run_main
from tests.test_visual_communication_checks import deck_project
from tests.test_visual_communication_intent import PIECE as BRIEFED
from tests.test_visual_communication_intent import intent, write_brief
from tests.test_visual_communication_look import (
    name_browser,
    no_browser_here,
    pages,
    starter_project,
    write_program,
)
from tests.test_visual_communication_verdict import COVERS, Copy, configured, grade, kept
from tests.visual_communication_project import project

(verdicts,) = load("visual-communication", "verdicts")


def _printed(script: ModuleType, root: Path, *args: str) -> dict[str, Any]:
    done = run_main(script, "--json", *args, cwd=root)
    assert done.returncode == 0, done.stderr
    document = json.loads(done.stdout)
    assert isinstance(document, dict), done.stdout
    return document


# --- `pkit visual intent --json` -----------------------------------------------------------

VISUAL_INTENT = Contract(
    name="pkit visual intent --json",
    forms={
        "answer": Form(
            keys={
                "piece": "str",
                "intent": "object|null",
                "intent.piece": "object",
                "intent.pages": "object",
                "intent.pages{}": "object",
            }
        )
    },
    shapes={
        "part": Form(
            keys={
                "goals": "list",
                "goals[]": "str",
                "relations": "list",
                "relations[]": "object",
                "relations[].text": "str",
                "relations[].relates": "list",
                "relations[].relates[]": "str",
                "takeaway": "str",
            }
        )
    },
    refs={"intent.piece": "part", "intent.pages{}": "part"},
    data=frozenset({"intent.pages"}),
)


def test_the_intent_document_holds_its_contract(tmp_path: Path) -> None:
    briefed = deck_project(tmp_path / "briefed")
    write_brief(
        briefed,
        piece={
            "goals": ["A newcomer can say where a decision lives."],
            "relations": [{"text": "A cover, then rules.", "relates": ["slides[cover].title"]}],
        },
        pages={"cover": {"takeaway": "What the talk is about."}},
    )
    unbriefed = deck_project(tmp_path / "unbriefed")
    check(
        VISUAL_INTENT,
        {"answer": [_printed(intent, briefed, BRIEFED), _printed(intent, unbriefed, BRIEFED)]},
    )


# --- `pkit visual pages --json` ------------------------------------------------------------

VISUAL_PAGES = Contract(
    name="pkit visual pages --json",
    forms={
        "answer": Form(
            keys={
                "piece": "str",
                "languages": "list",
                "languages[]": "str",
                "keys": "list",
                "keys[]": "str",
                "drawn-by-default": "object",
                "drawn-by-default.language": "str",
                "drawn-by-default.key": "str",
                "pages": "object",
                "pages{}": "list",
                "pages{}[]": "str",
                "renderer": "str",
                "tools": "object",
                "tools.svg": "object",
                "tools.svg.name": "str",
                "tools.svg.version": "str",
                "tools.svg.wheel": "str",
                "tools.html": "object",
                "tools.html.program": "str|null",
                "tools.html.named": "bool",
                "tools.html.looked": "list",
                "tools.html.looked[]": "str",
                "tools.html.forced-palettes": "list",
                "tools.html.forced-palettes[]": "str",
            }
        )
    },
    sets={
        "renderer": frozenset({"svg", "html"}),
        "tools.html.forced-palettes[]": frozenset({"light", "dark"}),
    },
    data=frozenset({"pages"}),
)


def test_the_pages_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    named = starter_project(tmp_path / "named")
    name_browser(named, write_program(tmp_path / "browser" / "chromium"))
    printed = [_printed(pages, named, "tag")]
    no_browser_here(tmp_path, monkeypatch)
    printed.append(_printed(pages, starter_project(tmp_path / "none"), "tag"))
    check(VISUAL_PAGES, {"answer": printed}, enumerations={"renderer": ("svg", "html")})


# --- `pkit visual verdict --json` ----------------------------------------------------------

VISUAL_VERDICT = Contract(
    name="pkit visual verdict --json",
    forms={
        "answer": Form(
            keys={
                "piece": "str",
                "round": "int",
                "report": "str",
                "bar": "object|null",
                "rules": "list",
                "rules[]": "str",
                "verdict": "object|null",
                "verdict.meets": "bool",
                "verdict.pages": "list",
                "verdict.pages[]": "object",
                "verdict.pages[].page": "str",
                "verdict.pages[].meets": "bool",
                "verdict.pages[].failing": "list",
                "verdict.pages[].failing[]": "object",
                "verdict.piece": "object",
                "verdict.piece.meets": "bool",
                "verdict.piece.failing": "list",
                "verdict.piece.failing[]": "object",
                "verdict.marked": "list",
                "verdict.marked[]": "object",
                "ends-the-loop": "bool",
                "why": "list",
                "why[]": "str",
                "reading": "object|null",
                "reading.rules": "object",
                "reading.rules{}": "object",
                "reading.rules{}.major": "int",
                "reading.rules{}.text": "str",
                "reading.reviewer": "str|null",
                "reading.design-knowledge": "str",
                "reading.code": "str",
                "reading.checks": "str|null",
                "reading.model": "object",
                "reading.model.name": "str",
                "reading.model.effort": "str",
            }
        )
    },
    shapes={
        "grade": Form(
            keys={
                "rule": "str",
                "on": "object",
                "on.page": "str",
                "on.piece": "bool",
                "grade": "str",
                "evidence": "str",
                "mark": "str",
            }
        )
    },
    refs={
        "verdict.pages[].failing[]": "grade",
        "verdict.piece.failing[]": "grade",
        "verdict.marked[]": "grade",
    },
    sets={
        "grade:grade": frozenset({"below competent", "competent", "professional", "excellent"}),
        "grade:mark": frozenset({"need", "asker"}),
    },
    data=frozenset({"reading.rules"}),
    payloads=frozenset({"bar"}),
)


def test_the_verdict_document_holds_its_contract(tmp_path: Path) -> None:
    given = Copy(project(tmp_path / "given"))
    configured(given, *COVERS)
    kept(
        given,
        [
            grade("RS-GRAPHIC-001", page="cover", grade="excellent"),
            grade("RS-GRAPHIC-001", page="layers", grade="competent"),
            grade("RS-GRAPHIC-001", "need", page="layers", grade="below competent"),
            grade("RS-COMM-003", grade="professional"),
            grade("RS-COMM-003", "asker", grade="below competent"),
        ],
    )
    whole = Copy(project(tmp_path / "whole"))
    configured(whole, *COVERS)
    kept(whole, [grade("RS-GRAPHIC-001", page="cover"), grade("RS-COMM-003", grade="competent")])
    no_bar = Copy(project(tmp_path / "no-bar"))
    kept(no_bar, [grade("RS-GRAPHIC-001", page="cover")])
    left_out = Copy(project(tmp_path / "left-out"))
    configured(left_out, *COVERS)
    kept(left_out, [grade("RS-GRAPHIC-001", page="cover")])
    printed = [copy.answered("deck") for copy in (given, whole, no_bar, left_out)]
    check(
        VISUAL_VERDICT,
        {"answer": printed},
        enumerations={"grade:grade": verdicts.GRADES},
    )


#: The contracts of each visual-communication command that prints a document for a
#: program, by the command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "visual-communication intent": (VISUAL_INTENT,),
    "visual-communication pages": (VISUAL_PAGES,),
    "visual-communication verdict": (VISUAL_VERDICT,),
}
