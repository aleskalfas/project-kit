#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6",
#   "jsonschema>=4.21",
#   "fonttools>=4.50",
#   "uharfbuzz>=0.39",
#   "uniseg>=0.8",
#   "pypdf>=4",
# ]
# ///
"""The visual-communication prototype: draws a piece from its content.

    uv run --script visual.py render pieces/friday-slice
    uv run --script visual.py export pieces/friday-slice
    uv run --script visual.py mural  pieces/friday-slice --lang en --out <map.yaml>
    uv run --script visual.py check  pieces/friday-slice
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
