---
rule-set: REWORK
version: 2.1.0
inherits: [living-docs:LDOC@1, WRITE@2]
scope:
  paths:
    - .pkit/permissions/README.md
    - docs/permissions/README.md
    - .pkit/capabilities/living-docs/README.md
    - .pkit/capabilities/living-docs/pages.md
    - .pkit/capabilities/living-docs/spaces.md
    - .pkit/capabilities/living-docs/validation.md
    - .pkit/capabilities/living-docs/agent.md
    - docs/capabilities/README.md
    - docs/capabilities/living-docs/README.md
    - docs/capabilities/living-docs/010-set-up-your-spaces.md
    - docs/capabilities/living-docs/020-bring-in-your-documents.md
    - docs/capabilities/living-docs/030-write-a-page.md
    - docs/capabilities/living-docs/040-have-a-page-read-as-its-reader.md
    - docs/capabilities/living-docs/050-fix-a-stale-page.md
  types: [living-docs:page]
rules:
  RS-REWORK-001:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "ADR-069 point 4 decides the names. A number in a name gives the reading order a home that a test can hold the README's list to. Numbers in tens leave room for a page between two others, so adding one renames none. A rename of a shipped page owes revalidations and a changeset (ADR-069, Implications)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#3", "ADR-069#4"]}
  RS-REWORK-002:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "ADR-069 point 4 decides how a move keeps its links. A link from outside the change, such as from an adopter's page or an old message, cannot be mended by the change. It still lands where the old address stays. The pilot renamed five headings to drop their citations, and kept each old address as an HTML id (PR #2018)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#4"], artefact: ["RS-USER-001"]}
  RS-REWORK-003:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "ADR-069 point 4 decides what a user page cites. An adopter's agent cannot read a record or an issue that does not ship, so a citation of one leads it nowhere. The maintainer agreed on 24 October that a page cites only the records that ship (#1928). project-kit's own records live under tech-docs/, which never ships."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#4"]}
  RS-REWORK-004:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "ADR-069 point 4 decides how a component's page reaches the backbone's. A capability or an adapter runs on a range of backbone versions, so a page it ships meets backbone pages it was not written against. A backbone page may be numbered anew or moved, while an area's README moves only with its folder (ADR-069 point 3)."}
    pkit:
      friction:
        anchors: {record: ["ADR-069#3", "ADR-069#4"]}
  RS-REWORK-005:
    status: accepted
    origin: {date: 2026-10-25, by: "Aleš Kalfas", why: "The maintainer chose a contents list for a page a reader moves around in, such as a long guide or a reference (#2053). A generator writes it, and a check fails it when stale. Four second-level sections is project-kit's choice of where a page becomes one. A list kept by hand drifts when a section is added or renamed."}
# The parts of rules that project-kit's own tools check (COR-051 point 2). Each stands
# in for its rule's part only where the rule binds, and whoever judges the rest of the
# rule there leaves that part to it.
# - The numbering test, tests/test_page_numbering.py, holds the list of each README
#   this set's scope selects to the numbered pages and subfolders beside it.
# - The contents generator, scripts/page_contents.py, checks every contents list a
#   page holds, as CONTRIBUTING.md says.
checks:
  RS-REWORK-001:
    - check: page-numbering
      part: Each number is in tens, no two of a folder's pages or subfolders share one, and the folder's README lists each numbered page and subfolder in number order, each by a list item that opens with a link to it.
  RS-REWORK-005:
    - check: page-contents
      part: The list between the page's contents markers is the one the contents generator writes from the page's second-level headings.
---

# The documentation rework's writing rules

This set brings project-kit's general writing rules, `WRITE`, to each page the documentation rework has rewritten (EPIC #1928). It also holds the rules ADR-069 point 4 gives every user page, and the rule on a contents list.

