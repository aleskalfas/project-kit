"""Brands: their design tokens and Resolver document in the DTCG format 2025.10, the
foundations' declarations of the shared roles, axes, colour families and pairs (DEC-004),
and the own roles of the component libraries resolved with a brand (DEC-008).

**The foundations' declarations** (`roles.yaml`, format `roles`) name each shared role with
its type, and a default that aliases an older role where it has one; each shared axis with
its kind, its modes and its default; the colour families, each a mapping of its members to
colour roles; and the pairs of colour roles that must contrast, at WCAG's levels. A shared
role carries no value, so it is no DTCG token. A role of the type `picture` takes a picture
file of the brand as its value; it carries no default, and no brand owes it a value
(DEC-025 point 4).

**A component library's own roles** (`roles.yaml` of a library of kind `components` other
than the foundations, `read_own_roles`) lie under a group of its name, none under the group
of component tokens (DEC-004 point 7). Each has a type, and may carry a default: an alias
to another of its own roles, or to a role of a library it builds on, the shared roles
included, of the same type, never to a value or a component token (DEC-008 point 3). Its
pairs each name one of its own roles. It declares no axes, no colour families and no
picture role, which the foundations' alone are. What is wrong in it never refuses it: it
is kept as its findings, each naming its version, and a role or a pair that cannot be
read is left out.

**A scope** (`Scope`) is the roles one resolution reads: the foundations' and the own roles
of each component library resolved with them, one version of each, under a lock or as a
version is checked alone (DEC-008 point 1). It judges each library's defaults and pairs
against the libraries it builds on there: a default that aliases a component token, a
role of another type or of a library it does not build on, a default that leads nowhere
or a loop of defaults, each fails; a pair that, its own roles replaced by their defaults,
falls on no pair the foundations, the library or a library it builds on declares at a
level as strict fails; a role whose chain of defaults does not end at a shared role is
stated as a fact. A role's type reads from the scope with no brand.

**A brand** is one library version of kind `brand`. Its `library.yaml` names the DTCG
version, its Resolver document, its open roles, and the brand it builds on as its base, if
any. Format 1 reads this subset of DTCG 2025.10, and refuses the rest, which a later
format may add:

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
  file of the brand's version folder. Each modifier is a shared axis the brand varies:
  its contexts are the modes it gives, the axis's default among them, and its default the
  axis's (DEC-004 point 1). A brand may leave out an axis it does not vary.
- *Fonts* lie in the capability's extension key, `pkit.visual-communication`, on a
  `fontFamily` token: `files` maps each family to its file in the brand's version folder,
  or to `{"hash": "sha256:<hex>"}` for a file in the location's `fonts/`; `measure` says
  how it is measured, `file` alone in format 1.
- *A picture role's value* is an empty group at the role's path, with no `$type`, since
  DTCG has no type for a file (DEC-025 point 4). Its `$extensions` name the file in the
  capability's extension key, `{"file": "<name>"}`, by its bare name in the version's
  `pictures/`. It aliases nothing, no token aliases it, and it merges as a token does.

**The axes a brand has** (DEC-004 point 2, DEC-021 point 2), which its keys span:

- *every shared value axis, whole:* a mode the brand does not give takes its values at
  the axis's default, and in a brand built on another its base's values there. So a new
  mode of the foundations reads no released brand as broken;
- *a shared size axis only where it gives one:* a brand with no base has one where a
  modifier varies it, with the modes that modifier gives. A brand built on another has
  its base's sizes. So a brand that gives no size keeps its combinations when the
  foundations declare a size axis, and a piece that names a size it lacks is refused.

**Resolution** merges the brand's sources in resolution order for a combination, over the
roles' defaults, then resolves aliases. Every shared role but a picture role must resolve
in every combination, to its declared type; a loop or a dangling alias fails; a value axis
that changes anything but a colour or a picture fails. A picture role's value names a file
the version holds in `pictures/`, by its exact name, or that is a finding. Open roles name
roles the brand may give values, or groups of them by whole segments.

**A brand and a library's own roles** (DEC-008 points 1 and 4 to 6):

- *reached only where named:* a brand reaches a library's roles, to give one a value, open
  it or alias it, only where its `builds-on` names that library by the major the scope's
  version fits (`named`). A token it holds under the name of a library it names gives one
  of its roles a value; one that names none of them, or is of another type, is a finding.
  Under the name of a library it does not name, a token stays private, and where the scope
  holds that library, as under a lock, it asks for attention;
- *defaults below every brand:* a default lies under the base's tokens and the brand's own
  sources, and is resolved after the merge, so it follows the value the brand gives the
  role it aliases. A role whose chain of defaults reaches no value has none under the
  brand; a brand that names its library gives each of its roles with no default a value
  in every combination, or that is a finding;
- *exports:* a brand exports, beside the shared roles, each role of a library it names
  that it or its base gives a value (`roles`). It exports a shared picture role only
  where it or its base gives it a value (DEC-025 point 4). Every role with a value under
  it but a picture role, a role left at its default included, is `valued`, which the
  document of values holds;
- *pairs:* a library's pair is judged at a brand only where the brand's values reach it,
  through a value the brand or its base gives a library's role along either role's chain
  of defaults, and then in every combination; at its defaults it is its library's to
  judge.

**A brand built on another** (DEC-004 point 6) marks one entry of its `builds-on`, a
brand, `base: true`. The caller gives the version folder of each library the lock names
(`locked`), and the base is read from the one of its name, first, its own base before it;
its major is the one the entry names. In each combination:

- *merged before aliases are resolved:* the base's tokens come first, then the brand's
  own sources in its resolution order. The brand's value for a role its base opens wins in
  the combinations its sources cover, and the base's holds elsewhere; every token that
  aliases the role, the base's own included, follows the merged value. A value the brand
  gives a role its base does not open is a finding, and the base's value holds;
- *each library's private tokens stay its own:* an alias reaches the exported roles and
  the tokens of the library that writes it, never a token its base keeps private, which
  fails. So a base may reshape its private tokens freely;
- *the base's axes:* the brand varies values on its base's axes, by their names and modes,
  its base's sizes among them. A modifier for another axis, a context for another mode, or
  another default fails;
- *chains narrow:* the brand's open roles name only roles its base opens to it (format 1
  has no brand's own roles), so each link of a chain opens at most what the last opens.
  A base opens a role of a library only where it names that library, and a brand built on
  it gives the role a value only where it names the library too (DEC-008 point 4).

A brand that cannot be resolved raises TokenError, carrying its findings. One that can is
a Brand, whose `findings` hold what is wrong but leaves it usable: an open role it does
not have, a value for a role its base does not open, a font file or a picture file
nothing holds, a declared pair below its contrast, a token under a library's name that
gives none of its roles a value, a role of a library it names that it leaves with no
value. Its `facts` hold what its version alone states: each shared picture role it gives
no value (DEC-025 point 9). A library's own
`roles.yaml` is no brand's: its findings are the scope's (`Scope.findings`), each naming
the library's version. Every finding of a brand names the brand's version as where it
lies, so its level is read where it lies (DEC-002 point 7); a fault of the lock, a base it
names at another major or not at all, names none, and always fails. A brand's findings
hold its base's too, each naming the base's version; a pair or a font family is judged at
the brand only where the brand's values change what the base gives.

Knows nothing of the working folder, pieces, the list or the configuration.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from _lib import keys
from _lib.env import MissingFont, UnvaluedRole
from _lib.files import FileError, read_bound
from _lib.findings import ATTENTION, FACT, FAILS, Finding
from _lib.libraries import FOUNDATIONS, LibraryError, read_library
from _lib.names import COMPONENT, is_name, is_segment, is_token_path
from _lib.reading import ReadError, read_json

#: The capability's extension key in DTCG files (DEC-004 point 1).
EXTENSION = "pkit.visual-communication"

#: The DTCG versions format 1 reads, for token files and the Resolver document alike.
DTCG_VERSIONS = ("2025.10",)

#: The DTCG types format 1 reads.
TYPES = ("color", "dimension", "fontFamily", "fontWeight", "number", "typography")

#: The type of a picture role, whose value is a picture file of the brand's version
#: (DEC-025 point 4). DTCG has no type for a file, so no token takes it.
PICTURE = "picture"

#: The types a role may have: the DTCG types format 1 reads, and a picture.
ROLE_TYPES = (*TYPES, PICTURE)

#: The folder of a brand's version that holds the files its picture roles name.
PICTURES = "pictures"

#: The keys a picture role's group may hold (DEC-025 point 4): no `$type` and no child.
_PICTURE_KEYS = ("$description", "$extensions", "$deprecated")

#: A picture file's bare name (DEC-025 point 2): lower-case letters, digits and hyphens,
#: from a letter, then its extension.
_PICTURE_NAME = re.compile(r"^[a-z][a-z0-9-]*\.(png|jpg|jpeg)$")

#: The members of a typography value, each with its type.
TYPOGRAPHY = {
    "fontFamily": "fontFamily",
    "fontSize": "dimension",
    "fontWeight": "fontWeight",
    "letterSpacing": "dimension",
    "lineHeight": "number",
}

#: The kinds of value a value axis may change (DEC-004 point 2): colours and pictures in
#: format 1.
VALUE_AXIS_TYPES = ("color", PICTURE)

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
    """A token path the brand gives no value at: no role, or a role it leaves with none."""


class RoleWithoutValue(UnknownRole, UnvaluedRole):
    """A role the scope declares that has no value under the brand: a library's own role
    whose chain of defaults reaches none, which no brand of its chain gives one. The engine
    reads it as `env.UnvaluedRole`: it names the role's library, and whether a brand of the
    chain names that library (DEC-008 points 4 and 9)."""


@dataclass(frozen=True)
class Axis:
    """A shared axis: its name, its kind (`value` or `size`), its modes and its default."""

    name: str
    kind: str
    modes: tuple[str, ...]
    default: str


@dataclass(frozen=True)
class Role:
    """A role, shared or a library's own: its token path, its type, and the role its default
    aliases, if any."""

    path: str
    type: str
    default: str | None = None


@dataclass(frozen=True)
class Pair:
    """Two colour roles that must contrast: `text` drawn on `under`, at `level`; `index`, its
    place in its file's `pairs`, from 0."""

    text: str
    under: str
    level: str
    index: int = field(default=0, compare=False)

    @property
    def minimum(self) -> float:
        return LEVELS[self.level]


