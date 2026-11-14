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

**Exit 0 is no pass.** The render exits 0 once it has drawn, findings or not. It judges no content against its components, so it draws over a mistyped key and prints nothing of it. Only the check reports that. Exit 1 means it refused, and drew nothing ([Draw it once](piece.md#6-draw-it-once)).

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

`pkit visual pages <piece>` lists what can be drawn: its languages and keys, what is drawn by default, and each page by its number and trace id. `pkit visual look <piece>` draws pages as images in the clone's local `look/<piece>/`, or `look/<piece>.html/` for the HTML renderer's pages. It moves no lock, keeps no finding, and replaces what an earlier run left there ([The viewing step](../../outputs.md#the-viewing-step)).

**Which pages to draw:**

- **While you mend a page:** `pkit visual look <piece> --page <page>`, by its number or its trace id. By default that is the source language, in the first key.
- **A language or a mode you changed:** add `--language <language>` or `--key <key>`, each of which may repeat.
- **Each size the piece names:** a look draws one size by default. Draw each other size with `--key`, a phone's among them, or all with `--every-key`.
- **Before you stop:** `pkit visual look <piece> --every-language --every-key`. A fault may lie in one language, one mode or one size alone, such as a longer word that breaks a line.

**How to read them.** Open each image, one at a time, and read it as the piece's `audience` would. Go through what the content gives, part by part, then look over the page as a whole. A frame file beside each image gives each element's trace id and its box in the image's pixels, so you can name what you found.

**Against the brief.** Where the piece keeps a brief, read each page against its part and the whole piece's: does the page make visible each relation, serve each goal, and leave the reader with its takeaway, or its lead? Read the reasons last, once you have judged the page, so they do not steer what you see, and check that each still holds of the drawing ([The brief](../../files.md#the-brief)).

**A page in bands.** A page too tall for one image, such as a phone's web page, is drawn in bands, each an image as wide as the page. Read every band of the page, in order, before you judge it. Each overlaps the next by a line, so a part cut at a band's edge shows whole in the band beside it ([The viewing step](../../outputs.md#the-viewing-step)).

**What `report.json` adds.** It says what the images cannot show ([What the report says](../../outputs.md#what-the-report-says)):

| Entry | What it tells you | What to do |
|---|---|---|
| `dropped` | The page does not show a text, a run or a span. Through the HTML renderer, `why` names the cause, and a `cut` or `covered` entry gives the `share` of the span's ink it loses. | Read it as a part missing from the page, even where the image looks whole, and find the element by its frame. Mend it where its cause lies, never by accepting it ([visual-communication:DEC-037-text-the-page-hides] point 1): `no ink` in the span's paint or the file; `off the page` and `cut` in the layout or the content, so the text stays inside its page; `covered` in the layout, the content, or the spacing a component or the brand sets between lines and between texts. Under forced colours alone, two covers are the draw order's to mend ([visual-communication:DEC-039-forced-colours-grounds-and-edges], its Rationale): a part between two texts, which the later text's ground lies over, drawn before both texts, or after both where it meets neither text's letters; and a clipped shape, such as a path or a sign, drawn before the text that rests on it. If you cannot mend it, report it. |
| `dropped-not-read` | Through the SVG renderer, the causes of `dropped` the read does not reach: `cut` and `covered`. | Read the images for a text a part covers or the page's edge cuts. |
| `losses` | What the renderer left out, accepted or not. | Treat one the piece does not accept as `loss` in step 4. |
| `drawn-otherwise` | A run measured in more than one family, which the tool may set in one of them. | Trust the image less on that line. |
| `band`, on an image | The image is one band of a page too tall for one, with its number and how many the page has. | Read each band the page has before you judge the page. |
| `on-white`, on an image | Through the SVG renderer, the page draws no ground of its own, so its white is not the piece's. | Judge a text over nothing knowing this. |
| `on-browser-ground`, on an image | Through the HTML renderer, the page draws no ground of its own. It lies on the browser's own ground in the mode drawn, which differs between browsers. | Judge a text over nothing knowing this, in each mode. No check reads that ground. |

**What an image cannot prove** ([visual-communication:DEC-015-viewing-step-and-reviewer] point 6):

- **A browser's drawing.** An image shows this tool's drawing, and no other tool's.
- **A later drawing.** The pixels may change with the tool, its version or the machine. Keep no image as a reference, and compare none as a contract.
- **A page you did not draw.** One language, one key or one size stands for no other.
- **A pass.** A page that looks right has passed nothing. The check still measures it.

### Where a look stops

Through the HTML renderer a look needs a browser. Where none can run, the look exits 3, leaves the page files and `report.json` with no image, and names the ways on, in this order ([When the browser stops](../../outputs.md#when-the-browser-stops)):

1. a build pipeline's drawings of the piece's pages, where the project has its pipeline draw them. They show a pushed commit, not the working tree.
2. the same look, run once by a person outside any sandbox, such as in their own terminal. That line is addressed to a person, not to you.
3. the SVG renderer's pages, `pkit visual look <piece> --renderer svg`, which show the layout, never the HTML renderer's page.

Where a sandbox stopped it, the stop says so. Go on as [visual-communication:DEC-024-outside-programs-sandbox] point 6 holds:

- **Never take the command out of the sandbox yourself.** Never apply an exclusion from the session's sandbox, and never use the harness's escape on your own. Letting a command out is a person's act.
- **Run the command as the project writes it.** Never change its form to slip out of the sandbox.
- **Read the pipeline's drawings** of the commit you pushed, where you can reach them. Otherwise, or where you need the working tree drawn, ask a person, naming the ways on the stop names.
- **In a run the permission model confines,** a builder's among them, no pipeline's drawings are in reach. Only the SVG renderer's pages remain there. Whoever started the run may read the pipeline's drawings once its commits are pushed.

**How to find a pull request's drawings.** A pipeline that draws them keeps them as `visual-drawings-<commit>`, named by the full hash of the commit it drew ([A pipeline's drawings](../../outputs.md#a-pipelines-drawings)). Take the pull request's head commit, then fetch its drawings into a folder of their own, named by that commit.

Never fetch them into `look/`: a look replaces its renderer's folder there. Read the fetched folder as a look's: `report.json` first, then each image with its frames. They show that commit as the pipeline's browser drew it. Where the download is refused, or its host is out of reach, say so and ask a person.

**Where a person ran the look outside the sandbox,** read the folder that run left in `look/<piece>.html/`. Never run the look over it, since a run replaces that folder ([visual-communication:DEC-020-html-page-drawing] point 5).

## 4. Mend

Mend at the nearest place that holds the fault. Try the content first, then a local component, then a library.

**Never a value in a component.** A component takes its lengths, colours and fonts from roles, and a brand gives the values ([visual-communication:DEC-005-engine-and-plugins] point 1). The check fails a hand-written `#ff0000` or `=:width - 24`.

**When to hand it to `graphic-designer`.** A mend changes a word, an option or a part. A page whose design does not carry its point needs designing again: its form shows another structure than its content has, it has no focal point, a brief finding asks for another form, or no library draws what the brief asks. Hand such a page, or the whole piece, to the capability's designer, naming the piece and its pages ([The designer](../../README.md#the-designer)). It designs them from the brief, mends at the root, has the reviewer read every page before it stops, and tells you what it changed.

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

In the brief ([The brief](../../checks.md#the-brief)):

| Label | What to do |
|---|---|
| `brief-page` | Key the part by the id of a page the content holds, or give the page that id. Before the page exists, keep its intent under `piece`. |
| `brief-path` | Name the part by the keys and ids the content file writes, from the page in a page's part. The message names the nearest key or id. |

Mend the brief, not the content, where an id was renamed on purpose. Never change what the brief asks to clear a finding: its goals and relations are what whoever asked for the piece wants.

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

**When to hand the images to `graphic-design-reviewer`.** It reports what no check measures, whether the pages keep the capability's rules, and whether they show what the piece's brief asks ([The reviewer](../../README.md#the-reviewer)). Dispatch it:

- where a page is dense, since no check measures overlaps or alignment
- where a change reached pages you did not read yourself
- before the piece goes to its audience
- where you cannot read an image yourself

Before you dispatch it, run `pkit visual look` once with all you want read, since it sees only what the last run drew. Name the piece. You may hand it a pipeline's drawings instead, naming the folder you fetched them into and the commit they show. Where its harness reads no image it stops and says so, and those pages stay not looked at.

It reads the piece's brief, and the capability's rule sets, beside the images. Its report names the brief it read, or that the piece has none. Each finding is one of four kinds, kept apart by what it cites:

- **A fault,** from its list of what no check measures, such as text over text. Mend it as in step 4.
- **A rule finding,** which cites a rule of the capability's rule sets by its id. Mend the page so it keeps the rule. Today such a finding only informs.
- **A brief finding,** which cites the part of the brief a page does not show: a relation, a goal, a takeaway, or a reason that does not hold of the drawing. Mend the drawing, in the content or a component, so it shows what the brief asks. Where you changed a choice on purpose, write its reason again. Never draw a relation the brief names as another to fit what a library draws.
- **A note,** anything else worth a look, which never fails.

Its findings are advice, and it changes nothing. Where a piece keeps no brief, it has none to judge against, and says so. Where `graphic-designer` builds the piece, it dispatches the reviewer itself before it stops, or asks you to where it cannot, and hands you the report as the reviewer wrote it.

**Then commit** the piece's folder: `piece.yaml`, the content, its brief, any local component, its `pictures/`, and the `findings.yaml` of the last render. So the check reads it on a fresh clone ([The findings record](../../checks.md#the-findings-record)). Commit the library copies and the configuration with the first piece.
