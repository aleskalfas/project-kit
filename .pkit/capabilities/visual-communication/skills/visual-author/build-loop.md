# The build loop

A piece is built by turns: render it, check it, read it, mend it, and render it again. Each turn answers another question. The render draws, the check measures, and only reading shows what a reader gets. A pass of one says nothing of the others.

Run the steps in this order, on a piece that holds a lock (`piece.md`).

## 1. Render

`pkit visual render <piece>` moves a draft's lock, computes every scene, and writes `findings.yaml` beside `piece.yaml`. It draws an SVG preview of each scene in the clone's local folder, and replaces the piece's previews from before.

It prints:

- **`lock:`** each library version the piece is drawn under.
- **`previews:`** how many it drew, and where.
- **A line for each finding,** opening with its level: `fails:`, `attention:` or `fact:`. Then its place and its message.
- **`loss:`** each loss a renderer reports that the piece does not accept ([The loss report](../../outputs.md#the-loss-report)).
- **`findings:`** how many it kept in `findings.yaml`.

**Exit 0 is no pass.** The render exits 0 once it has drawn, findings or not. It judges no content against its components, so it draws over a mistyped key and prints nothing of it. Only the check reports that. Exit 1 means it refused, and drew nothing ([Draw it once](piece.md#5-draw-it-once)).

## 2. Check

`pkit visual check <piece>` judges the piece and draws nothing. It reads the scene findings from `findings.yaml` where the record still verifies, and otherwise computes them ([When the check reads it](../../checks.md#when-the-check-reads-it)). It exits 1 when a finding fails.

Each finding prints two lines:

```
  error   visual/pieces/first-talk/content.en.yaml#slides[parts].visual.items[content].heading  [content-key]
    → `starter/card` takes no field or option `heading`; did you mean `head`?
```

- **The severity** is its level ([Severities](../../checks.md#severities)):
  - `error` fails. Mend it.
  - `warning` asks for attention. The message says for whom, after ` — for `.
  - `info` states a fact, and asks for nothing.
- **The place** is `<file>#<where>`, the file to open and where to look in it ([What a finding says](../../checks.md#what-a-finding-says)). A trace id, such as `deck/slides[parts]/visual`, names an element of the scene. It follows the content's ids, so it leads to the part of the file to open ([Trace ids](../../components.md#trace-ids)).
- **The label,** in square brackets, is the finding's name. Find what to do with it in step 4.
- **The message** says what was found. A fix, where it names one, follows after ` — `.

A finding in a library version that the project does not correct asks for attention, and names who corrects it. Edit no copy to clear it. Report it to whoever asked for the piece.

## 3. Read

`pkit visual pages <piece>` lists what can be drawn: its languages and keys, what is drawn by default, and each page by its number and trace id. `pkit visual look <piece>` draws pages as images in the clone's local `look/<piece>/`. It moves no lock, keeps no finding, and replaces what an earlier run left there ([The viewing step](../../outputs.md#the-viewing-step)).

**Which pages to draw:**

- **While you mend a page:** `pkit visual look <piece> --page <page>`, by its number or its trace id. By default that is the source language, in the first key.
- **A language or a mode you changed:** add `--language <language>` or `--key <key>`, each of which may repeat.
- **Before you stop:** `pkit visual look <piece> --every-language --every-key`. A fault may lie in one language or one mode alone, such as a longer word that breaks a line.

**How to read them.** Open each image, one at a time, and read it as the piece's `audience` would. Go through what the content gives, part by part, then look over the page as a whole. A frame file beside each image gives each element's trace id and its box in the image's pixels, so you can name what you found.

**What `report.json` adds.** It says what the images cannot show ([What the report says](../../outputs.md#what-the-report-says)):

| Entry | What it tells you | What to do |
|---|---|---|
| `dropped` | The tool drew nothing of a text or a run. | Read it as a part missing from the page, even where the image looks whole. Find the element by its frame, and mend what lost it. If you cannot, report it. |
| `losses` | What the renderer left out, accepted or not. | Treat one the piece does not accept as `loss` in step 4. |
| `drawn-otherwise` | A run measured in more than one family, which the tool may set in one of them. | Trust the image less on that line. |
| `on-white`, on an image | The page draws no ground of its own, so its white is not the piece's. | Judge a text over nothing knowing this. |

**What an image cannot prove** ([visual-communication:DEC-015-viewing-step-and-reviewer] point 6):

- **A browser's drawing.** An image shows this tool's drawing, and no other tool's.
- **A later drawing.** The pixels may change with the tool, its version or the machine. Keep no image as a reference, and compare none as a contract.
- **A page you did not draw.** One language or one key stands for no other.
- **A pass.** A page that looks right has passed nothing. The check still measures it.

## 4. Mend

Mend at the nearest place that holds the fault. Try the content first, then a local component, then a library.

**Never a value in a component.** A component takes its lengths, colours and fonts from roles, and a brand gives the values ([visual-communication:DEC-005-engine-and-plugins] point 1). The check fails a hand-written `#ff0000` or `=:width - 24`.

### The content

Most faults end here, in `content.<language>.yaml`. Shorten a text. Choose another word of an option, or another pattern. Move items to a page of their own.

### A local component

Write one where no library component does the visual's job. It is data, kept in `components/<name>.yaml` in the piece's folder. Content places it as `use: piece/<name>`, filled as a library component is. The check reads it, and the render draws the piece with it ([Components](../../components.md)).

```yaml
pkit_schema: visual-communication:component
schema_version: 1
status: experimental
about: A note on its own ground, as wide as it is given.
fields:
  type: object
  required: [label]
  properties:
    label:
      type: string
      x-pkit-prose: true
parts:
  ground:
    box: {fill: surface, stroke: line, rx: "=@space.1"}
    width: "=:width"
    height: "=:height"
  label:
    text: {content: label, style: type.body, fill: text-primary}
    x: "=@space.3"
    y: "=@space.2"
    width: "=:width - 2 * @space.3"
preferred:
  height: "=label.bottom + @space.2"
```

In a deck's content, it fills a slide's `visual`:

```yaml
visual:
  use: piece/note
  label: One note, drawn by a component of this piece.
```

### A library

Change a library only where the fault lies in it, or other pieces need the same component.

- **A copy of a library the capability ships** is never edited. `pkit visual add` replaces or restores it, and a local edit is lost. Report the fault for whoever maintains the capability.
- **The project's own library** takes the change in a version of its own, listed in the library folder ([The library folder](../../files.md#the-library-folder)). A released version never changes. `pkit visual release <library>` releases the new one.

### By finding

Each label has its row in [Findings by area](../../checks.md#findings-by-area). These are the ones a piece meets most.

In the content ([Content against components](../../checks.md#content-against-components)):

| Label | What to do |
|---|---|
| `content-key` | Rename or remove the key. The message names the nearest known key. |
| `content-required` | Add the field. |
| `content-type`, `content-value`, `content-count` | Change the value, or add or remove items, as the message says. |
| `content-option` | Name a word the option takes. |
| `content-layout` | Name one of the top's layouts, or the component that draws the page. |
| `content-component` | Name the component with `use`, and give the id and the fields on each item. |
| `id-shape`, `id-twice`, `id-languages` | Give each item one id, unique in its list, and the same in every language. |
| `item-clash` | Take the key off the item. |
| `list-clash` | Nothing, until an item needs the key. |
| `tie-shape`, `tie-path`, `tie-ends`, `tie-component` | Name each end by the keys and ids the content file writes ([Content files](../../files.md#content-files)). |

From the scenes ([Scenes](../../checks.md#scenes)):

| Label | What to do |
|---|---|
| `text-overflow` | A word is wider than its text, and text never shrinks. Shorten the word, or give it more width, with fewer items in the row. |
| `gets-less` | Shorten the text, take items out, or choose an option that asks for less. |
| `unknown-component` | Correct the `use`, by the library's page. |
| `unknown-concept` | Name the notation under `notations`, and a concept it holds. |
| `concept-uncoloured` | Choose a style its component paints from its colour family, or drop the `override`. |
| `end-not-found`, `end-point`, `tie-page` | Name an item drawn once, on the tie's page, and a point it exposes. |
| `contrast-drawn` | Drop the `override` or the `concept` that paints the text, or choose an option that lays it on another ground. |
| `font-missing` | Take the character out of the content. |
| `component-shape`, `unknown-colour`, `unknown-role`, `formula-unreadable`, `formula-reach`, `formula-dimension` | In a local component, mend the place the message names, and take each value from a role. |
| `no-size` | Give the local component a `preferred` size, or place it where it is given one. |
| `component-experimental` | Nothing. The library may change it in any release, and the piece still draws. |
| `component-deprecated` | Replace it with the component its library names in its place. |
| `loss` | Change what draws it, or ask a person. Only a person accepts a loss, with a reason ([Accepting a loss](../../outputs.md#accepting-a-loss)). |
| `not-checked` | Run `pkit visual render <piece>`, and commit `findings.yaml`. |

In the files and the libraries ([Files and binding](../../checks.md#files-and-binding), [Libraries and locks](../../checks.md#libraries-and-locks)):

| Label | What to do |
|---|---|
| `binding` | Write the binding the message names. |
| `piece-unreadable` | Mend the file and the field the message names. |
| `lock-missing` | Run `pkit visual render <piece>`. |
| `lock-version`, `lock-not-held`, `lock-unreadable`, `lock-incomplete`, `lock-majors` | Run `pkit visual render <piece>`, which moves a draft's lock. A pinned draft or a published piece takes the fix its row names. |
| `copy-not-shipped`, `library-changed` | Run `pkit visual add <library>`, which brings a copy back to what the capability ships. Restore a version of the project's own library as it was released. |

The render's own facts, `held-clash`, `held-end`, `lock-below` and `lock-kept`, ask for nothing. They say how it chose the lock ([Content against components](../../checks.md#content-against-components)).

After each mend, go back to step 1.

## 5. Stop

The loop ends when all three hold.

1. **The check passes.** `pkit visual check <piece>` exits 0, after the last render. Run `pkit validate` too. It runs the same check ([In `pkit validate`](../../checks.md#in-pkit-validate)), beside the data validation, which alone holds `piece.yaml` to its schema ([The binding](../../files.md#the-binding)).
2. **The pages read.** Each page you drew reads as its `audience` needs, and each entry of `report.json` is answered.
3. **What was not looked at is named.** Report which pages, languages and keys nobody read. What you did not see is not looked at, never clean.

**When to hand the images to `graphic-design-reviewer`.** It reports what no check measures ([The reviewer](../../README.md#the-reviewer)). Dispatch it:

- where a page is dense, since no check measures overlaps or alignment
- where a change reached pages you did not read yourself
- before the piece goes to its audience
- where you cannot read an image yourself

Before you dispatch it, run `pkit visual look` once with all you want read, since it sees only what the last run drew. Name the piece. Mend a fault it reports as in step 4. Its findings are advice, and it changes nothing. Where its harness reads no image it stops and says so, and those pages stay not looked at.

**Then commit** the piece's folder: `piece.yaml`, the content, any local component, and the `findings.yaml` of the last render. So the check reads it on a fresh clone ([The findings record](../../checks.md#the-findings-record)). Commit the library copies and the configuration with the first piece.
