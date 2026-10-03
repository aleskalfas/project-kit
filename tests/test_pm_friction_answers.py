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
    document = _document(
        _entry(
            "docs/install.md", "unchanged", "The flag rename leaves the install steps as written."
        ),
        _entry(
            "docs/cli.md",
            "deferred",
            "Rewritten with the redesign.",
            anchor=("path", "src/cli/**"),
            asked=False,
        ),
        _entry("docs/api.md", "updated", None, status="bump"),
        _entry("docs/faq.md", None, "Reworded.", status="edited", asked=False),
        _entry("docs/new.md", "unanchored", "A rule of the method.", asked=False, new=True),
        _entry(
            "docs/guide.md",
            "unchanged",
            "The guide holds.",
            kept=[(("record", "DEC-1"), "Waiting on the record."), (("path", "x/**"), None)],
        ),
    )
    assert fa.render(document, HEAD) == "\n".join(
        [
            "## Friction answers",
            "",
            f"<!-- pkit-friction-answers:start head={HEAD} base={MERGE_BASE} -->",
            "6 answers written by this change, as of `1a2b3c4` — the change check's list "
            "(`pkit friction check`). Each is on its artefact.",
            "",
            "1. `docs/install.md` — **unchanged**: "
            "``The flag rename leaves the install steps as written.``",
            "2. `docs/cli.md` — **deferred** `path:src/cli/**` — not asked for by the change "
            "check: ``Rewritten with the redesign.``",
            "3. `docs/api.md` — **updated** — the diff does not bear it out",
            "4. `docs/faq.md` — **no outcome** — not asked for by the change check; edited "
            "without a revalidation: ``Reworded.``",
            "5. `docs/new.md` — **unanchored** — a new artefact; not asked for by the change "
            "check: ``A rule of the method.``",
            "6. `docs/guide.md` — **unchanged**: ``The guide holds.``",
            "   - keeps the deferral of `record:DEC-1`: ``Waiting on the record.``",
            "   - keeps the deferral of `path:x/**`",
            "<!-- pkit-friction-answers:end -->",
        ]
    )


def test_a_change_that_wrote_no_answers_has_no_section(fa: ModuleType) -> None:
    assert fa.render(_document(), HEAD) is None
    assert fa.lines(_document()) == []


def test_files_the_check_could_not_read_are_counted_on_the_first_line(fa: ModuleType) -> None:
    one = fa.render(_document(_entry("a.md", "updated"), unreadable=["b.md"]), HEAD)
    assert one is not None and "1 file the check could not read is not listed." in one
    two = fa.render(_document(_entry("a.md", "updated"), unreadable=["b.md", "c.md"]), HEAD)
    assert two is not None and "2 files the check could not read are not listed." in two


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
        "1. docs/a\\u200b.md — unchanged: fine\\x1b[1A\\x1b[2Kgone \\u202eesrever\\nnext"
    ]


def test_a_reason_with_backticks_sits_in_a_longer_code_span(fa: ModuleType) -> None:
    section = fa.render(_document(_entry("a.md", "unchanged", "the ``flag`` is `x`")), HEAD)
    # Ending on a backtick, the words are padded on both sides; CommonMark drops the pads.
    assert section is not None and ": ``` the ``flag`` is `x` ```" in section
    section = fa.render(_document(_entry("a.md", "unchanged", "plain")), HEAD)
    assert section is not None and ": ``plain``" in section


def test_the_terminal_list_carries_every_word_and_mark(fa: ModuleType) -> None:
    document = _document(
        _entry("docs/install.md", "unchanged", "Holds."),
        _entry("docs/cli.md", "deferred", "Later.", anchor=("path", "src/**"), asked=False),
        _entry("docs/g.md", "unchanged", "Holds.", kept=[(("path", "x/**"), "Kept.")]),
    )
    assert fa.lines(document) == [
        "1. docs/install.md — unchanged: Holds.",
        "2. docs/cli.md — deferred path:src/** — not asked for by the change check: Later.",
        "3. docs/g.md — unchanged: Holds.",
        "   keeps the deferral of path:x/**: Kept.",
    ]


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
    orphan = f"{BODY}\n## Friction answers\n\n{fa.MARKER_START} head=x base=y -->\nleft\n"
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
    assert stamped.index("## Friction answers") > stamped.index("as a line.")


HAND = (
    "## Friction answers\n\n"
    "An agent's own list:\n\n"
    "```\n"
    "## not a heading, inside a fence\n"
    "1. docs/a.md — unchanged: fixes #9\n"
    "```\n"
)


def test_a_section_no_command_wrote_is_stripped_whole(fa: ModuleType) -> None:
    """An unmarked `## Friction answers` — a list typed by hand — is stripped up to
    the next heading of level one or two outside a fenced block, or the footer."""
    body = f"Closes #42\n\n## Summary\n\nDone.\n\n{HAND}\n## Doc impact\n\nThe README.\n"
    assert fa.hand_written(body) and not fa.has_list(body)
    assert fa.strip(body) == BODY
    assert not fa.current(body, None)
    last = f"{BODY}\n{HAND}\n{FOOTER}\n"
    assert fa.strip(last) == f"{BODY}\n{FOOTER}\n"
    section = _section(fa, _entry("a.md", "unchanged", "Holds."))
    assert fa.stamp(last, section) == f"{BODY}\n{section}\n\n{FOOTER}\n"
    assert not fa.current(f"{last}\n{section}\n", section)


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
        f"No answer written by this change, as of `{head[:7]}`, in the change check's list "
        "(`pkit friction check`); it is dormant at that head.",
        "",
        fa.SETTINGS_LEAD,
        "",
        f"- {fa.PLACES}: `docs` → none",
        fa.MARKER_END,
    ]
    assert fa.lines(found.document, found.settings) == [f"{fa.PLACES}: docs → none"]


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


def test_a_setting_is_read_for_closing_references_and_delimiters(fa: ModuleType) -> None:
    settings = [fa.Setting(fa.PLACES, (), ("fixes #5/**",))]
    assert fa.closing_reference(_document(), settings) == (fa.SETTINGS_WHERE, "fixes #5")
    settings = [fa.Setting(fa.PLACES, ("<!--/**",), ())]
    assert fa.comment_delimiter(_document(), settings) == (fa.SETTINGS_WHERE, "<!--")
