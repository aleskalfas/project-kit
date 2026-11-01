"""Brands: their design tokens and Resolver document in the DTCG format 2025.10, and the
foundations' declarations of the shared roles, axes, colour families and pairs (DEC-004).

**The foundations' declarations** (`roles.yaml`, format `roles`) name each shared role with
its type, and a default that aliases an older role where it has one; each shared axis with
its kind, its modes and its default; the colour families, each a mapping of its members to
colour roles; and the pairs of colour roles that must contrast, at WCAG's levels. A shared
role carries no value, so it is no DTCG token.

**A brand** is one library version of kind `brand`. Its `library.yaml` names the DTCG
version, its Resolver document and its open roles. Format 1 reads this subset of DTCG
2025.10, and refuses the rest, which a later format may add:

- *Token files* hold groups and tokens. A token has `$value`, and may have `$type`,
  `$description`, `$extensions` and `$deprecated`; a group may have the same but `$value`,
  and its `$type` passes to the tokens below it in the same file. Every name is a segment
  of a token path. The types are `color` (sRGB: `colorSpace`, three `components` in 0..1,
  `alpha` and `hex` optional), `dimension` (`value` in `px`), `fontFamily` (a name or a
  list), `fontWeight` (1..1000), `number` and `typography` (its five members). A value, or
  a typography member, may alias another token as `{a.b}`.
- *The Resolver document* has `version`, `sets` and `modifiers`, and `resolutionOrder`
  naming each set and modifier once as `{"$ref": "#/sets/<n>"}` or
  `{"$ref": "#/modifiers/<n>"}`; later wins. A source is `{"$ref": "<token file>"}`, a
  file of the brand's version folder. Each modifier is a shared axis: its contexts are the
  axis's modes, and its default the axis's. A brand may leave out an axis it does not vary.
- *Fonts* lie in the capability's extension key, `pkit.visual-communication`, on a
  `fontFamily` token: `files` maps each family to its file in the brand's version folder,
  or to `{"hash": "sha256:<hex>"}` for a file in the location's `fonts/`; `measure` says
  how it is measured, `file` alone in format 1.

**Resolution** merges the brand's sources in resolution order for a combination, over the
shared roles' defaults, then resolves aliases. Every shared role must resolve in every
combination, to its declared type; a loop or a dangling alias fails; a value axis that
changes anything but a colour fails. Open roles name roles the brand exports, or groups of
them by whole segments.

A brand that cannot be resolved raises TokenError, carrying its findings. One that can is
a Brand, whose `findings` hold what is wrong but leaves it usable: an open role it does
not have, a font file nothing holds, a declared pair below its contrast. Every finding of
a brand names the brand's version as where it lies, so its level is read where it lies
(DEC-002 point 7).

Knows nothing of the working folder, pieces, the list or the configuration.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from _lib import keys
from _lib.env import MissingFont
from _lib.files import FileError, read_bound
from _lib.findings import ATTENTION, FAILS, Finding
from _lib.names import COMPONENT, is_name, is_segment, is_token_path
from _lib.reading import ReadError, read_json

#: The capability's extension key in DTCG files (DEC-004 point 1).
EXTENSION = "pkit.visual-communication"

#: The DTCG versions format 1 reads, for token files and the Resolver document alike.
DTCG_VERSIONS = ("2025.10",)

#: The DTCG types format 1 reads.
TYPES = ("color", "dimension", "fontFamily", "fontWeight", "number", "typography")

#: The members of a typography value, each with its type.
TYPOGRAPHY = {
    "fontFamily": "fontFamily",
    "fontSize": "dimension",
    "fontWeight": "fontWeight",
    "letterSpacing": "dimension",
    "lineHeight": "number",
}

#: The kinds of value a value axis may change (DEC-004 point 2): colours alone in format 1.
VALUE_AXIS_TYPES = ("color",)

#: The axes' kinds.
AXIS_KINDS = ("value", "size")

#: The contrast each level of a pair must reach (WCAG 2.2: 1.4.3 and 1.4.11).
LEVELS = {"text": 4.5, "large-text": 3.0, "marks": 3.0}

#: How a font is measured in format 1 (DEC-004 point 9).
MEASURES = ("file",)

_ALIAS = re.compile(r"^\{([^{}]+)\}$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOKEN_KEYS = ("$value", "$type", "$description", "$extensions", "$deprecated")
_GROUP_KEYS = ("$type", "$description", "$extensions", "$deprecated")
_RESOLVER_KEYS = ("version", "name", "description", "sets", "modifiers", "resolutionOrder")


class TokenError(Exception):
    """Declarations or a brand that cannot be read or resolved; `findings` says why."""

    def __init__(self, findings: Iterable[Finding]) -> None:
        self.findings = tuple(findings)
        super().__init__("; ".join(f.message for f in self.findings))


class UnknownRole(KeyError):
    """A token path the brand exports no role at."""


@dataclass(frozen=True)
class Axis:
    """A shared axis: its name, its kind (`value` or `size`), its modes and its default."""

    name: str
    kind: str
    modes: tuple[str, ...]
    default: str


@dataclass(frozen=True)
class Role:
    """A shared role: its token path, its type, and the role its default aliases, if any."""

    path: str
    type: str
    default: str | None = None


@dataclass(frozen=True)
class Pair:
    """Two colour roles that must contrast: `text` drawn on `under`, at `level`."""

    text: str
    under: str
    level: str

    @property
    def minimum(self) -> float:
        return LEVELS[self.level]


@dataclass(frozen=True)
class Declarations:
    """The foundations' declarations (`roles.yaml`)."""

    roles: dict[str, Role]
    axes: dict[str, Axis]
    families: dict[str, dict[str, str]]
    pairs: tuple[Pair, ...]

    @property
    def top_groups(self) -> tuple[str, ...]:
        """The first segments of the shared roles, which no library takes as its name."""
        return tuple(sorted({path.split(".")[0] for path in self.roles}))


