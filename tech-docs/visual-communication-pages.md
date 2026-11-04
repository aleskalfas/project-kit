---
reader: maintainer
kind: reference
pkit:
  friction:
    anchors:
      record:
        - COR-050#5
      artefact:
        - living-docs:RS-LDOC-002
        - living-docs:RS-LDOC-003
---

# The visual-communication pages

For whoever edits the visual-communication capability's pages in `.pkit/capabilities/visual-communication/`. A page that summarises a fact another page holds anchors the section that holds it (RS-LDOC-002). This page holds the order those anchors keep. It is maintainer documentation, so the pages themselves leave it out (RS-LDOC-003).

## The order of their anchors

Artefact anchors may form no cycle, and an anchor on a section counts as one on its whole page (COR-050 point 5). So the pages keep one order, and a page anchors only the pages before it in the order:

1. `files.md`
2. `components.md`
3. `outputs.md`
4. `checks.md`
5. `README.md`