@dataclass(frozen=True)
class Declarations:
    """A library's declarations, its `roles.yaml`: the foundations' shared roles, axes,
    colour families and pairs (DEC-004), or a component library's own roles and pairs
    (DEC-008 point 8).

    - `label`: `<name>@<version>` of the library they lie in, and `file` the file as
      findings name it.
    - `own`: for a library other than the foundations, its name, the group its own roles
      lie under; "" for the foundations, whose roles are shared.
    - `builds_on`: the libraries it builds on, by name.
    - `findings`: what is wrong in a library's own roles that leaves the rest usable. The
      foundations' declarations hold none: what is wrong in them refuses them.
    """

    roles: dict[str, Role]
    axes: dict[str, Axis]
    families: dict[str, dict[str, str]]
    pairs: tuple[Pair, ...]
    label: str = ""
    file: str = ""
    own: str = ""
    builds_on: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()

    @property
    def top_groups(self) -> tuple[str, ...]:
        """The first segments of the shared roles, which no library takes as its name."""
        return tuple(sorted({path.split(".")[0] for path in self.roles}))

    @property
    def major(self) -> int | None:
        """The major of the version they lie in, as `label` gives it, or None."""
        major = self.label.partition("@")[2].partition(".")[0]
        return int(major) if major.isdigit() else None


# --- the foundations' declarations --------------------------------------------------------------


def read_declarations(path: Path, *, library: str = "", shown: str = "") -> Declarations:
    """The foundations' declarations in the `roles.yaml` at `path`. `library` is
    `<name>@<version>` of the library they lie in, and `shown` the file's path as findings
    name it. Raises TokenError."""
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
    return Declarations(
        roles=roles, axes=axes, families=families, pairs=pairs, label=library, file=file
    )


#: What a library other than the foundations does not declare, with what it is for.
_FOUNDATIONS_ONLY = {"axes": "the shared axes", "families": "the colour families"}


def read_own_roles(
    path: Path,
    *,
    name: str,
    library: str = "",
    shown: str = "",
    builds_on: Iterable[str] = (),
) -> Declarations:
    """The own roles and pairs of the component library `name`, in the `roles.yaml` at
    `path` (DEC-004 point 7, DEC-008 point 8): each role under the group of its name, none
    under the group of component tokens, and each pair naming one of them. It declares no
    axes and no colour families: the foundations' alone are. `library` and `shown` are as
    for `read_declarations`, and `builds_on` names the libraries it builds on.

    Never raises: what is wrong is kept as the declarations' `findings`, and a role or a
    pair that cannot be read is left out. A default is kept as its alias says; whether it
    holds the `Scope` judges, with the libraries the role may reach."""
    file = shown or path.as_posix()
    problems = _Problems(file, library)
    roles: dict[str, Role] = {}
    pairs: tuple[Pair, ...] = ()
    try:
        data = read_bound(path, "roles")
    except (ReadError, FileError) as exc:
        problems.add("roles-unreadable", str(exc))
    else:
        for key, what in _FOUNDATIONS_ONLY.items():
            if data.get(key):
                problems.add(
                    "roles-declaration",
                    f"`{key}` lies in the `roles.yaml` of `{name}`, and only the foundations "
                    f"declare {what}: another library declares its own roles and their pairs "
                    f"alone, so the capability does not read it",
                    key,
                )
        roles = _read_roles(data.get("roles"), problems, own=name)
        pairs = _read_pairs(data.get("pairs", []), roles, problems, own=name)
    return Declarations(
        roles=roles,
        axes={},
        families={},
        pairs=pairs,
        label=library,
        file=file,
        own=name,
        builds_on=tuple(builds_on),
        findings=tuple(problems.found),
    )


def _read_roles(raw: Any, problems: _Problems, own: str = "") -> dict[str, Role]:
    """The roles `raw` maps; `own` names the library whose own roles they are, or is ""
    for the shared roles."""
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
        if own and not path.startswith(f"{own}."):
            problems.add(
                "role-name",
                f"`{path}` lies outside `{own}`, the group of the library's own roles",
                where,
            )
            continue
        if not isinstance(spec, Mapping) or spec.get("type") not in ROLE_TYPES:
            problems.add(
                "role-type", f"the role `{path}` names no type of {', '.join(ROLE_TYPES)}", where
            )
            continue
        if own and spec["type"] == PICTURE:
            problems.add(
                "role-picture",
                f"the role `{path}` is of the type `{PICTURE}`, and only the foundations "
                f"declare a picture role, so the capability does not read it",
                where,
            )
            continue
        default = spec.get("default")
        if default is not None and spec["type"] == PICTURE:
            problems.add(
                "role-default",
                f"the picture role `{path}` carries a default, and a picture role carries "
                f"none, since no brand owes it a value",
                where,
            )
            continue
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
        if role.default is None or own:
            continue  # an own role's default is the scope's to judge (`Scope`)
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


def _read_pairs(
    raw: Any, roles: Mapping[str, Role], problems: _Problems, own: str = ""
) -> tuple[Pair, ...]:
    """The pairs `raw` lists. Of the shared roles, each names two colour roles; of a
    library's own (`own`), each names one of its own roles, and whether the other is a
    colour role it may reach the `Scope` judges."""
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
        named = [r for r in (text, under) if r in roles] if own else [text, under]
        if own and is_token_path(text) and is_token_path(under) and not named:
            problems.add("pair-shape", f"pair {index} names none of the library's own roles", where)
            continue
        if not (is_token_path(text) and is_token_path(under)) or any(
            roles.get(r) is None or roles[r].type != "color" for r in named
        ):
            problems.add("pair-shape", f"pair {index} does not name two colour roles", where)
            continue
        pairs.append(Pair(text=text, under=under, level=spec["level"], index=index))
    return tuple(pairs)


# --- a scope: the roles one resolution reads ----------------------------------------------------


