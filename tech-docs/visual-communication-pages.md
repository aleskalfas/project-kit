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
---

# The visual-communication pages

For whoever edits the visual-communication capability's pages in `.pkit/capabilities/visual-communication/`. A page that summarises a fact another page holds anchors the section that holds it (RS-LDOC-002). Such an anchor can close a cycle, and this page says how to keep from closing one.

## Before you anchor one page on another

Anchors between artefacts may form no cycle, and an anchor on a section counts as one on its whole page (COR-050 point 5). So before you anchor a section of another page, read that page's artefact anchors, and theirs in turn. Where they already reach the page you edit, your anchor would close a cycle, which the checks report as an error.