# --- the foundations' declarations --------------------------------------------------------------


def read_declarations(path: Path, *, library: str = "", shown: str = "") -> Declarations:
    """The declarations in the `roles.yaml` at `path`. `library` is `<name>@<version>` of
    the library they lie in, and `shown` the file's path as findings name it. Raises
    TokenError."""
    file = shown or path.as_posix()
    problems = _Problems(file, library)
    try:
        data = read_bound(path, "roles")
    except (ReadError, FileError) as exc:
        raise TokenError([problems.finding("roles-unreadable", str(exc))]) from exc
    roles = _read_roles(data.get("roles"), problems)
    axes = _read_axes(data.get("axes", {}), problems)
    families = _read_families(data.get("families", {}), roles, problems)
    pairs = _read_pairs(data.get("pairs", []), roles, problems)
    if problems.found:
        raise TokenError(problems.found)
    return Declarations(roles=roles, axes=axes, families=families, pairs=pairs)


def _read_roles(raw: Any, problems: _Problems) -> dict[str, Role]:
    if not isinstance(raw, Mapping) or not raw:
        problems.add("roles-shape", "`roles` is not a mapping of token paths to roles", "roles")
        return {}
    roles: dict[str, Role] = {}
    for path, spec in raw.items():
        where = f"roles.{path}"
        if not is_token_path(path):
            problems.add("role-name", f"`{path}` is not a token path of lower-case words", where)
            continue
        if path.split(".")[0] == COMPONENT:
            problems.add(
                "role-name",
                f"`{path}` lies under `{COMPONENT}`, the group of component tokens",
                where,
            )
            continue
        if not isinstance(spec, Mapping) or spec.get("type") not in TYPES:
            problems.add(
                "role-type", f"the role `{path}` names no type of {', '.join(TYPES)}", where
            )
            continue
        default = spec.get("default")
        target = None
        if default is not None:
            match = _ALIAS.match(default) if isinstance(default, str) else None
            if match is None:
                problems.add(
                    "role-default", f"the default of `{path}` is not an alias `{{role}}`", where
                )
                continue
            target = match.group(1)
        roles[path] = Role(path=path, type=spec["type"], default=target)
    for role in roles.values():
        if role.default is None:
            continue
        aliased = roles.get(role.default)
        if aliased is None or aliased.default is not None or aliased.type != role.type:
            problems.add(
                "role-default",
                f"the default of `{role.path}` must alias a role of type `{role.type}` that has "
                f"no default itself, not `{role.default}`",
                f"roles.{role.path}",
            )
    for path in roles:
        for other in roles:
            if other.startswith(f"{path}."):
                problems.add(
                    "role-name", f"the role `{path}` is also a group of `{other}`", f"roles.{path}"
                )
                break
    return roles


def _read_axes(raw: Any, problems: _Problems) -> dict[str, Axis]:
    if not isinstance(raw, Mapping):
        problems.add("axes-shape", "`axes` is not a mapping of axes", "axes")
        return {}
    axes: dict[str, Axis] = {}
    for name, spec in raw.items():
        where = f"axes.{name}"
        if not is_name(name) or not isinstance(spec, Mapping):
            problems.add(
                "axis-shape",
                f"the axis `{name}` is not a name with its kind, modes and default",
                where,
            )
            continue
        modes = spec.get("modes")
        kind, default = spec.get("kind"), spec.get("default")
        if kind not in AXIS_KINDS:
            problems.add(
                "axis-shape", f"the axis `{name}` has no kind of {', '.join(AXIS_KINDS)}", where
            )
            continue
        if (
            not isinstance(modes, list)
            or len(modes) < 2
            or len(set(modes)) != len(modes)
            or not all(is_name(mode) for mode in modes)
        ):
            problems.add(
                "axis-shape", f"the axis `{name}` does not name two or more modes, each once", where
            )
            continue
        if default not in modes:
            problems.add(
                "axis-shape", f"the default of the axis `{name}` is not one of its modes", where
            )
            continue
        axes[name] = Axis(name=name, kind=kind, modes=tuple(modes), default=default)
    return axes


def _read_families(
    raw: Any, roles: Mapping[str, Role], problems: _Problems
) -> dict[str, dict[str, str]]:
    if not isinstance(raw, Mapping):
        problems.add("families-shape", "`families` is not a mapping of colour families", "families")
        return {}
    families: dict[str, dict[str, str]] = {}
    for name, members in raw.items():
        where = f"families.{name}"
        if not is_name(name) or not isinstance(members, Mapping) or not members:
            problems.add(
                "family-shape", f"the family `{name}` is not a name with its members", where
            )
            continue
        for member, role in members.items():
            if not is_name(member) or roles.get(role) is None or roles[role].type != "color":
                problems.add(
                    "family-shape",
                    f"the member `{member}` of the family `{name}` names no colour role",
                    f"{where}.{member}",
                )
        families[name] = dict(members)
    return families


