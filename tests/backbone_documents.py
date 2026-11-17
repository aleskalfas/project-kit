"""How the contract tests of the backbone's documents run a command and read what it
prints (ADR-097 point 7).

A test runs the command in its own process, through the CLI's entry, and reads the one
document it prints, or each line of a stream of them. `tests/document_contracts.py`
holds what it read to the command's contract.
"""

from __future__ import annotations

import json
from typing import Any

from click.testing import CliRunner, Result

from project_kit.cli import main

#: The option by which a backbone command prints its document for a program.
JSON_OPTION = "--json"


def invoke(*args: str, stdin: str | None = None) -> Result:
    """The backbone command `args` names, run in this process."""
    return CliRunner().invoke(main, list(args), input=stdin)


def document_of(result: Result) -> dict[str, Any]:
    """The one document `result` printed."""
    assert result.stdout, result.output
    document = json.loads(result.stdout)
    assert isinstance(document, dict), result.stdout
    return document


def documents_of(result: Result) -> list[dict[str, Any]]:
    """Each document of the stream `result` printed, one a line."""
    assert result.stdout, result.output
    documents = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert documents and all(isinstance(document, dict) for document in documents), result.stdout
    return documents
