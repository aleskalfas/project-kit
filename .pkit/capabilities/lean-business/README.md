# lean-business capability

lean-business guides a person through the lean method of validating a business model, as Ash Maurya's *Running Lean* (third edition, 2022) teaches it. An idea is sketched as canvases, one for each variant of its business model. The person judges each variant at the desk, for desirability, viability and feasibility, and shortlists the ones worth testing. Then they test the riskiest assumptions in short experiments, declared before they run, inside time-boxed cycles that end in a decision to persevere, pivot or pause. The capability keeps the record of all this as data, works out what follows from it, and leaves every judgement to the person. Install it in any repository where you want to decide what is worth building before building it: a product's own repository, or one kept only for exploring ideas.

"Lean business" here means validating a business model, not running a business at low cost.

## What this capability ships

- `decisions/` — the principles the capability fixes:
  - [lean-business:DEC-001-lean-business-discipline]: what it carries, its words, its seams with other capabilities, and how it credits the method.
  - [lean-business:DEC-002-lean-business-data-model]: an idea as a folder of data files that hold only what a person wrote or decided.
  - [lean-business:DEC-003-lean-business-process]: the processes of a variant, an experiment and a cycle, and why each judgement is the person's.

The schemas, process definitions, commands and skill these records decide are being built under project-kit#3426. This README lists them as they land.

## Adopter setup

Install:

```
pkit capabilities install lean-business
```

The ideas live in `lean-business/` at the repository's root, one folder per idea. The first command that writes an idea records that location in the capability's own configuration, `.pkit/capabilities/lean-business/project/config.yaml`. To keep the ideas elsewhere, record another location before the first idea ([lean-business:DEC-002-lean-business-data-model] point 1). An idea's data is as private as the repository that holds it.

## Credits and licence

The method is Ash Maurya's, from *Running Lean: Iterate from Plan A to a Plan That Works*, third edition (O'Reilly, 2022). The capability carries the method in its own words and ships no text of the book.

The canvas follows the Lean Canvas, Ash Maurya's adaptation of Alex Osterwalder's Business Model Canvas, both published under the Creative Commons Attribution-ShareAlike 3.0 licence. The capability uses the names of the canvas's boxes as its fields, describes them in its own words, and ships no file under that licence. Wherever it draws a canvas, it draws it with the credit and licence line beneath ([lean-business:DEC-001-lean-business-discipline]).

The names *Running Lean* and *Lean Canvas* may be trademarks of their owners. They are used here only to credit the source.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[lean-business:DEC-001-lean-business-discipline]`. Other capabilities and adopter content use the same form.

## Dependencies

None beyond the backbone. The capability reads no other capability. A later view may read its status's structured form, and the experiments' results may cite evidence records, without either becoming a dependency ([lean-business:DEC-001-lean-business-discipline]).
