"""The pages' contents lists, `scripts/page_contents.py` (#2053).

- **Which pages:** the artefacts living-docs' page type types, wherever they lie,
  as the console fences' run chooses them; a page without the markers is left
  alone.
- **What the list holds:** one item for each second-level heading, in the page's
  order, outside fenced code; a heading of another level is none. The item shows
  the heading's text, a link in it read as its words.
- **The address:** the host's, built on the backbone's slug: a code span's text
  kept, punctuation dropped, underscores kept, a link read as its words, and a
  repeated title numbered `-1`, `-2` over headings of every level. An explicit
  anchor kept for an old address changes no item.
- **The check:** a stale list fails, naming its page and line; so do markers that
  make no one pair. `--update` writes each stale list between its markers and
  nothing else, and no list where the markers fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts import console_fences as cf
from scripts import page_contents as pc

from project_kit.document_parts import heading_slug
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

OPEN, CLOSE = pc.OPENING, pc.CLOSING


def _page(*body: str) -> str:
    return "\n".join(["---", "reader: user", "kind: guide", "---", "", "# Guide", "", *body, ""])


class Pages:
    """A repository of fixture pages, and the check run on them."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "repo"
        self.root.mkdir()

    def write(self, path: str, *body: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_page(*body), encoding="utf-8")

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")

    def run(self, *paths: str, update: bool = False) -> pc.Report:
        return pc.check_pages(self.root, paths or ("guide.md",), update=update)


@pytest.fixture
def pages(tmp_path: Path) -> Pages:
    return Pages(tmp_path)


def _list(text: str) -> list[str]:
    """The lines between a text's markers."""
    lines = text.split("\n")
    return lines[lines.index(OPEN) + 1 : lines.index(CLOSE)]


# --- what the list holds ---------------------------------------------------------------


def test_update_writes_each_second_level_heading_in_order_and_the_list_is_then_fresh(
    pages: Pages,
) -> None:
    pages.write(
        "guide.md",
        "A guide to read in any order.",
        "",
        OPEN,
        CLOSE,
        "",
        "## Installing",
        "",
        "### From a checkout",
        "",
        "```markdown",
        "## A heading in fenced code",
        "```",
        "",
        "## Using it",
    )

    report = pages.run(update=True)

    assert report.updated == ["guide.md"]
    assert pc.exit_status(report, update=True) == 0
    assert _list(pages.read("guide.md")) == [
        "- [Installing](#installing)",
        "- [Using it](#using-it)",
    ]
    again = pages.run()
    assert again.findings == [] and again.lists == 1
    assert pc.exit_status(again, update=False) == 0


def test_an_item_shows_the_heading_s_text_a_link_read_as_its_words() -> None:
    body = "\n".join(
        [
            "# Guide",
            "",
            "## The `--update` flag",
            "## See [the reference](reference.md) <a id='old'></a>",
        ]
    )

    assert pc.items(body) == [
        "- [The `--update` flag](#the---update-flag)",
        "- [See the reference](#see-the-reference)",
    ]


# --- the address -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("The `--update` flag", "the---update-flag"),
        ("Hooks (`after_record`)", "hooks-after_record"),
        ("`pkit validate`", "pkit-validate"),
        ("What's new? (v2.0)", "whats-new-v20"),
        ("Step 1 — short title", "step-1--short-title"),
        ("Privilege *definitions*", "privilege-definitions"),
        ("depends_on — metadata", "depends_on--metadata"),
        ("The _new_ way", "the-new-way"),
        ("A \\_kept\\_ underscore", "a-_kept_-underscore"),
        ("See [the guide](guide.md)", "see-the-guide"),
        ("Fish &amp; chips", "fish--chips"),
        ('Old title <a id="old-title-adr-1"></a>', "old-title"),
    ],
    ids=[
        "code",
        "code-with-underscore",
        "only-code",
        "punctuation",
        "dash",
        "emphasis",
        "underscore-in-a-word",
        "underscore-emphasis",
        "escaped-underscore",
        "link",
        "entity",
        "explicit-anchor-inline",
    ],
)
def test_an_address_is_the_heading_s_as_the_host_renders_it(title: str, expected: str) -> None:
    assert pc.address(title) == expected


@pytest.mark.parametrize(
    "title", ["Running checks", "What's new? (v2.0)", "Step 1 — short title", "Ünïcode Größe"]
)
def test_an_address_is_the_backbone_s_slug_where_the_title_holds_no_underscore_or_markup(
    title: str,
) -> None:
    assert pc.address(title) == heading_slug(title)


def test_a_repeated_title_is_numbered_over_headings_of_every_level() -> None:
    body = "\n".join(
        ["# Example", "", "## Example", "", "### Example", "", "## Example", "", "## Other"]
    )

    assert pc.items(body) == [
        "- [Example](#example-1)",
        "- [Example](#example-3)",
        "- [Other](#other)",
    ]
    assert pc.addresses(["Example", "Example 1", "Example"]) == [
        "example",
        "example-1",
        "example-2",
    ]


