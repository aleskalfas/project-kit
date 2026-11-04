"""Tests for the reading of YAML's plain block form beside ruamel's loader (#2410): every
text reads as the loader reads it, read here where it is in the form, by the loader
otherwise — the loader's own error included — and the answer files are in the form."""

from __future__ import annotations

import random
import sys
import tomllib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import ruamel.yaml
from packaging.version import Version
from ruamel.yaml import YAML
from ruamel.yaml.constructor import BaseConstructor
from ruamel.yaml.reader import Reader
from ruamel.yaml.resolver import VersionedResolver

from project_kit import answer_files as af
from project_kit import block_yaml, document_parts
from project_kit import friction_discovery as fd
from project_kit import friction_write as fw

REPO_ROOT = Path(__file__).resolve().parent.parent


def _exact(value: Any) -> Any:
    """`value` with every type and key order spelt out: `1`, `1.0` and `True` are equal
    in Python, and so are two mappings in different orders."""
    if isinstance(value, dict):
        return ("dict", tuple((_exact(k), _exact(v)) for k, v in value.items()))
    if isinstance(value, list):
        return ("list", tuple(_exact(v) for v in value))
    if isinstance(value, datetime):
        return ("datetime", value.isoformat(), repr(value.tzinfo))
    return (type(value).__name__, repr(value))


def _outcome(read: Callable[[], Any]) -> tuple[str, Any]:
    try:
        return ("value", _exact(read()))
    except Exception as exc:  # the loader's error is part of what it gives
        return ("error", (type(exc).__name__, str(exc)))


def _loaded(text: str) -> Any:
    """The text as a loader of its own reads it: a loader that failed on a text keeps
    what it had built of it, and may fail on the next with an error of the last."""
    return YAML(typ="safe", pure=True).load(text)


def _both(text: str) -> tuple[tuple[str, Any], tuple[str, Any], bool]:
    """The loader's outcome, `load`'s, and whether `load` read the text itself."""
    asked: list[bool] = []

    def fallback() -> Any:
        asked.append(True)
        return _loaded(text)

    expected = _outcome(lambda: _loaded(text))
    found = _outcome(lambda: block_yaml.load(text, fallback))
    return expected, found, not asked


# --- texts at the edges of the form -------------------------------------------------

