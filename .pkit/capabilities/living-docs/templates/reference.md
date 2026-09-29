---
# A reference page (living-docs DEC-001 point 3; RS-LDOC-004): the page that
# describes one surface — an area, a capability, an adapter, a command set —
# to the reader who uses it: what it is for, how it is used, and what holds.
# A page that only points into a folder is a signpost instead (RS-LDOC-005).
# Copy it beside the surface it describes — usually as its README.md — and
# fill it in.
reader: user                      # who the page is for: an id of the readers point (user, maintainer, or one the project adds)
kind: reference                   # the page's kind: this template's
pkit:
  friction:
    anchors:
      path: ["<surface>/**"]      # the code and files it describes: a change there asks whether the page still holds
      record: ["<record>"]        # the decisions it applies: a change to one asks the same
---

# <Surface>

<One paragraph: what this surface is for, for this reader, and the decision it rests on.>

## <A part of the surface, or a task the reader does with it>

<What the reader does and what holds, each rule citing the decision it comes from.>
