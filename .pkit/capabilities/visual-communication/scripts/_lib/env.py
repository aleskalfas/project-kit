"""What the engine reads, through one protocol (visual-communication DEC-005 point 3).

The engine (`formula`, `layout`, `text`, `scene`) knows nothing of the working folder,
pieces, the library list or the configuration. It reads every component, role, font
and produced picture through an `Env`, which the pipeline builds from the project's
files, and which the engine's tests stand in for with an in-memory one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class MissingFont(Exception):
    """A font a role names has no committed file, so the render is refused before
    anything is laid out (DEC-004 point 9). The message names the font."""


class UnreadableComponent(KeyError):
    """A component whose file is present and cannot be read as one: the reader refuses it,
    or it holds no mapping. It is a `KeyError`, so a reader that asks only whether there is
    a component finds none. The message names the component and the reader's error."""

    def __init__(self, use: str, why: str) -> None:
        super().__init__(use)
        self.use = use
        self.why = why

    def __str__(self) -> str:
        return f"the component `{self.use}` cannot be read: {self.why}"


@dataclass(frozen=True)
class PictureInfo:
    """A produced output of the piece, as its record keeps it (DEC-006 points 2-3).

    - `variants`: variant key -> `{"file": str, "pixels": {"width": int, "height": int}}`.
    - `points`: point -> variant key -> `{"x": float, "y": float}`, in the variant's
      pixels, the origin at the top-left corner, y down.
    """

    variants: dict[str, dict]
    points: dict[str, dict]


class Env(Protocol):
    """Everything the engine reads while it computes one scene."""

    def component(self, use: str) -> dict:
        """A component as data, by its use (`<library>/<component>`, or `piece/<component>`
        for a local one). Raises `KeyError` where there is none, and `UnreadableComponent`,
        which is a `KeyError`, where its file is present and cannot be read."""
        ...

    def role(self, token_path: str) -> dict:
        """A role's resolved DTCG value in the scene's size combination, aliases resolved:
        a dimension `{value, unit}`, a number, a font family list, a typography mapping.
        The engine never asks for a colour's: colours stay roles in the scene. Raises
        `KeyError` for a role the brand gives no value."""
        ...

    def font_file(self, family: str) -> Path:
        """The committed font file of a family in the default font profile. Raises
        `MissingFont`."""
        ...

    def picture(self, output: str) -> PictureInfo:
        """A produced output of the piece. Raises `KeyError` where the piece has none."""
        ...

    def family(self, name: str) -> dict[str, str]:
        """A colour family the foundations declare: each member mapped to a colour role
        (DEC-004 point 10). Raises `KeyError` where they declare no such family."""
        ...

    def library_version(self, library: str) -> str:
        """The version of a library the piece's lock names, for traces and findings."""
        ...