def test_an_explicit_anchor_kept_for_an_old_address_changes_no_item(pages: Pages) -> None:
    pages.write(
        "guide.md",
        OPEN,
        CLOSE,
        "",
        '<a id="the-old-name"></a>',
        "",
        "## The new name",
    )

    pages.run(update=True)

    assert _list(pages.read("guide.md")) == ["- [The new name](#the-new-name)"]


# --- the check ---------------------------------------------------------------------------


def test_a_stale_list_fails_naming_its_page_and_update_writes_nothing_else(
    pages: Pages,
) -> None:
    pages.write("other.md", "No list here.", "", "## Alone")
    pages.write(
        "guide.md",
        "Lead.",
        "",
        OPEN,
        "- [Old name](#old-name)",
        CLOSE,
        "",
        "## New name",
        "",
        "Text.",
    )
    before = pages.read("guide.md")

    report = pages.run("guide.md", "other.md")

    assert [(f.path, f.line) for f in report.findings] == [("guide.md", 10)]
    assert "the contents list is stale" in report.findings[0].message
    assert "  +- [New name](#new-name)" in report.findings[0].detail
    assert pc.exit_status(report, update=False) == 1
    assert pages.read("guide.md") == before

    pages.run("guide.md", "other.md", update=True)

    fresh = before.replace("[Old name](#old-name)", "[New name](#new-name)")
    assert pages.read("guide.md") == fresh
    assert OPEN not in pages.read("other.md")


def test_a_page_without_markers_is_left_alone_and_passes(pages: Pages) -> None:
    pages.write("guide.md", "## A section")

    report = pages.run(update=True)

    assert report.findings == [] and report.lists == 0 and report.updated == []
    assert pc.render(report) == "No contents list in 1 page(s).\n"


def test_markers_quoted_in_code_are_no_markers(pages: Pages) -> None:
    pages.write(
        "guide.md",
        f"A page opts in with `{OPEN}`.",
        "",
        "```markdown",
        OPEN,
        CLOSE,
        "```",
        "",
        "## A section",
    )

    assert pages.run().lists == 0


@pytest.mark.parametrize(
    ("markers", "message", "line"),
    [
        ((OPEN,), "that no `<!-- /pkit:contents -->` closes", 8),
        ((CLOSE,), "closes no contents list", 8),
        ((CLOSE, OPEN, CLOSE), "closes no contents list", 8),
        ((OPEN, CLOSE, CLOSE), "closes no contents list", 10),
        ((OPEN, CLOSE, OPEN, CLOSE), "a second `<!-- pkit:contents -->`", 10),
    ],
    ids=["unclosed", "closing-alone", "closing-first", "second-closing", "second-list"],
)
def test_markers_that_make_no_one_pair_fail_and_update_writes_nothing(
    pages: Pages, markers: tuple[str, ...], message: str, line: int
) -> None:
    pages.write("guide.md", *markers, "", "## A section")
    before = pages.read("guide.md")

    report = pages.run(update=True)

    assert len(report.findings) == 1
    assert message in report.findings[0].message
    assert report.findings[0].line == line
    assert pc.exit_status(report, update=True) == 1
    assert pages.read("guide.md") == before


# --- which pages, and the command line ------------------------------------------------------


def test_the_pages_are_those_the_console_fences_run_reads(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo: AdopterRepo = make_adopter_repo(capabilities=("living-docs",))
    repo.write(
        {
            ".pkit/project/config.yaml": (
                "docs: {user: docs/, internal: tech-docs/}\n"
                "friction:\n"
                "  places:\n"
                "    - {path: GUIDE.md, type: living-docs:page}\n"
                "    - NOTES.md\n"
            ),
            "GUIDE.md": _page("Out of both roots."),
            "NOTES.md": _page("Declared, with no type."),
            "docs/guide.md": _page("Under the user root."),
        }
    )

    assert pc.pages(repo.root) == cf.pages(repo.root) == ["GUIDE.md", "docs/guide.md"]


def test_the_command_line_checks_the_pages_and_exits_as_it_finds(
    pages: Pages, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(pc, "pages", lambda root: ["guide.md"])
    pages.write("guide.md", OPEN, CLOSE, "", "## A section")

    assert pc.main(["NOTES.md"], root=pages.root) == 2
    assert "no artefact typed living-docs:page: NOTES.md" in capsys.readouterr().err
    assert pc.main([], root=pages.root) == 1
    assert "guide.md:8: the contents list is stale" in capsys.readouterr().out
    assert pc.main(["--update"], root=pages.root) == 0
    assert "updated guide.md" in capsys.readouterr().out
    assert pc.main(["guide.md"], root=pages.root) == 0
    assert capsys.readouterr().out == "1 contents list(s) in 1 page(s): no finding(s)\n"
