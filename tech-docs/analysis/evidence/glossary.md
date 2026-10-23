---
builds-on:
  - analysis: core
    version: 2.0.0
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Ground each claim about an outside fact in a recorded excerpt of its source, with each citation checked against the evidence records.
TERM-evidence-record:
  name: evidence record
  noun-forms: [evidence records]
  status: active
  definition: "entry of a scope's YAML file that keeps a verbatim excerpt of an outside source, its origin and when it was fetched"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/evidence/schemas/evidence-record.yaml
        record:
          - evidence:DEC-001
          - evidence:DEC-002
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than evidence's floor, 1.26.0.
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Ground each claim about an outside fact in a recorded excerpt of its source, with each citation checked against the evidence records.

## TERM-evidence-record — evidence record

**Example:** the record `api-rate-limit` keeps a passage of an API's documentation on its rate limit, and a document cites it as `[ev:api-rate-limit]`.

**Distinctions:**

- **Citation:** the token `[ev:<slug>]` in a document, which names one record of its scope (DEC-001).
- **Snapshot:** a durable copy of the source, captured as the excerpt was fetched. The record holds only where the copy lies (DEC-002).
- **The fact:** what the excerpt says. `fetched_at` says when the excerpt was captured, never when the fact was true (DEC-002).
