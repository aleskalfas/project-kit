# Share the grammar, lock every delivered talk

The idea he senses he is missing already exists, and it has a standard file format. It is **design tokens**: the design language stored as named data in tiers. The first tier holds raw values. The second holds roles such as "accent", "surface" or "primary text". An optional third holds values for one part of one component. Components do not derive from this language. They **bind** to the role names, and switching the theme swaps the values behind those names. The word "projection" fits a different relation: the one from his logical layer to HTML, Mural or Figma. His two talks follow the pattern that design-system practice predicts. Reuse gathers in the foundations (theme and frame) and in a few small blocks that do not depend on any message. The content diagrams are "snowflakes", one-offs that are expected and healthy. They belong in a labelled place inside the talk, and a shape is promoted to the shared library only after it has appeared about three times. Freedom for one-offs comes from making the shared layer a **grammar**: primitives, layout operators and defaults that make a new diagram cheap. A catalogue of finished diagrams does not give that freedom. On updates, every tool surveyed has the consumer **pull** changes rather than having the library push them. A talk being drafted may follow the newest library. A delivered talk records exact versions, keeps a static export, and changes only through a deliberate upgrade with a before-and-after preview. His refusal to touch delivered talks applies the same principle as a lockfile. In visual work even a "patch" changes the picture.

## The missing concept is a design language stored as tokens that components bind to

