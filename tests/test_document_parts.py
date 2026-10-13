"""Where a part of a document lies: the one reading of a Markdown body (ADR-057 point 2).

Artefact discovery cuts a collection entry's section with it, and the rule-set
reader lists a rule-set file's sections with it, so the two find the same
sections. It gives a body's headings outside fenced code, a section by its id
or its slug, and the lead (#1414).
"""

from __future__ import annotations

import pytest

from project_kit import document_parts as dp

# --- front matter and body ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("---\na: 1\n---\nbody\n", ("a: 1\n", "body\n")),
        ("---\na: 1\n---\n\n\nbody\n", ("a: 1\n", "body\n")),
        ("---\na: 1\n", (None, "---\na: 1\n")),  # never closed
        ("--- \na: 1\n---\n", ("a: 1\n", "")),  # trailing space on the opening fence
        ("----\na: 1\n---\n", (None, "----\na: 1\n---\n")),  # not a fence
        ("no front matter\n", (None, "no front matter\n")),
        # Line endings are read universally: both parts come back with `\n`.
        ("---\r\na: 1\r\n---\r\nbody\r\n", ("a: 1\n", "body\n")),
        ("---\r\nb: |\r\n  two\r\n  lines\r\n---\r\n", ("b: |\n  two\n  lines\n", "")),
        ("--- \r\na: 1\r\n---\t\r\n\r\n\r\nbody\r\n", ("a: 1\n", "body\n")),
        ("---\ra: 1\r---\rbody\r", ("a: 1\n", "body\n")),  # a lone `\r`
        ("no front matter\r\n", (None, "no front matter\n")),
    ],
)
def test_split_front_matter(text: str, expected: tuple[str | None, str]) -> None:
    assert dp.split_front_matter(text) == expected


@pytest.mark.parametrize(
    ("text", "front_matter", "reason"),
    [
        (
            "---\nid: X\ndate: 2026-10-13\n6: [7]\n---\nbody\n",
            {"id": "X", "date": "2026-10-13", "6": [7]},
            None,
        ),
        ("---\n- a list\n---\nbody\n", None, None),  # front matter that is no mapping
        ("no front matter\n", None, None),
        ("---\nid: [unclosed\n---\nbody\n", None, "line 2"),
    ],
)
def test_front_matter_is_parsed_as_written(
    text: str, front_matter: dict[str, object] | None, reason: str | None
) -> None:
    """Dates and keys come back as written; a parse failure names where it failed."""
    parsed, body, why = dp.parse_front_matter(text)
    assert parsed == front_matter
    assert body == dp.split_front_matter(text)[1]
    assert (why is None) == (reason is None)
    if reason is not None:
        assert why is not None and reason in why


def test_the_body_opens_on_the_line_after_its_front_matter_and_the_blank_lines() -> None:
    text = "---\na: 1\n---\n\n\nbody\n"
    _front, body = dp.split_front_matter(text)
    assert dp.body_first_line(text, body) == 6
    crlf = text.replace("\n", "\r\n")
    assert dp.body_first_line(crlf, dp.split_front_matter(crlf)[1]) == 6


# --- headings outside fenced code ---------------------------------------------------------


def test_body_headings_skip_fenced_code_to_its_own_closing_marker() -> None:
    """Tildes do not close a backtick fence, and a fence never closed runs to the end."""
    body = "# One\n```\n~~~\n# not a heading\n```\n## Two ##\n   ~~~\n# not a heading either\n"
    assert dp.body_headings(body) == (
        dp.Heading(level=1, title="One", start=0),
        dp.Heading(level=2, title="Two", start=body.index("## Two")),
    )


def test_the_lines_outside_fenced_code_leave_out_the_fence_and_what_it_holds() -> None:
    body = "one\n```sh\n# install\n```\ntwo\n"
    assert [line.text for line in dp.Body.read(body).lines()] == ["one", "two", ""]
    assert [line.start for line in dp.Body.read(body).lines()][:2] == [0, body.index("two")]


# --- a section by its id ------------------------------------------------------------------


def test_entry_section_runs_to_the_next_heading_of_equal_or_higher_level() -> None:
    body = "# Set\n\n## RS-1: One\n\ntext\n\n### RS-1 detail\n\nmore\n\n## RS-10 — Ten\n\nten\n"
    assert dp.entry_section(body, "RS-1") == "## RS-1: One\n\ntext\n\n### RS-1 detail\n\nmore\n"
    assert dp.entry_section(body, "RS-10") == "## RS-10 — Ten\n\nten\n"
    assert dp.entry_section(body, "RS-2") == ""


