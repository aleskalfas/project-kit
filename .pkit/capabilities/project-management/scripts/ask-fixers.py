#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — ask-fixers (DEC-056 point 2).

Asks the person whether each fixer may start on its own: one question for each
agent the `pkit::work-tracking:fixers` point names, about the types of its
entries that pass the point's checks and have no answer in the grant list. The
words are built from the declaration, for example:

  living-docs can keep your pages true on its own. After each merge, its agent
  living-docs proposes a fix for each one that went out of date, and nothing is
  applied until you approve it. Turn this on? [Y/n]

At a terminal — standard input and standard output both — each answer is
recorded in the grant list (`fixers` in `project/config.yaml`) as it is given:
a yes as a grant, a no as a refusal, so nothing asks about those types again.
With nobody at a terminal, nothing is granted or recorded: each question is
printed with the one command line that grants its fixer. Running this command
is never the consent; only the answer is. An answer counts once its change
merges into the default branch.

Exempt from the bootstrap gate: the backbone is to ask it at the end of an
install or upgrade, possibly before the project bootstrapped, and it reads and
writes nothing a bootstrap provides.

Usage:
  pkit pm ask-fixers

Exit codes:
  0  nothing waits, every question was answered, or nobody was there to ask
  1  the point does not resolve or cannot be read, or the grant list cannot be
     read or written
  2  usage error, or the capability is not found
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib.fixer_cli import run_ask_verb


def main() -> int:
    return run_ask_verb()


if __name__ == "__main__":
    sys.exit(main())
