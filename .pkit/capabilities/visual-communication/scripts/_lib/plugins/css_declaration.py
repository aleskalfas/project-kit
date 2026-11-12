"""The CSS code writer's declaration, plain data (visual-communication DEC-005 points 8 and 9).

Read with the standard library alone, so the check knows what the writer takes, and which
losses a declaration of written code meets, without importing the writer.

- `version`: the writer's own version. It rises when the same values document could give
  other CSS; the reference outputs pinned to it in the capability's tests catch a change
  made without one.
- `forms`: the versions of its spelling it writes (DEC-005 point 8). A declaration of
  written code names one; the writer keeps writing every form it shipped.
- `kinds`: the DTCG types its language has a form for. A token of another type is a loss,
  left out, known before the writer runs: a typography, and a picture role's file
  (DEC-025 point 4).
- `axis-kinds`: the kinds of axis its selectors spell: value axes alone. The command hands
  it a brand's values at the default of each axis of another kind, a size, and reports
  each token that axis changes as a loss, approximated (DEC-021 point 8).
- `programs`, `services`: what it needs beyond the project's files: none.
"""

DECLARATION = {
    "name": "css",
    "kind": "code-writer",
    "version": "1.0.0",
    "seam": 7,
    "module": "css",
    "forms": [1],
    "kinds": ["color", "dimension", "fontFamily", "fontWeight", "number"],
    "axis-kinds": ["value"],
    "programs": [],
    "services": [],
}
