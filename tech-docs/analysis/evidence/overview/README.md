# Overview of the analysis of evidence

<!-- pkit:overview reads=5 fingerprint=sha256:a482125b007a3623e5db79735398f58d79d8cc64cc7a0859b74dee1fc0719ad9 -->

No record states what evidence is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of evidence under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis describes what evidence does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Areas

### 010-ground-claims

Ground each claim a project's documents make about an outside fact in a recorded excerpt of its source, so a reader can follow the claim to its source.

**Its concepts:**

- [010 — Outside facts and citations](../domain-model/010-outside-facts-and-citations.md)

**Its requirements:** none.

**Its use cases:**

- [UC-036 — Ground a claim in its source](../use-case-model/use-cases/010-ground-claims/UC-036-ground-claim.md)

**Its journeys:** none.

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [010-ground-claims](#010-ground-claims) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [010-ground-claims](#010-ground-claims) |

### Concepts

The [glossary](../glossary.md) defines each term.

Each view of the domain model explains a group of related concepts:

- [010 — Outside facts and citations](../domain-model/010-outside-facts-and-citations.md)

### Diagrams

`pkit analysis diagram --analysis evidence` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
