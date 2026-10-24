"""The runner of the pages' `console` fences, `scripts/console_fences.py` (#1807).

- **Which pages:** the artefacts living-docs' page type types, wherever they lie,
  as the backbone's discovery reads them; a document no place types is none.
- **Which fences:** a `console` fence, in a list item too; a fence of another
  language, and a `console` fence quoted inside one, are never run. A line before
  the first command, or no command at all, fails the fence.
- **Where a command runs:** in a copy of the scratch project, from its root, with
  a home and a temporary folder of its own and none of the caller's environment.
  A fence's commands share its copy, and no fence sees another's.
- **What is compared:** the output, with the scratch folders, the repository and
  the version written as placeholders, and `<any>` in the page matching any text
  within a line.
- **`--update`:** writes the new output, keeping the page's lines that still
  match and the output of the commands that matched, and never an output with a
  line that would read as a command or close the fence.
- **Safety:** a write in the repository fails the test and stops the run; a
  command past its time or output limit fails its fence, and so does one whose
  escaped process holds its output; what a command leaves running is stopped,
  an interrupted run included; the scratch area lies outside the repository and
  is removed after.
- **The scratch project:** built only when a fence can run, by `git init`,
  `pkit init` and a commit that is not signed; git there allows no SSH.

Each test but the page-type one runs the runner on fixture pages, with a builder
that makes an empty project, so no test installs project-kit or reaches the
network; the build itself is tested with a stand-in `pkit`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path

import pytest
from scripts import console_fences as cf

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

FENCE = "```"


def _empty_project(project: Path, env: Mapping[str, str]) -> None:
    project.mkdir(parents=True)
    (project / "seed.txt").write_text("seed\n", encoding="utf-8")


def _never_built(project: Path, env: Mapping[str, str]) -> None:
    raise AssertionError("the scratch project was built with no fence to run")


def _page(*body: str) -> str:
    return "\n".join(["---", "reader: user", "kind: guide", "---", "", "# Guide", "", *body, ""])


class Pages:
    """A repository of fixture pages, and the runner run on them."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "repo"
        self.root.mkdir()
        self.scratch = tmp_path / "scratch"
        self.scratch.mkdir()

    def write(self, path: str, *body: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_page(*body), encoding="utf-8")

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")

    def run(self, *paths: str, update: bool = False, timeout: float = 30.0) -> cf.Report:
        return cf.run_pages(
            self.root,
            paths or ("guide.md",),
            update=update,
            timeout=timeout,
            build=_empty_project,
            scratch_parent=self.scratch,
        )


@pytest.fixture
def pages(tmp_path: Path) -> Pages:
    return Pages(tmp_path)


def _messages(report: cf.Report) -> list[str]:
    return [finding.message for finding in report.findings]


# --- which fences ------------------------------------------------------------------------


def test_a_fence_s_commands_and_their_output_are_read_in_a_list_item_too() -> None:
    text = _page(
        "- Run it:",
        "",
        "  ```console",
        "  $ echo one",
        "  one",
        "",
        "  $ ls",
        "  ```",
    )

    (fence,) = cf.console_fences(text.split("\n"), "guide.md")

    assert fence.problem is None
    assert fence.indent == 2
    assert [(c.text, c.output) for c in fence.commands] == [("echo one", ("one", "")), ("ls", ())]
    assert fence.line == 10


def test_a_fence_of_another_language_and_one_quoted_inside_it_are_not_run() -> None:
    text = _page(
        "````markdown",
        "```console",
        "$ echo quoted",
        "```",
        "````",
        "",
        "```sh",
        "$ curl https://example.com",
        "```",
        "",
        "```console title=run",
        "$ echo run",
        "run",
        "```",
    )

    fences = cf.console_fences(text.split("\n"), "guide.md")

    assert [[c.text for c in fence.commands] for fence in fences] == [["echo run"]]


@pytest.mark.parametrize(
    ("body", "problem"),
    [
        (("output first", "$ echo x"), "comes before the fence's first command"),
        (("just output",), "comes before the fence's first command"),
        ((), "the fence holds no command"),
    ],
    ids=["a-line-before-the-first-command", "output-only", "empty"],
)
def test_a_fence_that_cannot_run_fails_and_nothing_is_built(
    pages: Pages, body: tuple[str, ...], problem: str
) -> None:
    pages.write("guide.md", "```console", *body, FENCE)

    report = cf.run_pages(
        pages.root, ["guide.md"], build=_never_built, scratch_parent=pages.scratch
    )

    (message,) = _messages(report)
    assert problem in message
    assert report.commands == 0
    assert cf.exit_status(report, update=False) == 1


