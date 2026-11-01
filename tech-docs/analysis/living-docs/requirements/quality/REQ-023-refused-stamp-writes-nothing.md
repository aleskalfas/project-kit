---
id: REQ-023
title: A refused stamp puts back what it wrote, or names what it could not
status: active
statement: A refused `pkit living-docs new` leaves the project as it was, save a consented root change, or names each file or folder it could not restore.
measure: After a refusal, the project equals itself before the command ran, byte for byte, save what the refusal names and a consented root change.
applies-to: "`pkit living-docs new page` and `pkit living-docs new space`, whenever either refuses, a refusal after its write included."
obligation: v1:sha256:2d66814f7e6d216c9b3d6aa4a81b1d7390776bb89b31bb8dc8c6b595bc4d8179
actors:
  - core:ACT-developer
  - core:ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/_lib/stamp.py
        - tests/test_living_docs_new.py
      record:
        - living-docs:DEC-001#2
---

# REQ-023 · Quality · A refused stamp puts back what it wrote, or names what it could not

**Verified by:** Tests take a snapshot of the [project](../../../core/glossary.md#term-project--project) before a refusal of `new page` or `new space`, and find it unchanged after. Their refusals come before the write and after it. Among them are a write that brings a [validation](../../../core/glossary.md#term-validation--validation) error, a failed recording of the definitions location and an interruption. No test covers a file that cannot be put back.

**Rationale:** The [capability](../../../core/glossary.md#term-capability--capability)'s README makes [validation](../../../core/glossary.md#term-validation--validation) the [stamp](../../../core/glossary.md#term-stamp--stamp)'s one judge. A write that brings an error the [project](../../../core/glossary.md#term-project--project) did not have is put back, and the command refuses. So what it stamps passes `pkit living-docs validate` wherever the project passed it before, and a refusal leaves nothing half written.