#: Each text is read as the loader reads it, here or by the loader: where the form ends,
#: and where YAML's own rules are easy to read wrong.
EDGES = [
    # plain scalars and their types
    "a: x\nb: README.md\nc: a b  c\n",
    "a: 12\nb: -12\nc: 0o17\nd: 0x1F\ne: 1_000\nf: 1.5\ng: 1e3\nh: .inf\ni: .nan\n",
    "a: true\nb: True\nc: yes\nd: no\ne: on\nf: null\ng: Null\nh: ~\ni:\n",
    "at: 2026-10-30T04:15:20Z\nday: 2026-10-30\nspaced: 2026-1-1 9:00:00Z\n",
    "zoned: 2026-01-01 09:00:00 +02:00\nfraction: 2026-01-01T09:00:00.5Z\n",
    "a: x:y\nb: pkit::work-tracking:doc-check\nc: COR-013#1\nd: http://example.com/a\n",
    "a: x # a comment\nb: x# no comment\nc: x #\nd: # nothing but a comment\n",
    'a: a, b\nb: a [b] {c}\nc: a]b\nd: don\'t\ne: say "hi"\n',
    "a: x: y\n",
    "a: x:\n",
    "a: -x\nb: - x\nc: ?x\nd: x?\ne: :x\nf: '%x'\n",
    "a: '%x'\nb: '@x'\nc: '`x`'\n",
    "a: %x\n",
    "a: @x\n",
    "a: =\nb: <<\n",
    "<<: {a: 1}\nb: 2\n",
    "a: é — ü\nb: \u00a0x\nc: x\u00a0\nd: 日本\n",
    # quoted scalars
    "a: 'single'\nb: 'it''s'\nc: ''\nd: ' padded '\n",
    "a: 'x' # c\nb: 'x' y\n",
    'a: "double"\nb: "a\\nb\\tc"\nc: "\\u00e9"\nd: "a\\"b\\\\c"\ne: "\\/"\nf: ""\n',
    'a: "\\ud83d\\ude00"\n',
    'a: "\\x41"\nb: "\\N"\nc: "\\e"\n',
    'a: "x" # c\nb: "x" y\n',
    'a: "unterminated\n',
    'a: "over\n  lines"\n',
    'a: "#not a comment"\n',
    # flow collections
    "a: []\nb: {}\nc: [ ]\nd: { }\n",
    "a: [x, y]\nb: [x,y]\nc: [ x  y , z ]\nd: [x:y, pkit::a]\ne: [RS-1#x]\n",
    "a: [x #y]\n",
    "a: [x, , y]\n",
    "a: [x, y, ]\n",
    "a: [x: y]\n",
    "a: [x:, y]\n",
    'a: ["x", \'y\', "z, w"]\nb: [[x], [y, [z]]]\n',
    'a: {x: y, z: [1, 2]}\nb: {id: TERM-a, name: a b}\nc: {d: "q"}\n',
    "a: {x}\nb: {x: }\n",
    "a: {x: y, x: z}\n",
    "a: [x] y\nb: [x] # c\n",
    "a: [\n",
    "a: [x\n",
    "a: [x,\n",
    "a: [x, [y]\n",
    "a: {\n",
    "a: {x: y\n",
    "a: {x: y,\n",
    "a: {x:\n",
    "- [\n",
    "a: [x,\n  y]\n",
    "a: {x: y,\n  z: w}\n",
    # block structure
    "a:\n  b:\n    c: d\n  e: f\ng: h\n",
    "a:\n- x\n- y\nb: z\n",
    "a:\n  - x\n  - y\n",
    "- a\n- b: c\n  d: e\n- - f\n",
    "- a: b\n  c:\n  - d\n  e: f\n",
    "-   a: b\n    c: d\n",
    "-\n  a: b\n",
    "a:\n  x\n",
    "a: x\n  y\n",
    "a: x\n\n  y\n",
    "a: x\n  # a comment, not more of x\nb: y\n",
    "a:\n  b: c\n d: e\n",
    "a:\n    b: c\n  d: e\n",
    "a: x\n- y\n",
    "  a: x\n  b: y\n",
    "  a: x\nb: y\n",
    "a: x\na: y\n",
    "1: x\n",
    "null: x\n",
    "2026-01-01: x\n",
    "a b: x\n",
    "a:b: x\nc::\n",
    "'a': x\n",
    "? a\n: x\n",
    "a: &anchor x\nb: *anchor\n",
    "a: !!str 1\n",
    "a: |\n  text\n",
    "a: >-\n  folded\n  text\n",
    # documents
    "",
    "# only a comment\n",
    "x\n",
    "---\na: x\n",
    "a: x\n...\n",
    "%YAML 1.1\n---\na: yes\n",
    "a: x\n---\nb: y\n",
    # characters the loader refuses, or reads as a break
    "a: x\tb\n",
    "a:\tx\n",
    "a: x\r\nb: y\r\n",
    "a: x\u2028b: y\n",
    "a: x\x85b\n",
    "\ufeffa: x\n",
    "a: x\x07\n",
    "a: x\x7f\n",
    "a: x  \nb: y   \n",
]


@pytest.mark.parametrize("text", EDGES)
def test_each_text_at_the_edges_reads_as_the_loader_reads_it(text: str) -> None:
    expected, found, _here = _both(text)
    assert found == expected


def test_a_text_in_the_form_is_read_without_the_loader() -> None:
    expected, found, here = _both(
        "answers:\n  - artefact: README.md\n    read:\n      - a.yaml\n    revalidated:\n"
        "      at: 2026-10-30T04:15:20Z\n      outcome: unchanged\n"
        '      unchanged-because: "it holds: still"\n'
    )
    assert here and found == expected


