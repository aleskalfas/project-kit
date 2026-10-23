---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-storyboard, name: storyboard}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Record a demo of my command line by running an executable storyboard, a document people read as it stands.
TERM-executable-storyboard:
  name: executable storyboard
  noun-forms: [executable storyboards]
  status: active
  definition: "Markdown document that scripts a demo of a command line step by step, which people read as it stands and the runner carries out directly"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/scripts/storyboards/parser.py
        record:
          - demo-recording:DEC-001
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `020-set-up`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than demo-recording's floor, 1.26.0.
  - **Term:** [storyboard](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-storyboard--storyboard)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Record a demo of my command line by running an executable storyboard, a document people read as it stands.

## TERM-executable-storyboard — executable storyboard

**Example:** a demo's document opens with its title, then `## Step 1 — <title>`, with prose for the reader and a fenced block whose tag names what the runner does.

**Distinctions:**

- **Storyboard:** the core's term for a document that scripts a dialogue with a person, which the file that carries it out follows. An executable storyboard runs commands, and scripts no dialogue.
- **Directive:** a fenced block whose language tag names what the runner does at that step. An unknown tag is a warning, so the document stays readable (DEC-001).
- **A generated file:** none exists. The document is the one source, and nothing is generated from it (DEC-001).
