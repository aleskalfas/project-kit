"""The doc-examples capability's CLI and its run, end to end (#2098; doc-examples
DEC-001 points 3, 10 and 11).

- **The pages (point 3):** `pkit doc-examples pages` lists the documents of the
  types the configuration names, or of living-docs' page type when it names none;
  a document of no type, or one that declares no page kind, is none. `--json` gives
  the run its root and configuration. A selection it cannot read, no types and no
  living-docs, or a type nobody declares, exits 1 and names the fix.
- **Validation (point 11):** `pkit doc-examples validate --json` answers the
  findings document: a placeholder's name not in upper case, a variable taking the
  caller's value under a placeholder's name, and a fence that cannot be read are
  errors; a fence under another name for a shell session is a warning. The
  capability registers it as a member of `pkit validate`.
- **The run through the CLI (point 10):** the run, started by its path, reads the
  pages through the CLI and exits 0 when the fences match, 1 when one fails, and
  2 when the selection cannot be read.

Each test stands up a real adopter repository with the capability installed. Its
scripts are pointed at this interpreter, and the `pkit` they read through is the
real CLI under this interpreter (`pkit_on_path`), so no test reaches the network.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from project_kit import validators
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

CAPABILITY = Path(".pkit") / "capabilities" / "doc-examples"
SCRIPTS = CAPABILITY / "scripts"
CONFIG = f"{CAPABILITY.as_posix()}/project/config.yaml"
FENCE = "```"


def _page(*body: str, kind: str = "guide") -> str:
    return "\n".join(["---", "reader: user", f"kind: {kind}", "---", "", "# Guide", "", *body, ""])


def _to_this_interpreter(repo: AdopterRepo, script: Path) -> None:
    path = repo.root / script
    body = path.read_text(encoding="utf-8").split("\n", 1)[1]
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")


def _adopter(make_adopter_repo: MakeAdopterRepo, *, living_docs: bool = True) -> AdopterRepo:
    capabilities = ("living-docs", "doc-examples") if living_docs else ("doc-examples",)
    repo = make_adopter_repo(capabilities=capabilities)
    for script in ("pages.py", "validate.py"):
        _to_this_interpreter(repo, SCRIPTS / script)
    return repo


def _script(repo: AdopterRepo, name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo.root / SCRIPTS / name), *args],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _pages_document(repo: AdopterRepo) -> dict[str, Any]:
    done = _script(repo, "pages.py", "--json")
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


# --- the pages ------------------------------------------------------------------------


def test_the_pages_are_the_documents_of_living_docs_page_type_by_default(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = _adopter(make_adopter_repo)
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
            CONFIG: (
                "schema_version: 1\n"
                "setup: [git init -q]\n"
                "path: [<project>/bin]\n"
                "environment: {CACHE: <scratch>/cache, TOKEN: null}\n"
                "placeholders: {VERSION: cat VERSION}\n"
            ),
        }
    )

    document = _pages_document(repo)
    listed = _script(repo, "pages.py")

    assert document == {
        "schema_version": 1,
        "root": str(repo.root),
        "types": ["living-docs:page"],
        "pages": ["GUIDE.md", "docs/guide.md"],
        "setup": ["git init -q"],
        "path": ["<project>/bin"],
        "environment": {"CACHE": "<scratch>/cache", "TOKEN": None},
        "placeholders": {"VERSION": "cat VERSION"},
    }
    assert listed.stdout == (
        "2 page(s), the documents of living-docs:page:\n  GUIDE.md\n  docs/guide.md\n"
    )


def test_a_project_names_the_types_of_its_own_pages(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = _adopter(make_adopter_repo, living_docs=False)
    repo.write(
        {
            ".pkit/project/config.yaml": (
                "friction:\n  places:\n    - {path: README.md, type: tutorial}\n    - NOTES.md\n"
            ),
            "README.md": "---\ntitle: Read me\n---\n\n# Read me\n",
            "NOTES.md": "---\ntitle: Notes\n---\n\n# Notes\n",
            CONFIG: "schema_version: 1\ntypes: [tutorial]\n",
        }
    )

    assert _pages_document(repo)["pages"] == ["README.md"]


@pytest.mark.parametrize(
    ("living_docs", "config", "said"),
    [
        (
            False,
            "schema_version: 1\n",
            "names no types, and no installed component declares living-docs' page type",
        ),
        (True, "schema_version: 1\ntypes: [acme:page]\n", "names `acme:page`, which no installed"),
        (True, "schema_version: 1\ntypes: [tutorial]\n", "names `tutorial`, a type of the project"),
        (True, "schema_version: 1\nsetup: echo\n", "/setup: is no list of texts"),
    ],
    ids=["no-selection", "undeclared-component-type", "ungiven-project-type", "of-another-shape"],
)
def test_a_selection_that_cannot_be_read_exits_1_naming_the_fix(
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    living_docs: bool,
    config: str,
    said: str,
) -> None:
    repo = _adopter(make_adopter_repo, living_docs=living_docs)
    repo.write({CONFIG: config})

    done = _script(repo, "pages.py", "--json")

    assert done.returncode == 1
    assert said in done.stderr
    assert done.stdout == ""
    assert "`pkit doc-examples validate` reports the same problems." in done.stderr


# --- validation -----------------------------------------------------------------------


def test_validation_reports_the_configuration_and_each_fence_that_cannot_be_read(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = _adopter(make_adopter_repo)
    repo.write(
        {
            "docs/guide.md": _page(
                "```console",
                "output first",
                "$ echo x",
                FENCE,
                "",
                "```shell-session",
                "$ echo y",
                FENCE,
                "",
                "```console",
                "$ echo fine",
                "fine",
                FENCE,
            ),
            CONFIG: (
                "schema_version: 1\n"
                "environment: {version: null, KEPT: value}\n"
                "placeholders: {VERSION: cat VERSION, name: echo x}\n"
            ),
        }
    )

    done = _script(repo, "validate.py", "--json")
    document = json.loads(done.stdout)

    assert done.returncode == 0
    assert document["summary"] == [
        "2 console fence(s) in 1 page(s), the documents of living-docs:page."
    ]
    found = {(f["severity"], f["location"]): f["message"] for f in document["findings"]}
    assert set(found) == {
        ("error", f"{CONFIG}:/placeholders/name"),
        ("error", f"{CONFIG}:/environment/version"),
        ("error", "docs/guide.md:8"),
        ("warning", "docs/guide.md:13"),
    }
    assert "takes a name in upper case" in found[("error", f"{CONFIG}:/placeholders/name")]
    assert (
        "`<VERSION>`, the name the placeholder `<VERSION>` has"
        in found[("error", f"{CONFIG}:/environment/version")]
    )
    assert "comes before the fence's first command" in found[("error", "docs/guide.md:8")]
    assert "a `shell-session` fence" in found[("warning", "docs/guide.md:13")]
    assert _script(repo, "validate.py").returncode == 1


def test_a_clean_project_validates_and_the_capability_registers_its_validator(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = _adopter(make_adopter_repo)
    repo.write({"docs/guide.md": _page("```console", "$ echo fine", "fine", FENCE)})

    done = _script(repo, "validate.py")

    assert (done.returncode, done.stdout) == (
        0,
        "1 console fence(s) in 1 page(s), the documents of living-docs:page.\n",
    )
    members = [member.name for member in validators.registered_validators(repo.root)]
    assert "doc-examples:examples" in members


# --- the run through the CLI -------------------------------------------------------------


def _run(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo.root / SCRIPTS / "run-examples.py"), *args],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_the_run_reads_its_pages_through_the_cli_and_exits_as_it_finds(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = _adopter(make_adopter_repo)
    repo.write(
        {
            "docs/guide.md": _page(
                "```console", "$ cat VERSION", "<VERSION>", "$ cat greeting", "hello", FENCE
            ),
            CONFIG: (
                "schema_version: 1\n"
                "setup: ['printf \"hello\\n\" > greeting', 'echo 2.0.1 > VERSION']\n"
                "placeholders: {VERSION: cat VERSION}\n"
            ),
        }
    )

    passed = _run(repo)
    repo.write({"docs/guide.md": _page("```console", "$ cat greeting", "goodbye", FENCE)})
    failed = _run(repo, "docs/guide.md")
    repo.write({CONFIG: "schema_version: 1\ntypes: [acme:page]\n"})
    stopped = _run(repo)

    assert (passed.returncode, passed.stdout) == (
        0,
        "2 command(s) run, in 1 fence(s) of 1 page(s): no finding(s)\n",
    )
    assert failed.returncode == 1
    assert "docs/guide.md:9: `cat greeting` printed other output than the page shows" in (
        failed.stdout
    )
    assert stopped.returncode == 2
    assert stopped.stderr.startswith("doc-examples: `pkit doc-examples pages --json` exited 1")
    assert "names `acme:page`, which no installed component declares" in stopped.stderr
