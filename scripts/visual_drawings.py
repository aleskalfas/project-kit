"""Draw each piece's HTML pages on a pull request, and keep them for an agent to fetch
(visual-communication DEC-024 point 5).

The checks workflow's `drawings` job runs it on a pull request's head commit, on the Linux
runner's Chrome, after `pkit sync`:

    uv run python scripts/visual_drawings.py <out>

- **Each piece.** For each piece of the project's visual workspace, the location the
  capability's configuration records (`visual/` where it records none), it runs the look
  through the HTML renderer, in every language and every key, in the form the project writes
  it: `uv run pkit visual look <piece> --renderer html --every-language --every-key`. It
  passes no flag and sets nothing that bears on the browser's own sandbox, so the browser
  starts as the look starts it (DEC-024 point 1).
- **What it keeps.** It copies the look's folder, with each piece's images, frames, page
  files and report, into `<out>`, which the job keeps as the artefact
  `visual-drawings-<commit>`. A stop's report is kept with the rest.
- **What it says.** It writes what each look did into the job's summary,
  `$GITHUB_STEP_SUMMARY` where it is set: each piece, how its look ended, and what a look
  that did not draw printed. It names the commit from `$PKIT_DRAWN_COMMIT`.
- **A stop is no clean run.** It exits 1 where any look did not draw: a stop, a refusal or
  any other failure. A workspace with no piece draws nothing, and passes.

It holds no secret and asks for none. It reads the repository and writes only `<out>` and
what the look writes in the clone's local folder.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

#: The capability's configuration, which records the location, and the location where it
#: records none (visual-communication DEC-002 point 1).
CONFIG = Path(".pkit/capabilities/visual-communication/project/config.yaml")
DEFAULT_LOCATION = "visual"

#: Where the look writes each renderer's folder, relative to the project root.
LOOK_FOLDER = Path(".pkit/capabilities/visual-communication/project/local/look")

#: The look, in the form the project writes it, before the piece's name, and after it.
LOOK = ("uv", "run", "pkit", "visual", "look")
HTML_PAGES = ("--renderer", "html", "--every-language", "--every-key")

#: The look's exit where the browser drew nothing (`look.py`'s `STOPPED`).
STOPPED = 3

#: The name the job keeps the drawings under, with the commit they show.
ARTEFACT = "visual-drawings-{commit}"


@dataclass(frozen=True)
class Looked:
    """One piece's look: how it ended, and what it printed."""

    piece: str
    exit: int
    stdout: str
    stderr: str

    @property
    def drew(self) -> bool:
        return self.exit == 0

    @property
    def ended(self) -> str:
        if self.exit == 0:
            return "drew"
        if self.exit == STOPPED:
            return "stopped"
        if self.exit == 1:
            return "refused"
        return f"failed, exit {self.exit}"


def location(root: Path) -> Path:
    """The location the configuration records, or the default where it records none."""
    config = root / CONFIG
    recorded = None
    if config.is_file():
        data = YAML(typ="safe").load(config.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            recorded = data.get("location")
    return root / (recorded if isinstance(recorded, str) and recorded else DEFAULT_LOCATION)


def pieces(root: Path) -> list[str]:
    """Each piece of the location, by name, in order: a folder of `pieces/` that holds a
    `piece.yaml`."""
    folder = location(root) / "pieces"
    if not folder.is_dir():
        return []
    return sorted(each.name for each in folder.iterdir() if (each / "piece.yaml").is_file())


def command(piece: str) -> list[str]:
    """The look that draws every page of `piece` through the HTML renderer."""
    return [*LOOK, piece, *HTML_PAGES]


def look(root: Path, piece: str) -> Looked:
    """`piece`'s look, run from `root`."""
    done = run(command(piece), root)
    return Looked(piece, done.returncode, done.stdout, done.stderr)


def run(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """`argv` run from `cwd`, what it printed captured."""
    return subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True, check=False)


def keep(root: Path, out: Path) -> None:
    """Copy the look's folder into `out`, as it lies, or make `out` empty where no look
    wrote one."""
    if out.exists():
        shutil.rmtree(out)
    source = root / LOOK_FOLDER
    if source.is_dir():
        shutil.copytree(source, out, symlinks=True)
    else:
        out.mkdir(parents=True)


def summary(looked: Sequence[Looked], commit: str) -> str:
    """What the job's summary says: the artefact, then each piece and how its look ended,
    with what a look that did not draw printed."""
    name = ARTEFACT.format(commit=commit or "<commit>")
    lines = [
        "### Each piece's HTML pages, drawn by the runner's browser",
        "",
        f"Kept as the artefact `{name}`, of commit `{commit or 'unknown'}` "
        "(visual-communication DEC-024 point 5).",
        "",
    ]
    if not looked:
        return "\n".join([*lines, "The visual workspace holds no piece, so nothing was drawn.", ""])
    lines += ["| Piece | Its look |", "|---|---|"]
    lines += [f"| `{each.piece}` | {each.ended} |" for each in looked]
    for each in looked:
        if not each.drew:
            said = (each.stderr or each.stdout).strip() or "nothing"
            ran = " ".join(command(each.piece))
            lines += ["", f"`{ran}` {each.ended}:", "", "```", said, "```"]
    return "\n".join([*lines, ""])


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: visual_drawings.py <out>", file=sys.stderr)
        return 2
    root = Path.cwd()
    out = Path(args[0])
    looked = [look(root, piece) for piece in pieces(root)]
    keep(root, out)
    said = summary(looked, os.environ.get("PKIT_DRAWN_COMMIT", ""))
    print(said)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as written:
            written.write(said)
    for each in looked:
        if not each.drew:
            print(f"error: the look of `{each.piece}` {each.ended}", file=sys.stderr)
    return 0 if all(each.drew for each in looked) else 1


if __name__ == "__main__":
    sys.exit(main())
