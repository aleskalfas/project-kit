---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-capability, name: capability}
      - {id: TERM-component, name: component}
      - {id: TERM-decision-record, name: decision record}
      - {id: TERM-finding, name: finding}
      - {id: TERM-harness, name: harness}
      - {id: TERM-install, name: install}
      - {id: TERM-package-metadata, name: package metadata}
      - {id: TERM-project, name: project}
      - {id: TERM-skill, name: skill}
      - {id: TERM-system, name: system}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Ground each claim about an outside fact in a recorded excerpt of its source, with each citation checked against the evidence records.
      - id: ACT-ai-agent
        name: AI agent
TERM-citation:
  name: citation
  noun-forms: [citations]
  status: active
  definition: "token of the form `[ev:<slug>]` in the text of a document, which names an evidence record by that record's `id`"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/evidence/scripts/validate.py
        record:
          - evidence:DEC-001
          - evidence:DEC-003
TERM-evidence-record:
  name: evidence record
  noun-forms: [evidence records]
  status: active
  definition: "entry that keeps a verbatim excerpt of the source of an outside fact, with where the source lies and when the excerpt was fetched"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/evidence/schemas/evidence-record.yaml
        record:
          - evidence:DEC-001
          - evidence:DEC-002
TERM-evidence-scope:
  name: evidence scope
  noun-forms: [evidence scopes]
  status: active
  definition: "directory whose root holds the YAML file of a fixed name keeping verbatim excerpts, with what lies below it up to the next such file"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/evidence/scripts/validate.py
        record:
          - evidence:DEC-002
TERM-outside-fact:
  name: outside fact
  noun-forms: [outside facts]
  status: active
  definition: "state of affairs beyond the project, which only a source elsewhere can confirm"
  replaces:
    - external fact
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/evidence/skills/evidence/add.md
        record:
          - evidence:DEC-001
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than evidence's floor, 1.26.0.
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [component](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-component--component)
  - **Term:** [decision record](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-decision-record--decision-record)
  - **Term:** [finding](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-finding--finding)
  - **Term:** [harness](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-harness--harness)
  - **Term:** [install](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-install--install)
  - **Term:** [package metadata](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-package-metadata--package-metadata)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [skill](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-skill--skill)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Ground each claim about an outside fact in a recorded excerpt of its source, with each citation checked against the evidence records.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)

## TERM-citation — citation

Explained in [VIEW-outside-facts-and-citations](domain-model/010-outside-facts-and-citations.md#citation).

**Example:** the sentence `The API accepts up to 1,000 requests per hour per client [ev:api-rate-limit].` carries one citation, which names the [evidence record](#term-evidence-record--evidence-record) `api-rate-limit`.

**Distinctions:**

- **A citation of a decision record:** a reference such as `[evidence:DEC-001-citation-discipline]`, which names a record of a [component](../core/glossary.md#term-component--component). The core's `pkit refs validate` checks it, never evidence (the [capability](../core/glossary.md#term-capability--capability)'s README).
- **A link or a footnote:** a citation is written as plain text, and holds no URL. The evidence record it names holds where the source lies (DEC-001).
- **The same text where the check skips it:** in a fenced code block or an HTML comment of a Markdown file, or in the scope's `evidence.yaml`. An excerpt there may quote such text from its source. There it is no citation (DEC-003).

## TERM-evidence-record — evidence record

Explained in [VIEW-outside-facts-and-citations](domain-model/010-outside-facts-and-citations.md#evidence-record).

**Example:** the record `api-rate-limit` keeps a passage of an API's documentation on its rate limit, and a document cites it as `[ev:api-rate-limit]`.

**Distinctions:**

- **Citation:** the token in a document that names the record. The record keeps the excerpt the [citation](#term-citation--citation) points to (DEC-001).
- **Snapshot:** a durable copy of the source, captured as the excerpt was fetched. The record holds only where the copy lies (DEC-002).
- **The outside fact:** what the excerpt bears out. `fetched_at` says when the excerpt was captured, never when the fact was true (DEC-002).

## TERM-evidence-scope — evidence scope

Explained in [VIEW-outside-facts-and-citations](domain-model/010-outside-facts-and-citations.md#evidence-scope).

**Example:** the directory `research/api-survey/` holds an `evidence.yaml`, so it is an evidence scope. A [citation](#term-citation--citation) in `research/api-survey/overview.md` names an [evidence record](#term-evidence-record--evidence-record) of that file.

**Distinctions:**

- **The `evidence.yaml`:** the file that holds the scope's evidence records. The scope is the directory that holds the file, with what lies below it (DEC-002).

## TERM-outside-fact — outside fact

Explained in [VIEW-outside-facts-and-citations](domain-model/010-outside-facts-and-citations.md#outside-fact).

**Example:** an API's documentation says that each authenticated client may issue up to 1,000 requests per hour. That limit is an outside fact, so a document that states it cites an [evidence record](#term-evidence-record--evidence-record). A licence's terms and a regulatory threshold are others.

**Distinctions:**

- **A fact of the project's own:** such as a path, a function or a decision of the [project](../core/glossary.md#term-project--project). Its source is the project itself, so no [citation](#term-citation--citation) backs it (the `evidence` [skill](../core/glossary.md#term-skill--skill)'s add operation).
- **The project's own conclusion:** a claim that no public source supports. It is written as the project's conclusion, with no citation. Or a working note of the project becomes its source, which an evidence record names (the `evidence` skill's add operation).