class Scope:
    """The roles one resolution reads (DEC-008 point 1): the foundations' shared roles, and
    the own roles of each component library resolved with them, one version of each, as
    their declarations give them. A role's type reads from it with no brand.

    - `foundations`: the foundations' declarations; `axes`, `families` and `top_groups`
      are theirs.
    - `libraries`: each component library's declarations of its own roles, by its name.
    - `roles`: every role, by its token path; `owner`, the library whose own role each is,
      or "" for a shared role.
    - `defaults`: the default of each own role that holds (DEC-008 point 3): an alias to a
      role its library may reach, its own or one of a library it builds on, the shared
      roles included where it builds on the foundations, of its type, never a component
      token, in no loop. A default that does not hold is its library's finding, and
      gives the role no value.
    - `pairs`: the foundations' pairs, then each library's that names colour roles it may
      reach.

    Its findings (`findings_of`) are each library's: those its file holds, then those its
    defaults and pairs show here. Each names the library's version."""

    def __init__(self, foundations: Declarations, libraries: Iterable[Declarations] = ()) -> None:
        self.foundations = foundations
        self.libraries = {declared.own: declared for declared in libraries if declared.own}
        self.roles: dict[str, Role] = dict(foundations.roles)
        self.owner: dict[str, str] = dict.fromkeys(foundations.roles, "")
        for name, declared in sorted(self.libraries.items()):
            for path, role in declared.roles.items():
                if path not in self.roles:
                    self.roles[path] = role
                    self.owner[path] = name
        self.defaults: dict[str, str] = {}
        self._found: dict[str, list[Finding]] = {
            name: list(declared.findings) for name, declared in self.libraries.items()
        }
        for name in sorted(self.libraries):
            self._check_defaults(name)
        self._check_loops()
        library_pairs: list[Pair] = []
        for name in sorted(self.libraries):
            library_pairs.extend(self._check_pairs(name))
            self._state_ends(name)
        self.pairs: tuple[Pair, ...] = (*foundations.pairs, *library_pairs)

    @property
    def axes(self) -> dict[str, Axis]:
        return self.foundations.axes

    @property
    def families(self) -> dict[str, dict[str, str]]:
        return self.foundations.families

    @property
    def top_groups(self) -> tuple[str, ...]:
        return self.foundations.top_groups

    def type_of(self, token_path: str) -> str:
        """The type of the role at `token_path`, shared or a library's own. Raises
        UnknownRole for a path no declaration of the scope holds."""
        if token_path not in self.roles:
            raise UnknownRole(token_path)
        return self.roles[token_path].type

    def default_of(self, token_path: str) -> str | None:
        """The role the default of the role at `token_path` aliases: a shared role's as the
        foundations declare it, an own role's where it holds; None for none."""
        if self.owner.get(token_path):
            return self.defaults.get(token_path)
        role = self.roles.get(token_path)
        return role.default if role is not None else None

    def findings_of(self, name: str) -> list[Finding]:
        """The findings of the library `name`'s own roles in this scope."""
        return list(self._found.get(name, []))

    @property
    def findings(self) -> list[Finding]:
        """The findings of every library's own roles in this scope, by the libraries'
        names."""
        return [finding for name in sorted(self._found) for finding in self._found[name]]

    def reach(self, name: str) -> set[str]:
        """The roles the library `name` may alias or pair with: its own, and those of each
        library it builds on that the scope holds, the shared roles where it builds on the
        foundations (DEC-008 point 3)."""
        declared = self.libraries[name]
        reached = set(declared.roles)
        for other in declared.builds_on:
            if other == FOUNDATIONS:
                reached.update(self.foundations.roles)
            elif other in self.libraries:
                reached.update(self.libraries[other].roles)
        return reached

    def _add(self, name: str, code: str, message: str, where: str, level: str = FAILS) -> None:
        declared = self.libraries[name]
        self._found[name].append(
            Finding(code, level, message, file=declared.file, where=where, library=declared.label)
        )

    def _check_defaults(self, name: str) -> None:
        """Each default of the library's own roles, against the roles it may reach."""
        reach = self.reach(name)
        for path, role in sorted(self.libraries[name].roles.items()):
            target = role.default
            if target is None:
                continue
            where = f"roles.{path}"
            if target == COMPONENT or target.startswith(f"{COMPONENT}."):
                self._add(
                    name,
                    "role-default",
                    f"the default of `{path}` aliases `{target}`, a component token: a role "
                    f"defaults to a role, never to the token of one part",
                    where,
                )
            elif target in reach and self.roles[target].type != role.type:
                self._add(
                    name,
                    "role-default",
                    f"the default of `{path}` aliases `{target}`, of type "
                    f"`{self.roles[target].type}`, not `{role.type}`",
                    where,
                )
            elif target in reach:
                self.defaults[path] = target
            elif target in self.roles:
                holder = self.owner[target] or FOUNDATIONS
                self._add(
                    name,
                    "role-default",
                    f"the default of `{path}` aliases `{target}`, a role of `{holder}`, which "
                    f"`{name}` does not build on",
                    where,
                )
            else:
                self._add(
                    name,
                    "default-dangling",
                    f"the default of `{path}` aliases `{target}`, which neither `{name}` nor a "
                    f"library it builds on declares",
                    where,
                )

    def _check_loops(self) -> None:
        """Each loop of defaults, at each own role in it; its defaults then give no value."""
        looped: set[str] = set()
        for start in sorted(self.defaults):
            chain = [start]
            current = start
            while current in self.defaults and current not in looped:
                current = self.defaults[current]
                if current in chain:
                    loop = chain[chain.index(current) :]
                    shown = " → ".join((*loop, current))
                    for path in loop:
                        looped.add(path)
                        self._add(
                            self.owner[path],
                            "default-loop",
                            f"the defaults make a loop: {shown}",
                            f"roles.{path}",
                        )
                    break
                chain.append(current)
        for path in looped:
            del self.defaults[path]

    def _check_pairs(self, name: str) -> list[Pair]:
        """The library's pairs that name colour roles it may reach; each one, at its
        defaults, rests on a pair the foundations, the library or a library it builds on
        declares, in either order, at a level that needs as much contrast or more (DEC-008
        point 6). A pair with an own role that has no default is judged only at the brands
        that give that role a value."""
        declared = self.libraries[name]
        reach = self.reach(name)
        declaring = [self.foundations, declared] + [
            self.libraries[other] for other in declared.builds_on if other in self.libraries
        ]
        rests = [pair for each in declaring for pair in each.pairs]
        kept = []
        for pair in declared.pairs:
            where = f"pairs.{pair.index}"
            stray = next(
                (
                    r
                    for r in (pair.text, pair.under)
                    if r not in reach or self.roles[r].type != "color"
                ),
                None,
            )
            if stray is not None:
                self._add(
                    name,
                    "pair-shape",
                    f"pair {pair.index} names `{stray}`, which is no colour role of `{name}` or "
                    f"of a library it builds on",
                    where,
                )
                continue
            kept.append(pair)
            own = [r for r in (pair.text, pair.under) if self.owner.get(r) == name]
            if any(r not in self.defaults for r in own):
                continue
            text, under = (
                self.defaults.get(r, r) if r in own else r for r in (pair.text, pair.under)
            )
            if not any(
                {rest.text, rest.under} == {text, under} and rest.minimum >= pair.minimum
                for rest in rests
            ):
                self._add(
                    name,
                    "pair-defaults",
                    f"pair {pair.index}, `{pair.text}` on `{pair.under}`, falls at its defaults "
                    f"on `{text}` on `{under}`, which neither the foundations, `{name}` nor a "
                    f"library it builds on declares as a pair at a level as strict as "
                    f"`{pair.level}`",
                    where,
                )
        return kept

    def _state_ends(self, name: str) -> None:
        """A fact for each own role whose chain of defaults ends at no shared role, so only
        a brand that gives a value along it draws it (DEC-008 point 9). A role whose own
        default does not hold has its failing finding instead."""
        declared = self.libraries[name]
        for path, role in sorted(declared.roles.items()):
            if role.default is not None and path not in self.defaults:
                continue
            end, seen = path, {path}
            while end in self.defaults and self.defaults[end] not in seen:
                end = self.defaults[end]
                seen.add(end)
            if self.owner.get(end) == "":
                continue
            said = (
                f"`{path}` has no default"
                if end == path
                else f"the chain of defaults of `{path}` ends at `{end}`, which has none that holds"
            )
            self._add(
                name,
                "role-brand-only",
                f"{said}, so it ends at no shared role: only a brand that gives it a value "
                f"draws it",
                f"roles.{path}",
                level=FACT,
            )