def _read_pairs(raw: Any, roles: Mapping[str, Role], problems: _Problems) -> tuple[Pair, ...]:
    if not isinstance(raw, list):
        problems.add("pairs-shape", "`pairs` is not a list of pairs", "pairs")
        return ()
    pairs = []
    for index, spec in enumerate(raw):
        where = f"pairs.{index}"
        if not isinstance(spec, Mapping) or spec.get("level") not in LEVELS:
            problems.add("pair-shape", f"pair {index} names no level of {', '.join(LEVELS)}", where)
            continue
        text, under = spec.get("text"), spec.get("under")
        if any(roles.get(r) is None or roles[r].type != "color" for r in (text, under)):
            problems.add("pair-shape", f"pair {index} does not name two colour roles", where)
            continue
        pairs.append(Pair(text=text, under=under, level=spec["level"]))
    return tuple(pairs)


# --- a brand ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    """A token as one file writes it: its type, given or passed down by its group in that
    file, its value, its extensions, and the file."""

    path: str
    type: str | None
    value: Any
    extensions: Mapping[str, Any]
    file: str


@dataclass(frozen=True)
class _Resolved:
    type: str
    value: Any


class _Problem(Exception):
    def __init__(self, code: str, message: str, file: str, where: str) -> None:
        super().__init__(message)
        self.code, self.message, self.file, self.where = code, message, file, where


class Brand:
    """One brand version, read and checked against the foundations' declarations.

    - `name`, `version`: as its `library.yaml` gives them.
    - `axes`: the shared axes, each a key's axis, whether the brand varies it or not.
    - `roles`: the token paths it exports, the shared roles, in path order.
    - `open`: its open roles, as its `library.yaml` lists them.
    - `findings`: what is wrong, leaving it usable.
    """

    def __init__(
        self,
        *,
        name: str,
        version: str,
        folder: Path,
        foundations: Declarations,
        open_roles: tuple[str, ...],
        resolved: dict[str, dict[str, _Resolved]],
        fonts: dict[str, Path | None],
        findings: tuple[Finding, ...],
    ) -> None:
        self.name = name
        self.version = version
        self.folder = folder
        self.axes = dict(foundations.axes)
        self.roles = tuple(sorted(foundations.roles))
        self.open = open_roles
        self.findings = findings
        self._foundations = foundations
        self._resolved = resolved
        self._fonts = fonts

    def resolve(self, token_path: str, combination: Mapping[str, str]) -> Any:
        """The value of the role at `token_path` in `combination` (an axis left out takes
        its default), aliases resolved, in canonical form: a colour `{colorSpace,
        components, alpha}`, a dimension `{value, unit}`, a font family a list of names, a
        typography its five members so, a number. Raises UnknownRole for a path the brand
        exports no role at, and keys.BadKey for a combination the axes do not hold."""
        if token_path not in self._foundations.roles:
            raise UnknownRole(token_path)
        key = keys.key_of(combination, self.axes)
        return self._resolved[key][token_path].value

    def type_of(self, token_path: str) -> str:
        """The DTCG type of the role at `token_path`. Raises UnknownRole."""
        if token_path not in self._foundations.roles:
            raise UnknownRole(token_path)
        return self._foundations.roles[token_path].type

    def font_file(self, family: str) -> Path:
        """The committed font file that measures and draws `family` in the default font
        profile. Raises MissingFont, naming the family, when none is declared or held."""
        if family not in self._fonts:
            raise MissingFont(
                f"the font family `{family}` has no file in the brand {self.name} {self.version}: "
                f"name one in `{EXTENSION}` `files` on its font token"
            )
        found = self._fonts[family]
        if found is None or not found.is_file():
            raise MissingFont(
                f"the font family `{family}` names a file the project does not hold, in the "
                f"brand {self.name} {self.version}"
            )
        return found

    def families(self) -> tuple[str, ...]:
        """The font families the brand declares files for, in name order."""
        return tuple(sorted(self._fonts))

    def combinations(self) -> list[dict[str, str]]:
        """Every combination of the axes' modes, in key order."""
        return keys.combinations({axis.name: axis.modes for axis in self.axes.values()}, self.axes)


def read_brand(
    folder: Path,
    foundations: Declarations,
    *,
    fonts: Path | None = None,
    root: Path | None = None,
) -> Brand:
    """The brand whose version folder is `folder`, read and checked against
    `foundations`. `fonts` is the location's folder of fonts a brand names by hash; findings
    name files relative to `root` when given, else to `folder`. Raises TokenError."""
    shown = folder.relative_to(root).as_posix() + "/" if root is not None else ""
    library_file = f"{shown}library.yaml"
    try:
        library = read_bound(folder / "library.yaml", "library")
    except (ReadError, FileError) as exc:
        raise TokenError([Finding("brand-unreadable", FAILS, str(exc), file=library_file)]) from exc
    label = f"{library.get('name')}@{library.get('version')}"
    reader = _BrandReader(folder, foundations, library, label, shown, fonts)
    return reader.read()


