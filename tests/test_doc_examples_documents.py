"""Each document a doc-examples command prints for a program holds its contract (ADR-097
point 7).

The test runs the command's script in the test's own process (`tests/in_process.py`), its
`pkit` calls answered by the backbone in this process too, and holds what it prints to the
contract pinned here with `tests/document_contracts.py`. A key or a value that goes, or
comes back, fails until the same change updates the pin, beside the changeset that declares
the break. `tests/test_capability_documents.py` holds the ratchet over every capability's
commands.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Mapping

import pytest

from tests.adopter_repo import MakeAdopterRepo
from tests.document_contracts import Contract, Form, check
from tests.in_process import InProcessPkit, load, run_main
from tests.test_doc_examples_commands import CONFIG, _page

pages, selection = load("doc-examples", "pages.py", "selection")

# --- `pkit doc-examples pages --json` ------------------------------------------------------

DOC_EXAMPLES_PAGES = Contract(
    name="pkit doc-examples pages --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "root": "str",
                "types": "list",
                "types[]": "str",
                "pages": "list",
                "pages[]": "str",
                "setup": "list",
                "setup[]": "str",
                "path": "list",
                "path[]": "str",
                "environment": "object",
                "environment{}": "str|null",
                "placeholders": "object",
                "placeholders{}": "str",
            }
        )
    },
    data=frozenset({"environment", "placeholders"}),
)


def test_the_pages_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo(capabilities=("living-docs", "doc-examples"))
    repo.write(
        {
            "docs/guide.md": _page("Under the user root."),
            CONFIG: (
                "schema_version: 1\n"
                "setup: [git init -q]\n"
                "path: [<project>/bin]\n"
                "environment: {CACHE: <scratch>/cache, TOKEN: null}\n"
                "placeholders: {VERSION: cat VERSION}\n"
            ),
        }
    )
    monkeypatch.setattr(
        selection,
        "read_artefacts",
        functools.partial(selection.read_artefacts, run=InProcessPkit()),
    )
    done = run_main(pages, "--json", cwd=repo.root)
    assert done.returncode == 0, done.stderr
    check(DOC_EXAMPLES_PAGES, {"answer": [json.loads(done.stdout)]})


#: The contracts of each doc-examples command that prints a document for a program, by the
#: command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "doc-examples pages": (DOC_EXAMPLES_PAGES,),
}