def read_scope(folders: Mapping[str, Path], *, root: Path | None = None) -> Scope:
    """The scope of the library versions whose folders `folders` gives, by name: the
    foundations' declarations, and the own roles of each other library of kind `components`
    whose folder holds a `roles.yaml` (DEC-008 point 8). A library whose `library.yaml`
    cannot be read adds nothing, its own check reporting it. Where `folders` holds no
    foundations, as for a library that builds on none, the scope holds no shared role.
    Findings name files relative to `root` when given. Raises TokenError for the
    foundations' declarations."""

    def shown(path: Path) -> str:
        return path.relative_to(root).as_posix() if root is not None else path.as_posix()

    foundations = Declarations(roles={}, axes={}, families={}, pairs=())
    if FOUNDATIONS in folders:
        roles = folders[FOUNDATIONS] / "roles.yaml"
        foundations = read_declarations(
            roles, library=f"{FOUNDATIONS}@{roles.parent.name}", shown=shown(roles)
        )
    own = []
    for name, folder in sorted(folders.items()):
        path = folder / "roles.yaml"
        if name == FOUNDATIONS or not path.is_file():
            continue
        try:
            library = read_library(folder)
        except LibraryError:
            continue
        if library.kind != "components":
            continue
        own.append(
            read_own_roles(
                path,
                name=library.name,
                library=library.label,
                shown=shown(path),
                builds_on=[need.name for need in library.builds_on],
            )
        )
    return Scope(foundations, own)


# --- a brand ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    """A token as one file writes it: its type, given or passed down by its group in that
    file, its value, its extensions and the file; the library whose file holds it
    (`owner`, its label, or "" for a shared role's default), and how findings name that
    library's version folder (`prefix`)."""

    path: str
    type: str | None
    value: Any
    extensions: Mapping[str, Any]
    file: str
    owner: str = ""
    prefix: str = ""

    @property
    def shown(self) -> str:
        """The token's file, as findings name it."""
        return f"{self.prefix}{self.file}"


@dataclass(frozen=True)
class _View:
    """The tokens of one combination before aliases are resolved (DEC-004 point 6, DEC-008
    point 1): the token that gives each role its value, whichever library of the chain
    writes it or the role's default; `merged`, the same before each own role's default that
    reaches no value is left out; each library's private tokens, by its label; and the
    libraries each brand of the chain names, by its label."""

    roles: dict[str, _Token]
    merged: dict[str, _Token]
    private: dict[str, dict[str, _Token]]
    named: dict[str, frozenset[str]]


@dataclass(frozen=True)
class _Resolved:
    type: str
    value: Any


class _Problem(Exception):
    """A token that cannot be resolved; `shown` is its file as findings name it."""

    def __init__(self, code: str, message: str, shown: str, where: str) -> None:
        super().__init__(message)
        self.code, self.message, self.shown, self.where = code, message, shown, where


class Brand:
    """One brand version, read and checked against the roles of a scope (`Scope`), over its
    base when it builds on one.

    - `name`, `version`, `label` (`<name>@<version>`): as its `library.yaml` gives them.
    - `scope`: the roles it is resolved against.
    - `axes`: the axes it has, each a key's axis: every shared value axis, whole, whether
      it varies it or not, and each shared size axis it or its base gives, with the modes
      given (DEC-021 point 2). They are the axes and modes it exports (DEC-004 point 5).
    - `named`: the libraries of the scope it names among those it builds on, by the major
      their version fits, whose roles it reaches (DEC-008 point 4).
    - `roles`: the token paths it exports, in path order: the shared roles, each shared
      picture role only where it or its base gives it a value (DEC-025 point 4), and each
      role of a library it names that it or its base gives a value (DEC-008 point 5).
    - `valued`: every role with a value in every combination, in path order: its exports,
      and each other role of the scope's libraries, at its default. The document of values
      holds these (DEC-005 point 7). A picture role is none of them, since the document
      has no form for a file yet (DEC-025 point 4).
    - `open`: its open roles, as its `library.yaml` lists them.
    - `opened`: the roles a brand built on it may give values: those its open roles name,
      narrowed to those its base opens to it.
    - `base`: the brand it builds on as its base, read, or None.
    - `findings`: what is wrong, leaving it usable: its own, then its base's.
    - `facts`: what its version states, and no piece: each shared picture role it gives no
      value, once (DEC-025 point 9). The check of the version alone reports them, apart
      from `findings`, which a piece's lock reads too.
    """

    def __init__(
        self,
        *,
        name: str,
        version: str,
        folder: Path,
        scope: Scope,
        axes: dict[str, Axis],
        named: frozenset[str],
        roles: tuple[str, ...],
        valued: tuple[str, ...],
        open_roles: tuple[str, ...],
        opened: frozenset[str],
        base: Brand | None,
        views: dict[str, _View],
        resolved: dict[str, dict[str, _Resolved]],
        hidden: dict[str, dict[str, _Resolved]],
        fonts: dict[str, Path | None],
        findings: tuple[Finding, ...],
        facts: tuple[Finding, ...],
    ) -> None:
        self.name = name
        self.version = version
        self.folder = folder
        self.scope = scope
        self.axes = axes
        self.named = named
        self.roles = roles
        self.valued = valued
        self.open = open_roles
        self.opened = opened
        self.base = base
        self.findings = findings
        self.facts = facts
        self._views = views
        self._resolved = resolved
        self._hidden = hidden
        self._fonts = fonts

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"

    def resolve(self, token_path: str, combination: Mapping[str, str]) -> Any:
        """The value of the role at `token_path` in `combination` (an axis left out takes
        its default), aliases resolved, in canonical form: a colour `{colorSpace,
        components, alpha}`, a dimension `{value, unit}`, a font family a list of names, a
        typography its five members so, a number. Raises RoleWithoutValue for a library's
        role that has no value under the brand, UnknownRole for a path it holds no role at
        or a picture role, which no part shows yet, and keys.BadKey for a combination the
        axes do not hold."""
        if token_path not in self.valued:
            if token_path in self.scope.roles and self.scope.owner[token_path]:
                library = self.scope.owner[token_path]
                raise RoleWithoutValue(token_path, library, named=self.names(library))
            raise UnknownRole(token_path)
        key = keys.key_of(combination, self.axes)
        return self._resolved[key][token_path].value

    def names(self, library: str) -> bool:
        """Whether the brand, or a brand of the chain below it, names the library `library`
        among those it builds on (DEC-008 point 4). A role of such a library that has no
        value is that brand's finding (`library-role-missing`), or its library's where its
        default does not hold."""
        brand: Brand | None = self
        while brand is not None:
            if library in brand.named:
                return True
            brand = brand.base
        return False

    def type_of(self, token_path: str) -> str:
        """The DTCG type of the role at `token_path`, as its declaration gives it, whether
        the brand gives it a value or not (`Scope.type_of`). Raises UnknownRole."""
        return self.scope.type_of(token_path)

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
    scope: Scope | Declarations,
    *,
    fonts: Path | None = None,
    root: Path | None = None,
    locked: Mapping[str, Path] | None = None,
) -> Brand:
    """The brand whose version folder is `folder`, read and checked against `scope`, or
    against the foundations' declarations alone, over its base when it marks one. `fonts`
    is the location's folder of fonts a brand names by hash. `locked` gives the version
    folder of each library the lock names, by its name; a base is read from it. Findings
    name files relative to `root` when given, else to the version folder they lie in.
    Raises TokenError."""
    shown = _shown(folder, root)
    try:
        library = read_bound(folder / "library.yaml", "library")
    except (ReadError, FileError) as exc:
        raise TokenError([_unreadable(exc, folder, shown)]) from exc
    if isinstance(scope, Declarations):
        scope = Scope(scope)
    reader = _BrandReader(folder, scope, library, shown, fonts, root, locked or {}, ())
    return reader.read()


def _shown(folder: Path, root: Path | None) -> str:
    """How findings name a version folder: relative to `root`, or "" without one."""
    return folder.relative_to(root).as_posix() + "/" if root is not None else ""


def _unreadable(exc: Exception, folder: Path, shown: str) -> Finding:
    """A brand whose `library.yaml` cannot be read, naming the version its folder holds,
    `libraries/<name>/<version>/`, so its level is read where it lies."""
    return Finding(
        "brand-unreadable",
        FAILS,
        str(exc),
        file=f"{shown}library.yaml",
        library=f"{folder.parent.name}@{folder.name}",
    )


def _named(raw: Any, scope: Scope) -> frozenset[str]:
    """The libraries of `scope` that a `builds-on`, `raw`, names by the major their version
    there fits (DEC-008 point 4)."""
    return frozenset(
        entry["name"]
        for entry in (raw if isinstance(raw, list) else [])
        if isinstance(entry, Mapping)
        and entry.get("name") in scope.libraries
        and isinstance(entry.get("major"), int)
        and not isinstance(entry.get("major"), bool)
        and entry["major"] == scope.libraries[entry["name"]].major
    )


