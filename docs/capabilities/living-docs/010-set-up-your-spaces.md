---
reader: act-adopter
kind: guide
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/new.py
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/schemas/readers.schema.json
      record: ["living-docs:DEC-001#1", "living-docs:DEC-001#2", "living-docs:DEC-001#3", "living-docs:DEC-001#7", "living-docs:DEC-001#8", "COR-050#8", "COR-050#14", "COR-051#4"]
      artefact:
        - UC-043
        - ACT-adopter
        - .pkit/capabilities/living-docs/spaces.md#declaring-the-spaces
        - .pkit/capabilities/living-docs/spaces.md#the-space-definition-template
        - .pkit/capabilities/living-docs/spaces.md#each-definitions-scope
        - .pkit/capabilities/living-docs/README.md#authoring-the-docs-author-skill
        - .pkit/capabilities/living-docs/README.md#a-fresh-project-the-first-stamp-sets-the-roots-apart
        - .pkit/capabilities/living-docs/README.md#the-readers-point
        - .pkit/capabilities/living-docs/validation.md#what-fails
        - .pkit/cli/README.md#configuration-file
        - .pkit/cli/README.md#connections-resolve-address---json
---

# Set up your spaces

A documentation space holds the pages written for one audience, and its definition holds the rules those pages follow. Here you create the two spaces every project has, the user space and the technical space. You also declare your pages, their readers and the code they cover. What a space's configuration holds is in [the reference on spaces](../../../.pkit/capabilities/living-docs/spaces.md#declaring-the-spaces).

## Contents