class _BrandReader:
    """Reads one brand version; collects what it finds as findings."""

    def __init__(
        self,
        folder: Path,
        foundations: Declarations,
        library: Mapping[str, Any],
        label: str,
        shown: str,
        fonts: Path | None,
    ) -> None:
        self.folder = folder
        self.foundations = foundations
        self.library = library
        self.label = label
        self.shown = shown
        self.fonts_folder = fonts
        self.fatal: list[Finding] = []
        self.kept: list[Finding] = []
        self.flat: dict[str, dict[str, _Token]] = {}

    # findings

    def _finding(
        self, code: str, message: str, file: str = "", where: str = "", level: str = FAILS
    ) -> Finding:
        return Finding(
            code, level, message, file=f"{self.shown}{file}", where=where, library=self.label
        )

    def _fail(self, code: str, message: str, file: str = "", where: str = "") -> None:
        self.fatal.append(self._finding(code, message, file, where))

    def _keep(
        self, code: str, message: str, file: str = "", where: str = "", level: str = FAILS
    ) -> None:
        self.kept.append(self._finding(code, message, file, where, level))

    # the whole

    def read(self) -> Brand:
        library = self.library
        if library.get("kind") != "brand":
            self._fail(
                "brand-kind",
                f"{self.label} is not a brand (`kind: {library.get('kind')}`)",
                "library.yaml",
                "kind",
            )
            raise TokenError(self.fatal)
        if library.get("dtcg") not in DTCG_VERSIONS:
            self._fail(
                "brand-dtcg",
                f"`dtcg: {library.get('dtcg')}` is not a DTCG version format 1 reads "
                f"({', '.join(DTCG_VERSIONS)})",
                "library.yaml",
                "dtcg",
            )
        resolver = self._read_resolver(library.get("resolver"))
        if self.fatal or resolver is None:
            raise TokenError(self.fatal)
        order, sets, modifiers = resolver
        resolved: dict[str, dict[str, _Resolved]] = {}
        everything = keys.combinations(
            {axis.name: axis.modes for axis in self.foundations.axes.values()},
            self.foundations.axes,
        )
        for combination in everything:
            key = keys.key_of(combination, self.foundations.axes)
            sources = self._sources(order, sets, modifiers, combination)
            resolved[key] = self._resolve_combination(sources, key)
        if self.fatal:
            raise TokenError(self._unique(self.fatal))
        self._check_value_axes(resolved)
        if self.fatal:
            raise TokenError(self._unique(self.fatal))
        open_roles = self._check_open(library.get("open", []))
        fonts = self._read_fonts(resolved)
        self._check_pairs(resolved)
        return Brand(
            name=str(library.get("name")),
            version=str(library.get("version")),
            folder=self.folder,
            foundations=self.foundations,
            open_roles=open_roles,
            resolved=resolved,
            fonts=fonts,
            findings=tuple(self._unique(self.kept)),
        )

    @staticmethod
    def _unique(found: list[Finding]) -> list[Finding]:
        """Each finding once: a fault in a shared file shows in every combination."""
        seen: set[tuple[str, str, str, str]] = set()
        out = []
        for finding in found:
            mark = (finding.code, finding.file, finding.where, finding.message)
            if mark not in seen:
                seen.add(mark)
                out.append(finding)
        return out

    # the Resolver document

    def _read_resolver(
        self, path: Any
    ) -> (
        tuple[
            tuple[tuple[str, str], ...],
            dict[str, tuple[str, ...]],
            dict[str, dict[str, tuple[str, ...]]],
        ]
        | None
    ):
        rel = self._inside(path, "library.yaml", "resolver")
        if rel is None:
            return None
        try:
            doc = read_json(self.folder / rel)
        except ReadError as exc:
            self._fail("resolver-unreadable", str(exc), rel)
            return None
        if not isinstance(doc, Mapping):
            self._fail("resolver-shape", "the Resolver document is not an object", rel)
            return None
        for key in doc:
            if key not in _RESOLVER_KEYS:
                self._fail(
                    "resolver-shape",
                    f"the Resolver document has `{key}`, which format 1 does not read",
                    rel,
                    key,
                )
        if doc.get("version") not in DTCG_VERSIONS:
            self._fail(
                "resolver-shape",
                f"the Resolver document's `version` is not {', '.join(DTCG_VERSIONS)}",
                rel,
                "version",
            )
        raw_sets, raw_modifiers = doc.get("sets", {}), doc.get("modifiers", {})
        sets = self._read_sets(raw_sets, rel)
        modifiers = self._read_modifiers(raw_modifiers, rel)
        names = {
            "sets": set(raw_sets) if isinstance(raw_sets, Mapping) else set(),
            "modifiers": set(raw_modifiers) if isinstance(raw_modifiers, Mapping) else set(),
        }
        order = self._read_order(doc.get("resolutionOrder"), names, rel)
        if self.fatal:
            return None
        return order, sets, modifiers

    def _read_sets(self, raw: Any, rel: str) -> dict[str, tuple[str, ...]]:
        if not isinstance(raw, Mapping):
            self._fail("resolver-shape", "`sets` is not an object", rel, "sets")
            return {}
        sets = {}
        for name, spec in raw.items():
            where = f"sets.{name}"
            if not isinstance(spec, Mapping) or set(spec) - {"sources", "description"}:
                self._fail(
                    "resolver-shape",
                    f"the set `{name}` holds more than `sources` and `description`",
                    rel,
                    where,
                )
                continue
            sets[name] = self._read_sources(spec.get("sources"), rel, where)
        return sets

    def _read_modifiers(self, raw: Any, rel: str) -> dict[str, dict[str, tuple[str, ...]]]:
        if not isinstance(raw, Mapping):
            self._fail("resolver-shape", "`modifiers` is not an object", rel, "modifiers")
            return {}
        modifiers = {}
        for name, spec in raw.items():
            where = f"modifiers.{name}"
            axis = self.foundations.axes.get(name)
            if axis is None:
                self._fail(
                    "brand-axis",
                    f"the modifier `{name}` is no shared axis; format 1 reads no axis of a "
                    f"brand's own (the shared axes: {', '.join(sorted(self.foundations.axes))})",
                    rel,
                    where,
                )
                continue
            if not isinstance(spec, Mapping) or set(spec) - {"contexts", "default", "description"}:
                self._fail(
                    "resolver-shape",
                    f"the modifier `{name}` holds more than `contexts`, `default` and "
                    f"`description`",
                    rel,
                    where,
                )
                continue
            contexts = spec.get("contexts")
            if not isinstance(contexts, Mapping) or set(contexts) != set(axis.modes):
                self._fail(
                    "brand-axis",
                    f"the modifier `{name}` must have one context for each mode of the axis: "
                    f"{', '.join(axis.modes)}",
                    rel,
                    f"{where}.contexts",
                )
                continue
            if spec.get("default") != axis.default:
                self._fail(
                    "brand-axis",
                    f"the modifier `{name}` must default to the axis's default, `{axis.default}`",
                    rel,
                    f"{where}.default",
                )
                continue
            modifiers[name] = {
                mode: self._read_sources(contexts[mode], rel, f"{where}.contexts.{mode}")
                for mode in axis.modes
            }
        return modifiers

    def _read_sources(self, raw: Any, rel: str, where: str) -> tuple[str, ...]:
        if not isinstance(raw, list):
            self._fail("resolver-shape", f"`{where}` is not a list of sources", rel, where)
            return ()
        files = []
        for index, source in enumerate(raw):
            at = f"{where}.{index}"
            if not isinstance(source, Mapping) or set(source) != {"$ref"}:
                self._fail(
                    "resolver-shape",
                    f'the source `{at}` is not `{{"$ref": "<token file>"}}`',
                    rel,
                    at,
                )
                continue
            file = self._inside(source["$ref"], rel, at)
            if file is not None:
                files.append(file)
                self._flatten(file)
        return tuple(files)

    def _read_order(
        self, raw: Any, names: Mapping[str, set[str]], rel: str
    ) -> tuple[tuple[str, str], ...]:
        """The resolution order; `names` holds the document's own sets and modifiers."""
        if not isinstance(raw, list):
            self._fail("resolver-shape", "`resolutionOrder` is not a list", rel, "resolutionOrder")
            return ()
        order: list[tuple[str, str]] = []
        for index, item in enumerate(raw):
            where = f"resolutionOrder.{index}"
            ref = item.get("$ref") if isinstance(item, Mapping) and set(item) == {"$ref"} else None
            match = (
                re.fullmatch(r"#/(sets|modifiers)/([^/]+)", ref) if isinstance(ref, str) else None
            )
            if match is None:
                self._fail(
                    "resolver-shape",
                    f"`{where}` is not a reference to a set or a modifier",
                    rel,
                    where,
                )
                continue
            kind, name = match.group(1), match.group(2)
            if name not in names[kind]:
                self._fail(
                    "resolver-shape",
                    f"`{where}` names `{ref}`, which the document does not hold",
                    rel,
                    where,
                )
                continue
            if (kind, name) in order:
                self._fail("resolver-shape", f"`{where}` names `{ref}` a second time", rel, where)
                continue
            order.append((kind, name))
        named = {(kind, name) for kind, name in order}
        for kind, held in names.items():
            for name in sorted(held):
                if (kind, name) not in named:
                    self._fail(
                        "resolver-shape",
                        f"`resolutionOrder` does not name `#/{kind}/{name}`",
                        rel,
                        "resolutionOrder",
                    )
        return tuple(order)

    def _inside(self, path: Any, rel: str, where: str) -> str | None:
        """`path` as a file of the brand's version folder, or None, failing it."""
        if not isinstance(path, str) or not path:
            self._fail("brand-file", f"`{where}` names no file", rel, where)
            return None
        posix = PurePosixPath(path)
        if posix.is_absolute() or ".." in posix.parts or "\\" in path or "#" in path:
            self._fail(
                "brand-file",
                f"`{path}` is not a path within the brand's version folder",
                rel,
                where,
            )
            return None
        if not (self.folder / path).is_file():
            self._fail(
                "brand-file",
                f"`{path}` names a file the brand's version folder does not hold",
                rel,
                where,
            )
            return None
        return posix.as_posix()

    # token files

    def _flatten(self, file: str) -> None:
        if file in self.flat:
            return
        self.flat[file] = {}
        try:
            data = read_json(self.folder / file)
        except ReadError as exc:
            self._fail("tokens-unreadable", str(exc), file)
            return
        if not isinstance(data, Mapping):
            self._fail("tokens-shape", "a token file is not an object", file)
            return
        self._walk(data, "", None, file, top=True)

    def _walk(
        self,
        node: Mapping[str, Any],
        prefix: str,
        inherited: str | None,
        file: str,
        *,
        top: bool = False,
    ) -> None:
        group_type = node.get("$type", inherited)
        if "$type" in node and node["$type"] not in TYPES:
            self._fail(
                "token-type",
                f"`$type: {node['$type']}` is not a type format 1 reads ({', '.join(TYPES)})",
                file,
                prefix,
            )
            return
        for key, child in node.items():
            if key.startswith("$"):
                if key not in _GROUP_KEYS and not (top and key == "$schema"):
                    self._fail(
                        "tokens-shape",
                        f"the group `{prefix or '(top)'}` has `{key}`, which format 1 does "
                        f"not read",
                        file,
                        prefix,
                    )
                continue
            path = f"{prefix}.{key}" if prefix else key
            if not is_segment(key):
                self._fail(
                    "token-name",
                    f"`{key}` is not a name of lower-case words of letters and digits",
                    file,
                    path,
                )
                continue
            if not isinstance(child, Mapping):
                self._fail("tokens-shape", f"`{path}` is neither a group nor a token", file, path)
                continue
            if "$value" in child:
                self._token(child, path, group_type, file)
            else:
                self._walk(child, path, group_type, file)

    def _token(self, node: Mapping[str, Any], path: str, inherited: str | None, file: str) -> None:
        for key in node:
            if key not in _TOKEN_KEYS:
                self._fail(
                    "tokens-shape",
                    f"the token `{path}` has `{key}`, which a token does not hold",
                    file,
                    path,
                )
                return
        type_ = node.get("$type", inherited)
        if type_ is not None and type_ not in TYPES:
            self._fail(
                "token-type",
                f"`$type: {type_}` is not a type format 1 reads ({', '.join(TYPES)})",
                file,
                path,
            )
            return
        extensions = node.get("$extensions", {})
        if not isinstance(extensions, Mapping):
            self._fail(
                "tokens-shape", f"the `$extensions` of `{path}` is not an object", file, path
            )
            return
        if EXTENSION in extensions and type_ != "fontFamily":
            self._fail(
                "tokens-shape",
                f"`{path}` carries `{EXTENSION}`, which only a `fontFamily` token takes in "
                f"format 1",
                file,
                path,
            )
            return
        self.flat[file][path] = _Token(path, type_, node["$value"], extensions, file)

    # resolution

    def _sources(
        self,
        order: tuple[tuple[str, str], ...],
        sets: Mapping[str, tuple[str, ...]],
        modifiers: Mapping[str, Mapping[str, tuple[str, ...]]],
        combination: Mapping[str, str],
    ) -> list[str]:
        files: list[str] = []
        for kind, name in order:
            files.extend(sets[name] if kind == "sets" else modifiers[name][combination[name]])
        return files

    def _resolve_combination(self, sources: list[str], key: str) -> dict[str, _Resolved]:
        merged: dict[str, _Token] = {}
        for role in self.foundations.roles.values():
            if role.default is not None:
                merged[role.path] = _Token(role.path, role.type, f"{{{role.default}}}", {}, "")
        for file in sources:
            merged.update(self.flat.get(file, {}))
        self._check_paths(merged)
        resolved: dict[str, _Resolved] = {}
        for path in merged:
            try:
                resolved[path] = self._resolve(path, merged, resolved, ())
            except _Problem as problem:
                self._fail(problem.code, problem.message, problem.file, problem.where)
        for role in self.foundations.roles.values():
            found = resolved.get(role.path)
            if role.path not in merged:
                self._fail(
                    "role-missing",
                    f"the brand gives the role `{role.path}` no value in the combination `{key}`",
                    "",
                    role.path,
                )
            elif found is not None and found.type != role.type:
                self._fail(
                    "role-type",
                    f"the role `{role.path}` is of type `{role.type}`, but the brand gives it a "
                    f"`{found.type}` in the combination `{key}`",
                    merged[role.path].file,
                    role.path,
                )
        return resolved

    def _check_paths(self, merged: Mapping[str, _Token]) -> None:
        shared_groups = set(self.foundations.top_groups)
        for path, token in merged.items():
            if (
                token.file
                and path.split(".")[0] in shared_groups
                and path not in self.foundations.roles
            ):
                self._fail(
                    "token-shared-group",
                    f"`{path}` lies in the shared group `{path.split('.')[0]}` but is no shared "
                    f"role; a brand's own tokens lie in groups of their own",
                    token.file,
                    path,
                )
            for other in merged:
                if other.startswith(f"{path}."):
                    self._fail(
                        "tokens-shape",
                        f"`{path}` is a token in one file and a group in another",
                        token.file,
                        path,
                    )
                    break

    def _resolve(
        self,
        path: str,
        merged: Mapping[str, _Token],
        done: dict[str, _Resolved],
        chain: tuple[str, ...],
    ) -> _Resolved:
        if path in done:
            return done[path]
        token = merged[path]
        if path in chain:
            loop = " → ".join((*chain[chain.index(path) :], path))
            raise _Problem("alias-loop", f"the aliases make a loop: {loop}", token.file, path)
        chain = (*chain, path)
        target = self._alias(token.value)
        if target is not None:
            if target not in merged:
                raise _Problem(
                    "alias-dangling",
                    f"`{path}` aliases `{target}`, which the brand does not hold",
                    token.file,
                    path,
                )
            found = self._resolve(target, merged, done, chain)
            if token.type is not None and token.type != found.type:
                raise _Problem(
                    "alias-type",
                    f"`{path}` is of type `{token.type}` but aliases `{target}`, of type "
                    f"`{found.type}`",
                    token.file,
                    path,
                )
            done[path] = found
            return found
        if token.type is None:
            raise _Problem(
                "token-type", f"`{path}` has no `$type`, and its group gives none", token.file, path
            )
        if token.type == "typography":
            value = self._typography(token, merged, done, chain)
        else:
            value = _canonical(token.type, token.value, token.file, path)
        found = _Resolved(token.type, value)
        done[path] = found
        return found

    def _typography(
        self,
        token: _Token,
        merged: Mapping[str, _Token],
        done: dict[str, _Resolved],
        chain: tuple[str, ...],
    ) -> dict[str, Any]:
        raw = token.value
        if not isinstance(raw, Mapping) or set(raw) != set(TYPOGRAPHY):
            raise _Problem(
                "token-value",
                f"`{token.path}` is a typography, which holds exactly {', '.join(TYPOGRAPHY)}",
                token.file,
                token.path,
            )
        value = {}
        for member, type_ in TYPOGRAPHY.items():
            target = self._alias(raw[member])
            where = f"{token.path}.{member}"
            if target is None:
                value[member] = _canonical(type_, raw[member], token.file, where)
                continue
            if target not in merged:
                raise _Problem(
                    "alias-dangling",
                    f"`{where}` aliases `{target}`, which the brand does not hold",
                    token.file,
                    token.path,
                )
            found = self._resolve(target, merged, done, chain)
            if found.type != type_:
                raise _Problem(
                    "alias-type",
                    f"`{where}` must be a `{type_}`, but aliases a `{found.type}`",
                    token.file,
                    token.path,
                )
            value[member] = found.value
        return value

    @staticmethod
    def _alias(value: Any) -> str | None:
        match = _ALIAS.match(value) if isinstance(value, str) else None
        return match.group(1) if match else None

    # checks across combinations

    def _check_value_axes(self, resolved: Mapping[str, Mapping[str, _Resolved]]) -> None:
        axes = self.foundations.axes
        for key, values in resolved.items():
            combination = keys.parse_key(key, axes)
            for axis in axes.values():
                if axis.kind != "value" or combination[axis.name] == axis.default:
                    continue
                base = keys.key_of({**combination, axis.name: axis.default}, axes)
                before = resolved[base]
                for path in sorted(set(values) | set(before)):
                    one, other = values.get(path), before.get(path)
                    if one == other:
                        continue
                    type_ = one.type if one is not None else other.type if other is not None else ""
                    if type_ in VALUE_AXIS_TYPES:
                        continue
                    self._fail(
                        "value-axis-changes-size",
                        f"the value axis `{axis.name}` may change only colours, but its mode "
                        f"`{combination[axis.name]}` changes `{path}`, a `{type_}`, in the "
                        f"combination `{key}`",
                        "",
                        path,
                    )

    def _check_open(self, raw: Any) -> tuple[str, ...]:
        if not isinstance(raw, list):
            self._keep("open-shape", "`open` is not a list of roles", "library.yaml", "open")
            return ()
        exported = self.foundations.roles
        for entry in raw:
            if not is_token_path(entry) or not any(
                path == entry or path.startswith(f"{entry}.") for path in exported
            ):
                self._keep(
                    "open-unknown",
                    f"the open role `{entry}` names no role the brand exports, nor a group of them",
                    "library.yaml",
                    "open",
                )
        return tuple(entry for entry in raw if isinstance(entry, str))

    def _read_fonts(
        self, resolved: Mapping[str, Mapping[str, _Resolved]]
    ) -> dict[str, Path | None]:
        fonts: dict[str, Path | None] = {}
        declared: dict[str, tuple[Any, str, str]] = {}
        for file, tokens in self.flat.items():
            for path, token in tokens.items():
                extension = token.extensions.get(EXTENSION)
                if extension is None:
                    continue
                if (
                    not isinstance(extension, Mapping)
                    or set(extension) != {"files", "measure"}
                    or extension["measure"] not in MEASURES
                    or not isinstance(extension["files"], Mapping)
                ):
                    self._keep(
                        "font-shape",
                        f"`{EXTENSION}` on `{path}` must hold `files` and `measure` "
                        f"({', '.join(MEASURES)})",
                        file,
                        path,
                    )
                    continue
                for family, where in extension["files"].items():
                    if family in declared and declared[family][0] != where:
                        self._keep(
                            "font-shape", f"the family `{family}` is given two files", file, path
                        )
                        continue
                    declared[family] = (where, file, path)
        for family, (where, file, path) in declared.items():
            fonts[family] = self._font_path(family, where, file, path)
        named = set()
        for values in resolved.values():
            for found in values.values():
                if found.type == "fontFamily":
                    named.update(found.value)
                elif found.type == "typography":
                    named.update(found.value["fontFamily"])
        for family in sorted(named - set(fonts)):
            self._keep(
                "font-missing",
                f"the font family `{family}` has no file: name one in `{EXTENSION}` `files` on "
                f"its font token",
                "",
                family,
            )
        return fonts

    def _font_path(self, family: str, where: Any, file: str, path: str) -> Path | None:
        if (
            isinstance(where, Mapping)
            and set(where) == {"hash"}
            and _HASH.match(str(where["hash"]))
        ):
            found = self._held_font(where["hash"])
            if found is None:
                self._keep(
                    "font-missing",
                    f"the font family `{family}` names the file {where['hash']}, which the "
                    f"location's `fonts/` does not hold",
                    file,
                    path,
                )
            return found
        if isinstance(where, str):
            posix = PurePosixPath(where)
            if not posix.is_absolute() and ".." not in posix.parts and "\\" not in where:
                target = self.folder / where
                if not target.is_file():
                    self._keep(
                        "font-missing",
                        f"the font family `{family}` names `{where}`, which the brand's version "
                        f"folder does not hold",
                        file,
                        path,
                    )
                return target
        self._keep(
            "font-shape",
            f"the file of the font family `{family}` is neither a path within the brand's "
            f'version folder nor `{{"hash": "sha256:<hex>"}}`',
            file,
            path,
        )
        return None

    def _held_font(self, wanted: str) -> Path | None:
        if self.fonts_folder is None or not self.fonts_folder.is_dir():
            return None
        for candidate in sorted(self.fonts_folder.iterdir()):
            if candidate.is_file() and not candidate.is_symlink():
                if f"sha256:{hashlib.sha256(candidate.read_bytes()).hexdigest()}" == wanted:
                    return candidate
        return None

    def _check_pairs(self, resolved: Mapping[str, Mapping[str, _Resolved]]) -> None:
        for pair in self.foundations.pairs:
            for key, values in resolved.items():
                text, under = values[pair.text].value, values[pair.under].value
                if under["alpha"] < 1:
                    self._keep(
                        "pair-translucent",
                        f"`{pair.under}` is translucent in the combination `{key}`, so the "
                        f"contrast of `{pair.text}` on it depends on what lies under it",
                        "",
                        pair.under,
                        level=ATTENTION,
                    )
                    continue
                ratio = contrast_ratio(text, under)
                if ratio < pair.minimum:
                    self._keep(
                        "pair-contrast",
                        f"`{pair.text}` on `{pair.under}` has the contrast {ratio:.2f} in the "
                        f"combination `{key}`, below the {pair.minimum} its level "
                        f"`{pair.level}` needs",
                        "",
                        pair.text,
                    )