class _BrandReader:
    """Reads one brand version; collects what it finds as findings. `chain` names the
    brands built on it that are being read, the last built on it directly."""

    def __init__(
        self,
        folder: Path,
        scope: Scope,
        library: Mapping[str, Any],
        shown: str,
        fonts: Path | None,
        root: Path | None,
        locked: Mapping[str, Path],
        chain: tuple[str, ...],
    ) -> None:
        self.folder = folder
        self.scope = scope
        self.library = library
        self.name = str(library.get("name"))
        self.label = f"{library.get('name')}@{library.get('version')}"
        self.named = _named(library.get("builds-on"), scope)
        self.shown = shown
        self.fonts_folder = fonts
        self.root = root
        self.locked = locked
        self.chain = chain
        self.pictures = frozenset(
            path for path, role in scope.foundations.roles.items() if role.type == PICTURE
        )
        self.fatal: list[Finding] = []
        self.kept: list[Finding] = []
        self.flat: dict[str, dict[str, _Token]] = {}

    # findings

    def _finding(
        self,
        code: str,
        message: str,
        file: str = "",
        where: str = "",
        level: str = FAILS,
        *,
        shown: str | None = None,
        fix: str = "",
        who: str = "",
    ) -> Finding:
        """A finding of this brand version; `shown`, when given, names its file as it is,
        such as a token file of its base."""
        return Finding(
            code,
            level,
            message,
            file=shown if shown is not None else f"{self.shown}{file}",
            where=where,
            fix=fix,
            library=self.label,
            who=who,
        )

    def _fail(self, code: str, message: str, file: str = "", where: str = "") -> None:
        self.fatal.append(self._finding(code, message, file, where))

    def _fail_problem(self, problem: _Problem) -> None:
        self.fatal.append(
            self._finding(problem.code, problem.message, where=problem.where, shown=problem.shown)
        )

    def _keep(
        self,
        code: str,
        message: str,
        file: str = "",
        where: str = "",
        level: str = FAILS,
        *,
        shown: str | None = None,
        fix: str = "",
        who: str = "",
    ) -> None:
        self.kept.append(
            self._finding(code, message, file, where, level, shown=shown, fix=fix, who=who)
        )

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
        base = self._read_base(library.get("builds-on"))
        resolver = self._read_resolver(library.get("resolver"), base)
        if self.fatal or resolver is None:
            raise TokenError(self._unique(self.fatal))
        order, sets, modifiers = resolver
        axes = self._axes(modifiers, base)
        views: dict[str, _View] = {}
        resolved: dict[str, dict[str, _Resolved]] = {}
        hidden: dict[str, dict[str, _Resolved]] = {}
        everything = keys.combinations({axis.name: axis.modes for axis in axes.values()}, axes)
        for combination in everything:
            key = keys.key_of(combination, axes)
            sources = self._sources(order, sets, modifiers, combination, base)
            views[key] = self._view(sources, base, key)
            resolved[key], hidden[key] = self._resolve_combination(views[key], key)
        if self.fatal:
            raise TokenError(self._unique(self.fatal))
        self._check_value_axes(axes, views, resolved, hidden)
        if self.fatal:
            raise TokenError(self._unique(self.fatal))
        self._check_library_tokens()
        self._check_library_roles(resolved, base)
        self._check_pictures()
        open_roles, opened = self._check_open(library.get("open", []), base)
        fonts = self._read_fonts(resolved, hidden, base)
        self._check_pairs(views, resolved, base)
        valued = tuple(
            path
            for path in sorted(self.scope.roles)
            if path not in self.pictures and all(path in r for r in resolved.values())
        )
        pictures = {path for path in self.pictures if any(path in r for r in resolved.values())}
        exported = tuple(
            sorted(
                {
                    path
                    for path in valued
                    if not self.scope.owner[path]
                    or any(path in view.roles and view.roles[path].owner for view in views.values())
                }
                | pictures
            )
        )
        return Brand(
            name=self.name,
            version=str(library.get("version")),
            folder=self.folder,
            scope=self.scope,
            axes=axes,
            named=self.named,
            roles=exported,
            valued=valued,
            open_roles=open_roles,
            opened=opened,
            base=base,
            views=views,
            resolved=resolved,
            hidden=hidden,
            fonts=fonts,
            findings=(*self._unique(self.kept), *(base.findings if base is not None else ())),
            facts=tuple(
                self._finding(
                    "picture-role-unvalued",
                    f"the brand gives the shared picture role `{path}` no value, which no "
                    f"brand owes it",
                    where=path,
                    level=FACT,
                )
                for path in sorted(self.pictures - pictures)
            ),
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

    # the base

    def _read_base(self, raw: Any) -> Brand | None:
        """The brand that `builds-on` marks as the base, read first from the folder the lock
        gives; None when it marks none, or when the base cannot be read, failing why."""
        marked = (
            [entry for entry in raw if isinstance(entry, Mapping) and "base" in entry]
            if isinstance(raw, list)
            else []
        )
        if not marked:
            return None
        name, major = marked[0].get("name"), marked[0].get("major")
        if (
            len(marked) > 1
            or marked[0].get("base") is not True
            or not is_name(name)
            or not isinstance(major, int)
            or isinstance(major, bool)
        ):
            self._fail(
                "base-shape",
                "`builds-on` does not mark one base as `{name, major, base: true}`: a brand "
                "has at most one base",
                "library.yaml",
                "builds-on",
            )
            return None
        if name == self.name or name in self.chain:
            loop = " → ".join((*self.chain, self.name, name))
            self._fail(
                "base-loop", f"the brands build on each other: {loop}", "library.yaml", "builds-on"
            )
            return None
        folder = self.locked.get(name)
        if folder is None or not (folder / "library.yaml").is_file():
            self._fail_lock(
                f"{self.label} builds on its base `{name}` {major}, and the lock names no "
                f"version of it the project holds",
                f"name a version of `{name}` of major {major} in the lock",
            )
            return None
        shown = _shown(folder, self.root)
        try:
            data = read_bound(folder / "library.yaml", "library")
        except (ReadError, FileError) as exc:
            self.fatal.append(_unreadable(exc, folder, shown))
            return None
        if data.get("kind") != "brand":
            self._fail(
                "base-kind",
                f"the base `{name}` of {self.label} is not a brand (`kind: {data.get('kind')}`): "
                f"a brand builds only on a brand as its base",
                "library.yaml",
                "builds-on",
            )
            return None
        version = str(data.get("version"))
        if version.partition(".")[0] != str(major):
            self._fail_lock(
                f"the lock names {name}@{version}, but {self.label} builds on its base `{name}` "
                f"{major}",
                f"name a version of `{name}` of major {major} in the lock",
            )
            return None
        reader = _BrandReader(
            folder,
            self.scope,
            data,
            shown,
            self.fonts_folder,
            self.root,
            self.locked,
            (*self.chain, self.name),
        )
        try:
            return reader.read()
        except TokenError as exc:
            self.fatal.extend(exc.findings)
            return None

    def _fail_lock(self, message: str, fix: str) -> None:
        """A base the lock does not give at the major the brand builds on: a fault only the
        lock that combines the versions shows, so it names no version and always fails
        (DEC-002 point 7)."""
        self.fatal.append(
            Finding(
                "base-lock",
                FAILS,
                message,
                file=f"{self.shown}library.yaml",
                where="builds-on",
                fix=fix,
            )
        )

    # the Resolver document

    def _read_resolver(
        self, path: Any, base: Brand | None
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
        modifiers = self._read_modifiers(raw_modifiers, rel, base)
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

    def _read_modifiers(
        self, raw: Any, rel: str, base: Brand | None
    ) -> dict[str, dict[str, tuple[str, ...]]]:
        """Each modifier, one of the shared axes, by the contexts of the modes it gives, the
        axis's default among them (DEC-004 point 1); a brand built on another keeps its
        base's axes, modes and defaults (DEC-004 point 6), and adds or changes none."""
        if not isinstance(raw, Mapping):
            self._fail("resolver-shape", "`modifiers` is not an object", rel, "modifiers")
            return {}
        axes = base.axes if base is not None else self.scope.axes
        modifiers = {}
        for name, spec in raw.items():
            where = f"modifiers.{name}"
            axis = axes.get(name)
            if axis is None and base is not None:
                self._fail(
                    "base-axis",
                    f"the modifier `{name}` adds an axis, and a brand built on {base.label} "
                    f"varies only its base's axes: {', '.join(sorted(axes))}",
                    rel,
                    where,
                )
                continue
            if axis is None:
                self._fail(
                    "brand-axis",
                    f"the modifier `{name}` is no shared axis; format 1 reads no axis of a "
                    f"brand's own (the shared axes: {', '.join(sorted(self.scope.axes))})",
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
            added = sorted(set(contexts) - set(axis.modes)) if isinstance(contexts, Mapping) else []
            if base is not None and added:
                self._fail(
                    "base-axis",
                    f"the modifier `{name}` adds the mode {', '.join(f'`{m}`' for m in added)}, "
                    f"and a brand built on {base.label} varies only its base's modes of "
                    f"`{name}`: {', '.join(axis.modes)}",
                    rel,
                    f"{where}.contexts",
                )
                continue
            if base is not None and spec.get("default") != axis.default:
                self._fail(
                    "base-axis",
                    f"the modifier `{name}` changes the default to `{spec.get('default')}`, "
                    f"and a brand built on {base.label} keeps its base's default, "
                    f"`{axis.default}`",
                    rel,
                    f"{where}.default",
                )
                continue
            if not isinstance(contexts, Mapping) or added:
                self._fail(
                    "brand-axis",
                    f"the modifier `{name}` must have one context for each mode it gives, "
                    f"each a mode of the axis: {', '.join(axis.modes)}",
                    rel,
                    f"{where}.contexts",
                )
                continue
            if axis.default not in contexts:
                self._fail(
                    "brand-axis",
                    f"the modifier `{name}` must give the axis's default, `{axis.default}`, "
                    f"among its contexts",
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
                if mode in contexts
            }
        return modifiers

    def _axes(
        self, modifiers: Mapping[str, Mapping[str, tuple[str, ...]]], base: Brand | None
    ) -> dict[str, Axis]:
        """The axes the brand has (DEC-021 point 2): its base's, where it builds on one;
        else every shared value axis, whole, and each shared size axis a modifier varies,
        with the modes that modifier gives, in the order the foundations declare them."""
        if base is not None:
            return dict(base.axes)
        return {
            name: axis
            if axis.kind == "value"
            else Axis(
                name=name,
                kind=axis.kind,
                modes=tuple(mode for mode in axis.modes if mode in modifiers[name]),
                default=axis.default,
            )
            for name, axis in self.scope.axes.items()
            if axis.kind == "value" or name in modifiers
        }

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
            if path in self.pictures:
                self._picture(child, path, file)
            elif "$value" in child:
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
        self.flat[file][path] = _Token(
            path, type_, node["$value"], extensions, file, owner=self.label, prefix=self.shown
        )

    def _picture(self, node: Mapping[str, Any], path: str, file: str) -> None:
        """The value of the picture role at `path` (DEC-025 point 4): an empty group, since
        DTCG has no type for a file, whose `$extensions` name the file by its bare name in
        the capability's extension key, `{"file": "<name>"}`, and alias nothing. It is kept
        as a token of the type `picture`, so it merges as a token does."""
        shape = (
            f"`{path}` is a picture role, so its value is an empty group whose `$extensions` "
            f'hold `{EXTENSION}` as `{{"file": "<name>"}}`'
        )
        stray = next((key for key in node if key not in _PICTURE_KEYS), None)
        extensions = node.get("$extensions")
        given = extensions.get(EXTENSION) if isinstance(extensions, Mapping) else None
        if stray is not None or not isinstance(given, Mapping) or set(given) != {"file"}:
            held = f", and it holds `{stray}`" if stray is not None else ""
            self._fail("picture-shape", f"{shape}{held}", file, path)
            return
        name = given["file"]
        if not isinstance(name, str) or _PICTURE_NAME.match(name) is None:
            self._fail(
                "picture-name",
                f"`{path}` names `{name}`, which is no picture file's bare name: lower-case "
                f"letters, digits and hyphens, from a letter, then `.png`, `.jpg` or `.jpeg`",
                file,
                path,
            )
            return
        self.flat[file][path] = _Token(
            path, PICTURE, name, {}, file, owner=self.label, prefix=self.shown
        )

    # resolution

    def _sources(
        self,
        order: tuple[tuple[str, str], ...],
        sets: Mapping[str, tuple[str, ...]],
        modifiers: Mapping[str, Mapping[str, tuple[str, ...]]],
        combination: Mapping[str, str],
        base: Brand | None,
    ) -> list[str]:
        """The brand's sources for `combination`, in resolution order. At a mode a modifier
        does not give, it takes the sources of the axis's default; in a brand built on
        another, none, so its base's values hold there (DEC-004 point 2)."""
        files: list[str] = []
        for kind, name in order:
            if kind == "sets":
                files.extend(sets[name])
                continue
            contexts, mode = modifiers[name], combination[name]
            if mode not in contexts and base is None:
                mode = self.scope.axes[name].default
            files.extend(contexts.get(mode, ()))
        return files

    def _view(self, sources: list[str], base: Brand | None, key: str) -> _View:
        """The tokens of the combination `key` before aliases are resolved: the base's, or
        the roles' defaults without a base, then the brand's own sources in order, later
        winning (DEC-008 point 1). A role its base does not open keeps the base's token, a
        finding. A token at a role of a library the brand does not name, or of another type
        than the role, stays private (DEC-008 point 4)."""
        if base is None:
            merged = {
                path: _Token(path, role.type, f"{{{default}}}", {}, "", prefix=self.shown)
                for path, role in self.scope.roles.items()
                if (default := self.scope.default_of(path)) is not None
            }
            below: dict[str, dict[str, _Token]] = {}
            named: dict[str, frozenset[str]] = {}
        else:
            under = base._views[key]
            merged, below, named = dict(under.merged), under.private, under.named
        own: dict[str, _Token] = {}
        for file in sources:
            for path, token in self.flat.get(file, {}).items():
                library = self.scope.owner.get(path)
                if (
                    library is None
                    or (library and library not in self.named)
                    or (library and token.type not in (None, self.scope.roles[path].type))
                ):
                    own[path] = token
                elif base is None or path in base.opened:
                    merged[path] = token
                else:
                    why = (
                        f"does not name `{library}`, so it opens none of its roles"
                        if library and library not in base.named
                        else "does not open it to the brand"
                    )
                    holds = (
                        "the base's value or the role's default" if library else "the base's value"
                    )
                    self._keep(
                        "role-not-open",
                        f"the brand gives `{path}` a value, but its base {base.label} {why}, so "
                        f"{holds} holds; it opens: {', '.join(sorted(base.opened)) or 'nothing'}",
                        where=path,
                        shown=token.shown,
                        fix=f"take `{path}` out of {token.file}",
                    )
        return _View(
            self._pruned(merged),
            merged,
            {**below, self.label: own},
            {**named, self.label: self.named},
        )

    def _pruned(self, merged: Mapping[str, _Token]) -> dict[str, _Token]:
        """`merged` without each library role's default whose chain reaches no value: such
        a role has none under the brand (DEC-008 point 1)."""
        roles = dict(merged)
        while True:
            gone = [
                path
                for path, token in roles.items()
                if self._is_default(path, token) and self._alias(token.value) not in roles
            ]
            if not gone:
                return roles
            for path in gone:
                del roles[path]

    def _is_default(self, path: str, token: _Token) -> bool:
        """Whether `token` is the default of a library's own role, which no brand writes."""
        return token.owner == "" and bool(self.scope.owner.get(path))

    def _resolve_combination(
        self, view: _View, key: str
    ) -> tuple[dict[str, _Resolved], dict[str, _Resolved]]:
        """Every role with a value in the combination `key`, resolved, and every private
        token of this brand; a base's private tokens are resolved only where an alias leads.
        A library role's default that leads to no value of its type leaves the role with
        none; a brand's value for it of another type is a finding, and gives it none."""
        self._check_paths(view)
        done: dict[tuple[str, str], _Resolved] = {}
        resolved: dict[str, _Resolved] = {}
        hidden: dict[str, _Resolved] = {}
        for path, token in view.roles.items():
            try:
                resolved[path] = self._resolve(("", path), view, done, ())
            except _Problem as problem:
                if not self._is_default(path, token):
                    self._fail_problem(problem)
        for path in view.private[self.label]:
            try:
                hidden[path] = self._resolve((self.label, path), view, done, ())
            except _Problem as problem:
                self._fail_problem(problem)
        for role in self.scope.foundations.roles.values():
            found = resolved.get(role.path)
            if role.path not in view.roles and role.type == PICTURE:
                continue  # no brand owes a picture role a value (DEC-025 point 4)
            if role.path not in view.roles:
                self._fail(
                    "role-missing",
                    f"the brand gives the role `{role.path}` no value in the combination `{key}`",
                    "",
                    role.path,
                )
            elif found is not None and found.type != role.type:
                self.fatal.append(
                    self._finding(
                        "role-type",
                        f"the role `{role.path}` is of type `{role.type}`, but the brand gives "
                        f"it a `{found.type}` in the combination `{key}`",
                        where=role.path,
                        shown=view.roles[role.path].shown,
                    )
                )
        for path, found in list(resolved.items()):
            role = self.scope.roles.get(path)
            if role is None or not self.scope.owner[path] or found.type == role.type:
                continue
            del resolved[path]
            token = view.roles[path]
            if token.owner == self.label:
                self._keep(
                    "library-token",
                    f"`{path}`, a role of `{self.scope.owner[path]}` of type `{role.type}`, is "
                    f"given a `{found.type}` in the combination `{key}`, so it gives the role "
                    f"no value",
                    where=path,
                    shown=token.shown,
                )
        return resolved, hidden

    def _check_paths(self, view: _View) -> None:
        shared_groups = set(self.scope.top_groups)
        tokens = {
            path: token for path, token in view.roles.items() if not self._is_default(path, token)
        }
        tokens.update(view.private[self.label])
        for path, token in tokens.items():
            if (
                token.owner == self.label
                and path.split(".")[0] in shared_groups
                and path not in self.scope.foundations.roles
            ):
                self._fail(
                    "token-shared-group",
                    f"`{path}` lies in the shared group `{path.split('.')[0]}` but is no shared "
                    f"role; a brand's own tokens lie in groups of their own",
                    token.file,
                    path,
                )
            for other in tokens:
                if other.startswith(f"{path}."):
                    self.fatal.append(
                        self._finding(
                            "tokens-shape",
                            f"`{path}` is a token in one file and a group in another",
                            where=path,
                            shown=token.shown,
                        )
                    )
                    break

    def _resolve(
        self,
        ref: tuple[str, str],
        view: _View,
        done: dict[tuple[str, str], _Resolved],
        chain: tuple[tuple[str, str], ...],
    ) -> _Resolved:
        """The value of the token `ref` names: `("", <role>)` for an exported role,
        `(<library>, <path>)` for a library's private token."""
        if ref in done:
            return done[ref]
        scope, path = ref
        token = view.private[scope][path] if scope else view.roles[path]
        if ref in chain:
            loop = " → ".join(step for _, step in (*chain[chain.index(ref) :], ref))
            raise _Problem("alias-loop", f"the aliases make a loop: {loop}", token.shown, path)
        chain = (*chain, ref)
        target = self._alias(token.value)
        if target is not None:
            found = self._resolve(self._target(token, target, path, view), view, done, chain)
            if found.type == PICTURE:
                raise _Problem(
                    "alias-type",
                    f"`{path}` aliases `{target}`, a picture role, whose value is a group no "
                    f"token aliases",
                    token.shown,
                    path,
                )
            if token.type is not None and token.type != found.type:
                raise _Problem(
                    "alias-type",
                    f"`{path}` is of type `{token.type}` but aliases `{target}`, of type "
                    f"`{found.type}`",
                    token.shown,
                    path,
                )
            done[ref] = found
            return found
        if token.type is None:
            raise _Problem(
                "token-type",
                f"`{path}` has no `$type`, and its group gives none",
                token.shown,
                path,
            )
        if token.type == PICTURE:
            value = token.value  # the file's bare name, read with its group (`_picture`)
        elif token.type == "typography":
            value = self._typography(token, view, done, chain)
        else:
            value = _canonical(token.type, token.value, token.shown, path)
        found = _Resolved(token.type, value)
        done[ref] = found
        return found

    def _target(self, token: _Token, target: str, where: str, view: _View) -> tuple[str, str]:
        """Where an alias in `token`, at `where`, leads: a role, or a private token of the
        library that writes `token` (DEC-004 point 6). A brand's token reaches a library's
        role only where that brand names the library; a default reaches any role (DEC-008
        point 4). Raises _Problem for an alias into another library's private token, or one
        that leads nowhere."""
        library = self.scope.owner.get(target)
        if target in view.private.get(token.owner, {}) and (
            target not in view.roles or (library and library not in view.named[token.owner])
        ):
            return (token.owner, target)
        if target in view.roles and (
            not library or token.owner == "" or library in view.named[token.owner]
        ):
            return ("", target)
        if library and token.owner:
            why = (
                "which has no value under the brand"
                if library in view.named[token.owner]
                else f"which {token.owner} does not name among the libraries it builds on"
            )
            raise _Problem(
                "alias-dangling",
                f"`{where}` aliases `{target}`, a role of `{library}`, {why}",
                token.shown,
                token.path,
            )
        holder = next(
            (owner for owner, held in view.private.items() if target in held),
            None,
        )
        if holder is not None:
            raise _Problem(
                "alias-private",
                f"`{where}` aliases `{target}`, which {holder} keeps private: a brand aliases "
                f"only the roles its base exports",
                token.shown,
                token.path,
            )
        raise _Problem(
            "alias-dangling",
            f"`{where}` aliases `{target}`, which the brand does not hold",
            token.shown,
            token.path,
        )

    def _typography(
        self,
        token: _Token,
        view: _View,
        done: dict[tuple[str, str], _Resolved],
        chain: tuple[tuple[str, str], ...],
    ) -> dict[str, Any]:
        raw = token.value
        if not isinstance(raw, Mapping) or set(raw) != set(TYPOGRAPHY):
            raise _Problem(
                "token-value",
                f"`{token.path}` is a typography, which holds exactly {', '.join(TYPOGRAPHY)}",
                token.shown,
                token.path,
            )
        value = {}
        for member, type_ in TYPOGRAPHY.items():
            target = self._alias(raw[member])
            where = f"{token.path}.{member}"
            if target is None:
                value[member] = _canonical(type_, raw[member], token.shown, where)
                continue
            found = self._resolve(self._target(token, target, where, view), view, done, chain)
            if found.type != type_:
                raise _Problem(
                    "alias-type",
                    f"`{where}` must be a `{type_}`, but aliases a `{found.type}`",
                    token.shown,
                    token.path,
                )
            value[member] = found.value
        return value

    @staticmethod
    def _alias(value: Any) -> str | None:
        match = _ALIAS.match(value) if isinstance(value, str) else None
        return match.group(1) if match else None

    # checks across combinations

    def _check_value_axes(
        self,
        axes: Mapping[str, Axis],
        views: Mapping[str, _View],
        resolved: Mapping[str, Mapping[str, _Resolved]],
        hidden: Mapping[str, Mapping[str, _Resolved]],
    ) -> None:
        """A value axis of the brand's `axes` changes only colours. A library's role its
        library leaves at its defaults changes only as the roles they alias do, which are
        judged themselves."""
        for key in resolved:
            combination = keys.parse_key(key, axes)
            for axis in axes.values():
                if axis.kind != "value" or combination[axis.name] == axis.default:
                    continue
                at_default = keys.key_of({**combination, axis.name: axis.default}, axes)
                for values, before in (
                    (resolved[key], resolved[at_default]),
                    (hidden[key], hidden[at_default]),
                ):
                    for path in sorted(set(values) | set(before)):
                        one, other = values.get(path), before.get(path)
                        if one == other:
                            continue
                        if (
                            values is resolved[key]
                            and self.scope.owner.get(path)
                            and not self._reached(path, views[key])
                            and not self._reached(path, views[at_default])
                        ):
                            continue
                        type_ = (
                            one.type if one is not None else other.type if other is not None else ""
                        )
                        if type_ in VALUE_AXIS_TYPES:
                            continue
                        self._fail(
                            "value-axis-changes-size",
                            f"the value axis `{axis.name}` may change only colours and "
                            f"pictures, but its mode "
                            f"`{combination[axis.name]}` changes `{path}`, a `{type_}`, in the "
                            f"combination `{key}`",
                            "",
                            path,
                        )

    def _reached(self, path: str, view: _View) -> bool:
        """Whether a value a brand of the chain gives a library's own role reaches the role
        at `path` in `view`: it or a library role along its chain of defaults (DEC-008
        point 6). A role that follows its defaults to a shared role is its library's."""
        seen: set[str] = set()
        while self.scope.owner.get(path) and path not in seen:
            seen.add(path)
            token = view.roles.get(path)
            if token is None:
                return False
            if not self._is_default(path, token):
                return True
            path = self._alias(token.value) or ""
        return False

    def _check_library_tokens(self) -> None:
        """Each of the brand's tokens under the name of a library of the scope (DEC-008
        point 4): where the brand names the library, one that is none of its roles, or is
        of another type, is a finding; where it does not, the token stays private and asks
        for attention."""
        for file, tokens in sorted(self.flat.items()):
            for path, token in tokens.items():
                library = path.split(".")[0]
                declared = self.scope.libraries.get(library)
                if declared is None:
                    continue
                role = declared.roles.get(path)
                if library not in self.named:
                    self._keep(
                        "library-token-private",
                        f"`{path}` lies under `{library}`, which the brand does not name, by the "
                        f"major of {declared.label}, among the libraries it builds on, so it stays "
                        f"private and gives `{library}` nothing",
                        file,
                        path,
                        ATTENTION,
                        fix=f"name `{library}` in `builds-on` to give its roles values, or move "
                        f"`{path}` to a group of the brand's own",
                        who=f"the owner of the brand {self.name}",
                    )
                elif role is None:
                    self._keep(
                        "library-token",
                        f"`{path}` lies under `{library}`, which the brand names, but is none of "
                        f"its roles: a token under a library the brand names gives one of its "
                        f"roles a value, and the brand's private tokens lie in groups of its own",
                        file,
                        path,
                    )
                elif token.type is not None and token.type != role.type:
                    self._keep(
                        "library-token",
                        f"`{path}` is of type `{token.type}`, but the role `{path}` of `{library}` "
                        f"is of type `{role.type}`, so it gives the role no value",
                        file,
                        path,
                    )

    def _check_library_roles(
        self, resolved: Mapping[str, Mapping[str, _Resolved]], base: Brand | None
    ) -> None:
        """A brand that names a library gives each of its roles without a default a value
        in every combination (DEC-008 point 4). Where its base names the library and leaves
        the role with none too, the finding is the base's."""
        for path, role in sorted(self.scope.roles.items()):
            library = self.scope.owner[path]
            if not library or library not in self.named or role.default is not None:
                continue
            missing = [key for key, values in resolved.items() if path not in values]
            if base is not None and library in base.named:
                missing = [key for key in missing if path in base._resolved[key]]
            if not missing:
                continue
            where = (
                "in any combination"
                if len(missing) == len(resolved)
                else "in the combination"
                + ("s " if len(missing) > 1 else " ")
                + ", ".join(f"`{key}`" for key in missing)
            )
            self._keep(
                "library-role-missing",
                f"the brand names `{library}`, and gives its role `{path}`, which has no default, "
                f"no value {where}",
                "",
                path,
                fix=f"give `{path}` a value in every combination",
            )

    def _check_pictures(self) -> None:
        """Each file the brand's own picture values name is one its version holds in
        `pictures/`, found by its exact name, and no symbolic link (DEC-025 point 9). A
        base's values are its base's to judge."""
        folder = self.folder / PICTURES
        held = (
            {entry.name for entry in folder.iterdir() if entry.is_file() and not entry.is_symlink()}
            if folder.is_dir()
            else set()
        )
        for file, tokens in sorted(self.flat.items()):
            for path, token in sorted(tokens.items()):
                if token.type == PICTURE and token.value not in held:
                    self._keep(
                        "picture-missing",
                        f"the picture role `{path}` names `{token.value}`, which the brand's "
                        f"version does not hold in `{PICTURES}/`",
                        file,
                        path,
                        fix=f"add `{PICTURES}/{token.value}` to the brand's version, or name a "
                        f"file it holds there",
                    )

    def _check_open(self, raw: Any, base: Brand | None) -> tuple[tuple[str, ...], frozenset[str]]:
        """The open roles as `open` lists them, and the roles they open: those each entry
        names of the shared roles and the roles of the libraries the brand names, narrowed
        to those its base opens to it (DEC-004 point 6, DEC-008 point 4)."""
        if not isinstance(raw, list):
            self._keep("open-shape", "`open` is not a list of roles", "library.yaml", "open")
            return (), frozenset()
        openable = {
            path
            for path, library in self.scope.owner.items()
            if not library or library in self.named
        }
        open_to_it = base.opened if base is not None else frozenset(openable)
        opened: set[str] = set()
        for entry in raw:
            named = {
                path
                for path in openable
                if is_token_path(entry) and (path == entry or path.startswith(f"{entry}."))
            }
            if not named:
                library = self.scope.owner.get(
                    next(
                        (
                            path
                            for path in sorted(self.scope.roles)
                            if is_token_path(entry)
                            and (path == entry or path.startswith(f"{entry}."))
                        ),
                        "",
                    )
                )
                self._keep(
                    "open-unknown",
                    f"the open role `{entry}` names roles of `{library}`, which the brand does not "
                    f"name among the libraries it builds on, so it opens none of them"
                    if library
                    else f"the open role `{entry}` names no role the brand exports, nor a group "
                    f"of them",
                    "library.yaml",
                    "open",
                )
                continue
            closed = sorted(named - open_to_it)
            if closed and base is not None:
                self._keep(
                    "open-wider",
                    f"the open role `{entry}` opens {', '.join(f'`{p}`' for p in closed)}, which "
                    f"its base {base.label} does not open to it: a brand opens only roles open "
                    f"to it",
                    "library.yaml",
                    "open",
                    fix=f"take `{entry}` out of `open`, or name only roles {base.label} opens",
                )
            opened |= named & open_to_it
        return tuple(entry for entry in raw if isinstance(entry, str)), frozenset(opened)

    def _read_fonts(
        self,
        resolved: Mapping[str, Mapping[str, _Resolved]],
        hidden: Mapping[str, Mapping[str, _Resolved]],
        base: Brand | None,
    ) -> dict[str, Path | None]:
        """The file of each font family, the base's first, then the brand's own; a family
        a value names with no file is a finding, unless the base names it too, whose
        finding it is."""
        fonts: dict[str, Path | None] = dict(base._fonts) if base is not None else {}
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
        named = _families(resolved, hidden)
        if base is not None:
            named -= _families(base._resolved, base._hidden)
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

    def _check_pairs(
        self,
        views: Mapping[str, _View],
        resolved: Mapping[str, Mapping[str, _Resolved]],
        base: Brand | None,
    ) -> None:
        """Each pair of the scope in every combination; a combination where the pair is as
        its base gives it is the base's to report. A library's pair is judged only where
        the brand's values reach it, and then in every combination where both its roles
        have a value; at its defaults it is its library's (DEC-008 point 6)."""
        for pair in self.scope.pairs:
            roles = (pair.text, pair.under)
            if any(self.scope.owner.get(r) for r in roles) and not any(
                self._reached(r, view) for r in roles for view in views.values()
            ):
                continue
            for key, values in resolved.items():
                if pair.text not in values or pair.under not in values:
                    continue
                text, under = values[pair.text].value, values[pair.under].value
                below = base._resolved[key] if base is not None else {}
                if (
                    pair.text in below
                    and pair.under in below
                    and (text, under) == (below[pair.text].value, below[pair.under].value)
                ):
                    continue
                if under["alpha"] < 1:
                    self._keep(
                        "pair-translucent",
                        f"`{pair.under}` is translucent in the combination `{key}`, so the "
                        f"contrast of `{pair.text}` on it depends on what lies under it",
                        "",
                        pair.under,
                        level=ATTENTION,
                        fix=f"give `{pair.under}` an opaque colour in `{key}`, or judge the "
                        f"contrast where it is drawn",
                        who=f"the owner of the brand {self.name}",
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


def _families(*maps: Mapping[str, Mapping[str, _Resolved]]) -> set[str]:
    """The font families the resolved values name, in any combination."""
    named: set[str] = set()
    for resolved in maps:
        for values in resolved.values():
            for found in values.values():
                if found.type == "fontFamily":
                    named.update(found.value)
                elif found.type == "typography":
                    named.update(found.value["fontFamily"])
    return named


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


def _canonical(type_: str, value: Any, shown: str, where: str) -> Any:
    """`value` of `type_` in canonical form; _Problem, naming the file `shown`, when it is
    not of that type as format 1 reads it."""
    found = _canonical_or_none(type_, value)
    if found is _INVALID:
        raise _Problem("token-value", f"`{where}` is no {_SHAPES[type_]}", shown, where)
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