<!-- pkit:contents -->
- [Why each audience gets a space](#why-each-audience-gets-a-space)
- [Declare the pages outside the documentation roots](#declare-the-pages-outside-the-documentation-roots)
- [Create the two spaces](#create-the-two-spaces)
- [Declare your readers](#declare-your-readers)
- [Declare the code your pages should cover](#declare-the-code-your-pages-should-cover)
- [Name the page your readers start from](#name-the-page-your-readers-start-from)
<!-- /pkit:contents -->

## Why each audience gets a space

A page written for two audiences serves neither. Users need what the system does and how to use it, and maintainers need why it is built so, and by which rules. A space keeps each audience's pages under a documentation root of their own. The rules forbid a user page to link into the technical space.

Each fence on this page starts from a fresh project. Right after the install, both spaces share one documentation root, `docs/`, and neither has its definition yet. Validation reports both, and fails nothing:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs validate | grep -e "error(s)" -e "no definition yet:" -e "both documentation roots"
0 error(s), 3 report(s).
    → space 'user' has no definition yet: its rules — a project rule set inheriting living-docs:LDOC@1, scoped to the space's pages, under `docs/living-docs/rule-sets/` — are written when the space is created, by `pkit living-docs new space user`, which names it as the space's `definition` (DEC-001 point 2).
    → space 'technical' has no definition yet: its rules — a project rule set inheriting living-docs:LDOC@1, scoped to the space's pages, under `docs/living-docs/rule-sets/` — are written when the space is created, by `pkit living-docs new space technical`, which names it as the space's `definition` (DEC-001 point 2).
    → both documentation roots are 'docs', so the user and technical spaces are not separate yet: user-facing navigation must never lead into technical material, and neither root lies inside the other — `pkit living-docs new space user` offers to set the internal root apart, at 'tech-docs', before it creates the space, or set it with `pkit config set docs.internal <path>` (DEC-001 points 1 and 2).
```

## Declare the pages outside the documentation roots

A file outside both documentation roots is a page only where you declare it, such as your top-level `README.md` or a `wiki/` folder. Declare it before you create its space, so that the space's definition takes it in. A file you declare later must be added to the definition's scope by hand ([the reference, "Each definition's scope"](../../../.pkit/capabilities/living-docs/spaces.md#each-definitions-scope)).

1. List each file or folder in `friction.places` of the backbone configuration, with the page type:

   ```yaml
   # .pkit/project/config.yaml
   friction:
     places:
       - {path: README.md, type: living-docs:page}
       - {path: wiki, type: living-docs:page}
   ```

2. Assign each to its space under `places` in living-docs' configuration, creating the file if it does not exist:

   ```yaml
   # .pkit/capabilities/living-docs/project/config.yaml
   pkit_schema: living-docs:config
   schema_version: 1
   places:
     README.md: user
     wiki: user
   ```

Each such place names exactly one space. A file inside a documentation root needs neither entry, since the root gives it its space.

## Create the two spaces

Create the spaces before you install a capability that writes into the technical space's documentation root, such as software-analysis. What it writes into `docs/` before then stays there.

Create the user space first, then the technical space. Each command writes the space's definition, a rule set under the technical space's root, and names it in living-docs' configuration ([the reference, "Authoring"](../../../.pkit/capabilities/living-docs/README.md#authoring-the-docs-author-skill)). Below, `grep` keeps the lines that say what the first command wrote:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs new space user --yes 2>&1 | grep -e "^set" -e "^stamped" -e "^RS-USER"
set docs.internal = tech-docs  (.pkit/project/config.yaml)
stamped tech-docs/living-docs/rule-sets/user.md: the definition of space 'user', rule set USER, inheriting living-docs:LDOC@1, scoped to the space's pages (docs/**).
RS-USER-001, reader paths stay unbroken, is written accepted: the review of the change that carries this definition accepts it (COR-051 point 4).
$ pkit living-docs new space technical
stamped tech-docs/living-docs/rule-sets/technical.md: the definition of space 'technical', rule set TECHNICAL, inheriting living-docs:LDOC@1, scoped to the space's pages (tech-docs/**).
named it as the space's `definition` in .pkit/capabilities/living-docs/project/config.yaml.
Name the space's entry point in .pkit/capabilities/living-docs/project/config.yaml once its page exists (`pkit living-docs new page … --space technical`); then run `pkit living-docs validate`, `pkit validate` and `pkit friction check`.
$ pkit living-docs validate | head -3
2 space(s); roots docs/ (user) and tech-docs/ (internal); 0 project place(s), 0 assigned; definitions under tech-docs/living-docs/.
user: 0 page(s); definition tech-docs/living-docs/rule-sets/user.md.
technical: 0 page(s); definition tech-docs/living-docs/rule-sets/technical.md.
```

- **The roots set apart.** The two spaces still share `docs/`. So the first command sets the technical space's root to `tech-docs/` before it writes ([the reference, "A fresh project"](../../../.pkit/capabilities/living-docs/README.md#a-fresh-project-the-first-stamp-sets-the-roots-apart)). At a terminal it asks first, and elsewhere it needs `--yes`. Name another folder with `--internal-root <path>`.
- **No document moves.** A maintainer's document left in `docs/` stays there, until you bring it into the technical space ("Bring in your documents").
- **A preview.** `--dry-run` says what the command would write, and writes nothing.
- **The definition it writes.** Each definition inherits the shared method, `LDOC`, and its scope selects the space's pages. The user space's definition adds a rule of its own: its readers' paths through its pages stay unbroken ([the reference, "The space-definition template"](../../../.pkit/capabilities/living-docs/spaces.md#the-space-definition-template)).
- **A failed write is put back.** Where a command's write would bring a validation error your project did not have, it puts back what it wrote, refuses, and quotes the error.

Commit what the two commands wrote. The user space's own rule is written as accepted, so read it before you merge. Merging that change accepts it for every page of the user space.

**A space of your own.** A project may add a space for an audience neither space serves, such as the readers of an interface reference. Its entry in living-docs' configuration names its `audience`, and its places are assigned to it first, since it has no root of its own. Then `pkit living-docs new space <space>` writes its definition ([the reference, "Declaring the spaces"](../../../.pkit/capabilities/living-docs/spaces.md#declaring-the-spaces)).

## Declare your readers

Each page names its reader by an id your project declares. `user` and `maintainer` come built in, and a capability may add readers of its own. A fresh project holds the two built in:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit connections resolve pkit::documentation:readers | head -4
    pkit::documentation:readers
                         union · inert fail · default always — resolved
                         entry    maintainer — the default
                         entry    user — the default
```

Add a reader of your own in the readers' project file, under the technical space's root. Say what the reader needs and, if you wish, the pages they read in order ([the reference, "The readers point"](../../../.pkit/capabilities/living-docs/README.md#the-readers-point)):

```yaml
# tech-docs/pkit/fillers/pkit/documentation/readers.yaml
schema_version: 1
value:
  - id: operator
    description: Runs the service in production, and needs its settings and what to do when it fails.
    paths:
      - description: Restarts the service after a failure.
        pages: [docs/operations.md, docs/runbooks/restart.md]
```

No check reads a path. Where a page's rules ask for unbroken reader paths, as the user space's rule does, the agent's review follows each path through the page.

## Declare the code your pages should cover

The surface is the code your documentation ought to describe, such as your command-line sources. Declare it under `friction.surface` of the backbone configuration ([the CLI reference, "Configuration file"](../../../.pkit/cli/README.md#configuration-file)):

```yaml
# .pkit/project/config.yaml
friction:
  surface:
    - src/**
```

The whole-repository friction check then counts each surface file that no page anchors. Bringing your documents in ends with that count at zero, among other measures ("Bring in your documents").

## Name the page your readers start from

Each space names the page its readers start from, as its `entry-point` in living-docs' configuration. Name it once that page exists, such as your top-level `README.md` once it is a page of the user space:

```yaml
# .pkit/capabilities/living-docs/project/config.yaml
spaces:
  user:
    definition: tech-docs/living-docs/rule-sets/user.md
    entry-point: README.md
```

Validation fails an entry point that is not a document of its space ([the reference, "What fails"](../../../.pkit/capabilities/living-docs/validation.md#what-fails)).
