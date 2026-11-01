"""The data the engine reads: libraries, components, brands, notations and pieces.

The engine knows no component by name. It reads each library's files into specs and leaves their
meaning to the layout tools.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from .text import Estimate, Face, Style
from .tokens import TokenSet, as_number, read_file

SCHEMA_VERSION = 1
ENGINE_VERSION = "0.1.0"  # the prototype's engine; libraries name it in `requires`


class EngineError(Exception):
    pass


def read_yaml(path: Path):
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise EngineError(f"missing file {path}") from e


def check_schema_version(data, path):
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise EngineError(f"{path}: schema_version must be {SCHEMA_VERSION}")


def prose_strings(schema: dict, value, path: str):
    """The strings of a value that its schema marks as prose (`x-pkit-prose: true`), with their paths."""
    if not isinstance(schema, dict):
        return
    if schema.get("x-pkit-prose") and isinstance(value, str):
        yield path, value
    if isinstance(value, dict):
        for key, sub in (schema.get("properties") or {}).items():
            if key in value:
                yield from prose_strings(sub, value[key], f"{path}/{key}" if path else key)
    elif isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            key = item.get("id", i) if isinstance(item, dict) else i
            yield from prose_strings(schema["items"], item, f"{path}/{key}")


# ---------------------------------------------------------------- components


class Spec:
    """A component, a layout or a local definition, read from data."""

    def __init__(self, data: dict, ref: str, library: "Library", kind: str | None = None):
        self.data = data
        self.ref = ref
        self.library = library
        self.name = data.get("name", ref.rsplit("/", 1)[-1])
        self.kind = kind or data.get("kind", "block")
        self.status = data.get("status")
        self.fields = data.get("fields") or {"type": "object", "properties": {}}
        self.options = {k: list(v) for k, v in (data.get("options") or {}).items()}
        self.states = dict(data.get("states") or {})
        self.colour = data.get("colour")
        self.values = dict(data.get("values") or {})
        self.preferred = dict(data.get("preferred") or {})
        self.draws = dict(data.get("draws") or {})
        self.exposes = list(data.get("exposes") or [])
        self.parts = list((data.get("parts") or {}).items())
        self.part_index = dict(self.parts)
        self.page = data.get("page")
        self.bounds = dict(data.get("bounds") or {})
        self.define = {name: Spec(d, f"{ref}#{name}", library, kind="local") for name, d in (data.get("define") or {}).items()}

    @property
    def label(self):
        return f"{self.ref}@{self.library.version}"

    def own_fields(self) -> set[str]:
        return set((self.fields.get("properties") or {}).keys())


class Library:
    def __init__(self, root: Path, name: str, version: str):
        self.name, self.version = name, version
        self.path = root / name / version
        meta_path = self.path / "library.yaml"
        if not meta_path.exists():
            raise EngineError(f"library {name} {version} is not in {root}")
        self.meta = read_yaml(meta_path)
        check_schema_version(self.meta, meta_path)
        if self.meta.get("name") != name or str(self.meta.get("version")) != version:
            raise EngineError(f"{meta_path}: name or version does not match its folder")
        self.kind = self.meta["kind"]
        needed = str((self.meta.get("requires") or {}).get("visual-communication", ENGINE_VERSION))
        if not (ENGINE_VERSION == needed or ENGINE_VERSION.startswith(needed + ".")):
            raise EngineError(f"{meta_path}: needs visual-communication {needed}; this engine is {ENGINE_VERSION}")
        self._components: dict[str, Spec] | None = None

    def file(self, rel: str) -> Path:
        return self.path / rel

    def components(self) -> dict[str, Spec]:
        if self._components is None:
            self._components = {}
            for path in sorted(self.path.rglob("*.yaml")):
                data = read_yaml(path)
                if isinstance(data, dict) and data.get("kind") in ("block", "pattern", "top"):
                    check_schema_version(data, path)
                    self._components[data["name"]] = Spec(data, f"{self.name}/{data['name']}", self)
        return self._components


class Brand:
    """A brand library: its tokens per font profile, theme and mode, its layouts and pictures."""

    def __init__(self, library: Library):
        self.library = library
        meta = library.meta
        self.tokens_meta = meta["tokens"]
        self.themes: dict[str, dict[str, str]] = self.tokens_meta["themes"]
        self.default_theme = self.tokens_meta.get("default") or next(iter(self.themes))
        self.profiles: dict[str, dict] = meta["font_profiles"]
        self.entry_points: dict[str, dict] = meta["entry_points"]
        self.pictures: dict[str, str] = meta.get("pictures") or {}
        self._sets: dict = {}
        self._faces: dict = {}

    @property
    def name(self):
        return self.library.name

    def modes(self) -> list[str]:
        return [f"{theme}/{mode}" for theme, modes in self.themes.items() for mode in modes]

    def token_files(self, profile: str, theme_mode: str) -> list[Path]:
        theme, mode = theme_mode.split("/")
        files = list(self.tokens_meta["base"]) + [self.profiles[profile]["tokens"], self.themes[theme][mode]]
        return [self.library.file(f) for f in files]

    def tokens(self, profile: str, theme_mode: str | None = None) -> TokenSet:
        theme_mode = theme_mode or f"{self.default_theme}/{next(iter(self.themes[self.default_theme]))}"
        key = (profile, theme_mode)
        if key not in self._sets:
            files = self.token_files(profile, theme_mode)
            for path, token in read_file(files[-1]).items():  # the mode's file: values only, so a mode never moves anything
                if token.type != "color":
                    raise EngineError(f"{files[-1]}: {path} is a {token.type}; a mode's file holds colours only")
            self._sets[key] = TokenSet(files)
        return self._sets[key]

    def layouts(self, entry: str) -> Spec:
        point = self.entry_points.get(entry)
        if not point:
            raise EngineError(f"brand {self.name} has no entry point {entry}")
        path = self.library.file(point["layouts"])
        data = read_yaml(path)
        check_schema_version(data, path)
        return Spec(data, f"{self.name}/{entry}", self.library, kind="layouts")

    def picture(self, name: str) -> Path | None:
        rel = self.pictures.get(name)
        return self.library.file(rel) if rel else None

    def style(self, tokens: TokenSet, name: str) -> Style:
        """A text style (`type.<name>`) with the face that measures it in this font profile."""
        path = f"type.{name}"
        value = tokens.resolve(path)
        raw = tokens.raw(path).value
        while isinstance(raw, str):  # a style that aliases another style
            raw = tokens.raw(raw.strip("{}")).value
        family_path = raw["fontFamily"].strip("{}")
        family = tokens.resolve(family_path)
        ext = tokens.extensions(family_path).get("pkit.visual", {})
        weight = int(value.get("fontWeight", 400))
        size = as_number(value["fontSize"], path)
        line_height = float(value["lineHeight"]) * size
        files = ext.get("files") or {}
        face_key = (family, weight, ext.get("measure"))
        if face_key not in self._faces:
            if files:
                rel = files.get(str(weight)) or files.get("400")
                path_ = self.library.file(rel)
                if not path_.exists():
                    raise EngineError(f"brand {self.name}: font file {rel} is missing")
                self._faces[face_key] = Face(path_, family, weight)
            elif ext.get("measure") == "estimate":
                self._faces[face_key] = Estimate(family, weight)
            else:
                raise EngineError(f"brand {self.name}: font {family} has no file and is not marked as estimated")
        return Style(name, self._faces[face_key], size, line_height, weight, ext.get("render", "text"))


class Notation:
    def __init__(self, library: Library):
        self.library = library
        data = read_yaml(library.file("concepts.yaml"))
        check_schema_version(data, library.file("concepts.yaml"))
        self.concepts: dict[str, dict] = data["concepts"]
        glossary = library.file("glossary.yaml")
        self.glossary = read_yaml(glossary) if glossary.exists() else {}

    @property
    def name(self):
        return self.library.name


# ---------------------------------------------------------------- pieces


def find_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / "libraries").is_dir():
            return folder
    raise EngineError(f"no libraries/ folder above {start}")


class Piece:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.name = self.path.name
        meta_path = self.path / "piece.yaml"
        self.meta = read_yaml(meta_path)
        check_schema_version(self.meta, meta_path)
        self.root = find_root(self.path)
        self.lock: dict[str, str] = {k: str(v) for k, v in self.meta["lock"].items()}
        self.libraries = {name: Library(self.root / "libraries", name, version) for name, version in self.lock.items()}
        top_lib, top_name = self.meta["top"].split("/")
        self.top = self.library(top_lib).components().get(top_name)
        if not self.top or self.top.kind != "top":
            raise EngineError(f"{meta_path}: top {self.meta['top']} is not a top component")
        self.brand_entry = self.meta["brand"]
        self.notations = [Notation(self.library(n)) for n in self.meta.get("notations") or []]
        self.languages: list[str] = self.meta["languages"]
        self.source = self.meta.get("source", self.languages[0])

    def library(self, name: str) -> Library:
        if name not in self.libraries:
            raise EngineError(f"piece {self.name}: library {name} is not in its lock")
        return self.libraries[name]

    def brand(self, entry: str | None = None) -> tuple[Brand, str]:
        name, point = (entry or self.brand_entry).split("/")
        return Brand(self.library(name)), point

    def preview_targets(self) -> list[tuple[str, str]]:
        """(brand entry, theme/mode) pairs the piece is drawn in for previews."""
        out = []
        for entry, modes in (self.meta.get("previews") or {self.brand_entry: None}).items():
            brand, _ = self.brand(entry)
            for mode in modes or brand.modes():
                out.append((entry, mode))
        return out

    def content_file(self, lang: str) -> Path:
        return self.path / f"content.{lang}.yaml"

    def content(self, lang: str) -> dict:
        path = self.content_file(lang)
        data = read_yaml(path)
        check_schema_version(data, path)
        if self.top.name not in data:
            raise EngineError(f"{path}: no `{self.top.name}:` at the top")
        return data[self.top.name]

    def pages(self, lang: str) -> list[dict]:
        content = self.content(lang)
        field = self.top.data.get("pages", "self")
        return [content] if field == "self" else list(content.get(field) or [])

    def content_hash(self) -> str:
        h = hashlib.sha256()
        for path in [self.path / "piece.yaml"] + [self.content_file(l) for l in self.languages]:
            h.update(path.read_bytes())
        return h.hexdigest()
