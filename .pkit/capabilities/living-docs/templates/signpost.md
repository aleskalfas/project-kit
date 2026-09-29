---
# A signpost page (living-docs DEC-001 point 3; RS-LDOC-005): an index-like
# file that tells its reader what a folder holds and where to go, never a
# summary of what the files say. Copy it into the folder it signposts —
# usually as its README.md — and fill it in.
reader: user                      # who the page is for: an id of the readers point (user, maintainer, or one the project adds)
kind: signpost                    # the page's kind: this template's
pkit:
  friction:
    anchors:
      path: ["<folder>/*"]        # what the folder holds: a change there asks whether the signpost still points right
---

# <Folder>

<One sentence: what this folder is for, for this reader.>

- [<entry>](<entry>) — <what the reader finds there, in a line>.