@pytest.mark.parametrize(
    "text",
    ["a: x\na: y\n", "a: x\n  y: z\n", "a: [x, y\n", 'a: "x\n', "a:\n  b: c\n d: e\n"],
)
def test_a_text_the_loader_refuses_raises_its_error(text: str) -> None:
    """A text this reading is unsure of is the loader's, so a text it refuses fails as
    it fails, with its own error."""
    expected, found, here = _both(text)
    assert expected[0] == "error"
    assert found == expected and not here


# --- the loader this reading takes its parts from -------------------------------------


def test_every_fallback_reads_by_the_pure_python_loader() -> None:
    """The exact reading is ruamel's pure-Python safe loader: a fallback left to pick
    libyaml, where ruamel's compiled binding is installed, would read YAML 1.1. Each
    module that calls this reading hands it a fallback through its own `_yaml`."""
    callers = sorted(
        path.stem
        for path in (REPO_ROOT / "src" / "project_kit").glob("*.py")
        if "block_yaml.load(" in path.read_text(encoding="utf-8")
    )
    assert callers == ["answer_files", "document_parts", "friction_discovery"]
    for module in (af, document_parts, fd):
        assert module._yaml.pure is True, module.__name__


def test_the_declared_floor_of_the_loader_is_its_oldest_tested_version() -> None:
    """An install resolves no ruamel.yaml older than the versions this reading is held to."""
    dependencies = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    (floor,) = [
        requirement.removeprefix("ruamel.yaml>=")
        for requirement in dependencies["project"]["dependencies"]
        if requirement.startswith("ruamel.yaml")
    ]
    assert floor == min(block_yaml.TESTED_VERSIONS, key=Version)


def test_the_reading_is_on_with_the_installed_loader() -> None:
    """The locked ruamel.yaml is a version this reading is held to: a lock moved to another
    fails here, until the two readings are compared under it."""
    assert ruamel.yaml.__version__ in block_yaml.TESTED_VERSIONS
    assert block_yaml.ON


