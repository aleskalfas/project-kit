---
# A documentation space's definition (living-docs DEC-001 point 2): the rules
# the space's pages follow — the shared method, LDOC, inherited, and the
# space's own rules on top. It is a project rule set (COR-051), so the
# backbone validates it and checks the pin.
#
# To use it: copy it to `<definitions>/rule-sets/<space>.md` — `<definitions>`
# is the location living-docs declares, `living-docs/` under the internal
# documentation root, recorded on first use in
# `.pkit/capabilities/living-docs/project/docs-locations.yaml` — rename the
# set, write the title and the scope's paths, and name the file as the space's
# `definition` in `.pkit/capabilities/living-docs/project/config.yaml`.
#
# The scope says where the rules bind. LDOC takes no scope, so its rules bind
# on a page only through a set of the project's own whose scope selects the
# page (COR-051 point 7). Write the scope with the definition, and the rules,
# with the checks of their parts, bind on the space's pages from the first one.
# `paths` names the space's root, everything beneath it, and each place
# assigned to the space outside that root; `exclude` leaves out what lies
# under the root but belongs to another space. `types` selects the pages
# alone, never a definition, a record or a rule there. A place outside every
# root then gives the page type in `friction.places` (DEC-001 point 1).
# `pkit living-docs validate` names the scope to write for a definition
# without one.
#
# The user space adds one rule of its own: its readers' paths stay unbroken
# (DEC-001 point 3).
#
# A rule is `RS-<SET>-NNN`, with a body section headed by its id and title. It
# is an artefact of its own (COR-051 point 2), so it carries the friction block
# in its own container — for example:
#
#   RS-SPACE-001:
#     status: accepted
#     origin: {decision: "living-docs:DEC-001"}   # or {date, by, why}
#     pkit:
#       friction:
#         anchors: {record: ["living-docs:DEC-001"]}
rule-set: SPACE                   # rename: upper-case letters and digits, unique among rule sets
version: 1.0.0                    # the set's own version; an inheritor pins its major
inherits: [living-docs:LDOC@1]    # the shared method, pinned to its major
scope:                            # the space's pages (COR-051 point 2)
  paths: ["<root>/**"]            # the space's root, then each place assigned to it
  types: [living-docs:page]       # the pages alone
rules: {}                         # the space's own rules, each added when it is needed (RS-LDOC-006)
---

# The <space> space's definition

The rules the <space> space's pages follow: the shared method, `living-docs:LDOC`, and the rules below. The scope above selects the space's pages, so these rules bind on them. The space's entry point and places are in `.pkit/capabilities/living-docs/project/config.yaml`.
