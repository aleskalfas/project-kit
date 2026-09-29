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
# set, write the title, and name the file as the space's `definition` in
# `.pkit/capabilities/living-docs/project/config.yaml`.
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
rules: {}                         # the space's own rules, each added when it is needed (RS-LDOC-006)
---

# The <space> space's definition

The rules the <space> space's pages follow: the shared method, `living-docs:LDOC`, and the rules below. The space's entry point and places are in `.pkit/capabilities/living-docs/project/config.yaml`.
