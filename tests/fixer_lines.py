"""The result lines of a fixer run, read by the run's contract.

project-management DEC-056 point 3 sets what a fixer's final message ends with: one
line for each artefact the brief names, in one of three forms, a `none` line carrying
one of a fixed list of reasons. The contract is data, project-management's
`schemas/fixer-contract.yaml`, and the drift command reads the lines through
`scripts/_lib/fixer_contract.py`. The tests of each fixer — the living-docs agent and
software-analysis' analysis-resolver (#1801) — read their lines here, through that
same module, so a fixer's lines are read as the command reads them:

- **the forms** are the data's, in its order: proposed, held, none. Their
  placeholders are `<agent>`, `<artefact>`, `<the question>`, `<reason>` and `<the
  reason in words>`;
- **the reasons** are the data's `none` reasons, in its order;
- **which lines count**: each line of the message, split at each line feed, that,
  stripped of the whitespace around it, starts with the data's lead. A fence's own
  lines never do, and a line behind a quote's `>` does not count.

`test_pm_fixer_contract.py` holds DEC-056 and project-management's README to the
data, both ways.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parent.parent
MODULE = (
    REPO
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "fixer_contract.py"
)


def _module() -> ModuleType:
    """The contract's module, loaded by its path under a name of its own, so no other
    capability's `_lib` on `sys.path` can stand in for it."""
    name = "pm_fixer_contract_for_tests"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract_module = _module()
CONTRACT = contract_module.load()

#: What a result line starts with, once the whitespace around it is stripped.
LEAD = CONTRACT.lead

_PLACEHOLDER = re.compile(r"<[^<>]+>")


@dataclass(frozen=True)
class Result:
    """One line read by the grammar."""

    state: str  # proposed, held or none
    artefact: str
    answer: str | None = None  # a proposed line's answer file
    reason: str | None = None  # a none line's code
    words: str | None = None  # a held line's question, or a none line's reason in words


def forms() -> tuple[str, ...]:
    """The contract's three line forms, in its order."""
    return tuple(CONTRACT.forms.values())


def reasons() -> tuple[str, ...]:
    """The contract's `none` reasons, in its order."""
    return tuple(CONTRACT.reasons)


def read(line: str, agent: str) -> Result | None:
    """The result `line` gives for `agent`, or None for a line off the grammar or for
    another agent."""
    parsed = contract_module.parse_line(line, CONTRACT)
    if isinstance(parsed, str) or parsed.agent != agent:
        return None
    answer = None
    if parsed.state == contract_module.PROPOSED:
        answer = f"{parsed.artefact}/{CONTRACT.answer_file}"
    return Result(parsed.state, parsed.artefact, answer, parsed.reason, parsed.words)


def counted(message: str) -> list[str]:
    """The lines of `message` the command reads as result lines, stripped."""
    return contract_module.result_lines(message, CONTRACT)


def fill(form: str, values: dict[str, str]) -> str:
    """`form` with each placeholder `values` names filled; any other left in place."""
    return _PLACEHOLDER.sub(lambda found: values.get(found.group(0), found.group(0)), form)
