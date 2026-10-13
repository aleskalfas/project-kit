---
rule-set: ANA
version: 1.0.0
inherits: [WRITE@1]
scope:
  types: [software-analysis:actor, software-analysis:term, software-analysis:use-case, software-analysis:journey]
rules: {}
---

# ANA — project-kit's rules for its analysis

These are the rules project-kit's analysis follows. The set holds no rule of its own yet, so the analysis follows the accepted rules of `WRITE`, which it inherits.

- **What it reaches:** every actor, glossary term, use case and journey, by the four types software-analysis declares (software-analysis DEC-001 point 2). The scope names no paths, so it reaches the analysis wherever software-analysis places it.
- **What it does not reach:** a revalidation record. A revalidation record is a held document, never an artefact, so no scope reaches it. Its words are a person's decision (RS-WRITE-013).
- **What it inherits:** `WRITE`, project-kit's general writing rules, pinned at `WRITE@1`. So `WRITE`'s accepted rules bind on the analysis through this set (COR-051 point 7).
- **Its rules, next:** the rule on the actor's voice and the rule that fills `RS-WRITE-002#labels` come with #1368.
- **Note:** how rules are named, accepted and inherited is the rule-set record's (COR-051). A rule binds only once it is accepted.