Design-system writing uses a few words loosely, so the first step is to fix them. The Nielsen Norman Group defines a **design system** as "a complete set of standards intended to manage design at scale using reusable components and patterns". It usually contains a style guide, a component library and a pattern library ([NN/g](https://www.nngroup.com/articles/design-systems-101/)). A **design language** sits above the design system: it is the brand's visual and verbal identity. The cleanest example is also one of his own contexts. Carbon, IBM's open-source design system, is built on the IBM Design Language, which Carbon calls "the digital expression of the IBM brand". Carbon delivers that language as "foundations, components, patterns, and code" ([Carbon](https://carbondesignsystem.com/all-about-carbon/what-is-carbon/)). So the language is not itself a component library. It is what the library expresses.

The step that turns a design language into data is called **design tokens**. The standard defines a token as "information associated with a human readable name, at minimum a name/value pair", for example `color-text-primary: #000000` ([DTCG Format 2025.10](https://www.designtokens.org/TR/2025.10/format/)). Adobe's Spectrum says directly that "primitive tokens define the available values in the design language" ([Spectrum](https://spectrum.adobe.com/page/design-tokens/)). Brad Frost describes tokens as the low-level definitions that "make up a design language", and he keeps them in their own layer so the brand language can be themed and versioned apart from the components ([Frost 2023](https://bradfrost.com/blog/post/the-design-system-ecosystem/)). Mature systems settle on **three tiers**. The table shows how the names differ between systems. The last column is an illustration for his tool, not taken from any source.

| Tier, in plain words | Material 3 | Spectrum | Carbon | Illustration for his tool |
|---|---|---|---|---|
| Raw values | reference, `--md-ref-*` | primitive, `blue-800` | palette, `$blue-60` | `palette.blue-60`, `font.sans` |
| Roles: what a value is for | system, `--md-sys-color-primary` | semantic, `accent-background-color-default` | role tokens, `$text-primary` | `color.accent`, `color.surface`, `space.gap-m` |
| One part of one component | component, `--md-filled-button-container-color` | component-specific, `tooltip-maximum-width` | "component-specific variables" | `chip.background`, `footer.rule-color` |

Sources: [Material Web](https://material-web.dev/theming/material-theming/), [Spectrum](https://spectrum.adobe.com/page/design-tokens/), [Carbon themes](https://carbondesignsystem.com/elements/themes/overview/).

**Themes work at the middle tier.** Carbon states the rule plainly: "Tokens are universal and never change across themes", and a theme is "a collection of visual attributes assigned to the tokens" ([Carbon themes](https://carbondesignsystem.com/elements/themes/overview/)). The token `$text-primary` is near-black in the White theme and near-white in the Gray 100 theme, but its name never changes. This gives his "themes can be switched" decision a precise rule: **components refer to role names, never to raw values**, or a theme switch cannot reach them. Atlassian warns against choosing a token because its colour "looks similar", "since this can break the experience in other themes" ([Atlassian](https://atlassian.design/foundations/tokens/design-tokens)).

The format is now stable enough to adopt. The W3C Design Tokens Community Group published its **first stable version, 2025.10, on 28 October 2025**. It has three modules: Format, Color and Resolver ([W3C CG](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/)). It is a Community Group report, not a W3C Standard ([Format 2025.10](https://www.designtokens.org/TR/2025.10/format/)). The **Resolver** module is the part he needs for themes. It describes "modifiers" such as theme or brand, each with named contexts such as light, dark or brandA. One set of token files then yields every combination without copying files ([Resolver 2025.10](https://www.designtokens.org/TR/2025.10/resolver/)). Tool support is real but uneven. Style Dictionary is a reference implementation of the standard. It merges all token files into one tree, then runs per-platform "transforms" and "formats" that turn the same token into a CSS variable, an Android resource or a Swift constant ([Style Dictionary](https://styledictionary.com/info/architecture/)). Yet it still lacks full 2025.10 support ([Style Dictionary DTCG](https://styledictionary.com/info/dtcg/)). Figma imports and exports its variables as DTCG JSON ([Figma](https://help.figma.com/hc/en-us/articles/15343816063383-Modes-for-variables)).

With these words in place, his phrase "a design language defined in a unified way, with components as its projection" splits into two different relations. **Between the language and the components, the relation is binding, not projection.** Material 3 shows the chain. A filled button's container colour is a component token. It points at the system token `--md-sys-color-primary`, which in turn points at a reference value ([Material Web](https://material-web.dev/theming/material-theming/)). The component's structure stays fixed, and its look is looked up through these references. **Between the logical layer and HTML, Mural or Figma, the relation is projection.** Style Dictionary is a mature, working example of such projection, but for values only. No established pipeline exists for structure. Carbon, Material and Spectrum each write their components by hand for every framework. Frost calls this the "technology-specific implementation" layer ([Frost 2023](https://bradfrost.com/blog/post/the-design-system-ecosystem/)).

The closest public attempt to keep components themselves as data is Adobe's **Spectrum Design Data** specification. It is still `1.0.0-draft`. It stores each component's anatomy, options and state model as validated JSON, in layers that go from foundation to platform to product ([Spectrum Design Data](https://opensource.adobe.com/spectrum-design-data/spec)). That points to the second half of the missing concept: separating a component's specification from its implementation.
- A **component specification** names the parts and slots, the options, the states, and the token each part uses. It belongs in his logical layer, as data.
- A **component implementation** exists once per renderer. In his tool it is the adapter code.

Under this split, a "UI kit" in Figma is one projection of the library, not its source.

## Reuse belongs in the foundations, and the 38 diagrams are healthy one-offs

### His two talks follow the curve the field reports

Brad Frost sorts reusable work into three tiers that fit his evidence closely.
- **Design system components** are "shared, content-agnostic, and context-agnostic built for maximal reuse".
- **Recipes** are arrangements of those components that "may only apply to one product".
- **Snowflakes** are one-offs that "don't really get reused outside of their first use case".

([Frost 2021](https://bradfrost.com/blog/post/design-system-components-recipes-and-snowflakes/))

Here is how his two talks map onto those tiers:
- **The frame** he carried into the second talk (slide, section slide, footer line and theme) is foundations plus templates.
- **The two small building blocks** are system components: small, and free of any particular message.
- **The first talk's content components** were tied to their messages, so they did not travel.
- **The 38 diagrams** are snowflakes.

That is the expected shape, not a failure of reuse.

Broader data points the same way, though the evidence is thin. In zeroheight's 2025 survey of 294 practitioners, **tokens were present in 84% of systems, up from 56% a year earlier, and UI patterns in 64%** ([zeroheight 2025](https://zeroheight.com/how-we-document)). At Pinterest, the share of design layers that came from the shared library ranged from **about 50% on one team to about 2% on another** ([Figma blog](https://www.figma.com/blog/how-pinterests-design-systems-team-measures-adoption/)). NN/g notes that pattern libraries are "often thought of as less robust compared to component libraries" ([NN/g](https://www.nngroup.com/articles/design-systems-101/)).

Presentation tools share the same layers:
1. tokens;
2. a frame drawn on every slide;
3. named layouts with slots;
4. blocks placed inside a slide;
5. ways to override a single slide.

When no layout fits, Microsoft's own advice is to choose the Blank layout and add your own placeholders ([Microsoft](https://support.microsoft.com/en-US/PowerPoint/edit-and-re-apply-a-slide-layout)). The pattern that emerges is that **the more a part depends on its message, the less it is reused.** No source measures reuse per layer, and none studies slide or diagram libraries specifically. Treat this as a consistent pattern, not a measured law.

### Promote parts on evidence of reuse, not on hope

The field does not ban one-offs. It gives them a known place and promotes them when they repeat.
- **Dan Mall's threshold:** if one team needs a component, wait; if two teams need it, wait longer. "If three or more teams need a component right now or very soon … that's a good candidate", because "Design systems exist to solve common problems" ([Dan Mall](https://v5.danmall.com/posts/three-times-is-a-pattern/)).
- **GOV.UK's first gate** asks that a proposal be **useful**, backed by links to versions already used in different services, and **unique**, so that it does not duplicate something already in the system ([GOV.UK](https://design-system.service.gov.uk/community/contribution-criteria/)).

For a single author, "three teams" becomes "three talks", and the evidence of use is the one-offs he has already drawn.

Frost recommends a standard folder for one-offs next to the system, with neutral names such as `/one-offs` or `/departures`. The owner can then audit them and lift good ones into the system. In his words, "even deviations still work with the grain of the system" ([Frost 2018](https://bradfrost.com/blog/post/where-to-put-one-off-components/)). Nathan Curtis adds that fixes and small improvements are frequent and cheap, while new components are rare and costly ([Curtis 2020](https://nathanacurtis.substack.com/p/defining-design-system-contributions-eb48e00e8898)). So tweaking an existing part should be frictionless, and only a new shared part should need more ceremony. His remark that content elements "evolve more often" points the same way. Elements built for one message keep being rebuilt, because they never belonged in a shared library.

### A grammar, not a catalogue, keeps one-offs cheap

The 38 diagrams raise the real design question: what can be shared when the finished pictures cannot? Research on visual grammars answers it.
- **Wickham's layered grammar of graphics** (the basis of ggplot2) lets authors "move beyond named graphics (e.g., the scatterplot) and gain insight into the deep structure". It splits a graphic into independent parts (data, mappings, marks, scales, coordinates), and each can be changed on its own. A **hierarchy of defaults** means a short specification still yields a complete picture ([Wickham 2010](https://vita.had.co.nz/papers/layered-grammar.pdf)).
- **Vega-Lite** fills in partial specifications with "smart defaults". It has a `repeat` operator that draws one sub-view for each entry in a list. It compiles down to the lower-level Vega for authors who need finer control ([Vega-Lite paper](https://idl.cs.washington.edu/files/2017-VegaLite-InfoVis.pdf)).
- **Penrose** separates three things. The **Domain** is the types and relations a kind of diagram accepts. The **Substance** is one diagram's content. The **Style** is how a domain is drawn. As a result, one program encodes "a family of possible visualizations, rather than one specific diagram". The same set relations appear as nested disks under one Style and as a tree under another ([Penrose](https://penrose.cs.cmu.edu/media/Penrose_SIGGRAPH2020.pdf)).

For his tool, the shared layer should therefore contain:
- **primitives** such as box, text and connector;
- **layout operators**: stack, align, distribute and repeat;
- **defaults**;
- **a few "kinds" of diagram.**

The kinds are what Wickham calls "subgrammars for particular families of plots". With these in place, a one-off costs a few lines that combine shared parts, and it automatically wears the current theme.

Two engineering lessons come with this approach.
1. **The grammar needs a stopping point before general code.** Vega's expression language is "a restricted subset of JavaScript" with no assignment and no loops. The aim is to "keep the expression language simple, secure and free of unwanted side effects" ([Vega](https://vega.github.io/vega/docs/expressions/)). It is the precedent for arithmetic formulas over a list item's position, the list's length and tokens. Such formulas stay data and render the same way in every renderer.
2. **Layout should be deterministic and local.** Penrose's optimiser starts from random samples, it "can't guarantee" a valid diagram, and the paper describes no way to pin positions ([Penrose](https://penrose.cs.cmu.edu/media/Penrose_SIGGRAPH2020.pdf)). The authors of Bluefish first built on the Cassowary constraint solver, then dropped it because "a global solver increases viscosity". They switched to local rules, in which each position or size has exactly one owner and a second writer is an error ([Bluefish](https://arxiv.org/html/2307.00146v4)).

Manual adjustments belong in an override layer keyed by **stable ids**. Structurizr keeps manual positions outside its source. It warns that if the keys of its views are generated automatically, "you will likely lose manual layout information" ([Structurizr DSL](https://docs.structurizr.com/dsl/language)).

Freedom also needs a sanctioned way out. Figma separates two kinds of change. One is a change made through the allowed settings, called overrides, such as text, fills, or a swapped nested part. The other is leaving the system: **detaching** turns an instance into a plain copy, after which Figma will "no longer apply any changes made to the component" ([Figma detach](https://help.figma.com/hc/en-us/articles/360038665754-Detach-an-instance-from-the-component)). Teams read detach counts as a to-do list. The athenahealth design-systems lead says, "If someone in our organization is detaching a component, I want to know why". The causes named are bugs, missing features, and combinations nobody expected ([Figma blog 2025](https://www.figma.com/blog/design-systems-104-making-metrics-matter/)). His tool can copy a shared part into the talk's one-off area and record its origin and version. Every departure is then both free and visible when he reviews one-offs for promotion.

## Eight levels in three scopes give each part one owner and one rhythm

The best-known layering, Frost's Atomic Design, has five levels: atoms, molecules, organisms, templates and pages. Its author calls it "not rigid dogma", and it allows organisms to contain other organisms, so the nesting has no fixed depth ([Atomic Design](https://atomicdesign.bradfrost.com/chapter-2/)). Large systems such as Carbon organise themselves as foundations, components and patterns instead ([Carbon](https://carbondesignsystem.com/all-about-carbon/what-is-carbon/)). The idea from Atomic Design that has lasted is the split between a template and a page. Templates are "page-level objects that place components into a layout". A page is a template filled with real content. For him, that is a slide layout and a filled slide.

His components nest to any depth, so he does not need the chemistry names. He needs levels that differ in **who owns them, how often they change, and whether a change may reach a delivered talk**. The table proposes eight levels inside the logical layer, grouped into three scopes:
- **Shared core:** used across all contexts.
- **Per context:** one library for DAM, one for IBM.
- **Per talk.**

| Level | Established term | Holds | Scope | Changes |
|---|---|---|---|---|
| 1. Tokens | design tokens: primitive, semantic, component | raw values; roles such as accent, surface, primary text, medium gap; a few per-part values | role names in the shared core, values per context | when a brand changes |
| 2. Themes | themes, modes; Resolver modifiers | named value sets along separate axes: context (DAM, IBM), mode (light, dark, inverse section), scale (projector slide, dense board) | per context | rarely |
| 3. Primitives and layout operators | atoms; layout relations | box, text, connector, icon; stack, align, distribute, repeat; restricted formulas | shared core | slowest of all |
| 4. Components | design system components, content- and context-agnostic | his two small building blocks; chips, callouts, labels | shared core | often, mostly small changes |
| 5. Recipes and diagram kinds | patterns, recipes, subgrammars | recurring compositions with defaults, such as a timeline, a comparison or a layered stack | shared core or per context, after about three uses | as they are promoted |
| 6. Frame | template; slide master and layouts with named slots | slide, title slide, section slide, footer line, grid | per context | about yearly |
| 7. One-offs | snowflakes, departures, detached copies | the 38 diagrams; any copied and changed part, with its origin | per talk | never shared |
| 8. Talk | page, instance, document | the material, the frame layouts it uses, its one-offs, overrides by stable id, and its version lock | per talk | frozen once delivered |

Two pieces sit outside the logical layer, one on each side.
- **Above it is the brand guide**: logo, imagery, and tone of voice. These are kept outside the token system in practice. Atlassian, for example, links its token documentation to a separate brand kit ([Atlassian](https://atlassian.design/foundations/tokens/design-tokens)).
- **Below it are the renderers**: HTML, Mural and Figma adapters. Frost calls these "technology-specific implementations", and DTCG calls them translation tools.

A context library should be **a set of values, a frame, and a few parts that only that brand uses**. It should not be a fork of the components. Infinum's case study shows both versions of this choice. A client with four brands kept three Figma files per brand, twelve in all, so every shared update had to be repeated in each one. They moved to one shared component set whose look is driven by tokens. They put the brand-flavoured, more variable parts (banners, cards, templates) in per-brand files, and they built the components in grey first, adding brand styling afterwards ([Infinum](https://infinum.com/blog/multibrand-design-system-tokens/)). Frost reports that customised brand versions mostly change colour and typography ([Frost 2022](https://bradfrost.com/blog/post/the-many-faces-of-themeable-design-systems/)).

Three precedents show how a context library can be organised:
- **Quarto's `_brand.yml`** is one YAML file holding colour roles, logos, typography and light/dark variants. It applies across HTML, reveal.js and Typst output, and each project keeps its own copy ([Quarto brand](https://quarto.org/docs/authoring/brand.html)). It is the closest existing precedent for "one library per context".
- **Spectrum's theme element** has three independent switches: `system` (which Adobe product family), `color` (light or dark) and `scale` (desktop or mobile) ([sp-theme](https://opensource.adobe.com/spectrum-web-components/tools/theme/)). This supports keeping context, mode and output scale as separate axes rather than one list of themes.
- **For the IBM context, much of the value set already exists.** Carbon's four themes (White, Gray 10, Gray 90 and Gray 100) are light and dark versions of one brand, and teams make a new theme by changing the default values ([Carbon themes](https://carbondesignsystem.com/elements/themes/overview/)).

There is a cost to building ahead of need. One practitioner describes a lead designer who spent a week building four brand themes, each with dark and high-contrast modes, for brands that did not yet exist. He also describes tracing a wrong colour through several layers of references ([DEV](https://dev.to/alexandersstudi/multi-brand-design-systems-are-a-massive-waste-of-time-3b7f)). The author sells a token tool, so read his account with that in mind. The number of combinations is the product of the contexts on each axis ([Resolver 2025.10](https://www.designtokens.org/TR/2025.10/resolver/)), so every speculative mode multiplies the work. Infinum's lesson pulls the other way: role tokens alone made it hard to adjust a single brand, and next time they would add component-level tokens earlier ([Infinum](https://infinum.com/blog/multibrand-design-system-tokens/)). His two contexts are real, so building for two brands is not premature. The sound sequence is:
1. Start with raw values and roles.
2. Add component tokens only where a context actually differs.
3. Add modes and scales when a real talk needs them.

## Where the research backs his decisions and where it pushes back

| His decision | Verdict | What the research says |
|---|---|---|
| The logical layer is the source; renderers only project it | **Fits, at a cost** | Style Dictionary, Structurizr's exporters, and Vega-Lite compiling to Vega all work this way. Every projection loses something, and no tool projects structure natively to all of his targets |
| Components are data, all the way down | **Fits, with limits** | Spectrum Design Data and Penrose keep components or diagram families as data, and Frost wants components "intentionally dumb" ([Frost 2023](https://bradfrost.com/blog/post/the-design-system-ecosystem/)). Composition needs renderer primitives at the bottom and a restricted formula language at the top |
| The layer holds its own component libraries and themes | **Fits, if split further** | Tokens need their own layer and their own version, because they change on a different rhythm ([Curtis 2018](https://nathanacurtis.substack.com/p/versioning-design-systems-48cceb5ace4d)) |
| Themes can be switched | **Fits only if themes swap values** | Carbon: role names stay, values change. **Conflicts** if a "theme" also moves layout, shapes or structure |
| One template library per context | **Fits** if a context library is values, a frame and a few brand-only parts | Infinum, Quarto and Carbon. **Conflicts** if each context forks the components |
| A design language with components as its projection | **Conflicts with established usage** | The language is the brand's identity and its range of values. Components bind to it, and projection runs from model to renderer. No standard goes beyond tokens toward a formal language that components are generated from; Spectrum's draft comes closest |
| Delivered talks are never updated | **Fits** | This is the principle behind lockfiles, Figma's opt-in updates and Quarto's vendored extensions |

**A theme should not carry structure.** Slidev, one of the closest tools to his plan, says themes "should focus on appearance" and leaves features to add-ons ([Slidev](https://sli.dev/guide/write-theme)). D2 shows what happens otherwise. Its Terminal theme changes letter case, corner radius, font and borders, and D2's own documentation admits that "many of the properties apparent in the diagram do not appear in the source" ([D2 themes](https://d2lang.com/tour/themes)). In his tool the separation should be clean:
- **A theme** is values bound to roles.
- **The frame** is a per-context template.
- **Switching context** swaps both the theme and the frame.
- **Switching mode** swaps values only.

**Projection to several renderers is his least proven bet.** Structurizr's exporters "do not support all available shapes/features" compared with its own renderer, and the documentation does not record what each format loses ([Structurizr export](https://docs.structurizr.com/export)). Slidev's PowerPoint export takes one of two routes. It can flatten each slide into an image, in which case "the text will not be selectable". Or it can rebuild native shapes, but SVG then stays as pictures, theme decorations are dropped, and fonts are not embedded ([Slidev export](https://sli.dev/guide/exporting)). The best precedent is Quarto. Its source names a small set of slide kinds, and its PowerPoint renderer maps each kind to a layout of the same name in the client's own template: Title Slide, Section Header, Two Content and so on ([Quarto PowerPoint](https://quarto.org/docs/presentations/powerpoint.html)). In Keynote, placeholders carry tags, and when a slide switches layout its content moves to the placeholder with the matching tag ([Apple](https://support.apple.com/guide/keynote/tan7a2b69972/mac)).

The research found **no tool that renders one component definition natively into HTML, a slide tool and a design tool at once**, so here his tool goes beyond prior art. The research also found nothing on whether Mural has any notion of variables or themes. The likely path is to resolve tokens into literal values before pushing to Mural, but this is unverified. Figma, by contrast, has variables with modes and imports DTCG files. The contract between the logical layer and the renderers should therefore be:
- **layout names and slot roles**, not CSS class names;
- **a declared feature list for each renderer**;
- **a report of what each render lost**.

D2's layout engines show why the feature list matters: locking an element's position works only under one of its three engines ([D2 layouts](https://d2lang.com/tour/layouts/)).

**"All the way down" must not tax the one-off.** Penrose's authors concede that writing diagrams in a language makes it "more difficult for (say) visual artists and designers to contribute new representations" ([Penrose](https://penrose.cs.cmu.edu/media/Penrose_SIGGRAPH2020.pdf)). If a one-off is painful to write as data, the 38 diagrams will escape the tool entirely. Structurizr keeps a door open with its `image` view, which accepts a picture drawn elsewhere ([Structurizr DSL](https://docs.structurizr.com/dsl/language)). A comparable way to embed a hand-drawn or renderer-native object keeps the creative floor low. The cost is that such objects do not change with the theme.

## Updates should be pulled, locked and previewed, never pushed

Presentation tools deliver shared changes in four ways, and he should choose among them on purpose.
1. **Copied when the deck is created.** A PowerPoint template is copied into each new deck, so a later template update never reaches decks already made. Microsoft's advice for moving a deck to a new template is to start a new file from the template and paste the old slides in ([Microsoft](https://support.microsoft.com/en-US/PowerPoint/apply-a-template-to-an-existing-presentation)).
2. **Linked, with explicit acceptance.** In Figma, a badge announces library updates, and the editor of each file reviews them side by side and chooses Update for one asset or Update all ([Figma review](https://help.figma.com/hc/en-us/articles/360039234193)). Google Slides' linked slides refresh only when someone clicks Update, and the link can be cut ([Google](https://support.google.com/docs/answer/7009814?hl=en)).
3. **Resolved by reference at build time.** Slidev names its theme by package name or local path and loads it whenever the deck is built ([Slidev](https://sli.dev/guide/theme-addon)).
4. **Copied into the project and updated on command.** Quarto tells users to commit extensions into the project so it does not depend on a package manager or on old versions staying available. `quarto update` asks for confirmation before changing anything ([Quarto extensions](https://quarto.org/docs/extensions/managing.html)).

A tool that renders from source behaves like the third model by default. That is the dangerous model: without a pin, any change to a library silently repaints every old talk the next time it is rendered.

Software solves this with two separate controls. A **version range** says which updates are allowed: `^1.0.4` accepts minor and patch releases ([npm semver](https://docs.npmjs.com/about-semantic-versioning)). A **lockfile** records "the exact tree that was generated", so every later install is identical ([npm lockfile](https://docs.npmjs.com/cli/v10/configuring-npm/package-lock-json)). Semantic versioning numbers releases as MAJOR.MINOR.PATCH, where only a MAJOR release may break existing use. On that basis Carbon promises that on a minor or patch update "you should feel confident that you can update without anything breaking" ([Carbon versioning](https://raw.githubusercontent.com/carbon-design-system/carbon/main/docs/guides/versioning.md)).

That promise holds for code behaviour. **It does not hold for pictures.** A padding fix is a patch in code terms, yet it still changes every slide that uses the component. Figma's rules show the same sensitivity: overrides survive a change only when "the layer names … must match" ([Figma overrides](https://help.figma.com/hc/en-us/articles/360039150733-Apply-overrides-to-instances)). In visual work, "breaking" therefore means "renders differently". So ranges suit only talks still being drafted, and **delivered talks need exact pins**. The table gives the lifecycle this implies.

| Talk state | Follows | Mechanism | Precedent |
|---|---|---|---|
| Drafting | newest compatible shared core and context library | a version range, re-checked on each render | npm ranges; Slidev themes loaded by reference |
| Delivered | exactly what was shown | an exact lock on every library and the renderer, old versions kept available, a static export archived | `package-lock.json`; Quarto's committed extensions; PDF |
| Reused for a new audience | chosen newer versions | copy the talk, then run an explicit upgrade with a before-and-after preview for each slide | Microsoft's "new file and paste"; Figma's Update and Update all |

The tools offer three strengths of protection, and they combine well.
1. **Pinning by reference** keeps a link back to the library, so a deliberate upgrade stays possible. It requires the old version to stay retrievable.
2. **Copying the library into the talk** survives anything, but makes later upgrades awkward. Slidev's "eject" copies a theme into the deck's own folder ([Slidev eject](https://sli.dev/features/eject-theme)).
3. **A static export** is immune to everything, including the rendering engine itself. reveal.js 6.0.0 moved plugin paths and renamed files, which breaks decks even when the theme does not change ([reveal.js 6.0.0](https://github.com/hakimel/reveal.js/releases/tag/6.0.0)).

For a delivered talk, a pin plus an export gives an editable source and a faithful record of what the audience saw.

**What should be versioned, and how?**
- **The unit of versioning.** Frost prefers one version number for a whole library when consumers are few, because its parts stay compatible and testable together. He reserves per-component versions for systems that serve dozens or hundreds of apps ([Frost 2022](https://bradfrost.com/blog/post/design-system-versioning-single-library-or-individual-components/)). In practice that means one number for the shared core and one for each context library.
- **The yearly frame change is a major release** of the context library. Frost observes that real breaking changes after a first stable release tend to be overhauls across the whole library, such as new typography or a redesign. The most reused layer is therefore the most dangerous one to change.
- **Retiring a part** follows GOV.UK's lane: deprecate a part in any release and remove it in the next major one ([GOV.UK Frontend](https://frontend.design-system.service.gov.uk/staying-up-to-date)).
- **A cheap guard against accidental breaks** is Carbon's committed snapshot of each component's public interface, which reviewers compare when the interface changes ([Carbon versioning](https://raw.githubusercontent.com/carbon-design-system/carbon/main/docs/guides/versioning.md)). For visuals, the analogue is a stored reference render of each component.

Large systems ship scripts that rewrite consumers' code during upgrades. For one author with a handful of pinned talks, a short migration note for each breaking change is enough, because old talks never upgrade unless he asks.

One gap deserves to be stated plainly. None of the authorities in the notes documents a practice for freezing a delivered presentation: Curtis, Frost, NN/g, Figma, Carbon, Polaris, Atlassian and GOV.UK. The recommendation above is assembled from neighbouring practice. Docusaurus also offers a warning about snapshotting: "Most of the time, you don't need versioning", and it suggests keeping fewer than ten versions ([Docusaurus](https://docusaurus.io/docs/versioning)). Copying the whole library into every talk would recreate that sprawl. Pinning by reference, plus an export, avoids it.

## Conclusion

Design-system practice assumes the consumer is another team. In his case the consumer is his past self, and each delivered talk is a consumer that must never be disturbed. That reduces most of the governance machinery (committees, notice periods, upgrade scripts) to two mechanisms: **a lock inside every talk**, and **a periodic review of one-offs across talks** that promotes whatever has appeared three times. It also changes what success means. The tool should not be judged by how much of a talk comes from the library. The two measures that matter are how cheap a one-off is to make, and how quickly a repeated one-off becomes shared. By those measures, his 38 diagrams are not wasted reuse. They are the backlog.

The two halves of his architecture stand on very different ground. The value half (tokens, roles and switchable themes) is solved and standardised in DTCG 2025.10, and he should adopt it rather than invent it. The structure half has no prior art: one component specification rendered natively into HTML, Mural and Figma. He should therefore design three things from the start: the per-renderer feature lists, the stable ids for overrides, and the line between a theme (values) and a frame (layout). Three points remain open. Mural's support for variables is unknown. Support for the Resolver module across tools is unverified. And there is no reuse data specific to slide or diagram libraries.
