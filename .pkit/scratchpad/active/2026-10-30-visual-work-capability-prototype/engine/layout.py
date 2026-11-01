"""The layout engine: components as data, evaluated value by value into a scene.

An instance is a component with its fields (from the content), its options and the size its parent
gives it. Every value it computes (a part's frame, a named value, its preferred size) is a cell,
computed on first use in the order the references give; a loop is refused, naming it (point 19).

Each element has two sizes: the size it prefers (from its content, `preferred:`) and the size it
gets (from its parent; by default what it prefers). One owner per value: a parent may give a height
only before anything has read it.

The general tools a component may use (4a, 19, 21): formulas; references to the frames of its own
parts and of parts below; repetition over a list with the stack and row operators (gap, align,
equal sizes, shares, fill, distribute); the optional part (`when:`); lining up with one item (`line-up`) or one
line of a text (`<part>.lines.<n>`); connectors between items by id with their ends spread; and the
colour ramp (`ramp: level`).
"""

from __future__ import annotations

import copy
import re

import jsonschema

from .formula import FormulaError, evaluate, is_formula
from .model import EngineError, Spec, prose_strings
from .text import break_text, prepare, shell_runs

PRIMITIVES = ("box", "ellipse", "text", "runs", "line", "image")
GEOMETRY = {"x", "y", "width", "height", "from", "to", "when"}
RESERVED = GEOMETRY | {
    "use", "with", "draw", "repeat", "stack", "row", "ties", "slot", "style", "colour", "align", "wrap",
    "highlight", "run-colours", "decorative", "ramp", "spread", "gap", *PRIMITIVES,
}
UNIVERSAL_FIELDS = {"id": {"type": "string"}, "concept": {"type": "string"}, "state": {"type": "string"},
                    "use": {"type": "string"}, "override": {"type": "object"}}
FIELD = re.compile(r"\{([A-Za-z0-9_.\-]+)\}")
DERIVED = {"right": ("x", "width", 1.0), "bottom": ("y", "height", 1.0), "center": ("x", "width", 0.5), "middle": ("y", "height", 0.5)}


def r2(v: float) -> float:
    return round(float(v), 2)


def wrap_of(spec, inst) -> bool:
    return inst.pick(spec.get("wrap", "yes")) == "yes" and "runs" not in spec