@pytest.mark.parametrize(
    "removed",
    [
        "a version not tested",
        "the reader's refused characters",
        "the constructor's call",
        "the resolver's call",
        "the module of nodes",
    ],
)
def test_a_loader_without_a_part_this_reading_takes_turns_it_off(
    removed: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Under a ruamel.yaml version it was not held to, or one without a part this reading
    takes, or that calls one another way, the parts are not taken, so the reading is off
    rather than misreading or failing at import."""
    if removed == "a version not tested":
        monkeypatch.setattr(ruamel.yaml, "__version__", "0.20.0")
    elif removed == "the reader's refused characters":
        monkeypatch.delattr(Reader, "NON_PRINTABLE")
    elif removed == "the constructor's call":
        monkeypatch.delattr(BaseConstructor, "construct_non_recursive_object")
    elif removed == "the resolver's call":
        monkeypatch.setattr(VersionedResolver, "resolve", lambda self, value: None)
    else:
        monkeypatch.setitem(sys.modules, "ruamel.yaml.nodes", None)
    assert block_yaml._parts() is None


def test_a_reading_turned_off_gives_every_text_to_the_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(block_yaml, "ON", False)
    expected, found, here = _both("a: x\nb: [1, 2]\n")
    assert found == expected and not here


# --- texts made at random around the form -------------------------------------------

_KEYS = [
    "a", "b", "key", "TERM-x", "x_y", "a.b", "pkit::work-tracking:doc-check", "a:b", "1",
    "null", "true", "2026-01-01", "<<", "a b", "'q'", '"q"', "a#b", "~", "-k", "?k", "日本",
]  # fmt: skip
#: Scalars in the form, as files write them.
_PLAIN_FORM = [
    "x", "README.md", "a b", "a#b", "a:b", "pkit::a", "12", "1.5", "true", "null", "~", "é —",
    "2026-01-01T09:00:00Z", "2026-01-01", "'single'", "'it''s'", '"double"', '"a\\nb: c"', "[]",
    "{}", "[a, b]", "[RS-1#x, 'y', \"z\"]", "{a: b, c: [d]}", "x # c", '"q" # c',
]  # fmt: skip
#: Scalars at the edges of the form, or past them.
_SCALARS = [
    "x", "README.md", "a b", "a  b", "a: b", "a #b", "a#b", "a:b", "a:", ":a", "-", "-x", "- x",
    "?x", "x?", "~", "null", "Null", "true", "True", "yes", "12", "-12", "0o17", "0x1F", "1_000",
    "1.5", "1e3", ".inf", "-.inf", ".nan", "2026-01-01", "2026-01-01T09:00:00Z",
    "2026-1-1 9:00:00Z", "2026-01-01 09:00:00 +02:00", "'single'", "'it''s'", "'a' b", "''",
    '"double"', '"a\\nb"', '"\\u00e9"', '"\\ud83d\\ude00"', '"\\x41"', '"a\\"b"', '"a" b', '""',
    '"unterminated', "[a, b]", "[]", "{}", "{a: b}", "[a: b]", "[a, , b]", "[a,]", "[a, [b]]",
    "{a: [b, c]}", "[\"x\", 'y']", "[a #b]", "[RS-1#x]", "{a: b, a: c}", "*alias", "&anchor x",
    "!tag x", "!!str 1", "|", ">-", "%x", "@x", "`x`", "é", "a\u00a0b", "#x", "x # c", "x #",
    "=", "<<", "a, b", "a [b]", "a]b", "{a: b} x", "[a] # c", '"q" # c', "'q' #c", "x\ty",
]  # fmt: skip


def _document(chance: random.Random) -> str:
    """A text in or around the block form: nested mappings and sequences in the layouts
    YAML allows — sequences under a key indented or not, an entry's mapping on its dash's
    line or the next — with comments, blank lines and trailing spaces; now and then a
    line moved off its indent, repeated, or broken."""
    lines: list[str] = []
    step = chance.choice([2, 2, 2, 4, 1])

    def scalar() -> str:
        return chance.choice(_PLAIN_FORM if chance.random() < 0.85 else _SCALARS)

    def mapping(indent: int, depth: int, lead: str | None) -> None:
        keys = chance.sample(_KEYS[:8], chance.randint(1, 4))
        for index, key in enumerate(keys):
            if chance.random() < 0.05:
                key = chance.choice(_KEYS)  # past the form, or written twice
            prefix = f"{lead} " if (lead is not None and index == 0) else " " * indent
            pick = chance.random()
            if depth >= 3 or pick < 0.5:
                lines.append(f"{prefix}{key}: {scalar()}")
                continue
            lines.append(f"{prefix}{key}:")
            if pick < 0.52:
                lines.append(" " * (indent + step) + scalar())  # a scalar on the next line
            elif pick < 0.8:
                mapping(indent + step, depth + 1, None)
            elif pick < 0.9:
                sequence(indent, depth + 1, None)  # its dashes at the key's column
            else:
                sequence(indent + step, depth + 1, None)

    def sequence(indent: int, depth: int, lead: str | None) -> None:
        for index in range(chance.randint(1, 4)):
            dash = f"{lead} -" if (lead is not None and index == 0) else " " * indent + "-"
            pick = chance.random()
            if depth >= 3 or pick < 0.5:
                lines.append(f"{dash} {scalar()}")
            elif pick < 0.85:
                mapping(indent + 2, depth + 1, dash)  # its first key on the dash's line
            elif pick < 0.9:
                lines.append(f"{dash} - {scalar()}")
            else:
                lines.append(dash)
                mapping(indent + step, depth + 1, None)

    (mapping if chance.random() < 0.7 else sequence)(0, 0, None)
    for _ in range(chance.randint(0, 2)):
        at = chance.randrange(len(lines) + 1)
        lines.insert(at, chance.choice(["", "# a comment", "  # an indented comment", "   "]))
    if chance.random() < 0.15:
        at = chance.randrange(len(lines))
        lines[at] = " " + lines[at] if chance.random() < 0.5 else lines[at][1:]
    if chance.random() < 0.05:
        at = chance.randrange(len(lines))
        lines.insert(at, lines[at])
    if chance.random() < 0.1:
        at = chance.randrange(len(lines))
        lines[at] += chance.choice(["  ", " # trailing", "\t"])
    return "\n".join(lines) + "\n"


@pytest.mark.filterwarnings("ignore::ruamel.yaml.error.ReusedAnchorWarning")
def test_texts_made_at_random_read_as_the_loader_reads_them() -> None:
    """Some thousands of texts, in the form and just outside it: each reads as the loader
    reads it, and enough of them are read here, and enough by the loader, for both
    readings to be held."""
    chance = random.Random(2410)
    here = 0
    texts = [_document(chance) for _ in range(2000)]
    for text in texts:
        expected, found, read_here = _both(text)
        assert found == expected, text
        here += read_here
    assert 0.25 * len(texts) < here < 0.75 * len(texts)


def test_texts_cut_short_at_random_read_as_the_loader_reads_them() -> None:
    """A text cut anywhere, mid-line, mid-quote or mid-collection, reads as the loader
    reads it: a reading never fails where the loader's would not."""
    chance = random.Random(2411)
    for _ in range(1000):
        text = _document(chance)
        cut = text[: chance.randrange(1, len(text) + 1)]
        expected, found, _here = _both(cut)
        assert found == expected, cut


# --- the answer files ------------------------------------------------------------------

#: Reasons as people write them: words the writer leaves plain, and words it quotes.
_REASONS = [
    "The page states nothing the change decides.",
    "ACT-developer's need now names the bump segment — with the same meaning.",
    "It holds: the reading is the same.",
    "#2410 builds it, and the reference follows.",
    'It says "stale" where it meant "out of date".',
    "- a reason that opens like an entry",
    "a reason with a back\\slash and 'quotes'",
    "null",
    "12",
]


def test_the_answer_writer_s_files_are_read_without_the_loader() -> None:
    """The form the writer gives answer files is read here, so the check's reading of
    every answer file in history stays off the loader."""
    entries = [
        {
            af.ARTEFACT_KEY: location,
            af.READ_KEY: [f"2026103{n}T0{n}1520Z-4151420{n}.yaml" for n in range(index % 4)],
            af.REVALIDATED_KEY: {
                "at": f"2026-10-30T0{index % 10}:15:20Z",
                "outcome": "unchanged" if index % 2 else "updated",
                "unchanged-because": reason,
                af.DEFERRED_KEY: [
                    {"anchor": {"kind": "record", "value": "ADR-057"}, "reason": reason}
                ]
                if index % 3 == 0
                else [],
            },
        }
        for index, (location, reason) in enumerate(
            zip(["README.md", "docs/a b.md", "tech-docs/x.md#TERM-a"] * 3, _REASONS, strict=False)
        )
    ]
    text, _first, _last = fw.answer_file_text(entries)
    expected, found, here = _both(text)
    assert here and found == expected


@pytest.mark.answers
def test_every_answer_file_of_the_tree_is_read_without_the_loader() -> None:
    """The project's own answer files are all read here, and a sample of them as the
    loader reads them: an answer file the writer did not shape this way would put the
    check's time back on the loader."""
    paths = sorted((REPO_ROOT / af.FOLDER).glob(f"*{af.SUFFIX}"))
    assert paths
    for index, path in enumerate(paths):
        text = path.read_text(encoding="utf-8")
        assert block_yaml.load(text, _refused) is not None, path.name
        if index % 25 == 0:
            expected, found, _here = _both(text)
            assert found == expected, path.name


def _refused() -> Any:
    raise AssertionError("read by the loader")
