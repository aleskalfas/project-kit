---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# One reviewer judges a change against the rules that govern what it touches

A design for #1385, which also designs the merge-gate trigger of #1386. The maintainer asked for both on 8 October, before the rest of the analysis build.

- **Paths:** `PM/` is `.pkit/capabilities/project-management/`, `LD/` is `.pkit/capabilities/living-docs/`, and `SE/` is `.pkit/capabilities/software-engineering/`.
- **Read from main** at commit `78837af9`. Every line number cited here is of that commit.
- **Citations:** by file and line, as the brief for this note asks. RS-WRITE-014, which would drop line numbers, is still proposed and binds nothing.
- **The kind note:** `.pkit/scratchpad/active/2026-10-05-analysis-kind-structure.md`, the design for #1352. This note builds on its reading of scope and its preview.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers "Questions", and the project manager files "Slicing".

## The question

How does one reviewer judge a change against the accepted rules that govern each artefact it touches, and when does the merge gate require it?

- **The maintainer's words, 8 October:** specialised reviewers should not be prompted with fixed rules.
- **What he asked for instead:** one general reviewer that gets the rules governing each changed document. It serves user pages, technical pages and the analysis alike.
- **Why one:** it is "a general mechanism corresponding to the rules general mechanism", that is, to the rule sets of COR-051.
- **It replaces** the separate analysis reviewer and page reviewer proposed earlier on 8 October (#1385, "Related").

## Today

No reviewer at the merge gate reads a rule set, and no rule set in project-kit declares the scope a reviewer would read.

### Who reviews a pull request that changes documentation or the analysis

The gate resolves its reviewers from the closing issue's classification and from whether the diff touches code (project-management DEC-032 point 1).

- **`pm-reviewer`:** the project's baseline, on every pull request (`PM/project/config.yaml:120-121`).
- **`docs-reviewer`:** on every classified pull request, through `type: "*"`, and on any diff that touches code (`SE/review-contributions.yaml:58-62`).
- **`code-reviewer` and `security-reviewer`:** only when the diff touches code. A Markdown file is documentation (`PM/scripts/_lib/required_reviewers.py:738` and `:776`).
- **An unclassified pull request that touches no code:** `pm-reviewer` alone. software-engineering names that gap and accepts it (`SE/review-contributions.yaml:27-30`).

So a classified change to a page or to an actor draws two reviewers: `pm-reviewer` and `docs-reviewer`.

### What those two check

- **`pm-reviewer`:** the branch, the title, the classification, the closing link, migrations and shared files (`PM/agents/pm-reviewer.md:60-67`).
- **`docs-reviewer`:** three lenses (`SE/agents/docs-reviewer.md:29-33`).
  - It blocks on new public surface left undocumented, and on a doc that contradicts the code (`:45-48`).
  - Clarity and style findings are advisory (`:49`).
  - It reads a project's own rules from the `<project-conventions>` overlay category (`:39-41`). project-kit's overlay defines no such category (`.pkit/agents/project/overlay.yaml`), so it reviews as a generalist.
- **Neither reads a rule set.** The rules that govern a page or an actor reach neither prompt.

### What scripts check

The check aggregator runs `pkit validate` and `pkit friction check` on every pull request (`scripts/check.sh:159-161`).

- **The rule-set pass:** the checks COR-051 asks for, such as origins, ids, the join between data and prose, and inheritance (`src/project_kit/rule_sets.py:1-40`).
- **living-docs' pass:** the checkable parts of its rules. A page's sections against its kind's structure (RS-LDOC-004), its `reader` resolving, and its anchors.
- **software-analysis' pass:** each artefact's front matter and placeholders.
- **The change check:** every artefact whose anchors changed carries an answer (COR-050 point 6).

### What nobody checks at the gate

- **`WRITE` on the analysis.** project-kit's operational rules send whoever writes the analysis to `WRITE` (`.pkit/rules/project.md` rule 3). No check and no reviewer holds a change to it.
- **The parts of `LDOC` and `USER` that need judgement.** Examples are "every statement is grounded by the page's anchors", "each fact is stated once", and "says only what that reader needs" (`LD/rule-sets/ldoc.md:73-81`).
  - The living-docs agent judges them in a reader-review, and only when someone asks (`LD/agents/living-docs/living-docs.md:38` and `:119`).
- **So a change can break an accepted rule and still pass every review.** A 40-word sentence in an actor, or a fact a second page already states, would draw no finding from either reviewer.

### What coverage data exists

The artefacts document names, on each artefact, the rule sets whose scope covers it, and today it names none.

- **The key:** `in_scope_of`, added by #1361 (`src/project_kit/friction_discovery.py:2564-2581` and `:2808`).
- **Measured on `78837af9`:** `pkit friction artefacts --json` lists 111 artefacts, and `in_scope_of` is empty on every one.
- **Why:** no rule set in project-kit declares `scope`.
  - **`WRITE`:** "This set has no scope of its own" (`tech-docs/rule-sets/writing.md:52`).
  - **`TECH` and `USER`:** each inherits `living-docs:LDOC@1` and declares no scope (`tech-docs/living-docs/rule-sets/technical.md:1-6` and `user.md:1-5`). They bind through living-docs' assignment of places to spaces (`LD/project/config.yaml:13-44`).
  - **`LDOC`:** no scope. It binds through living-docs' own check.
- **A scope is checked for shape only** (`.pkit/schemas/README.md:519`). Nothing reads it but the artefacts document.
- **So a trigger on `in_scope_of` would fire on nothing in project-kit today,** and a reviewer reading it would find no rules. Part 2 says what coverage needs.
