# Writing a page

A page is written for one reader of one space, and follows one kind's format. It anchors to what makes each of its statements true (DEC-001 point 4).

## 1. Choose the space

The space is the reader's audience. The user space serves people who use the system. The technical space serves those who build it. A project may add others. If the space has no definition yet, follow `space.md` first. No rule binds on a page without one, and the stamp warns of it.

## 2. Choose the kind

- **`signpost`**: an index-like file that says what a folder holds and where to go, never a summary of what the files say (RS-LDOC-005).
- **`reference`**: the page that describes one surface, such as an area, a capability or a command set, to the reader who uses it.

The stamp takes a kind the capability declares. A kind the project adds has its own template, so write that page by hand from it.

## 3. Choose where the file goes

Under the space's root, or in a place assigned to the space. Never in the definitions location, where a file is a template and never a page. A signpost usually goes into the folder it signposts, as its `README.md`. A reference page goes beside the surface it describes. The stamp refuses a file that the check does not read as a page of the space you named.

## 4. Name the reader

The reader the page is for, by its id in the readers point: `user` and `maintainer` by default, or one the project adds (RS-LDOC-003). The page says only what that reader needs.

## 5. Decide what it rests on

Each statement rests on something the page anchors (RS-LDOC-001). Anchor the narrowest thing, on the one part a statement rests on where it rests on one part.

- **`--path <glob>`**: the code and files it describes. A signpost anchors what its folder holds, `<folder>/*`. A reference page anchors the surface's code.
- **`--record <id>`**: the decisions it applies, or one point of one, `<record>#<point>`.
- **`--artefact <id>`**: a rule, an analysis artefact, or the home of a fact it summarises, `<page>#<section-slug>`.
- **`--source <name>`**: a captured source it quotes.

A page with nothing to anchor yet is stamped with an empty friction block. It is counted as unanchored for onboarding, never failed. Its reason for having no anchors is a person's decision, written only after they accept it word for word (DEC-001 point 8).

## 6. Preview, then stamp

```
pkit living-docs new page <file> --space <space> --kind <kind> --reader <id> --title "<Title>" [--path <glob>]... [--record <id>]... [--artefact <id>]... [--source <name>]... --dry-run
pkit living-docs new page <file> --space <space> --kind <kind> --reader <id> --title "<Title>" [--path <glob>]... [--record <id>]... [--artefact <id>]... [--source <name>]...
```

The title fills the page's level-1 heading. The stamp lists the lines that still hold one of the template's placeholders.

## 7. Fill it

Write in each placeholder's place what it asks for, and only what the reader needs.

- **One home per fact** (RS-LDOC-002). A fact a decision record decides needs no link where this page anchors the record, whole or in a part that stands on what decides it. Any other fact another page already states in full is stated here only as a summary that links to that page, however short. Then anchor the home's section: add `<page>#<section-slug>` to the front matter's `artefact` anchors.
- **A statement nothing grounds** needs its anchor, or it goes.

## 8. Check and commit

Run the checks in the shared framing's "After stamping", then commit.