def test_a_page_with_no_fence_passes_and_nothing_is_built(pages: Pages) -> None:
    pages.write("guide.md", "Some prose.", "", "```sh", "$ make", "```")

    report = cf.run_pages(
        pages.root, ["guide.md"], build=_never_built, scratch_parent=pages.scratch
    )

    assert (report.fences, report.findings) == (0, [])
    assert cf.render(report) == "No `console` fence in 1 page(s).\n"
    assert cf.exit_status(report, update=False) == 0


# --- where a command runs -----------------------------------------------------------------


def test_a_command_runs_in_the_scratch_project_with_a_home_and_tmp_of_its_own(
    pages: Pages, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONSOLE_FENCES_SECRET", "s3cret")
    monkeypatch.setenv("GIT_DIR", str(pages.root / ".git"))
    pages.write(
        "guide.md",
        "```console",
        "$ pwd",
        "<project>",
        "$ cat seed.txt",
        "seed",
        '$ echo "$HOME" "$TMPDIR"',
        "<home> <tmp>",
        '$ echo "${CONSOLE_FENCES_SECRET-none}" "${GIT_DIR-none}"',
        "none none",
        f"$ echo {pages.root}",
        "<repository>",
        "$ git config --global --get protocol.ssh.allow",
        "never",
        FENCE,
    )

    report = pages.run()

    assert report.findings == []
    assert report.commands == 6
    assert cf.exit_status(report, update=False) == 0


def test_a_fence_s_commands_share_its_project_and_no_fence_sees_another_s(
    pages: Pages,
) -> None:
    pages.write(
        "guide.md",
        "```console",
        "$ mkdir sub && cd sub && touch made",
        "$ pwd",
        "<project>",
        "$ ls sub",
        "made",
        FENCE,
        "",
        "```console",
        "$ ls sub 2> /dev/null || echo missing",
        "missing",
        FENCE,
    )

    report = pages.run()

    assert report.findings == []


def test_writes_in_the_scratch_home_and_tmp_pass(pages: Pages) -> None:
    pages.write("guide.md", "```console", '$ touch "$HOME/a" "$TMPDIR/b" c', FENCE)

    assert pages.run().findings == []


# --- what is compared ---------------------------------------------------------------------


def test_differing_output_fails_with_a_diff(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo one", "two", FENCE)

    report = pages.run()

    (finding,) = report.findings
    assert (finding.path, finding.line) == ("guide.md", 9)
    assert finding.message == "`echo one` printed other output than the page shows"
    assert "  -two" in finding.detail
    assert "  +one" in finding.detail
    rendered = cf.render(report)
    assert rendered.startswith("guide.md:9: `echo one` printed other output")
    assert rendered.endswith("1 command(s) run, in 1 fence(s) of 1 page(s): 1 finding(s)\n")
    assert cf.exit_status(report, update=False) == 1


def test_spaces_ending_a_line_and_blank_lines_ending_the_output_are_not_compared(
    pages: Pages,
) -> None:
    pages.write("guide.md", "```console", "$ printf 'a  \\n\\n\\n'", "a", "", FENCE)

    assert pages.run().findings == []


@pytest.mark.parametrize(
    ("expected", "actual", "matches"),
    [
        ("took <any> seconds", "took 0.25 seconds", True),
        ("took <any> seconds", "took seconds", False),
        ("<any>", "", True),
        ("a.b", "axb", False),
        ("<any>-<any>", "x-y-z", True),
    ],
)
def test_any_stands_for_any_text_within_a_line(expected: str, actual: str, matches: bool) -> None:
    assert cf.line_matches(expected, actual) is matches


def test_the_version_and_the_paths_are_written_as_placeholders(tmp_path: Path) -> None:
    replace = cf.substitutions(
        {"<project>": tmp_path / "p", "<home>": tmp_path / "p-home"}, "1.2.3"
    )

    text = f"pkit 1.2.3, not 11.2.3, 1.2.30 or 1.2.3.4, in {tmp_path}/p and {tmp_path}/p-home/x"

    assert cf.normalised(text, replace) == [
        "pkit <version>, not 11.2.3, 1.2.30 or 1.2.3.4, in <project> and <home>/x"
    ]


# --- --update -----------------------------------------------------------------------------


def test_update_writes_the_new_output_and_keeps_what_still_matches(pages: Pages) -> None:
    pages.write(
        "guide.md",
        "1. Run it:",
        "",
        "   ```console",
        "   $ echo one",
        "   old",
        "",
        "   $ printf 'a\\nb-123\\n'",
        "   a",
        "   b-<any>",
        "   c",
        "   $ echo three  ",
        "   three",
        "   ```",
        "",
        "More prose.",
    )

    report = pages.run(update=True)

    assert len(report.findings) == 2
    assert all(finding.rewritable for finding in report.findings)
    assert report.updated == ["guide.md"]
    assert cf.exit_status(report, update=True) == 0
    assert pages.read("guide.md") == _page(
        "1. Run it:",
        "",
        "   ```console",
        "   $ echo one",
        "   one",
        "",
        "   $ printf 'a\\nb-123\\n'",
        "   a",
        "   b-<any>",
        "   $ echo three  ",
        "   three",
        "   ```",
        "",
        "More prose.",
    )
    assert pages.run().findings == []


def test_update_leaves_a_page_whose_output_matches_untouched(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo same", "same", FENCE)
    before = pages.read("guide.md")

    report = pages.run(update=True)

    assert report.updated == []
    assert pages.read("guide.md") == before


@pytest.mark.parametrize(
    "printed",
    ["$ echo injected", "$", "```", "  ````  "],
    ids=["a-command", "a-bare-prompt", "a-closing-fence", "a-longer-closing-fence"],
)
def test_update_never_writes_output_that_would_read_as_markup(pages: Pages, printed: str) -> None:
    pages.write("guide.md", "```console", f"$ printf '%s\\n' '{printed}'", "old", FENCE)
    before = pages.read("guide.md")

    report = pages.run(update=True)

    (finding,) = report.findings
    assert not finding.rewritable
    assert "`--update` leaves it, since a line of it would read as a command" in finding.message
    assert report.updated == []
    assert pages.read("guide.md") == before
    assert cf.exit_status(report, update=True) == 1


def test_the_longest_run_of_matching_lines_is_kept() -> None:
    expected = ["header", "x <any>", "gone", "footer"]
    actual = ["header", "new", "x 1", "footer", "tail"]

    assert cf.updated_output(expected, actual) == ["header", "new", "x <any>", "footer", "tail"]


# --- safety -------------------------------------------------------------------------------


def test_a_write_in_the_repository_fails_and_stops_the_run(pages: Pages) -> None:
    (pages.root / "notes.txt").write_text("kept\n", encoding="utf-8")
    pages.write(
        "guide.md",
        "```console",
        f"$ touch {pages.root}/stray.txt && echo more >> {pages.root}/notes.txt",
        "$ echo never",
        "never",
        FENCE,
    )
    pages.write("later.md", "```console", "$ echo later", "later", FENCE)

    report = pages.run("guide.md", "later.md", update=True)

    (finding,) = report.findings
    assert "wrote outside the scratch project, in the repository" in finding.message
    assert finding.detail == ("  notes.txt", "  stray.txt")
    assert report.stopped
    assert report.commands == 1
    assert report.updated == []
    assert "stopped: a command wrote in the repository" in cf.render(report)
    assert cf.exit_status(report, update=True) == 1


def test_a_command_past_its_time_limit_fails_its_fence_only(pages: Pages) -> None:
    pages.write(
        "guide.md",
        "```console",
        "$ sleep 20",
        "$ echo never",
        FENCE,
        "",
        "```console",
        "$ echo next",
        "next",
        FENCE,
    )

    started = time.monotonic()
    report = pages.run(timeout=0.5)

    assert time.monotonic() - started < 10
    (message,) = _messages(report)
    assert message.startswith("`sleep 20` ran longer than 0.5 seconds")
    assert report.commands == 2
    assert not report.stopped


def _plain() -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", os.defpath)}


def test_a_command_printing_past_the_output_limit_is_stopped(tmp_path: Path) -> None:
    started = time.monotonic()
    ran = cf.run_command("yes", tmp_path, _plain(), timeout=20, limit=1000)

    assert time.monotonic() - started < 10
    assert ran.stopped == "size"
    assert len(ran.output) == 1000


def test_a_process_that_left_the_group_holding_the_output_is_left_at_the_time_limit(
    tmp_path: Path,
) -> None:
    escape = f"{sys.executable} -c 'import os, time; os.setsid(); time.sleep(3)' &"

    started = time.monotonic()
    ran = cf.run_command(escape, tmp_path, _plain(), timeout=0.5)

    assert time.monotonic() - started < 2.5
    assert ran.stopped == "time"


def test_an_interrupted_run_stops_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "marker"

    def interrupted(*_args: object, **_kwargs: object) -> list[object]:
        raise KeyboardInterrupt

    monkeypatch.setattr(cf.selectors.DefaultSelector, "select", interrupted)
    with pytest.raises(KeyboardInterrupt):
        cf.run_command(f"sleep 1; touch {marker}", tmp_path, _plain(), timeout=20)
    time.sleep(1.5)

    assert not marker.exists()


def test_what_a_command_leaves_running_is_stopped(pages: Pages, tmp_path: Path) -> None:
    late = tmp_path / "late"
    pages.write(
        "guide.md",
        "```console",
        f"$ (sleep 1; touch {late}) > /dev/null 2>&1 &",
        FENCE,
    )

    report = pages.run()
    time.sleep(1.5)

    assert report.findings == []
    assert not late.exists()


def test_the_scratch_area_lies_outside_the_repository_and_is_removed(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo x", "x", FENCE)

    with pytest.raises(cf.CannotRun, match="lies inside the repository"):
        cf.run_pages(pages.root, ["guide.md"], build=_empty_project, scratch_parent=pages.root)
    pages.run()

    assert list(pages.scratch.iterdir()) == []
    assert [path.name for path in pages.root.iterdir()] == ["guide.md"]


def test_the_listing_leaves_out_the_git_index_and_a_repository_inside(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "index").write_text("one", encoding="utf-8")
    (root / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    (root / "worktree").mkdir()
    (root / "worktree" / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    (root / "a.txt").write_text("a", encoding="utf-8")
    before = cf.listing(root)

    (root / ".git" / "index").write_text("two, refreshed", encoding="utf-8")
    (root / "worktree" / "new").write_text("another repository's", encoding="utf-8")
    unchanged = cf.changed(before, cf.listing(root))
    (root / ".git" / "HEAD").write_text("another ref", encoding="utf-8")

    assert sorted(before) == [".git", ".git/HEAD", "a.txt"]
    assert unchanged == []
    assert cf.changed(before, cf.listing(root)) == [".git/HEAD"]


# --- the scratch project --------------------------------------------------------------------


def _stand_in_pkit(bin_dir: Path, body: str) -> None:
    bin_dir.mkdir()
    pkit = bin_dir / "pkit"
    pkit.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    pkit.chmod(0o755)


def test_the_scratch_project_is_installed_and_committed_unsigned(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    _stand_in_pkit(bin_dir, 'mkdir .pkit && echo "$@" > .pkit/installed')
    scratch = cf.Scratch.made(tmp_path / "build")

    cf.build_project(scratch.project, cf.environment(scratch, tmp_path / "uv", bin_dir))

    installed = (scratch.project / ".pkit" / "installed").read_text(encoding="utf-8")
    assert installed == f"init --root {scratch.project}\n"
    log = subprocess.run(
        ["git", "log", "--format=%s %G?"],
        cwd=scratch.project,
        capture_output=True,
        text=True,
        check=True,
    )
    assert log.stdout == "Install project-kit N\n"


def test_a_scratch_project_that_cannot_be_built_names_the_step(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    _stand_in_pkit(bin_dir, "echo 'no network' >&2; exit 3")
    scratch = cf.Scratch.made(tmp_path / "build")

    with pytest.raises(cf.CannotRun) as raised:
        cf.build_project(scratch.project, cf.environment(scratch, tmp_path / "uv", bin_dir))

    assert f"`pkit init --root {scratch.project}` exited 3" in str(raised.value)
    assert "no network" in str(raised.value)


# --- which pages, and the command line ------------------------------------------------------


def test_the_pages_are_the_artefacts_of_living_docs_page_type_wherever_they_lie(
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
            "docs/kindless.md": "---\nreader: user\n---\n\n# No kind\n",
        }
    )

    assert cf.pages(repo.root) == ["GUIDE.md", "docs/guide.md"]


def test_a_path_named_that_is_no_page_stops_the_run(
    pages: Pages, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cf, "pages", lambda root: ["guide.md"])
    monkeypatch.setattr("sys.dont_write_bytecode", False)
    pages.write("guide.md", "Prose.")

    assert cf.main(["NOTES.md"], root=pages.root) == 2
    assert "no artefact typed living-docs:page: NOTES.md" in capsys.readouterr().err
    assert cf.main([], root=pages.root) == 0
    assert capsys.readouterr().out == "No `console` fence in 1 page(s).\n"
