"""The doc-examples run, `.pkit/capabilities/doc-examples/scripts/run-examples.py`
(#2098; doc-examples DEC-001). It grew from project-kit's own runner (#1807, #2017).

- **Which fences (point 2):** a `console` fence, in a list item or a block quote
  too; a fence of another language, and one quoted inside it, are never run; a
  fence under another name for a shell session is reported and fails nothing. A
  line before the first command, or no command, fails the fence.
- **How commands run (point 2):** in order, in one shell for the fence, from the
  scratch project's root, so a `cd` or a variable carries over; standard output
  and error reach one pipe, in order; the exit status is not compared.
- **The scratch project (point 4):** the setup step builds it once, in an empty
  folder with a home of its own and the repository's path given; each fence
  starts from it as the setup left it, at the same paths, with an empty
  temporary folder. A setup step that fails, or writes in the repository, stops
  the run. With no fence to run, no setup runs.
- **The environment (point 4):** the caller's `PATH` behind the project's
  folders, the project's variables, its values naming the run's folders, the
  caller's value of a variable named with none, the settings the run fixes, and
  nothing else of the caller's. A caller's value is written as its placeholder.
- **Placeholders (point 5):** the run's folders, `<any>`, and the project's own,
  each the one line its command prints, matched where it stands whole; the
  longest text first. A placeholder's command that fails, or prints no line or
  two, stops the run.
- **An update (point 7):** writes the new output, keeping what still matches, in
  the fence's quote and indent; never output that reads as a command, closes the
  fence or holds `<any>`; no page when a command wrote in the repository, and not
  a page that changed while the run read it.
- **The guards (point 8):** a write in the repository fails the test and stops the
  run, one in its git directory does neither; a command past its time or output
  limit fails its fence; what a command leaves running is stopped, an interrupted
  run included; the scratch area lies outside the repository and is removed.
- **The selection and the command line (points 3 and 10):** the pages document
  the CLI answers is read, and one of another shape stops the run; a page named
  that is no page stops it; exit 0, 1 and 2.

Every test runs the run on fixture pages with a setup step that needs no network.
The run's program is loaded by its path under a name of its own.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".pkit" / "capabilities" / "doc-examples" / "scripts" / "run-examples.py"
FENCE = "```"


def _load() -> ModuleType:
    name = "doc_examples_run_under_test"
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run: Any = _load()


def _page(*body: str) -> str:
    return "\n".join(["---", "reader: user", "kind: guide", "---", "", "# Guide", "", *body, ""])


SEED = ("printf 'seed\\n' > seed.txt",)


class Pages:
    """A repository of fixture pages, and the run run on them."""

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

    def selection(self, *paths: str, **config: Any) -> Any:
        config.setdefault("setup", SEED)
        return run.Selection(self.root, paths or ("guide.md",), **config)

    def run(
        self,
        *paths: str,
        update: bool = False,
        timeout: float = 30.0,
        caller: Mapping[str, str] | None = None,
        **config: Any,
    ) -> Any:
        return run.run_pages(
            self.selection(*paths, **config),
            update=update,
            limits=run.Limits(timeout, 30.0),
            scratch_parent=self.scratch,
            caller={"PATH": os.environ.get("PATH", os.defpath)} if caller is None else caller,
        )


@pytest.fixture
def pages(tmp_path: Path) -> Pages:
    return Pages(tmp_path)


def _messages(report: Any) -> list[str]:
    return [finding.message for finding in report.findings]


NEVER_SET_UP = ("echo 'the setup ran with no fence to run'; exit 7",)


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

    (fence,) = run.console_fences(text.split("\n"), "guide.md")

    assert fence.problem is None
    assert fence.indent == 2
    assert [(c.text, c.output) for c in fence.commands] == [("echo one", ("one", "")), ("ls", ())]
    assert fence.line == 10


def test_a_fence_opened_on_a_list_item_s_marker_and_one_in_a_block_quote_are_read() -> None:
    text = _page(
        "1. ```console",
        "   $ echo listed",
        "   listed",
        "   ```",
        "",
        "> A quote:",
        ">",
        "> ```console",
        "> $ echo quoted",
        ">   quoted",
        "> ```",
        "",
        "> ```console",
        "> $ echo cut",
        "Out of the quote, which ends the fence.",
    )

    listed, quoted, cut = run.console_fences(text.split("\n"), "guide.md")

    assert (listed.indent, listed.quote) == (3, "")
    assert [(c.text, c.output) for c in listed.commands] == [("echo listed", ("listed",))]
    assert quoted.quote == "> "
    assert [(c.text, c.output) for c in quoted.commands] == [("echo quoted", ("  quoted",))]
    assert [c.text for c in cut.commands] == ["echo cut"]
    assert cut.end == 21


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

    fences = run.console_fences(text.split("\n"), "guide.md")

    assert [[c.text for c in fence.commands] for fence in fences] == [["echo run"]]


def test_a_fence_under_another_name_for_a_shell_session_is_reported_and_fails_nothing(
    pages: Pages,
) -> None:
    pages.write("guide.md", "```shell-session", "$ echo never", "never", FENCE)

    report = pages.run(setup=NEVER_SET_UP)

    (note,) = report.notes
    assert (note.line, report.findings, report.commands) == (8, [], 0)
    assert "a `shell-session` fence is a shell session no run checks" in note.message
    assert run.render(report).startswith("guide.md:8: a `shell-session` fence")
    assert run.exit_status(report, update=False) == 0


@pytest.mark.parametrize(
    ("body", "problem"),
    [
        (("output first", "$ echo x"), "comes before the fence's first command"),
        (("just output",), "comes before the fence's first command"),
        ((), "the fence holds no command"),
    ],
    ids=["a-line-before-the-first-command", "output-only", "empty"],
)
def test_a_fence_that_cannot_run_fails_and_no_setup_runs(
    pages: Pages, body: tuple[str, ...], problem: str
) -> None:
    pages.write("guide.md", "```console", *body, FENCE)

    report = pages.run(setup=NEVER_SET_UP)

    (message,) = _messages(report)
    assert problem in message
    assert report.commands == 0
    assert run.exit_status(report, update=False) == 1


def test_a_page_with_no_fence_passes_and_no_setup_runs(pages: Pages) -> None:
    pages.write("guide.md", "Some prose.", "", "```sh", "$ make", "```")

    report = pages.run(setup=NEVER_SET_UP)

    assert (report.fences, report.findings) == (0, [])
    assert run.render(report) == "No `console` fence in 1 page(s).\n"
    assert run.exit_status(report, update=False) == 0


# --- how commands run ---------------------------------------------------------------------


def test_a_command_runs_in_the_scratch_project_with_a_home_and_tmp_of_its_own(
    pages: Pages,
) -> None:
    pages.write(
        "guide.md",
        "```console",
        "$ pwd",
        "<project>",
        "$ cat seed.txt",
        "seed",
        '$ echo "$HOME" "$TMPDIR"',
        "<home> <tmp>",
        '$ echo "${DOC_EXAMPLES_SECRET-none}" "${GIT_DIR-none}"',
        "none none",
        f"$ echo {pages.root}",
        "<repository>",
        FENCE,
    )
    caller = {
        "PATH": os.environ.get("PATH", os.defpath),
        "DOC_EXAMPLES_SECRET": "s3cret",
        "GIT_DIR": str(pages.root / ".git"),
    }

    report = pages.run(caller=caller)

    assert report.findings == []
    assert report.commands == 5
    assert run.exit_status(report, update=False) == 0


def test_a_fence_s_commands_run_in_one_shell_and_no_fence_sees_another_s(
    pages: Pages,
) -> None:
    pages.write(
        "guide.md",
        "```console",
        "$ mkdir sub && cd sub && touch made && WHERE=sub",
        "$ pwd",
        "<project>/sub",
        '$ echo "$WHERE"',
        "sub",
        FENCE,
        "",
        "```console",
        "$ pwd",
        "<project>",
        "$ ls sub 2> /dev/null || echo missing",
        "missing",
        '$ echo "${WHERE-unset}"',
        "unset",
        FENCE,
    )

    assert pages.run().findings == []


def test_output_and_errors_reach_one_pipe_in_order_and_the_status_is_not_compared(
    pages: Pages,
) -> None:
    pages.write(
        "guide.md",
        "```console",
        "$ echo out; echo err >&2; printf 'no newline'",
        "out",
        "err",
        "no newline",
        "$ false",
        '$ read line; echo "read: [$line]"',
        "read: []",
        FENCE,
    )

    assert pages.run().findings == []


def test_a_command_that_ends_the_shell_fails_the_fence_s_later_commands(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo bye; exit 3", "bye", "$ echo never", FENCE)

    report = pages.run()

    (message,) = _messages(report)
    assert (
        message
        == "`echo bye; exit 3` ended the fence's shell; the fence's later commands did not run"
    )
    assert report.commands == 1


def test_writes_in_the_scratch_home_and_tmp_pass(pages: Pages) -> None:
    pages.write("guide.md", "```console", '$ touch "$HOME/a" "$TMPDIR/b" c', FENCE)

    assert pages.run().findings == []


# --- the scratch project ----------------------------------------------------------------


def test_the_setup_step_runs_once_in_one_shell_given_the_repository_s_path(
    pages: Pages,
) -> None:
    setup = (
        "mkdir -p tools && cd tools",
        'echo "$DOC_EXAMPLES_REPOSITORY" > repository.txt',
        "echo run >> ../../setup-runs",
        'echo "$PWD" > built-in.txt',
        "printf 'home\\n' > \"$HOME/.made\"",
    )
    pages.write(
        "guide.md",
        "```console",
        "$ cat tools/repository.txt tools/built-in.txt ../setup-runs ~/.made",
        "<repository>",
        "<project>/tools",
        "run",
        "home",
        "$ rm tools/built-in.txt ~/.made",
        FENCE,
        "",
        "```console",
        "$ ls tools ~/.made",
        "<home>/.made",
        "",
        "tools:",
        "built-in.txt",
        "repository.txt",
        '$ echo "${DOC_EXAMPLES_REPOSITORY-not given}"',
        "not given",
        FENCE,
    )

    assert pages.run(setup=setup).findings == []


def test_a_setup_step_that_fails_stops_the_run_naming_its_command(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo x", "x", FENCE)

    with pytest.raises(run.CannotRun) as raised:
        pages.run(setup=("echo fine", "echo 'no network' >&2; exit 3", "echo never"))

    message = str(raised.value)
    assert message.startswith("the setup step's command `echo 'no network' >&2; exit 3` exited 3")
    assert "no network" in message
    assert list(pages.scratch.iterdir()) == []


def test_a_setup_step_that_writes_in_the_repository_stops_the_run(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo x", "x", FENCE)

    with pytest.raises(run.CannotRun, match=r"wrote in the repository:\n  stray\.txt"):
        pages.run(setup=(f"touch {pages.root}/stray.txt",))


# --- the environment ---------------------------------------------------------------------


def test_the_environment_holds_the_project_s_folders_variables_and_the_fixed_settings(
    pages: Pages,
) -> None:
    pages.write(
        "guide.md",
        "```console",
        '$ echo "$PATH"',
        "<project>/bin:/usr/bin:/bin",
        '$ echo "$CACHE" "$FROM_CALLER" "${UNSET_IN_CALLER-unset}" "$LANG" "$TERM" "$NO_COLOR"',
        "<scratch>/cache <FROM_CALLER> unset C dumb 1",
        "$ tool",
        "the project's tool",
        FENCE,
    )
    setup = (
        "mkdir bin",
        "printf '#!/bin/sh\\necho \"the project'\\''s tool\"\\n' > bin/tool",
        "chmod +x bin/tool",
    )

    report = pages.run(
        setup=setup,
        path=("<project>/bin",),
        environment={
            "CACHE": "<scratch>/cache",
            "FROM_CALLER": None,
            "UNSET_IN_CALLER": None,
            "LANG": "en_US.UTF-8",
        },
        caller={"PATH": "/usr/bin:/bin", "FROM_CALLER": "caller", "LANG": "de_DE"},
    )

    assert report.findings == []


def test_a_value_taken_from_the_caller_is_written_as_its_placeholder(pages: Pages) -> None:
    pages.write("guide.md", "```console", '$ echo "token: $gh_token"', "old", FENCE)

    report = pages.run(
        update=True,
        environment={"gh_token": None},
        caller={"PATH": os.environ.get("PATH", os.defpath), "gh_token": "ghp_secret"},
    )

    assert run.exit_status(report, update=True) == 0
    assert "ghp_secret" not in pages.read("guide.md")
    assert "token: <GH_TOKEN>" in pages.read("guide.md")


@pytest.mark.parametrize(
    "printed",
    ["prefix_ghp_secret", "ghp_secret1", "\\nghp_secret"],
    ids=["after-a-word", "before-a-digit", "after-an-escape"],
)
def test_a_value_taken_from_the_caller_is_never_written_where_it_stands_in_a_word(
    pages: Pages, printed: str
) -> None:
    pages.write("guide.md", "```console", f"$ printf '%s\\n' '{printed}'", "old", FENCE)
    before = pages.read("guide.md")

    report = pages.run(
        update=True,
        environment={"gh_token": None},
        caller={"PATH": os.environ.get("PATH", os.defpath), "gh_token": "ghp_secret"},
    )

    (finding,) = report.findings
    assert not finding.rewritable
    assert finding.message.endswith("since a line of it holds a value a variable takes from you")
    assert not any("ghp_secret" in row for row in finding.detail)
    assert pages.read("guide.md") == before


def test_a_failing_setup_step_s_output_shows_a_caller_s_value_masked(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo x", "x", FENCE)

    with pytest.raises(run.CannotRun) as raised:
        pages.run(
            setup=('echo "token=$gh_token"; exit 1',),
            environment={"gh_token": None},
            caller={"PATH": os.environ.get("PATH", os.defpath), "gh_token": "ghp_secret"},
        )

    assert "token=<GH_TOKEN>" in str(raised.value)
    assert "ghp_secret" not in str(raised.value)


# --- what is compared ---------------------------------------------------------------------


def test_differing_output_fails_with_a_diff(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo one", "two", FENCE)

    report = pages.run()

    (finding,) = report.findings
    assert (finding.path, finding.line) == ("guide.md", 9)
    assert finding.message == "`echo one` printed other output than the page shows"
    assert "  -two" in finding.detail
    assert "  +one" in finding.detail
    rendered = run.render(report)
    assert rendered.startswith("guide.md:9: `echo one` printed other output")
    assert rendered.endswith("1 command(s) run, in 1 fence(s) of 1 page(s): 1 finding(s)\n")
    assert run.exit_status(report, update=False) == 1


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
    assert run.line_matches(expected, actual) is matches


def test_the_project_s_placeholder_stands_for_the_line_its_command_prints(
    pages: Pages,
) -> None:
    pages.write(
        "guide.md",
        "```console",
        "$ cat VERSION",
        "<VERSION>",
        "$ echo v1.2.3 1.2.30 11.2.3 1.2.3.4 x1.2.3",
        "v<VERSION> 1.2.30 11.2.3 1.2.3.4 x<VERSION>",
        FENCE,
    )

    report = pages.run(setup=("echo 1.2.3 > VERSION",), placeholders={"VERSION": "cat VERSION"})

    assert report.findings == []


@pytest.mark.parametrize(
    ("text", "line", "replaced"),
    [
        ("1.2.3", "pkit 1.2.3, v1.2.3, (1.2.3)", "pkit <X>, v<X>, (<X>)"),
        ("1.2.3", "11.2.3 1.2.30 1.2.3.4 0.1.2.3", "11.2.3 1.2.30 1.2.3.4 0.1.2.3"),
        ("1.2.3", "1.2.3. Done, 1.2.3a1", "<X>. Done, <X>a1"),
        ("acme", "acme acme-cli acme_cli acmes 2acme", "<X> <X>-cli acme_cli acmes 2acme"),
        ("1", "1 of 10, 21, 1.5, v1", "<X> of 10, 21, 1.5, v<X>"),
        ("@corp", "me@corp.example @corps", "me<X>.example @corps"),
    ],
)
def test_a_project_s_text_is_replaced_only_where_it_stands_whole(
    text: str, line: str, replaced: str
) -> None:
    assert run.substitutions({}, {"<X>": text}).apply(line) == replaced


def test_the_longest_text_is_replaced_first_and_never_inside_a_longer_one(
    tmp_path: Path,
) -> None:
    replace = run.substitutions(
        {"<project>": tmp_path / "p", "<home>": tmp_path / "p-home"},
        {"<NAME>": "p", "<OTHER>": "project"},
    )

    text = f"{tmp_path}/p and {tmp_path}/p-home/x, p project"

    assert run.normalised(text, replace) == ["<project> and <home>/x, <NAME> <OTHER>"]


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("exit 4", "exited 4"),
        ("printf ''", "printed no text"),
        ("printf 'a\\nb\\n'", "printed more than one line"),
        ('echo x > "$DOC_EXAMPLES_REPOSITORY/stray.txt"', "wrote in the repository"),
    ],
)
def test_a_placeholder_s_command_that_fails_stops_the_run(
    pages: Pages, command: str, message: str
) -> None:
    pages.write("guide.md", "```console", "$ echo x", "x", FENCE)

    with pytest.raises(run.CannotRun) as raised:
        pages.run(placeholders={"VERSION": command})

    assert f"the command of the placeholder `<VERSION>`, `{command}`, {message}" in str(
        raised.value
    )


# --- an update ----------------------------------------------------------------------------


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
    assert run.exit_status(report, update=True) == 0
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


def test_update_writes_in_the_fence_s_block_quote(pages: Pages) -> None:
    pages.write("guide.md", "> ```console", "> $ printf 'a\\n\\nb\\n'", "> old", ">", "> ```")

    report = pages.run(update=True)

    assert report.updated == ["guide.md"]
    assert pages.read("guide.md") == _page(
        "> ```console", "> $ printf 'a\\n\\nb\\n'", "> a", ">", "> b", ">", "> ```"
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
    assert run.exit_status(report, update=True) == 1


@pytest.mark.parametrize(
    "printed",
    ["about tool\\r$ echo injected", "\\033[31mred\\033[0m", "a\\0b"],
    ids=["a-carriage-return", "a-terminal-escape", "a-nul"],
)
def test_update_never_writes_output_that_holds_a_control_character(
    pages: Pages, printed: str
) -> None:
    pages.write("guide.md", "```console", f"$ printf '{printed}\\n'", "old", FENCE)
    before = pages.read("guide.md")

    report = pages.run(update=True)

    (finding,) = report.findings
    assert not finding.rewritable
    assert finding.message.endswith(
        "since a line of it holds a control character, which could end a line or hide text"
    )
    assert not any(run.CONTROL.search(row) for row in finding.detail)
    assert pages.read("guide.md") == before
    assert len(run.console_fences(before.split("\n"), "guide.md")[0].commands) == 1


def test_update_never_writes_output_that_holds_the_wildcard_text(pages: Pages) -> None:
    pages.write("guide.md", "```console", "$ echo 'took <any> seconds'", "old", FENCE)
    before = pages.read("guide.md")

    report = pages.run(update=True)

    (finding,) = report.findings
    assert not finding.rewritable
    assert finding.message.endswith(
        "; `--update` leaves it, since a line of it holds `<any>`, "
        "which the next run would read as any text"
    )
    assert report.updated == []
    assert pages.read("guide.md") == before
    assert run.exit_status(report, update=True) == 1


def test_update_writes_no_page_when_a_later_command_wrote_in_the_repository(
    pages: Pages,
) -> None:
    pages.write("first.md", "```console", "$ echo new", "old", FENCE)
    pages.write("later.md", "```console", f"$ touch {pages.root}/stray.txt", FENCE)
    before = pages.read("first.md")

    report = pages.run("first.md", "later.md", update=True)

    assert report.stopped
    assert [finding.path for finding in report.findings] == ["first.md", "later.md"]
    assert report.findings[0].rewritable
    assert report.updated == []
    assert pages.read("first.md") == before
    assert "no page was updated" in run.render(report)
    assert run.exit_status(report, update=True) == 1


def test_a_write_in_the_repository_after_the_last_command_stops_the_run(
    pages: Pages, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages.write("guide.md", "```console", "$ echo new", "old", FENCE)
    removed = run._remove

    def edited_meanwhile(path: Path) -> None:
        removed(path)
        if path.parent == pages.scratch:
            (pages.root / "guide.md").write_text("edited meanwhile\n", encoding="utf-8")

    monkeypatch.setattr(run, "_remove", edited_meanwhile)

    report = pages.run(update=True)

    assert report.stopped
    assert report.updated == []
    assert pages.read("guide.md") == "edited meanwhile\n"
    finding = report.findings[-1]
    assert finding.message.startswith(
        "a process the run left wrote in the repository after its last command"
    )
    assert finding.detail == ("  guide.md",)
    assert run.exit_status(report, update=True) == 1


def test_a_write_by_a_process_a_fence_left_stops_the_run(pages: Pages, tmp_path: Path) -> None:
    pages.write(
        "guide.md",
        "```console",
        f"$ (sleep 0.3; touch {pages.root}/late.txt) > /dev/null 2>&1 &",
        "$ sleep 1",
        FENCE,
        "",
        "```console",
        "$ echo never",
        "never",
        FENCE,
    )

    report = pages.run()

    (finding,) = report.findings
    assert finding.message.startswith("`sleep 1` wrote outside the scratch project")
    assert finding.detail == ("  late.txt",)
    assert report.commands == 2


def test_update_does_not_write_a_page_that_changed_while_the_run_read_it(
    pages: Pages, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages.write("guide.md", "```console", "$ echo new", "old", FENCE)
    before = pages.read("guide.md")
    read = run.read_page
    reads: list[Path] = []

    def read_twice(path: Path) -> str:
        reads.append(path)
        return read(path) if len(reads) == 1 else "edited meanwhile\n"

    monkeypatch.setattr(run, "read_page", read_twice)

    report = pages.run(update=True)

    assert len(reads) == 2
    assert report.updated == []
    assert pages.read("guide.md") == before
    assert "the page changed while the run read it" in _messages(report)[-1]
    assert run.exit_status(report, update=True) == 1


def test_a_page_is_read_with_a_carriage_return_inside_its_line() -> None:
    text = _page("```console", "$ tool --about", "about tool\r$ echo injected", FENCE)

    (fence,) = run.console_fences(text.split("\n"), "guide.md")

    assert [c.text for c in fence.commands] == ["tool --about"]


def test_a_page_written_with_carriage_returns_and_line_feeds_reads_as_lines(
    pages: Pages,
) -> None:
    (pages.root / "guide.md").write_bytes(
        _page("```console", "$ echo crlf", "crlf", FENCE).replace("\n", "\r\n").encode()
    )

    assert run.read_page(pages.root / "guide.md") == _page(
        "```console", "$ echo crlf", "crlf", FENCE
    )
    assert pages.run().findings == []


def test_the_longest_run_of_matching_lines_is_kept() -> None:
    expected = ["header", "x <any>", "gone", "footer"]
    actual = ["header", "new", "x 1", "footer", "tail"]

    assert run.updated_output(expected, actual) == ["header", "new", "x <any>", "footer", "tail"]


# --- the guards ---------------------------------------------------------------------------


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
    assert "stopped: a command wrote in the repository" in run.render(report)
    assert run.exit_status(report, update=True) == 1


def test_a_write_in_the_git_directory_passes_and_one_elsewhere_still_fails(
    pages: Pages,
) -> None:
    git_dir = pages.root / ".git"
    (git_dir / "objects").mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    pages.write(
        "guide.md",
        "```console",
        f"$ touch {git_dir}/objects/fetched {git_dir}/index && echo x >> {git_dir}/HEAD",
        f"$ mkdir {git_dir}/worktrees && echo written",
        "written",
        f"$ touch {pages.root}/stray.txt",
        FENCE,
    )

    report = pages.run()

    (finding,) = report.findings
    assert finding.line == 12
    assert "wrote outside the scratch project, in the repository" in finding.message
    assert finding.detail == ("  stray.txt",)
    assert report.commands == 3


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
    assert (
        message == "`sleep 20` ran longer than 0.5 seconds; the fence's later commands did not run"
    )
    assert report.commands == 2
    assert not report.stopped


def _plain() -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", os.defpath)}


def test_a_command_printing_past_the_output_limit_is_stopped(tmp_path: Path) -> None:
    started = time.monotonic()
    with run.Shell(tmp_path, _plain()) as shell:
        ran = shell.run("yes", timeout=20, limit=1000)

    assert time.monotonic() - started < 10
    assert ran.stopped == "size"
    assert len(ran.output) == 1000


def test_an_interrupted_run_stops_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "marker"

    def interrupted(*_args: object, **_kwargs: object) -> list[object]:
        raise KeyboardInterrupt

    monkeypatch.setattr(run.selectors.DefaultSelector, "select", interrupted)
    with pytest.raises(KeyboardInterrupt), run.Shell(tmp_path, _plain()) as shell:
        shell.run(f"sleep 1; touch {marker}", timeout=20)
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
    pages.write("guide.md", "```console", "$ echo x", "x", "$ chmod -w .", FENCE)

    with pytest.raises(run.CannotRun, match="lies inside the repository"):
        run.run_pages(pages.selection(), scratch_parent=pages.root, caller=_plain())
    report = pages.run()

    assert report.findings == []
    assert list(pages.scratch.iterdir()) == []
    assert [path.name for path in pages.root.iterdir()] == ["guide.md"]


def test_the_listing_leaves_out_the_git_directory_and_a_repository_inside(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / ".git" / "objects").mkdir(parents=True)
    (root / ".git" / "index").write_text("one", encoding="utf-8")
    (root / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    (root / "worktree").mkdir()
    (root / "worktree" / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    (root / "a.txt").write_text("a", encoding="utf-8")
    before = run.listing(root)

    (root / ".git" / "index").write_text("two, refreshed", encoding="utf-8")
    (root / ".git" / "HEAD").write_text("another ref", encoding="utf-8")
    (root / ".git" / "objects" / "ab").write_text("another session's fetch", encoding="utf-8")
    (root / "worktree" / "new").write_text("another repository's", encoding="utf-8")
    unchanged = run.changed(before, run.listing(root))
    (root / "a.txt").write_text("changed", encoding="utf-8")
    (root / "docs" / "cloned").mkdir(parents=True)
    (root / "docs" / "cloned" / ".git").mkdir()
    (root / "docs" / "cloned" / "file.txt").write_text("cloned", encoding="utf-8")

    assert sorted(before) == ["a.txt", "worktree"]
    assert unchanged == []
    assert run.changed(before, run.listing(root)) == ["a.txt", "docs", "docs/cloned"]


def test_removing_the_scratch_area_changes_no_mode_outside_it(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    (parent / "area" / "locked").mkdir(parents=True)
    (parent / "area" / "locked" / "file").write_text("x", encoding="utf-8")
    (parent / "area" / "link").symlink_to(tmp_path / "outside")
    (tmp_path / "outside").write_text("kept", encoding="utf-8")
    (parent / "area" / "locked").chmod(0o500)
    (parent / "area").chmod(0o000)
    parent.chmod(0o755)

    run._remove(parent / "area")

    assert not (parent / "area").exists()
    assert parent.stat().st_mode & 0o777 == 0o755
    assert (tmp_path / "outside").read_text(encoding="utf-8") == "kept"


def test_the_listing_keeps_a_linked_worktree_s_git_file(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    before = run.listing(tmp_path)

    (tmp_path / ".git").write_text("gitdir: somewhere else", encoding="utf-8")

    assert sorted(before) == [".git"]
    assert run.changed(before, run.listing(tmp_path)) == [".git"]


# --- the selection and the command line ---------------------------------------------------


def test_the_pages_document_is_read_and_one_of_another_shape_stops_the_run(
    tmp_path: Path,
) -> None:
    selection = run.selection_of(
        {
            "schema_version": 1,
            "root": str(tmp_path),
            "types": ["living-docs:page"],
            "pages": ["README.md"],
            "setup": ["git init -q"],
            "path": [],
            "environment": {"CACHE": "<scratch>/cache", "TOKEN": None},
            "placeholders": {"VERSION": "cat VERSION"},
        }
    )

    assert selection.root == tmp_path
    assert selection.pages == ("README.md",)
    assert selection.environment == {"CACHE": "<scratch>/cache", "TOKEN": None}
    for document in (
        {"schema_version": 2, "root": "/r", "pages": []},
        {"schema_version": 1, "pages": []},
        {"schema_version": 1, "root": "/r", "pages": "README.md"},
        {"schema_version": 1, "root": "/r", "pages": [], "environment": {"X": 1}},
        [],
    ):
        with pytest.raises(run.CannotRun):
            run.selection_of(document)


def test_a_cli_that_cannot_answer_stops_the_run_with_what_it_said(tmp_path: Path) -> None:
    script = tmp_path / "pages"
    script.write_text(
        "#!/bin/sh\necho 'error: the configuration names no types' >&2\nexit 1\n",
        encoding="utf-8",
    )
    script.chmod(0o755)

    with pytest.raises(run.CannotRun) as raised:
        run.read_selection(tmp_path, [str(script)])
    with pytest.raises(run.CannotRun, match="cannot run"):
        run.read_selection(tmp_path, [str(tmp_path / "absent")])

    assert str(raised.value) == f"`{script}` exited 1\n  error: the configuration names no types"


def test_the_command_line_runs_the_pages_named_and_refuses_one_that_is_no_page(
    pages: Pages, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run, "read_selection", lambda cwd: pages.selection("guide.md"))
    monkeypatch.setattr("sys.dont_write_bytecode", False)
    pages.write("guide.md", "Prose.")

    assert run.main(["NOTES.md"], cwd=pages.root) == 2
    assert "not among the pages the run reads: NOTES.md" in capsys.readouterr().err
    assert run.main(["guide.md"], cwd=pages.root) == 0
    assert capsys.readouterr().out == "No `console` fence in 1 page(s).\n"
