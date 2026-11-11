"""The JSON code writer's declaration, plain data (visual-communication DEC-005 points 7 to 9).

Read with the standard library alone, so the check knows what the writer takes, and that a
declaration of written code meets no loss, without importing the writer.

- `version`: the writer's own version. It rises when the same values document could give
  another file; the reference output pinned to it in the capability's tests catches a
  change made without one.
- `forms`: the versions of its spelling it writes (DEC-005 point 8). Each form is that
  version of the values document: form 1 is version 1, and form 2 version 2, which holds a
  picture role's file (DEC-025 point 4). A declaration of written code names one; the
  writer keeps writing every form it shipped.
- `kinds`: by form, every type that form's version of the document can hold: every DTCG
  type, `typography` included, and a `picture` in form 2. The command hands a writer only
  the types its form names here, so a picture role is a loss of form 1, known before the
  writer runs, and the writer writes the rest of the document unchanged.
- `axis-kinds`: every kind of axis, since a combination is a key of the document whichever
  kind of axis it lies on. So the document holds the keys of each size a brand gives
  (DEC-021 point 8), and the command takes no axis at its default for it.
- `prefix`: False, since a token path stays as the brand exports it. The command refuses a
  declaration of written code that names one.
- `programs`, `services`: what it needs beyond the project's files: none.
"""

DECLARATION = {
    "name": "json",
    "kind": "code-writer",
    "version": "1.0.0",
    "seam": 6,
    "module": "json",
    "forms": [1, 2],
    "kinds": {
        "1": ["color", "dimension", "fontFamily", "fontWeight", "number", "typography"],
        "2": ["color", "dimension", "fontFamily", "fontWeight", "number", "typography", "picture"],
    },
    "axis-kinds": ["value", "size"],
    "prefix": False,
    "programs": [],
    "services": [],
}