- **What it binds:** its own rules, and those of `WRITE` and of the shared method, `living-docs:LDOC`, on each page its scope selects. The scope selects by path and by living-docs' page type, as the space definitions do.
- **Where its rules reach:** only the pages the scope lists, so a rule here reaches a user page once a slice of the rework adds it. The scope lists the reworked pages one by one (ADR-069 point 4), as the pilot set it up (#2012). So accepting a rule costs only the pages already rewritten.
- **Why it inherits `LDOC`:** a set that holds a project's documentation rules inherits `LDOC` (living-docs DEC-001 point 3). It pins major 1, as `GUIDE`, `USER` and `TECH` do. One page reached through two pins of a set at different majors fails validation (COR-051 point 7).
- **How it grows:** each slice of the rework adds the pages it rewrites or creates to the scope's paths. A page several slices rewrite joins with the last of them.
- **The guides' set:** `GUIDE` (`guide.md` beside this one) holds the rules that only the guides and the entry README follow. Its scope selects `docs/**` and `README.md`, and keeps it however this set grows.
- **Accepted:** every rule here is accepted, and binds now on each page the scope lists (COR-051 point 4). The maintainer adopted them on 25 October (#2022). A rule added later binds on each of those pages, all at once, when it is accepted. So the change that accepts it mends the pages that break it, or first leaves them out of the scope (COR-060 point 2).
- **How a rule reads:** a statement, then *How*, then examples, as in `WRITE`. Its reason is the `why` of its origin, in the front matter. What binds is a rule's statement and its *How*. The examples, a "such as" phrase, a sentence that starts "An instance is" and a *Note* only illustrate.
- **The examples:** each quotes the page it names, as main holds it, unless it names a commit. An example on no branch says so.
- **When it goes:** once the spaces' definitions, `TECH` and `USER`, inherit `WRITE` (#1350). `USER` then takes this set's rules (ADR-069), every page takes `WRITE` through its space, and this set is removed.

## RS-REWORK-001 — Numbered names for pages read in order

Name a page or a subfolder that its reader reads in order with a number in tens, and a lookup page by its topic.

- **How:**
  - The number opens the name, `010-`, `020-` and so on, in the order the reader reads. A gap of ten leaves room for a page between two others.
  - A lookup page, which a reader looks up rather than reads in order, takes its topic as its name, with no number, such as `glossary.md`.
  - Every page but a README is read in order or looked up.
  - The folder's README lists its numbered pages and subfolders in number order. The README keeps its own name (ADR-069 point 3).
- **Breaks the rule:** a guide folder on no branch holds `turning-it-on.md` and `common-tasks.md`, read in that order, and neither name says so.
- **Keeps the rule:** the same pages on no branch, named `010-turning-it-on.md` and `020-common-tasks.md`, and a glossary beside them named `glossary.md`.
- **Note:** ADR-069 point 4 gives this rule a test as its check, which holds each README's list to the numbers, as the set's `checks` declare. It came with the first numbered folder, living-docs' guide (RS-LDOC-006).

## RS-REWORK-002 — A move keeps every address

When a page or a section moves, mend every link to it in the same change. Keep a moved section's old address on the page it left.

- **How:**
  - A move is a page moved or renamed, a section moved to another page, or a heading renamed, since a heading's text gives its address. RS-WRITE-016 decides whether a heading that text points to may move. This rule adds what a move owes.
  - Mend each link in the repository that leads to what moved. Look for the old path, and for the old address after its `#`.
  - A renamed heading keeps its old address as an HTML id on the line before it, such as `<a id="old-address"></a>`.
  - A section that leaves a page keeps its old address there as an HTML id, before a sentence that links where the section went.
- **Breaks the rule:** a rewrite on no branch drops the "(PRJ-006)" from the reference's heading "The permission-prompt diagnostic loop", with no HTML id. A link to `#the-permission-prompt-diagnostic-loop-prj-006` then lands at the page's top.
- **Keeps the rule:** the permissions reference holds `<a id="the-permission-prompt-diagnostic-loop-prj-006"></a>` on the line before that heading.
- **Note:** RS-USER-001 asks that readers' paths stay unbroken, and this rule says what a move owes them. RS-WRITE-016 keeps a heading that a pointer outside what the change can edit leads to, such as a link from an adopter's repository. Where that pointer is a link, the heading may be renamed if the old address still leads to it, as this rule's HTML id does.

## RS-REWORK-003 — Cite only what ships

Cite on a user page only the records the core and the capabilities ship, cite no issue, and link nothing under `tech-docs/`. A page that ships links nothing that does not ship, but its guide's README.

- **How:**
  - A citation is the id of a record or an issue in what the page shows its reader, with a link or without. Headings count, and code blocks, command output, comments and front matter do not.
  - project-kit's own records are its ADRs and its PRJs. A statement that rests on one keeps it as an anchor in the front matter (RS-LDOC-001), and the page neither cites nor links it.
  - A heading that cited such a record or an issue drops the citation, and keeps its old address (RS-REWORK-002).
  - A page that ships is one under `.pkit/` other than the release guide, `.pkit/release/README.md`. It links its guide's README at the `latest` tag (ADR-069 point 2), and nothing else that does not ship.
- **Breaks the rule:** the permissions README before the pilot, at commit `8f7ea252`, says "The design … is [ADR-060](../../tech-docs/architecture/decisions/ADR-060-path-scoped-workspace-allow.md)." It cites a record of project-kit's own, and links under `tech-docs/`, which never ships.
- **Keeps the rule:** ADR-060 stands among the permissions reference's anchors, and its text states the design with no citation: "The workspace's design is a path-scoped allow …"
- **Note:** on a page that ships, a link from outside what the change can edit may lead to any heading. RS-WRITE-016 lets such a heading drop its citation where the old address still leads to it.

## RS-REWORK-004 — A component's page reaches a backbone page through its area's README

On a page a capability or an adapter ships, link a backbone page only through its area's README, or name it by its role.

- **How:**
  - A backbone page is a page under `.pkit/` that no capability or adapter ships, such as the CLI reference.
  - Through its area's README means the link leads to the README of the folder that holds the backbone page, such as `.pkit/cli/README.md`. A link to a section of that README counts, since where the installed version lacks the section, the link still lands on the README.
  - By its role means the page names the backbone page by what it is for, such as "the CLI reference", with no link.
  - A decision record is no page, and RS-REWORK-003 says which a page may cite. A link to another capability's or adapter's page is outside this rule.
  - The rule does not reach a backbone page, nor a guide in `docs/`, whose links to the references all read one version.
- **Breaks the rule:** a capability's README on no branch links `../../cli/020-friction.md`, a page the backbone may number anew or move in a later version.
- **Keeps the rule:** the living-docs README links the schemas reference as `../../schemas/README.md#rule-set-files`, a section of the schemas area's README.

## RS-REWORK-005 — A long page opens with a generated contents list

Open a page of four or more second-level sections with a contents list of them, written by the contents generator.

- **How:**
  - The count leaves out the contents section itself.
  - The list stands right after the page's lead, under a second-level heading of its own, such as "Contents". It holds one item for each other second-level section, in the page's order.
  - The contents generator, `scripts/page_contents.py`, writes the list between the markers `<!-- pkit:contents -->` and `<!-- /pkit:contents -->` (`CONTRIBUTING.md`, "The pages' contents lists").
- **Breaks the rule:** the first pass of the permissions README, at commit `fe244502` of PR #2018, has nine second-level sections and no contents list.
- **Keeps the rule:** the permissions reference's "Contents" stands right after its one-line purpose, its list between the two markers.
- **Note:** the contents generator checks that the list is the one it writes, as the set's `checks` declare.
