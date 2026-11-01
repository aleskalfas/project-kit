# visual-communication capability

Visual work made from reusable parts. A *piece*, such as a presentation or a figure in a documentation page, keeps its content as data. Libraries give it its look: components that arrange and draw the content, brands that hold the values (colours, fonts, sizes), and notations that say what a thing is. Several renderers draw the same piece: SVG, HTML, PDF and Mural. A project installs the capability when its visuals should share a look, reuse what was made before, appear under more than one brand or in more than one language, and be checked like the rest of its work.

## What this capability ships

At 0.1.0 the capability ships the decisions of its architecture. The engine, `pkit visual`, follows in the work built on them.

- `decisions/DEC-NNN-*.md`: the principles every piece, library and renderer follows.

## Adopter setup

Install:

```
pkit capabilities install visual-communication
```

Nothing to configure yet: the configuration comes with the commands.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename
stem: `[visual-communication:DEC-001-<slug>]`. Other capabilities and adopter content
use the same form.

## Dependencies

None at 0.1.0.