def test_entry_section_takes_the_id_as_a_whole_token() -> None:
    """Two hyphenated ids sharing a prefix: the shorter one's section is never the longer's,
    whichever comes first."""
    body = (
        "## uc-login-sso — Sign in with SSO\n\nsso\n\n"
        "## uc-login.v2 — Sign in, again\n\nagain\n\n"
        "## uc-login — Sign in\n\nlogin\n\n"
        "## uc-login: the details\n\ndetails\n"
    )
    assert dp.entry_section(body, "uc-login") == "## uc-login — Sign in\n\nlogin\n"
    assert dp.entry_section(body, "uc-login-sso") == "## uc-login-sso — Sign in with SSO\n\nsso\n"
    assert dp.entry_section(body, "uc-login.v2") == "## uc-login.v2 — Sign in, again\n\nagain\n"
    assert dp.entry_section(body, "uc-log") == ""
    # Punctuation that continues no id ends it, as the end of the heading does.
    assert dp.entry_section("## uc-login: Sign in\n\ntext\n", "uc-login") == (
        "## uc-login: Sign in\n\ntext\n"
    )
    assert dp.entry_section("## uc-login.\n\ntext\n", "uc-login") == "## uc-login.\n\ntext\n"


def test_entry_section_skips_headings_in_fenced_code() -> None:
    """A heading inside fenced code opens no section and ends none (#1372)."""
    login = (
        "## uc-login — Sign in\n\n"
        "```sh\n# install the client\nmake client\n```\n\n"
        "~~~markdown\n## uc-logout — an example, not an entry\n~~~\n\n"
        "still signing in\n"
    )
    body = f"{login}\n## uc-signup — Sign up\n\nsignup\n"
    assert dp.entry_section(body, "uc-login") == login
    assert dp.entry_section(body, "uc-logout") == ""


def test_a_section_s_span_covers_exactly_its_text() -> None:
    """The span and the text come from one extent, so a reader of the span reads
    exactly the text that is compared; the line breaks ending it are left out."""
    text = "---\nid: x\n---\n\n## A\n\nfirst\n\n\n## B\n\nsecond"
    _front, body = dp.split_front_matter(text)
    read = dp.Body.read(body)
    lines = text.split("\n")
    for part_id, expected in (("A", "## A\n\nfirst\n"), ("B", "## B\n\nsecond\n")):
        extent = read.section_by_id(part_id)
        assert extent is not None and read.text_of(extent) == expected
        span = read.span_of(extent, dp.body_first_line(text, body))
        assert span is not None
        assert "\n".join(lines[span.first_line - 1 : span.last_line]) + "\n" == expected


# --- a section by its slug ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Authoring commands", "authoring-commands"),
        ("`friction check [--base <ref>]`", "friction-check---base-ref"),
        ("What a point stands on, and why", "what-a-point-stands-on-and-why"),
        ("Ids: 1.2 and D3 — kept", "ids-12-and-d3--kept"),
        ("Schéma über alles", "schéma-über-alles"),
        ("Two  spaces", "two--spaces"),
        ("--- ???", "----"),
        ("!!!", ""),
    ],
)
def test_a_heading_s_slug(title: str, slug: str) -> None:
    """Lower case; letters, digits, spaces and hyphens kept; each space a hyphen."""
    assert dp.heading_slug(title) == slug


def test_a_slug_finds_every_section_whose_heading_has_it() -> None:
    body = (
        "# Page\n\nlead\n\n## Authoring commands\n\none\n\n### Detail\n\ndeep\n\n"
        "## Other\n\n```\n## Authoring commands\n```\n\n## authoring Commands!\n\ntwo\n"
    )
    read = dp.Body.read(body)
    found = read.sections_by_slug("authoring-commands")
    # The fenced heading is no heading; the two others share one slug, which the caller judges.
    assert [read.text_of(extent) for extent in found] == [
        "## Authoring commands\n\none\n\n### Detail\n\ndeep\n",
        "## authoring Commands!\n\ntwo\n",
    ]
    assert read.sections_by_slug("detail")[0].heading == read.headings[2]
    assert read.sections_by_slug("missing") == ()
    assert read.sections_by_slug("") == ()  # an empty slug names no heading


# --- the lead -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "lead"),
    [
        # A first-level heading that opens the body is part of the lead.
        ("# Title\n\nWhat it is.\n\n## Section\n\ntext\n", "# Title\n\nWhat it is.\n"),
        # A body without a title has a lead too.
        ("What it is.\n\n## Section\n\ntext\n", "What it is.\n"),
        ("\n\nWhat it is.\n\n\n## Section\n", "What it is.\n"),
        # A body that opens with any other heading has an empty lead.
        ("## Section\n\ntext\n", ""),
        # A first-level heading after text does not open the body: the lead ends there.
        ("intro\n\n# Title\n\ntext\n", "intro\n"),
        # A heading in fenced code ends nothing.
        ("# Title\n\n```\n## not a section\n```\n", "# Title\n\n```\n## not a section\n```\n"),
        ("only text, no heading", "only text, no heading\n"),
        ("", ""),
    ],
)
def test_the_lead_is_the_body_before_its_first_heading(body: str, lead: str) -> None:
    read = dp.Body.read(body)
    extent = read.lead()
    assert extent.heading is None
    assert read.text_of(extent) == lead
    assert (read.span_of(extent, 1) is None) == (lead == "")


def test_the_lead_s_span_counts_the_file_s_lines() -> None:
    text = "---\nid: page\n---\n# Page\n\nIt says this.\n\n## More\n"
    _front, body = dp.split_front_matter(text)
    read = dp.Body.read(body)
    assert read.span_of(read.lead(), dp.body_first_line(text, body)) == dp.SectionSpan(4, 6)
