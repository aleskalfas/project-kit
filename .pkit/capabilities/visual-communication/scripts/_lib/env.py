"""What the engine reads, through one protocol (visual-communication DEC-005 point 3).

The engine (`formula`, `layout`, `text`, `scene`) knows nothing of the working folder,
pieces, the library list or the configuration. It reads every component, role, colour
family, concept, font, produced picture and picture file through an `Env`, which the
pipeline builds from the project's files, and which the engine's tests stand in for with an
in-memory one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from _lib.pictures import Judged


class MissingFont(Exception):
    """A font a role names has no committed file, so the render is refused before
    anything is laid out (DEC-004 point 9). The message names the font."""


class UnreadableFont(MissingFont):
    """A font whose committed file is present and cannot be read as one, which refuses as a
    missing font does. The message names the file and the font reader's error."""

    def __init__(self, path: Path, error: Exception) -> None:
        why = str(error) or type(error).__name__
        super().__init__(f"the font file {path} cannot be read: {why}")


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


class UnknownConcept(KeyError):
    """A concept the piece's notations do not hold: the piece names no notation of its
    name, or its notation holds no such concept. The message says which."""

    def __init__(self, concept: str, why: str) -> None:
        super().__init__(concept)
        self.concept = concept
        self.why = why

    def __str__(self) -> str:
        return self.why


class UnvaluedRole(KeyError):
    """A library's own role that has no value under the brand: its chain of defaults reaches
    none, and the brand gives it none (DEC-008 point 1). `library` names the library whose
    role it is, and `named` says whether the brand, or a brand it builds on, names that
    library (point 4). Where one does, it owes the role a value, and that is its finding.
    Where none does, neither the brand nor the library alone is at fault, so a part that
    reads the role is found at the lock that combines them (point 9)."""

    def __init__(self, role: str, library: str, *, named: bool) -> None:
        super().__init__(role)
        self.role = role
        self.library = library
        self.named = named


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
        `UnvaluedRole`, a `KeyError`, for a library's own role that has no value under the
        brand, and `KeyError` for a path that holds no role."""
        ...

    def font_file(self, family: str) -> Path:
        """The committed font file of a family in the default font profile. Raises
        `MissingFont`."""
        ...

    def picture(self, output: str) -> PictureInfo:
        """A produced output of the piece. Raises `KeyError` where the piece has none."""
        ...

    def picture_file(self, holder: str, name: object, *, named: str, where: str) -> Judged:
        """The picture file `name` names, found by its bare name and read (DEC-025 points 2,
        5 and 9): in the piece's own `pictures/` where `holder` is `piece`, else in the
        `pictures/` of the version the lock names of the library `holder`. It comes with its
        findings, each lying where `pictures.Folder` places it: one on the file itself at the
        file, and one on the name, which `named` gives in words, at `where`, in no file, so
        the engine places it in what named it, the content or a component."""
        ...

    def family(self, name: str) -> dict[str, str]:
        """A colour family the foundations declare: each member mapped to a colour role
        (DEC-004 point 10). Raises `KeyError` where they declare no such family."""
        ...

    def concept(self, name: str) -> str | None:
        """The colour family a concept maps to, by its name read with its notation's,
        `<notation>/<concept>` (DEC-004 point 10); None where its notation, or the concept
        in it, cannot be read, which is a finding in the notation. Raises `UnknownConcept`,
        a `KeyError`, where the piece names no such notation, or its notation holds no such
        concept."""
        ...

    def library_version(self, library: str) -> str:
        """The version of a library the piece's lock names, for traces and findings."""
        ...