# --- values -------------------------------------------------------------------------------------


#: What each type is, as a refusal names it.
_SHAPES = {
    "color": "sRGB colour `{colorSpace: srgb, components, alpha?, hex?}`",
    "dimension": "dimension `{value, unit: px}`",
    "fontFamily": "font family: a name, or a list of names",
    "fontWeight": "font weight, a number from 1 to 1000",
    "number": "number",
}

#: What `_canonical_or_none` gives for a value that is not of its type.
_INVALID = object()


def _canonical(type_: str, value: Any, file: str, where: str) -> Any:
    """`value` of `type_` in canonical form; _Problem when it is not of that type as format
    1 reads it."""
    found = _canonical_or_none(type_, value)
    if found is _INVALID:
        raise _Problem("token-value", f"`{where}` is no {_SHAPES[type_]}", file, where)
    return found


def _canonical_or_none(type_: str, value: Any) -> Any:
    if type_ == "color":
        if (
            isinstance(value, Mapping)
            and value.get("colorSpace") == "srgb"
            and set(value) <= {"colorSpace", "components", "alpha", "hex"}
            and isinstance(value.get("components"), list)
            and len(value["components"]) == 3
            and all(_unit(c) for c in value["components"])
            and _unit(value.get("alpha", 1))
            and (
                "hex" not in value
                or (
                    isinstance(value["hex"], str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", value["hex"])
                )
            )
        ):
            return {
                "colorSpace": "srgb",
                "components": list(value["components"]),
                "alpha": value.get("alpha", 1),
            }
    elif type_ == "dimension":
        if (
            isinstance(value, Mapping)
            and set(value) == {"value", "unit"}
            and _number(value["value"])
            and value["unit"] == "px"
        ):
            return {"value": value["value"], "unit": "px"}
    elif type_ == "fontFamily":
        names = [value] if isinstance(value, str) else value
        if (
            isinstance(names, list)
            and names
            and all(isinstance(n, str) and n.strip() for n in names)
        ):
            return list(names)
    elif type_ in ("fontWeight", "number"):
        if _number(value) and (type_ == "number" or 1 <= value <= 1000):
            return value
    return _INVALID


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _unit(value: Any) -> bool:
    return _number(value) and 0 <= value <= 1


def contrast_ratio(text: Mapping[str, Any], under: Mapping[str, Any]) -> float:
    """The WCAG contrast of the colour `text` drawn on the opaque colour `under`, both in
    canonical form: a translucent text is laid over `under` first."""
    alpha = text["alpha"]
    drawn = [
        t * alpha + u * (1 - alpha)
        for t, u in zip(text["components"], under["components"], strict=True)
    ]
    lighter, darker = sorted((_luminance(drawn), _luminance(under["components"])), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(components: Iterable[float]) -> float:
    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in components)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class _Problems:
    """The findings of a declarations file."""

    def __init__(self, file: str, library: str) -> None:
        self.file, self.library = file, library
        self.found: list[Finding] = []

    def finding(self, code: str, message: str, where: str = "") -> Finding:
        return Finding(code, FAILS, message, file=self.file, where=where, library=self.library)

    def add(self, code: str, message: str, where: str = "") -> None:
        self.found.append(self.finding(code, message, where))