def empty(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


class PageContext:
    """What every instance of one page shares: the brand's tokens for a font profile, the language,
    the notations, and where problems are reported."""

    def __init__(self, piece, brand, tokens, profile, lang, labels, page_id, number, count, problems):
        self.piece, self.brand, self.tokens, self.profile, self.lang = piece, brand, tokens, profile, lang
        self.labels, self.page_id, self.number, self.count = labels, page_id, number, count
        self.problems = problems
        self.prose: dict[str, str] = {}  # content path -> text, for every prose field drawn
        self._styles = {}
        self.content_file = f"content.{lang}.yaml"

    def problem(self, kind, where, message):
        entry = (kind, f"{self.content_file} {where}", message)
        if entry not in self.problems:
            self.problems.append(entry)

    def style(self, name):
        if name not in self._styles:
            if f"type.{name}" not in self.tokens:
                raise EngineError(f"no text style type.{name} in brand {self.brand.name}")
            self._styles[name] = self.brand.style(self.tokens, name)
        return self._styles[name]

    def number_token(self, path):
        if path not in self.tokens:
            raise EngineError(f"no token {path} in brand {self.brand.name}")
        return self.tokens.number(path)

    def component(self, ref: str) -> Spec:
        lib, _, name = ref.partition("/")
        spec = self.piece.library(lib).components().get(name)
        if not spec:
            raise EngineError(f"no component {ref}")
        return spec

    def concept_family(self, concept, where):
        for notation in self.piece.notations:
            if concept in notation.concepts:
                return notation.concepts[concept]["colour"]
        self.problem("REF", where, f"concept {concept!r} is in no notation of the piece")
        return None

    def colour_token(self, role, where):
        token = f"color.{role}"
        if token not in self.tokens:
            self.problem("REF", where, f"colour role {role!r} has no token in brand {self.brand.name}")
        return token


class Group:
    def __init__(self, width):
        self.width, self.height = width, 0.0
        self.items: list[tuple[str, float, float, float, float, "Instance"]] = []
        self.extras: list[tuple["Instance", float, float]] = []


class Instance:
    def __init__(self, page: PageContext, spec: Spec, fields: dict, options: dict, path: list[str], content_path: str,
                 given: dict | None = None, scope: "Instance | None" = None):
        self.page, self.spec, self.fields, self.options = page, spec, fields, options
        self.path, self.content_path, self.given, self.scope = path, content_path, dict(given or {}), scope
        self.cells: dict[str, float] = {}
        self.evaluating: list[str] = []
        self.children: dict[str, Instance] = {}
        self.groups: dict[str, Group] = {}
        self.texts: dict[str, dict] = {}
        self.tone = self._tone()

    # ------------------------------------------------------------ what it is and how it looks

    def where(self, part=None):
        return "/".join([self.content_path] + ([part] if part else []))

    def _tone(self):
        family = self.given.get("ramp") or self.spec.colour or (self.scope.tone if self.scope else None) or "neutral"
        concept = self.fields.get("concept")
        if concept:
            family = self.page.concept_family(concept, self.where()) or family
        state = self.fields.get("state")
        if state:
            if state not in self.spec.states:
                self.page.problem("SCHEMA", self.where(), f"state {state!r} is not declared by {self.spec.ref}")
            elif self.spec.states[state]:
                family = self.spec.states[state]
        return family

    def word(self, key):
        if key in self.options:
            value = self.options[key]
            return "item" if isinstance(value, dict) else value
        if self.scope and key in self.scope.options and key not in self.fields:
            return self.scope.word(key)
        value = self.fields.get(key)
        return value if isinstance(value, str) else None

    def pick(self, value):
        """A value that may switch on an option or a field: `{by: fill, plain: …, tint: …, else: …}`."""
        while isinstance(value, dict) and "by" in value:
            word = self.word(value["by"])
            if word in value:
                value = value[word]
            elif "else" in value:
                value = value["else"]
            else:
                raise EngineError(f"{self.spec.ref}: no branch for {value['by']}={word!r}")
        return value

    def colour(self, value, part):
        value = self.pick(value)
        if value in (None, "none"):
            return None
        override = (self.fields.get("override") or {}).get(part)
        if override:
            value = override
        if isinstance(value, str) and value.startswith("tone."):
            value = f"{self.tone}.{value[5:]}"
        if not isinstance(value, str) or value.startswith("#"):
            self.page.problem("SCHEMA", self.where(part), f"colour {value!r} is not a role; raw values belong to a brand")
            return None
        return self.page.colour_token(value, self.where(part))

    # ------------------------------------------------------------ fields and conditions

    def lookup(self, name):
        if name.startswith("page."):
            return {"page.number": self.page.number, "page.count": self.page.count}.get(name, "")
        if name.startswith("labels."):
            return self.page.labels.get(name[7:], "")
        if name in self.fields:
            return self.fields[name]
        if name in self.options or (self.scope and name in self.scope.options):
            return self.word(name)
        return None

    def interpolate(self, template):
        template = self.pick(template)
        if not isinstance(template, str):
            return template
        m = FIELD.fullmatch(template)
        if m:
            return self.lookup(m.group(1))
        return FIELD.sub(lambda m: "" if empty(self.lookup(m.group(1))) else str(self.lookup(m.group(1))), template).strip()

    def holds(self, cond) -> bool:
        if isinstance(cond, list):
            return all(self.holds(c) for c in cond)
        negate = cond.startswith("!")
        cond = cond.lstrip("!")
        if "=" in cond:
            key, values = cond.split("=", 1)
            ok = self.word(key) in values.split("|")
        else:
            ok = not empty(self.lookup(cond))
        return ok != negate

    def present(self, pname) -> bool:
        spec = self.spec.part_index[pname]
        if "when" in spec and not self.holds(spec["when"]):
            return False
        if "slot" in spec and empty(self.fields.get(spec["slot"])):
            return False
        if "image" in spec and self.picture(pname) is None:
            return False
        if "repeat" in spec and empty(self.field_list(spec["repeat"])):
            return False
        return True

    def kind(self, pname) -> str:
        spec = self.spec.part_index[pname]
        for k in ("repeat", "ties"):
            if k in spec:
                return k
        if "use" in spec:
            return "component"
        if "slot" in spec:
            return "component" if isinstance(self.fields.get(spec["slot"]), dict) else "text"
        if "runs" in spec:
            return "text"
        for k in PRIMITIVES:
            if k in spec:
                return k
        raise EngineError(f"{self.spec.ref}: part {pname} has no kind")

    def field_list(self, name):
        value = self.fields.get(name) if not FIELD.fullmatch(str(name)) else self.interpolate(name)
        return value if isinstance(value, list) else []

    # ------------------------------------------------------------ cells

    def give(self, name, value):
        if name in self.cells and abs(self.cells[name] - value) > 0.01:
            raise EngineError(f"{self.spec.ref} at {self.where()}: {name} was read before its parent gave it (two owners)")
        self.given[name] = value
        self.cells.pop(name, None)

    def value(self, v, extra=None):
        v = self.pick(v)
        if isinstance(v, (int, float)):
            return float(v)
        if is_formula(v):
            try:
                return evaluate(v, lambda n: extra[n] if extra and n in extra else self.get(n), self.page.number_token)
            except FormulaError as e:
                raise EngineError(f"{self.spec.ref} at {self.where()}: {e}") from e
        raise EngineError(f"{self.spec.ref} at {self.where()}: {v!r} is not a number or a formula")

    def get(self, name) -> float:
        if name in self.cells:
            return self.cells[name]
        if name in self.evaluating:
            loop = self.evaluating[self.evaluating.index(name):] + [name]
            raise EngineError(f"loop in {self.spec.ref} at {self.where()}: " + " -> ".join(loop))
        self.evaluating.append(name)
        try:
            result = self._compute(name)
        finally:
            self.evaluating.pop()
        self.cells[name] = result
        return result

    def _compute(self, name) -> float:
        parts = name.split(".")
        head = parts[0]
        if name in ("width", "height"):
            if self.given.get(name) is not None:
                return self.given[name]
            return self.get(f"preferred.{name}")
        if head == "preferred":
            if parts[1] not in self.spec.preferred:
                raise EngineError(f"{self.spec.ref}: no {parts[1]} given and no preferred {parts[1]} declared")
            return self.value(self.spec.preferred[parts[1]])
        if head in ("index", "count") or head in ("from", "to"):
            given = self.given.get(head)
            if given is None:
                raise EngineError(f"{self.spec.ref}: {head} is not given here")
            return given if head in ("index", "count") else given[0 if parts[1] == "x" else 1]
        if head == "page" and self.spec.kind == "layouts":
            return self.value(self.spec.page[parts[1]])
        if head in self.spec.values and len(parts) == 1:
            return self.value(self.spec.values[head])
        if head in self.spec.part_index:
            return self.part_value(head, parts[1:])
        raise EngineError(f"{self.spec.ref} at {self.where()}: unknown name {name!r}")

    def part_value(self, pname, rest) -> float:
        if not rest:
            raise EngineError(f"{self.spec.ref}: {pname} needs a property")
        prop = rest[0]
        if prop in DERIVED:
            base, size, k = DERIVED[prop]
            return self.get(f"{pname}.{base}") + k * self.get(f"{pname}.{size}")
        if prop in ("x", "y", "width", "height") and len(rest) == 1:
            return self.part_geometry(pname, prop)
        kind = self.kind(pname)
        if kind == "repeat" and prop == "count":
            return float(len(self.field_list(self.spec.part_index[pname]["repeat"])))
        if kind == "text" and prop == "natural":
            return self.text_layout(pname, natural=True)["natural"]
        if kind == "text" and prop == "lines":
            n, sub = int(rest[1]), rest[2]
            lh = self.text_layout(pname)["line_height"]
            top = self.get(f"{pname}.y") + (n - 1) * lh
            return {"y": top, "middle": top + lh / 2, "bottom": top + lh, "height": lh}[sub]
        if kind == "component" and prop == "preferred":
            return self.child(pname).get(".".join(rest))
        if kind == "component":
            child = self.child(pname)
            if prop not in child.spec.exposes:  # a parent reads below a child only what the child exposes (point 20)
                raise EngineError(f"{self.spec.ref}: {pname}.{'.'.join(rest)}: {child.spec.ref} does not expose {prop!r}")
            inner = child.get(".".join(rest))
            return inner + self._offset(pname, rest[-1])
        if kind == "repeat":
            group = self.arrange(pname)
            items = group.items
            match = items[0] if prop == "first" else items[-1] if prop == "last" else next((i for i in items if i[0] == prop), None)
            if not match:
                raise EngineError(f"{self.spec.ref}: no item {prop!r} in {pname}")
            _, x, y, w, h, _ = match
            frame = {"x": x, "y": y, "width": w, "height": h}
            sub = rest[1]
            if sub in DERIVED:
                base, size, k = DERIVED[sub]
                val = frame[base] + k * frame[size]
            else:
                val = frame[sub]
            return val + self._offset(pname, sub)
        raise EngineError(f"{self.spec.ref}: cannot read {pname}.{'.'.join(rest)}")

    def _offset(self, pname, prop):
        if prop in ("x", "right", "center"):
            return self.get(f"{pname}.x")
        if prop in ("y", "bottom", "middle"):
            return self.get(f"{pname}.y")
        return 0.0

    def part_geometry(self, pname, prop) -> float:
        spec = self.spec.part_index[pname]
        if not self.present(pname):
            if prop in ("width", "height"):
                return 0.0
            try:
                return self.value(spec[prop]) if prop in spec else 0.0
            except EngineError:
                return 0.0
        kind = self.kind(pname)
        points = self.points(pname) if (kind == "line" or "from" in spec) else None
        if points:
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            return {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}[prop]
        if prop in ("x", "y"):
            return self.value(spec[prop]) if prop in spec else 0.0
        if kind == "ties":
            return 0.0
        if prop == "width":
            if "width" in spec:
                return self.value(spec["width"])
            if kind == "text":
                return self.text_layout(pname, natural=True)["natural"]
            if kind == "component":
                return self.child(pname).get("width")
            if kind == "repeat":
                return self.get("width")
            raise EngineError(f"{self.spec.ref}: part {pname} needs a width")
        if "height" in spec:
            h = self.value(spec["height"])
            if kind == "component":
                self.child(pname).give("height", h)
            return h
        if kind == "text":
            return self.text_layout(pname)["height"]
        if kind == "component":
            return self.child(pname).get("height")
        if kind == "repeat":
            return self.arrange(pname).height
        raise EngineError(f"{self.spec.ref}: part {pname} needs a height")

    def points(self, pname):
        spec = self.spec.part_index[pname]
        src = spec.get("line", spec) if "line" in spec else spec
        if "from" not in src:
            return None
        pts = [src["from"], *src.get("via", []), src["to"]]
        return [(self.value(p[0]), self.value(p[1])) for p in pts]

    # ------------------------------------------------------------ text

    def picture(self, pname):
        spec = self.spec.part_index[pname]["image"]
        name = self.interpolate(spec.get("picture"))
        return self.page.brand.picture(name) if name else None

    def text_layout(self, pname, natural=False):
        key = (pname, natural)
        if key in self.texts:
            return self.texts[key]
        spec = self.spec.part_index[pname]
        style = self.page.style(self.interpolate(spec.get("style", "body")))
        colour_role = spec.get("colour", "text-primary")
        wrap = self.pick(spec.get("wrap", "yes")) == "yes" and "runs" not in spec
        if "slot" in spec and "text" not in spec:
            template = "{" + spec["slot"] + "}"
        else:
            template = spec.get("text", spec.get("runs"))
        content = self.interpolate(template)
        highlight = self.pick(spec.get("highlight", "none"))
        if isinstance(content, str) and highlight == "shell":
            lines_runs = shell_runs(content)
        elif isinstance(content, list):
            lines_runs = [[list(r) if isinstance(r, list) else [r, None] for r in line] for line in content]
        else:
            content = "" if empty(content) else str(content)
            width = None if (natural or not wrap) else self.get(f"{pname}.width")
            lines, overflow = break_text(content, width, style, self.page.lang) if content else ([], False)
            lines_runs = [[[line, None]] for line in lines]
            if overflow:
                self.page.problem("FIT", self.where(pname), f"a word is wider than its box ({width:.0f})")
        line_widths = [style.width("".join(t for t, _ in line)) for line in lines_runs]
        layout = {
            "style": style, "colour": colour_role, "runs": lines_runs, "widths": line_widths,
            "natural": max(line_widths, default=0.0), "line_height": style.line_height,
            "height": len(lines_runs) * style.line_height, "field": FIELD.fullmatch(str(template)) and FIELD.fullmatch(str(template)).group(1),
            "source": prepare(content, self.page.lang) if isinstance(content, str) and highlight != "shell" else None,
        }
        self.texts[key] = layout
        return layout

    # ------------------------------------------------------------ children

    def draw_param(self, name):
        if name in self.fields and not isinstance(self.fields[name], list):
            return self.fields[name], self
        if name in self.spec.draws:
            return self.spec.draws[name], self
        if self.scope:
            return self.scope.draw_param(name)
        return None, self

    def resolve(self, use, bindings: dict, item: dict | None = None, item_path=None):
        """The component a part or an item is drawn by, with its fields and options."""
        scope = None
        defaults = {}
        content_path = item_path or self.content_path
        if use in self.spec.define or (self.scope and use in self.scope.spec.define and use not in self.spec.draws):
            owner = self if use in self.spec.define else self.scope
            comp = owner.spec.define[use]
            scope = owner if owner.spec.kind != "local" else owner.scope or owner
            merged = dict(item or {})
            merged.update(bindings)
            return comp, merged, {}, scope, content_path
        param, owner = (None, None)
        if item is not None and isinstance(item.get("use"), str):
            ref = item["use"]
        elif use == "self":
            ref = self.fields.get("use")
            if not ref:
                param, owner = self.draw_param("item")
                ref = param.get("use") if isinstance(param, dict) else param
                defaults = {k: v for k, v in param.items() if k != "use"} if isinstance(param, dict) else {}
        elif "/" in str(use):
            ref = use
        else:
            param, owner = self.draw_param(use)
            if param is None:
                raise EngineError(f"{self.spec.ref}: nothing draws {use!r}")
            ref = param.get("use") if isinstance(param, dict) else param
            defaults = {k: v for k, v in param.items() if k != "use"} if isinstance(param, dict) else {}
        comp = self.page.component(ref)
        merged = dict(defaults)
        if use == "self":
            own = self.spec.own_fields() - {"id"}
            merged.update({k: v for k, v in self.fields.items() if k not in own and k != "use"})
        if item is not None:
            merged.update({k: v for k, v in item.items() if k != "use"})
        merged.update(bindings)
        options = {}
        for opt, values in comp.options.items():
            value = merged.pop(opt, None)
            if value is None:
                options[opt] = values[0]
            elif isinstance(value, dict) and "item" in value and "item" in values:
                options[opt] = value
            elif value in values:
                options[opt] = value
            else:
                self.page.problem("SCHEMA", content_path, f"option {opt}={value!r} is not one of {values} of {comp.ref}")
                options[opt] = values[0]
        self.validate(comp, merged, content_path)
        return comp, merged, options, None, content_path

    def validate(self, comp: Spec, fields: dict, where: str):
        schema = copy.deepcopy(comp.fields)
        props = schema.setdefault("properties", {})
        for k, v in UNIVERSAL_FIELDS.items():
            props.setdefault(k, v)
        for k in comp.draws:
            props.setdefault(k, {"type": ["object", "string"]})
        schema.setdefault("additionalProperties", False)
        for path, text in prose_strings(schema, fields, where):
            self.page.prose[path] = text
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(fields), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path)
            allowed = sorted(set(props) | set(comp.options))
            msg = err.message if err.validator != "additionalProperties" else f"{err.message}; {comp.ref} takes {', '.join(allowed)}"
            self.page.problem("SCHEMA", f"{where}{'/' + loc if loc else ''}", msg)

    def child(self, pname) -> "Instance":
        if pname in self.children:
            return self.children[pname]
        spec = self.spec.part_index[pname]
        reserved = RESERVED - set(PRIMITIVES)  # a part drawn by a component draws no primitive: `text:` is a field
        bindings = {k: self.interpolate(v) for k, v in spec.items() if k not in reserved}
        bindings = {k: v for k, v in bindings.items() if not empty(v)}
        if spec.get("with") == "fields":  # this item's fields, less the ones this component reads itself
            own = self.spec.own_fields() - {"id"}
            bindings = {**{k: v for k, v in self.fields.items() if k not in own and k != "use"}, **bindings}
        elif "with" in spec:
            extra = self.interpolate(spec["with"]) or {}
            bindings = {**extra, **bindings}
        content_path = self.content_path
        use = spec.get("use")
        if "slot" in spec and not use:
            item = self.fields[spec["slot"]]
            content_path = self.where(spec["slot"])
            comp, fields, options, scope, _ = self.resolve(item.get("use"), {}, item=item, item_path=content_path)
        elif isinstance(use, str) and FIELD.fullmatch(use):
            item = self.interpolate(use)
            content_path = self.where(FIELD.fullmatch(use).group(1))
            comp, fields, options, scope, _ = self.resolve(item.get("use"), {}, item=item, item_path=content_path)
        elif use == "item":
            comp, fields, options, scope, _ = self.resolve("self", bindings)
        else:
            comp, fields, options, scope, _ = self.resolve(use, bindings, item_path=content_path)
        given = {}
        if "from" in spec:
            pts = self.points(pname)
            x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
            given["from"] = (pts[0][0] - x0, pts[0][1] - y0)
            given["to"] = (pts[-1][0] - x0, pts[-1][1] - y0)
            given["width"] = max(p[0] for p in pts) - x0
            given["height"] = max(p[1] for p in pts) - y0
        elif "width" in spec:
            given["width"] = self.value(spec["width"])
        inst = Instance(self.page, comp, fields, options if comp.kind != "local" else {}, self.path + [pname], content_path, given, scope)
        self.children[pname] = inst
        return inst

    # ------------------------------------------------------------ operators

    def arrange(self, pname) -> Group:
        if pname in self.groups:
            return self.groups[pname]
        spec = self.spec.part_index[pname]
        items = self.field_list(spec["repeat"])
        width = self.get(f"{pname}.width")
        mode = "stack" if "stack" in spec else "row"
        op = {k: v for k, v in (spec.get(mode) or {}).items()}
        n = len(items)
        gap = self.value(op.get("gap", 0))
        group = Group(width)
        shares = self.pick(op.get("shares", [1]))
        shares = [shares[i] if i < len(shares) else 1 for i in range(n)]
        insts = []
        for i, item in enumerate(items):
            key = str(item.get("id", f"#{i}"))
            extra = {"index": float(i), "count": float(n)}
            if mode == "stack":
                w = self.value(op["item-width"], extra) if "item-width" in op else width
            else:
                w = (width - gap * (n - 1)) * shares[i] / sum(shares)
            path = f"{self.where(spec['repeat'])}/{key}"
            comp, fields, options, scope, _ = self.resolve(spec.get("draw", "item"), {}, item=item, item_path=path)
            given = {"width": w}
            if spec.get("ramp"):
                given["ramp"] = f"{spec['ramp']}-{min(i + 1, 5)}"
            inst = Instance(self.page, comp, fields, options, self.path + [pname, key], path, given, scope)
            insts.append((key, w, inst))
        heights = [inst.get("preferred.height") for _, _, inst in insts]
        if op.get("equal") == "height" or "fill" in op:
            heights = [max(heights, default=0)] * n
        if "fill" in op and n:
            share = (self.value(op["fill"]) - gap * (n - 1)) / n
            heights = [max(h, share) for h in heights]
        for (_, _, inst), h in zip(insts, heights):
            inst.give("height", h)
        align = self.pick(op.get("align", "start" if mode == "stack" else "top"))
        if mode == "stack":
            if "distribute" in op and n > 1:  # spread over a length: the gaps grow, never below the gap given
                gap = max(gap, (self.value(op["distribute"]) - sum(heights)) / (n - 1))
            y = 0.0
            for (key, w, inst), h in zip(insts, heights):
                x = {"start": 0.0, "center": (width - w) / 2, "end": width - w}[align]
                group.items.append((key, x, y, w, h, inst))
                y += h + gap
            group.height = max(y - gap, 0.0)
        else:
            tallest = max(heights, default=0.0)
            x = 0.0
            for (key, w, inst), h in zip(insts, heights):
                y = {"top": 0.0, "middle": (tallest - h) / 2, "bottom": tallest - h, "item": 0.0}[align]
                group.items.append((key, x, y, w, h, inst))
                x += w + gap
            if align == "item":
                self._line_up(group, op)
            group.height = max((it[2] + it[4] for it in group.items), default=0.0)
        self.groups[pname] = group
        return group

    def _line_up(self, group: Group, op):
        """Line the other items up with one item found by id inside one of them, and draw the arrow."""
        target = self.options.get("line-up", {}).get("item")
        holder = None
        for i, (key, x, y, w, h, inst) in enumerate(group.items):
            found = inst.find(target)
            if found:
                holder = (i, x + found[0], y + found[1], found[2], found[3])
                break
        if not holder:
            self.page.problem("REF", self.where(), f"line-up: no item {target!r} in any panel")
            return
        i, fx, fy, fw, fh = holder
        middle = fy + fh / 2
        for j, (key, x, y, w, h, inst) in enumerate(group.items):
            if j != i:
                group.items[j] = (key, x, max(middle - h / 2, 0.0), w, h, inst)
        nxt = group.items[i + 1] if i + 1 < len(group.items) else None
        if nxt and op.get("connector"):
            start, end = (fx + fw + 16, middle), (nxt[1] - 16, middle)
            comp, fields, options, scope, _ = self.resolve(op["connector"], {})
            x0 = start[0]
            given = {"from": (0.0, 0.0), "to": (end[0] - x0, 0.0), "width": end[0] - x0, "height": 0.0}
            group.extras.append((Instance(self.page, comp, fields, options, self.path + ["line-up"], self.content_path, given), x0, middle))

    def tie_connectors(self, pname):
        """Connectors between items found by id, each end spread around its item's middle."""
        if pname in self.groups:
            return self.groups[pname]
        spec = self.spec.part_index[pname]
        ties = []
        for tie in self.field_list(spec["ties"]):
            targets = tie["to"] if isinstance(tie["to"], list) else [tie["to"]]
            for t in targets:
                ties.append((tie, tie["from"], t))
        frames = {}
        for _, a, b in ties:
            for key in (a, b):
                if key not in frames:
                    frames[key] = self.find(key)
                    if frames[key] is None:
                        self.page.problem("REF", self.where(spec["ties"]), f"tie names {key!r}, which no item has as its id")
        ties = [t for t in ties if frames[t[1]] and frames[t[2]]]
        spread_out, spread_in = (self.value(s) for s in spec.get("spread", [0, 0]))
        gap = self.value(spec.get("gap", 0))
        group = Group(0.0)
        for n, (tie, a, b) in enumerate(ties):
            outs = sorted((t for t in ties if t[1] == a), key=lambda t: frames[t[2]][1] + frames[t[2]][3] / 2)
            ins = sorted((t for t in ties if t[2] == b), key=lambda t: frames[t[1]][1] + frames[t[1]][3] / 2)
            j, k = outs.index((tie, a, b)), ins.index((tie, a, b))
            fa, fb = frames[a], frames[b]
            start = (fa[0] + fa[2] + gap, fa[1] + fa[3] / 2 + (j - (len(outs) - 1) / 2) * spread_out)
            end = (fb[0] - gap, fb[1] + fb[3] / 2 + (k - (len(ins) - 1) / 2) * spread_in)
            fields = {k_: v for k_, v in tie.items() if k_ in ("concept", "state")}
            bindings = {k_: self.interpolate(v) for k_, v in spec.items() if k_ not in RESERVED}
            comp, fields, options, scope, _ = self.resolve(spec.get("draw", "connector"), {**bindings, **fields}, item_path=self.where(spec["ties"]))
            x0, y0 = min(start[0], end[0]), min(start[1], end[1])
            given = {"from": (start[0] - x0, start[1] - y0), "to": (end[0] - x0, end[1] - y0),
                     "width": abs(end[0] - start[0]), "height": abs(end[1] - start[1])}
            inst = Instance(self.page, comp, fields, options, self.path + [pname, f"{a}--{b}"], self.where(spec["ties"]), given)
            group.extras.append((inst, x0, y0))
        self.groups[pname] = group
        return group

    def find(self, key):
        """The frame of the item with this id, anywhere below, relative to this instance."""
        for pname, spec in self.spec.parts:
            if not self.present(pname):
                continue
            kind = self.kind(pname)
            if kind == "repeat":
                group = self.arrange(pname)
                gx, gy = self.get(f"{pname}.x"), self.get(f"{pname}.y")
                for k, x, y, w, h, inst in group.items:
                    if k == key:
                        return (gx + x, gy + y, w, h)
                for k, x, y, w, h, inst in group.items:
                    found = inst.find(key)
                    if found:
                        return (gx + x + found[0], gy + y + found[1], found[2], found[3])
            elif kind == "component":
                found = self.child(pname).find(key)
                if found:
                    return (self.get(f"{pname}.x") + found[0], self.get(f"{pname}.y") + found[1], found[2], found[3])
        return None

    # ------------------------------------------------------------ the scene

    def trace(self, *more):
        return "/".join(self.path + list(more))

    def emit(self, x=0.0, y=0.0) -> dict:
        width, height = self.get("width"), self.get("height")
        node = {"type": "group", "id": self.trace(), "component": self.spec.label, "x": r2(x), "y": r2(y),
                "width": r2(width), "height": r2(height), "content": self.content_path, "children": []}
        if self.options:
            node["options"] = {k: v for k, v in self.options.items()}
        if self.fields.get("concept"):
            node["concept"] = self.fields["concept"]
        if self.fields.get("state"):
            node["state"] = self.fields["state"]
        if "height" in self.spec.preferred and self.given.get("height") is not None:
            preferred = self.get("preferred.height")
            if preferred - self.given["height"] > 0.5:
                self.page.problem("FIT", self.where(), f"{self.spec.ref} needs {preferred:.0f} high and gets {self.given['height']:.0f}")
        for pname, spec in self.spec.parts:
            if not self.present(pname):
                continue
            node["children"].extend(self.emit_part(pname, spec))
        if self.spec.kind == "layouts":
            for pname, bound in self.spec.bounds.items():
                if self.present(pname) and self.get(f"{pname}.bottom") > self.value(bound) + 0.5:
                    self.page.problem("FIT", self.where(pname), f"{pname} reaches {self.get(pname + '.bottom'):.0f}, past {self.value(bound):.0f}")
        return node

    def emit_part(self, pname, spec) -> list[dict]:
        kind = self.kind(pname)
        pid = self.trace(pname)
        if kind == "repeat":
            group = self.arrange(pname)
            node = {"type": "group", "id": pid, "x": r2(self.get(f"{pname}.x")), "y": r2(self.get(f"{pname}.y")),
                    "width": r2(group.width), "height": r2(group.height), "children": []}
            for key, x, y, w, h, inst in group.items:
                node["children"].append(inst.emit(x, y))
            for inst, x, y in group.extras:
                node["children"].append(inst.emit(x, y))
            return [node]
        if kind == "ties":
            group = self.tie_connectors(pname)
            node = {"type": "group", "id": pid, "x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0, "children": []}
            for inst, x, y in group.extras:
                node["children"].append(inst.emit(x, y))
            return [node]
        if kind == "component":
            self.get(f"{pname}.width"), self.get(f"{pname}.height")  # the size it gets, given before it draws
            return [self.child(pname).emit(self.get(f"{pname}.x"), self.get(f"{pname}.y"))]
        frame = {k: r2(self.get(f"{pname}.{k}")) for k in ("x", "y", "width", "height")}
        if kind in ("box", "ellipse"):
            prim = spec[kind]
            out = {"type": kind, "id": pid, **frame, "fill": self.colour(prim.get("fill"), pname)}
            stroke = self.colour(prim.get("stroke"), pname)
            if stroke:
                out["stroke"] = stroke
                out["stroke_width"] = r2(self.value(prim.get("stroke-width", 1)))
                if self.pick(prim.get("dash", "no")) == "yes":
                    out["dash"] = [r2(out["stroke_width"] * 3), r2(out["stroke_width"] * 2)]
            if kind == "box" and prim.get("radius") is not None:
                radius = self.value(prim["radius"])
                if radius:
                    out["radius"] = r2(radius)
            return [out]
        if kind == "line":
            prim = spec["line"]
            out = {"type": "line", "id": pid, "points": [[r2(a), r2(b)] for a, b in self.points(pname)],
                   "stroke": self.colour(prim.get("stroke", "tone.line"), pname), "stroke_width": r2(self.value(prim.get("stroke-width", 2))),
                   "tips": self.interpolate(prim.get("tips", "none")) or "none"}
            if self.pick(prim.get("dash", "no")) == "yes":
                out["dash"] = [r2(out["stroke_width"] * 3), r2(out["stroke_width"] * 2)]
            return [out]
        if kind == "image":
            prim = spec["image"]
            path = self.picture(pname)
            rel = path.relative_to(self.page.piece.root).as_posix()
            return [{"type": "image", "id": pid, **frame, "href": rel, "fit": prim.get("fit", "contain"),
                     "tint": self.colour(prim.get("tint"), pname) if prim.get("tint") else None}]
        return [self.emit_text(pname, spec, frame)]

    def emit_text(self, pname, spec, frame):
        layout = self.text_layout(pname)
        style = layout["style"]
        run_colours = spec.get("run-colours") or {}
        decorative = set(spec.get("decorative") or [])
        base = self.colour(spec.get("colour", "text-primary"), pname)
        align = self.interpolate(spec.get("align", "start")) or "start"
        lines = []
        for runs, line_width in zip(layout["runs"], layout["widths"]):
            out_runs, pen = [], 0.0
            for text, role in runs:
                run = {"text": text, "x": r2(pen), "fill": base}
                pen += style.advance(text)
                if role:
                    if role in run_colours:
                        run["fill"] = self.colour(run_colours[role], pname)
                    else:
                        family = self.page.concept_family(role, self.where(pname))
                        if family:
                            run["fill"] = self.page.colour_token(f"{family}.ink", self.where(pname))
                    if role in decorative:
                        run["decorative"] = True
                out_runs.append(run)
            shift = {"start": 0.0, "center": (frame["width"] - line_width) / 2, "end": frame["width"] - line_width}[align]
            lines.append({"x": r2(shift), "width": r2(line_width), "runs": out_runs})
        missing = set()
        for runs in layout["runs"]:
            for text, _ in runs:
                missing |= style.face.missing(text)
        if missing:
            self.page.problem("FONT", self.where(pname), f"{style.face.family} has no glyph for {''.join(sorted(missing))!r}")
        out = {
            "type": "text", "id": self.trace(pname), **frame,
            "align": align,
            "font": {"family": style.face.family, "weight": style.weight, "size": r2(style.size), "line_height": r2(style.line_height),
                     "baseline": r2(style.baseline), "style": style.name, "render": style.render,
                     "measured": style.face.record(self.page.piece.root)},
            "lines": lines,
        }
        if layout["source"] is not None and wrap_of(spec, self) and len(lines) > 1:
            out["source"] = layout["source"]  # the unbroken text, for a renderer that breaks lines itself (Mural)
        for runs, w in zip(layout["runs"], layout["widths"]):
            if w > frame["width"] + 0.5:
                out["overflow"] = True
                self.page.problem("FIT", self.where(pname), f"a line is {w:.0f} wide in a box {frame['width']:.0f} wide")
                break
        if frame["height"] + 0.5 < layout["height"]:
            out["overflow"] = True
            self.page.problem("FIT", self.where(pname), f"text needs {layout['height']:.0f} high and gets {frame['height']:.0f}")
        if layout["field"] and layout["field"] in self.fields:
            out["field"] = f"{self.content_path}/{layout['field']}"
        return out
