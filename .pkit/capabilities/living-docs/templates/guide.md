---
# A guide (living-docs DEC-003; RS-LDOC-004): the page that explains one
# subject — an area, a component, a tool, a feature — to the reader who uses
# it: why it exists, what it solves for them, and how they do its tasks. Its
# parts come in this order: the title, a lead with any contents list, why the
# subject exists, the reader's tasks, and, on a folder's entry page, the
# folder's pages last. A section on how the subject works may stand anywhere
# after the why. The detail a reader looks up is left to the page that
# describes the subject, which the lead names where one does. Stamp it with
# `pkit living-docs new page <file> --kind guide …`, and fill it in.
reader: user                      # who the page is for: an id of the readers point (user, maintainer, or one the project adds)
kind: guide                       # the page's kind: this template's
pkit:
  friction:
    anchors:
      path: ["<subject>/**"]      # the code and files of the subject it explains: a change there asks whether the guide still holds
      record: ["<record>"]        # the decisions it explains: a change to one asks the same
      artefact: ["<page>#<section>"]  # the home of each fact it summarises, such as a section of the page that describes the subject
---

# <Subject>

<One paragraph: what this subject is, for this reader, and which page describes it, where one does.>

<A contents list, if the page wants one: a link to each section below.>

## <Why the subject exists>

<The problem it solves for this reader, as they meet it.>

## <A task the reader does>

<How the reader does it, and what they see once it is done. A task comes after any task it needs done first.>

## <The folder's pages>

<Only on a folder's entry page, such as its README: the pages the folder holds for this reader, in the order they take them, a subfolder's pages through its entry page. Delete this section on any other page.>

- [<page>](<page>) — <what the reader finds there, in a line>.
